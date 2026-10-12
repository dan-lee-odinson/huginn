#!/usr/bin/env python3
"""The five model properties, demonstrated to FAIL under a violated condition.

D-013 item 2, closing OF-013's B4 shortfall. HUG-VER-002: "Every requirement verified by
Test shall have a checker demonstrated to fail under a violated condition before its
passing result is accepted." Five Test-verified requirements — HUG-SYS-001, HUG-EPS-001,
HUG-EPS-002, HUG-CMD-004, HUG-CMD-005 — had only green cases. A property asserted over a
domain and never shown to catch a violation of itself is a check nobody has falsified;
its passing result is not yet evidence.

ONE PREDICATE, TWO POLARITIES. Each property below is a function that takes a model and
returns a finding or None. The GREEN case runs it against the real model and requires
silence; the RED case runs THE SAME predicate against a model with that one invariant
broken and requires it to speak. A red case written as a separate assertion would show
that some check catches the mutation, not that the check guarding the requirement does.

CAUGHT BY DETECTION, NEVER BY EXCEPTION. OF-011's lesson, made a test rather than a
comment. `defs_generation:G11.m1` was scored CAUGHT because the check raised KeyError
before it could report the violation it had already found, and crash and detection are
indistinguishable to a criterion that only asks "did it fail to return true". So `probe`
reports three outcomes, not two, and every red case asserts DETECTED specifically. A
mutation that makes the model explode is an INSTRUMENT_FAULT and fails these tests.

THE MUTATIONS ARE SUBCLASSES AND PER-INSTANCE BINDINGS. Nothing monkeypatches a module
or edits a source file: a red case that mutated global state could leak into the suites
that run after it, and the one thing worse than an unfalsified check is a falsified one
that broke its neighbours.
"""
import unittest

from harness import bare_eps, eps_defs, spacecraft
from sim.eps import Eps, EpsFaults

DETECTED, SILENT, INSTRUMENT_FAULT = "DETECTED", "SILENT", "INSTRUMENT_FAULT"


def probe(predicate, subject):
    """Run a property predicate and say WHICH of three things happened.

    Two outcomes would be enough to make a red case pass and are exactly why OF-011
    went unnoticed for the life of the build.
    """
    try:
        finding = predicate(subject)
    except Exception as exc:
        return INSTRUMENT_FAULT, f"{type(exc).__name__}: {exc}"
    return (DETECTED, finding) if finding else (SILENT, None)


# --------------------------------------------------------------------------- the
# predicates. Each states its requirement's property, and nothing else.

def energy_balance_holds(eps):
    """HUG-EPS-001: SoC evolves per array generation minus load consumption."""
    eps.state.ramp_elapsed_s = eps.ramp_s
    illuminated = eps.state.illuminated
    before = eps.soc_pct
    for _ in range(60):
        eps.step(1.0, illuminated, EpsFaults())
    after = eps.soc_pct
    if illuminated and after <= before:
        return (f"sunlit for 60 s and state of charge did not rise: "
                f"{before:.4f} -> {after:.4f}")
    if not illuminated and after >= before:
        return (f"eclipsed for 60 s and state of charge did not fall: "
                f"{before:.4f} -> {after:.4f}")
    if not 0.0 <= after <= 100.0:
        return f"state of charge left [0, 100]: {after}"
    return None


def generation_is_zero_in_eclipse(eps):
    """HUG-EPS-002: solar-array generation is zero in eclipse."""
    eps.state.illuminated = False
    eps.state.ramp_elapsed_s = eps.ramp_s
    eps.step(1.0, False, EpsFaults())
    gen = sum(eps.state.string_currents_a)
    if gen > 1e-9:
        return f"generating {gen:.4f} A of array current in eclipse"
    return None


def two_independently_observable_strings(eps):
    """HUG-SYS-001: the EPS comprises TWO solar-array strings.

    Two strings that can never differ are one string reported twice, and FM-EPS-01's
    detection — string asymmetry — depends on their being separately observable.
    """
    eps.state.ramp_elapsed_s = eps.ramp_s
    eps.step(1.0, True, EpsFaults(strings_zeroed=frozenset({1})))
    currents = eps.state.string_currents_a
    if len(currents) != 2:
        return f"the EPS reports {len(currents)} array string(s), not two"
    a1, a2 = currents
    if abs(a1 - a2) < 1e-9:
        return (f"string 1 forced to zero and both strings still read the same "
                f"({a1:.4f} A, {a2:.4f} A): the two are not separately observable")
    if a1 > 1e-9:
        return f"string 1 forced to zero still generates {a1:.4f} A"
    return None


def safe_entry_is_unconditional(sc):
    """HUG-CMD-004: ground-commanded SAFE entry is always accepted, from any mode."""
    for mode in ("NOMINAL", "LOW_POWER", "SAFE"):
        sc.eps.state.mode = mode
        before = sc.cdh.acc_count
        accepted, reason = sc.cdh.receive("CMD_SAFE_ENTER")
        if not accepted or sc.cdh.acc_count != before + 1:
            return f"SAFE entry from {mode} was not accepted (reason {reason})"
        if sc.eps.state.mode != "SAFE":
            return f"SAFE entry from {mode} accepted but mode is {sc.eps.state.mode}"
    return None


def reset_establishes_the_counter_epoch(sc):
    """HUG-CMD-005: reset reinitialises the counters to zero, then applies its own
    acceptance increment — so the post-reset epoch is (1, 0) from ANY prior state.

    This is the sole exception to simple delta arithmetic, which is why the
    acknowledgement is the epoch itself rather than a delta.
    """
    for acc, rej in ((0, 0), (5, 3), (65535, 65535)):
        sc.cdh.acc_count, sc.cdh.rej_count = acc, rej
        sc.cdh.receive("CMD_SYS_RESET")
        if (sc.cdh.acc_count, sc.cdh.rej_count) != (1, 0):
            return (f"from ({acc}, {rej}) reset produced "
                    f"({sc.cdh.acc_count}, {sc.cdh.rej_count}), not the (1, 0) epoch")
    return None


# --------------------------------------------------------------------------- the
# mutations. Each breaks exactly the invariant its predicate asserts.

class _GeneratesInTheDark(Eps):
    """HUG-EPS-001 violated: the pack gains charge with no sun on the arrays."""

    def _generation(self, faults):
        total, powers = super()._generation(faults)
        if not self.state.illuminated:
            powers = tuple(self.string_peak_w for _ in powers)
            total = sum(powers)
        return total, powers


class _LeakyEclipse(Eps):
    """HUG-EPS-002 violated: the ramp never reaches zero, so the arrays keep
    generating with the Earth between them and the sun."""

    def _ramp_factor(self):
        if self.state.illuminated:
            return super()._ramp_factor()
        return 0.25


class _OneStringReportedTwice(Eps):
    """HUG-SYS-001 violated: one string's current reported on both channels."""

    def _refresh_derived(self, p_net, p_load, string_powers=None):
        super()._refresh_derived(p_net, p_load, string_powers)
        currents = self.state.string_currents_a
        if len(currents) == 2:
            self.state.string_currents_a = (currents[1], currents[1])


def _mutated_eps(cls, soc_pct=50.0, illuminated=True):
    return cls(eps_defs(), initial_soc_pct=soc_pct, initial_mode="NOMINAL",
               initial_illuminated=illuminated)


# --------------------------------------------------------------------------- cases

class TestThePredicatesHoldOnTheRealModel(unittest.TestCase):
    """GREEN. If a predicate speaks here, every red case below is meaningless."""
    verifies = ("HUG-EPS-001", "HUG-EPS-002", "HUG-SYS-001", "HUG-CMD-004",
                "HUG-CMD-005")
    polarity = "green"

    def test_every_property_is_silent_on_the_real_model(self):
        for name, predicate, subject in (
                ("energy balance sunlit", energy_balance_holds,
                 bare_eps(soc_pct=50.0, illuminated=True)),
                ("energy balance eclipsed", energy_balance_holds,
                 bare_eps(soc_pct=50.0, illuminated=False)),
                ("eclipse generation", generation_is_zero_in_eclipse, bare_eps()),
                ("two strings", two_independently_observable_strings, bare_eps()),
                ("safe entry", safe_entry_is_unconditional, spacecraft()),
                ("reset epoch", reset_establishes_the_counter_epoch, spacecraft())):
            with self.subTest(property=name):
                outcome, detail = probe(predicate, subject)
                self.assertEqual(outcome, SILENT,
                                 f"{name} on the unmutated model: {detail}")


class TestEnergyBalanceCatchesItsViolation(unittest.TestCase):
    """RED — HUG-EPS-001."""
    verifies = ("HUG-EPS-001",)
    polarity = "red"

    def test_a_battery_that_charges_in_eclipse_is_caught(self):
        outcome, detail = probe(
            energy_balance_holds,
            _mutated_eps(_GeneratesInTheDark, illuminated=False))
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("did not fall", detail)


class TestEclipseGenerationCatchesItsViolation(unittest.TestCase):
    """RED — HUG-EPS-002."""
    verifies = ("HUG-EPS-002",)
    polarity = "red"

    def test_arrays_generating_in_eclipse_are_caught(self):
        outcome, detail = probe(generation_is_zero_in_eclipse,
                                _mutated_eps(_LeakyEclipse))
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("in eclipse", detail)


class TestTheTwoStringsCatchTheirViolation(unittest.TestCase):
    """RED — HUG-SYS-001."""
    verifies = ("HUG-SYS-001",)
    polarity = "red"

    def test_one_string_reported_on_both_channels_is_caught(self):
        outcome, detail = probe(two_independently_observable_strings,
                                _mutated_eps(_OneStringReportedTwice))
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("separately observable", detail)


class TestSafeEntryCatchesItsViolation(unittest.TestCase):
    """RED — HUG-CMD-004. The requirement is UNCONDITIONAL acceptance, so its
    violation is any mode in which the command is refused, or accepted without
    reaching SAFE."""
    verifies = ("HUG-CMD-004",)
    polarity = "red"

    def test_a_safe_entry_inhibited_in_safe_mode_is_caught(self):
        sc = spacecraft()
        original = sc.cdh._cmd_safe_enter

        def inhibited(args):
            if sc.eps.state.mode == "SAFE":
                return sc.cdh._reject("MODE_INHIBIT")
            return original(args)

        sc.cdh._cmd_safe_enter = inhibited
        outcome, detail = probe(safe_entry_is_unconditional, sc)
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("was not accepted", detail)

    def test_an_accepted_command_that_does_not_reach_safe_is_caught(self):
        sc = spacecraft()
        sc.cdh._cmd_safe_enter = lambda args: sc.cdh._accept()
        outcome, detail = probe(safe_entry_is_unconditional, sc)
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("mode is", detail)


class TestTheResetEpochCatchesItsViolation(unittest.TestCase):
    """RED — HUG-CMD-005. A reset that merely increments is the defect that makes
    the exception to delta arithmetic invisible."""
    verifies = ("HUG-CMD-005",)
    polarity = "red"

    def test_a_reset_that_does_not_zero_the_counters_is_caught(self):
        sc = spacecraft()
        sc.cdh._cmd_sys_reset = lambda args: sc.cdh._accept()
        outcome, detail = probe(reset_establishes_the_counter_epoch, sc)
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("not the (1, 0) epoch", detail)

    def test_a_reset_that_zeroes_without_its_own_accept_is_caught(self):
        """(0, 0) is not the epoch either: the reset's own acceptance is part of it."""
        sc = spacecraft()

        def zero_only(args):
            sc.cdh.acc_count = 0
            sc.cdh.rej_count = 0
            return True, "NONE"

        sc.cdh._cmd_sys_reset = zero_only
        outcome, detail = probe(reset_establishes_the_counter_epoch, sc)
        self.assertEqual(outcome, DETECTED, f"outcome={outcome} detail={detail}")
        self.assertIn("not the (1, 0) epoch", detail)


class TestAMutationThatCrashesIsNotAPass(unittest.TestCase):
    """OF-011, asserted rather than trusted.

    If `probe` folded an exception into "not silent", a model that exploded would score
    as a working red case — which is exactly how G11.m1 certified a check that never
    reported the violation it had already found.
    """
    verifies = ("HUG-VER-002",)
    polarity = "red"

    def test_an_exploding_subject_reports_instrument_fault_not_detected(self):
        class _Exploding:
            def __getattr__(self, name):
                raise RuntimeError("this model cannot be observed")

        outcome, detail = probe(generation_is_zero_in_eclipse, _Exploding())
        self.assertEqual(outcome, INSTRUMENT_FAULT, detail)
        self.assertNotEqual(outcome, DETECTED,
                            "a crash must never be counted as a caught violation")

    def test_the_three_outcomes_are_distinct(self):
        self.assertEqual(len({DETECTED, SILENT, INSTRUMENT_FAULT}), 3)


if __name__ == "__main__":
    unittest.main()
