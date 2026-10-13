#!/usr/bin/env python3
"""The four Phase 3 demonstrations, each with its negative controls.

    python tools/demonstrate.py b6 b7 b10 b14      run all four
    python tools/demonstrate.py b7                 run one

Every demonstration runs inside `tools/evidence.py` (owner ruling D-008), so its
artifacts are copied into `verification/evidence/<demo>/` at execution time, digested,
and committed. A demonstration that captures nothing raises.

WHY EACH ONE CARRIES A NEGATIVE CONTROL
---------------------------------------
Adversarial review of the first specifications for these four returned HOLLOW on all
four, and the controls below are what survived that review. The shape it kept finding is
the one D-009 already cost this build once: a demonstration whose passing transcript can
be produced with the mechanism under test absent, disconnected, or dead.

  B6   a monitor that has never read the counter used to annunciate GREEN -> YELLOW ->
       RED with textbook spacing on an empty system. So the control is GREEN-HOLD:
       frames flowing for longer than RED_S with no alarm. A dead monitor cannot do
       that, because its clock would pass RED_S regardless. And the halt must be an
       ABSENCE OF FRAMES ON A LIVE LINK, not a link drop, which COSMOS detects by other
       means entirely.

  B7   `cmd_no_hazardous_check` called on its own demonstrates that a bypass exists, not
       that a gate does. Step two must be the RESEND THAT FOLLOWS a caught refusal, with
       the caught error carried into the record. The negative control is a
       non-hazardous command going through unconfirmed on the same link in the same
       state -- otherwise a disconnected interface produces the same non-effect and
       reads exactly like a block.

  B10  reading the repository's CONFIG_ID.txt and comparing it to the repository's
       source is check G9: hermetic, already green, and it passes with Docker stopped.
       The verdict has to be computed from what the INSTANCE holds, and the NO-GO leg
       has to perturb what the instance holds -- with the instance demonstrably alive
       throughout, or "no-go" is indistinguishable from "nothing answered".

  B14  a correct playback is not evidence the native logs were read: COSMOS 7 picks its
       historical source at runtime and may serve from the decom database or an
       in-memory stream. So the log object is named by absolute path and its bytes are
       digested, the simulator is proven off by port and by interface state, and the
       values are compared against what the log itself contains.
"""
import argparse
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ground_config                                              # noqa: E402
import hugdefs                                                    # noqa: E402
import pass_setup                                                 # noqa: E402
import evidence                                                   # noqa: E402
from evidence import Evidence                                     # noqa: E402
from ve import conformance, recorder                            # noqa: E402
from ve.viewer import build as viewer_build                     # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PROJECT = REPO / "gnd" / "openc3"
SIM_PORT = 7801


# --------------------------------------------------------------------------- ground

def _env(name):
    text = (PROJECT / ".env").read_text(encoding="utf-8")
    found = re.search(rf"^{name}=(.*)$", text, re.M)
    if not found:
        raise RuntimeError(f"{name} not set in gnd/openc3/.env")
    return found.group(1).strip()


def _compose_out(args):
    out = subprocess.run(["docker", "compose"] + args, cwd=PROJECT,
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=300)
    if out.returncode != 0:
        raise RuntimeError(f"compose {args[0]} failed: {out.stderr[:300]}")
    return out.stdout


def annunciations_in(text):
    """Staleness level changes found in a raw operator-log slice, in order.

    Module-level and taking TEXT rather than a connection, so the demonstration parses
    the very bytes it archived. A parse that runs against a live query while the
    evidence file is fetched separately is two reads of a moving source, and the
    artifact then only resembles what the verdict was computed from.
    """
    out = []
    for line in text.split("\n"):
        brace = line.find("{")
        if brace < 0:
            continue
        try:
            entry = json.loads(line[brace:])
        except json.JSONDecodeError:
            continue
        msg = str(entry.get("message", ""))
        m = re.search(r"CDH_FRAME_CNT staleness (\w+)", msg)
        if m:
            out.append({"level": m.group(1), "at": entry.get("@timestamp"),
                        "message": msg.strip()})
    return out


def _read_log_script(path):
    """A python -c body that reads `path` with the GROUND SYSTEM's reader.

    **Newline-separated, and that is the whole point of this function existing.**
    The first version of B14's two controls built this by concatenating
    `"...;r=PacketLogReader();"` with `"try:\\n"`, which is a SyntaxError: a compound
    statement cannot follow semicolon-joined simple ones. Both controls therefore
    printed nothing, and both were scored on the ABSENCE of a "PACKETS n" line — so a
    file-bound control that never ran read as `file_bound=True` and B14 was one clause
    away from passing on it. An absence taken for a pass is what D-011 exists about.

    One builder, used by the real read and by both controls, so they cannot drift into
    proving different things.
    """
    return (
        "from openc3.logs.packet_log_reader import PacketLogReader\n"
        "r = PacketLogReader()\n"
        "try:\n"
        f"    pkts = [p for p in r.each({path!r})]\n"
        "    print('PACKETS', len(pkts))\n"
        "    print('TARGET', pkts[0].target_name if pkts else '-')\n"
        "    print('PACKET_NAME', pkts[0].packet_name if pkts else '-')\n"
        "    print('FIRST_LEN', len(pkts[0].buffer) if pkts else 0)\n"
        "except Exception as e:\n"
        "    print('REFUSED', type(e).__name__, e)\n"
    )


def measurements_in(text):
    """`key: value` lines from a measurements artifact, as a dict of strings.

    Deliberately a flat, dull format. The verdict has to be re-derivable by a reader
    holding only the evidence directory, and prose is not re-derivable.
    """
    out = {}
    for line in text.split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key and not key.startswith("#"):
            out[key] = value.strip()
    return out


def b6_verdict(slice_text, measurements_text, since):
    """B6's verdict, computed from ARCHIVED BYTES ALONE. Returns (ok, reasons).

    D-012: *verdict computable from the archived evidence alone; live polls pace but
    never decide.* Before this the verdict read `saw_green`, `saw_yellow`, `saw_red`,
    `froze` and `link_live` -- all booleans returned by `wait_for` against a live
    connection. Those decide when to stop waiting, which is pacing; they were also
    deciding PASS, which is not. A run could therefore report PASS on observations that
    existed nowhere afterwards: the log slice rotated, and the evidence directory held
    nothing anyone could recompute the answer from.

    So the inputs here are the archived operator-log slice and the archived measurements
    file, and nothing else. `since` bounds the slice to this run. A reader holding the
    evidence directory and this function can re-derive PASS or FAIL; if they cannot, the
    evidence did not establish it.

    Pure and module-level so both polarities can be driven from stored text with no
    ground system present -- which is also the only way to red-case a verdict that had
    only ever run against a live one.
    """
    reasons = []
    m = measurements_in(measurements_text)

    transcript = [a for a in annunciations_in(slice_text) if a["at"] and a["at"] > since]
    levels = [a["level"] for a in transcript]

    # The monitor must be seen ENTERING each level, in order, inside this run's window.
    missing = [lvl for lvl in ("GREEN", "YELLOW", "RED") if lvl not in levels]
    for level in missing:
        reasons.append(f"no {level} annunciation in the archived slice")
    if not missing and not (levels.index("GREEN") < levels.index("YELLOW")
                            < levels.index("RED")):
        reasons.append(f"annunciations out of order: {levels}")

    # GREEN-HOLD: frames advanced for longer than RED_S with no alarm. Both halves come
    # from the archive -- the counter readings were recorded into it, and the absence of
    # an alarm is checked against the archived transcript rather than a live query.
    try:
        before = int(m["counter_before_hold"])
        after = int(m["counter_after_hold"])
        hold_s = float(m["hold_s"])
        red_s = float(m["red_s"])
    except (KeyError, ValueError):
        reasons.append("the archived measurements do not carry the GREEN-HOLD readings")
    else:
        if after <= before:
            reasons.append(f"counter did not advance during the hold: {before} -> {after}")
        if hold_s <= red_s:
            reasons.append(f"hold of {hold_s:.0f} s did not exceed RED_S={red_s:.0f} s, "
                           f"so a silent monitor would also have raised no alarm")
        hold_end = m.get("hold_ended_at", "")
        alarmed = [a for a in transcript
                   if a["level"] in ("YELLOW", "RED") and hold_end and a["at"] <= hold_end]
        if alarmed:
            reasons.append(f"alarm during the GREEN-HOLD window: "
                           f"{[a['level'] for a in alarmed]}")

    if m.get("counter_froze", "").lower() != "true":
        reasons.append("the counter was not observed to freeze, so the alarm that "
                       "follows is not attributable to a halt")
    if m.get("interface_state_at_alarm", "") != "CONNECTED":
        reasons.append(f"the link was {m.get('interface_state_at_alarm')!r} at the "
                       f"alarm, so this is not an absence of frames on a live link")

    # READ_FAULT must not appear: it would mean the monitor lost its read path mid-run,
    # and the levels either side of that gap are not one continuous observation (D-012).
    if "READ_FAULT" in levels:
        reasons.append("the monitor annunciated READ_FAULT during the run, so its "
                       "levels do not form one continuous observation")
    return (not reasons), reasons


class Cosmos:
    """The ground system, as the demonstrations talk to it."""

    def __init__(self):
        self.base = f"http://localhost:{_env('OPENC3_EXTERNAL_URL').rsplit(':', 1)[1]}"
        self.token = _env("OPENC3_SERVICE_PASSWORD")

    def api(self, method, params=None, scope="DEFAULT"):
        body = json.dumps({
            "jsonrpc": "2.0", "method": method, "params": params or [],
            "id": 1, "keyword_params": {"scope": scope},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/openc3-api/api", data=body,
            headers={"Authorization": self.token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # COSMOS returns a JSON-RPC error body with a non-2xx status - a refused
            # hazardous command comes back as 409. Raising here would throw away the
            # refusal, which in this demonstration IS the evidence.
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"error": {"message": f"HTTP {exc.code}: {raw[:400]}",
                                  "data": {"class": f"HTTP{exc.code}"}}}

    def call(self, method, params=None):
        """Returns (result, error). Errors are DATA here — a refusal is the evidence."""
        out = self.api(method, params)
        return out.get("result"), out.get("error")

    def tlm(self, item):
        result, error = self.call("tlm", [f"HUGINN HK {item}"])
        if error:
            raise RuntimeError(f"tlm({item}) failed: {error.get('message')}")
        return result

    def interface(self):
        result, error = self.call("get_interface", ["HUGINN_INT"])
        if error:
            raise RuntimeError(f"get_interface failed: {error.get('message')}")
        return result

    def monitor_iterations(self):
        """The STALENESS microservice's own iteration counter, or None.

        A restart resets it, so a small value is how this demonstration knows it is
        looking at a fresh process rather than one that inherited its state.
        """
        try:
            user, password = (ground_config._env("OPENC3_REDIS_USERNAME"),
                              ground_config._env("OPENC3_REDIS_PASSWORD"))
            out = _compose_out(
                ["exec", "-T", "openc3-redis", "sh", "-c",
                 f"redis-cli --user '{user}' --pass '{password}' --no-auth-warning "
                 f"HGET DEFAULT__openc3_microservice_status "
                 f"DEFAULT__USER__OPENC3-HUGINN-STALENESS"])
            return json.loads(out.strip()).get("count")
        except Exception:
            return None

    def raw_message_log(self, files=3):
        """The ground system's own PERSISTED log messages, verbatim.

        Not `docker compose logs`. The operator container's Docker log is capped at
        max-size 10m / max-file 3 (compose.yaml), and a demonstration driving frames at
        10-20x fills that in minutes -- so the run's own annunciations rotate out from
        under it while the run is still going. Measured: an end-of-run fetch returned a
        slice whose newest entry predated the start of the run, having lost the GREEN,
        YELLOW and RED the monitor had emitted in between.

        COSMOS writes the same messages to its log bucket, where they are not subject
        to container log rotation. That is the ground system's record of what it
        annunciated, which is what B6 is about -- and it survives, which is what D-008
        is about.
        """
        listing = _compose_out(
            ["exec", "-T", "openc3-buckets", "sh", "-c",
             "ls -t /data/logs/DEFAULT/text_logs/openc3_log_messages/*/*.txt "
             "2>/dev/null | head -%d" % files])
        paths = [p for p in listing.splitlines() if p.strip()]
        if not paths:
            raise RuntimeError(
                "the ground system has written no message log to its bucket; there is "
                "nothing to read, and a demonstration cannot pass on an absent source")
        # Oldest first, so the concatenation reads forward in time.
        return _compose_out(
            ["exec", "-T", "openc3-buckets", "sh", "-c",
             "cat " + " ".join(reversed(paths))])

    def raw_operator_log(self, window="20m"):
        """The operator container's log from `since`, VERBATIM.

        This is the authoritative source the B6 diagnosis used, and the bytes it
        returns are archived as evidence before anything parses them. A demonstration
        that reads a volatile source and preserves only its conclusion cannot be
        re-examined: when B6's transcript came back empty, the log slice that would
        have settled it had already rotated away.
        """
        # The RELATIVE form ("15m"), not an absolute RFC3339 marker. Both are
        # documented, but on this Docker build an absolute marker close to now
        # returns an empty slice while the relative form over the same span returns
        # tens of kilobytes -- measured side by side, same format, same second. That
        # emptiness is what made B6 report no annunciations across three runs while
        # the monitor was annunciating correctly.
        #
        # A coarse window is the safe direction to be wrong in: the caller filters
        # exactly, by the log's own @timestamp, so an over-wide slice costs nothing
        # and an over-narrow one loses the evidence.
        out = subprocess.run(
            ["docker", "compose", "logs", "openc3-operator", "--no-log-prefix",
             "--since", window],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300)
        if out.returncode != 0:
            raise RuntimeError(f"could not read the operator log: {out.stderr[:300]}")
        return out.stdout

    def operator_log(self, since=None, tail=3000):
        """Structured log lines from the operator container, newest last.

        Bounded by TIME when a start is known, not by line count. `--tail N` is a
        window that slides on VOLUME: during a demonstration at 20x frame rate the
        operator emits thousands of lines, and the handful this demonstration cares
        about get pushed out from underneath it. That is not a hypothetical — B6
        reported no annunciations at all across two runs while the monitor was
        annunciating GREEN, YELLOW and RED correctly the whole time.
        """
        args = ["docker", "compose", "logs", "openc3-operator", "--no-log-prefix"]
        args += ["--since", since] if since else ["--tail", str(tail)]
        out = subprocess.run(
            args, cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180)
        entries = []
        for line in out.stdout.split("\n"):
            brace = line.find("{")
            if brace < 0:
                continue
            try:
                entries.append(json.loads(line[brace:]))
            except json.JSONDecodeError:
                continue
        return entries

    def live_annunciations(self, since):
        """Staleness levels from the LIVE container log. **For pacing only (D-012).**

        The two log sources have opposite faults and the demonstration needs both.

        The bucket log is DURABLE but LAGGING: COSMOS flushes messages to it on a
        cycle, so a level emitted a second ago is not in it yet. The container log is
        PROMPT but PERISHABLE: capped at 10m/3 files, it rotates the run's own lines
        away while the run is still going (OF-007).

        Pacing needs promptness — it only decides when to stop waiting. The verdict
        needs durability, and takes the bucket log. Wiring pacing to the durable source
        cost a measured 181 s of waiting for a GREEN that the monitor had already
        emitted and the bucket had not yet received; the run then reached its GREEN-HOLD
        after the scenario's halt had latched, and failed on a control that never had a
        chance to hold.

        Filtered by TIMESTAMP, never by position: `--tail N` slides on volume, and at
        demonstration frame rates the handful of lines this cares about are pushed out
        from under it.
        """
        return [a for a in annunciations_in("\n".join(
                    json.dumps(e) for e in self.operator_log(since=since)))
                if a["at"] and a["at"] > since]

    def staleness_annunciations(self, since=None):
        """Staleness level changes as the DURABLE record holds them.

        This is the deciding source: what the ground system persisted, not what its
        container log happened to still be holding. Use :meth:`live_annunciations` to
        pace a wait; use this, or better the archived bytes, to conclude anything.
        """
        if since is not None:
            return [a for a in annunciations_in(self.raw_message_log())
                    if a["at"] and a["at"] > since]
        out = []
        for e in self.operator_log():
            msg = str(e.get("message", ""))
            m = re.search(r"CDH_FRAME_CNT staleness (\w+)", msg)
            if m:
                out.append({"level": m.group(1), "at": e.get("@timestamp"),
                            "message": msg.strip()})
        return out

    @staticmethod
    def now_stamp():
        """A marker usable both as a `docker compose logs --since` bound and as a
        lexicographic cut against the log's own @timestamp field.

        Host and container clocks were measured equal before relying on this. A few
        seconds are given back so a line stamped either side of the boundary is kept
        rather than silently dropped -- the filter below is exact, so an over-wide
        window costs nothing and an over-narrow one loses evidence."""
        from datetime import datetime, timedelta, timezone
        return ((datetime.now(timezone.utc) - timedelta(seconds=3))
                .strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z")


def sim_port_open():
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", SIM_PORT)) == 0


class Sim:
    """The simulator, run as a subprocess for the length of a demonstration."""

    def __init__(self, scenario, rate=1.0):
        self.scenario, self.rate = scenario, rate
        self.proc = None
        self.log = []

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, str(REPO / "tools" / "serve_sim.py"), self.scenario,
             "--rate", str(self.rate)],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        for _ in range(60):
            if sim_port_open():
                return self
            time.sleep(0.5)
        raise RuntimeError("the simulator did not start serving")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:      # pragma: no cover
                self.proc.kill()
        for _ in range(40):
            if not sim_port_open():
                break
            time.sleep(0.5)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def wait_for(predicate, timeout, poll=1.0, what=""):
    """Poll until true. Returns (ok, elapsed)."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            if predicate():
                return True, time.monotonic() - start
        except Exception:
            pass
        time.sleep(poll)
    return False, time.monotonic() - start


def connected(cosmos):
    try:
        return cosmos.interface().get("state") == "CONNECTED"
    except Exception:
        return False


# ------------------------------------------------------------------------------ B6

def demo_b6():
    """The staleness alarm fires on a halted counter — and cannot fire on nothing."""
    cosmos = Cosmos()
    with Evidence("B6-staleness-halted-counter", obligation="B6",
                  requirement="HUG-GND-002",
                  description="Ground-side derived staleness monitor annunciates "
                              "YELLOW at 10 s and RED at 30 s of no-advance, on a live "
                              "link, and holds GREEN while frames flow.") as ev:
        # P4 latches the generation halt at scenario t = 1200 s. The monitor's
        # thresholds are WALL time, so the rate is chosen to put the fault about a
        # minute out: long enough for the GREEN-HOLD control to complete on flowing
        # frames first, short enough that the demonstration is minutes rather than
        # half an hour. Nothing about the scenario is altered — only when it is read.
        with Sim("P4_hk_generation_halt", rate=10.0) as sim:
            ok, _ = wait_for(lambda: connected(cosmos), 90, what="interface connect")
            if not ok:
                ev.record("FAIL", "the interface never connected; nothing below would "
                                  "mean anything")
                return False

            # --- Start the monitor from a KNOWN state.
            # The monitor annunciates only on level CHANGE, so what it says depends on
            # what it inherited. Worse, a long-lived monitor can latch: if its reads
            # begin failing after a dependency restart, the except-branch swallows that,
            # and because it HAS read successfully at some point the NO_READ guard does
            # not apply — it sits in RED forever, silently. A 23-hour-old process was
            # doing exactly that while a freshly started one annunciated GREEN within
            # seconds on the same live telemetry (OF-006).
            #
            # Restarting it here is not tidying up. It is what makes the GREEN below an
            # OBSERVATION rather than an inheritance, and it is the only way this
            # demonstration can say the monitor was alive when the halt arrived.
            since = cosmos.now_stamp()
            ground_config._compose(
                ["exec", "-T", "openc3-operator", "sh", "-c",
                 "pkill -f frame_staleness.py"])

            # --- CONTROL: the monitor must ENTER GREEN inside this window.
            # A monitor that is dead, latched, or unable to read cannot do this. It is
            # the liveness proof the earlier runs lacked: they inherited whatever state
            # the process happened to hold and could not tell a working monitor from a
            # silent one.
            # PACING ONLY (D-012): the live container log, because it is prompt.
            # Whether the run PASSES is decided later from the archived bucket log.
            saw_green, t_green = wait_for(
                lambda: any(a["level"] == "GREEN"
                            for a in cosmos.live_annunciations(since)),
                180, poll=3.0, what="monitor enters GREEN")
            ev.capture_text(
                "green-entry.txt",
                f"monitor restarted at {since}\n"
                f"entered GREEN within window: {saw_green} "
                f"(after {t_green:.0f} s)\n"
                f"annunciations so far (live source, pacing): "
                f"{[a['level'] for a in cosmos.live_annunciations(since)]}\n",
                note="CONTROL: the monitor was restarted and observed ENTERING GREEN on "
                     "live telemetry inside this run's window. A dead, latched or "
                     "unreadable monitor cannot produce this, so every level that "
                     "follows is emitted by a monitor known to be reading.")

            # --- CONTROL: GREEN-HOLD. Frames flowing longer than RED_S with no alarm.
            # A monitor that cannot read the counter is incapable of this: its clock
            # runs from process start and passes RED_S regardless.
            red_s = 30
            hold_s = red_s + 8
            t0 = time.monotonic()
            first_cnt = cosmos.tlm("CDH_FRAME_CNT")
            time.sleep(hold_s)
            last_cnt = cosmos.tlm("CDH_FRAME_CNT")
            # Stamped so the verdict can bound the GREEN-HOLD window in the ARCHIVED
            # transcript, rather than trusting a live query made at this moment.
            hold_ended_at = cosmos.now_stamp()
            during_hold = cosmos.live_annunciations(since)
            alarmed = [a for a in during_hold if a["level"] in ("YELLOW", "RED")]
            green_hold_ok = (last_cnt > first_cnt) and not alarmed
            ev.capture_text(
                "green-hold.txt",
                f"held {hold_s:.0f} s (RED_S={red_s})\n"
                f"CDH_FRAME_CNT {first_cnt} -> {last_cnt}\n"
                f"alarms during hold: {alarmed}\n"
                f"annunciations during hold: {during_hold}\n",
                note="CONTROL: frames advancing for longer than RED_S with no alarm. "
                     "A monitor that never reads the counter cannot produce this.")

            # --- the halt. The fault suppresses generation; the LINK STAYS UP.
            # Wait until the counter actually stops advancing, so what follows is
            # measured from the real onset rather than from when we asked.
            def counter_frozen():
                first = cosmos.tlm("CDH_FRAME_CNT")
                time.sleep(3)
                return cosmos.tlm("CDH_FRAME_CNT") == first

            froze, _ = wait_for(counter_frozen, 240, poll=2.0, what="generation halt")
            state_at_halt = cosmos.interface().get("state")

            saw_yellow, t_yellow = wait_for(
                lambda: any(a["level"] == "YELLOW"
                            for a in cosmos.live_annunciations(since)),
                180, what="YELLOW")
            saw_red, t_red = wait_for(
                lambda: any(a["level"] == "RED"
                            for a in cosmos.live_annunciations(since)),
                180, what="RED")

            iface = cosmos.interface()
            link_live = iface.get("state") == "CONNECTED"

            # --- ARCHIVE THE SOURCE, THEN PARSE THE ARCHIVE.
            # One read of the operator log, bounded by time, saved verbatim before
            # anything interprets it — and the transcript below is parsed out of those
            # same bytes. The previous version parsed a live query and would have
            # written a separate summary file, so the artifact only resembled what the
            # verdict was computed from. When the transcript came back empty there was
            # nothing to re-examine, and the slice that would have settled it had
            # rotated away by the time anyone looked.
            # --- WAIT FOR THE DECIDING SOURCE TO CATCH UP BEFORE READING IT.
            # The live log told us GREEN, YELLOW and RED were emitted; the bucket log is
            # where the verdict reads them, and COSMOS flushes to it on a cycle. Reading
            # it the instant RED appeared live is a race: the same run returns PASS when
            # the flush has landed and INSTRUMENT_FAULT when it has not, which is what
            # the confirming run of this build did.
            #
            # This is still pacing, not deciding. It waits for the durable record to be
            # complete; what that record then says is the verdict's business. If the
            # flush never arrives the wait times out, the transcript is short, and the
            # INSTRUMENT_FAULT below is the correct outcome rather than a coin toss.
            def archive_has_all_three():
                got = {a["level"] for a in annunciations_in(cosmos.raw_message_log())
                       if a["at"] and a["at"] > since}
                return {"GREEN", "YELLOW", "RED"} <= got

            archived_ok, t_archive = wait_for(archive_has_all_three, 180, poll=5.0,
                                              what="bucket log catches up")
            raw = cosmos.raw_message_log()
            ev.capture_text(
                "operator-log-slice.txt", raw,
                note="THE SOURCE. The ground system's own persisted message log, "
                     "verbatim and unfiltered. Every claim below is parsed out of "
                     "this file, so a reader can re-derive the transcript rather than "
                     "take it on report.")
            transcript = [a for a in annunciations_in(raw)
                          if a["at"] and a["at"] > since]
            ev.capture_text(
                "annunciations.txt",
                "\n".join(f"{a['at']}  {a['level']}  {a['message']}"
                          for a in transcript) + "\n",
                note="the staleness level changes parsed from operator-log-slice.txt")
            ev.capture_text(
                "halt-fidelity.txt",
                f"interface state at halt onset: {state_at_halt}\n"
                f"interface state at the alarm: {iface.get('state')}\n"
                f"rxcnt: {iface.get('rxcnt')}  txcnt: {iface.get('txcnt')}\n"
                f"counter froze: {froze}\n"
                f"saw YELLOW: {saw_yellow}  saw RED: {saw_red}\n",
                note="CONTROL: the alarm fired while the interface was CONNECTED, so "
                     "this is an absence of frames on a live link — not a link drop, "
                     "which COSMOS detects by other means.")
            ev.capture_file(REPO / "sim" / "scenarios" / "P4_hk_generation_halt.yaml",
                            note="the scenario whose fault suppresses generation")

            levels = [a["level"] for a in transcript]
            ev.note(f"annunciation order: {levels}")
            ev.note(f"GREEN-HOLD held: {green_hold_ok}; link live at alarm: {link_live}")

            # --- Did the INSTRUMENT work, or did the SUBJECT fail?
            # An empty slice, or a slice carrying no annunciation of any kind, means
            # the collection path returned nothing — which says nothing about the
            # monitor. Calling that FAIL would assert something about a subject this
            # run never observed.
            if not raw.strip() or not transcript:
                ev.record("INSTRUMENT_FAULT",
                          f"the operator-log slice for this run "
                          f"({len(raw)} bytes) carried no staleness annunciation of "
                          f"any level, so the monitor's behaviour was not observed. "
                          f"GREEN-HOLD held={green_hold_ok}, counter froze={froze}, "
                          f"link live={link_live} — the run itself proceeded, but the "
                          f"collection did not. B6 is neither discharged nor refuted.")
                return False

            # --- THE VERDICT'S INPUTS, ARCHIVED BEFORE THE VERDICT IS TAKEN.
            # Everything the verdict needs and cannot parse out of the log slice goes
            # here, in a flat re-derivable format. The live booleans above (`saw_green`,
            # `saw_yellow`, `saw_red`, `froze`) paced the run -- they decided when to
            # stop waiting -- and from here on they decide nothing (D-012).
            ev.capture_text(
                "measurements.txt",
                f"# B6 verdict inputs. The verdict is computed from THIS file and the\n"
                f"# archived operator-log slice, and from nothing live.\n"
                f"monitor_restarted_at: {since}\n"
                f"counter_before_hold: {first_cnt}\n"
                f"counter_after_hold: {last_cnt}\n"
                f"hold_s: {hold_s:.1f}\n"
                f"red_s: {red_s}\n"
                f"hold_ended_at: {hold_ended_at}\n"
                f"archive_caught_up: {archived_ok} (after {t_archive:.0f} s)\n"
                f"counter_froze: {froze}\n"
                f"interface_state_at_halt: {state_at_halt}\n"
                f"interface_state_at_alarm: {iface.get('state')}\n"
                f"rxcnt: {iface.get('rxcnt')}\n"
                f"txcnt: {iface.get('txcnt')}\n",
                note="THE VERDICT'S OTHER INPUT. Everything the verdict needs that is "
                     "not in the log slice, recorded before the verdict is taken so a "
                     "reader can recompute PASS or FAIL from this directory alone.")

            # Read both inputs BACK OFF DISK. If a capture silently failed, the verdict
            # cannot be computed and the run must not report on a subject it did not
            # archive.
            ok, reasons = b6_verdict(ev.archived("operator-log-slice.txt"),
                                     ev.archived("measurements.txt"),
                                     since)
            ev.note("verdict computed from artifacts/operator-log-slice.txt and "
                    "artifacts/measurements.txt; live polls paced the run only")
            if ok:
                ev.record("PASS",
                          f"monitor restarted and observed entering GREEN on live "
                          f"telemetry, then held GREEN for {hold_s:.0f} s with the "
                          f"counter advancing ({first_cnt} -> {last_cnt}) and no alarm, "
                          f"then annunciated YELLOW and RED in order on a CONNECTED link "
                          f"once generation halted. Every clause re-derived from the "
                          f"archived slice and measurements, not from the live polls.")
            else:
                ev.record("FAIL", "; ".join(reasons))
            return ok


# ------------------------------------------------------------------------------ B7

def demo_b7():
    """Two-step confirmation: step one is refused, step two is the resend after it."""
    cosmos = Cosmos()
    with Evidence("B7-hazardous-two-step", obligation="B7",
                  requirement="HUG-CMD-001",
                  description="A hazardous command is refused unconfirmed and accepted "
                              "only on the resend that follows the refusal, while a "
                              "non-hazardous command goes through on the same link.") \
            as ev:
        with Sim("P1_nominal", rate=5.0):
            ok, _ = wait_for(lambda: connected(cosmos), 90)
            if not ok:
                ev.record("FAIL", "the interface never connected")
                return False

            # A disconnected interface refuses everything and reads exactly like a
            # block, so the link state is recorded with every leg.
            iface_before = cosmos.interface()

            # --- CONTROL: a NON-hazardous command, same link, same state, unconfirmed.
            mode_before = cosmos.tlm("EPS_MODE")
            rate_result, rate_error = cosmos.call(
                "cmd", ["HUGINN", "CMD_PLD_SET_RATE", {"rate": 2.0}])
            control_ok = rate_error is None and rate_result is not None

            # --- STEP ONE: the hazardous command, unconfirmed. Must be REFUSED, and
            # refused for BEING HAZARDOUS rather than for any other reason.
            step1_result, step1_error = cosmos.call(
                "cmd", ["HUGINN", "CMD_SAFE_ENTER"])
            refused = step1_error is not None
            right_reason = refused and (
                step1_error.get("data", {}).get("class") == "HazardousError")
            mode_after_step1 = cosmos.tlm("EPS_MODE")

            # --- STEP TWO: the resend that FOLLOWS the caught refusal. Not a bypass
            # called in isolation — the confirmation is the operator acting on the
            # error above, and that error is carried into the record here.
            step2_result, step2_error = (None, None)
            if refused:
                step2_result, step2_error = cosmos.call(
                    "cmd_no_hazardous_check", ["HUGINN", "CMD_SAFE_ENTER"])
            accepted = step2_error is None and step2_result is not None

            # Effect asserted as a TRANSITION, not a state: P1_nominal starts NOMINAL
            # and a mode command to the mode you are already in is a no-op, so "mode
            # is X" proves nothing (OF-004).
            moved, _ = wait_for(lambda: cosmos.tlm("EPS_MODE") == "SAFE", 60)
            mode_after_step2 = cosmos.tlm("EPS_MODE")
            iface_after = cosmos.interface()

            ev.capture_text(
                "step-one-refusal.json",
                json.dumps(step1_error, indent=2) + "\n",
                note="STEP ONE: the unconfirmed hazardous command, refused. The error "
                     "class must be HazardousError — a disconnected interface also "
                     "refuses, and would read exactly like a block.")
            ev.capture_text(
                "step-two-acceptance.json",
                json.dumps({"result": step2_result, "error": step2_error}, indent=2)
                + "\n",
                note="STEP TWO: the resend performed AFTER the refusal above was "
                     "caught. Called on its own it would demonstrate that a bypass "
                     "exists, not that a gate does.")
            ev.capture_text(
                "non-hazardous-control.json",
                json.dumps({"result": rate_result, "error": rate_error}, indent=2)
                + "\n",
                note="CONTROL: a NON-hazardous command on the same link in the same "
                     "state is accepted unconfirmed. This is what distinguishes a "
                     "hazardous gate from a dead uplink.")
            ev.capture_text(
                "effect.txt",
                f"EPS_MODE before        : {mode_before}\n"
                f"EPS_MODE after step one: {mode_after_step1}   (must be unchanged)\n"
                f"EPS_MODE after step two: {mode_after_step2}   (must be SAFE)\n"
                f"transition observed    : {mode_before} -> {mode_after_step2}\n"
                f"interface before       : {iface_before.get('state')} "
                f"txcnt={iface_before.get('txcnt')}\n"
                f"interface after        : {iface_after.get('state')} "
                f"txcnt={iface_after.get('txcnt')}\n",
                note="The effect is a TRANSITION. P1_nominal starts NOMINAL and a mode "
                     "command to the current mode is a no-op, so a state assertion "
                     "would be satisfied whether or not anything was blocked.")
            ev.capture_file(
                REPO / "gnd/openc3/plugins/openc3-cosmos-huginn/targets/HUGINN"
                / "cmd_tlm/cmd.txt",
                note="the generated command definition carrying HAZARDOUS, whose "
                     "reason text appears verbatim in the refusal above")

            blocked_effect = mode_after_step1 == mode_before
            ok = (control_ok and refused and right_reason and blocked_effect
                  and accepted and moved and mode_after_step2 == "SAFE"
                  and iface_after.get("state") == "CONNECTED")
            ev.note(f"control accepted unconfirmed: {control_ok}")
            ev.note(f"step one refused as HazardousError: {right_reason}")
            ev.note(f"step two accepted after the refusal: {accepted}")
            if ok:
                ev.record("PASS",
                          f"unconfirmed hazardous command refused as HazardousError "
                          f"with no effect; the resend after that refusal was accepted "
                          f"and moved EPS_MODE {mode_before} -> {mode_after_step2}; a "
                          f"non-hazardous command went through unconfirmed on the same "
                          f"link")
            else:
                ev.record("FAIL",
                          f"control={control_ok} refused={refused} "
                          f"reason={right_reason} no_effect={blocked_effect} "
                          f"accepted={accepted} moved={moved}")
            return ok


# ----------------------------------------------------------------------------- B10

def demo_b10():
    """Pass setup returns GO on the configuration of record and NO-GO on drift."""
    cosmos = Cosmos()
    with Evidence("B10-config-mismatch-no-go", obligation="B10",
                  requirement="HUG-GND-006",
                  description="PROC-001's pre-pass step verifies the loaded "
                              "configuration and returns GO; a perturbation of what "
                              "the INSTANCE holds returns NO-GO, with the instance "
                              "alive throughout.") as ev:
        # --- GO leg
        go, go_lines = pass_setup.run("DEMO-B10-GO", record=False)
        ev.capture_text("go-leg.md", "\n".join(go_lines) + "\n",
                        note="the pre-pass step against the configuration of record")

        # --- liveness inside the NO-GO window. "NO-GO" and "nothing answered" must be
        # distinguishable, so the instance is shown alive at the moment it says NO-GO.
        alive_before = {"targets": ground_config._compose(
            ["ps", "--services", "--filter", "status=running"]).stdout.split()}

        # --- NO-GO leg. Perturb what the INSTANCE holds, not the working tree: the
        # verdict must be computed from the loaded configuration, and a repository-side
        # edit would be a comparison of the working tree with itself.
        target = ("/data/config/DEFAULT/targets/HUGINN/cmd_tlm/tlm.txt")
        # The backup lives on the HOST. /tmp inside the buckets container is a
        # read-only filesystem, and more to the point a restore that depends on the
        # perturbed system still being writable is a restore that can fail exactly
        # when it is needed. This demonstration must not be able to leave the
        # instance perturbed.
        backup = REPO / "verification" / "evidence" / "_b10_tlm_backup.txt"
        backup.parent.mkdir(parents=True, exist_ok=True)
        perturbed = False
        try:
            saved = subprocess.run(
                ["docker", "compose", "cp", f"openc3-buckets:{target}", str(backup)],
                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=180)
            if saved.returncode != 0 or not backup.exists():
                ev.record("FAIL", f"could not back up the loaded configuration before "
                                  f"perturbing it: {saved.stderr.strip()}")
                return False
            out = ground_config._compose(
                ["exec", "-T", "openc3-buckets", "sh", "-c",
                 f"printf '# perturbation injected by the B10 demonstration\\n' "
                 f">> {target} && echo PERTURBED"])
            perturbed = "PERTURBED" in out.stdout
            if not perturbed:
                ev.record("FAIL", f"could not perturb the loaded configuration: "
                                  f"{out.stderr.strip() or out.stdout.strip()}")
                return False
            nogo, nogo_lines = pass_setup.run("DEMO-B10-NOGO", record=False)
            alive_during = ground_config._compose(
                ["ps", "--services", "--filter", "status=running"]).stdout.split()
            ev.capture_text("nogo-leg.md", "\n".join(nogo_lines) + "\n",
                            note="the same step with the INSTANCE's copy of tlm.txt "
                                 "perturbed by one appended line")
            ev.capture_text(
                "liveness.txt",
                f"services running before: {sorted(alive_before['targets'])}\n"
                f"services running during NO-GO: {sorted(alive_during)}\n"
                f"interface state during NO-GO: {cosmos.interface().get('state')}\n",
                note="CONTROL: the instance is alive at the moment it returns NO-GO, "
                     "so the verdict is a comparison result and not the silence of a "
                     "dead system.")
        finally:
            if perturbed:
                subprocess.run(
                    ["docker", "compose", "cp", str(backup),
                     f"openc3-buckets:{target}"],
                    cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=180)
            if backup.exists():
                backup.unlink()

        restored, restored_lines = pass_setup.run("DEMO-B10-RESTORED", record=False)
        ev.capture_text("restored-leg.md", "\n".join(restored_lines) + "\n",
                        note="FM-GND-04 note (e): the mismatch response reloads and "
                             "re-runs this same step, which must return GO again")

        ok = go and not nogo and restored
        ev.note(f"GO leg: {go}; NO-GO leg returned no-go: {not nogo}; "
                f"restored: {restored}")
        ev.note("The no-go is procedural (D-010): the tool arms no command inhibit, "
                "and says so in its own output.")
        if ok:
            ev.record("PASS",
                      "the pre-pass step returned GO on the configuration of record, "
                      "NO-GO when the instance's own copy was perturbed by one line "
                      "while the instance stayed alive, and GO again once restored")
        else:
            ev.record("FAIL", f"go={go} nogo_detected={not nogo} restored={restored}")
        return ok


# ----------------------------------------------------------------------------- B14

def demo_b14():
    """A recorded pass replays from the ground system's own native log, simulator off."""
    cosmos = Cosmos()
    with Evidence("B14-native-log-playback", obligation="B14",
                  requirement="HUG-SYS-006",
                  description="Telemetry recorded during a pass is recoverable from "
                              "the ground system's native log after the simulator is "
                              "stopped.") as ev:
        # --- record a pass
        with Sim("P1_nominal", rate=5.0):
            ok, _ = wait_for(lambda: connected(cosmos), 90)
            if not ok:
                ev.record("FAIL", "the interface never connected; nothing was recorded")
                return False
            start_cnt = cosmos.tlm("CDH_FRAME_CNT")
            time.sleep(45)
            end_cnt = cosmos.tlm("CDH_FRAME_CNT")
            last_met = cosmos.tlm("CDH_MET")
            last_soc = cosmos.tlm("EPS_BATT_SOC")

        # --- the simulator is OFF. Proven two ways, not asserted.
        port_closed = not sim_port_open()
        iface_state, _ = wait_for(
            lambda: cosmos.interface().get("state") != "CONNECTED", 90)
        state_now = cosmos.interface().get("state")
        ev.capture_text(
            "simulator-off.txt",
            f"TCP {SIM_PORT} accepting connections: {sim_port_open()}\n"
            f"HUGINN_INT state: {state_now}\n"
            f"last CDH_FRAME_CNT seen live: {end_cnt}\n",
            note="CONTROL: the source is gone by two independent observables — the "
                 "port refuses connections and the ground system's own interface is "
                 "no longer CONNECTED. A screenshot of a frozen display would show "
                 "the same values whether or not anything was replayed.")

        # --- the log objects, named by absolute path and digested. A demo that globs
        # for "a HUGINN log" and finds frames has bound to nothing.
        listing = ground_config._compose(
            ["exec", "-T", "openc3-buckets", "sh", "-c",
             "ls -1 /data/logs/DEFAULT/raw_logs/tlm/HUGINN/*/*.bin.gz 2>/dev/null | "
             "tail -3"])
        objects = [p for p in listing.stdout.split("\n") if p.strip()]
        if not objects:
            ev.record("FAIL", "the ground system wrote no native telemetry log for the "
                              "pass; there is nothing to play back")
            return False
        digests = ground_config._compose(
            ["exec", "-T", "openc3-buckets", "sh", "-c",
             "; ".join(f'sha256sum "{p}"' for p in objects)])
        ev.capture_text(
            "log-objects.txt",
            f"{listing.stdout}\n{digests.stdout}\n",
            note="the specific native log objects this playback reads, by absolute "
                 "path and digest. TLM_LOG_CYCLE_TIME is 300 s so a real pass spans "
                 "more than one object.")

        # --- copy the newest object out and archive it as evidence
        newest = objects[-1]
        local = REPO / "verification" / "evidence" / "_b14_tmp.bin.gz"
        local.parent.mkdir(parents=True, exist_ok=True)
        cp = subprocess.run(
            ["docker", "compose", "cp",
             f"openc3-buckets:{newest}", str(local)],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180)
        if cp.returncode != 0 or not local.exists():
            ev.record("FAIL", f"could not retrieve the native log object: {cp.stderr}")
            return False
        ev.capture_file(local, name="ground-native-telemetry.bin.gz",
                        note="the ground system's own native raw telemetry log for the "
                             "recorded pass, preserved at execution time (D-008)")

        # The log lives in the BUCKETS container; the ground system's reader lives in
        # the OPERATOR container, which does not mount that volume. So the archived
        # bytes are copied in and read there — which also means the bytes played back
        # are exactly the bytes preserved as evidence, not another fetch of a moving
        # source.
        in_operator = "/tmp/b14-native-telemetry.bin.gz"
        push = subprocess.run(
            ["docker", "compose", "cp", str(local),
             f"openc3-operator:{in_operator}"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180)
        local.unlink()
        if push.returncode != 0:
            ev.record("FAIL", f"could not stage the log for playback: {push.stderr}")
            return False

        # --- read it back with the GROUND SYSTEM's reader, not this repository's codec.
        # Decoding the log with sim/interface.py's FrameCodec would prove the repo can
        # read its own format and nothing about the ground system.
        # /openc3/python/.venv/bin/python, not `python`. The container's default
        # interpreter has no openc3 package, and the ModuleNotFoundError it raises
        # reads as "the log could not be played back" rather than "the wrong Python
        # was asked". The staleness monitor cost this build the same confusion once.
        VENV = "/openc3/python/.venv/bin/python"

        # --- DECOMPRESS FIRST. PacketLogReader does not do it for you.
        # Measured, both ways, on the same object: pointed at the `.bin.gz` it raises
        # `ValueError: OpenC3 file header not found`; pointed at the gunzipped bytes it
        # returns 1108 HUGINN HK packets. It reads the gzip magic, does not find the
        # `COSMOS5_` header, and refuses. So the header read was never broken — it was
        # being handed compressed bytes. The bucket stores `.bin.gz`; the reader wants
        # the file.
        #
        # The evidence chain is preserved rather than shortened: the object is copied
        # out of the bucket, archived AS RETRIEVED in its compressed form, pushed in,
        # and decompressed HERE — so the bytes read are derived from the archived bytes
        # and both digests are recorded below.
        decompressed = in_operator[:-3]      # strip .gz
        gunzip = ground_config._compose(
            ["exec", "-T", "openc3-operator", "sh", "-c",
             f"gunzip -kf '{in_operator}' && "
             f"sha256sum '{in_operator}' '{decompressed}' && "
             f"head -c 8 '{decompressed}'"])
        ev.capture_text(
            "decompression.txt",
            f"the bucket stores the native log gzipped; the ground system's reader "
            f"does not decompress.\n\n"
            f"gunzip -kf {in_operator}\n\n"
            f"stdout:\n{gunzip.stdout}\nstderr:\n{gunzip.stderr[:600]}\n",
            note="THE CHAIN: sha256 of the archived .bin.gz and of the decompressed "
                 "bytes actually read, plus the first 8 bytes showing the COSMOS5_ "
                 "header the reader looks for. The digest of the .gz here must match "
                 "ground-native-telemetry.bin.gz in this same directory.")

        read = ground_config._compose(
            ["exec", "-T", "openc3-operator", VENV, "-c",
             _read_log_script(decompressed)])
        ev.capture_text("playback.txt",
                        f"read: {decompressed}\n"
                        f"stdout:\n{read.stdout}\nstderr:\n{read.stderr}\n",
                        note="the log read back by the GROUND SYSTEM's own reader "
                             "inside the operator container, with the simulator off")

        # --- CONTROL: the SAME reader refuses the COMPRESSED object.
        # Without this the decompression step above is an unexplained ritual: a reader
        # that accepted both would make the gunzip a no-op nobody could tell had
        # mattered. The refusal is the evidence that the archived form and the readable
        # form are different things, and which one the reader needs.
        gz_read = ground_config._compose(
            ["exec", "-T", "openc3-operator", VENV, "-c",
             _read_log_script(in_operator)])
        # The reader must be seen REFUSING, and no packets returned. Scoring on the
        # absence of a "PACKETS" line alone is what let a control that never compiled
        # read as a pass.
        gz_refused = ("REFUSED" in gz_read.stdout
                      and not re.search(r"PACKETS (\d+)", gz_read.stdout))
        ev.capture_text(
            "compressed-refused.txt",
            f"the same reader, same container, pointed at the COMPRESSED object:\n"
            f"  {in_operator}\n\n"
            f"stdout:\n{gz_read.stdout}\nstderr:\n{gz_read.stderr[:400]}\n\n"
            f"refused: {gz_refused} (must be True)\n",
            note="CONTROL: PacketLogReader does not decompress. It refuses the .bin.gz "
                 "with 'OpenC3 file header not found' — the gzip magic is not the "
                 "COSMOS5_ header. This is why the playback reads the decompressed "
                 "bytes, and it is the finding that unblocked B14.")

        # --- OF-005 CONTROL: prove the read is FILE-BOUND, not database-backed.
        # COSMOS 7 chooses its historical source at runtime — decommutated items come
        # from the time-series database and recent raw packets can be served from an
        # in-memory stream — so packets coming back is not evidence the native log was
        # read. The same reader, same container, same call, pointed at a path that does
        # not exist must produce NOTHING. If it still returns packets, they were coming
        # from somewhere other than the file named above and this demonstration proves
        # nothing about B14.
        bogus = in_operator.replace(".bin.gz", ".NOT-A-REAL-LOG.bin.gz")
        control = ground_config._compose(
            ["exec", "-T", "openc3-operator", VENV, "-c",
             _read_log_script(bogus)])
        control_played = re.search(r"PACKETS (\d+)", control.stdout)
        control_count = int(control_played.group(1)) if control_played else 0
        # The reader must be seen REFUSING, not merely seen saying nothing. This control
        # previously scored a SyntaxError as a pass: the script never compiled, printed
        # nothing, and "no PACKETS line" was read as "the reader returned no packets".
        file_bound = control_count == 0 and "REFUSED" in control.stdout
        ev.capture_text(
            "of005-file-bound-control.txt",
            f"the same reader, same container, pointed at a path that does not exist:\n"
            f"  {bogus}\n\n"
            f"stdout:\n{control.stdout}\nstderr:\n{control.stderr[:600]}\n\n"
            f"packets returned: {control_count} (must be 0)\n",
            note="OF-005 CONTROL: a database-backed read would still return packets "
                 "for a bad path. Returning none proves the playback above was bound "
                 "to the named native log file.")

        played = re.search(r"PACKETS (\d+)", read.stdout)
        count = int(played.group(1)) if played else 0
        target_ok = "TARGET HUGINN" in read.stdout
        ok = bool(port_closed and iface_state and count > 0 and target_ok
                  and file_bound and gz_refused)
        ev.note(f"frames recorded live: {end_cnt - start_cnt}; packets read back: "
                f"{count}")
        ev.note(f"simulator port closed: {port_closed}; interface state: {state_now}")
        if ok:
            ev.record("PASS",
                      f"{count} packet(s) recovered from the ground system's own "
                      f"native log by its own reader, with the simulator stopped "
                      f"(port closed, interface {state_now})")
        else:
            ev.record("FAIL",
                      f"port_closed={port_closed} disconnected={iface_state} "
                      f"packets={count} target_ok={target_ok} file_bound={file_bound} "
                      f"compressed_refused={gz_refused}")
        return ok




# ----------------------------------------------------------------------------- B14

#: A control that ran and observed nothing writes this; a control that never ran
#: cannot. OF-008's whole defect was that the two were indistinguishable, because
#: both controls were scored on `count == 0` and a script that died of a SyntaxError
#: produces the same zero as a reader that ran and refused a bad path.
_REFUSED = re.compile(r"^REFUSED\s+(\w+)\b(.*)$", re.MULTILINE)


def b14_verdict(playback_text, simulator_off_text, decompression_text,
                of005_text, compressed_text, archived_gz_sha256):
    """B14's verdict, computed from ARCHIVED BYTES ALONE (D-012). (ok, reasons).

    Written under D-013 item 1 to close OF-012: B6 and B11 each had a verdict that
    re-derives its demonstration from the archive under executed red and green cases,
    and B14 — the obligation that discharges HUG-SYS-006 — had none. Its repaired
    controls therefore had nothing that would fail if the repair were reverted.

    EVERY CONTROL IS SCORED ON A POSITIVE OBSERVATION. This is the whole lesson of
    OF-008 and it is the reason this function exists. Both of B14's original controls
    asked "did the reader return zero packets", which a reader that ran and correctly
    refused a bad path satisfies — and which a control whose script never compiled
    satisfies equally well. Neither could have failed. So each control here must show
    the reader ACTUALLY RAN AND REFUSED, by name: a `REFUSED <ExceptionType>` line that
    only an executed reader produces. The zero-count line is still required, but it is
    never sufficient on its own, because an absence is not an observation.

    NOTHING HERE RAISES. OF-011: a check that dies on malformed input is
    indistinguishable from one that detected a violation, and the caller cannot tell a
    finding from a crash. Every clause below reports; none throws.

    Pure and module-level so both polarities can be driven from stored text with no
    ground system present, which is the only way to red-case a verdict that would
    otherwise only ever run against a live one.
    """
    reasons = []

    def _int_after(text, token):
        m = re.search(rf"{token}\s+(\d+)", text or "")
        return int(m.group(1)) if m else None

    # --- 1. The playback recovered packets. Positive, and from the archive.
    packets = _int_after(playback_text, "PACKETS")
    if packets is None:
        reasons.append("playback names no PACKETS count: nothing establishes that the "
                       "ground system's reader returned anything at all")
    elif packets <= 0:
        reasons.append(f"playback returned {packets} packets")

    # --- 2. It read the DECOMPRESSED native log, not the compressed object.
    read = re.search(r"^read:\s*(\S+)", playback_text or "", re.MULTILINE)
    if not read:
        reasons.append("playback names no file it read")
    elif read.group(1).endswith(".gz"):
        reasons.append(f"playback read {read.group(1)}, the compressed object the "
                       f"reader cannot parse — so the packets came from somewhere else")

    # --- 3. The source was gone. Two independent observables, both read positively:
    # a frozen display would show the same telemetry whether or not anything replayed.
    port = re.search(r"accepting connections:\s*(\w+)", simulator_off_text or "")
    state = re.search(r"HUGINN_INT state:\s*(\w+)", simulator_off_text or "")
    if not port:
        reasons.append("no record of whether the simulator port was closed")
    elif port.group(1).strip().lower() != "false":
        reasons.append("the simulator was still accepting connections: this playback "
                       "cannot be distinguished from live telemetry")
    if not state:
        reasons.append("no record of the ground system's interface state")
    elif state.group(1).strip().upper() == "CONNECTED":
        reasons.append("the ground system's interface was still CONNECTED")

    # --- 4/5. The two controls. Each must have RUN, by name, and reported its result.
    for label, text, absence_token, absence_want, want_exc in (
            ("OF-005 file-bound", of005_text, r"packets returned:\s*(\d+)", "0",
             "FileNotFoundError"),
            ("compressed-refused", compressed_text, r"refused:\s*(\w+)", "True",
             "ValueError")):
        refused = _REFUSED.search(text or "")
        if not refused:
            reasons.append(
                f"{label} control shows no REFUSED line: nothing in the archive says "
                f"the reader ever ran. A control scored only on its absence cannot "
                f"fail, and this is the shape OF-008 recorded")
        elif refused.group(1) != want_exc:
            reasons.append(f"{label} control refused with {refused.group(1)}, not "
                           f"{want_exc}: it failed for a different reason than the one "
                           f"the control is about")
        got = re.search(absence_token, text or "")
        if not got:
            reasons.append(f"{label} control records no outcome")
        elif got.group(1).strip().lower() != absence_want.lower():
            reasons.append(f"{label} control reported {got.group(1)}, expected "
                           f"{absence_want}")

    # --- 6. The chain: what was decompressed is what is archived here.
    digests = re.findall(r"^([0-9a-f]{64})\s+(\S+)", decompression_text or "",
                         re.MULTILINE)
    gz = [d for d, p in digests if p.endswith(".gz")]
    if not gz:
        reasons.append("decompression record names no digest for the compressed object")
    elif archived_gz_sha256 and gz[0] != archived_gz_sha256:
        reasons.append(
            f"the decompression record's .gz digest {gz[0][:12]}… is not the digest of "
            f"the .gz archived beside it ({str(archived_gz_sha256)[:12]}…): the bytes "
            f"that were read are not the bytes preserved")
    if "COSMOS5_" not in (decompression_text or ""):
        reasons.append("decompression record does not show the COSMOS5_ header the "
                       "ground system's reader looks for")

    return not reasons, reasons


# ------------------------------------------------------------------- B7 and B10 verdicts
#
# D-019 selection 4, "B7 and B10 result checks". B6, B11 and B14 each had a verdict that
# re-derives the demonstration's result from its archived bytes under executed red and
# green cases; B7 and B10 had only the result their live run wrote into the manifest. A
# manifest that says PASS is the demonstration's word about itself. These recompute it.


def hazardous_commands(cmd_txt):
    """{command: True if HAZARDOUS} for one generated `cmd.txt`, read off its text.

    A COMMAND line opens a block and every indented line after it belongs to that block,
    so a HAZARDOUS line is attributed to the command it sits under, never by position.
    """
    out, current = {}, None
    for line in (cmd_txt or "").splitlines():
        m = re.match(r"^COMMAND\s+\S+\s+(\S+)", line)
        if m:
            current = m.group(1)
            out[current] = False
        elif current and re.match(r"^\s+HAZARDOUS\b", line):
            out[current] = True
    return out


def hazardous_reason(cmd_txt, command):
    """The reason text on `command`'s HAZARDOUS line, or None."""
    current = None
    for line in (cmd_txt or "").splitlines():
        m = re.match(r"^COMMAND\s+\S+\s+(\S+)", line)
        if m:
            current = m.group(1)
            continue
        h = re.match(r'^\s+HAZARDOUS\s+"(.*)"\s*$', line)
        if h and current == command:
            return h.group(1)
    return None


def _json(text, label, reasons):
    try:
        return json.loads(text or "")
    except (TypeError, ValueError) as exc:
        reasons.append(f"{label} is not readable JSON ({type(exc).__name__})")
        return None


def b7_verdict(refusal_text, acceptance_text, control_text, effect_text, cmd_txt):
    """B7's verdict, computed from ARCHIVED BYTES ALONE. (ok, reasons).

    The two-step gate is real only if four things are each shown POSITIVELY, because a
    dead uplink or a disconnected interface also refuses everything:

      - step one was refused AS HAZARDOUS, with the reason text the generated
        definition carries, and changed nothing;
      - step two was the same command resent WITH the hazardous check off, accepted,
        and moved the mode — a transition, since a mode command to the current mode
        is a no-op (OF-004);
      - a non-hazardous control went through WITH the hazardous check on, on the
        same link, so the gate is selective rather than a block on everything;
      - the link carried exactly the two accepted commands and not the refused one.

    Nothing here raises: a malformed artifact is a reason, never an exception (OF-011).
    """
    reasons = []
    flags = hazardous_commands(cmd_txt)
    if not flags:
        reasons.append("the archived cmd.txt defines no commands")

    # --- step one: refused, as hazardous, for the generated definition's reason
    refusal = _json(refusal_text, "step-one-refusal.json", reasons) or {}
    data = refusal.get("data") or {}
    ivars = data.get("instance_variables") or {}
    refused_cmd = ivars.get("@cmd_name")
    if data.get("class") != "HazardousError":
        reasons.append(f"step one was refused as {data.get('class')!r}, not "
                       f"HazardousError: a refusal for any other reason reads exactly "
                       f"like a block")
    if not refused_cmd:
        reasons.append("the refusal names no command")
    elif not flags.get(refused_cmd):
        reasons.append(f"{refused_cmd} is not HAZARDOUS in the archived cmd.txt, so its "
                       f"refusal is not the gate under test")
    elif ivars.get("@hazardous_description") != hazardous_reason(cmd_txt, refused_cmd):
        reasons.append("the refusal's reason is not the HAZARDOUS text the generated "
                       "definition carries for that command")

    # --- step two: the same command, resent with the check off, accepted
    accept = _json(acceptance_text, "step-two-acceptance.json", reasons) or {}
    result = accept.get("result") or {}
    if accept.get("error") is not None or not result:
        reasons.append("step two was not accepted")
    else:
        if result.get("cmd_name") != refused_cmd:
            reasons.append(f"step two sent {result.get('cmd_name')!r}, not the refused "
                           f"{refused_cmd!r}: it is not the resend of step one")
        if str(result.get("hazardous_check")).lower() != "false":
            reasons.append("step two did not go out with the hazardous check off, so it "
                           "is not the confirmation step")

    # --- the control: non-hazardous, unconfirmed, accepted with the check on
    control = _json(control_text, "non-hazardous-control.json", reasons) or {}
    cres = control.get("result") or {}
    if control.get("error") is not None or not cres:
        reasons.append("the non-hazardous control was not accepted: the link may "
                       "refuse everything, and the gate cannot be told from a dead uplink")
    else:
        if flags.get(cres.get("cmd_name"), True):
            reasons.append(f"the control {cres.get('cmd_name')!r} is not a "
                           f"non-hazardous command of the archived cmd.txt")
        if str(cres.get("hazardous_check")).lower() != "true":
            reasons.append("the control went out with the hazardous check off, so it "
                           "shows nothing about the gate")

    # --- the effect, and the link
    def field(label):
        m = re.search(rf"^{re.escape(label)}\s*:\s*(\S+)", effect_text or "", re.M)
        return m.group(1) if m else None

    before, after1, after2 = (field("EPS_MODE before"), field("EPS_MODE after step one"),
                              field("EPS_MODE after step two"))
    if None in (before, after1, after2):
        reasons.append("effect.txt does not record the mode before and after each step")
    else:
        if after1 != before:
            reasons.append(f"the refused command changed EPS_MODE {before} -> {after1}")
        if after2 != "SAFE":
            reasons.append(f"after step two EPS_MODE is {after2}, not SAFE")
        if after2 == before:
            reasons.append("no transition: the mode before step two was already the "
                           "mode after it (OF-004)")
    link = re.findall(r"^interface (before|after)\s*:\s*(\S+)\s+txcnt=(\d+)",
                      effect_text or "", re.M)
    states = {k: (s, int(n)) for k, s, n in link}
    if set(states) != {"before", "after"}:
        reasons.append("effect.txt does not record the interface before and after")
    else:
        if states["after"][0] != "CONNECTED":
            reasons.append(f"the interface ended {states['after'][0]}, not CONNECTED")
        sent = states["after"][1] - states["before"][1]
        if sent != 2:
            reasons.append(f"the link transmitted {sent} command(s); the two accepted "
                           f"commands and not the refused one make 2")
    return not reasons, reasons


def _leg(text):
    """(verdict, {condition: PASS|FAIL}, executed, identity line) for one pre-pass leg."""
    verdict = re.search(r"^### Verdict: \*\*(GO|NO-GO)\*\*", text or "", re.M)
    conditions = dict((name.strip(), state) for state, name in re.findall(
        r"^- \*\*(PASS|FAIL)\*\* — ([^:]+):", text or "", re.M))
    executed = re.search(r"^\| Executed \| (\S+) \|", text or "", re.M)
    identity = re.search(r"^DICTIONARY_VERSION .*$", text or "", re.M)
    return (verdict.group(1) if verdict else None, conditions,
            executed.group(1) if executed else None,
            identity.group(0) if identity else None)


#: The three conditions the pre-pass step reports, by the names it prints.
B10_CONDITIONS = ("identity vs dictionary of record", "loaded vs repository (D-010)",
                  "target inventory (D-009)")


def b10_verdict(go_text, nogo_text, restored_text, liveness_text):
    """B10's verdict, computed from ARCHIVED BYTES ALONE. (ok, reasons).

    NO-GO is only evidence if it is NO-GO FOR THE RIGHT REASON from a system that was
    answering. So the NO-GO leg must fail the loaded-vs-repository comparison and pass
    the identity check — the perturbation is one the source digest cannot see, which is
    what D-010 says the comparison exists for — with the instance's services running at
    that moment. GO before and GO after bracket it, in that order, on one displayed
    configuration identity.
    """
    reasons = []
    legs = {"GO": _leg(go_text), "NO-GO": _leg(nogo_text), "restored": _leg(restored_text)}
    for name, (verdict, conditions, _when, _ident) in legs.items():
        missing = [c for c in B10_CONDITIONS if c not in conditions]
        if missing:
            reasons.append(f"the {name} leg does not report {missing}")
        want = "NO-GO" if name == "NO-GO" else "GO"
        if verdict != want:
            reasons.append(f"the {name} leg's verdict is {verdict}, not {want}")
        if name != "NO-GO" and any(s != "PASS" for s in conditions.values()):
            reasons.append(f"the {name} leg has a failing condition")

    nogo = legs["NO-GO"][1]
    if nogo.get("loaded vs repository (D-010)") != "FAIL":
        reasons.append("the NO-GO leg did not fail the loaded-vs-repository comparison: "
                       "it is a NO-GO for some other reason than the perturbation")
    elif "targets/HUGINN/" not in (nogo_text or ""):
        reasons.append("the NO-GO leg names no HUGINN target file that differed")
    if nogo.get("identity vs dictionary of record") != "PASS":
        reasons.append("the NO-GO leg failed the identity check, so the perturbation is "
                       "one the source digest could see, and the comparison is untested")
    if nogo.get("target inventory (D-009)") != "PASS":
        reasons.append("the NO-GO leg failed the target inventory as well")

    times = [legs[k][2] for k in ("GO", "NO-GO", "restored")]
    if None in times:
        reasons.append("a leg records no execution time")
    elif not times[0] < times[1] < times[2]:
        reasons.append(f"the legs did not run GO, NO-GO, restored in that order: {times}")
    idents = {legs[k][3] for k in legs}
    if None in idents or len(idents) != 1:
        reasons.append("the three legs do not display one configuration identity")

    def services(label):
        m = re.search(rf"^{re.escape(label)}:\s*(\[.*\])\s*$", liveness_text or "", re.M)
        return re.findall(r"'([^']+)'", m.group(1)) if m else None

    before, during = (services("services running before"),
                      services("services running during NO-GO"))
    if not during:
        reasons.append("no service is recorded running during the NO-GO: the verdict "
                       "cannot be told from the silence of a dead instance")
    elif "openc3-cosmos-cmd-tlm-api" not in during:
        reasons.append("the command and telemetry API the pre-pass step queries was not "
                       "running during the NO-GO")
    if before is not None and during is not None and sorted(before) != sorted(during):
        reasons.append("the services running during the NO-GO differ from those before it")
    return not reasons, reasons


# ----------------------------------------------------------------------------- B11

def b11_verdict(chain_text, verdict_text, refusal_text, markup_text):
    """B11's verdict, computed from ARCHIVED BYTES ALONE (D-012). (ok, reasons).

    Every input is a file this run wrote into its own evidence directory and then read
    back off disk. A reader holding only that directory can recompute this result: the
    chain binds the three artifacts to one another by digest, the verdict artifact
    carries the full rule accounting, the refusal artifact carries the named rules of the
    red leg, and the markup artifact carries the suite result.
    """
    reasons = []
    chain = measurements_in(chain_text)
    verdict = measurements_in(verdict_text)

    for link in ("package_sha256", "verdict_sha256", "viewer_page_sha256"):
        if len(chain.get(link, "")) != 64:
            reasons.append(f"chain link {link} is not a sha256: {chain.get(link)!r}")
    # The chain must bind, not merely list: the verdict has to be ABOUT this package and
    # the page has to be built FROM it. Three digests sitting together prove adjacency.
    if chain.get("verdict_covers_package_sha256") != chain.get("package_sha256"):
        reasons.append("the verdict does not cover the archived package")
    if chain.get("viewer_page_built_from_sha256") != chain.get("package_sha256"):
        reasons.append("the viewer page was not built from the archived package")
    if verdict.get("package_sha256") != chain.get("package_sha256"):
        reasons.append("the verdict artifact names a different package than the chain")

    if verdict.get("result") != "CONFORMS":
        reasons.append(f"the recorded package did not conform: {verdict.get('result')!r}")
    declared = int(verdict.get("rules_declared", "0") or 0)
    in_check = int(verdict.get("rules_in_check", "0") or 0)
    at_viewer = int(verdict.get("rules_at_viewer", "0") or 0)
    if declared < 30:
        reasons.append(f"only {declared} rules declared; the contract is not loaded")
    if in_check + at_viewer != declared:
        reasons.append(f"accounting does not close: {in_check} + {at_viewer} "
                       f"!= {declared}")
    if verdict.get("rules_in_both") != "0":
        reasons.append(f"{verdict.get('rules_in_both')} rule(s) claimed at both sites")
    if verdict.get("rules_in_neither") != "0":
        reasons.append(f"{verdict.get('rules_in_neither')} rule(s) implemented nowhere")
    if "NOWHERE" in verdict_text:
        reasons.append("a declared rule is implemented nowhere")

    if "REFUSED" not in refusal_text:
        reasons.append("the perturbed package was not refused")
    named = set(re.findall(r"RS-\d+-\d+", refusal_text))
    if not named:
        reasons.append("the refusal named no rule, so RS-7-20 is not satisfied")
    for expected in ("RS-7-12", "RS-7-10"):
        if expected not in named:
            reasons.append(f"the refusal did not name {expected}, which the "
                           f"perturbation violates")

    markup = measurements_in(markup_text)
    if markup.get("result") != "OK":
        reasons.append(f"the malicious-markup suite did not pass: "
                       f"{markup.get('result')!r}")
    if int(markup.get("tests_run", "0") or 0) < 10:
        reasons.append(f"the markup suite ran only {markup.get('tests_run')} test(s)")
    if int(markup.get("hostile_payloads", "0") or 0) < 12:
        reasons.append(f"only {markup.get('hostile_payloads')} hostile payload(s)")

    return not reasons, reasons


def demo_b11():
    """The recorder-to-viewer path, end to end, against the live stack."""
    import hashlib
    import subprocess as sp
    cosmos = Cosmos()
    with Evidence("B11-replay-package-and-viewer", obligation="B11",
                  requirement="HUG-UI-002/003/004/005/007",
                  description="A pass recorded while the ground segment is live "
                              "exports a replay package conforming to every rule of "
                              "the interface definition, the display-only viewer "
                              "renders it, and a perturbed copy is refused by name "
                              "with no page written.") as ev:

        # The live stack must be the configuration of record BEFORE anything is
        # recorded. A package taken against a drifted ground segment is a faithful
        # record of the wrong thing (D-010).
        go, setup_lines = pass_setup.run("DEMO-B11", record=False)
        ev.capture_text("pass-setup.md", "\n".join(setup_lines) + "\n",
                        note="PRECONDITION: the ground segment is the configuration of "
                             "record at the moment of recording (D-010, HUG-GND-006).")
        if not go:
            ev.record("FAIL", "the ground segment was not GO at pass setup; a package "
                              "recorded against a drifted configuration would record "
                              "the wrong thing faithfully")
            return False

        with Sim("P1_nominal_orbit", rate=20.0) as sim:
            connected_ok, _ = wait_for(lambda: connected(cosmos), 120)
            iface = cosmos.interface()
            ev.capture_text(
                "live-stack.txt",
                f"interface_state: {iface.get('state')}\n"
                f"rxcnt: {iface.get('rxcnt')}\n"
                f"simulator_serving: {sim_port_open()}\n",
                note="the ground segment was live and receiving telemetry while this "
                     "pass was recorded")
            if not connected_ok:
                ev.record("FAIL", "the ground segment never connected to the simulator")
                return False

            # A fresh identifier per attempt: RS-2-03 says an identifier is used once,
            # and a demonstration must not consume a real pass's name twice.
            pass_id = "b11-demo-" + ev.attempt.replace("attempt-", "")
            replay_dir = ev.artifacts_dir / "replay"
            package = recorder.build_package("P1_nominal_orbit", pass_id,
                                             end_s=600.0, start_s=8900.0)
            written = recorder.write_package(package, pass_id, replay_dir=replay_dir)

        # Digest what was ARCHIVED, not what was built: the bytes on disk are the
        # evidence, and a digest of an in-memory object proves nothing about them.
        ev._record_artifact(written, "the exported replay package, as written")
        package_sha = hashlib.sha256(written.read_bytes()).hexdigest()

        conforms, violations = conformance.check(
            package, filename_stem=pass_id, path=written)
        declared = list(conformance.rule_ids())
        in_check = conformance.implemented_in_check()
        at_viewer = set(conformance.IMPLEMENTED_AT_VIEWER)
        lines = [
            "# B11 conformance verdict",
            "",
            f"package: {written.name}",
            f"package_sha256: {package_sha}",
            f"schema: {hugdefs.load_replay_schema()['schema']}",
            f"result: {'CONFORMS' if conforms else 'REFUSED'}",
            f"violations: {len(violations)}",
            "",
            "# rule accounting",
            f"rules_declared: {len(declared)}",
            f"rules_in_check: {len(in_check)}",
            f"rules_at_viewer: {len(at_viewer)}",
            f"rules_in_both: {len(in_check & at_viewer)}",
            f"rules_in_neither: {len(set(declared) - in_check - at_viewer)}",
            "",
            "# every declared rule, and the site that implements it",
        ]
        for rule in declared:
            if rule in in_check:
                where = "check"
            elif rule in at_viewer:
                where = "viewer:" + conformance.IMPLEMENTED_AT_VIEWER[rule]["module"]
            else:
                where = "NOWHERE"
            lines.append(f"{rule}: {where}")
        ev.capture_text("conformance-verdict.txt", "\n".join(lines) + "\n",
                        note="the verdict and the FULL rule accounting: every declared "
                             "rule and the site that implements it. A rule reading "
                             "NOWHERE would be one nobody enforces.")
        verdict_sha = hashlib.sha256(
            ev.archived("conformance-verdict.txt").encode("utf-8")).hexdigest()

        page_path = viewer_build.build(written, out_dir=ev.artifacts_dir / "viewer")
        ev._record_artifact(page_path,
                            "the viewer page built from that package: one self-contained "
                            "file, no backend, no network (HUG-UI-006)")
        page_sha = hashlib.sha256(page_path.read_bytes()).hexdigest()

        ev.capture_text(
            "digest-chain.txt",
            "# B11 evidence chain\n"
            "#\n"
            "# package -> verdict -> viewer page. Each link records the digest of the\n"
            "# artifact it is about, so the three are BOUND rather than merely adjacent.\n"
            "# Three files in a directory prove they were written together and nothing\n"
            "# more; these say which package the verdict judged and which package the\n"
            "# page was built from.\n"
            "#\n"
            "# Recompute: sha256sum artifacts/replay/*.json artifacts/viewer/*.html\n"
            "\n"
            f"package: replay/{written.name}\n"
            f"package_sha256: {package_sha}\n"
            f"verdict: conformance-verdict.txt\n"
            f"verdict_sha256: {verdict_sha}\n"
            f"verdict_covers_package_sha256: {package_sha}\n"
            f"viewer_page: viewer/{page_path.name}\n"
            f"viewer_page_sha256: {page_sha}\n"
            f"viewer_page_built_from_sha256: {package_sha}\n",
            note="THE CHAIN. Binds package, verdict and page to one another by digest.")

        # --- RED POLARITY.
        perturbed = json.loads(written.read_text(encoding="utf-8"))
        perturbed["frames"][0]["eps_batt_soc"] = 101.0
        perturbed["frames"][0]["eps_mode"] = "TURBO"
        perturbed_path = ev.artifacts_dir / "replay" / (pass_id + "-perturbed.json")
        perturbed_path.write_bytes(
            json.dumps(perturbed, separators=(",", ":")).encode("utf-8"))
        ev._record_artifact(perturbed_path,
                            "RED: the same package with two values moved outside their "
                            "dictionary domains")
        refusal = conformance.refuse(perturbed, filename_stem=perturbed_path.stem,
                                     path=perturbed_path)
        ev.capture_text("red-refusal.txt", (refusal or "NOT REFUSED") + "\n",
                        note="RED: the refusal, naming each rule and quoting its own "
                             "statement (RS-7-20). A refusal saying only 'invalid "
                             "package' would tell an operator nothing to act on.")

        red_dir = ev.artifacts_dir / "viewer-red"
        viewer_refused = "no"
        try:
            viewer_build.build(perturbed_path, out_dir=red_dir)
        except viewer_build.ViewerRefusal as exc:
            viewer_refused = "yes"
            ev.capture_text("red-viewer-refusal.txt", str(exc) + "\n",
                            note="RED: the viewer declined to render the perturbed "
                                 "package (RS-2-04).")
        ev.capture_text(
            "red-no-page.txt",
            f"viewer_refused: {viewer_refused}\n"
            f"page_written_for_perturbed_package: "
            f"{(red_dir / (perturbed_path.stem + '.html')).exists()}\n",
            note="RED: a page written and then abandoned would be a page an operator "
                 "could open, which is exactly the best-effort rendering RS-2-04 "
                 "forbids.")

        markup = sp.run([sys.executable, "-m", "unittest", "test_malicious_markup", "-v"],
                        cwd=str(REPO / "tests"), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=600)
        transcript = markup.stdout + markup.stderr
        ran = re.search(r"Ran (\d+) tests", transcript)
        sys.path.insert(0, str(REPO / "tests"))
        import test_malicious_markup as tmm
        ev.capture_text(
            "malicious-markup.txt",
            f"result: {'OK' if markup.returncode == 0 else 'FAILED'}\n"
            f"tests_run: {ran.group(1) if ran else 0}\n"
            f"hostile_payloads: {len(tmm.HOSTILE)}\n"
            f"exit_code: {markup.returncode}\n"
            "\n# transcript\n" + transcript,
            note="HUG-UI-007: the malicious-markup suite, EXECUTED as part of this "
                 "evidence run rather than cited from another one.")

        ok, reasons = b11_verdict(ev.archived("digest-chain.txt"),
                                  ev.archived("conformance-verdict.txt"),
                                  ev.archived("red-refusal.txt"),
                                  ev.archived("malicious-markup.txt"))
        ev.note(f"conformance: {'CONFORMS' if conforms else 'REFUSED'} over "
                f"{len(declared)} declared rules")
        ev.note(f"accounting: {len(in_check)} in check + {len(at_viewer)} at viewer, "
                f"{len(in_check & at_viewer)} in both, "
                f"{len(set(declared) - in_check - at_viewer)} in neither")
        ev.note("verdict computed from artifacts/digest-chain.txt, "
                "conformance-verdict.txt, red-refusal.txt and malicious-markup.txt; "
                "the live stack paced this run and decided none of it")
        if ok:
            ev.record("PASS",
                      f"a pass recorded while the ground segment was live exported a "
                      f"package conforming to all {len(declared)} rules; the viewer "
                      f"page was built from it; a perturbed copy was refused by name "
                      f"and no page was written for it")
        else:
            ev.record("FAIL", "; ".join(reasons))
        return ok


DEMOS = {"b6": demo_b6, "b7": demo_b7, "b10": demo_b10, "b11": demo_b11,
         "b14": demo_b14}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("demos", nargs="+", choices=sorted(DEMOS) + ["all"])
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):     # pragma: no cover
        pass
    names = sorted(DEMOS) if "all" in args.demos else args.demos
    results = {}
    for name in names:
        print(f"\n{'=' * 70}\n{name.upper()}\n{'=' * 70}", flush=True)
        written_before = len(evidence.WRITTEN)
        try:
            DEMOS[name]()
        except Exception as exc:
            print(f"  {type(exc).__name__}: {exc}", flush=True)
        # THE MANIFEST IS AUTHORITATIVE. Report the outcome that was RECORDED, not a
        # verdict re-derived from the demonstration's return value. Those two can
        # disagree: a demonstration that records INSTRUMENT_FAULT returns False, and the
        # runner used to print that False as "FAIL" — announcing about the subject
        # exactly what the manifest had just declined to say. A summary line is what
        # most readers see, so it is the last place the vocabulary should drift.
        written = evidence.WRITTEN[written_before:]
        if written:
            results[name] = {"result": written[-1]["result"],
                             "attempt": written[-1]["attempt"]}
        else:
            # No manifest at all: the demonstration died before recording anything.
            # That is not a statement about the subject either.
            results[name] = {"result": "NO_RECORD", "attempt": "-"}
        print(f"  -> {results[name]['result']} ({results[name]['attempt']})", flush=True)

    print(f"\n{'=' * 70}")
    for name, r in results.items():
        print(f"  {name.upper():<5} {r['result']:<17} {r['attempt']}")
    passed = [r for r in results.values() if r["result"] == "PASS"]
    owed = [n for n, r in results.items() if r["result"] != "PASS"]
    if owed:
        print(f"\n  {len(passed)}/{len(results)} passed. Still owed: "
              f"{', '.join(sorted(n.upper() for n in owed))}")
        print("  An INSTRUMENT_FAULT is not a failure of the subject, and it is not a "
              "pass either.")
    return 0 if not owed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
