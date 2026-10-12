# Demonstration evidence — B6-staleness-halted-counter

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B6-staleness-halted-counter` |
| Obligation | B6 |
| Requirement | HUG-GND-002 |
| Started (UTC) | 2026-08-07T01:31:07Z |
| Finished (UTC) | 2026-08-07T01:39:17Z |
| Result | **PASS** |
| What it demonstrates | Ground-side derived staleness monitor annunciates YELLOW at 10 s and RED at 30 s of no-advance, on a live link, and holds GREEN while frames flow. |

**Outcome:** monitor restarted and observed entering GREEN on live telemetry, then held GREEN for 38 s with the counter advancing (95 -> 496) and no alarm, then annunciated YELLOW and RED in order on a CONNECTED link once generation halted. Every clause re-derived from the archived slice and measurements, not from the live polls.

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/green-entry.txt` | 158 | `b8e96f28268e54082016a51915afa61711a5ddf74367ab6941844073a1637ac3` | CONTROL: the monitor was restarted and observed ENTERING GREEN on live telemetry inside this run's window. A dead, latched or unreadable monitor cannot produce this, so every level that follows is emitted by a monitor known to be reading. |
| `artifacts/green-hold.txt` | 4075 | `ce09e28927c21ac85c7d9dcba45da9b5fbc2615b91d2198348b8cf3b35db4c36` | CONTROL: frames advancing for longer than RED_S with no alarm. A monitor that never reads the counter cannot produce this. |
| `artifacts/operator-log-slice.txt` | 461218 | `4204d835ae301c857ab55551cafc0635275cd5004c22bb9091685bd5bbc9e40d` | THE SOURCE. The ground system's own persisted message log, verbatim and unfiltered. Every claim below is parsed out of this file, so a reader can re-derive the transcript rather than take it on report. |
| `artifacts/annunciations.txt` | 4048 | `f706d8650028bbbf0b0ebdf700da8c1a3a62d53157d718b5fa19d1ff8f8182f3` | the staleness level changes parsed from operator-log-slice.txt |
| `artifacts/halt-fidelity.txt` | 157 | `064cc7be518827d4434fe38c308caac892a62437f55d74a1ad972145d295a4ac` | CONTROL: the alarm fired while the interface was CONNECTED, so this is an absence of frames on a live link — not a link drop, which COSMOS detects by other means. |
| `artifacts/P4_hk_generation_halt.yaml` | 1117 | `473ddadf92fe6b7ff8db766e6e30d42dd607a3e06c772f497a34e979286ee1aa` | the scenario whose fault suppresses generation |
| `artifacts/measurements.txt` | 434 | `33eb609fe046bd6a411e8dcf90321cbc87f5a921a606ae83a04bf729a4183094` | THE VERDICT'S OTHER INPUT. Everything the verdict needs that is not in the log slice, recorded before the verdict is taken so a reader can recompute PASS or FAIL from this directory alone. |

## Observations

- annunciation order: ['GREEN', 'GREEN', 'YELLOW', 'RED']
- GREEN-HOLD held: True; link live at alarm: True
- verdict computed from artifacts/operator-log-slice.txt and artifacts/measurements.txt; live polls paced the run only

## Provenance

These artifacts are committed to the repository. They do not depend on any
ground-system retention setting, on a Docker volume surviving, or on this
machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that
protects the window between a pass ending and its capture — it is not the
mechanism by which this evidence is preserved, and nothing here relies on
it.
