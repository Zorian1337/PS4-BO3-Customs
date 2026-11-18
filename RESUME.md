# Current SPRX handoff — 2026-11-18

Read `AGENTS.md`, this current handoff, and [the authoritative SPRX roadmap](docs/PS4-STABILITY-ROADMAP-2026-11-17.md) first. The dedicated [stable PS4 test-build handoff](docs/TEST-BUILD-HANDOFF-2026-11-18.md) contains artifact identity, install/rollback procedure and staged console gates.

## Mandatory test-build filename convention

- Every SPRX test build delivered to the user must use the exact filename format `BO3-Customs-dev<N>-DEBUG.sprx` (for example, dev.70 is `BO3-Customs-dev70-DEBUG.sprx` and the next build is `BO3-Customs-dev71-DEBUG.sprx`).
- Build numbering clarification: dev.69 was the build before last, dev.70 is the current build, and the next build must be dev.71. Do not skip or reuse a number.
- Preserve exact capitalization, hyphenation and `.sprx` extension. Do not deliver generic names such as `BO3-Customs.sprx`, versioned `v4.00.1` names, or alternate suffixes as the user-facing test binary.
- Apply this name to the actual SPRX file inside the delivered test package and to any standalone SPRX download. Keep build/run IDs, source SHA and checksum in the manifest or handoff, not in the SPRX filename.

## Current candidate and repository state

- **Repository:** `Zorian1337/PS4-BO3-Customs`, default branch `main`.
- **Current SPRX source:** PR #60 and #61 are merged. PR #61 merge commit is `9ba6ca4b592fd4fff16c9f683755894a7ac9c09d`; subsequent main updates are documentation-only, with no SPRX source changes.
- **Latest verified main artifact:** BO3 Auto Build [#44337307357](https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44337307357), source commit `eb3e0fd2881bc0a74f565d9f6d90613daf347019`, artifact ID `14442381395`; ZIP SHA-256 `36e84e726c518dc108cdf865324e19f7cd93dd273a77e975694e859f22da3b48`; embedded SPRX SHA-256 `242895ba2d269c771aefc2a566de91ab85e9b16d3916b0fea9cdabb430d2ae48` (487,216 bytes). Both hashes were independently checked from the downloaded artifact.
- **Merged Lua ownership work:** PR #60 (`715a9f28ed081eda588e9f52fa02c4d1dc762679`) and PR #61 (`9ba6ca4b592fd4fff16c9f683755894a7ac9c09d`). Do not treat PR #60/#61 as open.
- **Validation:** all 47 registered host regressions; ASan/UBSan + TSan source-read gate tests; nested/concurrent reader, timeout/reopen and failed-free/retry tests; all 14 native PS4 translation units; GoldHEN FSELF packaging/inspection; malformed module/container rejection controls. Workflow host, SPRX and final-completeness jobs succeeded.
- **Not proven:** manifest says `console_validated:false`, `sony_signed:false`. No PS4 gameplay test, HKS cache invalidation proof or complete disable/re-enable/reload proof exists yet.

## 2026-11-18 mod-enable/UI failure investigation

- New investigation: [docs/INVESTIGATION-2026-11-18-MOD-ENABLE-UI-FAILURES.md](docs/INVESTIGATION-2026-11-18-MOD-ENABLE-UI-FAILURES.md).
- The 00:47 server shutdown is the expected queued frontend reload. The 03:17 Lua retention failure is a confirmed PS4 mmap ENOMEM after 27,688,960 bytes mapped; UI Error 81928 is fail-closed handling and the later missing-main error is a partial frontend-build consequence.
- Source review found the retained arena searches only its newest block and can strand free tails in older append-only blocks. Planned correction: search all blocks before mapping, add allocator regressions and bounded usage diagnostics; preserve 32 MiB / 4,096-header caps and never reclaim closure-owned bytecode.
- DS4C's nil-index remains a third-party stripped-bytecode exception with an unknown operand; no safe patch can be inferred from this log. Existing successful-main recovery needs a full failure/recovery/Mods-disable regression.
- At documentation time, the issue inventory and proposed corrections are recorded; implementation and fresh target build are pending. No console test, release, upload or build authorization is implied.


## 2026-11-18 implementation update — mod-enable Lua arena

- Source-only candidate branch: `fix/mod-enable-lua-arena-reuse` (six commits ahead of main, zero behind; not merged). It scans every append-only retention block for a fitting tail before mapping, adds checked size arithmetic, and records retained/mapped/reusable/largest-tail/header diagnostics.
- Added allocator C++ regression coverage and native frontend error-recovery source assertions. The C++ helper logic compiled and passed under g++ C++20 and UBSan; ASan could not start in the local Python runtime. Full repository host checks, target build and console validation remain outstanding.
- Main remains unchanged and at its last target-build-verified source. No SPRX build was started; the workflow requires explicit approval.
- The 00:47 shutdown is expected frontend reload behavior. The 03:17 mmap failure is ENOMEM; the fix targets stranded block tails but the next console trace must establish whether remaining failure is fragmentation or true process memory pressure. DS4C's stripped nil-index remains unfixable without exact matching source/decoded operand evidence.
