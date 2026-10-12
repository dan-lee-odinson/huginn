#!/usr/bin/env python3
"""Build the VÉ viewer page for one replay package.

    python -m ve.viewer.build replay/pass-001.json

The output is a single self-contained HTML file: no backend, no network, no external
asset (HUG-UI-006). Open it from a local file or serve it as a static object; there is
nothing else to run.

THIS IS THE ONLY PATH TO A RENDERED PAGE, AND THAT IS RS-2-04.
The rule says the viewer refuses -- never best-effort renders -- a package with an unknown
schema version, an unmatchable dict_ref, or any violation of the contract. The way that is
made true here is structural rather than diligent: conformance runs BEFORE a byte of page
is written, and the emitted page has no fetch, no file input and no import, so it cannot
acquire a different package later. There is no code path from an unchecked package to a
display.

That is also why the viewer is built in Python rather than shipped as a JavaScript
application that loads packages. A JS viewer would need the contract implemented again in
JS -- the private copy HUG-UI-003 forbids -- and the two would drift, each staying green
against its own reading. One implementation, and the page is its output.

WHAT THE BUILDER DECIDES AND WHAT THE PAGE DECIDES.
Every rule the schema governs is settled here, in Python, against the same modules the
recorder uses: shortest-arc and antimeridian splitting (RS-4-02) via `ve.interpolate`,
event text through the text-only sink via `ve.render`. What ships to the browser is
drawing code that holds no rules and no thresholds.
"""
import argparse
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
import hugdefs                                                    # noqa: E402
from ve import conformance, interpolate, render                 # noqa: E402

VIEWER_DIR = Path(__file__).resolve().parent
OUT_DIR = REPO / "viewer"


class ViewerRefusal(RuntimeError):
    """The viewer declined to render, with the reason and the rule."""


def ground_times(meta, end_s):
    """`epoch_utc + t_s` for every whole second, precomputed (RS-2-05).

    Computed here so the page never does date arithmetic: a browser formatting an
    instant applies the reader's timezone, and two operators comparing the same pass
    would read different clocks off the same package.
    """
    epoch = datetime.strptime(meta["epoch_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc)
    return [(epoch + timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%SZ")
            for i in range(int(end_s) + 1)]


def event_rows(events):
    """Event rows as HTML, with every package string through the text-only sink.

    Rendered HERE rather than in the browser so the Python sink -- the one with the
    malicious-markup test against it -- is in the real render path and not merely
    available. The page's JavaScript then only decides which rows are in the past, and
    constructs no package string at all.
    """
    rows = []
    for e in events:
        text = render.to_html_text(e["text"])
        sev = render.to_html_text(e["sev"])
        detail = ""
        if "cmd" in e:
            cmd = e["cmd"]
            detail = (f' <span class="t">{render.to_html_text(cmd["mnemonic"])} '
                      f'{render.to_html_text(cmd["result"])}'
                      + (f' ({render.to_html_text(cmd["reason"])})'
                         if cmd["reason"] != "NONE" else "")
                      + "</span>")
        rows.append(
            f'<div class="event" data-sev="{sev}" data-event-t="{float(e["t_s"])}" '
            f'data-past="no"><span class="t">{float(e["t_s"]):.0f} s</span>'
            f'{text}{detail}</div>')
    if not rows:
        # An honest empty state. "No events" is a fact about the pass; a blank panel is
        # ambiguous between that and a panel that failed to render.
        rows.append('<div class="event" data-event-t="0" data-past="yes">'
                    '<span class="t">--</span>no events recorded in this pass</div>')
    return "\n".join(rows)


def power_flow_svg():
    """The EPS power-flow diagram. Static geometry; the renderer sets arrow widths."""
    return """<svg id="power-svg" viewBox="0 0 720 200">
  <rect class="node" x="20" y="30" width="120" height="46" rx="4"/>
  <text class="node-label" x="80" y="58">ARRAY STRING 1</text>
  <rect class="node" x="20" y="124" width="120" height="46" rx="4"/>
  <text class="node-label" x="80" y="152">ARRAY STRING 2</text>
  <rect class="node" x="300" y="77" width="120" height="46" rx="4"/>
  <text class="node-label" x="360" y="105">BUS</text>
  <rect class="node" x="580" y="30" width="120" height="46" rx="4"/>
  <text class="node-label" x="640" y="58">LOAD</text>
  <rect class="node" x="580" y="124" width="120" height="46" rx="4"/>
  <text class="node-label" x="640" y="152">BATTERY</text>
  <line id="flow-sa1" class="flow flow-in" x1="140" y1="53" x2="300" y2="92"/>
  <line id="flow-sa2" class="flow flow-in" x1="140" y1="147" x2="300" y2="108"/>
  <line id="flow-load" class="flow flow-in" x1="420" y1="92" x2="580" y2="53"/>
  <line id="flow-batt" class="flow flow-in" x1="420" y1="108" x2="580" y2="147"/>
  <text class="flow-label" x="200" y="60">SA1</text>
  <text class="flow-label" x="200" y="152">SA2</text>
  <text class="flow-label" x="480" y="60">LOAD</text>
  <text class="flow-label" x="480" y="152">BATT</text>
</svg>"""


def annunciator_rows():
    """One row per annunciated point. The mnemonics come from the generated limit
    table, so a point that gains a limit in the dictionary appears here without an
    edit and a point that loses one disappears."""
    # Asked of the GENERATOR, not scraped out of the JavaScript it emits. The first
    # version split the file on the literal `const VE_LIMITS = ` and broke the moment
    # that declaration changed -- a second reader of the same fact, which is the shape
    # this repository keeps removing. One producer, and callers ask it.
    import gen_ve_viewer
    limits = gen_ve_viewer.limit_table(hugdefs.load_tlm_cmd())
    rows = []
    for mnemonic in sorted(limits):
        spec = limits[mnemonic]
        if spec["kind"] not in ("thresholds", "state"):
            continue
        rows.append(
            f'<div class="readout" data-annunciator="{mnemonic}" data-state="none">'
            f'<span class="label">{mnemonic.upper()}</span>'
            f'<span class="value">--</span></div>')
    rows.append('<div class="readout" id="annunciator-staleness" data-state="none">'
                '<span class="label">FRAME STALENESS</span>'
                '<span class="value">--</span></div>')
    return "\n".join(rows)


def build_page(package, pass_id):
    """The self-contained page for a package that has already been checked."""
    meta = package["meta"]
    segments = interpolate.ground_track_segments(package["track"])
    data = {
        "meta": meta,
        "track": package["track"],
        "trackSegments": segments,
        "frames": package["frames"],
        "groundTime": ground_times(meta, meta["end_s"]),
    }
    limits_js = (VIEWER_DIR / "limits.js").read_text(encoding="utf-8")
    ve_js = (VIEWER_DIR / "ve.js").read_text(encoding="utf-8")
    ve_css = (VIEWER_DIR / "ve.css").read_text(encoding="utf-8")

    # `</script` cannot appear inside an inline script, whatever it is escaped as in
    # JSON. Splitting it is the standard, boring fix and it keeps the data a single
    # JSON literal rather than something the page has to parse specially.
    payload = json.dumps(data, ensure_ascii=True, allow_nan=False).replace(
        "</", "<\\/")

    esc = html.escape
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>VÉ — {esc(pass_id)}</title>
<style>
{ve_css}
</style>
</head>
<body>
<h1>VÉ — pass {esc(pass_id)}</h1>
<div class="banner">
  <strong>Display only.</strong> This page renders a recorded replay package. It has no
  command path, no live-data path, and no connection to the simulator or the ground
  system. Scenario <strong>{esc(str(meta['scenario']))}</strong> ·
  terminal <strong>{esc(str(meta['gs']))}</strong> ·
  epoch <strong>{esc(str(meta['epoch_utc']))}</strong> ·
  dictionary <strong>{esc(str(meta['dict_ref']['version']))}</strong>
  ({esc(str(meta['dict_ref']['sha256'])[:12])}…) ·
  schema <strong>{esc(str(meta['schema']))}</strong> ·
  orbit <strong>{esc(str(meta['orbit_ref']))}</strong>
</div>

<div class="grid">
  <div>
    <div class="panel">
      <h2>Orbit — ground track, eclipse, contact window</h2>
      <svg id="orbit-svg" viewBox="0 0 720 360"></svg>
      <div class="controls">
        <button id="play">Play</button>
        <input type="range" id="scrubber">
        <span class="clock">T+<strong id="clock-t">--</strong> ·
          <strong id="clock-utc">--</strong></span>
      </div>
    </div>

    <div class="panel">
      <h2>EPS power flow</h2>
      {power_flow_svg()}
    </div>

    <div class="panel">
      <h2>Battery state of charge — with limit bands from the dictionary</h2>
      <svg id="trend-soc" viewBox="0 0 720 150"></svg>
      <h2 style="margin-top:12px">Battery voltage — with limit bands</h2>
      <svg id="trend-volt" viewBox="0 0 720 150"></svg>
    </div>
  </div>

  <div>
    <div class="panel">
      <h2>Position</h2>
      <div class="readout"><span class="label">Latitude</span>
        <span class="value" id="pos-lat">--</span></div>
      <div class="readout"><span class="label">Longitude</span>
        <span class="value" id="pos-lon">--</span></div>
      <div class="readout"><span class="label">Altitude</span>
        <span class="value" id="pos-alt">--</span></div>
      <div class="readout"><span class="label">Elevation</span>
        <span class="value" id="pos-el">--</span></div>
      <div class="readout"><span class="label">Illumination</span>
        <span class="value" id="pos-ecl">--</span></div>
      <div class="readout"><span class="label">Contact</span>
        <span class="value" id="pos-contact">--</span></div>
    </div>

    <div class="panel">
      <h2>Annunciators</h2>
      {annunciator_rows()}
    </div>

    <div class="panel">
      <h2>Events — commands accepted and rejected</h2>
      <div class="events">
{event_rows(package['events'])}
      </div>
    </div>
  </div>
</div>

<script>
{limits_js}
window.VE_PACKAGE = {payload};
</script>
<script>
{ve_js}
</script>
</body>
</html>
"""


def build(package_path, out_dir=None):
    """Check, then render. Raises ViewerRefusal if the package is not one."""
    package_path = Path(package_path)
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ViewerRefusal(f"{package_path} could not be read as JSON: {exc}")

    # RS-2-04, and it happens here rather than anywhere later. Nothing below this line
    # runs for a package that failed, so there is no partial render, no "best effort",
    # and no page to mistake for a good one.
    problem = conformance.refuse(package, filename_stem=package_path.stem,
                                 path=package_path)
    if problem:
        raise ViewerRefusal(
            f"the viewer will not render {package_path.name}.\n{problem}")

    out_dir = Path(out_dir or OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{package_path.stem}.html"
    target.write_bytes(build_page(package, package_path.stem).encode("utf-8"))
    return target


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("package")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # pragma: no cover
        pass
    try:
        target = build(args.package, args.out_dir)
    except ViewerRefusal as exc:
        print(f"REFUSED: {exc}")
        return 1
    size = target.stat().st_size
    print(f"wrote {target} ({size // 1024} KiB, self-contained: no backend, no network)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
