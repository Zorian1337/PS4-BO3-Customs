# XAssetEntry reserve-index safety contract

Issue: [#30 — Bulk mod activation exhausts shared XAssetEntry registry](https://github.com/Zorian1337/PS4-BO3-Customs/issues/30)

## Problem

A fresh dev.66 nine-mod activation exhausted the shared 152,576-entry XAssetEntry registry and the Database thread aborted with the native allocation fatal. Per-type asset-pool growth does not expand this separate shared registry.

The issue records the dev.67 design constraints: preserve every original entry address, retain the native hash modulus and allocation/free/unload paths, and append reserve pages only when the native free list is empty. Native chain links are positive signed-32-bit indices, so every reserve entry must encode and decode to exactly the same address. The candidate design also requires matching 32-byte address residue, bounded reserve capacity, validated mapping results, and a fail-closed path.

## Proposed correction

1. Recover the supported build's exact allocator boundary, native table base, entry layout, free-list/index consumers, hook ABI and instruction fingerprints.
2. Keep the original table and all existing entry addresses fixed. Never relocate the live table or overwrite adjacent globals.
3. Allocate reserve pages only at the native allocator boundary after the existing free list is exhausted. Do not bypass native allocation/free/unload.
4. Before publishing a page, validate the entire mapping: address residue, alignment, positive signed-32 index round-trip for every node, readable/writable span, mapping success, and reserve-cap arithmetic.
5. Publish only fully validated pages; on any failure, unmap the unpublished page, stop retrying after the configured cap/failure, and preserve the native fatal behavior.
6. Add production-body tests for the original fast path, empty-list refill, mapping failure, all alignment residues, index limits, free/reuse, cap, ABI forwarding and fingerprint rejection.
7. Validate a fresh-process nine-mod reproduction before closing the issue.

Alternatives rejected: relocating the original registry invalidates outstanding entry pointers; extending its static array in place can overwrite adjacent globals; increasing unrelated per-type pools cannot fix this shared registry; dropping or replacing assets would silently break requested content.

## Work started: pure index arithmetic

`SPRX/xasset_reserve_index.hpp` now contains a small pure helper for the one arithmetic rule that can be independently tested from the issue evidence: converting an entry address to a positive signed-32-bit index and proving the exact address round-trip. A second helper validates the first and last indices of a complete fixed-stride page, which bounds every entry between them. A third helper selects an interior page start from a returned mapping while preserving the native table's modulo-stride residue; it checks that the entire requested page fits in the original mapping and leaves all outputs unchanged on failure. The host test covers all 32 address residues, sparse addresses above 4 GiB, the signed-index boundary, page ranges that cross that boundary, every mapping/table residue combination, insufficient mapping spans, misalignment, zero stride, overflow, and unchanged outputs on rejection.

This is deliberately groundwork, not the dev.67 allocator fix. It does not map memory, inspect engine structures, publish entries, or claim to validate the native ABI. Do not wire it into a hook until the missing native contracts and matching build fingerprints are independently recovered.


## Public-source layout facts verified

The inspected public `SPRX/t7_maps.cpp` currently defines the following
build-relative values:

- Hash bucket table: `kAssetHash = 0x57E9710`
- Hash bucket count: `kAssetHashSize = 152576`
- Entry table base: `kAssetEntries = 0x587E710`
- Entry stride: `kAssetEntrySize = 32`
- In-use byte offset: `kAssetEntryInUse = 17`
- Next-chain index offset: `kAssetEntryNext = 20`

The existing `ClearAssetsInUse()` walks each bucket as a `uint32_t` index and
loads the next index from the entry at `entries + 32 * index + 20`. This
confirms the public table base/stride and one index consumer used by this
repository. It does **not** identify the native allocator boundary, free-list
head/return path, all native index consumers, complete entry ABI, or matching
executable fingerprints. The values are relative to the supported module base
and must not be treated as universally valid across BO3 builds.


## Source-call-path audit (2026-11-18)

A second pass over the full published `SPRX/t7_maps.cpp` source narrowed
what can be stated safely:

- `LinkXAsset_h` is a link-stage hook at the build-relative site
`kLinkXAsset = 0x857A10`. It calls `GrowPool(assetType)` and
`T7Log_PoolOut(assetType)` before forwarding the original link call.
It does **not** receive an XAssetEntry allocation request/result and is not
the shared XAssetEntry allocator boundary. Reusing it for reserve-page
publication would therefore be an unproven timing/ABI assumption.
- The hook is installed only after the existing LinkXAsset and ZonePriority
byte signatures match. Those signatures validate the link hook's supported
build shape; they do not fingerprint or validate a different allocator
function.
- `ClearAssetsInUse()` is the one explicit XAssetEntry-table consumer
found in the published SPRX source. It reads bucket heads from
`g_base + 0x57E9710` and walks the table at
`g_base + 0x587E710` using a 32-byte stride, reading the next-chain
field at offset 20 and clearing the in-use byte at offset 17. Its bucket and
next fields are loaded as `uint32_t`.
- That unsigned load is an important qualification: the dev.67 design notes
specify positive signed-32-bit indices, and the helper now tests that proposed
rule in both encode and decode directions. The public SPRX consumer alone does
not prove that every native consumer treats the high bit as invalid. The
signed-positive rule remains a native-contract requirement to verify, not a
fact established solely by this source.
- No published SPRX function found in this pass exposes the native XAssetEntry
free-list head, allocation failure return, free/recycle path, or all native
index consumers. The source has no `DB_AssetPoolAlloc` implementation;
the existing pool allocator and the XAssetEntry registry are separate systems.

### Updated implementation gate

Do not add an allocator detour based only on the LinkXAsset signature. Before
runtime code can be considered safe, the supported executable analysis must
supply all of the following as one coherent build-specific evidence set:

1. Allocator entry address, complete prologue/instruction fingerprint, exact
   argument and return ABI, and every call site that can allocate entries.
2. Free-list head representation, empty sentinel, index signedness, index
   base/stride, full entry field layout, and the native free/reuse path.
3. Every native consumer of bucket and chain indices, including bounds and
   whether the index is ever used in pointer arithmetic before validation.
4. The allocator's synchronization/lock contract and whether allocation can
   re-enter during zone load/unload or callbacks.
5. The exact mapping API semantics, address-residue strategy, maximum reserve
   count, failure cleanup, and safe publication ordering for the supported
   PS4 process.
6. A build fingerprint that is checked independently from the existing
   LinkXAsset/ZonePriority signatures.

The current helper is intentionally a standalone arithmetic contract test.
It is not called by production code until the items above are verified. The
correct next step is native call-graph recovery, not a guessed hook or a
larger reserve constant.


## External reverse-engineering references checked

The public COD Engine Research LoadContext page describes the shared global
registry concept, but its detailed evidence is explicitly PS3-oriented. Its
illustrative XAssetEntry has 16-bit next-hash and override indices at offsets
0x0C/0x0E. That does not match this repository's PS4 source observations:
32-byte stride and a 32-bit next-chain read at offset 20. It is therefore useful
only as architectural context; its layout, allocator addresses, lock behavior,
and function contracts must not be transplanted into this PS4 implementation.

Reference: https://codresearch.dev/index.php/Category:LoadContext
The public page identifies the PS3 DB_LoadXAssets function and labels its
field evidence as PS3-proven; it does not provide the supported PS4 retail
allocator's address, signature, free-list representation, or synchronization
contract. This reinforces the requirement for matching-PS4 executable
analysis rather than borrowing a neighboring platform's structure.


## Supported-build executable allocator audit (2026-11-18)

The saved PS4 retail executable analysis now exposes the native allocation and release routines. This is a substantial improvement over the public SPRX-only call-path audit, but it still does not justify a reserve-page hook.

Observed in the analyzed executable image (Ghidra decompiler pseudocode; addresses are image-relative):

- `FUN_008583b0` at `0x8583B0` is a native XAssetEntry allocation routine. It pops an entry from the global free-list head `DAT_05d26718`, advances that head through the entry's first pointer-sized word, writes the requested asset type, and initializes fields at offsets `+0x10`, `+0x18`, and `+0x11`. If the global free list is empty, it logs the existing fatal message to increase `XASSET_ENTRY_POOL_SIZE`; it does not request a reserve page.
- The same allocator also maintains a separate per-type object/free-list pool under `DAT_037c83F0` / `DAT_037c8408`. That is not the global XAssetEntry free list and must not be confused with it.
- `FUN_008587B0` at `0x8587B0` is a native entry/object swap/relink routine. It takes two entry-like pointers and flags, dispatches type-specific work, copies/swaps payloads, and may adjust metadata. It is not a reserve allocator.
- `FUN_00858CB0` at `0x858CB0` performs type-specific release/cleanup and pushes objects into per-type free lists. The global XAssetEntry free-list push is visible separately in the larger unload/release paths.
- The global entry storage begins at `DAT_0587E710`, with 0x20-byte stride. Hash bucket heads begin at `DAT_057E9710`; the native traversal loops over `0x25400` (152,576) buckets. The entry's primary next-chain index is at offset `0x14`; an additional chain at offset `0x1C` is also traversed in several paths. A second index at offset `0x00` is used as the entry's global free-list link when the entry is unused.
- Native consumers use expressions equivalent to `entryBase + (uint32_index * 0x20)` and follow links through offsets `0x14` and `0x1C`. The decompiler shows multiple native loops over the fixed 152,576-bucket table, including lookup, unload, enumeration and rebuild paths. The public SPRX `ClearAssetsInUse()` is only one consumer.
- Global pool exhaustion accounting is maintained at `DAT_05D26720` / `DAT_05D26724`; the native fatal is reached when `DAT_05D26718` is null. This is direct evidence that merely enlarging unrelated type-specific pools cannot solve the reported exhaustion.

### Consequence for the reserve-page proposal

The native allocator ABI and primary global free-list representation are now partially recovered, but reserve-page integration is **still blocked**. The native free-list head is a pointer, while hash chains and other traversal structures store 32-bit indices. The decompilation shows fixed bucket counts and multiple chain consumers, but does not yet prove:

1. the exact base-to-index encoding formula and whether every consumer validates the high bit, sign, upper bound and reserved sentinels before pointer arithmetic;
2. whether a newly mapped page can be represented by every native consumer, including the second chain at offset `0x1C`, global free-list links at offset `0x00`, hash bucket rebuilds, and any hidden consumers outside the recovered function set;
3. whether the page can be placed at a compatible address/residue and remain mapped for the entire lifetime of every pointer/reference;
4. the allocator's complete lock/reentrancy contract. The decompilation shows lock/refcount machinery around surrounding operations, but does not yet prove that every allocator/free-list access is protected by one common lock;
5. an independent executable fingerprint and verified PS4 mapping/unmapping API contract for the exact target build.

**Do not wire the reserve-page helper into `FUN_008583B0` yet.** A hook that only changes `DAT_05D26718` can make allocation appear to succeed while native hash, secondary-chain, unload, or rebuild consumers still calculate invalid addresses. Keep the native fatal path intact until the full index mapping and all consumers are proven.

### Required next reverse-engineering pass

- Recover the full callers and cross-references for `FUN_008583B0`, `FUN_008587B0`, and `FUN_00858CB0`, including every write to `DAT_05D26718`, every initialization of the entry table, and all reads of offsets `0x00`, `0x14`, and `0x1C`.
- Enumerate all native references to `DAT_0587E710`, `DAT_057E9710`, and the global free-list head, then classify each as allocation, free, hash lookup, secondary-chain traversal, unload, enumeration or rebuild.
- Recover the exact index mapping from original entry addresses to indices, including sentinel semantics and maximum representable entry index.
- Identify the lock acquired by the allocator itself (if any), its callers and whether it covers free-list publication and all chain modifications.
- Only after these checks, add a production-body host fixture for the real allocator fast path, empty-list failure, reserve-page publication, free/reuse, concurrent allocation/free, mapping failure and ABI passthrough.

This section is based on the saved matching PS4 executable analysis, not original source. Ghidra pseudocode is evidence for the observed control/data flow but is not a substitute for validating instruction bytes, calling conventions, runtime addresses and synchronization on the exact retail build.
