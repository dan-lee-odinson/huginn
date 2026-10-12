#!/usr/bin/env python3
"""Attempts are append-only, and the manifest is the authoritative outcome.

Two apparatus properties, both earned by the Phase 3 record rather than reasoned into
existence.

APPEND-ONLY. The evidence directory used to be `evidence/<demo_id>/`, reused on every
run, so a re-run wrote straight over its predecessor. That is how the contaminated B6 and
B14 attempts lost their artifacts and had to be reconstructed by hand from a diagnosis
transcript. An overwritten attempt is indistinguishable from an attempt that never
happened, which is the failure the whole evidence discipline exists to prevent — D-008
stopped evidence expiring, D-011 stopped a failed collection being recorded as a verdict
about the subject, and this stops a successor erasing what its predecessor saw.

AUTHORITATIVE OUTCOME. The runner printed `'PASS' if returned_value else 'FAIL'`, so a
demonstration that recorded INSTRUMENT_FAULT — and returned False, correctly — was
announced as FAIL. That states about the subject exactly what the manifest had just
declined to state.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import evidence as ev_mod                                        # noqa: E402
from evidence import Evidence                                    # noqa: E402


class AttemptTestCase(unittest.TestCase):
    """Each test gets its own evidence root and its own WRITTEN registry."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved_root = ev_mod.EVIDENCE_ROOT
        ev_mod.EVIDENCE_ROOT = Path(self._tmp.name) / "evidence"
        self._saved_written = list(ev_mod.WRITTEN)
        ev_mod.WRITTEN.clear()

    def tearDown(self):
        ev_mod.WRITTEN[:] = self._saved_written
        ev_mod.EVIDENCE_ROOT = self._saved_root
        self._tmp.cleanup()

    def _run(self, demo_id, result, text):
        """One complete attempt. The directory is NOT pinned — the allocation under
        test is the one the real runs use."""
        with Evidence(demo_id, obligation="B6",
                      requirement="HUG-GND-002") as ev:
            ev.capture_text("a.txt", text)
            ev.record(result, "detail")
        return ev


class TestAttemptsAreAppendOnly(AttemptTestCase):
    verifies = ("HUG-VER-003",)

    def test_the_first_run_is_attempt_001(self):
        ev = self._run("B6", "INSTRUMENT_FAULT", "first\n")
        self.assertEqual(ev.dir.name, "attempt-001")
        self.assertEqual(ev.dir.parent.name, "B6")

    def test_a_second_run_gets_its_own_directory(self):
        first = self._run("B6", "INSTRUMENT_FAULT", "first\n")
        second = self._run("B6", "PASS", "second\n")
        self.assertEqual(first.dir.name, "attempt-001")
        self.assertEqual(second.dir.name, "attempt-002")

    def test_the_earlier_attempt_survives_untouched(self):
        """RED. This is the property the change exists for."""
        first = self._run("B6", "INSTRUMENT_FAULT", "the bytes the first run saw\n")
        artifact_before = (first.dir / "artifacts" / "a.txt").read_bytes()
        manifest_before = (first.dir / "MANIFEST.md").read_bytes()

        self._run("B6", "PASS", "the bytes the second run saw\n")

        self.assertEqual((first.dir / "artifacts" / "a.txt").read_bytes(),
                         artifact_before,
                         "the second attempt overwrote the first attempt's artifact")
        self.assertEqual((first.dir / "MANIFEST.md").read_bytes(), manifest_before,
                         "the second attempt overwrote the first attempt's manifest")
        self.assertIn(b"INSTRUMENT_FAULT", manifest_before,
                      "the first attempt's own outcome must still be readable")

    def test_ten_attempts_all_survive_and_stay_ordered(self):
        """Numbering must not collapse or wrap once it leaves single digits."""
        for i in range(1, 11):
            self._run("B6", "FAIL", f"attempt {i}\n")
        names = sorted(p.name for p in (ev_mod.EVIDENCE_ROOT / "B6").iterdir())
        self.assertEqual(names, [f"attempt-{i:03d}" for i in range(1, 11)])
        for i in range(1, 11):
            body = (ev_mod.EVIDENCE_ROOT / "B6" / f"attempt-{i:03d}"
                    / "artifacts" / "a.txt").read_text(encoding="utf-8")
            self.assertEqual(body, f"attempt {i}\n")

    def test_writing_into_an_existing_attempt_raises(self):
        """RED for the guard itself: even a caller that pins a directory cannot write
        over a manifest that already recorded what a run saw."""
        first = self._run("B6", "PASS", "x\n")
        again = Evidence("B6", obligation="B6", requirement="HUG-GND-002")
        again.dir = first.dir
        again.artifacts_dir = first.dir / "artifacts"
        with self.assertRaises(ev_mod.EvidenceError):
            with again:
                pass

    def test_separate_demonstrations_number_independently(self):
        self._run("B6", "PASS", "x\n")
        self._run("B6", "PASS", "y\n")
        other = self._run("B14", "PASS", "z\n")
        self.assertEqual(other.dir.name, "attempt-001")

    def test_every_attempt_appears_in_the_summary(self):
        self._run("B6", "INSTRUMENT_FAULT", "first\n")
        self._run("B6", "PASS", "second\n")
        rows = [r for r in ev_mod.summary() if r["demo_id"] == "B6"]
        self.assertEqual([r["attempt"] for r in rows],
                         ["attempt-001", "attempt-002"])
        self.assertEqual([r["result"] for r in rows], ["INSTRUMENT_FAULT", "PASS"])

    def test_the_manifest_names_its_own_attempt(self):
        ev = self._run("B6", "PASS", "x\n")
        self.assertIn("| Attempt | `attempt-001` |",
                      (ev.dir / "MANIFEST.md").read_text(encoding="utf-8"))

    def test_the_empty_directory_rule_still_holds_per_attempt(self):
        """GREEN-adjacent: allocating a directory must not become a way to leave an
        empty claim behind."""
        with self.assertRaises(ev_mod.EvidenceError):
            with Evidence("B6", obligation="B6", requirement="HUG-GND-002") as ev:
                ev.record("PASS", "captured nothing")


class TestTheRecordedOutcomeIsAuthoritative(AttemptTestCase):
    verifies = ("HUG-VER-003",)

    def test_writing_a_manifest_records_the_outcome(self):
        self._run("B6", "INSTRUMENT_FAULT", "x\n")
        self.assertEqual(ev_mod.WRITTEN[-1]["result"], "INSTRUMENT_FAULT")
        self.assertEqual(ev_mod.WRITTEN[-1]["demo_id"], "B6")
        self.assertEqual(ev_mod.WRITTEN[-1]["attempt"], "attempt-001")

    def test_the_registry_and_the_manifest_cannot_disagree(self):
        """RED. If these two can differ, the registry is not the record and a runner
        reading it is back to re-deriving a verdict."""
        for result in ("PASS", "FAIL", "INSTRUMENT_FAULT"):
            ev = self._run("D", result, "x\n")
            manifest = (ev.dir / "MANIFEST.md").read_text(encoding="utf-8")
            self.assertIn(f"**{result}**", manifest)
            self.assertEqual(ev_mod.WRITTEN[-1]["result"], result)

    def test_a_crashed_demonstration_still_records_its_outcome(self):
        """A runner must be able to report something truthful about a run that blew
        up, rather than inventing one."""
        try:
            with Evidence("B6", obligation="B6", requirement="HUG-GND-002") as ev:
                ev.capture_text("a.txt", "x\n")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertEqual(ev_mod.WRITTEN[-1]["result"], "FAIL")

    def test_instrument_fault_is_not_reported_as_a_failure_of_the_subject(self):
        """RED — the runner-vocabulary defect, at the level the runner reads.

        A demonstration recording INSTRUMENT_FAULT returns False. If the outcome a
        runner reports is derived from that boolean it says FAIL, which is a claim about
        the subject the manifest deliberately does not make.
        """
        self._run("B6", "INSTRUMENT_FAULT", "x\n")
        recorded = ev_mod.WRITTEN[-1]["result"]
        self.assertNotEqual(recorded, "FAIL")
        self.assertNotEqual(recorded, "PASS")
        self.assertEqual(recorded, "INSTRUMENT_FAULT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
