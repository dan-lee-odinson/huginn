#!/usr/bin/env python3
"""B11's verdict function, at both polarities (D-012, HUG-VER-002).

D-012 requires a demonstration's verdict to be computable from its archived evidence
alone: the live stack paces a run and decides none of it. `b11_verdict` takes four
archived texts and nothing else, so these cases drive it with no stack, no simulator and
no evidence directory.

The red cases are the ways a B11 evidence set could LOOK complete and mean nothing: a
chain whose links do not bind, an accounting that does not close, a refusal that names no
rule, and a markup suite that did not run.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from demonstrate import b11_verdict                              # noqa: E402

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def chain(package=SHA_A, verdict=SHA_B, page=SHA_C, covers=None, built_from=None):
    return (f"package: replay/p.json\n"
            f"package_sha256: {package}\n"
            f"verdict_sha256: {verdict}\n"
            f"verdict_covers_package_sha256: {package if covers is None else covers}\n"
            f"viewer_page_sha256: {page}\n"
            f"viewer_page_built_from_sha256: "
            f"{package if built_from is None else built_from}\n")


def verdict(result="CONFORMS", declared=32, in_check=29, at_viewer=3, both=0,
            neither=0, package=SHA_A, extra=""):
    return (f"package_sha256: {package}\n"
            f"result: {result}\n"
            f"violations: 0\n"
            f"rules_declared: {declared}\n"
            f"rules_in_check: {in_check}\n"
            f"rules_at_viewer: {at_viewer}\n"
            f"rules_in_both: {both}\n"
            f"rules_in_neither: {neither}\n" + extra)


REFUSAL = ("REFUSED: the package violates 2 conformance rule(s).\n"
           "  RS-7-10  frames[0].eps_mode is 'TURBO'\n"
           "  RS-7-12  frames[0].eps_batt_soc is 101.0\n")

MARKUP = "result: OK\ntests_run: 16\nhostile_payloads: 16\nexit_code: 0\n"


class TestTheCompleteEvidenceSetPasses(unittest.TestCase):
    """GREEN. If this fails every red case below is meaningless."""
    verifies = ("HUG-VER-003",)
    polarity = "green"

    def test_a_complete_set_passes(self):
        ok, reasons = b11_verdict(chain(), verdict(), REFUSAL, MARKUP)
        self.assertTrue(ok, reasons)


class TestTheChainMustBind(unittest.TestCase):
    """RED. Three digests sitting in a directory prove they were written together and
    nothing more."""
    verifies = ("HUG-VER-003",)
    polarity = "red"

    def test_a_verdict_about_a_different_package(self):
        ok, reasons = b11_verdict(chain(covers=SHA_B), verdict(), REFUSAL, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("does not cover" in r for r in reasons))

    def test_a_page_built_from_a_different_package(self):
        ok, reasons = b11_verdict(chain(built_from=SHA_B), verdict(), REFUSAL, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("not built from" in r for r in reasons))

    def test_the_verdict_artifact_naming_another_package(self):
        ok, reasons = b11_verdict(chain(), verdict(package=SHA_B), REFUSAL, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("different package" in r for r in reasons))

    def test_a_missing_digest(self):
        ok, reasons = b11_verdict(chain(page="short"), verdict(), REFUSAL, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("viewer_page_sha256" in r for r in reasons))


class TestTheAccountingMustClose(unittest.TestCase):
    """RED. An accounting that does not add up is the shape a silently-unenforced rule
    hides in."""
    verifies = ("HUG-UI-002",)
    polarity = "red"

    def test_a_rule_implemented_nowhere(self):
        ok, reasons = b11_verdict(chain(), verdict(in_check=28, neither=1), REFUSAL,
                                  MARKUP)
        self.assertFalse(ok)

    def test_a_rule_claimed_at_both_sites(self):
        ok, reasons = b11_verdict(chain(), verdict(both=1), REFUSAL, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("both" in r for r in reasons))

    def test_the_sum_not_matching_the_declared_count(self):
        ok, reasons = b11_verdict(chain(), verdict(at_viewer=2), REFUSAL, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("does not close" in r for r in reasons))

    def test_the_word_nowhere_anywhere_in_the_listing(self):
        """The per-rule listing is the readable half; a NOWHERE in it fails even if the
        counts happen to add up."""
        ok, reasons = b11_verdict(chain(), verdict(extra="RS-9-99: NOWHERE\n"),
                                  REFUSAL, MARKUP)
        self.assertFalse(ok)

    def test_a_contract_that_did_not_load(self):
        ok, reasons = b11_verdict(chain(), verdict(declared=0, in_check=0, at_viewer=0),
                                  REFUSAL, MARKUP)
        self.assertFalse(ok)

    def test_a_package_that_did_not_conform(self):
        ok, reasons = b11_verdict(chain(), verdict(result="REFUSED"), REFUSAL, MARKUP)
        self.assertFalse(ok)


class TestTheRedLegMustHaveHappened(unittest.TestCase):
    """RED. A green leg alone shows the checker accepts things, not that it rejects
    anything."""
    verifies = ("HUG-VER-002",)
    polarity = "red"

    def test_a_perturbed_package_that_was_not_refused(self):
        ok, reasons = b11_verdict(chain(), verdict(), "the package looks fine\n", MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("not refused" in r for r in reasons))

    def test_a_refusal_that_names_no_rule(self):
        ok, reasons = b11_verdict(chain(), verdict(), "REFUSED: invalid package\n",
                                  MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("named no rule" in r for r in reasons))

    def test_a_refusal_missing_one_of_the_two_perturbations(self):
        partial = "REFUSED\n  RS-7-10 eps_mode is 'TURBO'\n"
        ok, reasons = b11_verdict(chain(), verdict(), partial, MARKUP)
        self.assertFalse(ok)
        self.assertTrue(any("RS-7-12" in r for r in reasons))


class TestTheMarkupSuiteMustHaveRun(unittest.TestCase):
    """RED."""
    verifies = ("HUG-UI-007",)
    polarity = "red"

    def test_a_failing_markup_suite(self):
        ok, reasons = b11_verdict(chain(), verdict(), REFUSAL,
                                  "result: FAILED\ntests_run: 16\n"
                                  "hostile_payloads: 16\n")
        self.assertFalse(ok)

    def test_a_suite_that_ran_almost_nothing(self):
        ok, reasons = b11_verdict(chain(), verdict(), REFUSAL,
                                  "result: OK\ntests_run: 1\nhostile_payloads: 16\n")
        self.assertFalse(ok)

    def test_a_thin_payload_list(self):
        """A suite that passes over three payloads is not the malicious-markup test."""
        ok, reasons = b11_verdict(chain(), verdict(), REFUSAL,
                                  "result: OK\ntests_run: 16\nhostile_payloads: 3\n")
        self.assertFalse(ok)


class TestTheArchivedEvidenceItself(unittest.TestCase):
    """The committed evidence must satisfy the same function, read off disk."""
    verifies = ("HUG-UI-002", "HUG-VER-003")

    ROOT = (REPO / "verification" / "evidence" / "B11-replay-package-and-viewer")

    def test_the_recorded_attempt_recomputes_as_pass(self):
        attempts = sorted(self.ROOT.glob("attempt-*")) if self.ROOT.is_dir() else []
        self.assertTrue(attempts, "no B11 evidence attempt is present")
        latest = attempts[-1] / "artifacts"
        ok, reasons = b11_verdict(
            (latest / "digest-chain.txt").read_text(encoding="utf-8"),
            (latest / "conformance-verdict.txt").read_text(encoding="utf-8"),
            (latest / "red-refusal.txt").read_text(encoding="utf-8"),
            (latest / "malicious-markup.txt").read_text(encoding="utf-8"))
        self.assertTrue(ok, f"the archived evidence does not recompute as PASS: "
                            f"{reasons}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
