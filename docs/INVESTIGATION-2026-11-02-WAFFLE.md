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
