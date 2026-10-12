# Demonstration evidence — B6-staleness-halted-counter-attempt-2026-08-05

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B6-staleness-halted-counter-attempt-2026-08-05` |
| Obligation | B6 |
| Requirement | HUG-GND-002 |
| Started (UTC) | 2026-08-06T12:10:57Z |
| Finished (UTC) | 2026-08-06T12:10:57Z |
| Result | **INSTRUMENT_FAULT** |
| What it demonstrates | Attempt at the B6 demonstration on 2026-08-05. Re-recorded under INSTRUMENT_FAULT after the directory was deleted; the monitor was working and the harness could not read it. |

**Outcome:** the staleness monitor annunciated GREEN -> YELLOW -> RED correctly on a CONNECTED link, verified in the ground system's own log; the harness's collection path returned an empty transcript. B6 is neither discharged nor refuted by this run and is still owed.

> **This run establishes nothing about the subject.** The instrument —
> the collection path this demonstration reads its evidence through —
> failed. The obligation is neither discharged nor refuted here, and
> this record must not be counted as a pass. The demonstration is still
> owed.

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/what-the-harness-reported.txt` | 394 | `7af71b46795834acd62b59e3755e9ba095afdade58b3325a0a9ca0b8289460f1` | the harness's own output. GREEN-HOLD passed; the transcript came back empty. |
| `artifacts/what-the-ground-system-actually-emitted.txt` | 965 | `28f3b34163243d19e5de64c40ae26f335d8be3a33b572ef8e573dfabb365295c` | the subject's actual behaviour, transcribed from the diagnosis. The raw slice was not preserved and is no longer retrievable. |
| `artifacts/why-this-is-not-a-fail.txt` | 1170 | `54234605f9d9717dc9d68b33d4c1e209fbc01e363fe812b009f5adafb9a0a536` | why INSTRUMENT_FAULT rather than FAIL, and why the deletion was wrong |

## Observations

- The monitor's own defect -- importing tlm from openc3.script, which raises 'Token is required' inside a microservice -- was found and fixed during this same attempt. That fix is real and is in the record at 19f05b7; it is not what this fault is about.
- Superseded by whatever the next B6 run records. This entry is the attempt, not the demonstration.

## Provenance

These artifacts are committed to the repository. They do not depend on any
ground-system retention setting, on a Docker volume surviving, or on this
machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that
protects the window between a pass ending and its capture — it is not the
mechanism by which this evidence is preserved, and nothing here relies on
it.
