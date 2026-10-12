#!/usr/bin/env python3
"""Generate docs/requirements.md from defs/requirements.yaml.

Obligation B2. The requirements document's own header states the rule: the markdown
is the drafting surface only, and becomes a generated view at build. It is now that
view — editing it directly is prohibited; regenerate instead.

Usage:
    python tools/gen_requirements.py            regenerate the document
    python tools/gen_requirements.py --check    exit 1 if the document on disk differs
"""
import sys

from hugdefs import console, docs_dir, emit, load_requirements, md_table


def build(defs):
    doc = defs["document"]
    out = []
    w = out.append

    w("# " + doc["system_title"])
    w(f"## {doc['doc_title']} v{defs['requirements_version']}")
    w("")
    w("**Status:** " + doc["status"])
    w("")
    w("**Verification methods:** " + doc["verification_methods"])
    w("")
    w("**Traceability rule:** " + doc["traceability_rule"])
    w("")
    w("---")
    w("")

    # Groups and rows render in source order, never sorted: HUG-UI-007 precedes
    # HUG-UI-006 in the record, and sorting by identifier would reorder the record.
    for group in defs["groups"]:
        w(f"## {group['id']}: {group['name']}")
        w("")
        rows = [[r["id"], r["text"], ", ".join(r["verification"]), r["trace"]]
                for r in group["requirements"]]
        out.extend(md_table(["ID", "Requirement", "Ver.", "Notes / trace"], rows))
        w("")

    w("---")
    w("")
    w(f"## Disposition ledger ({doc['ledger_heading']})")
    w("")
    for i, item in enumerate(defs["disposition_ledger"], 1):
        w(f"{i}. {item}")

    return out


def main(argv):
    console()
    check = "--check" in argv
    target = docs_dir() / "requirements.md"
    matched = emit(target, build(load_requirements()), check_only=check)
    rel = "docs/requirements.md"
    if check:
        print(f"[{'PASS' if matched else 'FAIL'}] {rel} matches defs/requirements.yaml"
              + ("" if matched else " — the document has drifted from its source;"
                                    " regenerate it (hand edits are prohibited)"))
        return 0 if matched else 1
    print(f"generated {rel} from defs/requirements.yaml"
          + (" (unchanged)" if matched else " (updated)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
