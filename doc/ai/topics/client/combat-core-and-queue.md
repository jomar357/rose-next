# Client combat: core model and damage queue

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 40-49 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=40-49 sha256=bbfe5496350a6c4dca6a3677fdf3f9a72f79e66fae2eb4f70caee1d3dfca53e4 -->
## Combat Presentation System

Critical architecture: live combat damage is server-authored only. Client presentation is allowed to decide *when* to show a hit, but never *how much* damage combat did.

- **Damage source:** FlatBuffer `DamageEvent` contains `event_id`, `defender_seq`, canonical `attacker_id`, `defender_id`, `raw_damage`, `damage_value`, `hp_after`, `presentation_kind`, and `lethal`. `CombatSwing` wraps a `DamageEvent` plus motion data for confirmed normal attacks. Client-local `queued_at_ms` is stamped in `PushCombatDamageEvent()` only; it is not wire data and must not be serialized.
- **Queue ownership:** every `CObjCHAR` owns `m_CombatDamageQueue`. `recv_combat_swing()` queues the event on the defender before calling `StartConfirmedCombatSwing()`. Standalone `DamageEvent` packets are queued and either wait for a hit frame/projectile impact or present immediately depending on `presentation_kind`.
- **Presentation timing:** `Hitted()` consumes exactly one matching event for the current attacker. `NoEvent` means no HP change, no digits, no hit animation, no vibration, and no hit sound. Never resurrect timeout or missed-hit recovery behavior.
- **Crowd catch-up (2026-09-10 trial):** local-avatar fights with eight recent confirmed monster attackers use adaptive melee draining; membership lasts 3 s after the last confirmed attack and exits after 1 s continuously below eight. Membership is independent of the queue. At a real presentation, drain oldest nonlethal melee events toward 5% max HP outstanding, capped at six positive digits / sixteen events; misses advance silently. One-through-seven fights retain ordinary timing unless still exiting a prior crowd. Projectiles, lethal timing, healing-order guards and buff/impact feedback rules remain protected. See [doc/combat-crowd-drain.md](../../../combat-crowd-drain.md) for diagnostics, limits and the first in-game results: the player reported smoother presentation, and worst visible HP at lethal receipt fell from 31% to 9% across the two sessions. Further gameplay testing continues.
- **Projectile timing:** `ProjectileImpact` events stay queued until a bullet/skill projectile impact calls `Hitted()`. Generic immediate presentation must reject projectile events and push them back.
- **Hard-control interrupted swings:** `StartConfirmedCombatSwing()` records the exact server event id and defender for the attacker's current confirmed swing. Faint/sleep status application calls `CancelInterruptedCombatSwingPresentation()` before `SetCMD_STOP()`: if the swing's projectile has not spawned yet, the defender discards that exact event via `CombatPresentationQueue::discard_event()`/`DiscardQueuedCombatDamageEvent()` instead of leaving it to be consumed by the next attack. Nonlethal avatar damage lowers authoritative shadow HP and stages drift for the next real hit with no phantom digit; lethal avatar damage calls `MarkPendingAuthoritativeDeath()` and `PresentPendingAuthoritativeDeath()` immediately so the player is not alive-client / dead-server. Once `ActionBow`/`ActionGun`/pet weapon fire actually creates a projectile, `MarkPendingCombatSwingProjectileSpawned()` keeps the queued event for the real impact. `Hitted()` and explicit discard paths clear the pending swing state by event id.
<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
