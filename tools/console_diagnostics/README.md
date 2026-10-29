# Console crash/error diagnostics

The normal console session log stays `/data/BO3-Customs/log.txt` and still resets
when BO3 starts. The new DEBUG plugin also appends error context to
`/data/BO3-Customs/crash-errors.log`. Restarting BO3 does not erase that error log.
This native log requires a build containing `error_capture.hpp`; dev.32 does not
have it. No companion Lua change is required.

The persistent log contains UI errors, GSC/CSC runtime errors, engine errors,
missing assets, bytecode failures and detected stalls, with preceding context,
build/mod/zone information and subsequent stack output. Consecutive errors share
a context window. It rotates at 8 MiB to `crash-errors.log.1`, keeping about16 MiB
maximum. It never rotates or renames the normal session log. Error batches are
written and synced by the existing logging worker; the game thread does not
perform new disk IO for each runtime error. Queue overflow is reported explicitly.

## Start collecting

Double-click `WATCH_CONSOLE.cmd` in the repository root. It runs until Ctrl+C.
It reads the two named log files by anonymous FTP and listens to the existing
klog server. It never uploads, deletes console files, reads SPRX binaries or
changes the session log on the console. A game restart does not stop collection;
connection errors retry automatically.

From PowerShell in the repository:

```powershell
python tools/console_diagnostics/console_logs.py capture --minutes 5
python tools/console_diagnostics/console_logs.py capture --once --no-klog
```

Set `BO3_CONSOLE_HOST`, pass `--host CONSOLE_HOST`, or save an ignored
`.local/console.json` containing `{"host":"CONSOLE_HOST"}`. The default ports
are FTP 2121 and klog 3232. No new application or Python package is required.
The klog server must already be running if kernel crash details are wanted.

Local output defaults to `dev12-work/reports/console-diagnostics`, outside Git:

- `session.log`: current full session mirror, replaced after game restarts.
- `device-crash-errors.log`: mirror of the persistent console error log.
- `crash-errors.log`: detailed reports with UI/script/native error context and
  related kernel snippets; preserved across game and reader restarts.
- `status.json`: compact event index, current build/map/mod context and repeats.

Local detailed reports rotate at8 MiB with three backups. Device-error rotation
also preserves one previous local mirror. Remote individual-file reads are capped
at16 MiB; an oversized session is reported without modifying it, and persistent
error collection is still attempted independently. The normal session log on the
console remains untouched, whatever its size.

## Read only what is needed

```powershell
python tools/console_diagnostics/console_logs.py summary
python tools/console_diagnostics/console_logs.py incident E000001
python tools/console_diagnostics/console_logs.py summary --details
```

Use `summary` first, then request an incident rather than repeatedly printing
entire logs. Collection and grouping run locally without model calls. This
reduces chat output; it does not require an automation or paid monitoring job.
Related kernel lines are correlated by capture time and labeled accordingly,
not assumed to be the cause. The Mono banner `SIGSEGV: normal` is not reported
as a game crash. Real kernel fatal records retain signal, registers, backtrace
and module mappings when supplied by the server.

Offline review of a saved run:

```powershell
python tools/console_diagnostics/console_logs.py analyze "saved-session.txt" --klog "saved-klog.txt" --output "../reports/review"
```

Resolve plugin return addresses using its exact matching local ELF:

```powershell
python tools/console_diagnostics/console_logs.py symbolize --elf "build/openorbis/BO3-Customs.elf" --base 0x8033c000 0x80350082
```

On this workstation the command uses the existing WSL Debian LLVM tool. Do not
substitute an ELF from another build or assume the game's eboot matches because
its version label is the same. Function identity needs matching binary evidence.

## Limits and recovery workflow

A process cannot write its own log after the kernel has killed it. The native
error file preserves preceding game-side failures, while an active reader can
save kernel-only crash output. The worker flush interval is200 ms, so immediate
termination or storage failure can still lose the last queued lines. Dropped
context, missing kernel output and file/network failures must remain visible;
no logger can guarantee details the engine never emits.

For each new failure: preserve the files, record exact build/map/mod order,
identify the first error before the cascade, compare multiple possible causes,
and validate a targeted change against working cases. Keep native-game crashes,
mod script exceptions and missing optional assets distinct. A final printed asset
or a successful compile does not establish the root cause or console stability.
Do not publish logs or change a mod's source merely because it was active.

## Checks

```powershell
python tools/console_diagnostics/test_console_logs.py
```

The native host checks are `SPRX/tests/error_capture_checks.py`,
`lua_ownership_index_checks.py`, `mod_lua_retention_checks.py` and
`ui_startup_unload_checks.py`. They exercise production source, but do not replace
PS4/PS5 validation of mod loading, unloading and returning from a match.
