# AI skill references: five failure classes

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 528-654 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=528-654 sha256=dc1a16ef9c0abc9b82d1b54797500b03cff22da4e9f29ac1b59e5a291f3ff323 -->
**The same rule holds for skills.** AI action 24 carries a `short` skill id at
offset 10 and nothing validated it either: RoseZA's `OR_THORNIE.AIP` (Fearsome
Terrasaurus King) casts 3603 "Charge" and 3604 "Fireball", both blank rows in our
`LIST_SKILL`. The server broadcast the cast, `Skill_START` switched on
`SKILL_TYPE 0` and did nothing, and every client played the boss's casting
motion for nothing — which also replaced the attack motion of a swing the server
had already applied, so the client discarded that hit and the killing blow
presented death from a bar ~1000 HP too high (2026-09-14). `F_AIACT24` now
refuses a blank/out-of-range skill with a once-per-id warning, the client
presents a self-pre-empted swing instead of folding it (client `CLAUDE.md`,
"Self-pre-empted swings"), and `scripts/audit-ai-skill-refs.py` strips the casts
(same CLI and backup scheme as the monster audit; backups in
`build/ai-skill-refs/`). Nine file/skill pairs, 16 records, in six files. The
docstring records what each id is in RoseZA/667 so a later skill import can
`--restore` first and put the casts back. `import-oro-667.py` step 3h checks that
a cast *animates*, not that the row exists. **The proper fix is
`scripts/import-monster-skills.py`** (first used for this boss: Charge 3603 +
Fireball 3604, with FILE_EFFECT 1881-1884, LIST_EFFECT bullet 476 and eight
`.eft`/`.ptl` files): it resolves the whole chain a monster skill needs, writes
rows **in place at the source index** because our effect/sound/bullet tables are
the same lineage as RoseZA's (it refuses if an index is occupied by something
else), and **does not copy `SKILL_POWER`** — RoseZA's 3500/2000 would one-shot at
our stat scale, our own monster attack skills run 25-100, and for a 2900-ATK
boss the weapon formula floors at ~1400 regardless of power, so both use the
magic formula. The first cut (450/350, sized on balance-sim's synthetic Knight)
measured 2x too hot on the real tester (6.4 damage per power point); they are
now **230/190**, which landed Fireball at 1436-1447 on a 6102-HP character.
Sequence: import → `audit-ai-skill-refs.py --restore` → `audit-ai-skill-refs.py`
again. Second use: Nigaki's Voltage Jolt (871, `--skills 871`) — **Karkia's AI
is Jrose's, so its skill ids are Jrose's** (RoseZA's 871 is a different row);
the row is the Mage player skill, so the importer's per-skill `clear` list
blanks its learn-tree columns and its STL key (which would alias one of ours).
Every effect/bullet/sound index already matched here and the chain was present.
**The quiet failure is an id that is occupied here by a different skill**, which
the blank-row check cannot see: Nigaki also cast Jrose's 923 (rank 3 of the
Cleric's ally Heal, type 11) and our 923 is the player's Healing (type 10,
self) — the Flower Garden's Nigakis spam-cast it on each other with a spell
sound and never fought back. The audit now maps an AI file to its source dump by
filename prefix (`kh_`/`kak_` → Jrose, `or_` → RoseZA) and flags a cast whose
`SKILL_TYPE` differs between the dump's row and ours (the Karkia importer's own
ports and re-points are allowlisted in `DELIBERATE`); its `--remap
FILE.aip:OLD=NEW` re-points casts, and the importer's per-skill `dest` puts a
colliding row at the table's tail (Heal Ally at **7012**, `set={21:16, 22:370}`
because Jrose keeps the ability in its columns 89/90). The Devourer's 3613 was
the other collision (RoseZA long-range damage vs our Karkia Stun port) and is
stripped. Mukuroji's 30-per-tick "poison" is its retail burn (3050 → LIST_STATUS
58 Flame Heat), not a defect. **The third failure class is a cast that can never
present itself**: the client plays CHR slot `nMotion` to cast and `nMotion+1` to
release, and a projectile skill launches only from frames 24/34 (or 26/25) of
the release clip. Orgeid's Jrose CHR held the event-less casting clip in both
slots (bolt never fired, damage landed on a later melee frame with no visual,
status payload timed out); Mukuroji's release is the pig attack clip (frames
21/31). The audit **warns** about these on every run and never strips them —
the fix is a CHR slot (`CHR_MOTION_OVERRIDE` in `import-karkia.py`, applied
without a `--stage 3` by `scripts/fix-chr-skill-slots.py`); `--strict-motions`
makes them fail `--verify`. Current list: Mukuroji 2539 (kept aside, its donor
AI and model disagree) and the seven nameless, unspawned `sur_mon_s1.aip` rows
944-959.
**The fourth failure class is an AI authored against a slot layout the model
does not have.** Grand Master Devourer 2226 (third importer use: 3609 Dispel
Buffs, 3610 Area Slow, 3611 Stun Blast, RoseZA's 3613 Range Attack at **7013**
because ours is Karkia Stun) casts on nMotion 7 and 9, but its model's clip
pairs sit at 6/7 and 8/9 — with our cast = `nMotion` / release = `nMotion+1`
rule (client `CObjMOB` and server `CObjNPC` agree; 1498 of 1565 shipped casts
follow it) the boss released on an event-less charge clip or on no clip at all,
and its self-buffs on 2 released on the hit clip. A parked payload with no
action frame is not lost, it is *folded silently* after the 3 s abandon grace
(`ProcTimeOutEffectedSkill`), so the failure reads as damage with no cast. The
fix is the AI, not the CHR: `audit-ai-skill-refs.py --remotion FILE.aip:OLD=NEW`
(7=6, 9=8, 2=6 here), recorded in the manifest like `--remap`; `--restore
--only FILE.aip` undoes one file without reverting every other file's strip and
remap. Two more data traps from that kit: **RoseZA/667 author a skill's status
in column 88/90**, which our 87-column table never reads (a verbatim copy is a
stun that does not stun — the importer's `set` puts the id back into column
11, and a slow also needs `AT_SPEED` 23 in 21 and a rate in 23, house 30-70%);
and Stun Blast, like the source, has no success ratio, so the stun always lands
when the event fires. The audit's release-clip warning now covers every cast,
split into *projectile* (bullet never fires) and *payload* (resolves silently
~3 s late); ~110 retail self-buffs are in the payload list and are left alone.
First test (2026-09-14): the four imported casts never rolled — they live on
the *attack-move* pattern (evaluated only while the boss chases) behind 25/8/8/5%
rolls and extra gates (a buff on you; a second attacker; an enemy in reach) —
and what read as "a spell with no status" was the boss's when-damaged
self-casts 3596/3597, the same RoseZA rows imported nameless by the old Oro
import with the column-88 status lost; re-imported over them (`overwrite`),
which also repairs the Eldeon/Karkia casters sharing them. **Eldeon's skill
rows are ruff's, not RoseZA's** (byte-identical to the ruff dump, an older
authoring; ruff's LIST_STATUS is our numbering), so a row that "disagrees"
with RoseZA's column 88 is usually doing what ruff meant, just differently —
policy (2026-09-15): keep what works even where it differs, fix what would
bug, fix what makes no sense. Eight rows qualified and are corrected in place
by the importer's `patch` mode (name + status + ability columns only, the
balance passes' damage columns untouched): a self-buff that muted its own
caster (3588), two self/area casts with no status at all (3593, 3598), and
five "damage + stun" rows with no stun (3551, 3572, 3582, 3595, 3527). 3572 is
shared by the Ikaness Engineer and Karkia's Murilos, and a stun on a fast,
numerous spider is a nuisance — so `patch` + `dest` copies our row to **7014**
with the stun for the Engineer (`--remap ed_icanes6.aip:3572=7014`) and the
Murilos keep the plain row. EZ01 validated in game 2026-09-15; EJ02/EJ03 rows
applied, pending a fight. Details and what was deliberately left alone: the
importer docstring.
**The fifth failure class is a gate nobody can pass**: even at a 100% roll
(`--rechance FILE.aip:SKILL=PCT`, for testing) the two damage casts never
fired, because their condition 02 ("N enemies within D m with level diff in
[lo, hi]") is authored as [100, 100] — our server reads it through the 2004
`short nLevelDiff/nLevelDiff2` layout, and a target exactly 100 levels below
the boss does not exist. RoseZA's server evidently read that as "any". Fixed
with `--rewindow FILE.aip:SKILL=LO,HI` (-100,100); the audit warns about any
cast behind a lo >= hi window (only these two in the tree; 18 more such
windows gate retail movement). Also: a pattern's events are first-match-wins,
so a 100% event starves everything after it — bump one at a time. All four
casts plus the self-casts validated in game 2026-09-14: bolt ~1200 with a
real projectile, Stun Blast ~820 with the stun, slow and dispel with icons.
The last stripped casts — Inguz 654 (3044, an area stun), Penguin
Artillery 1458 (2980) and Gangster Pangs 1456/1457 (2979), none spawned — are
imported too (2026-09-15, powers re-based by the casters' ATK; all three validated
in game the same day — RoseZA's 3044 needed a scope, it was authored at 0, and a
4 s duration, since a cast's status is presented 1-3 s after the server applies it),
so nothing is stripped for a missing row any more. Mini-Devourer 2225 casts 3042 from a
model with no skill clip at all (slots 0-5); with no 3D artist, its casts are
removed (`--strip or_minidevourer1.aip:3042`) and it fights with normal attacks. Two client rules came out of validating the kit: a remote caster's queued
skill command must be validated on `GSV_SKILL_START` (a mob's second cast was
being deleted, its lethal projectile then died by the 6 s timeout), and a lethal
legacy `GSV_DAMAGE_OF_SKILL` payload arms pending death at receive (else the
avatar's swings in the 2 s before the caster's action frame are silent instead
of MISS). Both in client `CLAUDE.md`.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
