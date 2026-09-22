"""Rewrite broken-English skill descriptions in LIST_SKILL_S.STL.

The English tooltip text is language block 1 of `data/3DDATA/STB/LIST_SKILL_S.STL`,
keyed by the STB's last column (`LSkill0921` for every rank of Healing). Only the
English block is touched; the other four languages are left as they are.

Why each rewrite (alpha test #2, 2026-09-22):

  * Healing (921-930, type 10, target filter 1 = party, radius 1300-2000): the server
    (`CObjCHAR::Skill_START_10_11`) heals the caster and every party member inside
    the radius. The old text -- "You can recover your and your party member's HP at
    the same time" -- was read as unclear/broken by testers.
  * Cure (931-940, type 11, target filter 3 = any friendly, range 2000): a single
    target heal, usable on yourself.

Idempotent: re-running finds the text already in place and writes nothing.
`--dry-run` prints the plan, `--verify` fails if any entry differs from the table,
`--restore` puts the pre-run file back from `build/skill-descriptions/`. Backups go
outside `data/` because `pack.rs` bakes any stray file under it into the `.vfs`.
"""
import argparse
import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STL = os.path.join(ROOT, "data", "3DDATA", "STB", "LIST_SKILL_S.STL")
BACKUP_DIR = os.path.join(ROOT, "build", "skill-descriptions")
ENGLISH = 1

TEXT = {
    b"LSkill0921": b"Restores your HP, and the HP of every party member near you.",
    b"LSkill0931": b"Restores the HP of the targeted character. Can be cast on yourself.",
}


def load_stl_codec():
    spec = importlib.util.spec_from_file_location("azn", os.path.join(HERE, "add-zone-name.py"))
    mod = importlib.util.module_from_spec(spec)
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = saved
    return mod.stl_read, mod.stl_write


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    backup = os.path.join(BACKUP_DIR, "LIST_SKILL_S.STL")
    if args.restore:
        if not os.path.exists(backup):
            sys.exit(f"no backup at {backup}")
        shutil.copyfile(backup, STL)
        print(f"restored {STL} from {backup}")
        return

    stl_read, stl_write = load_stl_codec()
    keys, langs = stl_read(STL)
    index = {k: i for i, (k, _) in enumerate(keys)}
    missing = [k for k in TEXT if k not in index]
    if missing:
        sys.exit(f"keys not in STL: {missing}")

    changes = []
    for key, desc in TEXT.items():
        name, old = langs[ENGLISH][index[key]]
        if old != desc:
            changes.append((key, name, old, desc))

    if args.verify:
        for key, name, old, desc in changes:
            print(f"DIFF {key.decode()} ({name.decode()}): {old.decode()!r} != {desc.decode()!r}")
        print("verify:", "OK" if not changes else f"{len(changes)} entries differ")
        sys.exit(0 if not changes else 1)

    if not changes:
        print("nothing to do; all descriptions already in place")
        return
    for key, name, old, desc in changes:
        print(f"{key.decode()} ({name.decode()}):\n   - {old.decode()}\n   + {desc.decode()}")
    if args.dry_run:
        print("dry run; nothing written")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(backup):
        shutil.copyfile(STL, backup)
        print(f"backup: {backup}")
    for key, name, old, desc in changes:
        langs[ENGLISH][index[key]] = (name, desc)
    stl_write(STL, keys, langs)

    keys2, langs2 = stl_read(STL)
    for key, desc in TEXT.items():
        assert langs2[ENGLISH][index[key]][1] == desc, key
    print(f"wrote {len(changes)} description(s) to {STL}; verified by re-read")


if __name__ == "__main__":
    main()
