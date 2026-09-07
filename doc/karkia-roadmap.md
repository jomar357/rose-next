# Karkia Import Roadmap

Companion to [doc/karkia-survey.md](karkia-survey.md), which is the evidence. This is the
plan. **Stages 1-3 are built** (`scripts/import-karkia.py`, `scripts/add-karkia-travel.py`);
stages 4-6 are not. Stages 1 and 2a are validated in game.

Two scope decisions are settled going in:

- **No quests.** Karkia's are Japanese, and the RoseZA quest import was the painful half of
  `project_oro_import`.
- **Travel is NPC-driven, not gate-driven.** Karkia has no entrance at all. Rather than
  author warp-gate objects into maps we have never opened, the way in is a dialog option on
  NPCs that already do travel — a solved problem here, see §2.
- **The Memories cluster and the Tower stay unreachable, deliberately.** Jrose gated 133/134/144
  behind a quest about Karkia's past and 136 behind an endgame wave activity. They are content
  we will author our own way into, not holes to patch.

---

## 1. What "done" looks like

Nine zones a level-220-ish player can reach, fight through and leave, with monsters tuned
to our curve, loot worth taking, and no dependency on Jrose's quest chain or its
instanced-dungeon generator.

```
   Jones (Junon Polis) / Nova (Orlean Portal Temple)
                     |  "What of the dead world, Karkia?"
                     v
  86 Church  <--191--  87 CEMETERY  --192-->  88 SpireVil  --185-->  135 TowerPlace
  (arrival)              ^  |   ^               ^  |                     |
                         |  |   +----173--------+  |                     |
                         |  |                      +--------186----------+
                      178|  ^179
                         v  |
                  131 Burned Forest

  134 MemoriesBoss --180--> 133 Memories <--190-- 144 FlowerGarden     136 Tower
       [reached by a quest we have not written]                    [endgame activity]
```

The gates are Jrose's own, restored. The way in is one dialog option on two existing NPCs.
**The Church has no gate back out** — Jrose gave it one in and none back — so leaving is a
Return scroll until stage 6 places its NPCs and one of them hosts the return trip.

---

## 2. The travel design

`scripts/add-karkia-travel.py` writes one QSD trigger, `Karkia-TravelToChurch`, appended to
`QP401.QSD` as a `KarkiaTravel` pattern — the same file and mechanism Oro's travel uses. It
teleports to zone 86 at that zone's own `start` event position, read out of the `.ZON` rather
than pasted (the file stores `x, z, y` and both horizontal coordinates need a half-zone bias;
`add-oro-travel.py`'s `zon_event_positions()` already gets this right).

`quest-editor con-warp` then appends the dialog option to both NPCs that already do travel,
through the QEX1 appendix, so each keeps everything it already offered:

| NPC | where | already offered |
|---|---|---|
| 1104 `[Historian] Jones` | Junon Polis (zone 2) | the trip to Oro |
| 2101 `[Interplanetary Guide] Nova` | Orlean Portal Temple (zone 73) | the trip home, the Oro fate choice |

The Church rather than the Cemetery because it is Karkia's town: no monsters, and ten NPCs
once stage 6 places them. The Cemetery is a 7x7 field of level-211+ monsters.

**Verify a `.CON` edit by decoding, never by grep.** The payload is XOR'd
(`xor_key(len, file_size)`: len when odd, else file size), so a plaintext search reports a
correct file as broken — which it did here on the first check.

---

## 3. Stages

Same shape as `scripts/import-oro.py`: one script, `--stage N`, idempotent, `--dry-run`,
`--selftest` proving every writer round-trips byte-identically before anything is touched.
Each stage is independently testable in game and independently revertible.

`data/` is gitignored, so **the script's docstring is the only committed record** of what was
done and why.

### Stage 1 — terrain, art, zone rows  *(DONE + validated in game, 2026-09-07)*

Built as `scripts/import-karkia.py`. Result: 962 map files (59.96 MB), 208 terrain
tiles (12.12 MB), 16 object tables, 462 art files (13.01 MB), 2 sky textures; 88 `.IFO`
with entity lumps emptied, 9 `.ZON` given a `LUMP_ECONOMY`, `LIST_ZONE` grown to 145
rows, `LIST_ZONE_S.STL` +9 keys, `LIST_SKY` row 17 added. Then
`scripts/add-dds-mipmaps.py` gave mip chains to the 419 new power-of-two textures --
all 419 were files this import created, no pre-existing texture was touched.
`--verify` and a re-run (fully idempotent, 0 of everything) both pass.

In-game test found two defects, both fixed in e22e156e and neither in the map data:
`TEST_ZONE_NO` was 100, a hard ceiling that left zones 131+ with no `CZoneTHREAD`, so
86/87/88 worked and the rest dropped the player on teleport (see
`reference_zone_number_ceiling`); and the asset walker missed the `.zmo` an `.eft` names,
costing 15 motion files. Re-tested: all nine zones load, assets display. What it does:

Copy the 9 `.ZON`/`.IFO` sets with the MOB, REGEN, WARP and EVENT_OBJECT lumps emptied on
the way in (count = 0, lump table untouched) so later stages just refill them. Plus the 16
map `.ZSC`s, `3Ddata\KARKIA\`, the 208 terrain tiles, the new map meshes and textures,
`LIST_SKY` row 17 + the two `LUNAR\Sky02` textures, `LIST_ZONE` rows 86–144 with fresh
`LZON*` STL keys, and English zone names via `scripts/add-zone-name.py`.

Two things this stage must get right:

- **Append a synthetic `LUMP_ECONOMY` to each `.ZON`.** Karkia's are the stripped late-Jrose
  variant with no lump 4, so `CEconomy::Load` never runs and the server's zone economy runs
  on uninitialised heap. Copy the five ints from a comparable zone of ours.
- **Never overwrite an existing `.dds`.** 331 of the shared textures differ only because ours
  have mip chains and Jrose's do not. `copy_new()` never overwrites, which makes that safe by
  construction; the new textures then get chains of their own from
  `scripts/add-dds-mipmaps.py` (419 files, every one written by this import).

Also renumber on the way in: `WARP.STB` 170 and 172 are live Oro gates, and STL key
`LZON086` belongs to our zone 82.

**Acceptance:** GM-warp into each of the nine and walk around. No missing-asset lines in
`error.txt`, no black terrain, minimap draws, zone name shows above it. Run
`scripts/audit-zsc-bounds.py` afterwards — Karkia adds 16 ZSC tables and the cached bounding
boxes in every ZSC in the game are wrong (`doc/zsc-bounding-boxes.md`), so confirm nothing
under-covers badly enough to pop out of the frustum.

### Stage 2 — gates and travel

Split into two pushes, because the halves have very different risk. 2a is data through the
machinery stage 1 already proved; 2b needs a `.CON` built from scratch, which is new Rust.

#### Stage 2a — the internal warp gates  *(DONE, 2026-09-07)*

`--stage 2`. 10 `WARP.STB` rows and 11 gate placements back into the `.IFO` WARP lumps.
**170 and 172 were remapped to 191/192** — they are live Oro gates (`TOWN→ODE01`,
`ODRP01→ODE01`), so copying them verbatim would have silently redirected Muris. That puts
every Karkia gate in one contiguous 173–192 band; our table's last occupied row was 172.

Everything but the id remap and the English names is read from the source at run time — the
destination zone and event name from Jrose's `WARP.STB`, the placements from its `.IFO`s — so
a gate the script does not know about cannot go missing quietly. All 10 destination event
positions were verified to resolve byte-for-byte in the destination `.ZON` **before** anything
was written; a miss there is what produces an `IS_HACKING` disconnect rather than a failed
warp. `--verify` also asserts Oro's 170/172 still point at zone 82.

This makes each cluster walkable: 87 ↔ 88 ↔ 135, 87 ↔ 131, 87 → 86, and 133 ↔ 144, 134 → 133.
There is still no way *into* Karkia — that is 2b.

#### Stage 2b — the way in  *(DONE, 2026-09-07)*

**Scoped down from a per-zone Wayfinder to a single option on two existing NPCs.** The
Memories cluster (133/134/144) and the Tower (136) are not holes to patch: they are content
Jrose gated behind a quest about Karkia's past and an endgame wave/boss activity, and we will
author our own way in later. So no new NPC was needed, and no new Rust either.

`scripts/add-karkia-travel.py` writes one QSD trigger, `Karkia-TravelToChurch`, appended to
`QP401.QSD` as a `KarkiaTravel` pattern — the same file and mechanism Oro's travel uses. It
teleports to **zone 86, the Church**, at that zone's own `start` event position read out of
the `.ZON` rather than pasted. Then `quest-editor con-warp` appends the dialog option to both
existing travel NPCs through the QEX1 appendix:

| NPC | where | already offered |
|---|---|---|
| 1104 `[Historian] Jones` | Junon Polis (zone 2) | the trip to Oro |
| 2101 `[Interplanetary Guide] Nova` | Orlean Portal Temple (zone 73) | the trip home, and the Oro fate choice |

The Church rather than the Cemetery because it is Karkia's town: no monsters, and ten NPCs
once stage 6 places them. The Cemetery is a 7×7 field of level-211+ monsters.

**Known gap: the Church has no way out.** Jrose gave it a gate in (191, from the Cemetery)
and none back, and its NPCs are not placed until stage 6 — so a player who takes the trip is
standing in an empty 2×2 map and leaves by Return scroll. Closing it needs either a second
warp option ("Karkia: the Cemetery") on the same two NPCs, which is ten minutes, or the
Church's own NPCs at stage 6. Deliberately left open rather than decided here.

**Acceptance:** walk every gate in both directions, then teleport to all nine zones and back
out to Junon. No `IS_HACKING` disconnects — that is what a destination event position
resolving to NULL looks like, and it is why the Oro importer verifies every destination
byte-for-byte before writing.

### Stage 3 — monsters, un-tuned  *(DONE, 2026-09-07)*

`--stage 3`. 38 `LIST_NPC` rows at native ids 2685–2731, 37 STL keys (2689 and 2731 share one), 36 AI rows and 34 `.aip` files, 38 `LIST_NPC.CHR` entries with +32 models / +16 meshes / +40 materials in `PART_NPC.ZSC`, 70 art files, 2 character effects, 2 mob-weapon presentation rows, and 2,011 spawn points into 77 `.IFO`s. Idempotent; `--verify` passes.

Names are authored, not copied — Jrose's `LIST_NPC_S.STL` is the legacy `I_NUM` dialect with Japanese text and no language blocks. Cross-checked against the `.aip` filenames where those name the creature (`kak_spider` → Murilo, `kak_neggolem` → Neg Golem).

Two things found by running it:

- **`import_characters` crashed on a sentinel.** Three Karkia monsters carry an anim entry of `(65535, 52685)` — `0xCDCD`, MSVC's uninitialised-heap fill, written out by whatever built these files. **Our own `LIST_NPC.CHR` has 112 of them** across 12,027 entries, so it is tolerated padding, not corruption. Out-of-range pool indices now pass through verbatim instead of being remapped (there is no string to intern) or dropped (which would make imported rows a different shape from the ones we ship).
- **Weapon row 1137 has no bullet effect in either table.** Harmless here: `UsesProjectileAttackPresentation()` is `weapon > 0 && bullet_effect > 0`, so an empty row just selects the melee hit frame — correct for its users, which are melee at 250 cm. The warning now applies the game's own test rather than firing on every empty row.

#### Stage 3b — the monsters' skills  *(DONE, 2026-09-07)*

Folded into `--stage 3` as step 3i. **36 of 36** skill ids the Karkia AI casts now resolve.

§6 said 23 ids with six needing attention. Both numbers were low: that survey walked a
hand-listed set of `.aip` filenames covering only the 31 *spawned* monsters, and the seven
AI-summoned-only ones have AI rows of their own carrying five more skills (3711, 3771,
3779–3781, on the two Hebarn Officers, the Corroded Golem and the Revived Veteran). Deriving
the AI file from each monster's `LIST_NPC` col 16 instead of a filename list is what found
them — and is what the verifier does now.

Final tally: **9 rows ported**, **2 re-pointed**, 25 already correct.

| | |
|---|---|
| ported into their own (blank) rows | 3613, 3616, 3627, 3711, 3771, 3779, 3780, 3781 |
| ported to a different row | 3685 → 3686 (3685 is our "GM Blessing") |
| re-pointed in the `.aip` | 716 → 361 Berserk, 846 → 1090 Tornado |
| assets | `FILE_EFFECT` +2 rows, `QUESTARUA_EXP.EFT` + chain (6 files) |

Two judgement calls. **Berserk** re-points to rank 1 because theirs is rank 1 of its family —
matching the rank position is the least invented choice, and stage 4 can raise it.
**Tornado** re-points to rank 10 instead, matched on *power*: theirs is power 500, and our
Tornado family only runs ranks 6–10, of which rank 10 is power 501. The rank numbering does
not correspond, so matching on it would have been meaningless.

Col 0 is authored rather than copied: theirs is a Japanese editor label and the cp932 bytes
become mojibake in our UTF-8 table. The server reads `SKILL_NAME` from col 0 while the client
shows the STL name, so an ASCII label is both correct and readable.

#### What stage 3 deliberately did not do

38 `LIST_NPC` rows at **native ids 2685–2731** (all free on our side, which makes the AI's
summon references resolve with no binary patching), the 29 `.aip` files, character
models/skeletons/motions with the usual index remap, and the REGEN lumps refilled.

Copy for identity — name, model, size, sounds, attack type, range, AI id. Leave the stat
columns as Jrose wrote them for exactly one play session, so we can see the fights before
we change them, then never again.

Zero AI opcodes here are new to our server, so nothing to implement. The `.aip` files copy
verbatim; six skill references need attention (§6) — three re-point at skills we already own,
three port across with one effect asset. None needs authoring.

**Acceptance:** monsters spawn, animate, path, attack, and die. `/dps` shows damage flowing.
The D=Seed's summon behaviour fires. Nothing crashes.

### Stage 4 — the balance pass  *(DONE, 2026-09-07)*

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

The three placeholder zones stay empty for now (§4, decision 4).

**Acceptance:** re-run `scripts/balance-sim.py` against the written rows and check
swings-per-kill lands in the same band as our own monsters at that level. Then actually play
it.

**Result.** `scripts/rebalance-karkia.py` does levels, HP and ATK; DEF and RES are left to
`rebalance-endgame-curve.py`, which already caps every level-200+ monster at the trend
fitted from levels 60–199 and had simply never seen Karkia (it last ran in August). Measured
with the server's own PVM damage formula against a level-240 character:

| | before | after |
|---|---:|---:|
| swings to kill a trash mob | 3,481 | **67** |
| hits the player survives | 2.8 | **18.6** |
| Neg Golem, the tankiest field elite | 143,650 | **193** |

Two things that were nearly missed:

- **The DEF number in the paragraph above is the one that mattered, and it was the only one
  a new script did not need to touch.** Duplicating that cap in `rebalance-karkia.py` would
  have left two copies to keep in sync; restoring and re-applying the existing pass after
  the levels moved was the whole fix.
- **The boss sidecar is load-bearing.** `rebalance-endgame-curve.py` resolves a boss as
  "listed in a sidecar **or** `NPC_HP >= 1000`", and budgeting boss HP moves Karkia's bosses
  *below* that threshold while its ordinary trash (Neg Golem at 6,500) sits *above* it — the
  heuristic fails in both directions here. It now reads a list of sidecars and Karkia writes
  its own.

Ranking inside a zone is preserved, not flattened: each monster's ratio to its zone median
is square-rooted and capped, so the Neg Golem stays the tankiest thing in the Cemetery at 3x
ordinary trash instead of 41x. Levels are remapped linearly inside each zone so Jrose's own
progression survives. All seven balance passes `--verify` clean.

### Stage 5 — drops  *(wiring DONE 2026-09-07; content pending)*

Split, because the plumbing turned out to be broken in a way the content pass would
have inherited. `scripts/rewire-karkia-drops.py` fixed it and
**[doc/project-drops.md](project-drops.md) is the plan for the rest.**

Two collisions, both from one cause — a drop-table id and a zone id share a single
namespace in `Get_DropITEM`:

- Karkia's own tables (Jrose's 831/832/835/851–854) were live for our Desert
  Scavenger, its Agitated twin, and the **Fearsome Terrasaurus King**. Authoring
  Karkia loot into them would have handed it to Oro. Now 900–906.
- Karkia's **zone fallback** rows (86, 87, 88, 131, 133–136, 144) were live tables
  for thirteen of our own low-level monsters — rows 86 and 87 are named *"EVE Zone
  (Fishing System)"* and *"(Farming System)"*. With drop chance at 20, **~80% of
  Karkia's drops came from those tables**, which is what players were actually
  picking up. Those tables moved to 940–948 with their users repointed; chance is
  now 80, our own level-200+ median.

Karkia now drops **nothing**, deliberately: correct-and-empty is a better base than
plausible-and-wrong, and the content pass is now pure content.

Two things §5 of the drops doc records that change what is possible:

- **A drop cell is `type * 1000 + number`, so item numbers above 999 cannot drop at
  all.** The 73 imported Jrose weapons (1381–1453) are unreachable as loot; the 35
  shields and 43 of the back items are fine. The weapons want a Karkia NPC shop in
  stage 6 rather than an encoding change.
- **Oro has the identical defect** — all 40 of its level-200+ monsters point at empty
  tables and it has been running on its zone fallback since import. The endgame has
  never had an authored loot tier; Karkia only made it visible.

### Stage 6 — NPCs

Split into four, because only the first is mechanical.

#### Stage 6a — place them  *(DONE, 2026-09-07)*

`--stage 6`. 32 `LIST_NPC` rows with English names, 32 STL keys, 32 CHR entries,
42 `PART_NPC` models (+17 meshes, +25 materials), 66 art files, 32 `LIST_EVENT`
registrations, the 32 `.CON` dialogs, and the placements into the `.IFO` **MOB**
lumps — NPCs are a fixed placement carrying an AI row and a `.CON` name, not a
REGEN spawner. Ten in the Church, five in Spire Village, five at the Foot of the
Tower; twelve more wait in Memories and the Garden.

The dialogs came in **verbatim**, which is only safe because **none of the 32 offers
a quest** — checked with `quest-editor con-triggers` across all of them rather than
assumed, so nothing can dangle from the quest chain we deliberately skipped. They
speak Japanese until 6c. One of them (`EM03-001`, the Storagekeeper) calls
`GF_openBank`, so it works today.

Three things worth carrying forward:

- **Compare `.CON` references on the STEM.** The `.IFO` stores the reference *with*
  the extension for the `EM86` family and *without* it for the rest, while
  `LIST_EVENT` always holds a full path. Comparing basenames reported two thirds of
  the set as missing — twice, once against the filesystem and once against the
  table — and both were my error, not the data's.
- **`EVENT_FILENAME` is column 3.** Column 1 is a type marker. Guessing it produced
  a confident "none of these are registered", which was wrong.
- **A CHR entry is addressed by NPC id**, and `import_characters` copies index to
  index, so the nine remapped NPCs landed at their Jrose ids and had to be moved.
  It also *skips occupied slots*, so nothing of ours could be overwritten — and all
  nine were empty regardless, our own 1074 `[Wounded Traveler] Seth` having a
  `LIST_NPC` row but no CHR entry.

#### Stage 6b — the way back out  *(DONE, 2026-09-07)*

The oldest open gap, from §1: Jrose gave the Church a gate in and none back, so
leaving was a Return scroll. `add-karkia-travel.py` now carries **both legs** — each
its own QSD pattern, so either can be added alone and a re-run of either is a no-op
— and the return lands in **Junon Polis**, read from `JPT01.ZON`'s own `start` event
rather than hard-coded. Host is **[Explorer] Petri (4146)**, the Church's own
traveller: the same casting as Jones the Historian and Nova the Guide.

**And 19 NPCs were mute, which was not the Japanese text.** `zonefile.cpp` resolves a
dialog with `_stricmp` on the **full basename** of `EVENT_FILENAME`, extension
included, and Jrose stores the reference *with* `.con` for the `EM86` family and
*without* it for the other 19. Their server tolerated that; ours sets
`nQuestIDX = 0`, so those NPCs had no dialog at all. Stage 6 now rewrites each
placement's reference to exactly what our `LIST_EVENT` row holds — **32 of 32
resolve, up from 13**.

Verify a `.CON` edit by **decoding the QEX1 appendix**, never by grep: the payload is
XOR'd, so a plaintext search reports a correct file as broken.

#### Stage 6c — English dialog  *(DONE, 2026-09-07)*

`scripts/translate-karkia-dialog.py`. **All 20 reachable NPCs, 1,140 nodes, 0
missing.** The 12 in Memories and the Garden are left, since those zones sit
behind a quest we have not written.

Not through QEX1, as this section originally assumed — **dialog text is not in the
`.CON` at all.** A conversation node carries a `str_id` that indexes
`ulngtb_con.ltb`: row = the string id, col 0 a key, cols 1..N the per-language
text as UTF-16LE (`GetEventString(id) = GetMbcsString(lang+1, id)`). So the whole
translation is rows in that table and not one byte of any `.CON`.

Scope was the work. Jrose ships **2,383 translatable strings / 67k Japanese
characters**, mostly branches for quest chains we never imported. Two filters make
it tractable:

- drop nodes gated behind a check function — quest state that can never be true
- **de-duplicate**: "I'll pass" appears 96 times, "Thank you" 55, "Understood" 49

That is 2,383 → **654 distinct strings**, and 147 of them alone covered 54% of all
nodes.

For once an id space was free by luck rather than arrangement: Karkia's ids run
21135–33071 and our table had 20876 rows. Verified after writing that all 20,876
pre-existing rows are byte-identical.

Translations live in `scripts/karkia-dialog-en.json`, committed — `data/` is
gitignored, so authored text kept only there would be lost. An untranslated string
stays Japanese rather than being guessed at.

#### Stage 6e — the six mute NPCs  *(DONE, 2026-09-07)*

`scripts/unlock-karkia-idle-dialog.py`. Six reachable NPCs opened no dialog at
all — Blago, Emil, Ragia, Jenner, Brown, Physalis. Not the Japanese text, and
not a broken import: it is `CEvent::Conversation` doing what it is told.

```cpp
case SC_MSG_NPCSAY:
    Del_ClickITEMS();
    g_itMGR.CloseQueryDlg();
    szMessage = this->ParseMESSAGE(...m_Message.Get());
    if (szMessage == NULL) break;      // no window, AND no recursion
    g_itMGR.OpenQueryDLG(...);
    Conversation(...m_lChildDataIDX);
```

The text is `g_LngTBL.GetEventString(iStrID)`, so **a node with an empty LTB cell
renders nothing and never reaches its child menu.** Every Karkia `.CON` opens on
a `BasicMenu` node that is deliberately empty (its own Japanese reads "normally
blocked off, do not use"), so an NPC is audible only if some *later* root node
both passes its check function and has text. The talkers have an ungated
greeting there; these six had every greeting behind a `TA_*`/`AT_*` check for a
quest chain we never imported, so the root loop skipped all of them.

The fix blanks the 32-byte check-function field on one existing greeting each,
promoting it to that NPC's default line. No node added, no string resized: the
field is a fixed slot in the 80-byte record, so it is a pure in-place edit of
the XOR'd collection. Verified byte-for-byte — file sizes, node trees and Lua
tails all identical, and **every changed byte is a character of the blanked
name** (11 = `TA_Normal01`, 30 = `AT_Kakia_EpisodeQ527_Before_01`).

Which greeting, and why — none of the six has a click function of its own, so
exposing one only ever shows text:

| NPC | line | subtree |
|---|---|---|
| Blago | "……." | 1 node, no clicks — reads as a captain who won't talk to you |
| Emil | "Why in god's name did they post me somewhere this dangerous…" | 1 node, no clicks |
| Ragia | "…It is still too early for you, child." | 1 node; `root[2]` rejected, its option fires `AT_Normal04` |
| Jenner | his first-meeting line, the right default for a player who has done none of his quests | 7 nodes, no clicks |
| Brown | the "lost child" greeting into the lore of the goddess abandoning Karkia | 37 nodes, no clicks |
| Physalis | "Hmm… Is there not a decent ring to be had anywhere…" | 8 nodes; one option fired `AT_Q547_02`, so that *click* field is blanked too |

Brown's `root[3]` was rejected for a second reason worth remembering: **all** of
its options are gated, so the box would have opened with no way to dismiss it.
An exposed greeting needs at least one ungated option under it.

The only two click functions anywhere in the exposed subtrees are
`AT_GotoJunon` (left gated, on a branch we do not expose) and `AT_Q547_02`
(neutered). Nothing un-gates a quest grant or a turn-in.

**Two survived that first pass, and the reason is worth keeping.** Holk and Brown
were still mute. `Conversation` does **not** stop at the first root node that
passes — it runs all of them, and each NPCSAY calls `Del_ClickITEMS()` +
`CloseQueryDlg()` *before* the empty-string test. So the **last** match wins, and
a later node that passes its check but has no LTB text silently closes the window
an earlier one opened.

Their final root node is gated on a **default-state** predicate — `TA_Normal`
(Brown) and `TA_Yuusha_inventoryfull` (Holk) — true precisely *because* no quest
is active, and both have empty text. Every other Karkia NPC's last gate is a
positive quest check (`_Yet`, `_End`, `_Check`, `_Finish`), false for us, which is
why 18 of 20 worked. Note the tempting predictor is wrong: "last root node has
empty text" describes **17 of the 20**, including every working one.

Also note `QST_RESULT_INVALID = 0` but `QST_RESULT_FAILED = 2` and `STOPPED = 3`.
`Conversation` tests `iResult < 1`, so a *missing* trigger is correctly false but
a trigger that exists and **fails** is truthy and shows its node.

The fix for those two moves the good greeting to the **end** of the root offset
table, so it wins whatever the gates do — no Lua evaluation required. Order comes
purely from `pMenuColl->m_SubMenuMMT[j]`, so it permutes four-byte entries and
moves no node body; still no size change. Verified against the pessimistic bound
"assume every gate is true", under which both now speak. Trade-off, deliberate:
if Karkia quests are ever imported, this default overrides their greetings and
the two `PROMOTE` entries should be dropped.

Addressing gotcha: `TARGETS` names nodes by **`str_id`, never item index** —
promotion permutes the table, so an index would name a different node afterwards.
That is how the first `--verify` broke.

Knock-on: `translate-karkia-dialog.py` now reads conversation nodes from **our**
`data/3DDATA/EVENT`, not the Jrose originals. It skips gated nodes, so a node
this script exposes has to be collectable from the files we actually ship or its
line stays Japanese. That added 9 strings (1,131 → 1,140).

#### Stage 6d — shops

Seven `LIST_SELL` tabs need stock written (513, 514, 515, 584, 585, 593, 594). The
other seven Karkia references resolve to **our existing tabs** — the Master Smith
lands on One-hand/Two-hand/Bows, the Parel Caravan on Materials — which is a working
shop for free, as long as nothing authors Karkia stock *into* those rows.

This is also where the imported Jrose weapons go: `doc/project-drops.md` establishes
they can never drop (item numbers above 999 are unaddressable in a drop cell), so a
Karkia shop is their only home short of changing the encoding.

---

## 4. Decisions taken

Settled 2026-09-06.

1. **Karkia is an alternative to late Oro, not a sequel to it.** Same band, different
   flavour, for players who do not enjoy the Wasteland. Level targets in §5.
2. **The raid tier stays a raid.** The Drake → Hebarn Executive escalation is kept, tuned
   down until a coordinated party can take it. Numbers in §5.
3. **No fate-system hook** for now. Karkia reads as Hebarn territory but is open to everyone;
   gating it on the Arua/Hebarn markers can be layered on later.
4. **The three unpopulated zones are deferred.** They ship walkable and quiet; population is
   a later pass.
5. **NPCs are the last step of v1**, after monsters. The way *in* is the exception — it is
   stage 2, because travel is not optional. (The per-zone Wayfinder that stage 2 was first
   planned around was dropped; see §2 and stage 2b.)
6. **Monsters are the priority.** Stages 3 and 4 are what makes Karkia real.

The monsters' skill references, which the survey listed as 23 open items, turned out to be
almost a non-issue once checked properly — see §6. Copy the `.aip` files verbatim; six
references need attention, not twenty-three, and none of the six needs authoring.

---

## 5. Balance targets

Ballpark, derived rather than guessed — but derived from `scripts/balance-sim.py`'s
deliberately pessimistic baseline (no refine grades, gems, passives or buffs, and about 20%
low on ATK against a measured character). **Treat every number as a floor and expect to
tune down after the first real fight.**

### Level bands

Oro measured from its own spawn lumps runs 201–240, with late Oro (Wasteland 1 and 2, Ruins
Path, Gates of Muris) at 208–240. Karkia should overlap that, not sit above it:

| | authored | proposed | pairs with |
|---|---|---|---|
| 87 Cemetery | 211–221 | **215–228** | Wasteland 1 (208–225) |
| 88 Spire Village | 225–231 | **228–238** | Wasteland 2 / Ruins Path (213–232) |
| Deadly Drake 2729 (Cemetery) | 250 | **238** | — |
| Deadly Drake α 2699 (Village) | 250 | **240** | Gates of Muris bosses (240) |
| Hebarn Executives 2685/2686 | 250 | **240** | above anything we have |
| Corroded Golem 2687 | 245 | **238** | — |
| Revived Veteran 2688 | 240 | **235** | — |

This keeps Karkia's own internal progression (Cemetery → Spire Village → bosses) instead of
squashing it, and needs no level-cap change.

### The three stats that matter, and the order they matter in

Reference: our current top boss is the level-240 Fearsome Terrasaurus King —
**87,360 effective HP** (`level x col 8`), ATK 2997, DEF 997, AVOID 504.

- **DEF is a trap, not a difficulty knob.** Measured party DPS against a level-238 boss:
  DEF 1100 costs 6%, DEF 1300 costs 26%, DEF 1500 costs 36%. Beyond that it stops making the
  fight harder and starts making hits *read* as doing nothing — the documented failure mode
  in `doc/balance-analysis.md`, and exactly what Karkia's authored DEF of 2300–3600 does.
  **Cap boss DEF at ~1,250 and trash on the normal curve.**
- **ATK is already at its ceiling.** Our existing boss at ATK 2997 kills a baseline
  level-238 Champion in 4.2 swings (6.5 s) and a Mage in 2.5 (4 s). Karkia's authored
  4,323–5,325 is a one-to-two-swing kill on anything. **Keep raid-boss ATK at 2,600–3,000**
  and put the threat into adds and positioning, which is what "coordinate" can actually
  answer. Raising it past 3,200 just makes the healer's reaction window shorter than the
  server round trip.
- **HP is the honest knob**, because it is the only one that lengthens a fight without
  distorting how it reads.
- Leave **AVOID** at our tier (~500). Raider accuracy is already the weak link — it lands
  6–24% of swings at this level — and raising AVOID punishes one class disproportionately.

### Boss HP budget

Party cap is 7 (`MAX_PARTY_MEMBERS`). At the pessimistic baseline a level-238 player does
~34–46 DPS against a boss in this DEF band; a geared, buffed one plausibly 1.5–2x that.

| | proposed effective HP | `col 8` at that level | sanity check |
|---|---:|---:|---|
| Cemetery zone boss (Drake 2729) | **180,000** ≈ 2x our top boss | 756 @ lv238 | long solo fight; comfortable for 3–4 |
| Raid encounter total (Drake α + 2 Executives) | **~450,000** | — | ~17 min for a geared 5, ~12 for 7; 2+ hours solo, i.e. not soloable |
| — Drake α 2699 | 120,000 | 500 @ lv240 | the opener |
| — each Hebarn Executive | 165,000 | 688 @ lv240 | the payload, x2 |

Against Jrose's authored values that is a uniform ~7–8x reduction (their Drakes are
1.3–1.7 M, their Executives 6.5 M each), which is about the ratio between their players'
output and ours — so the shape of their encounter survives; only the scale changes.

### Spawn density is authored on a different philosophy from ours

Reported from a first visit: *"Spire Village is an absolute hell, there is so many
monsters."* Measured, it is not mainly a count problem — it is a **distribution**
problem, and Karkia's two real zones are laid out unlike anything we ship.

`CRegenPOINT::Load` reads a per-point `m_iLimitCNT`, and `Proc()` only spawns while
`m_iLiveCNT < m_iLimitCNT`, so that field is the concurrent cap. Pairing it with the
spawn positions in the `.IFO` gives the shape of a zone:

| zone | points | monsters | per point | median gap to nearest point |
|---|---:|---:|---:|---:|
| **Karkia Spire Village** | 1111 | 1111 | **1.0** | **5.0 m** |
| **Karkia Cemetery** | 847 | 847 | **1.0** | **7.5 m** |
| Eldeon EZ01 | 2118 | 2118 | 1.0 | 8.9 m |
| Junon JG07 | 81 | 798 | 9.9 | 21.5 m |
| Oro ODE01 | 25 | 241 | 9.6 | 33.5 m |
| Oro ODD01 | 65 | 350 | 5.4 | 45.0 m |
| Lunar LP03 | 61 | 280 | 4.6 | 46.1 m |

Ours are **clumps**: a handful of points, ~5-10 monsters each, 20-45 m of empty
ground between them, so a player picks a clump, clears it, and walks to the next.
Karkia is **a carpet**: one monster per point, points 5 m apart, 10th-percentile gap
2.5 m. There is no quiet ground anywhere in Spire Village — you are never not in
contact range of something. Only EZ01 is authored the same way here, and it is a
low-level zone with harmless monsters.

**Done, 2026-09-07: Spire Village thinned to 25%** (`SPAWN_THINNING` in
`scripts/import-karkia.py`, applied when stage 3 writes the REGEN lump so a re-run
cannot undo it). 1111 points -> 278.

The first version of this analysis used a 60 m radius and concluded Spire Village
was only ~14% busier than Junon JG07. That was wrong, and an in-game screenshot
disproved it: the HUD read **Mob:659** at Pos[515829, 506346] with a 26.8 ms frame
(render 11.5, scnupd 7.0, shadow 4.1 -- all three scale with object count) on a
5060. Matching that reading puts the client's real neighbourhood at **~200 m**, and
at that radius the comparison inverts:

| zone | typical bodies | worst | mesh draws |
|---|---:|---:|---:|
| Spire Village *(before)* | 485 | 736 | 964 |
| **Spire Village *(after)*** | **116** | **174** | **225** |
| Junon JG07 (our densest) | 186 | 286 | 239 |
| Oro Gates of Muris | 160 | 221 | 340 |
| Karkia Cemetery | 98 | 229 | 221 |
| Eldeon EZ01 | 523 | 830 | 1233 |

Not 14% over JG07 — **2.6x the bodies and 4x the mesh draws**, because Karkia's
roster is multi-part humanoids where Junon's low-level field is jelly beans: same
headcount, roughly double the per-frame work. **Measure density at the radius the
client actually loads, and weight it by mesh count.** A monster count alone, or a
radius picked for convenience, gives the wrong answer confidently.

Thinning is spatial, not every-Nth: it removes whichever surviving point is closest
to another survivor, so it eats the tight clusters and leaves the layout's outline.
That shows in the result — the median gap went 5.0 -> 15.8 m but the 10th
percentile went 2.5 -> 12.7 m, a 5x improvement against the median's 3.2x. Uniform
sampling would have kept the worst clumps intact, which is what made the zone a
brawl rather than a field.

The Cemetery is deliberately untouched: 98 typical / 221 draws already sits inside
what our own zones run.

**Eldeon EZ01 is worse than Spire Village ever was** (523 typical, 1233 draws) and
is ours, not an import. Its monsters are low level and simple, so it may not bite
the same way, but it is worth a look on its own.

### The summon chain needs its own pass

Karkia's monsters summon adds constantly, and two of those summons are boss-tier:

| summoner | summons | authored HP | proposed |
|---|---|---:|---|
| `ks_2699` Drake α | 2685 + 2686 Hebarn Executives | 6,500,000 each | 165,000 each — **this is the raid, keep it** |
| `ks_2692`, `ks_2697`, `ks_2698` *(trash)* | 2687 Corroded Golem | 2,793,000 | **~60,000** — an elite add, well below zone-boss tier |
| `ks_2692`, `ks_2697`, `ks_2698` *(trash)* | 2688 Revived Veteran | 672,000 | **~45,000** |
| `kak_summonseed` D=Seed | 2705 D-Pollinosis x6 | 10,850 | scale with the tier |
| most Cemetery mobs | 2731 / 2689 Ghost Seed | 14–16 k, ATK 1 | scale with the tier |

Trash summoning a boss is not something coordination can answer, so 2687 and 2688 come down
hard. 2704 D=Seed is a stationary spawner (ATK 10 — it never attacks) at 215,000 authored
HP; bring it to ~40,000 so clearing it is a real objective rather than an endurance test.

**This table is incomplete — read §7 before tuning any of it.** Decoding the AI found a
second link it does not show: the Corroded Golem has a 15% chance *each* of summoning both
Hebarn Executives when it dies, so the chain runs trash → Golem → 6.5 M HP raid boss with
no boss kill in it. And none of these summons can despawn on our server.

EXP is 133x ours across the board; `scripts/rebalance-exp-rewards.py` owns that.

---

## 6. The monsters' skill references

The survey flagged 23 skill ids the Karkia AI casts through `AIACT_24` and warned they might
mean different things here. Checked properly — every one of our 87 columns, both sides — the
picture is far better than that:

| | rows | what happens if we copy the `.aip` verbatim |
|---|---|---|
| **identical on both sides** | 12 — 3548, 3549, 3557, 3572, 3574, 3575, 3579, 3580, 3582, 3585, 3586, 3599 | works exactly as authored |
| **same skill, different numbers** | 5 — 2910, 2911, 2913, 2941, 2954 | right effect, our duration and magnitude (mostly *stronger*: 2941 is rate 15 / 35 s here against rate 7 / 15 s there). 2910/2911/2913 have no casting or action motion on our side, so the effect lands with no animation |
| **blank on our side** | 4 — 716, 3613, 3616, 3627 | the monster spends an AI action doing nothing. `CObjAI::SetCMD_Skill2OBJ` does not validate the row, so an empty skill executes as an empty skill — no crash |
| **genuinely different** | 2 — 846, 3685 | see below |

**Settled as of stage 3b: all of them work.** Re-walked from `LIST_NPC` col 16 across
all 38 monsters (the 23 above came from a hand-listed set of `.aip` filenames that
covered only the spawned ones), the AI casts **36** distinct skills and **zero** of them
are dead on our server. The four "blank" rows were filled by the port; the five the
bosses cast that this table never saw — 2914, 3594, 3596, 3597, 3598 — turn out to be
present and **cell-for-cell identical to Jrose** across all 50 mechanical columns.

Careful with that check: those five have an **empty name in column 0** and a fully
populated row behind it. Column 0 is an editor label the server never reads, so testing
it reports a working skill as blank — which is exactly the false alarm this note exists
to stop. Test `SKILL_TYPE` (col 5) and the mechanical columns, never the name.

Those two are the only real losses, and neither is harmful:

- **846** is トルネード (Tornado) there — type 17, radius 700, power 500 — and **Spell Mastery**
  here, a type-15 passive. The AI casts it *at its attack target*, so instead of a 500-power
  AoE the monster fires a passive at the player: a no-op, or at worst a trivial gift.
- **3685** is a radius-1500 self-buff there and **GM Blessing** here — which despite the name
  is an empty row (no type, no ability pairs). The AI casts it *on itself*, so nothing
  happens.

So the blast radius is **10 of the 38 monsters**, and they pair up because the α set shares
its AI with the Cemetery original:

| monsters | affected rows | what they lose |
|---|---|---|
| 2703 / 2692 Revived Quarantine Member | 716 (self), 846 (target) | its self-Berserk and its Tornado — the biggest loss |
| 2716 / 2697 Evil Eye | 3685 (self), 3627 (target) | a self-buff and a silence |
| 2715 / 2696 Murillo | 3613 (target) | a 5 s stun |
| 2725 Evil Fairy | 3616 (target) | a 100-power nuke |
| 2714 / 2695 Deadly Wolf | 2941, 2954 | nothing — magnitude only |
| 2719 Woodnoid | 2910, 2911, 2913 | nothing — magnitude, plus no cast animation |

### None of the six needs authoring

Three of them we **already have**, because they are *player* skills the AI borrows —
`LIST_SKILL` col 35 (Job) and the parent-skill and weapon columns give them away:

| row | Jrose | ours | action |
|---|---|---|---|
| 716 | バーサク, a Champion 2H/spear/axe self-buff (job 62, parent 711, level 120) | **Berserk**, rows 361–380 | re-point the `.aip`. Import nothing |
| 846 | トルネード, a Mage staff nuke (job 42, parent 841, level 70) | **Tornado**, rows 1086–1090 | re-point |
| 3627 | `kleitos_沈黙`, a silence | **Silence**, rows 1071–1075 | re-point, or port theirs if the numbers differ enough to matter |

Two caveats on those three. Our copies are *ranked families* (Berserk has 20 ranks), so pick
a rank suited to a level-215+ monster rather than defaulting to rank 1. And the job/weapon/
parent-skill columns are learning gates, not casting gates — a monster ignores them — but
that is worth confirming in game rather than asserting.

The other three are genuine monster skills, and they **port by straight copy**, because the
support tables are index-aligned and Jrose only ever appended to them:

| table | rows we both have | identical path | **rows only they have** | rows only we have | different |
|---|---:|---:|---:|---:|---:|
| `FILE_EFFECT` | 3162 | 496 | 484 | **0** | 26 |
| `FILE_SOUND` | 2001 | 1283 | 75 | **0** | 1 |
| `TYPE_MOTION` | 621 | 163 | 296 | **0** | 4 |
| `FILE_MOTION` | 1271 | 350 | 284 | 21 | 0 |

"0 rows only we have" is the property that matters: wherever we have a row, they have the
same row, so a ported skill's effect / sound / motion index either resolves to the identical
file here or lands on a row we left blank — never on a *different* asset. (`FILE_MOTION` is
the exception with 21 rows of ours they lack, and 26 `FILE_EFFECT` rows genuinely differ;
none of the six skills touches any of them, but a broader skill import should check.)

Checked index by index for the three:

| row | what it is | ports cleanly? |
|---|---|---|
| 3613 | `蟻スタン（5秒）` — type 17 AoE, radius 3000, power 400, 5 s stun | **yes.** Motions 8/9, effect 1611 `_s_spin_attack02.eft`, sound 131 all resolve to the same files here |
| 3685 | type 8 self-buff, radius 1500, status effects 20 + 22, 50 s | **yes.** `LIST_STATUS` 20 and 22 are identical in every numeric column — the only difference is that they kept the Korean name and we translated it to "Def Increased" / "Magic Resistance Increased" |
| 3616 | `questarua` — type 7, radius 3000, power 100 | **yes, plus one asset.** Its impact effect is `FILE_EFFECT` 1460 `questarua_exp.eft`, which is blank here; the file exists in the Jrose tree (`3Ddata\EFFECT\QUESTARUA_EXP.EFT` and its `EFFECTMESH\QUESTARUA_EXP` folder), so write the row and copy the assets |

**Plan: copy the `.aip` files verbatim, re-point three `nSkill` fields at skills we already
own, and port three rows plus one effect.** Copying cols 0–85 is safe — the layouts align by
meaning across that whole range. **Col 86 does not**: ours is the STL key, theirs is
`AVAILABLE_STATUS`, which is exactly the trap `doc/jrose-survey.md` §2.2 warns about. Leave
our col 86 alone.

Worth doing rather than deferring: the Cemetery roster's identity is partly its casting, and
a silence plus a stun is most of what makes the Evil Eye and Murillo interesting.

---

## 7. The bosses, decoded

Vouched for from the data rather than in game, since summon-only bosses are awkward to
reach. Everything below was read out of the `.aip` bytes against
`src/sho_gameserver/src/ai_lib/` — the **structs** in `cai_file.h`, not the comments
above the functions, which name fields the code does not use (`AICOND27`'s comment says
`cChrType`; the code reads `btIsAllied`, and the two `short`s after it are 2-byte
aligned, so a naive offset reads the padding and prints nonsense level ranges).

Dispatch is `g_FuncCOND[Type & 0xff]` / `g_FuncACTION[Type & 0xff]` on tables that start
at index 1, so a file's `Type` *t* is `F_AICOND_(t-1)` / `F_AIACT(t-1)`.

**Max HP is `level × col 8`** (`m_iOriMaxHP = NPC_LEVEL * NPC_HP`), which is why the
table below reads 26,000 where §5 quotes 6,500,000.

| | level | col 8 | effective HP | ATK | DEF | RES |
|---|---:|---:|---:|---:|---:|---:|
| 2699 Deadly Drake α | 250 | 6,759 | 1,689,750 | 4,526 | 1,281 | 3,120 |
| 2685 Pazugenti | 250 | 26,000 | 6,500,000 | 4,323 | 1,250 | 2,600 |
| 2686 Scylla Mira | 250 | 26,000 | 6,500,000 | 4,323 | 1,250 | 2,600 |
| 2687 Corroded Golem | 245 | 11,400 | 2,793,000 | 3,380 | 600 | 1,500 |
| 2688 Revived Veteran | 240 | 2,800 | 672,000 | 2,980 | 600 | 1,500 |

### What they actually do

A hit only runs the damaged pattern some of the time — 40% for the Drake α and the
Golem, 30% for the rest — and *then* each event rolls its own chance, so the rates below
compound. The officers hold an AI variable that acts as a cooldown counter: casting adds
to it, an idle event decays it, and the cast is gated on it staying under a ceiling.

- **2685 Pazugenti** — 40% Ferdinand Stun (AoE r4000, 200 power, 4 s) on the target,
  above 5% HP; 30% self-buffs 3596 when the target has a buff up, 30% self-buffs 3597
  when the target has no debuff. Flees home if dragged 80 from spawn. On death, at
  night only, five Ghost Seeds.
- **2686 Scylla Mira** — identical, with Duke Vlad Counter (AoE r5000, power 10) in
  place of the stun.
- **2687 Corroded Golem** — the busiest. Idle: 25% KS Defence Down (AoE r1800, 300, 60 s)
  when two or more players are within 17. Damaged: 5% self-buff 2912, 20% self-buff 2914
  after a hit ≥ 100 damage, 20% Defence Down, 10% KS Stun (AoE r1500, 250, 5 s), and
  below 30% HP a 10% chance to summon a Revived Veteran. Below 40% HP it calls a nearby
  idle ally onto its target 60% of the time.
- **2688 Revived Veteran** — 50% KS Poison (single target, 350, 30 s) on a target with
  no debuff, twice over; 30% self-buff 3598; the same two officer self-buffs.
- **2699 Deadly Drake α** — no skills at all. It is a stat check and a summoner.

**Tornado is switched off (2026-09-07).** Skill 1090 on the Revived Quarantine
Officer (2703) and its Alpha (2692) was reported in game as damage with no visible
cast, and a run of "blank hits" ending in a death. That is not bad luck:
`kak_livingdead.aip` carries a damaged-rate of **100%**, so 2703 rolled it on 10% of
every hit it took. Filling in its missing animation pair fixed the *monster's*
animation, not the skill's presentation. It is disabled by zeroing the percentage on
the `AICOND_07` gating its event — the same way the source data disables its own
dead events — via `AIP_DISABLE_SKILLS` in the importer, so a re-run cannot restore
it. One byte to put back.

Worth noting what makes it the odd one out: 1090 is one of only **two re-pointed
skills**, meaning one of *our player* skills handed to a monster rather than a row
ported from Jrose. Its sibling 361 Berserk is a self-buff and presents its own
effect, so it looks fine. 3613 Karkia Stun was also never seen in game and is
deliberately **left enabled** — 35% damaged-rate × a 10% roll × "target has no
harmful status" is ~3.5% of hits taken, which explains it without a defect, and its
motion pair is verified present.

Motion is clean: 76 of the 80 `AIACT_24` records already resolved to a complete
casting/skill anim pair, and the four that did not were the Revived Quarantine Officer,
fixed in `a86dbbff`. Every boss animates.

### Two things worth knowing before tuning them

**The despawn rule was dead, so summoned bosses were permanent — now fixed.** All four
carry the same idle event: *if `<condition 31>` and no player within 40 → kill itself*
(`F_AIACT23` is `Add_DAMAGE(HP + 1)`). We had no `F_AICOND_30`; the id fell on
`F_AICOND_NULL`, which returns **false** on the server (the client's returns *true* —
they disagree), so the event never ran and the boss never cleaned itself up. The only
other lifetime path did not apply either: `CObjCHAR::Create_PET` attaches
`FLAG_ING_DEC_LIFE_TIME` **only if the summoner already had it**, which a field-spawned
trash mob does not — and our `status_effects.cpp` no longer drains on that flag anyway.

This was **not** an import defect and not Karkia-specific — our own 466 `.aip` files use
condition 31 twenty-nine times, so it had always been dead here. Karkia is just the first
content that summons enough for it to show.

Condition 31 is now implemented as `F_AICOND_30`, "has been alive at least N seconds".
Nothing documented it — the meaning was reconstructed from how the data uses it. 33 of
its 35 uses gate suicide from the idle pattern, and the value follows the rank ladder of
three independent summon families:

| | rank 1 | rank 2 | rank 3 |
|---|---:|---:|---:|
| `manaflame` | 60 s | 90 s | 120 s |
| `murthflame` | 60 s | 90 s | 120 s |
| `sur_fire` (BoneFire) | 60 s | 90 s | 120 s |

which is what identifies it as a lifetime in seconds rather than a distance or a count.
Karkia's `-1200` is a disabled timer — always true — leaving the bosses' rule as pure
"no player within 40 → despawn".

Two things about the implementation:

- **Player summons are deliberately exempt.** They run the same idle pattern, so a
  faithful implementation would have started expiring BoneFire at 60–120 s and
  Elemental/Wolf at 300 s — a change to existing gameplay nobody asked for, and one
  those skills no longer expect since we removed the summon HP-drain. A player's summon
  is bounded by the summon gauge; a monster's summon is bounded by nothing, which is the
  accumulation this condition exists to stop. `CObjSUMMON` overrides `GetCallerObjIDX()`
  to return the owning *user*, so its `Get_CALLER()` resolves to an avatar while a
  monster-summoned pet resolves to a mob or to NULL — that is the discriminator.
- **No field monster is affected.** Every one of the 40-odd rows carrying a suicide
  timer is summon-only; none appears in any map REGEN lump. Checked before shipping,
  because a field monster on a 60 s timer would vanish and respawn forever.

**The summon chain is worse than §5 recorded.** §5 has trash summoning the Golem. It
does not have what the Golem does on *its* death:

| on death | chance | summons |
|---|---:|---|
| 2687 Corroded Golem | **15% each** | 2685 Pazugenti **and** 2686 Scylla Mira |
| 2688 Revived Veteran | 1% each | the same two |
| 2699 Deadly Drake α | 4% each | the same two |

So the live chain is *trash → Corroded Golem → 15% → a level-250, 6.5 M HP raid boss
that cannot despawn*, with no boss kill anywhere in it. That is the strongest argument
yet for §5's "bring 2687 and 2688 down hard", and it wants a decision on the officer
summons themselves — drop the rate, gate them behind the Drake α, or cut them from the
trash-fed rows.

**Some events are dead in Jrose too.** Several are gated on a `0%` roll
(`Get_RANDOM(100) < 0` is never true): both officers' low-HP self-heal 3594 and their
"call for help". That is their authoring, not our import — leave it or author over it,
but do not go looking for a bug.

---

## 8. Still open

Small, and none of them blocks starting.

- **Where the entrance NPC stands.** Proposal: **Muris**, since Karkia is an Oro-tier
  alternative and Muris is where a player stands when choosing what to do next — which makes
  reaching Oro a light, natural gate. Junon Polis instead would make Karkia bypass Oro
  entirely. Return leg goes back to Muris either way, free, like Oro's.
- **A level requirement on the warp**, or none. Oro deliberately has none — the real gate
  there is the monsters. Same logic probably applies.
- **Whether the α set gets re-themed.** 10 of Karkia's 31 monsters are the Cemetery roster
  again at higher level with an α suffix. Shipping them as-is is honest ("the same horrors,
  worse") and free; re-theming is real work. Decide when Spire Village is first playable.

---

## 9. Effort shape

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

No server or client code change is required by anything above. The six skill references in §6 are
data too, so that stays true.

## 10. Before the first line of code

- Re-read [doc/jrose-survey.md](jrose-survey.md) §2 — all three silent-failure traps apply.
- Re-read §5 — the balance targets are a floor from a pessimistic model, not a spec.
- `rose.vfs` is 1.99 GB and Karkia adds ~105 MB, so no rollover concern
  (`reference_vfs_offset_limit`), but bake with `scripts/pack.ps1` so the archive self-verifies.
- Servers cache STBs at startup — restart them after every stage, and rebake + redeploy the
  client for anything that touches `data/`.
