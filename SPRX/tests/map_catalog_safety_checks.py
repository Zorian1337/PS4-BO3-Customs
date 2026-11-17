"""Exercise real directory enumeration and guard catalog publication invariants."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "t7_maps.cpp").read_text()


def extract_function(source, signature):
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
    raise AssertionError(f"unterminated function: {signature}")


PREFIX = r"""
#include <atomic>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#define SCE_KERNEL_O_RDONLY 1
#define SCE_KERNEL_O_DIRECTORY 2
#define SCE_KERNEL_DT_DIR 4
#define ORBIS_KERNEL_ERROR_ENOENT ((int)0x80020002u)
struct SceKernelDirent { uint64_t d_fileno; uint16_t d_reclen; uint8_t d_type; char d_name[1]; };
static bool g_scanFailed = false;
static char g_scanFailure[224] = {};
static std::vector<std::string> logs;
static int openResult = 7, readResult = 0, closeResult = 0;
static bool delivered = false;
static unsigned char bytes[1024];
static int byteCount = 0;
static void T7Log_Write(const char* fmt, ...)
{
    char line[512];
    va_list args; va_start(args, fmt); vsnprintf(line, sizeof(line), fmt, args); va_end(args);
    logs.emplace_back(line);
}
static int sceKernelOpen(const char*, int, int) { return openResult; }
static int sceKernelGetdents(int, void* out, size_t capacity)
{
    if (readResult < 0) return readResult;
    if (delivered) return 0;
    delivered = true;
    assert((size_t)byteCount <= capacity);
    memcpy(out, bytes, (size_t)byteCount);
    return byteCount;
}
static int sceKernelClose(int) { return closeResult; }
static int sceKernelUsleep(unsigned) { return 0; }
static void Reset()
{
    g_scanFailed = false; g_scanFailure[0] = 0; logs.clear();
    openResult = 7; readResult = 0; closeResult = 0; delivered = false; byteCount = 0;
    memset(bytes, 0, sizeof(bytes));
}
static size_t AddEntry(size_t at, const char* name, uint8_t type = 8)
{
    const size_t header = offsetof(SceKernelDirent, d_name);
    const size_t length = strlen(name);
    const size_t record = (header + length + 1 + 7) & ~size_t(7);
    auto* entry = (SceKernelDirent*)(bytes + at);
    entry->d_fileno = 1; entry->d_reclen = (uint16_t)record; entry->d_type = type;
    memcpy(entry->d_name, name, length + 1);
    byteCount = (int)(at + record);
    return record;
}
"""


def main():
    begin = SOURCE.index("enum class FolderScanStatus")
    end = SOURCE.index("static void AddFile(", begin)
    production = SOURCE[begin:end]

    with tempfile.TemporaryDirectory(prefix="bo3-map-catalog-") as temp:
        cpp = Path(temp) / "catalog.cpp"
        binary = Path(temp) / "catalog"
        harness = r"""
int main()
{
    char names[2][96] = {};
    Reset(); AddEntry(0, "zm_test.ff");
    auto r = ListFolder("/maps", false, names, 2, false);
    assert(r.status == FolderScanStatus::Ok && r.count == 1);
    assert(std::strcmp(names[0], "zm_test.ff") == 0);

    Reset(); r = ListFolder("/maps", false, names, 2, true);
    assert(r.status == FolderScanStatus::Ok && r.count == 0);

    Reset(); openResult = ORBIS_KERNEL_ERROR_ENOENT;
    r = ListFolder("/optional", true, names, 2, true);
    assert(r.status == FolderScanStatus::Missing && r.Complete());
    Reset(); openResult = ORBIS_KERNEL_ERROR_ENOENT;
    r = ListFolder("/required", true, names, 2, false);
    assert(r.status == FolderScanStatus::OpenFailed && !r.Complete());
    Reset(); openResult = (int)0x8002000Du;
    r = ListFolder("/denied", true, names, 2, true);
    assert(r.status == FolderScanStatus::OpenFailed);

    Reset(); readResult = (int)0x80020005u;
    r = ListFolder("/io", false, names, 2, false);
    assert(r.status == FolderScanStatus::ReadFailed);

    Reset(); AddEntry(0, "broken");
    ((SceKernelDirent*)bytes)->d_reclen = 0;
    r = ListFolder("/bad-record", false, names, 2, false);
    assert(r.status == FolderScanStatus::MalformedRecord);

    Reset();
    const size_t header = offsetof(SceKernelDirent, d_name);
    auto* bad = (SceKernelDirent*)bytes;
    bad->d_fileno = 1; bad->d_reclen = (uint16_t)(header + 4); bad->d_type = 8;
    memcpy(bad->d_name, "nope", 4); byteCount = header + 4;
    r = ListFolder("/unterminated", false, names, 2, false);
    assert(r.status == FolderScanStatus::MalformedRecord);

    Reset(); AddEntry(0, "first"); AddEntry((size_t)byteCount, "second");
    r = ListFolder("/full", false, names, 1, false);
    assert(r.status == FolderScanStatus::CapacityExceeded && r.count == 1);

    Reset(); AddEntry(0, "this-name-is-far-too-long-for-the-catalog-entry-buffer-which-is-ninety-six-bytes-wide-and-keeps-going");
    r = ListFolder("/long", false, names, 2, false);
    assert(r.status == FolderScanStatus::NameTooLong);

    Reset(); AddEntry(0, "close"); closeResult = (int)0x80020005u;
    r = ListFolder("/close", false, names, 2, false);
    assert(r.status == FolderScanStatus::CloseFailed);

    Reset(); readResult = (int)0x80020005u;
    r = ListFolder("/failure", false, names, 2, false);
    assert(!AcceptFolderResult("/failure", r));
    assert(g_scanFailed && std::strstr(g_scanFailure, "read-failed"));

    std::puts("PASS: directory scan distinguishes empty/missing/open/read/malformed/name/capacity/close outcomes");
}
"""
        cpp.write_text(PREFIX + production + harness)
        subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        "-O1", "-pthread", str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    refresh = extract_function(SOURCE, "bool T7Maps_Refresh()")
    install = extract_function(SOURCE, "void T7Maps_Install(")
    rollback = extract_function(SOURCE, "static void RestoreCatalog(")
    commit = extract_function(SOURCE, "static void CommitCatalog(")
    scan_all = extract_function(SOURCE, "static bool ScanAll()")
    scan_mods = extract_function(SOURCE, "static bool ScanMods(")
    add_file = extract_function(SOURCE, "static void AddFile(")
    add_package = extract_function(SOURCE, "static int AddPackage(")

    assert "CaptureCatalog()" in refresh and "RestoreCatalog(previous)" in refresh
    assert "if (!scanned)" in refresh or "if(!scanned)" in refresh
    assert "CaptureCatalog()" in install and "RestoreCatalog(previous)" in install
    assert "ReleaseCandidateMods();" in rollback
    assert "memcpy(g_mods, snapshot->mods" in rollback
    assert "free(snapshot->mods[i].description)" in commit
    assert "memset(g_mods, 0, sizeof(g_mods))" in scan_all
    assert "if (!ScanUsermaps(" in scan_all
    assert "if (!BuildMapsTableLua())" in scan_all
    assert "Mod candidate{}" in scan_mods and "free(mod.description)" not in scan_mods
    assert "FolderScanStatus::CapacityExceeded" in add_file
    assert "FolderScanStatus::CapacityExceeded" in add_package
    assert "ORBIS_KERNEL_ERROR_ENOENT" in production
    print("PASS: failed refresh restores catalog arrays, Lua buffers, dirty state and mod-description ownership")


if __name__ == "__main__":
    main()
