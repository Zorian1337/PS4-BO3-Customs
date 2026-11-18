#pragma once
#include <atomic>
#include <cstdint>

// One atomic word prevents a new reader racing between close and drain.
class LuaRetentionGate
{
    static constexpr uint32_t kClosing = uint32_t(1) << 31;
    static constexpr uint32_t kReaders = ~kClosing;
    std::atomic<uint32_t> state_{0};
public:
    LuaRetentionGate() = default;
    LuaRetentionGate(const LuaRetentionGate&) = delete;
    LuaRetentionGate& operator=(const LuaRetentionGate&) = delete;
    bool TryEnter()
    {
        uint32_t state = state_.load(std::memory_order_acquire);
        for (;;)
        {
            if ((state & kClosing) || (state & kReaders) == kReaders) return false;
            if (state_.compare_exchange_weak(state, state + 1, std::memory_order_acq_rel,
                                             std::memory_order_acquire)) return true;
        }
    }
    void Leave() { state_.fetch_sub(1, std::memory_order_release); }
    bool BeginClose()
    {
        uint32_t state = state_.load(std::memory_order_acquire);
        for (;;)
        {
            if (state & kClosing) return false;
            if (state_.compare_exchange_weak(state, state | kClosing, std::memory_order_acq_rel,
                                             std::memory_order_acquire)) return true;
        }
    }
    bool IsClosed() const { return (state_.load(std::memory_order_acquire) & kClosing) != 0; }
    bool IsDrained() const { return (state_.load(std::memory_order_acquire) & kReaders) == 0; }
    void Reopen() { state_.fetch_and(kReaders, std::memory_order_release); }
    class Scope
    {
        LuaRetentionGate* gate_ = nullptr;
    public:
        explicit Scope(LuaRetentionGate& gate) : gate_(gate.TryEnter() ? &gate : nullptr) {}
        ~Scope() { if (gate_) gate_->Leave(); }
        Scope(const Scope&) = delete;
        Scope& operator=(const Scope&) = delete;
        explicit operator bool() const { return gate_ != nullptr; }
    };
};
