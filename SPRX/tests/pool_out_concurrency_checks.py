"""Stress the production pool-out once-only latch from concurrent asset workers."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "t7_log.cpp").read_text(encoding="utf-8")
start = source.index("void T7Log_PoolOut(int32_t type)\n{")
opening = source.index("{", start)
depth = 0
end = opening
while end < len(source):
    if source[end] == "{":
        depth += 1
    elif source[end] == "}":
        depth -= 1
        if depth == 0:
            end += 1
            break
    end += 1
assert depth == 0
function = source[start:end]

fixture = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <thread>
#include <vector>

namespace T7Log {
constexpr uintptr_t kAssetPools = 0;
constexpr uint32_t kTypeCount = 103;
static const char* k_typeNames[kTypeCount] = {};
static uintptr_t g_base = 0;
}
static std::atomic<unsigned> writes{0};
static std::atomic<unsigned> poolSnapshots{0};
static void T7Log_Write(const char*, ...) { writes.fetch_add(1, std::memory_order_relaxed); }
static void T7Log_Pools(const char*, uint32_t) { poolSnapshots.fetch_add(1, std::memory_order_relaxed); }

struct AssetPool {
    uint64_t reserved;
    uint32_t size;
    uint32_t limit;
    uint8_t single;
    uint8_t padding[3];
    uint32_t used;
    uintptr_t free;
};
static_assert(sizeof(AssetPool) == 32);
static AssetPool pools[T7Log::kTypeCount]{};
''' + function + r'''

int main() {
    T7Log::g_base = reinterpret_cast<uintptr_t>(pools);
    auto& exhausted = pools[7];
    exhausted.limit = 1;
    exhausted.used = 1;
    exhausted.single = 0;
    exhausted.free = 0;

    constexpr unsigned threadCount = 32;
    constexpr unsigned callsPerThread = 2000;
    std::atomic<unsigned> ready{0};
    std::atomic<bool> go{false};
    std::vector<std::thread> workers;
    for (unsigned i = 0; i < threadCount; ++i) workers.emplace_back([&] {
        ready.fetch_add(1, std::memory_order_release);
        while (!go.load(std::memory_order_acquire)) std::this_thread::yield();
        for (unsigned n = 0; n < callsPerThread; ++n) T7Log_PoolOut(7);
    });
    while (ready.load(std::memory_order_acquire) != threadCount) std::this_thread::yield();
    go.store(true, std::memory_order_release);
    for (auto& worker : workers) worker.join();
    assert(writes.load() == 1);
    assert(poolSnapshots.load() == 1);

    pools[8].limit = 10; pools[8].used = 10; pools[8].free = 1;
    pools[9].limit = 1; pools[9].used = 1; pools[9].single = 1;
    pools[10].limit = 0; pools[10].used = 0;
    T7Log_PoolOut(8); T7Log_PoolOut(9); T7Log_PoolOut(10);
    T7Log_PoolOut(-1); T7Log_PoolOut(103);
    assert(writes.load() == 1 && poolSnapshots.load() == 1);
    std::puts("PASS: concurrent pool-out callbacks emit exactly one diagnostic per exhausted type");
}
'''

with tempfile.TemporaryDirectory(prefix="bo3-pool-out-") as directory:
    cpp = Path(directory) / "check.cpp"
    binary = Path(directory) / "check"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-pthread", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
