// VÉ viewer limit table.
//
// GENERATED FILE - DO NOT EDIT. Source: defs/tlm_cmd.yaml
// Dictionary version: 0.5
// Source sha256: 5e1c2750ef9e0d5463f8b2fcb27abeb1dbde63c1b749717ed170cc2bacd60679
//
// HUG-UI-005: limit values and alarm colorings derive from the dictionary at
// build time; the viewer defines no limits of its own. A threshold typed into
// the renderer would be a second source of truth for a number an operator makes
// decisions against.
//
// A null side is an ABSENT limit (ruling D-001), and the renderer draws no band
// there. It is not a missing value to be filled in with something convenient.

// Assigned to `window` deliberately. A top-level `const` in a classic script
// lives in script scope and never becomes a window property, so the renderer
// read `window.VE_LIMITS` as undefined and threw on the first threshold
// lookup -- the orbit drew, the trends did not, and every readout stayed at
// `--`. Nothing in the Python checks could see it; only running the page did.
window.VE_LIMITS = {
  "adm_eclipse": {
    "decimals": null,
    "kind": "none",
    "units": "n/a",
    "values": [
      "SUNLIT",
      "ECLIPSE"
    ]
  },
  "cdh_cmd_acc_cnt": {
    "decimals": null,
    "kind": "none",
    "units": "n/a"
  },
  "cdh_cmd_rej_cnt": {
    "decimals": null,
    "kind": "delta",
    "severity": "yellow",
    "units": "n/a"
  },
  "cdh_frame_cnt": {
    "decimals": null,
    "kind": "staleness",
    "red_s": 30,
    "units": "n/a",
    "yellow_s": 10
  },
  "cdh_met": {
    "decimals": null,
    "kind": "none",
    "units": "s"
  },
  "cdh_rej_reason": {
    "decimals": null,
    "kind": "none",
    "units": "n/a",
    "values": [
      "NONE",
      "UNKNOWN_OPCODE",
      "ARG_RANGE",
      "MODE_INHIBIT"
    ]
  },
  "eps_batt_i": {
    "decimals": 1,
    "kind": "thresholds",
    "rh": 2.5,
    "rl": -2.5,
    "units": "A",
    "yh": 2.0,
    "yl": -2.0
  },
  "eps_batt_soc": {
    "decimals": 0,
    "kind": "thresholds",
    "rh": null,
    "rl": 20,
    "units": "%",
    "yh": null,
    "yl": 35
  },
  "eps_batt_v": {
    "decimals": 1,
    "kind": "thresholds",
    "rh": 8.5,
    "rl": 6.8,
    "units": "V",
    "yh": 8.3,
    "yl": 7.2
  },
  "eps_bus_v": {
    "decimals": 2,
    "kind": "thresholds",
    "rh": 5.25,
    "rl": 4.75,
    "units": "V",
    "yh": 5.1,
    "yl": 4.9
  },
  "eps_load_i": {
    "decimals": 1,
    "kind": "thresholds",
    "rh": 2.0,
    "rl": null,
    "units": "A",
    "yh": 1.5,
    "yl": null
  },
  "eps_mode": {
    "annunciates": [
      "SAFE"
    ],
    "decimals": null,
    "kind": "state",
    "units": "n/a",
    "values": [
      "NOMINAL",
      "LOW_POWER",
      "SAFE"
    ]
  },
  "eps_sa1_i": {
    "decimals": null,
    "kind": "unalarmed",
    "units": "A"
  },
  "eps_sa2_i": {
    "decimals": null,
    "kind": "unalarmed",
    "units": "A"
  },
  "pld_rate": {
    "decimals": null,
    "kind": "range",
    "max": 10,
    "min": 0.1,
    "units": "Hz"
  },
  "pld_state": {
    "decimals": null,
    "kind": "none",
    "units": "n/a",
    "values": [
      "OFF",
      "ON"
    ]
  }
};

