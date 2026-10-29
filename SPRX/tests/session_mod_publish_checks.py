#!/usr/bin/env python3
"""Verify the real session setter invalidates Lua state on join and leave."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "t7_maps.cpp").read_text(encoding="utf-8")

# Native selection must not resolve an overlong requested folder name by
# truncating it into a different installed mod's valid prefix.
selection = source[source.index("int T7Maps_SelectMod("):source.index("const char* T7Maps_ModsLua()", source.index("int T7Maps_SelectMod("))]
assert "if (length >= kNameMax)" in selection
assert selection.index("if (length >= kNameMax)") < selection.index("FindMod(name)")
assert "at = *end ? end + 1 : end;" in selection

# Applying a stack during gameplay must not consume the request before a safe
# frontend frame can process it. Keep the guard ahead of the atomic exchange.
frame = source[source.index("void T7Maps_FrameWork()"):source.index("int T7Maps_MapCount()") if source.index("int T7Maps_MapCount()") > source.index("void T7Maps_FrameWork()") else len(source)]
apply_guard = frame[frame.index("if (g_applyWanted.load("):frame.index("ApplyModsNow();")]
assert "!g_inLevel" in apply_guard and "g_loadOriginal" in apply_guard
assert "ModHooksReady()" in apply_guard and "g_applyWanted.exchange(false" in apply_guard
assert apply_guard.index("!g_inLevel") < apply_guard.index("g_applyWanted.exchange(false")

start = source.index("void T7Maps_SetSessionMods(")
setter = source[start:source.index("bool T7Maps_SessionModsReady(", start)]
fixture = r'''
#include <atomic>
#include <cstdio>
#include <cstring>
namespace T7Maps {}
constexpr int kNameMax = 56, kT7ShareName = 56, kMaxStack = 24;
static int g_sessionModCount = -1, g_chosenCount = 1;
static char g_sessionMods[kMaxStack][kNameMax];
static std::atomic<bool> g_modsLuaDirty{false};
static void T7Log_Write(const char*, ...) {}
PRODUCTION
int main() {
    const char names[2][56] = {"bots", "lobby"};
    T7Maps_SetSessionMods(names, 2);
    if (!g_modsLuaDirty || g_sessionModCount != 2 ||
        std::strcmp(g_sessionMods[0], "bots") || std::strcmp(g_sessionMods[1], "lobby")) return 1;
    g_modsLuaDirty.store(false);
    T7Maps_SetSessionMods(nullptr, -1);
    if (!g_modsLuaDirty || g_sessionModCount != -1) return 2;
    g_modsLuaDirty.store(false);
    T7Maps_SetSessionMods(names, 0);
    if (!g_modsLuaDirty || g_sessionModCount != 0) return 3;
    std::puts("PASS: session join, leave and empty host invalidate Lua state and preserve host order");
}
'''.replace("PRODUCTION", setter)
with tempfile.TemporaryDirectory(prefix="bo3-session-publish-") as directory:
    cpp = Path(directory) / "publish.cpp"
    exe = Path(directory) / "publish"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
