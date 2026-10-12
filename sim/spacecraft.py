#!/usr/bin/env python3
"""The modeled spacecraft: EPS and C&DH stepped together on one deterministic clock.

Builds to HUG-SYS-001 (1 s or finer), HUG-SYS-003 (bit-for-bit reproducible),
HUG-SYS-004 (real and accelerated time, identical results) and HUG-SYS-005 (faults by
scenario file only).

THE TICK ORDER IS A CONTRACT, NOT AN IMPLEMENTATION DETAIL.

Each tick, in this order:

  1. fault onsets at or before now are applied
  2. commands the ground sends on this tick are received and take effect
  3. the physics advances one step
  4. the housekeeping frame is generated

Step 2 before step 4 is what makes HUG-CMD-007's visibility bound true: a command
received on this tick has its counter increment AND its commanded effect in the frame
generated on this same tick - no later than the next frame, as the requirement
demands. Reordering 2 after 4 would delay every commanded effect by one frame and
make the operator's "verify by counter delta plus the affected telemetry point" read
one frame stale. The suite asserts the bound, so the order cannot drift back.

Time is `tick * dt`, an integer count times the model step. No wall clock is read
anywhere in this path, which is what makes real-time and accelerated-time execution
produce identical results (HUG-SYS-004) - pacing is the runner's business and the
model cannot observe it.
"""
from sim.cdh import Cdh
from sim.eps import Eps, EpsFaults


class Spacecraft:
    def __init__(self, eps_defs, tlm_defs, scenario):
        self.scenario = scenario
        self.dt = float(eps_defs["model"]["time_step_s"])
        self.eps = Eps(eps_defs,
                       initial_soc_pct=scenario.initial_soc_pct,
                       initial_mode=scenario.initial_mode,
                       initial_illuminated=scenario.illuminated_at(0))
        if scenario.initial_payload_on:
            # Honours the same inhibits a ground command would face: a scenario
            # cannot start the payload in a state the record forbids commanding it
            # into (HUG-CMD-002, CON-04).
            if self.eps.can_activate_payload():
                self.eps.state.payload_on = True
        self.cdh = Cdh(tlm_defs, self.eps)
        self.tick = 0
        self._halt_applied = False

    # ------------------------------------------------------------------ time

    @property
    def t_s(self):
        """Elapsed model time. Integer tick count times the step - never a clock."""
        return self.tick * self.dt

    @property
    def met_s(self):
        """Mission elapsed time, the CDH_MET telemetry point. Telemetry CONTENT, and
        never a timebase for the recorded package (replay_schema.md Sec. 2)."""
        return int(self.t_s)

    # ------------------------------------------------------------------ stepping

    def _faults_now(self):
        """Fault state assembled from the scenario alone (HUG-SYS-005)."""
        strings, stuck = set(), False
        for f in self.scenario.faults_active_at(self.t_s):
            if f["fault"] == "array_string_zero":
                strings.add(f["string"] if f["string"] is not None else 1)
            elif f["fault"] == "stuck_load":
                stuck = True
            elif f["fault"] == "hk_generation_halt":
                # Latches at onset. Applied once: a re-application every tick would
                # undo a CMD_SYS_RESET that cleared it, and PROC-003 would have no
                # recovery path at all.
                if not self._halt_applied:
                    self.cdh.halt_hk_generation()
                    self._halt_applied = True
            else:
                raise ValueError(f"unknown fault in scenario: {f['fault']!r}")
        return EpsFaults(strings_zeroed=frozenset(strings), stuck_load=stuck)

    def step(self):
        """Advance one tick. Returns the frame generated on it, or None if the
        generation-halt fault is latched."""
        faults = self._faults_now()

        for cmd in self.scenario.commands_at(self.t_s):
            self.cdh.receive(cmd["mnemonic"], cmd["args"])

        self.eps.step(self.dt, self.scenario.illuminated_at(self.t_s), faults)

        frame = self.cdh.generate_frame(self.met_s)
        self.tick = self.tick + 1
        return frame

    def run(self, duration_s=None):
        """Run to duration and return every frame actually generated.

        Frames the generation-halt fault suppressed are absent from this list rather
        than present-and-empty. The gap IS the record (replay_schema.md Sec. 5).
        """
        if duration_s is None:
            duration_s = self.scenario.duration_s
        frames = []
        while self.t_s < duration_s:
            frame = self.step()
            if frame is not None:
                frames.append(frame)
        return frames
