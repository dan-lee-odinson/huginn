# Demonstration evidence — B14-native-log-playback-attempt-2026-08-06

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B14-native-log-playback-attempt-2026-08-06` |
| Obligation | B14 |
| Requirement | HUG-SYS-006 |
| Started (UTC) | 2026-08-07T00:27:00Z |
| Finished (UTC) | 2026-08-07T00:29:33Z |
| Result | **INSTRUMENT_FAULT** |
| What it demonstrates | A B14 attempt on 2026-08-06 reported FAIL because a second, overlapping demonstration run's simulator was holding TCP 7801 open, answering a control this demonstration depends on. |

**Outcome:** the simulator-off control failed against another run's simulator, not against B14's subject. The playback was never fairly attempted. B14 is neither discharged nor refuted by this run.

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
| `artifacts/what-happened.txt` | 2147 | `82b233f85cc51a9022b2587590f6d76b529cbc36f358c95f8f6f8e1805105805` | why this FAIL is not a statement about B14, and what was separately true of the run |
| `artifacts/run-2-runner-output.txt` | 425 | `003df99014c2751fa97b3ef2151291ded10e73a50a486277d32c373b41d4485f` | runner output for the run — B6 PASS, B14 FAIL; both void |
