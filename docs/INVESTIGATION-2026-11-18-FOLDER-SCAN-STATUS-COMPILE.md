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
