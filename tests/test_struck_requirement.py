#!/usr/bin/env python3
"""A requirement struck in place by an owner ruling (D-019, selection 2).

D-019 strikes HUG-SYS-006 in place: its identifier and text are kept, it is marked struck
by the ruling, and the traceability matrix shows it struck. These cases pin the three
places that rule lands: the generated requirements view, the matrix, and the
verification report's count.

The matrix cases build a two-row spine rather than reading the record. The record has
exactly one struck row and it has cases, so it can show the exemption only in the shape
that needs no exemption. The synthetic spine can show both halves: a struck row with no
cases owes nothing (green), and the same row with its marker removed is a finding (red).
That pair is what tells an exemption keyed on the marker from one keyed on nothing.

What the exemption must NOT do is covered by `tools/gen_traceability.py --self-test`
(F1.m4, F3.m3): a struck row covers no CONOPS identifier and lifts no other requirement
to a NEED.
"""
import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tools" / "checkers"))
import gen_requirements                                              # noqa: E402
import gen_traceability                                              # noqa: E402
import gen_verification_report                                       # noqa: E402
import hugdefs                                                       # noqa: E402

LIVE = {"id": "HUG-SYS-001", "verification": ["T"], "trace": "NEED-01", "text": "Live."}
STRUCK = {"id": "HUG-SYS-002", "verification": ["D"], "trace": "NEED-01",
          "text": "Struck, and still readable.", "struck": "D-019"}
CONOPS = {"NEED-01"}


def spine(*rows):
    return {"groups": [{"id": "HUG-SYS", "name": "System",
                        "requirements": [copy.deepcopy(r) for r in rows]}]}


def case(cid, verifies, kind="test", outcome="PASS", polarity="red"):
    return {"case_id": cid, "kind": kind, "outcome": outcome, "verifies": [verifies],
            "polarity": polarity, "polarity_source": "declared"}


def record(*cases):
    return {"cases": list(cases)}


def row(rows, rid):
    return next(r for r in rows if r["id"] == rid)


class TestTheRecordStrikesHugSys006(unittest.TestCase):
    """GREEN, off the record: the strike D-019 made is the one the source carries."""
    verifies = ("HUG-VER-001",)
    polarity = "green"

    def test_hug_sys_006_is_struck_by_d019_with_its_text_kept(self):
        reqs = {r["id"]: r for r in
                hugdefs.requirements_flat(hugdefs.load_requirements())}
        sys006 = reqs["HUG-SYS-006"]
        self.assertEqual(sys006.get("struck"), "D-019")
        self.assertTrue(sys006["text"].startswith(
            "Every campaign session shall be recorded such that any pass can be replayed"))

    def test_no_other_requirement_is_struck(self):
        struck = [r["id"] for r in hugdefs.requirements_flat(hugdefs.load_requirements())
                  if "struck" in r]
        self.assertEqual(struck, ["HUG-SYS-006"])


class TestTheGeneratedViewKeepsTheText(unittest.TestCase):
    """GREEN: the view marks the row struck and keeps every word of it."""
    verifies = ("HUG-VER-001",)
    polarity = "green"

    def test_a_struck_row_names_its_ruling_and_keeps_its_text(self):
        cell = gen_requirements.requirement_cell(STRUCK)
        self.assertEqual(cell, "**Struck in place by D-019.** ~~Struck, and still readable.~~")

    def test_a_live_row_is_its_text(self):
        self.assertEqual(gen_requirements.requirement_cell(LIVE), "Live.")


class TestAStruckRowOwesNothing(unittest.TestCase):
    """GREEN: the exemption works where it applies."""
    verifies = ("HUG-VER-001",)
    polarity = "green"

    def test_a_struck_row_with_no_cases_is_not_a_finding(self):
        rows, findings = gen_traceability.build_matrix(
            spine(LIVE, STRUCK), set(CONOPS), record(case("t1", "HUG-SYS-001")))
        self.assertEqual(findings, [])
        self.assertEqual(row(rows, "HUG-SYS-002")["verdict"], "STRUCK")
        self.assertEqual(row(rows, "HUG-SYS-002")["cases_verdict"], "NO_RECORD")

    def test_a_struck_row_keeps_its_cases_and_shows_what_they_did(self):
        rows, findings = gen_traceability.build_matrix(
            spine(LIVE, STRUCK), set(CONOPS),
            record(case("t1", "HUG-SYS-001"),
                   case("verification/evidence/B99/attempt-001", "HUG-SYS-002",
                        kind="demonstration")))
        struck = row(rows, "HUG-SYS-002")
        self.assertEqual(findings, [])
        self.assertEqual((struck["verdict"], struck["cases_verdict"]), ("STRUCK", "PASS"))
        self.assertEqual(struck["demonstrations"], ["verification/evidence/B99/attempt-001"])
        text = gen_traceability.render(
            rows, findings,
            {"metadata": {"commit": "c", "commit_subject": "s", "tree_clean": True,
                          "executed_utc": "t", "python": "p", "platform": "x"},
             "counts": {"test": 1, "check": 0, "mutation": 0, "demonstration": 1}},
            set(CONOPS))
        self.assertIn("| STRUCK (D-019; cases PASS) |", text)
        self.assertIn("- Struck in place by D-019.", text)
        self.assertIn("Struck in place: `HUG-SYS-002` (D-019).", text)


class TestTheExemptionIsKeyedOnTheMarker(unittest.TestCase):
    """RED: take the marker away and the same row is a finding again."""
    verifies = ("HUG-VER-001",)
    polarity = "red"

    def test_the_same_row_unstruck_with_no_cases_is_an_f2_finding(self):
        unstruck = {k: v for k, v in STRUCK.items() if k != "struck"}
        rows, findings = gen_traceability.build_matrix(
            spine(LIVE, unstruck), set(CONOPS), record(case("t1", "HUG-SYS-001")))
        self.assertIn("F2", {c for c, _m in findings})
        self.assertEqual(row(rows, "HUG-SYS-002")["verdict"], "NO_RECORD")

    def test_a_live_row_beside_a_struck_one_still_owes_its_cases(self):
        rows, findings = gen_traceability.build_matrix(
            spine(LIVE, STRUCK), set(CONOPS), record())
        self.assertEqual([c for c, _m in findings], ["F2"])
        self.assertIn("HUG-SYS-001", findings[0][1])


def _report(rows):
    rec = {"metadata": {"commit": "c", "commit_subject": "s", "tree_clean": True,
                        "executed_utc": "t", "python": "p", "platform": "x"},
           "counts": {"test": 1, "check": 0, "mutation": 0, "demonstration": 0},
           "obligations": {}}
    return gen_verification_report.render_report(rows, [], rec, [], [])


class TestTheReportCountsStruckApart(unittest.TestCase):
    """GREEN: a struck row is neither established nor missing; it is counted apart."""
    verifies = ("HUG-VER-003",)
    polarity = "green"

    def test_a_struck_row_is_counted_apart(self):
        rows, _ = gen_traceability.build_matrix(
            spine(LIVE, STRUCK), set(CONOPS), record(case("t1", "HUG-SYS-001")))
        text = _report(rows)
        self.assertIn("1 of 1 requirements in force are established PASS by this run. "
                      "1 more is struck in place and not counted.", text)
        self.assertIn("| STRUCK | 1 | `HUG-SYS-002` |", text)


class TestWithoutAStrikeTheRowCounts(unittest.TestCase):
    """RED: the same row unstruck counts against the release as not established."""
    verifies = ("HUG-VER-003",)
    polarity = "red"

    def test_the_unstruck_row_is_in_force_and_not_established(self):
        unstruck = {k: v for k, v in STRUCK.items() if k != "struck"}
        rows, _ = gen_traceability.build_matrix(
            spine(LIVE, unstruck), set(CONOPS), record(case("t1", "HUG-SYS-001")))
        text = _report(rows)
        self.assertIn("1 of 2 requirements in force are established PASS by this run.",
                      text)
        self.assertNotIn("| STRUCK |", text)

if __name__ == "__main__":
    unittest.main()
