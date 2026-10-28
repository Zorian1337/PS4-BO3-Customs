#!/usr/bin/env python3
"""Execute the actual Lua selection/status functions with an isolated UI mock."""
from pathlib import Path
import subprocess
import sys

script = Path(sys.argv[1]).read_text(encoding="utf-8")
prefix = script[:script.index("local function OverlayType(")]
actions = script[script.index("function UI.Choose("):script.index("function UI.Open(")]
fixture = "assert(loadfile([[" + sys.argv[1] + "]]))\n" + '''
local writes = 0
CoD = { LobbyMenus = { AddButtonsForTarget = function() end } }
Engine = { SetDvar = function() writes = writes + 1 end }
BO3CustomsChosenMods = { "personal" }
BO3CustomMods = { {name="bots", title="Bots"}, {name="lobby", title="Lobby"} }
'''+prefix+actions+'''
UI.RefreshChecks = function() end
UI.RefreshStates = function() end
assert(ChosenList()[1] == "personal")
BO3CustomsSessionMods = { "bots", "lobby" }
assert(Position("bots") == 1 and Position("lobby") == 2 and Position("personal") == nil)
assert(string.find(StatusText(), "Host mods selected:", 1, true))
UI.Toggle(nil, 0, "bots")
UI.Choose(nil, 0, "!off")
assert(writes == 0 and BO3CustomsChosenMods[1] == "personal")
BO3CustomsActiveMods = { {name="bots"}, {name="lobby"} }
assert(string.find(StatusText(), "Host mods loaded:", 1, true))
BO3CustomsActiveMods[2].loading = true
assert(string.find(StatusText(), "Host mods selected:", 1, true))
BO3CustomsSessionMods = {}
assert(#ChosenList() == 0 and string.find(StatusText(), "using no mods", 1, true))
BO3CustomsSessionMods = nil
assert(ChosenList()[1] == "personal")
UI.Toggle(nil, 0, "bots")
assert(writes == 1 and BO3CustomsChosenMods[1] == "personal" and BO3CustomsChosenMods[2] == "bots")
print("PASS: host selection/status, loading distinction, empty host, protected personal choices and leave restoration")
'''
subprocess.run([sys.argv[2], "-"], input=fixture, text=True, check=True)
