"""Strip AI skill casts (AIACT24) that name a skill missing from LIST_SKILL.STB.

Sibling of `audit-ai-monster-refs.py`, which it imports for the .aip container
codec (parse/build/round-trip self-test). One AI action type carries a skill
id: **24 "use skill on target/self"** --

    struct AIACT24 { DWORD dwSize; AITYPE Type; BYTE btTarget; short nSkill; short nMotion; };

default packing, so `nSkill` is the `<h` at offset 10 and `nMotion` at 12; every
record we ship is 16 bytes. Nothing between the .aip and the server validated the
id -- `F_AIACT24` handed it straight to `SetCMD_Skill2OBJ` -- so an imported AI
that names a skill nobody imported with it *casts a skill that does not exist*.

Why this is not cosmetic
------------------------
Found 2026-09-14 on Fearsome Terrasaurus King (LIST_NPC 2265). Its AI is RoseZA's
`OR_THORNIE.AIP`, deliberately kept by the 667 Oro import, and it casts 3603
"Charge" and 3604 "Fireball" from its attack-move and when-damaged patterns. Both
are blank rows in our LIST_SKILL. What happened:

  * The server accepted the cast, broadcast GSV_TARGET_SKILL, and `Skill_START`
    switched on SKILL_TYPE 0 -- no effect. Every client played the boss's casting
    motion for nothing: "a different animation that doesn't deal any damage".
  * That cast replaced the boss's *attack* motion on the client. The server had
    already applied that swing's damage (Attack_START applies at frame 0), so the
    client's 3 s orphan sweep discarded the event and folded the HP silently.
    Two consecutive discards (611 + 475 HP) followed by the killing blow (545)
    presented the avatar's death from a visible 1323 HP.

The code side is fixed on both ends: the client now presents a swing that the
attacker's own skill command pre-empts (`CObjCHAR::PresentPreemptedCombatSwing`),
and `F_AIACT24` refuses a skill id whose row is blank or out of range, warning
once. This script removes the *cause*: an action that can only ever be refused is
dead weight, and leaving it in reads as a kit the monster never actually has.
`import-oro-667.py` step 3h checks that every cast *animates* on the model
(`aip_skill_motions` / `chr_anim_audit`) but never that the skill row exists --
this is the missing half of that check.

What the dangling ids are (RoseZA / 667 LIST_SKILL), for the day they get imported
----------------------------------------------------------------------------------
  or_thornie.aip      3603 Charge        type 3 (attack-motion change), range 500, power 2000
                      3604 Fireball      type 6 (projectile magic), power 3500, bullet 476,
                                         casting fx 1882, skill fx 1883, hit fx 95, sfx 93/148
  or_gmdevourer1.aip  3609 AOE movement-speed reduction (667: "Dispell (3-8) Buffs"), type 12/8
                      3610 Slow (AOE)    type 8, duration 30
                      3611 Stun + Damage AOE, type 17, power 400
  inguz.aip           3044 (type 7 area magic, power 200, Korean name)
  kh_2676.aip         871  Voltage Jolt  type 6, power 440 (RoseZA)
  pengun.aip          2979 jump attack (long range), type 6, power 250
  penart.aip          2980 stun-damage jump attack (long range), type 6, power 200

`scripts/import-monster-skills.py` is the importer (Charge/Fireball were the
first, 2026-09-14): it resolves the effect/bullet/sound chain, writes the rows in
place at the source index (our tables are the same lineage as RoseZA's, so the
indices line up) and re-bases SKILL_POWER to our scale. **Ordering dependency:**
after importing, `--restore` this script's backups so the casts come back, then
re-run it -- with the rows present only the remaining dangling casts are
stripped. The restore is whole-file, so do it before re-running, not after.

What it does
------------
Removes the offending action record from its event and decrements that event's
action count; everything else in the file is copied through byte-for-byte (the
codec's `--selftest` proves the rewrite round-trips every .aip before any is
touched). Backups go to `build/ai-skill-refs/manifest.json`, never beside the
.aip -- `pack.rs` filters only hidden entries and `pack.ps1` hard-errors on any
`.bak` under data/.

`data/` is gitignored, so this file is the only committed record of the change.
"""

import argparse
import base64
import importlib.util
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

AIACT24 = 0x19 | 0x0B000000  # type index 25 == "act 24" in the tool's 1-based numbering
TARGET_OFF, SKILL_OFF, MOTION_OFF = 8, 10, 12

SKILL_STB = os.path.join("data", "3DDATA", "STB", "LIST_SKILL.STB")
BACKUP_DIR = os.path.join("build", "ai-skill-refs")
MANIFEST = "manifest.json"

TARGET_LABEL = {0: "cond-char", 1: "cur-target", 2: "self"}


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mon = load("audit-ai-monster-refs")  # parse_aip / build_aip / aip_files / selftest
rd = load("rose-data-reader")


# --------------------------------------------------------------------------- #
# LIST_SKILL


def load_skill_rows(root):
    """True per row when the row is entirely blank (every cell empty)."""
    stb = rd.Stb(os.path.join(root, SKILL_STB))
    return [all(not stb.get(r, c) for c in range(stb.cols)) for r in range(stb.rows)]


def skill_problem(blank, idx):
    if idx < 1 or idx >= len(blank):
        return "out of range (table has %d rows)" % len(blank)
    if blank[idx]:
        return "BLANK ROW"
    return None


# --------------------------------------------------------------------------- #
# actions


def act_skill(a):
    """(target, skill, motion) if this is a skill-use action, else None."""
    if len(a) < MOTION_OFF + 2:
        return None
    typ, = struct.unpack_from("<I", a, 4)
    if typ != AIACT24:
        return None
    skill, motion = struct.unpack_from("<hh", a, SKILL_OFF)
    return (a[TARGET_OFF], skill, motion)


def scan(root, blank):
    """[(path, [(pat_i, ev_i, act_i, target, skill, motion, why)])]"""
    todo = []
    for p in mon.aip_files(root):
        b = open(p, "rb").read()
        _hdr, _title, pats, _tail = mon.parse_aip(b)
        hits = []
        for pi, (_pn, evs) in enumerate(pats):
            for ei, (_en, _cs, acts) in enumerate(evs):
                for ai, a in enumerate(acts):
                    s = act_skill(a)
                    if not s:
                        continue
                    tgt, skill, motion = s
                    why = skill_problem(blank, skill)
                    if why is None:
                        continue
                    hits.append((pi, ei, ai, tgt, skill, motion, why))
        if hits:
            todo.append((p, hits))
    return todo


def strip(b, hits):
    hdr, title, pats, tail = mon.parse_aip(b)
    drop = {}
    for pi, ei, ai, *_rest in hits:
        drop.setdefault((pi, ei), set()).add(ai)
    newpats = []
    for pi, (pn, evs) in enumerate(pats):
        newevs = []
        for ei, (en, cs, acts) in enumerate(evs):
            kill = drop.get((pi, ei), set())
            newevs.append((en, cs, [a for ai, a in enumerate(acts) if ai not in kill]))
        newpats.append((pn, newevs))
    return mon.build_aip(hdr, title, newpats, tail)


def report(todo):
    for p, hits in todo:
        for _pi, _ei, _ai, tgt, skill, motion, why in hits:
            print("   %-28s skill %-5d (target %-10s motion %2d) %s"
                  % (os.path.basename(p), skill, TARGET_LABEL.get(tgt, tgt), motion, why))


def do_restore(root):
    bdir = os.path.join(root, BACKUP_DIR)
    mpath = os.path.join(bdir, MANIFEST)
    if not os.path.isfile(mpath):
        print("nothing to restore (%s not found)" % mpath)
        return 0
    man = json.load(open(mpath))
    n = 0
    for rel, rec in sorted(man["files"].items()):
        open(os.path.join(root, rel), "wb").write(base64.b64decode(rec["original"]))
        n += 1
    os.remove(mpath)
    print("restored %d file(s) from %s" % (n, bdir))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true", help="preview without writing")
    ap.add_argument("--verify", action="store_true", help="check that no dangling refs remain")
    ap.add_argument("--restore", action="store_true", help="undo from build/ai-skill-refs/")
    ap.add_argument("--selftest", action="store_true", help="prove the rewriter round-trips")
    a = ap.parse_args()
    root = os.path.abspath(a.root)

    if a.restore:
        return do_restore(root)

    print("self-test (the rewriter must reproduce every file byte-identically):")
    if not mon.selftest(root):
        print("\nABORT: rewriter is not byte-exact; nothing was touched.")
        return 1
    if a.selftest:
        return 0

    blank = load_skill_rows(root)
    todo = scan(root, blank)

    if a.verify:
        if todo:
            print("\nVERIFY FAILED: %d file(s) still carry dangling skill refs" % len(todo))
            report(todo)
            return 1
        print("\nALL CHECKS PASSED -- no AI action casts a missing skill.")
        return 0

    if not todo:
        print("\nnothing to do -- no AI action casts a missing skill.")
        return 0

    nrefs = sum(len(h) for _p, h in todo)
    print("\n%d dangling skill cast(s) in %d file(s):" % (nrefs, len(todo)))
    report(todo)

    if a.dry_run:
        print("\ndry run: nothing written")
        return 0

    bdir = os.path.join(root, BACKUP_DIR)
    os.makedirs(bdir, exist_ok=True)
    mpath = os.path.join(bdir, MANIFEST)
    man = json.load(open(mpath)) if os.path.isfile(mpath) else {"files": {}}

    for p, hits in todo:
        b = open(p, "rb").read()
        rel = os.path.relpath(p, root).replace("\\", "/")
        # Keep the *first* original seen, so a second run stays undoable to the
        # true pre-edit bytes rather than to an already-stripped file.
        man["files"].setdefault(rel, {})
        man["files"][rel].setdefault("original", base64.b64encode(b).decode("ascii"))
        man["files"][rel]["stripped"] = [
            {"pattern": pi, "event": ei, "action": ai, "target": tgt, "skill": skill,
             "motion": motion, "why": why}
            for pi, ei, ai, tgt, skill, motion, why in hits
        ]
        out = strip(b, hits)
        # Re-parse the result: exactly the flagged records must be gone and the
        # header / trailing bytes untouched.
        h0, _t0, pats_before, tail0 = mon.parse_aip(b)
        h1, _t1, pats_after, tail1 = mon.parse_aip(out)
        removed = sum(len(evs_b[ei][2]) - len(evs_a[ei][2])
                      for (_pn, evs_b), (_pn2, evs_a) in zip(pats_before, pats_after)
                      for ei in range(len(evs_b)))
        if removed != len(hits) or tail1 != tail0 or h1 != h0:
            print("ABORT: rewrite of %s did not remove exactly the flagged records" % rel)
            return 1
        open(p, "wb").write(out)
        print("   wrote %s (-%d action record(s))" % (rel, len(hits)))

    json.dump(man, open(mpath, "w"), indent=1)
    print("\nbackups + manifest: %s" % mpath)

    if scan(root, blank):
        print("VERIFY FAILED after write")
        return 1
    print("verified: no dangling skill casts remain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
