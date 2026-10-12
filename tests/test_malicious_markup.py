#!/usr/bin/env python3
"""The malicious-markup test (B11, HUG-UI-007).

HUG-UI-007: *"The viewer shall render replay event text through a text-only sink with no
markup or code interpretation; no replay-package content shall be interpreted as
executable or markup content."* Resolved at G001-02 F-15, which required this test by
name.

TWO INDEPENDENT GUARANTEES, AND THE TEST TREATS THEM AS INDEPENDENT.

  1. RS-6-01 binds the PRODUCER: no markup is emitted, and `ve/conformance.py` refuses
     a package whose event text carries any.
  2. HUG-UI-007 binds the VIEWER: the sink never interprets, whatever it is handed.

The second half of this suite deliberately BYPASSES the first — it hands hostile strings
straight to the sink, as though the conformance check did not exist. That is the point. A
filter is a thing that can have a hole; a sink that never interprets cannot. If the sink's
inertness were contingent on the filter having run, then one bypass in the filter would be
an execution, and the two guarantees would really be one.

INERT, NOT ABSENT. Every assertion below requires the hostile text to still be VISIBLE
after rendering. A sanitiser that stripped `<script>` would also be deciding what an
operator is allowed to read, and an event whose text silently vanished would be an event
that did not happen as far as the display is concerned. The operator sees exactly what the
package said; none of it acts.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
from ve import conformance, render                             # noqa: E402
from test_replay_conformance import conforming_package           # noqa: E402

#: Hostile payloads. Each is a real technique rather than a decorative `<b>`: script
#: injection, attribute breakout, event handlers on tags that need no closing, protocol
#: handlers, entity-encoded reopening, and a comment breakout.
HOSTILE = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<iframe src='javascript:alert(1)'></iframe>",
    "\" onmouseover=\"alert(1)",
    "' onfocus='alert(1)",
    "javascript:alert(document.cookie)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "&lt;script&gt;alert(1)&lt;/script&gt;",
    "&#60;script&#62;alert(1)&#60;/script&#62;",
    "--><script>alert(1)</script><!--",
    "</textarea><script>alert(1)</script>",
    "<a href=\"javascript:alert(1)\">click</a>",
    "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e",
    "<!--#exec cmd=\"/bin/ls\"-->",
    "{{constructor.constructor('alert(1)')()}}",
]


class TestTheProducerSideRefusesMarkup(unittest.TestCase):
    """RS-6-01 — producers emit no markup, and a package carrying it is refused."""
    verifies = ("HUG-UI-007",)

    def test_every_hostile_payload_is_refused_in_event_text(self):
        for payload in HOSTILE:
            with self.subTest(payload=payload[:40]):
                package = conforming_package()
                package["events"][0]["text"] = payload
                _ok, violations = conformance.check(package, filename_stem="pass-001")
                rules = {v.rule for v in violations}
                # Not every payload is markup-shaped -- the template-injection and
                # backslash-escaped ones are not -- so the requirement here is that the
                # package is refused OR the sink renders it inert, and the sink half is
                # asserted unconditionally below. What must never happen is a payload
                # that is neither refused nor inert.
                if "RS-6-01" not in rules:
                    self.assertTrue(
                        render.renders_inert(render.to_html_text(payload)),
                        f"{payload!r} was neither refused by RS-6-01 nor rendered "
                        f"inert; it is covered by neither guarantee")

    def test_the_refusal_names_the_rule(self):
        package = conforming_package()
        package["events"][0]["text"] = "<script>alert(1)</script>"
        text = conformance.refuse(package, filename_stem="pass-001")
        self.assertIn("RS-6-01", text)

    def test_plain_event_text_is_not_refused(self):
        """GREEN. A producer-side filter that flagged ordinary operational text would
        make the rule unusable, and it would be turned off."""
        for benign in ("payload activated", "eclipse entry at 1204 s",
                       "SoC 74.5% -- above the 40% activation inhibit",
                       "CMD_PLD_SET_RATE accepted (rate 2.5 Hz)"):
            with self.subTest(text=benign):
                package = conforming_package()
                package["events"][0]["text"] = benign
                _ok, violations = conformance.check(package, filename_stem="pass-001")
                self.assertNotIn("RS-6-01", {v.rule for v in violations})


class TestTheSinkRendersHostileTextInert(unittest.TestCase):
    """HUG-UI-007 — and this half assumes the check above does not exist.

    Every case here hands the sink a payload directly. If these passed only because
    conformance had already refused the package, the sink would not be a second
    guarantee at all.
    """
    verifies = ("HUG-UI-007",)

    def test_every_hostile_payload_renders_inert(self):
        for payload in HOSTILE:
            with self.subTest(payload=payload[:40]):
                rendered = render.to_html_text(payload)
                self.assertTrue(
                    render.renders_inert(rendered),
                    f"{payload!r} rendered as {rendered!r}, which can still act")

    def test_no_structural_character_survives_unencoded(self):
        for payload in HOSTILE:
            with self.subTest(payload=payload[:40]):
                rendered = render.to_html_text(payload)
                for ch in ("<", ">"):
                    self.assertNotIn(ch, rendered)

    def test_the_hostile_text_is_still_visible(self):
        """INERT, NOT ABSENT. An operator must see what the package said."""
        payload = "<script>alert('xss')</script>"
        rendered = render.to_html_text(payload)
        self.assertIn("script", rendered)
        self.assertIn("alert", rendered)
        self.assertGreater(len(rendered), len(payload),
                           "the payload was shortened, which means content was removed "
                           "rather than encoded")

    def test_nothing_is_stripped_or_replaced(self):
        """Every payload's alphanumeric content survives intact. A sanitiser would
        fail this while still looking safe."""
        for payload in HOSTILE:
            with self.subTest(payload=payload[:40]):
                rendered = render.to_html_text(payload)
                letters = "".join(c for c in payload if c.isalnum())
                surviving = "".join(c for c in rendered if c.isalnum())
                for chunk in ("script", "alert", "onerror", "onload"):
                    if chunk in letters:
                        self.assertIn(chunk, surviving,
                                      f"{chunk!r} was removed from {payload!r}")

    def test_benign_text_passes_through_readably(self):
        """GREEN. An encoder that mangled ordinary text would make the display worse
        and would be worked around."""
        plain = "SoC 74.5 percent, payload ON, rate 2.5 Hz"
        self.assertEqual(render.to_html_text(plain), plain)

    def test_the_sink_refuses_a_non_string(self):
        """A non-string reaching the sink means a package was rendered without
        conformance checking, which is a control-flow bug worth a loud failure."""
        with self.assertRaises(TypeError):
            render.to_html_text({"text": "<script>"})

    def test_the_plain_text_surface_does_not_encode(self):
        """The sink is chosen by the OUTPUT surface, never by the content. On a console
        there is no markup language, and `&amp;` in front of an operator is a defect."""
        self.assertEqual(render.to_plain_text("a & b < c"), "a & b < c")


class TestTheOracleItself(unittest.TestCase):
    """The inertness oracle must be able to fail, or every assertion using it is
    vacuous."""
    verifies = ("HUG-UI-007",)

    def test_unrendered_hostile_text_is_not_inert(self):
        """RED for the oracle: a raw payload carrying a structural character must be
        reported as dangerous, or every assertion using the oracle is vacuous."""
        structural = [p for p in HOSTILE
                      if any(c in p for c in render.STRUCTURAL_IN_OUTPUT)]
        self.assertGreaterEqual(len(structural), 10)
        for payload in structural:
            with self.subTest(payload=payload[:40]):
                self.assertFalse(
                    render.renders_inert(payload),
                    f"the oracle called raw {payload!r} inert, so every test using it "
                    f"proves nothing")

    def test_the_oracle_asks_about_structure_not_vocabulary(self):
        """The first oracle searched rendered output for `onerror=` and `javascript:`
        and failed six correctly-encoded payloads. An attribute needs an element and an
        element needs an unencoded `<`; once the brackets are encoded those are letters
        on a screen. An oracle chasing vocabulary also cannot keep up with a payload
        that spells its attack differently."""
        self.assertTrue(render.renders_inert("onerror=alert(1) javascript:alert(1)"),
                        "the oracle flagged scary words that cannot act as text")
        self.assertFalse(render.renders_inert("<b>"),
                         "the oracle missed a character that can open an element")

    def test_the_payload_list_is_not_empty(self):
        self.assertGreaterEqual(len(HOSTILE), 12)


class TestTheTwoGuaranteesAreIndependent(unittest.TestCase):
    verifies = ("HUG-UI-007",)

    def test_the_sink_does_not_import_the_conformance_filter(self):
        """If the sink depended on the producer-side filter, one hole would be two.

        An IMPORT check, not a word search: the first version of this test grepped for
        the string "conformance" and failed on the docstring that explains why the two
        are separate -- a test asserting on prose rather than on the dependency it
        cares about.
        """
        import ast
        tree = ast.parse((REPO / "ve" / "render.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("conformance", imported)
        self.assertNotIn("ve", imported)

    def test_the_sink_makes_no_decision_about_content(self):
        """BEHAVIOURAL. The encoder defers entirely to the standard library, so hostile
        and benign strings take an identical path.

        Stated as behaviour rather than as the absence of an `if` in the source -- the
        first version of this test looked for `if ` and failed on the type guard, which
        is not a decision about content at all.
        """
        import html
        for payload in HOSTILE + ["ordinary text", "", "SoC 74.5%", "a & b"]:
            with self.subTest(payload=payload[:40]):
                self.assertEqual(render.to_html_text(payload),
                                 html.escape(payload, quote=True),
                                 "the sink transformed the input in some way of its "
                                 "own; anything beyond encoding is a judgement about "
                                 "content, and judgements can be wrong")

    def test_the_encoding_is_reversible(self):
        """Nothing is lost. Unescaping the rendered form returns the original exactly,
        which is what makes 'inert, not absent' verifiable rather than asserted."""
        import html
        for payload in HOSTILE:
            with self.subTest(payload=payload[:40]):
                self.assertEqual(html.unescape(render.to_html_text(payload)), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
