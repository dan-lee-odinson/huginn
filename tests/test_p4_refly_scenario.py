#!/usr/bin/env python3
"""The PASS-4 re-fly scenario (owner ruling D-021, OF-028).

On the first flight of PASS-4 two things kept the record from showing that the
operator's reset happened. The command counters read ACC 1, REJ 0 before the halt, which
is also the reset's epoch, so the epoch could not tell a reset from no reset. And the
scenario's own reset at MET 1320 restored telemetry before the operator's did.

D-021 puts the re-fly on a copy of the scenario, `P4_hk_generation_halt_refly`, with one
more command accepted before the halt and no scripted reset. The original stays as it
was flown. Two properties follow, and each is held to both polarities here: the reset
epoch differs from the counters before the halt, and nothing but an operator reset
brings telemetry back. The first flight's scenario fails both, which is OF-028.
"""
import copy
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))
import hugdefs                                                       # noqa: E402
from sim.scenario import Scenario                                    # noqa: E402
from sim.spacecraft import Spacecraft                                # noqa: E402

SCENARIOS = REPO / "sim" / "scenarios"
FLOWN = "P4_hk_generation_halt"
REFLY = "P4_hk_generation_halt_refly"
HALT_T = 1200
#: An operator's reset, sent between the halt and the first flight's scripted reset.
OPERATOR_RESET = {"t_s": 1260, "mnemonic": "CMD_SYS_RESET", "args": {}}
RESET_EPOCH = (1, 0)


def load(name):
    return yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text(encoding="utf-8"))


def run(data, operator=()):
    data = copy.deepcopy(data)
    data["commands"] = list(data.get("commands", [])) + [dict(c) for c in operator]
    sim = Spacecraft(hugdefs.load_eps(), hugdefs.load_tlm_cmd(), Scenario(data))
    return sim.run()


def counters(frame):
    return frame["CDH_CMD_ACC_CNT"], frame["CDH_CMD_REJ_CNT"]


def epoch_shows_reset(data):
    """None if the counters before the halt differ from a reset's epoch, else why not.

    That the first frame after a reset reads the epoch is held directly, below.
    """
    frames = run(data, [OPERATOR_RESET])
    before = [f for f in frames if f["CDH_MET"] < HALT_T]
    after = [f for f in frames if f["CDH_MET"] >= HALT_T]
    if not before or not after:
        return "no frame before the halt, or none after the reset"
    if counters(before[-1]) == RESET_EPOCH:
        return (f"the counters read ACC {RESET_EPOCH[0]}, REJ {RESET_EPOCH[1]} before the "
                f"halt as well, so the reset epoch cannot tell a reset from no reset")
    return None


def only_an_operator_reset_restores(data):
    """None if no frame follows the halt until an operator sends CMD_SYS_RESET."""
    after = [f for f in run(data) if f["CDH_MET"] >= HALT_T]
    if after:
        return (f"telemetry returns at MET {after[0]['CDH_MET']} with no operator command: "
                f"the scenario recovers on its own")
    return None


class TestTheReflyScenario(unittest.TestCase):
    """GREEN: the re-fly scenario has both properties, and is the flown one otherwise."""
    verifies = ("HUG-EPS-004", "HUG-CMD-005")
    polarity = "green"

    def test_it_differs_from_the_flown_scenario_in_two_places_only(self):
        flown, refly = load(FLOWN), load(REFLY)
        for key in ("scenario_id", "description", "commands"):
            flown.pop(key)
        commands = refly.pop("commands")
        refly.pop("scenario_id")
        refly.pop("description")
        self.assertEqual(refly, flown)
        expected = [c for c in load(FLOWN)["commands"] if c["mnemonic"] != "CMD_SYS_RESET"]
        expected.append({"t_s": 600, "mnemonic": "CMD_PLD_SET_RATE", "args": {"rate": 2.0}})
        self.assertEqual(sorted(commands, key=lambda c: c["t_s"]),
                         sorted(expected, key=lambda c: c["t_s"]))

    def test_the_reset_epoch_differs_from_the_counters_before_the_halt(self):
        self.assertIsNone(epoch_shows_reset(load(REFLY)))
        before = [f for f in run(load(REFLY)) if f["CDH_MET"] < HALT_T]
        self.assertEqual(counters(before[-1]), (2, 0))

    def test_only_an_operator_reset_restores_telemetry(self):
        self.assertIsNone(only_an_operator_reset_restores(load(REFLY)))

    def test_an_operator_reset_restores_telemetry_at_the_epoch(self):
        after = [f for f in run(load(REFLY), [OPERATOR_RESET]) if f["CDH_MET"] >= HALT_T]
        self.assertEqual(after[0]["CDH_MET"], OPERATOR_RESET["t_s"])
        self.assertEqual(counters(after[0]), RESET_EPOCH)


class TestTheFirstFlightsScenarioFailsBoth(unittest.TestCase):
    """RED: each property refuses the scenario that lacks it."""
    verifies = ("HUG-EPS-004", "HUG-CMD-005")
    polarity = "red"

    def test_the_flown_scenario_epoch_shows_nothing(self):
        finding = epoch_shows_reset(load(FLOWN))
        self.assertIsNotNone(finding)
        self.assertIn("cannot tell a reset from no reset", finding)

    def test_the_flown_scenario_recovers_on_its_own(self):
        finding = only_an_operator_reset_restores(load(FLOWN))
        self.assertIsNotNone(finding)
        self.assertIn("MET 1320", finding)

    def test_the_refly_without_its_extra_command(self):
        data = load(REFLY)
        data["commands"] = [c for c in data["commands"] if c["mnemonic"] != "CMD_PLD_SET_RATE"]
        self.assertIsNotNone(epoch_shows_reset(data))

    def test_the_refly_with_a_late_scripted_reset(self):
        data = load(REFLY)
        data["commands"].append({"t_s": 1800, "mnemonic": "CMD_SYS_RESET", "args": {}})
        finding = only_an_operator_reset_restores(data)
        self.assertIsNotNone(finding)
        self.assertIn("MET 1800", finding)


if __name__ == "__main__":
    unittest.main()
