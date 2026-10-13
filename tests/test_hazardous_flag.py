#!/usr/bin/env python3
"""The hazardous flag reaches the generated ground definitions (D-019 selection 4).

`defs/tlm_cmd.yaml` marks three commands hazardous, and the ground system's two-step
confirmation applies to exactly the commands the generated `cmd.txt` carries a HAZARDOUS
line under. G1 already proves the committed `cmd.txt` is what the generator produces.
It does not prove the generator reads the flag: a generator that hard-coded the three
names would round-trip just as cleanly, and would keep marking them after the dictionary
changed. These cases close that gap, at both polarities.
"""
import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import gen_openc3_config                                             # noqa: E402
import hugdefs                                                       # noqa: E402
from demonstrate import hazardous_commands                           # noqa: E402

CMD_TXT = (REPO / "gnd" / "openc3" / "plugins" / "openc3-cosmos-huginn" / "targets"
           / "HUGINN" / "cmd_tlm" / "cmd.txt")


def flags(tlm):
    return {c["mnemonic"]: bool(c["hazardous"]) for c in tlm["commands"]}


def mismatches(cmd_txt, tlm):
    """Every command whose HAZARDOUS marking in `cmd_txt` disagrees with the dictionary."""
    generated, wanted = hazardous_commands(cmd_txt), flags(tlm)
    return sorted(set(generated) ^ set(wanted)) + sorted(
        m for m in set(generated) & set(wanted) if generated[m] != wanted[m])


def build(tlm):
    version, digest = gen_openc3_config.source_digest()
    return "\n".join(gen_openc3_config.build_cmd(tlm, version, digest))


class TestTheGeneratedDefinitionsCarryTheFlag(unittest.TestCase):
    """GREEN: the committed cmd.txt marks exactly the commands the dictionary flags."""
    verifies = ("HUG-GND-001",)
    polarity = "green"

    def test_the_committed_cmd_txt_matches_the_dictionary(self):
        tlm = hugdefs.load_tlm_cmd()
        self.assertEqual(mismatches(CMD_TXT.read_text(encoding="utf-8"), tlm), [])
        self.assertEqual(sorted(m for m, h in flags(tlm).items() if h),
                         ["CMD_MODE_SET", "CMD_SAFE_ENTER", "CMD_SYS_RESET"])

    def test_the_generator_follows_every_flag_it_is_given(self):
        """Flip each command's flag in memory and regenerate: the marking follows."""
        base = hugdefs.load_tlm_cmd()
        for i, cmd in enumerate(base["commands"]):
            tlm = copy.deepcopy(base)
            tlm["commands"][i]["hazardous"] = not cmd["hazardous"]
            with self.subTest(command=cmd["mnemonic"]):
                self.assertEqual(mismatches(build(tlm), tlm), [])


class TestAFlagThatDidNotReachTheGround(unittest.TestCase):
    """RED: a definition that disagrees with the dictionary is caught."""
    verifies = ("HUG-GND-001",)
    polarity = "red"

    def test_a_hazardous_command_with_its_line_removed(self):
        text = CMD_TXT.read_text(encoding="utf-8")
        lines = text.splitlines()
        reset = next(i for i, l in enumerate(lines) if " CMD_SYS_RESET " in l)
        self.assertIn("HAZARDOUS", lines[reset + 1])
        del lines[reset + 1]
        self.assertEqual(mismatches("\n".join(lines), hugdefs.load_tlm_cmd()),
                         ["CMD_SYS_RESET"])

    def test_a_non_hazardous_command_marked_hazardous(self):
        lines = CMD_TXT.read_text(encoding="utf-8").splitlines()
        rate = next(i for i, l in enumerate(lines) if " CMD_PLD_SET_RATE " in l)
        lines.insert(rate + 1, '  HAZARDOUS "planted"')
        self.assertEqual(mismatches("\n".join(lines), hugdefs.load_tlm_cmd()),
                         ["CMD_PLD_SET_RATE"])

    def test_the_dictionary_changed_and_the_definitions_did_not(self):
        tlm = hugdefs.load_tlm_cmd()
        for cmd in tlm["commands"]:
            if cmd["mnemonic"] == "CMD_MODE_SET":
                cmd["hazardous"] = False
        self.assertEqual(mismatches(CMD_TXT.read_text(encoding="utf-8"), tlm),
                         ["CMD_MODE_SET"])


if __name__ == "__main__":
    unittest.main()
