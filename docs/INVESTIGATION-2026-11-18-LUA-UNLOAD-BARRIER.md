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
