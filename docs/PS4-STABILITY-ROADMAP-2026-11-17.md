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

## GitHub cleanup audit (2026-11-17)\n\nReviewed all 10 open issues and every open PR in `Zorian1337/PS4-BO3-Customs`.\nPR #36 is now merged; it was the only open PR. No issue was closed because\neach remaining issue still has an unresolved source, reproduction, package,\nor console-validation requirement. Issue #32 received a status comment\nclarifying that its focused converter checks do not replace a complete package\nconversion with sound, movies and `acts` enabled plus a console load. The\nrapid X/back symptom in #29 was reported fixed on dev.65, but the corresponding\nsource correction is still documented as local/uncommitted, so it is not yet\nclosed as a repository fix.\n\n## Other open workstreams — issue triage

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


## Active follow-up — Issue #30 shared XAssetEntry registry (2026-11-17)

**Problem:** the dev.66 nine-mod activation exhausted the shared 152,576-entry XAssetEntry registry and the Database thread aborted. Per-type asset-pool growth does not enlarge this separate registry.

**Proposed fix:** preserve the original table and entry addresses; append bounded reserve pages only at the verified native allocator boundary when the original free list is empty. Before publication, validate the full mapping, 32-byte address residue, every positive signed-32-bit chain index round-trip, native read/write span, reserve cap, and exact allocator/free-list ABI. On any mapping or contract failure, do not publish the page and preserve native fatal behavior. Never relocate the live table, overwrite adjacent globals, drop assets, or bypass native validation.

**Work started on** `recovery/xasset-entry-index-safety`:
- Added `SPRX/xasset_reserve_index.hpp`, pure checked conversion and whole-page first/last-index validation for positive signed-32-bit native indices.
- Added `SPRX/tests/xasset_reserve_index_tests.cpp` covering all 32 address residues, sparse addresses above 4 GiB, the signed-index boundary, page ranges crossing that boundary, misalignment, zero stride, address overflow and unchanged outputs on rejection.
- Added [the detailed issue/solution/acceptance note](XASSET-RESERVE-INDEX-SAFETY.md).

This is arithmetic groundwork only. It does not map or publish reserve memory, validate the game's actual allocator ABI, or fix the registry exhaustion. The new C++ test is auto-discovered by `.github/scripts/run_host_checks.py`; CI must pass before this work is considered reviewed. The exact native allocator entry point, table/free-list consumers, instruction fingerprints and supported build identity remain prerequisites for the runtime correction.

**Acceptance criteria:** production-body tests for original fast path, refill, map failure, every residue/index limit, reuse/free, reserve cap and full native ABI forwarding; matching PS4 target build and artifact validation; fresh-process nine-mod console reproduction; no regressions to single-mod loading or unload.

## Parallel source recovery — PR #39

[PR #39](https://github.com/Zorian1337/PS4-BO3-Customs/pull/39) continues to carry the issue-driven dev.65 UI/image-lifetime guards and dev.69 stream rejection diagnostics. Its additional 32-worker diagnostic-cap stress test and roadmap/RESUME updates are on that separate draft branch. All six GitHub Actions workflows now pass on head `84ecf1917ad6e3930f7643e473076a9ce3f35059`: SPRX diagnostics #517, project-session guard #294, frontend reload #293, mod-stack transaction #292, script priority #298 and in-game script log #89. The project guard completed the publication audit and full host regression inventory; diagnostics passed including the concurrent stream-cap test. These are host/CI results only. Keep PR #39 separate from the #30 allocator work until both branches have passed their own review and CI.


## XAssetEntry registry follow-up (2026-11-18)

- [x] Verify the arithmetic helper and whole-page index bounds with host tests.
- [x] Add checked index decoding and rejection tests for zero/negative indices and pointer overflow.
- [x] Add residue-preserving selection of a full reserve page inside an mmap span, including insufficient-span rejection.
- [x] Audit published t7_maps.cpp: LinkXAsset_h is a link-stage hook, not the shared XAssetEntry allocator.
- [x] Record ClearAssetsInUse() as the explicit public SPRX chain consumer; it reads bucket/next values as uint32_t and uses a 32-byte entry stride.
- [ ] Verify whether the dev.67 positive signed-32 index rule is enforced by every native consumer; current public source does not prove it.
- [ ] Recover the native allocator/free/reuse functions, complete entry ABI, every native index consumer, synchronization contract, and independent build fingerprint.
- [ ] Implement reserve-page mapping/publication only after the native contract is proven; test mapping failure, cleanup, cap, reuse, and original fast-path ABI.
- [ ] Reproduce the nine-mod dev.66 exhaustion case in a fresh process with the matching build and verify no regression after the runtime fix.

The helper remains arithmetic-only and is not wired into production. Latest PR head 91cc1e6 passed SPRX diagnostics run 44208924179 and project-session guard run 44208924265; the full registered host inventory reports 43 regression programs with zero failures, including the new encode/decode/page-selection fixture. No PS4 target build, SPRX upload, or console test was performed.
