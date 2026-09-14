"""Import a monster's skill kit from a reference dump, with its effect chain.

The 667 Oro import brought the monsters and kept RoseZA's AI files for them, but
never the *skills* those AI files cast: `OR_THORNIE.AIP` (Fearsome Terrasaurus
King, LIST_NPC 2265) casts 3603 "Charge" and 3604 "Fireball", both blank rows in
our LIST_SKILL. The result was a boss that played a casting animation for nothing
(and, until the client learned to present a pre-empted swing, ate the damage of
the swing it interrupted -- see `audit-ai-skill-refs.py`). This script is the
other half of that audit: instead of stripping the cast, bring the skill in.

What a monster skill needs (traced from io_skill.h and the client consumers)
---------------------------------------------------------------------------
  LIST_SKILL row      cols 0-86 (ours has 87 columns; RoseZA has 114, the rest is
                      newer-client data we do not read)
  FILE_EFFECT rows    cols 56/59/62/65 casting effects, 74 hit effect, 77/80 hit
                      dummy effects -> `g_pEffectLIST->Add_EffectWithIDX`
  FILE_SOUND rows     cols 58/61/64/67 casting, 73 bullet fire, 76 hit, 79/82
                      hit dummy -> `g_pSoundLIST->IDX_PlaySound3D`
  LIST_EFFECT row     col 71 SKILL_BULLET_NO -> `EFFECT_BULLET_NORMAL(I)` is
                      LIST_EFFECT col 11 (a FILE_EFFECT row), cols 9/10 the hit
                      effects, 13-15 move type / bullet type / speed, 16/17 sounds
  the .eft files and, transitively, their .PTL / texture / mesh files
                      (`import-oro.py: effect_chain`)
  the monster's CHR   the cast motion comes from the AI action's nMotion, not from
                      the skill row (CObjMOB::GetANI_Casting == m_cSkillMotionIDX,
                      the action motion is that +1) -- `import-oro-667.py` step 3h
                      already proved those slots animate on this model.

Every index above resolves to the same row in our tables as in RoseZA's, because
our FILE_EFFECT / FILE_SOUND / LIST_EFFECT are the same lineage: the survey for
this boss found identical paths at 95, 71, 1035 (effects), 67, 91, 93, 148, 1121
(sounds), and *blank* rows at exactly the indices the new skills need (FILE_EFFECT
1881-1884, LIST_EFFECT 476). So rows are written **in place at the source index**,
and the script refuses if a needed row is occupied by something else -- that is
the signal that a future dump's namespace has drifted and the row needs re-pointing
(the Artisan recipe, `import-artisan-skill.py`).

Damage is deliberately NOT copied
---------------------------------
RoseZA's SKILL_POWER (Fireball 3500, Charge 2000) is sized for RoseZA's stat
scale, the same way the monsters' HP/ATK were before `rebalance-oro-667.py`.
Through `CCal::Get_SkillDAMAGE` (monster branch) against a synthetic level-240
Knight (balance-sim.py `make("Knight", 240)`: 3918 HP, DEF 2004, RES 1060) they
would deal ~7250 and ~4350 -- an instant kill next to the boss's ~330 normal swing.
Two things fix the scale:

  * Our own monster attack skills (every AIACT24 cast in our .aip files, 39
    rows) run SKILL_POWER 25-100, median 50; the highest damage-dealing one is
    Tornado at 501.
  * For a 2900-ATK boss the *weapon* formula (SKILL_DAMAGE_TYPE 1) is dominated by
    the `(power + atk*0.2) * (atk+60)` term: even power 0 lands ~1400 on that
    Knight (36% of HP), and 667's Charge is authored as type 1. So both skills use
    the magic formula (type 2), which is linear in power.

    The first cut (450 / 350) was sized on balance-sim's synthetic Knight and came
    out 2x too hot on the real tester (6102 HP, evidently far less DEF/RES than
    the synthetic block): Fireball 2865-2923, Charge 2174-2290, i.e. 6.4 damage
    per power point on both. The powers are therefore calibrated on the measured
    ratio, to about a quarter (Fireball) and a fifth (Charge) of that tester's HP:

        Fireball  power 230  ->  ~1500 measured-scale   (vs its 470-620 swing)
        Charge    power 190  ->  ~1200 measured-scale

    A well-geared level-240 character takes roughly half of that. `--power`
    overrides per skill for tuning; `scripts/balance-sim.py`'s
    `magic_skill_damage` re-derives the synthetic side.

The status columns (11/12) are cleared: 667 attaches LIST_STATUS 150/120 there and
our status table has 62 rows. Everything else in the row is the source's.

Usage
-----
    python scripts/import-monster-skills.py --selftest
    python scripts/import-monster-skills.py --dry-run
    python scripts/import-monster-skills.py            # write
    python scripts/import-monster-skills.py --verify
    python scripts/import-monster-skills.py --restore  # from build/monster-skills/

Then put the AI casts back:  `audit-ai-skill-refs.py --restore` followed by
`audit-ai-skill-refs.py` again -- with the rows present only the *other* files'
dangling casts are stripped, and `--verify` on both audits must pass. Servers
cache the STBs at startup: restart the gameserver, and ship the client the new
files (loose or baked).

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
SRC = r"C:\Users\Thomas\Desktop\Testclients\RoseZA test client\data"

STB = os.path.join("3DDATA", "STB")
BACKUP_DIR = os.path.join(REPO, "build", "monster-skills")
MANIFEST = "manifest.json"

# skill id -> what we change from the source row. Everything else is copied.
SKILLS = {
    3603: dict(name="Charge", dmgtype=2, power=190),
    3604: dict(name="Fireball", dmgtype=2, power=230),
}

# LIST_SKILL columns (io_skill.h)
C_NAME, C_TYPE, C_POWER, C_STATUS1, C_STATUS2, C_DMGTYPE = 0, 5, 9, 11, 12, 15
C_BULLET = 71
EFFECT_COLS = (56, 59, 62, 65, 74, 77, 80)     # FILE_EFFECT rows
SOUND_COLS = (58, 61, 64, 67, 73, 76, 79, 82)  # FILE_SOUND rows
# LIST_EFFECT (bullet row) columns (stb.h)
BULLET_EFFECT_COLS = (9, 10, 11, 12)           # FILE_EFFECT rows
BULLET_SOUND_COLS = (16, 17)                   # FILE_SOUND rows


def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [fname]
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    finally:
        sys.argv = saved
    return m


oro = load("import_oro", "import-oro.py")   # Stb (set/to_bytes), effect_chain, rel_path


def ival(stb, r, c):
    v = stb.get(r, c).strip()
    return int(v) if v.lstrip(b"-").isdigit() else 0


def blank_row(stb, r):
    return r < stb.rows and not any(x.strip() for x in stb.d[r])


class Plan:
    """Everything the import will write, resolved before anything is touched."""

    def __init__(self, ours, src):
        self.ours, self.src = ours, src
        self.o = {n: oro.Stb(os.path.join(ours, STB, n)) for n in
                  ("LIST_SKILL.STB", "FILE_EFFECT.STB", "FILE_SOUND.STB", "LIST_EFFECT.STB")}
        self.s = {n: oro.Stb(os.path.join(src, STB, n)) for n in self.o}
        self.skill_rows = {}     # id -> cells
        self.effect_rows = {}    # FILE_EFFECT idx -> cells
        self.bullet_rows = {}    # LIST_EFFECT idx -> cells
        self.efts = set()
        self.problems = []
        for sid, spec in SKILLS.items():
            self._skill(sid, spec)

    # -- resolution ------------------------------------------------------
    def _need_effect(self, idx, why):
        if idx <= 0:
            return
        o, s = self.o["FILE_EFFECT.STB"], self.s["FILE_EFFECT.STB"]
        if idx >= s.rows or not s.get(idx, 1).strip():
            self.problems.append("%s: source FILE_EFFECT %d is empty" % (why, idx))
            return
        spath = s.get(idx, 1)
        self.efts.add(spath.decode("latin-1"))
        if idx < o.rows and o.get(idx, 1).strip():
            if o.get(idx, 1).strip().lower() != spath.strip().lower():
                self.problems.append("%s: FILE_EFFECT %d is %r here but %r in source"
                                     % (why, idx, o.get(idx, 1), spath))
            return
        if idx >= o.rows:
            self.problems.append("%s: FILE_EFFECT %d is past our table (%d rows)" % (why, idx, o.rows))
            return
        self.effect_rows[idx] = [s.get(idx, c) for c in range(o.cols)]

    def _need_sound(self, idx, why):
        if idx <= 0:
            return
        o, s = self.o["FILE_SOUND.STB"], self.s["FILE_SOUND.STB"]
        if idx >= o.rows or idx >= s.rows or o.get(idx, 0).strip().lower() != s.get(idx, 0).strip().lower():
            self.problems.append("%s: FILE_SOUND %d differs (%r vs %r)"
                                 % (why, idx, o.get(idx, 0), s.get(idx, 0)))

    def _need_bullet(self, idx, why):
        if idx <= 0:
            return
        o, s = self.o["LIST_EFFECT.STB"], self.s["LIST_EFFECT.STB"]
        if idx >= s.rows:
            self.problems.append("%s: source LIST_EFFECT %d missing" % (why, idx))
            return
        for c in BULLET_EFFECT_COLS:
            self._need_effect(ival(s, idx, c), "%s bullet %d col %d" % (why, idx, c))
        for c in BULLET_SOUND_COLS:
            self._need_sound(ival(s, idx, c), "%s bullet %d col %d" % (why, idx, c))
        if idx < o.rows and not blank_row(o, idx):
            same = all(o.get(idx, c).strip() == s.get(idx, c).strip() for c in range(min(o.cols, s.cols)))
            if not same:
                self.problems.append("%s: LIST_EFFECT %d is occupied here and differs" % (why, idx))
            return
        if idx >= o.rows:
            self.problems.append("%s: LIST_EFFECT %d is past our table (%d rows)" % (why, idx, o.rows))
            return
        self.bullet_rows[idx] = [s.get(idx, c) for c in range(o.cols)]

    def _skill(self, sid, spec):
        o, s = self.o["LIST_SKILL.STB"], self.s["LIST_SKILL.STB"]
        why = "skill %d" % sid
        if sid >= s.rows or not s.get(sid, C_TYPE).strip():
            self.problems.append("%s: not in source" % why)
            return
        if sid >= o.rows:
            self.problems.append("%s: past our LIST_SKILL (%d rows)" % (why, o.rows))
            return
        if not blank_row(o, sid):
            self.problems.append("%s: our row is occupied (%r)" % (why, o.get(sid, 0)))
            return
        cells = [s.get(sid, c) for c in range(o.cols)]
        cells[C_NAME] = spec["name"].encode("latin-1")
        cells[C_POWER] = str(spec["power"]).encode()
        cells[C_DMGTYPE] = str(spec["dmgtype"]).encode()
        cells[C_STATUS1] = b""
        cells[C_STATUS2] = b""
        self.skill_rows[sid] = cells
        for c in EFFECT_COLS:
            self._need_effect(ival(s, sid, c), "%s col %d" % (why, c))
        for c in SOUND_COLS:
            self._need_sound(ival(s, sid, c), "%s col %d" % (why, c))
        self._need_bullet(ival(s, sid, C_BULLET), why)

    # -- files ------------------------------------------------------------
    def files(self):
        """(rel, present_here) for every asset the effect chain needs."""
        deps = oro.effect_chain(sorted(self.efts), self.src)
        out = []
        for rel in sorted(deps, key=str.lower):
            if not os.path.isfile(oro.rel_path(self.src, rel)):
                self.problems.append("asset missing from source: %s" % rel)
                continue
            out.append((rel, os.path.isfile(oro.rel_path(self.ours, rel))))
        return out

    def report(self, files):
        for sid, cells in sorted(self.skill_rows.items()):
            print("   LIST_SKILL %4d  %-10s type %s dmgtype %s power %s bullet %s"
                  % (sid, cells[C_NAME].decode(), cells[C_TYPE].decode(), cells[C_DMGTYPE].decode(),
                     cells[C_POWER].decode(), cells[C_BULLET].decode() or "-"))
        for idx, cells in sorted(self.effect_rows.items()):
            print("   FILE_EFFECT %4d  %s" % (idx, cells[1].decode("latin-1")))
        for idx, cells in sorted(self.bullet_rows.items()):
            print("   LIST_EFFECT %4d  bullet fx %s hit %s/%s speed %s" %
                  (idx, cells[11].decode(), cells[9].decode(), cells[10].decode(), cells[15].decode()))
        new = [r for r, have in files if not have]
        print("   %d asset file(s) in the effect chain, %d to copy:" % (len(files), len(new)))
        for r in new:
            print("      %s" % r)


def write_manifest(root, man):
    bdir = BACKUP_DIR
    os.makedirs(bdir, exist_ok=True)
    json.dump(man, open(os.path.join(bdir, MANIFEST), "w"), indent=1)


def do_restore(root):
    mpath = os.path.join(BACKUP_DIR, MANIFEST)
    if not os.path.isfile(mpath):
        print("nothing to restore (%s not found)" % mpath)
        return 0
    man = json.load(open(mpath))
    for rel, b64 in sorted(man["stb"].items()):
        open(os.path.join(root, rel), "wb").write(base64.b64decode(b64))
        print("   restored %s" % rel)
    for rel in man["copied"]:
        p = oro.rel_path(root, rel)
        if os.path.isfile(p):
            os.remove(p)
            print("   removed  %s" % rel)
    os.remove(mpath)
    return 0


def verify(root):
    ok = True
    o = {n: oro.Stb(os.path.join(root, STB, n)) for n in ("LIST_SKILL.STB", "FILE_EFFECT.STB", "LIST_EFFECT.STB")}
    for sid, spec in SKILLS.items():
        sk = o["LIST_SKILL.STB"]
        good = (sk.get(sid, C_NAME) == spec["name"].encode("latin-1")
                and ival(sk, sid, C_POWER) == spec["power"]
                and ival(sk, sid, C_DMGTYPE) == spec["dmgtype"]
                and ival(sk, sid, C_TYPE) > 0)
        print("   LIST_SKILL %d %-9s %s" % (sid, spec["name"], "OK" if good else "MISSING/DIFFERS"))
        ok &= good
        for c in EFFECT_COLS:
            i = ival(sk, sid, c)
            if i and not o["FILE_EFFECT.STB"].get(i, 1).strip():
                print("      FILE_EFFECT %d blank" % i); ok = False
            if i:
                rel = o["FILE_EFFECT.STB"].get(i, 1).decode("latin-1")
                if not os.path.isfile(oro.rel_path(root, rel)):
                    print("      missing file %s" % rel); ok = False
        b = ival(sk, sid, C_BULLET)
        if b and blank_row(o["LIST_EFFECT.STB"], b):
            print("      LIST_EFFECT %d blank" % b); ok = False
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=DATA, help="our data dir (default: <repo>/data)")
    ap.add_argument("--source", default=SRC, help="reference data dir (default: RoseZA)")
    ap.add_argument("--power", action="append", default=[], metavar="ID=POWER",
                    help="override SKILL_POWER for one skill, e.g. 3604=400")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="prove the STB writer round-trips")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    for ov in a.power:
        sid, pw = ov.split("=")
        SKILLS[int(sid)]["power"] = int(pw)

    if a.restore:
        return do_restore(root)
    if a.verify:
        print("verify:")
        return 0 if verify(root) else 1

    print("self-test (the STB writer must reproduce every table byte-identically):")
    for n in ("LIST_SKILL.STB", "FILE_EFFECT.STB", "FILE_SOUND.STB", "LIST_EFFECT.STB"):
        p = os.path.join(root, STB, n)
        same = oro.Stb(p).to_bytes() == open(p, "rb").read()
        print("   %-18s %s" % (n, "OK" if same else "FAIL"))
        if not same:
            return 1
    if a.selftest:
        return 0

    plan = Plan(root, a.source)
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

    if os.path.isfile(os.path.join(BACKUP_DIR, MANIFEST)):
        print("\nABORT: %s exists -- --restore first, or delete it to re-run on top" % os.path.join(BACKUP_DIR, MANIFEST))
        return 1
    man = {"stb": {}, "copied": []}
    for n in ("LIST_SKILL.STB", "FILE_EFFECT.STB", "LIST_EFFECT.STB"):
        rel = os.path.join(STB, n).replace("\\", "/")
        man["stb"][rel] = base64.b64encode(open(os.path.join(root, STB, n), "rb").read()).decode("ascii")
    for sid, cells in plan.skill_rows.items():
        for c, v in enumerate(cells):
            plan.o["LIST_SKILL.STB"].set(sid, c, v)
    for idx, cells in plan.effect_rows.items():
        for c, v in enumerate(cells):
            plan.o["FILE_EFFECT.STB"].set(idx, c, v)
    for idx, cells in plan.bullet_rows.items():
        for c, v in enumerate(cells):
            plan.o["LIST_EFFECT.STB"].set(idx, c, v)
    for n in ("LIST_SKILL.STB", "FILE_EFFECT.STB", "LIST_EFFECT.STB"):
        open(os.path.join(root, STB, n), "wb").write(plan.o[n].to_bytes())
        print("   wrote %s" % n)
    for rel, have in files:
        if have:
            continue
        d = oro.rel_path(root, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(oro.rel_path(a.source, rel), d)
        man["copied"].append(rel)
    print("   copied %d file(s)" % len(man["copied"]))
    write_manifest(root, man)
    print("\nverify:")
    return 0 if verify(root) else 1


if __name__ == "__main__":
    sys.exit(main())
