// VÉ viewer renderer.
//
// THIS FILE HOLDS NO RULES. Every threshold comes from VE_LIMITS, generated from
// defs/tlm_cmd.yaml (HUG-UI-005). Every geometry decision that the replay schema governs
// -- shortest-arc interpolation, antimeridian splitting -- was made by the Python builder
// before this file ever saw the data, because those are contract rules and the contract
// has one implementation. What is left here is drawing.
//
// PACKAGE-DERIVED STRINGS ARE NEVER ASSIGNED TO innerHTML. Numbers are formatted and set
// with textContent; event text is rendered server-side through the Python sink and is
// already inert by the time this file runs. Two sinks, and neither is the reason the
// other may be relaxed (HUG-UI-007).
//
// NO NETWORK, NO STORAGE, NO INPUT. There is no fetch, no XMLHttpRequest, no file input
// and no import: the only package this page can render is the one the builder embedded
// after checking it (RS-2-04). A page that could load another package could load an
// unchecked one.

"use strict";

(function () {
  const P = window.VE_PACKAGE;
  const L = window.VE_LIMITS;

  // ---------------------------------------------------------------- small helpers

  const $ = (id) => document.getElementById(id);

  function fmt(mnemonic, value) {
    // Decimal places come from the dictionary. A display that invented a precision
    // would be claiming the instrument resolves more than it does.
    const spec = L[mnemonic] || {};
    const dp = spec.decimals;
    if (value === null || value === undefined) return "--";
    return typeof dp === "number" ? Number(value).toFixed(dp) : String(value);
  }

  function severity(mnemonic, value) {
    // GREEN / YELLOW / RED from the dictionary's thresholds. A null side is an ABSENT
    // limit (D-001): there is no band there and no value can violate it.
    const s = L[mnemonic];
    if (!s || s.kind !== "thresholds" || value === null || value === undefined) {
      return "none";
    }
    if (s.rl !== null && s.rl !== undefined && value <= s.rl) return "red";
    if (s.rh !== null && s.rh !== undefined && value >= s.rh) return "red";
    if (s.yl !== null && s.yl !== undefined && value <= s.yl) return "yellow";
    if (s.yh !== null && s.yh !== undefined && value >= s.yh) return "yellow";
    return "green";
  }

  // The frame in effect at a given pass time: the most recent one AT OR BEFORE it.
  // Never the nearest, and never interpolated -- a frame is a measurement that was
  // received, and inventing one between two of them would be the fabrication RS-5-01
  // forbids the recorder. Before the first frame there is nothing, and the readouts
  // say so rather than showing the first frame early.
  function frameAt(t) {
    let lo = 0, hi = P.frames.length - 1, found = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (P.frames[mid].t_s <= t) { found = mid; lo = mid + 1; } else { hi = mid - 1; }
    }
    return found < 0 ? null : P.frames[found];
  }

  function trackAt(t) {
    let lo = 0, hi = P.track.length - 1, found = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (P.track[mid].t_s <= t) { found = mid; lo = mid + 1; } else { hi = mid - 1; }
    }
    return P.track[found];
  }

  // ------------------------------------------------------------------- orbit view

  const MAP_W = 720, MAP_H = 360;
  const lonX = (lon) => (lon + 180) * (MAP_W / 360);
  const latY = (lat) => (90 - lat) * (MAP_H / 180);

  // Runs of constant illumination within one segment. Eclipse is drawn ON the track
  // rather than as a shade over the map: the spacecraft is in eclipse, not a region of
  // the Earth, and a rectangle across the map would say the wrong thing about where.
  function illuminationRuns(segment) {
    const runs = [];
    let current = null;
    segment.forEach((s) => {
      if (!current || current.ecl !== s.ecl) {
        if (current) {
          // Carry one sample across so consecutive runs join rather than showing a
          // gap at every terminator crossing.
          current.samples.push(s);
          runs.push(current);
        }
        current = { ecl: s.ecl, samples: [s] };
      } else {
        current.samples.push(s);
      }
    });
    if (current) runs.push(current);
    return runs;
  }

  function polyline(svg, samples, cls) {
    if (samples.length < 2) return;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("class", cls);
    line.setAttribute("points",
      samples.map((s) => `${lonX(s.lon_deg).toFixed(1)},${latY(s.lat_deg).toFixed(1)}`)
             .join(" "));
    svg.appendChild(line);
    return line;
  }

  function drawOrbit() {
    const svg = $("orbit-svg");

    // Graticule first, so everything else draws over it. Without it a ground track is
    // a squiggle on black with no way to read a longitude off the panel.
    for (let lon = -180; lon <= 180; lon += 30) {
      const l = document.createElementNS("http://www.w3.org/2000/svg", "line");
      l.setAttribute("class", "graticule");
      l.setAttribute("x1", lonX(lon)); l.setAttribute("x2", lonX(lon));
      l.setAttribute("y1", 0); l.setAttribute("y2", MAP_H);
      svg.appendChild(l);
    }
    for (let lat = -60; lat <= 60; lat += 30) {
      const l = document.createElementNS("http://www.w3.org/2000/svg", "line");
      l.setAttribute("class", lat === 0 ? "graticule equator" : "graticule");
      l.setAttribute("x1", 0); l.setAttribute("x2", MAP_W);
      l.setAttribute("y1", latY(lat)); l.setAttribute("y2", latY(lat));
      svg.appendChild(l);
    }

    // The ground track, split at the antimeridian by the builder (RS-4-02) and then
    // by illumination here. `ecl` is ground-computed from the propagated orbit and is
    // present for every sample whether or not telemetry arrived (RS-4-01).
    P.trackSegments.forEach((seg) => {
      illuminationRuns(seg).forEach((run) => {
        polyline(svg, run.samples,
                 run.ecl ? "ground-track eclipse" : "ground-track sunlit");
      });
    });

    // The contact window: the part of the track above the horizon, drawn over the rest.
    const inContact = P.track.filter(
      (s) => s.t_s >= P.meta.aos_s && s.t_s <= P.meta.los_s);
    polyline(svg, inContact, "contact-window");

    // The ground terminal, at the point of highest elevation -- the only place in the
    // package where the station's position is implied rather than stated.
    let best = P.track[0];
    P.track.forEach((s) => { if (s.el_deg > best.el_deg) best = s; });
    const gs = document.createElementNS("http://www.w3.org/2000/svg", "path");
    gs.setAttribute("class", "ground-station");
    gs.setAttribute("d", `M ${lonX(best.lon_deg).toFixed(1)} ` +
      `${(latY(best.lat_deg) - 6).toFixed(1)} l 5 9 l -10 0 z`);
    svg.appendChild(gs);

    const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    marker.setAttribute("id", "sc-marker");
    marker.setAttribute("r", 5);
    marker.setAttribute("class", "spacecraft");
    svg.appendChild(marker);
  }

  // -------------------------------------------------------------- power flow view

  // Arrow width scales with current magnitude. The scale is derived from the largest
  // magnitude the package actually contains, so a pass never renders off the panel and
  // never renders as a flat line -- both of which would make the animation decorative.
  let powerScale = 1;
  function preparePower() {
    let peak = 0;
    P.frames.forEach((f) => {
      ["eps_sa1_i", "eps_sa2_i", "eps_load_i", "eps_batt_i"].forEach((k) => {
        peak = Math.max(peak, Math.abs(f[k] || 0));
      });
    });
    powerScale = peak > 0 ? 14 / peak : 1;
  }

  function updatePower(f) {
    const set = (id, amps) => {
      const el = $(id);
      if (!el) return;
      const w = Math.max(1, Math.abs(amps || 0) * powerScale);
      el.setAttribute("stroke-width", w.toFixed(2));
      // Charge and discharge are opposite directions, and the arrow says which.
      el.setAttribute("class", "flow " + ((amps || 0) >= 0 ? "flow-in" : "flow-out"));
    };
    if (!f) return;
    set("flow-sa1", f.eps_sa1_i);
    set("flow-sa2", f.eps_sa2_i);
    set("flow-load", f.eps_load_i);
    set("flow-batt", f.eps_batt_i);
  }

  // ------------------------------------------------------------------ trend plots

  const TREND_W = 720, TREND_H = 150;

  function drawTrend(svgId, mnemonic) {
    const svg = $(svgId);
    const spec = L[mnemonic] || {};
    const values = P.frames.map((f) => f[mnemonic]).filter((v) => typeof v === "number");
    if (!values.length) return;

    // The vertical range must contain every limit that EXISTS, so a band is never drawn
    // off the panel where an operator cannot see the value approach it.
    const candidates = values.slice();
    ["rl", "yl", "yh", "rh"].forEach((k) => {
      if (spec[k] !== null && spec[k] !== undefined) candidates.push(spec[k]);
    });
    let lo = Math.min.apply(null, candidates), hi = Math.max.apply(null, candidates);
    const pad = (hi - lo) * 0.08 || 1;
    lo -= pad; hi += pad;

    const x = (t) => (t - P.meta.aos_s * 0) * (TREND_W / Math.max(1, P.meta.end_s));
    const y = (v) => TREND_H - ((v - lo) / (hi - lo)) * TREND_H;

    // Limit bands. An ABSENT side draws NOTHING -- not a band at the edge of the panel,
    // which would read as a limit that exists (D-001).
    const band = (from, to, cls) => {
      if (from === null || from === undefined || to === null || to === undefined) return;
      const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      r.setAttribute("x", 0);
      r.setAttribute("width", TREND_W);
      r.setAttribute("y", Math.min(y(from), y(to)).toFixed(1));
      r.setAttribute("height", Math.abs(y(from) - y(to)).toFixed(1));
      r.setAttribute("class", cls);
      svg.appendChild(r);
    };
    // Eclipse spans, drawn behind the limit bands. A battery discharging is only
    // legible next to WHY it is discharging, and the answer is almost always here.
    let run = null;
    P.track.forEach((s, i) => {
      if (s.ecl && run === null) run = s.t_s;
      const last = i === P.track.length - 1;
      if (run !== null && (!s.ecl || last)) {
        const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        r.setAttribute("x", x(run).toFixed(1));
        r.setAttribute("width", Math.max(1, x(s.t_s) - x(run)).toFixed(1));
        r.setAttribute("y", 0);
        r.setAttribute("height", TREND_H);
        r.setAttribute("class", "eclipse-span");
        svg.appendChild(r);
        run = null;
      }
    });

    band(lo, spec.rl, "band-red");
    band(spec.rl, spec.yl, "band-yellow");
    band(spec.yh, spec.rh, "band-yellow");
    band(spec.rh, hi, "band-red");

    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("class", "trend-line");
    line.setAttribute("points", P.frames
      .filter((f) => typeof f[mnemonic] === "number")
      .map((f) => `${x(f.t_s).toFixed(1)},${y(f[mnemonic]).toFixed(1)}`).join(" "));
    svg.appendChild(line);

    const cursor = document.createElementNS("http://www.w3.org/2000/svg", "line");
    cursor.setAttribute("class", "cursor");
    cursor.setAttribute("y1", 0);
    cursor.setAttribute("y2", TREND_H);
    cursor.setAttribute("id", svgId + "-cursor");
    svg.appendChild(cursor);
  }

  function moveCursors(t) {
    ["trend-soc", "trend-volt"].forEach((id) => {
      const c = $(id + "-cursor");
      if (!c) return;
      const x = t * (TREND_W / Math.max(1, P.meta.end_s));
      c.setAttribute("x1", x.toFixed(1));
      c.setAttribute("x2", x.toFixed(1));
    });
  }

  // ----------------------------------------------------------------- annunciators

  function updateAnnunciators(f, t) {
    const rows = document.querySelectorAll("[data-annunciator]");
    rows.forEach((row) => {
      const mnemonic = row.getAttribute("data-annunciator");
      const valueEl = row.querySelector(".value");
      const spec = L[mnemonic] || {};
      if (!f) {
        valueEl.textContent = "--";
        row.setAttribute("data-state", "none");
        return;
      }
      const v = f[mnemonic];
      valueEl.textContent = fmt(mnemonic, v) +
        (spec.units && spec.units !== "n/a" ? " " + spec.units : "");
      let state = severity(mnemonic, v);
      // A state point annunciates on the values the dictionary names, not on a
      // threshold. EPS_MODE = SAFE is the one this mission cares about.
      if (spec.kind === "state") {
        state = (spec.annunciates || []).indexOf(v) >= 0 ? "red" : "green";
      }
      row.setAttribute("data-state", state);
    });

    // Staleness is a GROUND-side derived monitor, not an onboard limit: a halted
    // counter cannot alarm itself. Here it is computed from the gap between the frame
    // in effect and the cursor, using the dictionary's own thresholds.
    const stale = $("annunciator-staleness");
    if (stale) {
      const spec = L["cdh_frame_cnt"] || {};
      const gap = f ? t - f.t_s : null;
      const el = stale.querySelector(".value");
      if (gap === null) {
        el.textContent = "no frame";
        stale.setAttribute("data-state", "none");
      } else {
        el.textContent = gap.toFixed(0) + " s";
        stale.setAttribute("data-state",
          gap >= spec.red_s ? "red" : gap >= spec.yellow_s ? "yellow" : "green");
      }
    }
  }

  // ----------------------------------------------------------------------- events

  // Event rows are rendered by the BUILDER through the Python text-only sink, and are
  // already in the document. This only decides which are in the past at time t, so no
  // package string is constructed here at all.
  function updateEvents(t) {
    document.querySelectorAll("[data-event-t]").forEach((row) => {
      const et = parseFloat(row.getAttribute("data-event-t"));
      row.setAttribute("data-past", et <= t ? "yes" : "no");
    });
  }

  // ------------------------------------------------------------------- the scrubber

  function show(t) {
    const f = frameAt(t);
    const s = trackAt(t);

    $("clock-t").textContent = t.toFixed(0) + " s";
    // Ground time is epoch + t_s: the package's own anchor (RS-2-05). Formatted from
    // the epoch string rather than the viewer's clock, so the display reads the same
    // in every timezone it is opened in.
    $("clock-utc").textContent = P.groundTime[Math.min(Math.round(t), P.groundTime.length - 1)] || "--";

    const marker = $("sc-marker");
    if (marker && s) {
      marker.setAttribute("cx", lonX(s.lon_deg).toFixed(1));
      marker.setAttribute("cy", latY(s.lat_deg).toFixed(1));
    }
    $("pos-lat").textContent = s ? s.lat_deg.toFixed(2) + " deg" : "--";
    $("pos-lon").textContent = s ? s.lon_deg.toFixed(2) + " deg" : "--";
    $("pos-alt").textContent = s ? s.alt_km.toFixed(1) + " km" : "--";
    $("pos-el").textContent = s ? s.el_deg.toFixed(1) + " deg" : "--";
    $("pos-ecl").textContent = s ? (s.ecl ? "ECLIPSE" : "SUNLIT") : "--";
    $("pos-contact").textContent =
      (t >= P.meta.aos_s && t <= P.meta.los_s) ? "IN CONTACT" : "no contact";

    updatePower(f);
    updateAnnunciators(f, t);
    updateEvents(t);
    moveCursors(t);
  }

  function init() {
    preparePower();
    drawOrbit();
    drawTrend("trend-soc", "eps_batt_soc");
    drawTrend("trend-volt", "eps_batt_v");

    const slider = $("scrubber");
    slider.min = 0;
    slider.max = P.meta.end_s;
    slider.step = P.meta.cadence_s;
    slider.value = P.meta.aos_s;
    slider.addEventListener("input", () => show(parseFloat(slider.value)));

    let timer = null;
    $("play").addEventListener("click", () => {
      if (timer) { clearInterval(timer); timer = null; $("play").textContent = "Play"; return; }
      $("play").textContent = "Pause";
      timer = setInterval(() => {
        const next = parseFloat(slider.value) + P.meta.cadence_s;
        if (next > P.meta.end_s) { clearInterval(timer); timer = null; $("play").textContent = "Play"; return; }
        slider.value = next;
        show(next);
      }, 50);
    });

    show(parseFloat(slider.value));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
