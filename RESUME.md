# Current SPRX handoff — 2026-11-18

Read `AGENTS.md`, this current handoff, and [the authoritative SPRX roadmap](docs/PS4-STABILITY-ROADMAP-2026-11-17.md) first. The dedicated [stable PS4 test-build handoff](docs/TEST-BUILD-HANDOFF-2026-11-18.md) contains artifact identity, install/rollback procedure and staged console gates.

## Mandatory test-build filename convention

- Every SPRX test build delivered to the user must use the exact filename format `BO3-Customs-dev<N>-DEBUG.sprx` (for example, the next numbered build after dev.69 is `BO3-Customs-dev70-DEBUG.sprx`).
- Preserve exact capitalization, hyphenation and `.sprx` extension. Do not deliver generic names such as `BO3-Customs.sprx`, versioned `v4.00.1` names, or alternate suffixes as the user-facing test binary.
- Apply this name to the actual SPRX file inside the delivered test package and to any standalone SPRX download. Keep build/run IDs, source SHA and checksum in the manifest or handoff, not in the SPRX filename.

## Current candidate and repository state

- **Repository:** `Zorian1337/PS4-BO3-Customs`, default branch `main`.
- **Current SPRX source:** PR #60 and #61 are merged. PR #61 merge commit is `9ba6ca4b592fd4fff16c9f683755894a7ac9c09d`; subsequent main updates are documentation-only, with no SPRX source changes.
- **Latest verified main artifact:** BO3 Auto Build [#44337307357](https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44337307357), source commit `eb3e0fd2881bc0a74f565d9f6d90613daf347019`, artifact ID `14442381395`; ZIP SHA-256 `36e84e726c518dc108cdf865324e19f7cd93dd273a77e975694e859f22da3b48`; embedded SPRX SHA-256 `242895ba2d269c771aefc2a566de91ab85e9b16d3916b0fea9cdabb430d2ae48` (487,216 bytes). Both hashes were independently checked from the downloaded artifact.
- **Merged Lua ownership work:** PR #60 (`715a9f28ed081eda588e9f52fa02c4d1dc762679`) and PR #61 (`9ba6ca4b592fd4fff16c9f683755894a7ac9c09d`). Do not treat PR #60/#61 as open.
- **Validation:** all 47 registered host regressions; ASan/UBSan + TSan source-read gate tests; nested/concurrent reader, timeout/reopen and failed-free/retry tests; all 14 native PS4 translation units; GoldHEN FSELF packaging/inspection; malformed module/container rejection controls. Workflow host, SPRX and final-completeness jobs succeeded.
- **Not proven:** manifest says `console_validated:false`, `sony_signed:false`. No PS4 gameplay test, HKS cache invalidation proof or complete disable/re-enable/reload proof exists yet.
- **Fastest stable route:** use the verified main-branch artifact above. Do not merge unrelated draft PRs just to generate a new build. See [the stable test-build handoff](docs/TEST-BUILD-HANDOFF-2026-11-18.md) for install, rollback and staged testing steps.

## Open work — do not include in first candidate

- PR #39: draft UI transition/image lifetime + dev.69 stream diagnostics; wait-zone publication and image lifetime/reuse remain unresolved.
- PR #40: draft XAssetEntry arithmetic research only; production reserve hook removed; does not fix exhaustion.
- PR #41: draft Blood Run bootstrap regression only; actual GSC/gameplay/pause failures remain.
- PR #47: draft native GPU/clientfield/zone evidence documentation only.
- PR #58/#59: stale duplicate Lua ownership branches; PR #60 is the merged implementation. Do not merge duplicates.
- Other unresolved issues: XAssetEntry exhaustion, GPU fault ownership, mode/zone transitions, clientfield mismatch, host/BG-cache activation, Seven-Eleven multi-mod stall, Buried backend crash and Blood Run gameplay scripts.

## Required console test order

1. Verify artifact ZIP and embedded SPRX SHA-256 values.
2. Back up dev.69 SPRX and existing `/data/BO3-Customs/` files; replace only the SPRX.
3. First boot from internal storage with no mod selected; preserve `log.txt`.
4. Load one known-good mod/map and play briefly.
5. Disable it through the normal Mods UI; verify frontend reload and stock Lua/UI restoration.
6. Re-enable/disable once, then fully restart and verify stock startup.
7. Only after these pass, extend play and test one additional feature at a time. Do not start with bulk stacks, rapid mode switching or known-problem maps.
8. On crash/hang, stop and save logs/test sequence before another launch. Roll back by restoring the backed-up dev.69 SPRX only.

## Mandatory work protocol

For each issue: inspect current source/history/logs; document evidence, root-cause confidence, alternatives, affected files, proposed fix, tradeoffs and tests **before implementation**; finish the SPRX issue inventory; implement with production-path regression tests; run host/sanitizer/source-policy checks; obtain a fresh PS4 target build for every SPRX source change; update roadmap and this handoff. Never claim target or console validation that did not run.

Use connected GitHub tools directly in Chat mode when Work mode is unavailable. Keep private captures, binaries, toolchains, credentials and third-party plugin content out of public commits. No release, FTP deployment or console-validation claim without evidence.

---

## Historical handoff archive




## Historical handoff archive

## Historical handoff archive

## Historical handoff: map-load diagnostics + transactional catalog refresh (PR #36; now merged)

## Catalog refresh safety implementation
