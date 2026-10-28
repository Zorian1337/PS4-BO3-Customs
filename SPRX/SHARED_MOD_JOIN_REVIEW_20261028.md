# Shared mod join review — 2026-10-28

## Latest: dev.22 follow-up, source only

**Delivery update:** the user subsequently approved both builds. This candidate
was built as dev.23 Debug and uploaded; see `CHANGELOG-dev.23.md` for validation,
original hash and transformed FTP readback details. Runtime remains unverified.

New capture `sprx22-doesntletplayerjoiniftheydonthavethemod_iftheydomodmakes them spectate.txt`, SHA256 `2A0BDF20891E533F9E61CA698CC6BAEC02B6AC17CED9592E2E2468A49CA02378`, supersedes the earlier readiness hypothesis as a sufficient fix. At 01:08.579–01:08.601, both host mods append after zm_common is loaded; 01:11.165 declares readiness. The client then fails with EXE_ERR_BG_CACHE at 02:11.012 and zero script errors. At 03:32.270 the manual-activation retry again has zero files to fetch, reaches map loading and repeatedly reports the local player not in gameplay. This client-side capture cannot explain the host's spawn rejection. It also cannot demonstrate a download failure: both mod folders were already discovered.

Changed `ApplyModsNow` only for a host-owned stack that differs from the loaded stack. It now uses the preexisting whole-mode-common free/load transaction, allowing AddModZones to plan the ordered stack together with common loading instead of appending it afterward. Existing loaded matching stacks still return without reload; personal activation, zone-loading/in-level/common-on-top guards and exact readiness checks remain. No KillServer, protocol change, save write, cache-check bypass or 8-player-specific behavior was added.

`session_common_activation_checks.py` executes the actual production function with ASan/UBSan for a fresh stack, wrong order, matching stack, empty host, pending zones, wrong memory-pool position, in-level protection, missing common and personal activation. Existing readiness/install/publication/transaction/frontend fixtures also pass; diff check is clean. Both CI host-check lists include the fixture. These tests establish routing and guards, not native cache-index correctness. The changed common load is a console validation candidate, not a proven fix for EXE_ERR_BG_CACHE.

No SPRX package, upload, commit or push made in this follow-up. Explicit build permission is still required. Validate automatic activation with two real clients before introducing bots. Verify exact host/client file hashes/order: installed names alone are insufficient. A fresh-download case remains untested. Keep the 8-player mod's human readiness work in its own project.

Base: fork main `34ab597658e18edb181439d9dbcc01fedbdab1e2` (dev.21 stabilization).
Local source was clean before a fast-forward from origin/main. No SPRX build,
console upload, commit, or remote write was performed for this review.

## Evidence from the supplied captures

`t161-mp-disconnectonjoin.txt` is a Zombies Space Tower join capture despite its
filename. It demonstrates download, discovery, session selection and zone loading:

- 09:23.254: host advertises two mods, with four missing files totaling 145152 bytes.
- 09:23.273–09:23.730: localized/core/ZM mod files download successfully.
- 09:23.840: discovery finds `zm8p_ps4_t161`.
- 09:23.863: host's two mods replace the client's one personally ticked mod.
- 10:52.236: `EXE_ERR_BG_CACHE`, with zero script errors in the level.
- 10:53.909–10:53.951: transition snapshot confirms selected=2, loaded=2,
  core-mod=1, zm-mod=1, with `zombiebots` then `zm8p_ps4_t161` in BOTH lists.
- 11:39.515: second attempt needs zero files. Subsequent gameplay logs include
  the t161 dynamic scoreboard with 18 players and 12 visible rows.

The exact localization of `EXE_ERR_BG_CACHE` was established in the mod journal:
**Client/Server Index Mismatch**. It is distinct from `EXE_CLIENT_FIELD_MISMATCH`.
The captured failure is therefore not proof of missing activation or a mismatch
in clientfield registrations. The two other supplied log.txt files instead
capture separate map stalls, already covered by dev.21's stability tracker:
`log (1).txt` opens external `zm_ds_facility_zw` with a full1536-entry registry,
then stops progressing for20/40/60seconds. `log.txt` opens internal
`zm_radiant_hallway`, emits craftables/BGB undefined-object errors, and later
samples Main at `BADF5A`. Neither establishes an additional failed mod download.
All three report `Debug build of Oct 28 2026 07:56:54` and PS4. The printed
stamp does not itself provide the source SHA; the enclosing directory names
the dc326f stabilization artifact. Keep that distinction in future comparisons.

## Demonstrated source defects corrected locally

1. `Finish()` previously published readiness without checking that every host
   mod survived the post-download discovery scan. `ChosenForLoad()` can skip a
   missing mod. Validate the entire list first so a partial stack is rejected,
   and log every installed, selected session mod in host order. This does not
   claim that asset linking has finished.
2. `T7Maps_SetSessionMods()` changed the effective list without dirtying the Lua
   publication. Joining/leaving now invalidates that publication.
3. The Mods UI used only the client's personal choice for checkmarks/status.
   Publish a separate `BO3CustomsSessionMods` value: ordered table for a host
   session, including an empty table for a host without mods, and nil outside
   the session. The Lua UI reads that list and explicitly distinguishes selected
   versus loaded mods. Its Choose/Toggle actions leave personal choices alone
   while a host owns the session. Leaving restores the personal list naturally.

No forced frontend reload, KillServer, schema bypass, cache bypass, or gameplay
patch was introduced. These fixes do not resolve the observed cache mismatch.

## Lua bundle

Input SHA-256:
`20471e4ab337807d3272ca7fc02a7141349bbfc0796fd0d757a9af6d6a84b7fe`.

Extracted editable working copy:
`F:/tools/sprx/dev12-work/lua-base-review/BO3-Customs-lua-base`.

The archive has 46 files, 594354 uncompressed bytes: 39 compiled LuaQ files
under `lui`, and seven editable Lua scripts under `ui_scripts`. Only
`ui_scripts/mods.lua` was edited. The 39 compiled chunks and six other scripts
remain unchanged. This working copy is not deployed. The new UI remains usable
with older SPRX builds because an absent session global falls back to the
existing personal-choice behavior. No 8-player feature was put in this bundle.

## Validation performed

- `share_install_checks.py`: executes production Finish with incomplete stack,
  existing complete stack, pending refresh, absent map, empty host and fetched
  files; ASan/UBSan passed.
- `session_mod_publish_checks.py`: executes production session setter; join,
  leave and empty host invalidate Lua data and preserve order; sanitizers passed.
- `session_mod_ui_checks.py`: parses full modified Lua and executes its actual
  selection/status/action functions in Lua 5.1 with UI mocks. Host loading,
  loaded status, empty host, leave and personal-choice retention pass.
- Existing mod-stack transaction, frontend-reload and map-routing host tests pass.
- 8-player source/capacity checks pass. Its gameplay/source remains unchanged.

These tests exercise source boundaries; no native SPRX target link or console
test occurred. Run the UI test with the working mods.lua path and the existing
`F:/tools/bo3/BO3-18-Player-Zombies-master/tools/lua_runtime/lua-linux` in WSL.

## Remaining investigation, in priority order

1. Obtain the paired host and client logs from one failed lobby start, followed
   by the successful in-progress join with unchanged map/mod files. Compare
   ordered cache construction and actual loaded-zone readiness at launch.
2. Compare exact map/mod file hashes on both consoles, especially ZM Bots and
   Space Tower. Current Exchange skips an already-installed mod by folder name;
   it does not prove its bytes match the host. The zero-file second attempt
   proves presence, not content identity. A negotiated content manifest would
   address this; avoid forcing silent overwrites or changing the protocol
   without backward-compatible tests.
3. Resolve the actual native cache failure site before changing mod precache or
   rebuilding asset indexes. Late joining succeeding suggests initialization
   order/readiness is a candidate, but does not prove which owner is wrong.
4. Keep t161's fixed schema, dynamic scoreboard, selector, revive and spawn
   workers unchanged until the failed native cache entry is identified. The
   PS4 builder deliberately retains native paired BGB scripts; do not re-add
   the excluded custom manager/helper merely because root source contains it.
5. Track MP mode-transition stability and Complex's child-server-variable pool
   exhaustion independently from this cache-index disconnect.

## Binary analysis limitation

REA opened the supplied eboot as ELF x86-64 with SHA-256
`e45285380245f1566c2e4dec17912dac95c3bc4ef6ecac6a700b3b901d6926a4`.
A targeted dossier request for the recorded caller address `0xef2da4` still
requires complete Ghidra auto-analysis; it did not return within this review's
bounded window and was cancelled. No native function identity/ABI, hook target,
or cache-rebuild fix is claimed from that attempt. The prior DayBreak dossier
remains historical reference only; it provides no proof for the join failure.

## Next delivery gate

Explicit user permission is required before another SPRX build. Preserve the
original Lua ZIP and use the reviewed working copy for any later approved Lua
deployment. Runtime validation must precede a claim that the join is fixed.

## Follow-up: manual activation succeeds (2026-10-28)

User confirms clients can join directly after manually enabling the mods. This
adds a controlled distinction to the investigation. Source comparison confirms
manual choice queues Prefetch/Apply, whereas automatic Finish previously only
changed the session list and immediately released the launch hold. Mods then
loaded at the later level-zone hook. A loaded-list snapshot after failure does
not establish that those assets were ready before cache initialization.

Implementation plan: prepare the host-selected stack through the existing
main-frame ApplyModsNow path, keep the launch hold until the exact ordered
stack and its required core/mode zones report ready, and suppress the native
KillServer menu refresh while connected to a host. Discovery must run once per
installation, not every waiting frame. A bounded activation timeout must report
failure and retain the hold rather than continuing with an unready stack.
Keep native cache validation, protocol, personal selections and all 8-player
gameplay features unchanged. Test both already-enabled and newly downloaded
stacks, ordering mismatch, asynchronous zone completion, timeout, cancel and
leave behavior before considering any approved target build.

### Implemented source candidate

- Finish performs discovery/list installation once and then stays in
  `kInstalling` while the main-frame loader applies the session stack. The
  normal Apply request is retried at most once per second for at most90seconds.
- `T7Maps_SessionModsReady()` requires the exact loaded AND redirect-stack
  count/order, the current native session mode, no zones still loading, and
  loaded core/current-mode zones for every selected mod. Merely publishing
  `g_loadedCount` no longer releases this launch hold.
- Already-enabled stacks proceed immediately when that readiness query passes.
  Empty host stacks wait until previously loaded local mods are removed.
- An incomplete discovered list or activation timeout retains the launch hold.
  The status explains the failure; explicit cancellation releases it. A fresh
  session starts with reset installation state. Existing lobby keepalive runs
  while waiting, so waiting does not intentionally disconnect the client.
- `ReloadFrontend()` refuses its KillServer path while a host session owns the
  mod selection. Personal menu activation outside that session retains its
  existing behavior. Other native shutdown paths are untouched.
- The status now shows `ENABLING HOST MODS`, including when no download was
  necessary. Download progress alone is no longer presented as activation.

Production-function host fixtures pass for pending zones, each core/mode zone,
wrong order, wrong mode, partial/foreign redirect stack, missing host mod,
already-enabled stack, empty host, refresh-once behavior, retry interval,
timeout retaining hold, explicit cancellation, and inactive-session cancel.
Existing frontend reload (including the new host-connection guard), transaction,
map routing, Lua UI and publication fixtures pass. `git diff --check` passes.

This corrects a demonstrated ordering/readiness omission. It remains a console
validation candidate for EXE_ERR_BG_CACHE, not a confirmed cure. In addition to
joining, validate pause, dynamic scoreboard and revive behavior on the joining
client, since its preexisting Lua module cache can differ from a manually
reloaded frontend. No generic forced Lua reload was added without that evidence.

No SPRX/mod build, upload, commit, remote issue or PR was created. The8-player
runtime source and its feature schema remain unchanged; the shared activation
fix is generic BO3-Customs code.
