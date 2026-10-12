# Demonstration evidence — B6-staleness-halted-counter-attempt-2026-08-06

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B6-staleness-halted-counter-attempt-2026-08-06` |
| Obligation | B6 |
| Requirement | HUG-GND-002 |
| Started (UTC) | 2026-08-07T00:25:00Z |
| Finished (UTC) | 2026-08-07T01:33:00Z |
| Result | **INSTRUMENT_FAULT** |
| What it demonstrates | Three B6 attempts on 2026-08-06 that establish nothing: one INSTRUMENT_FAULT where the verdict raced the log flush it reads, and two contaminated by two demonstration runs overlapping on one ground system. |

**Outcome:** run 1 reached its verdict before COSMOS had flushed this run's annunciations to the bucket log, so the archived slice carried none of them; runs 2 and 3 overlapped for roughly two minutes and drove the same simulator and interface, voiding both verdicts. B6 is neither discharged nor refuted by any of the three.

> **This run establishes nothing about the subject.** The instrument —
> the collection path this demonstration reads its evidence through, and
> the isolation the run depends on — failed. The obligation is neither
> discharged nor refuted here, and this record must not be counted as a
> pass. The demonstration is discharged by the clean serial run named
> above, not by this.

**These artifacts are a labelled transcription, not the runs' own evidence.**
The harness overwrites a demonstration's directory on re-run, so each attempt's
artifact set was replaced by the next. What survives is the runner's own output,
verbatim, and the account in `what-happened.txt`. That is weaker than the
artifacts and is what there is — the same shape as the 2026-08-05 attempt, whose
raw slice had rotated away before anyone looked.

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/what-happened.txt` | 4071 | `754cd08f1953c857f9d08ab3bdd63b5ba1c5c8d0e5e3524658bca6be79947e35` | the account of all three runs, what each reported, why none is evidence, and where each stands |
| `artifacts/run-1-runner-output.txt` | 425 | `634ec09d03fd44567177556b412c0d867c5b5c360dd19c741253b877af2aa4f2` | runner output for run 1 — B6 INSTRUMENT_FAULT (summary line printed FAIL), B14 PASS |
| `artifacts/run-2-runner-output.txt` | 425 | `003df99014c2751fa97b3ef2151291ded10e73a50a486277d32c373b41d4485f` | runner output for run 2 — reported B6 PASS and B14 FAIL; both void, it overlapped run 3 |
| `artifacts/run-3-runner-output.txt` | 150 | `a199a44b00e0a8be95d9391be403355913ce7cb9fd50aff0fa5c788c7c45cc2a` | runner output for run 3 — killed during B6 once the overlap was found; no verdict |
