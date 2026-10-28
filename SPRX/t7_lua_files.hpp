#pragma once

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "t7_maps.hpp"
#include "t7_log.hpp"

// Read-only companion files. Configuration/saves/log writes keep their existing paths.
namespace T7LuaFiles
{
constexpr size_t kRootSize = 192;
constexpr size_t kMaxRoots = 16;
inline char g_roots[kMaxRoots][kRootSize] = {};
inline size_t g_rootCount = 0;
inline std::atomic<bool> g_ready{false};
inline std::atomic<bool> g_loading{false};

inline bool SafePath(const char* path, bool absolute)
{
    if (!path || !*path || (path[0] == '/') != absolute)
        return false;
    const char* segment = path;
    for (const char* at = path;; ++at)
    {
        const unsigned char c = (unsigned char)*at;
        if (c && (c < 32 || c == 127 || c == '\\' || c == ':'))
            return false;
        if (!c || c == '/')
        {
            const size_t length = (size_t)(at - segment);
            if ((length == 1 && segment[0] == '.') ||
                (length == 2 && segment[0] == '.' && segment[1] == '.'))
                return false;
            segment = at + 1;
        }
        if (!c)
            return true;
    }
}

inline char* ReadAt(const char* path, size_t maximum, size_t* length, bool text)
{
    const int fd = sceKernelOpen(path, SCE_KERNEL_O_RDONLY, 0);
    if (fd < 0)
        return nullptr;
    const int64_t size = sceKernelLseek(fd, 0, SEEK_END);
    char* body = nullptr;
    size_t used = 0;
    if (size > 0 && (uint64_t)size <= maximum && sceKernelLseek(fd, 0, SEEK_SET) == 0)
        body = (char*)malloc((size_t)size + 1);
    while (body && used < (size_t)size)
    {
        const int64_t got = sceKernelRead(fd, body + used, (size_t)size - used);
        if (got <= 0 || (uint64_t)got > (size_t)size - used)
            break;
        used += (size_t)got;
    }
    char extra;
    const bool complete = body && used == (size_t)size && sceKernelRead(fd, &extra, 1) == 0;
    const bool closed = sceKernelClose(fd) >= 0;
    if (!complete || !closed || (text && memchr(body, 0, used)))
    {
        free(body);
        return nullptr;
    }
    body[used] = 0;
    if (length)
        *length = used;
    return body;
}

inline void LoadRoots()
{
    if (g_ready.load(std::memory_order_acquire))
        return;
    while (g_loading.exchange(true, std::memory_order_acquire))
        sceKernelUsleep(50);
    if (!g_ready.load(std::memory_order_relaxed))
    {
        // This small bootstrap file stays internal so recovery does not depend on a drive.
        char* roots = ReadAt("/data/BO3-Customs/lua_roots.txt", 4096, nullptr, true);
        for (char* at = roots; at && *at && g_rootCount < kMaxRoots;)
        {
            char* end = strchr(at, '\n');
            char* next = end ? end + 1 : nullptr;
            if (end)
                *end = 0;
            while (*at == ' ' || *at == '\t')
                ++at;
            size_t length = strlen(at);
            while (length && (at[length - 1] == ' ' || at[length - 1] == '\t' || at[length - 1] == '\r' || at[length - 1] == '/'))
                at[--length] = 0;
            if (*at != '#' && length < kRootSize && SafePath(at, true))
            {
                bool duplicate = false;
                for (size_t i = 0; i < g_rootCount; ++i)
                    duplicate = duplicate || strcmp(g_roots[i], at) == 0;
                if (!duplicate)
                    snprintf(g_roots[g_rootCount++], kRootSize, "%s", at);
            }
            at = next;
        }
        free(roots);
        g_ready.store(true, std::memory_order_release);
    }
    g_loading.store(false, std::memory_order_release);
}

inline char* Read(const char* relative, size_t maximum, size_t* length = nullptr, bool text = true)
{
    if (length)
        *length = 0;
    if (!maximum || !SafePath(relative, false))
        return nullptr;
    LoadRoots();
    const size_t drives = sizeof(k_driveRoots) / sizeof(k_driveRoots[0]);
    for (size_t i = 0; i < g_rootCount + 1 + drives; ++i)
    {
        char root[kRootSize];
        if (i < g_rootCount)
            snprintf(root, sizeof(root), "%s", g_roots[i]);
        else if (i == g_rootCount)
            snprintf(root, sizeof(root), "/data/BO3-Customs");
        else
            snprintf(root, sizeof(root), "/%s/BO3-Customs", k_driveRoots[i - g_rootCount - 1]);
        char path[512];
        const int count = snprintf(path, sizeof(path), "%s/%s", root, relative);
        if (count < 0 || (size_t)count >= sizeof(path))
            continue;
        char* body = ReadAt(path, maximum, length, text);
        if (body)
        {
            if (strcmp(root, "/data/BO3-Customs") != 0)
                T7Log_Write("[Lua] companion %s read from %s", relative, root);
            return body;
        }
    }
    return nullptr;
}
}
