# Game server AI guard, junk NPC rows, skill damage, status effects

> **Provenance:** moved verbatim on 2026-09-24 from `src/sho_gameserver/CLAUDE.md` lines 93-108 (revision `84f6206`).
> Original bytes: [`src--sho_gameserver--CLAUDE.md.txt`](../../archive/2026-09-24/src--sho_gameserver--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=93-108 sha256=54c751b7c6b4d7c3aee288cac58840a541f4b75d317460fb3963339d7e4b040b -->
### AI Script Guard

Monster AI script action `AIACT24` / `F_AIACT24` blocks hostile `btTarget == 0` condition-checked target skills unless that target is already the monster's current combat target. This prevents non-aggro scripted projectile attacks from sending early target-skill/damage packets. `btTarget == 1` current-target combat skills, `btTarget == 2` self skills, and allied/friendly skills remain allowed. **Since 2026-09-14 the block applies to non-monster casters only** (`Get_ObjTYPE() != OBJ_MOB`): a monster casting a hostile skill at a character its idle pattern found is how caster mobs *aggro* — Nigaki's `kh_2676.aip` has "enemy within 12 m → Voltage Jolt" as its only offensive action besides a 20 % chance to turn on whoever hit it — and blocking it left it a passive heal-bot that never fought back. The cast goes through and `SetCMD_Skill2OBJ` makes that character the current target, so every later cast is a normal combat skill. Logged as `non_aggro_script_skill_aggro`; the blocked case keeps `non_aggro_script_skill_blocked`. Note the server has no auto-aggro on damage: `Apply_DAMAGE` only fires `Do_DamagedAI`, so an AI file that relies on its source server's auto-targeting (a `beaten` pattern at 20 %) fights only as often as its AI says.

### A Junk NPC Row Must Degrade, Not Kill

`CObjMOB::Init` derives max HP as `NPC_LEVEL * NPC_HP` and sizes the per-attacker saved-damage table (`m_SavedDAMAGED`, EXP/drop share) as `NPC_HP / 8 + 4` into a **short**. Three LIST_NPC rows (996 Moss Golem, 997 Nepenthes, 998 Turak — unspawned duplicates, HP column 7.9-13 million where the largest real value is 10,701) overflowed both: a negative max HP and a negative table size that `new[]` read as ~4 billion, so `/mon 996` killed the process with nothing in the log (2026-09-15). `ClampedMobMaxHP` / `ClampedSavedDamageCNT` (64-bit product clamped to `INT_MAX`; table capped at 4096) cover `Init` and `Change_CHAR`. The rows stay as they are — the balance passes leave them alone on purpose — and the Eldeon Moss Golem that actually spawns is **1591**. `/mon` and `/mon2` (`cheatcmd.cpp`, `MobRowRefusalReason`) now refuse such rows with a whisper saying why — no model, level 0, or an HP column over 20,000 — so a tester summoning by number cannot get an invisible or absurd monster. Survey 2026-09-15: of 1,426 named rows, 646 are placed on a map and 111 more are reachable through AI summons; of the 669 unreachable, 212 have junk stats, 183 share a name with a live row, 302 are coherent unused retail/event content. Ids are load-bearing (drop tables, AI, quests, dialogs), so rows are never deleted or renumbered.

### Skill Damage Presentation

`SKILL_TYPE_06` (projectile magic — Icebolt, Lightning, etc.) `Skill_START` must tag the `DamageEvent` with `ProjectileImpact`, not `Immediate`. `CObjCHAR::Give_DAMAGE` takes trailing `Packets::DamagePresentationKind kind = Immediate` and `short nSkillIDX = 0` parameters so the projectile-magic call site can pass `ProjectileImpact` + the active skill while shield-counter / status-tick / cheatcmd call sites keep the defaults (`nSkillIDX` is meter display metadata; see Combat Presentation Packet Rules). `CObjCHAR::IsProjectilePresentedSkill(short)` wraps the shared `Rose::Combat::is_projectile_presented_skill(skill_type, bullet_no)` helper, which the client also uses. The rule is: `05/06` projectile-presented, `03/19` projectile-presented only with a bullet id, and target-bound `09/11/13` never projectile-presented because their `BULLET_NO` is an effect graphic, not a tracked projectile.

### Status Effect Application

`Skill_ApplyIngSTATUS` returns `btSuccessBITS` (a per-slot bitmask) that is set **before** `UpdateIngSTATUS` is called. `UpdateIngSTATUS`'s own return value is consumed only to decide whether the *target's* current command should be cleared (`Del_ActiveSKILL` + `SetCMD_STOP`) — that's used for stun/sleep, which return non-zero specifically for `FLAG_ING_FAINTING | FLAG_ING_SLEEP`. Do not confuse this with packet suppression: `Skill_ChangeIngSTATUS` sends `GSV_EFFECT_OF_SKILL` whenever `btSuccessBITS != 0`, regardless of `UpdateIngSTATUS`'s return. Continuing-target debuffs (e.g. Fire Ring's `ING_DEC_DPOWER`) follow this path and persist for their `SKILL_DURATION`; `Get_DEF()` reads `Adj_DPOWER() = m_nAdjVALUE[ING_INC_DPOWER] - m_nAdjVALUE[ING_DEC_DPOWER] + m_nAruaRES`, so the reduction takes effect on every subsequent damage formula evaluation. Debug traces under `SkillStatusTrace` (apply site) and `defender_def` / `defender_dec_dpower` in the `CombatTrace server combat swing` line let you verify the debuff is being read on each swing.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
