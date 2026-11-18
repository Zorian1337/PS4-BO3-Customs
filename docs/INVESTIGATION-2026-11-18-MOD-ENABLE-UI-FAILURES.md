# Frontend mod-enable failures: Lua arena exhaustion and UI recovery — 2026-11-18

## Scope and source baseline

This investigation covers the supplied 00:47, 03:17 and DS4C UI captures, the current `main` implementations in `SPRX/t7_lua.cpp` and `SPRX/t7_maps.cpp`, and the merged Lua ownership/unload protections from PRs #60 and #61. No raw console log, mod payload, executable or private content is copied into this repository.

## Incident A — normal frontend transition, then retention failure

### Direct evidence

- At 00:47.596 the mod manager reports that changes wait for the current frontend to shut down.
- At 00:47.654 the server is shut down with `EXE_SERVERKILLED` and zero script runtime errors. The call is made by the mod/frontend reload path (`ReloadFrontend` calls the verified `KillServer` entry after queuing the change).
- The old zones unload, the queued two-mod stack is selected, and the new `core_frontend` load is requested. The transition trace reports three waiting zones and a pending reload.
- The UI snapshot is explicitly busy during the zone request. That is not evidence of a UI-state corruption by itself.

### Assessment

The server shutdown and zone reload are expected parts of the current frontend-reload design, not the crash. The queue/wait behavior should be preserved. Do not remove the reload or suppress `EXE_SERVERKILLED` to hide this transition.

## Incident B — Lua bytecode arena mapping failure

### Direct evidence

- At 03:17.512 the retention layer rejects `ui/uieditor/widgets/StartMenu/StartMenu_Media.lua` before loading borrowed bytecode because the dedicated arena allocation failed.
- The arena had mapped 27,688,960 bytes; the next mapping request was 262,144 bytes and returned `0x8002000C`.
- `0x8002000C` is `SCE_KERNEL_ERROR_ENOMEM` (cannot allocate memory), not a Lua syntax/bytecode validation error. Reference: [PS4 Developer Wiki — CE error codes](https://www.psdevwiki.com/ps4/CE).
- The next log line is the same failed request; then the plugin deliberately raises UI Error 81928 rather than return an unsafe borrowed pointer.
- UI Error 21544 (`Tried to add nonexistent menu main`) follows the retention error. The frontend is therefore already in a partial menu-build state when the missing-menu error appears.
- The trace later reports successful main-menu registration, retries compatibility injection, observes a new `core_frontend` UI state, and continues with map/lobby UI hooks. The mod manager reports that menus did not build with the selected third-party mod and preserves the selected stack.
- The earlier transition trace records 240 conservative active-zone fallback lookups. This is a count of fallback decisions, not a byte count and not proof that all 240 created unique retained bodies.

### Source-level allocator finding

`AllocateRetainedLua()` walks only the current head block (`g_retainedLuaBlocks`). When the head cannot fit the next allocation, it maps another block even if an older block in the append-only block list still has sufficient unused tail space. Because old blocks are never reclaimed and the allocator does not search them, usable mapped capacity can be stranded. This is a concrete source-level fragmentation defect.

The observed ENOMEM is confirmed by the kernel return code. The log does not expose per-block used/free bytes, so it does not yet prove how much of the 27,688,960 mapped bytes was stranded or that this defect alone caused the mapping failure. The safe correction is to search every existing block for a fitting range before requesting another mapping, while retaining stable addresses and process-lifetime ownership. Add tests for reuse of a non-head block, exact-fit allocation, no-fit mapping, alignment and overflow. Add bounded diagnostics for retained bytes/count, mapped bytes, request size and reusable free bytes so the next capture distinguishes true process memory pressure from internal fragmentation.

Do not simply raise the 32 MiB cap, reclaim old blocks, return borrowed bytecode, or force HKS cache invalidation. Existing closures may still reference retained bodies. Keep the 4,096-header and 32 MiB hard limits until a separate lifetime proof supports changing them.

### UI recovery finding

The retention failure is deliberately fail-closed: it returns an immutable diagnostic rawfile instead of the zone-owned bytecode. This protects source lifetime but the diagnostic error interrupts the current menu build. The later successful `AddMenu("main")` recovery path is already present in source. The missing-main error is a downstream symptom of the interrupted menu graph, not evidence that the native menu registry itself is broken.

Add a regression that exercises the full error/recovery state contract: failed mod UI require pauses compatibility injection for that frontend generation; it does not discard the selected stack or disable the Mods removal path; only a successful native `main` registration re-arms recovery; a non-main menu registration does not; the next valid frontend generation can rebuild the compatibility UI. Keep native Lua errors visible.

## Incident C — DS4C nil-index and missing menus

### Direct evidence

- DS4C's compiled `ui/T7/Utility/DS4C_ProgressionStore.lua` throws a nil-index at stripped location `3778239045:629`.
- The error is inside third-party stripped bytecode. The supplied stack does not identify the nil operand.
- UI Error 21544 for missing `main` and then `Lobby` follows the first exception. A later capture similarly reports a nil-index followed by a missing `main`/ `Lobby` menu graph.
- The existing investigation `INVESTIGATION-2026-11-02-DS4C-UI.md` records that the locally available payload was not readable by the current Havok bytecode parser and no editable Lua source was available.

### Assessment and safe path

This is a third-party mod compatibility exception, distinct from the arena ENOMEM. The current evidence cannot identify or safely synthesize the missing field. Do not blanket-fill nil globals, swallow Lua exceptions, rewrite protected bytecode, clear package state, or unload a selected mod after one exception. Those changes could corrupt otherwise valid menus or mask the mod defect.

Keep the narrow successful-`main` recovery behavior, add/retain regression coverage, and improve diagnostics to preserve the first exception, frontend generation and last module identity. A true DS4C correction requires the exact matching mod package/source or a decoded instruction/operand analysis. Until then classify DS4C as a known third-party compatibility failure, not a generic loader crash.

## Implementation plan (documented before source changes)

1. Extract a small production helper for finding a fitting range in the existing retained-block chain; use it before any new `sceKernelMmap` call. Do not move or free blocks.
2. Add production-body host coverage for non-head block reuse, exact-fit, no-fit, alignment, integer overflow and unchanged allocator state on failure.
3. Add bounded DEBUG retention accounting: mapped bytes, used retained bytes, header count, per-block reusable tail bytes, attempted request and native mapping result. Avoid unbounded per-file logs or dereferencing unvalidated pointers.
4. Add/extend the UI error recovery regression so the selected stack and normal Mods disable route remain available after a retention failure and recovery only follows successful `main` registration.
5. Re-run the complete registered host suite, sanitizer checks where applicable, source-policy/session audit, and the PS4 target build for the exact changed source.
6. Preserve the normal queued frontend shutdown and native error reporting. Do not claim the DS4C nil-index is fixed without its exact bytecode/source evidence.
7. Console validation remains separate: clean process, one known-good mod, disable to stock, re-enable/disable repeat, then one affected third-party mod. Record first error and artifact/source identity.

## Validation boundary

The source review confirms the allocator's head-only search defect and the error-code classification. No console reproduction, HKS cache proof, or proof that the fragmentation defect was the sole ENOMEM cause is claimed by this investigation.


## Candidate implementation status — 2026-11-18

A source-only candidate is recorded on branch `fix/mod-enable-lua-arena-reuse-final` (source-only branch created from the latest main head; not merged and no PR opened). It:

- Adds `T7LuaRetentionArena::FindBlockWithSpace()` and changes `AllocateRetainedLua()` to search every existing append-only block before calling `sceKernelMmap`. Stable block addresses and process-lifetime bytecode ownership are unchanged; no old block or HKS closure storage is reclaimed.
- Adds checked size/alignment arithmetic and tracks aggregate reusable tail bytes. Failure diagnostics now distinguish requested allocation size from mmap block size and report retained bytes, mapped bytes, aggregate reusable bytes, largest reusable tail and retained header count.
- Adds `SPRX/tests/lua_retention_arena_tests.cpp` for older-block reuse, exact fit, insufficient contiguous space, invalid block metadata and size-limit behavior. The existing host runner discovers all `*_tests.cpp` files automatically.
- Extends `lua_menu_recovery_checks.py` with source-contract assertions that a modded UI error pauses only compatibility injection, does not clear the selected stack, and only a successful native `AddMenu("main")` call re-arms recovery. The Mods entry remains present in the Lua UI source.

**Validation performed:** the helper/test logic was compiled and run with local g++ C++20 and UBSan; both passed. ASan could not start in the local Python runtime because its runtime was not first in the process library list. The full repository host suite, PS4 target build, and console lifecycle tests have not run. The new source branch therefore remains an unvalidated implementation candidate; `main` remains unchanged and retains its last verified target-build state. No SPRX build was started because the workflow requires explicit build approval.

**Remaining boundary:** the log proves kernel ENOMEM but does not prove how much arena space was stranded or that fragmentation was the sole cause. The new largest-tail diagnostics will distinguish internal fragmentation from true process memory pressure on the next matching console run. DS4C's nil operand remains unknown and cannot be safely patched from stripped third-party bytecode alone.
