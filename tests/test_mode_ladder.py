#!/usr/bin/env python3
"""The mode ladder: downward-only as a property, and both recovery floors at both
polarities.

Owner standing instruction for Phase 2, and the property four FMEA rows lean on:

  FM-EPS-10 rates an unactuated ladder as a LATENT defeat of a protective layer, and
  its compensating provision is that the ground can always force SAFE. If the ladder
  could promote itself, that latency would become an active hazard - the spacecraft
  could climb out of the protection it just entered, with the ground none the wiser.
  So "downward only" is asserted as a PROPERTY over the whole state space, not at
  sampled points: sampling proves the sampled points, and a promotion bug is exactly
  the kind that hides between them.

  The recovery floors sit 5 points above the autonomous entry thresholds so a
  commanded recovery cannot immediately re-trip the ladder (Dictionary Sec. 2
  mode-authority rule). Both floors are tested at BOTH polarities - just below must
  be refused, at and above must be accepted - because a floor that only ever gets
  tested from the accepting side is not a floor.
"""
import unittest

from harness import bare_eps, eps_defs, set_soc, spacecraft


class TestDownwardOnlyProperty(unittest.TestCase):
    """HUG-EPS-003 / CON-02: autonomous transitions are downward only."""
    verifies = ("HUG-EPS-003",)

    def test_ladder_never_promotes_over_the_whole_soc_domain(self):
        defs = eps_defs()
        order = defs["mode_ladder"]["order"]
        # 0.00% to 100.00% in 0.01% steps, from every starting mode: 30 003 states.
        # Exhaustive over the domain at a resolution finer than any threshold, so
        # there is no gap between tested points for a promotion to hide in.
        steps = 10001
        promotions, checked = [], 0
        eps = bare_eps()
        for start_mode in order:
            for i in range(steps):
                soc = i / 100.0
                eps.state.mode = start_mode
                eps.state.energy_wh = eps.capacity_wh * (soc / 100.0)
                before = eps.depth_index(eps.state.mode)
                eps._apply_ladder()
                after = eps.depth_index(eps.state.mode)
                checked += 1
                if after < before:
                    promotions.append((start_mode, soc, eps.state.mode))
        self.assertEqual(promotions, [],
                         f"the autonomous ladder promoted in {len(promotions)} of "
                         f"{checked} states; it must only ever move deeper")
        self.assertEqual(checked, steps * len(order))

    def test_ladder_enters_the_deeper_mode_at_each_threshold(self):
        """The property above forbids promotion; this one shows the ladder still
        acts, so 'never promotes' is not satisfied by a ladder that never moves."""
        defs = eps_defs()
        entry = defs["mode_ladder"]["autonomous_entry_soc_pct"]
        for soc, expected in ((entry["LOW_POWER"] - 0.01, "LOW_POWER"),
                              (entry["SAFE"] - 0.01, "SAFE")):
            sim = set_soc(spacecraft(), soc)
            sim.eps._apply_ladder()
            self.assertEqual(sim.eps.state.mode, expected,
                             f"at SoC {soc}% the ladder should hold {expected}")

    def test_autonomous_entry_sheds_the_payload(self):
        """HUG-EPS-003: each transition sheds the payload load."""
        defs = eps_defs()
        entry = defs["mode_ladder"]["autonomous_entry_soc_pct"]
        for soc in (entry["LOW_POWER"] - 0.01, entry["SAFE"] - 0.01):
            sim = set_soc(spacecraft(), 100.0)
            sim.eps.state.payload_on = True
            set_soc(sim, soc)
            sim.eps._apply_ladder()
            self.assertFalse(sim.eps.state.payload_on,
                             f"payload not shed on autonomous entry at SoC {soc}%")

    def test_no_autonomous_recovery_path_exists_at_any_soc(self):
        """Stepping the model - not just the ladder - must never promote either.

        This runs the full step path so a promotion introduced anywhere in it, not
        only in the ladder function, is caught.
        """
        for start_mode in ("SAFE", "LOW_POWER"):
            for soc in (0.0, 19.99, 20.0, 25.0, 29.99, 30.0, 35.0, 50.0, 99.99, 100.0):
                sim = spacecraft()
                sim.eps.state.mode = start_mode
                set_soc(sim, soc)
                before = sim.eps.depth_index(start_mode)
                for _ in range(120):
                    sim.step()
                after = sim.eps.depth_index(sim.eps.state.mode)
                self.assertGreaterEqual(
                    after, before,
                    f"stepping from {start_mode} at SoC {soc}% promoted the "
                    f"spacecraft to {sim.eps.state.mode} with no ground command")


class TestRecoveryFloorsBothPolarities(unittest.TestCase):
    """HUG-CMD-006: commanded recovery is refused below the target's floor."""
    verifies = ("HUG-CMD-006", "HUG-EPS-003")

    def test_each_floor_refuses_just_below_and_accepts_at_the_floor(self):
        defs = eps_defs()
        floors = defs["mode_ladder"]["recovery_floor_soc_pct"]
        self.assertEqual(set(floors), {"NOMINAL", "LOW_POWER"},
                         "the record defines exactly two commandable targets")
        for target, floor in sorted(floors.items()):
            with self.subTest(target=target, polarity="below floor -> refused"):
                sim = spacecraft()
                sim.eps.state.mode = "SAFE"
                set_soc(sim, floor - 0.01)
                accepted, reason = sim.cdh.receive("CMD_MODE_SET", {"target": target})
                self.assertFalse(accepted,
                                 f"CMD_MODE_SET {target} accepted at SoC "
                                 f"{floor - 0.01}%, below its {floor}% floor")
                self.assertEqual(reason, "MODE_INHIBIT")
                self.assertEqual(sim.eps.state.mode, "SAFE",
                                 "a refused mode command must not change the mode")
            with self.subTest(target=target, polarity="at floor -> accepted"):
                sim = spacecraft()
                sim.eps.state.mode = "SAFE"
                set_soc(sim, floor)
                accepted, reason = sim.cdh.receive("CMD_MODE_SET", {"target": target})
                self.assertTrue(accepted,
                                f"CMD_MODE_SET {target} refused at exactly its "
                                f"{floor}% floor; the floor is inclusive")
                self.assertEqual(reason, "NONE")
                self.assertEqual(sim.eps.state.mode, target)

    def test_floors_sit_above_the_autonomous_entry_points(self):
        """The hysteresis property the mode-authority rule exists to give: a
        commanded recovery cannot immediately re-trip the ladder."""
        defs = eps_defs()
        floors = defs["mode_ladder"]["recovery_floor_soc_pct"]
        entry = defs["mode_ladder"]["autonomous_entry_soc_pct"]
        self.assertGreater(floors["NOMINAL"], entry["LOW_POWER"],
                           "recovering to NOMINAL at its floor would re-trip LOW_POWER")
        self.assertGreater(floors["LOW_POWER"], entry["SAFE"],
                           "recovering to LOW_POWER at its floor would re-trip SAFE")

    def test_a_recovery_at_the_floor_survives_the_next_step(self):
        """Executed rather than argued: command the recovery at exactly the floor,
        then step, and the ladder must not take it straight back."""
        defs = eps_defs()
        floors = defs["mode_ladder"]["recovery_floor_soc_pct"]
        for target, floor in sorted(floors.items()):
            sim = spacecraft()
            sim.eps.state.mode = "SAFE"
            set_soc(sim, floor)
            self.assertTrue(sim.cdh.receive("CMD_MODE_SET", {"target": target})[0])
            sim.step()
            self.assertEqual(sim.eps.state.mode, target,
                             f"the ladder re-tripped {target} immediately after a "
                             f"commanded recovery at its {floor}% floor")

    def test_safe_target_is_an_argument_error_not_an_inhibit(self):
        """HUG-CMD-006: SAFE entry is CMD_SAFE_ENTER's function, so SAFE as a
        CMD_MODE_SET target is ARG_RANGE. The distinction is what the operator
        reads out of CDH_REJ_REASON."""
        sim = set_soc(spacecraft(), 100.0)
        accepted, reason = sim.cdh.receive("CMD_MODE_SET", {"target": "SAFE"})
        self.assertFalse(accepted)
        self.assertEqual(reason, "ARG_RANGE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
