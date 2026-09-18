# Mors Survey (Jrose)

**Status:** survey only — nothing imported, no data or code changed. Import deferred by
decision on 2026-09-18.
**Date:** 2026-09-18.
**Dump:** `C:\Users\Thomas\Desktop\Testclients\Jrose` (loose `3Ddata\`).
**Prior art:** [doc/karkia-survey.md](karkia-survey.md) — Mors is authored as a direct
continuation of Karkia and shares its container quirks, its AI lineage and its
`QN-KAK001.QSD`. Read that first; this document records what differs.

Reuse `scripts/rose-data-reader.py` for anything that reads Jrose tables — the three traps
in [doc/jrose-survey.md](jrose-survey.md) §2 all apply here.

---

## 1. Verdict up front

**Import it, but only after the dungeon question is answered.** Half of Mors — two of its
four zones, three of its bosses and the back half of the quest chain — lives inside
Jrose's instanced-dungeon generator, which we do not have. The outdoor half is the
cleanest port we have surveyed: zero missing assets on either the map or the character
side, zero AI opcodes our server cannot run, and almost no id collisions.

| | |
|---|---|
| Zones | **4** — 2 outdoor (5x5 chunks, 800 m square each), 2 **instanced dungeons** |
| Planet | slot **10**, unnamed. `STR_PLANET.STL` names only 1–7, and the fiction calls Mors a *satellite*, not a planet |
| Map chunks | **50** (441 files, 18.2 MB). Half of Karkia, a third of the Oro import |
| Map art | **837 assets referenced, 0 missing.** 185 new to us + 271 differing = ~21.4 MB |
| Character art | 28 skeletons, 264 motions, 44 `PART_NPC` objects → **664 files, 0 missing**, 548 new (~24.2 MB) |
| Monsters | **39** placed across the four zones, **+12** reachable only through AI summons = 51 rows. Levels **226–265** |
| NPCs | **10 placed**, 13 `.CON` dialogs, all 13 registered in `LIST_EVENT` (rows 550–569) |
| Dialog | **1,186 lines, Japanese only.** Zero English anywhere in the block |
| Quests | **26** named quests (557–573, 588–598) in `QN-KAK001.QSD` + 24 per-monster kill files |
| AI | **34 `.aip`**, conditions `{2,3,4,5,7,8,9,10,11,12,14,28,29,31}`, actions `{4,5,7,9,12,13,14,15,16,17,20,24,25,36,38}` — **every one already implemented** |
| **Blocker** | Zones 139 and 141 are **procedural dungeons**. No system — §7 |
| **Blocker** | **172 skill casts** naming 33 skills. 18 of the 33 would do nothing here — §6 |
| **Blocker** | Levels 245–265 sit above our 240 cap; drops use a different table format — §8 |
| **Gap** | The Karkia-side entrance NPC is written, registered, and **placed nowhere** — §5 |

VFS budget is not a concern: `rose.vfs` is 2.20 GB against the 4 GB ceiling, and the whole
of Mors is well under 50 MB.

---

## 2. What Mors actually is

`LIST_ZONE.STB` rows 138–141, all planet 10:

| row | folder | shape | Japanese name | working English | sky | camera |
|----:|---|---|---|---|---:|---:|
| 138 | `Satellite\STSatellite` | 5x5, 800 m | モルス | Mors | *blank* (0) | — |
| 139 | *procedural* | 6 layouts, 21²–35² | 旧・モルス霊廟 | The Old Mors Mausoleum | 1 | 6 |
| 140 | `Satellite\STOutpost` | 5x5, 800 m | モルス前哨基地 | Mors Outpost Base | *blank* (0) | — |
| 141 | *procedural* | 5 layouts, 13²–35² | モルス前哨拠点 | Mors Outpost Stronghold | 17 | 9 |

"Mors" is Latin for death, and the bestiary is a Requiem mass: Dies Irae, Inquisitio,
Angelus, Imperator, Redemptio, Ergastulum, Damnatio, Custos, Apostolus, Exorcista,
Sacerdos, Gladiomurus, Arbor Domina. The place names are not — モルス霊廟 is a mausoleum,
and the dungeon is the tribe's own ancestral tomb, taken over by the enemy.

Zone 142 (ラーの食料庫, "Ra's Larder") sits next to these rows and is **not Mors** — it is
planet 8, an Oro cooking dungeon. Scope by planet column, not by row adjacency.

Sky columns on 138 and 140 are **blank**, which is the Skaaj trap: the client reads the
cell as an integer and gets sky 0, while the map editor's old `IsValidMap` rejected the
row outright. The editor now resolves it the client's way (`MapManager.SkyIndex`), so
these open — but write an explicit 0 on import, the way `import-skaaj.py` does.

Sky 17 (zone 141) and camera rows 6/9 are the same ones Karkia already needs.

---

## 3. The story, and why it is the reason to import

This is the only Jrose content we have surveyed whose *writing* is the deliverable. It
answers the question our Karkia import leaves open, and it is the bridge to Hebarn.

The Winged Tribe (翼人族) tell it across 1,186 lines:

- Mors was granted the office of **Watcher** by the goddess **Arua**.
- When the goddess **Hebarn** raised her banner against Arua, the **Devil Pest**
  (デビルペスト) was born. The Winged Tribe's charge was to watch it and, if need be,
  hold it back. They failed; it leaked out to every planet.
- The Winged Tribe are **resistant**. It is not an infection but a curse that nests inside
  and transforms, and it can only take you **if you wish it**. Those who gave in are the
  **Fallen** (堕天族).
- The player is the **救世主**, the awaited savior, identified by a glowing feather their
  god sends to the one who will save the lower world.

The cast is *Hamlet*, and not by accident — アムレート is **Amleth**, the pre-Shakespearean
Danish original:

| id | name | role | source |
|---:|---|---|---|
| 4115 | アムレート **Amleth** | 統率者, leader | Hamlet |
| 4116 | マーセラー **Marcellus** | 導き手, guide (greets you on arrival) | Marcellus |
| 4117 | オフィリア **Ophelia** | 指南者, equipment instructor / smith | Ophelia |
| 4118 | スターン **Stern** | 補給員, quartermaster (shop/storage/repair/refine) | Guildenstern |
| 4119 | クランゼン **Kranzen** | 補佐官, adjutant (medal exchange, repeatables) | Rosencrantz |
| — | ガイロディアス **Gairodias** | named once; never appears | Claudius |

Amleth's arc: he is not the real leader. His father — the *previous* Amleth, the great
king — was reported to have died bravely at the front. He was in fact **assassinated on
the battlefield by Gairodias, his own younger brother**, who then stood before the tribe,
declared he would lead in his brother's stead, **took Amleth's mother and a large part of
the army, and defected to the Fallen**. What remains on Mors are his father's loyalists.
Amleth says he might have been consumed by revenge if he were alone; instead he means to
finish his father's watch.

The outpost cast (zone 140) is a separate, plainer set: リニヨン Rinyon (部隊長, captain),
イリス Iris (scout), スティン Stin (medic, stammers), プリム Prim (magic officer),
ビルマ Birma (researcher).

**The story stops mid-sentence.** The last beat is Rinyon confirming that Apostolus really
does resurrect, and Amleth reading the report: *"So falling grants them some power… that
is why our intelligence has been useless. For now we hold the line and think of a way
through."* Gairodias never appears. Hebarn never arrives. Quest 599 does not exist.

---

## 4. Dialog, and the one free gift in it

13 `.CON` files, all registered in `LIST_EVENT` rows 550–569. Text lives in
`ULNGTB_CON.LTB` rows **32030–33358** — the last 4% of a 33,359-row table, i.e. literally
the newest writing in the client.

Coverage across the block: **JA 1,186 / EN 0 / KO 0**. Everything needs translating.

The gift: Jrose **repurposed the Korean column (1)** as an authoring note naming the quest
and node — `Main_Q557_01`, `Main_Q560_03`, `Main_590_01`. Every line is therefore already
mapped to its quest step, which is exactly the index a translator and an importer both
want, and which no other region of the table has.

`.CON` Lua is XOR-obfuscated, so **grepping a `.CON` for a trigger name finds nothing and
proves nothing**. Decode the script blob first (`xor_key(lua_len, file_size)`, blob at the
offset in header word 520) — that is how `warp_to_morusu` was located. Same key scheme
`src/tools/quest-editor/src/convo.rs` already implements.

### Not Mors, despite the filename

`EM04-006.CON` / `EM04-007.CON` are **シュタイニア Steinia** and **ニトラリア Nitraria**,
two 惑星探索者 treasure hunters placed in **Karkia's Flower Garden**
(`KFLOWERGARDEN\33_32.IFO`), who run the Lamp summon system and the 灰塵のファフニール
fight. Their text sits inside the Mors LTB block and their filenames carry the Mors prefix.
**Importing by filename prefix drags them onto the wrong planet.**

---

## 5. The entrance is written, registered, and placed nowhere

The bridge from Karkia is complete as data:

1. **Leve** (`[守護門番]レーヴェ`, NPC 4093, Karkia Memories) researches monsters carrying a
   divine blessing that resembles Hebarn's but is *far stronger*, concludes another god is
   moving against Karkia, and hands the player a **glowing feather** (quest 555).
2. Quest 556 sends the player back to **the Abandoned Church** (zone 86).
3. `EM86-014.CON` — a Winged envoy — recognises the feather and offers passage.
4. Its Lua calls trigger **`warp_to_morusu`**, a `REWD_007` in `QN-KAK001.QSD` landing at
   **zone 138, (520000, 521100)**.
5. Marcellus's `warp_to_kyokai` is the return leg.

**`EM86-014` is placed on no map.** Every other NPC in the series is placed — EM86-001…009
in the church, EM86-010…013 in Spire Village — and `EM86-014` alone is not. `LIST_NPC` row
**4128** holds a *second* `[翼人族の導き手]マーセラー`, also placed nowhere; it is almost
certainly him. As shipped in this client the door to Mors has no doorman.

That is a one-line `.IFO` placement to author, not a missing feature.

`WARP.STB` 191/192 are Mors's only two gates (138↔140) and **both collide with our Karkia
gates** (`WARP_K8786`, `WARP_087088`). Renumber; 194+ are free.

---

## 6. Monsters and AI

39 monsters across the four zones, named by their `.aip` prefix — `st_` (138), `stdg_`
(139), `sto_` (140), `stodg_` (141). All 39 bind a real skeleton in `LIST_NPC.CHR`, with
bespoke rigs dated `_20231026`, `_20231221`, `_20240704`.

| zone | trash | mid | bosses |
|---|---|---|---|
| 138 Mors | Dies Irae, Inquisitio, Angelus (lv245) + 3 critters (lv226–231) | Imperator, Redemptio (lv251) | Ergastulum (lv254, 47k HP), **Damnatio**, **Solnigel** (lv258, 62k) |
| 139 Mausoleum | "Irecti" variants of the field five, Sacerdos, Sabulum Arena, Ira Daemonio, Pergrande | — | **Gladiomurus** (lv258, 43k) |
| 140 Outpost | Aeter Pupa, Ira Daemonio, Sacerdos + 3 critters | Arbor Domina, Exorcista (lv256) | Pugilatus (lv259), **Custos** (lv263, 62k), **Apostolus** (lv263, 62k) |
| 141 Stronghold | Starda Ape x2 | — | **Andreios** (lv265), **Diyavol** (lv264) |

Two are narratively load-bearing. **Solnigel** is a noble Winged house that defected, whose
family power is *making duplicates of itself* — the in-fiction justification for it being
the repeatable dungeon target. **Apostolus** (呪術師) revives for as long as his
soul-source survives, which is the cliffhanger the chain ends on.

### The summon closure

Walk it before importing — this is the `Change_CHAR` crash class. 12 ids are reachable
only through AI actions, **all 12 occupied in Jrose** (no blank rows, so no crash), of
which **9 are free in our table** and 3 collide:

| id | name | ours |
|---:|---|---|
| 2294–2296 | マスターロッド / カタール / ランチャー | **occupied** (Eldeon Ikaness) — remap |
| 2488, 2490 | ペスオクトアレネ, ルトゥムプーパ | free |
| 2888–2891 | `[カーキアの英雄]` **Yurias, Yuki, Ellen, Aishira** — the Heroes of Karkia, summoned by Custos and Damnatio as corrupted thralls | free |
| 2892, 2951, 2957 | ミディアテンペスト, テルースプーパ, スターダエイプ | free |

### AI opcodes: nothing new

34 `.aip` parse cleanly with `audit-ai-monster-refs.py`'s reader. Conditions used are
`{2,3,4,5,7,8,9,10,11,12,14,28,29,31}` and actions
`{4,5,7,9,12,13,14,15,16,17,20,24,25,36,38}`. Our server implements conditions 1–31 and
actions 1–38, so **every opcode is already covered** — the same result Karkia gave.

### The skill blocker

**172 `AIACT24` casts across 34 files, naming 33 distinct skill ids.** All 33 are occupied
in Jrose's `LIST_SKILL.STB`, the higher ones with descriptive Japanese names
(`アストルム 広範囲魔法攻撃（青）`, `鳥ボス 範囲火炎(強)`). Against ours, comparing
`SKILL_TYPE` (game column 5) the way `audit-ai-skill-refs.py` does:

| | count | ids |
|---|---:|---|
| **blank in ours** | **15** | 1651, 2990, 3690, 3705, 3710, 3722, 3723, 3724, 3726, 3743, 3744, 3750, 3761, 3782, 3783 |
| **occupied, `SKILL_TYPE` differs** | **3** | 3096, 3687, 3691 |
| occupied, same `SKILL_TYPE` | 15 | 1601, 2901, 2910, 2912–2916, 2922, 2952, 2987, 3025, 3044, 3594–3597 |

**18 of the 33 would do nothing as imported.** The 15 blanks are the "blank row" class:
the server broadcasts the cast, `Skill_START` switches on `SKILL_TYPE 0` and does nothing,
and the client plays a casting motion that **replaces an already-applied swing** — the bug
that killed a tester at 1300 HP (see `project_preempted_swing_fix`). The 3 mismatches fail
the same way for a different reason: Jrose's 3687 is `シャグラン・アレニェ 範囲毒攻撃`
(type 17) while ours is `GM Healing` at **type 0**, and 3691 is `凶ドラ HP残し` (type 17)
against our `GM Purify`, also type 0. A blank-row check alone will not see these; the type
comparison is what catches them.

The remaining 15 share a type and are plausibly the same lineage — several are RoseZA/ruff
rows we already imported (3044 Inguz Stun Wave, 3594–3597 Dispel Buffs / Area Slow / Kera
Stun Blast). *Plausibly* is the operative word: matching `SKILL_TYPE` is what the audit
flags on, not proof of a matching skill. Spot-check them against the Jrose rows before
trusting them.

The tooling is built for this: `scripts/import-monster-skills.py` for the chain (effect,
bullet, sound, status columns), `--dest` for collisions, `audit-ai-skill-refs.py --remap`
to re-point casts. A known job of known size — roughly the Grand Master Devourer kit times
four — but not free, and it must happen before anything is spawned.

Check the cast-motion convention on import too (`nMotion` casts, `nMotion+1` releases).
Every Mors cast uses motion **6 or 8**, so slot pairs 6/7 and 8/9 must exist in each
model's CHR entry, or the payload folds silently ~3 s late with no visual.

---

## 7. The dungeon blocker

Zones 139 and 141 point at `3Ddata\Maps\Oro\ramesses\dungeon.zon` — Jrose's
instanced-dungeon generator, a `.ZON` with no terrain, assembled at runtime from a
room-prefab `.ZSC` plus a layout `.STB`. **We have no such system**, and the Karkia survey
already scoped its six equivalent rows out for the same reason.

What Mors ships for them, all present and complete:

| | layouts | sizes | ZSC objects | meshes | textures |
|---|---:|---|---:|---:|---:|
| `STSatelliteDg` | 6 | 21²–35² | 241 | 17 | 17 |
| `STBaseDG` | 5 | 13²–35² | 241 | 45 | 45 |

`npc group` is blank in both tables, so the dungeon population is server-side — the same
as Karkia's Memory Dungeon.

The cost of leaving them out is not cosmetic. Out with them go **Gladiomurus, Andreios and
Diyavol**, quests **570, 571, 572 and 598**, and the chain's two climaxes. Quest 571 (the
Solnigel force survey) is also one of the two repeatables the whole medal economy runs on.

Three ways forward, in increasing order of work:

1. **Outdoor only.** Zones 138 and 140, quests 557–569 and 588–597. Re-point 570–572 and
   598 at outdoor targets or drop them. Cheapest, and it still delivers the entire Amleth
   story and both outpost arcs.
2. **Hand-author the two dungeons as fixed maps**, the way we would any other zone. The
   tilesets are complete, so this is level design, not engineering.
3. **Implement the generator.** Out of proportion to this content alone, but it would
   unlock Karkia's four dungeon rows and Oro's Ramesses mine at the same time.

Recommend 1 for a first pass, with 2 as a follow-up.

---

## 8. Balance and drops

Levels **226–265** against our **240 cap**, which puts the top of Mors past the level gate
(`kLevelGateScale` 1.05, see `reference_combat_level_gate`). At a level-240 character,
auto-attack land rate against Mors is:

| monster level | example | auto-attacks landed |
|---:|---|---:|
| 245 | Dies Irae, Inquisitio, Angelus | ~86% |
| 254 | Ergastulum | ~68% |
| 258 | Solnigel, Damnatio, Gladiomurus | ~60% |
| 263 | Custos, Apostolus | ~48% |
| 265 | Andreios | ~44% |

Skills use the gentler non-proportional gate and stay effective throughout — that
asymmetry is intended and should be left alone, but it means Mors as authored is a
caster's zone unless the levels come down. A `rebalance-mors.py` in the shape of
`rebalance-karkia.py` is the expected fix; note the ordering rules in the CLAUDE.md balance
section (DEF/RES after any level move, bosses before EXP), and that the Karkia and Eldeon
fits would need a new exclusion band for whatever id range Mors lands in.

Two other stat shapes to expect: field trash is **low HP / high ATK** (408–796 HP at
ATK 1600–2500), and boss DEF runs 3000–3500, which against a level-240 ATK approaches the
`(ATK - DEF + 250)` damage floor.

**Drops must be re-authored.** Jrose stores them in `ITEM_DROP(NEW).STB` — 1200 rows x 64
columns, item/weight pairs, and an item-id encoding (`12001533`, `10005573`) that is not
our `type * 1000 + no`. Note that `ITEM_DROPNEW.STB` sits beside it and is **entirely
blank**; reading the wrong one of the two gives a silent empty result. Our `ITEM_DROP.STB`
is 3701 x 51 in the classic format. Tables **872–891 are free in ours** (831 is not — it is
an Oro table), so the ids can be kept; the contents cannot. Same job
`scripts/add-oro-drops.py` did for Oro.

---

## 9. Containers and id collisions

Everything parses with the readers in `scripts/import-oro.py`. The `.ZON`s are the
**stripped newer variant** the Karkia survey documents — 28-byte block 0, lumps 0–3, and
**no `LUMP_ECONOMY`** — so the same synthetic lump 4 fix applies, for the same reason
(`CEconomy::Init` otherwise runs off uninitialised memory).

| table | Mors wants | our state | action |
|---|---|---|---|
| `LIST_NPC` monsters | 2481–2487, 2895–2900, 2933–2956, 4120–4127 | **all free** | **import at native ids** — keeps AI summon references correct for free |
| `LIST_NPC` NPCs | 4115–4119, 4128 | free | native ids |
| `LIST_NPC` NPCs | 4138–4142 | **occupied** — our remapped Karkia church NPCs (Fritz, Nemo, Petri…) | remap |
| `LIST_NPC` summons | 2294–2296 | **occupied** (Eldeon) | remap |
| `LIST_ZONE` | 138–141 | free (our table is 145 rows, highest occupied 144) | native rows |
| `LIST_ZONE_S.STL` | `LZON138`–`LZON141` | free | native keys |
| `WARP.STB` | 191, 192 | **occupied** (Karkia gates) | **renumber** — 194+ free |
| `FILE_AI` | 1158–1165, 1169–1175, 1204, 1208–1211, 1216–1217 | free (2252 rows) | native rows |
| `ITEM_DROP` | 872–891 | free | native ids, contents re-authored (§8) |
| `LIST_QUEST` | 557–598 | free (5515 rows) | native rows |
| `LIST_EVENT` | 13 `.CON` registrations | rows 550–569 not present here | copy the rows |
| items (BODY/FOOT/ARMS/BACK/JEWEL/JEMITEM/QUESTITEM/USEITEM) | all beyond our row counts | — | grow and append; ids will not survive |
| planet 10 | — | we use 1, 2, 3, 4, 8 | fine; `Check_WarpPayment` treats planet ≥ 4 uniformly. `STR_PLANET.STL` has no row 10, so add one if Mors should name itself |

Item ids are the one place nothing lands natively: every Mors item table index is past the
end of ours, so the 10 avatar sets, 4 gems, 28 rings/necklaces/earrings, the White Wing
Medals and 26 quest items all become appends with new ids — and every QSD reward payload
referencing them must be rewritten, exactly as `QUEST_ITEM_REMAP` does for Oro.

---

## 10. Art

The map ZSCs reference **837 assets and every one is present.** Where they come from:

| source folder | assets |
|---|---:|
| `junon` | 634 |
| `satellite` | 163 |
| `karkia` | 23 |
| `npc` | 11 |
| `eldeon` | 5 |
| `skaaj` | 1 |

Like Karkia, Mors is mostly re-dressed Junon art with a small bespoke set. Against our
`data/`: **381 byte-identical, 271 differing, 185 new** — roughly 21.4 MB to copy, and the
271 differing files need the usual per-file decision (ours are generally the better copies
where we have retouched them).

Character side: the 51 monster/NPC rows pull **28 skeletons, 264 motions and 44
`PART_NPC.ZSC` objects**, resolving to **664 files, none missing**, of which **548 are new
to us** (~24.2 MB). The bespoke rigs — `BOSS01_ANGEL_20231221`, `BOSS02ANGEL_20231026`,
`ARMOR_WARRIOR_BONE_20240704`, `SARUHANE_BONE_20240704`, `NPC01_1216`, and a `MOVEWING`
set — are the newest assets in the entire dump.

Both outdoor maps ship a `MINIMAP.DDS`. Neither zone sets a world-map number, so Mors
would not appear on the star map without one.

---

## 11. Traps, collected

- **`.CON` Lua is XOR-obfuscated.** Grepping a `.CON` for a trigger name finds nothing and
  proves nothing. Decode first.
- **`EM04-006` / `EM04-007` are Karkia, not Mors.** Scope NPCs by placement, never by
  filename prefix.
- **Zone 142 is Oro**, not Mors. Scope by planet column, not row adjacency.
- **Jrose strips spawn rosters from the client build.** Mors's regen points hold Red
  Jellybeans and a blank id 20 — but so do Karkia's, and Junon's starter field has *no*
  regen points at all. This is the house pattern, **not** a signal that the content is
  unfinished. Spawn placement is ours to author either way, as `SPAWN_ROSTER` was for
  Karkia.
- **`ITEM_DROPNEW.STB` is blank; `ITEM_DROP(NEW).STB` is the real one.** Two files, one
  bracket apart, and the decoy reads as "no drops authored".
- **A blank sky column means sky 0**, not an invalid row.
- **`*.IFO` + `*.ifo` globs double-count on Windows** (the 667 lesson) — the two outdoor
  maps have 25 chunks each, not 50. The chunk `.IFO`s also sit *beside* the per-chunk
  folders, not inside them, so `*/*.IFO` silently matches nothing.
- **`LIST_NPC` column 18 is the drop table, not 19.** Jrose labels its columns; read the
  header rather than assuming our offsets.
- **AI entity types are tagged.** Condition types are `0x04000000 | n`, action types
  `0x0B000000 | n`, and the dispatch table has a NULL at index 0 — so file type 25 is
  `F_AIACT24`, the skill cast. Mask wrong or go off by one and 172 casts look like zero.
- **The skill-name lookup through `LIST_SKILL_S.STL` fails silently** on this dump; a blank
  name is not a blank row. Test `occupied()` on the STB row instead.

---

## 12. If and when we import

Suggested staging, mirroring `import-karkia.py`:

1. **Terrain and art** — 50 chunks, 4 map ZSCs, the two dungeon tilesets (cheap to carry
   even if the dungeons are deferred), `LIST_ZONE` 138–141 + STL keys, synthetic
   `LUMP_ECONOMY`, explicit sky 0.
2. **Characters** — 51 `LIST_NPC` rows with the three remaps, `LIST_NPC.CHR`, `PART_NPC`
   objects, 664 asset files, 34 `.aip` at native `FILE_AI` rows.
3. **Skills** — `import-monster-skills.py` for the 18 broken ids, spot-check the other 15,
   then `audit-ai-skill-refs.py --restore` and re-run. **Before any spawns exist.**
4. **Spawns** — author `SPAWN_ROSTER` / `SPAWN_CAP` / camps ourselves; simulate
   `CRegenPOINT::Proc`, never sum `limitCNT`.
5. **Balance** — `rebalance-mors.py`; levels first, then DEF/RES, then EXP.
6. **Drops** — re-author tables 872–891 in our format.
7. **NPCs, dialog and gates** — 13 `.CON` + `LIST_EVENT` rows, translate 1,186 lines using
   the column-1 quest-step index, renumber warps 191/192, **and place `EM86-014` in the
   Abandoned Church.**
8. **Quests** — 26 triggers out of `QN-KAK001.QSD` with item-id remapping, minus whatever
   the dungeon decision removes.

Step 7's last clause is the whole difference between a zone you can GM-warp to and a
planet the player can find.
