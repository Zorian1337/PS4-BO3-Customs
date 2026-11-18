#pragma once

#include <cstdint>
#include <limits>

namespace XAssetReserveIndex
{
// Convert an entry address to the positive signed-32-bit index used by the
// native XAssetEntry chains. This validates arithmetic only: it does not
// prove that an address is mapped, owned, initialized, or safe to publish.
inline bool TryEncodePositiveIndex(uintptr_t tableBase, uintptr_t entryAddress,
                                   uint32_t entryStride, int32_t& encoded)
{
    if (!entryStride || entryAddress <= tableBase)
        return false;

    const uintptr_t delta = entryAddress - tableBase;
    if (delta % entryStride)
        return false;

    const uintptr_t index = delta / entryStride;
    if (!index || index > static_cast<uintptr_t>(std::numeric_limits<int32_t>::max()))
        return false;

    // Keep the native decode operation explicit and reject any arithmetic
    // shape that would not round-trip exactly.
    if (index > (std::numeric_limits<uintptr_t>::max() - tableBase) / entryStride)
        return false;

    if (tableBase + index * entryStride != entryAddress)
        return false;

    encoded = static_cast<int32_t>(index);
    return true;
}

// Validate the index range for every fixed-stride entry in one reserve page.
// This is still arithmetic-only: the caller must separately prove that the
// page is mapped, writable, correctly owned, and safe to publish.
inline bool TryValidatePage(uintptr_t tableBase, uintptr_t pageBase,
                            uintptr_t pageBytes, uint32_t entryStride,
                            int32_t& firstIndex, int32_t& lastIndex)
{
    if (!entryStride || !pageBytes || pageBytes % entryStride || pageBase <= tableBase)
        return false;

    if (pageBytes > std::numeric_limits<uintptr_t>::max() - pageBase)
        return false;

    const uintptr_t lastEntry = pageBase + pageBytes - entryStride;
    int32_t first = 0;
    int32_t last = 0;
    if (!TryEncodePositiveIndex(tableBase, pageBase, entryStride, first) ||
        !TryEncodePositiveIndex(tableBase, lastEntry, entryStride, last) ||
        last < first)
        return false;

    firstIndex = first;
    lastIndex = last;
    return true;
}
}
