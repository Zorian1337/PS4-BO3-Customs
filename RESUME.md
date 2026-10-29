# Resume SPRX / Lua development

**Current source: `v4.00.1-dev.34 DEBUG`, experimental. This is not a release.**
Native build/format checks and focused host regressions pass. Console stability,
repeated menu switching and native crash resolution are not confirmed.

## Read first

1. [AGENTS.md](AGENTS.md): scope, privacy and publication rules.
2. [Development status](docs/DEVELOPMENT.md): verified findings and next checks.
3. [Workflow](docs/WORKFLOW.md): source validation and build procedure.

Do not reread old conversations or entire logs by default. Inspect the current
branch/diff and the specific source or incident needed for the next task.

## Where to continue

The current candidate addresses menu re-entry after unloading custom UI content:
the console MODS entry now calls its own handler, normalizes its controller and
uses live console selection queries within that menu. Other menus retain their
original callbacks. It also captures LobbyVM initialization failures in the
persistent error log. These are source-verified corrections awaiting console tests.

Next: test **load -> unload -> load** at least three times with one content item,
then repeat after entering/leaving a match. Preserve the first LobbyVM/UI error
and any native stack. Compare the selected and loaded stacks, controller,
frontend generation and active UI/menu functions before changing code again.
Do not assume that the last requested Lua file caused the failure.

## Resume from Chat

Use the connected GitHub repository `Zorian1337/PS4-BO3-Customs`, branch `main`.
Read this file and the linked development status, then fetch only relevant files.
Chat can review or plan from those sources; local files, console FTP, kernel
output and native tools require an available local Work environment. Never claim
those checks ran when that access is unavailable.

Suggested prompt:

> Continue the BO3-Customs SPRX/Lua work from RESUME.md and AGENTS.md on main.
> Inspect the current status/diff and upstream main first. Keep current features,
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
