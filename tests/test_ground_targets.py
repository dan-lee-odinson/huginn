#!/usr/bin/env python3
"""The foreign-target check, driven at both polarities (HUG-VER-002, B4).

The predicate lives in tools/ground_targets.py as a pure function so it can be falsified
here without a running stack. A check that can only be exercised by standing up Docker
gets exercised rarely, and one that is never seen to fail is not evidence of anything.

The red cases are the shapes contamination actually took. INST and INST2 are not
hypothetical: they were loaded in HUGINN's instance for one bring-up, alongside HUGINN,
because OPENC3_DEMO=0 reads as "on" to init.sh (DECISIONS.md D-009).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ground_targets import allowed_targets, compare, describe    # noqa: E402

ALLOWED = ["UNKNOWN", "HUGINN"]


class TestForeignTargetsAreCaught(unittest.TestCase):
    """RED: every one of these must fail the check."""
    verifies = ("HUG-GND-001", "HUG-GND-006")
    polarity = "red"

    def _must_fail(self, loaded, because):
        ok, evidence = describe(loaded, ALLOWED)
        self.assertFalse(ok, f"{because}: {loaded} passed the check")
        return evidence

    def test_the_demo_targets_that_actually_loaded(self):
        """The exact inventory HUGINN's instance held at the contaminated bring-up."""
        evidence = self._must_fail(
            ["UNKNOWN", "HUGINN", "INST", "INST2", "EXAMPLE"],
            "the demo plugin's targets alongside HUGINN")
        for name in ("INST", "INST2", "EXAMPLE"):
            self.assertIn(name, evidence, "the evidence must name what it found")

    def test_a_single_foreign_target(self):
        self._must_fail(["UNKNOWN", "HUGINN", "INST"], "one foreign target")

    def test_a_foreign_target_with_a_plausible_name(self):
        """Contamination does not have to look like the demo. A target named for this
        mission is still not the configuration of record unless defs says so."""
        self._must_fail(["UNKNOWN", "HUGINN", "HUGINN_TEST"], "a plausible-looking name")


class TestAnIncompleteInstanceIsAlsoCaught(unittest.TestCase):
    """RED: subtraction-only checking would pass these. The loaded configuration is
    not HUGINN's if HUGINN is not in it."""
    verifies = ("HUG-GND-001", "HUG-GND-006")
    polarity = "red"

    def test_an_empty_instance_does_not_pass(self):
        """This is the vacuous-pass shape: nothing loaded means nothing foreign, and a
        check hunting only for extras would report clean on a dead instance."""
        ok, _ = describe([], ALLOWED)
        self.assertFalse(ok, "an empty instance passed the foreign-target check")

    def test_huginn_missing_does_not_pass(self):
        ok, evidence = describe(["UNKNOWN"], ALLOWED)
        self.assertFalse(ok)
        self.assertIn("HUGINN", evidence)

    def test_both_directions_are_reported_together(self):
        """A reader fixing one problem should not have to re-run to discover the
        other."""
        ok, evidence = describe(["UNKNOWN", "INST"], ALLOWED)
        self.assertFalse(ok)
        self.assertIn("INST", evidence)
        self.assertIn("HUGINN", evidence)


class TestTheCleanInstanceHolds(unittest.TestCase):
    """GREEN: these must NOT be flagged, or the check is reading for a spelling
    rather than for the condition."""
    verifies = ("HUG-GND-001", "HUG-GND-006")
    polarity = "green"

    def test_the_permitted_set_exactly(self):
        ok, evidence = describe(["UNKNOWN", "HUGINN"], ALLOWED)
        self.assertTrue(ok, evidence)

    def test_order_does_not_matter(self):
        ok, _ = describe(["HUGINN", "UNKNOWN"], ALLOWED)
        self.assertTrue(ok)

    def test_duplicates_do_not_matter(self):
        """Redis returns a hash key list; a repeat would be COSMOS's business, not a
        contamination signal."""
        ok, _ = describe(["UNKNOWN", "HUGINN", "HUGINN"], ALLOWED)
        self.assertTrue(ok)


class TestThePermittedSetIsAnchored(unittest.TestCase):
    verifies = ("HUG-GND-001", "HUG-GND-006")

    def test_allowed_targets_agrees_with_the_plugin(self):
        """defs/ground.yaml names the permitted set, but the plugin declares what is
        actually installed. If a rename moved one and not the other, this check would
        be permitting a target that does not exist and failing the one that does."""
        allowed = allowed_targets()
        self.assertIn("HUGINN", allowed)
        self.assertIn("UNKNOWN", allowed)

    def test_the_permitted_set_is_small_and_deliberate(self):
        """Not a style rule. Every name here is a target that contamination could hide
        behind, so the set growing silently is the thing to notice."""
        self.assertEqual(sorted(allowed_targets()), ["HUGINN", "UNKNOWN"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
