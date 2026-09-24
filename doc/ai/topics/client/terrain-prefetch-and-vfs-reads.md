# Terrain: chunk prefetch and buffered VFS reads

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 174-189 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=174-189 sha256=74bc979108b1ae02099c32ad3aecba237e06a6309651da2a50dbf96952cafd32 -->
**Chunk prefetch (`CMapFilePrefetcher`, `io_terrain.cpp`)**
- Background worker at `THREAD_PRIORITY_BELOW_NORMAL` that reads-and-discards the files `CMAP::Load` will need, warming the OS cache. Requested from `AddMAP` when a cell is enqueued; invalidated by a generation counter on zone change / disable. Toggle with `[VIDEO] MAP_PREFETCH=0`.
- **It reads through the VFS, not loose files.** The original version `fopen`'d loose `<map>.HIM/.TIL/.IFO` paths, which exist only on a loose dev install — a deployed client has no loose `3ddata\MAPS` at all, so every open failed into `if (!f) continue;` and the whole mitigation was a silent no-op in the build that ships. If you change the read path, verify against a *packed* deploy.
- The worker owns a **private** `VHANDLE` from `OpenVFS("data.idx", "r")`, opened on the main thread in `EnsureStarted()` (`CVFS::Open` writes global CRT state via `_set_fmode`) before the thread exists. `OpenVFS` does `new CVFS_Manager`, so it shares no mutable state with the engine's handle; the index maps it reads are filled at mount and never written again. Mode is `"r"`, not `"mr"` — the plain-`FILE*` branch makes `vfread` an `fseek`+`fread`, warming the cache with no `MapViewOfFile` churn in a 32-bit address space.
- It warms six files per cell, not three: `.HIM`, `.TIL`, `.IFO`, `<x>_<y>_PlaneLightingMap.dds`, and the two `LightMap\*.lit`. **The lightmap DDS is 131–350 KB — over ten times the rest of the cell combined**, so the original three-extension list covered under a tenth of the bytes. It is read by the *engine's* separate memory-mapped handle, but warming still works: both are views of the same `rose.vfs` and Windows backs the file cache and the mapped section with the same physical pages.
- `pfHit=satisfied/attempted` on the HUD's `Stream:` line is the honesty check. Non-zero attempted with zero satisfied means the worker runs but resolves nothing.

**Buffered VFS reads (`CFileSystemTriggerVFS`)**
- `Read()` keeps a 32 KB sequential read-ahead buffer, and **`m_lLogicalPos` — not the underlying `VFileHandle` — is the authoritative file position.** `Tell()` must return it (after a refill the handle sits up to 32 KB ahead), `Seek()` moves it and deliberately does *not* invalidate the buffer (so the `.IFO` lump walk's Tell→Seek→read→Seek-back stays free), and `IsEOF()` compares it against `vfgetsize`. `Seek` mirrors `vfseek`'s clamping to `[0, size]`-and-succeed. `OpenFile`/`CloseFile` must reset both — these objects are **pooled and reused** by `CVFSManager`, so stale buffer state would be served as the next file's content.
- Why: every typed reader (`ReadFloat`, `ReadInt32`, `ReadByte`, …) funnels into `Read()`, which previously issued one `::vfread` — a `memset` plus an `fseek`+`fread` CRT round trip — per call, for as little as one byte. Terrain parses scalar-by-scalar, so a 19 KB `.HIM` was ~4,900 such calls. Measured against the shipped `rose.vfs`, warm cache: `.HIM` **2.88 ms → 0.057 ms (51×)**, `.TIL` 0.26 → 0.011 (24×), a 22 KB `.lit` **3.22 ms → 0.068 ms (47×)**. That was the bulk of the `him=3.2` and `lit=4.0` phases on the `MapIO:` row.
- **If you touch this, re-run `vfs_buffer_tests`** (`src/tests/vfs_buffer/`). It compiles the real `cfilesystemtriggervfs.cpp` translation unit — not a copy — and checks it against raw `VOpenFile`/`vfread` ground truth over 6 real files: full sequential scalar passes, 4,000 random seek/read ops each, all three seek origins, over-seek clamping, EOF short reads with zero-fill, and pooled re-open (~917k assertions). It needs real game data, so run it from a deployed game dir or pass one:
  ```
  bin\release\vfs_buffer_tests.exe C:\path\to\game
  ```
  With no `data.idx` present it prints `SKIP` and returns 0, so it is safe to run unconditionally after a build. Verified to fail loudly: reintroducing the old `Tell()` (returning `vftell` instead of `m_lLogicalPos`) trips 147k assertions immediately.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
