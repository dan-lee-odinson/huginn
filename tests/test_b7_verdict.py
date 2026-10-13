#!/usr/bin/env python3
"""B7's verdict, driven from stored bytes with no ground system (D-019 selection 4).

B7 is the hazardous-command two-step. Its manifest says PASS, and until now that was the
only thing that did: no executed case re-derived the result from what the demonstration
archived. `b7_verdict` does, and these cases hold it to both polarities.

EVERY RED CASE IS A WAY A BLOCKED UPLINK PASSES FOR A GATE. A disconnected interface
refuses every command, so a refusal on its own proves nothing; a resend that was never
the confirmation proves nothing; a control that went out with the check switched off
proves nothing. Each case below is one of those, one edit away from the real archive.

The GREEN baseline is the archived evidence of `attempt-001`, read off disk.
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from demonstrate import b7_verdict                                   # noqa: E402

ART = REPO / "verification" / "evidence" / "B7-hazardous-two-step" / "attempt-001" / "artifacts"
FILES = ("step-one-refusal.json", "step-two-acceptance.json", "non-hazardous-control.json",
         "effect.txt", "cmd.txt")


def archived(name):
    return (ART / name).read_text(encoding="utf-8")


def inputs(**over):
    base = {"refusal_text": archived("step-one-refusal.json"),
            "acceptance_text": archived("step-two-acceptance.json"),
            "control_text": archived("non-hazardous-control.json"),
            "effect_text": archived("effect.txt"),
            "cmd_txt": archived("cmd.txt")}
    base.update(over)
    return base


def edited_json(name, edit):
    doc = json.loads(archived(name))
    edit(doc)
    return json.dumps(doc)


class TestTheArchivedEvidencePasses(unittest.TestCase):
    """GREEN, off disk. If this fails every red case below is meaningless."""
    verifies = ("HUG-CMD-001",)
    polarity = "green"

    def test_the_committed_b7_evidence_satisfies_the_verdict(self):
        ok, reasons = b7_verdict(**inputs())
        self.assertTrue(ok, f"the archived B7 evidence does not verify: {reasons}")

    def test_the_verdict_is_computable_from_the_archive_alone(self):
        for name in FILES:
            with self.subTest(artifact=name):
                self.assertTrue((ART / name).is_file())


class TestARefusalThatIsNotTheGate(unittest.TestCase):
    """RED: step one refused, but not as the hazardous gate refuses."""
    verifies = ("HUG-CMD-001",)
    polarity = "red"

    def assertFails(self, **over):
        ok, reasons = b7_verdict(**inputs(**over))
        self.assertFalse(ok)
        return reasons

    def test_refused_for_another_reason(self):
        def edit(d):
            d["data"]["class"] = "DisabledError"
        self.assertFails(refusal_text=edited_json("step-one-refusal.json", edit))

    def test_refused_with_a_reason_the_definition_does_not_carry(self):
        def edit(d):
            d["data"]["instance_variables"]["@hazardous_description"] = "Confirm"
        self.assertFails(refusal_text=edited_json("step-one-refusal.json", edit))

    def test_the_refused_command_is_not_hazardous(self):
        def edit(d):
            d["data"]["instance_variables"]["@cmd_name"] = "CMD_PLD_SET_RATE"
        reasons = self.assertFails(refusal_text=edited_json("step-one-refusal.json", edit))
        self.assertTrue(any("is not HAZARDOUS" in r for r in reasons), reasons)

    def test_the_definition_no_longer_marks_it_hazardous(self):
        cmd = archived("cmd.txt").replace(
            'COMMAND HUGINN CMD_SAFE_ENTER BIG_ENDIAN "EPS_MODE → SAFE; payload shed"\n'
            '  HAZARDOUS "Two-step confirmation required (Dictionary Sec. 2; B7, FM-CDH-04)"\n',
            'COMMAND HUGINN CMD_SAFE_ENTER BIG_ENDIAN "EPS_MODE → SAFE; payload shed"\n')
        self.assertNotEqual(cmd, archived("cmd.txt"), "the edit did not apply")
        reasons = self.assertFails(cmd_txt=cmd)
        self.assertTrue(any("is not HAZARDOUS" in r for r in reasons), reasons)

    def test_a_malformed_refusal_is_a_reason_not_a_crash(self):
        reasons = self.assertFails(refusal_text="{not json")
        self.assertTrue(any("not readable JSON" in r for r in reasons), reasons)


class TestAResendThatIsNotTheConfirmation(unittest.TestCase):
    """RED: step two accepted, but not as the confirmed resend of step one."""
    verifies = ("HUG-CMD-001",)
    polarity = "red"

    def test_the_resend_went_out_with_the_check_on(self):
        def edit(d):
            d["result"]["hazardous_check"] = "true"
        ok, _ = b7_verdict(**inputs(
            acceptance_text=edited_json("step-two-acceptance.json", edit)))
        self.assertFalse(ok)

    def test_the_resend_is_a_different_command(self):
        def edit(d):
            d["result"]["cmd_name"] = "CMD_SYS_RESET"
        ok, _ = b7_verdict(**inputs(
            acceptance_text=edited_json("step-two-acceptance.json", edit)))
        self.assertFalse(ok)

    def test_the_resend_was_refused_too(self):
        def edit(d):
            d["error"] = {"class": "HazardousError"}
        ok, _ = b7_verdict(**inputs(
            acceptance_text=edited_json("step-two-acceptance.json", edit)))
        self.assertFalse(ok)


class TestAControlThatShowsNothing(unittest.TestCase):
    """RED: the control that tells a selective gate from a dead uplink, broken."""
    verifies = ("HUG-CMD-001",)
    polarity = "red"

    def test_the_control_was_refused(self):
        def edit(d):
            d["error"] = {"class": "DisabledError"}
        ok, _ = b7_verdict(**inputs(
            control_text=edited_json("non-hazardous-control.json", edit)))
        self.assertFalse(ok)

    def test_the_control_is_itself_hazardous(self):
        def edit(d):
            d["result"]["cmd_name"] = "CMD_MODE_SET"
        ok, _ = b7_verdict(**inputs(
            control_text=edited_json("non-hazardous-control.json", edit)))
        self.assertFalse(ok)

    def test_the_control_went_out_with_the_check_off(self):
        def edit(d):
            d["result"]["hazardous_check"] = "false"
        ok, _ = b7_verdict(**inputs(
            control_text=edited_json("non-hazardous-control.json", edit)))
        self.assertFalse(ok)


class TestAnEffectThatIsNotATransition(unittest.TestCase):
    """RED: the mode and the link do not show what the gate did."""
    verifies = ("HUG-CMD-001",)
    polarity = "red"

    def effect(self, old, new):
        text = archived("effect.txt")
        self.assertIn(old, text)
        return text.replace(old, new)

    def test_the_refused_command_changed_the_mode(self):
        ok, _ = b7_verdict(**inputs(effect_text=self.effect(
            "EPS_MODE after step one: NOMINAL", "EPS_MODE after step one: SAFE")))
        self.assertFalse(ok)

    def test_the_mode_was_already_safe(self):
        ok, _ = b7_verdict(**inputs(effect_text=self.effect(
            "EPS_MODE before        : NOMINAL", "EPS_MODE before        : SAFE").replace(
            "EPS_MODE after step one: NOMINAL", "EPS_MODE after step one: SAFE")))
        self.assertFalse(ok)

    def test_the_refused_command_reached_the_link(self):
        ok, reasons = b7_verdict(**inputs(effect_text=self.effect(
            "interface after        : CONNECTED txcnt=3",
            "interface after        : CONNECTED txcnt=4")))
        self.assertFalse(ok)
        self.assertTrue(any("transmitted 3" in r for r in reasons), reasons)

    def test_the_interface_ended_disconnected(self):
        ok, _ = b7_verdict(**inputs(effect_text=self.effect(
            "interface after        : CONNECTED", "interface after        : DISCONNECTED")))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
