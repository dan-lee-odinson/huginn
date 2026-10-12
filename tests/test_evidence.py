#!/usr/bin/env python3
"""The evidence harness: gate evidence as preserved artifact (owner ruling D-008).

The harness exists to make one failure mode impossible — a demonstration that appears
to have been performed, with nothing preserved to show it. Every property below is
about that, and each is red-cased: it is not enough that the harness writes a manifest
when things go well.
"""
import sys
import unittest
from pathlib import Path

from harness import REPO

sys.path.insert(0, str(REPO / "tools"))

import evidence as ev_mod  # noqa: E402
from evidence import Evidence, EvidenceError  # noqa: E402


class EvidenceTestCase(unittest.TestCase):
    """Each test gets its own evidence root, so no test writes into the real one."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._saved_root = ev_mod.EVIDENCE_ROOT
        ev_mod.EVIDENCE_ROOT = Path(self._tmp.name) / "evidence"

    def tearDown(self):
        ev_mod.EVIDENCE_ROOT = self._saved_root
        self._tmp.cleanup()

    def _evidence(self, demo_id="DEMO", **kw):
        """A real Evidence against the temporary root.

        The directory is NOT pinned here. It used to be, which meant every test wrote to
        `<root>/<demo_id>/` and none of them exercised the attempt allocation the real
        runs use — the tests would have kept passing while the append-only property was
        broken."""
        return Evidence(demo_id, obligation=kw.pop("obligation", "B14"),
                        requirement=kw.pop("requirement", "HUG-SYS-006"), **kw)


class TestEvidenceIsPreserved(EvidenceTestCase):
    verifies = ("HUG-VER-003",)

    def test_a_completed_demonstration_writes_artifacts_and_a_manifest(self):
        with self._evidence("B14-playback") as ev:
            ev.capture_text("console.txt", "played back with the simulator stopped")
            ev.record("PASS", "native log replayed in the ground system")
        manifest = (ev.dir / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("**PASS**", manifest)
        self.assertIn("B14", manifest)
        self.assertIn("HUG-SYS-006", manifest)
        self.assertTrue((ev.artifacts_dir / "console.txt").is_file())

    def test_every_artifact_is_digested(self):
        """The digest is what binds what the gate reads to what the demonstration
        produced. Without it the manifest is a list of filenames."""
        import hashlib
        with self._evidence() as ev:
            ev.capture_text("out.txt", "measured value 1.80 A")
            ev.record("PASS")
        raw = (ev.artifacts_dir / "out.txt").read_bytes()
        self.assertIn(hashlib.sha256(raw).hexdigest(),
                      (ev.dir / "MANIFEST.md").read_text(encoding="utf-8"))

    def test_a_captured_file_is_copied_not_referenced(self):
        """A path into a container volume or a temp directory is not evidence — it is
        a pointer to something that will not be there later."""
        source = Path(self._tmp.name) / "native.log"
        source.write_bytes(b"ground system native log content")
        with self._evidence() as ev:
            ev.capture_file(source, "ground-native.log")
            ev.record("PASS")
        copied = ev.artifacts_dir / "ground-native.log"
        self.assertTrue(copied.is_file())
        source.unlink()                      # the original goes away, as a volume would
        self.assertTrue(copied.is_file(), "the artifact did not survive its source")
        self.assertEqual(copied.read_bytes(), b"ground system native log content")


class TestTheEmptyDirectoryRule(EvidenceTestCase):
    """The rule that makes the harness worth having."""
    verifies = ("HUG-VER-003",)

    def test_a_demonstration_capturing_nothing_raises(self):
        with self.assertRaises(EvidenceError) as caught:
            with self._evidence("EMPTY") as ev:
                ev.record("PASS", "claimed without evidence")
        self.assertIn("captured no artifacts", str(caught.exception))

    def test_a_demonstration_without_a_result_raises(self):
        with self.assertRaises(EvidenceError):
            with self._evidence("NORESULT") as ev:
                ev.capture_text("out.txt", "something happened")

    def test_capturing_a_file_that_does_not_exist_raises(self):
        """The demonstration must produce its artifact before capturing it. Capturing
        a missing path would otherwise write a manifest naming a file that is not
        there."""
        with self.assertRaises(EvidenceError):
            with self._evidence() as ev:
                ev.capture_file(Path(self._tmp.name) / "never-produced.log")


class TestFailureIsAlsoEvidence(EvidenceTestCase):
    verifies = ("HUG-VER-003",)

    def test_a_crashed_demonstration_still_writes_a_manifest_marked_fail(self):
        """A crashed demonstration is a result. Burying it would be the worst outcome
        available — it would look identical to one that was never run."""
        with self.assertRaises(ZeroDivisionError):
            with self._evidence("CRASHED") as ev:
                ev.capture_text("partial.txt", "got this far")
                _ = 1 / 0
        manifest = (ev.dir / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("**FAIL**", manifest)
        self.assertIn("ZeroDivisionError", manifest)
        self.assertTrue((ev.artifacts_dir / "partial.txt").is_file(),
                        "artifacts captured before the crash were not preserved")

    def test_a_recorded_failure_is_preserved_not_suppressed(self):
        with self._evidence("FAILED-DEMO") as ev:
            ev.capture_text("out.txt", "alarm did not fire")
            ev.record("FAIL", "staleness alarm never annunciated")
        self.assertIn("**FAIL**", (ev.dir / "MANIFEST.md").read_text(encoding="utf-8"))


class TestTheEvidenceFolderContract(unittest.TestCase):
    """Properties of the real evidence folder, not a temporary one."""
    verifies = ("HUG-VER-003",)

    def test_the_evidence_folder_exists_and_states_the_principle(self):
        readme = REPO / "verification" / "evidence" / "README.md"
        self.assertTrue(readme.is_file())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("preserved artifact, not a retention window", text)
        for obligation in ("B6", "B7", "B10", "B14"):
            self.assertIn(obligation, text,
                          f"the evidence folder does not say what {obligation} owes")

    def test_evidence_is_not_gitignored(self):
        """Evidence that is not committed is not evidence. This is the one large-ish
        artifact class in the repository that must NOT be excluded."""
        gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
        for line in gitignore.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                self.assertNotIn("verification/evidence", stripped,
                                 "the evidence folder is gitignored; gate evidence must "
                                 "be committed")

    def test_the_plugin_does_not_present_retention_as_the_evidence_mechanism(self):
        """Ruling D-008 corrected the earlier design. The generated plugin still sets
        LOG_RETAIN_TIME, but it must describe it as a margin rather than as the way
        evidence is preserved — otherwise the repository contradicts its own ruling."""
        plugin = (REPO / "gnd" / "openc3" / "plugins" / "openc3-cosmos-huginn"
                  / "plugin.txt").read_text(encoding="utf-8")
        self.assertIn("LOG_RETAIN_TIME", plugin)
        lowered = plugin.lower()
        self.assertTrue("margin" in lowered or "not the mechanism" in lowered,
                        "plugin.txt still presents log retention as the evidence "
                        "mechanism; ruling D-008 makes the archived artifact the "
                        "mechanism and retention only a margin")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestInstrumentFault(EvidenceTestCase):
    """The third outcome: collection failed, so the subject's status is not
    established by this run.

    It exists because B6 needed it and there was nowhere to put it. The staleness
    monitor was annunciating GREEN -> YELLOW -> RED correctly, verified in the ground
    system's own log, while the harness meant to read those annunciations returned an
    empty transcript. FAIL would have asserted something false about a working monitor;
    deleting the directory left no trail that the attempt happened at all.
    """
    verifies = ("HUG-VER-003",)

    def test_instrument_fault_is_an_accepted_outcome(self):
        with self._evidence("B6-attempt") as ev:
            ev.capture_text("raw.txt", "some collected bytes\n", note="the slice")
            ev.record("INSTRUMENT_FAULT", "collection returned an empty transcript")
        text = (ev.dir / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("INSTRUMENT_FAULT", text)

    def test_the_manifest_says_the_subject_is_not_established(self):
        """A reader who skims must not be able to mistake this for either verdict."""
        with self._evidence("B6-attempt") as ev:
            ev.capture_text("raw.txt", "x\n")
            ev.record("INSTRUMENT_FAULT", "the collection path failed")
        text = (ev.dir / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("establishes nothing about the subject", text)
        self.assertIn("still", text.lower())

    def test_it_is_not_counted_as_a_pass(self):
        """RED. The whole point is that it must not be totalled with the passes."""
        with self._evidence("B6-attempt") as ev:
            ev.capture_text("raw.txt", "x\n")
            ev.record("INSTRUMENT_FAULT", "collection failed")
        rows = ev_mod.summary()
        row = next(r for r in rows if r["demo_id"] == "B6-attempt")
        self.assertEqual(row["result"], "INSTRUMENT_FAULT")
        self.assertNotEqual(row["result"], "PASS")

    def test_it_still_obeys_the_empty_directory_rule(self):
        """RED. An instrument fault that captured nothing is the same empty claim as
        any other — arguably worse, since it asserts a collection was attempted."""
        with self.assertRaises(ev_mod.EvidenceError):
            with self._evidence("B6-attempt") as ev:
                ev.record("INSTRUMENT_FAULT", "nothing captured")

    def test_an_unknown_result_is_still_refused(self):
        """RED for the guard itself: widening to three must not widen to anything."""
        with self.assertRaises(ValueError):
            with self._evidence("B6-attempt") as ev:
                ev.capture_text("raw.txt", "x\n")
                ev.record("INCONCLUSIVE", "not a member of the set")

    def test_pass_and_fail_do_not_carry_the_not_established_banner(self):
        """GREEN. The banner must appear only where it belongs, or it stops meaning
        anything."""
        for result in ("PASS", "FAIL"):
            with self._evidence(f"D-{result}") as ev:
                ev.capture_text("raw.txt", "x\n")
                ev.record(result, "a statement about the subject")
            text = (ev.dir / "MANIFEST.md").read_text(encoding="utf-8")
            self.assertNotIn("establishes nothing about the subject", text,
                             f"{result} must not carry the instrument-fault banner")
