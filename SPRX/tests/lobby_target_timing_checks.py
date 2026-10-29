"""Execute the production lobby-target shim with the installed Lua 5.1 runner.
Host contract coverage only; HKS/console activation still requires validation.
"""
from pathlib import Path
import ast
import os
import shutil
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "SPRX/t7_lua.cpp").read_text(encoding="utf-8")
block = source.split("static const char k_lobbyTargetLua[] =", 1)[1].split(";", 1)[0]
shim = "".join(ast.literal_eval(value) for value in re.findall(r'"(?:[^"\\]|\\.)*"', block))
hook = source.split("static uint64_t Require_h(", 1)[1].split("static void", 1)[0]
call = hook.index("((Passthrough_t)g_requireOriginal)")
assert hook.index('k_lobbyTargetLua') < call < hook.rindex('k_lobbyTargetLua')
assert 'return result;' in hook
fixture = r'''local apply = assert(loadstring(SHIM))
LobbyData = nil
apply()
LobbyData = false
apply()
LobbyData = { UITargets = {} }
apply()
assert(LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME == nil)
local custom = { id = 310, name = "NativeCustom", maxClients = 18, settings = {} }
LobbyData.UITargets.UI_MPLOBBYONLINECUSTOMGAME = custom
local ok = pcall(function() return LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME.id end)
assert(not ok) -- The DS4C root access fails before the compatibility target exists.
apply()
local target = LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME
assert(target.id == 320 and target.maxClients == 18 and target.settings == custom.settings)
assert(custom.id == 310 and custom.name == "NativeCustom")
for i = 1,1000 do apply(); assert(LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME == target) end
local native = { id = 999, name = "ExistingModTarget" }
LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME = native
apply()
assert(LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME == native)
local replacement = { UI_MPLOBBYONLINECUSTOMGAME = { id = 310, maxClients = 4 } }
LobbyData = { _originalTable = { UITargets = { _originalTable = replacement } } }
apply()
assert(replacement.UI_MPLOBBYONLINEMODGAME.id == 320)
assert(replacement.UI_MPLOBBYONLINEMODGAME.maxClients == 4)
LobbyData = {UITargets = {UI_MPLOBBYONLINEMODGAME = false}}
apply()
assert(LobbyData.UITargets.UI_MPLOBBYONLINEMODGAME == false)
print("PASS: late/replaced/proxy lobby data, existing-target preservation, native settings and repeated refresh")
'''
build = root / 'build'
build.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='lobby-target-', dir=build) as temporary:
    path = Path(temporary) / 'test.lua'
    path.write_text('local SHIM = [====[' + shim + ']====]\n' + fixture, encoding='utf-8')
    runner = os.environ.get('BO3_LUA_RUNNER') or os.environ.get('LUA_RUNNER') or shutil.which('lua5.1') or shutil.which('luajit') or shutil.which('lua')
    if not runner:
        raise SystemExit('Set BO3_LUA_RUNNER to an existing Lua 5.1-compatible executable')
    subprocess.run([runner, str(path)], check=True, timeout=30)
