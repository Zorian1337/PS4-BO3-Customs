"""Exercise actual load/XPAK hooks under deterministic concurrent and nested calls."""
from pathlib import Path
import os, subprocess, sys, tempfile

root=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (root/'t7_maps.cpp').read_text()
def function(name,kind='uint64_t'):
    a=source.index('static '+kind+' '+name+'(');b=source.index('{',a);depth=1;end=b+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[a:end]
state='static ModLoadContexts<> g_zoneLoadContexts;' if 'g_zoneLoadContexts' in source else 'static std::atomic<uintptr_t> g_loadingZone{0}; static std::atomic<uint64_t> g_loadingThread{0};'
fixture=r'''
#include "mod_load_context.hpp"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <string>
#include <thread>
using Hook_t=uint64_t(*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,double,double,double,double,double,double,double,double);
using LoadXFile_t=uint64_t(*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,double,double,double,double,double,double,double,double);
static thread_local uint64_t identity=0;
static uint64_t scePthreadSelf(){return identity;}
constexpr int kNameMax=56,kXpakNames=16;
static char g_xpakNames[kXpakNames][kNameMax+8]{};
static std::atomic<unsigned> g_xpakNameAt{0};
struct Entry{struct{const char*name;}mod;};
static Entry g_stack[]={{{"base"}},{{"second"}},{{"third"}}};
static int g_stackCount=3;
struct ListReader{};
static bool RangeReadable(uintptr_t p,size_t){return p!=0;}
static bool LanguagePrefixed(const char*){return false;}
static bool StackName(const char*zone,int* index,char* inner,size_t size){int slot=0; if(sscanf(zone,"m%d_",&slot)!=1)return false;*index=slot-1;snprintf(inner,size,"zm_mod");return true;}
static bool StackFileIn(const Entry&,const char*file,bool){return strcmp(file,"zm_mod.xpak")==0;}
static void T7Log_Write(const char*,...){}
constexpr int kKeyValuePairs=1,kBgCache=2,kScriptParseTree=54,kRawFileAsset=47;
static thread_local int noted=-1;
static void NoteUiFile(uintptr_t,int index){noted=index;}
static void ClaimStackScript(uintptr_t,int index){noted=index;}
static int StackIndexOfZone(const char*zone){int index=-1;char inner[56];StackName(zone,&index,inner,sizeof(inner));return index;}
static int ZoneKind(const char*,bool*){return 1;}
static bool EqualsNoCase(const char*a,const char*b){return strcmp(a,b)==0;}
static const char* InternName(const char*){return "unused";}
struct ClaimLock{};

static thread_local std::string opened;
static uint64_t NativeXpak(uint64_t a,uint64_t b,uint64_t c,uint64_t d,uint64_t e,uint64_t f,double x0,double x1,double x2,double x3,double x4,double x5,double x6,double x7){
 assert(b==2&&c==3&&d==4&&e==5&&f==6&&x0==1&&x1==2&&x2==3&&x3==4&&x4==5&&x5==6&&x6==7&&x7==8);opened=(const char*)a;return 0x4321;
}
static void* g_xpakOpenOriginal=(void*)NativeXpak;
static uint64_t NativeLoad(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,double,double,double,double,double,double,double,double);
static void* g_loadXFileOriginal=(void*)NativeLoad;
STATE
HOOKS
static void Open(){ alignas(uintptr_t) uint64_t header=1; uint64_t asset[2]={kRawFileAsset,(uintptr_t)&header};noted=-1;RenameStackAsset((uintptr_t)asset); assert(XPakOpen_h((uint64_t)"zm_mod",2,3,4,5,6,1,2,3,4,5,6,7,8)==0x4321);}
static uint64_t Load(const char*zone,uint64_t flag=2){return LoadXFile_h(1,flag,(uint64_t)zone,4,5,6,7,8,1,2,3,4,5,6,7,8);}
static std::atomic<int> phase{0};
static uint64_t NativeLoad(uint64_t a,uint64_t flag,uint64_t zone,uint64_t d,uint64_t e,uint64_t f,uint64_t g,uint64_t h,double x0,double x1,double x2,double x3,double x4,double x5,double x6,double x7){
 assert(a==1&&d==4&&e==5&&f==6&&g==7&&h==8&&x0==1&&x1==2&&x2==3&&x3==4&&x4==5&&x5==6&&x6==7&&x7==8);
 if(identity==1){phase=1;while(phase<2)std::this_thread::yield();Open();assert(noted==1&&opened=="m2_zm_mod");phase=3;}
 else if(identity==2){phase=2;while(phase<3)std::this_thread::yield();Open();assert(noted==2&&opened=="m3_zm_mod");}
 else if(identity==9){Open();assert(opened==(const char*)zone);if(flag==2){assert(Load("m3_zm_mod",3)==0x9876);Open();assert(opened=="m2_zm_mod");}}
 return 0x9876;
}
int main(){
 identity=9;assert(Load("m2_zm_mod")==0x9876);Open();assert(opened=="zm_mod");
 std::thread a([]{identity=1;assert(Load("m2_zm_mod")==0x9876);Open();assert(opened=="zm_mod");});
 while(phase<1)std::this_thread::yield();
 std::thread b([]{identity=2;assert(Load("m3_zm_mod")==0x9876);Open();assert(opened=="zm_mod");});a.join();b.join();
 identity=9;Open();assert(opened=="zm_mod");
}
'''.replace('STATE',state).replace('HOOKS',function('RenameStackAsset','void')+'\n'+function('LoadXFile_h')+'\n'+function('XPakOpen_h'))
with tempfile.TemporaryDirectory(prefix='zone-context-',dir=root.parent/'build') as tmp:
    cpp=Path(tmp)/'check.cpp';exe=Path(tmp)/'check';cpp.write_text(fixture)
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-pthread','-fsanitize=address,undefined','-I',str(root),str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=30)
print('PASS: concurrent/nested asset ownership and XPAK isolation, native calls/arguments/results, restored context after exit')
