# Demonstration evidence

**Gate evidence as preserved artifact, not a retention window** — owner ruling D-008.

Every demonstration writes its artifacts into a subdirectory here **as it runs**, with a
`MANIFEST.md` recording what was captured, when, its sha256, and the executed result.
The artifacts are committed to the repository.

```
verification/evidence/
  <demo-id>/
    MANIFEST.md      what was captured, when, digests, PASS or FAIL
    artifacts/       the preserved files themselves
```

## Why not a retention window

The first design set the ground system's `LOG_RETAIN_TIME` to thirty days and treated
that as protecting the B14 pass recording. It does not:

- the logs live in a Docker named volume, and `docker compose down -v` destroys them in
  one keystroke, with no warning and no trace;
- retention **expires**. Evidence valid for thirty days is evidence with a deadline, and
  HUG-G002 has no deadline;
- the artifact stays outside version control, so nothing binds what a reviewer reads to
  what the demonstration produced;
- and the failure is silent — an empty volume months later cannot distinguish a
  demonstration that never ran from one whose evidence aged out.

Capturing at execution time inverts all four. `LOG_RETAIN_TIME` remains set, but only as
a margin covering the seconds between a pass ending and its capture. It is not the
mechanism, and nothing here depends on it.

## What each demonstration owes

| Obligation | Requirement | Demonstration | Artifact it must preserve |
|---|---|---|---|
| **B6** | HUG-GND-002 | Staleness alarm fires on a halted counter | Annunciation transcript showing yellow at 10 s and red at 30 s |
| **B7** | Dictionary §2, FM-CDH-04 | Two-step confirmation on a hazardous command | Transcript of the confirmation flow for each of the three hazardous commands |
| **B10** | HUG-GND-006 | Configuration digest mismatch is a no-go | The displayed version and digest, and the refusal on mismatch |
| **B14** | HUG-SYS-006 | Recorded pass played back with the simulator stopped | **The ground system's native telemetry and command logs**, exported and archived here |

B14's artifact is the one the ruling names explicitly, and it is the one a retention
window would have put most at risk: it is the largest, the most tempting to leave in
place, and the only one that *is* the evidence rather than describing it.

## The empty-directory rule

A demonstration that captures nothing **raises** rather than completing. An evidence
directory with nothing in it is a claim that something was shown with nothing to show,
which is worse than no directory at all — it reads as evidence to anyone skimming.

A demonstration that crashes still writes its manifest, marked FAIL, with whatever it
had captured. A crashed demonstration is a result; burying it would be the worst
outcome available.
