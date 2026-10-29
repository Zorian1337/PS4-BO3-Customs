#!/usr/bin/env python3
"""Guard config IO bounds independently of console runtime."""
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "t7_config.cpp").read_text(encoding="utf-8")
read = source[source.index("static int64_t ReadAll("):source.index("static bool WriteAll(")]
write = source[source.index("static bool WriteAll("):source.index("static void Put(")]

assert "if ((uint64_t)got > size - 1 - used)" in read
assert read.index("if ((uint64_t)got > size - 1 - used)") < read.index("used += (size_t)got")
assert "failed = true;" in read
assert "if (put <= 0 || (uint64_t)put > length - used)" in write
assert write.index("if (put <= 0 || (uint64_t)put > length - used)") < write.index("used += (size_t)put")
assert "const bool synced = used == length && sceKernelFsync(fd) >= 0;" in write
print("PASS: config IO rejects invalid native byte counts before advancing buffers")
