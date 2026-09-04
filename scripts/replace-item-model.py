#!/usr/bin/env python3
"""Swap the model of an item we already imported, keeping its id.

WHY THIS EXISTS
---------------
Some source models are placeholders. Jrose's `mant_dammy_m.zms` -- "dammy" is
dummy -- is 3 vertices in a bounding box 0.0014 units across, and 76 of their
back rows use it: their mantles are drawn by some other system (the textures live
under `3Ddata/NPC/MANT/`, not with the avatar art), and the back slot only holds a
stand-in. Imported faithfully, it equips and shows nothing.

Removing such an item is the wrong repair when it is not the last row: item ids
are baked into inventories, banks, drop tables and shop stock, so dropping row 997
would renumber everything above it. Replacing the model in place keeps every id,
and the STB row, the STL text and the icon all keep pointing where they did.

`import-item.py --art-only` now refuses a source object whose every part is
degenerate, so this should not be needed again for that reason -- but "the model
turned out to be wrong" is a general enough problem to keep a tool for.

WHAT IT DOES
------------
Rewrites one object of a model ZSC from a source dump's object, remapping mesh,
material and effect indices exactly as the importer does (reusing entries we
already hold, appending the ones we do not), and copies any newly referenced
assets. The object count never changes, so no index moves.

Optionally rewrites the item's name and description (`--name` / `--desc`, which
update both the STL the client reads and STB column 0 the server reports) and its
icon (`--copy-icon`).

**The rewrite is proved before it is used.** --selftest re-serialises the whole
ZSC with no substitution and asserts the result is byte-identical to the file on
disk; a plain run does that check too before writing anything. Objects are
variable-length records, so a writer that is subtly wrong would corrupt every
object after the one it touched, and that failure would not look like a bad write
-- it would look like unrelated items losing their models.
"""
import argparse
import importlib.util
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OURS = "data"


def load(fname, mod):
    spec = importlib.util.spec_from_file_location(mod, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ser_object(obj):
    """Serialise one ZSC object record.

    Mirrors Zsc.__init__'s reader exactly, including that dummies and the
    bounding box are only present when the object has parts.
    """
    cyl, parts, dummies, bb = obj
    out = [cyl, struct.pack("<H", len(parts))]
    for mid, tid, props in parts:
        out += [struct.pack("<HH", mid, tid), props]
    if parts:
        out.append(struct.pack("<H", len(dummies)))
        for a, props in dummies:
            out += [a, props]
        out.append(bb)
    return b"".join(out)


def ser_zsc(ii, z, meshes, materials, effects, objects):
    out = [struct.pack("<H", len(meshes))]
    out += [m + b"\x00" for m in meshes]
    out.append(struct.pack("<H", len(materials)))
    out += [p + b"\x00" + flags for p, flags in materials]
    out.append(struct.pack("<H", len(effects)))
    out += [e + b"\x00" for e in effects]
    out.append(struct.pack("<H", len(objects)))
    out += [ser_object(o) for o in objects]
    return b"".join(out)


def roundtrip_ok(ii, path):
    z = ii.Zsc(path)
    rebuilt = ser_zsc(ii, z, z.meshes, z.materials, z.effects, z.objects)
    original = z.d[:z.obj_end]          # trailing junk some editors leave is not ours to keep
    return rebuilt == original, len(rebuilt), len(original)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", default="back")
    ap.add_argument("--id", type=int, help="OUR item id whose model is replaced")
    ap.add_argument("--source", help="source data directory")
    ap.add_argument("--source-row", type=int, help="object index in the source's model ZSC")
    ap.add_argument("--name", help="also rewrite the item name (STL + STB col 0)")
    ap.add_argument("--desc", help="also rewrite the item description (STL)")
    ap.add_argument("--copy-icon", action="store_true",
                    help="port the source row's icon into our atlas and repoint the STB")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="only prove the ZSC writer round-trips byte-identically")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(OURS, "3DDATA")):
        sys.exit("run from the repo root (data/3DDATA not found)")
    ii = load("import-item.py", "import_item")
    if args.type not in ii.TYPES:
        sys.exit("unknown type %s" % args.type)
    _tnum, stb_rel, zsc_rels, stl_rel, prefix, _cols = ii.TYPES[args.type]

    if args.selftest:
        bad = 0
        for rel in zsc_rels + (ii.FIELD_ZSC_REL,):
            p = os.path.join(OURS, rel)
            ok, a, b = roundtrip_ok(ii, p)
            print("  %-40s %s (%d vs %d bytes)"
                  % (os.path.basename(rel), "identical" if ok else "*** DIFFERS ***", a, b))
            bad += 0 if ok else 1
        sys.exit(bad)

    for req in ("id", "source", "source_row"):
        if getattr(args, req) is None:
            sys.exit("--%s is required" % req.replace("_", "-"))

    for rel in zsc_rels:
        ours_path = os.path.join(OURS, rel)
        ok, _a, _b = roundtrip_ok(ii, ours_path)
        if not ok:
            sys.exit("%s does not round-trip through the writer -- refusing to touch it"
                     % os.path.basename(rel))

        z = ii.Zsc(ours_path)
        if not 0 <= args.id < len(z.objects):
            sys.exit("id %d out of range (%s holds %d objects)"
                     % (args.id, os.path.basename(rel), len(z.objects)))
        src = ii.Zsc(os.path.join(args.source, rel))
        if not 0 <= args.source_row < len(src.objects):
            sys.exit("source row %d out of range (%d objects)"
                     % (args.source_row, len(src.objects)))

        # Reuse the importer's remapping by appending, then move the appended
        # object onto the target index and drop the tail. That keeps one copy of
        # the index-remapping logic rather than a second, subtly different one.
        appended_idx, files_needed, blob = ii.zsc_build_append(
            ours_path, src, args.source_row, args.source, True)
        # Zsc only parses from a path, so the candidate goes through a temp file
        # rather than being re-implemented against a buffer. It is removed in the
        # finally below, and it lives beside the ZSC where a stray .bak would --
        # so if this ever aborts hard, delete it before baking (pack.rs has no
        # extension filter).
        open_tmp = os.path.join(OURS, rel + ".replace-tmp")
        with open(open_tmp, "wb") as fh:
            fh.write(blob)
        try:
            z2 = ii.Zsc(open_tmp)
            objects = list(z2.objects)
            new_obj = objects[appended_idx]
            old = z.objects[args.id]
            objects = objects[:-1]
            objects[args.id] = new_obj
            out = ser_zsc(ii, z2, z2.meshes, z2.materials, z2.effects, objects)
        finally:
            os.remove(open_tmp)

        print("%s: object %d  %d part(s) -> %d part(s)"
              % (os.path.basename(rel), args.id, len(old[1]), len(new_obj[1])))
        for mid, tid, _p in new_obj[1]:
            print("    mesh %s" % ii.norm(z2.meshes[mid]))
        if not args.dry_run:
            with open(ours_path, "wb") as fh:
                fh.write(out)
            check = ii.Zsc(ours_path)
            assert len(check.objects) == len(z.objects), "object count changed"
            assert check.objects[args.id][1], "replacement object has no parts"
        ii.copy_assets(files_needed, args.source, args.dry_run)

    # name / description / icon
    if args.name or args.desc or args.copy_icon:
        stb_path = os.path.join(OURS, stb_rel)
        _d, _o, rows, cols, data = ii.stb_read(stb_path)
        key = data[args.id][cols - 2]
        if args.copy_icon:
            _sd, _so, _sr, _sc, sdata = ii.stb_read(os.path.join(args.source, stb_rel))
            new_icon = ii.copy_source_icon(args.source,
                                           int(sdata[args.source_row][9] or b"0"),
                                           "%s%d" % (prefix.lower(), args.id), args.dry_run)
            ii.stb_set_cell(stb_path, args.id, 9, str(new_icon), args.dry_run)
        if args.name:
            ii.stb_set_cell(stb_path, args.id, 0,
                            args.name.encode("euc-kr", "replace"), args.dry_run)
        if args.name or args.desc:
            stl_path = os.path.join(OURS, stl_rel)
            keys, langs = ii.stl_read(stl_path)
            hit = [i for i, (k, _n) in enumerate(keys) if k == key]
            if not hit:
                sys.exit("STL has no key %s" % key.decode("ascii", "replace"))
            i = hit[0]
            for entries in langs:
                n, d = entries[i]
                entries[i] = (args.name.encode("utf-8") if args.name else n,
                              args.desc.encode("utf-8") if args.desc else d)
            ii.stl_write(stl_path, keys, langs, args.dry_run)
            print("text: %s -> %r" % (key.decode(), args.name or "(desc only)"))

    print("\n%s" % ("DRY RUN - nothing written." if args.dry_run
                    else "done.  Re-run add-dds-mipmaps.py, then re-bake."))


if __name__ == "__main__":
    main()
