# Bound Lua rawfile asset-name reads

## Finding

The rawfile lookup hook checked only the first 16 bytes of a game-owned asset-name pointer, then scanned up to 191 bytes looking for a terminator. A valid short name near an unmapped page boundary could therefore pass the initial check and fault during the later scan. The missing-config diagnostic also formatted the original pointer directly after checking only four bytes.

## Correction

`CopyAssetName()` now validates each contiguous chunk before reading it. It tries chunks of at most 16 bytes and halves the requested span when a range crosses an unreadable mapping boundary. It accepts only a NUL-terminated name that fits the destination, and never dereferences bytes beyond a validated span. The missing-config diagnostic uses the copied name or a safe placeholder.

Native asset lookup arguments and return behavior are unchanged. Invalid/unreadable names simply skip the plugin's Lua-name classification and continue through the original native lookup.

## Regression coverage

The production helper is extracted into an ASan/UBSan host fixture. It covers normal and non-Lua names, the maximum accepted name, unterminated input, a valid name ending exactly at a readable-page boundary, an unterminated name at that boundary, null/overflow addresses, and undersized output.

## Limits

This is source-level memory-boundary hardening. It is not a native PS4 build or console validation, and it does not change Lua bytecode retention, mod selection, unload, or restoration behavior.
