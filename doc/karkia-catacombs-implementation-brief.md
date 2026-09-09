# Karkia catacombs: implementation brief

**Status, 2026-09-09: research complete, nothing built.** This document is the
handoff into an implementation session. It does not repeat the reverse
engineering — the three reports below are in the workspace and remain the
authority for every recovered detail.

| Report | Settles |
|---|---|
| [jrose-catacombs-investigation.md](jrose-catacombs-investigation.md) | Maze generator, mesh/descriptor selection, floor tables, warp gates, minimap, protocol, entry UI, bosses/chests. Appendices A and C are runnable transcriptions with conformance hashes. |
| [jrose-catacombs-collision-investigation.md](jrose-catacombs-collision-investigation.md) | Per-part collision flags, hierarchy, unit/transform recipe, the flat-ground override, picking and residency integration points. Appendix has a snapshot recipe with hashes. |
| [jrose-tower-of-sorrow-investigation.md](jrose-tower-of-sorrow-investigation.md) | The shared extension-packet transport, reused here. Also the reason the catacombs are the better first dungeon — see §6. |

**Is more reverse engineering needed? No.** Both catacomb reports independently
concluded another pass over the same client cannot recover what is missing, and
this session found nothing to add. What remains is either ours to author (§4) or
only answerable by building it (§5). The one optional external source is recorded
footage, useful for corroborating presentation, not for recovering rules.

---

## 1. The design decision that shapes everything

**One shared maze per dungeon, seeded from the calendar, rerolled daily.**

Jrose gives each party its own seeded instance. We are not doing that, for a
reason that is structural rather than a shortcut:

`CZoneLIST` allocates `m_ppThreadZONE` as a **flat array indexed by zone number**,
sized to the zone table's row count ([zonelist.cpp:19,96](../src/sho_gameserver/src/zonelist.cpp)).
One zone is one thread is one shared world. The `bool` on `CZoneTHREAD` is thread
suspension, not an instance flag. **The server has no instancing of any kind.**

Deriving the seed from the date rather than storing it removes three more things:

- No persistence, no reset job, no admin command to force a reroll.
- No packet to distribute the seed — server and client agree because the calendar
  agrees. (Jrose sends it in extension `0x29`; we would not need to.)
- It is **reproducible**: a maze reported broken on Tuesday can be regenerated on
  Thursday and inspected. A stored random seed loses that at rollover.

Accepted consequence: the day's layout is public once someone maps it. For a
family-and-friends alpha that is acceptable and arguably social; it resets daily.

**This same decision solves the navigation problem in §3.** The server rolls one
seed per dungeon per day, derives one occupancy grid from it, and hands it to the
zone the way a `.MOV` file would be. No per-party regeneration.

## 2. Entry design

An NPC at each crypt mouth takes a material toll and warps the party in.

This deliberately replaces Jrose's entry subsystem — daily eligibility, two
alternative payment items, leader sponsorship, per-catacomb once-a-day accounting,
an 05:00 reset. The collision report's companion recovered that **interface** in
full and was explicit that the **server bookkeeping behind it is unrecoverable**.
Routing around it removes the least reconstructable part of the feature.

**Toll should come from the Cemetery, not a shop.** A bought toll is a gold cost
with extra steps and puts the gate in a different zone from the door. Zone 87's
monsters already drop, from `add-karkia-drops.py`'s `MAT_CEMETERY`:

| id | item | price |
|---:|---|---:|
| 151 | Black Hearts | 305 |
| 152 | Green Hearts | 495 |
| 153 | Blue Hearts | 875 |

A crypt whose keeper asks for hearts, paid by the dead in the graveyard above it,
closes the loop in one zone and needs no new drop authoring. The Cemetery bosses
drop **Golden Hearts (156)** and **White Hearts (157)** — a natural gate for the
second catacomb, giving the two dungeons an order without inventing anything.

Existing machinery covers all of it: `quest-editor con-store`/`con-warp` for the
dialog option, the QEX1 appendix for the Lua, `add-karkia-travel.py` for the warp
leg. See [reference_con_dialog_format] in memory and `scripts/add-karkia-travel.py`.

## 3. What this session verified in *our* codebase

The collision report makes claims about Rose Next. Three were checked directly and
all three hold. These are the load-bearing ones.

**Sorrow wall 113 will work.** Its collision sits on a *child* of a zero-collision
root, which a root-only importer would drop. `zz_visible::gather_collidable`
([zz_visible.cpp:1678](../src/engine/src/zz_visible.cpp)) pushes a node only if its
own level is nonzero but **recurses into children unconditionally**, so the child
is collected. Note it also requires `inscene` — residency is real (§5).

**The monster-height helper skips our floors.** `getWorldObjectHeightInScene`
([zz_interface.cpp:8784](../src/engine/src/zz_interface.cpp)) contains
`if (ZZ_IS_NOTMOVEABLE(level)) continue; // skip if not moveable`. Catacomb floors
are `0x0C` = polygon collision **plus** NOTMOVEABLE, so every Sorrow floor and most
Reminiscence floors are invisible to it — and `AdjustHeight_Monster` reaches it via
`CTERRAIN::GetHeightTop`. Monsters would stand at the reused outdoor heightfield,
looking like a placement bug.

Jrose's answer is a hard flat plane: zones 76/77 branch to a function that is
literally `fldz; ret 8`, returning 0.0 for every X/Y. **We need our own dungeon
ground-height policy; this is not optional polish.** The avatar's collision
response also *clamps* height against the terrain value, so a leftover heightfield
can lift the player off a correctly placed floor.

**The server movement grid is 5 m.** `nATTR_GRID_SIZE 500`
([zonefile.h:117](../src/sho_gameserver/src/zonefile.h)), with `IsMovablePOS` on
the next line. Three grid cells per 15 m maze cell — but as the report warns, that
ratio does not establish index alignment, and `IsMovablePOS` is a *destination*
test that says nothing about walls in between.

## 4. What this session found about our data

**Zone numbers collide.** Jrose's 76 and 77 are our **Golden Ring** and **Golden
Ring** (Oro). Renumber, as we did for Karkia's own zones. `LIST_ZONE` has 145 rows,
83 blank, and **89–130 is a free run of 42** sitting between our Karkia blocks
(86–88 and 131–136, 144) — so 89/90 puts the catacombs beside the Cemetery in the
table as well as in the fiction. Both are below `TEST_ZONE_NO` (250), so they will
actually serve; see [reference_zone_number_ceiling] in memory.

**Monster ids are almost all free.** Of the 32 catacomb NPC ids, **31 are blank in
our `LIST_NPC`**. The single collision is **2264 = our Terrasaurus Predator**. The
two bosses (2771 Reminiscence, 2274 Sorrow) are both free.

**The asset import is tiny.** 46 files, **0.74 MB** total —
`3Ddata/KARKIA/KCatacomb` (13 ZMS + 10 DDS) and
`3Ddata/MAPS/KARKIA/KCATACOMB` (11 ZSC + 10 STB + 2 DDS) — plus 31 `KCC*.AIP` at
42 KB. Smaller than a single armour set.

**We have no catacomb assets today.** The only match under `data/` is an unrelated
Eldeon mesh.

**Newly imported textures will need mip chains** — every armour import this week
logged `src_mips=1` slow creates. Run `scripts/add-dds-mipmaps.py --subdir` after
importing; see its runs-on-record.

## 5. The work, in stages

Ordered so the risky parts are provable early and the cheap parts are testable
before the expensive ones exist.

1. **Entry loop, against a placeholder.** NPC at the crypt mouth, material toll,
   warp into *any* existing dungeon zone. Proves the part that is new to us — gate,
   cost, descent, return — while the maze does not exist yet. Uses only tooling we
   already have.
2. **Asset import.** 46 files, renumbered zones, 31 NPC rows plus one remap for
   2264. Then the mip pass.
3. **Generator port.** Transcribe Appendix A of the main report to C++ and check
   it against its published hash (`Maze(12345,15,15,1)` →
   `8a5ee93a…`). Then Appendix C for descriptors
   (`9af04a35…`, final PRNG state `554256261`). **Both have conformance vectors —
   you know when you are done.**
4. **Ground-height policy.** A dungeon plane at Z = 0 that `GetHeight`,
   `GetHeightTop` and the avatar's height clamp all respect, without changing
   ordinary-zone behaviour.
5. **Scene assembly and collision.** ZSC bank selection, root transform, insertion.
   Compare against the collision report's snapshot hashes
   (Reminiscence `8a7c00a3…` 225 parts / 57,402 triangles; Sorrow `54f33e16…`
   249 / 11,020).
6. **Server occupancy.** Derive the movement grid from the same daily seed. Mind
   the 3:1 ratio caveat and wall protrusions beyond the nominal tile.
7. **Population.** Author it (§6). Place the two bosses, the chests and their
   mimics.
8. **Progression.** Gatekeeper → key → gate, if kept (§7).

## 6. What must be authored, not recovered

Neither report found these in the client, and both concluded they are not there:

- **Per-floor monster population, counts and positions.** The
  `KCATACOMB010x_NPC.STB` files look authoritative and are **Ramesses/Oro copies**
  — a trap the report flags explicitly. Do not build a "faithful" schedule from them.
- **Gatekeeper selection** — which monster carries the key.
- **Daily reset, pricing and once-per-day accounting** — replaced by §2 anyway.
- **Server navigation representation.**

For a maze this is a much lower-stakes authoring job than the tower's 250 floors of
waves: scatter monsters through corridors and nobody can tell it is not original.
That asymmetry is why the catacombs are the better first dungeon.

## 7. Decisions the implementation session should make first

1. **Keep the gatekeeper/key descent?** Jrose gates each floor on killing a
   keyholder and gathering the party. It is cheap for us — a per-character counter,
   or simply "the gate opens when this floor's named monster dies" — and it is what
   stops the dungeon being a footrace to B5. Worth a deliberate yes/no rather than
   quietly dropping it.
2. **Both catacombs, or one?** Sorrow has richer wall geometry (28 parts to
   Reminiscence's 17) and the harder boss. Shipping Reminiscence alone halves the
   population authoring and proves the pipeline.
3. **Five floors, or fewer?** The floor tables are data; nothing forces five.
4. **What the toll actually costs**, and whether the second dungeon uses the boss
   Hearts.

## 8. Acceptance

The collision report's §6 lists six acceptance cases — ground, collision
hierarchy, movement, picking, residency, server agreement. Use them as written.

The three that no document can settle in advance, and where the time will go:

- **Residency.** Does collision survive the camera turning, a streaming boundary,
  and floor teardown? Note our ordinary patch removal also removes fixed objects
  from the scene, and `gather_collidable` requires `inscene`.
- **Picking.** Clicks must land on generated floors. `CTERRAIN::Pick_POSITION`
  iterates terrain patches, so an inserted floor is *not* automatically a movement
  destination — and terrain or sky hits will hide the gap.
- **Step/slide response** at speed, and for cart/castle-gear widths.

Everything verified so far is geometry and static tracing. Nobody has had this in
our engine.
