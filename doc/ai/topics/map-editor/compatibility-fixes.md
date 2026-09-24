# Map editor compatibility fixes already made

> **Provenance:** moved verbatim on 2026-09-24 from `xadet/rose-online-map-editor/CLAUDE.md` lines 163-294 (revision `84f6206`).
> Original bytes: [`xadet--rose-online-map-editor--CLAUDE.md.txt`](../../archive/2026-09-24/xadet--rose-online-map-editor--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=xadet/rose-online-map-editor/CLAUDE.md lines=163-294 sha256=03c2d68ca589b51132d3a2e09a828d79432285f5a2ccfc17331e671029dc450a -->
## Compatibility Fixes Already Made

- **Saving a Karkia or Skaaj map destroyed its IFOs (2026-09-23).** Every Jrose-origin
  IFO (all 141 in `KARKIA\*` and `SKAAJ\SKTOWN`) has no MapInfo lump 0, so
  `MapInfo.MapName` stayed null and `IFO.Save` threw inside `BinaryWriter.Write`.
  `FileHandler` opens for writing with `FileMode.Create`, so the first IFO was left
  as a 188-byte stub (every object, NPC, spawn and warp gone), and the exception on
  the raw save thread took the editor down with the ZON already rewritten.
  `FileHandler.Write<BString>` now writes null as empty. Both the client
  (`CMAP::ReadMapINFO`) and the server ignore lump 0, so the empty MapInfo lump the
  editor now adds is inert, like the empty object/water lumps it always wrote.
  Verified with a headless load-and-save of every map file through the editor's own
  readers and writers (all Karkia zones, Skaaj, Zant JDT01, Sunshine Coast SUM_EVENT):
  no failures, every object field and extra byte-identical, positions within 0.02 cm,
  TIL and LIT byte-identical, HIM heights identical. The one intended difference: the
  HIM trailer's per-patch height bounds, which Jrose stores as real values, are
  rewritten as the +/-FLT_MAX placeholders every retail Junon HIM already carries --
  conservative for culling, and correct after the terrain is reshaped.
- **Deleting a placed decoration/construction object misassigns lightmaps (known,
  not fixed).** LIT entries are keyed by 1-based ordinal within the block's lump and
  `RemoveAt` does not renumber them, so every later object takes its neighbour's
  lightmap; the client's `LoadLightMapINFO` also indexes `m_pObjectIndex` with that
  ordinal unchecked. Move or sink an object instead of deleting it. New objects are
  appended, get no LIT entry, and render without baked lighting.

- **A blank sky column no longer hides a map (2026-09-17).** `IsValidMap` rejected any
  LIST_ZONE row whose sky cell (editor column 8, game column 7) was empty, and the load
  path did `Convert.ToInt32` on it. The client reads that cell as an integer, so blank
  means sky 0 -- Jrose leaves it blank on 11 maps (Skaaj `LZON079`, MyRoom2, 8, 9, 36,
  73, 93, 133, 138, 140, 144) and none of them appeared in the Open dialog.
  `MapManager.SkyIndex` now resolves the row the client's way (blank/unparsable/out of
  range -> 0, with a log line for the latter two). Jrose's `LIST_ZONE_S.STL` is the old
  `I_NUM` dialect the STL reader cannot parse, so its Open list shows keys (`LZON079`)
  rather than names; the ID column is the reliable handle. Verified with a headless
  `FileManager.Initialize()` harness against the Jrose data: 100 maps listed,
  `IsValidMap(79)` true, `SkyIndex(79)` 0.
- **Movement painting (2026-09-13).** Open a map, then **Tools > Movement (.MOV) >
  Paint movement permissions**, or the **MOV** toolbar button. Left-drag paints
  5 m cells with 1/3/5/7-cell square brushes; one drag is one undo command.
  Green = allowed, red = blocked; blue/purple = missing-file allowed/blocked
  defaults; yellow previews the brush. The overlay follows HIM triangles.
  **The current game has two effective MOV states, not three:** `0` permits
  `SetCMD_MOVE2D`; every nonzero byte blocks it. Players and attack chasing do not
  consult MOV. Existing nonzero bytes are preserved until explicitly painted.
  `MovementMaps.Find` follows the server: filename `x_y` maps to server block
  `(x, 64-y)`, with MOV rows growing northwards (the reverse of HIM rows).
  The panel's **Save / generate MOV files** writes only movement files; normal
  Save includes pending MOV edits. Creating the first file also generates all
  missing blocks, preserving the server's no-MOV fallback instead of accidentally
  blocking untouched terrain. Existing partial coverage defaults missing blocks
  to blocked. Each replacement is atomic and backs up the previous file under
  `.mov-backups/<timestamp-id>/`; the whole map is not a single transaction.
  Failed writes retain unsaved edits for retry. Malformed MOV disables movement
  editing without preventing the rest of the map from opening. Closing/opening
  another map prompts for unsaved movement edits. Restart the server to apply.
  Run `tests/Run-MovementTests.ps1`: builds Release x86, checks actual MOV files
  byte-for-byte, server coordinates, coverage generation, backup/retry behavior,
  cross-block brush + undo/redo, and actual XNA rendering/state restoration.
  Passed against 1,369 map MOV files; interactive in-editor/in-game retest pending.

- **Karkia lightmap trailers and zero-height spawn previews (2026-09-12).** All 98
  Cemetery LITs end after the object records; the trailing DDS catalogue is optional
  and the game never reads it. `LIT.Load` accepts EOF there, preserves whether the
  catalogue existed on save, closes its reader on failure, and logs actual exceptions.
  All 847 Cemetery regen entries store Z=0 although ground is 5-43 m higher. Monster
  previews now sample terrain triangles for zero-height entries; explicit nonzero
  heights and stored IFO coordinates stay intact. Model bounds, inactive/empty markers,
  selection handles and radius overlays use the display position. The minimap preview
  already worked because it only needs XY. Real XNA loader checks passed Cemetery
  (847 spawns) and Spire Village (278); all 220 Karkia LITs and the Lion's Plains LITs
  round-tripped byte-identically to temporary files. Terrain interpolation, selection
  bounds and unchanged stored spawn positions passed; GUI retest pending.
- **Transform terrain relative to its block origin.** Lion's Plains (667, JPVP04)
  decoration 158 in `34_33.IFO` is the circular `m-kwangjangside` paving. Its lowest
  surface sits about 2 mm above the terrain near world coordinates (5440, 5067).
  Multiplying large terrain coordinates by a combined view/projection matrix in
  the vertex shader lost enough precision to draw the ground through the paving
  as the camera moved. `Heightmap.Draw` now supplies a block origin and a combined
  translation/view/projection matrix; both Height shaders subtract that origin
  before transforming. Stored vertices, culling, picking, brush world coordinates,
  and game assets remain unchanged. Default editor depth was already Depth24.
  Verified 2026-09-12 with actual XNA draws of the platform and underlying terrain
  at 15 camera positions, in normal and height-editing modes: up to 106,093 platform
  pixels were incorrectly covered before; zero after, against platform-only renders
  (RGB total-difference tolerance 20). Release x86 build passed; GUI retest pending.
- **Morph materials must use their STB depth/transparency flags.** Kenji's shoreline
  waves (`LIST_MORPH_OBJECT` rows 1-3) have depth testing on and depth writing off.
  The editor previously ignored those flags: transparent wave triangles wrote depth
  and cut polygon-shaped holes in the water drawn afterwards. `Objects.Animation`
  reads alpha/two-sided/alpha-test/Z-test/Z-write/blend-op from editor cells
  5/6/7/8/9/12 (game column + 1), and `AnimationManager.Draw` applies them and
  restores the caller's depth/cull state afterwards. Material-cache identity includes
  render settings as well as the texture path; distinct materials share image storage
  without sharing flags. Verified 2026-09-12 with actual XNA GPU draws of all three
  Kenji wave meshes/motions at three views: the original blocked 32,195-40,960 pixels
  of a diagnostic background plane; fixed draws blocked zero. Wave-only images were
  pixel-identical before/after. Material disposal/state restoration and ODP01/ODFS01
  terrain/scenery/NPC/monster loading also passed; user confirmed the Kenji fix.
- **Share object lightmaps by full path.** Fossil Sanctuary (667, ODFS01) has
  2,710 lightmapped part instances sharing 112 atlas textures across decoration
  and construction. Loading a DDS per part consumed about 2,247 MiB of nominal
  base texture storage instead of 70 MiB and exhausted the x86 editor while
  loading objects. `ObjectManager.LoadLightmap` caches by case-insensitive full
  path; parts retain independent UV transforms. The manager owns these textures
  until `Clear`, including textures detached from draw batches by editing/undo.
  `ClearBatch` must not dispose them; `Clear` disposes each texture once and also
  releases mesh vertex/index buffers. Tested with real XNA terrain, scenery, NPC
  and monster loads for ODP01 -> ODGR01 -> ODFS01 -> ODGR01 -> ODFS01, including
  disposal checks after clearing draw batches (2026-09-11). GUI retest remains
  separate from this loader check.
- Tileset helper STBs resolve from both `3Ddata\ESTB` and `ESTB`.
- **A bad global table no longer kills startup.** `FileManager.Add` registers an empty
  placeholder for a missing or unreadable STB/STL/ZSC/CHR and continues, and `STB.Load`
  checks the `STB` signature up front so the log names the file instead of dying with a
  bare `EndOfStreamException`. This is what foreign data sets trip over — QQ-iROSE ships
  an *encrypted* `3Ddata\TERRAIN\TILES\ZONETYPEINFO.STB` (editor-only data; the game
  itself never reads that table), which used to abort `Initialize()` and leave every
  later dictionary lookup throwing `KeyNotFoundException`. With no zone-type table,
  `GetTileSetFile` falls through to `InferTileSetFile`, so maps still load and only the
  tile brush palette is empty. The default constructors of STB/STL/ZSC/CHR allocate
  their collections so a placeholder is safe to read.
- Out-of-range object references in an IFO are skipped with a log line rather than
  aborting the map load (`Object.Add` bounds-checks the IFO's object ID against the
  zone ZSC, and each part's model/texture ID against the ZSC's lists).
- Map loading wrapped in stage-specific exception logging with UI unfreeze on failure.
- `Output` mirrors every line and full exceptions to `Map Editor.log`.
- Heightmap fallback allocates `ShadowMapRaw` before filling a default shadow texture.
- Empty/missing optional ZSC motion paths are skipped instead of opening an empty `.ZMO`.
- Monster list remove guards against `SelectedIndex == -1`.
- Tactical monster removal uses `TacticalList.SelectedIndex` (not `BasicList`).
- Newly added monster row is auto-selected after adding to a spawn.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
