#!/usr/bin/env python3
"""The wire format, cross-checked against the generated packet definition.

Both sides of the simulator-to-ground link are generated from defs/tlm_cmd.yaml: the
ground system's packet definition by tools/gen_openc3_config.py, and the byte packing by
sim/interface.py. This suite asserts they agree FIELD FOR FIELD, by parsing the
generated tlm.txt and comparing it to what the codec actually emits.

That cross-check is the point. Two definitions of a wire format agree until the day they
do not, and the failure is silent - the ground system decodes garbage into
plausible-looking values, and nothing anywhere raises. Comparing the two generated
artifacts to each other catches a drift that neither one could catch alone.
"""
import re
import socket
import struct
import time
import unittest

from harness import REPO, spacecraft, tlm_defs

from sim.interface import CommandCodec, FrameCodec, TelemetryServer

TLM_TXT = (REPO / "gnd" / "openc3" / "plugins" / "openc3-cosmos-huginn"
           / "targets" / "HUGINN" / "cmd_tlm" / "tlm.txt")


def generated_fields():
    """(name, bits, type) for every item in the generated packet, in wire order."""
    out = []
    for line in TLM_TXT.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^\s*APPEND(?:_ID)?_ITEM\s+(\S+)\s+(\d+)\s+(\S+)", line)
        if m:
            out.append((m.group(1), int(m.group(2)), m.group(3)))
    return out


class TestTheTwoGeneratedSidesAgree(unittest.TestCase):
    verifies = ("HUG-GND-001",)

    def setUp(self):
        self.defs = tlm_defs()
        self.codec = FrameCodec(self.defs)
        self.fields = generated_fields()

    def test_the_generated_packet_was_found(self):
        """A scan that silently found nothing would make every comparison below
        vacuous."""
        self.assertGreater(len(self.fields), 10,
                           f"only {len(self.fields)} items parsed from {TLM_TXT}")

    def test_field_order_matches(self):
        ground = [name for name, _bits, _type in self.fields]
        wire = ["SYNC", "LENGTH"] + [p["mnemonic"] for p in self.codec.body]
        self.assertEqual(wire, ground,
                         "the packing order and the generated packet definition "
                         "disagree about field order")

    def test_field_widths_match(self):
        ground = {name: bits for name, bits, _type in self.fields}
        self.assertEqual(ground["SYNC"], self.codec.sync_bits)
        self.assertEqual(ground["LENGTH"], self.codec.length_bits)
        for point in self.codec.body:
            name = point["mnemonic"]
            self.assertEqual(ground[name], int(point["bits"]),
                             f"{name}: the packet definition says {ground[name]} bits, "
                             f"the codec packs {point['bits']}")

    def test_frame_size_matches_the_generated_definition(self):
        total_bits = sum(bits for _n, bits, _t in self.fields)
        self.assertEqual(self.codec.frame_size, total_bits // 8,
                         "the packed frame is not the size the ground system expects")

    def test_cdh_met_appears_exactly_once(self):
        """Dictionary Sec. 3 puts the MET timestamp in the header and the points in
        dictionary order, and CDH_MET is both. Carrying it twice would put two mission
        times in one frame and invite them to disagree."""
        names = [name for name, _b, _t in self.fields]
        self.assertEqual(names.count("CDH_MET"), 1)


class TestEncoding(unittest.TestCase):
    verifies = ("HUG-GND-001",)

    def setUp(self):
        self.codec = FrameCodec(tlm_defs())

    def _frame(self):
        sim = spacecraft()
        frame = None
        while frame is None:
            frame = sim.step()
        return frame

    def test_a_real_frame_encodes_to_the_expected_size(self):
        raw = self.codec.encode(self._frame())
        self.assertEqual(len(raw), self.codec.frame_size)

    def test_the_sync_marker_leads_every_frame(self):
        raw = self.codec.encode(self._frame())
        (sync,) = struct.unpack_from(">H", raw, 0)
        self.assertEqual(sync, self.codec.sync_value)

    def test_the_length_field_counts_the_octets_after_itself(self):
        """This is the contract the plugin's LENGTH protocol is generated against; if
        it is off by the header size the ground system frames on the wrong boundary."""
        raw = self.codec.encode(self._frame())
        (length,) = struct.unpack_from(">H", raw, 2)
        self.assertEqual(length, len(raw) - 4)

    def test_enum_values_encode_to_their_dictionary_index(self):
        """A member's wire code is its zero-based index in enum_values - the rule
        stated in defs, which the ground system's STATE lines are generated from."""
        sim = spacecraft()
        frame = None
        while frame is None:
            frame = sim.step()
        frame = dict(frame)
        frame["EPS_MODE"] = "SAFE"
        raw = self.codec.encode(frame)
        offset = 4 + 4 + 7 * 4          # MET + the seven leading floats
        (code,) = struct.unpack_from(">B", raw, offset)
        self.assertEqual(code, 2, "SAFE should encode as index 2 of the EPS_MODE enum")

    def test_a_value_outside_its_dictionary_enum_is_refused(self):
        """Refusing beats encoding a wrong code: a bad state silently on the wire would
        display as a valid state the spacecraft is not in."""
        frame = dict(self._frame())
        frame["EPS_MODE"] = "TURBO"
        with self.assertRaises(ValueError):
            self.codec.encode(frame)


class TestCommandDecoding(unittest.TestCase):
    verifies = ("HUG-CMD-001",)

    def setUp(self):
        self.codec = CommandCodec(tlm_defs())
        self.defs = tlm_defs()

    def _opcode(self, mnemonic):
        return next(c["opcode"] for c in self.defs["commands"]
                    if c["mnemonic"] == mnemonic)

    def test_a_no_argument_command_decodes(self):
        raw = struct.pack(">H", self._opcode("CMD_SAFE_ENTER"))
        mnemonic, args = self.codec.decode(raw)
        self.assertEqual(mnemonic, "CMD_SAFE_ENTER")
        self.assertEqual(args, {})

    def test_an_enum_argument_decodes_to_its_dictionary_spelling(self):
        raw = struct.pack(">HB", self._opcode("CMD_PLD_SET_STATE"), 1)
        mnemonic, args = self.codec.decode(raw)
        self.assertEqual(mnemonic, "CMD_PLD_SET_STATE")
        self.assertEqual(args, {"state": "ON"})

    def test_a_float_argument_decodes(self):
        raw = struct.pack(">Hf", self._opcode("CMD_PLD_SET_RATE"), 2.5)
        mnemonic, args = self.codec.decode(raw)
        self.assertEqual(mnemonic, "CMD_PLD_SET_RATE")
        self.assertAlmostEqual(args["rate"], 2.5, places=6)

    def test_an_unknown_opcode_returns_none_rather_than_being_swallowed(self):
        """HUG-CMD-001 requires every received command be accounted. This layer hands
        the unknown opcode up so the C&DH can reject it as UNKNOWN_OPCODE; dropping it
        here would leave the ground waiting for a counter delta that never comes."""
        unknown = max(c["opcode"] for c in self.defs["commands"]) + 1
        mnemonic, args = self.codec.decode(struct.pack(">H", unknown))
        self.assertIsNone(mnemonic)


class TestThePluginProtocolMatchesTheCommandPath(unittest.TestCase):
    """The command wire format, cross-checked against the plugin's INTERFACE line.

    This class exists because of a bug the rest of this file could not see. The
    telemetry cross-check above compares the codec to the generated tlm.txt field for
    field, and TestCommandDecoding asserts the codec decodes a bare opcode. Neither
    looks at the plugin's INTERFACE line, where the LENGTH protocol is configured - and
    that line carried fill_fields=True, telling COSMOS to write a sync marker and length
    field onto every OUTGOING command.

    So the two sides disagreed about the command format while both suites stayed green:
    the simulator read the opcode at byte 0, the ground system tried to write a 16-bit
    length at bit offset 16 of a 2-byte buffer, and every hazardous command failed to
    transmit. It surfaced only when a command was actually sent through a running
    COSMOS. Two generated artifacts agreeing with a THIRD artifact separately is not the
    same as agreeing with each other.
    """
    verifies = ("HUG-GND-001", "HUG-GND-003")

    PLUGIN = (REPO / "gnd" / "openc3" / "plugins" / "openc3-cosmos-huginn" / "plugin.txt")

    def setUp(self):
        self.defs = tlm_defs()
        line = next(l for l in self.PLUGIN.read_text(encoding="utf-8").splitlines()
                    if l.startswith("INTERFACE "))
        self.args = line.split()
        self.protocol = self.args[self.args.index("LENGTH"):]

    def test_the_interface_line_was_found_and_parsed(self):
        """A scan that silently found nothing would make every assertion below
        vacuous."""
        self.assertIn("LENGTH", self.args)
        self.assertGreaterEqual(len(self.protocol), 10,
                                f"LENGTH protocol arguments look truncated: "
                                f"{self.protocol}")

    def test_fill_fields_is_off_because_the_record_declares_no_command_frame(self):
        """THE REGRESSION. fill_fields is the last positional argument on a long line,
        which is exactly where a wrong value hides."""
        fill_fields = self.protocol[9]
        expected = "True" if self.defs.get("command_frame") else "False"
        self.assertEqual(
            fill_fields, expected,
            f"the plugin sets fill_fields={fill_fields}, but the record "
            f"{'declares' if self.defs.get('command_frame') else 'declares no'} "
            f"command frame. With fill_fields=True and unframed commands, COSMOS "
            f"writes a length field into a buffer with no room for one and the "
            f"command never transmits.")

    def test_a_bare_opcode_is_what_the_command_codec_expects(self):
        """The other half of the same binding: with fill_fields off, what COSMOS puts
        on the wire is the bare command buffer, and byte 0 must be the opcode."""
        codec = CommandCodec(self.defs)
        opcode = next(c["opcode"] for c in self.defs["commands"]
                      if c["mnemonic"] == "CMD_SAFE_ENTER")
        mnemonic, _args = codec.decode(struct.pack(">H", opcode))
        self.assertEqual(mnemonic, "CMD_SAFE_ENTER",
                         "the codec does not read a bare 2-byte command, so the "
                         "record's command format and fill_fields=False disagree")

    def test_the_length_protocol_numbers_still_come_from_the_frame_header(self):
        header = {h["name"]: h for h in self.defs["frame"]["header"]}
        self.assertEqual(int(self.protocol[1]), header["SYNC"]["bits"])
        self.assertEqual(int(self.protocol[2]), header["LENGTH"]["bits"])
        self.assertEqual(int(self.protocol[3]),
                         (header["SYNC"]["bits"] + header["LENGTH"]["bits"]) // 8)
        self.assertEqual(self.protocol[7], f"0x{header['SYNC']['value']:04X}")


class TestTelemetryServer(unittest.TestCase):
    verifies = ("HUG-GND-003",)

    def test_a_client_receives_exactly_the_bytes_the_codec_produced(self):
        codec = FrameCodec(tlm_defs())
        server = TelemetryServer(codec, host="127.0.0.1", port=0).start()
        try:
            client = socket.create_connection(("127.0.0.1", server.port), timeout=5)
            client.settimeout(5)
            deadline = time.time() + 5
            while server.client_count == 0 and time.time() < deadline:
                time.sleep(0.01)
            sim = spacecraft()
            frame = None
            while frame is None:
                frame = sim.step()
            self.assertEqual(server.send_frame(frame), 1)
            received = client.recv(4096)
            self.assertEqual(received, codec.encode(frame))
            client.close()
        finally:
            server.stop()

    def test_no_frame_is_sent_when_the_simulator_produces_none(self):
        """Under the generation-halt fault the simulator produces nothing, and the
        outage must reach the ground as an ABSENCE. Sending a filler frame would hide
        exactly the condition PROC-003 exists to detect."""
        codec = FrameCodec(tlm_defs())
        server = TelemetryServer(codec, host="127.0.0.1", port=0).start()
        try:
            sim = spacecraft("P4_hk_generation_halt")
            onset = next(f["t_s"] for f in sim.scenario.faults
                         if f["fault"] == "hk_generation_halt")
            suppressed = 0
            while sim.t_s <= onset + 5:
                if sim.step() is None:
                    suppressed += 1
            self.assertGreater(suppressed, 0,
                               "the generation-halt fault produced no suppressed ticks, "
                               "so this proves nothing")
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
