#!/usr/bin/env python3
"""Guard the asynchronous mod-variable config-save handoff."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = (root / "t7_config.cpp").read_text(encoding="utf-8")
header = (root / "t7_config.hpp").read_text(encoding="utf-8")
builtins = (root / "t7_builtins.cpp").read_text(encoding="utf-8")

worker = config[config.index("static void* AsyncSaveWorker"):config.index("\nstruct Lock")]
queue = config[config.index("bool T7Config_SaveAsync("):]

assert "bool T7Config_SaveAsync(" in header
assert "bool T7Config_SaveTakeFailure();" in header
assert "scePthreadCreate(&worker" in queue
assert "g_asyncWorkerStarted.store(false" in queue
assert "if (g_asyncQueueLock.test_and_set(std::memory_order_acquire))" in queue
assert queue.index("if (g_asyncQueueLock.test_and_set") < queue.index("memcpy(g_asyncSection")
assert "memcpy(g_asyncLines, lines, linesLength + 1)" in queue
assert "g_asyncPending.store(true, std::memory_order_release)" in queue
assert "scePthreadDetach(worker)" in queue
assert "g_asyncQueueLock.test_and_set(std::memory_order_acquire)" in worker
assert "g_asyncPending.exchange(false, std::memory_order_acq_rel)" in worker
assert "T7Config_Save(g_asyncSection, owns, g_asyncLines)" in worker
assert "g_asyncFailed.store(true, std::memory_order_release)" in worker
assert "g_asyncQueueLock.clear(std::memory_order_release)" in worker
assert "char lines[sizeof(g_asyncLines)]" not in worker

tick = builtins[builtins.index("void T7Builtins_Tick()"):]
assert "T7Config_SaveTakeFailure()" in tick
assert "T7Config_SaveAsync(\"mod variables\", OwnsLine, lines)" in tick
assert "g_varsDirty.store(true, std::memory_order_release)" in tick
assert "T7Config_Save(\"mod variables\"" not in tick
assert "kSaveFrames = 120" in builtins

print("PASS: mod-variable autosave queues an owned snapshot; queue failure preserves dirty state")
