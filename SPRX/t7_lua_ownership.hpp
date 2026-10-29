#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>

namespace T7LuaOwnership
{
// The display/compatibility name list is deliberately not a lifetime index.
// Entries are append-only: a cached closure can outlive an unloaded zone.
class Index
{
    static constexpr size_t kSlots = 8192;
    static constexpr size_t kWords = 16384;
    static constexpr size_t kBits = kWords * 64;
    std::atomic<uint64_t> keys[kSlots]{};
    std::atomic<uint64_t> bits[kWords]{};
    std::atomic<bool> overflow{false};

    static uint64_t Hash(const char* name)
    {
        uint64_t h = 14695981039346656037ull;
        for (; *name; ++name)
        {
            unsigned char c = (unsigned char)*name;
            if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
            if (c == 92) c = '/';
            h = (h ^ c) * 1099511628211ull;
        }
        return h ? h : 1;
    }
    static size_t Bit(uint64_t h, unsigned i)
    {
        h += 0x9e3779b97f4a7c15ull * (i + 1);
        h = (h ^ (h >> 30)) * 0xbf58476d1ce4e5b9ull;
        h = (h ^ (h >> 27)) * 0x94d049bb133111ebull;
        return (size_t)(h ^ (h >> 31)) & (kBits - 1);
    }
public:
    void Mark(const char* name)
    {
        if (!name || !*name) return;
        const uint64_t h = Hash(name);
        for (unsigned i = 0; i < 4; ++i)
        {
            const size_t bit = Bit(h, i);
            bits[bit / 64].fetch_or(1ull << (bit % 64), std::memory_order_release);
        }
        if (overflow.load(std::memory_order_acquire)) return;
        for (size_t i = 0; i < 128; ++i)
        {
            auto& key = keys[(h + i) & (kSlots - 1)];
            uint64_t before = 0;
            if (key.compare_exchange_strong(before, h, std::memory_order_release, std::memory_order_relaxed) || before == h)
                return;
        }
        overflow.store(true, std::memory_order_release);
    }
    bool MayContain(const char* name) const
    {
        if (!name || !*name) return false;
        const uint64_t h = Hash(name);
        for (size_t i = 0; i < 128; ++i)
        {
            const uint64_t key = keys[(h + i) & (kSlots - 1)].load(std::memory_order_acquire);
            if (key == h) return true;
            if (!key) break;
        }
        if (!overflow.load(std::memory_order_acquire)) return false;
        // On saturation, a possible collision means retain, never borrow.
        // Display-list overflow never becomes a blanket retain-all decision.
        for (unsigned i = 0; i < 4; ++i)
        {
            const size_t bit = Bit(h, i);
            if (!(bits[bit / 64].load(std::memory_order_acquire) & (1ull << (bit % 64)))) return false;
        }
        return true;
    }
};
}
