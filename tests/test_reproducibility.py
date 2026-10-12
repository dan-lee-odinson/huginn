#!/usr/bin/env python3
"""Bit-for-bit reproducibility, and the proof that no scenario path can read a wall
clock or draw unseeded randomness.

Owner standing instruction for Phase 2. HUG-SYS-003 and ASM-01 make reproducibility a
property of the record, not a nicety: the campaign's four passes ARE its evidence, so
a pass that cannot be re-run to the same numbers is not evidence of anything. And
HUG-SYS-004 requires real-time and accelerated-time execution to give identical model
results.

Reproducibility is asserted THREE ways, because each catches what the others cannot:

  1. BEHAVIOURAL - run each scenario twice and compare every field of every frame,
     on the exact float repr rather than a rounded rendering. Catches an actual
     divergence, but only if the run happens to take the non-deterministic branch.

  2. STATIC - walk the AST of every module in the scenario path and refuse any wall
     clock read or any use of the process-global `random` generator. Catches the
     capability before it is ever exercised, including on a branch a test never
     reaches. This is the one that matters: a `time.time()` inside a rarely-taken
     fault path would pass (1) for years.

  3. RUNTIME - trap the clock and entropy sources so any call raises, then run a
     full scenario. Catches a dynamic route to them - a getattr, an import inside a
     function - that the static walk cannot see.

Neither (1) nor (3) alone would justify the claim, and the record's rule against
unexecuted direction claims means the claim is exactly what these three execute.
"""
import ast
import unittest
from pathlib import Path

from harness import CAMPAIGN, REPO, eps_defs, frame_signature, scenario, spacecraft

SIM_DIR = REPO / "sim"

# Module-level imports forbidden in the scenario path. `math` is here because
# transcendental results can differ between platform libm versions, which would break
# byte equality across machines even with identical inputs.
FORBIDDEN_IMPORTS = {"time", "datetime", "math", "secrets", "uuid", "calendar"}

# ONE narrow, named exemption, and only for `math`.
#
# Owner ruling D-003 chose SGP4 propagation and declined to pay for cross-machine byte
# equality ("across runs is enough"). Propagation and the coordinate transforms it needs
# are trigonometric by nature; there is no propagator that is not. So sim/orbit.py is
# permitted `math`, and the consequence is stated in its own module docstring rather
# than discovered later: orbit-derived values are reproducible run-to-run on a machine
# and are not claimed byte-equal between machines.
#
# The exemption covers `math` ALONE. Clock reads and unseeded randomness stay forbidden
# in sim/orbit.py exactly as everywhere else, and the exemption list is itself asserted
# below so a new module cannot quietly join it.
MATH_EXEMPT_MODULES = {"orbit.py"}

# Attribute calls forbidden anywhere in the scenario path.
FORBIDDEN_CALLS = {
    ("time", "time"), ("time", "monotonic"), ("time", "perf_counter"),
    ("time", "process_time"), ("time", "time_ns"), ("time", "monotonic_ns"),
    ("datetime", "now"), ("datetime", "utcnow"), ("datetime", "today"),
    ("date", "today"), ("os", "urandom"), ("uuid", "uuid1"), ("uuid", "uuid4"),
}

# The process-global generator. `random.Random(seed)` is permitted - that is an
# explicitly seeded instance - but every module-level function shares one generator
# seeded from entropy, so a single call destroys reproducibility silently.
FORBIDDEN_RANDOM_FUNCTIONS = {
    "random", "randint", "randrange", "choice", "choices", "shuffle", "sample",
    "uniform", "gauss", "normalvariate", "seed", "getrandbits", "randbytes",
    "triangular", "betavariate", "expovariate",
}


def sim_modules():
    return sorted(SIM_DIR.glob("*.py"))


class TestBitForBitReproducibility(unittest.TestCase):
    """HUG-SYS-003 / ASM-01."""
    verifies = ("HUG-SYS-003",)

    def test_each_campaign_scenario_reproduces_exactly(self):
        for name in CAMPAIGN:
            with self.subTest(scenario=name):
                first = frame_signature(spacecraft(name).run())
                second = frame_signature(spacecraft(name).run())
                self.assertEqual(len(first), len(second))
                self.assertEqual(first, second,
                                 f"{name} produced different frames on a second run "
                                 f"from the same scenario file")
                self.assertGreater(len(first), 0, f"{name} produced no frames")

    def test_stepping_in_different_batch_sizes_gives_identical_results(self):
        """HUG-SYS-004: real-time and accelerated-time execution give identical model
        results. The model never observes pacing, so batch size is the honest proxy
        for it - and the test would fail if any state depended on how the caller
        chose to drive the loop."""
        name = "P1_nominal"
        reference = frame_signature(spacecraft(name).run())
        for batch in (1, 7, 60, 997):
            with self.subTest(batch=batch):
                sim = spacecraft(name)
                frames, duration = [], sim.scenario.duration_s
                while sim.t_s < duration:
                    for _ in range(batch):
                        if sim.t_s >= duration:
                            break
                        frame = sim.step()
                        if frame is not None:
                            frames.append(frame)
                self.assertEqual(frame_signature(frames), reference,
                                 f"stepping {batch} ticks at a time changed the result")

    def test_the_seed_is_carried_and_a_seeded_generator_exists(self):
        """HUG-SYS-003 names the seed as part of the scenario identity. It is carried
        and a seeded generator is constructed eagerly, so nothing can quietly fall
        back to the process-global one by finding it absent."""
        for name in CAMPAIGN:
            sc = scenario(name)
            self.assertIsInstance(sc.seed, int)
            # Two independent loads of the same file must yield the same SEQUENCE.
            # Drawing one value from each of five fresh generators would compare five
            # copies of the same first draw and pass regardless.
            first = [sc.rng.random() for _ in range(5)]
            again = [x for x in (lambda g: [g.random() for _ in range(5)])(
                scenario(name).rng)]
            self.assertEqual(first, again,
                             f"{name}: the scenario generator is not seed-determined")
            self.assertEqual(len(set(first)), 5,
                             f"{name}: the generator returned the same value five "
                             f"times, so this proves nothing about the sequence")

    def test_the_default_generation_profile_uses_no_transcendental_function(self):
        """The cosine profile is selectable but not the default. Transcendental
        results can differ between platform libm versions, so the default path is kept
        free of them and this asserts the configuration, not just the code."""
        self.assertEqual(eps_defs()["model"]["generation_profile"], "flat",
                         "the default generation profile must stay 'flat' unless the "
                         "owner rules otherwise; 'cosine' introduces math.pi into the "
                         "reproducibility-critical path")


class TestNoWallClockOrUnseededRandomnessStatically(unittest.TestCase):
    """The static half of the determinism proof."""
    verifies = ("HUG-SYS-003",)

    def test_sim_modules_exist_to_be_scanned(self):
        """A scan that silently found nothing to scan would pass forever."""
        modules = sim_modules()
        self.assertGreaterEqual(len(modules), 4,
                                f"expected the simulator modules under {SIM_DIR}, "
                                f"found {[m.name for m in modules]}")

    def test_no_module_level_import_of_a_nondeterministic_source(self):
        offences = []
        for path in sim_modules():
            exempt = {"math"} if path.name in MATH_EXEMPT_MODULES else set()
            forbidden = FORBIDDEN_IMPORTS - exempt
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:                     # module level only
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in forbidden:
                            offences.append(f"{path.name}:{node.lineno} import {root}")
                elif isinstance(node, ast.ImportFrom):
                    root = (node.module or "").split(".")[0]
                    if root in forbidden:
                        offences.append(f"{path.name}:{node.lineno} from {root} import")
        self.assertEqual(offences, [],
                         f"non-deterministic module imported at module level: {offences}")

    def test_the_math_exemption_is_exactly_the_orbit_module(self):
        """The exemption list is asserted, so a later module cannot quietly join it and
        silently give up run-to-run reproducibility in the EPS or C&DH path."""
        self.assertEqual(MATH_EXEMPT_MODULES, {"orbit.py"},
                         "only sim/orbit.py is exempt from the math rule, under owner "
                         "ruling D-003; adding another module needs a ruling, not an "
                         "edit to this set")
        # Checked over the AST at ANY scope, not only module level: a function-level
        # `import math` in a rarely-taken branch is exactly the latent transcendental
        # this rule exists to keep out of the EPS and C&DH paths.
        offences = []
        for path in sim_modules():
            if path.name in MATH_EXEMPT_MODULES:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] == "math" for a in node.names):
                        offences.append(f"{path.name}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] == "math":
                        offences.append(f"{path.name}:{node.lineno}")
        self.assertEqual(offences, [],
                         f"math imported at some scope in a non-exempt module: "
                         f"{offences}")

    def test_the_exempt_module_is_still_held_to_the_clock_and_entropy_rules(self):
        """The exemption is for `math` alone. A clock read in sim/orbit.py would break
        run-to-run reproducibility just as surely as one anywhere else."""
        path = SIM_DIR / "orbit.py"
        self.assertTrue(path.exists())
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offences = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in (FORBIDDEN_IMPORTS - {"math"}):
                        offences.append(f"import {root}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in (FORBIDDEN_IMPORTS - {"math"}):
                    offences.append(f"from {root} import")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = (node.func.value.id
                         if isinstance(node.func.value, ast.Name) else None)
                if (owner, node.func.attr) in FORBIDDEN_CALLS:
                    offences.append(f"{owner}.{node.func.attr}()")
                if owner == "random" and node.func.attr in FORBIDDEN_RANDOM_FUNCTIONS:
                    offences.append(f"random.{node.func.attr}()")
        self.assertEqual(offences, [],
                         f"sim/orbit.py reaches a non-deterministic source other than "
                         f"math: {offences}")

    def test_no_clock_read_or_entropy_call_anywhere_in_the_scenario_path(self):
        offences = []
        for path in sim_modules():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                owner = func.value.id if isinstance(func.value, ast.Name) else None
                if owner is None:
                    continue
                if (owner, func.attr) in FORBIDDEN_CALLS:
                    offences.append(f"{path.name}:{node.lineno} {owner}.{func.attr}()")
                if owner == "random" and func.attr in FORBIDDEN_RANDOM_FUNCTIONS:
                    offences.append(f"{path.name}:{node.lineno} random.{func.attr}() "
                                    f"uses the process-global generator")
        self.assertEqual(offences, [],
                         f"wall clock or unseeded randomness in the scenario path: "
                         f"{offences}")

    def test_the_scan_would_catch_a_violation(self):
        """The scan's own red case. Without this, 'no violations found' is
        indistinguishable from 'the scan does not work' — the direction-claim rule
        the record earned at G001-12 F-02.
        """
        planted = ("import time\n"
                   "import random\n"
                   "def go():\n"
                   "    t = time.time()\n"
                   "    x = random.random()\n"
                   "    r = random.Random(7)\n"
                   "    return t, x, r\n")
        tree = ast.parse(planted)
        import_hits, call_hits, allowed = [], [], []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        import_hits.append(alias.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = (node.func.value.id
                         if isinstance(node.func.value, ast.Name) else None)
                if (owner, node.func.attr) in FORBIDDEN_CALLS:
                    call_hits.append(f"{owner}.{node.func.attr}")
                elif owner == "random" and node.func.attr in FORBIDDEN_RANDOM_FUNCTIONS:
                    call_hits.append(f"random.{node.func.attr}")
                elif owner == "random" and node.func.attr == "Random":
                    allowed.append("random.Random")
        self.assertEqual(import_hits, ["time"], "the import scan missed `import time`")
        self.assertEqual(sorted(call_hits), ["random.random", "time.time"],
                         "the call scan missed a planted violation")
        self.assertEqual(allowed, ["random.Random"],
                         "random.Random(seed) is explicitly permitted and must not be "
                         "flagged; flagging it would push scenarios toward the global "
                         "generator instead")


class TestNoWallClockOrUnseededRandomnessAtRuntime(unittest.TestCase):
    """The runtime half: trap the sources, then actually run a scenario."""
    verifies = ("HUG-SYS-003", "HUG-SYS-004")

    def test_a_full_scenario_runs_with_the_clock_and_entropy_trapped(self):
        import datetime as datetime_module
        import random as random_module
        import time as time_module

        tripped = []

        def trap(label):
            def boom(*args, **kwargs):
                tripped.append(label)
                raise AssertionError(f"scenario path called {label}")
            return boom

        saved = {}
        for module, names in ((time_module, ("time", "monotonic", "perf_counter",
                                             "time_ns", "monotonic_ns")),
                              (random_module, ("random", "randint", "choice",
                                               "shuffle", "getrandbits", "uniform"))):
            for name in names:
                if hasattr(module, name):
                    saved[(module, name)] = getattr(module, name)
                    setattr(module, name, trap(f"{module.__name__}.{name}"))
        saved_dt = datetime_module.datetime
        try:
            class TrappedDatetime(datetime_module.datetime):
                @classmethod
                def now(cls, tz=None):
                    tripped.append("datetime.now")
                    raise AssertionError("scenario path called datetime.now")

                @classmethod
                def utcnow(cls):
                    tripped.append("datetime.utcnow")
                    raise AssertionError("scenario path called datetime.utcnow")
            datetime_module.datetime = TrappedDatetime

            frames = spacecraft("P4_hk_generation_halt").run()
            self.assertGreater(len(frames), 0,
                               "the trapped run produced no frames, so it proved "
                               "nothing about the scenario path")
        finally:
            datetime_module.datetime = saved_dt
            for (module, name), original in saved.items():
                setattr(module, name, original)

        self.assertEqual(tripped, [],
                         f"the scenario path reached a trapped source: {tripped}")

    def test_the_runtime_trap_would_catch_a_violation(self):
        """The trap's own red case: something that does read the clock must trip it."""
        import time as time_module
        saved = time_module.time
        tripped = []

        def boom(*args, **kwargs):
            tripped.append("time.time")
            raise AssertionError("trapped")
        time_module.time = boom
        try:
            with self.assertRaises(AssertionError):
                time_module.time()
        finally:
            time_module.time = saved
        self.assertEqual(tripped, ["time.time"],
                         "the runtime trap did not fire on a real clock read")


if __name__ == "__main__":
    unittest.main(verbosity=2)
