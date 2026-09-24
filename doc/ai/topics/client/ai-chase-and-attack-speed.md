# Client AI chase movement and attack speed

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 95-116 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=95-116 sha256=f8ae3472978718d76cddf79f0a322d49f1f00e988eafbad5f67f36c410bf6cf0 -->
### AI Chase Movement (CMD_MOVE with target)

`Recv_gsv_ATTACK` routes monster attacks through `CObjCHAR::SetCombatAttackIntent` → `SetCMD_MOVE(target=avatar)`, **not** `SetCMD_ATTACK`. The monster walks toward the player in `CMD_MOVE` state and the actual swing is started later by `CombatSwing` / `StartConfirmedCombatSwing`. This means `CObjAI::ProcCMD_MOVE` runs for chasing monsters, not just for click-to-walk player input.

`CObjAI::ProcCMD_MOVE` has two distinct paths and the dispatch matters for combat sync:

- **USER mover** (`this->IsUSER()`): use `Goto_TARGET(pTarget, AVT_CLICK_EVENT_RANGE | NPC_CLICK_EVENT_RANGE)` — these click-event ranges (1000 / 250 in `datatype.h`) are UX values for "I clicked on someone to talk to them", not combat ranges. They are correct **only** for player-initiated walks. **Exception (2026-09-22): a player walking to a player where both are `is_pvp_enabled()` chases to `Get_AttackRange()` instead.** A PVP attack click comes back as `GSV_ATTACK` → `SetCombatAttackIntent` → `CMD_MOVE` with an avatar target, which landed in this branch and `SetCMD_STOP()`'d the attacker at the 10 m interact ring; it then stood still for the 1-2 s the server needed to close the distance, until the first `CombatSwing` restarted it (alpha test #2: "I click a player, stop on the way for no reason, then resume"). Monsters never showed it because an `OBJ_MOB` target matches neither USER sub-branch and falls through to `Goto_POSITION()`.
- **Non-USER mover (monster, NPC, summon)** with a `pTarget`: use `Goto_TARGET(pTarget, this->Get_AttackRange())` so the chase re-reads `pTarget->m_PosCUR` each tick via `Restart_MOVE` and follows the live player position, halting at the monster's own attack range where the server starts its swing.
- **No target** (server-side move to a position): fall through to `Goto_POSITION()`.

Do not collapse these paths. The historical bug: every mover used `AVT_CLICK_EVENT_RANGE` (1000) and called `SetCMD_STOP()` when crossing that ring, freezing brawlers ~10 m from the player while the server kept advancing them and landing real hits — visible as "monster suddenly stops, then resumes" with client HP > server HP. Sister bug if the non-USER path is changed to `Goto_POSITION()`: the chase walks to a stale snapshot of the player position at packet-arrival time and only re-aims when the next `gsv_ATTACK`/`gsv_MOVE` arrives, producing the kiting-to-first-position visual artefact.

### Attack Speed Presentation

The server owns the swing cadence: its `CObjAI::Start_ATTACK` plays the attack motion at `total_attack_speed() / 100` and applies damage at frame 0 of each loop. The client only *animates* that cadence, at `Get_fAttackSPEED()` read once per `Start_ATTACK`, and nothing on the wire carries a per-swing rate — so whatever this client holds in the attacker's `stats.attack_speed` is what the observer sees. Three independent defects each put a remote player at **exactly 1.00x**, which is why the first multi-player test (2026-09-19) came back as "player A sees B attack at normal speed while B is visibly fast":

- **An avatar's `stats.attack_speed` is the server total, applied verbatim.** `gsv_AVT_CHAR.m_nPsvAtkSpeed`, `gsv_SPEED_CHANGED.m_nPsvAtkSPEED` and `UpdateStats.attack_speed` are all filled from `total_attack_speed()` — weapon + passives + running buffs + goddess + server.toml `base_attack_speed` (35) — and the 2005 "passive only" field names lie. `CObjCHAR::Get_fAttackSPEED` (reached by `CObjAVT`/`CObjUSER` only; mobs, NPCs and carts override) therefore returns `stats.attack_speed / 100`, floored at 0.3, and nothing else. It used to add `m_EndurancePack`'s INC/DEC_ATK_SPD and the goddess term on top, which counted every attack-speed buff twice: a buffed player saw their *own* swings faster than the server ran them, with the surplus hit frames logging `queued presentation miss`. Same rule as `stats.move_speed`, which the client never re-buffs either. `CObjMOB::Get_fAttackSPEED` keeps STB + endurance delta because the server never syncs a monster's speed.
- **Never overwrite a synced speed at creation.** `Recv_gsv_AVT_CHAR` writes the packet value *before* `Add_AvtCHAR` → `CObjAVT::Create`, which used to clobber it with `1500 / (WEAPON_ATTACK_SPEED(BODY_PART_WEAPON_R) + 5)` — a slot index (8) fed to an item-number macro, i.e. `LIST_WEAPON` row 8 "Elven Sword", speed 10 → 100 → 1.0x for every player until a `GSV_SPEED_CHANGED` happened to arrive for them (level-up, equip change, buff). This was the primary cause of the report. `Create` now seeds only while the value is still 0 (the local avatar, created before its first `UpdateStats`), from the weapon actually equipped.
- **`Set_MOTION` re-arms rate and repeat count on every attack-motion call.** `Chg_CurMOTION` returns false when the motion pointer is unchanged, and between a remote attacker's swings the refusal branch of `ProcCMD_ATTACK` calls `Attack_END()`, which resets the animatable to 1.0 *without* replacing the motion (deliberately — see the phantom-swing notes above). A second swing on the same clip therefore replayed at 1.0x whatever `Get_fAttackSPEED()` said: a third of an avatar's swings (`GetANI_Attack` picks one of three clips at random) and every standing second-and-later swing of a monster (one clip). The `else if (bAttackMotion)` branch in `Set_MOTION` fixes it, scoped to attack motions so move/stop playback is untouched. The server's `Set_MOTION` now stores `m_fCurAniSPEED` on every swing too, so an attack-speed buff applied mid-fight changes the cadence on both sides at the *next swing* (it used to wait for the next motion change).

Diagnostics: `CombatTrace attack motion start: obj N rate R synced S repeat K` (Debug) fires once per swing start. Pair it with `combat swing received` for the same attacker: with the rate right, receives and `queued presentation pop` are 1:1. An attacker animated slower than the server swings shows more receives than pops plus `orphaned damage swept` folds for its events — on screen, a 1.0x animation with fewer digits and an HP bar dropping in silent chunks. The dev target window's "Attack speed" line shows `Get_fAttackSPEED()` of the targeted object. Left alone on purpose: the `IsA(OBJ_AVATAR)` branch of the buff-magnitude estimate in `Recv_gsv_EFFECT_OF_SKILL` (it has no `AT_ATK_SPD` case, so a remote avatar's endurance value is a flat-only guess — display-only now), and the dead `GetPsv_ATKSPEED` / `m_nPsvAtkSPEED` scaffolding from the abandoned client-side formula.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
