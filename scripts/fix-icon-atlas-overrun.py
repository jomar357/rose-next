#!/usr/bin/env python3
"""Move item icons off atlas cells that hang over the edge of their sheet.

THE DEFECT
----------
ITEM1.TSI lays each 512x512 sheet out as a 13x13 grid of 40px cells. 13 * 40 is
520, so the last column (x 480..520) and the last row (y 480..520) hang **8px**
off the texture. The engine's default texture address mode is WRAP
(ZZ_TADDRESS_WRAP, zz_interface.h), so those 8px sample from the opposite edge of
the sheet and the icon draws with a torn strip of a neighbouring cell down its
right side or along its bottom. 8 of 40 -- exactly a fifth of the icon, which is
what it looks like on screen.

The geometry is retail's, not ours. Every shipped sheet has the same 25 bad cells
(13 in the last column + 13 in the last row - 1 shared corner) and retail paints
art into all of them. It never shows, because **no item in the shipped tables
points at one**: of 1,953 retail icon indices actually referenced, zero are bad
cells. The defect has been dormant in the data since the game shipped.

What woke it up was our own allocator. add-item-icon.py filled cells densely from
0, so once an extension sheet passed cell 155 it started handing out bad cells,
and imported items landed on them. That is why this shows on imports (RoseZA's
and Jrose's alike) and never on retail gear.

WHAT THIS DOES
--------------
Relocates each over-hanging sprite in our extension sheets (icon51+) to a cell
that fits, and rewrites the sprite entry in place.

The sprite keeps its index, so **no STB column 9 anywhere has to change**. That
works because the two things are stored separately: the client reads sprites in
flat order across all blocks -- so the index is the position, and a sprite must
never move between blocks -- but it resolves the *texture* from the per-sprite
id, not from the block it sits in (io_imageres.cpp, `m_TextureVec[nID].m_nTXID`).
So a sprite can stay in icon51's block, keep index 8605, and point at icon52.

Retail's own bad cells are left alone: nothing references them, and rewriting
1,250 shipped sprites to fix a defect no player can see is not a trade worth
making. --include-retail forces it if that ever changes.

THE ART IS ALREADY CLIPPED
--------------------------
add_icon pasted a 40x40 image at the cell origin, and PIL clips at the image
bounds, so a bad cell only ever received 32x40, 40x32 or 32x32 of it. The missing
strip is not recoverable from the sheet -- it was never written. Relocation moves
what survives, so the icon comes out correct but up to 8px short on one edge,
instead of correct-plus-someone-else's-pixels. Re-import the item if you want
those pixels back; that re-crops from the source atlas.

Idempotent: a second run finds nothing to do. --verify checks the whole atlas.
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


def sheet_path(ico, name):
    p = os.path.join(ico.RES_DIR, name)
    if os.path.exists(p):
        return p
    for alt in os.listdir(ico.RES_DIR):          # source dirs vary in case
        if alt.lower() == name.lower():
            return os.path.join(ico.RES_DIR, alt)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="only report sprites whose rect leaves its sheet")
    ap.add_argument("--include-retail", action="store_true",
                    help="also relocate over-hanging sprites in icon01-50 (nothing "
                         "references them today, so this is normally pointless churn)")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(OURS, "3DDATA")):
        sys.exit("run from the repo root (data/3DDATA not found)")

    ico = load("add-item-icon.py", "add_item_icon")
    from PIL import Image

    textures, blocks = ico.tsi_read(ico.TSI)
    ext_tex = {i for i, (n, _) in enumerate(textures)
               if n.lower().startswith("icon") and n.lower().endswith(".dds")
               and n[4:-4].isdigit() and int(n[4:-4]) >= ico.FIRST_EXT_SHEET}

    doomed = []
    retail_bad = 0
    for flat, bi, slot, texid, x1, y1, x2, y2 in ico.iter_sprites(blocks):
        if ico.rect_fits(x1, y1, x2, y2):
            continue
        if texid not in ext_tex and not args.include_retail:
            retail_bad += 1
            continue
        doomed.append((flat, bi, slot, texid, x1, y1, x2, y2))

    print("sprites whose rect leaves their sheet: %d to fix, %d left alone in retail sheets"
          % (len(doomed), retail_bad))
    if args.verify:
        sys.exit(1 if doomed else 0)
    if not doomed:
        print("nothing to do.")
        return

    taken = ico.occupied_cells(textures, blocks)
    sheets = {}                      # texid -> PIL image (lazy, written once at the end)
    new_textures = list(textures)
    new_blocks = [(c, bytearray(r)) for c, r in blocks]

    def sheet_for(texid):
        if texid not in sheets:
            name = new_textures[texid][0]
            p = sheet_path(ico, name)
            if os.path.exists(p):
                sheets[texid] = ico.dds_read_bgra(p)
            else:
                sheets[texid] = Image.new("RGBA", (ico.SHEET_SIZE, ico.SHEET_SIZE),
                                          (0, 0, 0, 0))
        return sheets[texid]

    def next_free():
        """A free good cell in the last extension sheet, adding a sheet if full."""
        ext = [i for i in range(len(new_textures)) if i in ext_tex or i >= len(textures)]
        if ext:
            tid = max(ext)
            for c in ico.GOOD_CELLS:
                if (tid, c) not in taken:
                    return tid, c
        nums = [int(n[4:-4]) for n, _ in new_textures
                if n.lower().startswith("icon") and n.lower().endswith(".dds")
                and n[4:-4].isdigit() and int(n[4:-4]) >= ico.FIRST_EXT_SHEET]
        num = max(nums) + 1 if nums else ico.FIRST_EXT_SHEET
        name = "icon%02d.dds" % num
        new_textures.append(ico.texture_entry(name))
        new_blocks.append((0, bytearray()))
        tid = len(new_textures) - 1
        ext_tex.add(tid)
        sheets[tid] = Image.new("RGBA", (ico.SHEET_SIZE, ico.SHEET_SIZE), (0, 0, 0, 0))
        print("   started a new sheet %s" % name)
        return tid, ico.GOOD_CELLS[0]

    for flat, bi, slot, texid, x1, y1, x2, y2 in doomed:
        src = sheet_for(texid)
        # Only the part inside the texture was ever written; the rest was clipped
        # away by PIL when the icon was first pasted.
        box = (x1, y1, min(x2, ico.SHEET_SIZE), min(y2, ico.SHEET_SIZE))
        art = src.crop(box)
        dst_tid, cell = next_free()
        nx, ny = ico.cell_xy(cell)
        sheet_for(dst_tid).paste(art, (nx, ny))
        taken.add((dst_tid, cell))

        cnt, raw = new_blocks[bi]
        off = slot * 54
        label = bytes(raw[off + 22:off + 54])
        raw[off:off + 54] = struct.pack("<h4iI", dst_tid, nx, ny,
                                        nx + ico.CELL, ny + ico.CELL, 0) + label
        print("   icon %-5d %-11s (%3d,%3d) %dx%d  ->  %-11s (%3d,%3d)"
              % (flat, new_textures[texid][0], x1, y1, box[2] - x1, box[3] - y1,
                 new_textures[dst_tid][0], nx, ny))

    if not args.dry_run:
        for tid, img in sheets.items():
            ico.dds_write(sheet_path(ico, new_textures[tid][0]), img, False)
        ico.tsi_write(ico.TSI, new_textures,
                      [(c, bytes(r)) for c, r in new_blocks], False)

    # verify from what is on disk
    if not args.dry_run:
        t2, b2 = ico.tsi_read(ico.TSI)
        left = [f for f, _bi, _s, tid, ax1, ay1, ax2, ay2 in ico.iter_sprites(b2)
                if not ico.rect_fits(ax1, ay1, ax2, ay2) and tid in ext_tex]
        assert not left, "still over-hanging after the fix: %s" % left[:8]
        assert sum(c for c, _ in b2) == sum(c for c, _ in blocks), \
            "sprite count changed -- indices would have shifted"
        print("\nverified: no extension-sheet sprite leaves its texture, "
              "and the sprite count is unchanged (%d), so every icon index still "
              "means what it did." % sum(c for c, _ in b2))
    print("\n%s  Re-run add-dds-mipmaps.py, then re-bake."
          % ("DRY RUN - nothing written." if args.dry_run else "done."))


if __name__ == "__main__":
    main()
