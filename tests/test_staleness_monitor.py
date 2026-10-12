#!/usr/bin/env python3
"""The B6 staleness monitor, driven at both polarities (HUG-VER-002, B4).

This exercises THE GENERATED FILE — the one the plugin installs and the operator
container runs — not a copy of its logic. openc3 is not installed here, so its three
imports are stubbed and the run loop is driven with a controlled clock.

The headline case is OF-002. Before the fix, a monitor whose `tlm()` call failed on every
iteration annunciated GREEN -> YELLOW at 10 s -> RED at 30 s with textbook spacing,
because `last_change` was initialised to process start and only a *changed* value moved
it. A monitor that had never once read CDH_FRAME_CNT produced exactly the transcript B6
exists to prove, on a system with no spacecraft and no link.

So the clock now cannot start until a read has SUCCEEDED, and the pre-first-read
condition annunciates as NO_READ. `test_a_monitor_that_can_never_read_stays_no_read` is
the red case: it must fail if that property is removed.
"""
import sys
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MONITOR = (REPO / "gnd" / "openc3" / "plugins" / "openc3-cosmos-huginn"
           / "microservices" / "STALENESS" / "frame_staleness.py")


def _load_monitor(tlm_impl):
    """Import the generated monitor with openc3 stubbed and `tlm` under our control."""
    class _Logger:
        def __init__(self):
            self.lines = []

        def warn(self, msg):
            self.lines.append(msg)

    class _Microservice:
        def __init__(self):
            self.cancel_thread = False
            self.logger = _Logger()
            self.count = 0
            self.scope = "DEFAULT"

        @classmethod
        def class_run(cls):                      # pragma: no cover - not reached here
            pass

    micro_pkg = types.ModuleType("openc3.microservices.microservice")
    micro_pkg.Microservice = _Microservice
    api_pkg = types.ModuleType("openc3.api.tlm_api")
    api_pkg.tlm = tlm_impl
    tm_pkg = types.ModuleType("openc3.utilities.thread_manager")
    tm_pkg.ThreadManager = types.SimpleNamespace(
        instance=lambda: types.SimpleNamespace(shutdown=lambda: None))

    saved = {k: sys.modules.get(k) for k in
             ("openc3", "openc3.microservices", "openc3.microservices.microservice",
              "openc3.api", "openc3.api.tlm_api", "openc3.utilities",
              "openc3.utilities.thread_manager")}
    sys.modules["openc3"] = types.ModuleType("openc3")
    sys.modules["openc3.microservices"] = types.ModuleType("openc3.microservices")
    sys.modules["openc3.microservices.microservice"] = micro_pkg
    sys.modules["openc3.api"] = types.ModuleType("openc3.api")
    sys.modules["openc3.api.tlm_api"] = api_pkg
    sys.modules["openc3.utilities"] = types.ModuleType("openc3.utilities")
    sys.modules["openc3.utilities.thread_manager"] = tm_pkg
    try:
        ns = {"__file__": str(MONITOR), "__name__": "frame_staleness_under_test"}
        exec(compile(MONITOR.read_text(encoding="utf-8"), str(MONITOR), "exec"), ns)
        return ns
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class _Clock:
    """A controlled clock. Each sleep advances time by exactly POLL_S."""

    def __init__(self, poll_s):
        self.now = 1000.0
        self.poll_s = poll_s

    def time(self):
        return self.now

    def sleep(self, _s):
        self.now += self.poll_s


def run_monitor(reader, iterations):
    """Drive the generated run loop `iterations` times. Returns (levels, log lines).

    `reader` is called with the iteration index and returns the counter value, or raises
    to simulate a failed read.
    """
    calls = {"i": 0}

    def tlm(_mnemonic, scope=None):
        i = calls["i"]
        return reader(i)

    ns = _load_monitor(tlm)
    cls = ns["FrameStalenessMicroservice"]
    clock = _Clock(ns["POLL_S"])
    ns["time"].time = clock.time
    ns["time"].sleep = clock.sleep

    service = cls()
    original_sleep = clock.sleep

    def counting_sleep(s):
        original_sleep(s)
        calls["i"] += 1
        if calls["i"] >= iterations:
            service.cancel_thread = True

    ns["time"].sleep = counting_sleep
    service.run()
    return service.logger.lines, ns


class TestTheDeadMonitorCannotProduceTheTranscript(unittest.TestCase):
    """RED — this is OF-002 and it must fail if the NO_READ property is removed."""
    verifies = ("HUG-GND-002",)
    polarity = "red"

    def test_a_monitor_that_can_never_read_stays_no_read(self):
        def always_fails(_i):
            raise RuntimeError("no such packet")

        lines, _ns = run_monitor(always_fails, iterations=60)
        joined = "\n".join(lines)
        self.assertIn("NO_READ", joined,
                      "a monitor that never read must say so")
        for forbidden in ("YELLOW", "RED"):
            self.assertNotIn(
                f"staleness {forbidden}", joined,
                f"a monitor that has NEVER read the counter annunciated {forbidden} "
                f"after 60 s. That is the OF-002 defect: it is indistinguishable from a "
                f"real detected halt, so the alarm would be evidence of nothing.\n"
                f"{joined}")

    def test_the_dead_monitor_ran_long_enough_for_red_to_have_fired(self):
        """Guards the case above from passing because the run was too short."""
        lines, ns = run_monitor(lambda _i: (_ for _ in ()).throw(RuntimeError()),
                                iterations=60)
        self.assertGreater(60 * ns["POLL_S"], ns["RED_S"],
                           "the run must exceed RED_S or the assertion above is vacuous")


class TestARealHaltIsStillCaught(unittest.TestCase):
    """The property B6 actually claims. If these fail the fix broke the monitor."""
    verifies = ("HUG-GND-002",)

    @staticmethod
    def _halting(i):
        """Advances for 5 s, then holds — a successful read, then a halted counter."""
        return 100 + min(i, 5)

    def test_a_halted_counter_goes_green_then_yellow_then_red(self):
        lines, _ns = run_monitor(self._halting, iterations=60)
        joined = "\n".join(lines)
        self.assertIn("staleness GREEN", joined)
        self.assertIn("staleness YELLOW", joined)
        self.assertIn("staleness RED", joined)
        order = [lvl for lvl in ("GREEN", "YELLOW", "RED")
                 if f"staleness {lvl}" in joined]
        self.assertEqual(order, ["GREEN", "YELLOW", "RED"])

    def test_the_thresholds_are_the_dictionary_s(self):
        lines, ns = run_monitor(self._halting, iterations=60)
        yellow = next(l for l in lines if "staleness YELLOW" in l)
        red = next(l for l in lines if "staleness RED" in l)
        self.assertIn(f"yellow {ns['YELLOW_S']} s", yellow)
        self.assertIn(f"red {ns['RED_S']} s", red)

    def test_a_read_failure_AFTER_a_successful_read_is_a_READ_FAULT_not_staleness(self):
        """**RED, polarity one (OF-006 / D-012).**

        This assertion used to require ``staleness RED`` here, which is the defect itself
        written down as a requirement. A ground-segment read failure and a spacecraft halt
        are different conditions and must not share a vocabulary: a monitor that cannot
        read has no basis for a claim about the spacecraft. Must fail if READ_FAULT is
        removed, and must fail if a staleness level is annunciated while blind.
        """
        def ok_then_fails(i):
            if i < 3:
                return 100 + i
            raise RuntimeError("interface down")

        lines, _ns = run_monitor(ok_then_fails, iterations=60)
        joined = "\n".join(lines)
        self.assertIn("staleness READ_FAULT", joined,
                      "reads failing after a successful read is a GROUND fault and the "
                      "monitor must annunciate it as one")
        for forbidden in ("YELLOW", "RED"):
            self.assertNotIn(
                f"staleness {forbidden}", joined,
                f"the monitor annunciated {forbidden} while unable to read. That is a "
                f"claim about the SPACECRAFT by a process that cannot see it -- OF-006, "
                f"and the reason 'in RED' and 'died an hour ago' produced identical "
                f"output.\n{joined}")

    def test_the_read_fault_run_was_long_enough_for_red_to_have_fired(self):
        """Guards the case above from passing because the run was too short."""
        def ok_then_fails(i):
            if i < 3:
                return 100 + i
            raise RuntimeError("interface down")

        _lines, ns = run_monitor(ok_then_fails, iterations=60)
        self.assertGreater(60 * ns["POLL_S"], ns["RED_S"] + 3 * ns["POLL_S"],
                           "the run must exceed RED_S measured from the last good read, "
                           "or the assertion above passes for the wrong reason")

    def test_the_read_fault_annunciation_names_the_ground_segment(self):
        """The words are the point: the operator must be told which segment is broken."""
        def ok_then_fails(i):
            if i < 3:
                return 100 + i
            raise RuntimeError("interface down")

        lines, _ns = run_monitor(ok_then_fails, iterations=60)
        fault = next(line for line in lines if "READ_FAULT" in line)
        self.assertIn("GROUND-SEGMENT", fault)
        self.assertIn("no staleness claim", fault)

    def test_a_recovered_read_path_is_annunciated_in_its_own_right(self):
        """**RED, polarity two (D-012).**

        Falling straight back to GREEN would tell the operator the spacecraft is healthy
        without ever saying the ground path had been down, and a level either side of an
        unannounced gap is worth nothing. Must fail if the recovery annunciation is
        removed.
        """
        def ok_fails_then_ok(i):
            if i < 3:
                return 100 + i
            if i < 20:
                raise RuntimeError("interface down")
            return 200 + i

        lines, _ns = run_monitor(ok_fails_then_ok, iterations=40)
        joined = "\n".join(lines)
        self.assertIn("staleness READ_FAULT", joined)
        self.assertIn("READ_RECOVERED", joined,
                      "the read path came back and the monitor never said so; the "
                      "operator cannot tell that a gap happened")
        self.assertLess(joined.index("READ_FAULT"), joined.index("READ_RECOVERED"),
                        "recovery must be annunciated after the fault, not before")

    def test_the_level_is_restated_after_recovery_against_working_reads(self):
        """A level from before the outage is not a current statement about the craft."""
        def green_fails_then_green(i):
            if i < 3:
                return 100 + i
            if i < 12:
                raise RuntimeError("interface down")
            return 200 + i

        lines, _ns = run_monitor(green_fails_then_green, iterations=30)
        recovered_at = next(i for i, line in enumerate(lines) if "READ_RECOVERED" in line)
        after = "\n".join(lines[recovered_at + 1:])
        self.assertIn("staleness GREEN", after,
                      "after recovery the monitor must restate the level against reads "
                      "known to be working, even if it is the level it had before")

    def test_staleness_across_a_read_outage_is_not_erased_by_recovery(self):
        """The clock is not reset by the outage, and that is deliberate.

        If the counter genuinely did not advance while the ground path was down, that
        staleness is real, and the monitor observes it on recovery by comparing values
        across the gap. Suppressing the CLAIM during the blind window must not amount to
        forgiving the halt.
        """
        def halted_across_outage(i):
            if i < 3:
                return 100 + i
            if i < 40:
                raise RuntimeError("interface down")
            return 102          # the value it already had: it never advanced

        lines, _ns = run_monitor(halted_across_outage, iterations=60)
        joined = "\n".join(lines)
        after = joined.split("READ_RECOVERED", 1)[1]
        self.assertIn("staleness RED", after,
                      "the counter did not advance across the outage, so on recovery the "
                      "halt is real and must be annunciated; resetting the clock would "
                      "forgive a genuine halt")

    def test_a_counter_that_keeps_advancing_never_alarms(self):
        """GREEN-HOLD. A dead monitor cannot do this, which is what makes it the
        control that distinguishes the two."""
        lines, ns = run_monitor(lambda i: 100 + i, iterations=60)
        joined = "\n".join(lines)
        self.assertNotIn("staleness YELLOW", joined)
        self.assertNotIn("staleness RED", joined)
        self.assertGreater(60 * ns["POLL_S"], ns["RED_S"])

    def test_recovery_returns_to_green(self):
        """Halt, then resume — the monitor must come back rather than latch."""
        def halt_then_resume(i):
            if i < 5:
                return 100 + i
            if i < 45:
                return 105
            return 105 + (i - 45)

        lines, _ns = run_monitor(halt_then_resume, iterations=60)
        levels = [l.split("staleness ")[1].split(":")[0] for l in lines
                  if "staleness " in l]
        self.assertIn("RED", levels)
        self.assertEqual(levels[-1], "GREEN", f"did not recover: {levels}")


class TestTheGeneratedFileIsTheOneUnderTest(unittest.TestCase):
    verifies = ("HUG-GND-001", "HUG-GND-002")

    def test_the_monitor_is_generated_and_not_hand_edited(self):
        src = MONITOR.read_text(encoding="utf-8")
        self.assertIn("GENERATED from defs/tlm_cmd.yaml", src)

    def test_the_thresholds_come_from_defs(self):
        sys.path.insert(0, str(REPO / "tools"))
        import hugdefs
        defs = hugdefs.load_tlm_cmd()
        point = next(p for g in defs["telemetry_groups"] for p in g["points"]
                     if p["limits"]["kind"] == "staleness")
        _lines, ns = run_monitor(lambda i: 100 + i, iterations=2)
        self.assertEqual(ns["YELLOW_S"], int(point["limits"]["yellow_s"]))
        self.assertEqual(ns["RED_S"], int(point["limits"]["red_s"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
