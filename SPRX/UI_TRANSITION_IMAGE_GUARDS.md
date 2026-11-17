# UI transition and custom-image callback guards

## Queued zone transitions

The UI busy predicate now includes the plugin's queued mod-zone wait state
(g_reloadCheck and the pending wait-zone count), not just native loading slots
and frontend handoff flags. This closes the interval where a mod-zone request
has been queued but the engine has not yet published its loading state.

Tick-driven Lua work rechecks the predicate after acquiring the nonblocking UI
lock. If a transition began between the frame-entry check and lock acquisition,
the lock is released and the tick exits without mutating the UI. Transition
snapshots use the same post-lock check.

## Custom image lifetime

A cached custom-image address is now treated as a known custom pointer even if
its native image slot has since been retired or reused. At delayed SetImage
assignment, the code revalidates the slot's in-use state and name. Retired
custom images are replaced with a nonblocking native $white lookup when the
element handle is still valid. Invalid/stale element generations are dropped
without writing or forwarding the stale custom pointer. Stock images retain
the original native passthrough path.

These are source-level guards for the reported rapid main-menu X/back case and
adjacent delayed image callback hazard. They do not prove the separate
multi-mod Database-thread crash is fixed. Native build and console reproduction
remain required.
