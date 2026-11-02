"""Keep missing PC child-class fallbacks ahead of their parent constructors."""
import ast
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "SPRX/t7_lua.cpp").read_text(encoding="utf-8")
start = SOURCE.index("static const char k_lobbyParityLua[] =")
lua_lines = []
for line in SOURCE[start:].splitlines()[1:]:
    match = re.match(r'\s*"((?:\\.|[^"\\])*)"\s*$', line)
    if not match:
        break
    lua_lines.append(ast.literal_eval('"' + match.group(1) + '"'))
LUA = "".join(lua_lines)

assert "fe_FooterContainer_NOTLobby = { 'StarterPackWatermark' }" in LUA
fallback_guard = LUA.index("if cod[childClassName] == nil then")
fallback_install = LUA.index("rawset(cod, childClassName, fallback)", fallback_guard)
parent_constructor = LUA.index("return make(unpack(args, 1, argc))", fallback_install)
assert fallback_guard < fallback_install < parent_constructor
assert "local element = lui.UIElement.new()" in LUA[fallback_guard:parent_constructor]
