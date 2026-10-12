#!/usr/bin/env python3
"""Run every HUGINN checker and test suite. One command, before every commit.

    python tools/run_checks.py            everything (checks and both self-tests)
    python tools/run_checks.py --fast     checks only, skipping the self-tests
    python tools/run_checks.py --verbose  stream each suite's full output

Exit status is 0 only when every suite passes, so this is usable as a commit gate
and as CI.

The self-tests are not optional decoration. HUG-VER-002 and obligation B4: a
checker's passing result counts as evidence only once the checker has been
demonstrated to fail under a violated condition. --fast exists for a tight edit loop;
the gate before a commit is the full run.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
REPO = REPO.parent

def _counts(module, attr):
    """How many checks and cases a checker actually carries, asked of the checker.

    These were literals - "84 two-polarity cases", "66 two-polarity cases" - and the
    66 was stale within an hour of the suite growing to 72. A gate that misreports its
    own coverage is the same defect as a document restating another document's version:
    a fact copied out of its source and left to drift. Counted here instead.
    """
    import importlib
    m = importlib.import_module(module)
    return len(m.CHECKS), sum(len(v) for v in getattr(m, attr).values())


def _suites():
    sys.path.insert(0, str(REPO / "tools" / "checkers"))
    drc_checks, drc_cases = _counts("design_record_consistency", "MUTATIONS")
    gen_checks, gen_cases = _counts("defs_generation", "MUTATIONS")
    return [
        ("design record consistency", ["tools/checkers/design_record_consistency.py"],
         f"{drc_checks} checks over the record's prose", False),
        ("design record consistency — self-test",
         ["tools/checkers/design_record_consistency.py", "--self-test"],
         f"{drc_cases} two-polarity cases", True),
        ("defs generation", ["tools/checkers/defs_generation.py"],
         f"{gen_checks} checks binding sources to generated views", False),
        ("defs generation — self-test",
         ["tools/checkers/defs_generation.py", "--self-test"],
         f"{gen_cases} two-polarity cases", True),
        ("evidence integrity", ["tools/verify_evidence.py", "--verify"],
         "every manifest digest matches the artifact it names", False),
        ("dependency declaration", ["tools/check_deps.py", "--verify"],
         "every third-party import declared, every pin still imported", False),
        ("simulator", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
         "EPS, commanding, accounting, interface and ground-inventory properties",
         False),
        # B3 and B5's falsifiability, and the reason they are self-tests rather than
        # document checks. Both generators emit a CLEAN document against this record
        # whether or not their conditions work: every failure condition HUG-VER-001
        # names has zero naturally occurring instances here, so a generator with all of
        # them stubbed produces the same output. The self-tests are what tell the two
        # apart. The documents themselves are records of an execution and carry run
        # metadata, so they cannot round-trip byte-identically the way a generated view
        # of defs/ must — `--check` normalises the run metadata and is not gated.
        ("traceability matrix — self-test",
         ["tools/gen_traceability.py", "--self-test"],
         "every HUG-VER-001 failure condition demonstrated to fail generation", True),
        ("evidence chain — self-test",
         ["tools/gen_verification_report.py", "--self-test"],
         "an index that cannot back its claim is refused", True),
        # D-014's classification, and the rule that makes it bind. The plan is checked
        # rather than self-tested only: it IS a deterministic view of defs/campaign.yaml
        # and the pinned orbit, so unlike a verification report it can round-trip.
        ("campaign plan", ["tools/gen_campaign.py", "--check"],
         "the plan is what the record and the pinned orbit generate", False),
        ("campaign plan — self-test", ["tools/gen_campaign.py", "--self-test"],
         "D-014 decides both tiers, and a plan that violates it is refused", True),
    ]


SUITES = _suites()


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover
        pass
    fast = "--fast" in argv
    verbose = "--verbose" in argv

    results, t0 = [], time.time()
    for name, cmd, what, is_self_test in SUITES:
        if fast and is_self_test:
            results.append((name, None, what))
            continue
        started = time.time()
        env = dict(os.environ)
        # The simulator suite imports `sim`, `tools` and its own harness by name.
        env["PYTHONPATH"] = os.pathsep.join(
            [str(REPO), str(REPO / "tools"), str(REPO / "tests"),
             env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        proc = subprocess.run([sys.executable] + cmd, cwd=REPO, env=env,
                              capture_output=not verbose, text=True,
                              encoding="utf-8", errors="replace")
        elapsed = time.time() - started
        ok = proc.returncode == 0
        results.append((name, ok, f"{what} — {elapsed:.1f}s"))
        if not ok and not verbose:
            print(f"\n===== {name} FAILED =====")
            print(proc.stdout or "")
            print(proc.stderr or "")

    print("\n" + "=" * 72)
    print("HUGINN check summary")
    print("=" * 72)
    for name, ok, what in results:
        mark = "SKIPPED" if ok is None else ("PASS" if ok else "FAIL")
        print(f"  [{mark:>7}] {name}\n            {what}")

    ran = [r for r in results if r[1] is not None]
    failed = [r[0] for r in ran if not r[1]]
    print("=" * 72)
    if fast:
        print("  --fast: self-tests SKIPPED. A checker's pass is not evidence until its")
        print("  red case is demonstrated to fail it (HUG-VER-002, B4). Run the full")
        print("  suite before committing.")
    print(f"  {len(ran) - len(failed)}/{len(ran)} suites pass in {time.time() - t0:.1f}s"
          + (f"; FAILING: {failed}" if failed else ""))
    print("=" * 72)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
