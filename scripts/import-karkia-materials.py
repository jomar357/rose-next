"""Import Karkia's materials from Jrose, as flavour now and craft inputs later.

Twenty-five materials at `LIST_NATURAL` rows 740-764. The selection is not
arbitrary: **every one of them is already named in dialog we have translated**,
or is the lesser tier of something that is. Belfa explains that Graphistone is
the forging reagent; Astraea's price lists ask for Starlight, four Tomes, the
Arcane Sigil, Black Iron Gears, the four Latin colour cores, Stella Libra and
Sol Niger Horns; Nagia's seal chain runs on Phil Tempest's magic stones and
seven Sacred Demon Crystals; Lowe pays in Starlight. Until now every one of
those was a name with nothing behind it.

--- why row 740 and not the end of the table

A packed item code is `type * 1000 + no` in three places that matter here:

    drop cells        CCal::Get_DropITEM
    quest rewards     REWD_001 -> tagBaseITEM::Init(int)
    recipe inputs     PRODUCT_NEED_ITEM_NO

so an item numbered **above 999 can be neither dropped, granted by a quest, nor
used in a craft**. (The wide form added for drops and shops does not reach these
three.) `LIST_NATURAL` is 981 rows, so appending -- which is all
`import-item.py` could do before -- leaves 19 usable slots and then walks
straight past the ceiling. `--target-row` was added for this.

**A blank STB row is not a free row.** Our data is a translated dump with gaps,
and rows 455-489 look empty in `LIST_NATURAL.STB` while
`LIST_NATURAL_S.STL` still names them -- "Yellow petals", "Big green herb",
"Perfect green herb". Those are retail materials whose STB rows were lost, and
writing over them would have destroyed the only surviving record of what they
were, then displayed Graphistone under a key that says Yellow petals. A row is
free only if it is blank in the STB **and** unnamed in the STL **and**
unreferenced by any drop cell, shop slot or recipe input. 478 rows pass all
three; 735-899 is the largest clean run, and 740-764 is taken from the middle
of it.

--- why --art-only

Jrose's `LIST_NATURAL_S.STL` is the legacy `I_NUM` dialect our strict reader
rejects, so no source cell can be read for the name anyway. `--art-only` clones
every stat column from one of our own rows and takes only the icon, which is
also the safe mode for a foreign schema. The template is Chromium (12:8), an
ordinary stackable material; `--price` then restores the tier that actually
distinguishes these from each other.

Idempotent by construction: a row that already carries a name is refused by
`--target-row`, so a re-run stops rather than duplicating. `--verify` checks
all 25 landed with the right name and price.

After running: restart the servers and re-bake the VFS. Spawn one with
`/item 12:<id>` (GM access 2048).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE = r"C:\Users\Thomas\Desktop\Testclients\Jrose"
TEMPLATE = 8            # our Chromium: a plain stackable material
FIRST_ROW = 740

# (jrose row, our row, name, price, description)
MATERIALS = [
    # -- the forge chain: Belfa and Astraea both spend these -------------------
    (1363, 740, "Graphistone", 50000,
     "A rare ore found only in the Tower of Despair. Karkia's smiths temper a "
     "weapon past its grade with it."),
    (1374, 741, "Starlight", 1000,
     "A mineral scarce even on Karkia. The Starsteel armourers will not work "
     "for anyone who cannot bring them some."),
    (1387, 742, "Black Iron Gear", 100,
     "A blackened cog of unknown make. Astraea takes them by the fifty."),
    # -- the four tomes and their lesser scrolls -------------------------------
    (1375, 743, "Scroll of Might", 300,
     "A rubbing of a stronger text. Raises the strength of what it is bound into."),
    (1376, 744, "Scroll of Reason", 300,
     "A rubbing of a stronger text. Raises the intellect of what it is bound into."),
    (1377, 745, "Scroll of the Water Mirror", 300,
     "A rubbing of a stronger text. Steadies what it is bound into."),
    (1378, 746, "Scroll of Gale", 300,
     "A rubbing of a stronger text. Quickens what it is bound into."),
    (1379, 747, "Tome of Might", 1000,
     "The full text the scroll was copied from. Armourers ask for fifty at a time."),
    (1380, 748, "Tome of Reason", 1000,
     "The full text the scroll was copied from. Armourers ask for fifty at a time."),
    (1381, 749, "Tome of the Water Mirror", 1000,
     "The full text the scroll was copied from. Armourers ask for fifty at a time."),
    (1382, 750, "Tome of Gale", 1000,
     "The full text the scroll was copied from. Armourers ask for fifty at a time."),
    (1383, 751, "Talisman of Enchantment", 300,
     "A charm that holds an enchantment in place, after a fashion."),
    (1384, 752, "Arcane Sigil of Enchantment", 1000,
     "The proper article, and the one an armourer will accept."),
    # -- Astraea's high tier ---------------------------------------------------
    (1432, 753, "Ruber Core", 100, "A red core. It answers to strength."),
    (1433, 754, "Caerula Core", 100, "A blue core. It answers to steadiness."),
    (1434, 755, "Viride Core", 100, "A green core. It answers to speed."),
    (1435, 756, "Flavus Core", 100, "A yellow core. It answers to the mind."),
    (1445, 757, "Stella Libra", 100,
     "A star-scale. The Starsteel armourers weigh a core against it before "
     "setting the metal."),
    (1446, 758, "Sol Niger Horn", 2000,
     "A horn of black sun. Ten will buy an armourer's whole attention."),
    # -- Nagia's seal chain ----------------------------------------------------
    (1350, 759, "Phil Tempest's Magic Stone", 500,
     "Cut from the storm itself. Nagia forges the key to the Infinite Prison "
     "from ten of them, and a cracked one is worth nothing."),
    (1351, 760, "Magic Stone Crystal", 800,
     "What is left when an incomplete Karkia is put down. It still hums."),
    (1349, 761, "Sacred Demon Crystal", 2000,
     "Seven of these will break the seal. Nagia does not say what happens then."),
    (1520, 762, "Fafnir's Magic Stone", 1137,
     "Prised from the ash-grey wyrm the surveyors summon out of their Lamp."),
    # -- two metals, for the crafting bench later -------------------------------
    (1352, 763, "Tamahagane", 500,
     "Jewel steel, folded and folded again. Rare on a world that has forgotten "
     "how to make it."),
    (1440, 764, "Stardust Lantern", 1500,
     "A lantern that burns powdered starlight. Cold to the touch."),
]


def run(m, dry):
    jrose_row, our_row, name, price, desc = m
    cmd = [sys.executable, os.path.join(HERE, "import-item.py"),
           "--type", "natural", "--source", SOURCE,
           "--source-row", str(jrose_row), "--target-row", str(our_row),
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
    import importlib.util
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
    for _j, row, name, price, _d in MATERIALS:
        if row >= nat.rows:
            bad.append("%d: past the end of the table" % row)
            continue
        got = rd.scrub(nat.s(row, 0)).strip()
        if got != name:
            bad.append("%d: name is %r, want %r" % (row, got, name))
        elif nat.i(row, 5) != price:
            bad.append("%d %s: price is %d, want %d"
                       % (row, name, nat.i(row, 5), price))
    over = [r for _j, r, _n, _p, _d in MATERIALS if r > 999]
    print("%d materials; %d problem(s)%s"
          % (len(MATERIALS), len(bad), (":\n  " + "\n  ".join(bad[:8])) if bad else ""))
    if over:
        print("!! %d rows above the 999 ceiling: %s" % (len(over), over))
    return 1 if bad or over else 0


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
            failed.append((m[1], m[2], out.strip().splitlines()[-1:]))
            print("  %-14s %-4d %s\n     %s"
                  % ("FAILED", m[1], m[2], out.strip()[-300:]))
    print("\n%d %s, %d already present, %d failed"
          % (done, "planned" if args.dry_run else "imported", skipped, len(failed)))
    if failed:
        return 1
    if not args.dry_run:
        print("rows %d-%d, all below the 999 ceiling so they can drop, be quest "
              "rewards and be recipe inputs" % (FIRST_ROW, MATERIALS[-1][1]))
        return verify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
