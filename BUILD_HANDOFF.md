# HUGINN v0.1 — Build-Phase Handoff to Claude Code

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Project | HUGINN: CubeSat Mission Operations Simulator (`HUG-` prefix) |
| Owner / design authority | Dan Lee-Odinson — every disposition, classification, and scope decision is his and only his |
| Builder (you) | Claude Code, executing the build phase against the frozen v0.1 design record |
| Baseline | Repo first commit **c293bb9152987be0d97ee55349fc9963c1465576** — "HUG-G001 series closure baseline" |
| Repo location | the repository root on the operator's machine |
| Gate ahead | **HUG-G002** — the first build gate; it owes every demonstration in §5 and both debt retirements in §6 |

---

## 1. Context in one page

HUGINN is the owner's portfolio flagship: a 6U CubeSat mission operations simulator, v0.1
scoped to an end-to-end EPS (electrical power) operations slice — a modeled spacecraft, a real
OpenC3 COSMOS ground segment, written procedures, and a human-in-the-loop simulated mission
campaign. The spacecraft is never "flown"; it is **operated through a simulated mission
campaign** (see §8 for binding terminology).

The design record you are building to survived **seventeen rounds of documented adversarial
review** (gate series HUG-G001 through HUG-G001-17): 97 findings, every one dispositioned by
the owner, zero appeals. The seventeenth review returned the product record clean; the owner's
§5.4 determination closed the series on 2026-07-29 and the baseline was committed. The review
ledgers live at `..\method\dispositions\HUG-G001*.yaml` (seventeen files, adjacent to this
repo) — they are the authority trail for every decision in the record. Read them when a design
choice seems odd: it almost certainly was argued, ruled, and settled.

**The record is frozen. You build to it; you do not redesign it.** Anything you believe needs
changing — a value, a requirement, a scope line — goes to the owner as a question, and changes
only by his ruling. That discipline is what the seventeen rounds bought; do not spend it.

## 2. What is in the repo

| Path | Content | Version at baseline |
|---|---|---|
| `docs/concept_brief.md` | Scope, objectives O1–O4, inclusions/exclusions (§3), roadmap, review-record status | Concept Brief v0.23 (v0.21 at baseline; advanced by rulings D-005, D-006) |
| `docs/conops.md` | Mission overview, ground segment (§3.2 — the two recording paths), ops phases and scenarios, §4.4 limit-response coverage, pass timeline, ops organization | CONOPS v0.9 (v0.8 at baseline; advanced by ruling D-004) |
| `docs/requirements.md` | The requirement set (HUG-SYS/EPS/CMD/GND/OPS/UI/VER), trace to NEED/CON/ASM | Requirements v0.12 |
| `docs/tlm_cmd_dictionary.md` | 16 telemetry points (1 Hz housekeeping), limits, 5 commands with validation/inhibit rules, HUG-CMD-007 accounting contract, notes 1–3 | Dictionary v0.5 |
| `docs/fmea.md` | 22 failure modes, dispositions (COMMITTED rows are your build obligations), §6 fault-set selection, §8 owner ledger | FMEA v0.15 (v0.14 at baseline; advanced by ruling D-006) |
| `defs/replay_schema.md` | The recorder→VÉ replay package interface (prose spec; becomes `defs/replay_schema.yaml` in Phase 1) | Replay Schema v0.9 |
| `tools/checkers/design_record_consistency.py` | The 16-check consistency checker with 84-case two-polarity self-test | v18 |

Notes: (a) the checker's `DOCS` constant still names the packet-era artifact filenames
(`HUGINN_*.md`) — adapting it to the repo layout is part of Phase 1; (b) git on this working
copy is healthy for native use — the baseline commit is intact and the tree matches it. If
`git status` shows phantom modifications at first touch, verify content against HEAD before
believing it (a remote-mount sync produced stat noise once; content was verified identical).

## 3. Non-negotiable ground rules

1. **Owner authority.** Dispositioned values (limits, thresholds, floors, counts, station
   name, orbit class) change only by the owner's ruling. When in doubt, ask him — one clear
   question with options beats a silent assumption.
2. **Single-source discipline (D0-6 companion).** Once a `defs/` source exists, the generated
   view is never hand-edited. The dictionary and requirements docs carry this rule in their
   own headers: after generation is stood up, editing those markdown files directly is
   prohibited — regenerate them.
3. **No unexecuted direction claims.** Never state which way a checker or mechanism fails or
   doesn't ("over-flags only", "cannot miss X") without an executed case in a suite that
   demonstrates it, with recorded result and polarity. This rule was earned the hard way
   (G001-12 F-02) and is now load-bearing for debt retirement (§6).
4. **Two-polarity testing (HUG-VER-002).** Every checker you write gets negative-tested — a
   red case it must catch and, where the form is tricky, a green case it must not flag —
   before its pass counts as evidence.
5. **Every-statement sweeps.** When you fix or change a cross-cutting statement, sweep ALL
   documents, ALL cells (detection/provision cells included), ALL changelogs, and verify
   section references point where the text actually lives. Four late-series findings came
   from sweeps that stopped one layer short.
6. **Ledgers are read-only history.** Never edit `..\method\dispositions\*` except as the
   owner directs for a new gate.
7. **Terminology bindings (§8)** hold in every file, comment, commit message, and UI string.

## 4. Build order (plan of record)

Work the phases in order; each has an acceptance criterion you can execute. Commit granularly
with messages that cite the requirement or FMEA row a change serves — the HUG-G002 ledger
will want commit hashes per obligation.

### Phase 1 — `defs/` single sources (FIRST, before any simulator code)

Stand up the four structured sources and their generators (Python, stdlib-preferred):

- `defs/tlm_cmd.yaml` → `tools/gen_openc3_config.py` (OpenC3 target config) and
  `tools/gen_dictionary.py` (regenerates `docs/tlm_cmd_dictionary.md`).
- `defs/requirements.yaml` → generator that renders `docs/requirements.md` as a view.
- `defs/replay_schema.yaml` — the machine form of `defs/replay_schema.md` §2–§7 (schema
  identity advances per its own one-identity rule when it changes).
- `defs/fmea.yaml` → `tools/gen_fmea.py` (renders `docs/fmea.md` as a view). **Added by
  owner ruling D-001, 2026-07-29**, per the commitment already standing in FMEA §9:
  *"Before build, this document's worksheet rows move to structured form alongside
  `defs/requirements.yaml` so FM IDs can be referenced by checkers and scenario files."*
  Same round-trip acceptance as the other three. The Risk column is derived from
  severity × likelihood through the §3 criticality matrix rather than stored, so a row's
  rating and its risk class cannot disagree.

**Acceptance:** each generated document is semantically identical to the committed baseline
doc (same values, same rows, same normative statements — layout may be regenerated); the
consistency checker, adapted to the repo layout, runs 16/16 with its 84-case self-test green;
a round-trip check proves the generated docs come from the defs and nothing else. This phase
discharges D0-6 **by construction**. For D0-17 items 1–4 and 6 the phrasing is ruled
(D-002): **superseded for the generated documents; residual scope: the three prose
documents; retirement pronounced at HUG-G002** — §6 as rescoped by D-001 carries the
per-item scope. Record the demonstration, don't just assert it, and pronounce nothing the
gate has not pronounced.

### Phase 2 — EPS spacecraft simulator (`sim/`)

Build to `docs/requirements.md` HUG-SYS/EPS/CMD rows and the dictionary. Headline
dispositioned values (the docs are authoritative where this summary is thin): two solar-array
strings 17 W peak combined; 38 Wh battery behind a 5.0 V regulated bus; 4 W bus load + 3 W
switchable payload; charge taper at full (design protection — dictionary note 2); mode ladder
NOMINAL → LOW_POWER at 30% SoC → SAFE at 20%, **downward transitions only**, recovery only by
ground command with floors 35% (NOMINAL) / 25% (LOW_POWER); the five commands exactly per
dictionary §2 (CMD_PLD_SET_STATE, CMD_PLD_SET_RATE, CMD_SAFE_ENTER, CMD_SYS_RESET,
CMD_MODE_SET) with their validation/inhibit rules and reject reasons {UNKNOWN_OPCODE,
ARG_RANGE, MODE_INHIBIT}; HUG-CMD-007 exactly-once accounting, ≤1-frame visibility, and the
CMD_SYS_RESET counter epoch ACC=1/REJ=0 as the reset acknowledgement; 16-point 1 Hz
housekeeping frame in dictionary order. Orbit: sun-synchronous ~550 km, mid-morning LTAN —
**pin the surrogate reference orbit element set in the repo** (HUG-SYS-002) and replace the
representative contact values with computed ones. Model illumination/eclipse and SAA transit
intervals (O1 counts them). Scenarios: bit-for-bit reproducible; faults injected by scenario
file only (HUG-SYS-003/005).

**Acceptance:** a test suite exercising every command rule at both polarities, the ladder's
downward-only property, the recovery floors, the reset epoch, and frame timing; plus a
reproducibility test (same scenario → identical output).

### Phase 3 — OpenC3 COSMOS ground segment (`ground/`)

Target config **generated** from `defs/tlm_cmd.yaml` (B-obligation B1), never hand-edited.
Configure: limit monitoring per the dictionary; the ground-side derived staleness monitor on
CDH_FRAME_CNT, 10 s yellow / 30 s red (B6, HUG-GND-002); two-step confirmation on the three
hazardous commands (B7); loaded-configuration version/digest displayed at pass setup and
verified against the dictionary of record — mismatch = no-go (B10, HUG-GND-006); and the
ground system's **native timestamped telemetry and command logs recorded in a form OpenC3 can
play back** (B14, HUG-GND-004) — that playback, in the ground system, is the demonstration
evidence that discharges HUG-SYS-006. Keep the two recording paths separate exactly as
FM-GND-06 and CONOPS §3.2 state them: native-log playback is one path; the replay package
(Phase 4) is the other; neither substitutes for the other.

**Acceptance:** a scripted demonstration of each: staleness alarm firing on a halted counter,
two-step flow on a hazardous command, digest mismatch no-go, and a recorded pass played back
in OpenC3 with the simulator off.

### Phase 4 — VÉ recorder and viewer (`ve/`)

Recorder writes the replay package per `defs/replay_schema.yaml`; the VÉ **display-only
mission viewer** renders it with neither simulator nor ground system running (HUG-UI-002).
Honor the full schema contract: canonical lowercase `pass_id` grammar with reserved-basename
exclusion, filename-stem equality, and recorder refusal of identifier reuse; track/frames
split with per-sample illumination; recorder monotonic timebase anchored by `meta.epoch_utc`;
`dict_ref` binding; unconditional dictionary-native value domains; the event-local
result–reason invariant; shortest-arc display; text-only rendering sink (HUG-UI-007).

**Acceptance:** a conformance test suite over the schema (both polarities), plus the
**malicious-markup test** — hostile content in string fields renders inert (B11).

### Phase 5 — Procedures (`procedures/`)

PROC-001 (nominal pass), PROC-002 (limit response), PROC-003 (loss of telemetry/command —
the 10 s no-delta threshold is its decision point). Every step carries a stable step
identifier, names its role and the telemetry it checks; the pass report carries **exactly one
completion entry for every step** of the governing procedure, keyed by step ID, with state
from {completed, not applicable, omitted}, applicability basis on not-applicable entries, and
state-conditional decision evidence — the branch-selecting observation for a completed
decision step, or the record that none occurred for an omitted one. Omissions are
dispositioned as anomalies: re-execution where feasible, or explicit owner risk acceptance
(B13, HUG-OPS-001/002).

**Acceptance:** a pass-report validator that enforces the completion-record contract at both
polarities (missing entry, duplicate entry, invented evidence on an omitted step — all red).

### Phase 6 — Verification apparatus (`tools/`, `verification/`)

The traceability matrix generated per HUG-VER-001 from `defs/requirements.yaml`: full
requirements-source spine, per-requirement upstream NEED path, downstream edge, and a
**negative case per failure edge** (B3 — this is where D0-17 item 4 retires). The
verification report generated by executing checkers (HUG-VER-003/B5). And the **item-5
evidence chain** (§6): an index mapping every direction claim made by any checker or
inventory statement to its executed case ID, recorded result, and polarity.

### Phase 7 — Campaign (`campaign/`)

Scenarios P1–P4: at least one nominal and three anomaly passes, executed human-in-the-loop by
procedure — the owner operates; passes are the evidence. Objectives to demonstrate: O1 ≥20
SAA transits/week payload-active; O3 ≥90% recovery of collected, time-tagged science frames;
O4 every limit violation detected, annunciated, and responded per CONOPS §4.4. Each pass
produces its report (Phase 5 contract) and both recordings (Phase 3/4 paths).

### Phase 8 — HUG-G002 evidence assembly

Collect the demonstrations against §5's table with commit hashes and executed-case IDs. The
gate itself runs through the owner's review process (packet assembly and the adversarial
reviewer are handled in his Cowork workflow, not by you) — your deliverable is a repo where
every §5 row and both §6 retirements point at executable, re-runnable evidence.

## 5. The B-table — build obligations the record has already claimed

These carry **COMMITTED** status in the FMEA and the gate record; HUG-G002 demands their
demonstration. This is your checklist.

| # | Obligation | Source | Built in |
|---|---|---|---|
| B1 | `defs/tlm_cmd.yaml` generates OpenC3 config and dictionary doc | Dictionary header; HUG-GND-001 | Phase 1/3 |
| B2 | `defs/requirements.yaml` single source; requirements doc a generated view | Requirements header | Phase 1 |
| B3 | Traceability matrix per HUG-VER-001 with a negative case per failure edge | HUG-VER-001 | Phase 6 |
| B4 | Every checker negative-tested before its pass counts | HUG-VER-002 | all phases |
| B5 | Verification report generated by executing checkers | HUG-VER-003 | Phase 6 |
| B6 | Ground-side derived staleness monitor (10 s YL / 30 s RL) | Dictionary note 1; HUG-GND-002 | Phase 3 |
| B7 | Hazardous-command two-step confirmation | Dictionary §2; FM-CDH-04 | Phase 3 |
| B8 | Onboard validation, inhibits, HUG-CMD-007 exactly-once accounting with reset epoch | HUG-CMD-001..007 | Phase 2 |
| B9 | Downward-only mode ladder; ground-commanded recovery floors | HUG-EPS-003 / HUG-CMD-006 | Phase 2 |
| B10 | Config version/digest verification at pass setup; mismatch = no-go | HUG-GND-006; FM-GND-04 | Phase 3 |
| B11 | Replay package per schema — full contract incl. pass_id grammar and malicious-markup test; VÉ path only | HUG-UI-002/003/004/005/007 | Phase 4 |
| B12 | Bit-for-bit scenario reproducibility; faults by scenario file only | HUG-SYS-003/005 | Phase 2 |
| B13 | Stable step IDs + every-step completion record with state-conditional decision evidence | HUG-OPS-001/002; CONOPS §4.2 | Phase 5 |
| B14 | Ground-system-native log record and playback — **the path that discharges HUG-SYS-006**; the replay package does not. *HUG-SYS-006 is struck in place by D-019; the August demonstration stays as evidence of the path* | HUG-SYS-006 (struck, D-019); HUG-GND-004; CONOPS §3.2; FM-GND-06 | Phase 3 |

## 6. Ratified debt — what retires, and how (owner rulings; do not blur these)

> **Rescoped by owner ruling D-001, 2026-07-29 (see `DECISIONS.md`).** As first
> written, this section attributed to Phase 1 a retirement its own deliverable list
> could not produce: items 1 and 6, and part of 2 and 3, are bounds on parsing
> documents Phase 1 did not make generated views. The ruling added `defs/fmea.yaml` to
> Phase 1 scope — per the commitment already standing in FMEA §9 — and directed this
> summary be rescoped to match. What follows is the rescoped statement, measured
> against the four sources Phase 1 now delivers. Phase 1's §4 entry is amended to four
> sources accordingly.
>
> **Phrasing ruled by D-002, 2026-07-29.** The build does not pronounce retirement —
> that is a gate act. Wherever the D0-17 items 1–4 and 6 status is stated the required
> form is: **superseded for the generated documents; residual scope: the three prose
> documents; retirement pronounced at HUG-G002.** The per-item entries below state
> supersession scope factually beneath that pronouncement, because the residual is not
> uniform across the items. None of them describes an item as retired.

- **D0-6:** full semantic contradiction detection arrives with `defs/` single-source
  generation; verified at HUG-G002. **Discharged for every value now structured** —
  telemetry, commands, requirements, and the FMEA ratings — because a structured value
  exists once and every view is generated from it. Where a structured value also appears
  inside a normative sentence, a check binds the two. Free prose in the concept brief,
  CONOPS and replay-schema drafting surface remains outside this discharge.
- **D0-17 items 1–4 and 6** (line-scan orphans, table ownership, tab-column fences,
  parent-token validation, link-destination grammar): the ratified path is that
  structured data supersedes the Markdown parsing they bounded, **for each document that
  becomes a generated view and only for those.** Status: **superseded for the generated
  documents; residual scope: the three prose documents; retirement pronounced at
  HUG-G002.** After Phase 1 three documents are generated views (dictionary,
  requirements, FMEA) and three prose documents remain: `docs/concept_brief.md`,
  `docs/conops.md`, `defs/replay_schema.md`. Measured against the consistency checks:
  6 of 16 are now fully backed by structured data, up from 4 before the FMEA source.
  - **Item 1 (line-scan orphans): superseded, no prose residual within this bound.**
    C14 reads only the FMEA, which is now a generated view.
  - **Item 2 (table ownership for definition rows): superseded, no prose residual within
    this bound.** All four definition-row classes — requirement rows (C2), telemetry rows
    (C4/C5), command rows (C6) and FMEA worksheet rows (C14/C15) — come from structured
    sources, so ownership is established by construction rather than inferred from
    Markdown position.
  - **Item 3 (tab-column fences)** and **item 6 (link-destination grammar): superseded
    for the three generated documents**, whose tables are emitted in a known grammar and
    are never parsed from hand-written Markdown. Residual scope for both is the three
    prose documents, which is now the whole of the residual.
  - **Item 4 (parent-token validation): structurally enabled only; not superseded.**
    Trace cells are structured and parsed by one function; per the ratified path this
    item reaches the gate through the generated traceability matrix's negative cases (B3).
- **D0-17 item 5 (suite-traceable residual execution) — AMENDED criterion, and the record's
  most-litigated line:** it retires **only** when every checker and mechanism-inventory
  direction claim maps to an identified executed case and recorded result, **including
  required polarity**, demonstrated at HUG-G002. `defs/` generation alone does NOT retire
  it. Build the claim→case→result index as a first-class artifact (Phase 6), not a footnote.

## 7. Working with the owner

Dan is the design authority and the mission operator. He is not a programmer yet — he is
learning, and he is deeply interested in spaceflight, so **explain what you build as you
build it**: short, concrete explanations of what each component does and why the record
requires it, tied to the mission (what the operator will see and do). Prefer showing him a
running thing over describing an abstraction. Bring him decisions, not puzzles: when a choice
is genuinely his (a value, a scope line, a trade with operational consequences), present the
options and consequences plainly and record his answer. His rulings go in his words.

## 8. Binding terminology (holds everywhere, including code comments and commit messages)

- "**operated through a simulated mission campaign**" — never "flown"
- "**surrogate reference orbit derived from a public element set**" — never "a real TLE"
- VÉ is the "**display-only mission viewer**" — never a "control console"
- Human-in-the-loop passes are the evidence; detectors are advisory-only — command authority
  stays human
- NOAA data is the environmental truth input
- Ground station: **GS-RAVENSROOST** (fictional, central Florida)

## 9. First actions

1. `git log` — confirm HEAD is c293bb91… and the tree is clean; investigate before building
   if not.
2. Commit this handoff as the build phase's opening commit.
3. Set up the Python environment and CI habit: the adapted consistency checker + all new test
   suites runnable by one command; run them before every commit.
4. Start Phase 1. `defs/` first — everything else stands on it.

*Handoff prepared by the drafting assistant (Cowork) at the owner's direction, 2026-07-29,
from the closed HUG-G001 record. The record is the authority; where this handoff and the
record disagree, the record wins — and tell the owner you found a disagreement.*
