# Demonstration evidence — B14-native-log-playback

Captured at execution time under owner ruling D-008: gate evidence is a
preserved artifact, not a retention window. Every file below was written
into this repository as the demonstration ran, and is digested so that what
the gate reads can be shown to be what the demonstration produced.

| Field | Value |
|---|---|
| Demonstration | `B14-native-log-playback` |
| Obligation | B14 |
| Requirement | HUG-SYS-006 |
| Started (UTC) | 2026-08-07T01:39:30Z |
| Finished (UTC) | 2026-08-07T01:40:37Z |
| Result | **PASS** |
| What it demonstrates | Telemetry recorded during a pass is recoverable from the ground system's native log after the simulator is stopped. |

**Outcome:** 760 packet(s) recovered from the ground system's own native log by its own reader, with the simulator stopped (port closed, interface ATTEMPTING)

## Artifacts

| File | Bytes | sha256 | Note |
|---|---|---|---|
| `artifacts/simulator-off.txt` | 101 | `b8a5be4f477f5a1f732532e677da90c54d845678ea7e1da8009656425cd1e506` | CONTROL: the source is gone by two independent observables — the port refuses connections and the ground system's own interface is no longer CONNECTED. A screenshot of a frozen display would show the same values whether or not anything was replayed. |
| `artifacts/log-objects.txt` | 1010 | `5836f6b2a9da8e3af01d7be80959779fca4bf87f87c4846bde458847dbf5171c` | the specific native log objects this playback reads, by absolute path and digest. TLM_LOG_CYCLE_TIME is 300 s so a real pass spans more than one object. |
| `artifacts/ground-native-telemetry.bin.gz` | 17005 | `ef4e5f545b66936c989610f932329d82d6edef06b1083a42154f88263963d5a1` | the ground system's own native raw telemetry log for the recorded pass, preserved at execution time (D-008) |
| `artifacts/decompression.txt` | 357 | `2b92813fa2b984fa845694b259dc8495596cc9cc9c6add3dad757737feb8e9d9` | THE CHAIN: sha256 of the archived .bin.gz and of the decompressed bytes actually read, plus the first 8 bytes showing the COSMOS5_ header the reader looks for. The digest of the .gz here must match ground-native-telemetry.bin.gz in this same directory. |
| `artifacts/playback.txt` | 137668 | `abb2fd67cb273017c6d9fdb3f418ba15d9a90060059fd7ba5484d398b8acde3a` | the log read back by the GROUND SYSTEM's own reader inside the operator container, with the simulator off |
| `artifacts/compressed-refused.txt` | 199 | `f803bb997b9da97df5426146f09bad50924f99267af736371f35267b1eecc09f` | CONTROL: PacketLogReader does not decompress. It refuses the .bin.gz with 'OpenC3 file header not found' — the gzip magic is not the COSMOS5_ header. This is why the playback reads the decompressed bytes, and it is the finding that unblocked B14. |
| `artifacts/of005-file-bound-control.txt` | 287 | `88fb3d64c49e0a50fae6dc03bd97a9f611ef63908200c1ef7d26add7aea1f1e7` | OF-005 CONTROL: a database-backed read would still return packets for a bad path. Returning none proves the playback above was bound to the named native log file. |

## Observations

- frames recorded live: 236; packets read back: 760
- simulator port closed: True; interface state: ATTEMPTING

## Provenance

These artifacts are committed to the repository. They do not depend on any
ground-system retention setting, on a Docker volume surviving, or on this
machine still existing. `LOG_RETAIN_TIME` in the plugin is a margin that
protects the window between a pass ending and its capture — it is not the
mechanism by which this evidence is preserved, and nothing here relies on
it.
