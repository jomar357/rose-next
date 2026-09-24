# Walkability and missing .MOV files

> **Provenance:** moved verbatim on 2026-09-24 from `src/sho_gameserver/CLAUDE.md` lines 142-194 (revision `84f6206`).
> Original bytes: [`src--sho_gameserver--CLAUDE.md.txt`](../../archive/2026-09-24/src--sho_gameserver--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=142-194 sha256=6d0a70dcb2e1aee134b9f99700947ae0582e53f9984bce2630b574200050ef53 -->
## Walkability, and why a missing .MOV killed every leash in Karkia

`CZoneFILE::LoadZONE` allocates the move-attribute grid and `FillAll()`s it — **1 =
blocked** — then clears bits from each map tile's `*.MOV`. `LoadMOV` returns silently
when the file does not exist. So a zone that ships **no `.MOV` at all** is blocked on
every cell, and `IsMovablePOS()` returns false everywhere in it.

That gates exactly one thing that matters: `CObjCHAR::SetCMD_MOVE2D` rejects every
destination. And `SetCMD_MOVE2D` is the move used by

- the **leash** — `AIACT_16` → `CObjMOB::Run_AWAY()` → "flee to within N m of my
  regen point",
- idle wandering (`AIACT_03`/`AIACT_04`), and
- fleeing on low HP.

**Chase does not go through it.** `CObjAI::ProcCMD_ATTACK` uses
`Goto_TARGET`/`Start_MOVE`, which has no walkability gate. The result in such a zone
is a monster that chases perfectly and can never give up — and since `Run_AWAY`
leaves the command as `CMD_ATTACK` when it fails, and nothing logs, it looks like
missing AI data rather than a missing asset. It is not missing AI data: 379 of our
509 `.aip` files declare a pattern-2 leash, and every Karkia monster has one
(typically "≥50-80 m from spawn → run back to within 1-5 m").

Since 2026-09-12 `LoadZONE` counts the tiles that actually loaded and, if **none** did,
opens the walkability grid and logs a warning. This is the server-side form of the engine's
"Missing Assets Must Degrade, Not Kill" rule. Things to know:

- **It opens only the cells under a map tile that actually loaded, not the whole grid.**
  The first version cleared all 2048×2048 cells, which also opened the void *outside* the
  map — and since `IsMovablePOS` gates nothing but `SetCMD_MOVE2D`, monsters promptly
  wandered off the terrain. A position off the map is what feeds garbage into the client's
  `CTERRAIN::GetPATCH`. `LoadMAP` records each tile in `m_bMapTileLOADED`; a tile is
  `PATCH_COUNT_PER_MAP_AXIS * 2` grid cells per axis (`LoadMOV`'s own stride), and
  `MAP_COUNT_PER_ZONE_AXIS` of those is exactly `MAP_MOVE_ATTR_GRID_CNT`.
- **Do not use `m_nMinMapX`/`m_nMaxMapX`/`m_nMinMapY`/`m_nMaxMapY`** (`zonefile.h`). They
  are declared and never assigned anywhere, so they hold uninitialised garbage. A per-tile
  flag is also correct for a non-rectangular zone, which a min/max box is not.

- It fires for all 9 Karkia zones and for **Lunar LZ02** — the only zones we ship with
  zero `.MOV`. Nothing else is affected; no zone has *partial* coverage, so the
  "none loaded" test can never half-apply to a map that meant to block something.
- Jrose never shipped Karkia's `.MOV` either, so there is nothing to import. Generating
  them from terrain is the only way to get real per-cell walkability there.
- The cost is that monsters in those zones can path into geometry a map author would
  have blocked. That is the accepted trade against an unbounded chase.
- `IsMovablePOS` has only two other callers and neither changes behaviour: a telemetry
  flag in `gs_socketlsv.cpp` and a GM readout in `cheatcmd.cpp`.
- Aggro radius and leash distance are **`.aip` data, not code** — metres in the file,
  ×100 at load (`cai_file.cpp`). There is no sight/aggro/chase column in `LIST_NPC.STB`
  and no server.toml knob. Karkia's idle-aggro radii are 13-22 m.
- Same gate, same trap as `CObjSUMMON::PlayerOrderMoveTo` above, which exists because
  player click-to-move must not be gated either.

<!-- verbatim:end -->

## Updates

- **2026-09-24 (verified on this checkout's data, build of `28a777f` + local changes).** The
  no-`.MOV` fallback now fires for more zones than the text above lists: the game server log
  showed it for exactly 14 zones: 14, 57, 83, 85, 86, 87, 88, 89, 131, 133, 134, 135, 136, 144
  (Lunar LZ02 was not among them). Oro (667 ships no `.MOV`) and Skaaj were imported after this text was
  written.
