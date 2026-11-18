#include "../stream_guard.hpp"

#include <atomic>
#include <barrier>
#include <cassert>
#include <cstdint>
#include <thread>
#include <vector>

int main()
{
    // Exercise the exact production claim helper under simultaneous contention.
    // Each round starts every worker together, then lets each worker race for
    // the bounded diagnostic budget many times.
    constexpr unsigned workerCount = 32;
    constexpr unsigned attemptsPerWorker = 64;

    for (unsigned round = 0; round < 8; ++round)
    {
        std::atomic<uint32_t> claimed{0};
        std::atomic<uint32_t> successes{0};
        std::barrier start(static_cast<std::ptrdiff_t>(workerCount));
        std::vector<std::thread> workers;
        workers.reserve(workerCount);

        for (unsigned worker = 0; worker < workerCount; ++worker)
        {
            workers.emplace_back([&] {
                start.arrive_and_wait();
                for (unsigned attempt = 0; attempt < attemptsPerWorker; ++attempt)
                {
                    if (StreamGuard::TryClaimDiagnostic(claimed))
                        successes.fetch_add(1, std::memory_order_relaxed);
                }
            });
        }

        for (auto& worker : workers)
            worker.join();

        assert(successes.load(std::memory_order_relaxed) == 16);
        assert(claimed.load(std::memory_order_relaxed) == 16);

        // The saturated counter must remain saturated; it must not wrap,
        // reopen the budget, or claim additional events.
        for (unsigned attempt = 0; attempt < 1024; ++attempt)
            assert(!StreamGuard::TryClaimDiagnostic(claimed));
        assert(claimed.load(std::memory_order_relaxed) == 16);
    }
}
