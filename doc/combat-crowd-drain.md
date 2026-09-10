# Crowd damage presentation

The September 10, 2026 client log showed deaths with 1,431, 740 and 1,552 HP
still visible when the lethal packet arrived. The first two never opened the old
twelve-queued-attacker gate. In the 1,431 HP case, eleven nonlethal events held
1,403 damage across only five queued attackers; individual hits often did
160-195 damage, well above the previous tuning session's roughly 35 HP per
attacker. Queued attacker count is not a reliable measure of hidden damage.

The player reports that fights with one through seven monsters feel good. The
new policy therefore preserves their ordinary timing and applies catch-up only
to the local avatar after eight recent monster attackers qualify.

## Trial policy

- `CombatCrowdTracker` records distinct monsters with confirmed deferred attacks
  against the avatar in the last 3,000 ms, including misses. This is an estimate
  of current activity, not a server aggro count. Dead or removed monsters leave
  the tracker. Queue presentation does not remove crowd membership.
- Eight attackers open crowd mode. Once membership drops below eight, it must
  stay below for 1,000 ms before closing. `Proc()` updates this even without new
  hit frames. A returning eighth attacker cancels the exit timer.
- At a normal incoming presentation, extra nonlethal melee events drain oldest
  first while their combined damage exceeds 5% of maximum HP. Six positive
  damage digits and sixteen total events cap each batch. Zero-damage events
  advance their existing checkpoints silently and do not use positive digit slots.
- Projectiles and lethal events retain their existing presentation paths. The
  drain uses `ApplyPresentedCombatDamage`, preserving healing-order guards and
  HP reconciliation. It does not strip buffs or create extra impact effects,
  sounds or vibration. Death is not delayed to complete a drain.

The damage sum is a presentation workload estimate, **not current server HP**:
heals, discarded hits and pending projectiles can make the actual bar discrepancy
different. The 5% target is not a guarantee on HP displayed at death. Some crowd
digits appear before their own monster's impact; the bounded drain trades that
precision for earlier warning of incoming damage.

## First gameplay test (September 10, 2026)

The player reported smoother presentation in the session starting at 19:43:57
UTC. Four deaths arrived with 376, 57, 459 and 352 visible HP out of 4,951 maximum,
compared with 73, 1,431, 740, 1,552 and 957 in the earlier session. Worst visible
HP at lethal receipt fell from 31% to 9%; the average fell from 19% to 6%.
These were different fights, not a controlled benchmark.

Crowd mode was active at all four deaths. Of 62 drain batches that left the
avatar alive, 58 reached the 247-HP backlog target immediately; four reached the
six-digit limit first. The worst new death had 46 recent attackers.

Residual unevenness remains: the largest sampled visible/server HP gap was
846 HP, and one nonfatal drain batch lowered visible HP by 1,123. Keep the
current settings for continued gameplay testing rather than increasing the cap;
watch occasional large catch-up drops and verify smaller fights remain smooth.
The release client build and combat presentation tests passed.

## Reading the next debug log

`[LOG] LEVEL=debug` enables these existing `CombatTrace` diagnostics:

- `crowd drain opened/closed`: recent active attackers separately from queued
  attackers, visible/max HP, queued melee damage, target and timing windows.
- `crowd drain pop`: event ID, original damage/checkpoint and queue age in ms.
- `crowd drain batch`: before/after queued damage and visible HP, shadow HP,
  events and positive digit counts. Repeated batches above target indicate the
  work cap or insufficient presentation opportunities, not gate oscillation.
- `Combat HP death correction deferred`: also records crowd state, active
  attackers, queued melee damage and maximum HP at the lethal receive point.

Compare ordinary fights, a sustained crowd, and reducing the crowd back below
eight. Assess both HP still displayed at death and how early/bursty digits feel.
Log timestamps are UTC (two hours behind Paris in September).

The policy and queue protections are covered by `combat_presenter_tests`.
Changing the tracker layout requires a clean client rebuild because it is a
member of `CObjCHAR`.
