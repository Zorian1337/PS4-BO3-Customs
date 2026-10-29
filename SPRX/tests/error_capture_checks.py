"""Production persistent-error buffer/file paths, including short writes and rotation."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'t7_log.cpp').read_text();a=s.index('static bool WriteAll(');b=s.index('static void Append(',a);io=s[a:b]
writer=s[s.index('static void* Writer('):s.index('static void WriteV(',s.index('static void* Writer('))]
fixture=r'''
#include "error_capture.hpp"
#include <cassert>
#include <cstdio>
#include <string>
#include <map>
#include <algorithm>
#include <cstdint>
struct SceKernelStat{long st_size;};
static const char* kErrorPath="errors",*kPreviousErrorPath="previous";
constexpr uint64_t kErrorLogMax=8*1024*1024;
constexpr int SCE_KERNEL_O_WRONLY=1,SCE_KERNEL_O_CREAT=2,SCE_KERNEL_O_APPEND=4;
static std::map<std::string,std::string> files;
static bool failSync=false,failRename=false;static std::string opened;
static int sceKernelStat(const char*p,SceKernelStat*out){if(!files.count(p))return -1;out->st_size=files[p].size();return 0;}
static int sceKernelRename(const char*a,const char*b){if(failRename)return -1;files[b]=files[a];files.erase(a);return 0;}
static int sceKernelOpen(const char*p,int flags,int){assert(flags==7);opened=p;return 1;}
static long sceKernelWrite(int,const char*p,size_t size){size=std::min(size,(size_t)7);files[opened].append(p,size);return size;}
static int sceKernelFsync(int){return failSync?-1:0;}
static int sceKernelClose(int){return 0;}
IO
constexpr size_t kQueueBytes=128*1024;
constexpr unsigned kWriterEveryUs=200000;
static T7ErrorCapture::Buffer g_errorCapture;
static char g_queue[kQueueBytes],g_flushing[kQueueBytes+128],g_errorFlushing[kQueueBytes+128];
static size_t g_queued=0;static uint32_t g_dropped=0;
static unsigned loops=0,notices=0;
static const char* kLogPath="session";
struct Done{};
static void QueueLock(){}static void QueueUnlock(){}
static uint64_t sceKernelGetProcessTime(){return loops*1000000ull;}
static void DebugOut(const char*){++notices;}
static void sceKernelUsleep(unsigned){
 if(++loops==4)throw Done{};
 failSync=loops==1;
 if(loops==2){const char line[]="[Lua] UI Error 222: next batch\n";g_errorCapture.Push(line,sizeof(line)-1,2000000);}
}
WRITER
int main(){
 T7ErrorCapture::Buffer buffer;static char bytes[128*1024];uint32_t dropped=0;
 auto push=[&](const std::string& text,uint64_t now){buffer.Push(text.c_str(),text.size(),now);};
 push("[Build] BUILD1\n",1);
 push("[Transition] loaded mod 1: ds4c\n",2);
 for(int i=0;i<2000;++i)push("ordinary progress line; no issue\n",3+i);
 assert(buffer.Drain(bytes,sizeof(bytes),&dropped)==0);
 push("[Lua] UI Error 12345: nil value\n",10000000);
 push("stack traceback: function caller\n",10000001);
 auto size=buffer.Drain(bytes,sizeof(bytes),&dropped);std::string report(bytes,size);
 assert(!dropped && report.find("BUILD1")!=std::string::npos);
 assert(report.find("loaded mod 1: ds4c")!=std::string::npos);
 assert(report.find("UI Error 12345")!=std::string::npos && report.find("function caller")!=std::string::npos);
 files["session"]="unchanged normal log";
 assert(AppendErrorFile(report.data(),report.size()));
 T7ErrorCapture::Buffer next;next.Push("[Build] BUILD2\n",15,1);
 next.Push("[Script] runtime error 5\n",25,10000000);size=next.Drain(bytes,sizeof(bytes),&dropped);
 assert(AppendErrorFile(bytes,size));
 assert(files["errors"].find("BUILD1")!=std::string::npos && files["errors"].find("BUILD2")!=std::string::npos);
 assert(files["session"]=="unchanged normal log");
 files["errors"]=std::string(kErrorLogMax,'X');files["previous"]="older";
 assert(AppendErrorFile("new",3));assert(files["errors"]=="new" && files["previous"].size()==kErrorLogMax);
 files["errors"]=std::string(kErrorLogMax,'Y');failRename=true;
 assert(!AppendErrorFile("abc",3));assert(files["errors"].size()==kErrorLogMax);failRename=false;
 failSync=true;assert(!AppendErrorFile("abc",3));failSync=false;
 assert(T7ErrorCapture::Buffer::IsError("[Lua] LobbyVM Error 74046: nil call"));
 assert(!T7ErrorCapture::Buffer::IsError("SIGSEGV:       normal"));
 assert(T7ErrorCapture::Buffer::IsError("[Stall] the game has made no progress"));
 files["errors"].clear();
 const char first[]="[Lua] UI Error 111: retry batch\n";g_errorCapture.Push(first,sizeof(first)-1,1);
 try{Writer(nullptr);}catch(const Done&){}
 assert(notices==1 && files["errors"].find("retry batch")!=std::string::npos && files["errors"].find("next batch")!=std::string::npos);
 puts("PASS: native error-only capture with build/mod/stack context, persistent append across sessions, short writes, sync failure, bounded rotation and unchanged session log");
}
'''.replace('IO',io).replace('WRITER',writer)
with tempfile.TemporaryDirectory(prefix='bo3-error-log-') as d:
 cpp=Path(d)/'check.cpp';exe=Path(d)/'check';cpp.write_text(fixture)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(root),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=30)
