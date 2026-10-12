#!/usr/bin/env python3
"""The completion-record contract, at both polarities (B13, HUG-OPS-001/002).

The acceptance for Phase 5 is a validator that enforces the contract at both polarities —
missing entry, duplicate entry, invented evidence on an omitted step, all red.

WHY EACH RED CASE IS A WAY A RECORD LOOKS COMPLETE AND SAYS NOTHING. A completion record
is the artifact that turns an execution into evidence, and the failure mode is never a
record that is obviously wrong. It is one that reads as thorough: every step present,
every state filled in, and no way to tell from it whether anybody looked at the
spacecraft. Each case below is one of those shapes.

The fixtures are built FROM the procedure definition, so a step added to
`defs/procedures.yaml` appears in them without an edit. A hand-written fixture would go
stale the first time a procedure changed, and the suite would keep passing against a
contract nobody executes.
"""
import copy
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hugdefs                                                    # noqa: E402
import pass_report                                                # noqa: E402


def procedure(proc_id="PROC-001"):
    return pass_report.procedure_by_id(proc_id)


def valid_report(proc_id="PROC-001", pass_id="2026-08-08-A"):
    """A report that satisfies every clause. The suite's green baseline.

    Built from the procedure so it cannot drift from it: every step gets an entry,
    decision steps get a declared branch and an observation, every `records:` field the
    step declares is filled in, and a branch that `requires` another step's record finds
    that record there.
    """
    proc = procedure(proc_id)
    record = []
    for step in proc["steps"]:
        entry = {
            "step": step["id"],
            "role": step["role"],
            "operator": "Dan Lee-Odinson",
            "state": "completed",
        }
        if step.get("records"):
            entry["records"] = {field: "recorded value"
                                for field in step["records"]}
        if step.get("decision"):
            entry["branch"] = step["decision"]["branches"][0]["outcome"]
            entry["observation"] = "what was seen that selected this branch"
        record.append(entry)
    entries = {e["step"]: e for e in record}
    for step in proc["steps"]:
        need = (step.get("decision") or {}).get("branches", [{}])[0].get("requires")
        if need:
            entries[need["step"]].setdefault("records", {})[need["record"]] = need["equals"]
    return {
        "pass_id": pass_id,
        "procedure": proc_id,
        "executed_utc": "2026-08-08T02:00:00Z",
        "pass_plan": {"window_aos_utc": "2026-08-08T02:00:00Z",
                      "window_los_utc": "2026-08-08T02:07:00Z",
                      "predicted_soc_pct": 78},
        "event_timeline": [{"utc": "2026-08-08T02:00:00Z", "event": "AOS"}],
        "limit_violations": [],
        "actions": [{"step": proc["steps"][0]["id"], "action": "pass plan reviewed"}],
        "completion_record": record,
        "anomalies": [],
    }


def step_with(predicate, proc_id="PROC-001"):
    return next(s for s in procedure(proc_id)["steps"] if predicate(s))


def entry_for(report, step_id):
    return next(e for e in report["completion_record"] if e["step"] == step_id)


class TestTheBaselineIsValid(unittest.TestCase):
    """GREEN. If this fails every red case below is meaningless."""
    verifies = ("HUG-OPS-002",)
    polarity = "green"

    def test_a_complete_record_validates(self):
        for proc_id in ("PROC-001", "PROC-002", "PROC-003"):
            with self.subTest(procedure=proc_id):
                ok, findings = pass_report.validate(valid_report(proc_id))
                self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_the_baseline_covers_every_step(self):
        """Guards the green case from passing over a truncated fixture."""
        for proc_id in ("PROC-001", "PROC-002", "PROC-003"):
            report = valid_report(proc_id)
            self.assertEqual(len(report["completion_record"]),
                             len(procedure(proc_id)["steps"]))


class TestEveryStepIsAccountedFor(unittest.TestCase):
    """RED — the three the acceptance names first."""
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def test_a_missing_entry(self):
        report = valid_report()
        dropped = report["completion_record"].pop(4)
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any(dropped["step"] in str(f) and "NO entry" in str(f)
                            for f in findings))

    def test_a_duplicate_entry(self):
        report = valid_report()
        report["completion_record"].append(copy.deepcopy(
            report["completion_record"][0]))
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("2 entries" in str(f) for f in findings))

    def test_an_entry_for_a_step_the_procedure_does_not_have(self):
        report = valid_report()
        report["completion_record"].append({"step": "PROC-001-S99",
                                            "state": "completed",
                                            "role": "EPS", "operator": "someone"})
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("not a step of" in str(f) for f in findings))

    def test_an_empty_completion_record(self):
        """The shape a record takes when the pass was flown and nobody wrote it up."""
        report = valid_report()
        report["completion_record"] = []
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertGreaterEqual(len(findings), len(procedure()["steps"]))

    def test_a_missing_report_section(self):
        for section in ("pass_plan", "event_timeline", "limit_violations", "actions",
                        "anomalies"):
            with self.subTest(section=section):
                report = valid_report()
                report.pop(section)
                ok, findings = pass_report.validate(report)
                self.assertFalse(ok)
                self.assertTrue(any(section in str(f) for f in findings))


class TestInventedEvidenceOnAnOmittedStep(unittest.TestCase):
    """RED — the third shape the acceptance names, and the most dangerous.

    An omitted step was not executed. Anything it claims to have observed is evidence
    for something nobody did, and a reviewer skimming states would read it as taken.
    """
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def _omit(self, report, step_id, **extra):
        entry = entry_for(report, step_id)
        entry.clear()
        entry.update({"step": step_id, "state": "omitted", "anomaly": "ANOM-001"})
        entry.update(extra)
        report["anomalies"] = [{
            "id": "ANOM-001", "step": step_id,
            "finding": "step not executed",
            "feasibility": "the step recurs on the next pass of this procedure",
            "disposition": "re_execution",
            "re_executed_as": {"pass_id": "2026-08-09-A", "step": step_id},
        }]
        return report

    def test_an_omitted_step_carrying_an_observation(self):
        step = step_with(lambda s: s.get("decision"))
        report = self._omit(valid_report(), step["id"],
                            observation="the counter was advancing")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("inventing evidence" in str(f) for f in findings))

    def test_an_omitted_step_carrying_a_branch(self):
        step = step_with(lambda s: s.get("decision"))
        report = self._omit(valid_report(), step["id"], branch="acquired")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("inventing evidence" in str(f) for f in findings))

    def test_an_omitted_decision_step_that_does_not_record_that_nothing_was_observed(self):
        """HUG-OPS-002 asks for that positively. Silence and 'nothing happened' are
        different records, and only one of them can be reviewed."""
        step = step_with(lambda s: s.get("decision"))
        report = self._omit(valid_report(), step["id"])
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("no observation was made" in str(f) for f in findings))

    def test_a_properly_omitted_decision_step_is_accepted(self):
        """GREEN. A validator that rejected every omission would push operators to
        mark skipped steps completed, which is the opposite of what it is for."""
        step = step_with(lambda s: s.get("decision"))
        report = self._omit(valid_report(), step["id"], no_observation_made=True)
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_an_omitted_step_with_no_anomaly_reference(self):
        step = step_with(lambda s: s.get("decision"))
        report = self._omit(valid_report(), step["id"], no_observation_made=True)
        entry_for(report, step["id"]).pop("anomaly")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("no anomaly reference" in str(f) for f in findings))

    def test_an_omitted_step_referencing_an_anomaly_that_is_not_there(self):
        step = step_with(lambda s: s.get("decision"))
        report = self._omit(valid_report(), step["id"], no_observation_made=True)
        entry_for(report, step["id"])["anomaly"] = "ANOM-999"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("not in the report" in str(f) for f in findings))


class TestTheOmittedStateIsPermanent(unittest.TestCase):
    """RED — the clause that makes every other clause worth having.

    A record that could be healed after the fact is unfalsifiable: any gap could be
    closed retroactively by the person who left it.
    """
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def _omitted(self, **anomaly):
        step = step_with(lambda s: s.get("decision"))
        report = valid_report()
        entry = entry_for(report, step["id"])
        entry.clear()
        entry.update({"step": step["id"], "state": "omitted", "anomaly": "ANOM-001",
                      "no_observation_made": True})
        base = {"id": "ANOM-001", "step": step["id"], "finding": "not executed",
                "feasibility": "recurs next pass", "disposition": "re_execution",
                "re_executed_as": {"pass_id": "2026-08-09-A", "step": step["id"]}}
        base.update(anomaly)
        report["anomalies"] = [base]
        return report

    def test_a_re_execution_claimed_in_the_same_pass(self):
        """The self-healing record. Re-execution is at the NEXT opportunity and is
        recorded THERE; claiming it here rewrites a missed step as a taken one."""
        report = self._omitted(re_executed_as={"pass_id": "2026-08-08-A",
                                               "step": "PROC-001-S05"})
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("truthful and permanent" in str(f) for f in findings))

    def test_a_re_execution_naming_no_pass(self):
        report = self._omitted(re_executed_as={"step": "PROC-001-S05"})
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)

    def test_an_undispositioned_omission(self):
        report = self._omitted(disposition=None)
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)

    def test_a_third_disposition_nobody_defined(self):
        report = self._omitted(disposition="will_look_into_it")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("no third option" in str(f) for f in findings))

    def test_an_owner_acceptance_with_nobody_accepting(self):
        report = self._omitted(disposition="owner_risk_acceptance",
                               rationale="low consequence", re_executed_as=None)
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("nobody named as accepting" in str(f) for f in findings))

    def test_an_owner_acceptance_with_no_rationale(self):
        report = self._omitted(disposition="owner_risk_acceptance",
                               accepted_by="Dan Lee-Odinson", re_executed_as=None)
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("no rationale" in str(f) for f in findings))

    def test_a_disposition_with_no_feasibility_determination(self):
        """The corrective-action choice is itself a decision: 'where feasible' is its
        selector. A branch whose selector is unstated is one nobody can review."""
        report = self._omitted(feasibility=None)
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("feasibility" in str(f) for f in findings))

    def test_a_properly_dispositioned_owner_acceptance_is_accepted(self):
        """GREEN."""
        report = self._omitted(disposition="owner_risk_acceptance",
                               accepted_by="Dan Lee-Odinson",
                               rationale="the step cannot recur; commissioning is over",
                               re_executed_as=None)
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))


class TestCompletedMeansSomethingWasObserved(unittest.TestCase):
    """RED — the central hole HUG-OPS-002 leaves open on its own.

    The requirement mandates evidence only on a completed DECISION step, so a record
    could mark every ordinary step completed, carry nothing, and satisfy the letter of
    it. The procedure's own `records:` closes that: a step that declares what it records
    is a step whose completed entry must carry those values.
    """
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def test_a_completed_step_that_records_none_of_its_declared_values(self):
        step = step_with(lambda s: s.get("records"))
        report = valid_report()
        entry_for(report, step["id"]).pop("records")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("claimed rather than executed" in str(f)
                            for f in findings))

    def test_a_completed_step_missing_one_declared_value(self):
        step = step_with(lambda s: len(s.get("records") or []) > 1)
        report = valid_report()
        dropped = step["records"][0]
        entry_for(report, step["id"])["records"].pop(dropped)
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any(dropped in str(f) for f in findings))

    def test_a_completed_step_with_a_blank_value(self):
        """A field present and empty is the same claim as one absent, dressed up."""
        step = step_with(lambda s: s.get("records"))
        report = valid_report()
        entry_for(report, step["id"])["records"][step["records"][0]] = "   "
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)

    def test_a_completed_step_with_no_operator(self):
        """An execution nobody performed is not one."""
        report = valid_report()
        report["completion_record"][0].pop("operator")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("nobody behind it" in str(f) for f in findings))

    def test_a_step_executed_as_the_wrong_role(self):
        report = valid_report()
        step = report["completion_record"][0]
        step["role"] = "PLAN" if step["role"] != "PLAN" else "EPS"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("assigns it to" in str(f) for f in findings))


class TestDecisionStepsCarryTheirBranchAndObservation(unittest.TestCase):
    """RED."""
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def test_a_completed_decision_with_no_branch(self):
        step = step_with(lambda s: s.get("decision"))
        report = valid_report()
        entry_for(report, step["id"]).pop("branch")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("nobody can show was made" in str(f) for f in findings))

    def test_a_completed_decision_with_no_observation(self):
        step = step_with(lambda s: s.get("decision"))
        report = valid_report()
        entry_for(report, step["id"]).pop("observation")
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("nobody can show was earned" in str(f) for f in findings))

    def test_a_branch_the_procedure_does_not_declare(self):
        step = step_with(lambda s: s.get("decision"))
        report = valid_report()
        entry_for(report, step["id"])["branch"] = "it_seemed_fine"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("does not declare" in str(f) for f in findings))

    def test_every_declared_branch_is_accepted(self):
        """GREEN. A validator that only accepted the happy branch would make the
        unhappy ones unrecordable, and an operator would record the happy one."""
        step = step_with(lambda s: s.get("decision"))
        for branch in step["decision"]["branches"]:
            with self.subTest(branch=branch["outcome"]):
                report = valid_report()
                entry_for(report, step["id"])["branch"] = branch["outcome"]
                ok, findings = pass_report.validate(report)
                self.assertTrue(ok, "\n".join(str(f) for f in findings))


class TestNotApplicableIsNotAnEscapeHatch(unittest.TestCase):
    """RED. Applicability is decided by the same person writing the record, so left
    unchecked it defeats the whole omission mechanism: anything skipped becomes 'not
    applicable' and no finding is ever raised."""
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def test_not_applicable_on_a_step_that_always_applies(self):
        step = step_with(lambda s: str(s.get("applicability")) == "always")
        report = valid_report()
        entry = entry_for(report, step["id"])
        entry.clear()
        entry.update({"step": step["id"], "state": "not_applicable",
                      "basis": "we were busy"})
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("always applies" in str(f) for f in findings))

    def test_not_applicable_with_no_basis(self):
        step = step_with(lambda s: s.get("applicable_when"))
        report = valid_report()
        entry = entry_for(report, step["id"])
        entry.clear()
        entry.update({"step": step["id"], "state": "not_applicable"})
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("better word" in str(f) for f in findings))

    def test_not_applicable_contradicted_by_the_branch_actually_recorded(self):
        """The step that closes the hatch. A step cannot be inapplicable because of a
        decision that in fact went the other way."""
        step = step_with(lambda s: s.get("applicable_when"))
        gate = step["applicable_when"]
        report = valid_report()
        entry_for(report, gate["step"])["branch"] = gate["branch"]
        entry = entry_for(report, step["id"])
        entry.clear()
        entry.update({"step": step["id"], "state": "not_applicable",
                      "basis": "no activation was planned"})
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("went the other way" in str(f) for f in findings))

    def test_not_applicable_consistent_with_the_branch_is_accepted(self):
        """GREEN. When the gate really did go the other way, the step really is
        inapplicable."""
        step = step_with(lambda s: s.get("applicable_when"))
        gate = step["applicable_when"]
        other = next(b["outcome"] for b in procedure()["steps"][
            [s["id"] for s in procedure()["steps"]].index(gate["step"])
        ]["decision"]["branches"] if b["outcome"] != gate["branch"])
        report = valid_report()
        entry_for(report, gate["step"])["branch"] = other
        for dependent in procedure()["steps"]:
            if (dependent.get("applicable_when") or {}).get("step") == gate["step"]:
                entry = entry_for(report, dependent["id"])
                entry.clear()
                entry.update({"step": dependent["id"], "state": "not_applicable",
                              "basis": f"{gate['step']} selected {other}"})
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))


class TestTheStateSetIsBounded(unittest.TestCase):
    verifies = ("HUG-OPS-002",)

    def test_a_state_outside_the_set(self):
        report = valid_report()
        report["completion_record"][0]["state"] = "mostly done"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("bounded set" in str(f) for f in findings))

    def test_the_state_set_comes_from_the_record(self):
        self.assertEqual(hugdefs.load_procedures()["completion_states"],
                         ["completed", "not_applicable", "omitted"])


class TestTheProceduresSatisfyHugOps001(unittest.TestCase):
    """The procedures themselves, not the records made against them."""
    verifies = ("HUG-OPS-001",)

    def test_every_step_has_a_stable_identifier_of_the_required_form(self):
        import re
        for proc in hugdefs.load_procedures()["procedures"]:
            for i, step in enumerate(proc["steps"], 1):
                self.assertRegex(step["id"], r"^PROC-\d{3}-S\d{2}$")
                self.assertEqual(step["id"], f"{proc['id']}-S{i:02d}",
                                 "step identifiers must be stable and sequential")

    def test_every_step_names_a_role_that_exists(self):
        roles = {r["id"] for r in hugdefs.load_procedures()["roles"]}
        for proc in hugdefs.load_procedures()["procedures"]:
            for step in proc["steps"]:
                self.assertIn(step["role"], roles)

    def test_every_step_names_the_telemetry_it_checks(self):
        """`checks` may be empty for a planning or command-send step, but the key must
        be present: an absent key is an unanswered question, an empty list is an
        answered one."""
        for proc in hugdefs.load_procedures()["procedures"]:
            for step in proc["steps"]:
                self.assertIn("checks", step, f"{step['id']} names no telemetry")

    def test_every_checked_mnemonic_is_in_the_dictionary(self):
        """A procedure that told an operator to read a point that does not exist would
        be discovered at the console, during a pass."""
        known = {p["mnemonic"] for p in hugdefs.points(hugdefs.load_tlm_cmd())}
        for proc in hugdefs.load_procedures()["procedures"]:
            for step in proc["steps"]:
                for mnemonic in step.get("checks") or []:
                    self.assertIn(mnemonic, known,
                                  f"{step['id']} checks {mnemonic}, which is not a "
                                  f"dictionary point")

    def test_every_decision_step_names_an_observation_for_every_branch(self):
        """HUG-OPS-001's hardest clause: EACH branch, not the happy one. A branch with
        no stated observation is one an operator cannot select under stress, which is
        the only time the procedure is read."""
        for proc in hugdefs.load_procedures()["procedures"]:
            for step in proc["steps"]:
                decision = step.get("decision")
                if not decision:
                    continue
                self.assertGreaterEqual(len(decision["branches"]), 2,
                                        f"{step['id']} is a decision with one branch")
                for branch in decision["branches"]:
                    self.assertTrue(str(branch.get("observation", "")).strip(),
                                    f"{step['id']} branch {branch['outcome']} names no "
                                    f"observation")
                    self.assertTrue(str(branch.get("then", "")).strip(),
                                    f"{step['id']} branch {branch['outcome']} says "
                                    f"nothing about what follows")

    def test_the_three_procedures_the_requirement_names_exist(self):
        ids = {p["id"] for p in hugdefs.load_procedures()["procedures"]}
        self.assertEqual(ids, {"PROC-001", "PROC-002", "PROC-003"})

    def test_proc_001_invokes_the_pass_setup_tool(self):
        """FM-GND-04's detection and response, made a tool by D-010."""
        tools = [s.get("tool", "") for s in procedure("PROC-001")["steps"]]
        self.assertTrue(any("pass_setup.py" in str(t) for t in tools),
                        "PROC-001 does not invoke the pre-pass configuration check")

    def test_proc_003_distinguishes_the_conditions_that_present_alike(self):
        """Three different things present as 'the counter is not advancing at the
        ground': a spacecraft halt, a ground-link loss, and a monitor that cannot read
        (OF-006). A procedure whose branches do not separate them sends a hazardous
        command to a vehicle nothing has observed."""
        step = step_with(lambda s: s.get("decision") and "three" in
                         str(s["decision"]["question"]).lower(), "PROC-003")
        outcomes = {b["outcome"] for b in step["decision"]["branches"]}
        self.assertEqual(len(outcomes), 3, outcomes)
        joined = " ".join(b["observation"] for b in step["decision"]["branches"])
        self.assertIn("READ_FAULT", joined)


class TestInPassReExecution(unittest.TestCase):
    """PROC-001-S03's no-go branch orders S02 re-run inside the same pass.

    HUG-OPS-002 gives the step exactly one entry, so the failed attempt has nowhere to
    go unless the entry can hold it. If it cannot, the record keeps only the attempt
    that worked and the pass looks like it went right the first time.
    """
    verifies = ("HUG-OPS-002",)

    def _repeatable(self):
        return step_with(lambda s: s.get("repeatable"))["id"]

    def test_the_procedure_marks_the_steps_it_orders_re_run(self):
        # S03's no-go branch and PROC-003's ground-path branch both say re-run S02.
        # If S02 is not marked repeatable, a truthful record of that re-run is refused.
        ordering = [s for s in procedure("PROC-001")["steps"] + procedure("PROC-003")["steps"]
                    for b in (s.get("decision") or {}).get("branches", [])
                    if "re-run PROC-001-S02" in (b.get("then") or "")]
        self.assertTrue(ordering, "no branch orders a re-run; this test guards nothing")
        self.assertTrue(pass_report.step_index(procedure("PROC-001"))["PROC-001-S02"]
                        .get("repeatable"))

    def test_green_a_described_re_run_is_accepted(self):
        report = valid_report()
        entry = entry_for(report, self._repeatable())
        entry["attempts"] = 2
        entry["earlier_attempts"] = [{"outcome": "NO-GO on loaded-vs-repository; "
                                                 "reloaded config per FM-GND-04 (e)"}]
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, findings)

    def test_red_a_second_entry_is_still_refused(self):
        # The re-run must go INSIDE the entry. A duplicate entry would let a record
        # carry both a completed and an omitted account of the same step.
        report = valid_report()
        step_id = self._repeatable()
        report["completion_record"].append(dict(entry_for(report, step_id)))
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("2 entries" in f.detail for f in findings), findings)

    def test_red_a_counted_attempt_that_is_never_described(self):
        report = valid_report()
        entry_for(report, self._repeatable())["attempts"] = 3
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("owed" in f.detail for f in findings), findings)

    def test_red_an_earlier_attempt_with_no_outcome(self):
        report = valid_report()
        entry = entry_for(report, self._repeatable())
        entry["attempts"] = 2
        entry["earlier_attempts"] = [{"records": {"pass_setup_verdict": "NO-GO"}}]
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("names no outcome" in f.detail for f in findings), findings)

    def test_red_a_re_run_of_a_step_the_procedure_never_orders_re_run(self):
        report = valid_report()
        step = step_with(lambda s: not s.get("repeatable"))
        entry = entry_for(report, step["id"])
        entry["attempts"] = 2
        entry["earlier_attempts"] = [{"outcome": "did it twice"}]
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("does not mark it repeatable" in f.detail
                            for f in findings), findings)

    def test_red_the_count_and_the_account_contradicting_each_other(self):
        report = valid_report()
        entry_for(report, self._repeatable())["earlier_attempts"] = [{"outcome": "x"}]
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("contradict" in f.detail for f in findings), findings)


class TestAPassThatInvokesAContingencyProcedure(unittest.TestCase):
    """PROC-001 hands off to PROC-002 and PROC-003 from named branches.

    A pass that followed those instructions has to be able to record the contingency
    work. Without it the operator either loses the work or files a second report
    claiming to be a separate pass that never happened.
    """
    verifies = ("HUG-OPS-001", "HUG-OPS-002")

    def _handoff(self, target):
        for step in procedure("PROC-001")["steps"]:
            for branch in (step.get("decision") or {}).get("branches", []):
                if target in (branch.get("then") or ""):
                    return step["id"], branch["outcome"]
        raise AssertionError(f"PROC-001 has no branch invoking {target}")

    def _invoking_report(self, target="PROC-002"):
        step_id, outcome = self._handoff(target)
        report = valid_report()
        entry_for(report, step_id)["branch"] = outcome
        sub = valid_report(target, pass_id="unused")
        report["invoked_procedures"] = [{
            "procedure": target, "invoked_from": step_id,
            "completion_record": sub["completion_record"]}]
        return report, step_id, outcome

    def test_the_handoff_branches_exist(self):
        for target in ("PROC-002", "PROC-003"):
            self.assertTrue(self._handoff(target))

    def test_green_a_contingency_procedure_run_from_its_branch(self):
        report, _, _ = self._invoking_report()
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, findings)

    def test_red_the_invoking_step_took_a_different_branch(self):
        # The record says PROC-002 ran and also says the decision that would have
        # ordered it went the other way. Both cannot be true.
        report, step_id, outcome = self._invoking_report()
        other = next(b["outcome"]
                     for b in pass_report.step_index(procedure("PROC-001"))[step_id]
                     ["decision"]["branches"] if b["outcome"] != outcome)
        entry_for(report, step_id)["branch"] = other
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("went the other way" in f.detail for f in findings), findings)

    def test_red_invoked_from_a_step_that_never_calls_it(self):
        report, _, _ = self._invoking_report()
        report["invoked_procedures"][0]["invoked_from"] = "PROC-001-S01"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("never calls it" in f.detail or "no branch whose instruction"
                            in f.detail for f in findings), findings)

    def test_red_invoked_from_a_step_that_does_not_exist(self):
        report, _, _ = self._invoking_report()
        report["invoked_procedures"][0]["invoked_from"] = "PROC-001-S99"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("unattached work" in f.detail for f in findings), findings)

    def test_red_the_contingency_record_is_held_to_the_same_rules(self):
        # An invoked procedure is not a lower tier of evidence. A missing step in
        # PROC-002's record is the same omission finding it would be in PROC-001's.
        report, _, _ = self._invoking_report()
        dropped = report["invoked_procedures"][0]["completion_record"].pop()["step"]
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any(dropped in f.detail and "NO entry" in f.detail
                            for f in findings), findings)

    def test_red_an_unknown_contingency_procedure(self):
        report, step_id, _ = self._invoking_report()
        report["invoked_procedures"][0]["procedure"] = "PROC-999"
        ok, findings = pass_report.validate(report)
        self.assertFalse(ok)
        self.assertTrue(any("PROC-999" in f.detail for f in findings), findings)


def invoking_report(target="PROC-002"):
    """A PROC-001 report that invokes `target` from the branch ordering it, as
    2026-09-20-P2b invokes PROC-002. Returns the report and the invoked record."""
    for step in procedure("PROC-001")["steps"]:
        for branch in (step.get("decision") or {}).get("branches", []):
            if target in (branch.get("then") or ""):
                report = valid_report()
                entry_for(report, step["id"])["branch"] = branch["outcome"]
                sub = valid_report(target, pass_id="unused")["completion_record"]
                report["invoked_procedures"] = [{"procedure": target,
                                                 "invoked_from": step["id"],
                                                 "completion_record": sub}]
                return report, sub
    raise AssertionError(f"PROC-001 has no branch invoking {target}")


def pass3_shape(point="EPS_LOAD_I"):
    """PASS-3 as planned: PROC-002 invoked, entered on the load alarm, S02 taking `load
    alarm` and S03 `load excursion`. `point` swaps the alarm S01 confirmed."""
    report, sub = invoking_report()
    value = {"EPS_LOAD_I": 1.8, "EPS_BATT_SOC": 34.996}[point]
    by_step = {e["step"]: e for e in sub}
    by_step["PROC-002-S01"]["records"] = {"annunciated_point": point,
                                          "annunciated_value": value,
                                          "annunciated_level": "YELLOW"}
    by_step["PROC-002-S02"].update(
        branch="load alarm",
        observation="PROC-002 was entered on the point S01 confirmed")
    by_step["PROC-002-S03"].update(
        branch="load excursion",
        observation="EPS_LOAD_I 1.800 A with EPS_SA1_I and EPS_SA2_I both 1.70 A, SUNLIT")
    return report, sub


def the_rules_findings(report):
    """(ok, the findings raised by the `requires` rule alone). Other clauses' findings
    are left out, so a red case is never satisfied by a finding some other rule raised."""
    ok, findings = pass_report.validate(report)
    return ok, [f for f in findings if "which requires" in f.detail]


def the_procedures_with_the_rule_changed(equals):
    """An in-memory copy of defs/procedures.yaml with the load-alarm rule's value
    changed. None when the source declares no such rule."""
    procs = copy.deepcopy(hugdefs.load_procedures())
    proc = next(p for p in procs["procedures"] if p["id"] == "PROC-002")
    step = next(s for s in proc["steps"] if s["id"] == "PROC-002-S02")
    branch = next((b for b in step["decision"]["branches"]
                   if b["outcome"] == "load alarm"), {})
    if not branch.get("requires"):
        return None
    branch["requires"]["equals"] = equals
    return procs


class TestABranchMustBeEarnedByTheRecordItRequires(unittest.TestCase):
    """RED. PROC-002-S02's `load alarm` is selected by the point S01 confirmed.

    Accepted on its own say-so, it would let any operator skip S02's energy question
    after any alarm. Each case finds the `requires` rule's own finding, never just any
    finding: an omitted S01 raises other findings, and a red case satisfied by one of
    them would pass with the rule deleted.
    """
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def test_load_alarm_after_a_state_of_charge_alarm_is_refused(self):
        report, _sub = pass3_shape("EPS_BATT_SOC")
        ok, rule = the_rules_findings(report)
        self.assertEqual(len(rule), 1, f"the requires rule raised {rule}")
        self.assertFalse(ok)
        for word in ("'load alarm'", "PROC-002-S01", "annunciated_point", "EPS_LOAD_I",
                     "EPS_BATT_SOC"):
            self.assertIn(word, rule[0].detail)

    def test_load_alarm_with_s01_omitted_is_refused(self):
        report, sub = pass3_shape()
        s01 = next(e for e in sub if e["step"] == "PROC-002-S01")
        s01.clear()
        s01.update({"step": "PROC-002-S01", "state": "omitted", "anomaly": "ANOM-T"})
        report["anomalies"] = [{
            "id": "ANOM-T", "step": "PROC-002-S01", "finding": "S01 not executed",
            "disposition": "owner_risk_acceptance", "feasibility": "not re-executable",
            "accepted_by": "Flight Director", "rationale": "test"}]
        ok, rule = the_rules_findings(report)
        self.assertEqual(len(rule), 1, f"the requires rule raised {rule}")
        self.assertFalse(ok)
        for word in ("'load alarm'", "PROC-002-S01", "not completed", "'omitted'"):
            self.assertIn(word, rule[0].detail)

    def test_load_alarm_with_no_s01_entry_is_refused(self):
        report, sub = pass3_shape()
        sub[:] = [e for e in sub if e["step"] != "PROC-002-S01"]
        ok, rule = the_rules_findings(report)
        self.assertEqual(len(rule), 1, f"the requires rule raised {rule}")
        self.assertFalse(ok)
        self.assertIn("it has no entry", rule[0].detail)

    def test_with_the_rule_changed_in_the_source_the_pass3_shape_is_refused(self):
        """The rule comes from defs/procedures.yaml: change it there and the verdict
        changes, with nothing in the validator edited."""
        procs = self.the_changed_source()
        report, _sub = pass3_shape("EPS_LOAD_I")
        with mock.patch.object(pass_report.hugdefs, "load_procedures",
                               return_value=procs):
            ok, rule = the_rules_findings(report)
        self.assertEqual(len(rule), 1, f"the requires rule raised {rule}")
        self.assertFalse(ok)
        self.assertIn("EPS_BATT_SOC", rule[0].detail)

    def test_the_validator_names_no_step_or_mnemonic_of_the_rule(self):
        """Every value of every `requires` lives in the procedure, none in the code."""
        source = Path(pass_report.__file__).read_text(encoding="utf-8")
        needs = [b["requires"] for p in hugdefs.load_procedures()["procedures"]
                 for s in p["steps"] for b in (s.get("decision") or {}).get("branches", [])
                 if b.get("requires")]
        self.assertTrue(needs, "no branch declares requires; this test guards nothing")
        for need in needs:
            for value in need.values():
                self.assertNotIn(str(value), source)

    def the_changed_source(self):
        procs = the_procedures_with_the_rule_changed("EPS_BATT_SOC")
        self.assertIsNotNone(procs, "the load alarm branch declares no requires in "
                                    "defs/procedures.yaml; there is no rule to change")
        return procs


class TestABranchEarnedByTheRecordItRequiresIsAccepted(unittest.TestCase):
    """GREEN. The rule must not refuse PASS-3, the shape it was ruled for."""
    verifies = ("HUG-OPS-002",)
    polarity = "green"

    def test_the_pass3_shape_raises_no_finding(self):
        report, _sub = pass3_shape()
        ok, rule = the_rules_findings(report)
        self.assertEqual(rule, [])
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_with_the_rule_changed_in_the_source_the_state_of_charge_shape_passes(self):
        procs = the_procedures_with_the_rule_changed("EPS_BATT_SOC")
        self.assertIsNotNone(procs, "the load alarm branch declares no requires in "
                                    "defs/procedures.yaml; there is no rule to change")
        report, _sub = pass3_shape("EPS_BATT_SOC")
        with mock.patch.object(pass_report.hugdefs, "load_procedures",
                               return_value=procs):
            ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_the_rule_is_declared_in_the_procedure(self):
        step = pass_report.step_index(procedure("PROC-002"))["PROC-002-S02"]
        branch = next(b for b in step["decision"]["branches"]
                      if b["outcome"] == "load alarm")
        self.assertEqual(branch.get("requires"),
                         {"step": "PROC-002-S01", "record": "annunciated_point",
                          "equals": "EPS_LOAD_I"})


def pass4_shape():
    """PASS-4 as planned: frames lock at PROC-001-S05, the counter halts part-way through
    the contact, and PROC-003 is entered on the staleness annunciation and hands back at
    PROC-001-S06. Returns the report and its invoked item."""
    report = valid_report()
    entry_for(report, "PROC-001-S05")["branch"] = "acquired"
    sub = valid_report("PROC-003", pass_id="unused")["completion_record"]
    by_step = {e["step"]: e for e in sub}
    by_step["PROC-003-S01"]["records"] = {"last_frame_utc": "2026-10-11T19:05:00Z",
                                          "last_cdh_frame_cnt": 1200,
                                          "staleness_level": "RED"}
    by_step["PROC-003-S02"].update(
        branch="spacecraft-side",
        observation="HUGINN_INT CONNECTED, Tlm pkts frozen, staleness RED")
    by_step["PROC-003-S03"]["records"] = {"reset_command_utc": "2026-10-11T19:06:30Z"}
    by_step["PROC-003-S04"]["records"] = {"acc_cnt_post_reset": 1, "rej_cnt_post_reset": 0,
                                          "soc_pct_post_reset": 65.0}
    by_step["PROC-003-S05"].update(
        branch="restored", observation="CDH_FRAME_CNT advancing again, staleness GREEN")
    for step_id in ("PROC-003-S06", "PROC-003-S07", "PROC-003-S08", "PROC-003-S09"):
        by_step[step_id].clear()
        by_step[step_id].update({"step": step_id, "state": "not_applicable",
                                 "basis": "telemetry presentation; no command went "
                                          "unacknowledged"})
    item = {"procedure": "PROC-003", "invoked_on": "staleness",
            "resumed_at": "PROC-001-S06", "completion_record": sub}
    report["invoked_procedures"] = [item]
    return report, item


def the_procedures_with_the_entry_changed(one_of):
    """An in-memory copy of defs/procedures.yaml with PROC-003's entry evidence changed.
    None when the source declares no such entry."""
    procs = copy.deepcopy(hugdefs.load_procedures())
    proc = next(p for p in procs["procedures"] if p["id"] == "PROC-003")
    if not (proc.get("entered_on") or {}).get("requires"):
        return None
    proc["entered_on"]["requires"]["one_of"] = list(one_of)
    return procs


class TestAnAnnunciationEntryMustBeDeclaredAndShown(unittest.TestCase):
    """RED. A procedure entered on an alarm rather than from a branch.

    The second way into a contingency procedure has no branch to trace to, so each case
    is a way a record could claim it without earning it. Each finds the entry rule's own
    finding: several of these records raise other findings too, and a red case satisfied
    by one of them would pass with the rule deleted.
    """
    verifies = ("HUG-OPS-002",)
    polarity = "red"

    def _one(self, report, *words):
        """The one finding naming all of `words`, which only the entry rule writes."""
        ok, findings = pass_report.validate(report)
        matching = [f for f in findings if all(w in f.detail for w in words)]
        self.assertEqual(len(matching), 1, f"no single finding names {words}; the "
                                           f"validator raised {[str(f) for f in findings]}")
        self.assertFalse(ok)
        return matching[0]

    def test_invoked_on_a_procedure_that_declares_no_entry_is_refused(self):
        report = valid_report()
        report["invoked_procedures"] = [{
            "procedure": "PROC-002", "invoked_on": "staleness",
            "resumed_at": "PROC-001-S06",
            "completion_record": valid_report("PROC-002")["completion_record"]}]
        self._one(report, "PROC-002", "declares no entry")

    def test_invoked_on_and_invoked_from_together_are_refused(self):
        report, item = pass4_shape()
        item["invoked_from"] = "PROC-001-S05"
        self._one(report, "both invoked_on", "PROC-001-S05")

    def test_a_missing_resumed_at_is_refused(self):
        report, item = pass4_shape()
        del item["resumed_at"]
        self._one(report, "no resumed_at")

    def test_a_resumed_at_outside_the_governing_procedure_is_refused(self):
        report, item = pass4_shape()
        item["resumed_at"] = "PROC-002-S01"
        self._one(report, "PROC-002-S01", "not a step of PROC-001")

    def test_a_green_staleness_level_is_refused(self):
        report, item = pass4_shape()
        s01 = next(e for e in item["completion_record"] if e["step"] == "PROC-003-S01")
        s01["records"]["staleness_level"] = "GREEN"
        finding = self._one(report, "staleness_level: GREEN")
        for word in ("PROC-003-S01", "YELLOW", "RED"):
            self.assertIn(word, finding.detail)

    def test_an_s01_that_was_not_completed_is_refused(self):
        report, item = pass4_shape()
        s01 = next(e for e in item["completion_record"] if e["step"] == "PROC-003-S01")
        s01.clear()
        s01.update({"step": "PROC-003-S01", "state": "omitted", "anomaly": "ANOM-T"})
        report["anomalies"] = [{
            "id": "ANOM-T", "step": "PROC-003-S01", "finding": "S01 not executed",
            "disposition": "owner_risk_acceptance", "feasibility": "not re-executable",
            "accepted_by": "Flight Director", "rationale": "test"}]
        self._one(report, "PROC-003-S01", "not completed", "'omitted'")

    def test_with_the_entry_changed_in_the_source_the_pass4_shape_is_refused(self):
        """The evidence comes from defs/procedures.yaml: narrow it there to YELLOW and
        the RED record is refused, with nothing in the validator edited."""
        procs = the_procedures_with_the_entry_changed(["YELLOW"])
        self.assertIsNotNone(procs, "PROC-003 declares no entered_on.requires in "
                                    "defs/procedures.yaml; there is no entry to change")
        report, _item = pass4_shape()
        with mock.patch.object(pass_report.hugdefs, "load_procedures",
                               return_value=procs):
            self._one(report, "staleness_level: RED")

    def test_the_validator_names_no_step_field_or_level_of_the_entry(self):
        """Every value of every entered_on lives in the procedure, none in the code."""
        source = Path(pass_report.__file__).read_text(encoding="utf-8")
        entries = [p["entered_on"] for p in hugdefs.load_procedures()["procedures"]
                   if p.get("entered_on")]
        self.assertTrue(entries, "no procedure declares entered_on; this test guards "
                                 "nothing")
        for entry in entries:
            need = entry.get("requires") or {}
            values = [entry.get("annunciation"), need.get("step"), need.get("record")]
            values += list(need.get("one_of") or [])
            for value in values:
                self.assertIsNone(re.search(rf"\b{re.escape(str(value))}\b", source),
                                  f"{value!r} is written in pass_report.py")


class TestAnAnnunciationEntryThatIsDeclaredAndShownIsAccepted(unittest.TestCase):
    """GREEN. The rule must not refuse PASS-4, the shape it was ruled for."""
    verifies = ("HUG-OPS-002",)
    polarity = "green"

    def test_the_pass4_shape_passes(self):
        report, _item = pass4_shape()
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_with_the_entry_changed_in_the_source_a_green_level_passes(self):
        procs = the_procedures_with_the_entry_changed(["GREEN"])
        self.assertIsNotNone(procs, "PROC-003 declares no entered_on.requires in "
                                    "defs/procedures.yaml; there is no entry to change")
        report, item = pass4_shape()
        s01 = next(e for e in item["completion_record"] if e["step"] == "PROC-003-S01")
        s01["records"]["staleness_level"] = "GREEN"
        with mock.patch.object(pass_report.hugdefs, "load_procedures",
                               return_value=procs):
            ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_the_entry_is_declared_in_the_procedure(self):
        self.assertEqual(procedure("PROC-003").get("entered_on"),
                         {"annunciation": "staleness",
                          "requires": {"step": "PROC-003-S01", "record": "staleness_level",
                                       "one_of": ["YELLOW", "RED"]}})


class TestTheWorkedExample(unittest.TestCase):
    """The committed example must stay valid, or it teaches the wrong form."""
    verifies = ("HUG-OPS-002",)

    EXAMPLE = (REPO / "docs" / "pass_reports" / "EXAMPLE-2026-08-08-A" / "report.yaml")

    def test_the_example_validates(self):
        import yaml
        report = yaml.safe_load(self.EXAMPLE.read_text(encoding="utf-8"))
        ok, findings = pass_report.validate(report)
        self.assertTrue(ok, "\n".join(str(f) for f in findings))

    def test_the_example_shows_all_three_states(self):
        """A worked example carrying only completed entries would teach an operator
        that the other two states are theoretical."""
        import yaml
        report = yaml.safe_load(self.EXAMPLE.read_text(encoding="utf-8"))
        states = {e.get("state") for e in report["completion_record"]}
        self.assertEqual(states, {"completed", "not_applicable", "omitted"})

    def test_the_example_cannot_collide_with_a_real_pass(self):
        import yaml
        report = yaml.safe_load(self.EXAMPLE.read_text(encoding="utf-8"))
        self.assertTrue(report["pass_id"].startswith("EXAMPLE-"))


class TestTheTemplate(unittest.TestCase):
    verifies = ("HUG-OPS-002",)

    def test_the_template_pre_seeds_every_step(self):
        """An operator writing from memory writes the steps they remember; the ones
        they forgot are exactly the ones the record exists to surface."""
        for proc_id in ("PROC-001", "PROC-002", "PROC-003"):
            text = pass_report.template(proc_id)
            for step in procedure(proc_id)["steps"]:
                self.assertIn(step["id"], text)

    def test_the_template_is_not_valid_until_filled_in(self):
        """RED. A template that validated as-is would be a completed record of a pass
        nobody flew."""
        import yaml
        report = yaml.safe_load(pass_report.template("PROC-001"))
        ok, _findings = pass_report.validate(report)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
