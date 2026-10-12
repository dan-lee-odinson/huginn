#!/usr/bin/env python3
"""Write a replay package for an executed pass (B11, recorder side).

    python -m ve.recorder P1_nominal_orbit --pass-id pass-001 --duration 600

The package is the recorder-to-VÉ interface defined by `defs/replay_schema.yaml`. This
module writes it; `ve/conformance.py` decides whether what was written is a package at
all, and this module refuses to claim it wrote one unless that check passes.

THE RECORDER CHECKS ITS OWN OUTPUT BEFORE CLAIMING SUCCESS. Not as a courtesy — as the
only way `RS-2-03` can mean anything. That rule says an identifier is used once, so a
later execution can neither overwrite an earlier pass nor quietly sit beside it. An
identifier is consumed the moment a file bearing it exists, so writing first and
validating afterwards would consume the identifier on a package that turned out not to
conform, and the pass could then never be recorded correctly under its own name.

TRACK IS COMPUTED, FRAMES ARE RECEIVED, AND THE DIFFERENCE IS THE POINT.
`track` comes from the propagated surrogate orbit and exists for every cadence instant
whether or not telemetry arrived (RS-4-01). `frames` carries one entry per housekeeping
frame ACTUALLY produced, and fabricates nothing (RS-5-01): under the generation-halt fault
there are simply no entries, and the gap is the record. A recorder that filled the gap —
with nulls, with the previous frame, with anything — would be manufacturing telemetry the
spacecraft never sent, which is the failure the whole outage-detection layer exists to
notice.
"""
import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
import hugdefs                                                    # noqa: E402
from ve import conformance                                      # noqa: E402
from sim.orbit import Orbit                                       # noqa: E402
from sim.scenario import Scenario                                 # noqa: E402
from sim.spacecraft import Spacecraft                             # noqa: E402

REPLAY_DIR = REPO / "replay"


class RecorderRefusal(RuntimeError):
    """The recorder declined to write, with the reason."""


def existing_pass_ids(replay_dir=None):
    """Identifiers already assigned to an executed pass (RS-2-03).

    Read from the directory rather than a side ledger. A ledger is a second place the
    truth lives, and the question "has this identifier been used?" is answered by
    whether a package bearing it exists — which is also what a reviewer would check.
    """
    replay_dir = Path(replay_dir or REPLAY_DIR)
    if not replay_dir.is_dir():
        return set()
    return {p.stem for p in replay_dir.glob("*.json")}


def _dict_ref():
    """The dictionary this package's values are native to (RS-7-14)."""
    version, digest = _source_digest()
    return {"version": str(version), "sha256": digest}


def _source_digest():
    raw = (REPO / "defs" / "tlm_cmd.yaml").read_bytes()
    return (hugdefs.load_tlm_cmd()["dictionary_version"],
            hashlib.sha256(raw).hexdigest())


def build_track(orbit, end_s, cadence_s, start_s=0.0):
    """One sample per cadence instant, from the propagated orbit (RS-4-01, RS-7-07).

    `start_s` offsets the SCENARIO time the orbit is asked about; the package's own t_s
    stays pass-relative and starts at 0, because that is what meta.epoch_utc anchors
    (RS-2-05). A recorder that wrote scenario time into t_s would put a package's zero
    somewhere other than its own epoch.
    """
    samples = []
    for i in range(math.floor(end_s / cadence_s) + 1):
        t = i * cadence_s
        scenario_t = start_s + t
        lat, lon, alt = orbit.subpoint(scenario_t)
        az, el, _rng = orbit.look_angles_at(scenario_t)
        samples.append({
            "t_s": t,
            "lat_deg": round(lat, 6),
            "lon_deg": round(_lon_range(lon), 6),
            "alt_km": round(alt, 3),
            "az_deg": round(az % 360.0, 6),
            "el_deg": round(el, 6),
            # Ground-computed illumination, deterministic on every pass shape and
            # independent of telemetry reception. ADM_ECLIPSE in a received frame is the
            # telemetered counterpart and is never the display source (G001-03 F-03).
            "ecl": not orbit.illuminated_at(scenario_t),
        })
    return samples


def _lon_range(lon):
    """Longitude in the schema's (-180, 180] — -180 is not a legal value (RS-7-09)."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return 180.0 if lon <= -180.0 else lon


def build_frames(sim, end_s, start_s=0.0):
    """(frames, events) for one recorded span.

    frames: one entry per housekeeping frame actually produced (RS-5-01). Member names
    are the dictionary mnemonic lowercased, the schema's bijective transform and the only
    mapping that exists (RS-5-02) — derived from the frame the simulator hands over, so a
    dictionary point added upstream appears here with no edit.

    events: what the C&DH DECIDED, observed by wrapping `cdh.receive` rather than by
    re-deriving it from counter deltas. The counters move for scenario-scripted commands
    too, so a recorder inferring outcomes from them would attribute the wrong result to
    the wrong command whenever both happened on one tick (OF-004). The C&DH's own return
    value is the fact; everything else is a reconstruction of it.
    """
    frames, events = [], []
    original_receive = sim.cdh.receive

    # Run the scenario forward to the recording start WITHOUT recording. The pass is
    # what the package covers; the hours of orbit before it are not part of this pass
    # and belong in no package.
    while sim.t_s < start_s:
        sim.step()

    def observing_receive(mnemonic, args=None):
        accepted, reason = original_receive(mnemonic, args)
        events.append({
            "t_s": sim.t_s - start_s,
            # Plain text, no markup: RS-6-01 binds the PRODUCER, and this is the
            # producer. The viewer's sink is a second, independent guarantee.
            "text": f"{mnemonic} {'accepted' if accepted else 'rejected'}",
            "sev": "info" if accepted else "warn",
            "cmd": {
                "mnemonic": mnemonic,
                "result": "accepted" if accepted else "rejected",
                # The event-local result-reason invariant (RS-7-15): reason is 'NONE'
                # if and only if result is 'accepted'. Taken from the C&DH's own
                # rejection reason so the two cannot disagree.
                "reason": "NONE" if accepted else str(reason),
            },
        })
        return accepted, reason

    sim.cdh.receive = observing_receive
    try:
        while sim.t_s < start_s + end_s:
            t = sim.t_s - start_s
            frame = sim.step()
            if frame is None:
                # The generation-halt fault. NOTHING is appended: the absence is the
                # record.
                continue
            frames.append({"t_s": t,
                           **{k.lower(): v for k, v in frame.items()}})
    finally:
        sim.cdh.receive = original_receive
    return frames, events


def build_events(sim_events):
    """Events as the schema defines them, with the result-reason invariant intact."""
    out = []
    for e in sim_events:
        event = {"t_s": e["t_s"], "text": e["text"], "sev": e["sev"]}
        if "cmd" in e:
            event["cmd"] = e["cmd"]
        out.append(event)
    return out


def build_package(scenario_name, pass_id, end_s=None, cadence_s=None,
                  gs="GS-RAVENSROOST", start_s=0.0):
    """The package for one executed pass, as a dict. Does not write."""
    scenario = Scenario.load(REPO / "sim" / "scenarios" / f"{scenario_name}.yaml")
    eps_defs, tlm_defs = hugdefs.load_eps(), hugdefs.load_tlm_cmd()
    sim = Spacecraft(eps_defs, tlm_defs, scenario)
    orbit = Orbit(REPO / "defs" / "orbit", scenario.start_epoch_utc)

    cadence_s = float(cadence_s or tlm_defs["frame"]["rate_hz"] and
                      1.0 / float(tlm_defs["frame"]["rate_hz"]))
    end_s = float(end_s if end_s is not None else scenario.duration_s)

    frames, events = build_frames(sim, end_s, start_s)
    events = build_events(events)
    track = build_track(orbit, end_s, cadence_s, start_s)

    # Contact windows are computed over the WHOLE span the orbit covers and then
    # expressed pass-relative, so a window that opened before the recording started is
    # still found rather than silently missed.
    windows = [(a - start_s, b - start_s)
               for a, b in orbit.contact_windows(start_s + end_s)
               if b > start_s and a < start_s + end_s]
    if windows:
        aos_s, los_s = float(max(0.0, windows[0][0])), float(windows[0][1])
    else:
        # No contact window inside the recorded span. The schema requires aos_s and
        # los_s, and inventing a window would put a contact on the display that the
        # geometry says did not happen — so the recorder refuses rather than guessing.
        raise RecorderRefusal(
            f"no contact window with {gs} in the recorded span "
            f"[{start_s}, {start_s + end_s}] s from {scenario.start_epoch_utc}; a "
            f"package must carry aos_s and los_s, and "
            f"the recorder does not invent a pass that the pinned geometry says did "
            f"not occur (RS-7-04)")

    eclipses = [(a - start_s, b - start_s)
                for a, b in orbit.eclipse_intervals(start_s + end_s)
                if b > start_s and a < start_s + end_s]
    version, _ = _source_digest()
    # meta.epoch_utc is "the instant of t_s = 0 on the recorder clock" (Sec. 3), and
    # t_s is pass-relative. When recording starts partway into a scenario, that instant
    # is the scenario epoch PLUS the recording start -- not the scenario epoch.
    #
    # Writing the scenario epoch put the viewer's clock 8900 s wrong on the first page
    # built: it read 00:01:30Z for a pass that happened at 02:29:50Z. Every value was
    # right and every time was wrong, which is the more dangerous of the two because
    # the display looks healthy.
    epoch = _iso_z(scenario.start_epoch_utc, offset_s=start_s)
    meta = {
        "pass_id": pass_id,
        "scenario": scenario_name,
        "gs": gs,
        "epoch_utc": epoch,
        "cadence_s": cadence_s,
        "aos_s": aos_s,
        "los_s": min(los_s, end_s),
        "end_s": end_s,
        "eclipse_entry_s": float(eclipses[0][0]) if eclipses else None,
        "eclipse_exit_s": float(eclipses[0][1]) if eclipses else None,
        "orbit_ref": (REPO / "defs" / "orbit" / "element_set.tle")
        .read_text(encoding="utf-8").strip().split("\n")[0].strip(),
        "dict_ref": _dict_ref(),
        "schema": str(hugdefs.load_replay_schema()["schema"]),
    }
    return {"meta": meta, "track": track, "frames": frames, "events": events}


def _iso_z(value, offset_s=0.0):
    """An ISO 8601 UTC instant with the trailing Z the schema requires (RS-2-05)."""
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        moment = datetime.fromisoformat(text)
    else:
        moment = value
    moment = moment.astimezone(timezone.utc) + timedelta(seconds=float(offset_s))
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_package(package, pass_id, replay_dir=None):
    """Validate, then write. In that order, and the order is the requirement.

    An identifier is consumed the moment a file bearing it exists, so a recorder that
    wrote first and validated afterwards would burn the identifier on a non-conforming
    package — and RS-2-03 would then forbid ever recording that pass correctly under its
    own name.
    """
    replay_dir = Path(replay_dir or REPLAY_DIR)
    target = replay_dir / f"{pass_id}.json"

    if pass_id in existing_pass_ids(replay_dir):
        raise RecorderRefusal(
            f"RS-2-03: pass_id {pass_id!r} is already assigned to an executed pass "
            f"({target.relative_to(REPO).as_posix() if target.exists() else target}). "
            f"An identifier is used once, so a later execution can neither overwrite an "
            f"earlier pass nor sit beside it.")

    problem = conformance.refuse(package, filename_stem=pass_id, path=target)
    if problem:
        raise RecorderRefusal(
            f"the recorder built a package that does not conform, and will not write "
            f"it — writing would consume the identifier on a package that is not one.\n"
            f"{problem}")

    replay_dir.mkdir(parents=True, exist_ok=True)
    # Compact, and ensure_ascii so the bytes are stable across platforms and locales.
    # This is a machine interface: pretty-printing a 9600-frame package costs megabytes
    # for whitespace no reader benefits from. allow_nan=False makes RS-7-02 structural --
    # a non-finite number cannot be serialised at all, rather than being written as the
    # `NaN` token that is not legal JSON and that some parsers accept anyway.
    body = json.dumps(package, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)
    target.write_bytes((body + "\n").encode("utf-8"))
    return target


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenario")
    ap.add_argument("--pass-id", required=True)
    ap.add_argument("--duration", type=float, default=None,
                    help="recorded span in seconds (default: the scenario's)")
    ap.add_argument("--start", type=float, default=0.0,
                    help="scenario time at which recording begins; the package's own "
                         "t_s remains pass-relative and starts at 0")
    ap.add_argument("--replay-dir", default=None)
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # pragma: no cover
        pass
    try:
        package = build_package(args.scenario, args.pass_id, end_s=args.duration,
                                start_s=args.start)
        target = write_package(package, args.pass_id, args.replay_dir)
    except RecorderRefusal as exc:
        print(f"REFUSED: {exc}")
        return 1
    print(f"wrote {target} — {len(package['track'])} track sample(s), "
          f"{len(package['frames'])} frame(s), {len(package['events'])} event(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
