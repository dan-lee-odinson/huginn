#!/usr/bin/env python3
"""Run a scenario and show what the operator would see.

    python sim/run.py                                  list the scenarios
    python sim/run.py P1_nominal                       summary plus a sampled timeline
    python sim/run.py P2_array_string_loss --every 300 a coarser timeline
    python sim/run.py P4_hk_generation_halt --events   only the moments that matter

This is a look at the model, not a ground system. Limit colouring here is computed
from defs/tlm_cmd.yaml purely so the timeline is readable; OpenC3 is the real
annunciator (Phase 3), and VÉ the real viewer (Phase 4).
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for extra in (str(REPO), str(REPO / "tools")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import hugdefs  # noqa: E402

from sim.scenario import Scenario  # noqa: E402
from sim.spacecraft import Spacecraft  # noqa: E402

SCENARIO_DIR = REPO / "sim" / "scenarios"


def limit_flag(limits, value):
    """R, Y or blank for a value against a dictionary threshold set."""
    if limits.get("kind") != "thresholds":
        return " "
    rl, yl, yh, rh = (limits.get(k) for k in ("rl", "yl", "yh", "rh"))
    if (rl is not None and value <= rl) or (rh is not None and value >= rh):
        return "R"
    if (yl is not None and value <= yl) or (yh is not None and value >= yh):
        return "Y"
    return " "


def main(argv=None):
    hugdefs.console()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", nargs="?", help="scenario name under sim/scenarios/")
    parser.add_argument("--every", type=int, default=600,
                        help="timeline sample interval in seconds (default 600)")
    parser.add_argument("--events", action="store_true",
                        help="show only mode changes, limit crossings and command "
                             "accounting changes")
    args = parser.parse_args(argv)

    available = sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))
    if not args.scenario:
        print("scenarios in sim/scenarios/:")
        for name in available:
            print(f"  {name}")
        return 0
    if args.scenario not in available:
        print(f"unknown scenario {args.scenario!r}; available: {', '.join(available)}",
              file=sys.stderr)
        return 2

    tlm = hugdefs.load_tlm_cmd()
    limits = {p["mnemonic"]: p["limits"]
              for g in tlm["telemetry_groups"] for p in g["points"]}
    scenario = Scenario.load(SCENARIO_DIR / f"{args.scenario}.yaml")
    sim = Spacecraft(hugdefs._load("eps.yaml"), tlm, scenario)

    print(f"scenario   {scenario.scenario_id}")
    print(f"           {scenario.description}")
    print(f"epoch      {scenario.start_epoch_utc}   seed {scenario.seed}   "
          f"duration {scenario.duration_s} s")
    if scenario.faults:
        for f in scenario.faults:
            extra = f" string {f['string']}" if f["string"] else ""
            print(f"fault      t+{f['t_s']:>6} s  {f['fault']}{extra}")
    for c in scenario.commands:
        print(f"command    t+{c['t_s']:>6} s  {c['mnemonic']} {c['args'] or ''}")
    print()
    header = (f"{'MET':>7}  {'ecl':<7} {'mode':<9} {'SoC':>7} {'V':>7} "
              f"{'battI':>7} {'loadI':>7} {'SA1':>6} {'SA2':>6}  {'PLD':<4} "
              f"{'ACC':>4} {'REJ':>4}  reason")
    print(header)
    print("-" * len(header))

    frames = []
    previous = None
    while sim.t_s < scenario.duration_s:
        frame = sim.step()
        if frame is None:
            continue
        frames.append(frame)
        met = frame["CDH_MET"]
        interesting = previous is None or (
            frame["EPS_MODE"] != previous["EPS_MODE"]
            or frame["PLD_STATE"] != previous["PLD_STATE"]
            or frame["ADM_ECLIPSE"] != previous["ADM_ECLIPSE"]
            or frame["CDH_CMD_ACC_CNT"] != previous["CDH_CMD_ACC_CNT"]
            or frame["CDH_CMD_REJ_CNT"] != previous["CDH_CMD_REJ_CNT"]
            or limit_flag(limits["EPS_BATT_SOC"], frame["EPS_BATT_SOC"])
            != limit_flag(limits["EPS_BATT_SOC"], previous["EPS_BATT_SOC"])
            or limit_flag(limits["EPS_LOAD_I"], frame["EPS_LOAD_I"])
            != limit_flag(limits["EPS_LOAD_I"], previous["EPS_LOAD_I"]))
        if interesting or (not args.events and met % args.every == 0):
            print(f"{met:>7}  {frame['ADM_ECLIPSE']:<7} {frame['EPS_MODE']:<9} "
                  f"{frame['EPS_BATT_SOC']:>6.2f}{limit_flag(limits['EPS_BATT_SOC'], frame['EPS_BATT_SOC'])} "
                  f"{frame['EPS_BATT_V']:>6.2f}{limit_flag(limits['EPS_BATT_V'], frame['EPS_BATT_V'])} "
                  f"{frame['EPS_BATT_I']:>6.2f}{limit_flag(limits['EPS_BATT_I'], frame['EPS_BATT_I'])} "
                  f"{frame['EPS_LOAD_I']:>6.2f}{limit_flag(limits['EPS_LOAD_I'], frame['EPS_LOAD_I'])} "
                  f"{frame['EPS_SA1_I']:>6.2f} {frame['EPS_SA2_I']:>6.2f}  "
                  f"{frame['PLD_STATE']:<4} {frame['CDH_CMD_ACC_CNT']:>4} "
                  f"{frame['CDH_CMD_REJ_CNT']:>4}  {frame['CDH_REJ_REASON']}")
        previous = frame

    expected = int(scenario.duration_s / sim.dt)
    gap = expected - len(frames)
    print()
    print(f"frames generated {len(frames)} of {expected} ticks"
          + (f"; {gap} absent - the generation-halt gap, preserved as the record"
             if gap else ""))
    socs = [f["EPS_BATT_SOC"] for f in frames]
    print(f"SoC {socs[0]:.2f}% -> {socs[-1]:.2f}%   minimum {min(socs):.2f}%   "
          f"modes seen: {', '.join(sorted({f['EPS_MODE'] for f in frames}))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
