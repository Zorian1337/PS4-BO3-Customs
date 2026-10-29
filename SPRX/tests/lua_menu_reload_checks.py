"""Exercise actual Mods menu entry/query callbacks across repeated opens."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[2];source=(root/'Lua/ui_scripts/mods.lua').read_text()
def section(start,end):return source[source.index(start):source.index(end,source.index(start))]
fixture=r'''
assert(loadfile("Lua/ui_scripts/mods.lua"))
local UI={pcMenu=true,logged={}}
local engine={GetPrimaryController=function()return 0 end}
local function IsElement(v)return type(v)=="table" end
local function Log()end
local function LogOnce()end
local function ActiveList()return BO3CustomsActiveMods or {} end
local function Define(name,fn)if rawget(_G,name)==nil then rawset(_G,name,fn)end end
local opened,delegated,fallback=0,0,0
Mods_OpenLoadMenu=function()delegated=delegated+1;error("unsupported PC LobbyVM open")end
local nativeOpen=Mods_OpenLoadMenu
Mods_UsingModsUgcName=function()delegated=delegated+1;return "native outside" end
Mods_UsingModsInternalName=function()return "native internal"end
Mods_IsUsingMods=function()return false end
UI.Open=function()fallback=fallback+1;return "fallback"end
'''
fixture+=section('local function Controller(','local function StatusText(')
fixture+=section('function UI.OpenMenu(','function UI.Applied(')
fixture+=section('function UI.OpenAction(','Define("Mods_LoadMod"')
fixture+=section('local function BindMenuQuery(','\nRefreshLobby()\nLog("installed")')
fixture+=r'''
local ButtonId="btnModsLoad"
local ModeIds={btnZM=true}
local cod={LobbyMenus={History={}}}
LobbyData={UITargets={UI_MODESELECT={id=0}},GetLobbyNav=function()return 0 end}
BO3CustomMods={{name="ds4c"}}
'''
fixture+=section('local function IsMainMenuTarget(','local function HideOnline(')
fixture+=r'''
local parent={}
OpenPopup=function(menu,name,controller)
 assert(menu==parent and name=="MenuModsLoad" and controller==0)
 assert(UI.opening and Mods_UsingModsUgcName()=="ugc1")
 opened=opened+1;UI.menu=parent;return parent
end
BO3CustomsActiveMods={{name="ds4c",ugc="ugc1",internal="core_mod"}}
for i=1,20 do
 local buttons={{customId="btnZM"}}
 AddModsButton(nil,0,buttons)
 assert(#buttons==2 and buttons[2].action~=nativeOpen)
 buttons[2].action(parent,nil,nil)
 assert(opened==i and delegated==0 and not UI.opening)
 assert(Mods_IsUsingMods() and Mods_UsingModsInternalName()=="core_mod")
 BO3CustomsActiveMods={}
 assert(Mods_UsingModsUgcName()=="" and not Mods_IsUsingMods())
 UI.menu=nil
 BO3CustomsActiveMods={{name="ds4c",ugc="ugc1",internal="core_mod"}}
end
assert(Mods_OpenLoadMenu==nativeOpen)
assert(Mods_UsingModsUgcName()=="native outside" and delegated==1)
OpenPopup=function()error("construction failed")end
assert(UI.OpenMenu(parent,nil)=="fallback" and fallback==1 and not UI.opening)
print("PASS: 20 menu reopen cycles bypass unsupported PC opener, normalize controller, scope live mod queries and preserve outside native handlers; popup failure restores state")
'''
subprocess.run([sys.argv[1],'-'],input=fixture,text=True,cwd=root,check=True)
