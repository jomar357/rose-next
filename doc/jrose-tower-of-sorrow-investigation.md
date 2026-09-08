# Jrose: Tower of Sorrow (嘆きの塔) investigation

**Date:** 2026-09-08. **Scope:** static investigation; no game code or game data modified, and no Jrose executable executed.

**Reference client:** `C:\Users\Thomas\Desktop\Testclients\Jrose`.
Paths below are relative to this directory unless explicitly prefixed with `src/`, `scripts/`, or `data/`, which refer to Rose Next.

## 1. What we recovered

The Tower of Sorrow is a dedicated, server-controlled instance feature. Its internal name is **Tenku** (天空, “sky/heavens”), its quest file is **CelestialTower**, and its lobby uses **mugen**. Searching only for “sorrow” misses almost everything.

There is enough surviving material to reconstruct the client presentation and a substantial part of the encounter content:

- Lobby **zone 98**, tower **zone 99**, NPC conversations, entrance and ranking interfaces.
- The active client's exact starting-floor choices: **normal 1, 11, 21, …, 151; boss rush 200 or 240**.
- Normal and boss room models, including alternate room variants, and their music.
- **461 tower-associated NPC rows (3510–3970)**, recovered by combining name and AI references, and **263 `TENKU_*.AIP` files** containing monster behavior. The first-pass name-only filter found only 345; see §12.
- A **historical partial boss-checkpoint mapping through 190F**, matched to local NPC IDs, plus recoverable boss-summon actions. These are not a complete final-version wave schedule.
- A tower-specific network protocol for entry, floor setup, starting combat, counting enemies/kills, reporting completion times, and ending a run.
- Quest rewards, entry-item identities, achievement milestones at floors 250 and 260, and links to the related Slayer challenges.

**What was not recovered is the authoritative floor/wave schedule:** which monster IDs appear on each floor, their quantities, placement, release timing, difficulty scaling, and exact loot/entry policies. No complete controller for those rules was found in the loose client data or the client code traced here. Those remain server-side reconstruction work; the NPC catalogue is not itself a wave schedule.

### Evidence labels used in this report

| Label | Meaning |
|---|---|
| **Binary** | Decoded instructions or tables in the supplied `TRose.exe`; describes this client build. |
| **Data** | A parsed local table, conversation, quest, AI, or asset; existence alone does not prove runtime use. |
| **Historical** | A dated publisher announcement; rules may have changed afterward. |
| **Player record** | A surviving community table or dated player observation; potentially incomplete, mistaken, or from an older version. |
| **Inference** | Interpretation supported by the above but not demonstrated end to end. |
| **Unknown** | Not established by this investigation. |

All executable addresses are **preferred virtual addresses**, using image base `0x00400000`, not file offsets or guaranteed live-process addresses. Function names in this report are descriptive labels, not recovered symbols. There was no live server session or packet capture.

## 2. Identity, maps, and lobby

### Zone tables

`3Ddata/STB/LIST_ZONE.STB`, indexed using the game's zero-based data rows:

| Field | Zone 98 | Zone 99 |
|---|---|---|
| Internal name, column 0 | 天空の塔の島 | 天空の塔 |
| Localized name | 未知の火山島 — Unknown Volcanic Island | 嘆きの塔 — Tower of Sorrow |
| STL key | `LZON098` | `LZON099` |
| Zone file, column 1 | `3Ddata/Maps/Junon/mugen/mugen01.zon` | `3Ddata/Maps/Oro/ramesses/dungeon.zon` |
| Zone type, column 20 | 2 | 5 |
| Underground flag, column 4 | 0 | 1 |
| Sector-size field, column 25 | 4000 | 5000 |
| PAT field, column 30 | 0 | 3 |

**Data:** Zone 99 has empty minimap and normal object/building table paths. Its `dungeon.zon` is only **90 bytes**, containing blocks 0 and 1. There are no `.IFO` files directly in that Ramesses directory. The tower interior is constructed by special client code from `TENKU` room assets; importing the zone row alone will not reproduce it.

The other tower named `KTower` in Karkia, zone 136, is a different location. Ramesses room/dungeon resources and the separate Slayer modes also need to be distinguished from normal tower progression.

### Lobby placement is recoverable

The `mugen` directory contains **25 `.IFO` files**. Parsing their NPC, regeneration, and event-object lumps found **11 NPC placements, zero regeneration entries, and zero event-object entries** in those categories.

| NPC ID | Role | IFO | Conversation |
|---|---|---|---|
| 1504 | Kevin, transport | `31_33.IFO` | `EM98-004.CON` |
| **1505** | **Albert, tower reception** | `32_32.IFO` | **`EM98-005.CON`** |
| 1506 | Marvel, supplies/repair/storage | `32_32.IFO` | `EM98-006.CON` |
| **1507** | **Petrov, investigation leader and Slayer access** | `32_32.IFO` | **`EM98-007.CON`** |
| 1508 | Caroline, research/reward exchanges | `32_32.IFO` | `EM98-008.CON` |
| 1509 | Bino, lore | `32_32.IFO` | `EM98-009.CON` |
| **1503** | **Ranking board** | `33_32.IFO` | **`EM98-010.CON`** |
| 1518 | Granada, warp | `33_32.IFO` | `EM98-011.CON` |
| 1510 | Simon | `33_32.IFO` | `EM98-012.CON` |
| 4002 | Kerion, later research quests | `33_32.IFO` | `EM98-013.CON` |
| 1769 | Other placement | `32_32.IFO` | `EMPTY` |

Corresponding `LIST_EVENT.STB` rows include **443 = Albert**, **445 = Petrov**, **441 = ranking board**. These are event-table IDs, not NPC IDs. The IFOs directly name their `.CON` files.

`CELESTIALTOWER.QSD` has a `move-tower` trigger at file offset **`0x187`**, with a type-7 warp reward at **`0x1B5`** targeting **zone 98, x=507400, y=511400** in stored game coordinates. It does not directly enter the instance. The transport Lua in `EM98-001/002.CON` calls this trigger.

## 3. Entry rules: current code versus old dialogue

### The active entry route

**Binary + decoded Lua:** `EM98-005.CON` contains Lua 4 bytecode. Its active function, `AT_Reception_Enter_Open`, is equivalent to:

```lua
function AT_Reception_Enter_Open(hID)
    local iObject = QF_getEventOwner(hID)
    GF_TenkuOpen(iObject)
end
```

The native bridge is identifiable through the `GF_TenkuOpen` string at **`0x716AFC`**, its wrapper at **`0x5086D0`**, and the implementation at **`0x5066F0`**. The implementation checks channel availability through the reception NPC and checks party leadership before opening/requesting entry information. It contains explicit “unavailable on this channel” and “the party leader must speak” messages.

Three actual interfaces survive under `3Ddata/Control/Xml/`:

| XML | Purpose | Useful control IDs |
|---|---|---|
| `DlgTenkuEnter.xml` | Normal/boss-rush entry | 51 normal, 52 boss rush, 100 floor list, 200 member/eligibility list, 12 enter, 11 cancel |
| `DlgTenkuBoard.xml` | Tower ranking | 100 list, 11 button, 10 close |
| `DlgTenkuEnterDragon.xml` | Separate Slayer/rift entry | 200 eligibility list, 12 enter, 11 cancel |

The native button-label initialization at **`0x56D390`** explicitly assigns 通常階 (“normal floors”) and ボスラッシュ (“boss rush”) to controls 51 and 52. The radio selection becomes mode **0 or 1** (`0x56D500`). Modes **2 and above** use the related rift/Slayer branch.

### Exact starting-floor choices in this executable

This is a fixed client list, with server-supplied eligibility/payment information layered on top. The list builder is **`0x56E7E0`**. It reads counts at **`0x71FC88`** and array pointers at **`0x7734C0`**.

| Mode | Count | Array VA | Stored floor values |
|---|---:|---|---|
| Normal, 0 | 16 | `0x71FC8C` | **1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151** |
| Boss rush, 1 | 2 | `0x71FC9C` | **200, 240** |
| Rift branch | 1 | `0x71FC9E` | 1 |

These are **starting choices**, not the maximum reachable floors. They are also not proof that every player can select every choice successfully. The enter button sends the selected floor and mode to the server (`0x56F128` → `0x56C2E0`).

### Eligibility and payment presentation

**Binary:** `0x56F280` renders per-member records received from the server. It has branches for:

- A member being too far away or unavailable locally.
- An invalid character state.
- **Three or more members of the same class.**
- No capacity to accept another quest.
- A member not belonging to the required clan.
- **More than four party members.**
- A valid daily entry.
- The member paying with an entry item.
- The leader paying for the member.
- Missing one required item, or either of two alternative items.

The class/clan/party-size messages are selected from server status fields. Their presence proves support for these restrictions, **not that all of them apply to both normal tower and every Slayer variant**. A four-player limit should therefore not be asserted as a universal rule from this client alone.

The response copies **two 14-byte item descriptors** into the window and uses their decoded names and quantities in the payment text. Consequently the active prices and item alternatives are not fully defined by the old dialogue.

### Old dialogue is unusually misleading here

**Data:** `ULNGTB_CON.LTB` retains text describing one free visit per day, minimum level 15, re-entry talismans, no more than two of the same class, a full quest log, and floor skips. Examples in Japanese-language column **3**:

| LTB row | Meaning |
|---:|---|
| 18915 | One investigation per day; bring a release talisman or return tomorrow. |
| 18917 | Party leader must register. |
| 19027 | A party member already has nine quests. |
| 19046 | At most two people of the same class. |
| 19073 | A true release talisman provides access to F200. |
| 19815 | Select an investigation start in ten-floor increments. |

However, disassembling the embedded Lua shows that **the old `TA_Reception_*`, `TA_CHK_Enter_*`, and `TA_CHK_STAT_*` checks return numeric 0, and the old `AT_Reception_Enter_F*` actions are empty**. The new native-window function is the operative replacement in this file. Numeric 0 is being passed back to the conversation engine; do not interpret this through Lua truthiness alone.

Therefore, keep this dialogue as historical design evidence. Do not implement daily charging, a nine-quest limit, or talisman floor skips solely by copying these obsolete functions.

One additional trap: the QSD trigger `tower_Lv_check`, offset **`0x2BA`**, contains an ability condition **level < 15**, not “level >= 15.” Its comparison byte is **3**, which the shared quest operator implementation maps to `<`. It is a rejection-style check; the name alone is ambiguous.

## 4. What a run looks like

**Data:** Petrov's dialogue, LTB row **18951**, describes being shut into a large room, defeating the creatures inside, and then proceeding into another room above. Caroline's row **18974** describes these transitions as teleportation between spaces. This agrees with the native room replacement code.

**Binary:** A defensible reconstruction of the flow is:

```text
Talk to Albert
  -> native entry window / server eligibility and payment exchange
  -> select normal start or boss-rush start
  -> server accepts entry
  -> server sets floor number and normal/boss room flag
  -> client builds the room and displays a three-second start countdown
  -> server starts combat
  -> server supplies monster-count and kill-count events
  -> server declares completion and supplies the authoritative clear time
  -> room transition / next floor
  -> eventually server ends the run: defeat, timeout, exit, or progression limit
```

The countdown is presentation code, not a client-authorized permission to spawn monsters or advance a floor. The exact server ordering, delays between spawn batches, and handling of late packets have not been observed live.

### Timers and scoring

- **Binary:** The pre-combat display computes a **three-second countdown** in `0x56C443`–`0x56C4FE`.
- The HUD exposes current floor, **kills / total**, lap time, best time, and a new-lap-record message. The relevant strings are at `0x71F8B4`–`0x71F99C`.
- The display's local elapsed time is advanced at `0x56C140`. Completion event **`0x9D`** replaces the lap value with a **server-provided u32 time**. The formatting routines work in milliseconds.
- **For modes >= 2**, the HUD displays a **900,000 ms / 15-minute** remaining-time calculation, using accumulated combat lap times (`0x56C3C7`–`0x56C3F9`). This is evidence for the Slayer/rift branch, **not a recovered 15-minute limit for normal tower**.
- A distinct “seconds until transfer” display uses **15 seconds for modes 0/1** and **60 seconds for modes >= 2**, when state flag `0x20` is set (`0x56C9EF`–`0x56CA38`). These are client display constants. They do not prove a 15-second pause between every ordinary floor.
- Death, timeout, and “cannot climb further” are distinct server events/messages. Disconnect/resume behavior, resurrection allowances, total normal-run limits, and ranking tie-break rules remain unknown.

### Boss cadence and version history

**Historical:** A publisher release dated **2012-03-26** explicitly describes party instances, a boss every **ten floors**, a then-maximum floor **250**, and increased chances of level-210 armor drops on higher floors. This is publisher text reproduced by [4Gamer](https://www.4gamer.net/games/017/G001719/20120326008/), not a claim that every 2012 rule survived unchanged into this dump.

**Data:** This later dump contains `LIST_ACHIEVEMENT.STB` row **52**, “Tower of Sorrow,” for clearing **250F**, and row **57**, “Tower of Episode,” for clearing **260F**. Row **51** records **100 cumulative floor clears**. Thus the content includes the expansion beyond the historical 250-floor milestone.

**Binary:** Room selection uses a server-provided flag, not a recovered `floor % 10` formula. The exact boss-rush floor sequence after starting at 200 or 240 has not been recovered.

## 5. Room art is unusually complete

`3Ddata/TENKU/` contains:

| File | Role | Meshes | Materials | Direct asset references checked |
|---|---|---:|---:|---:|
| `TK_ROOM.ZSC` | Normal room | 23 | 23 | 34 |
| `TK_ROOM_B.ZSC` | Alternate normal room | 19 | 19 | 27 |
| `TK_ROOM_BOSS.ZSC` | Boss room | 23 | 23 | 34 |
| `TK_ROOM_BOSS_B.ZSC` | Alternate boss room | 19 | 19 | 27 |

**Data validation:** All four tables parse, each has ten object slots, and **every direct mesh/material/effect/part-motion reference enumerated by the existing ZSC reader exists in the loose tree**. This was a reference check, not a rendered visual test or recursive validation of every effect dependency.

`TK_ROOM.STB` and `TK_ROOM_BOSS.STB` each have ten data rows, with only row **1** populated. Their final two columns contain **1** and **200**, under headers A and B. The other columns reference authoring `.txt` names such as `mg_tower02.txt`. Those values should not be mistaken for wave counts or a list of 200 floors. The `.txt` files are not present in the loose tree; the compiled ZSC assets are present.

**Binary:** The asset loader near **`0x56F5F0`–`0x56F813`** explicitly loads the two STBs and four ZSCs. Floor setup calls **`0x56D6F0`**, which selects room object **1**, choosing normal or boss assets from the received room flag. The corresponding music is:

- `Sound/BGM/nageki_n.ogg`, string VA **`0x71FAE8`**.
- `Sound/BGM/nageki_boss.ogg`, string VA **`0x71FACC`**.

Both music files exist. The zone's generic Ramesses BGM fields are therefore insufficient to reproduce the observed client branch. The exact purpose and switching behavior of every `_B` room component still needs rendering-oriented analysis.

## 6. Monsters and AI: recovered content, missing encounter schedule

### Tower-specific NPC rows

Selecting `LIST_NPC.STB` column 0 with the literal prefix **`塔 `** yields **345 rows**, spanning IDs **3510–3970** with gaps, and stored levels **2–250**. These reference **198 distinct FILE_AI rows**. This is a reproducible catalogue criterion, not proof that every matching row was used in the final server configuration.

**Second-pass correction:** That filter misses 116 records. Including NPCs whose referenced AI filename starts with `TENKU` recovers **461 consecutive rows, 3510–3970**, referencing **269 distinct AI rows**. This includes the earlier boss block and legacy names that do not decode cleanly as Japanese. Use the revised export in §11; the 345 count describes only the literal-prefix subset.

Examples:

| NPC ID | Internal name / identity | Stored level | AI row |
|---:|---|---:|---:|
| 3510 | 塔 チビゼリービーン — small Jelly Bean | 2 | 660 |
| 3512 | 塔 ゼリービーン — Jelly Bean | 3 | 661 |
| 3540 | 塔 見習いシェフウーピー(16) | 16 | 651 |
| 3660 | 塔 ジュノンゴーレム — Junon Golem | 85 | 732 |
| 3790 | 塔 シククアサシン — Sikuku Assassin | 205 | 785 |
| 3942–3960 | Several explicitly named summoned variants | varies | varies |
| 3961 | 塔 黄金鳥エルドラド | 220 | 518 |
| 3962 | 塔 異端審問官ヘイレン | 250 | 861 |
| 3966 | 塔 カーシアーナ | 250 | 979 |
| 3967 | 塔 シャグラン・アレニエ | 250 | 931 |
| **3968** | **至極の統治者ゼラスト — Zerast** | **225** | **547** |
| 3969 | 塔 オニ・覇 | 250 | 995 |
| **3970** | **煉獄の覇者 アウクシリア — Auxilia** | **220** | **996** |

Names in parentheses, NPC IDs, and stored levels are not floor assignments. The high-floor achievement bosses even have stored levels below 250. Never derive a schedule by equating level and floor.

Rows **125 and 126** of `LIST_ACHIEVEMENT.STB` explicitly link 100 tower kills to **NPC 3970** and **NPC 3968**, respectively. This is stronger evidence of actual tower association than a name prefix alone.

### AI files are readable

There are **263 files beginning `TENKU` with `.AIP` extension**. All parsed to EOF without structural errors, across **4,107 AI events**. The data uses the familiar six-pattern structure, including spawn, idle, attacking, being attacked, and death-related pattern slots.

Observed raw action subtype values range through **`0x26`**. They fit the shared AI opcode vocabulary in `src/common/shared/cai_file.h`; this does not by itself establish complete semantic or balancing compatibility with Rose Next.

Useful examples:

- AI **635** → `3Ddata/AI/tenku_de_zs.aip`: ordinary movement/targeting/combat decisions; no global floor schedule.
- AI **996** → `3Ddata/AI/tenku_auxilia.aip`: boss combat behavior is recoverable. Skill actions reference **3728, 3729, 3730**, with motion IDs **6/8**. Monster variable 0 is initialized/updated around conditional skill phases.
- AI **547** → `3Ddata/AI/slayer_zerustdragon.aip`: exists and is referenced by tower NPC 3968, illustrating that the `TENKU` filename filter is not the complete dependency closure.

**Opcode numbering trap:** raw action subtype **`0x19`** is named **`AIACT_24`** in Rose Next; raw **`0x24`** is **`AIACT_35`**, monster-variable modification. The low numeric subtype and the source macro suffix differ by one. Repeated `0xCD` bytes in padding are not parameters.

The tower AI set also contains summon actions. Reconstructing boss adds is possible by following those records, but their existence does not reveal the instance controller's floor-wide spawn batches. No raw quest-trigger action `0x1F` or regeneration-toggle action `0x22` occurred in the 263-file `TENKU` scan under the shared opcode mapping.

### What the client does not tell us

Still unknown: the complete final-version per-floor roster, simultaneous enemy counts, spawn positions, wave release conditions, scaling by party or floor, exact boss-selection probabilities, upper-floor variants, and the full rewards/drop controller. `ITEM_DROP.STB` and NPC drop fields may contribute, but no complete tower-specific policy was established. In particular, **do not treat NPC column 24 values as a verified tower drop table or literal final HP** without tracing the Jrose stat code.

## 7. Network protocol recovered from the executable

### Generic extension envelope

**Binary:** Sender **`0x522500`** constructs:

```text
offset  size  meaning
0       u16   total packet length = payload_length + 9
2       u16   packet type 0x0829
4       2     existing legacy header bytes; not initialized by this routine
6       u16   extension command
8       N     payload
8+N     u8    0xBE terminator
```

Receive dispatcher **`0x51C250`** checks the last byte for `0xBE`, reads the command at offset 6, and passes payload beginning at offset 8. This describes the in-memory packet construction/consumption before or after any lower-layer framing/encoding; it is not a raw-wire capture.

Two parts of this extension protocol handle the tower:

1. **Command `0x00DC`**, containing entry-window submessages; dispatched at **`0x51D87C`** to **`0x56EDD0`**.
2. **Commands `0x0096`–`0x00A8`**, containing run/HUD events; dispatched at **`0x51E137`** to **`0x56CB40`**.

**Do not confuse `0xDC` with the outer packet ID `0x829`, or with its own payload's submessage byte.**

### Client → server, extension command 0xDC

Payload offsets below are relative to packet offset 8. Only explicitly assigned fields are described; padding/unused bytes are not assumed to be zero.

| Sender VA | Payload length | Submessage at +0 | Other assigned fields / interpretation |
|---|---:|---:|---|
| `0x56C290` | 3 | 1 | +2 u8 mode/category; initial entry-information request, waits for reply |
| `0x56C0A0` | 2 | 3 | Close/cancel entry-information flow |
| `0x56C0D0` | 6 | 5 | +2 u8 category, +3 u8 tab selector, +4 u16 selected floor; refresh eligibility after selection changes |
| `0x56C2E0` | 5 | 6 | +2 u16 selected floor, +4 u8 category; submit entry, waits for reply |
| `0x56C070` | 2 | 7 | Leave-tower confirmation callback |

`0x56C120` separately requests ranking data with extension command **`0x00A3`**, empty payload, and a different final sender argument. The transport-routing significance of that argument was not fully traced.

### Server → client, command 0xDC

`0x56EDD0` dispatches on signed payload byte 0, submessages 1–6:

| Submessage | Handler | Observed action |
|---:|---|---|
| 1 | `0x56EDF4` | Store result byte +1 and release the synchronous wait. |
| 2 | `0x56EE08` | On successful result, populate/open the appropriate entry window. |
| 3 | `0x56EF07` | Close entry windows. |
| 4 | default | No handling in this dispatcher. |
| 5 | `0x56EF31` | Refresh entry information. |
| 6 | `0x56F012` | Completion/result acknowledgment releasing the wait. |

In the type-2 response, +2 is the mode/category; **28 bytes at +6** are copied as the pair of entry-item descriptors. Member records begin at **+0x22**, have **0x29-byte wire stride**, and terminate with a zero leading dword. They are expanded into **0x6C-byte client records**. Do not serialize the expanded UI struct as the wire format.

### Server → client run events

The event table at **`0x56CF04`** establishes the following mapping. Semantic names are reconstructed from their effects:

| Extension command | Handler VA | Observed effect |
|---|---|---|
| `0x96` | `0x56CB6E` | Initialize accepted run state; status at payload +0x12, mode at +0x11; resets counters/timers. |
| `0x97` | default | No action in this handler. |
| **`0x98`** | **`0x56CBFE`** | **Set floor and room:** u16 floor at +0, room flag u8 at +4, optional string at +5; resets lap and rebuilds room. Bytes +2/+3 not interpreted here. |
| **`0x99`** | **`0x56CC80`** | **Start combat:** clear preparing flag, set fighting flag, reset lap clocks. |
| **`0x9A`** | **`0x56CCAD`** | **Increment kill/display-progress counter** at state +0x20. |
| **`0x9B`** | **`0x56CCB8`** | **Increment total-enemy counter** at state +0x1E. |
| `0x9C` | `0x56CCC3` | Store server object ID and corresponding NPC ID for a target-related update. |
| **`0x9D`** | **`0x56CCDD`** | **Floor clear:** accept u32 server lap time, reconcile counters, stop fighting and mark clear. |
| `0x9E` | `0x56CD1B` | Clear transfer flag and perform transition/control/camera operations; exact server meaning not fully assigned. |
| `0x9F` | `0x56CD7B` | Set transfer flag and reset transfer-display timer. |
| **`0xA0`** | **`0x56CD89`** | **Defeat:** clear active state and display “力尽きてしまいました。” |
| **`0xA1`** | **`0x56CDD6`** | **Timeout:** clear active state and display “時間切れです。” |
| `0xA2` | default | No action in this handler. |
| `0xA3` | `0x56CE8A` | Forward ranking data to the ranking-window updater. |
| `0xA4`, `0xA5` | default | No action in this handler. |
| `0xA6` | `0x56CEA5` | Accept/clear a **0x108-byte best-record block**; format its leading time value. |
| `0xA7` | `0x56CBCF` | Enter the control/preparation branch shared with initialization. |
| **`0xA8`** | **`0x56CE23`** | **End/progression limit:** clear active state; conditionally display “cannot climb further” for modes 0/1. |

The HUD at **`0x56C84F`** prints state +0x20 over state +0x1E. This establishes the direction of the two increment events. It does **not** establish whether every summon counts toward completion, whether totals arrive before spawns, or whether the server sends one increment for each individual monster packet.

State object offsets useful for further RE: **+0x1C floor, +0x1E total, +0x20 kills, +0x26 flags, +0x27 room variant, +0x10 elapsed display time, +0x14 lap time, +0x18 accumulated lap time, +0x15C mode**. In the traced avatar, this object is at avatar **+0x2898**.

Observed flag bits: **0x01 active, 0x02 preparing, 0x04 fighting, 0x10 cleared, 0x20 transfer countdown**. Names describe the traced use, not a recovered original enum.

## 8. Quests, rewards, and related modes

`LIST_QUESTDATA.STB` row **42** loads `3Ddata/QuestData/CelestialTower.qsd`. The file parses exactly to EOF: **10 patterns, 108 triggers, 10,579 bytes**. Reward/action types present are **0, 1, 5, 7, 15**. There is **no type-8 monster-spawn reward** in this QSD.

Its contents primarily cover transport, rejection checks, top-floor proof exchanges, equipment exchanges, and Slayer/rift reward exchanges. It is not the missing floor controller.

Key identities:

| Table / ID | Meaning |
|---|---|
| `LIST_QUEST` **1145** | 嘆きの塔 調査隊結成 — investigate the tower and obtain proof of reaching the top |
| `LIST_QUESTITEM` **430** | 魔方陣の欠片 — magic-circle fragment, report to Petrov |
| `LIST_NATURAL` **534** | 契約の書 — Contract Book |
| `LIST_NATURAL` **695** | 解除の霊符 — release talisman |
| `LIST_NATURAL` **699** | 真・解除の霊符 — true release talisman |
| Quest **86** | Bring back five proofs from tower boss rush for the master-class storyline |
| Quest **504** | Gather five catalyst-stone types for the Karkia journey |
| Quest **5414** | Gather five named research materials from floors 250 and above |

**Concrete reward trace:** `get-reward-bookofseal`, trigger offset **`0x396`**, requires quest 1145 and at least one item **13430** (quest item 430). It performs quest operations and grants item **12534** (natural item 534). The reward record is at **`0x3FF`**. The file also contains jewelry exchange branches for IDs **7257–7260, 7267–7270, 7277–7280**. Those are quest exchange rewards, not a recovered boss drop distribution.

Item identifiers above use the familiar type/row encoding for these legacy values. Do not blindly extend that simple arithmetic to every large item value in later Jrose quests.

### Slayer/rift challenges are adjacent, separate content

The “rift between space and time” (**時空の狭間**) uses `GF_TenkuOpenDra`, `DlgTenkuEnterDragon.xml`, and the mode>=2 branches of the shared system. Petrov's Lua invokes that bridge; quests 1146–1149 and later rows include Dragon/Gigant/Vampire/Insect Slayer, EX variants, rookie/clan variants, and Slayer/Fury Rush.

These explain why clan restrictions, four-player messages, named challenge rooms, and a 15-minute clock appear in the same code as the normal tower. They should not all be merged into one set of normal-tower rules.

## 9. Executables, DLLs, and the boundary of this investigation

`TRose.exe` is an ordinary PE32 image with readable x86 code, `.text`, `.rdata`, `.data`, resources, and relocation sections. Its PE timestamp decodes to **2024-11-06 01:09:35 UTC**. The earlier workspace survey calls it “2024-12”; that may describe packaging/file metadata, but it is not this PE header timestamp. Neither date guarantees the date of every asset in the dump.

Tower code was found in **TRose.exe itself**. Inspection of the root DLLs did not identify a tower controller:

- `extr01/02/03.dll` have small code sections, large data sections, and ordinal-only exports. No relevant tower strings were found; `extr02.dll` has an unrelated “MOON-香奈- CD Tenku” string. Their exact roles were not fully reverse engineered.
- Other DLLs include image, XML, and compression libraries and `TriggerInfo.dll`. A negative string search is not proof that an opaque DLL contains no relevant behavior.
- The `.VFS` archives and `data.idx` were not decrypted. Existing workspace context identifies the index as encrypted `IDX2`. Findings about missing files/controllers refer to the readable loose tree and traced executable paths, not a proof about every encrypted archive byte.

No passwords, server credentials, or live service access were needed.

### Reproducible source fingerprints

| File | Bytes | SHA-256 |
|---|---:|---|
| `TRose.exe` | 4,076,544 | `536bb1cdd0f637a77d33e99eb08027876328195cf57a7545c150cf6d80b50041` |
| `3Ddata/STB/LIST_ZONE.STB` | 49,198 | `ab9d3c459a506efb809cfb653ff84c5db19d7bc44250f57bcd1d8c67676322e9` |
| `3Ddata/STB/LIST_NPC.STB` | 812,454 | `19fe9d8291eada6f06121f3479de006131f8b2de7d8ce672e58e54113aa3c018` |
| `3Ddata/QUESTDATA/CELESTIALTOWER.QSD` | 10,579 | `209dd0d14e122e261d1cdd6fac7d06edc891c969191ddb887969d3c371b2e218` |
| `3Ddata/EVENT/EM98-005.CON` | 17,353 | `1119115a2c52f75fc2c979bfb12ba56bd922451543feda5fe14c1221e56697af` |
| `3Ddata/EVENT/ULNGTB_CON.LTB` | 8,183,722 | `8a441d77e3421eb33de4630d1ffd9be0a966740cc75bcb8290ff442789e7d36a` |

## 10. Implications for Rose Next

The checked workspace has **an empty zone-99 row**. Searches of the current client/server/shared source did not find a `Tenku`, `CelestialTower`, or `nageki` implementation. Existing quest, AI, monster, and zone systems offer reusable pieces, but a zone import alone does not supply this feature.

| Area | Reusable evidence/content | Work still required for a faithful implementation |
|---|---|---|
| Lobby | Complete map/NPC/conversation associations | Import/remap assets, dialogues, travel and NPC IDs |
| Interior | Four valid room ZSCs and music | Implement room construction/transitions, collision and placement; verify visually |
| Monsters | Tower NPC definitions and AI files | Dependency closure for skills/models/summons; remap and check semantics |
| Instance controller | Client event flow and state transitions | Party isolation, authoritative timers, spawns, kill accounting, failure/exit and cleanup |
| Floor design | Start choices, historical ten-floor boss cadence, milestones | Recover or author the actual floor/wave schedule |
| Rewards | Quest/item/achievement definitions | Verify loot rules, entry charging, persistence, ranking rules and later variants |
| UI/protocol | Entry/ranking XML and decoded protocol | Implement equivalents for Rose Next; old Jrose wire compatibility is optional |

Relevant current source entry points to inspect when implementation is authorized:

- `src/sho_gameserver/src/gs_threadzone.cpp`, `zonelist.cpp`, `zonefile.cpp`, and `common/cregenarea.cpp`: zones, instance lifecycle and spawn scheduling.
- `src/sho_gameserver/src/gs_user.cpp`: entry validation and party/user state.
- `src/common/shared/io_quest.cpp`, `cai_file.h`, and server `ai_lib/ai_action.cpp`: quest/AI compatibility.
- `src/client/io_terrain.cpp`, `network/recvpacket.cpp`, and interface code: room construction and client presentation.

**Recommended next investigative target:** a Jrose GameServer binary, server configuration/data directory, or a captured successful tower session. Those could establish the missing floor schedule and entry/drop policies. If unavailable, the recovered client contract is enough to design a Rose Next adaptation, but its wave tables and unresolved rules should be explicitly marked as newly authored rather than original Jrose behavior.

## 11. How to reproduce the key checks

Existing workspace readers used:

- `scripts/rose-data-reader.py`: STB1, legacy STL, cp932 names and dynamic string-key columns.
- `scripts/translate-karkia-dialog.py`: conversation nodes and UTF-16LE LTB cells.
- `src/tools/quest-editor/src/convo.rs`: conversation XOR/embedded-script layout.
- `src/tools/quest-editor/src/qsd.rs`: self-sized QSD condition/reward records.
- `scripts/import-oro.py`: IFO and ZSC structure/reference readers.
- `thirdparty/lua-4.0.1/src/lundump.c` and `lopcodes.h`: Lua 4 bytecode layout and instruction decoding.
- Python `pefile` and `capstone`: PE mapping and x86 disassembly. Analysis helpers/output were kept in the system temporary directory; they are not required game changes.

### Export the expanded tower NPC catalogue without changing data

Run the following Python from the repository root. Redirect its output if a CSV is wanted later:

```python
import csv, importlib.util, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(r"C:\Users\Thomas\Desktop\Testclients\Jrose")
spec = importlib.util.spec_from_file_location("rd", "scripts/rose-data-reader.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)
npc = rd.Stb(root / "3Ddata/STB/LIST_NPC.STB", "cp932")
ai = rd.Stb(root / "3Ddata/STB/FILE_AI.STB", "cp932")
names = rd.Stl(root / "3Ddata/STB/LIST_NPC_S.STL", "cp932").by_key()
key_column = npc.key_column()
writer = csv.writer(sys.stdout, lineterminator="\n")
writer.writerow(["id", "localized_name", "internal_name", "model", "stored_level", "ai_id", "ai_file"])
for i in range(npc.rows):
    a = npc.i(i, 16)
    ai_file = ai.s(a, 0) if 0 <= a < ai.rows else ""
    if npc.s(i, 0).startswith("塔 ") or pathlib.PureWindowsPath(ai_file).name.lower().startswith("tenku"):
        localized = names.get(npc.s(i, key_column), ("",))[0]
        writer.writerow([i, localized, npc.s(i, 0), npc.s(i, 1), npc.i(i, 7), a, ai_file])
```

### Verify the starting-floor arrays independently

```python
import pefile, struct
pe = pefile.PE(r"C:\Users\Thomas\Desktop\Testclients\Jrose\TRose.exe")
image = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
counts = image[0x71FC88-base:0x71FC88-base+3]
pointers = struct.unpack_from("<3I", image, 0x7734C0-base)
for count, address in zip(counts, pointers):
    print(hex(address), list(image[address-base:address-base+count]))
```

### Important decoding precautions

Jrose's STB/STL strings generally require **cp932**; STL files here use the legacy `N_NUM/I_NUM/Q_NUM` layout. `ULNGTB_CON.LTB` is **UTF-16LE**, with Japanese in **column 3**. Reading the English/key columns produces plausible-looking but wrong dialogue.

For `.CON` Lua: read the script offset at file byte **520**, then a u32 script length. XOR each script byte with `(length if length is odd else complete_file_size) & 0xff`. The decoded tower scripts begin `1B 4C 75 61 40`, Lua **4.0**, not Lua 5.x. Validate complete consumption when parsing nested prototypes, QSD records, and AI events.

Do not interpret disassembly through an arbitrary unaligned address or through a jump table as executable instructions. The function starts, branch targets, and data addresses above were checked separately. All protocol layouts remain static-analysis results pending live validation.

## 12. Second pass: partial schedule recovery and a larger catalogue

**Follow-up date:** 2026-09-08. This pass investigated the missing schedule specifically. It recovered useful additional evidence, but no authoritative final-version floor controller.

### 12.1 The first NPC filter missed most early bosses

**Data:** Combining the literal `塔 ` prefix with a reference to a `TENKU*.AIP` filename produces exactly **461 consecutive NPC rows, 3510–3970**. Of the 116 additions:

- **31** are earlier monster rows with legacy/mixed-encoding internal labels.
- **85** are rows **3856–3940**, including the main earlier boss block and an Oro Scarab summon target.

Localized names must come from `LIST_NPC_S.STL`, joined through the STB's actual string-key column. For example, NPC **3872** is internally `ピラミットBOSS1` but displays **アビスハウル**; NPC **3935** is internally `エルダンボス１` but displays **カカトゥオイデス**. Searching only internal Japanese names misses these associations.

The 461-row set references **269 distinct FILE_AI rows**. Eight NPCs use files without `TENKU` in their paths: **3519, 3961, 3963–3968**. Consequently even the expanded name/AI catalogue is a starting set for dependency tracing, not a guarantee that all summons and shared skills are included.

The revised CSV-export example in §11 reproduces all 461 rows. **Do not derive floors from their row order.** The continuous allocation is strong evidence of a content block, but it does not encode spawn quantities or encounter boundaries.

### 12.2 Historical checkpoints matched to local IDs

**Player record + inference:** The surviving [Japanese tower wiki](https://wikiwiki.jp/roseonline/Area/Junon/%E6%9C%AA%E7%9F%A5%E3%81%AE%E7%81%AB%E5%B1%B1%E5%B3%B6) records these checkpoints. IDs below are our localized-name matches; ranges are inclusive. They identify reported species, **not counts, spawn order, or simultaneous groups**.

| Historical floor | Candidate local NPC IDs |
|---:|---|
| 10 | 3856 |
| 20 | 3857–3858 |
| 30 | 3859–3860 |
| 40 | 3861–3862 |
| 50 | 3863–3865 |
| 60 | 3866–3868 |
| 70 | 3869–3871 |
| 80 | 3872–3875 |
| 90 | 3876–3879 |
| 100 | 3880, 3883–3884; G-master ambiguous |
| 110 | 3886–3887; G-master and stone-golem ambiguous |
| 120 | 3885, 3890–3892 |
| 130 | 3893–3897, including the later comment's correction |
| 140 | 3898–3902 |
| 150 | 3903–3907 |
| 160 | 3908–3911 |
| 170 | 3912–3915 |
| 180 | 3916–3919 |
| 190 | 3920–3923 |

**Local ambiguity:** IDs **3881** and **3888** have near-identical localized G-master names. The historical stone-golem label does not uniquely establish **3889**. Neither association is resolved by sorting IDs.

The same page reports **random bosses from 200F onward** (2013-05-17), and **Sikuku Assassins on 162F/163F** (2016-12-06); the latter matches local **3790**. These remain dated observations, not final-build guarantees. [Source](https://wikiwiki.jp/roseonline/Area/Junon/%E6%9C%AA%E7%9F%A5%E3%81%AE%E7%81%AB%E5%B1%B1%E5%B3%B6).

### 12.3 Higher-floor evidence supports pools, not a fixed sequence

**Player record:** The separate [Japanese achievement/location page](https://wikiwiki.jp/roseonline/%E7%A7%B0%E5%8F%B7) associates several bosses with broad floor ranges. Matching those names to the local tower variants gives these **partial candidate pools**:

| Reported range | Local IDs matched to named bosses |
|---|---|
| 200–250 | **3928** Mega Drake; **3931** Moss Golem; **3934** Executioner Kera; **3935** Cacatuoides; **3936** Trifasciata |
| 251–260 | **3961** Eldorado; **3962** Inquisitor; **3963** D=Matthias; **3964–3965** Katouka variants; **3966** Khasiana; **3967** Araignee; **3968** Zerast; **3970** Auxilia |

This does not assign one boss to each individual floor, establish selection weights, or prove the pool is exhaustive. **3969**, the Oni variant, is tower-associated in the local data but was not independently placed into a floor range by these records. The local achievements directly naming 3968/3970 remain the stronger evidence of those two NPC IDs' tower use.

### 12.4 Actual boss-add rules survive in AIP records

**Data + shared-schema interpretation:** The 263 `TENKU` AI files contain **63 summon action records**, across **56 events**: raw subtype **0x0B: 2**, **0x25: 13**, **0x26: 48**. These are script records, not a claim that 63 monsters spawn during a run.

Examples of direct parent-to-summon links:

| Parent NPC | AI file | Summoned NPC IDs present in its actions |
|---:|---|---|
| 3859, Formic Leader | `TENKU_JUNON_MELEE1.AIP` | 3947 |
| 3865, Aqua Giant | `TENKU_AAJU-AQUAKINGBOSS.AIP` | 3950 |
| 3869, Guardian Tree | `TENKU_TREE_BOSS.AIP` | 3949 |
| 3873, Junon King Kong | `TENKU_JUNON_GORILLA.AIP` | 3951, 3952 |
| 3878, Krawfy Giant | `TENKU_LOBSTER1_BOSS.AIP` | 3953, 3955 |
| 3890, Giant Worm Dragon | `TENKU_WORMDRAGON3.AIP` | 3882 |
| 3935, Cacatuoides | `TENKU_ELC_BOSS01.AIP` | 3942–3946 |
| 3936, Trifasciata | `TENKU_ELC_BOSS02.AIP` | 3942–3946 |

**Concrete decoded example:** `TENKU_JUNON_MELEE1.AIP`, damaged pattern **3**, event **4**, contains:

| Record file offset | Raw subtype | Decoded fields |
|---|---|---|
| `0x448` | Condition `0x08` | Probability byte **20** |
| `0x454` | Condition `0x1D` | Monster variable **0**, compare **<= 5** |
| `0x46C` | Action `0x26` | Summon NPC **3947**, position selector **0** (self), stored distance **10**, owner flag **1** |
| `0x480` | Action `0x24` | Add **2** to monster variable **0** |

Under the shared implementation, this means a **20% chance check**, gated by the monster variable, followed by creating an owned Formic Sergeant near the boss and increasing that variable. Event **5** repeats the same record pattern at `0x4B8/0x4C4/0x4DC/0x4F0`.

The interpreting source is `src/common/shared/cai_file.h` (`AICOND07`, `Check_AiOP`, `Result_AiOP`) and server `ai_lib/ai_condition.cpp` / `ai_action.cpp` (`F_AICOND_07`, `F_AICOND_28`, `F_AIACT35`, `F_AIACT37`). This interpretation still needs runtime compatibility validation against Jrose. The stored distance is reported without assuming the final coordinate conversion.

Do not turn duplicate events into a fixed two-monster wave: event selection, damage-trigger throttling, other variable changes, and summon lifetime affect actual behavior. This is **boss combat logic**, not the instance's initial population or floor-wide wave scheduler. Some AI actions summon NPCs outside 3510–3970, so importing that contiguous block alone still misses dependencies.

### 12.5 Broader searches and eliminated candidates

**Data:** All **548 loose QSD files** parsed to EOF, with **9,451 triggers** and **332 type-8 spawn records**. None of those records directly names NPC **3510–3970** or destination zone **98/99**. The monster ID is at reward offset **+8** and zone ID at **+20**, under the shared aligned `STR_REWD_008` layout. This rules out a direct tower schedule made of ordinary type-8 rewards in those parsed files; it does not rule out other server operations or indirect scripting.

Trigger names containing `wave` outside CelestialTower lead to **Wilberik/Ulverick wave quests**, not the tower. Their name similarity is not evidence of a shared encounter schedule.

All **172 loose STB files** were parsed and screened for tower/floor terms and numeric values in the recovered NPC range. The most plausible new numeric candidate was **`LIST_EPIC.STB`**: 31 rows, 211 columns, with 457 cells matching that range. Inspection shows named attack/defense modifier families, ability IDs and values, then monster target lists. For example its Dragon Slayer rows use ability IDs **178/179** with values **15/25**. It is evidence for modifier target membership, **not floor placement**. The existing workspace stat survey independently identifies this ability family. Other numeric hits include item IDs, prices, skills and achievements; equal numbers across different tables do not establish NPC references.

The Ramesses `PARTS_LV*.STB` files contain room-part authoring paths, while the two `TENKU` STBs still contain only their single populated room-definition row. No new floor roster was identified in these candidates.

**Archive limit:** A read-only signature/string probe of the five root VFS files and `data.idx` found no literal `TENKU`/`tenku` strings. The first `STB1` hit in `3DDATA.VFS`, file offset **`0x442610BF`**, has an impossible STB header and was rejected as a false positive. No decrypted archive listing was recovered; this probe is not an exhaustive archive-content search.

### 12.6 What is worth pursuing next

The second pass justifies **partial historical reconstruction**: earlier boss checkpoints, some later boss-pool members, and explicit boss-add behavior now have evidence. The remaining gap is specifically the ordinary-floor populations, their counts and positions, wave timing, and final-version pool rules.

The next useful sources would be:

1. **Recorded Jrose runs**, especially floors 1–30 and 190–210, where visible floor numbers, enemy counters, names and spawn batches can test these hypotheses.
2. **A server binary or server-side configuration**, which could recover authoritative spawn templates and selection rules directly.
3. **A decrypted archive index**, to determine whether any additional server-oriented data was accidentally shipped. The present encrypted archives alone do not establish that such data exists.

Further blind filename searching in this loose client tree is now unlikely to recover the whole schedule. Until stronger evidence appears, preserve the checkpoint mapping as historical/inferred and explicitly label any newly authored ordinary-floor waves.
