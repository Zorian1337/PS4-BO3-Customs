# Stream guard diagnostics

`BlockJob_h` retains its established stream-ring and length rejection policy. When
that policy rejects a job, DEBUG builds now emit a bounded trace record before
the same two length fields are cleared:

- `reason=outside-ring` or `reason=invalid-lengths`;
- read-ring base, stream slot and data pointer;
- unpacked, hashed and stored lengths.

The recorder is nonblocking and saturates at 16 events for the process lifetime.
Release builds do not emit the trace. The native arguments, rejection conditions,
field writes and original function call remain unchanged. This is diagnostic
instrumentation only; it is not a fix for the Buried backend crash.

The host regression test exercises valid pass-through, the outside-ring
rejection, both malformed-length conditions, boundary arithmetic, and the
concurrent 16-event cap. Console reproduction and correlation with a fresh
Buried kernel report are still required before attributing the crash.
