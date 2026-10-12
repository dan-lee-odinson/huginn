# Demonstration evidence — B11-replay-package-and-viewer

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B11-replay-package-and-viewer` |
| Attempt | `attempt-001` |
| Obligation | B11 |
| Requirement | HUG-UI-002/003/004/005/007 |
| Started (UTC) | 2026-08-08T14:33:09Z |
| Finished (UTC) | 2026-08-08T14:33:19Z |
| Result | **PASS** |
| What it demonstrates | A pass recorded while the ground segment is live exports a replay package conforming to every rule of the interface definition, the display-only viewer renders it, and a perturbed copy is refused by name with no page written. |

**Outcome:** a pass recorded while the ground segment was live exported a package conforming to all 32 rules; the viewer page was built from it; a perturbed copy was refused by name and no page was written for it

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/pass-setup.md` | 988 | `1a0ab28527d5da52810d2f1984d70e8a7f1b6c542b37ae828cd9b32d1d5c0703` | PRECONDITION: the ground segment is the configuration of record at the moment of recording (D-010, HUG-GND-006). |
| `artifacts/live-stack.txt` | 63 | `3a47517eee1870d016533caaf56d5b50dcb08fdfe6ba7aa66f9fc6e4967b9ce3` | the ground segment was live and receiving telemetry while this pass was recorded |
| `artifacts/replay/b11-demo-001.json` | 284659 | `84eb716c7c68df9c66cf83ca797649558f07ef948491d7f7bfeb4db6b0cdd820` | the exported replay package, as written |
| `artifacts/conformance-verdict.txt` | 882 | `ba0de9e5f0b559a8b890e7bd06cd602c4569a3b1416524106ff4273c73d61f3f` | the verdict and the FULL rule accounting: every declared rule and the site that implements it. A rule reading NOWHERE would be one nobody enforces. |
| `artifacts/viewer/b11-demo-001.html` | 438652 | `ed8c4038e7cc6c77ca14e677b49ee46534b1acd1006a7b319f1d4640941fb1a8` | the viewer page built from that package: one self-contained file, no backend, no network (HUG-UI-006) |
| `artifacts/digest-chain.txt` | 960 | `c5091949f9223951d129d73b2d27cc92ebeb8125a3adc0e774c6d91790f0f13f` | THE CHAIN. Binds package, verdict and page to one another by digest. |
| `artifacts/replay/b11-demo-001-perturbed.json` | 284644 | `a5335f5fac39f277d4e8c634d05ba3609e747411eccc3a6a787ebf10bd212655` | RED: the same package with two values moved outside their dictionary domains |
| `artifacts/red-refusal.txt` | 729 | `2b11f099383d507fcdd5fe1b63a84de942432a156ae0b102f0c9dbab515ff737` | RED: the refusal, naming each rule and quoting its own statement (RS-7-20). A refusal saying only 'invalid package' would tell an operator nothing to act on. |
| `artifacts/red-viewer-refusal.txt` | 785 | `cf64879d54a336b9b1311eeeafcaf72d781e63c6df1f7f1606c23f920d488108` | RED: the viewer declined to render the perturbed package (RS-2-04). |
| `artifacts/red-no-page.txt` | 62 | `df798178c4a73f583a134be584449b5489b5dd8dd31436a0de8bf8ff3288b4c6` | RED: a page written and then abandoned would be a page an operator could open, which is exactly the best-effort rendering RS-2-04 forbids. |
| `artifacts/malicious-markup.txt` | 3313 | `d5c8c9d3dc3299ac4ba58db0dd5a9ef8c017dfa6fb4648793457d8dd6aacdbcc` | HUG-UI-007: the malicious-markup suite, EXECUTED as part of this evidence run rather than cited from another one. |

## Observations

- conformance: CONFORMS over 32 declared rules
- accounting: 29 in check + 3 at viewer, 0 in both, 0 in neither
- verdict computed from artifacts/digest-chain.txt, conformance-verdict.txt, red-refusal.txt and malicious-markup.txt; the live stack paced this run and decided none of it

## Provenance

These artifacts are committed to the repository. They do not depend on any
ground-system retention setting, on a Docker volume surviving, or on this
machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that
protects the window between a pass ending and its capture — it is not the
mechanism by which this evidence is preserved, and nothing here relies on
it.
