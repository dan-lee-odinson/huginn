# Surrogate reference orbit — options for the owner's ruling

Prepared 2026-07-29 at the owner's standing instruction: *"bring me the surrogate
reference orbit options before pinning the element set."* Nothing here is pinned.
His ruling goes in `DECISIONS.md`; this file is superseded by the pinned element set
and its source note once he has ruled.

Five decisions, and they are coupled — which is why they come together. Decisions 1–3
determine the contact and eclipse geometry every campaign pass runs on; decision 4 is
a value the record says is recorded in the repo and is not yet; decision 5 only has an
answer once the sunlit fraction is fixed.

What the record constrains, so the options stay inside it:

- **Sun-synchronous, ~550 km, mid-morning LTAN** (Brief §mission rationale, CONOPS
  §1.1, §3.3). Sun-synchronous orbits occupy a narrow band, roughly 97°–99°
  inclination and 500–900 km.
- **A surrogate reference orbit derived from a public element set**, "recorded in the
  repository with its epoch and source, pinned (never auto-updated), so every campaign
  result is reproducible" (Brief). Never "a real TLE" (Brief §terminology).
- **ASM-03:** the element set is pinned for the campaign; contact geometry is stable
  across all four passes.
- **HUG-SYS-002:** propagate from the pinned set; derive eclipse state and
  ground-terminal visibility from that propagation.
- **HUG-SYS-003:** bit-for-bit reproducible **across runs**.

A check on the record's own representative figures, before choosing anything: a
circular orbit at 550 km has a period of 95.5 min, which is CONOPS §3.3's "~96 minutes".
At 705 km it is 98.7 min and at 786 km 100.4 min. **The record's stated period is
consistent with ~550 km and not with the higher SSO altitudes**, which narrows
decision 1 more than it first appears.

---

## Decision 1 — which object's element set to derive from

| | Candidate class | Fits ~550 km | Fits mid-morning LTAN | Spacecraft class | Note |
|---|---|---|---|---|---|
| **1a** | A 6U-class CubeSat on an SSO rideshare (Transporter-class deployment) | **Yes** — these target roughly 500–550 km | **Yes** — mid-morning is the common rideshare LTAN | **6U CubeSat — matches HUGINN** | Apt in geometry *and* class. Needs a specific NORAD ID chosen, since many near-identical objects share a deployment |
| **1b** | A large Earth-observation satellite with published mid-morning LTAN (Landsat-class ~705 km LTAN 10:00; Sentinel-2-class ~786 km LTAN 10:30) | No — 705/786 km | Yes | Large EO platform | Well documented and stable, but the altitude contradicts the record's ~550 km and its ~96 min period |
| **1c** | A ~500–520 km SSO EO smallsat | Close | Varies by object | Smallsat, not CubeSat | Geometry fits; class does not |

**Recommendation: 1a.** It is the only class that fits both the altitude the record
states and the spacecraft class HUGINN is. Choosing 1b would mean either accepting
contact and eclipse numbers that disagree with CONOPS §3.3, or revising the record —
and the record is frozen.

## Decision 2 — where the element set comes from, and how it is pinned

| | Source | Immutable? | Note |
|---|---|---|---|
| **2a** | **CelesTrak historical archive** — a specific dated snapshot | **Yes** | The archive runs from 1980 to the present and exists to support exactly this: reproducible propagation from an archived snapshot |
| 2b | Space-Track | Yes, but account-gated | Credentials make a public repo awkward |
| 2c | CelesTrak current GP data, fetched at run time | **No** | **Violates the brief outright** — "pinned (never auto-updated)" |

**Recommendation: 2a.** Record in `defs/orbit/`: the element-set text verbatim, the
NORAD catalogue number, the element epoch, the retrieval date, and the source URL. That
satisfies the brief's "epoch and source" clause literally, and the file being in git
makes the pin enforceable rather than aspirational.

## Decision 3 — the propagator, which is also the dependency decision

Neither `sgp4` nor `skyfield` is installed on this machine; `numpy` is.

| | Approach | New dependencies | Fidelity | Reproducibility |
|---|---|---|---|---|
| **3a** | **`sgp4` package** on the pinned element set | one small pip package, no data files | The model the element set is *made for* — two-line element sets are Brouwer mean elements produced specifically for SGP4 | Exact for a fixed library version; same-machine byte-identical |
| 3b | Keplerian + J2 nodal regression, seeded from the element set, stdlib only | **none** | Adequate for eclipse intervals, a 10° elevation mask and SAA transits — the brief's own rule is that "model fidelity is bounded by the requirements" | Same-machine byte-identical |
| 3c | **Skyfield** | one package **plus a ~17 MB JPL ephemeris binary pinned in the repo** | Highest — precise sun geometry | Same-machine byte-identical |

The brief's risk table names Skyfield ("Skyfield handles orbit propagation"), so 3c has
record support — but that is a risk-mitigation note, not a requirement, and pinning a
17 MB binary into the repository of record is a real cost for sun-vector precision this
mission does not need.

**Recommendation: 3a, with an analytical low-precision sun position for eclipse.**
Propagating a TLE with anything other than SGP4 is a fidelity mismatch that would be
hard to defend at a gate; and the analytical sun position avoids the large binary while
being far more accurate than the eclipse geometry needs.

**One consequence to state plainly.** Today the simulator is bit-for-bit reproducible
because it uses only `+ - * /` on floats, which are IEEE-754 exact. Any propagator
introduces trigonometric functions, whose last bits can differ between platform maths
libraries. HUG-SYS-003 requires reproducibility **across runs**, which all three options
satisfy. Byte-identical results **across machines** is a stronger property the record
does not require, and none of the three gives it for free. If you want it, say so and
I will hold the orbit results to a fixed-point grid — but that is a decision, not a
default.

## Decision 4 — GS-RAVENSROOST site coordinates

**The record says these are recorded in the repository, and they are not.** Brief:
"one fictional ground terminal, callsign GS-RAVENSROOST, at a fixed site in central
Florida (site coordinates recorded in the repo)". Dictionary ledger item 4 says the
same. They cannot be derived; they are a value, and values are yours.

They must be pinned alongside the element set: ASM-03 requires stable contact geometry
across all four campaign passes, and the site is half of that geometry. A specific
latitude, longitude and elevation in central Florida is all that is needed.

## Decision 5 — FM-EPS-08's energy-negative statement

Coupled to the orbit, because the answer depends on the sunlit fraction the pinned
element set produces. **Measured, not estimated** (all figures per orbit, 5760 s orbit,
2100 s eclipse, sunlit fraction 0.6354, ratified envelope):

| Generation profile | Average sunlit generation | Payload ON + stuck load | Payload SHED + stuck load |
|---|---|---|---|
| Flat — the record's plain reading of HUG-EPS-002 | 17.00 W (100% of peak) | **+2.200 Wh** positive | **+6.940 Wh** positive |
| Cosine average (2/π) | 10.82 W (63.7% of peak) | **−3.766 Wh** negative | **+0.974 Wh** positive |

FM-EPS-08 states the "energy-negative trend persists **even after payload shed**".
For that to be literally true:

- average sunlit generation would have to be below **9.81 W — 57.7% of the ratified
  17 W peak**; a pure cosine average is 63.7%, so even that does not reach it;
- or the sunlit fraction would have to fall below **0.3767 — eclipse above 62% of the
  orbit**, which no sun-synchronous orbit at this altitude produces (a 550 km
  mid-morning SSO gives roughly 36%).

**So FM-EPS-08's stated end effect is not reachable from the ratified envelope at any
credible orbit.** That is a finding about the record, not about the model.

| | Reading | Cost |
|---|---|---|
| **5a** | Read "energy-negative trend" as the **worsening depth of discharge**, which the model does reproduce, and record that reading | No change to any ratified value. CONOPS P3's own words already match it: "actual SoC diverges below plan… manage depth of discharge" |
| 5b | Rule a dispositioned average-to-peak generation derate below 57.7% | Changes a modeled quantity and needs a record note; also makes nominal margins thinner everywhere |
| 5c | Log an FMEA erratum for a later gate | The divergence stays open into HUG-G002 |

**Recommendation: 5a.** It requires changing nothing that was ratified, it matches
CONOPS §4.3's own wording for P3, and the model already reproduces every
operationally meaningful part: SoC diverges below plan, depth of discharge worsens
measurably against the same pass without the fault, and load current crosses yellow
before red. The FMEA row's "SoC declines toward SAFE" is the only phrase that
overstates it.

---

## Sources consulted

- [CelesTrak: Historical NORAD Two-Line Element Sets](http://celestrak.org/NORAD/archives/)
- [CelesTrak: A New Way to Obtain GP Data](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [What Is a Sun-Synchronous Orbit (SSO)? — KeepTrack](https://keeptrack.space/space-terms/sun-synchronous-orbit)
- [CUSP: a two-CubeSat constellation — SSO 500–600 km, LTAN 9:30–12:00](https://arxiv.org/pdf/2208.06211)
- [3UCubed: CubeSat rideshare SSO deployment](https://arxiv.org/pdf/2211.15781)
