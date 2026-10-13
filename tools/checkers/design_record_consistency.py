#!/usr/bin/env python3
"""HUGINN design-record consistency checks, v22 (build phase; FMEA v0.16 baseline).

v22 CHANGES TWO CHECKS, per owner ruling D-020. FMEA v0.16 adds FM-GND-07, the row
D-012 queued for the HUG-G002 revision set, and scopes Sec. 6 to the selection made at
HUG-G001: the rows the campaign was planned and executed on. A row added later is
recorded in a new Sec. 6.3 instead of the screen. C14 counted exactly 22 worksheet rows
and C15 required the selected and excluded sets to cover every R2 worksheet row. Both
were claims about the HUG-G001 record, and both now name it:
  - C14: each of the 22 HUG-G001 rows is present inside a worksheet table, and rows
    added later stand beside them. A bare count would accept a deleted HUG-G001 row as
    soon as one row had been added, and the new red case C14.m6 is exactly that. A
    Sec. 6.3 row needs no recognition of its own here: it names a worksheet row, and
    one that names none is a dangling citation, which C14 already rejects.
  - C15: the selected and excluded sets exactly partition the HUG-G001 R2 rows, and the
    Sec. 6.3 table, parsed within the Sec. 6 bounds by the same grammar, lists exactly
    the R2 rows outside them - each once, well formed, with a risk spelling that agrees
    with its worksheet row.
No other check, claim or self-test case changes. The companion baseline is Concept
Brief v0.28, CONOPS v0.10, Requirements v0.13, FMEA v0.16, Replay Schema v0.9,
Dictionary v0.5.

Prior version header follows.

HUGINN design-record consistency checks, v21 (build phase; FMEA v0.15 baseline).

v21 IS A DOCUMENT-BASELINE SYNC ONLY, per owner ruling D-006. No check, no claim and no
self-test case changes: still 16 checks and 84 cases. The FMEA advanced v0.14 -> v0.15
when ground rule GR-02's limit basis was restated as a ratification anchor with its
currency condition, and the concept brief advanced v0.22 -> v0.23 to keep its companion
baseline current. The companion baseline this checker is written against is therefore
Concept Brief v0.23, CONOPS v0.9, Requirements v0.12, FMEA v0.15, Replay Schema v0.9,
Dictionary v0.5.

Executed at the sync: 16/16 checks PASS and 84/84 self-test cases correct.

Prior version header follows.

HUGINN design-record consistency checks, v20 (build phase; CONOPS v0.9 baseline).

v20 IS A DOCUMENT-BASELINE SYNC ONLY, per owner ruling D-004. No check, no claim and no
self-test case changes: still 16 checks and 84 cases, identical logic and identical
PASS/FAIL messages. The record's CONOPS advanced v0.8 -> v0.9 when the representative
orbit and contact values in its Sec. 3.3 were replaced with values computed from the
pinned surrogate reference element set and the pinned GS-RAVENSROOST site - a
replacement HUG-SYS-002 pre-authorized and v0.8's own Sec. 3.3 announced. The companion
baseline this checker is written against is therefore Concept Brief v0.21, CONOPS v0.9,
Requirements v0.12, FMEA v0.15, Replay Schema v0.9, Dictionary v0.5.

Executed at the sync: 16/16 checks PASS and 84/84 self-test cases correct, against the
v0.9 CONOPS.

Prior version header follows.

HUGINN design-record consistency checks, v19 (build phase, repo layout).

v19 CHANGES LAYOUT AND PORTABILITY ONLY - no check, no claim, and no self-test case
is altered. Still 16 checks and 84 self-test cases, with identical logic and identical
PASS/FAIL messages. Three changes, all outside the checks:
  1. DOCS holds repo-relative paths (docs/*.md, defs/replay_schema.md) instead of the
     packet-era versioned filenames, and the artifact root is the repo root.
  2. The self-test stages only the six documents load() reads instead of copying the
     whole artifact tree - at repo root that would have copied .git 84 times.
  3. Report output degrades unencodable characters instead of dying on a cp1252
     console (the run previously aborted mid-report on Windows).
Executed at adaptation: 16/16 checks PASS and 84/84 self-test cases correct, both
before the change (packet-era filenames, documents byte-identical) and after.

NOTE for the build phase: docs/tlm_cmd_dictionary.md and docs/requirements.md are now
GENERATED VIEWS of defs/tlm_cmd.yaml and defs/requirements.yaml. These checks still
read the markdown, which is correct - they verify the record as it reads. The binding
between each generated view and its source is checked separately by
tools/checkers/defs_generation.py.

Prior version header follows.

HUGINN design-record consistency checks, v18 (HUG-G001 series closure baseline).

SERIES-CLOSURE BASELINE SYNC per the Director's HUG-G001-17 ruling (2026-07-29,
accept with modification/apparatus; the Sec. 5.4 determination closing the HUG-G001
series): the checker's behavior and claims are UNCHANGED from v13 through v17 -
16 checks, 84 self-test cases, the G001-13/G001-14 narrowed claims intact
(canonical-form discipline over the record's defined table grammar; ownership and
parent-token exclusions stated at every claim site; renderer fidelity beyond the
grammar is D0-17 ratified debt). v18 updates only the document baseline (Concept
Brief v0.21 - the G001-17 F-01 correction of the v0.17 changelog entry's
debt-retirement statement to the two retirement paths - with CONOPS v0.8 (v0.9 as
of the v20 sync above),
Requirements v0.12, FMEA v0.14, Replay Schema v0.9, Dictionary v0.5 unchanged) and
the versioned review-record constants.

WHAT THESE CHECKS CLAIM (v14, narrowed): canonical-form discipline over the RECORD'S
DEFINED TABLE GRAMMAR - canonical identifier rows (leading '| ', plain spellings), pipe
tables introduced by a header-plus-delimiter pair, standard unindented-to-3-space
``` / ~~~ fences, and the specific normalizations enumerated in _strip_inline and
_resolve_inline_links - executed with the fence-aware, escape-parity parsing built
across G001-07 through G001-12.

WHAT THEY DO NOT CLAIM: full CommonMark renderer fidelity. The renderer-contract gaps
found at HUG-G001-13 and accepted by the Director as RATIFIED DEBT - C14's line-based
orphan scan (F-01), table ownership for definition rows (F-02), tab-column fence
indentation (F-03), parent-token validation in trace cells (F-04), suite-traceable
residual execution (F-05), and link-destination grammar at the false-positive polarity
(F-07) - are open by ruling, not by oversight. Their retirement paths differ (D0-17 as
amended per G001-14 F-04; stated per G001-16 F-03): the register's items 1-4 and 6
(F-01/F-02/F-03/F-04/F-07 above) retire at build, when defs/ single-source generation
replaces hand-maintained Markdown as the record's substrate and verification moves to
structured data, superseding this checker's Markdown parsing entirely (HUG-G002;
companion to the D0-6 debt). Item 5 - suite-traceable residual execution (F-05 above) -
retires ONLY by its own amended criterion: every checker and mechanism-inventory
direction claim maps to an identified executed case and recorded result, including
required polarity, demonstrated at HUG-G002; defs/ generation alone does not retire it.
Contesting the debt boundary remains admissible; restating the debt's existence is
dispositioned.

Mechanics carried from v13 (all still executed, within the narrowed claim):
  shared parsed-table representation (_doc_rows / _tables_with_lines) for every
  definition-row consumer; escape-parity cell splitting; 0-3-space fence boundaries;
  balanced-parenthesis link destinations; rendered-label normalization with
  definition-gated reference links; recognition/hygiene layering across C1/C2/C14/C15.

Carried from v11: the table-row scope of the canonical rule with its two stay-green
non-table cases; the rendered-label normalizer's reference-style link resolution
(definition-gated) and CommonMark backslash unescapes; recognition/hygiene layering
across C1/C2/C14/C15.
Carried from v10: the unified canonical-row rule itself (one test, no branch seams) with
its rendered-label normalization of inline links/images, HTML tags, HTML entities,
emphasis/code/strike delimiters, and leading/trailing-only underscore stripping.
Carried from v9: indent/whitespace tolerance in the canonical test; _md_tables
renderer-faithful table parse (outer pipes optional) in C14 and C15; C15
count-before-validate on exclusion rows; C3 context-independent fixed-point reachability
with the stay-green cycle-with-exit case; word-bounded rule markers; C16 result-reason
invariant anchors, one-identity, unconditional pld_rate, and review-record claims; C15
Sec.6-Sec.7 bounding and R2 partition assertion; C12 own-fragment /
quoted-enumeration-run exemption with line-wide quote pairing; two-polarity self-test.

RATIFIED DEBT (Director, 2026-07-25): full semantic contradiction detection over free prose
is beyond these checks and is not claimed. It arrives with defs/ single-source generation at
build and is verified at HUG-G002. Until then every check's PASS message states exactly what
was proven and no more.

Modes:
  python consistency_checks.py               run all checks; exit 1 on any FAIL
  python consistency_checks.py --self-test   negative-test every check, including adversarial
                                             mutations in the reviewer's own reproduction
                                             forms (additions, replacements, and relocations,
                                             not only deletions); exit 1 if any mutation is
                                             missed.
"""
import html
import re
import shutil
import sys
import tempfile
from pathlib import Path

# v19 (build phase): repo-relative paths. The packet-era artifact filenames carried
# the document version in the name; in the repo the version lives in the document's
# own title line, which is where C16's one-identity check already reads it from.
DOCS = {
    "brief": "docs/concept_brief.md",
    "conops": "docs/conops.md",
    "reqs": "docs/requirements.md",
    "dict": "docs/tlm_cmd_dictionary.md",
    "fmea": "docs/fmea.md",
    "schema": "defs/replay_schema.md",
}

NUMWORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
           "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
           "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
           "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
# Lexical bound (stated in claims per G001-03 F-10): word-number recognition covers
# one..twenty; counts outside that domain are recognized in digit form only.

# The review-record claim the brief must carry for THIS baseline (G001-04 F-06). These
# constants are part of the versioned check set: a future round updates them with the docs.
REVIEW_STATE = ("seventeen adversarial review rounds complete", "all 97 findings")

# The 22 FMEA worksheet rows of the HUG-G001 record: the rows the v0.1 fault set was
# selected from and the campaign was planned and executed on (owner ruling D-020). A
# row added later is not one of them; FMEA Sec. 6.3 records it instead of the screen.
G001_FMEA_ROWS = tuple([f"FM-EPS-{i:02d}" for i in range(1, 12)]
                       + [f"FM-CDH-{i:02d}" for i in range(1, 6)]
                       + [f"FM-GND-{i:02d}" for i in range(1, 7)])


def load(art):
    art = Path(art)
    return ({k: (art / v).read_text(encoding="utf-8") for k, v in DOCS.items()},
            {k: (art / v).read_bytes() for k, v in DOCS.items()})


def _tables_with_lines(lines):
    """THE table parser — one fence-aware parser under C1, C14, and C15 (G001-11 F-03).
    Bounded Markdown pipe tables, parsed as renderers treat them (G001-07 F-03): a table
    is a header line containing '|' immediately followed by a delimiter line of
    dashes/pipes/colons; its body is every subsequent non-blank line containing '|'.
    Outer pipes are OPTIONAL on every row. Fenced code regions are excluded from table
    detection (G001-10 F-03) — fenced content renders as code, never as a table.
    Returns a list of (header_index, header_line, [(index, body_line), ...]) with
    0-based indices into lines."""
    mask = _fenced_mask(lines)
    tables, i = [], 0
    while i < len(lines):
        if (not mask[i] and "|" in lines[i] and i + 1 < len(lines) and not mask[i + 1]
                and "-" in lines[i + 1] and re.fullmatch(r"[\s|:\-]+", lines[i + 1])):
            body, j = [], i + 2
            while j < len(lines) and lines[j].strip() and "|" in lines[j] and not mask[j]:
                body.append((j, lines[j]))
                j += 1
            tables.append((i, lines[i], body))
            i = j
        else:
            i += 1
    return tables


def _md_tables(lines):
    """View of _tables_with_lines for callers that need (header_line, [body_lines]) —
    the same single fence-aware parse (G001-11 F-03)."""
    return [(hdr, [ln for _, ln in body]) for _, hdr, body in _tables_with_lines(lines)]


def _cells(row):
    """Split a Markdown table row into stripped cells at renderer-significant separators:
    outer pipes optional; a pipe is a separator only when preceded by an EVEN run of
    backslashes - escape status is decided by the PARITY of the complete immediately
    preceding backslash run (G001-11 F-04; G001-12 F-02), as CommonMark's escape rule
    composes: an odd run leaves the pipe escaped (cell content); an even run, including
    zero, leaves it a boundary."""
    parts, cur, bs = [], [], 0
    for ch in row.strip():
        if ch == "\\":
            cur.append(ch)
            bs += 1
        elif ch == "|" and bs % 2 == 0:
            parts.append("".join(cur))
            cur = []
            bs = 0
        else:
            cur.append(ch)
            bs = 0
    parts.append("".join(cur))
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [c.strip() for c in parts]


def _fenced_mask(lines):
    """Boolean mask over lines: True for lines inside fenced code blocks (``` or ~~~),
    fences included (G001-10 F-03: fenced content renders as literal text, never as a
    table). CommonMark boundaries (G001-12 F-03): an OPENING fence is a run of >=3
    backticks or tildes indented AT MOST 3 spaces - a 4+-space-indented run is an
    indented code line, not a fence opener, and opens nothing; a backtick fence's info
    string may not contain a backtick. The CLOSING fence is a run of the same character,
    at least the opening run's length, indented at most 3 spaces, with nothing else on
    the line."""
    mask = [False] * len(lines)
    fence = None
    for i, ln in enumerate(lines):
        indent = len(ln) - len(ln.lstrip(" "))
        s = ln.strip()
        if fence is None:
            m = re.match(r"(`{3,}|~{3,})(.*)$", s)
            if m and indent <= 3 and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                mask[i] = True
        else:
            mask[i] = True
            if indent <= 3 and re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + ",}", s):
                fence = None
    return mask


def _table_rows(text):
    """Header and body rows of RENDERED Markdown tables (G001-10 F-03), yielded as
    (1-based line number, raw line) — a view of the same single fence-aware parser
    (G001-11 F-03). The delimiter line renders as structure, not text, and is not
    yielded."""
    lines = text.splitlines()
    for hi, hdr, body in _tables_with_lines(lines):
        yield (hi + 1, hdr)
        for j, ln in body:
            yield (j + 1, ln)


def _doc_rows(text):
    """Body-row cell lists of every rendered table in text — the shared parsed-table
    representation for definition-row and requirement-row consumers (G001-12 F-01).
    Every consumer that used to read start-of-line regular expressions reads this view
    instead, so the fence mask and the escape-parity cell splitter govern all of them:
    a definitions table relocated into fenced code vanishes from the rendered record
    and from every consumer together."""
    for _hi, _hdr, body in _tables_with_lines(text.splitlines()):
        for _j, ln in body:
            yield _cells(ln)


REFDEF = re.compile(r"(?m)^ {0,3}\[([^\]]+)\]:\s*\S")


def _norm_label(s):
    """CommonMark reference-label matching normalization (G001-11 F-02): trim, collapse
    internal whitespace runs to a single space, case-fold — the renderer's full matching
    rule, not a subset of it."""
    return re.sub(r"\s+", " ", s.strip()).casefold()


def _ref_labels(text):
    """Labels of CommonMark link reference definitions in this document, normalized with
    the renderer's full matching rule (G001-10 F-02; G001-11 F-02): reference-style links
    resolve to their labels only when a matching definition exists, exactly as a renderer
    resolves them."""
    return {_norm_label(m.group(1)) for m in REFDEF.finditer(text)}


IDFORMS = (r"FM-(?:EPS|CDH|GND)-\d{2}|HUG-[A-Z]+-\d{3}|(?:EPS|PLD|CDH|ADM)_[A-Z0-9_]+"
           r"|CMD_[A-Z0-9_]+|NEED-\d{2}|CON-\d{2}|ASM-\d{2}")
IDPLAIN = re.compile(r"(?:" + IDFORMS + r")")


def _strip_inline(s, refs=frozenset()):
    """RENDERED-LABEL normalizer for a candidate identifier cell (G001-08 F-03; G001-09
    F-03/F-04; G001-10 F-02): resolve inline Markdown links and images to their labels;
    resolve REFERENCE-STYLE links - full [text][label], collapsed [text][], shortcut
    [text] - each only when its label has a matching definition in refs (the document's
    link reference definitions), labels matched with the renderer's full rule - trim,
    internal-whitespace collapse, case-fold (G001-11 F-02); strip inline HTML tags; decode HTML
    entities; remove emphasis/code/strike delimiters; apply CommonMark BACKSLASH
    UNESCAPES (a backslash before ASCII punctuation renders as the punctuation alone);
    and strip only LEADING/TRAILING underscores - interior underscores are identifier
    characters (EPS_BATT_V), never emphasis delimiters, per CommonMark's intra-word
    rule."""
    s = s.strip()
    s = _resolve_inline_links(s)

    def _ref(m):
        label = _norm_label(m.group(2) or m.group(1))
        return m.group(1) if label in refs else m.group(0)
    s = re.sub(r"!?\[([^\]]*)\]\[([^\]]*)\]", _ref, s)
    s = re.sub(r"!?\[([^\]]*)\](?![\[(])",
               lambda m: m.group(1) if _norm_label(m.group(1)) in refs else m.group(0), s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[*`~]", "", s)
    s = re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", s)
    # G001-12 F-02: strip trailing escape residue (whitespace/backslash runs) from the
    # candidate label. Deliberately OVER-INCLUSIVE in the safe direction: a first cell
    # rendering as an identifier plus stray residue is treated as that identifier, which
    # can only add flags and counts - the direction is demonstrated by executed red cases,
    # not asserted from reasoning (the v12 lookbehind residual claim was refuted).
    s = re.sub(r"[\s\\]+$", "", s)
    return s.strip().strip("_")


def _resolve_inline_links(s):
    """Resolve inline Markdown links and images [label](destination) to their labels with
    BALANCED-PARENTHESIS, backslash-escape-aware destinations (G001-12 F-04), per
    CommonMark: a destination may contain nested balanced parentheses and escaped
    characters, so the resolver walks it with a depth counter instead of stopping at the
    first closing parenthesis."""
    out = []
    opener = re.compile(r"!?\[([^\]]*)\]\(")
    i, n = 0, len(s)
    while i < n:
        m = opener.match(s, i)
        if not m:
            out.append(s[i])
            i += 1
            continue
        j, depth, esc = m.end(), 1, False
        while j < n and depth:
            ch = s[j]
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            j += 1
        if depth == 0:
            out.append(m.group(1))
            i = j
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def c1(text, raw):
    bad = [DOCS[k] for k in raw if b"\r\n" in raw[k]]
    # ONE unified canonical-row rule, TABLE-ROW SCOPED (G001-07 F-03; G001-08 F-02/F-03;
    # G001-09 F-02/F-03/F-04; G001-10 F-02/F-03): on every header and body row of every
    # rendered pipe table (fenced code excluded), take the first cell with outer pipes
    # optional and normalize it as a renderer would display it - including reference-style
    # links and backslash escapes. If it renders as a known ID form, the row must be
    # canonical - leading '| ' and the plain spelling - else it is a defect. The rule
    # governs table rows, as the Director ratified (D0-13): an identifier-and-pipe line in
    # prose or in a code fence renders as text or code, not as a table row, and is not
    # flagged.
    noncanon = []
    for k, t in text.items():
        refs = _ref_labels(t)
        for i, ln in _table_rows(t):
            first = _cells(ln)[0]
            norm = _strip_inline(first, refs)
            if IDPLAIN.fullmatch(norm) and not (ln.startswith("| ") and first == norm):
                noncanon.append((DOCS[k], i))
    ok = not bad and not noncanon
    return (ok, f"CRLF found in: {bad}; non-canonical identifier table rows (pipe-less, indented, formatted, "
                f"link-wrapped, reference-linked, or escape-disguised): {noncanon}" if not ok
            else "0 CRLF pairs across 6 files; 0 non-canonical identifier rows under the table-row-scoped canonical rule "
                 "(rendered-label normalization incl. reference links and backslash escapes; G001-07 F-03 through "
                 "G001-10 F-02/F-03) - claim bounded to the record's table grammar; renderer fidelity beyond it is "
                 "ratified debt (G001-13 ruling)")


def c2(text, raw):
    # Definition rows are recognized as they RENDER (G001-10 F-02): the first cell of every
    # requirements table row, normalized by the rendered-label normalizer with the
    # document's reference definitions, counts as a definition when it renders as a
    # requirement ID - so a disguised duplicate definition row trips the uniqueness test
    # here while C1 flags its spelling.
    _reqrefs = _ref_labels(text["reqs"])
    defs = [n for _, _ln in _table_rows(text["reqs"])
            for n in [_strip_inline(_cells(_ln)[0], _reqrefs)]
            if re.fullmatch(r"HUG-[A-Z]+-\d{3}", n)]
    dupes = sorted({d for d in defs if defs.count(d) > 1})
    referenced = set()
    for k in ("fmea", "conops", "brief", "schema", "dict"):
        referenced |= set(re.findall(r"\b(HUG-[A-Z]+-\d{3})\b", text[k]))
    # slash-abbreviated citations (e.g. HUG-UI-002/003/005) expand and validate per suffix (G001-03 F-12)
    slash_bad = []
    n_slash = 0
    for k in DOCS:
        for m in re.finditer(r"\b(HUG-[A-Z]+)-(\d{3})((?:/\d{3})+)", text[k]):
            for sfx in m.group(3).strip("/").split("/"):
                n_slash += 1
                if f"{m.group(1)}-{sfx}" not in defs:
                    slash_bad.append((DOCS[k], f"{m.group(1)}-.../{sfx}"))
    undefined = sorted(referenced - set(defs))
    ok = not dupes and not undefined and not slash_bad
    return (ok, f"duplicate IDs: {dupes}; undefined refs: {undefined}; bad slash suffixes: {slash_bad}" if not ok
            else f"{len(defs)} identifier-shaped requirement rows across recognized tables (ownership not established - "
                 f"D0-17 item 2), all unique; {len(referenced)} distinct cited + {n_slash} slash-expanded suffixes resolve "
                 f"in the scanned classes (requirement-parent tokens in trace cells excluded - D0-17 item 4)")


def c3(text, raw):
    # G001-12 F-01: definition and requirement rows come from the shared parsed-table
    # representation, not start-of-line regexes - a fenced-away table vanishes here too.
    defined = {cs[0] for cs in _doc_rows(text["conops"])
               if cs and re.fullmatch(r"NEED-\d{2}|CON-\d{2}|ASM-\d{2}", cs[0])}
    cited = set(re.findall(r"\b((?:NEED|CON|ASM)-\d{2})\b", text["reqs"]))
    dangling = sorted(cited - defined)
    uncovered = sorted(defined - cited)
    # G001-04 F-05: lineage is a graph property, not token presence. G001-05 F-04: computed
    # as a context-independent FIXED-POINT reachability pass - rows citing a NEED seed the
    # reachable set, which propagates backward through parent edges until stable. There is no
    # recursion and no cache, so no traversal order exists for a result to depend on; a cycle
    # is credited only if some row on it independently reaches a NEED (which makes the credit
    # genuine: an acyclic path exists through that exit).
    needs, parents = {}, {}
    for cs in _doc_rows(text["reqs"]):
        if cs and len(cs) >= 2 and re.fullmatch(r"HUG-[A-Z]+-\d{3}", cs[0]):
            needs[cs[0]] = set(re.findall(r"\bNEED-\d{2}\b", cs[-1]))
            parents[cs[0]] = set(re.findall(r"\bHUG-[A-Z]+-\d{3}\b", cs[-1]))
    self_refs = sorted(r for r in parents if r in parents[r])
    reach = {r: bool(needs[r]) for r in parents}
    changed = True
    while changed:
        changed = False
        for r in parents:
            if not reach[r] and any(reach.get(p, False) for p in parents[r] if p != r):
                reach[r] = True
                changed = True
    no_lineage = sorted(r for r in parents if not reach[r])
    ok = not dangling and not uncovered and not self_refs and not no_lineage
    return (ok, f"cited-but-undefined: {dangling}; defined-but-uncited: {uncovered}; "
                f"self-referencing rows: {self_refs}; rows with no acyclic path to a NEED: {no_lineage}" if not ok
            else f"{len(defined)} defined IDs, all cited; NEED/CON/ASM citations resolve (requirement-parent tokens NOT "
                 f"validated against the definition set - D0-17 item 4); {len(parents)} rows: fixed-point "
                 f"reachability - no self-reference, no cycle credited without a NEED exit, every row reaches a NEED "
                 f"(order-independent by form; G001-04 F-05, G001-05 F-04)")


def c4(text, raw):
    # G001-12 F-01: definitions from the shared parsed-table representation.
    dict_tlm = {cs[0] for cs in _doc_rows(text["dict"])
                if cs and re.fullmatch(r"(?:EPS|PLD|CDH|ADM)_[A-Z0-9_]+", cs[0])}
    used = set()
    for k in ("fmea", "conops", "schema", "reqs", "brief"):
        used |= set(re.findall(r"\b((?:EPS|PLD|CDH|ADM)_[A-Z0-9_]+)\b", text[k]))
    unknown = sorted(used - dict_tlm)
    # normative lowercase members in the replay schema map via the bijective transform (G001-03 F-11)
    lower_used = set(re.findall(r"\b((?:eps|pld|cdh|adm)_[a-z0-9_]+)\b", text["schema"]))
    lower_bad = sorted(t for t in lower_used if t.upper() not in dict_tlm)
    ok = not unknown and not lower_bad
    return (ok, f"unknown mnemonics: {unknown}; unmapped lowercase members: {lower_bad}" if not ok
            else f"{len(dict_tlm)} telemetry-shaped rows recognized across the dictionary's tables (ownership not "
                 f"established - D0-17 item 2); {len(used)} uppercase uses + {len(lower_used)} lowercase schema members; "
                 f"all resolve via the bijective transform")


def _count_scan(text, noun_pat, expected):
    """Find 'N <noun>' statements (digit or word), N != expected -> contradictions."""
    hits = []
    for k, t in text.items():
        for m in re.finditer(r"(?<![-.\d])\b(\d+)\s+" + noun_pat, t, re.I):
            if int(m.group(1)) != expected:
                hits.append((DOCS[k], m.group(0)))
        for m in re.finditer(r"\b(" + "|".join(NUMWORD) + r")\s+" + noun_pat, t, re.I):
            if NUMWORD[m.group(1).lower()] != expected:
                hits.append((DOCS[k], m.group(0)))
    return hits


def c5(text, raw):
    # G001-12 F-01: definition rows from the shared parsed-table representation.
    rows = [cs[0] for cs in _doc_rows(text["dict"])
            if cs and re.fullmatch(r"(?:EPS|PLD|CDH|ADM)_[A-Z0-9_]+", cs[0])]
    dupes = sorted({r for r in rows if rows.count(r) > 1})
    contra = _count_scan(text, r"(?:telemetry|dictionary)\s+points?\b", 16)
    ok = len(rows) == 16 and not dupes and not contra
    return (ok, f"rows={len(rows)} dupes={dupes} count-contradictions={contra}")


def c6(text, raw):
    # G001-12 F-01: definition rows from the shared parsed-table representation.
    rows = [cs[0] for cs in _doc_rows(text["dict"])
            if cs and re.fullmatch(r"CMD_[A-Z0-9_]+", cs[0])]
    dupes = sorted({r for r in rows if rows.count(r) > 1})
    used = set()
    for k in ("fmea", "conops", "reqs", "brief", "schema"):
        used |= set(re.findall(r"\b(CMD_[A-Z0-9_]+)\b", text[k]))
    unknown = sorted(used - set(rows))
    ok = len(rows) == 5 and not dupes and not unknown
    return (ok, f"rows={len(rows)} dupes={dupes} unknown-cited={unknown}")


def c7(text, raw):
    anchors_ok = ("## 2. Commands (5)" in text["dict"] and "Commands (five)" in text["brief"]
                  and "all five v0.1 commands" in text["reqs"] and "five-command set" in text["conops"])
    contra = _count_scan(text, r"commands?\b", 5)
    header = [(DOCS[k], m) for k, t in text.items()
              for m in re.findall(r"Commands \((\d+)\)", t) if m != "5"]
    ok = anchors_ok and not contra and not header
    return (ok, f"anchors={anchors_ok}; count-contradictions={contra + header}" if not ok
            else "4 anchors present; bounded scan finds no conflicting command-count statement")


def c8(text, raw):
    pairs = [("reqs", "LOW_POWER mode when SoC falls below 30%"),
             ("reqs", "SAFE mode when SoC falls below 20%"),
             ("reqs", "below 35% for target NOMINAL or below 25% for target LOW_POWER"),
             ("reqs", "SoC is below 40%"),
             ("dict", "< 35% for NOMINAL or < 25% for LOW_POWER"),
             ("dict", "EPS_BATT_SOC < 40%"),
             ("dict", "20 / 35 / n/a / n/a"),
             ("fmea", "recovery floors 35%/25%"),
             ("fmea", "30%/20%"),
             ("conops", "LOW_POWER at 30% SoC → SAFE at 20%"),
             ("conops", "below 40% SoC"),
             ("brief", "LOW_POWER 30%")]
    missing = [(k, s) for k, s in pairs if s not in text[k]]
    ALLOWED = {20.0, 25.0, 30.0, 35.0, 40.0}
    contra = [(DOCS[k], m.group(0)) for k, t in text.items()
              for m in re.finditer(r"(?:below|<)\s*(\d+(?:\.\d+)?)\s*%", t)
              if float(m.group(1)) not in ALLOWED]
    ok = not missing and not contra
    return (ok, f"missing anchors: {missing}; out-of-set thresholds: {contra}" if not ok
            else f"{len(pairs)} anchors present; bounded scan: every below/< percentage is in the ratified set")


ENVELOPE = {
    "capacity_Wh":  (38.0,  [r"(\d+(?:\.\d+)?)\s*Wh\b", r"(\d+(?:\.\d+)?)\s*watt-hours?\b"]),
    "bus_V":        (5.0,   [r"(\d+(?:\.\d+)?) V (?:regulated )?bus\b", r"bus voltage (?:of )?(\d+(?:\.\d+)?) V"]),
    "array_W":      (17.0,  [r"(\d+(?:\.\d+)?) W peak (?:array|combined)\b",
                             r"array peak generation (?:of )?(\d+(?:\.\d+)?) W",
                             r"peak generation of (\d+(?:\.\d+)?) W",
                             r"(\d+(?:\.\d+)?) W array\b"]),
    "string_W":     (8.5,   [r"(\d+(?:\.\d+)?) W strings?\b", r"2\s*[×x]\s*(\d+(?:\.\d+)?) W"]),
    "bus_load_W":   (4.0,   [r"(\d+(?:\.\d+)?) W (?:nominal )?bus load", r"bus load (?:of )?(\d+(?:\.\d+)?) W",
                             r"\((\d+(?:\.\d+)?) W bus[,)]"]),
    "payload_W":    (3.0,   [r"(\d+(?:\.\d+)?) W payload\b", r"payload load (?:of )?(\d+(?:\.\d+)?) W"]),
    "efficiency":   (0.95,  [r"efficienc(?:y|ies)\D{0,25}?(0\.\d+)", r"(0\.\d+) charge"]),
}


def c9(text, raw):
    contra, n = [], 0
    for k, t in text.items():
        for q, (auth, pats) in ENVELOPE.items():
            for pat in pats:
                for m in re.finditer(pat, t):
                    n += 1
                    if abs(float(m.group(1)) - auth) > 1e-9:
                        contra.append((DOCS[k], q, m.group(0)))
    OWNER = {"reqs": [q for q in ENVELOPE if q != "string_W"], "fmea": list(ENVELOPE)}
    missing = [(k, q) for k, qs in OWNER.items() for q in qs
               if not any(re.search(p, text[k]) for p in ENVELOPE[q][1])]
    ok = not contra and not missing
    return (ok, f"contradictions: {contra}; missing-from-owner-doc: {missing}" if not ok
            else f"recognized-phrasing sweep, 7 quantities, {n} occurrences, all authoritative; owner docs complete "
                 f"(NOT semantic detection — that is ratified debt, due with defs/ generation at HUG-G002)")


def c10(text, raw):
    ok = "6.8 / 7.2 / 8.3 / 8.5" in text["dict"]
    return (ok, "battery-voltage limit anchor present in dictionary (anchor presence only)" if ok
            else "battery-voltage limit anchor NOT found")


def c11(text, raw):
    anchors = [("dict", "no advance for 10 s → YL; 30 s → RL"),
               ("conops", "yellow at 10 s and red at 30 s")]
    bad = [(k, s) for k, s in anchors if s not in text[k]]
    return (not bad, f"missing normative anchors: {bad}" if bad
            else "normative staleness anchors present in dictionary and CONOPS (the two docs this check reads)")


FORBIDDEN = ["flown", "real tle", "control console", "mission control"]
RULE_MARKERS = ["never", "no claim", "shall not", "prohibit", "disallow"]


def _has_marker(s):
    # G001-05 F-05: markers match as bounded words, never substrings - "nevertheless" is not
    # "never". A letter on either side breaks the match, so an inflected form ("prohibits",
    # "disallowed") must be listed explicitly to count; the strictness errs toward flagging.
    return any(re.search(r"(?<![a-z])" + re.escape(mk) + r"(?![a-z])", s) for mk in RULE_MARKERS)


def c12(text, raw):
    # G001-03 F-09: fragments split on ; . ! ? dashes AND commas/colons. G001-04 F-04: a quoted
    # occurrence is exempt only if its OWN fragment carries a rule marker, or the marker is
    # reachable backward through an uninterrupted run of quoted-enumeration fragments (fragments
    # containing nothing but quoted phrases and connectors). A marker in an unrelated earlier
    # fragment on the same physical line exempts nothing.
    viol = []
    for k, t in text.items():
        for i, line in enumerate(t.splitlines(), 1):
            cf = line.casefold()
            spans, start = [], 0
            for m in re.finditer(r"[;.!?,:]|—|–", line):
                spans.append((start, m.start()))
                start = m.end()
            spans.append((start, len(line)))
            # quote spans pair LINE-WIDE first, because punctuation inside quotes ("...,")
            # splits fragments mid-quotation and would defeat fragment-local pairing
            qspans = [(m.start(), m.end()) for m in re.finditer(r'"[^"]*"|“[^”]*”', cf)]

            def enum_only(j):
                a, b = spans[j]
                residue = "".join(ch for ii, ch in enumerate(cf[a:b], a)
                                  if not any(qa <= ii < qb for qa, qb in qspans))
                return re.fullmatch(r"[\s|*_>\-–—]*(?:(?:or|and|nor)[\s|*_>\-–—]*)*", residue) is not None

            for p in FORBIDDEN:
                for m in re.finditer(re.escape(p), cf):
                    idx = m.start()
                    j = next((jj for jj, (a, b) in enumerate(spans) if a <= idx < b), len(spans) - 1)
                    a, b = spans[j]
                    marked = _has_marker(cf[a:b])
                    quoted = any(qa < idx < qb for qa, qb in qspans)
                    run_ok = False
                    if quoted and not marked and enum_only(j):
                        for q in range(j - 1, -1, -1):
                            qa, qb = spans[q]
                            if _has_marker(cf[qa:qb]):
                                run_ok = True
                                break
                            if not enum_only(q):
                                break
                    if not (marked or run_ok):
                        viol.append((DOCS[k], i, p))
    return (not viol, f"violations: {viol}" if viol
            else "0 forbidden-phrase occurrences outside rule scope (word-bounded marker in own fragment — G001-05 F-05 — or "
                 "quoted within an unbroken quoted-enumeration run back to the marker's fragment — G001-04 F-04; "
                 "proposition-level binding remains within the ratified debt)")


def c13(text, raw):
    eustis = [DOCS[k] for k, t in text.items() if "GS-EUSTIS" in t]
    raven = all("GS-RAVENSROOST" in text[k] for k in ("brief", "conops", "dict", "schema"))
    return (not eustis and raven, f"GS-EUSTIS found in {eustis}; RAVENSROOST coverage={raven}")


def c14(text, raw):
    # parse bounded Markdown tables (outer pipes optional per row - G001-07 F-03); an FM
    # definition row counts only inside a table whose header is the FMEA worksheet header
    # (G001-02 F-13). The Sec. 6.2 exclusion table is a recognized citation location
    # (G001-04 F-02); FM-row lines anywhere else are orphans.
    in_table, excl_rows = [], []
    _fmrefs = _ref_labels(text["fmea"])
    for hdr, body in _md_tables(text["fmea"].splitlines()):
        # G001-08 F-03 / G001-10 F-02: recognize identifiers as they RENDER - inline
        # formatting stripped, reference links and backslash escapes resolved - so a
        # disguised duplicate row is counted (and C1 flags the spelling itself)
        ids = [_strip_inline(cs[0], _fmrefs) for cs in map(_cells, body)
               if cs and re.fullmatch(r"FM-(?:EPS|CDH|GND)-\d{2}", _strip_inline(cs[0], _fmrefs))]
        if "Failure mode (cause)" in hdr:
            in_table += ids
        elif "First failed criterion" in hdr:
            excl_rows += ids
    everywhere = re.findall(r"\b(FM-(?:EPS|CDH|GND)-\d{2})\b", text["fmea"])
    row_lines = re.findall(r"^\|? ?(FM-(?:EPS|CDH|GND)-\d{2}) \|", text["fmea"], re.M)
    orphans = sorted(set(row_lines) - set(in_table) - set(excl_rows))
    dupes = sorted({i for i in in_table if in_table.count(i) > 1})
    dangling = sorted(set(everywhere) - set(in_table))
    # D-020: the 22 HUG-G001 rows are named, not counted - a count would accept a
    # deleted HUG-G001 row as soon as one row had been added after the selection
    absent = [i for i in G001_FMEA_ROWS if i not in in_table]
    ok = not orphans and not dupes and not dangling and not absent
    return (ok, f"rows-in-worksheet-tables={len(in_table)} HUG-G001-rows-absent={absent} orphaned-FM-row-lines={orphans} dupes={dupes} dangling-citations={dangling}")


def c15(text, raw):
    # G001-12 F-01: the HUG-EPS-004 row comes from the shared parsed-table representation.
    row = next((cs[1] for cs in _doc_rows(text["reqs"])
                if cs and len(cs) >= 2 and cs[0] == "HUG-EPS-004"), "")
    req_ok = all(s in row for s in ["array-string output forced to zero", "stuck-on load of 2.0 W",
                                    "housekeeping telemetry generation halt"])
    fm = text["fmea"]
    _fmrefs = _ref_labels(fm)  # G001-10 F-02: recognition resolves reference-style links
    # G001-04 F-03: parse ONLY between the Sec. 6 and Sec. 7 headings
    m6 = re.search(r"^## 6\. ", fm, re.M)
    m7 = re.search(r"^## 7\. ", fm, re.M)
    bounded = bool(m6 and m7 and m6.start() < m7.start())
    sec6 = fm[m6.end():m7.start()] if bounded else ""
    fault_cells, id_rows, post_rows = [], [], []
    for hdr, body in _md_tables(sec6.splitlines()):
        if "Injected fault" in hdr:
            fault_cells = [cs for cs in map(_cells, body) if cs and re.match(r"\([abc]\) ", cs[0])]
        elif "First failed criterion" in hdr:
            for cs in map(_cells, body):
                if cs and re.fullmatch(r"FM-(?:EPS|CDH|GND)-\d{2}", _strip_inline(cs[0], _fmrefs)):
                    id_rows.append(cs)
        elif "Selection status" in hdr:
            # D-020: Sec. 6.3, the R2 rows added after the selection. Parsed and
            # validated exactly as the exclusion rows are: counted before validation.
            for cs in map(_cells, body):
                if cs and re.fullmatch(r"FM-(?:EPS|CDH|GND)-\d{2}", _strip_inline(cs[0], _fmrefs)):
                    post_rows.append(cs)
    # G001-05 F-06 + G001-06 F-02 + G001-07 F-03 + G001-08 F-03: EVERY row whose first cell
    # RENDERS as an FM identifier counts BEFORE any other cell is validated - the table
    # parse is renderer-faithful (outer pipes optional) and so is identifier recognition
    # (inline formatting stripped). Duplicate IDs, malformed rows, and formatted identifier
    # cells are separate defects rejected ahead of the mapping.
    excl_ids = [_strip_inline(cs[0], _fmrefs) for cs in id_rows]
    excl_dupes = sorted({i for i in excl_ids if excl_ids.count(i) > 1})
    malformed, excl_raw = [], []
    for cs in id_rows:
        sid = _strip_inline(cs[0], _fmrefs)
        rm = re.fullmatch(r"(R[123]) \(([IV]+)/([A-E])\)", cs[1]) if len(cs) >= 4 else None
        cm = re.fullmatch(r"\([a-e]\)", cs[2]) if len(cs) >= 4 else None
        if rm and cm and cs[0] == sid:
            excl_raw.append((sid, (rm.group(1), rm.group(2), rm.group(3))))
        else:
            malformed.append(sid)
    excl = dict(excl_raw)
    post_ids = [_strip_inline(cs[0], _fmrefs) for cs in post_rows]
    post_dupes = sorted({i for i in post_ids if post_ids.count(i) > 1})
    post_malformed, post_raw = [], []
    for cs in post_rows:
        sid = _strip_inline(cs[0], _fmrefs)
        rm = re.fullmatch(r"(R[123]) \(([IV]+)/([A-E])\)", cs[1]) if len(cs) >= 4 else None
        if rm and cs[0] == sid:
            post_raw.append((sid, (rm.group(1), rm.group(2), rm.group(3))))
        else:
            post_malformed.append(sid)
    post = dict(post_raw)
    expected = [("(a) Array string output zero", "FM-EPS-01"),
                ("(b) Stuck-on load, 2.0 W", "FM-EPS-08"),
                ("(c) Housekeeping telemetry generation halt", "FM-CDH-01")]
    fmea_ok = (len(fault_cells) == 3
               and all(any(cs[0] == e0 and len(cs) > 1 and cs[1] == e1 for cs in fault_cells) for e0, e1 in expected))
    sel = {}
    for cs in fault_cells:
        if len(cs) >= 3 and re.fullmatch(r"FM-(?:EPS|CDH|GND)-\d{2}", cs[1]):
            rm = re.fullmatch(r"(R[123]) \(([IV]+)/([A-E])\)", cs[2])
            if rm:
                sel[cs[1]] = (rm.group(1), rm.group(2), rm.group(3))
    # G001-04 F-02 mechanization: selected + excluded must exactly partition the worksheet R2
    # set, with severity/likelihood agreeing row-for-row.
    ws = {}
    for hdr, body in _md_tables(fm.splitlines()):
        if "Failure mode (cause)" in hdr:
            for cs in map(_cells, body):
                if cs and re.fullmatch(r"FM-(?:EPS|CDH|GND)-\d{2}", _strip_inline(cs[0], _fmrefs)):
                    ridx = next((ii for ii, c in enumerate(cs) if re.fullmatch(r"R[123]", c)), None)
                    if ridx is not None:
                        ws[_strip_inline(cs[0], _fmrefs)] = (cs[ridx], cs[ridx - 2], cs[ridx - 1])
    # D-020: the partition is of the HUG-G001 R2 rows; the R2 rows outside that record
    # are exactly the Sec. 6.3 rows. Every R2 worksheet row is in exactly one table.
    g001 = set(G001_FMEA_ROWS)
    r2 = {i for i, v in ws.items() if v[0] == "R2" and i in g001}
    r2_later = {i for i, v in ws.items() if v[0] == "R2" and i not in g001}
    overlap = sorted(set(sel) & set(excl))
    missing = sorted(r2 - set(sel) - set(excl))
    extra = sorted((set(sel) | set(excl)) - r2)
    post_missing = sorted(r2_later - set(post))
    post_extra = sorted(set(post) - r2_later)
    mismatch = sorted([i for i in sel if ws.get(i) != sel[i]] + [i for i in excl if ws.get(i) != excl[i]]
                      + [i for i in post if ws.get(i) != post[i]])
    ok = (req_ok and bounded and fmea_ok and len(id_rows) == 13 and not excl_dupes and not malformed
          and not overlap and not missing and not extra and not mismatch
          and not post_dupes and not post_malformed and not post_missing and not post_extra)
    return (ok, f"HUG-EPS-004 row clauses: {req_ok}; Sec6-bounded: {bounded}; selected rows parsed: {len(fault_cells)}/3 "
                f"({fmea_ok}); ID-bearing exclusion rows: {len(id_rows)}/13, duplicate IDs: {excl_dupes}, malformed rows: "
                f"{malformed}; partition errors — overlap: {overlap}, unmapped HUG-G001 R2: {missing}, "
                f"non-HUG-G001-R2 listed: {extra}, sev/lik disagree: {mismatch}; Sec. 6.3 — duplicate IDs: "
                f"{post_dupes}, malformed rows: {post_malformed}, later R2 rows unlisted: {post_missing}, "
                f"listed but not a later R2 row: {post_extra}" if not ok
            else f"the HUG-EPS-004 row (located by spelling across recognized tables; ownership not established - D0-17 "
                 f"item 2) carries all three fault clauses; Sec. 6 tables parsed WITHIN the Sec.6→Sec.7 bounds "
                 f"(G001-04 F-03) with a grammar-bounded Markdown parse — outer pipes optional (G001-07 F-03), fence-aware "
                 f"(G001-11 F-03), escaped-pipe cells intact (G001-11 F-04); renderer fidelity beyond the grammar is ratified "
                 f"debt (G001-13 ruling): 3 selected + 13 "
                 f"ID-bearing exclusion rows, counted before any cell validation — no duplicates, no malformed rows (G001-05 "
                 f"F-06; G001-06 F-02) — exactly partition the {len(r2)} HUG-G001 worksheet R2 rows, every exclusion cites "
                 f"a criterion (a)-(e), sev/lik agree row-for-row (G001-04 F-02); the Sec. 6.3 table lists exactly the "
                 f"{len(r2_later)} R2 row(s) added after the selection, each once and agreeing with its worksheet row (D-020)")


def c16(text, raw):
    # G001-04 F-01: the interface has ONE version identity — title version, title schema
    # number, and the required meta.schema member value must be equal.
    tm = re.search(r"Interface Definition, v(\d+\.\d+) \(schema (\d+\.\d+)\)", text["schema"])
    sm = re.search(r"\| `schema` \| required \| string \| `\"(\d+\.\d+)\"` for this definition", text["schema"])
    ids = {tm.group(1), tm.group(2), sm.group(1)} if tm and sm else set()
    id_ok = len(ids) == 1
    # G001-04 F-07: the pld_rate conformance bound is unconditional in the Sec. 7 contract
    sec7 = text["schema"].split("## 7.", 1)[-1].split("## 8.", 1)[0]
    pr = re.search(r"`pld_rate`[^;]*", sec7)
    pld_ok = bool(pr) and "[0.1, 10]" in pr.group(0) and "when" not in pr.group(0)
    # G001-05 F-03: the command-event result-reason invariant is stated in Sec. 6 and enforced
    # as a Sec. 7 cross-field rule (anchor presence in both places).
    inv6 = 'Result–reason invariant (normative, per G001-05 F-03)' in text["schema"]
    inv7 = 'satisfies the §6 result–reason invariant (`reason` `"NONE"` if and only if `result` `"accepted"`)' in sec7
    # G001-04 F-06: review-record claims synchronized with the packet's record; no artifact
    # calls itself a draft awaiting disposition.
    brief_ok = all(s in text["brief"] for s in REVIEW_STATE)
    stale = [DOCS[k] for k, t in text.items() if "draft for owner disposition" in t]
    ok = id_ok and pld_ok and inv6 and inv7 and brief_ok and not stale
    return (ok, f"schema identities found: {sorted(ids)} (must be exactly one); pld_rate unconditional: {pld_ok}; "
                f"result-reason invariant Sec6/Sec7: {inv6}/{inv7}; brief review-record claim present: {brief_ok}; "
                f"draft-awaiting-disposition wording in: {stale}" if not ok
            else f"one schema identity ({next(iter(ids))}) across title and meta.schema member (G001-04 F-01); pld_rate bound "
                 f"unconditional in Sec. 7 (F-07); result-reason invariant stated in Sec. 6 and enforced in Sec. 7 (G001-05 "
                 f"F-03); brief review-record claim matches this baseline; no artifact claims draft status (F-06)")


CHECKS = [
    ("C1", "format hygiene: LF; canonical-row discipline over the record's table grammar (beyond it = ratified debt)", c1),
    ("C2", "requirement IDs: unique identifier-shaped rows (ownership = D0-17 debt); scanned citation classes resolve", c2),
    ("C3", "trace lineage: set coverage + fixed-point NEED reachability (order-independent)", c3),
    ("C4", "telemetry mnemonics: uppercase uses + lowercase schema members resolve", c4),
    ("C5", "telemetry: 16 identifier-shaped rows (ownership = D0-17 debt), no duplicates, no conflicting counts", c5),
    ("C6", "commands: 5 identifier-shaped rows (ownership = D0-17 debt), no duplicates, citations resolve", c6),
    ("C7", "command count: 4 anchors + bounded conflicting-count scan", c7),
    ("C8", "mode thresholds: 12 anchors + bounded out-of-set percentage scan", c8),
    ("C9", "EPS envelope: recognized-phrasing sweep, 7 quantities (semantic detection = ratified debt)", c9),
    ("C10", "battery-voltage limit anchor present (anchor presence only)", c10),
    ("C11", "staleness normative anchors in dictionary and CONOPS", c11),
    ("C12", "terminology: forbidden phrases only in rule scope (word-bounded markers, own-fragment/enumeration-run)", c12),
    ("C13", "station name: GS-RAVENSROOST only; GS-EUSTIS absent", c13),
    ("C14", "FMEA worksheets: the 22 HUG-G001 rows inside grammar-bounded tables; Sec. 6.2 recognized; none orphaned (line-scan scope = ratified debt)", c14),
    ("C15", "fault set: HUG-EPS-004 row ⇄ Sec6-bounded grammar-bounded tables; count-before-validate partition of HUG-G001 R2, Sec. 6.3 the rest", c15),
    ("C16", "identity & status: one schema identity; unconditional pld_rate; result-reason invariant; review record synced", c16),
]

# ---------------- self-test: every check must catch every listed mutation ----------------

def _dup_row(key, prefix):
    def f(t):
        row = [l for l in t.splitlines() if l.startswith(prefix)][0]
        return t.replace(row, row + "\n" + row, 1)
    return (key, f)


def _fence_table(header_sig):
    """Wrap the contiguous table whose header contains header_sig in a code fence
    (G001-11 F-03): a renderer then displays code, not a table, so the normative table
    disappears from the rendered record and its check must turn red."""
    def f(t):
        lines = t.splitlines()
        out, cur, fenced = [], [], False
        for ln in lines:
            if ln.startswith("|"):
                cur.append(ln)
            else:
                if cur:
                    if not fenced and header_sig in cur[0]:
                        out.append("```")
                        out.extend(cur)
                        out.append("```")
                        fenced = True
                    else:
                        out.extend(cur)
                    cur = []
                out.append(ln)
        if cur:
            if not fenced and header_sig in cur[0]:
                out.append("```")
                out.extend(cur)
                out.append("```")
                fenced = True
            else:
                out.extend(cur)
        assert fenced, f"table {header_sig!r} not found"
        return "\n".join(out) + "\n"
    return f


def _fence_table_containing(key, row_prefix):
    """Wrap the contiguous table containing a line starting with row_prefix in a code
    fence (G001-12 F-01): the definitions vanish from the rendered record, and the
    consumer that reads them through the shared parsed-table representation must turn
    red."""
    def f(t):
        lines = t.splitlines()
        out, cur, fenced = [], [], False

        def flush():
            nonlocal fenced, cur
            if cur:
                if not fenced and any(l.startswith(row_prefix) for l in cur):
                    out.append("```")
                    out.extend(cur)
                    out.append("```")
                    fenced = True
                else:
                    out.extend(cur)
                cur = []
        for ln in lines:
            if ln.startswith("|"):
                cur.append(ln)
            else:
                flush()
                out.append(ln)
        flush()
        assert fenced, f"table containing {row_prefix!r} not found"
        return "\n".join(out) + "\n"
    return (key, f)


def _f03_pseudofence(t):
    """G001-12 F-03 reproduction: a 4-space-indented backtick run - an indented code line
    to a renderer, NOT a fence opener - placed before a real table that carries a stealth
    pipe-less formatted duplicate, with a bare run after the section. The renderer shows
    the table and its stealth row; a mask with the wrong opening-fence boundary swallows
    the region and misses the row."""
    row = [l for l in t.splitlines() if l.startswith("| HUG-SYS-001 ")][0]
    t = t.replace(row, row + "\n**HUG-SYS-001** | pseudo-fenced stealth duplicate | T | NEED-02 |", 1)
    h = t.find("## HUG-SYS: System")
    t = t[:h] + "    ```\n" + t[h:]
    e = t.find("## HUG-EPS")
    return t[:e] + "```\n\n" + t[e:]


def _ins(key, prefix, new_line, extra=""):
    """Insert new_line directly after the first line starting with prefix - INSIDE the
    rendered table that line belongs to (G001-10 F-03: red mutations must be table rows,
    not end-of-file text). extra, if given, is appended at end of file (used for link
    reference definitions)."""
    def f(t):
        row = [l for l in t.splitlines() if l.startswith(prefix)][0]
        return t.replace(row, row + "\n" + new_line, 1) + extra
    return (key, f)


def _relocate_table(header_sig):
    """Remove the intact contiguous table whose header contains header_sig; append it at EOF."""
    def f(t):
        lines = t.splitlines()
        out, moved, cur, in_tbl = [], [], [], False
        for ln in lines:
            if ln.startswith("|"):
                cur.append(ln)
            else:
                if cur:
                    if not moved and header_sig in cur[0]:
                        moved = cur
                    else:
                        out.extend(cur)
                    cur = []
                out.append(ln)
        if cur:
            if not moved and header_sig in cur[0]:
                moved = cur
            else:
                out.extend(cur)
        assert moved, f"table {header_sig!r} not found"
        return "\n".join(out) + "\n\nRelocated for reference:\n\n" + "\n".join(moved) + "\n"
    return f


#: Which requirements each check discharges, for the traceability matrix (B3).
#:
#: Declared HERE, beside the checks, rather than in the matrix — a matrix carrying its
#: own copy of this mapping would be the hand-maintained matrix HUG-VER-001 prohibits.
#:
#: Empty tuples are deliberate, not omissions: C1 (format hygiene), C12 (terminology)
#: and C14 (FMEA worksheet structure) hold the record's own shape rather than evidencing
#: a numbered requirement. Listing them empty means a check ADDED and never mapped is
#: visibly missing from this dict rather than indistinguishable from one mapped to
#: nothing on purpose.
CHECK_VERIFIES = {
    "C1": (),
    "C2": ("HUG-VER-001",),
    "C3": ("HUG-VER-001",),
    "C4": ("HUG-GND-001",),
    "C5": ("HUG-GND-001",),
    "C6": ("HUG-CMD-001", "HUG-GND-003"),
    "C7": ("HUG-GND-003",),
    "C8": ("HUG-EPS-003",),
    "C9": ("HUG-EPS-005",),
    "C10": ("HUG-GND-002",),
    "C11": ("HUG-GND-002",),
    "C12": (),
    "C13": ("HUG-GND-005",),
    "C14": (),
    "C15": ("HUG-EPS-004", "HUG-SYS-005"),
    "C16": ("HUG-UI-003",),
}


MUTATIONS = {
    "C1": [("reqs", lambda t: t + "crlf line\r\n"),
           # G001-10 F-03: every red row below is INSERTED INSIDE a rendered table so it
           # exercises table-row behavior, not an end-of-file line scan.
           # G001-07 F-03 class guard: a stealth ID-leading row without its outer pipe
           _ins("reqs", "| HUG-SYS-001 ", "HUG-SYS-001 | stealth duplicate row without outer pipe | T | NEED-02 |"),
           # G001-08 F-02 reproductions: the no-space form and the indented form
           _ins("reqs", "| HUG-SYS-001 ", "HUG-SYS-001| stealth duplicate, separator touching the identifier | T | NEED-02 |"),
           _ins("reqs", "| HUG-SYS-001 ", "   HUG-SYS-001 | stealth duplicate, renderer-accepted indentation | T | NEED-02 |"),
           # G001-08 F-03 class guard: a formatted identifier cell behind a canonical pipe
           _ins("reqs", "| HUG-SYS-001 ", "| **HUG-SYS-001** | formatted stealth duplicate | T | NEED-02 |"),
           # G001-09 F-02 reproduction: formatted identifier on an outer-pipe-less row
           _ins("reqs", "| HUG-SYS-001 ", "**HUG-SYS-001** | formatted pipe-less stealth duplicate | T | NEED-02 |"),
           # G001-09 F-03 reproductions: formatted underscore-bearing telemetry and command IDs
           _ins("dict", "| EPS_BATT_V ", "| **EPS_BATT_V** | formatted stealth telemetry duplicate | float | V | none |"),
           _ins("dict", "| CMD_SAFE_ENTER ", "| **CMD_SAFE_ENTER** | none | formatted stealth command duplicate | none |"),
           # G001-09 F-04 reproduction: link-wrapped identifier cell
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001](https://example.invalid/x) | link-wrapped stealth duplicate | T | NEED-02 |"),
           # G001-10 F-02 reproductions: backslash-escaped and full-reference forms...
           _ins("reqs", "| HUG-SYS-001 ", "| HUG\\-SYS\\-001 | backslash-escaped stealth duplicate | T | NEED-02 |"),
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001][r1] | full-reference stealth duplicate | T | NEED-02 |",
                "\n[r1]: https://example.invalid/x\n"),
           # ...plus the remaining reference syntaxes of the same class: collapsed and shortcut
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001][] | collapsed-reference stealth duplicate | T | NEED-02 |",
                "\n[HUG-SYS-001]: https://example.invalid/x\n"),
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001] | shortcut-reference stealth duplicate | T | NEED-02 |",
                "\n[HUG-SYS-001]: https://example.invalid/x\n"),
           # G001-11 F-02 reproduction: link and definition labels that differ in internal
           # whitespace but normalize to the same CommonMark label
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001][review label] | whitespace-label stealth duplicate | T | NEED-02 |",
                "\n[review  label]: https://example.invalid/x\n"),
           # G001-11 F-04 reproduction: link destination containing an escaped pipe -
           # one rendered cell whose label is the bare identifier
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001](https://example.invalid/x\\|y) | escaped-pipe stealth duplicate | T | NEED-02 |"),
           # G001-12 F-02 reproduction: an EVEN backslash run before the separator - the
           # escaped backslash is content, the pipe is a real boundary, and the rendered
           # first cell bears the identifier plus escape residue
           _ins("reqs", "| HUG-SYS-001 ", "| **HUG-SYS-001**\\\\| stealth duplicate behind an escaped-backslash separator | T | NEED-02 |"),
           # G001-12 F-03 reproduction: indented pseudo-fence must NOT mask the real table
           # or its stealth row
           ("reqs", _f03_pseudofence),
           # G001-12 F-04 reproductions: balanced and escaped parentheses in link destinations
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001](https://example.invalid/x(1)y) | balanced-parenthesis stealth duplicate | T | NEED-02 |"),
           _ins("reqs", "| HUG-SYS-001 ", "| [HUG-SYS-001](https://example.invalid/x\\(1y) | escaped-parenthesis stealth duplicate | T | NEED-02 |"),
           # G001-10 F-03 STAY-GREEN cases: identifier-and-pipe lines that render as prose
           # and as fenced code are NOT table rows and must not be flagged
           ("conops", lambda t: t + "\nHUG-SYS-001 | an identifier-and-pipe line in plain prose, outside any table\n",
            "green"),
           ("conops", lambda t: t + "\n```\nHUG-SYS-001 | example checker input line inside a fenced code block\n```\n",
            "green")],
    "C2": [_dup_row("reqs", "| HUG-EPS-001 "),
           ("fmea", lambda t: t + "\nSee HUG-ZZZ-999 for details.\n"),
           ("schema", lambda t: t.replace("HUG-UI-002/003/004/005", "HUG-UI-002/003/004/099", 1))],
    "C3": [("conops", lambda t: t.replace("| NEED-01 |", "| NEED-09 |", 1)),
           ("reqs", lambda t: t.replace("| T | NEED-02; CON-01; CON-03 |", "| T | CON-01; CON-03 |", 1)),
           # G001-04 F-05 reproductions: a row citing itself as its parent...
           ("reqs", lambda t: t.replace("| T | HUG-SYS-005; G001 F-03 |", "| T | HUG-EPS-004; G001 F-03 |", 1)),
           # ...and a two-row cycle with no NEED termination (HUG-SYS-005 ⇄ HUG-EPS-004)
           ("reqs", lambda t: t.replace("| I, T | NEED-04 |", "| I, T | HUG-EPS-004 |", 1)),
           # G001-05 F-04 STAY-GREEN case: the reviewer's exact cycle-with-exit topology
           # (A cites {R, Q}; R -> P; P -> A; Q reaches a NEED). Every row keeps genuine
           # acyclic lineage through the exit, so C3 must PASS - the v5 recursive checker
           # flagged this order-dependently; the fixed-point form cannot.
           ("reqs", lambda t: t
              .replace("| I | NEED-02; FMEA REC-02; G001-07 F-01 |", "| I | HUG-OPS-002; HUG-OPS-003 |", 1)
              .replace("| I | NEED-04; G001-06 F-01; G001-07 F-01; G001-07 F-02; G001-08 F-01; G001-09 F-01; G001-10 F-01 |\n| HUG-OPS-003",
                       "| I | HUG-OPS-004 |\n| HUG-OPS-003", 1)
              .replace("requirements. | I | NEED-04 |", "requirements. | I | HUG-OPS-001 |", 1),
            "green"),
           # G001-12 F-01 reproduction: the NEED/CON/ASM definitions table relocated into
           # fenced code - the definitions vanish from the rendered record
           _fence_table_containing("conops", "| NEED-01 ")],
    "C4": [("fmea", lambda t: t + "\nEPS_FAKE_POINT appears here.\n"),
           ("schema", lambda t: t.replace("eps_batt_soc", "eps_batt_socc", 1)),
           # G001-12 F-01 reproduction: the telemetry definitions table fenced away
           _fence_table_containing("dict", "| EPS_BATT_V ")],
    "C5": [_dup_row("dict", "| EPS_BATT_V "),
           ("conops", lambda t: t + "\nThe frame carries 17 telemetry points in this revision.\n"),
           ("conops", lambda t: t + "\nThe frame carries seventeen telemetry points in this revision.\n"),
           # G001-12 F-01 reproduction: the telemetry definitions table fenced away
           _fence_table_containing("dict", "| EPS_BATT_V ")],
    "C6": [_dup_row("dict", "| CMD_SAFE_ENTER "),
           # G001-12 F-01 reproduction: the command definitions table fenced away
           _fence_table_containing("dict", "| CMD_SAFE_ENTER ")],
    "C7": [("dict", lambda t: t.replace("## 2. Commands (5)", "## 2. Commands (6)")),
           ("dict", lambda t: t + "\nThe v0.1 command set comprises six commands in total.\n")],
    "C8": [("reqs", lambda t: t.replace("below 35% for target NOMINAL", "below 45% for target NOMINAL")),
           ("conops", lambda t: t + "\nPayload activation is additionally inhibited below 45% in cold cases.\n")],
    "C9": [("conops", lambda t: t + "\nA 5.5 V regulated bus is described here.\n"),
           ("conops", lambda t: t + "\nSolar-array peak generation of 20 W is assumed for margin studies.\n")],
    "C10": [("dict", lambda t: t.replace("6.8 / 7.2 / 8.3 / 8.5", "6.8 / 7.2 / 8.3 / 8.6"))],
    "C11": [("dict", lambda t: t.replace("no advance for 10 s", "no advance for 12 s"))],
    "C12": [("brief", lambda t: t + "\nThe orbit uses a real TLE for propagation.\n"),
            ("conops", lambda t: t + "\nWe never rest during a pass; VÉ serves as mission control for the public feed.\n"),
            ("conops", lambda t: t + "\nVÉ is never command-capable, but it is mission control for the public feed.\n"),
            ("conops", lambda t: t + "\nOne rule never changes: the public feed runs through mission control here.\n"),
            # G001-04 F-04 reproduction: QUOTED claim in a later fragment, marker in an
            # unrelated earlier fragment on the same line
            ("conops", lambda t: t + '\nWe never rest during a pass; the stream bills VÉ as "mission control" for the evening.\n'),
            # G001-05 F-05 reproduction: marker text only as a substring of a larger word
            ("conops", lambda t: t + "\nVÉ is nevertheless mission control for the public feed.\n")],
    "C13": [("conops", lambda t: t + "\nGS-EUSTIS appears here.\n")],
    "C14": [("fmea", lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("| FM-GND-06 ")) + "\n"),
            ("fmea", lambda t: t.replace("| FM-CDH-03 |", "An explanatory paragraph interrupts the table here.\n| FM-CDH-03 |", 1)),
            # G001-08 F-03 reproduction: a duplicate WORKSHEET row with a code-span identifier
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-06 \|(.*)\n)", lambda m: m.group(1) + "| `FM-GND-06` |" + m.group(2) + "\n",
                                      t, count=1, flags=re.M)),
            # G001-10 F-02 class guard: a duplicate WORKSHEET row with a full-reference
            # identifier and its matching definition
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-06 \|(.*)\n)",
                                      lambda m: m.group(1) + "| [FM-GND-06][d1] |" + m.group(2) + "\n",
                                      t, count=1, flags=re.M) + "\n[d1]: https://example.invalid/x\n"),
            # G001-11 F-03 reproduction: a WORKSHEET table relocated into a code fence -
            # the renderer shows code, the worksheet rows vanish from the rendered record
            ("fmea", _fence_table("Failure mode (cause)")),
            # D-020: a HUG-G001 row deleted, with the row count restored by the row added
            # after the selection. The v21 count of 22 accepted this; only the named set
            # can see it.
            ("fmea", lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("| FM-EPS-09 ")) + "\n"),
            # D-020: a HUG-G001 row renumbered out of the record
            ("fmea", lambda t: t.replace("| FM-EPS-09 |", "| FM-EPS-12 |", 1))],
    "C15": [("reqs", lambda t: t.replace("(b) stuck-on load of 2.0 W;", "(b) stuck-on load of 2.5 W;", 1)),
            ("fmea", lambda t: t.replace("| (c) Housekeeping telemetry generation halt | FM-CDH-01 | R2 (II/C) | P4 | PROC-003 |\n", "", 1)
                               + "\n| (c) Housekeeping telemetry generation halt | FM-CDH-01 | R2 (II/C) | P4 | PROC-003 |\n"),
            # G001-04 F-03 reproduction: the INTACT selected-set table relocated outside Sec. 6
            ("fmea", _relocate_table("Injected fault")),
            # G001-04 F-02 mechanization mutations: drop an exclusion row; disagree on sev/lik;
            # cite a criterion outside (a)-(e)
            ("fmea", lambda t: re.sub(r"^\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n", "", t, count=1, flags=re.M)),
            ("fmea", lambda t: t.replace("| FM-GND-02 | R2 (III/C) |", "| FM-GND-02 | R2 (III/D) |", 1)),
            ("fmea", lambda t: t.replace("| FM-GND-02 | R2 (III/C) | (c) |", "| FM-GND-02 | R2 (III/C) | (f) |", 1)),
            # G001-05 F-06 reproductions: duplicate exclusion rows - identical, and with a
            # conflicting criterion - must both fail via raw-row duplicate rejection
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)", r"\1\1", t, count=1, flags=re.M)),
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1| FM-GND-02 | R2 (III/C) | (e) | Duplicate conflicting exclusion of record. |\n",
                                      t, count=1, flags=re.M)),
            # G001-06 F-02 reproductions: MALFORMED duplicates - invalid criterion, and a
            # broken risk cell - must fail via count-before-validate (the reviewer's forms)
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1| FM-GND-02 | R2 (III/C) | (f) | Malformed duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1| FM-GND-02 | R2 III/C | (e) | Malformed duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # G001-07 F-03 reproduction: duplicate row in the valid NO-LEADING-PIPE Markdown
            # form - a renderer shows a fourth column-aligned row; the parse must count it
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1FM-GND-02 | R2 (III/C) | (e) | Duplicate exclusion, no leading pipe. |\n",
                                      t, count=1, flags=re.M)),
            # G001-08 F-03 reproduction: duplicate exclusion row with a BOLD identifier cell
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1| **FM-GND-02** | R2 (III/C) | (e) | Formatted duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # G001-09 F-04 reproduction: duplicate exclusion row with a LINK-WRAPPED identifier
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1| [FM-GND-02](https://example.invalid/x) | R2 (III/C) | (e) | Link-wrapped duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # G001-10 F-02 class guard: duplicate exclusion row with a BACKSLASH-ESCAPED identifier
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      lambda m: m.group(1) + "| FM\\-GND\\-02 | R2 (III/C) | (e) | Backslash-escaped duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # G001-11 F-03 reproductions: the SELECTED-SET table, then the EXCLUSION table,
            # relocated into code fences - each renders as code and must turn C15 red
            ("fmea", _fence_table("Injected fault")),
            ("fmea", _fence_table("First failed criterion")),
            # G001-11 F-04 reproduction: duplicate exclusion row whose link destination
            # contains an escaped pipe - one rendered cell, bare identifier label
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      lambda m: m.group(1) + "| [FM-GND-02](https://example.invalid/x\\|y) | R2 (III/C) | (e) | Escaped-pipe duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # G001-12 F-01 reproduction: the requirements table carrying HUG-EPS-004 fenced
            # away - the normative fault-clause row vanishes from the rendered record
            _fence_table_containing("reqs", "| HUG-EPS-004 "),
            # G001-12 F-02 reproduction: duplicate exclusion row behind an even backslash run
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      lambda m: m.group(1) + "| FM-GND-02\\\\| R2 (III/C) | (e) | Escaped-backslash duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # G001-12 F-04 reproduction: duplicate exclusion row with a balanced-parenthesis
            # link destination
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      lambda m: m.group(1) + "| [FM-GND-02](https://example.invalid/x(1)y) | R2 (III/C) | (e) | Balanced-parenthesis duplicate exclusion. |\n",
                                      t, count=1, flags=re.M)),
            # D-020 Sec. 6.3 reproductions. The row added after the selection: dropped
            # from Sec. 6.3; replaced there by a HUG-G001 row; with a risk spelling that
            # disagrees with its worksheet row; listed twice; listed again malformed;
            # moved into the exclusion record instead; and the whole table fenced away or
            # relocated outside Sec. 6.
            ("fmea", lambda t: re.sub(r"^\| FM-GND-07 \| R2 \(II/C\) \| v0\.16.*\n", "", t, count=1, flags=re.M)),
            ("fmea", lambda t: t.replace("| FM-GND-07 | R2 (II/C) | v0.16", "| FM-GND-04 | R2 (II/C) | v0.16", 1)),
            ("fmea", lambda t: t.replace("| FM-GND-07 | R2 (II/C) | v0.16", "| FM-GND-07 | R2 (II/D) | v0.16", 1)),
            # a HUG-G001 row listed in Sec. 6.3 as well as in the exclusion record
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-07 \| R2 \(II/C\) \| v0\.16.*\n)",
                                      r"\1| FM-GND-04 | R2 (II/C) | v0.16 (D-020) | Listed here as well. |\n",
                                      t, count=1, flags=re.M)),
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-07 \| R2 \(II/C\) \| v0\.16.*\n)", r"\1\1", t, count=1, flags=re.M)),
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-07 \| R2 \(II/C\) \| v0\.16.*\n)",
                                      r"\1| FM-GND-07 | R2 II/C | v0.16 (D-020) | Malformed duplicate. |\n",
                                      t, count=1, flags=re.M)),
            # a malformed Sec. 6.3 row naming a HUG-G001 row: no other clause sees it,
            # because a row that fails validation never enters the Sec. 6.3 mapping
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-07 \| R2 \(II/C\) \| v0\.16.*\n)",
                                      r"\1| FM-GND-04 | R2 II/C | v0.16 (D-020) | Malformed stray row. |\n",
                                      t, count=1, flags=re.M)),
            ("fmea", lambda t: re.sub(r"^(\| FM-GND-02 \| R2 \(III/C\) \| \(c\) \|.*\n)",
                                      r"\1| FM-GND-07 | R2 (II/C) | (e) | Moved out of Sec. 6.3. |\n",
                                      re.sub(r"^\| FM-GND-07 \| R2 \(II/C\) \| v0\.16.*\n", "", t, count=1, flags=re.M),
                                      count=1, flags=re.M)),
            ("fmea", _fence_table("Selection status")),
            ("fmea", _relocate_table("Selection status")),
            # GREEN: a Sec. 6.3 status cell reworded changes no membership
            ("fmea", lambda t: t.replace("| v0.16 (D-020) | Added after the campaign was executed;",
                                         "| v0.16 (D-020) | Added once the campaign had been executed;", 1), "green")],
    "C16": [# G001-04 F-01 reproduction: member discriminator disagrees with the title identity
            ("schema", lambda t: t.replace('`"0.9"` for this definition', '`"0.8"` for this definition', 1)),
            # G001-04 F-07 reproduction: the conditional bound reintroduced
            ("schema", lambda t: t.replace("`pld_rate` ∈ [0.1, 10] in every frame regardless of `pld_state`",
                                           '`pld_rate` ∈ [0.1, 10] when `pld_state` = "ON"', 1)),
            # G001-04 F-06 reproductions: stale review-record claim; draft wording reintroduced
            ("brief", lambda t: t.replace("seventeen adversarial review rounds complete", "sixteen adversarial review rounds complete", 1)),
            ("schema", lambda t: t + "\nThis revision is a draft for owner disposition.\n"),
            # G001-05 F-03 mechanization: the Sec. 7 invariant cross-field rule stripped
            ("schema", lambda t: t.replace('; every `events[].cmd` satisfies the §6 result–reason invariant '
                                           '(`reason` `"NONE"` if and only if `result` `"accepted"`)', "", 1))],
}


def iter_selftest_cases(art):
    """Per-case self-test results, structured. `self_test` prints from this.

    ONE IMPLEMENTATION, TWO CALLERS. The printed self-test and the verification run
    (B5, HUG-VER-003) must not be able to disagree about which cases ran or how each
    went. A second traversal written beside this one would be a private copy of the
    case list, and the two would drift the first time a mutation was added — the
    defect G1 exists to catch in the generated views, reappearing inside the checker.
    """
    for cid, _name, fn in CHECKS:
        for j, entry in enumerate(MUTATIONS[cid], 1):
            doc_key, mut = entry[0], entry[1]
            polarity = entry[2] if len(entry) > 2 else "red"
            raised = None
            with tempfile.TemporaryDirectory() as td:
                # Stage only the six documents load() reads, preserving their
                # repo-relative layout. (v18 copied the whole artifact directory;
                # at repo root that would copy .git 84 times over.) load() opens
                # nothing else, so the staged tree is equivalent for every check.
                mart = Path(td) / "record"
                for rel in DOCS.values():
                    dst = mart / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(art / rel, dst)
                p = mart / DOCS[doc_key]
                p.write_bytes(mut(p.read_text(encoding="utf-8")).encode("utf-8"))
                try:
                    ok, _ = fn(*load(mart))
                except Exception as exc:
                    # OF-008's shape exactly: a red case can be satisfied by a crash
                    # rather than by the check detecting the violation it was written
                    # for. Recorded rather than swallowed, so the verification report
                    # can count how many red cases owe their result to an exception.
                    ok, raised = False, f"{type(exc).__name__}: {exc}"
            passed = (not ok) if polarity == "red" else ok
            yield {
                "case_id": f"{cid}.m{j}", "check": cid, "polarity": polarity,
                "target": DOCS[doc_key], "passed": passed, "raised": raised,
                "label": ("CAUGHT" if passed else "MISSED") if polarity == "red"
                         else ("HELD-GREEN" if passed else "FALSE-FLAG"),
            }


def self_test(art):
    print("SELF-TEST: every RED mutation below must turn its check red; every GREEN case must\n"
          "leave its check green (G001-05 F-04, G001-10 F-03: valid-but-tricky structures must\n"
          "not be flagged). Adversarial forms included, from the reviewers' reproduction forms\n"
          "of HUG-G001-02 through HUG-G001-12.\n")
    failed = []
    for case in iter_selftest_cases(art):
        print(f"[{case['label']}] {case['case_id']} ({case['target']}"
              + (", green-expected" if case["polarity"] == "green" else "") + ")")
        if not case["passed"]:
            failed.append(case["case_id"])
    total = sum(len(v) for v in MUTATIONS.values())
    print(f"\nSELF-TEST RESULT: {total-len(failed)}/{total} cases correct"
          + (f"; FAILED: {failed}" if failed
             else " — every check falsifiable on red forms and stable on green forms"))
    return 1 if failed else 0


def iter_check_cases(art):
    """Per-check results, structured. `run_all` prints from this; B5 records it."""
    text, raw = load(art)
    for cid, name, fn in CHECKS:
        raised = None
        try:
            ok, ev = fn(text, raw)
        except Exception as exc:
            # A check that raised did not observe its subject. That is a statement
            # about the checker, not about the record, and the verification report
            # records it as INSTRUMENT_FAULT rather than as a failing record.
            ok, ev = False, f"raised {type(exc).__name__}: {exc}"
            raised = f"{type(exc).__name__}: {exc}"
        yield {"case_id": cid, "name": name, "passed": ok, "evidence": ev,
               "raised": raised}


def run_all(art):
    fails = []
    for case in iter_check_cases(art):
        print(f"[{'PASS' if case['passed'] else 'FAIL'}] {case['case_id']} {case['name']}\n"
              f"       {case['evidence']}")
        if not case["passed"]:
            fails.append(case["case_id"])
    print(f"\nRESULT: {len(CHECKS)-len(fails)}/{len(CHECKS)} checks PASS"
          + (f"; FAILING: {fails}" if fails else " — design record consistent (within the stated scope of each check)"))
    return 1 if fails else 0


if __name__ == "__main__":
    # Several check names and PASS messages carry the record's own characters
    # (U+21C4, U+2192, U+2014). On a console whose encoding is cp1252 - the Windows
    # default, and the owner's machine - printing them raised UnicodeEncodeError and
    # the run died mid-report with an exit status that looked like a check failure.
    # Report text is never the thing under test, so degrade unencodable characters
    # rather than lose the report.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - non-reconfigurable stream
        pass
    art = Path(__file__).resolve().parent.parent.parent
    sys.exit(self_test(art) if "--self-test" in sys.argv else run_all(art))
