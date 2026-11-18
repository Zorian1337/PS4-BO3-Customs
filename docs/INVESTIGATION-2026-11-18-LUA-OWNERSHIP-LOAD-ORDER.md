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


## Follow-up source review — first-stack zone scope and fixture policy (2026-11-18)

### Newly identified production boundary defect

Reviewing PR #58 against the actual StackPrefix(), StackName() and ZoneKind() implementations found that StackPrefix() only recognizes m2_ through m24_ and returns a zero-based index (number - 1). The first selected mod's four zones are deliberately unprefixed (core_mod, zm_mod, mp_mod, cp_mod); ZoneKind() recognizes these names and StackIndexOfZone() returns index **0**. Later stacked mods return indices 1–23.

PR #58 currently enables the per-zone retention scope only when zoneIndex > 0. That excludes every first-mod unprefixed zone. The full ApplyModsNow() transaction scope covers stack changes initiated through that function, but it does not cover later level loads of an already-selected first mod when no stack change is occurring. In that path, a rawfile lookup can still race ahead of the ownership mark.

**Impact/confidence:** direct source-level control-flow finding; high confidence that index 0 is excluded. Whether a particular console lookup hits the window still needs a matching-build trace. This is a correctness gap in the proposed fix, not merely missing test coverage.

**Required correction before merge:** enable the per-zone RAII scope for every recognized mod-zone kind (zoneIndex >= 0), including index 0. Keep unrelated zone names at -1 and do not enable the fallback for them. Extend the production LoadXFile_h() fixture to assert that unprefixed first-mod zones map to 0 and activate the scope, m2_/later zones map to positive indices and activate it, and unrelated/base game zones remain inactive. Cover nested and concurrent scopes under ASan/UBSan + TSan.

### Retention fixture correction

The failed PR #58 diagnostics run is caused by the obsolete extracted-fixture stub T7Maps_UsingMods(), which is no longer called by the production rawfile hook after retention policy was centralized in T7Maps_NeedsLuaRetention(). The fixture's active flag is still needed: make its T7Maps_NeedsLuaRetention() stub call the production T7LuaOwnership::ShouldRetainLua(true, false, active, owned && ownership.MayContain(name)), remove only the unused T7Maps_UsingMods() stub, and keep the existing disabled-mod assertion for the marked ui/test.lua asset. This preserves a meaningful test of stock passthrough after disable instead of deleting that coverage.

Both corrections are required before treating PR #58 as review-ready. Re-run the full exact-head diagnostics, sanitizer tests, project-session guard and all other PR workflows afterward; then synchronize with current main, review the complete diff and obtain a fresh PS4 target build.


## Implementation status — current-main PR #59 (2026-11-18)

The active-zone retention correction and its regression coverage have been ported from the diverged PR #58 branch onto a clean branch based on current main as PR #59 (`28fedd0dca94eb0cda2f636f3d76dfbacdc84331`). The implementation now:

- Uses an atomic RAII counter for every recognized mod-zone `LoadXFile_h()` call, including first-mod index 0, and for the complete changed-stack `ApplyModsNow()` transaction.
- Copies and bounds the zone name for the lifetime of the native load call while preserving the original native arguments.
- Removes the rawfile hook's outer `T7Maps_UsingMods()` short-circuit and centralizes the decision in `T7Maps_NeedsLuaRetention()` / `ShouldRetainLua()`.
- Preserves stock Lua passthrough when mods are disabled outside active mod-zone/stack-transition scopes.
- Tests all four unprefixed first-mod zones, later stacked zones, unrelated-zone exclusion, nested/concurrent scopes, fallback policy and disabled-stock behavior.

All six exact-head PR #59 workflows passed: SPRX diagnostics, Project Session Guard, in-game script log regression, frontend reload state regression, script priority context regression and mod stack transaction regression. The branch is one commit ahead and zero behind current main. A fresh PS4 target build is still required before merge; no console, HKS module-cache restoration or full disable/re-enable/reload lifecycle claim is made. The original PR #58 branch is superseded and is not the merge candidate.
