#!/usr/bin/env python3
"""Every command rule at both polarities.

Phase 2 acceptance: "a test suite exercising every command rule at both polarities".
HUG-CMD-001..006 and Dictionary Sec. 2.

Boundaries are tested ON the value and just outside it, because an inhibit tested
only from the inside is not an inhibit and a range tested only from the outside is not
a range. Every threshold comes from `defs/`, so a wrong value in the source fails
these tests instead of being agreed with.
"""
import unittest

from harness import bare_eps, eps_defs, set_soc, spacecraft, tlm_defs


def rate_bounds():
    cmd = next(c for c in tlm_defs()["commands"] if c["mnemonic"] == "CMD_PLD_SET_RATE")
    arg = next(a for a in cmd["args"] if a["name"] == "rate")
    return float(arg["min"]), float(arg["max"])


class TestPayloadActivation(unittest.TestCase):
    """HUG-CMD-002 / CON-04: inhibited in SAFE or below the activation floor."""
    verifies = ("HUG-CMD-002",)

    def setUp(self):
        self.inhibit = float(
            eps_defs()["mode_ladder"]["payload_activation_inhibit_soc_pct"])

    def test_activation_floor_at_both_polarities(self):
        for soc, expect in ((self.inhibit - 0.01, False), (self.inhibit, True)):
            with self.subTest(soc=soc, expect_accept=expect):
                sim = set_soc(spacecraft(), soc)
                accepted, reason = sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "ON"})
                self.assertEqual(accepted, expect,
                                 f"payload activation at SoC {soc}% against a "
                                 f"{self.inhibit}% floor")
                self.assertEqual(sim.eps.state.payload_on, expect)
                if not expect:
                    self.assertEqual(reason, "MODE_INHIBIT")

    def test_activation_is_inhibited_in_safe_at_any_state_of_charge(self):
        """The mode inhibit is independent of the floor: a full battery in SAFE still
        refuses. Otherwise a spacecraft that safed itself could be loaded straight
        back up by an operator reading only the SoC."""
        for soc in (self.inhibit, 60.0, 99.99, 100.0):
            with self.subTest(soc=soc):
                sim = set_soc(spacecraft(), soc)
                sim.eps.state.mode = "SAFE"
                accepted, reason = sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "ON"})
                self.assertFalse(accepted, f"payload activated in SAFE at SoC {soc}%")
                self.assertEqual(reason, "MODE_INHIBIT")

    def test_deactivation_is_always_accepted(self):
        """Shedding load is never inhibited — the direction that makes the spacecraft
        safer must not be refusable."""
        for mode in ("NOMINAL", "LOW_POWER", "SAFE"):
            for soc in (0.0, 19.0, 39.99, 100.0):
                with self.subTest(mode=mode, soc=soc):
                    sim = set_soc(spacecraft(), soc)
                    sim.eps.state.mode = mode
                    sim.eps.state.payload_on = True
                    accepted, _ = sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "OFF"})
                    self.assertTrue(accepted)
                    self.assertFalse(sim.eps.state.payload_on)

    def test_an_undefined_state_argument_is_an_argument_error(self):
        for bad in ("MAYBE", "on", "", None, 1):
            with self.subTest(state=bad):
                sim = set_soc(spacecraft(), 100.0)
                accepted, reason = sim.cdh.receive("CMD_PLD_SET_STATE", {"state": bad})
                self.assertFalse(accepted)
                self.assertEqual(reason, "ARG_RANGE")


class TestPayloadRate(unittest.TestCase):
    """HUG-CMD-003: 0.1-10 Hz only, and rejected when the payload is OFF."""
    verifies = ("HUG-CMD-003",)

    def setUp(self):
        self.lo, self.hi = rate_bounds()

    def _payload_on(self):
        sim = set_soc(spacecraft(), 100.0)
        self.assertTrue(sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "ON"})[0])
        return sim

    def test_range_bounds_at_both_polarities(self):
        cases = [(self.lo, True), (self.hi, True),
                 (self.lo - 0.001, False), (self.hi + 0.001, False),
                 (0.0, False), (-1.0, False), (1000.0, False)]
        for rate, expect in cases:
            with self.subTest(rate=rate, expect_accept=expect):
                sim = self._payload_on()
                accepted, reason = sim.cdh.receive("CMD_PLD_SET_RATE", {"rate": rate})
                self.assertEqual(accepted, expect,
                                 f"rate {rate} against range [{self.lo}, {self.hi}]")
                if expect:
                    self.assertEqual(sim.eps.state.pld_rate_hz, rate)
                else:
                    self.assertEqual(reason, "ARG_RANGE")

    def test_rate_is_inhibited_while_the_payload_is_off(self):
        sim = set_soc(spacecraft(), 100.0)
        self.assertFalse(sim.eps.state.payload_on)
        accepted, reason = sim.cdh.receive("CMD_PLD_SET_RATE", {"rate": 5.0})
        self.assertFalse(accepted)
        self.assertEqual(reason, "MODE_INHIBIT")

    def test_range_is_checked_before_the_payload_off_inhibit(self):
        """The order is observable in CDH_REJ_REASON, so it is pinned. An operator
        debugging a rejected rate command needs to know which gate stopped it."""
        sim = set_soc(spacecraft(), 100.0)          # payload OFF and rate out of range
        accepted, reason = sim.cdh.receive("CMD_PLD_SET_RATE", {"rate": 99.0})
        self.assertFalse(accepted)
        self.assertEqual(reason, "ARG_RANGE",
                         "with both gates failing, the argument error is reported")

    def test_a_non_numeric_rate_is_an_argument_error(self):
        for bad in ("5.0", None, True, [5.0]):
            with self.subTest(rate=bad):
                sim = self._payload_on()
                accepted, reason = sim.cdh.receive("CMD_PLD_SET_RATE", {"rate": bad})
                self.assertFalse(accepted)
                self.assertEqual(reason, "ARG_RANGE")

    def test_the_rate_register_always_holds_a_dictionary_valid_value(self):
        """replay_schema.md Sec. 5 / RS-7-13: pld_rate is dictionary-bounded in every
        payload state, so an OFF frame reports the resting register value and never a
        sentinel or a null."""
        sim = self._payload_on()
        self.assertTrue(sim.cdh.receive("CMD_PLD_SET_RATE", {"rate": 7.0})[0])
        self.assertTrue(sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "OFF"})[0])
        frame = sim.cdh.generate_frame(0)
        self.assertEqual(frame["PLD_STATE"], "OFF")
        self.assertGreaterEqual(frame["PLD_RATE"], self.lo)
        self.assertLessEqual(frame["PLD_RATE"], self.hi)


class TestSafeEntryIsUnconditional(unittest.TestCase):
    """HUG-CMD-004: SAFE-mode entry from the ground is always accepted regardless of
    mode. This is the ground's unconditional backstop, and FM-EPS-10 names it as the
    compensating provision for a ladder that fails to actuate — so it is asserted as a
    property over the state space, not at a few points."""
    verifies = ("HUG-CMD-004",)

    def test_accepted_from_every_mode_across_the_soc_domain(self):
        modes = eps_defs()["mode_ladder"]["order"]
        refused = []
        for mode in modes:
            for i in range(0, 10001, 25):            # 0.00% to 100.00%, 401 points
                soc = i / 100.0
                sim = set_soc(spacecraft(), soc)
                sim.eps.state.mode = mode
                accepted, _ = sim.cdh.receive("CMD_SAFE_ENTER", {})
                if not accepted or sim.eps.state.mode != "SAFE":
                    refused.append((mode, soc))
        self.assertEqual(refused, [],
                         f"CMD_SAFE_ENTER was refused or failed to enter SAFE in "
                         f"{len(refused)} states; it must always be accepted")

    def test_safe_entry_sheds_the_payload(self):
        sim = set_soc(spacecraft(), 100.0)
        self.assertTrue(sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "ON"})[0])
        self.assertTrue(sim.eps.state.payload_on)
        self.assertTrue(sim.cdh.receive("CMD_SAFE_ENTER", {})[0])
        self.assertFalse(sim.eps.state.payload_on)
        self.assertEqual(sim.eps.state.mode, "SAFE")


class TestModeSetTransitionEffects(unittest.TestCase):
    """Dictionary Sec. 2: a commanded transition to LOW_POWER sheds the payload; a
    transition to NOMINAL does NOT re-enable it."""
    verifies = ("HUG-CMD-006",)

    def test_commanded_low_power_sheds_the_payload(self):
        sim = set_soc(spacecraft(), 100.0)
        self.assertTrue(sim.cdh.receive("CMD_PLD_SET_STATE", {"state": "ON"})[0])
        self.assertTrue(sim.cdh.receive("CMD_MODE_SET", {"target": "LOW_POWER"})[0])
        self.assertEqual(sim.eps.state.mode, "LOW_POWER")
        self.assertFalse(sim.eps.state.payload_on,
                         "a commanded transition to LOW_POWER must shed the payload")

    def test_commanded_nominal_does_not_re_enable_the_payload(self):
        """Re-activation is CMD_PLD_SET_STATE's job, subject to its own inhibits. A
        mode command that silently powered the payload back on would bypass the 40%
        activation floor."""
        sim = set_soc(spacecraft(), 100.0)
        sim.eps.state.mode = "LOW_POWER"
        self.assertFalse(sim.eps.state.payload_on)
        self.assertTrue(sim.cdh.receive("CMD_MODE_SET", {"target": "NOMINAL"})[0])
        self.assertEqual(sim.eps.state.mode, "NOMINAL")
        self.assertFalse(sim.eps.state.payload_on)

    def test_undefined_targets_are_argument_errors(self):
        for bad in ("SAFE", "safe", "NOMINAL_PLUS", "", None, 0):
            with self.subTest(target=bad):
                sim = set_soc(spacecraft(), 100.0)
                accepted, reason = sim.cdh.receive("CMD_MODE_SET", {"target": bad})
                self.assertFalse(accepted)
                self.assertEqual(reason, "ARG_RANGE")


class TestFiveCommandsExactly(unittest.TestCase):
    verifies = ("HUG-CMD-001",)
    def test_the_spacecraft_implements_exactly_the_records_command_set(self):
        """Dictionary Sec. 2 defines five. A sixth the record does not name would be
        an undocumented capability; a missing one would be an unimplemented
        requirement."""
        sim = spacecraft()
        recorded = {c["mnemonic"] for c in tlm_defs()["commands"]}
        self.assertEqual(len(recorded), 5)
        self.assertEqual(set(sim.cdh.commands), recorded)
        for mnemonic in recorded:
            self.assertTrue(hasattr(sim.cdh, "_cmd_" + mnemonic[4:].lower()),
                            f"{mnemonic} has no handler")

    def test_opcodes_are_unique_and_dispatch_to_their_own_command(self):
        sim = spacecraft()
        opcodes = [c["opcode"] for c in tlm_defs()["commands"]]
        self.assertEqual(len(set(opcodes)), len(opcodes), "opcodes must be unique")
        for command in tlm_defs()["commands"]:
            self.assertEqual(sim.cdh.opcodes[command["opcode"]], command["mnemonic"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
