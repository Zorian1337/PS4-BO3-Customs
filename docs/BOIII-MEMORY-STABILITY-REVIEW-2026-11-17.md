# BOIII memory/stability research and PS4 implementation review

Date: 2026-11-17

## Scope

Compared the PS4 fork Zorian1337/PS4-BO3-Customs, Joker's public
ItsJokerZz/PS4-BO3-Customs implementation, and the public Ezz-lol/boiii-free
client. BOIII was used strictly as research material. Its Windows x64 client,
offsets, memory APIs, allocator replacement, and launcher behavior are not
portable to the PS4 SPRX.

BOIII source inspected at commit
5aa7fac39c51438d9c1e312b99534b7fef3bff44, including:

- docs/asset-pool.md
- src/client/component/asset_limits.cpp
- src/client/game/impl/db/db.cpp
- src/client/game/structs/db/xasset/pool.hpp

Our source inspected on main, including SPRX/t7_maps.cpp,
SPRX/tests/pool_growth_checks.py, SPRX/DIAGNOSTICS.md, and the existing
frame-work/upstream stability reports.

## Key BOIII findings

### Pool expansion is not universally safe

BOIII documents that:

- GFX World, COM World, and Game World are effectively limited to the active
  world and a loading world. Engine code accesses their statically allocated
  storage directly, so relocating/reallocating these pools can break global
  references.
- GFX Image has direct/static access and fixed-size assumptions in streaming
  code.
- XModelMesh has hard-coded pool-size assumptions in engine call sites.

This is more useful than the general claim that BOIII supports expansion:
the project's own documentation explicitly limits where reallocation is safe.

### BOIII's allocator is a full replacement, not a drop-in PS4 technique

BOIII's reallocate_asset_pool() allocates a replacement array with calloc,
copies currently allocated entries, rebuilds the free list, updates the pool
descriptor, and may free a prior extended allocation. It serializes
reallocation with a mutex. Its replacement DB_AssetPoolAlloc_Impl() uses a
separate allocation mutex so native asset allocations cannot race with pool
reallocation.

That design relies on BOIII's Windows process, allocator, engine function
replacement, and memory ownership. Porting it to PS4 would require proving the
equivalent engine ABI, allocation ownership, all direct pool references, and
the correct synchronization boundary. It must not be copied into this SPRX.

### BOIII configuration defaults are not proof of safe automatic growth

BOIII's default list includes several pools at their original sizes, including
one-entry asset categories. Those defaults do not mean the pools should be
automatically expanded whenever full. Its configuration path only applies
requested sizes greater than the current capacity and its documented caveats
still apply.

## Comparison with our current implementation

Our fork uses append-only overflow blocks linked into the engine free list
instead of relocating the original pool. That avoids moving the original
allocation, but it does not make every asset type safe to grow.

Current safeguards retained:

- immutable linear growth-table lookup (no lazily published mutable index);
- a serialized growth operation;
- at most 1 MiB mapped per synchronous growth batch;
- a shared 64 MiB plugin-owned allocation ceiling;
- bounded image overflow reserve (25% of its tracked baseline), with layout
  validation;
- failure latching to prevent repeated mmap storms;
- free-list and budget regression coverage.

These limits bound our own additional allocations. They do not represent
available system RAM, do not reclaim native engine allocations, and do not
prove the native allocator is synchronized with our growth hook.

## Implemented changes from this comparison

### 1. Exclude COM World and Game World from automatic growth

BOIII's documented direct-global access caveat applies to COM World and Game
World. Our growth table previously included types 13 and 14. They are now
excluded. GFX World (type 16) and XModelMesh (type 5) were already excluded.
We do not relocate these engine-owned world pools.

### 2. Exclude the three one-entry pools seen in the crash log

The supplied pre-level snapshot showed:

- snddriverglobals: 1/1, single=0, no free entry;
- bulletpenetration: 1/1, single=0, no free entry;
- locdmgtable: 1/1, single=0, no free entry.

The fork's minimum extra-capacity policy could otherwise append up to 64
entries to any exhausted tracked pool, including these three. Their engine
allocation contracts and whether they can legitimately contain multiple
assets have not been established. They are now excluded from automatic growth.
A full one-entry snapshot is treated as a diagnostic observation, not a
request to allocate more memory.

This is a conservative compatibility choice, not proof that these pools are
formally singleton types. If future evidence demonstrates a map requires
multiple instances and the engine handles them safely, they can be reconsidered
individually with a dedicated test.

### 3. Explicit singleton and exclusion regression coverage

The production pool-growth fixture now verifies:

- types 13 and 14 are not eligible for growth;
- types 37, 72 and 73 are not eligible for growth;
- an otherwise eligible pool marked single=1 is not grown;
- those cases perform no mmap and do not mutate the free-list pointer or limit.

### 4. Correct ScriptBase output-capacity validation

The bounded script-name reader previously used a conservative capacity check
that compared the full source filename length plus four against the output
buffer. The required output is only the filename stem plus its NUL terminator.
The check now validates the actual output length, allowing valid short names
with appropriately sized output buffers while still rejecting undersized
buffers. Regression coverage includes both cases.

### 5. Retain bounded rawfile and script-name reads

The existing changes to NoteLevelLua() and ScriptBase() copy engine-owned
names byte-by-byte only after readability checks, stop at a bounded local
capacity, and reject unreadable/unterminated names. This prevents an unbounded
strlen() from crossing a page boundary during asset linking. It is a real
memory-safety hardening item, but not proven to be the cause of the reported
zm_ccube crash.

## Important remaining risk: synchronization with native allocation

BOIII's source explicitly serializes its replacement asset allocator with
pool reallocation. Our g_poolGrowthLock serializes concurrent SPRX growth
operations, but the current source does not establish that the engine's
native asset-pool allocation path takes the same lock.

We must not assume these are equivalent. A future change that wraps or
replaces the native allocator could introduce deadlocks, change engine
threading, or break target ABI if done without the exact PS4 function
signature and call graph. This is a high-priority research task, not a safe
blind patch. Until that contract is established, keep the existing append-only
approach, strict per-type allowlist, and bounded memory ceiling; do not add
world/image/model-mesh types.

## Findings deliberately not ported

- No BOIII Windows client hooks, PE offsets, launcher, Steam integration,
  asset-pool reallocation routine, or Windows memory APIs.
- No blanket doubling of all asset pools.
- No increase to the 64 MiB plugin growth ceiling.
- No expansion of image/world/model-mesh pools.
- No forced completion of pending lighting blobs or bypass of streaming
  dependency checks.
- No global script compiler or VM rewrite based only on PC behavior.

## Verification status

The source and regression changes are committed together with this report.
The GitHub diagnostics workflow should compile and run the pool and bounded
name fixtures. The PS4 target build and console reproduction still need
successful workflow/console evidence before calling the crash fixed.
