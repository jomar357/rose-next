# CLAUDE.md — Rose Next Game Server (component guide)

Auto-loaded when working under `src/sho_gameserver/`. The root [CLAUDE.md](../../CLAUDE.md) and
[doc/ai/](../../doc/ai/INDEX.md) rules apply first. This compact guide replaced a 207-line version
on 2026-09-24; every line of that version is preserved verbatim in the `doc/ai/topics/gameserver/`
files below ([archive](../../doc/ai/archive/2026-09-24/MANIFEST.md),
[mapping](../../doc/ai/migration/2026-09-24-mapping.md)). The rules here summarise inherited,
unverified notes: read the topic before changing the code it describes.

`sho_gameserver`: real-time gameplay (combat, movement, NPCs, AI, zones, parties, chat). C++,
IOCP (from `common-server`), one thread per zone (`gs_threadzone`), sector broadcasting
(`send_packet_nearby()` = 9 sectors). Handlers `Recv_cli_*` / `Send_gsv_*`. Configured by
`server.toml` in the working directory (see `doc/server.toml.example`); never copy real
connection strings or passwords into docs. Built `MinSpace` (`/O1`) on purpose.

## Combat (server-authoritative)

- `CObjCHAR::Apply_DAMAGE()` applies HP once; the client only presents what the server sends.
  Normal attacks send `CombatSwing` after damage is calculated; skills, projectiles, status ticks
  and fallbacks send `DamageEvent`.
- `hp_after` is the authoritative checkpoint; `damage_value` is the digit. Combat HP decreases need
  a `DamageEvent` path; direct HP stat sync is reconciliation only.
- Projectile-capable damage uses `ProjectileImpact` (e.g. `SKILL_TYPE_06` in `Skill_START`);
  `Immediate` is only for true immediate effects.
- Both combat sends broadcast around the **defender**. Set `lethal` on every kill (it also syncs
  the owner's summon gauge; lethal packets are mirrored to an out-of-range summon owner).
- `skill_id` and `source_attacker_id` are display metadata for the damage meter; no logic may
  branch on them.
- Legacy `GSV_DAMAGE_OF_SKILL` must carry post-`Apply_DAMAGE` HP in `m_iHP_AFTER`.
- Speed fields on the wire are totals applied verbatim by the client.
- A repeat attack order on the current target is a no-op, not a stop.
- Keep client and server in agreement: hit reactions were removed on both sides.

Topics: [combat flow and packet rules](../../doc/ai/topics/gameserver/combat-flow-and-packet-rules.md) ·
[AI guard, junk NPC rows, skill damage, status effects](../../doc/ai/topics/gameserver/ai-guard-npc-rows-skills-status.md) ·
cross-cutting: [project/combat-damage-presentation](../../doc/ai/topics/project/combat-damage-presentation.md),
[project/monster-balance-level-gate](../../doc/ai/topics/project/monster-balance-level-gate.md)

## AI, data rows and movement

- `F_AIACT24` refuses blank/out-of-range skills and gates hostile condition-checked target skills.
- A junk `LIST_NPC` row must degrade, not kill (short overflows in `CObjMOB::Init`); `NPC_NAME` is
  NULL server-side but `""` client-side.
- Player-ordered summon moves use `CObjSUMMON::PlayerOrderMoveTo`, **not** `SetCMD_MOVE2D`, which
  silently rejects non-walkable cells.
- A zone with no `.MOV` would be blocked everywhere (leash/wander/flee dead, chase intact);
  `LoadZONE` opens only cells under loaded tiles. Aggro/leash distances are `.aip` data.

Topics: [summon control](../../doc/ai/topics/gameserver/summon-control.md) ·
[walkability and .MOV](../../doc/ai/topics/gameserver/walkability-mov.md) ·
[overview, configuration, dependencies](../../doc/ai/topics/gameserver/overview.md) ·
cross-cutting: [project/missing-npc-row-degrade](../../doc/ai/topics/project/missing-npc-row-degrade.md),
[project/ai-skill-reference-failures](../../doc/ai/topics/project/ai-skill-reference-failures.md),
[project/monster-spawning-regen](../../doc/ai/topics/project/monster-spawning-regen.md)
