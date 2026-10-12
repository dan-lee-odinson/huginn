#!/usr/bin/env python3
"""How the viewer draws BETWEEN track samples (RS-4-02).

RS-4-02: *"Circular quantities (lon_deg, az_deg) interpolate along the shortest arc;
non-circular quantities (lat_deg, alt_km, el_deg) interpolate linearly."*

This is the rule no single package can exhibit or violate, which is why
`ve/conformance.py` dispositions it here rather than pretending to check it. It is a
property of the viewer's drawing, and the only place it can be demonstrated is in the
drawing.

WHY IT MATTERS, concretely. A ground track crossing the antimeridian has consecutive
samples at lon_deg = 179.5 and -179.5. Linear interpolation walks the long way round —
359 degrees of the wrong direction — and draws a line straight across the map, through
every longitude the spacecraft was never at. It looks like a glitch, so an operator
learns to ignore it, and the next time the display is wrong about something that matters
they ignore that too. The same applies to azimuth sweeping through north during a pass,
which is the ordinary case at a high-latitude ground station, not an edge case.

WHICH QUANTITIES ARE CIRCULAR IS READ FROM THE SCHEMA, not decided here. A quantity moved
between the two lists in `defs/replay_schema.yaml` changes this module's behaviour with no
edit, which is the point: the interface definition is the single source and this is one of
its two readers.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hugdefs                                                    # noqa: E402


def circular_fields():
    """Track fields the schema declares circular."""
    return set(hugdefs.load_replay_schema()["interpolation"]["shortest_arc"])


def linear_fields():
    """Track fields the schema declares non-circular."""
    return set(hugdefs.load_replay_schema()["interpolation"]["linear"])


def lerp(a, b, f):
    """Straight-line interpolation, for quantities that do not wrap."""
    return a + (b - a) * f


def shortest_arc(a, b, f, period=360.0):
    """Interpolate a circular quantity the short way round.

    The difference is reduced into (-period/2, +period/2], so a step from 179.5 to
    -179.5 is treated as +1 degree rather than -359. The result is returned in the
    schema's own range for longitude, (-180, 180], because a viewer that produced 180.5
    would be handing its own display a value the conformance contract would refuse.
    """
    delta = (b - a + period / 2.0) % period - period / 2.0
    value = a + delta * f
    # Normalise into (-180, 180] for period=360: the half-open end matters, since 180 is
    # a legal longitude and -180 is not (RS-7-09).
    value = (value + period / 2.0) % period - period / 2.0
    if value <= -period / 2.0:
        value += period
    return value


def sample_at(track, t_s):
    """The track state at an arbitrary time, interpolated per RS-4-02.

    Times outside the track clamp to its ends rather than extrapolating. A viewer that
    extrapolated would draw positions the recorder never computed, which is the same
    fabrication RS-5-01 forbids for frames — the orbit view would show the spacecraft
    somewhere nothing ever said it was.
    """
    if not track:
        raise ValueError("an empty track has no state to interpolate; a package with "
                         "an empty track is refused by RS-4-01 before reaching here")
    if t_s <= track[0]["t_s"]:
        return dict(track[0])
    if t_s >= track[-1]["t_s"]:
        return dict(track[-1])

    lo = 0
    for i in range(len(track) - 1):
        if track[i]["t_s"] <= t_s <= track[i + 1]["t_s"]:
            lo = i
            break
    a, b = track[lo], track[lo + 1]
    span = b["t_s"] - a["t_s"]
    f = 0.0 if span == 0 else (t_s - a["t_s"]) / span

    circular, linear = circular_fields(), linear_fields()
    out = {"t_s": t_s}
    for field in set(a) - {"t_s"}:
        if field in circular:
            out[field] = shortest_arc(a[field], b[field], f)
        elif field in linear:
            out[field] = lerp(a[field], b[field], f)
        else:
            # Not a continuous quantity — `ecl` is the only one, and an illumination
            # state has no meaningful midpoint. It holds until the next computed sample
            # rather than being blended into a value the propagator never produced.
            out[field] = a[field]
    return out


def ground_track_segments(track, max_step_deg=170.0):
    """The ground track as polylines, split where it crosses the antimeridian.

    RS-4-02 AT THE DRAWING, which is the only place it can be. A viewer that drew one
    polyline through every sample would, at a crossing from lon 179.5 to -179.5, draw a
    line straight across the map through every longitude the spacecraft was never at.
    It reads as a glitch, so an operator learns to ignore it — and the next time the
    display is wrong about something that matters, they ignore that too.

    The split is detected as a longitude step larger than any real one: the spacecraft
    moves a few tenths of a degree per second, so a jump of more than `max_step_deg`
    is the coordinate wrapping rather than the vehicle moving. `shortest_arc` above
    answers the same question for a point BETWEEN two samples; this answers it for the
    line drawn through them.

    Returns a list of segments, each a list of samples. Latitude, altitude and
    elevation are untouched — they do not wrap, and splitting on them would be
    inventing a discontinuity.
    """
    if not track:
        return []
    segments, current = [], [track[0]]
    for previous, sample in zip(track, track[1:]):
        if abs(sample["lon_deg"] - previous["lon_deg"]) > max_step_deg:
            segments.append(current)
            current = [sample]
        else:
            current.append(sample)
    segments.append(current)
    return segments
