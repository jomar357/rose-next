# Karkia Survey (Jrose)

**Status:** survey only — nothing imported, no data or code changed.
**Date:** 2026-09-06.
**Dump:** `C:\Users\Thomas\Desktop\Testclients\Jrose` (loose `3Ddata\`).
**Scope decision going in:** quests are **out**. Karkia's are Japanese, and the RoseZA
quest import was the painful half of `project_oro_import`. This survey therefore treats
terrain, art, monsters, NPCs and gates as the deliverable, and quests as ours to author.

Reuse `scripts/rose-data-reader.py` for anything that reads Jrose tables — the three traps
in [doc/jrose-survey.md](jrose-survey.md) §2 all apply here.

---

## 1. Verdict up front

**Import it. The container work is the cleanest of any port we have done; the monster
stats are unusable and have to be re-derived.**

| | |
|---|---|
| Real zones | **9** (plus 6 zone rows that are instanced-dungeon slots — see §2) |
| Size | **111 map chunks**, 2.84 km² of terrain. Biggest zone 7x7 (1120 m square) |
| Format | Every `.ZON`, `.IFO`, `.ZSC`, `.CHR`, `.AIP` parses with our existing readers |
| Missing assets | **Zero.** 900 map meshes, 435 map textures, 115 character meshes, 44 skeletons, 227 motions — all present |
| New bytes | ~105 MB. `rose.vfs` is 1.99 GB against a 4 GB ceiling |
| AI | 29 `.aip` files, **zero opcodes our server does not already run** |
| Monsters | 31 spawned + 7 AI-summoned, levels 211–250 |
| NPCs | 32, with all 32 `.CON` dialogs present *and* registered in `LIST_EVENT` |
| **Blocker** | Monster stats come from a game where players hit ~3x harder. As authored they are unplayable — §7 |
| **Blocker** | Karkia has **no entrance**, and splits into two disconnected clusters — §5 |

Both blockers are authoring work, not engineering work. Nothing in this survey needs a
server or client code change.

---

## 2. What Karkia actually is

`LIST_ZONE.STB` has 15 rows in the Karkia family. Only **9 are real maps**; the other 6
point at `3Ddata\Maps\Oro\ramesses\dungeon.zon`, which is Jrose's instanced-dungeon
generator — a `.ZON` with only lumps 0 and 1, no terrain at all, built at runtime from the
room-prefab `.ZSC`/`.STB` sets in `MAPS\KARKIA\KCATACOMB`, `KHOSPITAL`, `KMEMORYDG` and
`KFLOWERGARDENDG`. We have no such system. **Those 6 rows are out of scope**, and their
four prefab directories can be skipped entirely.

The 9 real zones:

| row | folder | chunks | extent | Japanese name (`LIST_ZONE_S.STL`) | working English |
|----:|---|---:|---|---|---|
| 86 | `KChurch` | 2x2 | 320 m | 取り残された教会 | The Abandoned Church |
| 87 | `KCemetery` | 7x7 | 1120 m | 荒れ果てた共同墓地 | The Desolate Cemetery |
| 88 | `KSpireVil` | 5x5 | 800 m | スピール村 | Spire Village |
| 131 | `KBurnedForest` | 3x3 | 480 m | 焼却された森 | The Burned Forest |
| 133 | `KMemories` | 3x3 | 480 m | カーキアの記憶 | Memories of Karkia |
| 134 | `KMemoriesBoss` | 1x1 | 160 m | 無限牢獄 | Infinite Prison |
| 135 | `KTowerPlace` | 2x2 | 320 m | 絶望の塔 | Tower of Despair (grounds) |
| 136 | `KTower` | 1x1 | 160 m | 絶望の塔 | Tower of Despair |
| 144 | `KFlowerGarden` | 3x3 | 480 m | カーキアの花園 | Garden of Karkia |

For scale: our biggest zones are `EJ01` at 77 chunks and `JPT01` at 48. Karkia's Cemetery
(49) is on par with Junon Polis. The whole planet is **smaller than the Oro import** — 111
chunks against ~150 across Oro's 12 zones.

Two of the nine are effectively empty shells today. **`KTower` has one object, no NPCs, no
monsters and no gates**; `KMemoriesBoss` has six objects and one gate out. They are rooms
waiting for content, not maps we would be losing anything by deferring.

---

## 3. Container formats: all compatible, with one wrinkle

Everything parses with the readers already in `scripts/import-oro.py`. Specifically
verified:

- **9 `.ZON`** — all have both a `start` and a `restore` event position, so none of the
  per-zone `ZONE_REVIVE_POS` hand-fixing the Oro import needed applies here.
- **111 `.IFO`** — 2,844 object placements, 12 building placements, 2,011 regen points,
  32 NPCs, 11 warp gates, 3 effects, 3 morphs, 1 event object. All 23 `OCEAN` lumps are
  well-formed (`float size; i32 count; count x 6 floats`; it is not an object lump, so
  `parse_object_lump` will "fail" on it — that is the script, not the data).
- **16 map `.ZSC`** — every object id placed by an `.IFO` is inside its table's object
  count, and no referenced object is empty.
- `LIST_NPC.CHR` / `PART_NPC.ZSC` — all 70 characters have a CHR entry.

### The wrinkle: Karkia `.ZON`s are the stripped, newer variant

Karkia — and Satellite, Skaaj, Arena, Fortress, MyRoom2, Ulverick, everything Jrose added
late — writes a **28-byte block 0 and no `LUMP_ECONOMY`**. Classic zones write a
36,892-byte block 0 (a 64x64 editor cell table) plus lump 4.

The client does not care: `CTERRAIN::ReadZoneINFO` reads exactly 28 bytes and throws away
width and height. The **server** half-cares. `CZoneFILE::ReadECONOMY` is what calls
`CEconomy::Load`, and with no lump it never runs — so `m_nTown_CONSUM[]` and
`m_dwTown_COUNTER` keep whatever the heap held, and `CEconomy::Init` computes
`m_iTownITEM[nP] = m_nTown_CONSUM[nP] * 100` off that garbage. `CEconomy::Proc` then grinds
on it every tick. It is not fatal — `m_btItemRATE` is clamped to 45..65 and `m_iIsDungeon`
is written but never read — but shop prices in an imported Karkia zone would be driven by
uninitialised memory.

**Fix on import: append a synthetic `LUMP_ECONOMY` copied from a comparable zone of ours.**
It is five ints and it keeps the format uniform. Do not patch `CEconomy` instead — a zeroed
table is not the same as a sane one, and the next stripped-`.ZON` import would hit it again.

---

## 4. What collides, and what does not

This is the part that silently produces a broken import if skipped.

| thing | Karkia wants | our state | action |
|---|---|---|---|
| `LIST_NPC` 2685–2731 (38 monsters) | 2685–2731 | **all free** (our last occupied row is 2265) | **import at native ids** — this keeps the `.aip` summon references correct for free |
| `LIST_NPC` 1047–1190 (9 Church NPCs) | 1047, 1048, 1074, 1076–1080, 1190 | **all occupied** | remap to free ids |
| `LIST_NPC` 4016–4137 (23 NPCs) | beyond our 3,033 rows | — | grow the table, and `LIST_NPC.CHR` in step (it supports holes) |
| `WARP.STB` 170, 172 | Cemetery→Church, Cemetery→SpireVil | **live Oro gates** (`TOWN→ODE01`, `ODRP01→ODE01`) | **must renumber** — copying verbatim silently breaks Muris |
| `WARP.STB` 173, 178–180, 185, 186, 189, 190 | | free | usable as-is |
| `LIST_ZONE_S.STL` key `LZON086` | zone 86 | **used by our zone 82** (Gates of Muris) | renumber. Write names with `scripts/add-zone-name.py` — ours is `ITST01` with 5 language blocks, Jrose is legacy `I_NUM`, and the strings are Japanese anyway |
| `LIST_ZONE` rows 86–144 | | we have 83 | grow to 145. No fixed cap anywhere: both servers size their arrays from `g_TblZONE.row_count` |
| `LIST_SKY` row 17 | zones 87, 88, 131, 135 | we have 13 rows (0–12) | add row 17 plus the two `3Ddata\LUNAR\Sky02\*.dds`. Row 1 (used by 86, 134, 136) is already byte-identical to ours |
| `LIST_CAMERA` | **none of the 9 real zones sets col 21** | 6 rows | nothing to do. The instanced-dungeon rows want cameras 6 and 9; they are out of scope |
| `LIST_EVENT` | 32 `.CON` registrations | 898 free rows, none of these present | copy the 32 rows. Better than Oro, where the *source* had registered none of its 44 |
| weather 5 | zones 87, 88, 131, 135 | `GLOBALSCR.LUA` handles 1 and 2 | harmless no-op; add a Lua branch if we want the effect |
| planet 6 | all 9 | we use 1, 2, 3, 4, 8 | fine. `Check_WarpPayment` treats planet ≥ 4 uniformly, which Oro already exercises, and the loading-screen table is a `multimap` with a default fallback |
| `ZONETYPEINFO.STB` | `.ZON` ZoneType 1 for all 9 | row 1 exists (`LIST_CNST_JD`) | nothing to do. Jrose has no Karkia row either — even their own editor opens Karkia as "mountain" |

Path case is a non-issue: `pack.rs` uppercases on the way in and triggervfs compares with
`stricmp`, so Karkia's mixed-case `3Ddata\KARKIA\...` table references resolve fine.

---

## 5. The gate graph, and the three holes in it

All 11 placed gates, resolved through `WARP.STB` to their destination event position:

```
  86 Church  <--170--  87 Cemetery  --172-->  88 SpireVil  --185-->  135 TowerPlace
 (no exit)                 |  ^                  |  ^                    |
                           |  +------173---------+  +--------186---------+
                           |
                        178|  ^179
                           v  |
                     131 Burned Forest

  134 MemoriesBoss  --180-->  133 Memories  <--190--  144 FlowerGarden
   (one-way out)                    +--------189-------------^

  136 Tower — no gates at all
```

Three consequences, all of them ours to author:

1. **Nothing enters Karkia.** No gate anywhere in the game points at a Karkia zone. Jrose's
   entrance is a quest warp we are not importing. Exactly the shape the Oro import left
   behind, which reached its zones by GM warp until an entrance was decided.
2. **133 / 134 / 144 are a second, disconnected cluster**, and 136 (the Tower) is isolated
   entirely — there is no gate from `KTowerPlace` into the tower it is named after. Those
   transitions were quest warps or instanced-dungeon exits.
3. **The Church is one-way.** Gate 170 goes in; `KChurch`'s `.IFO`s have no `WARP` lump.

Gate 185 is placed twice in the same `.IFO` (`34_33`) — two gate objects on one spot.
Harmless, but do not silently dedupe it and then wonder why the count moved.

---

## 6. Art: the reuse is enormous, and our copies are the better ones

The Karkia `.ZSC`s reference 1,356 assets. **1,351 are present.** The 5 that are not are
`3ddata\3light_*` entries with no file extension sitting in the effect list — editor light
names, not files.

Where they come from is the interesting part: **891 come from `3ddata\junon\`**, 117 from
Eldeon, 32 from Tenku, 30 from Oro, 1 from Skaaj. Karkia is largely re-dressed Junon art.

Hashing the 915 that share a path with us:

| | identical | different | new to us |
|---|---:|---:|---:|
| `.zms` | 547 | **19** | 332 |
| `.dds` | 0 | **331** | 93 |
| `.eft` | 18 | 0 | 11 |

**Every one of the 331 differing `.dds` is the same art with our mip chain added.** Ours are
1.33x (or 2.66x) the size and a header check confirms it: `mips=0` there, `mips=9` here. We
ran `scripts/add-dds-mipmaps.py` over these. **An import must never overwrite our DDS with
Jrose's** — and it should run that script over the 93 genuinely new ones.

The 19 differing `.zms` are mostly the `newtree00*` family (ours are exactly 2x — a
different vertex format), a few `ZMS0007`-vs-`ZMS0008` pairs, and the Oro trees we took from
RoseZA. Keep ours in all 19 cases; the Karkia `.ZSC` will simply render our version of the
same tree.

Character art is the same story and even lighter. Across all 70 monsters and NPCs, only
**33 new meshes, 65 new textures, 4 new skeletons, 34 new motions and 1 new effect** — the
other 227 motions and 40 skeletons we already hold byte-identical.

Terrain tiles are wholly new and wholly self-contained: 208 files, 12.7 MB, under
`3Ddata\TERRAIN\TILES\KARKIA\`, zero collisions.

**Byte budget:** ~63 MB `MAPS\KARKIA` + ~10.5 MB `3Ddata\KARKIA` + 12.7 MB tiles + ~17 MB
new character and map assets ≈ **105 MB**, against a `rose.vfs` currently at 1.99 GB and a
4 GB ceiling. Plus 3 BGM tracks (`KChurch.ogg`, `KField.ogg`, `Boss02.ogg`, ~7 MB) which go
loose into the deployed `Sound\BGM\` — outside `data/` and outside the VFS.

---

## 7. The monsters: import the rows, throw away the numbers

31 spawned monsters at levels 211–250, plus 7 that exist only as AI summons. Level-wise
they slot in above Oro nicely: we currently have 16 monsters at 210–219, 11 at 220–229,
5 at 230–239 and 3 at 240+.

Stat-wise they are from a different game. Medians against our own post-rebalance monsters
at the same level:

| lv 210–219 | ours | Karkia | x |
|---|---:|---:|---:|
| HP (`level * col 8`) | 12,900 | 43,000 | **3.3** |
| ATK | 1,228 | 3,062 | 2.5 |
| **DEF** | **737** | **2,350** | **3.2** |
| RES | 637 | 800 | 1.3 |
| EXP | 1,934 | 256,880 | **133** |

DEF is what kills it. Damage is proportional to `(ATK - DEF + 250)`, and a level-216 Raider
measured in game has ATK 1201. `1201 - 2350 + 250` is negative, so **every swing lands on
the damage floor of 5**. Replaying `Get_BasicDAMAGE` through `scripts/balance-sim.py`
against the real rows:

```
Champion lv215 (ATK 885, HP 3421)
  our median mob lv215  hp    12,318  def   737 | 106 dmg/hit |     144 swings to kill
  karkia 2701    lv213  hp    23,430  def 2,350 |   8 dmg/hit |   4,229 swings | it hits 91% for 1,487 (3 swings kills you)
  karkia 2717    lv216  hp   151,200  def 3,000 |   8 dmg/hit |  21,577 swings | it hits 98% for 2,704 (1 swing)
  karkia 2722    lv221  hp 1,436,500  def 2,300 |   8 dmg/hit | 262,774 swings | it hits 100% for 1,971 (2 swings)
  karkia 2699    lv250  hp 1,689,750  def 3,120 |   0 dmg/hit |  unhittable    | it hits 100% for 5,736 (1 swing)
```

Level 240 barely improves it — the best case is still 1,857 swings for a level-211 trash
mob. Two Karkia monsters are *unhittable* (the level gate discards the swing outright), and
the bosses sit at 1.4–1.7 M HP against our ~87 k Oro bosses.

**So: copy the rows for identity — name, model, size, sounds, AI id, attack type — and
re-derive level, HP, ATK, DEF, RES, HIT, AVOID and EXP from our own curve.** The tooling is
already written and this is exactly what it is for:
`scripts/rebalance-endgame-curve.py --stat def|res` fits the trend from levels 60–199,
`scripts/rebalance-oro-bosses.py` sets boss HP to 10x the HP trend, and
`scripts/rebalance-exp-rewards.py` handles the 133x EXP gap. Mind the order dependency
recorded in `project_monster_balance_passes`.

Three of the nine zones need their population authored from scratch regardless.
**`KBurnedForest`, `KMemories` and `KFlowerGarden` spawn only monster id 1** —
チビゼリービーン, the level-2 Jelly Bean. The regen infrastructure is laid out (23, 10 and 20
points; limits 265, 102, 188) but no real monster was ever assigned to it.

Drop tables and shop tabs do not travel at all — item ids mean different things across dumps
(`project_oro_import_survey`). Karkia references 4 `ITEM_DROP` rows and 14 `LIST_SELL` tabs;
all of that is ours to write.

### Server load is not a concern

`KCemetery` holds 847 concurrent monsters and `KSpireVil` 1,111, authored as one regen point
per monster with `limit=1` and `tactics=1`. That looks alarming next to our usual "46 points,
limit 5–13" style, but it is not new: our own `EZ01` runs **2,118** live monsters in exactly
that one-point-per-monster style. Karkia's 2,513 across five zones sits inside what we
already run.

---

## 8. AI: the best news in the survey

29 `.aip` files, all present, all parsing. Enumerating every opcode they use against every
opcode our 468 existing `.aip` files use:

```
Karkia conditions: 2 3 4 5 7 8 11 12 13 14 15 18 21 28 29
Karkia actions:    1 4 5 6 7 9 12 14 16 17 18 20 25 36 37 38
NEW opcodes Karkia needs:  conditions []   actions []
```

**Zero.** No server work at all.

Worth knowing anyway, because it will matter for Satellite or Skaaj: `g_FuncCOND` has 63
slots and `CAI_EVENT::Check` indexes it with `Type & 0xff` and no bounds check, so a file
using opcode ≥ 63 would call through garbage. Karkia's maximum is 29.

What the `.aip` files *do* carry is cross-references that need remapping — and this is the
one corner the Oro import cut, since it copied `.aip` files verbatim:

- **23 skill ids** (716, 846, 2910–3685) through `AIACT_24` "use skill toward target",
  57 uses. Our `LIST_SKILL` has those rows but they are different skills. Left alone,
  Karkia monsters cast whatever our row 3585 happens to be.
- **10 summon NPC ids** through `AIACT_36`/`AIACT_37`, 38 uses. All of them land in
  2685–2731 — which is **why importing monsters at their native ids matters**. Do that and
  these resolve correctly with no binary patching at all.

Those 7 summon-only monsters (2685–2689, 2705, 2731) are why the monster set is 38 rows and
not 31; two of them are level-250 "Hebarn officers".

---

## 9. NPCs and dialog

32 NPCs: Church 9, Spire Village 5, Memories 10, TowerPlace 5, FlowerGarden 2, plus one
Memories-set NPC standing in the Church. All 32 `.CON` dialogs exist in `3Ddata\EVENT\` and
all 32 are registered in Jrose's `LIST_EVENT.STB` — better than Oro, where none were.

The text is Japanese and lives in `ulngtb_con.ltb` (theirs is 8.2 MB against our 3.9 MB).
Two honest options:

- **Skip NPCs in the first pass.** Nothing else depends on them; the zones work without.
- **Import them with authored English dialog.** The `.CON` Lua bytecode blob cannot be
  regenerated, but our QEX1 appendix (`reference_con_dialog_format`) runs extra Lua source
  in the same `lua_State`, and `src/tools/quest-editor` already writes both halves.

Nine are shopkeepers — 4097 大神官 (4 tabs), 4103 名将の鍛冶師 (4 tabs), 4104
パーレル隊商の商人 (2 tabs), and six with one tab each. Their stock is ours to author either
way.

---

## 10. Suggested staging

Mirror `scripts/import-oro.py` — same stage structure, same idempotence, same `--dry-run` /
`--selftest` discipline. Each stage independently testable and independently revertible.

1. **Terrain, art, zone rows, names.** The 9 `.ZON`/`.IFO` sets with MOB/REGEN/WARP/
   EVENT_OBJECT lumps emptied on the way in, the 16 map `.ZSC`s, the 208 tiles, `LIST_SKY`
   row 17, the synthetic `LUMP_ECONOMY`, `LIST_ZONE` rows and English names. Testable by
   GM-warping in and walking around. **Never overwrite an existing `.dds`.**
2. **Gates.** 10 `WARP.STB` rows at *new* ids (170 and 172 must move) with the `.IFO` warp
   objects repointed, plus whatever entrance and inter-cluster links we decide to author.
3. **Monsters.** 38 `LIST_NPC` rows at native ids 2685–2731, 29 `.aip` files, character
   models/skeletons/motions with the usual index remap, the REGEN lumps — **then a balance
   pass before anyone plays it.** Populate the three placeholder zones.
4. **NPCs.** 32 rows, models, `LIST_EVENT` rows, dialog (authored, not translated).
5. **Drops and shops.** Ours to write. Nothing to copy.

Before any of it, re-read [doc/jrose-survey.md](jrose-survey.md) §2. And remember `data/` is
gitignored — **the import script is the only committed record of what was done**, so the
reasoning belongs in its docstring, not in a commit message.
