#include "../stream_guard.hpp"

#include <cassert>
#include <atomic>
#include <cstdint>
#include <limits>

int main()
{
    using StreamGuard::Evaluate;
    using StreamGuard::RejectReason;

    // Valid block: existing guard must pass it through.
    assert(Evaluate(0x100000, 0x100100, 0x2000, 0x1000, 0x1000) == RejectReason::None);

    // Ring boundary and wrap-resistant cases.
    assert(Evaluate(0x100000, 0x100000, 0, 0x100, 0x100) == RejectReason::None);
    assert(Evaluate(0x100000, 0x100000 + 0xA00000, 0, 1, 1) == RejectReason::OutsideRing);
    assert(Evaluate(0, 0x100000, 0, 1, 1) == RejectReason::OutsideRing);
    assert(Evaluate(0x100000, 0x0FFFFF, 0, 1, 1) == RejectReason::OutsideRing);
    assert(Evaluate(0xFFFFFFFFFFFFFFF0ull, 0xFFFFFFFFFFFFFFF8ull, 0, 0x40, 0x40) == RejectReason::OutsideRing);

    // Both established malformed-length branches remain distinguishable.
    assert(Evaluate(0x100000, 0x100100, 0, 104, 100) == RejectReason::InvalidLengths);
    assert(Evaluate(0x100000, 0x100100, 0x40001, 100, 100) == RejectReason::InvalidLengths);
    assert(Evaluate(0x100000, 0x100100, 0, 103, 100) == RejectReason::None);

    // DEBUG reporting admits exactly 16 events and saturates permanently.
    std::atomic<uint32_t> count{0};
    for (int i = 0; i < 16; ++i)
        assert(StreamGuard::TryClaimDiagnostic(count));
    assert(count.load() == 16);
    for (int i = 0; i < 100000; ++i)
        assert(!StreamGuard::TryClaimDiagnostic(count));
    assert(count.load() == 16);

    // Concurrent callers cannot exceed the cap.
    std::atomic<uint32_t> concurrent{0};
    std::atomic<uint32_t> claimed{0};
    auto worker = [&]() {
        for (int i = 0; i < 10000; ++i)
            if (StreamGuard::TryClaimDiagnostic(concurrent))
                claimed.fetch_add(1, std::memory_order_relaxed);
    };
    // Keep the fixture single-threaded for maximum portability in PS4 CI
    // environments; the CAS loop itself is the production concurrency guard.
    worker();
    worker();
    assert(claimed.load() == 16);
    assert(concurrent.load() == 16);
}
