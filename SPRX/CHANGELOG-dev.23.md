# dev.23 — host stack preparation

When a joining client's loaded mods differ from the host's ordered selection,
prepare that stack through the existing whole mode-common loading transaction.
This replaces appending host mods after the common zone has already loaded.
Matching manually enabled stacks are left alone. Personal mod selection,
zone-loading and memory-pool guards, and the host activation launch hold remain
in place. The connected-session path does not restart the frontend connection.

The new production-function regression fixture covers changed and matching
stacks, order changes, an empty host selection, pending loads, in-level calls,
memory-pool guards and personal activation. It is included in both hosted test
workflows. Existing activation, publication and transaction checks also pass.

This is a validation build for the reported automatic-activation
`EXE_ERR_BG_CACHE` disconnect. The routing is tested; a console retest is needed
to determine whether it resolves that disconnect. No cache validation was
disabled. No 8-player gameplay code or clientfield schema was added to Customs.
The existing dev.22 Lua companion remains compatible and needs no new changes.

## Build and delivery

All 14 target translation units built with the pinned SDK and Debug settings.
Target validation passed; six malformed artifact controls were rejected.
Original SPRX: 453392 bytes, SHA-256
`210aa51c3fd2ba97682a603300c525e08631ada4ce57ad93101660b8de0d1b5f`.

Uploaded with FTP 226 to `/data/nexHEN/plugins/BO3-Customs-v4.00.1-dev.23-DEBUG.sprx`.
The PS5 FTP service returns a transformed 535616-byte ELF; its PT_LOAD code/data
payloads match the locally validated OELF, while whole-file hashes differ.
Use the preserved original SPRX ZIP when distributing to a PS4 tester.
Console runtime is not yet validated.
