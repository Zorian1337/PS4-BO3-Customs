# SPRX / Lua work

Read RESUME.md first, then only the linked section/source needed for the task.
The user's current request takes precedence over older project guidance within
applicable system/developer constraints. Keep a compact, factual handoff current.

## Scope and privacy

- Work here concerns the BO3-Customs SPRX, companion Lua and their generic tools.
  Preserve the existing upstream converter, but do not add private gameplay-mod
  code, downloaded content, raw logs, console identifiers, reverse-engineered
  third-party plugins, game executables or private research to this repository.
- Keep local captures, toolchains, builds, private notes and credentials in ignored
  locations. Never stage a directory wholesale without reviewing its contents.
- Public engine-analysis notes must be relevant, sanitized and source-supported.
  Never publish a game binary or private plugin reconstruction to support a note.
- Do not rewrite Git history or prune objects as routine cleanup. Inspect disk/Git
  state first; never run gc merely because a previous session mentioned storage.

## Evidence, implementation and performance

- Preserve error evidence privately. Document credible causes, alternative fixes,
  tradeoffs and fallback paths before changing code; distinguish fact from theory.
- Keep desired features and native behavior. Do not replace a defect with disabled
  functionality, permanent restart-only locks, busy polling or unsupported pool
  changes. Recheck working cases and repeat/recovery paths.
- Test first load, unload, reloading, stack changes and switching after gameplay.
  Host mocks and Lua runners do not reproduce BO3 or prove console stability.
- Maintain native arguments/return values, UI ownership and bytecode lifetimes.
  Do not bypass clientfield validation or infer native identity from an offset alone.
- Preserve the internal-first lookup policy for root-level BO3-Customs content.
  Read compiler/linker manifests; do not substitute tools or assume SDK ABIs.

## Efficient sessions

- Start with tools/project_session.py status and the current Git diff.
- For logs, read a compact diagnostic summary, then one relevant incident; keep
  complete evidence on disk. Do not repeatedly paste whole logs into the chat.
- Reuse installed tools. Ask before downloading missing dependencies. No unattended
  model loops, paid API integration or recurring automation is needed to resume.
- Use existing checks and the target build instructions. Change and test source
  before making a candidate, rather than repeatedly rebuilding as a substitute
  for review. Get explicit permission before another SPRX build.

## GitHub and release boundaries

- Fetch upstream main before source work; preserve local changes and compare heads.
  Never force-push or discard another contributor's work to synchronize.
- Current experimental SPRX/Lua source may be published to the fork's main branch.
  Source publication is not build, upload, stability or release approval.
- Do not release testing/buggy plugins. Build/upload/release only within the user's
  explicit approval. Do not auto-create debug releases from source housekeeping.
- Keep binaries out of a Releases folder. Approved distributions belong on GitHub
  Releases with tags, matching source, accurate notes and verified assets.
- Push upstream only reviewed, evidenced fixes. Do not label a guessed crash cause
  a fix, close an unresolved issue or merge unvalidated gameplay experiments.
- Before committing, run tools/project_session.py audit and inspect every staged
  path. Publish source/tests/docs only; no private material or generated artifacts.
