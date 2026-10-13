#!/usr/bin/env python3
"""Check G2, generation is deterministic, demonstrated to fail (D-019 selection 4).

G2 renders every generated view twice from the same source and requires identical
bytes. It carries no source mutation in the defs-generation self-test, and says why:
no edit to a source file can make deterministic code nondeterministic. So until now
nothing had shown G2 could fail at all, and a G2 that compared nothing, or compared each
output with itself, would have passed every run.

The red cases make one generator depend on something other than its source: a counter
that advances on every call, the shape of a clock, a process-level cache or an unseeded
random draw. G2 must report it, and name the view. One red case is planted in the first
view G2 renders and one in the last, so a check that stopped early cannot pass both.

The plant is a `mock.patch.object` on the generator's module attribute, undone when
the case ends, so nothing leaks into the suites that run after it.
"""
import itertools
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tools" / "checkers"))
import defs_generation                                               # noqa: E402


def drifting(original):
    """`original`, plus one line that changes on every call."""
    counter = itertools.count()

    def build(*args, **kwargs):
        return list(original(*args, **kwargs)) + [f"# render {next(counter)}"]
    return build


class TestGenerationIsDeterministic(unittest.TestCase):
    """GREEN: the real generators, rendered twice, agree byte for byte."""
    polarity = "green"

    def test_g2_holds_on_the_record(self):
        ok, evidence = defs_generation.g2_deterministic()
        self.assertTrue(ok, evidence)


class TestANondeterministicGeneratorIsCaught(unittest.TestCase):
    """RED: one generator made to depend on something besides its source."""
    polarity = "red"

    def assertCaught(self, module, name, view):
        with mock.patch.object(module, name, drifting(getattr(module, name))):
            ok, evidence = defs_generation.g2_deterministic()
        self.assertFalse(ok, "G2 passed with a generator that renders differently on "
                             "every call")
        self.assertIn("NONDETERMINISTIC", evidence)
        self.assertIn(f"'{view}'", evidence)

    def test_the_first_view_g2_renders(self):
        self.assertCaught(defs_generation.gen_dictionary, "build", "dictionary")

    def test_the_last_view_g2_renders(self):
        self.assertCaught(defs_generation.gen_openc3_config, "build_config_id",
                          "CONFIG_ID.txt")

    def test_the_plant_is_undone(self):
        """The red cases above leave the generators as they found them."""
        self.assertCaught(defs_generation.gen_dictionary, "build", "dictionary")
        ok, evidence = defs_generation.g2_deterministic()
        self.assertTrue(ok, evidence)


if __name__ == "__main__":
    unittest.main()
