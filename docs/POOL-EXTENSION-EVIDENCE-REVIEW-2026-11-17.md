# Pool-extension evidence review and next stability work

Updated: 2026-11-17

## Executive conclusion

The previous pool exclusions were conservative, not a verified diagnosis of
the reported crash. The supplied zm_ccube excerpt contains no allocator
failure, pool-out event, exception, or fatal PC. It only shows three one-entry
pools at 1/1 before the level-load request.

The pool policy should therefore be treated as provisional. The user's report
that this fork performed faster than Joker's build is important evidence to
preserve: pool extension may have reduced repeated pool pressure or avoided a
later exhaustion path. We do not yet have an A/B benchmark that attributes the
speed difference to pool growth.

## What the current hook actually observes

In `SPRX/t7_maps.cpp`, `LinkXAsset_h` calls `GrowPool(type)` before invoking
the original `LinkXAsset` function. `GrowPool` only sees the pool descriptor
and whether its free-list pointer is null. It does not intercept the native
asset-pool allocator's failure return.

Consequently, an empty free list observed at this hook is evidence that the
pool is exhausted at that instant, but it is not proof that a native allocation
has failed. The incoming asset has already reached the link hook. Growth here
is a pre-emptive attempt to provide free entries for subsequent assets, not a
strict "grow only after failed allocation" implementation.

Do not claim the current hook meets a failed-allocation-only policy. To do that
safely, first identify the PS4 allocator function, its return/error semantics,
all call sites, and its synchronization/thread contract. Then add a failure
event that records type, pool descriptor, requested allocation, and caller
before considering a retry or growth.

## Pool-by-pool evidence

### COM World (type 13) and Game World (type 14)

The previous table used 136-byte and 80-byte entries with an initial limit of
2. They were removed because upstream BOIII documentation warns that COM
World and Game World are accessed through engine-global references and that
reallocating those pools is unsafe.

The COD Engine Research Black Ops 3 public-beta table independently lists
COM World and Game World with pool count 2. That corroborates their small
fixed baseline, but it does not prove the final PS4 retail layout or erase the
direct-reference warning. Keep them excluded from automatic growth unless
the supported PS4 binary proves every reference and allocation path is safe.

### snddriverglobals (type 37)

The previous table used a 120-byte entry and limit 1. The COD Engine Research
Black Ops 3 public-beta table also lists snddriverglobals with pool count 1.
This is meaningful corroboration that it is intended as a singleton category.
Keep it excluded; growing a one-instance global object table is not a safe
general-purpose capacity optimization.

### bulletpenetration (type 72) and locdmgtable (type 73)

The previous table used 488-byte and 96-byte entries, each with limit 1.
The supplied log shows each at 1/1. I did not find authoritative final-build
PS4 evidence establishing that either category supports multiple entries.
Keep them excluded for now, but label their status as unverified rather than
proven singleton types. Their native constructors, consumers, and allocator
call sites need reverse-engineering before any extension is reconsidered.

### Other previously eligible pools

The exclusions did not remove the existing growth paths for ordinary
allowlisted pools such as material, scriptparsetree, rawfile, localize, and
image. The current policy still has a 64 MiB plugin-owned budget, a 1 MiB
synchronous batch limit, per-pool growth caps, and an image-specific reserve.
Those controls limit our allocations but do not prove synchronization with
the native allocator.

## Confirmed hot-path optimization (source branch)

The pool allowlist is immutable and already strictly sorted by asset type, but
GrowthFor() previously scanned the complete table for every LinkXAsset_h
callback. Since the hook runs for every linked asset, this added an avoidable
O(N) lookup to the database-worker hot path, including for asset types that
are not eligible for growth.

The stability/pool-lookup-hotpath branch replaces the scan with a lower-bound
binary search. It preserves the exact allowlist and pool-growth policy; no
pool capacities, allocations, locks, or engine calls change. The production
host fixture now checks strict ordering, resolves every table entry to its
exact record, and rejects absent types below, between, and above the table.
This is a provable reduction in comparisons (O(N) to O(log N)); it has not yet
been benchmarked on console, so no frame-time percentage is claimed. Host CI
is pending. No native build or console test has been performed for this branch.

## Confirmed diagnostic data race corrected

T7Log_PoolOut() is called from LinkXAsset_h(), which runs on database
workers. Its static per-type told[] latch was a plain bool array read and
written without synchronization. Concurrent calls therefore had a C++ data
race and could emit duplicate pool-out snapshots. The latch now uses
std::atomic<bool>::exchange() after confirming the pool is genuinely empty,
so exactly one worker claims the once-only diagnostic. A host stress fixture
extracts and compiles the production function, starts 32 concurrent workers,
and verifies exactly one diagnostic/snapshot for an exhausted type while
ignoring free, singleton, zero-limit and invalid types. This corrects the
plugin-owned diagnostic race; it does not synchronize diagnostic reads with
the engine's native allocator or establish a failed allocation.

## CI coverage gap found and corrected

The dedicated pull-request SPRX diagnostics workflow did not previously run
pool_growth_checks.py, even though the test was included in the full main-branch
host suite. The workflow now explicitly invokes the fixture so changes to the
pool-growth lookup and free-list logic receive focused PR validation. The
workflow run for this change is pending.

## Stability/performance work order

1. Keep the bounded rawfile/script-name reads. They remove unsafe unbounded
   reads from the asset-link path without changing engine pool capacities.
2. Keep COM/Game World and snddriverglobals excluded pending binary-level
   proof. Keep bulletpenetration/locdmgtable excluded pending their own
   allocator/consumer audit.
3. Add per-pool telemetry before changing capacity policy: type/name, entry
   size, initial/current limit, used count, free-list pointer state, singleton
   flag, growth attempts/success/failure, bytes mapped, caller/zone, and
   timestamp. Use fixed-size counters/ring storage and emit summaries outside
   the hot path.
4. Reverse-engineer the PS4 native allocator and determine whether the empty
   free-list observation happens before or after its failure path. Do not add a
   hook or shared lock until the call graph and ABI are verified.
5. Compare the custom map FF/FD pair, XPAK list, and dependency closure against
   a known-working map. A file-open success alone does not validate the
   fastfile's internal dependency closure.
6. Extend the lighting trace to preserve a compact identity/state history for
   each active blob across samples: slot, category, state, generation,
   wanted-generation match, last-wanted tick, item identifier/hash, and
   stream-pool free space. One missing blob at an early checkpoint is not a
   failure; a stable unresolved identity across a stalled load is stronger
   evidence.
7. Add phase diagnostics around zone load/unload and asset linking: thread
   identity, zone name, phase, call depth, elapsed time, and first fatal
   exception PC/register snapshot where the platform exposes it. Keep all
   memory reads guarded and bounded.

## A/B benchmark plan

To establish whether pool extensions explain the speed advantage, produce
two otherwise identical builds from the same source revision:

- Control: current restricted allowlist.
- Variant: re-enable only a pool whose native contract has been verified;
  never enable COM/Game World or singleton candidates just to create a test.

Use the same console, game build, map files, mod stack, and cold/warm sequence.
Record load-to-gameplay time, time spent in streaming wait, per-pool high-water
marks, mmap/growth counts and bytes, memory high-water, frame-time/stall
samples, and crashes. Repeat each case enough times to separate normal
variance from a real change. Do not infer performance from a single run.

## CI verification

Workflow run
https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44168194622
completed successfully: host regression job passed, PS4 SPRX build and native
artifact validation passed, and the overall workflow completed successfully.
The dedicated diagnostics run
https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44168047271
also passed. These results verify source/host checks and the target artifact;
they do not establish console stability or prove the crash is fixed.

## Sources

- BOIII pool documentation and its fixed-global-reference caveats:
  https://github.com/Ezz-lol/boiii-free
- COD Engine Research, Black Ops 3 public-beta pool table (not a final PS4
  retail specification):
  https://codresearch.dev/index.php/Category:Assets
- Repository investigation:
  `docs/INVESTIGATION-2026-11-17-ZM-CCUBE-CRASH.md`
