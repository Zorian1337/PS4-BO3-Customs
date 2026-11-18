# Current SPRX handoff — 2026-11-18

Read `AGENTS.md` and the authoritative section at the top of [the SPRX stability roadmap](docs/PS4-STABILITY-ROADMAP-2026-11-17.md) first. That roadmap is the source of truth for scope, every open SPRX issue, evidence, proposed fixes, priority, PR status and buildability gates.

- **Scope:** SPRX/runtime only, including companion Lua where it is part of SPRX behavior. FFPorter issue #32, Osiris and unrelated projects are deferred.
- **Repository:** `Zorian1337/PS4-BO3-Customs`, branch `main`.
- **Current main:** `main` (documentation-only follow-ups after the verified source build).
- **Last verified buildable source:** `46c72aba2738f66221f344e77f445d136c27f596`. PR #54's fresh target build #44249707280 passed.
- **Merged fixes:** PR #50 (FolderScanStatus target compile), #51 (bounded Lua asset-name reads) and #52 (nonblocking optional Lua fallback + atomic companion-Lua cache publication).
- **Latest target build:** [BO3 Auto Build #44249707280](https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44249707280) completed successfully. All 14 native translation units compiled, GoldHEN link/package succeeded, native module/container validation passed, and the final workflow gate succeeded.
- **Verified Debug SPRX:** artifact `bo3-sprx-46c72aba2738f66221f344e77f445d136c27f596-1` (ID `14403093011`), 487,088 bytes; SHA-256 `7f33a320338eaa28ea6868b48d2a68e4ac428d9b1856b1f12b92e69f60bfef0d`. Hash matched the downloaded artifact and manifest. Native evidence artifact ID `14403137765`.
- **Open PRs:** #39 (draft; wait-zone publication race review required), #40 (arithmetic-only XAssetEntry groundwork), #41 (Blood Run fallback regression), #47 (GPU/clientfield/zone evidence), #55 (Lua ownership publication; checks pending). PR #54 (bounded bytecode-retention lock) is merged and target-build validated. PR #56 (Lua ownership publication) has exact-head checks running; target build is pending. PRs #42/#45/#46/#53 are closed unmerged as superseded by #51/#52/#54. PRs #43/#48/#49 are superseded and closed; #37/#38 are superseded by #39.
- **Lua acceptance:** users must always be able to disable mods and restore original included Lua behavior without crashes, resets, stale bytecode or partial state. PRs #51/#52 do not complete HKS module-cache or full disable/restore validation.
- **Remaining work:** review and target-build PR #53; close the ownership-index publication and full HKS disable/restore evidence gaps; audit mod-stack capacity; continue native XAssetEntry, GPU, zone/clientfield and GSC evidence tracks. Rebuild after every subsequent source change before calling that revision buildable.
- **Validation boundary:** the exact commit above is buildable. The manifest records `console_validated: false` and `sony_signed: false`; no PS4/PS5 console validation, FTP deployment or release was performed. Buildability is not a stability guarantee.
- **Workflow:** document each issue and proposed correction before implementation; keep the SPRX inventory current; add production-path tests; update this file and the roadmap after every meaningful change. Work in Chat mode using connected GitHub tools when Work mode is unavailable.
- **Publication:** source/test/docs only. Keep private logs, binaries, toolchains, credentials and third-party plugin content out of the public repository. Do not upload/release or claim console validation without actual evidence.

---

## Historical handoff archive

## Historical handoff archive

## Historical handoff archive

## Historical handoff: map-load diagnostics + transactional catalog refresh (PR #36; now merged)

## Catalog refresh safety implementation

The current branch now treats directory enumeration as a result, not just an
entry count. It distinguishes optional ENOENT from open failures, getdents
read errors, stat failures for DT_UNKNOWN entries, malformed/truncated records,
overlong names, capacity exhaustion, and close failures. DT_UNKNOWN entries
are stat-classified rather than silently omitted. Optional folders (user maps,
shared zones, mod roots, alternate package folders, sound folders, and movie
folders) may be absent; once present, scan failures abort publication.

All catalog scanners propagate failures. Package/file/mod/movie limits, path truncation, and generated custom-map Lua
buffer truncation now fail the candidate scan instead of silently producing a
partial list. Every data root is preflighted and rechecked after scanning; if a
root that supplied existing catalog entries disappears or becomes inaccessible,
the candidate is rejected rather than silently dropping that storage's maps. Refresh takes a rollback snapshot of package/file/movie/mod
arrays, counters, generated map Lua buffers, mod-description ownership, and the
mod-Lua dirty flag while the existing reader/writer gate excludes readers.
Only a fully completed scan commits; a failed scan frees candidate descriptions
and restores the last known-good snapshot. Snapshot allocation failure leaves
the current catalog untouched. Startup has no previous catalog, so a failed
initial scan clears its candidate and publishes no partial entries.

The scan remains synchronous. No worker-thread scan or double-buffered
publication was introduced. T7Maps_MapCount() and T7Maps_ModCount() now
participate in the reader gate. The Lua-string accessors retain their existing
synchronous-consumption contract; callers run the returned source immediately
on the frame/UI path rather than retaining it across a refresh.

A new host regression exercises the actual production ListFolder() function
against empty/missing directories, open/read/stat/close failures, malformed
and unterminated records, truncated dirent headers, overlong names, capacity
exhaustion, and unknown entry types. It also exercises checked Lua appends,
storage-root loss detection, rollback, and description ownership invariants.
It is registered in the full host inventory and focused SPRX diagnostics.

**Validation:** implementation source head ba6f5a43d8e3dcf658278c085e9d585a3d9de31a passed
the full-range source publication audit, publication-guard unit tests, all 42
registered host regression programs (zero failures), focused SPRX diagnostics,
and the related frontend/mod-stack/script-priority workflows. The new
directory, storage-root, Lua-output builder, and catalog rollback tests all
passed. No native SPRX build, upload, release, or PS4/PS5 console test was
performed. The zm_ccube crash cause remains unknown; diagnostics and catalog
safety are not a claim that the map crash is fixed.

## Map-load diagnostics

The Debug map preflight checks package-local .ff and .fd files separately
and records the /app0/zone fallback state. Custom-map package file opens log
elapsed time and returned fd, including failures. The native LoadLevelZones
call logs its own duration separately from mod preparation. These remain
observational diagnostics.

## Candidate reconciliation — dev.69 / issue #33

Issue #33 describes a dev.69 DEBUG candidate with a bounded
`stream-block-rejected` event for the existing backend stream guard. A direct
source check of both public `main` and PR #36's `SPRX/t7_maps.cpp` found no
such event string or trace implementation. The issue therefore describes a
candidate that is not reproducible from the currently published source refs.

The issue records a local SPRX size of 487,856 bytes and a remote FTP SIZE
response of 576,352 bytes (the OELF container size); the remote bytes were not
read back. Remote artifact identity is unverified. Treat dev.69 as a local
test candidate, not a verified public-source build or release.

Next: recover and review the exact dev.69 source patch, reconcile it with the
current branch, add a production-body regression for both guard branches and
the 16-event cap, then rerun source CI. Reproduce Buried from a fresh process
without mods and correlate the trace with the first kernel fault. The SIGSEGV
at RIP `0xFA2A98` remains unexplained. Do not rebuild, upload, release, or
claim a fix without explicit approval and matching evidence.

## Review follow-up validation (2026-11-17)

The full source review caught three stale mod-stack calls to the previous
four-argument `ListFolder` API. They now consume structured scan results,
log incomplete scans and roll back file additions from a failed folder scan.
The host regression now checks the arity of every production scanner call.

Final reviewed head before this documentation sync,
`c48c5b54e8a6e8bce9fa64d8662cf94f3973067f`, passed all five required GitHub
workflows: SPRX diagnostics, project-session guard, frontend reload,
mod-stack transaction and script-priority. The project-session guard audited
the complete `main`-to-PR diff, passed its own unit tests and the full
registered host regression inventory. The directory scanner, storage-root,
Lua-output, catalog rollback and map-load timing fixtures passed.

No native SPRX build, upload, release or PS4/PS5 console test was performed.
PR #36 is merged. No native SPRX build, upload, release or PS4/PS5 console
test was performed. The `zm_ccube` crash remains unresolved.

## Review boundary

PR #36 is merged; no further PR action is pending. Do not build/upload/release
an SPRX unless separately requested.

---


Branch: `diagnostics/map-load-phase-timing`; PR:
https://github.com/Zorian1337/PS4-BO3-Customs/pull/36

The Debug map preflight now checks package-local `.ff` and `.fd` files
separately and records the `/app0/zone` fallback state. Custom-map package
file opens log elapsed time and the returned fd, including failures. The
native `LoadLevelZones` call logs its own duration separately from mod
preparation. These are observational diagnostics only; they do not change
routing or claim to fix the `zm_ccube` crash.

PR head `ca9fd4d5f8f901b5b35daeaa5807fc8a31317532`: focused SPRX diagnostics
passed; full-range publication audit passed; publication guard unit tests
passed; all 41 registered host regression programs passed. No native SPRX
build or PS4/PS5 console test was performed. PR #36 is now merged.

Next source task: recover and review the dev.69 trace patch provenance, then
continue the Buried crash investigation without speculative runtime changes.
Do not move scanning to a worker until catalog pointer lifetime and reclamation
are explicitly safe. Keep the current synchronous refresh behavior until the
double-buffer design is proven.

# Current candidate: dev.60 (existing); next source-only review branch: stability/pool-lookup-hotpath

## Asset-link hot-path lookup optimization (2026-11-17)

The sorted asset-pool growth allowlist is now searched with binary search instead
of a full linear scan for every linked asset. This preserves the same allowlist
and capacity policy while reducing lookup comparisons from O(N) to O(log N).
The host fixture now verifies strict table ordering, every entry's lookup, and
missing types. This is an algorithmic hot-path reduction, not a measured
console speed claim. It is isolated on stability/pool-lookup-hotpath. The final PR diagnostics run
passed, including both pool fixtures, and the focused mod-stack, frontend-reload,
script-priority and import-lifetime workflows passed. No native build or console
test was requested or performed.

Latest PR diagnostics run https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44170446291 passed on workflow commit `19adea1`, including host-runner inventory validation, pool-growth and pool-out concurrency tests, and Lua recovery checks.

See [the pool lookup optimization note](docs/POOL-LOOKUP-HOTPATH-OPTIMIZATION-2026-11-17.md).

# Current candidate: dev.60

## Pool-out diagnostic concurrency fix (2026-11-17)

T7Log_PoolOut() runs from concurrent asset-link workers. Its process-lifetime
once-only latch is now atomic, and a 32-worker production-function stress test
verifies one diagnostic per exhausted type. The pool-growth and pool-out tests
are both part of pull-request diagnostics and the full host test inventory.

## Frame-stall hardening (2026-11-17)

See [the frame-work hardening report](docs/FRAME-WORK-STABILITY-2026-11-17.md)
and [the original incident analysis](docs/INVESTIGATION-2026-11-17-FRAME-STALL.md).
The mod-variable autosave now queues an owned config snapshot for background
persistence and retries after queue or disk-write failures. Debug watchdog
phases distinguish lobby evaluation, hosted-state snapshots, share completion
and full catalog refresh. Rawfile UI filenames are now scanned only within
their 96-byte destination bound, with every byte checked readable and a
terminator required before ownership tracking.

GitHub verification on commit `7e241f8`: all 38 host regression programs
passed, including the unreadable-page-edge filename test; the SPRX diagnostics
workflow passed; and the automatic PS4 GoldHEN Debug build plus native-artifact
validation passed. No console test has been performed. The full catalog refresh
remains synchronous intentionally:
its writer lock currently makes readers wait, so a naive worker move would
still block the main thread. A double-buffered catalog is the safe next design.
Do not claim the historical stall/crash resolved without a matching console
reproduction and fresh watchdog capture.

The DS4C dev.58 console session reports a stripped-code nil-index in the
modded progression UI, followed by failed `main`/`Lobby` registrations. The
exact nil operand is not recoverable from the protected fastfile payload, so
dev.60 does not claim to fix that third-party callback. It fixes a separate
source recovery defect: a successful native `AddMenu("main")` rebuild now
clears the UI-error latch and retries compatibility injection with fresh
state-local caches. Focused ASan/UBSan coverage passes. See
[the DS4C investigation](docs/INVESTIGATION-2026-11-02-DS4C-UI.md).

## Upstream stability review (2026-11-17)

See [the Joker upstream comparison and stability action list](docs/UPSTREAM-STABILITY-REVIEW-2026-11-17.md). It records which upstream hot-path implementations are less safe than ours, the shared unchecked initialization/watchdog thread creation defects, and the next timing/test work. No source behavior or build was changed during that review.

Dev.60 is a Debug test candidate. The target build still needs to pass. Console
validation of the DS4C UI remains required; no gameplay crash or map stability
claim follows from these logs.

## Previous candidate: dev.59

See [Waffle Tower launch investigation](docs/INVESTIGATION-2026-11-02-WAFFLE.md).
The new correction handles exact readable bytecode ranges across more than
eight adjacent mappings and separates validation failures from allocation
failures. Waffle Tower gameplay and DS4C frontend-camera errors remain
console-validation tasks. README now inventories implemented SPRX features
and their limits. Earlier UI fixes and validation history follow below.

# Current handoff: dev.58 UI compatibility source

The current Debug candidate is dev.58. The bytecode-confirmed footer failure
uses an absent PC StarterPackWatermark class before the old post-construction
repair can run. The missing-only class fallback fixes that ordering for both
footer variants and preserves provider implementations, including inherited
ones. Additional source corrections handle incomplete description widgets,
replacement LuaUtils/LUI tables, probe retry/cleanup, and callback ownership.

Read [the investigation](docs/INVESTIGATION-2026-11-02-LOBBY-UI.md) for evidence,
rejected hypotheses, validation limits, and future diagnostic guidance. The
Debug native build and artifact validation passed. Focused native checks and
source checks passed. Lua 5.1 compatibility and menu-recovery scenarios passed in GitHub CI;
console validation of dev.58 remains pending. No universal mod stability or
kernel-panic prevention claim is made. Keep private captures and binaries out
of source commits.

## Earlier development history

# Resume SPRX / Lua development

**Active source line: `main`. Current candidate: dev.53 frontend Lua-error
containment on top of dev.52. It is a debug test, not a stable release; console
validation remains pending. The debug SPRX compiled and FTP returned a
successful transfer acknowledgement to `/data/nexHEN/plugins`; the binary was
not read back from the console.**

The dev.50 PS5 crash capture showed image-pool exhaustion immediately before a
Database-thread fault. dev.51 grows only that evidenced pool and adds
entry-size/singleton/free-list details to snapshots. The dev.51 Reaper capture
then showed UI 24280 in the mod's `leveling_io.lua`, followed by missing `main`
and `Lobby` menus; our UI scripts also entered the failed generation. dev.52
contains our injection after a modded UI error while retaining selected zones.
It does not fix the third-party Lua nil access. See
[development status](docs/DEVELOPMENT.md).

The newest dev.52 console captures also show a 256 KiB retained-bytecode mapping
request returning null, followed by UI errors 66077/64046/18426. Dev.53 clarifies
the specific validation failure and blocks all three compatibility-injection
points after a frontend Lua error, until the next frontend generation. The 166
GSC errors in the multi-mod capture and the separate EBOOT SIGILL do not prove
this Lua failure caused the gameplay crash. No global GSC or asset-pool change
is justified by those traces.

## Read first

1. [AGENTS.md](AGENTS.md): scope, privacy and publication rules.
2. [Development status](docs/DEVELOPMENT.md): verified findings and next checks.
3. [Workflow](docs/WORKFLOW.md): source validation and build procedure.

Do not reread old conversations or entire logs by default. Inspect the current
branch/diff and the specific source or incident needed for the next task.

## Where to continue

The current source review is summarized in
[docs/INVESTIGATION-2026-10-29.md](docs/INVESTIGATION-2026-10-29.md). It records
the LUI callback boundary fix, why the supplied camo and custom-map logs do not
prove a root cause, and what console evidence is still needed. Issue #23 remains
separate; read [docs/INVESTIGATION-23.md](docs/INVESTIGATION-23.md) before
resuming its multi-mod loading and Lua-state restoration work.

Verified source corrections isolate zone/XPAK/asset ownership per loader worker
and restore exact temporary Lua platform flags, including frontend table replacement.
Both regressions fail against the original source and pass after the corrections.
All 34 host programs pass; both earlier changed PS4 units pass Debug/Release
syntax validation. Dev.49 was built and uploaded for testing; console behavior is
not yet confirmed.

The console hang and Reaper's nil operand are **not confirmed resolved**. Preserve
native frontend rebuilding, automatic recovery and bytecode-lifetime protection.
Complete arbitrary-mod Lua-state restoration still requires lifecycle evidence;
do not replace it with broad global/module resets or a restart-only unload lock.

Latest source task: deduplicate the completed provider map list. Dev.49's older
table filter missed provider-appended rows because the external-owner wrappers
returned them unfiltered. The newer Lua keeps the provider builder/callbacks,
filters its completed rows into categories, and removes duplicates by both load
target and displayed title after removing color codes. Provider compatibility and
stats metadata stay attached to the retained row. An existing provider category
control retains ownership; otherwise shared tabs drive its original MapList.

All 34 host regressions passed, with focused checks repeated after the final Lua
cleanup. Restoring the old bypass makes the provider-row regression fail. The
new companion Lua was subsequently uploaded and verified byte-for-byte against
source commit `8f9e31d`. No native SPRX changes or new build were needed.

The user confirmed that duplicate rows are fixed. The latest companion Lua
also preserves provider styling and meaningful compatibility metadata: full
builder input, placeholder-aware row ranking, original colored labels and
original warning/check callbacks. No provider names, palettes or compatibility
tables are encoded in the implementation. The new regression fails before the
fix and passes afterward, including incompatible status zero and conflicting
style/status protection. Existing deduplication and reopen checks still pass.

Next: test `Lua/ui_scripts/mapselect.lua` with the existing dev.49 plugin. Check
colored names and the provider's compatibility warnings while confirming one
row per map under Customs, selection, repeat opens and refreshes. The MapSelect trace reports the input
and final row counts. Separately, resolve the Reaper nil operand from matching
bytecode/debug evidence and review post-unload globals/module ownership. Do not
assume invalid GSC opcode is the first cause: its record precedes the first
printed watchdog warning but lies inside the warning's reported no-progress
interval. Existing GPU findings remain in [development status](docs/DEVELOPMENT.md).

## Resume from Chat

Use the connected GitHub repository `Zorian1337/PS4-BO3-Customs`, branch `testing/dev35-debug-build`.
Read this file and the linked development status, then fetch only relevant files.
Chat can review or plan from those sources; local files, console FTP, kernel
output and native tools require an available local Work environment. Never claim
those checks ran when that access is unavailable.

Suggested prompt:

> Continue the BO3-Customs SPRX/Lua work from RESUME.md and AGENTS.md on testing/dev35-debug-build.
> Continue Issue #23 using docs/INVESTIGATION-23.md. Inspect
> the current status/diff and upstream main first. Keep current features,
> document evidence and alternative fixes, and validate targeted changes. Do not
> publish private material or create a plugin build/release without approval.

Related Chat and Work chats can share a project. See the official
[projects and chats guidance](https://learn.chatgpt.com/docs/projects).

## Resume locally

Run `RESUME_WORK.cmd`, or `python tools/project_session.py status`, for a compact
source/status summary. Run `CHECK_SOURCE.cmd` for the configured host checks.
These commands make no model/API calls and never build, upload or release a SPRX.
Local device/tool paths belong in ignored `.local/` settings, not this file.

Update this file and the status record when evidence changes, including what was
actually tested, remaining uncertainty and the single next useful task. Keep
version change notes with an approved GitHub release, not loose per-build files.

## CI coverage correction

The pool-growth fixture was not included in the focused SPRX diagnostics
workflow used for pull requests. It is now explicitly run by that workflow,
so the binary-search lookup contract and existing allocation regressions are
checked before merge. The updated SPRX diagnostics workflow passed on final source commit `fdcc08e`; the pool-growth and pool-out concurrency fixtures ran successfully. Focused mod-stack, frontend-reload, script-priority and import-lifetime workflows also passed. No PS4 native build or console test was performed for this branch.
## Pool-out diagnostic concurrency fix (2026-11-17)

Source review confirmed that T7Log_PoolOut() is called from LinkXAsset_h(),
which can run concurrently on database workers, but its static per-type
once-only told[] latch was a plain bool array. Concurrent check/set was a
data race. It now uses std::atomic<bool> and exchange() so only one worker
claims each diagnostic. Added a production-function concurrency stress
fixture and registered it in both PR diagnostics and the full host runner.
CI for the updated test is pending; this is a diagnostic race fix, not proof
of a pool allocator failure or of the reported map crash.

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


## Native allocator/GPU/mode/map/target audit — 2026-11-18

A consolidated engineering audit is now recorded in [docs/NATIVE-ALLOCATOR-GPU-MODE-AUDIT-2026-11-18.md](docs/NATIVE-ALLOCATOR-GPU-MODE-AUDIT-2026-11-18.md). New Ghidra evidence identifies the native XAssetEntry allocation path at 0x8583b0, transfer path at 0x8587b0, type cleanup at 0x858cb0, the 152,576-bucket hash table, 32-byte entry stride, shared free-list head and multiple distinct 32-bit link fields. This materially narrows issue #30, but the exact executable fingerprint, complete index-consumer call graph, free-list mutation contexts and lock contract remain unverified; PR #40 stays arithmetic-only and no reserve allocator hook was added.

The audit records why issue #28's GPU fault remains unattributed, why issues #1/#2 still need native zone ownership and clientfield table comparison, what exact DS4C/Blood Run evidence is missing for issues #23/#31, and why PR #43 still needs an explicitly authorized PS4 target build. No speculative GPU lifetime, transition, script or allocator changes were made. No target build, console test, merge, upload or release was performed. FFPorter remains out of scope.


## PR #40 safety review correction — 2026-11-18

A live-branch review found that PR #40 had briefly grown beyond its stated arithmetic-only scope: it added a production reserve-page publisher called from LinkXAsset_h. That implementation treated the shared state value at 0x0CF60BB4 as proof that the current worker owned the native registry lock. The saved FUN_008583b0 decompilation shows the global free-list pop occurs before a later acquisition of that lock for a separate per-type fallback traversal. A shared lock-state value does not establish current-thread ownership, and the link-stage hook is not the recovered allocator boundary. The new reserve discovery/publication state was also ordinary non-atomic state reached from concurrent link workers.

The production reserve function, constants, include and LinkXAsset_h call were removed from PR #40. Its SPRX/t7_maps.cpp now matches main byte-for-byte. The pure arithmetic header and host tests remain, with comments explicitly describing the unsigned-index interpretation as a candidate model rather than a verified all-consumer ABI. PR #40's body and design note were corrected to state that it does not fix exhaustion. This is a safety rollback, not a runtime fix; do not reintroduce reserve publication until allocator timing, lock ownership, every index consumer and concurrent free/reuse behavior are proven.


## Native index cross-reference count and host validation — 2026-11-18

The saved Ghidra analysis search returned 41 references to the entry base DAT_0587E710, 42 references to the bucket-head array DAT_057E9710, 41 references to the primary next-link field at DAT_0587E724 (entry offset 0x14), 25 references to the secondary link at DAT_0587E72C (entry offset 0x1C), and 12 references to the global free-list head DAT_05d26718. These are textual cross-reference counts in the saved decompilation, not a deduplicated count of unique functions; they establish that the consumer audit is broader than the SPRX's single public walker.

After removal of the unverified reserve publisher, PR #40 head 719b78ba5fcd88b13701f82b4af187e5ca6d30bd passed both SPRX diagnostics (run 44235584368) and the project-session guard (run 44235584360). The guard covers the registered host regression inventory. These checks validate the arithmetic helper and repository policy only; they do not execute the retail allocator, prove the native lock contract, or build the PS4 target. PR #40 remains draft and does not fix issue #30.


## Recovered dev.69 log evidence for the reserve feature — 2026-11-18

A saved Library file, log(8).txt, is explicitly labelled BO3-Customs-v4.00.1-dev.69-DEBUG (debug build timestamp Nov 7 2026). It contains the startup line "[Pools] shared asset-entry reserve ready (bounded 16 MiB)" at approximately 00:02.270. This confirms that a reserve-related initialization path existed in that dev.69 candidate; it does not establish that a page was actually mapped or linked into the native free list. The log contains no per-page "[XAsset] reserve added" record, no reserve entry count/index range, and no native allocator/free-list state dump.

Later in that same excerpt, the custom zm_ccube level request records a GPU checkpoint with assets linked=148,929. That is an SPRX linked-asset counter, not a proven sample of the native global XAssetEntry active count, and it is below the reported 152,576 registry capacity. The excerpt ends shortly after the level begins loading; it does not show a successful complete load, a reserve allocation event, or the eventual outcome. An earlier EXE_SERVERKILLED line at 01:52.785 occurs before the zm_ccube load request and reports zero script runtime errors at that shutdown; it must not be attributed to XAsset exhaustion or the GPU protection fault from issue #28.

The first trace line also labels the process trace as "custom-surfaces-only; native-GPU-allocator-and-submissions-unknown", so this log does not provide the missing native GPU allocation/submission ownership. Treat this file as a valuable historical candidate log, not proof that dev.69's reserve implementation fixed issue #30 or that the GPU fault was diagnosed. The dev.67 artifact/hash in issue #30 remains a separate candidate record; its exact source patch and runtime behavior still need provenance recovery.


## Additional native netfield lead for the clientfield investigation — 2026-11-18

The saved executable decompilation contains a large BG_InitClientFields-related path. In the inspected region it iterates a fixed 0x75 (117) entry name table rooted at PTR_s_unarchivedState_initialPlayersCo_015e8890 and matches names such as archivedState.worldFields[0] through archivedState.worldFields[25]. For each matched field it reads an associated 32-bit value from UNK_015e8898 + index*0x18; unmatched names call the diagnostic "Netfield %s not found during BG_InitClientFields." This is a concrete native network-field initialization lead that can help locate the surrounding registry and its mapping data.

It is **not yet proven to be the same registry** as the GSC Clientfield Mismatch reported by issue #2. The current inspection did not establish the server/client registration table layout, the mismatch comparison function, or the actual differing field. Do not equate the 117-name netfield map with script clientfield registrations or change its contents based on this observation. Next step is to identify the containing native function and its callers, then trace the actual mismatch diagnostic's call path on the same executable fingerprint.


## Separate dev.67 private reserve candidate — provenance and validation boundary

Issue #30's original body records a separate private dev.67 candidate that must not be conflated with the later PR #40 LinkXAsset_h implementation reviewed and removed above. The issue reports that dev.67 used a signature-gated allocator-boundary refill, 1 MiB anonymous pages, a 16 MiB cap, unchanged original entry addresses/hash modulus/native free/unload behavior, positive signed-32 index round-trips, and fail-closed mapping/fingerprint checks. It reports 65 relevant fingerprints, production-body ASan/UBSan checks, a private 10,000-node fixture executing matching original allocator/free-list fragments, Debug/Release PS4 syntax checks, a 14-unit Debug build, four payload-segment validation, malformed-container rejection, and local artifact SHA-256 68e7ef4049e1993b61a7104767e5baed24c72663ad6bc8a73ca3475b4f897e76 for BO3-Customs-dev67-DEBUG.sprx (487,808 bytes).

These are recorded claims from the issue's local-candidate report; the source tree, matching ELF/OELF, private fixture, fingerprint table, and build/validation outputs are described as archived locally but were not found in the currently accessible GitHub branch or Library search. Therefore they have not been independently reproduced or reviewed in this session. The issue itself states the original bulk stack still needs a fresh-process console reproduction. Delivery used FTP with only remote SIZE queried; no remote readback was performed. The exact candidate's implementation and provenance should be recovered from that local archive before any attempt to reintroduce it into current main.

The dev.69 log(8).txt is a different artifact: it records only a startup "shared asset-entry reserve ready" line and later 148,929 SPRX-linked assets before the excerpt ends at map-load start. It does not prove that the dev.67 allocator fix was present or that a reserve page was consumed. The PR #40 runtime hook that was removed is also a separate, unsafe reconstruction; it must not be presented as the dev.67 candidate or as a review of that private source.

The dev.67 build report does not satisfy PR #43's target-compatibility gate: it predates the FolderScanStatus correction and is not a target build of the corrected PR #43 head. A fresh PS4 target build is still needed after that source correction, followed by console verification where relevant.


## Native allocator audit follow-up — 2026-11-18

The native allocator deep pass is preserved in [docs/NATIVE-ALLOCATOR-GPU-MODE-AUDIT-2026-11-18.md](docs/NATIVE-ALLOCATOR-GPU-MODE-AUDIT-2026-11-18.md). New exact operation-order finding: FUN_008583b0 (0x8583b0) pops the shared free-list head DAT_05d26718 and updates allocation counters before it later acquires DAT_0CF60BB4 for a per-type fallback bucket traversal. That later lock is not evidence of ownership of the global free-list and must not be reused for reserve publication. Native entry links are distinct: first-word pointer for shared free-list, 32-bit index at +0x14 for the bucket chain, and 32-bit index at +0x1C for secondary/override chains; entries are 0x20 bytes and bucket heads are separate (0x25400). The Ghidra analysis profile hash is not an executable fingerprint.

The audit document was extended with this operation order and exact remaining gates. Status comments were posted to issues #30, #28, #1, #2, #20, #23 and #31. No production allocator/GPU/transition/GSC change was made because the missing contracts or source evidence are still essential to avoid introducing memory corruption or masking native failures. PR #40 remains arithmetic-only; PR #41 remains bootstrap-test-only. Existing PR #43 compiler correction still needs an explicitly approved PS4 target build. FFPorter remains out of scope.


## Target-build workflow and current PR handoff — 2026-11-18

The repository's .github/workflows/bo3-build.yml runs on pushes to main and supports workflow_dispatch. Its SPRX job installs clang-18/lld-18, invokes .github/scripts/build_sprx.py --package, validates the native module/container, and uploads the SPRX plus native build evidence. It is not configured as a pull_request build. The GitHub connector available in this session exposes workflow-run inspection but no workflow-dispatch action. Therefore the corrected target compile can be exercised either by an explicitly approved merge/push to main (which triggers the workflow) or by the repository owner manually dispatching BO3 Auto Build in GitHub Actions. No target build was started.

The original PR #43 is now closed as superseded, not merged. Its clean replacement is PR #48, based on current main with 3 commits ahead and 0 behind; all five PR workflows passed on head 1144635efc6af64904efa1e27671598a179b26d9 (SPRX diagnostics 44237212529, project-session guard 44237212480, mod stack transaction 44237212537, script priority context 44237213746, frontend reload state 44237212518). PR #48 is ready for review and remains unmerged pending the target-build authorization.

PR #40 remains draft research groundwork only. Its production reserve hook was removed; SPRX/t7_maps.cpp matches main byte-for-byte. Its latest safe head passed SPRX diagnostics and project-session guard, but the tests validate helper arithmetic and repository policy, not the native allocator. The private dev.67 candidate described in issue #30 remains separate and unreviewed from its local source archive.
