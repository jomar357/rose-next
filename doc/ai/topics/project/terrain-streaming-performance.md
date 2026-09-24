# Terrain streaming performance (summary)

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 665-673 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=665-673 sha256=fd3cba57a7f089bb6f61f10f395f5c7776fd9329811c0858b7e8472b5e4a7927 -->
### Terrain Streaming Performance

Chunk-display hitches are **resource creation at first render**, not chunk file I/O. The client `CLAUDE.md` has the full picture; the two things to know before touching it:

- **Measure lead time, not queue depth.** Frames between a resource being queued and being force-loaded is what tells you which fix applies. Terrain meshes measured **1 frame** (no amortiser can help — cap the inserts, `[VIDEO] TERRAIN_INSERTS_PER_FRAME`); textures measured **200-300 frames** (the amortiser had slack and wasted it — `[VIDEO] LOAD_BUDGET_US`). Applying either fix to the other problem does nothing.
- **A map tile that is allocated but not `MAP_USING` next to the player crashed the client** (2026-09-18, walking towards the Skaaj lighthouse; `GetViewFrustumEq` on `this = 0x22C0`, i.e. NULL plus the member offset). `ClearAllQuadPatchManager()` nulled the nine neighbour pointers but not `m_isUse`, and `UpdatePatchManager()` only rewrote the flag for a NULL or in-use neighbour, so a freed, dirty or still-loading slot kept last frame's TRUE beside a NULL pointer, and the next cull wrote through it. Both sites now clear the flag. The one unexplained Karkia crash of 2026-09-09 was preceded by the same `DeferredFreeMAP` teardown and is very likely this bug.
- Diagnostics are opt-in: `[VIDEO] STREAM_SPIKE_LOG_MS` (0 = off) plus the `MapIO:`/`Flush:` debug-HUD rows and `/perfreset`.
- **`STREAM_SPIKE_LOG_MS` only fires on streaming time**, so a hitch from any other phase writes nothing and is indistinguishable from a smooth frame. `[VIDEO] FRAME_SPIKE_LOG_MS` (0 = off) triggers on *total* frame time and logs that frame's own phase split (`netin/logic/scnupd/shadow/render/ui/present/oth` + the logic sub-slots + the flush counters), which is what names a non-streaming hitch. Reach for it first; the streaming log narrows down what it finds. Run with `VSYNC=0` while hunting, or the vsync wait in `present` masks everything.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
