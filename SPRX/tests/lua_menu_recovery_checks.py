#!/usr/bin/env python3
"""Run the production recovery callbacks under Lua 5.1; no BO3 runtime emulation."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
mods = (root / "Lua/ui_scripts/mods.lua").read_text(encoding="utf-8")
maps = (root / "Lua/ui_scripts/mapselect.lua").read_text(encoding="utf-8")
lua = sys.argv[1]

def section(source, start, end):
    return source[source.index(start):source.index(end, source.index(start))]

mod_fixture = r'''
assert(loadfile("Lua/ui_scripts/mods.lua"))
local writes,delegated=0,0
local UI={}
local engine={SetDvar=function(name,value) assert(name=="bo3customs_mod" and type(value)=="string"); writes=writes+1 end}
local function IsElement(value) return type(value)=="table" or type(value)=="userdata" end
local function Controller(value) return value or 0 end
local function Log() end
local function StatusText() return "host owns selection" end
local function ChosenList() return BO3CustomsChosenMods end
local function Same(a,b) return string.lower(a)==string.lower(b) end
local function ModelText(element,key) return element[key] end
local recoveryPopups=0
local function ShowChoice(menu,controller,title,message,choices,kind)
 assert(menu==UI.menu and controller==0 and title=="MODS" and message=="unsupported")
 assert(kind=="Error" and #choices==1 and choices[1].label=="OK")
 recoveryPopups=recoveryPopups+1
 return true
end
UI.SetStatus=function() end
UI.SetChosen=function(list) BO3CustomsChosenMods=list end
UI.RefreshChecks=function() end
UI.RefreshStates=function() end
Mods_Unload=function(...) delegated=delegated+1; return "original",select("#",...) end
Mods_LoadMod=function(...) delegated=delegated+1; return "original load",select("#",...) end
'''
mod_fixture += section(mods, "function UI.Choose(", "function UI.SetChosen(")
mod_fixture += section(mods, "function UI.Toggle(", "function UI.Unload(")
mod_fixture += section(mods, "function UI.Unload(", "function UI.Open(")
mod_fixture += section(mods, "function UI.Applied(", "local ownedActions = {}")
mod_fixture += section(mods, "local ownedActions = {}", "-- Keep the MODS entry available")
mod_fixture += section(mods, 'Define("Mods_LoadMod"', 'Define("Mods_RefreshListMods"')
mod_fixture += section(mods, "for name, action in pairs(ownedActions) do", '\nRefreshLobby()\nLog("installed")')
mod_fixture += r'''
local menu={}
UI.menu=menu
BO3CustomsChosenMods={}
-- Invalid catalog values must never reach the native comma-separated selector.
UI.Toggle(menu,0,nil)
UI.Toggle(menu,0,{name="bad"})
UI.Toggle(menu,0,"")
UI.Toggle(menu,0,"mod,other")
UI.Toggle(menu,0,string.rep("x",56))
assert(writes==0 and #BO3CustomsChosenMods==0)
local full={}
for i=1,24 do full[i]="mod"..i end
BO3CustomsChosenMods=full
UI.Toggle(menu,0,"mod25")
assert(writes==1 and #BO3CustomsChosenMods==25)
UI.Toggle(menu,0,"mod24")
assert(writes==2 and #BO3CustomsChosenMods==24)
-- Reset the fixture before testing the normal load/unload path.
BO3CustomsChosenMods={}
writes=0
Mods_LoadMod(menu,{folder="ds4c"},0)
assert(writes==1 and BO3CustomsChosenMods[1]=="ds4c" and delegated==0)
Mods_Unload(menu,nil,0)
assert(writes==2 and #BO3CustomsChosenMods==0 and delegated==0)
BO3CustomsChosenMods={"personal"}; BO3CustomsSessionMods={"host"}
Mods_Unload(menu,nil,0)
assert(writes==2 and BO3CustomsChosenMods[1]=="personal")
BO3CustomsSessionMods=nil
local a,b=Mods_Unload({},nil,0,"param",{})
assert(a=="original" and b==5 and delegated==1 and writes==2)
assert(Mods_LoadMod({},nil,0)=="original load" and delegated==2)
-- Widget refresh errors must not prevent the native deselection request.
UI.SetChosen=function() error("broken mod widget") end
assert(not pcall(Mods_Unload,menu,nil,0))
assert(writes==3)
BO3CustomsChosenMods={"ds4c"}
assert(not pcall(UI.Toggle,menu,0,"ds4c"))
assert(writes==4)
-- A failed native request must not make the UI claim a different selection.
UI.SetChosen=function(list) BO3CustomsChosenMods=list end
UI.SetStatus=function(message) assert(type(message)=="string") end
engine.SetDvar=function() error("native dvar unavailable") end
BO3CustomsChosenMods={"ds4c"}
UI.Unload(menu,0)
assert(#BO3CustomsChosenMods==1 and BO3CustomsChosenMods[1]=="ds4c" and UI.pending==nil)
UI.Toggle(menu,0,"ds4c")
assert(#BO3CustomsChosenMods==1 and BO3CustomsChosenMods[1]=="ds4c" and UI.pending==nil)
-- A native rejection must roll back the optimistic choice; stale replies
-- must not undo a more recent request.
engine.SetDvar=function(name,value) writes=writes+1 end
UI.SetChosen=function(list) BO3CustomsChosenMods=list end
UI.Choose(menu,0,"!off")
UI.SetChosen({})
UI.Applied("!off",-1,"unsupported")
assert(BO3CustomsChosenMods[1]=="ds4c" and UI.pending==nil and recoveryPopups==1)
UI.Choose(menu,0,"ds4c")
UI.Choose(menu,0,"!off")
UI.Applied("ds4c",-1,"stale")
assert(UI.pending ~= nil and UI.pending.request=="!off")
UI.Applied("!off",0,"off")
assert(UI.pending==nil)
print("PASS: unload routes only owned menus, delegates other contexts, protects host choices and preserves selection on native request failure")
'''
subprocess.run([lua, "-"], input=mod_fixture, text=True, cwd=root, check=True)

# Verify main-menu-only insertion without relying on any game-mode buttons
# or the availability of the mod catalog.
button_fixture = r'''
local ButtonId="btnModsLoad"
local UI={logged={}}
local cod={LobbyMenus={History={}}}
local function LogOnce() end
LobbyData={UITargets={UI_MODESELECT={id=1},UI_CPLOBBY={id=2}},GetLobbyNav=function() return 1 end}
'''
button_fixture += section(mods, "local function IsMainMenuTarget(", "local function HideOnline(")
button_fixture += r'''
assert(IsMainMenuTarget(1))
assert(not IsMainMenuTarget(2))
assert(not IsMainMenuTarget(999))
local main={}
AddModsButton(0,1,main)
assert(#main==1 and main[1].customId==ButtonId and main[1].disabled==false)
AddModsButton(0,1,main)
assert(#main==1)
local secondary={}
AddModsButton(0,2,secondary)
assert(#secondary==0)
local empty={}
AddModsButton(0,999,empty)
assert(#empty==0)
LobbyData.UITargets.UI_MODESELECT=nil
assert(IsMainMenuTarget(1), "PS5 main menu target 1 must remain supported without UI_MODESELECT")
assert(not IsMainMenuTarget(410), "secondary lobby target must not receive MODS")
local ps5main={}
AddModsButton(0,1,ps5main)
assert(#ps5main==1 and ps5main[1].customId==ButtonId)
local ps5secondary={}
AddModsButton(0,410,ps5secondary)
assert(#ps5secondary==0)
print("PASS: MODS is independent of catalog and mode buttons, unique on main menu, absent elsewhere")
'''
subprocess.run([lua, "-"], input=button_fixture, text=True, cwd=root, check=True)


map_fixture = r'''
assert(loadfile("Lua/ui_scripts/mapselect.lua"))
local Tabs={lists={}}
local choosing,owned=false,false
local function Choosing() return choosing end
local function Zombies() return 0 end
local function ExternalZMOwner() return owned end
local function LogOnce() end
local function EnsureCustomEntries() end
-- PrepareZMMaps calls the catalog normalizer in production; this fixture is
-- testing ownership/table preservation and intentionally supplies no catalog.
local function NormalizeCatalogEntries() end
local PrepareCategories,PrepareMaps=function(p,c,l) return p(c,l) end,function(p,c,l) return p(c,l) end
CoD={mapsTable={
  zm_good={session_mode=0,dlc_pack=0,unique_id=1,mapName="Good"},
  zm_custom={session_mode=0,dlc_pack=0,unique_id=2,mapName="Custom",previewImage={invalid=true}},
  zm_locked={session_mode=0,dlc_pack=1,unique_id=3},
  zm_hidden={session_mode=0,dlc_pack=-1,unique_id=4},
  mp_other={session_mode=1,dlc_pack=0,unique_id=5},
}}
Engine={IsMapValid=function(id) return id=="zm_good" or id=="zm_custom" end,Localize=function(s) return s end}
local prepared=0
ListHelper_Prepare=function(list,controller,name,prepare)
  prepared=prepared+1; list.rows=prepare(controller,list); return "native helper"
end
'''
map_fixture += section(maps, "local function RemoveInjectedEntries(", "local function BuildWith(")
map_fixture += section(maps, "local function BuildWith(", "local function WrapMapsList(")
map_fixture += section(maps, "local function PrepareZMMaps(", "local function Install()")
map_fixture += section(maps, "local function RemoveOwnedTabs(", "local function RefreshMultiplayer(")
map_fixture += r'''
assert(WrapListPrepare())
local list={}
local full=CoD.mapsTable
local ok=pcall(BuildWith,{},function() error("missing dependency") end)
assert(not ok and CoD.mapsTable==full)
local result=ListHelper_Prepare(list,0,"ZMMapsList",function() error("function expected instead of nil") end)
assert(result=="native helper" and #list.rows==2 and CoD.mapsTable==full, "recovery rows mismatch")
assert(list.rows[1].properties.mapId=="zm_good" and list.rows[2].properties.mapId=="zm_custom")
assert(list.rows[2].models.Image=="playlist_standard" and not list.rows[2].properties.purchasable)
owned=true
local ownedTable=CoD.mapsTable
local injected={bo3_custom=true}
CoD.mapsTable.injected=injected
Tabs.injectedMaps={injected=injected}
RemoveInjectedEntries()
assert(CoD.mapsTable.injected==nil, "owned menu retained a BO3-Customs-injected row")
ListHelper_Prepare(list,0,"ZMMapsList",function()
  local count=0
  for id in pairs(CoD.mapsTable) do if id=="zm_custom" then count=count+1 end end
  return {customCount=count}
end)
assert(list.rows.customCount==1 and CoD.mapsTable==ownedTable and CoD.mapsTable==full,
  "owned map table was replaced or lost its custom entry")
owned=false
local healthy={{models={custom="keep"}}}
ListHelper_Prepare(list,0,"ZMMapsList",function() return healthy end)
assert(list.rows==healthy)
choosing=true
assert(not pcall(ListHelper_Prepare,list,0,"ZMMapsList",function() error("playlist failure") end))
choosing=false
assert(not pcall(ListHelper_Prepare,list,0,"ChangeMapMaps",function() error("MP failure") end))
-- A Reaper-owned menu must remain the only selector after a refresh. If
-- BO3-Customs created its bar before ownership was observed, remove only our
-- bar and leave the owner's map list intact.
local added,removed,updated=0,0,0
AddTabs=function() added=added+1 end
local ownedMenu={
  BO3TabBar={close=function() removed=removed+1 end},
  MapList={updateDataSource=function() updated=updated+1 end},
}
owned=true
RefreshZombies(ownedMenu,0)
assert(added==0 and removed==1 and updated==1 and ownedMenu.BO3TabBar==nil,
  "owned menu refresh must suppress duplicate BO3-Customs tabs")
owned=false
local stockMenu={MapList={}}
RefreshZombies(stockMenu,0)
assert(added==1, "stock menu refresh must retain BO3-Customs tabs")
print("PASS: failed ZM list recovery retains valid stock/custom map IDs, excludes locked/hidden/MP maps, preserves successful builders and restores map tables")
'''
subprocess.run([lua, "-"], input=map_fixture, text=True, cwd=root, check=True)

# Exercise details scrolling with incomplete console UI event metadata.
scroll_fixture = r'''
local Details={deadzone=0.25,stickSpeed=260,resume=3000,hold=3000,speed=24}
local scrolls=0
local function StickY() return 1 end
local function Now() return 100 end
local function ScrollAt(state) return state.offset end
local function ScrollMove(state,offset)
  assert(type(offset)=="number" and offset==offset and offset>=0 and offset<=state.distance)
  scrolls=scrolls+1
  state.offset=offset
end
local function ScrollAnimate() error("unexpected animation") end
'''
scroll_fixture += section(mods, "local function ScrollStick(", "local function ScrollReset(")
scroll_fixture += r'''
local state={distance=100,offset=50,generation=0}
for _, event in ipairs({{}, {timeElapsed="garbage"}, {timeElapsed=0}, {timeElapsed=0/0}, {timeElapsed=500}, {timeElapsed="16"}}) do
  ScrollStick(state,event)
end
ScrollStick(state,nil)
assert(scrolls==7 and state.offset>=0 and state.offset<=100)
print("PASS: MODS details scrolling survives missing and malformed UI elapsed time")
'''
subprocess.run([lua, "-"], input=scroll_fixture, text=True, cwd=root, check=True)

color_fixture = r'''
local function CheckColor()
'''
color_fixture += section(mods, "local function CheckColor()", "local function AddCheckbox(").split("local function CheckColor()\n", 1)[1]
color_fixture += r'''
ColorSet={Orange={r=0.5}}
local r,g,b=CheckColor()
assert(r==1 and g==0.5 and b==0.1)
ColorSet.Orange.g=0.6; ColorSet.Orange.b=0.7
r,g,b=CheckColor()
assert(r==0.5 and g==0.6 and b==0.7)
print("PASS: incomplete optional accent colors use complete fallback RGB")
'''
subprocess.run([lua, "-"], input=color_fixture, text=True, cwd=root, check=True)
