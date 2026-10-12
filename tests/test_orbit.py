#!/usr/bin/env python3
"""The pinned surrogate reference orbit: the pin's integrity, and the geometry
HUG-SYS-002 requires be derived from it.

Built under owner ruling D-003. Two things these tests exist to hold:

  THE PIN CANNOT ROT. The element set arrived as fetched text and lives as a file in a
  repository. A single altered digit would still propagate to a plausible-looking orbit
  that is not the object's, and every downstream number - eclipse timing, contact
  windows, SAA counts - would look entirely reasonable while being wrong. The mod-10
  checksum is therefore re-verified on every load, and that check carries its own red
  case here.

  REPRODUCIBILITY IS CLAIMED ONLY WHERE IT HOLDS. Ruling D-003 item 4: across runs, not
  across machines. Propagation uses trigonometry, whose last bits can differ between
  platform maths libraries. These tests assert same-machine run-to-run equality and
  deliberately do not assert cross-machine byte equality - the record does not require
  it and a claim that held on one machine would be worse than no claim.
"""
import math
import unittest
from pathlib import Path

from harness import REPO

from sim.orbit import (EARTH_A_KM, Orbit, OrbitNotPinned, load_element_set,
                       tle_checksum_ok)

ORBIT_DIR = REPO / "defs" / "orbit"
EPOCH = "2026-07-29T00:00:00Z"
DAY_S = 86400.0


def _separation_m(p, q):
    """Great-circle separation between two (lat, lon) points, in metres."""
    la1, la2 = math.radians(p[0]), math.radians(q[0])
    dla, dlo = math.radians(q[0] - p[0]), math.radians(q[1] - p[1])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def orbit():
    return Orbit(ORBIT_DIR, EPOCH)


class TestThePinsIntegrity(unittest.TestCase):
    verifies = ("HUG-SYS-002",)

    def test_the_pinned_element_set_loads_with_valid_checksums(self):
        name, line1, line2 = load_element_set(ORBIT_DIR)
        self.assertTrue(name, "the pinned element set has no object name")
        for index, line in ((1, line1), (2, line2)):
            self.assertEqual(len(line), 69,
                             f"line {index} is {len(line)} characters, not 69")
            self.assertTrue(tle_checksum_ok(line),
                            f"line {index} of the pinned element set fails its "
                            f"mod-10 checksum")

    def test_a_corrupted_digit_is_refused(self):
        """The checksum's red case. Without it, 'checksums valid' is
        indistinguishable from 'the checksum function returns True'."""
        _name, line1, _line2 = load_element_set(ORBIT_DIR)
        # Flip one digit in the middle of the line, leaving the checksum character.
        position = 30
        original = line1[position]
        replacement = "0" if original != "0" else "1"
        corrupted = line1[:position] + replacement + line1[position + 1:]
        self.assertNotEqual(corrupted, line1)
        self.assertFalse(tle_checksum_ok(corrupted),
                         "a single altered digit passed the checksum, so a corrupted "
                         "pin would propagate silently")

    def test_a_missing_pin_raises_rather_than_guessing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(OrbitNotPinned):
                load_element_set(td)

    def test_a_corrupt_pin_on_disk_raises_rather_than_propagating(self):
        import tempfile
        _name, line1, line2 = load_element_set(ORBIT_DIR)
        with tempfile.TemporaryDirectory() as td:
            bad = line1[:30] + ("0" if line1[30] != "0" else "1") + line1[31:]
            (Path(td) / "element_set.tle").write_text(
                f"CORRUPTED\n{bad}\n{line2}\n", encoding="utf-8")
            with self.assertRaises(OrbitNotPinned):
                load_element_set(td)

    def test_the_source_note_records_what_the_brief_requires(self):
        """The brief requires the element set be recorded "with its epoch and source,
        pinned (never auto-updated)". A pin with no provenance is not a pin."""
        note = (ORBIT_DIR / "SOURCE.md").read_text(encoding="utf-8")
        for required in ("NORAD catalogue number", "41850", "Element epoch",
                         "Source", "Retrieved", "Never auto-updated"):
            self.assertIn(required, note,
                          f"the source note does not record {required!r}")

    def test_nothing_in_the_orbit_path_fetches_at_run_time(self):
        """ASM-03 needs contact geometry stable across all four campaign passes. A live
        fetch would let it change between them."""
        source = (REPO / "sim" / "orbit.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "requests", "http.client", "socket", "urlopen"):
            self.assertNotIn(forbidden, source,
                             f"sim/orbit.py references {forbidden!r}; the pinned "
                             f"element set must never be fetched at run time")


class TestPropagationAndGeometry(unittest.TestCase):
    verifies = ("HUG-SYS-002",)

    @classmethod
    def setUpClass(cls):
        cls.orbit = orbit()
        cls.summary = cls.orbit.geometry_summary(DAY_S)

    def test_propagation_succeeds_across_a_campaign_duration(self):
        for t in (0.0, 3600.0, DAY_S, DAY_S * 4):
            r, _jd = self.orbit.position_eci(t)
            radius = math.sqrt(sum(c * c for c in r))
            self.assertGreater(radius, EARTH_A_KM,
                               f"propagated position at t+{t} s is inside the Earth")
            self.assertLess(radius, EARTH_A_KM + 2000.0,
                            f"propagated position at t+{t} s is not in low Earth orbit")

    def test_the_orbit_is_sun_synchronous(self):
        incl = math.degrees(self.orbit.satrec.inclo)
        self.assertGreaterEqual(incl, 97.0)
        self.assertLessEqual(incl, 99.0)

    def test_the_period_agrees_with_the_mean_motion(self):
        n = self.orbit.revs_per_day()
        self.assertAlmostEqual(self.summary["period_min"], 1440.0 / n, places=6)
        self.assertGreater(self.summary["period_min"], 90.0)
        self.assertLess(self.summary["period_min"], 100.0)

    def test_the_subpoint_stays_on_the_globe(self):
        for t in range(0, int(DAY_S), 971):
            lat, lon, alt = self.orbit.subpoint(float(t))
            self.assertGreaterEqual(lat, -90.0)
            self.assertLessEqual(lat, 90.0)
            self.assertGreater(lon, -180.0)
            self.assertLessEqual(lon, 180.0)
            self.assertGreater(alt, 300.0, "sub-satellite altitude below LEO")
            self.assertLess(alt, 900.0)

    def test_the_ground_track_reaches_the_latitudes_the_mission_needs(self):
        """CONOPS Sec. 1.1: radiation mapping "requires latitude coverage from
        equatorial to polar". Objective O2 samples poleward of 60 deg."""
        lats = [self.orbit.subpoint(float(t))[0] for t in range(0, int(DAY_S), 60)]
        self.assertGreater(max(lats), self.orbit.auroral_lat_deg,
                           "the ground track never reaches the northern auroral region")
        self.assertLess(min(lats), -self.orbit.auroral_lat_deg,
                        "the ground track never reaches the southern auroral region")
        self.assertTrue(any(abs(l) < 5.0 for l in lats),
                        "the ground track never crosses the equatorial region")

    def test_eclipse_occurs_once_per_orbit_and_alternates_with_sunlight(self):
        """CONOPS Sec. 1.1: the orbit "places the spacecraft in eclipse every orbit"
        and makes the charge/discharge cycle the operational rhythm."""
        eclipses = self.orbit.eclipse_intervals(DAY_S)
        orbits = self.summary["orbits_per_day"]
        self.assertGreaterEqual(len(eclipses), int(orbits) - 1,
                                f"{len(eclipses)} eclipses in a day of {orbits:.2f} "
                                f"orbits; the record requires one every orbit")
        self.assertLessEqual(len(eclipses), int(orbits) + 1)
        for a, b in eclipses:
            self.assertGreater(b, a, "an eclipse interval is not forward in time")
        for (a1, b1), (a2, _b2) in zip(eclipses, eclipses[1:]):
            self.assertLess(b1, a2, "eclipse intervals overlap")
            self.assertTrue(self.orbit.illuminated_at((b1 + a2) / 2.0),
                            "the gap between two eclipses is not sunlit")

    def test_the_eclipse_fraction_is_physically_plausible(self):
        fraction = self.summary["eclipse_fraction"]
        self.assertGreater(fraction, 0.20,
                           "an eclipse fraction this low is not credible for a "
                           "sun-synchronous low Earth orbit")
        self.assertLess(fraction, 0.40)

    def test_every_contact_window_is_above_the_mask_and_the_gaps_are_below_it(self):
        """CON-01 / HUG-GND-005: telemetry receivable and commands sendable ONLY inside
        a computed window. A window that is not really above the mask would license
        commanding the spacecraft cannot hear."""
        windows = self.orbit.contact_windows(DAY_S)
        self.assertGreater(len(windows), 0, "the site sees no contacts at all in a day")
        mask = self.orbit.elevation_mask_deg
        for a, b in windows:
            mid = (a + b) / 2.0
            _az, el, _rng = self.orbit.look_angles_at(mid)
            self.assertGreaterEqual(el, mask,
                                    f"window [{a}, {b}) has elevation {el:.2f} deg at "
                                    f"its midpoint, below the {mask} deg mask")
        # Halfway between consecutive windows the spacecraft must be out of contact.
        for (_a1, b1), (a2, _b2) in zip(windows, windows[1:]):
            _az, el, _rng = self.orbit.look_angles_at((b1 + a2) / 2.0)
            self.assertLess(el, mask,
                            "the spacecraft is above the mask between two windows, so "
                            "they should have been one window")

    def test_look_angles_use_the_schema_conventions(self):
        """replay_schema.md Sec. 4 / RS-7-09: az in [0, 360), el in [-90, 90]."""
        for t in range(0, int(DAY_S), 613):
            az, el, rng = self.orbit.look_angles_at(float(t))
            self.assertGreaterEqual(az, 0.0)
            self.assertLess(az, 360.0)
            self.assertGreaterEqual(el, -90.0)
            self.assertLessEqual(el, 90.0)
            self.assertGreater(rng, 0.0)

    def test_saa_transits_clear_the_o1_target_when_scaled_to_a_week(self):
        """Objective O1: at least 20 SAA transits per week with the payload active.
        v0.1 does not exercise O1, but the geometry must be capable of it or the
        objective would be unreachable by construction."""
        per_day = self.summary["saa_transits"]
        self.assertGreaterEqual(per_day * 7, 20,
                                f"{per_day} SAA transits/day is {per_day * 7}/week, "
                                f"below objective O1's 20/week")

    def test_every_saa_transit_is_inside_the_defined_region(self):
        for a, b in self.orbit.saa_transits(DAY_S):
            mid = (a + b) / 2.0
            self.assertTrue(self.orbit.in_saa_at(mid),
                            f"transit [{a}, {b}) midpoint is outside the SAA region")
            self.assertGreaterEqual(b - a, self.orbit.saa_min_transit_s,
                                    "a transit shorter than the minimum was counted")


class TestReproducibilityAcrossRuns(unittest.TestCase):
    """Owner ruling D-003 item 4: across runs. Not across machines."""
    verifies = ("HUG-SYS-003",)

    def test_two_orbits_from_the_same_pin_and_epoch_agree_exactly(self):
        a, b = orbit(), orbit()
        for t in (0.0, 137.0, 3600.0, 12345.0, DAY_S):
            self.assertEqual(repr(a.position_eci(t)[0]), repr(b.position_eci(t)[0]),
                             f"propagated position differs between runs at t+{t} s")
            self.assertEqual(repr(a.look_angles_at(t)), repr(b.look_angles_at(t)))
            self.assertEqual(a.illuminated_at(t), b.illuminated_at(t))

    def test_interval_computation_reproduces_exactly(self):
        a, b = orbit(), orbit()
        self.assertEqual(a.contact_windows(DAY_S), b.contact_windows(DAY_S))
        self.assertEqual(a.eclipse_intervals(DAY_S), b.eclipse_intervals(DAY_S))
        self.assertEqual(a.saa_transits(DAY_S), b.saa_transits(DAY_S))

    def test_a_different_epoch_gives_a_different_result(self):
        """Guards against the reproducibility tests above being satisfied by a
        propagator that returns the same thing regardless of input."""
        a = Orbit(ORBIT_DIR, EPOCH)
        c = Orbit(ORBIT_DIR, "2026-07-30T00:00:00Z")
        self.assertNotEqual(repr(a.position_eci(0.0)[0]), repr(c.position_eci(0.0)[0]),
                            "the propagator ignores the campaign epoch")


class TestGroundStation(unittest.TestCase):
    verifies = ("HUG-GND-005",)

    def test_the_station_matches_the_record(self):
        o = orbit()
        self.assertEqual(o.station_callsign, "GS-RAVENSROOST")
        self.assertEqual(o.elevation_mask_deg, 10.0,
                         "CONOPS Sec. 3.3 states a 10 deg elevation mask")
        lat, lon, _alt = o.site
        # Central Florida, per the brief and dictionary ledger item 4.
        self.assertTrue(26.0 <= lat <= 30.0,
                        f"site latitude {lat} is not in central Florida")
        self.assertTrue(-83.0 <= lon <= -80.0,
                        f"site longitude {lon} is not in central Florida")

    def test_the_pinned_site_is_the_ruled_point_and_not_the_facility_ruled_out(self):
        """Owner ruling D-004 item 2, verified the way the element sets were.

        Two public sources publish coordinates 9.37 km apart under the SAME name,
        "Kennedy Space Center Visitor Complex". One of them is the Apollo/Saturn V
        Center. A name match therefore does not identify a site, and the owner ruled
        the correct point and named the wrong one explicitly. This asserts the pin is
        the ruled point - sub-metre from its authoritative reference - and is nowhere
        near the coordinate ruled out. 9.4 km of site displacement moves every computed
        contact window, and ASM-03 requires that geometry stable across the campaign.
        """
        import yaml
        station = yaml.safe_load(
            (ORBIT_DIR / "ground_station.yaml").read_text(encoding="utf-8"))
        site = station["site"]
        v = site["verification"]

        self.assertEqual(site["status"], "pinned")
        self.assertEqual(site["ruled_by"], "D-004")

        pinned = (float(site["latitude_deg"]), float(site["longitude_deg"]))
        reference = tuple(float(x) for x in v["authoritative_reference_deg"])
        ruled_out = tuple(float(x) for x in v["ruled_out_deg"])

        self.assertLess(_separation_m(pinned, reference), 5.0,
                        f"the pinned site is {_separation_m(pinned, reference):.1f} m "
                        f"from its recorded authoritative reference")
        self.assertGreater(_separation_m(pinned, ruled_out), 5000.0,
                           "the pinned site is close to the coordinate the owner ruled "
                           "out; the Apollo/Saturn V Center must not be substituted")
        self.assertAlmostEqual(_separation_m(pinned, ruled_out) / 1000.0,
                               float(v["ruled_out_separation_km"]), places=1,
                               msg="the recorded separation does not match the "
                                   "coordinates actually pinned")

    def test_the_orbit_uses_the_pinned_site_and_not_the_ruled_out_one(self):
        """The value the propagator actually reads, not just the value in the file."""
        import yaml
        station = yaml.safe_load(
            (ORBIT_DIR / "ground_station.yaml").read_text(encoding="utf-8"))
        ruled_out = tuple(float(x) for x in
                          station["site"]["verification"]["ruled_out_deg"])
        o = orbit()
        self.assertGreater(_separation_m((o.site[0], o.site[1]), ruled_out), 5000.0,
                           "the Orbit object is using the coordinate that was ruled out")


if __name__ == "__main__":
    unittest.main(verbosity=2)
