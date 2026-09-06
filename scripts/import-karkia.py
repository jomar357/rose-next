"""Import the Karkia planet (9 zones) from the Jrose client.

Karkia is Jrose's late-era undead planet -- a cemetery, an overrun village, a
burned forest, a tower and a memory-realm cluster. `doc/karkia-survey.md` is the
evidence that it is importable; `doc/karkia-roadmap.md` is the plan this script
implements. Read the roadmap before changing anything here.

Staged the same way as `scripts/import-oro.py`, and for the same reason -- each
stage is independently testable in game and independently revertible:

    --stage 1   terrain, art, zone rows, zone names. No NPCs, no monsters, no
                gates: the copied .IFOs get their MOB/REGEN/WARP/EVENT_OBJECT
                lumps emptied on the way in (count = 0, lump table untouched),
                so later stages just refill them.

Stages 2-6 (gates and travel, monsters, the balance pass, drops, NPCs) are
planned in the roadmap and not written yet.

Every stage is idempotent -- re-running detects what is already in place and does
nothing. --dry-run previews. --selftest proves every writer round-trips
byte-identically before anything is touched.

Why this is a *port* and not a copy
-----------------------------------
The container formats are unchanged (all 9 .ZON, 111 .IFO and 18 .ZSC parse with
the readers already in import-oro.py, and not one referenced asset is missing),
which is what makes stage 1 cheap. Five things still do not travel:

  * **Karkia's .ZON files are the stripped late-Jrose variant**: a 28-byte block 0
    and *no* LUMP_ECONOMY. The client does not care -- ReadZoneINFO reads exactly
    28 bytes -- but the server does. CZoneFILE::ReadECONOMY is the only caller of
    CEconomy::Load, so with no lump 4 it never runs, and CEconomy::Init then
    computes `m_iTownITEM[nP] = m_nTown_CONSUM[nP] * 100` off uninitialised heap.
    Not fatal (m_btItemRATE is clamped to 45..65) but the zone's shop prices would
    be driven by garbage. Every one of our own 55 zones has a lump 4, so this
    script splices one in -- see zon_with_economy().

  * **WARP.STB 170 and 172 are live Oro gates** here (TOWN->ODE01 and
    ODRP01->ODE01). Karkia uses those ids for Cemetery->Church and
    Cemetery->SpireVil. Nothing in stage 1 writes WARP.STB, but stage 2 must
    renumber rather than copy, or Muris breaks silently.

  * **LIST_ZONE_S.STL key LZON086 is our zone 82** (Gates of Muris), and Karkia's
    zone 86 asks for exactly that key. Fresh keys are allocated here (LZON091+,
    the first free block above our highest) and the English names are authored --
    the source strings are Japanese and our STL is the modern ITST01 dialect with
    five language blocks against Jrose's legacy I_NUM.

  * **Our .dds files are the better copies.** 331 of the textures Karkia shares
    with us differ only in that ours carry mip chains (mips=9 against mips=0) --
    we ran add-dds-mipmaps.py over them. copy_new() never overwrites, which makes
    that safe by construction; the *new* textures want the same treatment, so the
    run ends by listing them.

  * `LIST_SKY` row 17 does not exist here (we have 13 rows). Four Karkia zones
    reference it. It is copied along with the two LUNAR\\Sky02 textures.

Deliberately not done in stage 1: the entrance. Karkia has no gate from anywhere
in the game, and its nine zones split into two disconnected clusters plus an
isolated Tower -- that is stage 2's Wayfinder NPC. Reach the zones with a GM warp
until then.

After running: rebake the client VFS and restart the servers (they cache STBs at
startup).

File formats this script writes are documented at their reader/writer functions,
or in import-oro.py where they are shared.
"""
import argparse
import importlib.util
import io
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------- config
DEFAULT_SRC = r"C:\Users\Thomas\Desktop\Testclients\Jrose"

MAPS_REL = r"3DDATA\MAPS\KARKIA"
KARKIA_ART_REL = r"3DDATA\KARKIA"
ZONE_STB_REL = r"3DDATA\STB\LIST_ZONE.STB"
ZONE_STL_REL = r"3DDATA\STB\LIST_ZONE_S.STL"
SKY_STB_REL = r"3DDATA\STB\LIST_SKY.STB"

# zone row -> (map folder, English name, fresh STL key)
#
# The names are authored, not translated cell-for-cell: LIST_ZONE col 0 carries an
# editor label ("K-Karkia's Memories (boss)") while LIST_ZONE_S.STL carries the
# in-game one, and it is the STL that draws above the minimap. Rows 135 and 136
# share one name in the source (both 絶望の塔); they are split here because the
# minimap would otherwise show the same string in two different places.
ZONES = [
    (86,  "KCHURCH",       "The Abandoned Church", "LZON091"),
    (87,  "KCEMETERY",     "The Desolate Cemetery", "LZON092"),
    (88,  "KSPIREVIL",     "Spire Village",         "LZON093"),
    (131, "KBURNEDFOREST", "The Burned Forest",     "LZON094"),
    (133, "KMEMORIES",     "Memories of Karkia",    "LZON095"),
    (134, "KMEMORIESBOSS", "Infinite Prison",       "LZON096"),
    (135, "KTOWERPLACE",   "Foot of the Tower",     "LZON097"),
    (136, "KTOWER",        "Tower of Despair",      "LZON098"),
    (144, "KFLOWERGARDEN", "Garden of Karkia",      "LZON099"),
]
MAX_ZONE_ROW = max(r for r, _, _, _ in ZONES)

# Our LIST_ZONE is 36 columns to Jrose's 37; cols 0-35 align by meaning and col 36
# (their world-map number) is theirs alone. Two are overridden rather than copied:
# col 0 is the editor label and col 26 is the STL key that collides.
ZONE_COPY_COLS = 36
ZONE_NAME_COL, ZONE_STL_COL = 0, 26

# Four Karkia zones point at LIST_SKY row 17 (a Lunar sky variant); the other five
# use row 1, which is already byte-identical to ours.
SKY_ROW = 17

# Where a synthetic LUMP_ECONOMY comes from. Any of our zones would do -- 50 of our
# 55 carry the identical 74-byte block -- but a populated Junon field zone gives
# sane non-zero town figures rather than the all-zero ones some Oro zones carry.
ECONOMY_TEMPLATE_REL = r"3DDATA\MAPS\JUNON\JG01\JG01.ZON"

# .ZON lump ids (client io_terrain.h ZONE_LUMP_TYPE); note these are a *different*
# enum from the .IFO lump ids, which import-oro.py owns.
ZON_LUMP_INFO, ZON_LUMP_EVENT, ZON_LUMP_TILE = 0, 1, 2
ZON_LUMP_BRUSHES, ZON_LUMP_ECONOMY = 3, 4

# CEconomy::Load reads three ints then MAX_PRICE_TYPE - MIN_PRICE_TYPE of them
# (datatype.h: 1 and 11), after three pascal strings. Anything past that is
# editor slack the reader never touches.
ECONOMY_MIN_INTS = 3 + (11 - 1)


def load_oro():
    """Reuse import-oro.py's readers and writers rather than duplicating them.

    Same trick rebalance-endgame-curve.py uses. Its main() is guarded by
    __name__, so importing it under any other name runs no side effects.
    """
    spec = importlib.util.spec_from_file_location(
        "import_oro", os.path.join(HERE, "import-oro.py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, ["import-oro.py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = saved
    return mod


oro = load_oro()


# ------------------------------------------------------------------- helpers
# import-oro.py's ABS_ASSET_RE matches only .ptl/.dds/.tga/.zms, so an .eft that
# animates a mesh -- and names the .zmo that drives it -- loses the motion. That
# is not theoretical: JGTFOODSHOP_NIGHT01.EFT names JGTFOODSHOP_NIGHT01.ZMO, and
# the client pops a modal "open error" box for it on entering Spire Village. 14
# .zmo across the Karkia effect chain were missed that way.
#
# .eft is included so the walk is transitive through nested effects, and .mrp
# (morph targets) because an animated-building .eft names one of those too.
EFFECT_ASSET_RE = re.compile(
    rb"3DDATA[\\/][0-9A-Za-z_\\/. -]+?\.(?:ptl|dds|tga|zms|zmo|eft|mrp)", re.I)
# A .ptl names its textures bare; an .eft names its .mrp bare, relative to itself.
BARE_TEXTURE_RE = re.compile(rb"[0-9A-Za-z_][0-9A-Za-z_-]*\.(?:dds|tga)", re.I)
BARE_SIBLING_RE = re.compile(rb"[0-9A-Za-z_][0-9A-Za-z_.-]*\.(?:mrp|zmo)", re.I)
PARTICLE_TEXTURE_DIR = r"3DDATA\EFFECT\PARTICLES\TEXTURE"


def effect_chain(seeds, src_index):
    """.eft -> .ptl/.mrp/.zmo/.zms -> particle texture, transitively.

    Same shape as import-oro.py's version, with the wider extension set above and
    bare sibling names resolved against the referring file's own directory. Both
    formats are length-prefixed binary; the paths are recovered by pattern rather
    than with a full parser because these fields are all we need and the files are
    a few hundred bytes each.
    """
    out, queue, seen = set(), list(seeds), set()
    while queue:
        rel = queue.pop()
        k = key_of(rel)
        if k in seen:
            continue
        seen.add(k)
        out.add(rel)
        p = src_index.get(k)
        if p is None:
            continue
        blob = open(p, "rb").read()
        for hit in EFFECT_ASSET_RE.finditer(blob):
            queue.append(hit.group().decode("latin-1"))
        # A bare name is a path *reconstruction*, not a reference: we are guessing
        # the directory. Only take it if the guess resolves, because a bare name
        # that does not is usually one already covered by an absolute path
        # elsewhere in the same file (an .eft names both `_pumpkin_01.zmo` and
        # `3DDATA\EFFECT\EFFECTMESH\_PUMPKIN_01.ZMO`), and reporting the failed
        # guess as "missing from source" would be a lie about a file we have.
        # Absolute references stay unguarded, so a genuinely absent one is still
        # reported.
        parent = os.path.dirname(k)
        bare = []
        if k.endswith(".ptl"):
            bare = [os.path.join(PARTICLE_TEXTURE_DIR, h.group().decode("latin-1"))
                    for h in BARE_TEXTURE_RE.finditer(blob)]
        elif k.endswith(".eft"):
            bare = [os.path.join(parent, h.group().decode("latin-1"))
                    for h in BARE_SIBLING_RE.finditer(blob)]
        queue += [b for b in bare if key_of(b) in src_index]
    return out


def key_of(rel):
    """Data-relative lookup key: backslashes, separator runs collapsed, lowercase.

    Collapsing runs is not tidiness. Several Jrose .eft and .ptl files embed a
    C-escaped path *literally* -- the bytes on disk really are
    `3DData\\\\Effect\\\\Particles\\\\_fire_02.dds` -- and a lookup that takes
    them at face value reports 19 files that are present in both trees as
    missing from the source. `zz_slash_converter` (engine/include/zz_string.h)
    performs exactly this collapse before every VFS open, which is why the engine
    resolves them and why matching it is the right fix rather than special-casing
    the offending files.
    """
    if isinstance(rel, bytes):
        rel = rel.decode("latin-1")
    out = []
    for ch in rel:
        if ch in "\\/":
            if out and out[-1] == "\\":
                continue
            out.append("\\")
        else:
            out.append(ch)
    return "".join(out).lstrip("\\").lower()


def index_tree(root):
    """Case-insensitive map of data-relative path -> real path.

    Windows would resolve the case for us, but relying on that hides a genuinely
    missing file behind a lookup that happens to work on one machine. Building the
    index means "not in source" is reported rather than discovered at bake time.
    """
    idx = {}
    for base, _, names in os.walk(root):
        rel = os.path.relpath(base, root)
        if rel == ".":
            rel = ""
        for n in names:
            idx[key_of(os.path.join(rel, n))] = os.path.join(base, n)
    return idx


def dest_of(ours, rel):
    """Our tree is uppercase throughout; keep it that way."""
    return os.path.join(ours, key_of(rel).upper().replace("\\", "/"))


def copy_new(rels, src_index, ours, dry, label):
    """Copy data-relative paths we do not already have. Never overwrites.

    Not overwriting is a correctness property here, not an optimisation: 331 of
    the textures Karkia shares with us are the same art with our mip chains added,
    and Jrose's copies would be a downgrade.
    """
    new, total, missing, new_dds = 0, 0, [], []
    for rel in sorted({key_of(r) for r in rels}):
        s = src_index.get(rel)
        if s is None:
            missing.append(rel)
            continue
        d = dest_of(ours, rel)
        if os.path.isfile(d):
            continue
        new += 1
        total += os.path.getsize(s)
        if rel.endswith(".dds"):
            new_dds.append(rel)
        if not dry:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(s, d)
    print(f"    {label:26s} {new:5d} new files  {total / 1048576:7.2f} MB"
          + (f"   ({len(missing)} NOT IN SOURCE)" if missing else ""))
    for m in missing[:8]:
        print(f"        missing from source: {m}")
    return new, total, missing, new_dds


# -------------------------------------------------------------------- ZON I/O
# Same container as an .IFO -- i32 lump_count, lump_count x (i32 type, i32 absolute
# offset), then the blocks contiguously in table order -- but a different lump
# enum. import-oro.py's read_ifo/build_ifo work on it unchanged.
def zon_lumps(path):
    return oro.read_ifo(path)


def economy_template(ours):
    """The raw LUMP_ECONOMY block of one of our zones, checked for shape.

    Copied verbatim rather than synthesised: the block is three pascal strings
    followed by 13 ints, and taking a real one means the layout cannot drift from
    what CZoneFILE::ReadECONOMY actually reads.
    """
    p = os.path.join(ours, ECONOMY_TEMPLATE_REL.replace("\\", "/"))
    if not os.path.isfile(p):
        raise SystemExit(f"economy template missing: {p}")
    buf, bounds = zon_lumps(p)
    off, end = oro.lump_block(bounds, ZON_LUMP_ECONOMY)
    if off is None:
        raise SystemExit(f"{p}: no LUMP_ECONOMY to use as a template")
    blk = buf[off:end]
    parse_economy(blk, p)                      # refuse a template we cannot read
    return blk


def parse_economy(blk, where):
    """Walk a LUMP_ECONOMY block exactly as CZoneFILE::ReadECONOMY does."""
    o = 0
    for _ in range(3):                         # zone name, BGM, background model
        if o >= len(blk):
            raise SystemExit(f"{where}: economy block truncated in the strings")
        n = blk[o]; o += 1 + n
        if o > len(blk):
            raise SystemExit(f"{where}: economy string runs past the block")
        if _ == 0:
            o += 4                             # i32 m_iIsDungeon follows the name
    if (len(blk) - o) < 4 * ECONOMY_MIN_INTS:
        raise SystemExit(f"{where}: economy block has {(len(blk) - o) // 4} ints, "
                         f"needs {ECONOMY_MIN_INTS}")
    return struct.unpack_from(f"<{ECONOMY_MIN_INTS}i", blk, o)


def zon_with_economy(path, template):
    """Return the .ZON bytes with a LUMP_ECONOMY appended, or None if it has one.

    Appended last so the lump table stays in ascending offset order, which is what
    read_ifo asserts and what both the client and server loaders assume when they
    seek per lump.
    """
    buf, bounds = zon_lumps(path)
    if oro.lump_block(bounds, ZON_LUMP_ECONOMY)[0] is not None:
        return None
    blocks = [buf[off:end] for _, off, end in bounds] + [template]
    types = [t for t, _, _ in bounds] + [ZON_LUMP_ECONOMY]
    out = [struct.pack("<i", len(types))]
    cur = 4 + 8 * len(types)
    for t, blk in zip(types, blocks):
        out.append(struct.pack("<ii", t, cur))
        cur += len(blk)
    out.extend(blocks)
    return b"".join(out)


# ------------------------------------------------------------------ selftest
def selftest(ours, src, src_index):
    """Every writer must reproduce its input byte-for-byte with no edits."""
    ok = True

    def check(label, name, same):
        nonlocal ok
        ok = ok and same
        print(f"    {label:34s} {'OK' if same else 'FAIL'}   {name}")

    for rel in (ZONE_STB_REL, SKY_STB_REL):
        p = os.path.join(ours, rel.replace("\\", "/"))
        check("STB round-trip", os.path.basename(p),
              oro.Stb(p).to_bytes() == open(p, "rb").read())

    p = os.path.join(ours, ZONE_STL_REL.replace("\\", "/"))
    check("STL round-trip", os.path.basename(p),
          oro.Stl(p).to_bytes() == open(p, "rb").read())

    # Karkia's own containers, plus a couple of ours, through the shared readers.
    probes = []
    for _, folder, _, _ in ZONES:
        d = os.path.join(src, MAPS_REL.replace("\\", "/"), folder)
        if os.path.isdir(d):
            probes += [os.path.join(d, f) for f in sorted(os.listdir(d))
                       if f.lower().endswith(".ifo")][:4]
    mine = os.path.join(ours, r"3DDATA\MAPS\ELDEON\EJT01".replace("\\", "/"))
    if os.path.isdir(mine):
        probes += [os.path.join(mine, f) for f in sorted(os.listdir(mine))
                   if f.lower().endswith(".ifo")][:3]
    cont_ok = lump_ok = True
    for p in probes:
        buf, bounds = oro.read_ifo(p)
        cont_ok = cont_ok and oro.build_ifo(bounds, buf, {}) == buf
        for lt in oro.LUMPS_STAGE1_EMPTY:
            if oro.lump_block(bounds, lt)[0] is None:
                continue
            off, end = oro.lump_block(bounds, lt)
            objs, trailing = oro.read_lump(buf, bounds, lt)
            if oro.build_object_lump(objs, trailing) != buf[off:end]:
                lump_ok = False
                print(f"        lump {lt} round-trip FAILED in {p}")
    check("IFO container rebuild", f"{len(probes)} files", cont_ok)
    check("IFO lump decode round-trip", "MOB/REGEN/WARP/EVENT_OBJECT", lump_ok)

    # The economy splice: it must add exactly one lump, leave every other block
    # byte-identical, and produce something ReadECONOMY can walk.
    try:
        tmpl = economy_template(ours)
    except SystemExit as e:
        check("economy template", str(e), False)
        return ok
    check("economy template parses", f"{len(tmpl)} bytes", True)

    splice_ok = True
    for _, folder, _, _ in ZONES:
        d = os.path.join(src, MAPS_REL.replace("\\", "/"), folder)
        if not os.path.isdir(d):
            continue
        zon = [f for f in os.listdir(d) if f.lower().endswith(".zon")]
        if not zon:
            continue
        p = os.path.join(d, zon[0])
        buf, bounds = zon_lumps(p)
        blob = zon_with_economy(p, tmpl)
        if blob is None:
            splice_ok = False
            print(f"        {zon[0]} already has a LUMP_ECONOMY -- unexpected")
            continue
        tmp = io.BytesIO(blob)
        nb, nbounds = _bounds_from_bytes(blob)
        if [t for t, _, _ in nbounds] != [t for t, _, _ in bounds] + [ZON_LUMP_ECONOMY]:
            splice_ok = False
            print(f"        {zon[0]} lump table wrong after splice")
            continue
        for (t, o1, e1), (t2, o2, e2) in zip(bounds, nbounds):
            if buf[o1:e1] != nb[o2:e2]:
                splice_ok = False
                print(f"        {zon[0]} lump {t} changed during splice")
        eo, ee = oro.lump_block(nbounds, ZON_LUMP_ECONOMY)
        parse_economy(nb[eo:ee], zon[0])
    check("ZON economy splice", f"{len(ZONES)} zones", splice_ok)
    return ok


def _bounds_from_bytes(blob):
    """read_ifo, but on an in-memory blob (used to verify a splice before writing)."""
    n, = struct.unpack_from("<i", blob, 0)
    tab = [struct.unpack_from("<ii", blob, 4 + 8 * i) for i in range(n)]
    bounds = [(t, off, tab[i + 1][1] if i + 1 < n else len(blob))
              for i, (t, off) in enumerate(tab)]
    return blob, bounds


# ------------------------------------------------------- stage 1: empty zones
def stage1(ours, src, src_index, dry):
    print("stage 1 -- terrain, art, zone rows, zone names")

    src_maps = os.path.join(src, MAPS_REL.replace("\\", "/"))
    dst_maps = os.path.join(ours, MAPS_REL.replace("\\", "/"))
    template = economy_template(ours)

    # --- 1a. maps, with the entity lumps emptied and an economy lump spliced in
    copied = rewritten = spliced = total = 0
    for row, folder, _, _ in ZONES:
        s = os.path.join(src_maps, folder)
        d = os.path.join(dst_maps, folder)
        if not os.path.isdir(s):
            raise SystemExit(f"source map folder missing: {s}")
        # Recursive: every chunk has a <x>_<y>/LIGHTMAP subdirectory the client
        # loads separately (CTERRAIN::LoadLightMapINFO), so a flat copy loses
        # lighting without erroring.
        for base, _, names in os.walk(s):
            sub = os.path.relpath(base, s)
            dbase = d if sub == "." else os.path.join(d, sub)
            for name in sorted(names):
                sp, dp = os.path.join(base, name), os.path.join(dbase, name)
                if os.path.isfile(dp):
                    continue
                low = name.lower()
                if low.endswith(".ifo"):
                    buf, bounds = oro.read_ifo(sp)
                    repl = {}
                    for lt in oro.LUMPS_STAGE1_EMPTY:
                        off, end = oro.lump_block(bounds, lt)
                        if off is None or buf[off:off + 4] == b"\0\0\0\0":
                            continue
                        _, trailing = oro.read_lump(buf, bounds, lt)
                        repl[lt] = oro.build_object_lump([], trailing)
                    blob = oro.build_ifo(bounds, buf, repl) if repl else buf
                    rewritten += 1 if repl else 0
                elif low.endswith(".zon"):
                    blob = zon_with_economy(sp, template)
                    if blob is None:
                        blob = open(sp, "rb").read()
                    else:
                        spliced += 1
                else:
                    blob = None
                if not dry:
                    os.makedirs(dbase, exist_ok=True)
                    if blob is None:
                        shutil.copyfile(sp, dp)
                    else:
                        with open(dp, "wb") as fh:
                            fh.write(blob)
                copied += 1
                total += os.path.getsize(sp)
    print(f"    {'map files':26s} {copied:5d} new files  {total / 1048576:7.2f} MB")
    print(f"    {'':26s}       {rewritten} .IFO with entity lumps emptied, "
          f"{spliced} .ZON given a LUMP_ECONOMY")

    # --- 1b. terrain tiles named by each .ZON's tile lump
    tiles = set()
    for _, folder, _, _ in ZONES:
        d = os.path.join(src_maps, folder)
        zon = [f for f in os.listdir(d) if f.lower().endswith(".zon")][0]
        tiles |= {t for t in oro.zon_tiles(os.path.join(d, zon))
                  if "\\" in t or "/" in t}
    new_dds = []
    _, _, _, tile_dds = copy_new(tiles, src_index, ours, dry, "terrain tiles")
    new_dds += tile_dds

    # --- 1c. the object tables and every file they name
    zsc_rels = []
    art = set()
    src_art = os.path.join(src, KARKIA_ART_REL.replace("\\", "/"))
    if not os.path.isdir(src_art):
        raise SystemExit(f"source art folder missing: {src_art}")
    for name in sorted(os.listdir(src_art)):
        if not name.lower().endswith(".zsc"):
            continue
        rel = f"{KARKIA_ART_REL}\\{name}"
        zsc_rels.append(rel)
        art |= oro.zsc_asset_refs(oro.Zsc(os.path.join(src_art, name)))
    # ...plus the files the .IFO records name inline. The EFFECT and SOUND lumps
    # each carry a filename in the record rather than an index into a table, so
    # they are invisible to anything that only walks the ZSC tables.
    for _, folder, _, _ in ZONES:
        d = os.path.join(src_maps, folder)
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".ifo"):
                continue
            buf, bounds = oro.read_ifo(os.path.join(d, name))
            for lt in (oro.LUMP_EFFECT, oro.LUMP_SOUND):
                objs, _ = oro.read_lump(buf, bounds, lt)
                for o in objs or []:
                    n = o["extra"][0]
                    art.add(o["extra"][1:1 + n].decode("latin-1"))
    art = {a for a in art if "\\" in a or "/" in a}
    art |= effect_chain({a for a in art if a.lower().endswith(".eft")}, src_index)
    copy_new(zsc_rels, src_index, ours, dry, "object tables")
    _, _, _, art_dds = copy_new(art, src_index, ours, dry, "deco/cnst art")
    new_dds += art_dds

    # --- 1d. the sky
    src_sky = oro.Stb(os.path.join(src, SKY_STB_REL.replace("\\", "/")))
    our_sky = oro.Stb(os.path.join(ours, SKY_STB_REL.replace("\\", "/")))
    added = our_sky.grow_to(SKY_ROW + 1)
    want = [src_sky.get(SKY_ROW, c) for c in range(our_sky.cols)]
    if our_sky.d[SKY_ROW] != want:
        for c in range(our_sky.cols):
            our_sky.set(SKY_ROW, c, src_sky.get(SKY_ROW, c))
        our_sky.save(dry)
        print(f"    {'LIST_SKY.STB':26s} +{added} rows, row {SKY_ROW} written")
    else:
        print(f"    {'LIST_SKY.STB':26s} row {SKY_ROW} already present")
    sky = {our_sky.get(SKY_ROW, c).decode("latin-1") for c in range(5)}
    _, _, _, sky_dds = copy_new({x for x in sky if "\\" in x or "/" in x},
                                src_index, ours, dry, "sky assets")
    new_dds += sky_dds

    # --- 1e. zone rows
    src_zone = oro.Stb(os.path.join(src, ZONE_STB_REL.replace("\\", "/")))
    zstb = oro.Stb(os.path.join(ours, ZONE_STB_REL.replace("\\", "/")))
    grown = zstb.grow_to(MAX_ZONE_ROW + 1,
                         labels={r: n for r, _, n, _ in ZONES})
    changed = 0
    for row, folder, name, stl_key in ZONES:
        if not src_zone.occupied(row):
            raise SystemExit(f"source LIST_ZONE row {row} ({folder}) is empty")
        before = list(zstb.d[row])
        for c in range(ZONE_COPY_COLS):
            zstb.set(row, c, src_zone.get(row, c))
        zstb.set(row, ZONE_NAME_COL, name)      # theirs is a Japanese editor label
        zstb.set(row, ZONE_STL_COL, stl_key)    # theirs collides with our zone 82
        if zstb.d[row] != before:
            changed += 1
    print(f"    {'LIST_ZONE.STB':26s} +{grown} rows (now {zstb.rows}), "
          f"{changed} Karkia rows written")
    zstb.save(dry)

    # --- 1f. zone names
    zstl = oro.Stl(os.path.join(ours, ZONE_STL_REL.replace("\\", "/")))
    n = 0
    for _, _, name, key in ZONES:
        if zstl.has(key):
            continue
        zstl.append(key, int(key[4:]), name)
        n += 1
    print(f"    {'LIST_ZONE_S.STL':26s} +{n} keys (now {len(zstl.keys)})")
    if n:
        zstl.save(dry)

    # --- 1g. what still wants doing by hand
    if new_dds:
        print(f"\n    NOTE: {len(new_dds)} new .dds have no mip chain (Jrose ships them")
        print("          flat). Run scripts/add-dds-mipmaps.py over them -- our copies of")
        print("          the shared textures already have chains, which is why nothing")
        print("          here overwrites an existing file.")
    print("    NOTE: BGM lives outside data/ -- copy Sound/BGM/KChurch.ogg, KField.ogg")
    print("          and Boss02.ogg into the deployed game dir if you want music (a")
    print("          missing track is silence, not an error).")
    print("    NOTE: zone 134's minimap is 'NOMAP' in the source, so its minimap panel")
    print("          draws empty. That is Jrose's authoring, not a broken import.")
    print("    NOTE: Karkia keeps its native zone numbers (86-144), which leaves blank")
    print("          LIST_ZONE rows in the gaps. The gameserver skips those on")
    print("          Is_FileExist; the worldserver's Init only tests ZONE_FILE for NULL,")
    print("          not for empty, so each blank row logs one 'zone file open error' at")
    print("          startup and carries on. We already have ~26 such rows -- this adds")
    print("          more noise, not a new failure. Native numbers are kept because the")
    print("          .ZON event names and the revive-zone columns encode them.")
    print("    NOTE: .bak files sit next to every table touched. pack.rs filters only")
    print("          *hidden* entries, so delete them before baking or they go in the .vfs.")


def verify(ours):
    """Re-derive the result from what is on disk, after the fact."""
    print("verify -- reading back what is in data/")
    dst_maps = os.path.join(ours, MAPS_REL.replace("\\", "/"))
    bad = 0
    for row, folder, name, key in ZONES:
        d = os.path.join(dst_maps, folder)
        if not os.path.isdir(d):
            print(f"    !! zone {row} {folder}: map folder missing")
            bad += 1
            continue
        hims = [f for f in os.listdir(d) if f.lower().endswith(".him")]
        zon = [f for f in os.listdir(d) if f.lower().endswith(".zon")]
        if not zon:
            print(f"    !! zone {row} {folder}: no .ZON")
            bad += 1
            continue
        p = os.path.join(d, zon[0])
        buf, bounds = zon_lumps(p)
        types = [t for t, _, _ in bounds]
        eo, ee = oro.lump_block(bounds, ZON_LUMP_ECONOMY)
        econ = "missing"
        if eo is not None:
            parse_economy(buf[eo:ee], p)
            econ = f"{ee - eo}B ok"
        names = [n for n, _ in oro.zon_events(p)]
        live = 0
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".ifo"):
                continue
            b2, bd2 = oro.read_ifo(os.path.join(d, f))
            for lt in oro.LUMPS_STAGE1_EMPTY:
                off, _ = oro.lump_block(bd2, lt)
                if off is not None and b2[off:off + 4] != b"\0\0\0\0":
                    live += 1
        flag = ""
        if eo is None or live:
            flag = "   <-- CHECK"
            bad += 1
        print(f"    zone {row:3d} {folder:14s} {len(hims):3d} chunks  lumps={types}  "
              f"economy={econ}  events={len(names)}  live-entity-lumps={live}{flag}")

    zstb = oro.Stb(os.path.join(ours, ZONE_STB_REL.replace("\\", "/")))
    zstl = oro.Stl(os.path.join(ours, ZONE_STL_REL.replace("\\", "/")))
    for row, folder, name, key in ZONES:
        got_name = zstb.get(row, ZONE_NAME_COL).decode("latin-1")
        got_key = zstb.get(row, ZONE_STL_COL).decode("latin-1")
        zon_path = zstb.get(row, 1).decode("latin-1")
        on_disk = os.path.isfile(os.path.join(ours, zon_path.replace("\\", "/")))
        problems = []
        if got_name != name:
            problems.append(f"name={got_name!r}")
        if got_key != key:
            problems.append(f"key={got_key!r}")
        if not zstl.has(key):
            problems.append("no STL entry")
        if not on_disk:
            problems.append(f"ZONE_FILE not on disk: {zon_path}")
        if problems:
            bad += 1
            print(f"    !! zone {row}: {'; '.join(problems)}")
    sky = oro.Stb(os.path.join(ours, SKY_STB_REL.replace("\\", "/")))
    if sky.rows <= SKY_ROW or not sky.occupied(SKY_ROW):
        bad += 1
        print(f"    !! LIST_SKY row {SKY_ROW} missing (rows={sky.rows})")
    else:
        print(f"    LIST_SKY row {SKY_ROW} = "
              f"{sky.get(SKY_ROW, 0).decode('latin-1')}")
    print(f"    LIST_ZONE rows={zstb.rows}  LIST_ZONE_S keys={len(zstl.keys)}")
    print(f"\n    {'ALL CHECKS PASSED' if not bad else f'{bad} PROBLEM(S)'}")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", type=int, choices=(1,), action="append",
                    help="stage to run (repeatable); omit to run them all")
    ap.add_argument("--dry-run", action="store_true", help="preview without writing")
    ap.add_argument("--selftest", action="store_true",
                    help="prove every writer is byte-faithful, then exit")
    ap.add_argument("--verify", action="store_true",
                    help="read back what is in data/ and check it, then exit")
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--source", default=DEFAULT_SRC, help="Jrose client root")
    args = ap.parse_args()

    ours = os.path.join(args.root, "data")
    src = args.source
    if not os.path.isdir(ours):
        raise SystemExit(f"not found: {ours} (run from the repo root or pass --root)")
    if args.verify:
        return 0 if verify(ours) else 1
    if not os.path.isdir(src):
        raise SystemExit(f"source client root not found: {src}")

    print(f"source: {src}")
    print(f"target: {os.path.abspath(ours)}\n")
    print("indexing the source tree...")
    src_index = index_tree(src)
    print(f"    {len(src_index)} files\n")

    print("self-test (every writer must round-trip byte-identically):")
    if not selftest(ours, src, src_index):
        raise SystemExit("self-test FAILED -- refusing to write")
    if args.selftest:
        return 0

    print()
    for s in sorted(set(args.stage or (1,))):
        {1: stage1}[s](ours, src, src_index, args.dry_run)
        print()

    if args.dry_run:
        print("dry run: nothing written")
    else:
        print("done -- .bak backups alongside every table touched.")
        print("Next: --verify, then rebake the client VFS and restart the servers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
