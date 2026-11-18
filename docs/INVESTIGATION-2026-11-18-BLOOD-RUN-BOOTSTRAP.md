# Blood Run usermap bootstrap regression

Issue: [#31 — Blood Run mod script failures, frozen controls and missing UI](https://github.com/Zorian1337/PS4-BO3-Customs/issues/31)

## Confirmed failure and scope

The dev.67 capture recorded a modded frontend Lua error because the game called
Mods_IsUsingUsermap while that global was absent. The current public source
contains a compatibility bootstrap in SPRX/t7_lua.cpp. It installs the
fallback only when the global is absent and derives the answer from
Engine.GetCurrentMap(), treating core_frontend and failed probes as not being
a usermap. A separate LuaUtils parity shim follows the same absent-only rule.

This correction addresses the observed missing-global compatibility failure.
It does not repair the repeated invalid-value errors in
scripts/blood_run_menu.gsc, the untracked usermap GSC offsets, server shutdown,
or the later frozen-controls/pause report.

## Implementation in this PR

- Added SPRX/tests/blood_run_bootstrap_checks.py. It extracts and executes the
  actual production Lua bootstrap rather than reimplementing its logic.
- Registered the new check in .github/scripts/run_host_checks.py so the
  inventory guard requires it to run on every PR.
- The fixture verifies a real map returns true and the map name, core_frontend
  returns false, absent map data returns false, a throwing native map probe
  fails closed, a pre-existing provider is preserved, and selecting a mod in
  the frontend does not misclassify the frontend as a usermap.

## Remaining blockers

The matching Blood Run GSC source or trustworthy source lines for the logged
offsets are still unavailable in the public repository. Compiled FF/XPAK
packages do not provide enough information to safely rewrite those call
sites. Do not add guessed entity/array guards, suppress the menu, or change
pause behavior without the matching script source and a fresh reproduction.

The next console comparison remains a clean BO3 process with the mod selected
before the first map load, followed by a capture containing the first GSC
errors, server transition, frozen-controls state, and an actual pause
open/close attempt.

## Validation boundary

This PR adds a host regression for the compatibility fallback. It is not a
native SPRX build, does not validate the third-party GSC bytecode, and does
not establish console stability or fix the gameplay stall.
