"""Stage 5b: Karkia's loot tables.

Karkia's tables were wired at stage 5 and left empty. This fills them, and it is
the first authored endgame loot tier the game has had -- Oro's 38 tables are
still empty and should get the same treatment next (doc/project-drops.md #5).

--- the three things that decide every number here

**1. The level gap picks the audience, not us.** `Get_DropITEM` returns false at
10+ levels above the monster, so a level-240 player gets *nothing* from anything
below 231. Karkia therefore has two separate loot audiences and the tiers are
placed to match:

    900/901/902 + zone 87   Cemetery, mobs lv215-228   -> players 215-238
    906         + zone 88   Spire Village, lv228-240   -> the only cap-level farm
    903/904/905/907/908     bosses, lv235-240

That is also why the lv240 mythical weapons are boss-only: they have to come off
lv235+ monsters or nobody at cap could ever earn one.

**2. Every kill already rolls.** With `NPC_DROP_ITEM` (col 20) at 80, `drop_var`
is never <= 0 at level parity, so there is no "does it drop" step -- **how many
of slots 0..29 are filled *is* the drop rate.** Measured over 1.5M simulated
kills at parity: slots 0-4 are ~6.0% each, decaying to 1.17% at slot 29; filling
12 slots yields 61.7%, filling all 30 yields 100%. 12 is the house figure, and
matches our live 200-210 tables.

**3. Two multipliers apply before any cell is read**, and they are easy to
forget:

    col 19 (money)  -- fires *instead of* an item, so it eats the item rate
    col 20 (80)     -- 80% own table, 20% the row numbered after the ZONE

The zone fallback is why rows 87 and 88 are written too: they mirror 900 and 906
so the 20% is not a dead roll. Without that mirroring every rate below drops by
a fifth (shields would be 1 in 37, not 1 in 30).

--- the resulting rates, at level parity

    materials / use items      46% of kills
    a shield  (redirect @ 10)  1 in 30
    a weapon  (redirect @ 11)  1 in 32
    money     (col 19 = 15)    15% of kills
    nothing                    33%

    a mythical weapon from a boss   36% per kill  (slots 0-7, col 19 = 0 so
                                                   money never eats the roll)

Table 906 is the exception and carries **three** redirects rather than two: it
is the cap-level farm and has twice the weapon pool (10 lv235 weapons against 5
elsewhere), so weapons run 1 in 16 there. Deliberate -- the hardest monsters in
the zone should pay best.

--- what fills them

Materials are metals, leather and "hearts", never wood: Karkia is a dead world
of ruins and undead and its tables should not read like a forest. Bosses get the
top of the range.

The signature drops are the two imported Jrose sets, which have **no source
anywhere in the game** until now:

  * 17 shields at lv210-240 (`9:308-342`). We ship exactly two endgame shields
    of our own, so this is the worst-served slot in the game by a wide margin.
  * 34 weapons across three tiers (`8:1381-1453`), reachable at all only since
    the drop encoding was widened -- ids above 999 could not be addressed by a
    drop cell before. See rose/common/drop_item_code.h.

The Jrose *back* items are deliberately not here: they cap at level 150 (DEF
5-29), so dropping one off a level-238 monster would be wrong. They want a pass
of their own aimed at the 100-150 band.

--- NPC table changes

Both Drakes are bosses that were sharing a *trash* table -- Deadly Drake (2729)
pointed at 900 and Deadly Drake Alpha (2699) at 906, so they dropped exactly
what the mobs around them did. They get rows 907 and 908.

Idempotent. `--dry-run` / `--verify` / `--restore`. Backups go to build/, never
beside the data: src/pipeline/src/pack.rs walks the data tree filtering only
*hidden* entries -- no extension filter -- so a .bak in data/3DDATA/STB gets
baked into the .vfs.

After running: restart the servers (they cache STBs at startup) and re-bake the
client VFS (the Monster Inspector reads these tables client-side).
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STB = os.path.join(ROOT, "data", "3DDATA", "STB")
DROP_STB = os.path.join(STB, "ITEM_DROP.STB")
NPC_STB = os.path.join(STB, "LIST_NPC.STB")
BACKUP = os.path.join(ROOT, "build", "karkia-drops-backup")
SIDECAR = os.path.join(ROOT, "build", "karkia-drops.json")

WIDE_BASE = 100000          # Rose::Store::kWideBase
LEGACY_MAX_NO = 999
MAX_ITEM_NO = 2047          # tagBaseITEM: m_nItemNo is 11 bits
MAX_SENTINEL = 1000         # Rose::Drop::kMaxSentinel
REDIRECT_BASE_COL = 26      # Rose::Drop::kRedirectBaseColumn
REDIRECT_WIDTH = 5
COMMON_SLOTS = 30           # the main roll is RANDOM(30)
LAST_SLOT = 49              # slot 50 reads col 51 on a 51-column table -> dead

T_BACK, T_WEAPON, T_SUBWPN, T_USE, T_NATURAL = 6, 8, 9, 10, 12

# LIST_NPC columns
COL_DROP_TYPE, COL_DROP_MONEY, COL_DROP_ITEM = 18, 19, 20

MONEY_FIELD = 15            # % of kills that pay zuly instead of an item
MONEY_BOSS = 0              # bosses pay items; money would eat the mythical roll

# ---------------------------------------------------------------- item pools
# Materials, cheapest first -- low slots are the most frequent.
MAT_CEMETERY = [151, 47, 8, 152, 48, 9, 153, 49, 10]      # hearts/leather/metal
MAT_SPIRE = [49, 10, 154, 50, 16, 84, 155, 85, 17]        # the better half
MAT_BOSS = [86, 156, 87, 88, 157]                         # Lisent + top hearts

USE_FIELD = [13, 32]                                      # Vital / Spiritual (XL)
USE_BOSS = [35, 36]                                       # Health / Mana Bottle (XL)

# Jrose shields by level band (type 9)
SHIELD_210 = [308, 309, 310]                              # Freyja, Garm, Fafnir
SHIELD_215 = [320, 321, 322]                              # Steam Clock x3
SHIELD_220 = [311, 312, 313]                              # Cathedral, Ashura, Reconquista
SHIELD_225 = [331]                                        # Lord Knight
SHIELD_230 = [314, 315, 316]                              # Ushumgal, Zlatorog, Lindwurm
SHIELD_235 = [328]                                        # Lord of Riot
SHIELD_240 = [317, 318, 319]                              # the Evolved trio

# Jrose weapons by tier (type 8) -- all above id 999, so all wide-encoded
WPN_220 = [1426, 1427, 1428, 1429, 1430, 1431, 1432, 1433, 1434, 1435, 1436]
WPN_235 = [1437, 1438, 1439, 1440, 1441, 1442, 1443, 1444, 1445, 1446]
WPN_240 = [1383, 1386, 1389, 1392, 1395, 1398, 1401, 1404, 1407, 1410, 1413,
           1416, 1419]

# ---------------------------------------------------------------- the tables
# common: slots 0.. in order. A ("redirect", group) entry costs one common slot
#         and makes that group reachable.
# groups: group number -> the five items in its window.
def field(mats, uses, shields, weapons, extra=None):
    common = [(T_NATURAL, m) for m in mats[:8]] + [(T_USE, u) for u in uses]
    common = common[:10 if extra is None else 9]
    groups = {1: [(T_SUBWPN, s) for s in shields],
              2: [(T_WEAPON, w) for w in weapons]}
    common += [("redirect", 1), ("redirect", 2)]
    if extra:
        groups[3] = [(T_WEAPON, w) for w in extra]
        common.insert(-2, ("redirect", 3))
    return common, groups


def boss(mythicals, shields):
    """Eight mythical slots -> 36% per kill, then materials and a shield."""
    common = [(T_WEAPON, w) for w in mythicals[:8]]
    common += [(T_SUBWPN, s) for s in shields[:2]]
    common += [(T_NATURAL, m) for m in MAT_BOSS[:1]]
    common += [(T_USE, USE_BOSS[0])]
    return common, {}


TABLES = {
    900: ("Cemetery trash (17 mobs, lv215-228)",
          field(MAT_CEMETERY, USE_FIELD, SHIELD_210 + SHIELD_215[:2],
                WPN_220[:5])),
    901: ("Revived Quarantine Officer (lv223)",
          field(MAT_CEMETERY, USE_FIELD, SHIELD_215[2:] + SHIELD_220 + SHIELD_225,
                WPN_220[5:10])),
    902: ("D-Seed (lv215)",
          field(MAT_CEMETERY, USE_FIELD, SHIELD_210 + SHIELD_215[:2],
                [WPN_220[10]] + WPN_220[:4])),
    906: ("Alpha roster (10 mobs, lv228-240)",
          field(MAT_SPIRE, USE_FIELD, SHIELD_230 + SHIELD_235 + SHIELD_240[:1],
                WPN_235[:5], extra=WPN_235[5:])),
    903: ("BOSS Hebarn Officer Pazugenti (lv240)",
          boss([1389, 1398, 1404, 1407, 1419, 1395, 1392, 1386], SHIELD_240)),
    904: ("BOSS Hebarn Officer Scylla Mira (lv240)",
          boss([1383, 1386, 1392, 1401, 1410, 1413, 1416, 1389], SHIELD_240)),
    905: ("BOSS Corroded Golem + Revived Veteran (lv238/235)",
          boss([1395, 1404, 1416, 1413, 1401, 1410, 1383, 1398], SHIELD_240)),
    907: ("BOSS Deadly Drake (lv238, Cemetery)",
          boss([1389, 1392, 1395, 1398, 1401, 1404, 1407, 1410], SHIELD_240)),
    908: ("BOSS Deadly Drake Alpha (lv240, Spire Village)",
          boss([1383, 1386, 1413, 1416, 1419, 1389, 1398, 1404], SHIELD_240)),
}

# Zone-number rows mirror the dominant table for that zone, so the 20% fallback
# is not a dead roll. Without these every rate above loses a fifth.
ZONE_MIRROR = {87: 900, 88: 906}

# npc row -> new drop table. Both Drakes were sharing a trash table.
NPC_TABLE_FIX = {2729: 907, 2699: 908}

BOSS_ROWS = {2685, 2686, 2687, 2688, 2699, 2729}
KARKIA_NPC_RANGE = range(2685, 2732)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = saved
    return mod


def encode(item_type, item_no):
    """Rose::Drop::encode_drop_item."""
    if not 0 < item_no <= MAX_ITEM_NO:
        raise SystemExit(f"item no {item_no} outside 1..{MAX_ITEM_NO}")
    packed = (item_type * 1000 + item_no if item_no <= LEGACY_MAX_NO
              else item_type * WIDE_BASE + item_no)
    if packed <= MAX_SENTINEL:
        raise SystemExit(f"{item_type}:{item_no} packs to {packed}, a sentinel")
    return packed


def build_row(common, groups):
    """slot -> packed value, for one ITEM_DROP row."""
    cells = {}
    for slot, entry in enumerate(common):
        if slot >= COMMON_SLOTS:
            raise SystemExit(f"common section overflows slot {COMMON_SLOTS - 1}")
        if entry[0] == "redirect":
            cells[slot] = entry[1]
        else:
            cells[slot] = encode(*entry)
    for group, items in groups.items():
        base = REDIRECT_BASE_COL + group * REDIRECT_WIDTH
        if len(items) > REDIRECT_WIDTH:
            raise SystemExit(f"group {group}: {len(items)} items, max {REDIRECT_WIDTH}")
        for i, entry in enumerate(items):
            slot = base + i
            if slot > LAST_SLOT:
                raise SystemExit(f"group {group} entry {i} lands on dead slot {slot}")
            cells[slot] = encode(*entry)
    reachable = {e[1] for e in common if e[0] == "redirect"}
    for group in groups:
        if group not in reachable:
            raise SystemExit(f"group {group} has no redirect pointing at it")
    return cells


def plan():
    rows = {}
    for row, (label, (common, groups)) in TABLES.items():
        rows[row] = (label, build_row(common, groups))
    for zone, src in ZONE_MIRROR.items():
        rows[zone] = (f"zone {zone} fallback, mirrors {src}", dict(rows[src][1]))
    return rows


def apply(oro, dry):
    drop = oro.Stb(DROP_STB)
    npc = oro.Stb(NPC_STB)
    report = []
    rows = plan()

    for row in sorted(rows):
        label, cells = rows[row]
        if row >= drop.rows:
            raise SystemExit(f"ITEM_DROP has no row {row}")
        occupied = [s for s in range(LAST_SLOT + 1) if drop.get(row, 1 + s).strip()]
        if occupied and not all(int(drop.get(row, 1 + s) or 0) == cells.get(s, 0)
                                for s in occupied):
            raise SystemExit(
                f"ITEM_DROP row {row} already has content in slots {occupied[:6]} "
                "-- refusing to overwrite a table we did not author")
        for s in range(LAST_SLOT + 1):
            v = cells.get(s, 0)
            drop.set(row, 1 + s, str(v).encode("latin-1") if v else b"")
        common = sum(1 for s in cells if s < COMMON_SLOTS)
        rare = sum(1 for s in cells if s >= COMMON_SLOTS)
        report.append(f"  row {row:<4} {label:<46} {common:>2} common, {rare:>2} rare")

    for nid, tbl in NPC_TABLE_FIX.items():
        was = npc.get(nid, COL_DROP_TYPE).decode("latin-1")
        npc.set(nid, COL_DROP_TYPE, str(tbl).encode("latin-1"))
        report.append(f"  npc {nid} drop table {was} -> {tbl} (was a trash table)")

    money = 0
    for nid in KARKIA_NPC_RANGE:
        if nid >= npc.rows or not npc.get(nid, 0).strip():
            continue
        if not npc.get(nid, COL_DROP_TYPE).strip() or \
                int(npc.get(nid, COL_DROP_TYPE) or 0) == 0:
            continue                       # Ghost Seeds never drop; leave them
        want = MONEY_BOSS if nid in BOSS_ROWS else MONEY_FIELD
        if int(npc.get(nid, COL_DROP_MONEY) or 0) != want:
            npc.set(nid, COL_DROP_MONEY, str(want).encode("latin-1"))
            money += 1
    report.append(f"  money: {money} rows set "
                  f"(field {MONEY_FIELD}%, bosses {MONEY_BOSS}%)")

    if dry:
        return report, None
    return report, (drop.to_bytes(), npc.to_bytes())


def verify(oro):
    drop = oro.Stb(DROP_STB)
    npc = oro.Stb(NPC_STB)
    bad = []
    for row, (label, cells) in plan().items():
        for s in range(LAST_SLOT + 1):
            got = int(drop.get(row, 1 + s) or 0)
            if got != cells.get(s, 0):
                bad.append(f"row {row} slot {s}: {got} != {cells.get(s, 0)}")
                break
    for nid, tbl in NPC_TABLE_FIX.items():
        if int(npc.get(nid, COL_DROP_TYPE) or 0) != tbl:
            bad.append(f"npc {nid}: drop table is "
                       f"{npc.get(nid, COL_DROP_TYPE).decode('latin-1')}")
    for nid in KARKIA_NPC_RANGE:
        if nid >= npc.rows or not npc.get(nid, 0).strip():
            continue
        if int(npc.get(nid, COL_DROP_TYPE) or 0) == 0:
            continue
        want = MONEY_BOSS if nid in BOSS_ROWS else MONEY_FIELD
        if int(npc.get(nid, COL_DROP_MONEY) or 0) != want:
            bad.append(f"npc {nid}: money is "
                       f"{npc.get(nid, COL_DROP_MONEY).decode('latin-1')}, want {want}")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    oro = load("import-oro")

    if args.restore:
        if not os.path.isdir(BACKUP):
            sys.exit("no backup -- nothing to restore")
        n = 0
        for path in (DROP_STB, NPC_STB):
            src = os.path.join(BACKUP, os.path.basename(path))
            if os.path.isfile(src):
                shutil.copyfile(src, path)
                n += 1
        if os.path.exists(SIDECAR):
            os.remove(SIDECAR)
        print(f"restored {n} table(s) from {os.path.relpath(BACKUP, ROOT)}")
        return 0

    if args.verify:
        bad = verify(oro)
        print(f"{len(TABLES)} tables + {len(ZONE_MIRROR)} zone mirrors; "
              f"{len(bad)} problem(s)" + ("\n  " + "\n  ".join(bad[:10]) if bad else ""))
        return 1 if bad else 0

    report, blobs = apply(oro, args.dry_run)
    print("\n".join(report))
    if args.dry_run:
        print("\ndry run: nothing written")
        return 0

    os.makedirs(BACKUP, exist_ok=True)
    for path in (DROP_STB, NPC_STB):
        bak = os.path.join(BACKUP, os.path.basename(path))
        if not os.path.exists(bak):
            shutil.copyfile(path, bak)
    for path, blob in zip((DROP_STB, NPC_STB), blobs):
        with open(path, "wb") as fh:
            fh.write(blob)
    with open(SIDECAR, "w", encoding="utf-8") as fh:
        json.dump({"tables": sorted(TABLES), "zones": ZONE_MIRROR,
                   "npc_table_fix": NPC_TABLE_FIX}, fh, indent=1)

    bad = verify(oro)
    if bad:
        print("VERIFY FAILED after writing:")
        for b in bad[:10]:
            print("  " + b)
        return 1
    print("\nwritten and verified; restart the servers and re-bake the VFS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
