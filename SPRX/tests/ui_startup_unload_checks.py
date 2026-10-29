"""Exercise production startup gating, frame ordering and retention ownership."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
lua=(root/'t7_lua.cpp').read_text()
maps=(root/'t7_maps.cpp').read_text()
main=(root/'main.cpp').read_text()
def section(s,a,b): return s[s.index(a):s.index(b,s.index(a))]
gate=section(lua,'static bool FrontendReadyForInjection()','static void HookAddMenu()')
reset=section(lua,'void T7Lua_FrontendWillLoad()','void T7Lua_Tick()')
owner=section(maps,'bool T7Maps_NeedsLuaRetention(','bool T7Maps_UiTransitionBusy()')
frame=section(main,'uint64_t Frame_h(','bool IsBlackOps3(')
fixture=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <strings.h>
#include <string>
#include <cstdio>
static bool inLevel=false,uiReady=true,locked=false,menuExists=false;
static unsigned probes=0,recoveries=0;
static bool usingMods=false;
static bool T7Maps_UsingMods(){return usingMods;}
static bool T7Maps_MenusBroken(){++recoveries;return true;}
static bool T7Maps_InLevel(){return inLevel;}
namespace T7Lua {
static uintptr_t state=0x10000,g_base=(uintptr_t)&state;
constexpr uintptr_t kLuaState=0;
static std::atomic<uintptr_t> g_completedMainState{0};
static std::atomic<uint32_t> g_frontendGeneration{0};
static std::atomic<bool> g_menuInitPending{false};
static const char* k_menusProbeLua="probe";
static bool UiUp(){return uiReady;}
static bool UiTryLock(){return !locked;}
static void UiUnlock(){}
static void SetDvar(const char*,const char*){}
static bool RunLuaOn(uintptr_t,const char*,const char*){++probes;return true;}
static uintptr_t FindDvar(const char*){return 1;}
static const char* DvarText(uintptr_t){return menuExists?"1":"2";}
GATE
}
RESET
#include "t7_lua_ownership.hpp"
namespace T7Maps {
static T7LuaOwnership::Index g_modLuaOwnership;
}
OWNER
static std::string order;
static void T7Maps_FrameWork(){order+='M';}
static void T7Share_Tick(){order+='S';}
static void T7Builtins_Tick(){order+='B';}
static void T7Lua_Tick(){order+='L';}
using Hook_t=uint64_t(*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,double,double,double,double,double,double,double,double);
static uint64_t Native(uint64_t a,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,double x,double,double,double,double,double,double,double){assert(a==17 && x==1.25);order+='N';return 0xDEADBEEF;}
static void* g_frameOriginal=(void*)&Native;
FRAME
int main(){
 using namespace T7Lua;
 for(int i=0;i<29;++i)assert(!FrontendReadyForInjection());
 assert(probes==0);
 assert(!FrontendReadyForInjection() && probes==1);
 menuExists=true;
 for(int i=0;i<29;++i)assert(!FrontendReadyForInjection());
 assert(FrontendReadyForInjection() && probes==2);
 assert(g_completedMainState==state);
 auto before=probes;assert(FrontendReadyForInjection() && probes==before);
 T7Lua_FrontendWillLoad(); // The engine reuses the same VM address after Complex.
 menuExists=false;assert(g_completedMainState==0);
 for(int i=0;i<29;++i)assert(!FrontendReadyForInjection());
 assert(!FrontendReadyForInjection() && probes==before+1);
 state+=16;before=probes;
 for(int i=0;i<29;++i)assert(!FrontendReadyForInjection());
 assert(probes==before);
 g_completedMainState=state;assert(FrontendReadyForInjection());
 uiReady=false;assert(!FrontendReadyForInjection());uiReady=true;
 inLevel=true;g_completedMainState=0;assert(FrontendReadyForInjection());inLevel=false;
 T7Maps::g_modLuaOwnership.Mark("ui/mod.lua");
 T7Maps::g_modLuaOwnership.Mark("lua/shared/mod.lua");
 assert(!T7Maps_NeedsLuaRetention("ui/stock.lua"));
 assert(T7Maps_NeedsLuaRetention("UI/MOD.LUA"));
 assert(T7Maps_NeedsLuaRetention("lua/shared/mod.lua"));
 T7Lua_FrontendWillLoad();menuExists=false;usingMods=true;
 for(int i=0;i<60;++i)assert(!FrontendReadyForInjection());
 assert(recoveries==1); // A failed required module cannot strand the Mods menu.
 T7Lua_FrontendWillLoad();
 for(int i=0;i<30;++i)assert(!FrontendReadyForInjection());
 assert(recoveries==2);
 assert(Frame_h(17,2,3,4,5,6,1.25,2,3,4,5,6,7,8)==0xDEADBEEF);
 assert(order=="MSBNL");
 puts("PASS: delayed menu readiness, same-address frontend reset, late injection, conservative ownership, native-first Lua work and native result preservation");
}
'''
for key,value in [('GATE',gate),('RESET',reset),('OWNER',owner),('FRAME',frame)]:fixture=fixture.replace(key,value)
with tempfile.TemporaryDirectory(prefix='bo3-startup-') as d:
 cpp=Path(d)/'test.cpp';exe=Path(d)/'test';cpp.write_text(fixture)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(root),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=30)
