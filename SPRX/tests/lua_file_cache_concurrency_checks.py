#!/usr/bin/env python3
"""Run the production companion-Lua cache initializer concurrently under sanitizers."""
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


FUNCTION = extract_function(SOURCE, "static const RawFileAsset* LuiFileFor(const char* name)\n{")
assert "g_luiFileStates[i].compare_exchange_strong" in FUNCTION
assert "std::memory_order_release" in FUNCTION
assert "file.tried" not in FUNCTION

FIXTURE = r"""
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <vector>

struct LuiFile { const char* asset; char* data; };
struct RawFileAsset { const char* name; int32_t length; int32_t padding; const char* buffer; };
static LuiFile g_luiFiles[] = {
    {"ui/t7/utility/pcutility.lua", nullptr},
    {"ui/uieditor/menus/mods/menumodsload.lua", nullptr},
    {"ui/uieditor/widgets/mods/widgetmodsload.lua", nullptr},
    {"ui/uieditor/widgets/mods/entrymodsload.lua", nullptr},
};
static RawFileAsset g_luiAssets[4] = {};
static std::atomic<uint8_t> g_luiFileStates[4] = {};
constexpr uint8_t kLuiFileUninitialized=0, kLuiFileLoading=1, kLuiFileReady=2, kLuiFileFailed=3;
constexpr size_t kLuiFileCount=4;
static std::atomic<int> readCalls{0};
static std::atomic<bool> blockRead{false}, readEntered{false}, releaseRead{false}, readFails{false};
static char* ReadLuiCopy(const char*, size_t* used)
{
    ++readCalls;
    readEntered.store(true, std::memory_order_release);
    while (blockRead.load(std::memory_order_acquire) && !releaseRead.load(std::memory_order_acquire))
        std::this_thread::yield();
    if (readFails.load(std::memory_order_relaxed)) return nullptr;
    const char text[]="return true";
    char* body=(char*)malloc(sizeof(text));
    assert(body);
    memcpy(body,text,sizeof(text));
    *used=sizeof(text)-1;
    return body;
}
""" + FUNCTION + r"""
int main()
{
    // Hold the winning initializer inside its filesystem read. Contenders must
    // observe Loading and return without touching the unpublished entry.
    blockRead.store(true, std::memory_order_release);
    const RawFileAsset* winner=nullptr;
    std::thread first([&]{ winner=LuiFileFor("ui/t7/utility/pcutility.lua"); });
    for(unsigned n=0;n<1000000 && !readEntered.load(std::memory_order_acquire);++n)
        std::this_thread::yield();
    assert(readEntered.load(std::memory_order_acquire));

    std::vector<std::thread> contenders;
    std::atomic<unsigned> skipped{0};
    for(unsigned n=0;n<32;++n)
        contenders.emplace_back([&]{ if(!LuiFileFor("UI/T7/UTILITY/PCUTILITY.LUA")) ++skipped; });
    for(auto& thread:contenders) thread.join();
    assert(skipped==32 && readCalls==1);
    assert(g_luiFileStates[0].load(std::memory_order_acquire)==kLuiFileLoading);

    releaseRead.store(true, std::memory_order_release);
    first.join();
    assert(winner && winner==&g_luiAssets[0]);
    assert(winner->name==g_luiFiles[0].asset && winner->length==11);
    assert(std::strcmp(winner->buffer,"return true")==0);
    assert(g_luiFileStates[0].load(std::memory_order_acquire)==kLuiFileReady);

    contenders.clear();
    std::atomic<unsigned> hits{0};
    for(unsigned n=0;n<32;++n)
        contenders.emplace_back([&]{ if(LuiFileFor("ui/t7/utility/pcutility.lua")==winner) ++hits; });
    for(auto& thread:contenders) thread.join();
    assert(hits==32 && readCalls==1); // One immutable publication, shared by all readers.

    readFails.store(true, std::memory_order_relaxed);
    assert(LuiFileFor("ui/uieditor/menus/mods/menumodsload.lua")==nullptr);
    assert(g_luiFileStates[1].load(std::memory_order_acquire)==kLuiFileFailed);
    const int before=readCalls;
    assert(LuiFileFor("ui/uieditor/menus/mods/menumodsload.lua")==nullptr);
    assert(readCalls==before); // Failed first read remains a cached negative result.
    assert(LuiFileFor("not/a/companion.lua")==nullptr);
    puts("PASS: one initializer wins, readers never observe partial entries, ready publication is shared and failures remain cached");
}
"""

with tempfile.TemporaryDirectory(prefix="bo3-lua-file-cache-") as directory:
    source = Path(directory) / "fixture.cpp"
    source.write_text(FIXTURE, encoding="utf-8")
    for sanitizer in ("address,undefined", "thread"):
        binary = Path(directory) / ("fixture-" + sanitizer.replace(",", "-"))
        subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        f"-fsanitize={sanitizer}", "-pthread", str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=30)
