#!/usr/bin/env python3
"""HUGINN electrical power subsystem model.

Builds to HUG-EPS-001..005 and the mode-authority rule of Dictionary Sec. 2. Every
dispositioned value comes from defs/eps.yaml; nothing is hard-coded here.

What an operator sees this produce, and why the record requires it:

  Energy balance (HUG-EPS-001). Two array strings generate; the bus load and, when
  on, the payload consume. The difference charges or discharges the battery at 0.95
  efficiency each way. State of charge is that running total - the number the
  operator's standing question is about ("does actual SoC track the plan?",
  CONOPS Sec. 4.1).

  Illumination (HUG-EPS-002). Generation is zero in eclipse and ramps across the
  boundary over no more than 10 s. Eclipse every orbit is what makes the
  charge/discharge cycle the mission's operational rhythm.

  The mode ladder (HUG-EPS-003). Below 30% SoC the spacecraft protects itself by
  entering LOW_POWER; below 20%, SAFE. Each entry sheds the payload. It only ever
  moves DOWN on its own - toward safety. Coming back up is a deliberate ground act
  (CMD_MODE_SET, HUG-CMD-006), because a spacecraft that can promote itself can
  promote itself into a brownout.

Arithmetic is restricted to +, -, * and / on floats: those are IEEE-754 exact and
reproduce bit-for-bit across runs (HUG-SYS-003), and across machines too. No
transcendental function is called anywhere in this module under either generation
profile - the cosine profile's 2/pi is an exact double literal, not a library
division - so the maths library never enters the EPS path at all.
"""
from dataclasses import dataclass

# 2/pi, as an exact double literal rather than a `math.pi` division.
#
# The cosine generation profile needs this single constant and nothing else from the
# maths library. Writing it as a literal keeps `math` out of the EPS path entirely, so
# even the non-default profile stays byte-identical across machines - and the one
# module-level `math` exemption in the determinism scan stays genuinely confined to
# sim/orbit.py, where trigonometry is unavoidable.
TWO_OVER_PI = 0.6366197723675814


def _interp(curve, x):
    """Piecewise-linear interpolation over an ascending (x, y) anchor list.

    Multiplication and division only - no library call whose result could differ
    between platforms or releases.
    """
    if x <= curve[0][0]:
        return curve[0][1]
    if x >= curve[-1][0]:
        return curve[-1][1]
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if x0 <= x <= x1:
            span = x1 - x0
            if span == 0:
                return y1
            return y0 + (y1 - y0) * ((x - x0) / span)
    return curve[-1][1]


@dataclass
class EpsFaults:
    """Fault state, set only from a scenario file (HUG-SYS-005, HUG-EPS-004)."""
    strings_zeroed: frozenset = frozenset()   # 1-based string indices forced to zero
    stuck_load: bool = False


@dataclass
class EpsState:
    energy_wh: float
    mode: str
    payload_on: bool
    pld_rate_hz: float
    illuminated: bool
    # Seconds since the last illumination change, capped at the ramp length. Drives
    # the HUG-EPS-002 ramp; capped so it cannot grow without bound over a long run.
    ramp_elapsed_s: float = 0.0
    # Derived, refreshed every step so a frame never reports a stale intermediate.
    string_currents_a: tuple = ()
    load_current_a: float = 0.0
    battery_current_a: float = 0.0

    @property
    def soc_pct(self):
        raise NotImplementedError  # set by Eps; SoC needs capacity


class Eps:
    """The EPS model. One instance per simulated spacecraft."""

    def __init__(self, defs, initial_soc_pct, initial_mode="NOMINAL",
                 initial_illuminated=True):
        env = defs["envelope"]
        ladder = defs["mode_ladder"]
        model = defs["model"]

        self.capacity_wh = float(env["battery_capacity_wh"])
        self.bus_v = float(env["bus_voltage_v"])
        self.string_count = int(env["array_string_count"])
        self.string_peak_w = float(env["array_string_peak_w"])
        self.bus_load_w = float(env["bus_load_w"])
        self.payload_load_w = float(env["payload_load_w"])
        self.eta_charge = float(env["charge_efficiency"])
        self.eta_discharge = float(env["discharge_efficiency"])

        self.order = list(ladder["order"])
        self.entry = dict(ladder["autonomous_entry_soc_pct"])
        self.floors = dict(ladder["recovery_floor_soc_pct"])
        self.payload_inhibit_soc = float(ladder["payload_activation_inhibit_soc_pct"])
        self.sheds_on_entry = bool(ladder["sheds_payload_on_autonomous_entry"])

        self.stuck_load_w = float(defs["faults"]["stuck_load"]["power_w"])

        self.ramp_s = float(model["eclipse_ramp_s"])
        self.profile = model["generation_profile"]
        self.ocv = [(float(a), float(b)) for a, b in model["ocv_curve_soc_pct_to_v"]]
        self.r_internal = float(model["internal_resistance_ohm"])
        self.taper_start = float(model["charge_taper_start_soc_pct"])

        self.state = EpsState(
            energy_wh=self.capacity_wh * (float(initial_soc_pct) / 100.0),
            mode=initial_mode,
            payload_on=False,
            pld_rate_hz=float(model["initial_pld_rate_hz"]),
            illuminated=bool(initial_illuminated),
            ramp_elapsed_s=self.ramp_s,
        )
        # Derived values are populated before the first step so a frame can never
        # report an uninitialised string current.
        self._refresh_derived(0.0, 0.0, tuple(0.0 for _ in range(self.string_count)))

    # ------------------------------------------------------------------ queries

    @property
    def soc_pct(self):
        return self.state.energy_wh / self.capacity_wh * 100.0

    @property
    def battery_voltage_v(self):
        """Terminal voltage. With internal_resistance_ohm at 0 this is the
        open-circuit voltage, which is what CONOPS Sec. 4.4 describes when it calls
        the low-voltage alarm a presentation of the low-battery condition."""
        ocv = _interp(self.ocv, self.soc_pct)
        if self.r_internal == 0.0:
            return ocv
        return ocv + self.state.battery_current_a * self.r_internal

    def depth_index(self, mode):
        """Position in the ladder; larger is deeper (safer)."""
        return self.order.index(mode)

    # ------------------------------------------------------------ ground actions

    def shed_payload(self):
        self.state.payload_on = False

    def can_activate_payload(self):
        """HUG-CMD-002 / CON-04: inhibited in SAFE or below the activation floor."""
        return self.state.mode != "SAFE" and self.soc_pct >= self.payload_inhibit_soc

    def command_mode(self, target):
        """Ground-commanded mode change (CMD_MODE_SET, HUG-CMD-006).

        Returns True if accepted. The floor check is the caller's contract to
        report; this refuses rather than silently clamping, because a mode change
        that half-happened is worse than one that did not.
        """
        if target not in self.floors:
            return False
        if self.soc_pct < self.floors[target]:
            return False
        going_down = self.depth_index(target) > self.depth_index(self.state.mode)
        self.state.mode = target
        # Dictionary Sec. 2: a commanded transition to LOW_POWER sheds the payload;
        # a transition to NOMINAL does NOT re-enable it (re-activation is
        # CMD_PLD_SET_STATE's job, subject to its own inhibits).
        if going_down and self.sheds_on_entry:
            self.shed_payload()
        return True

    def enter_safe(self):
        """CMD_SAFE_ENTER: always accepted onboard (HUG-CMD-004)."""
        self.state.mode = "SAFE"
        self.shed_payload()

    # -------------------------------------------------------------------- step

    def step(self, dt, illuminated, faults):
        """Advance one time step. Returns nothing; read state through the queries."""
        st = self.state

        if bool(illuminated) != st.illuminated:
            st.illuminated = bool(illuminated)
            st.ramp_elapsed_s = 0.0
        # The transition step advances the ramp too. Skipping it (an `elif` here)
        # spread a 10 s ramp over 11 steps, which exceeds the bound HUG-EPS-002
        # actually names - "no more than 10 s". Full output is now reached on the
        # tenth step after the boundary, exactly at the bound.
        if st.ramp_elapsed_s < self.ramp_s:
            st.ramp_elapsed_s = st.ramp_elapsed_s + dt
            if st.ramp_elapsed_s > self.ramp_s:
                st.ramp_elapsed_s = self.ramp_s

        p_gen, string_powers = self._generation(faults)
        p_load = self._load(faults)
        p_net = p_gen - p_load

        # Charge taper at full (Dictionary note 2) - the modeled design protection.
        if p_net > 0.0:
            p_net = p_net * self._taper_factor()

        hours = dt / 3600.0
        if p_net >= 0.0:
            self.state.energy_wh = st.energy_wh + p_net * hours * self.eta_charge
        else:
            self.state.energy_wh = st.energy_wh + p_net * hours / self.eta_discharge

        if st.energy_wh > self.capacity_wh:
            st.energy_wh = self.capacity_wh
        elif st.energy_wh < 0.0:
            st.energy_wh = 0.0

        self._refresh_derived(p_net, p_load, string_powers)
        self._apply_ladder()

    # ---------------------------------------------------------------- internals

    def _ramp_factor(self):
        """HUG-EPS-002: zero in eclipse, ramping across the boundary over no more
        than eclipse_ramp_s."""
        if self.ramp_s <= 0.0:
            return 1.0 if self.state.illuminated else 0.0
        frac = self.state.ramp_elapsed_s / self.ramp_s
        if frac > 1.0:
            frac = 1.0
        return frac if self.state.illuminated else 1.0 - frac

    def _generation(self, faults):
        factor = self._ramp_factor()
        if self.profile == "flat":
            per_string = self.string_peak_w * factor
        elif self.profile == "cosine":
            # Selectable but not the default; see defs/eps.yaml generation_profile.
            # The mean of cos over a half-cycle, as an exact literal - no library call,
            # so choosing this profile costs no reproducibility.
            per_string = self.string_peak_w * factor * TWO_OVER_PI
        else:
            raise ValueError(f"unknown generation_profile: {self.profile!r}")
        powers = []
        for index in range(1, self.string_count + 1):
            powers.append(0.0 if index in faults.strings_zeroed else per_string)
        total = 0.0
        for p in powers:
            total = total + p
        return total, tuple(powers)

    def _load(self, faults):
        p = self.bus_load_w
        if self.state.payload_on:
            p = p + self.payload_load_w
        if faults.stuck_load:
            p = p + self.stuck_load_w
        return p

    def _taper_factor(self):
        soc = self.soc_pct
        if soc <= self.taper_start:
            return 1.0
        span = 100.0 - self.taper_start
        if span <= 0.0:
            return 0.0
        remaining = (100.0 - soc) / span
        return remaining if remaining > 0.0 else 0.0

    def _refresh_derived(self, p_net, p_load, string_powers=None):
        st = self.state
        if string_powers is not None:
            st.string_currents_a = tuple(p / self.bus_v for p in string_powers)
        st.load_current_a = p_load / self.bus_v
        v = _interp(self.ocv, self.soc_pct)
        # Battery current at battery voltage, signed + charge / - discharge per the
        # dictionary. Guard against a zero-voltage divide at an empty pack.
        st.battery_current_a = (p_net / v) if v != 0.0 else 0.0

    def _apply_ladder(self):
        """HUG-EPS-003, downward only.

        The autonomous ladder may only ever move the spacecraft DEEPER. It compares
        depth and refuses to promote, so no arithmetic accident can turn this into an
        autonomous recovery path - the property the test suite asserts over the whole
        SoC domain rather than at sampled points.
        """
        soc = self.soc_pct
        target = None
        if soc < self.entry["SAFE"]:
            target = "SAFE"
        elif soc < self.entry["LOW_POWER"]:
            target = "LOW_POWER"
        if target is None:
            return
        if self.depth_index(target) <= self.depth_index(self.state.mode):
            return                      # would be a promotion, or no change
        self.state.mode = target
        if self.sheds_on_entry:
            self.shed_payload()
