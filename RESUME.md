# Resume SPRX / Lua development

**Current source: dev.34 DEBUG base plus unbuilt GPU/readiness corrections. Experimental; not a release.**
Native build/format checks and focused host regressions pass. Console stability,
repeated menu switching and native crash resolution are not confirmed.

## Read first

1. [AGENTS.md](AGENTS.md): scope, privacy and publication rules.
2. [Development status](docs/DEVELOPMENT.md): verified findings and next checks.
3. [Workflow](docs/WORKFLOW.md): source validation and build procedure.

Do not reread old conversations or entire logs by default. Inspect the current
branch/diff and the specific source or incident needed for the next task.

## Where to continue

The active task is GPU/native stall investigation. Work mode fetched the changes
made in Chat, preserved the console's persistent crash log privately, and checked
the production texture-readiness hook against an execution fixture.

**Verified correction:** its 180-second fallback now refuses to mark textures
ready while required image/mesh parts are missing or unreadable. Blocked residency
checks retry at most four times per second. Native readiness still wins immediately;
stock maps, native arguments/results and GPU completion state remain unchanged.
The previous source fails the new negative control. Thirty host regression
programs pass; the changed PS4 translation unit passes Debug/Release syntax checks.
No new SPRX was built, uploaded or released. The console still has the old candidate.

**Still open:** this is not a confirmed cure for the captured native compute stall.
The historical PS4 gameplay run reached native texture readiness before the timeout,
so this fallback did not cause that run. The current saved PS5 startup stall has
only five native frames and completion ahead of the requested frame; it must not
be misreported as an outstanding frame fence. See the GPU section in
[development status](docs/DEVELOPMENT.md) for evidence, alternatives and validation.

Next: identify the blocked native wait from matching game/ELF evidence, then compare
one controlled run per case with the matching diagnostics. Do not force GPU fences,
expand pools without exhaustion evidence, or claim the new guard resolved either
stall. Obtain explicit approval before building a candidate. Existing menu re-entry
validation remains open; retain the dev.34 MODS-handler corrections.

## Resume from Chat

Use the connected GitHub repository `Zorian1337/PS4-BO3-Customs`, branch `main`.
Read this file and the linked development status, then fetch only relevant files.
Chat can review or plan from those sources; local files, console FTP, kernel
output and native tools require an available local Work environment. Never claim
those checks ran when that access is unavailable.

Suggested prompt:

> Continue the BO3-Customs SPRX/Lua work from RESUME.md and AGENTS.md on main.
> Continue the GPU/native stall investigation in docs/DEVELOPMENT.md. Inspect
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
