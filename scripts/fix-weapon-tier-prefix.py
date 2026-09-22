"""Repair the columns the lv210 weapon tier imported wrong: name prefix and motion type.

`LIST_WEAPON.STB`'s second-to-last column is the STR_ITEMPREFIX id the client
prepends to the item name (`CItem::GetItemRareType` -> `GetItemPrefix`; 1-8 are the
rare grades, 9 is "[Costume]", 10 "[Event]" ...). It also colours the name: 1-20 draw
sky-blue instead of the plain yellow. `import-weapon-tier.py --tier newwep` took its
twelve donors from QQ-iROSE's level-255 cash-shop rows, and `import-item.py` copied
every column but the STL key, so Arcidian Sword and its eleven siblings (rows
1368-1379) shipped as "[Costume] Arcidian Sword" (alpha test #2, 2026-09-22). They are
ordinary weapons here -- stats authored by the tier script, sold and dropped like any
other -- so the column is cleared. `import-item.py` now blanks it on every stat-copying
import, so a re-run of the tier cannot bring it back.

Motion type (game col 34) picks the animation set the character uses with the
weapon, independently of the item type: 1 = 1H sword, 3 = 1H blunt, 5 = 2H sword,
8 = 2H axe ... QQ authored Arcidian Sword (a 1H sword) on the 2H-sword set and Flesh
Reaver (a 2H sword) on the 2H-axe set, and both came through verbatim, so Arcidian
Sword was held two-handed. `MOTION` puts them on the set every other weapon of their
type uses.

Scope is the reviewed row set below; a row whose name does not match is refused.
Idempotent; `--dry-run` / `--verify` / `--restore` (backup in `build/weapon-tier-prefix/`,
outside `data/` because `pack.rs` bakes any stray file under it into the `.vfs`).
"""
import argparse
import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STB = os.path.join(ROOT, "data", "3DDATA", "STB", "LIST_WEAPON.STB")
BACKUP = os.path.join(ROOT, "build", "weapon-tier-prefix", "LIST_WEAPON.STB")

ROWS = {
    1368: b"Arcidian Sword", 1369: b"Befoul Hammer", 1370: b"Flesh Reaver",
    1371: b"Fortitude Spear", 1372: b"Befoul Axe", 1373: b"Fluctuator Bow",
    1374: b"Heat Ray Gun", 1375: b"Intrepid Staff", 1376: b"Intrepid Wand",
    1377: b"Juxtapose Katar", 1378: b"Arcidian Dual Hand", 1379: b"Dromosaur Bow Gun",
}
MOTION_COL = 34
MOTION = {1368: b"1", 1370: b"5"}  # row -> the motion set its weapon type uses


def load_importer():
    spec = importlib.util.spec_from_file_location("import_item", os.path.join(HERE, "import-item.py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [sys.argv[0]]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = saved
    return mod


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not os.path.exists(BACKUP):
            sys.exit(f"no backup at {BACKUP}")
        shutil.copyfile(BACKUP, STB)
        print(f"restored {STB} from {BACKUP}")
        return

    imp = load_importer()
    _, _, rows, cols, data = imp.stb_read(STB)
    prefix_col = cols - 3  # data[] cells exclude the row-name column: STL key is cols-2
    todo = []
    for r, name in ROWS.items():
        if data[r][0].strip() != name:
            sys.exit(f"row {r} is {data[r][0]!r}, expected {name!r}; refusing")
        v = data[r][prefix_col].strip()
        if v and v != b"0":
            todo.append((r, name, prefix_col, v, b""))
        if r in MOTION and data[r][MOTION_COL].strip() != MOTION[r]:
            todo.append((r, name, MOTION_COL, data[r][MOTION_COL].strip(), MOTION[r]))

    if args.verify:
        for r, name, col, old, new in todo:
            print(f"DIFF row {r} {name.decode()} col {col}: {old.decode()!r} != {new.decode()!r}")
        print("verify:", "OK" if not todo else f"{len(todo)} cell(s) differ")
        sys.exit(0 if not todo else 1)

    if not todo:
        print("nothing to do; every reviewed cell is already in place")
        return
    for r, name, col, old, new in todo:
        what = "prefix" if col == prefix_col else "motion"
        print(f"row {r} {name.decode()}: {what} {old.decode() or '(blank)'} -> {new.decode() or '(blank)'}")
    if args.dry_run:
        print("dry run; nothing written")
        return

    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    if not os.path.exists(BACKUP):
        shutil.copyfile(STB, BACKUP)
        print(f"backup: {BACKUP}")
    for r, _, col, _, new in todo:
        imp.stb_set_cell(STB, r, col, new, False)
    _, _, _, _, data = imp.stb_read(STB)
    assert all(data[r][col].strip() == new for r, _, col, _, new in todo)
    print(f"wrote {len(todo)} cell(s); verified by re-read")


if __name__ == "__main__":
    main()
