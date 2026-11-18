# Mod Lua ownership mark-before-lookup ordering — 2026-11-18

## Source evidence

- `LoadXFile_h()` creates a per-thread `ModLoadContexts<>::Scope` from its zone-name argument before calling the native `LoadXFile` function. The context remains available for the duration of that native load.
- `LinkXAsset_h()` calls `NoteLevelLua()` after the native asset-link operation. For rawfile assets, `NoteLevelLua()` calls `NoteUiFile()`, which marks a bounded `.lua` name in `g_modLuaOwnership`.
- `T7Maps_NeedsLuaRetention()` currently consults only `g_modLuaOwnership.MayContain(name)`.
- The rawfile hook in `t7_lua.cpp` additionally gates retention on `T7Maps_UsingMods()`.
- `ApplyModsNow()` updates `g_loadedCount` after the mod-zone load operation returns. During the initial load, the mod zone can therefore be in flight while the loaded-mod count still reflects the previous (possibly empty) stack.

The per-thread load context and ownership index make attribution possible, but the current retention decision does not use the active zone context. A lookup that occurs during the mod-zone load before `NoteUiFile()` publishes the name can miss the index. The outer `T7Maps_UsingMods()` gate can also suppress retention during initial mod loading while `g_loadedCount` has not yet been updated.

## Impact and confidence

The source ordering and current gating are directly visible. Whether BO3 actually requests the Lua rawfile before or after the link hook on the same or a different worker still needs a matching-build trace. This is a credible lifetime-safety gap, not a proven cause of a reported crash.

PR #57 closes the separate in-flight `Mark()/MayContain()` publication window. It does not close a lookup that begins before `Mark()` has started.

## Proposed correction

1. Add a small RAII active-mod-zone-load counter. In `LoadXFile_h()`, safely copy/validate the zone name, resolve it with `StackIndexOfZone()`, and increment the counter only when the zone is a non-base mod stack entry. Decrement on every exit.
2. Keep the existing per-thread `ModLoadContexts` scope. The global active counter covers a rawfile lookup that runs on a different worker while a mod zone is being loaded.
3. Change `T7Maps_NeedsLuaRetention()` to return true for bounded `.lua` names while any mod zone load is active, even if `g_loadedCount` has not yet been updated. Outside an active mod-zone load, preserve the existing `T7Maps_UsingMods() && ownershipIndex.MayContain(name)` behavior so disabling mods returns stock Lua without retaining every previously modded name forever.
4. Remove the outer `T7Maps_UsingMods()` gate at the rawfile hook call site; the helper becomes the single policy point and checks active-zone context or the published ownership index.
5. Count/log how many rawfile lookups use the active-zone fallback. This makes the conservative false-positive cost measurable; do not retain non-`.lua` assets.
6. Add host tests for nested/concurrent active-zone scopes, initial load while loaded-mod count is zero, stock lookup after all mod-zone scopes end, and non-Lua names. Add source assertions that `LoadXFile_h()` scopes the counter around the native call.

## Tradeoff

While any mod zone is being loaded, a Lua rawfile lookup from another worker may be a stock dependency rather than an asset owned by that mod. The fallback conservatively retains it. The window is limited to active mod-zone loading and the file type is limited to `.lua`; measure the extra retained count against the existing 32 MiB/4,096-header budget.

## Required validation

- Production helper tests for active counter RAII, nested loads, concurrent loads, counter underflow avoidance and retention decision.
- ThreadSanitizer on the counter and lookup/mark interactions.
- Full host regression inventory and PS4 target build.
- Matching-build DEBUG capture with zone name, stack index, pthread ID, lookup decision and ownership mark order.
- Console validation remains separate.
