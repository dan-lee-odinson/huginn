#!/usr/bin/env python3
"""The replay-package conformance contract, checked rule by rule (B11).

    python -m ve.conformance replay/pass-001.json

`defs/replay_schema.yaml` is the recorder-to-VÉ interface, and its 32 conformance rules
are the whole of what a package must satisfy. This module is the one implementation of
them: the recorder writes a package and checks it before claiming to have written one,
and the viewer checks a package before rendering a pixel of it.

ONE IMPLEMENTATION, TWO CALLERS. HUG-UI-003 says recorder and viewer both reference the
interface definition and neither embeds a private copy. A checker per side is a private
copy with extra steps — the two drift, each stays green against its own reading, and the
seam between them is where a malformed package lives. That is the shape D-032 removed
from the resolution rule in another repository on this machine, and the shape D-009 cost
this build a demo plugin over. So: one module, and the rules come from the schema.

EVERY REFUSAL NAMES ITS RULE (RS-7-20). A refusal that says "invalid package" tells an
operator nothing they can act on, and tells a reviewer nothing about which guarantee
failed. Each violation here carries the rule id and the observed value.

THE RULE SET IS DERIVED, NOT RESTATED. `RULES` below is read from the schema at import,
and `test_replay_conformance.py` asserts that every rule the schema declares has a check
here. A rule added to the interface definition and not to this file is a rule nobody
enforces, and it would fail silently — the package would simply pass.
"""
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hugdefs                                                    # noqa: E402


def rule_ids():
    """Every conformance rule id the interface definition declares."""
    return [r["id"] for r in hugdefs.load_replay_schema()["conformance_rules"]]


def rule_statement(rule_id):
    for r in hugdefs.load_replay_schema()["conformance_rules"]:
        if r["id"] == rule_id:
            return r.get("statement", "")
    raise KeyError(rule_id)


class Violation:
    """One failed rule, named."""

    def __init__(self, rule, detail):
        self.rule = rule
        self.detail = detail

    def __str__(self):
        return f"{self.rule}: {self.detail}"

    def __repr__(self):                                # pragma: no cover
        return f"Violation({self.rule!r}, {self.detail!r})"


# --------------------------------------------------------------------------- helpers

def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _strictly_increasing(values):
    return all(b > a for a, b in zip(values, values[1:]))


def _telemetry_points():
    defs = hugdefs.load_tlm_cmd()
    return [p for g in defs["telemetry_groups"] for p in g["points"]]


def _member_names():
    """The frame member names, by the schema's bijective transform (RS-5-02)."""
    return {p["mnemonic"].lower(): p for p in _telemetry_points()}


# ----------------------------------------------------------------------------- checks
#
# One function per rule, named for the rule. Each appends Violations and returns nothing;
# a rule that cannot be evaluated because an earlier structural rule already failed says
# so rather than raising, so a single malformed package produces a full report instead of
# stopping at the first problem an operator would then have to fix blind.

def check(package, filename_stem=None, known_pass_ids=(), path=None):
    """(ok, [Violation, ...]) for one package.

    `filename_stem` enables RS-7-18; `known_pass_ids` enables RS-2-03/RS-7-19. Omitting
    either does not silently skip its rule — the rule reports that it could not be
    evaluated, because a check that quietly does nothing is indistinguishable from one
    that passed.
    """
    v = []
    schema = hugdefs.load_replay_schema()

    # --- RS-2-02: exactly four top-level members
    if not isinstance(package, dict):
        return False, [Violation("RS-2-02", f"package is {type(package).__name__}, "
                                            f"not a JSON object")]
    expected_top = set(schema["top_level_members"])
    actual_top = set(package)
    if actual_top != expected_top:
        v.append(Violation(
            "RS-2-02",
            f"top-level members are {sorted(actual_top)}, contract requires exactly "
            f"{sorted(expected_top)}"))

    meta = package.get("meta")
    track = package.get("track")
    frames = package.get("frames")
    events = package.get("events")
    if not isinstance(meta, dict):
        v.append(Violation("RS-2-02", "meta is missing or not an object"))
        return False, v
    for name, value in (("track", track), ("frames", frames), ("events", events)):
        if not isinstance(value, list):
            v.append(Violation("RS-2-02", f"{name} is missing or not an array"))
    if any(not isinstance(x, list) for x in (track, frames, events)):
        return False, v

    # --- RS-7-01: no members outside the schema, at every level
    meta_fields = schema["meta_fields"]
    extra_meta = set(meta) - set(meta_fields)
    if extra_meta:
        v.append(Violation("RS-7-01", f"meta carries undefined member(s) "
                                      f"{sorted(extra_meta)}"))
    missing_meta = [k for k, spec in meta_fields.items()
                    if spec.get("required") and k not in meta]
    if missing_meta:
        v.append(Violation("RS-7-01", f"meta is missing required member(s) "
                                      f"{sorted(missing_meta)}"))
    track_fields = set(schema["track_sample_fields"])
    for i, s in enumerate(track):
        if not isinstance(s, dict):
            v.append(Violation("RS-7-01", f"track[{i}] is not an object"))
            continue
        if set(s) - track_fields:
            v.append(Violation("RS-7-01", f"track[{i}] carries undefined member(s) "
                                          f"{sorted(set(s) - track_fields)}"))
        if track_fields - set(s):
            v.append(Violation("RS-7-01", f"track[{i}] is missing "
                                          f"{sorted(track_fields - set(s))}"))
    event_fields = set(schema["event_fields"])
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            v.append(Violation("RS-7-01", f"events[{i}] is not an object"))
            continue
        if set(e) - event_fields:
            v.append(Violation("RS-7-01", f"events[{i}] carries undefined member(s) "
                                          f"{sorted(set(e) - event_fields)}"))

    # --- RS-3-01: meta.schema is the schema number of this interface definition
    if str(meta.get("schema")) != str(schema["schema"]):
        v.append(Violation("RS-3-01", f"meta.schema is {meta.get('schema')!r}, this "
                                      f"interface definition is {schema['schema']!r}"))

    # --- RS-7-16/17/18: the pass_id grammar, reserved basenames, filename stem
    pass_id = meta.get("pass_id")
    grammar = meta_fields["pass_id"]["grammar"]
    if not isinstance(pass_id, str) or not re.match(grammar, pass_id):
        v.append(Violation("RS-7-16", f"pass_id {pass_id!r} does not match {grammar}"))
    if isinstance(pass_id, str) and pass_id.lower() in set(
            meta_fields["pass_id"]["reserved_basenames"]):
        v.append(Violation("RS-7-17", f"pass_id {pass_id!r} is a reserved device "
                                      f"basename"))
    if filename_stem is None:
        v.append(Violation("RS-7-18", "no filename stem supplied, so equality with "
                                      "pass_id could not be evaluated"))
    elif pass_id != filename_stem:
        v.append(Violation("RS-7-18", f"pass_id {pass_id!r} is not byte-equal to the "
                                      f"filename stem {filename_stem!r}"))

    # --- RS-2-01: the package sits at replay/<pass_id>.json
    if path is not None:
        path = Path(path)
        if path.suffix != ".json":
            v.append(Violation("RS-2-01", f"package path {path.as_posix()!r} is not a "
                                          f".json file"))
        if path.parent.name != "replay":
            v.append(Violation("RS-2-01", f"package path {path.as_posix()!r} is not "
                                          f"under replay/"))

    # --- RS-2-05: t_s is anchored to UTC by meta.epoch_utc, so the anchor must be one
    epoch = meta.get("epoch_utc")
    if not isinstance(epoch, str) or not EPOCH_UTC.match(epoch):
        v.append(Violation("RS-2-05", f"meta.epoch_utc is {epoch!r}; every t_s is "
                                      f"anchored to UTC by it, so it must be an "
                                      f"ISO 8601 UTC instant"))

    # --- RS-2-03 / RS-7-19: identifiers are used once
    if isinstance(pass_id, str) and pass_id in set(known_pass_ids):
        v.append(Violation("RS-2-03", f"pass_id {pass_id!r} is already assigned to an "
                                      f"executed pass; an identifier is used once"))
        v.append(Violation("RS-7-19", f"a second package exists for pass {pass_id!r}"))

    # --- RS-7-02: all numbers finite
    def scan_numbers(node, path):
        if isinstance(node, dict):
            for k, val in node.items():
                scan_numbers(val, f"{path}.{k}")
        elif isinstance(node, list):
            for i, val in enumerate(node):
                scan_numbers(val, f"{path}[{i}]")
        elif _num(node) and not math.isfinite(node):
            v.append(Violation("RS-7-02", f"{path} is {node}, which is not finite"))
    scan_numbers(package, "package")

    # --- RS-7-03/04: cadence and the pass window
    cadence = meta.get("cadence_s")
    if not _finite(cadence) or cadence <= 0:
        v.append(Violation("RS-7-03", f"cadence_s is {cadence!r}, must be > 0"))
    aos, los, end = meta.get("aos_s"), meta.get("los_s"), meta.get("end_s")
    if not all(_finite(x) for x in (aos, los, end)):
        v.append(Violation("RS-7-04", f"aos_s/los_s/end_s are {aos!r}/{los!r}/{end!r}; "
                                      f"all must be finite numbers"))
    elif not (0 <= aos < los <= end):
        v.append(Violation("RS-7-04", f"requires 0 <= aos_s < los_s <= end_s, got "
                                      f"{aos} / {los} / {end}"))

    # --- RS-7-05/06: every t_s in range, strictly increasing per array
    for name, arr in (("track", track), ("frames", frames), ("events", events)):
        times = [s.get("t_s") for s in arr if isinstance(s, dict)]
        if any(not _finite(t) for t in times):
            v.append(Violation("RS-7-05", f"{name} has a non-numeric t_s"))
            continue
        if _finite(end):
            out = [t for t in times if not (0 <= t <= end)]
            if out:
                v.append(Violation("RS-7-05", f"{name} has t_s outside [0, {end}]: "
                                              f"{out[:4]}"))
        if not _strictly_increasing(times):
            v.append(Violation("RS-7-06", f"{name}.t_s is not strictly increasing"))

    # --- RS-7-07: the track grid
    if _finite(end) and _finite(cadence) and cadence > 0:
        expected = math.floor(end / cadence) + 1
        if len(track) != expected:
            v.append(Violation("RS-7-07", f"track has {len(track)} samples, the grid "
                                          f"requires floor({end}/{cadence})+1 = "
                                          f"{expected}"))
        for i, s in enumerate(track):
            if not isinstance(s, dict):
                continue
            t = s.get("t_s")
            if _finite(t) and abs(t - i * cadence) > 1e-9:
                v.append(Violation("RS-7-07", f"track[{i}].t_s is {t}, the cadence "
                                              f"grid puts it at {i * cadence}"))
                break

    # --- RS-4-01: track always present
    if not track:
        v.append(Violation("RS-4-01", "track is empty; it carries computed position "
                                      "independent of telemetry reception and is "
                                      "always present"))

    # --- RS-7-08/09: track domains
    ranges = {"lat_deg": (-90, 90, True, True), "az_deg": (0, 360, True, False),
              "el_deg": (-90, 90, True, True)}
    for i, s in enumerate(track):
        if not isinstance(s, dict):
            continue
        if not isinstance(s.get("ecl"), bool):
            v.append(Violation("RS-7-08", f"track[{i}].ecl is {s.get('ecl')!r}, "
                                          f"must be a boolean"))
        lon = s.get("lon_deg")
        if _finite(lon) and not (-180 < lon <= 180):
            v.append(Violation("RS-7-09", f"track[{i}].lon_deg is {lon}, must be in "
                                          f"(-180, 180]"))
        for field, (lo, hi, lo_in, hi_in) in ranges.items():
            val = s.get(field)
            if not _finite(val):
                continue
            ok = (lo <= val if lo_in else lo < val) and (val <= hi if hi_in else val < hi)
            if not ok:
                v.append(Violation("RS-7-09", f"track[{i}].{field} is {val}, outside "
                                              f"its Sec. 4 range"))

    # --- RS-5-02: frame member names are the dictionary's, lowercased
    members = _member_names()
    for i, f in enumerate(frames):
        if not isinstance(f, dict):
            v.append(Violation("RS-5-01", f"frames[{i}] is not an object"))
            continue
        # t_s is the package timebase (RS-2-05, RS-7-06), carried by every array entry.
        # It is not a telemetry point, and the bijective transform does not cover it.
        unknown = set(f) - set(members) - {"t_s"}
        if unknown:
            v.append(Violation("RS-5-02", f"frames[{i}] carries member(s) {sorted(unknown)} "
                                          f"which are not dictionary mnemonics "
                                          f"lowercased"))
        missing = set(members) - set(f)
        if missing:
            v.append(Violation("RS-5-02", f"frames[{i}] is missing {sorted(missing)}"))

    # --- RS-7-10/11/12/13: dictionary-native value domains, unconditionally
    for i, f in enumerate(frames):
        if not isinstance(f, dict):
            continue
        for name, point in members.items():
            if name not in f:
                continue
            val = f[name]
            if point["type"] == "enum":
                if val not in point["enum_values"]:
                    v.append(Violation("RS-7-10", f"frames[{i}].{name} is {val!r}, not "
                                                  f"a dictionary value of "
                                                  f"{point['mnemonic']}"))
            elif "CNT" in point["mnemonic"]:
                if not isinstance(val, int) or isinstance(val, bool) \
                        or not (0 <= val <= 65535):
                    v.append(Violation("RS-7-11", f"frames[{i}].{name} is {val!r}, must "
                                                  f"be an integer in [0, 65535]"))
        soc = f.get("eps_batt_soc")
        if _finite(soc) and not (0 <= soc <= 100):
            v.append(Violation("RS-7-12", f"frames[{i}].eps_batt_soc is {soc}, must be "
                                          f"in [0, 100]"))
        rate = f.get("pld_rate")
        if _finite(rate) and not (0.1 <= rate <= 10):
            v.append(Violation(
                "RS-7-13",
                f"frames[{i}].pld_rate is {rate} with pld_state="
                f"{f.get('pld_state')!r}; the rate register always holds a "
                f"dictionary-valid value, so an OFF frame still reports one in "
                f"[0.1, 10]"))

    # --- RS-6-01: event text is plain, no markup
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            continue
        text = e.get("text")
        if not isinstance(text, str):
            v.append(Violation("RS-6-01", f"events[{i}].text is {text!r}, must be a "
                                          f"string"))
        elif MARKUP.search(text):
            v.append(Violation("RS-6-01", f"events[{i}].text carries markup-significant "
                                          f"content: {text[:60]!r}"))
        sev = e.get("sev")
        if sev not in schema["event_fields"]["sev"]["values"]:
            v.append(Violation("RS-7-01", f"events[{i}].sev is {sev!r}, not one of "
                                          f"{schema['event_fields']['sev']['values']}"))

    # --- RS-6-02 / RS-7-14 / RS-7-15: the command sub-object
    commands = {c["mnemonic"] for c in hugdefs.load_tlm_cmd()["commands"]}
    reasons = next(p["enum_values"] for p in _telemetry_points()
                   if p["mnemonic"] == "CDH_REJ_REASON")
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            continue
        cmd = e.get("cmd")
        if cmd is None:
            continue
        if not isinstance(cmd, dict):
            v.append(Violation("RS-6-02", f"events[{i}].cmd is {cmd!r}, must be an "
                                          f"object"))
            continue
        if cmd.get("mnemonic") not in commands:
            v.append(Violation("RS-7-14", f"events[{i}].cmd.mnemonic "
                                          f"{cmd.get('mnemonic')!r} is not in the "
                                          f"dict_ref dictionary"))
        result, reason = cmd.get("result"), cmd.get("reason")
        if result not in ("accepted", "rejected"):
            v.append(Violation("RS-6-02", f"events[{i}].cmd.result is {result!r}"))
        if reason not in reasons:
            v.append(Violation("RS-7-14", f"events[{i}].cmd.reason {reason!r} is not a "
                                          f"CDH_REJ_REASON dictionary value"))
        elif (reason == "NONE") != (result == "accepted"):
            v.append(Violation(
                "RS-7-15",
                f"events[{i}].cmd has result={result!r} with reason={reason!r}; the "
                f"event-local invariant is that reason is 'NONE' if and only if result "
                f"is 'accepted'"))

    return not v, v


#: Characters and sequences that make a string markup-significant. Deliberately broad:
#: RS-6-01 forbids producers emitting markup at all, so this is a producer-side gate, and
#: the viewer's inertness does not depend on it (HUG-UI-007 is discharged by the sink, not
#: by this pattern). Two independent guarantees, because a filter is a thing that can have
#: a hole and a sink that never interprets cannot.
MARKUP = re.compile(r"[<>&]|\bjavascript:|\bdata:text/html|&#|</?\s*\w+", re.I)

#: An ISO 8601 UTC instant. Every t_s in the package is pass-relative seconds anchored to
#: UTC by meta.epoch_utc (RS-2-05), so an anchor that is not an instant leaves the whole
#: timeline unanchored — every displayed time would be relative to nothing.
EPOCH_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


# --------------------------------------------------------------------- rules coverage

def implemented_in_check():
    """Rule ids this module enforces as package-content checks, from its own source.

    Derived from the source rather than hand-listed, so it cannot claim a rule it does
    not check. `test_replay_conformance.py` compares this against the schema's declared
    set: a rule in the interface definition with no check here is a rule nobody enforces,
    and a package violating it would simply pass.
    """
    src = Path(__file__).read_text(encoding="utf-8")
    # `\s*` matters: two of these are constructed across a line break, and a pattern
    # that missed them reported them unimplemented when they were not. A coverage
    # report that undercounts is a smaller problem than one that overcounts, but both
    # are the module lying about itself.
    return set(re.findall(r'Violation\(\s*"(RS-[\d-]+)"', src))


def implemented_rules():
    """Every rule implemented anywhere: as a content check here, or at the viewer.

    Two sites, one accounting. `test_replay_conformance.py` asserts that declared ==
    check + viewer, that nothing appears in both, and that nothing falls out of both --
    a rule the schema declares and nobody implements would otherwise sit in the registry
    looking accounted for while a package violating it simply passed.
    """
    return implemented_in_check() | set(IMPLEMENTED_AT_VIEWER)


#: Rules that are not properties of a package's CONTENT, and the code that implements
#: each one at the viewer.
#:
#: These were DISPOSITIONS — prose saying where a rule would be honoured, written before
#: the viewer existed. A disposition is a promise; each of these is now a named module
#: and symbol that a test calls. The distinction matters because a disposition cannot
#: fail: it is a sentence, and sentences stay true while the code beneath them rots.
#:
#: `test_ve_viewer.py` calls every symbol named here and asserts it does the thing the
#: entry claims. A rule listed with a symbol that does not exist, or that exists and does
#: not behave, fails — which is exactly what a disposition could never do.
IMPLEMENTED_AT_VIEWER = {
    "RS-2-04": {
        "module": "ve.viewer.build",
        "symbol": "build",
        "how": "runs the full contract before writing a byte of page and raises "
               "ViewerRefusal on any violation; the emitted page has no fetch, no file "
               "input and no import, so there is no code path from an unchecked "
               "package to a display.",
    },
    "RS-4-02": {
        "module": "ve.interpolate",
        "symbol": "ground_track_segments",
        "how": "splits the drawn ground track where it crosses the antimeridian, and "
               "shortest_arc interpolates the circular quantities between samples; "
               "linear interpolation would draw a line across the whole map through "
               "longitudes never visited.",
    },
    "RS-7-20": {
        "module": "ve.conformance",
        "symbol": "refuse",
        "how": "every refusal names the rule it failed and quotes that rule's own "
               "statement from the interface definition, so an operator is told what "
               "to fix rather than that something is invalid.",
    },
}


def refuse(package, filename_stem=None, known_pass_ids=(), path=None):
    """Render the refusal an operator sees. RS-7-20: a refusal names its rule."""
    ok, violations = check(package, filename_stem, known_pass_ids, path)
    if ok:
        return None
    # Grouped by rule. A structural mistake in a recorder produces one violation per
    # frame, and ten thousand identical lines buries the other rules that also failed —
    # an operator then fixes the one they can see and re-runs into the next. Each rule
    # is stated once, with how many entries hit it and the first few that did.
    by_rule = {}
    for viol in violations:
        by_rule.setdefault(viol.rule, []).append(viol.detail)
    lines = [f"REFUSED: the package violates {len(by_rule)} conformance rule(s) of "
             f"replay schema {hugdefs.load_replay_schema()['schema']} "
             f"({len(violations)} occurrence(s))."]
    for rule in sorted(by_rule):
        details = by_rule[rule]
        lines.append(f"  {rule}  ({len(details)} occurrence(s))")
        lines.append(f"      rule: {rule_statement(rule)}")
        for detail in details[:3]:
            lines.append(f"      - {detail}")
        if len(details) > 3:
            lines.append(f"      - ... and {len(details) - 3} more")
    return "\n".join(lines)


def main(argv):
    if not argv:
        print(__doc__.split("\n")[0])
        return 2
    path = Path(argv[0])
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {path} could not be read as JSON ({exc})")
        return 1
    problem = refuse(package, filename_stem=path.stem, path=path)
    if problem:
        print(problem)
        return 1
    print(f"[PASS] {path} conforms to replay schema "
          f"{hugdefs.load_replay_schema()['schema']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
