# The .vfs offset limit (2 GB -> 4 GB)

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 816-835 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=816-835 sha256=227bbb8d46f9907c0038b1382d0a64ab1dddf25a5a7c53fc71c1eba5bde987fc -->
### The .vfs Offset Limit (2 GB -> 4 GB)

**A `.vfs` archive cannot exceed 4 GB, and could not exceed 2 GB before 2026-08-29.** `FileEntry::lFileOffset` in triggervfs was a *signed 32-bit* `long`, so a file stored past byte 2,147,483,647 got a negative offset, the client seeked to garbage and read binary noise. It is now unsigned, which doubles the ceiling — the on-disk field is the same four bytes, only the interpretation changed.

Three things had to change together, and each failed differently:

- `FileEntry::lFileOffset` and `VFileHandle::lStartOff`/`lEndOff` are unsigned. `MapViewOfFile` already took the offset as a DWORD low + DWORD high(0) pair, so the engine's memory-mapped path needed nothing else.
- **`vfread` had a `(signed)` cast** on the end-of-file comparison that actively defeated the unsigned field, plus a `long` offset and a 32-bit `fseek`. The client opens `"r"` (plain fseek/fread) while the engine opens `"mr"` (memory-mapped) — **completely different code paths**, so verifying one proves nothing about the other. The mapped path worked as soon as the field was unsigned; the plain path silently returned **zeros** until `_fseeki64`.
- `vfseek`'s clamps must be **signed 64-bit**. In 32-bit unsigned, `lStartOff + offset` with a negative offset wraps and the underflow guard silently fails.

**Bake with `scripts/pack.ps1`** (`data/` -> `Exes/`). It now runs `verify-vfs.py` itself and fails the bake if the archive is unaddressable, and it prefers `bin/release/pipeline.exe` over the copy in `Exes/`. That default matters: `Exes/pipeline.exe` had gone **four months stale** (2026-04-06, against a rollover added 2026-08-17), so every bake ran a packer built before the size guard existed — which is the entire reason `rose.vfs` sailed past the split threshold with no `rose_2.vfs` while the code looked correct. Checking the timestamp of `bin/release/pipeline.exe` says nothing about what actually packed the archive.

Verify manually with `scripts/verify-vfs.py <game-dir>` after any bulk bake — it re-derives everything from the bytes on disk, so a packer bug cannot hide from it. `scripts/make-oversize-vfs.py` builds a sparse >2 GB archive with a deterministic payload and `vfs_buffer_tests.exe --bigtest <dir>` reads it back through the real triggervfs in **both** modes, checking content it re-derives from the file name — an independent oracle, not a comparison of two paths that share the bug.

The failure looks nothing like its cause. Whichever files happen to land past the boundary are simply the tail of the archive — when it first hit, that was `SCRIPTS\INIT.LUA`, so the client died at startup with a Lua `invalid control char near 'char(6)'` parse error followed by `assert: failed. zz_shader::check_system_shaders()`. Nothing pointed at the archive.

`pack.rs` now **rolls over to `rose_2.vfs`, `rose_3.vfs`, …** at 4.2 GB (`VFS_MAX_BYTES`; the margin below the 4 GiB ceiling absorbs the largest single asset, since the check runs before writing — it was 1.9 GB while the offset field was still signed) and hard-errors if an offset would still overflow. Both the `.idx` format (`VfsIndex::file_systems` is a list) and the runtime (`CVFS_Manager::m_vecVFS`, searched by `OpenFile`) already supported multiple archives — only the packer was hardcoded to one. **Ship every `rose*.vfs` alongside `data.idx`**, not just `rose.vfs`.

Diagnosing a suspected bad bake: parse the `.idx` FAT (`short len; char name[len]; long off,len,blk; BYTE deleted,compress,enc; DWORD version,crc`) and check for negative offsets — that is a two-minute script and it is unambiguous.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
