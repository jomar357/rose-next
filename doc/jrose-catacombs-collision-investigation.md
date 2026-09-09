# Jrose catacombs: collision and Rose Next walkability

Third investigative pass, 2026-09-09. Companion to [the topology, mesh and protocol report](jrose-catacombs-investigation.md).

Reference client: `C:\Users\Thomas\Desktop\Testclients\Jrose`. Rose Next source reviewed at commit `a01b7f6f`. This pass changes research Markdown only. No client, engine, server, game data or database was changed, and no game process was launched.

## Finding

**Jrose makes the maze solid through ordinary, per-part ZSC collision flags and the transformed ZMS triangles. It also explicitly substitutes a flat Z = 0 ground-height function for the catacomb zones.** The topology grid and model IDs alone do not supply all of that behavior.

Rose Next already has the corresponding triangle collision machinery. Its existing terrain-height, terrain-picking, scene residency and server movement-grid paths still require integration with procedural instances. Importing the models without addressing those paths is insufficient.

Evidence recovered in this pass:

- Exact collision flags and parent relationships for all **225 nonempty part records** across the ten floor ZSCs; **130 records have collision enabled**.
- All **37 referenced ZMS paths** parsed, including **26 collision-enabled mesh paths**. Meshes, transforms, parent tags and collision flags are identical across B1–B5 within each visual family; materials are outside this comparison.
- Native calls that read the collision property, assign it to each visible node, apply root transforms and insert the hierarchy into the scene.
- A native **flat-ground override**, a separate procedural picking path, and evidence that dungeon geometry has its own residency management.
- **128 offline mesh assemblies** checked against the recovered topology. All tested open connections, solid-neighbor barriers and ground probes passed. These are geometry checks, not a live Rose Next engine test.

## 1. Collision is an object-part property

ZSC property **29 / `0x1D`** contains a little-endian signed 16-bit collision level. Missing property means zero for a newly constructed fixed part.

Native evidence:

| Jrose VA | Behavior |
|---|---|
| `0x428F40–0x428FB0` | Fixed-part constructor initializes collision field `+0x4A` to zero |
| `0x429140`, collision branch `0x429207–0x429227` | Property reader stores a nonzero collision value in `part + 0x4A` |
| `0x57B250`, call `0x57B2F8` | Dungeon model recursively creates parts through the shared fixed-part loader |
| `0x4293F0`, call `0x42950F` | Loader reads `part + 0x4A` and applies it to the created visible node |
| `0x5D1590` | Collision setter stores the supplied value in `visible + 0x1F4` |
| `0x5D15C0` | Height-only query reads bit 5 of that same field |
| `0x57A498`, `0x57A4D3`, `0x57A4F4` | Apply model scale, rotation, then scene insertion |

The corresponding Rose Next functions are `CFixedPART::Load` and `CFixedPART::LoadVisible` in [io_model.cpp](../src/client/io_model.cpp), and `setCollisionLevel` in [zz_interface.cpp](../src/engine/src/zz_interface.cpp). The native code and source agree on this storage and call pattern. No separate collision-mesh filename is referenced by the traced dungeon part path.

Relevant Rose Next flag values from [zz_type.h](../src/engine/include/zz_type.h):

| Value | Meaning |
|---|---|
| `0x00` | Collision disabled |
| `0x04` | Polygon collision |
| `0x08` | `NOTMOVEABLE` modifier |
| `0x0C` | Polygon collision plus `NOTMOVEABLE` |
| `0x20` | Height-only modifier; absent from the audited catacomb parts |

**Do not translate `0x0C` into “block the entire maze cell.”** The value occurs on ordinary floor planes as well as walls. Rose Next's local-avatar body/foot queries intersect the triangles, while some other query paths use the modifier as a filter. The meaning depends on the consumer.

### Exact part inventory

Part indices below are zero-based within each ZSC object. Object IDs are the original sparse ZSC slots, not mesh-array indices.

| Family | Object IDs | Collision-enabled parts | Disabled parts |
|---|---|---|---|
| Reminiscence | Floor 1 | Part 0: `0x04` | — |
| Reminiscence | Floors 17, 33, 49, 65–68 | Part 0: `0x0C` | — |
| Reminiscence | Walls 81, 97, 113, 129 | Part 0: `0x0C` | — |
| Reminiscence | Ceilings 161, 177, 193, 209, 225 | — | Part 0: `0x00` |
| Sorrow | Floors 1, 17, 33, 49, 65–68 | Part 0: `0x0C` | — |
| Sorrow | Wall 81 | Parts 0 and 2: `0x0C` | Parts 1, 3, 4 |
| Sorrow | Wall 97 | Part 0: `0x0C` | Parts 1, 2 |
| Sorrow | Wall 113 | **Part 1: `0x0C`** | **Part 0** |
| Sorrow | Wall 129 | Parts 0 and 2: `0x0C` | Parts 1, 3, 4 |
| Sorrow | Ceilings 161, 177, 193, 209, 225 | — | Part 0: `0x00` |

Per floor ZSC: Reminiscence has 17 parts, 12 with collision; Sorrow has 28 parts, 14 with collision. The full nonempty object-slot inventory contains respectively **1,924** and **366** collision-enabled triangle records, counting repeated floor variants separately and retaining degenerate faces.

The most consequential hierarchy case is **Sorrow wall 113**:

```text
part 0: wall_c_1_1_L00.zms       collision 0, root
  part 1: wall_c_1_1_L00_P01.zms  collision 12, parent = part 0
```

A root-only collision exporter would omit this wall. Keeping decorative children indiscriminately is also wrong: many other Sorrow children intentionally have collision disabled.

Every audited part has local translation `(0,0,0)`, local scale `(1,1,1)`, and quaternion `(w,x,y,z)=(-1,0,0,0)`, which is an identity rotation. The stored parent tag is 0 for roots and 1 for children; the loader subtracts one, yielding parent -1 or 0. Every live object has one root, and its children inherit that root's maze transform.

All ten ZSCs have zero cylinder radius/offset records for their nonempty objects. These assets therefore do not supply the optional tree-style collision cylinders consumed by Rose Next's monster correction code.

## 2. Units, transforms and ground height

The ZMS7/8 vertices are in engine metres. Rose Next's `zz_mesh_tool::load_mesh_8` reads these positions directly; it does not multiply them by `ZZ_SCALE_IN`. Engine API positions and collision radii are supplied in client world units and converted by 0.01 at the interface boundary. **Scale values are dimensionless and are not converted.**

For these assets, the recovered transform is:

```text
engine_position = (floor_origin_world / 100)
                + (15*x, 15*y, 0)
                + rotate_Z(orientation * 90 degrees, 15 * mesh_vertex)
```

The floor origin here is its XY origin with Z = 0. The cell position is its center. Apply the root scale once; children already inherit it. Do not pre-scale ZMS7/8 vertices by 0.01 or apply a second factor of 15 to children.

Measured mesh examples:

- Reminiscence floors span exactly `[-0.5,+0.5]` in local X/Y and have Z = 0: a **15 × 15 metre** tile after scaling.
- Sorrow floors differ from those limits by tiny exporter float errors. Their nominal tile-edge gap after scaling is about **8 micrometres**, and their maximum absolute vertex Z is about **0.33 micrometres**. Offline ground probes allow a small barycentric tolerance rather than treating those export errors as intentional holes.
- Main wall geometry reaches local Z ≈ 1.5, or **22.5 metres** after scaling. Some wall extents reach ±0.58, extending beyond the nominal half-cell boundary. A box that covers only the 15-metre tile footprint is not a faithful geometry bound.
- Ceilings are visible geometry with collision zero. They do not act as overhead collision surfaces in the audited data.

### The flat-ground hook is explicit

The terrain-height routine at **`0x42C4B0`** recognizes zones 76 and 77 and branches to **`0x42C5F5`**. It clears the optional missing-terrain indicator and, when the dungeon instance exists, calls **`0x5791F0`**:

```asm
0x5791F0  fldz
0x5791F2  ret 8
```

That function returns **0.0 for every X/Y**. If no instance exists on this branch, the fallback also returns zero. This is direct evidence that Jrose does not obtain catacomb ground height by sampling the reused Ramesses map heightfield.

Rose Next's [CTERRAIN::GetHeight](../src/client/io_terrain.cpp) currently looks up a terrain map and calls `CMAP::GetHEIGHT`; a missing map returns zero but reports missing terrain. Accidental zero from missing terrain is not equivalent to the explicit dungeon path. Avatar collision responses also clamp height against this terrain value, so an underlying heightfield above the generated floor can lift the avatar even when the mesh placement is correct.

There is a separate monster-height concern: `AdjustHeight_Monster` calls `CTERRAIN::GetHeightTop`, whose `getWorldObjectHeightInScene` implementation **skips `NOTMOVEABLE` nodes**. Consequently it skips all Sorrow floor pieces and most Reminiscence floor pieces. An intentional flat-ground service at Z = 0 is compatible with these flags; relying on that helper to discover the floor triangles is not.

A future implementation should route ground height, terrain normal/slope behavior and actor placement through a consistent dungeon policy. Z = 0 is recovered; the exact choice of new engine interfaces is an implementation decision. Do not globally alter ordinary-zone height behavior to accommodate the catacombs.

## 3. Scene insertion, collision queries and picking

The dungeon object wrapper's scale and rotation helpers (`0x57B020`, `0x57B1E0`) operate on the root node. Insertion helper **`0x57B000 → 0x5CE7F0`** inserts that hierarchy after the transforms are set. The geometry update creates nearby cell objects and later destroys objects whose residency counters expire (`0x57A59E–0x57A642`). Geometry residency therefore also controls availability of mesh collision.

Rose Next's corresponding engine behavior is visible in [zz_visible.cpp](../src/engine/src/zz_visible.cpp):

- `insert_scene()` refreshes bounds and propagates insertion to children.
- `gather_collidable()` checks each node's own nonzero collision level and then recursively visits children even if the parent's level is zero.
- `test_intersection_sphere()` requests triangle collision. `zz_mesh_tool::test_intersection_mesh_sphere` transforms the sphere into mesh-local coordinates, including its radius, and tests the ZMS faces.
- Ray queries use the transformed mesh triangles. Setting a collision flag without inserting the node into the scene does not make it available to scene-wide collection.

The local-avatar path in [cobjchar_collision.cpp](../src/client/cobjchar_collision.cpp) collects nearby nodes through `collectByMinMaxVec3`, builds body/foot probes, and uses triangle-sphere tests and a movement ray. Its collision response restores the previous position, sends `CLI_CANTMOVE`, and stops movement. The avatar body-front radius is **30 world units / 0.30 m**; the foot-front radius is **20 units / 0.20 m**. Their positions depend on animation/model COM and facing. These are not a single universal capsule around the actor pivot.

The shared `ZZ_TYPE_MODEL` exclusion matters: `CollectContact` skips descendants of character-model nodes. Generated architecture should use the fixed-visible hierarchy, or another integration that preserves its collision visibility, rather than being attached under a character model for convenience.

**Residency requirement:** nearby collision must remain queryable when the camera turns away, while the player crosses a streaming boundary, and immediately after entering a new floor. Rose Next's ordinary patch removal also removes its fixed objects from the engine scene. Its existing geometry-derived bounds work should be respected; do not use the cached ZSC object box as the sole world collision/residency extent. See [the workspace bounding-box investigation](zsc-bounding-boxes.md). This pass traced the relevant lifetimes but did not run a live streaming test.

### Clicking on a generated floor is a separate integration point

Jrose has a dungeon branch in terrain picking at **`0x42ABD0`**, routing through **`0x42AC36 → 0x579200 → 0x579D40`**. It scans instantiated primary cell objects, calls **`0x57B0E0`** across their parts, and chooses the nearest reported mesh-ray intersection through engine `intersectRay` at **`0x5D08C0`**. This path does not require a terrain patch beneath the mouse ray. It considers primary floor/wall objects rather than the separate ceiling pointer.

Rose Next's `CTERRAIN::Pick_POSITION` currently delegates to [CPatchManager::Pick_POSITION](../src/client/terrain/patchmanager.cpp). The latter iterates terrain patches. [CGameStateMain::Pick_POSITION](../src/client/system/cgamestatemain.cpp) combines that result with object picking and a sky fallback. An inserted raw floor visible is therefore not automatically a movement destination through this terrain-picking path. Procedural floor picking needs a deliberate route; ordinary terrain or sky hits can otherwise conceal the missing integration.

## 4. The server movement grid is independent

Rose Next's [CZoneFILE](../src/sho_gameserver/src/zonefile.h) stores a **500-world-unit / 5-metre** movement grid. `IsMovablePOS` considers a cleared bit movable. [LoadZONE and LoadMOV](../src/sho_gameserver/src/zonefile.cpp) initialize bits as blocked and clear cells where a `.MOV` byte is zero. Missing `.MOV` files do not populate a generated maze's movement data.

The AI method [CObjCHAR::SetCMD_MOVE2D](../src/sho_gameserver/src/cobjchar.cpp) checks the destination through `IsMovablePOS`. This is a destination test, not proof that the line to that destination avoids intervening walls. The avatar movement path instead relies in part on client collision feedback through [classUSER::Recv_cli_CANTMOVE](../src/sho_gameserver/src/gs_user.cpp). Neither path currently derives a new movement grid from the recovered catacomb seed.

Therefore the client triangles and a server movement representation are both required. A proposed server implementation can derive occupancy from the same seeded layout, but must account for cell-center alignment, wall protrusions, actor clearance and paths between cells. **Three 5-metre grid widths equal one 15-metre maze cell; that dimensional ratio alone does not establish index alignment or make every point in a passage cell traversable.** The original Jrose server's navigation representation was not recovered.

The optional client monster-cylinder system is not a substitute: these ZSCs provide no cylinders, and `AdjustHeight_Monster` is not the local-avatar triangle-blocking path. A visually correct local-player collision result would not prove monster chase, summon movement or server-authoritative movement is correct.

## 5. Offline geometry checks and their limits

The test reconstructed the **64 generator fixtures** listed in the main report, each with the two collision mesh families: **128 assemblies**, using descriptor flags 0. This includes format-control dimensions beyond the live floor rows. Geometry equivalence across the five floor ZSCs per family was checked separately.

All transforms were applied to actual ZMS triangles with hierarchy and collision flags preserved. The geometric calculations used metre coordinates, exact quarter-turn matrices and double-precision arithmetic. They were run outside the game; they do not reproduce engine broad-phase collection, float rounding, animation COM, frame ordering or network movement.

| Probe | Count | Result |
|---|---:|---|
| Cardinal connection between two open cells; each undirected edge once | 30,240 | No collision within the tested 0.30 m swept radius at Z = 1.125 m |
| Open cell toward an adjacent solid-cell center | 38,848 | Each segment met collision geometry, within 0.0001 m intersection tolerance |
| Ground support at seven evenly spaced points on each open connection | 211,680 | All found floor triangles near Z = 0 |

The Z = 1.125 m probe corresponds to the height of the horizontal movement ray in Rose Next's avatar collision code when the previous pivot is at Z = 0. Sweeping a 0.30 m radius there is a useful geometry-clearance check; it is **not an exact replay of the avatar's animation-dependent body and foot probes**.

The segment/triangle clearance calculation checks endpoint-to-triangle distance, triangle-edge-to-segment distance, and segment/face intersection. Candidate triangle bounds are expanded around the segment by 0.31 m, covering the tested 0.30 m radius. Ground support uses XY triangle barycentric coordinates with tolerance `1e-6` and accepts surface Z within 0.001 m of the plane. Maximum observed accepted floor deviation was **`3.2783542814304707e-7 m`**.

Two deliberate mistakes established that the checks detect meaningful failures, using the 15 × 15, floor-seed-12345 fixture with Sorrow meshes:

- Omitting wall 113's collision child produced **5 missing-wall probes**.
- Applying an extra 0.01 scale conversion produced **180 missing-wall probes** and **620 missing-ground probes**.

These results establish viable center-to-center routes and collision barriers in the sampled assembled geometry. They do not establish every off-center route, diagonal corner behavior, all seeds, step/slide response, cart/castle-gear clearance, high-speed tunneling, or live scene residency.

### Reproducible collision-geometry fingerprints

The appendix below supplies a canonical snapshot recipe for a developer to compare their imported collision parts. It consumes the main report's verified 20-byte cell descriptors and the reference ZSC/ZMS files. The serialization is a research comparison format, not a game format or a native physics-state hash.

Fixture: `Maze(12345, 15, 15, 1)`, descriptor flags 0, floor XY origin `(0,0)`, Z = 0. The same result was obtained using each of B1–B5's ZSCs within its family.

| Mesh family | Emitted collidable part instances | Triangle records | Snapshot SHA-256 |
|---|---:|---:|---|
| Reminiscence | 225 | 57,402 | `8a7c00a3d89e6988a851884bba4bd95a718f97560ade80b9129ca03d7b51b2d1` |
| Sorrow | 249 | 11,020 | `54f33e160b4d4d797eac4b81977aaeb7df2d97ad6bafe7ea2c3ab5816f330600` |

Matching this hash verifies the specified part/flag/triangle emission and canonical transform recipe. It does **not** certify Rose Next runtime collision. Unlike the main report's instruction-emulator comparisons, these fingerprints are generated from the decoded assets and research recipe.

## 6. What developers should validate in Rose Next

The next useful step is a temporary engine integration fixture, using the seeded descriptors and original collision parts, with these acceptance cases:

1. **Ground:** spawn local player, remote player, monster and summon on ordinary corridors and room tiles. They remain on the dungeon plane regardless of the reused outdoor terrain data; slope/normal queries agree with that plane.
2. **Collision hierarchy:** Sorrow wall 113 blocks movement with root collision zero. Decorative non-colliding parts and ceilings stay excluded.
3. **Movement:** follow the center-to-center route, approach walls and corners from several directions, and verify body/foot response at normal and high movement speeds. Test allowed vehicle/body sizes separately.
4. **Picking:** clicks hit generated floors/walls at the correct world position without requiring an unrelated terrain patch or sky fallback.
5. **Residency:** camera turns, nearby-cell loads, floor entry and floor teardown preserve the intended collision lifetime. Removed floors leave no stale nodes; the destination floor is queryable before actor simulation resumes.
6. **Server agreement:** generated occupancy and path handling keep NPCs/summons out of walls; client stop feedback and server movement remain consistent. A valid destination on the other side of a wall must not be mistaken for a clear route.

The original client now provides enough evidence to specify collision data, transforms, the ground plane and the picking/insertion interfaces. The remaining uncertainty is their integration and behavior in a running Rose Next instance, plus the unrecovered original server navigation policy.

## Appendix: canonical collision snapshot recipe

Extract this Python block into a temporary research script, or execute it alongside the main report's Appendices A and C. It uses the existing workspace's `scripts/import-oro.py` reader without changing it. The recipe deliberately asserts the audited catacomb transforms and parent structure; it is not a general-purpose ZSC hierarchy importer.

```python
import hashlib
import importlib.util
from pathlib import Path
import struct


def zms_triangles(path):
    """Read static ZMS7/8 triangle positions in mesh metres."""
    data = Path(path).read_bytes()
    offset = data.index(0) + 1
    version = data[:offset - 1]
    assert version in (b"ZMS0007", b"ZMS0008")
    flags = struct.unpack_from("<I", data, offset)[0]
    offset += 28  # format + min/max
    bones = struct.unpack_from("<H", data, offset)[0]
    offset += 2 + bones * 2
    count = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    vertices = list(struct.iter_unpack("<3f", data[offset:offset + count * 12]))
    offset += count * 12
    for mask, stride in ((4, 12), (8, 16), (16, 16), (32, 8), (64, 12),
                         (128, 8), (256, 8), (512, 8), (1024, 8)):
        if flags & mask:
            offset += count * stride
    count = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    faces = list(struct.iter_unpack("<3H", data[offset:offset + count * 6]))
    assert all(index < len(vertices) for face in faces for index in face)
    offset += count * 6
    for _ in range(2):  # material runs, strips
        count = struct.unpack_from("<H", data, offset)[0]
        offset += 2 + count * 2
    if version == b"ZMS0008":
        offset += 2
    assert offset == len(data)
    return [[vertices[i] for i in face] for face in faces]


def zsc_properties(raw):
    result = {}
    offset = 0
    while raw[offset]:
        tag, length = raw[offset:offset + 2]
        offset += 2
        result[tag] = raw[offset:offset + length]
        offset += length
    return result


def collision_snapshot(workspace, reference, zsc_relative, cells, width, height):
    """Canonical research snapshot, NOT a serialized game/physics format.

    cells: normalized 20-byte records from the main report's Appendix C.
    Origin is (0,0,0), coordinates are metres, rotations are exact quarter turns.
    Only nonzero-collision parts of each primary cell object are included.
    All audited ceilings are collision-zero. Do not generalize this shortcut.
    """
    spec = importlib.util.spec_from_file_location(
        "catacomb_zsc_reader", Path(workspace) / "scripts/import-oro.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    reference = Path(reference)
    zsc = reader.Zsc(reference / zsc_relative)
    digest = hashlib.sha256()
    digest.update(b"KCC-COLLISION-SNAPSHOT-v1\0")
    digest.update(struct.pack("<HH", width, height))
    cache = {}
    part_count = triangle_count = 0
    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 20
            obj = struct.unpack_from("<H", cells, offset + 8)[0]
            rotation = cells[offset + 14]
            if obj == 0:
                continue
            for part_index, (mesh_id, material_id, raw) in enumerate(zsc.objects[obj][1]):
                props = zsc_properties(raw)
                # These assertions deliberately restrict this recipe to audited data.
                assert struct.unpack("<3f", props[1]) == (0., 0., 0.)
                assert struct.unpack("<4f", props[2]) == (-1., 0., 0., 0.)
                assert struct.unpack("<3f", props[3]) == (1., 1., 1.)
                assert struct.unpack("<h", props[7])[0] == (0 if part_index == 0 else 1)
                level = struct.unpack("<h", props.get(29, b"\0\0"))[0]
                if level == 0:
                    continue
                mesh_path = zsc.meshes[mesh_id].decode("cp932")
                if mesh_path not in cache:
                    cache[mesh_path] = zms_triangles(reference / mesh_path)
                triangles = cache[mesh_path]
                digest.update(struct.pack("<6HI", x, y, obj, part_index,
                                          level, rotation, len(triangles)))
                for triangle in triangles:
                    for vx, vy, vz in triangle:
                        # Parent transforms are identity; root scale is applied ONCE.
                        rx, ry = ((vx, vy), (-vy, vx), (-vx, -vy), (vy, -vx))[rotation]
                        xyz = (15 * (x + rx), 15 * (y + ry), 15 * vz)
                        # Canonicalize negative zero before packing float64 values.
                        digest.update(struct.pack("<3d", *(0. if v == 0 else v for v in xyz)))
                part_count += 1
                triangle_count += len(triangles)
    return digest.hexdigest(), part_count, triangle_count
```

Example, with `Maze` and `catacomb_descriptors` loaded from the main report:

```python
workspace = Path(r"C:\Users\Thomas\Desktop\Rose\rose-next-classic")
reference = Path(r"C:\Users\Thomas\Desktop\Testclients\Jrose")
maze = Maze(12345, 15, 15, 1)
cells, _ = catacomb_descriptors(maze.g, 15, 15, 12345)
result = collision_snapshot(
    workspace, reference,
    "3Ddata/MAPS/KARKIA/KCATACOMB/KCATACOMB0201.ZSC", cells, 15, 15)
assert result == (
    "54f33e160b4d4d797eac4b81977aaeb7df2d97ad6bafe7ea2c3ab5816f330600",
    249, 11020)
```
