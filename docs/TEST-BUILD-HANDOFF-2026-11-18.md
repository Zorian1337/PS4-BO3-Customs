# Stable PS4 testing build handoff — 2026-11-18

**Purpose:** get a newer, reproducible BO3-Customs Debug SPRX onto the PS4 quickly without pulling unfinished experiments into the build. This is a controlled testing candidate, not a release or a claim of console stability.

## Recommended candidate: merged Lua ownership + unload-barrier source

Use the source currently on `main`. It contains the two Lua lifetime changes that were merged and target-build validated:

- PR #60, merge commit `715a9f28ed081eda588e9f52fa02c4d1dc762679`: tracks active mod-zone loads, including first-mod index-zero zones and nested/concurrent loads, so Lua rawfiles are retained even before ownership publication completes. Stock rawfile passthrough remains the intended behavior after mods are disabled.
- PR #61, merge commit `9ba6ca4b592fd4fff16c9f683755894a7ac9c09d`: adds a single-atomic close/read-count gate around the complete borrowed-source read in `RetainModLua()`. New readers fail closed during teardown; existing readers drain for at most 100 ms; timeout or failed zone free aborts unload and reopens the gate; successful frontend teardown reopens before replacement Lua loads.

Current `main` at the time of this handoff is `eb3e0fd2881bc0a74f565d9f6d90613daf347019`. It is one documentation-only commit after PR #61's merge commit; compare shows no source changes after the merged Lua work. The PR #61 target artifact below therefore represents the same SPRX source currently on `main`.

## Existing verified artifact (fastest route)

The exact PR #61 head `f7db33a9e2c25daca8f79df8cbd6cf2c79062a3c` passed BO3 Auto Build run [#44336275249](https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44336275249).

- Artifact: `bo3-sprx-f3546ae7d0a508c990a314705f228ea233ecd6d6-1`
- Artifact ID: `14442530769`
- ZIP SHA-256: `2d3982b64d55afe3e53369b614c88d4b0135f3554b3db0a72df7e440c7182506`
- Embedded `BO3-Customs.sprx`: 487,216 bytes
- SPRX SHA-256: `e04143784dff72a24a00cb5f321594a7e0f4800aaa30414bc088eb2e4b2c9408`
- Workflow jobs: host = success; SPRX = success; final completeness = success; converter = skipped as expected on this fork.
- Validation: all 47 registered host regressions; ASan/UBSan and TSan retention-gate checks; nested/concurrent reader, unmapped-pointer rejection, timeout/reopen and failed-free/retry coverage; all 14 PS4 native translation units; GoldHEN FSELF packaging/inspection; malformed module/container rejection controls.

The manifest explicitly records `console_validated: false` and `sony_signed: false`. This proves target buildability and package validation, not actual PS4 runtime stability, HKS cache invalidation, or complete stock Lua restoration. Do not describe it as console-tested.

## Preferred way to get the next main-branch build

The fastest safe route is to use the existing artifact above; it is already built from the same SPRX source now on `main`. Do not merge unrelated draft PRs just to produce a new build.

If a fresh artifact tied to the current main SHA is desired, push an approved commit to `main` or manually dispatch **BO3 Auto Build** from GitHub Actions. The workflow on `main` runs host/policy checks, compiles the 14 native translation units with the pinned LLVM 18/OpenOrbis toolchain, links/packages the GoldHEN SPRX, validates the native module/container and malformed-container rejection cases, then uploads the SPRX and native evidence artifacts. The default configuration is Debug unless repository variable `BO3_SPRX_CONFIGURATION` overrides it. The fork workflow does not deploy to the console or create a release.

For source changes, require the PR-time checks and a fresh successful target build for the exact merged source. Never treat host-only success as a PS4 target build.

## Do not pull these unfinished changes into this testing candidate

- PR #39: UI transition/image callback lifetime and dev.69 stream diagnostics. It remains draft; wait-zone publication and image lifetime/reuse concerns remain. Do not cherry-pick it into the stable test candidate yet.
- PR #40: XAssetEntry arithmetic/research groundwork only. Its speculative production reserve hook was removed. It does not fix the shared registry exhaustion reported by the nine-mod dev.66 test.
- PR #41: tests the missing `Mods_IsUsingUsermap` bootstrap fallback only. It does not fix the reported Blood Run GSC errors, shutdown, frozen controls or pause behavior.
- PR #47: evidence/documentation only; it does not fix GPU faults, clientfield mismatch or zone ownership.
- PR #58 and #59: older duplicate Lua ownership branches. PR #60 is the merged ownership implementation; do not merge these duplicates.
- PR #60 and #61 are merged. Do not treat their old PR state in historical handoff sections as current.

Also unresolved: XAssetEntry capacity/exhaustion, GPU protection-fault attribution, native mode/zone ownership, clientfield registration mismatch, wait-zone/image callback lifetime, host/BG-cache behavior, Seven-Eleven multi-mod stall, Buried backend crash attribution, and Blood Run gameplay GSC behavior.

## Console installation and rollback procedure

1. Download the verified Actions artifact by artifact ID/name from run #44336275249. Keep the ZIP intact until its SHA-256 has been checked against the value above. Extract only the intended `BO3-Customs.sprx`; do not assume the artifact is a complete `Console.zip` replacement.
2. Back up the currently installed dev.69 SPRX and the existing `/data/BO3-Customs/` configuration/scripts. Preserve maps, mods, saves, `active_mod.txt`, and all other console files.
3. For the first pass, place the candidate SPRX in the existing internal-storage plugin location and keep the current GoldHEN/plugin-loader configuration. Do not move the whole installation to USB/extended storage or change several variables at once.
4. Start BO3 with no selected mod. Confirm the plugin loads, the frontend reaches the normal menu, and the log is created. Copy `/data/BO3-Customs/log.txt` before the next launch.
5. Load one known-good, modest mod/map. Confirm normal menu/gameplay entry and play briefly.
6. Disable that mod through the normal Mods UI. Let the frontend transition finish. Confirm stock menus and stock Lua-backed UI return without crash, reset, stale mod behavior or a stuck transition.
7. Re-enable the same mod once, then disable it again. If both cycles pass, fully exit/restart BO3 and verify stock startup again.
8. Only after those checks, extend the play session and test additional features one at a time. Keep the first session to one mod; do not begin with bulk stacks, repeated rapid mode changes, or known-problem maps.
9. If anything crashes or hangs, stop and preserve the current log and exact test sequence before restarting. Roll back by restoring the backed-up dev.69 SPRX; do not overwrite the rest of the installation.

## What this candidate is and is not expected to improve

It is newer than dev.69 and includes the merged Lua ownership-publication and source-read/unload protections plus the previously merged bounded-name, nonblocking cache, bounded retention-lock and ownership-publication fixes. Those changes directly address unsafe Lua lookup/teardown races.

It is **not** a verified performance upgrade, a fix for the dev.69 XAssetEntry reserve path, or proof that large mod stacks are safe. The retained bytecode arena remains append-only with a finite 32 MiB / 4,096-header budget; no HKS cache invalidation or arena reclamation is attempted. Host-session stack transitions with old mod zones are deliberately deferred where teardown and replacement loading share one native operation.

## Acceptance gates for calling it a playable test build

- [ ] Artifact ZIP and embedded SPRX hashes match the recorded values.
- [ ] Plugin loads and reaches the frontend from a clean BO3 start.
- [ ] One known-good mod loads and reaches gameplay.
- [ ] Disable returns to stock frontend/Lua behavior without crash or stale state.
- [ ] Re-enable/disable repeat succeeds.
- [ ] Full BO3 restart returns to stock startup.
- [ ] Logs and exact artifact/source identity are preserved for any failure.

Passing these gates establishes a useful user-tested candidate for the tested configuration only. It does not clear the unrelated open stability issues or establish safety for maximum mod stacks.
