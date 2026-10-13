#!/usr/bin/env python3
"""FM-EPS-06, charge taper at full battery, demonstrated to fail (D-019 selection 4).

Dictionary note 2 makes the charge taper the modeled design protection against
overcharge, and FM-EPS-06's disposition defers its verification to HUG-G002. The two
existing taper cases (`test_eps_model.TestChargeTaper`) are green only, and one of them
cannot fail on the taper at all: with the taper removed, the energy clamp alone still
holds state of charge at or below 100 %, so "the taper prevents overshoot past full"
passes either way.

What the taper does that nothing else does is stop charge current at full. So the
property below asks for that: hold a nearly full battery in sunlight until it is full,
and require the charge current to have tapered to zero, never rising on the way.
Recorded alongside these cases: `OF-034` — with the taper removed the battery still reads
8.2 V, below the voltage-high alarm FM-EPS-06 names as its detection.

Same harness as `test_model_red_cases`: one predicate, two polarities, and a red case
counts only on DETECTED, never on an exception.
"""
import sys
import unittest
from pathlib import Path

# Runnable on its own as well as under discovery: the shared harness lives beside it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import bare_eps, eps_defs                               # noqa: E402
from sim.eps import Eps, EpsFaults                                   # noqa: E402
from test_model_red_cases import DETECTED, SILENT, probe            # noqa: E402

#: Long enough to fill from 99 % on the real model with margin: the band is 1 % of
#: 38 Wh, charged at about 1.6 A and tapering to zero across it.
HOLD_S = 7200


def charge_tapers_at_full(eps):
    """FM-EPS-06 / dictionary note 2: at full charge, charge current tapers to zero."""
    eps.state.ramp_elapsed_s = eps.ramp_s
    currents = []
    for _ in range(HOLD_S):
        eps.step(1.0, True, EpsFaults())
        currents.append(eps.state.battery_current_a)
    if eps.soc_pct < 99.999:
        return f"held sunlit for {HOLD_S} s and the battery reached only {eps.soc_pct:.4f} %"
    rising = [i for i in range(1, len(currents)) if currents[i] > currents[i - 1] + 1e-12]
    if rising:
        return f"charge current rose inside the taper band at step {rising[0]}"
    if currents[-1] > 1e-6:
        return (f"full battery still taking {currents[-1]:.4f} A of charge current: the "
                f"taper did not act, which is FM-EPS-06's failure mode")
    return None


class _NoTaper(Eps):
    """FM-EPS-06's failure mode: charge control does not taper at full."""

    def _taper_factor(self):
        return 1.0


class _TaperThatStopsHalfway(Eps):
    """A taper that acts but never reaches zero."""

    def _taper_factor(self):
        return max(super()._taper_factor(), 0.5)


def _near_full(cls=None):
    if cls is None:
        return bare_eps(soc_pct=99.0, illuminated=True)
    return cls(eps_defs(), initial_soc_pct=99.0, initial_mode="NOMINAL",
               initial_illuminated=True)


class TestTheTaperHoldsOnTheRealModel(unittest.TestCase):
    """GREEN. If the predicate speaks here, the red cases below are meaningless."""
    verifies = ("HUG-EPS-001",)
    polarity = "green"

    def test_the_real_model_tapers_to_zero_at_full(self):
        self.assertEqual(probe(charge_tapers_at_full, _near_full()), (SILENT, None))


class TestAFailedTaperIsCaught(unittest.TestCase):
    """RED: the charge taper broken two ways, each DETECTED by the same predicate."""
    verifies = ("HUG-EPS-001",)
    polarity = "red"

    def test_no_taper_at_all(self):
        outcome, finding = probe(charge_tapers_at_full, _near_full(_NoTaper))
        self.assertEqual(outcome, DETECTED, finding)
        self.assertIn("FM-EPS-06", finding)

    def test_a_taper_that_stops_halfway(self):
        outcome, finding = probe(charge_tapers_at_full, _near_full(_TaperThatStopsHalfway))
        self.assertEqual(outcome, DETECTED, finding)


if __name__ == "__main__":
    unittest.main()
