#!/usr/bin/env python3
"""Is the configuration the instance LOADED the one this repository generates?

    python tools/ground_config.py            digest each artifact on both sides
    python tools/ground_config.py --verify   fail on any difference, either direction

Owner ruling D-010, closing OF-001.

`CONFIG_ID.txt` carries the sha256 of `defs/tlm_cmd.yaml`, and pass setup compares it to
the dictionary of record. That is sound and it keeps its meaning. What it cannot see is
that the generated ground configuration is determined by the dictionary **and by
`tools/gen_openc3_config.py`** — so a generator change moves the artifact the ground
system executes while leaving the dictionary, and therefore the digest, byte-identical.

That is not hypothetical. At the `fill_fields` fix the repository said
`... 0x4855 None False` and the running instance said `... 0x4855 None True`, with equal
digests and equal plugin versions. Every hazardous command was untransmittable and a
digest comparison would have returned GO.

THE COMPARISON IS EXACT IN BOTH DIRECTIONS. A differing artifact is the failure that
prompted this, but an artifact the instance is missing is equally not the configuration of
record, and one the instance holds that this repository does not generate is a stray the
digest cannot see either. A subtraction in one direction would pass an instance with
nothing loaded.

THE ARTIFACT LIST IS DERIVED, NOT LISTED. It comes from `gen_openc3_config.generated_files`
— the generator's own answer to what it emits. A second hand-kept list here would go stale
the first time a file was added there, and a missing entry reads as "nothing to compare"
rather than as a gap.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_openc3_config                                          # noqa: E402
import hugdefs                                                    # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PROJECT = REPO / "gnd" / "openc3"

#: Where the running instance keeps its copy of each generated artifact, relative to the
#: repository path the generator writes. `None` means the artifact is deliberately not
#: part of the loaded configuration, with the reason given — an entry here is a decision,
#: and an unmapped artifact is an error rather than a silent skip.
INSTANCE_LOCATION = {
    "targets/HUGINN/target.txt":
        "bucket:/data/config/DEFAULT/targets/HUGINN/target.txt",
    "targets/HUGINN/CONFIG_ID.txt":
        "bucket:/data/config/DEFAULT/targets/HUGINN/CONFIG_ID.txt",
    "targets/HUGINN/cmd_tlm/tlm.txt":
        "bucket:/data/config/DEFAULT/targets/HUGINN/cmd_tlm/tlm.txt",
    "targets/HUGINN/cmd_tlm/cmd.txt":
        "bucket:/data/config/DEFAULT/targets/HUGINN/cmd_tlm/cmd.txt",
    "microservices/STALENESS/frame_staleness.py":
        "bucket:/data/config/DEFAULT/microservices/"
        "DEFAULT__USER__OPENC3-HUGINN-STALENESS/frame_staleness.py",
    # plugin.txt is not unpacked to the config bucket; the instance keeps the lines it
    # instantiated the plugin from, in its own model store. That IS the loaded copy —
    # it is what the interface and microservice definitions were built from — and it is
    # the artifact the fill_fields drift lived in.
    "plugin.txt": "redis:plugin_txt_lines",
    # The gemspec is build input, not runtime configuration. The instance never reads it;
    # it reads the gem that was built FROM it, and every file inside that gem is compared
    # above. Excluded deliberately, not overlooked.
    "openc3-cosmos-huginn.gemspec": None,
}


# ------------------------------------------------------------------ the pure predicate

def compare(loaded, repository):
    """(differing, missing_from_instance, extra_in_instance).

    Pure — takes both sides as {artifact: digest} dicts — so tests/test_ground_config.py
    can drive every polarity without a running stack.
    """
    differing = sorted(k for k in set(loaded) & set(repository)
                       if loaded[k] != repository[k])
    missing = sorted(set(repository) - set(loaded))
    extra = sorted(set(loaded) - set(repository))
    return differing, missing, extra


def describe(loaded, repository):
    """(ok, one-line evidence). Written once so --verify and the tests report the same
    sentence."""
    if not repository:
        return False, ("the repository side is empty, so there is nothing to compare "
                       "and a pass would mean nothing")
    differing, missing, extra = compare(loaded, repository)
    problems = []
    if differing:
        problems.append(
            f"differ between the instance and this repository: {differing} — the loaded "
            f"ground configuration is not the one this repository generates, and the "
            f"source digest cannot see it (D-010)")
    if missing:
        problems.append(f"generated here but NOT loaded in the instance: {missing}")
    if extra:
        problems.append(f"loaded in the instance but not generated here: {extra}")
    if problems:
        return False, "; ".join(problems)
    return True, (f"{len(repository)} generated artifact(s) are byte-identical between "
                  f"this repository and the loaded configuration")


def repository_artifacts():
    """{artifact: sha256} for every file the generator emits that the instance loads."""
    defs = hugdefs.load_tlm_cmd()
    version, digest = gen_openc3_config.source_digest()
    plugin_dir = gen_openc3_config.plugin_dir()
    out = {}
    for path in gen_openc3_config.generated_files(defs, version, digest):
        rel = path.relative_to(plugin_dir).as_posix()
        if rel not in INSTANCE_LOCATION:
            raise AssertionError(
                f"the generator emits {rel!r}, which tools/ground_config.py neither "
                f"compares nor deliberately excludes. Add it to INSTANCE_LOCATION — "
                f"with None and a reason if it is genuinely not part of the loaded "
                f"configuration. An unmapped artifact would be silently unchecked.")
        if INSTANCE_LOCATION[rel] is None:
            continue
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


# ---------------------------------------------------------------------- the live side

def _compose(args, **kw):
    """Run a compose command and decode its output as UTF-8, explicitly.

    `text=True` alone decodes with the LOCALE encoding, which on this machine is cp1252.
    plugin.txt contains an em-dash; decoded as cp1252 it becomes two different
    characters, the digest changes, and this check reports a configuration drift that
    does not exist. That false positive was live in the first version of this file and
    would have made the pass-setup step cry wolf on every run -- the fastest way to
    teach an operator to ignore a no-go.
    """
    return subprocess.run(["docker", "compose"] + args, cwd=PROJECT,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="strict", timeout=180, **kw)


def _env(name):
    env = (PROJECT / ".env").read_text(encoding="utf-8")
    found = re.search(rf"^{name}=(.*)$", env, re.M)
    if not found:
        raise RuntimeError(f"{name} is not set in gnd/openc3/.env")
    return found.group(1).strip()


def _bucket_digests(paths):
    """sha256 of each path, computed INSIDE the container that holds them."""
    script = "; ".join(
        f'if [ -f "{p}" ]; then echo "{p} $(sha256sum "{p}" | cut -d" " -f1)"; '
        f'else echo "{p} MISSING"; fi' for p in paths)
    out = _compose(["exec", "-T", "openc3-buckets", "sh", "-c", script])
    if out.returncode != 0:
        raise RuntimeError(f"could not read the loaded configuration: "
                           f"{out.stderr.strip() or out.stdout.strip()}")
    got = {}
    for line in out.stdout.split("\n"):
        parts = line.strip().split()
        if len(parts) == 2:
            got[parts[0]] = parts[1]
    return got


def _plugin_txt_digest(scope="DEFAULT"):
    """sha256 of the plugin.txt lines the instance instantiated the plugin from."""
    user, password = _env("OPENC3_REDIS_USERNAME"), _env("OPENC3_REDIS_PASSWORD")
    out = _compose(["exec", "-T", "openc3-redis", "sh", "-c",
                    f"redis-cli --user '{user}' --pass '{password}' --no-auth-warning "
                    f"HGETALL {scope}__openc3_plugins"])
    if out.returncode != 0:
        raise RuntimeError(f"could not read the plugin model: {out.stderr.strip()}")
    lines = [l for l in out.stdout.split("\n") if l.strip()]
    blobs = [l for l in lines if l.lstrip().startswith("{")]
    for blob in blobs:
        try:
            model = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if not str(model.get("name", "")).startswith("openc3-cosmos-huginn"):
            continue
        text = "\n".join(model.get("plugin_txt_lines", [])) + "\n"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    raise RuntimeError(
        "no HUGINN plugin model found in the instance. Either the plugin is not "
        "installed or the scope is wrong; both are conditions this check must refuse "
        "to pass rather than read as an empty configuration")


def query_loaded():
    """{artifact: sha256} as the RUNNING INSTANCE holds it.

    Read from the instance's own stores — the config bucket its microservices load from,
    and the plugin model its definitions were instantiated from. Not from the repository
    working tree, and not from the built gem: comparing the repository to itself is the
    shape this check exists to avoid.
    """
    wanted = {rel: loc for rel, loc in INSTANCE_LOCATION.items() if loc}
    bucket = {rel: loc.split("bucket:", 1)[1]
              for rel, loc in wanted.items() if loc.startswith("bucket:")}
    digests = _bucket_digests(list(bucket.values()))
    loaded = {}
    for rel, path in bucket.items():
        got = digests.get(path)
        if got and got != "MISSING":
            loaded[rel] = got
    if any(loc == "redis:plugin_txt_lines" for loc in wanted.values()):
        loaded["plugin.txt"] = _plugin_txt_digest()
    return loaded


def verify():
    ok, evidence = describe(query_loaded(), repository_artifacts())
    print(f"[{'PASS' if ok else 'FAIL'}] loaded-vs-repository: {evidence}")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)
    if args.verify:
        return verify()
    repo, loaded = repository_artifacts(), query_loaded()
    print(f"{'artifact':<46} {'repository':<18} {'instance':<18}")
    for rel in sorted(set(repo) | set(loaded)):
        print(f"{rel:<46} {repo.get(rel, '-')[:16]:<18} "
              f"{loaded.get(rel, '-')[:16]:<18}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
