"""Production no-allocation ownership index: long paths, saturation and concurrency."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include "t7_lua_ownership.hpp"
#include <cassert>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>
#include <atomic>
int main(){
 T7LuaOwnership::Index index;
 auto path=[](int i){return "ui/"+std::string(180,'a')+"/custom_"+std::to_string(i)+".lua";};
 assert(!index.MayContain("ui/LUI/LUI.lua"));
 for(int i=0;i<1200;++i) index.Mark(path(i).c_str());
 for(int i=0;i<1200;++i) assert(index.MayContain(path(i).c_str()));
 assert(!index.MayContain("ui/LUI/LUI.lua"));
 index.Mark("UI/TEST.LUA");assert(index.MayContain("ui/test.lua"));
 index.Mark("ui\\long\\test.lua");assert(index.MayContain("ui/long/test.lua"));
 std::vector<std::thread> workers;
 for(int t=0;t<8;++t)workers.emplace_back([&,t]{for(int i=t;i<20000;i+=8)index.Mark(path(i).c_str());});
 for(auto&t:workers)t.join();
 for(int i=0;i<20000;++i)assert(index.MayContain(path(i).c_str()));
 unsigned extra=0;
 for(int i=0;i<100000;++i)extra+=index.MayContain(("ui/stock/"+std::to_string(i)+".lua").c_str());
 assert(extra<50); // Saturation must not make all unrelated stock Lua retained.
 for(auto name:{"ui/LUI/LUI.lua","ui/uieditor/clientfieldmodels.lua","ui/uieditor/widgets/MediaManager/MediaManager_SelectedItemInfo.lua","ui/uieditor/widgets/Barracks/CombatRecordButton.lua"})assert(!index.MayContain(name));
 index.Mark("ui/LUI/LUI.lua");assert(index.MayContain("ui/LUI/LUI.lua")); // Real overrides still receive lifetime protection.
 printf("PASS: 20000 long-path owners, case/slash parity, concurrent insertion, conservative saturation; %u of100000 extra stock matches\n",extra);
}
'''
with tempfile.TemporaryDirectory(prefix='bo3-ownership-') as d:
 cpp=Path(d)/'check.cpp';exe=Path(d)/'check';cpp.write_text(fixture)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-pthread','-I',str(root),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=30)
