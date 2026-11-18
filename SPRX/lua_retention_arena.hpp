#pragma once

#include <cstddef>

namespace T7LuaRetentionArena
{
// Blocks are append-only and their addresses are stable for the process
// lifetime. Reuse any existing tail that can fit the aligned allocation before
// asking the kernel for another mapping.
template <class Block>
Block* FindBlockWithSpace(Block* first, std::size_t bytes)
{
    for (Block* block = first; block; block = block->next)
    {
        if (block->used <= block->size && bytes <= block->size - block->used)
            return block;
    }
    return nullptr;
}
}
