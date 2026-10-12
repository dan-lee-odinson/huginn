#!/usr/bin/env python3
"""B14's verdict, driven from stored bytes with no ground system (D-012, D-013 item 1).

Written to close OF-012. B6 and B11 each had a verdict function whose red and green
cases run in the gate; B14 — the obligation that discharges HUG-SYS-006 — had none, so
OF-008's direction claim had no covering case and the repair to its controls had nothing
that would fail if it were reverted.

EVERY RED CASE BELOW WITNESSES THE ACTUAL FAILURE MODE, not a plausible neighbour of it.
The two that matter are `TestAControlThatNeverRan`: they strip the evidence that the
reader executed while leaving the zero-count line the original controls were scored on
intact. That is precisely the state B14 was in when it reported PASS — a script that died
of a SyntaxError produces the same zero as a reader that ran and correctly refused — and
a verdict that accepts it has learned nothing from OF-008.

The GREEN baseline is the real archived evidence, read off disk. A synthetic green would
only prove the function accepts fixtures the same author wrote.
"""
import hashlib
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from demonstrate import b14_verdict                                  # noqa: E402

ATTEMPT = REPO / "verification" / "evidence" / "B14-native-log-playback" / "attempt-002"
ART = ATTEMPT / "artifacts"


def archived(name):
    return (ART / name).read_text(encoding="utf-8", errors="replace")


def archived_gz_digest():
    return hashlib.sha256((ART / "ground-native-telemetry.bin.gz").read_bytes()).hexdigest()


def inputs(**over):
    """The real archive, with named substitutions. Every red case is one edit from green."""
    base = {
        "playback_text": archived("playback.txt"),
        "simulator_off_text": archived("simulator-off.txt"),
        "decompression_text": archived("decompression.txt"),
        "of005_text": archived("of005-file-bound-control.txt"),
        "compressed_text": archived("compressed-refused.txt"),
        "archived_gz_sha256": archived_gz_digest(),
    }
    base.update(over)
    return base


class TestTheArchivedEvidencePasses(unittest.TestCase):
    """GREEN, off disk. If this fails every red case below is meaningless."""
    verifies = ("HUG-SYS-006", "HUG-GND-004")
    polarity = "green"

    def test_the_committed_b14_evidence_satisfies_the_verdict(self):
        ok, reasons = b14_verdict(**inputs())
        self.assertTrue(ok, f"the archived B14 evidence does not verify: {reasons}")

    def test_the_verdict_is_computable_from_the_archive_alone(self):
        """No ground system, no simulator, no network — only bytes in the repository."""
        self.assertTrue(ATTEMPT.is_dir())
        for name in ("playback.txt", "simulator-off.txt", "decompression.txt",
                     "of005-file-bound-control.txt", "compressed-refused.txt",
                     "ground-native-telemetry.bin.gz"):
            with self.subTest(artifact=name):
                self.assertTrue((ART / name).is_file(),
                                f"{name} is not in the archive, so the verdict is not "
                                f"computable from the archive alone")


class TestAControlThatNeverRan(unittest.TestCase):
    """RED — OF-008's exact shape, and the reason this file exists.

    Both of B14's original controls were scored on an absence: `packets returned: 0`
    and `refused: True`. Both scripts died of a SyntaxError and never ran, producing
    that same absence. These cases remove only the evidence that the reader executed —
    the `REFUSED <ExceptionType>` line — and leave the absence intact. A verdict that
    still passes is a verdict that would have certified B14 in its broken state.
    """
    verifies = ("HUG-SYS-006",)
    polarity = "red"

    def test_the_of005_control_with_no_evidence_it_ever_ran(self):
        stripped = re.sub(r"^REFUSED.*$", "", archived("of005-file-bound-control.txt"),
                          flags=re.MULTILINE)
        self.assertIn("packets returned: 0", stripped,
                      "the absence-based clause must still be satisfied, or this case "
                      "tests something easier than the defect")
        ok, reasons = b14_verdict(**inputs(of005_text=stripped))
        self.assertFalse(ok)
        self.assertTrue(any("never ran" in r or "REFUSED" in r for r in reasons), reasons)

    def test_the_compressed_control_with_no_evidence_it_ever_ran(self):
        stripped = re.sub(r"^REFUSED.*$", "", archived("compressed-refused.txt"),
                          flags=re.MULTILINE)
        self.assertIn("refused: True", stripped)
        ok, reasons = b14_verdict(**inputs(compressed_text=stripped))
        self.assertFalse(ok)
        self.assertTrue(any("never ran" in r or "REFUSED" in r for r in reasons), reasons)

    def test_an_entirely_empty_control_artifact(self):
        ok, reasons = b14_verdict(**inputs(of005_text=""))
        self.assertFalse(ok)

    def test_a_control_that_failed_for_a_different_reason(self):
        """A reader that died of the wrong exception refused nothing about the path."""
        wrong = archived("of005-file-bound-control.txt").replace(
            "REFUSED FileNotFoundError", "REFUSED SyntaxError")
        ok, reasons = b14_verdict(**inputs(of005_text=wrong))
        self.assertFalse(ok)
        self.assertTrue(any("different reason" in r for r in reasons), reasons)


class TestThePlaybackMustHaveReadTheNativeLog(unittest.TestCase):
    """RED — OF-005's claim: the packets came from the named file, not a database."""
    verifies = ("HUG-SYS-006",)
    polarity = "red"

    def test_a_playback_that_returned_no_packets(self):
        ok, reasons = b14_verdict(**inputs(
            playback_text=archived("playback.txt").replace("PACKETS 760", "PACKETS 0")))
        self.assertFalse(ok)
        self.assertTrue(any("0 packets" in r for r in reasons), reasons)

    def test_a_playback_with_no_packet_count_at_all(self):
        ok, reasons = b14_verdict(**inputs(
            playback_text=archived("playback.txt").replace("PACKETS 760", "")))
        self.assertFalse(ok)
        self.assertTrue(any("no PACKETS count" in r for r in reasons), reasons)

    def test_a_playback_that_read_the_compressed_object(self):
        """The reader cannot parse a .gz, so packets from one came from elsewhere."""
        ok, reasons = b14_verdict(**inputs(
            playback_text=archived("playback.txt").replace(
                "read: /tmp/b14-native-telemetry.bin",
                "read: /tmp/b14-native-telemetry.bin.gz")))
        self.assertFalse(ok)
        self.assertTrue(any("compressed object" in r for r in reasons), reasons)


class TestTheSourceMustHaveBeenGone(unittest.TestCase):
    """RED — otherwise 'playback' is indistinguishable from live telemetry."""
    verifies = ("HUG-SYS-006",)
    polarity = "red"

    def test_the_simulator_still_accepting_connections(self):
        ok, reasons = b14_verdict(**inputs(
            simulator_off_text=archived("simulator-off.txt").replace(
                "accepting connections: False", "accepting connections: True")))
        self.assertFalse(ok)
        self.assertTrue(any("live telemetry" in r for r in reasons), reasons)

    def test_the_ground_interface_still_connected(self):
        ok, reasons = b14_verdict(**inputs(
            simulator_off_text=archived("simulator-off.txt").replace(
                "HUGINN_INT state: ATTEMPTING", "HUGINN_INT state: CONNECTED")))
        self.assertFalse(ok)
        self.assertTrue(any("CONNECTED" in r for r in reasons), reasons)

    def test_no_record_of_the_source_state_at_all(self):
        ok, reasons = b14_verdict(**inputs(simulator_off_text=""))
        self.assertFalse(ok)
        self.assertGreaterEqual(len(reasons), 2)


class TestTheChainToTheArchivedBytes(unittest.TestCase):
    """RED — OF-009's lesson: a digest nobody recomputes binds nothing."""
    verifies = ("HUG-SYS-006",)
    polarity = "red"

    def test_a_decompression_record_for_a_different_gz(self):
        other = "f" * 64
        ok, reasons = b14_verdict(**inputs(
            decompression_text=archived("decompression.txt").replace(
                archived_gz_digest(), other)))
        self.assertFalse(ok)
        self.assertTrue(any("not the digest" in r for r in reasons), reasons)

    def test_no_cosmos_header_shown(self):
        ok, reasons = b14_verdict(**inputs(
            decompression_text=archived("decompression.txt").replace("COSMOS5_", "")))
        self.assertFalse(ok)
        self.assertTrue(any("COSMOS5_" in r for r in reasons), reasons)

    def test_no_digest_recorded_for_the_compressed_object(self):
        ok, reasons = b14_verdict(**inputs(decompression_text="nothing here"))
        self.assertFalse(ok)


class TestTheVerdictDetectsRatherThanRaises(unittest.TestCase):
    """OF-011's lesson, applied to this function.

    A check that dies on malformed input is indistinguishable from one that detected a
    violation: both fail to return true. G11 was CAUGHT by a KeyError for exactly this
    reason and the self-test scored the crash as a working red case. Every clause here
    must REPORT.
    """
    verifies = ("HUG-SYS-006",)
    polarity = "red"

    def test_every_artifact_empty_reports_and_does_not_raise(self):
        ok, reasons = b14_verdict("", "", "", "", "", "")
        self.assertFalse(ok)
        self.assertTrue(reasons)

    def test_none_inputs_report_and_do_not_raise(self):
        ok, reasons = b14_verdict(None, None, None, None, None, None)
        self.assertFalse(ok)
        self.assertTrue(reasons)

    def test_binary_garbage_reports_and_does_not_raise(self):
        junk = "\x00\xff� not a log at all \x01"
        ok, reasons = b14_verdict(junk, junk, junk, junk, junk, junk)
        self.assertFalse(ok)
        self.assertTrue(reasons)


class TestValidVariationsAreNotFlagged(unittest.TestCase):
    """GREEN — the verdict must read for the condition, not for a spelling."""
    verifies = ("HUG-SYS-006",)
    polarity = "green"

    def test_a_different_packet_count_still_passes(self):
        ok, reasons = b14_verdict(**inputs(
            playback_text=archived("playback.txt").replace("PACKETS 760", "PACKETS 12")))
        self.assertTrue(ok, reasons)

    def test_a_different_non_connected_interface_state_still_passes(self):
        ok, reasons = b14_verdict(**inputs(
            simulator_off_text=archived("simulator-off.txt").replace(
                "HUGINN_INT state: ATTEMPTING", "HUGINN_INT state: DISCONNECTED")))
        self.assertTrue(ok, reasons)

    def test_extra_log_noise_around_the_controls_still_passes(self):
        noisy = ("warning: unrelated container chatter\n"
                 + archived("of005-file-bound-control.txt")
                 + "\ntrailing diagnostic output\n")
        ok, reasons = b14_verdict(**inputs(of005_text=noisy))
        self.assertTrue(ok, reasons)


if __name__ == "__main__":
    unittest.main()
