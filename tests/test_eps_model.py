#!/usr/bin/env python3
"""The EPS power model, and the limit-catches-its-fault properties the record claims.

HUG-EPS-001/002/005, Dictionary note 2 and ledger item 1.

Dictionary disposition ledger item 1 is a VERIFICATION OBLIGATION, not a remark:
"each limit must catch its fault case (string failure eventually crosses the SoC
yellow; stuck-on load crosses EPS_LOAD_I yellow before red)". Those two are asserted
here against the real campaign scenarios, so the campaign's detection paths are shown
to work before an operator relies on them.

Every limit is read from defs/tlm_cmd.yaml. Nothing here restates a threshold.
"""
import unittest

from harness import (bare_eps, eps_defs, frame_signature, set_soc, spacecraft,
                     tlm_defs)


def limits_of(mnemonic):
    for group in tlm_defs()["telemetry_groups"]:
        for point in group["points"]:
            if point["mnemonic"] == mnemonic:
                return point["limits"]
    raise AssertionError(f"{mnemonic} not in the dictionary")


class TestEnergyBalance(unittest.TestCase):
    """HUG-EPS-001: SoC evolves per array generation minus load consumption, with
    charge and discharge efficiency 0.95."""
    verifies = ("HUG-EPS-001", "HUG-SYS-001")

    def test_generation_above_load_charges_and_below_load_discharges(self):
        for illuminated, expect_rising in ((True, True), (False, False)):
            with self.subTest(illuminated=illuminated):
                eps = bare_eps(soc_pct=50.0, illuminated=illuminated)
                eps.state.ramp_elapsed_s = eps.ramp_s      # past the ramp
                before = eps.soc_pct
                from sim.eps import EpsFaults
                for _ in range(60):
                    eps.step(1.0, illuminated, EpsFaults())
                after = eps.soc_pct
                if expect_rising:
                    self.assertGreater(after, before, "sunlit with only the bus load "
                                                      "must charge the battery")
                else:
                    self.assertLess(after, before, "eclipse must discharge it")

    def test_efficiencies_are_the_dispositioned_values_and_are_applied(self):
        env = eps_defs()["envelope"]
        self.assertEqual(env["charge_efficiency"], 0.95)
        self.assertEqual(env["discharge_efficiency"], 0.95)
        from sim.eps import EpsFaults
        # One hour sunlit with only the bus load: net 17 - 4 = 13 W, stored at 0.95.
        eps = bare_eps(soc_pct=0.0, illuminated=True)
        eps.state.ramp_elapsed_s = eps.ramp_s
        for _ in range(3600):
            eps.step(1.0, True, EpsFaults())
        expected_wh = (17.0 - 4.0) * 0.95
        self.assertAlmostEqual(eps.state.energy_wh, expected_wh, places=6,
                               msg="charge efficiency is not applied as stated")

    def test_state_of_charge_stays_inside_zero_to_one_hundred(self):
        from sim.eps import EpsFaults
        for soc, illuminated in ((99.9, True), (0.1, False)):
            eps = bare_eps(soc_pct=soc, illuminated=illuminated)
            eps.state.ramp_elapsed_s = eps.ramp_s
            for _ in range(7200):
                eps.step(1.0, illuminated, EpsFaults())
                self.assertGreaterEqual(eps.soc_pct, 0.0)
                self.assertLessEqual(eps.soc_pct, 100.0)


class TestIllumination(unittest.TestCase):
    """HUG-EPS-002: zero in eclipse, ramping across transitions over no more than
    10 s."""
    verifies = ("HUG-EPS-002", "HUG-SYS-001")

    def test_generation_is_zero_in_eclipse(self):
        from sim.eps import EpsFaults
        eps = bare_eps(illuminated=False)
        eps.state.ramp_elapsed_s = eps.ramp_s
        eps.step(1.0, False, EpsFaults())
        self.assertEqual(eps.state.string_currents_a, (0.0, 0.0),
                         "an array in eclipse must generate nothing")

    def test_the_ramp_completes_within_the_bound_the_requirement_names(self):
        from sim.eps import EpsFaults
        bound = float(eps_defs()["model"]["eclipse_ramp_s"])
        self.assertLessEqual(bound, 10.0, "HUG-EPS-002 bounds the ramp at 10 s")
        eps = bare_eps(illuminated=False)
        eps.state.ramp_elapsed_s = eps.ramp_s
        eps.step(1.0, False, EpsFaults())
        # Transition into sunlight, then step exactly the bound.
        for _ in range(int(bound)):
            eps.step(1.0, True, EpsFaults())
        full = eps.string_peak_w / eps.bus_v
        for current in eps.state.string_currents_a:
            self.assertAlmostEqual(current, full, places=9,
                                   msg=f"generation had not reached full {bound} s "
                                       f"after the eclipse exit")

    def test_the_ramp_is_a_ramp_and_not_a_step(self):
        """The bound above is an upper limit, so a model that jumped straight to full
        would satisfy it. This asserts the ramp actually ramps."""
        from sim.eps import EpsFaults
        eps = bare_eps(illuminated=False)
        eps.state.ramp_elapsed_s = eps.ramp_s
        eps.step(1.0, False, EpsFaults())
        full = eps.string_peak_w / eps.bus_v
        eps.step(1.0, True, EpsFaults())          # first sunlit tick
        self.assertGreater(eps.state.string_currents_a[0], 0.0,
                           "the ramp had not started")
        self.assertLess(eps.state.string_currents_a[0], full,
                        "generation jumped straight to full; that is a step, not a ramp")

    def test_the_ramp_is_monotonic_and_never_overshoots(self):
        from sim.eps import EpsFaults
        eps = bare_eps(illuminated=False)
        eps.state.ramp_elapsed_s = eps.ramp_s
        eps.step(1.0, False, EpsFaults())
        full = eps.string_peak_w / eps.bus_v
        previous = 0.0
        for _ in range(int(eps.ramp_s) + 5):
            eps.step(1.0, True, EpsFaults())
            current = eps.state.string_currents_a[0]
            self.assertGreaterEqual(current, previous - 1e-12, "the ramp went backwards")
            self.assertLessEqual(current, full + 1e-12, "the ramp overshot full output")
            previous = current


class TestChargeTaper(unittest.TestCase):
    """Dictionary note 2: charge taper at full charge is the modeled design
    protection, and the EPS_BATT_V high alarm is the separate operational alarm."""
    verifies = ("HUG-EPS-001",)

    def test_a_nominally_full_battery_does_not_annunciate_voltage_high(self):
        """If a full battery tripped the voltage-high yellow, that alarm would fire
        on every good pass and FM-EPS-06's meaning — a charge-control failure — would
        be lost in the noise."""
        from sim.eps import EpsFaults
        lim = limits_of("EPS_BATT_V")
        eps = bare_eps(soc_pct=99.0, illuminated=True)
        eps.state.ramp_elapsed_s = eps.ramp_s
        for _ in range(7200):
            eps.step(1.0, True, EpsFaults())
        self.assertAlmostEqual(eps.soc_pct, 100.0, places=3)
        self.assertLess(eps.battery_voltage_v, lim["yh"],
                        f"a full battery reads {eps.battery_voltage_v:.3f} V, at or "
                        f"above the yellow-high limit {lim['yh']} V")

    def test_the_taper_prevents_overshoot_past_full(self):
        from sim.eps import EpsFaults
        eps = bare_eps(soc_pct=99.5, illuminated=True)
        eps.state.ramp_elapsed_s = eps.ramp_s
        for _ in range(3600):
            eps.step(1.0, True, EpsFaults())
            self.assertLessEqual(eps.soc_pct, 100.0)


class TestLimitsCatchTheirFaultCases(unittest.TestCase):
    """Dictionary disposition ledger item 1, asserted against the campaign scenarios."""
    verifies = ("HUG-EPS-004",)

    def test_array_string_failure_crosses_the_soc_yellow(self):
        """FM-EPS-01 / P2. 'string failure eventually crosses the SoC yellow.'"""
        soc_yl = limits_of("EPS_BATT_SOC")["yl"]
        frames = spacecraft("P2_array_string_loss").run()
        socs = [f["EPS_BATT_SOC"] for f in frames]
        self.assertGreater(socs[0], soc_yl,
                           "P2 must start above the yellow so the crossing is a "
                           "crossing and not the initial condition")
        self.assertLess(min(socs), soc_yl,
                        f"P2 never crossed the SoC yellow limit {soc_yl}%; minimum "
                        f"reached was {min(socs):.2f}%")

    def test_array_string_failure_is_visible_as_string_asymmetry(self):
        """FM-EPS-01's detection path: 'EPS_SA1_I/EPS_SA2_I asymmetry'."""
        frames = spacecraft("P2_array_string_loss").run()
        asymmetric = [f for f in frames
                      if f["EPS_SA1_I"] != f["EPS_SA2_I"]]
        self.assertGreater(len(asymmetric), 0,
                           "the failed string produced no observable asymmetry, so "
                           "FM-EPS-01's detection path would not work")
        after = asymmetric[-1]
        self.assertEqual(after["EPS_SA1_I"], 0.0, "the failed string must read zero")

    def test_stuck_load_crosses_load_current_yellow_before_red(self):
        """FM-EPS-08 / P3. 'stuck-on load crosses EPS_LOAD_I yellow before red.'"""
        lim = limits_of("EPS_LOAD_I")
        frames = spacecraft("P3_stuck_load").run()
        loads = [f["EPS_LOAD_I"] for f in frames]
        peak = max(loads)
        self.assertGreater(peak, lim["yh"],
                           f"P3 peak load current {peak:.3f} A never reached the "
                           f"yellow-high limit {lim['yh']} A")
        self.assertLess(peak, lim["rh"],
                        f"P3 peak load current {peak:.3f} A reached the red-high limit "
                        f"{lim['rh']} A; the record says yellow BEFORE red")

    def test_the_generation_halt_preserves_the_gap_and_the_truth_state(self):
        """HUG-EPS-004(c) / FM-CDH-01 / P4. No frames from onset; truth continues; the
        gap is the record (replay_schema.md Sec. 5)."""
        sc = spacecraft("P4_hk_generation_halt")
        onset = next(f["t_s"] for f in sc.scenario.faults
                     if f["fault"] == "hk_generation_halt")
        reset = next(c["t_s"] for c in sc.scenario.commands
                     if c["mnemonic"] == "CMD_SYS_RESET")
        frames = sc.run()
        mets = {f["CDH_MET"] for f in frames}
        missing = [t for t in range(onset, reset) if t not in mets]
        self.assertEqual(len(missing), reset - onset,
                         "every tick from fault onset to the reset must be absent")
        self.assertIn(reset, mets, "frame generation must resume on the reset tick")
        # Truth state kept evolving through the gap: the frame after the reset carries
        # a different SoC than the last frame before the fault.
        before = [f for f in frames if f["CDH_MET"] < onset][-1]
        after = [f for f in frames if f["CDH_MET"] >= reset][0]
        self.assertNotEqual(before["EPS_BATT_SOC"], after["EPS_BATT_SOC"],
                            "the spacecraft truth state must continue to evolve while "
                            "no frames are generated")


class TestFmEps08AsRuled(unittest.TestCase):
    """FM-EPS-08's "energy-negative trend", under owner ruling D-003 item 3.

    FM-EPS-08 states that with the stuck load the "energy-negative trend persists even
    after payload shed ... SoC declines toward SAFE".

    Measured: for that to be literally true, average sunlit generation would have to be
    below 9.81 W - 57.7% of the ratified 17 W peak - and a pure cosine average is 63.7%,
    so even that does not reach it. The alternative route needs a sunlit fraction below
    0.3767, meaning eclipse above 62% of the orbit, and this orbit gives about 30%. No
    credible orbit produces it.

    THE OWNER RULED (D-003 item 3): read "energy-negative trend" as the WORSENING DEPTH
    OF DISCHARGE, which the model does reproduce. Nothing ratified changes. The reading
    is the one CONOPS Sec. 4.3 already uses for P3 in its own words - "actual SoC
    diverges below plan ... manage depth of discharge".

    So these two tests now assert the RULED reading, not an open question: the orbit
    average rises under the flat profile (which is expected and correct), and the depth
    of discharge measurably worsens against the same pass without the fault (which is
    what the row means). If the generation profile is ever changed, the first test fails
    loudly and this ruling must be revisited rather than silently overtaken.
    """
    verifies = ("HUG-EPS-004",)

    def test_stuck_load_orbit_average_rises_under_the_flat_profile_as_ruled(self):
        self.assertEqual(eps_defs()["model"]["generation_profile"], "flat",
                         "ruling D-003 item 3 was made against the flat profile; "
                         "changing it requires revisiting the ruling")
        frames = spacecraft("P3_stuck_load").run()
        socs = [f["EPS_BATT_SOC"] for f in frames]
        self.assertGreater(
            socs[-1], socs[0],
            "P3 state of charge no longer rises. The generation profile or the sunlit "
            "fraction has changed, so ruling D-003 item 3 - which read FM-EPS-08 as the "
            "worsening depth of discharge precisely because the orbit average stays "
            "positive - must be revisited with the owner rather than overtaken.")

    def test_the_depth_of_discharge_does_worsen_with_the_stuck_load(self):
        """The part of FM-EPS-08 the model does reproduce: with the stuck load the
        battery gives up more per eclipse than it would without it."""
        with_fault = spacecraft("P3_stuck_load")
        without = spacecraft("P3_stuck_load")
        without.scenario.faults = []
        a = [f["EPS_BATT_SOC"] for f in with_fault.run()]
        b = [f["EPS_BATT_SOC"] for f in without.run()]
        self.assertLess(a[-1], b[-1],
                        "the stuck load must leave the battery worse off than the same "
                        "pass without it")


if __name__ == "__main__":
    unittest.main(verbosity=2)
