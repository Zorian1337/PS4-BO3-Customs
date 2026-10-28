# t162 / dev.23 automatic activation failure

## Captured evidence — 2026-10-28

Host log SHA256: `BD1FB31E690599CC07B9CCC614BFC592CB611403FF2DE0BCD278D51C9DDDEC74`.
Tester log SHA256: `40D21469D3DE6574F9856C2F15225B33EB7AF1BBC62D9BB8A1DC33E35103B452`.
Both identify dev.23. Host selected ZM Bots first and t162 second.

Tester downloaded all four absent t162 files (145408 bytes) at 01:02.014–01:02.590,
then discovered the mod, selected the host stack, loaded it with a fresh
zm_common transaction and waited for zone completion. Readiness was released at
01:24.902; EXE_ERR_BG_CACHE followed at 02:00.379 with zero script errors. Thus
file transfer, discovery and ordered-zone loading occurred; they were insufficient
to produce the engine state of manual activation. Do not call this a demonstrated
missing-file transfer or clientfield-schema failure.

The host first selected mods before entering the lobby; its manual path restarted
the frontend at 00:53.391. The automatic client's corresponding restart was
suppressed at 01:24.890 to preserve its connection. A full common reload did not
eliminate the cache-index failure. A later retry reused already-loaded zones.
The user confirms manual enabling permits joining and spawning without spectator
lock. The host readiness trace retains the missing second human at 5050/10050 ms,
then reports two humans playing/spawned at 15050 ms. Preserve t162's spawn fix.

## Investigation plan and release gates

1. Locate the native BG cache failure check and initialization/reset boundaries
   using the existing PS4 1.33 image. Identify the actual mismatching index/table
   before adding a native reset or bypass. Never disable index validation.
2. Compare the manual frontend transition with session activation, especially
   Lua/native precache initialization and retained common/menu state. Do not
   assume a zone-loaded flag proves those state machines completed.
3. Consider a controlled preparation/rejoin transaction if the native frontend
   restart is required. It must retain the exact host identity/ordered selection,
   finish downloading first, prevent a half-prepared launch, reconnect through
   the existing native lobby API and restore personal selection on leave. Do
   not simply remove the connected-session KillServer guard.
4. Distinguish stale same-name local mod content from timing: the current
   manifest skips installed folders and does not authenticate all host file
   hashes. The t162 transfer size matches the built package, but the two bot
   folders have not been proved byte-identical. Record this as an independent
   uncertainty rather than inventing a content mismatch.
5. Add production-function regression coverage for the chosen transition and
   retain the successful manual path. Keep gameplay changes out of Customs.

No new build is approved by this report. No new package, upload or upstream PR.
Console validation remains necessary before claiming automatic activation fixed.

## Native check identified; read-only diagnostic source added

Existing cached PS4 1.33 executable image SHA256
`62c62d57b34060d41ab702a2747bb20d8c04a0f9573ae1e42f6e075a6cc417ba`
contains the BG-cache error reference at RVA7C93E9. The preceding native check
at7C928E compares two32-bit values stored at1F276E0/1F276E4 and suppresses the
error for a zero received value. Config-string processing at549C39 handles
index0xCA9, reads the previous cached value at1F276DC, parses the received word,
and, when different, calls53ABE0 to hash native cache entries before recording
the received/computed pair. These are cached-image offsets, not live addresses
without adding the validated game base.

Added signature-checked, readable-range-checked snapshots of these three words
to existing transition diagnostics and the exact EXE_ERR_BG_CACHE error path.
No native writes, reset, forced checksum equality, new hooks, asset queries,
frontend restarts or gameplay edits. This provides the missing distinction
between unloaded files and an actual native index-table hash disagreement.
The code is diagnostic; it does not itself fix automatic activation. Required
next evidence: host/client snapshots across the failed automatic and successful
manual paths, plus proof of the safe stock pre-join/rejoin contract before any
connected frontend restart is implemented.

Production-function host tests pass for signature mismatch, unreadable memory,
equal/unequal checksums, null context, zero-base startup, unchanged native bytes
and normal error forwarding. Existing transition and script-import lifetime
fixtures also pass. No new target SPRX has been compiled or uploaded. The online
stock PS4 `lua/Lobby/lobby.lua` reference exposes `LobbyVM.JoinSystemlink` and
`Lobby.Process.JoinSystemlink(controller, lobbyMainMode, lobbyNetworkMode,
hostXuid, hostInfo)`; translating that to a safe native UI/VM reconnect path
remains unimplemented. No reference files have been downloaded to disk.
