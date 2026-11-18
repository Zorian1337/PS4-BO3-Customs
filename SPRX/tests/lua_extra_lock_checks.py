#!/usr/bin/env python3
"""Execute the production Lua companion-cache lookup and verify lock contention is bounded."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "t7_lua.cpp").read_text(encoding="utf-8")


def extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError(f"unterminated function: {signature}")


FUNCTION = extract_function(SOURCE, "static const RawFileAsset* LuiExtraFor(const char* name)\n{")
assert "if (g_luiExtraLock.exchange(true, std::memory_order_acquire))\n        return nullptr;" in FUNCTION
assert "while (g_luiExtraLock.exchange" not in FUNCTION
assert "sceKernelUsleep" not in FUNCTION

FIXTURE = r"""
#include <atomic>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

struct RawFileAsset { const char* name; int32_t length; int32_t padding; char* buffer; };
struct LuiExtra { char name[160]; RawFileAsset asset; bool found; };
constexpr int kLuiExtraMax = 96;
static LuiExtra g_luiExtra[kLuiExtraMax] = {};
static int g_luiExtraCount = 0;
static std::atomic<bool> g_luiExtraLock{false};
static int readCalls = 0;
static int logCalls = 0;
static bool readSucceeds = true;
static char* ReadLuiCopy(const char*, size_t* used)
{
    ++readCalls;
    if (!readSucceeds) return nullptr;
    const char body[] = "return true";
    char* copy = (char*)malloc(sizeof(body));
    assert(copy);
    memcpy(copy, body, sizeof(body));
    *used = sizeof(body) - 1;
    return copy;
}
static void T7Log_Write(const char*, ...)
{
    ++logCalls;
}
""" + FUNCTION + r"""
int main()
{
    // Contention must return immediately, leave the cache untouched, and avoid
    // filesystem work. The original unbounded sleep loop would hang this test.
    g_luiExtraLock.store(true, std::memory_order_release);
    assert(LuiExtraFor("ui/scripts/first.lua") == nullptr);
    assert(readCalls == 0 && g_luiExtraCount == 0 && logCalls == 0);
    assert(g_luiExtraLock.load(std::memory_order_acquire));
    g_luiExtraLock.store(false, std::memory_order_release);

    const RawFileAsset* first = LuiExtraFor("UI\\Scripts\\First.lua");
    assert(first && first->buffer && first->length == 11);
    assert(std::string(first->name) == "ui/scripts/first.lua");
    assert(std::string(first->buffer, first->length) == "return true");
    assert(readCalls == 1 && g_luiExtraCount == 1 && logCalls == 1);
    assert(!g_luiExtraLock.load(std::memory_order_acquire));
    assert(LuiExtraFor("ui/scripts/first.lua") == first);
    assert(readCalls == 1 && g_luiExtraCount == 1);

    readSucceeds = false;
    assert(LuiExtraFor("ui/scripts/missing.lua") == nullptr);
    assert(readCalls == 2 && g_luiExtraCount == 2);
    assert(LuiExtraFor("ui/scripts/missing.lua") == nullptr);
    assert(readCalls == 2 && g_luiExtraCount == 2); // Cached negative lookup.

    const int before = readCalls;
    assert(LuiExtraFor("../outside.lua") == nullptr);
    assert(LuiExtraFor("ui/../../outside.lua") == nullptr);
    assert(LuiExtraFor(std::string(200, 'x').c_str()) == nullptr);
    assert(readCalls == before);

    g_luiExtraCount = kLuiExtraMax;
    assert(LuiExtraFor("ui/scripts/full.lua") == nullptr);
    assert(readCalls == before);
    puts("PASS: production Lua fallback lookup is nonblocking under contention; cache, miss, path and capacity behavior preserved");
}
"""

with tempfile.TemporaryDirectory(prefix="bo3-lua-extra-lock-") as directory:
    source = Path(directory) / "fixture.cpp"
    binary = Path(directory) / "fixture"
    source.write_text(FIXTURE, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-pthread", str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=15)
