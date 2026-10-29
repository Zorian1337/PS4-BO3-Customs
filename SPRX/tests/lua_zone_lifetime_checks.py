"""Exercise diagnostic buffer retirement before a native zone unload."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "t7_log.cpp").read_text()
buffer = source[source.index("void T7Log_LuiBuffer("):source.index("void T7Log_LuaFailure(")]
zone = source[source.index("void T7Log_Zone("):source.index("void T7Log_NewLevel(")]
prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <sys/mman.h>
static bool busy=false;
static unsigned probes=0;
static bool T7Maps_UiTransitionBusy() { return busy; }
static bool RangeReadable(uintptr_t p,size_t) { ++probes; return p>4096; }
static void T7Log_Write(const char*,...) {}
namespace T7Log {
constexpr unsigned kNameMax=128, kLuaFilesKept=4;
struct LuaFile { char name[kNameMax]; uintptr_t data; uint32_t length; };
static uintptr_t g_base=1;
static LuaFile g_luaFiles[kLuaFilesKept];
static unsigned g_luaFileCount=0, g_chainAt=3, g_chainShown=2;
static char g_lastLui[kNameMax]="old.lua";
static void Lock() {}
static void Unlock() {}
static void ShowShutdownNotes() {}
}
'''
main = r'''
int main() {
    using namespace T7Log;
    auto memory=(unsigned char*)mmap(nullptr,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    assert(memory!=MAP_FAILED);
    *(int32_t*)(memory+8)=32;
    *(uintptr_t*)(memory+16)=(uintptr_t)(memory+64);
    memcpy(memory+64,"\x1bLua",4);
    T7Log_LuiBuffer("old.lua",(uintptr_t)memory);
    assert(g_luaFileCount==1);
    T7Log_Zone("new_mod",0x40,0x40000000);
    assert(g_luaFileCount==1); // Load-without-free must retain safe entries.
    T7Log_Zone(nullptr,0,0x100);
    assert(g_luaFileCount==0 && !g_lastLui[0] && !g_chainAt && !g_chainShown);
    assert(mprotect(memory,4096,PROT_NONE)==0);
    busy=true;
    const auto before=probes;
    T7Log_LuiBuffer("retired.lua",(uintptr_t)memory);
    assert(probes==before && g_luaFileCount==0); // Never touch a retiring zone.
    munmap(memory,4096);
    puts("PASS: borrowed Lua buffers retire before free and are not recorded during database transitions");
}
'''
with tempfile.TemporaryDirectory(prefix="bo3-lua-zone-") as directory:
    cpp, binary = Path(directory) / "check.cpp", Path(directory) / "check"
    cpp.write_text(prefix + buffer + zone + main)
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
