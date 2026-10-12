## PROC-001 pre-pass — configuration verification (HUG-GND-006)

| Field | Value |
|---|---|
| Pass | `DEMO-B10-NOGO` |
| Executed | 2026-08-05T03:06:25+00:00 |
| Step | PROC-001 pre-pass, AOS − 5 min (CONOPS §5) |
| Tool | `tools/pass_setup.py` |

### Loaded configuration, as displayed by the ground system

```
DICTIONARY_VERSION 0.5   SOURCE_SHA256 5e1c2750ef9e0d5463f8b2fcb27abeb1dbde63c1b749717ed170cc2bacd60679
```

- **PASS** — identity vs dictionary of record: loaded identity matches the dictionary of record (v0.5, 5e1c2750ef9e0d54…)
- **FAIL** — loaded vs repository (D-010): differ between the instance and this repository: ['targets/HUGINN/cmd_tlm/tlm.txt'] — the loaded ground configuration is not the one this repository generates, and the source digest cannot see it (D-010)
- **PASS** — target inventory (D-009): 2 target(s) loaded, exactly the permitted set ['HUGINN', 'UNKNOWN']

### Verdict: **NO-GO** for commanding

**A mismatch is a no-go for commanding until resolved (HUG-GND-006).** The response is FM-GND-04 note (e): reload the generated configuration and re-run this step. 

This verdict is **procedural** (D-010). No technical command inhibit is armed by this tool — the no-go is a condition on the Flight Director's go/no-go at AOS − 5 min. Commanding against a NO-GO is a procedure violation to be dispositioned as an anomaly in the pass report, not something this tool prevents.

