"""Exercise NoteLevelLua against readable, bounded, and page-edge asset names."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "t7_maps.cpp").read_text(encoding="utf-8")
start = source.index("static void NoteLevelLua(uint64_t asset)\n{")
opening = source.index("{", start)
depth = 0
end = opening
while end < len(source):
    if source[end] == "{":
        depth += 1
    elif source[end] == "}":
        depth -= 1
        if depth == 0:
            end += 1
            break
    end += 1
assert depth == 0
function = source[start:end]

fixture = r"""
#include "t7_lua_ownership.hpp"
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <strings.h>
#include <sys/mman.h>
#include <unistd.h>

constexpr int kRawFileAsset = 47;
constexpr size_t kNameMax = 56;
constexpr size_t kInternedMax = 128;
static std::atomic<bool> g_usermapLevel{true};
static uintptr_t guardStart = 0;
static bool RangeReadable(uintptr_t address, size_t bytes)
{
    if (!address || address > UINTPTR_MAX - bytes)
        return false;
    return !guardStart || address < guardStart && bytes <= guardStart - address;
}
static uint64_t scePthreadSelf() { return 1; }
struct ZoneContexts {
    const char* current = "zm_ccube";
    uintptr_t Current(uint64_t) const { return (uintptr_t)current; }
};
static ZoneContexts g_zoneLoadContexts;
struct ListReader {};
static int MapPackageFile(const char*) { return 0; }
static bool EqualsNoCase(const char* a, const char* b) { return strcasecmp(a, b) == 0; }
static T7LuaOwnership::Index g_modLuaOwnership;
""" + function + r"""

static void Invoke(const char* name)
{
    alignas(uintptr_t) unsigned char asset[16] = {};
    uintptr_t header = (uintptr_t)&name;
    const int32_t type = kRawFileAsset;
    memcpy(asset, &type, sizeof(type));
    memcpy(asset + 8, &header, sizeof(header));
    NoteLevelLua((uintptr_t)asset);
}
int main()
{
    const char valid[] = "scripts/zm_ccube/example.lua";
    Invoke(valid);
    assert(g_modLuaOwnership.MayContain(valid));

    const char other[] = "scripts/zm_ccube/example.gsc";
    Invoke(other);
    assert(!g_modLuaOwnership.MayContain(other));

    const long page = sysconf(_SC_PAGESIZE);
    assert(page > 0);
    auto* memory = (char*)mmap(nullptr, (size_t)page * 2, PROT_READ | PROT_WRITE,
                               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(memory != MAP_FAILED);
    assert(mprotect(memory + page, (size_t)page, PROT_NONE) == 0);
    memory[page - 2] = '.';
    memory[page - 1] = 'l';
    guardStart = (uintptr_t)(memory + page);
    Invoke(memory + page - 2); // The missing terminator is behind an unreadable page.
    assert(!g_modLuaOwnership.MayContain(memory + page - 2));
    guardStart = 0;
    assert(munmap(memory, (size_t)page * 2) == 0);

    char tooLong[kInternedMax + 8];
    memset(tooLong, 'a', sizeof(tooLong));
    tooLong[sizeof(tooLong) - 1] = 0;
    Invoke(tooLong);
    assert(!g_modLuaOwnership.MayContain(tooLong));

    puts("PASS: NoteLevelLua copies readable names safely, rejects page-crossing and unterminated names, and retains valid Lua ownership");
}
"""
with tempfile.TemporaryDirectory(prefix="bo3-rawfile-name-") as directory:
    cpp = Path(directory) / "check.cpp"
    binary = Path(directory) / "check"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-pthread", "-I", str(root), str(cpp), "-o", str(binary)],
                   check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
