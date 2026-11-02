# 2026-11-02 lobby UI nil-index error

Current source: dev.58. The later bytecode-confirmed correction supersedes the
earlier LobbyMember hypothesis below. The user subsequently authorized a dev.58
Debug build including the additional review fixes. Build and artifact validation
passed; console validation remains pending. Earlier no-build notes describe the
authorization state at that stage of the investigation.


## Evidence

The debug session log reports UI errors 24858 and 13963 at 01:52 and 01:59.
Both report `3778239045:252: attempt to index a nil value`. The first stack
includes `bo3customs_lobby:167` in a function named `new`; the second reports
the same failing function. The error occurs in the frontend after
`reaper_collection` is loaded and a remote LAN lobby member is visible. The
SPRX reports the UI exception and pauses additional compatibility injection
for that frontend generation; that pause is recovery behavior, not the original
exception.

The `bo3customs_lobby:167` frame maps to the generic PC-widget constructor
wrapper in `k_lobbyParityLua`: it calls the widget's original `new(...)` at
line 167, before applying its post-construction compatibility repairs. The
player-list scenario narrows the likely widget to `CoD.LobbyMember`, which is
in `pcChildren` and whose expected child `LobbyMemberMP45` is absent on some
PS4 UI states.

The public PC Lua dump shows `CoD.LobbyMember.new` constructing
`CoD.LobbyMemberMP45.new(menu, controller)` during the parent constructor, then
linking and animating that child. The current shim only adds a stand-in child
after the parent constructor returns. Therefore the repair arrives too late if
the PC-only child class itself is missing. This is a source-supported root
cause candidate, not a byte-for-byte proof for the PS4 Lua build.

Reference source: [PC `LobbyMember.lua`](https://github.com/KingslayerKyle/T7LuaRepo/blob/main/Dumps/PC_Ship_2025-05-31/ui/uieditor/widgets/Lobby/Lists/Members/LobbyMember.lua)
and [PC `LobbyMemberMP45.lua`](https://github.com/KingslayerKyle/T7LuaRepo/blob/main/Dumps/PC_Ship_2025-05-31/ui/uieditor/widgets/Lobby/Lists/Members/LobbyMemberMP45.lua).

## Correction

Before wrapping/constructing `CoD.LobbyMember`, the compatibility layer now
provides a minimal `CoD.LobbyMemberMP45` class only when that class is absent.
Its constructor returns a base `LUI.UIElement`, which satisfies the parent's
`setAlpha`, model-link, and layout calls without replacing any class supplied by
the game or a mod. The existing child stand-in remains as a later safeguard.

This is a generic missing-PC-widget fallback keyed by the parent/child
relationship. It does not branch on the Reaper mod name and leaves an existing
`CoD.LobbyMemberMP45` implementation untouched. The starter-pack badge itself
is omitted when the fallback is used.

## Validation limits

The focused source-order regression passes. The Debug build completed all 14
native translation units and the target artifact checks. The artifact is not
console-validated. A PS4 run with the rebuilt SPRX is still required to verify
that these UI errors are gone and that player-list behavior remains stable.
The newly attached log identifies dev.53 built at 10:37 and therefore predates
the fallback build; it is a baseline capture, not evidence that the fallback
failed. The error is distinct from the earlier GobbleGum `string .. nil`
exception.

## dev.55 console capture

The next capture identifies dev.55 Debug and repeats the same
`3778239045:252: attempt to index a nil value` exception. This confirms the
`LobbyMemberMP45` fallback was insufficient; it does not establish that the
fallback itself caused a new error. The stack's `bo3customs_lobby:189` maps to
the generic widget wrapper's `make(...)` call. One reproduction occurs after a
remote lobby member is present; another stack includes `mapselect.lua` while
the map menu is being constructed. The wrapper covers multiple PC widgets, so
the log does not identify which original constructor failed.

Do not extend placeholder classes based only on the current stack. First add
diagnostic context that records the wrapped CoD widget name when its original
constructor throws, then use a resulting capture to target a fail-closed,
missing-only compatibility correction. No new SPRX should be built until that
source-level fix is established.

## Bytecode-confirmed correction

Offline parsing of all 73 mod Lua chunks identifies a matching wrapped constructor: `fe_FooterContainer_NOTLobby`. Its function hash is 3778239045; instruction 249 fetches `CoD.StarterPackWatermark`, and instruction 252 fetches `new` from that value. The log separately confirms the StarterPackWatermark module is unavailable on PS4. This directly explains the nil index before post-construction repair. Both footer classes now receive the missing watermark class before construction, only if absent. This fixes the shared footer dependency across menu entry points. The speculative LobbyMemberMP45 class fallback is removed. Constructor failures also retain widget names and tracebacks for future unrelated errors. Console validation of dev.56 remains required.

## Follow-up review

Decompiling the matching footer confirms its watermark use is limited to base-element layout, attachment, and close operations; the fallback provides those operations. A separate description-rebuild path allocated a replacement and immediately indexed `box.textBox`; an incomplete provider widget could throw inside the protected repair and leave the replacement unclosed. The repair now handles a nil constructor result and closes an incomplete replacement before returning, leaving the original description in place. Native diagnostic forwarding, Lua root priority/I/O bounds, and borrowed-bytecode lifetime checks passed under WSL. Lua runtime regressions could not run because no compatible interpreter is installed. dev.57 adds this defensive correction; it is not evidence that all third-party UI faults are eliminated.

## Further review: source changes after dev.57, no build authorized

Additional defects corrected in source:

- LuaUtils compatibility initialization used one boolean for the whole UI state. A provider replacing the LuaUtils table was skipped permanently. Track initialization by table identity with weak keys, and preserve inherited provider functions.
- LUI method probing was marked complete before a successful probe and keyed only by class name. Retry unsuccessful probes and reapply when the class table changes.
- Successful temporary method-probe widgets were never closed. Close the probe after copying its independent method functions.
- Missing watermark detection ignored inherited CoD classes and could shadow a provider class exposed through a metatable. Respect normal class lookup before creating a fallback.
- CreateWithRefresh unconditionally restored AddButtonCallbackFunction after constructing a menu, overwriting a provider replacement made during construction. Restore only if our temporary wrapper still owns the slot.

Added executable regression scenarios to the existing compatibility fixture covering table replacement, inherited provider functions/classes, failed-probe retry, successful-probe cleanup and LUI class replacement. These Lua execution scenarios have not run locally: no compatible Lua interpreter is installed. The focused source-order check and git diff whitespace check pass. No SPRX build, version bump, ZIP or console upload was performed for these changes.

## PR verification

The GitHub diagnostics workflow ran the actual compatibility fixture with Lua
5.1, including replacement tables/classes, inherited implementations, probe
retry/cleanup and platform-scope restoration. These scenarios and companion
menu recovery checks passed, together with the native diagnostics checks and
script-log workflow. [Verified CI run](https://github.com/Zorian1337/PS4-BO3-Customs/actions/runs/41482881872).
This resolves the earlier local-interpreter validation gap; console behavior
remains a separate pending check.
