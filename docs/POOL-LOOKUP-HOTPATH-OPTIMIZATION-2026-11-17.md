# Asset-pool lookup hot-path optimization — 2026-11-17

## Finding

LinkXAsset_h calls GrowPool(type) for every linked asset. GrowPool calls
GrowthFor(type), which previously scanned the entire g_poolGrowth array
linearly, even when the current asset type was not in the growth allowlist.

The allowlist is static and strictly sorted by asset type. This makes the
linear scan unnecessary work on a high-frequency database-worker path.

## Change

GrowthFor() now performs a lower-bound binary search over the existing immutable
array. It returns the same matching record or null; it does not change any
pool capacities, eligibility, allocation sizes, synchronization, or engine
calls.

Expected algorithmic work changes from O(N) comparisons per lookup to
O(log N). This is a structural improvement, not a measured console frame-time
claim. No benchmark data exists yet.

## Regression coverage

SPRX/tests/pool_growth_checks.py now verifies:
- table asset types are strictly increasing;
- every registered type resolves to its exact table record;
- absent types below, between, and above registered entries return null;
- existing pool-growth behavior and safety assertions remain intact.

The fixture compiles the production GrowthFor() and GrowPool() code with
ASan/UBSan in the diagnostics workflow.

## Scope and safety

- No pool extensions were restored or removed by this optimization.
- No memory budget, growth cap, singleton exclusion, image reserve, or batch
  limit changed.
- No new native hook, detour, thread, or lock was added.
- No converter, Lua, or gameplay behavior changed.

## CI coverage correction

The focused pull-request diagnostics workflow previously omitted the pool
fixture. It now runs pool_growth_checks.py, so the production binary-search
lookup and existing growth invariants are tested on pull requests. The new run
is pending.

## Validation status

- Source change and regression update: committed on
  stability/pool-lookup-hotpath.
- Host CI: pending.
- PS4 native build: not run; project instructions require explicit approval
  before another native build.
- Console benchmark: pending. Compare cold/warm map load, level-link time,
  and frame stalls against the same base commit before assigning a speedup.

## Next review

If CI passes, review the branch diff and merge the source-only optimization.
Then continue the higher-risk catalog double-buffering design and native pool
allocator audit separately. Do not mix them into this change.
