# Client build, conventions, launch and diagnostic logging

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 693-745 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=693-745 sha256=e79dd7c548681110bc9e7813697afb80a9fc5224e664316eb10fb801aa216407 -->
## Build

Built as part of `rose-next.sln` (x86/Win32). Depends on:
- `engine` — 3D rendering
- `common` — shared game logic
- `tgamectrl` — UI controls
- `lib_util` — utilities
- `common-lib` (Rust) — FFI staticlib
- Thirdparty: Direct3D 9Ex (core headers come from the Windows SDK), D3DX9 June 2010 (`d3dx9_43.dll`, **must ship with the client**), lua4, imgui, **RmlUi 6.2 + FreeType 2.13.3**, ogg/vorbis, flatbuffers, sqlite, zlib

## Conventions

- Classes prefixed with `C` (CObjCHAR, CNetwork)
- Members prefixed with `m_` (m_CombatDamageQueue, m_iAuthoritativeHP)
- Globals prefixed with `g_` (g_GameDATA, g_pNet)
- Precompiled headers: `stdafx.h`
- Resource files: `client.rc`, `res/`

## Client Launch

```
rosenext.exe --server <IP>
rosenext.exe --server 127.0.0.1 --username user --password pass --auto-connect-server 1 --auto-connect-channel 1 --auto-connect-character CharName
```

Working directory: `dev/game/` (set up via `just dev-setup`)

### Diagnostic logging

`client.log` verbosity is a runtime switch resolved in `winmain.cpp::ResolveLogLevel()`:

```
rose-next.ini  ->  [LOG]  LEVEL=debug
environment    ->  ROSE_LOG_LEVEL=debug     (wins over the ini)
```

Accepted: `trace` / `debug` / `info` (default) / `warn` / `error` / `off`; anything else
falls back to `info`. The resolved level is echoed into the log itself as
`Log level: <name>`, so a handed-over log states its own verbosity — without it a log with
no `CombatTrace` lines reads identically whether the trace was off or the traced code never ran.

**Everything diagnostic reports at Debug.** `LogString(LOG_DEBUG_, ...)` maps to
`LogLevel::Debug`, which covers all `CombatTrace` lines (queued/popped/discarded damage
events, server swings, skill classification), skill tracing and the streaming counters. It
is also *loud*: terrain streaming logs per object, so the file grows fast and the
`fmt::sprintf` cost lands on exactly the frames that already hitch (see `rose/common/log.h`).
Keep repros short and put it back to `info` afterwards.

The file is `client-YYYY-MM-DD.log` in the game directory, opened in **append** mode — it
accumulates across runs on the same day, so delete it (or note the wall-clock time of the
repro) before capturing. It flushes per record, so it survives a hard crash; `error.txt`
does not.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
