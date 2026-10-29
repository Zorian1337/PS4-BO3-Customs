# Frontend and map-start crash review — 2026-10-29

This is a sanitized summary of the supplied local captures. The original logs
remain private and are not part of this repository. Findings below distinguish
observed errors from possible causes; no console crash is claimed fixed here.

## Findings

### Frontend menu refresh

One capture reports a LUI nil-index error in the stock clientfield-model path,
with the BO3-Customs `AddButtonsForTarget` wrapper in the call stack. The wrapper
previously called the captured stock `LobbyMenus.AddButtonsForTarget` function
without protection. A stock callback exception could therefore escape through
our wrapper and abort that target's UI refresh. This is a demonstrated unsafe
boundary and a plausible contributor to menu errors during mode transitions.
It does not prove that the Mods menu itself was being added to Zombies, nor that
it caused a native game crash.

The wrapper now protects only the stock callback. On success it passes through
the exact returned button table and keeps existing hide/add behavior. On an
exception it logs once for that target and returns a new empty list; it never
reuses another target's buttons or inserts the Mods button into a failed target.
This preserves the existing main-menu target gate and avoids stale menu state.

### Camo selection

The submitted captures do not contain a reliable crash signature tied to the
camo action: there is no matching native crash trace or clear faulting call. A
camo-related command appears in the session, but nearby later errors are not
proof of causation. The observed customization-pool counters are not shown to be
exhausted in the relevant sequence. No pool sizes or camo behavior were changed.

Next evidence needed: a fresh error log beginning before opening the camo option,
the exact option and weapon selected, the first UI/GSC/CSC error, and the native
crash tail if the process exits. Compare the same action with the plugin disabled
and with only the plugin enabled. If the failure is a Lua callback, contain the
specific callback and preserve the stock result; if a pool allocation fails,
verify the failing pool and allocator bounds before changing capacity; if the
engine crashes in a native path, use a matching build's call stack rather than
guessing from the last log line.

### Custom-map startup and delayed loading

The supplied custom-map startup capture continues to emit frames after a long
texture-loading interval. It does not contain a definitive process-crash marker.
The log also includes control-state changes and script/asset warnings. These
could reflect expensive streaming, map-owned script work, frontend state, or an
incomplete capture; they do not establish which component caused the reported
crash. The sampled image/customization pool values do not prove exhaustion.

Next evidence needed: one isolated startup with the exact plugin and mod stack
recorded, plus the persistent error log and the final kernel crash context. Keep
frame, stream, GPU, and pool counters together. Compare plugin-off and plugin-on
runs on the same map. Only change a pool after a matching allocation failure;
only change a GPU wait after proving the relevant submission/completion state.

### Menu state across game modes

The captures include a LobbyVM transition error, but do not show a direct proof
that the Mods entry was injected into a Zombies target. The current Lua code
gates that entry to the mode-select target and skips secondary lobby IDs. The
stock-callback containment above is the only source change made for this report.
If the entry still appears in Zombies, log the target ID and target name at
construction time and verify which Lua generation owns the callback; do not
broaden target fallbacks or retain button tables between menu generations.

## Other plausible causes and safe ways to distinguish them

1. **Stock frontend callback exception:** now contained by the wrapper and
   covered by a Lua regression. Verify that the UI remains navigable on console.
2. **Third-party map/mod script exception:** the captures include script errors
   attributed to external mod content. Reproduce with that content isolated;
   do not patch its behavior in this generic frontend code without its source.
3. **Asset streaming delay:** compare frame and stream progress through the
   stall; do not infer a GPU deadlock from a single unchanged completion sample.
4. **Resource exhaustion:** require an allocator/pool failure at the moment of
   failure. Current snapshots are not sufficient evidence to enlarge pools.
5. **Camo callback or asset path:** reproduce the exact selection and capture
   the first exception/crash frame before changing callback routing or assets.

## Validation and limits

The Lua host regression verifies pass-through on success, exception containment,
fresh fallback-table ownership, once-per-target logging, and that the failed
callback does not append a menu entry. Host tests do not emulate BO3's LUI or
prove console stability. No SPRX build, upload, pool change, or upstream patch
was made for this review.

## Continuation checklist

- Run the repository host suite and `git diff --check` before publishing source.
- On console, check mode-select navigation, Zombies entry, return to frontend,
  and the Mods entry after a failed/normal menu refresh.
- Capture a dedicated camo-option reproduction and its first fault, if any.
- Capture the complete custom-map startup and kernel crash context; compare a
  same-map plugin-off run before changing streaming or pool behavior.
- Record any new symptom and the tested source revision in `docs/DEVELOPMENT.md`.
