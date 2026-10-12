# Pinned surrogate reference element set — source note

Required by the concept brief: the chosen element set is "recorded in the repository
with its epoch and source, pinned (never auto-updated), so every campaign result is
reproducible". This is that record.

**Terminology, binding everywhere (Brief §terminology):** this is a **surrogate
reference orbit derived from a public element set**. Never "a real TLE". HUGINN is a
fictional spacecraft; CELTEE 1 is a real object whose orbit HUGINN's surrogate is
derived from, and the two are not the same thing.

## The pin

| Field | Value |
|---|---|
| File | `defs/orbit/element_set.tle` |
| File sha256 | `0bf4be06332139804efee8904572bd93ed9deee5a8893c7e4a1f494f4e29e679` |
| Object | CELTEE 1 |
| NORAD catalogue number | 41850 |
| International designator | 2016-067C |
| Element epoch | 2026 day 209.61814869 UTC (2026-07-28, ~14:50 UTC) |
| Source | CelesTrak, `GROUP=cubesat&FORMAT=tle` |
| Retrieved | 2026-07-29 |
| Selected under | Owner ruling **D-003 item 1** — "6U CubeSat on an SSO rideshare" |
| Status | **CONFIRMED by owner ruling D-004 item 1 (2026-07-29)** as the surrogate source object. |

**Never auto-updated.** No tool in this repository fetches element sets at run time.
`sim/orbit.py` reads this file and nothing else. ASM-03 requires contact geometry stable
across all four campaign passes, and a live fetch would break that between passes.

## Verification performed at selection, recorded rather than asserted

| Check | Result |
|---|---|
| Line 1 mod-10 checksum | **VALID** |
| Line 2 mod-10 checksum | **VALID** |
| `sgp4.Satrec.twoline2rv` parses | **OK** |
| `sgp4` propagation at 2026-07-29 12:00 UTC | **error code 0** |

The checksums matter because the element set arrived as fetched text. A single altered
digit would have produced a plausible-looking orbit that is not the object's, and no
downstream check would have noticed. Ten candidates were fetched and all ten verified;
the checksum test is re-run by the test suite so the pin cannot rot.

## Derived geometry, and how it compares to the record

| Quantity | Computed from the pinned set | Record's representative value | Note |
|---|---|---|---|
| Inclination | 98.062° | sun-synchronous | Inside the 97°–99° sun-synchronous band |
| Eccentricity | 0.0002569 | — | Near-circular; the lowest of the verified candidates |
| Mean altitude | 505.7 km | ~550 km | 44 km low |
| Perigee / apogee altitude | 503.9 / 507.4 km | — | 3.5 km spread |
| Orbital period | 94.73 min | ~96 min | 1.27 min short |
| LTAN | 08:44 | mid-morning | Mid-morning |

**Why a 44 km difference is not a defect.** The brief asks for an element set "for an
existing satellite in a **comparable** orbit", not an identical one, and CONOPS §3.3
states its own figures are "representative until the surrogate element set is pinned in
the repository; **computed values from the pinned orbit replace them at build**
(HUG-SYS-002)". The record therefore anticipates that computed values differ from the
representative ones — replacing them is the build obligation, not a deviation from it.

Worth recording as the reason no closer match exists: of ten verified candidates, none
was simultaneously above 520 km **and** mid-morning. Sun-synchronous CubeSats at
mid-morning LTAN in the current catalogue sit nearer 490–510 km, having decayed from
their insertion altitudes. CELTEE 1 is the best available on the two quantities that
drive eclipse duration and contact windows — altitude and period — among those that are
also mid-morning and near-circular.

Candidates verified and set aside:

| Object | Altitude | Period | LTAN | Set aside because |
|---|---|---|---|---|
| OPTICUBE 04 | 536.7 km | 95.38 min | 07:45 | Closest altitude, but LTAN is early morning and eccentricity 0.0015 is the highest of the set |
| UKUBE-1 | 523.6 km | 95.10 min | 17:58 | LTAN is late afternoon |
| SKYSAT-B | 603.8 km | 96.77 min | 14:52 | Best period, but LTAN is early afternoon and it is not a CubeSat |
| AEROCUBE 8D | 490.9 km | 94.43 min | 09:00 | LTAN centres mid-morning best, but 59 km low |
| AEROCUBE 8C | 490.2 km | 94.41 min | 08:49 | 60 km low |
| SKYSAT-C1 / C5 / C10, FLOCK 4BE-27 | 455–465 km | 93.7–93.9 min | evening / night | Too low and not mid-morning; SKYSAT-C1 is also outside the sun-synchronous inclination band |

## Ground terminal

GS-RAVENSROOST's site coordinates are in `defs/orbit/ground_station.yaml`, pinned
alongside this element set because ASM-03 requires the whole contact geometry stable
across the campaign. **They are pinned by owner ruling D-004 item 2** at the Kennedy
Space Center Visitor Complex, verified the same way this element set was — see that
file, which also records the different facility ruled out and why a name match alone
did not identify the site.

## Computed geometry now in the record

The geometry computed from this element set together with the pinned site has been
landed in CONOPS §3.3 as v0.9 (ruling D-004), replacing the representative values that
section carried through v0.8. That replacement is what HUG-SYS-002 requires and what
v0.8's own §3.3 said would happen at build.

## Sources

- [CelesTrak GP data, CubeSat group](https://celestrak.org/NORAD/elements/gp.php?GROUP=cubesat&FORMAT=tle)
- [CelesTrak: GP data formats](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [CelesTrak: Historical NORAD Two-Line Element Sets](http://celestrak.org/NORAD/archives/)
