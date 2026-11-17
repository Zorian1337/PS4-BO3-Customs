"""Compile the production BlockJob_h and DEBUG trace helper with host stubs."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "t7_maps.cpp").read_text()


def extract_block(source, marker, terminator="}"):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise ValueError(f"unterminated block: {marker}")


EVENT = extract_block(SOURCE, "struct StreamBlockRejected")
HOOK = extract_block(SOURCE, "static uint64_t BlockJob_h(")
TRACE = extract_block(SOURCE, "static void TraceStreamBlockRejections()")

PREFIX = r'''
#include "diagnostic_ring.hpp"
#include <atomic>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using Hook_t = uint64_t (*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                            double,double,double,double,double,double,double,double);
static constexpr uintptr_t kReadRing = 0;
static uint64_t ringBase = 0;
static uintptr_t g_base = (uintptr_t)&ringBase;
static unsigned nativeCalls = 0;
static uint64_t expectedArgs[6] = {};
static uint64_t Native(uint64_t a1,uint64_t a2,uint64_t a3,uint64_t a4,uint64_t a5,uint64_t a6,
                       double x0,double x1,double x2,double x3,double x4,double x5,double x6,double x7)
{
    const uint64_t args[] = {a1,a2,a3,a4,a5,a6};
    for (unsigned i=0;i<6;++i) assert(args[i] == expectedArgs[i]);
    const double values[] = {x0,x1,x2,x3,x4,x5,x6,x7};
    for (unsigned i=0;i<8;++i) assert(values[i] == (double)i + 0.25);
    ++nativeCalls;
    return 0xBADC0FFEEULL;
}
static void* g_blockOriginal = (void*)Native;
static std::vector<std::string> lines;
static void T7Log_Write(const char* format, ...)
{
    char line[1024];
    va_list args;
    va_start(args, format);
    vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    lines.emplace_back(line);
}
'''

GLOBALS = r'''
static DiagnosticRing<StreamBlockRejected, 16> g_streamBlockRejected;
static std::atomic<uint32_t> g_streamRejectAttempts{0};
static std::atomic<uint32_t> g_streamRejectDropped{0};
static std::atomic<uint32_t> g_streamRejectLogged{0};
static std::atomic<bool> g_streamRejectFlush{false};
'''

MAIN = r'''
static void Invoke(uint8_t* job, uint64_t* slot)
{
    uint64_t* jobWords = (uint64_t*)job;
    jobWords[2] = (uintptr_t)slot;
    expectedArgs[0] = (uintptr_t)job;
    expectedArgs[1] = 2; expectedArgs[2] = 3; expectedArgs[3] = 4;
    expectedArgs[4] = 5; expectedArgs[5] = 6;
    const uint64_t result = BlockJob_h(expectedArgs[0],2,3,4,5,6,
                                       0.25,1.25,2.25,3.25,4.25,5.25,6.25,7.25);
    assert(result == 0xBADC0FFEEULL);
}

int main()
{
    static uint8_t ring[0xA00000 + 64];
    static uint8_t job[32];
    static uint8_t slotBytes[0x40040];
    auto* slot = (uint64_t*)slotBytes;
    ringBase = (uintptr_t)ring;

    // Valid input must pass through without mutation or diagnostic.
    *(uint64_t*)(slotBytes + 0x40020) = ringBase + 0x1000;
    *(uint32_t*)(slotBytes + 0x40028) = 128;
    *(uint32_t*)(slotBytes + 0x4002C) = 64;
    *(uint32_t*)(slotBytes + 0x40030) = 64;
    Invoke(job, slot);
    assert(*(uint32_t*)(slotBytes + 0x40028) == 128);
    assert(*(uint32_t*)(slotBytes + 0x4002C) == 64);
    assert(g_streamRejectAttempts.load() == 0);

    // The range-overrun branch must preserve its original zeroing behavior.
    *(uint64_t*)(slotBytes + 0x40020) = ringBase + 0xA00000 - 16;
    *(uint32_t*)(slotBytes + 0x40028) = 128;
    *(uint32_t*)(slotBytes + 0x4002C) = 64;
    *(uint32_t*)(slotBytes + 0x40030) = 64;
    Invoke(job, slot);
    assert(*(uint32_t*)(slotBytes + 0x40028) == 0);
    assert(*(uint32_t*)(slotBytes + 0x4002C) == 0);

    // The inconsistent-length branch must retain the same native mutation.
    *(uint64_t*)(slotBytes + 0x40020) = ringBase + 0x2000;
    *(uint32_t*)(slotBytes + 0x40028) = 128;
    *(uint32_t*)(slotBytes + 0x4002C) = 64;
    *(uint32_t*)(slotBytes + 0x40030) = 59;
    Invoke(job, slot);
    assert(*(uint32_t*)(slotBytes + 0x40028) == 0);
    assert(*(uint32_t*)(slotBytes + 0x4002C) == 0);

    // An oversized unpacked length is the other odd-guard condition.
    *(uint64_t*)(slotBytes + 0x40020) = ringBase + 0x2000;
    *(uint32_t*)(slotBytes + 0x40028) = 0x40001;
    *(uint32_t*)(slotBytes + 0x4002C) = 32;
    *(uint32_t*)(slotBytes + 0x40030) = 32;
    Invoke(job, slot);
    assert(*(uint32_t*)(slotBytes + 0x40028) == 0);
    assert(*(uint32_t*)(slotBytes + 0x4002C) == 0);

    TraceStreamBlockRejections();
    assert(lines.size() == 3);
    assert(lines[0].find("event=stream-block-rejected") != std::string::npos);
    assert(lines[0].find("reason=outside") != std::string::npos);
    assert(lines[1].find("reason=odd") != std::string::npos);
    assert(lines[2].find("reason=odd") != std::string::npos);

    // More rejects cannot exceed the documented 16-event lifetime cap.
    for (unsigned i=0;i<24;++i)
    {
        *(uint64_t*)(slotBytes + 0x40020) = ringBase + 0xA00000 - 8;
        *(uint32_t*)(slotBytes + 0x40028) = 128;
        *(uint32_t*)(slotBytes + 0x4002C) = 64;
        *(uint32_t*)(slotBytes + 0x40030) = 64;
        Invoke(job, slot);
    }
    TraceStreamBlockRejections();
    assert(lines.size() == 16);
    TraceStreamBlockRejections();
    assert(lines.size() == 16);
    assert(nativeCalls == 28);
    puts("PASS: production BlockJob guard branches, mutation, ABI passthrough and 16-event cap");
}
'''


def main():
    assert "event=stream-block-rejected" in TRACE
    assert "g_streamRejectAttempts.compare_exchange_weak" in HOOK
    assert "#ifdef _DEBUG" in HOOK
    with tempfile.TemporaryDirectory(prefix="bo3-stream-guard-") as temp:
        temp = Path(temp)
        source = temp / "stream_guard.cpp"
        binary = temp / "stream_guard"
        source.write_text(PREFIX + EVENT + ";\n" + GLOBALS + "\n" + HOOK + "\n" + TRACE + "\n" + MAIN)
        subprocess.run([
            "g++", "-std=c++20", "-D_DEBUG", "-Wall", "-Wextra", "-Werror", "-O1",
            "-pthread", "-fsanitize=address,undefined", "-I", str(ROOT),
            str(source), "-o", str(binary)
        ], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
