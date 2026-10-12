# HUGINN: CubeSat Mission Operations Simulator
## Replay Package Interface Definition, v0.9 (schema 0.9)

| Field | Value |
|---|---|
| Effort prefix | `HUG-` |
| Owner / design authority | Dan Lee-Odinson |
| Date | 2026-07-26 |
| Status | v0.9, HUG-G001-15 fix revision per Director disposition 2026-07-29 (accept/product, G001-15 F-01): the two replay obligations are separated — this package is the recorder-to-ODIN (now VÉ) interface governed by HUG-UI-002/003/004/005/007 alone; ground-system replay is discharged by the ground system's native log recording and playback under HUG-SYS-006, which this document no longer claims. Prior revisions: v0.8 (G001-14 fix: canonical pass_id form), v0.7 (G001-13 fix: filename-stem binding), v0.6 (G001-05 fix: result–reason invariant), v0.5 (G001-04 fixes), v0.4 (G001-03 fix), v0.3 (G001-02 fixes). Before build, the definition moves to `defs/replay_schema.yaml` (HUG-UI-003) and becomes interface v1.0 at build freeze. |
| Drafting assistance | Claude (claude-fable-5). Drafting assistance only; the owner holds design authority and makes all dispositions. |

---

## 1. Purpose and governing requirements

The replay package is the documented interface between the recording side of the campaign and the VÉ mission viewer, so that every executed pass replays in the viewer with neither the simulator nor the ground system running (HUG-UI-002) and recorder and viewer share one definition (HUG-UI-003). Ground-system replay is a SEPARATE obligation — discharged by the ground system's native timestamped log recording and playback (HUG-SYS-006), not by this package (per G001-15 F-01). Governing requirements: HUG-UI-002/003/004/005, HUG-UI-007 (text-only rendering).

## 2. Package form and timebase

One package per executed pass: a single JSON object at `replay/<pass_id>.json`, with exactly four top-level members: `meta`, `track`, `frames`, `events`. The recorder shall refuse to assign a `pass_id` already assigned to an executed pass (per G001-14 F-01) — an identifier is used once, so a later execution can neither overwrite nor alias an earlier package. The viewer refuses (never best-effort renders) a package with an unknown `schema` version, an unmatchable `dict_ref`, or any violation of the §7 conformance contract.

**Timebase (normative, per F-02):** every `t_s` in `track`, `frames`, and `events` is pass-relative seconds on the **ground recorder's monotonic clock** — receive time for telemetry frames, computation time for track samples, occurrence time for events — anchored to UTC by `meta.epoch_utc` (ground time = `epoch_utc + t_s`). CDH_MET is telemetry *content*, never a timebase; a stalled or jumping MET corrupts nothing in the package timeline (FMEA FM-CDH-05). `t_s` values are strictly increasing within each array.

## 3. `meta` — pass identification, epoch, and provenance (object)

| Field | Req. | Type | Semantics |
|---|---|---|---|
| `pass_id` | required | string | Campaign pass identifier in the single cross-platform canonical form: matches `^[a-z0-9][a-z0-9_-]{0,63}$` (lowercase-only, so exactly one spelling exists and comparison is byte-exact — case collision on case-insensitive filesystems is impossible by construction), is not a reserved device basename (`con`, `prn`, `aux`, `nul`, `com1`–`com9`, `lpt1`–`lpt9`), equals the package filename stem exactly, and is never reused across executed passes (§2, §7 — per G001-13 F-06 and G001-14 F-01). |
| `scenario` | required | string | Scenario file identifier that produced the pass. |
| `gs` | required | string | Ground terminal callsign ("GS-RAVENSROOST" in v0.1). |
| `epoch_utc` | required | string | ISO 8601 UTC instant of `t_s = 0` on the recorder clock (§2). |
| `cadence_s` | required | number > 0 | Track sampling interval and nominal telemetry cadence. |
| `aos_s`, `los_s` | required | number | Acquisition / loss of signal, recorder-clock pass-relative; `aos_s < los_s`. |
| `eclipse_exit_s` | optional / null | number | Eclipse exit within the recorded span. **Null or absent when no eclipse boundary occurs in the span** (F-06); a pass with an eclipse entry instead may carry `eclipse_entry_s` under the same rule. |
| `end_s` | required | number | Last recorded time; `end_s ≥ los_s` permitted. |
| `orbit_ref` | required | string | Provenance: the pinned surrogate reference element set (`defs/orbit/`). |
| `dict_ref` | required | object | `{ "version": string, "sha256": hex }` of the `defs/tlm_cmd.yaml` in force at recording; unmatchable → refuse. |
| `schema` | required | string | `"0.9"` for this definition; unknown → refuse. The value always equals the schema number in this document's title — the two are one identity, asserted by the packet consistency checks (per G001-04 F-01). |

## 4. `track` — ground-computed position (array, always present; per F-01)

The ground always knows where the spacecraft should be, whether or not it can hear it: `track` carries position computed from the propagated surrogate reference orbit at exactly one sample per `cadence_s` step over `0 … end_s`, independent of telemetry reception. The orbit view and sky track render exclusively from `track`.

| Field | Type | Semantics |
|---|---|---|
| `t_s` | number | Sample time (§2 timebase). |
| `lat_deg`, `lon_deg`, `alt_km` | number | Geodetic WGS-84 ground track; `lat_deg` ∈ [−90, 90], `lon_deg` ∈ (−180, 180]. |
| `az_deg`, `el_deg` | number | Topocentric look angles from the ground terminal; `az_deg` ∈ [0, 360), 0 = north, clockwise; `el_deg` ∈ [−90, 90], negative below horizon. |
| `ecl` | boolean | **Required on every track sample (per G001-03 F-03).** Ground-computed illumination state from the propagated orbit: `true` = in eclipse, `false` = sunlit. The orbit view's eclipse display renders from this member — deterministic on every pass shape, independent of telemetry reception; ADM_ECLIPSE in received frames is the telemetered counterpart, never the display source. |

**Interpolation (normative, per F-07):** for display between samples, circular quantities (`lon_deg`, `az_deg`) interpolate along the **shortest arc** (179° → −179° crosses the antimeridian through 180°, a 2° path; 359° → 1° crosses north through 0°, a 2° path); non-circular quantities (`lat_deg`, `alt_km`, `el_deg`) interpolate linearly.

## 5. `frames` — received housekeeping telemetry (array; per F-01)

**One entry per housekeeping frame actually received, at its receive `t_s`. Nothing is fabricated: during a telemetry outage — including the exercised generation-halt fault (HUG-EPS-004(c)) — no entries exist, and the gap itself is the record.** The viewer renders last-received values visibly stale per the dictionary staleness thresholds (derived at build time per HUG-UI-005); the reception gap in a P4 replay is the evidence, preserved.

Each frame carries the 16 dictionary points. **Member-name rule (normative, per F-05):** each JSON member name is the dictionary mnemonic **lowercased** (`EPS_BATT_V` → `eps_batt_v`). This transform is bijective over the dictionary's mnemonic set (mnemonics are unique case-insensitively); producer and consumer both apply exactly this transform, and no other mapping exists. Types and units are dictionary-native (voltages V, currents A, SoC %, enums as their dictionary string values, counters as integers); limit evaluation happens in native units against the `dict_ref` dictionary; the viewer derives display values (e.g. watts = current × `eps_bus_v`), never the reverse.

**Payload-rate domain (normative, per G001-04 F-07):** PLD_RATE is dictionary-bounded in every payload state. The rate register always holds a dictionary-valid rate — its initial value lies in the dictionary range, and CMD_PLD_SET_RATE can neither set an out-of-range value nor act while the payload is OFF — so a frame recorded with the payload OFF reports the resting register value, never a sentinel, a null, or an out-of-domain number. The producer shall not emit, and the §7 contract does not admit, any other representation.

## 6. `events` — operator-salient timeline (array of objects)

| Field | Req. | Type | Semantics |
|---|---|---|---|
| `t_s` | required | number | Occurrence time (§2 timebase). |
| `text` | required | string | Display text. **Plain text only: producers shall emit no markup; the viewer shall render `text` through a text-only sink with no markup or code interpretation (HUG-UI-007, per F-15) — markup-significant characters render inert.** |
| `sev` | required | string | `info` \| `warn` \| `crit`. |
| `cmd` | optional | object | Present exactly when the event records a command: `{ "mnemonic": dictionary command mnemonic, "result": "accepted" \| "rejected", "reason": CDH_REJ_REASON value }`. **Result–reason invariant (normative, per G001-05 F-03):** `reason` is event-local — it reports this event's own outcome, never the CDH_REJ_REASON telemetry register's last-reject value: `reason` is `"NONE"` exactly when `result` is `"accepted"`, and a non-NONE dictionary rejection value exactly when `result` is `"rejected"`. |

## 7. Conformance contract (per F-06)

A package violating any rule below is malformed and refused with a stated reason. Requiredness is as marked in §3–§6; members not defined by this schema are forbidden. Value rules: all numbers finite; `cadence_s > 0`; `0 ≤ aos_s < los_s ≤ end_s`; every `t_s` ∈ [0, `end_s`]; `t_s` strictly increasing within each of `track`, `frames`, `events`; `track` has exactly `floor(end_s / cadence_s) + 1` samples on the cadence grid, each carrying `ecl` as a boolean; angular and geodetic ranges per §4; enum members take only their dictionary values; counters are integers in [0, 65535]; `eps_batt_soc` ∈ [0, 100]; `pld_rate` ∈ [0.1, 10] in every frame regardless of `pld_state` (§5: the rate register always holds a dictionary-valid value — per G001-04 F-07). Cross-field: every `events[].cmd.mnemonic` exists in the `dict_ref` dictionary; every `events[].cmd` satisfies the §6 result–reason invariant (`reason` `"NONE"` if and only if `result` `"accepted"`). Identity: `meta.pass_id` matches the canonical lowercase grammar `^[a-z0-9][a-z0-9_-]{0,63}$`, is not a reserved device basename (`con`, `prn`, `aux`, `nul`, `com1`–`com9`, `lpt1`–`lpt9`), and equals the package filename stem exactly — byte-exact, which the lowercase-only grammar makes sufficient on case-insensitive and case-sensitive filesystems alike; a mismatch, an out-of-grammar identifier, or a reserved basename is refused (per G001-13 F-06, G001-14 F-01). With the §2 recorder rule that an identifier is never reused across executed passes, exactly one conforming package can exist per executed pass on every supported platform. The machine-checkable form of this contract is the content of `defs/replay_schema.yaml` at build; this table is the normative drafting surface until then.

## 8. What the package deliberately excludes

Limit values, colorings, staleness thresholds (derived from `defs/tlm_cmd.yaml` at build; bound by `dict_ref`). Command definitions. Executable or markup content of any kind. Any live-data path.

## 9. Provenance

Draft 0.1: embedded seed of ODIN_Prototype_v0.html (2026-07-24), extracted 2026-07-25. v0.2: HUG-G001 fix revision. v0.3: HUG-G001-02 fix revision. The prototype conforms to none of these; the built recorder and viewer conform to `defs/replay_schema.yaml` generated from this definition.

## 10. Changelog

- **v0.9 (2026-07-29):** HUG-G001-15 fix revision per Director disposition (accept/product): **F-01** → the replay obligations are separated: §1 binds this package to the ODIN viewer path alone (HUG-UI-002/003/004/005/007) and states that ground-system replay is discharged by the ground system's native log recording and playback (HUG-SYS-006), not by this package; the interface identity advances to 0.9 under the one-identity rule.
- **v0.8 (2026-07-29):** HUG-G001-14 fix revision per Director disposition (accept/product): **F-01** → `pass_id` becomes a single cross-platform canonical form — lowercase-only grammar `^[a-z0-9][a-z0-9_-]{0,63}$` (case collision impossible by construction; comparison byte-exact), reserved device basenames excluded (§3, §7), and the recorder refuses identifier reuse across executed passes (§2); the interface identity advances to 0.8 under the one-identity rule.
- **v0.7 (2026-07-29):** HUG-G001-13 fix revision per Director disposition (accept/product): **F-06** → `pass_id` bounded to the identifier grammar `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (§3) and bound to the package filename stem by exact equality as a §7 refusal condition, closing the conflicting-identity path; the interface identity advances to 0.7 under the one-identity rule.
- **v0.6 (2026-07-26):** HUG-G001-05 fix revision per Director disposition (accept/product): **F-03** → normative event-local result–reason invariant on command events (`reason` `"NONE"` iff `result` `"accepted"`; a non-NONE dictionary rejection value iff `"rejected"`), stated in §6 and enforced as a §7 cross-field rule; the interface identity advances to 0.6 under the one-identity rule.
- **v0.5 (2026-07-26):** HUG-G001-04 fix revision per Director disposition (accept/product): **F-01** → `meta.schema` discriminator aligned with the interface version and bound to the title identity, with a document/member agreement check added to the packet consistency checks; **F-07** → `pld_rate` dictionary bound made unconditional (§5 payload-rate domain rule; §7) — an OFF frame carries the resting rate register, never an out-of-domain value; **F-06** → status row synchronized with the disposition record: revision authorization stated, draft-awaiting-disposition wording struck.
- **v0.4 (2026-07-26):** HUG-G001-03 fix revision (accept/product): F-03 → required `ecl` illumination boolean on every track sample; orbit-view eclipse display renders from track, deterministic through outages and on boundary-free passes; `eclipse_exit_s`/`eclipse_entry_s` remain optional convenience markers only.
- **v0.3 (2026-07-25):** HUG-G001-02 fix revision, per owner dispositions (accept/product): **F-01** → `track`/`frames` split — track always present from propagation; frames are received telemetry only, gaps preserved as evidence; **F-02** → normative ground-recorder timebase for all `t_s`, CDH_MET demoted to content; **F-05** → normative bijective lowercase member-name transform, "verbatim" claim struck; **F-06** → §7 conformance contract (requiredness, null semantics for `eclipse_exit_s`, ordering, ranges, cross-field rules); **F-07** → shortest-arc interpolation for circular quantities; **F-15** → plain-text-only events with text-only-sink rendering (HUG-UI-007).
- **v0.2 (2026-07-25):** HUG-G001 fix revision (pos block, epoch_utc, dict_ref, dictionary-native frames, crit severity, structured cmd events).
- **v0.1 (2026-07-25):** Extracted from the prototype's embedded draft 0.1 seed.
