# dev.22 — host mod preparation before joining

Automatic host selection previously marked downloads ready immediately after
selecting mods. Manual activation additionally queued the loader, so the two
paths prepared assets at different points in the join sequence.

- Queue the existing mod Apply path while the client waits in the lobby.
- Release the launch hold only after the exact host-ordered stack and its
  core/current-mode zones are ready.
- Refresh discovery once per installation; bound activation retries and retain
  the hold on incomplete installation or activation timeout, with cancellation.
- Prevent the frontend's KillServer refresh while joined to a host.
- Refresh published Lua data on session changes and supply a matching Mods UI
  source file under `Lua/ui_scripts/mods.lua`.

Host fixtures cover pending/complete zones, wrong mode/order, incomplete stack,
retry/timeout, cancellation, personal selection retention and frontend reload
guarding. Existing stack/routing regressions pass. This is a console validation
candidate for the reported Client/Server Index Mismatch. No consistency check
is bypassed, and hardware behavior is not yet confirmed.

The8-player mod is maintained separately. This revision does not increase the
native script-variable pool or claim to fix the Complex18-player freeze.

Build validation: all14 PS4 translation units compiled with the existing pinned
OpenOrbis cache, the target artifact verifier passed, and all six malformed
container controls were rejected. The existing host regression suite plus the
new activation/session fixtures and Lua UI mock test passed. The image-surface
fixture exercised its generated cases; no local PNG sample set was supplied.

Artifact: `BO3-Customs-v4.00.1-dev.22-DEBUG.sprx`,453392bytes.
SHA-256: `b2ea8f85757355615ffcbD2f17421e48ba6873417ac8c0d69b47ae2e510b9641`.
Console runtime validation remains pending.
