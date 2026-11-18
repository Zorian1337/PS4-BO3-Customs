from pathlib import Path

source = Path("SPRX/t7_maps.cpp").read_text(encoding="utf-8")
header = Path("SPRX/stream_guard.hpp").read_text(encoding="utf-8")

assert '#include "stream_guard.hpp"' in source
start = source.index("static uint64_t BlockJob_h(")
end = source.index("\nstatic bool CodeImageSet", start)
hook = source[start:end]
assert "StreamGuard::Evaluate(ring, data, unpacked, hashed, stored)" in hook
assert "StreamGuard::TryClaimDiagnostic(g_streamRejectDiagnosticCount)" in hook
assert 'event=stream-block-rejected reason=%s ring=%llX slot=%llX data=%llX unpacked=%u hashed=%u stored=%u' in hook
assert hook.index("T7Log_Write") < hook.index("*(uint32_t*)(slot + 0x4002C) = 0;")
assert "g_blockOriginal" in hook and "return ((Hook_t)g_blockOriginal)" in hook
assert "compare_exchange_weak" in header and "current < 16" in header
print("stream guard hook integration checks passed")
