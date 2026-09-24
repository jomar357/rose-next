# Client overview

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 1-39 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=1-39 sha256=11d7b6fe4793bbd0ba4fd67f55b11ec47bef21c65e12b91c68de956919ef9232 -->
# CLAUDE.md — Rose Next Client

## Overview

Direct3D 9Ex (with plain D3D9 fallback) Win32 game client. Single-threaded game loop with packet-based server communication. All code is C++ built with VS2019 targeting x86.

## Key Subsystems

| Directory | Purpose |
|-----------|---------|
| `network/` | TCP socket management, packet send/recv (CNetwork singleton) |
| `interface/` | UI dialogs and HUD elements |
| `gameproc/` | Game state machine and processing |
| `gamedata/` | Runtime game data management |
| `ai_lib/` | Client-side AI behavior |
| `event/` | Event scripting |
| `sfx/` | Special effects |
| `sound/` | Audio playback |
| `terrain/` | Terrain rendering |
| `system/` | System-level (input, window) |
| `scripts/` | Lua scripting integration |
| `objectcommand/` | Character action/command processing |

## Important Classes

- **CObjCHAR** (`cobjchar.cpp/h`) — Base character object (player, NPC, monster). Manages server-authored damage presentation, HP reconciliation, pending death state, and animation states. Most combat display logic lives here.
- **CObjUSER** (`cobjuser.cpp/h`) — Player character (extends CObjCHAR)
- **CGame** (`game.cpp/h`) — Main game loop and state
- **CNetwork** (`network/cnetwork.h`) — Singleton, manages Login/World/Game server connections
- **CGameOBJ** (`cgameobj.cpp/h`) — Base game object

## Networking

- Separate socket connections per server phase: Login → World → Game
- Packet handlers: `Recv_gsv_*()` for incoming, `Send_cli_*()` for outgoing
- FlatBuffers used for some packets (stat updates, movement)
- Packet receive: `network/recvpacket.cpp`
- Packet send: `network/sendpacket.cpp`

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
