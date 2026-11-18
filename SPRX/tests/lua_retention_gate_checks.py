from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parent
source=root/'lua_retention_gate_tests.cpp'
with tempfile.TemporaryDirectory(prefix='lua-gate-',dir=root.parent/'build') as tmp:
    for sanitizer in ('address,undefined','thread'):
        exe=Path(tmp)/('gate-'+sanitizer.replace(',','-'))
        subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-Wall','-Wextra','-Werror','-O1','-pthread',
                        f'-fsanitize={sanitizer}','-I',str(root),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True,timeout=60)
print('PASS: Lua retention gate close/entry race, unreadable-pointer rejection, drain and concurrent readers (ASan/UBSan + TSan)')
