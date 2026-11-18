"""Exercise bounded production rawfile-name copying at unreadable mapping edges."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "t7_lua.cpp").read_text(encoding="utf-8")
start = SOURCE.index("static bool CopyAssetName(")
end = SOURCE.index("static uint64_t FindXAsset(", start)
HELPER = SOURCE[start:end]
FIND = SOURCE[end:SOURCE.index("static void AddPcUtil();", end)]

assert "CopyAssetName(name, asset, sizeof(asset), &assetLength)" in FIND
assert 'haveAssetName ? asset : "?"' in FIND
assert "text[length]" not in FIND
assert "RangeReadable(base + copied, checked)" in HELPER

FIXTURE = r"""
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <sys/mman.h>
#include <unistd.h>

static uintptr_t readableBegin = 0;
static uintptr_t readableEnd = 0;
static bool RangeReadable(uintptr_t address, size_t bytes)
{
    return address >= readableBegin && address <= readableEnd &&
           bytes <= readableEnd - address;
}
""" + HELPER + r"""
int main()
{
    char output[192] = {};
    size_t length = 999;

    const char valid[] = "ui/test.lua";
    readableBegin = (uintptr_t)valid;
    readableEnd = readableBegin + sizeof(valid);
    assert(CopyAssetName((uint64_t)readableBegin, output, sizeof(output), &length));
    assert(length == 11 && std::strcmp(output, valid) == 0);

    const char notLua[] = "ui/test.txt";
    readableBegin = (uintptr_t)notLua;
    readableEnd = readableBegin + sizeof(notLua);
    assert(CopyAssetName((uint64_t)readableBegin, output, sizeof(output), &length));
    assert(length == 11 && std::strcmp(output, notLua) == 0);

    char maximum[192];
    std::memset(maximum, 'a', sizeof(maximum));
    maximum[191] = 0;
    readableBegin = (uintptr_t)maximum;
    readableEnd = readableBegin + sizeof(maximum);
    assert(CopyAssetName((uint64_t)readableBegin, output, sizeof(output), &length));
    assert(length == 191 && output[191] == 0);

    char unterminated[192];
    std::memset(unterminated, 'x', sizeof(unterminated));
    readableBegin = (uintptr_t)unterminated;
    readableEnd = readableBegin + sizeof(unterminated);
    length = 123;
    assert(!CopyAssetName((uint64_t)readableBegin, output, sizeof(output), &length));
    assert(length == 0 && output[191] == 0);

    const size_t page = (size_t)sysconf(_SC_PAGESIZE);
    char* memory = (char*)mmap(nullptr, page * 2, PROT_READ | PROT_WRITE,
                               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(memory != MAP_FAILED);
    assert(mprotect(memory + page, page, PROT_NONE) == 0);

    // The 12-byte name including NUL ends exactly at the readable page edge.
    char* edge = memory + page - 12;
    std::memcpy(edge, "ui/test.lua", 11);
    edge[11] = 0;
    readableBegin = (uintptr_t)memory;
    readableEnd = (uintptr_t)(memory + page);
    assert(CopyAssetName((uint64_t)(uintptr_t)edge, output, sizeof(output), &length));
    assert(length == 11 && std::strcmp(output, "ui/test.lua") == 0);

    // An unterminated string at the boundary must fail before touching PROT_NONE.
    char* badEdge = memory + page - 8;
    std::memset(badEdge, 'z', 8);
    readableBegin = (uintptr_t)memory;
    readableEnd = (uintptr_t)(memory + page);
    assert(!CopyAssetName((uint64_t)(uintptr_t)badEdge, output, sizeof(output), &length));

    assert(!CopyAssetName(0, output, sizeof(output), &length));
    assert(!CopyAssetName((uint64_t)UINTPTR_MAX - 2, output, sizeof(output), &length));
    assert(!CopyAssetName((uint64_t)readableBegin, output, 1, &length));
    assert(munmap(memory, page * 2) == 0);
    std::puts("PASS: bounded rawfile names, maximum length, unterminated input and unreadable page edges");
}
"""

with tempfile.TemporaryDirectory(prefix="bo3-lua-asset-name-") as directory:
    directory = Path(directory)
    source = directory / "lua_asset_name.cpp"
    binary = directory / "lua_asset_name"
    source.write_text(FIXTURE, encoding="utf-8")
    subprocess.run([
        "g++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-O1",
        "-fsanitize=address,undefined", str(source), "-o", str(binary)
    ], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
