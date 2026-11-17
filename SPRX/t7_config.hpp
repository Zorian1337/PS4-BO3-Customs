#pragma once

#include <cstddef>

bool T7Config_Read(char* out, size_t size);

bool T7Config_Save(const char* section, bool (*owns)(const char* line), const char* lines);

// Queue an immutable snapshot for background persistence; false means retry later.
bool T7Config_SaveAsync(const char* section, bool (*owns)(const char* line), const char* lines);
