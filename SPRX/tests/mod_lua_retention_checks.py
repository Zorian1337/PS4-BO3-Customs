"""Exercise production rawfile retention across unmapping and failed allocation.

This verifies buffer ownership and hook routing, not HKS/game lifecycle behavior.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "t7_lua.cpp").read_text(encoding="utf-8")
retention = source[source.index("struct RawFileAsset"):source.index("static const char* const k_graphicsDvars")]
hook = source[source.index("static uint64_t FindXAsset("):source.index("static void AddPcUtil();")]
guard = source[source.index("bool T7Lua_PrepareModUiUnload()"):source.index("void T7Lua_RunShareVm(")]
fixture = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <thread>
#include <vector>
#include <sys/mman.h>
static uintptr_t denied=0; static size_t deniedSize=0;
static bool failAllocation=false, active=true;
static bool owned=true;
static bool RangeReadable(uintptr_t address,size_t bytes) {
    if(address<4096 || bytes>UINTPTR_MAX-address) return false;
    return !denied || address+bytes<=denied || address>=denied+deniedSize;
}
static std::atomic<unsigned> mappingCalls{0};
static int sceKernelMmap(int,size_t bytes,int,int,int,int,void** output) {
    ++mappingCalls;
    if(failAllocation) return -1;
    *output=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(*output==MAP_FAILED) { *output=nullptr; return -1; }
    return 0;
}
static void sceKernelUsleep(int) { std::this_thread::yield(); }
static void T7Log_Write(const char*,...) {}

#include "t7_lua_failure.hpp"
#include "t7_lua_ownership.hpp"
static T7LuaOwnership::Index ownership;
namespace T7Lua {
#define malloc BO3_RETENTION_MUST_NOT_USE_LIBC_HEAP
''' + retention + r'''
#undef malloc
}
''' + guard + r'''
namespace T7Lua {
using Passthrough_t=uint64_t (*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                               double,double,double,double,double,double,double,double);
static uintptr_t g_base=1; constexpr uintptr_t kExecFindReturn=0;
constexpr int kRawFileType=47;
static RawFileAsset* nativeFile=nullptr;
static uint64_t NativeFind(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                           double,double,double,double,double,double,double,double) {
    return reinterpret_cast<uint64_t>(nativeFile);
}
static void* g_findAssetOriginal=reinterpret_cast<void*>(&NativeFind);
static bool T7Maps_UsingMods() { return active; }
static bool T7Maps_NeedsLuaRetention(const char* name) { return owned && ownership.MayContain(name); }
static void T7Log_LuiFile(const char*) {}
static void T7Log_LuiBuffer(const char*,uintptr_t) {}
static const RawFileAsset* LuiFileFor(const char*) { return nullptr; }
static const RawFileAsset* LuiExtraFor(const char*) { return nullptr; }
static bool LuaMissing(uint64_t raw) { return !raw; }
''' + hook + r'''
}
int main() {
    using namespace T7Lua;
    char* mapped=static_cast<char*>(mmap(nullptr,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0));
    assert(mapped!=MAP_FAILED);
    std::strcpy(mapped,"ui/test.lua");
    std::memcpy(mapped+256,"\x1bLuaQ",5);
    RawFileAsset raw{mapped,64,17,mapped+256};
    nativeFile=&raw;
    ownership.Mark("ui/test.lua");
    const auto find=[&](int type=47){return FindXAsset(type,reinterpret_cast<uint64_t>(mapped),0,0,0,0,0,0,0,0,0,0,0,0);};
    active=false; assert(find()==reinterpret_cast<uint64_t>(&raw));
    active=true; assert(find(1)==reinterpret_cast<uint64_t>(&raw));
    owned=false; assert(find()==reinterpret_cast<uint64_t>(&raw)); owned=true;
    auto saved=reinterpret_cast<const RawFileAsset*>(find());
    assert(saved!=&raw && saved->buffer!=raw.buffer && saved->name!=raw.name);
    assert(saved->length==64 && saved->padding==17 && reinterpret_cast<uintptr_t>(saved->buffer)%16==0);
    const auto bytes=g_retainedLuaBytes.load();
    const auto mappedBytes=g_retainedLuaMapped.load();
    assert(mappedBytes==256u*1024u && mappingCalls==1);
    for(int i=0;i<1000;++i) assert(find()==reinterpret_cast<uint64_t>(saved));
    assert(g_retainedLuaBytes==bytes && g_retainedLuaCount==1);
    assert(g_retainedLuaMapped==mappedBytes && mappingCalls==1);
    assert(T7Lua_PrepareModUiUnload());
    // The original zone's name and bytecode are now genuinely inaccessible.
    denied=reinterpret_cast<uintptr_t>(mapped); deniedSize=4096;
    assert(munmap(mapped,4096)==0);
    assert(std::strcmp(saved->name,"ui/test.lua")==0 && std::memcmp(saved->buffer,"\x1bLuaQ",5)==0);
    denied=0;

    char chunk[64]={}; std::memcpy(chunk,"\x1bLuaQ",5);
    RawFileAsset replacement{"ui/test.lua",64,17,chunk};
    assert(RetainModLua("ui/test.lua",reinterpret_cast<uint64_t>(&replacement))==reinterpret_cast<uint64_t>(saved));
    chunk[20]=42;
    auto changed=reinterpret_cast<const RawFileAsset*>(RetainModLua("ui/test.lua",reinterpret_cast<uint64_t>(&replacement)));
    assert(changed!=saved && changed->buffer[20]==42 && saved->buffer[20]==0);
    assert(g_retainedLuaCount==2); // New bytes at a reused source address remain distinct.
    std::atomic<bool> start{false}; std::vector<std::thread> workers;
    for(int i=0;i<12;++i) workers.emplace_back([&]{
        while(!start.load()) std::this_thread::yield();
        for(int j=0;j<100;++j) RetainModLua("ui/parallel.lua",reinterpret_cast<uint64_t>(&replacement));
    });
    start=true; for(auto& thread:workers) thread.join();
    assert(g_retainedLuaCount==3);
    RawFileAsset text{"ui/source.lua",20,0,"return 'plain source'"};
    assert(RetainModLua(text.name,reinterpret_cast<uint64_t>(&text))==reinterpret_cast<uint64_t>(&text));
    RawFileAsset shortText{"ui/short.lua",2,0,"--"};
    assert(RetainModLua(shortText.name,reinterpret_cast<uint64_t>(&shortText))==reinterpret_cast<uint64_t>(&shortText));
    assert(g_retainedLuaFailures==0);

    failAllocation=true;
    g_retainedLuaBlocks->used=g_retainedLuaBlocks->size; // Force another slab.
    assert(RetainModLua("ui/fail.lua",reinterpret_cast<uint64_t>(&replacement))!=reinterpret_cast<uint64_t>(&replacement));
    assert(T7Lua_PrepareModUiUnload());
    assert(T7Lua_PrepareModUiUnload());
    RawFileAsset core{"ui/LUI/LUI.lua",64,0,chunk};
    nativeFile=&core;
    auto coreResult=FindXAsset(47,reinterpret_cast<uint64_t>(core.name),0,0,0,0,0,0,0,0,0,0,0,0);
    assert(coreResult==reinterpret_cast<uint64_t>(&core)); // Failed mod allocation cannot reject stock recovery UI.
    failAllocation=false;
    auto retry=reinterpret_cast<const RawFileAsset*>(RetainModLua("ui/fail.lua",reinterpret_cast<uint64_t>(&replacement)));
    assert(retry->buffer!=reinterpret_cast<const char*>(kLuaRetentionFailure));
    assert(retry->buffer[20]==42 && T7Lua_PrepareModUiUnload());
    const auto used=g_retainedLuaBytes.load(); g_retainedLuaBytes=kRetainedLuaBudget;
    assert(RetainModLua("ui/budget.lua",reinterpret_cast<uint64_t>(&replacement))!=reinterpret_cast<uint64_t>(&replacement));
    g_retainedLuaBytes=used;
    const auto realMapped=g_retainedLuaMapped.load();
    g_retainedLuaMapped=kRetainedLuaBudget;
    const auto beforeCalls=mappingCalls.load();
    assert(RetainModLua("ui/mapped-budget.lua",reinterpret_cast<uint64_t>(&replacement))!=reinterpret_cast<uint64_t>(&replacement));
    assert(mappingCalls==beforeCalls); // Refuse before making an over-budget map.
    g_retainedLuaMapped=realMapped;
    RawFileAsset oversized{"ui/oversized.lua",INT32_MAX,0,chunk};
    assert(RetainModLua(oversized.name,reinterpret_cast<uint64_t>(&oversized))!=reinterpret_cast<uint64_t>(&oversized));
    g_retainedLua=nullptr;
    while(g_retainedLuaBlocks) {
        auto block=g_retainedLuaBlocks; auto next=block->next;
        const auto size=block->size; assert(munmap(block,size)==0); g_retainedLuaBlocks=next;
    }
    std::puts("PASS: dedicated arena without libc allocations, mapped-byte budget, hook pass-through, source unmap, dedup/version/concurrency and failed chunks rejected without blocking unload");
}
'''
with tempfile.TemporaryDirectory(prefix="bo3-mod-lua-retention-") as directory:
    cpp, binary = Path(directory) / "check.cpp", Path(directory) / "check"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-pthread", "-I", str(root), str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
