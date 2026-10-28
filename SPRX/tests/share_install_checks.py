#!/usr/bin/env python3
"""Run the production share installer against incomplete/complete manifests."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "t7_share.cpp").read_text(encoding="utf-8")
start = source.index("static bool InstallHoldsLaunch()")
finish = source[start:source.index("static void KeepJoinAlive(", start)]
fixture = r'''
#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <cstring>
struct Session {
    bool active = true;
    bool fetched = false, needMap = false, listed = true;
    bool installed = false;
    uint64_t activationAt = 0, activationRetryAt = 0;
    char map[56] = "map";
    int modCount = 2;
    char mods[2][56] = {"bots", "lobby"};
};
static Session g_session;
namespace T7Share {}
static bool g_ready = true;
static std::atomic<bool> g_busy{false}, g_stop{false};
static std::atomic<bool> g_mapsChanged{false};
static bool g_overriding = false;
enum { kInstalling, kReady, kFailed, kIdle };
static std::atomic<int> g_phase{kInstalling};
static bool refreshReady = true, mapPresent = true;
static bool zonesReady = true;
static uint64_t now = 100;
constexpr uint64_t kModActivationWaitUs = 90000000, kModActivationRetryUs = 1000000;
static int refreshes = 0, applies = 0, selections = 0;
static uint64_t sceKernelGetProcessTime() { return now; }
static bool T7Maps_SessionModsReady() { return zonesReady; }
static void T7Maps_RequestApply() { ++applies; }
static int installed = 2, selected = -1;
static char order[128] = {};
static bool T7Maps_Refresh() { ++refreshes; return refreshReady; }
static bool T7Maps_HasMap(const char*) { return mapPresent; }
static bool T7Maps_HasMod(const char* name) {
    return installed == 2 || (installed == 1 && std::strcmp(name, "bots") == 0);
}
static void T7Maps_SetSessionMods(const char (*names)[56], int count) {
    ++selections;
    selected = count;
    if (count == 2) std::snprintf(order, sizeof(order), "%s,%s", names[0], names[1]);
}
static void Fail(const char*, ...) { g_phase.store(kFailed); }
static void Notify(const char*, ...) {}
static void T7Log_Write(const char*, ...) {}
PRODUCTION
CANCEL
static void Reset() {
    g_session = Session{};
    g_phase.store(kInstalling); g_mapsChanged.store(false); g_overriding = false;
    refreshReady = mapPresent = true; installed = 2; selected = -1; order[0] = 0;
    zonesReady = true; now = 100; refreshes = applies = selections = 0;
    g_busy.store(false); g_stop.store(false);
}
int main() {
    Reset(); installed = 1; Finish();
    if (g_phase != kFailed || selected != -1 || g_overriding) return 1;
    if (!InstallHoldsLaunch()) return 17;
    T7Share_Cancel();
    if (InstallHoldsLaunch()) return 18;
    Reset(); Finish();
    if (g_phase != kReady || selected != 2 || !g_overriding || std::strcmp(order, "bots,lobby")) return 2;
    Reset(); g_session.fetched = true; refreshReady = false; Finish();
    if (g_phase != kInstalling || selected != -1 || g_overriding) return 3;
    Reset(); g_session.needMap = true; mapPresent = false; Finish();
    if (g_phase != kFailed || selected != -1) return 4;
    Reset(); g_session.modCount = 0; Finish();
    if (g_phase != kReady || selected != 0 || !g_overriding) return 5;
    Reset(); g_session.fetched = true; Finish();
    if (g_phase != kReady || selected != 2 || !g_mapsChanged) return 6;
    Reset(); g_session.fetched = true; zonesReady = false; Finish();
    if (g_phase != kInstalling || applies != 1 || !g_session.installed) return 7;
    if (!InstallHoldsLaunch()) return 12;
    Finish();
    if (g_phase != kInstalling || selections != 1 || refreshes != 1 || applies != 1) return 8;
    now += kModActivationRetryUs; Finish();
    if (applies != 2) return 9;
    zonesReady = true; Finish();
    if (g_phase != kReady || selections != 1 || refreshes != 1) return 10;
    if (InstallHoldsLaunch()) return 13;
    Reset(); zonesReady = false; Finish();
    now += kModActivationWaitUs; Finish();
    if (g_phase != kFailed) return 11;
    if (!InstallHoldsLaunch()) return 14;
    T7Share_Cancel();
    if (!g_stop || InstallHoldsLaunch()) return 15;
    Reset(); g_session.active = false; T7Share_Cancel();
    if (g_stop) return 16;
    std::puts("PASS: partial stacks rejected; ordered existing/downloaded stacks wait for activation; single discovery; bounded retry/timeout");
}
'''.replace("PRODUCTION", finish).replace("CANCEL", source[source.index("void T7Share_Cancel()"):source.index("bool T7Share_TakeMapsChanged()")])
with tempfile.TemporaryDirectory(prefix="bo3-share-install-") as directory:
    cpp = Path(directory) / "install.cpp"
    exe = Path(directory) / "install"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
