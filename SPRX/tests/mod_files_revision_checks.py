"""Execute generated ownership updates in a single Lua state across mod changes."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

source = (Path(__file__).resolve().parents[1] / "t7_maps.cpp").read_text()
begin = source.index("const char* T7Maps_ModFilesLua()")
function = source[begin:source.index("bool T7Maps_ModsChanged()", begin)]
fixture = r'''
#include <atomic>
#include <cstdio>
#include <cstring>
#include <string>
namespace T7Maps {
static char g_modFilesLua[65536];
static std::atomic<unsigned> g_modFilesRevision{1};
static const char* files="['old.lua']='old.lua',\n";
static void Append(char* out,size_t,size_t* used,const char* text) {
    std::strcpy(out+*used,text); *used+=std::strlen(text);
}
static void AppendModFiles(char* out,size_t size,size_t* used) { Append(out,size,used,files); }
}
PRODUCTION
int main() {
    std::puts(T7Maps_ModFilesLua());
    std::puts("--CHUNK--");
    T7Maps::files="['new.lua']='new.lua',\n";
    ++T7Maps::g_modFilesRevision;
    std::puts(T7Maps_ModFilesLua());
}
'''.replace("PRODUCTION", function)
with tempfile.TemporaryDirectory(prefix="bo3-mod-files-") as directory:
    cpp, binary = Path(directory) / "check.cpp", Path(directory) / "check"
    cpp.write_text(fixture)
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-Wall", "-Wextra", "-Werror",
                    str(cpp), "-o", str(binary)], check=True)
    first, second = subprocess.check_output([str(binary)], text=True).split("--CHUNK--")
    lua = f'''
local first=assert(loadstring([==[{first}]==]))
local second=assert(loadstring([==[{second}]==]))
first()
assert(BO3CustomsModFiles['old.lua'] and not BO3CustomsModFiles['new.lua'])
local original=BO3CustomsModFiles
first()
assert(BO3CustomsModFiles==original)
second()
assert(not BO3CustomsModFiles['old.lua'] and BO3CustomsModFiles['new.lua'])
assert(BO3CustomsModFilesRevision==2)
local replaced=BO3CustomsModFiles
second()
assert(BO3CustomsModFiles==replaced)
print('PASS: ownership follows mod revisions; unchanged requires reuse the same Lua table')
'''
    subprocess.run([sys.argv[1], "-"], input=lua, text=True, check=True)
