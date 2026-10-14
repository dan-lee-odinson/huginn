#!/usr/bin/env python3
"""The flown campaign tied to HUG-OPS-003 and HUG-OPS-004 (D-019 selection 4).

Written to close OF-013's last two rows. Both requirements were the only two in the
matrix with no executed case, because the campaign they describe had not been flown when
the matrix was built. It has been, and these cases read what it left behind.

THE GREEN BASELINE IS THE RECORD AS FILED. A synthetic campaign would only prove the
checks accept fixtures written to pass them. Every red case below is one edit away from
the real record, and each edit is a way the campaign could look complete while not being
so: a pass whose record its scenario does not reproduce, an operator command missing from
the log, an anomaly report that names the wrong contacts, a finding that never reached the
register.

The heaviest step, replaying every filed record against every campaign scenario, runs
once per process. A red case that changes a record replays only that record.

A re-fly's record does not exist until the re-fly is flown. Its cases relabel a filed
record as one the re-fly's scenario reproduced, which is one edit from the record as
filed, and what they hold is where such a record counts.
"""
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import campaign_record as cr                                         # noqa: E402

_BASE = {}


def base():
    """The record as filed, loaded and classified once."""
    if not _BASE:
        campaign = cr.load_campaign()
        records = cr.load_records()
        _BASE.update(campaign=campaign, records=records,
                     classified=cr.classify(records, campaign),
                     classes=cr.fault_classes(), reports=cr.load_anomaly_reports(),
                     register=cr.register_keys())
    return copy.deepcopy(_BASE)


def reclassify(b, record_id, change):
    """Apply `change` to one record and re-establish only that record."""
    for i, c in enumerate(b["classified"]):
        if c["id"] == record_id:
            rec = c["record"]
            change(rec)
            b["classified"][i] = cr.classify([rec], b["campaign"])[0]
            return b
    raise KeyError(record_id)


def relabel(b, record_id, scenario):
    """Treat one counted record as reproduced by `scenario`: what a re-fly's record is."""
    for c in b["classified"]:
        if c["id"] == record_id:
            c["scenario"], c["scenarios"] = scenario, [scenario]
            return b
    raise KeyError(record_id)


def ops003(b):
    return cr.ops003_problems(b["campaign"], b["classified"], b["classes"])


def ops004(b):
    return cr.ops004_problems(b["campaign"], b["classified"], b["reports"], b["register"])


def ar(b, ar_id):
    return next(r for r in b["reports"] if r["id"] == ar_id)


class TestTheCampaignAsFlownMeetsHugOps003(unittest.TestCase):
    """GREEN, off the record."""
    verifies = ("HUG-OPS-003",)
    polarity = "green"

    def test_the_filed_campaign_meets_hug_ops_003(self):
        self.assertEqual(ops003(base()), [])

    def test_every_pass_is_reproduced_by_its_scenario_and_only_its_scenario(self):
        counted = {c["id"]: c["scenario"] for c in base()["classified"] if c["counted"]}
        self.assertEqual(counted, {
            "2026-09-13-P1": "P1_nominal",
            "2026-09-20-P2a": "P2_array_string_loss",
            "2026-09-20-P2b": "P2_array_string_loss",
            "2026-10-11-P3": "P3_stuck_load",
            "2026-10-11-P4": "P4_hk_generation_halt",
        })

    def test_the_first_pass_1_attempt_and_the_example_are_not_counted(self):
        by_id = {c["id"]: c for c in base()["classified"]}
        self.assertFalse(by_id["2026-08-03-P1"]["valid"])
        self.assertFalse(by_id["2026-08-03-P1"]["counted"])
        self.assertIsNone(by_id["EXAMPLE-2026-08-08-A"]["record"]["telemetry"])
        self.assertFalse(by_id["EXAMPLE-2026-08-08-A"]["counted"])

    def test_each_scenario_counts_toward_one_pass_re_flies_included(self):
        self.assertEqual(cr.scenario_passes(base()["campaign"]), {
            "P1_nominal": "PASS-1",
            "P2_array_string_loss": "PASS-2",
            "P3_stuck_load": "PASS-3",
            "P4_hk_generation_halt": "PASS-4",
            "P4_hk_generation_halt_refly": "PASS-4",
        })

    def test_every_scenario_the_campaign_flies_is_a_candidate(self):
        rec = next(c["record"] for c in base()["classified"] if c["id"] == "2026-10-11-P4")
        with mock.patch.object(cr, "replay", return_value=(False, "")) as replay:
            cr.classify([rec], base()["campaign"])
        self.assertEqual({call.args[0] for call in replay.call_args_list},
                         set(cr.scenario_passes(base()["campaign"])))

    def test_the_pass_4_re_fly_scenario_reproduces_no_filed_record(self):
        """Its extra command shows in the first frame the first flight received."""
        rec = next(c["record"] for c in base()["classified"] if c["id"] == "2026-10-11-P4")
        ok, detail = cr.replay("P4_hk_generation_halt_refly", rec)
        self.assertFalse(ok)
        self.assertIn("diverges at MET 1102", detail)
        self.assertNotIn("P4_hk_generation_halt_refly",
                         [s for c in base()["classified"] for s in c["scenarios"]])

    def test_a_re_fly_record_counts_toward_its_pass(self):
        """PASS-4 met by a record of its re-fly alone."""
        b = relabel(base(), "2026-10-11-P4", "P4_hk_generation_halt_refly")
        self.assertEqual(ops003(b), [])

    def test_the_operator_commands_are_what_make_pass_3_reproduce(self):
        """Without its logged shed, the scenario stops matching at the shed's frame."""
        rec = next(c["record"] for c in base()["classified"] if c["id"] == "2026-10-11-P3")
        self.assertEqual(cr.replay("P3_stuck_load", rec), (True, "all 427 frames reproduced"))
        ok, detail = cr.replay("P3_stuck_load", rec, with_commands=False)
        self.assertFalse(ok)
        self.assertIn("diverges at MET 959", detail)


class TestACampaignThatFallsShortOfHugOps003(unittest.TestCase):
    """RED: each one edit from the record as filed."""
    verifies = ("HUG-OPS-003",)
    polarity = "red"

    def assertProblem(self, b, text):
        problems = ops003(b)
        self.assertTrue(any(text in p for p in problems), problems)

    def test_no_nominal_pass(self):
        b = base()
        b["campaign"]["passes"][0]["fault_class"] = b["campaign"]["passes"][1]["fault_class"]
        self.assertProblem(b, "no nominal pass")

    def test_two_anomaly_passes_of_one_fault_class(self):
        b = base()
        b["campaign"]["passes"][3]["fault_class"] = b["campaign"]["passes"][2]["fault_class"]
        self.assertProblem(b, "one pass each")

    def test_a_pass_with_no_filed_record(self):
        b = base()
        b["classified"] = [c for c in b["classified"] if c["id"] != "2026-10-11-P3"]
        self.assertProblem(b, "PASS-3 (P3_stuck_load) has no record")

    def test_pass_1_with_only_the_attempt_the_validator_refuses(self):
        b = base()
        b["classified"] = [c for c in b["classified"] if c["id"] != "2026-09-13-P1"]
        self.assertProblem(b, "PASS-1 (P1_nominal) has no record")

    def test_a_reproduced_record_the_validator_refuses(self):
        """The re-fly's telemetry still reproduces; its completion record does not hold."""
        b = reclassify(base(), "2026-09-13-P1",
                       lambda rec: rec["report"]["completion_record"].pop())
        self.assertProblem(b, "PASS-1 (P1_nominal) has no record")

    def test_one_recorded_value_its_scenario_does_not_produce(self):
        def tamper(rec):
            rec["telemetry"][200]["EPS_BATT_SOC"] = "80.0"
        b = reclassify(base(), "2026-10-11-P4", tamper)
        self.assertProblem(b, "PASS-4 (P4_hk_generation_halt) has no record")

    def test_an_operator_command_missing_from_the_log(self):
        b = reclassify(base(), "2026-10-11-P3", lambda rec: rec["commands"].clear())
        self.assertProblem(b, "PASS-3 (P3_stuck_load) has no record")

    def test_a_pass_with_nothing_sent_from_the_console(self):
        """PASS-4 still reproduces without its reset (OF-028), so only this check sees it."""
        b = reclassify(base(), "2026-10-11-P4", lambda rec: rec["commands"].clear())
        self.assertProblem(b, "PASS-4's records log no command from the console")

    def test_a_re_fly_record_whose_re_fly_is_not_in_the_campaign(self):
        b = relabel(base(), "2026-10-11-P4", "P4_hk_generation_halt_refly")
        b["campaign"]["passes"][3]["reflies"] = []
        self.assertProblem(b, "PASS-4 (P4_hk_generation_halt) has no record")

    def test_a_scenario_claimed_by_two_passes(self):
        campaign = base()["campaign"]
        campaign["passes"][2]["reflies"][0]["scenario"] = "P4_hk_generation_halt_refly"
        with self.assertRaisesRegex(ValueError, "flown by both PASS-3 and PASS-4"):
            cr.scenario_passes(campaign)

    def test_a_record_executed_a_day_after_its_frames_arrived(self):
        def late(rec):
            rec["report"]["executed_utc"] = "2026-10-12T16:58:41Z"
        b = reclassify(base(), "2026-10-11-P3", late)
        self.assertProblem(b, "2026-10-11-P3 says it was executed at")


class TestTheAnomalyReportsMeetHugOps004(unittest.TestCase):
    """GREEN, off the record."""
    verifies = ("HUG-OPS-004",)
    polarity = "green"

    def test_the_filed_anomaly_reports_meet_hug_ops_004(self):
        self.assertEqual(ops004(base()), [])

    def test_a_re_fly_record_is_one_its_pass_report_names(self):
        b = relabel(base(), "2026-10-11-P4", "P4_hk_generation_halt_refly")
        self.assertEqual(ops004(b), [])

    def test_each_anomaly_pass_has_its_own_report(self):
        reports = {r["id"]: r["fields"]["Scenario"].split("`")[1] for r in base()["reports"]}
        self.assertEqual(reports, {
            "AR-001": "sim/scenarios/P2_array_string_loss.yaml",
            "AR-002": "sim/scenarios/P3_stuck_load.yaml",
            "AR-003": "sim/scenarios/P4_hk_generation_halt.yaml",
        })


class TestAnAnomalyReportThatFallsShortOfHugOps004(unittest.TestCase):
    """RED: each one edit from the record as filed."""
    verifies = ("HUG-OPS-004",)
    polarity = "red"

    def assertProblem(self, b, text):
        problems = ops004(b)
        self.assertTrue(any(text in p for p in problems), problems)

    def test_an_anomaly_pass_with_no_report(self):
        b = base()
        b["reports"] = [r for r in b["reports"] if r["id"] != "AR-002"]
        self.assertProblem(b, "PASS-3 has 0 anomaly reports")

    def test_a_report_filed_against_another_pass_scenario(self):
        b = base()
        f = ar(b, "AR-002")["fields"]
        f["Scenario"] = f["Scenario"].replace("P3_stuck_load", "P4_hk_generation_halt")
        self.assertProblem(b, "PASS-4 has 2 anomaly reports")

    def test_a_report_stating_another_fault_class(self):
        b = base()
        ar(b, "AR-003")["fields"]["Fault class"] = "HUG-EPS-004(a), single array-string"
        self.assertProblem(b, "AR-003's fault class does not state PASS-4's")

    def test_a_report_missing_one_of_its_contacts(self):
        b = base()
        f = ar(b, "AR-001")["fields"]
        f["Contacts"] = f["Contacts"].replace("`2026-09-20-P2b` (response)", "")
        self.assertProblem(b, "AR-001 names contacts ['2026-09-20-P2a']")

    def test_a_report_missing_its_pass_re_fly_record(self):
        b = relabel(base(), "2026-10-11-P4", "P4_hk_generation_halt_refly")
        f = ar(b, "AR-003")["fields"]
        f["Contact"] = f["Contact"].replace("`2026-10-11-P4`", "")
        self.assertProblem(b, "the records that flew PASS-4 are ['2026-10-11-P4']")

    def test_a_report_with_no_response_section(self):
        b = base()
        a = ar(b, "AR-002")
        a["headings"] = [h for h in a["headings"] if "response" not in h.lower()]
        self.assertProblem(b, "AR-002 has no response section")

    def test_a_report_with_no_outcome_section(self):
        b = base()
        a = ar(b, "AR-003")
        a["headings"] = [h for h in a["headings"] if "outcome" not in h.lower()]
        self.assertProblem(b, "AR-003 has no outcome section")

    def test_a_report_with_no_findings_section(self):
        b = base()
        a = ar(b, "AR-002")
        a["has_findings_section"], a["findings"] = False, []
        self.assertProblem(b, "AR-002 has no 'Findings raised by this anomaly' section")

    def test_a_finding_that_never_reached_the_register(self):
        b = base()
        a = ar(b, "AR-002")
        a["findings"][1] = a["findings"][1].replace("Registered as OF-024.",
                                                    "Not yet in the register.")
        self.assertProblem(b, "AR-002 finding 2 says it is not yet in the register")

    def test_a_finding_citing_an_entry_the_register_does_not_hold(self):
        b = base()
        a = ar(b, "AR-001")
        a["findings"][0] = a["findings"][0].replace("OF-019", "OF-999")
        self.assertProblem(b, "AR-001 finding 1 cites ['OF-999'], not in the register")


if __name__ == "__main__":
    unittest.main()
