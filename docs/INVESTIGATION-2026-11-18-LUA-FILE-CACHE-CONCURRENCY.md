# Thread-safe companion Lua cache publication — 2026-11-18

## Finding

`LuiFileFor()` lazily initializes four process-lifetime companion-Lua entries. The previous `LuiFile` records used plain `tried`, `data` and length fields, and the associated `RawFileAsset` was populated field-by-field without synchronization. Concurrent rawfile lookups could both perform filesystem reads, race on the initialization flag and observe partially published metadata.

## Impact and confidence

The unsynchronized fields and multi-step publication are directly visible in source. Concurrent lookup workers are a supported possibility in the loader path. The exact occurrence rate on console is not established, but the data race is a source-level defect if two workers initialize the same entry concurrently.

## Proposed correction

Use one atomic state per cache entry:

- `Uninitialized`: no worker has claimed initialization.
- `Loading`: one worker owns the read and publication.
- `Ready`: the complete `RawFileAsset` is published.
- `Failed`: initialization failed and the prior negative-cache behavior is retained.

The winning worker claims `Uninitialized → Loading` with compare/exchange, performs the existing bounded file read, writes all non-atomic fields, then publishes `Ready` with release ordering. Readers acquire-load the state and return the asset only after observing `Ready`. Contenders during `Loading` or `Failed` return the existing native fallback result rather than blocking. Retained buffers remain process-lifetime so existing Lua closures cannot outlive them.

## Tradeoffs and constraints

- No cache entry may expose a partially initialized `RawFileAsset`.
- No worker waits for another worker's file I/O.
- Failure caching remains consistent with the previous `tried` behavior; retry policy must not silently change.
- The cache remains bounded to the four known companion files.
- Native rawfile lookup arguments and return values must remain unchanged when the optional cache does not serve a file.

## Required validation

- Exercise concurrent first requests against the production `LuiFileFor()` body.
- Assert exactly one filesystem read/initializer wins per entry.
- Assert readers observe only fully initialized `RawFileAsset` metadata after acquire.
- Cover read failure, concurrent failure, already-ready fast path and independent entries.
- Run the full host inventory, diagnostics and PS4 target build.
- Console validation remains separate.
