# Map editor overview, build/deploy, architecture, data formats

> **Provenance:** moved verbatim on 2026-09-24 from `xadet/rose-online-map-editor/CLAUDE.md` lines 1-127 (revision `84f6206`).
> Original bytes: [`xadet--rose-online-map-editor--CLAUDE.md.txt`](../../archive/2026-09-24/xadet--rose-online-map-editor--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=xadet/rose-online-map-editor/CLAUDE.md lines=1-127 sha256=a8d01bb929ae3b21204a2bfa9370749e81325bc0980b802db5c8bcb9f6a074c2 -->
# CLAUDE.md — ROSE Online Map Editor (xadet)

## What This Is

The legacy **xadet** ROSE Online Map Editor, vendored into the Rose Next Classic
workspace at `xadet/rose-online-map-editor/`. It is a standalone C# desktop app
(circa 2007) used to author ROSE map/zone data — terrain, tiles, objects, NPCs,
monsters, spawns, warps, water, effects, sounds, and event triggers.

Treat it as an isolated subproject. It does **not** share build tooling, language,
or runtime with the rest of the workspace (which is C++/Rust). The only coupling is
the ROSE *data* it reads/writes from `../../data`.

- **UI:** WPF (`.NET Framework 3.5`)
- **Rendering:** XNA 3.1 (DirectX 9 era), hosted inside a WinForms panel in the WPF window
- **Audio:** irrKlang (`irrKlang.NET2.0.dll`)
- **Platform:** x86 only, `WinExe`, root namespace `Map_Editor`
- **License:** Apache 2.0

> **Vendored, not a submodule.** This tree is a copy of upstream
> [jackwakefield/rose-online-map-editor](https://github.com/jackwakefield/rose-online-map-editor)
> at commit `7f0462e`, committed straight into this repo (Apache 2.0, `LICENSE`
> kept). There is no nested `.git` and no upstream remote — our changes can't go
> back upstream, because they target this project's data layout rather than the
> retail-era layout the editor was written for. `git log -- xadet/` splits into
> exactly two commits: the pristine vendor, then everything we changed.

## Build, Deploy, Run

Build with **VS2019 MSBuild, Release, x86**. The `irrKlang.NET2.0.dll` reference is
stale, so point `ReferencePath` at the workspace `data` folder where the DLL lives.

```powershell
& 'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe' `
  'Map Editor.sln' /p:Configuration=Release /p:Platform=x86 `
  /p:ReferencePath='C:\Users\Thomas\Desktop\Rose\rose-next-classic\data' /m:1 /v:minimal
```

**Editing source is not enough.** The user runs `../../data/Map Editor.exe`, so after
any change you must rebuild and copy the binaries into `data`:

```powershell
Copy-Item 'Map Editor\bin\x86\Release\Map Editor.exe' '..\..\data\Map Editor.exe' -Force
Copy-Item 'Map Editor\bin\x86\Release\Map Editor.pdb' '..\..\data\Map Editor.pdb' -Force
```

The editor's working directory is `../../data`. ROSE data paths come from the
STB/ZON/ZSC/IFO files and often use legacy mixed-case paths like `3Ddata`.

## Architecture

Entry flow:

1. `App.xaml.cs` — application entry. Installs three global exception handlers
   (WPF dispatcher, AppDomain, WinForms thread) that all funnel to `Output.WriteException`.
   Loads config via `ConfigurationManager`, then creates and shows the `Main` window.
2. `Main.xaml(.cs)` — the WPF main window. Hosts the XNA render surface in a WinForms
   `Panel` (`RenderPanelHost.Child`, exposed as `RenderPanel`). Wires up timers,
   menus, manipulation modes, and the right-side tool panels.
3. `Engine/Main.cs` — the XNA `Game`-style render/update loop driving everything below.

Globals live on `App`: `App.Form` (the WPF window) and `App.Engine` (the XNA engine).

### Engine manager layout (`Map Editor/Engine/`)

The engine is organized into single-responsibility *managers*:

- **`FileManager/`** — binary readers/writers for ROSE formats. This is the
  serialization heart of the editor.
  - `Data/` — `STB` (tables), `STL` (localized strings), `TileSet`, `LTB`
  - `Map/` — `ZON` (zone metadata), `IFO` (per-block objects/NPCs/events/water/collision/sounds), `HIM` (heightmap), `TIL` (tiles), `LIT` (lightmaps), `MOV` (movement/walkability)
  - `Models/` — `ZSC` (object defs), `ZMS` (meshes), `ZMO` (motions)
  - `Character/` — `CHR` (NPC/monster model defs)
  - `FileManager.cs` / `FileHandler.cs` — dispatch + low-level binary IO
- **`MapManager/`** — runtime, in-memory map objects grouped by domain:
  `Terrain/` (Heightmaps, Water), `Objects/` (Decoration, Construction, Animation,
  Collision, EventTriggers), `Characters/` (NPCs, Monsters), `Events/` (SpawnPoints,
  WarpGates), `Misc/` (Effects, Sounds, Sky). `MapManager.cs` orchestrates load/save.
- **`ToolManager/`** — interactive editing tools, one per editable object type,
  mirroring the MapManager domains. `Manipulation/` holds Translate / CursorTranslate
  gizmos; `ITool` is the common interface.
- **`RenderManager/`** — `ObjectManager`, `AnimationManager`, `TextureManager`, and
  debug `Primitives/` (Cone, Cylinder, Sphere, Radius).
- **`ShaderManager/`** — one wrapper class per HLSL effect (Height, HeightEditing,
  Object, NPC, Animation, TileRotation, SimpleColour, SimpleTexture). Compiled
  shaders ship as `.xnb` under `Content/`.
- **`CameraManager/`** — Orthographic + Perspective camera types.
- **`SpriteManager/`** — `FontManager`, `ToolTipManager`.
- **`UndoManager/`** — command pattern. Each editable type has a `Commands/<Type>/`
  folder with `Added` / `Removed` / `Positioned` / `ValueChanged` (and type-specific)
  commands implementing `ICommand`. Touching edit behavior usually means touching
  the matching undo command too.

### UI (`Map Editor/Forms/`)

- `Forms/Controls/*.xaml(.cs)` — the right-side editing panel for each tool
  (BrushTool, HeightTool, TileTool, WaterTool, DecorationTool, ConstructionTool,
  AnimationTool, CollisionTool, EventTriggerTool, NPCTool, MonsterTool,
  SpawnPointTool, WarpGateTool, EffectTool, SoundTool, plus `NPC/PreviewPanel`).
- `Forms/New`, `Forms/Open`, `Forms/Search`, `Forms/Tools/Options` — dialogs.

### Misc (`Map Editor/Misc/`)

- `ConfigurationManager.cs` — loads/validates editor config.
- `Output.cs` — logging. Every output line and all exceptions are mirrored to
  `../../data/Map Editor.log`.

### Editor-local data

- `ESTB/` — editor-only tileset helper STBs (`Table_Tileset_*`, `TileLookup_Type_*`,
  `EDITOR_System_Object.STB`) checked into this project. The editor resolves these
  from **both** `3Ddata\ESTB` (old layout) and root `ESTB` (current Rose Next layout)
  — keep both lookups working.

## ROSE Data File Reference

| Ext | Purpose |
|-----|---------|
| `STB` / `STL` | data tables / localized strings (e.g. `LIST_ZONE.STB`, `LIST_ZONE_S.STL`) |
| `ZON` | zone-level metadata, textures, spawn points |
| `IFO` | per-block objects, NPCs, monsters, events, water, collision, sounds |
| `HIM` / `TIL` | terrain heightmap / tile indices |
| `MOV` | per-tile walkability/movement |
| `LIT` | object/building lightmaps |
| `ZSC` / `ZMS` / `ZMO` | object definitions / meshes / optional motions |
| `CHR` | NPC/monster character model definitions |

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
