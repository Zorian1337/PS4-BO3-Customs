# Waffle Tower launch / DS4C frontend investigation

The dev.58 session requests `lobbyLaunchGame 1 zm_waffle_tower zclassic`.
Before that request, DS4C frontend-camera CSC raises undefined-to-string and
undefined-index errors at offsets 0x3413 and 0x322C. Those are separate mod
script errors; this loader patch does not fabricate script values or suppress
those exceptions.

After the launch request the session rejects actions_or.lua and
datasources_or.lua with **unreadable Lua chunk range**. The allocation log
shows a previous successful result (0), not a new failed allocation. Later
presence/soundset nil errors occur after foundational modules were rejected.
They must not be treated as independent missing-function fixes yet.

Source review found exact RangeReadable delegated to a scan helper limited to
eight virtual-memory regions. Valid large bytecode spanning more regions can
be rejected. The exact validator now walks contiguous readable regions to the
requested end, requires forward progress, and rejects overflow, holes and
unreadable mappings. The bounded string-scanning helper remains unchanged.
This corrects an evidenced source defect; the capture does not enumerate the
actual mappings, so a new console run is needed to confirm it explains this
particular buffer rejection.

Additional corrections: the rejection module no longer mislabels every
validation failure as out-of-memory; stale mapping success data is printed only
for an actual arena-allocation rejection. The generic bytecode retention budget
and fail-closed lifetime policy remain enforced.

Regression: production exact-range code tested across 24 adjacent mappings,
unaligned page boundaries, holes, protection changes, nonprogressing mappings,
invalid addresses, overflow and a missing tail. Existing arena retention tests
pass, including unmapping, alias/revision deduplication, concurrency and failed
allocation. Map files are present locally, but content completeness and console
gameplay are not established. No map-specific bypass is added.

## Review of the newly supplied `log.txt` and `log1.txt`

`log1.txt` is a dev.53 capture (10:37:35). It reports 127 custom maps while
`ext0` and `usb0` both have an accessible `BO3-Customs` directory. Reaper is
selected. The repeated `3778239045:252` nil-index errors and later nil-call
errors match the older frontend wrapper failure already investigated above.
The missing-only PC widget dependency fallbacks and constructor diagnostics are
present in the later source; this dev.53 capture predates them and is not a
regression report for current `main`.

`log.txt` is a dev.58 capture (11:29:59). At startup, none of the listed
external roots reports a `BO3-Customs` directory, and the scanner finds 15
custom maps. This differs from the earlier 127-map scan alongside the storage
availability change; the logs do not show a map-count cap or a failed map
preflight. The capture selects the patched DS4C mod, logs repeated errors in
its `ds4c_frontend_cam.csc` script (owner is untracked), and later requests
`zm_waffle_tower`. `EXE_SERVERKILLED` immediately follows the explicit map
launch request and is the recorded level-transition path, not evidence by
itself of a native crash. The session ends before confirming the map's stable
in-game state.

During frontend loading, dev.58 rejects `actions_or.lua` and
`datasources_or.lua` because their borrowed bytecode ranges are unreadable.
The subsequent `presence.lua` and `soundsets.lua` nil-index failures happen
after those foundational module rejections, so the available evidence does not
justify treating them as independent nil-guard defects. The CSC errors belong
to compiled mod content and its source is not available here; adding invented
values or suppressing those exceptions would change third-party behavior.

The relevant source correction is already in current `main`: PR #25 replaced
the fixed-eight-region range scan with a full contiguous readable-range walk,
and corrected the failure diagnostic so an unreadable source range is not
reported as allocation exhaustion. The allocation log in dev.58 shows a
successful mapping result (`0`); it does not support an out-of-memory diagnosis.
This source fix addresses the proven range-validator limitation, but the log
does not include the raw pointer, byte length, or virtual-region map needed to
prove that limitation caused these exact rejections. The newer source also
fails closed rather than returning a potentially dangling bytecode pointer.

Validation on current source: `readable_range_checks.py`,
`mod_lua_retention_checks.py`, and `ui_startup_unload_checks.py` all pass under
WSL. These host checks validate bounds, lifetime, failure handling, and menu
recovery; they cannot establish PS4 behavior for this dev.58 run. No further
runtime or Lua change is justified by these older captures, and no build was
made for this review.
