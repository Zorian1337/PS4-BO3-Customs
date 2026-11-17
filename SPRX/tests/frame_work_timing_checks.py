#!/usr/bin/env python3
"""Guard detailed stall attribution for lobby completion and catalog refresh."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
share = (root / "t7_share.cpp").read_text(encoding="utf-8")
maps = (root / "t7_maps.cpp").read_text(encoding="utf-8")

assert "T7FrameWorkPhase_Set(21);" in share
assert "T7FrameWorkPhase_Set(22);" in share
assert "T7FrameWorkPhase_Set(23);" in share
assert share.index("T7FrameWorkPhase_Set(23);") < share.index("const bool refreshed = T7Maps_Refresh();")
refresh_at = share.index("const bool refreshed = T7Maps_Refresh();")
assert refresh_at < share.index("T7FrameWorkPhase_Set(22);", refresh_at)
assert 'phase == 20 ? "share/Evaluate"' in maps
assert 'phase == 21 ? "share/hosted snapshot"' in maps
assert 'phase == 22 ? "share/Finish"' in maps
assert 'phase == 23 ? "share/map catalog refresh"' in maps

print("PASS: watchdog can distinguish lobby evaluation, completion and full catalog refresh")
