# Demonstration evidence — B7-hazardous-two-step

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B7-hazardous-two-step` |
| Obligation | B7 |
| Requirement | HUG-CMD-001 |
| Started (UTC) | 2026-08-05T03:04:20Z |
| Finished (UTC) | 2026-08-05T03:04:42Z |
| Result | **PASS** |
| What it demonstrates | A hazardous command is refused unconfirmed and accepted only on the resend that follows the refusal, while a non-hazardous command goes through on the same link. |

**Outcome:** unconfirmed hazardous command refused as HazardousError with no effect; the resend after that refusal was accepted and moved EPS_MODE NOMINAL -> SAFE; a non-hazardous command went through unconfirmed on the same link

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/step-one-refusal.json` | 11463 | `ba62aea54272c83d5698c0ba0bf0591f4cb7b250bdb725a7d4f5d099d8356d3f` | STEP ONE: the unconfirmed hazardous command, refused. The error class must be HazardousError — a disconnected interface also refuses, and would read exactly like a block. |
| `artifacts/step-two-acceptance.json` | 406 | `e4be926f3b9b047f82a1431c16392a264a08c6ea84d9dceb725c057a6ca68f8c` | STEP TWO: the resend performed AFTER the refusal above was caught. Called on its own it would demonstrate that a bypass exists, not that a gate does. |
| `artifacts/non-hazardous-control.json` | 427 | `8e0424b68a5501c8dda4e83bbd058928a295b29ea2e75f16b82784e10b972299` | CONTROL: a NON-hazardous command on the same link in the same state is accepted unconfirmed. This is what distinguishes a hazardous gate from a dead uplink. |
| `artifacts/effect.txt` | 262 | `7deeef9e0bfe9e97a189e00f4f3664efc208bac60835fc5e1290faade1467f33` | The effect is a TRANSITION. P1_nominal starts NOMINAL and a mode command to the current mode is a no-op, so a state assertion would be satisfied whether or not anything was blocked. |
| `artifacts/cmd.txt` | 2027 | `acc88a6e996b23c8afba022ec20548cb11b6c626bd03cf92edea9210202ea915` | the generated command definition carrying HAZARDOUS, whose reason text appears verbatim in the refusal above |

## Observations

- control accepted unconfirmed: True
- step one refused as HazardousError: True
- step two accepted after the refusal: True

## Provenance

These artifacts are committed to the repository. They do not depend on any
ground-system retention setting, on a Docker volume surviving, or on this
machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that
protects the window between a pass ending and its capture — it is not the
mechanism by which this evidence is preserved, and nothing here relies on
it.
