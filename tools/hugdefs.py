#!/usr/bin/env python3
"""Shared loading and rendering vocabulary for the HUGINN `defs/` single sources.

Every generator imports the loaders and the render helpers from here. The rendering
vocabulary (how a limits kind becomes a dictionary cell, how a type becomes its
spelling) exists exactly once: if `gen_dictionary.py` and `gen_openc3_config.py` each
carried their own copy, the two views could drift apart while both still "came from
the defs", which is the failure single-source discipline exists to prevent
(B1/B2, HUG-GND-001).

The repo root is rebindable through `set_repo()` so the two-polarity suite in
tools/checkers/defs_generation.py can run real generation against a staged copy of
the sources. Directory accessors are functions, not constants, so a rebind is seen by
callers that imported them by name.

Stdlib plus PyYAML only.
"""
import re
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent

# Generated views and the source each is generated from.
GENERATED = {
    "docs/tlm_cmd_dictionary.md": "defs/tlm_cmd.yaml",
    "docs/requirements.md": "defs/requirements.yaml",
    "gnd/openc3/plugins/openc3-cosmos-huginn/": "defs/tlm_cmd.yaml",
    "docs/fmea.md": "defs/fmea.yaml",
    # The VÉ viewer's limit table. HUG-UI-005 requires the viewer's limits and alarm
    # colorings to derive from the dictionary at build time, so this is a generated view
    # like any other -- round-tripped by G1 and scanned by G12, which G12's own docstring
    # anticipated ("an VÉ display in Phase 4").
    "ve/viewer/limits.js": "defs/tlm_cmd.yaml",
    # The operator's procedure documents. Generated so the document a human
    # follows and the step list tools/pass_report.py reviews against cannot
    # differ by a step (HUG-OPS-001/002).
    "procedures/": "defs/procedures.yaml",
}


def set_repo(path):
    """Point every loader and generator at a different repo root."""
    global _ROOT
    _ROOT = Path(path).resolve()


def repo():
    return _ROOT


def defs_dir():
    return _ROOT / "defs"


def docs_dir():
    return _ROOT / "docs"


def _load(name):
    with (defs_dir() / name).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_tlm_cmd():
    return _load("tlm_cmd.yaml")


def load_requirements():
    return _load("requirements.yaml")


def load_replay_schema():
    return _load("replay_schema.yaml")


def load_fmea():
    return _load("fmea.yaml")


def load_ground():
    return _load("ground.yaml")


def load_eps():
    return _load("eps.yaml")


def load_procedures():
    return _load("procedures.yaml")


def load_evidence_chain():
    return _load("evidence_chain.yaml")


def points(defs):
    """All telemetry points in frame order: group order, then order within group."""
    return [p for g in defs["telemetry_groups"] for p in g["points"]]


def requirements_flat(defs):
    """Every requirement in record order, each tagged with its group id."""
    return [dict(r, group=g["id"]) for g in defs["groups"] for r in g["requirements"]]


TRACE_TOKEN = re.compile(r"\b(?:NEED-\d{2}|CON-\d{2}|ASM-\d{2}|HUG-[A-Z]+-\d{3})\b")


def trace_tokens(trace_cell):
    """The NEED / CON / ASM / HUG- identifiers cited by one requirement's trace cell.

    The trace cell is the ONE source for a requirement's upstream citations; this
    parses them rather than the source carrying a second, separately-maintained list
    that could disagree with it. HUG-VER-001's matrix (B3, Phase 6) uses this as its
    upstream spine.
    """
    return TRACE_TOKEN.findall(trace_cell)


def console():
    """Make stdout survive the record's own characters (−, →, —, ⇄).

    The Windows console default is cp1252, which raises UnicodeEncodeError on them:
    a tool would die mid-report with an exit status indistinguishable from a real
    failure. Report text is never the thing under test, so degrade rather than lose.
    """
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - non-reconfigurable stream
        pass


# --------------------------------------------------------------------------- render

MINUS = "−"  # U+2212 MINUS SIGN — the record spells negative limits with it
ARROW = "→"  # U+2192 RIGHTWARDS ARROW


def fmt_limit(value, decimals):
    """A limit value at its dictionary spelling; None is the absent-limit spelling."""
    if value is None:
        return "n/a"
    s = f"{abs(value):.{decimals}f}"
    return (MINUS + s) if value < 0 else s


def fmt_num(value):
    """Shortest exact decimal spelling (0.1 -> '0.1', 10 -> '10', 10.0 -> '10')."""
    return f"{value:g}"


def render_type(point):
    """The Type cell: 'float', 'uint16 (wraps)', 'enum {A, B, C}'."""
    if point["type"] == "enum":
        return "enum {" + ", ".join(point["enum_values"]) + "}"
    return point["type"] + (" (wraps)" if point.get("wraps") else "")


def render_limits(limits):
    """The Limits cell for one telemetry point, by `kind`."""
    kind = limits["kind"]
    if kind == "thresholds":
        d = limits["decimals"]
        return " / ".join(fmt_limit(limits[s], d) for s in ("rl", "yl", "yh", "rh"))
    if kind == "unalarmed":
        return "n/a (context-dependent; monitored, not alarmed)"
    if kind == "state":
        return "state-based: " + ", ".join(limits["annunciates"]) + " annunciates"
    if kind == "none":
        q = limits.get("qualifier")
        return f"none ({q})" if q else "none"
    if kind == "range":
        return f"valid range {fmt_num(limits['min'])}-{fmt_num(limits['max'])}"
    if kind == "staleness":
        return (f"staleness: no advance for {fmt_num(limits['yellow_s'])} s {ARROW} YL; "
                f"{fmt_num(limits['red_s'])} s {ARROW} RL (ground-computed derived check)")
    if kind == "delta":
        return f"delta > 0 annunciates {limits['severity']}"
    raise ValueError(f"unknown limits kind: {kind!r}")


def render_args(command):
    """The Arguments cell for one command."""
    args = command["args"]
    if not args:
        return "none"
    parts = []
    for a in args:
        if a["type"] == "enum":
            parts.append(f"{a['name']}: {{{', '.join(a['enum_values'])}}}")
        else:
            unit = f" {a['units']}" if a.get("units") else ""
            parts.append(f"{a['name']}: {a['type']}{unit}")
    return "; ".join(parts)


# ----------------------------------------------------------------------- doc output

def md_table(header_cells, body_rows):
    """A pipe table in the record's grammar: outer pipes, single-space padding,
    '|---|' delimiter row."""
    out = ["| " + " | ".join(header_cells) + " |",
           "|" + "---|" * len(header_cells)]
    out += ["| " + " | ".join(r) + " |" for r in body_rows]
    return out


def emit(path, lines, check_only=False):
    """Write `lines` (joined with LF, one trailing LF) to `path`, or in check mode
    compare and report. Returns True when the file on disk matches what would be
    written.

    LF and a single trailing newline are not cosmetic: C1 of the design-record
    consistency checks asserts zero CRLF pairs across the record, and bytes are
    written directly so the platform's text-mode newline translation cannot
    reintroduce them.
    """
    text = "\n".join(lines) + "\n"
    new = text.encode("utf-8")
    path = Path(path)
    old = path.read_bytes() if path.exists() else None
    if check_only:
        return old == new
    if old != new:
        path.write_bytes(new)
    return old == new
