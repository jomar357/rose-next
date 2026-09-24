# Project overview and architecture

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 1-22; `CLAUDE.md` lines 210-212 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=1-22 sha256=17cbc454ab5a6d8c921d89a0d5150f2fcbbd3f7ad9dfc63b89673a1e9b227f47 -->
# CLAUDE.md — Rose Next Classic

## Project Overview

Rose Next Classic is a modernized ROSE Online private server + client built on the original iROSE C++ codebase. The server uses PostgreSQL (replacing MSSQL). The client is a Direct3D 9Ex (with plain D3D9 fallback) Win32 application. Everything is **32-bit x86 Windows**.

## Architecture

```
Client (C++/D3D9Ex) ←→  LoginServer (C++)  ←→  WorldServer (C++)  ←→  GameServer (C++)
                                    ↕                ↕                    ↕
                              PostgreSQL DB     Game Data (STB/STL)   Game Data
```

- **Client:** `src/client/` — Direct3D 9Ex (plain D3D9 fallback), Win32, packet-based networking
- **Servers:** `src/sho_loginserver/`, `src/sho_worldserver/`, `src/sho_gameserver/`
- **Shared C++:** `src/common/` (calculations, items, quests), `src/common-server/` (IOCP sockets, SQL threads)
- **Shared Rust:** `src/common-lib/` — FFI library (logger, config parsing, FlatBuffers codegen)
- **Engine:** `src/engine/` — 3D rendering, terrain, effects
- **UI framework:** `src/tgamectrl/` — custom GUI controls
- **Pipeline:** `src/pipeline/` (Rust) — asset baking tool

<!-- verbatim:end -->

<!-- verbatim:begin src=CLAUDE.md lines=210-212 sha256=c79e15b8a5f7c069a31b328eae1eef3fb97e49676e7225bfe45c7220f798684b -->
### Server Zone Architecture
GameServer manages zones via `gs_threadzone` — each zone runs in its own thread. Players are tracked per-sector for efficient broadcasting (`send_packet_nearby()` checks 9 adjacent sectors).

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
