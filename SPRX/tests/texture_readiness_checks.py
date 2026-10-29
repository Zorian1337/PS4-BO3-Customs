"""Execute the production timeout hook; no GPU/engine emulation claims."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]).read_text() if len(sys.argv) > 1 else (root / 't7_maps.cpp').read_text()
begin = source.index('static bool RequiredTexturePartsResident()') if 'static bool RequiredTexturePartsResident()' in source else source.index('static uint64_t TexturesLoaded_h(')
body = source[begin:source.index('static uint64_t DemoStart_h(', begin)]
fixture = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
using Hook_t=uint64_t(*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,double,double,double,double,double,double,double,double);
alignas(uintptr_t) static unsigned char memory[256]{};
static uintptr_t g_base=(uintptr_t)memory;
constexpr uintptr_t kScrVmTop=0,kStreamPending=16,kStreamStarted=20,kStreamDone=21,kStreamOverride=22;
constexpr uintptr_t kPartsRequired=32,kPartsInMemory=40,kMeshRequired=48,kMeshInMemory=52;
constexpr int kPartWords=2,kMeshWords=1,kVarInteger=7;
constexpr uint64_t kTextureWaitUs=180000000,kGateLogUs=1000000,kGateLogSlowUs=5000000;
static std::atomic<uint64_t> g_textureWaitStart{1},g_gateLogged{0},g_textureProbeAt{0};
static std::atomic<uint32_t> g_gateLogs{0};
static std::atomic<bool> g_usermapLevel{true},g_texturesForced{false};
static uint64_t now=180000002, calls=0;
static int nativeReady=0, sideEffect=0, checks=0;
static uintptr_t denied=0;
static bool RangeReadable(uintptr_t p,size_t n) {
    ++checks;
    if(p==g_base+kMeshInMemory && sideEffect==1) *(int32_t*)(g_base+kStreamPending)=1;
    if(p==g_base+kMeshInMemory && sideEffect==2) g_textureWaitStart=now;
    return p!=denied && p>=g_base && p-g_base<sizeof(memory) && n<=sizeof(memory)-(p-g_base);
}
static uint64_t sceKernelGetProcessTime(){return now;}
static void T7Log_Write(const char*,...){}
static void LogStreamGate(uint64_t,bool){}
static uint64_t Native(uint64_t a,uint64_t b,uint64_t c,uint64_t d,uint64_t e,uint64_t f,
 double x0,double x1,double x2,double x3,double x4,double x5,double x6,double x7) {
 assert(a==1&&b==2&&c==3&&d==4&&e==5&&f==6);
 assert(x0==1&&x1==2&&x2==3&&x3==4&&x4==5&&x5==6&&x6==7&&x7==8);
 ++calls; *(int32_t*)(memory+128)=nativeReady; return 0x12345678;
}
static void* g_texturesOriginal=(void*)Native;
''' + body + r'''
static int Run(){auto before=calls;auto result=TexturesLoaded_h(1,2,3,4,5,6,1,2,3,4,5,6,7,8);assert(calls==before+1&&result==0x12345678);return *(int32_t*)(memory+128);}
static void Reset(){
 memset(memory,0,sizeof(memory)); *(uintptr_t*)memory=g_base+128; *(int32_t*)(memory+136)=kVarInteger;
 memory[kStreamStarted]=memory[kStreamDone]=1;
 *(uint32_t*)(memory+kPartsRequired)=3; *(uint32_t*)(memory+kPartsInMemory)=3;
 *(uint32_t*)(memory+kMeshRequired)=5; *(uint32_t*)(memory+kMeshInMemory)=5;
 now=180000002;g_textureWaitStart=1;g_gateLogged=now;g_gateLogs=0;g_textureProbeAt=0;
 g_usermapLevel=true;g_texturesForced=false;nativeReady=0;sideEffect=0;denied=0;checks=0;
}
int main(){
 Reset();*(uint32_t*)(memory+kPartsInMemory)=1;assert(Run()==0); // idle flags, missing required texture
 Reset();*(uint32_t*)(memory+kMeshInMemory)=1;assert(Run()==0);
 Reset();denied=g_base+kPartsRequired;assert(Run()==0);
 Reset();denied=g_base+kMeshInMemory;assert(Run()==0);
 Reset();assert(Run()==1&&g_texturesForced);assert(Run()==1); // no success-path flicker
 Reset();*(uint32_t*)(memory+kPartsRequired)=0;*(uint32_t*)(memory+kMeshRequired)=0;assert(Run()==1);
 Reset();*(int32_t*)(memory+kStreamPending)=1;assert(Run()==0);
 Reset();memory[kStreamDone]=0;assert(Run()==0);
 Reset();sideEffect=1;assert(Run()==0); // new work appeared during residency scan
 Reset();sideEffect=2;assert(Run()==0); // level changed during residency scan
 Reset();now=2;assert(Run()==0);assert(checks<=2); // no residency scan before timeout
 Reset();now=1;g_textureWaitStart=100;assert(Run()==0&&g_textureWaitStart==1&&!g_texturesForced);
 Reset();g_usermapLevel=false;assert(Run()==0&&checks==0);
 Reset();denied=g_base+kPartsRequired;nativeReady=1;assert(Run()==1&&!g_textureWaitStart);
 Reset();denied=g_base+kScrVmTop;assert(Run()==0);
 Reset();*(int32_t*)(memory+136)=0;assert(Run()==0);
 Reset();*(uint32_t*)(memory+kPartsInMemory)=1;assert(Run()==0);checks=0;++now;
 assert(Run()==0&&checks<=5); // blocked fallback does not rescan every script tick
 now+=250000;*(uint32_t*)(memory+kPartsInMemory)=3;assert(Run()==1);
}
'''
with tempfile.TemporaryDirectory(prefix='texture-ready-', dir=root.parent/'build') as directory:
    test=Path(directory)/'check.cpp';test.write_text(fixture);exe=Path(directory)/'check'
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(test),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=30)
print('PASS: native readiness/calls preserved; fallback rejects missing/unreadable parts, transitions and new stream work; bounded retries')
