#include "../xasset_reserve_index.hpp"

#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>

int main()
{
    constexpr uint32_t stride = 32;

    // The native index is unsigned 32-bit, not signed 32-bit. Exercise every
    // table-base residue and indices on both sides of INT32_MAX.
    for (uintptr_t residue = 0; residue < stride; ++residue)
    {
        const uintptr_t base = 0x100000 + residue;
        for (uint32_t index : {1u, 2u, 17u, 524272u, 0x80000001u, UINT32_MAX})
        {
            uint32_t encoded = 0;
            const uintptr_t entry = base + static_cast<uintptr_t>(index) * stride;
            assert(XAssetReserveIndex::TryEncodeIndex(base, entry, stride, encoded));
            assert(encoded == index);
            uintptr_t decoded = 0;
            assert(XAssetReserveIndex::TryDecodeIndex(base, encoded, stride, decoded));
            assert(decoded == entry);
        }
    }

    // Sparse mappings above 4 GiB and indices above the signed boundary remain
    // valid because native consumers zero-extend the uint32_t chain values.
    {
        const uintptr_t base = 0x100000000ull + 13;
        const uintptr_t entry = base + static_cast<uintptr_t>(0xF0000000u) * stride;
        uint32_t encoded = 0;
        assert(XAssetReserveIndex::TryEncodeIndex(base, entry, stride, encoded));
        assert(encoded == 0xF0000000u);
    }

    // The last uint32 index is representable; the next one is not.
    {
        const uintptr_t base = 0x200000000ull + 7;
        uintptr_t entry = base + static_cast<uintptr_t>(UINT32_MAX) * stride;
        uint32_t encoded = 0;
        assert(XAssetReserveIndex::TryEncodeIndex(base, entry, stride, encoded));
        assert(encoded == UINT32_MAX);

        entry = base + (static_cast<uintptr_t>(UINT32_MAX) + 1) * stride;
        encoded = 123;
        assert(!XAssetReserveIndex::TryEncodeIndex(base, entry, stride, encoded));
        assert(encoded == 123);
    }

    // Reject addresses that cannot be represented by the native index rule.
    {
        uint32_t encoded = 77;
        assert(!XAssetReserveIndex::TryEncodeIndex(0x1000, 0x1000, stride, encoded));
        assert(!XAssetReserveIndex::TryEncodeIndex(0x1000, 0x0FFF, stride, encoded));
        assert(!XAssetReserveIndex::TryEncodeIndex(0x1000, 0x1021, stride, encoded));
        assert(!XAssetReserveIndex::TryEncodeIndex(0x1000, 0x1020, 0, encoded));
        assert(encoded == 77);
    }

    // Reject the zero sentinel, zero stride, and pointer overflow.
    {
        uintptr_t decoded = 0x1234;
        assert(!XAssetReserveIndex::TryDecodeIndex(0x1000, 0, stride, decoded));
        assert(!XAssetReserveIndex::TryDecodeIndex(0x1000, 1, 0, decoded));
        assert(decoded == 0x1234);

        const uintptr_t base = std::numeric_limits<uintptr_t>::max() - 15;
        assert(!XAssetReserveIndex::TryDecodeIndex(base, 1, stride, decoded));
        assert(decoded == 0x1234);
    }

    // Validate complete pages at all table-base residues.
    for (uintptr_t residue = 0; residue < stride; ++residue)
    {
        const uintptr_t base = 0x300000 + residue;
        const uintptr_t page = base + 4096 * stride;
        constexpr uintptr_t pageBytes = 1u << 20;
        uint32_t first = 0;
        uint32_t last = 0;
        assert(XAssetReserveIndex::TryValidatePage(base, page, pageBytes, stride, first, last));
        assert(first == 4096);
        assert(last == first + static_cast<uint32_t>(pageBytes / stride) - 1);
    }

    // A page may end exactly at UINT32_MAX but may not cross that boundary.
    {
        const uintptr_t base = 0x400000;
        const uint32_t count = 4;
        const uint32_t firstValid = UINT32_MAX - count + 1;
        const uintptr_t validPage = base + static_cast<uintptr_t>(firstValid) * stride;
        uint32_t first = 0;
        uint32_t last = 0;
        assert(XAssetReserveIndex::TryValidatePage(base, validPage, count * stride,
                                                   stride, first, last));
        assert(first == firstValid && last == UINT32_MAX);

        const uintptr_t invalidPage = base + static_cast<uintptr_t>(UINT32_MAX - 2) * stride;
        first = 41;
        last = 42;
        assert(!XAssetReserveIndex::TryValidatePage(base, invalidPage, count * stride,
                                                    stride, first, last));
        assert(first == 41 && last == 42);
    }

    // mmap returns a page-aligned base; select an interior range with the
    // table's modulo-stride residue.
    for (uintptr_t residue = 0; residue < stride; ++residue)
    {
        const uintptr_t table = 0x200000 + residue;
        const uintptr_t mapping = 0x400000;
        constexpr uintptr_t pageBytes = 4096;
        constexpr uintptr_t mappingBytes = pageBytes + stride - 1;
        uintptr_t page = 0;
        uint32_t first = 0;
        uint32_t last = 0;
        assert(XAssetReserveIndex::TrySelectPage(table, mapping, mappingBytes,
                                                 pageBytes, stride, page, first, last));
        assert(page == mapping + residue);
        assert(page % stride == table % stride);
        assert(first > 0 && last >= first);
    }
    {
        uintptr_t page = 0x55;
        uint32_t first = 66;
        uint32_t last = 77;
        assert(!XAssetReserveIndex::TrySelectPage(0x200001, 0x400000, 4096, 4096,
                                                  stride, page, first, last));
        assert(page == 0x55 && first == 66 && last == 77);
        assert(!XAssetReserveIndex::TrySelectPage(0x20001F, 0x400000, 4096 + stride - 2,
                                                  4096, stride, page, first, last));
        assert(page == 0x55 && first == 66 && last == 77);
    }

    // Construct and walk the exact pointer-linked free list consumed by the
    // native allocator. Every entry is zeroed except its next pointer.
    {
        alignas(32) uint8_t page[32 * 8];
        std::memset(page, 0xA5, sizeof(page));
        const uintptr_t tail = 0x123456789ABCDEF0ull;
        uintptr_t head = 0;
        uint32_t count = 0;
        assert(XAssetReserveIndex::TryBuildFreeList(reinterpret_cast<uintptr_t>(page),
                                                    sizeof(page), stride, tail, head, count));
        assert(head == reinterpret_cast<uintptr_t>(page));
        assert(count == 8);
        for (uint32_t i = 0; i < count; ++i)
        {
            const uintptr_t entry = reinterpret_cast<uintptr_t>(page) + static_cast<uintptr_t>(i) * stride;
            const uintptr_t expected = i + 1 < count ? entry + stride : tail;
            uintptr_t next = 0;
            std::memcpy(&next, reinterpret_cast<const void*>(entry), sizeof(next));
            assert(next == expected);
            for (uint32_t byte = sizeof(uintptr_t); byte < stride; ++byte)
                assert(reinterpret_cast<const uint8_t*>(entry)[byte] == 0);
        }
    }

    // Invalid free-list page shapes do not write memory or publish outputs.
    {
        alignas(32) uint8_t page[64];
        std::memset(page, 0x5A, sizeof(page));
        const uint8_t original[sizeof(page)] = {0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,
                                                0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A};
        uintptr_t head = 0x1111;
        uint32_t count = 22;
        assert(!XAssetReserveIndex::TryBuildFreeList(reinterpret_cast<uintptr_t>(page),
                                                     sizeof(page) - 1, stride, 0, head, count));
        assert(!XAssetReserveIndex::TryBuildFreeList(reinterpret_cast<uintptr_t>(page),
                                                     sizeof(page), sizeof(uint32_t), 0, head, count));
        assert(!XAssetReserveIndex::TryBuildFreeList(UINTPTR_MAX - 15, 32, stride, 0, head, count));
        assert(head == 0x1111 && count == 22);
        assert(std::memcmp(page, original, sizeof(page)) == 0);
    }
}
