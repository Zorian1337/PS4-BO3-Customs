"""Run every committed SPRX host regression; fail on unregistered new checks."""
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
# Utilities and SDK-specific checks require explicit inputs and are not host tests.
EXPLICIT = {'compare_module_metadata.py', 'openorbis_header_checks.py'}
LUA_ARGUMENTS = {
    'lua_menu_recovery_checks.py': ['{lua}'],
    'lua_menu_reload_checks.py': ['{lua}'],
    'mod_files_revision_checks.py': ['{lua}'],
    'session_mod_ui_checks.py': ['Lua/ui_scripts/mods.lua', '{lua}'],
}
ARGUMENTS = {name: LUA_ARGUMENTS.get(name, []) for name in (
    'bg_cache_snapshot_checks.py config_io_bounds_checks.py diagnostic_hook_checks.py error_capture_checks.py 
    'frontend_reload_checks.py game_log_bridge_checks.py gpu_progress_checks.py '
    'lobby_target_timing_checks.py lua_file_roots_checks.py lua_menu_recovery_checks.py '
    'lua_menu_reload_checks.py lua_ownership_index_checks.py lua_zone_lifetime_checks.py '
    'map_fastfile_route_checks.py map_image_surface_checks.py missing_import_lifetime_checks.py '
    'mod_files_revision_checks.py mod_lua_retention_checks.py mod_stack_transaction_checks.py '
    'pool_growth_checks.py script_priority_context_checks.py session_common_activation_checks.py '
    'session_mod_publish_checks.py session_mod_ready_checks.py session_mod_ui_checks.py '
    'share_install_checks.py storage_safety_checks.py texture_readiness_checks.py ui_startup_unload_checks.py'
).split()}


def main():
    tests = ROOT / "SPRX/tests"
    scripts = {p.name for p in tests.glob("*.py")}
    if scripts != set(ARGUMENTS) | EXPLICIT:
        raise SystemExit(f"Update CI test inventory: new={scripts - set(ARGUMENTS) - EXPLICIT}, missing={set(ARGUMENTS) - scripts}")
    if '--list' in sys.argv:
        print('\n'.join(ARGUMENTS)); print('Explicit input checks: ' + ', '.join(sorted(EXPLICIT))); return 0
    lua = os.environ.get('BO3_LUA_RUNNER') or shutil.which('lua5.1') or shutil.which('luajit') or shutil.which('lua')
    if not lua:
        raise SystemExit('Set BO3_LUA_RUNNER to an existing Lua 5.1-compatible executable')
    os.environ['BO3_LUA_RUNNER'] = lua
    failures = []
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for name, arguments in ARGUMENTS.items():
        print(f"::group::{name}", flush=True)
        result = subprocess.run([sys.executable, str(tests / name), *[v.replace("{lua}", lua) for v in arguments]],
                                cwd=ROOT, env=environment, timeout=180)
        if result.returncode:
            failures.append(name)
        print("::endgroup::", flush=True)
    cpp = sorted(tests.glob("*_tests.cpp"))
    with tempfile.TemporaryDirectory(prefix="bo3-host-") as directory:
        for source in cpp:
            binary = Path(directory) / source.stem
            print(f"::group::{source.name}", flush=True)
            build = subprocess.run(["g++", "-std=c++20", "-Wall", "-Wextra", "-Werror",
                                    "-O1", "-pthread", str(source), "-o", str(binary)], timeout=120)
            if build.returncode or subprocess.run([str(binary)], timeout=120).returncode:
                failures.append(source.name)
            print("::endgroup::", flush=True)
    print(f"{len(ARGUMENTS) + len(cpp)} regression programs; failures: {failures}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
