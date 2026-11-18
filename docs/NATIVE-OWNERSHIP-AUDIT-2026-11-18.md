# Native ownership and target-readiness audit (2026-11-18)

This audit records what the available PS4 retail executable analysis and current SPRX source establish for the remaining stability tracks. It intentionally separates confirmed control/data flow from hypotheses. No unverified native allocator, GPU resource, zone-lifetime or clientfield-layout hook is introduced.

## 1. GPU protection fault — ownership still not attributable

### What the current SPRX actually observes

The current debug-only dispatch hook in `SPRX/t7_maps.cpp` records a bounded snapshot containing:

- command-buffer pointer selected from the context's deferred pointer, falling back to its immediate pointer;
- command label pointer and issued-command counter read from that buffer;
- caller return address;
- compute/shader pointer from the context;
- dispatch dimensions and current level-frame count.

The hook then immediately forwards the original dispatch call. The stall reporter separately samples native frame/stream progress, required/resident image and mesh parts, blob residency, and command completion/submission progress.

This is useful correlation data, but it does not establish:
- which allocation created the command buffer, shader, descriptor, texture, render target or backing GPU memory;
- which subsystem owns each allocation or its release callback;
- whether the command buffer is still in flight when an associated resource is released;
- which submission/fence/queue completion makes the resource safe to reclaim;
- whether the protection faulting address belongs to the recorded dispatch or to another GPU client.

### Required fix path

1. Recover the exact GPU submission and memory lifecycle imports/call graph for the supported PS4 EBOOT, including queue submit, direct-memory allocate/map/unmap/free, resource creation/destruction and completion/fence paths.
2. Identify stable allocation handles and ownership edges; do not use numerical address overlap as proof of ownership.
3. Correlate each dispatch with a monotonically increasing submission ID and queue/fence completion, without dereferencing pointers after their lifetime.
4. Record bounded allocation/free events and the resource's last submitted fence; retain resources until the native completion contract proves safe release.
5. Correlate the protection-fault address and fault timestamp with live allocation intervals and in-flight submissions. A match is attribution evidence only after address-space and lifetime semantics are verified.
6. Add offline tests for address reuse, overlapping virtual ranges, out-of-order completion, double free, queue reset, and log-buffer overflow. Then validate on the exact console/build.

Do not add a guessed free hook, delay frees, or retain arbitrary GPU memory. Those can leak scarce memory or make a fault worse.

## 2. Mode transitions and clientfield registration

### Confirmed executable observations

The saved retail executable analysis contains clientfield/netfield code paths with these visible behaviors:

- The clientfield registry is partitioned into 14 set tables (loop bound `0xE`).
- Each set uses a table descriptor with a `0x4018` byte stride. The decompiled code reads a per-set entry count and iterates a pointer array of registered field descriptors.
- Field descriptors are accessed through fields including an identifier at `+0x18`, a bit offset at `+0x24`, a field kind/type byte at `+0x25`, a bit width at `+0x28`, and a bit mask at `+0x20`. A field-set packing routine reports when assigned bit widths exceed the 32-bit field capacity.
- Runtime getters/setters select a clientfield set and look up a descriptor by ID. They distinguish ordinary, counter and other field types and report “Unknown client field set” or “Client field does not exist” when the expected registration is absent.
- Other code logs “Netfield %s not found during BG_InitClientFields,” demonstrating that initialization resolves named netfields before use.

These observations show that a clientfield mismatch can arise from set selection, missing registration, field type, bit width/offset/mask, or initialization order—not merely a missing name. The current SPRX transition snapshot logs selected/loaded mod stacks, mode/common state, UI state and Lua generation, but it does not yet snapshot this native registry.

### Safe diagnostic next step

Before adding any native reads, recover the exact initialization function and its callers, identify the set-table globals and per-build address fingerprints, and verify the registry is stable while snapshots are taken. Then add read-only, bounded snapshots of each set's count and field descriptors, with a generation/initialization guard. Compare ZM and MP only after both registries are known complete. Log differences by set, field ID/name, type, width, bit offset, mask and registration order. Never mutate the registry or repair offsets at runtime.

### Zone ownership gap

The current mod loader wraps native zone loads/unloads and records request flags and selected/loaded mod state. It does not yet prove which native zone record owns each script/clientfield registration, when that registration is retired, or whether a mode transition reuses an old registry generation. The next pass must trace native zone acquire/release and clientfield init/shutdown against the same generation timeline. Do not infer ownership solely from zone names or allocation flags.

## 3. Map/mod loading — exact script evidence remains mandatory

The available logs narrow some failures to particular mod slots and GSC offsets, but compiled GSC bytecode does not reliably identify the original source-level expression or correct fix. A generic SPRX-side workaround would risk hiding malformed script behavior or breaking unrelated mods.

Required evidence per reproduction:
- exact mod package/archive and its checksum;
- exact compiled GSC file and the source/decompiler output for the failing function/offset;
- game executable/build fingerprint and BO3-Customs SPRX build;
- clean-process log from before first map load through the first error, server shutdown, stall or crash;
- selected mod stack and zone request/unload timeline;
- a baseline run without the failing mod and a controlled one-mod-at-a-time run.

Then validate the script's array/reference/type contract, opcode sequence and required globals against the matching build. Fix the script or its loader contract at the narrowest layer. Preserve the ability to disable every mod and restore the included stock Lua files; do not retain duplicate bytecode or mutate original assets as a workaround.

## 4. XAssetEntry exhaustion — native allocator recovery

The deeper allocator findings are recorded in [XAssetEntry reserve-index safety](XASSET-RESERVE-INDEX-SAFETY.md) on PR #40. In brief, the saved executable analysis identifies native allocation at `0x8583B0`, the global free-list head, 32-byte entries, fixed hash buckets, and multiple native chain traversal/release paths. That proves the allocator boundary more clearly than the previous SPRX-only audit, but not the complete index-encoding, sentinel, synchronization or mapping-lifetime contract. Reserve-page runtime integration remains unsafe until every consumer is enumerated and verified.

## 5. Target compatibility after PR #43

PR #43 restores the newline that had commented out `FolderScanStatus` and adds a source regression guard. Its SPRX diagnostics and host workflows pass on the PR head, but those checks do not compile the complete source with the PS4 SDK/toolchain. The target translation unit remains unverified.

The repository's automatic PS4 build is tied to the protected main-branch workflow path; the available GitHub integration exposes workflow-run inspection and reruns but no workflow-dispatch action. I have not merged PR #43 or pushed to main merely to force a build. The safe next step is to approve the PR/main build trigger or provide a dedicated non-deploying target-build workflow with a manual dispatch. No artifact upload, release or console deployment is authorized by this audit.

## Status summary

| Track | Confirmed progress | Still required before claiming fixed |
|---|---|---|
| XAssetEntry exhaustion | Native allocator and several index/free paths recovered; PR #40 arithmetic groundwork documented | Complete all-consumer index contract, synchronization, mapping lifetime, production hook tests, nine-mod console reproduction |
| GPU protection fault | Current debug dispatch and progress instrumentation characterized | Native allocation/submission/fence/free ownership graph and correlated fault capture |
| Mode transitions | Native clientfield set/table behavior partially recovered; current transition snapshots reviewed | Exact registry globals/init/shutdown, stable read-only snapshot, ZM/MP diff, zone ownership generation |
| Map/mod loading | Existing logs narrow failure locations | Exact matching GSC package/source and clean-start controlled reproduction |
| Target compatibility | PR #43 host/source guards pass | Full PS4 SDK target compile and artifact inspection |

No issue is closed by this investigation. No production GPU ownership hook, clientfield mutation, allocator hook, target build, console test, upload or deployment was performed.
