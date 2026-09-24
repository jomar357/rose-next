# Character spawn (motion parser) and texture create costs

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 273-312 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=273-312 sha256=43220c52baafb2fe84a3a6ed4081151ef6f9d54669926efa0440916700778ee6 -->
**Character spawn was a motion-parser problem (fixed)**

Walking through Muris produced 20-100 ms frames whose cost split across two buckets, which is why neither the streaming log nor the packet timer found it alone. Chased to the bottom, the chain was: `GSV_NPC_CHAR`/`GSV_MOB_CHAR` handler -> `CObjCHAR::CreateCHAR` -> `LoadModelNODE` -> `Get_MOTION(0)` -> lazy ZMO load. Measured 10-26 ms **per new NPC type**; repeat spawns of a loaded type are free, and `skel` (0.4-1.2 ms) and `::loadModel` (0.1-0.4 ms) were never the problem.

The cost was not I/O. `zz_motion::load` read the frame section **one float at a time**, and every `zz_vfs::read_float` bottoms out in `zz_vfs_pkg::read_`, which calls `vftell` then `vfread` — both `__stdcall` exports of `triggervfs.dll` — behind a virtual dispatch. A 30-bone, 200-frame motion is ~24,000 floats, so ~48,000 cross-DLL calls, plus up to four `is_a()` type-chain walks per channel *per frame*. It now sizes the frame section from the channel types, reads it in one call via `zz_fast_reader`, and switches on the stored `channel_type` the way `update_mesh` always did.

Things that will bite:

- **This is an engine change: deploy `rosenext.exe` and `znzin.dll` as a pair.**
- `zz_fast_reader` (written 2011) had **no users at all** before this. It also had a `new[]`/scalar-`delete` mismatch, harmless for `char` but fixed since it is now a hot path.
- **The bulk read is padded, not strict** (`load_padded`). The old field-by-field reader could not fail: a short file left stale values and carried on, so a truncated motion was a visibly wrong animation. Failing hard would turn that into an NPC that never spawns — a cosmetic fault promoted to a functional one. Zeros are at least deterministic.
- **`ZZ_CTYPE_NORMAL` shares the position channel class and has therefore always been scaled and `ZZ_XFORM_IN`'d like a position.** Odd, preserved deliberately — that commit was a speed change, not a behaviour change.
- **A quat is laid out `x,y,z,w` but the file stores `w,x,y,z`.** Reading a rotation as one 4-float block into the quat silently rotates every bone. Read the components individually.
- Our `.vfs` is **not** encrypted (`pack.rs` never sets `is_encrypted`), so `zz_vfs_pkg::read_`'s encrypted branch is dead here. Be aware it rebuilds a 4 KB crypt table **and heap-allocates a `std::string`, per call** — against an encrypted archive the old per-float reader would have been catastrophic rather than merely slow.

- **`spawn[n= skel= mot= load= parts= bone= rest=]`** breaks one `CObjCHAR::CreateCHAR` into its steps, accumulated per frame. Spawn cost lands in **two** buckets and neither log alone reveals it: the skeleton, motion and materials have `load_weight == 0` so they load inline inside the packet handler (charged to `pkt`), while the meshes and textures are queued and then force-flushed at render (charged to `flush`, under `shadow`). This is what found the motion parser above — `mot` was 90%+ of every spawn and is now 0.1–0.5 ms.

**Texture create, not texture I/O** (`tex[n= read= create=]` on the spike line)

Once character spawn was fixed, every remaining spike was `shadow` = flush = textures. The split says the file read is ~0.1 ms per texture and `D3DXCreateTextureFromFileInMemoryEx` is everything else — and it is not a fixed overhead: one session measured **0.20 ms and 11.13 ms per texture**, a 55x spread.

`zz_renderer_d3d.cpp` carries a note from the original team that names the mechanism: a 512x512 DXT1 costs **0.729 ms at miplevel 1 and 57 ms at miplevel 2**. Same file, same size — the cost is D3DX *generating* a mip chain instead of copying the file's, which for a DXT source means decompress, box-filter and recompress per level. No D3DX flag avoids the recompress, so this cannot be tuned away in the renderer.

`INIT.LUA` asks for 3 mip levels (`setMipmapLevel(3)`, which the gutterless lightmap atlas requires — see the root `CLAUDE.md`). A file that ships its own chain is a cheap copy; a file with none has to have one built at load.

**1257 of 11427 shipped DDS files have no mip chain**, and the distribution is damning: `ELDEON` 99% (208/210) and `ORO` 70% (103/148) — both our own imports — against `MAPS` 9.9% and `AVATAR` 4.3%. Muris is Eldeon, which is why the test route hits it hardest. 819 of the 1257 are DXT-compressed, so regenerating them offline needs a DXT encoder (`texconv`/DirectXTex, or a `squish`-style crate if it goes in `src/pipeline`, which is the right home for a bake-time concern). Those files are 193.6 MB and full chains add roughly a third, so **re-check `rose.vfs` against the 2 GB rollover limit after such a bake**.

Ruled out statically before any of this: `PERFORMANCE=4` indexes `c_iPeformances {5,4,3,2,1}` to quality level 1, which leaves `texture_loading_format` 0 and `tex->get_format()` at `ZZ_FMT_UNKNOWN` — D3DX reads that as "keep the file's format" — and `texture_loading_scale` 0, so there is **no format conversion and no rescale**. Both were better suspects than they turned out to be.

`r_d3d: slow texture create` in **`error.txt`** (not `client.log` — it is a `ZZ_LOG`) names any create over 2 ms with its path, `src_mips` and `req_mips`. An in-game capture settled it past correlation: **196 of 196 slow creates had `src_mips=1`**, no exceptions, costing 1300 ms across 163 distinct files in one short session.

Fixed in the data by `scripts/add-dds-mipmaps.py`, which rebuilds every chainless DDS through the already-vendored `thirdparty/directxtex-2020.9.30/texconv.exe`. 1256 files, 193.6 MB -> 259.1 MB. Its docstring carries the reasoning and the traps (`-dx9` is mandatory or the client silently cannot load the file; backups live outside `data/` because `pack.rs` has no extension filter and would bake a `.bak` into the archive).

Result, same route: texture create went from **100.1 ms to 1.5 ms** for a comparable batch (66.8 -> 1.5 ms for the identical 6 textures on one frame), slow creates from **196 to 2**, and the worst frame in the session from **139.6 ms to 30.7 ms**. The two survivors are the 1024x1024 sky textures at 7.0 and 2.4 ms, now with `src_mips=11` — the honest cost of a texture that size, not a defect.

**`vfgetdata()` is a trap — do not use it.** It looks like a free whole-file pointer and returns `pVFH->pData + pVFH->iAllocOffset` with no null check, while `vfread` checks `pData` precisely because it is legitimately NULL for a handle whose data was never preloaded. For such a handle it hands back a small **non-NULL** garbage pointer that passes any sanity test and faults on first use. `zz_vfs_pkg_buffered` was written against it and killed the client a second after the window appeared; it now owns its buffer and fills it with one ordinary `read_`. Note `error.txt` still showed the *previous* session throughout, because the engine log is buffered — `client.log` is what showed startup stopping right after `Init_DEVICE`.

**Lightmap atlases are excluded, and that was learned the hard way.** The first run converted 354 of them and produced a dark wash on map objects that appeared at distance and vanished as you walked in — a lightmap multiplies into object colour, so bleeding between the atlas's gutterless cells reads exactly like that. The engine still caps loads at 3 levels, but those levels now come from texconv's default FANT filter, whose support reaches past one texel, instead of D3DX's strict 2x2 box. The root `CLAUDE.md` already warned that chains are unsafe for these; the script now skips anything under a `LIGHTMAP` path, and `--restore-excluded` puts back files a newly added exclusion says should never have been touched.

**This pushes the archive over the rollover threshold.** `rose.vfs` was 1.93 GB against `pack.rs`'s `VFS_MAX_BYTES` of 1.90 GB, so the next bake produces `rose.vfs` **and `rose_2.vfs`** — both must ship alongside `data.idx`. See the root `CLAUDE.md` on the 2 GB limit; the failure mode for a missing second archive is a Lua parse error at startup that points nowhere near the cause.
<!-- verbatim:end -->

## Updates

- **2026-09-24 (migration, status: historical qualification, unverified).** The 1.90 GB `VFS_MAX_BYTES` cited above predates the 2 GB -> 4 GB offset change; the current rollover is documented as 4.2 GB in [project/vfs-offset-limit.md](../project/vfs-offset-limit.md). C-002 in [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md).
