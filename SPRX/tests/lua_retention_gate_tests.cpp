#include "lua_retention_gate.hpp"
#include <cassert>
#include <cstdint>
#include <thread>
#include <vector>
#include <atomic>
#include <sys/mman.h>
#include <unistd.h>

static uint64_t guardedRead(LuaRetentionGate& gate, const volatile uint64_t* borrowed)
{
    LuaRetentionGate::Scope read(gate);
    if (!read) return 0xBAD0;
    return *borrowed;
}

int main()
{
    LuaRetentionGate gate;
    void* denied = mmap(nullptr, 4096, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(denied != MAP_FAILED);
    assert(gate.BeginClose());
    assert(gate.IsClosed() && gate.IsDrained());
    assert(guardedRead(gate, static_cast<const volatile uint64_t*>(denied)) == 0xBAD0);
    assert(!gate.TryEnter());
    gate.Reopen();
    assert(guardedRead(gate, static_cast<const volatile uint64_t*>(denied)) != 0xBAD0 ? false : true);

    std::atomic<bool> entered{false}, release{false};
    std::thread reader([&] {
        LuaRetentionGate::Scope scope(gate);
        assert(scope);
        entered.store(true, std::memory_order_release);
        while (!release.load(std::memory_order_acquire)) std::this_thread::yield();
    });
    while (!entered.load(std::memory_order_acquire)) std::this_thread::yield();
    assert(gate.BeginClose());
    assert(!gate.IsDrained());
    assert(!gate.TryEnter());
    release.store(true, std::memory_order_release);
    reader.join();
    assert(gate.IsDrained());
    assert(!gate.BeginClose()); // already closed; only owner reopens
    gate.Reopen();
    assert(!gate.IsClosed() && gate.IsDrained());

    std::atomic<unsigned> completed{0};
    std::vector<std::thread> workers;
    for (unsigned i=0;i<8;++i) workers.emplace_back([&] {
        for (unsigned n=0;n<10000;++n) {
            LuaRetentionGate::Scope scope(gate);
            if (scope) completed.fetch_add(1, std::memory_order_relaxed);
        }
    });
    for (auto& worker:workers) worker.join();
    assert(completed.load()==80000 && gate.IsDrained());
    munmap(denied,4096);
}
