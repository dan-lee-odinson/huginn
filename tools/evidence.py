#!/usr/bin/env python3
"""Gate evidence as preserved artifact, captured at execution time.

Owner ruling D-008: "archive the B14 pass recording (and each demo's artifacts) into
the evidence folder at execution time — gate evidence as preserved artifact, not a
retention window."

WHY A RETENTION WINDOW IS THE WRONG MECHANISM, stated once here because the earlier
design got it wrong. Setting the ground system's LOG_RETAIN_TIME to thirty days looks
like it protects the evidence, and does not:

  - the logs still live in a Docker named volume, and `docker compose down -v` destroys
    them in one keystroke with no warning and no trace;
  - retention EXPIRES. Evidence that is valid for thirty days is evidence with a
    deadline, and HUG-G002 has no such deadline;
  - the artifact stays outside version control, so nothing binds what the gate reads to
    what the demonstration actually produced;
  - and the failure is silent. A reviewer opening an empty volume months later cannot
    tell a demonstration that never ran from one whose evidence aged out.

Capturing at execution time inverts every one of those. The artifact is written into
the repository as the demonstration runs, digested so it is tamper-evident, and
committed alongside the code that produced it.

    from evidence import Evidence

    with Evidence("B14-native-log-playback", obligation="B14",
                  requirement="HUG-SYS-006") as ev:
        ...run the demonstration...
        ev.capture_file(exported_log, "ground-native-telemetry.log")
        ev.capture_text("console.txt", captured_output)
        ev.record("PASS", "pass played back in the ground system with the simulator "
                          "stopped")

On exit the manifest is written with a sha256 for every artifact. **A demonstration
that captures nothing raises rather than completing**, so an evidence directory can
never exist as an empty claim that something was shown.
"""
import hashlib
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO / "verification" / "evidence"


#: Every manifest written in this process, in order. The outcome a runner reports comes
#: from here, not from a demonstration function's return value — the manifest is the
#: record, and a runner that prints its own verdict can contradict it.
WRITTEN = []


class EvidenceError(RuntimeError):
    """Raised when a demonstration would complete without preserving evidence."""


class Evidence:
    """One demonstration's evidence directory, written as the demonstration runs."""

    def __init__(self, demo_id, obligation, requirement, description=""):
        if not demo_id or "/" in demo_id or "\\" in demo_id:
            raise ValueError(f"demo_id must be a simple name, got {demo_id!r}")
        self.demo_id = demo_id
        self.obligation = obligation
        self.requirement = requirement
        self.description = description
        # The demonstration's directory holds one numbered directory per ATTEMPT.
        # `dir` is allocated at __enter__ rather than here, so the number reflects what
        # is on disk when the run actually starts.
        self.demo_dir = EVIDENCE_ROOT / demo_id
        self.dir = None
        self.artifacts_dir = None
        self.attempt = None
        self.artifacts = []
        self.result = None
        self.result_detail = ""
        self.notes = []
        # Wall-clock time is provenance here, not a model input. The determinism rules
        # that forbid it bind the scenario path in sim/, which this is not.
        self.started_utc = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ capture

    def _record_artifact(self, path, note):
        raw = path.read_bytes()
        self.artifacts.append({
            "name": path.relative_to(self.artifacts_dir).as_posix(),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "note": note,
        })

    def capture_file(self, source, name=None, note=""):
        """Copy a file produced by the demonstration into the evidence directory.

        Copied, not referenced. A path into a container volume or a temp directory is
        not evidence — it is a pointer to something that will not be there later.
        """
        source = Path(source)
        if not source.is_file():
            raise EvidenceError(
                f"{self.demo_id}: cannot capture {source} — it does not exist. The "
                f"demonstration must produce its artifact before capturing it.")
        target = self.artifacts_dir / (name or source.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self._record_artifact(target, note)
        return target

    def capture_text(self, name, text, note=""):
        """Write captured output — a console transcript, a query result — as an
        artifact. LF endings, so the record's byte-level conventions hold here too."""
        target = self.artifacts_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        body = text if text.endswith("\n") else text + "\n"
        target.write_bytes(body.replace("\r\n", "\n").encode("utf-8"))
        self._record_artifact(target, note)
        return target

    def archived(self, name):
        """Read back an artifact THIS run already captured, as text.

        The verdict must be computable from the archived evidence alone (D-012): live
        polls pace a demonstration but never decide it. That is only true if the
        verdict's inputs ARE the archived bytes, so it reads them back off disk rather
        than trusting the in-memory values it happened to write a moment earlier. A run
        whose capture silently failed then cannot also report PASS about the thing it
        did not capture — it raises here instead.
        """
        target = self.artifacts_dir / name
        if not target.is_file():
            raise EvidenceError(
                f"{self.demo_id}: the verdict asked for artifact {name!r}, which was "
                f"never captured. A verdict computed from an artifact that does not "
                f"exist is not computable from the evidence.")
        return target.read_text(encoding="utf-8")

    def note(self, text):
        """An observation worth preserving that is not itself a file."""
        self.notes.append(text)

    #: The outcomes a demonstration may record.
    #:
    #: PASS and FAIL are both statements ABOUT THE SUBJECT: it did the thing, or it did
    #: not. INSTRUMENT_FAULT is a statement about the RUN: collection failed, so this
    #: run establishes nothing about the subject either way.
    #:
    #: The third one exists because B6 needed it and there was nowhere to put it. The
    #: staleness monitor was annunciating GREEN -> YELLOW -> RED correctly, verified in
    #: the ground system's own log, while the harness that was supposed to read those
    #: annunciations returned an empty transcript. Recording FAIL would have asserted
    #: something false about a working monitor; deleting the directory, which is what
    #: happened, left no trail that the attempt was made at all. Neither is honest.
    #:
    #: An INSTRUMENT_FAULT is NOT a pass and must never be counted as one. It is a
    #: demonstration still owed.
    RESULTS = ("PASS", "FAIL", "INSTRUMENT_FAULT")

    def record(self, result, detail=""):
        """The demonstration's outcome. All three are evidence."""
        if result not in self.RESULTS:
            raise ValueError(f"result must be one of {self.RESULTS}, got {result!r}")
        self.result = result
        self.result_detail = detail

    # ------------------------------------------------------------------ manifest

    def _manifest(self):
        finished = datetime.now(timezone.utc)
        stamp = "%Y-%m-%dT%H:%M:%SZ"
        out = [
            f"# Demonstration evidence — {self.demo_id}",
            "",
            "Captured at execution time under owner ruling D-008: gate evidence is a",
            "preserved artifact, not a retention window. Every file below was written",
            "into this repository as the demonstration ran, and is digested so that what",
            "the gate reads can be shown to be what the demonstration produced.",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Demonstration | `{self.demo_id}` |",
            f"| Attempt | `{self.attempt}` |",
            f"| Obligation | {self.obligation} |",
            f"| Requirement | {self.requirement} |",
            f"| Started (UTC) | {self.started_utc.strftime(stamp)} |",
            f"| Finished (UTC) | {finished.strftime(stamp)} |",
            f"| Result | **{self.result}** |",
        ]
        if self.description:
            out += [f"| What it demonstrates | {self.description} |"]
        if self.result_detail:
            out += ["", f"**Outcome:** {self.result_detail}"]
        if self.result == "INSTRUMENT_FAULT":
            out += [
                "",
                "> **This run establishes nothing about the subject.** The instrument —",
                "> the collection path this demonstration reads its evidence through —",
                "> failed. The obligation is neither discharged nor refuted here, and",
                "> this record must not be counted as a pass. The demonstration is still",
                "> owed.",
            ]
        out += [
            "",
            "## Artifacts",
            "",
            "| File | Bytes | sha256 | Note |",
            "|---|---|---|---|",
        ]
        for a in self.artifacts:
            out.append(f"| `artifacts/{a['name']}` | {a['bytes']} | "
                       f"`{a['sha256']}` | {a['note'] or '—'} |")
        if self.notes:
            out += ["", "## Observations", ""]
            out += [f"- {n}" for n in self.notes]
        out += [
            "",
            "## Provenance",
            "",
            "These artifacts are committed to the repository. They do not depend on any",
            "ground-system retention setting, on a Docker volume surviving, or on this",
            "machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that",
            "protects the window between a pass ending and its capture — it is not the",
            "mechanism by which this evidence is preserved, and nothing here relies on",
            "it.",
            "",
        ]
        return out

    # ------------------------------------------------------------------- context

    ATTEMPT_GLOB = "attempt-*"

    def _next_attempt_dir(self):
        """The next unused attempt directory for this demonstration.

        ATTEMPTS ARE APPEND-ONLY. Every run gets a fresh numbered directory, and no run
        may write into one that already holds a manifest. Before this, a re-run wrote
        straight over `evidence/<demo_id>/` — so a second attempt silently destroyed the
        first. That is how the contaminated B6 and B14 attempts lost their artifacts and
        had to be reconstructed by hand from a diagnosis transcript.

        It is the same failure D-008 and D-011 each address, arriving by a third route.
        D-008 stopped evidence expiring; D-011 stopped a failed collection being recorded
        as a verdict about the subject; this stops a later run erasing what an earlier one
        saw. An overwritten attempt is indistinguishable from an attempt that never
        happened, and the whole discipline exists to make missing things visible.
        """
        existing = (sorted(self.demo_dir.glob(self.ATTEMPT_GLOB))
                    if self.demo_dir.is_dir() else [])
        used = [int(d.name.split("-", 1)[1]) for d in existing
                if d.name.split("-", 1)[1].isdigit()]
        return self.demo_dir / f"attempt-{(max(used) + 1) if used else 1:03d}"

    def __enter__(self):
        if self.dir is None:
            self.dir = self._next_attempt_dir()
            self.artifacts_dir = self.dir / "artifacts"
        self.attempt = self.dir.name
        if (self.dir / "MANIFEST.md").exists():
            raise EvidenceError(
                f"{self.demo_id}: {self.dir} already holds a manifest. Attempts are "
                f"append-only — a run must never write over one that already recorded "
                f"what it saw.")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            # The demonstration blew up. Preserve whatever it managed to capture and
            # record the failure — a crashed demonstration is a result, and burying it
            # would be the worst outcome of all.
            self.result = self.result or "FAIL"
            self.result_detail = (self.result_detail
                                  or f"demonstration raised {exc_type.__name__}: {exc}")
            self.note(f"Terminated by {exc_type.__name__}. Artifacts below are whatever "
                      f"had been captured before that point.")
            self._write()
            return False

        if not self.artifacts:
            raise EvidenceError(
                f"{self.demo_id}: the demonstration captured no artifacts. An evidence "
                f"directory with nothing in it is a claim that something was shown "
                f"without anything to show, which is worse than no directory at all. "
                f"Capture the artifact or let the demonstration fail.")
        if self.result is None:
            raise EvidenceError(
                f"{self.demo_id}: no result recorded. Call record('PASS'|'FAIL', ...) "
                f"before the demonstration completes.")
        self._write()
        return False

    def _write(self):
        text = "\n".join(self._manifest())
        (self.dir / "MANIFEST.md").write_bytes(text.encode("utf-8"))
        # Recorded at the moment the manifest is written, so a caller can report what
        # was RECORDED instead of re-deriving a verdict. A runner printing "FAIL" while
        # the manifest it just wrote says INSTRUMENT_FAULT is contradicting the record.
        WRITTEN.append({"demo_id": self.demo_id, "attempt": self.attempt,
                        "result": self.result, "dir": self.dir})


def summary():
    """Every demonstration whose evidence is preserved, for the gate packet."""
    if not EVIDENCE_ROOT.is_dir():
        return []
    out = []
    for manifest in sorted(EVIDENCE_ROOT.glob("*/attempt-*/MANIFEST.md")):
        text = manifest.read_text(encoding="utf-8")
        result = "UNKNOWN"
        for line in text.split("\n"):
            if line.startswith("| Result |"):
                result = line.split("**")[1] if "**" in line else result
        artifacts = len(list((manifest.parent / "artifacts").rglob("*")))
        out.append({"demo_id": manifest.parent.parent.name,
                    "attempt": manifest.parent.name, "result": result,
                    "artifacts": artifacts})
    return out


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover
        pass
    rows = summary()
    if not rows:
        print("No demonstration evidence preserved yet.")
        print(f"Expected under {EVIDENCE_ROOT.relative_to(REPO).as_posix()}/")
        sys.exit(0)
    print(f"{'demonstration':42s} {'attempt':12s} {'result':17s} artifacts")
    print("-" * 84)
    for r in rows:
        print(f"{r['demo_id']:42s} {r['attempt']:12s} "
              f"{r['result']:17s} {r['artifacts']}")

    # Every attempt is listed, not just the latest. A demonstration that took three
    # goes to get right is a different thing from one that worked first time, and the
    # gate reads the difference. Only PASS counts as discharged.
    passed = {r["demo_id"] for r in rows if r["result"] == "PASS"}
    owed = sorted({r["demo_id"] for r in rows} - passed)
    print(f"\n{len(passed)} demonstration(s) discharged by a passing attempt.")
    if owed:
        print(f"Still owed: {', '.join(owed)}")
