# Buffs and passives are percentage-based

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 684-728 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=684-728 sha256=3e9492e2a28ea0a30d3c247200a5b11797252b04ba0b4ae0b56d2544145f3554 -->
### Buffs And Passives Are Percentage-Based

`LIST_SKILL.STB` carries every ability effect in two columns: a **flat** value
(`SKILL_INCREASE_ABILITY_VALUE`, game col 22/25) and a **percentage**
(`SKILL_CHANGE_ABILITY_RATE`, col 23/26). Our buffs and passives now use the
percentage column — flat values were sized for a level-100 cap and decayed to
irrelevance by level 240 (Power Support's +70 ATK is 19% of a level-100
character and 7% of a level-240 one). Converted by
`scripts/convert-buffs-to-percent.py` (idempotent, sidecar,
`--dry-run`/`--verify`/`--restore`); its docstring is the record of what changed
and what was deliberately left flat.

Things that will bite:

- **A percentage must be taken off the *pre-buff* stat.** `Get_SkillAdjustVALUE`
  calls `Get_BaseAbilityValue`, not `Get_AbilityValue`/`Get_DefaultAbilityValue`.
  The current-value accessors already include the running buff, and
  `StatusEffects::IsEnableApplay` rejects a recast only when it is *weaker*, so a
  percentage off the current value compounds on every recast and settles at
  `rate/(1-rate)` — a declared +30% delivered +43%, +50% delivered +100%, and
  >=100% grew until the `(short)` cast overflowed. Keep the server
  (`CObjAVT::Get_BaseAbilityValue`) and client (`CObjUSER::Get_BaseAbilityValue`)
  lists in sync or the two sides disagree on a buff's magnitude.
- **The two columns follow opposite rules.** Passives are either/or
  (`InitPassiveSkill` / `Skill_LEARN` do `if (RATE) … else FLAT`, so a non-zero
  rate makes the flat value dead data); buffs are additive
  (`Get_SkillAdjustVALUE` sums both terms, so a leftover flat applies *as well*).
  Always zero the flat column when writing a rate.
- **Heals must stay flat.** `Get_SkillAdjustVALUE` resolves `AT_HP`/`AT_MP` to
  *current* HP/MP, so a percentage heal scales with what you have left — useless
  exactly when you need it. `AT_MAX_HP` is the one that means max HP.
- **HIT is deliberately still flat.** Accuracy is a cliff (see the level-gate
  section below), and a percentage hands *less* HIT to the low-CON builds already
  pinned at the 7% floor.
- Passives are re-derived from the table on load (`InitPassiveSkill` rebuilds
  from zero), so a data change needs only a server restart, no migration.
- `Get_BaseAbilityValue` is **virtual on `CObjCHAR`**, the base of every character
  object on both sides. Touching it is a vtable-layout change in a widely
  included header — clean-rebuild `client` and `sho_gameserver`, never
  incremental (see the class-layout warning under Common Pitfalls).

Full measurements and the rest of the balance plan are in
[doc/balance-analysis.md](../../../balance-analysis.md); `scripts/balance-sim.py`
re-derives every number in it against the live STBs.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
