#include "../lua_retention_arena.hpp"

#include <cassert>
#include <cstddef>
#include <cstdio>
#include <limits>

struct Block
{
    Block* next;
    std::size_t size;
    std::size_t used;
};

int main()
{
    std::size_t aligned = 0;
    assert(T7LuaRetentionArena::Align16(0, &aligned) && aligned == 0);
    assert(T7LuaRetentionArena::Align16(1, &aligned) && aligned == 16);
    assert(T7LuaRetentionArena::Align16(16, &aligned) && aligned == 16);
    assert(T7LuaRetentionArena::Align16(17, &aligned) && aligned == 32);
    assert(!T7LuaRetentionArena::Align16(static_cast<std::size_t>(-1), &aligned));

    std::size_t required = 0;
    assert(T7LuaRetentionArena::RequiredMappingSize(1, 32, &required) && required == 0x4000);
    assert(T7LuaRetentionArena::RequiredMappingSize(0x4000, 32, &required) && required == 0x8000);
    assert(!T7LuaRetentionArena::RequiredMappingSize(static_cast<std::size_t>(-1), 32, &required));
    assert(!T7LuaRetentionArena::RequiredMappingSize(1, static_cast<std::size_t>(-1), &required));

    // The newest block is too small, but an older block has enough free tail.
    // The production allocator must reuse that tail instead of mapping again.
    Block older{nullptr, 1024, 256};
    Block head{&older, 512, 500};
    assert(T7LuaRetentionArena::FindBlockWithSpace(&head, 768) == &older);

    // Exact-fit allocations are valid and must not require an extra byte.
    older.used = 256;
    assert(T7LuaRetentionArena::FindBlockWithSpace(&head, 768) == &older);
    older.used = 257;
    assert(T7LuaRetentionArena::FindBlockWithSpace(&head, 767) == &older);
    assert(T7LuaRetentionArena::FindBlockWithSpace(&head, 768) == nullptr);

    // Corrupt metadata is skipped without unsigned subtraction underflow.
    Block invalid{nullptr, 64, 65};
    Block valid{&invalid, 128, 64};
    assert(T7LuaRetentionArena::FindBlockWithSpace(&invalid, 1) == nullptr);
    assert(T7LuaRetentionArena::FindBlockWithSpace(&valid, 64) == &valid);
    assert(T7LuaRetentionArena::FindBlockWithSpace(&valid, 65) == nullptr);

    // A request larger than every remaining contiguous tail is rejected.
    Block smallA{nullptr, 256, 128};
    Block smallB{&smallA, 256, 128};
    assert(T7LuaRetentionArena::FindBlockWithSpace(&smallB, 129) == nullptr);
    assert(T7LuaRetentionArena::FindBlockWithSpace(&smallB, 128) == &smallB);

    // Empty request is representable; production always passes a nonzero,
    // 16-byte-aligned allocation after its overflow check.
    assert(T7LuaRetentionArena::FindBlockWithSpace(&head, 0) == &head);

    // No helper arithmetic adds the request to used, so size_t max cannot
    // wrap into an apparent fit.
    assert(T7LuaRetentionArena::FindBlockWithSpace(&head,
        std::numeric_limits<std::size_t>::max()) == nullptr);

    std::puts("PASS: retained Lua arena searches every stable block tail and rejects invalid/oversized ranges");
}
