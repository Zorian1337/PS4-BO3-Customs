# SPRX / Lua development workflow

## Before changes

Run `python tools/project_session.py status`. Fetch upstream main and compare
heads without resetting local work. Read RESUME.md and the relevant status item.
In Chat, use connected GitHub access for source review; use local Work when the
next step needs the console, local artifacts or native tools. A saved chat is
helpful context, not a substitute for the current working tree.

Preserve a new issue privately, list credible causes/correction paths and choose
a targeted change with evidence. Keep release-ready claims separate from source
checks and console reports. Update the status once, rather than keeping parallel
outdated per-build notes.

## Check source

`CHECK_SOURCE.cmd` uses an ignored local test command when configured. On Linux:

```sh
BO3_LUA_RUNNER=/path/to/lua5.1 python3 .github/scripts/run_host_checks.py
python3 tools/console_diagnostics/test_console_logs.py
python3 tools/test_project_session.py
```

Host checks need an existing C++20 compiler, Python and an installed Lua runner.
Use `--list` to inspect the check inventory. These are contract/source regressions,
not the BO3 VM. The SDK header check and native artifact comparison are separate
explicit checks that require their actual inputs. Do not install dependencies
or substitute versions silently.

## Native candidate, only after approval

See [the OpenOrbis adapter](../SPRX/openorbis/README.md). The maintained builder is
`.github/scripts/build_sprx.py --configuration Debug`. It may fetch checksum-pinned
public dependencies when not cached; obtain approval for needed downloads first.
Local installed tool/cache settings stay private. Keep the Windows ORBIS project
available; do not publish personal SDK/toolchain archives.

On the fork, pushing reviewed source to `main` starts **BO3 Auto Build**. GitHub
Actions compiles the PS4 SPRX with the pinned OpenOrbis/GoldHEN toolchain and
builds the Windows FF Porter, then retains both as run-specific artifacts for
14 days. A manual workflow run on `main` does the same. This does not create a
release or upload to a console. See [build and notice setup](../.github/BO3_AUTOBUILD.md).

Compile all native translation units, verify the original FSELF against the OELF,
run malformed-container controls, compare loader metadata and bind the artifact
to source hashes. Changes to companion Lua need a matching text/hash verification.
Never read an uploaded SPRX back by FTP to verify it: some servers transform it.
Original container plus transfer completion/metadata are the relevant upload checks.

A build is an experiment, not stability evidence. Before another build, finish the
source review and meaningful checks. Keep source and test versions consistent.
Do not publish a plugin release merely because it compiled or CI passed.

## Console validation

Use a fresh process and one candidate. Test startup, first load, unload, repeated
reload, return from gameplay, mode changes and the relevant controller/peer cases.
Keep the first error and corresponding kernel/native stack. Use generic content
labels in public notes; retain identifying evidence privately.

The normal session log still resets at game start. The separate persistent error
log survives restarts with bounded rotation. See
[diagnostic commands and limits](../tools/console_diagnostics/README.md) and
[native diagnostic design](../SPRX/DIAGNOSTICS.md).

## Publish source, not private evidence

Review `git diff` and every staged path. Run `python tools/project_session.py audit`.
The guard checks additions/changes; it does not silently remove existing upstream
converter data. No raw logs, credentials, private content, research binaries,
compiled plugins, generated caches or build outputs belong in a source commit.

Current candidate source can go to the fork's main branch, marked unvalidated.
Keep upstream submissions to reviewed, evidenced corrections. The upstream's
release automation is not authorization to publish a candidate from this fork.
Approved releases use GitHub tags/assets with accurate notes and provenance;
no stale `Releases/` directory or loose per-build patch notes should accumulate.
The release notice workflow uses the `DISCORD_WEBHOOK_URL` repository secret
and includes the release body and attached download links. Rotate the previously
shared webhook before configuring that secret; never commit its URL.

## End each session

Update RESUME.md / docs/DEVELOPMENT.md with the current state, evidence, checks,
unknowns and next useful action. Keep machine-specific paths and manifests in
ignored `.local/` state. Do not create a second public handoff file with conflicting
state. Do not rerun builds or recrawl old logs just to reconstruct prior work.
