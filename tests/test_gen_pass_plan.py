#!/usr/bin/env python3
"""The predicted pass plan, at both polarities (OF-020).

THE DANGER THIS FILE EXISTS FOR. A prediction built from the same run as the truth IS the
truth, so actual-minus-predicted is identically zero and the plan reports every pass as
nominal. Such a tool runs, produces a tidy table, and never once says anything. These
cases are what separate the prediction from that.

THE TRUTH IS COMPUTED HERE, INDEPENDENTLY. Every actual run below is the plain simulator
on the scenario as loaded from disk — never anything from tools/gen_pass_plan.py. If the
truth came through the tool too, a broken tool would make both sides wrong in the same
way and the comparison would agree with itself.

Each red case was made to fail on purpose before it was trusted; the commit that adds
this file records how each one was broken.
"""
import builtins
import hashlib
import io
import os
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import gen_pass_plan                                                # noqa: E402
import hugdefs                                                      # noqa: E402
from sim.scenario import Scenario                                   # noqa: E402
from sim.spacecraft import Spacecraft                               # noqa: E402

SCENARIOS = REPO / "sim" / "scenarios"


def actual(name, start_at, duration):
    """THE TRUTH: the scenario exactly as on disk, faults and all. {MET: frame}."""
    sim = Spacecraft(hugdefs.load_eps(), hugdefs.load_tlm_cmd(),
                     Scenario.load(SCENARIOS / f"{name}.yaml"))
    while sim.t_s < start_at:
        sim.step()
    out = {}
    while sim.t_s < start_at + duration:
        frame = sim.step()
        if frame is not None:
            out[frame["CDH_MET"]] = frame
    return out


def predicted(name, start_at, duration):
    _scenario, frames = gen_pass_plan.predict(name, start_at, duration)
    return {f["CDH_MET"]: f for f in frames}


class TestTheControl(unittest.TestCase):
    """RED CASE 1. A scenario with no faults must predict itself, frame for frame.

    P1_nominal has no faults, so the prediction rule should change nothing at all. It
    does script commands (payload ON at MET 180, rate at MET 240), which makes this the
    case that also catches a generator that throws the planned commands away along with
    the faults: that prediction diverges from MET 180.
    """
    verifies = ("HUG-SYS-005",)
    polarity = "red"

    def test_p1_nominal_predicts_itself_identically(self):
        truth = actual("P1_nominal", 0, 600)
        plan = predicted("P1_nominal", 0, 600)
        self.assertEqual(len(truth), 600)
        self.assertEqual(sorted(plan), sorted(truth))
        for met in sorted(truth):
            self.assertEqual(plan[met], truth[met], f"frame at MET {met} differs")

    def test_p1_nominal_has_no_faults_and_does_have_commands(self):
        """The two facts the control rests on, checked rather than assumed."""
        sc = Scenario.load(SCENARIOS / "P1_nominal.yaml")
        self.assertEqual(sc.faults, [])
        self.assertTrue(any(c["t_s"] < 600 for c in sc.commands))


class TestTheDivergence(unittest.TestCase):
    """RED CASE 2 — the one that must not be wrong.

    P3_stuck_load, acquisition at MET 800, 430 s. The stuck load starts at MET 900. A
    generator that forgot to drop the faults predicts 68.333 % at LOS instead of 68.792 %,
    1.800 A of load instead of 1.400 A, and a divergence of zero everywhere.
    """
    verifies = ("HUG-SYS-005", "HUG-OPS-002")
    polarity = "red"

    @classmethod
    def setUpClass(cls):
        cls.plan = predicted("P3_stuck_load", 800, 430)
        cls.truth = actual("P3_stuck_load", 800, 430)

    def test_predicted_state_of_charge_at_los(self):
        self.assertEqual(round(self.plan[1229]["EPS_BATT_SOC"], 3), 68.792)

    def test_predicted_load_is_the_unfaulted_load_across_the_whole_contact(self):
        loads = {round(f["EPS_LOAD_I"], 3) for f in self.plan.values()}
        self.assertEqual(loads, {1.400})

    def test_predicted_battery_current_at_los(self):
        self.assertEqual(round(self.plan[1229]["EPS_BATT_I"], 4), 1.2986)

    def test_the_truth_side_is_what_the_measurements_say(self):
        """The comparison is only meaningful if the truth is right too."""
        self.assertEqual(round(self.truth[1229]["EPS_BATT_SOC"], 3), 68.333)
        self.assertEqual(round(self.truth[899]["EPS_LOAD_I"], 3), 1.400)
        self.assertEqual(round(self.truth[900]["EPS_LOAD_I"], 3), 1.800)
        self.assertEqual(round(self.truth[1229]["EPS_BATT_I"], 4), 1.0397)

    def test_no_divergence_before_the_fault(self):
        d = self.truth[800]["EPS_BATT_SOC"] - self.plan[800]["EPS_BATT_SOC"]
        self.assertEqual(round(d, 3), 0.0)

    def test_the_fault_shows_as_divergence_at_los(self):
        d = self.truth[1229]["EPS_BATT_SOC"] - self.plan[1229]["EPS_BATT_SOC"]
        self.assertEqual(round(d, 3), -0.458)


class TestFrameAbsence(unittest.TestCase):
    """RED CASE 3. A telemetry halt costs no power.

    P4_hk_generation_halt suppresses frames from MET 1200 until its scripted reset at
    1320. State of charge does not diverge at all, so a tool that compared only values
    would call the pass nominal. The signature is 120 frames the plan expects and the
    actual run never produces.
    """
    verifies = ("HUG-SYS-005", "HUG-OPS-002")
    polarity = "red"

    START, DURATION = 1100, 430          # MET 1100..1529, spanning the halt

    @classmethod
    def setUpClass(cls):
        cls.plan = predicted("P4_hk_generation_halt", cls.START, cls.DURATION)
        cls.truth = actual("P4_hk_generation_halt", cls.START, cls.DURATION)

    def test_the_plan_expects_every_frame(self):
        self.assertEqual(len(self.plan), self.DURATION)

    def test_exactly_120_expected_frames_never_arrive(self):
        missing = sorted(set(self.plan) - set(self.truth))
        self.assertEqual(len(missing), 120)
        self.assertEqual((missing[0], missing[-1]), (1200, 1319))

    def test_state_of_charge_does_not_diverge(self):
        worst = max(abs(self.truth[m]["EPS_BATT_SOC"] - self.plan[m]["EPS_BATT_SOC"])
                    for m in self.truth)
        self.assertEqual(round(worst, 4), 0.0)

    def test_the_artefact_states_the_expected_frame_count(self):
        with tempfile.TemporaryDirectory() as td:
            _path, text = gen_pass_plan.generate("TEST-P4", "P4_hk_generation_halt",
                                                 self.START, self.DURATION, 2, td)
        self.assertIn(f"**{self.DURATION} frames**, MET 1100 through 1529", text)
        self.assertIn("| Scenario | `P4_hk_generation_halt` |", text)


class TestRefusal(unittest.TestCase):
    """RED CASE 4. A window the scenario cannot fill is refused, not emitted short."""
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def test_start_beyond_the_scenario_is_refused(self):
        dur = Scenario.load(SCENARIOS / "P3_stuck_load.yaml").duration_s
        with self.assertRaises(gen_pass_plan.PlanRefused) as caught:
            gen_pass_plan.predict("P3_stuck_load", dur + 1, 430)
        self.assertIn(str(dur), str(caught.exception))

    def test_start_exactly_at_the_scenario_end_is_refused(self):
        dur = Scenario.load(SCENARIOS / "P3_stuck_load.yaml").duration_s
        with self.assertRaises(gen_pass_plan.PlanRefused):
            gen_pass_plan.predict("P3_stuck_load", dur, 430)

    def test_a_contact_running_past_the_scenario_end_is_refused(self):
        dur = Scenario.load(SCENARIOS / "P3_stuck_load.yaml").duration_s
        with self.assertRaises(gen_pass_plan.PlanRefused) as caught:
            gen_pass_plan.predict("P3_stuck_load", dur - 100, 430)
        message = str(caught.exception)
        self.assertIn(str(dur - 100), message)
        self.assertIn("430", message)

    def test_the_command_line_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            old = gen_pass_plan.REPORTS
            gen_pass_plan.REPORTS = Path(td)
            try:
                err = io.StringIO()
                stderr, sys.stderr = sys.stderr, err
                try:
                    rc = gen_pass_plan.main(["--pass-id", "T", "--scenario",
                                             "P3_stuck_load", "--start-at", "99999",
                                             "--duration", "430", "--contact", "9"])
                finally:
                    sys.stderr = stderr
                written = list(Path(td).iterdir())
            finally:
                gen_pass_plan.REPORTS = old
            # Checked FIRST, because writing is the side effect a refusal exists to
            # prevent. This assertion was once vacuous: generate() bound its output
            # directory at definition time, so re-pointing REPORTS changed nothing and
            # this list was empty however the tool behaved.
            self.assertEqual(written, [], f"a refused plan was written: {written}")
            self.assertEqual(rc, 2)
            self.assertIn("[REFUSED]", err.getvalue())


class TestTheContactGuard(unittest.TestCase):
    """RED. D-016 ruling 1: a pass flies a contact's duration taken from the computed week.

    The tool recorded --contact and never checked it, so --contact 9 --duration 410 made
    a plan that called itself contact 9 and was 20 s short. Each red case checks that
    NOTHING WAS WRITTEN before it checks the refusal: writing is the harm a refusal
    prevents, and checked second it is never reached when the guard is missing.
    """
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def _attempt(self, contact, duration):
        with tempfile.TemporaryDirectory() as td:
            try:
                gen_pass_plan.generate("TEST-C", "P3_stuck_load", 800, duration, contact,
                                       out_root=td)
                refused = None
            except gen_pass_plan.PlanRefused as exc:
                refused = exc
            written = list(Path(td).iterdir())
        return refused, written

    def test_a_duration_that_is_not_the_contacts_length_is_refused(self):
        refused, written = self._attempt(9, 410)
        self.assertEqual(written, [], f"a refused plan was written: {written}")
        self.assertIsNotNone(refused)
        self.assertIn("430", str(refused))
        self.assertIn("410", str(refused))

    def test_a_contact_past_the_end_of_the_week_is_refused(self):
        refused, written = self._attempt(20, 430)
        self.assertEqual(written, [], f"a refused plan was written: {written}")
        self.assertIsNotNone(refused)
        self.assertIn("20", str(refused))

    def test_contact_zero_is_refused(self):
        refused, written = self._attempt(0, 430)
        self.assertEqual(written, [], f"a refused plan was written: {written}")
        self.assertIsNotNone(refused)

    def test_the_command_line_refuses_a_mismatched_duration_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            old = gen_pass_plan.REPORTS
            gen_pass_plan.REPORTS = Path(td)
            err = io.StringIO()
            try:
                stderr, sys.stderr = sys.stderr, err
                try:
                    rc = gen_pass_plan.main(["--pass-id", "T", "--scenario",
                                             "P3_stuck_load", "--start-at", "800",
                                             "--duration", "410", "--contact", "9"])
                finally:
                    sys.stderr = stderr
                written = list(Path(td).iterdir())
            finally:
                gen_pass_plan.REPORTS = old
        self.assertEqual(written, [], f"a refused plan was written: {written}")
        self.assertEqual(rc, 2)
        self.assertIn("contact 9 is 430 s in the computed week", err.getvalue())


class TestTheContactGuardAccepts(unittest.TestCase):
    """GREEN. The guard must not refuse what the computed week actually contains."""
    verifies = ("HUG-OPS-002",)
    polarity = "green"

    def test_pass_3s_real_invocation_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            path, _text = gen_pass_plan.generate("TEST-P3", "P3_stuck_load", 800, 430, 9,
                                                 out_root=td)
            self.assertTrue(path.is_file())

    def test_the_lengths_are_the_computed_weeks(self):
        """The committed campaign plan's values, reached by computation, not by reading it."""
        lengths = gen_pass_plan.contact_lengths()
        self.assertEqual(len(lengths), 19)
        self.assertEqual({c: lengths[c] for c in (1, 9, 13, 16)},
                         {1: 330.0, 9: 430.0, 13: 450.0, 16: 430.0})

    def test_the_lengths_are_numbered_as_the_campaign_plan_numbers_them(self):
        import gen_campaign
        table = {c["index"]: c["duration_s"] for c in gen_campaign.build()["contacts"]}
        self.assertEqual(gen_pass_plan.contact_lengths(), table)

    def test_the_guard_never_reads_the_campaign_plan(self):
        """The plan is a generated view. A guard that parsed it would trust a copy."""
        reads = []
        real_open, real_path_open = builtins.open, pathlib.Path.open

        def spy_open(file, mode="r", *a, **k):
            reads.append(str(file))
            return real_open(file, mode, *a, **k)

        def spy_path_open(self, mode="r", *a, **k):
            reads.append(str(self))
            return real_path_open(self, mode, *a, **k)

        builtins.open, pathlib.Path.open = spy_open, spy_path_open
        try:
            gen_pass_plan.check_contact(9, 430)
        finally:
            builtins.open, pathlib.Path.open = real_open, real_path_open
        self.assertTrue(reads, "the spy saw no reads at all, so it proves nothing")
        self.assertEqual([r for r in reads if "CAMPAIGN_PLAN" in r], [])


class TestTheConstraints(unittest.TestCase):
    """GREEN. Determinism, blindness to the truth, and the scenario left untouched."""
    verifies = ("HUG-SYS-003", "HUG-SYS-005")
    polarity = "green"

    ARGS = ("P3_stuck_load", 800, 430, 9)

    def test_same_inputs_give_byte_identical_output(self):
        old = os.environ.get("SOURCE_DATE_EPOCH")
        os.environ["SOURCE_DATE_EPOCH"] = "1791936000"
        try:
            outs = []
            for _ in range(2):
                with tempfile.TemporaryDirectory() as td:
                    path, _t = gen_pass_plan.generate("TEST-P3", *self.ARGS, out_root=td)
                    outs.append(path.read_bytes())
        finally:
            if old is None:
                os.environ.pop("SOURCE_DATE_EPOCH", None)
            else:
                os.environ["SOURCE_DATE_EPOCH"] = old
        self.assertEqual(outs[0], outs[1])
        self.assertNotIn(b"\r", outs[0])

    def test_the_tool_never_reads_anything_under_pass_reports(self):
        reads = []
        real_open, real_path_open = builtins.open, pathlib.Path.open

        def spy_open(file, mode="r", *a, **k):
            if "r" in mode or mode == "rb":
                reads.append(str(file))
            return real_open(file, mode, *a, **k)

        def spy_path_open(self, mode="r", *a, **k):
            if "r" in mode:
                reads.append(str(self))
            return real_path_open(self, mode, *a, **k)

        builtins.open, pathlib.Path.open = spy_open, spy_path_open
        try:
            with tempfile.TemporaryDirectory() as td:
                gen_pass_plan.generate("TEST-P3", *self.ARGS, out_root=td)
        finally:
            builtins.open, pathlib.Path.open = real_open, real_path_open
        self.assertTrue(reads, "the spy saw no reads at all, so it proves nothing")
        leaked = [r for r in reads if "pass_reports" in r.replace("\\", "/")]
        self.assertEqual(leaked, [], f"the prediction read the record of a pass: {leaked}")

    def test_no_scenario_file_is_modified(self):
        def digests():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(SCENARIOS.glob("*.yaml"))}
        before = digests()
        with tempfile.TemporaryDirectory() as td:
            gen_pass_plan.generate("TEST-P3", *self.ARGS, out_root=td)
        self.assertEqual(digests(), before)

    def test_the_artefact_carries_every_section_the_operator_needs(self):
        with tempfile.TemporaryDirectory() as td:
            _path, text = gen_pass_plan.generate("TEST-P3", *self.ARGS, out_root=td)
        for needed in ("| Pass | `TEST-P3` |", "| Scenario | `P3_stuck_load` |",
                       "430 s, the length of computed contact 9",
                       "| Acquisition (AOS) | MET 800, chosen for this pass |",
                       "| Loss of signal (LOS) | MET 1230, computed",
                       "| Dictionary version |", "| Generated (UTC) |",
                       "with its faults removed", "the divergence is the",
                       "PROC-001-S06", "PROC-001-S15", "PROC-001-S16",
                       "**430 frames**", "Predicted illumination transitions",
                       "Predicted profile, every 30 s"):
            self.assertIn(needed, text)

    def test_a_fault_that_survives_the_rule_is_refused_not_emitted(self):
        """fault_free() checks its own result rather than trusting the assignment."""
        sc = Scenario.load(SCENARIOS / "P3_stuck_load.yaml")
        sc.faults_active_at = lambda t_s: [{"t_s": 900, "fault": "stuck_load"}]
        with self.assertRaises(RuntimeError):
            gen_pass_plan.fault_free(sc)


if __name__ == "__main__":
    unittest.main()
