# Game server overview, configuration, dependencies

> **Provenance:** moved verbatim on 2026-09-24 from `src/sho_gameserver/CLAUDE.md` lines 1-57; `src/sho_gameserver/CLAUDE.md` lines 109-125; `src/sho_gameserver/CLAUDE.md` lines 195-207 (revision `84f6206`).
> Original bytes: [`src--sho_gameserver--CLAUDE.md.txt`](../../archive/2026-09-24/src--sho_gameserver--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=1-57 sha256=a508371903e6b7c5c29e52ea9815e09c40e3a53bde674b17ce106cef57c8ff0f -->
# CLAUDE.md — Rose Next Game Server

## Overview

The game server (`sho_gameserver`) is the main server handling real-time gameplay: combat, movement, NPCs, AI, zones, parties, and chat. C++ built with VS2019 targeting x86. Uses IOCP for networking and PostgreSQL for persistence.

## Architecture

```
main.cpp → lib_gsmain (init) → Zone Threads (gs_threadzone)
                                    ↓
                              Per-zone game loop:
                              - Process player input packets
                              - Run AI (cobjavt / ai_lib)
                              - Compute combat (srv_common/)
                              - Broadcast state changes
                              - SQL thread for persistence
```

## Key Source Layout

| File/Dir | Purpose |
|----------|---------|
| `src/main.cpp` | Entry point |
| `src/lib_gsmain.cpp/h` | Server initialization and main loop |
| `src/gs_threadzone.cpp/h` | Zone thread — per-zone game ticks |
| `src/gs_user.cpp/h` | Player session management |
| `src/gs_listuser.cpp/h` | Connected user tracking |
| `src/gs_threadsql.cpp/h` | Async SQL operations |
| `src/gs_party.cpp/h` | Party system |
| `src/gs_socketlsv.cpp/h` | Inter-server communication (login/world) |
| `src/network.cpp/h` | Packet broadcasting helpers |
| `src/cobjchar.cpp/h` | Server-side character object |
| `src/cobjavt.cpp/h` | Avatar (player) object |
| `src/cobjnpc.cpp/h` | NPC/monster object |
| `src/cobjevent.cpp/h` | Event objects |
| `src/cobjitem.cpp/h` | Dropped item objects |
| `src/status_effects.cpp/h` | Buff/debuff system |
| `src/srv_common/` | Combat calculations, skill processing, damage application |
| `src/ai_lib/` | Server-side AI behavior |
| `src/common/` | Code shared with worldserver |

## Networking

- IOCP-based (inherited from `common-server/`)
- Packet handlers: `Recv_cli_*()` for client packets, `Send_gsv_*()` for server packets
- Broadcasting: `send_packet()` (single), `send_packet_party()` (party), `send_packet_nearby()` (sector-based, 9 adjacent sectors)
- FlatBuffers for some packet types (movement, stat updates)
- Inter-server: communicates with LoginServer and WorldServer via `gs_socketlsv`

## Zone System

- Each zone runs in its own thread (`gs_threadzone`)
- Zones divided into sectors for spatial queries
- `send_packet_nearby()` broadcasts to players in 9 adjacent sectors
- Zone data loaded from STB files in `data/` directory

<!-- verbatim:end -->

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=109-125 sha256=25e5bb2710e3d4a27e7adb3a80a4e035194adf2cb5e81e1dbd3693110aed5195 -->
## Configuration

`server.toml` in working directory (see `doc/server.toml.example`):
```toml
[database]
connection_string = "postgres://user:pass@localhost/rose-next"

[gameserver]
ip = "127.0.0.1"
port = 29200
server_name = "Channel 1"
data_dir = "C:\\path\\to\\data"
log_level = 2
```

Log levels: 0=Trace, 1=Debug, 2=Info, 3=Warn, 4=Error, 5=Off

<!-- verbatim:end -->

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=195-207 sha256=0f0cb81945a172061f793cad1d8c0809ffdd10a92219be38a9152a6d1d6f3b66 -->
## Dependencies

- `common-server` — IOCP sockets, SQL thread base
- `common` — shared game logic (calculations, items, quests)
- `common-lib` (Rust FFI) — logger, config parsing
- `lib_util` — C++ utilities
- Thirdparty: libpq (PostgreSQL), lua5, flatbuffers

## Conventions

- Same C++ conventions as client: `C` class prefix, `m_` members, `g_` globals
- Precompiled headers: `stdafx.h`
- Server-specific prefixes: `gs_` for gameserver modules, `srv_` for server-common
<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
