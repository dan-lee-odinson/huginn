#!/usr/bin/env python3
"""Generate docs/fmea.md from defs/fmea.yaml.

Authorized by owner ruling D-001 (DECISIONS.md, 2026-07-29) and by FMEA Sec. 9, which
already committed the worksheet rows to structured form before build so FM identifiers
could be referenced by checkers and scenario files.

The Risk column is DERIVED here, not stored: every Risk cell in the document — each
worksheet row, and each risk spelling in the Sec. 6.1, 6.2 and 6.3 tables — is looked up
in the Sec. 3 criticality matrix from that row's severity and likelihood. A row's
rating and its risk class cannot disagree, because the risk class is not a second
fact. That is the D0-6 discharge for this document: the contradiction the old
string-comparison check hunted for is now unrepresentable.

Usage:
    python tools/gen_fmea.py            regenerate the document
    python tools/gen_fmea.py --check    exit 1 if the document on disk differs
"""
import sys

from hugdefs import console, docs_dir, emit, load_fmea, md_table


def risk_of(defs, row):
    """Risk class for a worksheet row, from the Sec. 3 criticality matrix."""
    return defs["criticality_matrix"][row["severity"]][row["likelihood"]]


def risk_spelling(defs, row):
    """The Sec. 6 spelling: risk class with the rating that produced it."""
    return f"{risk_of(defs, row)} ({row['severity']}/{row['likelihood']})"


def worksheet_rows(defs):
    """Every worksheet row in document order, keyed by FM identifier."""
    return {r["id"]: r
            for block in defs["worksheets"] if block.get("rows")
            for r in block["rows"]}


def build(defs):
    doc = defs["document"]
    out = []
    w = out.append

    w("# " + doc["system_title"])
    w(f"## {doc['doc_title']}, v{defs['fmea_version']}")
    w("")
    out.extend(md_table(["Field", "Value"],
                        [[h["field"], h["value"]] for h in doc["header_rows"]]))
    w("")
    w("---")
    w("")

    # ---- Sec. 1
    w("## 1. Purpose and scope")
    w("")
    w(defs["purpose"]["intro"])
    w("")
    for i, item in enumerate(defs["purpose"]["items"], 1):
        w(f"{i}. {item}")
    w("")
    w(defs["purpose"]["in_scenario"])
    w("")
    w(defs["purpose"]["analysis_level"])
    w("")

    # ---- Sec. 2
    w("## 2. Ground rules and assumptions")
    w("")
    out.extend(md_table(["ID", "Rule"],
                        [[g["id"], g["rule"]] for g in defs["ground_rules"]]))
    w("")

    # ---- Sec. 3
    w("## 3. Severity and likelihood definitions")
    w("")
    w(defs["severity_lead"])
    w("")
    out.extend(md_table(["Cat.", "Name", "Definition"],
                        [[s["cat"], s["name"], s["definition"]]
                         for s in defs["severity_definitions"]]))
    w("")
    w(defs["likelihood_lead"])
    w("")
    out.extend(md_table(["Level", "Name", "Definition"],
                        [[s["level"], s["name"], s["definition"]]
                         for s in defs["likelihood_definitions"]]))
    w("")
    w(defs["criticality_matrix_lead"])
    w("")
    levels = defs["criticality_matrix_levels"]
    out.extend(md_table([defs["criticality_matrix_corner"]] + levels,
                        [[s["cat"]] + [defs["criticality_matrix"][s["cat"]][l]
                                       for l in levels]
                         for s in defs["severity_definitions"]]))
    w("")
    w(defs["risk_class_note"])
    w("")
    w(defs["disposition_vocabulary"])
    w("")

    # ---- Sec. 4-5 worksheets
    cols = defs["worksheet_columns"]
    for block in defs["worksheets"]:
        w("#" * block["level"] + " " + block["heading"])
        w("")
        if block.get("preamble"):
            w(block["preamble"])
            w("")
        if block.get("rows"):
            out.extend(md_table(cols, [
                [r["id"], r["function"], r["failure_mode"], r["end_effect"],
                 r["severity"], r["likelihood"], risk_of(defs, r),
                 r["detection"], r["provisions"], r["disposition"]]
                for r in block["rows"]]))
            w("")
        if block.get("footnote"):
            w(block["footnote"])
            w("")

    # ---- Sec. 6
    fs = defs["fault_set"]
    by_id = worksheet_rows(defs)
    w("## 6. Fault-set justification")
    w("")
    w(fs["intro"])
    w("")
    w(fs["step_1"])
    w("")
    w(fs["step_2"])
    w("")
    for c in fs["criteria"]:
        w(f"- **({c['letter']}) {c['name']}** {c['text']}")
    w("")
    w(fs["step_3"])
    w("")
    w("### " + doc["section_6_1_heading"])
    w("")
    out.extend(md_table(fs["selected_columns"], [
        [s["fault"], s["row"], risk_spelling(defs, by_id[s["row"]]),
         s["campaign_pass"], s["procedure"]] for s in fs["selected"]]))
    w("")
    w(fs["selected_note"])
    w("")
    w("### " + doc["section_6_2_heading"])
    w("")
    out.extend(md_table(fs["exclusion_columns"], [
        [e["row"], risk_spelling(defs, by_id[e["row"]]), e["criterion"], e["basis"]]
        for e in fs["exclusions"]]))
    w("")
    w(fs["assurance_note"])
    w("")
    w(fs["rollup"])
    w("")
    # Sec. 6.3 (D-020): R2 rows added after the HUG-G001 selection. Rendered after the
    # roll-up, so the Sec. 6.1 and 6.2 tables render as they did before; the Sec. 6.2
    # heading's wording comes from the source and now names the HUG-G001 rows.
    w("### " + doc["section_6_3_heading"])
    w("")
    w(fs["post_selection_intro"])
    w("")
    out.extend(md_table(fs["post_selection_columns"], [
        [s["row"], risk_spelling(defs, by_id[s["row"]]), s["added"], s["status"]]
        for s in fs["post_selection"]]))
    w("")

    # ---- Sec. 7
    w("## 7. Findings and recommendations")
    w("")
    w(defs["recommendations_intro"])
    w("")
    for r in defs["recommendations"]:
        w(r["finding"])
        w("")
        w(r["resolution"])
        w("")

    # ---- Sec. 8-10
    w(f"## 8. Disposition ledger ({doc['section_8_heading']})")
    w("")
    for i, item in enumerate(defs["disposition_ledger"], 1):
        w(f"{i}. {item}")
    w("")
    w("## 9. Traceability")
    w("")
    w(defs["traceability"])
    w("")
    w("## 10. Changelog")
    w("")
    # Record order, never sorted: v0.11 sits second, between v0.14 and v0.13.
    for entry in defs["changelog"]:
        w(f"- {entry}")

    return out


def main(argv):
    console()
    check = "--check" in argv
    target = docs_dir() / "fmea.md"
    matched = emit(target, build(load_fmea()), check_only=check)
    rel = "docs/fmea.md"
    if check:
        print(f"[{'PASS' if matched else 'FAIL'}] {rel} matches defs/fmea.yaml"
              + ("" if matched else " — the document has drifted from its source;"
                                    " regenerate it (hand edits are prohibited)"))
        return 0 if matched else 1
    print(f"generated {rel} from defs/fmea.yaml"
          + (" (unchanged)" if matched else " (updated)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
