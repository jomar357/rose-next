# Cull bounds come from geometry, not the ZSC

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 285-331 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=285-331 sha256=c8a116965142d04b05f1fcdd200d1242d6afe926d13e01e6fc406cb437e54094 -->
### Cull Bounds Come From Geometry, Not From The ZSC (Client/Engine)

Every ZSC object record caches a model-space AABB, and **it is wrong in every ZSC in
the game**: the exporter scaled only X into world units (cm) and left Y and Z in mesh
units, so the stored box is ~100x too thin and ~100x too short. Retail Junon has it too,
so it is not an import artefact. Muris' canyon walls registered as a 336 m x 4.0 m x
1.1 m ribbon on the ground instead of a 336 m x 396 m x 114 m wall; because fixed
objects live or die with their terrain patch, turning the camera pushed the ribbon out
of the frustum and `RemoveFromScene()` deleted the whole wall mid-screen. 222 of the
1388 map objects in `data/` under-cover by more than 20 m, the worst by 970 m (Junon
Polis' planet vessel).

It only ever mattered because we re-enabled patch culling: the original
`ViewCullingFunc` had its condition commented out around an unconditional `return 0`,
so every patch was "fully inside" every frame and the boxes were inert. *Re-enabling
dead code promotes its inputs from decorative to load-bearing* — the same shape as the
missing-asset retry storm below.

`CMAP_PATCH::MakeAABBFromObject` now asks the engine for the world AABB it already
derives from real mesh min/max (`getVisibleWorldMinMax` -> `CObjFIXED::GetWorldMinMax`),
keeping the cached box only as a fallback. This is safe at map-load time because
`loadMesh` reads the ZMS header min/max **eagerly**, independent of lazy geometry
loading, and `loadVisible` builds each part's OBB before the object is ever inserted
into the scene.

Things that will bite:

- **The client now imports a new engine export, so `rosenext.exe` and `znzin.dll` must
  be deployed as a pair.** A new exe against an old DLL will not start. `scripts/ab-build.ps1`
  exists for this constraint.
- **Mesh units depend on the ZMS version.** `load_mesh_minmax` applies `ZZ_XFORM_IN`
  (x0.01) for version < 7 only, so v7/v8 headers are metres and v6 headers are already
  cm. We ship 22 v6 meshes.
- `ViewCullingFunc` tests only **four** frustum planes (near, far, left, right — never
  top or bottom), so vertical FOV culls nothing and the commented-out z comparisons in
  `CompareSizePath2Obj` are not worth restoring on their own.
- A narrow residual remains: an object that fits inside its patch's 10 m footprint but
  towers over local terrain never gets `ExPatchEnable` and is still culled by a
  terrain-only z. See the doc for why the obvious one-line fix is insufficient.

`scripts/audit-zsc-bounds.py` is the verification tool: read-only by default, it
re-derives the correct box from ZMS headers plus part transforms, proves the axis-scale
signature per file, ranks objects whose geometry escapes their stored box, flags boxes
that are corruptly *over*sized, and reports missing mesh files. Run it after any
`import-*.py` that appends ZSC objects. Full record in
[doc/zsc-bounding-boxes.md](../../../zsc-bounding-boxes.md).

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
