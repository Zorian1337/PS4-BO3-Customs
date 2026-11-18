# Native allocator, GPU, transition and target-build audit

Updated: 2026-11-18

This note consolidates the latest source and saved executable-analysis review for issues #1, #2, #20, #23, #28, #30 and #31, plus PRs #39, #40 and #43. It separates evidence from hypotheses and records what remains gated on a matching executable, source package, target build or console capture.

## 1. XAssetEntry registry exhaustion — issue #30 / PR #40

### Confirmed failure
A dev.66 bulk activation with nine selected mods exhausted the shared XAssetEntry registry and emitted the native diagnostic "Could not allocate asset - increase XASSET_ENTRY_POOL_SIZE", followed by a Database-thread abort. The issue records 152,576 entries. Per-type asset-pool growth is a different allocator and cannot enlarge this registry.

### New native-code observations from the saved Ghidra analysis
The saved Ghidra 12.1.3 decompilation exposes these paths and structures:

- FUN_008583b0 (0x8583b0) is an allocation path. It reads the shared free-list head from DAT_05d26718; when non-null it pops the first entry by loading the pointer stored at the entry's first word, writes the requested asset type, initializes metadata fields and updates shared allocated/high-water counters.
- The same function emits the exact exhaustion diagnostic when the free-list head is null. The decompilation then continues into code that uses the selected pointer. This places exhaustion at the native allocator boundary, not merely at a SPRX pool limit.
- FUN_008587b0 (0x8587b0) is a native entry-transfer/copy path. It uses a native lock and copies/swaps asset payload and metadata. A reserve implementation cannot assume entries are immutable while linked or transferred.
- FUN_00858cb0 (0x858cb0) performs type-specific cleanup and updates per-type free-list state. Separate unlink/teardown paths reinsert entries into the shared DAT_05d26718 free list. Free/reuse behavior is distributed across multiple native paths.
- The hash-bucket-head array begins at DAT_057e9710 and is traversed for 0x25400 (152,576) buckets. Entry records are addressed from DAT_0587e710 with a 0x20-byte stride. The initialized shared free-list head is DAT_05d26718 = &DAT_0587e730.
- Native code uses multiple 32-bit links inside each 32-byte entry. The decompilation shows accesses through offsets 0x14 and 0x1c in addition to type/data fields. These are distinct link roles and must not be collapsed into one generic next field.
- A native pointer-to-index conversion is visible in the link path. Many consumers multiply 32-bit chain values by 0x20 to address entries. Searches in the saved analysis found dozens of uses of entry/link fields, including code outside the SPRX ClearAssetsInUse() walk.

### Impact and remaining proof
This is materially stronger than the earlier SPRX-only audit: we now have a native allocation function, transfer path, cleanup path, shared free-list head, bucket count, record stride and multiple index-link fields. It confirms reserve-page integration must cover allocation, free/reuse, link/override chains, transfer, unload and all readers—not only the SPRX hash walk.

The saved decompiler output is not original source. Its exact executable fingerprint has not yet been tied to the failing dev.66/dev.67 capture and the currently supported PS4 1.33 module. The complete native call graph and all direct/indirect index consumers have not yet been enumerated. Exact lock ownership/re-entrancy and every free-list mutation context remain unproven. The positive signed-32 index rule in PR #40 is a conservative candidate constraint, not a proven rule for every native consumer.

### Safe implementation decision
Do not add reserve mapping or an allocator detour yet. A reserve page could be addressable by the SPRX but invisible to a native reader, interpreted as a pointer by another consumer, omitted from cleanup, or raced by an unguarded free-list mutation. PR #40 remains arithmetic groundwork. Next gate: a fingerprinted native call-graph audit with every entry/link read, write, index conversion, allocator/free path and lock context listed. Then add production-body tests around the exact original functions and free/reuse behavior before considering a hook.

## 2. GPU protection fault — issue #28

The issue records an asynchronous GPU read-protection fault during a mode-common transition. The kernel capture does not identify a CPU faulting instruction or the GPU allocation/resource/submission responsible. Existing checkpoints observe frame visibility/age, GPU completion/submission counter movement, resource pending/started/done state, missing image/mesh parts and lighting progress. These are progress signals, not ownership evidence.

No GPU allocation/free order, resource lifetime, pool ownership or submission behavior was changed. The missing link is a matching-build trace tying the fault address to an allocation identity and generation, owning subsystem, last command submission referencing it, and completion/fence state. The dev.64 candidate and its local delivery record are not proof of a public-source or hardware fix. Keep the GPU fault unattributed until that chain exists.

## 3. Mode transitions and clientfield registration — issues #1 and #2

Existing public instrumentation records raw session-mode bits, selected/loaded mod names, explicit core/ZM/MP/CP zone presence, apply-request state, UI-state pointer comparisons and native level-load return values around transitions. Script errors can include a tracked script-owner slot when a matching claim exists. This improves observability but does not establish native zone ownership or client/server clientfield schema equality.

Issue #2's supplied Complex trace reports Clientfield Mismatch after loading zm_complex, with zero script runtime errors in the same capture. The current public SPRX does not expose the differing native registration entries. Existing logs do not provide a validated clientfield registry layout, names, pools, versions, widths, types or owning registration script.

Do not change transition ordering, zone ownership or clientfield registration. The next source task is a fingerprinted comparison of native client/server registration tables and registration call paths. Any reader must be bounded, read-only and guarded by verified structure/range checks. Capture both sides before mismatch teardown. Zone ownership must be traced across load, transfer, unload and reuse; UI-state pointers alone are not zone ownership.

## 4. Map/mod loading and GSC failures — issues #20, #23 and #31

### Seven-Eleven / DS4C
Issue #23's log associates mod-slot-2 with DS4C Patched in the two-mod stack. scripts/shared/array_shared.gsc first reports a by-reference array-type error near +0x4220, followed by repeated invalid-opcode reports near +0x4222. The error occurs after the observed loading stall begins. The exact DS4C package/source and matching build are still absent, so this is a strong lead, not a proven stall cause. The large asset-link count difference is not itself proof of an asset-capacity fault.

### Blood Run
Issue #31 records undefined entity/variable/vector operations in scripts/zm/zm_blood_run.gsc and repeated invalid-value polling in scripts/blood_run_menu.gsc, followed by a server shutdown in one run. A later run shows a separate gameplay freeze while client frames continue. Public source already includes an absent-only Mods_IsUsingUsermap Lua bootstrap for the frontend error; it does not fix the map/menu GSC errors or prove the gameplay/pause stall is fixed. Matching GSC source lines and a clean-start capture with the mod selected before the first map load are still required.

### Host activation / BG cache
Issue #20 shows downloaded mod files and zone readiness before EXE_ERR_BG_CACHE; manual activation of the same reported stack succeeds. Transfer/zone completion is not sufficient to establish correct BG-cache contents or host/client parity. Do not bypass native checksum validation. Capture and compare exact mod file hashes/order and received/calculated checksum values across failed automatic and successful manual activation.

No third-party GSC behavior is patched without exact source or a reproducible bytecode/source mapping. Preserve native script error handling. Do not suppress invalid opcodes, silently skip dependencies, or change mod selection/rollback semantics. Obtain exact packages/source and isolate each mod alone, then combined, on a clean process.

## 5. Target compatibility — PR #43

PR #43 corrects a real translation-unit defect: a literal escaped newline left FolderScanStatus inside a preceding // comment. It adds a source-line regression assertion to SPRX/tests/map_catalog_safety_checks.py, preventing the prior host fixture from extracting and compiling an enum token that was still commented out in the actual source file.

The correction has passed the recorded host/PR workflows, but no PS4 target build has been run after the fix. The previous automatic target build stopped at this compiler error, so additional compiler/linker errors may remain. A host regression or source-policy check is not a PS4 toolchain build.

Do not merge or manually dispatch the target build without the user's explicit authorization. When authorized, run the actual PS4 build workflow from the corrected PR head, retain the complete compiler log and artifacts, and fix each subsequent target-only error before console testing. No artifact, upload, release or runtime verification is claimed here.

## 6. Work completed vs. blocked

- [x] Re-reviewed native XAssetEntry allocation and sampled native free/reuse/transfer paths in the saved Ghidra analysis.
- [x] Recorded registry geometry, shared free-list head, exhaustion diagnostic and multiple 32-bit link fields.
- [x] Kept PR #40 arithmetic-only; no speculative allocator hook or reserve-page publication.
- [x] Reconfirmed current GPU telemetry does not attribute ownership; no speculative resource lifetime change.
- [x] Reconciled mode/clientfield, DS4C, Blood Run and BG-cache findings against their current issue records.
- [x] Confirmed PR #43 contains a source-line guard for the swallowed enum declaration.
- [ ] Tie saved executable analysis to the exact failing/supported PS4 build fingerprint.
- [ ] Enumerate every native XAssetEntry index consumer and free-list mutation/lock context.
- [ ] Attribute the GPU fault to a specific allocation and submission generation.
- [ ] Capture native zone ownership and exact client/server clientfield registry differences.
- [ ] Obtain matching DS4C and Blood Run script sources/packages and reproduce on clean startup.
- [ ] Run an explicitly authorized PS4 target build after PR #43.

No target build, console test, merge, upload, release or deployment was performed as part of this audit. FFPorter remains out of scope.


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


## Native allocator deep pass — exact operation order and distinct link roles

The saved Ghidra decompilation was re-read around the complete allocation and cleanup bodies. The following details are now recorded to prevent a future reserve implementation from relying on the wrong lock or link field.

### Allocation function 0x8583B0 (FUN_008583b0)

Observed order in the decompiler:

1. Read the global free-list head from `DAT_05D26718`.
2. If it is null, emit `Could not allocate asset - increase XASSET_ENTRY_POOL_SIZE`.
3. Increment `DAT_05D26720` (current allocation count), update `DAT_05D26724` (high-water count), and update the named `XAssetEntryCount` statistic when available.
4. Pop the free-list node by assigning `DAT_05D26718 = *(uint**)node`, then write the requested type into the first 32-bit word.
5. Attempt the per-type physical-preset free-list path using `DAT_037C8400/8408` and related per-type counters.
6. **Only if that per-type path cannot supply an entry**, acquire the state represented by `DAT_0CF60BB4` using a thread-local recursion counter and atomic compare/exchange loop. Under that scope, walk all `0x25400` hash buckets at `DAT_057E9710`, traversing bucket links at entry offset `0x14` and override/secondary links at offset `0x1C`; then release the scoped lock and call the fatal path.
7. On success, initialize the entry's type-specific data pointer, type metadata, and link/flag fields before returning it.

This ordering is critical: the shared free-list pop at step 4 occurs **before** the later `DAT_0CF60BB4` lock scope at step 6. Therefore, that lock state is not evidence that a caller owns the global free-list lock, and the current decompilation does not show it protecting reserve-page publication or the initial global free-list pop. Reusing it as a reserve-publication lock would be unsafe.

### Distinct native links and consumers

- Entry base: `DAT_0587E710`; stride: `0x20`.
- Shared free-list next pointer: the first pointer-sized word of each free node, consumed by `DAT_05D26718 = *(uint**)node` and rebuilt by native cleanup paths.
- Hash-bucket chain link: 32-bit index at entry offset `0x14` (`DAT_0587E724`).
- Secondary/override chain link: 32-bit index at entry offset `0x1C` (`DAT_0587E72C`).
- Hash bucket heads: `DAT_057E9710`, with `0x25400` buckets. The bucket-head array is not the entry table and is not the free-list.
- Entry index conversion appears as `(entry - 0x0587E710) / 0x20` in native link code. Multiple consumers multiply stored indices by `0x20` before dereferencing the corresponding link field.

The transfer path at `0x8587B0` uses a separate lock/state mechanism around payload/metadata copy or swap. The cleanup path at `0x858CB0` dispatches type-specific cleanup and updates per-type free lists. Additional teardown/rebuild paths walk the hash and secondary chains and push nodes back to the shared free list. These are separate lifecycle operations; the fact that a 32-bit index fits an arithmetic bound does not prove that an added entry is visible to every traversal or is correctly reclaimed.

### What this changes in the engineering plan

The allocator investigation is no longer blocked on finding the native allocator entry point: that function is identified. The remaining blockers are now narrower and concrete:

1. Identify and fingerprint the exact executable/module used for the failing dev.66/dev.67 run and the supported PS4 target. The Ghidra analysis profile hash `07bc342c072de5802bde3fe6af22f16637477553bf3c011ec84d73c25263f6f9` identifies the analysis profile, **not** the executable fingerprint.
2. Enumerate every function that reads or writes the shared free-list head, entry first word, offset `0x14`, and offset `0x1C`; include indirect function-table dispatches and cleanup/rebuild paths.
3. Recover the actual lock/critical-section contract for each mutation. Do not infer ownership from a shared busy flag or from a different lock used during a later fallback traversal.
4. Prove index interpretation, sentinel values, signedness, bounds and pointer provenance at every consumer.
5. Only after those gates, test the exact allocator body and concurrent allocate/free/reuse behavior. A reserve hook must attach at the allocator boundary and preserve all native accounting and cleanup invariants.

No production reserve publisher or allocator detour is justified by this evidence yet. PR #40 remains arithmetic/test groundwork only.


## Target-build workflow and current PR handoff — 2026-11-18

The repository's .github/workflows/bo3-build.yml runs on pushes to main and supports workflow_dispatch. Its SPRX job installs clang-18/lld-18, invokes .github/scripts/build_sprx.py --package, validates the native module/container, and uploads the SPRX plus native build evidence. It is not configured as a pull_request build. The GitHub connector available in this session exposes workflow-run inspection but no workflow-dispatch action. Therefore the corrected target compile can be exercised either by an explicitly approved merge/push to main (which triggers the workflow) or by the repository owner manually dispatching BO3 Auto Build in GitHub Actions. No target build was started.

The original PR #43 is now closed as superseded, not merged. Its clean replacement is PR #48, based on current main with 3 commits ahead and 0 behind; all five PR workflows passed on head 1144635efc6af64904efa1e27671598a179b26d9 (SPRX diagnostics 44237212529, project-session guard 44237212480, mod stack transaction 44237212537, script priority context 44237213746, frontend reload state 44237212518). PR #48 is ready for review and remains unmerged pending the target-build authorization.

PR #40 remains draft research groundwork only. Its production reserve hook was removed; SPRX/t7_maps.cpp matches main byte-for-byte. Its latest safe head passed SPRX diagnostics and project-session guard, but the tests validate helper arithmetic and repository policy, not the native allocator. The private dev.67 candidate described in issue #30 remains separate and unreviewed from its local source archive.
