# Map editor debugging workflow and editing guidelines

> **Provenance:** moved verbatim on 2026-09-24 from `xadet/rose-online-map-editor/CLAUDE.md` lines 128-162 (revision `84f6206`).
> Original bytes: [`xadet--rose-online-map-editor--CLAUDE.md.txt`](../../archive/2026-09-24/xadet--rose-online-map-editor--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=xadet/rose-online-map-editor/CLAUDE.md lines=128-162 sha256=0c9f4653e8befd11185b16cb46fbdc1da51eb66833c6235d06188f1d38e5cbce -->
## Debugging Workflow

The editor logs to `../../data/Map Editor.log`. When a bug is reported:

1. Read the tail of the log — it records the load *stage* and full stack traces.
2. Trust the logged stage/trace before guessing.
3. Patch source → rebuild Release x86 → copy `.exe` + `.pdb` into `../../data`.
4. Clear the log before asking the user to retest.

```powershell
Get-Content '..\..\data\Map Editor.log' -Tail 200
Clear-Content '..\..\data\Map Editor.log'
```

## Editing Guidelines

- **Keep changes narrow.** This is old UI/tooling code with many implicit
  assumptions; avoid broad refactors and formatting churn.
- **Be tolerant of optional assets.** Log missing optional models/textures/motions
  and continue; only abort a map load when a *required* file is missing. Never
  silently swallow new exceptions in load paths — log context + the full exception.
- **WPF threading.** Updates to WPF controls from background threads must go through
  the dispatcher.
- **Don't touch game data** to fix editor code unless the user explicitly asks.
  Editing `../../data` is a separate concern from editing this source tree.
- **A saved map reaches the two halves of the game differently.** The servers
  read `data/` directly (`server.toml` `data_dir`), so a save applies on their
  next restart; the client reads maps from `rose.vfs` (no loose `3ddata/maps` in
  the launch folder), so the same save needs a VFS re-bake + deploy before it is
  visible in game.
- **Saving is all-or-nothing and has no undo.** `Save_Click` rewrites the ZON,
  every IFO, every TIL, every HIM and all LITs of the loaded map, with no dirty
  tracking and no backup — and `data/` is git-untracked by design. Back up the
  zone folder before an editing session.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
