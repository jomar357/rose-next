"""Find which reference dump an atlas icon was originally cropped from.

Written to repair icons that the old cell allocator clipped: a cell hanging 8px
off the right of its sheet only ever received 32 of its 40 columns, and the
missing strip is not in our data at all (see fix-icon-atlas-overrun.py). To get
it back you have to re-crop from the source -- and for imports made before the
batch manifests existed, nothing recorded what that source was.

Matching finds it. Our copy is the decoded source pixels stored uncompressed, so
the surviving columns match the original **bit for bit**: a correct hit scores
mean-absolute-difference 0.000 and everything else is far away. That is an
identification, not a guess.

It searches every ITEM1.TSI under the test-client directory, which matters --
two of the seven icons this was written for turned out to come from QQ-iROSE and
not from RoseZA, where they had been assumed to originate. A RoseZA-only search
found plausible-looking wrong answers at MAD 7 and 29.

Edit TARGETS for the sprite indices to identify. --apply re-pastes each confident
hit at full 40x40 into the cell it already occupies, so no index moves and no STB
changes. Then run add-dds-mipmaps.py and re-bake.

Two of the original eleven never matched anywhere (MAD ~9-11). Nothing references
them, so they were left as they are; a low score with no exact hit most likely
means the icon was added from a PNG rather than cropped from a dump.
"""
import importlib.util, os, struct, sys, glob
import numpy as np
from PIL import Image

HERE = os.path.join(os.getcwd(), "scripts")
def load(n, f):
    s = importlib.util.spec_from_file_location(n, os.path.join(HERE, f))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ico = load("ico", "add-item-icon.py")

APPLY = "--apply" in sys.argv
KEEP = 32
TC = r"C:/Users/Thomas/Desktop/Testclients"

textures, blocks = ico.tsi_read(ico.TSI)
sprites = {f: (bi, slot, tid, x1, y1) for f, bi, slot, tid, x1, y1, _a, _b
           in ico.iter_sprites(blocks)}
ours_cache = {}
def our_art(idx):
    _bi, _slot, tid, x1, y1 = sprites[idx]
    n = textures[tid][0]
    if n not in ours_cache:
        ours_cache[n] = ico.dds_read_bgra(os.path.join(ico.RES_DIR, n))
    return ours_cache[n].crop((x1, y1, x1 + ico.CELL, y1 + ico.CELL))

TARGETS = [(8579, "Akela Bowgun"), (8592, "Golden Angel Shield"),
           (8475, "(unreferenced)"), (8488, "(unreferenced)")]
mine = {i: np.asarray(our_art(i).crop((0, 0, KEEP, ico.CELL)), dtype=np.int16)
        for i, _ in TARGETS}

def find_atlases():
    out = []
    for d in sorted(os.listdir(TC)):
        root = os.path.join(TC, d)
        if not os.path.isdir(root):
            continue
        for tsi in glob.glob(os.path.join(root, "**", "ITEM1.TSI"), recursive=True):
            out.append((d, tsi))
    return out

best = {i: (1e18, None) for i, _ in TARGETS}
for dump, tsi in find_atlases():
    res_dir = os.path.dirname(tsi)
    try:
        stex, sblocks = ico.tsi_read(tsi)
    except Exception as e:
        print("  %-22s unreadable TSI (%s)" % (dump, e)); continue
    sheets = {}
    n = 0
    for (sheet, _), (cnt, raw) in zip(stex, sblocks):
        if sheet not in sheets:
            p = os.path.join(res_dir, sheet)
            if not os.path.exists(p):
                for a in os.listdir(res_dir):
                    if a.lower() == sheet.lower():
                        p = os.path.join(res_dir, a); break
            try:
                sheets[sheet] = np.asarray(Image.open(p).convert("RGBA"), dtype=np.int16)
            except Exception:
                sheets[sheet] = None
        im = sheets[sheet]
        if im is None:
            continue
        for i in range(cnt):
            _t, x1, y1, _x2, _y2 = struct.unpack_from("<h4i", raw[i*54:(i+1)*54], 0)
            if y1 + ico.CELL > im.shape[0] or x1 + KEEP > im.shape[1]:
                continue
            patch = im[y1:y1+ico.CELL, x1:x1+KEEP]
            for t, _lbl in TARGETS:
                d = int(np.abs(patch - mine[t]).sum())
                if d < best[t][0]:
                    best[t] = (d, (dump, res_dir, sheet, x1, y1))
            n += 1
    print("  scanned %-22s %5d sprites" % (dump, n))

print()
hits = []
for t, lbl in TARGETS:
    score, where = best[t]
    mad = score / float(KEEP * ico.CELL * 4)
    if where is None:
        print("  %-5d %-22s no candidate" % (t, lbl)); continue
    dump, res_dir, sheet, x1, y1 = where
    print("  %-5d %-22s -> %-22s %-12s @(%3d,%3d)  MAD=%.3f %s"
          % (t, lbl, dump, sheet, x1, y1, mad, "OK" if mad < 1.0 else "*** still weak ***"))
    if mad < 1.0:
        hits.append((t, res_dir, sheet, x1, y1))

if APPLY and hits:
    dirty = {}
    for t, res_dir, sheet, x1, y1 in hits:
        p = os.path.join(res_dir, sheet)
        if not os.path.exists(p):
            for a in os.listdir(res_dir):
                if a.lower() == sheet.lower():
                    p = os.path.join(res_dir, a); break
        art = Image.open(p).convert("RGBA").crop((x1, y1, x1 + ico.CELL, y1 + ico.CELL))
        _bi, _slot, tid, dx, dy = sprites[t]
        n = textures[tid][0]
        if n not in dirty:
            dirty[n] = ours_cache.get(n) or ico.dds_read_bgra(os.path.join(ico.RES_DIR, n))
        dirty[n].paste(art, (dx, dy))
    for n, img in dirty.items():
        p = os.path.join(ico.RES_DIR, n)
        if not os.path.exists(p):
            for a in os.listdir(ico.RES_DIR):
                if a.lower() == n.lower():
                    p = os.path.join(ico.RES_DIR, a); break
        ico.dds_write(p, img, False)
    print("\nre-pasted %d icon(s) at full 40x40" % len(hits))
