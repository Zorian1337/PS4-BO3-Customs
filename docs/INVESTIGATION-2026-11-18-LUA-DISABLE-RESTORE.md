# Lua mod disable, frontend reload and stock restoration audit — 2026-11-18

## Current source path

1. `ApplyModsNow()` detects a changed selected/loaded mod stack. When loaded mods exist, it calls `T7Lua_PrepareModUiUnload()`.
2. `T7Lua_PrepareModUiUnload()` currently logs the retained-bytecode count, byte count, mapped budget and failures, then returns true. It deliberately does not free the retention arena or invalidate old bytecode because existing Lua closures may still reference it.
3. For a menu/frontend stack change outside a host session, `ApplyModsNow()` queues the change, calls `ReloadFrontend()`, and waits for the next `core_frontend` load.
4. `ApplyModsAtFrontend()` applies the queued unload before the original `core_frontend` zone load. It frees removed mod zones, updates the loaded stack and removes mod ownership claims.
5. `T7Lua_FrontendWillLoad()` advances the frontend generation and resets UI injection/error state.
6. Once the loaded stack no longer contains mods, `T7Maps_UsingMods()` is false and the rawfile hook should return the native stock rawfile unchanged. The existing host retention fixture verifies this isolated pass-through behavior.

## Important lifetime behavior

- The bytecode arena is process-lifetime and append-only. Old revisions are retained so closures cannot point into an unloaded zone or freed rawfile buffer.
- The ownership index is also append-only. A name previously supplied by a mod may remain marked after the mod is disabled; this can conservatively retain later bytecode for the same name.
- The current design does not attempt to reclaim old bytecode on mod disable because no native proof exists that every closure/module reference has been destroyed.
- This is a deliberate safety choice, but it creates a finite 32 MiB/4,096-header retention budget that needs worst-case accounting.

## Unresolved lifecycle gaps

### Frontend path is not proven end-to-end

The host fixture proves that the hook returns the native stock rawfile when its simulated `active` flag is false. It does not execute the native HKS module cache, `ReloadFrontend`, actual zone free, frontend generation changes or real UI `require` behavior. We therefore do not yet have console proof that the base Lua module is reloaded rather than served from an old HKS module cache.

### Host-session path differs

When `g_sessionModCount >= 0`, `ApplyModsNow()` uses a fresh mode-common load transaction and does not take the ordinary frontend-shutdown/reload branch. `T7Lua_FrontendWillLoad()` is therefore not necessarily called for this stack change. We need to verify whether existing HKS module references remain active, whether the new mod stack is reflected in subsequent rawfile lookups, and whether stale closures remain safe.

### Retention failure recovery is not proven

When validation, budget or allocation fails, `RetainLuaFailure()` returns an immutable valid bytecode chunk that raises a diagnostic Lua error. `T7Lua_OnUiLuaError()` blocks compatibility injection until a later frontend generation. Source comments say mod removal remains available, but there is no production-path test proving that the user can still reach and use the Mods disable controls after this failure.

### Ownership ordering remains unverified

The ownership index is marked from the rawfile link hook and consulted by the HKS rawfile lookup hook. A false-negative ownership decision would return a borrowed rawfile buffer. See `INVESTIGATION-2026-11-18-LUA-OWNERSHIP-PUBLICATION.md`.

## Proposed correction and validation plan

- Preserve process-lifetime retained buffers until closure/module lifetime can be proven; do not free them just because a mod zone unloads.
- Add DEBUG generation/source diagnostics for each relevant Lua lookup: native vs mod rawfile, ownership decision, retained header identity, frontend generation and pthread ID. Keep logs bounded and avoid reading untrusted pointers.
- Build a production lifecycle harness around the actual hook helpers for: mod load, first require, closure retained, disable, zone unload, frontend reload, stock source selected, re-enable, changed revision, and old closure still valid.
- Add a separate host-session stack-change test for the path that does not reload `core_frontend`.
- Exercise the fail-closed retention error and prove the stock Mods menu/recovery path remains available; if not, provide a stock-owned recovery route that does not depend on mod Lua.
- Measure worst-case unique Lua bodies, header count, deduplication and map overhead on representative large stacks. Keep the current caps until evidence supports a change.
- Run full host checks and PS4 target build after every source correction; console tests are required for actual HKS module-cache and disable/restore claims.

## Disposition

No arena reclamation or forced HKS cache manipulation is authorized by current evidence. Keep the safe process-lifetime retention model while closing the bounded-lock and ownership-publication hazards. Do not claim complete mod disable/restore validation from host tests alone.
