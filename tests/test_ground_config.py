#!/usr/bin/env python3
"""The loaded-vs-repository check, at both polarities (HUG-VER-002, B4). Ruling D-010.

The predicate is pure and takes both sides as arguments, so every case here runs without
a stack. The red cases are the drift that actually happened: at the `fill_fields` fix the
repository and the instance disagreed about `plugin.txt` while the source digest and the
plugin version were identical on both sides.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import ground_config as gc                                       # noqa: E402
from ground_config import compare, describe                      # noqa: E402

REPO_SIDE = {
    "plugin.txt": "aaa",
    "targets/HUGINN/cmd_tlm/tlm.txt": "bbb",
    "targets/HUGINN/CONFIG_ID.txt": "ccc",
}


class TestDriftIsCaught(unittest.TestCase):
    """RED."""
    verifies = ("HUG-GND-006",)
    polarity = "red"

    def test_the_fill_fields_drift(self):
        """The one that happened: one artifact differs, everything else agrees, and the
        source digest is identical on both sides so it cannot see it."""
        loaded = dict(REPO_SIDE, **{"plugin.txt": "DIFFERENT"})
        ok, evidence = describe(loaded, REPO_SIDE)
        self.assertFalse(ok)
        self.assertIn("plugin.txt", evidence)
        self.assertIn("D-010", evidence)

    def test_the_digest_agreeing_does_not_rescue_it(self):
        """CONFIG_ID.txt identical on both sides while the plugin differs is exactly the
        shape B10's digest comparison returns GO on."""
        loaded = dict(REPO_SIDE, **{"plugin.txt": "DIFFERENT"})
        self.assertEqual(loaded["targets/HUGINN/CONFIG_ID.txt"],
                         REPO_SIDE["targets/HUGINN/CONFIG_ID.txt"])
        self.assertFalse(describe(loaded, REPO_SIDE)[0])

    def test_an_artifact_the_instance_never_loaded(self):
        loaded = {k: v for k, v in REPO_SIDE.items() if k != "plugin.txt"}
        ok, evidence = describe(loaded, REPO_SIDE)
        self.assertFalse(ok)
        self.assertIn("NOT loaded", evidence)

    def test_an_artifact_the_instance_has_that_we_do_not_generate(self):
        loaded = dict(REPO_SIDE, **{"targets/INST/cmd_tlm/tlm.txt": "zzz"})
        ok, evidence = describe(loaded, REPO_SIDE)
        self.assertFalse(ok)
        self.assertIn("not generated here", evidence)

    def test_an_empty_instance_does_not_pass(self):
        """The vacuous shape: nothing loaded means nothing differing, and a
        difference-only check would call a dead instance clean."""
        self.assertFalse(describe({}, REPO_SIDE)[0])

    def test_an_empty_repository_side_does_not_pass(self):
        """If the artifact list came back empty, every comparison below it is vacuous.
        Refusing is the only honest answer."""
        ok, evidence = describe(REPO_SIDE, {})
        self.assertFalse(ok)
        self.assertIn("nothing to compare", evidence)

    def test_all_three_directions_reported_together(self):
        loaded = {"plugin.txt": "DIFFERENT", "targets/INST/x.txt": "zzz"}
        ok, evidence = describe(loaded, REPO_SIDE)
        self.assertFalse(ok)
        self.assertIn("plugin.txt", evidence)
        self.assertIn("NOT loaded", evidence)
        self.assertIn("not generated here", evidence)


class TestAgreementHolds(unittest.TestCase):
    """GREEN."""
    verifies = ("HUG-GND-006",)
    polarity = "green"

    def test_identical_sides_pass(self):
        ok, evidence = describe(dict(REPO_SIDE), REPO_SIDE)
        self.assertTrue(ok, evidence)
        self.assertIn("byte-identical", evidence)

    def test_compare_is_symmetric_in_what_it_names(self):
        differing, missing, extra = compare({"a": "1"}, {"a": "2", "b": "3"})
        self.assertEqual((differing, missing, extra), (["a"], ["b"], []))


class TestTheArtifactListIsDerived(unittest.TestCase):
    """The list is the generator's own. A hand-kept second list is what goes stale, and
    a missing entry reads as 'nothing to compare' rather than as a gap."""
    verifies = ("HUG-GND-006",)

    def test_every_generated_artifact_is_mapped_or_explicitly_excluded(self):
        """This is the guard: adding a file to the generator without deciding what it
        means for the loaded configuration must raise, not silently skip."""
        gc.repository_artifacts()          # raises AssertionError if anything is unmapped

    def test_the_repository_side_is_not_empty_and_covers_the_known_artifacts(self):
        arts = gc.repository_artifacts()
        self.assertIn("plugin.txt", arts)
        self.assertIn("targets/HUGINN/cmd_tlm/tlm.txt", arts)
        self.assertIn("microservices/STALENESS/frame_staleness.py", arts)
        for digest in arts.values():
            self.assertEqual(len(digest), 64)

    def test_the_gemspec_is_excluded_deliberately(self):
        """Build input, not runtime configuration. Recorded as a decision with None
        rather than by being absent from the map."""
        self.assertIn("openc3-cosmos-huginn.gemspec", gc.INSTANCE_LOCATION)
        self.assertIsNone(gc.INSTANCE_LOCATION["openc3-cosmos-huginn.gemspec"])
        self.assertNotIn("openc3-cosmos-huginn.gemspec", gc.repository_artifacts())

    def test_an_unmapped_generated_artifact_raises(self):
        """RED for the guard itself."""
        saved = dict(gc.INSTANCE_LOCATION)
        gc.INSTANCE_LOCATION.pop("plugin.txt")
        try:
            with self.assertRaises(AssertionError) as caught:
                gc.repository_artifacts()
            self.assertIn("plugin.txt", str(caught.exception))
        finally:
            gc.INSTANCE_LOCATION.clear()
            gc.INSTANCE_LOCATION.update(saved)


class TestTheLiveAdapterDecodesExplicitly(unittest.TestCase):
    verifies = ("HUG-GND-006",)

    def test_compose_output_is_decoded_as_utf8_not_the_locale(self):
        """`text=True` alone decodes with the locale encoding — cp1252 on this machine.
        plugin.txt carries an em-dash, and decoding it as cp1252 changes the digest and
        reports a drift that does not exist. That false positive was live in the first
        version of this file, and a check that cries wolf every run is how an operator
        learns to ignore a no-go."""
        import inspect
        src = inspect.getsource(gc._compose)
        self.assertIn('encoding="utf-8"', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
