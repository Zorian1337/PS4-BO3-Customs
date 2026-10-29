# BO3 Customs builds, prereleases and Discord notices

## Build from the fork's main branch

Every push to `main` in `Zorian1337/PS4-BO3-Customs`, or a manual run of
**BO3 Auto Build** on `main`, runs the host checks and Linux OpenOrbis/GoldHEN
SPRX build. The SPRX job compiles and inspects all native translation units
with the pinned toolchain. It creates a commit/run-specific SPRX Actions
artifact retained for 14 days. The fork workflow does not create a GitHub
Release or upload to a console. The separate Windows FF Porter build remains
on the upstream converter branch so its tests cannot block the fork's SPRX
artifact.

The same workflow still supports pushes to the upstream repository's
`nexus/standalone-converter` branch. A newer push cancels an older in-progress
build. No game-source fixes are merged to `main` automatically.

On this fork's `main`, the workflow runs the committed SPRX host regression
programs, release-policy and package-verification tests, and the Linux
OpenOrbis/GoldHEN SPRX cross-build of every native translation unit. On the
upstream converter branch only, it also runs the Windows converter checks and
publish profile. Every artifact records its exact source SHA, workflow run,
run attempt, file sizes and SHA-256 checksums. Expired, mismatched, incomplete
or failed builds cannot be published.

## Hosted SPRX builder

The SPRX builds on a GitHub-hosted Ubuntu 24.04 runner with LLVM 18. The
converter builds on a GitHub-hosted Windows runner only on the upstream
converter branch. No personal computer or private ORBIS runner needs to
remain online.

The native job downloads public OpenOrbis 0.5.4 and the pinned GoldHEN CRT
from upstream, verifies their hashes, compiles all 14 native translation
units and packages with `create-fself --lib`. The user's uploaded toolchain
archives are not published. The exact public input URLs, hashes and actual
compiler/linker versions are recorded in each manifest. See the
[native adapter](https://github.com/Hi6795/PS4-BO3-Customs/blob/nexus/standalone-converter/SPRX/openorbis/README.md)
and [dependency lock](openorbis-lock.json).

Candidates default to **Debug** to retain runtime logging and the kernel
and Unity watchdog imports. Set `BO3_SPRX_CONFIGURATION=Release` to select
Release; the selected value appears in the manifest.

The native job saves the compiler log, target-aware `readoelf` inspection
and structured validation report as a CI evidence artifact. It checks
module parameters, imports, exports, entrypoints, relocations and load
segments, then compares every packaged FSELF payload with the inspected
OELF. Its report is bound to the binary SHA-256 in the release manifest.
Missing or mismatched target inspection evidence blocks publication.

The original Windows ORBIS project is retained for manual builds. The build
workflow has no pull-request execution trigger. Any component failure blocks
the `complete` job and automatic publication.

## Discord release notification

`.github/workflows/discord-release.yml` posts a single orange embed when a
GitHub Release is published. It uses the release's actual notes and attached
asset URLs, with the `BO3 Customs Releases` identity, a project avatar, and
mentions disabled. It includes direct asset links and a link to the full release
page. Notification failures do not invalidate or roll back the release.

Create or rotate a Discord webhook, then add it in repository **Settings →
Secrets and variables → Actions → New repository secret** as
`DISCORD_WEBHOOK_URL`. The webhook URL was previously shared in a chat; revoke
that URL and use a newly generated one. Never put the URL in source, workflow
arguments, release notes or logs.

GitHub does not start a second workflow for a release created with
`GITHUB_TOKEN`. The existing manual debug publisher therefore calls the same
notifier directly after publishing. Releases published through GitHub's UI
are handled by the `release: published` workflow.

## Release timing

**BO3 Quiet Release** checks hourly at minute 27 and after build completion.
The default quiet period is **24 hours**, measured from the most recent of:

- The candidate commit's committer timestamp.
- Completion/update of its latest successful build.
- Issue activity since that commit in the fork or upstream repository,
  including comments and changes to closed issues.

Open issues labeled `release-blocker` or `regression` in either repository
block publication regardless of age. Existing unlabeled reports remain
known issues and do not automatically restart the clock unless updated.
Tracker/API errors stop the release check; they are never interpreted as a
quiet tracker.

| Repository Actions variable | Effect |
| --- | --- |
| `BO3_RELEASE_QUIET_HOURS` unset or `24` | Default 24-hour quiet period |
| `BO3_RELEASE_QUIET_HOURS=48` or `72` | Two- or three-day quiet period |
| `BO3_RELEASE_QUIET_HOURS=0` | Publish each fully passing fix without waiting; blocker checks still apply |
| `BO3_AUTO_RELEASE_ENABLED=false` | Pause automatic publication while builds continue |

GitHub scheduling can be delayed. Release timing is checked when the job
actually runs. Artifacts are retained for 14 days; expired artifacts require
a fresh build, which restarts the quiet period.

## Published files

Each new `nexus-ci-<12-character-source-sha>` tag is an **experimental
prerelease** and never replaces GitHub's latest stable release. Files include:

- `BO3-Customs.sprx` and `PS4.FF.Porter.exe` from the exact same build attempt.
- The checksum-pinned upstream `Console.zip` from `.github/bo3-release.json`.
- Both build manifests, a combined `build-info.json`, `LICENSE` and
  `SHA256SUMS.txt`.

The publisher verifies the entire Console.zip checksum, required Lua files,
every Lua file's decompression/CRC and per-file SHA-256, and safe archive
paths. It does not execute the console's HKS interpreter. Updating the
upstream archive requires a reviewed change to the dependency lock; changes
to the same upstream download URL do not silently enter a release.

All assets are checked locally before a draft is created. The branch, build
attempt, tracker and cooldown are checked again before the draft becomes
public. A changed candidate or new report keeps the release unpublished.
An interrupted upload retains a draft for retry. An already published tag is
never overwritten, and no workflow auto-promotes an experimental build to
stable. These checks are snapshots, not an atomic transaction across GitHub
issues and releases.

Passing automation and a quiet tracker do not establish console stability.
The manifests and release notes explicitly mark PS4 BO3 1.33 hardware
validation as pending.

## Maintenance and validation

The hourly issue watch should inspect build failures after each committed
fix and add new host regressions to `.github/scripts/run_host_checks.py`.
Unregistered new Python checks fail CI instead of being silently omitted.

```sh
python3 -m unittest discover -s .github/scripts/tests -v
python3 .github/scripts/run_host_checks.py
```

The host checks need GCC, Clang, Python 3.11+ and liblua5.4. They are distinct
from the Windows offline suite and the OpenOrbis target compile. No live release API
writes occur during the publisher's unit tests.

The automation files also live on the default branch because GitHub runs
scheduled and workflow-run handlers from that branch. That setup commit
contains only automation configuration/scripts/documentation; the candidate
game source stays on `nexus/standalone-converter`.

References: [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners),
[.NET setup](https://github.com/actions/setup-dotnet),
[artifact storage](https://github.com/actions/upload-artifact).
