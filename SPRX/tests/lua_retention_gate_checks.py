from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parent
source=root/'lua_retention_gate_tests.cpp'
build=root.parent/'build'
build.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='lua-gate-',dir=build) as tmp:
    for sanitizer in ('address,undefined','thread'):
        exe=Path(tmp)/('gate-'+sanitizer.replace(',','-'))
        subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-Wall','-Wextra','-Werror','-O1','-pthread',
                        f'-fsanitize={sanitizer}','-I',str(root),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True,timeout=60)
lua=(root/'t7_lua.cpp').read_text()
prepare=lua[lua.index('bool T7Lua_PrepareModUiUnload()'):lua.index('void T7Lua_RunShareVm()',lua.index('bool T7Lua_PrepareModUiUnload()'))]
retain=lua[lua.index('static uint64_t RetainModLua('):lua.index('static const char* const k_graphicsDvars',lua.index('static uint64_t RetainModLua('))]
assert retain.index('LuaRetentionGate::Scope sourceRead') < retain.index('if (!name)')
assert 'return RetainLuaFailure("(unavailable)", 0' in retain
assert 'BeginClose()' in prepare and 'IsDrained()' in prepare and 'Reopen()' in prepare
assert 'kDrainAttempts = 2000' in prepare
maps=(root/'t7_maps.cpp').read_text()
apply=maps[maps.index('static void ApplyModsNow()'):maps.index('static void ApplyModsAtFrontend()',maps.index('static void ApplyModsNow()'))]
assert apply.index('ReloadFrontend(') < apply.index('T7Lua_PrepareModUiUnload()')
assert 'if (!FreeModsFrom(keep))' in apply and 'T7Lua_ResumeModUiRetention();' in apply
assert 'T7Lua_ResumeModUiRetention();' in maps[maps.index('void T7Maps_FrameWork()'):]
print('PASS: gate close/entry race, unreadable-pointer rejection, drain, concurrency and source integration (ASan/UBSan + TSan)')
