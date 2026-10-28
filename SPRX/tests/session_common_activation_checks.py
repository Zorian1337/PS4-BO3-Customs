#!/usr/bin/env python3
"""Execute production ApplyModsNow against isolated loader/session fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "t7_maps.cpp").read_text()
start = source.index("static void ApplyModsNow()")
body = source[start:source.index("#ifdef _DEBUG", start)]
fixture = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <strings.h>
constexpr int kMaxStack=4, kNameMax=56, kModeCommonFlags=0x40;
struct ZoneInfo { const char* name; int allocFlags; int freeFlags; };
static bool g_loadOriginal=true, g_inLevel=false, loading=false, hooks=true, onTop=true;
static bool g_reloadCheck=false, g_reloadForced=false;
static std::atomic<bool> g_applyWanted{false};
static int g_loadedCount=0, wanted=2, mode=1, g_sessionModCount=2;
static int keepAssets=0, reloads=0, appends=0, frees=0, syncs=0, clears=0, frontend=0;
static char g_loaded[4][56] = {};
static const char* const k_modeCommons[]={"","zm_common","mp_common","cp_common"};
static uintptr_t g_base=(uintptr_t)&keepAssets;
constexpr int kKeepAssetUse=0;
static void RenderSync() { ++syncs; }
static uintptr_t kRenderSync=(uintptr_t)&RenderSync-g_base;
static bool ModHooksReady() { return hooks; }
static bool AnyZoneLoading() { return loading; }
static int ChosenForLoad(char names[][56]) {
    if (wanted>0) std::strcpy(names[0],"bots");
    if (wanted>1) std::strcpy(names[1],"lobby");
    return wanted;
}
static bool EqualsNoCase(const char* a,const char* b) { return strcasecmp(a,b)==0; }
static int LoadedModeCommon() { return mode; }
static void LoadModeCommonForMods() { ++reloads; }
static bool ModeCommonOnTop() { return onTop; }
static void T7Log_Write(const char*,...) {}
static void ClearAssetsInUse() { ++clears; }
template<class... Args> static void LoadXAssets_h(uint64_t pointer,Args...) {
    auto common=(const ZoneInfo*)pointer;
    assert(std::strcmp(common->name,"zm_common")==0);
    assert(common->allocFlags==kModeCommonFlags && common->freeFlags==kModeCommonFlags);
    ++reloads;
}
static bool IsUiMod(const char*) { return true; }
static bool IsUnshown(const char*) { return false; }
static bool FreeModsFrom(int) { ++frees; return true; }
static void PruneWaitZones() {}
static void RemoveClaimsFrom(int) {}
static void BeginListWrite() {}
static void EndListWrite() {}
static void SetStack(const char (*)[56],int) {}
static void SetLoaded(int n) { g_loadedCount=n; }
static void AppendMods(const char (*)[56],int,int) { ++appends; }
static void ReloadFrontend(const char*) { ++frontend; }
FUNCTION
int main() {
    ApplyModsNow(); // Fresh host stack: whole common transaction, no partial append/restart.
    assert(reloads==1 && appends==0 && frees==0 && syncs==1 && clears==1 && frontend==0);
    loading=true; ApplyModsNow(); assert(reloads==1 && g_applyWanted.load()); loading=false;
    onTop=false; ApplyModsNow(); assert(reloads==1); onTop=true;
    g_inLevel=true; ApplyModsNow(); assert(reloads==1); g_inLevel=false;
    g_loadedCount=2; std::strcpy(g_loaded[0],"bots"); std::strcpy(g_loaded[1],"lobby");
    ApplyModsNow(); assert(reloads==1); // Already manually enabled: untouched.
    std::strcpy(g_loaded[0],"lobby"); std::strcpy(g_loaded[1],"bots");
    ApplyModsNow(); assert(reloads==2 && appends==0); // Wrong order also needs whole reload.
    wanted=0; ApplyModsNow(); assert(reloads==3); // Empty host removes local extras.
    g_loadedCount=0; wanted=2; g_sessionModCount=-1;
    ApplyModsNow(); assert(reloads==3 && appends==1); // Personal menu path preserved.
    g_sessionModCount=2; mode=-1; ApplyModsNow(); assert(reloads==4); // No common loaded yet.
    assert(frontend==0);
    std::puts("PASS: host common transaction, exact-order no-op, empty host, zone/memory guards and personal activation");
}
'''.replace("FUNCTION", body)
with tempfile.TemporaryDirectory(prefix="bo3-common-activation-") as directory:
    cpp = Path(directory) / "activation.cpp"
    exe = Path(directory) / "activation"
    cpp.write_text(fixture)
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
