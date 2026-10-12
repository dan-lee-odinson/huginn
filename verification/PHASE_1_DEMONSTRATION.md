# HUGINN Phase 1 — demonstration record

| Field | Value |
|---|---|
| Phase | 1 — `defs/` single sources and their generated views |
| Baseline | `c293bb9` — HUG-G001 series closure baseline |
| Gate ahead | HUG-G002 |
| Builder | Claude Code (Opus 5), executing the build phase |
| Owner / design authority | Dan Lee-Odinson |
| Date | 2026-07-29 |

Phase 1's acceptance criterion asks for a demonstration, not an assertion. Every
result below was produced by executing a suite in this repository; every claim names
the case that produced it and that case's polarity. Reproduce all of it with:

```bash
python tools/run_checks.py
```

---

## 1. Acceptance against the handoff's stated criterion

> *"each generated document is semantically identical to the committed baseline doc
> (same values, same rows, same normative statements — layout may be regenerated);
> the consistency checker, adapted to the repo layout, runs 16/16 with its 84-case
> self-test green; a round-trip check proves the generated docs come from the defs
> and nothing else."*

| Criterion | Result | Evidence |
|---|---|---|
| Generated documents semantically identical to baseline | **Exceeded — byte-identical** | §2 |
| Consistency checker adapted, 16/16 | **PASS** | §3 |
| 84-case self-test green | **84/84** | §3 |
| Round-trip proves generation from defs and nothing else | **PASS, destructively** | §2 |
| D0-6 discharged by construction | **Discharged for every structured value** | §5 |
| D0-17 items 1–4 and 6 | **Superseded for the generated documents; residual scope: the three prose documents; retirement pronounced at HUG-G002** | §5 |

**Ruling D-001 (2026-07-29) closed the scope gap this record first raised.** §6 as
originally written reported that the handoff's Phase 1 scope could not deliver the
D0-17 retirement it claimed, because `docs/fmea.md` had no `defs/` source. The owner
ruled that `defs/fmea.yaml` be added to Phase 1 scope — per the commitment already
standing in FMEA §9 — and that the handoff's summary be rescoped to match. Both are
done; §6 now records the outcome rather than the question.

**Ruling D-002 (2026-07-29) fixed the phrasing.** This record had pronounced retirement
on the build's own authority. It is not the builder's to pronounce. The phrasing above
is the ruled form and is used wherever the D0-17 status is stated; §5 carries it and
nothing in this record describes a D0-17 item as retired.

## 2. Round-trip demonstration — executed destructively

The weak form of a round-trip check compares a document to its regeneration. The
strong form deletes the document first, so nothing on disk can contribute to the
result. The strong form was executed for all three generated documents.

| Case | Document | Action | Result |
|---|---|---|---|
| RT-01 | `docs/tlm_cmd_dictionary.md` | deleted, rebuilt from `defs/tlm_cmd.yaml` alone | md5 `5576d08deb477e7a45500c5ff074067b` before and after; empty `git diff` against `c293bb9`; `cmp` identical |
| RT-02 | `docs/requirements.md` | deleted, rebuilt from `defs/requirements.yaml` alone | md5 `4c7c333495bf1322e62bfd31149b8ae9` before and after; empty `git diff` against `c293bb9` |
| RT-03 | `docs/fmea.md` | deleted, rebuilt from `defs/fmea.yaml` alone | md5 `d4faa6ffa770ad9e25b801a05d84989c` before and after; empty `git diff` against `c293bb9`; C14 and C15 pass against the regenerated document |
| RT-04 | all three, plus `ground/targets/HUGINN/` | rendered twice from the same source | 6 rendered outputs identical across runs (check G2) |

All three documents are **byte-identical** to the frozen baseline, not merely semantically
identical. The acceptance criterion permits regenerated layout; none was needed.

A separate guard was executed while authoring the sources: the bootstrap that
produced `defs/tlm_cmd.yaml` aborts unless all 16 telemetry rows and all 5 command
rows render back to their baseline table cells. It ran clean, so no structured value
was transcribed into the source in a form that would not reproduce the record.

## 3. Suite results — executed

| Suite | Scope | Result |
|---|---|---|
| `design_record_consistency.py` | 16 checks over the record's prose | **16/16 PASS** |
| `design_record_consistency.py --self-test` | 84 two-polarity cases | **84/84 correct** |
| `defs_generation.py` | 12 checks binding sources to generated views | **12/12 PASS** |
| `defs_generation.py --self-test` | 36 two-polarity cases (31 red, 5 green) | **36/36 correct** |
| `run_checks.py` | all four suites | **4/4 pass, exit 0, 6.4 s** |

The consistency checker was executed at 16/16 and 84/84 **both before and after**
adaptation — before, against the packet-era filenames with the documents
byte-identical; after, against the repo layout and against the *regenerated*
dictionary, requirements and FMEA documents. The adaptation changed layout and portability
only: no check, no claim, and no self-test case was altered.

### 3.1 The two checkers do not subsume one another — demonstrated

A hand edit was injected into the generated `docs/requirements.md`
(`## HUG-SYS: System` → `## HUG-SYS: System (hand edit)`).

| Case | Checker | Result | Polarity |
|---|---|---|---|
| SUB-01 | `design_record_consistency.py` | 16/16 **PASS** — the edit is perfectly consistent prose | red case, deliberately not caught |
| SUB-02 | `defs_generation.py` G1 | **FAIL**, view named as stale | red, CAUGHT |
| SUB-03 | `run_checks.py` | **exit 1**, failing suite named | red, CAUGHT |

This is why both checkers exist. One verifies the record as it reads; the other
verifies the binding between source and view. Neither is redundant, and the claim is
executed rather than argued.

## 4. Obligations advanced

| # | Obligation | Phase 1 status | Evidence |
|---|---|---|---|
| B1 | `defs/tlm_cmd.yaml` generates OpenC3 config and dictionary doc | **Generated; wiring and demonstration in Phase 3** | RT-01; G1; `ground/targets/HUGINN/` |
| B2 | `defs/requirements.yaml` single source; requirements doc a generated view | **Met** | RT-02; G1 |
| B4 | Every checker negative-tested before its pass counts | **Met for every checker in the repo** | 84/84 and 36/36 |
| B6 | Ground-side staleness monitor 10 s YL / 30 s RL | **Thresholds structured in defs; emission in Phase 3** | `limits.kind: staleness` |
| B7 | Hazardous-command two-step confirmation | **Three commands emit `HAZARDOUS`, derived not counted** | `cmd_tlm/cmd.txt` |
| B10 | Config version/digest verification at pass setup | **Digest generated from source bytes; display in Phase 3** | G9 |
| B11 | Replay package per schema, full contract | **Contract in machine form, 32 identified rules; validator in Phase 4** | G10 |

## 5. Ratified debt — what Phase 1 supersedes

> **Pronouncement of record, per owner ruling D-002:**
> **superseded for the generated documents; residual scope: the three prose documents;
> retirement pronounced at HUG-G002**

Retirement is a gate act, not a build act. This section establishes supersession and
its scope; it pronounces nothing. Nothing below describes a D0-17 item as retired.

Scope note: ruling D-001 added `defs/fmea.yaml` to Phase 1, so four sources exist and
three of the six record documents are generated views. Three prose documents remain:
`docs/concept_brief.md`, `docs/conops.md`, `defs/replay_schema.md`.

### D0-6 — semantic contradiction detection

The debt: *full semantic contradiction detection over free prose is beyond the
consistency checks; it arrives with `defs/` single-source generation.*

Discharged **by construction for every value that is now structured**. A limit, a
count, a threshold, a requirement attribute or an FMEA rating exists once, in one
source, and every view is generated from it — two views cannot state different values
because there is only one value.

Three mechanisms carry the discharge, each executed:

| Mechanism | What it makes impossible | Evidence |
|---|---|---|
| Single source per value | Two views stating different values | G1, G2 |
| Derivation instead of storage | A row's rating disagreeing with its risk class — the FMEA Risk column is computed from severity × likelihood through the §3 matrix at every one of its 38 rendering sites, not stored | Bootstrap abort-gate reproduced all 22 worksheet Risk cells and all 16 §6 risk spellings; G11 |
| Structured value bound to the prose that states it | A number drifting between a normative sentence and its source | G6 (5/5 command thresholds), G11 (disposition class leads its own cell) |

The middle row is the strongest form. The contradiction the old string-comparison
check hunted for — a Risk cell disagreeing with its own rating — is now
*unrepresentable* rather than merely detected.

**Scope of the discharge:** telemetry and command definitions, the requirement set,
and the FMEA. Free prose in the concept brief, CONOPS and replay-schema drafting
surface remains outside it, and that residual is now the whole of it.

### D0-17 items 1–4 and 6

The ratified retirement path is that structured data supersedes the Markdown parsing
these items bounded. That happens for a document exactly when the document becomes a
generated view.

Executed measurement — which checks still read hand-maintained prose:

| | Checks | Before the FMEA source | After |
|---|---|---|---|
| Fully backed by structured data | C2, C5, C6, C10, **C14, C15** | 4 of 16 | **6 of 16** |
| Still reading prose | C1, C3, C4, C7, C8, C9, C11, C12, C13, C16 | 12 of 16 | 10 of 16 |

Per-item supersession scope. The pronouncement above is the standing form; the residual
is not uniform across the items, so each is stated factually beneath it. No row below
pronounces retirement.

| Item | Bound | Supersession scope |
|---|---|---|
| 1 | C14's line-based orphan scan | **Superseded; no prose residual within this bound.** C14 reads only `docs/fmea.md`, which is now a generated view — the line-scan bound has nothing hand-maintained left to scan. Retirement pronounced at HUG-G002. |
| 2 | Table ownership for definition rows | **Superseded; no prose residual within this bound.** All four definition-row classes now come from structured sources — requirement rows (C2), telemetry rows (C4/C5), command rows (C6), FMEA worksheet rows (C14/C15) — so ownership is established by construction rather than inferred from Markdown position. Retirement pronounced at HUG-G002. |
| 3 | Tab-column fence indentation | **Superseded for the three generated documents; residual scope: the three prose documents.** Generated tables are emitted by `hugdefs.md_table` in a known grammar and are never parsed from hand-written Markdown. Retirement pronounced at HUG-G002. |
| 4 | Parent-token validation in trace cells | **Structurally enabled only; not superseded.** Trace cells are structured and parsed by one function (`hugdefs.trace_tokens`, executed over all 38 rows: every row yields at least one citation). Per the ratified path this item reaches the gate through the generated traceability matrix's negative cases — B3, Phase 6. |
| 6 | Link-destination grammar, false-positive polarity | **Superseded for the three generated documents; residual scope: the three prose documents.** Retirement pronounced at HUG-G002. |

### D0-17 item 5 — untouched, by ruling

Neither superseded nor claimed. Its amended criterion requires every checker and
mechanism-inventory direction claim to map to an identified executed case, recorded
result and required polarity, demonstrated at HUG-G002. `defs/` generation alone does
not retire it. Phase 1 lays the anchors it will need: the 32 `RS-<section>-<nn>`
conformance-rule identifiers, and the case identifiers of both self-test suites
(84 + 36 cases, each reporting its polarity).

## 6. Owner ruling D-001 — implemented

The ruling is recorded verbatim in `DECISIONS.md`. Implementation:

| Item | Directed | Status |
|---|---|---|
| 1 | `defs/fmea.yaml` with generated `docs/fmea.md`, same round-trip acceptance | **Done.** RT-03: deleted and rebuilt byte-identically. The hardest document in the record — 22 worksheet rows across three tables, six further tables, a derived Risk column, and a changelog whose order is not descending (v0.11 sits second, preserved). |
| 1 | Rescope the handoff's D0-17 retirement summary | **Done.** `BUILD_HANDOFF.md` §4 Phase 1 (three sources → four) and §6, both marked as rescoped by D-001, carrying the per-item status above. |
| 2 | Sentinels confirmed, labelled as absent | **Done.** Retained with their in-file labelling; two points affected, `EPS_BATT_SOC` and `EPS_LOAD_I`. |
| 2 | Red-cased guard: no sentinel ever appears as a real threshold in any generated document or display | **Done.** Check **G12**, three red cases and three green. |
| 3 | Record the ruling verbatim in a new `DECISIONS.md` | **Done.** Entry D-001. |
| 3 | Proceed to Phase 2 once the FMEA source is green | **FMEA source green.** See §3. |

### G12 — the sentinel guard, executed at both polarities

The guard admits a sentinel in exactly one place: an OpenC3 `LIMITS` line whose
immediately preceding lines say it stands for absent. In a generated *document* it is
never admissible — a document has no place to put the caveat where an operator would
read it alongside the number.

| Case | Form | Polarity | Result |
|---|---|---|---|
| G12.m1 | A sentinel written into a generated document (the `EPS_BATT_SOC` limits cell) | red | CAUGHT |
| G12.m2 | The absent-label stripped from the OpenC3 config, leaving the number readable as a threshold | red | CAUGHT |
| G12.m3 | `1e+300` in a generated file — *not* a sentinel; a naive substring match would false-flag it | green | HELD-GREEN |
| G12.m4 | The labelled sentinel lines exactly as generated | green | HELD-GREEN |
| G12.c1 | A generated view registered but unreachable by the scan, as a Phase 4 ODIN (now VÉ) display would be before it exists | red | CAUGHT — reported as `GENERATED VIEW NOT COVERED BY THIS SCAN` |

G12.c1 is the ruling's "or display" clause made enforceable ahead of the displays
existing. Coverage is derived from `hugdefs.GENERATED`, so a Phase 3 ground screen or
a Phase 4 ODIN view is covered by registering it — and *failing* to register it is
itself a check failure, not a silent gap. The sentinel pattern is built from the
generator's own constants, so changing a sentinel value cannot leave the guard hunting
for the old one.

## 7. Questions to the owner

### Answered

1. **Absent limit sides in the OpenC3 configuration.** OpenC3's `LIMITS` keyword takes
   four values and has no spelling for "no limit on this side". Two points are one-sided
   in the record: `EPS_BATT_SOC` has no high limits (note 2 — overcharge protection is
   the `EPS_BATT_V` voltage-high alarm) and `EPS_LOAD_I` has no low limits.
   **RULED — D-001 item 2, 2026-07-29:** sentinels confirmed as the spelling of record,
   labelled as absent, with a red-cased guard that no sentinel ever appears as a real
   threshold in any generated document or display. Implemented as check G12; see §6.

### Still open

Neither blocks Phase 2. Both have operational consequences and are the owner's.

2. **Two byte-layout choices, delegated to `defs/` by Dictionary §3.** §3 says the
   exact byte layout lives in `defs/tlm_cmd.yaml` and the document never specifies
   bytes by hand, so these were authored rather than asked — but both are visible to
   an operator and are recorded here rather than buried:
   - the header's MET timestamp **is** `CDH_MET`, one field read once and exposed
     under its dictionary mnemonic, rather than a second mission time in the same
     frame that could disagree with the first;
   - enum wire codes are the zero-based index in `enum_values`, so the member list
     stays the single source for both the spelling and the code.

3. **Header wording, editorial.** Both generated documents' status paragraphs still
   describe the move to `defs/` in the future tense ("before build, definitions move
   to `defs/tlm_cmd.yaml`"). That move has now happened. The wording is part of the
   frozen record and was left byte-identical rather than edited. Changing it is a
   record change and therefore the owner's ruling, not a build action.

## Appendix — captured suite output

The verbatim output of `python tools/run_checks.py` and both defs-generation runs at
this commit is in `_capture.txt` alongside this record.
