# ROSE GM Item Browser

`gm-item-browser.exe` is a read-only Windows companion for alpha testers. It
shares the NPC shop editor's item categories, icon atlas reader and DDS decoder.

## For testers

1. Keep the supplied `data` folder beside `gm-item-browser.exe` and launch it.
   The loose data loads automatically, without a game installation or VFS.
2. Search by name, ID, or `type:ID` (for example `8:1453`). Multiple search words
   must all match. Use item type, subtype, and minimum/maximum stat filters to
   narrow the list; blank bounds are unlimited.
3. Click **Copy** on a row, then paste the command into game chat. Select an item
   name to see its description, stats, and quantity control for stackable items.

Use **Open data folder** to choose another loose data set, or **Open VFS** to
select a game's `data.idx`. The tool also accepts an extracted folder's `3DDATA`
or `STB` subfolder, or a path on the command line. It reads every archive listed in `data.idx`,
including `rose_2.vfs` and later parts, without extracting them. A packed source
uses its archive data consistently; choose the extracted folder to inspect
unpacked development changes. Use **Reload** after updating game data.

Automatic loading prefers `data/` beside the executable, then data directly
beside the executable (including `data.idx`), then those same locations under
the working directory. An explicit command-line path overrides automatic loading.

Names and descriptions come from the English STL tables, with raw STB names as
a fallback. Equipment variants include their translated `STR_ITEMPREFIX.STL`
prefix (for example, **Golden Trunket Armor**), which is also searchable. If the
prefix table is missing from an older package, prefixed equipment uses its raw
table name and the browser shows a data warning.
The item ID is the table row position used by the game. The type
number shown beside the category is the first `/item` argument; **subtype** is
the separate numeric equipment/item class stored in the table.

**Stats:** level is the character-level requirement (0 means no level gate).
Attack, defense and resistance are base table values, before item bonuses,
refinement, gems and character calculations. A dash means a stat does not apply;
setting a range excludes those rows. Vehicle attack and consumable requirements
use their own table layouts. Invalid ranges show an error and match no items.

**Commands:** `/item type ID` creates one item. Stackable quantities are limited
to the server's range of 1–100. Equipment commands omit the third argument,
because the server interprets it as an appraisal stat. Rows outside IDs 1–2047
or with no icon have no Copy action; uncheck **Spawnable items only** to inspect
them. GM access is still required in the game; this tool does not grant access
or connect to the server.

## Build and run

From the repository's `src` directory:

```powershell
cargo +stable-i686-pc-windows-msvc build --release -p npc-shop-editor --bin gm-item-browser
../bin/release/gm-item-browser.exe ../data
```

To build a portable package, run from the repository root:

```powershell
./scripts/package-gm-item-browser.ps1
```

This creates `dist/gm-item-browser/` with the following layout:

```text
gm-item-browser.exe
README.txt
data/
  3DDATA/
    STB/           (14 item tables, their translations, and STR_ITEMPREFIX.STL)
    CONTROL/RES/   (ITEM1.TSI and the icon sheets it references)
```

Only the required loose assets are copied, and their hashes are verified against
the source. Optional `-DataRoot` and `-OutputDir` parameters select different
source/output folders. Regenerate and redistribute the package after changing
item data so testers see the same catalog as the server.

Testers need no Rust installation or editor. VFS loading remains optional;
keep all the game's `rose*.vfs` archives alongside the selected `data.idx` when
using that option.

The existing editor still runs with `cargo run -p npc-shop-editor`.

## Validation

From `src`:

```powershell
cargo +stable-i686-pc-windows-msvc test -p npc-shop-editor
cargo +stable-i686-pc-windows-msvc test -p npc-shop-editor workspace_catalog_and_icons_from_loose_and_packed_data -- --ignored --nocapture
```

The second check requires this workspace's `data/` and `Exes/` assets. It loads
the catalog and decodes every referenced item icon from both sources. Unit
fixtures cover mixed stat schemas, high item IDs, command arguments, filters,
multiple archives, deleted entries, truncated archives, and offsets above 2 GB.
