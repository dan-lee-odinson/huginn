# HUGINN — maintenance log

Environment and repository maintenance actions that are **not** design decisions.

Owner rulings live in `DECISIONS.md`; the frozen design record lives in `docs/`. Nothing in
this file changes either. Its purpose is narrow: when a later session opens this repo and
finds a commit, a file, or a missing container it did not expect, the explanation is here
rather than looking like tampering or a fault.

Entries are newest first.

---

## 2026-08-31 — Docker disk recovery, pass telemetry committed, one acquisition figure corrected

| Field | Value |
|---|---|
| Date | 2026-08-31 |
| Performed by | Cowork session, at the owner's direction |
| Owner | Dan Lee-Odinson |
| Commits | `bfbe4d8`, `5d7b47e` |
| Design decisions taken | **None.** No ruling was made or implied; no dispositioned value changed |
| Gates | `tools/run_checks.py` — 11/11 suites pass, after the changes |

### 1. Why anything happened at all

The operator's system drive reached 93% full. The cause was Docker Desktop's virtual disk,
`docker_data.vhdx`, at 256.25 GB. HUGINN was not the cause and was not the fix.

Measured with `docker system df -v`:

| | |
|---|---|
| `cosmos-project_*` volumes (the training demo) | **117.5 GB**, of which `cosmos-project_openc3-tsdb-v` alone was 108.6 GB |
| `huginn_*` volumes (all nine) | 3.5 GB |
| All eight openc3 images (every one in use) | 3.7 GB |
| Build cache | 0 |
| Empty space inside the VHDX never returned to Windows | ~131 GB |

The demo stack had been running continuously since late July with a restart policy. Its stock
sample targets (INST, INST2) emit telemetry at 1 Hz, and every packet was written to its
time-series volume. Four weeks of that is where the 108.6 GB came from.

**Outcome: 233.6 GB recovered on the system drive.**

### 2. What changed in the Docker environment — read this before looking for the demo

**The training demo on 2900 no longer exists as a running system.** Its nine containers were
removed by name and its nine `cosmos-project_*` volumes were deleted. This is the fact most
likely to look wrong later, because the record asserts the demo is there:

| Where the record refers to it | Status now |
|---|---|
| `DECISIONS.md` D-007 — "the stock COSMOS demo is cloned and running at localhost:2900" | The clone at `<cosmos-project>` still exists; it is **not running**, and answers nothing on 2900 |
| `defs/ground.yaml` — `reserved_by_training_demo: [2900, 2943]` | **Unchanged and still correct.** The reservation stands; nothing else may bind those host ports |
| `gnd/openc3/compose.yaml` header comment — the two must not collide | **Unchanged and still correct.** HUGINN remains on 2910/2953 |

Nothing in the repository was edited to account for this, and nothing needed to be: the
reservation is a constraint, not an assertion that the demo is up. `tools/run_checks.py` passes
11/11 with the demo absent, so no gate depends on it.

**To restore the demo** (it rebuilds fresh, empty volumes):

```
cd <cosmos-project>
docker compose up -d
```

Its previous four weeks of accumulated sample telemetry is gone and was the point of the
exercise. Its 435 kB Redis configuration was archived first, to
a local backup folder as `cosmos-demo-redis.tar.gz`, in case anything had been configured there
and forgotten. Before deleting, `localhost:2900` was opened and inspected: four interfaces,
all stock (`INST_INT`, `INST2_INT`, `EXAMPLE_INT`, `TEMPLATED_INT`), **no `HUGINN_INT`** — the
D-007 migration to 2910 had left nothing of the owner's behind.

**If the demo is stood up again, shut it down when finished** — `cd <cosmos-project>` then
`docker compose down`. Leaving it running is what consumed a quarter of the disk.

### 3. HUGINN itself — untouched, and verified so

No `huginn_*` volume was deleted, modified, or recreated. `docker compose down` was run in
`gnd/openc3` **without** `-v`, which removes containers and the network and leaves volumes
intact; the command output shows no `Volume ... Removed` line.

Verified after the work, before the irreversible compaction step:

- `HUGINN_INT` present in CmdTlmServer, COSMOS Core 7.2.1
- The full HK dictionary intact in Data Extractor — `EPS_BATT_V`, `EPS_BATT_SOC`, `EPS_SA1_I`,
  `ADM_ECLIPSE`, `PLD_STATE`, `CDH_MET`, `CDH_FRAME_CNT` and the rest
- PASS-1 telemetry extractable for the 2026-08-29 window: 594 packets, CDH_MET 5 → 598

`HUGINN_INT` showing `ATTEMPTING` with `ConnectionRefusedError` on `host.docker.internal:7801`
is the expected state with no simulator running, per `HUGINN_PREFLIGHT_CHECK.md` §3.

Archives of the four substantive HUGINN volumes were taken to an external backup drive before any
deletion, and verified with `gzip -t`:

| File | From volume |
|---|---|
| `huginn-tsdb.tar.gz` | `huginn_openc3-tsdb-v` |
| `huginn-object.tar.gz` | `huginn_openc3-object-v` |
| `huginn-redis.tar.gz` | `huginn_openc3-redis-v` |
| `huginn-gems.tar.gz` | `huginn_openc3-gems-v` |

The backup drive is exFAT. Adequate for `.tar.gz` archives; **not** a place to relocate
the Docker disk image — exFAT has no journaling and no sparse-file support. That option was
considered and rejected for this reason.

### 4. Commit `bfbe4d8` — pass telemetry committed as evidence

`docs/pass_reports/2026-08-03-P1/telemetry_hk.csv`, 594 rows, from COSMOS Data Extractor over
the pass window.

Rationale: the pass report asserts values that, until now, only a running COSMOS instance could
substantiate. With the extract committed beside `report.yaml`, a reviewer can check the report
against the data without standing up the ground segment — which sits closer to the Core-only
reproducibility line the scope rule already draws.

Line-ending note, because `.gitattributes` warns about exactly this: the repo sets
`* text=auto eol=lf` and exempts only `verification/evidence/**`. COSMOS emits this CSV LF-only,
so it committed byte-identical and no digest could be disturbed. Verified with
`git ls-files --eol` returning `i/lf w/lf`. **A future extract that arrives CRLF would need a
`docs/pass_reports/**/*.csv -text` rule before it is committed.**

The CSV is not registered in any evidence manifest and carries no digest. `evidence integrity`
passes unaffected. Whether pass telemetry should become digested evidence under
`verification/` is an open question for the owner, not a decision taken here.

### 5. Commit `5d7b47e` — an acquisition figure corrected, and one bad number left standing

Two prose edits to `docs/pass_reports/2026-08-03-P1/report.yaml`. No `records:` field was
changed and no key was added, so the structure the checkers read is identical: still 15
`event_timeline` entries, still 18 `completion_record` steps, ANOM-001 intact.

**What the CSV resolved.** The record carried acquisition as derived and explicitly flagged as
unobserved — *"first frame received (derived from RECEIVED_COUNT arithmetic, MET ~10; not
directly observed)"*, repeated in S04's note. The recorded telemetry answers it directly:

| | Recorded |
|---|---|
| First received frame | CDH_MET 5, CDH_FRAME_CNT 6, RECEIVED_COUNT 8982, at 18:47:30.799Z |
| Last received frame | CDH_MET 598, CDH_FRAME_CNT 599, RECEIVED_COUNT 9575 |
| Frames received | 594 |
| Frames sent (S16) | 599 |
| Never reached the ground | frames 1–5, MET 0–4, before the interface came up |

Both edits say **supersedes** and retain the old figure and why it was wrong, rather than
overwriting it silently.

`records.first_frame_utc` was deliberately **left at 18:49:06Z**. That field means the earliest
frame *observed live on the console* (MET 100), which is a different fact from when the ground
first received data. Changing it would conflate two things the record separates. If the owner
would rather that structured field track acquisition, that is his ruling to make.

**A bad number is in the repository on purpose.** The message of `bfbe4d8` states *"593 of 599
frames received"*. That is wrong — it is 594. The error was the assistant's: a range counted
inclusively has one more member than its difference, and `9575 − 8982 = 593` omitted the `+ 1`.
Three independent counts in the file agree on 594 (row count, CDH_MET span, RECEIVED_COUNT
span), and CDH_FRAME_CNT 6→599 is a fourth. Git said `595 insertions` — one header plus 594
rows — which was the tell.

Per `HUG-OPS-002`, it was **not** amended away. No force-push. `bfbe4d8` keeps the wrong figure;
`5d7b47e` supersedes it and names it in its own message. A later reader comparing the two
commits is seeing a correction, not a contradiction.

### 6. One thing a later session should not repeat

`git` must not be run against this repo through the Cowork device bridge. Doing so created
`.git/index.lock` and could not remove it — file deletion is blocked on that mount — which
blocked the owner's own commits until he deleted the lock by hand. It also reported nearly
every file as modified, which was an artifact of two gits with different configuration reading
one working tree, not real changes; `git status` from Windows confirmed `working tree clean`
immediately afterward.

That failure mode is already noted in `BUILD_HANDOFF.md` §2 — *"if `git status` shows phantom
modifications at first touch, verify content against HEAD before believing it"*. This is a
second instance of the same thing, from a different cause. **Read files over the bridge; run
git on Windows.**

### 7. Open items for the owner — none actioned

1. **The training demo.** Restore it on 2900, or record that HUGINN no longer keeps a training
   clone. D-007's port separation stands either way.
2. **Pass telemetry as digested evidence.** `telemetry_hk.csv` currently sits outside the
   evidence manifest. Whether extracts belong under `verification/evidence/` with digests, and
   whether extracting the pass window is a step in `HUGINN_PREFLIGHT_CHECK.md`, are unruled.
3. **`records.first_frame_utc`** — see §5.
4. **Pre-existing, unrelated to this work:** `report.yaml` steps S17 and S18 remain at
   `CHANGE-ME`, and `anomalies[0].re_executed_as` has no `pass_id`. The latter is already noted
   in `bfbe4d8`'s parent commit message as *"unfiled pending re-fly id"*.

### 8. Verification a later session can run

```
git log --oneline -4
tools\run_checks.py                                       # expect 11/11
git ls-files --eol docs/pass_reports/2026-08-03-P1/telemetry_hk.csv   # expect i/lf w/lf
docker volume ls                                          # expect nine huginn_* and no cosmos-project_*
cd gnd\openc3 && docker compose up -d                     # then http://localhost:2910
```

---

*Maintenance log opened by the Cowork session at the owner's direction, 2026-08-31. It records
actions taken, not decisions made. Where this file and the design record disagree, the record
wins — and tell the owner a disagreement was found.*
