# Map editor verification checklist

> **Provenance:** moved verbatim on 2026-09-24 from `xadet/rose-online-map-editor/CLAUDE.md` lines 295-305 (revision `84f6206`).
> Original bytes: [`xadet--rose-online-map-editor--CLAUDE.md.txt`](../../archive/2026-09-24/xadet--rose-online-map-editor--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=xadet/rose-online-map-editor/CLAUDE.md lines=295-305 sha256=0cd1d1e7875ca31f490e17216ce8b44b181cf7a355557e8baf1a54a25ff7b890 -->
## Verification Checklist

**Map-load fixes:** open a Junon and a non-Junon map; confirm the log reaches
`Loading Completed`; review missing-optional-asset logs for acceptability.

**Monster/spawn UI:** select a spawn; add+delete a Basic monster; add+delete a
Tactical monster; try Delete/Remove with nothing selected (must not throw); test
undo/redo if undo commands were touched.

**Object/terrain:** open a map with decoration + construction; pan to force
rendering; confirm load finishes and the UI unfreezes after any failure.
<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
