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

## Build System

Mixed Rust (i686-pc-windows-msvc) + C++ (VS2019, x86). Three-phase build:

```powershell
# Full build (recommended)
just build release    # or: scripts/build.ps1 -config release

# Manual steps:
# 1. Build thirdparty C++ deps
MSBuild.exe thirdparty.sln -p:Configuration=release;Platform=x86
# 2. Build Rust crates (MUST be i686)
cd src/ && cargo +stable-i686-pc-windows-msvc build --release
# 3. Build Rose Next C++ projects
MSBuild.exe rose-next.sln -p:Configuration=release;Platform=x86
```

### Key build facts
- Rust toolchain override: `stable-i686-pc-windows-msvc` in `src/`
- Cargo target dir: `bin/` (set in `src/.cargo/config`)
- Output binaries: `bin/release/` — rosenext.exe, sho_gameserver.exe, sho_loginserver.exe, sho_worldserver.exe, pipeline.exe
- Thirdparty output: `bin/release/thirdparty/`
- `ntdll.lib` is a required linker dependency for client and all servers
- Build assets: `just build-assets release` or `scripts/build-assets.ps1`
- **`common` and `lib_util` used to compile with `/Od` in the *release* configuration** — an explicit `<Optimization>Disabled</Optimization>` in their release `ItemDefinitionGroup`, not an inherited default. Both are now `MaxSpeed`. **Check what a project actually compiles before estimating the blast radius.** `common.vcxproj` builds only 8 of the 21 `.cpp` files under `src/common/` — `io/stb.cpp`, `io/reader.cpp`, `log.cpp`, `network/network_util.cpp`, `util.cpp`, `uuid.cpp`, `sha256.cpp`, `goddess_effect.cpp`. `lib_util` adds `CStr`, `CRandom`, the socket layer, `PacketHEADER`, threads and hashing. `calculation.cpp` and the shared item/quest code are **not** in either — they are listed directly in `client.vcxproj` and `sho_gameserver.vcxproj`, so combat math was always optimized. The fix is real but it is the STB/string/socket layer, not the game logic. Measured on `item_drop.stb` (438 KB, 188,751 cells): parse **34 ms → 2 ms, 17x**, which took the character-select stall's table loading with it.
  - **A missing `<Optimization>` element does *not* mean `/Od`.** `triggervfs`, `tgamectrl` and `common-server` have no such element and inherit `/O2` from the MSBuild release defaults — they are fine. Only an *explicit* `Disabled` is a bug, so grepping for absent properties produces false positives. Confirm with `MSBuild ... -t:<project> -v:detailed` and read the actual `CL.exe` command line.
  - `sho_gameserver` is deliberately `MinSpace` (`/O1`), which is optimized, just for size rather than speed.
  - **MSVC's diagnostics here are localised (French).** Filtering build output for `": error"` silently matches nothing — the string is `": erreur"`. A build that failed can look like a build that passed.
- **D3D9 core headers come from the Windows 10 SDK**, not the vendored DX SDK — `d3d9.h`/`d3d9types.h`/`d3d9caps.h` were deleted from `thirdparty/directx9/include/` so the SDK copies (which have the 9Ex interfaces) win. MSVC searches every `/I` path before the system include dirs, so the vendored copies could not be beaten by ordering. The rest of the vendored SDK stays, because D3DX9 is not in the Windows SDK.
- **`d3dx9_43.dll` must ship with the client** — D3DX9 is linked against the June 2010 redistributable rather than the old static lib. `scripts/post-build.ps1` copies it into `bin/<config>` and `scripts/dist.ps1` bundles it; a hand-rolled deploy that forgets it produces a client that will not start.
- **RmlUi and FreeType are hand-written `.vcxproj` files in `thirdparty.sln`** (like every other dep here — the upstream projects are CMake-based and we do not use CMake). Both need `RMLUI_CUSTOM_RTTI` (client RTTI is off) and `RMLUI_FONT_ENGINE_FREETYPE` — without the latter RmlUi compiles its "no font engine" branch and `Rml::Initialise` fails at runtime. RmlUi also needs per-directory object output (`<ObjectFileName>$(IntDir)%(RelativeDir)</ObjectFileName>`): `Source/Core/Geometry.cpp` and `Source/Debugger/Geometry.cpp` share a basename and otherwise overwrite each other, failing the link with unresolved externals that look like missing sources.

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
│   │                   # also builds gm-item-browser.exe: read-only tester catalog, stats + /item clipboard
│   └── quest-editor/    # CLI + egui wizard: Hunt/Fetch quests + NPC dialog givers (see its PROGRESS.md)
├── rmlui/               # (in client/) RmlUi integration: D3D9 backend, system iface, panels
├── lib_util/            # C++ utility library
└── triggervfs/          # Virtual filesystem
data/                    # Game data files (STB tables, scripts, shaders)
database/                # PostgreSQL schema + migrations
thirdparty/              # C++ deps (lua, zlib, ogg/vorbis, imgui, flatbuffers, etc.)
scripts/                 # PowerShell build/dev scripts
 
```

## Database

- PostgreSQL 12+
- Connection configured in `server.toml` (see `doc/server.toml.example`)
- Migrations in `database/migrations/` — squash with `scripts/squash-migrations.ps1`
- Passwords: SHA256 + salt (generate with `scripts/generate-password.py`)

## Networking

- Custom packet-based protocol over TCP (IOCP on server side)
- FlatBuffers for some packet types (defined in `src/common-lib/packets/*.fbs`)
- C++ packet definitions in `src/common/include/rose/network/`
- Client has separate socket connections: Login → World → Game server

## Code Conventions

- C++ formatting: **do not run clang-format over the tree.** `.clang-format` /
  `.clang-format-ignore` are inherited from the original team and the checked-in code no
  longer matches what current clang-format produces (VS2019's 12.0.0 rewrites ~4x more
  lines than a typical change touches, burying real diffs in churn). Match the style of
  the surrounding code by hand instead. The `scripts/format_code.py` driver was removed
  for this reason; the config files are kept only so editors have something to read.
- Rust: standard `cargo fmt`
- Prefix conventions: `C` for classes (CItem, CObjCHAR), `m_` for members, `g_` for globals
- Server packet handlers: `Recv_cli_*` / `Send_gsv_*` naming
- Client packet handlers: `Recv_gsv_*` / `Send_cli_*` naming

## Dev Environment

```powershell
just dev-setup              # Creates dev/ symlinks for assets
just client release         # Run client
just server-all release     # Run all servers
just loginserver release    # Run individual server
```

- Client looks for assets in `dev/game/`
- Servers look for data in `data/` (configurable in server.toml)
- A/B test two client builds in the real game: `scripts/ab-build.ps1 stage <name>` / `use <name>` / `toggle`. `rosenext.exe` imports `znzin.dll` by name, so the exe+dll must be swapped as a **pair** — never rename one half. See the header for the HUD-labelling and vsync caveats.
- Auto-connect: `rosenext.exe --server 127.0.0.1 --username user --password pass --auto-connect-server 1 --auto-connect-channel 1 --auto-connect-character CharName`

## Important Patterns

### Combat Damage Presentation
Combat damage is server-authoritative. The server calculates and applies HP once, then sends FlatBuffer `DamageEvent` / `CombatSwing` packets containing the final `damage_value`, `hp_after`, `presentation_kind`, and `lethal` checkpoint. Legacy `GSV_DAMAGE_OF_SKILL` packets also carry authoritative `m_iHP_AFTER`; the client must not synthesize combat skill checkpoints from visible HP. The client must not recalculate live combat damage.

The client queues `DamageEvent`s per defender in `CObjCHAR::m_CombatDamageQueue`. `CombatSwing` queues the event before starting the confirmed attack animation; `Hitted()` consumes exactly one matching event at the visual hit frame. Projectile damage is queued on receive and presented only on projectile impact. If hard control such as sleep/faint interrupts an attacker before its confirmed normal swing can spawn or reach its hit/projectile consumer, the client discards that exact queued event by `event_id`, folds the server-applied HP silently into the next real presentation, and immediately presents avatar death if the orphan was lethal. Direct HP stat packets (`UpdateStats.hp`, `GSV_SET_HPnMP`) update authoritative shadow HP; lower HP never silently moves the visible bar during combat.

**Mob-death item drops are announced by the sector broadcast, not by the damage packet.** The legacy `gsv_DAMAGE` / `gsv_DAMAGE_OF_SKILL` builders appended the drop inline as a `tag_DROPITEM` *and* called `CObjITEM::SetACTIVE()` as a side effect of building the packet. The FlatBuffer `DamageEvent` path carries no drop, so that activation has to be explicit — and it must happen **before** `CZoneTHREAD::Add_DIRECT`, because a field item is announced exactly once, at insertion: `AddObjectToSector` calls `Make_gsv_ADD_OBJECT`, which early-returns while `m_iRemainTIME <= 0`, and the entire nine-sector broadcast block is skipped. Activating afterwards produces an item that is live in the zone, holds a valid index, is pickable by position — and invisible to every client. Use `SetACTIVE()` rather than `bActive=true` on `InitItemOBJ`: only the former applies the longer party-ownership window. **A field item is also announced more than once, and the client must tolerate that** — at insertion, and again by the sector-visibility path when a player crosses into the sector it landed in (drop positions are randomised by +/-100 units, so a mob-death drop often lands one sector over). The server re-sends deliberately, calling `Update_OwnerObjIDX` first because ownership can change. `CObjectMANAGER::Add_GndITEM` does **not** dedupe: it allocates a fresh slot and `Set_EmptySlot` repoints `m_nServer2ClientOBJ` at the new object, orphaning the first — still drawn, unreachable by server index, so it can never be picked up or removed. The symptom is two identical items where one loots and one is permanent. `Recv_gsv_ADD_FIELDITEM` now refreshes the existing object instead; that is done in the handler rather than inside `Add_GndITEM` because the caller follows up with `InsertToScene()`, which calls `CreateAnimatable()` and re-links scene nodes and is not safe to run twice. Note `CObjectMANAGER::Set_ServerObjectIndex` has a guard for exactly this and it does not work: it indexes `m_nServer2ClientOBJ[client_idx]` where it means `[server_idx]`, and `Set_EmptySlot` writes the map directly without ever calling it — so the "Server replaced existing object" warning never fires. **There are two client routes that build a ground item, and both need that guard.** A skill kill announces the same drop twice: `Apply_DAMAGE` activates and inserts it (sector broadcast → `Recv_gsv_ADD_FIELDITEM`), and the very same `CObjITEM` is then passed to `Send_gsv_DAMAGE_OF_SKILL`, which appends it inline as a `tag_DROPITEM` → `PushFieldItemToList` → `CObjCHAR::DropFieldItemFromList`. The broadcast wins the race (sent at insertion; the list drains only when the death animation presents), so the second route is the one that orphans. Auto-attack kills never take it — `Send_gsv_DAMAGE2Sector` has **no callers**, so the FlatBuffer path carries no inline drop — which is why this reproduces on a skill/summon class (Dealer) and not on a Soldier auto-attacking, and why fixing only the handler looked like a complete fix. The other three drop sites (`cobjnpc.cpp`, two in `gs_user.cpp`) already pass `bActive=true` and were never affected, which is why player- and AI-dropped items worked while mob kills dropped nothing.

A queued event that can never be presented must be removed, or reconciliation dies. `has_pending_damage()` gates **both** HP reconciliation paths, so a single event stranded in a defender's queue disables HP convergence for that character for the rest of its life — the bar then moves only by each hit's own digit and the client/server drift accumulates unbounded. Draining on the attacker's `Dead()` covers only attackers that die; an attacker that leaves your sectors (`Del_Object`), a zone change (`Clear`), or a second swing queued before the first was presented all strand events too. `CObjCHAR::Proc()` runs a timed orphaned-damage sweep as the generic safety net; it resolves silently into shadow HP and deliberately skips lethal events, which have their own death-presenting paths. See client `CLAUDE.md`.

HP convergence is hidden from floating digits. `DamageEvent.damage_value` is the displayed hit number, while folded reconciliation/checkpoint drift only affects visible HP and death state. Local-avatar dead reconciliation becomes pending authoritative death: outgoing attacks show MISS/no damage until the next incoming monster hit presents death, except mutual-death cases where the avatar dies immediately after the monster's normal lethal presentation. When the avatar kills its only/last attacker mid-swing, the drain-on-death path presents the mutual death immediately on the kill (no incoming hit is coming). A `CObjCHAR::Proc()` backstop forces the death after ~1.5 s if the avatar is left pending-dead with no presentation (no-attacker kills like DoT/fall damage), so the player is never stranded alive-client / dead-server and frozen. Remote/non-avatar lethal melee events also have a ~1.5 s spectator fallback: if the killer animation never consumes the queued death on this client, the defender still runs `Dead()` instead of remaining visually alive. The fallback defers (up to a 6 s hard cap) while the killer's confirmed swing for that exact event is still live — slow cart/castle-gear swings put the hit frame past 1.5 s, and popping early killed one-shot targets mid-swing. See client `CLAUDE.md` for details.

### Rendering Device (Direct3D 9Ex)
The client runs on a **Direct3D 9Ex** device when available, falling back to plain D3D9. The payoff is that alt-tab, lock, UAC and RDP no longer lose the device — previously each cost a full invalidate → reset → reload-every-texture-from-VFS cycle that also threw on failure.

Consequences worth knowing before touching rendering:
- **`D3DPOOL_MANAGED` is illegal on a 9Ex device** and has been removed from everything we compile. New resources go in `D3DPOOL_DEFAULT` and must survive `invalidate_device_objects()` / `restore_device_objects()`. `D3DPOOL_SYSTEMMEM` is still legal — use it for anything that genuinely needs `LockRect`, since DEFAULT textures cannot be locked.
- A DEFAULT-pool buffer that is locked every frame needs `D3DUSAGE_DYNAMIC` + `D3DLOCK_DISCARD`; a plain DEFAULT buffer locked per-frame stalls the pipeline. Conversely `D3DLOCK_DISCARD` is illegal on a non-dynamic buffer.
- `S_PRESENT_OCCLUDED` and `S_PRESENT_MODE_CHANGED` are **success** codes — a plain `FAILED()` test misses them. Occlusion must throttle, never reset. An occlusion log line is *not* a black screen: a skipped present leaves the previous front buffer on screen, so the throttle costs a dropped frame, never a blank one.
- Under 9Ex `TestCooperativeLevel()` is deprecated and always returns `S_OK`; use `CheckDeviceState()`, and only after a present returns something unusual.
- **Fullscreen is borderless by default** — a windowed device covering the monitor, so nothing ever hands display-mode ownership back and forth. The legacy exclusive device is `[VIDEO] EXCLUSIVE_FULLSCREEN=1` (or `ROSE_EXCLUSIVE_FULLSCREEN=1`); it produced brief full-screen black flashes mid-game that borderless removes by construction. In borderless the backbuffer is **always** the monitor size — anything else is stretched by D3D and drifts UI hit-testing.
- **`_fill_fullscreen_mode_ex()`'s `D3DDISPLAYMODEEX` must mirror the present parameters exactly** (`Format` = `BackBufferFormat` even though that is `A8R8G8B8`, `RefreshRate` = `FullScreen_RefreshRateInHz` even when that is 0). The runtime cross-checks them and returns `D3DERR_INVALIDCALL` — and the fallback ladder then hands back a working Ex device via plain `CreateDevice`, so **only the log tells you**. Read `error.txt` after any device-creation change.
- Force the legacy path for A/B testing with `[VIDEO] D3D9EX=0` in `rose-next.ini` or `ROSE_NO_D3D9EX=1` in the environment — and confirm via the log, since a toggle that silently does nothing gives a false negative.
- The **depth-stencil format is negotiated at device creation**, not fixed — see "Depth Buffer Precision" below before touching format selection in `initialize()`.

`[VIDEO] VSYNC=0` uncaps the framerate — but vsync is **not** the only limiter, contrary to what this line used to say. `zz_system::sleep()`, reached from `swapBuffers()`, enforces `max_framerate` with `::Sleep()`. It does not bind in practice only because `data/SCRIPTS/INIT.LUA:39` calls `setFramerateRange(15, 1000)`; the `src/` default is **60**, so grepping `src/` alone gives the wrong answer — the same trap as `setMipmapLevel` and `setLazyBufferSize`. Note `sleep()` also runs `manager_update()`, the resource amortiser, so the client's `present` phase has never been GPU wait alone: measured, real Present is 0.2–0.4 ms and the rest was the amortiser plus a per-frame yield. Full design notes, the D3DX9 upgrade rationale, the rejected `FLIPEX` work and the remaining gaps are in [doc/d3d9ex-migration.md](doc/d3d9ex-migration.md).

### Bone Particle Budget (Client/Engine)
Cosmetic character bone effects created by `CCharMODEL::CreateBoneEFFECT` are tracked separately by `CBoneEffectBudget` (`src/client/BoneEffectBudget.*`). This budget exists for passive bone-attached aura/loop effects only; skill, hit, projectile, terrain, weather, weapon, and normal world effects must not be registered there.

The manager budgets visible bone-effect groups by estimated particle capacity and emit rate, then applies particle-only tiers through `CEffect::SetParticleTier`: Full, Reduced, Minimal, Off. Mesh and sound components remain unchanged. Runtime caps and emit scaling are enforced in the engine particle emitter/sequence code, so degraded/off tiers are actually cheaper instead of only hidden. Current relaxed budgets are 480 runtime particles, 360 emit/sec, and 3 full duplicate groups per same NPC/effect signature. The debug HUD exposes this as the `BoneFx:` line.

Additive-compatible bone particles also opt into safe texture batching through `CEffect::SetParticleBatchRenderHint`, forwarded to `zz_particle_emitter`. Only `CreateBoneEFFECT` enables this hint. The engine batches hinted additive sequences by texture/render state in `zz_particle_emitter::RenderParticleListWithBatching`; incompatible particles and all non-bone effects use the old render path. The debug HUD exposes batching as the `PartBatch:` line.

### Monster Spawning: A Regen Point's Cap Is Not A Cap

`CRegenPOINT::Proc` is a **tactical escalation state machine**, not a spawn list. Its
five "basic" slots plus two "tactics" slots are steps, and each tick it picks one or
two of them — never all five — from an 11-branch table indexed by

    iVar = ((limitCNT*2 - liveCNT) * curTactics * 50) / (limitCNT * tacticPoint)

Two things follow, and both have bitten:

- **`tacticPoint` decides whether `limitCNT` means anything.** `CZoneTHREAD::RegenCharacter`
  has **no cap check** — the only gate is `Proc`'s early return while
  `liveCNT >= limitCNT`, so whatever branch fires spawns its full count regardless of
  how much room is left. `tacticPoint` scales the whole table: at 100 (the house value;
  every zone we ship uses 50-200) an empty point starts at `iVar == curTactics == 1`,
  walks up from the bottom branch and fills to exactly `limitCNT`. At **1** the first
  tick computes `iVar = 100`, lands in the *top* branch, and spawns four bodies into a
  cap of one. Karkia's two main maps shipped that way and held 3,388 and 1,109 monsters
  against summed caps of 847 and 278 — **every density figure measured from the tables
  was 4x low.** Never derive a zone's population from `sum(limitCNT)`; simulate `Proc`.
- **Per-slot count must stay well under `limitCNT`.** Count 5 against a cap of 5 means
  slot 0 fills the point on tick one and slots 1-4 are unreachable until a player
  clears the nest by hand — which reads in game as "this zone only has one monster",
  then a second species, then a third. Retail runs counts of 1-2 against caps of 2-13.
  Weight a species by **repeating its slot**, never by raising the count. `interval`
  paces the escalation as well as the respawn: one tick is one step.

Karkia's rosters, caps, intervals and camp layout live in `scripts/import-karkia.py`
stage 3 (`SPAWN_ROSTER` / `SPAWN_CAP` / `SPAWN_INTERVAL` / `SPAWN_THINNING` /
`SPAWN_CAMPS`), which **rebuilds every REGEN lump from source on each run** — so
editing an `.IFO` by hand or in the map editor is silently undone by the next
`--stage 3`. Note the two main maps are authored as a *carpet* of single-species
points, so spatial thinning deletes species; `SPAWN_CAMPS` merges neighbouring points
into mixed-species camps instead, which cannot.

Separately: **a zone that ships no `.MOV` file is blocked on every cell**, which
silently disables monster leashing, wandering and fleeing while leaving chase intact.
See the gameserver `CLAUDE.md`.

### Server Zone Architecture
GameServer manages zones via `gs_threadzone` — each zone runs in its own thread. Players are tracked per-sector for efficient broadcasting (`send_packet_nearby()` checks 9 adjacent sectors).

### Summon Control (CTRL+Click)
Players can directly command their summons with CTRL+click: on terrain → all summons move there; on a hostile monster → all summons attack it. Non-CTRL clicks are unchanged, and CTRL+click is only hijacked when the player actually owns a summon. The client (`jcommandstate.cpp` `TrySummonControlClick`, hooked into both single- and double-click paths) sends the shared `CLI_SUMMON_CONTROL` packet; the server (`classUSER::Recv_cli_SUMMON_CONTROL` → `CZoneTHREAD::CommandSummons_MoveTo`/`_Attack`) is authoritative. `CObjSUMMON` holds a ~5 s manual-order window that suppresses its follow-the-owner loop and AIP auto-aggro, then resumes normal following. Move orders use `CObjSUMMON::PlayerOrderMoveTo` (tolerant of non-walkable cells) — **not** `SetCMD_MOVE2D`, whose `IsMovablePOS` gate silently drops clicks. See the client and gameserver `CLAUDE.md` files for details.

### Summon Info Panel (Client)
`CSummonInfoPanel` (`src/client/interface/csummoninfopanel.*`) is a draggable on-screen overlay showing the player's active summons (name, ATK/DEF/LV/RES, HP). It draws directly with sprites/fonts (no XML resource) and is visible only while the player owns a summon. Key gotcha: a summon's stats are **scaled at creation** by summon-skill level + owner level (server `CObjSUMMON::SetCallerOBJ`), so the panel shows the scaled values, not the raw NPC table. The client recomputes the same formulas once at summon time in `recvpacket.cpp` and caches them in `SummonMobInfo` — if you touch the server scaling, update the client copy too. The underlying summon gauge (`CObjUSER::m_SummonedMobList`) is decremented at packet receive on lethal FlatBuffer `CombatSwing`/`DamageEvent` **and** legacy `DMG_BIT_DEAD` damage packets; the server mirrors lethal packets to a summon's out-of-range owner so a summon dying off-screen can't leak a gauge entry. See client `CLAUDE.md` for details.

### Monster Inspector (Client-Only Window Skill)
The "Monster Inspector" skill (LIST_SKILL row appended by `scripts/add-monster-inspector-skill.py`, currently id 7001; learn via GM `/add skill 7001` — not `/set`, whose handler has no SKILL branch) opens `CMonsterInspectorPanel` showing a targeted monster's level, live HP, LIST_NPC stats, drop-list icons (from `ITEM_DROP.STB`: mob table + zone table, redirect groups expanded) and a rotating 3D model. It is a `SKILL_CREATE_WINDOW` (type 2) skill with `SKILL_POWER` 50 — the client opens the window locally and **never sends a packet**, so it cannot aggro; the server needed no changes. The 3D preview is a client-only puppet clone of the monster model glued in front of the camera behind a cut-out pane (no render-to-texture). See client `CLAUDE.md` "Monster Inspector" for details.

### NPC Overhead Quest Icons (Client-Only)
NPCs show a "!" when they offer an acceptable quest and a "?" when a quest can be turned in (nothing otherwise). Revives the dead retail pipeline (`CObjNPC::m_nQuestSignal` + `QUEST_EMOTICON_*` draw in `CNameBox::DrawNpcName`); our evaluator is fully client-side and covers **all** quests: trigger names are harvested from the NPC's `.CON` Lua string constants (readable even in compiled bytecode), classified by QSD reward composition (`REWD_000` op1 = accept; `COND_000` + advance-or-delete-with-grant = turn-in; delete-only = abandon option, ignored), and probed with the same `CheckQUEST(..., false)` call retail dialogs use. Quest-editor dialogs additionally evaluate their `CHK_*` Lua check functions in a throwaway state. Refresh: NPC spawn / quest packets / 2 s tick. Sprites installed by `scripts/add-quest-emoticons.py` (placeholders; `--icons` for real art). **Deploy gotcha:** `UI_strID.ID` loads via `fopen` from the loose `3ddata\control\xml\` folder — the VFS bake never covers it. The tool-side mirror of the classifier lives in `src/tools/quest-editor/src/classify.rs` (keep in sync with `cevent.cpp`); it powers the wizard's "this NPC already offers …" info, the `con-triggers` CLI, and an icon-compatibility check in the editor's verify step. See client `CLAUDE.md` "NPC Overhead Quest Icons".

### Damage Meter (Client-Only)
The `/dps` chat command (intercepted locally, never sent) toggles `CDamageMeterPanel` — a draggable DPS/damage overlay with Damage Done (self + party ranking), My Skills, and Damage Taken views. Data comes from `CDamageMeter` (`src/client/gamedata/`), fed by a read-only tap at the single chokepoint `CObjCHAR::PushCombatDamageEvent`; it observes the authoritative combat event stream and never mutates presentation state. Party members' damage is metered for free because combat events broadcast to the 9 surrounding sectors. Attribution rides on two `DamageEvent` wire fields that are **display metadata only** (presentation must never branch on them): `skill_id` (exact skill; legacy `GSV_DAMAGE_OF_SKILL` also carries it; `CombatSwing` = auto-attack; client heuristic as fallback) and `source_attacker_id` (credit target when ≠ attacker: DoT caster, summon owner — so DoTs credit their caster and party pets fold into their owner's row). Cart/castle-gear attacks fold to the rider via `IsPET()` (castle gear is `OBJ_CGEAR`, not `OBJ_CART` — an equality check silently drops gear damage). See client `CLAUDE.md` "Damage Meter".

### Chat Item Links (Client-Only)
Shift+click an item icon in any `CSlot` (inventory, bank, equip, stores) inserts `[Item Name]` into the chat input; on send it is substituted with the wire token `<il:XXXXXXXXXXXX>` (12 hex chars = the 6 packed bytes of `tagBaseITEM`). Receivers rebuild name/rarity-color/tooltip locally from STBs (nothing spoofable is transmitted), render the link inline in the chat log (`CTListBox` link segments), and hover shows the standard item tooltip. Overhead speech bubbles show the plain `[Name]`. **Zero server changes** — chat relays bytes verbatim; the client never sends a message whose `strlen` exceeds 129 bytes (the server's `IS_HACKING` chat guard). Codec in `src/client/interface/chatitemlink.*`; max 3 links/message. See client `CLAUDE.md` "Chat Item Links".

### Item Preview Panel (Client-Only)
Alt+left-click an equipment item (any inventory/bank/store `CSlot` icon, or a chat item link) opens `CItemPreviewPanel` — the player's character wearing that item in a rotating 3D pane, without equipping it or sending any packet. Previews are cumulative while the panel stays open (hat + chest + weapon together; closing resets). Ctrl+click was unavailable (already bound to wishlist registration on item icons). The puppet reuses `CJustModelAVT` (character-select model viewer), never inserted into the scene, rendered through the same avatar-selection viewport pipeline as the Monster Inspector. Shared pane helpers + the avatar-selection camera absolute-value mirror live in `src/client/interface/OverlayPanelUtil.*` (one mirror process-wide — both panels use it). See client `CLAUDE.md` "Item Preview Panel".

### RmlUi UI Layer (Client)
New/custom client panels can be authored in **HTML/CSS-like files** (`.rml` / `.rcss`) instead of
hard-coded C++ draw calls, via **RmlUi 6.2 + FreeType 2.13.3** (`thirdparty/RmlUi-6.2`,
`thirdparty/freetype-2.13.3`, built as x86 `/MT` static libs with `RMLUI_CUSTOM_RTTI`). The client
side is `src/client/rmlui/`; assets live loose in `3ddata/rmlui/`.

Off by default — enable with `[VIDEO] RMLUI=1` in `rose-next.ini` or `ROSE_RMLUI=1`. When enabled,
`/dps` opens the RmlUi damage meter instead of the legacy `CDamageMeterPanel`; both read the same
`CDamageMeter` core, so they A/B in place.

**Scope is new/custom panels only.** `tgamectrl`, the 56 retail XML dialogs, chat input and **IME**
are out — RmlUi has no IME composition handling, and the input boundary is the fiddliest part of the
integration. The purpose is quick, player-editable interfaces, **not** reproducing the original
TSI/atlas workflow: `.rml`/`.rcss` are loaded loose (never via the VFS) so players can edit them, and
texture loading resolves **disk first, VFS second** so a player's file overrides shipped art.

Linear gradients are implemented in the D3D9 backend without a shader, and `border-radius` needs no
renderer support, so skins need no image files at all. Radial/conic gradients, blurred `box-shadow`,
`filter` and `transform` are **not** implemented and will warn or do nothing. Full design notes,
phase history, the authoring palette and the traps are in
[doc/rmlui-evaluation.md](doc/rmlui-evaluation.md); client specifics are in the client `CLAUDE.md`.

### Cull Bounds Come From Geometry, Not From The ZSC (Client/Engine)

Every ZSC object record caches a model-space AABB, and **it is wrong in every ZSC in
the game**: the exporter scaled only X into world units (cm) and left Y and Z in mesh
units, so the stored box is ~100x too thin and ~100x too short. Retail Junon has it too,
so it is not an import artefact. Muris' canyon walls registered as a 336 m x 4.0 m x
1.1 m ribbon on the ground instead of a 336 m x 396 m x 114 m wall; because fixed
objects live or die with their terrain patch, turning the camera pushed the ribbon out
of the frustum and `RemoveFromScene()` deleted the whole wall mid-screen. 222 of the
1388 map objects in `data/` under-cover by more than 20 m, the worst by 970 m (Junon
Polis' planet vessel).

It only ever mattered because we re-enabled patch culling: the original
`ViewCullingFunc` had its condition commented out around an unconditional `return 0`,
so every patch was "fully inside" every frame and the boxes were inert. *Re-enabling
dead code promotes its inputs from decorative to load-bearing* — the same shape as the
missing-asset retry storm below.

`CMAP_PATCH::MakeAABBFromObject` now asks the engine for the world AABB it already
derives from real mesh min/max (`getVisibleWorldMinMax` -> `CObjFIXED::GetWorldMinMax`),
keeping the cached box only as a fallback. This is safe at map-load time because
`loadMesh` reads the ZMS header min/max **eagerly**, independent of lazy geometry
loading, and `loadVisible` builds each part's OBB before the object is ever inserted
into the scene.

Things that will bite:

- **The client now imports a new engine export, so `rosenext.exe` and `znzin.dll` must
  be deployed as a pair.** A new exe against an old DLL will not start. `scripts/ab-build.ps1`
  exists for this constraint.
- **Mesh units depend on the ZMS version.** `load_mesh_minmax` applies `ZZ_XFORM_IN`
  (x0.01) for version < 7 only, so v7/v8 headers are metres and v6 headers are already
  cm. We ship 22 v6 meshes.
- `ViewCullingFunc` tests only **four** frustum planes (near, far, left, right — never
  top or bottom), so vertical FOV culls nothing and the commented-out z comparisons in
  `CompareSizePath2Obj` are not worth restoring on their own.
- A narrow residual remains: an object that fits inside its patch's 10 m footprint but
  towers over local terrain never gets `ExPatchEnable` and is still culled by a
  terrain-only z. See the doc for why the obvious one-line fix is insufficient.

`scripts/audit-zsc-bounds.py` is the verification tool: read-only by default, it
re-derives the correct box from ZMS headers plus part transforms, proves the axis-scale
signature per file, ranks objects whose geometry escapes their stored box, flags boxes
that are corruptly *over*sized, and reports missing mesh files. Run it after any
`import-*.py` that appends ZSC objects. Full record in
[doc/zsc-bounding-boxes.md](doc/zsc-bounding-boxes.md).

### Depth Buffer Precision (Engine)

The device used a **16-bit depth buffer** (`D3DFMT_D16`, hardcoded), and the avatar
camera's near plane is **1 m** against a far plane of 800 m (`LIST_CAMERA` columns 5
and 6, multiplied by 100 into cm by `ApplyCameraOption`, then by `ZZ_SCALE_IN` into
engine metres). Resolvable depth separation is `z^2*(f-n)/(n*f*2^bits)`, which at 16
bits is 3.8 cm at 50 m, 15 cm at 100 m and **61 cm at 200 m** — so any two surfaces
mounted closer than that collapsed into one depth bucket and z-fought. On screen it
read as black bands crawling across a distant object and resolving cleanly as you
walked in, because the loser of the fight is usually an unlit interior or backside.
It did not reproduce in the xadet map editor, which is XNA and defaults to Depth24.

`initialize()` now probes `D24S8 -> D24X8 -> D16` with `CheckDeviceFormat` +
`CheckDepthStencilMatch` and stores the winner in `depthstencil_format`. 24 bits is
256x finer, which pushes the onset past the far plane for any realistic mounting gap.

Things that will bite:

- **The near plane is the whole story; the far plane is nearly irrelevant.** With
  `f >> n` the expression collapses to `z^2/(n*2^bits)`. Pulling the far plane from
  800 m in to 250 m changes precision by 0.4%; raising the near plane from 1 m to 5 m
  improves it 5x. Reach for `n` or for bit depth, never for `f`.
- **Only the log tells you which format you got.** `r_d3d: depth-stencil format = N`
  — 75 is D24S8, 77 is D24X8, 80 is the old D16. A probe that silently falls back
  looks exactly like a fix that did not work. Same trap as the D3D9Ex toggle.
- `DEPTH_STENCIL_FORMAT` is now only the fallback seed. Every consumer reads the
  member `depthstencil_format`, including the offscreen z-surface in
  `restore_device_objects()` — that site used the macro directly and would otherwise
  have silently disagreed with the device.
- The FSAA check validates the sample type against the **backbuffer and the depth
  format**. Checking only the backbuffer was harmless while the depth format was a
  constant and is not once it varies: a mismatch fails device creation outright
  rather than degrading to no FSAA.
- Nothing in the engine touches the stencil buffer (no stencil render states, `Clear`
  never passes `D3DCLEAR_STENCIL`), so D24X8 is as good as D24S8. Both are probed
  because driver support for the two is not identical.
- Force the old buffer for A/B testing with `[VIDEO] DEPTH24=0` in `rose-next.ini` or
  `ROSE_NO_DEPTH24=1` in the environment — and confirm via the log.
- There is **no depth bias anywhere**. `zz_renderer_d3d::set_depthbias` is declared
  and defined but never called, and would not work if it were: D3D9's
  `D3DRS_DEPTHBIAS` takes a float bit-pattern, so its `int` parameter turns any small
  value into a denormal ~= 0. Do not reach for it to paper over a z-fight.

Which assets were affected: the failure needs two mesh parts of one object stacked
closer than the depth resolution. The recognisable family is shop signs, statues, and
the `road01`/`road01top` overlay pairs — that naming convention is the real tell, and
Junon Polis has the most of them.

A one-off scan for part pairs whose world AABBs overlap widely on two axes and by
under 25 cm on the third flagged 70 of the 14618 map objects. **Treat that as
corroboration for why only a few assets showed the artefact, not as a predictor**, and
do not rebuild it as a tool: an AABB overlap is not a surface separation (the boxes of
a concave part overlap where the surfaces do not), the thresholds were chosen to fit
the reported case rather than derived, and at 24 bits the separation that still fights
is under ~0.3 cm at any distance we draw — two orders of magnitude below what that
scan measured. If a similar artefact ever survives the format check in the log,
measure real mesh-surface separation; the AABB proxy will mislead you.

To confirm a suspected z-fight from data alone, with no rebuild:
`scripts/set-camera-near-plane.py` raises the near plane across all six `LIST_CAMERA`
rows (`--dry-run` / `--verify` / `--restore`). Precision scales with `n` but onset
*distance* only with `sqrt(n)`, so 1 -> 5 moves the artefact out ~2.2x rather than
removing it — a partial retreat is the confirming signal, not a weak result. The
follow camera's minimum distance is 1.0 m, so a 5 m near plane clips the avatar at
full zoom-in; that is expected, not a second bug. It writes no sidecar next to the
STB on purpose, since `pack.rs` would bake one into the `.vfs`.

### Object Lightmaps Are A Gutterless Atlas (Engine)

Each map-object *part* gets one cell of a shared lightmap texture — `OBJECT_128_0.DDS`
is a 4x4 grid of 128 px cells — and `SetLightMap` addresses it with a UV transform
applied in the vertex shader (`(uv + cell_xy) / grid_n`). There is **no padding between
cells**, so mipmapping, which knows nothing about the grid, would blend a part's
lighting with its neighbours' at low enough mip levels.

It cannot happen, and the reason is one line of Lua: `data/SCRIPTS/INIT.LUA:33` calls
`setMipmapLevel(3)`, which caps every texture at three mip levels. A 512 px atlas only
ever gets 512 -> 256 -> 128, and across every atlas we ship the smallest cell stays at
8x8 texels — bleeding needs cells under about 2. **Grepping `src/` alone says the
opposite**, because the DDS files do carry full mip chains down to 1x1 and the C++
defaults do not cap anything; this is the same trap as `setLazyBufferSize`.

So: treat `mipmap_level = -1` (load the file's full chain) as unsafe for lightmapped
map objects. `setDisplayQualityLevel` levels 3 and 4 set exactly that — level 5 escapes
it only by disabling lightmaps outright. If it ever did appear it would be a flat,
uniform brightness shift over a whole part with neighbouring parts of the same object
drifting out of agreement, never bands and never a sharp onset; it is also
self-limiting, since the mip level tracks screen size and a cell only falls under a
texel once the part is a couple of pixels across.

### Missing Assets Must Degrade, Not Kill (Engine/VFS)

An asset referenced by the data but absent from the baked `.vfs` used to be **fatal anywhere in the game** — four independent defects sat on that one path, each masking the next. All are fixed; the contract now is *a missing file logs once and the object renders without that part*. Keep it that way:

- **Never pass a string-ish class through `ZZ_LOG`'s varargs.** `zz_slash_converter`'s first and only member is `char _str[ZZ_MAX_STRING]` and its `operator const char*()` applies at ordinary call sites but **not** through `...`, so `ZZ_LOG("%s", converter)` copies the buffer onto the stack and `%s` consumes the first four *characters* as a pointer. Always `.get()`. (`zz_string` survives only by luck — it stores a `char*` first.)
- `zz_vfs_pkg::open` must null-check `fp_` **before** using it. `VOpenFile` legitimately returns NULL for a file in neither a package nor on disk, and `zz_assertf` is compiled out in release.
- A failed load must be **recorded**, not retried. `zz_mesh::load` sets `load_permanently_failed` (and `set_path` only clears it when the path actually changes, since `loadMesh` calls `set_path` on every attempt). `CFileLIST::Get_DATA` sets `tagFileDATA::m_bLoadFailed` — that covers motions and materials, but **not meshes**: `loadMesh` always hands back the spawned node, so `CMeshLIST::Load_FILE` reports success even for a file that will never load. Without the engine-side flag a single missing mesh produced 2.26M retries and a 447 MB `error.txt`.
- `zz_manager` must **drop** a terminally failed node, not re-queue it. `zz_node::is_load_terminally_failed()` (overridden by `zz_mesh`) distinguishes "file is missing" from "not ready yet"; without it `update()` pops and re-pushes the node every frame for the life of the process, `update()` never hits its both-lines-empty early return, and since `push()` does a linear `find()` the cost is O(n²) per update in the number of missing meshes.
- `zz_manager::update`'s entrance loop also bounds failed re-inserts per update. The failure branch re-queues without decrementing `entrance_time_accumulated`, so an unloadable node otherwise spins forever *within a single update*. Note this only became a *hard* freeze once the retry throttling above was fixed — removing accidental throttling can expose a latent spin.

### A Missing NPC Row Must Degrade, Not Kill (Client/Server)

The sibling of the rule above, on the data side. Six AI action types carry a
monster id as a `WORD` at offset 8 — 09 `Change_CHAR`, 10 `Create_PET`, 18, 20,
36, 37 — and an imported `.aip` routinely names monsters that were never
imported with it. The summon actions were always safe by accident
(`CZoneTHREAD::RegenCharacter` rejects an unknown id), but **`Change_CHAR` had no
guard on either side** and crashed the client. The 2026-09-12 Karkia session:

- `kak_ghost_cemetery.aip` (NPC 2731 "Ghost Seed", summoned by the whole Burned
  Forest roster) does `Change_CHAR` → 2734-2738, all **blank rows** in our
  `LIST_NPC`.
- Client `CObjMOB::Change_CHAR` calls `DeleteCHAR()` and *then* `Create()`.
  `CreateCHAR` returns at its part-count check, so the object stayed alive with
  **no engine model node** — invisible, unclickable, and logging
  `interface: getVisibility() failed` every frame.
- `CCharMODEL::DeleteBoneEFFECT` took `CEffect**` **by value**, so
  `SAFE_DELETE_ARRAY` nulled only the local copy and left `m_ppBoneEFFECT`
  dangling. Invisible on the normal path because `CreateCHAR` reassigns it a few
  lines later — but a *failed* `Create()` never does. Zone teardown then walked
  freed memory and freed the array a second time.

Things that will bite:

- **Heap corruption produces no crash dump.** It fail-fasts
  (`STATUS_HEAP_CORRUPTION`) without unwinding, so `SetUnhandledExceptionFilter`
  is never consulted and `CrashHandler` wrote nothing. A vectored handler now
  catches the three fail-fast codes; anything else is handed straight back,
  because a VEH sees every first-chance exception including ordinary handled ones.
- **`NPC_NAME` is NULL on the server and `""` on the client** — `STBDATA::get_cstr`
  returns `nullptr` for a blank cell, while the client goes through
  `CStringManager`. A guard written as `if (!NPC_NAME(i))` is correct server-side
  and useless client-side.
- **`error.txt` accumulates across sessions and is buffered**; `client.log`
  flushes per record. Read `client.log` first — here it named the exact object
  (`client_idx 1217, type 7, char_no 2735`) and stopped mid-`FreeZONE(131)`,
  which located the crash. `error.txt` only had 434 subject-less engine lines.
- Count broken *objects*, not log lines: one object spams every frame.

`scripts/audit-ai-monster-refs.py` is the data tool — read-only with
`--dry-run`/`--verify`, strips the dead action records otherwise, and has a
`--selftest` that proves the container rewrite is byte-identical across all 509
`.aip` before touching anything. Backups go to `build/ai-monster-refs/`, **not**
beside the `.aip`, because `pack.ps1` hard-errors on a `.bak` under `data/`. Run
it after any `import-*.py` that brings in AI files. It found 278 dangling
references in 45 files: Oro (2236/2237, 3001-3003), Karkia's ghosts and Flower
Garden, and three pre-existing retail ones.

**The same rule holds for skills.** AI action 24 carries a `short` skill id at
offset 10 and nothing validated it either: RoseZA's `OR_THORNIE.AIP` (Fearsome
Terrasaurus King) casts 3603 "Charge" and 3604 "Fireball", both blank rows in our
`LIST_SKILL`. The server broadcast the cast, `Skill_START` switched on
`SKILL_TYPE 0` and did nothing, and every client played the boss's casting
motion for nothing — which also replaced the attack motion of a swing the server
had already applied, so the client discarded that hit and the killing blow
presented death from a bar ~1000 HP too high (2026-09-14). `F_AIACT24` now
refuses a blank/out-of-range skill with a once-per-id warning, the client
presents a self-pre-empted swing instead of folding it (client `CLAUDE.md`,
"Self-pre-empted swings"), and `scripts/audit-ai-skill-refs.py` strips the casts
(same CLI and backup scheme as the monster audit; backups in
`build/ai-skill-refs/`). Nine file/skill pairs, 16 records, in six files. The
docstring records what each id is in RoseZA/667 so a later skill import can
`--restore` first and put the casts back. `import-oro-667.py` step 3h checks that
a cast *animates*, not that the row exists. **The proper fix is
`scripts/import-monster-skills.py`** (first used for this boss: Charge 3603 +
Fireball 3604, with FILE_EFFECT 1881-1884, LIST_EFFECT bullet 476 and eight
`.eft`/`.ptl` files): it resolves the whole chain a monster skill needs, writes
rows **in place at the source index** because our effect/sound/bullet tables are
the same lineage as RoseZA's (it refuses if an index is occupied by something
else), and **does not copy `SKILL_POWER`** — RoseZA's 3500/2000 would one-shot at
our stat scale, our own monster attack skills run 25-100, and for a 2900-ATK
boss the weapon formula floors at ~1400 regardless of power, so both use the
magic formula. The first cut (450/350, sized on balance-sim's synthetic Knight)
measured 2x too hot on the real tester (6.4 damage per power point); they are
now **230/190**, which landed Fireball at 1436-1447 on a 6102-HP character.
Sequence: import → `audit-ai-skill-refs.py --restore` → `audit-ai-skill-refs.py`
again. Second use: Nigaki's Voltage Jolt (871, `--skills 871`) — **Karkia's AI
is Jrose's, so its skill ids are Jrose's** (RoseZA's 871 is a different row);
the row is the Mage player skill, so the importer's per-skill `clear` list
blanks its learn-tree columns and its STL key (which would alias one of ours).
Every effect/bullet/sound index already matched here and the chain was present.
**The quiet failure is an id that is occupied here by a different skill**, which
the blank-row check cannot see: Nigaki also cast Jrose's 923 (rank 3 of the
Cleric's ally Heal, type 11) and our 923 is the player's Healing (type 10,
self) — the Flower Garden's Nigakis spam-cast it on each other with a spell
sound and never fought back. The audit now maps an AI file to its source dump by
filename prefix (`kh_`/`kak_` → Jrose, `or_` → RoseZA) and flags a cast whose
`SKILL_TYPE` differs between the dump's row and ours (the Karkia importer's own
ports and re-points are allowlisted in `DELIBERATE`); its `--remap
FILE.aip:OLD=NEW` re-points casts, and the importer's per-skill `dest` puts a
colliding row at the table's tail (Heal Ally at **7012**, `set={21:16, 22:370}`
because Jrose keeps the ability in its columns 89/90). The Devourer's 3613 was
the other collision (RoseZA long-range damage vs our Karkia Stun port) and is
stripped. Mukuroji's 30-per-tick "poison" is its retail burn (3050 → LIST_STATUS
58 Flame Heat), not a defect. **The third failure class is a cast that can never
present itself**: the client plays CHR slot `nMotion` to cast and `nMotion+1` to
release, and a projectile skill launches only from frames 24/34 (or 26/25) of
the release clip. Orgeid's Jrose CHR held the event-less casting clip in both
slots (bolt never fired, damage landed on a later melee frame with no visual,
status payload timed out); Mukuroji's release is the pig attack clip (frames
21/31). The audit **warns** about these on every run and never strips them —
the fix is a CHR slot (`CHR_MOTION_OVERRIDE` in `import-karkia.py`, applied
without a `--stage 3` by `scripts/fix-chr-skill-slots.py`); `--strict-motions`
makes them fail `--verify`. Current list: Mukuroji 2539 (kept aside, its donor
AI and model disagree) and the seven nameless, unspawned `sur_mon_s1.aip` rows
944-959.
**The fourth failure class is an AI authored against a slot layout the model
does not have.** Grand Master Devourer 2226 (third importer use: 3609 Dispel
Buffs, 3610 Area Slow, 3611 Stun Blast, RoseZA's 3613 Range Attack at **7013**
because ours is Karkia Stun) casts on nMotion 7 and 9, but its model's clip
pairs sit at 6/7 and 8/9 — with our cast = `nMotion` / release = `nMotion+1`
rule (client `CObjMOB` and server `CObjNPC` agree; 1498 of 1565 shipped casts
follow it) the boss released on an event-less charge clip or on no clip at all,
and its self-buffs on 2 released on the hit clip. A parked payload with no
action frame is not lost, it is *folded silently* after the 3 s abandon grace
(`ProcTimeOutEffectedSkill`), so the failure reads as damage with no cast. The
fix is the AI, not the CHR: `audit-ai-skill-refs.py --remotion FILE.aip:OLD=NEW`
(7=6, 9=8, 2=6 here), recorded in the manifest like `--remap`; `--restore
--only FILE.aip` undoes one file without reverting every other file's strip and
remap. Two more data traps from that kit: **RoseZA/667 author a skill's status
in column 88/90**, which our 87-column table never reads (a verbatim copy is a
stun that does not stun — the importer's `set` puts the id back into column
11, and a slow also needs `AT_SPEED` 23 in 21 and a rate in 23, house 30-70%);
and Stun Blast, like the source, has no success ratio, so the stun always lands
when the event fires. The audit's release-clip warning now covers every cast,
split into *projectile* (bullet never fires) and *payload* (resolves silently
~3 s late); ~110 retail self-buffs are in the payload list and are left alone.
First test (2026-09-14): the four imported casts never rolled — they live on
the *attack-move* pattern (evaluated only while the boss chases) behind 25/8/8/5%
rolls and extra gates (a buff on you; a second attacker; an enemy in reach) —
and what read as "a spell with no status" was the boss's when-damaged
self-casts 3596/3597, the same RoseZA rows imported nameless by the old Oro
import with the column-88 status lost; re-imported over them (`overwrite`),
which also repairs the Eldeon/Karkia casters sharing them. **Eldeon's skill
rows are ruff's, not RoseZA's** (byte-identical to the ruff dump, an older
authoring; ruff's LIST_STATUS is our numbering), so a row that "disagrees"
with RoseZA's column 88 is usually doing what ruff meant, just differently —
policy (2026-09-15): keep what works even where it differs, fix what would
bug, fix what makes no sense. Eight rows qualified and are corrected in place
by the importer's `patch` mode (name + status + ability columns only, the
balance passes' damage columns untouched): a self-buff that muted its own
caster (3588), two self/area casts with no status at all (3593, 3598), and
five "damage + stun" rows with no stun (3551, 3572, 3582, 3595, 3527). 3572 is
shared by the Ikaness Engineer and Karkia's Murilos, and a stun on a fast,
numerous spider is a nuisance — so `patch` + `dest` copies our row to **7014**
with the stun for the Engineer (`--remap ed_icanes6.aip:3572=7014`) and the
Murilos keep the plain row. EZ01 validated in game 2026-09-15; EJ02/EJ03 rows
applied, pending a fight. Details and what was deliberately left alone: the
importer docstring.
**The fifth failure class is a gate nobody can pass**: even at a 100% roll
(`--rechance FILE.aip:SKILL=PCT`, for testing) the two damage casts never
fired, because their condition 02 ("N enemies within D m with level diff in
[lo, hi]") is authored as [100, 100] — our server reads it through the 2004
`short nLevelDiff/nLevelDiff2` layout, and a target exactly 100 levels below
the boss does not exist. RoseZA's server evidently read that as "any". Fixed
with `--rewindow FILE.aip:SKILL=LO,HI` (-100,100); the audit warns about any
cast behind a lo >= hi window (only these two in the tree; 18 more such
windows gate retail movement). Also: a pattern's events are first-match-wins,
so a 100% event starves everything after it — bump one at a time. All four
casts plus the self-casts validated in game 2026-09-14: bolt ~1200 with a
real projectile, Stun Blast ~820 with the stun, slow and dispel with icons.
The last stripped casts — Inguz 654 (3044, an area stun), Penguin
Artillery 1458 (2980) and Gangster Pangs 1456/1457 (2979), none spawned — are
imported too (2026-09-15, powers re-based by the casters' ATK), so nothing is
stripped for a missing row any more. Mini-Devourer 2225 casts 3042 from a
model with no skill clip at all (slots 0-5); with no 3D artist, its casts are
removed (`--strip or_minidevourer1.aip:3042`) and it fights with normal attacks. Two client rules came out of validating the kit: a remote caster's queued
skill command must be validated on `GSV_SKILL_START` (a mob's second cast was
being deleted, its lethal projectile then died by the 6 s timeout), and a lethal
legacy `GSV_DAMAGE_OF_SKILL` payload arms pending death at receive (else the
avatar's swings in the 2 s before the caster's action frame are silent instead
of MISS). Both in client `CLAUDE.md`.

### Debugging a Client Crash or Freeze

The client has **no unhandled-exception filter and no minidump writer**, so a crash leaves `error.txt` ending with a clean `log: end.` and nothing else. Use `scripts/debug-client-crash.ps1` (servers up first): it hash-verifies `bin/<config>` PDBs against the deployed binaries, forces windowed mode, restores `rose-next.ini` afterwards, and writes `!analyze -v` + all thread stacks + a full `.dmp` on the access violation.

- cdb has **no working-directory switch** and the debuggee inherits the caller's, so it must launch from the game dir — otherwise the client can't find `rose.vfs` and exits early, looking exactly like "it didn't crash".
- For a **freeze, don't kill the process**: `cdb -pv -p <pid>` attaches non-invasively and works even with cdb already attached.
- The deployed `triggervfs.dll` does not match `bin/release`, so frames through it resolve to nonsense (`VGetVfsNames+0x…`) — disassemble the caller rather than trusting the symbol.
- **`client.log` survives a crash; `error.txt` does not.** The engine log is buffered, so a hard crash loses the whole session and the file still ends at the *previous* run's `log: end.` — which reads as "it never launched". The Rust-side `client.log` flushes per record, so read it first to see how far startup actually got.
- **A crash right after a class-layout change is a stale-build artifact until proven otherwise.** Adding a member to a widely-included header (`zz_node.h` is the base of every engine object) after an *interrupted* build leaves some objects compiled against the old layout. Kill stray `cl`/`link`/`mspdbsrv`, delete `build/<config>`, rebuild serially before debugging anything else.

### Terrain Streaming Performance

Chunk-display hitches are **resource creation at first render**, not chunk file I/O. The client `CLAUDE.md` has the full picture; the two things to know before touching it:

- **Measure lead time, not queue depth.** Frames between a resource being queued and being force-loaded is what tells you which fix applies. Terrain meshes measured **1 frame** (no amortiser can help — cap the inserts, `[VIDEO] TERRAIN_INSERTS_PER_FRAME`); textures measured **200-300 frames** (the amortiser had slack and wasted it — `[VIDEO] LOAD_BUDGET_US`). Applying either fix to the other problem does nothing.
- Diagnostics are opt-in: `[VIDEO] STREAM_SPIKE_LOG_MS` (0 = off) plus the `MapIO:`/`Flush:` debug-HUD rows and `/perfreset`.
- **`STREAM_SPIKE_LOG_MS` only fires on streaming time**, so a hitch from any other phase writes nothing and is indistinguishable from a smooth frame. `[VIDEO] FRAME_SPIKE_LOG_MS` (0 = off) triggers on *total* frame time and logs that frame's own phase split (`netin/logic/scnupd/shadow/render/ui/present/oth` + the logic sub-slots + the flush counters), which is what names a non-streaming hitch. Reach for it first; the streaming log narrows down what it finds. Run with `VSYNC=0` while hunting, or the vsync wait in `present` masks everything.

### Shared Data Types
`src/common/shared/` contains game data structures (items, quests, inventory, economy) used by both client and server. Changes here affect both sides.

### Item Encoding And Package Items
Item headers are shared wire data between client and server. `tagBaseITEM` uses a 5-bit item type plus an 11-bit item number so item IDs above 1023 (for example use-item boxes `10:1060`-`10:1062`) round-trip correctly. The created flag is server-only state on `tagITEM`; do not put it back into the packed 16-bit header or the client will decode high IDs as wrapped lower IDs (for example `10:1060` becoming `10:36`).

When creating items from explicit type/id pairs, use the type/id initializer instead of the legacy `type * 1000 + id` packed integer format. The latter cannot represent item numbers above 999. This matters for `/item`, package rewards, and any code path that spawns or grants modern high-numbered use items.

Use-item class `322` is a package box: the value in `LIST_USEITEM.STB` `ADD_DATA_VALUE` selects a server-side reward package. Unknown package IDs should fail without consuming the box so missing package mappings are visible and recoverable.

### Buffs And Passives Are Percentage-Based

`LIST_SKILL.STB` carries every ability effect in two columns: a **flat** value
(`SKILL_INCREASE_ABILITY_VALUE`, game col 22/25) and a **percentage**
(`SKILL_CHANGE_ABILITY_RATE`, col 23/26). Our buffs and passives now use the
percentage column — flat values were sized for a level-100 cap and decayed to
irrelevance by level 240 (Power Support's +70 ATK is 19% of a level-100
character and 7% of a level-240 one). Converted by
`scripts/convert-buffs-to-percent.py` (idempotent, sidecar,
`--dry-run`/`--verify`/`--restore`); its docstring is the record of what changed
and what was deliberately left flat.

Things that will bite:

- **A percentage must be taken off the *pre-buff* stat.** `Get_SkillAdjustVALUE`
  calls `Get_BaseAbilityValue`, not `Get_AbilityValue`/`Get_DefaultAbilityValue`.
  The current-value accessors already include the running buff, and
  `StatusEffects::IsEnableApplay` rejects a recast only when it is *weaker*, so a
  percentage off the current value compounds on every recast and settles at
  `rate/(1-rate)` — a declared +30% delivered +43%, +50% delivered +100%, and
  >=100% grew until the `(short)` cast overflowed. Keep the server
  (`CObjAVT::Get_BaseAbilityValue`) and client (`CObjUSER::Get_BaseAbilityValue`)
  lists in sync or the two sides disagree on a buff's magnitude.
- **The two columns follow opposite rules.** Passives are either/or
  (`InitPassiveSkill` / `Skill_LEARN` do `if (RATE) … else FLAT`, so a non-zero
  rate makes the flat value dead data); buffs are additive
  (`Get_SkillAdjustVALUE` sums both terms, so a leftover flat applies *as well*).
  Always zero the flat column when writing a rate.
- **Heals must stay flat.** `Get_SkillAdjustVALUE` resolves `AT_HP`/`AT_MP` to
  *current* HP/MP, so a percentage heal scales with what you have left — useless
  exactly when you need it. `AT_MAX_HP` is the one that means max HP.
- **HIT is deliberately still flat.** Accuracy is a cliff (see the level-gate
  section below), and a percentage hands *less* HIT to the low-CON builds already
  pinned at the 7% floor.
- Passives are re-derived from the table on load (`InitPassiveSkill` rebuilds
  from zero), so a data change needs only a server restart, no migration.
- `Get_BaseAbilityValue` is **virtual on `CObjCHAR`**, the base of every character
  object on both sides. Touching it is a vtable-layout change in a widely
  included header — clean-rebuild `client` and `sho_gameserver`, never
  incremental (see the class-layout warning under Common Pitfalls).

Full measurements and the rest of the balance plan are in
[doc/balance-analysis.md](doc/balance-analysis.md); `scripts/balance-sim.py`
re-derives every number in it against the live STBs.

### Monster Balance And The Level Gate

Combat math lives in `src/common/calculation.cpp` (server-only, behind `#ifdef __SERVER`). Two properties dominate how hard content feels, and neither is obvious from the numbers in `LIST_NPC.STB`:

- **The normal-attack gate is level-proportional.** `Get_SuccessRATE` discards an attack outright when `(player_lv + 10) - monster_lv * kLevelGateScale + rand(1..50)` is non-positive. Because the monster term is *scaled*, the required level surplus grows with absolute level — at the original 1.1 it was ~2-3 levels in Luna, 6-10 across Eldeon, and 20+ in Oro, where it exceeded our own 240 character cap (Gates of Muris wanted 243; the level-240 bosses wanted 254). It is now **1.05**. Anything that reads as "I can't hit this" is usually this gate, not accuracy — check the level difference before touching HIT/AVOID.
- **Skills deliberately use a gentler, non-proportional gate** (`Get_SkillDAMAGE`): weapon `lv + 20 - mlv`, magic `lv + 30 - mlv`. A level-140 raider lands 0% of auto-attacks on a level-173 monster but ~66% of skills. Casters therefore stay effective at a level deficit where auto-attacks stop connecting entirely — that asymmetry is intended, keep it.

Also worth knowing: **damage is proportional to `(ATK - DEF + 250)`**, so a monster whose DEF approaches the player's ATK sits on a damage floor — the fight gets long *and* reads as though the hits do nothing, and small gear changes swing the result wildly because the two terms nearly cancel. And `Get_DropITEM` returns false once `player_lv - monster_lv >= 10`, so lowering a monster's level to make it easier can silently kill its drops.

Idempotent balance passes correct the data, each with a sidecar next to the STB and `--dry-run` / `--verify` / `--restore`. **Re-running them has order dependencies**: the DEF/RES pass looks up the trend at a monster's *current* level and consults the boss sidecars to identify bosses, so if a level or the boss set changes, restore and re-apply DEF/RES afterwards; `rebalance-oro-bosses.py` changes HP that `rebalance-exp-rewards.py` keys on, so **bosses before EXP**. Then re-verify **every** pass, not just the one you touched: the Karkia and Eldeon passes recompute their targets from a trend fitted on the live table's level 60-199 rows, and both now exclude Oro's id band 2100-2399 (the Shadow Ghost ladder sits at 183-219) and 3001-3003 (event summons with placeholder stats) — any future import into that window needs the same exclusion or every verify drifts by a few points.

- `scripts/rebalance-oro-667.py` — the 667-build Oro (see the section below): level bands per zone, HP/ATK/HIT/AVOID onto the sub-200 trend with the zone spread square-rooted and capped, bosses by hand, the Shadow Ghost ladder. Writes `LIST_NPC.oro667-bosses.json`. Replaced `rebalance-oro-accuracy.py`, whose factor was fitted to RoseZA's scale.
- `scripts/rebalance-karkia.py` — Karkia levels/HP/ATK + `karkia-bosses.json`.
- `scripts/rebalance-endgame-curve.py --stat def|res` — caps level-200+ DEF/RES at the trend fitted from levels 60-199. Bosses (three sidecars) get `BOSS_MULTIPLIER` (1.2).
- `scripts/rebalance-oro-bosses.py` — boss HP to 10x the HP trend and level to the 240 cap, scoped from the Oro REGEN lumps by HP column. Since the Oro pass budgets its own bosses under that threshold it now only reaches `EXTRA_BOSS_ROWS` (Luna's Behemoth King).
- `scripts/rebalance-eldeon-outliers.py` — two hand-picked monsters that escaped the passes above through scope gaps.
- `scripts/rebalance-exp-rewards.py` — the EXP column from the levelling pace.

Their docstrings carry the reasoning and record what was deliberately left alone (Luna's Astarot King and Gem quartet, the big-HP piñata field monsters, unspawned duplicate rows with billion-HP columns). Since `data/` is gitignored, **the script is the only committed record of the change** — put new reasoning there, not just in a commit message.

### Oro Is The 667 Build's Oro (2026-09-13)

The RoseZA-era Oro was removed (`scripts/remove-oro.py`, everything moved to `build/oro-removal/`, `--restore`) and the 667 test client's version imported (`scripts/import-oro-667.py`: `--selftest --dry-run --verify --revert`, undo in `build/oro-667/`). Ten zones: 14 Colosseum (walkable, empty), 71 Muris, 72 Portal Room, 73 Portal Temple, 78/79 Wasteland, 80 Oasis Shrine, 81 Ruins Path, 83 Golden Ring (`ODGR01`), 85 Fossil Sanctuary (`ODFS01`). 667 itself deleted the old Wreckage, Golden Ring 01-03 and Gates of Muris. **No quests** by decision; the fate system, the Jones/Nova travel legs (`QP401.QSD` now holds only those two triggers) and the Muris shops stay. Not yet validated in game.

Things that will bite:

- **667 ships no `.aip`, no `FILE_AI.STB`, no `.CON`, no `ulngtb_con.ltb` and no `.MOV`.** Its AI-type column indexes RoseZA's `FILE_AI`, and numbers under ~2100 (ghosts 47, lizards 91) do not line up with our rows — the importer resolves AI **by filename** through a 667 → RoseZA source chain. The 43 Oro dialogs, their text, the `OR_*` `.aip` files and the shared folders' `.MOV` grids are RoseZA's and were deliberately **kept in place**. `scripts/import-oro.py` is no longer run; it is the codec library every later importer loads. Its dialogs are **`.CXE`, which is not encrypted**: `CXE1000` magic, then blocks of an instruction stream (set message / set option / jump / jump-if / close), the strings **embedded per language** (English and Portuguese) and the Lua as plain **source** — brett19's rosebrowser `cxe.js` is the reference reader. So 667's dialog text *is* recoverable (Bryll `NPC2100`, Alana `EM71-007`, and newer versions of the rest) through an offline CXE → `.CON` + LTB + QEX1 converter; the Lua dialect and the jump-graph → node-tree mapping are the two things to confirm first.
- **667 stores attack speed (`LIST_NPC` game col 14) in a different unit** — 3300 where RoseZA and our retail rows hold 40-110, and 8000-10000 on the critters. Copied verbatim it plays as a 33x attack rate. The importer re-bases it from RoseZA's row or a family sibling (`ATK_SPEED_DONOR`); every other column is at ratio ~1 between the two dumps except the stats the balance pass rewrites. New textures need `add-dds-mipmaps.py` (the importer records what it created in `build/oro-667/import-manifest.json`); Oro's lightmaps are mipped as of 2026-09-14, same scoped opt-in as Karkia's.
- **667's `NPC_TYPE` codes are composite** — 42 Leader-Guard, 53, 72 King-Guard, 75 King-Ranger … — and `CNameBox::DrawTargetMark` uses that column *directly* as a sprite index into `TARGETMARK.TSI` (36 sprites), so those monsters showed no mark beside the focus bar. The importer folds them to the units digit (the base class); the server only compares the column against 900. Bare-handed monsters present their hit through `NPC_HAND_HIT_EFFECT` (game col 33, a `LIST_EFFECT` row): 667 left it blank on the Golden Scarabs and the Hungry Desert Scavenger, which landed no visible impact; 403 is the retail default and the importer fills it.
- **Walk the summon closure at import time.** Nineteen Oro monsters `SummonMaster` Shadow Ghosts 2236/2237 and Ghost Seed's `ghost_m5.aip` `Change_CHAR`s the whole 2230-2239 ladder; none is in any spawn lump and all were blank here (the crash class from `audit-ai-monster-refs.py`). The importer walks `act_monster` ids transitively from the roster and imports whatever a dump has. Scope a monster as blank by **name and model**, not `occupied()`: rows 6/7 carried stray cells and were skipped by the first dry-run.
- **Ten species have AI in no dump we own** (Golden Scarab 2279-2281, Ikaness 2290-2296). `AI_DONOR` lends them ours: Ikaness ← retail Ikaness 424-430 (same skeletons), Scarabs ← the Scorpio line, which casts nothing — the scarab model has animation types 0-5 only. Donor casts are audited fatally; 667's own oddities (the Devourers cast on slots 2 and 7, as RoseZA shipped them) are reported only.
- **A lone boss point has the same slot shape as a carpet point.** ODFS01/ODGR01 are single-species carpets (`consolidate_carpet`, 60 m camps of 5, tacticPoint 100) and their 23 boss points are one species, count 1 — at **cap 1 and a 30-minute interval**. The carpet criterion requires `cap >= 2 and interval < 600`, or the kings fold into 20-second camps. Also: `*.IFO` + `*.ifo` globs double-count on Windows — the survey's 1406/890 points were 703/424.
- 667's warp rows 178-180 collide with live Karkia gates (`GATE_REMAP` → 187/188/193). Cactus 2181 is a 667 "interactive object" NPC we cannot run (147 points removed). Bryll 2100 and Alana 2121 are placed mute (dialog file in no readable dump); the twelve fate vassals speak only once a fate is chosen — by design, not a defect (`scripts/audit-oro-idle-dialog.py` is the lua4-driven survey).
- Drop columns come from RoseZA's rows (tables 773-851 reserved, empty); the 19 new species got free tables 852-870 at item rate 100. **Nothing drops in Oro** until the drop pass.

### Data Repair Tooling

Our `data/` is a translated iROSE dump with gaps; the reference dumps in `C:\Users\Thomas\Desktop\Testclients\` (QQ-iROSE, RoseZA, titanRose) are intact, so diffing a single field across all three is a fast, high-confidence way to find and fix them. All three scripts below are idempotent, take `--dry-run`, and verify after writing. `data/` is gitignored, so **the script is the only committed record of the change** — put the reasoning in its docstring.

- `scripts/fix-mob-bullet-effects.py` — restores `WEAPON_BULLET_EFFECT` (`LIST_WEAPON.STB` game col 38). Empty there means a ranged monster fires **no projectile and lands no visible hit**: the client's `Get_BulletNO()` skips `Add_BULLET`, and the server's `UsesProjectileAttackPresentation()` picks `MeleeHitFrame`, which nothing on a bow/gun motion consumes.
- `scripts/add-zone-name.py` — appends entries to `LIST_ZONE_S.STL`. A blank name above the minimap is **not** a minimap bug: the name comes from the STL keyed by `ZONE_STRING_ID`, never from the STB name column. Documents the `ITST01` layout, incl. the 7-bit varint lengths and the fact that the client ignores the per-entry offset table and reads strings sequentially.
- `scripts/check-shop-tabs.py` — read-only audit of every shop tab an NPC references, for the two ways one opens broken: **no caption** (the client resolves it through the `LIST_SELL.STB` STL key in game col 1, never from the col 0 name, so a well-named row can still draw blank) and **no stock** (all 48 slots zero). `--compare` diffs the stock count against the reference dumps, which separates "we lost this row" from "retail shipped it empty". Nine of our live tabs are nameless and twelve are itemless; rows 323/327 (Reene, Cassirin) and 386/387 (Punwell) are stocked in the references and empty here. **Never grep an STL for keys** — each key is followed by a u32 id whose low byte is often an ASCII digit (id 304 → `30 01 00 00`, and `0x30` is `'0'`), so `LSEL\d+` reads `LSEL304` as `LSEL3040` and reports a present key as missing. Parse the table.
- `scripts/fix-chr-skill-slots.py` — applies `import-karkia.py`'s `CHR_MOTION_OVERRIDE` to `LIST_NPC.CHR` without a `--stage 3`. A monster casts with the AI action's `nMotion`: slot `nMotion` casts, slot `nMotion+1` releases, and only the release clip's action frames (24/34 launch, 26 fire, 25 hit) make the skill land on screen. Orgeid (2723) had the no-event casting clip in both slots with the real release clip unused in slot 7 — inherited from Jrose's CHR, not an import artefact — so its bolt never fired and its damage showed on a later melee frame with no visual. The table lives in the importer so a re-import keeps it; backups in `build/chr-skill-slots/`.
- `scripts/fix-mob-weapon-presentation.py` — fills a **blank mob weapon row's** presentation columns (LIST_WEAPON 39 hit effect, 40 swing sound, 42 hit sound) from a donor row. A monster with a weapon presents its hits through the weapon row and the NPC-level fallbacks (cols 31/33) are skipped, so a blank row is worse than no weapon: digits, no impact, no sound. Moon Sister Inguz's staff 1130 (shared with Melendino 1473) was blank in every dump we own; it takes the Sikuku Jailer's 1143 values (2026-09-15). Only all-blank rows are touched; backups in `build/mob-weapon-presentation/`.
- `scripts/restore-warp-gates.py` — re-inserts `LUMP_TERRAIN_WARP` (type 10) objects into map `.IFO`s. `WARP.STB` and the destination `.ZON` event positions are usually fine; the missing piece is the trigger object the player walks into. Has a `--selftest` that proves the container rewrite is byte-identical before it touches anything.

Note `src/pipeline/src/pack.rs` walks the data tree filtering only *hidden* entries — no extension filter — so any `.bak` these scripts leave behind gets baked into the `.vfs`. Clean them before a bake.

### The .vfs Offset Limit (2 GB -> 4 GB)

**A `.vfs` archive cannot exceed 4 GB, and could not exceed 2 GB before 2026-08-29.** `FileEntry::lFileOffset` in triggervfs was a *signed 32-bit* `long`, so a file stored past byte 2,147,483,647 got a negative offset, the client seeked to garbage and read binary noise. It is now unsigned, which doubles the ceiling — the on-disk field is the same four bytes, only the interpretation changed.

Three things had to change together, and each failed differently:

- `FileEntry::lFileOffset` and `VFileHandle::lStartOff`/`lEndOff` are unsigned. `MapViewOfFile` already took the offset as a DWORD low + DWORD high(0) pair, so the engine's memory-mapped path needed nothing else.
- **`vfread` had a `(signed)` cast** on the end-of-file comparison that actively defeated the unsigned field, plus a `long` offset and a 32-bit `fseek`. The client opens `"r"` (plain fseek/fread) while the engine opens `"mr"` (memory-mapped) — **completely different code paths**, so verifying one proves nothing about the other. The mapped path worked as soon as the field was unsigned; the plain path silently returned **zeros** until `_fseeki64`.
- `vfseek`'s clamps must be **signed 64-bit**. In 32-bit unsigned, `lStartOff + offset` with a negative offset wraps and the underflow guard silently fails.

**Bake with `scripts/pack.ps1`** (`data/` -> `Exes/`). It now runs `verify-vfs.py` itself and fails the bake if the archive is unaddressable, and it prefers `bin/release/pipeline.exe` over the copy in `Exes/`. That default matters: `Exes/pipeline.exe` had gone **four months stale** (2026-04-06, against a rollover added 2026-08-17), so every bake ran a packer built before the size guard existed — which is the entire reason `rose.vfs` sailed past the split threshold with no `rose_2.vfs` while the code looked correct. Checking the timestamp of `bin/release/pipeline.exe` says nothing about what actually packed the archive.

Verify manually with `scripts/verify-vfs.py <game-dir>` after any bulk bake — it re-derives everything from the bytes on disk, so a packer bug cannot hide from it. `scripts/make-oversize-vfs.py` builds a sparse >2 GB archive with a deterministic payload and `vfs_buffer_tests.exe --bigtest <dir>` reads it back through the real triggervfs in **both** modes, checking content it re-derives from the file name — an independent oracle, not a comparison of two paths that share the bug.

The failure looks nothing like its cause. Whichever files happen to land past the boundary are simply the tail of the archive — when it first hit, that was `SCRIPTS\INIT.LUA`, so the client died at startup with a Lua `invalid control char near 'char(6)'` parse error followed by `assert: failed. zz_shader::check_system_shaders()`. Nothing pointed at the archive.

`pack.rs` now **rolls over to `rose_2.vfs`, `rose_3.vfs`, …** at 4.2 GB (`VFS_MAX_BYTES`; the margin below the 4 GiB ceiling absorbs the largest single asset, since the check runs before writing — it was 1.9 GB while the offset field was still signed) and hard-errors if an offset would still overflow. Both the `.idx` format (`VfsIndex::file_systems` is a list) and the runtime (`CVFS_Manager::m_vecVFS`, searched by `OpenFile`) already supported multiple archives — only the packer was hardcoded to one. **Ship every `rose*.vfs` alongside `data.idx`**, not just `rose.vfs`.

Diagnosing a suspected bad bake: parse the `.idx` FAT (`short len; char name[len]; long off,len,blk; BYTE deleted,compress,enc; DWORD version,crc`) and check for negative offsets — that is a two-minute script and it is unambiguous.

### Item Import Tooling
`scripts/import-item.py` imports an equipment item from another ROSE data dump (e.g. an evo-era private server) as a new appended ID: STB row, model ZSC object (with mesh/material dedup), ground-drop model (`--copy-field-model`), STL name/desc key, and any missing mesh/texture files. Always start with `--dry-run`; it makes `.bak` backups and verifies after writing. **`data/` is gitignored and `pack.rs` filters only *hidden* entries, so delete those `.bak`s before a bake or they end up inside the `.vfs`.** Undo a run with `scripts/remove-trailing-items.py` (trailing rows only, matched by `--name-prefix`).

**Prefer `--art-only --template-row N` for anything from an unfamiliar dump.** It takes the model (plus `--copy-icon` / `--copy-field-model`) and clones every stat column from one of *our* rows, reading no source cell at all. That is a safety property, not a convenience: item bonus/requirement columns are ability ids fed straight into `m_iAddValue[nType] += nValue` with **no bounds check** on either side (`src/client/common/cuserdata.cpp`, and the gameserver's copy). `m_iAddValue` is `int[AT_MAX]` with `m_nPassiveRate`/`m_btRecoverHP`/`m_iDropRATE` directly behind it, so a modern affix id (Jrose uses 174/175/184/185/195) silently corrupts adjacent character state instead of erroring. `--art-only` also skips the source STL, sidestepping foreign dialects — Jrose writes the legacy `I_NUM` header that our strict reader rejects. See [doc/jrose-back-import.md](doc/jrose-back-import.md). `scripts/add-item-icon.py` adds a custom item icon from a PNG (any size, auto-downscaled to a 40×40 cell) to the `ITEM1.TSI` atlas and prints the new global icon index (`--weapon-row N` also patches the STB); requires Pillow. `scripts/add-skill-icon.py` is the same tool for **skill** icons (`SKILLICON.TSI`, extension sheets `skill04.dds`+, original indices 0–506, extensions from 507; `--skill-row N` patches `LIST_SKILL.STB` col 51). Note the two TSIs use different sprite-rect conventions (item `x..x+40`, skill `x..x+39`) — each script matches its atlas. Both docstrings document the underlying binary formats — read them before editing STB/ZSC/STL/TSI by hand.

**Putting a new skill in the skill tree needs an art edit**, not just an XML node: the boxes and connectors are painted into the per-category `DEALER_*.DDS`, and `CSkillTreeDlg` has no line-drawing code at all — the XML only positions a 40×40 icon, at coordinates that are **absolute inside the dialog**, not relative to the parent node. The xml loads loose via `fopen` (never the VFS) while the DDS loads from the VFS and ignores a loose copy, so the two halves deploy differently. Recipe, coordinate system and traps: [doc/skill-tree-art.md](doc/skill-tree-art.md).

Key facts: weapon visuals come from `LIST_WEAPON.ZSC` indexed by item number (1:1 with STB rows) — the STB "model file" text column is vestigial and never read by the game. Ground-drop visuals are a separate index (STB col 10) into `LIST_FieldITEM.ZSC`. Icon indices are global sprite positions in `ITEM1.TSI` (originally 50 sheets × 169 cells = 0–8449; extension sheets `icon51.dds`+ continue from 8450). After data edits, restart servers (they cache STBs at startup) and the client.

### NPC Dialog Quest Options (.CON QEX1 Appendix)
NPC conversations are `.CON` files (`data/3DDATA/EVENT/`) whose logic is compiled Lua 4 **bytecode** — new functions can't be merged into the blob (Lua 4.0.1 rejects multi-chunk buffers). Our extension: an optional appendix after the Lua tail (`b"QEX1"; i32 len; XOR'd Lua source`) that the client (`cevent.cpp`, `QEX_APPENDIX_MAGIC`) executes into the same `lua_State` via a second `Do_Buffer`. The quest editor uses it to append quest options to an NPC's existing dialog without replacing it (`quest-editor con-append`, or the wizard's append radio). Codec + gotchas (main-blob XOR key depends on file size; menu-0 append ordering) live in `src/tools/quest-editor/src/convo.rs` and the tool's `PROGRESS.md`. `.CON` files are client-only — the server never reads them; quest authority stays in QSD triggers. Appended `.CON`s require the QEX1-aware client: ship client + data together.

## Common Pitfalls

- **Always build via the .sln, not individual .vcxproj files.** Projects depend on `$(SolutionDir)` and `$(GeneratedDirCommon)` (→ `build/gen/common/`) from `rose-next.props`. These don't resolve when building a vcxproj standalone. Use: `MSBuild.exe rose-next.sln -p:Configuration=release;Platform=x86 -t:sho_gameserver`
- The `common.vcxproj` pre-build step runs `cargo build`, so building via the solution handles Rust automatically
- Always build Rust with i686 toolchain — the entire project is 32-bit x86
- FlatBuffers schemas in `src/common-lib/packets/` must be compiled with `flatc` (handled by build.rs)
- `src/common-lib/build.rs` uses `PROFILE` env var (not `DEBUG`) to find flatc path
- Server projects link against Rust staticlib output — build Rust before C++
- Thirdparty must be built before rose-next.sln
