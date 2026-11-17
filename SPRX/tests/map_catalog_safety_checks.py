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
#include <cstdarg>
#include <cstring>
#include <string>
#include <vector>
#define SCE_KERNEL_O_RDONLY 1
#define SCE_KERNEL_O_DIRECTORY 2
#define SCE_KERNEL_DT_DIR 4
#define SCE_KERNEL_DT_UNKNOWN 0
constexpr int kListedNameMax = 96;
constexpr int kKernelErrorNoEntry = (int)0x80020002u;
struct SceKernelDirent { uint64_t d_fileno; uint16_t d_reclen; uint8_t d_type; char d_name[1]; };
struct SceKernelStat { uint32_t st_mode; };
static bool g_scanFailed = false;
static char g_scanFailure[224] = {};
static std::vector<std::string> logs;
static int openResult = 7, readResult = 0, closeResult = 0, statResult = 0;
static uint32_t statMode = 0040000;
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
static int sceKernelStat(const char*, SceKernelStat* st) { if (statResult < 0) return statResult; st->st_mode = statMode; return 0; }
static int sceKernelUsleep(unsigned) { return 0; }
static void Reset()
{
    g_scanFailed = false; g_scanFailure[0] = 0; logs.clear();
    openResult = 7; readResult = 0; closeResult = 0; statResult = 0; statMode = 0040000; delivered = false; byteCount = 0;
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

    Reset(); openResult = kKernelErrorNoEntry;
    r = ListFolder("/optional", true, names, 2, true);
    assert(r.status == FolderScanStatus::Missing && r.Complete());
    Reset(); openResult = kKernelErrorNoEntry;
    r = ListFolder("/required", true, names, 2, false);
    assert(r.status == FolderScanStatus::OpenFailed && !r.Complete());
    Reset(); openResult = (int)0x8002000Du;
    r = ListFolder("/denied", true, names, 2, true);
    assert(r.status == FolderScanStatus::OpenFailed);

    Reset(); readResult = (int)0x80020005u;
    r = ListFolder("/io", false, names, 2, false);
    assert(r.status == FolderScanStatus::ReadFailed);

    Reset(); byteCount = 8;
    r = ListFolder("/short-header", false, names, 2, false);
    assert(r.status == FolderScanStatus::MalformedRecord);
    Reset(); byteCount = 9;
    r = ListFolder("/short-header", false, names, 2, false);
    assert(r.status == FolderScanStatus::MalformedRecord);

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

    Reset(); AddEntry(0, "unknown-dir", SCE_KERNEL_DT_UNKNOWN);
    statMode = 0040000;
    r = ListFolder("/unknown-dir", true, names, 2, false);
    assert(r.status == FolderScanStatus::Ok && r.count == 1);
    Reset(); AddEntry(0, "unknown-file", SCE_KERNEL_DT_UNKNOWN);
    statMode = 0100000;
    r = ListFolder("/unknown-file", false, names, 2, false);
    assert(r.status == FolderScanStatus::Ok && r.count == 1);
    Reset(); AddEntry(0, "unknown-denied", SCE_KERNEL_DT_UNKNOWN);
    statResult = (int)0x8002000Du;
    r = ListFolder("/unknown-denied", true, names, 2, false);
    assert(r.status == FolderScanStatus::StatFailed);

    Reset(); readResult = (int)0x80020005u;
    r = ListFolder("/failure", false, names, 2, false);
    assert(!AcceptFolderResult("/failure", r));
    assert(g_scanFailed && std::strstr(g_scanFailure, "read-failed"));

    std::puts("PASS: directory scan distinguishes empty/missing/open/read/stat/malformed/name/capacity/close outcomes");
}
"""
        cpp.write_text(PREFIX + production + harness)
        subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        "-O1", "-pthread", str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    append_functions = (
        extract_function(SOURCE, "static bool AppendChecked(")
        + "\n"
        + extract_function(SOURCE, "static bool AppendLuaStringChecked(")
    )
    append_harness = r"""
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <cstring>
int main()
{
    char small[4] = {};
    size_t used = 0;
    assert(AppendChecked(small, sizeof(small), &used, "abc"));
    assert(std::strcmp(small, "abc") == 0 && used == 3);
    assert(!AppendChecked(small, sizeof(small), &used, "x"));

    char exact[6] = {};
    used = 0;
    assert(AppendLuaStringChecked(exact, sizeof(exact), &used, "abc"));
    assert(std::strcmp(exact, "\"abc\"") == 0 && used == 5);

    char tooSmall[5] = {};
    used = 0;
    assert(!AppendLuaStringChecked(tooSmall, sizeof(tooSmall), &used, "abc"));
    assert(tooSmall[used] == 0);
    std::puts("PASS: custom-map Lua append helpers detect exact-fit and truncation boundaries");
}
"""
    with tempfile.TemporaryDirectory(prefix="bo3-map-lua-bounds-") as temp:
        cpp = Path(temp) / "append.cpp"
        binary = Path(temp) / "append"
        cpp.write_text("#include <cstddef>\n#include <cstdio>\n" + append_functions + append_harness)
        subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    root_functions = (
        extract_function(SOURCE, "static bool PathUsesDataRoot(")
        + "\n"
        + extract_function(SOURCE, "static bool CatalogUsesDataRoot(")
        + "\n"
        + extract_function(SOURCE, "static bool CheckDataRoot(")
    )
    root_prefix = r"""
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <cstring>
#define SCE_KERNEL_O_RDONLY 1
#define SCE_KERNEL_O_DIRECTORY 2
constexpr int kKernelErrorNoEntry = (int)0x80020002u;
enum class FolderScanStatus { OpenFailed, CloseFailed };
struct Package { char folder[64]; char alternate[64]; };
struct Mod { char folder[64]; char alternate[64]; };
static Package g_packages[4];
static Mod g_mods[4];
static int g_packageCount=0, g_modCount=0;
static bool g_scanFailed=false;
static int openResult=4, closeResult=0;
static void MarkScanFailure(const char*, FolderScanStatus, int) { g_scanFailed=true; }
static int sceKernelOpen(const char*, int, int) { return openResult; }
static int sceKernelClose(int) { return closeResult; }
"""
    root_main = r"""
int main()
{
    bool present=true;
    openResult=kKernelErrorNoEntry;
    assert(CheckDataRoot("/usb0/BO3-Customs",false,&present) && !present);

    std::strcpy(g_packages[0].folder,"/usb0/BO3-Customs/usermaps/zm_test");
    g_packageCount=1; g_scanFailed=false;
    assert(!CheckDataRoot("/usb0/BO3-Customs",false,&present));
    assert(g_scanFailed);

    std::strcpy(g_packages[0].folder,"/usb01/BO3-Customs/usermaps/zm_other");
    g_scanFailed=false;
    assert(CheckDataRoot("/usb0/BO3-Customs",false,&present) && !present);
    assert(!g_scanFailed);

    std::strcpy(g_mods[0].folder,"/ext2/BO3-Customs/mods/test");
    g_modCount=1; g_scanFailed=false; openResult=8; closeResult=0;
    assert(CheckDataRoot("/ext2/BO3-Customs",false,&present) && present);

    openResult=kKernelErrorNoEntry; present=true; g_scanFailed=false;
    assert(!CheckDataRoot("/ext2/BO3-Customs",true,&present));
    assert(g_scanFailed);

    openResult=8; closeResult=(int)0x80020005u; g_scanFailed=false;
    assert(!CheckDataRoot("/ext2/BO3-Customs",false,&present));
    assert(g_scanFailed);
    std::puts("PASS: missing populated storage roots and mid-scan unmounts reject refresh");
}
"""
    with tempfile.TemporaryDirectory(prefix="bo3-map-root-presence-") as temp:
        cpp = Path(temp) / "roots.cpp"
        binary = Path(temp) / "roots"
        cpp.write_text(root_prefix + root_functions + root_main)
        subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    transaction_start = SOURCE.index("struct CatalogSnapshot")
    transaction_end = SOURCE.index("static bool PathUsesDataRoot(", transaction_start)
    transaction = SOURCE[transaction_start:transaction_end]
    transaction_prefix = r"""
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
constexpr int kMaxPackages = 4, kMaxFiles = 8, kMaxMods = 4;
struct Package { int marker; };
struct File { int marker; };
struct Movie { int marker; };
struct Mod { int marker; char* description; };
static Package g_packages[kMaxPackages];
static File g_files[kMaxFiles];
static Movie g_movies[64];
static Mod g_mods[kMaxMods];
static int g_packageCount=0, g_fileCount=0, g_movieCount=0, g_modCount=0;
static int g_levelCommon=-1, g_listedMaps=0;
static char g_customMapsLua[64]={}, g_mapsTableLua[96]={};
static std::atomic<bool> g_modsLuaDirty{false};
static bool g_scanCandidateActive = false;
"""
    transaction_main = r"""
int main()
{
    g_packageCount=1; g_packages[0].marker=41;
    g_fileCount=1; g_files[0].marker=42;
    g_movieCount=1; g_movies[0].marker=43;
    g_modCount=1; g_mods[0].marker=44; g_mods[0].description=strdup("previous-description");
    g_levelCommon=5; g_listedMaps=6;
    std::strcpy(g_customMapsLua,"previous-maps"); std::strcpy(g_mapsTableLua,"previous-table");
    g_modsLuaDirty.store(false);

    CatalogSnapshot* snapshot=CaptureCatalog();
    assert(snapshot);
    char* const previousDescription=g_mods[0].description;

    g_packageCount=2; g_packages[0].marker=99;
    g_fileCount=3; g_files[0].marker=98;
    g_movieCount=4; g_movies[0].marker=97;
    std::memset(g_mods,0,sizeof(g_mods));
    g_modCount=1; g_mods[0].marker=96; g_mods[0].description=strdup("candidate-description");
    g_levelCommon=95; g_listedMaps=94;
    std::strcpy(g_customMapsLua,"candidate-maps"); std::strcpy(g_mapsTableLua,"candidate-table");
    g_modsLuaDirty.store(true);
    g_scanCandidateActive = true;

    RestoreCatalog(snapshot);
    assert(g_packageCount==1 && g_packages[0].marker==41);
    assert(g_fileCount==1 && g_files[0].marker==42);
    assert(g_movieCount==1 && g_movies[0].marker==43);
    assert(g_modCount==1 && g_mods[0].marker==44);
    assert(g_mods[0].description==previousDescription);
    assert(std::strcmp(g_mods[0].description,"previous-description")==0);
    assert(g_levelCommon==5 && g_listedMaps==6);
    assert(std::strcmp(g_customMapsLua,"previous-maps")==0);
    assert(std::strcmp(g_mapsTableLua,"previous-table")==0);
    assert(!g_modsLuaDirty.load());
    assert(!g_scanCandidateActive);

    // A root-preflight failure occurs before candidate arrays are started.
    snapshot=CaptureCatalog();
    char* const stillPublishedDescription=g_mods[0].description;
    g_scanCandidateActive=false;
    RestoreCatalog(snapshot);
    assert(g_mods[0].description==stillPublishedDescription);
    assert(std::strcmp(g_mods[0].description,"previous-description")==0);

    snapshot=CaptureCatalog();
    assert(snapshot);
    char* const committedOldDescription=g_mods[0].description;
    std::memset(g_mods,0,sizeof(g_mods));
    g_modCount=1; g_mods[0].description=strdup("committed-description");
    g_scanCandidateActive=true;
    CommitCatalog(snapshot);
    assert(!g_scanCandidateActive);
    assert(g_mods[0].description && std::strcmp(g_mods[0].description,"committed-description")==0);
    free(g_mods[0].description);
    g_mods[0].description=nullptr;
    (void)committedOldDescription; // CommitCatalog owns and frees the previous allocation.
    std::puts("PASS: catalog rollback restores all arrays, counters, Lua buffers and mod-description ownership");
}
"""
    with tempfile.TemporaryDirectory(prefix="bo3-map-catalog-transaction-") as temp:
        cpp = Path(temp) / "transaction.cpp"
        binary = Path(temp) / "transaction"
        cpp.write_text(transaction_prefix + transaction + transaction_main)
        subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    refresh = extract_function(SOURCE, "bool T7Maps_Refresh()")
    install = extract_function(SOURCE, "void T7Maps_Install(")
    rollback = extract_function(SOURCE, "static void RestoreCatalog(")
    commit = extract_function(SOURCE, "static void CommitCatalog(")
    scan_all = extract_function(SOURCE, "static bool ScanAll()")
    check_root = extract_function(SOURCE, "static bool CheckDataRoot(")
    uses_root = extract_function(SOURCE, "static bool CatalogUsesDataRoot(")
    custom_maps = SOURCE[SOURCE.index("static bool BuildCustomMapsLua()"):SOURCE.index("static char g_mapsTableLua")]
    initial = extract_function(SOURCE, "static bool ScanAllInitial()")
    scan_mods = extract_function(SOURCE, "static bool ScanMods(")
    add_file = extract_function(SOURCE, "static void AddFile(")
    add_package = extract_function(SOURCE, "static int AddPackage(")

    assert "CaptureCatalog()" in refresh and "RestoreCatalog(previous)" in refresh
    assert "if (!scanned)" in refresh or "if(!scanned)" in refresh
    assert "ScanAllInitial()" in install
    assert "ReleaseCandidateMods();" in initial and "g_packageCount = 0" in initial
    assert "if (g_scanCandidateActive)" in rollback and "ReleaseCandidateMods();" in rollback
    assert "memcpy(g_mods, snapshot->mods" in rollback
    assert "free(snapshot->mods[i].description)" in commit
    assert "memset(g_mods, 0, sizeof(g_mods))" in scan_all
    assert "g_scanCandidateActive = true" in scan_all
    assert "!ScanUsermaps(" in scan_all
    assert "if (!BuildMapsTableLua())" in scan_all
    assert "if (!BuildCustomMapsLua())" in scan_all
    assert "AppendChecked(" in custom_maps and "AppendLuaStringChecked(" in custom_maps
    assert "Mod candidate{}" in scan_mods and "free(mod.description)" not in scan_mods
    assert "FolderScanStatus::CapacityExceeded" in add_file
    assert "FolderScanStatus::CapacityExceeded" in add_package
    assert "kKernelErrorNoEntry" in production
    assert "CatalogUsesDataRoot(root)" in check_root and "PathUsesDataRoot" in uses_root
    assert "CheckDataRoot(dataRoots[i], true" in scan_all
    print("PASS: failed refresh restores catalog arrays, Lua buffers, dirty state and mod-description ownership")


if __name__ == "__main__":
    main()
