<p align="center"><img src="Tool/logo.png" width="96" alt="BO3-Customs"></p>

# BO3-Customs

A PC converter for custom *Call of Duty: Black Ops III* maps and mods, with an experimental console SPRX loader for supported HEN environments.

> **Release vs. development:** Install console packages only from [GitHub Releases](https://github.com/Zorian1337/PS4-BO3-Customs/releases). The latest `main` branch contains experimental SPRX/Lua source; passing host checks does **not** establish PS4/PS5 runtime stability. For current status, see [RESUME.md](RESUME.md) and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Requirements

- A supported HEN console with **BO3 version 1.33** (any region).
- BO3 installed on PC, plus the custom maps or mods you intend to convert.
- The converter, `Console.zip`, and a matching SPRX from an approved [release](https://github.com/Zorian1337/PS4-BO3-Customs/releases).

## Quick start

1. Extract `Console.zip` and copy its console contents to `/data/`.
2. Put the matching SPRX in `/data/BO3-Customs/` (or another location supported by your loader).
3. Open the PC converter; add a BO3 map or mod and select **Convert**.
4. Copy converted maps to `/data/BO3-Customs/usermaps/<map>/` and mods to `/data/BO3-Customs/mods/<mod>/`.
5. Start BO3, load the SPRX using your console's supported method, and choose the content in-game.

External or USB storage can use `BO3-Customs/usermaps/` and `BO3-Customs/mods/` at the drive root. Console settings, logs and saves stay under `/data/BO3-Customs/`.

## SPRX features

The experimental SPRX provides the following console features. Availability
also depends on the game build, loader, installed companion Lua and converted
content; this table describes implemented support, not a promise that every
third-party map or mod works.

| Feature | Implemented behavior | Validation and limits |
| --- | --- | --- |
| Maps and storage | Discovers converted usermaps on internal, USB and extended storage; routes fastfiles, XPAKs, sounds and preview images | Content must be converted for the target; discovery does not prove playability |
| Map selection | Standard/Customs categories, canonical installed-map routing, alias/duplicate filtering, refresh, preview details and uninstall prompts | Ambiguous map identities are not guessed; provider menus may differ |
| Mods | Selects mod stacks, applies zone changes through frontend reloads and tracks mod asset ownership | Mods can conflict with each other or require unsupported PC functions |
| Lua compatibility | Loads companion scripts with internal-first lookup; provides selected missing PC helpers and footer components; preserves provider callbacks | Partial compatibility layer, not a PC runtime; external DLL features may remain unavailable |
| UI lifetime and recovery | Retains borrowed mod bytecode within bounded arenas, validates source ranges and pauses additional injection after a frontend error | Invalid data is rejected; some failures require fully restarting BO3 |
| Input | Keyboard/mouse bindings, mouse settings and menu pointer/touchpad integration | Hardware, menu-provider and gameplay behavior require console testing |
| Local preferences | Persists configuration and separates map/mod saves under `/data/BO3-Customs/` | A third-party script can still use its own incompatible save format |
| LAN sharing | Missing-content checks, transfer prompts/progress, lobby map status and supported player-menu actions | Depends on compatible peers, host state and network reachability; not public matchmaking support |
| Engine compatibility | Targeted asset, script, zone, image/streaming, frontend, frame-limit and split-screen adaptations | Signature/version dependent; no guarantee against kernel panics or GPU hangs |
| Debug diagnostics | UI/LobbyVM and GSC/CSC errors, asset fallbacks, transition/ownership details, stall/GPU progress and persistent error capture | Debug candidates only for some features; reporting an error does not repair its cause |
| Diagnostic tools | Read-only log collection and localized UI-error recognition, including `ERRUR IU` | Original error text and stacks are preserved for investigation |

### Compatibility and known limits

Host regression checks exercise argument forwarding, ownership, storage bounds,
menu recovery and Lua compatibility with mocks. The native build checks the
SPRX container and loader metadata. Neither verifies gameplay on a console.
See [the current handoff](RESUME.md) and [investigation notes](docs/INVESTIGATION-2026-11-02-LOBBY-UI.md)
for evidence and remaining checks.

The dev.58 capture requesting **`zm_waffle_tower`** fails during UI module
validation before it demonstrates a successful map load. It also contains
separate DS4C frontend-camera script errors. The exact-range validator is now
corrected to accept readable chunks spanning more than eight adjacent memory
regions, while continuing to reject holes and unreadable memory. This is a
generic loader correction; Waffle Tower gameplay and the DS4C camera behavior
still require a new console run. Do not treat this map as console-verified yet.

### Converter tabs

| Tab | Purpose |
| --- | --- |
| **Convert** | Add installed or downloaded PC maps/mods and convert them |
| **Converted** | Review content ready to transfer |
| **Community** | Browse available converted content |
| **Installed** | Review or remove installed content |
| **Settings** | Configure FTP, destinations and updates |

### Send by FTP

In **Settings**, enter the console's IP address and select **Test**. The default port is **2121**, or specify a different one (for example, `192.168.1.50:21`). **Console files** can transfer the approved console bundle and SPRX; **Send to console** transfers selected content. **Auto-FTP** transfers items after conversion/download. Choose internal, USB or extended storage as the destination.

## Multiplayer and saved content

For System Link games and compatible tunnels, participating consoles need the SPRX. Missing map/mod transfers and prompts depend on the same compatible content and host session state. Successful download alone does not guarantee that a mod was activated successfully.

Mod and map saves are kept separately under `/data/BO3-Customs/saves/<mod-or-map>/`. Uninstalling content does not require deleting those saves.

## Recover from a broken mod

Fully close BO3 and reopen it. On a fresh process, locally selected mods are not automatically activated from `active_mod.txt`. Leave the failing mod deselected. If necessary, close BO3 before deleting **only** that mod's installed folder; do not delete your game saves.

Returning to the main menu is **not** a full process restart: custom code or assets can remain loaded. Host-selected content may be activated again when joining a lobby. The in-game menu has limited recovery support, but it cannot recover every native crash or GPU hang.

## Troubleshooting and diagnostics

- Open an [issue](https://github.com/Zorian1337/PS4-BO3-Customs/issues) describing the console model, BO3 version, exact SPRX build, map, mod stack, storage destination and reproducible steps.
- Preserve `/data/BO3-Customs/log.txt` **before restarting BO3**, because each process start replaces the normal session log.
- Supported DEBUG candidates can also write `/data/BO3-Customs/crash-errors.log`, which persists across process restarts. Never publish private console identifiers or unrelated captures.
- For black-screen or GPU-stall reports, include surrounding `[GPU]`, `[Stream]`, `[Blobs]` and `[Stall]` lines. Current source distinguishes GPU job submission from completion and separates loading lighting blobs from resident ones; neither is a standalone proof of a GPU defect.
- If possible, compare the **same converted map** with mods disabled on internal and external storage. Save the converter's analysis log using **Log → Save**.

See [console diagnostics](tools/console_diagnostics/README.md) for read-only log collection and [development status](docs/DEVELOPMENT.md) for limitations and console validation.

## Development

Start with [RESUME.md](RESUME.md), [AGENTS.md](AGENTS.md) and [docs/WORKFLOW.md](docs/WORKFLOW.md). The source includes the SPRX, companion Lua, the converter, and host regression checks.

On Windows, `RESUME_WORK.cmd` prints a compact status summary and `CHECK_SOURCE.cmd` runs source checks using the configured environment. These commands do **not** create an SPRX release. Native builds require a compatible toolchain and explicit approval for this project's development workflow; see the [build workflow](docs/WORKFLOW.md).

Pushing to this repository's `main` also runs **BO3 Auto Build** in GitHub
Actions. It compiles the PS4 SPRX and stores a run-specific artifact; it does
not publish a release. Published GitHub releases can be
announced to Discord using the `DISCORD_WEBHOOK_URL` Actions secret. Setup and
behavior are documented in [the build guide](.github/BO3_AUTOBUILD.md).

The converter can be published separately using the project's documented .NET toolchain:

```powershell
cd Tool/Porter
dotnet publish src/FFPorter.Desktop.T7/FFPorter.Desktop.T7.csproj -p:PublishProfile=FolderProfile
```

The published executable is placed under `Tool/Porter/publish/`.

## Credits and license

Originally developed by **ItsJokerZz**, with contributions from project maintainers and community contributors. **flatz** provided `downgrade_elf.py` and `make_fself.py`.

Licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE).
