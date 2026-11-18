# Mod Lua ownership index publication and lookup ordering — 2026-11-18

## Finding

The ownership index is populated by `NoteUiFile()`, called from `LinkXAsset_h()` for linked rawfile assets in a mod zone. The rawfile lookup hook later calls `T7Maps_NeedsLuaRetention(name)`, which asks `g_modLuaOwnership.MayContain(name)` whether the name belongs to a mod.

`T7LuaOwnership::Index::Mark()` currently sets four Bloom bits first, then attempts to publish the exact 64-bit key into an open-addressed atomic key table. `MayContain()` searches the exact-key table and only consults Bloom bits after the table's overflow flag is set.

If `Mark(name)` and `MayContain(name)` execute concurrently before overflow, the lookup can observe the slot as empty before the exact key is published and return false even though the Bloom bits are already being populated. The operations are atomic and do not cause C++ undefined behavior, but the result can be a false negative during publication. A false negative means `RetainModLua()` may return the borrowed engine rawfile rather than a stable retained copy.

Separately, the exact ordering between rawfile `LinkXAsset_h`/ownership marking and the HKS `FindXAsset` lookup has not been demonstrated from a matching executable trace. Normal zone loading may link assets before the UI VM requests them, but the source-only tests do not prove that order across worker/UI threads.

## Impact and confidence

- The two-stage Mark/MayContain publication window is directly visible in the header.
- Whether the engine can issue the corresponding lookup during that window depends on native call ordering and pthread concurrency that have not yet been captured.
- The ownership-index test currently runs concurrent writers, then performs reads after all writers join. It does not query the same names concurrently with publication.

This is a high-priority lifetime-safety gap to close, not a proven explanation for a specific crash.

## Proposed correction

1. Establish the real order and thread identities for mod rawfile linking, `NoteUiFile`, HKS rawfile lookup and `RetainModLua`. Use bounded DEBUG diagnostics with asset name/hash, zone context, pthread ID and publication generation.
2. Make in-progress exact-key publication visible to readers. A reserved per-slot pending-key sentinel (with a masked hash) can be published before the final key; `MayContain` must treat a matching pending key as owned.
3. Preserve fail-closed Bloom behavior when the exact table is saturated. Ensure a concurrent mark during overflow cannot create a transient false negative.
4. If evidence shows lookup can precede `NoteUiFile` entirely, mark ownership earlier in the zone load path or use validated current-zone context for the retention decision. Do not simply retain every stock Lua asset.
5. Add concurrent reader/writer regression coverage and test saturation, duplicate names, case/slash normalization and collision behavior.

## Required validation

- A deterministic production-helper test for a reader observing an in-progress key publication.
- ThreadSanitizer on concurrent Mark/MayContain readers and writers.
- A matching-build DEBUG trace proving link/mark/lookup ordering and pthread identities.
- Full host workflows and a fresh PS4 target build.
- Console validation remains separate.


## Revised correction design before implementation — 2026-11-18

The first proposed pending-key sentinel would close the exact-key insertion window but would not by itself cover the saturated Bloom-only path. The implementation will instead bracket every `Mark()` with an atomic in-flight publication count and completion generation:

- `Mark()` increments the in-flight count before hashing or publishing any key/Bloom bits and decrements it only after the complete update; each completion advances a generation.
- `MayContain()` returns conservative true while any publication is in flight. Otherwise it snapshots the generation, performs the exact-key/Bloom lookup, and rechecks both generation and in-flight count. If a writer overlapped the lookup, it returns true rather than a possible false negative.
- This deliberately permits a brief false positive for an unrelated Lua name while a mod Lua name is being marked. The mark operation is bounded and only applies to Lua rawfiles; safety is preferred over returning a borrowed buffer during publication.
- The regression will hold a writer in the publication phase using a long test-only name, wait until the production in-flight counter is visible, and assert the reader fails closed. It will also run concurrent Mark/MayContain activity under ThreadSanitizer.

This closes only the in-flight publication window. It does not prove that native HKS lookup can never occur before `NoteUiFile()` is first called; matching-build link/lookup order and pthread IDs still require evidence.
