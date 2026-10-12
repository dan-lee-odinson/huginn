"""VÉ — the display-only mission viewer and its recorder (Phase 4).

VÉ renders recorded replay packages and nothing else. It is a VIEWER, never a control
console: it has no command path, no live-data path, and no connection to the simulator or
the ground system (HUG-UI-002, replay_schema excluded_content).

The recorder writes packages; conformance decides whether what was written is one; render
and interpolate are the viewer-side halves of two rules no package can carry.
"""
