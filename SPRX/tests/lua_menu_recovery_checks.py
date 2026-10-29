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
local Tabs={lists={},current={}}
local choosing,owned=false,false
local function Choosing() return choosing end
local function Zombies() return 0 end
local function ExternalZMOwner() return owned end
local function CustomList() return {1} end
local function LogOnce() end
local function EnsureCustomEntries() end
-- PrepareZMMaps calls the catalog normalizer in production; this fixture is
-- testing ownership/table preservation and intentionally supplies no catalog.
local function NormalizeCatalogEntries() end
local function NormalizeMapRows(items) return items end
local function NormalizeZMRows(items) return items end
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
-- Keep the provider's MapList and use one category control. Existing category
-- controls own navigation; otherwise our existing tabs drive the provider list.
local added,removed,updated=0,0,0
AddTabs=function() added=added+1 end
local ownedMenu={
  BO3TabBar={close=function() removed=removed+1 end,
    Tabs={grid={updateDataSource=function() end}}},
  MapList={updateDataSource=function() updated=updated+1 end},
}
owned=true
RefreshZombies(ownedMenu,0)
assert(added==0 and removed==0 and updated==1 and ownedMenu.BO3TabBar~=nil,
  "provider MapList must retain the shared category tabs")
ownedMenu.mapCategoriesList={}
RefreshZombies(ownedMenu,0)
assert(removed==1 and updated==2 and ownedMenu.BO3TabBar==nil,
  "provider category controls must not receive a second tab bar")
local providerMenu={MapList={}}
RefreshZombies(providerMenu,0)
assert(added==1, "provider with no category controls must get the shared tabs")
owned=false
local stockMenu={MapList={}}
RefreshZombies(stockMenu,0)
assert(added==2, "stock menu refresh must retain BO3-Customs tabs")
print("PASS: failed ZM list recovery retains valid stock/custom map IDs, excludes locked/hidden/MP maps, preserves successful builders and restores map tables")
'''
subprocess.run([lua, "-"], input=map_fixture, text=True, cwd=root, check=True)

# Provider compatibility rows must remain in Customs and collapse onto the
# installed internal map row, regardless of whether their external ID is numeric.
catalog_fixture = r'''
local BO3CustomMaps={
  {id="zm_backrooms", name="Backrooms", ugc=123456789},
  {id="zm_other", displayName="Other Map"},
  {id="zm_shared_a", name="Shared Map"},
  {id="zm_shared_b", title="Shared Map"},
}
local function AllCustom() return BO3CustomMaps end
local function Zombies() return 0 end
local function Multiplayer() return 1 end
'''
catalog_fixture += section(maps, "local function ModeOf(", "local function Template(")
catalog_fixture += r'''
local mapsTable={
  zm_nacht={session_mode=0,dlc_pack=0,unique_id=1,mapName="Nacht"},
  zm_backrooms={session_mode=0,dlc_pack=0,unique_id=2,mapName="Backrooms"},
  ["123456789"]={session_mode=0,dlc_pack=0,unique_id=90,publisherId=123456789,mapName="^1Backrooms Compatibility"},
  catalog_alias={session_mode=0,dlc_pack=0,unique_id=91,ugc="123456789",mapName="A different compatibility title"},
  zm_other={session_mode=0,dlc_pack=0,unique_id=3,mapName="Other Map"},
  catalog_title_alias={session_mode=0,dlc_pack=0,unique_id=92,mapTitle="^2Other Map"},
  zm_shared_a={session_mode=0,dlc_pack=0,unique_id=4,mapName="Shared Map"},
  zm_shared_b={session_mode=0,dlc_pack=0,unique_id=5,mapName="Shared Map"},
  catalog_ambiguous={session_mode=0,dlc_pack=0,unique_id=93,mapTitle="Shared Map"},
}
local standard=VisibleMaps(mapsTable,0,false)
assert(standard.zm_nacht~=nil and standard.zm_backrooms==nil and standard["123456789"]==nil and
  standard.catalog_alias==nil and standard.zm_other==nil and standard.catalog_title_alias==nil and
  standard.catalog_ambiguous==nil,
  "custom catalog rows or compatibility aliases leaked into Standard")
local custom=VisibleMaps(mapsTable,0,true)
assert(custom.zm_backrooms==mapsTable.zm_backrooms and custom["123456789"]==nil and
  custom.catalog_alias==nil and custom.zm_other==mapsTable.zm_other and custom.catalog_title_alias==nil and
  custom.zm_shared_a==mapsTable.zm_shared_a and custom.zm_shared_b==mapsTable.zm_shared_b and
  custom.catalog_ambiguous==nil,
  "Customs must keep installed rows once and omit unresolved aliases")
print("PASS: catalog aliases stay out of Standard, canonical maps appear once, and ambiguous aliases fail closed")
'''
subprocess.run([lua, "-"], input=catalog_fixture, text=True, cwd=root, check=True)

# Execute the actual ListHelper/DataSource wrappers with a provider that appends
# its own catalog independently of CoD.mapsTable, as replacement menus can do.
provider_fixture = r'''
local Tabs={current={},lists={},injectedMaps={}}
local CustomsCategory=10100
local owned,choosing=true,false
local function ExternalZMOwner() return owned end
local function Choosing() return choosing end
local function Zombies() return 0 end
local function Multiplayer() return 1 end
local function LogOnce() end
local function EnsureCustomEntries() end
local function Current(c) return Tabs.current[c or 0] or "standard" end
local function SquareButton() return 2 end
local function AddRefreshButton() end
local function Try(label,fn,...)
 local ok,err=pcall(fn,...);assert(ok,err);return ok
end
local catalog={
 {id="zm_backrooms",name="Backrooms",ugc="123456789"},
 {id="zm_other",name="Other Map"},
 {id="mp_backrooms",name="Backrooms",mode="mp"},
}
local function AllCustom() return catalog end
CoD={gameModeEnum=0,perController={[0]={mapCategory=0}},mapsTable={
 zm_nacht={session_mode=0,dlc_pack=0,unique_id=1,mapName="Nacht"},
 zm_backrooms={session_mode=0,dlc_pack=0,unique_id=2,mapName="^1Backrooms"},
 zm_other={session_mode=0,dlc_pack=0,unique_id=3,mapName="^2Backrooms"},
}}
Engine={IsMapValid=function(id) return CoD.mapsTable[id]~=nil end,
 Localize=function(s) return s end,DvarString=function() return "zm_backrooms" end}
'''
provider_fixture += section(maps, "local function ModeOf(", "local function Template(")
provider_fixture += section(maps, "local function MapRowTitle(", "local function TitleSet(")
provider_fixture += section(maps, "local function TabOf(", 'DataSources.BO3CustomsMapTabs =')
provider_fixture += section(maps, "local function RemoveInjectedEntries(", "local function WrapCombatRecord(")
provider_fixture += section(maps, "local function AddTabs(", "local function Refresh(")
provider_fixture += section(maps, "local function CreateWithRefresh(", "local function HasCustoms(")
provider_fixture += section(maps, "local function RemoveOwnedTabs(", "local function RefreshMultiplayer(")
provider_fixture += section(maps, "local function WrapMenu(", "local function WrapChangeMap(")
provider_fixture += section(maps, "local function AddCustomsCategory(", "local function Install(")
provider_fixture += r'''
local callback=function(row) return row.properties.mapId end
local providerRows={
 {models={displayText="Nacht"},properties={mapId="zm_nacht"}},
 {models={displayText="^2Backrooms"},properties={mapId="zm_backrooms",selectIndex=true}},
 {models={displayText=" ^1BACKROOMS ",mapName="Backrooms",compatibilityStatus="COMPATIBLE"},
  properties={mapId="123456789",internalMapName="123456789",workshopId="123456789",
    mapStatsId="stats-key",onSelect=callback,purchasable=true}},
 {models={displayText="^5Backrooms"},properties={mapId="zm_other"}},
 {models={displayText="another alias title"},properties={mapId="zm_backrooms"}},
 {models={displayText="not installed"},properties={mapId="999999999"}},
 {models={displayText="^3Backrooms"},properties={mapId="mp_backrooms"}},
 owner="provider",
}
local calls=0
local function provider(c,list)
 calls=calls+1
 return providerRows
end
ListHelper_Prepare=function(list,c,name,build)
 list.rows=build(c,list)
 return "native result"
end
DataSources={ZMMapsList={prepare=function(c,list)
 return ListHelper_Prepare(list,c,"ZMMapsList",provider)
end}}
assert(WrapListPrepare() and WrapMapsList())
local full=CoD.mapsTable
local list={}
Tabs.current[0]="standard"
assert(DataSources.ZMMapsList.prepare(0,list)=="native result")
assert(calls==1 and #list.rows==1 and list.rows[1].properties.mapId=="zm_nacht",
 "provider-appended custom rows leaked into Standard")
Tabs.current[0]="custom"
DataSources.ZMMapsList.prepare(0,list)
assert(calls==2 and #list.rows==1 and list.rows.owner=="provider",
 "aliases or differently colored copies remained in Customs")
local row=list.rows[1]
assert(row.properties.mapId=="zm_backrooms" and row.properties.internalMapName=="zm_backrooms")
assert(row.models.compatibilityStatus=="COMPATIBLE" and row.properties.workshopId=="123456789" and
 row.properties.mapStatsId=="stats-key" and row.properties.onSelect==callback,
 "provider compatibility, stats or callback metadata was lost")
assert(callback(row)=="zm_backrooms" and row.properties.selectIndex==true and row.properties.purchasable==false)
assert(row.models.displayText==" ^1BACKROOMS " and providerRows[3].properties.mapId=="123456789" and
 providerRows[3].properties.selectIndex==nil and providerRows[3].properties.purchasable==true,
 "normalization changed the provider's reusable source row")
for i=1,20 do DataSources.ZMMapsList.prepare(0,list);assert(#list.rows==1) end
assert(CoD.mapsTable==full)
-- A title/ID bridge must merge both earlier groups rather than leave a second
-- winner when identifiers and display names disagree across provider rows.
local bridge={
 {models={displayText="Alpha"},properties={mapId="zm_backrooms"}},
 {models={displayText="Beta"},properties={mapId="zm_other"}},
 {models={displayText="^1Beta"},properties={mapId="zm_backrooms"}},
}
assert(#NormalizeMapRows(bridge,0,true)==1, "transitive aliases left multiple winners")
for a=1,3 do for b=1,3 do for c=1,3 do
 if a~=b and a~=c and b~=c then
  assert(#NormalizeMapRows({bridge[a],bridge[b],bridge[c]},0,true)==1,
    "alias cleanup depended on provider row order")
 end
end end end
-- Names differing by punctuation are not merely color variants.
bridge[3]=nil;bridge[1].models.displayText="A: Map";bridge[2].models.displayText="A Map"
assert(#NormalizeMapRows(bridge,0,true)==2)
-- Playlist IDs and opaque non-map contracts remain owned by the provider.
choosing=true;DataSources.ZMMapsList.prepare(0,list);assert(list.rows==providerRows);choosing=false
local opaque={{models={custom="keep"}}}
assert(NormalizeMapRows(opaque,0,true)==opaque)
CoD.perController[0].mapCategory=10100
local count=calls
local changed=PrepareMaps(provider,0,list)
assert(#changed==1 and calls==count+1 and CoD.mapsTable==full and CoD.perController[0].mapCategory==10100)
assert(not pcall(PrepareMaps,function() error("provider failed") end,0,list))
assert(CoD.mapsTable==full and CoD.perController[0].mapCategory==10100)
CoD.perController[0].mapCategory=0
assert(#PrepareMaps(provider,0,list)==1)
local categories={{models={text="STANDARD"},properties={category=0}}}
local function categoryProvider() return categories end
PrepareCategories(categoryProvider,0,list);PrepareCategories(categoryProvider,0,list)
assert(#categories==2, "repeated category preparation appended another Customs tab")
-- Recovery must pass through the same category and color-duplicate filter.
Tabs.current[0]="custom"
ListHelper_Prepare(list,0,"ZMMapsList",function() error("provider failed") end)
assert(#list.rows==1 and list.rows[1].properties.mapId~="zm_nacht")
-- The provider keeps its menu, list widget and click handler. Shared tabs only
-- choose which completed rows that same builder supplies.
local elements,created,updates,watcherClosed={},0,0,0
local mapList={onSelect=callback,setTopBottom=function() end,
 updateDataSource=function() updates=updates+1;DataSources.ZMMapsList.prepare(0,list) end}
local menu={MapList=mapList,addElement=function(self,e) elements[#elements+1]=e end}
CoD.FE_TabBar={new=function()
 local grid={setHorizontalCount=function() end,setDataSource=function() end,updateDataSource=function() end}
 return {Tabs={grid=grid},setLeftRight=function() end,setTopBottom=function() end,close=function() end}
end}
LUI={UIElement={new=function()
 return {linkToElementModel=function(self,grid,name,link,fn) self.onTab=fn end,
   close=function() watcherClosed=watcherClosed+1 end}
end},createMenu={ZMMapSelection=function() created=created+1;return menu end}}
Engine.GetModelValue=function(value) return value end
assert(WrapMenu())
assert(LUI.createMenu.ZMMapSelection(0)==menu and menu.MapList==mapList and mapList.onSelect==callback)
assert(menu.BO3TabBar~=nil and #elements==2 and #list.rows==1)
elements[2].onTab("standard")
assert(Tabs.current[0]=="standard" and #list.rows==1 and list.rows[1].properties.mapId=="zm_nacht")
LUI.createMenu.ZMMapSelection(0)
assert(created==2 and #elements==2 and Tabs.current[0]=="standard", "reopen duplicated tabs or lost their state")
menu.mapCategoriesList={}
LUI.createMenu.ZMMapSelection(0)
assert(menu.BO3TabBar==nil and menu.BO3TabWatcher==nil and watcherClosed==1 and
 Tabs.current[0]==nil and menu.MapList==mapList and #list.rows==2,
 "existing provider category controls must remain authoritative")
-- Placeholder fields must not outrank a classified provider row. Status zero
-- is meaningful: retain the provider's original incompatible-map check.
local warnings=0
local originalCheck=function(row)
 if tonumber(row.models.compatibilityStatus)==0 then warnings=warnings+1;return "confirm-incompatible" end
 return "load:"..row.properties.mapId
end
local placeholder={models={displayText="Backrooms",compatibilityStatus=-1},
 properties={mapId="zm_backrooms",workshopId="",mapStatsId="",onSelect=callback}}
local decorated={models={displayText="^1Backrooms",mapName="Backrooms",compatibilityStatus=0},
 properties={mapId="123456789",internalMapName="123456789",workshopId="123456789",
 mapStatsId="stats-key",onSelect=originalCheck}}
local kept=NormalizeMapRows({placeholder,decorated},0,true)
assert(#kept==1 and kept[1].models.displayText=="^1Backrooms" and kept[1].models.compatibilityStatus==0,
 "a plain placeholder replaced provider styling or compatibility status zero")
assert(kept[1].properties.onSelect==originalCheck and kept[1].properties.onSelect(kept[1])=="confirm-incompatible" and warnings==1)
assert(kept[1].properties.mapId=="zm_backrooms" and decorated.properties.mapId=="123456789")
-- Styling may live on a lower-ranked duplicate. Borrow only its display label;
-- keep the meaningful row's complete compatibility/callback contract.
local classified={models={displayText="Backrooms",mapName="Backrooms",compatibilityStatus=0},
 properties={mapId="zm_backrooms",workshopId="123456789",mapStatsId="stats-key",onSelect=originalCheck}}
local styled={models={displayText="^3Backrooms"},properties={mapId="zm_backrooms"}}
kept=NormalizeMapRows({classified,styled},0,true)
assert(#kept==1 and kept[1].models.displayText=="^3Backrooms" and kept[1].models.compatibilityStatus==0 and
 kept[1].properties.onSelect==originalCheck and classified.models.displayText=="Backrooms" and styled.models.compatibilityStatus==nil,
 "preserving a colored label lost meaningful metadata or changed a reusable provider row")
styled.models.compatibilityStatus=1;styled.models.displayText="^2Backrooms"
kept=NormalizeMapRows({classified,styled},0,true)
assert(kept[1].models.displayText=="Backrooms" and kept[1].models.compatibilityStatus==0,
 "a colored alias with conflicting compatibility must not repaint the selected result")
-- Input catalog pruning must not discard the provider's decorated source
-- record before its builder has produced compatibility models and callbacks.
owned=false
CoD.mapsTable["123456789"]={session_mode=0,dlc_pack=0,mapName="Backrooms",mapNameCaps="^1Backrooms"}
local function metadataBuilder()
 local rows={placeholder}
 if CoD.mapsTable["123456789"]~=nil then rows[#rows+1]=decorated end
 return rows
end
DataSources.ZMMapsList={prepare=function(c,list)
 return ListHelper_Prepare(list,c,"ZMMapsList",metadataBuilder)
end}
assert(WrapMapsList());Tabs.current[0]="custom"
DataSources.ZMMapsList.prepare(0,list)
assert(#list.rows==1 and list.rows[1].models.displayText=="^1Backrooms" and list.rows[1].properties.onSelect==originalCheck,
 "the provider did not see its complete styled catalog")
CoD.perController[0].mapCategory=10100
kept=PrepareMaps(metadataBuilder,0,list)
assert(#kept==1 and kept[1].models.compatibilityStatus==0 and kept[1].models.displayText=="^1Backrooms" and
 CoD.mapsTable==full and CoD.perController[0].mapCategory==10100,
 "category organization pruned provider compatibility input or leaked temporary state")
local registered
local nativeAdd=function(menu,element,c,button,key,action,condition)
 registered=action;return "native registration"
end
CoD.Menu={AddButtonCallbackFunction=nativeAdd}
local providerMenu={}
local built=CreateWithRefresh(function()
 assert(CoD.Menu.AddButtonCallbackFunction(providerMenu,{},0,1,"ENTER",originalCheck,function() return true end)=="native registration")
 return providerMenu
end,0,"zm")
assert(built==providerMenu and registered==originalCheck and CoD.Menu.AddButtonCallbackFunction==nativeAdd and
 registered(kept[1])=="confirm-incompatible", "map selection wrapping replaced the provider's compatibility action")
print("PASS: completed provider rows dedupe across IDs/colors, stay in Customs, retain valid callbacks/metadata and recover without persistent mutations")
'''
subprocess.run([lua, "-"], input=provider_fixture, text=True, cwd=root, check=True)

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
