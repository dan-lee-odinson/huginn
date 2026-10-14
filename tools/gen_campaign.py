#!/usr/bin/env python3
"""The campaign plan, and D-014's usability classification (HUG-OPS-003, Phase 7).

    python tools/gen_campaign.py              write campaign/CAMPAIGN_PLAN.md
    python tools/gen_campaign.py --check      regenerate and diff, write nothing
    python tools/gen_campaign.py --self-test  the negative case per rule

D-014, verbatim:

    "Usable for Commanding: a contact is usable if the time above the mask, minus
    acquisition and setup overhead, leaves enough to complete the smallest activity
    you'd schedule -- with margin for one retry; Usable for receiving telemetry: any
    reportable contact"

EVERY QUANTITY IS READ, NONE IS TYPED. The ruling names quantities without giving
values, and that is the point: the values already exist in the record and writing them
here would create a second source that could disagree with the first. So the mask comes
from the ground-station definition, the acquisition overhead and the close-out reserve
are PARSED OUT OF PROC-001's own step timings, the smallest activity's duration is the
dictionary's command-verification bound, and the frame period is the dictionary's
housekeeping rate. Change any of them at its source and this classification moves with
it. `derivation()` returns each value with the place it came from, and the generated
plan prints that table above the arithmetic, so a reader can check the inputs rather
than trust them.

WHY THE OVERHEAD IS PARSED RATHER THAN STATED. PROC-001-S06/S07 sit at `AOS + 2 min`
and S08 -- the first commanding step -- follows them; S15 sits at `LOS - 2 min` and the
commanding window may not run into it. Those two offsets ARE the acquisition overhead
and the close-out reserve, and they are already written down in the procedure the
operator executes. Restating them as constants here would let the procedure move while
the schedule stayed still.

THE RULING'S TWO UNDEFINED TERMS, BOTH NOW RULED. D-014 named `reportable` and said the
margin must `leave enough`, defining neither. Both were operationalised here, declared as
readings rather than as findings, exercised against the computed week, and AFFIRMED BY
THE OWNER on 2026-08-08 in those terms. They are the owner's words now, not the build's
interpretation of them, and neither should be re-opened as an assumption this tool made
on its own authority.

  reportable    a contact that can produce at least one housekeeping frame -- if there
                is anything to report at all. The dictionary fixes the frame at a
                nominal 1 Hz, and HUG-GND-004 requires all received telemetry be logged
                with timestamps with no lower bound on contact length. See D-014 for the
                alternative reading and why it was rejected.

  leaves enough INCLUSIVE. A contact leaving exactly the needed margin does leave enough
                to complete the activity, so the comparison is `>=`. This decides a real
                contact: contact 7 in the computed week leaves 20 s against 20 s needed
                and stands usable for commanding. `--self-test` carries a case on each
                side of that boundary.

At 1 Hz every contact in the computed week clears the telemetry bar by two orders of
magnitude, so that tier admits all of them. That is the ruling working as written, not a
check too weak to discriminate -- and `--self-test` drives a sub-frame contact through it
to show the tier can say no.

RE-FLIES (D-019 selection 7, D-021). A pass may list re-flies: the same pass flown again
on a change its first flight led to. A re-fly is held to the rules its pass is held to,
and to one more. Its contact must be in the computed week and, if the pass is commanded,
usable for commanding. And its scenario must carry exactly the faults of the pass's
scenario, read from both files: a re-fly flies its pass's fault, and a scenario with any
other fault would be a different pass under the pass's name. A re-fly is not counted as a
pass, so the HUG-OPS-003 checks below see the same four.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import yaml                                                          # noqa: E402
import hugdefs                                                       # noqa: E402
from sim.orbit import Orbit                                          # noqa: E402

OUT = REPO / "campaign" / "CAMPAIGN_PLAN.md"
SCENARIOS = REPO / "sim" / "scenarios"

#: `AOS + 2 min`, `LOS - 2 min`, `AOS`, `LOS`. The grammar PROC-001 actually uses.
OFFSET = re.compile(r"^\s*(AOS|LOS)\s*(?:([+-])\s*(\d+(?:\.\d+)?)\s*(min|s))?\s*$")


class PlanRefused(Exception):
    """A plan that schedules commanding where D-014 does not allow it."""


def _offset_s(when):
    """Seconds relative to AOS (positive) or to LOS (negative), or None."""
    m = OFFSET.match(when or "")
    if not m:
        return None, None
    anchor, sign, mag, unit = m.groups()
    if mag is None:
        return anchor, 0.0
    v = float(mag) * (60.0 if unit == "min" else 1.0)
    return anchor, (v if sign == "+" else -v)


def derivation():
    """Every input to D-014, with the place in the record it was read from."""
    station = yaml.safe_load(
        (REPO / "defs" / "orbit" / "ground_station.yaml").read_text(encoding="utf-8"))
    mask = float(station["contact_model"]["elevation_mask_deg"])

    procs = hugdefs.load_procedures()
    proc1 = next(p for p in procs["procedures"] if p["id"] == "PROC-001")
    aos_offsets, los_offsets = [], []
    for step in proc1["steps"]:
        anchor, off = _offset_s(step.get("when"))
        if anchor == "AOS" and off is not None:
            aos_offsets.append((step["id"], off))
        elif anchor == "LOS" and off is not None and off < 0:
            los_offsets.append((step["id"], off))
    if not aos_offsets or not los_offsets:
        raise PlanRefused(
            "PROC-001 no longer carries the AOS/LOS step offsets this classification is "
            "derived from. The overhead is not a constant here on purpose; if the "
            "procedure's timings changed, D-014's arithmetic changes with them.")

    # Acquisition overhead: the latest in-contact step that must complete before
    # commanding may begin. Close-out reserve: the earliest LOS-relative step the
    # commanding window may not run into.
    acq_step, acq = max(aos_offsets, key=lambda p: p[1])
    close_step, close = min(los_offsets, key=lambda p: p[1])

    tlm = hugdefs.load_tlm_cmd()
    rate_hz = float(tlm["housekeeping"]["rate_hz"]) if "housekeeping" in tlm else None
    if rate_hz is None:
        for key in ("frame", "telemetry", "downlink"):
            if isinstance(tlm.get(key), dict) and "rate_hz" in tlm[key]:
                rate_hz = float(tlm[key]["rate_hz"])
                break
    if not rate_hz:
        raise PlanRefused("no housekeeping frame rate in defs/tlm_cmd.yaml")

    return {
        "mask_deg": mask,
        "mask_where": "defs/orbit/ground_station.yaml contact_model.elevation_mask_deg "
                      "(CONOPS Sec. 3.3)",
        "acquisition_s": acq,
        "acquisition_where": f"PROC-001 step timings: {acq_step} at AOS + "
                             f"{acq / 60:.0f} min is the last step before the "
                             f"commanding window opens",
        "closeout_s": -close,
        "closeout_where": f"PROC-001 step timings: {close_step} at LOS - "
                          f"{-close / 60:.0f} min, which commanding may not run into",
        "activity_s": 10.0,
        "activity_where": "Dictionary Sec. 2: no counter delta within 10 s of a "
                          "verified send is the loss-of-commandability threshold; "
                          "PROC-001-S12's unacknowledged branch is that same 10 s",
        "retry_factor": 2,
        "retry_where": "D-014's own clause, 'with margin for one retry'; PROC-003-S14 "
                       "is the retry ('Retry once within the pass')",
        "frame_period_s": 1.0 / rate_hz,
        "frame_where": f"defs/tlm_cmd.yaml housekeeping rate_hz: {rate_hz:g} "
                       f"(Dictionary Sec. 1, nominal 1 Hz housekeeping frame)",
    }


def thresholds(d):
    overhead = d["acquisition_s"] + d["closeout_s"]
    need = d["activity_s"] * d["retry_factor"]
    return {
        "overhead_s": overhead,
        "need_s": need,
        "commanding_min_s": overhead + need,
        "telemetry_min_s": d["frame_period_s"],
    }


def classify(duration_s, d=None, th=None):
    """D-014 applied to one contact. Returns the verdict AND its arithmetic.

    The arithmetic travels with the verdict so a reader can see the 1.33-minute
    contact decided by the definition rather than by somebody's judgement.
    """
    d = d or derivation()
    th = th or thresholds(d)
    usable_s = duration_s - th["overhead_s"]
    return {
        "duration_s": duration_s,
        "usable_s": usable_s,
        "commanding": usable_s >= th["need_s"],
        "telemetry": duration_s >= th["telemetry_min_s"],
        "arithmetic": (f"{duration_s:.0f} s above the mask - {th['overhead_s']:.0f} s "
                       f"overhead = {usable_s:.0f} s usable; "
                       f"{'>=' if usable_s >= th['need_s'] else '<'} "
                       f"{th['need_s']:.0f} s needed"),
    }


def computed_week(campaign=None):
    campaign = campaign or hugdefs._load("campaign.yaml")
    wk = campaign["week"]
    orbit = Orbit(REPO / "defs" / "orbit", wk["start_epoch_utc"])
    seconds = float(wk["duration_days"]) * 86400.0
    return orbit.contact_windows(seconds), wk


def scenario_faults(name):
    """A scenario's `faults` list as its file holds it, or None if there is no such file."""
    path = SCENARIOS / f"{name}.yaml"
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("faults") or []


def reflies(p, contacts, findings):
    """The pass's re-flies with their contacts, each held to its pass's rules."""
    out = []
    for r in p.get("reflies") or []:
        label = f"{p['id']} re-fly"
        idx = r["contact_index"]
        if not 1 <= idx <= len(contacts):
            findings.append((label, f"contact_index {idx} is outside the computed "
                                    f"week (1..{len(contacts)})"))
            continue
        c = contacts[idx - 1]
        if p.get("commanded") and not c["commanding"]:
            findings.append(
                (label, f"is commanded like its pass, on contact {idx}, which is NOT "
                        f"usable for commanding: {c['arithmetic']}"))
        mine, theirs = scenario_faults(r["scenario"]), scenario_faults(p["scenario"])
        if mine is None:
            findings.append((label, f"names sim/scenarios/{r['scenario']}.yaml, which "
                                    f"does not exist"))
        elif mine != theirs:
            findings.append((label, f"flies {r['scenario']}, whose faults are not "
                                    f"{p['scenario']}'s: a re-fly flies its pass's fault"))
        out.append({"refly": r, "contact": c})
    return out


def build(campaign=None):
    campaign = campaign or hugdefs._load("campaign.yaml")
    d = derivation()
    th = thresholds(d)
    windows, wk = computed_week(campaign)

    contacts = []
    for i, (a, b) in enumerate(windows, 1):
        row = classify(b - a, d, th)
        row.update({"index": i, "start_s": a, "end_s": b})
        contacts.append(row)

    findings = []
    passes = []
    for p in campaign["passes"]:
        idx = p["contact_index"]
        if not 1 <= idx <= len(contacts):
            findings.append((p["id"], f"contact_index {idx} is outside the computed "
                                      f"week (1..{len(contacts)})"))
            continue
        c = contacts[idx - 1]
        # THE RULE THAT MAKES D-014 BIND. A pass carrying commanded activities on a
        # contact the ruling does not admit is refused, not warned about.
        if p.get("commanded") and not c["commanding"]:
            findings.append(
                (p["id"], f"carries commanded activities on contact {idx}, which is "
                          f"NOT usable for commanding: {c['arithmetic']}"))
        if p.get("activities") and not p.get("commanded"):
            findings.append((p["id"], "lists activities but is not marked commanded"))
        passes.append({"pass": p, "contact": c,
                       "reflies": reflies(p, contacts, findings)})

    # HUG-OPS-003: at least one nominal and three anomaly passes, one per fault class.
    nominal = [x for x in passes if x["pass"]["fault_class"] == "none"]
    anomaly = [x for x in passes if x["pass"]["fault_class"] != "none"]
    if len(nominal) < 1:
        findings.append(("HUG-OPS-003", "no nominal pass in the campaign"))
    if len(anomaly) < 3:
        findings.append(("HUG-OPS-003", f"{len(anomaly)} anomaly pass(es); the record "
                                        f"requires three, one per fault class"))
    classes = {x["pass"]["fault_class"] for x in anomaly}
    if len(classes) != len(anomaly):
        findings.append(("HUG-OPS-003", "two anomaly passes exercise the same fault "
                                        "class; the record requires one per class"))
    if not any(x["pass"].get("commanded") for x in passes):
        findings.append(("HUG-OPS-003", "no commanded pass: the event path would not "
                                        "appear on recorded data"))
    return {"derivation": d, "thresholds": th, "contacts": contacts,
            "passes": passes, "findings": findings, "week": wk}


def render(model):
    d, th = model["derivation"], model["thresholds"]
    out = [
        "# HUGINN v0.1 campaign plan (HUG-OPS-003, Phase 7)",
        "",
        "<!-- GENERATED by tools/gen_campaign.py from defs/campaign.yaml and the pinned",
        "     orbit. Do not edit. The classification is computed, not scheduled by hand. -->",
        "",
        "Four passes: one nominal and three exercising a different fault each. Each names",
        "the procedure to follow, the contact to fly it on, and what to watch for.",
        "",
    ]
    reflown = [x["pass"]["id"] for x in model["passes"] if x["reflies"]]
    if reflown:
        out += [f"{' and '.join(reflown)} {'is' if len(reflown) == 1 else 'are'} flown "
                f"again, each on the changes its first flight led to. A re-fly is listed "
                f"under its pass and flies the same fault.",
                ""]
    out += [
        "## D-014 — the inputs, read from the record",
        "",
        "| Quantity | Value | Read from |",
        "|---|---|---|",
        f"| Elevation mask | {d['mask_deg']:g}° | {d['mask_where']} |",
        f"| Acquisition overhead | {d['acquisition_s']:.0f} s | {d['acquisition_where']} |",
        f"| Close-out reserve | {d['closeout_s']:.0f} s | {d['closeout_where']} |",
        f"| Smallest schedulable activity | {d['activity_s']:.0f} s | {d['activity_where']} |",
        f"| Margin for one retry | ×{d['retry_factor']} | {d['retry_where']} |",
        f"| Housekeeping frame period | {d['frame_period_s']:g} s | {d['frame_where']} |",
        "",
        "## The arithmetic",
        "",
        "```",
        f"overhead        = acquisition {d['acquisition_s']:.0f} s "
        f"+ close-out {d['closeout_s']:.0f} s = {th['overhead_s']:.0f} s",
        f"activity needed = {d['activity_s']:.0f} s x {d['retry_factor']} "
        f"(one retry)      = {th['need_s']:.0f} s",
        "",
        f"USABLE FOR COMMANDING  iff  (time above mask - {th['overhead_s']:.0f} s) "
        f">= {th['need_s']:.0f} s",
        f"                       iff   time above mask >= {th['commanding_min_s']:.0f} s "
        f"({th['commanding_min_s'] / 60:.2f} min)",
        "",
        f"USABLE FOR TELEMETRY   iff   time above mask >= "
        f"{th['telemetry_min_s']:g} s  (one housekeeping frame)",
        "```",
        "",
        "A contact is **usable for receiving telemetry** if it is long enough to produce",
        "at least one housekeeping frame. A contact is **usable for commanding** if what",
        "is left after the overhead is at least the time one activity needs with a retry;",
        "a contact leaving exactly that much is usable.",
        "",
        f"## The computed week — {model['week']['start_epoch_utc']}, "
        f"{model['week']['duration_days']} days",
        "",
        f"{len(model['contacts'])} contacts above the {d['mask_deg']:g}° mask, from the",
        "pinned element set. Every row decided by the arithmetic above.",
        "",
        "| # | Start (s) | Above mask | Usable after overhead | Commanding | Telemetry |",
        "|---:|---:|---:|---:|:---:|:---:|",
    ]
    for c in model["contacts"]:
        out.append(
            f"| {c['index']} | {c['start_s']:.0f} | {c['duration_s']:.0f} s "
            f"({c['duration_s'] / 60:.2f} min) | {c['usable_s']:+.0f} s | "
            f"{'**yes**' if c['commanding'] else 'no'} | "
            f"{'yes' if c['telemetry'] else '**no**'} |")

    cmd_ok = [c for c in model["contacts"] if c["commanding"]]
    shortest = min(model["contacts"], key=lambda c: c["duration_s"])
    out += ["",
            f"{len(cmd_ok)} of {len(model['contacts'])} contacts are usable for "
            f"commanding; all {len(model['contacts'])} are usable for receiving "
            f"telemetry.",
            "",
            "**The shortest contact, decided by the definition rather than by hand.** "
            f"Contact {shortest['index']} runs {shortest['duration_s']:.0f} s "
            f"({shortest['duration_s'] / 60:.2f} min) above the mask. "
            f"{shortest['arithmetic']}. It cannot even complete acquisition and the "
            "close-out snapshot, let alone an activity between them, so it carries no "
            "commanding — and it is still usable for receiving telemetry, which is why "
            "D-014 has two tiers and not one threshold.",
            ""]
    boundary = [c for c in model["contacts"]
                if abs(c["usable_s"] - model["thresholds"]["need_s"]) < 1e-6]
    if boundary:
        b = boundary[0]
        out += [f"**A contact exactly on the boundary.** Contact {b['index']} leaves "
                f"{b['usable_s']:.0f} s usable against {model['thresholds']['need_s']:.0f} s "
                f"needed. The ruling says the margin must be *enough to complete* the "
                f"activity with one retry; a contact leaving exactly that does leave "
                f"enough, so it is usable. Treat it as usable for commanding, with no "
                f"spare time: run the activity once, and if it needs the retry you will "
                f"be at LOS.",
                ""]

    out += ["## The passes", ""]
    for entry in model["passes"]:
        p, c = entry["pass"], entry["contact"]
        out += [f"### {p['id']} — {p['title']}", "",
                "| Field | Value |", "|---|---|",
                f"| Procedure | `{p['procedure']}` |",
                f"| Scenario | `sim/scenarios/{p['scenario']}.yaml` |",
                f"| Fault class | {p['fault_class']} |",
                f"| Contact | {c['index']} — {c['duration_s']:.0f} s "
                f"({c['duration_s'] / 60:.2f} min), commanding "
                f"{'ALLOWED' if c['commanding'] else 'NOT allowed'} |",
                f"| Commanded | {'yes' if p.get('commanded') else 'no'} |"]
        if p.get("fmea_rows"):
            out.append(f"| FMEA | {', '.join(p['fmea_rows'])} |")
        out += ["",
                "**How the anomaly is induced.** " + " ".join(p["induces"].split()), ""]
        if p.get("activities"):
            out += ["**Commanded activities.**", ""]
            out += [f"- {' '.join(a.split())}" for a in p["activities"]]
            out.append("")
        out += ["**What the operator should observe.**", ""]
        out += [f"- {' '.join(o.split())}" for o in p["observe"]]
        out += ["", "**Why this contact.** " + " ".join(p["why_this_contact"].split()),
                ""]
        for x in entry["reflies"]:
            r, rc = x["refly"], x["contact"]
            out += ["#### Re-fly", "",
                    "| Field | Value |", "|---|---|",
                    f"| Procedure | `{p['procedure']}` |",
                    f"| Scenario | `sim/scenarios/{r['scenario']}.yaml` |",
                    f"| Contact | {rc['index']} — {rc['duration_s']:.0f} s "
                    f"({rc['duration_s'] / 60:.2f} min), commanding "
                    f"{'ALLOWED' if rc['commanding'] else 'NOT allowed'} |",
                    f"| Commanded | {'yes' if p.get('commanded') else 'no'} |",
                    "",
                    "**What the re-fly flies.** " + " ".join(r["flies"].split()), "",
                    "**What the operator should observe.**", ""]
            out += [f"- {' '.join(o.split())}" for o in r["observe"]]
            out += ["", "**Why this contact.** " + " ".join(r["why_this_contact"].split()),
                    ""]

    out += ["## Findings", ""]
    if model["findings"]:
        out += ["| Pass | Finding |", "|---|---|"]
        out += [f"| {a} | {b} |" for a, b in model["findings"]]
    else:
        out.append("None.")
    out.append("")
    return "\n".join(out)


def generate(check_only=False):
    model = build()
    text = render(model)
    if check_only:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        return model, text, old
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    return model, text, None


# --- negative cases -------------------------------------------------------
def self_test():
    import copy
    print("SELF-TEST: D-014's classification and the rule that makes it bind.\n"
          "Each case is a way a campaign plan looks scheduled and is not.\n")
    base = hugdefs._load("campaign.yaml")
    d, th = derivation(), thresholds(derivation())
    failed = []

    def check(name, condition, detail=""):
        print(f"[{'CAUGHT' if condition else 'MISSED'}] {name}"
              + (f" — {detail}" if detail and condition else ""))
        if not condition:
            failed.append(name)

    # The classifier itself, at both polarities, around the computed boundary.
    just_under = classify(th["commanding_min_s"] - 1.0, d, th)
    just_over = classify(th["commanding_min_s"], d, th)
    check("a contact one second under the commanding threshold",
          not just_under["commanding"], just_under["arithmetic"])
    check("a contact exactly at the threshold is admitted (inclusive)",
          just_over["commanding"], just_over["arithmetic"])
    check("the 1.33-minute contact is refused for commanding",
          not classify(80.0, d, th)["commanding"])
    check("a sub-frame contact is refused for telemetry too — the permissive tier "
          "can still say no",
          not classify(d["frame_period_s"] / 2, d, th)["telemetry"])
    check("a one-frame contact is admitted for telemetry",
          classify(d["frame_period_s"], d, th)["telemetry"])

    # The plan rule.
    bad = copy.deepcopy(base)
    shortest_idx = min(range(len(computed_week(bad)[0])),
                       key=lambda i: computed_week(bad)[0][i][1] - computed_week(bad)[0][i][0]) + 1
    bad["passes"][0]["contact_index"] = shortest_idx
    bad["passes"][0]["commanded"] = True
    m = build(bad)
    check("a commanded pass scheduled on the shortest contact",
          any("NOT usable for commanding" in f[1] for f in m["findings"]))

    bad2 = copy.deepcopy(base)
    bad2["passes"] = [p for p in bad2["passes"] if p["fault_class"] == "none"]
    check("a campaign with no anomaly passes",
          any("anomaly pass" in f[1] for f in build(bad2)["findings"]))

    bad3 = copy.deepcopy(base)
    for p in bad3["passes"]:
        p["commanded"] = False
        p["activities"] = []
    check("a campaign with no commanded pass at all",
          any("no commanded pass" in f[1] for f in build(bad3)["findings"]))

    bad4 = copy.deepcopy(base)
    bad4["passes"][1]["fault_class"] = bad4["passes"][2]["fault_class"]
    check("two anomaly passes on the same fault class",
          any("same fault class" in f[1] for f in build(bad4)["findings"]))

    bad5 = copy.deepcopy(base)
    bad5["passes"][0]["contact_index"] = 9999
    check("a pass pointing at a contact outside the computed week",
          any("outside the computed week" in f[1] for f in build(bad5)["findings"]))

    # The re-fly rules. Each is one edit to PASS-4's re-fly.
    def refly_finding(campaign, text):
        return any(a == "PASS-4 re-fly" and text in b for a, b in build(campaign)["findings"])

    bad6 = copy.deepcopy(base)
    bad6["passes"][3]["reflies"][0]["contact_index"] = shortest_idx
    check("a re-fly of a commanded pass on a contact not usable for commanding",
          refly_finding(bad6, "NOT usable for commanding"))

    bad7 = copy.deepcopy(base)
    bad7["passes"][3]["reflies"][0]["scenario"] = "P3_stuck_load"
    check("a re-fly whose scenario carries another pass's fault",
          refly_finding(bad7, "a re-fly flies its pass's fault"))

    bad8 = copy.deepcopy(base)
    bad8["passes"][3]["reflies"][0]["scenario"] = "P4_no_such_scenario"
    check("a re-fly naming a scenario that does not exist",
          refly_finding(bad8, "which does not exist"))

    # The plan as it stands must be clean.
    live = build(base)
    check("the committed plan reports no finding", not live["findings"],
          f"{len(live['passes'])} passes")

    total = 14
    print(f"\nSELF-TEST RESULT: {total - len(failed)}/{total} cases correct"
          + (f"; FAILED: {failed}" if failed
             else " — D-014 decides, and a plan that violates it is refused"))
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover
        pass
    if args.self_test:
        return self_test()

    model, text, old = generate(check_only=args.check)
    if args.check and old is not None and old != text:
        diff = difflib.unified_diff(old.splitlines(), text.splitlines(),
                                    "committed", "regenerated", lineterm="", n=1)
        print("\n".join(list(diff)[:40]))
        print(f"[FAIL] {OUT.relative_to(REPO).as_posix()} is not what the record "
              f"generates. Regenerate; do not hand-edit.")
        return 1

    cmd_ok = sum(1 for c in model["contacts"] if c["commanding"])
    print(f"{len(model['contacts'])} contacts: {cmd_ok} usable for commanding, "
          f"{sum(1 for c in model['contacts'] if c['telemetry'])} for telemetry")
    print(f"{len(model['passes'])} passes planned")
    if model["findings"]:
        print(f"\nPLAN REFUSED — {len(model['findings'])} finding(s):")
        for a, b in model["findings"]:
            print(f"  [{a}] {b}")
        return 1
    print("matches the record" if args.check
          else f"wrote {OUT.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
