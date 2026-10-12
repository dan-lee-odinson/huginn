#!/usr/bin/env python3
"""Surrogate reference orbit: propagation, eclipse, contact windows, SAA transits.

HUG-SYS-002: "The simulator shall propagate spacecraft position from the pinned
surrogate reference element set stored in `defs/orbit/`, and shall derive eclipse state
and ground-terminal visibility from that propagation."

Built under owner ruling D-003: element set from the ruled class (pinned in
`defs/orbit/element_set.tle`, provenance in `SOURCE.md`), SGP4 propagation via the
`sgp4` package, and an analytical solar position for eclipse rather than a pinned
ephemeris binary.

TERMINOLOGY, BINDING: this is a **surrogate reference orbit derived from a public
element set**. Never "a real TLE" (Brief terminology rules). The pinned object is real;
HUGINN is not, and the surrogate is not the object.

WHAT THE OPERATOR GETS FROM THIS, AND WHY THE RECORD WANTS IT HERE

  Eclipse. The battery charge/discharge cycle is "the central operational rhythm of the
  mission" (CONOPS Sec. 1.1) and eclipse drives it. The ground computes it from the
  propagated orbit, so it is known whether or not the spacecraft can be heard - which is
  exactly why track[].ecl in the replay package renders from here and not from the
  telemetered ADM_ECLIPSE (RS-7-08, replay_schema.md Sec. 4).

  Contact windows. CON-01 and HUG-GND-005: telemetry is receivable and commands
  sendable ONLY inside a computed window. A pass plan is a prediction from this
  propagation, and the operator's first question at AOS is whether the spacecraft
  arrived when the plan said it would.

  SAA transits. Objective O1 counts them. v0.1 does not exercise O1 - the payload is a
  switchable load, not a sensor - but the count is what the full mission is for, and
  computing it now means the campaign's geometry is the geometry the objective would
  eventually be measured against.

REPRODUCIBILITY, STATED PRECISELY (owner ruling D-003 item 4)

  The EPS and C&DH models use only + - * / on floats, which are IEEE-754 exact, so they
  are byte-identical across runs and across machines. Propagation cannot be: SGP4 and
  the coordinate transforms below use trigonometric functions, whose last bits can
  differ between platform maths libraries.

  HUG-SYS-003 requires reproducibility ACROSS RUNS. That holds here and is tested. Byte
  equality ACROSS MACHINES is a stronger property the record does not require, the owner
  ruled against paying for, and this module therefore does not claim it. Saying so here
  is the point: a claim that only held on one machine would be worse than no claim.
"""
import math
from pathlib import Path

import yaml
from sgp4.api import Satrec, jday

# WGS-84
EARTH_A_KM = 6378.137
EARTH_F = 1.0 / 298.257223563
EARTH_E2 = 2.0 * EARTH_F - EARTH_F * EARTH_F
EARTH_B_KM = EARTH_A_KM * (1.0 - EARTH_F)


class OrbitNotPinned(RuntimeError):
    """Raised when no element set is pinned in defs/orbit/, or the pin is corrupt."""


# ------------------------------------------------------------------- element set

def tle_checksum_ok(line):
    """TLE mod-10 checksum: digits count as themselves, '-' as 1, everything else 0.

    Re-checked every time the element set is loaded, not only when it was selected. The
    pin is a file in a repository; a corrupted digit would still propagate to a
    plausible-looking orbit that is not the object's, and nothing downstream would
    notice.
    """
    if len(line) < 69:
        return False
    total = 0
    for ch in line[:68]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return line[68].isdigit() and int(line[68]) == total % 10


def load_element_set(orbit_dir):
    """(name, line1, line2) from the pinned file, checksums verified."""
    path = Path(orbit_dir) / "element_set.tle"
    if not path.exists():
        raise OrbitNotPinned(
            f"no element set pinned at {path}. HUG-SYS-002 requires propagation from "
            f"the pinned set; see defs/orbit/SOURCE.md.")
    lines = [l for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]
    if len(lines) < 3:
        raise OrbitNotPinned(f"{path} does not hold a three-line element set")
    name, line1, line2 = lines[0].strip(), lines[1], lines[2]
    for index, line in ((1, line1), (2, line2)):
        if not tle_checksum_ok(line):
            raise OrbitNotPinned(
                f"{path} line {index} fails its mod-10 checksum. The pinned element set "
                f"is corrupt; restore it from the source recorded in SOURCE.md rather "
                f"than propagating from it.")
    return name, line1, line2


# ------------------------------------------------------------------ time and sun

def iso_to_jd(iso):
    """ISO 8601 UTC instant to (jd, fr).

    Parsed by hand: `datetime` is deliberately absent from the scenario path (see
    tests/test_reproducibility.py), and turning a fixed string into numbers needs no
    calendar library.
    """
    text = iso.strip().replace("Z", "").replace("T", " ")
    date_part, _, time_part = text.partition(" ")
    y, m, d = (int(x) for x in date_part.split("-"))
    hh = mm = 0
    ss = 0.0
    if time_part:
        bits = time_part.split(":")
        hh = int(bits[0])
        mm = int(bits[1]) if len(bits) > 1 else 0
        ss = float(bits[2]) if len(bits) > 2 else 0.0
    return jday(y, m, d, hh, mm, ss)


def sun_unit_vector_eci(jd_total):
    """Unit vector to the Sun in ECI, from a low-precision analytical solar position.

    Accurate to well under a degree, against an eclipse boundary the spacecraft crosses
    in a few seconds. Ruling D-003 chose this over a pinned JPL ephemeris binary, and
    solar precision is not the binding constraint on anything downstream.
    """
    n = jd_total - 2451545.0
    L = math.radians((280.460 + 0.9856474 * n) % 360.0)
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2.0 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    return (math.cos(lam),
            math.cos(eps) * math.sin(lam),
            math.sin(eps) * math.sin(lam))


def gmst_rad(jd_total):
    """Greenwich mean sidereal time (IAU 1982)."""
    T = (jd_total - 2451545.0) / 36525.0
    seconds = (67310.54841
               + (876600.0 * 3600.0 + 8640184.812866) * T
               + 0.093104 * T * T
               - 6.2e-6 * T * T * T)
    return math.radians((seconds / 240.0) % 360.0)


# --------------------------------------------------------------- transformations

def eci_to_ecef(r_eci, jd_total):
    theta = gmst_rad(jd_total)
    c, s = math.cos(theta), math.sin(theta)
    x, y, z = r_eci
    return (x * c + y * s, -x * s + y * c, z)


def ecef_to_geodetic(r_ecef):
    """WGS-84 geodetic latitude, longitude, altitude, iterated to convergence."""
    x, y, z = r_ecef
    lon = math.atan2(y, x)
    p = math.sqrt(x * x + y * y)
    lat = math.atan2(z, p)
    n = EARTH_A_KM
    for _ in range(8):
        sin_lat = math.sin(lat)
        n = EARTH_A_KM / math.sqrt(1.0 - EARTH_E2 * sin_lat * sin_lat)
        lat = math.atan2(z + n * EARTH_E2 * sin_lat, p)
    cos_lat = math.cos(lat)
    alt = (p / cos_lat) - n if abs(cos_lat) > 1e-12 else abs(z) - EARTH_B_KM
    return math.degrees(lat), math.degrees(lon), alt


def geodetic_to_ecef(lat_deg, lon_deg, alt_km):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    n = EARTH_A_KM / math.sqrt(1.0 - EARTH_E2 * sin_lat * sin_lat)
    return ((n + alt_km) * cos_lat * math.cos(lon),
            (n + alt_km) * cos_lat * math.sin(lon),
            (n * (1.0 - EARTH_E2) + alt_km) * sin_lat)


def look_angles(site_geodetic, r_ecef):
    """Topocentric azimuth, elevation and range of r_ecef from the site.

    Azimuth is 0 at north increasing clockwise, and elevation is negative below the
    horizon — the conventions replay_schema.md Sec. 4 states for track[].az_deg and
    el_deg, so the recorder needs no second transform of its own.
    """
    lat_deg, lon_deg, alt_km = site_geodetic
    site = geodetic_to_ecef(lat_deg, lon_deg, alt_km)
    d = (r_ecef[0] - site[0], r_ecef[1] - site[1], r_ecef[2] - site[2])
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    east = -sin_lon * d[0] + cos_lon * d[1]
    north = -sin_lat * cos_lon * d[0] - sin_lat * sin_lon * d[1] + cos_lat * d[2]
    up = cos_lat * cos_lon * d[0] + cos_lat * sin_lon * d[1] + sin_lat * d[2]
    rng = math.sqrt(east * east + north * north + up * up)
    az = math.degrees(math.atan2(east, north)) % 360.0
    el = math.degrees(math.asin(up / rng)) if rng > 0.0 else 0.0
    return az, el, rng


# ------------------------------------------------------------------------ orbit

class Orbit:
    """The pinned surrogate reference orbit, propagated from a campaign start epoch."""

    def __init__(self, orbit_dir, start_epoch_utc):
        orbit_dir = Path(orbit_dir)
        self.name, self.line1, self.line2 = load_element_set(orbit_dir)
        self.satrec = Satrec.twoline2rv(self.line1, self.line2)

        station = yaml.safe_load(
            (orbit_dir / "ground_station.yaml").read_text(encoding="utf-8"))
        self.station_callsign = station["callsign"]
        self.elevation_mask_deg = float(station["contact_model"]["elevation_mask_deg"])
        site = station["site"]
        self.site = (float(site["latitude_deg"]), float(site["longitude_deg"]),
                     float(site["elevation_m"]) / 1000.0)
        self.site_status = site.get("status", "pinned")

        regions = yaml.safe_load((orbit_dir / "regions.yaml").read_text(encoding="utf-8"))
        saa = regions["south_atlantic_anomaly"]
        self.saa_lat = tuple(float(x) for x in saa["latitude_deg"])
        self.saa_lon = tuple(float(x) for x in saa["longitude_deg"])
        self.saa_min_transit_s = float(saa["minimum_transit_s"])
        self.auroral_lat_deg = float(regions["high_latitude_auroral"]["poleward_of_deg"])

        self.jd0, self.fr0 = iso_to_jd(start_epoch_utc)
        self.start_epoch_utc = start_epoch_utc

    # ------------------------------------------------------------------ sampling

    def _jd_at(self, t_s):
        """(jd, fr) at t_s after the campaign start epoch.

        The day fraction is carried separately and normalised, which is why sgp4 offers
        the split signature: folding the offset into a single large Julian date loses
        sub-second precision at these magnitudes.
        """
        fr = self.fr0 + t_s / 86400.0
        jd = self.jd0
        while fr >= 1.0:
            fr -= 1.0
            jd += 1.0
        return jd, fr

    def position_eci(self, t_s):
        jd, fr = self._jd_at(t_s)
        err, r, _v = self.satrec.sgp4(jd, fr)
        if err != 0:
            raise RuntimeError(
                f"SGP4 propagation failed at t+{t_s} s with error code {err}. The "
                f"pinned element set cannot be propagated to this time; check the "
                f"campaign epoch against the element epoch in defs/orbit/SOURCE.md.")
        return r, jd + fr

    def subpoint(self, t_s):
        """Geodetic latitude, longitude and altitude of the sub-satellite point."""
        r_eci, jd_total = self.position_eci(t_s)
        return ecef_to_geodetic(eci_to_ecef(r_eci, jd_total))

    def illuminated_at(self, t_s):
        """True when sunlit. Cylindrical Earth-shadow model: in eclipse when on the
        anti-sun side of the terminator plane AND inside the shadow cylinder.

        Cylindrical rather than conical, deliberately. The penumbra at this altitude is
        crossed in a few seconds, and the model's own array ramp is 10 s (HUG-EPS-002) —
        a penumbral refinement would be finer than the thing it feeds.
        """
        r_eci, jd_total = self.position_eci(t_s)
        s = sun_unit_vector_eci(jd_total)
        along = r_eci[0] * s[0] + r_eci[1] * s[1] + r_eci[2] * s[2]
        if along > 0.0:
            return True
        perp = (r_eci[0] - along * s[0], r_eci[1] - along * s[1], r_eci[2] - along * s[2])
        distance = math.sqrt(perp[0] ** 2 + perp[1] ** 2 + perp[2] ** 2)
        return distance > EARTH_A_KM

    def look_angles_at(self, t_s):
        r_eci, jd_total = self.position_eci(t_s)
        return look_angles(self.site, eci_to_ecef(r_eci, jd_total))

    def visible_at(self, t_s):
        """CON-01 / HUG-GND-005: inside a contact window above the elevation mask."""
        _az, el, _rng = self.look_angles_at(t_s)
        return el >= self.elevation_mask_deg

    def in_saa_at(self, t_s):
        lat, lon, _alt = self.subpoint(t_s)
        return (self.saa_lat[0] <= lat <= self.saa_lat[1]
                and self.saa_lon[0] <= lon <= self.saa_lon[1])

    def poleward_at(self, t_s):
        """Objective O2's auroral regions: poleward of the stated geographic latitude."""
        lat, _lon, _alt = self.subpoint(t_s)
        return abs(lat) >= self.auroral_lat_deg

    # ------------------------------------------------------------------ intervals

    def _intervals(self, predicate, duration_s, step_s, minimum_s=0.0):
        """Half-open [start, end) intervals over which predicate holds.

        Sampled on a fixed grid rather than root-found, at the caller's step. A boundary
        resolved finer than the model's own time step would be a precision the campaign
        cannot observe, and the grid keeps the result a pure function of its inputs.
        """
        out, start = [], None
        t = 0.0
        while t < duration_s:
            if predicate(t):
                if start is None:
                    start = t
            elif start is not None:
                if t - start >= minimum_s:
                    out.append((start, t))
                start = None
            t += step_s
        if start is not None and duration_s - start >= minimum_s:
            out.append((start, duration_s))
        return out

    def eclipse_intervals(self, duration_s, step_s=5.0):
        return self._intervals(lambda t: not self.illuminated_at(t), duration_s, step_s)

    def contact_windows(self, duration_s, step_s=10.0):
        return self._intervals(self.visible_at, duration_s, step_s)

    def saa_transits(self, duration_s, step_s=10.0):
        return self._intervals(self.in_saa_at, duration_s, step_s,
                               minimum_s=self.saa_min_transit_s)

    # -------------------------------------------------------------------- summary

    def revs_per_day(self):
        return self.satrec.no_kozai * 1440.0 / (2.0 * math.pi)

    def geometry_summary(self, duration_s=86400.0):
        """Computed contact and eclipse geometry - the values HUG-SYS-002 requires
        replace CONOPS Sec. 3.3's representative ones."""
        eclipses = self.eclipse_intervals(duration_s)
        contacts = self.contact_windows(duration_s)
        transits = self.saa_transits(duration_s)
        n = self.revs_per_day()
        return {
            "object": self.name,
            "epoch_utc": self.start_epoch_utc,
            "period_min": 1440.0 / n if n else float("nan"),
            "orbits_per_day": n,
            "eclipse_count": len(eclipses),
            "eclipse_mean_min": (sum(b - a for a, b in eclipses) / len(eclipses) / 60.0
                                 if eclipses else 0.0),
            "eclipse_fraction": (sum(b - a for a, b in eclipses) / duration_s
                                 if duration_s else 0.0),
            "contact_count": len(contacts),
            "contact_mean_min": (sum(b - a for a, b in contacts) / len(contacts) / 60.0
                                 if contacts else 0.0),
            "contact_longest_min": (max(b - a for a, b in contacts) / 60.0
                                    if contacts else 0.0),
            "saa_transits": len(transits),
        }
