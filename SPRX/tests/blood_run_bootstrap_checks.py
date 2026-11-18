"""Exercise the production missing Mods_IsUsingUsermap bootstrap and provider preservation."""
from pathlib import Path
import ast
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[2]).read_text() if len(sys.argv) > 2 else (root / "SPRX/t7_lua.cpp").read_text()
block = source.split("static const char k_globalAliasLua[] =", 1)[1].split(";", 1)[0]
chunk = "".join(ast.literal_eval(value) for value in re.findall(r'"(?:[^"\\]|\\.)*"', block))
assert "Mods_IsUsingUsermap" in chunk
assert "function() return level() ~= nil end" in chunk

fixture = r\'''
local function install(map, fail)
  local env=setmetatable({}, {__index=_G})
  env._G=env
  env.Engine={GetCurrentMap=function()
    if fail then error("map probe unavailable") end
    return map
  end}
  local bootstrap=assert(loadstring(CHUNK))
  setfenv(bootstrap,env)
  bootstrap()
  return env
end

local map=install("zm_blood_run",false)
assert(type(map.Mods_IsUsingUsermap)=="function")
assert(map.Mods_IsUsingUsermap()==true)
assert(map.Mods_UsingUsermapUgcName()=="zm_blood_run")
assert(map.Mods_IsUsingMods()==true)

local frontend=install("core_frontend",false)
assert(frontend.Mods_IsUsingUsermap()==false)
assert(frontend.Mods_UsingUsermapUgcName()=="")
assert(frontend.Mods_IsUsingMods()==false)

local absent=install(nil,false)
assert(absent.Mods_IsUsingUsermap()==false)
assert(absent.Mods_UsingUsermapUgcName()=="")
local failed=install(nil,true)
assert(failed.Mods_IsUsingUsermap()==false)
assert(failed.Mods_UsingUsermapUgcName()=="")

local provider=function() return "provider-owned" end
local preserved=setmetatable({}, {__index=_G})
preserved._G=preserved
preserved.Engine={GetCurrentMap=function() return "zm_blood_run" end}
preserved.Mods_IsUsingUsermap=provider
local bootstrap=assert(loadstring(CHUNK))
setfenv(bootstrap,preserved)
bootstrap()
assert(preserved.Mods_IsUsingUsermap==provider)
assert(preserved.Mods_IsUsingUsermap()=="provider-owned")

local chosen=install("core_frontend",false)
chosen.BO3CustomsChosenMod="selected_mod"
-- A selected mod does not turn a frontend into a usermap.
assert(chosen.Mods_IsUsingMods()==true)
assert(chosen.Mods_IsUsingUsermap()==false)
print("PASS: Blood Run usermap fallback detects maps, rejects frontend/errors, and preserves existing providers")
\'''

subprocess.run([sys.argv[1], "-"], input="local CHUNK=[====[" + chunk + "]====]\n" + fixture,
               text=True, cwd=root, check=True)
