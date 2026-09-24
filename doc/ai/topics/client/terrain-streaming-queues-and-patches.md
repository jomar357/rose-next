# Terrain streaming: queues, hysteresis, patch keep-alive

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 135-157 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=135-157 sha256=ce66adb8b02f47de54b794969702e6e65e1a494bb66579235be35317fc756371 -->
### Zone Warp / Terrain Streaming

Zone changes (`CGameStateWarp` → `CTERRAIN::LoadZONE` / `FreeZONE`) and per-frame streaming in `SetCenterPosition` are sensitive to stale state. Containers below are **zone-local**; if they survive a teleport the client keeps loading/freeing old-zone terrain for many frames after warp. `ResetStreamingState()` (called from `FreeZONE` after `SubMAP(MOVE_UPDATE_ALL)`) clears all of them.

**Load / unload queues**
- `m_LoadOneMapData` — deferred per-map loads drained by `SetCenterPosition()`, one map per `kMinMapLoadIntervalMs` (150 ms) via `m_dwLastMapLoadTick`. Never replace with a frame-count gate — at 60 fps the old `% 5` drain produced visible post-stop hitches for several seconds.
- `m_DirtyMapList` — recycle list of freed `CMAP*` entries.
- **`FreeDirtyMAP()` is dead code and its 150 ms budget protects nothing.** The intent was two-phase teardown (mark `MAP_DIRTY`, clear later), but `CMAP::Free()` calls `ClearFromNZIN()` inline and `ClearFromNZIN()` ends with `m_nUseMODE = MAP_EMPTY` — so nothing is ever `DIRTY` and the `IsDirty()` scan can never match. The real teardown cost is paid inside `DrainPendingUnloads` (below), which is where the cap actually lives. Do not cite `kMinDirtyFreeIntervalMs` as protecting unloads.

**Map-level hysteresis (curve-back prevention)**
- Map unloads are deferred, not immediate: `DeferSubMAP` pushes doomed cells onto `m_PendingUnloadList`; `DrainPendingUnloads(dwNow)` commits them only when the player is > `kMapUnloadHysteresisRadius` (2) maps away OR `kMapUnloadGraceMs` (3 s) has elapsed.
- `DrainPendingUnloads` commits **at most one map per `kMinDirtyFreeIntervalMs`** (`m_dwLastUnloadTick`). A teardown is expensive and synchronous — `ClearFromNZIN()` unregisters all 256 patches, deletes every fixed object/effect/sound in the cell and frees the 257 heightfield rows — and a diagonal crossing makes up to five cells eligible at once, on the same frames the load path is already hitching. Zone teardown bypasses this: `FreeZONE` calls `SubMAP(MOVE_UPDATE_ALL)` then `ResetStreamingState()`.
- `AddMAP` fast-path: if the target cell is still pending unload, `CancelPendingUnload` removes the entry and **skips the disk-load enqueue entirely**. Do not re-enqueue loads for cells that are still live.
- `DoActualUnload` is the only place that calls `pMAP->Free()` + nulls `m_pMAPS` for deferred unloads. The old direct `SubMAP` path only runs on zone teardown.

**Patch keep-alive (camera-rotation prevention)**
- `CPatchManager::Delete_UnvisiblePatch` uses `kPatchEvictGraceFrames` = 30 frames (~0.5 s at 60 fps; `m_wLastViewFRAME` is `uint16_t`; subtract with wrap-safe arithmetic). Do not evict on `m_wLastViewFRAME != view_frame` — that re-introduces free-look stutter.
- `Update_VisiblePatchManager(nMappingX, nMappingY)` runs the proximity pass (`Update_VisiblePatch`) after frustum culling so nearby terrain stays in-scene regardless of camera angle. Free-look (right-click drag) rotates yaw + pitch and can reveal many quadrants at once — without proximity keep-alive each re-entering patch pays `InsertToScene` = walk `m_FixObjLIST` + `m_EffectLIST`.
- Ring radius is `kProximityRingRadius` = 12 (~452 patches via `g_pCRange->GetStartIndex(12)`). The earlier 22 covered 1513 points (~66% of the 48×48 grid), stamped every ring patch's `m_wLastViewFRAME` to the current frame every frame, and so defeated the eviction grace — `resPatch` pinned at 2304 and FPS collapsed in open zones. Any raise above 12 should be measured against `ring=` on the Scene HUD line and `resPatch`.
- First-time proximity inserts are capped at `kMaxProximityInsertsPerFrame` = 4 so teleport warm-up cannot itself cause a burst. Frustum-visible patches are never budget-gated (must render this frame or you get holes).
- `CPatchManager::s_nRingStampsThisFrame` counts ring hits per frame (both stamp and budgeted insert). Reset in `CTERRAIN::SetCenterPosition` next to `CMAP_PATCH::s_nInsertThisFrame`; surfaced on the HUD as `ring=` in the Scene: line.
- `CPatchManager::GetFrustumPatchCount()` exposes `m_nSubPATCH` (patches selected by the quadtree frustum pass after `CalculateViewFrustumCulling`). Surfaced on the HUD as `sub=` on the same Scene: line so `sub` vs `resPatch` distinguishes real frustum set from proximity keep-alive + eviction-grace overhang. If `sub ≈ resPatch` in an open zone, the frustum isn't rejecting and the location is content-bound (not a streaming bug).

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
