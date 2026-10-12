"""HUGINN ground-side frame-staleness monitor (B6, HUG-GND-002).

GENERATED from defs/tlm_cmd.yaml - do not edit. The thresholds below are the
dictionary's, not this file's.

Dictionary note 1: "a halted counter cannot alarm itself". Neither can anything
driven by packet arrival - under HUG-EPS-004(c) no frames arrive at all. This
runs on its own clock so the alarm fires during an outage, which is the only
time it matters.
"""
import os
import sys
import time

from openc3.microservices.microservice import Microservice
# The INTERNAL telemetry API, not openc3.script. openc3.script is the external
# script interface: inside a microservice it raises "Token is required" on
# every call, which this monitor's except-branch swallows -- leaving a process
# that runs forever and never once reads the counter. That is exactly what was
# happening in the deployed instance, and it was invisible until the NO_READ
# state existed to say so (OF-002).
from openc3.api.tlm_api import tlm
from openc3.utilities.thread_manager import ThreadManager

TARGET = 'HUGINN'
PACKET = "HK"
COUNTER = 'CDH_FRAME_CNT'
YELLOW_S = 10
RED_S = 30
POLL_S = 1.0


class FrameStalenessMicroservice(Microservice):
    def run(self):
        last_value = None
        # None until a read SUCCEEDS. The staleness clock cannot start before
        # this monitor has actually looked at the counter once - see NO_READ.
        last_change = None
        annunciated = None
        reads_ok = 0
        # None while reads are working; set to the clock at the FIRST failure of
        # a run of failures, so READ_FAULT can report how long the ground path
        # has been down and recovery can report how long the gap was (D-012).
        read_fault_since = None
        while not self.cancel_thread:
            read_failed = False
            try:
                value = tlm(f"{TARGET} {PACKET} {COUNTER}",
                            scope=self.scope)
            except Exception:
                # The read failed. If we have read successfully before this is a
                # GROUND-SEGMENT fault, not a spacecraft one - see READ_FAULT. If
                # we never have, last_change is still None and stays None.
                read_failed = True
                value = last_value
            now = time.time()
            if read_failed:
                # ONLY after a prior success. A monitor that has NEVER read is
                # NO_READ, not READ_FAULT: nothing has broken, it has not started
                # yet, and before AOS that is the normal condition (OF-002). The
                # first draft of this state omitted the guard and turned every
                # never-read monitor into a ground fault; the OF-002 red case
                # caught it.
                if reads_ok > 0 and read_fault_since is None:
                    read_fault_since = now
            else:
                reads_ok += 1
                if last_change is None:
                    last_change = now
                if read_fault_since is not None:
                    # THE READ PATH CAME BACK, and that is annunciated in its own
                    # right. Falling straight back to GREEN would tell the
                    # operator the spacecraft is healthy without ever saying the
                    # ground path had been down, and the levels either side of a
                    # gap are worth nothing unless you know the gap was there.
                    self.logger.warn(
                        f"{COUNTER} staleness READ_RECOVERED: reads working "
                        f"again after {now - read_fault_since:.1f} s of "
                        f"READ_FAULT; staleness reporting resumes")
                    read_fault_since = None
                    # Re-annunciate the level even if it is the one from before
                    # the outage: it has to be restated against reads that are
                    # known to be working, or the last word on the spacecraft
                    # stays a level measured before the ground path failed.
                    annunciated = None
            if value is not None and value != last_value:
                last_value = value
                last_change = now

            if read_fault_since is not None:
                # CANNOT READ, HAVING READ BEFORE. A ground-segment read failure
                # and a spacecraft halt are different conditions and must not
                # share a vocabulary (D-012). No staleness LEVEL is annunciated
                # and no staleness NUMBER is quoted: both are claims about the
                # spacecraft, and a monitor that cannot read has no basis for
                # either. Before this state existed the clock kept running, RED
                # was annunciated once, and the process then fell silent forever
                # - byte-identical output to a monitor that had died (OF-006).
                #
                # last_change is deliberately NOT reset. If the counter genuinely
                # did not advance across the outage that staleness is real, and
                # it is observed on recovery by comparing values across the gap.
                level, stale_s = "READ_FAULT", 0.0
            elif last_change is None:
                # NEVER READ. Not staleness: this monitor has not yet seen the
                # counter at all, which before AOS is the normal condition and
                # at any other time means the monitor is blind rather than the
                # spacecraft silent. Annunciating it as RED would make a dead
                # monitor indistinguishable from a detected halt - the two would
                # emit the same GREEN/YELLOW/RED transcript, and the alarm would
                # be evidence of nothing.
                level, stale_s = "NO_READ", 0.0
            else:
                stale_s = now - last_change
                if stale_s >= RED_S:
                    level = "RED"
                elif stale_s >= YELLOW_S:
                    level = "YELLOW"
                else:
                    level = "GREEN"
            if level != annunciated:
                annunciated = level
                if level == "NO_READ":
                    self.logger.warn(
                        f"{COUNTER} staleness NO_READ: the monitor has not yet "
                        f"read the counter; the staleness clock has not started")
                elif level == "READ_FAULT":
                    self.logger.warn(
                        f"{COUNTER} staleness READ_FAULT: the monitor cannot "
                        f"read the counter after {reads_ok} successful reads. "
                        f"This is a GROUND-SEGMENT fault; no staleness claim is "
                        f"made about the spacecraft while it persists")
                else:
                    self.logger.warn(
                        f"{COUNTER} staleness {level}: no advance for "
                        f"{stale_s:.1f} s (yellow {YELLOW_S} s, red {RED_S} s; "
                        f"{reads_ok} successful reads)")
            self.count += 1
            time.sleep(POLL_S)


if os.path.basename(__file__) == os.path.basename(sys.argv[0]):
    FrameStalenessMicroservice.class_run()
    ThreadManager.instance().shutdown()
    ThreadManager.instance().join()
