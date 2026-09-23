"""Give Angelic Arrow and Vengeance Arrow a projectile (bullet rows from tsuki).

Symptom (alpha #2): shooting with "Angelic Arrow" (LIST_NATURAL 320) draws no
arrow at all. Vengeance Arrow (319) has the same defect and simply had not been
reported yet.

Cause: an arrow's projectile is `NATURAL_BULLET_NO` (LIST_NATURAL game col 17),
an index into LIST_EFFECT; that row names the bullet .eft (col 11), the hit
effects (9/10), move type / speed (13-15) and the fire/hit sounds (16/17). Our
two top-tier arrows point at LIST_EFFECT 597 and 600, and both rows are **blank**
here. `CObjAVT::Get_BulletNO` / `CObjUSER::Get_BulletNO` return the index, the
client builds a CBullet from an empty row and nothing is drawn.

Where the rows come from: our arrow rows 318-320 are NARose-era (the same
names and attack values as the tsuki dump), but the LIST_EFFECT rows they
reference never came with them. Every other reference dump (QQ, RoseZA, titan,
ruff, 139, 667, Evo, Jrose) has 597-600 blank as well and their 318-320 are
either blank or different arrows; **tsuki is the only dump that has them**:

  LIST_EFFECT 597  bullet arrow_effect_1.EFT (FILE_EFFECT 32), hit elect_hit_02
                   (97), critical hit_critical_01 (71), direction move, 3000
                   speed, bow sounds 1121/68 -- tsuki's own Angelic Arrow uses it
  LIST_EFFECT 600  bullet bandy_bow_02 (1335), hit _bow_hit_01 (1061), same
                   motion and sounds -- a plain bow bullet (tsuki re-pointed its
                   Vengeance Arrow to 295, a sibling row; we keep our 600)

Our FILE_EFFECT / FILE_SOUND / LIST_EFFECT are the same lineage as tsuki's: 71,
1061, 1335, 1121 and 68 hold identical entries in both, and FILE_EFFECT 32 / 97
are blank here, so every row is written **in place at the source index**. The
resolution, the refusal when an index is occupied by something different, and
the .eft -> .PTL -> texture walk are `import-monster-skills.py`'s `Plan`, reused
unchanged. Nothing else in our data references LIST_EFFECT 597 or 600.

  python scripts/import-arrow-bullets.py --dry-run
  python scripts/import-arrow-bullets.py
  python scripts/import-arrow-bullets.py --verify
  python scripts/import-arrow-bullets.py --restore

Undo: the two STBs are saved whole in `build/arrow-bullets/manifest.json` with
the list of copied asset files. As with any whole-file backup, `--restore` also
reverts any later edit to FILE_EFFECT/LIST_EFFECT made by another script, so run
every other verify afterwards.

Client-only data: LIST_EFFECT / FILE_EFFECT and the effect files are read by the
client alone, so rebake the VFS; no server restart is needed.

`data/` is gitignored, so this docstring is the only committed record of the change.
"""

import argparse
import base64
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(REPO, "data")
TSUKI = r"C:\Users\Thomas\Desktop\Testclients\tsuki"
BACKUP_DIR = os.path.join(REPO, "build", "arrow-bullets")
MANIFEST = os.path.join(BACKUP_DIR, "manifest.json")

# LIST_NATURAL row -> LIST_EFFECT bullet row it already points at
ARROWS = {
    319: ("Vengeance Arrow", 600),
    320: ("Angelic Arrow", 597),
}
C_NATURAL_BULLET = 17


def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [fname]
    try:
        spec.loader.exec_module(m)
    finally:
        sys.argv = saved
    return m


ms = load("import_monster_skills", "import-monster-skills.py")
oro, STB = ms.oro, ms.STB
TABLES = ("FILE_EFFECT.STB", "LIST_EFFECT.STB")


def plan_for(root):
    ms.SOURCES["tsuki"] = TSUKI
    plan = ms.Plan(root, [])
    plan.src = TSUKI
    plan.s = plan._tables("tsuki")
    nat = oro.Stb(os.path.join(root, STB, "LIST_NATURAL.STB"))
    for row, (name, bullet) in sorted(ARROWS.items()):
        if nat.get(row, 0) != name.encode("latin-1") or ms.ival(nat, row, C_NATURAL_BULLET) != bullet:
            plan.problems.append("LIST_NATURAL %d is %r -> %d here, expected %s -> %d"
                                 % (row, nat.get(row, 0), ms.ival(nat, row, C_NATURAL_BULLET), name, bullet))
            continue
        plan._need_bullet(bullet, "%s (natural %d)" % (name, row))
    # Walk assets only from the FILE_EFFECT rows we write. A row already present
    # here keeps our own .eft, which can differ from tsuki's (our _bow_hit_01.eft
    # uses the _spreas/_shine particles, tsuki's its own _bow_hit_01.ptl), so
    # following tsuki's copy would import particles nothing references.
    new = {cells[1].decode("latin-1").lower() for cells in plan.effect_rows.values()}
    plan.efts = {(src, rel) for src, rel in plan.efts if rel.lower() in new}
    return plan


def verify(root):
    ok = True
    fe = oro.Stb(os.path.join(root, STB, "FILE_EFFECT.STB"))
    le = oro.Stb(os.path.join(root, STB, "LIST_EFFECT.STB"))
    for row, (name, bullet) in sorted(ARROWS.items()):
        bad = []
        if ms.blank_row(le, bullet):
            bad.append("LIST_EFFECT %d blank" % bullet)
        else:
            for c in ms.BULLET_EFFECT_COLS:
                i = ms.ival(le, bullet, c)
                if not i:
                    continue
                rel = fe.get(i, 1).decode("latin-1")
                if not rel.strip():
                    bad.append("FILE_EFFECT %d blank" % i)
                elif not os.path.isfile(oro.rel_path(root, rel)):
                    bad.append("missing %s" % rel)
            if not ms.ival(le, bullet, 11):
                bad.append("LIST_EFFECT %d has no bullet effect" % bullet)
        print("   %-16s -> LIST_EFFECT %d  %s" % (name, bullet, "OK" if not bad else "; ".join(bad)))
        ok &= not bad
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=DATA, help="our data dir (default: <repo>/data)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)

    if a.restore:
        if not os.path.isfile(MANIFEST):
            print("nothing to restore (%s not found)" % MANIFEST)
            return 0
        man = json.load(open(MANIFEST))
        for rel, b64 in sorted(man["stb"].items()):
            open(os.path.join(root, rel), "wb").write(base64.b64decode(b64))
            print("   restored %s" % rel)
        for rel in man["copied"]:
            p = oro.rel_path(root, rel)
            if os.path.isfile(p):
                os.remove(p)
                print("   removed  %s" % rel)
        os.remove(MANIFEST)
        return 0
    if a.verify:
        print("verify:")
        return 0 if verify(root) else 1

    print("self-test (the STB writer must reproduce every table byte-identically):")
    for n in TABLES:
        p = os.path.join(root, STB, n)
        same = oro.Stb(p).to_bytes() == open(p, "rb").read()
        print("   %-18s %s" % (n, "OK" if same else "FAIL"))
        if not same:
            return 1

    plan = plan_for(root)
    files = plan.files()
    print("\nplan:")
    plan.report(files)
    if plan.problems:
        print("\nABORT, unresolved:")
        for p in plan.problems:
            print("   " + p)
        return 1
    if a.dry_run:
        print("\ndry run: nothing written")
        return 0
    if not plan.bullet_rows and not plan.effect_rows:
        print("\nnothing to write")
        return 0 if verify(root) else 1
    if os.path.isfile(MANIFEST):
        print("\nABORT: %s exists -- --restore first, or delete it to re-run on top" % MANIFEST)
        return 1

    man = {"stb": {}, "copied": []}
    for n in TABLES:
        rel = os.path.join(STB, n).replace("\\", "/")
        man["stb"][rel] = base64.b64encode(open(os.path.join(root, STB, n), "rb").read()).decode("ascii")
    for idx, cells in plan.effect_rows.items():
        for c, v in enumerate(cells):
            plan.o["FILE_EFFECT.STB"].set(idx, c, v)
    for idx, cells in plan.bullet_rows.items():
        for c, v in enumerate(cells):
            plan.o["LIST_EFFECT.STB"].set(idx, c, v)
    for src, rel, have in files:
        if have:
            continue
        d = oro.rel_path(root, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(oro.rel_path(src, rel), d)
        man["copied"].append(rel)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    json.dump(man, open(MANIFEST, "w"), indent=1)
    for n in TABLES:
        open(os.path.join(root, STB, n), "wb").write(plan.o[n].to_bytes())
        print("   wrote %s" % n)
    print("   copied %d file(s)" % len(man["copied"]))
    print("\nverify:")
    return 0 if verify(root) else 1


if __name__ == "__main__":
    sys.exit(main())
