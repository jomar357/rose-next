#!/usr/bin/env python3
"""Give LIST_SUBWPN rows 301-305 real names instead of literal question marks.

WHAT THESE ROWS ARE
-------------------
They look broken -- column 0 reads `??????????`, there is no STL key, and DEF and
RES are empty -- and they sit in the middle of the shield list, so they read as
corrupt player gear. They are not.

They are **monster equipment**. Column 1 points into `WEAPON\\mobwpn\\`, and
LIST_NPC's "Left Hand Equip" column (game col 6) references them from **31
monsters**: Tirwin x7, Yeti Guard, Golden Yeti, Doonga Warrior and Captain,
Woopie King and Glutton, Rackie in four forms, Penguin Swordsman and Warrior,
Elec Ghost, Shaman Poltergeist, Moon Child, and Goblin Wizard (that one via the
right-hand column). Every ZSC object is intact and every mesh is present.

**So they must not be deleted.** Removing them strips the off-hand model from all
31, and they are not trailing rows anyway, so removing them would renumber every
shield above -- including the 35 imported on 2026-09-06.

Empty DEF/RES is correct too: monster equipment grants no player stats.

WHAT IS ACTUALLY WRONG
----------------------
Only the name. The bytes in column 0 are literal `?` (0x3F), not mojibake -- a
Korean name was lost in the translation pass that produced our data/, replaced
character by character with question marks.

It is harmless at runtime. These rows never enter an inventory, so no tooltip is
ever built; the client reads names from the STL (there is no key here, and
nothing looks one up); and the server's ITEM_NAME reads column 0 only for logs
and GM output. Nothing renders wrongly in game.

It is worth fixing anyway, because the rows are indistinguishable from real
breakage when read by a person or a tool -- which is exactly what happened: they
were reported as broken shields before anyone checked what referenced them.

Names below are derived from the model path in column 1, so they say what the row
actually is. Idempotent; --dry-run and --verify supported.
"""
import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OURS = "data"
STB_REL = os.path.join("3DDATA", "STB", "LIST_SUBWPN.STB")

# row -> (expected model-path fragment, new name). The fragment is checked before
# writing so this cannot rename the wrong row if the table ever shifts.
NAMES = {
    301: ("mob_raccoon",      "Mob Off-hand: Rackie"),
    302: ("mob_wolf",         "Mob Off-hand: Wolf"),
    303: ("mob_small_Goblin", "Mob Off-hand: Goblin"),
    304: ("mon_tyrantgarda",  "Mob Off-hand: Tyrant Garda"),
    305: ("mon_tirwin",       "Mob Off-hand: Tirwin Shield"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="report the current names and exit non-zero if any is unnamed")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(OURS, "3DDATA")):
        sys.exit("run from the repo root (data/3DDATA not found)")
    spec = importlib.util.spec_from_file_location("ii", os.path.join(HERE, "import-item.py"))
    ii = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ii)

    path = os.path.join(OURS, STB_REL)
    _d, _o, rows, cols, data = ii.stb_read(path)

    if args.verify:
        bad = 0
        for r, (_frag, want) in sorted(NAMES.items()):
            cur = data[r][0].decode("latin-1")
            ok = cur == want
            bad += 0 if ok else 1
            print("  row %d: %-32r %s" % (r, cur, "OK" if ok else "*** not named ***"))
        sys.exit(1 if bad else 0)

    changed = 0
    for r, (frag, want) in sorted(NAMES.items()):
        if not 0 <= r < len(data):
            sys.exit("row %d out of range (%d rows)" % (r, len(data)))
        model = data[r][1].decode("latin-1")
        if frag.lower() not in model.lower():
            sys.exit("row %d model path %r does not contain %r -- the table has shifted, "
                     "refusing to rename the wrong row" % (r, model, frag))
        cur = data[r][0].decode("latin-1")
        if cur == want:
            print("  row %d already named %r" % (r, want))
            continue
        print("  row %d %-22r -> %r   (%s)" % (r, cur, want, model))
        ii.stb_set_cell(path, r, 0, want.encode("euc-kr", "replace"), args.dry_run)
        changed += 1

    if not args.dry_run and changed:
        _d, _o, r2, c2, d2 = ii.stb_read(path)
        assert (r2, c2) == (rows, cols), "table shape changed -- that should be impossible"
        for r, (_frag, want) in NAMES.items():
            assert d2[r][0].decode("latin-1") == want, "row %d did not take" % r
        print("verified: %d row(s) renamed, table shape unchanged (%dx%d)"
              % (changed, r2 - 1, c2 - 1))
    print("\n%s" % ("DRY RUN - nothing written." if args.dry_run
                    else "done.  Restart the gameserver (it caches STBs) and re-bake."))


if __name__ == "__main__":
    main()
