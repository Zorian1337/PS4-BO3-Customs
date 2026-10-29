# Multi-mod loading and frontend recovery

Updated 2026-10-29. Development branch: `testing/dev35-debug-build`.
Tracks [Issue #23](https://github.com/Zorian1337/PS4-BO3-Customs/issues/23).
Source fixes below are verified by host regressions, not confirmed console cures.
No plugin was built or released during this investigation. The experimental
candidate workflow is manual-only; ordinary source pushes cannot publish a build.

## Keep the failures separate

The supplied working 7-Eleven run has no selected gameplay mods and reaches client
frames. The failing capture first applies Reaper Collection with JINX, encounters
UI 24280 (`attempt to index a nil value`), then UI 21544 (missing `main` menu).
Automatic recovery unticks Reaper. The later map load uses JINX and DS4C Patched.
That sequence does not isolate either mod as the cause of the loading hang.

Timestamp clarification: the first invalid-opcode record is at 04:06.561. The
first printed no-progress warning is stamped 04:20.400 and describes twenty
seconds without a native frame or linked asset. Thus the opcode precedes the
printed warning but falls within its reported quiet interval. This does not
establish whether the opcode fault initiated, prolonged or followed a load fault.
Do not equate the first watchdog warning with the exact onset of a hang.

The different asset-link totals are cumulative observations, not proof of pool
exhaustion. A frame-completion value ahead of a stale request is not proof of an
outstanding GPU frame. Retain the distinct CPU, GPU, script and UI evidence.

## Verified source correction: concurrent zone attribution

`LoadXFile_h` previously saved and replaced one global zone pointer and one
global loading-thread ID around the native loader. Overlapping workers could
overwrite one another's pair; out-of-order returns restored another worker's
stale context. Asset ownership/renaming and XPAK routing could consequently lose
the active mod context. Atomic individual fields do not make that saved pair a
per-worker stack.

The hook now uses the existing bounded `ModLoadContexts` facility. Asset naming,
map-Lua ownership and XPAK routing query the current worker's context. Nested loads
restore their caller's zone; exiting a load releases its slot. No global mutex is
held across native loading and no new dynamic TLS or per-load heap allocation is
introduced. Native loader/XPAK arguments and return values are preserved.

`zone_load_context_checks.py` executes the production hooks with deterministic
worker overlap, nested loads and XPAK/asset attribution checks. The original source
fails; the corrected source passes under ASan/UBSan. This proves the attribution
defect, not that it was exercised in the supplied console run. Capacity remains
bounded at the existing facility's 64 slots; exhausted/unknown contexts do not
borrow another worker's ownership.

Alternatives considered: serializing native load calls risks reentry/deadlocks
and reduces parallelism; replacing the engine's worker scheme is unnecessarily
broad. Neither was adopted. Script opcode rewriting and priority changes are not
part of this correction.

## Verified source corrections: exact Lua platform-state restoration

The compatibility `require` wrapper used an `and/or` expression that converted an
original raw `CoD.isPC = false` into `nil`. Its temporary scope marker was also
always cleared to `nil`, even when its original value was explicitly `false`.
The wrapper now saves and restores both exact values after successful or failed
imports; error propagation and existing nested-import recovery remain intact.

The periodic platform helper also reused one saved value after the `CoD` table
was replaced. Its snapshot now belongs to the actual table and captures the raw
field, so a new table is not overwritten with a previous table's platform flag.
Inherited values are restored by removing the temporary raw override, rather
than leaving a permanent shadowing field.

`lua_compat_scope_checks.py` executes the actual production chunks using the
installed Lua 5.1 runner. It covers false/nil state, failed imports, idempotent
installation, native/unowned imports, inherited flags and replacement tables.
The original source fails; the corrected source passes. This runner is not HKS
or the BO3 engine, and these tests do not prove Reaper's nil operand is fixed.

## Package inspection

The supplied Reaper localized `bp_core_mod.ff` walks successfully: 642 assets
registered. Its XPAK has seven entries/index records; recomputed keys match and
the reconstructed XPAK is byte-identical. Input hashes remain unchanged.

The main `core_mod.ff` also walks successfully: 4,515 asset records, 4,514
registrations reported by the porter. Seventy-three Lua chunks were recovered
privately for inspection, including the leveling modules named by the log.
Passing these format checks does not establish runtime dependency or frontend
compatibility. Logged stripped-function identifiers are shared across chunks,
so the last loaded filename and identifier alone cannot identify the nil operand.
Do not fabricate missing tables/functions to make the error disappear.

Raw logs, packages, recovered bytecode and machine-specific paths remain local;
none are part of this repository change. Source packages were not modified.

## Unloading and original-state restoration

Keep the existing frontend shutdown/rebuild sequence, selection rollback,
missing-menu probe and automatic untick recovery. Retained bytecode stays alive:
freeing it while the native VM still references it would reintroduce use-after-free.
These changes restore the platform flags they own; they do **not** claim complete
restoration of every global, metatable or loaded module modified by arbitrary mods.

Complete restoration must include the native UI/VM lifecycle. Next checks should
compare the original globals, `package.loaded`, menu constructors and compatibility
ownership after load/unload/reload, including reuse of the VM address and replacement
of Lua tables. Retaining bytecode is memory-lifetime protection, not permission to
serve a disabled mod's assets in place of the original ones.

Avoid replaying a blanket global-table snapshot: that could restore stale engine
objects or erase unrelated valid changes. Avoid clearing `package.loaded` broadly:
existing references and subscriptions could survive and acquire duplicate handlers.
Use owned-write rollback where its lifetime is proved, or the native rebuild path
where arbitrary mod state must be discarded. No restart-only unload lock was added.

## Validation and next actions

- All 33 registered host regression programs pass; the diagnostic/publication
  tools' 13 unit tests pass. Both modified PS4 translation units pass installed-SDK
  Debug/Release syntax checks. No linking, packaging or console changes occurred.
- Preserve the working-case controls and the current recovery tests. The source
  branch can advance without requiring an immediate console session.
- Map Reaper's actual nil operand from matching bytecode/debug evidence before
  adding a compatibility shim. Keep that fix independent from multi-mod loading.
- Compare matching mod scripts and load ownership before claiming an opcode issue
  is repaired. Do not suppress invalid opcodes or clientfield validation.
- Hardware validation can later use each mod alone, then the combined stack, then
  disable/re-enable and repeat after a match. Report the first failure and matching
  source/artifact identity; no further build is authorized by this source task.

Issue #23 remains open. The supplied loading hang and Reaper's frontend failure
are not confirmed resolved by these source corrections.
