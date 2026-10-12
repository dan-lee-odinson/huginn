# HUGINN: CubeSat Mission Operations Simulator
## Concept of Operations (CONOPS), v0.10

| Field | Value |
|---|---|
| Effort prefix | `HUG-` |
| Owner / design authority | Dan Lee-Odinson |
| Date | 2026-07-25 |
| Status | v0.10, revision per owner ruling D-019 (2026-10-12): the replay clauses of O4, NEED-04 and §3.2 are struck, kept and marked. Prior revision v0.9, build-phase revision per owner ruling D-004 (2026-07-29): §3.3's representative orbit and contact values are replaced with values computed from the pinned surrogate reference element set and the pinned GS-RAVENSROOST site coordinates. This replacement was pre-authorized by HUG-SYS-002 and stated in v0.8's own §3.3 — "computed values from the pinned orbit replace them at build" — so it discharges a build obligation rather than reopening a dispositioned value; §5's preamble is swept to match. No objective, limit, procedure or ops-organization content changes. Prior revision v0.8, HUG-G001-16 fix revision per Director disposition 2026-07-29 (accept, G001-16 F-04): the v0.7 revision references corrected — the two-path recording statement added at v0.7 lives in the §3.2 ground-segment description, not §5 (the representative pass timeline); the substantive two-path text is unchanged. The v0.7 change stands as ratified: §3.2 separates the two recording paths — ground-system native logs for ground-system replay (HUG-SYS-006), and the replay package for the ODIN (now VÉ) viewer (HUG-UI-002/003). All prior ratifications (framing, O1/O3 targets, ops organization, §4.4 limit-response coverage, per-step completion record, state-conditional pass-report form) unchanged. |
| Drafting assistance | Claude (claude-fable-5). Drafting assistance only; the owner holds design authority and makes all dispositions. |

---

## 1. Mission overview

### 1.1 Mission statement

HUGINN carries a single energetic-particle counter to map the low-Earth-orbit radiation environment — the South Atlantic Anomaly and the high-latitude particle regions — as a data product for LEO operators planning component tolerance and safe-mode policy. The orbit follows the mission: radiation mapping requires latitude coverage from equatorial to polar, so HUGINN operates in a sun-synchronous orbit near 550 km with a mid-morning local time of ascending node, which additionally places the spacecraft in eclipse every orbit and makes the battery charge/discharge cycle the central operational rhythm of the mission.

### 1.2 Mission objectives

Objectives O1–O3 are stated for the full mission; v0.1 does not exercise them (the v0.1 payload is a switchable power load — the sensor model is out of scope per concept brief §3). Objective O4 is the operations objective the v0.1 campaign fully exercises.

1. **O1 — SAA coverage (full mission):** map particle flux over the South Atlantic Anomaly on at least 20 SAA transits per week with the payload active.
2. **O2 — High-latitude coverage (full mission):** sample both auroral regions (poleward of 60° geographic latitude) on every orbit in which the payload is active.
3. **O3 — Data product (full mission):** deliver a weekly radiation-environment map with documented coverage and gap accounting, recovering at least 90% of collected, time-tagged science frames to the ground.
4. **O4 — Safe operations (exercised in v0.1):** conduct pass operations by written procedure such that every limit violation is detected and annunciated, and responded to per the limit-response coverage of §4.4 — demonstrated over a campaign of at least one nominal and three anomaly passes~~, each replayable from its recorded package~~ (replay clause struck by D-019).

### 1.3 Exercise frame

HUGINN is a fictional spacecraft operated through a simulated mission campaign for mission-operations training and demonstration. The orbit is a surrogate reference orbit derived from a pinned public element set, and the spacecraft is a Python simulation; the ground system operating it (OpenC3 COSMOS) is real. This frame is established here once and is not re-caveated below.

## 2. Stakeholders and needs

| ID | Stakeholder | Need |
|---|---|---|
| NEED-01 | LEO operator (data customer) | Radiation-environment data with known, documented coverage of the SAA and high-latitude regions — which requires faithful orbit propagation, eclipse state, and ground-visibility geometry from the reference orbit. |
| NEED-02 | Mission operations team | Displays, limits, commands, and written procedures sufficient for one operator on console to conduct a pass safely, in real or accelerated time, with the modeled spacecraft behaving consistently at 1 s resolution or finer. |
| NEED-03 | Spacecraft (asset preservation) | Protection from deep discharge and unsafe configurations: autonomous power-mode protection when the ground cannot act, and onboard validation that rejects unknown, out-of-range, or inhibited commands. |
| NEED-04 | Systems engineering / review authority | A reproducible, reviewable record from need through verification: deterministic scenarios, faults injected by scenario file, ~~every pass recorded and replayable without live systems,~~ reports and verification results generated from evidence (replay clause struck by D-019). |

## 3. System overview

### 3.1 Space segment

HUGINN is a 6U CubeSat whose electrical power subsystem is modeled end-to-end: two solar-array strings (17 W peak combined), a 38 Wh battery behind a 5.0 V regulated bus, switchable loads (4 W bus, 3 W payload), and an autonomous power-mode ladder (NOMINAL → LOW_POWER at 30% SoC → SAFE at 20%, downward transitions only). The payload is a switchable load with a sampling-rate register. Command handling implements the five-command set with acceptance/rejection accounting and reason codes. Deliberately not modeled in v0.1: thermal, attitude control, link-budget physics, and payload sensor physics.

### 3.2 Ground segment

One ground terminal, GS-RAVENSROOST, at a fixed site in central Florida. OpenC3 COSMOS is the command-and-control system: telemetry displays and limit monitoring generated from the dictionary of record, command sending with two-step confirmation on hazardous commands, and timestamped logging of all telemetry and commands. Every pass is recorded on two separate paths (G001-15 F-01): the ground system's native timestamped telemetry and command logs ~~support replaying any pass in the ground system without the simulator running (HUG-SYS-006)~~ (replay clause struck by D-019), and a replay package — renderable without the simulator or ground system running — feeds the VÉ display-only mission viewer as the presentation layer over the operational record (HUG-UI-002/003).

### 3.3 Orbit and contact geometry

Sun-synchronous, mid-morning local time of ascending node. The values below are **computed** from the surrogate reference element set pinned in `defs/orbit/` and the GS-RAVENSROOST site coordinates pinned alongside it. They replace the representative values this section carried through v0.8, which is what HUG-SYS-002 requires and what v0.8 itself said would happen (owner ruling D-004, 2026-07-29).

| Quantity | Computed from the pinned orbit and site | Representative value replaced |
|---|---|---|
| Orbital period | 94.73 min | ~96 minutes |
| Orbits per day | 15.20 | roughly 15 |
| Eclipse | one every orbit, 15 per day, mean 29.1 min | ~35 minutes every orbit |
| Eclipse share of each orbit | 30% | not previously stated |
| Usable contacts above the 10° elevation mask | 19 across seven days — two to three per day, averaging 2.7 | 4–6 per day |
| Contact duration | mean 5.9 min, longest 7.5 min, shortest 1.3 min | individual passes up to ~8 minutes |
| SAA transits | 12 per day, 84 per week | not previously stated |

The two daily pass clusters near the mid-morning and late-evening local overflight times are confirmed by the computation rather than assumed: the first day's contacts fall at local solar 07.7, 09.2 and 21.1.

The contact count is the one material change, and it is geometry rather than a modelling choice — at the site's latitude a 10° elevation mask admits three of the five daily horizon crossings. Two to three contacts a day remains ample for the campaign's scheduled passes (ASM-02), and objective O1's target of at least 20 SAA transits per week is met with wide margin.

## 4. Operational phases and scenarios

### 4.1 Phases

**Commissioning.** First acquisition, state-of-health verification, and first payload activation, executed as the nominal activation pass (PROC-001). Commissioning ends when the spacecraft has completed one full orbit power-positive with the payload active.

**Routine operations.** Recurring pass operations: pass planning against predicted contact windows and eclipse timing, state-of-health assessment each contact, payload duty management within the power envelope, and pass reporting. The operational heartbeat is the orbit's charge/discharge cycle; the operator's standing question is whether actual state of charge tracks the plan.

**Contingency operations.** Entered when a limit violation, unexpected trend, or loss of insight is declared an anomaly by the Flight Director. Governed by PROC-002 (low battery) and PROC-003 (loss of telemetry or commandability); ends with recovery to a commanded stable configuration and an anomaly report.

### 4.2 Nominal pass scenario (representative times)

At AOS−15 min the Ops Planner reviews the pass plan: contact window, predicted elevation profile, eclipse timing relative to the pass, planned commands, and the SoC value the plan predicts at acquisition. At AOS−5 the EPS Officer brings up the ground system, confirms displays and limits loaded from the dictionary of record, and the Flight Director gives go for the pass.

At AOS, telemetry frame lock: the EPS Officer confirms CDH_FRAME_CNT advancing and the staleness monitor green. By AOS+2 the state-of-health assessment is complete — EPS panel green, battery voltage and SoC against plan, both array-string currents consistent with the illumination state. The commanding window follows per the pass plan: for a payload activation, the EPS Officer confirms EPS_BATT_SOC above the 40% activation inhibit, the Flight Director authorizes, and CMD_PLD_SET_STATE ON is sent; the operator verifies CDH_CMD_ACC_CNT incremented by one and PLD_STATE reads ON, then sets the sampling rate (CMD_PLD_SET_RATE, in-range 0.1–10 Hz) and verifies the same way — every command confirmed by counter delta plus its affected telemetry point (PROC-001).

At LOS−2 the EPS Officer takes the final state snapshot — mode, SoC, load current, trend against plan — and at LOS the contact ends. Within 30 minutes the Ops Planner files the pass report: plan, event timeline, any limit violations, actions with procedure step references, the per-step completion record — one entry for every step of the governing procedure, keyed by its stable step identifier, with completion state, applicability basis, and state-conditional decision evidence: the branch-selecting observation for a completed decision step, or the record that no observation was made and no branch was selected for an omitted one — and disposition of anything anomalous, including any step-omission finding raised by the report review, dispositioned as an anomaly with defined corrective action (HUG-OPS-002).

### 4.3 Contingency scenarios

**Solar-array string failure (campaign pass P2).** A string's output drops to zero; generation halves and the spacecraft trends energy-negative with the payload on. The ground sees asymmetric string currents and SoC falling through the 35% yellow limit ahead of plan. PROC-002 governs: confirm the power-negative trend, shed the payload by command, and if SoC continues toward the autonomous thresholds, let the mode ladder protect the spacecraft. Recovery from any resulting LOW_POWER or SAFE state is a deliberate ground act: CMD_MODE_SET, once SoC has recovered above the commanded mode's floor.

**Stuck-on load (campaign pass P3).** An unexpected 2.0 W draw appears and cannot be shed; total load current crosses its yellow limit and actual SoC diverges below plan. PROC-002's load-shed branch governs: isolate what can be shed (the payload), replan the power budget around the stuck load, and manage depth of discharge until the fault clears or is dispositioned as a permanent constraint.

**Loss of telemetry or commandability (campaign pass P4).** The telemetry frame counter stops advancing; the ground-side staleness monitor turns yellow at 10 s and red at 30 s while the spacecraft's true state is unknown. PROC-003 governs: confirm staleness is not a ground-side artifact, then escalate to CMD_SYS_RESET (hazardous, two-step confirmation), which clears the fault, reinitializes counters, and preserves SoC. The same procedure's command-path branch governs the mirror case — telemetry flowing but commands unacknowledged (no accept/reject counter delta after a verified send) — with in-pass retry before escalation.

### 4.4 Limit-response coverage

Every alarmed limit in the dictionary maps to a governing response. The *generic contingency response* is defined once: the Flight Director declares an anomaly, the spacecraft is safed by command (CMD_SAFE_ENTER) if power integrity is threatened, and an anomaly report is filed (§4.1 contingency operations). Dedicated procedures govern where the response has decision structure worth scripting; the remainder carry the generic response or a documented acceptance.

| Alarmed limit (dictionary) | Governing response |
|---|---|
| EPS_BATT_SOC low (YL 35 / RL 20) | PROC-002 low-battery response. |
| EPS_BATT_V low (YL 7.2 / RL 6.8) | PROC-002 (low-voltage presentation of the low-battery condition). |
| EPS_BATT_V high (YH 8.3 / RH 8.5) | Generic contingency response. No dedicated procedure step in v0.1 — accepted by owner (FMEA §8 item 5); charge-taper model behavior is the design provision (FM-EPS-06). |
| EPS_BATT_I (± YL/RL) | Generic contingency response; if driven by a discharge trend, PROC-002 governs. |
| EPS_BUS_V (RL 4.75 / RH 5.25) | Generic contingency response; bus-regulation failure is an architecture-accepted risk (FM-EPS-07) — alarm coverage plus safing is the defined response. |
| EPS_LOAD_I (YH 1.5 / RH 2.0) | PROC-002, load-shed branch. |
| EPS_MODE = SAFE (annunciation) | PROC-002 closeout; recovery is ground-commanded via CMD_MODE_SET. |
| CDH_FRAME_CNT staleness (10 s YL / 30 s RL) | PROC-003 loss-of-telemetry-or-command response. |
| CDH_CMD_REJ_CNT delta (yellow) | Command-verify step of the executing procedure; repeated or unexplained failure escalates to PROC-003's command-path branch (10 s threshold per HUG-CMD-007). |

## 5. Pass timeline (representative)

The element set is pinned as of v0.9, and the computed contact geometry is in §3.3. The times below remain a representative sequencing template for procedure timing — they were never contact-window values — and are unchanged.

| Time (rel. AOS) | Event | Role / action |
|---|---|---|
| AOS − 15 min | Pass plan review | Ops Planner: window, eclipse timing, planned commands, predicted SoC (PROC-001 pre-pass) |
| AOS − 5 min | Ground system configured | EPS Officer: displays up, limits from dictionary of record; FD go/no-go |
| AOS | Acquisition; frame lock | EPS Officer: CDH_FRAME_CNT advancing; staleness monitor green |
| AOS + 2 min | State-of-health assessment | EPS Officer: EPS panel green, SoC vs. plan; note any yellow to FD |
| AOS + 3 min | Commanding window | FD authorizes; commands per pass plan; verify accept counter + affected telemetry per step |
| LOS − 2 min | Final state check | EPS Officer: mode, SoC, load current, trend snapshot |
| LOS | End of contact | Ops Planner: begin pass report |
| LOS + 30 min | Pass report filed | Ops Planner: report to `docs/pass_reports/` (HUG-OPS-002) |

## 6. Operations organization

One operator wears all roles; the roles are still named, because procedures assign steps to roles, and separating them on paper is what lets more than one person execute them later — including the v0.2 blind-injection tabletop, where the roles split across people.

**Flight Director (FD):** pass go/no-go, command authorization, anomaly declaration, disposition authority during the pass. **EPS Officer:** power and state-of-health monitoring, limit-violation response, command execution and verification. **Ops Planner:** pass plan, timeline keeping, pass and anomaly reports.

## 7. Constraints and assumptions

| ID | Statement |
|---|---|
| CON-01 | Telemetry is receivable and commands sendable only within computed GS-RAVENSROOST contact windows. |
| CON-02 | Onboard autonomy is limited to downward power-mode transitions; every transition to a higher mode is by ground command only (CMD_MODE_SET). |
| CON-03 | Single ground station; no cross-support from other terminals. |
| CON-04 | Payload activation is inhibited below 40% SoC and in SAFE mode; command inhibits are onboard functions, not ground conventions. |
| ASM-01 | For a given scenario file, simulation results are bit-for-bit reproducible; all faults enter by scenario file. |
| ASM-02 | Single-operator availability (evenings/weekends cadence); passes are scheduled, not continuously staffed. |
| ASM-03 | The surrogate reference element set is pinned for the campaign; contact geometry is stable across all campaign passes. |

## 8. Traceability hooks

Needs carry NEED-nn IDs (§2) and constraints CON-nn / ASM-nn IDs (§7); requirements in the requirements document trace to these IDs, and nothing traces to prose. This section exists so the CONOPS participates in the generated traceability matrix (HUG-VER-001).

## 9. Changelog

- **v0.10 (2026-10-12):** Revision per Director ruling D-019: the replay clauses of O4, NEED-04 and §3.2 are struck, kept and marked.
- **v0.9 (2026-07-29):** Build-phase revision per owner ruling D-004. §3.3's representative orbit and contact values replaced with values computed from the pinned surrogate reference element set (CELTEE 1, NORAD 41850) and the pinned GS-RAVENSROOST site coordinates, per HUG-SYS-002 and v0.8 §3.3's own statement that computed values would replace them at build. §5's preamble swept to match, its times unchanged. The material change is the usable contact count, 4–6 per day representative → two to three per day computed; the two daily pass clusters are confirmed by computation. No change to objectives, limits, procedures, the fault set, or ops organization.
- **v0.8 (2026-07-29):** HUG-G001-16 fix revision per Director disposition (accept, G001-16 F-04): the v0.7 revision references corrected from §5 to §3.2 in the status row and the changelog entry below — the two-path recording statement lives in the §3.2 ground-segment description; §5 is the representative pass timeline. Substantive text unchanged; no change to objectives, orbit values, or ops organization.
- **v0.7 (2026-07-29):** HUG-G001-15 fix revision per Director disposition (accept/product, G001-15 F-01): §3.2 ground-segment description separates the two recording paths — native ground-system logs for HUG-SYS-006 replay, the replay package for ODIN (HUG-UI-002/003). No change to objectives, orbit values, or ops organization. *(This entry originally cited §5; corrected to §3.2 at v0.8 per G001-16 F-04.)*
- **v0.6 (2026-07-28):** HUG-G001-11 fix revision per Director disposition (accept/product, G001-11 F-01): §4.2 pass-report description aligned to HUG-OPS-002 v0.11's state-conditional decision evidence — a completed decision step's entry carries the branch-selecting observation; an omitted decision step's entry carries the record that none occurred. No change to objectives, orbit values, or ops organization.
- **v0.5 (2026-07-27):** HUG-G001-07 fix revision per Director disposition (accept/product, G001-07 F-01): §5 pass-close report description aligned to the per-step completion record contract (HUG-OPS-002 v0.8); the actions-only content list is retired everywhere it appeared. No change to objectives, orbit values, or ops organization.
- **v0.4 (2026-07-25):** HUG-G001 fix revision per owner disposition of F-02 (accept/product): O4 narrowed to "detected and annunciated, responded per §4.4"; §4.4 limit-response coverage table added mapping all nine alarmed limit classes to PROC-002/PROC-003, the generic contingency response, or a documented owner acceptance.
- **v0.3 (2026-07-25):** Owner ratified the two [proposed] objective targets: O1 ≥20 SAA transits/week payload-active; O3 ≥90% recovery of collected, time-tagged science frames. Markers removed; document fully dispositioned.
- **v0.2 (2026-07-25):** Full prose draft from Outline v0.1. Framing per owner ratifications in the drafting walkthrough: full-mission objectives O1–O3 ([proposed] targets pending disposition) + ops objective O4; representative orbit/contact values labeled pending the pinned element set; FD / EPS Officer / Ops Planner organization. Consistent with the post-FMEA record: five commands, CMD_MODE_SET ground-commanded recovery (CON-02), PROC-003 as loss-of-telemetry-or-command response.
- **v0.1 (2026-07-24):** Skeleton outline with section guidance.
