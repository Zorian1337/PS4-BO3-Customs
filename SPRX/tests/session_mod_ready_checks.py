#!/usr/bin/env python3
"""Exercise real ordered-stack and per-zone readiness before releasing a join."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "t7_maps.cpp").read_text(encoding="utf-8")
start = source.index("bool T7Maps_SessionModsReady()")
ready = source[start:source.index("bool T7Maps_ShareMap(", start)]
start = source.index("static bool StackModReady(")
stack_ready = source[start:source.index("static void SetRefreshOnClose(", start)]
fixture = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <strings.h>
namespace T7Maps {}
constexpr int kModZoneKinds = 4;
struct Mod { char name[56]; bool zones[4]; };
struct Stack { Mod mod; char zones[4][56]; };
static Stack g_stack[2] = {
    {{"bots", {true,true,false,false}}, {"bots_core","bots_zm","",""}},
    {{"lobby",{true,true,false,false}}, {"lobby_core","lobby_zm","",""}}
};
static char g_loaded[2][56] = {"bots", "lobby"};
static char g_sessionMods[2][56] = {"bots", "lobby"};
static uintptr_t g_base = 1;
static int g_sessionModCount = 2, g_loadedCount = 2, g_stackCount = 2;
static int loadedMode = 1, sessionMode = 1;
static bool loading = false;
static int pendingSlot = -1, pendingKind = -1;
static bool AnyZoneLoading() { return loading; }
static int LoadedModeCommon() { return loadedMode; }
static int SessionModeCommon() { return sessionMode; }
static bool EqualsNoCase(const char* a, const char* b) { return strcasecmp(a, b) == 0; }
static int ZoneStateOf(const char* name) {
    for (int i=0; i<2; ++i) for (int k=0; k<4; ++k)
        if (std::strcmp(name, g_stack[i].zones[k]) == 0)
            return i == pendingSlot && k == pendingKind ? 1 : 2;
    return 0;
}
STACK
READY
int main() {
    if (!T7Maps_SessionModsReady()) return 1;
    for (int i=0; i<2; ++i) for (int k=0; k<2; ++k) {
        pendingSlot=i; pendingKind=k;
        if (T7Maps_SessionModsReady()) return 2;
    }
    pendingSlot=pendingKind=-1;
    std::strcpy(g_sessionMods[0], "lobby"); std::strcpy(g_sessionMods[1], "bots");
    if (T7Maps_SessionModsReady()) return 3;
    std::strcpy(g_sessionMods[0], "bots"); std::strcpy(g_sessionMods[1], "lobby");
    loading=true; if (T7Maps_SessionModsReady()) return 4; loading=false;
    loadedMode=2; if (T7Maps_SessionModsReady()) return 5; loadedMode=1;
    g_loadedCount=1; if (T7Maps_SessionModsReady()) return 6; g_loadedCount=2;
    g_stackCount=1; if (T7Maps_SessionModsReady()) return 7; g_stackCount=2;
    std::strcpy(g_stack[1].mod.name, "foreign");
    if (T7Maps_SessionModsReady()) return 8;
    std::strcpy(g_stack[1].mod.name, "lobby");
    if (!T7Maps_SessionModsReady()) return 9;
    g_sessionModCount=0; if (T7Maps_SessionModsReady()) return 10;
    g_loadedCount=0; if (!T7Maps_SessionModsReady()) return 11;
    g_sessionModCount=-1; if (T7Maps_SessionModsReady()) return 12;
    std::puts("PASS: exact host order, core/mode completion, mode identity, no extra/foreign stack and empty host readiness");
}
'''.replace("STACK", stack_ready).replace("READY", ready)
with tempfile.TemporaryDirectory(prefix="bo3-session-ready-") as directory:
    cpp = Path(directory) / "ready.cpp"
    exe = Path(directory) / "ready"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
