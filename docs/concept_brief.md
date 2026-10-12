# HUGINN: CubeSat Mission Operations Simulator

**Concept Brief, v0.26 (dispositioned)**

| Field | Value |
|---|---|
| Effort prefix | `HUG-` (per workspace charter gate-ID rule) |
| Owner / design authority | Dan Lee-Odinson |
| Date | 2026-07-24 |
| Status | Dispositioned. All eight open decisions ratified by owner 2026-07-24; FMEA dispositioned 2026-07-25 with REC-01 resolved as a fifth command (CMD_MODE_SET) and REC-02 as a broadened PROC-003. Ground station GS-RAVENSROOST. The HUG-G001 gate series is CLOSED by the owner's §5.4 determination of 2026-07-29: seventeen adversarial review rounds complete (HUG-G001 through HUG-G001-17), all 97 findings dispositioned by the owner — implemented, or carried as ratified verification-apparatus debt under the owner's HUG-G001-13 and HUG-G001-14 rulings; the seventeenth review returned the product record clean, and the single apparatus finding is fixed in this revision. Current companion baseline — CONOPS v0.10, Requirements v0.12, TLM/CMD Dictionary v0.5, FMEA v0.15, Replay Schema v0.9. |
| Drafting assistance | Claude (claude-fable-5). Drafting assistance only; the owner holds design authority and makes all dispositions. |

---

## 1. Purpose and portfolio positioning

HUGINN is a CubeSat mission operations simulator: a fictional 6U spacecraft, simulated in Python, **operated through a simulated mission campaign** against real ground software (OpenC3 COSMOS), with a complete systems-engineering record from stakeholder needs through verification results.

The project exists to close a specific portfolio gap: no current evidence of operational telemetry work, commanding, procedure execution, pass operations, anomaly response, or requirements-to-verification traceability. HUGINN produces that evidence in one coherent artifact.

The one-sentence version for a recruiter: *"I directed the build of a CubeSat training simulator and its ground segment, the starting point for HUGINN's flight version under Project AESIR: I set its scope, ratified its design values, put its systems-engineering record through documented adversarial review and dispositioned every finding, and operated the spacecraft through nominal and anomaly passes by procedure."*

Positioning rules:

- The project name is always paired with its descriptive title: **HUGINN: CubeSat Mission Operations Simulator**. Recruiter comprehension never depends on the mythology.
- Feasibility target per external review (2026-07-24): the v0.1 slice is a 4-6 week build at full-time pace; planned here as roughly two 4-week module cycles part-time. The full multi-subsystem vision is a 3-6 month program and is explicitly out of scope for v0.1.
- The failure mode to avoid is a sprawling half-built simulator. A finished narrow release outscores an ambitious incomplete one (assessed 9/10 finished vs 3/10 sprawling). The exclusions list in §3 is contractual: adding scope requires revising this brief, which means re-gating it.

## 2. Mission rationale (ratified by owner 2026-07-24)

The orbit and instrument must follow from a mission rationale, never from a default. Ratified rationale:

**Mission statement.** HUGINN carries a single energetic-particle counter to map the LEO radiation environment, including the South Atlantic Anomaly and the high-latitude particle regions, as a data product for LEO operators planning component tolerance and safe-mode policy.

**Orbit selection.** Radiation-environment mapping requires latitude coverage from equatorial (SAA) to polar (auroral/cusp regions), which argues for a high-inclination orbit. A sun-synchronous orbit near 550 km with a mid-morning local time of ascending node is proposed. Note what this choice buys the simulation deliberately: an eclipse every orbit, which makes the EPS battery charge/discharge cycle the central operational rhythm of the mission. (A dawn-dusk orbit was considered and rejected for v0.1: it minimizes eclipses, which would flatten exactly the EPS dynamics this slice is built to exercise.)

**Surrogate reference orbit.** A fictional spacecraft cannot have a real element set. HUGINN uses a **surrogate reference orbit derived from a public element set** for an existing satellite in a comparable orbit. The chosen element set is recorded in the repository with its epoch and source, pinned (never auto-updated), so every campaign result is reproducible. All documentation labels it as a surrogate.

**Environmental data.** If NOAA SWPC space-weather data is used in later phases, it is an **environmental truth input** to the payload sensor model, never a substitute for one. A payload sensor model (sampling cadence, noise, saturation, latency, failure behavior) is out of scope for v0.1; the payload in v0.1 is a power load with an on/off state and a sampling-rate register, nothing more.

**Ground station.** One fictional ground terminal, callsign GS-RAVENSROOST, at a fixed site in central Florida (site coordinates recorded in the repo). Pass windows are computed from the surrogate orbit and this site's geometry; the contact model is a simple elevation-mask visibility window.

## 3. Scope

### v0.1 inclusions (the whole list, and nothing else)

1. **EPS model:** solar-array generation (two strings), eclipse transitions, bus loads, battery state of charge with charge/discharge efficiency. Time-stepped simulation, deterministic for a given scenario seed.
2. **Telemetry:** 10-20 points per the TLM/CMD dictionary (companion doc), nominal 1 Hz frame.
3. **Commands (five):** payload state set (on/off), payload sampling-rate set, safe-mode entry, system reset, mode set (ground-commanded recovery from SAFE/LOW_POWER; added by FMEA REC-01 disposition, 2026-07-25). Command acknowledgement, rejection with reason codes, and accept/reject counters.
4. **Ground contact model:** one station, elevation-mask visibility, telemetry and commanding only inside contact windows.
5. **Ground system:** OpenC3 COSMOS as the primary command-and-control system: packet definitions, limits, displays, command sending, logging. (Open MCT deferred; if used later it is an optional visualization layer only.)
6. **Procedures (three):** PROC-001 nominal activation pass; PROC-002 low-battery response; PROC-003 loss-of-telemetry-or-command response (broadened from stale-telemetry-only by FMEA REC-02 disposition, 2026-07-25).
7. **Fault injections (three):** solar-array string failure; stuck-on load (unexpected power draw); stale telemetry (frame counter stops advancing). Faults are defined in scenario files, never code edits.
8. **Campaign:** at least one nominal pass and three anomaly passes, executed human-in-the-loop, each producing a pass report. Documented interactive passes are the evidence; there is no unattended multi-day campaign in v0.1.
9. ~~**Recorded replay:** every pass is recorded and replayable in the ground system without the simulator running, so a reviewer never needs a live setup.~~ Struck by D-019.
10. **SE record:** thin CONOPS + stakeholder needs, numbered requirements, telemetry/command dictionary, FMEA, tool-generated traceability matrix, verification report, anomaly reports, post-campaign report. The replay package format is documented as an interface definition (see §5.1).
11. **Mission viewer (VÉ):** a polished, game-quality, display-only web viewer that renders recorded replay packages. Requirements HUG-UI-001 through HUG-UI-007. Boundaries in §5.1 are part of this inclusion: display-only, replay-driven, static hosting, limits derived from the dictionary source, text-only rendering of package content.

### v0.1 exclusions (adding any of these requires revising and re-gating this brief)

Thermal model. ADCS model. Link-budget/comms modeling beyond the visibility window. Payload sensor model. Multi-day unattended campaigns. Machine-learning or LLM components (MIMIR integration is a later phase, advisory-only when it comes). Live external data feeds (BIFROST is a separate adapter project). Any second spacecraft. Any SSA/conjunction function (HEIMDALL is a separate effort, if ever). Commanding, or any control path, from the mission viewer. Live telemetry streaming into the viewer (the v0.1 viewer is replay-driven; a live view is a v0.2 candidate).

## 4. Terminology rules (binding for all HUGINN documents and the README)

1. The spacecraft is **operated through a simulated mission campaign**. It is never described as "flown."
2. The orbit is a **surrogate reference orbit derived from a public element set**, always labeled as such. Never "a real TLE."
3. Limits in the dictionary are authoritative *within the simulation*, derived from the EPS design envelope defined in this project. If any value is borrowed from public CubeSat references, the source is cited in the dictionary.
4. External data, if ever ingested, is an environmental truth input, named by source.
5. No claim of operational, flight, or mission-control capability. The words "training-class" or "simulation" appear wherever a reader could mistake the artifact for an operational system.
6. Detection or advisory functions added in later phases are **advisory-only**; command authority always remains with the human operator.
7. The mission viewer is a **display-only mission viewer**, never a "control console," "mission control," or any phrase implying command capability. Passes are executed on the operator console (OpenC3); the viewer renders the record.

## 5. Architecture

```
scenario file (orbit pin, seed, fault schedule)
        |
        v
  Python simulator  ----->  telemetry stream  ----->  OpenC3 COSMOS
  (EPS + orbit +            (TCP/IP interface)        (displays, limits,
   command handling)  <-----  commands  <-----         procedures, logging)
        |                                                   |
        v                                                   v
  recorded truth data                          telemetry/command logs
        \___________________  ______________________________/
                            \/
                     replay package + pass reports
                            |
                            v
              VÉ mission viewer (display-only,
              renders replay packages; no uplink path)
```

Single sources of truth, per the derive-don't-maintain rule:

- `defs/tlm_cmd.yaml` generates both the OpenC3 packet/command definitions and the human-readable dictionary document.
- `defs/requirements.yaml` is the requirements source; the requirements document is a generated view.
- The traceability matrix is generated by tool from requirement IDs referenced in test/checker code. A hand-maintained matrix is prohibited.
- The verification report is generated by executing the checkers, never by writing prose about them. Every checker is made to fail on purpose once (negative check) before its passing result is trusted.
- The replay package schema (`defs/replay_schema.yaml`) is the documented interface between the recording side and the viewer; both reference it, neither embeds its own copy. Viewer limit colorings derive from `defs/tlm_cmd.yaml`, the same source the ground system uses.

### 5.1 Mission viewer: VÉ

**VÉ: HUGINN Mission Viewer** is the public face of the project: a game-quality, designed web application that plays back recorded passes. The architecture rationale is the two-console pattern real missions use: flight controllers work dense, functional displays (here, OpenC3), while the presentation layer the public sees (NASA's Eyes, launch-webcast telemetry) is a separate product consuming the same data. VÉ is that second product.

Boundaries, binding:

1. **Display-only.** No command path exists from VÉ to anything. This is a structural property (no uplink code), verified by inspection, never a configuration flag.
2. **Replay-driven.** VÉ renders recorded replay packages; it does not require the simulator or ground system to be running. This keeps the viewer decoupled: it cannot break, block, or fake the ops evidence.
3. **Static.** VÉ runs from local files or static hosting (GitHub Pages); no backend services.
4. **Derived, not duplicated.** Alarm colorings and limit values come from `defs/tlm_cmd.yaml` at build time; VÉ never hand-defines a limit.
5. **Priority rule (clarified per G001-03 F-05, owner ruling 2026-07-26).** If schedule pressure forces a choice, the four documented passes win over viewer *polish* — and only polish. The minimum viewer — HUG-UI-004's required content, honoring every boundary in this list — is a v0.1 release condition (definition-of-done item 7) and may not slip. A finished ops slice with a plain minimum viewer outscores a stunning viewer orbiting an unfinished mission.
6. **Text-only rendering (HUG-UI-007, per G001-02 F-15).** Replay-package text renders through a text-only sink with no markup or code interpretation; no package content is ever interpreted as executable. Verified with a malicious-markup package test.

Minimum v0.1 content (HUG-UI-004): orbit view with eclipse state and contact window, EPS power-flow animation, battery SoC and voltage trends with limit bands, annunciator panel, command accept/reject events, and a pass timeline scrubber.

**Aesthetic (ratified by owner 2026-07-24, from the three-way concept board): Modern HUD.** Dark glass panels over a faint grid, thin line work, cyan structure. Chart data marks use the validated palette #1D9BD1 / #C57D1F on surface #0B1017 (passes all six dataviz checks: lightness band, chroma floor, CVD separation, normal-vision floor, contrast). Brighter cyan #38BDF8 is UI chrome only; amber is reserved for caution states, red for critical.

## 6. Campaign design

Minimum campaign for v0.1 release, all human-in-the-loop, all recorded:

| Pass | Scenario | Procedure(s) exercised |
|---|---|---|
| P1 | Nominal activation: acquire, verify EPS state, enable payload, set sampling rate | PROC-001 |
| P2 | Solar-array string failure injected before contact | PROC-002 |
| P3 | Stuck-on load; SoC declining faster than predicted | PROC-002 (load-shed branch) |
| P4 | Stale telemetry mid-pass | PROC-003 |

Each pass produces a pass report: pass plan, event timeline, limit violations, actions taken with procedure step references, the per-step completion record against the governing procedure, anomaly disposition — including any step-omission finding, dispositioned with defined corrective action — and open items. Anomaly passes additionally produce an anomaly report. The post-campaign report closes the record.

Stretch goal for v0.2, deliberately not in v0.1: a blind pass where someone other than the operator selects which fault to inject, so diagnosis happens without foreknowledge.

## 7. Gate plan

HUGINN's SE record goes through the workspace's adversarial review process (Sol review, owner disposition) under the `HUG-` prefix. Gates map onto the standard review lifecycle:

- **HUG-G001 (design record review; SRR/PDR-class):** freeze and review the design record before build completes: this brief, CONOPS, requirements (including HUG-UI), TLM/CMD dictionary, replay interface definition, FMEA. Catches requirement and design defects while they are cheap.
- **HUG-G002 (verification and campaign review; TRR/post-test-class):** freeze and review the built artifact's evidence: generated traceability matrix, verification report, pass reports, anomaly reports, post-campaign report.

Packets are assembled per `PACKAGING_RULE.md`, with the machine verification run before every freeze (mechanism inventory by executing checks, manifest verification, leak sweep, and, for code artifacts, clean import and full test collection from packet contents alone). Dispositioned findings from these gates are part of the portfolio deliverable: the README links the review record, alongside the published method (DOI: 10.5281/zenodo.21512210).

## 8. Roadmap beyond v0.1 (sequence per external review, 2026-07-24; item 2 owner addition, 2026-07-25)

1. **HUGINN v0.1:** EPS mission-operations slice (this brief).
2. **MUNINN: HUGINN Operator's Tutorial** (named by owner, 2026-07-25 — Odin's second raven, memory, paired with Huginn's thought): a plain-language teaching document, written for a reader with no aerospace or programming background, that walks them through operating the simulator end to end — bringing up the ground system, running or replaying a pass, reading the displays, responding to an anomaly by procedure — and at every step grounds what the reader is doing in real mission-operations practice: why limit sets are layered ahead of onboard autonomy, why safe mode latches until a human commands recovery, why every command is verified by counter delta plus its telemetry effect, why passes end in reports. A teaching tool first, and simultaneously evidence that the operator understands the domain well enough to teach it. Sequenced after the v0.1 release (it teaches the released artifact); may proceed in parallel with v0.2. Terminology rules (§4) apply in full.
3. **HUGINN v0.2:** expanded fault campaign, blind-injection tabletop passes, possible thermal model.
4. **MIMIR v0.1:** baseline anomaly-detection evaluation on the public JPL SMAP/MSL labeled dataset (separate project, separate brief).
5. **Integration:** one validated MIMIR detector into HUGINN as advisory-only FDIR; human-dispositioned anomaly reports.
6. **BIFROST:** live-data/replay adapter only, if built.
7. **HEIMDALL:** only if SSA becomes a deliberate job-search track; separate brief with the safer "public-data conjunction triage demonstrator" framing.

## 9. Schedule alignment

- v0.1 build window target: August-September 2026, spanning the PHY 1001 module (2026-08-03 to 2026-08-30; the EPS energy-balance model is directly reusable physics practice) and the Fall A module.
- HUG-G001 (design record) target: mid-to-late August 2026, before the bulk of ground-system integration.
- HUG-G002 (verification and campaign) target: ~~end of September 2026~~ December 2026 (D-019).
- Cadence rule: one phase per 4-week module, matching the standing portfolio commitment. Dates are targets, not commitments; the release rule is "frozen and gated," never "it's the end of the month."

## 10. Definition of done (v0.1 release criteria)

1. Four passes executed and documented per §6~~, each replayable from the recorded package~~ (replay clause struck by D-019).
2. All eleven inclusion items in §3 present, except inclusion 9, struck by D-019; zero exclusion items present.
3. Traceability matrix and verification report generated by tool; every checker negative-tested.
4. HUG-G001 and HUG-G002 dispositioned; accepted findings implemented.
5. README presents the project in one screen: what it is, what it is not (terminology rules honored), ~~how to replay a pass,~~ where the SE record and review record live (replay clause struck by D-019).
6. ~~A short screen recording of one nominal and one anomaly pass.~~ The screenshots included in the README (D-019 ruling 2).
7. ~~VÉ renders all four campaign passes from their replay packages, in the ratified aesthetic, from static hosting or local files, honoring every §5.1 boundary including text-only rendering (HUG-UI-001..007). This is the minimum viewer of the §5.1 priority rule: a release condition, not deferrable polish.~~ Struck by D-019 selection 9.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scope creep into a sprawling simulator | §3 exclusions are contractual; scope changes force a brief revision and re-gate. |
| Python skill gap (owner is early in the Python track) | The EPS model is arithmetic and control flow; no advanced libraries required. Skyfield handles orbit propagation. AI-assisted development is used and documented per the owner's established practice. |
| OpenC3 bring-up cost (Docker, packet config learning curve) | Timebox first bring-up to one week using the COSMOS demo configuration. Fallback while learning: matplotlib strip charts from the recorded stream, with OpenC3 integration as its own milestone rather than a blocker. |
| Time pressure from 45+ hr/wk work plus coursework | Module-cadence phasing; the narrow slice is the release, everything else is roadmap. |
| Fidelity rabbit holes (battery chemistry, orbit perturbations) | Model fidelity is bounded by the requirements; anything not needed to exercise a procedure or a limit is out. |
| Viewer polish competes with ops evidence | §5.1 priority rule: passes win over polish. Polish beyond the HUG-UI-004 minimum can slip; the minimum viewer honoring every §5.1 boundary is a release condition and cannot (G001-03 F-05, owner ruling). VÉ remains decoupled (replay-driven), and the display-only boundary prevents it from growing into a second ground system. |
| A beautiful viewer invites "what's behind it?" skepticism | The README leads with the operator console and the SE record; VÉ is presented as the presentation layer over recorded evidence, never as the ground system. |

## 12. Repository layout (proposed)

```
huginn/
├── README.md
├── docs/
│   ├── concept_brief.md
│   ├── conops.md
│   ├── requirements.md            (generated view; source in defs/)
│   ├── tlm_cmd_dictionary.md      (generated view; source in defs/)
│   ├── fmea.md
│   ├── verification_report.md     (generated by executing checkers)
│   ├── traceability_matrix.md     (generated by tool)
│   ├── pass_reports/
│   └── anomaly_reports/
├── defs/
│   ├── requirements.yaml          (single source: requirements)
│   ├── tlm_cmd.yaml               (single source: telemetry + commands)
│   ├── replay_schema.yaml         (interface definition: recorder → viewer)
│   └── orbit/                     (pinned surrogate element set + source note)
├── sim/
│   ├── eps.py
│   ├── orbit.py
│   ├── spacecraft.py
│   ├── interface.py               (OpenC3-facing TCP interface)
│   └── scenarios/                 (seed + fault schedule files)
├── gnd/
│   └── openc3/                    (plugin/config generated from defs/tlm_cmd.yaml)
├── procedures/
│   ├── PROC-001_nominal_activation.md
│   ├── PROC-002_low_battery.md
│   └── PROC-003_loss_of_telemetry_or_command.md
├── tools/
│   ├── gen_dictionary.py
│   ├── gen_openc3_config.py
│   ├── gen_traceability.py
│   └── checkers/
├── tests/
├── viewer/                        (VÉ: static web app, display-only)
└── replay/                        (recorded campaign packages)
```

## 13. Provenance and references

- Concept originated in a brainstorming session (Claude, 2026-07-24); scoped per an external feasibility review (GPT, 2026-07-24), whose corrections are incorporated throughout, most materially: campaign framing (documented human-in-the-loop passes over unattended duration), surrogate-orbit labeling, orbit-follows-rationale, sensor-model honesty, and the narrow MVP.
- Ground software: OpenC3 COSMOS (https://docs.openc3.com/docs); NASA Open MCT (https://github.com/nasa/openmct) deferred.
- Review methodology: Lee-Odinson (2026), *The Process Is the Product*, https://doi.org/10.5281/zenodo.21512210.

## 14. Changelog

- **v0.13 (2026-07-27):** HUG-G001-09 fix-revision status sync: nine completed rounds, 67 dispositioned findings, companion versions current (Requirements v0.10, FMEA v0.11). No scope change; §3 inclusions and exclusions unchanged.
- **v0.14 (2026-07-28):** HUG-G001-10 fix-revision status sync: ten completed rounds, 70 dispositioned findings, companion versions current (Requirements v0.11, FMEA v0.12). No scope change; §3 inclusions and exclusions unchanged.
- **v0.15 (2026-07-28):** HUG-G001-11 fix-revision status sync: eleven completed rounds, 74 dispositioned findings, companion versions current (CONOPS v0.6). No scope change; §3 inclusions and exclusions unchanged.
- **v0.16 (2026-07-28):** HUG-G001-12 fix-revision status sync: twelve completed rounds, 79 dispositioned findings, companion versions unchanged (all five round-12 findings were apparatus — the six-document record itself drew none). No scope change; §3 inclusions and exclusions unchanged.
- **v0.17 (2026-07-29):** HUG-G001-13 fix-revision status sync: thirteen completed rounds, 86 dispositioned findings; Replay Schema v0.7 (F-06: pass_id grammar and filename binding); the owner's ruling narrows the consistency checks' claims to the record's defined table grammar and carries the six remaining apparatus findings as ratified debt with two retirement paths: items 1–4 and 6 of the D0-17 register retire at build when defs/ generation supersedes Markdown parsing (HUG-G002); item 5 — suite-traceable residual execution — retires only through its amended claim-to-executed-case-and-result criterion with required polarity at HUG-G002 (D0-17 as amended per G001-14 F-04). No scope change; §3 inclusions and exclusions unchanged. *(This entry originally assigned all six items to defs/-generation retirement — accurate under the original D0-17, superseded by the amendment one round later; corrected to the two-path statement at v0.21 per G001-17 F-01.)*
- **v0.18 (2026-07-29):** HUG-G001-14 fix-revision status sync: fourteen completed rounds, 90 dispositioned findings; Replay Schema v0.8 (F-01: canonical lowercase pass_id form, reserved-basename exclusion, recorder reuse refusal); the checks complete the claim narrowing at the five remaining sites (F-02/F-03), and D0-17's item-5 retirement criterion is amended per the owner's F-04 disposition. No scope change; §3 inclusions and exclusions unchanged.
- **v0.26 (2026-10-12):** Release criteria and schedule revised per Director ruling D-019: §3 inclusion 9 struck; §10 items 1 and 5 lose their replay clauses, item 2 notes inclusion 9's strike, item 6 becomes the screenshots included in the README, and item 7 is struck (selection 9); §9's HUG-G002 target moves to December 2026; the status line names CONOPS v0.10. Struck text is kept and marked.
- **v0.25 (2026-10-11):** The §1 one-sentence version for a recruiter is recast in the Director's directed wording, per Director direction, to match the README of the public release. Its first-person claims of having built the simulator and written the systems-engineering record are replaced with what the Director did: directed the build, set its scope, ratified its design values, dispositioned every review finding and operated the passes. The sentence also names this release as a training simulator and the starting point for HUGINN's flight version under Project AESIR. No scope change; §3 inclusions and exclusions unchanged.
- **v0.24 (2026-09-13):** Mission viewer renamed ODIN → **VÉ** (ASCII identifier `VE`) per Director direction. ODIN now names the operational intelligence of Project AESIR — the component that runs the mission and holds a rung on the authority ladder — and could not also name a display-only viewer in a programme whose architecture turns on command authority. VÉ is Odin's brother, whose gift to the first humans is sight. Naming convention follows the RAGNAROK precedent: **VÉ** as the display form in prose, headings and UI text; `VE` as the ASCII identifier in filenames, paths, code identifiers and repo names — so the package is `ve/` and the browser globals are `VE_PACKAGE` / `VE_LIMITS`. HUG-UI-001 through HUG-UI-007 are unchanged in substance and apply to the viewer under its new name; in particular HUG-UI-001's display-only property — no code path from the viewer to the simulator, the ground system or any command interface, verified by inspection and never a configuration flag — is unaffected. The rename is recorded forward, not backward: changelog entries, revision history, dated notes and every artifact under `verification/evidence/` keep ODIN as written, annotated “(now VÉ)” only where a reader would otherwise be lost. No scope change; §3 inclusions and exclusions unchanged.
- **v0.23 (2026-07-29):** Companion-baseline sync per owner ruling D-006. The status row's current companion baseline advances FMEA v0.14 → v0.15, following the FMEA build-phase revision ruled at D-006 in which ground rule GR-02's limit basis was restated as a ratification anchor with its currency condition. This revision changes the companion version citation and nothing else: no scope change, §3 inclusions and exclusions unchanged, review-record status unchanged. The sync is not a separate decision — check G15 enforces companion-baseline currency, so advancing the FMEA without it would leave the record inconsistent by construction.
- **v0.22 (2026-07-29):** Companion-baseline sync per owner ruling D-005. The status row's current companion baseline advances CONOPS v0.8 → v0.9, following the CONOPS build-phase revision ruled at D-004 in which §3.3's representative orbit and contact values were replaced by values computed from the pinned surrogate reference element set and the pinned GS-RAVENSROOST site — a replacement HUG-SYS-002 pre-authorized and CONOPS v0.8's own §3.3 announced. This revision changes the companion version citation and nothing else: no scope change, §3 inclusions and exclusions unchanged, review-record status unchanged.
- **v0.21 (2026-07-29):** HUG-G001-17 fix revision and series closure per owner disposition (accept with modification/apparatus, G001-17 F-01): the v0.17 changelog entry's debt-retirement statement corrected to the two retirement paths — items 1–4 and 6 via defs/ generation, item 5 only via its amended claim-to-case-and-result criterion (D0-17 as amended). The seventeenth review returned the product record clean with all sixteen prior rounds' closures held; the owner's §5.4 determination closes the HUG-G001 series. Status row updated: seventeen rounds, 97 findings, series closed. No scope change; §3 inclusions and exclusions unchanged.
- **v0.20 (2026-07-29):** HUG-G001-16 fix-revision status sync: sixteen completed rounds, 96 dispositioned findings; the replay separation completed at FMEA FM-GND-06 (G001-16 F-01: FMEA v0.14), the overcharge-coverage statement corrected at dictionary note 2 (G001-16 F-02: Dictionary v0.5), and the CONOPS revision references corrected §5 → §3.2 (G001-16 F-04: CONOPS v0.8). No scope change; §3 inclusions and exclusions unchanged.
- **v0.19 (2026-07-29):** HUG-G001-15 fix-revision status sync: fifteen completed rounds, 92 dispositioned findings; the two replay obligations separated (G001-15 F-01: Requirements v0.12, CONOPS v0.7, Replay Schema v0.9) and FM-EPS-06's provisions corrected (G001-15 F-02: FMEA v0.13). No scope change; §3 inclusions and exclusions unchanged — item 9 (ground-system replay) and item 11 (ODIN viewer, now VÉ) were always distinct inclusions; the record now allocates them distinctly.
- **v0.12 (2026-07-27):** HUG-G001-08 fix-revision status sync: eight completed rounds, 63 dispositioned findings, companion versions current (Requirements v0.9, FMEA v0.10). No scope change; §3 inclusions and exclusions unchanged.
- **v0.11 (2026-07-27):** HUG-G001-07 fix revision per owner disposition (accept/product, G001-07 F-01): §6 pass-report description aligned to the per-step completion record contract; status row synced (seven rounds, 60 findings, companion versions current). No scope change; §3 inclusions and exclusions unchanged.
- **v0.10 (2026-07-27):** HUG-G001-06 fix-revision status sync (the mechanized review-record claim doing its job): six completed rounds, 57 dispositioned findings, companion versions current (Requirements v0.7, FMEA v0.8). No scope change; §3 inclusions and exclusions unchanged.
- **v0.9 (2026-07-26):** HUG-G001-05 fix-revision status sync (the mechanized review-record claim doing its job): five completed rounds, 55 dispositioned findings, companion versions current (FMEA v0.7, Replay Schema v0.6). No scope change; §3 inclusions and exclusions unchanged.
- **v0.8 (2026-07-26):** HUG-G001-04 fix revision per owner disposition of finding F-06 (accept/product): status row synchronized with the review record of the baseline it ships in — four completed rounds, 49 dispositioned findings, companion versions current (FMEA v0.6, Replay Schema v0.5). The review-record claim is now asserted by the packet consistency checks, so this ripple cannot silently recur. No scope change; §3 inclusions and exclusions unchanged.
- **v0.7 (2026-07-26):** HUG-G001-03 fix revision per owner dispositions: F-04 → HUG-UI-007 integrated into the binding scope (inclusion 11 range, §5.1 boundary 6, definition-of-done item 7); F-05 → ODIN release contradiction resolved by owner ruling — the HUG-UI-004 minimum viewer honoring every §5.1 boundary is a release condition, only polish beyond it may slip (§5.1 priority rule and §11 risk row reworded). Companion baseline refs updated. No change to §3 exclusions.
- **v0.6 (2026-07-25):** HUG-G001-02 fix revision per owner disposition of finding F-14 (accept/product): status field refreshed to the actual gate-series baseline; definition-of-done item 2 corrected to "all eleven inclusion items" (miscounted since ODIN became item 11 in v0.2 — a defect that survived two review rounds before Sol caught it); repository layout renames PROC-003 to its broadened identity. No scope change; §3 inclusions and exclusions unchanged.
- **v0.5 (2026-07-25):** Operator's Tutorial named **MUNINN** per owner (§8 item 2); name paired with its descriptive title per the §1 positioning rule. Same day: CONOPS v0.3 — owner ratified the two [proposed] objective targets (O1 ≥20 SAA transits/week; O3 ≥90% frame recovery), completing CONOPS disposition.
- **v0.4 (2026-07-25):** Roadmap addition per owner direction: HUGINN Operator's Tutorial (§8 item 2) — plain-language teaching walkthrough grounding simulator use in real mission-operations practice; sequenced post-v0.1, parallelizable with v0.2. No change to v0.1 scope; §3 inclusions and exclusions unchanged.
- **v0.3 (2026-07-25):** FMEA v0.1 drafted (severity × likelihood FMECA, full v0.1 ops-slice scope, 22 failure modes, no R1 at baseline) and dispositioned same day (FMEA v0.2). REC-01 resolved as ground mode-set command: inclusion 3 becomes five commands (CMD_MODE_SET; autonomy downward-only, recovery by ground command). REC-02 resolved: PROC-003 broadened to loss-of-telemetry-or-command response. Companion revisions: Requirements v0.3, TLM/CMD Dictionary v0.3. Design record complete for HUG-G001.
- **v0.2 addendum (2026-07-24):** Owner decision walkthrough completed; all eight open decisions ratified (mission/orbit, EPS envelope, 2S battery limits, mode ladder NOMINAL→LOW_POWER 30%→SAFE 20% with 40% activation inhibit, command-safety pattern, 16-point telemetry set, staleness 10/30 s). Ground station renamed GS-RAVENSROOST. [TBR] markers removed from requirements (v0.2) and dictionary (now v0.2).
- **v0.2 (2026-07-24):** Added ODIN mission viewer per owner direction: inclusion 11, §5.1 boundaries, terminology rule 7, viewer exclusions, HUG-UI requirements reference, replay interface definition, definition-of-done item 7, two risk rows, repo additions (`viewer/`, `defs/replay_schema.yaml`). Same day: aesthetic ratified from the concept board (Modern HUD).
- **v0.1 (2026-07-24):** Initial draft from brainstorm + external feasibility review.
