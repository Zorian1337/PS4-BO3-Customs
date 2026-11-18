# PS4 BO3-Customs stability roadmap

Updated: 2026-11-17

The goal is stable custom-map loading and long sessions on constrained PS4
memory, not maximum asset capacity. Every memory increase must be justified by
a reproducible exhaustion record and bounded by a measured budget.

## P0 — Map catalog integrity and map-load diagnostics (PR #36; merged)

Branch: `diagnostics/map-load-phase-timing`
PR: https://github.com/Zorian1337/PS4-BO3-Customs/pull/36

- [x] Replace count-only directory enumeration with structured scan outcomes
  for open/read/stat/record/name/capacity/close failures.
- [x] Reject incomplete catalog candidates instead of publishing partial maps,
  mods, movies, or generated map Lua.
- [x] Preflight and recheck storage roots; retain the previous catalog if a
  populated drive disappears or becomes inaccessible during refresh.
- [x] Snapshot and restore catalog arrays, counters, generated Lua, mod
  description ownership, and dirty state on refresh failure.
- [x] Add production-function host coverage for directory parsing, unknown
  dirent types, storage-root loss, Lua output bounds, and rollback ownership.
- [x] Add FF/FD preflight, package-open timing, and native LoadLevelZones timing
  to DEBUG diagnostics.
- [x] Re-run PR CI after the follow-up correction to legacy mod-stack scanner
  call sites and the new scanner-arity regression.
- [x] Complete full-diff review and squash-merge PR #36 to `main` (`10169fc1100eb88813c28bffdf0f2ae32c5a6df6`).
- [ ] Run the PS4 target build only after explicit approval, then validate on
  console. The earlier PR CI runs were host regressions and do not constitute
  a native build or runtime test.

The review caught three mod-stack call sites still using the old four-argument
ListFolder interface after the scanner changed to a five-argument structured
result. Those call sites now consume FolderScanResult, report failures, and
roll back additions from a failed folder scan. The regression checks every
ListFolder invocation for the correct argument count. PR #36 was squash-merged
after the full diff review; its final head `6c757633504d048183a119328872b96e058741c2`
passed all five required workflows: SPRX diagnostics (run 417), project-session
guard (run 160), frontend reload (run 236), mod-stack transaction (run 235),
and script-priority (run 241). The full-range publication audit, publication-
guard tests, and complete registered host regression inventory passed on the
preceding source/test head. These are host checks only.

The `zm_ccube` crash remains unconfirmed. Both FF and FD opened in the supplied
excerpt; the first fatal record was not present. Do not treat catalog integrity
or added timing as a fix for that crash.

## P1 — Buried backend crash and dev.69 source provenance

Issue #33 documents a dev.68 PS5 SIGSEGV on `2_Backend` while loading
`zm_buried`, with RIP `0xFA2A98` and read address `0x27`. The kernel stack
is incomplete; two GSC errors are confirmed but not proven causal.

The issue describes a dev.69 DEBUG trace event named
`stream-block-rejected`, but the inspected public `main` and PR #36 source
do not contain that event. The candidate's FTP SIZE response matched the OELF
container size rather than the local SPRX size, and remote bytes were not read
back. The dev.69 artifact is therefore not verified as a build of the public
source.

- [ ] Recover and review the exact dev.69 source patch; publish it only after
  production-body tests cover pass-through, both rejection branches and the
  16-event cap.
- [ ] Reproduce Buried in a fresh process without mods and preserve the raw
  kernel report plus the preceding 30 seconds.
- [ ] Correlate bounded stream-guard events with the first native fault. A
  matching executable fingerprint or complete fault report is still needed
  to resolve RIP `0xFA2A98`.
- [ ] Verify the exact candidate artifact by reading it back before treating
  an FTP transfer receipt or SIZE response as artifact identity.

Do not infer causality from the GSC errors, missing-resource fallbacks, or
absence of a trace event. Do not rebuild, upload, release, or claim the crash
fixed without explicit approval and matching evidence.

## P0 — Landed source hardening; CI verified

- [x] Replace per-asset linear pool-allowlist lookup with binary search on the
  sorted immutable table (review branch; focused PR CI passed; not merged).
- [x] Test strict allowlist ordering, lookup of every registered type, and
  misses below, between, and above registered types.
- [x] Add the pool-growth fixture to pull-request SPRX diagnostics.
- [x] Make the per-type pool-out diagnostic latch atomic for concurrent asset-link workers.
- [x] Add a concurrent production-function regression to PR diagnostics and the full host test inventory.
- [x] Confirm the updated SPRX diagnostics workflow passed on final source commit `fdcc08e`, including both pool fixtures.
- [x] Confirm the follow-up diagnostics run `44170446291` passed host-runner inventory validation and the same pool/Lua checks.
- [x] Confirm focused mod-stack, frontend-reload, script-priority and import-lifetime workflows passed.

- [x] Exclude COM World and Game World from automatic pool growth.
- [x] Exclude the one-entry sound-driver, bullet-penetration, and
  location-damage pools from automatic growth pending proof of safe multi-entry
  semantics.
- [x] Regression-test the fixed-pool allowlist and the native singleton flag.
- [x] Bound rawfile Lua ownership name reads.
- [x] Bound script-name reads and correct output-capacity validation.
- [x] Confirm the GitHub diagnostics workflow passes.
- [x] Confirm the PS4 GoldHEN Debug build and native artifact validation pass.
- [ ] Compare pool-enabled and pool-restricted builds on console before
  declaring the pool policy a performance or stability win.

## P1 — Prove native allocator concurrency contract

- [ ] Locate and validate the PS4 DB_AssetPoolAlloc address, signature,
  call sites, and thread context for the supported BO3 build.
- [ ] Determine whether the native allocator already serializes asset-pool
  free-list mutations across DB workers.
- [ ] Compare that synchronization with our append-only pool-growth lock.
- [ ] Add a host concurrency model and target-side diagnostic before changing
  allocator hooks.
- [ ] Only implement a shared allocator/growth lock if the call graph proves
  the lock is re-entrant-safe and does not serialize unrelated engine work.
- [ ] Separate pool exhaustion observation from confirmed allocator failure;
  the current LinkXAsset hook observes an empty free list but does not capture
  the native allocator's failed-allocation return.

## P1 — Diagnose map streaming and lighting dependencies

- [ ] Capture a complete zm_ccube load trace, including the first fatal
  record or exception PC and the preceding 30 seconds.
- [ ] Track the identity and state transitions of the missing lighting blob.
- [ ] Distinguish a delayed resource from a permanently unresolved dependency.
- [ ] Compare FF/FD/XPAK dependencies against a known-good map.
- [ ] Never mark a resource resident or skip a required dependency to hide a
  load failure.

## P2 — Reduce persistent memory pressure with evidence

- [ ] Record per-pool baseline, current limit, allocated count, growth bytes,
  and high-water mark across repeated map loads.
- [ ] Determine whether asset pools retain map-specific entries after unload.
- [ ] Identify plugin-owned buffers and caches that can be safely released or
  reused between maps.
- [ ] Measure the actual memory impact of the 64 MiB growth ceiling before
  changing it.
- [ ] Keep image, world, and XModelMesh restrictions unless native references
  and fixed-size assumptions are disproven.

## P2 — Improve map-load observability

- [ ] Emit a compact per-zone load summary with elapsed time and asset counts.
- [ ] Add bounded stream-state history for image, mesh, lighting, and sound.
- [ ] Record pool-out events with type, limit, entry size, singleton state,
  free-list state, and the last growth attempt.
- [ ] Preserve logs across crashes and include build/source identifiers.
- [ ] Keep diagnostics bounded so instrumentation cannot become a new memory
  or frame-time problem.

## P3 — Longer-term architectural improvements

- [ ] Build immutable/double-buffered map catalogs to remove long writer
  sections from the game-thread read path.
- [ ] Audit all zone unload/reload ownership and stale pointer lifetimes.
- [ ] Evaluate asset deduplication and converter-side dependency pruning before
  increasing runtime pool sizes.
- [ ] Revisit script bytecode and rawfile retention only with before/after
  memory measurements and guaranteed mod-disable/revert behavior.



## Current PR review and source recovery (2026-11-17)

Five PRs are open; none is approved for merge by this review.

| PR | Branch / scope | CI and source review | Next gate |
|---|---|---|---|
| [#43 FolderScanStatus target compile fix](https://github.com/Zorian1337/PS4-BO3-Customs/pull/43) | Restore enum declaration swallowed by a literal escaped newline; add source-line regression guard | SPRX diagnostics, source-policy audit and publication guards pass; all 42 registered host regressions pass on source head `e0e1af00e4d51c41250d13ff9cfa4fa42d59702f` | Keep draft; no second target build without explicit approval; additional compile errors may remain |
| [#42 Lua rawfile asset-name bounds](https://github.com/Zorian1337/PS4-BO3-Customs/pull/42) | Bounded chunk reads before Lua classification and safe missing-config logging; native lookup/retention behavior unchanged | Source-policy audit, publication guard, 43 host regressions, SPRX diagnostics and script-log checks pass on `bfc2673bd9e5acd816408fca4fc7681fe172380c` | Ready for review; no target build or console test |
| [#41 Blood Run bootstrap regression](https://github.com/Zorian1337/PS4-BO3-Customs/pull/41) | Production-Lua test for the existing absent-only `Mods_IsUsingUsermap` fallback | Diagnostics and project-session checks pass on `eb7344720765748a8bad335ccb2eb09cdbfc41b2`; no GSC behavior changed | Keep open; obtain matching Blood Run GSC source and a clean-start console capture for gameplay/pause failures |
| [#40 XAssetEntry index groundwork](https://github.com/Zorian1337/PS4-BO3-Customs/pull/40) | Checked encode/decode and reserve-page index arithmetic only | Source-policy and diagnostics checks pass on `02e710f85a25d04ccad3f54fd07deffe1d4f2561); no native hook or mapping | Keep draft; resolve signed/unsigned native index semantics and prove allocator/free-list ABI, all consumers, thread synchronization and supported build fingerprint |
| [#39 combined UI/image and stream recovery](https://github.com/Zorian1337/PS4-BO3-Customs/pull/39) | Recreates dev.65 transition/image guards and dev.69 bounded stream diagnostics | Source head `481d4d4952952f07a52c60e6605197b11474473d` passes six workflows and 47 host regressions. A 1,024-entry no-eviction tombstone registry now preserves retired addresses; capacity exhaustion retains active ownership and refuses replacement. Stock-slot reuse is distinguished from freed/different custom slots; callback-after-record-reuse regression passes | Keep draft; latest docs/workflow-summary-only head is awaiting project-session guard. No target build or console test |
| [#38 standalone UI/image guards](https://github.com/Zorian1337/PS4-BO3-Customs/pull/38) | Earlier standalone implementation of part of #39 | Superseded by combined #39; not independently accepted | Do not merge independently |
| [#37 standalone stream diagnostics](https://github.com/Zorian1337/PS4-BO3-Customs/pull/37) | Earlier standalone implementation of part of #39 | Superseded by combined #39; not independently accepted | Do not merge independently |

### Issue-specific boundaries

- **#30 XAssetEntry exhaustion:** the dev.67 reserve-page runtime correction is not present in public `main`. PR #40 is arithmetic groundwork, not an allocator fix. The observed native chain consumer uses `uint32_t`; the positive signed-32 assumption needs proof before any production integration.
- **#29 rapid X/back:** the tester reported the dev.65 symptom improved. PR #39 now preserves retired custom-image addresses and tests delayed callbacks after record reuse, including capacity exhaustion and stock-slot reuse. Keep the issue open until the latest docs-only guard passes and a fresh console reproduction is recorded.
- **#33 Buried backend crash:** PR #39 restores bounded rejection diagnostics only. It does not fix RIP `0xFA2A98`; reproduce without mods and correlate the first fault with a matching executable.
- **#31 Blood Run:** PR #41 validates only the missing-global fallback. Repeated GSC invalid-value errors, server shutdown, frozen controls and pause behavior remain unresolved.
- **Lua retention / disable-mod recovery:** any future changes must prove first load, unload, reload, overlapping stack changes, frontend reconstruction, and restoration of original included Lua bytecode. Never trade away the user's ability to disable mods or recover without a crash/reset.

No native SPRX build, upload, release, or console test was performed for these PRs. Host CI is not target ABI or runtime proof. Preserve the current build-approval boundary in `AGENTS.md`.

## Other open workstreams — issue triage

These tracks are separate from PR #36. Keep their evidence and acceptance
criteria independent; do not combine them into a broad stability claim.

| Issue | Public-source status | Next safe step |
|---|---|---|
| [#32 FFPorter embedded XModels / texture-combo aliases](https://github.com/Zorian1337/PS4-BO3-Customs/issues/32) | Converter implementation is present in `main`; focused conversion reported 0 unresolved fixups, but sound, movies and `acts` checks were disabled and PS4 loading was not tested. | Complete a full package conversion with all content classes enabled, validate every zone/language link, then test on console. |
| [#31 Blood Run](https://github.com/Zorian1337/PS4-BO3-Customs/issues/31) | The `Mods_IsUsingUsermap` Lua fallback is present in `main`; it has not been built or console-verified. Mod GSC failures and later server/pause stall remain unresolved. | Build only with approval; compare a clean process with the mod selected before first map load; obtain matching GSC source for the reported offsets. |
| [#30 XAssetEntry registry exhaustion](https://github.com/Zorian1337/PS4-BO3-Customs/issues/30) | The dev.67 reserve-page correction is documented as a local candidate, not present in inspected public `main`. Candidate transfer was acknowledged but remote bytes were not read back. | Recover/review the exact source patch, add reproducible tests, then fresh-process console-test the nine-mod case. Preserve native entries and fatal behavior. |
| [#29 rapid menu X/back](https://github.com/Zorian1337/PS4-BO3-Customs/issues/29) | Tester reports dev.65 stopped the rapid X/circle crash; the corresponding source changes are documented as local/uncommitted. | Reconcile the exact patch before shipping. Keep the later multi-mod Database-thread crash separate. |
| [#28 GPU protection fault](https://github.com/Zorian1337/PS4-BO3-Customs/issues/28) | Diagnostic candidate and source corrections are documented as local/uncommitted; native GPU allocation/free/submission ownership is not fully traced. | Recover the exact source and correlate a fresh capture. Do not change GPU resource lifetimes or claim a fix from numerical overlap alone. |
| [#23 Seven-Eleven multi-mod hang](https://github.com/Zorian1337/PS4-BO3-Customs/issues/23) | Investigation only. The invalid opcode is observed after the stall, not proven to cause it. | Compare no-mod, each mod alone, then both; inspect script identity/ownership and asset pressure without assuming the linked-asset count is causal. |
| [#20 automatic host activation BG-cache mismatch](https://github.com/Zorian1337/PS4-BO3-Customs/issues/20) | Checksum observation is available; the mismatch is not fixed. | Compare host/client checksum, transition timing, exact mod bytes and order for automatic versus manual activation. Never bypass native validation. |
| [#2 clientfield/script context diagnostics](https://github.com/Zorian1337/PS4-BO3-Customs/issues/2) | Error-budget and script-owner portions are implemented; native clientfield registry differences and validated caller/entity context remain missing. | Add guarded read-only registry-difference output only after validating the PS4 layout; retain native error handling. |
| [#1 ZM-to-MP transition diagnostics](https://github.com/Zorian1337/PS4-BO3-Customs/issues/1) | Transition snapshots are implemented; the failing mode transition has not been captured with the needed ownership/Lua-generation evidence. | Capture a fresh ZM-to-MP and MP-to-ZM reproduction and compare selected/loaded stacks, mode-common ownership and native completion. |

## Exit criteria

A stability change is not considered complete solely because it compiles.
For each P0/P1 change require:

1. host regression pass;
2. PS4 target build and native artifact validation;
3. repeated cold and warm custom-map loads;
4. map transition and return-to-menu tests;
5. a long session with memory/pool high-water observations;
6. no regressions to disabling mods or restoring original Lua content.

Console tests remain pending until a tester supplies the corresponding logs.


## PR #42 — Lua rawfile name bounds (2026-11-17)

The rawfile lookup hook previously validated only 16 bytes before scanning up to 191 bytes for a terminator, and the missing-config diagnostic formatted the original game-owned pointer. PR #42 adds validated chunk copying, rejects unterminated/unreadable names for plugin classification, and logs from the copied buffer or a placeholder. Native lookup arguments/results and Lua bytecode retention are unchanged. Its source-policy audit, publication guard, 43 host regressions, SPRX diagnostics and script-log checks pass on `bfc2673bd9e5acd816408fca4fc7681fe172380c`. It is ready for review, not merged; no target build or console test.


## P0 — Restore FolderScanStatus target declaration (2026-11-18)

Automatic BO3 Auto Build run #75 attempted the PS4 cross-compile after a documentation push to `main` and failed in `SPRX/t7_maps.cpp`. A literal escaped newline after `// libkernel ENOENT` swallowed the `FolderScanStatus` enum, producing an `expected unqualified-id` error and undeclared-type errors. The compiler stopped at its error limit; additional target errors may remain. Artifact upload and native-module inspection were skipped.

PR #43 (`fix/folder-scan-status-declaration`) replaces the literal escape with a real newline and adds a guard to `map_catalog_safety_checks.py`; the old test extracted the enum token from the comment, masking the full translation-unit failure. Host/source-policy checks are pending. No second target build is authorized or claimed. See the investigation in PR #43.


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
