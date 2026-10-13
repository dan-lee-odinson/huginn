# HUGINN — owner decisions of record

Rulings by the design authority, Dan Lee-Odinson, recorded verbatim in his words.

This file is the build phase's authority trail for decisions taken *after* the
HUG-G001 series closed. It does not replace the review ledgers at
`..\method\dispositions\HUG-G001*.yaml`, which remain the authority for every
decision inside that series and are read-only history.

Each entry records the ruling verbatim, what prompted it, and what changed in the
repository because of it. Where a ruling directs a change to the frozen record or to
`BUILD_HANDOFF.md`, this file is the authorization for that change.

---

## D-001 — FMEA source, sentinel guard, and Phase 2 gate

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | `verification/PHASE_1_DEMONSTRATION.md` §6 and §7 — a scope gap between the handoff's D0-17 retirement summary and its own Phase 1 deliverable list, plus two open questions with operational consequence |
| Status | Ruled; implementation in progress |

### Ruling (verbatim)

> Ruling: (1) Add defs/fmea.yaml with generated docs/fmea.md to Phase 1 scope, per the
> FMEA §9 commitment; same round-trip acceptance as the other three sources; rescope
> the handoff's D0-17 retirement summary to match. (2) Absent limit sides confirmed as
> sentinels labeled as absent, with a red-cased guard that no sentinel ever appears as
> a real threshold in any generated document or display. (3) Record this ruling
> verbatim in a new DECISIONS.md, then proceed to Phase 2 once the FMEA source is
> green.

### What prompted it

**(1)** Phase 1 delivered the three sources the handoff specified, and both generated
documents came out byte-identical to the frozen baseline. But the handoff also states
that Phase 1 "retires D0-17 items 1–4 and 6", and those two statements did not meet:
items 1 and 6, and part of 2 and 3, are bounds on parsing `docs/fmea.md`, which had no
`defs/` source and so remained hand-maintained Markdown. Measured at the time: 4 of
the 16 consistency checks were backed by structured data; 12 still read prose, C14 and
C15 among them.

The ruling cites FMEA §9, which had already committed to this:

> *"Before build, this document's worksheet rows move to structured form alongside
> `defs/requirements.yaml` so FM IDs can be referenced by checkers and scenario files;
> this markdown is the drafting surface."*

The record therefore asked for the FMEA source before the handoff summarized the debt;
the ruling aligns the handoff to the record rather than the other way round.

**(2)** OpenC3's `LIMITS` keyword takes four values and has no spelling for "no limit
on this side". Two points are one-sided in the record — `EPS_BATT_SOC` has no high
limits (Dictionary note 2: overcharge protection is the `EPS_BATT_V` voltage-high
alarm, not a SoC limit) and `EPS_LOAD_I` has no low limits. The generator emitted
magnitudes no physical value can reach, labelled in the file as standing for absent.
The question put was whether that spelling is acceptable, given an operator could read
a limit bar that does not exist in the record.

### Consequences in the repository

| # | Change | Where |
|---|---|---|
| 1 | `defs/fmea.yaml` added as the fourth single source; `docs/fmea.md` becomes a generated view under the same byte-identical round-trip acceptance as the other three | `defs/`, `tools/gen_fmea.py` |
| 1 | `BUILD_HANDOFF.md` §6 D0-17 retirement summary rescoped to match actual coverage | `BUILD_HANDOFF.md` |
| 1 | `verification/PHASE_1_DEMONSTRATION.md` §5–§6 restated against the new scope | `verification/` |
| 2 | Absent-limit sentinels confirmed as the spelling of record, retained with their in-file labelling | `tools/gen_openc3_config.py` |
| 2 | New guard, red-cased: no sentinel value may appear as a real threshold in any generated document or display | `tools/checkers/defs_generation.py` |
| 3 | This file | `DECISIONS.md` |
| 3 | Phase 2 (EPS spacecraft simulator) begins once the FMEA source is green | — |

### Note on scope of the sentinel guard (D-001 item 2)

The ruling says "any generated document or display". Phase 1 can enforce it over
everything that exists to generate: the three generated documents and the OpenC3 target
configuration. ODIN (now VÉ; Phase 4) and the ground displays (Phase 3) do not exist yet. The
guard is written so that a new generated output is covered by adding it to one list,
and its absence from that list is itself a failure rather than a silent gap — so the
obligation cannot be quietly dropped when those phases arrive.

---

## D-008 — gate evidence as preserved artifact, not a retention window

| Field | Value |
|---|---|
| Date | 2026-07-30 |
| Ruled by | Dan Lee-Odinson, design authority |
| Self-label | *(instruction ahead of the Phase 3 demonstrations)* |
| Prompted by | The Phase 3 plugin setting `LOG_RETAIN_TIME` to thirty days and treating that as protecting the B14 pass recording |
| Status | Ruled; implemented |

### Ruling (verbatim)

> When the demonstrations run, archive the B14 pass recording (and each demo's
> artifacts) into the evidence folder at execution time — gate evidence as preserved
> artifact, not a retention window.

### What was wrong with the design this corrects

The plugin set the ground system's log retention to thirty days, and the commit message
argued that this protected the B14 evidence — *"a log rotated away before the gate is
evidence lost"*. The reasoning was right about the risk and wrong about the remedy. A
retention window fails four ways, and the ruling closes all four:

| Failure | Retention window | Archived at execution |
|---|---|---|
| One keystroke destroys it | `docker compose down -v` drops the named volume, no warning, no trace | The artifact is in the repository |
| It expires | Evidence valid for thirty days; HUG-G002 has no deadline | Permanent |
| Nothing binds it to the run | The artifact sits outside version control | Digested and committed alongside the code that produced it |
| The failure is silent | An empty volume months later cannot be told apart from a demonstration that never ran | An absent evidence directory is unmistakable |

The fourth is the worst. Every other discipline in this build exists to make a missing
thing visible — the two-polarity suites, the empty-register assertion, the
no-unexecuted-direction-claims rule — and log retention would have reintroduced exactly
the silent absence they were built to prevent, at the one place where the evidence
actually is the artifact rather than a description of it.

### What was built

`tools/evidence.py` — a context manager each demonstration runs inside. It creates the
evidence directory, copies artifacts in **as the demonstration runs**, digests every
one, and writes a manifest recording what was captured, when, and the executed result.

```python
with Evidence("B14-native-log-playback", obligation="B14",
              requirement="HUG-SYS-006") as ev:
    ...run the demonstration...
    ev.capture_file(exported_log, "ground-native-telemetry.log")
    ev.record("PASS", "played back in the ground system with the simulator stopped")
```

Four properties, each red-cased in `tests/test_evidence.py` (11 cases, all executed):

- **Artifacts are copied, not referenced.** A path into a container volume is not
  evidence; it is a pointer to something that will not be there later. The test deletes
  the source afterwards and asserts the artifact survives.
- **Everything is digested.** The sha256 is what binds what the gate reads to what the
  demonstration produced. Without it the manifest is a list of filenames.
- **A demonstration that captures nothing raises.** An evidence directory with nothing
  in it is a claim that something was shown with nothing to show — worse than no
  directory, because it reads as evidence to anyone skimming.
- **A crashed demonstration still writes its manifest, marked FAIL**, with whatever it
  had captured. A crashed demonstration is a result; burying it would make it
  indistinguishable from one never run.

`verification/evidence/README.md` states the principle and what each of B6, B7, B10 and
B14 owes. A test asserts the folder is **not** gitignored — it is the one artifact class
in this repository that must be committed.

### Retention, restated

`LOG_RETAIN_TIME` stays in the plugin, but its description and its comment now say what
it is: a margin covering the seconds between a pass ending and its capture. A test
asserts the plugin does not present retention as the evidence mechanism, so the
repository cannot drift back into contradicting this ruling.

### Consequences in the repository

| Change | Where |
|---|---|
| Evidence harness with the empty-directory rule | `tools/evidence.py` |
| 11 red-cased tests over its properties | `tests/test_evidence.py` |
| Evidence folder, the principle, and what each obligation owes | `verification/evidence/README.md` |
| `LOG_RETAIN_TIME` restated as a margin, in both its description and its comment | `tools/gen_openc3_config.py` → regenerated `plugin.txt` |
| Runbook's `down -v` warning corrected — it was written against the superseded design | `gnd/RUNBOOK.md` |
| This entry | `DECISIONS.md` |

---

## D-007 — ground segment deployment: own COSMOS project, pinned

| Field | Value |
|---|---|
| Date | 2026-07-30 |
| Decided by | Claude Code, under owner instruction to "decide explicitly … and record the deployment choice and reasoning in DECISIONS.md" |
| Self-label | *(environment update preceding Phase 3 wiring)* |
| Status | **RATIFIED by the design authority, 2026-07-30.** Decided by the builder under delegation, then ratified; it now binds as an owner decision. |

### The owner's instruction (verbatim)

> Environment update before you wire Phase 3: Docker Desktop (WSL2) is installed and
> working, and the stock COSMOS demo is cloned and running at localhost:2900 — I'm using
> it separately for operator training. Two machine quirks already found: Docker does not
> autostart on this machine (first suspect on any compose failure), and a
> settings-store.json rename issue. For HUGINN: pin the OpenC3 version in the repo
> rather than tracking latest, decide explicitly whether HUGINN deploys as its own
> COSMOS project or as a target added to the existing clone — avoiding a port collision
> with the demo either way — and record the deployment choice and reasoning in
> DECISIONS.md.

**Note on authority.** This entry records a decision the owner delegated to the
builder, made under his instruction to "decide explicitly", and **subsequently ratified
by him on 2026-07-30**. It binds as an owner decision. The delegation and the
ratification are both recorded because the distinction matters to a reviewer reading the
register: this is the one entry that was not a ruling when it was written.

### Environment, as found rather than as assumed

Read from the running system before deciding anything:

| | Value |
|---|---|
| OpenC3 COSMOS version running | **7.2.1** |
| Training clone | `<cosmos-project>`, compose project `cosmos-project` |
| Host ports it binds | `127.0.0.1:2900` and `127.0.0.1:2943` (localhost-only) |
| Internal-only ports | 2901, 2902, 6379–6380, 8812, 9000, 9009 — not host-bound, so not a collision surface |
| Upstream tag posture | `.env` already carries `OPENC3_TAG=7.2.1`, not `latest` |

The training clone's `openc3-cosmos-init` container sits at `exited(1)`. That is normal
for an init container that has completed, but it is also where the operator's
`settings-store.json` issue would surface, so it is noted rather than passed over.

### The decision: HUGINN deploys as its own COSMOS project

Not as a target added to the training clone. Six reasons, in the order they bind:

1. **B14's evidence would live in someone else's volume.** HUG-SYS-006 is discharged by
   the ground system's *native* timestamped logs being recorded and played back. Those
   logs are the campaign's evidence. In a shared instance they would sit in volumes the
   operator is also using for training and may reset between sessions — the campaign's
   evidence destroyed by an unrelated `docker compose down -v`.

2. **B10's configuration identity would stop being HUGINN's.** HUG-GND-006 has the
   ground system display the loaded configuration's version and digest at pass setup,
   verified against the dictionary of record, mismatch = no-go. A shared instance loads
   the demo targets too, so "the loaded configuration" would be HUGINN's plus whatever
   else is installed. `OPENC3_DEMO=0` on a dedicated instance makes the check mean what
   the requirement says it means.

3. **The gate needs the ground segment to be reproducible from the repository.** A
   HUG-G002 reviewer must be able to stand it up. `<cosmos-project>` is outside this
   repository, is not version-controlled by it, and is the operator's working training
   environment. A ground segment that only exists on one machine is not evidence.

4. **ASM-03 requires stable contact geometry across all four campaign passes.** A shared
   instance being reconfigured or reset mid-campaign for a training session breaks that,
   and would do so silently.

5. **The record already says so.** The concept brief's repository tree puts `gnd/openc3/`
   *inside* the repository — a project directory, not a pointer to an external clone.

6. **Blast radius, both ways.** Training cannot break the campaign, and campaign work
   cannot disturb a training session in progress.

**The cost, stated plainly:** a second COSMOS stack is eight more containers. On this
machine they need not run simultaneously — the training demo and the campaign are
different activities on different days — and neither is harmed by the other being
stopped. If memory pressure ever makes that awkward, stopping one is a `docker compose
down` in its own directory, with no configuration change and no risk to the other.

### Version pinned, not tracked

`defs/ground.yaml` is the single source: **OpenC3 COSMOS 7.2.1**. All nine image
references in the vendored `compose.yaml` resolve through `${OPENC3_TAG}`, and none
names a literal tag or `latest`.

The pin is not housekeeping. HUG-SYS-003 requires campaign results reproducible across
runs; a ground system that changed version between passes would break that without
leaving a diff. And HUG-GND-006's digest check is only meaningful if the system
performing it is itself fixed.

### Ports

| | Host | Container |
|---|---|---|
| HUGINN web | **2910** | 2900 |
| HUGINN secondary | **2953** | 2943 |
| Training demo | 2900 / 2943 | 2900 / 2943 |

Only the host side moves. Traefik listens on 2900/2943 inside its own namespace
(`openc3-traefik/traefik.yaml`: `address: ":2900"`), and upstream's
`NetworkConfiguration.md` is explicit — *"modify the first port number if desired (Note:
leave the last :2900)"*. Changing the container side would break traefik's routing rather
than relocate the service.

Check **G16** asserts *disjointness* from the demo's ports rather than HUGINN's specific
numbers, so either side can move later as long as they stay apart.

### Credentials are generated, never committed

The upstream template ships working default credentials in `.env`. This repository ships
none. `gnd/openc3/.env.template` carries `__GENERATE__` markers;
`tools/setup_ground.py` writes the real `.env` with fresh random values; `.gitignore`
excludes it; G16 fails if any credential value is ever committed or if the ignore rule
is removed.

Two reasons. Copying the training clone's values would couple two instances that have no
reason to share secrets. And a working credential committed to a repository that may
become public outlives whatever posture made it look safe — this repository's siblings
have been published.

Credentials are the one thing here deliberately **not** reproducible. HUG-SYS-003's
bit-for-bit requirement is about simulation results from a scenario file; a Redis
password is not an input to any of them, and seeding it would make it predictable for no
benefit.

### Machine quirks, recorded where they will be found

Both are in `gnd/RUNBOOK.md`, because both present as something other than what they are:

- **Docker does not autostart.** First suspect on any compose failure. After a reboot,
  `docker compose` fails in whatever way a missing daemon happens to surface — usually a
  connection error that reads like a configuration fault. `docker info` first, always.
- **`settings-store.json` rename issue.** Presents as Docker Desktop failing to start or
  to apply settings, not as a COSMOS problem, so it is easy to chase into the wrong
  stack.

### Consequences in the repository

| Change | Where |
|---|---|
| Vendored OpenC3 project at the pinned tag: compose, traefik and redis config, CA bundle | `gnd/openc3/` |
| Host ports 2910/2953; compose project `huginn`; `OPENC3_DEMO=0` | `gnd/openc3/compose.yaml`, `.env.template` |
| Deployment pin as a single source | `defs/ground.yaml` |
| Credential generator; real `.env` gitignored | `tools/setup_ground.py`, `.gitignore` |
| Check G16, seven red cases and one green | `tools/checkers/defs_generation.py` |
| Runbook, including both machine quirks | `gnd/RUNBOOK.md` |
| This entry | `DECISIONS.md` |

The demo's 12 MB of plugin gems were **not** vendored. HUGINN's target is generated from
`defs/tlm_cmd.yaml` (B1), so the demo's plugins are not a dependency.

---

## Numbering map — how a ruling's self-label reconciles with its register key

Ruled at D-006. Rulings arrive labelled by their **subject** — the prior ruling whose
open item they close, or the record element they act on — while this register keys them
**sequentially** by the order they were given. The two are not the same string, and
without this map a reader finding "D-004:" at the head of a ruling would look for it
under D-004 and find a different ruling.

| Register key | Ruling's own self-label | Subject the self-label names | Date |
|---|---|---|---|
| **D-001** | *(none — "Ruling: (1) … (2) … (3) …")* | FMEA source, sentinel guard, Phase 2 gate | 2026-07-29 |
| **D-002** | *(none — "For the retirement pronouncement: …")* | D0-17 supersession phrasing | 2026-07-29 |
| **D-003** | *(none — given as selections from enumerated options)* | Orbit element-set class, propagator, FM-EPS-08 | 2026-07-29 |
| **D-004** | `D-003:` | Closes D-003's two outstanding items | 2026-07-29 |
| **D-005** | `D-004:` | Closes D-004's flagged item | 2026-07-29 |
| **D-006** | `GR-02:` | Acts on FMEA ground rule GR-02 | 2026-07-29 |
| **D-007** | *(none — environment update preceding Phase 3)* | Ground segment deployment; decided by the builder under delegation, **ratified by the owner 2026-07-30** | 2026-07-30 |
| **D-008** | *(none — instruction ahead of the Phase 3 demonstrations)* | Gate evidence archived at execution time rather than held by a retention window | 2026-07-30 |
| **D-009** | *(none — "Blocker ruled, option (b): …")* | The mechanism that actually suppresses the demo plugin | 2026-08-04 |
| **D-010** | `D-010:` | OF-001 ruled option 3; B10's enforcement point named | 2026-08-06 |
| **D-011** | *(none — instruction ahead of resuming Phase 3)* | INSTRUMENT_FAULT, a third evidence outcome | 2026-08-06 |
| **D-012** | `D-012:` | OF-006 read-fault vocabulary; OF-007 accepted as implemented | 2026-08-06 |
| **D-013** | *(none — the Phase 6 instruction, recorded afterwards under Phase 6R)* | The verification apparatus: B3, B5, and the item-5 evidence chain | 2026-08-08 |
| **D-014** | *(none — given as two labelled definitions)* | What makes a contact usable, per tier; its two undefined terms operationalised by the builder and **affirmed by the owner 2026-08-08** | 2026-08-08 |
| **D-015** | *(none — three dispositions, each labelled by the finding it closes)* | A pass may span two contacts; the simulator gains a start offset | 2026-09-13 |
| **D-016** | *(none — two selections from options put to the Director, and one ruling in the Director's own words)* | Contact designation, two-contact filing, and cross-contact inference | 2026-09-20 (recorded 2026-10-11) |
| **D-017** | *(none — three selections from options put to the Director)* | PASS-3: the predicted profile first, a load alarm routed to S03, and the change red-lined | 2026-10-11 |
| **D-018** | *(none — three selections from options put to the Director)* | PASS-4: the staleness annunciator located and red-lined, PROC-003 entered on the alarm, the scripted reset kept | 2026-10-11 |
| **D-019** | *(none — "Rulings: First, … 2. … 3. …", then selections from options put to the Director, and on the draft a further ruling and a constraint in his own words)* | HUG-G002 scope: the v0.1 release criteria revised, HUG-SYS-006 struck in place, the gaps and register ruled, the target set | 2026-10-12 |
| **D-020** | *(none — four selections from options put to the Director)* | FM-GND-07: D-012's FMEA row rated and dispositioned, and §6 kept as the HUG-G001 selection | 2026-10-13 |
| **D-021** | *(none — three selections from options put to the Director, and one answer in his own words)* | HUG-G002 build 5: plain console text, the command read-back, the stuck-load wording, and the PASS-4 re-fly scenario | 2026-10-13 |
| **D-022** | *(none — one selection from options put to the Director)* | The ground system moves to the public copy, with its stored data | 2026-10-13 |

Two of these self-labels — `D-010:` and `D-012:` — happen to equal their own register key
rather than naming a prior entry. That is a coincidence of those two rulings arriving after
the register had caught up with them, not a change of convention: the rule below still
holds, and the next self-label that names a prior entry will differ from its key again.

**Rows D-009 through D-013 were added on 2026-08-08.** The map had stopped at D-008 while
the register ran to D-012, which the Phase 6 verification report detected and reported by
parsing both. The rulings themselves were never altered; only this reconciliation table
was behind, which is the failure mode the table exists to prevent and the reason it is now
generated against on every run.

One entry began as a builder decision taken under explicit delegation (D-007)
rather than as an owner ruling, and was ratified by the owner afterwards. It is kept
here because it binds the build the same way and needs the same visibility; its entry
records both the delegation and the ratification, because a reviewer reading the
register should be able to see which entries were rulings when written and which
became rulings later.

**The rule, stated so it holds for the next one:** the register key is assigned in
sequence at the time of recording and never changes. A ruling's self-label is recorded
verbatim in its entry and is treated as a *reference to its subject*, not as its
identifier. Where a self-label names a prior register key, that prior entry carries a
"Closed by" pointer back, so the chain is traversable from either end.

Cross-references elsewhere in the repository — commit messages, `BUILD_HANDOFF.md`,
`defs/`, checker docstrings — always use the **register key**, never the self-label.

---

## D-006 — GR-02 amended; FMEA to v0.15; numbering map stated

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Ruled by | Dan Lee-Odinson, design authority |
| Self-label | `GR-02:` — naming the FMEA ground rule acted on |
| Prompted by | D-005's flagged finding: check G15 flagged FMEA GR-02's bare "TLM/CMD Dictionary v0.2" as ambiguous between provenance and a stale currency claim |
| Status | Ruled; implemented |
| Closes | D-005 "One finding the check turned up, needing a ruling" |

### Ruling (verbatim)

> GR-02: amend to state the ratification anchor and its currency condition — limits are
> those ratified at Dictionary v0.2, unchanged through the current dictionary; any limit
> change reopens this analysis. FMEA advances to v0.15, changelog citing this ruling,
> checker baseline synced, the G15 register entry retired. Also state the DECISIONS.md
> numbering map so each ruling's self-label reconciles with its register key. Then
> proceed to Phase 3.

### What the amendment does

GR-02 read *"Limits are those of the TLM/CMD Dictionary v0.2."* — a bare version
citation that could be read either as provenance or as a stale claim of currency, with
no way for a reader or a checker to tell which. It now reads:

> *"Limits are those ratified at TLM/CMD Dictionary v0.2 and unchanged through the
> current dictionary; any limit change reopens this analysis."*

The substance does not change — the dictionary records all limit values unchanged
through v0.5, so GR-02 always analysed against the limits that are still current. What
changes is that **the sentence now says so**. The ambiguity is resolved in the record
rather than in the checker, which is the right place for it: a checker exemption would
have left the sentence just as ambiguous to a human reader.

The third clause is the load-bearing one. *"Any limit change reopens this analysis"*
converts a silent dependency into a stated one: the FMEA's ratings rest on those limit
values, and a future limit change now carries an explicit obligation to revisit the
analysis rather than leaving it to be noticed.

### The check follows the record

G15 gains a **ratification anchor** rule, and the anchor form requires **both** halves:

- an anchor phrase — "ratified at"
- a currency condition — "unchanged through the current"

An anchor phrase *without* a currency condition is read as a currency claim and must
match exactly. That is what keeps the form honest: otherwise "ratified at" alone would
be a way to spell any stale citation as provenance and quietly silence the check. It is
red-cased — case G15.m7 strips the currency condition from GR-02 and the check turns red.

**A hole the suite found while this was being built.** Anchor detection was first scoped
to the *line*. Case G15.m6 — a stale reference injected onto the same line as the
legitimate anchor — was MISSED, because one anchor sentence was granting anchor status
to every reference sharing its line. A Markdown table cell is a single line and can hold
several sentences, so that is exactly where it would have happened in practice.
Detection is now scoped to the **sentence** containing the reference, and m6 is caught.

The register entry is **retired**. `KNOWN_STALE_CURRENCY_CLAIMS` is now empty, and a test
asserts it stays empty so an entry cannot appear silently. The mechanism remains for a
future finding that genuinely needs a ruling before it can be fixed.

Result across the record: **5 currency claims correct, 50 provenance citations and 2
ratification anchors all naming revisions that exist.**

### Consequences in the repository

| Change | Where |
|---|---|
| GR-02 amended; FMEA v0.14 → v0.15 with a changelog entry citing this ruling | `defs/fmea.yaml` → regenerated `docs/fmea.md` |
| G15 ratification-anchor rule, sentence-scoped, both halves required | `tools/checkers/defs_generation.py` |
| G15 register entry retired; register asserted empty | `tools/checkers/defs_generation.py` |
| Concept Brief v0.22 → v0.23, companion baseline FMEA v0.14 → v0.15 | `docs/concept_brief.md` |
| Consistency checker baseline synced as v21 | `tools/checkers/design_record_consistency.py` |
| Companion versions updated | `BUILD_HANDOFF.md` |
| Numbering map | `DECISIONS.md`, above |

### One consequence taken as implied, and why

The concept brief's companion baseline cited FMEA v0.14. Advancing the FMEA without
syncing it would have left check G15 failing — the ruling would have produced a red gate
by construction. The sync is therefore treated as the completion of "checker baseline
synced" rather than as a separate decision, following the precedent D-005 set for the
same act. Recorded here rather than done silently.

---

## D-005 — concept brief companion sync, and a cross-reference check

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | D-004's flagged item: the concept brief's status row still claimed "CONOPS v0.8" after CONOPS advanced to v0.9, and no check covered cross-document version references |
| Status | Ruled; implemented |
| Closes | D-004 "One item flagged, not acted on" |

### Ruling (verbatim)

> D-004: Advance the Concept Brief to v0.22 as a companion-baseline sync (CONOPS v0.9),
> changelog citing this ruling. Add a check that validates every cross-document version
> reference in all six documents against the referenced document's actual version,
> red-cased both polarities. Record verbatim in DECISIONS.md.

### The brief, advanced

Concept Brief v0.21 → **v0.22**. The status row's current companion baseline advances
CONOPS v0.8 → v0.9; nothing else changes. Scope, §3 inclusions and exclusions, and the
review-record status are untouched.

The changelog entry was placed immediately before the v0.21 entry rather than at either
end of the section. The brief's changelog is not ordered — it runs v0.13, v0.14 … v0.18,
**v0.21, v0.20, v0.19**, v0.12 … v0.1 — so "append at the end" and "prepend at the top"
would both have been wrong. This is the same non-ordering that made G14's invariant
order-free, and it is recorded here because it will catch the next person too.

### The check — G15, and why flat equality would have been wrong

Implemented as check **G15**. Building it surfaced that "every cross-document version
reference" is two different claims needing two different assertions:

| Kind | Example | Assertion |
|---|---|---|
| **Currency** — what the record *is* now | Brief: "Current companion baseline — CONOPS v0.9" | Must **equal** the referenced document's actual version. This is the class that goes stale, and the class that produced this ruling. |
| **Provenance** — which revision something *happened at* | FMEA §7: "Implemented as HUG-CMD-006 … in Requirements v0.3" | Must name a revision that **exists** — at or below the referenced document's current version. Forcing it to v0.12 would make the record lie about its own history. |

Flat equality would have demanded rewriting 47 legitimate historical citations.
Provenance is identified by region rather than by guesswork — changelog sections,
disposition-ledger sections, provenance sections, numbered ledger items, and
date-stamped owner resolutions. Everything else is read as a currency claim, which is
the conservative direction: an ambiguous reference is checked more strictly, not less.

Executed at both polarities, seven cases:

| Case | Form | Polarity | Result |
|---|---|---|---|
| G15.m1 | The companion baseline left at CONOPS v0.8 — the exact failure that earned the check | red | CAUGHT |
| G15.m2 | A stale Dictionary version in the same baseline list | red | CAUGHT |
| G15.m3 | A stale Replay Schema version in the same list | red | CAUGHT |
| G15.m4 | A provenance citation of Requirements v9.9 — a revision that does not exist | red | CAUGHT |
| G15.m5 | Genuine provenance, "Requirements v0.3", left alone | green | HELD-GREEN |
| G15.m6 | A second, unregistered stale currency claim alongside the registered one | red | CAUGHT |
| G15.m7 | An unrelated edit to the same document | green | HELD-GREEN |

Result across the record: **6 currency claims all correct, 47 provenance citations all
naming revisions that exist.**

### One finding the check turned up, needing a ruling — CLOSED by ruling D-006

**FMEA §2, ground rule GR-02: "Limits are those of the TLM/CMD Dictionary v0.2."** The
dictionary is at v0.5.

It sits in the ground-rules table, outside every historical region, so G15 reads it as a
currency claim and flags it. Two honest readings, and which one is right is a judgment
about the record rather than about the scanner:

- **Provenance.** It names the revision at which those limits were ratified. The
  dictionary records "All limit values and previously ratified content unchanged"
  through v0.5, so the limits GR-02 analysed against are still the current limits and
  the statement is substantively true.
- **A stale currency claim.** It says the limits *are* the v0.2 dictionary's, present
  tense, and the current dictionary is v0.5.

It is **registered, not exempted**, in `KNOWN_STALE_CURRENCY_CLAIMS` with its reasoning
and what it awaits. The register is one entry; case G15.m6 proves a *new* stale claim
still fails, so the register is not a way to switch the check off. Correcting GR-02
would advance the FMEA to v0.15 — a second frozen-document revision — which this ruling
did not authorize.

Recommendation: read it as provenance and leave the text alone, since the limits are
genuinely unchanged and the citation is accurate about where they came from. The
alternative — updating it to v0.5 — is harmless but slightly changes the sentence's
meaning from "the limits ratified at v0.2" to "the limits as of v0.5".

**RULED at D-006:** neither. The owner amended GR-02 to state the ratification anchor
*and* its currency condition explicitly, resolving the ambiguity in the record rather
than choosing a reading of an ambiguous sentence. The register entry is retired.

### Consequences in the repository

| Change | Where |
|---|---|
| Concept Brief v0.21 → v0.22, companion baseline synced, changelog entry citing this ruling | `docs/concept_brief.md` |
| Check G15 with seven two-polarity cases | `tools/checkers/defs_generation.py` |
| GR-02 registered as a known finding awaiting a ruling | `tools/checkers/defs_generation.py` |
| This entry | `DECISIONS.md` |

---

## D-004 — surrogate source object confirmed; GS-RAVENSROOST pinned

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | The two items D-003 left outstanding: confirmation of the specific catalogue object, and the GS-RAVENSROOST site coordinates the record said were in the repository and were not |
| Status | Ruled; implemented |
| Closes | D-003 "Still outstanding" items 1 and 2 |

### Ruling (verbatim)

> D-003: (1) CELTEE 1 / NORAD 41850 confirmed as the surrogate source object. (2)
> GS-RAVENSROOST fixed at 28.5219°N, 80.6817°W — the Kennedy Space Center Visitor
> Complex, the Space Shop. Note: 28.6055/−80.6695 found online is the Apollo/Saturn V
> Center, a different facility — do not substitute it. Verify the pinned point falls
> within the Visitor Complex footprint the same way the element sets were verified,
> recompute geometry from both rulings together, land the computed values in CONOPS §3.3
> as v0.9 citing HUG-SYS-002's pre-authorization and this ruling, sync the checker
> baseline, and record this verbatim in DECISIONS.md.

### Verification of the site, performed as the ruling required

The owner's note was not a precaution — it was correct, and the trap is worse than a
stale search result. **Two public sources publish coordinates 9.37 km apart under the
same name, "Kennedy Space Center Visitor Complex."**

| | Coordinate | Source | Separation from the ruled point |
|---|---|---|---|
| Ruled point | 28.5219 N, 80.6817 W | owner ruling D-004 | — |
| Authoritative reference | 28.521894 N, 80.681702 W | latlong.net, "Kennedy Space Center Visitor Complex, FL, USA" | **0.70 m** |
| Ruled out | 28.6055 N, 80.6695 W | latitude.to, published under the **same** name | **9.37 km** (9.31 km north, 1.19 km east) |

The ruled point is the authoritative reference rounded to four decimal places —
sub-metre. The coordinate the owner ruled out is 9.37 km away and is the Apollo/Saturn V
Center. Two coordinates that far apart cannot both be one facility, so **a name match
alone does not identify a site** — which is exactly the failure mode the element-set
checksums exist to catch in the other half of the geometry.

The separation matters operationally, not only bibliographically: 9.4 km of site
displacement moves every computed contact window, and ASM-03 requires that geometry be
stable across all four campaign passes. Both coordinates are recorded in
`defs/orbit/ground_station.yaml` so a later reader who finds the wrong one can see it
was considered and ruled out rather than overlooked, and two tests assert the pin is the
ruled point and that the propagator is not using the other.

### Geometry recomputed from both rulings together

| Quantity | Computed | Representative value replaced |
|---|---|---|
| Orbital period | 94.73 min | ~96 minutes |
| Orbits per day | 15.20 | roughly 15 |
| Eclipse | one every orbit, 15/day, mean 29.1 min | ~35 minutes every orbit |
| Eclipse share of each orbit | 30% | not previously stated |
| Usable contacts above the 10° mask | 19 across seven days — two to three per day | 4–6 per day |
| Contact duration | mean 5.9 min, longest 7.5 min, shortest 1.3 min | up to ~8 minutes |
| SAA transits | 12/day, 84/week | not previously stated |

The two daily pass clusters CONOPS §3.3 describes are **confirmed by computation rather
than assumed**: the first day's contacts fall at local solar 07.7, 09.2 and 21.1 — the
mid-morning and late-evening overflight times the section names.

The contact count is the one material change, and it is geometry rather than a modelling
choice: at the site's latitude a 10° mask admits three of the five daily horizon
crossings. Two to three a day remains ample for the campaign's scheduled passes
(ASM-02), and objective O1's ≥20 SAA transits per week is met with wide margin.

### Consequences in the repository

| # | Change | Where |
|---|---|---|
| 1 | CELTEE 1 / NORAD 41850 recorded as **confirmed** rather than provisionally selected | `defs/orbit/SOURCE.md` |
| 2 | Site pinned, with the verification and the ruled-out facility recorded | `defs/orbit/ground_station.yaml` |
| 2 | Two tests: the pin is the ruled point and not the other; the propagator uses the pinned site | `tests/test_orbit.py` |
| 3 | **CONOPS advanced v0.8 → v0.9.** §3.3's representative values replaced with computed ones, citing HUG-SYS-002's pre-authorization and this ruling | `docs/conops.md` |
| 3 | §5's preamble swept — it said the element set was not yet pinned, which v0.9 makes false. Its times are unchanged; they were a sequencing template, never contact-window values | `docs/conops.md` |
| 4 | Checker baseline synced to CONOPS v0.9 as **v20** — a document-baseline sync only; no check, claim or self-test case altered | `tools/checkers/design_record_consistency.py` |
| 5 | Companion version updated | `BUILD_HANDOFF.md` |
| 6 | This entry | `DECISIONS.md` |

**Why advancing a frozen document is not a breach of the freeze.** v0.8's own §3.3 said
these values were "representative until the surrogate element set is pinned in the
repository; computed values from the pinned orbit replace them at build (HUG-SYS-002)."
The replacement was pre-authorized by the record itself and is a build obligation
discharged, not a dispositioned value reopened. No objective, limit, threshold,
procedure, fault-set or ops-organization content changed.

### One item flagged, not acted on — CLOSED by ruling D-005

~~`docs/concept_brief.md` carries "Current companion baseline — CONOPS v0.8".~~
**Closed.** The owner ruled the companion sync at D-005: the brief advanced to v0.22,
and check G15 now validates every cross-document version reference in the record, so
this class of staleness fails a gate rather than waiting to be noticed.

---

## D-003 — surrogate reference orbit: element-set class, propagator, and FM-EPS-08

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | `defs/orbit/OPTIONS.md`, prepared at his standing instruction to bring the orbit options before pinning the element set |
| Status | Ruled; implementation in progress. Two items still need him — see "Still outstanding" |
| Form | Selected from the enumerated options rather than given in prose, so the rulings are recorded below as the options he chose, quoted from the option text he selected |

### Rulings

| # | Question | Ruling |
|---|---|---|
| 1 | Which object's element set should the surrogate reference orbit derive from? | **"6U CubeSat on an SSO rideshare"** — Transporter-class deployment, ~500–550 km, mid-morning LTAN |
| 2 | Which propagator? (also the dependency decision) | **"sgp4 + analytical sun"** — one small pip package, no data files; analytical sun position for eclipse rather than a pinned ephemeris binary |
| 3 | How should FM-EPS-08's "energy-negative trend" be read? | **"Worsening depth of discharge"** — the reading the model reproduces; nothing ratified changes |
| 4 | Byte-identical orbit results across different machines? | **"No — across runs is enough"** — HUG-SYS-003's actual requirement |

### What prompted it

The orbit could not be pinned without him, and four separate questions were entangled
in it. Two findings shaped the options, both measured rather than estimated.

**The record's own period narrows the element set more than it appears.** A circular
orbit at 550 km has a 95.5 min period, which is CONOPS §3.3's "~96 minutes". At 705 km
it is 98.7 min, at 786 km 100.4 min. So a Landsat- or Sentinel-class element set would
have meant either accepting contact numbers that disagree with a frozen document or
revising one. Ruling 1 keeps the record intact and additionally makes the surrogate apt
in spacecraft class, not only in geometry.

**FM-EPS-08's stated end effect is not reachable from the ratified envelope.** The row
says the stuck load's energy-negative trend "persists even after payload shed". For
that to be literally true, average sunlit generation would have to be below **9.81 W —
57.7% of the ratified 17 W peak**; a pure cosine average is 63.7%, so even that does
not reach it. The alternative route needs a sunlit fraction below 0.3767, meaning
eclipse above 62% of the orbit, and a 550 km mid-morning SSO gives about 36%. No
credible orbit produces it.

Ruling 3 resolves this without touching a ratified value. The reading it adopts is the
one CONOPS §4.3 already uses for P3 in its own words — *"actual SoC diverges below
plan… manage depth of discharge"* — and the model reproduces every operationally
meaningful part of the row: SoC diverges below plan, depth of discharge worsens
measurably against the same pass without the fault, and load current crosses yellow
before red. The single phrase that overstates it is the row's "SoC declines toward
SAFE".

### Consequences in the repository

| # | Change | Where |
|---|---|---|
| 1 | Element set selected from the ruled class, pinned with its epoch, source and retrieval date | `defs/orbit/` |
| 2 | `sgp4` added as a recorded, version-pinned dependency; propagation and analytical sun position implemented | `requirements.txt`, `sim/orbit.py` |
| 3 | The ruled reading recorded; the pinned-divergence test becomes an assertion of the ruled reading rather than of an open question | `defs/eps.yaml`, `tests/test_eps_model.py` |
| 4 | Reproducibility held to across-runs; no fixed-point grid introduced. The consequence is stated where it matters rather than assumed: trigonometric results can differ between platform maths libraries, so orbit-derived values are reproducible on a machine and are not asserted byte-equal between machines | `sim/orbit.py`, `tests/` |
| — | `defs/orbit/OPTIONS.md` is superseded by the pinned set and its source note, and retained as the record of what was decided against | `defs/orbit/` |

### Still outstanding — CLOSED by ruling D-004 (2026-07-29)

1. ~~**Confirmation of the specific catalogue object.**~~ **Closed.** CELTEE 1 /
   NORAD 41850 confirmed by D-004 item 1.

2. ~~**GS-RAVENSROOST site coordinates.**~~ **Closed.** Pinned by D-004 item 2 at the
   Kennedy Space Center Visitor Complex, 28.5219 N / 80.6817 W, verified sub-metre
   against an authoritative reference — and distinguished from a different facility
   9.37 km away that a second public source publishes under the same name.

---

## D-002 — how the D0-17 supersession is to be phrased

| Field | Value |
|---|---|
| Date | 2026-07-29 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | The Phase 1 build reporting D0-17 items 1 and 2 as "RETIRED" and items 3 and 6 as "RETIRED for the generated documents" |
| Status | Ruled; applied |

### Ruling (verbatim)

> For the retirement pronouncement: phrase it in DECISIONS.md and the evidence index as
> "superseded for the generated documents; residual scope: the three prose documents;
> retirement pronounced at HUG-G002"

### What prompted it

Phase 1's reporting pronounced retirement on its own authority. It is not the builder's
to pronounce. What the build can establish is that the Markdown parsing these items
bounded has been **superseded** for the documents that became generated views, and what
scope remains. Retirement is a gate act.

### Standing phrasing — the pronouncement of record

> **superseded for the generated documents; residual scope: the three prose documents;
> retirement pronounced at HUG-G002**

This is the required form wherever the D0-17 items 1–4 and 6 status is stated. It
applies to every artifact that states that status, not only to the two named in the
ruling: `BUILD_HANDOFF.md` §4 and §6 stated it too, and leaving them saying "retired"
while this file and the evidence index said "superseded" would have created exactly the
cross-document contradiction ground rule 5 requires sweeping. They were swept with the
two named artifacts. That extension is recorded here rather than made silently.

The Phase 6 claim→case→result index (D0-17 item 5, B3) will carry the same phrasing when
it is built; nothing in Phase 1 may pronounce ahead of it.

### Scope precision retained beneath the pronouncement

The pronouncement is the standing form. Beneath it, the per-item supersession scope is
stated factually, because the residual is not uniform across the items:

- **Items 1 and 2** have no prose residual within their own bounds. C14 reads only the
  FMEA, and all four definition-row classes now come from structured sources. Their
  supersession is complete for everything they bound — which is not the same as
  retirement, and is not stated as retirement.
- **Items 3 and 6** are superseded for the three generated documents and remain live
  against `docs/concept_brief.md`, `docs/conops.md` and `defs/replay_schema.md`.
- **Item 4** is structurally enabled only; per the ratified path it reaches the gate
  through the generated traceability matrix's negative cases (B3, Phase 6).

No item is described as retired anywhere in the build's own artifacts. Retirement is
pronounced at HUG-G002.

### Consequences in the repository

| Change | Where |
|---|---|
| D-002 recorded; standing phrasing stated | `DECISIONS.md` |
| §1 acceptance table, §5 heading and per-item table, §6 implementation table restated | `verification/PHASE_1_DEMONSTRATION.md` |
| §4 Phase 1 acceptance sentence and §6 per-item statuses swept to the same phrasing | `BUILD_HANDOFF.md` |

Commit messages already in history use the stronger word ("retires ... outright"). Those
are immutable and are not rewritten; this entry is the correction of record, and the
artifacts a reviewer reads carry the ruled phrasing.

---

## D-009 — the mechanism that actually suppresses the demo plugin

| Field | Value |
|---|---|
| Date | 2026-07-30 |
| Ruled by | Dan Lee-Odinson, design authority |
| Self-label | *(blocker ruling, option (b))* |
| Prompted by | The demo plugin installing itself into HUGINN's instance despite `OPENC3_DEMO=0`, with INST/INST2/EXAMPLE loaded alongside HUGINN |
| Status | Ruled; implemented and verified |

### Ruling (verbatim)

> Blocker ruled, option (b): find the mechanism that actually suppresses the demo
> plugin — check first whether OPENC3_DEMO is tested for presence rather than value —
> encode the suppression in the repo's compose/env template, rebuild from fresh
> volumes, and verify clean. Add a red-cased check that any foreign target in HUGINN's
> instance is a failing check, not a surprise. Record as D-009, then run the four
> demonstrations.

### The mechanism

The owner's first hypothesis was correct. `openc3-cosmos-init:7.2.1`, `/openc3/init.sh`
line 179:

```sh
if [ ! -z $OPENC3_DEMO ]; then
    ruby /openc3/bin/openc3cli load /openc3/plugins/gems/openc3-cosmos-demo-*.gem || exit 1
fi
```

`[ ! -z ... ]` tests the variable for **non-emptiness**. The value is never examined.
Measured in the image at four polarities plus absence:

| Setting | Result |
|---|---|
| `OPENC3_DEMO=0` | **installs the demo** |
| `OPENC3_DEMO=false` | **installs the demo** |
| `OPENC3_DEMO=1` | installs the demo |
| `OPENC3_DEMO=` | suppressed |
| absent | suppressed |

Every spelling of "off" a human would reach for turns it on. Upstream documents this
one line above the variable — *"Comment this variable to disable installing the Demo
(don't set it to 0)"* — and this build vendored that comment and then set it to `0`.

### Why the gate did not catch it

G16 carried a property named *"demo targets off"* since the ground segment was
vendored. It read:

```python
want_demo = "1" if ground["deployment"]["demo_targets"] else "0"
if demo != want_demo: ...
```

It compared the variable against `"0"` and passed green while the demo was installing.
The check encoded **the builder's model of the variable** — a boolean flag — rather than
**the consumer's reading of it** — a presence test. A check built on the same wrong
assumption as the thing it checks certifies the bug.

The red case was worse than useless. It mutated `OPENC3_DEMO=0` → `OPENC3_DEMO=1` and
was CAUGHT, which read as evidence the property was falsifiable. But **both values
install the demo**. The case proved the check could distinguish `0` from `1` — a
distinction the consumer never makes — while the baseline it was defending was broken
the entire time. A red case that flips between two values which both produce the failure
mode demonstrates nothing about the failure mode.

### Consequences

| Change | Where |
|---|---|
| `OPENC3_DEMO` no longer set in any form; the measured polarity table and the reason recorded at the line | `gnd/openc3/.env.template` |
| `OPENC3_EXTERNAL_URL` corrected 2900 → 2910 — upstream's default is the training demo's port, so HUGINN's own UI was handing out links into the other instance | `gnd/openc3/.env.template` |
| G16's demo property rewritten against the measured semantics: suppression means absent-or-empty, and any non-empty value fails. Raises rather than checks if `demo_targets` is ever set true, since there is no correct behaviour for that setting under B10 | `tools/checkers/defs_generation.py` |
| G16 gains an external-URL property: the URL must name a port this stack publishes and must not name one reserved by the training demo | same |
| Red cases replaced: `=0`, `=false` and `=1` each independently red; `=` held green, so the check reads for the condition rather than for a spelling. Two more for the external URL | same |
| `allowed_targets: [UNKNOWN, HUGINN]` with the justification for each | `defs/ground.yaml` |
| Foreign-target check: pure predicate plus a live Redis query, exact in both directions | `tools/ground_targets.py` |
| Eleven red/green cases on the predicate, including the exact inventory the contaminated instance held | `tests/test_ground_targets.py` |
| The plugin gemspec is now generated, carrying the dictionary version into the gem version | `tools/gen_openc3_config.py` |
| COSMOS's runtime write-back untracked; the 12 MB demo gem it had swept into a commit is gone | `.gitignore` |

### Why the foreign-target check is exact in both directions

Foreign targets are the failure that prompted it, but a check hunting only for extras
would report clean on an instance with nothing loaded at all — the usual shape of a
vacuous pass. An instance missing HUGINN is equally not the configuration of record.
`tests/test_ground_targets.py` red-cases the empty instance explicitly.

This matters to B10 specifically. HUG-GND-006 has pass setup verify *the loaded
configuration* against the dictionary of record, and the digest is computed over
HUGINN's own target. A second plugin's targets in the same instance would **not** fail
that comparison — B10 would pass while its sentence was untrue. The contamination was
invisible to the obligation it undermined.

### Verification

Rebuilt from fresh volumes: `docker compose down -v` (nine `huginn_*` volumes; the
operator's `cosmos-project_*` set untouched and the training demo still answering 200 on
2900 throughout), runtime write-back cleared, `.env` regenerated, stack up.

| Evidence | Before | After |
|---|---|---|
| Demo line in the init log | present | absent |
| `plugins/DEFAULT/` | 12 MB gem + instantiated `plugin_instance.json` | empty `targets_modified/` |
| Non-tool plugins in Redis | demo + HUGINN | `openc3-cosmos-huginn-0.5.gem__0` alone |
| Targets loaded | UNKNOWN, HUGINN, INST, INST2, EXAMPLE | UNKNOWN, HUGINN |

The foreign-target check was exercised at both polarities **on the live instance**, not
only in the suite: it failed with `missing ['HUGINN']` before the plugin was installed
and passed with `exactly the permitted set` after.

---

## D-010 — OF-001 ruled, and B10's enforcement point named

| Field | Value |
|---|---|
| Date | 2026-08-04 |
| Ruled by | Dan Lee-Odinson, design authority |
| Self-label | `D-010:` |
| Prompted by | OF-001 (the digest does not bind the generated ground configuration) and OF-003 (nothing performs the pass-setup comparison), both raised by adversarial review of the B10 demonstration |
| Status | Ruled; implemented |

### Ruling (verbatim)

> D-010: OF-001 ruled option 3 — a separate loaded-versus-repository check, exact in both
> directions, live adapter over a pure predicate, red-cased; the source digest keeps its
> dictionary-of-record meaning. B10's enforcement point is a pass-setup verification tool
> executed as PROC-001's pre-pass step per FM-GND-04, GO/NO-GO recorded in the pass
> report; the no-go is procedural — no technical command inhibit. Fix OF-002 and build
> the negative controls from the refutations into all four demonstration harnesses, then
> run them once, properly.

### Why the enforcement point was already the record's

The ruling does not invent a mechanism; it builds the one the record already names.
HUG-GND-006 reads *"At pass setup the ground system shall display the version and digest
of the loaded telemetry/command configuration, and the pre-pass step of PROC-001 shall
verify them against the dictionary of record; a mismatch shall be a no-go for commanding
until resolved."* FM-GND-04's detection column names the same step, and its
excluded-row note (e) says *"the mismatch response reloads and re-runs that same step
under its no-go rule."*

So the no-go being **procedural** is not a weakening. It is what the requirement says: the
pre-pass step of a procedure verifies, and a mismatch is a no-go **for commanding** —
a condition on the Flight Director's go/no-go at AOS − 5 min, not a technical inhibit in
the ground software. Building a command inhibit would have added a mechanism the record
does not have, at the layer where FM-CDH-04's two-step confirmation already lives.

### What the digest keeps meaning, and what the new check adds

| | Binds | Answers |
|---|---|---|
| `SOURCE_SHA256` in `CONFIG_ID.txt` | `defs/tlm_cmd.yaml` | is the loaded configuration the **dictionary of record**? |
| Loaded-vs-repository check | every generated artifact | is the loaded configuration the one **this repository generates**? |

The second is what OF-001 showed missing. The generated ground configuration is
determined by the dictionary *and* the generator, so a generator change moves the
artifact and cannot move the digest — which is exactly what happened at the `fill_fields`
fix, and would have read GO.

### Consequences

| Change | Where |
|---|---|
| Loaded-vs-repository check: pure predicate, live adapter reading the instance's own copies, exact in both directions | `tools/ground_config.py` |
| Pass-setup verification: displays the loaded version and digest, verifies against the dictionary of record, runs the loaded-vs-repository and foreign-target checks, emits GO/NO-GO | `tools/pass_setup.py` |
| GO/NO-GO recorded in the pass report | `docs/pass_reports/` (HUG-OPS-002) |
| The staleness monitor distinguishes *never read* from *read and not advancing* (OF-002) | `gnd/openc3/plugins/openc3-cosmos-huginn/microservices/STALENESS/frame_staleness.py` |
| Negative controls from the refutations built into all four demonstrations | `tools/demonstrate.py` |
| OF-001 and OF-003 dispositioned by this ruling; OF-002 closed by the fix | `verification/OPEN_FINDINGS.md` |

OF-004 and OF-005 are not struck by this ruling. They are demonstration-design constraints
and are discharged by the negative controls rather than by a decision.

---

## D-011 — INSTRUMENT_FAULT, a third evidence outcome

| Field | Value |
|---|---|
| Date | 2026-08-06 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | The B6 evidence directory being deleted rather than recorded, when the monitor was working and the harness could not read it |
| Status | Ruled; implemented |

### Ruling (verbatim)

> Before resuming: add a third manifest outcome to the evidence harness —
> INSTRUMENT_FAULT, meaning collection failed and the subject's status is not established
> by this run — red-cased like the others, and re-record the deleted B6 attempt under it
> so the trail shows what happened.

### Why two outcomes were not enough

PASS and FAIL are both statements about the **subject**: it did the thing, or it did not.
Neither was true of the B6 attempt. The monitor annunciated GREEN, YELLOW and RED
correctly on a CONNECTED link with the dictionary's thresholds, verified in the ground
system's own log, while the harness meant to collect those annunciations returned an
empty transcript.

FAIL would have asserted something false about a working monitor. Deleting the directory
left no trace the attempt had been made — the same silent absence D-008 exists to
prevent, reintroduced at the site D-008 governs.

An INSTRUMENT_FAULT is **not a pass**. `summary()` reports it as its own result so it
cannot be totalled with the passes, and the manifest says the run establishes nothing
about the subject. It is a demonstration still owed.

### Consequences

| Change | Where |
|---|---|
| Third outcome and the manifest banner | `tools/evidence.py` |
| Seven red/green cases, including that an unknown result is still refused and PASS/FAIL must NOT carry the banner | `tests/test_evidence.py` |
| The deleted attempt re-recorded, with what the harness reported and what the ground system emitted | `verification/evidence/B6-...-attempt-2026-08-05/` |
| B6 archives its source before parsing, and parses the archived bytes | `tools/demonstrate.py` |

The raw slice for the original attempt could not be recovered — the container log had
rotated past it — so that artifact is a labelled transcription. That absence is itself
the defect the ruling corrects.

---

## D-012 — OF-006 read-fault vocabulary, and OF-007 accepted as implemented

| Field | Value |
|---|---|
| Date | 2026-08-06 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | OF-006: a monitor that read successfully and then stopped being able to keeps the staleness clock running and annunciates RED once, then falls silent — indistinguishable from a monitor that died |
| Status | Ruled; implemented |

### Ruling (verbatim)

> D-012: OF-006 — product, accept with the stated fix direction. A ground-segment read
> failure and a spacecraft halt are different conditions and must not share a vocabulary.
> The monitor shall annunciate a distinct read-fault condition when reads fail after prior
> success, shall make no spacecraft-staleness claim while unable to read, and shall
> annunciate recovery of the read path; both polarities red-cased. Fix lands before B6 PASS
> evidence is recorded, so the evidence covers the final monitor. Queue an FMEA row for
> silent monitor read-path failure for the HUG-G002 revision set. OF-007 — apparatus,
> accept as implemented: the persisted bucket log is the evidence source of record for B6.
> Record verbatim in DECISIONS.md.

### What the vocabulary now separates

`NO_READ`, `READ_FAULT` and the staleness levels answer three different questions, and
before this ruling the second had no word of its own:

| Condition | Means | Annunciated as |
|---|---|---|
| Never read the counter | The monitor is blind and has never seen the spacecraft | `NO_READ` |
| Read, then stopped being able to | **The ground segment is broken**, and the spacecraft is unobserved | `READ_FAULT` |
| Reading, counter not advancing | **The spacecraft** is not advancing the counter | `GREEN`/`YELLOW`/`RED` |

**No staleness level is annunciated while read-faulted.** A staleness number is a claim
about the spacecraft, and a monitor that cannot read has no basis for one. The clock is
not reset either: if the counter has genuinely not advanced across the outage, that is
real staleness the monitor observes on recovery by comparing values across the gap.

**Recovery is annunciated in its own right.** Falling back to `GREEN` would say the
spacecraft is healthy without ever saying the ground path came back, and the operator
needs to know a gap existed to know what the levels around it are worth.

### Consequences

| Change | Where |
|---|---|
| `READ_FAULT` state, staleness suppressed while read-faulted, explicit recovery annunciation | `tools/gen_openc3_config.py`, regenerated into `gnd/.../STALENESS/frame_staleness.py` |
| Red cases at both polarities: read-fault must be annunciated, and recovery must be annunciated | `tests/test_staleness_monitor.py` |
| Generated-file expectations | `tests/test_ground_config.py` |
| FMEA row for silent monitor read-path failure, queued for the HUG-G002 revision set | `verification/OPEN_FINDINGS.md` |

OF-007 is accepted as implemented: B6 reads COSMOS's persisted bucket log, which held the
annunciations throughout the run that the container log rotated away.

---

## D-013 — Phase 6: the verification apparatus, and what a generated matrix must not be

| Field | Value |
|---|---|
| Date | 2026-08-08 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | Phase 5 closed at `376d248`; B3 (HUG-VER-001), B5 (HUG-VER-003) and the D0-17 item-5 evidence chain were the outstanding verification obligations |
| Status | Ruled; implemented at `0774847`; recorded here under the Phase 6R instruction |

**Recorded after execution, and the register says so.** The ruling was given as the Phase 6
instruction and the build was carried out under it before it was written down here. The
Phase 6 verification report then reported its own governing ruling as missing from the
register — which is the anti-drift clause in item 4 firing on the phase that introduced
it. `D-007` is the standing precedent for an entry whose recording and its authority do
not share a timestamp: the entry records both, because a reviewer should be able to see
which entries were rulings when written and which were written down afterwards.

### Ruling (verbatim)

> Build from `376d248` (gate 7/7, 396 tests).
>
> 1. B3 — traceability matrix. Every governing requirement mapped to the artifact and the executed case ID that verifies it. Derive the matrix from the record — generate it by executing the checks and reading the actual case identifiers, never maintain it by hand beside its sources. A row that cannot name an executed case is a finding, not a blank.
> 2. Verification report per HUG-VER-003 / B5 — produced by EXECUTING the checkers, never by reading the spec. Verdict vocabulary holds throughout: PASS/FAIL speak about the subject; INSTRUMENT_FAULT / READ_FAULT / NO_RECORD speak about the observer or the run.
> 3. ITEM-5 — EVIDENCE CHAIN. Map every direction claim to its executed case ID. Exhibits: D-009, the B6 dead-monitor incident, OF-006, OF-008, OF-009. State explicitly, with reasoning, whether OF-010 joins the exhibit set — do not silently include or omit it.
> 4. Open the report with the exact register tail after Phase 5 — last D-xxx and last OF-xxx, naming any entries Phase 5 added beyond OF-010 — so the Director's ledger and the repo cannot drift.
>
> Standing constraints: evidence written only by the harness into `verification/evidence/`; every checker made to fail on purpose before it is trusted; missing things must be loud.

### What "derive it by executing" forecloses

The ruling's first item rules out the matrix this build would otherwise have produced. A
matrix populated by scanning source for requirement identifiers populates **identically
whether or not a single case ran**, and the scan itself is wrong in ways that read as
thorough: measured across this suite, module-docstring attribution would have credited
`HUG-VER-002` — the two-polarity methodology requirement — with 136 cases, making it the
best-verified requirement in the system, and would have credited all 33 viewer cases to
`HUG-UI-003`, which that file names only to say the design avoids what it forbids.

So attribution is read from the **loaded test object** at run time, never from prose, and
the downstream cell is filled from a run record rather than a scan.

### The clean first run is the danger, not the reassurance

Measured against the record as it stands: all 38 requirements reach a NEED, 37 directly;
the parent graph has three edges and no cycle; all 11 CONOPS identifiers are cited. **Every
failure condition HUG-VER-001 specifies has zero naturally occurring instances**, so a
generator with all of them stubbed to `return True` emits a byte-identical matrix. The
standing constraint — every checker made to fail on purpose before it is trusted — is
therefore not satisfiable from the record and is satisfied against synthesized inputs.

### Consequences

| Change | Where |
|---|---|
| Observation layer: per-case identifiers and outcomes from an executed run; refuses a run that collected fewer cases than the build carries | `tools/verification_run.py` |
| `verifies` / `polarity` declared on 95 test classes, read off the loaded object | `tests/*.py` |
| `CHECK_VERIFIES` beside the checks, so no matrix carries its own copy of the mapping | `tools/checkers/*.py` |
| B3 generator, 7 conditions as a pure function of (spine, CONOPS, run record); 11 synthesized negative cases | `tools/gen_traceability.py` |
| B5 report and ITEM-5 chain; claims authored, execution status joined and not authorable | `tools/gen_verification_report.py`, `defs/evidence_chain.yaml` |
| Both self-tests in the gate — the documents are records of an execution and cannot round-trip | `tools/run_checks.py` |
| Register tail parsed from both registers on every generation | `verification/VERIFICATION_REPORT.md` |

### Item 3 answered: OF-010 joins, as a different species, saying so

The five named exhibits share a shape — a check that **passed** on a proposition it could
not support, silently, which is why each survived. OF-010's validator **failed**, loudly,
on a true record; on that difference alone it would be a correctness defect and not an
exhibit. It is admitted as `EX-7` because a second direction claim inside it has the shape
exactly — *63 green cases, therefore the contract is right*, false because the fixtures
were generated from the procedures' steps while both defects lived in the branches — and
because the only conforming record an operator could have filed would have read as a pass
that went right the first time. The objection is recorded with it: that downstream
consequence is **reasoned, not measured**, and every other exhibit was measured.

### Findings this ruling's execution surfaced

`OF-011` (fixed), `OF-012` and `OF-013` — including five Test-verified requirements whose
every executed case is green, and B14's verdict having no executed case at all. They are
recorded rather than resolved, per the standing constraint that missing things be loud.

---

## D-014 — what makes a contact usable, per tier

| Field | Value |
|---|---|
| Date | 2026-08-08 |
| Ruled by | Dan Lee-Odinson, design authority |
| Prompted by | Phase 7 campaign planning: the computed week contains contacts from 1.33 to 7.5 minutes, and nothing in the record said which of them an operator may schedule commanding on |
| Status | Ruled; operationalised at Phase 7; **both stated readings affirmed by the owner 2026-08-08** |

### Ruling (verbatim)

> "Usable for Commanding: a contact is usable if the time above the mask, minus
> acquisition and setup overhead, leaves enough to complete the smallest activity you'd
> schedule — with margin for one retry; Usable for receiving telemetry: any reportable
> contact"

### Affirmation (verbatim), 2026-08-08

The ruling named two terms it did not define — *reportable*, and what *leaves enough*
does at exact equality. Both were operationalised by the builder, declared as readings
rather than as findings, and offered for overrule. The owner affirmed them:

> "I affirm both stated readings — "reportable" means a contact that can produce at least
> one housekeeping frame, and "leaves enough" admits a contact at exact equality, so
> contact 7 stands usable for commanding. Both interpretations are ruled, not
> provisional."

**What this changes.** Nothing in the arithmetic and nothing in the classified week — the
generator already applied both readings, which is why the affirmation could be given
against a concrete result rather than against a proposal. What changes is their
STANDING: they were the builder's interpretation of the owner's words, and they are now
the owner's words. A later reader must not re-open either as an assumption the build
made on its own authority.

**Why the entry records two acts and not one.** `D-007` is the standing precedent: an
entry whose recording and its authority do not share a timestamp records both, because a
reviewer should be able to see which parts were ruled when written and which became
ruled afterwards. Here the ruling came first and its two readings were affirmed after
being exercised — the reverse order from D-007, and the same reason for recording both.

### Why two tiers and not one threshold

A single number would have made the short contacts worthless, and they are not. A pass
that is too short to command is still long enough to log state of health, and
`HUG-GND-004` requires all received telemetry be logged with timestamps regardless of how
long the contact ran. The ruling separates what a contact can CARRY from what it can
RECORD, and only the first is bounded by how long an activity takes.

### Every quantity comes from the record

The ruling names quantities without giving values, deliberately: the values already exist
and inventing them here would create a second source. Each is read from where it lives —
the arithmetic and the classified week are generated by `tools/gen_campaign.py`, never
typed.

| Quantity | Value | Read from |
|---|---|---|
| Elevation mask | 10° | `defs/orbit/ground_station.yaml` `contact_model.elevation_mask_deg`, citing CONOPS Sec. 3.3 |
| Acquisition overhead | 120 s | PROC-001's own step timings: S04/S05 at `AOS`, S06/S07 at `AOS + 2 min`; S08, the first commanding step, follows S07 |
| Close-out reserve | 120 s | PROC-001-S15 at `LOS - 2 min` — the final state snapshot, which the commanding window may not run into |
| Smallest schedulable activity | 10 s | One command, sent and verified. Dictionary Sec. 2: "No counter delta within 10 s of a verified send = the loss-of-commandability declaration threshold for PROC-003", and PROC-001-S12's unacknowledged branch is that same 10 s |
| Margin for one retry | ×2 → 20 s | The ruling's own clause; PROC-003-S14 is the retry it refers to ("Retry once within the pass") |

### "Reportable", and what it was taken to mean

**Affirmed 2026-08-08 — ruled, not provisional.** `Reportable` is the Director's word and
was not defined in the record. The reading below was stated rather than assumed, exercised
against the computed week, and then affirmed by the owner in those terms: **a contact is
reportable if it can produce at least one housekeeping frame** — that is, if there is
anything to report at all.

The reading comes from two places. The dictionary Sec. 1 fixes the housekeeping frame at
a nominal 1 Hz (`defs/tlm_cmd.yaml` `rate_hz: 1`), so one second above the mask is the
smallest interval that yields a frame. And `HUG-GND-004` requires all received telemetry
to be logged with timestamps, with no lower bound on contact length — so a contact that
yields a frame yields a record, and one that yields no frame yields nothing to log.

The alternative reading — that "reportable" means long enough to produce a pass report
under `HUG-OPS-002` — was rejected: a pass report is a product of the OPERATOR executing
a procedure, not a property of the geometry, and reading it that way would make the tier
depend on what the operator chose to do rather than on what the contact could carry.

**Consequence, stated plainly so it is not mistaken for an oversight:** at 1 Hz every
contact in the computed week clears this bar by two orders of magnitude, so the telemetry
tier admits all 19. That is the ruling working as written, not a check that fails to
discriminate — the discriminating tier is the commanding one, and the classifier is
red-cased against a sub-frame contact to show the telemetry tier can say no.

### "Leaves enough" at exact equality

**Affirmed 2026-08-08 — ruled, not provisional.** The commanding tier compares the time
left after overhead against the time one activity needs with a retry. The ruling says that
time must "leave enough to complete" the activity, and a contact leaving *exactly* the
needed margin does leave enough — so **the comparison is inclusive**:

```
usable for commanding  iff  (time above mask − overhead) >= activity × retry
```

This is not a rounding convention. It decides a real contact in the computed week:
**contact 7 leaves 20 s against 20 s needed and stands usable for commanding.** Under a
strict comparison it would be the only contact in the week to change tier, so the reading
was surfaced in the generated plan rather than settled silently, and the owner affirmed it.

The classifier carries both sides as cases: one second under the threshold is refused,
exactly at the threshold is admitted. A boundary with a red case on each side is a
boundary somebody checked.

### Consequences

| Change | Where |
|---|---|
| Classifier, arithmetic shown, both tiers, red-cased | `tools/gen_campaign.py` |
| Campaign plan source: four passes, procedures, anomalies, inductions | `defs/campaign.yaml` |
| Generated plan with the classified week | `campaign/CAMPAIGN_PLAN.md` |
| A commanded pass scheduled on a contact that is not usable-for-commanding fails generation | `tools/gen_campaign.py` |

---

## D-015 — a pass may span two contacts; the simulator gains a start offset

| Field | Value |
|---|---|
| Date | 2026-09-13 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | OF-016, OF-017, OF-018 — raised the same day while planning PASS-2 |
| Status | Ruled. Binding on the campaign from v0.1 onward |
| Form | Three dispositions and one mechanism, below |

### What was put to him

Planning PASS-2 established by measurement that every anomaly scenario injects its fault
after its assigned 430 s contact has closed, and that for PASS-2 no 430 s window anywhere
in the 23040 s scenario contains both FM-EPS-01's stated detection (string asymmetry,
visible only in sunlight) and PROC-001-S07's routing conditions (limits, crossed only in
eclipse). Three findings were raised. Each was put to the Director as a numbered choice.
He ruled on all three, and separately on the mechanism.

### The dispositions — the Director's own words

> OF-016: Option 3: Admit a two-contact pass for a fault class. We are striving for real
> operations methodology and capability, so let's follow that pattern.

> OF-017: Option 4: Two contacts - Following the decision in OF-016, we will observe the
> asymmetry on a sunlit contact, respond on a later eclipse contact where the limit is
> crossed.

> OF-018: Option 3, record the gap and accept it for v0.1 - the next gate must build
> around the new 2-contact pass ruling for mission generation so that missions do not
> either automatically fail in the future or silently pass because the second pass needed
> is outside of the mission scope.

### The mechanism

Ruled separately, from the same set of choices: **add a start offset to
`tools/serve_sim.py`**. A `--start-at <MET>` flag steps the model silently to the given
mission elapsed time and begins transmitting from there. This is a mechanism, not a
pattern — it changes how a contact is reached, not what a pass is. It was chosen over
re-timing the scenario files, which HUG-SYS-005 makes the sole source of faults and which
the Director declined to disturb, and over shortening the scenarios, which would have
destroyed the four-orbit trend `P2_array_string_loss` exists to produce.

Determinism carries the equivalence: the scenario engine is stepped by count
(HUG-SYS-003), so a silent pre-roll of N steps is exactly the run that would otherwise
have happened. Scripted commands and fault onsets falling inside the pre-roll are applied
to the model as it steps through them.

### What this ruling settles

1. **A pass may span two contacts.** Detection on one, response on another, is a valid
   pass — not a failed pass and not two passes. This is admitted for a fault class, on the
   Director's reasoning that it is what real operations do.
2. **PASS-2 is that pass.** The asymmetry is observed on a sunlit contact; the response is
   flown on a later eclipse contact where `EPS_BATT_SOC` crosses 35 %. Measured, the second
   contact fits inside the scenario's duration with roughly 910 s to spare.
3. **PROC-001-S07 is not given an asymmetry branch**, and no procedure that has passed a
   document gate is reopened by this ruling.
4. **No scenario file is re-timed.**
5. **The absent generation-time check is v0.1 debt, accepted knowingly**, with the
   obligation on the next gate stated above in the Director's own words.

### What this ruling does not settle, and deliberately leaves to the next gate

- How `tools/gen_campaign.py` selects and records a *pair* of contacts for a two-contact
  pass, and what it must refuse when the second contact falls outside the mission.
- What `report.yaml` looks like for a pass with two acquisitions and two losses of signal,
  and how `tools/pass_report.py` validates it.
- Whether the campaign plan's generated prose is checked against the model that produces
  the telemetry, which is OF-018's own subject.

Until that gate, a two-contact pass is flown and filed by hand, as two records or one, at
the Director's direction at the time.

### Relation to earlier rulings

- **D-014** (contact usability) is untouched. Its two tiers still decide which contacts
  can carry commanding; this ruling decides how many of them one pass may use.
- **HUG-SYS-005** (faults come from scenario files only) is untouched and is the reason
  re-timing was rejected.
- **HUG-OPS-002** (an omitted step is never deleted and never rewritten) is untouched.
- **HUG-GND-005** is the precedent OF-018 cites for the shape of the gap: a property
  asserted in the record and credited by checks exercising something adjacent to it.

---

## D-016 — contact designation, two-contact filing, and cross-contact inference

| Field | Value |
|---|---|
| Date | 2026-09-20 (recorded 2026-10-11) |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | Planning PASS-2 under D-015 |
| Status | Ruled. Acted on by 2026-09-20-P2a and 2026-09-20-P2b |
| Form | Three rulings: two by selection from options put to him, one in his words |

### 1. Contact designation — selected

Put to him: only computed contact 1 has its acquisition inside P2's 23040 s mission,
so PASS-2's second contact has no orbit-derived position. He selected the option
labelled "Duration from the week, position chosen": a pass flies a contact's
duration, taken from the computed week, at a mission position the pass plan
chooses, and both numbers are recorded.

### 2. Two-contact filing — his words

> That is my call - record 2 passes, 1 per contact, threaded by one anomaly record.

### 3. Cross-contact inference — selected

Put to him: on contact B both strings read 0.00 A, so PROC-002-S02 and S03 cannot
be answered from contact B's telemetry. He selected the option labelled "Carry
contact A forward, say so in the record": branches may be selected on another
contact's evidence, and every such observation names the contact it came from.

### Recorded late

These rulings were applied in both PASS-2 records on 2026-09-20 but did not reach
this register until 2026-10-11, when a build citing "D-016" found no such entry.

---

## D-017 — PASS-3: the predicted profile first, a load alarm routed to S03, and the change red-lined

| Field | Value |
|---|---|
| Date | 2026-10-11 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | Planning PASS-3 (OF-020, OF-021) |
| Status | Ruled. Ruling 1 acted on at `fac95f2`; rulings 2 and 3 acted on by the PROC-002 change that follows this entry |
| Form | Three rulings, each by selection from options put to him |

### 1. The predicted profile first — selected

Put to him: PROC-002-S02 cannot be completed for PASS-3 as the procedure stands, and
no predicted state-of-charge profile existed for any contact (OF-020). He selected the
option labeled "Build the predicted profile first": the profile is built before PASS-3
is flown. It was built as `tools/gen_pass_plan.py`, to the design rule OF-020 states.

### 2. A load alarm goes to S03 — selected

Put to him: in PASS-3 the load current crosses its 1.5 A yellow limit while
`EPS_BATT_I` stays positive, so neither outcome of PROC-002-S02 can be selected, and
S03, whose `load excursion` test the telemetry meets exactly, is never reached (OF-021,
instance 2). He selected the option labeled "Load alarm goes to S03": when PROC-002
was entered on `EPS_LOAD_I`, S02 records that and continues to S03; for every other
alarm S02's question is unchanged.

### 3. Red-line now, review later — selected

Put to him: PROC-002 has passed a document gate, so changing S02 changes a reviewed
procedure. He selected the option labeled "Red-line now, review later": the Director
approves the change, PASS-3 is flown on the changed procedure, and the change goes to
Sol in the next review gate.

### Recorded late

Ruling 1 was acted on at `fac95f2` before this entry existed. It is recorded here with
the two rulings that follow from it.

---

## D-018 — PASS-4: the staleness annunciator located and red-lined, PROC-003 entered on the alarm, the scripted reset kept

| Field | Value |
|---|---|
| Date | 2026-10-11 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | Planning PASS-4 (OF-025, OF-026) |
| Status | Ruled. Rulings 1 and 2 acted on by the procedures change that follows this entry; ruling 3 needs no change |
| Form | Three rulings, each by selection from options put to him |

### 1. Find it, then red-line — selected

Put to him: the procedures send the operator to a STALENESS target in Packet Viewer that does
not exist, and the monitor announces its levels only as COSMOS log messages (OF-025). He
selected the option labeled "Find it, then red-line": locate where the messages appear on the
console, then red-line the procedure steps to point there, by the route D-017 ruling 3 set. The
check was run the same day. The messages appear in CmdTlmServer's Log Messages list, from the
source `DEFAULT__USER__OPENC3-HUGINN-STALENESS`.

### 2. On the alarm, any time — selected

Put to him: PROC-001 hands off to PROC-003 only at acquisition (S05) and after an
unacknowledged command (S12), so a halt in the middle of a contact has no route, and the report
checker would refuse a record that ran PROC-003 (OF-026). He selected the option labeled "On the
alarm, any time": a staleness alarm at any point in the contact sends the operator to PROC-003,
and after the reset he returns to where he left off in PROC-001.

### 3. Leave it, beat the clock — selected

Put to him: `P4_hk_generation_halt` scripts its own CMD_SYS_RESET at MET 1320, 120 s after the
halt, so the spacecraft recovers without the operator if his reset is late. He selected the
option labeled "Leave it, beat the clock": the scenario is unchanged and the operator sends his
reset before the scripted one. If the scripted reset fires first, the record says so.

---

## D-019 — HUG-G002 scope: the v0.1 release criteria revised, HUG-SYS-006 struck in place, the gaps and register ruled, the target set

| Field | Value |
|---|---|
| Date | 2026-10-12 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | Planning HUG-G002: the evidence index of 2026-10-12 against `BUILD_HANDOFF.md` §5 and §6, and the v0.1 definition of done (concept brief §10) |
| Status | Ruled. Acted on by the changes that follow this entry |
| Form | Three rulings in the Director's own words, then selections from options put to him; on the draft of this entry, a ninth selection, a further ruling and a constraint, in his own words |

The private development archive's D-019 is a different ruling, the public-release ruling.

### The rulings — the Director's own words

> Rulings: First, I am striking the "replayable from the replay package" design requirement - the
> simulation produced findings that showed significant changes were needed to resolve
> procedure issues that had to be flown to be encountered, and so could not be replayed as
> originally designed.  Some of these issues will need to be resolved and proven by flying
> the G002 build-out. 2. The screen recording requirement is changed to the screenshots
> included in the README. 3. VE has been repositioned in the system operations structure and
> will be built out to be a functional UI, rather than a rendering.

### Selections — put to him as options, recorded by the labels he chose

**1. HUG-SYS-006 — "Strike it too".** Put to him: the first ruling strikes the
replay-package line; does it also strike HUG-SYS-006, which requires every campaign session
to play back in the ground system from the ground system's own logs? He selected the option
labeled "Strike it too": ground-system playback of campaign sessions leaves v0.1, and B14's
August demonstration stays in the record as evidence that the path works.

**2. How HUG-SYS-006 is struck — "Struck in place (Recommended)".** Put to him: nothing in
`defs/requirements.yaml` can mark a requirement struck, and 21 test cases and B14's evidence
cite it. He selected the option labeled "Struck in place (Recommended)", offered as the
recommended option: the ID and its text are kept, marked struck by this ruling, and the
traceability matrix shows it as struck.

**3. The mode ladder — "Model-level for v0.1".** Put to him: the autonomous mode ladder never
fired in any campaign pass (B9, OF-022). He selected the option labeled "Model-level for
v0.1": the model-level tests count for this gate, and the flown exercise stays a proposed
v0.2 goal.

**4. Gaps closed before the freeze.** Put to him: which gaps are closed before HUG-G002 is
frozen. He selected all four options offered:

- "B7 and B10 result checks": the hazardous two-step and the configuration no-go results are
  recomputed from their saved evidence, and the generated commands are tested for the
  hazardous flag.
- "Campaign record tests": executed cases tie the flown passes and anomaly reports to
  HUG-OPS-003 and HUG-OPS-004.
- "Failing-side tests": red cases for check G2 (generation is deterministic) and for
  FM-EPS-06 (charge taper at full battery).
- "D-012's FMEA row": the row for silent monitor read-path failure, queued by D-012 for this
  gate, is written into the FMEA.

**5. AR-003's unregistered findings — "Register all five".** Put to him: AR-003 §5 lists five
findings not in the register. He selected the option labeled "Register all five": they are
registered as OF-029 to OF-033, open, for this gate.

**6. The register.** Put to him: findings that still read open although the record shows each
fixed or addressed. He selected "OF-002", "OF-004", "OF-005" and "OF-008 and OF-009": all
five are closed as fixed. For OF-013's two open rows he selected "Update now, close with
tests": their reason is restated now, and they close when the campaign record tests land.
For OF-024 he selected "Leave the plan as flown": the campaign plan stays as PASS-3 flew it,
and OF-024 stands as the record of the error.

**7. What the build-out flies.** Put to him: which issues the HUG-G002 build-out fixes and
then flies, per the first ruling. He selected "AR-003 console issues", "Stuck-load S06
(OF-023)" and "PASS-4 reset evidence". The fourth option, re-flying the D-017 and D-018
red-lines, was not selected; D-017 ruling 3 still sends those red-lines to Sol in this gate.

**8. The target — "December".** Put to him: the month HUG-G002 closes. He selected
"December": December 2026.

**9. VÉ for v0.1 — "Keep VÉ as built for v0.1, and make the functional UI v0.2 scope".**
Selected on the draft of this entry. He stated the selection and its effect in his own words:

> VÉ for v0.1, by my selection "Keep VÉ as built for v0.1, and make the functional UI v0.2
> scope": §3 inclusion 11 and HUG-UI-001 to 007 stand for v0.1 as built and verified (B11).
> Definition-of-done item 7 is struck because rendering the four campaign passes is no longer
> a v0.1 condition. The functional UI of ruling 3 is v0.2 scope and comes with its own
> ratified requirements. Those requirements replace HUG-UI-001 and the §3 exclusion of
> commanding from the viewer, which stand until then.

### A further ruling — the Director's own words

> Also add the decision to specify VÉ is the operator's command console.

### A constraint on the build-out — the Director's own words

> The G002 build-out's changes to `defs/tlm_cmd.yaml` stay description-only, like the OF-031
> fix. A change to any command name, ID, hazardous flag or limit needs a note on its effect on
> the AES authority layer, whose specification is built on dictionary v0.2.

### Below the seam

Above this heading: the Director's words, and the selections he made from options put to him.
Below it: notes made in drafting this entry. They are not his ruling.

**On the further ruling.** It is v0.2 scope. Under Project AESIR, the operator console's
commands are HUMAN-origin requests through BALDUR (AESIR Constitutional Layer v0.5).

### Consequences in the repository

| Change | Where |
|---|---|
| HUG-SYS-006 marked struck in place, citing D-019; the generated requirements view and the traceability matrix show it struck | `defs/requirements.yaml`, the requirements generator, `tools/gen_traceability.py`, `docs/requirements.md` |
| Inclusion 9 struck; definition-of-done items 1 and 5 lose their replay clauses, item 2 notes inclusion 9's strike, item 6 becomes the screenshots included in the README, item 7 struck by selection 9; HUG-G002's target set to December 2026; the status line names CONOPS v0.10. Struck text kept and marked | `docs/concept_brief.md` §3, §10, §9 and the status line, as v0.26 |
| The replay clauses of O4, NEED-04 and §3.2 struck, kept and marked | `docs/conops.md`, as v0.10 |
| B14's row: HUG-SYS-006 marked struck; the August demonstration kept as evidence of the path | `BUILD_HANDOFF.md` §5 |
| OF-002, OF-004, OF-005, OF-008 and OF-009 closed as fixed; OF-013's reason restated; OF-024 ruled and left as flown; OF-029 to OF-033 registered from AR-003 §5 | `verification/OPEN_FINDINGS.md` |
| AR-003 §5's five "Not yet in the register" notes point to their new entries | `docs/anomalies/AR-003-hk-generation-halt.md` |
| Register row for D-019 | the numbering map in this file |

---

## D-020 — FM-GND-07: D-012's FMEA row rated and dispositioned, and §6 kept as the HUG-G001 selection

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | D-019 selection 4, "D-012's FMEA row": D-012 queued an FMEA row for silent monitor read-path failure for this gate without setting its content. The drafted row, FM-GND-07, was shown to the Director with its severity, likelihood and disposition left to him |
| Status | Ruled. Acted on by the changes that follow this entry |
| Form | Four selections from options put to the Director |

### Selections — put to him as options, recorded by the labels he chose

Before he chose, he was told that an R1 or R2 rating reopens the FMEA §6 fault-set
selection: as drafted, the row passes all five screening criteria, so at II/C it would
outrank the two III/C rows and take FM-EPS-08's slot, the stuck-load fault PASS-3 flew.

**1. Severity — "II, Critical (Recommended)".** Put to him: "What severity does FM-GND-07
carry?" He selected the option labeled "II, Critical (Recommended)", offered as the
recommended option. As put:

> A latent defeat of a detection layer: the same rating FM-GND-04 and FM-EPS-10 carry. This
> monitor is FM-CDH-01's only detection.

**2. Likelihood — "C, Occasional (Recommended)".** Put to him: "What likelihood does
FM-GND-07 carry?" He selected the option labeled "C, Occasional (Recommended)", offered as
the recommended option. As put:

> 'Has occurred on comparable missions.' It has happened twice on this ground system (OF-002,
> OF-006). That's the same likelihood the record gives FM-CDH-01's software hang and
> FM-GND-04's configuration drift. With II it's R2.

**3. Disposition — "DETECTED (Recommended)".** Put to him: "What disposition does FM-GND-07
carry?" He selected the option labeled "DETECTED (Recommended)", offered as the recommended
option. As put:

> Detection and response are defined, and the response hasn't been exercised in the campaign.
> That's accurate today: the detection is built and red-cased, and the PROC-003-S02 response
> has never been flown.

The option carried the disposition cell's text, which the row carries verbatim:

> DETECTED — read-fault detection built and red-cased per D-012 (OF-006); the PROC-003-S02
> response is defined and was not exercised in the v0.1 campaign

**4. The fault set — "Keep G001 selection (Recommended)".** Put to him: "If the row is R1 or
R2, how should §6 treat it?" He selected the option labeled "Keep G001 selection
(Recommended)", offered as the recommended option. As put:

> §6 stays the selection made at HUG-G001 from the 22 rows the campaign was planned and flown
> on. FM-GND-07 is recorded as added after the campaign flew and is nominated as a v0.2
> campaign candidate (REC-03). The claim that the rule 'reproduces the selected set' is scoped
> to those 22 rows, and G11 and C15 change to match, with red cases.

The option not selected, "Re-run with it in the pool", would have applied the rule as written
to all 23 rows.

### Below the seam

Above this heading: the selections the Director made from options put to him, and the
options as put. Below it: notes made in carrying them out. They are not his ruling.

**The screen reading is not adjudicated.** That FM-GND-07 passes criteria (a) to (e) is the
drafter's reading, put to him with the options. Selection 4 keeps the selection as made, so
the reading stands as context and is not ruled.

**C14 changes too.** The record checker's C14 counted exactly 22 worksheet rows. Scoping the
rule to the 22 HUG-G001 rows required the same change there: C14 now names the 22 rows
instead of counting them.

**The nomination is recorded in §6.3.** REC-03's finding and resolution are unchanged. FMEA
§6.3 records FM-GND-07 as nominated in addition to REC-03's three.

**"Executed", not "flown", in the FMEA.** The record checker's C12 keeps the word "flown" out
of the design record, so the FMEA says the campaign was planned and executed. The option's
wording is quoted above as put.

**OF-035, from drafting the row.** A monitor whose process stops is still silent, and no step
checks that it is running. That falls outside the read path D-012 named, so it is registered
as a finding rather than written into FM-GND-07.

### Consequences in the repository

| Change | Where |
|---|---|
| FM-GND-07 added to §5, rated II/C (R2) and dispositioned DETECTED; §6 scoped to the 22 HUG-G001 rows; new §6.3 records FM-GND-07 as added after the campaign and nominated as a v0.2 campaign candidate; status and changelog | `defs/fmea.yaml`, `docs/fmea.md`, as v0.16 |
| §6.3 rendered after the roll-up; the §6.1 and §6.2 tables render as before, and the §6.2 heading's wording now names the HUG-G001 rows (corrected under D-021: this row first said §6.1 and §6.2 rendered byte for byte as before) | `tools/gen_fmea.py` |
| G11 names the 22 HUG-G001 rows, partitions their R2 rows, and requires §6.3 to list exactly the R2 rows outside them; four red cases and one green case added | `tools/checkers/defs_generation.py` |
| C14 names the 22 HUG-G001 rows instead of counting 22; C15 partitions the HUG-G001 R2 rows and validates §6.3 the same way it validates the exclusion record; twelve red cases and one green case added; checker v22 | `tools/checkers/design_record_consistency.py` |
| The status line names FMEA v0.16 | `docs/concept_brief.md`, as v0.28 |
| OF-006 closed, its queued row landed; OF-035 registered | `verification/OPEN_FINDINGS.md` |
| Register row for D-020 | the numbering map in this file |

---

## D-021 — HUG-G002 build 5: plain console text, the command read-back, the stuck-load wording, and the PASS-4 re-fly scenario

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | D-019 selection 7, which sends "AR-003 console issues" (OF-030, OF-031), "Stuck-load S06 (OF-023)" and "PASS-4 reset evidence" (OF-028) to be fixed and then flown in the HUG-G002 build-out. How each is fixed was put to the Director |
| Status | Ruled. Acted on by the changes that follow this entry |
| Form | Three selections from options put to the Director, and one answer in his own words |

### What he was told before the questions

That the flown records must still validate: pass reports do not record a procedure
version, and the report checker reads the procedures as they stand, so no step name,
record field or existing branch changes. That the procedure changes take the route D-017
ruling 3 set: he approves them now, the re-flies use them, and Sol reviews them in this
gate. And that D-003 item 3, "Worsening depth of discharge", had already ruled on the stuck
load, so the procedure text is what moves.

### 1. OF-031 — the Director's own words

Put to him: "OF-031: how should Command Sender's descriptions become plain text?", with
the options "Generator writes plain text (Recommended)" and "Edit the dictionary's text".
He answered in his own words:

> Generator writes plain text - the generator turns the arrow, dash, and minus sign into
> plain characters and a new check fails any other special character. The dictionary's
> text and its version don't change and nothing in tim_cmd.yaml changes. Claude Code
> reinstalls the plugin before the next pass

### 2. OF-030 — "Read it back before every send (Recommended)"

Put to him: "OF-030: how should the procedures guard against Command Sender's leftover
command?" He selected the option labeled "Read it back before every send (Recommended)",
offered as the recommended option. As put:

> Every step that sends a command gets one sentence: before you send, read the command
> name in Command Sender; it must say that step's command. Command Sender opens on
> whatever was chosen last, which can be hazardous. A new check fails any sending step
> that's missing the sentence.

The option not selected was "Only before hazardous sends".

### 3. OF-023 — "Wording to match D-003 (Recommended)"

Put to him: "OF-023: how should PROC-002 handle the stuck load, given D-003?" He selected
the option labeled "Wording to match D-003 (Recommended)", offered as the recommended
option. As put:

> S05 names the comparison: after the shed, load current should fall to about 0.80 A, the
> bus alone; about 1.20 A means a load the shed didn't remove, which is the stuck load. S06
> stops saying the stuck load arrives with a negative battery current, and says it can
> arrive at 'recovered'. The eps.yaml note is corrected to cite D-003.

The option not selected was "Add a 'stuck load' branch".

### 4. OF-028 — "Only your reset clears it (Recommended)"

Put to him: "OF-028: what should the PASS-4 re-fly's scenario do?" He selected the option
labeled "Only your reset clears it (Recommended)", offered as the recommended option. As
put:

> A copy of the scenario for the re-fly; the original stays, so the flown PASS-4 still
> checks out. It adds one command before the halt, so the counters read 2 before it and
> 1/0 only after a reset. It has no scripted reset: if you don't reset, telemetry stays
> down. Replaces D-018 ruling 3 for the re-fly. PROC-003-S04 compares with the counters
> from before the halt.

The options not selected were "Keep a late safety net" and "Counters only".

### Below the seam

Above this heading: the Director's words, the selections he made from options put to him,
and the options as put. Below it: notes made in carrying them out. They are not his ruling.

**`tim_cmd.yaml`.** Answer 1 names `tim_cmd.yaml`. The build reads it as
`defs/tlm_cmd.yaml`, the file the option he adapted names, and changes nothing in it.

**What the generator maps.** The three characters are U+2192, the arrow, written `->`;
U+2014, the em dash, written `-`; and U+2212, the minus sign, written `-`. They reached four
definitions: the descriptions of CMD_SAFE_ENTER, CMD_SYS_RESET and CMD_MODE_SET, and of the
telemetry point EPS_BATT_I, which OF-031 did not name. Comment lines, which the console does
not display, keep their text. The configuration digest is the digest of
`defs/tlm_cmd.yaml` and does not change. Until the plugin is reloaded, the loaded
configuration differs from the repository's, which `tools/ground_config.py --verify`
reports and PROC-001's pre-pass check treats as a no-go.

**The new checks.** G19 holds the read-back. A step sends a command when it opens Command
Sender, or when its action or one of its branches says to send one; a branch that routes
to the step that sends ("Escalate to PROC-003-S03: send CMD_SYS_RESET") is not a send.
Eight steps carry the sentence. PROC-003-S06 and -S08 resend a command the procedure does
not name, so theirs reads "the command you mean to send". PROC-002-S08 sends
CMD_SAFE_ENTER from a branch and carries the sentence there. G20 holds the plain text,
over the definitions rendered from the source and every committed file of the plugin.

**Two sentences beyond the options' words.** PROC-003-S03 also tells the operator to note
the two counters before the reset: the comparison answer 4 names needs them, and no record
field may be added. The stuck-load wording at PROC-002-S06 cites D-003, which an operator
document may do.

**The re-fly scenario is not yet in the campaign plan.**
`sim/scenarios/P4_hk_generation_halt_refly.yaml` is in the repository with its tests.
Pointing the PASS-4 re-fly at it in `defs/campaign.yaml` waits for the re-fly's own
handoff, with its contact.

**Corrected in D-020.** D-020's consequences table said §6.3 was rendered "leaving §6.1 and
§6.2 byte for byte as before". The §6.2 heading's wording changed; only the two tables are
unchanged. The row is corrected and marked, and so is the matching comment in
`tools/gen_fmea.py`. Both were the drafter's notes, not the Director's ruling.

### Consequences in the repository

| Change | Where |
|---|---|
| The ground definitions written as plain text: three characters mapped, any other outside ASCII refused | `tools/gen_openc3_config.py`; `cmd.txt` and `tlm.txt` regenerated |
| The read-back in every step that sends a command; the stuck-load wording at PROC-002-S05 and -S06; PROC-003-S03 and -S04 compare the reset epoch with the counters before the outage; procedures v0.4 | `defs/procedures.yaml`; `procedures/PROC-001.md` to `PROC-003.md` regenerated |
| G19, the read-back, with five red cases and one green; G20, plain text, with four red cases and two green | `tools/checkers/defs_generation.py` |
| The PASS-4 re-fly scenario, and eight tests holding its two properties to both polarities | `sim/scenarios/P4_hk_generation_halt_refly.yaml`, `tests/test_p4_refly_scenario.py` |
| The test floor raised 560 → 568, with the suite at 578 | `tools/verification_run.py` |
| The generation-profile note cites D-003 item 3 | `defs/eps.yaml` |
| OF-023, OF-028, OF-030 and OF-031 ruled and fixed, open until flown | `verification/OPEN_FINDINGS.md` |
| D-020's consequences row corrected and marked; the matching comment corrected | this file; `tools/gen_fmea.py` |
| Register row for D-021 | the numbering map in this file |

---

## D-022 — the ground system moves to the public copy, with its stored data

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Ruled by | Dan Lee-Odinson (Director) |
| Prompted by | Build 5's step 10, the plugin reload D-021 answer 1 assigns to Claude Code. It could not run as written: the ground system on the Director's machine runs from the private archive's `gnd/openc3` folder, where its credentials are, and its containers read the plugin from the archive's copy. Claude Code stopped before the step and reported it |
| Status | Ruled. Acted on by the ground move that follows this entry, on the Director's machine; in the repository, only this entry changes |
| Form | One selection from options put to the Director |

### Selection — "Move it, keep its data (Recommended)"

Put to him: "How should the ground system move to the public copy?" He selected the option
labeled "Move it, keep its data (Recommended)", offered as the recommended option. As put:

> Claude Code copies the archive's credentials file into huginn-public, where git ignores it;
> it's never printed or committed, and the archive keeps its own copy. It recreates the same
> ground system from huginn-public, so the stored logs, users and settings carry over, then
> reloads the plugin and verifies it. I update your preflight's folder line to huginn-public.

The options not selected were "Move it, start fresh" and "Do it with the re-fly handoff".
Before he chose, he was told that editing the archive's plugin files was not offered,
because the archive is frozen by his ruling of 12 October 2026.

### Below the seam

Above this heading: the selection the Director made from options put to him, and the option
as put. Below it: notes made in carrying it out. They are not his ruling.

**Three items, not one file.** The option names "the archive's credentials file". The
ground system's generated, git-ignored state is three items: `gnd/openc3/.env`;
`gnd/openc3/openc3-redis/users.acl`, the Redis users, mounted into Redis; and
`gnd/openc3/plugins/DEFAULT/`, COSMOS's local-mode record of the installed plugin. All three
are copied, so the same ground system comes up. None is printed or committed.

**What carries over, and what stays.** The compose project name, `huginn`, and its named
volumes are the same, so their stored data carries over. The archive keeps its own copies
and is not otherwise changed. The compose file, the Redis and Traefik configuration and the
two templates are byte-identical in the two folders; `cacert.pem` differs only in line
endings in the archive's working copy. The plugin's source differs in three files: the
gemspec's license line, changed at the public release, and the two console definitions
build 5 regenerated. The reload builds the gem from the public copy's source.

**The preflight.** `HUGINN_PREFLIGHT_CHECK.md` is part of the Director's operator kit,
outside the repository. Cowork updates its folder line to the public copy.

### Consequences

| Change | Where |
|---|---|
| The three items copied from the archive's `gnd/openc3` to the public copy's; the ground system recreated from the public copy, with the same project name and volumes; the plugin reloaded and the loaded configuration verified | the ground system on the Director's machine |
| The pre-pass checklist's folder line points at the public copy | the Director's operator kit, outside the repository |
| Register row for D-022 | the numbering map in this file |
