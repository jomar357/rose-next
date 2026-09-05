use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{anyhow, Context, Result};
use roselib::files::stl::{StringTableLanguage, StringTableRow};
use roselib::files::{STB, STL};
use roselib::io::RoseFile;

/// Item category = which STB the item lives in.
/// The numeric value is the ROSE item type, which is also the encoding used
/// by the game's shop-slot encoding (see common/store_item_code.h).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum ItemCategory {
    Face = 1,
    Cap = 2,
    Body = 3,
    Arms = 4,
    Foot = 5,
    Back = 6,
    Jewel = 7,
    Weapon = 8,
    SubWpn = 9,
    UseItem = 10,
    Gem = 11,
    Natural = 12,
    QuestItem = 13,
    Vehicle = 14,
}

impl ItemCategory {
    pub const ALL: &'static [ItemCategory] = &[
        ItemCategory::Face,
        ItemCategory::Cap,
        ItemCategory::Body,
        ItemCategory::Arms,
        ItemCategory::Foot,
        ItemCategory::Back,
        ItemCategory::Jewel,
        ItemCategory::Weapon,
        ItemCategory::SubWpn,
        ItemCategory::UseItem,
        ItemCategory::Gem,
        ItemCategory::Natural,
        ItemCategory::QuestItem,
        ItemCategory::Vehicle,
    ];

    pub fn stb_name(&self) -> &'static str {
        match self {
            ItemCategory::Face => "LIST_FACEITEM.STB",
            ItemCategory::Cap => "LIST_CAP.STB",
            ItemCategory::Body => "LIST_BODY.STB",
            ItemCategory::Arms => "LIST_ARMS.STB",
            ItemCategory::Foot => "LIST_FOOT.STB",
            ItemCategory::Back => "LIST_BACK.STB",
            ItemCategory::Jewel => "LIST_JEWEL.STB",
            ItemCategory::Weapon => "LIST_WEAPON.STB",
            ItemCategory::SubWpn => "LIST_SUBWPN.STB",
            ItemCategory::UseItem => "LIST_USEITEM.STB",
            ItemCategory::Gem => "LIST_JEMITEM.STB",
            ItemCategory::Natural => "LIST_NATURAL.STB",
            ItemCategory::QuestItem => "LIST_QUESTITEM.STB",
            ItemCategory::Vehicle => "LIST_PAT.STB",
        }
    }

    pub fn display(&self) -> &'static str {
        match self {
            ItemCategory::Face => "Face",
            ItemCategory::Cap => "Helmet",
            ItemCategory::Body => "Body",
            ItemCategory::Arms => "Gauntlet",
            ItemCategory::Foot => "Boots",
            ItemCategory::Back => "Back",
            ItemCategory::Jewel => "Jewel",
            ItemCategory::Weapon => "Weapon",
            ItemCategory::SubWpn => "Sub Weapon",
            ItemCategory::UseItem => "Consumable",
            ItemCategory::Gem => "Gem",
            ItemCategory::Natural => "Material",
            ItemCategory::QuestItem => "Quest Item",
            ItemCategory::Vehicle => "Vehicle Part",
        }
    }
}

// Keep these and the codec in sync with
// src/common/include/rose/common/store_item_code.h (client and server).
const STORE_WIDE_BASE: i32 = 100_000;
const STORE_LEGACY_MAX_ITEM_NO: i32 = 999;
const STORE_MAX_ITEM_NO: i32 = 2047;

/// Decode either a legacy or wide LIST_SELL.STB slot into (type, id).
pub fn decode_item_no(full: i32) -> Option<(ItemCategory, i32)> {
    if full <= 0 {
        return None;
    }
    let base = if full >= STORE_WIDE_BASE {
        STORE_WIDE_BASE
    } else {
        1000
    };
    let ty = full / base;
    let id = full % base;
    if !(1..=STORE_MAX_ITEM_NO).contains(&id) {
        return None;
    }
    let cat = ItemCategory::ALL.iter().find(|c| **c as i32 == ty)?;
    Some((*cat, id))
}

/// Preserve legacy codes for IDs up to 999; larger IDs need the wide form
/// or the excess digits silently turn them into a different item category.
pub fn encode_item_no(cat: ItemCategory, id: i32) -> i32 {
    let base = if id <= STORE_LEGACY_MAX_ITEM_NO {
        1000
    } else {
        STORE_WIDE_BASE
    };
    (cat as i32) * base + id
}

#[derive(Debug, Clone)]
pub struct Item {
    pub category: ItemCategory,
    pub id: i32,
    pub name: String,
    pub icon_no: i32,
}

#[derive(Debug, Clone)]
pub struct Npc {
    pub id: i32,
    pub name: String,
    /// Roselib row index this NPC was read from in LIST_NPC.STB. Used as the
    /// authoritative target when writing edits back — don't trust `id`, which
    /// is just the root-column label.
    pub roselib_row: usize,
    /// The four columns [21,22,23,24] of LIST_NPC.STB. 0 = no tab.
    pub shop_tab_rows: [i32; 4],
}

impl Npc {
    pub fn has_shop(&self) -> bool {
        self.shop_tab_rows.iter().any(|r| *r > 0)
    }
}

/// A single shop tab (row of LIST_SELL.STB).
#[derive(Debug, Clone)]
pub struct ShopTab {
    pub row: usize, // 1-based row index in LIST_SELL.STB
    /// Internal STB description; use shop_tab_label for the in-game name.
    pub name: String,
    pub items: Vec<i32>, // full encoded item numbers, fixed length 48
    pub dirty: bool,
}

pub const SHOP_TAB_SLOT_COUNT: usize = 48;

/// The whole loaded workspace.
pub struct DataSet {
    pub root: PathBuf,

    pub npc_stb: STB,
    pub sell_stb: STB,

    pub npcs: Vec<Npc>,
    pub shop_tabs: HashMap<usize, ShopTab>, // row -> tab; filled lazily on edit
    /// ref_count[row] = how many NPC tab-refs point at LIST_SELL row `row`
    pub tab_ref_counts: HashMap<usize, usize>,
    pub item_db: ItemDb,
    pub zones: Vec<crate::zones::Zone>,
    /// English in-game shop labels keyed by LIST_SELL's STL link, not row ID.
    shop_names: HashMap<String, String>,

    pub any_npc_dirty: bool,
}

pub struct ItemDb {
    pub by_category: HashMap<ItemCategory, Vec<Item>>,
}

impl ItemDb {
    pub fn lookup(&self, cat: ItemCategory, id: i32) -> Option<&Item> {
        self.by_category
            .get(&cat)
            .and_then(|v| v.iter().find(|it| it.id == id))
    }

    pub fn all(&self) -> impl Iterator<Item = &Item> {
        self.by_category.values().flat_map(|v| v.iter())
    }
}

impl DataSet {
    pub fn load(root: &Path) -> Result<Self> {
        let stb_dir = resolve_stb_dir(root)?;

        let npc_stb =
            load_stb(&stb_dir, "LIST_NPC.STB").context("loading LIST_NPC.STB")?;
        let sell_stb =
            load_stb(&stb_dir, "LIST_SELL.STB").context("loading LIST_SELL.STB")?;
        let shop_names = load_shop_names(&stb_dir).unwrap_or_else(|e| {
            log::warn!("shop translations unavailable: {:#}", e);
            HashMap::new()
        });

        let npcs = collect_npcs(&npc_stb);
        let tab_ref_counts = count_tab_refs(&npcs);
        let item_db = ItemDb {
            by_category: load_all_item_tables(&stb_dir)?,
        };

        let zones = match crate::zones::load_zones(root, &stb_dir) {
            Ok(z) => z,
            Err(e) => {
                log::warn!("zone load failed: {}", e);
                Vec::new()
            }
        };

        Ok(Self {
            root: root.to_path_buf(),
            npc_stb,
            sell_stb,
            npcs,
            shop_tabs: HashMap::new(),
            tab_ref_counts,
            item_db,
            zones,
            shop_names,
            any_npc_dirty: false,
        })
    }

    /// Load (and cache) a shop tab from LIST_SELL.STB.
    ///
    /// Note: LIST_NPC's shop-tab columns store the *roselib data index*
    /// directly (matching the C++ server, which uses 0-based indexing into
    /// its already-header-stripped data), so no `row - 1` adjustment.
    pub fn get_or_load_tab(&mut self, row: usize) -> Option<&mut ShopTab> {
        if row == 0 || row >= self.sell_stb.data.len() {
            return None;
        }
        if !self.shop_tabs.contains_key(&row) {
            let cells = &self.sell_stb.data[row];
            // C++ col 0 (= roselib col 1) is the raw tab name
            // (e.g. "Soldier Skill"). C++ col 2..49 = item slots → roselib 3..50.
            let name = cells.get(1).cloned().unwrap_or_default();
            let mut items = Vec::with_capacity(SHOP_TAB_SLOT_COUNT);
            for slot in 0..SHOP_TAB_SLOT_COUNT {
                // C++ col 2+T → roselib col 3+T
                let col = 2 + 1 + slot;
                let v = cells
                    .get(col)
                    .and_then(|s| s.parse::<i32>().ok())
                    .unwrap_or(0);
                items.push(v);
            }
            self.shop_tabs.insert(
                row,
                ShopTab {
                    row,
                    name,
                    items,
                    dirty: false,
                },
            );
        }
        self.shop_tabs.get_mut(&row)
    }

    pub fn ref_count(&self, row: usize) -> usize {
        *self.tab_ref_counts.get(&row).unwrap_or(&0)
    }

    /// Match the English client's GetStoreTabName: resolve the STL key in
    /// game column 1 (roselib column 2). Column 0 is an internal description.
    pub fn shop_tab_label(&self, row: usize) -> String {
        let cells = self.sell_stb.data.get(row);
        if let Some(name) = cells
            .and_then(|cells| cells.get(2))
            .and_then(|key| self.shop_names.get(key))
        {
            return name.clone();
        }
        let description = cells
            .and_then(|cells| cells.get(1))
            .filter(|name| !name.trim().is_empty())
            .cloned()
            .unwrap_or_else(|| format!("Tab {}", row));
        format!("{} (untranslated)", description)
    }

    /// Assign a new, empty shop to an unused NPC tab. Reuse only a label and
    /// its STL key: the client reads the translated name through column 2,
    /// so an arbitrary inline name alone would produce a blank in-game tab.
    pub fn create_shop_tab(
        &mut self,
        npc_idx: usize,
        tab_slot: usize,
        label_row: usize,
    ) -> Result<usize> {
        let assigned = self
            .npcs
            .get(npc_idx)
            .and_then(|npc| npc.shop_tab_rows.get(tab_slot))
            .context("invalid NPC or tab slot")?;
        if *assigned != 0 {
            return Err(anyhow!("this tab already has a shop assigned"));
        }
        let source = self
            .sell_stb
            .data
            .get(label_row)
            .filter(|_| label_row > 0)
            .context("shop label not found")?;
        let name = source
            .get(1)
            .filter(|s| !s.trim().is_empty())
            .context("shop label has no name")?
            .clone();
        let key = source
            .get(2)
            .filter(|s| !s.trim().is_empty())
            .context("shop label has no translation key")?
            .clone();
        if self.sell_stb.headers.len() < 3 + SHOP_TAB_SLOT_COUNT {
            return Err(anyhow!("shop table does not have 48 item columns"));
        }
        let row = self.sell_stb.data.len();
        if row == 0 || row > i16::MAX as usize {
            return Err(anyhow!(
                "new shop row is outside the game's supported range"
            ));
        }
        let mut cells = vec![String::new(); self.sell_stb.headers.len()];
        cells[0] = row.to_string();
        cells[1] = name.clone();
        cells[2] = key;
        for cell in &mut cells[3..3 + SHOP_TAB_SLOT_COUNT] {
            *cell = "0".to_string();
        }
        self.sell_stb.data.push(cells);
        self.shop_tabs.insert(
            row,
            ShopTab {
                row,
                name,
                items: vec![0; SHOP_TAB_SLOT_COUNT],
                dirty: true,
            },
        );
        self.npcs[npc_idx].shop_tab_rows[tab_slot] = row as i32;
        self.tab_ref_counts.insert(row, 1);
        self.any_npc_dirty = true;
        Ok(row)
    }

    /// Place an item in an explicit slot, or the first empty slot when omitted.
    /// Resolve the destination before copy-on-write so a full/invalid target
    /// cannot duplicate a shared shop or mark it modified without an edit.
    pub fn place_shop_item(
        &mut self,
        npc_idx: usize,
        tab_slot: usize,
        destination: Option<usize>,
        item: i32,
    ) -> Result<usize> {
        let row = self
            .npcs
            .get(npc_idx)
            .and_then(|npc| npc.shop_tab_rows.get(tab_slot))
            .copied()
            .filter(|row| *row > 0)
            .context("no shop tab selected")? as usize;
        let tab = self.get_or_load_tab(row).context("shop tab not found")?;
        let slot = match destination {
            Some(slot) if slot < tab.items.len() => slot,
            Some(_) => return Err(anyhow!("shop slot is out of range")),
            None => tab
                .items
                .iter()
                .position(|value| *value == 0)
                .context("shop is full; select a slot to replace an item")?,
        };
        let row = self.begin_tab_edit(npc_idx, tab_slot)?;
        let tab = self.get_or_load_tab(row).context("shop tab not found")?;
        tab.items[slot] = item;
        tab.dirty = true;
        Ok(slot)
    }

    /// Begin a mutation on `(npc_idx, slot)`. If the referenced tab is shared
    /// with other NPCs, create a copy (append new row to LIST_SELL.STB) and
    /// retarget this NPC to the new row.
    ///
    /// Returns the effective tab row that should now be edited.
    pub fn begin_tab_edit(&mut self, npc_idx: usize, tab_slot: usize) -> Result<usize> {
        let npc = self
            .npcs
            .get_mut(npc_idx)
            .ok_or_else(|| anyhow!("invalid npc index"))?;
        let row = npc.shop_tab_rows[tab_slot];
        if row <= 0 {
            return Err(anyhow!("npc has no shop tab at slot {}", tab_slot));
        }
        let row = row as usize;
        let refs = *self.tab_ref_counts.get(&row).unwrap_or(&1);

        if refs <= 1 {
            return Ok(row);
        }

        // Copy-on-write: append a new row cloning the source.
        let source = self.sell_stb.data[row].clone();
        self.sell_stb.data.push(source);
        let new_row = self.sell_stb.data.len() - 1;

        // Retarget npc
        npc.shop_tab_rows[tab_slot] = new_row as i32;
        self.any_npc_dirty = true;

        // Update ref counts
        *self.tab_ref_counts.entry(row).or_insert(1) -= 1;
        self.tab_ref_counts.insert(new_row, 1);

        // Migrate cached tab (if any) to the new row so pending edits follow
        if let Some(mut tab) = self.shop_tabs.remove(&row) {
            tab.row = new_row;
            tab.dirty = true;
            self.shop_tabs.insert(new_row, tab);
        } else {
            // Force-load the new tab so callers see the fresh copy.
            let _ = self.get_or_load_tab(new_row);
        }

        Ok(new_row)
    }

    /// Apply any pending in-memory tab edits back into `sell_stb.data`, then
    /// write both STBs to disk. Backs up the originals to `.bak` first.
    pub fn save(&mut self) -> Result<()> {
        let stb_dir = resolve_stb_dir(&self.root)?;
        let sell_path = stb_dir.join("LIST_SELL.STB");
        let npc_path = stb_dir.join("LIST_NPC.STB");

        // Apply tab edits back into the STB cells.
        for tab in self.shop_tabs.values() {
            if !tab.dirty {
                continue;
            }
            let data_row = tab.row;
            while self.sell_stb.data.len() <= data_row {
                // Shouldn't happen, but keep bounds safe.
                self.sell_stb.data.push(Vec::new());
            }
            let row_cells = &mut self.sell_stb.data[data_row];
            // +1 offset everywhere: roselib includes the root column, C++ skips it.
            while row_cells.len() < 3 + SHOP_TAB_SLOT_COUNT {
                row_cells.push(String::from("0"));
            }
            // Preserve the internal description in roselib col 1. The client
            // resolves its displayed name through the STL key in col 2.
            if row_cells.len() > 1 {
                row_cells[1] = tab.name.clone();
            }
            for (slot, v) in tab.items.iter().enumerate() {
                row_cells[3 + slot] = v.to_string();
            }
        }

        // Apply NPC shop-tab-row edits back into LIST_NPC.STB.
        if self.any_npc_dirty {
            for npc in &self.npcs {
                let data_row = npc.roselib_row;
                if data_row >= self.npc_stb.data.len() {
                    continue;
                }
                let cells = &mut self.npc_stb.data[data_row];
                // C++ cols 21..24 → roselib cols 22..25 (root column offset).
                for (i, col) in [22, 23, 24, 25].iter().enumerate() {
                    if cells.len() > *col {
                        cells[*col] = npc.shop_tab_rows[i].to_string();
                    }
                }
            }
        }

        backup_once(&sell_path)?;
        backup_once(&npc_path)?;

        self.sell_stb
            .write_to_path(&sell_path)
            .map_err(|e| anyhow!("writing LIST_SELL.STB: {}", e))?;
        self.npc_stb
            .write_to_path(&npc_path)
            .map_err(|e| anyhow!("writing LIST_NPC.STB: {}", e))?;

        // Mark all tabs clean post-save.
        for tab in self.shop_tabs.values_mut() {
            tab.dirty = false;
        }
        self.any_npc_dirty = false;
        Ok(())
    }
}

pub fn resolve_stb_dir(root: &Path) -> Result<PathBuf> {
    // Accept both "root/3DDATA/STB" and "root" (if the user picked 3DDATA itself).
    let candidates = [
        root.join("3DDATA").join("STB"),
        root.join("3ddata").join("stb"),
        root.join("STB"),
        root.to_path_buf(),
    ];
    for c in candidates.iter() {
        if c.join("LIST_NPC.STB").exists() || c.join("list_npc.stb").exists() {
            return Ok(c.clone());
        }
    }
    Err(anyhow!(
        "could not find 3DDATA/STB/LIST_NPC.STB under '{}'",
        root.display()
    ))
}

pub fn resolve_icon_dir(root: &Path) -> Result<PathBuf> {
    // Resolve the same STB directory as DataSet, so selecting the data root,
    // 3DDATA, or STB itself all finds the sibling CONTROL/RES directory.
    let stb_dir = resolve_stb_dir(root)?;
    let data_dir = stb_dir.parent().context("STB directory has no parent")?;
    let candidates = [data_dir.join("CONTROL/RES"), data_dir.join("control/res")];
    for c in candidates.iter() {
        if c.exists() {
            return Ok(c.clone());
        }
    }
    Err(anyhow!(
        "could not find 3DDATA/CONTROL/RES under '{}'",
        root.display()
    ))
}

fn load_shop_names(dir: &Path) -> Result<HashMap<String, String>> {
    let path = file_ci(dir, "LIST_SELL_S.STL")?;
    let stl = STL::from_path(&path).map_err(|e| anyhow!("reading {}: {}", path.display(), e))?;
    let english = stl
        .language_tables
        .iter()
        .find(|table| table.language == StringTableLanguage::English)
        .context("LIST_SELL_S.STL has no English language table")?;
    Ok(stl
        .keys
        .iter()
        .zip(&english.rows)
        .filter_map(|(key, row)| {
            let StringTableRow::NormalRow(row) = row else {
                return None;
            };
            let name = row.text.trim();
            if name.is_empty() {
                return None;
            }
            Some((key.name.clone(), name.to_string()))
        })
        .collect())
}

fn load_stb(dir: &Path, name: &str) -> Result<STB> {
    let path = file_ci(dir, name)?;
    STB::from_path(&path).map_err(|e| anyhow!("STB::from_path({}): {}", path.display(), e))
}

/// Case-insensitive file lookup in a directory.
fn file_ci(dir: &Path, name: &str) -> Result<PathBuf> {
    let exact = dir.join(name);
    if exact.exists() {
        return Ok(exact);
    }
    let lower = name.to_ascii_lowercase();
    let upper = name.to_ascii_uppercase();
    for candidate in [dir.join(&lower), dir.join(&upper)] {
        if candidate.exists() {
            return Ok(candidate);
        }
    }
    for entry in fs::read_dir(dir).context("reading directory")? {
        let entry = entry?;
        let fname = entry.file_name();
        let fname_str = fname.to_string_lossy();
        if fname_str.eq_ignore_ascii_case(name) {
            return Ok(entry.path());
        }
    }
    Err(anyhow!("file not found: {}/{}", dir.display(), name))
}

fn collect_npcs(npc_stb: &STB) -> Vec<Npc> {
    let mut out = Vec::new();
    for (i, row) in npc_stb.data.iter().enumerate() {
        // roselib keeps the STB's root column at index 0, while the game's
        // `stb.cpp` skips it — so C++ column N maps to roselib column N+1.
        let col_i32 = |cpp_col: usize| -> i32 {
            row.get(cpp_col + 1)
                .and_then(|s| s.parse::<i32>().ok())
                .unwrap_or(0)
        };
        // NPC_TYPE (C++ col 27) — only type 999 is a real NPC.
        if col_i32(27) != 999 {
            continue;
        }
        // The root label doubles as the game-side NPC ID.
        let id = row
            .get(0)
            .and_then(|s| s.parse::<i32>().ok())
            .unwrap_or(i as i32);
        // C++ col 0 (= roselib col 1) is the raw display name for this build
        // (e.g. "[Weapon Seller] Raffle"). No STL lookup required.
        let name = row
            .get(1)
            .cloned()
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| format!("NPC {}", id));
        let shop_tab_rows = [col_i32(21), col_i32(22), col_i32(23), col_i32(24)];
        out.push(Npc {
            id,
            name,
            roselib_row: i,
            shop_tab_rows,
        });
    }
    out
}

fn count_tab_refs(npcs: &[Npc]) -> HashMap<usize, usize> {
    let mut counts: HashMap<usize, usize> = HashMap::new();
    for npc in npcs {
        for r in npc.shop_tab_rows.iter() {
            if *r > 0 {
                *counts.entry(*r as usize).or_insert(0) += 1;
            }
        }
    }
    counts
}

fn load_all_item_tables(stb_dir: &Path) -> Result<HashMap<ItemCategory, Vec<Item>>> {
    let mut out: HashMap<ItemCategory, Vec<Item>> = HashMap::new();
    for cat in ItemCategory::ALL {
        let stb = match load_stb(stb_dir, cat.stb_name()) {
            Ok(s) => s,
            Err(e) => {
                log::warn!("skipping {}: {}", cat.stb_name(), e);
                continue;
            }
        };
        let mut items = Vec::new();
        for (i, row) in stb.data.iter().enumerate() {
            // Root label doubles as the item ID (matches the game-side 0-based
            // index into the per-category STB).
            let id = row
                .get(0)
                .and_then(|s| s.parse::<i32>().ok())
                .unwrap_or(i as i32);
            // C++ col 0 (= roselib col 1) is the raw display name in this
            // build (e.g. "Wooden Sword"). No STL lookup needed.
            let name = row.get(1).cloned().unwrap_or_default();
            // ITEM_ICON_NO is C++ col 9 → roselib col 10.
            let icon_no = row
                .get(10)
                .and_then(|s| s.parse::<i32>().ok())
                .unwrap_or(0);
            if name.is_empty() && icon_no == 0 {
                continue;
            }
            items.push(Item {
                category: *cat,
                id,
                name,
                icon_no,
            });
        }
        out.insert(*cat, items);
    }
    Ok(out)
}

fn backup_once(path: &Path) -> Result<()> {
    let bak = path.with_extension({
        let mut s = path
            .extension()
            .map(|e| e.to_string_lossy().to_string())
            .unwrap_or_default();
        s.push_str(".bak");
        s
    });
    if !bak.exists() && path.exists() {
        fs::copy(path, &bak)
            .with_context(|| format!("backing up {} -> {}", path.display(), bak.display()))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn store_codes_match_game_format_at_legacy_and_wire_boundaries() {
        // Fixed expectations from the shared C++ shop codec, including the
        // reported Back #1001 collision and Huzam's existing weapon codes.
        for (cat, id, packed) in [
            (ItemCategory::Face, 1, 1001),
            (ItemCategory::Back, 999, 6999),
            (ItemCategory::Back, 1000, 601000),
            (ItemCategory::Back, 1001, 601001),
            (ItemCategory::Weapon, 1368, 801368),
            (ItemCategory::Weapon, 1379, 801379),
            (ItemCategory::UseItem, 1060, 1001060),
            (ItemCategory::Vehicle, 2047, 1402047),
        ] {
            assert_eq!(encode_item_no(cat, id), packed);
            assert_eq!(decode_item_no(packed), Some((cat, id)));
        }
        // The game also accepts the wide form for a low ID.
        assert_eq!(decode_item_no(600001), Some((ItemCategory::Back, 1)));
        for packed in [
            0,
            -1,
            999,
            1000,
            8000,
            100000,
            600000,
            602048,
            15001,
            i32::MAX,
        ] {
            assert_eq!(decode_item_no(packed), None, "invalid code {}", packed);
        }
    }

    #[test]
    #[ignore = "requires the workspace's extracted data assets"]
    fn workspace_wide_shop_items_resolve_and_catalog_ids_round_trip() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../data");
        let data = DataSet::load(&root).unwrap();
        let mut wide_count = 0;
        for row in &data.sell_stb.data {
            for packed in row
                .iter()
                .skip(3)
                .take(SHOP_TAB_SLOT_COUNT)
                .filter_map(|cell| cell.parse::<i32>().ok())
                .filter(|packed| *packed >= STORE_WIDE_BASE)
            {
                let (cat, id) = decode_item_no(packed).expect("wide shop code must decode");
                assert!(
                    data.item_db.lookup(cat, id).is_some(),
                    "missing item for {}",
                    packed
                );
                wide_count += 1;
            }
        }
        assert!(
            wide_count > 0,
            "expected existing wide shop codes in workspace data"
        );
        let mut catalog_count = 0;
        for item in data
            .item_db
            .all()
            .filter(|item| (1..=STORE_MAX_ITEM_NO).contains(&item.id))
        {
            assert_eq!(
                decode_item_no(encode_item_no(item.category, item.id)),
                Some((item.category, item.id)),
                "{}",
                item.name
            );
            catalog_count += 1;
        }
        println!(
            "Resolved {} existing wide shop entries; round-tripped {} catalog items",
            wide_count, catalog_count
        );
    }

    fn shared_shop() -> DataSet {
        let mut npc_stb = STB::new();
        npc_stb.headers = vec![String::new(); 26];
        npc_stb.data = vec![vec!["0".to_string(); 26]; 2];
        let npcs = (0..2)
            .map(|i| {
                npc_stb.data[i][0] = i.to_string();
                npc_stb.data[i][22] = "1".to_string();
                Npc {
                    id: i as i32,
                    name: format!("NPC {}", i),
                    roselib_row: i,
                    shop_tab_rows: [1, 0, 0, 0],
                }
            })
            .collect();
        let mut sell_stb = STB::new();
        sell_stb.headers = vec![String::new(); 3 + SHOP_TAB_SLOT_COUNT];
        sell_stb.data = vec![vec!["0".to_string(); 3 + SHOP_TAB_SLOT_COUNT]; 2];
        sell_stb.data[1][0] = "1".to_string();
        sell_stb.data[1][1] = "Weapons".to_string();
        sell_stb.data[1][2] = "LSEL1".to_string();
        sell_stb.data[1][3] = "8001".to_string();
        sell_stb.data[1][5] = "8002".to_string();
        DataSet {
            root: PathBuf::new(),
            npc_stb,
            sell_stb,
            npcs,
            shop_tabs: HashMap::new(),
            tab_ref_counts: HashMap::from([(1, 2)]),
            item_db: ItemDb {
                by_category: HashMap::new(),
            },
            zones: Vec::new(),
            shop_names: HashMap::from([("LSEL1".to_string(), "Weapon".to_string())]),
            any_npc_dirty: false,
        }
    }

    #[test]
    fn translated_shop_labels_do_not_replace_internal_descriptions() {
        let mut data = shared_shop();
        assert_eq!(data.shop_tab_label(1), "Weapon");
        data.get_or_load_tab(1).unwrap().name = "Darren - Weapon".to_string();
        assert_eq!(data.shop_tab_label(1), "Weapon");
        assert_eq!(data.sell_stb.data[1][1], "Weapons");
        let row = data.create_shop_tab(0, 1, 1).unwrap();
        assert_eq!(data.shop_tab_label(row), "Weapon");
        assert_eq!(data.sell_stb.data[row][1], "Weapons");
        assert_eq!(data.sell_stb.data[row][2], "LSEL1");
        data.shop_names.clear();
        assert_eq!(data.shop_tab_label(1), "Weapons (untranslated)");
    }

    #[test]
    #[ignore = "requires the workspace's extracted data assets"]
    fn workspace_darren_and_ministers_use_english_class_labels() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../data");
        let data = DataSet::load(&root).unwrap();
        for (npc_id, expected) in [
            (1081, vec!["Soldier", "Muse", "Hawker", "Dealer"]),
            (1086, vec!["Hawker"]),
            (1087, vec!["Dealer"]),
        ] {
            let npc = data.npcs.iter().find(|npc| npc.id == npc_id).unwrap();
            let labels: Vec<String> = npc
                .shop_tab_rows
                .iter()
                .filter(|row| **row > 0)
                .map(|row| data.shop_tab_label(*row as usize))
                .collect();
            assert_eq!(labels, expected, "NPC {}", npc_id);
            println!("NPC {}: {}", npc_id, labels.join(", "));
        }
    }

    #[test]
    fn creates_empty_tab_with_game_label_and_saves_items_and_npc_assignment() {
        let temp = tempfile::tempdir().unwrap();
        let mut data = shared_shop();
        data.root = temp.path().to_path_buf();
        let stb_dir = data.root.join("3DDATA/STB");
        fs::create_dir_all(&stb_dir).unwrap();
        data.npc_stb
            .write_to_path(&stb_dir.join("LIST_NPC.STB"))
            .unwrap();
        data.sell_stb
            .write_to_path(&stb_dir.join("LIST_SELL.STB"))
            .unwrap();
        let original_rows = data.sell_stb.data.clone();
        let original_npcs = data.npc_stb.data.clone();

        // All three unused tabs can be filled independently. Browsing or
        // choosing a label must not reuse the source's items or shared row.
        for tab_slot in 1..4 {
            let row = data.create_shop_tab(0, tab_slot, 1).unwrap();
            assert_eq!(row, tab_slot + 1);
            assert_eq!(data.ref_count(row), 1);
            assert_eq!(data.get_or_load_tab(row).unwrap().items, vec![0; 48]);
            assert_eq!(data.sell_stb.data[row][0], row.to_string());
            assert_eq!(data.sell_stb.data[row][1], "Weapons");
            assert_eq!(data.sell_stb.data[row][2], "LSEL1");
            assert_eq!(data.shop_tab_label(row), "Weapon");
            data.place_shop_item(0, tab_slot, Some(47), 801379).unwrap();
        }
        assert_eq!(&data.sell_stb.data[..2], original_rows.as_slice());
        assert_eq!(data.npcs[1].shop_tab_rows, [1, 0, 0, 0]);
        assert_eq!(data.ref_count(1), 2);
        data.save().unwrap();

        data.sell_stb = STB::from_path(&stb_dir.join("LIST_SELL.STB")).unwrap();
        data.shop_tabs.clear();
        let npcs = STB::from_path(&stb_dir.join("LIST_NPC.STB")).unwrap();
        assert_eq!(npcs.data[1], original_npcs[1]);
        for tab_slot in 1..4 {
            let row = tab_slot + 1;
            assert_eq!(npcs.data[0][22 + tab_slot], row.to_string());
            assert_eq!(data.sell_stb.data[row][2], "LSEL1");
            let items = &data.get_or_load_tab(row).unwrap().items;
            assert!(items[..47].iter().all(|item| *item == 0));
            assert_eq!(items[47], 801379);
        }
    }

    #[test]
    fn invalid_tab_creation_does_not_overwrite_or_append_shops() {
        let mut data = shared_shop();
        assert!(data.create_shop_tab(0, 0, 1).is_err()); // occupied
        assert!(data.create_shop_tab(2, 1, 1).is_err()); // missing NPC
        assert!(data.create_shop_tab(0, 4, 1).is_err()); // fifth tab
        assert!(data.create_shop_tab(0, 1, 0).is_err()); // reserved row
        assert!(data.create_shop_tab(0, 1, 2).is_err()); // missing label
        data.sell_stb.data[1][2].clear();
        assert!(data.create_shop_tab(0, 1, 1).is_err()); // missing in-game label
        assert_eq!(data.sell_stb.data.len(), 2);
        assert_eq!(data.npcs[0].shop_tab_rows, [1, 0, 0, 0]);
        assert!(!data.any_npc_dirty);
        assert!(data.shop_tabs.is_empty());
    }

    #[test]
    fn chosen_slot_survives_save_without_changing_other_slots_or_shared_npc() {
        let temp = tempfile::tempdir().unwrap();
        let mut data = shared_shop();
        data.root = temp.path().to_path_buf();
        let stb_dir = data.root.join("3DDATA/STB");
        fs::create_dir_all(&stb_dir).unwrap();
        data.npc_stb
            .write_to_path(&stb_dir.join("LIST_NPC.STB"))
            .unwrap();
        data.sell_stb
            .write_to_path(&stb_dir.join("LIST_SELL.STB"))
            .unwrap();
        let original = data.get_or_load_tab(1).unwrap().items.clone();

        // Choose the very last slot despite earlier holes, then replace an
        // occupied slot. Neither operation may shift neighbours or compact gaps.
        let back = encode_item_no(ItemCategory::Back, 1001);
        let weapon = encode_item_no(ItemCategory::Weapon, 1379);
        assert_eq!(data.place_shop_item(0, 0, Some(47), back).unwrap(), 47);
        assert_eq!(data.place_shop_item(0, 0, Some(0), weapon).unwrap(), 0);
        let copied_row = data.npcs[0].shop_tab_rows[0] as usize;
        assert_ne!(copied_row, 1);
        assert_eq!(data.npcs[1].shop_tab_rows[0], 1);
        assert_eq!(data.sell_stb.data.len(), 3); // only one copy
        assert_eq!(data.get_or_load_tab(1).unwrap().items, original);

        data.save().unwrap();
        let sell = STB::from_path(&stb_dir.join("LIST_SELL.STB")).unwrap();
        let npcs = STB::from_path(&stb_dir.join("LIST_NPC.STB")).unwrap();
        assert_eq!(npcs.data[0][22], copied_row.to_string());
        assert_eq!(npcs.data[1][22], "1");
        for (slot, old) in original.iter().enumerate() {
            let expected = match slot {
                0 => 801379,
                47 => 601001,
                _ => *old,
            };
            assert_eq!(sell.data[copied_row][3 + slot], expected.to_string());
            assert_eq!(sell.data[1][3 + slot], old.to_string());
        }
    }

    #[test]
    fn automatic_destination_still_uses_first_empty_slot() {
        let mut data = shared_shop();
        assert_eq!(data.place_shop_item(0, 0, None, 8003).unwrap(), 1);
        let row = data.npcs[0].shop_tab_rows[0] as usize;
        assert_eq!(
            &data.get_or_load_tab(row).unwrap().items[..4],
            &[8001, 8003, 8002, 0]
        );
    }

    #[test]
    fn full_shop_can_replace_but_failed_add_does_not_copy_shared_tab() {
        let mut data = shared_shop();
        for cell in &mut data.sell_stb.data[1][3..] {
            *cell = "8001".to_string();
        }
        assert!(data.place_shop_item(0, 0, None, 8003).is_err());
        assert!(data.place_shop_item(0, 0, Some(48), 8003).is_err());
        assert!(data.place_shop_item(0, 4, Some(0), 8003).is_err());
        assert_eq!(data.sell_stb.data.len(), 2);
        assert_eq!(data.npcs[0].shop_tab_rows[0], 1);
        assert!(!data.any_npc_dirty);
        assert!(!data.get_or_load_tab(1).unwrap().dirty);
        assert_eq!(data.place_shop_item(0, 0, Some(47), 8003).unwrap(), 47);
    }
}
