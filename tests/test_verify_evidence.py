#!/usr/bin/env python3
"""The evidence-integrity check, at both polarities (HUG-VER-002, B4).

The manifests carry a sha256 per artifact so that what the gate reads can be shown to be
what the demonstration produced. Nothing recomputed them, and they had already stopped
matching: evidence captured on Windows held CRLF, `.gitattributes` normalised the whole
repository to LF, and git stored a translated copy. One captured transcript hashed
`634ec09d…` in the working tree and `43b38324…` as git would check it out. On a fresh
clone — how a reviewer actually reads this repository — the digests would not have
verified and nothing would have said so.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import evidence as ev_mod                                        # noqa: E402
import verify_evidence as ve                                     # noqa: E402
from evidence import Evidence                                    # noqa: E402


class VerifyTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = ev_mod.EVIDENCE_ROOT
        ev_mod.EVIDENCE_ROOT = Path(self._tmp.name) / "evidence"

    def tearDown(self):
        ev_mod.EVIDENCE_ROOT = self._saved
        self._tmp.cleanup()

    def _attempt(self, demo_id="B6", text="captured bytes\n", result="PASS"):
        with Evidence(demo_id, obligation="B6", requirement="HUG-GND-002") as ev:
            ev.capture_text("a.txt", text)
            ev.capture_text("b.txt", "more\n")
            ev.record(result, "detail")
        return ev


class TestTamperingIsCaught(VerifyTestCase):
    """RED."""
    verifies = ("HUG-VER-003",)
    polarity = "red"

    def test_an_edited_artifact_fails(self):
        ev = self._attempt()
        (ev.dir / "artifacts" / "a.txt").write_bytes(b"edited after the fact\n")
        ok, summary, problems = ve.scan()
        self.assertFalse(ok)
        self.assertTrue(any("a.txt" in p for p in problems))

    def test_a_line_ending_translation_fails(self):
        """The exact defect: same text, different bytes. A check comparing content
        rather than bytes would pass this and miss what actually happened."""
        ev = self._attempt(text="line one\nline two\n")
        path = ev.dir / "artifacts" / "a.txt"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        ok, _summary, problems = ve.scan()
        self.assertFalse(ok, "a CRLF translation of the same text was not caught")
        self.assertTrue(any("a.txt" in p for p in problems))

    def test_a_missing_artifact_fails(self):
        ev = self._attempt()
        (ev.dir / "artifacts" / "a.txt").unlink()
        ok, _summary, problems = ve.scan()
        self.assertFalse(ok)
        self.assertTrue(any("absent from disk" in p for p in problems))

    def test_the_failure_names_both_digests(self):
        """A reader must be able to tell tampering from translation without guessing."""
        ev = self._attempt()
        (ev.dir / "artifacts" / "a.txt").write_bytes(b"x\n")
        _ok, _summary, problems = ve.scan()
        problem = next(p for p in problems if "a.txt" in p)
        self.assertIn("manifest records", problem)
        self.assertIn("on disk is", problem)


class TestVacuousPassesAreRefused(VerifyTestCase):
    """RED. A scan that finds nothing must not report success over an empty set."""
    verifies = ("HUG-VER-003",)
    polarity = "red"

    def test_an_empty_evidence_root_fails(self):
        ev_mod.EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
        ok, summary, _problems = ve.scan()
        self.assertFalse(ok)
        self.assertIn("no evidence manifests", summary)

    def test_a_missing_evidence_root_fails(self):
        ok, summary, _problems = ve.scan()
        self.assertFalse(ok)
        self.assertIn("does not exist", summary)

    def test_a_manifest_listing_no_artifacts_fails(self):
        ev = self._attempt()
        manifest = ev.dir / "MANIFEST.md"
        text = manifest.read_text(encoding="utf-8")
        stripped = "\n".join(l for l in text.split("\n")
                             if not l.startswith("| `artifacts/"))
        manifest.write_bytes(stripped.encode("utf-8"))
        ok, _summary, problems = ve.scan()
        self.assertFalse(ok)
        self.assertTrue(any("lists no artifacts" in p for p in problems))


class TestIntactEvidenceVerifies(VerifyTestCase):
    """GREEN."""
    verifies = ("HUG-VER-003",)
    polarity = "green"

    def test_an_untouched_attempt_passes(self):
        self._attempt()
        ok, summary, problems = ve.scan()
        self.assertTrue(ok, f"{summary} {problems}")
        self.assertIn("match the digests", summary)

    def test_every_attempt_is_checked_not_just_the_latest(self):
        """An earlier attempt is evidence too, and a check that only looked at the
        newest would let the record rot behind it."""
        first = self._attempt(text="first\n", result="INSTRUMENT_FAULT")
        self._attempt(text="second\n")
        (first.dir / "artifacts" / "a.txt").write_bytes(b"tampered\n")
        ok, _summary, problems = ve.scan()
        self.assertFalse(ok, "tampering with attempt-001 was not caught")
        self.assertTrue(any("attempt-001" in str(p) or "a.txt" in p for p in problems))

    def test_the_count_is_not_zero(self):
        """Guards the green case from passing because the scan found nothing."""
        self._attempt()
        _ok, summary, _problems = ve.scan()
        self.assertNotIn("0 artifact", summary)


class TestTheRealEvidenceVerifies(unittest.TestCase):
    """The repository's own committed evidence, checked as a reviewer would."""
    verifies = ("HUG-VER-003",)

    def test_committed_evidence_matches_its_manifests(self):
        ok, summary, problems = ve.scan()
        self.assertTrue(ok, f"{summary}\n" + "\n".join(problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
