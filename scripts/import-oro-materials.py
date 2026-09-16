"""Import Oro's monster-part materials from RoseZA, so its drop tables have
something of their own to pay out.

Nine materials. Six are written **in place at RoseZA's row numbers** because
our `LIST_NATURAL` is the same lineage and those rows are blank here: the 667
import took monsters, maps and NPCs but no items, and the earlier RoseZA
import never got as far as loot. Three move, because their RoseZA rows are not
free here (see below). Each is named for the family that drops it, which is
what lets add-oro-drops.py give every species a signature material instead
of the same metal everywhere:

    RoseZA  ours  name                family
    260     260   Dry Scale           Scorpio / Mastyx / Terrasaurus
    266     287   Broken Rune Piece   Scorpio / Scarab / Scavenger
    268     268   Asper Fang          Asper
    269     269   Asper Tongue        Asper
    273     285   Snapper Beak        Snapper
    274     286   Snapper Tail        Snapper
    275     275   Devourer Plate      Devourer
    276     276   Devourer Horn       Devourer
    277     277   Nymph Essence       Scavenger

Same recipe as import-karkia-materials.py: import-item.py `--art-only` clones
every stat column from our Chromium (12:8) and takes only the icon (extracted
from RoseZA's atlas and appended to ours -- icon indices are never portable
across dumps), then `--price` restores RoseZA's tier. Names and descriptions
are RoseZA's own English text (language block 1 of its STL; block 0 is
Korean, which is why `--art-only` cannot take them itself).

**A blank STB row is not a free row** (import-karkia-materials.py's lesson).
Rows 273 and 274 are blank in our STB but `LIST_NATURAL_S.STL` still names
them "Archangel Feather" and "Archdevil Feather", and drop tables 63-71
reference both -- retail items whose STB rows were lost, not free space. The
two Snapper parts therefore go to 285/286, which are blank in the STB, absent
from the STL and referenced by nothing. Row 266 carries an STL key here too
("Not used / you can sell this to npc." in every language -- a retail
placeholder), and import-item.py refuses a row whose key exists, so the rune
piece goes to 287 by the same rule rather than special-casing the tool.

All nine sit below the 999 ceiling, so they can be dropped, quest-granted and
used as recipe inputs (the craft tables do not use them yet; that is a later
pass).

Idempotent: `--target-row` refuses a row that already carries a name, so a
re-run stops instead of duplicating. `--dry-run` / `--verify`.

After running: restart the servers and re-bake the VFS. Spawn one with
`/item 12:<id>` (GM access 2048).
"""
import argparse
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE = r"C:\Users\Thomas\Desktop\Testclients\RoseZA test client\data"
TEMPLATE = 8            # our Chromium: a plain stackable material

# (RoseZA row, our row, name, price, description) -- text is RoseZA's English
MATERIALS = [
    (260, 260, "Dry Scale", 845,
     "A sliver of reptilian skin from an animal that has lived in the arid "
     "desert for a long period of time."),
    (266, 287, "Broken Rune Piece", 845,
     "What looks like a rune stone, but it appears to have been destroyed."),
    (268, 268, "Asper Fang", 1045,
     "A deadly weapon, this is the sharp tooth of a dangerous Asper."),
    (269, 269, "Asper Tongue", 1155,
     "Still dripping saliva, this is the digestive muscle from the mouth of "
     "an Asper."),
    (273, 285, "Snapper Beak", 600,
     "Powerful jaws that are capable of tearing flesh quite badly."),
    (274, 286, "Snapper Tail", 1045,
     "This saw-edged tail is quite long and resembles that of a kaiman."),
    (275, 275, "Devourer Plate", 845,
     "This piece of hard shell helped protect the body of a Devourer."),
    (276, 276, "Devourer Horn", 1270,
     "This is the lethal projection of bone and skin from a Devourer's head."),
    (277, 277, "Nymph Essence", 800,
     "Magical dust that falls from the wings of a Nymph."),
]


def run(m, dry):
    src_row, row, name, price, desc = m
    cmd = [sys.executable, os.path.join(HERE, "import-item.py"),
           "--type", "natural", "--source", SOURCE,
           "--source-row", str(src_row), "--target-row", str(row),
           "--art-only", "--template-row", str(TEMPLATE),
           "--name", name, "--desc", desc,
           "--price", str(price), "--copy-icon"]
    if dry:
        cmd.append("--dry-run")
    env = dict(os.environ, PYTHONIOENCODING="utf-8:replace")
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def load_reader():
    spec = importlib.util.spec_from_file_location(
        "rd", os.path.join(HERE, "rose-data-reader.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify():
    rd = load_reader()
    nat = rd.Stb(os.path.join(ROOT, "data", "3DDATA", "STB", "LIST_NATURAL.STB"),
                 "utf-8")
    bad = []
    for _s, row, name, price, _d in MATERIALS:
        if row >= nat.rows:
            bad.append("%d: past the end of the table" % row)
            continue
        got = rd.scrub(nat.s(row, 0)).strip()
        if got != name:
            bad.append("%d: name is %r, want %r" % (row, got, name))
        elif nat.i(row, 5) != price:
            bad.append("%d %s: price is %d, want %d"
                       % (row, name, nat.i(row, 5), price))
        elif nat.i(row, 9) <= 0:
            bad.append("%d %s: no icon" % (row, name))
    print("%d materials; %d problem(s)%s"
          % (len(MATERIALS), len(bad), (":\n  " + "\n  ".join(bad[:8])) if bad else ""))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        return verify()

    done, skipped, failed = 0, 0, []
    for m in MATERIALS:
        rc, out = run(m, args.dry_run)
        tag = "would import" if args.dry_run else "imported"
        if rc == 0:
            done += 1
            print("  %-14s %-4d %s" % (tag, m[1], m[2]))
        elif "refusing to overwrite" in out:
            skipped += 1
            print("  %-14s %-4d %s" % ("already there", m[1], m[2]))
        else:
            failed.append((m[1], m[2]))
            print("  %-14s %-4d %s\n     %s"
                  % ("FAILED", m[1], m[2], out.strip()[-400:]))
    print("\n%d %s, %d already present, %d failed"
          % (done, "planned" if args.dry_run else "imported", skipped, len(failed)))
    if failed:
        return 1
    if not args.dry_run:
        return verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
