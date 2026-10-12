#!/usr/bin/env python3
"""B6's verdict, driven from stored bytes with no ground system (D-012).

The ruling requires the verdict to be **computable from the archived evidence alone** —
live polls pace a demonstration but never decide it. Before the patch the verdict read
`saw_green`, `saw_yellow`, `saw_red`, `froze` and `link_live`: booleans returned by
`wait_for` against a live connection. Those decide when to stop waiting, which is pacing.
They were also deciding PASS, which is not, and a run could therefore report PASS on
observations that afterwards existed nowhere — the operator log rotates, and the evidence
directory held nothing anyone could recompute the answer from.

Every case here feeds `b6_verdict` archived text and nothing else. That is only possible
because the verdict is a pure function of the archive; a verdict reading live state could
not be red-cased at all without a running ground segment, which is why it never was.
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from demonstrate import b6_verdict, measurements_in  # noqa: E402

SINCE = "2026-08-06T12:00:00.000Z"


def _line(stamp, level, extra="no advance for 0.0 s"):
    """One operator-log line in the shape the real log emits: JSON after a prefix."""
    payload = {"@timestamp": stamp,
               "message": f"CDH_FRAME_CNT staleness {level}: {extra}"}
    return f"2026-08-06 12:00:00 INFO  {json.dumps(payload)}"


def _slice(*levels_at):
    return "\n".join(_line(stamp, level) for stamp, level in levels_at) + "\n"


GOOD_SLICE = _slice(
    ("2026-08-06T12:00:05.000Z", "GREEN"),
    ("2026-08-06T12:02:30.000Z", "YELLOW"),
    ("2026-08-06T12:02:50.000Z", "RED"),
)

GOOD_MEASUREMENTS = (
    "# B6 verdict inputs\n"
    f"monitor_restarted_at: {SINCE}\n"
    "counter_before_hold: 1200\n"
    "counter_after_hold: 1580\n"
    "hold_s: 38.0\n"
    "red_s: 30\n"
    "hold_ended_at: 2026-08-06T12:01:00.000Z\n"
    "counter_froze: True\n"
    "interface_state_at_halt: CONNECTED\n"
    "interface_state_at_alarm: CONNECTED\n"
    "rxcnt: 4210\n"
    "txcnt: 12\n"
)


class TestTheGoodRunPasses(unittest.TestCase):
    """The control. If this fails, every red case below passes for the wrong reason."""
    verifies = ("HUG-GND-002",)

    def test_a_complete_archive_yields_pass(self):
        ok, reasons = b6_verdict(GOOD_SLICE, GOOD_MEASUREMENTS, SINCE)
        self.assertTrue(ok, f"the good archive must pass: {reasons}")
        self.assertEqual(reasons, [])


class TestTheVerdictIsComputedFromTheArchive(unittest.TestCase):
    """RED — each case removes something from the ARCHIVE and requires FAIL.

    A verdict that consulted live state would be unmoved by these, because the archive
    is not where it was looking.
    """
    verifies = ("HUG-VER-003",)
    polarity = "red"

    def test_a_missing_level_in_the_slice_fails(self):
        for dropped in ("GREEN", "YELLOW", "RED"):
            with self.subTest(dropped=dropped):
                thinned = "\n".join(l for l in GOOD_SLICE.split("\n")
                                    if f"staleness {dropped}" not in l)
                ok, reasons = b6_verdict(thinned, GOOD_MEASUREMENTS, SINCE)
                self.assertFalse(ok)
                self.assertTrue(any(dropped in r for r in reasons), reasons)

    def test_levels_out_of_order_fail(self):
        out_of_order = _slice(
            ("2026-08-06T12:00:05.000Z", "RED"),
            ("2026-08-06T12:02:30.000Z", "YELLOW"),
            ("2026-08-06T12:02:50.000Z", "GREEN"),
        )
        ok, reasons = b6_verdict(out_of_order, GOOD_MEASUREMENTS, SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("out of order" in r for r in reasons), reasons)

    def test_annunciations_from_before_this_run_do_not_count(self):
        """The window is the point: an inherited transcript is not this run's evidence."""
        stale = _slice(
            ("2026-08-06T11:00:00.000Z", "GREEN"),
            ("2026-08-06T11:30:00.000Z", "YELLOW"),
            ("2026-08-06T11:45:00.000Z", "RED"),
        )
        ok, reasons = b6_verdict(stale, GOOD_MEASUREMENTS, SINCE)
        self.assertFalse(ok, "levels predating the run must not discharge it")
        # `in r`, not a bare truthy string: the first draft omitted it and the filter
        # matched every reason, which would have passed whatever the verdict returned.
        missing = [r for r in reasons if "annunciation in the archived" in r]
        self.assertEqual(len(missing), 3, f"all three levels must be missing: {reasons}")

    def test_an_empty_slice_fails(self):
        ok, reasons = b6_verdict("", GOOD_MEASUREMENTS, SINCE)
        self.assertFalse(ok)


class TestTheGreenHoldControlIsEnforcedFromTheArchive(unittest.TestCase):
    verifies = ("HUG-VER-002",)

    def test_a_counter_that_did_not_advance_during_the_hold_fails(self):
        frozen = GOOD_MEASUREMENTS.replace("counter_after_hold: 1580",
                                           "counter_after_hold: 1200")
        ok, reasons = b6_verdict(GOOD_SLICE, frozen, SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("did not advance" in r for r in reasons), reasons)

    def test_a_hold_shorter_than_red_s_fails(self):
        """A silent monitor also raises no alarm in a window too short to alarm in."""
        short = GOOD_MEASUREMENTS.replace("hold_s: 38.0", "hold_s: 12.0")
        ok, reasons = b6_verdict(GOOD_SLICE, short, SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("did not exceed RED_S" in r for r in reasons), reasons)

    def test_an_alarm_inside_the_hold_window_fails(self):
        alarmed = _slice(
            ("2026-08-06T12:00:05.000Z", "GREEN"),
            ("2026-08-06T12:00:40.000Z", "YELLOW"),   # inside hold_ended_at 12:01:00
            ("2026-08-06T12:02:50.000Z", "RED"),
        )
        ok, reasons = b6_verdict(alarmed, GOOD_MEASUREMENTS, SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("during the GREEN-HOLD" in r for r in reasons), reasons)

    def test_missing_measurements_fail_rather_than_default(self):
        ok, reasons = b6_verdict(GOOD_SLICE, "# nothing here\n", SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("do not carry the GREEN-HOLD" in r for r in reasons), reasons)


class TestTheHaltAttributionIsEnforcedFromTheArchive(unittest.TestCase):
    verifies = ("HUG-GND-002",)

    def test_a_counter_that_never_froze_fails(self):
        no_freeze = GOOD_MEASUREMENTS.replace("counter_froze: True",
                                              "counter_froze: False")
        ok, reasons = b6_verdict(GOOD_SLICE, no_freeze, SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("not observed to freeze" in r for r in reasons), reasons)

    def test_a_dropped_link_at_the_alarm_fails(self):
        """RED for the control B6 actually turns on: an absence of frames on a LIVE link
        is the claim. A disconnected link makes the alarm mean something else."""
        dropped = GOOD_MEASUREMENTS.replace("interface_state_at_alarm: CONNECTED",
                                            "interface_state_at_alarm: DISCONNECTED")
        ok, reasons = b6_verdict(GOOD_SLICE, dropped, SINCE)
        self.assertFalse(ok)
        self.assertTrue(any("live link" in r for r in reasons), reasons)


class TestAReadFaultBreaksTheObservation(unittest.TestCase):
    """D-012 reaching the verdict: a mid-run read fault is not one continuous look."""
    verifies = ("HUG-GND-002",)

    def test_a_read_fault_in_the_transcript_fails(self):
        interrupted = _slice(
            ("2026-08-06T12:00:05.000Z", "GREEN"),
            ("2026-08-06T12:01:30.000Z", "READ_FAULT"),
            ("2026-08-06T12:02:30.000Z", "YELLOW"),
            ("2026-08-06T12:02:50.000Z", "RED"),
        )
        ok, reasons = b6_verdict(interrupted, GOOD_MEASUREMENTS, SINCE)
        self.assertFalse(ok, "levels either side of a read fault are not one observation")
        self.assertTrue(any("READ_FAULT" in r for r in reasons), reasons)


class TestTheMeasurementsFormatIsReDerivable(unittest.TestCase):
    verifies = ("HUG-VER-003",)

    def test_comments_and_blanks_are_ignored(self):
        parsed = measurements_in("# a comment\n\nkey: value\nother:  spaced \n")
        self.assertEqual(parsed, {"key": "value", "other": "spaced"})

    def test_the_archived_format_round_trips(self):
        parsed = measurements_in(GOOD_MEASUREMENTS)
        self.assertEqual(parsed["counter_before_hold"], "1200")
        self.assertEqual(parsed["interface_state_at_alarm"], "CONNECTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
