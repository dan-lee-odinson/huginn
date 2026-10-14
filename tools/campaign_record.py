#!/usr/bin/env python3
"""The v0.1 campaign as flown, checked against HUG-OPS-003 and HUG-OPS-004 (D-019).

    python tools/campaign_record.py      print what each filed record is, and the verdict

HUG-OPS-003: "The v0.1 campaign shall comprise at least one nominal pass and three anomaly
passes (one per fault class), executed human-in-the-loop on the operator's scheduled
availability." HUG-OPS-004: "Each anomaly pass shall additionally produce an anomaly report
with cause, response evaluation, and any resulting change requests to procedures or
requirements." D-019 selection 4 asks for executed cases that tie the flown passes and the
anomaly reports to both. This is what those cases execute.

WHICH PASS A RECORD IS, DERIVED RATHER THAN DECLARED. No pass record names its scenario,
and a table here mapping records to passes would be a second source sitting beside the
records. The telemetry answers the question instead. The simulator is deterministic
(HUG-SYS-003), so a flown record is the run of exactly one scenario. Replayed with the
commands in the record's own ground command log, each sent on the tick after the last
frame the ground had received when it went out, that scenario reproduces every telemetry
point of every frame the ground received. Measured on the campaign as filed: every counted
record reproduces frame for frame, and every other campaign scenario diverges at the
record's first frame, because each scenario starts from its own state of charge.

HUMAN IN THE LOOP. A scenario's own scripted commands never reach the ground's command
log; what is in that log was sent from the console. Where an operator command had a
visible effect, the scenario alone stops reproducing the record at that frame and the
scenario plus the log reproduces all of it, so the operator's commands are part of the
evidence. Each campaign pass must show at least one. (In PASS-4 the operator's
CMD_SYS_RESET has no visible effect: the scenario's own reset had already cleared the halt,
and the post-reset epoch equals the counters before it. That is OF-028.)

RE-FLIES. A pass may list re-flies in defs/campaign.yaml (D-019 selection 7, D-021). A
re-fly flies its pass's fault, and tools/gen_campaign.py refuses one whose scenario does
not. Its scenario is one more candidate a record is replayed against, and a record it
reproduces counts toward the re-fly's pass. The PASS-3 re-fly flies the pass's own
scenario; the PASS-4 re-fly flies a copy in which only the operator's reset clears the
halt. A scenario claimed by two passes would leave a record's pass undecided, and is
refused.

WHAT THE RECORD CANNOT SHOW. "On the operator's scheduled availability" is a fact about
the operator's calendar. What a record does carry is when it says the pass was executed,
and the ground's receipt times say when its frames arrived. The first must come before the
second and within the same session: an hour, because PASS-2's two records share one
pre-pass verification and its second contact's first frame arrived 28 minutes after it.

WHAT COUNTS. A filed record counts toward the campaign when the pass-report validator
accepts it (HUG-OPS-002) and its telemetry identifies exactly one campaign scenario. The
first PASS-1 attempt, `2026-08-03-P1`, is refused by the validator and kept as filed; the
re-fly `2026-09-13-P1` is the nominal pass. `EXAMPLE-2026-08-08-A` carries no telemetry.
Neither is counted, and neither is an error: a campaign record may hold attempts.
"""
import csv
import re
import struct
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))
import hugdefs                                                       # noqa: E402
import pass_report                                                   # noqa: E402
from sim.scenario import Scenario                                    # noqa: E402
from sim.spacecraft import Spacecraft                                # noqa: E402

#: How long after its stated execution a record's first frame may arrive. See the module
#: docstring: PASS-2's second contact is the longest, at 28 minutes.
SESSION_S = 3600

FAULT_CLASS = re.compile(r"HUG-EPS-004\(([a-z])\)")
REGISTER_KEY = re.compile(r"\bOF-\d{3}\b")


# --------------------------------------------------------------------------- loading

def fault_classes():
    """The fault classes the record defines: HUG-EPS-004's lettered items.

    Read from the requirement so "one per fault class" means the record's own count,
    not a number typed in here.
    """
    reqs = {r["id"]: r for r in hugdefs.requirements_flat(hugdefs.load_requirements())}
    return sorted(set(re.findall(r"\(([a-z])\) ", reqs["HUG-EPS-004"]["text"])))


def load_campaign(repo=REPO):
    return yaml.safe_load((repo / "defs" / "campaign.yaml").read_text(encoding="utf-8"))


def scenario_passes(campaign):
    """{scenario: pass id} for every scenario the campaign flies, its re-flies included."""
    out = {}
    for p in campaign["passes"]:
        for name in [p["scenario"]] + [r["scenario"] for r in p.get("reflies") or []]:
            if out.get(name, p["id"]) != p["id"]:
                raise ValueError(f"{name} is flown by both {out[name]} and {p['id']}: a "
                                 f"record it reproduces would count toward either")
            out[name] = p["id"]
    return out


def _commands(path):
    """A ground command log: (sent_s, mnemonic, args) per command, in log order.

    The export repeats column names when packets of different shapes share a file, so
    an argument is read by name from the non-empty cells after the three fixed columns
    (TIME, TARGET, PACKET). The argument names come from the dictionary of record.
    """
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    head, out = rows[0], []
    argdefs = {c["mnemonic"]: c["args"] for c in hugdefs.load_tlm_cmd()["commands"]}
    for row in rows[1:]:
        mnemonic = row[2]
        cells = [(h, v) for i, (h, v) in enumerate(zip(head, row)) if i > 2 and v != ""]
        args = {}
        for a in argdefs[mnemonic]:
            values = [v for h, v in cells if h == a["name"].upper()]
            args[a["name"]] = float(values[-1]) if a["type"] == "float" else values[-1]
        sent = float(next(v for h, v in cells if h == "PACKET_TIMESECONDS"))
        out.append((sent, mnemonic, args))
    return out


def load_record(directory):
    """One filed pass record, as the files hold it."""
    tlm = directory / "telemetry_hk.csv"
    telemetry = None
    if tlm.is_file():
        with tlm.open(newline="", encoding="utf-8") as fh:
            telemetry = list(csv.DictReader(fh))
    return {
        "id": directory.name,
        "report": yaml.safe_load((directory / "report.yaml").read_text(encoding="utf-8")),
        "telemetry": telemetry,
        "commands": _commands(directory / "commands.csv"),
    }


def load_records(repo=REPO):
    return [load_record(d) for d in sorted((repo / "docs" / "pass_reports").iterdir())
            if (d / "report.yaml").is_file()]


def load_anomaly_reports(repo=REPO):
    """Each anomaly report's header table, headings and numbered findings."""
    out = []
    for path in sorted((repo / "docs" / "anomalies").glob("AR-*.md")):
        text = path.read_text(encoding="utf-8")
        fields = {}
        for line in text.splitlines():
            m = re.match(r"^\| ([^|]+?) \| (.+) \|$", line)
            if m and m.group(1) not in ("Field", "---"):
                fields.setdefault(m.group(1), m.group(2))
            if line.startswith("## "):
                break
        headings = re.findall(r"^## (.+)$", text, re.M)
        findings = []
        section = re.search(r"^## [^\n]*Findings raised by this anomaly\n(.*?)(?=^## |\Z)",
                            text, re.M | re.S)
        if section:
            findings = [f.strip() for f in
                        re.split(r"^(?=\d+\. )", section.group(1), flags=re.M)
                        if re.match(r"\d+\. ", f)]
        out.append({"id": path.name.split("-", 2)[0] + "-" + path.name.split("-", 2)[1],
                    "file": path.name, "fields": fields, "headings": headings,
                    "findings": findings, "has_findings_section": bool(section)})
    return out


def register_keys(repo=REPO):
    text = (repo / "verification" / "OPEN_FINDINGS.md").read_text(encoding="utf-8")
    return set(re.findall(r"^## (OF-\d{3}) ", text, re.M))


# --------------------------------------------------------------------------- replay

def _f32(x):
    return struct.unpack("f", struct.pack("f", float(x)))[0]


def _same(point, simulated, recorded):
    if point["type"] == "float":
        return _f32(simulated) == _f32(recorded)
    if point["type"].startswith("uint"):
        return int(simulated) == int(recorded)
    return str(simulated) == recorded


def replay(scenario_name, record, repo=REPO, with_commands=True):
    """(reproduced, detail): does this scenario reproduce the record's telemetry?

    The record's logged commands are sent on the tick after the last frame the ground
    had received when each went out. Every telemetry point the dictionary defines is
    compared, at the ground's own 32-bit width for floating-point points.
    """
    rows = record["telemetry"]
    if not rows:
        return False, "the record carries no telemetry"
    scenario = Scenario.load(repo / "sim" / "scenarios" / f"{scenario_name}.yaml")
    if with_commands:
        received = [(float(r["RECEIVED_TIMESECONDS"]), int(r["CDH_MET"])) for r in rows]
        for sent, mnemonic, args in record["commands"]:
            before = [met for t, met in received if t <= sent]
            if not before:
                return False, f"{mnemonic} was sent before the first frame arrived"
            scenario.commands.append({"t_s": max(before) + 1, "mnemonic": mnemonic,
                                      "args": dict(args)})
        scenario.commands.sort(key=lambda c: (c["t_s"], c["mnemonic"]))
    tlm = hugdefs.load_tlm_cmd()
    sim = Spacecraft(hugdefs.load_eps(), tlm, scenario)
    last = int(rows[-1]["CDH_MET"])
    if last >= scenario.duration_s:
        return False, f"the record runs to MET {last}, past the scenario's end"
    frames = {f["CDH_MET"]: f for f in sim.run(last + 1)}
    points = [p for p in hugdefs.points(tlm) if p["mnemonic"] in rows[0]]
    for row in rows:
        met = int(row["CDH_MET"])
        frame = frames.get(met)
        if frame is None:
            return False, f"the scenario generates no frame at MET {met}"
        for p in points:
            if not _same(p, frame[p["mnemonic"]], row[p["mnemonic"]]):
                return False, (f"diverges at MET {met}: {p['mnemonic']} simulated "
                               f"{frame[p['mnemonic']]!r}, recorded {row[p['mnemonic']]}")
    return True, f"all {len(rows)} frames reproduced"


def _utc(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()


def classify(records, campaign, repo=REPO):
    """Each record with what the record itself establishes about it."""
    scenarios = list(scenario_passes(campaign))
    out = []
    for rec in records:
        ok, findings = pass_report.validate(rec["report"])
        matches = [s for s in scenarios if replay(s, rec, repo)[0]] if rec["telemetry"] else []
        entry = {"id": rec["id"], "record": rec, "valid": ok,
                 "validator_findings": len(findings), "scenarios": matches}
        entry["counted"] = ok and len(matches) == 1
        entry["scenario"] = matches[0] if entry["counted"] else None
        out.append(entry)
    return out


# --------------------------------------------------------------------------- the checks

def ops003_problems(campaign, classified, classes):
    """HUG-OPS-003, from the campaign definition and the records. [] when it holds."""
    problems = []
    passes = campaign["passes"]
    nominal = [p for p in passes if p["fault_class"] == "none"]
    anomaly = [p for p in passes if p["fault_class"] != "none"]
    if not nominal:
        problems.append("the campaign defines no nominal pass")
    defined = []
    for p in anomaly:
        m = FAULT_CLASS.match(str(p["fault_class"]))
        if not m:
            problems.append(f"{p['id']}'s fault class {p['fault_class']!r} is not one of "
                            f"HUG-EPS-004's")
        else:
            defined.append(m.group(1))
    if sorted(defined) != classes:
        problems.append(f"the anomaly passes cover fault classes {sorted(defined)}; "
                        f"HUG-EPS-004 defines {classes}, one pass each")

    owner = scenario_passes(campaign)
    for p in passes:
        flown = [c for c in classified if c["counted"] and owner.get(c["scenario"]) == p["id"]]
        if not flown:
            problems.append(f"{p['id']} ({p['scenario']}) has no record the validator "
                            f"accepts whose telemetry its scenario, or a re-fly's, "
                            f"reproduces")
            continue
        if not any(c["record"]["commands"] for c in flown):
            problems.append(f"{p['id']}'s records log no command from the console: "
                            f"nothing shows a human in the loop")
        for c in flown:
            rows = c["record"]["telemetry"]
            executed = _utc(c["record"]["report"]["executed_utc"])
            first = float(rows[0]["RECEIVED_TIMESECONDS"])
            if not 0 <= first - executed <= SESSION_S:
                problems.append(f"{c['id']} says it was executed at "
                                f"{c['record']['report']['executed_utc']}, but its first "
                                f"frame arrived {first - executed:+.0f} s from then")
    return problems


def ops004_problems(campaign, classified, reports, register):
    """HUG-OPS-004, from the anomaly reports, the records and the register."""
    problems = []
    owner = scenario_passes(campaign)
    for p in (q for q in campaign["passes"] if q["fault_class"] != "none"):
        source = f"sim/scenarios/{p['scenario']}.yaml"
        mine = [r for r in reports if source in r["fields"].get("Scenario", "")]
        if len(mine) != 1:
            problems.append(f"{p['id']} has {len(mine)} anomaly reports naming {source}; "
                            f"it needs exactly one")
            continue
        ar = mine[0]
        tag = ar["id"]
        # Cause: the fault class and the scenario that injected it.
        code = FAULT_CLASS.match(str(p["fault_class"]))
        if not code or not ar["fields"].get("Fault class", "").startswith(code.group(0)):
            problems.append(f"{tag}'s fault class does not state {p['id']}'s, "
                            f"{p['fault_class'].split(' ')[0]}")
        # The records it reports on are the ones the telemetry says flew this pass,
        # its re-flies included.
        flown = sorted(c["id"] for c in classified
                       if c["counted"] and owner.get(c["scenario"]) == p["id"])
        named = sorted(re.findall(r"`(\d{4}-\d{2}-\d{2}-P\w+)`",
                                  ar["fields"].get("Contact", "")
                                  + ar["fields"].get("Contacts", "")))
        if named != flown:
            problems.append(f"{tag} names contacts {named}; the records that flew "
                            f"{p['id']} are {flown}")
        # Response evaluation.
        for word in ("response", "outcome"):
            if not any(word in h.lower() for h in ar["headings"]):
                problems.append(f"{tag} has no {word} section")
        # Change requests: every finding carried into the register.
        if not ar["has_findings_section"]:
            problems.append(f"{tag} has no 'Findings raised by this anomaly' section")
        for i, finding in enumerate(ar["findings"], 1):
            cited = set(REGISTER_KEY.findall(finding))
            if "not yet in the register" in finding.lower():
                problems.append(f"{tag} finding {i} says it is not yet in the register")
            elif not cited:
                problems.append(f"{tag} finding {i} names no register entry")
            elif cited - register:
                problems.append(f"{tag} finding {i} cites {sorted(cited - register)}, "
                                f"not in the register")
    return problems


def evaluate(repo=REPO):
    campaign = load_campaign(repo)
    classified = classify(load_records(repo), campaign, repo)
    return (campaign, classified,
            ops003_problems(campaign, classified, fault_classes()),
            ops004_problems(campaign, classified, load_anomaly_reports(repo),
                            register_keys(repo)))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover
        pass
    campaign, classified, p3, p4 = evaluate()
    by_scenario = scenario_passes(campaign)
    for c in classified:
        if c["counted"]:
            print(f"[COUNTED] {c['id']}: {by_scenario[c['scenario']]}, reproduced by "
                  f"{c['scenario']} with {len(c['record']['commands'])} logged command(s)")
        else:
            why = ("refused by the validator" if not c["valid"]
                   else "no telemetry" if not c["record"]["telemetry"]
                   else f"telemetry matches {c['scenarios'] or 'no campaign scenario'}")
            print(f"[NOT COUNTED] {c['id']}: {why}")
    for label, problems in (("HUG-OPS-003", p3), ("HUG-OPS-004", p4)):
        print(f"[{'PASS' if not problems else 'FAIL'}] {label}"
              + "".join(f"\n  - {m}" for m in problems))
    return 1 if (p3 or p4) else 0


if __name__ == "__main__":
    sys.exit(main())
