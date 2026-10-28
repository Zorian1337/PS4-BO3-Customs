# BO3-Customs Lua source updates

`ui_scripts/mods.lua` is the editable Mods UI from the supplied
BO3-Customs-lua-base bundle, with the host-session selection correction.
Its matching SPRX publishes `BO3CustomsSessionMods`; the UI shows this list
while joined and restores personal choices after leaving. Selected and loaded
are displayed as distinct states. Choose/Toggle cannot change personal choices
while the host owns the session.

For deployment, this file replaces `/data/BO3-Customs/ui_scripts/mods.lua`.
Retain the existing other six `ui_scripts` files and all39 compiled `lui` files.
The original supplied archive is unchanged. This is a source companion to the
SPRX; it is not embedded in the binary and contains no8-player mod features.

With an older SPRX that does not publish session selection, the UI retains its
existing personal-choice behavior. Runtime validation is still required.

Test using an existing Lua5.1 interpreter:

```
python3 SPRX/tests/session_mod_ui_checks.py Lua/ui_scripts/mods.lua /path/to/lua
```

The test parses the full file and executes the relevant production functions
against a small UI mock. It does not emulate the BO3 UI engine.
