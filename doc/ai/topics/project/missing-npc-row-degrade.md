# A missing NPC row must degrade, not kill

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 480-527 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=480-527 sha256=086d830301556a6c5a064455aff75421e3dc59be8cff95c27ce594c9e10ffc1b -->
### A Missing NPC Row Must Degrade, Not Kill (Client/Server)

The sibling of the rule above, on the data side. Six AI action types carry a
monster id as a `WORD` at offset 8 — 09 `Change_CHAR`, 10 `Create_PET`, 18, 20,
36, 37 — and an imported `.aip` routinely names monsters that were never
imported with it. The summon actions were always safe by accident
(`CZoneTHREAD::RegenCharacter` rejects an unknown id), but **`Change_CHAR` had no
guard on either side** and crashed the client. The 2026-09-12 Karkia session:

- `kak_ghost_cemetery.aip` (NPC 2731 "Ghost Seed", summoned by the whole Burned
  Forest roster) does `Change_CHAR` → 2734-2738, all **blank rows** in our
  `LIST_NPC`.
- Client `CObjMOB::Change_CHAR` calls `DeleteCHAR()` and *then* `Create()`.
  `CreateCHAR` returns at its part-count check, so the object stayed alive with
  **no engine model node** — invisible, unclickable, and logging
  `interface: getVisibility() failed` every frame.
- `CCharMODEL::DeleteBoneEFFECT` took `CEffect**` **by value**, so
  `SAFE_DELETE_ARRAY` nulled only the local copy and left `m_ppBoneEFFECT`
  dangling. Invisible on the normal path because `CreateCHAR` reassigns it a few
  lines later — but a *failed* `Create()` never does. Zone teardown then walked
  freed memory and freed the array a second time.

Things that will bite:

- **Heap corruption produces no crash dump.** It fail-fasts
  (`STATUS_HEAP_CORRUPTION`) without unwinding, so `SetUnhandledExceptionFilter`
  is never consulted and `CrashHandler` wrote nothing. A vectored handler now
  catches the three fail-fast codes; anything else is handed straight back,
  because a VEH sees every first-chance exception including ordinary handled ones.
- **`NPC_NAME` is NULL on the server and `""` on the client** — `STBDATA::get_cstr`
  returns `nullptr` for a blank cell, while the client goes through
  `CStringManager`. A guard written as `if (!NPC_NAME(i))` is correct server-side
  and useless client-side.
- **`error.txt` accumulates across sessions and is buffered**; `client.log`
  flushes per record. Read `client.log` first — here it named the exact object
  (`client_idx 1217, type 7, char_no 2735`) and stopped mid-`FreeZONE(131)`,
  which located the crash. `error.txt` only had 434 subject-less engine lines.
- Count broken *objects*, not log lines: one object spams every frame.

`scripts/audit-ai-monster-refs.py` is the data tool — read-only with
`--dry-run`/`--verify`, strips the dead action records otherwise, and has a
`--selftest` that proves the container rewrite is byte-identical across all 509
`.aip` before touching anything. Backups go to `build/ai-monster-refs/`, **not**
beside the `.aip`, because `pack.ps1` hard-errors on a `.bak` under `data/`. Run
it after any `import-*.py` that brings in AI files. It found 278 dangling
references in 45 files: Oro (2236/2237, 3001-3003), Karkia's ghosts and Flower
Garden, and three pre-existing retail ones.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
