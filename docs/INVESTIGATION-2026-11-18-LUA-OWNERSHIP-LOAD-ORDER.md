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

## Implementation candidate — PR #58

The source-only candidate adds:

- `ActiveModLuaRetentionScopes`, an atomic RAII counter for nested/concurrent mod-zone `LoadXFile_h()` scopes and the full changed-stack `ApplyModsNow()` transaction.
- A bounded readable zone-name copy before resolving the current stack index; the per-thread context now points at that call-lifetime copy, while the native `LoadXFile` arguments remain unchanged.
- A global active-zone/stack-transition fallback in `T7Maps_NeedsLuaRetention()`: during a mod-zone load or changed-stack transaction, retain only Lua rawfiles even if the ownership index has not yet been marked and `g_loadedCount` is still zero.
- The existing ownership-index path remains gated by `T7Maps_UsingMods()`, so stale names do not cause stock Lua retention after mods are disabled.
- The rawfile hook delegates the complete policy to `T7Maps_NeedsLuaRetention()`; the `.lua` suffix check is now case-insensitive.
- A DEBUG transition diagnostic reports the cumulative number of active-zone fallback retentions.

The host candidate extends the production `LoadXFile_h()` fixture with nested, concurrent and base-zone cases under ASan/UBSan + TSan, tests the retention policy truth table, and asserts the rawfile hook no longer short-circuits on `T7Maps_UsingMods()`.

The fallback intentionally may retain a stock Lua dependency requested by another worker during a mod-zone load or stack transaction. Its counter is included in transition diagnostics so this memory cost can be measured against the existing retention budget. Exact-head workflow and target-build results are pending; no runtime claim is made.

## Additional transition-scope refinement — 2026-11-18

Reviewing `ApplyModsNow()` and `AppendMods()` corrected the initial-load timing assumption: the ordinary menu path publishes `g_loadedCount` via `SetLoaded()` before the native mod-zone load. The host-session path is different and delegates to a fresh common-zone transaction. To cover both without depending on the exact `g_loadedCount` update point, the implementation will keep a retention scope active for the entire changed-stack transaction in `ApplyModsNow()`, in addition to the narrower per-zone `LoadXFile_h()` scope. The counter is nested/atomic, so the zone scopes remain valid inside the transaction. This can conservatively retain a stock Lua dependency during a stack transition; the fallback counter measures the cost.

## Validation feedback — diagnostics fixture dependency

The first PR workflow run found that `diagnostic_hook_checks.py` extracts `TraceModTransition()` into a standalone host fixture. The new transition fallback counter is a legitimate production dependency but the fixture did not declare it, so the extracted function failed to compile. This is a test-fixture dependency gap, not a target-source failure. Add an atomic zero-initialized counter to the fixture and assert the transition trace reports it; then rerun all exact-head workflows.

The zone-context regression now compares the copied context's zone-name contents rather than pointer identity; the hook intentionally stores a bounded call-lifetime copy instead of the engine-owned input pointer.

The follow-up fixture review also found the new transition-log assertion reused `found`, which is declared later in the same generated C++ fixture. Use a distinct `retentionTraceFound` variable to keep the fixture valid; this is another test-only correction, not a production behavior change.

The next exact-head diagnostic run found that `session_common_activation_checks.py` extracts the production `ApplyModsNow()` body but did not include the new retention-scope type or global instance. The correction is to include the production `mod_load_context.hpp` helper in that fixture and declare its test instance; the zone-context test separately exercises real nested/concurrent counter behavior. This is a host-fixture dependency, not a production compile failure.

The next diagnostics run found the existing `mod_lua_retention_checks.py` fixture still defined a `T7Maps_UsingMods()` stub that became unused when the outer gate was removed from the production rawfile hook. With `-Werror`, the stale static helper now fails the fixture compile. Remove the obsolete stub (and any state used only by it); the production policy remains exercised through the new helper tests.

The next diagnostics run exposed an obsolete `T7Maps_UsingMods()` stub in the bytecode-retention fixture. Because the production hook now delegates the complete decision to `T7Maps_NeedsLuaRetention()`, the fixture must model the new policy rather than retain the old outer gate. Remove the unused stub and exercise both `activeModRetentionScope=true` with `modsActive=false` (initial load) and both false (stock lookup after disable).

Review of the session fixture showed it extracts both `ApplyModsNow()` and `ApplyModsAtFrontend()`. The latter can call `AppendMods()` without the former's stack-transition scope; therefore only the common-zone stubs reached from `ApplyModsNow()` should assert the transaction scope. The `AppendMods()` stub must remain neutral. The zone-context fixture also compares the copied zone-name context by string value, not string-literal pointer identity.

## Follow-up review finding — first-mod zone index zero

The production `StackIndexOfZone()` returns `0` for the first unprefixed mod zone (`core_mod`, `zm_mod`, `mp_mod`, `cp_mod`) through its `ZoneKind()` fallback; later stacked zones return positive indices. The initial implementation used `zoneIndex > 0`, which misses the first mod when `ApplyModsAtFrontend()` loads it outside an `ApplyModsNow()` transition scope. The active per-zone condition must be `zoneIndex >= 0`. Extend the production hook fixture to distinguish the first unprefixed mod zone (index 0), later `m2_`/`m3_` zones, and unrelated base zones (index -1). This is a real coverage defect and must be fixed before merge.

## Latest host-suite feedback — 2026-11-18

The full Project Session Guard found two remaining extracted-fixture integration defects on head `ac92c6cd57a0546a88eb0f5f627dc1b0bdd4950e`: `ui_startup_unload_checks.py` extracts `T7Maps_NeedsLuaRetention()` and must provide the new `IsLuaUiFileName`, active-scope and fallback-counter dependencies; `zone_load_context_checks.py` stores `opened` as `std::string`, so its new `strcmp` assertions must pass `opened.c_str()`. These are fixture compile errors, not PS4 target errors. Add the minimal stubs and correct the string-view use, then rerun the entire host inventory. The first-mod `zoneIndex >= 0` source correction remains in place.
