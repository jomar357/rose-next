# Coplanar map-object placements flicker

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 399-446 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=399-446 sha256=b04484901baa81a4253034b0c9bc4a15ba3165a64274a9c1f247b88aabc849e1 -->
### Coplanar Placements Flicker; Depth Precision Cannot Save Them (Data)

A wall that "flashes" while the camera moves and settles a few seconds after it
stops is two **placements** of one map object with faces in exactly the same plane.
Junon Polis tiles its fountain-square wall with one 20 m segment (DECO 161
`portstairwall01`) at 10-19 m strides, so consecutive copies overlap by 0.6-9.8 m at
0.000 cm separation; the visible shape is the overlap region (a 61 cm stride
remainder reads as a thin line, a 6.35 m one as a big square), and it shows only
where the copies' per-placement lightmap cells disagree, since the mesh and texture
are otherwise identical. It reproduces in every ROSE client because the data is the
same, and the 24-bit depth buffer cannot touch it: the separation is zero, and a
depth bias has no way to tell the two apart. The "few seconds" is
`zz_camera_follow::interpolate_camera`, which approaches its target exponentially
and keeps creeping by sub-pixel amounts after the mouse is released; a bit-stable
camera gives a stable (if arbitrary) winner per pixel.

`scripts/fix-coplanar-object-overlaps.py` (2026-09-22; `--dry-run`/`--verify`/
`--restore`, manifest in `build/coplanar-overlaps/`) scans every zone's IFOs against
real ZMS geometry and moves one placement of each fighting pair by the smallest
multiple of 0.5 cm along a direction chosen per node, so every pair ends >= 1 cm
apart, then re-checks the moved geometry with the client's own float32 rounding
before writing. It rewrites only the twelve position bytes of a record. Across 60
zone rows it found 612 fighting pairs in 25 map folders (Union War, Golden
Colosseum, Junon Polis, Sikuku Prison, Junon Cartel and Forgotten Temple B1 carry
almost all; field maps are clean) and moved 594 records, most by 1.5-2 cm, none by
more than 7.5 cm. Applied 2026-09-22, not yet validated in game. Run it after any
`import-*.py` that brings in map files, then bake.

Things that will bite:

- **Never delete a duplicate record.** `CMAP::LoadLightMapINFO` keys objects by
  1-based ordinal within the lump, so removing a record shifts every lightmap after
  it. An exact duplicate (same object, transform and position, usually a building
  written into two neighbouring chunk files: Junon Polis DECO 153) is coplanar on
  every face and cannot be separated by any nudge; the script **sinks** the later
  record 100 m instead.
- **Back-to-back faces are not a fight.** Map materials default to
  `ZZ_CULLMODE_CW`, so one placement's top lying on another's bottom never draws
  against it; the detector keeps the facing sign (dropping it doubled Union War's
  count and pushed a stone wall 6 cm into the ground to dodge a phantom).
- **Near pairs are constraints.** Two copies 1-13 cm apart are not fighting, but a
  naive move of a neighbour makes them so; the planner carries signed per-plane
  separations for every pair inside that band and plans against 1.2 cm to absorb
  the rounding of normals and of float32 positions (an ulp is 1/16 cm at world
  scale), which is what left 0.86-0.92 cm gaps on the first attempt.
- Same-placement part overlaps (`road01`/`road01top`) are out of scope: they are a
  ZSC matter, already non-zero, and covered by the depth-buffer work above.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
