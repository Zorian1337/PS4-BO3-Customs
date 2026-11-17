#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <string>

#include <kernel.h>
#include <sys/mman.h>

#include "HDE64.h"
#include "Detour.hpp"
#include "libjbc.h"

#include "platform.hpp"
#include "t7_maps.hpp"
#include "t7_mapimages.hpp"
#include "t7_lua.hpp"
#include "t7_kbm.hpp"
#include "t7_log.hpp"
#include "t7_share.hpp"
#include "t7_builtins.hpp"

#ifdef _DEBUG
void T7FrameWorkPhase_Set(uint32_t phase);
uint32_t T7FrameWorkPhase_Get(uint64_t* startedAt);
#endif
