#pragma once

#include <atomic>
#include <cstdint>

namespace StreamGuard
{
enum class RejectReason : uint8_t
{
    None,
    OutsideRing,
    InvalidLengths
};

// Keep the arithmetic identical to BlockJob_h's established guard. In
// particular, use subtraction only after proving data >= ring so malformed
// addresses cannot wrap the range check.
inline RejectReason Evaluate(uint64_t ring, uint64_t data, uint32_t unpacked,
                             uint32_t hashed, uint32_t stored)
{
    const bool outside = hashed && (!ring || data < ring ||
                                    data - ring >= 0xA00000 ||
                                    hashed > 0xA00000 - (data - ring));
    if (outside)
        return RejectReason::OutsideRing;

    const bool odd = (hashed > stored && hashed - stored > 3) || unpacked > 0x40000;
    return odd ? RejectReason::InvalidLengths : RejectReason::None;
}

// Saturating, nonblocking claim for the first 16 diagnostic events. Once
// exhausted, the counter stays at the cap and never wraps back into logging.
inline bool TryClaimDiagnostic(std::atomic<uint32_t>& count)
{
    uint32_t current = count.load(std::memory_order_relaxed);
    while (current < 16)
    {
        if (count.compare_exchange_weak(current, current + 1,
                                        std::memory_order_relaxed,
                                        std::memory_order_relaxed))
            return true;
    }
    return false;
}
}
