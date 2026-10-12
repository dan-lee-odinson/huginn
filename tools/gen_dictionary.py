#!/usr/bin/env python3
"""Generate docs/tlm_cmd_dictionary.md from defs/tlm_cmd.yaml.

The dictionary document is a GENERATED VIEW. Its own header states the rule: once
the definitions live in `defs/tlm_cmd.yaml`, editing the markdown directly is
prohibited — regenerate it instead (single-source discipline, D0-6 companion;
obligations B1/B2).

Usage:
    python tools/gen_dictionary.py            regenerate the document
    python tools/gen_dictionary.py --check    exit 1 if the document on disk differs
                                              from what the defs generate (CI / the
                                              round-trip check)
"""
import sys

from hugdefs import (console, docs_dir, emit, load_tlm_cmd, md_table, render_args,
                     render_limits, render_type)


def build(defs):
    doc = defs["document"]
    out = []
    w = out.append

    w("# " + doc["system_title"])
    w(f"## {doc['doc_title']}, v{defs['dictionary_version']}")
    w("")
    w("**Status:** " + doc["status"])
    w("")
    w("**Limit provenance rule:** " + doc["limit_provenance_rule"])
    w("")
    w("---")
    w("")

    # ---- Section 1: telemetry, one table per group
    w("## " + doc["section_1_heading"])
    w("")
    for group in defs["telemetry_groups"]:
        w("### " + group["name"])
        w("")
        rows = [[p["mnemonic"], p["description"], render_type(p), p["units"],
                 render_limits(p["limits"])] for p in group["points"]]
        out.extend(md_table(["Mnemonic", "Description", "Type", "Units",
                             group["limits_header"]], rows))
        w("")

    w("Notes:")
    w("")
    for i, note in enumerate(defs["telemetry_notes"], 1):
        w(f"{i}. {note}")
    w("")

    # ---- Section 2: commands
    w("## " + doc["section_2_heading"])
    w("")
    rows = [[c["mnemonic"], render_args(c), c["rules"], c["effect"]]
            for c in defs["commands"]]
    out.extend(md_table(["Mnemonic", "Arguments", "Validation / inhibit rules",
                         "Nominal effect"], rows))
    w("")
    w(defs["command_accounting"])
    w("")
    w(defs["mode_authority_rule"])
    w("")

    # ---- Section 3: packet structure
    w("## " + doc["section_3_heading"])
    w("")
    w(defs["frame"]["packet_structure"])
    w("")

    # ---- Section 4: owner disposition ledger
    w(f"## 4. Disposition ledger ({doc['section_4_heading']})")
    w("")
    for i, item in enumerate(defs["disposition_ledger"], 1):
        w(f"{i}. {item}")

    return out


def main(argv):
    console()
    check = "--check" in argv
    target = docs_dir() / "tlm_cmd_dictionary.md"
    matched = emit(target, build(load_tlm_cmd()), check_only=check)
    rel = "docs/tlm_cmd_dictionary.md"
    if check:
        print(f"[{'PASS' if matched else 'FAIL'}] {rel} matches defs/tlm_cmd.yaml"
              + ("" if matched else " — the document has drifted from its source;"
                                    " regenerate it (hand edits are prohibited)"))
        return 0 if matched else 1
    print(f"generated {rel} from defs/tlm_cmd.yaml"
          + (" (unchanged)" if matched else " (updated)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
