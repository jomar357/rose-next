# Chunk-display hitch and load budgets

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 222-249 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=222-249 sha256=8a8268068c4ad790497a5473b9d2aa418efcdaf39790ef9ef841cc488cd13da3 -->
**Chunk-display hitch — the resolved picture**

The felt "stutter when new terrain appears" was never chunk file I/O (`MapIO` load is ~2-3 ms). It was resource creation forced at first render, and it had **two independent causes** that needed opposite fixes. Measured lead time (frames between a node being queued and force-flushed) is what separates them — see `getLoadPathCount(4/5)`.

| | terrain meshes | textures |
|---|---|---|
| lead time | **1 frame** | **207-309 frames** |
| cost each | ~0.1 ms | **~2.8 ms** |
| why it stalled | 256 patches entered the scene in one frame, rendered the next | `load_weight` = 1 ms/KB, so a 350 KB lightmap scored 350 and sat behind the `t > time_weight` gate ~70+ frames |
| fix | cap patch inserts (`[VIDEO] TERRAIN_INSERTS_PER_FRAME`) | wall-clock load budget (`[VIDEO] LOAD_BUDGET_US`) |

Result: 255-node / 12-46 ms spikes became 23-47-node / 4-6 ms, and at 60 Hz vsync those fit inside the frame budget entirely. The residual outlier (~35 ms) is one insert batch happening to pull in 12 new textures at once — lower `TERRAIN_INSERTS_PER_FRAME` to trade horizon fill-in speed for a smaller worst case.

**Do not try to fix the terrain half with the loading budget** (and vice versa). Terrain has no lead time to exploit; textures have plenty. That mismatch cost several wrong fixes.

**Terrain patch insert budget (`[VIDEO] TERRAIN_INSERTS_PER_FRAME`, default 24, 0 = uncapped)**
- Caps *first-time* frustum inserts of patches beyond `kNearInsertRadius` (6000 units / 60 m) in `CPatchManager::Update_VisiblePatchManager`. Nearer patches are never deferred — a hole at your feet is worse than distant pop-in — and a newly loaded map cell is >= 160 m away by construction, so the cap only bites at the far edge where fog covers it.
- Already-resident patches are unaffected: `Insert_VisiblePatch` only does work when `m_wLastViewFRAME == 0`, otherwise it just restamps. The sibling proximity path has always been budgeted (`kMaxProximityInsertsPerFrame` = 4); only the frustum path was uncapped, on the reasoning "must render this frame or you get holes" — true for near patches, not for an arriving chunk.
- What actually costs the frame is the **textures** an inserted batch drags in via `loadTerrainMaterial`, not the meshes. That is why this dial has more effect than its name suggests.

**Amortised loading budget (`[VIDEO] LOAD_BUDGET_US`, default 2000)**
- The engine's lazy entrance line exists so resources load over several frames instead of at first render. It never worked: `zz_manager::update` subtracted the **entire accumulated budget** on a successful load instead of the item's own weight, so `t` fell to ~0, `t > time_weight` failed, and the loop exited — **one node per manager per update**.
- Meanwhile `CPatchManager` inserts up to 4 patches/frame from the proximity ring and an *unbounded* number from the frustum pass. 4 in, 1 out: the queue could never catch up, a whole map chunk's **255 terrain meshes** backed up, and `zz_terrain_block::before_render()` (which flushes unconditionally) paid for all of them in one frame. Measured in-game at **12–46 ms per spike**, with `terrain=255 mesh=0 tex=1..35` and `ins=0` — i.e. the patches had been inserted on *earlier* frames, so this was never an insert-burst problem.
- Fixed by **bypassing the weight accounting entirely** when a budget is set and pacing the loop on a wall-clock slice shared across managers (`zz_manager::begin_load_budget`, reset per frame in `zz_system::manager_update`).
- **Charging per-item weight instead of the whole accumulator was tried first and was not enough** — worth knowing, because it looks like the obvious fix. The accumulator accrues `1 + total/10` ticks per frame (~24 at 130 fps → `t` = 5 ms), a terrain mesh has `load_weight` **1**, so the `t > time_weight` gate still stopped after **~4 loads/frame** — exactly the proximity ring's 4 inserts/frame. Break-even, so bursts never drained, and raising `LOAD_BUDGET_US` changed nothing because the budget was never the binding constraint. The weight model cannot be tuned into correctness: it is "1 ms per KB" (`load_byte_per_msec = 1000`) and a flat `1` for procedurally generated terrain meshes that read no file at all.
- `LOAD_BUDGET_US=0` restores the exact old behaviour — that is the A/B switch. The budget is only consumed when there is a backlog (`update()` early-returns on empty lines), so steady-state play pays nothing.
- `zz_time` is **unsigned**: the weight subtraction is clamped, because a wrap there hands out an effectively infinite budget.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
