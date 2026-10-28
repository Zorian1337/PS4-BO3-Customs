# dev.24 — native BG cache mismatch diagnostics

The t162/dev.23 tester log confirms the missing files downloaded and both host
mods finished loading. The subsequent EXE_ERR_BG_CACHE occurs with zero script
errors. Manual enabling permits the player to join and spawn. Automatic mod
activation is therefore still unresolved; common-zone completion alone is not
proof of equivalent native initialization.

This build records the native cached, received and calculated BG-cache checksum
words at transition boundaries and at that exact error. Reads require the PS4
1.33 comparison signature and readable memory ranges. It does not reset native
state, change a checksum, skip validation, disconnect/rejoin clients, or modify
the working t162 spawn gate. Existing activation behavior is retained pending
the safe frontend/pre-join sequence investigation.

Tests execute the production snapshot and error hook, verify no native bytes are
modified, cover unreadable/signature-mismatch startup, and preserve native error
arguments/results. The new fixture runs in both CI host-check workflows.

Use this diagnostic when comparing automatic activation with successful manual
activation; retain both host and joining-client logs. No new Lua bundle or
8-player mod package is required. This is not a confirmed automatic-join fix.

Build validation passed for all 14 target translation units and the native
artifact check, including rejection of six malformed controls. The original
SPRX and single-file ZIP are preserved under `dev12-work/releases/dev24`.
The attempted console FTP connection timed out; this build is not uploaded or
console-tested. Upstream PR #20 carries the diagnostics only and is mergeable;
the underlying activation defect remains tracked in the fork's issue #20.
