"""Give players a way to Karkia.

Karkia has no entrance: not one warp gate anywhere in the game points into it, and
the ten gates `import-karkia.py --stage 2` restored are all *internal*. Before this
script only a GM warp got you there.

So the trip is NPC-driven, exactly like Oro's:

    [Historian] Jones, Junon Polis (npc 1104)         --> zone 86, the Church
    [Interplanetary Guide] Nova, Orlean Portal Temple --> zone 86, the Church
                                          (npc 2101)

Both already carry a travel dialog, so the option is appended to what they have
rather than replacing it -- which is the whole point of the QEX1 appendix.

**Why the Church and not the Cemetery.** The Church is Karkia's town: no monsters,
and ten NPCs once stage 6 places them. The Cemetery is a 7x7 field of level-211+
monsters whose only route to the Church is a one-way gate in its far corner
(chunk 35_35). Landing players in the town is the same shape as Oro dropping them
in the Portal Room rather than the Wasteland.

Note the Church currently has **no way out** -- Jrose gave it a gate in and none
back, and its NPCs are not placed yet. Leaving is a Return scroll until a later
stage or a quest adds one. That is a known gap, not an oversight here.

This script writes only the QSD trigger. The dialog options are appended by the
quest editor, which owns the .CON codec:

    quest-editor con-warp <data> 1104 karkia Karkia-TravelToChurch --write
    quest-editor con-warp <data> 2101 karkia Karkia-TravelToChurch --write

(run-karkia-travel.ps1 does both plus this script, with the dialog text filled in.)

The destination is the zone's own `start` event position, read out of the .ZON
rather than hard-coded -- see add-oro-travel.py's zon_event_positions(), which is
reused here, for why that is not the arithmetic you would guess.

No level gate, for the same reason Oro has none: the real gate is the monsters.

Idempotent, --dry-run, --selftest.
"""
import argparse
import importlib.util
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
QSD = os.path.join(DATA, "3DDATA", "QUESTDATA", "QP401.QSD")

TRIGGER = "Karkia-TravelToChurch"
TRAVEL_PATTERN = "KarkiaTravel"
ZONE_CHURCH = 86
CHURCH_ZON = os.path.join(DATA, "3DDATA", "MAPS", "KARKIA", "KCHURCH", "KCHURCH.ZON")

# The NPCs that get the option. Both are placed and both already have a .CON.
HOSTS = [
    (1104, "[Historian] Jones",            "Junon Polis (zone 2)"),
    (2101, "[Interplanetary Guide] Nova",  "Orlean Portal Temple (zone 73)"),
]

REWD_007 = 0x01000000 | 7
# A real REWD_007 to copy the on-disk shape from, so we are not hand-rolling one.
TEMPLATE_TRIGGER = "PvP10-061"
TEMPLATE_QSD = os.path.join(DATA, "3DDATA", "QUESTDATA", "PVP10.QSD")


def load(name):
    """Reuse the QSD splice helpers and the .ZON reader already in scripts/."""
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name + ".py", "--help"]
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    finally:
        sys.argv = saved
    return mod


def landing_spot():
    travel = load("add-oro-travel")
    pos = travel.zon_event_positions(CHURCH_ZON)
    if "start" not in pos:
        raise SystemExit(f"{CHURCH_ZON}: no 'start' event position (have {sorted(pos)})")
    x, y = pos["start"]
    return int(round(x)), int(round(y))


def build(dry):
    fate = load("import-oro-fate")
    blob = open(QSD, "rb").read()
    if fate.qsd_has_trigger(blob, TRIGGER):
        print(f"   {TRIGGER} already present, nothing to do")
        return

    tmpl = fate.qsd_find_entity(open(TEMPLATE_QSD, "rb").read(),
                                TEMPLATE_TRIGGER, REWD_007)
    if tmpl is None:
        raise SystemExit(f"no REWD_007 template in {TEMPLATE_TRIGGER}")

    x, y = landing_spot()
    # STR_REWD_007: int iZoneSN; int iX; int iY; BYTE btPartyOpt.
    # Party option 0 -- dragging someone else's whole party to another planet on
    # one member's click is not what anyone means by "yes".
    rew = fate.qsd_patch(tmpl, (0, "<iii", (ZONE_CHURCH, x, y)), (12, "<B", (0,)))
    trigger = fate.qsd_build_trigger(TRIGGER, [], [rew])
    print(f"   {TRIGGER:<24} -> zone {ZONE_CHURCH} at ({x}, {y})  "
          f"[displayed {x/100:.0f},{y/100:.0f}]")

    out = fate.qsd_append_pattern(blob, TRAVEL_PATTERN, [trigger])
    ok, consumed = fate.qsd_parse_ok(out)
    if not ok:
        raise SystemExit(f"rebuilt QSD does not re-parse ({consumed}/{len(out)})")
    if not fate.qsd_has_trigger(out, TRIGGER):
        raise SystemExit(f"{TRIGGER} missing after rebuild")
    got = fate.qsd_find_entity(out, TRIGGER, REWD_007)
    gz, gx, gy = struct.unpack_from("<iii", got, 8)
    if (gz, gx, gy) != (ZONE_CHURCH, x, y):
        raise SystemExit(f"{TRIGGER}: wrote ({gz},{gx},{gy}), wanted "
                         f"({ZONE_CHURCH},{x},{y})")
    fate.write_file(QSD, out, dry)
    print(f"   QP401.QSD {len(blob)} -> {len(out)} bytes, re-parsed clean")


def selftest():
    print("== selftest")
    x, y = landing_spot()
    # A world position inside a 64-map zone is ~5.12M/2 units; anything near zero
    # means the half-zone bias or the y/z swap went wrong.
    if not (100_000 < x < 10_000_000 and 100_000 < y < 10_000_000):
        raise SystemExit(f"implausible landing spot ({x}, {y})")
    print(f"   KCHURCH.ZON start = ({x}, {y})")

    fate = load("import-oro-fate")
    for path in (QSD, TEMPLATE_QSD):
        blob = open(path, "rb").read()
        ok, consumed = fate.qsd_parse_ok(blob)
        if not ok:
            raise SystemExit(f"{os.path.basename(path)} does not parse "
                             f"({consumed}/{len(blob)})")
        print(f"   {os.path.basename(path):<14} parses exactly ({len(blob)} bytes)")
    if fate.qsd_find_entity(open(TEMPLATE_QSD, "rb").read(),
                            TEMPLATE_TRIGGER, REWD_007) is None:
        raise SystemExit(f"no REWD_007 template in {TEMPLATE_TRIGGER}")
    print(f"   REWD_007 template found in {TEMPLATE_TRIGGER}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    print("== Karkia travel trigger")
    build(args.dry_run)
    print("\ndone." + ("  (dry run -- nothing written)" if args.dry_run else ""))
    if not args.dry_run:
        print("next: append the dialog options --")
        for npc, who, where in HOSTS:
            print(f"   quest-editor con-warp <data> {npc} karkia {TRIGGER} --write"
                  f"    # {who}, {where}")
        print("then bake + restart. Appended options need the QEX1-aware client,")
        print("so deploy client and data together.")


if __name__ == "__main__":
    main()
