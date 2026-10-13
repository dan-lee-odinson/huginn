#!/usr/bin/env python3
"""HUGINN defs-generation checks, v1 (Phase 1).

WHAT THESE CHECKS CLAIM. That the `defs/` single sources and the views generated from
them are ONE record and cannot silently disagree:
  - every generated view is exactly what its source generates, right now
  - generation is deterministic
  - each source's version identity matches the identity in the view it generates, and
    the replay schema's identity matches at all three sites it appears
  - the structured values that also appear inside the record's prose agree with that
    prose (the command thresholds), so a value cannot drift between the two
  - the sources' own structural invariants hold: counts, uniqueness, the bijective
    mnemonic transform the replay schema depends on, group/identifier agreement,
    verification methods within the defined set, and no YAML type coercion

WHAT THEY DO NOT CLAIM. They do not check the record's prose against itself - that is
tools/checkers/design_record_consistency.py, which still reads the markdown, and
correctly so: it verifies the record as it reads. These checks verify the binding
BETWEEN source and view. Neither subsumes the other.

Every claim above is executed at BOTH POLARITIES by --self-test (HUG-VER-002, B4): a
red case each check must catch, and where the form is tricky a green case it must not
flag. A check's passing result counts as evidence only because its red case is
demonstrated to fail it. No direction claim is made here that the suite does not
execute (the rule earned at G001-12 F-02).

Modes:
  python tools/checkers/defs_generation.py              run all checks; exit 1 on FAIL
  python tools/checkers/defs_generation.py --self-test  two-polarity suite; exit 1 if
                                                        any red case is missed or any
                                                        green case is false-flagged
"""
import hashlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gen_dictionary  # noqa: E402
import gen_fmea  # noqa: E402
import gen_ve_viewer
import gen_procedures
import gen_openc3_config  # noqa: E402
import gen_requirements  # noqa: E402
import hugdefs  # noqa: E402
from hugdefs import (console, defs_dir, docs_dir, points, repo,  # noqa: E402
                     requirements_flat, set_repo, trace_tokens)

VERIFICATION_METHODS = {"T", "A", "I", "D"}

# Files the checks read. The self-test stages exactly these.
STAGED = [
    "defs/tlm_cmd.yaml", "defs/requirements.yaml", "defs/replay_schema.yaml",
    "defs/replay_schema.md", "defs/fmea.yaml", "defs/eps.yaml",
    "docs/tlm_cmd_dictionary.md", "docs/requirements.md", "docs/fmea.md",
    "gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/target.txt", "gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/CONFIG_ID.txt",
    "gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/cmd_tlm/tlm.txt", "gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/cmd_tlm/cmd.txt",
    # The three prose documents. Read only by G14, which is the one check that covers
    # documents with no `defs/` source to bind them to.
    "docs/concept_brief.md", "docs/conops.md",
    # The plugin wrapper and the B6 monitor, both generated.
    "gnd/openc3/plugins/openc3-cosmos-huginn/plugin.txt",
    "gnd/openc3/plugins/openc3-cosmos-huginn/openc3-cosmos-huginn.gemspec",
    "gnd/openc3/plugins/openc3-cosmos-huginn/microservices/STALENESS/frame_staleness.py",
    # The vendored ground project and its pin, read by G16.
    "defs/procedures.yaml",
    "procedures/PROC-001.md", "procedures/PROC-002.md", "procedures/PROC-003.md",
    # The operator products, read by G18.
    "campaign/CAMPAIGN_PLAN.md", "gnd/RUNBOOK.md",
    "defs/ground.yaml", "gnd/openc3/compose.yaml",
    "gnd/openc3/.env.template", "gnd/openc3/openc3-redis/users.acl.template",
    ".gitignore",
    # The owner-ruling register, read by G8: a requirement struck in place must name a
    # ruling that is in it (D-019).
    "DECISIONS.md",
]

# Every single-file generated view is staged automatically.
#
# THIS DERIVATION EXISTS BECAUSE THE HAND-KEPT LIST KEPT LOSING THINGS. Adding the
# generated gemspec, and then the VÉ limit table, each left the mutation harness
# staging a copy of the repository with that file MISSING — so G1 called it stale and
# G12 called it uncovered in every mutated copy, and the green cases false-flagged. The
# green cases caught it both times, which is the argument for having them; deriving the
# list is the argument for not needing to be caught a third time.
#
# Directory entries (trailing "/") stay hand-listed above: they expand to specific files
# and the harness copies files, not trees.
STAGED += [view for view in hugdefs.GENERATED
           if not view.endswith("/") and view not in STAGED]


# --------------------------------------------------------------------------- checks

#: Which generator produces each view in hugdefs.GENERATED.
#:
#: Keyed by the registry rather than kept as its own list, because a second list is what
#: drifts. This was a hand-written tuple of four pairs, and registering the VÉ limit
#: table in GENERATED gave it G12's sentinel scan but NOT G1's round trip — a wrong
#: threshold planted in `ve/viewer/limits.js` left G1 green. The view was registered as
#: generated and nothing was checking that it still matched what generates it.
GENERATORS = {
    "docs/tlm_cmd_dictionary.md": gen_dictionary,
    "docs/requirements.md": gen_requirements,
    "docs/fmea.md": gen_fmea,
    "gnd/openc3/plugins/openc3-cosmos-huginn/": gen_openc3_config,
    "ve/viewer/limits.js": gen_ve_viewer,
    "procedures/": gen_procedures,
}


def g1_round_trip():
    """Every generated view is exactly what its source generates, right now.

    COVERAGE IS CHECKED, NOT ASSUMED. A view in `hugdefs.GENERATED` with no generator
    here fails this check rather than being skipped: an unrun generator is a view nobody
    round-trips, and it would sit in the registry looking accounted for.
    """
    uncovered = sorted(set(hugdefs.GENERATED) - set(GENERATORS))
    if uncovered:
        return False, (f"registered as generated but with no generator to round-trip "
                       f"them: {uncovered}. A view nobody regenerates is a view nobody "
                       f"checks.")
    stale = []
    for name in sorted(GENERATORS):
        gen = GENERATORS[name]
        buf, sys.stdout = sys.stdout, open(_devnull(), "w")
        try:
            rc = gen.main(["--check"])
        finally:
            sys.stdout.close()
            sys.stdout = buf
        if rc != 0:
            stale.append(name)
    total = len(GENERATORS)
    return (not stale,
            f"{total - len(stale)}/{total} generated views match their source exactly"
            + (f"; STALE: {stale} — regenerate, hand edits are prohibited" if stale
               else " (documents byte-for-byte, not merely semantically)"))


def g2_deterministic():
    """Generation is deterministic: the same source yields the same bytes twice."""
    first = _render_all()
    second = _render_all()
    differing = [k for k in first if first[k] != second[k]]
    return (not differing,
            f"{len(first)} rendered outputs identical across two runs from the same "
            f"source" + (f"; NONDETERMINISTIC: {differing}" if differing else ""))


def g3_schema_identity():
    """The replay schema's identity agrees at all three sites it appears."""
    md = (defs_dir() / "replay_schema.md").read_text(encoding="utf-8")
    title = re.search(r"^## .*v[0-9.]+ \(schema ([0-9.]+)\)", md, re.M)
    member = re.search(r"`\"([0-9.]+)\"` for this definition", md)
    if not title or not member:
        return False, ("could not locate the schema identity in the prose "
                       f"(title={bool(title)}, meta.schema={bool(member)})")
    yml = hugdefs.load_replay_schema()["schema"]
    sites = {"prose title": title.group(1), "prose meta.schema": member.group(1),
             "defs/replay_schema.yaml": yml}
    ok = len(set(sites.values())) == 1
    return (ok, f"one schema identity ({yml}) across prose title, prose meta.schema "
                f"member, and the machine form" if ok else f"IDENTITIES DISAGREE: {sites}")


def g4_document_identities():
    """Each source's version equals the version in the view it generates."""
    bad = []
    pairs = [
        ("defs/tlm_cmd.yaml", hugdefs.load_tlm_cmd()["dictionary_version"],
         "docs/tlm_cmd_dictionary.md", r"^## .* v([0-9.]+)$"),
        ("defs/requirements.yaml", hugdefs.load_requirements()["requirements_version"],
         "docs/requirements.md", r"^## .* v([0-9.]+)$"),
        ("defs/fmea.yaml", hugdefs.load_fmea()["fmea_version"],
         "docs/fmea.md", r"^## .*, v([0-9.]+)$"),
    ]
    for src, version, doc, pat in pairs:
        text = (repo() / doc).read_text(encoding="utf-8")
        m = re.search(pat, text, re.M)
        if not m or m.group(1) != version:
            bad.append(f"{src}={version} vs {doc}={m.group(1) if m else 'absent'}")
    return (not bad,
            f"{len(pairs) - len(bad)}/{len(pairs)} sources carry the same version as "
            f"the view they generate" + (f"; DISAGREE: {bad}" if bad else ""))


def g5_no_type_coercion():
    """No YAML type coercion in enum members.

    YAML 1.1 reads bare OFF / ON / NO / YES / N / Y as booleans. Unquoted, the
    PLD_STATE enum loads as [False, True]: the dictionary still renders, the OpenC3
    config still generates, and the wire codes are still 0 and 1 — the corruption is
    silent. Every enum member must load as a string.
    """
    defs = hugdefs.load_tlm_cmd()
    bad = []
    for p in points(defs):
        for v in p.get("enum_values", []):
            if not isinstance(v, str):
                bad.append(f"{p['mnemonic']}:{v!r}")
    for c in defs["commands"]:
        for a in c["args"]:
            for v in a.get("enum_values", []):
                if not isinstance(v, str):
                    bad.append(f"{c['mnemonic']}.{a['name']}:{v!r}")
    n = sum(len(p.get("enum_values", [])) for p in points(defs)) + \
        sum(len(a.get("enum_values", [])) for c in defs["commands"] for a in c["args"])
    return (not bad, f"{n - len(bad)}/{n} enum members load as strings"
                     + (f"; COERCED: {bad}" if bad else ""))


def g6_threshold_prose_binding():
    """Every structured command threshold appears in that command's rules prose.

    The record states these values inside normative sentences; the source carries them
    as numbers for the simulator. This is what forbids the two from drifting apart.
    """
    defs = hugdefs.load_tlm_cmd()
    checked, bad = 0, []
    for c in defs["commands"]:
        for name, value in (c.get("thresholds") or {}).items():
            checked += 1
            if hugdefs.fmt_num(value) not in c["rules"]:
                bad.append(f"{c['mnemonic']}.{name}={value}")
    return (not bad, f"{checked - len(bad)}/{checked} command thresholds occur in "
                     f"their own rules prose"
                     + (f"; ABSENT: {bad}" if bad else ""))


def g7_telemetry_structure():
    """Telemetry source invariants, including the transform the replay schema needs."""
    defs = hugdefs.load_tlm_cmd()
    pts = points(defs)
    problems = []
    if len(pts) != defs["frame"]["point_count"]:
        problems.append(f"point_count={defs['frame']['point_count']} but {len(pts)} points")
    mnemonics = [p["mnemonic"] for p in pts]
    if len(set(mnemonics)) != len(mnemonics):
        problems.append("duplicate mnemonics")
    # RS-5-02: the lowercase transform must stay bijective over the mnemonic set,
    # or a replay frame member could not be mapped back to one dictionary point.
    lowered = [m.lower() for m in mnemonics]
    if len(set(lowered)) != len(mnemonics):
        problems.append("lowercase mnemonic transform is not bijective")
    missing_bits = [p["mnemonic"] for p in pts if not p.get("bits")]
    if missing_bits:
        problems.append(f"no bit width: {missing_bits}")
    return (not problems,
            f"{len(pts)} points: count agrees with frame.point_count, mnemonics unique, "
            f"lowercase transform bijective (RS-5-02), every point sized"
            + (f"; PROBLEMS: {problems}" if problems else ""))


def g8_requirements_structure():
    """Requirement source invariants."""
    defs = hugdefs.load_requirements()
    rows = requirements_flat(defs)
    problems = []
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        problems.append("duplicate requirement identifiers")
    misfiled = [r["id"] for r in rows if not r["id"].startswith(r["group"] + "-")]
    if misfiled:
        problems.append(f"identifier outside its group: {misfiled}")
    bad_ver = [r["id"] for r in rows
               if not set(r["verification"]) <= VERIFICATION_METHODS
               or not r["verification"]]
    if bad_ver:
        problems.append(f"verification method outside {sorted(VERIFICATION_METHODS)}: {bad_ver}")
    uncited = [r["id"] for r in rows if not trace_tokens(r["trace"])]
    if uncited:
        problems.append(f"trace cell yields no citation: {uncited}")
    # A requirement struck in place names the owner ruling that struck it (D-019). The
    # ruling must be in the register: a strike citing a ruling that does not exist would
    # take a requirement out of the release on no authority at all.
    struck = [r for r in rows if "struck" in r]
    if struck:
        register = (repo() / "DECISIONS.md").read_text(encoding="utf-8")
        rulings = set(re.findall(r"^## (D-\d{3}) ", register, re.M))
        for r in struck:
            ruling = r["struck"]
            if not isinstance(ruling, str) or not re.fullmatch(r"D-\d{3}", ruling):
                problems.append(f"{r['id']}: struck must name a ruling as 'D-nnn', "
                                f"not {ruling!r}")
            elif ruling not in rulings:
                problems.append(f"{r['id']}: struck by {ruling}, which is not a ruling "
                                f"in DECISIONS.md")
    return (not problems,
            f"{len(rows)} requirements: identifiers unique and inside their group, "
            f"verification methods within the defined set, every trace cell yields at "
            f"least one citation, {len(struck)} struck in place, each by a ruling in "
            f"the register" + (f"; PROBLEMS: {problems}" if problems else ""))


def g9_config_digest():
    """The digest the ground system displays is the digest of the source it was built
    from (HUG-GND-006 / B10). A stale digest would make the pass-setup verification
    pass while the loaded configuration disagreed with the dictionary of record."""
    raw = (defs_dir() / "tlm_cmd.yaml").read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    cfg = (repo() / "gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/CONFIG_ID.txt").read_text(encoding="utf-8")
    m = re.search(r"^SOURCE_SHA256 ([0-9a-f]{64})$", cfg, re.M)
    ok = bool(m) and m.group(1) == actual
    return (ok, f"CONFIG_ID.txt digest is the sha256 of defs/tlm_cmd.yaml "
                f"({actual[:12]}…)" if ok else
                f"DIGEST STALE: config={m.group(1)[:12] if m else 'absent'}… "
                f"source={actual[:12]}…")


def g10_conformance_rules():
    """Every replay conformance rule is addressable and attributed.

    The rule identifiers are the anchors the Phase 6 evidence index maps claim ->
    executed case -> result -> polarity against (D0-17 item 5), and the identifiers
    the Phase 4 validator reports refusals by (RS-7-20). A duplicated or unattributed
    identifier breaks that mapping.
    """
    rules = hugdefs.load_replay_schema()["conformance_rules"]
    ids = [r.get("id") for r in rules]
    problems = []
    if len(set(ids)) != len(ids):
        problems.append("duplicate rule identifiers")
    malformed = [i for i in ids if not i or not re.fullmatch(r"RS-\d-\d{2}", str(i))]
    if malformed:
        problems.append(f"malformed identifiers: {malformed}")
    incomplete = [r.get("id") for r in rules
                  if not r.get("statement") or not r.get("source")]
    if incomplete:
        problems.append(f"no statement or no source section: {incomplete}")
    return (not problems,
            f"{len(rules)} conformance rules: identifiers unique and well-formed, each "
            f"carrying a statement and the section it comes from"
            + (f"; PROBLEMS: {problems}" if problems else ""))


#: The real repository, fixed at import. `repo()` moves during the self-test.
_REAL_ROOT = Path(__file__).resolve().parent.parent.parent

_PLACEHOLDER = re.compile(r"<[a-z][a-z0-9-]*>")
#: Repo-relative paths named in a mechanism. Anything that looks like a path this
#: repository owns must actually be in it -- an instruction pointing at a file that is
#: not there is worse than no instruction, because the operator will look for it.
_REPO_PATH = re.compile(r"\b((?:tools|defs|docs|gnd|campaign|procedures|sim|verification|"
                        r"ve|tests)/[A-Za-z0-9_./-]*[A-Za-z0-9_-])")


def g17_procedure_executability():
    """Every procedure step is executable from its own text (OF-014, HUG-OPS-001).

    THE DEFECT THIS EXISTS FOR. The procedures were written for someone who already
    knew the program. Every step named an action -- "review the pass plan", "bring up
    the ground system" -- and no step named the mechanism that performs it: which
    application, which file by path, which command, or where a recorded value is
    written. The Director, who is the operator the record names, halted at
    PROC-001-S01 because the first step could not be executed from its own text.

    Operator readiness had been "verified" the day before. That check confirmed the
    tools RUN and the documents REGENERATE, which is a property of the build; it could
    not fail on a procedure that regenerates perfectly and instructs nobody. This check
    can: it asks whether a step names a mechanism, not whether the generator works.

    Each clause below is one way a step reads as complete and instructs nobody.
    """
    procs = hugdefs.load_procedures()
    problems = []

    ctx = procs.get("operator_context") or {}
    for key in ("console", "shell", "pass_plan", "pass_id", "records"):
        if not str(ctx.get(key, "")).strip():
            problems.append(f"operator_context.{key} is missing: the precondition every "
                            f"step assumes is stated nowhere")

    for proc in procs["procedures"]:
        for step in proc["steps"]:
            sid = step["id"]
            m = step.get("mechanism") or {}
            if not m:
                problems.append(f"{sid} names an action and no mechanism to perform it")
                continue
            if not str(m.get("expect", "")).strip():
                problems.append(f"{sid} does not say what the operator should see when "
                                f"it worked, so it cannot be known to have worked")
            if not (str(m.get("open", "")).strip() or str(m.get("run", "")).strip()):
                problems.append(f"{sid} names neither a thing to open nor a command to "
                                f"run: the operator has no way in")
            # Every recorded field must say WHERE it is written and in what form.
            if step.get("records") and not str(m.get("record_to", "")).strip():
                problems.append(f"{sid} lists records {step['records']} and does not say "
                                f"where the operator writes them")
            # A path named in an instruction must exist, or the operator hunts for it.
            blob = " ".join(str(m.get(k, "")) for k in ("open", "run", "record_to"))
            for path in set(_REPO_PATH.findall(blob)):
                probe = path.split("<")[0].rstrip("/")
                if "<" in path or not probe:
                    continue
                # Resolved against the REAL repository, never against `repo()`.
                #
                # The self-test stages only the files this checker reads, so under a
                # mutation `repo()` points at a tree with no tools/, campaign/ or gnd/
                # in it -- and every path in every step would report missing. That is
                # not a hypothetical: it made all five of this check's red cases pass
                # for a reason unrelated to their mutation, and the GREEN case is what
                # exposed it by failing when it should have held. OF-008's shape,
                # caught by the polarity that exists to catch it.
                if not (_REAL_ROOT / probe).exists():
                    problems.append(f"{sid} points the operator at {probe}, which is "
                                    f"not in the repository")
            # A placeholder the operator cannot resolve is an instruction they cannot
            # follow. Declared ones are fine; undeclared ones are the defect.
            declared = set((m.get("placeholders") or {}))
            for token in set(_PLACEHOLDER.findall(blob)):
                if token not in declared and token not in ("<number>", "<percent>",
                                                           "<amps>", "<volts>",
                                                           "<seconds>", "<mnemonic>",
                                                           "<time>", "<n>"):
                    problems.append(f"{sid} uses {token} without saying how to "
                                    f"construct it")

    total = sum(len(p["steps"]) for p in procs["procedures"])
    return (not problems,
            f"{total} steps across {len(procs['procedures'])} procedures: each names a "
            f"mechanism, what success looks like, and where its recorded values go; "
            f"every repo path named exists and every placeholder is resolvable"
            + (f"; PROBLEMS: {problems[:6]}" if problems else ""))


#: The documents an OPERATOR reads. Everything else in the repository is build-facing.
OPERATOR_PRODUCTS = ("procedures/PROC-001.md", "procedures/PROC-002.md",
                     "procedures/PROC-003.md", "campaign/CAMPAIGN_PLAN.md",
                     "gnd/RUNBOOK.md")

#: Language that belongs to the build and not to the console. Each entry is
#: (pattern, why). A ruling identifier may be CITED — `(D-010)` is fine — but the
#: moment a document explains who ruled it, when, or whether it was provisional, it has
#: started telling the operator about the project instead of about the spacecraft.
_AUDIENCE_LEAKS = [
    (r"\bOF-\d{3}\b", "an open-findings entry: build register, not operator material"),
    (r"\bERR-\d{3}\b", "an errata entry: build register"),
    (r"\bHUG-G\d{3}", "a gate identifier"),
    (r"\bD0-\d+\b", "a design-record debt item"),
    (r"\bobligation\s+B\d+\b", "a build obligation"),
    (r"\bthe Director\b|\bDirector's\b", "names the reader instead of addressing them"),
    (r"\bthe owner\b|\bowner ruling\b|\baffirmed by\b",
     "authority narration; authority lives in DECISIONS.md"),
    (r"\bruled, not provisional\b|\bprovisional\b", "ruling status is not operator news"),
    (r"\bred case\b|\bgreen case\b|\bself-test\b|\bboth polarities\b",
     "verification apparatus"),
    (r"\bthe gate\b|\bgate run\b", "build gate history"),
    (r"\brecorded verbatim\b|\bverbatim in\b", "record-keeping narration"),
    (r"\bwas rejected\b.*\breading\b|\bthe alternative reading\b",
     "adjudication of an interpretation"),
    (r"\bsurfaced rather than settled\b|\bsettled silently\b", "build-process narration"),
]


def g18_operator_audience():
    """Operator documents address the operator, and nobody else (OF-015).

    THE DEFECT THIS EXISTS FOR. The remediation for OF-014 fixed the procedures'
    missing mechanisms and, in the same edit, wrote the BUILD's voice into them: who
    ruled what and when, which interpretation was rejected, that a boundary had been
    surfaced rather than settled silently, and the reader named in the third person.
    None of it is wrong; all of it is addressed to the wrong person. An operator at a
    console needs to know what to open and what to type, and a document that pauses to
    explain its own authorship is a document they have to read past.

    The rule this enforces, as the owner stated it: an operator document may CITE a
    ruling identifier at most, never discuss it. So `(D-010)` passes and "owner ruling
    D-010 made it a tool" does not.

    Same shape as the packaging leak sweep: a list of things that must not appear in a
    product, checked over the product itself rather than over the intention.
    """
    problems = []
    for rel in OPERATOR_PRODUCTS:
        # From the tree under test, so a mutation reaches this check; falling back to
        # the real one only if a partial stage omitted the file, which keeps a missing
        # stage from reporting as a leak in every document at once.
        path = repo() / rel
        if not path.exists():
            path = _REAL_ROOT / rel
        if not path.exists():
            problems.append(f"{rel} is named as an operator product and is not present")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("<!--"):
                continue                      # generator provenance, not operator text
            for pattern, why in _AUDIENCE_LEAKS:
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    problems.append(f"{rel}:{lineno} {m.group(0)!r} — {why}")
    return (not problems,
            f"{len(OPERATOR_PRODUCTS)} operator documents carry no register entries, no "
            f"authority narration and no build-gate history"
            + (f"; {len(problems)} LEAK(S): {problems[:8]}" if problems else ""))


#: The 22 worksheet rows of the HUG-G001 record: the rows the v0.1 fault set was
#: selected from and the campaign was planned and executed on. Frozen by owner ruling
#: D-020. A row added to the worksheets later is not one of them; FMEA Sec. 6.3 records
#: it instead of the Sec. 6 screen. This replaces the bare count of 22 rows, which a
#: deleted HUG-G001 row would satisfy as soon as one row had been added.
G001_FMEA_ROWS = tuple([f"FM-EPS-{i:02d}" for i in range(1, 12)]
                       + [f"FM-CDH-{i:02d}" for i in range(1, 6)]
                       + [f"FM-GND-{i:02d}" for i in range(1, 7)])


def g11_fmea_structure():
    """FMEA source invariants, including the ones the record's own checks assert.

    The Risk column is not stored — it is derived from severity x likelihood through
    the Sec. 3 matrix wherever it is rendered — so a row's rating and its risk class
    cannot disagree. What remains checkable here is that the ratings are in the
    defined sets, that every HUG-G001 row is present, that the Sec. 6 tables reference
    rows that exist, that the selected and excluded sets exactly partition the HUG-G001
    R2 rows, and that Sec. 6.3 lists exactly the R2 rows added after the selection
    (D-020). C15 asserts the same partition over the rendered document; this asserts
    it over the source.
    """
    defs = hugdefs.load_fmea()
    rows = list(gen_fmea.worksheet_rows(defs).values())
    fs = defs["fault_set"]
    problems = []

    ids = [r["id"] for r in rows]
    absent = [i for i in G001_FMEA_ROWS if i not in ids]
    if absent:
        problems.append(f"HUG-G001 worksheet row(s) missing: {absent}")
    if len(set(ids)) != len(ids):
        problems.append("duplicate FM identifiers")

    sev_set = {s["cat"] for s in defs["severity_definitions"]}
    lik_set = {s["level"] for s in defs["likelihood_definitions"]}
    bad_rating = [r["id"] for r in rows
                  if r["severity"] not in sev_set or r["likelihood"] not in lik_set]
    if bad_rating:
        problems.append(f"rating outside the Sec. 3 definitions: {bad_rating}")

    # every severity/likelihood pair must be defined in the matrix, or a Risk cell
    # could not be rendered at all
    unmapped = [r["id"] for r in rows
                if r["likelihood"] not in defs["criticality_matrix"].get(r["severity"], {})]
    if unmapped:
        problems.append(f"no criticality-matrix entry: {unmapped}")

    # disposition class must lead its own cell (the structured value and the prose
    # cannot disagree about which disposition a row carries)
    vocab = set(re.findall(r"\b([A-Z]{6,})\b", defs["disposition_vocabulary"]))
    mismatched = [r["id"] for r in rows
                  if r["disposition"].split()[0] != r["disposition_class"]]
    if mismatched:
        problems.append(f"disposition_class is not the cell's leading term: {mismatched}")
    outside = [r["id"] for r in rows if r["disposition_class"] not in vocab]
    if outside:
        problems.append(f"disposition outside the Sec. 3 vocabulary: {outside}")

    # Sec. 6 tables must reference rows that exist
    known = set(ids)
    dangling = [e["row"] for e in fs["selected"] + fs["exclusions"] + fs["post_selection"]
                if e["row"] not in known]
    if dangling:
        problems.append(f"Sec. 6 references a row that does not exist: {dangling}")

    # STOP HERE IF A RATING IS UNUSABLE. Everything below derives risk through the
    # criticality matrix, and risk_of() cannot be asked about a rating the matrix does
    # not define — it raises KeyError. The self-test scored that crash as CAUGHT, so
    # G11.m1 (severity III -> V) reported a red case working while demonstrating only
    # that the checker dies on the input. The detection above had already found the
    # violation and never got to report it. Returning here means the red case is
    # caught by the check's own finding, which is what a red case is supposed to show.
    # OF-008's shape, and the reason the verification run records passed_by_exception.
    if bad_rating or unmapped:
        return False, ("ratings unusable, so derived risk was not computed: "
                       + "; ".join(problems))

    # selected + excluded exactly partition the HUG-G001 R2 rows, and Sec. 6.3 lists
    # exactly the R2 rows added after the selection (C15's property, asserted over the
    # source rather than over the rendered tables). Every R2 row is in exactly one.
    r2_all = {r["id"] for r in rows if gen_fmea.risk_of(defs, r) == "R2"}
    r2 = r2_all & set(G001_FMEA_ROWS)
    r2_later = r2_all - set(G001_FMEA_ROWS)
    sel = {s["row"] for s in fs["selected"]}
    exc = {e["row"] for e in fs["exclusions"]}
    post_list = [s["row"] for s in fs["post_selection"]]
    post = set(post_list)
    if sel & exc:
        problems.append(f"row both selected and excluded: {sorted(sel & exc)}")
    if sel | exc != r2:
        problems.append(f"selected+excluded do not partition the HUG-G001 R2 set: "
                        f"missing={sorted(r2 - (sel | exc))} "
                        f"extra={sorted((sel | exc) - r2)}")
    if len(post) != len(post_list):
        problems.append("duplicate Sec. 6.3 rows")
    if post != r2_later:
        problems.append(f"Sec. 6.3 does not list exactly the R2 rows added after the "
                        f"selection: missing={sorted(r2_later - post)} "
                        f"extra={sorted(post - r2_later)}")

    # every exclusion cites one of the Sec. 6 criteria letters
    letters = {c["letter"] for c in fs["criteria"]}
    uncited = [e["row"] for e in fs["exclusions"]
               if e["criterion"].strip("()") not in letters]
    if uncited:
        problems.append(f"exclusion cites no criterion (a)-(e): {uncited}")

    return (not problems,
            f"{len(rows)} worksheet rows, all {len(G001_FMEA_ROWS)} HUG-G001 rows among "
            f"them: ratings within the Sec. 3 definitions and mapped by the criticality "
            f"matrix, dispositions leading their own cells, {len(sel)} selected + "
            f"{len(exc)} excluded exactly partition the {len(r2)} HUG-G001 R2 rows, every "
            f"exclusion citing a criterion, and Sec. 6.3 lists exactly the "
            f"{len(r2_later)} R2 row(s) added after the selection (D-020)"
            + (f"; PROBLEMS: {problems}" if problems else ""))


# Owner ruling D-001 item 2: absent limit sides are spelled as sentinels labelled as
# absent, and no sentinel may ever appear as a real threshold in any generated
# document or display.
#
# The pattern is built from the generator's own constants rather than typed here, so
# changing a sentinel value cannot leave the guard looking for the old one. Bounded so
# 1e+300 is not read as 1e+30 followed by a zero.
def _sentinel_pattern():
    forms = set()
    for v in (gen_openc3_config.ABSENT_LIMIT_LOW, gen_openc3_config.ABSENT_LIMIT_HIGH):
        forms |= {f"{v:g}", repr(v), f"{v:e}", f"{v:E}"}
    ordered = sorted(forms, key=len, reverse=True)
    return re.compile(r"(?<![\d.])(" + "|".join(re.escape(f) for f in ordered) + r")(?![\d])")


ABSENT_LABEL = "stand for absent"


def g12_sentinel_never_a_threshold():
    """No absent-limit sentinel appears as a real threshold anywhere generated.

    Owner ruling D-001 item 2. A sentinel is admissible in exactly one place: an
    OpenC3 LIMITS line whose immediately preceding lines say it stands for absent.
    In a generated DOCUMENT it is never admissible — a document has no place to put
    the caveat where an operator would read it with the number.

    Coverage is checked, not assumed: every generated view registered in
    hugdefs.GENERATED must be reachable by this scan. A new generated output — an
    VÉ display in Phase 4, a ground screen in Phase 3 — that is not covered makes
    this check FAIL rather than silently passing over it.
    """
    pattern = _sentinel_pattern()
    scanned, offences, uncovered = [], [], []

    for view in hugdefs.GENERATED:
        target = repo() / view
        if view.endswith("/"):
            if not target.is_dir():
                uncovered.append(view)
                continue
            # Compiled bytecode and other build droppings are not generated views.
            # Skipping them by name rather than by "whatever fails to decode" keeps an
            # undecodable file that SHOULD have been scanned a visible failure.
            files = sorted(f for f in target.rglob("*")
                           if f.is_file()
                           and "__pycache__" not in f.parts
                           and f.suffix not in (".pyc", ".pyo", ".gem"))
        else:
            if not target.is_file():
                uncovered.append(view)
                continue
            files = [target]
        if not files:
            uncovered.append(view)
        for f in files:
            rel = f.relative_to(repo()).as_posix()
            scanned.append(rel)
            lines = f.read_text(encoding="utf-8").split("\n")
            for n, line in enumerate(lines):
                if not pattern.search(line):
                    continue
                is_document = f.suffix.lower() in (".md", ".html", ".htm")
                labelled = any(ABSENT_LABEL in prev for prev in lines[max(0, n - 3):n])
                if is_document or not labelled:
                    offences.append(f"{rel}:{n + 1}")

    ok = not offences and not uncovered
    detail = f"{len(scanned)} generated files scanned across {len(hugdefs.GENERATED)} views"
    if offences:
        detail += f"; SENTINEL AS A THRESHOLD: {offences}"
    if uncovered:
        detail += f"; GENERATED VIEW NOT COVERED BY THIS SCAN: {uncovered}"
    if ok:
        detail += ("; every sentinel occurrence sits in an OpenC3 LIMITS line labelled "
                   "as standing for absent, and no generated document carries one")
    return ok, detail



# Owner-dispositioned EPS values and the requirement whose text states each one.
# Same discipline as G6: a value the simulator computes from must occur in the
# normative sentence that dispositioned it, or the two have drifted.
EPS_VALUE_BINDINGS = [
    ("envelope", "battery_capacity_wh", "HUG-EPS-005", "38"),
    ("envelope", "bus_voltage_v", "HUG-EPS-005", "5.0"),
    ("envelope", "array_peak_w", "HUG-EPS-005", "17"),
    ("envelope", "bus_load_w", "HUG-EPS-005", "4"),
    ("envelope", "payload_load_w", "HUG-EPS-005", "3"),
    ("envelope", "charge_efficiency", "HUG-EPS-001", "0.95"),
    ("envelope", "discharge_efficiency", "HUG-EPS-001", "0.95"),
]
EPS_LADDER_BINDINGS = [
    ("autonomous_entry_soc_pct", "LOW_POWER", "HUG-EPS-003", "30"),
    ("autonomous_entry_soc_pct", "SAFE", "HUG-EPS-003", "20"),
    ("recovery_floor_soc_pct", "NOMINAL", "HUG-CMD-006", "35"),
    ("recovery_floor_soc_pct", "LOW_POWER", "HUG-CMD-006", "25"),
]


def g13_eps_envelope_binding():
    """Every dispositioned EPS value agrees with the requirement text that states it.

    HUG-EPS-005 requires the envelope be "recorded in `defs/` and used consistently by
    model, dictionary limits, and FMEA". This is what makes "consistently" checkable:
    the simulator reads these numbers, and each one is bound to the normative sentence
    it came from, so a value cannot be changed in the source without the record
    disagreeing out loud.
    """
    eps = hugdefs._load("eps.yaml")
    reqs = {r["id"]: r["text"] for r in requirements_flat(hugdefs.load_requirements())}
    problems, checked = [], 0

    for section, key, req_id, spelling in EPS_VALUE_BINDINGS:
        checked += 1
        value = eps[section][key]
        # The numeric value must BE the value, and the record's own spelling of it
        # must occur in the requirement. Comparing shortest-form spellings instead
        # would miss that the record writes "5.0 V" where `%g` gives "5".
        if float(value) != float(spelling):
            problems.append(f"{section}.{key}={value} is not {spelling}")
        elif spelling not in reqs.get(req_id, ""):
            problems.append(f"{section}.{key}={spelling} absent from {req_id}")

    ladder = eps["mode_ladder"]
    for section, key, req_id, spelling in EPS_LADDER_BINDINGS:
        checked += 1
        value = ladder[section][key]
        if float(value) != float(spelling):
            problems.append(f"mode_ladder.{section}.{key}={value} is not {spelling}")
        elif spelling not in reqs.get(req_id, ""):
            problems.append(f"mode_ladder.{section}.{key}={spelling} absent from {req_id}")

    checked += 1
    inhibit = hugdefs.fmt_num(ladder["payload_activation_inhibit_soc_pct"])
    if inhibit not in reqs.get("HUG-CMD-002", ""):
        problems.append(f"payload activation inhibit {inhibit} absent from HUG-CMD-002")

    checked += 1
    stuck = hugdefs.fmt_num(eps["faults"]["stuck_load"]["power_w"])
    if stuck not in reqs.get("HUG-EPS-004", ""):
        problems.append(f"stuck load {stuck} W absent from HUG-EPS-004")

    # Derived consistency: the two strings must sum to the dispositioned array peak.
    checked += 1
    env = eps["envelope"]
    if env["array_string_peak_w"] * env["array_string_count"] != env["array_peak_w"]:
        problems.append(
            f"{env['array_string_count']} strings of {env['array_string_peak_w']} W "
            f"do not sum to the dispositioned array peak {env['array_peak_w']} W")

    # The hysteresis property the mode-authority rule exists to provide.
    checked += 1
    if not (ladder["recovery_floor_soc_pct"]["NOMINAL"]
            > ladder["autonomous_entry_soc_pct"]["LOW_POWER"]
            and ladder["recovery_floor_soc_pct"]["LOW_POWER"]
            > ladder["autonomous_entry_soc_pct"]["SAFE"]):
        problems.append("a recovery floor does not sit above its autonomous entry "
                        "point; a commanded recovery could immediately re-trip")

    return (not problems,
            f"{checked - len(problems)}/{checked} dispositioned EPS values agree with "
            f"the requirement text that states them, the strings sum to the array peak, "
            f"and both recovery floors sit above their entry points"
            + (f"; PROBLEMS: {problems}" if problems else ""))



# Every record document, and where its version identity appears inside it.
RECORD_DOCUMENTS = [
    "docs/concept_brief.md", "docs/conops.md", "docs/fmea.md",
    "docs/requirements.md", "docs/tlm_cmd_dictionary.md", "defs/replay_schema.md",
]


def g14_document_version_self_agreement():
    """Each record document agrees with itself about its own version.

    EARNED BY A REAL MISS. When CONOPS advanced v0.8 -> v0.9 under ruling D-004, the
    status row and the changelog were updated and the TITLE LINE was not. Nothing caught
    it: G4 binds a version only for the three documents generated from a `defs/` source,
    and the three prose documents have no source to bind to. A document whose title and
    status disagree about which revision it is gets cited by version in the gate packet
    and in every companion-baseline list, so the disagreement travels.

    The invariant checked is deliberately order-free. "Newest changelog entry" is not
    well defined across this record - the concept brief's changelog ascends, the CONOPS
    and replay schema descend, and the FMEA's is neither (v0.11 sits second). What IS
    well defined is that a document's declared version must HAVE a changelog entry: a
    revision that advanced the version without logging it is exactly as broken as one
    that logged it without advancing the title.

      - the version in the document's opening lines is its declared version
      - if it carries a Status version, that must equal the declared version
      - if it carries a changelog, the declared version must appear among its entries
    """
    problems, checked = [], 0
    for rel in RECORD_DOCUMENTS:
        text = (repo() / rel).read_text(encoding="utf-8")
        head = "\n".join(text.split("\n")[:6])

        declared = re.search(r"v(\d+\.\d+)", head)
        if not declared:
            problems.append(f"{rel}: no version in its opening lines")
            continue
        declared = declared.group(1)
        checked += 1

        status = re.search(r"(?:\| Status \||\*\*Status:\*\*)\s*v(\d+\.\d+)", text)
        if status and status.group(1) != declared:
            problems.append(f"{rel}: title says v{declared}, Status says "
                            f"v{status.group(1)}")

        entries = re.findall(r"^- \*\*v(\d+\.\d+)", text, re.M)
        if entries and declared not in entries:
            problems.append(f"{rel}: declared v{declared} has no changelog entry "
                            f"(entries: v{', v'.join(entries[:4])}...)")

    return (not problems,
            f"{checked}/{len(RECORD_DOCUMENTS)} record documents agree with themselves: "
            f"title version matches the Status version where stated, and carries a "
            f"changelog entry where a changelog exists"
            + (f"; PROBLEMS: {problems}" if problems else ""))



# Every record document, and the names other documents refer to it by. Longest first,
# so "TLM/CMD Dictionary" is matched before the bare "Dictionary" inside it.
DOCUMENT_ALIASES = [
    ("TLM/CMD Dictionary", "docs/tlm_cmd_dictionary.md"),
    ("Concept Brief", "docs/concept_brief.md"),
    ("Replay Schema", "defs/replay_schema.md"),
    ("Requirements", "docs/requirements.md"),
    ("Dictionary", "docs/tlm_cmd_dictionary.md"),
    ("CONOPS", "docs/conops.md"),
    ("FMEA", "docs/fmea.md"),
]

CROSS_REF = re.compile(
    r"\b(" + "|".join(re.escape(n) for n, _ in DOCUMENT_ALIASES) + r")\s+v(\d+\.\d+)")

# A reference is PROVENANCE - a statement about which revision something happened at -
# when it sits in one of these regions. Everything else asserts CURRENCY.
HISTORICAL_HEADING = re.compile(r"^#+ .*(Changelog|[Dd]isposition ledger|Provenance)")
HISTORICAL_LINE = re.compile(
    r"^\s*-\s\*\*v\d"                      # a changelog entry
    r"|^\s*\d+\.\s"                        # a numbered ledger item
    r"|\*\*Resolution \(owner, \d{4}-"     # a date-stamped owner resolution
)


def _version_tuple(text):
    return tuple(int(x) for x in text.split("."))


def _declared_version(rel):
    head = "\n".join((repo() / rel).read_text(encoding="utf-8").split("\n")[:6])
    found = re.search(r"v(\d+\.\d+)", head)
    return found.group(1) if found else None


# Stale currency claims known to the build and awaiting an owner ruling.
#
# EMPTY. Its one entry - FMEA GR-02's bare "TLM/CMD Dictionary v0.2" - was retired by
# owner ruling D-006, which resolved the ambiguity in the RECORD rather than in this
# checker: GR-02 now states its ratification anchor and the anchor's currency condition,
# so it is a well-formed statement rather than something a register had to hold open.
#
# The mechanism stays for the next finding that genuinely needs a ruling before it can
# be fixed. Adding an entry is an owner decision, not an edit - it declares a known
# inconsistency in the record. A test asserts this stays empty, so an entry cannot
# appear silently.
KNOWN_STALE_CURRENCY_CLAIMS = {}

# A RATIFICATION ANCHOR names the revision something was ratified at AND states that it
# still holds. Both halves are required, and that is the whole point: the anchor phrase
# alone would be a way to spell any stale citation as provenance, so the sentence must
# also carry a currency condition a later reader can check. Owner ruling D-006
# established the form:
#
#   "Limits are those ratified at TLM/CMD Dictionary v0.2 and unchanged through the
#    current dictionary; any limit change reopens this analysis."
#
# An anchor phrase WITHOUT a currency condition is read as a currency claim and must
# match the referenced document exactly - the conservative direction, red-cased below.
ANCHOR_PHRASE = re.compile(r"\bratified at\b", re.I)
CURRENCY_CONDITION = re.compile(r"\bunchanged through the current\b", re.I)


def _is_ratification_anchor(line, position):
    """Is the reference at `position` inside a ratification-anchor SENTENCE?

    Scoped to the sentence, not the line. Line scoping had a hole the suite found:
    one legitimate anchor sentence granted anchor status to every other reference
    sharing its line, so a stale citation could be hidden by placing it beside a
    well-formed one. A cell in a Markdown table is a single line and can hold several
    sentences, which is exactly where that would have happened.
    """
    before = line.rfind(". ", 0, position)
    start = 0 if before < 0 else before + 2
    after = line.find(". ", position)
    end = len(line) if after < 0 else after
    sentence = line[start:end]
    return bool(ANCHOR_PHRASE.search(sentence)
                and CURRENCY_CONDITION.search(sentence))


def g15_cross_document_version_references():
    """Every cross-document version reference, checked against the referenced document.

    Ruled by the owner at D-005 after a companion-baseline citation went stale: the
    concept brief said "CONOPS v0.8" for as long as it took someone to notice, and
    nothing checked it.

    TWO KINDS OF REFERENCE, AND THEY NEED DIFFERENT ASSERTIONS. Flat equality would be
    wrong and would demand rewriting history:

      CURRENCY claims say what the record IS now - "Current companion baseline —
      CONOPS v0.9". These must equal the referenced document's actual version. This is
      the class that goes stale.

      PROVENANCE citations say which revision something HAPPENED at - FMEA §7's
      "Implemented as HUG-CMD-006 ... in Requirements v0.3", or GR-02's "Limits are
      those of the TLM/CMD Dictionary v0.2". Requirements v0.3 is where that change
      was made; forcing it to v0.12 would make the record lie about its own history.
      These are checked differently: the cited revision must EXIST - at or below the
      referenced document's current version - which catches a typo, an invented
      revision, or a citation of a version that has not happened yet.

    Provenance is identified by region, not by guesswork: changelog sections,
    disposition-ledger sections, provenance sections, numbered ledger items, and
    date-stamped owner resolutions. Everything else is read as a currency claim, which
    is the conservative direction - an ambiguous reference is checked more strictly,
    not less.
    """
    actual = {rel: _declared_version(rel) for _, rel in DOCUMENT_ALIASES}
    missing = sorted({rel for rel, v in actual.items() if v is None})
    if missing:
        return False, f"could not read a declared version from: {missing}"

    stale, impossible = [], []
    currency = provenance = anchors = known = 0

    for rel in sorted({r for _, r in DOCUMENT_ALIASES}):
        in_historical_section = False
        for number, line in enumerate((repo() / rel).read_text(encoding="utf-8")
                                      .split("\n"), 1):
            if line.startswith("#"):
                in_historical_section = bool(HISTORICAL_HEADING.match(line))
            historical = in_historical_section or bool(HISTORICAL_LINE.search(line))
            for found in CROSS_REF.finditer(line):
                name, cited = found.group(1), found.group(2)
                match_start = found.start()
                target = dict(DOCUMENT_ALIASES)[name]
                if rel == target:
                    continue                       # a self-reference; G14 owns that
                if historical:
                    provenance += 1
                    if _version_tuple(cited) > _version_tuple(actual[target]):
                        impossible.append(
                            f"{rel}:{number} cites {name} v{cited}, which does not "
                            f"exist — that document is at v{actual[target]}")
                elif _is_ratification_anchor(line, match_start):
                    anchors += 1
                    if _version_tuple(cited) > _version_tuple(actual[target]):
                        impossible.append(
                            f"{rel}:{number} anchors on {name} v{cited}, which does "
                            f"not exist — that document is at v{actual[target]}")
                else:
                    currency += 1
                    if cited != actual[target]:
                        if (rel, name, cited) in KNOWN_STALE_CURRENCY_CLAIMS:
                            known += 1
                            continue
                        stale.append(
                            f"{rel}:{number} claims {name} v{cited} as current; "
                            f"it is v{actual[target]}")

    problems = stale + impossible
    detail = (f"{currency} currency claims match the referenced document's actual "
              f"version; {provenance} provenance citations and {anchors} ratification "
              f"anchors all name a revision that exists")
    if known:
        detail += (f"; {known} known finding(s) registered and awaiting an owner "
                   f"ruling, listed in KNOWN_STALE_CURRENCY_CLAIMS")
    if problems:
        detail += f"; PROBLEMS: {problems}"
    return not problems, detail



GROUND_PROJECT = "gnd/openc3"
CREDENTIAL_VAR = re.compile(
    r"^(OPENC3_\S*(?:PASSWORD|USERNAME)|SECRET_KEY_BASE)=(.*)$", re.M)


def g16_ground_deployment_pin():
    """The vendored COSMOS project matches the deployment pinned in defs/ground.yaml.

    Owner instruction, recorded at D-007: pin the OpenC3 version rather than tracking
    latest, and keep HUGINN off the ports the operator's separate training demo binds.

    Four properties, each of which has bitten real projects:

      PINNED, NOT LATEST. Every image resolves through ${OPENC3_TAG}, and that tag is
      the version defs/ground.yaml names. A ground system that changed version between
      campaign passes would break HUG-SYS-003's reproducibility without leaving a diff,
      and would make HUG-GND-006's configuration-digest check meaningless - the thing
      doing the checking has to be fixed too.

      NO PORT COLLISION. The operator runs a stock COSMOS demo for training on 2900 and
      2943. HUGINN binds 2910 and 2953. The check asserts the two sets are disjoint
      rather than asserting HUGINN's specific numbers, so moving either is safe as long
      as they stay apart.

      OWN PROJECT. COMPOSE_PROJECT_NAME is what puts HUGINN's containers, networks and
      named volumes in their own namespace. Without it, `docker compose` derives the
      name from the directory and two stacks can share volumes - which is exactly how
      campaign evidence would end up mixed with training data.

      NO COMMITTED CREDENTIAL. The template carries generation markers only. A working
      credential committed to a repository that may become public outlives whatever
      posture made it look safe.

    Hermetic: reads files only. It must pass on a machine with no Docker running, which
    is also the machine state the gate will most often be run on.
    """
    project = repo() / GROUND_PROJECT
    ground = hugdefs._load("ground.yaml")
    problems, checked = [], 0

    compose_path = project / "compose.yaml"
    env_path = project / ".env.template"
    for path in (compose_path, env_path):
        if not path.exists():
            return False, f"vendored project incomplete: {path} is missing"
    compose = compose_path.read_text(encoding="utf-8")
    env = env_path.read_text(encoding="utf-8")

    def env_var(name):
        found = re.search(rf"^{name}=(.*)$", env, re.M)
        return found.group(1).strip() if found else None

    # --- pinned version
    checked += 1
    pinned = str(ground["openc3"]["version"])
    tag = env_var("OPENC3_TAG")
    if tag != pinned:
        problems.append(f"defs/ground.yaml pins OpenC3 {pinned} but .env.template has "
                        f"OPENC3_TAG={tag}")
    if tag in ("latest", "", None):
        problems.append(f"OPENC3_TAG={tag!r} tracks a moving target; the deployment "
                        f"must be pinned")

    # --- every image goes through the pinned tag
    checked += 1
    images = re.findall(r'^\s*image:\s*"?([^"\n]+)"?\s*$', compose, re.M)
    unpinned = [i for i in images if "${OPENC3_TAG}" not in i]
    if unpinned:
        problems.append(f"image(s) not resolving through the pinned tag: {unpinned}")
    if not images:
        problems.append("no image references found in compose.yaml — the scan is "
                        "looking in the wrong place")

    # --- host ports, and disjointness from the training demo
    checked += 1
    published = [int(m) for m in
                 re.findall(r'^\s*-\s*"127\.0\.0\.1:(\d+):\d+"\s*$', compose, re.M)]
    declared = sorted(int(v) for v in ground["deployment"]["host_ports"].values())
    if sorted(published) != declared:
        problems.append(f"compose publishes {sorted(published)} but defs/ground.yaml "
                        f"declares {declared}")
    reserved = set(int(p) for p in ground["deployment"]["reserved_by_training_demo"])
    collision = sorted(set(published) & reserved)
    if collision:
        problems.append(f"host port(s) {collision} collide with the operator's training "
                        f"demo; HUGINN must not bind them")

    # --- own project namespace
    checked += 1
    name = env_var("COMPOSE_PROJECT_NAME")
    if name != ground["deployment"]["compose_project_name"]:
        problems.append(f"COMPOSE_PROJECT_NAME={name!r} does not match the pinned "
                        f"project name {ground['deployment']['compose_project_name']!r}")

    # --- demo targets off
    #
    # OPENC3_DEMO is a PRESENCE flag, not a boolean. init.sh reads
    # `if [ ! -z $OPENC3_DEMO ]`, so ANY non-empty value installs the demo -
    # including 0 and false. Measured in the 7.2.1 image; see .env.template.
    #
    # The first version of this check compared the value against "0" and passed
    # green while the demo was installing. A check that encodes the builder's
    # model of a variable rather than the consumer's reading of it certifies the
    # bug. Suppression means absent-or-empty, and nothing else.
    checked += 1
    if ground["deployment"]["demo_targets"]:
        raise AssertionError(
            "defs/ground.yaml sets demo_targets true; HUG-GND-006 (B10) requires "
            "the loaded configuration be HUGINN's alone, so this check has no "
            "correct behaviour for that setting")
    demo = env_var("OPENC3_DEMO")          # None when absent or commented out
    if demo is not None and demo.strip() != "":
        problems.append(
            f"OPENC3_DEMO={demo!r} is a non-empty value, which INSTALLS the demo "
            f"plugin - init.sh tests this variable for presence, not truth, so "
            f"'0' and 'false' both switch it ON. Comment the line out or leave "
            f"the value empty (DECISIONS.md D-009)")

    # --- the instance's own external URL points at its own port
    #
    # Upstream ships OPENC3_EXTERNAL_URL=http://localhost:2900, which is the port
    # the operator's training demo answers on. Left at the default, HUGINN's UI
    # hands out links into the other instance - a cross-instance leak that the
    # published-port check above cannot see, because the collision is in a value
    # rather than in a binding.
    checked += 1
    external = env_var("OPENC3_EXTERNAL_URL") or ""
    external_port = re.search(r":(\d+)\s*$", external)
    if not external_port:
        problems.append(f"OPENC3_EXTERNAL_URL={external!r} names no port")
    elif int(external_port.group(1)) in reserved:
        problems.append(
            f"OPENC3_EXTERNAL_URL={external!r} points at port "
            f"{external_port.group(1)}, which defs/ground.yaml reserves for the "
            f"operator's training demo; HUGINN's UI would link into it")
    elif int(external_port.group(1)) not in published:
        problems.append(
            f"OPENC3_EXTERNAL_URL={external!r} names port "
            f"{external_port.group(1)}, which this stack does not publish "
            f"{sorted(published)}")

    # --- no committed credential
    checked += 1
    leaked = [n for n, v in CREDENTIAL_VAR.findall(env) if v.strip() != "__GENERATE__"]
    if leaked:
        problems.append(f"credential value(s) committed in .env.template: {leaked}")
    if not CREDENTIAL_VAR.findall(env):
        problems.append("no credential variables found in .env.template — the leak "
                        "scan is looking in the wrong place")

    # --- neither generated credential file may ever be tracked
    #
    # The ACL was the hole this check originally had: it scanned .env.template for
    # committed credentials and said nothing about openc3-redis/users.acl, which
    # carried upstream's published password hashes. A credential is a credential
    # whether or not it is hashed.
    for generated in (f"{GROUND_PROJECT}/.env",
                      f"{GROUND_PROJECT}/openc3-redis/users.acl"):
        checked += 1
        gitignore = (repo() / ".gitignore").read_text(encoding="utf-8")
        if generated not in gitignore:
            problems.append(f"{generated} is not gitignored")

    checked += 1
    acl_template = project / "openc3-redis" / "users.acl.template"
    if not acl_template.exists():
        problems.append("openc3-redis/users.acl.template is missing")
    else:
        acl = acl_template.read_text(encoding="utf-8")
        hashes = re.findall(r"#([0-9a-f]{64})", acl)
        if hashes:
            problems.append(f"{len(hashes)} password hash(es) committed in "
                            f"users.acl.template; it must carry placeholders only")

    return (not problems,
            f"{checked - len(problems)}/{checked} ground-deployment properties hold: "
            f"OpenC3 pinned at {pinned} across {len(images)} images, host ports "
            f"{sorted(published)} disjoint from the training demo's {sorted(reserved)}, "
            f"own compose project {name!r}, demo targets off, no committed credential"
            + (f"; PROBLEMS: {problems}" if problems else ""))


CHECKS = [
    ("G1", "round trip: every generated view is what its source generates", g1_round_trip),
    ("G2", "generation is deterministic", g2_deterministic),
    ("G3", "replay schema: one identity across prose title, prose member, machine form",
     g3_schema_identity),
    ("G4", "each source's version equals the version in the view it generates",
     g4_document_identities),
    ("G5", "no YAML type coercion in enum members", g5_no_type_coercion),
    ("G6", "command thresholds agree with the prose that states them", g6_threshold_prose_binding),
    ("G7", "telemetry source: counts, uniqueness, bijective transform, sizing",
     g7_telemetry_structure),
    ("G8", "requirement source: identifiers, grouping, methods, citations",
     g8_requirements_structure),
    ("G9", "displayed configuration digest is the digest of its source (B10)", g9_config_digest),
    ("G10", "replay conformance rules are uniquely addressable and attributed",
     g10_conformance_rules),
    ("G11", "FMEA source: ratings, dispositions, and the R2 partition", g11_fmea_structure),
    ("G12", "no absent-limit sentinel appears as a real threshold (ruling D-001)",
     g12_sentinel_never_a_threshold),
    ("G13", "dispositioned EPS values agree with the requirements that state them",
     g13_eps_envelope_binding),
    ("G14", "each record document agrees with itself about its own version",
     g14_document_version_self_agreement),
    ("G15", "cross-document version references match the document they reference",
     g15_cross_document_version_references),
    ("G17", "procedure source: every step executable from its own text (OF-014)",
     g17_procedure_executability),
    ("G18", "operator documents address the operator and nobody else (OF-015)",
     g18_operator_audience),
    ("G16", "ground deployment matches its pin: version, ports, project, no secrets",
     g16_ground_deployment_pin),
]


# ------------------------------------------------------------------------- helpers

def _devnull():
    return "NUL" if sys.platform == "win32" else "/dev/null"


def _render_all():
    """Rendered bytes of every generated view, without touching disk."""
    tlm, reqs = hugdefs.load_tlm_cmd(), hugdefs.load_requirements()
    version, digest = gen_openc3_config.source_digest()
    return {
        "dictionary": gen_dictionary.build(tlm),
        "requirements": gen_requirements.build(reqs),
        "fmea": gen_fmea.build(hugdefs.load_fmea()),
        "tlm.txt": gen_openc3_config.build_tlm(tlm, version, digest),
        "cmd.txt": gen_openc3_config.build_cmd(tlm, version, digest),
        "CONFIG_ID.txt": gen_openc3_config.build_config_id(version, digest),
    }


# ----------------------------------------------------- two-polarity mutation suite
#
# Each entry: (relative file, mutation, polarity). "red" mutations MUST turn their
# check red; "green" cases are valid-but-tricky forms the check must NOT flag.

def _sub(old, new, count=1):
    def f(t):
        assert t.count(old) >= count, f"mutation anchor not found: {old!r}"
        return t.replace(old, new, count)
    return f


def _append(extra):
    return lambda t: t + extra


def _alter_version_after(anchor, bump=1):
    """Change the first vN.M that follows `anchor`, whatever it currently is.

    Version-pinned mutation anchors have broken three times now — every time a
    document advanced, a case that hard-coded the old version stopped matching and the
    self-test died on a missing anchor rather than on a real failure. These cases are
    about a version being WRONG, not about which version it is, so they should not
    name one.
    """
    def f(text):
        index = text.index(anchor)
        match = re.compile(r"v(\d+)\.(\d+)").search(text, index)
        assert match, f"no version found after {anchor!r}"
        altered = f"v{match.group(1)}.{int(match.group(2)) + bump}"
        return text[:match.start()] + altered + text[match.end():]
    return f


#: Which requirements each check discharges, for the traceability matrix (B3).
#:
#: Declared HERE, beside the checks, rather than in the matrix — a matrix that carried
#: its own copy of this mapping would be the hand-maintained matrix HUG-VER-001
#: prohibits, and would go stale the first time a check changed what it looks at.
#:
#: A check may legitimately discharge nothing: G2 (determinism) and G14 (a document
#: agreeing with itself about its version) are hygiene over the generation machinery,
#: not evidence for a requirement. They are listed with an empty tuple rather than
#: omitted, so that a check ADDED and never mapped is visibly absent from this dict
#: instead of silently indistinguishable from one deliberately mapped to nothing.
CHECK_VERIFIES = {
    "G17": ("HUG-OPS-001",),
    "G18": ("HUG-OPS-001",),
    "G1": (),
    "G2": (),
    "G3": ("HUG-UI-003",),
    "G4": (),
    "G5": (),
    "G6": ("HUG-CMD-002", "HUG-CMD-003"),
    "G7": ("HUG-GND-001",),
    "G8": ("HUG-VER-001",),
    "G9": ("HUG-GND-006",),
    "G10": ("HUG-UI-003",),
    "G11": (),
    "G12": ("HUG-GND-002",),
    "G13": ("HUG-EPS-005",),
    "G14": (),
    "G15": (),
    "G16": ("HUG-GND-001", "HUG-GND-006"),
}


MUTATIONS = {
    # G1 — a hand edit to a generated view, in each view, must be caught.
    "G1": [
        ("docs/tlm_cmd_dictionary.md", _sub("| EPS_BATT_V | Battery voltage",
                                            "| EPS_BATT_V | Battery potential"), "red"),
        ("docs/requirements.md", _sub("## HUG-SYS: System", "## HUG-SYS: Systems"), "red"),
        ("gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/cmd_tlm/tlm.txt",
         _sub("LIMITS DEFAULT 1 ENABLED 6.8 7.2 8.3 8.5",
              "LIMITS DEFAULT 1 ENABLED 6.9 7.2 8.3 8.5"), "red"),
        # A limit edited in the SOURCE, with the view left stale — the direction a
        # careless regeneration-skip actually takes.
        ("defs/tlm_cmd.yaml", _sub("          rh: 8.5", "          rh: 8.6"), "red"),
        # GREEN: a source edit that changes no rendered byte must not be flagged.
        # This is a comment in the REQUIREMENTS source. The equivalent edit to
        # defs/tlm_cmd.yaml is NOT green and is a red case under G9: CONFIG_ID.txt
        # carries the sha256 of that file's bytes, so there is no such thing as a
        # cosmetic edit to it — a comment changes the digest the ground system
        # displays at pass setup, and the generated config is genuinely stale until
        # regenerated. That asymmetry is the B10 binding working, and it is recorded
        # here because it is the kind of thing a later reader would otherwise
        # rediscover as a puzzling failure.
        ("defs/requirements.yaml", _append("\n# a trailing comment renders nothing\n"),
         "green"),
    ],
    # G3 — the schema identity broken at each of the three sites.
    "G3": [
        ("defs/replay_schema.yaml", _sub("schema: '0.9'", "schema: '1.0'"), "red"),
        ("defs/replay_schema.md", _sub("Interface Definition, v0.9 (schema 0.9)",
                                       "Interface Definition, v0.9 (schema 0.8)"), "red"),
        ("defs/replay_schema.md", _sub('`"0.9"` for this definition',
                                       '`"0.7"` for this definition'), "red"),
    ],
    # G4 — a source version bumped without regenerating its view.
    "G4": [
        ("defs/tlm_cmd.yaml", _sub("dictionary_version: '0.5'",
                                   "dictionary_version: '0.6'"), "red"),
        ("defs/requirements.yaml", _sub("requirements_version: '0.13'",
                                        "requirements_version: '0.14'"), "red"),
    ],
    # G5 — the exact YAML 1.1 trap, unquoted.
    "G5": [
        ("defs/tlm_cmd.yaml", _sub("        enum_values: ['OFF', 'ON']\n"
                                   "        units: 'n/a'",
                                   "        enum_values: [OFF, ON]\n"
                                   "        units: 'n/a'"), "red"),
        # GREEN: 'NO' and 'ON' as QUOTED members are ordinary strings, not booleans.
        ("defs/tlm_cmd.yaml", _sub("          annunciates: ['SAFE']",
                                   "          annunciates: ['SAFE', 'NO', 'ON']"), "green"),
    ],
    # G6 — a threshold changed in the structure but not in the prose, and vice versa.
    "G6": [
        ("defs/tlm_cmd.yaml", _sub("      payload_on_soc_min_pct: 40",
                                   "      payload_on_soc_min_pct: 45"), "red"),
        ("defs/tlm_cmd.yaml", _sub("      recovery_floor_low_power_pct: 25",
                                   "      recovery_floor_low_power_pct: 20"), "red"),
    ],
    # G7 — telemetry source invariants.
    "G7": [
        ("defs/tlm_cmd.yaml", _sub("  point_count: 16", "  point_count: 15"), "red"),
        ("defs/tlm_cmd.yaml", _sub("      - mnemonic: EPS_SA2_I",
                                   "      - mnemonic: EPS_SA1_I"), "red"),
        ("defs/tlm_cmd.yaml", _sub("        bits: 32\n        units: 'V'",
                                   "        units: 'V'"), "red"),
    ],
    # G8 — requirement source invariants.
    "G8": [
        ("defs/requirements.yaml", _sub("      - id: HUG-SYS-002",
                                        "      - id: HUG-SYS-001"), "red"),
        ("defs/requirements.yaml", _sub("      - id: HUG-EPS-001",
                                        "      - id: HUG-GND-001"), "red"),
        ("defs/requirements.yaml", _sub("        verification: ['T']\n"
                                        "        trace: 'NEED-02, NEED-03'",
                                        "        verification: ['X']\n"
                                        "        trace: 'NEED-02, NEED-03'"), "red"),
        ("defs/requirements.yaml", _sub("        trace: 'NEED-02, NEED-03'",
                                        "        trace: 'to be determined'"), "red"),
        # GREEN: a multi-method row is ordinary, not a violation.
        ("defs/requirements.yaml", _sub("        verification: ['T']\n"
                                        "        trace: 'NEED-02, NEED-03'",
                                        "        verification: ['T', 'I', 'D', 'A']\n"
                                        "        trace: 'NEED-02, NEED-03'"), "green"),
        # RED: a strike citing a ruling that is not in the register, one that is not a
        # ruling key at all, and one that names nothing; and the ruling itself removed
        # from the register while the strike still cites it.
        ("defs/requirements.yaml", _sub("        struck: 'D-019'",
                                        "        struck: 'D-999'"), "red"),
        ("defs/requirements.yaml", _sub("        struck: 'D-019'",
                                        "        struck: 'D19'"), "red"),
        ("defs/requirements.yaml", _sub("        struck: 'D-019'",
                                        "        struck: ''"), "red"),
        ("DECISIONS.md", _sub("\n## D-019 — ", "\n## D-0l9 — "), "red"),
    ],
    # G9 — the displayed digest left stale after the source changed.
    "G9": [
        ("defs/tlm_cmd.yaml", _append("\n# any source change invalidates the digest\n"),
         "red"),
        ("gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/CONFIG_ID.txt",
         _sub("SOURCE_SHA256 ", "SOURCE_SHA256 0"), "red"),
    ],
    # G10 — rule identifiers duplicated, malformed, or unattributed.
    "G10": [
        ("defs/replay_schema.yaml", _sub("  - id: RS-7-02", "  - id: RS-7-01"), "red"),
        ("defs/replay_schema.yaml", _sub("  - id: RS-7-03", "  - id: RS-7-3"), "red"),
        ("defs/replay_schema.yaml", _sub("  - id: RS-7-04\n    source: Sec. 7\n",
                                         "  - id: RS-7-04\n"), "red"),
    ],
    # G17 — OF-014. Each red case is a way a step reads as complete and instructs
    # nobody; the green case is a step that names its mechanism differently from the
    # others and must not be flagged for it.
    "G17": [
        ("defs/procedures.yaml",
         _sub("open: 'http://localhost:2910 - Packet Viewer, EPS_BATT_SOC; and the",
              "open_GONE: 'http://localhost:2910 - Packet Viewer, EPS_BATT_SOC; and the"),
         "red"),                # PROC-001-S09: decide, with nothing put in front of you
        ("defs/procedures.yaml",
         _sub("          record_to: |-", "          record_to_UNSET: |-"),
         "red"),                                    # records listed, nowhere to write
        ("defs/procedures.yaml",
         _sub("          open: 'gnd/RUNBOOK.md'", "          open: 'gnd/NO_SUCH.md'"),
         "red"),                                    # points at a file that is not there
        ("defs/procedures.yaml",
         _sub("            python tools/pass_setup.py --pass-id <pass-id>",
              "            python tools/pass_setup.py --pass-id <mystery-id>"),
         "red"),                                    # a placeholder nobody can resolve
        ("defs/procedures.yaml",
         _sub("  console: |-", "  console_REMOVED: |-"), "red"),     # no console named
        ("defs/procedures.yaml",
         _sub("          open: 'campaign/CAMPAIGN_PLAN.md'",
              "          open: 'campaign/CAMPAIGN_PLAN.md   # the pass plan'"),
         "green"),                        # a comment on the path is not a broken path
    ],
    # G18 — OF-015. G18 reads the GENERATED products, so its mutations perturb the
    # source those products come from and require the leak to appear downstream. The
    # green case is a bare ruling citation, which the rule explicitly permits.
    "G18": [
        ("procedures/PROC-001.md",
         _sub("Navigation is the **menu sidebar on the left**.",
              "Navigation is the sidebar. This was ruled, not provisional."), "red"),
        ("procedures/PROC-001.md",
         _sub("You do not invent it; you read it off the campaign plan.",
              "The Director reads it off the campaign plan."), "red"),
        ("procedures/PROC-002.md",
         _sub("Do not copy files into `verification/evidence/` by hand.",
              "Do not copy files into `verification/evidence/` by hand (see OF-008)."),
         "red"),
        ("campaign/CAMPAIGN_PLAN.md",
         _sub("## Findings",
              "## Findings — affirmed by the owner, ruled not provisional"), "red"),
        ("gnd/RUNBOOK.md",
         _sub("# Ground segment runbook",
              "# Ground segment runbook (every check has a red case in the gate)"),
         "red"),
        # A bare ruling citation is what the rule explicitly permits.
        ("procedures/PROC-001.md",
         _sub("a mismatch is a no-go.", "a mismatch is a no-go (D-010)."), "green"),
    ],
    # G11 — FMEA source invariants.
    "G11": [
        # a rating outside the Sec. 3 definitions
        ("defs/fmea.yaml", _sub("        severity: 'III'\n        likelihood: 'C'",
                                "        severity: 'V'\n        likelihood: 'C'"), "red"),
        # the structured disposition class disagreeing with its own prose cell
        ("defs/fmea.yaml", _sub("        disposition_class: EXERCISED",
                                "        disposition_class: ACCEPTED"), "red"),
        # a Sec. 6 table referencing a row that does not exist
        ("defs/fmea.yaml", _sub("    - row: FM-EPS-02\n      criterion:",
                                "    - row: FM-EPS-99\n      criterion:"), "red"),
        # an R2 row dropped from the exclusion record breaks the partition
        ("defs/fmea.yaml", _sub("    - row: FM-EPS-03\n      criterion: '(a)'\n", ""),
         "red"),
        # a re-rating that moves a row out of R2 also breaks the partition, and it is
        # the direction a careless re-rating actually takes
        ("defs/fmea.yaml", _sub("        severity: 'II'\n        likelihood: 'D'",
                                "        severity: 'IV'\n        likelihood: 'D'"), "red"),
        # D-020: a HUG-G001 row renumbered out of the record. The count of rows is
        # unchanged, so only the named HUG-G001 set can see it.
        ("defs/fmea.yaml", _sub("      - id: FM-EPS-09\n", "      - id: FM-EPS-12\n"), "red"),
        # D-020: a HUG-G001 row listed in Sec. 6.3 in place of the row added after the
        # selection
        ("defs/fmea.yaml", _sub("    - row: FM-GND-07\n      added:",
                                "    - row: FM-GND-04\n      added:"), "red"),
        # D-020: the added row re-rated out of R2 while Sec. 6.3 still lists it
        ("defs/fmea.yaml", _sub("      - id: FM-GND-07\n        severity: 'II'\n        likelihood: 'C'",
                                "      - id: FM-GND-07\n        severity: 'III'\n        likelihood: 'D'"),
         "red"),
        # D-020: the added row's Sec. 6.3 entry listed twice
        ("defs/fmea.yaml", _sub("  post_selection:\n    - row: FM-GND-07\n",
                                "  post_selection:\n    - row: FM-GND-07\n      added: 'x'\n"
                                "      status: 'x'\n    - row: FM-GND-07\n"), "red"),
        # GREEN: rewording a Sec. 6.3 status cell changes no membership
        ("defs/fmea.yaml", _sub("        Added after the campaign was executed; not screened",
                                "        Added once the campaign had been executed; not screened"),
         "green"),
    ],
    # G12 — owner ruling D-001 item 2.
    "G12": [
        # a sentinel written into a generated DOCUMENT, where no caveat can travel
        # with the number
        ("docs/tlm_cmd_dictionary.md",
         _sub("| EPS_BATT_SOC | Battery state of charge | float | % | 20 / 35 / n/a / n/a |",
              "| EPS_BATT_SOC | Battery state of charge | float | % | "
              "20 / 35 / 1e+30 / 1e+30 |"), "red"),
        # the label stripped from the OpenC3 config: the number is now readable as a
        # threshold
        ("gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/cmd_tlm/tlm.txt",
         _sub("    # The unreachable magnitudes below stand for absent; they are not"
              " thresholds.\n", "", 2), "red"),
        # GREEN: 1e+300 is not 1e+30 followed by a zero. A naive substring match
        # would false-flag here.
        ("gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/cmd_tlm/cmd.txt",
         _append("\n# scale note: 1e+300 is not a sentinel value\n"), "green"),
        # GREEN: the labelled sentinel lines as generated must stay green.
        ("gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN/cmd_tlm/tlm.txt", lambda t: t, "green"),
    ],
    # G13 - a dispositioned EPS value changed away from its requirement text.
    "G13": [
        ("defs/eps.yaml", _sub("  battery_capacity_wh: 38", "  battery_capacity_wh: 40"),
         "red"),
        ("defs/eps.yaml", _sub("  charge_efficiency: 0.95", "  charge_efficiency: 0.9"),
         "red"),
        ("defs/eps.yaml", _sub("    LOW_POWER: 30", "    LOW_POWER: 28"), "red"),
        ("defs/eps.yaml", _sub("    NOMINAL: 35", "    NOMINAL: 32"), "red"),
        # A floor pushed below its autonomous entry point: a commanded recovery would
        # immediately re-trip the ladder, which is exactly what the 5-point margin
        # exists to prevent.
        ("defs/eps.yaml", _sub("    LOW_POWER: 25", "    LOW_POWER: 20"), "red"),
        # Strings that no longer sum to the dispositioned array peak.
        ("defs/eps.yaml", _sub("  array_string_peak_w: 8.5", "  array_string_peak_w: 9.0"),
         "red"),
        # GREEN: an authored model parameter is not a dispositioned value and must not
        # be bound to requirement text.
        ("defs/eps.yaml", _sub("  charge_taper_start_soc_pct: 99",
                               "  charge_taper_start_soc_pct: 98"), "green"),
    ],
    # G14 - the exact miss that earned this check: a version advanced in one place in a
    # document and not another. One case per site, so no single site can be the only one
    # the check actually reads.
    "G14": [
        ("docs/conops.md", _sub("## Concept of Operations (CONOPS), v0.10",
                                "## Concept of Operations (CONOPS), v0.9"), "red"),
        ("docs/conops.md", _sub("| Status | v0.10,", "| Status | v0.9,"), "red"),
        ("docs/conops.md", _sub("- **v0.10 (2026-10-12):** Revision per Director ruling",
                                "- **v1.10 (2026-10-12):** Revision per Director ruling"), "red"),
        ("defs/replay_schema.md", _sub("| Status | v0.9,", "| Status | v0.8,"), "red"),
        # A version advanced everywhere except the changelog - the mirror of the miss.
        ("docs/conops.md", _sub("- **v0.10 (2026-10-12):** Revision per Director ruling",
                                "- **v0.7b (2026-10-12):** Revision per Director ruling"), "red"),
        # The concept brief: version in a bold line, changelog in ASCENDING order.
        # Both shapes differ from every other document, so it gets its own case.
        ("docs/concept_brief.md", _alter_version_after("**Concept Brief,"), "red"),
        # GREEN: a version-shaped string in ordinary prose is not a version site.
        ("docs/conops.md",
         _append("\nA note mentioning v0.1 scope in passing.\n"), "green"),
    ],
    # G15 - the currency/provenance split is the whole difficulty, so both sides get
    # red cases AND green cases. A check that only tested currency would be satisfied
    # by one that flagged every historical citation in the record.
    "G15": [
        # RED, currency: the exact failure that earned this check - a companion-baseline
        # citation left behind when the referenced document advanced.
        ("docs/concept_brief.md",
         _alter_version_after("Current companion baseline — CONOPS"), "red"),
        ("docs/concept_brief.md",
         _alter_version_after("Current companion baseline — CONOPS v0.10, "
                              "Requirements v0.13, TLM/CMD Dictionary"), "red"),
        ("docs/concept_brief.md",
         _alter_version_after("Replay Schema"), "red"),
        # RED, provenance: a cited revision that does not exist. History may be old, but
        # it may not be invented or from the future.
        ("docs/fmea.md", _sub("in Requirements v0.3, and the Commands table",
                              "in Requirements v9.9, and the Commands table"), "red"),
        # GREEN: genuine provenance. Requirements v0.3 IS where CMD_MODE_SET landed;
        # forcing it to v0.12 would make the record lie about its own history.
        ("docs/fmea.md", _sub("HUG-OPS-001 amended accordingly in Requirements v0.3.",
                              "HUG-OPS-001 amended accordingly in Requirements v0.3."),
         "green"),
        # RED: a stale currency claim must fail. The register is empty, so this also
        # proves the register is not a way to switch the check off.
        ("docs/fmea.md", _sub("Limits are those ratified at TLM/CMD Dictionary v0.2",
                              "Requirements v0.4 applies. Limits are those ratified at "
                              "TLM/CMD Dictionary v0.2"), "red"),
        # RED: the anchor phrase WITHOUT its currency condition. This case is what keeps
        # the anchor form honest — otherwise "ratified at" alone would be a way to spell
        # any stale citation as provenance and quietly silence the check.
        ("docs/fmea.md",
         _sub("and unchanged through the current dictionary; any limit change reopens "
              "this analysis.", "for this analysis."), "red"),
        # GREEN: GR-02 as ruled at D-006 — anchor phrase AND currency condition, so the
        # sentence says what revision it anchors on and that the anchor still holds.
        ("docs/fmea.md",
         _append("\n<!-- unrelated trailing note -->\n"), "green"),
    ],
    # G16 - one red case per property, because a single case would leave the others
    # asserted only by their own passing result.
    "G16": [
        # The pin loosened to a moving target.
        ("gnd/openc3/.env.template", _sub("OPENC3_TAG=7.2.1", "OPENC3_TAG=latest"),
         "red"),
        # Version drifted away from what defs/ground.yaml pins.
        ("defs/ground.yaml", _sub("  version: '7.2.1'", "  version: '7.2.2'"), "red"),
        # A host port moved onto the operator's training demo.
        ("gnd/openc3/compose.yaml", _sub('- "127.0.0.1:2910:2900"',
                                         '- "127.0.0.1:2900:2900"'), "red"),
        # Project namespace removed - two stacks would then share named volumes.
        ("gnd/openc3/.env.template", _sub("COMPOSE_PROJECT_NAME=huginn",
                                          "COMPOSE_PROJECT_NAME="), "red"),
        # Demo targets switched on: "the loaded configuration" would stop being
        # HUGINN's alone, and HUG-GND-006's pass-setup check would lose its meaning.
        #
        # THE FIRST THREE CASES ALL SPELL "OFF" TO A HUMAN. init.sh tests this
        # variable for presence, so each of them installs the demo. The retired
        # version of this red case flipped 0 -> 1 and was caught, which proved the
        # check could tell 0 from 1 - a distinction the consumer never makes. The
        # baseline it was defending, OPENC3_DEMO=0, was installing the demo the
        # whole time it read green (DECISIONS.md D-009).
        ("gnd/openc3/.env.template", _sub("# OPENC3_DEMO=", "OPENC3_DEMO=0"), "red"),
        ("gnd/openc3/.env.template", _sub("# OPENC3_DEMO=", "OPENC3_DEMO=false"), "red"),
        ("gnd/openc3/.env.template", _sub("# OPENC3_DEMO=", "OPENC3_DEMO=1"), "red"),
        # GREEN: uncommented but empty is the other suppressing form, and must not
        # be flagged - otherwise the check would be reading for a spelling rather
        # than for the condition.
        ("gnd/openc3/.env.template", _sub("# OPENC3_DEMO=", "OPENC3_DEMO="), "green"),
        # The external URL left at upstream's default, which is the training
        # demo's port: HUGINN's own UI would hand out links into the other stack.
        ("gnd/openc3/.env.template", _sub("OPENC3_EXTERNAL_URL=http://localhost:2910",
                                          "OPENC3_EXTERNAL_URL=http://localhost:2900"),
         "red"),
        # ...and at a port nothing publishes, which is broken rather than leaky.
        ("gnd/openc3/.env.template", _sub("OPENC3_EXTERNAL_URL=http://localhost:2910",
                                          "OPENC3_EXTERNAL_URL=http://localhost:2911"),
         "red"),
        # A working credential committed to the template.
        ("gnd/openc3/.env.template",
         _sub("OPENC3_SERVICE_PASSWORD=__GENERATE__",
              "OPENC3_SERVICE_PASSWORD=hunter2"), "red"),
        # A password hash committed in the Redis ACL template. This is the case the
        # check originally missed: hashed or not, it is a credential.
        ("gnd/openc3/openc3-redis/users.acl.template",
         _sub("#__ADMIN_PASSWORD_SHA256__",
              "#749f09bade8aca755660eeb17792da880218d4fbdc4e25fbec279d7fe9f65d70"),
         "red"),
        # An image pinned past the tag variable, so the pin stops governing it.
        ("gnd/openc3/compose.yaml",
         _sub('openc3-traefik${OPENC3_IMAGE_SUFFIX}:${OPENC3_TAG}',
              'openc3-traefik${OPENC3_IMAGE_SUFFIX}:latest'), "red"),
        # GREEN: a comment added to the vendored project changes no pinned property.
        ("gnd/openc3/compose.yaml",
         _append(chr(10) + "# an added comment" + chr(10)), "green"),
    ],
    # G2 is a property of the generators, not of any source text; it is exercised by
    # every run above (each renders twice) and directly by the run-all report. No
    # source mutation can make deterministic code nondeterministic, so it carries no
    # mutation of its own. Its red cases make a generator depend on something besides
    # its source instead, and live in tests/test_g2_determinism.py (D-019).
    "G2": [],
}


def _stage(src_root, dst_root):
    for rel in STAGED:
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_root / rel, dst)


def iter_selftest_cases(root):
    """Per-case self-test results, structured. `self_test` prints from this.

    ONE IMPLEMENTATION, TWO CALLERS — the printed self-test and the verification run
    (B5, HUG-VER-003). A second traversal beside this one would be a private copy of
    the case list, and the two would drift the first time a mutation was added.
    """
    for cid, _name, fn in CHECKS:
        for j, (rel, mut, polarity) in enumerate(MUTATIONS[cid], 1):
            raised = None
            with tempfile.TemporaryDirectory() as td:
                staged = Path(td) / "record"
                _stage(root, staged)
                p = staged / rel
                p.write_bytes(mut(p.read_text(encoding="utf-8")).encode("utf-8"))
                set_repo(staged)
                try:
                    ok, _ev = fn()
                except Exception as exc:                     # a raised error is a catch
                    # OF-008's shape: a red case satisfied by a crash rather than by
                    # the check detecting its violation. Recorded, so the verification
                    # report can count how many red cases rest on an exception.
                    ok, raised = False, f"{type(exc).__name__}: {exc}"
                finally:
                    set_repo(root)
            passed = (not ok) if polarity == "red" else ok
            yield {
                "case_id": f"{cid}.m{j}", "check": cid, "polarity": polarity,
                "target": rel, "passed": passed, "raised": raised,
                "label": ("CAUGHT" if passed else "MISSED") if polarity == "red"
                         else ("HELD-GREEN" if passed else "FALSE-FLAG"),
            }


def self_test(root):
    console()
    print("SELF-TEST (HUG-VER-002, B4): every RED mutation must turn its check red;\n"
          "every GREEN case must leave its check green. A check's passing result counts\n"
          "as evidence only because its red case is demonstrated to fail it.\n")
    failed, total = [], 0
    for case in iter_selftest_cases(root):
        total += 1
        print(f"[{case['label']}] {case['case_id']} ({case['target']}"
              + (", green-expected" if case["polarity"] == "green" else "") + ")")
        if not case["passed"]:
            failed.append(case["case_id"])
    print(f"\nSELF-TEST RESULT: {total - len(failed)}/{total} cases correct"
          + (f"; FAILED: {failed}" if failed
             else " — every check falsifiable on red forms and stable on green forms"))
    if not failed:
        red = sum(1 for v in MUTATIONS.values() for m in v if m[2] == "red")
        print(f"  {red} red cases, {total - red} green cases across "
              f"{len([c for c in CHECKS if MUTATIONS[c[0]]])} mutation-carrying checks")
    return 1 if failed else 0


def iter_check_cases(root):
    """Per-check results, structured. `run_all` prints from this; B5 records it."""
    set_repo(root)
    for cid, name, fn in CHECKS:
        raised = None
        try:
            ok, ev = fn()
        except Exception as exc:
            # A check that raised did not observe its subject. That is a statement
            # about the checker, not about the record, and the verification report
            # records it as INSTRUMENT_FAULT rather than as a failing record.
            ok, ev = False, f"raised {type(exc).__name__}: {exc}"
            raised = f"{type(exc).__name__}: {exc}"
        yield {"case_id": cid, "name": name, "passed": ok, "evidence": ev,
               "raised": raised}


def run_all(root):
    console()
    fails = []
    for case in iter_check_cases(root):
        print(f"[{'PASS' if case['passed'] else 'FAIL'}] {case['case_id']} {case['name']}\n"
              f"       {case['evidence']}")
        if not case["passed"]:
            fails.append(case["case_id"])
    print(f"\nRESULT: {len(CHECKS) - len(fails)}/{len(CHECKS)} checks PASS"
          + (f"; FAILING: {fails}" if fails
             else " — sources and generated views are one record"))
    return 1 if fails else 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    sys.exit(self_test(root) if "--self-test" in sys.argv else run_all(root))
