# Current development status

Updated 2026-10-29. Source label: dev.34 DEBUG. **Unvalidated candidate, not a release.**

## Evidence and present behavior

| Area | Source/check evidence | Console evidence / remaining work |
| --- | --- | --- |
| Kernel file metadata | Explicit native stat ABI and image-parser checks replace an incompatible host layout | Previous image-preview correction was reported working; recheck after relevant IO changes |
| Lua lifetime | Mod/custom-zone bytecode retention, version deduplication and bounded dedicated memory; no blanket copying of stock UI because metadata is truncated or busy | The latest report confirms an initial UI-content load/unload; repeated entry still needs validation |
| Startup / frontend | Native frame precedes companion work; readiness resets on frontend transitions, including reused VM addresses | Early plugin injection and repeated mode/map returns need hardware checks |
| Menu re-entry | Console entry owns its callback; controller normalization and scoped live selection queries; twenty host Lua reopen cycles | Candidate addresses an observed LobbyVM 74046 / UI 40546 sequence; exact inner nil access and a later native crash are not conclusively attributed |
| Persistent diagnostics | Separate bounded error log, context/stack capture, short-write handling and IO retry; session log behavior retained | Validate console append across restarts and kernel correlation during a real fault |
| Content activation / joining | Transaction and readiness checks exist, with host regressions | Successful download is not proof of activation or matching BG-cache/schema; controlled peer testing remains necessary |

## GPU completion and lighting diagnostics (source-only, 2026-10-29)

- `SPRX/t7_maps.cpp` now reports completion-label changes and submission-counter
  changes independently. An unchanged completion value is **not** a proven GPU
  deadlock when the CPU may have stopped submitting work.
- The lighting-blob summaries now treat state 2 as **loading**, not resident.
  State 3 or higher is counted as resident, matching the per-record `[Blobs]`
  description. The GPU sample identifies resident/total counts separately for
  probes, volumes, sun-shadow trees, other resources and sky resources.
- The latest GPU regression suite passes in GitHub Actions. These are
  diagnostics/counter-correctness fixes, not forced GPU completion, a resource
  allocator change or a demonstrated reduction in black-screen duration.

**To establish a root cause on hardware:** use the exact matching experimental
SPRX, reproduce a single map load on PS4 and PS5, and preserve the first
`[GPU]`, `[Stream]`, `[Blobs]` and `[Stall]` sequence before restarting.
Compare whether frame/submission counters advance while completion does not,
and whether a specific required resource category remains loading. Include the
first engine error and thread stack. Without that evidence, changing GPU waits
or marking a deadlock fixed would be speculative.

## First next task: repeated menu operation

1. Use the matching candidate SPRX and companion `Lua/ui_scripts/mods.lua`.
2. With one test content item, load, unload and reload three times.
3. Enter and leave a match, then repeat selection/apply.
4. Read the earliest error, selected/loaded state, controller and menu generation.
5. If it fails, preserve the report before another restart and compare multiple
   causes. Do not change unrelated content or blame a last-loaded file without proof.

Potential follow-ups if the candidate does not resolve re-entry:

- Capture current menu/global function identities; check wrappers from an obsolete
  Lua table or an unsupported PC callback after frontend reconstruction.
- Inspect the exact nil operand using matching source/bytecode evidence.
- Check pending frontend-apply/reload flags after an empty selected stack and map
  return. Do not use a permanent restart requirement as the normal unload path.
- Compare an isolated item with an overlapping stack; a conflict is a separate
  result from failure of the loader's own menu.
- Use the exact built ELF for plugin stacks and a verified matching game image
  when native engine identity is needed. Never patch an assumed function.

No universal crash fix or performance improvement is established by these tests.
Asset-pool capacity, available process memory, IO stalls and UI state are separate
questions. Grow only verified pools on demonstrated exhaustion; never manipulate
GPU fences, arbitrary memory regions or native validation to hide a failure.

## Source map

- `SPRX/t7_maps.cpp`: catalog/zone routing, stack transactions, frontend handoff.
- `SPRX/t7_lua.cpp`: UI ownership, native hooks, compatibility and bytecode lifetime.
- `Lua/ui_scripts/mods.lua`: console menu entry, selection and scoped callbacks.
- `Lua/ui_scripts/mapselect.lua`: map selection and recovery.
- `SPRX/t7_log.cpp`, `error_capture.hpp`: diagnostics and persistent error context.
- `SPRX/t7_lua_ownership.hpp`: lifetime membership independent of display metadata.
- `SPRX/openorbis/`: target ABI adapter; `.github/openorbis-lock.json`: pinned tools.
- `SPRX/tests/`, `tools/console_diagnostics/`: regressions and read-only collection.

Private evidence and original binaries do not belong here. Keep only a sanitized
finding and a reproducible validation method in public status. Past draft release
notes and content-specific reports have been removed from the active source tree;
use Git history for source changes and GitHub Releases for approved distributions.

## Current source checks

The maintained host suite contains 29 regression programs, including two C++
executables. The separate diagnostic reader and publication guard have 13 unit
tests. The SDK header and native artifact comparisons require explicit matching
inputs and are not silently replaced by host stubs. These checks do not establish
console stability; the next hardware validation remains repeated menu re-entry.
