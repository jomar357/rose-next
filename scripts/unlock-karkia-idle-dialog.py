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

**Blanking a check is not always enough** -- see PROMOTE below. `Conversation`
runs *every* root node that passes, and each NPCSAY calls CloseQueryDlg() before
the empty-string test, so the LAST match wins and a later passing node with no
text silently closes the window an earlier one opened. Holk (untouched by the
unlock) and Brown were still mute after the first pass for exactly that reason:
their final root node is gated on a **default-state** predicate that is true
precisely because no quest is active. Those two get their greeting moved to the
end of the root offset table instead, which needs no knowledge of Lua truth
values.

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

# Root nodes whose greeting must win outright, as (con, who, menu, str_id).
#
# Blanking a check function is not enough on its own. `CEvent::Conversation`
# does NOT stop at the first node that passes -- it runs every one of them, and
# each SC_MSG_NPCSAY calls Del_ClickITEMS() + CloseQueryDlg() *before* the
# empty-string test. So the **last** matching root node wins, and a later node
# that passes its check but has no LTB text silently closes the window that an
# earlier one opened.
#
# That is what kept Holk and Brown mute after the first pass. Their last root
# node is gated on a **default-state** predicate -- `TA_Normal` (Brown) and
# `TA_Yuusha_inventoryfull` (Holk) -- which is true precisely because no quest
# is active, and both have empty text. Every other Karkia NPC's last gate is a
# positive quest check (`_Yet`, `_End`, `_Check`, `_Finish`) that is false for
# us, which is why 18 of 20 worked. Note "last node has empty text" is NOT the
# predictor: 17 of the 20 look like that.
#
# Rather than depend on Lua truth values that cannot be evaluated from the data,
# move the good greeting to the END of the root menu so it wins no matter which
# gates pass. Order comes purely from the sub-menu offset table
# (`pMenuColl->m_SubMenuMMT[j]`, cevent.cpp), so this permutes four-byte entries
# and moves no node body -- still no size change.
#
# Trade-off, deliberate: if Karkia quests are ever imported, this default will
# override their greetings and these two entries should be dropped.
PROMOTE = [
    ("EM02-112.CON", "[Warrant Officer] Holk", 0, 30749),
    ("EM86-003.CON", "[Priest] Brown", 0, 21289),
    # Gelt already sits after his ungated "………" line, so blanking the gate
    # would be enough today -- promoted anyway so the shop cannot be lost to a
    # later node that turns out to pass, which is the mistake made once here.
    ("EM86-013.CON", "[Spire Warrior] Gelt", 0, 25970),
    # Kashi, the Church's gate guard. His root carries TA_CanNotExit_Church,
    # whose bytecode negates its quest check -- so it is TRUE precisely because
    # the switch it reads was never imported. It fired after his greeting, with
    # no text, closing the window the greeting had opened: mute NPC, and the
    # con-warp exit option appended to nothing. Third instance of this pattern
    # after Holk and Brown, and the first where a trailing option made "move it
    # last" the wrong fix -- hence target_slot.
    ("EM86-004.CON", "[Church Guard] Kashi", 0, 21586),
    # Petri and Nemo are not broken -- they are *fragile*. Their greeting sits
    # at root[1] with gated speech nodes after it, so they work only because
    # every one of those gates is a positive quest check that returns false.
    # Both carry something a player cannot do without: Petri is the only way
    # home (a failure strands you in Karkia) and Nemo's shop hangs off her
    # greeting's child menu. Promotion is free and removes the dependency.
    #
    # Eleven other reachable NPCs are fragile the same way and are deliberately
    # left alone: they carry only flavour, and each promotion is a change to a
    # file that currently works.
    ("EM86-009.CON", "[Explorer] Petri", 0, 23269),
    ("EM86-001.CON", "[Shrine Maiden] Nemo", 0, 21321),
]

# (con, who, [(menu, str_id, field, expected current name)])
# field is "check" to expose a node, "click" to neuter a quest action.
#
# Nodes are addressed by **str_id, never by item index**: PROMOTE permutes the
# offset table, so an index recorded here would name a different node after a
# promotion -- which is exactly how the first attempt's --verify broke.
TARGETS = [
    ("EM86-010.CON", "[Spire Captain] Blago",
     [(0, 26040, "check", "AT_Kakia_EpisodeQ527_Before_01")]),
    ("EM02-108.CON", "[Field Medic] Emil",
     [(0, 29129, "check", "TA_MainQ_Q5504_01")]),
    ("EM03-007.CON", "[Mage of Dreams] Ragia",
     [(0, 30011, "check", "TA_Normal01")]),
    ("EM86-002.CON", "[Plague Doctor] Jenner",
     [(0, 21252, "check", "TA_SicknessUntoDeath_Start")]),
    ("EM86-003.CON", "[Priest] Brown",
     [(0, 21289, "check", "TA_KakiaVoyage_Talk")]),
    ("EM02-115.CON", "[Artificer] Physalis",
     [(0, 31024, "check", "TA_Q547_01"),
      (2, 31025, "click", "AT_Q547_02")]),
    # Gelt is Spire Village's quartermaster, and his whole service menu --
    # GF_openStore, GF_openBank, GF_repair, GF_openUpgrade, all four registered
    # in game_func_reg.inc -- hangs off this one node. Jrose gates it behind
    # finishing the plague-cure arc (episode 532), which we never imported, so
    # without this his shop tabs can never open: he answers with the fallback
    # "………" line and a single "(He's barely breathing.)" option.
    #
    # Exposing it is the same call already made for the other five: show the
    # state that makes the NPC work when no quest can ever run. The cost is
    # that Gelt reads as cured while Sulfa and Dinos still groan beside him.
    ("EM86-013.CON", "[Spire Warrior] Gelt",
     [(0, 25970, "check", "TA_Kakia_EpisodeQ532_Finish")]),
]


def all_cons():
    """Every .CON this script touches, in order, without duplicates."""
    return list(dict.fromkeys([c for c, _w, _e in TARGETS]
                              + [c for c, _w, _m, _s in PROMOTE]))


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
    for menu, str_id, field, expect in edits:
        off, length, key = menu_span(b, menu)
        coll = decode(b, off, length, key)
        item, _num = find_item(coll, str_id)
        if item is None:
            raise SystemExit(f"{con} menu{menu}: no node with str_id {str_id}")
        o = item_off(coll, item)
        cur = read_func(coll, o, field)
        if cur == "":
            report.append(f"   {con} menu{menu} str_id {str_id} {field}: already blank")
            continue
        if cur != expect:
            raise SystemExit(
                f"{con} menu{menu} str_id {str_id} {field}: expected {expect!r}, "
                f"found {cur!r} -- refusing to edit an unrecognised node")
        base = CHECK_OFF if field == "check" else CLICK_OFF
        # XOR is its own inverse and the key depends only on num_sub/length,
        # neither of which we touch -- so a zeroed byte encodes to the key.
        for k in range(FUNC_LEN):
            b[off + o + base + k] = key
        changed += 1
        verb = "exposed" if field == "check" else "neutered"
        report.append(f"   {con} menu{menu} str_id {str_id}: {verb} {cur}")
    if len(b) != len(blob):
        raise SystemExit(f"{con}: size changed -- refusing to write")
    return bytes(b) if changed else None


def find_item(coll, str_id):
    """Index of the item in `coll` carrying `str_id`, or None."""
    num_sub, = struct.unpack_from("<i", coll, 4)
    for j in range(max(0, num_sub)):
        o, = struct.unpack_from("<I", coll, 8 + j * 4)
        if o + 80 > len(coll):
            break
        if struct.unpack_from("<i", coll, o + 76)[0] == str_id:
            return j, num_sub
    return None, num_sub


# cevent.cpp SC_MSG_*: 1/2 open a window, 0/3/4 append a line to the open one.
SPEECH_TYPES = (1, 2)


def item_type(coll, slot):
    o, = struct.unpack_from("<I", coll, 8 + slot * 4)
    return struct.unpack_from("<i", coll, o + 4)[0]


def target_slot(coll, num_sub, moving):
    """Where the greeting has to sit: last of the speech nodes, but ahead of
    every option node.

    A speech node opens a window and closes whatever was open; an option node
    only appends a line to the window that is already open. So the greeting has
    to run after every other speech node (or one of them closes it) and before
    every option node (or the option is appended to nothing). Putting it simply
    last is wrong the moment the menu ends in options -- which is exactly what
    an appended con-warp/con-store option does.
    """
    order = [k for k in range(num_sub) if k != moving]
    for pos, k in enumerate(order):
        if item_type(coll, k) not in SPEECH_TYPES:
            return pos
    return len(order)


def promote_last(blob, menu, str_id, con, report):
    """Move the node carrying `str_id` to its winning slot (see target_slot)."""
    b = bytearray(blob)
    off, length, key = menu_span(b, menu)
    coll = decode(b, off, length, key)
    j, num_sub = find_item(coll, str_id)
    if j is None:
        raise SystemExit(f"{con} menu{menu}: no node with str_id {str_id}")
    want = target_slot(coll, num_sub, j)
    if j == want:
        report.append(f"   {con} menu{menu}: str_id {str_id} already in slot {want}")
        return None
    table = [struct.unpack_from("<I", coll, 8 + k * 4)[0] for k in range(num_sub)]
    table.insert(want, table.pop(j))
    for k, v in enumerate(table):
        struct.pack_into("<I", coll, 8 + k * 4, v)
    for k in range(8, len(coll)):          # re-encode; key is content-independent
        coll[k] ^= key
    b[off:off + length] = coll
    if len(b) != len(blob):
        raise SystemExit(f"{con}: size changed -- refusing to write")
    report.append(f"   {con} menu{menu}: str_id {str_id} moved {j} -> {want}"
                  f" (of {num_sub}), last speech node and ahead of every option")
    return bytes(b)


def promote_applied(blob, menu, str_id):
    off, length, key = menu_span(blob, menu)
    coll = decode(blob, off, length, key)
    j, num_sub = find_item(coll, str_id)
    if j is None:
        return False
    return j == target_slot(coll, num_sub, j)


def check_applied(blob, edits):
    for menu, str_id, field, _expect in edits:
        off, length, key = menu_span(blob, menu)
        coll = decode(blob, off, length, key)
        item, _num = find_item(coll, str_id)
        if item is None or read_func(coll, item_off(coll, item), field) != "":
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
        for con in all_cons():
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
                bad.append(f"{con} ({who}) not unlocked")
        for con, who, menu, str_id in PROMOTE:
            with open(os.path.join(EVENT, con), "rb") as fh:
                blob = fh.read()
            if not promote_applied(blob, menu, str_id):
                bad.append(f"{con} ({who}) greeting not last")
        print(f"{len(TARGETS)} unlocks + {len(PROMOTE)} promotions; "
              f"{len(bad)} wrong" + (f": {bad}" if bad else ""))
        return 1 if bad else 0

    report, written = [], []
    pending = {}
    for con, who, edits in TARGETS:
        path = os.path.join(EVENT, con)
        if not os.path.isfile(path):
            sys.exit(f"missing {path}")
        with open(path, "rb") as fh:
            blob = fh.read()
        report.append(f"{who}  {con}")
        out = apply_to(blob, edits, who, con, report)
        if out is not None:
            pending[con] = (path, blob, out)

    for con, who, menu, str_id in PROMOTE:
        path = os.path.join(EVENT, con)
        orig, cur = (pending[con][1], pending[con][2]) if con in pending else (
            open(path, "rb").read(),) * 2
        if con not in pending:
            report.append(f"{who}  {con}")
        out = promote_last(cur, menu, str_id, con, report)
        if out is not None:
            pending[con] = (path, orig, out)

    written = [(p, con, o, n) for con, (p, o, n) in pending.items()]

    print("\n".join(report))
    print(f"\n{len(written)} of {len(all_cons())} conversations need a change")
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
        edits = next((e for c, _w, e in TARGETS if c == con), None)
        if edits and not check_applied(blob, edits):
            sys.exit(f"verify failed for {con}")
        for c, _w, menu, str_id in PROMOTE:
            if c == con and not promote_applied(blob, menu, str_id):
                sys.exit(f"promotion verify failed for {con}")
    print(f"wrote {len(written)} .CON files, backups in "
          f"{os.path.relpath(BACKUP, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
