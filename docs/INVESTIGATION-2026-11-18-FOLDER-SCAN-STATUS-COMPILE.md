# Restore the FolderScanStatus declaration

## Finding

The main-branch PS4 compile in automatic BO3 Auto Build run #75 failed in `SPRX/t7_maps.cpp` at the directory-scan status declaration. The source contained a literal backslash-n sequence after the `// libkernel ENOENT` comment:

```cpp
constexpr int kKernelErrorNoEntry = (int)0x80020002u; // libkernel ENOENT\nenum class FolderScanStatus : uint8_t
```

Because the newline was escaped text rather than a real line break, the compiler treated the enum declaration as part of the comment. This caused the later `FolderScanStatus` references to be undeclared and stopped the target compile.

## Correction

PR #50 replaces the literal escape with a real source newline, restoring the enum declaration without changing enum values or directory-scan behavior.

## Regression coverage

`map_catalog_safety_checks.py` now asserts that the `FolderScanStatus` declaration begins on a real source line and is not swallowed by a preceding line comment. This specifically guards against the host test's previous blind spot: it extracted the enum token from the comment and compiled that extracted slice, so host tests passed while the full target translation unit failed.

## Validation boundary

The source-level correction and host regression passed all five required PR workflows on the prior PR head. PR #50 rebases the exact source/test correction onto the current documented `main`; its checks must rerun. No PS4 target build has yet run after the correction. Run #75 stopped at this compile failure after emitting the `FolderScanStatus` errors; the compiler's error limit means additional target errors may remain. The next buildability gate is the actual PS4 target workflow on this corrected current-main branch.


## Final target validation — 2026-11-18

Corrected source commit: `db015da32383c1f6196e78e04585b00d18f94e03`.
BO3 Auto Build run: [#44247367325](https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/44247367325).

- Host regression and policy/package tests: passed.
- PS4 cross-compiler installation: passed.
- Compile/link/package of all 14 native translation units: passed.
- Native module/container validation and malformed-container controls: passed.
- SPRX artifact upload: passed.
- Native build evidence artifact upload: passed.
- Final workflow completeness gate: passed.

The SPRX is buildable from this exact commit. This does not claim PS4 runtime/console stability; no console test, deployment or release was performed.
