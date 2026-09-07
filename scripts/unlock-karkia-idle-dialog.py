"""Give Karkia's mute NPCs an ungated idle greeting.

Six reachable Karkia NPCs open no dialog at all. It is not a broken import --
it is `CEvent::Conversation` (src/client/event/cevent.cpp) doing exactly what it
is told:

    case SC_MSG_NPCSAY:
        Del_ClickITEMS();
        g_itMGR.CloseQueryDlg();
        szMessage = this->ParseMESSAGE(...m_Message.Get());
        if (szMessage == NULL) break;      // no window, and no recursion
        g_itMGR.OpenQueryDLG(...);
        Conversation(...m_lChildDataIDX);

The text comes from `g_LngTBL.GetEventString(iStrID)`, so a node whose LTB cell
is empty renders nothing *and* never reaches its child menu. Every Karkia .CON
opens with a `BasicMenu` node that is deliberately empty (its own Japanese reads
"normally blocked off, do not use"), so an NPC is only audible if some *later*
root node passes its check function and has text.

Talking NPCs (Petri, Nemo, Holk, ...) have an ungated greeting in that slot.
The six here do not: every greeting they own sits behind a `TA_*`/`AT_*` check
for a quest chain we deliberately never imported, so the root loop skips them
all and the player clicks an NPC that does nothing.

The fix is the smallest one available: blank the 32-byte check-function field on
one existing greeting per NPC, which promotes it to that NPC's default line. No
node is added, no string changes length, and the file size is untouched -- the
field is a fixed slot inside the 80-byte record, so this is a pure in-place
edit of the (XOR'd) menu collection.

Which greeting was chosen, and why -- every one of these has no click function
of its own, so exposing it only ever shows text:

  Blago     EM86-010  root[1]  "......"        -> 1-node subtree, no clicks.
                                                  Reads as a captain who will
                                                  not talk to you. Ideal.
  Emil      EM02-108  root[1]  "why was I posted somewhere this dangerous..."
                                               -> 1-node subtree, no clicks.
  Ragia     EM03-007  root[1]  "...it is still too early for you."
                                               -> 1-node subtree, no clicks.
                                                  (root[2] was rejected: its
                                                  option fires AT_Normal04.)
  Jenner    EM86-002  root[1]  his first-meeting line, which is the correct
                                default for a player who has done none of his
                                quests -> 7-node subtree, zero click funcs.
  Brown     EM86-003  root[1]  the "lost child" greeting into the lore of the
                                goddess abandoning Karkia -> 37 nodes, zero
                                click funcs. root[3] was rejected: all of its
                                options are gated (so the box would have had no
                                way to dismiss it) and one fires AT_GotoJunon.
  Physalis  EM02-115  root[1]  "hmm... is there no good ring anywhere..."
                                -> one option in its child menu fires
                                AT_Q547_02, so that *click* field is blanked
                                too, leaving the line as pure dialogue.

Nothing here un-gates a turn-in line or a quest grant: the only two click
functions anywhere in the exposed subtrees are AT_GotoJunon (left gated, on a
branch we do not expose) and AT_Q547_02 (neutered).

Run `translate-karkia-dialog.py` afterwards -- these nodes were skipped by its
collector while they were gated, so their English has to be written in.

Idempotent. `--dry-run` / `--verify` / `--restore`. Backups go to build/, never
next to the data: src/pipeline/src/pack.rs walks the data tree filtering only
*hidden* entries -- no extension filter -- so a .bak left in data/3DDATA/EVENT
gets baked into the .vfs.
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVENT = os.path.join(ROOT, "data", "3DDATA", "EVENT")
BACKUP = os.path.join(ROOT, "build", "karkia-idle-dialog-backup")
SIDECAR = os.path.join(ROOT, "build", "karkia-idle-dialog.json")

CHECK_OFF, CLICK_OFF, FUNC_LEN = 12, 44, 32

# (con, who, [(menu, item, field, expected current name)])
# field is "check" to expose a node, "click" to neuter a quest action.
TARGETS = [
    ("EM86-010.CON", "[Spire Captain] Blago",
     [(0, 1, "check", "AT_Kakia_EpisodeQ527_Before_01")]),
    ("EM02-108.CON", "[Field Medic] Emil",
     [(0, 1, "check", "TA_MainQ_Q5504_01")]),
    ("EM03-007.CON", "[Mage of Dreams] Ragia",
     [(0, 1, "check", "TA_Normal01")]),
    ("EM86-002.CON", "[Plague Doctor] Jenner",
     [(0, 1, "check", "TA_SicknessUntoDeath_Start")]),
    ("EM86-003.CON", "[Priest] Brown",
     [(0, 1, "check", "TA_KakiaVoyage_Talk")]),
    ("EM02-115.CON", "[Artificer] Physalis",
     [(0, 1, "check", "TA_Q547_01"),
      (2, 0, "click", "AT_Q547_02")]),
]


def _cstr(b, o, n):
    f = b[o:o + n]
    z = f.find(b"\0")
    return f[:z if z >= 0 else n]


def menu_span(b, index):
    """(offset, length, xor key) of menu collection `index` in the raw file."""
    conv_off, _script_off = struct.unpack_from("<II", b, 516)
    _msg_num, _msg_off, menu_num, menu_off = struct.unpack_from("<iIiI", b, 524)
    if not 0 <= index < menu_num:
        raise SystemExit(f"menu {index} out of range (have {menu_num})")
    base = conv_off + menu_off
    mmt, = struct.unpack_from("<I", b, base + index * 4)
    off = base + mmt
    length, num_sub = struct.unpack_from("<ii", b, off)
    if length < 8 or off + length > len(b):
        raise SystemExit(f"menu {index}: bad collection length {length}")
    return off, length, (num_sub if num_sub & 1 else length) & 0xFF


def decode(b, off, length, key):
    coll = bytearray(b[off:off + length])
    for k in range(8, len(coll)):
        coll[k] ^= key
    return coll


def item_off(coll, item):
    num_sub, = struct.unpack_from("<i", coll, 4)
    if not 0 <= item < num_sub:
        raise SystemExit(f"item {item} out of range (have {num_sub})")
    o, = struct.unpack_from("<I", coll, 8 + item * 4)
    if o + 80 > len(coll):
        raise SystemExit(f"item {item}: body at {o} runs past the collection")
    return o


def read_func(coll, o, field):
    base = CHECK_OFF if field == "check" else CLICK_OFF
    return _cstr(coll, o + base, FUNC_LEN).decode("latin-1")


def apply_to(blob, edits, who, con, report):
    """Blank the named fields. Returns the new bytes, or None if already done."""
    b = bytearray(blob)
    changed = 0
    for menu, item, field, expect in edits:
        off, length, key = menu_span(b, menu)
        coll = decode(b, off, length, key)
        o = item_off(coll, item)
        cur = read_func(coll, o, field)
        if cur == "":
            report.append(f"   {con} menu{menu}[{item}] {field}: already blank")
            continue
        if cur != expect:
            raise SystemExit(
                f"{con} menu{menu}[{item}] {field}: expected {expect!r}, "
                f"found {cur!r} -- refusing to edit an unrecognised node")
        base = CHECK_OFF if field == "check" else CLICK_OFF
        # XOR is its own inverse and the key depends only on num_sub/length,
        # neither of which we touch -- so a zeroed byte encodes to the key.
        for k in range(FUNC_LEN):
            b[off + o + base + k] = key
        changed += 1
        verb = "exposed" if field == "check" else "neutered"
        report.append(f"   {con} menu{menu}[{item}] {verb} {cur}")
    if len(b) != len(blob):
        raise SystemExit(f"{con}: size changed -- refusing to write")
    return bytes(b) if changed else None


def check_applied(blob, edits):
    for menu, item, field, _expect in edits:
        off, length, key = menu_span(blob, menu)
        coll = decode(blob, off, length, key)
        if read_func(coll, item_off(coll, item), field) != "":
            return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not os.path.isdir(BACKUP):
            sys.exit("no backup -- nothing to restore")
        n = 0
        for con, _who, _edits in TARGETS:
            src = os.path.join(BACKUP, con)
            if not os.path.isfile(src):
                continue
            with open(src, "rb") as fh:
                blob = fh.read()
            with open(os.path.join(EVENT, con), "wb") as fh:
                fh.write(blob)
            n += 1
        if os.path.exists(SIDECAR):
            os.remove(SIDECAR)
        print(f"restored {n} .CON files from {os.path.relpath(BACKUP, ROOT)}")
        return 0

    if args.verify:
        bad = []
        for con, who, edits in TARGETS:
            with open(os.path.join(EVENT, con), "rb") as fh:
                blob = fh.read()
            if not check_applied(blob, edits):
                bad.append(f"{con} ({who})")
        print(f"{len(TARGETS)} conversations; "
              f"{len(bad)} not unlocked" + (f": {bad}" if bad else ""))
        return 1 if bad else 0

    report, written = [], []
    for con, who, edits in TARGETS:
        path = os.path.join(EVENT, con)
        if not os.path.isfile(path):
            sys.exit(f"missing {path}")
        with open(path, "rb") as fh:
            blob = fh.read()
        report.append(f"{who}  {con}")
        out = apply_to(blob, edits, who, con, report)
        if out is not None:
            written.append((path, con, blob, out))

    print("\n".join(report))
    print(f"\n{len(written)} of {len(TARGETS)} conversations need a change")
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    if not written:
        print("already applied")
        return 0

    os.makedirs(BACKUP, exist_ok=True)
    for path, con, blob, out in written:
        bak = os.path.join(BACKUP, con)
        if not os.path.exists(bak):
            with open(bak, "wb") as fh:
                fh.write(blob)
        with open(path, "wb") as fh:
            fh.write(out)
    with open(SIDECAR, "w", encoding="utf-8") as fh:
        json.dump({"targets": [[c, w, e] for c, w, e in TARGETS]}, fh, indent=1)

    for path, con, _blob, _out in written:
        with open(path, "rb") as fh:
            blob = fh.read()
        edits = next(e for c, _w, e in TARGETS if c == con)
        if not check_applied(blob, edits):
            sys.exit(f"verify failed for {con}")
    print(f"wrote {len(written)} .CON files, backups in "
          f"{os.path.relpath(BACKUP, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
