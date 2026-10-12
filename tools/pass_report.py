#!/usr/bin/env python3
"""The per-step completion record, validated against its governing procedure (B13).

    python tools/pass_report.py --validate docs/pass_reports/<pass>/report.yaml
    python tools/pass_report.py --template PROC-001 > report.yaml

HUG-OPS-002 makes post-pass review a comparison of the completion record against the
governing procedure. This is that comparison, executed rather than remembered.

WHAT MAKES AN EXECUTION INTO EVIDENCE. A procedure that was followed and a procedure that
was claimed to have been followed produce the same feeling and different records. The
contract below is what separates them, and every clause of it is a way a record could look
complete while saying nothing:

  exactly one entry per step   a record covering the steps someone remembered is a record
                               of what they remembered
  a bounded state set          "mostly done" is not a state; the record admits three
  a basis on not-applicable    "not applicable" without a reason is an omission wearing a
                               better word
  branch AND observation on    a completed decision step with no branch is a decision
  a completed decision step    nobody can show was made, and a branch with no observation
                               is one nobody can show was earned
  NOTHING on an omitted step   an omitted step that carries an observation is claiming an
                               observation nobody made — the record contradicting itself
  an anomaly reference on      an omission with no disposition is a finding that was
  every omitted entry          noticed and dropped
  the omitted state is         a record that could be rewritten to completed after the
  permanent                    fact is not a record

THE PERMANENCE CLAUSE IS THE ONE THAT MATTERS MOST. HUG-OPS-002 ends: *"The omitted state
is truthful and permanent for the pass in which the step was missed."* Re-execution at the
next opportunity is recorded as a COMPLETED ENTRY FOR THE RE-EXECUTED STEP — in that later
pass's record — and referenced from the omitted entry. The omitted entry stays omitted
forever. A record that healed itself would make every completion record unfalsifiable,
because any gap could be closed retroactively by the person who left it.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hugdefs                                                    # noqa: E402

#: The report's own required content (HUG-OPS-002, first sentence). Named here so a
#: report missing a whole section fails as loudly as one missing a step entry.
REQUIRED_SECTIONS = ["pass_id", "procedure", "pass_plan", "event_timeline",
                     "limit_violations", "actions", "completion_record", "anomalies"]

#: Dispositions an omission finding may carry. Both are named by the requirement; there
#: is no third, and "will look into it" is not a disposition.
DISPOSITIONS = ["re_execution", "owner_risk_acceptance"]


class Finding:
    """One contract violation, naming the clause it breaks."""

    def __init__(self, clause, detail):
        self.clause, self.detail = clause, detail

    def __str__(self):
        return f"{self.clause}: {self.detail}"


def procedure_by_id(proc_id):
    for proc in hugdefs.load_procedures()["procedures"]:
        if proc["id"] == proc_id:
            return proc
    raise KeyError(proc_id)


def step_index(proc):
    return {step["id"]: step for step in proc["steps"]}


def validate(report, procedures=None):
    """(ok, [Finding, ...]) for one pass report.

    Pure over its inputs: the report and the procedure definition. No clock, no
    filesystem, no campaign state — so the tests drive every clause directly.
    """
    findings = []

    if not isinstance(report, dict):
        return False, [Finding("HUG-OPS-002", "the report is not a mapping")]

    for section in REQUIRED_SECTIONS:
        if section not in report:
            findings.append(Finding(
                "HUG-OPS-002",
                f"the report has no {section!r}. The requirement names the report's "
                f"contents; a missing section is not an empty one."))
    if "completion_record" not in report or "procedure" not in report:
        return False, findings

    try:
        proc = procedure_by_id(report["procedure"])
    except KeyError:
        return False, findings + [Finding(
            "HUG-OPS-002",
            f"governing procedure {report['procedure']!r} is not in "
            f"defs/procedures.yaml; the record cannot be compared against a procedure "
            f"that does not exist")]

    record = report.get("completion_record") or []
    if not isinstance(record, list):
        return False, findings + [Finding("HUG-OPS-002",
                                          "completion_record is not a list")]

    states = hugdefs.load_procedures()["completion_states"]
    anomaly_ids = {a.get("id") for a in (report.get("anomalies") or [])
                   if isinstance(a, dict)}

    sub, seen = _validate_record(proc, record, states, anomaly_ids, proc["id"])
    findings += sub
    findings += _validate_invoked(report, proc, seen, states, anomaly_ids)
    findings += _validate_anomalies(report, seen)
    return not findings, findings


def _validate_invoked(report, governing, governing_seen, states, anomaly_ids):
    """A pass that hands off to a contingency procedure has to be able to say so.

    PROC-001-S05's not-acquired branch says "Execute PROC-003" and S07's says
    "Execute PROC-002". Without somewhere to put them, a pass that followed those
    instructions would either lose the contingency work entirely or have to file a
    second report that claims to be a different pass. Each invoked procedure carries
    its own complete completion record, held to the same rules, and must be traceable
    to the branch that ordered it — otherwise "we also ran PROC-002" is an assertion.
    """
    out = []
    invoked = report.get("invoked_procedures") or []
    if not isinstance(invoked, list):
        return [Finding("HUG-OPS-002", "invoked_procedures is not a list")]

    for i, item in enumerate(invoked):
        if not isinstance(item, dict):
            out.append(Finding("HUG-OPS-002",
                               f"invoked_procedures[{i}] is not a mapping"))
            continue
        pid, frm = item.get("procedure"), item.get("invoked_from")
        try:
            sub_proc = procedure_by_id(pid)
        except KeyError:
            out.append(Finding("HUG-OPS-002",
                               f"invoked procedure {pid!r} is not in defs/procedures.yaml"))
            continue

        # The second way in, which D-018 ruling 2 created: entered on an annunciation
        # the procedure declares, rather than from a branch that calls it.
        if item.get("invoked_on") is not None:
            out += _validate_entered_on(item, sub_proc, governing, states, anomaly_ids)
            continue

        # The invoking step must exist, must have actually recorded a branch, and that
        # branch must be the one whose instruction was to execute this procedure.
        src = step_index(governing).get(frm)
        if src is None:
            out.append(Finding(
                "HUG-OPS-002",
                f"{pid} claims it was invoked from {frm!r}, which is not a step of "
                f"{governing['id']}. A contingency procedure with no origin in the "
                f"governing record is unattached work."))
        else:
            entry = (governing_seen.get(frm) or [{}])[0]
            branch = entry.get("branch")
            ordered = [b for b in (src.get("decision") or {}).get("branches", [])
                       if pid in (b.get("then") or "")]
            if not ordered:
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{frm} has no branch whose instruction is to execute {pid}. "
                    f"A procedure cannot be invoked by a step that never calls it."))
            elif branch not in [b.get("outcome") for b in ordered]:
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{pid} claims invocation from {frm}, but that step recorded "
                    f"branch {branch!r} — not one of "
                    f"{[b.get('outcome') for b in ordered]}, the branches that call "
                    f"{pid}. The record says the procedure was run and also says the "
                    f"decision that would have ordered it went the other way."))

        sub, _ = _validate_record(sub_proc, item.get("completion_record") or [],
                                  states, anomaly_ids, f"{pid} (invoked from {frm})")
        out += sub
    return out


def _validate_entered_on(item, proc, governing, states, anomaly_ids):
    """A contingency procedure entered on an annunciation, not from a branch.

    D-018 ruling 2: an alarm at any point in the contact sends the operator to the
    contingency procedure, and when it is done they return to the governing procedure
    where they left off. That entry has no branch to trace to, so the record names the
    annunciation instead (`invoked_on`) and the governing step it resumed at
    (`resumed_at`). It is not taken on the record's say-so. The procedure must declare
    that entry (`entered_on`), and the invoked record must hold the evidence the
    declaration names: the step it names completed, with the field it names recording
    one of the values it lists. Otherwise "the alarm went off" would be an assertion
    nobody can check, and any contingency procedure could be attached to any pass.
    Every annunciation, step, field and value is read from defs/procedures.yaml.
    """
    out = []
    pid, on = proc["id"], item.get("invoked_on")
    label = f"{pid} (invoked on {on})"
    sub, seen = _validate_record(proc, item.get("completion_record") or [],
                                 states, anomaly_ids, label)
    out += sub

    if item.get("invoked_from") is not None:
        out.append(Finding(
            "HUG-OPS-002",
            f"{pid} carries both invoked_on {on!r} and invoked_from "
            f"{item['invoked_from']!r}. An invocation has one origin: a branch of the "
            f"governing procedure that calls it, or an annunciation the procedure declares "
            f"as its entry. A record naming both cannot say which happened."))

    entry = proc.get("entered_on")
    if not entry:
        out.append(Finding(
            "HUG-OPS-002",
            f"{pid} is recorded as invoked on {on!r}, but {pid} declares no entry on an "
            f"annunciation in defs/procedures.yaml. It can be invoked only from a branch "
            f"of {governing['id']} that calls it."))
    elif entry.get("annunciation") != on:
        out.append(Finding(
            "HUG-OPS-002",
            f"{pid} is recorded as invoked on {on!r}; the annunciation it declares as its "
            f"entry is {entry.get('annunciation')!r}."))

    resumed = item.get("resumed_at")
    if not str(resumed or "").strip():
        out.append(Finding(
            "HUG-OPS-002",
            f"{pid} was invoked on {on!r} and records no resumed_at. Entered part-way "
            f"through the contact, the operator returns to {governing['id']} where they "
            f"left off; without the step they returned to, nothing shows the governing "
            f"procedure was picked up again."))
    elif resumed not in step_index(governing):
        out.append(Finding(
            "HUG-OPS-002",
            f"{pid} records resumed_at {resumed!r}, which is not a step of "
            f"{governing['id']}, the governing procedure the operator returns to."))

    if entry:
        need = entry.get("requires") or {}
        if not all(key in need for key in ("step", "record", "one_of")):
            out.append(Finding(
                "HUG-OPS-002",
                f"{pid} declares its entry on {entry.get('annunciation')!r} without "
                f"requires: step, record and one_of, so no record can show the "
                f"annunciation was real."))
        else:
            named, field, allowed = need["step"], need["record"], need["one_of"]
            done = [e for e in seen.get(named, []) if e.get("state") == "completed"]
            if not done:
                found = [e.get("state") for e in seen.get(named, [])]
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{pid} was invoked on {on!r}, which requires {named} to have "
                    f"recorded {field} as one of {allowed}. {named} is not completed in "
                    f"{label} ("
                    + (f"its entry is {found[0]!r}" if found else "it has no entry")
                    + "), so nothing in the record shows the annunciation."))
            else:
                value = (done[0].get("records") or {}).get(field)
                if str(value).strip() not in [str(a) for a in allowed]:
                    out.append(Finding(
                        "HUG-OPS-002",
                        f"{pid} was invoked on {on!r}, which requires {named} to have "
                        f"recorded {field} as one of {allowed}. {named} recorded "
                        + (f"{field}: {value}" if value is not None else f"no {field}")
                        + ", so the record shows no annunciation to enter on."))
    return out


def _validate_record(proc, record, states, anomaly_ids, label):
    """Validate one completion record against one procedure. Returns (findings, seen)."""
    findings = []
    steps = step_index(proc)

    # --- exactly one entry per step, keyed by the stable identifier
    seen = {}
    for i, entry in enumerate(record):
        if not isinstance(entry, dict) or "step" not in entry:
            findings.append(Finding("HUG-OPS-002",
                                    f"completion_record[{i}] has no step identifier"))
            continue
        step_id = entry["step"]
        if step_id not in steps:
            findings.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is not a step of {label}. An entry for a step the "
                f"procedure does not have is a record of a different procedure."))
        seen.setdefault(step_id, []).append(entry)

    for step_id in steps:
        count = len(seen.get(step_id, []))
        if count == 0:
            findings.append(Finding(
                "HUG-OPS-002",
                f"{step_id} has NO entry in {label}. A step without any entry is an "
                f"omission finding — it must be recorded truthfully as omitted and "
                f"dispositioned, not left out."))
        elif count > 1:
            findings.append(Finding(
                "HUG-OPS-002",
                f"{step_id} has {count} entries in {label}. Exactly one entry per "
                f"step: two entries let a record carry both a completed and an omitted "
                f"account of the same step. A step that was legitimately re-run inside "
                f"the pass records its attempts within its single entry."))

    # The branch each decision step actually recorded, so an applicability claim can be
    # checked against what happened rather than against what the writer asserts.
    recorded_branches = {}
    for step_id, entries in seen.items():
        for entry in entries:
            if entry.get("state") == "completed" and entry.get("branch"):
                recorded_branches[step_id] = entry["branch"]

    for step_id, entries in seen.items():
        step = steps.get(step_id)
        if step is None:
            continue
        for entry in entries:
            findings += _validate_entry(entry, step, states, anomaly_ids,
                                        recorded_branches)
    findings += _validate_requires(steps, seen, label)
    return findings, seen


def _validate_requires(steps, seen, label):
    """A branch selected by another step's record must find that record there.

    D-017 ruling 2 routes a load alarm straight to cause identification. That branch is
    selected by the point the procedure was entered on, not by anything the deciding step
    observes, so unchecked it is open to every record: after any alarm at all, an operator
    could take it and skip the energy question the step exists to ask. A branch that
    declares `requires: {step, record, equals}` is therefore accepted only when the step it
    names completed, IN THE SAME COMPLETION RECORD, with that value recorded. The same
    record, because a contingency procedure runs as an invoked record inside the governing
    one and its steps are numbered within it. Which step, which field and which value are
    read from defs/procedures.yaml. None of them is written here.
    """
    out = []
    for step_id, entries in seen.items():
        step = steps.get(step_id)
        if step is None or not step.get("decision"):
            continue
        branches = {b.get("outcome"): b for b in step["decision"]["branches"]}
        for entry in entries:
            if entry.get("state") != "completed":
                continue
            outcome = entry.get("branch")
            need = (branches.get(outcome) or {}).get("requires")
            if not need:
                continue
            if not all(key in need for key in ("step", "record", "equals")):
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{step_id} branch {outcome!r} declares `requires` without all of "
                    f"step, record and equals. The procedure states a condition the "
                    f"record cannot be checked against."))
                continue
            named, field, expected = need["step"], need["record"], need["equals"]
            done = [e for e in seen.get(named, []) if e.get("state") == "completed"]
            if not done:
                found = [e.get("state") for e in seen.get(named, [])]
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{step_id} records branch {outcome!r}, which requires {named} to "
                    f"have recorded {field}: {expected}. {named} is not completed in "
                    f"{label} ("
                    + (f"its entry is {found[0]!r}" if found else "it has no entry")
                    + "), so nothing in the record selects this branch."))
                continue
            value = (done[0].get("records") or {}).get(field)
            if str(value).strip() != str(expected):
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{step_id} records branch {outcome!r}, which requires {named} to "
                    f"have recorded {field}: {expected}. {named} recorded "
                    + (f"{field}: {value}" if value is not None else f"no {field}")
                    + ", so this branch was not open to this pass."))
    return out


def _validate_entry(entry, step, states, anomaly_ids,
                    recorded_branches=None):
    """One completion-record entry against one procedure step."""
    out = []
    step_id = step["id"]
    state = entry.get("state")
    is_decision = bool(step.get("decision"))

    if state not in states:
        out.append(Finding(
            "HUG-OPS-002",
            f"{step_id} state is {state!r}; the bounded set is {states}. A state "
            f"outside the set is an opinion, not a record."))
        return out

    # --- who ran it. The requirement's per-step record is of an EXECUTION, and an
    # execution nobody performed is not one.
    if state == "completed":
        if not str(entry.get("operator") or "").strip():
            out.append(Finding(
                "HUG-OPS-001/002",
                f"{step_id} is completed with no operator named. A step records who "
                f"executed it; a completed step with no executor is a claim with "
                f"nobody behind it."))
        if not str(entry.get("role") or "").strip():
            out.append(Finding(
                "HUG-OPS-001",
                f"{step_id} is completed with no role recorded; the procedure assigns "
                f"it to {step['role']}."))
        elif entry.get("role") != step["role"]:
            out.append(Finding(
                "HUG-OPS-001",
                f"{step_id} was executed as {entry['role']!r} but the procedure "
                f"assigns it to {step['role']!r}."))

    # --- IN-PASS RE-EXECUTION.
    #
    # PROC-001-S03's no-go branch says re-run S02; S12's ARG_RANGE branch says correct
    # the argument and re-send. Those re-runs happen inside one pass, and HUG-OPS-002
    # allows the step exactly one entry — so without somewhere to put them, the record
    # keeps only the attempt that finally worked and the failed one leaves no trace.
    # That is the same shape as an omission: something happened and was not written
    # down. The entry holds every attempt; its own records are the final attempt's.
    attempts = entry.get("attempts", 1)
    earlier = entry.get("earlier_attempts") or []
    if not isinstance(attempts, int) or attempts < 1:
        out.append(Finding("HUG-OPS-002",
                           f"{step_id} attempts is {attempts!r}; it must be a positive "
                           f"integer count of executions."))
    elif attempts > 1:
        if not step.get("repeatable"):
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} records {attempts} attempts, but the procedure does not "
                f"mark it repeatable. Either the step was re-run without the procedure "
                f"calling for it — which is an anomaly, not a completion — or the "
                f"procedure is wrong about its own step."))
        if len(earlier) != attempts - 1:
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} records {attempts} attempts but describes "
                f"{len(earlier)} earlier one(s); {attempts - 1} are owed. An attempt "
                f"counted but not described is a re-run the record admits to and "
                f"then declines to explain."))
        for j, att in enumerate(earlier):
            if not isinstance(att, dict) or not str(att.get("outcome") or "").strip():
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{step_id} earlier attempt {j + 1} names no outcome. Why the "
                    f"first attempt did not stand is the whole reason it is recorded."))
    elif earlier:
        out.append(Finding(
            "HUG-OPS-002",
            f"{step_id} describes {len(earlier)} earlier attempt(s) but records "
            f"attempts as 1. The count and the account contradict each other."))

    # --- T-1: A COMPLETED NON-DECISION STEP MUST STILL CARRY EVIDENCE.
    #
    # HUG-OPS-002 mandates evidence only on a completed DECISION step, so a record could
    # mark every ordinary step completed and carry nothing at all -- frame lock, the
    # state-of-health assessment, the final snapshot -- and satisfy the requirement to
    # the letter while showing that nothing was observed.
    #
    # This does not invent a rule on top of the requirement. It enforces the PROCEDURE's
    # own statement: a step that declares `records:` says what executing it produces, so
    # a completed entry missing those values is a step whose own definition says it was
    # not executed. An operator can write "green" for a panel whose limits never loaded;
    # they cannot write a battery voltage they did not read.
    if state == "completed":
        for field in (step.get("records") or []):
            if not str((entry.get("records") or {}).get(field, "")).strip():
                out.append(Finding(
                    "HUG-OPS-001/002",
                    f"{step_id} is completed but records no {field!r}. The procedure "
                    f"says this step records it; a completed entry without it is a "
                    f"step claimed rather than executed."))

    # --- not applicable requires the stated basis
    if state == "not_applicable":
        if not str(entry.get("basis") or "").strip():
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is not_applicable with no basis. The requirement asks for "
                f"the condition or branch outcome that made it inapplicable; without "
                f"one, 'not applicable' is an omission wearing a better word."))
        if str(step.get("applicability", "always")).strip() == "always":
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is marked not_applicable, but the procedure says it always "
                f"applies. There is no condition that could be its basis."))

    # --- a completed DECISION step carries the branch AND the selecting observation
    if is_decision and state == "completed":
        declared = [b["outcome"] for b in step["decision"]["branches"]]
        branch = entry.get("branch")
        if not branch:
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is a completed decision step with no branch recorded. A "
                f"decision with no branch is one nobody can show was made."))
        elif branch not in declared:
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} records branch {branch!r}, which the procedure does not "
                f"declare; its branches are {declared}."))
        if not str(entry.get("observation") or "").strip():
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is a completed decision step with no branch-selecting "
                f"observation. A branch with no observation is one nobody can show was "
                f"earned."))

    # --- T-2: "not applicable" is checked against what actually happened, where the
    # procedure says which branch governs it. Applicability is otherwise decided by the
    # same person writing the record, which makes it an unfalsifiable escape hatch from
    # the entire omission mechanism: anything skipped becomes "not applicable" and no
    # finding is ever raised.
    if state == "not_applicable" and step.get("applicable_when"):
        gate = step["applicable_when"]
        governing = (recorded_branches or {}).get(gate["step"])
        if governing == gate["branch"]:
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is not_applicable, but {gate['step']} recorded branch "
                f"{governing!r} -- which is exactly the branch that makes this step "
                f"APPLY. A step cannot be inapplicable because of a decision that went "
                f"the other way."))

    # --- an OMITTED step observed nothing. Anything else is the record contradicting
    # itself, and it is the shape that would let a skipped step read as a taken one.
    if state == "omitted":
        for field in ("branch", "observation"):
            if str(entry.get(field) or "").strip():
                out.append(Finding(
                    "HUG-OPS-002",
                    f"{step_id} is omitted but carries {field}="
                    f"{entry.get(field)!r}. An omitted step was not executed, so no "
                    f"observation was made and no branch was selected; recording one "
                    f"is inventing evidence for a step nobody performed."))
        if is_decision and not entry.get("no_observation_made"):
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is an omitted decision step and does not record that no "
                f"observation was made and no branch was selected. The requirement "
                f"asks for that positively: silence and 'nothing happened' are "
                f"different records."))
        anomaly = entry.get("anomaly")
        if not anomaly:
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} is omitted with no anomaly reference. An omission with no "
                f"disposition is a finding that was noticed and dropped."))
        elif anomaly not in anomaly_ids:
            out.append(Finding(
                "HUG-OPS-002",
                f"{step_id} references anomaly {anomaly!r}, which is not in the "
                f"report's disposition-of-anomalies content."))
    return out


def _validate_anomalies(report, seen):
    """Every omission finding is dispositioned, and the omitted state is permanent."""
    out = []
    omitted = {step_id for step_id, entries in seen.items()
               for e in entries if e.get("state") == "omitted"}
    for anomaly in (report.get("anomalies") or []):
        if not isinstance(anomaly, dict):
            out.append(Finding("HUG-OPS-002", "an anomaly entry is not a mapping"))
            continue
        aid = anomaly.get("id", "<unnamed>")
        if not anomaly.get("finding"):
            out.append(Finding("HUG-OPS-002",
                               f"anomaly {aid} states no finding"))
        disposition = anomaly.get("disposition")
        if anomaly.get("step") in omitted or disposition is not None:
            if disposition not in DISPOSITIONS:
                out.append(Finding(
                    "HUG-OPS-002",
                    f"anomaly {aid} disposition is {disposition!r}; the requirement "
                    f"names {DISPOSITIONS} and no third option. An undispositioned "
                    f"omission is one that will be forgotten."))
            elif disposition == "re_execution":
                ref = anomaly.get("re_executed_as") or {}
                if not (ref.get("pass_id") and ref.get("step")):
                    out.append(Finding(
                        "HUG-OPS-002",
                        f"anomaly {aid} disposes by re-execution but does not name the "
                        f"pass and step where the re-execution is recorded as a "
                        f"completed entry."))
                if ref.get("pass_id") == report.get("pass_id"):
                    out.append(Finding(
                        "HUG-OPS-002",
                        f"anomaly {aid} claims the re-execution happened in THIS pass "
                        f"({report.get('pass_id')!r}). The omitted state is truthful "
                        f"and permanent for the pass in which the step was missed; "
                        f"re-execution is at the NEXT opportunity and is recorded "
                        f"there."))
            if not str(anomaly.get("feasibility") or "").strip():
                out.append(Finding(
                    "HUG-OPS-002",
                    f"anomaly {aid} chooses a disposition without stating the "
                    f"feasibility determination. The requirement selects between "
                    f"re-execution 'where feasible' and owner risk acceptance, so "
                    f"feasibility is the observation that picks the branch -- and a "
                    f"choice whose selector is unstated is one nobody can review."))
            if disposition == "owner_risk_acceptance":
                if not str(anomaly.get("accepted_by") or "").strip():
                    out.append(Finding(
                        "HUG-OPS-002",
                        f"anomaly {aid} disposes by owner risk acceptance with nobody "
                        f"named as accepting it. The requirement says approved by the "
                        f"design authority."))
                if not str(anomaly.get("rationale") or "").strip():
                    out.append(Finding(
                        "HUG-OPS-002",
                        f"anomaly {aid} accepts a risk with no rationale. An "
                        f"acceptance without a reason is a decision nobody can review."))
    return out


def template(proc_id):
    """A completion record pre-seeded with every step, for the operator to fill in.

    Pre-seeded deliberately. An operator writing the record from memory writes the steps
    they remember, and the steps they forgot are exactly the ones the record exists to
    surface. Starting from the full list means a gap has to be filled in as `omitted`
    rather than simply never appearing.
    """
    proc = procedure_by_id(proc_id)
    lines = [
        f"# Pass report — {proc['id']} {proc['title']}",
        "#",
        "# Every step is listed. Fill in each entry. A step that did not happen is",
        "# `omitted` with an anomaly reference -- never deleted, and never rewritten to",
        "# completed later (HUG-OPS-002).",
        "",
        "pass_id: CHANGE-ME",
        f"procedure: {proc['id']}",
        "executed_utc: CHANGE-ME",
        "",
        "pass_plan:",
        "  window_aos_utc: CHANGE-ME",
        "  window_los_utc: CHANGE-ME",
        "  predicted_soc_pct: CHANGE-ME",
        "  planned_commands: []",
        "",
        "event_timeline: []",
        "limit_violations: []",
        "actions: []",
        "",
        "completion_record:",
    ]
    for step in proc["steps"]:
        lines += [
            f"  - step: {step['id']}",
            f"    role: {step['role']}",
            "    operator: CHANGE-ME",
            "    state: CHANGE-ME        # completed | not_applicable | omitted",
        ]
        if step.get("decision"):
            outcomes = "|".join(b["outcome"] for b in step["decision"]["branches"])
            lines += [
                f"    branch: CHANGE-ME       # {outcomes}",
                "    observation: CHANGE-ME  # what you saw that selected that branch",
            ]
        if str(step.get("applicability", "always")).strip() != "always":
            lines.append("    # basis: <required if state is not_applicable>")
    lines += ["", "anomalies: []", ""]
    return "\n".join(lines) + "\n"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--validate", metavar="REPORT")
    ap.add_argument("--template", metavar="PROC_ID")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # pragma: no cover
        pass

    if args.template:
        print(template(args.template), end="")
        return 0
    if not args.validate:
        ap.print_help()
        return 2

    import yaml
    path = Path(args.validate)
    try:
        report = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"[FAIL] {path} could not be read: {exc}")
        return 1

    ok, findings = validate(report)
    if ok:
        proc = procedure_by_id(report["procedure"])
        print(f"[PASS] {path.name}: the completion record accounts for all "
              f"{len(proc['steps'])} steps of {proc['id']} — one entry each, every "
              f"not-applicable entry with a basis, every completed decision with its "
              f"branch-selecting observation.")
        return 0
    print(f"[FAIL] {path.name}: {len(findings)} completion-record finding(s). Each is "
          f"an omission finding under HUG-OPS-002 and must be dispositioned as an "
          f"anomaly.")
    for finding in findings:
        print(f"  - {finding}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
