# Drops — the endgame loot tier

Karkia stage 5. **The wiring is done; no loot is authored yet.** This is the plan for
the content pass, plus everything about the drop system that is not obvious from the
code. Companion to [doc/karkia-roadmap.md](karkia-roadmap.md).

---

## 1. Where this stands

`scripts/rewire-karkia-drops.py` (applied 2026-09-07, idempotent, `--restore`able)
fixed the plumbing. **Karkia currently drops nothing.** That is deliberate — it was
previously dropping *the wrong thing*, and correct-and-empty is a better base to
author onto than plausible-and-wrong.

What it corrected:

- Karkia's own drop tables were **831/832/835/851–854**, copied verbatim from Jrose.
  Three of those are live for our own monsters — 831 Desert Scavenger, 832 Agitated
  Desert Scavenger, and **851 Fearsome Terrasaurus King**, our top boss. Authoring
  Karkia loot into them would have handed it to Oro. They are now **900–906**,
  keeping Jrose's own grouping (one shared table for the Cemetery roster, one for
  Spire Village, one per boss).
- Karkia's **zone fallback** (see §2) resolved to `ITEM_DROP` rows 86, 87, 88, 131,
  133–136 and 144 — which were live tables for thirteen of our own low-level
  monsters (Melt Dut, Moss Ant, Moss Golem, the Pomics, the Rackies, Beetle,
  Assistant Chef Woopie). Rows 86 and 87 are literally named *"EVE Zone (Fishing
  System)"* and *"(Farming System)"*. Those tables moved to **940–948** with their
  users repointed, so the zone numbers are Karkia's now.
- Drop chance (`col 20`) went **20 → 80**, our own level-200+ median. At 20, ~80% of
  Karkia's rolls fell through to the zone table; that is what players were picking up.

| | Karkia table |
|---|---|
| Cemetery roster (20 monsters) | 900 |
| Revived Quarantine Officer | 901 |
| D-Seed | 902 |
| Hebarn Officer Pazugenti | 903 |
| Hebarn Officer Scylla Mira | 904 |
| Corroded Golem + Revived Veteran | 905 |
| Spire Village roster (10, incl. Drake α) | 906 |
| zone fallback, per zone | 86, 87, 88, 131, 133–136, 144 |

---

## 2. How the drop system actually works

From `CCal::Get_DropITEM` (`src/common/calculation.cpp:132`). Worth reading before
touching any of this — three of its properties are surprising.

```
drop_var = (WorldDROP + col20 - rand(1..100) - (levelgap + 16)*3.5 - 10 + dropRate) * 0.38
if drop_var <= 0                     -> no drop at all
if rand(1..100) <= col19             -> money instead of an item
if col20 - rand(1..100) >= 0         -> table = col 18   (the monster's own)
else                                 -> table = the ZONE NUMBER
cell = ITEM_DROP[table][1 + rand(0..min(drop_var, 30))]
```

- **A drop-table id and a zone id are the same namespace.** There is no separation.
  This is why Karkia's zone numbers were already somebody's loot table, and it will
  happen again to any content imported at a new zone number. Check both before
  allocating.
- **`col 20` is doing three jobs at once**: how often anything drops, how wide a
  slice of the table is reachable, and how often the zone fallback is used. It is not
  a clean "drop rate" knob.
- **A cell is `type * 1000 + number`**, so `item.m_cType = cell / 1000` and
  `m_nItemNo = cell % 1000`. **Item numbers above 999 cannot be dropped**, full stop.
  That is a tighter limit than the item *encoding*, which `tagBaseITEM` widened to an
  11-bit number (0–2047) — the drop table simply cannot address them.
- Cells valued **1–4 are redirect groups**, re-rolled at column `26 + value*5 +
  rand(5)`. A table therefore has a common section (columns 1–25) and four rarity
  buckets (26–50). `ITEM_DROP.STB` has 51 columns.
- `Get_DropITEM` returns false outright when the player is **10+ levels above** the
  monster, so lowering a monster's level can silently kill its drops.

---

## 3. What we can and cannot drop

| set | ids | droppable? |
|---|---|---|
| Jrose weapons (`project_jrose_weapon_import`) | 1381–1453 | **0 of 73** — all above 999 |
| Jrose back items (`project_jrose_back_import`) | 957–1061 | 43 of 105 (957–999 only) |
| Jrose shields (`project_jrose_subwpn_import`) | 308–342 | **35 of 35** |

The imported Jrose weapon sets **cannot be loot** without changing the cell encoding.
Options, in increasing order of cost: sell them from a Karkia NPC in stage 6 (free,
and stage 6 is coming anyway); make them quest rewards; or widen the drop encoding,
which touches shared client/server code and every existing table's meaning. **The
shop is the recommendation** — it also gives Karkia's NPCs a reason to exist.

---

## 4. The content plan

Three layers, in the order they should be authored.

### 4a. Materials as the backbone

The filler that stops a kill feeling empty, and it feeds crafting. Cheap, uses items
we already have, and it is what our own tables are mostly made of — our best live
endgame tables (940–942, ex-Moss Golem/Ant, level 200–210) run roughly **15–20
material cells to 4–8 use-item cells**, which is the ratio to copy.

Candidates already in `LIST_NATURAL`, at the tier Karkia sits in:

| | |
|---|---|
| metals | `12:8` Chromium, `12:9` Tiar, `12:10` Damascus, `12:16` Orihalcon, `12:17` Adamantium |
| woods | `12:37` Cinnamon, `12:38` Red Sandalwood, `12:39` Otherworldly, `12:40` Sephiroth |
| leathers | `12:47` Thick, `12:48` Hard, `12:49` Transparent, `12:50` Patterned |
| cloth | `12:59` Twill |

Karkia is a dead world of ruins and undead, so the flavour argument is for **metals,
leather and bone over wood** — Spire Village and the Cemetery should not read like a
forest. That is the one place to deviate from copying our existing tables wholesale.

### 4b. Use items as the reliable second layer

`10:13` Vital Water (XL), `10:32` Spiritual Water (XL), `10:157` HP Point (+1000),
`10:167` MP Point (+700), `10:171` Stamina. An endgame zone that funds its own
potion consumption is doing something useful even before the rare drops land.

### 4c. The imported Jrose sets as the signature drops

**This is the part that makes Karkia's loot feel like Karkia's.** The 35 shields
(`308–342`) and the 43 addressable back items (`957–999`) came from the same client
as Karkia itself, they are already in with art and stats — and **they currently have
no source anywhere in the game**. Karkia is where they should come from. It closes
`project_jrose_subwpn_import` and half of `project_jrose_back_import`.

Put them in the rarity buckets (columns 26–50), not the common section.

### 4d. Bosses

Each already has its own table (903–906). They should carry the best of §4c at a
much better rate, and are the natural home for anything we do not want in the field.

Note `NPC_DROP_MONEY` (`col 19`) is **0 across our entire game**, Karkia included —
nothing drops money today. Worth deciding deliberately rather than inheriting.

---

## 5. Oro has exactly the same problem

Not a Karkia-only defect, and worth doing in the same pass:

| | monsters | live drop table | empty table |
|---|---:|---:|---:|
| Karkia | 38 | 0 (wired, unfilled) | — |
| **Oro (lv 200+)** | 40 | **0** | **38** |
| Junon/Eldeon 150–199 | 100 | 59 | 33 |

Oro's monsters point at tables 773–851 and every one of them is empty, so Oro has
been running on its zone fallback since it was imported. **The whole endgame has no
authored loot tier** — Karkia just made it visible. Whatever shape §4 lands on should
be applied to Oro immediately after.

---

## 6. Open questions

- Should Karkia drop **our** endgame weapons (ids ≤ 999), or stay materials- and
  armour-flavoured so weapons stay a shop/quest reward?
- Money drops: leave at 0 like the rest of the game, or make Karkia the exception?
- The three placeholder zones (131/133/144) still spawn only a level-2 Jelly Bean
  (roadmap §4, decision 4). Their zone tables exist and are empty; leave them until
  the zones are populated.
