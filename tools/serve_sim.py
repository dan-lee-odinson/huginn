#!/usr/bin/env python3
"""Run the simulator as a live telemetry source for the ground segment.

    python tools/serve_sim.py                       nominal, real time
    python tools/serve_sim.py P4_hk_generation_halt the generation-halt fault
    python tools/serve_sim.py --rate 10             ten simulated seconds per second
    python tools/serve_sim.py P2_array_string_loss --start-at 21700

`--start-at <MET>` steps the model silently from MET 0 to that mission elapsed time and
begins transmitting from there. It exists because the campaign's contacts are windows
into a mission and the anomaly scenarios inject their faults well after the first
contact closes, so a run that always began at MET 0 could not reach them (OF-016,
ruled at D-015). Scenario files are not re-timed: HUG-SYS-005 makes them the sole
source of faults.

The pre-roll is the same run, not a shortcut. The engine is stepped by count and is
deterministic (HUG-SYS-003), so N silent steps leave exactly the state N transmitted
steps would have. Scripted commands and fault onsets inside the pre-roll are applied to
the model as it passes through them; what is suppressed is the TRANSMISSION, not the
simulation. Nothing is written to the socket before the start MET, and the server does
not begin listening until the pre-roll is finished.

`--start-at` AND `--limit` COMPOSE, AND `--limit` STAYS ABSOLUTE. `--limit` is a mission
elapsed time at which to stop, not a duration to run for, and that is unchanged by this
flag. So a 430 s contact opening at MET 21700 is `--start-at 21700 --limit 22130`.

A `--limit` AT OR BELOW `--start-at` IS REFUSED, naming both values, exactly as a
`--start-at` at or beyond the scenario's end is. It would stop before the first frame, and
a simulator that starts, accepts COSMOS's connection and then sends nothing is, on the
console, the same picture as a simulator that is not running at all. Both refusals live in
`check_run_window()` and run before any socket opens. Absolute was chosen
because both numbers are then read off the same clock the pass plan and the scenario use;
a relative `--limit` would mean one of the two flags counted from the mission and the
other from the run.

The generated plugin declares HUGINN_INT as a tcpip_client_interface onto
host.docker.internal:<port>, so the SIMULATOR IS THE SERVER and COSMOS dials in. That
direction is not arbitrary: the ground system reconnecting on its own schedule is what
makes an outage look like an outage from the ground side, which is the condition B6's
staleness monitor exists to notice.

Time is driven by a wall clock here and only here. The scenario engine remains
bit-for-bit reproducible (HUG-SYS-003) because it is stepped by count, not by clock -
this loop decides WHEN to call step(), never what step() computes. Nothing downstream of
the simulator sees a timestamp that did not come from mission elapsed time.
"""
import argparse
import signal
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

# Dependency preflight BEFORE the imports that would otherwise raise. hugdefs pulls in
# PyYAML and sim.orbit pulls in sgp4, so without this the first thing a fresh terminal
# sees is a bare ModuleNotFoundError naming a module, not an instruction naming an
# interpreter. check_deps imports nothing but the standard library, so it is safe here.
import check_deps                                                 # noqa: E402
check_deps.require("tools/serve_sim.py")

import hugdefs                                                    # noqa: E402
from sim.interface import CommandCodec, FrameCodec, TelemetryServer  # noqa: E402
from sim.scenario import Scenario                                 # noqa: E402
from sim.spacecraft import Spacecraft                             # noqa: E402


def build(scenario_name):
    """The spacecraft under a named scenario file, constructed the one way.

    Same construction the suite uses (tests/harness.py), reached through the same
    loaders, so what the ground segment sees in a demonstration is the object the
    property tests make their claims about.
    """
    sc = Scenario.load(REPO / "sim" / "scenarios" / f"{scenario_name}.yaml")
    return Spacecraft(hugdefs.load_eps(), hugdefs.load_tlm_cmd(), sc)


def pre_roll(sim, start_at, quiet=False):
    """Step the model silently to `start_at` MET. Returns the number of steps taken.

    No frame reaches the socket: this is called before the server begins listening, and
    it never touches one. Everything the scenario does on the way - scripted commands,
    fault onsets - is applied, because `sim.step()` applies them and the whole point is
    that the model arrives in the state it would have been in.
    """
    if not start_at:
        return 0
    steps = 0
    while sim.t_s < start_at:
        sim.step()
        steps += 1
    if not quiet:
        print(f"  pre-rolled {steps} step(s) to MET {sim.t_s:.0f}s, nothing transmitted",
              flush=True)
    return steps


def check_run_window(scenario_name, duration_s, start_at, limit):
    """Refuse a run that would transmit nothing, before anything opens a socket.

    The two refusals are one rule seen from either end of the run, and they live
    together so that one cannot be tightened while the other is forgotten - which is
    how this function came to exist: the --start-at guard shipped alone, and the
    --limit half was owed for a month.

    `limit` is tested exactly as the serve loop tests it (`if limit and ...`), so
    `--limit 0` keeps its existing meaning of no limit.
    """
    name = scenario_name or "nominal"
    if start_at and start_at >= duration_s:
        raise ValueError(
            f"--start-at {start_at:.0f} is at or beyond {name}'s "
            f"duration_s of {duration_s}; the run would transmit nothing. "
            f"The latest useful start is below {duration_s}.")
    if limit and limit <= start_at:
        hint = ""
        if limit > 0:
            hint = (f" If {limit:.0f} was meant as a contact length, the stop MET is "
                    f"{start_at + limit:.0f}.")
        raise ValueError(
            f"--limit {limit:.0f} is at or below --start-at {start_at:.0f}; the run would "
            f"stop before transmitting a single frame. --limit is the MET to stop at, "
            f"not a duration.{hint}")


def serve(scenario, port, rate, limit, quiet=False, start_at=0.0):
    defs = hugdefs.load_tlm_cmd()
    codec, commands = FrameCodec(defs), CommandCodec(defs)
    sim = build(scenario)

    # Refused before anything opens a socket: a run that would transmit nothing tells
    # the operator nothing about why.
    check_run_window(scenario, sim.scenario.duration_s, start_at, limit)

    pre_roll(sim, start_at, quiet)
    server = TelemetryServer(codec, host="0.0.0.0", port=port).start()

    # THE UPLINK. Without this the server accepts command bytes, reads them off the
    # socket and drops them: COSMOS reports the command sent, the interface counts the
    # transmitted octets, and the spacecraft state never moves. Every ground-side
    # indication says success. It was found by sending a real command and then checking
    # EPS_MODE, which had not changed - not by anything the ground system reported.
    #
    # Commands are queued here and applied by the serve loop at a tick boundary, never
    # inside a step. The socket thread and the model must not interleave, and applying
    # at the boundary is also what keeps a command's effect visible within one frame
    # rather than landing halfway through the tick that reports it.
    from collections import deque
    uplink = deque()

    def on_command(raw):
        uplink.append(raw)

    server.on_command = on_command

    stopping = {"now": False}

    def stop(_signum, _frame):
        stopping["now"] = True

    signal.signal(signal.SIGINT, stop)
    if not quiet:
        # The start MET is on this line ALWAYS, including the default, so an operator
        # reading a transcript can never mistake a pre-rolled run for a normal one by
        # its absence.
        print(f"serving {scenario or 'nominal'} on 0.0.0.0:{port} "
              f"({rate}x real time), transmitting from MET {sim.t_s:.0f}s", flush=True)

    sent = suppressed = 0
    uplinked = [0]
    started = time.monotonic()
    try:
        while not stopping["now"]:
            if limit and sim.t_s >= limit:
                break
            while uplink:
                raw = uplink.popleft()
                mnemonic, args = commands.decode(raw)
                if mnemonic is None:
                    # Handed to the C&DH by opcode so it is ACCOUNTED as
                    # UNKNOWN_OPCODE. Dropping it here would leave the ground
                    # waiting on a counter delta that never comes (HUG-CMD-001).
                    opcode = int.from_bytes(raw[:2], "big") if len(raw) >= 2 else -1
                    accepted, reason = sim.cdh.receive_opcode(opcode)
                else:
                    accepted, reason = sim.cdh.receive(mnemonic, args)
                uplinked[0] += 1
                if not quiet:
                    print(f"  uplink t={sim.t_s:6.0f}s  {mnemonic or f'opcode {opcode}'}"
                          f"  {'ACCEPTED' if accepted else 'REJECTED ' + str(reason)}",
                          flush=True)
            frame = sim.step()
            if frame is None:
                # The generation-halt fault. Nothing is transmitted, deliberately:
                # the outage must reach the ground as an ABSENCE of frames, which is
                # the only form PROC-003 and the staleness monitor can act on.
                suppressed += 1
            else:
                server.send_frame(frame)
                sent += 1
                if not quiet and sent % 10 == 0:
                    print(f"  t={sim.t_s:6.0f}s  frames={sent}  "
                          f"clients={server.client_count}", flush=True)
            # Sleep against the elapsed total rather than per-tick, so drift does not
            # accumulate over a long pass.
            target = started + (sim.t_s / rate)
            gap = target - time.monotonic()
            if gap > 0:
                time.sleep(min(gap, 1.0))
    finally:
        server.stop()
    if not quiet:
        print(f"stopped: {sent} frames sent, {suppressed} suppressed by fault, "
              f"{uplinked[0]} commands uplinked", flush=True)
    return sent, suppressed, uplinked[0]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenario", nargs="?", default=None)
    ap.add_argument("--port", type=int, default=7801)
    ap.add_argument("--rate", type=float, default=1.0,
                    help="simulated seconds per wall second")
    ap.add_argument("--limit", type=float, default=None,
                    help="stop at this mission elapsed time (absolute, not a duration)")
    ap.add_argument("--start-at", type=float, default=0.0, metavar="MET",
                    help="step silently to this mission elapsed time, then transmit "
                         "from there (default 0: transmit from the beginning)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    serve(args.scenario, args.port, args.rate, args.limit, args.quiet,
          args.start_at)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
