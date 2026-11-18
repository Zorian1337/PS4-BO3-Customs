# Current development status

Updated 2026-11-17. The dated investigation sections below retain their chronology; for active branch and candidate status, see [RESUME.md](../RESUME.md) and the [PS4 stability roadmap](PS4-STABILITY-ROADMAP-2026-11-17.md).


## Current PR review update (2026-11-17)

The repository now has five open PRs (#37–#41). PRs #37 and #38 are standalone predecessors to combined PR #39 and must not be merged independently. PR #39's six workflows and 46-program host inventory pass, but source review found a delayed custom-image callback can escape tracking after its `Picture` record is cleared/reused; a review comment is recorded, and the PR must remain draft until retired-address tracking and a post-reuse regression are added. PR #40's checked arithmetic tests pass, but the signed-32 index assumption remains unverified against the public `uint32_t` chain consumer; it is not a runtime allocator fix. PR #41's focused Lua fallback regression passes; Blood Run GSC/gameplay/pause failures remain open.

No native SPRX build, upload, release, or console test was performed. See [RESUME.md](../RESUME.md) and the [stability roadmap](PS4-STABILITY-ROADMAP-2026-11-17.md) for exact branch heads, checks, review blockers and next steps.

## DS4C UI failure and recovery (dev.60 candidate)

The console's latest attached session is dev.58, with `^6ds4c` selected. It
reports a stripped Lua nil-index in `DS4C_ProgressionStore.lua`, followed by
`main` and `Lobby` missing-menu errors. The current dev.59 console binary was
uploaded after that session. A local copy of the mod fastfile contains the
named Lua rawfile, but the payload is protected and does not match the standard
Havok chunk format expected by the current parser. The failing nil operand
cannot be identified from the supplied evidence. No native crash or map-load
failure is present in this session.

Review found that the UI-error latch was cleared on a new frontend generation,
but not if BO3 successfully rebuilt the `main` menu in the same Lua state. The
dev.60 source candidate now treats a successful native `main` registration as
a recovery signal, clears UI-state caches, and schedules the existing
injection path. Other menu registrations do not clear the latch. A focused
ASan/UBSan host test passes for both the recovery and non-main cases. This does
not repair the original DS4C nil access; runtime verification must establish
whether the mod's menu graph can rebuild successfully.

## Localized UI error capture (2026-11-02)

The tester reports that with Reaper Collection loaded, `ERRUR IU 25848`
appears when opening weapon customization, GobbleGums, or Reaper's menu, and
also in the regular player menu. These are reproduction points, not a trace
identifying the failing callback. The attached Oct. 15 startup text available
to this review ends during `core_frontend` loading and does not include the
reported code or its stack.

Source review found the host diagnostic reader recognized English
`UI Error <number>` and `LobbyVM Error <number>` forms only. It now also
classifies case-insensitive `ERRUR IU <number>` lines as `ui-error`, retaining
the original trigger and surrounding context. A regression covers code 25848
and stack retention. All 9 console diagnostic reader tests passed locally,
including the new regression.

This is a logging improvement only. The current native source already pauses
BO3-Customs compatibility injection after a modded frontend UI error until the
next frontend generation, while retaining selected mod zones. That containment
does not repair a Reaper callback and does not establish that the loader caused
the error. No native SPRX behavior changed, and no SPRX build or console
validation was performed. The first error's complete stack is still needed to
identify the failing menu callback.

## Current candidate (dev.53)

Dev.53 retains the dev.52 frontend error-containment behavior and clarifies
which validation failed when borrowed Lua bytecode cannot be retained. If the
UI error callback marks the current frontend generation broken, compatibility
scripts are skipped at each of the three `require` hook injection points until
the next frontend generation. Native `require` still runs normally, the mod
stack is not cleared, and unload remains available. These changes do not repair
the third-party module failure that triggers the containment path.

The latest console log shows a 256 KiB retention mapping request returning
null before UI 66077 and follow-on UI errors. This confirms an allocation
failure and the later UI cascade, but not the cause of the native SIGILL or
reported gameplay/map crashes. A multi-mod run logged many GSC runtime errors
in shared and map/mod scripts; no evidence isolates them to our GSC. The
separate Waffle capture loaded the map, logged 20 shared-script runtime errors,
and recovered image-streaming misses from 80/1040 to 0/1040 while GPU
completion advanced. It does not demonstrate a GPU deadlock or justify global
asset-pool expansion. Keep those crashes open pending a matching build and
first-fault native/kernel evidence.

Validation before packaging: 34 host regression programs, 8 console-log tests,
and 5 project-session tests passed. These are source/host checks, not PS5
stability validation. The dev.53 debug SPRX built with the pinned OpenOrbis
toolchain, passed target inspection and payload comparison, and received FTP
`226 Data transfer complete` at `/data/nexHEN/plugins`. It was not read back
from the console; gameplay validation remains pending.

Current candidate: dev.52 adds a frontend Lua-error containment guard after the
dev.51 PS5 capture showed a third-party menu exception followed by our own
compatibility scripts entering that failed UI state. It retains the selected
mod stack. This does **not** fix the third-party Lua exception or prove that
Reaper Collection can build its menus; console validation is required. The
dev.50 multi-mod crash and camo/custom-map startup reports remain separate; see
[Issue #23 investigation](INVESTIGATION-23.md).

## Frontend and custom-map review (2026-10-29)

- A supplied LUI trace includes the stock `AddButtonsForTarget` callback under
  our wrapper, which previously did not contain stock callback exceptions. The
  wrapper now logs once and returns a fresh empty table on exception, while
  preserving the stock return table exactly on success. It does not reuse
  buttons between targets or append the Mods item after a failed stock build.
- A focused Lua regression passes for the success path, exception recovery,
  non-reuse, log-once behavior and absence of menu injection on failure.
- The submitted camo logs do not show a definitive crash trace tied to selecting
  camo. No pool, weapon, or camo logic was modified.
- The custom-map startup capture shows a long loading interval and continued
  frames, but no definitive crash marker. No streaming or pool behavior was
  changed based on that evidence.
- Full host suite: 34 regression programs passed. This does not establish
  console/LUI stability; the menu path and exact camo/map reproductions still
  need hardware logs.

See [the sanitized investigation and continuation plan](INVESTIGATION-2026-10-29.md).

## Frontend Lua exception containment (dev.51 evidence; dev.52 candidate)

- The 2026-10-29 PS5 session identifies dev.51. Reaper Collection's `core_mod`
  fastfile and its UI Lua zones were selected and reported loaded before the
  frontend failed. The error is UI 24280 in `ui/uied/leveling_io.lua`, a nil
  index at stripped location `3778239045:654`. UI 21544 (`main` missing) and UI
  95515 (`Lobby` missing) follow. Those later errors are consistent with the
  frontend failing to construct; the trace does not identify the nil field.
- The local fastfile's asset walk confirms that the named Lua rawfile is
  supplied by the mod. ACTS confirms the payload is compiled BO3 Lua 5.1
  bytecode; it does not provide source lines or identify the nil operand from
  this capture. No third-party Lua was changed or copied into the repository.
- The trace then shows BO3-Customs' UI scripts entering the same failed
  frontend generation. dev.52 changes only that behavior: after a UI error in
  the active UI state while mods are selected, it clears stale `main`-menu
  readiness and pauses our compatibility injection until the next frontend
  generation. It leaves loaded zones and mod selection intact.
- Focused regression checks cover one-shot latching, no extra UI probes,
  generation reset, and ignoring in-game errors. This is fault containment, not
  a repair to the mod's Lua; if the underlying exception persists, the menus
  may still be unavailable in that session.

## Multi-mod crash and image-pool exhaustion (dev.50 evidence; dev.51 candidate)

- The persistent PS5 log records a Database-thread SIGSEGV while mods were
  loading in the frontend. Immediately beforehand, the engine reported the
  image pool full at 45,979/45,979 as another image linked. The backtrace is in
  the game executable, so this is strong evidence for pool exhaustion as the
  trigger, not proof of the exact faulting engine operation.
- Several mods were active. Their individual contribution is not isolated.
  Earlier GSC errors are from untracked scripts and do not identify the native
  crash cause. The `snddriverglobals` 1/1 report is not treated as exhaustion
  without proving it is not a singleton pool.
- Review of the same snapshot did not justify expanding more pools yet:
  material was at 22,220/22,870 after already growing from its 19,712 baseline;
  localize, rawfile, stringtable, scriptparsetree, weapon-camo, FX, leaderboard
  and font pools already have lazy growth handlers. XModel was at 9,204/10,240,
  not exhausted, and XModelMesh had no captured exhaustion event or validated
  entry layout. Raising those limits preemptively would spend memory without
  evidence that it helps performance. Pool growth prevents allocator
  exhaustion; it does not increase frame rate by itself.
- The working tree adds lazy growth for image assets only when the runtime
  entry size and initial limit match the observed BO3 1.33 layout. It limits
  the additional reserve to 25%, allocates in the existing 1 MiB batches, and
  uses the shared 64 MiB budget. It fails closed on a mismatched pool layout.
  Debug streaming scans stay within the original contiguous image table because
  overflow entries are separate free-list blocks.
- Pool snapshots now include entry size, singleton status and free-list state.
  This separates true exhaustion from expected 1/1 singleton records and gives
  us the runtime layout evidence needed before considering XModel or other
  additional pools.
- The previous focused pool-growth regression passed, including free-list,
  bounded-capacity and mismatch cases. The current candidate also changes
  pool-snapshot diagnostics; it must pass the hosted source checks and native
  build before upload. No console validation has been done for this candidate.
- The candidate build label is dev.51. A matching PS5 test is required before
  calling the crash fixed. If the image pool fills again, capture the new
  growth/cap log and test the same mod stack one item at a time before extending
  other pools.

## Evidence and present behavior

| Area | Source/check evidence | Console evidence / remaining work |
| --- | --- | --- |
| Kernel file metadata | Explicit native stat ABI and image-parser checks replace an incompatible host layout | Previous image-preview correction was reported working; recheck after relevant IO changes |
| Lua lifetime | Mod/custom-zone bytecode retention, version deduplication and bounded dedicated memory; no blanket copying of stock UI because metadata is truncated or busy | The latest report confirms an initial UI-content load/unload; repeated entry still needs validation |
| Startup / frontend | Native frame precedes companion work; readiness resets on frontend transitions, including reused VM addresses | Early plugin injection and repeated mode/map returns need hardware checks |
| Menu re-entry | Console entry owns its callback; controller normalization and scoped live selection queries; twenty host Lua reopen cycles | Candidate addresses an observed LobbyVM 74046 / UI 40546 sequence; exact inner nil access and a later native crash are not conclusively attributed |
| Persistent diagnostics | Separate bounded error log, context/stack capture, short-write handling and IO retry; session log behavior retained | Validate console append across restarts and kernel correlation during a real fault |
| Content activation / joining | Transaction and readiness checks exist, with host regressions | Successful download is not proof of activation or matching BG-cache/schema; controlled peer testing remains necessary |

## GPU completion and lighting diagnostics (source-only, 2026-10-29)

- `SPRX/t7_maps.cpp` now reports completion-label changes and submission-counter
  changes independently. An unchanged completion value is **not** a proven GPU
  deadlock when the CPU may have stopped submitting work.
- The lighting-blob summaries now treat state 2 as **loading**, not resident.
  State 3 or higher is counted as resident, matching the per-record `[Blobs]`
  description. The GPU sample identifies resident/total counts separately for
  probes, volumes, sun-shadow trees, other resources and sky resources.
- The latest GPU regression suite passes in GitHub Actions. These are
  diagnostics/counter-correctness fixes, not forced GPU completion, a resource
  allocator change or a demonstrated reduction in black-screen duration.

**To establish a root cause on hardware:** use the exact matching experimental
SPRX, reproduce a single map load on PS4 and PS5, and preserve the first
`[GPU]`, `[Stream]`, `[Blobs]` and `[Stall]` sequence before restarting.
Compare whether frame/submission counters advance while completion does not,
and whether a specific required resource category remains loading. Include the
first engine error and thread stack. Without that evidence, changing GPU waits
or marking a deadlock fixed would be speculative.

## Work-mode GPU investigation handoff (2026-10-29)

Source is based on dev.34 plus subsequent source-only changes; the installed
candidate does not contain these changes. No new artifact was produced.

| Finding | Evidence / limit | Next step |
| --- | --- | --- |
| Timeout could report ready with required parts absent | Production-hook fixture reproduces idle flags plus missing image/mesh bits; previous source incorrectly changes the script result to ready | New residency guard passes; verify compatible loading on hardware before claiming a runtime fix |
| PS5 startup stall | Saved persistent log identifies dev.34; five native frames, zero linked assets, completed 5743 vs requested 5741 across repeated samples | Resolve main-thread wait with matching native identity; this is not evidence of an uncompleted requested frame |
| PS4 gameplay compute stall | Historical capture repeats completion 243894 vs latest recorded compute job 243911 | Identify caller/shader/resource with matching native evidence and an isolated run; the cause is unconfirmed |
| Timeout guard cannot explain that gameplay capture | Native texture readiness was recorded after approximately 36 seconds, before the 180-second fallback | Keep the native compute investigation separate; do not label the guard a cure for this incident |

Implemented guard: check required image/mesh residency only after the timeout and
idle-stream checks; reject unreadable tables, newly queued stream work and observed
level changes. Throttle failed probes to 250 ms. Preserve native readiness, native
call arguments/results, stock-map behavior and repeated successful fallback calls.
No new lighting requirement or GPU completion write was introduced.

Validation: thirty production-source host regression programs pass. The new test
fails against the preceding source at the missing-required-texture assertion.
The changed PS4 translation unit passes installed-SDK Debug and Release syntax
checks without linking or packaging. These results do not validate BO3 scheduling
or show that a map with permanently missing required parts can finish loading;
the guard deliberately does not declare absent required data ready.

Remaining paths, in order:

1. Match the native main-thread wait and compute dispatch caller to the correct
   executable/source. Do not reuse an offset from a binary whose hook signatures
   do not match. Existing private analysis identified such a mismatch.
2. Compare isolated startup and gameplay reproductions with unchanged content,
   matching candidate/artifact identity and complete initial error/stack context.
   Separate CPU submission stoppage, outstanding compute work and IO backlog.
3. If the wait points to dynamic-image lifetime or frontend reentry, test that
   exact path against repeated working cases before changing ownership/scheduling.
4. If required resources remain absent, compare native requirement/residency bits
   and routed input files. Repair verified resource/conversion defects rather than
   declaring them loaded. Streamer idle flags alone do not identify the defect.
5. Grow a pool only after observed exhaustion and verified allocator/index bounds.
   Current startup samples do not show exhaustion of the observed major pools.

Rejected actions: force completion labels, bypass GPU waits, arbitrary pool growth,
remove content/features, or attribute a freeze to the final file in a log.
Raw captures, kernel details, private content names and machine paths stay local.
Chat can review this source/report; new console reproduction and native tools need
Work access. Ask for build approval only after the next source correction is reviewed.

## Menu validation still pending

1. Use the matching candidate SPRX and companion `Lua/ui_scripts/mods.lua`.
2. With one test content item, load, unload and reload three times.
3. Enter and leave a match, then repeat selection/apply.
4. Read the earliest error, selected/loaded state, controller and menu generation.
5. If it fails, preserve the report before another restart and compare multiple
   causes. Do not change unrelated content or blame a last-loaded file without proof.

Potential follow-ups if the candidate does not resolve re-entry:

- Capture current menu/global function identities; check wrappers from an obsolete
  Lua table or an unsupported PC callback after frontend reconstruction.
- Inspect the exact nil operand using matching source/bytecode evidence.
- Check pending frontend-apply/reload flags after an empty selected stack and map
  return. Do not use a permanent restart requirement as the normal unload path.
- Compare an isolated item with an overlapping stack; a conflict is a separate
  result from failure of the loader's own menu.
- Use the exact built ELF for plugin stacks and a verified matching game image
  when native engine identity is needed. Never patch an assumed function.

No universal crash fix or performance improvement is established by these tests.
Asset-pool capacity, available process memory, IO stalls and UI state are separate
questions. Grow only verified pools on demonstrated exhaustion; never manipulate
GPU fences, arbitrary memory regions or native validation to hide a failure.

## Source map

- `SPRX/t7_maps.cpp`: catalog/zone routing, stack transactions, frontend handoff.
- `SPRX/t7_lua.cpp`: UI ownership, native hooks, compatibility and bytecode lifetime.
- `Lua/ui_scripts/mods.lua`: console menu entry, selection and scoped callbacks.
- `Lua/ui_scripts/mapselect.lua`: map selection and recovery.
- `SPRX/t7_log.cpp`, `error_capture.hpp`: diagnostics and persistent error context.
- `SPRX/t7_lua_ownership.hpp`: lifetime membership independent of display metadata.
- `SPRX/openorbis/`: target ABI adapter; `.github/openorbis-lock.json`: pinned tools.
- `SPRX/tests/`, `tools/console_diagnostics/`: regressions and read-only collection.

Private evidence and original binaries do not belong here. Keep only a sanitized
finding and a reproducible validation method in public status. Past draft release
notes and content-specific reports have been removed from the active source tree;
use Git history for source changes and GitHub Releases for approved distributions.

## Current source checks

The maintained host suite contains 33 regression programs, including two C++
executables. The separate diagnostic reader and publication guard have 13 unit
tests. The SDK header and native artifact comparisons require explicit matching
inputs and are not silently replaced by host stubs. These checks do not establish
console stability; GPU/native stall and repeated menu re-entry validation remain open.


## Current review update (2026-11-18)

PR #39's source head `481d4d4952952f07a52c60e6605197b11474473d` passes all six workflows and 47 host regression programs. The delayed custom-image callback gap is addressed with a 1,024-entry process-lifetime no-eviction tombstone registry, fail-closed capacity behavior, stock-slot reuse passthrough and a production-hook ASan/UBSan regression. The later docs/workflow-summary-only head `f1ad3a282b0fe28494a9cdc4d0f459a65c7f26db` is awaiting its project-session guard. PR remains draft; no target build or console test.

PR #42 bounds rawfile asset-name reads and diagnostic formatting. All six workflows, source-policy audit, publication guard and 43 host regressions pass on `bfc2673bd9e5acd816408fca4fc7681fe172380c`. It is ready for review, not merged. Neither PR has a native target build or console result.


## Target compile blocker — FolderScanStatus (2026-11-18)

Automatic BO3 Auto Build run #75 was triggered by a documentation push to `main`, attempted the PS4 cross-compile and failed because a literal `\\n` after the `// libkernel ENOENT` comment left `FolderScanStatus` commented out in `t7_maps.cpp`. The compiler then reported an expected-unqualified-id and undeclared enum references. Artifact upload and native-module inspection were skipped. PR #43 restores the real newline and adds a source-line regression guard. SPRX diagnostics, source-policy audit, publication guards and all 42 host regressions pass on source head `e0e1af00e4d51c41250d13ff9cfa4fa42d59702f`. The compiler stopped at its error limit, so more target errors may remain. No second build or console test was performed.


## Repository progress update — 2026-11-18 (GitHub-only)

Current base: `main` at `2515af69f1c76d93e64dbd448938bcc9290108e2`.

- PR #39 (`recovery/issue-driven-dev65-dev69`) is rebased onto current main at `91296a01562a7f841e438678c61fb5158e73b917`. It contains the dev.65 queued-zone/UI/image-lifetime safeguards and dev.69 bounded stream-rejection diagnostics. A follow-up closes the Pending-publication race where FrameWork could clear Pending while the loader was still constructing its wait-zone list. All six PR workflows and both push checks pass. Keep draft until the independent #43 compile blocker is resolved and target-build approval is explicit.
- PR #42 (`fix/lua-asset-name-bounds`) is rebased at `18540a02a69ba9f8147a4b5a14af9b0c2d33122a`; three fresh checks pass. It bounds game-owned rawfile-name reads and safe diagnostic formatting without changing Lua bytecode retention, mod-stack behavior, or stock Lua restoration. Ready for review, but do not merge before #43 resolves the target compile blocker.
- PR #43 (`fix/folder-scan-status-declaration`) is rebased at `e2e4c429ab44b8f85eb70a813c7446cac0e4c41a`; all six PR workflows pass. It restores the real newline before `FolderScanStatus` and guards the previous host-test blind spot. No target build was run after the correction; more target compiler errors may remain.
- PR #40 (`recovery/xasset-entry-index-safety`) is rebased at `0fb48768dc80e35b5f4ee6d86351f110b0cb3d74`. It remains arithmetic/test groundwork only, not a runtime allocator fix. Native allocator ABI, all index consumers and synchronization remain unverified.
- PR #41 (`investigation/blood-run-bootstrap-regression`) is rebased at `ab1b8e5d4a358d92d4bd70cb01292414358c21b1`. It tests only the existing absent-only usermap Lua fallback; Blood Run GSC/gameplay/pause failures remain unresolved.
- PRs #37 and #38 were closed as superseded by combined PR #39; they must not be merged independently.

Issues #29, #30, #31 and #33 received source/validation status comments. Issues #1, #2, #20, #23, #28 and #32 remain open with their existing evidence requirements. Do not claim the Buried crash, Blood Run gameplay stall, GPU fault, Seven-Eleven hang, BG-cache join failure, or complete FFPorter package is fixed.

No native target build was run after the FolderScanStatus correction. No console test, upload, release or deployment was performed. Merging to `main` triggers the automatic PS4 build workflow; do not merge or trigger that build until explicitly approved. Host CI is not target ABI or console proof.


## Follow-up findings — 2026-11-18

- PR branches were synchronized once more after the documentation-only `[skip ci]` commits, so the current PR heads above are based on the latest `main`. The latest host/PR checks passed for #39, #40, #41, #42 and #43. Their target-build and console boundaries remain unchanged.
- PR #44 was closed without merge because its Tool/Porter changes are outside the repository's active SPRX/Lua maintenance scope. Its exploratory Windows run exposed stale Community/Pause test expectations for the retired `out/t7` layout; current settings use `out/usermaps` for maps and `out/mods` for mods. No Tool/Porter workflow or source changes were merged.
- Issue #23's stored failure log was re-reviewed: mod-slot-2 maps to DS4C Patched in the two-mod stack; `array_shared.gsc +0x4220` first reports a by-reference array-type error, followed by repeated invalid opcodes at `+0x4222`. The 20-second stall sample shows no client frames while GPU completion/submission counters continue changing and required image/mesh parts are complete. This narrows the investigation to the DS4C shared-script override but does not prove it caused the stall. The exact DS4C package/source is still needed.
- No target SPRX build, console test, upload, release or deployment has been performed. Do not merge to main until the target build is explicitly authorized; main pushes trigger the automatic PS4 build.


## Final source/host validation snapshot — 2026-11-18

All five active source PRs are now rebased onto the current `main` and have passed their latest PR workflows and push project-session guards:

- #39 `91296a01562a7f841e438678c61fb5158e73b917`: UI transition/image lifetime safeguards and bounded stream diagnostics; includes the Pending-publication race correction.
- #40 `0fb48768dc80e35b5f4ee6d86351f110b0cb3d74`: XAssetEntry address/index arithmetic groundwork only; native allocator integration is still unverified.
- #41 `ab1b8e5d4a358d92d4bd70cb01292414358c21b1`: Blood Run absent-only Lua fallback regression only; GSC/gameplay/pause failures remain open.
- #42 `18540a02a69ba9f8147a4b5a14af9b0c2d33122a`: bounded XAsset rawfile-name reads and diagnostics.
- #43 `e2e4c429ab44b8f85eb70a813c7446cac0e4c41a`: FolderScanStatus source newline correction and host regression guard.

PRs #37/#38 are closed as superseded by #39. PR #44 was closed without merge because Tool/Porter is outside the active SPRX/Lua maintenance scope.

### Lua retention / disable safety review

The current main implementation in `SPRX/t7_lua.cpp` retains HKS bytecode in a dedicated mmap arena (32 MiB total budget, 8 MiB per chunk, 4,096 retained headers), deduplicates byte-identical chunk bodies while preserving distinct asset headers/names, and keeps older revisions alive for cached closures. It avoids the transient libc heap and does not evict old retained assets. The ASan/UBSan host fixture covers source-page unmapping, repeated lookups, concurrent retention, same-name revisions, alias-body deduplication, allocation/budget failures, and native stock-rawfile passthrough when mods are disabled. This is source/host evidence; it does not replace the eventual console test of disabling mods after a real mod session.

### Remaining hard blockers

- `kMaxStack = 24` is a separate internal mod-stack bound. It sizes several fixed arrays and each stack entry embeds up to 160 file records. It has not been raised because doing so blindly changes static memory use and may exceed unverified native consumers. The user's no-artificial-stack-limit requirement is not yet satisfied.
- XAssetEntry reserve-page allocation still needs the exact supported-build native allocator/free-list ABI, every index consumer and synchronization contract.
- Blood Run's actual GSC failures still need matching GSC source and a clean-start console capture.
- Issue #23 is narrowed to the DS4C Patched mod-slot-2 shared-script override, but its exact package/source is not present; the GSC error does not prove it caused the stall.
- GPU resource ownership, clientfield schema comparisons, BG-cache/host activation behavior and full FFPorter package acceptance still require their matching native/runtime evidence.

No target SPRX build was run after the FolderScanStatus correction. No console test, upload, release or deployment was performed. Merging any PR to `main` triggers the automatic PS4 build; explicit approval is still required before that step. The five PR branches are clean and host-validated; their source diffs are ready for final target-build sequencing, not yet console-validated.


## SPRX-only progress — 2026-11-18

Current active scope is SPRX stability and Lua integration. FFPorter is explicitly out of scope for this workstream; no FFPorter source or workflow change is part of the current SPRX work.

- PR #45 (`fix/nonblocking-lua-fallback-lock`) replaces the unbounded wait in `LuiExtraFor()` with a single acquire attempt. The fallback cache is optional; when busy, the hook declines the PC-side fallback instead of sleeping indefinitely in an asset lookup. Native lookup arguments/results and stock Lua behavior remain unchanged.
- PR #45 adds `SPRX/tests/lua_extra_lock_checks.py`, which executes the production function with host stubs under ASan/UBSan and verifies lock contention returns immediately without file I/O or cache mutation, plus normal/cached/missing/invalid-path/capacity behavior.
- The test is registered in the complete host runner and focused SPRX diagnostics workflow.
- PR #45 was rebased onto main at `fb5e90a6ec1f4916d6224bf39eab91e3fc038a6f`; current head `9637b01d61b57c6c15809dc367f3c1f85ea81989` is 5 commits ahead and 0 behind. SPRX diagnostics, complete host regression inventory, source-policy guard, in-game script-log regression and push project-session guard all pass.
- PR #45 remains draft pending full source review and an approved target build. This is not proof of a PS4/PS5 runtime stall fix.

Other active SPRX boundaries remain:
- PR #39: UI transition/image lifetime guards and bounded stream rejection diagnostics; source/host validation only, not target/console validation.
- PR #42: bounded Lua rawfile-name reads; source/host validation only.
- PR #43: FolderScanStatus target translation-unit correction; host checks passed, but no target build has verified whether further compile errors remain.
- PR #40: XAssetEntry reserve-index arithmetic only. Do not implement an allocator hook without the exact supported-build ABI, full native index-consumer contract and synchronization proof.
- Issue #28: GPU fault remains unattributed. Existing GPU progress sampling is read-only; it does not identify the submitting GPU command or prove ownership.
- Issues #1/#2: transition and script diagnostics exist, but native clientfield registry comparison and validated caller/entity context remain open.
- Issue #30: reserve-page allocator work described in the issue is not present as a verified source patch in the current PR; do not imply the dev.67 local candidate is merged.

No native target build, console test, upload, release or deployment was performed. Merging to main triggers the automatic PS4 build; do not merge until the user explicitly approves that build. Host CI is not target ABI or console proof.


## Companion Lua cache concurrency follow-up — 2026-11-18

- PR #46 makes the four built-in companion Lua cache entries race-safe. A per-entry atomic state machine (Uninitialized/Loading/Ready/Failed) gives one worker initialization ownership; body and RawFileAsset fields are fully written before Ready is release-published. Readers acquire-load Ready before consuming them.
- Concurrent first-time lookups never wait on file I/O or inspect partially initialized metadata. They defer the optional companion override for that request; a later request can use the completed entry. Failed first reads remain negatively cached as before.
- Added `SPRX/tests/lua_file_cache_concurrency_checks.py`, which executes the production lookup function with 32 concurrent readers while the first read is held, then verifies one initializer, no partial publication, shared ready reads and cached failure. Registered in full host CI and focused SPRX diagnostics.
- PR #46 head `f4a4f948f8b193a877b342fa64285009c2f02d48` passed SPRX diagnostics, complete registered host regression inventory, source-policy guard, in-game script-log regression, and push-side checks.
- PR #45 separately addresses the unbounded lock wait in the optional Lua fallback cache; its current rebased head `575c058f5ee2f2cfa6164cf9f7e09b1cbec4b926` passed the same SPRX/host/guard/script-log checks.
- Both changes are draft PRs; neither has been target-built or console-tested. Their first-request fallback behavior is explicitly best-effort under contention and does not change bytecode-retention or mod-disable semantics.

These changes are source/host validated only. They do not establish a PS4/PS5 loader stall fix. Do not merge or trigger the automatic target build until approved.
