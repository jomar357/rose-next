"""Stage 6d: give Karkia its two working shops.

Karkia shipped four NPCs with shop tabs, and none of them sold anything useful:

  Gelt      4019  Spire Village      tab 585 -- past the end of LIST_SELL.STB
  Nemo      4142  Abandoned Church   tab 584 -- past the end of LIST_SELL.STB
  Belfa     4103  Foot of the Tower  tabs 478-481, shared with Crune
  Orentark  4104  Foot of the Tower  tabs 245/248, shared -- Materials, Dealer Skill

Two findings shaped what this script does, both from reading the client rather
than from the tables:

**A shop only exists if the NPC's .CON calls `GF_openStore`.** Exactly three
reachable Karkia conversations do: EM86-001 (Nemo), EM86-013 (Gelt) and
EM02-114 (Orentark). **Belfa does not**, so his four tabs can never open no
matter what is written into them -- which is why this script leaves him alone
and the roadmap's "a working shop for free" claim needed correcting. Fixing
Belfa means editing compiled Lua (a QEX1 appendix or a .CON rebuild), which is
a separate job.

All three call `GF_openStore(owner, 0)`, and the client only draws the fourth
tab for `bSpecialTab = 1`. So **only LIST_NPC cols 21-23 are usable**; col 24
is written as 0.

**A dangling tab row is safe but blank.** `STBDATA::value` bounds-checks the
flat index and returns a default, so rows 584/585 read as empty rather than
out of bounds -- an empty nameless tab, not a crash. (Note the client's
`CStringManager::GetStoreTabName` guards with `iIndex > row_count`, an
off-by-one that lets `iIndex == row_count` through; harmless for the same
reason, but it is a real off-by-one.)

Rather than pad LIST_SELL out to row 585 with 22 dead rows, this appends four
rows at 561-564 and repoints the two NPCs onto them.

--- what is sold, and why

`Rose::Store::encode_store_item` has a **wide form** -- `type * 100000 + no`
for ids above 999 -- supported by the client, the server and the shop editor.
That is what makes the imported Jrose weapons sellable at all: at ids 1381-1453
they are unreachable through the legacy `type * 1000 + no` packing, the same
wall that stops them ever dropping (see doc/project-drops.md).

None of the 73 imported weapons is sold anywhere today, so all of them are
Karkia-exclusive by construction. They fall into clean level tiers, and Oro's
weapon merchant (Huzam, tabs 5 and 6) already occupies 210 and 230:

    Oro sells        210, 230
    Karkia sells     215, 225      <- this script
    Karkia drops     220, 235, 240 <- reserved, doc/project-drops.md

The level-240 set is the mythical-name tier (Bahamut, Phoenix, Griffon,
Unicorn, Albion, Quetzalcoatl, ...) and is deliberately left for drops, as are
220 and 235. Two tiers left over are used by neither: the partial level-210 set
(1420-1425) duplicates Oro's tier, and the low oddments (1447-1453, levels
150-205) sit far below Karkia's 215-240 band.

Requirements are on our own scale, not inflated -- our level-230 Viper weapons
already ask STR 335-365, and the level-215 tier here asks 277-321.

Armour is deliberately not stocked; Karkia's armourer (Astraea) is in Memories,
which is unreachable, and there is no armour import yet.

Idempotent. `--dry-run` / `--verify` / `--restore`. Backups go to build/, never
beside the data: src/pipeline/src/pack.rs walks the data tree filtering only
*hidden* entries -- no extension filter -- so a .bak in data/3DDATA/STB gets
baked into the .vfs.

After running: restart the servers (they cache STBs at startup) and re-bake the
client VFS.
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
SELL_STB = os.path.join(STB, "LIST_SELL.STB")
SELL_STL = os.path.join(STB, "LIST_SELL_S.STL")
NPC_STB = os.path.join(STB, "LIST_NPC.STB")
BACKUP = os.path.join(ROOT, "build", "karkia-shops-backup")
SIDECAR = os.path.join(ROOT, "build", "karkia-shops.json")

WIDE_BASE = 100000          # Rose::Store::kWideBase
LEGACY_MAX_NO = 999         # Rose::Store::kLegacyMaxItemNo
MAX_ITEM_NO = 2047          # tagBaseITEM: m_nItemNo is 11 bits
SLOTS = 48                  # LIST_SELL is 2 + 48 columns

T_WEAPON, T_USE, T_NATURAL = 8, 10, 12

# LIST_NPC shop-tab columns. Col 24 is the fourth tab, which the client draws
# only for openStore(npc, 1); every Karkia seller passes 0, so it stays empty.
TAB_COLS = (21, 22, 23, 24)

# The imported Jrose weapons, by level tier. Complete coverage of all 13 weapon
# types in each of the two tiers we sell.
ARMS_215 = [1381, 1384, 1387, 1390, 1393, 1396, 1399, 1402, 1405, 1408, 1411,
            1414, 1417]
ARMS_225 = [1382, 1385, 1388, 1391, 1394, 1397, 1400, 1403, 1406, 1409, 1412,
            1415, 1418]

# Reserved for drops -- listed so the split is recorded in one place, and so
# --verify can prove none of them leaked into a shop.
DROP_ONLY = (
    [1426, 1427, 1428, 1429, 1430, 1431, 1432, 1433, 1434, 1435, 1436] +   # 220
    [1437, 1438, 1439, 1440, 1441, 1442, 1443, 1444, 1445, 1446] +         # 235
    [1383, 1386, 1389, 1392, 1395, 1398, 1401, 1404, 1407, 1410, 1413,
     1416, 1419]                                                           # 240
)

ARROWS = [301, 302, 303, 304, 305, 306, 311, 312, 313, 314, 315, 316, 317]
BULLETS = [321, 322, 323, 324, 325, 326, 327, 331, 332, 333]
SHELLS = [341, 342, 343, 344, 345, 351, 352, 353]
REPAIR_HAMMER = 291

# Endgame consumables only -- the church has little, but what it has is potent.
SUPPLIES = [3, 6, 35,        # Health Vial (L), Health Bottle (L) / (XL)
            23, 26, 36,      # Mana Vial (L), Mana Bottle (L) / (XL)
            9,               # Herbal Medicine (L)
            12, 13, 14,      # Vital Water (L) / (XL) / (XXL)
            31, 32, 33,      # Spiritual Water (L) / (XL) / (XXL)
            352]             # Junon Polis Return Scroll

# (row, tab caption, [(item type, item no), ...])
#
# 563 and 564 are chosen to land on LSEL563 "Potions" and LSEL564 "Ammo/Arrows",
# two orphan STL keys that were already in LIST_SELL_S.STL with no matching STB
# row. Reusing them means the captions are right with no new strings -- and it
# is why the potion tab is 563 and the ammunition tab 564, rather than the other
# way round. The caption written to col 0 is only a dev label; the client shows
# the STL text, so `check_captions` asserts the two agree.
NEW_TABS = [
    (561, "Karkia Arms lv215", [(T_WEAPON, n) for n in ARMS_215]),
    (562, "Karkia Arms lv225", [(T_WEAPON, n) for n in ARMS_225]),
    (563, "Potions", [(T_USE, n) for n in SUPPLIES]),
    (564, "Ammo/Arrows",
     [(T_NATURAL, n) for n in ARROWS + BULLETS + SHELLS]
     + [(T_USE, REPAIR_HAMMER)]),
]

# npc row -> the three drawable tabs, in order
#
# Belfa carries the same arms and ammunition as Gelt, deliberately. He is the
# Master Smith at the Foot of the Tower, which is the staging zone -- gear
# should be buyable where you prepare, not only in the deep field. Sharing the
# rows costs nothing and keeps one place to edit the stock.
#
# His old tabs 478-481 are *our* low-level rows, shared with Crune: level 38-77
# stock in a level 215-240 zone. Repointing leaves Crune untouched.
NPC_TABS = {
    4019: (561, 562, 564),   # [Spire Warrior] Gelt  -- arms and ammunition
    4103: (561, 562, 564),   # [Master Smith] Belfa  -- the Tower staging shop
    4142: (563, 0, 0),       # [Shrine Maiden] Nemo  -- "short of supplies"
}
NPC_NAMES = {4019: "[Spire Warrior] Gelt", 4103: "[Master Smith] Belfa",
             4142: "[Shrine Maiden] Nemo"}

# STB tables an item type is validated against, for the don't-sell / range check
TYPE_TABLE = {T_WEAPON: "LIST_WEAPON.STB", T_USE: "LIST_USEITEM.STB",
              T_NATURAL: "LIST_NATURAL.STB"}

ITEM_DONT_SELL = 0x01


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
    """Rose::Store::encode_store_item."""
    if not 0 < item_no <= MAX_ITEM_NO:
        raise SystemExit(f"item no {item_no} outside 1..{MAX_ITEM_NO}")
    return (item_type * 1000 + item_no if item_no <= LEGACY_MAX_NO
            else item_type * WIDE_BASE + item_no)


def check_captions(oro):
    """A pre-existing STL key must say what we think it says.

    LSEL563/LSEL564 already existed as orphans with no STB row. Reusing a key
    is only safe if its text matches the stock we are about to put behind it --
    otherwise the client draws someone else's caption over our tab.
    """
    stl = oro.Stl(SELL_STL)
    lookup = {k.decode("latin-1"): j for j, (k, _i) in enumerate(stl.keys)}
    bad = []
    for row, name, _items in NEW_TABS:
        key = f"LSEL{row}"
        j = lookup.get(key)
        if j is None:
            continue                      # we will append it ourselves
        texts = {r[j][0].decode("latin-1") for r in stl.langs if r[j][0]}
        if texts != {name}:
            bad.append(f"{key} already reads {sorted(texts)}, "
                       f"but this tab is {name!r}")
    return bad


def check_stock(rd):
    """Refuse to stock anything missing, or flagged not-for-sale."""
    bad = []
    for _row, _name, items in NEW_TABS:
        if len(items) > SLOTS:
            bad.append(f"row {_row}: {len(items)} items exceeds {SLOTS} slots")
        for ty, no in items:
            tbl = rd.Stb(os.path.join(STB, TYPE_TABLE[ty]), "utf-8")
            if no >= tbl.rows or not rd.scrub(tbl.s(no, 0)).strip():
                bad.append(f"type {ty} no {no}: no such item")
                continue
            if tbl.i(no, 3) & ITEM_DONT_SELL:
                bad.append(f"type {ty} no {no} "
                           f"({rd.scrub(tbl.s(no, 0))}): flagged don't-sell")
    leaked = [n for _r, _nm, items in NEW_TABS for ty, n in items
              if ty == T_WEAPON and n in DROP_ONLY]
    if leaked:
        bad.append(f"drop-only weapons leaked into a shop: {leaked}")
    return bad


def apply(oro, dry):
    sell = oro.Stb(SELL_STB)
    npc = oro.Stb(NPC_STB)
    stl = oro.Stl(SELL_STL)
    report = []

    want_rows = max(r for r, _n, _i in NEW_TABS) + 1
    if sell.rows < want_rows:
        report.append(f"LIST_SELL.STB {sell.rows} -> {want_rows} rows")
        sell.grow_to(want_rows)

    for row, name, items in NEW_TABS:
        if sell.occupied(row):
            cur = sell.get(row, 0).decode("latin-1")
            if cur != name:
                raise SystemExit(
                    f"LIST_SELL row {row} is occupied by {cur!r} -- refusing "
                    "to overwrite a row we did not author")
        key = f"LSEL{row}"
        sell.set(row, 0, name.encode("latin-1"))
        sell.set(row, 1, key.encode("latin-1"))
        for slot in range(SLOTS):
            packed = encode(*items[slot]) if slot < len(items) else 0
            sell.set(row, 2 + slot, str(packed).encode("latin-1") if packed
                     else b"")
        if not stl.has(key):
            stl.append(key, row, name)
            report.append(f"  STL +{key} = {name!r}")
        report.append(f"  row {row} {name!r}: {len(items)} items")

    for nid, tabs in NPC_TABS.items():
        before = [npc.get(nid, c).decode("latin-1") or "0" for c in TAB_COLS]
        for c, v in zip(TAB_COLS, list(tabs) + [0]):
            npc.set(nid, c, str(v).encode("latin-1") if v else b"0")
        after = [npc.get(nid, c).decode("latin-1") for c in TAB_COLS]
        report.append(f"  npc {nid} {NPC_NAMES[nid]}: {before} -> {after}")

    if dry:
        return report, None
    return report, (sell.to_bytes(), npc.to_bytes(), stl.to_bytes())


def verify(oro, rd):
    sell = oro.Stb(SELL_STB)
    npc = oro.Stb(NPC_STB)
    stl = oro.Stl(SELL_STL)
    bad = []
    for row, name, items in NEW_TABS:
        if sell.rows <= row:
            bad.append(f"LIST_SELL has no row {row}")
            continue
        if sell.get(row, 0).decode("latin-1") != name:
            bad.append(f"row {row}: caption is "
                       f"{sell.get(row, 0).decode('latin-1')!r}")
        if not stl.has(f"LSEL{row}"):
            bad.append(f"row {row}: no STL key LSEL{row}")
        got = [int(sell.get(row, 2 + s) or 0) for s in range(SLOTS)]
        want = [encode(*i) for i in items] + [0] * (SLOTS - len(items))
        if got != want:
            bad.append(f"row {row}: stock differs from plan")
    for nid, tabs in NPC_TABS.items():
        got = tuple(int(npc.get(nid, c) or 0) for c in TAB_COLS)
        if got != tuple(list(tabs) + [0]):
            bad.append(f"npc {nid}: tabs are {got}, expected "
                       f"{tuple(list(tabs) + [0])}")
    # nothing reserved for drops may be on sale anywhere in the table
    for row in range(sell.rows):
        for s in range(SLOTS):
            v = int(sell.get(row, 2 + s) or 0)
            if v <= 0:
                continue
            ty, no = ((v // WIDE_BASE, v % WIDE_BASE) if v >= WIDE_BASE
                      else (v // 1000, v % 1000))
            if ty == T_WEAPON and no in DROP_ONLY:
                bad.append(f"row {row} slot {s}: drop-only weapon {no} on sale")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    oro = load("import-oro")
    rd = load("rose-data-reader")

    if args.restore:
        if not os.path.isdir(BACKUP):
            sys.exit("no backup -- nothing to restore")
        n = 0
        for path in (SELL_STB, NPC_STB, SELL_STL):
            src = os.path.join(BACKUP, os.path.basename(path))
            if os.path.isfile(src):
                shutil.copyfile(src, path)
                n += 1
        if os.path.exists(SIDECAR):
            os.remove(SIDECAR)
        print(f"restored {n} table(s) from {os.path.relpath(BACKUP, ROOT)}")
        return 0

    if args.verify:
        bad = verify(oro, rd)
        print(f"{len(NEW_TABS)} tabs, {len(NPC_TABS)} NPCs; "
              f"{len(bad)} problem(s)"
              + ("\n  " + "\n  ".join(bad) if bad else ""))
        return 1 if bad else 0

    bad = check_captions(oro) + check_stock(rd)
    if bad:
        print("refusing to write:")
        for b in bad:
            print("  " + b)
        return 1

    report, blobs = apply(oro, args.dry_run)
    print("\n".join(report))
    total = sum(len(i) for _r, _n, i in NEW_TABS)
    print(f"\n{len(NEW_TABS)} tabs, {total} items, "
          f"{len(DROP_ONLY)} weapons reserved for drops")
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    os.makedirs(BACKUP, exist_ok=True)
    for path in (SELL_STB, NPC_STB, SELL_STL):
        bak = os.path.join(BACKUP, os.path.basename(path))
        if not os.path.exists(bak):
            shutil.copyfile(path, bak)
    for path, blob in zip((SELL_STB, NPC_STB, SELL_STL), blobs):
        with open(path, "wb") as fh:
            fh.write(blob)
    with open(SIDECAR, "w", encoding="utf-8") as fh:
        json.dump({"tabs": [[r, n] for r, n, _i in NEW_TABS],
                   "npcs": {str(k): list(v) for k, v in NPC_TABS.items()}},
                  fh, indent=1)

    bad = verify(oro, rd)
    if bad:
        print("VERIFY FAILED after writing:")
        for b in bad:
            print("  " + b)
        return 1
    print("written and verified; restart the servers and re-bake the VFS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
