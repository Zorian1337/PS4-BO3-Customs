# Wait-zone publication and custom-image lifetime review

Date: 2026-11-18  
Scope: SPRX only  
Status: findings documented; no implementation change made in this review

## 1. Wait-zone publication race (PR #39)

### Source evidence

The PR #39 implementation adds an atomic `g_uiZoneWaitState` and updates the UI predicate to read only that atomic. The code comments describe the wait-zone name array as worker-owned. That protects the UI predicate from directly traversing the array, but it does not synchronize the array's other readers and writers.

The source has these paths:

- `WaitForModZones()` writes `g_waitZoneCount`, `g_waitZones`, `g_waitFrom`, `g_reloadCheck` and `g_reloadSince`. It is called from the `LoadXAssets_h()` path and from the frontend zone-loading path.
- `T7Maps_FrameWork()` reads `g_waitZoneCount` and each `g_waitZones[i]` while calling `ZoneStateOf()`.
- `PruneWaitZones()` reads and compacts the same array and writes `g_waitZoneCount`; it is called during mod-stack application.
- `TraceModTransition()` reads the plain `g_reloadCheck` and `g_waitZoneCount`.
- `T7Maps_RequestApply()`, `T7Maps_RequestPrefetch()`, `T7Maps_MenusBuilt()` and `T7Maps_FrameWork()` also read/write the plain reload flags/timestamp. Only `g_uiZoneWaitState` is atomic.

There is no lock, immutable snapshot, atomic element storage or generation validation around the wait-zone array/count. Publishing Pending before mutation prevents the UI from treating the state as ready, but does not make concurrent reads of the ordinary C++ array/count safe. A frame can read the list while the loader appends, or prune while the loader updates it. The plain reload flag/timestamp can also be observed inconsistently.

### Impact and confidence

- High confidence: the shared wait-list and reload fields are unsynchronized in source.
- Runtime race occurrence is not yet proven: exact pthread identities and overlap timing require a matching-build DEBUG trace.
- Possible effects include torn/truncated names, skipped zones, incorrect readiness counts, lost pending zones during pruning, premature UI unlock, or undefined behavior from C++ data races.
- The existing atomic UI predicate is a partial mitigation, not a complete publication protocol.

### Proposed correction

Replace the mutable global wait list with a bounded, versioned snapshot publisher:

1. Serialize producer updates with a very short lock; do not call native zone-state functions, logging or allocation while holding it.
2. Merge names into the published state and increment a generation.
3. Have the frame thread attempt a nonblocking snapshot read. If publication is busy, skip the wait-list work for that frame and leave the UI state Pending.
4. Evaluate `ZoneStateOf()` against the local snapshot after releasing the lock.
5. Prune with compare-and-publish against the snapshot generation. If a producer has added zones since the read, discard the prune result rather than overwrite the newer list.
6. Move reload flags/timestamps and held/forced state into the same synchronized state or make each independently atomic with explicit ordering.
7. Make the 64-zone capacity explicit. On overflow, fail closed and report the overflow; never silently drop a required zone.

### Required validation

- Deterministic TSan test with concurrent producer and frame-reader threads.
- Producer appends while a snapshot is being read.
- Producer appends while pruning is prepared; generation mismatch must prevent lost updates.
- Duplicate zones, multiple producer calls, nested loading, empty/missing names, maximum capacity and overflow.
- Busy snapshot lock must not block the frame thread or clear Pending.
- Matching-build DEBUG trace of `scePthreadSelf()` in `WaitForModZones()`, `T7Maps_FrameWork()` and `PruneWaitZones()` to establish actual thread identities and overlap.
- Re-run full SPRX host inventory and PS4 target build.

## 2. Custom-image retirement and delayed callbacks (PR #39 / issue #29)

### Source evidence

The PR adds a fixed `g_retiredPictures[1024]` registry. It keeps retired native image addresses so delayed `SetImage_h()` callbacks do not blindly forward an old custom-image pointer. When the registry fills, it fails closed and stops replacing stale custom images. The active and retired registries are ordinary global arrays/counters; there is no explicit synchronization around `RegisterImage_h()`, `PictureFor()`, `RetirePicture()` and `SetImage_h()`.

The retired-address record is updated when the same address is encountered again. Since the callback carries a raw image pointer rather than an allocator generation, address reuse can make an old callback indistinguishable from a callback for a newly allocated image at the same address. The code validates the UI element handle, but that is not the same as validating the image allocation generation.

### Impact and confidence

- Confirmed design limitation: the tombstone registry has a hard 1024-entry lifetime cap and never reclaims records; after saturation, custom image replacement is disabled to preserve safety.
- Potential stale-generation ambiguity: native image pointer reuse is not paired with a generation token in the callback. Whether this produces a visible or unsafe stale update depends on native slot reuse and callback lifetime, which are not established by source alone.
- Thread race is not proven: `RegisterImage_h()` and `SetImage_h()` are Lua/UI hooks, but their actual pthread identity and concurrent invocation are not recorded.

### Proposed correction

Before changing the allocator-facing behavior:

1. Instrument image registration, retirement, callback and native slot reuse with pointer, name, element generation, frame and pthread ID.
2. Recover whether the native image slot has a generation/version field or whether a callback-drain/epoch barrier exists.
3. Prefer a generation-aware ownership token or a proven callback grace period before reclaiming retired addresses.
4. If address reuse cannot be distinguished safely, keep fail-closed behavior rather than evicting tombstones; make saturation visible and measured.
5. If callbacks can run concurrently, serialize registry mutations and lookups with a bounded, nonblocking publication design.

### Required validation

- TSan concurrent registration/retirement/callback fixture if distinct threads are possible.
- Deterministic stale callback before free, after free, after slot reuse by stock image and after slot reuse by another custom image.
- Retired registry saturation and fail-closed behavior.
- Matching-build DEBUG trace proving callback/registration thread identities and native slot reuse semantics.
- Full SPRX host suite and PS4 target build.

## Merge gate

PR #39 remains draft. Its UI atomic predicate alone is not sufficient evidence that the wait-zone state is race-free. Do not merge the wait-zone or image-lifetime changes until the relevant ownership/threading evidence and regression tests are complete. Keep the current known-buildable main source unchanged while this investigation is resolved.
