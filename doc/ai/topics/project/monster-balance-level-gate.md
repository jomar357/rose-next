# Monster balance and the level gate

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 729-748 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=729-748 sha256=cc2a5537e7609a6175a2c40ca06fdc9ac7521cbd4b25bb5e54f7bcb5930b44b2 -->
### Monster Balance And The Level Gate

Combat math lives in `src/common/calculation.cpp` (server-only, behind `#ifdef __SERVER`). Two properties dominate how hard content feels, and neither is obvious from the numbers in `LIST_NPC.STB`:

- **The normal-attack gate is level-proportional.** `Get_SuccessRATE` discards an attack outright when `(player_lv + 10) - monster_lv * kLevelGateScale + rand(1..50)` is non-positive. Because the monster term is *scaled*, the required level surplus grows with absolute level — at the original 1.1 it was ~2-3 levels in Luna, 6-10 across Eldeon, and 20+ in Oro, where it exceeded our own 240 character cap (Gates of Muris wanted 243; the level-240 bosses wanted 254). It is now **1.05**. Anything that reads as "I can't hit this" is usually this gate, not accuracy — check the level difference before touching HIT/AVOID.
- **Skills deliberately use a gentler, non-proportional gate** (`Get_SkillDAMAGE`): weapon `lv + 20 - mlv`, magic `lv + 30 - mlv`. A level-140 raider lands 0% of auto-attacks on a level-173 monster but ~66% of skills. Casters therefore stay effective at a level deficit where auto-attacks stop connecting entirely — that asymmetry is intended, keep it.

Also worth knowing: **damage is proportional to `(ATK - DEF + 250)`**, so a monster whose DEF approaches the player's ATK sits on a damage floor — the fight gets long *and* reads as though the hits do nothing, and small gear changes swing the result wildly because the two terms nearly cancel. And `Get_DropITEM` returns false once `player_lv - monster_lv >= 10`, so lowering a monster's level to make it easier can silently kill its drops.

Idempotent balance passes correct the data, each with a sidecar next to the STB and `--dry-run` / `--verify` / `--restore`. **Re-running them has order dependencies**: the DEF/RES pass looks up the trend at a monster's *current* level and consults the boss sidecars to identify bosses, so if a level or the boss set changes, restore and re-apply DEF/RES afterwards; `rebalance-oro-bosses.py` changes HP that `rebalance-exp-rewards.py` keys on, so **bosses before EXP**. Then re-verify **every** pass, not just the one you touched: the Karkia and Eldeon passes recompute their targets from a trend fitted on the live table's level 60-199 rows, and both now exclude Oro's id band 2100-2399 (the Shadow Ghost ladder sits at 183-219) and 3001-3003 (event summons with placeholder stats) — any future import into that window needs the same exclusion or every verify drifts by a few points.

- `scripts/rebalance-oro-667.py` — the 667-build Oro (see the section below): level bands per zone, HP/ATK/HIT/AVOID onto the sub-200 trend with the zone spread square-rooted and capped, bosses by hand, the Shadow Ghost ladder. Writes `LIST_NPC.oro667-bosses.json`. Replaced `rebalance-oro-accuracy.py`, whose factor was fitted to RoseZA's scale.
- `scripts/rebalance-karkia.py` — Karkia levels/HP/ATK + `karkia-bosses.json`.
- `scripts/rebalance-endgame-curve.py --stat def|res` — caps level-200+ DEF/RES at the trend fitted from levels 60-199. Bosses (three sidecars) get `BOSS_MULTIPLIER` (1.2).
- `scripts/rebalance-oro-bosses.py` — boss HP to 10x the HP trend and level to the 240 cap, scoped from the Oro REGEN lumps by HP column. Since the Oro pass budgets its own bosses under that threshold it now only reaches `EXTRA_BOSS_ROWS` (Luna's Behemoth King).
- `scripts/rebalance-eldeon-outliers.py` — two hand-picked monsters that escaped the passes above through scope gaps.
- `scripts/rebalance-exp-rewards.py` — the EXP column from the levelling pace.

Their docstrings carry the reasoning and record what was deliberately left alone (Luna's Astarot King and Gem quartet, the big-HP piñata field monsters, unspawned duplicate rows with billion-HP columns). Since `data/` is gitignored, **the script is the only committed record of the change** — put new reasoning there, not just in a commit message.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
