#!/usr/bin/env python3
"""The text-only rendering sink (HUG-UI-007).

HUG-UI-007, verbatim: *"The viewer shall render replay event text through a text-only
sink with no markup or code interpretation; no replay-package content shall be
interpreted as executable or markup content."*

THIS SINK NEVER INTERPRETS, IT ONLY ENCODES. That distinction is the whole requirement.
A sanitiser inspects input, decides what is dangerous, and removes it — so it is only as
good as its author's imagination, and every one of them has a bypass discovered later. An
encoder makes no decisions: every character that could be structural in the output
language is replaced by a reference that renders as that character and can never open an
element, close one, or start a script. There is nothing to bypass because nothing is
being judged.

So `to_html_text` has no allowlist, no blocklist, and no notion of "safe" content. Hostile
and benign strings take the identical path, which is why the malicious-markup test can
assert that the hostile ones come out visible and inert rather than removed: the operator
sees exactly what the package said, and none of it acts.

TWO INDEPENDENT GUARANTEES, deliberately. RS-6-01 forbids producers emitting markup at
all, and `ve/conformance.py` refuses a package whose event text carries markup. This
sink is the second: it assumes that check does not exist. A filter is a thing that can
have a hole; a sink that never interprets cannot. Neither is allowed to be the reason the
other may be relaxed.
"""
import html
import re

#: Characters that are structural in HTML. Every one is encoded, unconditionally.
#: Named here for the tests to iterate rather than for the encoder to consult — the
#: encoder defers to `html.escape`, which is the standard library's, not ours.
STRUCTURAL = ("<", ">", "&", '"', "'")


def to_html_text(text):
    """One replay string, encoded so it renders as itself and does nothing.

    `quote=True` encodes both quote characters as well, so the result is inert in an
    attribute context too. The viewer only ever places this in a text node, but a sink
    whose safety depends on where the caller puts it is a sink with a usage rule, and
    usage rules are the things that get forgotten.
    """
    if not isinstance(text, str):
        raise TypeError(f"the rendering sink takes strings; got {type(text).__name__}. "
                        f"A non-string reaching the sink means a package was rendered "
                        f"without conformance checking.")
    return html.escape(text, quote=True)


def to_plain_text(text):
    """The same content for a non-markup surface — a console, a log, a text file.

    Identity, and that is the point: in a context with no markup language there is
    nothing to encode, and pretending otherwise would put `&amp;` in front of an operator
    reading a terminal. The sink is chosen by the OUTPUT surface, never by the content.
    """
    if not isinstance(text, str):
        raise TypeError(f"the rendering sink takes strings; got {type(text).__name__}")
    return text


#: Sequences that can act when they appear UNENCODED in a document. Used only by the
#: tests, to assert that a raw payload really is dangerous before asserting that its
#: rendered form is not. The encoder does not consult this — if it did, it would be a
#: sanitiser.
DANGEROUS = re.compile(
    r"<\s*script|<\s*/\s*script|<\s*img|<\s*svg|<\s*iframe|onerror\s*=|onload\s*="
    r"|javascript:|data:text/html", re.I)

#: The characters that can END a text node or BREAK OUT of an attribute. Nothing else
#: in a string can begin markup, which is why this short list is the whole test.
STRUCTURAL_IN_OUTPUT = ("<", ">", '"', "'")


def renders_inert(rendered):
    """True when nothing in `rendered` can open an element or break an attribute.

    THE ORACLE ASKS ABOUT STRUCTURE, NOT VOCABULARY, and the difference cost this suite
    six false failures. The first version searched the RENDERED text for `onerror=`,
    `javascript:` and friends, and flagged `&lt;img src=x onerror=alert(1)&gt;` as
    dangerous. It is not. An attribute can only exist inside an element, an element can
    only be opened by an unencoded `<`, and once the angle brackets are encoded those
    characters are letters on a screen — which is precisely the outcome the requirement
    wants: the operator reads what the package said, and none of it acts.

    An oracle that hunts for scary words rather than for structure fails safe content
    and, worse, would pass a novel payload that spells its attack differently. The
    structural question has no vocabulary to keep up with.

    SCOPE, stated because it is a real limit and not a caveat. This is inertness in a
    TEXT NODE, which is the only place the viewer puts package content. A string like
    `javascript:alert(1)` is inert as text and would not be inert as the value of an
    `href`; encoding quotes does not make a URL scheme safe. The viewer never
    constructs a URL, an attribute, or a script from package content — that is a
    property of the viewer's construction, not of this function, and `excluded_content`
    in the schema forbids the package carrying such content in the first place.
    """
    return not any(ch in rendered for ch in STRUCTURAL_IN_OUTPUT)


def render_events(events, sink=to_html_text):
    """Every event's text through the sink, in order.

    Takes the sink as an argument so the viewer's surface chooses it, and so the tests
    can drive the same events through both surfaces and assert the difference is the
    surface rather than the content.
    """
    return [{"t_s": e["t_s"], "sev": e["sev"], "text": sink(e["text"])}
            for e in events]
