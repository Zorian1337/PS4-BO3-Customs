# Current repository status (2026-11-17)

- Active base: `main`; PR #36 is merged as `10169fc1100eb88813c28bffdf0f2ae32c5a6df6`.
- Open issues: 10. None is closed; each still has a source, provenance, reproduction, complete-package, or console-validation requirement.
- Open PRs: #37, #38, #39, #40, #41, #42 and #43. PRs #37/#38 are earlier standalone versions of combined PR #39; do not merge them independently.
- PR #39 (`recovery/issue-driven-dev65-dev69`) implements the dev.65 UI guards and dev.69 bounded stream diagnostics. Its source head `481d4d4952952f07a52c60e6605197b11474473d` passed all six workflows; the project-session guard reports 47 host regression programs with zero failures. The custom-image path now has a 1,024-entry process-lifetime no-eviction tombstone registry, fail-closed capacity handling, stock-slot reuse passthrough and ASan/UBSan callback-after-record-reuse coverage. A docs/workflow-summary-only follow-up head `2f03c992144aeb2f88f1364346b4ddbfe36d4ae6` is queued for its project-session guard. PR remains draft; no target build or console verification.
- PR #42 (`fix/lua-asset-name-bounds`) is ready for review. Source-policy audit, publication guard, all 43 host regressions, SPRX diagnostics and script-log checks passed on `bfc2673bd9e5acd816408fca4fc7681fe172380c`. It bounds game-owned rawfile-name reads and routes missing-config logging through a safe copy. It is not merged; no target build or console test was performed.
- PR #40 (`recovery/xasset-entry-index-safety`) is arithmetic groundwork only; native XAssetEntry allocator/free-list ABI, all index consumers and synchronization remain unverified. The public `ClearAssetsInUse()` consumer reads chain values as `uint32_t`; the proposed positive signed-32 subrange is conservative but does not prove every native consumer. Keep draft.
- PR #41 (`investigation/blood-run-bootstrap-regression`) tests the existing absent-only `Mods_IsUsingUsermap` fallback; it does not repair Blood Run GSC errors or gameplay/pause stalls. Keep draft.
- The automatic BO3 Auto Build run #75 (triggered by a documentation push to `main`, not an explicit build request) reached the PS4 compile and failed in `SPRX/t7_maps.cpp`: a literal `\\n` kept `FolderScanStatus` inside the preceding `//` comment. PR #43 fixes the declaration and adds a host source guard. The fix has not been target-built; further compiler errors may remain.
- No manual SPRX build, upload, release, or PS4/PS5 console test was performed. Do not start another build without explicit approval.
- Lua retention remains a critical acceptance area: preserve original included Lua behavior and ensure users can disable mods and restore non-mod state without crashes, resets, or stale bytecode. Neither PR #39 nor #42 changes bytecode retention.

Read `AGENTS.md`, then this file, the dated stability roadmap, and only the relevant issue/source sections. Current priorities and PR boundaries are recorded in the roadmap.

---



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