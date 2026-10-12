#!/usr/bin/env python3
"""Shared fixtures for the HUGINN simulator test suite.

Every test builds its spacecraft from the real `defs/` sources. None of them
hard-codes a dispositioned value: if a limit, threshold or floor is wrong in the
source, the test that depends on it fails rather than agreeing with the bug.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for extra in (str(REPO), str(REPO / "tools")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from functools import lru_cache  # noqa: E402

import hugdefs  # noqa: E402

from copy import deepcopy  # noqa: E402

from sim.eps import Eps  # noqa: E402
from sim.scenario import Scenario  # noqa: E402
from sim.spacecraft import Spacecraft  # noqa: E402

SCENARIO_DIR = REPO / "sim" / "scenarios"
CAMPAIGN = ["P1_nominal", "P2_array_string_loss", "P3_stuck_load",
            "P4_hk_generation_halt", "P1_nominal_orbit"]
# P1_nominal_orbit takes its eclipse from PROPAGATION of the pinned element set
# (HUG-SYS-002), so including it here puts the propagator itself under the
# bit-for-bit run-to-run assertion rather than only the EPS and C&DH models.


# The defs are parsed once. A property test that sweeps tens of thousands of states
# would otherwise spend all its time re-parsing YAML instead of exercising the model.
# Copies are handed out so no test can mutate another test's fixture.
@lru_cache(maxsize=1)
def _eps_defs_cached():
    return hugdefs._load("eps.yaml")


@lru_cache(maxsize=1)
def _tlm_defs_cached():
    return hugdefs.load_tlm_cmd()


def eps_defs():
    return deepcopy(_eps_defs_cached())


def tlm_defs():
    return deepcopy(_tlm_defs_cached())


def bare_eps(soc_pct=70.0, mode="NOMINAL", illuminated=True):
    """An Eps with no C&DH and no scenario — for properties of the power model
    alone, swept at a resolution a full Spacecraft build could not afford."""
    return Eps(_eps_defs_cached(), initial_soc_pct=soc_pct, initial_mode=mode,
               initial_illuminated=illuminated)


def scenario(name):
    return Scenario.load(SCENARIO_DIR / f"{name}.yaml")


def spacecraft(name=None, **overrides):
    """A spacecraft from a named scenario, or from a minimal synthetic one.

    `overrides` patch the synthetic scenario's data before construction, so a test
    can place the spacecraft in the exact state its property needs without a file.
    """
    if name is not None:
        sc = scenario(name)
    else:
        data = {
            "scenario_id": "synthetic",
            "seed": 1,
            "start_epoch_utc": "2026-07-29T00:00:00Z",
            "duration_s": 60,
            "initial": {"soc_pct": 70.0, "mode": "NOMINAL", "payload_on": False},
            "illumination": {"source": "schedule", "eclipse_intervals_s": []},
            "faults": [],
            "commands": [],
        }
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key].update(value)
            else:
                data[key] = value
        sc = Scenario(data)
    return Spacecraft(eps_defs(), tlm_defs(), sc)


def set_soc(sim, soc_pct):
    """Place the battery at an exact state of charge."""
    sim.eps.state.energy_wh = sim.eps.capacity_wh * (float(soc_pct) / 100.0)
    return sim


def frame_signature(frames):
    """An exact, order-preserving signature of a frame sequence.

    `repr` on a float is round-trip exact in Python 3, so this compares the actual
    bit patterns rather than a rounded rendering — which is what "bit-for-bit"
    (HUG-SYS-003) has to mean to be worth asserting.
    """
    return tuple(tuple((k, repr(v)) for k, v in f.items()) for f in frames)
