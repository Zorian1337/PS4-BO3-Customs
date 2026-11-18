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

`SPRX/xasset_reserve_index.hpp` now contains a small pure helper for the one arithmetic rule that can be independently tested from the issue evidence: converting an entry address to a positive signed-32-bit index and proving the exact address round-trip. A second helper validates the first and last indices of a complete fixed-stride page, which bounds every entry between them. The host test covers all 32 address residues, sparse addresses above 4 GiB, the signed-index boundary, page ranges that cross that boundary, misalignment, zero stride, overflow, and unchanged outputs on rejection.

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
