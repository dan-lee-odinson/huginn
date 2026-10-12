#!/usr/bin/env python3
"""Scenario files: the only way a fault enters the simulation.

HUG-SYS-005: "Fault injections shall be defined entirely in scenario files;
injecting a fault shall require no source-code change." HUG-SYS-003: "For a given
scenario file (seed, fault schedule, start epoch), simulation results shall be
bit-for-bit reproducible across runs."

Those two together are why this module exists as a boundary rather than a
convenience. A fault the simulator can produce that a scenario file cannot name
would be a fault the campaign could not reproduce, and a campaign whose passes are
its evidence cannot afford one.

DETERMINISM IS STRUCTURAL HERE, NOT A HABIT.

  Nothing in a scenario path reads a wall clock. Time is an integer tick count times
  the model step; `start_epoch_utc` is a label carried into the record, never a
  value the model computes from. A model that asked the operating system what time
  it was would produce a different run every time it ran, and the campaign's
  reproducibility claim would be false while every test still passed.

  Randomness, if a scenario ever needs any, comes from `Scenario.rng` - a generator
  seeded from the file's own `seed`. The module-level `random` functions share a
  process-global generator seeded from entropy, so a single call to one of them
  anywhere in a scenario path destroys reproducibility silently. The suite forbids
  both by static scan and by runtime trap.

ILLUMINATION has two sources, and both are deliberate.

  `source: orbit` derives eclipse state from the pinned surrogate reference element set
  by propagation, which is what HUG-SYS-002 requires and what a campaign pass uses.

  `source: schedule` states the eclipse intervals explicitly in the file. Kept, not
  legacy: it places an eclipse boundary on an exact tick so the HUG-EPS-002 ramp can be
  tested at the boundary, which an orbit-derived schedule cannot do as cleanly, and it
  keeps every EPS and C&DH test free of trigonometry so those paths stay byte-equal
  across machines as well as across runs.
"""
import random
from pathlib import Path

import yaml


class Scenario:
    def __init__(self, data, path=None):
        self.path = Path(path) if path else None
        self.data = data

        self.scenario_id = data["scenario_id"]
        self.description = data.get("description", "")
        self.seed = int(data["seed"])
        self.start_epoch_utc = data["start_epoch_utc"]
        self.duration_s = int(data["duration_s"])

        initial = data.get("initial", {})
        self.initial_soc_pct = float(initial.get("soc_pct", 70.0))
        self.initial_mode = initial.get("mode", "NOMINAL")
        self.initial_payload_on = bool(initial.get("payload_on", False))

        illum = data.get("illumination", {"source": "schedule",
                                          "eclipse_intervals_s": []})
        self.illumination_source = illum.get("source", "schedule")
        self.eclipse_intervals_s = [(int(a), int(b))
                                    for a, b in illum.get("eclipse_intervals_s", [])]

        self.faults = sorted(
            ({"t_s": int(f["t_s"]), "fault": f["fault"],
              "string": int(f["string"]) if "string" in f else None}
             for f in data.get("faults", [])),
            key=lambda f: (f["t_s"], f["fault"], f["string"] or 0))

        self.commands = sorted(
            ({"t_s": int(c["t_s"]), "mnemonic": c["mnemonic"],
              "args": dict(c.get("args", {}))}
             for c in data.get("commands", [])),
            key=lambda c: (c["t_s"], c["mnemonic"]))

        # The one permitted source of randomness, seeded from the file. Created
        # eagerly so a scenario cannot silently fall back to the process-global
        # generator by finding this absent.
        self.rng = random.Random(self.seed)

        # Where the pinned element set lives, for `illumination.source: orbit`.
        self.orbit_dir = Path(__file__).resolve().parent.parent / "defs" / "orbit"
        self._orbit_cache = None

    @classmethod
    def load(cls, path):
        path = Path(path)
        with path.open(encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh), path)

    def illuminated_at(self, t_s):
        """True when the spacecraft is sunlit at t_s.

        Half-open intervals [start, end): a boundary tick belongs to exactly one
        side, so an eclipse entry and the sunlit tick before it are never both true
        and never both false.
        """
        if self.illumination_source == "orbit":
            return self._orbit().illuminated_at(t_s)
        if self.illumination_source != "schedule":
            raise ValueError(
                f"unknown illumination.source {self.illumination_source!r}; expected "
                f"'orbit' (propagated from the pinned element set, HUG-SYS-002) or "
                f"'schedule' (explicit intervals in the file)")
        for start, end in self.eclipse_intervals_s:
            if start <= t_s < end:
                return False
        return True

    def _orbit(self):
        """The pinned orbit, built once per scenario.

        Imported here rather than at module scope so a schedule-driven scenario - which
        every EPS and C&DH test uses - never pulls the trigonometric propagation path
        into its process at all.
        """
        if self._orbit_cache is None:
            from sim.orbit import Orbit
            self._orbit_cache = Orbit(self.orbit_dir, self.start_epoch_utc)
        return self._orbit_cache

    def faults_active_at(self, t_s):
        """Fault onsets at or before t_s. Faults latch on: the record defines onset,
        and only CMD_SYS_RESET clears the generation halt (HUG-EPS-004(c))."""
        return [f for f in self.faults if f["t_s"] <= t_s]

    def commands_at(self, t_s):
        """Commands the ground sends on this exact tick, in file order."""
        return [c for c in self.commands if c["t_s"] == t_s]
