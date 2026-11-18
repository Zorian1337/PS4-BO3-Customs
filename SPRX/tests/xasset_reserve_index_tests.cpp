#include "../xasset_reserve_index.hpp"

#include <cassert>
#include <cstdint>
#include <limits>

int main()
{
    constexpr uint32_t stride = 32;

    // The reserve mapping must preserve the table's address residue. Exercise
    // every possible residue rather than testing only naturally aligned bases.
    for (uintptr_t residue = 0; residue < stride; ++residue)
    {
        const uintptr_t base = 0x100000 + residue;
        for (int32_t index : {1, 2, 17, 524272})
        {
            int32_t encoded = -1;
            const uintptr_t entry = base + static_cast<uintptr_t>(index) * stride;
            assert(XAssetReserveIndex::TryEncodePositiveIndex(base, entry, stride, encoded));
            assert(encoded == index);
            assert(base + static_cast<uintptr_t>(encoded) * stride == entry);
        }
    }

    // A sparse address above 4 GiB is valid when the signed index round-trips.
    {
        const uintptr_t base = 0x100000000ull + 13;
        const uintptr_t entry = base + static_cast<uintptr_t>(0x10000000) * stride;
        int32_t encoded = 0;
        assert(XAssetReserveIndex::TryEncodePositiveIndex(base, entry, stride, encoded));
        assert(encoded == 0x10000000);
    }

    // The last positive signed-32 index is representable; the next one is not.
    {
        const uintptr_t base = 0x200000000ull + 7;
        uintptr_t entry = base + static_cast<uintptr_t>(std::numeric_limits<int32_t>::max()) * stride;
        int32_t encoded = 0;
        assert(XAssetReserveIndex::TryEncodePositiveIndex(base, entry, stride, encoded));
        assert(encoded == std::numeric_limits<int32_t>::max());

        entry = base + (static_cast<uintptr_t>(std::numeric_limits<int32_t>::max()) + 1) * stride;
        encoded = 123;
        assert(!XAssetReserveIndex::TryEncodePositiveIndex(base, entry, stride, encoded));
        assert(encoded == 123);
    }

    // Reject addresses that cannot be represented by the native index rule.
    {
        int32_t encoded = 77;
        assert(!XAssetReserveIndex::TryEncodePositiveIndex(0x1000, 0x1000, stride, encoded));
        assert(!XAssetReserveIndex::TryEncodePositiveIndex(0x1000, 0x0FFF, stride, encoded));
        assert(!XAssetReserveIndex::TryEncodePositiveIndex(0x1000, 0x1021, stride, encoded));
        assert(!XAssetReserveIndex::TryEncodePositiveIndex(0x1000, 0x1020, 0, encoded));
        assert(encoded == 77);
    }
}
