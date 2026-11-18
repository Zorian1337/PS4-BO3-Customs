# Lua bytecode retention lock contention — 2026-11-18

## Finding

`RetainModLua()` serializes the process-lifetime bytecode arena behind one global `std::atomic_flag`. The current acquisition loops with `test_and_set()` and `sceKernelUsleep(50)` until the lock becomes available. The critical section includes a linear scan of retained headers, hash/length comparisons, potentially large byte comparisons, arena mapping/allocation, byte copying and list publication.

The same function can call `RetainLuaFailure()` for budget or allocation failures while the lock guard is still alive. That failure path increments counters and writes a diagnostic log before the guard releases the lock.

## Impact and confidence

The unbounded wait and work performed while holding the lock are directly visible in source. A preempted or delayed owner can make another rawfile lookup worker sleep/retry without a deadline. This is a loader-stall hazard, not a proven cause of any specific reported crash.

The current retention test exercises concurrent callers and deduplication but does not deliberately hold the production lock while a second caller attempts retention. Its process timeout would detect a permanent hang, not enforce a bounded lookup.

## Proposed correction

- Replace the unbounded wait loop with one nonblocking acquire attempt.
- If the arena lock is already held, return the existing immutable fail-closed Lua error asset; never return the borrowed rawfile buffer.
- Ensure the contention path does not clear or otherwise alter the lock owned by another worker.
- On arena-budget or mapping failure after acquiring the lock, release the lock before formatting/logging the failure. Do not perform potentially slow diagnostics while holding the arena lock.
- Preserve deduplication, immutable old revisions, process-lifetime mappings, the 32 MiB mapped/logical budget and the 4,096-header cap.

## Tradeoff

A mod Lua lookup that collides with another retention operation may fail closed for that request. This can produce a controlled Lua error, but avoids indefinite loader waiting and never exposes unretained bytecode. The recovery/disable UI must remain available after this error; that is a separate lifecycle validation gate documented in `INVESTIGATION-2026-11-18-LUA-DISABLE-RESTORE.md`.

## Required validation

- Add a production-function regression that pre-holds `g_retainedLuaLock`, calls `RetainModLua()`, and asserts immediate fail-closed return, no arena allocation, no list mutation and no clearing of the other worker's lock.
- Assert failure logging and all budget-failure paths execute after the lock is released.
- Run the concurrent dedup/revision tests, ASan/UBSan and ThreadSanitizer where supported.
- Run all host workflows and a fresh PS4 target build.
- Console validation remains separate.
