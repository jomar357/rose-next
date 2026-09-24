# Item import tooling

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 836-844 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=836-844 sha256=d1e5da1d53e73b7cc12ca342c6731724eb00c78a893781b6e0a36d859c1738c1 -->
### Item Import Tooling
`scripts/import-item.py` imports an equipment item from another ROSE data dump (e.g. an evo-era private server) as a new appended ID: STB row, model ZSC object (with mesh/material dedup), ground-drop model (`--copy-field-model`), STL name/desc key, and any missing mesh/texture files. Always start with `--dry-run`; it makes `.bak` backups and verifies after writing. **`data/` is gitignored and `pack.rs` filters only *hidden* entries, so delete those `.bak`s before a bake or they end up inside the `.vfs`.** Undo a run with `scripts/remove-trailing-items.py` (trailing rows only, matched by `--name-prefix`).

**Prefer `--art-only --template-row N` for anything from an unfamiliar dump.** It takes the model (plus `--copy-icon` / `--copy-field-model`) and clones every stat column from one of *our* rows, reading no source cell at all. That is a safety property, not a convenience: item bonus/requirement columns are ability ids fed straight into `m_iAddValue[nType] += nValue` with **no bounds check** on either side (`src/client/common/cuserdata.cpp`, and the gameserver's copy). `m_iAddValue` is `int[AT_MAX]` with `m_nPassiveRate`/`m_btRecoverHP`/`m_iDropRATE` directly behind it, so a modern affix id (Jrose uses 174/175/184/185/195) silently corrupts adjacent character state instead of erroring. `--art-only` also skips the source STL, sidestepping foreign dialects — Jrose writes the legacy `I_NUM` header that our strict reader rejects. See [doc/jrose-back-import.md](../../../jrose-back-import.md). `scripts/add-item-icon.py` adds a custom item icon from a PNG (any size, auto-downscaled to a 40×40 cell) to the `ITEM1.TSI` atlas and prints the new global icon index (`--weapon-row N` also patches the STB); requires Pillow. `scripts/add-skill-icon.py` is the same tool for **skill** icons (`SKILLICON.TSI`, extension sheets `skill04.dds`+, original indices 0–506, extensions from 507; `--skill-row N` patches `LIST_SKILL.STB` col 51). Note the two TSIs use different sprite-rect conventions (item `x..x+40`, skill `x..x+39`) — each script matches its atlas. Both docstrings document the underlying binary formats — read them before editing STB/ZSC/STL/TSI by hand.

**Putting a new skill in the skill tree needs an art edit**, not just an XML node: the boxes and connectors are painted into the per-category `DEALER_*.DDS`, and `CSkillTreeDlg` has no line-drawing code at all — the XML only positions a 40×40 icon, at coordinates that are **absolute inside the dialog**, not relative to the parent node. The xml loads loose via `fopen` (never the VFS) while the DDS loads from the VFS and ignores a loose copy, so the two halves deploy differently. Recipe, coordinate system and traps: [doc/skill-tree-art.md](../../../skill-tree-art.md).

Key facts: weapon visuals come from `LIST_WEAPON.ZSC` indexed by item number (1:1 with STB rows) — the STB "model file" text column is vestigial and never read by the game. Ground-drop visuals are a separate index (STB col 10) into `LIST_FieldITEM.ZSC`. Icon indices are global sprite positions in `ITEM1.TSI` (originally 50 sheets × 169 cells = 0–8449; extension sheets `icon51.dds`+ continue from 8450). After data edits, restart servers (they cache STBs at startup) and the client.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
