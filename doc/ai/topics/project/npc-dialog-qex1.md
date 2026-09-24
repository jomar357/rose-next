# NPC dialog quest options (.CON QEX1 appendix)

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 845-847 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=845-847 sha256=206fccde2457bc061e006ac494c4efbbc5c1a19b9db9e680ee19ae92b1819061 -->
### NPC Dialog Quest Options (.CON QEX1 Appendix)
NPC conversations are `.CON` files (`data/3DDATA/EVENT/`) whose logic is compiled Lua 4 **bytecode** — new functions can't be merged into the blob (Lua 4.0.1 rejects multi-chunk buffers). Our extension: an optional appendix after the Lua tail (`b"QEX1"; i32 len; XOR'd Lua source`) that the client (`cevent.cpp`, `QEX_APPENDIX_MAGIC`) executes into the same `lua_State` via a second `Do_Buffer`. The quest editor uses it to append quest options to an NPC's existing dialog without replacing it (`quest-editor con-append`, or the wizard's append radio). Codec + gotchas (main-blob XOR key depends on file size; menu-0 append ordering) live in `src/tools/quest-editor/src/convo.rs` and the tool's `PROGRESS.md`. `.CON` files are client-only — the server never reads them; quest authority stays in QSD triggers. Appended `.CON`s require the QEX1-aware client: ship client + data together.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
