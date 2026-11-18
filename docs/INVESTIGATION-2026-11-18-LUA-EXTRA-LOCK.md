# Nonblocking optional Lua fallback lookup — 2026-11-18

## Finding

`LuiExtraFor()` is called from the rawfile asset lookup hook. The existing implementation acquired `g_luiExtraLock` with an unbounded loop:

```cpp
while (g_luiExtraLock.exchange(true, std::memory_order_acquire))
    sceKernelUsleep(50);
```

The lock owner performs optional companion-file lookup and filesystem work while holding the lock. A delayed or stalled owner can therefore make every contending asset-lookup worker sleep/retry indefinitely. This can stall the loader even though the PC-side companion Lua fallback is optional.

## Impact and confidence

The unbounded wait is directly visible in source. The lock holder's filesystem work is also visible. This is a confirmed blocking design hazard; whether it caused a reported console stall is not established.

## Proposed correction

Use one nonblocking acquire attempt. If another worker owns the optional cache lock, return the native missing-asset result immediately. Do not wait, sleep, log heavily or enter a second lock path. The lock owner retains its existing release path and successful lookup behavior. A later asset lookup can retry after contention clears.

## Tradeoff

A concurrent first lookup may temporarily fall through to the native missing-asset result. This is preferable to blocking the loader indefinitely, but the regression must prove the native passthrough and later retry behavior. This change must not alter stock rawfile lookup or the companion asset contents.

## Required validation

- Extract and execute the production lock path in a host fixture.
- Verify an already-held lock returns immediately without sleeping or clearing another worker's lock.
- Verify the successful owner path releases the lock on every exit.
- Verify a later request succeeds after contention clears.
- Run the full host inventory, diagnostics and PS4 target build.
- Console validation remains separate.
