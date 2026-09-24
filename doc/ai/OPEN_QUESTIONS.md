# Open questions, unverified claims and conflicts

Newest sections last. Each item names its source and status. Close an item by moving it to
*Resolved* with the date, the evidence and the revision it was checked on; never delete it.

## Q: Current direction (PM)

- **Q-001 (2026-09-24)** What is the next development priority? Not yet given. Per PM-009 the AI
  must ask instead of picking from historical notes.
- **Q-002 (2026-09-24)** Where do game data, reference dumps and a deployable game folder come from
  on this machine? `data/` is empty apart from tracked skeleton files; the reference dumps
  (`C:\Users\Thomas\Desktop\Testclients\`) and `build/` backups are absent (see
  [UNAVAILABLE_KNOWLEDGE.md](UNAVAILABLE_KNOWLEDGE.md) U3-U5). Any data or in-game work needs this
  answered first.
- **Q-003 (2026-09-24)** May the PM supply the previous maintainer's memory directory (U1)? If so it
  should be archived before use.

## C: Conflicts found in inherited text (not resolved; neither side re-verified)

- **C-001 Is vsync the only frame cap?** [client/frame-timing-device-screen-modes.md](topics/client/frame-timing-device-screen-modes.md)
  (from `src/client/CLAUDE.md` line 661) says "Vsync is the only frame cap in the engine — there is
  no software frame limiter anywhere". [project/rendering-device-d3d9ex.md](topics/project/rendering-device-d3d9ex.md)
  (root `CLAUDE.md` line 162) says vsync is **not** the only limiter: `zz_system::sleep()` enforces
  `max_framerate`, defaulting to 60 in `src/` but raised by `data/SCRIPTS/INIT.LUA:39`
  `setFramerateRange(15, 1000)`, and explicitly calls itself a correction of an earlier line.
  *Likely* the root text is the newer claim. To settle: read `zz_system::sleep` and
  `swapBuffers` in `src/engine/`. `INIT.LUA` is not in this checkout (U4).
- **C-002 VFS size threshold.** [client/character-spawn-and-texture-create.md](topics/client/character-spawn-and-texture-create.md)
  (client line 312) cites `pack.rs` `VFS_MAX_BYTES` = 1.90 GB; [project/vfs-offset-limit.md](topics/project/vfs-offset-limit.md)
  says the rollover is now 4.2 GB and "was 1.9 GB while the offset field was still signed". Probably
  a historical statement rather than a live conflict. To settle: read `VFS_MAX_BYTES` in
  `src/pipeline/src/pack.rs`.
- **C-003 RmlUi scope.** [project/rmlui-ui-layer.md](topics/project/rmlui-ui-layer.md) states
  "Scope is new/custom panels only. tgamectrl, the 56 retail XML dialogs … are out", then describes
  UI2, an RmlUi remake of the retail HUD that hides legacy dialogs. Likely the scope grew on
  2026-09-23 without the scope sentence being updated. PM confirmation would settle which scope
  applies now.

## U: Inherited unfinished or unvalidated items (status as last documented)

| ID | Item | Source topic | Last documented status |
|---|---|---|---|
| U-01 | Coplanar placement fix (594 records moved) | [project/coplanar-placements.md](topics/project/coplanar-placements.md) | Applied 2026-09-22, not yet validated in game |
| U-02 | Oro 667 import | [project/oro-667-import.md](topics/project/oro-667-import.md) | Not yet validated in game |
| U-03 | CXE → `.CON` converter for 667 dialogs | same | Idea only; Lua dialect and jump-graph mapping "to confirm first" |
| U-04 | Skaaj import | [project/skaaj-import.md](topics/project/skaaj-import.md) | Imported 2026-09-18, not yet validated in game |
| U-05 | Eldeon EJ02/EJ03 skill-row fixes | [project/ai-skill-reference-failures.md](topics/project/ai-skill-reference-failures.md) | Applied, pending a fight (EZ01 validated 2026-09-15) |
| U-06 | Mukuroji 2539 cast release clip | same | Kept aside; donor AI and model disagree |
| U-07 | Karkia crash of 2026-09-09 | [project/terrain-streaming-performance.md](topics/project/terrain-streaming-performance.md) | "Very likely" the null-neighbour map-tile bug; not proven |
| U-08 | Tall object inside a 10 m patch footprint still culled | [project/cull-bounds-zsc.md](topics/project/cull-bounds-zsc.md) | Known residual; obvious one-line fix said to be insufficient |
| U-09 | Why a below-origin `drawFont` rect misbehaves | [client/overhead-names-cnamebox.md](topics/client/overhead-names-cnamebox.md) | "The underlying rule is not understood" |
| U-10 | Quest icon blind spot (2 of 437 triggers not named by a node function) | [client/npc-quest-icons.md](topics/client/npc-quest-icons.md) | Known limit |
| U-11 | Damage meter: party summons' legacy-path skill damage not owner-credited | [client/damage-meter.md](topics/client/damage-meter.md) | Known limit |
| U-12 | ~0.1 s HP-bar flash when a stale checkpoint presents before a heal sync | [client/combat-hp-authority-and-healing.md](topics/client/combat-hp-authority-and-healing.md) | Known residual |
| U-13 | Residual ~35 ms chunk hitch (one insert batch pulling 12 textures) | [client/chunk-hitch-and-load-budgets.md](topics/client/chunk-hitch-and-load-budgets.md) | Known residual |
| U-14 | UI2: quickbar/inventory need a `CDragNDropMgr` bridge before conversion | [project/rmlui-ui-layer.md](topics/project/rmlui-ui-layer.md) | Not started |
| U-15 | Karkia/LZ02 have no `.MOV`; generating from terrain is the only real fix | [gameserver/walkability-mov.md](topics/gameserver/walkability-mov.md) | Fallback in place; generation not done |
| U-16 | Map editor: deleting a decoration/construction object misassigns lightmaps | [map-editor/compatibility-fixes.md](topics/map-editor/compatibility-fixes.md) | Known, not fixed (workaround: move or sink) |
| U-17 | Map editor GUI retests: MOV painting, Karkia LIT trailers/spawn heights, terrain precision, lightmap sharing | same | Loader/automated checks passed; interactive retests pending |
| U-18 | Shop tabs 323/327 and 386/387 empty here but stocked in reference dumps; 9 nameless and 12 itemless live tabs | [project/data-repair-tooling.md](topics/project/data-repair-tooling.md) | Reported by `check-shop-tabs.py`; fix not documented |
| U-19 | 45 skill books whose skill has no STL key | same | Report-only |

## Resolved

_None yet._
