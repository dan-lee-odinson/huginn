#!/usr/bin/env python3
"""The simulator's OpenC3-facing TCP interface.

The ground system connects to this as a `tcpip_client_interface`, so the simulator is
the server. That direction is set by the generated plugin, which declares the interface
as a client onto `huginn_sim_host:huginn_sim_port`.

THE WIRE FORMAT IS DERIVED, NOT RESTATED. Both sides of this link are generated from
`defs/tlm_cmd.yaml`: the ground system's packet definition by `gen_openc3_config.py`,
and the byte packing here by the same field list, in the same order, at the same widths.
Nothing in this file names an offset or a size. A wire format written out by hand on one
side of a link is the classic way to get two definitions that agree until the day they
do not, and the failure is silent - the ground system decodes garbage into
plausible-looking values.

`tests/test_interface.py` cross-checks the packing against the generated `tlm.txt`
field-for-field, so the two generated artifacts are shown to agree rather than assumed
to.

FRAME LAYOUT, from the header in defs plus the dictionary order:

    SYNC     16 bits   0x4855
    LENGTH   16 bits   octets following this field
    CDH_MET  32 bits   the header timestamp, which IS dictionary point CDH_MET
    ...      the remaining 15 points, in dictionary order

CDH_MET appears once. Dictionary Sec. 3 puts the MET timestamp in the header and the
points in dictionary order, and CDH_MET is both - carrying it twice would put two
mission times in one frame and invite them to disagree.
"""
import socket
import socketserver
import struct
import threading

# Struct format per (type, bits) pair. Big-endian is applied once at the front of the
# whole format string, from the endianness declared in defs.
_PACK = {
    ("uint", 8): "B",
    ("uint", 16): "H",
    ("uint", 32): "I",
    ("float", 32): "f",
    ("float", 64): "d",
}

_ENDIAN = {"BIG_ENDIAN": ">", "LITTLE_ENDIAN": "<"}


def _wire_type(point):
    """The (kind, bits) a point occupies on the wire."""
    kind = point["type"]
    if kind == "enum":
        kind = "uint"
    elif kind.startswith("uint"):
        kind = "uint"
    return kind, int(point["bits"])


class FrameCodec:
    """Packs a housekeeping frame exactly as the generated packet definition reads it."""

    def __init__(self, tlm_defs):
        frame = tlm_defs["frame"]
        self.endian = _ENDIAN[frame["endianness"]]
        header = {h["name"]: h for h in frame["header"]}
        self.sync_value = int(header["SYNC"]["value"])
        self.sync_bits = int(header["SYNC"]["bits"])
        self.length_bits = int(header["LENGTH"]["bits"])

        points = [p for g in tlm_defs["telemetry_groups"] for p in g["points"]]
        by_name = {p["mnemonic"]: p for p in points}
        self.met_point = by_name["CDH_MET"]
        # Header MET first, then every other point in dictionary order - the same order
        # gen_openc3_config.py emits its APPEND_ITEM lines in.
        self.body = [self.met_point] + [p for p in points if p["mnemonic"] != "CDH_MET"]

        self.enum_codes = {
            p["mnemonic"]: {member: code for code, member in enumerate(p["enum_values"])}
            for p in points if p["type"] == "enum"
        }

        self.header_format = (self.endian
                              + _PACK[("uint", self.sync_bits)]
                              + _PACK[("uint", self.length_bits)])
        self.body_format = self.endian + "".join(
            _PACK[_wire_type(p)] for p in self.body)
        self.body_size = struct.calcsize(self.body_format)
        self.frame_size = struct.calcsize(self.header_format) + self.body_size

    def encode(self, frame):
        """One housekeeping frame dict -> bytes on the wire."""
        values = []
        for point in self.body:
            value = frame[point["mnemonic"]]
            if point["type"] == "enum":
                codes = self.enum_codes[point["mnemonic"]]
                if value not in codes:
                    raise ValueError(
                        f"{point['mnemonic']} carries {value!r}, which is not one of "
                        f"its dictionary values {sorted(codes)}")
                value = codes[value]
            elif point["type"].startswith("uint"):
                value = int(value)
            else:
                value = float(value)
            values.append(value)
        body = struct.pack(self.body_format, *values)
        # LENGTH counts the octets that follow it, which is the body - matching the
        # length_value_offset the plugin's LENGTH protocol is generated with.
        head = struct.pack(self.header_format, self.sync_value, len(body))
        return head + body


class CommandCodec:
    """Decodes an uplinked command into (mnemonic, args) for the spacecraft."""

    def __init__(self, tlm_defs):
        frame = tlm_defs["frame"]
        self.endian = _ENDIAN[frame["endianness"]]
        self.commands = {c["opcode"]: c for c in tlm_defs["commands"]}
        self.opcode_bits = 16

    def decode(self, raw):
        """bytes -> (mnemonic or None, args). An unknown opcode returns None so the
        C&DH can account it as UNKNOWN_OPCODE rather than this layer swallowing it -
        HUG-CMD-001 requires every received command be accounted."""
        if len(raw) < 2:
            return None, {}
        (opcode,) = struct.unpack_from(self.endian + "H", raw, 0)
        command = self.commands.get(opcode)
        if command is None:
            return None, {}
        args, offset = {}, 2
        for spec in command["args"]:
            if spec["type"] == "enum":
                (code,) = struct.unpack_from(self.endian + "B", raw, offset)
                offset += 1
                members = spec["enum_values"]
                args[spec["name"]] = members[code] if code < len(members) else code
            else:
                (value,) = struct.unpack_from(self.endian + "f", raw, offset)
                offset += 4
                args[spec["name"]] = value
        return command["mnemonic"], args


class TelemetryServer:
    """Serves housekeeping frames to whichever ground system connects.

    Frames are pushed to every connected client as the simulator produces them. When
    the generation-halt fault is latched the simulator produces none, and this sends
    none - the outage reaches the ground as an absence, which is what the fault is and
    what the ground-side staleness monitor exists to notice.
    """

    def __init__(self, codec, host="0.0.0.0", port=7801):
        self.codec = codec
        self.host, self.port = host, port
        self._clients = []
        self._lock = threading.Lock()
        self._server = None
        self._thread = None
        self.on_command = None

    def start(self):
        codec, outer = self.codec, self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                with outer._lock:
                    outer._clients.append(self.request)
                try:
                    while True:
                        raw = self.request.recv(4096)
                        if not raw:
                            break
                        if outer.on_command:
                            outer.on_command(raw)
                except OSError:
                    pass
                finally:
                    with outer._lock:
                        if self.request in outer._clients:
                            outer._clients.remove(self.request)

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self._server = Server((self.host, self.port), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def send_frame(self, frame):
        """Push one frame to every connected ground system. Returns how many got it."""
        raw = self.codec.encode(frame)
        sent = 0
        with self._lock:
            for client in list(self._clients):
                try:
                    client.sendall(raw)
                    sent += 1
                except OSError:
                    self._clients.remove(client)
        return sent

    @property
    def client_count(self):
        with self._lock:
            return len(self._clients)

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
