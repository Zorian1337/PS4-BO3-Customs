"""Exercise production pool growth; native allocation/index contracts remain untested."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "t7_maps.cpp").read_text(encoding="utf-8")
records = source[source.index("struct AssetPool"):source.index("static bool EqualsNoCase(")]
growth = source[source.index("static PoolGrowth* GrowthFor("):source.index("static void NoteLevelLua(")]
fixture = r'''
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <future>
#include <thread>
#include <vector>
constexpr int kScriptParseTree=54, kRawFileAsset=47, kImageAsset=9;
constexpr uint32_t kImageEntrySize=304, kImagePoolLimit=45979;
constexpr uintptr_t kAssetPools=0;
''' + records + r'''
static AssetPool nativePools[103]{};
static uintptr_t g_base=reinterpret_cast<uintptr_t>(nativePools);
static std::atomic<unsigned> allocations{0};
static bool failAllocation=false;
static std::vector<void*> blocks;
static void T7Log_Write(const char*,...) {}
static void sceKernelUsleep(int us) {
    std::this_thread::sleep_for(std::chrono::microseconds(us));
}
static int sceKernelMmap(int,size_t bytes,int,int,int,int,void** block) {
    ++allocations;
    if (failAllocation) return -1;
    *block=std::calloc(1,bytes);
    if (!*block) return -1;
    blocks.push_back(*block);
    return 0;
}
''' + growth + r'''
int main() {
    // Use the production table, including its atomic member initialization.
    for (auto& entry:g_poolGrowth) {
        assert(!entry.capped.load() && entry.grown==0);
        nativePools[entry.type].size=entry.size;
        nativePools[entry.type].limit=entry.limit;
    }
    auto* material=GrowthFor(6);
    auto* image=GrowthFor(kImageAsset);
    assert(material && material->size==664 && !GrowthFor(4));
    assert(image && image->size==304 && image->limit==45979);
    auto& pool=nativePools[6];

    // The ordinary nonexhausted asset-link path must not wait for the grow lock.
    pool.free=1;
    g_poolGrowthLock.test_and_set();
    auto normal=std::async(std::launch::async,[]{ GrowPool(6); });
    const auto status=normal.wait_for(std::chrono::milliseconds(500));
    g_poolGrowthLock.clear();
    normal.get();
    assert(status==std::future_status::ready && allocations==0);
    pool.free=0;

    // Real free-list creation and publication, with the production byte limits.
    GrowPool(6);
    assert(allocations==1 && material->grown>0 && pool.limit==material->limit+material->grown);
    assert(g_poolGrowthBytes<=1024u*1024u && g_poolGrowthBytes%0x4000==0);
    uintptr_t node=pool.free;
    for (unsigned i=0;i<material->grown;++i) {
        assert(node && node>=reinterpret_cast<uintptr_t>(blocks[0]));
        assert(node-reinterpret_cast<uintptr_t>(blocks[0])==size_t(i)*material->size);
        node=*reinterpret_cast<uintptr_t*>(node);
    }
    assert(!node);
    GrowPool(6); assert(allocations==1); // Existing free entries are reused.

    // Images only grow after exhaustion, use the verified entry layout, and
    // stay within a bounded reserve because streaming diagnostics use a fixed
    // contiguous image table. Check the production free-list construction.
    auto& imagePool=nativePools[kImageAsset];
    imagePool.size=kImageEntrySize-1;
    GrowPool(kImageAsset);
    assert(allocations==1 && image->capped.load()); // Unknown layouts must fail closed.
    image->capped=false;
    imagePool.size=kImageEntrySize;
    const size_t imageBlock=blocks.size();
    GrowPool(kImageAsset);
    assert(allocations==2 && image->grown>0 && image->grown<=image->limit/8);
    assert(imagePool.limit==image->limit+image->grown && imagePool.free);
    node=imagePool.free;
    for(unsigned i=0;i<image->grown;++i) {
        assert(node && node>=reinterpret_cast<uintptr_t>(blocks[imageBlock]));
        assert(node-reinterpret_cast<uintptr_t>(blocks[imageBlock])==size_t(i)*image->size);
        node=*reinterpret_cast<uintptr_t*>(node);
    }
    assert(!node);
    GrowPool(kImageAsset); assert(allocations==2); // The added list is reused.
    // Simulate each block being consumed; each synchronous allocation remains
    // within the production 1 MiB batch limit until the 25% cap is reached.
    while(image->grown<image->limit/4) {
        imagePool.free=0;
        const auto previous=allocations.load();
        GrowPool(kImageAsset);
        assert(allocations==previous+1);
    }
    const auto imageAllocations=allocations.load();
    assert(image->grown==image->limit/4);
    imagePool.free=0; // The reserve cap must not cause a repeated mmap storm.
    GrowPool(kImageAsset);
    assert(allocations==imageAllocations && image->capped.load());

    // Many workers race against a failed expansion. One failure must cap the
    // pool and every other worker must see it without another mmap attempt.
    const auto beforeFailedGrowth=allocations.load();
    failAllocation=true;
    std::atomic<bool> start{false};
    std::vector<std::thread> workers;
    for (unsigned n=0;n<16;++n) workers.emplace_back([&]{
        while(!start.load(std::memory_order_acquire)) std::this_thread::yield();
        for(unsigned i=0;i<1000;++i) GrowPool(22);
    });
    start.store(true,std::memory_order_release);
    for(auto& worker:workers) worker.join();
    assert(allocations==beforeFailedGrowth+1 && GrowthFor(22)->capped.load());
    assert(!nativePools[22].free && nativePools[22].limit==GrowthFor(22)->limit);
    // Budget exhaustion must cap the pool without repeated allocation work.
    failAllocation=false;
    const auto attempts=allocations.load();
    g_poolGrowthBytes=kPoolGrowthBudget-1;
    GrowPool(69);
    assert(GrowthFor(69)->capped.load() && allocations==attempts);
    for(unsigned i=0;i<1000;++i) GrowPool(69);
    assert(allocations==attempts);
    for(void* block:blocks) std::free(block);
    std::puts("PASS: production pool initialization/free list, bounded image reserve, nonblocking normal path and concurrent allocation-failure cap");
}
'''
with tempfile.TemporaryDirectory(prefix="bo3-pool-growth-") as directory:
    cpp, binary = Path(directory) / "check.cpp", Path(directory) / "check"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-pthread", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
