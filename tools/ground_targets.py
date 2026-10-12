#!/usr/bin/env python3
"""What is loaded in HUGINN's COSMOS instance, checked against what may be.

    python tools/ground_targets.py            list the targets the instance holds
    python tools/ground_targets.py --verify   fail if the inventory is not exactly
                                              defs/ground.yaml's allowed_targets

HUG-GND-006 (B10) has pass setup verify THE LOADED CONFIGURATION against the dictionary
of record. That obligation is only as good as the claim that the loaded configuration is
HUGINN's alone. A second plugin's targets sitting in the same instance would not fail the
digest comparison - the digest is computed over HUGINN's own target - so the discrepancy
would pass B10 while making B10's sentence untrue.

This build shipped OPENC3_DEMO=0 for one bring-up believing it read as "off". It is a
presence flag; the demo installed with INST, INST2 and EXAMPLE alongside HUGINN, and
nothing in the gate noticed. The instance was clean again within the hour, but the
half-hour in which it was not is the whole argument for this file: contamination has to
be a failing check, not something a builder happens to look at. (DECISIONS.md D-009.)

The comparison is EXACT IN BOTH DIRECTIONS. Foreign targets are the failure that
prompted it, but an instance missing HUGINN is equally not the configuration of record -
and a check that only hunted extras would pass an empty instance, which is the shape a
vacuous pass usually takes.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hugdefs                                                    # noqa: E402

REPO = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------ the pure predicate

def compare(loaded, allowed):
    """(foreign, missing) - what is present that may not be, and absent that must be.

    Pure, so tests/test_ground_targets.py can drive it at both polarities without a
    running stack. The live query below is the only part that needs Docker, and it does
    no judging of its own.
    """
    loaded, allowed = set(loaded), set(allowed)
    return sorted(loaded - allowed), sorted(allowed - loaded)


def describe(loaded, allowed):
    """(ok, one-line evidence). Written here rather than at the call site so the
    verify path and the test suite report the same sentence."""
    foreign, missing = compare(loaded, allowed)
    if foreign and missing:
        return False, (f"instance holds foreign target(s) {foreign} and is missing "
                       f"{missing}; loaded={sorted(loaded)}")
    if foreign:
        return False, (f"instance holds foreign target(s) {foreign} - the loaded "
                       f"configuration is not HUGINN's alone, so HUG-GND-006's pass-"
                       f"setup comparison would not mean what it says; "
                       f"loaded={sorted(loaded)}")
    if missing:
        return False, (f"instance is missing target(s) {missing}; loaded="
                       f"{sorted(loaded)}")
    return True, (f"{len(loaded)} target(s) loaded, exactly the permitted set "
                  f"{sorted(allowed)}")


def allowed_targets():
    """The permitted set from defs/ground.yaml, cross-checked against the plugin.

    ground.yaml is the source, but the HUGINN entry has to agree with the TARGET line
    the plugin actually declares - otherwise a rename in one place would leave this
    check permitting a target that no longer exists and failing the one that does.
    """
    ground = hugdefs.load_ground()
    allowed = list(ground["deployment"]["allowed_targets"])
    plugin = (REPO / "gnd" / "openc3" / "plugins" / "openc3-cosmos-huginn"
              / "plugin.txt").read_text(encoding="utf-8")
    declared = re.findall(r"^TARGET\s+\S+\s+(\S+)\s*$", plugin, re.M)
    for name in declared:
        if name not in allowed:
            raise AssertionError(
                f"plugin.txt declares TARGET {name}, which defs/ground.yaml's "
                f"allowed_targets {allowed} does not permit")
    return allowed


# -------------------------------------------------------------------- the live inventory

def _env(name):
    env = (REPO / "gnd" / "openc3" / ".env").read_text(encoding="utf-8")
    found = re.search(rf"^{name}=(.*)$", env, re.M)
    if not found:
        raise RuntimeError(f"{name} is not set in gnd/openc3/.env")
    return found.group(1).strip()


def query_loaded(scope="DEFAULT"):
    """Targets the running instance holds, read from Redis.

    Redis rather than the REST API deliberately: the API answers for the session the
    caller authenticated, while this is COSMOS's own model store - what the instance
    believes it has, not what it chooses to show. It is also the store the operator
    container reads at startup, so it cannot disagree with the running system without
    the running system being broken.
    """
    user, password = _env("OPENC3_REDIS_USERNAME"), _env("OPENC3_REDIS_PASSWORD")
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "openc3-redis", "sh", "-c",
         f"redis-cli --user '{user}' --pass '{password}' --no-auth-warning "
         f"HKEYS {scope}__openc3_targets"],
        cwd=REPO / "gnd" / "openc3", capture_output=True, text=True,
        encoding="utf-8", errors="strict", timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"could not read the target list from Redis: "
                           f"{out.stderr.strip() or out.stdout.strip()}")
    targets = [line.strip() for line in out.stdout.split("\n") if line.strip()]
    if not targets:
        # An empty answer is the vacuous-pass shape: no targets means nothing to find
        # foreign, and a subtraction-only check would call that clean.
        raise RuntimeError(
            f"Redis returned no targets for scope {scope}. Either the stack is not "
            f"up or the scope is wrong; both are conditions this check must refuse "
            f"to pass rather than read as an empty instance")
    return targets


def verify(scope="DEFAULT"):
    loaded = query_loaded(scope)
    ok, evidence = describe(loaded, allowed_targets())
    print(f"[{'PASS' if ok else 'FAIL'}] foreign-target check: {evidence}")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify", action="store_true",
                    help="fail unless the inventory is exactly the permitted set")
    ap.add_argument("--scope", default="DEFAULT")
    args = ap.parse_args(argv)
    if args.verify:
        return verify(args.scope)
    for name in sorted(query_loaded(args.scope)):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
