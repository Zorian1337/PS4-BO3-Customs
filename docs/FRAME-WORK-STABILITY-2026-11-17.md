# Frame-work stall hardening — 2026-11-17

## Source finding

The frame hook runs map maintenance, lobby sharing and builtins before the
original engine `Com_Frame`. Two concrete synchronous IO paths were confirmed:

- `T7Builtins_Tick()` calls `T7Config_Save()` after the 120-frame mod-variable
  save interval. That function reads the existing config, merges the section,
  writes a temporary file, calls `fsync`, closes it and renames it over the
  active config. A slow storage operation can therefore hold the game thread.
- After a shared download completes, `T7Share::Finish()` calls
  `T7Maps_Refresh()`. That function takes the catalog writer lock, scans the
  data root and every configured external drive, scans packages/mods/movies,
  rebuilds Lua catalog text, and then installs/retries hooks. This is a
  potentially large one-time frame operation.

Neither path is proven to be the exact cause of the historical October 15
20-second stall. The original log has no matching dev.60 binary/symbols, and
the new source changes have not been run on console.

## Implemented changes

### Mod-variable autosave no longer performs disk IO in the frame callback

- Added `T7Config_SaveAsync()`, which copies the section and complete text into
  an owned bounded snapshot. The caller's temporary buffer is never retained.
- A dedicated config worker performs the existing `T7Config_Save()` operation,
  preserving its merge, temp-file, fsync, close and atomic-rename behavior.
- The frame thread uses a try-lock to publish a snapshot. If the queue is busy
  or the worker cannot start, the call returns immediately and
  `g_varsDirty` is restored so the next 120-frame interval retries.
- The queue coalesces pending mod-variable snapshots: only the newest complete
  snapshot is needed for this one config section.
- A background write failure sets a failure flag; the next builtins tick marks
  variables dirty again so persistence is retried.
- The worker uses the static owned snapshot in place while holding its queue
  lock; it does not allocate a 32 KiB temporary on the worker stack.

Keyboard/mouse and graphics config saves retain their existing synchronous
entry points. They are user-triggered save paths, not the periodic per-frame
mod-variable autosave. They still share the config serialization lock, so a
user save overlapping the background save may wait for that write to finish.

### More precise stall attribution

Debug frame phases now distinguish:

- `share/Evaluate`
- `share/hosted snapshot`
- `share/Finish`
- `share/map catalog refresh`

The watchdog records the phase and elapsed time when it samples a stalled main
thread. Existing broad phases remain unchanged.

### Rawfile UI filename bounds

A second memory-safety issue was found in the asset-link path:
`NoteUiFile()` previously checked that the first four bytes of a game-owned
filename pointer were readable, then called unbounded `strlen()`. If a name
was unterminated or crossed an unreadable mapping, that scan could walk beyond
the filename buffer while the engine was linking assets.

The function now scans at most `sizeof(g_modUiFiles[0])` bytes (96 bytes),
checks each byte with `RangeReadable()`, requires a NUL terminator inside that
bound, and only then checks the `.lua` suffix or passes the name to ownership
helpers. Overlong or unreadable names are ignored rather than read past their
valid range. The existing `mod_lua_retention_checks.py` regression suite now
guards this ordering and rejects reintroduction of `strlen(name)`.

## Why the full catalog refresh was not moved to a worker yet

`T7Maps_Refresh()` holds the catalog writer state while `ScanAll()` mutates the
shared package/file/mod arrays. `ListReader` currently waits in a loop while a
writer is active. Simply running the scan on a background thread would still
make any engine/main-thread hook that needs a catalog read wait behind the
background scan. That would move the blocking point, not remove it, and could
make the same frame stall harder to diagnose.

The safe long-term solution is an immutable/double-buffered catalog: build a
complete replacement off-thread, then publish it in a short atomic swap while
readers continue using the previous catalog. That is a larger data-ownership
change and needs all catalog readers/writers audited before implementation.
Until then, the new phase 23 marker will tell us whether this operation is
actually implicated in a fresh stall.

## Verification status

- Source files and test additions were remotely re-fetched after each update.
- Added `SPRX/tests/config_async_checks.py` to guard snapshot ownership,
  non-blocking enqueue, failure retry and the absence of synchronous
  mod-variable persistence in `T7Builtins_Tick()`.
- Added `SPRX/tests/frame_work_timing_checks.py` to guard phase markers and
  phase-name reporting.
- Existing `SPRX/tests/config_io_bounds_checks.py` and
  `SPRX/tests/share_install_checks.py` remain relevant regression coverage.
- The existing storage fault-injection fixture was extended with host
  pthread shims so the production config worker can be compiled in isolation;
  its original config migration, short-write, fsync, close, rename and
  preservation checks remain enabled.
- The complete committed host regression suite passed on commit
  `7e241f8`: **38 regression programs, zero failures**. The isolated filename
  fixture also passed its unreadable-page-edge test.
- The SPRX diagnostics workflow passed on `7e241f8`.
- The automatic PS4 GoldHEN Debug build, native module/container validation
  and artifact upload all passed on `7e241f8`. This was the repository's
  push-triggered CI workflow; no separate manual build was requested.
- No PS4/PS5 console test has been performed. The old October log still cannot
  be symbolized against the dev.60 binary.

Do not call the historical stall or any crash resolved yet. The next safe
engineering task is the double-buffered catalog redesign; the new phase 23
marker will confirm whether that synchronous refresh is actually involved in
a reproduced stall. Keep engine-facing hook installation on the game thread.
