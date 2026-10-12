# `defs/orbit/` — the pinned surrogate reference element set

**Empty by design, pending the owner's ruling.**

The concept brief requires that HUGINN use a *surrogate reference orbit derived from a
public element set*, "recorded in the repository with its epoch and source, pinned
(never auto-updated), so every campaign result is reproducible". ASM-03 makes that pin
a campaign-wide constant: contact geometry must be stable across all four campaign
passes.

Choosing which element set to pin is the design authority's, and he asked for the
candidate options before the pin is made. Until he rules, this directory holds no
element set and `sim/orbit.py` raises rather than guessing — a placeholder that quietly
worked would make every campaign number computed from it look real.

Scenarios state their eclipse intervals explicitly until then
(`illumination.source: schedule`).

Terminology, binding everywhere: this is a **surrogate reference orbit derived from a
public element set**, never "a real TLE".
