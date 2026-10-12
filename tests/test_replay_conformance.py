#!/usr/bin/env python3
"""The replay-package contract, driven at both polarities (B11, HUG-VER-002).

`defs/replay_schema.yaml` declares 32 conformance rules. This suite builds a conforming
package and then breaks it, once per rule, asserting that the checker names THAT rule.

WHY ONE RED CASE PER RULE, AND WHY IT NAMES THE RULE. A suite that asserted only "the
package was refused" would pass while a checker refused everything for one reason — the
rules would be untested individually and a broken one would hide behind a working
neighbour. RS-7-20 requires a refusal to name what failed, so the tests assert on the
name; that makes each rule falsifiable on its own and makes the refusal useful to an
operator at the same time.

THE FIXTURE IS DERIVED FROM THE DICTIONARY. A hand-written package with the frame members
spelled out would go stale the first time a telemetry point was added, and the suite would
keep passing against a contract it no longer matched.
"""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
import hugdefs                                                    # noqa: E402
from ve import conformance                                      # noqa: E402


def _points():
    return [p for g in hugdefs.load_tlm_cmd()["telemetry_groups"] for p in g["points"]]


def _frame_member(point):
    """A dictionary-native value for one telemetry point."""
    kind = point["type"]
    if kind == "enum":
        return point["enum_values"][0]
    if "CNT" in point["mnemonic"]:
        return 1
    if point["mnemonic"] == "EPS_BATT_SOC":
        return 75.0
    if point["mnemonic"] == "PLD_RATE":
        return 1.0
    if kind.startswith("uint"):
        return 1
    return 1.0


def conforming_package(pass_id="pass-001", end_s=4.0, cadence_s=1.0):
    """A minimal package that satisfies every rule. The suite's green baseline."""
    members = {p["mnemonic"].lower(): _frame_member(p) for p in _points()}
    track = [{"t_s": i * cadence_s, "lat_deg": 10.0 + i, "lon_deg": 20.0 + i,
              "alt_km": 500.0, "az_deg": 100.0 + i, "el_deg": 30.0 + i,
              "ecl": bool(i % 2)}
             for i in range(math.floor(end_s / cadence_s) + 1)]
    frames = [{"t_s": i * cadence_s, **copy.deepcopy(members)}
              for i in range(int(end_s) + 1)]
    events = [
        {"t_s": 1.0, "text": "payload activated", "sev": "info",
         "cmd": {"mnemonic": "CMD_PLD_SET_STATE", "result": "accepted",
                 "reason": "NONE"}},
        {"t_s": 2.0, "text": "command rejected", "sev": "warn",
         "cmd": {"mnemonic": "CMD_SAFE_ENTER", "result": "rejected",
                 "reason": "MODE_INHIBIT"}},
        {"t_s": 3.0, "text": "eclipse entry", "sev": "info"},
    ]
    meta = {
        "pass_id": pass_id, "scenario": "P1_nominal_orbit", "gs": "GS-RAVENSROOST",
        "epoch_utc": "2026-07-29T00:00:00Z", "cadence_s": cadence_s,
        "aos_s": 1.0, "los_s": 3.0, "end_s": end_s,
        "eclipse_entry_s": None, "eclipse_exit_s": None,
        "orbit_ref": "CELTEE 1", "dict_ref": {"version": "0.5", "sha256": "0" * 64},
        "schema": str(hugdefs.load_replay_schema()["schema"]),
    }
    return {"meta": meta, "track": track, "frames": frames, "events": events}


def refused_rules(package, **kw):
    """The set of rule ids the checker names for this package."""
    kw.setdefault("filename_stem", package["meta"].get("pass_id"))
    kw.setdefault("path", Path("replay") / f"{kw['filename_stem']}.json")
    _ok, violations = conformance.check(package, **kw)
    return {v.rule for v in violations}


class TestTheBaselineConforms(unittest.TestCase):
    """GREEN. If this fails every red case below is meaningless."""
    verifies = ("HUG-UI-002",)
    polarity = "green"

    def test_the_conforming_package_is_accepted(self):
        ok, violations = conformance.check(
            conforming_package(), filename_stem="pass-001",
            path=Path("replay/pass-001.json"))
        self.assertTrue(ok, "\n".join(str(v) for v in violations))

    def test_a_recorded_package_conforms(self):
        """The real recorder's output, not just the fixture. If these diverge the suite
        is testing a package shape nothing produces."""
        real = REPO / "replay" / "pass-001.json"
        if not real.is_file():
            self.skipTest("no recorded package present")
        package = json.loads(real.read_text(encoding="utf-8"))
        ok, violations = conformance.check(package, filename_stem=real.stem, path=real)
        self.assertTrue(ok, "\n".join(str(v) for v in violations))


class TestEveryRuleIsFalsifiable(unittest.TestCase):
    """RED, one case per rule. Each breaks exactly one thing and expects that rule."""
    verifies = ("HUG-UI-003", "HUG-VER-002")
    polarity = "red"

    def _broken(self, mutate):
        package = conforming_package()
        mutate(package)
        return package

    def _assert_names(self, rule, mutate, **kw):
        rules = refused_rules(self._broken(mutate), **kw)
        self.assertIn(rule, rules,
                      f"breaking {rule} was not caught; the checker named {sorted(rules)}")

    # --- Sec. 2: form and identity
    def test_rs_2_01_a_package_outside_replay(self):
        self._assert_names("RS-2-01", lambda p: None,
                           path=Path("elsewhere/pass-001.json"))

    def test_rs_2_02_a_fifth_top_level_member(self):
        self._assert_names("RS-2-02", lambda p: p.update(extra={}))

    def test_rs_2_02_a_missing_top_level_member(self):
        self._assert_names("RS-2-02", lambda p: p.pop("events"))

    def test_rs_2_03_a_reused_identifier(self):
        rules = refused_rules(conforming_package(), known_pass_ids={"pass-001"})
        self.assertIn("RS-2-03", rules)

    def test_rs_2_05_an_epoch_that_is_not_an_instant(self):
        self._assert_names("RS-2-05",
                           lambda p: p["meta"].update(epoch_utc="last Tuesday"))

    def test_rs_3_01_a_schema_number_that_is_not_this_interface(self):
        self._assert_names("RS-3-01", lambda p: p["meta"].update(schema="0.1"))

    # --- Sec. 4: track
    def test_rs_4_01_an_empty_track(self):
        def mutate(p):
            p["track"] = []
            p["meta"]["end_s"] = 4.0
        self._assert_names("RS-4-01", mutate)

    # --- Sec. 5: frames
    def test_rs_5_01_a_frame_that_is_not_an_object(self):
        self._assert_names("RS-5-01", lambda p: p["frames"].__setitem__(0, "not a frame"))

    def test_rs_5_02_a_member_that_is_not_a_dictionary_mnemonic(self):
        self._assert_names("RS-5-02",
                           lambda p: p["frames"][0].update(battery_volts=7.4))

    def test_rs_5_02_a_mnemonic_left_uppercase(self):
        """The transform is bijective and lowercase; an uppercase member is a second
        mapping, which the rule says does not exist."""
        def mutate(p):
            p["frames"][0]["EPS_BATT_V"] = p["frames"][0].pop("eps_batt_v")
        self._assert_names("RS-5-02", mutate)

    # --- Sec. 6: events
    def test_rs_6_01_markup_in_event_text(self):
        self._assert_names("RS-6-01",
                           lambda p: p["events"][0].update(text="<b>bold</b>"))

    def test_rs_6_02_a_command_object_that_is_not_an_object(self):
        self._assert_names("RS-6-02", lambda p: p["events"][0].update(cmd="CMD"))

    def test_rs_6_02_a_result_outside_its_two_values(self):
        self._assert_names("RS-6-02",
                           lambda p: p["events"][0]["cmd"].update(result="maybe"))

    # --- Sec. 7: the value contract
    def test_rs_7_01_an_undefined_meta_member(self):
        self._assert_names("RS-7-01", lambda p: p["meta"].update(operator="dan"))

    def test_rs_7_01_a_missing_required_meta_member(self):
        self._assert_names("RS-7-01", lambda p: p["meta"].pop("gs"))

    def test_rs_7_01_an_undefined_track_member(self):
        self._assert_names("RS-7-01", lambda p: p["track"][0].update(range_km=1200.0))

    def test_rs_7_02_a_non_finite_number(self):
        self._assert_names("RS-7-02",
                           lambda p: p["track"][0].update(alt_km=float("inf")))

    def test_rs_7_03_a_zero_cadence(self):
        self._assert_names("RS-7-03", lambda p: p["meta"].update(cadence_s=0))

    def test_rs_7_04_a_window_out_of_order(self):
        self._assert_names("RS-7-04",
                           lambda p: p["meta"].update(aos_s=3.0, los_s=1.0))

    def test_rs_7_05_a_time_past_the_end(self):
        self._assert_names("RS-7-05", lambda p: p["events"][0].update(t_s=99.0))

    def test_rs_7_06_times_out_of_order(self):
        def mutate(p):
            p["events"][0]["t_s"], p["events"][1]["t_s"] = 2.0, 1.0
        self._assert_names("RS-7-06", mutate)

    def test_rs_7_07_a_track_off_the_cadence_grid(self):
        self._assert_names("RS-7-07", lambda p: p["track"].pop())

    def test_rs_7_08_a_non_boolean_eclipse_flag(self):
        self._assert_names("RS-7-08", lambda p: p["track"][0].update(ecl="yes"))

    def test_rs_7_09_a_longitude_at_the_excluded_end(self):
        """-180 is excluded and 180 is included; a checker using a closed interval on
        both ends would pass this."""
        self._assert_names("RS-7-09", lambda p: p["track"][0].update(lon_deg=-180.0))

    def test_rs_7_09_an_azimuth_at_360(self):
        self._assert_names("RS-7-09", lambda p: p["track"][0].update(az_deg=360.0))

    def test_rs_7_10_an_enum_outside_its_dictionary_values(self):
        self._assert_names("RS-7-10", lambda p: p["frames"][0].update(eps_mode="TURBO"))

    def test_rs_7_11_a_counter_past_its_width(self):
        self._assert_names("RS-7-11",
                           lambda p: p["frames"][0].update(cdh_frame_cnt=65536))

    def test_rs_7_12_a_state_of_charge_above_full(self):
        self._assert_names("RS-7-12",
                           lambda p: p["frames"][0].update(eps_batt_soc=101.0))

    def test_rs_7_13_a_rate_outside_its_domain_while_the_payload_is_off(self):
        """The rate register always holds a dictionary-valid value, so an OFF frame
        still reports one in [0.1, 10]. A checker that skipped the domain when
        pld_state was OFF would pass this."""
        self._assert_names("RS-7-13",
                           lambda p: p["frames"][0].update(pld_state="OFF",
                                                           pld_rate=0.0))

    def test_rs_7_14_a_command_mnemonic_not_in_the_dictionary(self):
        self._assert_names("RS-7-14",
                           lambda p: p["events"][0]["cmd"].update(mnemonic="CMD_LAND"))

    def test_rs_7_15_accepted_with_a_reason(self):
        self._assert_names("RS-7-15",
                           lambda p: p["events"][0]["cmd"].update(reason="ARG_RANGE"))

    def test_rs_7_15_rejected_with_reason_none(self):
        """The invariant is if-and-only-if. A checker testing one direction passes this
        one and fails the other, which is why both are here."""
        self._assert_names("RS-7-15",
                           lambda p: p["events"][1]["cmd"].update(reason="NONE"))

    def test_rs_7_16_a_pass_id_outside_the_grammar(self):
        def mutate(p):
            p["meta"]["pass_id"] = "Pass 001"
        self._assert_names("RS-7-16", mutate, filename_stem="Pass 001")

    def test_rs_7_17_a_reserved_device_basename(self):
        def mutate(p):
            p["meta"]["pass_id"] = "con"
        self._assert_names("RS-7-17", mutate, filename_stem="con")

    def test_rs_7_18_a_pass_id_that_is_not_the_filename_stem(self):
        self._assert_names("RS-7-18", lambda p: None, filename_stem="pass-002")

    def test_rs_7_18_is_not_skipped_when_no_stem_is_supplied(self):
        """A check that quietly does nothing when an input is absent is
        indistinguishable from one that passed."""
        _ok, violations = conformance.check(conforming_package())
        self.assertIn("RS-7-18", {v.rule for v in violations})

    def test_rs_7_19_a_second_package_for_one_pass(self):
        rules = refused_rules(conforming_package(), known_pass_ids={"pass-001"})
        self.assertIn("RS-7-19", rules)


class TestValidVariationsAreNotFlagged(unittest.TestCase):
    """GREEN. A checker reading for a spelling rather than the condition fails here."""
    verifies = ("HUG-UI-003",)
    polarity = "green"

    def _assert_clean(self, mutate):
        package = conforming_package()
        mutate(package)
        ok, violations = conformance.check(
            package, filename_stem=package["meta"]["pass_id"],
            path=Path("replay") / f"{package['meta']['pass_id']}.json")
        self.assertTrue(ok, "\n".join(str(v) for v in violations))

    def test_longitude_at_the_included_end(self):
        self._assert_clean(lambda p: p["track"][0].update(lon_deg=180.0))

    def test_azimuth_at_zero(self):
        self._assert_clean(lambda p: p["track"][0].update(az_deg=0.0))

    def test_a_counter_at_its_upper_bound(self):
        self._assert_clean(lambda p: p["frames"][0].update(cdh_frame_cnt=65535))

    def test_an_empty_frames_array_is_a_legitimate_outage(self):
        """RS-5-01: during an outage no entries exist and the gap IS the record. A
        checker requiring frames to be non-empty would refuse a correctly recorded
        generation-halt pass."""
        self._assert_clean(lambda p: p.update(frames=[]))

    def test_an_event_without_a_command(self):
        self._assert_clean(lambda p: p["events"][0].pop("cmd"))

    def test_a_pass_id_at_the_grammar_limits(self):
        limit = "a" + "z0-_" * 15 + "abc"
        self.assertEqual(len(limit), 64)

        def mutate(p):
            p["meta"]["pass_id"] = limit
        package = conforming_package()
        mutate(package)
        ok, violations = conformance.check(
            package, filename_stem=limit, path=Path("replay") / f"{limit}.json")
        self.assertTrue(ok, "\n".join(str(v) for v in violations))

    def test_nullable_eclipse_fields_may_be_null(self):
        self._assert_clean(lambda p: p["meta"].update(eclipse_entry_s=None,
                                                      eclipse_exit_s=None))


class TestRefusalNamesItsRule(unittest.TestCase):
    """RS-7-20. A refusal saying 'invalid package' is not actionable."""
    verifies = ("HUG-UI-003",)

    def test_the_refusal_names_the_rule_and_quotes_it(self):
        package = conforming_package()
        package["frames"][0]["eps_mode"] = "TURBO"
        text = conformance.refuse(package, filename_stem="pass-001")
        self.assertIn("RS-7-10", text)
        self.assertIn("dictionary values", text.lower())
        self.assertIn("TURBO", text)

    def test_a_conforming_package_is_not_refused(self):
        self.assertIsNone(conformance.refuse(
            conforming_package(), filename_stem="pass-001",
            path=Path("replay/pass-001.json")))

    def test_many_occurrences_of_one_rule_are_grouped(self):
        """Ten thousand identical lines buries the other rules that also failed."""
        package = conforming_package()
        for f in package["frames"]:
            f["eps_mode"] = "TURBO"
        text = conformance.refuse(package, filename_stem="pass-001")
        self.assertIn("occurrence(s)", text)
        self.assertLess(len(text.split("\n")), 40, "the refusal was not grouped")


class TestEveryDeclaredRuleIsAccountedFor(unittest.TestCase):
    """A rule in the interface definition with no check anywhere is a rule nobody
    enforces, and a package violating it would simply pass."""
    verifies = ("HUG-UI-003",)

    def test_declared_equals_check_plus_viewer(self):
        declared = set(conformance.rule_ids())
        unaccounted = declared - conformance.implemented_rules()
        self.assertEqual(unaccounted, set(),
                         f"rules declared by the schema and enforced nowhere: "
                         f"{sorted(unaccounted)}")

    def test_nothing_is_implemented_in_both_places(self):
        """A rule claimed at both sites means one of them is stale, and a reader
        cannot tell which is authoritative."""
        both = conformance.implemented_in_check() & set(
            conformance.IMPLEMENTED_AT_VIEWER)
        self.assertEqual(both, set(), f"claimed in both places: {sorted(both)}")

    def test_every_viewer_rule_names_the_code_that_implements_it(self):
        """These were dispositions -- prose promising where a rule would be honoured.
        A promise cannot fail. Each now names a module and symbol, and
        test_ve_viewer.py calls them."""
        for rule, entry in conformance.IMPLEMENTED_AT_VIEWER.items():
            self.assertTrue(entry["module"].startswith("ve"),
                            f"{rule} does not name a module in ve/")
            self.assertTrue(entry["symbol"], f"{rule} names no symbol")
            self.assertGreater(len(entry["how"]), 80,
                               f"{rule} does not say what its implementation does")

    def test_no_rule_is_claimed_that_the_schema_does_not_declare(self):
        self.assertEqual(conformance.implemented_rules() - set(conformance.rule_ids()),
                         set())

    def test_the_rule_set_is_not_empty(self):
        """Guards every assertion above from passing over an empty set."""
        self.assertGreaterEqual(len(conformance.rule_ids()), 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
