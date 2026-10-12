# Open findings

Things established as true that are **not yet dispositioned**. Not a backlog: each entry
is a claim with evidence, waiting on an owner ruling or on work that is scoped but not
done. Entries leave here by being ruled on (into `DECISIONS.md`) or by being closed with
the evidence that closes them.

---

## OF-001 — the configuration digest does not bind the generated ground configuration

**Status:** RULED at **D-010** (2026-08-04) and implemented.

**Claim.** `CONFIG_ID.txt` carries `SOURCE_SHA256`, the sha256 of `defs/tlm_cmd.yaml`.
HUG-GND-006 (B10) has pass setup verify *the loaded configuration* against the dictionary
of record, and that comparison is sound for everything the dictionary determines. But the
**generated ground configuration is not determined by the dictionary alone** — it is
determined by the dictionary *and by `tools/gen_openc3_config.py`*. A generator change
alters `plugin.txt` while `defs/tlm_cmd.yaml`, and therefore the digest, stays byte-identical.

**This was not hypothetical.** It happened during this build, in the window between two
commits:

| | Repository | Loaded in the instance | Digest |
|---|---|---|---|
| `plugin.txt` INTERFACE | `… 0x4855 None False` | `… 0x4855 None True` | **identical** |

The `fill_fields` fix changed the generated plugin and could not change the digest,
because it changed the generator rather than the dictionary. A B10 pass-setup check run
in that window would have compared the digest, found agreement, and returned **GO** while
the loaded ground configuration differed from the repository in a way that made every
hazardous command untransmittable.

Two further facts sharpen it:

- The plugin **gem version is also derived from the dictionary version** (`0.5`), so the
  two differing plugins carried the same version *and* the same digest. Version and digest
  agreed; the configurations did not.
- COSMOS **skips reinstalling a gem whose version it already holds**. The corrected plugin
  did not reach the instance until `OPENC3_FORCE_INSTALL=1` was set, and the stored
  `plugin_txt_lines` read the old value until then. So the identity that would have caught
  the drift is the same identity that caused the drift to persist.

**Why this is not simply a bug to fix.** B10 as specified compares the loaded
configuration against *the dictionary of record*, and the digest does exactly that. The
gap is that nothing carries an identity for the **generated** ground configuration — the
artifact the ground system actually executes. Closing it means either widening what the
digest covers or adding a second identity, and both change what HUG-GND-006's pass-setup
step asserts. That is a design decision, not a build decision.

**Options, for the ruling:**

1. **Digest the generated plugin as well.** `CONFIG_ID.txt` gains a second value over the
   generated artifacts. Pass setup compares both. Costs: the digest changes on every
   generator change, including cosmetic ones, and every such change becomes a no-go until
   the record is resynchronised.
2. **Digest the generator alongside the source.** Binds the pair that actually determines
   the output. Same currency problem, one layer up.
3. **Leave B10 as specified and add a separate loaded-vs-repository check**, in the shape
   of `tools/ground_targets.py`: not part of the digest comparison, but a failing check at
   pass setup all the same.
4. **Rule it out of scope for v0.1**, recording that the digest binds the dictionary and
   nothing claims to bind the generated configuration.

**Recommendation: (3).** It closes the hole without making the digest's currency condition
harder to satisfy, it matches a pattern already in the build and already red-cased, and it
keeps B10's sentence exactly as HUG-GND-006 states it. (1) and (2) make every generator
touch a gate event, which is the failure mode that produced the stale-baseline findings
earlier in this build.

**Evidence.** `git show 67e2320` (the fill_fields fix and its regression cases); the
stored `plugin_txt_lines` before and after `OPENC3_FORCE_INSTALL=1`; check G9
(`tools/checkers/defs_generation.py`), which is green throughout and correctly so — it
asserts the digest is the digest of its source, which was never in question.

**Found by:** adversarial specification review of the B10 demonstration, which flagged
the divergence as live in the instance at the time it ran.

---

## OF-002 — the staleness monitor cannot tell "watching, nothing advanced" from "never able to look"

**Status:** CLOSED as fixed under **D-019** (2026-10-12). The monitor tells "never read" apart from "not advancing" (evidence chain EX-2), and B6 passed on attempt-003.

`gnd/openc3/plugins/openc3-cosmos-huginn/microservices/STALENESS/frame_staleness.py`:

```python
try:
    value = tlm(f"{TARGET} {PACKET} {COUNTER}")
except Exception:
    value = last_value          # "the clock keeps running"
```

The swallow is deliberate and right for a *transient* read failure — during the outage
this monitor exists to detect, reads do fail, and the clock must keep running. It is
wrong for a *permanent* one. If `tlm()` throws on every iteration (auth failure, renamed
packet, plugin absent, target never loaded), `value` and `last_value` are both `None`
forever, `value != last_value` is never true, `last_change` is never updated, and
`stale_s` measures time since **process start**.

The monitor then annunciates GREEN → YELLOW at 10 s → RED at 30 s with textbook spacing,
on a system with no spacecraft, no link and no halted counter. **That is precisely the
transcript B6 is supposed to prove**, produced by a monitor that has never once read
CDH_FRAME_CNT.

A B6 demonstration therefore cannot rest on the annunciation transcript alone. It needs a
GREEN-HOLD limb: a sustained interval, longer than `RED_S`, with frames flowing and the
monitor demonstrably staying GREEN — which a dead monitor cannot do, because its clock
starts at process start and passes RED_S regardless.

**Fix direction:** the monitor should distinguish *never read* from *read and not
advancing*, and say so — a first successful read should be a precondition for
annunciating staleness at all, with the pre-first-read condition annunciated as its own
distinct state rather than silently sharing the vocabulary of a real halt.

---

## OF-003 — B10 has no enforcement point

**Status:** RULED at **D-010** (2026-08-04) and implemented.

`CONFIG_ID.txt` is generated and G9 proves the digest is the digest of its source. But
nothing in `gnd/` performs the pass-setup *comparison*, and nothing blocks commanding on a
mismatch. The ground segment contains eight files; none is a pass-setup screen, a Script
Runner procedure, or a check that gates the uplink.

A demonstration in which the verification step itself notices the mismatch and declines to
send is the step under test grading its own paper — it shows that a script can compare two
strings, not that the ground segment refuses a no-go configuration. The enforcement point
has to be named as a design decision and built before B10 can be demonstrated at all.
Related to and distinct from [OF-001](#of-001), which is about what the digest *covers*;
this is about nothing *acting* on it.

---

## OF-004 — scenario-scripted commands contaminate command-path assertions

**Status:** CLOSED as fixed under **D-019** (2026-10-12). B7's demonstration checks the refusal's error type and asserts the NOMINAL → SAFE transition.

Every scenario in `sim/scenarios/` scripts its own commands, applied through
`cdh.receive()` inside `step()`. `CDH_CMD_ACC_CNT` therefore advances on its own schedule,
and "the accepted counter advanced after I sent a command" proves nothing on its own.

Relatedly, effects must be asserted as **transitions, not states**: `P1_nominal` starts in
`NOMINAL`, and `command_mode('NOMINAL')` from `NOMINAL` is a no-op, so "EPS_MODE unchanged"
after a blocked command is satisfied whether or not anything was blocked.

*(The uplink verification already performed is not affected by this: `NOMINAL → SAFE` is a
real transition that no P1 scenario command produces, and `txbytes=2` is measured on the
interface. But the counter delta alone would not have carried it.)*

---

## OF-005 — "playback" may never touch the logs

**Status:** CLOSED as fixed under **D-019** (2026-10-12). B14's verdict requires proof that playback read the native log (evidence chain EX-4).

COSMOS 7 chooses its historical-streaming source at runtime: decommutated items come from
QuestDB, and raw packets switch to a Valkey stream when the requested start time is recent
enough to still be in memory. A playback that returns correct values is therefore not
evidence that the **native log files** were read — which is the whole of what B14 claims.

Two further traps recorded with it: decoding the `.bin.gz` with this repository's own
`FrameCodec` proves the repo can read its own format and says nothing about the ground
system; and a real pass spans more than one log object (`TLM_LOG_CYCLE_TIME` is 300 s while
contacts run to 7.5 min), so completeness checked on a single file can be satisfied while
the gap sits in its sibling.

---

*OF-002 through OF-005 were produced by adversarial review of the four demonstration
specifications. All four specifications were judged hollow as written; these are the
findings that survived verification against the repository.*

---

## OF-006 — the staleness monitor can latch silently when its reads stop working

**Status:** RULED at **D-012** (2026-08-06) and implemented. Retained here until the
queued FMEA row lands in the HUG-G002 revision set.

OF-002 gave the monitor a `NO_READ` state so a process that has **never** read the counter
cannot annunciate staleness. It does not cover a process that read successfully and then
**stopped being able to**.

There, `last_change` is already set, so the except-branch keeps the clock running,
staleness accrues to RED, RED is annunciated once, and — logging only on level *change* —
it never speaks again. It cannot recover either: every later read fails, so no value
change is ever seen.

**Measured.** A 23-hour-old monitor sat silent for over an hour with live telemetry
flowing and the counter advancing. Its loop was running (status count advancing ~1/s,
state RUNNING, no error) and `tlm()` worked from a shell in the same container. A freshly
started process on the same telemetry annunciated GREEN within four seconds.

**Why it matters.** "In RED" and "died some time ago" produce identical output — silence.
That is the ambiguity OF-002 was raised to remove, one step further along. B6 now restarts
the monitor and requires it to be seen *entering* GREEN in-window, so the levels that
follow come from a monitor known to be reading. That makes the demonstration sound; it
does not fix the monitor.

**Fix direction:** annunciate a distinct state when reads begin failing after having
succeeded. A ground-segment fault and a spacecraft fault are different conditions with
different responses, and they must not share a vocabulary.

**Ruled and implemented (D-012).** `READ_FAULT` is annunciated when reads fail after a
prior success; no staleness level or number is emitted while read-faulted, because both
are claims about the spacecraft; `READ_RECOVERED` annunciates the read path coming back
and the level is restated against reads known to be working. The staleness clock is not
reset by the outage, so a counter that genuinely did not advance across it is still
caught on recovery. Both polarities are red-cased in `tests/test_staleness_monitor.py`
and each was verified to fail with its guard removed.

**QUEUED FOR THE HUG-G002 REVISION SET (D-012).** An FMEA row for *silent monitor
read-path failure*: the ground-segment failure mode in which a monitor that has read
successfully stops being able to and, before this fix, produced output identical to a
monitor that had died. Detection is now the `READ_FAULT` annunciation; the row is owed
against the FMEA in the revision set, not against this build.

---

## OF-007 — the operator container's Docker log is not a durable evidence source

**Status:** RULED at **D-012** (2026-08-06), accepted as implemented. COSMOS's
persisted bucket log is the evidence source of record for B6.

`compose.yaml` caps container logs at `max-size: 10m`, `max-file: 3`. A demonstration
driving frames at 10-20x fills that in minutes, so a run's own annunciations rotate out
from under `docker compose logs` **while the run is still in progress**.

**Measured.** An end-of-run fetch returned a slice whose newest entry predated the start
of the run, having lost the GREEN, YELLOW and RED emitted in between. The same events were
in COSMOS's persisted bucket log throughout.

Separately, on this Docker build an absolute RFC3339 `--since` marker close to *now*
returns an empty slice while the relative form over the same span returns tens of
kilobytes — measured side by side, same format, same second.

B6 now reads the persisted bucket log. Any demonstration reading `docker compose logs` for
evidence inherits both problems.


---

## OF-008 — both of B14's negative controls were satisfied by a SyntaxError

**Status:** CLOSED as fixed under **D-019** (2026-10-12). Found and fixed while running
B14 under D-012; the fix is covered by evidence chain EX-4.

**Claim.** B14's two negative controls built their `python -c` body by concatenating
semicolon-joined statements with a compound one:

```
"from openc3.logs.packet_log_reader import PacketLogReader;" "r=PacketLogReader();" "try:\n" ...
```

That is a `SyntaxError` — a compound statement cannot follow simple ones joined by `;`.
Neither control ever ran.

**Why it was invisible.** Both were scored on the **absence** of a `PACKETS n` line:

```python
control_played = re.search(r"PACKETS (\d+)", control.stdout)
control_count = int(control_played.group(1)) if control_played else 0
file_bound = control_count == 0
```

A script that never compiles prints no `PACKETS` line, so `file_bound` was `True` — for
the same reason a working reader refusing a bad path would be `True`. **The OF-005
file-bound control, which exists specifically to prove the playback is not
database-backed, could not have failed.**

**Measured.** The captured artifact from the first B14 run under D-012:

```
stderr:
  File "<string>", line 1
    from ... import PacketLogReader;r=PacketLogReader();import sys;try:
                                                                   ^^^
SyntaxError: invalid syntax

packets returned: 0 (must be 0)
```

**This is the D-011 shape at a different site.** An absence produced by broken collection
was read as a statement about the subject. B14 was one clause away from PASSING on it.

**Fixed.** One `_read_log_script()` builder, newline-separated, used by the real read and
by both controls so they cannot drift; and both controls now require the reader to be seen
**REFUSING** — `REFUSED FileNotFoundError` for the bad path, `REFUSED ValueError OpenC3
file header not found` for the compressed object — rather than merely seen saying nothing.

**Owed:** a ruling on whether "scored on an absence" should be swept for across the other
demonstrations' controls. B7's and B10's controls were not audited for this shape.

---

## OF-009 — every evidence digest had stopped verifying, and nothing recomputed them

**Status:** CLOSED as fixed under **D-019** (2026-10-12). Found and fixed while migrating
attempts to the append-only layout; the fix is covered by evidence chain EX-5.

**Claim.** Each evidence manifest carries a sha256 per artifact so that what the gate reads
can be shown to be what the demonstration produced (D-008). On a fresh clone of the
repository at that point, **not one of those digests would have verified.**

Evidence captured on Windows can hold CRLF. `.gitattributes` set `* text=auto eol=lf` for
the whole repository, so git stored a line-ending-translated copy of every text artifact
while the manifest recorded the digest of the untranslated bytes. Measured on one captured
runner transcript:

| | sha256 |
|---|---|
| working tree, as captured and digested | `634ec09d…` |
| as git would check it out | `43b38324…` |

**Why it was invisible.** Nothing ever recomputed them. The digests were written at capture
time and read by nobody: a reviewer would have had to compute one by hand to notice, and
the evidence looked complete and tamper-evident in exactly the way it was not. A digest
nobody recomputes is decoration — it has the appearance of integrity and none of the
property.

**How it surfaced.** Not by inspection. `git` printed `warning: CRLF will be replaced by
LF` while committing the attempt migration, which is a routine message that is almost
always noise. It was worth one command to check, and the check disagreed with the manifest.

**Fixed at `ff40255`:**

| Change | Effect |
|---|---|
| `verification/evidence/** -text` in `.gitattributes` | git never translates a captured artifact; index and working tree agree |
| `tools/verify_evidence.py`, in the gate | every manifest digest is recomputed on every run |

The check refuses its own vacuous passes: an absent evidence root, a root with no
manifests, and a manifest listing no artifacts are each a failure rather than "all digests
verify" over an empty set. Eleven red/green cases; the one that matters is the
line-ending case — same text, different bytes — because a check comparing content rather
than bytes would pass it and miss precisely what happened.

**What it says about the discipline.** Three separate rulings now exist because evidence
kept failing in ways that looked like success: D-008 (evidence must not expire), D-011
(a failed collection is not a verdict about the subject), and the append-only attempt
layout (a successor must not erase its predecessor). This is a fourth shape of the same
thing — evidence that is present, readable, and no longer what it claims to be — and it is
the first one that would have been invisible to a reader rather than merely misleading.


---

## OF-010 — the validator refused records the procedures themselves ordered

**Status: found and fixed.** Recorded because it shipped at `bba2e0a`, not because it is
still live. Same precedent as OF-008.

Found by adversarially re-reading Phase 5 against the frozen record after it was
committed. Two cases where PROC-001 instructs the operator to do something and
`tools/pass_report.py` would then refuse the truthful record of having done it.

**(a) In-pass re-execution.** PROC-001-S03's no-go branch says to reload the generated
configuration and re-run S02 (FM-GND-04 note (e)); PROC-003's ground-path branch says the
same; S12's `ARG_RANGE` branch says to correct the argument and re-send. HUG-OPS-002
allows each step exactly one entry, and the validator enforced it — so a pass that
followed those instructions had nowhere to put the attempt that failed. The operator's
only conforming option was to record the successful attempt and drop the other, making a
pass that went no-go first read as one that went right the first time.

**(b) Multi-procedure passes.** PROC-001-S05's not-acquired branch says "Execute
PROC-003" and S07's limit-response branch says "Execute PROC-002". The report had a single
`procedure:` field, so contingency work had no place in the record at all: either lose it,
or file a second report claiming to be a separate pass that never occurred.

**Fixed:**

| Change | Effect |
|---|---|
| `repeatable: true` on PROC-001-S02/S10/S11/S12 | the procedure declares which steps it orders re-run |
| `attempts:` / `earlier_attempts:` on the entry | one entry still, holding every attempt; each earlier one must name its outcome |
| `invoked_procedures:` on the report | a contingency procedure carries a full completion record of its own |
| `_validate_invoked` | the invocation must trace to a branch that calls that procedure, on a step that recorded that branch |
| rendered into `procedures/PROC-00N.md` | the operator reading the procedure sees the allowance, not just the validator |

Both fixes are red-cased (13 new cases). The invoked record is held to the same rules as
the governing one — a missing step in PROC-002's record is the same omission finding it
would be in PROC-001's — and the traceability case is the one that matters: a report that
says PROC-002 ran *and* says the decision that would have ordered it went the other way is
refused, because otherwise "we also ran PROC-002" is an assertion with nothing behind it.

**What it says about the discipline.** The B13 suite was green at 63 cases against a
contract that could not record two things the procedures explicitly command. Every case
was built from the procedure definition, which is what kept them from going stale — but
they were all built from the *steps*, and both defects lived in the *branches*, in the
`then:` text telling the operator what to do next. A generated fixture inherits the
blind spot of the field it generates from. What found these was reading the branch
instructions as obligations on the record, which is the reading the operator will take.

---

## OF-011 — a red case that a crash satisfied, inside the machinery that certifies every other check

**Status: found and fixed.** Recorded because it shipped. Found while building Phase 6's
observation layer, which records `passed_by_exception` per mutation case for this reason.

`defs_generation:G11.m1` moves an FMEA severity rating outside the Sec. 3 definitions and
requires G11 to turn red. It did — by raising `KeyError: 'V'`. G11's own detection had
already found the violation and appended it to `problems`; execution then continued into
the R2 partition, whose `risk_of()` lookup cannot be asked about a rating the criticality
matrix does not define. The self-test's red criterion was "the check did not return true",
and a check that raises does not return true, so crash and detection scored identically.

This is OF-008's shape one level down: a control satisfied for a reason unrelated to what
it claimed to test, sitting inside the self-test apparatus that licenses every other
check's passing result under HUG-VER-002.

**Fixed:** `g11_fmea_structure` returns its finding before deriving risk it cannot derive.
`G11.m1` is now CAUGHT by the check's own report. Both checkers' `iter_selftest_cases`
record `raised` per case, and `tools/verification_run.py` carries it through as
`passed_by_exception`, so the verification report counts how many red cases rest on an
exception. The count is now zero and a second instance cannot arrive quietly.

---

## OF-012 — B14's demonstration verdict is the one no executed case re-establishes

**Status: CLOSED under D-013 item 1.** Surfaced by ITEM-5 (`EX-4`), which reported it on
every run until the covering cases existed. `EX-4` now carries 8 covering cases, 8
executed, 6 of them red, and the chain reports no finding — flipped by regenerating
against the run record, never by editing the chain.

B6 has `b6_verdict` and B11 has `b11_verdict`, each re-computing its demonstration's
verdict from the archived bytes under executed red and green cases — the discipline ruled
at D-012, that a verdict be computable from the archived evidence alone. There is no
`b14_verdict` and no `tests/test_b14_verdict.py`.

So OF-008's direction claim — two negative controls scored on an absence, both satisfied
by a `SyntaxError` that meant neither ever compiled — has **no covering case**. The repair
landed in `tools/demonstrate.py` and the B14 attempt-002 evidence records it; what does
not exist is an executed case that would fail if the repair were reverted. The evidence
chain says so in the table rather than omitting the row.

**How it was closed.** `b14_verdict()` in `tools/demonstrate.py` re-derives B14 from the
archived bytes alone, and `tests/test_b14_verdict.py` drives it at both polarities off
disk. Every control it scores must show the reader ACTUALLY RAN — a `REFUSED
<ExceptionType>` line that only an executed reader produces. The zero-count line the
original controls were scored on is still required and is never sufficient alone.

The two cases that carry the claim strip only the evidence of execution and assert the
absence clause still holds, so they pass against the verdict B14 shipped with and fail
against this one. That is what makes them a red case for OF-008's defect rather than for
a neighbour of it.

**Residual, recorded rather than closed:** the `SyntaxError` transcript that diagnosed
OF-008 exists only as prose in this register. The artifact was overwritten before the
evidence harness was capturing, so the defect itself is described but not archived.

---

## OF-013 — requirements the matrix reports as not established

**Status: PARTLY CLOSED under D-013 items 2 and 3.** Six of the eight rows closed; the two
that remain close when the campaign record tests land (D-019). These are the standing findings
`verification/TRACEABILITY.md` carries, listed here so the register and the generated
matrix cannot drift apart about what is outstanding.

| Condition | Requirement | Status | Why |
|---|---|---|---|
| F2 | `HUG-OPS-003` | **OPEN** | The campaign was flown, 2026-08-29 to 2026-10-11; no executed case yet ties the pass records to this requirement. Closes when the campaign record tests land (D-019). |
| F2 | `HUG-OPS-004` | **OPEN** | AR-001 to AR-003 are filed; no executed case yet checks them against this requirement. Closes when the campaign record tests land (D-019). |
| F2 | `HUG-GND-004` | CLOSED | B14 demonstrates timestamped logging and export; its frozen manifest declared only `HUG-SYS-006`. Corrected by `ERR-001` and attributed by an executed case (`tests/test_b14_verdict.py::TestTheArchivedEvidencePasses`), with the archive untouched. |
| F6 | `HUG-SYS-001` | CLOSED | `tests/test_model_red_cases.py::TestTheTwoStringsCatchTheirViolation` |
| F6 | `HUG-EPS-001` | CLOSED | `TestEnergyBalanceCatchesItsViolation` |
| F6 | `HUG-EPS-002` | CLOSED | `TestEclipseGenerationCatchesItsViolation` |
| F6 | `HUG-CMD-004` | CLOSED | `TestSafeEntryCatchesItsViolation` (refusal, and acceptance that never reaches SAFE) |
| F6 | `HUG-CMD-005` | CLOSED | `TestTheResetEpochCatchesItsViolation` (a reset that does not zero, and one that zeroes without its own accept) |

**How the F6 five were closed, and why it is not five new assertions.** Each property is
a single predicate. The green case runs it against the real model and requires silence;
the red case runs *the same predicate* against a subclassed model with that one invariant
broken and requires it to speak. A red case written as an independent assertion would
demonstrate that *some* check catches the mutation, not that the check guarding the
requirement does — which is the whole content of HUG-VER-002.

**Caught by detection, never by exception.** `probe()` reports three outcomes —
`DETECTED`, `SILENT`, `INSTRUMENT_FAULT` — and every red case asserts `DETECTED`
specifically. Two outcomes would have let a model that merely explodes score as a working
red case, which is exactly how `G11.m1` certified a check that never reported the
violation it had already found (`OF-011`). `TestAMutationThatCrashesIsNotAPass` asserts
that distinction rather than trusting it.

---

## OF-014 — the procedures were written for someone who already knew the program

**Status: FIXED at Phase 7R.** Raised by the Director at first execution. PROC-001 halted
at S01: the campaign never started.

### The finding, verbatim

> "The procedures assume a working knowledge of the program, which I do not possess. For
> example: [PROC-001-S01 and S02 as generated]. This does not tell me what app I need to
> open, where to find the pass plan (is that the same as the campaign plan?), what /
> where the records are located, how do I 'bring up the ground system' and how do I 'run
> the pre-pass configuration verification'."

### What was wrong

Every step named an ACTION and no step named the MECHANISM that performs it. "Review the
pass plan" named no file. "Bring up the ground system" named no command. Steps listed
`Records:` fields and never said where a recorded value is written or in what form. The
one thing every step assumed - that the operator knows the ground system is a web page at
a particular address - was stated in `gnd/RUNBOOK.md` and referenced from no procedure.

Nothing was missing from the BUILD. Every command the operator needed already existed and
worked. What was missing was any path from a step to the thing that performs it, and the
audience the record names for these procedures is a human without working knowledge of the
codebase. Measured against that audience the procedures were not executable, which makes
them not procedures.

The Director's parenthesis - *is that the same as the campaign plan?* - is the sharpest
part of the finding. It is the same document, and nothing said so.

### Why operator readiness passed the day before

Readiness was verified at `887a813` and reported as confirmed. That check ran the tools,
regenerated the procedure documents, and validated the worked example. Every one of those
is a property of the BUILD: it establishes that the machinery works. **None of them could
fail on a procedure that regenerates perfectly and instructs nobody.** The check and the
defect were about different subjects, and the report said "operator readiness confirmed"
on the strength of the wrong one.

This is a direction claim, and it belongs to the same family the evidence chain indexes:
*because the tools run and the documents regenerate, the operator can execute the
procedure.* The premise was true and the conclusion was false.

### The check that can now fail

`G17`, in `tools/checkers/defs_generation.py`, asks the question the readiness check could
not: does a step name a mechanism? It requires, per step, that the source declare

- something to **open** or a command to **run** - a way in;
- what the operator should **see when it worked**, so success is observable;
- for every `records:` field, **where it is written and in what form**;
- every repository path named actually present in the repository;
- every `<placeholder>` accompanied by a rule for constructing it;

and, once for the procedure set, the operator context every step assumes: the console, the
terminal, the pass plan, the pass identifier, and where records go.

Five red cases and one green, in the gate. G17 fails when a step is unexecutable, which is
a different question from whether the generator works.

### A defect inside the fix, caught by its own green case

G17's five red cases initially all passed **for the wrong reason**. The self-test stages
only the files this checker reads, so under a mutation the staged tree has no `tools/`,
`campaign/` or `gnd/` in it - and the path-existence clause reported every path in every
step missing, in the baseline as well as in each mutation. All five reds were caught by
the staging, not by their mutations.

The GREEN case is what exposed it: it false-flagged, which is the only signal that
distinguishes "the check fires on this mutation" from "the check fires on everything".
Fixed by resolving paths against the real repository root rather than against the moving
one. Recorded because it is OF-008's shape occurring inside the remediation for OF-014,
within the same hour - and because it is the clearest argument in this repository for why
a green case is not a formality.

---

## OF-015 — the operator documents were written for two audiences at once

**Status: FIXED at Phase 7R2.** Raised by the Director on reviewing the documents
remediated for [OF-014](#of-014), before any pass was attempted.

**A NEW FINDING, NOT AN EXTENSION OF OF-014, AND THE DISTINCTION MATTERS.** OF-014 was an
ABSENCE: steps named actions and no mechanisms, and `G17` now fails when a step has no way
in. This is a PRESENCE: the mechanisms are named, and the documents also carry material
addressed to somebody else. `G17` passes on every one of these findings. Most of the
contamination was written BY the remediation for OF-014 — fixing the absence introduced
the presence, in the same edit, which is why it is recorded as its own entry rather than
folded into the one whose fix caused it.

### The findings, verbatim

> * "Before you start" — The phrase "reached from the top menu bar" is inaccurate - it is
>   a menu sidebar
> * The Pass Plan — Remove the comment "and the Director's question was the correct one to
>   ask." this is a procedure document that is being designed for external use
> * The Pass Identifier — This phrase doesn't make sense: "It is your choice of nothing -
>   it is read off the plan - and the same string is used for the pass_setup call, the
>   report directory name, and the report's own pass_id field."
> * Where recorded values go — This needs to be written as numbered steps, starting with
>   1. Open terminal / powershell… etc
> * Checking your record — Is this command string all one command, or is it two?
> * Write it down: — This section is unintelligible

and against the campaign plan: remove the Director-specific language, remove the
build-gate references from the arithmetic section and from the boundary note, and remove
the narrated "Findings — None" paragraph.

### What was wrong, by class

1. **Audience contamination.** Who ruled what and when, which reading was rejected, that a
   boundary was "surfaced rather than settled silently", the reader named in the third
   person. None of it false; all of it addressed to the build rather than to the console.
2. **Factual inaccuracy.** The console navigation is a **menu sidebar on the left**, not a
   top menu bar. Written from memory of a product not looked at.
3. **Unusable form.** A sentence that did not parse; YAML grammar quoted inline and the
   operator left to construct the shape; a multi-line procedure given as prose; a wrapped
   command that could be read as two.

### The check that can now fail

`G18` sweeps the five operator products — the three procedures, the campaign plan and the
runbook — for register entries, authority narration and build-gate history. The rule it
enforces, as the owner stated it: an operator document may CITE a ruling identifier at
most, never discuss it. `(D-010)` passes; "owner ruling D-010 made it a tool" does not.
Five red cases and one green — the green being a bare citation, which the rule permits.

**On first run it found 16 leaks in 5 documents**, including four the manual review had
not reached: an `OF-002` reference inside a PROC-001 step, an `OF-006` reference inside a
PROC-003 branch, and two gate references in the runbook.

### What has no check, stated rather than implied

`G18` reads for audience, not for truth. **Nothing in this repository can catch "top menu
bar" when the navigation is a sidebar** — a description can be perfectly free of build
language and still describe a product nobody looked at. The console was confirmed running
and reachable during this remediation, but its navigation sits behind a password login,
and entering one is not something the build does. The correction therefore rests on the
Director's direct observation of the running console, which is a better source than the
build's memory and is recorded here as the source. The mitigation adopted is narrower
claims: the description now names the sidebar and the three tools used, and describes no
chrome that was not observed.

---

## OF-016 — every campaign anomaly pass injects its fault after its assigned contact has closed

**Status:** RULED at **D-015** (2026-09-13) and implemented — two-contact
passes admitted; simulator start offset added.

**Claim.** The campaign plan assigns the three anomaly passes to contacts of 430 s. Each
scenario injects its fault well after 430 s of mission elapsed time. `tools/serve_sim.py`
began every run at MET 0 and provided no way to open a contact later in a mission, so an
operator flying the assigned contact from acquisition observed only MET 0 through 430 and
**the fault never occurred inside the pass.**

| Pass | Contact | Window | Fault | Onset | Beyond the contact by |
|---|---|---|---|---|---|
| PASS-2 | 16 | 430 s | `array_string_zero` (string 1) | MET 600 | 170 s |
| PASS-3 | 9 | 430 s | `stuck_load` | MET 900 | 470 s |
| PASS-4 | 2 | 430 s | `hk_generation_halt` | MET 1200 | 770 s |

**No reassignment inside the plan closes this.** The longest contact in the computed week
is contact 13 at 450 s, shorter than the earliest fault onset.

**Two further consequences of the same mismatch.**

- All three scenarios script `CMD_PLD_SET_STATE ON` at **MET 120**, inside every contact.
  That is the pre-emption recorded as ANOM-001 on `2026-08-03-P1`, where the scenario
  activated the payload before the operator reached PROC-001-S10. On `2026-09-13-P1` the
  operator beat it by 92 s; at MET 120 the margin is smaller.
- `P4_hk_generation_halt` additionally scripts **`CMD_SYS_RESET` at MET 1320**. Per the
  campaign plan that command is PASS-4's *only* commanded activity, and it is hazardous,
  requiring the two-step confirmation demonstrated at B7. **The scenario performs the
  operator's sole task.** The measured suppression gap is MET 1200 through 1319, 120
  frames, with generation resuming at 1320 when the scenario's own reset fires — so the
  operator's entire window to detect and respond is 120 s, of which roughly 30 s is
  detection to RED.

**Why this was not simply a bug to fix.** The scenarios are **mission** timelines:
`P2_array_string_loss` runs 23040 s across four orbits, and its own comment says the four
orbits exist "so the decline is visible as a trend rather than a single sample." The
contacts are **windows into** a mission, computed later from the pinned orbit under D-014.
The two were authored against different notions of time and never reconciled.

**Measured scope, which is narrower than the table suggests.** Only PASS-2 requires more
than one contact:

- **PASS-3, one contact.** The stuck load at MET 900 drives `EPS_LOAD_I` from 1.400 to
  **1.800 A** within a single frame — above the 1.5 A yellow and below the 2.0 A red,
  which is the yellow-before-red ordering the dictionary's disposition ledger asserts.
  PROC-001-S07 therefore takes its limit-response branch at onset. A contact opening at
  MET 800 yields 331 of 431 frames satisfying S07, entirely in sunlight.
- **PASS-4, one contact.** A contact opening near MET 1000 spans the suppression gap.
- **PASS-2, two contacts.** See OF-017.

**Disposition (D-015).** Two-contact passes are admitted as a pattern; a start offset is
added to `tools/serve_sim.py` as the mechanism for reaching a contact that opens later in
a mission. Scenario files are not re-timed.

---

## OF-017 — for PASS-2, the FMEA's stated detection and the procedure's routing conditions cannot both be satisfied in any one contact

**Status:** RULED at **D-015** (2026-09-13) — PASS-2 becomes a two-contact pass:
observe on a sunlit contact, respond on a later eclipse contact.

**Claim.** FM-EPS-01 names **asymmetric string currents** as the detection for array-string
loss, and the campaign plan states that the operator observes "EPS_SA1_I collapsing to zero
while EPS_SA2_I holds." PROC-001-S07 routes to PROC-002 only on `EPS_BATT_SOC` at or below
35 %, `EPS_BATT_V` at or below 7.2 V, `EPS_LOAD_I` at or above 1.5 A, or `EPS_MODE` reading
SAFE. **No step of any procedure branches on string asymmetry.** In `P2_array_string_loss`
the asymmetry is visible only while sunlit, and the limit conditions are reached only in
eclipse — where both string currents read zero and the asymmetry is invisible. **No 430 s
window of the 23040 s scenario contains both.**

**Evidence** (measured on the operator's machine, with the operator's `check_fault_windows.py`):

| Window | SA1 / SA2 | SoC across window | BATT_V | Illumination | Frames satisfying S07 |
|---|---|---|---|---|---|
| AOS 660 → 1090 (60 s after onset) | **0.00 / 1.70** | **59.480 → 59.928 (rising)** | 7.5764 → 7.5824 | SUNLIT | **0 of 431** |
| AOS 21464 → 21894 (earliest with any trigger) | 0.00 / 0.00 | 37.312 → 34.996 | 7.3020 → 7.2750 | ECLIPSE | 1 of 431 |
| AOS 21700 → 22130 (crossing mid-contact) | 0.00 / 0.00 | 36.041 → 33.725 | 7.2871 → 7.2601 | ECLIPSE | **237 of 431** |

- First MET at which `EPS_BATT_SOC` ≤ 35 %: **21894**.
- `EPS_BATT_V` **never** reaches its 7.2 V yellow anywhere in the 23040 s scenario.
- The mode ladder first acts at MET **22822** (LOW_POWER); SoC at end of scenario 29.33 %.
- The second contact fits inside the scenario's duration with roughly 910 s to spare.

**What this meant for the pass as planned.** Flown in the only window reachable without a
tool change, PASS-2 shows an unmistakably dead solar string and PROC-001-S07 reads
`nominal`. PROC-002 is never invoked and the pass produces no anomaly response. The
campaign plan's generated statement that the operator observes state of charge "trending
below the plan's predicted value" is **false** in that window: charge *rises*, because one
surviving string at 1.7 A exceeds the 1.4 A load while sunlit.

**A smaller instance of the same prose-versus-measurement gap.** For PASS-3 the plan states
that the operator observes "EPS_BATT_SOC falling faster than the pass plan predicted." In
the reachable window charge also rises, 66.5 to 68.9, because that window is sunlit. PASS-3's
routing is unaffected — `EPS_LOAD_I` carries it — but the stated observation is not what the
model produces.

**Why this was not simply a bug to fix.** Adding an asymmetry branch to S07 changes a
procedure that has already passed a document gate, and raises a question the record has not
answered: whether the ground should route to a *power* contingency on evidence that is not
itself a power-limit violation. The alternative — accepting that this fault is detected but
not responded to inside one contact — is a statement about what the campaign demonstrates.

**Disposition (D-015).** Neither. PASS-2 becomes a two-contact pass: the asymmetry is
observed on a sunlit contact and the response is flown on a later eclipse contact where the
limit is crossed. S07 is not given an asymmetry branch and the scenario is not re-shaped.

---

## OF-018 — nothing verifies that a pass's scenario is observable within the contact it is assigned to

**Status:** RULED at **D-015** (2026-09-13) — recorded and **accepted for v0.1**,
with an obligation placed on the next gate.

**Claim.** `tools/gen_campaign.py` computes the contact week from the pinned element set and
assigns each pass a contact. Its self-test asserts D-014's two tiers and refuses a commanded
pass scheduled on a contact that is not usable for commanding. **It never compares a
scenario's fault onset, or the telemetry state that scenario produces, against the contact
the pass is assigned to.** The generated campaign plan therefore asserts, in prose,
observations that its own inputs make impossible — and `tools/run_checks.py` returns 11/11.

Both OF-016 and OF-017 are instances the absent check would have caught at generation time,
before any operator was scheduled against them. So is the PASS-3 observation noted in
OF-017.

**This is the shape already recorded against HUG-GND-005**: a property stated in the record
and credited by checks that exercise something adjacent to it. There the requirement was
contact-window gating and the credited cases were ground-station site pins. Here the property
is that a pass can observe what its plan says it observes, and the credited cases are
commanding-tier arithmetic.

**Disposition (D-015).** Recorded and accepted as v0.1 debt. The obligation the Director
placed on the next gate is stated in his own words in D-015 and is not restated here.

---

## OF-019 — the campaign plan records PASS-2 as uncommanded; its own procedure commands a shed

**Status:** open, defect in the generated campaign plan. Raised from flying PASS-2 on 2026-09-20.

**Claim.** `campaign/CAMPAIGN_PLAN.md` gives PASS-2 the field `Commanded | no`, and justifies its
contact selection on that basis — *"not commanded, so it does not need the commanding margin."*
PASS-2's procedure is PROC-002, whose **S04 sends `CMD_PLD_SET_STATE` with state OFF** whenever S03
selects array-string failure, which is the condition the pass is built to produce. The pass is
commanded.

**It was commanded in flight.** `docs/pass_reports/2026-09-20-P2b/commands.csv` holds exactly one
row: `CMD_PLD_SET_STATE`, `STATE OFF`, sent at 2026-09-20T22:09:51.046687Z, `RECEIVED_COUNT 2`.

**Scope.** The margin existed anyway — a 430 s contact leaves 190 s usable against the 20 s D-014
requires — so no pass was flown without the margin it needed. The defect is in the record, not in
the flight.

**Why it is not a one-line fix.** `gen_campaign.py` derives the `Commanded` field from
`defs/campaign.yaml`, which states *planned* commanding. PROC-002-S04's shed is *contingent* — it
fires only on a branch the plan cannot know in advance. The field conflates a plan with an outcome,
and both readings are defensible. What is not defensible is using the field to justify a contact
selection, which the generated prose does.

---

## OF-020 — no predicted state-of-charge profile exists for any contact

**Status:** RULED at **D-017** ruling 1 (2026-10-11), and implemented at `fac95f2` as
`tools/gen_pass_plan.py`. Raised from PASS-2 on 2026-09-20; became load-bearing while planning
PASS-3 on 2026-10-11. The `soc_delta_vs_plan_pct` values already filed in `2026-09-20-P2a` and
`2026-09-20-P2b` stand as filed.

**Claim.** The only predicted value the build produces is a scenario's `initial.soc_pct`, which is
the state of charge at **MET 0**. Both PASS-2 records carry it as `predicted_soc_pct: 55` for
contacts at MET 2190 and MET 21800, where the observed values are 61.07 % and 35.49 %.
`tools/pass_setup.py` produces configuration verification only and emits no profile.

Consequently **every `soc_delta_vs_plan_pct` field in every pass record is an artefact of comparing
two different mission times**, not a variance. `2026-09-20-P2a` records +6.199 and
`2026-09-20-P2b` records −20.144; neither number means anything.

**Why this blocks a procedure rather than merely annoying a reader.** PROC-002-S02 offers
*"the discharge is deeper than the eclipse plan predicts"* as one of two ways to select the branch
that leads to a response. With no plan to compare against, that criterion cannot be exercised at
all, in any pass. On PASS-2 it was the only criterion that could have applied, the other being
physically unreachable (OF-021).

**The divergence it would have shown is real and large.** Measured on `P3_stuck_load`, the stuck
load pushes state of charge below the same mission without the fault by 0.458 pp within one 430 s
contact and by 7.066 pp by the end of the first eclipse. The signal exists; nothing computes it.

**The design rule the fix must follow.** The prediction must be the **fault-free mission**: the same
scenario with its `faults:` list emptied and everything else identical, commands kept. A scripted
command is a planned activity; a fault is the thing that was not planned, which is exactly the split
HUG-SYS-005 already draws. A prediction generated from the same run as the truth would make
actual-versus-predicted identically zero and prove nothing.

**Verified against all four scenarios** (see `measurements.txt`): `P1_nominal`, having no faults,
predicts itself frame-for-frame identically — the control that the rule is implemented correctly.
`P4_hk_generation_halt` shows no state-of-charge divergence at all, because a telemetry halt costs
no power; its signature is instead **120 frames the plan expects and the actual run does not
produce**, which the same artefact captures.

---

## OF-021 — PROC-002-S02's decision table cannot be completed, demonstrated two different ways

**Status:** instance 2 RULED at **D-017** rulings 2 and 3 (2026-10-11) and implemented —
PROC-002-S02 gains the `load alarm` outcome, red-lined at procedures version 0.2 ahead of review.
Instance 1 open. Raised from PASS-2 on 2026-09-20 and from PASS-3 planning on 2026-10-11.

**Claim.** PROC-002-S02 asks *"Is the spacecraft trending energy-negative beyond what the
illumination state explains?"* and offers two outcomes:

| Outcome | Requires |
|---|---|
| `negative beyond eclipse` | `EPS_BATT_I` negative across three or more frames while SUNLIT, **or** discharge deeper than the eclipse plan predicts |
| `explained by eclipse` | `EPS_BATT_I` negative while ECLIPSE and the depth tracks the plan |

**Both outcomes presuppose that `EPS_BATT_I` is negative.** The table has no outcome for a
spacecraft that is charging, and no outcome for a spacecraft whose discharge cannot be compared to
a plan. The two anomaly passes fail it in opposite directions.

**Instance 1 — PASS-2, array-string loss.** The balance *is* negative, and neither route to
`negative beyond eclipse` is available. The sunlit-discharge route is **physically unreachable in
this scenario**: the surviving string carries 1.70 A against a 1.40 A load, so the battery charges
whenever sunlit and `EPS_BATT_I` is never negative in sunlight. The deeper-than-plan route needs an
artefact that does not exist (OF-020). The step was recorded on `2026-09-20-P2b` by carrying
contact A's observation across under the Director's cross-contact ruling of 2026-09-20, with the
gap stated in the entry.

**Instance 2 — PASS-3, stuck-on load.** The premise fails outright. Measured at the fault:

```
MET 899   EPS_LOAD_I 1.400 A   EPS_BATT_I +1.3038 A   SoC 66.500 %   SUNLIT
MET 900   EPS_LOAD_I 1.800 A   EPS_BATT_I +1.0430 A   SoC 66.506 %   SUNLIT
```

The stuck load costs 0.26 A of charge current and nothing more. State of charge **rises** across
the whole contact, 65.813 to 68.333. The battery does not go negative until MET 3664, in the first
eclipse, 2764 s after the fault and far beyond any contact containing it.

**The consequence for PASS-3.** PROC-002-S03 is applicable only *"when PROC-002-S02 selected the
negative branch"*. S03's own `load excursion` criteria are satisfied exactly — `EPS_LOAD_I` at
1.800 A is above the 1.5 A threshold with both strings symmetric at 1.70 A and consistent with
illumination — so **the step that can answer is gated behind the step that cannot**. S04's
commanded shed is never authorised, and the campaign plan's stated commanded activity for PASS-3
does not occur.

**What this is not.** It is not an argument that the shed is wrong. A stuck load that leaves the
spacecraft net-positive in sunlight is a loss of margin rather than a loss of power, and shedding
the sheddable load is a defensible response. The defect is that the procedure's gate asks about the
energy balance before asking about the cause, when the cause is diagnosable from the annunciated
point alone.

**What it needs.** OF-020's profile is a prerequisite and not a fix: with a plan to compare against,
PASS-2's instance resolves, and PASS-3's does not, because S02 would still be asking whether a
positive current is negative. Moving S02's test from *is the current negative* to *is the energy
trend below plan* is a change to a procedure that has passed a document gate, and is the Director's
ruling to make.

---

## OF-022 — no pass in the v0.1 campaign ever fires the autonomous mode ladder

**Status:** open. Raised from PASS-2 on 2026-09-20; already carried as the rationale for ANOM-002's
owner risk acceptance inside `docs/pass_reports/2026-09-20-P2b/report.yaml`.

**Claim.** HUG-EPS-003 specifies an autonomous mode ladder: LOW_POWER at 30 % state of charge,
SAFE at 20 %, shedding the payload on entry. The dictionary's disposition ledger asserts it. Four
steps of PROC-002 depend on it — S07 records the mode entered and the charge at entry, S08 chooses
between safing by command and letting the ladder hold, S09 recovers the commanded mode and S10
verifies that recovery. **Nothing in the campaign makes it fire.**

Measured over each scenario's full duration:

| Scenario | Lowest state of charge | Ladder |
|---|---|---|
| `P2_array_string_loss`, as actually flown | 31.216 % | never actuates |
| `P2_array_string_loss`, had the shed not been sent | 29.330 % | LOW_POWER at MET 22822 |
| `P3_stuck_load` | 60.009 % | never actuates |
| `P4_hk_generation_halt` | 65.009 % | never actuates |

**The second row is the one to read twice.** PASS-2's operator shed the payload at MET 22006, which
was correct, and that shed kept the battery above 30 % for the remainder of the mission. **The
operator's correct response is what removed the condition** those steps exist to record. Had the
shed not been sent, LOW_POWER would have fired at MET 22822 — 592 s after that contact's loss of
signal, so no contact of that pass would have observed it either.

**Already dispositioned once, narrowly.** ANOM-002 inside `2026-09-20-P2b` records PROC-002-S07 and
S08 as omitted and disposes by owner risk acceptance, on the determination that re-execution is not
feasible anywhere in v0.1. That disposition covers those two steps on that pass. It does not cover
the broader fact recorded here: that a core autonomous protection behaviour is asserted in the
design record and demonstrated by no pass in the campaign.

**Shape.** The same family as OF-018 — a property stated in the record whose demonstration the
campaign does not actually contain.

---

## OF-023 — PROC-002-S06 expects the stuck load to arrive still negative; in v0.1 it never does

**Status:** open, defect in a gated procedure. Raised while planning PASS-3 on 2026-10-11.
Does not block PASS-3: S06 can be completed truthfully.

**Claim.** PROC-002-S06's `recovered` outcome says *"The stuck-load case reaches here with the
balance still negative and is handled by the next branch"*, and its `still negative` outcome
calls a persisting negative current *"the stuck-load presentation"*. Both follow FMEA FM-EPS-08,
which states that with the stuck load the energy-negative trend persists after the payload shed.
`defs/eps.yaml` already carries, as an open question to the owner, the note that under the flat
generation profile it does not.

**Measured on `P3_stuck_load`, with the payload shed at MET 1000:**

```
MET  999   EPS_LOAD_I 1.800 A   EPS_BATT_I +1.0420 A   PLD_STATE ON    SUNLIT
MET 1000   EPS_LOAD_I 1.200 A   EPS_BATT_I +1.4328 A   PLD_STATE OFF   SUNLIT
```

After the shed the balance is positive, so S06 selects `recovered`, which its table permits,
and the procedure continues to S09 with the stuck 2.0 W still drawing. The stuck load shows
only at S05: `EPS_LOAD_I` falls by the payload's 0.600 A to 1.200 A, not to the 0.800 A the bus
draws with the payload off. Neither S05 nor S06 names 0.800 A as the comparison.

**What it needs.** S06's text and FM-EPS-08 describe a behavior the model does not produce.
Which one moves — the procedure text, the FMEA, or the generation profile `defs/eps.yaml` holds
open — is the owner's question already raised there.

**Shape.** The same family as OF-018 and OF-022 — a behavior stated in the record that no pass
in the campaign can show.

---

## OF-024 — the campaign plan's PASS-3 section cites the wrong FMEA row and the wrong expected trend

**Status:** RULED at **D-019** (2026-10-12): the campaign plan is left as PASS-3 flew it, and this entry stands as the record of the error. Raised from flying PASS-3 on 2026-10-11.

**Claim.** `campaign/CAMPAIGN_PLAN.md`, PASS-3, gives its FMEA row as `FM-EPS-02`, generated from
`defs/campaign.yaml` (`fmea_rows: [FM-EPS-02]`). FM-EPS-02 is total array output loss. The fault
PASS-3 flies is HUG-EPS-004(b), the stuck-on load, and every other record names FM-EPS-08 for it:
the FMEA's own fault-to-pass mapping (`(b) Stuck-on load, 2.0 W | FM-EPS-08 | … | P3`), the header
of `sim/scenarios/P3_stuck_load.yaml`, and `defs/eps.yaml`.

The same section tells the operator to expect *"EPS_BATT_SOC falling faster than the pass plan
predicted."* On `2026-10-11-P3` state of charge rose for the whole contact. Against the pass plan
it was 0.071 pp below at MET 950, before the shed, and 0.106 pp above at LOS, after it, because
the plan keeps the payload on.

**What it needs.** A correction to `defs/campaign.yaml`, regenerating the campaign plan. That
changes a generated plan record, so it is the owner's ruling to make.

**Shape.** The same family as OF-019 and OF-023: a planning record stating something the flown
pass does not show.

---

## OF-025 — the procedures send the operator to a STALENESS target that does not exist

**Status:** RULED at **D-018** ruling 1 (2026-10-11) and implemented, red-lined at procedures
version 0.3. Raised while planning PASS-4 on 2026-10-11.

**Claim.** PROC-001-S04 says *"The staleness annunciator is the STALENESS target in Packet
Viewer"*, and PROC-003-S01 and S02 open *"the STALENESS target"* and *"the STALENESS
annunciator level"*. The loaded configuration has two targets, HUGINN and UNKNOWN. The monitor
in `microservices/STALENESS/frame_staleness.py` publishes nothing to Packet Viewer: it announces
each level change as a COSMOS log message. `2026-09-13-P1` records the annunciator as not observed
because no such target exists.

**Where it actually appears.** Located by the Director on 2026-10-11 with a nominal run, then
the simulator stopped. The lines appear in **CmdTlmServer's Log Messages list**, level WARN,
source `DEFAULT__USER__OPENC3-HUGINN-STALENESS`; typing `staleness` in that list's Search box
shows only them:

```
18:28:17.829Z  CDH_FRAME_CNT staleness GREEN: no advance for 0.0 s (yellow 10 s, red 30 s; 64 successful reads)
18:29:20.896Z  CDH_FRAME_CNT staleness YELLOW: no advance for 10.0 s (yellow 10 s, red 30 s; 127 successful reads)
18:29:40.917Z  CDH_FRAME_CNT staleness RED: no advance for 30.0 s (yellow 10 s, red 30 s; 147 successful reads)
```

The same page carries what PROC-003-S02 compares the alarm against: the Interfaces tab shows
`HUGINN_INT`'s state and its Tlm pkts, the ground's received count.

**What it needs.** The procedures' Open and expect text to name CmdTlmServer's Log Messages, and
the console section to list CmdTlmServer as a tool the procedures use.

---

## OF-026 — no route into PROC-003 for a telemetry halt after acquisition

**Status:** RULED at **D-018** ruling 2 (2026-10-11) and implemented, red-lined at procedures
version 0.3. Raised while planning PASS-4 on 2026-10-11.

**Claim.** PROC-003's telemetry steps are entered *"on staleness annunciation"*, but PROC-001
hands off to PROC-003 from only two branches: PROC-001-S05 `not acquired`, at AOS, and
PROC-001-S12 `unacknowledged`, after a command. `tools/pass_report.py` accepts an invoked
procedure only from a governing step whose recorded branch calls it. A halt that begins after
frame lock, which is the presentation the campaign plan describes for PASS-4 (*"CDH_FRAME_CNT
ceasing to advance while the interface stays CONNECTED"*), therefore has no route into PROC-003,
and a record of the correct response would be refused.

Placing the contact so the halt precedes AOS does not fix it. The operator would then never see
the counter stop or the alarm go yellow and then red, and the alarm would already read RED from
before the contact (OF-027).

**Also affected.** PROC-003-S05 `restored` returns the operator to *"PROC-001 at PROC-001-S06"*,
which is right only when PROC-003 was entered from S05.

---

## OF-027 — the staleness monitor announces GREEN on its first read of a stored value, however old

**Status:** open. Raised while planning PASS-4 on 2026-10-11. Does not block PASS-4.

**Claim.** The monitor starts its staleness clock at its own first successful read. It does not
use the age of the value it reads. When COSMOS already holds a frame counter value from an
earlier session, the monitor's first line is GREEN even though nothing is arriving.

**Observed on 2026-10-11**, COSMOS started at 18:27:01Z with no simulator running:

```
18:27:14.760Z  CDH_FRAME_CNT staleness GREEN: no advance for 0.0 s (yellow 10 s, red 30 s; 1 successful reads)
18:27:24.770Z  CDH_FRAME_CNT staleness YELLOW: no advance for 10.0 s (yellow 10 s, red 30 s; 11 successful reads)
18:27:44.790Z  CDH_FRAME_CNT staleness RED: no advance for 30.0 s (yellow 10 s, red 30 s; 31 successful reads)
```

The counter value it read was the one COSMOS was still holding from the previous session. NO_READ,
the pre-acquisition state PROC-003-S02 describes as ordinary, was never announced.

**Consequence.** After any start or restart of the monitor, including the restart
PROC-003-S02's `monitor read fault` branch orders, the annunciator reads GREEN for 10 s
whatever the spacecraft is doing. Before AOS it reads RED, not NO_READ, whenever COSMOS holds an
old value.

**Why it does not block PASS-4.** In PASS-4 frames are flowing before the halt, so the monitor
goes GREEN, YELLOW, then RED as designed.

---

## OF-028 — in PASS-4 the post-reset counter epoch is the same as the counters before the halt

**Status:** open. Raised while planning PASS-4 on 2026-10-11. Does not block PASS-4.

**Claim.** PROC-003-S04 verifies CMD_SYS_RESET by its post-reset epoch,
`CDH_CMD_ACC_CNT = 1` and `CDH_CMD_REJ_CNT = 0`. In `P4_hk_generation_halt` the only command
accepted before the halt is the scenario's own payload ON at MET 120, so the counters read
ACC 1, REJ 0 before the halt as well. Measured on the model with a reset at MET 1260:

```
MET 1199   ACC 1   REJ 0   CDH_FRAME_CNT 1200   last frame before the halt
MET 1260   ACC 1   REJ 0   CDH_FRAME_CNT 1201   first frame after the reset
```

The epoch check passes whether or not a reset happened. The reset's real evidence in this pass is
frames resuming (PROC-003-S05) and the ground command log. The scenario's own scripted reset at
MET 1320 then resets the counters again, to the same values.

---

## OF-029 — the in-pass step list was too long to use at the pace of the pass

**Status:** open. Raised from PASS-4 on 2026-10-11 (AR-003 §5, finding 1); registered under
D-019 on 2026-10-12.

**Claim.** The in-pass instructions for PASS-4 were a 736-word step list, two pages long,
kept open beside the console. The scenario's scripted reset restored telemetry 21.1 s before
the operator's reset left the ground (AR-003 §3). The instructions are an operator aid
outside the repository.

---

## OF-030 — Command Sender reopens on the last packet selected, including a hazardous one

**Status:** open. Raised from PASS-4 on 2026-10-11 (AR-003 §5, finding 2); registered under
D-019 on 2026-10-12. Fixed and flown in the HUG-G002 build-out (D-019 selection 7).

**Claim.** On PASS-4 Command Sender opened on `CMD_MODE_SET`, held from an earlier session:
the packet sent by mistake on `2026-08-03-P1` (ANOM-001). The operator caught it with the
clock running and changed it to `CMD_SYS_RESET` by 20:06:05Z. No procedure step checks which
packet Command Sender holds before a hazardous command is sent.

---

## OF-031 — two hazardous commands' descriptions display as raw bytes in Command Sender

**Status:** open. Raised from PASS-4 on 2026-10-11 (AR-003 §5, finding 3); registered under
D-019 on 2026-10-12. Fixed and flown in the HUG-G002 build-out (D-019 selection 7).

**Claim.** Command Sender displayed the descriptions of `CMD_SYS_RESET` and `CMD_MODE_SET`
as `{"json_class":"String","raw":[...]}` arrays of numbers. The generated `cmd.txt`
descriptions of both, and of `CMD_SAFE_ENTER`, contain non-ASCII characters, an em dash and
a right arrow. The HK packet's description is plain ASCII and displays as text.

---

## OF-032 — two record keys name times their step no longer runs at

**Status:** open. Raised from PASS-4 on 2026-10-11 (AR-003 §5, finding 5); registered under
D-019 on 2026-10-12.

**Claim.** D-018 ruling 2 returns the operator to PROC-001-S06 after PROC-003, so on PASS-4
S06's `*_at_aos2` values were taken 357 s after AOS. S15 was taken 13 s before LOS, against
its "LOS minus 2 minutes".

---

## OF-033 — PROC-003-S10 places the anomaly report inside the pass report

**Status:** open. Raised from PASS-4 on 2026-10-11 (AR-003 §5, finding 6); registered under
D-019 on 2026-10-12.

**Claim.** PROC-003-S10 says the anomaly report is part of the pass report, not a separate
document. The campaign files its anomaly reports separately, as AR-001 to AR-003. PASS-4 did
both: a summary under `anomalies:` in its report, and AR-003.

---

# Errata against frozen evidence

**Archived evidence is never edited.** A demonstration manifest is digested at execution
time under D-008 and its digest is recomputed by `tools/verify_evidence.py` on every gate
run; correcting a manifest in place would break that binding and destroy the one property
the archive exists to have. Where an archived manifest is wrong or incomplete, the
correction is recorded HERE, against the frozen artifact, identified by its own digest so
the erratum cannot drift from what it corrects.

## ERR-001 — B14's manifest under-declares the requirements its demonstration covers

| Field | Value |
|---|---|
| Frozen artifact | `verification/evidence/B14-native-log-playback/attempt-002/MANIFEST.md` |
| Manifest sha256 | `af6fa9272da77893bd89637da9f09fcce6f8d50db2e8d0dd0376c132c8c01b29` |
| Raised | 2026-08-08, under D-013 item 3 |
| Artifact status | **Untouched.** No byte of the attempt directory was modified. |

**What the manifest says.** Its `| Requirement |` field reads `HUG-SYS-006`, and nothing
else.

**What the demonstration actually covered.** `BUILD_HANDOFF.md`'s B-table records B14
against *"HUG-SYS-006; HUG-GND-004; CONOPS §3.2; FM-GND-06"*, and the artifacts bear that
out: `HUG-GND-004` requires that all received telemetry be logged with timestamps and be
**exportable**, and `artifacts/log-objects.txt`, `artifacts/ground-native-telemetry.bin.gz`
and `artifacts/decompression.txt` are the export, by absolute path, digest and decompressed
bytes. The demonstration discharged both requirements and the manifest declared one.

**How this was found.** Not by reading the manifest. `tools/gen_traceability.py` builds the
downstream column from an executed run and reported `HUG-GND-004` under condition F2 — no
downstream verification reference of any kind — because the manifest's declaration is what
the run record reads. A matrix populated by scanning the source tree would have found
`HUG-GND-004` mentioned in `BUILD_HANDOFF.md` and reported it covered.

**Correction, and where the attribution now lives.** The requirement is attributed by an
executed case rather than by amending the archive:
`tests/test_b14_verdict.py::TestTheArchivedEvidencePasses` declares
`verifies = ("HUG-SYS-006", "HUG-GND-004")` and recomputes B14's verdict from the archived
bytes, so both requirements are discharged by a case that runs in the gate and would fail
if the archive changed. The next B14 attempt should declare both in its own manifest; until
then this erratum is the record.

**Scope.** This erratum corrects an ATTRIBUTION, not an observation. Nothing about what
B14 demonstrated, when, or with what result is altered — the manifest's `Result`,
`Outcome`, timestamps, artifact list and every digest stand exactly as recorded.
