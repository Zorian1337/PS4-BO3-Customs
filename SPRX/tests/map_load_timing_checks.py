"""Guard the map-load diagnostics added to the production hooks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "t7_maps.cpp").read_text()


def function_body(signature):
    start = SOURCE.index(signature)
    opening = SOURCE.index("{", start)
    depth = 0
    for index in range(opening, len(SOURCE)):
        if SOURCE[index] == "{":
            depth += 1
        elif SOURCE[index] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[start:index + 1]
    raise AssertionError(f"unterminated function: {signature}")


def main():
    preflight = function_body("static void TraceMapFastfilePreflight(")
    assert 'traceFile("ff")' in preflight
    assert 'traceFile("fd")' in preflight
    assert '"/app0/zone/%s"' in preflight
    assert "nativeResult" in preflight
    assert "package=%s" in preflight

    file_open = function_body("static uint64_t FileOpen_h(")
    assert "timedMapOpen" in file_open
    assert "call %llu us" in file_open
    assert "fd %d, call %llu us" in file_open

    level_load = function_body("static uint64_t LoadLevelZones_h(")
    assert "nativeStarted = sceKernelGetProcessTime()" in level_load
    assert "native level-zone result for %s: 0x%llX, call %llu us" in level_load

    print("PASS: FF/FD preflight, per-file open timing, and native level-zone timing are present")


if __name__ == "__main__":
    main()
