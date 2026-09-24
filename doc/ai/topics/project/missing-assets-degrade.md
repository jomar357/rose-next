# Missing assets must degrade, not kill

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 470-479 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=470-479 sha256=39c4684d9f8216e533473d8d58794b67633a822933987256ffde49f03082925b -->
### Missing Assets Must Degrade, Not Kill (Engine/VFS)

An asset referenced by the data but absent from the baked `.vfs` used to be **fatal anywhere in the game** — four independent defects sat on that one path, each masking the next. All are fixed; the contract now is *a missing file logs once and the object renders without that part*. Keep it that way:

- **Never pass a string-ish class through `ZZ_LOG`'s varargs.** `zz_slash_converter`'s first and only member is `char _str[ZZ_MAX_STRING]` and its `operator const char*()` applies at ordinary call sites but **not** through `...`, so `ZZ_LOG("%s", converter)` copies the buffer onto the stack and `%s` consumes the first four *characters* as a pointer. Always `.get()`. (`zz_string` survives only by luck — it stores a `char*` first.)
- `zz_vfs_pkg::open` must null-check `fp_` **before** using it. `VOpenFile` legitimately returns NULL for a file in neither a package nor on disk, and `zz_assertf` is compiled out in release.
- A failed load must be **recorded**, not retried. `zz_mesh::load` sets `load_permanently_failed` (and `set_path` only clears it when the path actually changes, since `loadMesh` calls `set_path` on every attempt). `CFileLIST::Get_DATA` sets `tagFileDATA::m_bLoadFailed` — that covers motions and materials, but **not meshes**: `loadMesh` always hands back the spawned node, so `CMeshLIST::Load_FILE` reports success even for a file that will never load. Without the engine-side flag a single missing mesh produced 2.26M retries and a 447 MB `error.txt`.
- `zz_manager` must **drop** a terminally failed node, not re-queue it. `zz_node::is_load_terminally_failed()` (overridden by `zz_mesh`) distinguishes "file is missing" from "not ready yet"; without it `update()` pops and re-pushes the node every frame for the life of the process, `update()` never hits its both-lines-empty early return, and since `push()` does a linear `find()` the cost is O(n²) per update in the number of missing meshes.
- `zz_manager::update`'s entrance loop also bounds failed re-inserts per update. The failure branch re-queues without decrementing `entrance_time_accumulated`, so an unloadable node otherwise spins forever *within a single update*. Note this only became a *hard* freeze once the retry throttling above was fixed — removing accidental throttling can expose a latent spin.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
