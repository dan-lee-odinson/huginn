#!/usr/bin/env python3
"""Generate the OpenC3 COSMOS target configuration from defs/tlm_cmd.yaml.

B1 and HUG-GND-001: "The ground system (OpenC3 COSMOS) telemetry and command
definitions shall be generated from `defs/tlm_cmd.yaml`; no hand-edited packet
definitions." Everything under gnd/openc3/plugins/openc3-cosmos-huginn/ is
output, never input.

Emitted (Phase 1 target config, Phase 3 plugin wrapper):
    plugin.txt              TARGET, INTERFACE and the B6 staleness MICROSERVICE
    targets/HUGINN/target.txt              target declaration
    cmd_tlm/tlm.txt         the 1 Hz housekeeping packet: 16 points, limits, states
    cmd_tlm/cmd.txt         the 5 commands: opcodes, arguments, HAZARDOUS flags (B7)
    CONFIG_ID.txt           source version + sha256 — the identity HUG-GND-006 has
                            the ground system display at pass setup (B10), and the
                            value a replay package's meta.dict_ref binds to

    microservices/STALENESS/frame_staleness.py   the B6 monitor itself

Still deferred: the reject-counter delta annunciation (limits.kind `delta`), whose
threshold is already in defs.

NOTHING HERE IS DEMONSTRATED YET. Phase 3's acceptance is a scripted demonstration of
each of B6, B7, B10 and B14 against a running ground segment. Until those have been
executed and recorded, this generator emits configuration that has not been shown to
work, and no claim in this repository says otherwise.

Usage:
    python tools/gen_openc3_config.py            regenerate the target config
    python tools/gen_openc3_config.py --check    exit 1 if any file on disk differs
"""
import hashlib
import sys

from hugdefs import (console, defs_dir, emit, load_tlm_cmd, points, render_limits,
                     repo)

TARGET = "HUGINN"


PLUGIN = "openc3-cosmos-huginn"
INTERFACE_NAME = "HUGINN_INT"
STALENESS_MICROSERVICE = "openc3-huginn-staleness"


def plugin_dir():
    return repo() / "gnd" / "openc3" / "plugins" / PLUGIN


def out_dir():
    return plugin_dir() / "targets" / TARGET

# OpenC3's LIMITS keyword takes four values — red-low, yellow-low, yellow-high,
# red-high — and has no spelling for "no limit on this side". Two points are
# one-sided in the record: EPS_BATT_SOC has no high limits (Dictionary note 2 —
# overcharge protection is the EPS_BATT_V voltage-high alarm, not a SoC limit) and
# EPS_LOAD_I has no low limits. Their absent sides are emitted as magnitudes no
# physical value in this model can reach, so the absent side can never annunciate.
#
# These are NOT dispositioned thresholds and must never be read as any. They are
# the generator's spelling of "the record defines no limit here", and every line
# that carries one says so in the emitted file. Open question to the owner.
ABSENT_LIMIT_LOW = -1.0e30
ABSENT_LIMIT_HIGH = 1.0e30

UNITS = {"V": ("Volts", "V"), "A": ("Amps", "A"), "%": ("Percent", "%"),
         "Hz": ("Hertz", "Hz"), "s": ("Seconds", "s")}


def source_digest():
    """(version, sha256) of the single source, for B10 / meta.dict_ref."""
    raw = (defs_dir() / "tlm_cmd.yaml").read_bytes()
    return load_tlm_cmd()["dictionary_version"], hashlib.sha256(raw).hexdigest()


def banner(version, digest, what):
    return [
        f"# {what}",
        "#",
        "# GENERATED FILE — DO NOT EDIT.",
        "# Source: defs/tlm_cmd.yaml   Generator: tools/gen_openc3_config.py",
        f"# Dictionary version: {version}",
        f"# Source sha256: {digest}",
        "#",
        "# HUG-GND-001 prohibits hand-edited packet definitions. Edit the source and",
        "# regenerate; an edit here is overwritten and, per HUG-GND-006, would make the",
        "# displayed configuration digest disagree with the dictionary of record — a",
        "# no-go for commanding at pass setup.",
        "",
    ]


def qstr(s):
    """A quoted OpenC3 string. Refuses rather than emits a broken definition.

    OpenC3 config strings are double-quoted with no escape: a record string
    containing a double quote would silently truncate a description and shift
    everything after it, producing a config that loads with wrong content instead
    of failing. No record string contains one today; this makes that a checked
    property of generation rather than a standing assumption.
    """
    if '"' in s:
        raise ValueError(
            f"record string contains a double quote, which OpenC3 config syntax "
            f"cannot carry: {s!r}. Resolve with the owner before generating.")
    return f'"{s}"'


def openc3_type(entry):
    t = entry["type"]
    if t == "float":
        return "FLOAT"
    if t == "enum" or t.startswith("uint"):
        return "UINT"
    raise ValueError(f"no OpenC3 type for {t!r}")


def units_lines(point):
    u = UNITS.get(point["units"])
    return [f"    UNITS {u[0]} {u[1]}"] if u else []


def state_lines(point, indent="    "):
    """Enum members as OpenC3 STATEs. A member's wire code is its zero-based index
    in enum_values — the rule stated in defs, so the member list is the one source
    for both spelling and code. An annunciating state carries its severity."""
    out = []
    annunciates = set()
    if point["limits"]["kind"] == "state":
        annunciates = set(point["limits"]["annunciates"])
    for code, member in enumerate(point["enum_values"]):
        sev = " RED" if member in annunciates else ""
        out.append(f"{indent}STATE {member} {code}{sev}")
    return out


# Why a point carries no LIMITS line. An unexplained absence in a generated config
# reads as an omission; each of these says which record rule produced it.
NO_LIMITS_REASON = {
    "unalarmed": ["# Monitored, not alarmed: the record defines no limits for this point",
                  "# (Dictionary v0.5: context-dependent)."],
    "state": ["# Annunciation here is state-based — the STATE ... RED above — not a",
              "# numeric limit."],
    "none": ["# The record defines no limits for this point."],
    "range": ["# 'valid range 0.1-10' is a validity DOMAIN, not an alarm. CMD_PLD_SET_RATE",
              "# rejects an out-of-range rate (ARG_RANGE) and the register therefore always",
              "# holds a dictionary-valid value, so there is nothing to annunciate",
              "# (replay_schema.md Sec. 5, payload-rate domain)."],
    "staleness": ["# Staleness is a GROUND-SIDE monitor (10 s yellow / 30 s red;",
                  "# B6, HUG-GND-002), not an onboard limit: a halted counter cannot alarm",
                  "# itself (Dictionary note 1). Emitted as the STALENESS microservice",
                  "# declared in plugin.txt, which runs on its own clock so the alarm",
                  "# fires during an outage - the only time it matters."],
    "delta": ["# 'delta > 0 annunciates yellow' is a ground-computed counter delta, not an",
              "# onboard limit. Emitted in Phase 3 with the ground segment."],
}


def limits_lines(point):
    """LIMITS for a point whose record limits are numeric thresholds; for every other
    kind, the reason no LIMITS line is emitted."""
    lim = point["limits"]
    if lim["kind"] != "thresholds":
        return ["    " + l for l in NO_LIMITS_REASON[lim["kind"]]]
    absent = [s for s in ("rl", "yl", "yh", "rh") if lim[s] is None]
    vals = [
        lim["rl"] if lim["rl"] is not None else ABSENT_LIMIT_LOW,
        lim["yl"] if lim["yl"] is not None else ABSENT_LIMIT_LOW,
        lim["yh"] if lim["yh"] is not None else ABSENT_LIMIT_HIGH,
        lim["rh"] if lim["rh"] is not None else ABSENT_LIMIT_HIGH,
    ]
    out = []
    if absent:
        out.append(f"    # The record defines no {'/'.join(absent)} limit for this point"
                   f" (Dictionary v0.5: {render_limits(lim)}).")
        out.append("    # The unreachable magnitudes below stand for absent; they are not"
                   " thresholds.")
    out.append("    LIMITS DEFAULT 1 ENABLED " + " ".join(f"{v:g}" for v in vals))
    return out


def build_tlm(defs, version, digest):
    out = banner(version, digest,
                 f"{TARGET} telemetry — 1 Hz housekeeping packet")
    frame = defs["frame"]
    out += [
        f"TELEMETRY {TARGET} HK {frame['endianness']} "
        f'"Housekeeping telemetry, {frame["rate_hz"]} Hz, '
        f'{frame["point_count"]} points in dictionary order"',
    ]
    for h in frame["header"]:
        if h["name"] == "SYNC":
            out.append(f'  APPEND_ID_ITEM {h["name"]} {h["bits"]} '
                       f'{h["type"].upper()} 0x{h["value"]:04X} ' + qstr("Frame sync marker"))
        elif h["name"] == "LENGTH":
            out.append(f'  APPEND_ITEM {h["name"]} {h["bits"]} '
                       f'{h["type"].upper()} ' + qstr("Octets following this field"))

    # CDH_MET is the header's MET timestamp AND dictionary point 12; it is emitted
    # once, at the header position Sec. 3 states, under its dictionary mnemonic.
    ordered = sorted(points(defs), key=lambda p: 0 if p["mnemonic"] == "CDH_MET" else 1)
    for p in ordered:
        out.append(f'  APPEND_ITEM {p["mnemonic"]} {p["bits"]} {openc3_type(p)} '
                   + qstr(p["description"]))
        out += units_lines(p)
        if p["type"] == "enum":
            out += state_lines(p)
        out += limits_lines(p)
    out.append("")
    return out


def build_cmd(defs, version, digest):
    out = banner(version, digest, f"{TARGET} commands — the 5 v0.1 commands")
    endian = defs["frame"]["endianness"]
    for c in defs["commands"]:
        out.append(f'COMMAND {TARGET} {c["mnemonic"]} {endian} ' + qstr(c["effect"]))
        if c["hazardous"]:
            out.append('  HAZARDOUS "Two-step confirmation required '
                       '(Dictionary Sec. 2; B7, FM-CDH-04)"')
        op = c["opcode"]
        out.append(f'  APPEND_ID_PARAMETER OPCODE 16 UINT {op} {op} {op} '
                   + qstr("Opcode"))
        for a in c["args"]:
            if a["type"] == "enum":
                lo, hi = 0, len(a["enum_values"]) - 1
                out.append(f'  APPEND_PARAMETER {a["name"].upper()} 8 UINT '
                           f'{lo} {hi} {lo} ' + qstr(a["name"]))
                for code, member in enumerate(a["enum_values"]):
                    out.append(f"    STATE {member} {code}")
            else:
                # Default is the range minimum: a value taken from the record rather
                # than a convenience value chosen here.
                out.append(f'  APPEND_PARAMETER {a["name"].upper()} 32 FLOAT '
                           f'{a["min"]:g} {a["max"]:g} {a["min"]:g} ' + qstr(a["name"]))
        out.append("")
    return out


def build_plugin_txt(defs, version, digest):
    """plugin.txt — how COSMOS is told what HUGINN is.

    Syntax verified against the reference plugin shipped with this OpenC3 release
    rather than written from memory: TARGET <folder> <name>; INTERFACE <name>
    <protocol file> <args...> with MAP_TARGET; MICROSERVICE <folder> <name> with CMD
    and TARGET_NAME.

    The interface is a TCP client onto the simulator, framed by the LENGTH protocol
    against the header defs/tlm_cmd.yaml declares — a 16-bit sync marker followed by a
    16-bit length. Every number below is derived from that header rather than chosen
    here, so a change to the frame layout in defs carries through instead of silently
    disagreeing with the ground system.
    """
    frame = defs["frame"]
    header = {h["name"]: h for h in frame["header"]}
    sync, length = header["SYNC"], header["LENGTH"]

    length_bit_offset = sync["bits"]
    length_bit_size = length["bits"]
    # The length field counts the octets that follow it, so the bytes from the start of
    # the frame up to the end of the length field are what must be added back.
    length_value_offset = (sync["bits"] + length["bits"]) // 8

    # fill_fields tells the LENGTH protocol to WRITE the sync marker and length field
    # into outgoing data. That is right for telemetry framing and wrong for HUGINN's
    # commands, which the record leaves unframed: sim/interface.py's CommandCodec reads
    # the opcode at byte 0, and tests/test_interface.py asserts it.
    #
    # This argument was hardcoded True while every number around it was derived, and the
    # docstring above claimed derivation - true of the numbers, blind to the boolean. The
    # effect was that COSMOS tried to write a 16-bit length at bit offset 16 of a 2-byte
    # command and every hazardous command failed to transmit with "2 byte buffer
    # insufficient to write UINT at bit_offset 16". Derived now, so a record that later
    # declares a command frame carries through instead of needing this remembered.
    fill_fields = "True" if defs.get("command_frame") else "False"

    out = banner(version, digest, f"{TARGET} plugin declaration")
    out += [
        "VARIABLE huginn_sim_host host.docker.internal",
        '  VARIABLE_DESCRIPTION "Host running the HUGINN simulator, as seen from inside'
        ' the container"',
        "VARIABLE huginn_sim_port 7801",
        '  VARIABLE_DESCRIPTION "TCP port the simulator serves housekeeping frames on"',
        "VARIABLE log_retain_time 2592000",
        '  VARIABLE_DESCRIPTION "Margin covering the window between a pass ending and'
        ' its evidence being archived (default 30 days). NOT the evidence mechanism -'
        ' see ruling D-008."',
        "",
        f"TARGET {TARGET} {TARGET}",
        "  # B14 / HUG-SYS-006: the ground system's native timestamped telemetry and",
        "  # command logs ARE the demonstration evidence.",
        "  #",
        "  # RETENTION IS A MARGIN, NOT THE MECHANISM (owner ruling D-008). Evidence is",
        "  # preserved by archiving it into verification/evidence/ at execution time,",
        "  # digested and committed. This setting only has to cover the window between",
        "  # a pass ending and its capture - seconds, not days. Relying on it instead",
        "  # would leave the evidence in a Docker volume that `down -v` destroys and",
        "  # that expires on a timer, and an empty volume months later cannot be told",
        "  # apart from a demonstration that never ran.",
        "  LOG_RETAIN_TIME <%= log_retain_time %>",
        "  TLM_LOG_CYCLE_TIME 300",
        "",
        f"INTERFACE {INTERFACE_NAME} openc3/interfaces/tcpip_client_interface.py"
        f" <%= huginn_sim_host %> <%= huginn_sim_port %> <%= huginn_sim_port %>"
        f" 10.0 None LENGTH {length_bit_offset} {length_bit_size}"
        f" {length_value_offset} 1 {frame['endianness']} 0"
        f" 0x{sync['value']:04X} None {fill_fields}",
        "  # LENGTH protocol arguments, all derived from the frame header in",
        f"  # defs/tlm_cmd.yaml: length field at bit {length_bit_offset},"
        f" {length_bit_size} bits wide,",
        f"  # counting octets after itself (offset {length_value_offset}), sync marker"
        f" 0x{sync['value']:04X}.",
        f"  # fill_fields={fill_fields}: the record declares no command frame, so"
        " outgoing",
        "  # commands are the bare opcode and arguments the simulator's CommandCodec"
        " reads.",
        f"  MAP_TARGET {TARGET}",
        "",
        f"MICROSERVICE STALENESS {STALENESS_MICROSERVICE}",
        "  # B6 / HUG-GND-002. On its own clock, not driven by packet arrival - under",
        "  # HUG-EPS-004(c) no packets arrive, and an outage is the only time this",
        "  # monitor matters (Dictionary note 1: a halted counter cannot alarm itself).",
        "  CMD python frame_staleness.py",
        f"  TARGET_NAME {TARGET}",
        "",
    ]
    return out


def build_staleness_microservice(defs):
    """The ground-side staleness monitor (B6, HUG-GND-002).

    Dictionary note 1 gives the reason this lives on the ground rather than onboard:
    "a halted counter cannot alarm itself". That also rules out anything driven by
    packet ARRIVAL — under HUG-EPS-004(c) no frames arrive at all, so a read conversion
    on an incoming frame would never run and the alarm would never fire. This is
    therefore a microservice on its own clock: it wakes on a timer, measures how long
    since the frame counter last advanced, and annunciates from that. An outage is the
    only time this matters, so being driven by anything the outage stops would defeat
    the whole mechanism.

    Thresholds come from defs/tlm_cmd.yaml - the same `staleness` limits kind the
    dictionary renders and which the target config deliberately refuses to emit as an
    onboard limit.

    NOT YET DEMONSTRATED. Phase 3's acceptance is a scripted demonstration of this
    alarm firing on a halted counter. Until that has been executed and recorded, this
    is code that has not been shown to work, and nothing in the repository says
    otherwise.
    """
    point = next(p for p in points(defs) if p["limits"]["kind"] == "staleness")
    limits = point["limits"]
    yellow, red = int(limits["yellow_s"]), int(limits["red_s"])
    q = '"""'
    return [
        f"{q}HUGINN ground-side frame-staleness monitor (B6, HUG-GND-002).",
        "",
        "GENERATED from defs/tlm_cmd.yaml - do not edit. The thresholds below are the",
        "dictionary's, not this file's.",
        "",
        'Dictionary note 1: "a halted counter cannot alarm itself". Neither can anything',
        "driven by packet arrival - under HUG-EPS-004(c) no frames arrive at all. This",
        "runs on its own clock so the alarm fires during an outage, which is the only",
        "time it matters.",
        f"{q}",
        "import os",
        "import sys",
        "import time",
        "",
        "from openc3.microservices.microservice import Microservice",
        "# The INTERNAL telemetry API, not openc3.script. openc3.script is the external",
        "# script interface: inside a microservice it raises \"Token is required\" on",
        "# every call, which this monitor's except-branch swallows -- leaving a process",
        "# that runs forever and never once reads the counter. That is exactly what was",
        "# happening in the deployed instance, and it was invisible until the NO_READ",
        "# state existed to say so (OF-002).",
        "from openc3.api.tlm_api import tlm",
        "from openc3.utilities.thread_manager import ThreadManager",
        "",
        f"TARGET = {TARGET!r}",
        'PACKET = "HK"',
        f"COUNTER = {point['mnemonic']!r}",
        f"YELLOW_S = {yellow}",
        f"RED_S = {red}",
        "POLL_S = 1.0",
        "",
        "",
        "class FrameStalenessMicroservice(Microservice):",
        "    def run(self):",
        "        last_value = None",
        "        # None until a read SUCCEEDS. The staleness clock cannot start before",
        "        # this monitor has actually looked at the counter once - see NO_READ.",
        "        last_change = None",
        "        annunciated = None",
        "        reads_ok = 0",
        "        # None while reads are working; set to the clock at the FIRST failure of",
        "        # a run of failures, so READ_FAULT can report how long the ground path",
        "        # has been down and recovery can report how long the gap was (D-012).",
        "        read_fault_since = None",
        "        while not self.cancel_thread:",
        "            read_failed = False",
        "            try:",
        '                value = tlm(f"{TARGET} {PACKET} {COUNTER}",',
        "                            scope=self.scope)",
        "            except Exception:",
        "                # The read failed. If we have read successfully before this is a",
        "                # GROUND-SEGMENT fault, not a spacecraft one - see READ_FAULT. If",
        "                # we never have, last_change is still None and stays None.",
        "                read_failed = True",
        "                value = last_value",
        "            now = time.time()",
        "            if read_failed:",
        "                # ONLY after a prior success. A monitor that has NEVER read is",
        "                # NO_READ, not READ_FAULT: nothing has broken, it has not started",
        "                # yet, and before AOS that is the normal condition (OF-002). The",
        "                # first draft of this state omitted the guard and turned every",
        "                # never-read monitor into a ground fault; the OF-002 red case",
        "                # caught it.",
        "                if reads_ok > 0 and read_fault_since is None:",
        "                    read_fault_since = now",
        "            else:",
        "                reads_ok += 1",
        "                if last_change is None:",
        "                    last_change = now",
        "                if read_fault_since is not None:",
        "                    # THE READ PATH CAME BACK, and that is annunciated in its own",
        "                    # right. Falling straight back to GREEN would tell the",
        "                    # operator the spacecraft is healthy without ever saying the",
        "                    # ground path had been down, and the levels either side of a",
        "                    # gap are worth nothing unless you know the gap was there.",
        "                    self.logger.warn(",
        '                        f"{COUNTER} staleness READ_RECOVERED: reads working "',
        '                        f"again after {now - read_fault_since:.1f} s of "',
        '                        f"READ_FAULT; staleness reporting resumes")',
        "                    read_fault_since = None",
        "                    # Re-annunciate the level even if it is the one from before",
        "                    # the outage: it has to be restated against reads that are",
        "                    # known to be working, or the last word on the spacecraft",
        "                    # stays a level measured before the ground path failed.",
        "                    annunciated = None",
        "            if value is not None and value != last_value:",
        "                last_value = value",
        "                last_change = now",
        "",
        "            if read_fault_since is not None:",
        "                # CANNOT READ, HAVING READ BEFORE. A ground-segment read failure",
        "                # and a spacecraft halt are different conditions and must not",
        "                # share a vocabulary (D-012). No staleness LEVEL is annunciated",
        "                # and no staleness NUMBER is quoted: both are claims about the",
        "                # spacecraft, and a monitor that cannot read has no basis for",
        "                # either. Before this state existed the clock kept running, RED",
        "                # was annunciated once, and the process then fell silent forever",
        "                # - byte-identical output to a monitor that had died (OF-006).",
        "                #",
        "                # last_change is deliberately NOT reset. If the counter genuinely",
        "                # did not advance across the outage that staleness is real, and",
        "                # it is observed on recovery by comparing values across the gap.",
        '                level, stale_s = "READ_FAULT", 0.0',
        "            elif last_change is None:",
        "                # NEVER READ. Not staleness: this monitor has not yet seen the",
        "                # counter at all, which before AOS is the normal condition and",
        "                # at any other time means the monitor is blind rather than the",
        "                # spacecraft silent. Annunciating it as RED would make a dead",
        "                # monitor indistinguishable from a detected halt - the two would",
        "                # emit the same GREEN/YELLOW/RED transcript, and the alarm would",
        "                # be evidence of nothing.",
        '                level, stale_s = "NO_READ", 0.0',
        "            else:",
        "                stale_s = now - last_change",
        "                if stale_s >= RED_S:",
        '                    level = "RED"',
        "                elif stale_s >= YELLOW_S:",
        '                    level = "YELLOW"',
        "                else:",
        '                    level = "GREEN"',
        "            if level != annunciated:",
        "                annunciated = level",
        '                if level == "NO_READ":',
        "                    self.logger.warn(",
        '                        f"{COUNTER} staleness NO_READ: the monitor has not yet "',
        '                        f"read the counter; the staleness clock has not started")',
        '                elif level == "READ_FAULT":',
        "                    self.logger.warn(",
        '                        f"{COUNTER} staleness READ_FAULT: the monitor cannot "',
        '                        f"read the counter after {reads_ok} successful reads. "',
        '                        f"This is a GROUND-SEGMENT fault; no staleness claim is "',
        '                        f"made about the spacecraft while it persists")',
        "                else:",
        "                    self.logger.warn(",
        '                        f"{COUNTER} staleness {level}: no advance for "',
        '                        f"{stale_s:.1f} s (yellow {YELLOW_S} s, red {RED_S} s; "',
        '                        f"{reads_ok} successful reads)")',
        "            self.count += 1",
        "            time.sleep(POLL_S)",
        "",
        "",
        "if os.path.basename(__file__) == os.path.basename(sys.argv[0]):",
        "    FrameStalenessMicroservice.class_run()",
        "    ThreadManager.instance().shutdown()",
        "    ThreadManager.instance().join()",
    ]


def build_target():
    return [
        f"# {TARGET} target declaration.",
        "# GENERATED FILE — DO NOT EDIT. Source: defs/tlm_cmd.yaml",
        "",
        "LANGUAGE python",
        "",
    ]


def build_config_id(version, digest):
    return [
        "# Loaded-configuration identity.",
        "#",
        "# HUG-GND-006 / B10: the ground system displays this version and digest at",
        "# pass setup, and PROC-001's pre-pass step verifies them against the",
        "# dictionary of record. A mismatch is a no-go for commanding until resolved.",
        "# It is also the value a replay package's meta.dict_ref carries",
        "# (replay_schema.md Sec. 3).",
        "",
        f"DICTIONARY_VERSION {version}",
        f"SOURCE_SHA256 {digest}",
        "",
    ]


def build_gemspec(version, digest):
    """The gemspec COSMOS builds the installable plugin from.

    Generated rather than authored because it carries the dictionary version into the
    gem's own version, so the artifact installed in the instance is identifiable as the
    dictionary it was built from without opening it. A hand-written gemspec would be a
    fourth place the version lives and the first to go stale.

    The version is normalised to a RubyGems-acceptable form: gem versions must be
    dot-separated digits, and the dictionary's 'v0.2' is not one.
    """
    gem_version = version.lstrip("vV")
    return [
        "# GENERATED FILE — DO NOT EDIT. Source: defs/tlm_cmd.yaml",
        f"# Dictionary {version}, source sha256 {digest[:12]}…",
        "",
        "Gem::Specification.new do |s|",
        f"  s.name        = {qstr(PLUGIN)}",
        f"  s.version     = {qstr(gem_version)}",
        "  s.summary     = 'HUGINN 6U CubeSat mission operations target'",
        "  s.description = 'Generated from defs/tlm_cmd.yaml. Hand edits are "
        "prohibited by HUG-GND-001.'",
        "  s.authors     = ['HUGINN']",
        "  s.license     = 'Apache-2.0'",
        "  s.files       = Dir['plugin.txt'] + Dir['targets/**/*'] + "
        "Dir['microservices/**/*']",
        "end",
        "",
    ]


def generated_files(defs, version, digest):
    """Every file this generator emits, as {path: lines}.

    A function rather than a literal inside ``main`` because it is the answer to "what
    does this repository generate?", and more than one caller needs it. In particular
    ``tools/ground_config.py`` compares the generated artifacts against the copies the
    running instance holds, and a hand-kept second list there would go stale the first
    time a file was added here -- silently, since a missing entry reads as "nothing to
    compare" rather than as a gap.
    """
    return {
        plugin_dir() / f"{PLUGIN}.gemspec": build_gemspec(version, digest),
        out_dir() / "target.txt": build_target(),
        out_dir() / "cmd_tlm/tlm.txt": build_tlm(defs, version, digest),
        out_dir() / "cmd_tlm/cmd.txt": build_cmd(defs, version, digest),
        out_dir() / "CONFIG_ID.txt": build_config_id(version, digest),
        plugin_dir() / "plugin.txt": build_plugin_txt(defs, version, digest),
        plugin_dir() / "microservices/STALENESS/frame_staleness.py":
            build_staleness_microservice(defs),
    }


def main(argv):
    console()
    check = "--check" in argv
    defs = load_tlm_cmd()
    version, digest = source_digest()

    files = generated_files(defs, version, digest)

    stale = []
    for path, lines in files.items():
        rel = path.relative_to(repo()).as_posix()
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            stale.append(rel)
            continue
        if not emit(path, lines, check_only=check):
            stale.append(rel)

    where = f"gnd/openc3/plugins/{PLUGIN}"
    if check:
        ok = not stale
        print(f"[{'PASS' if ok else 'FAIL'}] {where} matches defs/tlm_cmd.yaml"
              + ("" if ok else f" — stale or missing: {stale};"
                               " regenerate (hand edits are prohibited by HUG-GND-001)"))
        return 0 if ok else 1
    print(f"generated {len(files)} files under {where} from defs/tlm_cmd.yaml "
          f"(dictionary {version}, sha256 {digest[:12]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
