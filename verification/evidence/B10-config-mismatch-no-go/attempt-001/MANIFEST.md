# Demonstration evidence — B10-config-mismatch-no-go

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B10-config-mismatch-no-go` |
| Obligation | B10 |
| Requirement | HUG-GND-006 |
| Started (UTC) | 2026-08-05T03:06:22Z |
| Finished (UTC) | 2026-08-05T03:06:31Z |
| Result | **PASS** |
| What it demonstrates | PROC-001's pre-pass step verifies the loaded configuration and returns GO; a perturbation of what the INSTANCE holds returns NO-GO, with the instance alive throughout. |

**Outcome:** the pre-pass step returned GO on the configuration of record, NO-GO when the instance's own copy was perturbed by one line while the instance stayed alive, and GO again once restored

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/go-leg.md` | 991 | `4f2c03a0957d9996ea3b8d60af63caa63850d06a395157052c193199f359d9e6` | the pre-pass step against the configuration of record |
| `artifacts/nogo-leg.md` | 1433 | `663685f39737ab6cf0e6ad3a109bde8babe50d56e5a8f42854c1a3d1d16fa603` | the same step with the INSTANCE's copy of tlm.txt perturbed by one appended line |
| `artifacts/liveness.txt` | 451 | `4c08e0e1ce8d0a418df5613570a56145890ca9e744e44a4bea90232b295dbdd4` | CONTROL: the instance is alive at the moment it returns NO-GO, so the verdict is a comparison result and not the silence of a dead system. |
| `artifacts/restored-leg.md` | 997 | `b060e427e68b74401b98d35800d616a736ce50ccfcc482cd1ecf1a03ff6043cd` | FM-GND-04 note (e): the mismatch response reloads and re-runs this same step, which must return GO again |

## Observations

- GO leg: True; NO-GO leg returned no-go: True; restored: True
- The no-go is procedural (D-010): the tool arms no command inhibit, and says so in its own output.

## Provenance

These artifacts are committed to the repository. They do not depend on any
ground-system retention setting, on a Docker volume surviving, or on this
machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that
protects the window between a pass ending and its capture — it is not the
mechanism by which this evidence is preserved, and nothing here relies on
it.
