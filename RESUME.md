# Resume SPRX / Lua development

**Active source line: `main`. Current candidate: dev.51 pool diagnostics and
image-pool recovery. It is not a stable release; console validation remains
pending.**

The dev.50 PS5 crash capture showed image-pool exhaustion immediately before a
Database-thread fault. The dev.51 candidate grows only that evidenced pool and
adds entry-size/singleton/free-list details to pool snapshots. Other pools
reviewed from the same capture either already have lazy growth or lack a proven
exhaustion/layout. See [development status](docs/DEVELOPMENT.md). This candidate
does not claim a frame-rate improvement or a confirmed crash fix.

## Read first

1. [AGENTS.md](AGENTS.md): scope, privacy and publication rules.
2. [Development status](docs/DEVELOPMENT.md): verified findings and next checks.
3. [Workflow](docs/WORKFLOW.md): source validation and build procedure.

Do not reread old conversations or entire logs by default. Inspect the current
branch/diff and the specific source or incident needed for the next task.

## Where to continue

The current source review is summarized in
[docs/INVESTIGATION-2026-10-29.md](docs/INVESTIGATION-2026-10-29.md). It records
the LUI callback boundary fix, why the supplied camo and custom-map logs do not
prove a root cause, and what console evidence is still needed. Issue #23 remains
separate; read [docs/INVESTIGATION-23.md](docs/INVESTIGATION-23.md) before
resuming its multi-mod loading and Lua-state restoration work.

Verified source corrections isolate zone/XPAK/asset ownership per loader worker
and restore exact temporary Lua platform flags, including frontend table replacement.
Both regressions fail against the original source and pass after the corrections.
All 34 host programs pass; both earlier changed PS4 units pass Debug/Release
syntax validation. Dev.49 was built and uploaded for testing; console behavior is
not yet confirmed.

The console hang and Reaper's nil operand are **not confirmed resolved**. Preserve
native frontend rebuilding, automatic recovery and bytecode-lifetime protection.
Complete arbitrary-mod Lua-state restoration still requires lifecycle evidence;
do not replace it with broad global/module resets or a restart-only unload lock.

Latest source task: deduplicate the completed provider map list. Dev.49's older
table filter missed provider-appended rows because the external-owner wrappers
returned them unfiltered. The newer Lua keeps the provider builder/callbacks,
filters its completed rows into categories, and removes duplicates by both load
target and displayed title after removing color codes. Provider compatibility and
stats metadata stay attached to the retained row. An existing provider category
control retains ownership; otherwise shared tabs drive its original MapList.

All 34 host regressions passed, with focused checks repeated after the final Lua
cleanup. Restoring the old bypass makes the provider-row regression fail. The
new companion Lua was subsequently uploaded and verified byte-for-byte against
source commit `8f9e31d`. No native SPRX changes or new build were needed.

The user confirmed that duplicate rows are fixed. The latest companion Lua
also preserves provider styling and meaningful compatibility metadata: full
builder input, placeholder-aware row ranking, original colored labels and
original warning/check callbacks. No provider names, palettes or compatibility
tables are encoded in the implementation. The new regression fails before the
fix and passes afterward, including incompatible status zero and conflicting
style/status protection. Existing deduplication and reopen checks still pass.

Next: test `Lua/ui_scripts/mapselect.lua` with the existing dev.49 plugin. Check
colored names and the provider's compatibility warnings while confirming one
row per map under Customs, selection, repeat opens and refreshes. The MapSelect trace reports the input
and final row counts. Separately, resolve the Reaper nil operand from matching
bytecode/debug evidence and review post-unload globals/module ownership. Do not
assume invalid GSC opcode is the first cause: its record precedes the first
printed watchdog warning but lies inside the warning's reported no-progress
interval. Existing GPU findings remain in [development status](docs/DEVELOPMENT.md).

## Resume from Chat

Use the connected GitHub repository `Zorian1337/PS4-BO3-Customs`, branch `testing/dev35-debug-build`.
Read this file and the linked development status, then fetch only relevant files.
Chat can review or plan from those sources; local files, console FTP, kernel
output and native tools require an available local Work environment. Never claim
those checks ran when that access is unavailable.

Suggested prompt:

> Continue the BO3-Customs SPRX/Lua work from RESUME.md and AGENTS.md on testing/dev35-debug-build.
> Continue Issue #23 using docs/INVESTIGATION-23.md. Inspect
> the current status/diff and upstream main first. Keep current features,
> document evidence and alternative fixes, and validate targeted changes. Do not
> publish private material or create a plugin build/release without approval.

Related Chat and Work chats can share a project. See the official
[projects and chats guidance](https://learn.chatgpt.com/docs/projects).

## Resume locally

Run `RESUME_WORK.cmd`, or `python tools/project_session.py status`, for a compact
source/status summary. Run `CHECK_SOURCE.cmd` for the configured host checks.
These commands make no model/API calls and never build, upload or release a SPRX.
Local device/tool paths belong in ignored `.local/` settings, not this file.

Update this file and the status record when evidence changes, including what was
actually tested, remaining uncertainty and the single next useful task. Keep
version change notes with an approved GitHub release, not loose per-build files.
