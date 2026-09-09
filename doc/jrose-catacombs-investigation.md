# Jrose catacombs: maze, entry and progression investigation

Investigated: 2026-09-09. Reference: `C:\Users\Thomas\Desktop\Testclients\Jrose`.

Scope: **追想のカタコンベ** (Catacombs of Reminiscence) and **悲愴のカタコンベ** (Catacombs of Sorrow), entered from **荒れ果てた共同墓地** on Karkia. This is a research document. No Rose Next game code or data was changed. No game process, launcher or server was started; footage was deferred.

## What was recovered

**The actual deterministic maze generator survives in TRose.exe.** This investigation recovered its seed input, floor configuration, random-number recurrence, room placement and wall construction. A Python transcription included below matched the original instructions byte for byte in 64 emulator comparisons. This is substantially stronger evidence than inferring a generic maze algorithm from screenshots.

Also recovered:

- Both dungeon identities, all five floor sizes, and their complete directly referenced ZSC assets.
- The two cemetery entrance objects, injected by native code rather than stored in the cemetery IFO event-object lumps.
- The common dungeon packet family: seed/time initialization, movement request, shared exploration and dungeon key/progression state.
- Local versus remotely reported exploration brushes, plus a server-triggered full-map reveal operation.
- Actual catacomb boss IDs, quest completion hooks, and chest-to-mimic behavior.
- **Second pass:** neighborhood-to-mesh classification, quarter-turn rotations and seeded model selection; 256 complete cell-buffer comparisons matched the original instructions.
- **Second pass:** the entry window's daily eligibility, two payment alternatives and leader sponsorship records, plus the independent minimap cell-marker packet.
- **Third pass:** per-part collision flags/hierarchies, flat Z = 0 ground override, procedural picking and Rose Next integration requirements. See [the collision investigation](jrose-catacombs-collision-investigation.md), including 128 offline mesh assemblies and reproducible collision-geometry fingerprints.

Still unproven from the supplied client: the original server's population/placement algorithm, gatekeeper selection, daily reset and payment accounting, and enforcement details for party gathering, logout, timeouts and backtracking. Daily eligibility and leader sponsorship are now directly confirmed in the client UI, but their authoritative server implementations remain unavailable.

Evidence labels used below:

- **Binary/data:** directly read from this client or its assets.
- **Emulator-verified:** recovered instructions compared against the transcription in this document.
- **Historical:** published gameplay documentation, not proof of this executable's server configuration.
- **Unresolved:** no sufficient implementation evidence yet.

All EXE addresses below are virtual addresses at image base `0x400000`. STB row and column numbers use the workspace reader's zero-based indexing, including reserved row 0. Japanese text was decoded as CP932. The EXE SHA-256 is `536bb1cdd0f637a77d33e99eb08027876328195cf57a7545c150cf6d80b50041`.

## 1. Dungeon and floor data

`3Ddata/STB/LIST_ZONE.STB`, joined to `LIST_ZONE_S.STL`, identifies:

| Zone | Japanese name | Floor configuration |
|---|---|---|
| 76 | 追想のカタコンベ | `3Ddata/Maps/Karkia/KCatacomb/KCatacomb_Lv01.stb` |
| 77 | 悲愴のカタコンベ | `3Ddata/Maps/Karkia/KCatacomb/KCatacomb_Lv02.stb` |
| 87 | 荒れ果てた共同墓地 | Cemetery outdoor map |

Both dungeon zones use `3Ddata/Maps/Oro/ramesses/dungeon.zon` as the underlying zone and `Sound/BGM/Ramesses.ogg`. Their floor-table path is zone column 8. Their shared ZON does **not** mean they share one fixed maze.

The floor tables each contain reserved row 0 followed by five live rows. Their headers are `parts zsc`, `size X`, `size Y`, `num room`, `npc group`.

| Floor | Reminiscence grid | Room request | Sorrow grid | Room request |
|---|---:|---:|---:|---:|
| B1 | 15 × 15 | 1 | 15 × 15 | 1 |
| B2 | 17 × 17 | 1 | 17 × 17 | 1 |
| B3 | 19 × 19 | 1 | 19 × 19 | 1 |
| B4 | 21 × 21 | 2 | 21 × 21 | 1 |
| B5 | 25 × 25 | 2 | 21 × 21 | 1 |

Rows reference `KCATACOMB0101.ZSC` through `0105.ZSC` for zone 76 and `KCATACOMB0201.ZSC` through `0205.ZSC` for zone 77. Column 4 (`npc group`) is blank on all ten rows.

The loader at `0x576510` reads the zone's floor table. At `0x576763–0x5767A9`, it copies dimensions and splits column 3 into:

```text
requested_rooms = value % 1000
room_size_override = value / 1000     // integer division
```

Thus the catacombs use automatic room sizing. The column is not simply an unconditional count of finished rooms. The shared format also supports entries such as `7001` elsewhere: one requested room, size override 7.

Floor cells are **1,500 client coordinate units apart**, with a half-cell offset of 750 in world-to-cell conversion (`0x576860`, `0x5797DD`, `0x57AA87`). Under ROSE's centimeter convention this is 15 metres per cell. Grid dimensions include solid boundaries. A 25 × 25 grid therefore has a nominal 375-metre footprint, not 625 separate prebuilt rooms.

Do not include `KCATACOMB_LV03.STB` in these five-floor dungeons: it belongs to zone 78 and has six live floors.

## 2. Cemetery entrances are native additions

The cemetery's 49 IFO files did not supply these two entries as event-object records. The client adds them during map loading.

The native block beginning around `0x42FEDE` constructs records consumed by the loop at `0x430286–0x4303C5`. For zone 87:

| Entry selector | Constructed event ID | Position before ×100 conversion | Associated dungeon |
|---|---:|---|---|
| 1 | 1001 | X 4806.2827, Y 4786.8325, Z 41.4875 | Reminiscence |
| 2 | 1002 | X 5312.0317, Y 5030.1885, Z 35.0875 | Sorrow |

Both use `KCatacomb_Enter`. Coordinates come from EXE float constants at `0x707D34–0x707D3F` and `0x707D28–0x707D33`; insertion multiplies them into client world units. The association with each dungeon is corroborated by the historical entrance locations: approximately 4812/4786 and 5310/5040. See the [Reminiscence page](https://wikiwiki.jp/roseonline/Area/Khakia/%E8%BF%BD%E6%83%B3%E3%81%AE%E3%82%AB%E3%82%BF%E3%82%B3%E3%83%B3%E3%83%99) and [Sorrow page](https://wikiwiki.jp/roseonline/Area/Khakia/%E6%82%B2%E6%84%B4%E3%81%AE%E3%82%AB%E3%82%BF%E3%82%B3%E3%83%B3%E3%83%99).

The surviving plaintext `SCRIPTS/EVENTOBJECT_01.LUA` contains:

```lua
function KCatacomb_Enter(iObject)
    iIndex = SC_GetEventObjectIndex(iObject);
    SC_DgsOpen(iIndex);
end
```

Binding wrapper `0x421BD0` reaches `0x421290`, then the common entry routine `0x5368B0`. That routine checks the party leader case, validates the object and proximity, and converts an event ID back to the selector by subtracting 1000. The catacomb entry window title is at `0x71AF8C`, assigned by `0x5364A0`.

The second pass establishes the selector association directly: the `(u16 selector, u16 zone)` lookup table at **`0x71B0E0`** starts with `(1, 76), (2, 77)`, and the entry UI uses it at `0x536E73–0x536EBD` to select the zone name. The historical coordinates are corroboration, not the sole evidence for this mapping.

The entry proximity check at `0x536943` compares a three-dimensional Euclidean distance against **500 world units**, or 5 metres. While the leader's entry window is open, its update path at `0x5372BE` uses **1000 units**, or 10 metres, as the closure threshold. These are client UI checks, not proof of the server's admission radius for every participant.

Practical consequence: copying the outdoor map and CON files alone would omit these entrances. They need an equivalent runtime addition or deliberately authored replacement map objects.

## 3. Seeded generation: recovered implementation

### Seed flow

The common receive handler is `0x57B760`. Extension command **0x29** enters `0x57B812` and records a dungeon identity, mode byte, **16-bit seed**, and remaining time. The seed goes to global `0x7AB018`, then to the dungeon instance at offset `+6` during zone loading (`0x432295`).

`0x579480` builds the floor array. At `0x579729–0x579876`, it advances a 32-bit state once per floor and stores the low 16 bits into that floor's seed field `+0x18`:

```python
state = received_seed_u16
for floor in floors_in_table_order:
    state = ((4 * state + 1) * (state + 1)) & 0xffffffff
    floor.seed = state & 0xffff
```

The first floor uses the **advanced** seed, not the received value directly. Retain the full 32-bit state between floor assignments. Each floor then starts its own generator from its stored 16-bit seed.

`DgFloor::create` at `0x57A760` loads the floor's ZSC, initializes a temporary generator, applies the room-size override, and calls `0x57C5A0(seed, width, height, room_request)`. The error string `maze gen` at `0x720FBC` explicitly identifies this stage.

**Conclusion:** this client reconstructs the full geometry from a small seed and its local floor tables. It does not require a full tile-grid packet for initial maze construction. Server-side monster placement can still use additional state that is absent here.

### Random sequence and construction

The recurrence throughout the recovered generator is:

```python
state = ((4 * state + 1) * (state + 1)) & 0xffffffff
result = state % bound
```

This is not the C library `rand()` or a standard modern PRNG. Replacing it would change the layouts. Preserve every random call, including failed room-placement attempts and the direction swaps.

The recovered stages are:

1. Normalize dimensions to odd numbers, minimum 5. Initialize direction order `[0, 1, 2, 3]` and perform 1–3 random swaps.
2. Allocate a byte grid and mark its outside boundary solid.
3. Attempt large square rooms before building internal walls. The automatic outer room size is `(min(width, height) // divisor) | 1`, where divisor is 2 for one requested room and otherwise the requested room count. Without an override, automatic sizes below 7 disable room placement.
4. For each requested room, try up to 100 random even-coordinate origins. Four corner tests reject overlap/boundary collisions. Accepted rooms get solid perimeters and two opposing openings. Opening orientation is chosen by `random(10) < 5`.
5. Add internal walls on even-coordinate lattice points in two ordered passes, using shuffled cardinal directions. The first pass tries a random direction; the second connects remaining candidate points to an already marked neighbor. This is a wall-building algorithm, not a recursive depth-first corridor carver.

Generator storage is **column-major**: `grid[x * height + y]`. The renderable floor array is later populated in row-major order, with 20-byte cell records. Mixing these layouts transposes or scrambles non-square maps.

| Generator high bits | Meaning in this path | Render cell classification at `+0x0C` |
|---|---|---|
| `0x00` | Ordinary passage | 0 |
| `0x40` | Large-room interior/opening; low bits identify room | 1 |
| `0x80` | Out-of-bounds sentinel in access helpers | Default/unused classification |
| `0xC0` | Solid wall/boundary, including raw `0xFF` | `0xC0` |

Room placement returns the number successfully placed. All tested native catacomb configurations produced one room, including the B4/B5 configurations requesting two. This is a sample result, not an exhaustive claim about every possible seed. The raw table value must not be presented as proof of two guaranteed boss rooms.

### Verified example

Below is an actual generator output for **floor seed 12345**, 15 × 15, one requested room, automatic size. This is a synthetic test seed, not a captured historical run. `#` is solid; `.` is ordinary passage; `+` is room space/openings. Display Y runs from high to low.

```text
###############
#.#.....#.....#
#.#.#.#.###.#.#
#...#.#.....#.#
#.#########.#.#
#.#+++++#...#.#
#.#+++++#.#.#.#
#.+++++++.#.#.#
#.#+++++#.#.#.#
#.#+++++#.#.#.#
#.#########.#.#
#...#.......#.#
#.#.#.#.###.#.#
#.#...#.#...#.#
###############
```

Raw column-major byte-grid SHA-256: `8a5ee93ae42c590720bde4a97ae5714e6b6281938986b51887aa86ff4f8c4a2a`. There are 118 solid cells, 80 ordinary passage cells and 27 room/opening cells.

### Verification method and limits

Only the generator instruction range `0x57BD90–0x57C6AF` and its eight direction bytes at `0x721220` were copied into an isolated Unicorn x86 emulator. Calls to allocation, deallocation and memset were replaced by local memory operations. No Windows imports, game startup, rendering or networking were invoked.

The Python transcription in the appendix was compared with those instructions for seeds `0, 1, 2, 42, 12345, 32768, 54321, 65535` across:

- The six distinct `(width, height, room request)` combinations used by the two catacombs.
- A rectangular 17 × 23 map requesting three rooms with size override 5.
- A rectangular 15 × 19 map with no rooms.

**64/64 byte grids and placed-room counts matched.** All 64 outputs also had connected traversable cells. Separately, 24 native configurations were repeated in fresh emulators and produced identical results.

These comparisons verify the transcription against this executable, not historical seed choices or the missing server's population behavior. The appendix covers topology, not the complete renderer, collision integration, spawns or instance lifecycle.

## 4. Room meshes and assembly

All ten floor ZSCs have **241 object slots**: reserved slot 0 plus **3 banks × 5 shape classes × 16 variant slots**. This organization is explicit in `0x579B9B–0x579C0E`.

```text
object_slot = 1 + ((bank * 5 + shape_class) * 16) + variant_slot
bank 0 = floors
bank 1 = walls
bank 2 = ceilings
```

This is **not** a table of 15 independent four-direction connection masks. The renderer classifies a neighborhood and chooses a shape class, orientation and nonempty variant. Neighbor masks and matching patterns are embedded around `0x720E20–0x720FAB`; the classification passes run at `0x57ABF1–0x57ADA9`.

Nonempty catacomb ZSC objects are:

| Bank | Nonempty object IDs | Contents |
|---|---|---|
| Floor | 1, 17, 33, 49, 65–68 | Floor A–D, four floor-E variants |
| Wall | 81, 97, 113, 129 | Wall A–D; wall-E bank is empty |
| Ceiling | 161, 177, 193, 209, 225 | Ceiling mesh in each class |

Reminiscence has one mesh part per nonempty object. Sorrow's wall objects contain respectively 5, 3, 2 and 5 parts, including its additional scenery. Reminiscence uses paths under `3Ddata/KARKIA/KCatacomb/`; Sorrow uses `3Ddata/KARKIA/KCatacomb2/`.

The corresponding `KCATACOMB_PARTS_LV01.STB` and `...LV02.STB` have 241 rows and B1–B5 columns, with `.txt` authoring references matching these slots. The traced runtime path loads the floor ZSC directly. Do not make those authoring `.txt` files a prerequisite for runtime assembly without further evidence of a loader using them.

All direct mesh/material/effect/motion references from the ten catacomb ZSCs resolved in the supplied loose data. No missing direct ZSC dependency was found. This does not substitute for an in-game collision or rendering test.

**Collision follow-up:** the [third-pass report](jrose-catacombs-collision-investigation.md) now specifies the actual per-part collision flags and parent relationships. Most floor planes are flagged `0x0C`, Sorrow wall 113 keeps collision on a child with a non-colliding root, and ceilings have collision disabled. Jrose explicitly returns ground height zero for the dungeon. These details must accompany the mesh descriptors in a port.

### Second pass: exact shape and variant selection

The renderer's three passes at **`0x57ABF1–0x57AF68`** were transcribed and compared against those original instructions in an isolated x86 emulator. Appendix C contains a standalone implementation and the original pattern constants.

1. Convert topology to cell classes: ordinary passage = 0, room = 1, solid = `0xC0`. Each cell accumulates a **5 × 5 solid-neighbor mask**, with out-of-bounds positions contributing zero. Bits descend from bit 31 at offset `(-2,-2)` to bit 7 at `(+2,+2)`; bit 19 is the center.
2. Select the first matching `(shape, orientation)` using `(neighborhood & pattern_mask) == pattern_value`. The priority is **0, 3, 2, 1, 4** for open cells, and **0, 3, 2, 1** for solid cells. Within a shape, orientations are tested in order 0–3. Open and solid cells have separate pattern tables at `0x720EA0` and `0x720E20`; the priority bytes are at `0x720F40`. Shape/orientation default to zero if no pattern matches.
3. Visit cells in **row-major order** to choose models. Restart a separate 32-bit random state from the floor seed. Before every model choice, advance `s = ((4*s + 1)*(s + 1)) & 0xFFFFFFFF`, then choose `s % variant_count` from the compact list of nonempty ZSC objects for that bank and shape. Advance even when the count is one. A solid cell chooses a wall; an open cell chooses a floor, then a ceiling.

The shared instance flags at `instance + 0x40` can suppress ceilings with bit `0x04` and walls with bit `0x08`. A suppressed choice consumes no random step, so these flags can also change later model variants. These are recovered shared-renderer switches; their existence does not establish that the live catacombs enabled them.

Cell instantiation at `0x57A47D–0x57A4D3` uses a uniform **15.0 model scale** and orientation angles **0°, 90°, 180°, 270°**. The scale is a dimensionless model transform, separate from the 1500-world-unit cell spacing. Constants reside at `0x71577C`, `0x7079F0`, `0x709D44`, and `0x70B1F4`. Rotation helper `0x57B1E0` converts degrees to radians using `0x7074F0` and builds the rotation from its third angular component.

**Verification:** the 64 topology fixtures from section 3, each with flags 0, 4, 8 and 12, produced **256 byte-identical 20-byte-per-cell buffers and identical final random states**. Comparisons include neighborhood masks, cell classes, shape/orientation bytes and selected primary/ceiling object IDs. All ten catacomb ZSCs share the tested slot population; their actual mesh content differs. This validates descriptor selection, not GPU rendering, collision, or all possible seeds.

For floor seed 12345, 15 × 15, one requested room, automatic room sizing and flags 0, the normalized row-major descriptor buffer hashes to SHA-256 **`9af04a35183d43b31e4136b6455b6c59b85fb989fa2f48d322a4d3b966887483`**; final model-choice state is **554256261**. Normalization leaves object-pointer fields and unused bytes zero, as in Appendix C.

## 5. Entrance, exit and progressive minimap

### Procedural gate positions

`0x57AA4F–0x57ABD9` chooses the two warp positions after generation:

- Incoming position: scan along `x = 1` from low Y, selecting an ordinary passage cell.
- Outgoing position: scan along `x = width - 2` from high Y, selecting an ordinary passage cell.
- Convert cell coordinates with the floor origin and 1500-unit spacing.
- Use `3Ddata/Effect/_warp_dunjun_01.eft` for the gate effect.

The routine tests ordinary passage classification 0, rather than placing a gate at a random room center. It also conditionally creates the incoming gate's effect according to floor index and instance mode. The existence of incoming-position data does not establish that players could backtrack in a catacomb run.

### Exploration is separate from the complete topology

`0x576CC0` prepares the map image from the complete floor cell array. `0x577070` also allocates a separate exploration buffer. A map grid of W × H uses an exploration mask at **2W × 2H** resolution.

The world-to-cell helper at `0x576860` uses the floor origin and half-cell rounding. `0x576B90` notices the local player's cell changing and calls `0x576A00(x, y, 1)`. The network exploration path calls the same function with brush 0.

At `0x576A00`, a 4 × 4 brush is applied using the maximum of the existing and incoming alpha value. The brush origin is `(2*x - 1, 2*(height-y-1) - 1)` in the flipped-Y mask. Two brushes are embedded at `0x720790`:

```text
Remote/shared brush       Local brush
 36  46  46  36          100 128 128 100
 46  90  90  46          128 255 255 128
 46  90  90  46          128 255 255 128
 36  46  46  36          100 128 128 100
```

Exploration therefore accumulates and distinguishes locally visited from remotely reported cells. It does not generate geometry as the player walks.

Extension **0x2B** reads `(floor, x, y)` as three little-endian 16-bit values and invokes this shared reveal path (`0x57B7BF → 0x579220 → 0x576A00`). This directly supports party-shared exploration, although the server's exact broadcast policy remains unavailable.

There is also a full-reveal operation: dungeon extension **0xE0**, subcommand **11**, calls `0x5791D0 → 0x5771E0`, raising every mask value to at least 90. It preserves brighter locally explored cells. Its existence does not establish which gameplay action triggered it.

### Second pass: separate highlighted-cell overlay

Extension **`0x2C`** is now decoded. Its payload begins with a **u16 count**, followed at `+2` by that many four-byte entries, each **u16 X, u16 Y**, little-endian. There is no floor ID in this payload: `0x57B856 → 0x579250 → 0x579FB0 → 0x577D00` applies it to the current floor.

For a nonzero count, `0x577D00` replaces the old marker buffer/texture with a zeroed **W × H** bitmap. Each in-bounds coordinate sets `bitmap[(H - 1 - y)*W + x] = 1`. Coordinates with the high/sign bit set or outside the floor dimensions are ignored; duplicate coordinates mark the same cell. Texture builder `0x576EF0` gives marked cells ARGB **`0xFFD6D640`**, a yellow-green highlight, and leaves others transparent. The separate overlay is drawn at `0x577630–0x5776D8`.

This marker set is **replaced**, whereas exploration accumulates. One edge case matters: the outer packet handler ignores a **zero count**, preserving the previous markers; zero is not a clear-all message through this path. The payload has no monster ID, category, label or icon selector. It establishes the ability to highlight cells, but does not identify whether the server used them for gatekeepers, objectives or another purpose.

## 6. Network interfaces and progression

The shared extension transport is the same one documented in the [Tower investigation](jrose-tower-of-sorrow-investigation.md). Sender `0x522500` constructs an in-memory packet with base command `0x829`, a 16-bit extension at byte 6, payload at byte 8, and trailing `0xBE`. Total length is payload length + 9. Existing packet encryption/framing is outside this layout.

### Maze family

`0x51E0E2` routes the maze family to `0x57B760` via call `0x51E12A`.

| Extension | Observed behavior |
|---|---|
| `0x24` | Displays server-supplied text |
| `0x25` | Gate movement request/reply; reply checks payload byte `+0x10` |
| `0x26` | Common dungeon entry UI, also processed by `0x5789F0`; not fully decoded |
| `0x27` | Countdown initialization on a successful response |
| `0x28` | Clears that pre-departure countdown on success |
| `0x29` | Dungeon identity/mode/seed/remaining-time initialization |
| `0x2B` | Reveal one floor cell from the network |
| `0x2C` | Replace current-floor highlighted cells: u16 count followed by `(u16 x, u16 y)` entries; zero count is ignored |

Observed **0x29** payload fields, relative to its payload start:

| Offset | Read type | Meaning |
|---|---|---|
| `+0` | u32 | Dungeon/instance identity passed to movement logic |
| `+4` | u8 | Dungeon mode; influences generation/render flags |
| `+5` | — | Not read by this handler |
| `+6` | u16 | Run seed used to derive floor seeds |
| `+8` | u16 | Remaining run time, seconds |

`0x57B8D0` pairs the received duration with a local tick count, and the timer UI displays remaining time. **The client accepts the duration from the server. A hardcoded 2700-second catacomb rule was not recovered here.**

The `0x25` request at `0x578E70` sends 17 bytes: the instance identity at `+0`, X/Y floats at `+4/+8`, and a movement argument at `+12`; the last byte's request semantics were not established. Do not invent values for unspecified bytes from a guessed struct.

### Catacomb entry/key family

Extension **0xE0** routes through `0x51D897` to `0x536690`, using character state at `character + 0x5204`. The entry window and the shared maze renderer are separate pieces of the same path.

| Subcommand | Observed behavior |
|---|---|
| 1 | Client entry query from `0x5365E0`; five-byte payload including selector at `+2` |
| 2 | Entry-window records received; copied in 44-byte strides from payload `+0x21` |
| 3 | Cancellation path from the entry window |
| 6 | Client entry acceptance from `0x536630`; five-byte payload |
| 7 | Success updates character dungeon identity and required-key count; begins transition |
| 9 | Updates obtained/required key counters from payload `+2/+3` |
| 10 | Time-up notification; this particular popup branch explicitly checks zone 76 |
| 11 | Full minimap reveal, minimum alpha 90 |
| 12 | Clears character dungeon state; can report exhaustion/death |
| 13 | Switches floor using a u16 at payload `+4` |

The byte counters reside at character offsets **`+0x5208` obtained** and **`+0x5209` required**. The HUD string `鍵 %d/%d` survives at `0x72120C`.

At `0x578E70`, an active dungeon with obtained < required displays an instruction to defeat the gatekeeper and obtain a key. Once the count suffices, the party path displays a message that it is waiting for the other members and sends the movement request. The corresponding gate check at `0x579090` also uses these counters.

This gives direct evidence for **gatekeeper → key state → party waiting → server-authorized movement**. It does not prove the server's exact gathering radius, how it handles a dead/disconnected member, or which NPC is designated gatekeeper. The observed key state is a dedicated dungeon counter; the boss quest items below are separate.

The client gate-contact helper at `0x579F50` compares squared XY distance against **90000**, accepting a radius of **300 world units / 3 metres**. This detects contact by the checked position; it does not establish the server's whole-party gathering radius.

### Second pass: entry eligibility and payment records

The successful **`0xE0`, subcommand 2** response is copied by `0x536325` into the entry UI. Offsets below are relative to its extension payload, not the outer packet:

| Offset | Size/type | Meaning |
|---|---|---|
| `+0` | u8 | Subcommand 2 |
| `+1` | u8 | Result/error; zero selects the successful record path |
| `+2` | u16 | Entry selector, including 1/2 for these catacombs |
| `+4` | 1 byte | Meaning not established |
| `+5` | 14 bytes | First payment item descriptor, A |
| `+19` | 14 bytes | Second payment item descriptor, B |
| `+33` | 44-byte records | Participants, terminated by a record whose first u32 is zero |

The item descriptors are copied as 28 bytes and passed through the existing item-name and quantity helpers (`0x4F4950`, `0x4F34B0`). They are not hardcoded Courage Stone/Mallet constants in this handler. Their internal packed item format is outside this decoding.

Each participant record has this layout:

| Relative offset | Size/type | Observed use |
|---|---|---|
| `+0` | u32 | Identity checked against the resolved character's field `+0x4D8`; zero terminates the list |
| `+4` | u8 | May use participant's item A |
| `+5` | u8 | May use participant's item B |
| `+6` | u8 | Leader may cover item A |
| `+7` | u8 | Leader may cover item B |
| `+8` | u16 | Server object index, resolved through the object manager |
| `+10` | 32 bytes | Character name, consumed by the name-drawing path |
| `+42` | u8 | Daily eligibility flag |
| `+43` | u8 | Rejection/status code |

At **`0x536F60–0x53722B`**, the window first validates the locally resolved character and identity. An unresolved character is shown as too far away. Status 4 displays “cannot enter in the current state”; status 8 displays “too far away”; other nonzero statuses display a general entry rejection.

For a valid row, the first applicable display/eligibility branch wins:

```text
daily eligible
else participant uses A
else participant uses B
else leader covers A
else leader covers B
else entry item requirement is unmet
```

Direct Japanese strings include `デイリー有効` at `0x71B190`, `%sx%d を使用します` at `0x71B17C`, and `%sx%d をリーダーが負担します` at `0x71B15C`. Catacomb selectors 1/2 use the two-alternative missing-item message `%sx%d または %sx%d が必要です` at `0x71B13C`. Sponsored rows are colored yellow. The UI marks the group ready only when every participant row is eligible.

This is **binary evidence for daily eligibility, alternative entry items, and leader sponsorship**, including the client's displayed preference order when multiple server flags are set. It is not evidence that the server independently uses this order when debiting inventory. The server supplies the descriptors and all four payment flags; the exact quantities, 05:00 reset, once-per-catacomb bookkeeping, sponsor inventory reservation and atomic charging remain unrecovered.

## 7. Monsters, chests and quest hooks

### Actual boss identities

| Dungeon | LIST_NPC ID | Japanese name | Level field | AI row/file | NPC column 41 trigger |
|---|---:|---|---:|---|---|
| Reminiscence | 2771 | シャグラン・アレニェ | 250 | 931 / `KCC_ARAIGNEE.AIP` | `levelcap-liberation-altertumfluch` |
| Sorrow | 2274 | 古代樹 カーシアーナ | 250 | 979 / `KCC2_KHASIANA.AIP` | `catacombe2-quest` |

The historical wiki places both in their respective B5 large rooms. That floor assignment is historical evidence; the client boss rows themselves do not encode a B5 spawn schedule. See the [Reminiscence boss entry](https://wikiwiki.jp/roseonline/Area/Khakia/%E8%BF%BD%E6%83%B3%E3%81%AE%E3%82%AB%E3%82%BF%E3%82%B3%E3%83%B3%E3%83%99) and [Sorrow boss entry](https://wikiwiki.jp/roseonline/Area/Khakia/%E6%82%B2%E6%84%B4%E3%81%AE%E3%82%AB%E3%82%BF%E3%82%B3%E3%83%B3%E3%83%99).

Do not substitute Tower copies **3967/3966**, which reuse these AIs but omit the catacomb completion trigger. NPC 4010 is another unrelated low-level reuse of the Sorrow boss AI.

Quest records are recoverable and parse exactly to EOF:

- `QN-2771.QSD`, trigger at `0x1E`: selects quest **521**, checks the quest-item condition, and awards item **13473** = quest-item row **473**, **黄金のカケラ** (golden fragment).
- `QN-2274.QSD`, trigger at `0x1E`: selects quest **522**, checks its quest-item condition, and awards item **13474** = quest-item row **474**, **古代樹の枝** (ancient tree branch).
- `QN-KAK001.QSD` contains the Sorrow quest's acceptance/check/reward branches, including small crystal chest item `10/3616` and rainbow fragment `12/440` reward alternatives. These are quest progression/reward branches, not maze generation or daily-entry reset logic.

### AI-backed roster evidence

`LIST_NPC.STB` joined through `FILE_AI.STB` identifies the following catacomb AI families. This is a candidate population catalogue, **not a floor-by-floor placement table**:

| Family | NPC IDs | Examples |
|---|---|---|
| Reminiscence `KCC_*` | 2739–2750; 2771; 2773–2779 | ラッヘシュヴァーアト, ラッヘボーゲン, ムリロ, イビルアイ, D=ヴィクティム, イビルフェアリー, 呪われた殺人料理長, D=クレイトス, 吸血鬼デュッセルドルフ |
| Sorrow `KCC2_*` | 2262, 2264, 2267–2275 | エレメントバトラー, デス・ネパンデス, ブルゲイド, ルジゲイド, D=グールエレン, D=グールカミラ, ルンベック, シンベリ, エヴァゴルーム |
| Shared mimic AI | 2742, 2276 | Both use `KCC_MIMIC01.AIP` |

All **31 `KCC*.AIP` files**, totaling **434 event records**, parsed to EOF. Their behavior scripts survive, but an AI file is not the authoritative source of initial per-floor monster counts or coordinates.

Chest behavior is particularly concrete:

| Chest NPC | AI | Death-event condition | Summoned mimic |
|---:|---|---|---:|
| 2741 | `KCC_MIMIC01_BOX.AIP` | 50% probability, condition at `0x193` | 2742 |
| 2275 | `KCC2_MIMIC01_BOX.AIP` | 50% probability, condition at `0x193` | 2276 |

Both death events are pattern 5/event 0. The summon action at `0x1A3` has raw opcode **0x25** (serialized action ID 37), with NPC payload `b6 0a` or `e4 08`. Their idle pattern also has a 20% check and a monster-variable update; do not reinterpret that separate idle condition as the mimic spawn chance.

`LIST_NPC` gives drop-table selectors 840 for the chests, 841/850 for the two mimics, and 842/849 for the bosses. `ITEM_DROP(NEW).STB` contains matching named rows and small/large box weights, but its active server-loader status was not established. Those weights are **not asserted as live drop probabilities** here.

### Misleading NPC tables

Five `KCATACOMB010x_NPC.STB` files are present, each with headers `plase`, `flg`, `group cnt`, and ten NPC columns. However, sampled populated IDs resolve to **Ramesses/Oro** content:

| ID | Localized identity |
|---:|---|
| 2111 | ラメセスの宝箱 — Ramesses chest |
| 2181 | オロスコーピオン — Oro scorpion |
| 2201 | 泥人形 — mud doll |
| 2221 | タランチュラ — tarantula |
| 2231 | オロバット — Oro bat |
| 2510 | バルバロ |

There are no corresponding `KCATACOMB020x_NPC.STB` files, and both live floor tables have blank `npc group` cells. The traced client floor loader does not read that column.

These files are therefore **unvalidated population templates, plausibly copied from Ramesses**, not reliable proof that those Oro monsters inhabited the live catacombs. Do not build a supposedly faithful spawn schedule by trusting their filenames.

## 8. Checking the described gameplay rules

| Rule | Current evidence |
|---|---|
| Two separate cemetery dungeons | Binary/data: zones 76/77, selectors 1/2, separate tables and meshes |
| Five underground floors | Binary/data: five live rows in each table |
| RNG maze | Emulator-verified generator and binary seed flow |
| Minimap records explored route, shared with party | Binary: local and network reveal paths, separate alpha brushes |
| Gatekeeper gives a key | Binary: key counters and explicit gatekeeper instruction; exact NPC selection unresolved |
| Whole party must gather on gate | Historical rule; binary waiting/request path supports it, server enforcement unavailable |
| Maximum 45 minutes | Historical rule; binary duration is supplied by server |
| Monsters do not respawn | Historical rule; server regen policy unresolved; chest summons are a separate mechanism |
| Cannot return to previous floor | Historical rule; client has general floor switching, server permission rule unresolved |
| Once free per day per catacomb; reset after 05:00 | Binary daily-eligibility flag and UI; exact reset time and per-catacomb accounting remain historical |
| Extra entry: Courage Stone ×1 or Lucky Mallets ×3 per character | Binary two-item payment/sponsorship interface; exact item quantities remain historical and charging is server-side |
| Leader can cover members' entry items | Binary participant flags and explicit sponsorship display; debit/reservation rules unresolved |

The later [Reminiscence wiki](https://wikiwiki.jp/roseonline/Area/Khakia/%E8%BF%BD%E6%83%B3%E3%81%AE%E3%82%AB%E3%82%BF%E3%82%B3%E3%83%B3%E3%83%99), last modified 2022-04-10, and [Sorrow wiki](https://wikiwiki.jp/roseonline/Area/Khakia/%E6%82%B2%E6%84%B4%E3%81%AE%E3%82%AB%E3%82%BF%E3%82%B3%E3%83%B3%E3%83%99), last modified 2018-11-05, support the historical rules above. They also say the leader can cover members' entry items, solo entry is possible, and members must be nearby, on the same map and alive. They describe restricted party departure/kicking and trading, plus return to a designated location on timeout or logout. These dates precede the supplied EXE; channel lists and service policy should not be treated as build constants.

Local item identities:

- **勇気の石:** `LIST_NATURAL` row **701**, type **12**, legacy encoded ID **12701**.
- **開運小槌:** row **616**, type **12**, legacy encoded ID **12616**. Gift mallet variants are distinct items.
- Teleport scrolls: `LIST_USEITEM` rows **304/305**, type **10**. Their presence does not establish a bypass of daily eligibility.

The 05:00 reset boundary, exact per-character prices, and once-per-dungeon tracking still require historical documentation as the specification. The client now independently confirms the daily/payment/sponsorship interface, but not its server bookkeeping. No daily reset algorithm was recovered from the boss QSDs.

## 9. Implications for a future Rose Next implementation

Topology and mesh descriptors can be reconstructed from the surviving client algorithms and seed, with emulator comparisons supporting both transcriptions. The associated visual pieces are present. An equivalent implementation would need:

1. The generator, floor-table loader and deterministic per-floor seed derivation.
2. The recovered cell classification, shape/orientation matching and ZSC variant selection, followed by world placement and collision integration.
3. An instance service that owns party membership, eligibility, payment, timer, key state and floor transitions.
4. A separately established monster population policy, with live catacomb NPCs and the recovered boss/chest behaviors.
5. Shared exploration notifications, local/remote minimap masks, and the separate highlighted-cell overlay.

The original floor renderer keeps multiple floor definitions and locates the active floor from world coordinates. A new implementation could organize instances differently, but that would be a deliberate adaptation, not a recovered fact about the Jrose server.

The second pass closed the previously identified entry-window, marker-packet and neighborhood-to-mesh questions. The largest original-behavior gap is **server-owned population and progression policy**, especially gatekeeper choice and per-floor monster placement. The [third pass](jrose-catacombs-collision-investigation.md) recovered the collision inputs and checked assembled triangle geometry, while identifying specific Rose Next work for height, picking, collision residency and server navigation. Live engine integration remains to be validated. Original server data or packet captures would be more useful than another broad client pass for the server policies. Footage remains a final corroboration step for presentation and encountered monsters; it cannot establish every random outcome or payment edge case.

## 10. Address map for continuing the investigation

| Address | Role |
|---|---|
| `0x42FEDE`, `0x430286` | Native cemetery gate records and insertion loop |
| `0x421BD0`, `0x421290` | `SC_DgsOpen` wrapper and entry bridge |
| `0x5368B0` | Entry object, leader and proximity checks |
| `0x5365E0`, `0x536630` | Entry query and acceptance requests |
| `0x536690` | Dungeon/key state receive handler |
| `0x536325`, `0x536F60–0x53722B` | Entry records and daily/payment/sponsorship UI |
| `0x71B0E0` | Entry selector-to-zone table |
| `0x576510` | Zone-linked floor-table loader |
| `0x579480` | Floor allocation, parameters and seed chain |
| `0x57A760` | `DgFloor::create` |
| `0x57BDF0`, `0x57BE30` | Generator initialization and room-size override |
| `0x57C5A0` | Generator entry, seed normalization and allocation |
| `0x57C3D0` | Boundary, rooms and two wall-construction passes |
| `0x57BE70` | Room placement and openings |
| `0x57C200`, `0x57BD90` | Wall placement and grid-state test |
| `0x579AF0` | ZSC banks and valid variants |
| `0x57ABF1–0x57AF68` | Neighborhood masks, classes and mesh selection |
| `0x57A47D–0x57A4D3`, `0x57B1E0` | Model scale and quarter-turn rotation |
| `0x576860` | World-to-cell conversion |
| `0x576A00`, `0x576B90` | Reveal brush and local movement reveal |
| `0x576CC0`, `0x577070` | Map raster and exploration allocation |
| `0x5771E0` | Minimum-alpha full reveal |
| `0x577D00`, `0x576EF0` | Replace highlighted-cell mask and build its texture |
| `0x57B760`, `0x57B812` | Maze packet family and seed/time initialization |
| `0x578E70` | Key check, party waiting and gate movement request |
| `0x579F50` | 300-unit gate-contact radius |
| `0x57B8D0`, `0x57BCD0` | Remaining-time initialization and HUD |

## Appendix A: reproducible topology transcription

This standalone research code implements the recovered topology for valid floor inputs. It has no game dependency and no filesystem/network side effects. It intentionally excludes renderer classification and population logic. `Maze(...).g` is the raw column-major byte grid; `.n` is the number of rooms actually placed. The seed argument is a **floor seed**, after the run-to-floor derivation described above.

```python
class Maze:

    def __init__(self, seed, w, h, n, roomsize=0):
        self.s = seed & 65535
        self.w = max(5, w | 1)
        self.h = max(5, h | 1)
        self.g = bytearray(self.w * self.h)
        self.dirs = [0, 1, 2, 3]
        self.n = 0
        for _ in range(self.rand(3) + 1):
            self.swap()
        w, h = (self.w, self.h)
        for x in range(w):
            self.put(x, 0, 192)
            self.put(x, h - 1, 192)
        for y in range(h):
            self.put(0, y, 192)
            self.put(w - 1, y, 192)
        size = min(w, h) // (2 if n == 1 else n) | 1 if n else 0
        if roomsize:
            roomsize = min(15, max(3, roomsize | 1))
            if size < roomsize:
                n = 0
            size = roomsize
        elif size < 7:
            n = 0
        for _ in range(n):
            for attempt in range(100):
                x = self.rand(w - size) & 65534
                y = self.rand(h - size) & 65534
                if self.get(x, y) | self.get(x + size - 1, y) | self.get(x + size - 1, y + size - 1) | self.get(x, y + size - 1):
                    continue
                for xx in range(x, x + size):
                    for yy in range(y, y + size):
                        self.put(xx, yy, 64 | self.n)
                for xx in range(x, x + size):
                    self.put(xx, y, 255)
                    self.put(xx, y + size - 1, 192)
                for yy in range(y, y + size):
                    self.put(x, yy, 255)
                    self.put(x + size - 1, yy, 192)
                k = size // 2 - 1 | 1
                if self.rand(10) < 5:
                    self.put(x + k, y, 64 | self.n)
                    self.put(x + k, y + size - 1, 64 | self.n)
                else:
                    self.put(x, y + k, 64 | self.n)
                    self.put(x + size - 1, y + k, 64 | self.n)
                self.n += 1
                break
        for y in range(0, h // 2 + 1, 2):
            for _ in range(w // 2 + 1):
                self.wall(self.rand(w // 2 + 1) * 2, y, 0)
            for _ in range(w // 2 + 1):
                self.wall(self.rand(w // 2 + 1) * 2, h - 1 - y, 0)
        for x in range(0, w // 2 + 1, 2):
            for y in range(0, h, 2):
                self.wall(x, y, 1)
                self.wall(w - 1 - x, y, 1)

    def rand(self, n):
        self.s = (4 * self.s + 1) * (self.s + 1) & 4294967295
        return self.s % n if n else 0

    def swap(self):
        a = self.rand(4)
        b = self.rand(4)
        self.dirs[a], self.dirs[b] = (self.dirs[b], self.dirs[a])

    def get(self, x, y):
        return self.g[x * self.h + y] if 0 <= x < self.w and 0 <= y < self.h else 128

    def put(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[x * self.h + y] = v

    def wall(self, x, y, mode):
        if self.get(x, y):
            return
        self.swap()
        dx = [0, 0, -1, 1]
        dy = [-1, 1, 0, 0]
        ds = self.dirs if mode else self.dirs[:1]
        for d in ds:
            if self.get(x + dx[d] * 2, y + dy[d] * 2) & 192:
                self.put(x, y, 192)
                self.put(x + dx[d], y + dy[d], 192)
                return
import hashlib
m = Maze(12345, 15, 15, 1)
assert m.n == 1
assert hashlib.sha256(m.g).hexdigest() == '8a5ee93ae42c590720bde4a97ae5714e6b6281938986b51887aa86ff4f8c4a2a'
```

## Appendix B: reference hashes

| Relative path in reference client | SHA-256 |
|---|---|
| `TRose.exe` | `536bb1cdd0f637a77d33e99eb08027876328195cf57a7545c150cf6d80b50041` |
| `SCRIPTS/EVENTOBJECT_01.LUA` | `17b47a915c32064b98725e8c412b03dd8780b3284e41e29050a1458cd305da41` |
| `3Ddata/STB/LIST_ZONE.STB` | `ab9d3c459a506efb809cfb653ff84c5db19d7bc44250f57bcd1d8c67676322e9` |
| `3Ddata/STB/LIST_NPC.STB` | `19fe9d8291eada6f06121f3479de006131f8b2de7d8ce672e58e54113aa3c018` |
| `3Ddata/MAPS/KARKIA/KCATACOMB/KCATACOMB_LV01.STB` | `ba0013ce5e73ae8473969f496085799861175b68129a6861b7429d0f824a942c` |
| `3Ddata/MAPS/KARKIA/KCATACOMB/KCATACOMB_LV02.STB` | `e83a03f4bc9be369072125381c9665234ed9f6c3227151a423847c1e24aae6fa` |
| `3Ddata/MAPS/KARKIA/KCATACOMB/KCATACOMB0101.ZSC` | `904f5b7ddd771471a914de43d196a9f6f5b546681e554ff193dd9e20df7eb98c` |
| `3Ddata/MAPS/KARKIA/KCATACOMB/KCATACOMB0201.ZSC` | `082f10bbeae5b5541f0909cf3b5026a7171375a8e251346939e84572e239d8a2` |
| `3Ddata/QUESTDATA/QN-2771.QSD` | `d0c3898f70e6c8faaf8a19d4f0c2875a56d6d8ac455734811f6cb2bbd1248702` |
| `3Ddata/QUESTDATA/QN-2274.QSD` | `c5c8f5f74affc35004e0251abc151c501b2fe512484756482f618c407ff306e7` |

## Appendix C: reproducible mesh-descriptor transcription

This research code consumes Appendix A's raw grid and the same **floor seed**. It reproduces the classification and model-selection instructions at `0x57ABF1–0x57AF68` for the supplied catacomb banks. It performs no filesystem, network or engine calls. The pattern pairs below are `(mask, value)`, grouped by shape 0–4 (solid shapes 0–3), then orientation 0–3.

```python
import struct

CATACOMB_BANKS = (
    ((1,), (17,), (33,), (49,), (65, 66, 67, 68)),
    ((81,), (97,), (113,), (129,), ()),
    ((161,), (177,), (193,), (209,), (225,)),
)
SHAPE_PRIORITY = (0, 3, 2, 1, 4)

SOLID_PATTERNS = (
    ((0x011CE000, 0x01080000), (0x031CC000, 0x000C0000), (0x039C4000, 0x00084000), (0x019C6000, 0x00180000)),
    ((0x011C4000, 0x01084000), (0x011C4000, 0x001C0000), (0x011C4000, 0x01084000), (0x011C4000, 0x001C0000)),
    ((0x011CE000, 0x011C0000), (0x031CC000, 0x010C4000), (0x039C4000, 0x001C4000), (0x019C6000, 0x01184000)),
    ((0x011C6000, 0x01180000), (0x011CC000, 0x010C0000), (0x031C4000, 0x000C4000), (0x019C4000, 0x00184000)),
)

OPEN_PATTERNS = (
    ((0x001C4000, 0x00144000), (0x01184000, 0x01104000), (0x011C0000, 0x01140000), (0x010C4000, 0x01044000)),
    ((0x001C0000, 0x00140000), (0x01084000, 0x01004000), (0x001C0000, 0x00140000), (0x01084000, 0x01004000)),
    ((0x011C4000, 0x00004000), (0x011C4000, 0x00100000), (0x011C4000, 0x01000000), (0x011C4000, 0x00040000)),
    ((0x011C4000, 0x00044000), (0x011C4000, 0x00104000), (0x011C4000, 0x01100000), (0x011C4000, 0x01040000)),
    ((0x011C4000, 0x00000000), (0x011C4000, 0x00000000), (0x011C4000, 0x00000000), (0x011C4000, 0x00000000)),
)

def catacomb_descriptors(raw_grid, width, height, floor_seed, flags=0):
    """Return normalized row-major cell bytes and final model-choice state.

    Input is the column-major raw grid from Maze(...).g in Appendix A.
    Output has 20 bytes per cell: +8 u16 primary object, +10 u16 ceiling,
    +12 u8 cell kind, +13 u8 shape, +14 u8 orientation, +16 u32 mask.
    Unused bytes and runtime object pointers stay zero; all integers are LE.
    The bank lists describe the nonempty slots in all ten supplied ZSCs.
    """
    if len(raw_grid) != width * height or not (0 < width < 32768 and 0 < height < 32768):
        raise ValueError("Invalid grid dimensions")
    data = bytearray(width * height * 20)
    for y in range(height):
        for x in range(width):
            kind = raw_grid[x * height + y] & 0xC0
            data[(y * width + x) * 20 + 12] = 1 if kind == 0x40 else kind

    for y in range(height):
        for x in range(width):
            mask = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if data[(ny * width + nx) * 20 + 12] == 0xC0:
                            mask |= 1 << (31 - ((dy + 2) * 5 + dx + 2))
            offset = (y * width + x) * 20
            struct.pack_into("<I", data, offset + 16, mask)
            solid = bool(mask & 0x80000)
            patterns = SOLID_PATTERNS if solid else OPEN_PATTERNS
            found = False
            for shape in SHAPE_PRIORITY[:4 if solid else 5]:
                for orientation, (required_mask, required_value) in enumerate(patterns[shape]):
                    if mask & required_mask == required_value:
                        data[offset + 13] = shape
                        data[offset + 14] = orientation
                        found = True
                        break
                if found:
                    break

    state = floor_seed & 0xFFFFFFFF

    def choose(bank, shape):
        nonlocal state
        state = ((4 * state + 1) * (state + 1)) & 0xFFFFFFFF
        variants = CATACOMB_BANKS[bank][shape]
        # Valid catacomb fixtures never request an empty bank/shape.
        return variants[state % len(variants)]

    for offset in range(0, len(data), 20):
        kind, shape = data[offset + 12:offset + 14]
        if kind == 0xC0:
            if not flags & 8:
                struct.pack_into("<H", data, offset + 8, choose(1, shape))
        elif kind in (0, 1):
            struct.pack_into("<H", data, offset + 8, choose(0, shape))
            if not flags & 4:
                struct.pack_into("<H", data, offset + 10, choose(2, shape))
    return bytes(data), state
```

Example, after loading both appendices:

```python
import hashlib

maze = Maze(12345, 15, 15, 1)
cells, final_state = catacomb_descriptors(maze.g, 15, 15, 12345)
assert hashlib.sha256(cells).hexdigest() == (
    "9af04a35183d43b31e4136b6455b6c59b85fb989fa2f48d322a4d3b966887483"
)
assert final_state == 554256261
```

The second-pass comparison reused the 64 topology fixtures from section 3 with each of flags `0`, `4`, `8`, `12`. The emulator executed only the original selection instruction range with synthetic floor/cell memory and the original read-only pattern constants. It did not start TRose.exe, load its DLLs, create a game window or execute a server. Final cell bytes and PRNG states matched in all 256 cases. Mesh instantiation, scale/rotation helper calls and packet/UI behavior were established by static tracing; they are not covered by that emulator comparison.
