"""Exercise the production exact-range validator with fragmented mappings."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'SPRX/platform.cpp').read_text()
body=s[s.index('bool RangeReadable('):s.index('bool SafeStrStr(')]
fixture=r"""
#include <cstdint>
#include <cstddef>
#include <cassert>
struct SceKernelVirtualQueryInfo { void* start; void* end; int protection; };
static int mode=0, calls=0;
static int sceKernelVirtualQuery(void* p,int,SceKernelVirtualQueryInfo* q,size_t) {
 ++calls; auto a=(uintptr_t)p;
 if(a<0x10000 || a>=0x30000) return -1;
 auto base=a & ~(uintptr_t)0xfff;
 q->start=(void*)(base+(mode==1 && base==0x19000 ? 1:0));
 q->end=(void*)(mode==3 ? base : base+0x1000);
 q->protection=mode==2 && base==0x19000 ? 0:1;
 return 0;
}
"""+body+r"""
int main(){
 assert(RangeReadable(0x10000,0x18000)); assert(calls==24);
 assert(RangeReadable(0x10fff,2));
 for(mode=1;mode<=3;++mode) assert(!RangeReadable(0x10000,0x18000));
 mode=0; assert(!RangeReadable(0,1));assert(!RangeReadable(UINTPTR_MAX-2,8));
 assert(!RangeReadable(0x10000,0x30000));
 assert(RangeReadable(0x10000,0));
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'test.cpp';p.write_text(fixture);exe=Path(d)/'test'
 subprocess.run(['g++','-std=c++20','-Wall','-Wextra','-Werror',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: contiguous fragmented ranges, gaps, protections, progress, overflow and boundaries')
