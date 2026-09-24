# Game server combat flow and presentation packet rules

> **Provenance:** moved verbatim on 2026-09-24 from `src/sho_gameserver/CLAUDE.md` lines 58-92 (revision `84f6206`).
> Original bytes: [`src--sho_gameserver--CLAUDE.md.txt`](../../archive/2026-09-24/src--sho_gameserver--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=58-92 sha256=ad2973163146ded71e0d41b94d7fad5a948fabd91cda4e053fcb2d4884d84e7d -->
## Combat Flow

Live combat is server-authoritative. The client presents server damage events; it must not calculate live combat damage.

1. Client sends attack/skill packet or monster AI chooses an attack.
2. Server rolls/calculates damage with the shared calculation code compiled server-side.
3. `CObjCHAR::Apply_DAMAGE()` applies authoritative HP immediately and produces the final `uniDAMAGE` result.
4. Server emits FlatBuffer combat presentation data:
   - `CombatSwing` for normal melee/bow/gun attacks that should start a confirmed client swing.
   - `DamageEvent` for skills, projectile impacts, status ticks, counters, missing-attacker fallback, and immediate damage.
5. `DamageEvent.damage_value` is the visible hit delta; `hp_after` is the authoritative checkpoint. Do not rely on `UpdateStats.hp` / `GSV_SET_HPnMP` to present combat HP decreases.

### A Repeat Attack Order Is A No-Op

`CObjAI::can_attack()` answers false for two different things: "may not attack this" (no target, disguised/transparent, no PvP) **and** "already attacking this target". `CObjAI::SetCMD_ATTACK`'s else-branch reads any false as the first kind — clears the target, sets `CMD_STOP` — and `CObjCHAR::SetCMD_ATTACK` then broadcasts `GSV_STOP`. So a second `CLI_ATTACK` on the same monster *cancelled* the attack the first one started: double-click or spam-click a mob while running towards it and the character stopped (alpha report, 2026-09-19). The client's own de-dupe guard (`CSevenHeartUserInput::SetTargetObject_Normal`) cannot cover it, because it tests for `CMD_ATTACK` and the avatar is in `CMD_MOVE` for the whole approach (`Recv_gsv_ATTACK` → `SetCombatAttackIntent` → `SetCMD_MOVE`). `SetCMD_ATTACK` now returns false up front when the order repeats the current `CMD_ATTACK` target: nothing is sent, state and cadence are untouched. `can_attack`'s clause stays — `SetCMD_RUNnATTACK` relies on it to keep mob AI from re-broadcasting every tick. Do not "fix" this client-side by widening the guard to `CMD_MOVE`: the server drops to `CMD_STOP` without a broadcast when a target is lost, so a stale match would swallow a legitimate click. `common/cobjai.cpp` is **CP949** — edit it as bytes, the Edit tool re-encodes every Korean comment.

### PVP Ally Rule (clan fields, party zones)

`ZONE_PVP_STATE` (LIST_ZONE col 18): 0 none, 1 `AllExceptClan` (Junon/Luna Clan Field, Colosseum), 2 `AllExceptParty`, 3 `All`, 11 clan house (safe). In a clan field the zone's entry trigger runs `REWD_020` → `Set_TeamNoFromClanIDX()` (team = `100 + ClanID`), and the **client** decides "enemy" from that team number alone (it has no `Is_ALLIED` override) — so it simply never sends `CLI_ATTACK` / `CLI_TARGET_SKILL` at a clan mate. That was the *only* enforcement: `CObjAVT::Is_ALLIED`'s clan branch tested `GetGUILD()`, an un-overridden stub that always returns NULL (`CGuild` is a bare forward declaration), so server-side a clan mate was an enemy. Invisible for targeted attacks, but an AOE has no client-side target to filter — victims come from a purely spatial sweep (`FindFirstCHAR`) gated only by `Skill_IsPassFilter` → `!Is_ALLIED` — so AOEs hit clan mates (alpha test #2, 2026-09-22). `Is_ALLIED` now compares `GetClanID()` and falls back to the team-number compare, so the server agrees with the client for clanless players and GM team overrides too; `SKILL_TARGET_FILTER_GUILD` uses the clan id as well (it could never pass before), and `CObjAI::can_attack` refuses a user attacking an allied user, so a crafted packet cannot do what the client UI refuses. Do not add a virtual `GetClanID` to `CObjCHAR` for this — vtable change in the widest header; cast to `CObjAVT` after an `IsUSER()` test.

### Combat Presentation Packet Rules

- `DamageEvent` fields: `event_id`, `defender_seq`, `attacker_id`, `defender_id`, `raw_damage`, `damage_value`, `hp_after`, `presentation_kind`, `lethal`, `skill_id`, `source_attacker_id`. The last two (0 = unknown) are **display metadata for the client damage meter only** — neither server combat logic nor client presentation may branch on them; presentation keys on `attacker_id`.
  - `skill_id` flows via `Give_DAMAGE(..., kind, nSkillIDX)` → `Send_combat_damage_event` → `build_damage_event_packet`; `Skill_START` SKILL_TYPE_06 passes `Get_ActiveSKILL()`, the shield counter passes `nShieldSKILL`, status ticks pass the applying skill, all other call sites default to 0. `CombatSwing`'s embedded event always carries 0 (normal attack).
  - `source_attacker_id` = who to *credit* when it differs from `attacker_id`: the DoT caster (status ticks put the victim in `attacker_id`; the poison tick passes `m_iTargetOBJ[ING_POISONED]` — `StatusEffects::m_iTargetOBJ` stores the **speller** for skill-applied statuses, `Skill_ApplyIngSTATUS` passes `pSpeller->Get_INDEX()`) or a summon's owner (`resolve_summon_owner_index`, anonymous namespace `cobjchar.cpp` — same `GetCallerUsrIDX` + `GetCallerHASH` validation as `mirror_lethal_packet_to_summon_owner`; auto-applied in `Send_combat_swing` and, when no explicit source is given, `Send_combat_damage_event`).
- `presentation_kind` controls client timing: `MeleeHitFrame`, `ProjectileImpact`, `Immediate`, `StatusTick`, `MissingAttacker`.
- **Both combat sends broadcast around the *defender*** (`Send_combat_swing` since 2026-09-23; `Send_combat_damage_event` always did). The clients that hold — and can present — a damage event are exactly the defender's 9 sectors; `recv_combat_swing` early-outs without the defender object, so an attacker-centered broadcast adds nothing and *misses* clients in the one-sector differential ring whenever attacker and defender straddle a sector boundary. That miss was permanent for a kill: a damage-killed mob's removal is never broadcast (`CObjMOB::Make_gsv_SUB_OBJECT` returns false at `HP <= 0` — the death packet is the only removal notification a client ever gets), so a client that missed the lethal swing kept a live-looking, unclickable monster forever ("some monsters he sees are actually dead server-side"). Keep any new combat/death send defender-centered, and keep `mirror_lethal_packet_to_summon_owner` beside it for owners outside that neighborhood.
- Normal attacks should send `CombatSwing` after damage is calculated. This guarantees the client queues the event before starting the swing animation that will consume it.
- Projectile-capable damage must use `ProjectileImpact` so the client waits for bullet collision. Immediate presentation is only for true immediate effects such as status ticks, shield counters, and missing-attacker fallback.
- Keep direct HP stat sync as reconciliation only. Combat HP decreases need a `DamageEvent` path so digits, HP, hit feedback, and death presentation stay in one transaction.
- **Lethal events double as summon-gauge sync.** The client decrements its `m_SummonedMobList` (summon gauge) when a lethal `CombatSwing`/`DamageEvent` arrives, so the `lethal` flag must be set on every kill. Because `send_packet_nearby` only covers 9 sectors around the broadcast center, `Send_combat_swing` / `Send_combat_damage_event` also call `mirror_lethal_packet_to_summon_owner` (anonymous namespace, `cobjchar.cpp`): when the dead defender is a summon (`GetCallerUsrIDX` + matching `GetCallerHASH`) and the owner is not `IsNEIGHBOR` of the broadcast center, the same packet is sent to the owner directly — mirroring what legacy `Send_gsv_DAMAGE2Sector` did. Non-combat despawns (owner death/zone change, bonfire distance) emit no combat event at all and still use the synthetic legacy `GSV_DAMAGE` in `CObjSUMMON::Proc`.
- Legacy `GSV_DAMAGE_OF_SKILL` remains in use for several skill types. It must include the defender's post-`Apply_DAMAGE` HP in `m_iHP_AFTER`; the client converts this into `DamageEvent.hp_after` and must not infer the checkpoint from visible HP.
- **Speed fields on the wire are totals, and the client applies them verbatim.** `gsv_AVT_CHAR.m_nPsvAtkSpeed`, `gsv_SPEED_CHANGED.m_nPsvAtkSPEED` and `UpdateStats.attack_speed` are all `total_attack_speed()` — `stats.attack_speed` (weapon + passives, from `update_speed()`) + `Adj_ATK_SPEED()` (buffs + goddess) + server.toml `base_attack_speed` for users. The 2005 "passive only" field names are historical. `Send_gsv_SPEED_CHANGED` is the 9-sector broadcast that keeps observers' copies current (every `classUSER::UpdateAbility`, buff apply/expire via `sync_visible_skill_stats_after_effect` / `Proc_IngSTATUS`, passive learn); `send_update_stats_all` is owner-only. Since 2026-09-19 the client adds nothing on top — it used to add its own buff delta again, so a buffed player's own screen ran faster than the server did.
- **`Set_MOTION` stores `m_fCurAniSPEED` on every attack-motion call**, not only when `Chg_CurMOTION` reports a new pointer. Consecutive swings from a standstill re-issue the same motion, so an attack-speed buff applied mid-fight used to reach the cadence only at the next motion *change* (expiry alone had a retune in `Proc_IngSTATUS`). The client's `Set_MOTION` mirrors this, so both sides pick up a new rate on the next swing.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
