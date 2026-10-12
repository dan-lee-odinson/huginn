#!/usr/bin/env python3
"""The VÉ viewer (HUG-UI-004/005/006/007, and three schema rules).

The viewer is a Python-built static page. That is a design decision with a reason: a
JavaScript viewer that loaded packages would need the replay contract implemented again
in JS — the private copy HUG-UI-003 forbids — and the two would drift, each staying green
against its own reading. So the contract has one implementation, the builder runs it
before writing anything, and the page that ships holds drawing code with no rules in it.

THREE RULES ARE IMPLEMENTED HERE RATHER THAN DISPOSITIONED. RS-2-04, RS-4-02 and RS-7-20
are not properties of a package's content, so `ve/conformance.py` cannot check them
against one. They used to be prose entries saying where they *would* be honoured. A
disposition cannot fail — it is a sentence, and sentences stay true while the code beneath
them rots. Each is now a named symbol that this suite calls.
"""
import copy
import importlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
import gen_ve_viewer                                           # noqa: E402
import hugdefs                                                   # noqa: E402
from ve import conformance, interpolate, render                # noqa: E402
from ve.viewer import build as viewer_build                    # noqa: E402
from test_replay_conformance import conforming_package           # noqa: E402

VIEWER_DIR = REPO / "ve" / "viewer"


def code_only(text):
    """Source with comments removed, for assertions that are about CODE.

    Shared, because four separate tests in this file were written against raw source
    and every one of them caught the documentation instead of the behaviour: the word
    `innerHTML` in a comment saying it is never assigned, `XMLHttpRequest` in a comment
    saying there is none, and the `001` of a `D-001` ruling reference read as a numeric
    literal. A test that fails on a file's prose is not testing the file.

    Only whole comment lines are dropped, never a trailing `//` inside a line -- a URL
    such as `http://www.w3.org/2000/svg` is code, and cutting at its slashes would hide
    exactly the kind of external reference another test here exists to find.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith("//"))


def built_page(package=None, pass_id="pass-001"):
    """Build a page in a temporary directory and return its text."""
    package = package or conforming_package(pass_id=pass_id)
    with tempfile.TemporaryDirectory() as td:
        replay = Path(td) / "replay"
        replay.mkdir()
        src = replay / f"{pass_id}.json"
        src.write_text(json.dumps(package), encoding="utf-8")
        out = viewer_build.build(src, out_dir=Path(td) / "viewer")
        return out.read_text(encoding="utf-8")


class TestRS0204ImplementedAtTheViewer(unittest.TestCase):
    """RS-2-04 — the viewer refuses, never best-effort renders."""
    verifies = ("HUG-UI-003",)

    def test_a_non_conforming_package_produces_no_page(self):
        package = conforming_package()
        package["frames"][0]["eps_batt_soc"] = 101.0
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "replay"
            replay.mkdir()
            src = replay / "pass-001.json"
            src.write_text(json.dumps(package), encoding="utf-8")
            out_dir = Path(td) / "viewer"
            with self.assertRaises(viewer_build.ViewerRefusal):
                viewer_build.build(src, out_dir=out_dir)
            # RED: not merely "it raised". A page written and then abandoned would be a
            # page an operator could open, which is exactly best-effort rendering.
            self.assertFalse((out_dir / "pass-001.html").exists(),
                             "a page was written for a package that was refused")

    def test_the_refusal_names_the_rules(self):
        package = conforming_package()
        package["frames"][0]["eps_batt_soc"] = 101.0
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "replay"
            replay.mkdir()
            src = replay / "pass-001.json"
            src.write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaises(viewer_build.ViewerRefusal) as caught:
                viewer_build.build(src, out_dir=Path(td) / "viewer")
        self.assertIn("RS-7-12", str(caught.exception))

    def test_the_page_has_no_way_to_load_another_package(self):
        """The structural half. A page that could fetch or open a file could acquire an
        UNCHECKED package, and the guarantee would rest on nobody using that path."""
        page = code_only(built_page())
        # NOT a blanket ban on <input>: the pass-timeline scrubber is a range slider,
        # and the first version of this test failed on it. The concern is a control or
        # API that can ACQUIRE a package, not one that moves a cursor.
        for loader in ("fetch(", "XMLHttpRequest", 'type="file"', "import(",
                       "WebSocket", "EventSource", "navigator.clipboard"):
            self.assertNotIn(loader, page,
                             f"the page contains {loader!r}, so it can acquire a "
                             f"package that no one checked")

    def test_a_conforming_package_does_produce_a_page(self):
        """GREEN. A viewer that refused everything would satisfy the red case above and
        be useless."""
        self.assertIn("VÉ", built_page())


class TestRS0402ImplementedAtTheViewer(unittest.TestCase):
    """RS-4-02 — shortest arc for circular quantities, at the drawing."""
    verifies = ("HUG-UI-003",)

    def test_the_ground_track_splits_at_the_antimeridian(self):
        track = [{"lon_deg": 179.0, "lat_deg": 0.0}, {"lon_deg": 179.8, "lat_deg": 1.0},
                 {"lon_deg": -179.4, "lat_deg": 2.0}, {"lon_deg": -178.6, "lat_deg": 3.0}]
        segments = interpolate.ground_track_segments(track)
        self.assertEqual(len(segments), 2,
                         "the crossing was not split; one polyline through these "
                         "samples draws a line across the whole map")
        self.assertEqual([len(s) for s in segments], [2, 2])

    def test_a_track_that_does_not_cross_is_one_segment(self):
        """GREEN. Splitting where nothing wraps would invent a discontinuity."""
        track = [{"lon_deg": 10.0 + i, "lat_deg": 0.0} for i in range(5)]
        self.assertEqual(len(interpolate.ground_track_segments(track)), 1)

    def test_shortest_arc_goes_the_short_way(self):
        self.assertAlmostEqual(interpolate.shortest_arc(179.5, -179.5, 0.5), 180.0, 6)
        # Linear would give 0.0 — the middle of the map, half a world away.
        self.assertNotAlmostEqual(interpolate.shortest_arc(179.5, -179.5, 0.5), 0.0, 3)

    def test_the_built_page_carries_split_segments(self):
        """The rule has to reach the drawing, not just exist in a module."""
        page = built_page()
        self.assertIn("trackSegments", page)


class TestRS0720ImplementedAtTheViewer(unittest.TestCase):
    """RS-7-20 — a refusal names the rule it failed."""
    verifies = ("HUG-UI-003",)

    def test_the_refusal_quotes_the_rules_own_statement(self):
        package = conforming_package()
        package["meta"]["cadence_s"] = 0
        text = conformance.refuse(package, filename_stem="pass-001")
        self.assertIn("RS-7-03", text)
        self.assertIn(conformance.rule_statement("RS-7-03"), text)

    def test_a_refusal_without_a_rule_id_would_be_useless(self):
        """RED for the property: every line naming a problem names a rule."""
        package = conforming_package()
        package["frames"][0]["eps_mode"] = "TURBO"
        package["track"][0]["ecl"] = "yes"
        text = conformance.refuse(package, filename_stem="pass-001")
        for rule in ("RS-7-10", "RS-7-08"):
            self.assertIn(rule, text)


class TestTheAccounting(unittest.TestCase):
    """Two sites, one accounting: none in both, none in neither."""
    verifies = ("HUG-UI-003",)

    def test_declared_equals_check_plus_viewer(self):
        declared = set(conformance.rule_ids())
        check = conformance.implemented_in_check()
        viewer = set(conformance.IMPLEMENTED_AT_VIEWER)
        self.assertEqual(declared - check - viewer, set(),
                         "rules the schema declares and nobody implements")

    def test_nothing_is_claimed_in_both(self):
        both = conformance.implemented_in_check() & set(
            conformance.IMPLEMENTED_AT_VIEWER)
        self.assertEqual(both, set(), f"claimed twice: {sorted(both)}")

    def test_every_viewer_rule_names_a_symbol_that_exists_and_is_callable(self):
        """This is what a disposition could not do. A prose entry stays true while the
        code it describes is renamed or deleted; this fails."""
        for rule, entry in conformance.IMPLEMENTED_AT_VIEWER.items():
            with self.subTest(rule=rule):
                module = importlib.import_module(entry["module"])
                self.assertTrue(hasattr(module, entry["symbol"]),
                                f"{rule} names {entry['module']}.{entry['symbol']}, "
                                f"which does not exist")
                self.assertTrue(callable(getattr(module, entry["symbol"])))
                self.assertGreater(len(entry["how"]), 80,
                                   f"{rule} does not say what its implementation does")

    def test_the_rule_set_is_not_empty(self):
        self.assertGreaterEqual(len(conformance.rule_ids()), 30)
        self.assertEqual(len(conformance.IMPLEMENTED_AT_VIEWER), 3)


class TestHugUi005LimitsDeriveFromTheDictionary(unittest.TestCase):
    verifies = ("HUG-UI-005",)

    def test_the_limit_table_matches_the_dictionary(self):
        table = gen_ve_viewer.limit_table(hugdefs.load_tlm_cmd())
        for point in hugdefs.points(hugdefs.load_tlm_cmd()):
            limits = point.get("limits") or {}
            if limits.get("kind") != "thresholds":
                continue
            entry = table[point["mnemonic"].lower()]
            for side in ("rl", "yl", "yh", "rh"):
                self.assertEqual(entry[side], limits.get(side),
                                 f"{point['mnemonic']}.{side} disagrees with defs")

    def test_the_table_follows_the_dictionary_when_it_changes(self):
        """BEHAVIOURAL, and this is what HUG-UI-005 actually asks.

        The first version of this test scanned the renderer for any digit matching a
        threshold and failed on the CSS line-height `13px/1.5` -- proving the absence of
        a character rather than the presence of derivation. Moving a limit in the
        dictionary and watching the table follow proves the thing itself.
        """
        defs = copy.deepcopy(hugdefs.load_tlm_cmd())
        for group in defs["telemetry_groups"]:
            for point in group["points"]:
                if point["mnemonic"] == "EPS_BATT_V":
                    point["limits"]["rl"] = 5.55
        table = gen_ve_viewer.limit_table(defs)
        self.assertEqual(table["eps_batt_v"]["rl"], 5.55,
                         "the limit table did not follow the dictionary")
        # And the committed table is the UNMUTATED dictionary's, so the mutation above
        # cannot be what a passing result rests on.
        self.assertNotEqual(
            gen_ve_viewer.limit_table(hugdefs.load_tlm_cmd())["eps_batt_v"]["rl"],
            5.55)

    def test_the_severity_function_reads_every_bound_from_the_table(self):
        """STRUCTURAL, and narrow enough to mean something: the function that decides
        green/yellow/red compares against the spec's fields and against no number."""
        js = code_only((VIEWER_DIR / "ve.js").read_text(encoding="utf-8"))
        body = js.split("function severity(")[1].split("\n  }")[0]
        for field in ("s.rl", "s.yl", "s.yh", "s.rh"):
            self.assertIn(field, body,
                          f"severity() does not consult {field} from the generated "
                          f"table")
        numeric = re.findall(r"(?<![\w.])\d+\.?\d*(?![\w.])", body)
        self.assertEqual(numeric, [],
                         f"severity() compares against literal number(s) {numeric}; "
                         f"every bound must come from the dictionary")

    def test_absent_limit_sides_stay_null(self):
        """Ruling D-001 at the display. EPS_BATT_SOC has no high limits, and a
        sentinel standing in for one would be a limit an operator could read as real —
        a display has nowhere to put the caveat."""
        table = gen_ve_viewer.limit_table(hugdefs.load_tlm_cmd())
        soc = table["eps_batt_soc"]
        self.assertIsNone(soc["yh"])
        self.assertIsNone(soc["rh"])
        self.assertIsNotNone(soc["rl"])

    def test_the_generated_table_carries_no_sentinel(self):
        import gen_openc3_config
        text = (VIEWER_DIR / "limits.js").read_text(encoding="utf-8")
        for sentinel in (gen_openc3_config.ABSENT_LIMIT_LOW,
                         gen_openc3_config.ABSENT_LIMIT_HIGH):
            self.assertNotIn(f"{sentinel:g}", text)


class TestHugUi006StaticNoBackend(unittest.TestCase):
    verifies = ("HUG-UI-006", "HUG-UI-001")

    def test_the_page_references_no_external_asset(self):
        page = built_page()
        refs = re.findall(r'(?:src|href)\s*=\s*"([^"]*)"', page)
        self.assertEqual(refs, [], f"the page loads external assets: {refs}")

    def test_the_page_is_one_file(self):
        page = built_page()
        self.assertIn("<style>", page)
        self.assertIn("<script>", page)
        self.assertIn("window.VE_LIMITS", page)
        self.assertIn("window.VE_PACKAGE", page)

    def test_the_page_opens_from_a_file_url(self):
        """No absolute or protocol-relative URL anywhere: a page that reached out to a
        host would not work from local files and would not be backend-free."""
        page = built_page()
        for scheme in ("http://", "https://", "//cdn", "ws://"):
            # The SVG namespace is a URI in an attribute value, not a fetch.
            occurrences = [m for m in re.findall(re.escape(scheme) + r"\S*", page)
                           if "www.w3.org" not in m]
            self.assertEqual(occurrences, [], f"page reaches out: {occurrences[:3]}")


class TestHugUi004TheRequiredElements(unittest.TestCase):
    """The requirement names what the viewer shall present, at minimum."""
    verifies = ("HUG-UI-004",)

    def setUp(self):
        self.page = built_page()

    def test_orbit_view_with_eclipse_and_contact_window(self):
        self.assertIn('id="orbit-svg"', self.page)
        self.assertIn("eclipse", self.page.lower())
        self.assertIn("contact", self.page.lower())

    def test_eps_power_flow(self):
        self.assertIn('id="power-svg"', self.page)
        for node in ("ARRAY STRING 1", "ARRAY STRING 2", "BUS", "LOAD", "BATTERY"):
            self.assertIn(node, self.page)

    def test_soc_and_voltage_trends(self):
        self.assertIn('id="trend-soc"', self.page)
        self.assertIn('id="trend-volt"', self.page)

    def test_annunciator_states(self):
        self.assertIn("data-annunciator", self.page)
        self.assertIn('id="annunciator-staleness"', self.page)

    def test_command_accept_reject_events(self):
        package = conforming_package()
        page = built_page(package)
        self.assertIn("CMD_PLD_SET_STATE", page)
        self.assertIn("accepted", page)
        self.assertIn("rejected", page)
        self.assertIn("MODE_INHIBIT", page)

    def test_pass_timeline_scrubber(self):
        self.assertIn('id="scrubber"', self.page)
        self.assertIn('type="range"', self.page)


class TestHugUi007TheSinkIsInTheRenderPath(unittest.TestCase):
    """Not merely available — actually used on the way to the page."""
    verifies = ("HUG-UI-007",)

    def test_event_text_is_encoded_in_the_built_page(self):
        package = conforming_package()
        # A package carrying markup would be refused by RS-6-01, so this bypasses the
        # producer check to prove the SINK is what makes the page safe.
        package["events"][0]["text"] = "<script>alert(1)</script>"
        page = viewer_build.build_page(package, "pass-001")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_the_hostile_text_is_still_visible(self):
        package = conforming_package()
        package["events"][0]["text"] = "<script>alert(1)</script>"
        page = viewer_build.build_page(package, "pass-001")
        self.assertIn("alert(1)", page, "the content was removed rather than encoded")

    def test_the_renderer_never_assigns_innerhtml(self):
        """The JS half. Package strings reach the DOM through textContent or through
        rows the Python sink already encoded."""
        js = code_only((VIEWER_DIR / "ve.js").read_text(encoding="utf-8"))
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write",
                     "eval(", "Function("):
            self.assertNotIn(sink, js,
                             f"ve.js uses {sink!r}, which interprets its argument")

    def test_the_renderer_does_set_textcontent(self):
        """GREEN, and it guards the red case above from passing on an empty file."""
        js = code_only((VIEWER_DIR / "ve.js").read_text(encoding="utf-8"))
        self.assertGreater(js.count("textContent"), 5)

    def test_the_builder_uses_the_proven_sink(self):
        import inspect
        src = inspect.getsource(viewer_build.event_rows)
        self.assertIn("render.to_html_text", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
