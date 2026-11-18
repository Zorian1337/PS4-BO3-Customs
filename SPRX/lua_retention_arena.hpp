#pragma once

#include <cstddef>

namespace T7LuaRetentionArena
{
inline bool Align16(std::size_t value, std::size_t* aligned)
{
    if (!aligned || value > static_cast<std::size_t>(-1) - 15)
        return false;
    *aligned = (value + 15) & ~static_cast<std::size_t>(15);
    return true;
}

inline bool RequiredMappingSize(std::size_t bytes, std::size_t header, std::size_t* required)
{
    const std::size_t maximum = static_cast<std::size_t>(-1);
    if (!required || header > maximum - 0x3FFF || bytes > maximum - header - 0x3FFF)
        return false;
    *required = (header + bytes + 0x3FFF) & ~static_cast<std::size_t>(0x3FFF);
    return true;
}

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
