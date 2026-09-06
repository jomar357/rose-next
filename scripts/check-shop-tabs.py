"""Audit every NPC shop tab for the two ways one can open broken. Read-only.

A shop tab is a row of LIST_SELL.STB that an NPC names in LIST_NPC.STB game
columns 21..24. Two independent things can be missing from that row, and neither
is an error anywhere -- the tab just opens wrong:

  * No caption. `CStore::ChangeStore` calls `STORE_NAME(row)`, which on the
    client is `CStringManager::GetStoreTabName` -> take the STL key from game
    column 1 (e.g. "LSEL462") and look it up in LIST_SELL_S.STL. An empty or
    unknown key returns `m_strNull` -- an empty string, never NULL, so nothing
    crashes and the tab still sells. It simply has no name above the slots.
    Game column 0 is an internal description that the running game never shows;
    a row can look perfectly named here and still be blank in game.

  * No stock. Game columns 2..49 are the 48 item slots. A row of zeroes is a
    tab that opens empty.

Both are invisible in a diff and neither shows up in the server log, so this
script exists to make them countable. It writes nothing.

Cross-check against the reference dumps in C:/Users/Thomas/Desktop/Testclients
with --compare: a row that is empty here and stocked there is a gap in our
translated dump and is probably recoverable; a row empty in every dump is how
retail shipped it and should be left alone. (Do not copy item codes across
dumps blind -- item ids diverge between them. Use it to decide what is worth
looking at, not as an import source.)

Known state of our data at the time of writing, from --compare:

    rows 323, 327          empty here, stocked in every reference dump
    rows 386, 387          empty here, stocked in 667 and RoseZA only
    rows 394 395 397 429 433   empty in every dump, retail included

Usage:
    python scripts/check-shop-tabs.py                 # audit ours
    python scripts/check-shop-tabs.py --compare       # + reference dumps
    python scripts/check-shop-tabs.py --all           # include unused rows

Note on grepping an STL for keys: do not. Each key is immediately followed by a
u32 id whose low byte is often an ASCII digit (id 304 -> 30 01 00 00, and 0x30
is '0'), so a regex like `LSEL\\d+` silently reads "LSEL304" as "LSEL3040" and
reports a key that is present as missing. Parse the table.
"""
import argparse, io, os, struct, sys

STB_REL = os.path.join("3DDATA", "STB")
REFERENCE_ROOT = r"C:/Users/Thomas/Desktop/Testclients"
# Reference dumps, as <name>: <path to the dir holding 3DDATA>.
REFERENCE_DUMPS = {
    "667": "667/extracted data",
    "evo137": "Evo 137 client/Extracted data",
    "qq": "QQ-iROSE Online/QQiroseData",
    "roseza": "RoseZA test client/data",
    "ruff": "ruff/extracted data",
    "titan": "titanRose/data",
}

# Game columns. LIST_SELL: 0 = internal description, 1 = STL key, 2..49 = slots.
SELL_NAME_COL = 0
SELL_KEY_COL = 1
SELL_FIRST_SLOT_COL = 2
SELL_SLOT_COUNT = 48
# LIST_NPC: 21..24 are the four shop tabs, 27 is NPC_TYPE (999 = a real NPC).
NPC_NAME_COL = 0
NPC_SHOP_TAB_COLS = (21, 22, 23, 24)
NPC_TYPE_COL = 27
NPC_TYPE_REAL = 999
# Tab 4 is only drawn when the NPC's .CON calls openStore(npc, 1).
SPECIAL_TAB_INDEX = 3


def read_pstr(buf, o):
    b = buf[o]
    o += 1
    if b & 0x80:
        b2 = buf[o]
        o += 1
        n = (b2 << 7) | (b - 0x80)
    else:
        n = b
    return buf[o:o + n], o + n


def stl_keys(path):
    """The set of keys an STL defines. Handles the NRST01/ITST01/QEST01 header
    uniformly -- only the key table is needed here, and that part is shared."""
    buf = open(path, "rb").read()
    fmt, o = read_pstr(buf, 0)
    if fmt not in (b"NRST01", b"ITST01", b"QEST01"):
        raise ValueError(f"{path}: unknown STL identifier {fmt!r}")
    count, = struct.unpack_from("<I", buf, o)
    o += 4
    keys = set()
    for _ in range(count):
        k, o = read_pstr(buf, o)
        o += 4  # u32 id
        keys.add(k.decode("latin-1"))
    return keys


def stb_read(path):
    f = io.BytesIO(open(path, "rb").read())
    if f.read(4) != b"STB1":
        raise ValueError(f"{path}: not an STB1 file")
    offset, rows, cols = struct.unpack("<III", f.read(12))
    f.seek(offset)

    def pstr():
        n, = struct.unpack("<H", f.read(2))
        return f.read(n).decode("utf-8", "replace")

    return [[pstr() for _ in range(cols - 1)] for _ in range(rows - 1)]


def cell_int(row, col):
    try:
        return int(row[col])
    except (IndexError, ValueError):
        return 0


def stock(sell_row):
    return sum(
        1 for c in range(SELL_FIRST_SLOT_COL, SELL_FIRST_SLOT_COL + SELL_SLOT_COUNT)
        if cell_int(sell_row, c) > 0
    )


def load(root):
    stb = os.path.join(root, STB_REL)
    return (
        stb_read(os.path.join(stb, "LIST_NPC.STB")),
        stb_read(os.path.join(stb, "LIST_SELL.STB")),
        stl_keys(os.path.join(stb, "LIST_SELL_S.STL")),
    )


def shop_tab_users(npc_tbl):
    """LIST_SELL row -> [(npc row, npc name, tab index)]. A row nothing points
    at cannot be seen in game, however broken it looks."""
    used = {}
    for i, row in enumerate(npc_tbl):
        if cell_int(row, NPC_TYPE_COL) != NPC_TYPE_REAL:
            continue
        for tab, col in enumerate(NPC_SHOP_TAB_COLS):
            sell_row = cell_int(row, col)
            if sell_row > 0:
                name = row[NPC_NAME_COL] if row else ""
                used.setdefault(sell_row, []).append((i, name or f"npc {i}", tab))
    return used


def out(line):
    sys.stdout.buffer.write(line.encode("utf-8") + b"\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--compare", action="store_true",
                    help="also report how the reference dumps stock each broken row")
    ap.add_argument("--all", action="store_true",
                    help="report every LIST_SELL row, not just ones an NPC uses")
    args = ap.parse_args()

    data_root = os.path.join(args.root, "data")
    if not os.path.isdir(os.path.join(data_root, STB_REL)):
        raise SystemExit(f"not found: {os.path.join(data_root, STB_REL)} "
                         "(run from the repo root or pass --root)")
    npc_tbl, sell_tbl, keys = load(data_root)
    used = shop_tab_users(npc_tbl)
    out(f"LIST_SELL.STB: {len(sell_tbl)} rows; LIST_SELL_S.STL: {len(keys)} keys; "
        f"{len(used)} rows referenced by {sum(len(v) for v in used.values())} NPC tabs")

    refs = {}
    if args.compare:
        for name, rel in REFERENCE_DUMPS.items():
            path = os.path.join(REFERENCE_ROOT, rel)
            try:
                refs[name] = stb_read(os.path.join(path, STB_REL, "LIST_SELL.STB"))
            except Exception as e:
                out(f"  (reference {name} unavailable: {e})")

    rows = range(1, len(sell_tbl)) if args.all else sorted(used)
    nameless, empty, special = [], [], []
    for row in rows:
        if row >= len(sell_tbl):
            out(f"row {row}: past the end of LIST_SELL.STB, referenced by "
                + ", ".join(u[1] for u in used.get(row, [])))
            continue
        cells = sell_tbl[row]
        key = cells[SELL_KEY_COL].strip() if len(cells) > SELL_KEY_COL else ""
        n = stock(cells)
        problems = []
        if not key:
            problems.append("no STL key")
        elif key not in keys:
            problems.append(f"key {key} not in LIST_SELL_S.STL")
        if n == 0:
            problems.append("no items")
        if problems:
            who = ", ".join(f"{u[1]} tab {u[2] + 1}" for u in used.get(row, [])) or "unused"
            desc = cells[SELL_NAME_COL] if len(cells) > SELL_NAME_COL else ""
            line = f"row {row:4}: {'; '.join(problems):<40} [{desc}] <- {who}"
            if refs:
                have = [f"{name}={stock(t[row])}" for name, t in refs.items()
                        if row < len(t) and stock(t[row]) > 0]
                line += "\n            reference stock: " + (", ".join(have) or "none")
            out(line)
            if "no STL key" in problems or any("not in" in p for p in problems):
                nameless.append(row)
            if n == 0:
                empty.append(row)
        for _, _, tab in used.get(row, []):
            if tab == SPECIAL_TAB_INDEX:
                special.append(row)

    out("")
    out(f"{len(nameless)} tab(s) will draw a blank caption: {nameless}")
    out(f"{len(empty)} tab(s) will open with no items: {empty}")
    out(f"{len(set(special))} row(s) sit in tab 4, which the client only draws when "
        f"the NPC's .CON calls openStore(npc, 1): {sorted(set(special))}")


if __name__ == "__main__":
    sys.exit(main())
