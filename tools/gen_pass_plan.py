#!/usr/bin/env python3
"""The predicted pass plan: what a contact looks like if nothing goes wrong (OF-020).

    python tools/gen_pass_plan.py --pass-id 2026-10-11-P3 --scenario P3_stuck_load \\
                                  --start-at 800 --duration 430 --contact 9

Writes docs/pass_reports/<pass-id>/pass_plan.md and prints the same content to stdout,
in UTF-8, as tools/pass_setup.py does. Do not redirect it: it writes its own file, and a
`>` redirect would collide with that write.

THE PREDICTION IS THE SAME SCENARIO WITH ITS FAULTS REMOVED, AND NOTHING ELSE CHANGED.
Commands, illumination, initial state, seed and duration are identical. A scripted
command is a planned activity; a fault is the thing that was not planned. That is the
split HUG-SYS-005 already draws by making scenario files the sole source of faults, and
this tool does nothing but act on it.

Built any other way, the prediction is worthless in a particular and dangerous way. A
prediction run from the same scenario as the truth is the truth: actual-minus-predicted
is identically zero for every point at every second, and the plan reports a nominal pass
no matter what the spacecraft does. It would look like a working tool and never once say
anything. That is why `fault_free()` is the one function here that must not be got wrong,
why it checks its own result, and why tests/test_gen_pass_plan.py's divergence case was
made to fail by removing it before the case was trusted.

The faults list is emptied IN MEMORY, on the copy this run loaded, for this run only. No
scenario file is written, moved or re-timed.

WHAT THE CONTACT FLAGS MEAN: D-016 RULING 1. A pass flies a contact's DURATION, taken
from the computed week, at a mission POSITION the pass plan chooses, and both numbers
are recorded. So `--start-at` is the chosen position - an acquisition MET, not an
orbit-derived contact time. `--duration` is the length of a contact of the computed week,
and `--contact` names which one. The two must agree, and the tool refuses a `--duration`
that is not `--contact`'s length, before anything is written. The lengths come from
tools/gen_campaign.py's own `computed_week()` - the pinned orbit and D-014's mask, the
computation the campaign plan is generated from - and never from CAMPAIGN_PLAN.md, which
is a view of that computation and not a source.

BLIND TO THE TRUTH. This tool never reads a telemetry extract, a pass report, or anything
under docs/pass_reports/ - it only writes pass_plan.md there. A prediction that could see
what happened is not a prediction.

THE CHECKPOINTS COME FROM THE PROCEDURE. The four moments the plan reports are the ones
PROC-001 asks the operator to record, and their offsets are read from that procedure's own
step timings rather than restated here, so a change to the procedure moves the plan with
it. The timing grammar is parsed by the same function tools/gen_campaign.py uses.

DETERMINISTIC. The engine steps by count. The one value that is not a function of the
inputs is the generation timestamp; it honours SOURCE_DATE_EPOCH, the reproducible-builds
convention, so that with it fixed the same inputs give byte-identical output.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import check_deps                                                  # noqa: E402
check_deps.require("tools/gen_pass_plan.py")

import hugdefs                                                     # noqa: E402
from gen_campaign import _offset_s, computed_week                  # noqa: E402
from sim.scenario import Scenario                                  # noqa: E402
from sim.spacecraft import Spacecraft                              # noqa: E402

SCENARIOS = REPO / "sim" / "scenarios"
REPORTS = REPO / "docs" / "pass_reports"
PROFILE_STEP_S = 30

#: The moments PROC-001 asks the operator to record, by the step that asks.
CHECKPOINTS = (
    ("Acquisition", "PROC-001-S04"),
    ("Acquisition + 2 min", "PROC-001-S06"),
    ("Loss of signal - 2 min", "PROC-001-S15"),
    ("Loss of signal", "PROC-001-S16"),
)


class PlanRefused(ValueError):
    """A plan this tool cannot produce honestly, refused rather than emitted short."""


def fault_free(scenario):
    """THE RULE. Empty the faults on this in-memory copy, then prove nothing is left.

    `Scenario.faults` is the only path a fault takes into the model: faults_active_at()
    reads it and Spacecraft._faults_now() reads that. The check below does not trust
    that statement - it asks the scenario, at its own end, whether any fault is still
    active. If a second path ever appears, or this line is ever changed to empty a copy
    rather than the list the model reads, the plan is refused instead of being emitted
    as a prediction that is secretly the truth.
    """
    scenario.faults = []
    leaked = scenario.faults_active_at(float(scenario.duration_s))
    if leaked:
        raise RuntimeError(
            f"a fault survived the prediction rule: {leaked}. A plan built from it would "
            f"diverge from the truth by nothing, and say so for every pass.")
    return scenario


def contact_lengths():
    """Each computed-week contact's time above the mask, keyed by its 1-based number.

    The same call tools/gen_campaign.py's build() makes for the campaign plan's
    computed-week table, numbered the same way, so a contact means one thing in both.
    """
    windows, _week = computed_week()
    return {i: b - a for i, (a, b) in enumerate(windows, 1)}


def check_contact(contact, duration):
    """Refuse a --duration that is not --contact's length in the computed week.

    Without this, `--contact 9 --duration 410` produced a plan for a 410 s contact that
    called itself contact 9 - a silently wrong header on a document an operator plans
    from, and a pass whose length matched no contact the orbit actually gives.
    """
    lengths = contact_lengths()
    if contact not in lengths:
        raise PlanRefused(
            f"--contact {contact} is not a contact of the computed week, which has "
            f"contacts 1 to {len(lengths)}")
    length = lengths[contact]
    if abs(float(duration) - float(length)) > 1e-6:
        raise PlanRefused(
            f"contact {contact} is {length:g} s in the computed week; --duration "
            f"{duration:g} does not match")


def load_scenario(name):
    path = SCENARIOS / f"{name}.yaml"
    if not path.is_file():
        raise PlanRefused(f"no scenario named {name!r} in sim/scenarios/")
    return Scenario.load(path)


def check_window(scenario, start_at, duration, name=None):
    """Refuse a window the scenario cannot fill, naming the numbers that conflict."""
    if duration <= 0:
        raise PlanRefused(f"--duration {duration:g} must be a positive number of seconds")
    if start_at < 0:
        raise PlanRefused(f"--start-at {start_at:g} is before the mission began (MET 0)")
    name = name or scenario.scenario_id
    if start_at >= scenario.duration_s:
        raise PlanRefused(
            f"--start-at {start_at:g} is at or beyond {name}'s "
            f"duration_s of {scenario.duration_s}; there is no mission there to predict")
    if start_at + duration > scenario.duration_s:
        raise PlanRefused(
            f"--start-at {start_at:g} plus --duration {duration:g} ends at MET "
            f"{start_at + duration:g}, beyond {name}'s duration_s of "
            f"{scenario.duration_s}; the profile would stop short of loss of signal")


def predict(name, start_at, duration):
    """The fault-free mission's frames across the contact. Returns (scenario, frames)."""
    scenario = load_scenario(name)
    check_window(scenario, start_at, duration, name)
    fault_free(scenario)
    sim = Spacecraft(hugdefs.load_eps(), hugdefs.load_tlm_cmd(), scenario)
    while sim.t_s < start_at:
        sim.step()
    frames = []
    while sim.t_s < start_at + duration:
        frame = sim.step()
        if frame is not None:
            frames.append(frame)
    return scenario, frames


def checkpoints(start_at, duration):
    """(label, step id, the step's own timing text, MET) for each checkpoint."""
    procs = hugdefs.load_procedures()
    steps = {s["id"]: s for p in procs["procedures"] for s in p["steps"]}
    los = start_at + duration
    out = []
    for label, step_id in CHECKPOINTS:
        when = (steps.get(step_id) or {}).get("when", "")
        anchor, offset = _offset_s(when)
        if anchor is None:
            raise RuntimeError(
                f"{step_id}'s timing {when!r} is not AOS- or LOS-relative; the plan's "
                f"checkpoints are read from PROC-001 and can no longer be placed")
        met = (start_at if anchor == "AOS" else los) + offset
        # A moment at or after LOS has no frame; the last one inside the contact is
        # what an operator can actually record there.
        met = min(int(met), int(los) - 1)
        out.append((label, step_id, when, met))
    return out


def _generated_utc():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = (datetime.fromtimestamp(int(epoch), timezone.utc) if epoch is not None
            else datetime.now(timezone.utc))
    return when.isoformat(timespec="seconds")


def _row(frame):
    return (f"{frame['EPS_BATT_SOC']:.3f} | {frame['EPS_BATT_I']:+.4f} | "
            f"{frame['EPS_LOAD_I']:.3f} | {frame['ADM_ECLIPSE']} | {frame['EPS_MODE']}")


def render(pass_id, scenario_name, frames, start_at, duration, contact):
    """The artefact. Written for the person at the console, not for the build."""
    by_met = {f["CDH_MET"]: f for f in frames}
    first, last = int(start_at), int(start_at + duration) - 1
    los = int(start_at + duration)
    dictionary = hugdefs.load_tlm_cmd().get("dictionary_version", "?")

    lines = [
        f"# Pass plan — {pass_id}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Pass | `{pass_id}` |",
        f"| Scenario | `{scenario_name}` |",
        f"| Contact length | {duration:g} s, the length of computed contact {contact} |",
        f"| Acquisition (AOS) | MET {first}, chosen for this pass |",
        f"| Loss of signal (LOS) | MET {los}, computed: acquisition plus contact length |",
        f"| Dictionary version | {dictionary} |",
        f"| Generated (UTC) | {_generated_utc()} |",
        "",
        "## What this plan is",
        "",
        "This is the mission as it would run if nothing went wrong: the same scenario, with",
        "the same scripted commands, the same illumination and the same starting state, and",
        "with its faults removed. It was computed before the pass and has not seen the pass.",
        "",
        "During the contact, compare live telemetry against it. Where the two agree, the",
        "spacecraft is doing what was planned. Where they diverge, **the divergence is the",
        "fault's signature** — which point, by how much, starting when. Write the divergence",
        "down; it is the observation.",
        "",
        "A telemetry halt shows up differently. It costs no power, so the values that do",
        "arrive can agree perfectly with this plan. Its signature is frames this plan expects",
        "that never arrive — count them.",
        "",
        "## Predicted values at the procedure's checkpoints",
        "",
        "| Checkpoint | Step | Timing | MET | EPS_BATT_SOC % | EPS_BATT_I A "
        "| EPS_LOAD_I A | ADM_ECLIPSE | EPS_MODE |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for label, step_id, when, met in checkpoints(start_at, duration):
        note = " (last frame)" if met == last else ""
        lines.append(f"| {label} | {step_id} | {when} | {met}{note} | "
                     f"{_row(by_met[met])} |")

    lines += [
        "",
        "## Expected frames",
        "",
        f"**{len(frames)} frames**, MET {first} through {last}, one per second.",
        "",
        "Count what arrives. Frames that should have arrived and did not are an observation",
        "in their own right, even when every value that did arrive agrees with this plan.",
        "",
        "## Predicted illumination transitions",
        "",
    ]
    transitions = [(b["CDH_MET"], a["ADM_ECLIPSE"], b["ADM_ECLIPSE"])
                   for a, b in zip(frames, frames[1:])
                   if a["ADM_ECLIPSE"] != b["ADM_ECLIPSE"]]
    if transitions:
        lines += ["| MET | From | To |", "|---:|---|---|"]
        lines += [f"| {m} | {a} | {b} |" for m, a, b in transitions]
    else:
        lines.append(f"None inside this contact: {frames[0]['ADM_ECLIPSE']} throughout.")

    lines += [
        "",
        f"## Predicted profile, every {PROFILE_STEP_S} s",
        "",
        "| MET | EPS_BATT_SOC % | EPS_BATT_I A | EPS_LOAD_I A | ADM_ECLIPSE | EPS_MODE |",
        "|---:|---:|---:|---:|---|---|",
    ]
    mets = list(range(first, last + 1, PROFILE_STEP_S))
    if mets[-1] != last:
        mets.append(last)
    for met in mets:
        note = " (last frame)" if met == last else ""
        lines.append(f"| {met}{note} | {_row(by_met[met])} |")
    return "\n".join(lines) + "\n"


def generate(pass_id, scenario_name, start_at, duration, contact, out_root=None):
    """Predict, render, write. Returns (path, text).

    `out_root` defaults to REPORTS resolved HERE, at call time, not in the signature. A
    default bound at definition time ignores any later change to REPORTS, and that is
    not hypothetical: the test that proves a refused plan writes nothing re-points
    REPORTS at a scratch directory, and with the default bound early its "nothing was
    written" assertion inspected a directory this function could never write to. It
    could not fail, and when the window guard was removed on purpose the plan landed
    in the real docs/pass_reports/ instead.
    """
    out_root = REPORTS if out_root is None else out_root
    if not pass_id or any(c in pass_id for c in ("/", "\\")) or ".." in pass_id:
        raise PlanRefused(f"--pass-id {pass_id!r} must be a single folder name")
    check_contact(contact, duration)
    scenario, frames = predict(scenario_name, start_at, duration)
    text = render(pass_id, scenario_name, frames, start_at, duration, contact)
    folder = Path(out_root) / pass_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "pass_plan.md"
    path.write_bytes(text.encode("utf-8"))
    return path, text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pass-id", required=True)
    ap.add_argument("--scenario", required=True,
                    help="a file in sim/scenarios/, named without the extension")
    ap.add_argument("--start-at", type=float, required=True, metavar="MET",
                    help="the chosen acquisition MET")
    ap.add_argument("--duration", type=float, required=True, metavar="S",
                    help="contact length in seconds, from the computed week")
    ap.add_argument("--contact", type=int, required=True,
                    help="which computed-week contact the duration was taken from")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover
        pass
    try:
        _path, text = generate(args.pass_id, args.scenario, args.start_at,
                               args.duration, args.contact)
    except PlanRefused as exc:
        print(f"[REFUSED] {exc}", file=sys.stderr)
        return 2
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
