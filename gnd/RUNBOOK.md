# Ground segment runbook

The HUGINN ground segment is a **self-contained OpenC3 COSMOS project** vendored at
`gnd/openc3/`, pinned to the version in `defs/ground.yaml`. It is deliberately separate
from the stock COSMOS demo the operator runs for training — see `DECISIONS.md` D-007
for why.

| | HUGINN | Operator's training demo |
|---|---|---|
| Compose project | `huginn` | `cosmos-project` |
| Location | `gnd/openc3/` (in this repo) | `<cosmos-project>` (outside it) |
| Web UI | http://localhost:**2910** | http://localhost:**2900** |
| Secondary | 2953 | 2943 |
| Demo targets | off | on |

They share nothing: separate containers, networks and named volumes. Either can be
reset without touching the other. Check **G16** asserts the ports stay disjoint.

## Operator environment

Do this once per machine, before anything else. Skipping it is how a fresh terminal
meets `ModuleNotFoundError: sgp4` halfway through `tools/serve_sim.py`.

**A Windows machine can have more than one Python.** `where python` can list several,
and only one of them may be the real interpreter you want. On the development machine
it listed:

```bash
where python
```

```
<python-install>\python.exe                                      <- the one to use
<user-profile>\AppData\Local\Microsoft\WindowsApps\python.exe    <- Microsoft Store stub
<user-profile>\AppData\Local\Python\bin\python.exe
```

The WindowsApps entry is not an interpreter at all — running it prints *"Python was not
found; run without arguments to install from the Microsoft Store"* and exits, which reads
like a broken install rather than a shim. Ask an interpreter to identify itself rather
than trusting the name:

```bash
python -c "import sys; print(sys.executable)"
```

**Install the pinned dependencies into that interpreter.** Not into "python" generally —
into the one you just printed:

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` pins PyYAML and sgp4 exactly. They are pinned rather than floated
because HUG-SYS-003 requires bit-for-bit reproducibility across runs, and a propagator
that changed version mid-campaign would break it (ruling D-003).

**Verify before you need it:**

```bash
python tools/check_deps.py --preflight
```

Passing prints the interpreter it is speaking about. Failing prints the full install
command for *that* interpreter, because "install sgp4" is not actionable on a machine
with several things called python.

`tools/serve_sim.py` runs this preflight itself before importing anything, so it fails
with instructions rather than a traceback. The check suite separately runs
`tools/check_deps.py --verify`, which is a different property: that the repository
*declares* what it imports. That one needs nothing installed and catches the reverse
problem too — a pinned package nothing imports, carried version-locked long after its
caller went away.

## First run

```bash
python tools/setup_ground.py
```

Writes `gnd/openc3/.env` from the committed template with freshly generated
credentials. That file is gitignored and must stay that way — no working credential
belongs in this repository.

```bash
cd gnd/openc3 && docker compose up -d
```

First start pulls ~8 images and takes a few minutes. The system is ready when the
`huginn-openc3-cosmos-init-1` container has completed.

```bash
docker compose ps
```

Then open **http://localhost:2910**.

## Stopping

```bash
cd gnd/openc3 && docker compose down
```

Add `-v` to also drop the named volumes.

**This is safe once a demonstration has run**, and that is deliberate. Under owner
ruling D-008 every demonstration archives its artifacts into `verification/evidence/`
**at execution time**, digested and committed — so the B14 pass recording is in the
repository, not in a volume. An earlier version of this runbook warned against `-v`
because the design then relied on log retention; that design was superseded precisely
because "don't press the dangerous key" is not a way to protect evidence.

## Known machine quirks

Found by the operator on this machine. They are recorded here because each presents as
something else, and every one cost time before it was recognised.

### Rebuilding the plugin does not update the running instance

**A rebuilt gem can sit on disk while the instance keeps running the old code, and
nothing says so.** `openc3cli load` compares the plugin's **`plugin.txt` lines** to
decide whether anything changed. Microservice file *contents* are not part of that
comparison, so a change to `microservices/STALENESS/frame_staleness.py` — regenerated,
rebuilt into the gem, loaded — is refused with:

```
No version change detected for: openc3-cosmos-huginn-0.5.gem__0
```

and, when handed the installed plugin's hash to take the update path:

```
Updating existing plugin: openc3-cosmos-huginn-0.5.gem__0 ...
No changes detected - Exiting without change
```

Both read like success. The instance keeps serving the previous file.

Bumping the version is **not** the way out: the plugin version is the dictionary
version, so raising it to force a reload would misstate which dictionary is loaded.
Destroy the plugin instance and load the gem fresh:

```bash
cd gnd/openc3
docker compose exec -T openc3-cosmos-cmd-tlm-api sh -c "cd /plugins/openc3-cosmos-huginn && gem build openc3-cosmos-huginn.gemspec"
docker compose exec -T openc3-cosmos-cmd-tlm-api ruby -e 'require "openc3"; require "openc3/models/plugin_model"; m = OpenC3::PluginModel.get(name: "openc3-cosmos-huginn-0.5.gem__0", scope: "DEFAULT"); OpenC3::PluginModel.from_json(m, scope: "DEFAULT").destroy'
MSYS_NO_PATHCONV=1 docker compose exec -T openc3-cosmos-cmd-tlm-api ruby /openc3/bin/openc3cli load /plugins/openc3-cosmos-huginn/openc3-cosmos-huginn-0.5.gem DEFAULT
```

Keep `MSYS_NO_PATHCONV=1` at the start of the third command. In Git Bash, an argument
that begins with `/` is rewritten into a Windows path, so without it ruby is handed a
path the container does not have and the load never runs. Bash elsewhere treats it as an
ordinary environment setting. The first two commands are unaffected: their container
paths sit inside a longer argument.

This recreates the target, the interface and all seven microservices. Native telemetry
and command logs live under `/data/logs/` in the buckets volume and are **not** touched.

**`ground_config.py --verify` is the guard, and it is the only thing that catches this:**

```bash
python tools/ground_config.py --verify
```

It digests what the **instance** holds — the config bucket its microservices load from,
and the plugin model its definitions were instantiated from — against what this
repository generates. Before the reload above it named the one file that differed:

```
[FAIL] loaded-vs-repository: differ between the instance and this repository:
       ['microservices/STALENESS/frame_staleness.py']
```

**Run it after any generator change, and before any demonstration whose evidence is
meant to cover the new code.** The configuration digest cannot see this class of drift —
that is why this check exists (D-010).

### Demonstrations must be run one at a time

`tools/demonstrate.py` binds to a fixed simulator port (7801) and to the one ground
system. Two runs at once fight over both, and the failure does not look like
contamination: B14 proves the simulator is off by checking that port refuses
connections, so a second run's simulator holding it open reads as an ordinary FAIL of a
control.

That happened on 2026-08-06 — a run interrupted by the machine sleeping was still alive
when a second was started, and two contaminated verdicts were recorded before the
overlap was noticed. **Confirm the previous run is dead before starting another:**

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object ProcessId,CommandLine"
```

Nothing matching `demonstrate.py` or `serve_sim` should be listed. The retained record
of that episode is `verification/evidence/B6-staleness-halted-counter-attempt-2026-08-06/`.

### Docker does not autostart

**First suspect on any compose failure.** Docker Desktop is not configured to start
with Windows, so a `docker compose` command run after a reboot fails in whatever way
the missing daemon happens to surface — usually a connection error that reads like a
configuration problem rather than a stopped service.

Check before debugging anything else:

```bash
docker info
```

If that errors, start Docker Desktop and wait for the whale icon to settle before
retrying. Nothing else in this runbook will work until it does.

### Credentials and the Redis ACL must be generated together

`WRONGPASS invalid username-password pair` from `openc3-cosmos-cmd-tlm-api` and
`openc3-cosmos-script-runner-api`, both restart-looping.

Redis stores the **sha256** of each password in `openc3-redis/users.acl`; the services
authenticate with the **plaintext** from `.env`. Generate one without the other and they
disagree. Nothing in the compose output says "credentials" — two services simply restart
forever. `tools/setup_ground.py` now writes both from the same values, and
`--check` verifies they still agree.

**After regenerating credentials, recreate the stack** — `docker compose down && docker
compose up -d`. A `restart` leaves the running containers holding the old values.

### Valkey rejects comments in the ACL file

`Aborting Valkey startup because of ACL errors: /config/users.acl:1 should start with
user keyword followed by the username` — repeated for every line.

The ACL file may contain **nothing but `user` lines**. No comments, no blank lines. The
error names every offending line rather than saying "comments are not allowed", which
makes it look like a corrupt file rather than a formatting rule.

The explanation therefore lives in `users.acl.template`, where a reader will find it,
and `setup_ground.py` strips it on the way out.

### `settings-store.json` rename issue

Docker Desktop on this machine has hit a `settings-store.json` rename failure. It
presents as Docker Desktop failing to start or failing to apply settings, not as a
COSMOS problem — so it is easy to chase into the wrong stack. If Docker Desktop itself
will not come up cleanly, treat it as a Docker Desktop fault and resolve it there
before returning to the ground segment.

Recorded so the next occurrence is recognised in seconds rather than diagnosed from
scratch.

## Why the container-side ports are still 2900/2943

Only the **host** side of each mapping is changed. Traefik listens on 2900 and 2943
inside its own network namespace (`openc3-traefik/traefik.yaml` sets `address: ":2900"`),
and upstream's own `NetworkConfiguration.md` is explicit about this: *"modify the first
port number if desired (Note: leave the last :2900)"*. Changing the container side would
break traefik's routing, not relocate the service.

## What the checks cover, and what they do not

**G16 covers** the pin, the port disjointness, the project namespace, demo targets being
off, and the absence of any committed credential. It is hermetic — it reads files only,
so it passes on a machine with Docker stopped, which is the state the check suite will most
often run in.

**G16 does not cover** whether the stack actually comes up. That is a live
demonstration, and it belongs to the Phase 3 acceptance evidence (B6 staleness alarm,
B7 two-step confirmation, B10 digest mismatch no-go, B14 recorded pass played back with
the simulator off), not to a static check.
