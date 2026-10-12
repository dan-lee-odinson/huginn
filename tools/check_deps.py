#!/usr/bin/env python3
"""Every third-party import this repository makes is declared in requirements.txt.

    python tools/check_deps.py            list what is imported and what is declared
    python tools/check_deps.py --verify   fail on an undeclared import or a dead pin
    python tools/check_deps.py --preflight  check the RUNNING interpreter can import them

requirements.txt was correct and complete before this file existed. It was also invisible:
nothing outside DECISIONS.md mentioned it, so a fresh terminal met `ModuleNotFoundError:
sgp4` from tools/serve_sim.py and the fix had to be guessed. A dependency that is declared
but not installable-by-instruction is a dependency the next operator discovers the hard
way, at the console, during a pass.

Two different failures, so two different modes:

  --verify     a SOURCE property. Does the repository declare what it imports? Runs in
               the gate, needs nothing installed.
  --preflight  an ENVIRONMENT property. Can THIS interpreter import them? Runs before
               serving, and reports the interpreter it is speaking about - the whole
               confusion is that "python" means different things in different terminals.

The comparison is exact in both directions. An undeclared import is the failure that
prompted this, but a declared package nothing imports is a pin that will be carried,
version-locked and unexamined, long after the code that needed it went away.
"""
import argparse
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Distribution name on PyPI vs the name you import. These differ often enough that
# comparing the two sets directly would report phantom problems in both directions.
IMPORT_TO_DISTRIBUTION = {
    "yaml": "PyYAML",
    "sgp4": "sgp4",
}

#: Every directory of first-party source. A package added to the repository and not
#: added here reads as third-party and fails --verify, which is how `ve` announced
#: itself: the guard does not assume, it asks.
SCAN_DIRS = ("sim", "tools", "tests", "ve")


def _local_module_names():
    """Names that resolve inside this repository, so they are not third-party.

    Derived from the tree rather than listed, because a hand-maintained exemption list
    is the thing that goes stale and starts hiding real undeclared imports.
    """
    names = set()
    for d in SCAN_DIRS:
        root = REPO / d
        if not root.is_dir():
            continue
        names.add(d)
        for p in root.rglob("*.py"):
            names.add(p.stem)
        for p in root.iterdir():
            if p.is_dir():
                names.add(p.name)
    return names


def imported_names(paths=None):
    """Top-level module names imported anywhere in the scanned source.

    Parsed with ast, not grepped. A regex over import lines picks up the word after
    'import' inside comments, docstrings and strings - the first draft of this scan
    reported 'what' and 'defs' as dependencies, both of which came from prose.
    """
    if paths is None:
        paths = [p for d in SCAN_DIRS for p in (REPO / d).rglob("*.py")
                 if (REPO / d).is_dir()]
    found = set()
    for path in paths:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                # level > 0 is a relative import, which is by definition local.
                if node.level == 0 and node.module:
                    found.add(node.module.split(".")[0])
    return found


def third_party(names, local=None):
    """Of these imported names, the ones that come from outside."""
    local = _local_module_names() if local is None else set(local)
    return {n for n in names
            if n not in sys.stdlib_module_names and n not in local}


def declared(text=None):
    """Distribution names pinned in requirements.txt, mapped to how they are imported."""
    if text is None:
        text = (REPO / "requirements.txt").read_text(encoding="utf-8")
    dists = set()
    for line in text.split("\n"):
        line = line.split("#")[0].strip()
        if not line:
            continue
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
            if sep in line:
                line = line.split(sep)[0]
                break
        dists.add(line.strip())
    return dists


def compare(imports, declared_dists):
    """(undeclared, unused) - imported but not pinned, and pinned but not imported."""
    dist_of = {k: v for k, v in IMPORT_TO_DISTRIBUTION.items()}
    needed = {dist_of.get(n, n) for n in imports}
    undeclared = sorted(needed - set(declared_dists))
    unused = sorted(set(declared_dists) - needed)
    return undeclared, unused


def describe(imports, declared_dists):
    undeclared, unused = compare(imports, declared_dists)
    if undeclared and unused:
        return False, (f"requirements.txt does not declare {undeclared}, and pins "
                       f"{unused} which nothing imports")
    if undeclared:
        return False, (f"requirements.txt does not declare {undeclared} - a fresh "
                       f"terminal would meet ModuleNotFoundError with no instruction "
                       f"telling it what to install")
    if unused:
        return False, (f"requirements.txt pins {unused}, which nothing imports; a "
                       f"version-locked dependency outliving its caller")
    return True, (f"{len(declared_dists)} declared dependenc(ies) "
                  f"{sorted(declared_dists)} exactly cover the third-party imports")


def verify():
    ok, evidence = describe(third_party(imported_names()), declared())
    print(f"[{'PASS' if ok else 'FAIL'}] dependency declaration: {evidence}")
    return 0 if ok else 1


def preflight(quiet=False):
    """Can the interpreter RUNNING THIS CODE import what the repository needs?

    Names the interpreter in every message. "Install sgp4" is not actionable advice on
    a machine with several things called python on PATH; "<interpreter path> -m pip
    install ..." is.
    """
    import importlib.util
    missing = []
    for name in sorted(third_party(imported_names())):
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    if missing:
        print(f"[FAIL] {sys.executable} cannot import {missing}.\n"
              f"       Install this repository's pinned dependencies into THAT "
              f"interpreter:\n"
              f"         \"{sys.executable}\" -m pip install -r "
              f"\"{REPO / 'requirements.txt'}\"\n"
              f"       (Any other python on PATH will not help - the one that must "
              f"have them is the one you run the tools with.)", file=sys.stderr)
        return 1
    if not quiet:
        print(f"[PASS] {sys.executable} can import every declared dependency")
    return 0


def require(tool_name):
    """Preflight guard for a tool's entry point. Exits with advice, not a traceback."""
    if preflight(quiet=True) != 0:
        print(f"       ({tool_name} cannot start without them.)", file=sys.stderr)
        raise SystemExit(1)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    args = ap.parse_args(argv)
    if args.verify:
        return verify()
    if args.preflight:
        return preflight()
    print(f"interpreter : {sys.executable}")
    print(f"imported    : {sorted(third_party(imported_names()))}")
    print(f"declared    : {sorted(declared())}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
