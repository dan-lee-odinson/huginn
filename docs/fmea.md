# HUGINN: CubeSat Mission Operations Simulator
## Failure Modes, Effects, and Criticality Analysis (FMEA), v0.16

| Field | Value |
|---|---|
| Effort prefix | `HUG-` |
| Owner / design authority | Dan Lee-Odinson |
| Date | 2026-07-26 |
| Status | v0.16, build-phase revision per owner ruling D-020 (2026-10-13): FM-GND-07 added, the staleness-monitor read-path row D-012 queued for the HUG-G002 revision set, rated II/C (R2) and dispositioned DETECTED. §6 stays the selection made at HUG-G001 from the 22 worksheet rows the campaign was planned and executed on; the new §6.3 records FM-GND-07 as added after the campaign was executed and nominated as a v0.2 campaign candidate. Selected set, the 22 existing rows' ratings and dispositions, and roll-up unchanged: no R1. Prior revision v0.15, build-phase revision per owner ruling D-006 (2026-07-29): GR-02's limit basis restated as a ratification anchor with its currency condition; no rating, disposition or selected-set change. Prior revisions: v0.14 (G001-16 fix), v0.13 (G001-15 fix), v0.12 (G001-10 fix), v0.11 (G001-09 fix), v0.10 (G001-08 fix), v0.9 (G001-07 fixes), v0.8 (G001-06 fix), v0.7 (G001-05 fixes), v0.6 (G001-04 fix), v0.5 (G001-03 fix), v0.4 (G001-02 fixes), v0.3 (G001 fixes), v0.2 (dispositioned). |
| Drafting assistance | Claude (claude-fable-5). Drafting assistance only; the owner holds design authority and makes all dispositions. |

---

## 1. Purpose and scope

This document analyzes the credible functional failure modes of the HUGINN spacecraft and its ground segment for the v0.1 operations slice, ranks them by criticality, and records for each the detection path, compensating provisions, and disposition. It serves three purposes in the design record:

1. It justifies the v0.1 injectable fault set (HUG-EPS-004) as a *selection* from the credible failure space rather than the whole of it (§6).
2. It verifies that every telemetry limit and procedure in the ratified dictionary and requirements has a failure mode it exists to catch, and that no high-criticality failure mode lacks a detection path.
3. It feeds the change recommendations in §7 into the requirements and dictionary before the HUG-G001 freeze, while defects are cheap.

The analysis is written in-scenario, like the CONOPS: HUGINN is a fictional 6U spacecraft operated through a simulated mission campaign; the analyzed "hardware" is the behavior specified in the requirements and modeled in the simulator. This FMEA covers the mission system as designed for v0.1 — it is not an FMEA of the Python implementation or the development process.

**Analysis level:** functional (subsystem functions, not piece-parts). **Items analyzed:** EPS (solar-array generation, energy storage, bus regulation, load switching, autonomous mode control), C&DH (telemetry generation, command handling, timekeeping), and the ground segment (GS-RAVENSROOST contact, telemetry/command transport, ground monitoring and display, operations). Subsystems excluded from v0.1 by concept brief §3 (thermal, ADCS, link-budget physics, payload sensor) appear only where a failure mode logically lands in them, dispositioned EXCLUDED for completeness.

## 2. Ground rules and assumptions

| ID | Rule |
|---|---|
| GR-01 | Single-failure analysis: one failure mode at a time, from a nominal initial state during routine operations (sunlit/eclipse cycle per the surrogate reference orbit, one ground contact per pass at GS-RAVENSROOST). |
| GR-02 | Design envelope values are those ratified under HUG-EPS-005: 38 Wh battery (2S Li-ion), 5.0 V regulated bus, 17 W peak array in two 8.5 W strings, 4 W nominal bus load, 3 W payload load, charge/discharge efficiency 0.95. Limits are those ratified at TLM/CMD Dictionary v0.2 and unchanged through the current dictionary; any limit change reopens this analysis. |
| GR-03 | Autonomous protective functions (mode ladder per HUG-EPS-003, command validation per HUG-CMD-001/002) are part of the analyzed baseline and are assumed to operate — except in the rows that analyze their own failure (FM-EPS-10, FM-CDH-03). |
| GR-04 | Severity is the worst credible end effect assuming **no ground intervention**. Ground detection and operator response are recorded as compensating provisions, not folded into severity. |
| GR-05 | Likelihood levels are assigned qualitatively from published small-satellite failure experience (EPS and software faults dominate early CubeSat failures; single-string and latch-up events are documented occurrences). Within the exercise they rank risk; they do not predict hardware behavior. |
| GR-06 | Detection paths use only the ratified 16-point telemetry set and ground-derived monitors. A failure mode detectable only with excluded telemetry (e.g., battery temperature) is marked accordingly. |

## 3. Severity and likelihood definitions

**Severity (mission-level end effect, per GR-04):**

| Cat. | Name | Definition |
|---|---|---|
| I | Catastrophic | Loss of spacecraft or permanent loss of mission capability (e.g., battery destruction, unrecoverable loss of bus power or C&DH). |
| II | Critical | Major mission degradation: extended loss of payload operations, loss of ground insight or commandability beyond one pass, latent defeat of a protective layer, or permanent capability reduction short of mission loss. |
| III | Marginal | Temporary, recoverable degradation: loss or curtailment of a single pass or of science collection, recoverable by procedure or autonomous protection. |
| IV | Negligible | Nuisance effect; no mission impact beyond minor inefficiency or operator workload. |

**Likelihood (qualitative, per GR-05):**

| Level | Name | Definition |
|---|---|---|
| A | Frequent | Expected to occur repeatedly during the mission. |
| B | Probable | Expected to occur at least once during the mission. |
| C | Occasional | May occur during the mission; has occurred on comparable missions. |
| D | Remote | Unlikely but credible. |
| E | Improbable | So unlikely it is assumed not to occur; consequences still analyzed. |

**Criticality matrix (risk class):**

| Sev \ Lik | A | B | C | D | E |
|---|---|---|---|---|---|
| I | R1 | R1 | R1 | R2 | R2 |
| II | R1 | R1 | R2 | R2 | R3 |
| III | R2 | R2 | R2 | R3 | R3 |
| IV | R3 | R3 | R3 | R3 | R3 |

R1 (high): unacceptable as-is — requires a design change or an explicit owner waiver. R2 (medium): acceptable only with a verified detection path plus a defined response, or an explicit owner risk acceptance. R3 (low): acceptable as-is.

**Disposition vocabulary:** EXERCISED = injected in the v0.1 campaign and procedure-covered; MITIGATED = design and/or process provision in place and **verified** — earnable only with HUG-G002 evidence, so no row carries it at this pre-build gate; **COMMITTED** = design provision required by a cited requirement or definition of record, whose existence and verification fall due at build and are demonstrated at HUG-G002 (added per F-09); DETECTED = detection and operator response defined but not exercised in the v0.1 campaign; ACCEPTED = risk accepted for v0.1 with rationale (owner ratification required, §8); EXCLUDED = belongs to modeling excluded from v0.1 by concept brief §3.

## 4. Worksheets — spacecraft

### 4.1 EPS

The mode ladder and limit set are deliberately layered: the ground sees EPS_BATT_SOC yellow at 35% before autonomy acts at 30% (LOW_POWER) and 20% (SAFE, coinciding with SoC red). An operator therefore gets one decision window ahead of each autonomous action.

| ID | Function | Failure mode (cause) | End effect (per GR-04) | S | L | Risk | Detection | Compensating provisions | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| FM-EPS-01 | Array generation | Single string output loss (string open, blocking-diode or interconnect failure) | Generation halved (17→8.5 W peak); energy-negative with payload on; autonomy sheds payload at 30% SoC; science lost until ground action | III | C | R2 | EPS_SA1_I/EPS_SA2_I asymmetry; SoC decline crossing YL 35 (dictionary ledger: string failure crosses SoC yellow); EPS_BATT_I discharge trend | Mode ladder (HUG-EPS-003); PROC-002 low-battery response | EXERCISED — fault (a) of HUG-EPS-004; campaign pass P2 |
| FM-EPS-02 | Array generation | Total array output loss (common-cause: deployment/harness failure) | No generation; battery depletes over a few orbits even in SAFE; loss of spacecraft | I | E | R2 | Both SA currents zero while ADM_ECLIPSE = SUNLIT | SAFE mode extends survival time for diagnosis; no recovery without generation | ACCEPTED — full common-cause generation loss (deployment/harness) is rated improbable (E) on 6U deployment heritage, and no credible v0.1 response exists regardless of cause. String redundancy is not the acceptance basis: it does not address a common-cause mode (rationale rewritten per F-10; owner re-ratification §8 item 6) |
| FM-EPS-03 | Array generation | Gradual output degradation (radiation/thermal cycling) | Slowly shrinking power margin; earlier LOW_POWER entries late in mission | III | B | R2 | SA current trend vs. beginning-of-life baseline across passes | Ops planning: reduced payload duty cycle | ACCEPTED for v0.1 (single-pass campaign cannot exercise a slow trend); trending is a v0.2 candidate (§7 REC-03) |
| FM-EPS-04 | Energy storage | Battery cell open-circuit failure | Loss of energy storage; spacecraft dies at first eclipse entry | I | E | R2 | EPS_BATT_V collapse / erratic under load (RL 6.8 V) | None onboard; single battery is a v0.1 architecture decision | ACCEPTED — single-string battery, consistent with 6U class practice |
| FM-EPS-05 | Energy storage | Capacity fade / cell degradation (cycling, age) | Effective capacity below 38 Wh; deeper depth-of-discharge each orbit; shrinking eclipse margin | II | C | R2 | Ground-observed drift in SoC-vs-voltage correlation; earlier YL 35 crossings than the pass plan predicts | Ops planning: DoD management via payload duty cycle | ACCEPTED for v0.1; v0.2 fault-campaign candidate (§7 REC-03) |
| FM-EPS-06 | Energy storage | Charge control failure at full charge (overcharge) | Cell overstress; possible permanent damage | II | E | R3 | EPS_BATT_V YH 8.3 / RH 8.5 | Model behavior: charge tapers at full (dictionary note 2); the EPS_BATT_V voltage-high alarm (YH 8.3 / RH 8.5) exists and receives the generic contingency response (CONOPS Sec. 4.4) — no dedicated battery-voltage-high procedure step in v0.1 (owner disposition, Sec. 8 item 5) | COMMITTED — charge-taper behavior is a definition of record (dictionary note 2), verification due at HUG-G002; absence of a battery-voltage-high procedure step accepted for v0.1 (owner disposition, §8 item 5; CONOPS §4.4 carries the generic-response mapping) |
| FM-EPS-07 | Bus regulation | Regulated bus out of tolerance or lost (regulator failure) | Brownout/damage of all loads including C&DH; loss of spacecraft | I | E | R2 | EPS_BUS_V outside RL 4.75 / RH 5.25 | None onboard; single regulator is a v0.1 architecture decision | ACCEPTED — single-point function, alarm coverage only |
| FM-EPS-08 | Load switching | Load stuck on, +2.0 W unexpected draw (switch FET short, radiation-induced latch-up) | Energy-negative trend persists even after payload shed (stuck load is unsheddable); SoC declines toward SAFE | III | C | R2 | EPS_LOAD_I crosses YH 1.5 A before RH 2.0 A (dictionary ledger item 1); plan-vs-actual SoC divergence | PROC-002 load-shed branch; mode ladder backstop | EXERCISED — fault (b) of HUG-EPS-004; campaign pass P3 |
| FM-EPS-09 | Load switching | Payload switch fails off / payload will not power | Loss of science collection; power posture unaffected | III | D | R3 | CMD_PLD_SET_STATE accepted (CDH_CMD_ACC_CNT increments) but PLD_STATE remains OFF | PROC-001 command-verify step (counter delta + affected telemetry point) | DETECTED by procedure |
| FM-EPS-10 | Autonomous mode control | Mode ladder fails to actuate at 30%/20% SoC (logic fault, SoC estimation error) | Latent defeat of a protective layer: no immediate effect from this failure alone. (The compound outcome — deep discharge during a concurrent energy-negative condition — is recorded under the GR-01 exception note below this table, not rated here.) | II | D | R2 | Ground cross-check: EPS_BATT_SOC below 30 with EPS_MODE still NOMINAL; SoC YL 35 precedes the 30% actuation point by design | CMD_SAFE_ENTER always accepted onboard (HUG-CMD-004) — ground can force SAFE. The HUG-VER-002 checker is development assurance that the ladder was built correctly; it is not a runtime mitigation. | DETECTED — ground cross-check plus commanded backstop; ladder implementation COMMITTED (verification at HUG-G002) |
| FM-EPS-11 | Autonomous mode control | Spurious LOW_POWER/SAFE entry (false trip) | Payload shed; science interrupted; spacecraft safe | III | D | R3 | EPS_MODE annunciation (SAFE annunciates per dictionary); SoC telemetry contradicts the transition | Operator diagnosis; ground-commanded recovery via CMD_MODE_SET (hazardous-flagged, two-step confirmation; REC-01 resolution) | DETECTED — commanded recovery path defined (REC-01 resolved) |

*GR-01 exception note (per G001 F-11; relocated below the completed worksheet per G001-02 F-13):* FM-EPS-10's worst compound outcome — an unactuated ladder concurrent with an energy-negative fault, permitting deep discharge (severity I) — requires two simultaneous failures and is therefore outside the single-failure frame. It is recorded here explicitly rather than silently folded into the row's rating; the compensating path for the compound case is the same ground cross-check and commanded SAFE entry, exercised every pass by the state-of-health assessment.

### 4.2 C&DH

| ID | Function | Failure mode (cause) | End effect (per GR-04) | S | L | Risk | Detection | Compensating provisions | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| FM-CDH-01 | Telemetry generation | Housekeeping telemetry generation halts — no frames generated or transmitted (software hang, task crash); observed as CDH_FRAME_CNT ceasing to advance | Ground loses insight; spacecraft state unknown; commanding integrity uncertain; autonomous protections continue onboard | II | C | R2 | Ground-derived staleness monitor on CDH_FRAME_CNT: no advance 10 s → YL, 30 s → RL (dictionary note 1 — a halted counter cannot alarm itself) | PROC-003 loss-of-telemetry-or-command response, escalating to CMD_SYS_RESET (hazardous, two-step confirm); reset preserves SoC per HUG-CMD-005 | EXERCISED — fault (c) of HUG-EPS-004; campaign pass P4 |
| FM-CDH-02 | C&DH processing | Total C&DH failure — no telemetry, no command response (processor failure) | Loss of insight and commandability; loss of mission | I | D | R2 | No frame lock at AOS on an otherwise nominal pass | None — no redundant processor in the v0.1 architecture | ACCEPTED — consistent with 6U class single-string avionics |
| FM-CDH-03 | Command handling | Command validation faulty — valid commands rejected or ignored (logic fault) | Loss of effective commandability; autonomy still protects power posture | II | D | R2 | CDH_CMD_REJ_CNT delta with CDH_REJ_REASON on a known-good command; CDH_CMD_ACC_CNT not incrementing | Retry per procedure command-verify step; escalation per PROC-003, whose scope covers loss of commandability (REC-02 resolution) | DETECTED by design (command accounting); PROC-003 owns the response (REC-02 resolved) |
| FM-CDH-04 | Command handling | Command executes incorrectly or unintended execution (corruption) | Wrong spacecraft configuration; worst credible case is an unintended hazardous action | II | E | R3 | Command accounting: effect verified by counter delta plus the affected telemetry point after every command | Hazardous commands (CMD_SAFE_ENTER, CMD_SYS_RESET, CMD_MODE_SET) require two-step ground confirmation; onboard inhibits reject unsafe payload activation (HUG-CMD-002) and unsafe mode transitions (HUG-CMD-006) | COMMITTED — the command-safety pattern is required by HUG-CMD-001/002/006 and the dictionary; built and verified at HUG-G002 (F-09) |
| FM-CDH-05 | Timekeeping | MET fault — CDH_MET stalls or jumps | Telemetry timeline corrupted; pass reconstruction and replay-package integrity degraded; no direct spacecraft hazard | III | E | R3 | CDH_MET vs. ground receive-time divergence across the pass | Ground timestamps all telemetry independently (HUG-GND-004); replay package times are pass-relative on the ground recorder's monotonic clock anchored by `meta.epoch_utc` (schema v0.3 §2), so a stalled or jumping CDH_MET corrupts telemetry content only, never the package timeline (G001 F-06; G001-02 F-02) | ACCEPTED — ground timestamping bounds the effect |

## 5. Worksheets — ground segment

| ID | Function | Failure mode (cause) | End effect (per GR-04) | S | L | Risk | Detection | Compensating provisions | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| FM-GND-01 | Contact (GS-RAVENSROOST) | Station outage — pass missed entirely (equipment failure, weather, scheduling) | One or more passes lost; no insight or commanding until next contact; onboard autonomy carries the spacecraft | III | B | R2 | Pass plan vs. contact log; absence of AOS | Single-station architecture is a ratified v0.1 decision; autonomous mode ladder rides through unattended orbits | ACCEPTED for v0.1; missed-pass drill is a v0.2 candidate (§7 REC-03) |
| FM-GND-02 | Telemetry transport | Downlink degraded — corrupted or dropped frames within a pass (link margin, interference) | Partial pass data; gaps in trend assessment | III | C | R2 | Frame-count gaps vs. CDH_FRAME_CNT; framing errors at ingest | Contact model is elevation-mask visibility only — link physics is out of v0.1 scope (brief §3) | EXCLUDED — listed for completeness; behavior not modeled in v0.1 |
| FM-GND-03 | Command transport | Uplink failure — command sent but not received | Commanded action does not occur; pass objectives slip | III | C | R2 | Command accounting: no CDH_CMD_ACC_CNT / REJ_CNT delta after send | Retry within the contact window per the procedure command-verify step | DETECTED by design (command accounting) |
| FM-GND-04 | Ground monitoring | Limit/display misconfiguration — wrong, stale, or hand-edited definitions loaded (config drift, stale generated file) | Latent: alarms missed or false; defeats the detection layer most other rows depend on | II | C | R2 | Loaded-configuration version/digest displayed at pass setup and verified against the dictionary of record per PROC-001's pre-pass step (HUG-GND-006); discrepancy between annunciated limits and the dictionary of record (HUG-GND-002) | OpenC3 definitions generated from `defs/tlm_cmd.yaml`, never hand-edited (HUG-GND-001); configuration mismatch = no-go for commanding (HUG-GND-006); every checker negative-tested (HUG-VER-002) | COMMITTED — detection and response required by HUG-GND-001/-002/-006; built and verified at HUG-G002 (G001 F-09; G001-02 F-04) |
| FM-GND-05 | Operations | Operator error — wrong command, wrong argument, or procedure step skipped | Wrong spacecraft configuration; worst credible case is an unintended hazardous command | II | C | R2 | Per-case (G001-05 F-02): wrong or invalid command/argument — command accounting in-contact (rejection with reason, or an accepted command whose effect fails the step's named telemetry check); wrong-but-valid command — the verify step's effect-vs-procedure check in-contact; skipped procedure step — no in-pass telemetry signature; detected post-pass by comparing the pass report's per-step completion record against the governing procedure — one entry per step, keyed by stable step identifier, with bounded completion state, applicability basis, and state-conditional decision evidence — the branch-selecting observation for a completed decision step, or the record that none occurred for an omitted one (HUG-OPS-002 per G001-06 F-01 / G001-07 F-01 / G001-10 F-01) — so an omission surfaces as an applicable step without a completed entry and is retained truthfully as an omitted entry referencing its anomaly disposition (G001-09 F-01) | Two-step confirmation on hazardous commands; onboard validation rejects out-of-range/inhibited commands (HUG-CMD-001/002); every procedure step names its role and the telemetry it checks (HUG-OPS-001); a step-omission finding is dispositioned as an anomaly in the pass report with defined corrective action — re-execution at the next opportunity where feasible, or an explicit owner risk acceptance approved by the design authority (HUG-OPS-002, Director-ruled Option A per G001-07 F-02, owner-bound per G001-08 F-01) | COMMITTED — the layered command-safety provisions are required by HUG-CMD-001/002 and HUG-OPS-001, and the per-step completion record with omission-anomaly disposition and corrective action by HUG-OPS-002 (G001-06 F-01; G001-07 F-01/F-02); built and verified at HUG-G002 (F-09) |
| FM-GND-06 | Logging / recording | Telemetry or command logging failure — pass record lost or incomplete | Both recording paths for the pass degraded — the ground system's native log record and the recorder-to-viewer replay package; no spacecraft hazard | III | D | R3 | Two separate post-pass checks in the pass report, one per recording path (G001-16 F-01): the native ground-system telemetry and command logs verified complete and played back in the ground system (HUG-GND-004; the playback is the HUG-SYS-006 evidence), and the replay package exported and checked for schema conformance on the recorder-to-viewer path (HUG-UI-002/003) | Each path carries its own response and evidence, and neither substitutes for the other: a native-log failure is worked as a ground-record anomaly against HUG-GND-004/HUG-SYS-006; a package failure is worked against the schema conformance contract, with renderability without live systems the HUG-UI-002 check | DETECTED by procedure |
| FM-GND-07 | Ground monitoring | Staleness monitor read path fails — reads of CDH_FRAME_CNT stop succeeding beneath a running monitor (telemetry API or credential failure), after prior success (OF-006) or from start-up (OF-002) | Latent: FM-CDH-01's only detection is defeated — a real telemetry halt goes unannunciated, and the last annunciated level stands as though current; no spacecraft effect of its own | II | C | R2 | The monitor's read-fault vocabulary (D-012): READ_FAULT at the first failed read after a success, NO_READ while it has never read; no staleness level or number while unable to read; READ_RECOVERED when reads return, with the level restated against working reads. Both polarities red-cased (`tests/test_staleness_monitor.py`); a READ_FAULT in a B6 transcript fails the verdict (`tests/test_b6_verdict.py`) | PROC-003-S02 `monitor read fault` branch: restart the staleness monitor and re-acquire, never escalate — a hazardous command would go to a vehicle nothing has observed; PROC-001-S04 requires GREEN at frame lock, so a monitor already blind when the pass begins is caught there. Open against these provisions: OF-027 (after a restart the annunciator reads GREEN for 10 s whatever the spacecraft is doing) and the evidence-chain EX-3 residual (the B6 verdict does not refuse NO_READ) | DETECTED — read-fault detection built and red-cased per D-012 (OF-006); the PROC-003-S02 response is defined and was not exercised in the v0.1 campaign |

## 6. Fault-set justification

The v0.1 injectable fault set (HUG-EPS-004) was selected, not assumed. The selection is one ordered rule, stated completely below; applying it to the 22 worksheet rows of the HUG-G001 record, the rows the campaign was planned and executed on, reproduces the selected set exactly, with no unstated step (restated per G001-04 F-02; scoped per D-020). Rows added to the worksheets after the campaign was executed are recorded in §6.3.

**Step 1 — candidate pool.** Every HUG-G001 worksheet row rated R2 at baseline. R2 is the highest criticality class present (no credible mode ranks R1 — roll-up below), and R3 rows are below the injection threshold by rule: campaign resources go to the highest class present. Pool: 16 rows.

**Step 2 — eligibility screen.** Criteria (a)–(e) are applied to each pool row in order; a row leaves the pool at the first criterion it fails, and §6.2 records that criterion as its exclusion of record.

- **(a) Single-pass observability.** From GR-01's nominal initial state, the fault's injection and its detection fit within one contact window as a single failure. Modes observable only across multiple passes (trends, drills), only under a compound precondition (the GR-01 exception row), or whose stated detection arrives only in post-pass review rather than within the contact, fail.
- **(b) Detectability.** Detectable with the ratified 16-point telemetry set and ground-derived monitors (GR-06).
- **(c) Procedurable in-pass response.** A credible written-procedure response exists and completes within the same contact window. Modes with no credible v0.1 response — the accepted architecture risks — fail.
- **(d) No excluded model.** Exercising the mode requires no thermal, ADCS, or link-physics model (brief §3).
- **(e) Routine-exercise exclusion (ratified: G001-03 F-06 disposition).** The mode's operator response must require diagnosis and decision beyond the routine command-verify step already exercised on every pass; a mode whose full detection-and-response path is demonstrated continuously by nominal operations adds no unexercised evidence when injected. Per the ratified FM-GND-03 application, a detection that is itself a routine per-pass step, with a response that repeats or escalates that same step per its written branch, is within this exclusion.

**Step 3 — cardinality and ranking.** The v0.1 campaign provides exactly three fault-injection passes (P2, P3, P4; CONOPS §5), so the injectable set is capped at three rows. If the screen left more than three, the top three would be taken by likelihood (A highest), then severity (I highest), then worksheet order. In v0.1 the screen leaves exactly three rows, so the ranking is not invoked and the cap is met exactly.

### 6.1 Selected set — the screen's three survivors

| Injected fault | FMEA row | Risk | Campaign pass | Procedure |
|---|---|---|---|---|
| (a) Array string output zero | FM-EPS-01 | R2 (III/C) | P2 | PROC-002 |
| (b) Stuck-on load, 2.0 W | FM-EPS-08 | R2 (III/C) | P3 | PROC-002 (load-shed branch) |
| (c) Housekeeping telemetry generation halt | FM-CDH-01 | R2 (II/C) | P4 | PROC-003 |

All three survivors carry likelihood C — the highest likelihood among rows passing the screen — which is the sense in which earlier revisions read "highest-likelihood"; likelihood is not itself a screen criterion.

### 6.2 Exclusion record — every unselected HUG-G001 R2 row, with its first failed criterion

| FMEA row | Risk | First failed criterion | Basis |
|---|---|---|---|
| FM-EPS-02 | R2 (I/E) | (c) | No credible v0.1 response regardless of cause (ACCEPTED architecture risk; §8 item 6). |
| FM-EPS-03 | R2 (III/B) | (a) | Degradation trend, observable only across passes (v0.2 candidate, REC-03). |
| FM-EPS-04 | R2 (I/E) | (c) | No onboard or procedural recovery from cell open-circuit (ACCEPTED). |
| FM-EPS-05 | R2 (II/C) | (a) | Capacity-fade trend, observable only across passes (v0.2 candidate, REC-03). |
| FM-EPS-07 | R2 (I/E) | (c) | No credible response to regulator loss (ACCEPTED). |
| FM-EPS-10 | R2 (II/D) | (a) | Latent single failure: detectable only under a compound precondition (SoC decline concurrent with the ladder fault — the GR-01 exception row), not as a single failure in one pass. |
| FM-CDH-02 | R2 (I/D) | (c) | No credible response to total C&DH loss (ACCEPTED). |
| FM-CDH-03 | R2 (II/D) | (e) | Detection is the routine command-verify step's counter/reason reading; the response — retry per that step, escalation per PROC-003's command-path branch — repeats and escalates that same routine step (the ratified FM-GND-03 pattern). |
| FM-GND-01 | R2 (III/B) | (a) | Missed-pass drill spans passes by definition (v0.2 candidate, REC-03). |
| FM-GND-02 | R2 (III/C) | (c) | No written in-pass response exists in v0.1 — degraded-downlink partial-pass data is accepted as recorded, with no procedure branch to exercise; the excluded link-physics model (criterion (d)) is context, not the exclusion of record (per G001-05 F-01). |
| FM-GND-03 | R2 (III/C) | (e) | Ratified exclusion of record (G001-03 F-06 disposition): detection (command accounting) and response (retry per the command-verify step, escalation per PROC-003's command branch) are exercised in every commanded sequence of every pass. |
| FM-GND-04 | R2 (II/C) | (e) | Detection and response are PROC-001's routine pre-pass configuration-verification step (HUG-GND-006), exercised every pass; the mismatch response reloads and re-runs that same step under its no-go rule. |
| FM-GND-05 | R2 (II/C) | (a) | Composite mode screened as a unit: the skipped-step case has no in-pass telemetry signature — its detection is the post-pass comparison of the report's per-step completion record against the governing procedure (HUG-OPS-002, per G001-06 F-01) — so the row's detection does not fit the contact window (per G001-05 F-02); the command-error cases alone would fall under (e) via the routine effect-vs-procedure verify step, noted as context. |

**Assurance-path note (context, not a criterion).** Four excluded rows — FM-EPS-10, FM-CDH-03, FM-GND-04, FM-GND-05 — are failures of, or are caught by, mechanisms whose correct construction is COMMITTED for verification at HUG-G002 (the HUG-VER-002 mode-ladder checker, command-validation negative tests, generated-configuration verification per HUG-GND-006). Earlier revisions cited that provision status as their exclusion reason; provision status is not a selection criterion, and the exclusions of record above rest entirely on the enumerated criteria. This note records the rows' assurance path only.

**Roll-up.** No failure mode in the analyzed baseline ranks R1: the layered design (limit set → autonomy → command safety → procedure) holds every credible mode at R2 or below, which is the result the layering exists to produce.

### 6.3 Rows added after the selection — R2 rows outside the HUG-G001 record

The selection above was made at HUG-G001, and the v0.1 campaign was planned and executed on it. A row added to the worksheets after the campaign was executed is recorded here instead of being screened into that set (D-020), with the ruling that added it. Every R2 worksheet row is therefore in exactly one of §6.1, §6.2 and §6.3.

| FMEA row | Risk | Added | Selection status |
|---|---|---|---|
| FM-GND-07 | R2 (II/C) | v0.16 (D-020) | Added after the campaign was executed; not screened into the v0.1 set. Nominated as a v0.2 campaign candidate, in addition to the three REC-03 nominations (D-020). |

## 7. Findings and recommendations

The analysis surfaced three items, all resolved by owner disposition 2026-07-25 (resolutions recorded inline and in §8):

**REC-01 — SAFE-mode recovery is undefined (from FM-EPS-11; also affects post-P2/P3 recovery).** The v0.1 command set can enter SAFE (CMD_SAFE_ENTER) but nothing defines how the spacecraft leaves it: there is no mode-set command, HUG-EPS-003 specifies only downward transitions, and HUG-CMD-005 is silent on what CMD_SYS_RESET does to EPS_MODE. As drafted, a spacecraft in SAFE — spurious or legitimate — has no specified path back to NOMINAL, and PROC-002 cannot be closed out. Options for owner decision: (1) autonomous recovery to NOMINAL when SoC recovers above a hysteresis threshold (e.g., 40%, aligning with the payload-activation inhibit); (2) add a ground mode-set command (hazardous-flagged); (3) define CMD_SYS_RESET to re-evaluate mode from current SoC. Each option implies a requirements and dictionary revision.

**Resolution (owner, 2026-07-25): option 2.** CMD_MODE_SET added as the fifth command — hazardous-flagged with two-step ground confirmation, targets NOMINAL or LOW_POWER only (SAFE entry remains CMD_SAFE_ENTER's function), rejected below SoC recovery floors (35% for NOMINAL, 25% for LOW_POWER — hysteresis above the 30%/20% autonomous entry points so a commanded exit cannot immediately re-trip). The design principle this establishes: autonomous transitions are downward only (toward safety); upward transitions occur only by deliberate ground command. Implemented as HUG-CMD-006 and an amended HUG-EPS-003 in Requirements v0.3, and the Commands table in Dictionary v0.3.

**REC-02 — No procedure owns loss of commandability (from FM-CDH-03, FM-GND-03).** Detection exists (command accounting) but the response beyond in-pass retry is undocumented. Options: extend PROC-003's escalation pattern to cover command-path failure, or defer a dedicated procedure to v0.2 and record the gap as accepted.

**Resolution (owner, 2026-07-25): extend PROC-003.** PROC-003 is broadened from "stale-telemetry response" to "loss-of-telemetry-or-command response": same detection-confirm-escalate pattern, with a command-path branch keyed on command accounting (no ACC/REJ counter delta after a verified send). HUG-OPS-001 amended accordingly in Requirements v0.3.

**REC-03 — v0.2 fault-campaign candidates.** The accepted R2 rows that a multi-pass v0.2 campaign could exercise, in priority order: battery capacity fade (FM-EPS-05), missed-pass/station-outage drill (FM-GND-01), array degradation trending (FM-EPS-03).

**Resolution (owner, 2026-07-25): ratified as nominated.**

## 8. Disposition ledger (all items resolved by owner, 2026-07-25)

1. Resolved: severity/likelihood definitions, criticality matrix, and ground rules (§2–§3) ratified as drafted.
2. Resolved: all eight ACCEPTED risks ratified — FM-EPS-02, FM-EPS-03, FM-EPS-04, FM-EPS-05, FM-EPS-07, FM-CDH-02, FM-CDH-05, FM-GND-01 (architecture-level acceptances consistent with the ratified v0.1 scope).
3. Resolved: REC-01 ruled as option 2 — ground mode-set command CMD_MODE_SET (see §7 resolution for parameters); drives Requirements v0.3, Dictionary v0.3, Concept Brief v0.3.
4. Resolved: REC-02 ruled as extend PROC-003 (loss-of-telemetry-or-command response); HUG-OPS-001 amended in Requirements v0.3.
5. Resolved: REC-03 v0.2 fault-campaign nominations ratified; FM-EPS-06 note (no battery-voltage-high procedure step) accepted for v0.1 — charge-taper model behavior plus the YH/RH alarm is the coverage (mapping now explicit in CONOPS §4.4).
6. Resolved (2026-07-25, HUG-G001 F-10, owner: accept/product): FM-EPS-02's acceptance re-ratified on the rewritten rationale — likelihood E on 6U deployment heritage plus no credible v0.1 response regardless of cause; string independence struck as a basis.

## 9. Traceability

Requirement IDs cited in this document (HUG-SYS-006, HUG-EPS-003/004/005, HUG-CMD-001/002/004/005, HUG-GND-001/002/004, HUG-OPS-001/002, HUG-UI-002, HUG-VER-002) participate in the generated traceability matrix per HUG-VER-001. Before build, this document's worksheet rows move to structured form alongside `defs/requirements.yaml` so FM IDs can be referenced by checkers and scenario files; this markdown is the drafting surface.

## 10. Changelog

- **v0.16 (2026-10-13):** Build-phase revision per owner ruling D-020, discharging the FMEA row D-012 queued for the HUG-G002 revision set. FM-GND-07 added to §5: the staleness monitor's read path fails beneath a running monitor (OF-006, OF-002), detected by the D-012 read-fault vocabulary and answered by PROC-003-S02's `monitor read fault` branch; rated II/C (R2) and dispositioned DETECTED. §6 is scoped to the selection made at HUG-G001 from the 22 worksheet rows the campaign was planned and executed on, and the new §6.3 records FM-GND-07 as added after the campaign was executed and nominated as a v0.2 campaign candidate. Selected set, the 22 existing rows' ratings and dispositions, and roll-up unchanged: no R1.
- **v0.15 (2026-07-29):** Build-phase revision per owner ruling D-006. GR-02's limit basis restated as a ratification anchor with its currency condition: limits are those ratified at TLM/CMD Dictionary v0.2, unchanged through the current dictionary, and any limit change reopens this analysis. Raised by check G15, which flagged the bare "Dictionary v0.2" citation as ambiguous between provenance and a stale currency claim; the amendment resolves the ambiguity in the text rather than in the checker. No limit value, rating, disposition, selected-set membership or roll-up changes: no R1.
- **v0.14 (2026-07-29):** HUG-G001-16 fix revision per Director disposition (accept/product, G001-16 F-01): FM-GND-06 restated as two explicitly separate recording paths — native-log completeness with in-ground-system playback as the HUG-SYS-006 evidence, and replay-package export with schema conformance on the recorder-to-viewer path (HUG-UI-002/003) — each failure path naming its own response and evidence. The row's detection cell no longer cites HUG-SYS-006 to a package check. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.11 (2026-07-27):** HUG-G001-09 fix revision per Director disposition (accept/product): G001-09 F-01 → skipped-step detection text aligned to the omitted completion state (Requirements v0.10) — an accepted omission is truthfully representable. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.13 (2026-07-29):** HUG-G001-15 fix revision per Director disposition (accept/product, G001-15 F-02): FM-EPS-06's contradictory "no operational overcharge alarm" sentence replaced with the dispositioned coverage — the voltage-high alarm exists and receives the generic contingency response; only the dedicated procedure step is waived for v0.1 (§8 item 5). Selected set, ratings, and roll-up unchanged: no R1.
- **v0.12 (2026-07-28):** HUG-G001-10 fix revision per Director disposition (accept/product): G001-10 F-01 → skipped-step detection text aligned to state-conditional decision evidence (Requirements v0.11) — an omitted decision step is representable without invented evidence. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.10 (2026-07-27):** HUG-G001-08 fix revision per Director disposition (accept/product): G001-08 F-01 → the skipped-step acceptance fallback bound to the owner (explicit owner risk acceptance approved by the design authority, per Requirements v0.9). Selected set, ratings, and roll-up unchanged: no R1.
- **v0.9 (2026-07-27):** HUG-G001-07 fix revision per Director disposition (accept/product): G001-07 F-01 → skipped-step detection bound to the defined completion-record contract (Requirements v0.8); G001-07 F-02 (Option A) → the response leg added: omission findings dispositioned as anomalies with defined corrective action, satisfying the §3 R2 rule from the record itself. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.8 (2026-07-27):** HUG-G001-06 fix revision per Director disposition (accept/product): G001-06 F-01 → FM-GND-05 skipped-step detection bound to the HUG-OPS-002 per-step completion record (Requirements v0.7) — detection is no longer claimed without a mechanism; worksheet cell, §6.2 basis, and disposition provisions updated. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.7 (2026-07-26):** HUG-G001-05 fix revision per Director disposition (accept/product): G001-05 F-01 → §6.2 FM-GND-02 exclusion of record corrected (d) → (c) per strict first-fail application; G001-05 F-02 → FM-GND-05 worksheet detection restated per-case, §6.2 exclusion remapped (e) → (a), and criterion (a)'s failing categories extended to name post-pass-only detection. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.6 (2026-07-26):** HUG-G001-04 fix revision per Director disposition (accept/product): G001-04 F-02 → §6 selection restated as one complete ordered rule (pool → screen (a)–(e) in first-fail order → cardinality/ranking) with a full per-row exclusion record (§6.2) covering all thirteen unselected R2 rows; the packet consistency checks now assert that the selected and excluded sets exactly partition the worksheet R2 set with severity/likelihood agreement row-for-row. Selected set, ratings, and roll-up unchanged: no R1.
- **v0.5 (2026-07-26):** HUG-G001-03 fix revision per owner disposition (accept/product): G001-03 F-06 → §6 selection criteria completed with explicit criterion (e); FM-GND-03 exclusion dispositioned under it. Ratings and roll-up unchanged: no R1.
- **v0.4 (2026-07-25):** HUG-G001-02 fix revision per owner dispositions (accept/product): G001-02 F-13 → GR-01 exception note relocated below the completed §4.1 worksheet (FM-EPS-11 restored to the table); G001-02 F-04 → FM-GND-04 detection/response bound to the new HUG-GND-006 loaded-configuration verification; FM-CDH-05 provision aligned to the schema v0.3 ground-recorder timebase. Ratings and roll-up unchanged: no R1.
- **v0.3 (2026-07-25):** HUG-G001 fix revision per owner dispositions (accept/product): F-09 → COMMITTED added to the disposition vocabulary; FM-EPS-06, FM-CDH-04, FM-GND-04, FM-GND-05 re-dispositioned MITIGATED→COMMITTED; F-11 → FM-EPS-10 reframed as latent single failure (severity I→II, disposition DETECTED+COMMITTED) with the compound outcome under an explicit GR-01 exception note; F-10 → FM-EPS-02 acceptance rationale rewritten and re-ratified (§8 item 6); F-06 → FM-CDH-05 provision text aligned to the schema v0.2 required epoch anchor. Baseline roll-up unchanged: no R1; every mode R2 or below.
- **v0.2 (2026-07-25):** Owner disposition walkthrough completed; all five §8 items resolved. REC-01 → CMD_MODE_SET (option 2, recovery floors 35%/25%); REC-02 → PROC-003 broadened; frame, ACCEPTED risks, REC-03, and FM-EPS-06 note ratified. Affected rows updated (FM-EPS-06/-11, FM-CDH-01/-03/-04); §8 converted to disposition ledger. Companion revisions: Requirements v0.3, Dictionary v0.3, Concept Brief v0.3.
- **v0.1 (2026-07-25):** Initial draft. Methodology per owner ratification of 2026-07-25: severity × likelihood FMECA, full v0.1 ops-slice scope, full coverage with disposition. 22 failure modes; no R1 at baseline; three recommendations raised (§7).
