# 2026-11-17 frame-stall investigation

## Finding from the supplied console log

The attached log was produced by a Debug build dated 2026-10-15 20:48:57. At
approximately 00:53.517 it reports that the game made no frame or asset-linking
progress for 20 seconds. The sampled main-thread chain contains several SPRX
return addresses:

`sprx+1FD4 sprx+1A6BC sprx+1B3E9 859BD0 sprx+153FE`

This establishes that the main thread was executing inside plugin code when
sampled. It does **not** identify the exact function or prove that the stall
caused a fatal crash. The matching October binary/symbols are not available to
map those offsets to source.

The log contains no explicit crash, SIGSEGV, SIGABRT or fatal-error record.
Later, at 02:16.586, it queues
`lobbyLaunchGame 1 zm_waw_spongebob_vinnyz500 zclassic`; at 02:18.788 the
server reports `EXE_SERVERKILLED` with zero script runtime errors, unloads
the previous zone, and proceeds to load the requested map. This sequence is
consistent with normal server teardown during a map launch, not proof of a
crash.

The missing frontend xanim records say the game used its default assets. The
pool snapshot shows xmodel 8637/10240, material 17689/19712, image 37386/45979,
and localize 21515/23552. `snddriverglobals 1 of 1 - FULL` is a singleton pool,
not evidence of ordinary pool exhaustion. None of these observations alone
identifies the cause of the no-progress interval.

## Source changes made

The source changes are deliberately diagnostic/hardening work, not a claimed
fix for an unproven crash cause.

- `SPRX/main.cpp`: check initialization-thread creation and join results.
  A create failure no longer joins an invalid handle. If BO3 is not detected
  before the existing probe timeout, the startup latch is released so a later
  loader callback can retry. If join fails, the latch remains set because the
  worker's state is unknown and retrying could duplicate partial initialization.
- `SPRX/main.cpp` and `SPRX/headers.hpp`: Debug builds track which part of the
  frame hook is currently executing: map work, sharing, builtins/config save,
  original engine `Com_Frame`, or Lua tick.
- `SPRX/t7_maps.cpp`: when the watchdog samples a stalled main thread, it now
  reports the active frame-hook phase and how long that phase has been active.
  This makes the next capture useful even if the matching old binary is absent.
- `SPRX/t7_maps.cpp`: the stall watchdog and log-mirror workers now have
  separate thread handles and are detached independently. Creation and detach
  outcomes are logged separately instead of overwriting one handle and
  reporting a combined state.

The existing frame order is preserved. In particular, map work, sharing and
builtins remain before the original engine frame, and Lua remains after it.
Moving engine-facing work to another thread without identifying its thread
affinity and ownership would introduce a new stability risk.

## Why this is not yet a crash fix

The frame phase marker will tell us whether a future stall occurs in map
maintenance, lobby sharing, config persistence, the engine frame, or Lua work.
If it identifies sharing or config persistence, the next step is to move only
the measured filesystem/network portion to a bounded worker/queue while keeping
engine state reads and mutations on their required thread. If it identifies
map work, inspect the specific pending zone/mod transaction before changing
its scheduling. If it identifies the engine frame, the SPRX stack and engine
return addresses need matching symbols or a fresh stack capture.

The current log predates dev.60 and cannot validate these source changes.
GitHub Actions on commit `7e241f8` passed all 38 host regression programs,
the dedicated SPRX diagnostics workflow, and the automatic pinned OpenOrbis
Debug PS4 cross-build plus target artifact validation. No PS4/PS5 console test
has been performed. Do not call the historical stall or a crash resolved
until the relevant scenario has been reproduced and retested on hardware.
