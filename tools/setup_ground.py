#!/usr/bin/env python3
"""Write gnd/openc3/.env from the committed template, with generated credentials.

    python tools/setup_ground.py           create .env if it does not exist
    python tools/setup_ground.py --force   regenerate it, replacing existing secrets
    python tools/setup_ground.py --check   report whether .env exists and is complete

The template is committed; the .env it produces is not (see .gitignore). Every
credential is generated fresh here rather than vendored from the operator's training
clone: two instances sharing secrets is a needless coupling, and a working credential
committed to a repository that may become public is a footgun that outlives whatever
posture made it look safe.

Credentials are the one thing in this repository deliberately NOT reproducible.
HUG-SYS-003's bit-for-bit requirement is about simulation results from a scenario file;
a Redis password is not an input to any of them, and seeding it would make it
predictable for no benefit.
"""
import secrets
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROJECT = REPO / "gnd" / "openc3"
TEMPLATE = PROJECT / ".env.template"
TARGET = PROJECT / ".env"
MARKER = "__GENERATE__"


def generate(name):
    """A value appropriate to the variable it fills."""
    if name.endswith("USERNAME"):
        return "huginn_" + secrets.token_hex(4)
    if name == "SECRET_KEY_BASE":
        return secrets.token_hex(64)          # Rails-style 128-char key
    return secrets.token_urlsafe(24)


def build():
    lines, filled = [], []
    for line in TEMPLATE.read_text(encoding="utf-8").split("\n"):
        if line.endswith("=" + MARKER):
            name = line[:-len("=" + MARKER)]
            lines.append(f"{name}={generate(name)}")
            filled.append(name)
        else:
            lines.append(line)
    return "\n".join(lines), filled


ACL_TEMPLATE = PROJECT / "openc3-redis" / "users.acl.template"
ACL_TARGET = PROJECT / "openc3-redis" / "users.acl"


def render_acl(env_values):
    """Write the Redis ACL from the SAME credentials written into .env.

    Redis stores the sha256 of each password in the ACL; the services authenticate with
    the plaintext from .env. The two must be generated together or they disagree — and
    that disagreement presents as two services restart-looping with `WRONGPASS`, which
    says nothing about credentials to anyone reading the compose output. The first
    bring-up failed exactly this way, because .env was generated and the vendored ACL
    still carried upstream's published hashes.
    """
    import hashlib

    def sha(name):
        return hashlib.sha256(env_values[name].encode("utf-8")).hexdigest()

    # Valkey rejects an ACL file containing ANYTHING but `user` lines — comments and
    # blank lines included, and it aborts startup naming every offending line rather
    # than saying "comments are not allowed". The explanation therefore lives in the
    # template, where a reader will find it, and is stripped on the way out.
    text = "\n".join(
        line for line in ACL_TEMPLATE.read_text(encoding="utf-8").split("\n")
        if line.strip() and not line.lstrip().startswith("#")) + "\n"
    for marker, value in (
        ("__REDIS_USERNAME__", env_values["OPENC3_REDIS_USERNAME"]),
        ("__REDIS_PASSWORD_SHA256__", sha("OPENC3_REDIS_PASSWORD")),
        ("__SR_USERNAME__", env_values["OPENC3_SR_REDIS_USERNAME"]),
        ("__SR_PASSWORD_SHA256__", sha("OPENC3_SR_REDIS_PASSWORD")),
        ("__ADMIN_PASSWORD_SHA256__", sha("OPENC3_REDIS_ADMIN_PASSWORD")),
    ):
        if marker not in text:
            raise RuntimeError(f"{ACL_TEMPLATE.name} has no {marker} placeholder")
        text = text.replace(marker, value)
    ACL_TARGET.write_bytes(text.encode("utf-8"))
    return ACL_TARGET


def parse_env(text):
    values = {}
    for line in text.split("\n"):
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def main(argv):
    if not TEMPLATE.exists():
        print(f"missing template: {TEMPLATE}", file=sys.stderr)
        return 2

    if "--check" in argv:
        if not TARGET.exists():
            print(f"[FAIL] {TARGET.relative_to(REPO)} does not exist — run "
                  f"`python tools/setup_ground.py` before starting the ground segment")
            return 1
        remaining = [l.split("=")[0] for l in TARGET.read_text(encoding="utf-8").split("\n")
                     if l.endswith("=" + MARKER)]
        if remaining:
            print(f"[FAIL] {TARGET.relative_to(REPO)} still has unfilled values: "
                  f"{remaining}")
            return 1
        if not ACL_TARGET.exists():
            print(f"[FAIL] {ACL_TARGET.relative_to(REPO)} does not exist — Redis will "
                  f"refuse every connection with WRONGPASS")
            return 1
        # Checking only that both files EXIST would miss the case that produced the
        # first failed bring-up: .env generated, ACL still carrying other credentials.
        import hashlib
        env = parse_env(TARGET.read_text(encoding="utf-8"))
        acl = ACL_TARGET.read_text(encoding="utf-8")
        for user_var, pass_var in (("OPENC3_REDIS_USERNAME", "OPENC3_REDIS_PASSWORD"),
                                   ("OPENC3_SR_REDIS_USERNAME",
                                    "OPENC3_SR_REDIS_PASSWORD")):
            digest = hashlib.sha256(env[pass_var].encode("utf-8")).hexdigest()
            if f"user {env[user_var]} on #{digest}" not in acl:
                print(f"[FAIL] the Redis ACL does not match .env for "
                      f"{env[user_var]}; regenerate with --force")
                return 1
        print(f"[PASS] {TARGET.relative_to(REPO)} and the Redis ACL exist and agree")
        return 0

    if TARGET.exists() and "--force" not in argv:
        print(f"{TARGET.relative_to(REPO)} already exists; leaving it alone. "
              f"Use --force to regenerate.\n"
              f"Regenerating invalidates any data the running stack holds under the "
              f"old credentials — stop the stack first.")
        return 0

    text, filled = build()
    TARGET.write_bytes((text if text.endswith("\n") else text + "\n").encode("utf-8"))
    print(f"wrote {TARGET.relative_to(REPO)} with {len(filled)} generated values")
    print("  " + ", ".join(filled))

    acl = render_acl(parse_env(text))
    print(f"wrote {acl.relative_to(REPO)} from the same credentials")

    print("\nBoth files are gitignored and must stay that way.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
