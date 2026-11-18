#pragma once

#include <cstdint>
#include <cstring>
#include <limits>

namespace XAssetReserveIndex
{
// The supported PS4 executable stores all three XAssetEntry chain links as
// uint32_t and zero-extends them before multiplying by the 32-byte stride.
// Index zero is the null sentinel; the full non-zero uint32_t range is valid.
inline bool TryEncodeIndex(uintptr_t tableBase, uintptr_t entryAddress,
                           uint32_t entryStride, uint32_t& encoded)
{
    if (!entryStride || entryAddress <= tableBase)
        return false;

    const uintptr_t delta = entryAddress - tableBase;
    if (delta % entryStride)
        return false;

    const uintptr_t index = delta / entryStride;
    if (!index || index > static_cast<uintptr_t>(std::numeric_limits<uint32_t>::max()))
        return false;

    if (index > (std::numeric_limits<uintptr_t>::max() - tableBase) / entryStride)
        return false;

    if (tableBase + index * entryStride != entryAddress)
        return false;

    encoded = static_cast<uint32_t>(index);
    return true;
}

// Decode the native unsigned index to its exact address. Reject zero and
// pointer overflow without modifying the caller's output.
inline bool TryDecodeIndex(uintptr_t tableBase, uint32_t encoded,
                           uint32_t entryStride, uintptr_t& entryAddress)
{
    if (!encoded || !entryStride)
        return false;

    const uintptr_t index = static_cast<uintptr_t>(encoded);
    if (index > (std::numeric_limits<uintptr_t>::max() - tableBase) / entryStride)
        return false;

    const uintptr_t address = tableBase + index * entryStride;
    uint32_t roundTrip = 0;
    if (!TryEncodeIndex(tableBase, address, entryStride, roundTrip) || roundTrip != encoded)
        return false;

    entryAddress = address;
    return true;
}

// Validate every fixed-stride entry in one reserve page by checking its first
// and last native indices. Since the stride is fixed, the intervening indices
// are contiguous. Mapping ownership and permissions remain the caller's job.
inline bool TryValidatePage(uintptr_t tableBase, uintptr_t pageBase,
                            uintptr_t pageBytes, uint32_t entryStride,
                            uint32_t& firstIndex, uint32_t& lastIndex)
{
    if (!entryStride || !pageBytes || pageBytes % entryStride || pageBase <= tableBase)
        return false;

    if (pageBytes > std::numeric_limits<uintptr_t>::max() - pageBase)
        return false;

    const uintptr_t lastEntry = pageBase + pageBytes - entryStride;
    uint32_t first = 0;
    uint32_t last = 0;
    if (!TryEncodeIndex(tableBase, pageBase, entryStride, first) ||
        !TryEncodeIndex(tableBase, lastEntry, entryStride, last) ||
        last < first)
        return false;

    firstIndex = first;
    lastIndex = last;
    return true;
}

// Select an interior page start from a returned mmap region while preserving
// the table base's modulo-stride residue. The original mapping base/size stays
// with the caller so it can unmap the full span if validation fails.
inline bool TrySelectPage(uintptr_t tableBase, uintptr_t mappingBase,
                          uintptr_t mappingBytes, uintptr_t pageBytes,
                          uint32_t entryStride, uintptr_t& pageBase,
                          uint32_t& firstIndex, uint32_t& lastIndex)
{
    if (!entryStride || !mappingBytes || !pageBytes)
        return false;

    const uintptr_t tableResidue = tableBase % entryStride;
    const uintptr_t mappingResidue = mappingBase % entryStride;
    const uintptr_t offset = (tableResidue + entryStride - mappingResidue) % entryStride;
    if (offset > mappingBytes || pageBytes > mappingBytes - offset ||
        offset > std::numeric_limits<uintptr_t>::max() - mappingBase)
        return false;

    const uintptr_t selected = mappingBase + offset;
    uint32_t first = 0;
    uint32_t last = 0;
    if (!TryValidatePage(tableBase, selected, pageBytes, entryStride, first, last))
        return false;

    pageBase = selected;
    firstIndex = first;
    lastIndex = last;
    return true;
}

// Build a native pointer-linked free list in a mapped reserve page. Each
// XAssetEntry's first eight bytes hold the next pointer while free; the native
// allocator overwrites the low 32-bit type field when it pops an entry. The
// page must already be mapped, writable, and validated by TryValidatePage.
inline bool TryBuildFreeList(uintptr_t pageBase, uintptr_t pageBytes,
                             uint32_t entryStride, uintptr_t tail,
                             uintptr_t& head, uint32_t& entryCount)
{
    if (!pageBase || !pageBytes || !entryStride ||
        entryStride < sizeof(uintptr_t) ||
        pageBytes % entryStride ||
        pageBytes > std::numeric_limits<uintptr_t>::max() - pageBase)
        return false;

    const uintptr_t count = pageBytes / entryStride;
    if (!count || count > std::numeric_limits<uint32_t>::max())
        return false;

    // All validation is complete before the first write, so rejected inputs
    // leave both the page and caller outputs untouched.
    for (uintptr_t i = 0; i < count; ++i)
    {
        const uintptr_t entry = pageBase + i * entryStride;
        const uintptr_t next = i + 1 < count ? entry + entryStride : tail;
        std::memset(reinterpret_cast<void*>(entry), 0, entryStride);
        std::memcpy(reinterpret_cast<void*>(entry), &next, sizeof(next));
    }

    head = pageBase;
    entryCount = static_cast<uint32_t>(count);
    return true;
}

}
