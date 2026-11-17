"""Test queued-zone transition gating and post-lock Lua rechecks from production source."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAPS = (ROOT / "t7_maps.cpp").read_text()
LUA = (ROOT / "t7_lua.cpp").read_text()


def extract_block(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise ValueError(f"unterminated block: {marker}")


ZONE_STATE = extract_block(MAPS, "static int ZoneStateOf(")
ANY_LOADING = extract_block(MAPS, "static bool AnyZoneLoading()")
BUSY = extract_block(MAPS, "bool T7Maps_UiTransitionBusy()")

for marker in (
    "static void AddPcUtil()", "static void ShowShare()", "static void InjectScripts()",
    "static void CheckMenus()", "void T7Lua_Tick()"
):
    body = extract_block(LUA, marker)
    lock = body.find("UiTryLock")
    check = body.find("T7Maps_UiTransitionBusy()", lock + 1)
    assert lock >= 0 and check > lock, f"{marker} must recheck transition state after taking the UI lock"

PREFIX = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
namespace T7Maps {
static constexpr uintptr_t kZoneNames=0x1000;
static constexpr int kZoneNameSlots=65;
static constexpr size_t kZoneNameStride=80, kZoneStateAt=72;
static constexpr size_t kNameMax=56;
static uint8_t memory[0x10000];
static uintptr_t T7Maps::g_base=(uintptr_t)memory;
static bool T7Maps::g_frontendApplyPending=false, T7Maps::g_frontendApplying=false, T7Maps::g_frontendApplyLoading=false;
static bool T7Maps::g_reloadCheck=false;
static char g_waitZones[64][kNameMax] = {};
static int g_waitZoneCount=0;
static bool EqualsNoCase(const char* a,const char* b) { return std::strcmp(a,b)==0; }
'''

MAIN = r'''
int main()
{
    std::strcpy(T7Maps::g_waitZones[0],"zm_mod");
    T7Maps::g_waitZoneCount=1;
    auto* entry=(char*)(T7Maps::g_base+T7Maps::kZoneNames+T7Maps::kZoneNameStride);
    std::strcpy(entry,"zm_mod");
    *(int32_t*)(entry+kZoneStateAt)=1;

    // Queued before the engine publishes loading state is already busy.
    g_reloadCheck=true;
    assert(T7Maps_UiTransitionBusy());

    // The held Mods overlay may resume once all its recorded zones are ready.
    *(int32_t*)(entry+kZoneStateAt)=2;
    assert(!T7Maps_UiTransitionBusy());

    // A live native loading slot remains busy even after the queued list clears.
    g_reloadCheck=false;
    *(int32_t*)(entry+kZoneStateAt)=1;
    assert(T7Maps_UiTransitionBusy());

    // Frontend handoff phases continue to block periodic Lua work.
    *(int32_t*)(entry+kZoneStateAt)=2;
    g_frontendApplyPending=true;
    assert(T7Maps_UiTransitionBusy());

    g_frontendApplyPending=false;
    g_frontendApplying=true;
    assert(T7Maps_UiTransitionBusy());

    g_frontendApplying=false;
    g_frontendApplyLoading=true;
    assert(T7Maps_UiTransitionBusy());

    g_frontendApplyLoading=false;
    g_base=0;
    assert(!T7Maps_UiTransitionBusy());
    puts("PASS: queued zones, ready held-overlay path, native loading and frontend handoff gates");
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix="bo3-ui-transition-") as temp:
        temp = Path(temp)
        cpp = temp / "ui_transition.cpp"
        exe = temp / "ui_transition"
        cpp.write_text(PREFIX + ZONE_STATE + "\n" + ANY_LOADING + "\n}\n" + BUSY + "\n" + MAIN)
        subprocess.run([
            "g++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-O1",
            "-fsanitize=address,undefined", str(cpp), "-o", str(exe)
        ], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
