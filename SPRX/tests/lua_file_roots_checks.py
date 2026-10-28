#!/usr/bin/env python3
"""Fault-inject the production companion-file reader; this is not a PS4 emulator."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
fixture = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
constexpr int SCE_KERNEL_O_RDONLY=0;
struct Handle { std::string path; size_t at; };
static std::map<std::string,std::string> files;
static std::map<int,Handle> handles;
static std::string badRead,badClose,badSeek,growing;
static int opens=0;
static int sceKernelOpen(const char* path,int flags,int) {
    assert(flags==SCE_KERNEL_O_RDONLY); ++opens;
    if(!files.count(path)) return -1;
    int fd=handles.empty()?1:handles.rbegin()->first+1;
    handles[fd]={path,0}; return fd;
}
static int64_t sceKernelLseek(int fd,int64_t offset,int mode) {
    auto& h=handles.at(fd);
    if(h.path==badSeek) return -1;
    h.at=mode==SEEK_END?files[h.path].size():size_t(offset);
    if(mode==SEEK_END && h.path==growing) --h.at;
    return h.at;
}
static int64_t sceKernelRead(int fd,void* data,size_t size) {
    auto& h=handles.at(fd);
    if(h.path==badRead && h.at>=3) return -1;
    size_t n=std::min({size,size_t(3),files[h.path].size()-h.at});
    memcpy(data,files[h.path].data()+h.at,n); h.at+=n; return n;
}
static int sceKernelClose(int fd) {
    bool fail=handles.at(fd).path==badClose;
    handles.erase(fd); return fail?-1:0;
}
static void sceKernelUsleep(int) {}
void T7Log_Write(const char*,...) {}
#include "t7_lua_files.hpp"
static const char* internal="/data/BO3-Customs/ui_scripts/test.lua";
static const char* external="/usb3/Custom Lua/ui_scripts/test.lua";
static void Reset() {
    files.clear(); handles.clear(); badRead.clear(); badClose.clear(); badSeek.clear(); growing.clear();
    T7LuaFiles::g_ready=false; T7LuaFiles::g_loading=false; T7LuaFiles::g_rootCount=0; opens=0;
}
static void Expect(const char* expected,size_t maximum=64) {
    size_t length=99;
    char* body=T7LuaFiles::Read("ui_scripts/test.lua",maximum,&length);
    if(expected) assert(body && std::string(body,length)==expected && body[length]==0);
    else assert(!body && length==0);
    free(body); assert(handles.empty());
}
int main() {
    Reset(); files[internal]="internal"; files["/usb7/BO3-Customs/ui_scripts/test.lua"]="usb7";
    Expect("internal"); files.erase(internal); Expect("usb7");
    Reset(); files["/data/BO3-Customs/lua_roots.txt"]=" # comment\r\n /usb3/Custom Lua/ \r\n/usb3/Custom Lua\n/usb0/../system\nrelative\n";
    files[external]="external"; files[internal]="internal";
    Expect("external"); assert(T7LuaFiles::g_rootCount==1);
    for(int fault=0;fault<6;++fault) {
        badRead.clear(); badClose.clear(); badSeek.clear(); growing.clear(); files[external]="external";
        if(fault==0) files.erase(external); // Removed/unplugged drive.
        if(fault==1) badRead=external;
        if(fault==2) badClose=external;
        if(fault==3) badSeek=external;
        if(fault==4) growing=external;
        if(fault==5) files[external]=std::string(65,'x');
        Expect("internal");
    }
    badRead.clear(); badClose.clear(); badSeek.clear(); growing.clear(); files[external]=""; Expect("internal");
    files[external]=std::string("a\0b",3); Expect("internal");
    size_t length=0; char* binary=T7LuaFiles::Read("ui_scripts/test.lua",64,&length,false);
    assert(binary && length==3 && binary[1]==0); free(binary);
    int before=opens;
    assert(!T7LuaFiles::Read("../outside",64)); assert(!T7LuaFiles::Read("/absolute",64));
    assert(!T7LuaFiles::Read("lui/a/../../outside",64)); assert(opens==before);
    Reset(); files["/data/BO3-Customs/lua_roots.txt"]=std::string(4097,'x'); files[internal]="internal";
    Expect("internal"); assert(T7LuaFiles::g_rootCount==0);
    Reset(); Expect(nullptr);
    std::puts("PASS: internal priority, configured/default external roots, complete reads, unplug/read/close/size fallback, binary data and path bounds");
}
'''
with tempfile.TemporaryDirectory(prefix="bo3-lua-roots-") as directory:
    source = Path(directory) / "fixture.cpp"
    binary = Path(directory) / "fixture"
    source.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-pthread", "-I", str(root), str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)
