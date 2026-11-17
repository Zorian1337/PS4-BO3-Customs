# 2026-11-17 ZM custom-map crash investigation

## Scope and confidence

This report analyzes the supplied PS4 Debug log excerpt for the custom map
`zm_ccube` against the current `Zorian1337/PS4-BO3-Customs` source. The excerpt
ends at approximately 01:55.031, shortly after the level-load request. It does
not contain a fatal signal, exception, native crash record, or the final
console log lines. The report therefore separates observed facts from leads.

## Timeline and observations

- 01:54.531: `zm_ccube.ff` opens from
  `/data/BO3-Customs/usermaps/zm_ccube/zm_ccube.ff`.
- 01:54.578: `zm_ccube.fd` opens from the game's `/app0//zone` directory.
- 01:54.588: the level-loading boundary is entered.
- The pre-level pool snapshot reports xmodel 6825/10240, material
  14997/19712, localize 21194/23552, customizationtable 5/8,
  customizationtablecolor 764/1024, stringtable 161/200, ddl 45/64,
  scriptparsetree 633/1024, bitfield 37/52, maptable 17/25 and
  maptableloadingimages 16/25.
- Three one-entry pools have no free-list pointer in this snapshot:
  snddriverglobals 1/1, bulletpenetration 1/1 and locdmgtable 1/1.
- 01:54.643: the load-xassets request is entered; subsequent trace records
  identify the zone request and the `zm_ccube` package.
- 01:54.801: the unnamed zone is unloaded with flags 0x400000.
- 01:54.807: `zm_ccube` is loaded with flags 0x100.
- 01:54.813: the log says `zm_levelcommon` goes in front of `zm_ccube`.
- 01:54.965: the GPU checkpoint reports level age 86 ms, 3315 native frames
  and 148929 linked assets.
- 01:54.994: the GPU frame label is readable; completed=13564,
  wanted=13551 and building=13548. Completion is ahead of wanted.
- 01:55.031: resource counters are readable, pending=1, started=0, done=0,
  image and mesh missing counts are zero, one lighting blob is not resident,
  and sound-loaded is 1.000.

The supplied excerpt ends here. The ordering of trace timestamps and formatted
log timestamps is not perfectly monotonic because records are emitted from
multiple threads and some diagnostic lines carry the sampled event time.

## What this does and does not prove

### Supported

1. Both custom-map files were opened successfully.
2. The engine entered the level-load path and requested the expected custom
   zone; the common level zone was placed ahead of the custom zone.
3. The GPU diagnostic could read its frame/resource observations at the
   checkpoint. The completion counter was ahead of the wanted counter.
4. At that instant, image/mesh part counters showed no missing required parts.
5. One lighting blob was not resident and the stream status showed one pending
   item. These are leads to follow, not fatal errors by themselves.
6. The three one-entry pools had no free-list pointer at the pre-level
   snapshot.

### Not established

- No crash signal, exception, fatal engine error, or failing allocation appears
  in this excerpt.
- A one-entry pool at 1/1 is not, by itself, proof that an allocation was
  attempted and failed. The current code excludes some special pools from
  automatic growth; the pool-out hook reports when another asset link reaches
  a full non-single pool, but that event is absent here.
- A missing lighting blob at an 86 ms checkpoint does not prove a streaming
  deadlock. The game may simply not have reached that resource yet.
- The GPU counters are observational diagnostics. Their values do not prove
  GPU completion, submission, or deadlock.
- The excerpt does not show whether the map ever reached gameplay, whether
  the pending zone completed, or what the fatal event was.

## Source review and actionable defect

### Fixed: unbounded rawfile-name scan during asset linking

The previous `NoteLevelLua()` checked only the first four bytes of an
engine-owned rawfile name and then called `strlen(name)`. A name starting near
the end of a readable page could cross into an inaccessible page before its
null terminator. Since this hook runs during asset linking, a malformed,
truncated, or otherwise short-lived name could crash the diagnostic/ownership
path during a map load.

The correction copies zone and rawfile names into bounded local buffers,
checking every source byte with `RangeReadable` before dereferencing it. It
also validates the asset record before reading its type/header and passes the
owned copy to the Lua-ownership index. The adjacent `ScriptBase()` helper now
uses the same bounded-copy rule for GSC/CSC script names, protecting the
stack-script ownership path as well. It preserves the intended behavior:
only Lua rawfiles belonging to the current usermap package (or
`zm_levelcommon`) are marked for retention.

A host regression test compiles the actual production function with stubs and
checks valid Lua names, non-Lua names, a non-terminated name crossing into a
protected page, and overlong names. This test protects the memory boundary;
it does not reproduce the game crash or validate PS4 engine offsets.

## Other source-review observations

1. The GPU progress report explicitly labels its counters as observations and
   emits resource categories. This is appropriate; do not turn a single
   missing blob into an automatic failure or force-complete streaming.
2. The watchdog checks the readability of diagnostic regions and bounds the
   blob dump. Keep those protections; do not add unguarded engine-memory scans.
3. The pool growth path uses a bounded 64 MiB plugin allocation budget, limits
   individual batches, and serializes free-list updates. The three full pools
   in this report are not configured for growth. Do not add them to the growth
   table without proving their native allocation/free-list contract.
4. The current pool-out diagnostic is the key evidence to collect if one of
   these pools is actually exhausted. Capture the exact `[Pools] the ... pool
   has no room left` line and the subsequent `when it ran out` snapshot.
5. `LoadXFile_h` uses per-thread scoped zone context and restores nested
   context on return; the repository has a concurrency regression test for
   nested/concurrent zone and XPAK loads.
6. The existing zone/Lua diagnostic lifetime tests protect against retaining
   borrowed buffers after unload. The new rawfile-name test addresses the
   separate bounded-read gap in `NoteLevelLua()`.

## Correction strategies

### A. Apply the bounded-read correction (implemented)

This is the lowest-risk immediate source fix. It removes an unbounded read
from the asset-link hot path without changing zone ordering, pool capacities,
streaming state, or native engine calls.

### B. Identify and correct a real pool exhaustion (conditional)

If the complete log contains a pool-out event for one of the three full pools,
identify the exact asset type and whether the engine attempted a new allocation.
Only then investigate an engine-compatible capacity increase or deduplication
of the offending asset. Do not enlarge singleton/special pools speculatively.

### C. Resolve a genuinely pending lighting resource (conditional)

If a longer trace shows the same blob stuck in state 1/2 while the level is
otherwise idle, capture its bounded blob record, category, generation, last
wanted tick, stream-pool free space, and zone state. Then determine whether
the resource is missing from the converted fastfile, has an invalid dependency,
or is waiting on the engine streamer. Do not mark it resident or skip the
dependency as a workaround.

### D. Isolate zone ordering and fastfile contents

Compare the `zm_levelcommon` and `zm_ccube` load records, map fastfile file
tables, required XPAK entries, and asset names against a known-good custom map.
If the crash follows only this map, validate its FF/FD pair and asset dependency
closure before changing global loading behavior.

### E. Add targeted phase and native-failure capture

If the bounded-read fix does not resolve the crash, retain the complete log
from before the map request through the next launch. Include the first
`[Stall]`, `[Pools]`, `[Blobs]`, script error, exception, and native error
records. A fresh crash dump or exception PC/register snapshot is required to
attribute a fatal fault. Avoid moving engine-owned operations to worker threads
without verified thread affinity.

## Required follow-up test

On console, use the same BO3 build and the same `zm_ccube` FF/FD pair. Test
the map from a cold main-menu launch, then repeat after loading a different
custom map. Retain the entire log, not just the final lines. Confirm whether
the level reaches gameplay and whether the pending lighting blob transitions
to resident. If it crashes, preserve the first exception/fatal record and
preceding 30 seconds.

## Validation status

- Source-level bounded-read correction: committed with a dedicated regression
  test.
- Host regression: run by the dedicated diagnostics workflow after push.
- PS4 cross-build: must be confirmed by the repository workflow result.
- Console reproduction: pending.
- Root cause of the reported crash: not confirmed.


## Follow-up instrumentation (2026-11-17; PR #36)

The next diagnostic-only change extends the preflight to both `.ff` and
`.fd`. For each extension it records whether a package-local file is
registered, the resolved package path and size, and whether the corresponding
`/app0/zone` fallback exists (including the native stat result). This is
important because the supplied capture opened the FF from the custom-map
folder but opened the FD through the game's zone path; neither open alone
establishes a mismatch or failure.

The Debug file-open hook now records elapsed time and the returned descriptor
for every custom-map package file, including failed opens. The native
`LoadLevelZones` call records its own elapsed time separately from the
pre-call mod preparation and transition snapshots. These measurements will
help identify which boundary stalls in a complete capture; they do not alter
routing or loading behavior.

The focused map-load diagnostic check passes. The SPRX diagnostics workflow
and the full host workflow passed on PR head
`ca9fd4d5f8f901b5b35daeaa5807fc8a31317532`; the complete registered host
inventory reports 41 regression programs with zero failures. The publication
audit covers the complete PR base-to-head diff. No SPRX build or console test
was performed. PR #36 remains subject to final review before merge.


## Catalog-safety follow-up (source implementation; console validation pending)

The map-catalog refresh path has been hardened independently of the crash
hypothesis:

- Directory enumeration now reports open, read, stat, malformed-record,
  overlong-name, capacity, and close outcomes separately. Optional directories
  are ignored only when the kernel reports ENOENT; other open errors abort.
- Directory entries with DT_UNKNOWN are classified with a bounded path and
  sceKernelStat. A failed classification aborts the scan rather than silently
  dropping a directory.
- Scanner failures and fixed-capacity/path truncation propagate to the top-level
  scan. The candidate is rejected instead of publishing a partial catalog.
- Refresh snapshots the previous catalog, generated map Lua, mod-description
  pointers and dirty state under the existing reader/writer exclusion. A
  complete candidate commits and releases old descriptions; a failed candidate
  is discarded and the previous catalog is restored. If snapshot allocation
  fails, refresh returns without modifying the current catalog.
- Startup has no previous catalog to preserve; failed initial scans clear the
  candidate rather than exposing partial entries.
- Scanning remains synchronous. This change does not introduce worker threads
  or claim that double-buffering is safe. Reader lifetime and reclamation still
  need a separate design before any asynchronous scan is considered.

The new host test executes the production directory-enumeration function with
controlled kernel-call results and checks the distinct outcomes, plus source
guards for rollback and description ownership. CI is still the required
validation for the current PR head. No native SPRX build or PS4/PS5 test was
performed. This work improves catalog integrity; it does not establish or fix
the cause of the reported zm_ccube crash.
