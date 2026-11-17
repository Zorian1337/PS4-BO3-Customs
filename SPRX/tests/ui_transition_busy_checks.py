from pathlib import Path

maps = Path("SPRX/t7_maps.cpp").read_text(encoding="utf-8")
lua = Path("SPRX/t7_lua.cpp").read_text(encoding="utf-8")

busy_start = maps.index("bool T7Maps_UiTransitionBusy()")
busy_end = maps.index("\n}", busy_start)
busy = maps[busy_start:busy_end]
assert "g_reloadCheck" in busy
assert "g_reloadCheck && !HeldModZonesReadyForUi()" in busy
assert "g_uiZoneWaitState" in maps
assert "g_uiZoneWaitState.load(std::memory_order_acquire) == kUiZoneWaitPending" in busy
assert "g_uiZoneWaitState.store(kUiZoneWaitPending, std::memory_order_release)" in maps
assert "g_uiZoneWaitState.store(kUiZoneWaitHeldReady, std::memory_order_release)" in maps
assert "g_uiZoneWaitState.store(kUiZoneWaitIdle, std::memory_order_release)" in maps
assert "g_waitZones" not in busy and "g_reloadCheck" not in busy
assert "ready += ZoneStateOf(g_waitZones[i]) >= 2 ? 1 : 0;" in maps
assert "g_frontendApplyPending" in busy and "AnyZoneLoading()" in busy

tick_start = lua.index("void T7Lua_Tick()")
tick_end = lua.index("\nbool T7Lua_MouseReady()", tick_start)
tick = lua[tick_start:tick_end]
assert "if (!g_base || T7Maps_UiTransitionBusy())" in tick
assert "if (T7Maps_UiTransitionBusy())" in tick
assert tick.index("if (T7Maps_UiTransitionBusy())") < tick.index("g_menuInitPending = false")
assert "if (!T7Maps_UiTransitionBusy() && UiUp())" in tick
for helper in ("static void ShowShare()", "static void InjectScripts()", "static void CheckMenus()", "static void AddPcUtil()"):
    start = lua.rindex(helper) if helper == "static void AddPcUtil()" else lua.index(helper)
    end = lua.find("\n}", start)
    assert "if (T7Maps_UiTransitionBusy())" in lua[start:end], helper

trace_start = lua.index("void T7Lua_TraceState(")
trace_end = lua.index("\nbool T7Lua_IsUiState", trace_start)
trace = lua[trace_start:trace_end]
assert "if (T7Maps_UiTransitionBusy())" in trace
assert trace.index("UiUnlock();") < trace.index("TraceStateLocked(reason);")
print("queued UI transition guards passed")
