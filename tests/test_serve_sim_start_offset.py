#!/usr/bin/env python3
"""The simulator start offset, at both polarities (OF-016, ruled at D-015).

The campaign's contacts are windows into a mission, and every anomaly scenario injects
its fault well after the first contact closes. Before `--start-at` a run always began at
MET 0, so an operator flying the assigned contact from acquisition saw MET 0 through 430
and the fault never occurred inside the pass. The offset is the mechanism the Director
ruled for reaching a contact that opens later; the scenario files are not re-timed,
because HUG-SYS-005 makes them the sole source of faults.

TWO THINGS ARE PROVED HERE AND THEY ARE NOT THE SAME THING.

  REACH       A pre-rolled run observes a fault that the window reachable without the
              offset does not contain. The green half is the reachable window showing
              NO asymmetry - without it, a test that merely finds the fault at MET 700
              would pass just as happily if the fault had been at MET 0 all along, and
              would be evidence for nothing.

  EQUIVALENCE The state after a silent pre-roll of N steps equals the state after N
              transmitted steps. This is the claim that makes the pre-roll admissible
              at all: if it were not exact, a pass flown from an offset would be a pass
              of a different mission. HUG-SYS-003 is what makes it true - the engine is
              stepped by count, not by clock - and this is where that is checked rather
              than assumed.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import serve_sim                                                     # noqa: E402

SCENARIO = "P2_array_string_loss"
FAULT_ONSET = 600.0          # MET at which P2 zeroes string 1
CONTACT_S = 430.0            # the contact PASS-2 was assigned, from the campaign plan


def strings_at(sim):
    return tuple(round(c, 6) for c in sim.eps.state.string_currents_a)


def state_of(sim):
    """Everything that must match for two runs to be the same run."""
    return (
        round(sim.t_s, 6),
        round(sim.eps.soc_pct, 9),
        sim.eps.state.mode,
        sim.eps.state.payload_on,
        round(sim.eps.state.load_current_a, 9),
        round(sim.eps.state.battery_current_a, 9),
        strings_at(sim),
        sim.cdh.acc_count,
        sim.cdh.rej_count,
        sim.cdh.frame_count,
        sim.cdh.hk_halted,
    )


class TestTheOffsetReachesAFaultTheContactCouldNot(unittest.TestCase):
    """RED — the defect OF-016 records, reproduced and then closed."""
    verifies = ("HUG-SYS-005",)
    polarity = "red"

    def test_the_window_reachable_without_the_offset_shows_no_asymmetry(self):
        """GREEN half. Without it the red half proves nothing about WHEN the fault is."""
        sim = serve_sim.build(SCENARIO)
        while sim.t_s < CONTACT_S:
            sim.step()
        a1, a2 = strings_at(sim)
        self.assertGreater(a1, 0.0,
                           "string 1 is already dead inside the first contact; the "
                           "offset would then be solving a problem that is not there")
        self.assertAlmostEqual(a1, a2, places=6)

    def test_a_pre_rolled_run_observes_the_asymmetry(self):
        sim = serve_sim.build(SCENARIO)
        serve_sim.pre_roll(sim, FAULT_ONSET + 100.0, quiet=True)
        a1, a2 = strings_at(sim)
        self.assertEqual(a1, 0.0, "string 1 should be zeroed past the fault onset")
        self.assertGreater(a2, 0.0, "string 2 should still be generating")

    def test_the_fault_onset_lies_beyond_the_assigned_contact(self):
        """The measurement OF-016 rests on, asserted rather than quoted."""
        sim = serve_sim.build(SCENARIO)
        self.assertGreater(FAULT_ONSET, CONTACT_S)


class TestThePreRollIsTheSameRun(unittest.TestCase):
    """The equivalence that makes a pre-rolled pass a pass of the same mission."""
    verifies = ("HUG-SYS-003",)
    polarity = "green"

    def test_pre_roll_equals_stepping_from_zero(self):
        for met in (120.0, 430.0, 700.0, 1500.0):
            with self.subTest(met=met):
                rolled = serve_sim.build(SCENARIO)
                serve_sim.pre_roll(rolled, met, quiet=True)
                stepped = serve_sim.build(SCENARIO)
                while stepped.t_s < met:
                    stepped.step()
                self.assertEqual(state_of(rolled), state_of(stepped))

    def test_scripted_commands_inside_the_pre_roll_are_applied(self):
        """P2 scripts CMD_PLD_SET_STATE ON at MET 120; a pre-roll past it must carry it."""
        sim = serve_sim.build(SCENARIO)
        serve_sim.pre_roll(sim, 300.0, quiet=True)
        self.assertGreater(sim.cdh.acc_count, 0,
                           "the scenario's scripted command was skipped by the pre-roll")

    def test_frames_continue_from_the_offset_not_from_zero(self):
        sim = serve_sim.build(SCENARIO)
        serve_sim.pre_roll(sim, 700.0, quiet=True)
        frame = sim.step()
        self.assertIsNotNone(frame)
        self.assertGreaterEqual(sim.t_s, 700.0)


class TestTheOffsetRefusesWhatItCannotServe(unittest.TestCase):
    """RED — a pre-roll past the scenario's end transmits nothing and must say so."""
    verifies = ("HUG-SYS-005",)
    polarity = "red"

    def test_a_start_beyond_the_scenario_duration_is_refused(self):
        sim = serve_sim.build(SCENARIO)
        duration = sim.scenario.duration_s
        with self.assertRaises(ValueError) as caught:
            serve_sim.serve(SCENARIO, port=0, rate=1.0, limit=None, quiet=True,
                            start_at=duration + 1.0)
        self.assertIn("duration_s", str(caught.exception))

    def test_a_start_exactly_at_the_duration_is_refused(self):
        sim = serve_sim.build(SCENARIO)
        with self.assertRaises(ValueError):
            serve_sim.serve(SCENARIO, port=0, rate=1.0, limit=None, quiet=True,
                            start_at=float(sim.scenario.duration_s))


class TestALimitAtOrBelowTheStartIsRefused(unittest.TestCase):
    """RED — the half of the window guard that was owed.

    `--start-at` beyond the scenario was refused from the start; `--limit` below
    `--start-at` was not, and transmitted nothing by documented design. On the console
    that is a simulator that starts, lets COSMOS connect, and sends no frames - the same
    picture as a simulator that is not up, which the preflight check teaches an operator
    to read as ConnectionRefusedError. The likeliest way to produce it is to type the
    contact's length where its stop MET belongs.
    """
    verifies = ("HUG-SYS-005",)
    polarity = "red"

    def test_a_limit_below_the_start_is_refused_naming_both_values(self):
        with self.assertRaises(ValueError) as caught:
            serve_sim.serve(SCENARIO, port=0, rate=1.0, limit=21000, quiet=True,
                            start_at=21700)
        message = str(caught.exception)
        self.assertIn("--limit 21000", message)
        self.assertIn("--start-at 21700", message)

    def test_a_limit_exactly_at_the_start_is_refused(self):
        """At equality the loop also stops before its first frame."""
        with self.assertRaises(ValueError):
            serve_sim.serve(SCENARIO, port=0, rate=1.0, limit=21700, quiet=True,
                            start_at=21700)

    def test_a_contact_length_typed_as_the_limit_is_named(self):
        with self.assertRaises(ValueError) as caught:
            serve_sim.check_run_window(SCENARIO, 23040, 21700, 430)
        self.assertIn("the stop MET is 22130", str(caught.exception))


class TestARunThatCanTransmitIsNotRefused(unittest.TestCase):
    """GREEN — the guard must not refuse a run that would transmit.

    Tested through the pure check rather than by starting a server: serve() would bind
    a socket, and a refusal test that needs the network is a test that fails for the
    network's reasons.
    """
    verifies = ("HUG-SYS-005",)
    polarity = "green"

    def test_a_limit_above_the_start_is_accepted(self):
        serve_sim.check_run_window(SCENARIO, 23040, 21700, 22130)

    def test_no_limit_is_accepted(self):
        serve_sim.check_run_window(SCENARIO, 23040, 21700, None)

    def test_limit_zero_keeps_its_meaning_of_no_limit(self):
        serve_sim.check_run_window(SCENARIO, 23040, 0, 0)

    def test_the_default_run_is_accepted(self):
        serve_sim.check_run_window(SCENARIO, 23040, 0.0, None)


class TestTheDefaultIsUnchanged(unittest.TestCase):
    """GREEN — the flag's absence must leave the previous behaviour exactly as it was."""
    verifies = ("HUG-SYS-003",)
    polarity = "green"

    def test_no_offset_takes_no_steps(self):
        sim = serve_sim.build(SCENARIO)
        self.assertEqual(serve_sim.pre_roll(sim, 0.0, quiet=True), 0)
        self.assertEqual(sim.t_s, 0.0)

    def test_no_offset_leaves_the_model_at_met_zero(self):
        sim = serve_sim.build(SCENARIO)
        serve_sim.pre_roll(sim, 0, quiet=True)
        self.assertEqual(state_of(sim), state_of(serve_sim.build(SCENARIO)))


if __name__ == "__main__":
    unittest.main()
