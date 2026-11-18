# Lua mod disable, frontend reload and stock restoration audit — 2026-11-18

## Current source path

1. `ApplyModsNow()` detects a changed selected/loaded mod stack. For an ordinary menu change it queues the frontend shutdown first; it does not close the source-read gate while waiting for `core_frontend`.
2. At the actual frontend apply boundary, immediately before `FreeModsFrom()`, `T7Lua_PrepareModUiUnload()` closes the atomic source-read gate and waits up to 100 ms for in-flight `RetainModLua()` operations. A lookup that arrives while closed returns the immutable rejection rawfile without dereferencing the borrowed name/header/buffer. A timeout reopens the gate and aborts unload.
3. If `FreeModsFrom()` fails, the gate is reopened and the existing zone stack is preserved. After successful removal, loaded-stack and ownership bookkeeping is updated, then the gate is reopened before `AppendMods()` can request replacement Lua.
4. Changed host-session stacks are deferred while old mods remain loaded because the host common-zone operation combines old-zone teardown and new mod loading in one native transaction. A no-common transition is also deferred while old mod sources remain. These paths do not hold the gate across replacement mod loads.
5. `T7Lua_FrontendWillLoad()` advances the frontend generation and resets UI injection/error state.
6. Once the loaded stack no longer contains mods, `T7Maps_UsingMods()` is false and the rawfile hook should return the native stock rawfile unchanged. The existing host retention fixture verifies this isolated pass-through behavior.

## Important lifetime behavior

- The bytecode arena is process-lifetime and append-only. Old revisions are retained so closures cannot point into an unloaded zone or freed rawfile buffer.
- The ownership index is also append-only. A name previously supplied by a mod may remain marked after the mod is disabled; this can conservatively retain later bytecode for the same name.
- The current design does not attempt to reclaim old bytecode on mod disable because no native proof exists that every closure/module reference has been destroyed.
- This is a deliberate safety choice, but it creates a finite 32 MiB/4,096-header retention budget that needs worst-case accounting.

## Unresolved lifecycle gaps

### Frontend path is not proven end-to-end

The host fixture proves that the hook returns the native stock rawfile when its simulated `active` flag is false. The unload-gate tests also pass an actually unmapped source pointer through production `RetainModLua()` while the gate is closed, verify that it is rejected without dereference, and force a held-reader timeout to verify the gate reopens. These tests still do not execute the native HKS module cache, `ReloadFrontend`, actual zone free, frontend generation changes or real UI `require` behavior. We therefore do not yet have console proof that the base Lua module is reloaded rather than served from an old HKS module cache.

### Host-session path differs

When `g_sessionModCount >= 0` and old mods are still loaded, `ApplyModsNow()` now defers a changed host stack until the current session ends. This avoids closing the source-read gate across a combined native transaction that may load replacement mod Lua before returning. If no old mods are loaded, the first host stack can still be loaded through the mode-common transaction. This deferral avoids the immediate source-pointer race but does not prove the HKS module cache or stale-closure behavior for host-session transitions.

### Retention failure recovery is not proven

When validation, budget or allocation fails, `RetainLuaFailure()` returns an immutable valid bytecode chunk that raises a diagnostic Lua error. `T7Lua_OnUiLuaError()` blocks compatibility injection until a later frontend generation. Source comments say mod removal remains available, but there is no production-path test proving that the user can still reach and use the Mods disable controls after this failure.

### Ownership ordering remains unverified

The ownership index is marked from the rawfile link hook and consulted by the HKS rawfile lookup hook. A false-negative ownership decision would return a borrowed rawfile buffer. See `INVESTIGATION-2026-11-18-LUA-OWNERSHIP-PUBLICATION.md`.

## Proposed correction and validation plan

- Preserve process-lifetime retained buffers until closure/module lifetime can be proven; do not free them just because a mod zone unloads.
- Add DEBUG generation/source diagnostics for each relevant Lua lookup: native vs mod rawfile, ownership decision, retained header identity, frontend generation and pthread ID. Keep logs bounded and avoid reading untrusted pointers.
- Build a production lifecycle harness around the actual hook helpers for: mod load, first require, closure retained, disable, zone unload, frontend reload, stock source selected, re-enable, changed revision, and old closure still valid.
- Keep the host-session deferral until a safe native split point is proven. Add console tests for session join/leave, disable/re-enable, and changed host stack without a `core_frontend` generation reset.
- Exercise the fail-closed retention error and prove the stock Mods menu/recovery path remains available; if not, provide a stock-owned recovery route that does not depend on mod Lua.
- Measure worst-case unique Lua bodies, header count, deduplication and map overhead on representative large stacks. Keep the current caps until evidence supports a change.
- Run full host checks and PS4 target build after every source correction; console tests are required for actual HKS module-cache and disable/restore claims.

## Disposition

No arena reclamation or forced HKS cache manipulation is authorized by current evidence. Keep the safe process-lifetime retention model while closing the bounded-lock and ownership-publication hazards. Do not claim complete mod disable/restore validation from host tests alone.


## Update — source-read gate implementation candidate (PR #61)

The source-read race described above now has a concrete implementation candidate in draft PR #61. The gate protects the entire `RetainModLua()` operation, including pointer validation, hashing, deduplication and copying; it uses a single atomic close-bit/reader-count word so an entrant cannot slip between close and drain. The ordinary frontend unload closes only at the free boundary and reopens before new mod Lua is loaded. Host-session and no-common transitions with old source zones are deferred instead of using the gate across mixed teardown/load calls.

The candidate does not reclaim the retained arena, invalidate HKS modules, or prove that old closures are destroyed. The ownership publication race is separately addressed by merged PR #60. Exact-head host/sanitizer checks and a PS4 target build are required before merge; console validation remains required before claiming end-to-end stock Lua restoration.


## Validation result — PR #61 candidate

Exact-head diagnostics and host tests passed, including the production source-pointer rejection and bounded timeout recovery tests. The full PR-time PS4 build and native package checks also passed. Artifact ID `14440233593`, ZIP SHA-256 `d4f93947b38b0cbcd2ba0b38f5e62d1117af6e9530d3ca6c635c67349010d34e`; embedded SPRX SHA-256 `7d6a7a65b55a82e1bbcc61b95ff88cf67f930a6385e023b6aee4353e7f1cf247`. Manifest remains `console_validated: false`, `sony_signed: false`. The source-read barrier is build-verified; native HKS cache behavior and real console disable/restore remain unverified.
