#!/usr/bin/env python3
"""Every digest in every evidence manifest still matches the artifact it names.

    python tools/verify_evidence.py            report each attempt
    python tools/verify_evidence.py --verify   fail on any mismatch

D-008 makes gate evidence a preserved artifact, and each manifest carries a sha256 for
every file it lists so that what the gate reads can be shown to be what the demonstration
produced. **A digest nobody recomputes is decoration.** This recomputes them.

It exists because they had already stopped matching. Evidence captured on Windows can
hold CRLF, `.gitattributes` set `* text=auto eol=lf` for the whole repository, and git
therefore stored a line-ending-translated copy: one captured runner transcript hashed
`634ec09d…` in the working tree and `43b38324…` as git would check it out. Every manifest
recorded the first. On a fresh clone — which is exactly how a reviewer would read this
repository — the digests would not have verified, and nothing would have said so.

`verification/evidence/** -text` stops the translation. This check is what makes the
stopping verifiable, and what will notice the next thing that edits an artifact after the
fact, whatever that turns out to be.

THE SCAN IS ITS OWN FIRST FAILURE MODE. A scan that silently finds nothing reports "all
digests verify" over an empty set, which is the vacuous pass this build has met more than
once. So an evidence root with no manifests, a manifest with no digests, and a manifest
naming a file that is absent are all failures rather than quiet successes.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence as ev_mod                                         # noqa: E402

REPO = Path(__file__).resolve().parent.parent

#: `| `artifacts/name` | bytes | `sha256` | note |`
ROW = re.compile(r"^\|\s*`(artifacts/[^`]+)`\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]{64})`\s*\|",
                 re.M)


def manifest_rows(text):
    """(relative path, recorded bytes, recorded sha256) for each artifact listed."""
    return [(m.group(1), int(m.group(2)), m.group(3)) for m in ROW.finditer(text)]


def check_attempt(manifest_path):
    """(ok, [problem, ...]) for one attempt's manifest."""
    text = manifest_path.read_text(encoding="utf-8")
    rows = manifest_rows(text)
    problems = []
    if not rows:
        return False, [f"{manifest_path}: lists no artifacts, so there is nothing to "
                       f"verify and a pass would mean nothing"]
    for rel, size, digest in rows:
        path = manifest_path.parent / rel
        if not path.is_file():
            problems.append(f"{rel}: recorded in the manifest but absent from disk")
            continue
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            problems.append(
                f"{rel}: manifest records {digest[:16]}… ({size} bytes), the file on "
                f"disk is {actual[:16]}… ({len(raw)} bytes) — the evidence is not the "
                f"bytes the demonstration produced")
        elif len(raw) != size:
            problems.append(f"{rel}: digest matches but the recorded size {size} is "
                            f"not {len(raw)}")
    return not problems, problems


def scan():
    """(ok, evidence, problems) across every attempt in the evidence root."""
    root = ev_mod.EVIDENCE_ROOT
    if not root.is_dir():
        return False, "the evidence root does not exist", []
    manifests = sorted(root.glob("*/attempt-*/MANIFEST.md"))
    if not manifests:
        return False, ("no evidence manifests found; a verification that checked "
                       "nothing would report success over an empty set"), []
    problems, artifacts = [], 0
    for manifest in manifests:
        ok, found = check_attempt(manifest)
        artifacts += len(manifest_rows(manifest.read_text(encoding="utf-8")))
        problems += found
    if problems:
        return False, f"{len(problems)} digest problem(s)", problems
    return True, (f"{artifacts} artifact(s) across {len(manifests)} attempt(s) match "
                  f"the digests their manifests record"), []


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # pragma: no cover
        pass
    ok, summary, problems = scan()
    print(f"[{'PASS' if ok else 'FAIL'}] evidence integrity: {summary}")
    for p in problems:
        print(f"  - {p}")
    if not args.verify:
        for manifest in sorted(ev_mod.EVIDENCE_ROOT.glob("*/attempt-*/MANIFEST.md")):
            good, found = check_attempt(manifest)
            rel = manifest.parent.relative_to(ev_mod.EVIDENCE_ROOT).as_posix()
            print(f"  {'ok  ' if good else 'BAD '} {rel}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
