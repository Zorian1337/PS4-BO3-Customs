from pathlib import Path

source = Path("SPRX/t7_mapimages.cpp").read_text(encoding="utf-8")
assert "static Picture* FindPicture(uint64_t image)" in source
assert "static bool StillOurs(const Picture& picture);" in source
start = source.index("static uint64_t SetImage_h(")
end = source.index("\nstatic bool Matches(", start)
hook = source[start:end]
assert "Picture* const picture = FindPicture(image);" in hook
assert "const uint64_t element = ElementArgument(a1);" in hook
assert "if (!element)\n            return 0;" in hook
assert hook.index("if (!element)") < hook.index("if (!StillOurs(*picture))")
assert "if (!picture)\n            return ((Hook_t)g_setImageOriginal)" in hook
assert "if (!StillOurs(*picture))" in hook
assert "const uint64_t white = ((FindAsset_t)(g_base + kFindAsset))(kImageType, \"$white\", 0, 0);" in hook
assert "if (!StillOurs(*picture))" in hook
assert 'kImageType, "$white", 0, 0' in hook
assert hook.index("StillOurs(*picture)") < hook.index("*(uint64_t*)(element + kElementImage) = image;")
assert "return 0;" in hook
print("custom image retirement and stale element guards passed")
