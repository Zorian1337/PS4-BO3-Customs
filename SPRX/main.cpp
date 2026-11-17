#include "headers.hpp"

#include <atomic>

namespace
{
constexpr uintptr_t kTitleProbe = 0x1312346;

constexpr uintptr_t kComFrame = 0xF0B8A0;

const uint8_t k_comFrame[] = { 0x55, 0x48, 0x89, 0xE5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54,
                               0x53, 0x48, 0x83, 0xE4, 0xE0, 0x48, 0x81, 0xEC, 0x40, 0x22, 0x00, 0x00 };

Detour g_frameDetour{};
void*  g_frameOriginal = nullptr;

using Hook_t = uint64_t (*)(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t, uint64_t,
                            double, double, double, double, double, double, double, double);

uint64_t Frame_h(uint64_t a1, uint64_t a2, uint64_t a3, uint64_t a4, uint64_t a5, uint64_t a6,
                 double x0, double x1, double x2, double x3, double x4, double x5, double x6, double x7)
{
#ifdef _DEBUG
    T7FrameWorkPhase_Set(1);
#endif
    T7Maps_FrameWork();
#ifdef _DEBUG
    T7FrameWorkPhase_Set(2);
#endif
    T7Share_Tick();
#ifdef _DEBUG
    T7FrameWorkPhase_Set(3);
#endif
    T7Builtins_Tick();
#ifdef _DEBUG
    T7FrameWorkPhase_Set(4);
#endif
    const uint64_t result = ((Hook_t)g_frameOriginal)(a1, a2, a3, a4, a5, a6, x0, x1, x2, x3, x4, x5, x6, x7);
#ifdef _DEBUG
    T7FrameWorkPhase_Set(5);
#endif
    T7Lua_Tick();
#ifdef _DEBUG
    T7FrameWorkPhase_Set(0);
#endif
    return result;
}

bool IsBlackOps3(uintptr_t base)
{
    return SafeStrStr(base + kTitleProbe, "Multiplayer") || SafeStrStr(base + kTitleProbe, "multiProgress");
}

uintptr_t WaitForBlackOps3()
{
    for (int attempt = 0; attempt < 100; ++attempt)
    {
        const uintptr_t base = (uintptr_t)GetBaseAddress();

        if (base && IsBlackOps3(base))
            return base;

        sceKernelUsleep(100 * 1000);
    }

    return 0;
}
}

#ifdef _DEBUG
namespace
{
std::atomic<uint32_t> g_frameWorkPhase{0};
std::atomic<uint64_t> g_frameWorkPhaseStarted{0};
}

void T7FrameWorkPhase_Set(uint32_t phase)
{
    if (!phase)
    {
        g_frameWorkPhase.store(0, std::memory_order_release);
        return;
    }

    g_frameWorkPhaseStarted.store(sceKernelGetProcessTime(), std::memory_order_relaxed);
    g_frameWorkPhase.store(phase, std::memory_order_release);
}

uint32_t T7FrameWorkPhase_Get(uint64_t* startedAt)
{
    const uint32_t phase = g_frameWorkPhase.load(std::memory_order_acquire);
    if (startedAt)
        *startedAt = g_frameWorkPhaseStarted.load(std::memory_order_relaxed);
    return phase;
}
#endif

extern "C" const char* sceKernelGetFsSandboxRandomWord();

static void* start_thread(void*)
{
   const uintptr_t base = WaitForBlackOps3();

   if (!base)
        return nullptr;

   const char* rand = sceKernelGetFsSandboxRandomWord();

   char path[256 * 2];
   snprintf(path, sizeof(path), "/%s/common/lib/libSceNotification.sprx", rand);

   bool is_ps5 = false;
   int fd = sceKernelOpen(path, SCE_KERNEL_O_RDONLY, 0);
   constexpr size_t kDriveCount = sizeof(k_driveRoots) / sizeof(k_driveRoots[0]);
#ifdef _DEBUG
   int mountResults[kDriveCount] = {};
#endif

   if (fd >= 0)
   {
       is_ps5 = true;
       sceKernelClose(fd);
   }

   if (!is_ps5)
   {
       for (size_t i = 0; i < kDriveCount; ++i)
       {
           const char* const drive = k_driveRoots[i];
           char mnt[128];
           int len = snprintf(mnt, sizeof(mnt), "/mnt/%s", drive);

           if (len < 0 || static_cast<size_t>(len) >= sizeof(mnt))
               continue;

#ifdef _DEBUG
           mountResults[i] = jbc_mount_in_sandbox(mnt, drive);
#else
           jbc_mount_in_sandbox(mnt, drive);
#endif
       }
   }

    T7Log_Install(base);
#ifdef _DEBUG
    T7Log_Write("[Build] BO3-Customs-v4.00.1-dev.60-DEBUG");
    if (!is_ps5)
    {
        for (size_t i = 0; i < kDriveCount; ++i)
        {
            char root[96];
            snprintf(root, sizeof(root), "/%s/BO3-Customs", k_driveRoots[i]);
            SceKernelStat st{};
            const bool accessible = sceKernelStat(root, &st) == 0 && SCE_KERNEL_S_ISDIR(st.st_mode);
            T7Log_Write("[Storage] /%s <- /mnt/%s: mount result=%d, BO3-Customs=%s",
                        k_driveRoots[i], k_driveRoots[i], mountResults[i], accessible ? "accessible" : "not found");
        }
    }
#endif
    T7Maps_Install(base);
    T7MapImages_Install(base);
    T7Lua_Install(base);
    T7Kbm_Install(base);
    T7Builtins_Install(base);

    if (T7Maps_MapCount() >= 0)
        T7Share_Install(base);

    T7Log_Write("[Maps] %d custom map(s) found", T7Maps_MapCount());

    if (RangeReadable(base + kComFrame, sizeof(k_comFrame)) &&
        memcmp((const void*)(base + kComFrame), k_comFrame, sizeof(k_comFrame)) == 0)
    {
        Detour_Attach(&g_frameDetour, (uint64_t)(base + kComFrame), (void*)Frame_h, &g_frameOriginal);
    }

    if (T7Maps_MapCount() < 0)
        Notify("BO3 Customs Mod loaded!\nCreated by ItsJokerZz. This game build is not supported - it needs version 1.33");
    else
    {
        char buff[256];
        if (T7Maps_ModCount() > 0)
            snprintf(buff, sizeof(buff), "BO3 Customs Mod loaded!\nCreated by ItsJokerZz.\nFound %d custom map(s) and %d mod(s)", T7Maps_MapCount(), T7Maps_ModCount());
        else
            snprintf(buff, sizeof(buff), "BO3 Customs Mod loaded!\nCreated by ItsJokerZz.\nFound %d custom map(s)", T7Maps_MapCount());
        Notify(buff);
    }

    return reinterpret_cast<void*>(1);
}

static std::atomic<bool> g_started{false};

static int Start()
{
    bool expected = false;
    if (!g_started.compare_exchange_strong(expected, true, std::memory_order_acq_rel))
        return 0;

    ScePthread thread{};
    const int created = scePthreadCreate(&thread, nullptr, start_thread, nullptr, "BO3-Customs Init");
    if (created != 0)
    {
        g_started.store(false, std::memory_order_release);
        return created;
    }

    void* result = nullptr;
    const int joined = scePthreadJoin(thread, &result);
    if (joined != 0)
    {
        // The worker's state is unknown after a failed join. Keep the startup
        // latch set so a second entry cannot duplicate partial initialization.
        return joined;
    }

    if (result != reinterpret_cast<void*>(1))
    {
        // BO3 was not ready within the probe window. Permit a later loader
        // callback to retry instead of permanently latching a no-op startup.
        g_started.store(false, std::memory_order_release);
    }

    return 0;
}

extern "C"
{
__declspec(dllexport) const char* g_pluginName = "BO3-Customs";

__declspec(dllexport) int32_t plugin_load(int32_t argc, const char* argv[])
{
    return Start();
}

__declspec(dllexport) int32_t plugin_unload(int32_t argc, const char* argv[])
{
    return 0;
}

int module_start(size_t argc, const void* args)
{
    return Start();
}

int module_stop(size_t argc, const void* args)
{
    return 0;
}
}
