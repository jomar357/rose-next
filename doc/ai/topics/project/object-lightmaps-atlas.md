# Object lightmaps are a gutterless atlas

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 447-469 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=447-469 sha256=7264b15f309b2034ed23220a3a0f8ba9c6ddca3ff092e9a5244e94064c6736d9 -->
### Object Lightmaps Are A Gutterless Atlas (Engine)

Each map-object *part* gets one cell of a shared lightmap texture — `OBJECT_128_0.DDS`
is a 4x4 grid of 128 px cells — and `SetLightMap` addresses it with a UV transform
applied in the vertex shader (`(uv + cell_xy) / grid_n`). There is **no padding between
cells**, so mipmapping, which knows nothing about the grid, would blend a part's
lighting with its neighbours' at low enough mip levels.

It cannot happen, and the reason is one line of Lua: `data/SCRIPTS/INIT.LUA:33` calls
`setMipmapLevel(3)`, which caps every texture at three mip levels. A 512 px atlas only
ever gets 512 -> 256 -> 128, and across every atlas we ship the smallest cell stays at
8x8 texels — bleeding needs cells under about 2. **Grepping `src/` alone says the
opposite**, because the DDS files do carry full mip chains down to 1x1 and the C++
defaults do not cap anything; this is the same trap as `setLazyBufferSize`.

So: treat `mipmap_level = -1` (load the file's full chain) as unsafe for lightmapped
map objects. `setDisplayQualityLevel` levels 3 and 4 set exactly that — level 5 escapes
it only by disabling lightmaps outright. If it ever did appear it would be a flat,
uniform brightness shift over a whole part with neighbouring parts of the same object
drifting out of agreement, never bands and never a sharp onset; it is also
self-limiting, since the mip level tracks screen size and a cell only falls under a
texel once the part is a couple of pixels across.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
