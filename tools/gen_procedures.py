#!/usr/bin/env python3
"""Generate the operator's procedure documents from `defs/procedures.yaml`.

    python tools/gen_procedures.py            write procedures/PROC-00N.md
    python tools/gen_procedures.py --check    fail if any is stale

The operator reads `procedures/PROC-001.md` on the console; `tools/pass_report.py`
validates a completion record against `defs/procedures.yaml`. They are the same procedure
because one is generated from the other.

WHY THAT MATTERS MORE HERE THAN ANYWHERE ELSE IN THE BUILD. HUG-OPS-002 makes post-pass
review a comparison of the completion record against "the governing procedure". If the
document the operator followed and the list the validator checks could differ by one step,
the review would pass a pass in which a step was never executed and never noticed — and
the whole completion record would be a record of the wrong procedure. Every other
generated view in this repository protects a machine from drift; this one protects the
review.

WRITTEN FOR SOMEONE EXECUTING IT UNDER TIME PRESSURE. Each step is a heading with its
identifier, its role, and the telemetry it checks, because the step identifier is what the
completion record is keyed by and an operator should never have to derive it. Decision
steps print every branch with the observation that selects it — including the branches
that go badly, which are the ones being read when the procedure is actually needed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_openc3_config                                          # noqa: E402
import hugdefs                                                    # noqa: E402
from hugdefs import repo                                          # noqa: E402


def _wrap(text, width=88, indent=""):
    """Reflow one paragraph. YAML folded scalars arrive as a single long line."""
    words, lines, current = str(text).split(), [], indent
    for word in words:
        candidate = (current + " " + word) if current.strip() else indent + word
        if len(candidate) > width and current.strip():
            lines.append(current)
            current = indent + word
        else:
            current = candidate
    if current.strip():
        lines.append(current)
    return lines


def _operator_context(ctx):
    """The "Before you start" section (OF-014).

    An operator without working knowledge of the codebase needs to know what to open
    before any step can mean anything. This was the missing precondition to every step
    in every procedure, which is why it is rendered once at the top of each rather than
    repeated per step or, as it was, nowhere.
    """
    if not ctx:
        return []
    order = [("console", "The console — what to open"),
             ("shell", "The terminal"),
             ("pass_plan", "The pass plan"),
             ("pass_id", "The pass identifier"),
             ("records", "Where recorded values go"),
             ("validate", "Checking your record"),
             ("evidence", "Evidence")]
    out = ["## Before you start", "",
           "You do not need to know this program to run this procedure. Everything each",
           "step needs is named in the step; this section names the things every step",
           "assumes.", ""]
    for key, title in order:
        if ctx.get(key):
            out += [f"### {title}", ""]
            out += str(ctx[key]).rstrip().splitlines()
            out.append("")
    return out


def build_procedure(proc, roles, version, digest, context=None):
    by_role = {r["id"]: r["name"] for r in roles}
    out = [
        f"# {proc['id']} — {proc['title']}",
        "",
        "GENERATED FILE — DO NOT EDIT. Source: `defs/procedures.yaml`",
        f"Procedures version: {version} · Dictionary sha256: {digest[:16]}…",
        "",
        "> Edit the source and regenerate. A hand edit here would make the document the",
        "> operator follows differ from the procedure `tools/pass_report.py` reviews the",
        "> completion record against — and post-pass review would then pass a pass in",
        "> which a step was never executed and never noticed (HUG-OPS-002).",
        "",
        "## Governs",
        "",
    ]
    out = out[:-2] + _operator_context(context) + out[-2:]
    # A blank line in the folded source is a paragraph break, and stays one.
    for i, paragraph in enumerate(str(proc["governs"]).split("\n")):
        if i:
            out.append("")
        out += _wrap(paragraph)
    out += [
        "",
        "## Roles",
        "",
        "| Role | Who |",
        "|---|---|",
    ]
    used = []
    for step in proc["steps"]:
        if step["role"] not in used:
            used.append(step["role"])
    for role_id in used:
        out.append(f"| **{role_id}** | {by_role.get(role_id, role_id)} |")
    out += [
        "",
        "Every step below carries a stable identifier (HUG-OPS-001). **The completion",
        "record is keyed by these identifiers**, one entry per step, with no exceptions",
        "(HUG-OPS-002) — including the steps that turn out not to apply.",
        "",
        "## Steps",
        "",
    ]

    for step in proc["steps"]:
        out.append(f"### {step['id']} — {by_role.get(step['role'], step['role'])}"
                   + (f" · {step['when']}" if step.get("when") else ""))
        out.append("")
        out += _wrap(step["action"])
        out.append("")
        if step.get("tool"):
            out += ["```bash", step["tool"], "```", ""]
        # OF-014: the mechanism comes BEFORE the metadata, because it is what the
        # operator does. The Director halted at S01 against a step whose text named
        # an action and no way to perform it.
        mech = step.get("mechanism") or {}
        if mech.get("open"):
            out.append(f"**Open:** {mech['open']}")
            out.append("")
        if mech.get("run"):
            out += ["**Run:**", "", "```bash", mech["run"].rstrip(), "```", ""]
        if mech.get("placeholders"):
            for token, meaning in mech["placeholders"].items():
                out.append(f"> `{token}` — {' '.join(str(meaning).split())}")
            out.append("")
        if mech.get("expect"):
            out.append(f"**You know it worked when:** {' '.join(mech['expect'].split())}")
            out.append("")
        if mech.get("record_to"):
            out.append(f"**Write it down:** {' '.join(mech['record_to'].split())}")
            out.append("")

        checks = step.get("checks") or []
        out.append(f"- **Checks:** {', '.join(f'`{c}`' for c in checks) if checks else '—'}")
        records = step.get("records") or []
        if records:
            out.append(f"- **Records:** {', '.join(f'`{r}`' for r in records)}")
        if step.get("repeatable"):
            out.append(
                "- **May be re-run within the pass.** Record it as ONE completion entry "
                "carrying every attempt (`attempts:` and `earlier_attempts:`), never as "
                "a second entry. The attempt that failed is part of the record of the "
                "pass; only the final attempt's values go in `records:`.")
        applicability = str(step.get("applicability", "always")).strip()
        if applicability == "always":
            out.append("- **Applicability:** always. A completion record entry reading "
                       "`not_applicable` for this step is itself a finding.")
        else:
            out.append("- **Applicability:** " + " ".join(applicability.split()))
        out.append("")

        decision = step.get("decision")
        if decision:
            out += [
                f"**Decision — {decision['question']}**",
                "",
                "| Outcome | The observation that selects it | Then |",
                "|---|---|---|",
            ]
            for branch in decision["branches"]:
                observation = " ".join(str(branch["observation"]).split())
                then = " ".join(str(branch["then"]).split())
                out.append(f"| `{branch['outcome']}` | {observation} | {then} |")
            out += [
                "",
                "> A completed entry for this step must record **which branch was taken "
                "and the observation that selected it**. An omitted entry must record "
                "that no observation was made and no branch was selected — those are "
                "different facts and the record keeps them apart (HUG-OPS-002).",
                "",
            ]
    return out


def generated_files(procs, version, digest):
    out = {}
    for proc in procs["procedures"]:
        out[repo() / "procedures" / f"{proc['id']}.md"] = build_procedure(
            proc, procs["roles"], version, digest,
            procs.get("operator_context"))
    return out


def main(argv):
    hugdefs.console()
    check = "--check" in argv
    procs = hugdefs.load_procedures()
    version = procs["procedures_version"]
    _dict_version, digest = gen_openc3_config.source_digest()

    stale = []
    for path, lines in generated_files(procs, version, digest).items():
        rel = path.relative_to(repo()).as_posix()
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            stale.append(rel)
            continue
        if not hugdefs.emit(path, lines, check_only=check):
            stale.append(rel)

    if check:
        ok = not stale
        print(f"[{'PASS' if ok else 'FAIL'}] procedures/ matches defs/procedures.yaml"
              + ("" if ok else f" — stale or missing: {stale}; regenerate "
                               "(hand edits are prohibited by HUG-OPS-001)"))
        return 0 if ok else 1
    count = len(procs["procedures"])
    steps = sum(len(p["steps"]) for p in procs["procedures"])
    print(f"generated {count} procedure(s), {steps} steps, from defs/procedures.yaml "
          f"(procedures {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
