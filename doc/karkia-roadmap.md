# Karkia Import Roadmap

Companion to [doc/karkia-survey.md](karkia-survey.md), which is the evidence. This is the
plan. **Nothing here is built yet.**

Two scope decisions are settled going in:

- **No quests.** Karkia's are Japanese, and the RoseZA quest import was the painful half of
  `project_oro_import`.
- **Travel is NPC-driven, not gate-driven.** Karkia has no entrance and splits into two
  disconnected clusters plus an isolated Tower. Rather than author warp-gate objects into
  maps we have never opened, every missing link becomes a teleporter NPC. This is a solved
  problem here — see §2.

---

## 1. What "done" looks like

Nine zones a level-220-ish player can reach, fight through and leave, with monsters tuned
to our curve, loot worth taking, and no dependency on Jrose's quest chain or its
instanced-dungeon generator.

```
                          [entrance NPC, outside Karkia]
                                       |
                                       v
  86 Church  <--gate 170--  87 CEMETERY  --172-->  88 SpireVil  --185-->  135 TowerPlace
   (W)                       (W) ^  |   ^           (W) ^  |               (W)  |
                                 |  |   +---173--------+  |                     |
                                 |  |                     +--------186----------+
                              178|  ^179
                                 v  |
                          131 Burned Forest (W)

  134 MemoriesBoss --180--> 133 Memories <--190-- 144 FlowerGarden      136 Tower
        (W)                    (W)                     (W)                 (W)

  (W) = Wayfinder NPC.  Solid arrows are the 11 gates that already exist in the data.
```

Everything reachable in both directions; the eight existing gates keep doing their job and
the Wayfinder covers the six holes (into the planet, out of the planet, out of the Church,
into Memories, into the Boss room, and both ways for the Tower).

---

## 2. The travel design

The mechanism exists and is already tooled. `scripts/add-oro-travel.py` writes a QSD trigger
whose reward is `REWD_007` (teleport), and `quest-editor con-warp <root> <npc> <key>
<trigger> --write` appends a "take me there" option — with a confirm prompt and fully
customisable text — onto an NPC's existing dialog through the QEX1 appendix. Oro reaches
Muris and comes back exactly this way today.

**Proposal: one `[Wayfinder]` NPC row, placed once in each of the nine zones, with a warp
option per destination.** One `LIST_NPC` row, one `.CON`, one `LIST_EVENT` row, nine
placements, and one QSD trigger per destination.

Place each instance at that zone's own `start` event position. That is guaranteed walkable
(it is where the zone drops you), it is where a teleporting player arrives, and it needs no
map knowledge. All nine `start` positions were checked against the chunk grid and land on
chunks that exist:

| zone | `start` world position | chunk |
|---|---|---|
| 86 Church | 517000, 521500 | 32,32 |
| 87 Cemetery | 562026, 522137 | 35,32 |
| 88 Spire Village | 536500, 521000 | 33,32 |
| 131 Burned Forest | 521598, 521100 | 32,32 |
| 133 Memories | 515902, 521100 | 32,32 |
| 134 Memories Boss | 520000, 521000 | 32,32 |
| 135 Tower Place | 516300, 521000 | 32,32 |
| 136 Tower | 520000, 520000 | 32,32 |
| 144 Flower Garden | 535148, 521000 | 33,32 |

Read them out of the `.ZON` at build time rather than pasting them — the file stores
`x, z, y` and every coordinate needs a half-zone bias added before it is a world position.
`add-oro-travel.py`'s `zon_event_positions()` already does this correctly; reuse it.

The Wayfinder needs a model. Reuse an existing NPC model rather than importing one — this
is plumbing, not a character.

---

## 3. Stages

Same shape as `scripts/import-oro.py`: one script, `--stage N`, idempotent, `--dry-run`,
`--selftest` proving every writer round-trips byte-identically before anything is touched.
Each stage is independently testable in game and independently revertible.

`data/` is gitignored, so **the script's docstring is the only committed record** of what was
done and why.

### Stage 1 — terrain, art, zone rows

Copy the 9 `.ZON`/`.IFO` sets with the MOB, REGEN, WARP and EVENT_OBJECT lumps emptied on
the way in (count = 0, lump table untouched) so later stages just refill them. Plus the 18
map `.ZSC`s, `3Ddata\KARKIA\`, the 208 terrain tiles, the new map meshes and textures,
`LIST_SKY` row 17 + the two `LUNAR\Sky02` textures, `LIST_ZONE` rows 86–144 with fresh
`LZON*` STL keys, and English zone names via `scripts/add-zone-name.py`.

Two things this stage must get right:

- **Append a synthetic `LUMP_ECONOMY` to each `.ZON`.** Karkia's are the stripped late-Jrose
  variant with no lump 4, so `CEconomy::Load` never runs and the server's zone economy runs
  on uninitialised heap. Copy the five ints from a comparable zone of ours.
- **Never overwrite an existing `.dds`.** 331 of the shared textures differ only because ours
  have mip chains and Jrose's do not. Run `scripts/add-dds-mipmaps.py` over the 93 new ones
  instead.

Also renumber on the way in: `WARP.STB` 170 and 172 are live Oro gates, and STL key
`LZON086` belongs to our zone 82.

**Acceptance:** GM-warp into each of the nine and walk around. No missing-asset lines in
`error.txt`, no black terrain, minimap draws, zone name shows above it. Run
`scripts/audit-zsc-bounds.py` afterwards — Karkia adds 18 ZSC tables and the cached bounding
boxes in every ZSC in the game are wrong (`doc/zsc-bounding-boxes.md`), so confirm nothing
under-covers badly enough to pop out of the frustum.

### Stage 2 — gates and travel

The 8 usable `WARP.STB` gates at new ids with the `.IFO` warp objects repointed, then the
Wayfinder: NPC row, model, `.CON`, `LIST_EVENT` row, nine placements, and the QSD triggers.
Plus the entrance and return legs.

**Acceptance:** walk every gate in both directions, then teleport to all nine zones and back
out to Junon. No `IS_HACKING` disconnects — that is what a destination event position
resolving to NULL looks like, and it is why the Oro importer verifies every destination
byte-for-byte before writing.

### Stage 3 — monsters, un-tuned

38 `LIST_NPC` rows at **native ids 2685–2731** (all free on our side, which makes the AI's
summon references resolve with no binary patching), the 29 `.aip` files, character
models/skeletons/motions with the usual index remap, and the REGEN lumps refilled.

Copy for identity — name, model, size, sounds, attack type, range, AI id. Leave the stat
columns as Jrose wrote them for exactly one play session, so we can see the fights before
we change them, then never again.

Zero AI opcodes here are new to our server, so nothing to implement.

**Acceptance:** monsters spawn, animate, path, attack, and die. `/dps` shows damage flowing.
The D=Seed's summon behaviour fires. Nothing crashes.

### Stage 4 — the balance pass

The real work, and the reason Karkia cannot ship on Jrose's numbers. Karkia DEF is 2,350 at
level 213 where ours is 737, which puts every player swing on the damage floor of 5 —
4,229 swings to kill a level-213 trash mob, which kills the player in three hits. Full
measurements in the survey §7.

Re-derive level, HP, ATK, DEF, RES, HIT, AVOID and EXP from our own curve with the existing
passes: `rebalance-endgame-curve.py --stat def|res` fits the trend from levels 60–199,
`rebalance-oro-bosses.py` sets boss HP to 10x the HP trend, `rebalance-exp-rewards.py`
handles the 133x EXP gap. **Mind the order dependency** recorded in
`project_monster_balance_passes`: the DEF/RES pass reads a monster's current level and the
boss sidecar, so any level change means restore, re-apply, re-verify all of them.

Write it as a `rebalance-karkia.py` in the same style — idempotent, sidecar next to the STB,
`--dry-run` / `--verify` / `--restore` — not as edits folded into the importer. The importer
should stay a faithful copy so it can be re-run.

Then populate the three placeholder zones (§4, question 4).

**Acceptance:** re-run `scripts/balance-sim.py` against the written rows and check
swings-per-kill lands in the same band as our own monsters at that level. Then actually play
it.

### Stage 5 — drops

Author `ITEM_DROP` rows. Nothing is copyable — item ids mean different things across dumps.
Karkia's mob drop-table ids 831, 832, 835 and 851–854 are all free on our side, so keep them
and copy `LIST_NPC` col 18 verbatim.

**One trap to handle here.** `CCal::Get_DropITEM` falls back to `iDropTBL = iZoneNO` when the
mob's own drop roll fails, so `ITEM_DROP` rows are indexed by drop-table id *and* by zone
number in one row space. Our drop-table ids run 61–486 densely, so **rows 86, 87, 88, 131,
133–136 and 144 are already occupied by other monsters' loot** — row 87 is labelled "EVE Zone
(Farming System)", row 144 belongs to a pair of level-18 monsters. Adding Karkia at those
zone numbers newly activates the collision, and a Karkia mob whose roll fails would drop
level-18 loot. (This is not new — Oro's zones 71–82 already sit on occupied rows — but
Karkia is a chance to notice it. Either author sane tables at the Karkia zone ids too, or
keep every Karkia mob's drop rate high enough that the fallback effectively never fires.)

### Stage 6 — NPCs (optional, see question 5)

32 rows, models, `LIST_EVENT` rows (all 32 `.CON`s are registered in Jrose's table, which is
better than Oro where none were), and authored English dialog through the QEX1 appendix.
Nine are shopkeepers whose 14 `LIST_SELL` tabs need stock written from scratch.

---

## 4. Open questions

These change the work rather than being decidable during it. Recommendation first in each.

### 1. Where does Karkia sit in progression?

Karkia is authored at 211–250 against our 240 cap, and Oro already occupies 200–240. The
answer sets every number in stage 4.

- **(a) Post-Oro endgame, 225–240** *(recommended)*. Karkia becomes the thing you do after
  Muris. Compresses 211–250 into 225–240, keeps Oro relevant, needs no cap change. The
  entrance NPC then lives in Muris and Karkia is gated behind reaching Oro.
- (b) Parallel to Oro, 200–240 — a second route through the same band. More content at the
  same level, less sense of progression.
- (c) Raise the cap past 240 for Karkia. We did this once for Oro (`project_level_cap_240`)
  and the EXP curve work that came with it was substantial.

### 2. What happens to the raid tier?

Karkia's top end is a raid we have no systems for. `ks_2699` (Deadly Drake α, level 250) is
scripted to summon **two 6.5 M-HP "Hebarn Executives"**, and three Spire Village trash mobs
summon a 2.79 M-HP Corroded Golem. Our biggest boss is ~87 k HP, and per
`project_class_identity_pass` we have no threat table and no group content.

- **(a) Rescale them into our boss tier and drop the escalation** *(recommended)* — Drakes
  become ~10x-trend zone bosses, the executive summons are removed from the `.aip`. Keeps
  Karkia a solo/small-group planet, which is what our combat supports.
- (b) Keep them as aspirational raid bosses nobody can kill yet. Honest, but it means placing
  content that is currently dead.
- (c) Build toward group content, with Karkia's top end as the target. A much bigger project.

### 3. Do we hook Karkia to the Oro fate system?

The raid bosses are literally ヘバーン幹部 — **Hebarn Executives** — and our Oro fate system
already gates content on the Arua/Hebarn marker skills 2880/2881
(`project_oro_fate_system`). That is a ready-made narrative hook.

- **(a) Faction-flavoured but not gated** *(recommended)* — Karkia reads as Hebarn territory,
  everyone can go. No new gating code, and it does not strand half the playerbase.
- (b) Fate-gated: Hebarn players get a different reception, or Arua players a harder version.
  More interesting, more authoring, and it doubles the testing.

### 4. What goes in the three empty zones?

`KBurnedForest`, `KMemories` and `KFlowerGarden` have regen infrastructure laid out (23, 10
and 20 points; limits 265, 102, 188) but spawn only monster id 1 — チビゼリービーン, the
level-2 Jelly Bean. Jrose never populated them.

- **(a) Spread the existing Karkia roster across them** *(recommended)* — cheapest, and it
  gives the 21-monster Cemetery roster somewhere else to appear.
- (b) Author new monsters using art we already hold. More distinct, real work.
- (c) Leave them quiet — no combat, pure atmosphere zones. Two of them (Memories, Flower
  Garden) read that way from their names.

Related: **10 of Karkia's 31 monsters are re-skins of the other 21** — Spire Village is the
Cemetery roster again at +14 levels with an α suffix. Worth deciding whether to lean into
that (same enemies, harder) or re-theme the α set.

### 5. NPCs in the first release, or not?

The zones work without them. The 32 dialogs are Japanese Lua bytecode we cannot regenerate —
we would author replacements through QEX1.

- **(a) Wayfinder only in v1, the rest later** *(recommended)*. One NPC to write, and Karkia
  becomes playable at stage 4 instead of stage 6.
- (b) All 32 up front, so Spire Village reads as inhabited from day one. Nine shops need
  stock authored, which is a balance decision of its own.

### 6. What do the monsters' 23 skills become?

Karkia's AI casts 23 Jrose skill ids (716, 846, 2910–3685) through `AIACT_24`, 57 uses.
Those rows exist on our side but mean different things, so copied verbatim the monsters cast
whatever our row 3585 happens to be. **The Oro import cut exactly this corner** — it copied
`.aip` files verbatim — so there is no precedent to inherit.

- **(a) Blank them, ship melee-only, add skills back deliberately** *(recommended)*. Safe,
  and it makes the first tuning pass legible.
- (b) Map each to a comparable existing skill. 23 judgement calls, and a wrong one is a
  monster casting a player buff at you.
- (c) Author new monster skills. Real content, and `project_artisan_skill_import` shows the
  recipe works.

### 7. Where does the entrance live, and is it gated?

Follows from question 1. If Karkia is post-Oro, the entrance NPC belongs in Muris and the
return leg goes back there. If it is parallel, Junon Polis like Oro's Historian Jones. Also
open: a level requirement on the warp, and whether the return leg is free (Oro's is).

---

## 5. Effort shape

Rough, for sequencing rather than scheduling. The engineering is small and the authoring is
most of it.

| stage | engineering | authoring |
|---|---|---|
| 1 terrain/art | moderate — mostly reusing `import-oro.py` writers | zone names |
| 2 gates + travel | small — the tooling exists | dialog text, entrance placement |
| 3 monsters | moderate — CHR/ZSC/motion remap, again reused | none |
| 4 balance | small — one rebalance script | **large: the whole tier** |
| 5 drops | trivial | **large: a Karkia loot tier** |
| 6 NPCs | small | large: 32 dialogs + 14 shop tabs |

No server or client code change is required by anything above. The two places that could
change that are question 2 (group content) and question 6(c) (new monster skills).

## 6. Before the first line of code

- Re-read [doc/jrose-survey.md](jrose-survey.md) §2 — all three silent-failure traps apply.
- Answer questions 1 and 2 at minimum; they determine stage 4, which is the bulk of the work.
- `rose.vfs` is 1.99 GB and Karkia adds ~105 MB, so no rollover concern
  (`reference_vfs_offset_limit`), but bake with `scripts/pack.ps1` so the archive self-verifies.
- Servers cache STBs at startup — restart them after every stage, and rebake + redeploy the
  client for anything that touches `data/`.
