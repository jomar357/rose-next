# Project structure

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 55-94 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=55-94 sha256=88e5301392026674cb0b36f96ef06f4d1c589846959942a06aac3c34bec4d741 -->
## Project Structure

```
src/
├── client/              # Game client (D3D9Ex, Win32)
│   ├── network/         # Packet send/recv
│   ├── interface/       # UI dialogs
│   ├── gameproc/        # Game state processing
│   └── ai_lib/          # Client-side AI
├── sho_gameserver/      # Main game server (combat, zones, NPCs)
│   └── src/
│       ├── ai_lib/      # Server AI
│       ├── srv_common/  # Server combat/skill logic
│       └── common/      # Shared with worldserver
├── sho_loginserver/     # Authentication server
├── sho_worldserver/     # World/channel management
├── common/              # Shared C++ (client + server)
│   ├── shared/          # Items, quests, inventory, economy
│   └── include/rose/    # Shared headers (network/, common/, io/, util/)
├── common-server/       # Shared server (IOCP sockets, SQL)
├── common-lib/          # Rust FFI lib (logger, config, flatbuffers)
├── engine/              # 3D engine (D3D9Ex rendering)
├── tgamectrl/           # UI control framework
├── pipeline/            # Rust asset pipeline tool
├── tools/               # Standalone Rust dev tools (workspace members)
│   ├── vfs-browser/     # rose-vfs: TUI browser for data.idx / .vfs (ratatui + rfd)
│   ├── npc-shop-editor/ # egui editor for LIST_NPC/LIST_SELL shop tabs (COW on shared rows)
│   │                   # also builds gm-item-browser.exe: read-only tester catalog, /item + /mon clipboard;
│   │                   # flags broken LIST_NPC rows (server refusal, CHR/ZSC/mesh/texture/motion)
│   └── quest-editor/    # CLI + egui wizard: Hunt/Fetch quests + NPC dialog givers (see its PROGRESS.md)
├── rmlui/               # (in client/) RmlUi integration: D3D9 backend, system iface, panels
├── lib_util/            # C++ utility library
└── triggervfs/          # Virtual filesystem
data/                    # Game data files (STB tables, scripts, shaders)
database/                # PostgreSQL schema + migrations
thirdparty/              # C++ deps (lua, zlib, ogg/vorbis, imgui, flatbuffers, etc.)
scripts/                 # PowerShell build/dev scripts
 
```

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
