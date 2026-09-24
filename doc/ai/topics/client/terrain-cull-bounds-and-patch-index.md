# Terrain: object cull bounds and patch index staleness

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 158-173 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=158-173 sha256=aaccc1b003ecc6d0a4733c722cc5cc64a0d0c4e790fbf5f252f78b3cf6fec5e0 -->
**Object cull bounds (`MakeAABBFromObject`) — never trust the ZSC box**
- Fixed objects live or die with their owning patch: `CMAP::AddObject` assigns an object to whichever patch holds its **pivot**, and `CMAP_PATCH::RemoveFromScene` pulls every object on that patch out of the engine scene. A patch is 10 m square, so nearly every building overhangs its own patch — that is what `m_AABBMin`/`m_AABBMax`, `CompareSizePath2Obj`, `ExPatchEnable` and the `m_ExPatchList[85]` global fallback exist for.
- **The bounding box cached in the ZSC is broken data in every file in the game.** The exporter scaled only X into world units (cm) and left Y and Z in mesh units, so the stored box is ~100× too thin and ~100× too short. Muris' `ORT01CLIFF01L` registered as a 336 m × 4.0 m × 1.1 m ribbon on the ground instead of a 336 m × 396 m × 114 m wall, so a camera turn evicted the patch and deleted the whole wall mid-screen. Retail Junon has the same defect (its planet vessel is off by 970 m), so this is not an import artefact.
- `MakeAABBFromObject` therefore asks the **engine** for the world AABB it already derives from real mesh min/max — `getVisibleWorldMinMax` → `CObjFIXED::GetWorldMinMax`, root node only — and keeps the cached box only as a fallback. Do not "optimise" this back to `pModel->m_BBMin`.
- Valid at map-load time because `loadMesh` reads the ZMS header min/max **eagerly** (`load_mesh_minmax`), independent of lazy geometry loading, and `loadVisible` sets `ZZ_BV_OBB` before `add_runit` so every part has an OBB immediately. `update_bvolume`'s internal `scene_refresh()` is a no-op while the node is out of scene.
- Root-node-only is complete: **zero** `LIST_CNST_*` / `LIST_DECO_*` objects have more than one parentless part (all multi-root models are character equipment, built from `CCharPART`), and `CObjFIXED::InsertToScene` only inserts the root anyway.
- **This adds an engine export, so `rosenext.exe` and `znzin.dll` must deploy as a pair** — a new exe against an old DLL will not start. Use `scripts/ab-build.ps1`.
- The far-insert near/far test in `Update_VisiblePatchManager` measures to the patch's own `m_aabb` footprint, **not** `m_AABBMin`. That corner is `+1e8` for object-less patches and, with correct bounds, one large object drags it hundreds of metres off the patch being decided.
- `ViewCullingFunc` loops `i < 4` — near, far, left, right, **never top or bottom** — so vertical FOV culls nothing and the commented-out z comparisons in `CompareSizePath2Obj` are not worth restoring on their own. Residual known gap: an object fitting inside its patch's 10 m footprint while towering over local terrain never gets `ExPatchEnable` and is still culled by a terrain-only z.
- `scripts/audit-zsc-bounds.py` verifies all of this from the data side. Full record: [doc/zsc-bounding-boxes.md](../../../zsc-bounding-boxes.md).

**Patch index staleness (latent; exposed by the proximity pass)**
- `CPatchManager::m_ppPATCH[48×48]` holds patch pointers for the current 3×3 map set. It is populated only by `ReOrginazationPatch` and does **not** track per-frame map-slot rotation in `SetCenterPosition`. The frustum path reads only `m_ppQuadPatchManager[3][3]` (which `UpdatePatchManager` refreshes), so this was latent until proximity was wired in.
- After any map-slot change the stale entries point into `CMAP::m_PATCH` storage that `CMAP::Free()` has `ZeroMemory`'d — deref yields a zeroed `CMAP_PATCH` with a null vtable, and the first virtual call (`InsertToScene` → `RegisterToNZIN`) crashes.
- `m_bPatchIndexDirty` flag on `CTERRAIN` is set by `SetMapPTR` and `DoActualUnload`; `SetCenterPosition` calls `ReOrginazationPatch` lazily when dirty, just before `Update_VisiblePatchManager`. **Any future code that directly reads `m_ppPATCH` must run after this refresh.**

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
