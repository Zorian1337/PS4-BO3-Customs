#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace T7ErrorCapture
{
// Caller serializes Push/Drain. No allocator, file IO or game callbacks here.
class Buffer
{
    static constexpr size_t kHistory = 32 * 1024, kQueue = 128 * 1024;
    char history[kHistory]{}, queue[kQueue]{};
    char build[512]{}, context[16][512]{};
    size_t contextNext=0, contextSize=0;
    size_t head=0, historySize=0, queued=0;
    uint64_t until=0;
    uint32_t dropped=0;
    void Add(const char* text,size_t size)
    {
        if (size > kQueue-queued) { ++dropped; return; }
        memcpy(queue+queued,text,size);queued+=size;
    }
    void Remember(const char* text,size_t size)
    {
        if (size>kHistory) { text+=size-kHistory;size=kHistory; }
        const size_t first=size<kHistory-head?size:kHistory-head;
        memcpy(history+head,text,first);memcpy(history,text+first,size-first);
        head=(head+size)%kHistory;historySize=historySize+size<kHistory?historySize+size:kHistory;
    }
public:
    static bool IsError(const char* text)
    {
        return (strstr(text,"[Lua]") && (strstr(text," Error ") || strstr(text," failed "))) ||
               strstr(text,"UI Error ") || strstr(text," runtime error ") ||
               strstr(text,"[Error]") || strstr(text,"[Fatal]") ||
               strstr(text,"[Asset] missing ") || strstr(text,"cannot retain ") ||
               strstr(text,"before loading borrowed bytecode") || strstr(text,"out of memory") ||
               strstr(text,"[Stall] the game has made no progress") || strstr(text,"clientfield mismatch");
    }
    void Push(const char* text,size_t size,uint64_t now)
    {
        if (strstr(text,"[Build]"))
        {
            const size_t count=size<sizeof(build)-1?size:sizeof(build)-1;
            memcpy(build,text,count);build[count]=0;
        }
        if (strstr(text,"[Transition]") || strstr(text,"[Mods] applying") || strstr(text,"[Zones] load"))
        {
            const size_t count=size<sizeof(context[0])-1?size:sizeof(context[0])-1;
            memcpy(context[contextNext],text,count);context[contextNext][count]=0;
            contextNext=(contextNext+1)%16;if(contextSize<16)++contextSize;
        }
        const bool error=IsError(text);
        if (error && (!until || now>until))
        {
            const char marker[]="\n================ CRASH / ERROR CONTEXT ================\n";
            Add(marker,sizeof(marker)-1);Add(build,strlen(build));
            for(size_t i=0;i<contextSize;++i)
            {
                const char* line=context[(contextNext+16-contextSize+i)%16];
                Add(line,strlen(line));
            }
            const size_t start=(head+kHistory-historySize)%kHistory;
            const size_t first=historySize<kHistory-start?historySize:kHistory-start;
            Add(history+start,first);Add(history,historySize-first);
        }
        if (error) until=now+3000000;
        if (error || (until && now<=until)) Add(text,size);
        Remember(text,size);
    }
    size_t Drain(char* out,size_t capacity,uint32_t* lost)
    {
        if (capacity<queued) return 0;
        memcpy(out,queue,queued);const size_t result=queued;queued=0;
        *lost=dropped;dropped=0;return result;
    }
};
}
