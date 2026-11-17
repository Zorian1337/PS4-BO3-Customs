# Upstream BO3-Customs stability review — 2026-11-17

## Scope and evidence

Reviewed the public upstream repository `ItsJokerZz/PS4-BO3-Customs` at
`c082b44640806b4406b6cb5349ccd36430d205b6` (v4.00, released 2026-10-21),
against this repository's `main` source, whose current Debug candidate is
`dev.60`.

Primary files compared:

- Upstream: `SPRX/main.cpp`, `SPRX/t7_maps.cpp`, `SPRX/t7_log.cpp`,
  `CHANGELOG.md`.
- Ours: the same SPRX files, `SPRX/tests/pool_growth_checks.py`,
  `SPRX/DIAGNOSTICS.md`, `RESUME.md`, and `docs/DEVELOPMENT.md`.

The supplied 2026-10-15 log reports a 20-second interval with no frame or
asset-link progress. Its main-thread stack contains multiple SPRX frames.
That is evidence that the main thread was executing plugin code when sampled,
but the log's old `sprx+offset` addresses cannot be reliably mapped to the
current dev.60 source without the matching October binary/map. The log predates
upstream v4.00 and our later dev.60 changes. Therefore this review identifies
credible paths and source defects; it does not claim a proven single cause for
that historical stall.

## Findings: retain our existing improvements

These are meaningful differences where upstream's current implementation is
less defensive. Do not replace our code with the simpler upstream versions.

### 1. Frame-hook ordering

Upstream `SPRX/main.cpp` calls `T7Lua_Tick()` before the original
`Com_Frame`. Our `main.cpp` calls the original frame first and runs
`T7Lua_Tick()` afterward. Keep our ordering: Lua compatibility work must not
sit in front of the game's frame progression.

The other callbacks still run before the original frame in both versions:
`T7Maps_FrameWork()`, `T7Share_Tick()`, and `T7Builtins_Tick()`. These remain
the highest-value places to add timing instrumentation (see action items).

### 2. Mod loading and frontend handoff

Upstream `T7Maps_FrameWork()` can call `PrefetchMods()`, which may append
mod zones while the frame hook is running. Its `ApplyModsNow()` path also
performs unload/load work directly from the frame-work path.

Our `PrefetchMods()` no longer loads zones from that tick; it only marks the
Mods overlay for refresh on close. Our apply path waits for the frontend
handoff, checks that loader hooks are ready, avoids consuming a request during
gameplay, and applies the selection at the intended frontend zone transition.
It also has a timeout for a frontend handoff that never completes.

Keep our deferred frontend transaction. Do not reintroduce upstream's
synchronous prefetch path. The remaining apply transaction still needs
instrumentation because zone unload/load and frontend reload are expensive
operations by nature.

### 3. Asset-pool growth

Upstream's `GrowPool()` uses a lazily initialized mutable lookup table and
does not serialize concurrent pool expansion. It has no shared plugin memory
budget and does not latch a failed `mmap` attempt, so later asset links can
retry the same failed expansion.

Our implementation uses a linear immutable-table lookup, serializes expansion,
rechecks the pool after taking the lock, limits each synchronous allocation to
1 MiB, enforces a shared growth budget, caps repeated failures, and treats
image pools specially because of their fixed streaming tables.

Keep our implementation. Do not port upstream's lazy static index or
unbounded retry behavior. The existing
`SPRX/tests/pool_growth_checks.py` exercises the production growth code,
including bounded image growth, allocation failure under concurrency, budget
exhaustion, free-list construction, and the non-exhausted fast path.

**Follow-up completed 2026-11-17:** the pool-growth fixture now marks an
eligible synthetic pool as singleton and asserts no mmap, no free-list change,
and no limit change. The growth allowlist also explicitly excludes COM World,
Game World, and the one-entry sound-driver, bullet-penetration, and
location-damage pools pending proof of safe multi-entry semantics. See
[the BOIII memory/stability comparison](BOIII-MEMORY-STABILITY-REVIEW-2026-11-17.md).

### 4. Concurrent map-list access

Upstream's `BeginListWrite()` sets the writer flag without acquiring it
atomically, so two writers can both proceed. Our implementation uses
`exchange(true)` to serialize writers and releases with acquire/release
ordering. Keep ours.

### 5. Failed mod-menu recovery

Upstream's `T7Maps_MenusBroken()` removes the suspected mod from the saved
selection and schedules an unload when its menus fail to build. Our version
preserves the selected stack because a frontend/UI error is not proof that the
last loaded mod caused it; transient menu rebuild failures must not silently
erase the user's selection.

Keep our preservation behavior. It is consistent with the requirement that
users retain control over disabling mods and that transient UI errors must not
turn into destructive state changes. Do not copy upstream's automatic
un-ticking behavior without stronger causal evidence and a reversible
transaction.

### 6. Diagnostics and unload lifetime

Our Debug watchdog adds GPU/resource progress, dispatch snapshots and loading
zone state to the upstream thread-stack and pool sampling. Our pool report
also records entry size, singleton state and free-list availability, so a
1/1 singleton is not mislabeled as an ordinary exhausted pool.

Our `T7Log_Zone()` invalidates diagnostic Lua entries that borrow pointers
into database-zone buffers before unload. Upstream's version does not do this.
Our `T7Log_NewLevel()` also resets the per-level script-error budget and
associated capture state.

Keep these protections. They improve diagnosis and avoid retaining stale
borrowed pointers across zone unloads.

## Actionable stability fixes in our repository

These are source-level defects or worthwhile hardening work found while
comparing the two repositories. They are not claimed to be the cause of the
October log by themselves.

### P0 — Check initialization-thread creation and join results

Both upstream and our `SPRX/main.cpp` currently do this in `Start()`:

- declare `ScePthread thread`;
- call `scePthreadCreate()` without checking its return value;
- call `scePthreadJoin(thread, ...)` unconditionally;
- leave `g_started` set even if initialization did not start successfully.

If thread creation fails, the handle is not valid for joining. The plugin can
also report successful startup despite its initialization worker never
running, and the one-shot `g_started` latch prevents a retry.

Status in our repo (source committed 2026-11-17):

- `scePthreadCreate` is checked; a failed create returns without joining an
  invalid handle and releases the startup latch.
- `scePthreadJoin` is checked. A failed join keeps the latch set because the
  worker's state is unknown and a retry could duplicate partial initialization.
- The worker returns a distinct success sentinel. A completed worker that
  timed out waiting for BO3 releases the latch so a later loader callback can
  retry; successful initialization remains latched.
- No runtime/console validation has been performed yet.

The startup failure is returned to the plugin loader; detailed logging before
`T7Log_Install` is not available in this path. Preserve the native entry-point
return contract when extending this handling.

Upstream issue [#32](https://github.com/ItsJokerZz/PS4-BO3-Customs/issues/32)
reported a plugin that did not initialize and produced no plugin log. The
discussion required kernel logs to diagnose loader/startup failures. A
contributor's issue-linked commit was described as propagating initialization
thread errors, but the current public upstream `main.cpp` still contains the
unchecked create/join sequence. Treat the issue as motivation, not proof that
the proposed fix is already present upstream.

### P1 — Fix watchdog worker handle ownership

Both versions' `StartStallWatch()` use one `ScePthread thread` variable for
both `StallWatch` and `StallMirror` creation. The second create overwrites
the first handle. Neither worker's creation result is handled independently,
and the combined status can say `NOT started` even if one worker is running.

Status in our repo (source committed 2026-11-17): the workers now use
distinct handles, each create and detach result is reported independently,
and each successful worker is detached. A partial start is reported as
`partially running`; the two handles can no longer overwrite one another.
Runtime behavior still needs target validation.

### P1 — Attribute time spent before the original game frame

Our frame hook still executes three plugin callbacks before `Com_Frame`:

- `T7Maps_FrameWork()`
- `T7Share_Tick()`
- `T7Builtins_Tick()`

The current code has already removed upstream's synchronous mod prefetch
from `T7Maps_FrameWork()`, but the callbacks should be timed independently.
In particular:

- `T7Share_Tick()` calls `Evaluate(true)`, which updates/publishes lobby
  state and can initiate a session transition/download.
- `T7Builtins_Tick()` can call `T7Config_Save()` synchronously when mod
  variables are dirty.
- `T7Maps_FrameWork()` can process a pending mod/frontend transaction and
  reload-state bookkeeping.

Status in our repo (source committed 2026-11-17): Debug builds mark the
active phase before each callback and the original engine frame. The watchdog
also distinguishes lobby evaluation, hosted-state snapshotting, share
completion and the full map-catalog refresh. It reports the phase and elapsed
time only when sampling a stall.

The periodic mod-variable autosave was a confirmed synchronous filesystem path
inside `T7Builtins_Tick()`. It now publishes an owned snapshot to a dedicated
config worker; the worker retains the existing merge/temp-file/fsync/rename
semantics. Queue pressure or worker creation failure leaves variables dirty
for retry, and a failed background write signals the next tick to retry.
Keyboard/mouse and graphics config saves remain synchronous on their explicit
user-action paths.

The shared-download completion path still invokes `T7Maps_Refresh()` from the
frame callback. It was not naively moved to a worker: `ScanAll()` holds the
catalog writer state, and `ListReader` currently spins until that writer
finishes. A worker scan would therefore still block main-thread catalog readers.
The safe next step is a double-buffered catalog with a short atomic publication
step. See [the frame-work hardening report](INVESTIGATION-2026-11-17-FRAME-WORK-STABILITY.md).

This is a concrete reduction in main-thread IO risk, not proof of the
historical stall's cause. The old binary is still required to identify which
callback occupied the stack at that time.

### P2 — Bound engine-owned rawfile and script-name reads

**Implemented 2026-11-17:** `NoteLevelLua()` and `ScriptBase()` now copy
engine-owned names byte-by-byte only after per-byte readability checks, stop
at bounded local capacities, and reject unreadable or unterminated names.
The regression fixture exercises valid names, invalid suffixes, an unreadable
page boundary, and short output-buffer sizing. This is defensive hardening;
the supplied log does not show that either path faulted.

## Upstream issue evidence relevant to stability

- [#38 Radiant Hallway issues](https://github.com/ItsJokerZz/PS4-BO3-Customs/issues/38):
  the report describes a late-game crash attributed by the reporter to pool
  bloat. The upstream discussion says the map's kill script was erroring on
  every kill and later overflowing the script stack; that is separate from
  proving a native pool exhaustion. Our bounded pool growth and current
  script-error diagnostics are the right direction; do not globally enlarge
  pools based on the report alone.
- [#33 Mob of the Dead Remastered](https://github.com/ItsJokerZz/PS4-BO3-Customs/issues/33):
  upstream identified a character with no movement sounds; the PC tolerated
  silence while PS4 crashed. This is a converter/content-compatibility case,
  not evidence for changing the SPRX frame or pool logic. Keep it separate
  from the October frontend stall.
- [#43 Too many maps in list](https://github.com/ItsJokerZz/PS4-BO3-Customs/issues/43)
  and [#45 126/127 map limit](https://github.com/ItsJokerZz/PS4-BO3-Customs/issues/45):
  these are catalog/zone-list capacity reports. Revisit only if our current
  map enumeration limits or a new log reproduce the same failure.

## Recommended order

1. Validate the new startup lifecycle and watchdog worker changes with
   the supported host checks and target syntax/link validation.
2. Capture a fresh Debug log if the stall recurs; inspect the reported frame
   callback phase before changing scheduling or moving work across threads.
3. Add bounded sub-operation timing for the identified phase only.
4. Completed: add singleton-pool regression coverage and exclude fixed/special
   pools from automatic growth.
5. Completed: bound rawfile and script-name reads; see the regression fixture.

The source now contains targeted startup hardening and Debug stall attribution.
No build, GitHub Actions run or console test was performed. These changes do
not prove the October 15 stall or any fatal crash is resolved. See
[the frame-stall investigation](INVESTIGATION-2026-11-17-FRAME-STALL.md).


## Addendum — BOIII comparison and low-memory corrections (2026-11-17)

The follow-up review of Ezz-lol/boiii-free is recorded in
[BOIII-MEMORY-STABILITY-REVIEW-2026-11-17.md](BOIII-MEMORY-STABILITY-REVIEW-2026-11-17.md).
It identified that our prior minimum-extra-capacity policy could grow
one-entry pools by up to 64 entries and that our growth table included COM
World and Game World. Those entries have now been removed from automatic
growth. The image, GFX World, and XModelMesh restrictions remain.

The native allocator synchronization contract remains an open P1 research
item: BOIII serializes its replacement allocator with pool reallocation, while
our append-only growth lock does not establish synchronization with BO3's
native allocator. No unverified allocator detour was introduced.

The new source/tests were committed in
`6193fe31d24009bda0c25833b5d60b09eccc750d`; documentation and roadmap were
committed in `0c97ead415a2f2b117fb95bc1478a63c555fe357`. At the time of this
addendum, the diagnostics workflow and main build were running. PS4 console
validation and the exact cause of the reported crash remain unconfirmed.

## Additional confirmed concurrency defect — pool-out once-only latch

T7Log_PoolOut() is invoked from LinkXAsset_h(), which can execute on multiple
database workers. The function used a plain static bool told[kTypeCount] for
its once-only per-type diagnostic. Concurrent read/write of that array was
a data race. The latch is now std::atomic<bool> and uses exchange() after
checking the pool state. A production-function stress fixture runs 32 workers
against the same exhausted type and checks for exactly one diagnostic.
The fixture is registered in the PR diagnostics workflow and full host suite.
Do not confuse this diagnostic race with a native allocator race; the latter
remains unproven and requires PS4 binary-level allocator analysis.