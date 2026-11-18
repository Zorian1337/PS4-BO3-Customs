# Mod Lua retention drain before zone unload — 2026-11-18

## Source evidence

- `RetainModLua()` dereferences the native `RawFileAsset`, reads the bytecode header, validates the source buffer, and hashes the complete bytecode body before acquiring `g_retainedLuaLock`.
- The bounded 200-attempt `g_retainedLuaLock` protects the retention arena/list after the source hash. It does not protect the source rawfile buffer while it is being validated or hashed.
- `T7Lua_PrepareModUiUnload()` currently logs retained counts/bytes and unconditionally returns true. It does not close the retention path, wait for in-flight operations, or coordinate with `RetainModLua()`.
- `ApplyModsNow()` calls `T7Lua_PrepareModUiUnload()` before paths that can remove mod zones. `FreeModsFrom()` can then release the zone containing the source rawfile.
- PR #58's active mod-zone/stack retention scopes decide whether a rawfile should be retained; they do not drain an already-running `RetainModLua()` call.

## Impact and confidence

This is a source-level lifetime race. If a loader worker is validating or hashing a mod Lua bytecode buffer while another thread proceeds through `FreeModsFrom()`, the backing zone can be unmapped during the read. The arena lock does not prevent this because it is acquired after the source hash. No specific crash log has yet proven this is the cause of a reported incident, but the ownership gap is concrete.

## Proposed correction

1. Add a small retention-operation gate with an atomic `closing` flag and atomic active-operation count.
2. Enter the gate at the very start of `RetainModLua()`, before dereferencing the native asset header or buffer. The RAII guard increments the active count, rechecks `closing`, and fails closed if unload has begun. The guard decrements on every return.
3. Make `T7Lua_PrepareModUiUnload()` close the gate, then wait a bounded interval for active operations to drain. On success, leave the gate closed and return true. On timeout, reopen it and return false so `ApplyModsNow()` aborts rather than freeing the zone.
4. Add `T7Lua_ResumeModUiRetention()` to reopen the gate only after old mod zones are safely released and before any new mod Lua lookup can occur.
5. Integrate resume at each verified transition point: after successful `FreeModsFrom()` and before `AppendMods()`; on a failed free, before returning; and at safe points in host-session/common-only branches that do not free mod zones. Keep `T7Lua_FrontendWillLoad()` as an idempotent safety reopen before frontend Lua scripts are requested.
6. If a lookup reaches `RetainModLua()` while the gate is closed, return the immutable rejection asset without touching the native rawfile pointer. Never return the borrowed bytecode pointer during a close window.
7. Keep the arena lock and its bounded acquisition policy; the new gate protects source lifetime, while the existing lock protects arena/list publication. Do not conflate the two.

## Required validation

- Host concurrency tests for Enter-vs-Close races, nested operations, active-count drain, timeout/reopen, and close/reopen ordering under ThreadSanitizer.
- A production `RetainModLua()` fixture that passes an intentionally unreadable rawfile pointer while the gate is closed and verifies the rejection asset is returned without dereference.
- Source-level integration checks for all `ApplyModsNow()` exits and the `FreeModsFrom()`/`AppendMods()` boundary.
- Full host regression inventory and a fresh PS4 target build.
- Console test of repeated enable/disable/reload and map transitions remains separate.

## Safety boundary

Do not merge a gate that can remain closed after a failed or deferred transition. Every successful close must have an explicit, audited resume point; every timeout must reopen before returning false. Do not reset/free the append-only bytecode arena as part of this fix because existing HKS closures may still reference retained chunks.


## Implementation plan — retention operation drain (2026-11-18)

### Required invariant
A native `RawFileAsset` header and its bytecode buffer are borrowed from a zone. No code may dereference either pointer after the unload barrier begins unless it has successfully entered the retention-operation gate. Unload may proceed only after the gate is closed and the active-operation count reaches zero. A lookup that arrives while closed must return the immutable rejection asset without inspecting `name`, `original`, the rawfile header, or the buffer.

### Concurrency design
Use one atomic word with a high `closing` bit and low active-reader count. Entry uses a compare/exchange loop: reject if `closing` is set; otherwise increment the count atomically. Close sets the bit with `fetch_or`, preventing all later entries, then waits a bounded number of short intervals for the low count to reach zero. This single-word state avoids the race inherent in separate `closing` and `active` atomics. The RAII reader guard decrements on every return. A timeout clears the closing bit and aborts the unload; it must never leave retention permanently closed.

### Integration boundaries
- Enter at the very first instruction of `RetainModLua()`, before validating or dereferencing the asset name/header/buffer.
- `T7Lua_PrepareModUiUnload()` closes and drains; it returns false on timeout so `ApplyModsNow()` leaves all zones intact.
- If frontend shutdown cannot be scheduled, or a later pre-free check aborts the transition, explicitly reopen the gate before returning.
- For a queued frontend transition, keep the gate closed across the gap until `ApplyModsAtFrontend()` has successfully removed old zones; reopen before the new `core_frontend` native load can request Lua modules.
- For the host-session/common-zone transaction, reopen only after the native common-zone load returns successfully. If the transaction is rejected before any zone free, reopen on that exit.
- If `FreeModsFrom()` fails or reports remaining mod zones, reopen before returning because the old source zones remain resident. On successful free, keep the gate closed only until the replacement stack is established and before any new frontend Lua lookup.
- Preserve the append-only retained bytecode arena. This gate protects source-buffer lifetime; it does not authorize reclaiming old chunks or manipulating the HKS module cache.

### Tests required before merge
- Unit test the production gate helper: entry/close race, nested readers, concurrent readers, close rejection, drain, timeout/reopen, and repeated close/open cycles.
- Compile and run under ASan/UBSan and ThreadSanitizer.
- Extract the production `RetainModLua()` body into a host fixture and pass an intentionally unreadable pointer while closed; assert the rejection asset is returned without any pointer read.
- Source integration checks every `ApplyModsNow()` return after a successful close, frontend queued transition, `ApplyModsAtFrontend()`, `FreeModsFrom()` failure/success, and host common-zone return.
- Full host regression inventory and fresh PS4 target build. Console validation is still required for real HKS/module-cache and disable/re-enable/reload behavior.

### Failure policy
Fail closed: on drain timeout, do not unload any zone. On a lookup while closed, return the immutable Lua error asset without dereferencing borrowed data. Never free/reset the retained arena. Keep the user's ability to disable mods by ensuring every aborted transition reopens the gate and every successful transition reopens before new UI scripts are loaded.
