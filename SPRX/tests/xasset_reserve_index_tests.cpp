#include "../xasset_reserve_index.hpp"

#include <cassert>
#include <cstdint>
#include <limits>
#include <initializer_list>

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
            uintptr_t decoded = 0;
            assert(XAssetReserveIndex::TryDecodePositiveIndex(base, encoded, stride, decoded));
            assert(decoded == entry);
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
    // Reject non-positive sentinel indices, zero stride, and pointer overflow.
    {
        uintptr_t decoded = 0x1234;
        assert(!XAssetReserveIndex::TryDecodePositiveIndex(0x1000, 0, stride, decoded));
        assert(!XAssetReserveIndex::TryDecodePositiveIndex(0x1000, -1, stride, decoded));
        assert(!XAssetReserveIndex::TryDecodePositiveIndex(0x1000, 1, 0, decoded));
        assert(decoded == 0x1234);

        const uintptr_t base = std::numeric_limits<uintptr_t>::max() - 15;
        assert(!XAssetReserveIndex::TryDecodePositiveIndex(base, 1, stride, decoded));
        assert(decoded == 0x1234);
    }

    // Validate a complete reserve page, not just one selected entry. The
    // first and last indices bound every fixed-stride entry in between.
    for (uintptr_t residue = 0; residue < stride; ++residue)
    {
        const uintptr_t base = 0x300000 + residue;
        const uintptr_t page = base + 4096 * stride;
        constexpr uintptr_t pageBytes = 1u << 20;
        int32_t first = -1;
        int32_t last = -1;
        assert(XAssetReserveIndex::TryValidatePage(base, page, pageBytes, stride, first, last));
        assert(first == 4096);
        assert(last == first + static_cast<int32_t>(pageBytes / stride) - 1);
    }


    // mmap returns a page-aligned base; choose an interior page start with
    // the same modulo-stride residue as the native table base.
    for (uintptr_t residue = 0; residue < stride; ++residue)
    {
        const uintptr_t table = 0x200000 + residue;
        const uintptr_t mapping = 0x400000;
        constexpr uintptr_t pageBytes = 4096;
        constexpr uintptr_t mappingBytes = pageBytes + stride - 1;
        uintptr_t page = 0;
        int32_t first = -1;
        int32_t last = -1;
        assert(XAssetReserveIndex::TrySelectPage(table, mapping, mappingBytes,
                                                 pageBytes, stride, page, first, last));
        assert(page == mapping + residue);
        assert(page % stride == table % stride);
        assert(first > 0 && last >= first);
    }
    {
        uintptr_t page = 0x55;
        int32_t first = 66;
        int32_t last = 77;
        assert(!XAssetReserveIndex::TrySelectPage(0x200001, 0x400000, 4096, 4096,
                                                  stride, page, first, last));
        assert(page == 0x55 && first == 66 && last == 77);
        assert(!XAssetReserveIndex::TrySelectPage(0x200001, 0x400000, 4096 + stride - 2,
                                                  4096, stride, page, first, last));
        assert(page == 0x55 && first == 66 && last == 77);
    }

    // Reject malformed or partially representable pages without publishing
    // partial index outputs.
    {
        const uintptr_t base = 0x400000;
        int32_t first = 41;
        int32_t last = 42;
        assert(!XAssetReserveIndex::TryValidatePage(base, base + 32, 0, stride, first, last));
        assert(!XAssetReserveIndex::TryValidatePage(base, base + 32, 31, stride, first, last));
        assert(!XAssetReserveIndex::TryValidatePage(base, base + 33, 64, stride, first, last));
        assert(!XAssetReserveIndex::TryValidatePage(base, base + 32, 64, 0, first, last));
        assert(first == 41 && last == 42);

        const uintptr_t page = base + (static_cast<uintptr_t>(std::numeric_limits<int32_t>::max())) * stride;
        assert(!XAssetReserveIndex::TryValidatePage(base, page, 64, stride, first, last));
        assert(first == 41 && last == 42);

        const uintptr_t nearEnd = std::numeric_limits<uintptr_t>::max() - 31;
        assert(!XAssetReserveIndex::TryValidatePage(nearEnd - 32, nearEnd, 64, stride, first, last));
        assert(first == 41 && last == 42);
    }

}
