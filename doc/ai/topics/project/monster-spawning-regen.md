# Monster spawning: regen point caps

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 171-209 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=171-209 sha256=93f94b9f1efb36350af3d155076d467dc832ed946dab09dc8c2a8a98e9bece74 -->
### Monster Spawning: A Regen Point's Cap Is Not A Cap

`CRegenPOINT::Proc` is a **tactical escalation state machine**, not a spawn list. Its
five "basic" slots plus two "tactics" slots are steps, and each tick it picks one or
two of them — never all five — from an 11-branch table indexed by

    iVar = ((limitCNT*2 - liveCNT) * curTactics * 50) / (limitCNT * tacticPoint)

Two things follow, and both have bitten:

- **`tacticPoint` decides whether `limitCNT` means anything.** `CZoneTHREAD::RegenCharacter`
  has **no cap check** — the only gate is `Proc`'s early return while
  `liveCNT >= limitCNT`, so whatever branch fires spawns its full count regardless of
  how much room is left. `tacticPoint` scales the whole table: at 100 (the house value;
  every zone we ship uses 50-200) an empty point starts at `iVar == curTactics == 1`,
  walks up from the bottom branch and fills to exactly `limitCNT`. At **1** the first
  tick computes `iVar = 100`, lands in the *top* branch, and spawns four bodies into a
  cap of one. Karkia's two main maps shipped that way and held 3,388 and 1,109 monsters
  against summed caps of 847 and 278 — **every density figure measured from the tables
  was 4x low.** Never derive a zone's population from `sum(limitCNT)`; simulate `Proc`.
- **Per-slot count must stay well under `limitCNT`.** Count 5 against a cap of 5 means
  slot 0 fills the point on tick one and slots 1-4 are unreachable until a player
  clears the nest by hand — which reads in game as "this zone only has one monster",
  then a second species, then a third. Retail runs counts of 1-2 against caps of 2-13.
  Weight a species by **repeating its slot**, never by raising the count. `interval`
  paces the escalation as well as the respawn: one tick is one step.

Karkia's rosters, caps, intervals and camp layout live in `scripts/import-karkia.py`
stage 3 (`SPAWN_ROSTER` / `SPAWN_CAP` / `SPAWN_INTERVAL` / `SPAWN_THINNING` /
`SPAWN_CAMPS`), which **rebuilds every REGEN lump from source on each run** — so
editing an `.IFO` by hand or in the map editor is silently undone by the next
`--stage 3`. Note the two main maps are authored as a *carpet* of single-species
points, so spatial thinning deletes species; `SPAWN_CAMPS` merges neighbouring points
into mixed-species camps instead, which cannot.

Separately: **a zone that ships no `.MOV` file is blocked on every cell**, which
silently disables monster leashing, wandering and fleeing while leaving chase intact.
See the gameserver `CLAUDE.md`.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
