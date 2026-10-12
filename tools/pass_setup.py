#!/usr/bin/env python3
"""PROC-001 pre-pass configuration verification — B10's enforcement point.

    python tools/pass_setup.py --pass-id 2026-08-04-A
    python tools/pass_setup.py --pass-id ... --no-record   verify without writing

HUG-GND-006, verbatim: *"At pass setup the ground system shall display the version and
digest of the loaded telemetry/command configuration, and the pre-pass step of PROC-001
shall verify them against the dictionary of record; a mismatch shall be a no-go for
commanding until resolved."*

FM-GND-04 names this same step as the detection and response for loaded-configuration
drift, and its excluded-row note (e) says the mismatch response *"reloads and re-runs
that same step under its no-go rule."* Owner ruling D-010 made it a tool, executed as the
pre-pass step, with the GO/NO-GO recorded in the pass report.

THE NO-GO IS PROCEDURAL (D-010). This tool does not inhibit commanding and must not be
made to. The requirement says a mismatch is a no-go *for commanding* — a condition on the
Flight Director's go/no-go at AOS − 5 min, which is where the pass timeline already puts
it. A technical inhibit would be a mechanism the record does not have. What this tool
owes the operator is a correct, legible verdict and the evidence behind it; acting on a
NO-GO is the Flight Director's, and refusing to act is a procedural violation with a
name rather than a silent bypass.

EVERYTHING DISPLAYED IS READ FROM THE RUNNING INSTANCE. Not from the working tree. The
requirement is about the *loaded* configuration, and a step that read the repository and
compared it to the repository would pass with the ground segment switched off — which is
the shape this check exists to refuse.

Four conditions, all of which must hold for GO:

  1. the loaded configuration's dictionary version and source digest match the
     dictionary of record (HUG-GND-006, the digest keeping its D-010 meaning)
  2. every generated artifact loaded in the instance is byte-identical to the one this
     repository generates (D-010's loaded-vs-repository check)
  3. the instance holds exactly the permitted targets and no others (D-009)
  4. the instance answered at all — an unreadable instance is a NO-GO, never a pass
"""
import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_openc3_config                                          # noqa: E402
import ground_config                                              # noqa: E402
import ground_targets                                             # noqa: E402

REPO = Path(__file__).resolve().parent.parent
INSTANCE_CONFIG_ID = "/data/config/DEFAULT/targets/HUGINN/CONFIG_ID.txt"


def loaded_config_id():
    """The version and digest the INSTANCE holds, parsed from its own copy.

    This is the "display" half of HUG-GND-006. Reading the repository's CONFIG_ID.txt
    here would make the whole step a comparison of the working tree with itself.
    """
    out = ground_config._compose(
        ["exec", "-T", "openc3-buckets", "sh", "-c", f"cat {INSTANCE_CONFIG_ID}"])
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(
            f"could not read the loaded configuration identity from the instance "
            f"({INSTANCE_CONFIG_ID}). The ground segment is not up, or the HUGINN "
            f"plugin is not installed. Either way this is a NO-GO: an unreadable "
            f"instance is not a verified one")
    text = out.stdout
    version = re.search(r"^DICTIONARY_VERSION\s+(\S+)\s*$", text, re.M)
    digest = re.search(r"^SOURCE_SHA256\s+(\S+)\s*$", text, re.M)
    if not version or not digest:
        raise RuntimeError(
            f"the loaded CONFIG_ID.txt does not carry both DICTIONARY_VERSION and "
            f"SOURCE_SHA256; got:\n{text}")
    return version.group(1), digest.group(1)


def dictionary_of_record():
    """The version and digest of `defs/tlm_cmd.yaml` as this repository holds it.

    Deferred to the generator's own accessor rather than recomputed here. The digest in
    the loaded CONFIG_ID.txt was written by `source_digest`, so asking the same function
    is what makes this a comparison of the instance against the record, instead of a
    comparison of two independent opinions about how to derive an identity.
    """
    version, digest = gen_openc3_config.source_digest()
    return str(version), digest


def check_identity():
    """Condition 1 — loaded identity vs the dictionary of record."""
    loaded_v, loaded_d = loaded_config_id()
    record_v, record_d = dictionary_of_record()
    problems = []
    if loaded_v != record_v:
        problems.append(f"dictionary version: instance has {loaded_v!r}, "
                        f"the dictionary of record is {record_v!r}")
    if loaded_d != record_d:
        problems.append(f"source digest: instance has {loaded_d[:16]}…, "
                        f"the dictionary of record is {record_d[:16]}…")
    display = (f"DICTIONARY_VERSION {loaded_v}   SOURCE_SHA256 {loaded_d}")
    if problems:
        return False, display, "; ".join(problems)
    return True, display, (f"loaded identity matches the dictionary of record "
                           f"(v{record_v}, {record_d[:16]}…)")


def run(pass_id, record=True):
    """Execute the pre-pass step. Returns (go, lines)."""
    lines, go = [], True

    lines.append("## PROC-001 pre-pass — configuration verification (HUG-GND-006)")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Pass | `{pass_id}` |")
    lines.append(f"| Executed | {datetime.now(timezone.utc).isoformat(timespec='seconds')} |")
    lines.append(f"| Step | PROC-001 pre-pass, AOS − 5 min (CONOPS §5) |")
    lines.append(f"| Tool | `tools/pass_setup.py` |")
    lines.append("")

    # --- 1. displayed identity vs the dictionary of record
    try:
        ok, display, evidence = check_identity()
    except Exception as exc:
        ok, display, evidence = False, "UNREADABLE", f"{type(exc).__name__}: {exc}"
    go &= ok
    lines.append("### Loaded configuration, as displayed by the ground system")
    lines.append("")
    lines.append("```")
    lines.append(display)
    lines.append("```")
    lines.append("")
    lines.append(f"- **{'PASS' if ok else 'FAIL'}** — identity vs dictionary of record: "
                 f"{evidence}")

    # --- 2. loaded vs repository (D-010)
    try:
        ok, evidence = ground_config.describe(ground_config.query_loaded(),
                                              ground_config.repository_artifacts())
    except Exception as exc:
        ok, evidence = False, f"{type(exc).__name__}: {exc}"
    go &= ok
    lines.append(f"- **{'PASS' if ok else 'FAIL'}** — loaded vs repository (D-010): "
                 f"{evidence}")

    # --- 3. no foreign targets (D-009)
    try:
        ok, evidence = ground_targets.describe(ground_targets.query_loaded(),
                                               ground_targets.allowed_targets())
    except Exception as exc:
        ok, evidence = False, f"{type(exc).__name__}: {exc}"
    go &= ok
    lines.append(f"- **{'PASS' if ok else 'FAIL'}** — target inventory (D-009): "
                 f"{evidence}")

    lines.append("")
    lines.append(f"### Verdict: **{'GO' if go else 'NO-GO'}** for commanding")
    lines.append("")
    if go:
        lines.append("All four conditions hold. The loaded configuration is the "
                     "dictionary of record, is the configuration this repository "
                     "generates, and is HUGINN's alone.")
    else:
        lines.append("**A mismatch is a no-go for commanding until resolved "
                     "(HUG-GND-006).** The response is FM-GND-04 note (e): reload the "
                     "generated configuration and re-run this step. ")
        lines.append("")
        lines.append("This verdict is **procedural** (D-010). No technical command "
                     "inhibit is armed by this tool — the no-go is a condition on the "
                     "Flight Director's go/no-go at AOS − 5 min. Commanding against a "
                     "NO-GO is a procedure violation to be dispositioned as an anomaly "
                     "in the pass report, not something this tool prevents.")
    lines.append("")

    if record:
        out_dir = REPO / "docs" / "pass_reports" / pass_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "pass_setup.md"
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        lines.append(f"_Recorded at `{path.relative_to(REPO).as_posix()}` "
                     f"(HUG-OPS-002)._")
    return go, lines


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pass-id", required=True,
                    help="identifier for the pass this step belongs to")
    ap.add_argument("--no-record", action="store_true",
                    help="verify and print without writing the pass-report entry")
    args = ap.parse_args(argv)
    go, lines = run(args.pass_id, record=not args.no_record)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # pragma: no cover
        pass
    print("\n".join(lines))
    return 0 if go else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
