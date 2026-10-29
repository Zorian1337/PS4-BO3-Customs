#!/usr/bin/env python3
"""Check that closing the Mods menu does not reapply an unchanged stack."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
source = (root / "Lua/ui_scripts/mods.lua").read_text(encoding="utf-8")
lua = sys.argv[1]

assert "local function NeedsApply()" in source
assert "if NeedsApply() then" in source
assert "menu closed: no pending mod changes" in source

start = source.index("local function SameNames(")
end = source.index("local function ModLabel(", start)
functions = source[start:end]
fixture = r'''
local UI = { pending = nil }
local chosen, active = {}, {}
local function ChosenList() return chosen end
local function ActiveList() return active end
local function NameOf(item)
  if type(item) == "table" then return item.name end
  return item
end
local function Same(a, b) return a == b end
'''+functions+r'''
chosen, active = {}, {}
assert(NeedsApply() == false)
chosen = { "reaper_collection" }
assert(NeedsApply() == true)
active = { { name = "reaper_collection" } }
assert(NeedsApply() == false)
UI.pending = { request = "!off" }
assert(NeedsApply() == true)
print("PASS: unchanged menu closes do not reapply; pending and changed stacks remain eligible")
'''
subprocess.run([lua, "-"], input=fixture, text=True, cwd=root, check=True)
