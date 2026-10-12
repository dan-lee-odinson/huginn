#!/usr/bin/env python3
"""HUGINN command and data handling: validation, accounting, housekeeping frames.

Builds to HUG-CMD-001..007, HUG-EPS-004(c) and Dictionary Sec. 2. The command set,
opcodes, argument domains and telemetry order all come from defs/tlm_cmd.yaml.

The two contracts an operator's every action depends on:

  EXACTLY-ONCE ACCOUNTING (HUG-CMD-007). Every command the spacecraft receives
  increments exactly one of the accept / reject counters, by exactly one. That is
  what makes "verify by counter delta plus the affected telemetry point" a real
  verification step rather than a habit: a delta of one means one command was
  accounted, and no delta within 10 s of a verified send is the loss-of-
  commandability threshold PROC-003 keys on.

  THE RESET EPOCH (HUG-CMD-005). CMD_SYS_RESET is the sole exception to delta
  arithmetic. It zeroes both counters and then applies its own acceptance, so the
  first post-reset frame reads ACC = 1, REJ = 0. That epoch IS the acknowledgement -
  there is no delta to read, because the counters restarted. An operator who expects
  a delta here will misread a successful reset as a failed one, which is why the
  record states it and the suite asserts it as the only exception.

Rejection reasons are exactly the dictionary's three, and validation is ordered:
unknown opcode, then argument range, then mode inhibit. The order is observable -
a rejection reason tells the operator which gate stopped the command - so it is
fixed here rather than left to chance.
"""
from collections import OrderedDict

COUNTER_MODULUS = 65536          # uint16, wraps (Dictionary Sec. 1)

REASON_NONE = "NONE"
REASON_UNKNOWN_OPCODE = "UNKNOWN_OPCODE"
REASON_ARG_RANGE = "ARG_RANGE"
REASON_MODE_INHIBIT = "MODE_INHIBIT"


class Cdh:
    def __init__(self, tlm_defs, eps):
        self.defs = tlm_defs
        self.eps = eps

        self.commands = {c["mnemonic"]: c for c in tlm_defs["commands"]}
        self.opcodes = {c["opcode"]: c["mnemonic"] for c in tlm_defs["commands"]}
        rate_arg = next(a for a in self.commands["CMD_PLD_SET_RATE"]["args"]
                        if a["name"] == "rate")
        self.rate_min = float(rate_arg["min"])
        self.rate_max = float(rate_arg["max"])
        self.mode_targets = tuple(
            next(a for a in self.commands["CMD_MODE_SET"]["args"]
                 if a["name"] == "target")["enum_values"])
        self.payload_states = tuple(
            next(a for a in self.commands["CMD_PLD_SET_STATE"]["args"]
                 if a["name"] == "state")["enum_values"])

        self.acc_count = 0
        self.rej_count = 0
        self.rej_reason = REASON_NONE
        self.frame_count = 0
        self.hk_halted = False       # HUG-EPS-004(c), latched until CMD_SYS_RESET

    # -------------------------------------------------------------- accounting

    def _accept(self):
        self.acc_count = (self.acc_count + 1) % COUNTER_MODULUS
        return True, REASON_NONE

    def _reject(self, reason):
        self.rej_count = (self.rej_count + 1) % COUNTER_MODULUS
        self.rej_reason = reason
        return False, reason

    # ---------------------------------------------------------------- commanding

    def receive(self, mnemonic, args=None):
        """Receive one command. Returns (accepted, reason).

        Exactly one counter advances by exactly one on every call, including the
        unknown-opcode path - a command the spacecraft cannot identify is still a
        command it received, and HUG-CMD-001 requires it be accounted and reasoned.

        Uplink is independent of the housekeeping downlink, so this works while the
        generation-halt fault is latched. That is not an incidental property: it is
        the whole of PROC-003's escalation path (HUG-EPS-004(c)).
        """
        args = args or {}
        if mnemonic not in self.commands:
            return self._reject(REASON_UNKNOWN_OPCODE)

        handler = getattr(self, "_cmd_" + mnemonic[4:].lower())
        return handler(args)

    def receive_opcode(self, opcode, args=None):
        """Receive by wire opcode. An opcode outside the defined set is the
        UNKNOWN_OPCODE rejection of HUG-CMD-001."""
        if opcode not in self.opcodes:
            return self._reject(REASON_UNKNOWN_OPCODE)
        return self.receive(self.opcodes[opcode], args)

    def _cmd_pld_set_state(self, args):
        state = args.get("state")
        if state not in self.payload_states:
            return self._reject(REASON_ARG_RANGE)
        if state == "ON":
            # HUG-CMD-002 / CON-04: inhibited in SAFE or below the activation floor.
            if not self.eps.can_activate_payload():
                return self._reject(REASON_MODE_INHIBIT)
            self.eps.state.payload_on = True
        else:
            self.eps.shed_payload()
        return self._accept()

    def _cmd_pld_set_rate(self, args):
        rate = args.get("rate")
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            return self._reject(REASON_ARG_RANGE)
        rate = float(rate)
        # HUG-CMD-003: range first, then the payload-off inhibit. The order is
        # observable in CDH_REJ_REASON, so it is fixed rather than incidental.
        if rate < self.rate_min or rate > self.rate_max:
            return self._reject(REASON_ARG_RANGE)
        if not self.eps.state.payload_on:
            return self._reject(REASON_MODE_INHIBIT)
        self.eps.state.pld_rate_hz = rate
        return self._accept()

    def _cmd_safe_enter(self, args):
        # HUG-CMD-004: always accepted regardless of mode. This is the ground's
        # unconditional backstop (FM-EPS-10's compensating provision), so it has no
        # inhibit path at all.
        self.eps.enter_safe()
        return self._accept()

    def _cmd_sys_reset(self, args):
        """HUG-CMD-005. Clears the stale-telemetry fault, zeroes the counters, then
        applies its own acceptance, and preserves SoC."""
        soc_before = self.eps.state.energy_wh
        self.hk_halted = False
        self.acc_count = 0
        self.rej_count = 0
        self.rej_reason = REASON_NONE
        # The counters restart, then this command is accounted: ACC = 1, REJ = 0.
        # That epoch is the acknowledgement (Dictionary Sec. 2, ledger item 6).
        result = self._accept()
        # SoC is preserved, explicitly and verifiably - a reset that silently
        # re-initialised the battery would make the post-reset state a lie.
        self.eps.state.energy_wh = soc_before
        return result

    def _cmd_mode_set(self, args):
        target = args.get("target")
        # HUG-CMD-006: NOMINAL or LOW_POWER only. SAFE entry is CMD_SAFE_ENTER's
        # function, so SAFE as a target is an argument error, not an inhibit.
        if target not in self.mode_targets:
            return self._reject(REASON_ARG_RANGE)
        if not self.eps.command_mode(target):
            return self._reject(REASON_MODE_INHIBIT)
        return self._accept()

    # ------------------------------------------------------------------- faults

    def halt_hk_generation(self):
        """HUG-EPS-004(c). Latches: from onset no frames are generated, while the
        spacecraft truth state continues to evolve."""
        self.hk_halted = True

    # -------------------------------------------------------------------- frame

    def generate_frame(self, met_s):
        """One housekeeping frame, or None while generation is halted.

        Returns the 16 dictionary points in dictionary order, in dictionary-native
        units and types: floats for analogues, the enum's own string for states,
        integers for counters (replay_schema.md Sec. 5).

        None is not an error and not an empty frame - it is the absence of a frame,
        which is what the fault produces and what the reception gap in a P4 replay
        preserves as evidence.
        """
        if self.hk_halted:
            return None
        self.frame_count = (self.frame_count + 1) % COUNTER_MODULUS
        eps = self.eps
        st = eps.state
        strings = st.string_currents_a
        frame = OrderedDict()
        frame["EPS_BATT_V"] = eps.battery_voltage_v
        frame["EPS_BATT_I"] = st.battery_current_a
        frame["EPS_BATT_SOC"] = eps.soc_pct
        frame["EPS_SA1_I"] = strings[0] if len(strings) > 0 else 0.0
        frame["EPS_SA2_I"] = strings[1] if len(strings) > 1 else 0.0
        frame["EPS_BUS_V"] = eps.bus_v
        frame["EPS_LOAD_I"] = st.load_current_a
        frame["EPS_MODE"] = st.mode
        frame["ADM_ECLIPSE"] = "SUNLIT" if st.illuminated else "ECLIPSE"
        frame["PLD_STATE"] = "ON" if st.payload_on else "OFF"
        frame["PLD_RATE"] = st.pld_rate_hz
        frame["CDH_MET"] = int(met_s)
        frame["CDH_FRAME_CNT"] = self.frame_count
        frame["CDH_CMD_ACC_CNT"] = self.acc_count
        frame["CDH_CMD_REJ_CNT"] = self.rej_count
        frame["CDH_REJ_REASON"] = self.rej_reason
        return frame
