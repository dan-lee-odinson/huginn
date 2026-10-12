#!/usr/bin/env python3
"""Generate the VÉ viewer's limit table from the dictionary (HUG-UI-005).

    python tools/gen_ve_viewer.py            write ve/viewer/limits.js
    python tools/gen_ve_viewer.py --check    fail if it is stale

HUG-UI-005, verbatim: *"Limit values and alarm colorings displayed by the viewer shall
derive from `defs/tlm_cmd.yaml` at build time; the viewer shall not define limits
independently."*

So the viewer has no limits of its own and no way to acquire any: this file is the only
producer of `ve/viewer/limits.js`, the renderer reads that table and never a literal,
and a threshold typed into the renderer would be a second source of truth for a number an
operator makes decisions against. The dictionary is the record; a display disagreeing with
it is worse than a display with no bands at all, because it is confidently wrong.

ABSENT LIMIT SIDES STAY ABSENT (owner ruling D-001). `EPS_BATT_SOC` has no high limits and
`EPS_LOAD_I` has no low ones. In the OpenC3 configuration those sides are written as
sentinels with a caveat line above them, because the format demands a number; a DISPLAY has
no such excuse and no place to put the caveat where an operator would read it with the
number. So an absent side is emitted as `null` and the renderer draws no band there. G12
scans this file and fails if a sentinel ever appears in it as a threshold.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_openc3_config                                          # noqa: E402
import hugdefs                                                    # noqa: E402
from hugdefs import points, repo                                  # noqa: E402

OUT = "ve/viewer/limits.js"


def limit_table(defs):
    """{mnemonic: {...}} for every point the viewer can display.

    Carries the thresholds, the units and the decimal places the dictionary states, so
    the renderer formats a value the way the dictionary says it reads and does not
    invent a precision the instrument does not have.
    """
    table = {}
    for point in points(defs):
        limits = point.get("limits") or {}
        kind = limits.get("kind", "none")
        entry = {
            "units": point.get("units"),
            "kind": kind,
            "decimals": limits.get("decimals"),
        }
        if kind == "thresholds":
            # None stays None. An absent side is absent, not a large number wearing a
            # caveat (D-001); the renderer draws no band where there is no limit.
            for side in ("rl", "yl", "yh", "rh"):
                entry[side] = limits.get(side)
        elif kind == "state":
            entry["annunciates"] = list(limits.get("annunciates", []))
        elif kind == "range":
            entry["min"], entry["max"] = limits.get("min"), limits.get("max")
        elif kind == "staleness":
            entry["yellow_s"], entry["red_s"] = (limits.get("yellow_s"),
                                                 limits.get("red_s"))
        elif kind == "delta":
            entry["severity"] = limits.get("severity")
        if point["type"] == "enum":
            entry["values"] = list(point["enum_values"])
        table[point["mnemonic"].lower()] = entry
    return table


def build(defs, version, digest):
    table = limit_table(defs)
    body = json.dumps(table, indent=2, sort_keys=True, ensure_ascii=True,
                      allow_nan=False)
    return [
        "// VÉ viewer limit table.",
        "//",
        "// GENERATED FILE - DO NOT EDIT. Source: defs/tlm_cmd.yaml",
        f"// Dictionary version: {version}",
        f"// Source sha256: {digest}",
        "//",
        "// HUG-UI-005: limit values and alarm colorings derive from the dictionary at",
        "// build time; the viewer defines no limits of its own. A threshold typed into",
        "// the renderer would be a second source of truth for a number an operator makes",
        "// decisions against.",
        "//",
        "// A null side is an ABSENT limit (ruling D-001), and the renderer draws no band",
        "// there. It is not a missing value to be filled in with something convenient.",
        "",
        "// Assigned to `window` deliberately. A top-level `const` in a classic script",
        "// lives in script scope and never becomes a window property, so the renderer",
        "// read `window.VE_LIMITS` as undefined and threw on the first threshold",
        "// lookup -- the orbit drew, the trends did not, and every readout stayed at",
        "// `--`. Nothing in the Python checks could see it; only running the page did.",
        f"window.VE_LIMITS = {body};",
        "",
    ]


def generated_files(defs, version, digest):
    """Every file this generator emits, as {path: lines}."""
    return {repo() / OUT: build(defs, version, digest)}


def main(argv):
    gen_openc3_config.console()
    check = "--check" in argv
    defs = hugdefs.load_tlm_cmd()
    version, digest = gen_openc3_config.source_digest()

    stale = []
    for path, lines in generated_files(defs, version, digest).items():
        rel = path.relative_to(repo()).as_posix()
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            stale.append(rel)
            continue
        if not gen_openc3_config.emit(path, lines, check_only=check):
            stale.append(rel)

    if check:
        ok = not stale
        print(f"[{'PASS' if ok else 'FAIL'}] {OUT} matches defs/tlm_cmd.yaml"
              + ("" if ok else f" — stale or missing: {stale}; regenerate "
                               "(hand edits are prohibited by HUG-UI-005)"))
        return 0 if ok else 1
    print(f"generated {OUT} from defs/tlm_cmd.yaml "
          f"(dictionary {version}, sha256 {digest[:12]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
