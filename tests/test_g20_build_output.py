#!/usr/bin/env python3
"""Check G20 skips the plugin's build output and still reads everything else (OF-037).

G20 reads every file in the plugin folder for characters the console cannot display.
After a reload the folder also holds the gem the runbook's first reload command builds
there. The repository ignores it, but G20 read it as text and failed on its first
compressed byte, with every committed plugin file clean. CI checks out a fresh copy,
which has no gem, so it passed there.

G20 now lists the folder by the rule G12 already used: build output is skipped by name.
The red cases hold the other side. A file in the plugin folder that is not build output
is still read, and one that cannot be read as text still fails, so skipping the gem does
not become skipping whatever will not decode.

Each case stages a copy of the record, points the checker at it, adds one file, and
runs G20 there. Nothing is written to the repository.
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tools" / "checkers"))
import defs_generation as dg                                         # noqa: E402
import gen_openc3_config                                             # noqa: E402

#: Bytes that are not UTF-8: a gzip header, as a gem's members begin, then high bytes.
NOT_TEXT = b"\x1f\x8b\x08\x00" + bytes(range(128, 256))


class StagedRecord:
    """A copy of the record, with the checker pointed at it while the case runs."""

    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name) / "record"
        dg._stage(REPO, root)
        dg.set_repo(root)
        self.plugin = gen_openc3_config.plugin_dir()
        return self

    def __exit__(self, *exc):
        dg.set_repo(REPO)
        self._td.cleanup()

    def add(self, rel, data):
        path = self.plugin / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def g20():
    return dg.g20_console_plain_text()


class TestBuildOutputIsSkipped(unittest.TestCase):
    """GREEN: what a reload or a Python run leaves in the plugin folder is not read."""
    verifies = ("HUG-GND-001",)
    polarity = "green"

    def test_the_gem_a_reload_builds_is_skipped(self):
        with StagedRecord() as rec:
            before = g20()
            rec.add("openc3-cosmos-huginn-0.5.gem", NOT_TEXT)
            ok, evidence = g20()
        self.assertTrue(before[0], before[1])
        self.assertTrue(ok, evidence)
        self.assertEqual(evidence, before[1])

    def test_compiled_bytecode_is_skipped(self):
        with StagedRecord() as rec:
            rec.add("microservices/STALENESS/__pycache__/frame_staleness.cpython-313.pyc",
                    NOT_TEXT)
            ok, evidence = g20()
        self.assertTrue(ok, evidence)


class TestEverythingElseIsStillRead(unittest.TestCase):
    """RED: a file in the plugin folder that is not build output is still checked."""
    verifies = ("HUG-GND-001",)
    polarity = "red"

    def test_a_text_file_with_a_character_the_console_cannot_show(self):
        with StagedRecord() as rec:
            rec.add("targets/HUGINN/notes.txt", "EPS_MODE → SAFE\n".encode("utf-8"))
            ok, evidence = g20()
        self.assertFalse(ok)
        self.assertIn("targets/HUGINN/notes.txt:1 carries U+2192", evidence)

    def test_a_file_that_is_not_text_and_not_build_output(self):
        with StagedRecord() as rec:
            rec.add("targets/HUGINN/screens/raw.dat", NOT_TEXT)
            with self.assertRaises(UnicodeDecodeError):
                g20()


if __name__ == "__main__":
    unittest.main()
