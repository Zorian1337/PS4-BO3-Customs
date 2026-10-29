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

- All 34 registered host regression programs pass; the diagnostic/publication
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

## Current console-log review

The newer captures contain three separate failure classes and must not be treated
as one SPRX defect. The large GSC/CSC floods come from the selected private
zombiebots, DS4C and menu/map scripts. They include invalid entity/array/field
accesses and eventually force the engine to end the match; the SPRX cannot safely
turn those undefined values into valid gameplay objects. The same captures also
contain map-specific missing assets and script failures. Those remain separate
mod/map compatibility issues and their original files were not changed here.

One scrolling capture contains a nil-value Lua arithmetic failure in a selected
third-party script, outside this repository. It is not an SPRX-owned failure and
that script was not changed. The frontend captures repeatedly show LobbyVM error
74046 after the Mods menu is closed and rebuilt. A safe source-side improvement
is now implemented: closing an unchanged menu no longer requests a native
mod-stack apply. An explicit pending request or a real chosen-versus-active
change still uses the existing apply path. This reduces needless frontend
rebuilds and the associated unload/reload race without hiding errors or changing
selected mods.

The captures also show UI errors 24280/21544 in `ui/uied/leveling_io.lua` during
multi-mod frontend loading. Their missing menu/nil dependency is not proven to be
owned by BO3-Customs, so no speculative replacement was added. Missing materials
are logged as default fallbacks, and the GPU traces reach completion; adding GPU
fences or enlarging pools without a matching allocation failure would risk
deadlocks and was deliberately not done.

The Reaper Collection capture provided a source-owned map-selection finding:
`mapselect.lua` detected that an external mod supplied its own ZM map menu and
the compatibility path was replacing the menu's map table. That could make
custom maps unselectable or violate the owner's row/compatibility contract.
The compatibility path is now generic: it recognizes any loaded replacement
under the ZM map-menu namespace, preserves that menu's native map table, and
lets the normal catalog-entry merge supply available custom rows. It does not
name or special-case Reaper. The refresh path suppresses BO3-Customs' injected
tab bar/counter for any externally owned ZM menu; if our bar was created first,
only that bar is removed. Stock ZM menus retain the BO3-Customs tabs.

The original log files remain outside the repository. The next validation should
run the same selected stack with only this menu-apply change, then repeat with
each third-party mod isolated. A new binary/package is not implied by this source
commit and still requires an explicit build request.

The later Reaper capture showed UI errors 24280/21544 followed by the generic
menu probe treating the missing `main` constructor as proof that the selected
mod was bad. The recovery path now preserves the selected stack instead of
silently deleting it; the user can manually disable a failed frontend. This is
deliberately generic and does not claim that a third-party Lua error is fixed.
Catalog classification also recognizes common user-map flags (`isCustom`,
`isModMap`, `isUserMap` and snake-case variants), keeping those rows in the
custom category rather than the standard category.

The map selector now also cross-references the generic `BO3CustomMaps` catalog
by internal ID and normalized display name. Existing rows are marked in place
instead of cloned, invalid/locked rows are excluded from category data sources,
and stock rows remain in Standard. This is deliberately catalog-driven and
does not name or special-case Reaper Collection.

The console trace also showed duplicate custom rows: a canonical loadable
`zm_*` row followed by a compatibility row for the same map. The selector now
matches aliases by catalog identity first and normalized display title as a
fallback, keeps the canonical installed row, and deduplicates remaining title
matches deterministically.

When a Workshop-ID row matches a catalog entry, the selector resolves that row
to the catalog's canonical internal map ID (for example `zm_complex`) and uses
the canonical row for loading. The Workshop ID remains available as metadata
for compatibility/status reporting; it is not used as the map launch target.

The resolver now checks the catalog's exact `ugc`/PublisherID fields before
comparing display text. This matters because Reaper can expose a compatibility
row whose key is the numeric Workshop ID while its title differs from the
installed package title. The numeric row is classified as custom, suppressed
as a duplicate, and the canonical package ID is retained as the selectable
entry. Title/name comparison remains only a fallback for catalogs that do not
expose a Workshop ID.

### Numeric compatibility IDs

The numeric rows are not the map's internal fastfile name. They are generated
compatibility/catalog identifiers exposed by the replacement map frontend. In
the captured session, examples such as `2444580439`, `3303537924`, and
`3818361117` appeared beside canonical rows like `zm_complex`, `zm_dshouse`,
and `zm_onewindow_cave`. Their shared display names and missing canonical
`zm_*` route identify them as compatibility projections rather than separate
loadable maps. They may be useful later for compatibility/status lookups, so
the selector filters them from the visible lists instead of deleting or
rewriting the catalog data.

When a frontend probe reports a broken menu graph (for example, a provider
throws before `main`/`Lobby` exists), compatibility injection is now latched
off for that frontend generation. This prevents repeated BO3-Customs Lua
injection from compounding a provider's failure; a fresh frontend generation
clears the latch and allows a clean retry.

The next capture showed the third-party frontend throwing before the stock
`main` constructor existed. `mapselect.lua` now defers all map/list hooks when
that constructor is absent and retries from its existing tick path after the
frontend rebuilds. This keeps BO3-Customs from compounding an incomplete UI
state; it does not mask or claim to repair the third-party Lua exception.

## Reaper aliases in the Standard and Customs tabs

The latest report says the map targets now resolve, but Reaper compatibility
rows appear in Standard and beside the installed custom rows in Customs. Source
review found two gaps that can produce that result: custom classification did
not compare the installed catalog's `displayName`/`mapTitle` fields, and
duplicate suppression only discarded aliases whose IDs parsed as numbers. A
compatibility row using another ID format or a map-title field could miss both
protections. This is a source-supported explanation for the reported behavior,
not a claim that every Reaper row has that shape.

The map selector now includes those generic catalog title fields in matching.
Standard classification uses the catalog match, while Customs groups matches
under their canonical installed map ID and gives the actual installed row
priority. Ties are resolved deterministically. This applies to any external map
catalog; there is no Reaper name check or mod-specific branch. If installed maps
ambiguously share a title and have no exact Workshop identifier, the canonical
resolver still fails closed instead of guessing a launch target.

Other options considered: filtering all external rows would also hide valid maps
that lack an installed catalog match; deduplicating only by colored display
title misses aliases with different labels; mutating the third-party catalog
could break its own selectors. The selected approach only reclassifies and
deduplicates rows that resolve to an installed custom map, and leaves unmatched
external rows to their owner. Regression cases cover numeric and nonnumeric
aliases, Workshop-ID matches, colored title matches, stock rows and ambiguous
titles. Console behavior still needs validation.

## Completed provider rows bypassed the catalog filter

The next report confirms that compatible map targets work but duplicate rows
remain. Source review identifies a separate defect: both external-owner paths
in `WrapMapsList` and `PrepareZMMaps` return the provider's rows without category
filtering. The provider can also append engine mod-catalog rows independently of
`CoD.mapsTable`, so filtering that input table cannot cover its completed list.
The earlier table-only regression did not exercise this path.

Correction plan: keep the provider's builder and row metadata, normalize its
completed map rows to installed load targets, then filter categories and dedupe
by both target ID and displayed name without color escapes. Prefer useful
provider metadata when choosing between duplicate rows. Keep map-stat and
Workshop identifiers as metadata, restore temporary table/category state on
failure, and avoid persistent provider-row mutations across load/unload/reload.
The existing ZM tab bar can drive the provider's own MapList when it has no
category selector; an existing category selector must retain ownership.

Alternatives: another input-table-only filter misses appended rows; replacing
the builder loses compatibility labels and callbacks; deleting provider records
permanently risks stale references after unloading. Output normalization is the
selected narrow correction. Validate actual wrapper calls, repeated preparation,
colored-name duplicates with different IDs, bridge aliases, category boundaries,
valid selection properties, provider exceptions and restoration, plus playlist
and unrecognized row contracts. These are source checks, not console proof.

Implemented in companion `mapselect.lua`: the completed ZM and ChangeMap row
lists now pass through the same category/identity/title filter, including the
existing recovery path. Duplicate groups join by either load target or title
with numeric color escapes removed; bridge aliases cannot leave two winners.
Provider compatibility/stats fields and callbacks take preference over plain
catalog rows, while selection targets use installed internal map IDs. Copies
are made only for changed selection properties; source rows are not rewritten.
Pure numeric IDs that cannot resolve to an installed map are omitted.

Replacement ZM menus keep their menu object, original MapList and callbacks.
Shared tabs can drive that list when it has no category control. A provider's
existing category control remains authoritative, and removing shared tabs also
closes their model watcher. Repeat category preparation does not append another
Customs entry. Normalization runs during list preparation with local state;
there is no added polling or persistent provider-row cache. Count-change traces
use the existing MapSelect log bridge.

All 34 host regression programs passed. The focused Lua checks also passed after
the final watcher/logging changes. The regression executes actual wrappers with
a provider that appends rows independently of the map table, checks colors and
different IDs, every ordering of a three-row bridge, callbacks/metadata, repeated
preparation/reopening, category ownership, playlist bypass, and error restoration.
An in-memory negative control restoring the unfiltered provider return fails at
the Standard-category assertion. Following approval, the companion Lua was
uploaded and verified byte-for-byte against source commit `8f9e31d`, using the
existing dev.49 plugin. No SPRX rebuild was needed; frontend validation remains.
