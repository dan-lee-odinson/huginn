#!/usr/bin/env python3
"""B10's verdict, driven from stored bytes with no ground system (D-019 selection 4).

B10 is PROC-001's pre-pass configuration check: GO on the configuration of record,
NO-GO when what the instance holds drifts. Its manifest says PASS; `b10_verdict`
re-derives that from the three archived legs and the liveness record.

EVERY RED CASE IS A NO-GO THAT PROVES NOTHING. A NO-GO from a dead instance, a NO-GO
for a reason other than the perturbation, a NO-GO the source digest alone would have
caught (which is not what D-010's comparison exists for), or legs that did not run in
the order the demonstration claims. Each is one edit away from the real archive.

The GREEN baseline is the archived evidence of `attempt-001`, read off disk.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from demonstrate import b10_verdict                                  # noqa: E402

ART = (REPO / "verification" / "evidence" / "B10-config-mismatch-no-go" / "attempt-001"
       / "artifacts")
FILES = ("go-leg.md", "nogo-leg.md", "restored-leg.md", "liveness.txt")


def archived(name):
    return (ART / name).read_text(encoding="utf-8")


def inputs(**over):
    base = {"go_text": archived("go-leg.md"), "nogo_text": archived("nogo-leg.md"),
            "restored_text": archived("restored-leg.md"),
            "liveness_text": archived("liveness.txt")}
    base.update(over)
    return base


def edit(name, old, new):
    text = archived(name)
    if old not in text:
        raise AssertionError(f"edit anchor not in {name}: {old!r}")
    return text.replace(old, new, 1)


IDENTITY = "- **PASS** — identity vs dictionary of record:"
LOADED_FAIL = "- **FAIL** — loaded vs repository (D-010):"
LOADED_PASS = "- **PASS** — loaded vs repository (D-010):"
INVENTORY = "- **PASS** — target inventory (D-009):"


class TestTheArchivedEvidencePasses(unittest.TestCase):
    """GREEN, off disk."""
    verifies = ("HUG-GND-006",)
    polarity = "green"

    def test_the_committed_b10_evidence_satisfies_the_verdict(self):
        ok, reasons = b10_verdict(**inputs())
        self.assertTrue(ok, f"the archived B10 evidence does not verify: {reasons}")

    def test_the_verdict_is_computable_from_the_archive_alone(self):
        for name in FILES:
            with self.subTest(artifact=name):
                self.assertTrue((ART / name).is_file())


class TestANoGoForTheWrongReason(unittest.TestCase):
    """RED: the NO-GO leg says NO-GO, but not because of the perturbation."""
    verifies = ("HUG-GND-006",)
    polarity = "red"

    def test_the_nogo_leg_says_go(self):
        ok, _ = b10_verdict(**inputs(nogo_text=edit(
            "nogo-leg.md", "### Verdict: **NO-GO**", "### Verdict: **GO**")))
        self.assertFalse(ok)

    def test_the_identity_check_failed_instead(self):
        text = edit("nogo-leg.md", IDENTITY,
                    "- **FAIL** — identity vs dictionary of record:")
        text = text.replace(LOADED_FAIL, LOADED_PASS)
        ok, reasons = b10_verdict(**inputs(nogo_text=text))
        self.assertFalse(ok)
        self.assertTrue(any("some other reason" in r for r in reasons), reasons)

    def test_the_source_digest_could_see_the_perturbation(self):
        ok, reasons = b10_verdict(**inputs(nogo_text=edit(
            "nogo-leg.md", IDENTITY, "- **FAIL** — identity vs dictionary of record:")))
        self.assertFalse(ok)
        self.assertTrue(any("source digest could see" in r for r in reasons), reasons)

    def test_the_inventory_failed_too(self):
        ok, _ = b10_verdict(**inputs(nogo_text=edit(
            "nogo-leg.md", INVENTORY, "- **FAIL** — target inventory (D-009):")))
        self.assertFalse(ok)

    def test_the_nogo_names_no_target_file(self):
        ok, _ = b10_verdict(**inputs(nogo_text=edit(
            "nogo-leg.md", "['targets/HUGINN/cmd_tlm/tlm.txt']", "[]")))
        self.assertFalse(ok)


class TestTheLegsAroundTheNoGo(unittest.TestCase):
    """RED: the GO before and the GO after do not bracket the NO-GO."""
    verifies = ("HUG-GND-006",)
    polarity = "red"

    def test_the_go_leg_has_a_failing_condition(self):
        ok, _ = b10_verdict(**inputs(go_text=edit(
            "go-leg.md", INVENTORY, "- **FAIL** — target inventory (D-009):")))
        self.assertFalse(ok)

    def test_the_restored_leg_is_still_nogo(self):
        ok, _ = b10_verdict(**inputs(restored_text=edit(
            "restored-leg.md", "### Verdict: **GO**", "### Verdict: **NO-GO**")))
        self.assertFalse(ok)

    def test_the_restored_leg_ran_before_the_nogo(self):
        ok, reasons = b10_verdict(**inputs(restored_text=edit(
            "restored-leg.md", "| Executed | 2026-08-05T03:06:29+00:00 |",
            "| Executed | 2026-08-05T03:06:24+00:00 |")))
        self.assertFalse(ok)
        self.assertTrue(any("in that order" in r for r in reasons), reasons)

    def test_the_restored_leg_shows_another_configuration(self):
        ok, _ = b10_verdict(**inputs(restored_text=edit(
            "restored-leg.md", "DICTIONARY_VERSION 0.5", "DICTIONARY_VERSION 0.4")))
        self.assertFalse(ok)

    def test_a_leg_missing_a_condition(self):
        text = "\n".join(l for l in archived("go-leg.md").splitlines()
                         if "target inventory" not in l)
        ok, _ = b10_verdict(**inputs(go_text=text))
        self.assertFalse(ok)


class TestANoGoFromADeadInstance(unittest.TestCase):
    """RED: nothing shows the instance was answering when it said NO-GO."""
    verifies = ("HUG-GND-006",)
    polarity = "red"

    def test_no_service_running_during_the_nogo(self):
        text = "\n".join("services running during NO-GO: []"
                         if l.startswith("services running during NO-GO") else l
                         for l in archived("liveness.txt").splitlines())
        ok, reasons = b10_verdict(**inputs(liveness_text=text))
        self.assertFalse(ok)
        self.assertTrue(any("dead instance" in r for r in reasons), reasons)

    def test_the_api_the_step_queries_was_down(self):
        text = "\n".join(l.replace("'openc3-cosmos-cmd-tlm-api', ", "")
                         if l.startswith("services running during NO-GO") else l
                         for l in archived("liveness.txt").splitlines())
        ok, reasons = b10_verdict(**inputs(liveness_text=text))
        self.assertFalse(ok)
        self.assertTrue(any("command and telemetry API" in r for r in reasons), reasons)

    def test_the_services_changed_during_the_nogo(self):
        text = "\n".join(l.replace("'openc3-tsdb'", "'openc3-tsdb', 'openc3-extra'")
                         if l.startswith("services running during NO-GO") else l
                         for l in archived("liveness.txt").splitlines())
        ok, reasons = b10_verdict(**inputs(liveness_text=text))
        self.assertFalse(ok)
        self.assertTrue(any("differ from those before" in r for r in reasons), reasons)


if __name__ == "__main__":
    unittest.main()
