# Wait-zone list cross-thread publication review — 2026-11-18

## Status

**Finding:** source-supported concurrency hazard; actual runtime race occurrence is not yet proven.
**Scope:** SPRX only. This review blocks treating PR #39's atomic UI wait-state as complete transition synchronization.

## Evidence

1. `WaitForModZones()` mutates the shared `g_waitZones[]`, `g_waitZoneCount`, `g_waitFrom`, `g_reloadCheck` and `g_reloadSince` fields without a lock or atomic publication protocol.
2. `WaitForModZones()` is called from `LoadXAssets_h()` (the detour installed at the verified `DB_LoadXAssets` offset) when requested mod zones are added, and from the mod-apply path.
3. `T7Maps_FrameWork()` runs in the frame callback and reads `g_reloadCheck`, `g_waitZoneCount` and each `g_waitZones[i]` while calculating zone readiness.
4. The PR #39 implementation explicitly describes the wait-zone names as worker-owned and adds `g_uiZoneWaitState` so UI callers can avoid reading that array. However, `T7Maps_FrameWork()` still directly reads the mutable array. The new atomic state protects that separate UI predicate; it does not by itself publish a coherent array snapshot to the frame reader.
5. The shared flags/count/timestamps are ordinary non-atomic fields. If the loader hook and frame callback execute on different pthreads, this is a C++ data race and the frame can observe a partially updated list/count or stale reload state.

The native hook can be entered from more than one call path; thread identity and serialization of all callers have not yet been established. Therefore this is recorded as a high-priority hazard, not asserted as the proven cause of a reported crash.

## Impact

- The frame callback may iterate a wait-zone count while the loader is still writing names.
- A stale or partially published count/name set can cause premature frontend reload, delayed UI readiness, missed readiness transitions or invalid name reads.
- The atomic `g_uiZoneWaitState` in PR #39 does not close this writer-to-frame-reader race.
- A successful host test that checks only atomic UI predicate text cannot prove the shared list is race-free.

## Proposed correction

Preferred design: make the frame thread the sole owner of the mutable wait-zone list.

- Have loader-hook callers publish bounded, copied zone-name events into a fixed-capacity queue with explicit overflow diagnostics; do not enqueue pointers into the temporary `ZoneInfo` array.
- Drain events on the frame thread and update the canonical wait list, timeout, `from` index and readiness state there.
- Publish only an atomic generation/state to UI consumers. UI readers must never inspect the mutable list.
- If a bounded event queue cannot be implemented safely for the actual producer count, use a short, explicit synchronization primitive around a copied snapshot. The frame callback must use a nonblocking try-lock and skip one readiness update on contention; it must never spin or sleep while holding up `Com_Frame`.
- Establish whether `DB_LoadXAssets` can have concurrent producers. If multiple writers exist, the queue/lock must support them rather than assuming a single producer.
- Preserve existing timeout, held-overlay, frontend handoff and zone-readiness semantics.

## Required tests and evidence

- Extract/compile the production publication and snapshot helpers in a host harness.
- Exercise concurrent writer(s) and frame reader under ThreadSanitizer; include list reset, append, duplicate names, overflow, held-ready, timeout and simultaneous frontend transitions.
- Assert no borrowed `ZoneInfo.name` pointer survives the hook call.
- Verify that contention never blocks the frame reader and that no event is silently dropped.
- Run all host regression workflows and the PS4 target build.
- Capture loader/frame pthread IDs and transition generations on console before claiming runtime closure.

## Disposition

PR #39 remains draft until this is either disproven by verified single-thread/call-serialization evidence or corrected with production-path concurrency tests. Do not remove the atomic UI state; it addresses a separate reader path. Do not replace it with an unsynchronized flag or expose the worker-owned array to Lua.
