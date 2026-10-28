# BO3-Customs Lua source updates

`ui_scripts/mods.lua` is the editable Mods UI from the supplied
BO3-Customs-lua-base bundle, with the host-session selection correction.
Its matching SPRX publishes `BO3CustomsSessionMods`; the UI shows this list
while joined and restores personal choices after leaving. Selected and loaded
are displayed as distinct states. Choose/Toggle cannot change personal choices
while the host owns the session.

For deployment, the editable files replace their counterparts inside
`/data/BO3-Customs/ui_scripts/` or an optional Lua root supported by the new source.
Retain the other five `ui_scripts` files and all 39 compiled `lui` files.
The original supplied archive is unchanged. This is a source companion to the
SPRX; it is not embedded in the binary and contains no 8-player mod features.

With an older SPRX that does not publish session selection, the UI retains its
existing personal-choice behavior. Runtime validation is still required.

Test using an existing Lua 5.1 interpreter:

```
python3 SPRX/tests/session_mod_ui_checks.py Lua/ui_scripts/mods.lua /path/to/lua
```

The test parses the full file and executes the relevant production functions
against a small UI mock. It does not emulate the BO3 UI engine.

## Pending source changes after dev.25

`ui_scripts/mapselect.lua` is now kept here as editable source, copied from the
supplied companion bundle. Its recovery path runs only when an offline Zombies
map-list builder fails. It supplies stock row fields with the original map IDs,
excludes maps the engine considers invalid, and keeps a working mod's list
untouched. The row contract follows the public T7LuaRepo PC ship
[`ZMMapsList` source](https://github.com/KingslayerKyle/T7LuaRepo/blob/main/Dumps/PC_Ship_2025-05-31/ui/uieditor/datasources.lua).
It does not modify a mod's CSC scripts or guarantee that its camera/camo code is
compatible with PS4.

`mods.lua` routes load/unload through the console loader when its Mods menu is
active. Outside that menu an existing handler retains control. Turning mods off
queues native deselection before refreshing possibly broken mod widgets, and
cannot clear personal selections while a host owns the session. Physical zone
unloading still follows the existing safe apply/menu-close process.

Run the focused Lua regression with an existing Lua 5.1 executable:

```
python3 SPRX/tests/lua_menu_recovery_checks.py /path/to/lua
```

These are source changes awaiting a separately approved build and console test.
They are not included in the already published dev.25 binary or Console.zip.

## Optional Lua locations

The new SPRX source reads both `lui/` and `ui_scripts/` from the same ordered
root list. Without configuration, `/data/BO3-Customs` has priority, followed by
`/ext0/BO3-Customs` through `/ext7/BO3-Customs`, then `/usb0/BO3-Customs` through
`/usb7/BO3-Customs`. These are the console-visible mount paths, not Windows drive
letters. Connect the drive before starting BO3 so the loader can mount it.

To prefer another readable location, create the optional internal file
`/data/BO3-Customs/lua_roots.txt`. Each line is an absolute root containing
`lui/` and/or `ui_scripts/`. For example:

```
/usb0/BO3-Customs
/ext0/MyCustoms
```

Configured roots are tried first, in order. The normal internal root and default
external roots remain fallbacks. A file that is absent, unreadable, empty,
oversized, or incompletely read is skipped. Text scripts cannot contain embedded
NUL bytes; compiled LUI remains binary. This checks file reads, not Lua semantics:
a complete but incompatible script can still fail in the game.

The configuration accepts up to 16 roots, each under 192 bytes, in a file up to
4096 bytes. Blank lines and `#` comments are allowed; relative/traversal paths
are rejected. The configured root must already be readable inside the game
sandbox; this feature does not grant access to unmounted devices or arbitrary
system directories. Keep a matching full bundle internally for recovery.
Restart BO3 fully after changing roots or replacing cached compiled Lua files.
Successful external reads log the actual root. Saves, logs, configuration writes,
and installed mod assets retain their existing storage behavior.

## What changed for dev.22

Only `ui_scripts/mods.lua` changed in the supplied 46-file bundle. The other
six editable scripts and 39 compiled chunks are byte-identical to the original
archive. The complete companion ZIP is available locally at
`build/lua-dev22/BO3-Customs-lua-dev.22.zip` (163,601 bytes).

The new Mods UI reads the SPRX's host-session list instead of showing only the
client's personal tick list. It shows whether those host mods are selected or
loaded, protects personal choices from Choose/Toggle while joined, and restores
their display after leaving. It falls back to the previous behavior when used
with an older SPRX that does not publish the new global.

This display correction does not load fastfiles. The dev.22 SPRX itself queues
mod activation and holds launch until the ordered stack and required zones are
ready. Neither layer bypasses Client/Server Index Mismatch or clientfield checks.

## The seven editable scripts

Paths below are relative to `/data/BO3-Customs/ui_scripts/`. Behaviors in this
table were checked against the supplied source.

| File | What it does | Connection to the SPRX |
| --- | --- | --- |
| `mods.lua` | Builds the Mods entry, multi-mod selection/checkmarks, loading status and details panel; refreshes list state and requests Apply when the Mods menu closes. Dev.22 adds the host-session selection display described above. | Reads `BO3CustomMods`, chosen/active/session lists published by native code. Writes `bo3customs_mod`, `bo3customs_mods_apply` and refresh requests. Native code handles selection, zone loading and saved choices. |
| `mapselect.lua` | Adds custom map entries and category tabs, wraps map lists/menus, displays map descriptions and scrolling titles, adds uninstall confirmation and map-availability indicators, and retries UI hooks as widgets become available. | Uses native map/file/lobby data; requests uninstall through `bo3customs_uninstall` and refresh through `bo3customs_refresh`. It does not transfer map files itself. Its `BO3CustomsTick` wrapper maintains UI hooks and forwards queued diagnostics. |
| `maptable.lua` | Adds custom-map metadata to the table passed into the script. Copies a compatible stock Zombies/MP template, then assigns name, description, preview/loading image, movie and custom-map marker. | Consumes `BO3CustomMaps` published by the SPRX. It only inserts when `maps[map.id]` is absent; this Lua file alone cannot distinguish two different packages sharing the same internal map ID. |
| `graphics.lua` | Adds graphics options, including FOV, FPS limit/display, VSync, mesh/shadows, SSS, volumetric lighting, AA, ambient occlusion, motion blur and split-screen orientation. Adapts graphics menus/widgets and reset behavior for the console UI. | Changes the selected dvars and sends the changed settings through `bo3customs_graphics_save` for native persistence. It also redirects the graphics popup to the PC-style menu used by the compatibility layer. |
| `mouse.lua` | Draws a software cursor, connects mouse click/hover/navigation to UI buttons, adapts key prompts/localization, supplies missing PC-style profile/cursor functions, and adapts input/binding/reset menus. | Sends binding capture/reset and profile settings through native-handled dvars such as `bo3customs_kbm_capture`, `bo3customs_kbm_reset` and `bo3customs_mouse_invert`. Some UI calls temporarily set `CoD.isPC`; that is a compatibility wrapper, not a change of game platform. |
| `kbm_strings.lua` | Defines the `BO3CustomsStrings` text dictionary used by the keyboard/mouse compatibility layer. | Provides UI labels/localization replacements used by the Lua/native compatibility hooks. It contains text data, not spawning, scoreboard or lobby-limit logic. |
| `restart.lua` | Adds the stock Restart Level action to Zombies pause options for the game host, excluding demo playback; avoids adding a duplicate. | Wraps `ListHelper_Prepare` and calls the game's existing `RestartGame` action. It does not implement a replacement map-reset/spawn system. |

These scripts are loaded by native Lua injection at the appropriate UI/probe
points. For example, `T7Lua_Work` reads graphics/restart/mouse/mods scripts when
their pending flags are set and publishes mod data when it becomes dirty.
Their global guards prevent duplicate installation within the same Lua state.
`maptable.lua` expects the current map table as its vararg input rather than a
standalone menu invocation.

## The 39 compiled `lui` chunks

These files use the BO3 LuaQ bytecode header despite ending in `.lua`. They
remain unchanged. Their roles below follow their module names and the visible
require/API strings; they are an inventory of compatibility components, not a
claim that every compiled instruction has been decompiled or engine-tested.
Paths in this table are relative to `/data/BO3-Customs/lui/`.

| File | Role |
| --- | --- |
| `lua/lobby/lobbysteam.lua` | PC Steam lobby/session callbacks, including map/mode/client-count events, used within the compatibility environment. |
| `ui/t6/menus/keyboardtextfield.lua` | Keyboard text-entry component. |
| `ui/t7/utility/modsutility.lua` | Stock Mods utility/refresh/unload-overlay API. The inspected bytecode strings include mod-list refresh and unload actions. |
| `ui/t7/utility/pcutility.lua` | PC UI utility dependencies used by ported menus. |
| `ui/t7/utility/starterpackutility.lua` | Starter-pack UI compatibility utility. |
| `ui/uieditor/menus/core_patch_pc_require.lua` | PC UI require/dependency entry chunk. |
| `ui/uieditor/menus/lobby/common/lobbyserverbrowseronline.lua` | Server-browser menu. |
| `ui/uieditor/menus/mods/menumodsload.lua` | Stock Mods menu constructor, list, details, prompts and close cleanup. Editable `mods.lua` adapts this menu. |
| `ui/uieditor/menus/pc/keyboardinputoverlay.lua` | Keyboard input popup. |
| `ui/uieditor/menus/pc/serverbrowserfilters.lua` | Server-browser filter menu. |
| `ui/uieditor/menus/pc/serversettings.lua` | Server settings menu. |
| `ui/uieditor/widgets/charactercustomization/tauntbindswidget.lua` | Taunt binding UI. |
| `ui/uieditor/widgets/charactercustomization/tauntwidget.lua` | Taunt selection/display UI. |
| `ui/uieditor/widgets/horizontalscrollingtextbox_14pt.lua` | Horizontally scrolling text widget. |
| `ui/uieditor/widgets/hud/console/console.lua` | Console UI root. |
| `ui/uieditor/widgets/hud/console/consoleentry.lua` | Console output entry. |
| `ui/uieditor/widgets/hud/console/consoleentrycontainer.lua` | Console entry container. |
| `ui/uieditor/widgets/hud/console/consoleicon.lua` | Console icon widget. |
| `ui/uieditor/widgets/hud/console/consoletext.lua` | Console text widget. |
| `ui/uieditor/widgets/lobby/common/splitscreenlobbybuttonpc.lua` | PC-style split-screen lobby button. |
| `ui/uieditor/widgets/lobby/lists/lobbymembermp45.lua` | Lobby-member row widget. Its name does not establish an eight-player gameplay limit. |
| `ui/uieditor/widgets/mods/entrymodsload.lua` | One Mods list row. |
| `ui/uieditor/widgets/mods/widgetmodsload.lua` | Mods list/container widget. |
| `ui/uieditor/widgets/pc/choosecharacter/choosecharacter_cardclickbutton.lua` | Mouse-clickable character-selection card. |
| `ui/uieditor/widgets/pc/craft/craftemblemeditmouseinstructions.lua` | Mouse instructions for emblem editing. |
| `ui/uieditor/widgets/pc/craft/craftsideselectorbutton.lua` | Craft/editor side selector. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserbutton.lua` | Server-browser button/control component. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowsercheckbox.lua` | Server-browser checkbox. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserdetails.lua` | Selected-server details panel. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserflag.lua` | Server-browser flag/status widget. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserheader.lua` | Server-list header. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserheadericoncolumn.lua` | Server-list icon-column header. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserheadernamedcolumn.lua` | Server-list named-column header. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserplayerrow.lua` | Selected-server player row. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserrow.lua` | Server-list row. |
| `ui/uieditor/widgets/pc/serverbrowser/serverbrowserrowinternal.lua` | Internal server-list row content. |
| `ui/uieditor/widgets/pc/utility/inputtextfield.lua` | Input text-field component. |
| `ui/uieditor/widgets/pc/utility/starterpackwatermark.lua` | Starter-pack watermark widget. |
| `ui/uieditor/widgets/pc/utility/textinputwidget.lua` | Text-input container widget. |

## Logging and troubleshooting

The editable map/Mods UI queues bounded messages in
`BO3CustomsMapTabs.logs`. Native Debug code drains them into the BO3-Customs
log. `mapselect.lua` also has a fallback that raises a synthesized `[MapSelect]`
message from its tick wrapper when it has not observed the normal bridge drain.
Inspect the message body before classifying one of those records as a gameplay
exception. An arbitrary numbered UI error still requires its own call context.

For joining, distinguish these stages in the native log:

1. Files downloaded and discovered.
2. Host mods selected in order.
3. Required core/mode zones loaded and ready.
4. Client admitted to gameplay with matching native asset/script state.

The dev.22 Lua change makes stage 2 visible accurately; the SPRX activation gate
checks stage 3. A successful download or a ticked UI row does not establish
stage 4. The supplied failed join reports `EXE_ERR_BG_CACHE` (Client/Server Index
Mismatch), which differs from `EXE_CLIENT_FIELD_MISMATCH`.

This bundle contains no custom 18-player scoreboard, revive implementation,
GobbleGum replacement, or spawn queue. Those remain in the separate mod project.

## Installing the current change

The dev.22 SPRX has already been uploaded separately. The Lua ZIP has not been
installed on the console. To apply only this reviewed Lua change, replace
`/data/BO3-Customs/ui_scripts/mods.lua` with the tracked file from this folder,
then fully restart BO3 so its existing global installation guard is recreated.
The complete ZIP includes `lui/` and `ui_scripts/` at its root for a full bundle
installation, but the other 45 files do not need replacement for this change.
Retain any newer console-side changes to those other files.
