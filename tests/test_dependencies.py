#!/usr/bin/env python3
"""The dependency declaration, driven at both polarities (HUG-VER-002, B4).

The predicates in tools/check_deps.py are pure and take their inputs as arguments, so
these cases can plant an undeclared import without editing a source file and without
anything being installed.

The red cases are the failure that prompted the check: `requirements.txt` was correct,
complete and never mentioned outside DECISIONS.md, so a fresh terminal met
`ModuleNotFoundError: sgp4` from tools/serve_sim.py with nothing to tell it what to do.
"""
import ast
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_deps                                                # noqa: E402
from check_deps import compare, declared, describe, imported_names, third_party  # noqa: E402


class TestUndeclaredImportsAreCaught(unittest.TestCase):
    """RED."""
    verifies = ("HUG-VER-002",)
    polarity = "red"

    def test_an_undeclared_third_party_import(self):
        ok, evidence = describe({"yaml", "sgp4", "numpy"}, {"PyYAML", "sgp4"})
        self.assertFalse(ok, "an undeclared import passed the check")
        self.assertIn("numpy", evidence)

    def test_the_failure_that_prompted_this(self):
        """sgp4 imported, requirements.txt not declaring it - the shape the operator
        actually met, with the pin removed."""
        ok, evidence = describe({"yaml", "sgp4"}, {"PyYAML"})
        self.assertFalse(ok)
        self.assertIn("sgp4", evidence)

    def test_the_evidence_says_what_a_fresh_terminal_would_see(self):
        """A reader hitting this must not have to work out why it matters."""
        _ok, evidence = describe({"yaml", "sgp4"}, {"PyYAML"})
        self.assertIn("ModuleNotFoundError", evidence)


class TestDeadPinsAreCaught(unittest.TestCase):
    """RED. Subtraction in one direction only would carry these forever."""
    verifies = ("HUG-VER-002",)
    polarity = "red"

    def test_a_pinned_package_nothing_imports(self):
        ok, evidence = describe({"yaml"}, {"PyYAML", "requests"})
        self.assertFalse(ok)
        self.assertIn("requests", evidence)

    def test_both_directions_reported_together(self):
        ok, evidence = describe({"yaml", "numpy"}, {"PyYAML", "requests"})
        self.assertFalse(ok)
        self.assertIn("numpy", evidence)
        self.assertIn("requests", evidence)


class TestValidFormsHold(unittest.TestCase):
    """GREEN - the check must read for the condition, not for a spelling."""
    verifies = ("HUG-VER-002",)
    polarity = "green"

    def test_the_real_declaration(self):
        ok, evidence = describe(third_party(imported_names()), declared())
        self.assertTrue(ok, evidence)

    def test_the_import_name_and_distribution_name_may_differ(self):
        """`import yaml` is satisfied by PyYAML. Comparing the two sets directly would
        report a phantom problem in both directions at once."""
        undeclared, unused = compare({"yaml"}, {"PyYAML"})
        self.assertEqual(undeclared, [])
        self.assertEqual(unused, [])

    def test_version_specifiers_parse(self):
        for spec in ("PyYAML==6.0.3", "PyYAML>=6.0", "PyYAML~=6.0", "PyYAML"):
            self.assertEqual(declared(spec), {"PyYAML"}, f"failed on {spec!r}")

    def test_comments_and_blank_lines_are_ignored(self):
        text = "# a comment\n\nPyYAML==6.0.3  # trailing\n\n"
        self.assertEqual(declared(text), {"PyYAML"})


class TestTheScanItself(unittest.TestCase):
    """The scan is the part that can fail silently: a scan finding nothing makes every
    comparison above vacuously true."""
    verifies = ("HUG-VER-002",)

    def test_the_scan_finds_the_known_imports(self):
        found = imported_names()
        self.assertIn("yaml", found)
        self.assertIn("sgp4", found)
        self.assertGreater(len(found), 15, "the source scan found implausibly little")

    def test_stdlib_and_local_modules_are_not_reported_as_third_party(self):
        for name in ("os", "sys", "struct", "unittest", "hashlib"):
            self.assertNotIn(name, third_party({name}))
        for name in ("hugdefs", "harness", "sim", "evidence", "ground_targets"):
            self.assertNotIn(name, third_party({name}),
                             f"{name} is in this repository, not third-party")

    def test_prose_is_not_mistaken_for_an_import(self):
        """Parsed with ast rather than grepped. A regex over import lines reads the
        word after 'import' inside docstrings and comments - the first draft of this
        scan reported 'what' and 'defs' as dependencies, both from prose."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.py"
            p.write_text(
                '"""Docstring that says: import numpy, and from pandas import x."""\n'
                "# import requests\n"
                "S = 'import torch'\n"
                "import os\n", encoding="utf-8")
            found = imported_names([p])
        self.assertEqual(found, {"os"},
                         f"prose was mistaken for imports: {found}")

    def test_a_relative_import_is_not_third_party(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.py"
            p.write_text("from . import sibling\nfrom .pkg import thing\n",
                         encoding="utf-8")
            self.assertEqual(imported_names([p]), set())

    def test_the_local_name_set_is_derived_not_listed(self):
        """A hand-maintained exemption list is what goes stale and starts hiding real
        undeclared imports."""
        source = Path(check_deps.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_local_module_names")
        literals = [n.value for n in ast.walk(fn)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertNotIn("hugdefs", literals,
                         "local module names are being listed rather than derived")


if __name__ == "__main__":
    unittest.main(verbosity=2)
