use std::path::PathBuf;

use egui::{Color32, RichText, ScrollArea, Vec2};

use crate::data::{
    decode_item_no, encode_item_no, DataSet, ItemCategory, Npc, STORE_MAX_ITEM_NO,
};
use crate::icons::IconStore;

pub struct ShopEditorApp {
    data: Option<DataSet>,
    icons: IconStore,
    root: Option<PathBuf>,

    // UI state
    npc_search: String,
    item_search: String,
    selected_npc: Option<usize>,
    selected_tab: usize, // 0..=3
    selected_slot: Option<usize>, // None = first available slot
    new_tab_label_row: Option<usize>,
    item_filter_category: Option<ItemCategory>,
    status: String,
    load_error: Option<String>,
    icon_warning: Option<String>,
    /// Live text for the internal-description field. Keyed by (npc, tab slot)
    /// rather than by LIST_SELL row so the first keystroke's copy-on-write
    /// doesn't reseed the box out from under the cursor.
    description_edit: Option<DescriptionEdit>,
}

struct DescriptionEdit {
    npc_idx: usize,
    tab_slot: usize,
    text: String,
}

impl ShopEditorApp {
    pub fn new(_cc: &eframe::CreationContext<'_>, root: Option<PathBuf>) -> Self {
        let mut app = Self {
            data: None,
            icons: IconStore::empty(std::path::Path::new(".")),
            root: None,
            npc_search: String::new(),
            item_search: String::new(),
            selected_npc: None,
            selected_tab: 0,
            selected_slot: None,
            new_tab_label_row: None,
            item_filter_category: None,
            status: String::new(),
            load_error: None,
            icon_warning: None,
            description_edit: None,
        };
        if let Some(r) = root {
            app.load_root(r);
        }
        app
    }

    fn load_root(&mut self, root: PathBuf) {
        self.root = Some(root.clone());
        self.selected_slot = None;
        self.new_tab_label_row = None;
        self.icon_warning = None;
        self.description_edit = None;
        match DataSet::load(&root) {
            Ok(ds) => {
                self.data = Some(ds);
                self.icons = IconStore::load(&root).unwrap_or_else(|e| {
                    log::warn!("icon load failed: {}", e);
                    self.icon_warning = Some(format!("Icons unavailable: {:#}", e));
                    IconStore::empty(&root)
                });
                self.status = format!("Loaded {}", root.display());
                self.load_error = None;
            }
            Err(e) => {
                self.load_error = Some(format!("Failed to load: {}", e));
                self.data = None;
            }
        }
    }
}

impl eframe::App for ShopEditorApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        top_bar(self, ctx);

        if self.data.is_none() {
            egui::CentralPanel::default().show(ctx, |ui| {
                ui.vertical_centered(|ui| {
                    ui.add_space(60.0);
                    ui.heading("ROSE NPC Shop Editor");
                    ui.add_space(20.0);
                    if let Some(err) = &self.load_error {
                        ui.colored_label(Color32::LIGHT_RED, err);
                        ui.add_space(10.0);
                    }
                    if ui.button("Pick extracted VFS folder…").clicked() {
                        if let Some(p) = rfd::FileDialog::new()
                            .set_title("Select extracted VFS root")
                            .pick_folder()
                        {
                            self.load_root(p);
                        }
                    }
                });
            });
            return;
        }

        egui::SidePanel::left("sidebar")
            .resizable(true)
            .default_width(260.0)
            .show(ctx, |ui| sidebar_ui(self, ui));

        egui::SidePanel::right("item_browser")
            .resizable(true)
            .default_width(340.0)
            .show(ctx, |ui| item_browser_ui(self, ctx, ui));

        egui::CentralPanel::default().show(ctx, |ui| center_ui(self, ctx, ui));
    }
}

fn top_bar(app: &mut ShopEditorApp, ctx: &egui::Context) {
    egui::TopBottomPanel::top("top").show(ctx, |ui| {
        ui.horizontal(|ui| {
            ui.heading("ROSE NPC Shop Editor");
            ui.separator();
            if let Some(r) = &app.root {
                ui.label(
                    RichText::new(format!("Root: {}", r.display()))
                        .color(Color32::LIGHT_BLUE),
                );
            }
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                let save_enabled = app.data.is_some();
                if ui
                    .add_enabled(save_enabled, egui::Button::new("Save"))
                    .clicked()
                {
                    if let Some(data) = app.data.as_mut() {
                        match data.save() {
                            Ok(()) => app.status = "Saved.".to_string(),
                            Err(e) => app.status = format!("Save failed: {}", e),
                        }
                    }
                }
                if !app.status.is_empty() {
                    ui.label(RichText::new(&app.status).color(Color32::LIGHT_GREEN));
                }
            });
        });
        if let Some(warning) = &app.icon_warning {
            ui.colored_label(Color32::DARK_RED, warning);
        }
    });
}

fn sidebar_ui(app: &mut ShopEditorApp, ui: &mut egui::Ui) {
    let data = app.data.as_ref().unwrap();
    ui.label(RichText::new("Shopkeepers").strong());
    ui.text_edit_singleline(&mut app.npc_search);
    ui.separator();

    let filter = app.npc_search.to_lowercase();

    // id -> index lookup so zone entries (which store NPC ids) can select.
    let id_to_idx: std::collections::HashMap<i32, usize> = data
        .npcs
        .iter()
        .enumerate()
        .filter(|(_, n)| n.has_shop())
        .map(|(i, n)| (n.id, i))
        .collect();
    let mut shopkeeper_ids: Vec<i32> = id_to_idx.keys().copied().collect();
    shopkeeper_ids.sort_unstable();

    let mut click: Option<usize> = None;

    ScrollArea::vertical()
        .auto_shrink([false, false])
        .show(ui, |ui| {
            egui::CollapsingHeader::new("All shopkeepers")
                .default_open(true)
                .show(ui, |ui| {
                    for (idx, npc) in data.npcs.iter().enumerate() {
                        if !npc.has_shop() {
                            continue;
                        }
                        if !filter.is_empty()
                            && !npc.name.to_lowercase().contains(&filter)
                            && !npc.id.to_string().contains(&filter)
                        {
                            continue;
                        }
                        let selected = app.selected_npc == Some(idx);
                        let label = format!("[{}] {}", npc.id, npc.name);
                        if ui.selectable_label(selected, label).clicked() {
                            click = Some(idx);
                        }
                    }
                });

            ui.add_space(4.0);

            egui::CollapsingHeader::new("Zones")
                .default_open(false)
                .show(ui, |ui| {
                    let grouped =
                        crate::zones::group_npcs_by_zone(&data.zones, &shopkeeper_ids);
                    for zone in &data.zones {
                        let Some(ids) = grouped.get(&Some(zone.id)) else {
                            continue;
                        };
                        let header =
                            format!("{} ({})", zone.name, ids.len());
                        egui::CollapsingHeader::new(header)
                            .id_source(("zone", zone.id))
                            .show(ui, |ui| {
                                for id in ids {
                                    let Some(&idx) = id_to_idx.get(id) else {
                                        continue;
                                    };
                                    let npc = &data.npcs[idx];
                                    if !filter.is_empty()
                                        && !npc.name.to_lowercase().contains(&filter)
                                        && !npc.id.to_string().contains(&filter)
                                    {
                                        continue;
                                    }
                                    let selected = app.selected_npc == Some(idx);
                                    let label = format!("[{}] {}", npc.id, npc.name);
                                    if ui.selectable_label(selected, label).clicked() {
                                        click = Some(idx);
                                    }
                                }
                            });
                    }
                    if let Some(leftover) = grouped.get(&None) {
                        egui::CollapsingHeader::new(format!(
                            "(Unzoned) ({})",
                            leftover.len()
                        ))
                        .id_source("zone_none")
                        .show(ui, |ui| {
                            for id in leftover {
                                let Some(&idx) = id_to_idx.get(id) else {
                                    continue;
                                };
                                let npc = &data.npcs[idx];
                                if !filter.is_empty()
                                    && !npc.name.to_lowercase().contains(&filter)
                                    && !npc.id.to_string().contains(&filter)
                                {
                                    continue;
                                }
                                let selected = app.selected_npc == Some(idx);
                                let label = format!("[{}] {}", npc.id, npc.name);
                                if ui.selectable_label(selected, label).clicked() {
                                    click = Some(idx);
                                }
                            }
                        });
                    }
                });
        });

    if let Some(idx) = click {
        app.selected_npc = Some(idx);
        let npc = &app.data.as_ref().unwrap().npcs[idx];
        app.selected_tab = first_valid_tab(npc);
        app.selected_slot = None;
        app.new_tab_label_row = None;
        app.description_edit = None;
    }
}

fn first_valid_tab(npc: &Npc) -> usize {
    npc.shop_tab_rows
        .iter()
        .position(|r| *r > 0)
        .unwrap_or(0)
}

fn center_ui(app: &mut ShopEditorApp, ctx: &egui::Context, ui: &mut egui::Ui) {
    let Some(npc_idx) = app.selected_npc else {
        ui.vertical_centered(|ui| {
            ui.add_space(80.0);
            ui.label("Select an NPC from the left to edit their shop.");
        });
        return;
    };
    let data = app.data.as_ref().unwrap();
    let npc = data.npcs[npc_idx].clone();
    ui.horizontal(|ui| {
        ui.heading(format!("[{}] {}", npc.id, npc.name));
    });
    ui.separator();

    // Tab strip
    ui.horizontal(|ui| {
        for (i, row) in npc.shop_tab_rows.iter().enumerate() {
            let enabled = *row > 0;
            let label = if enabled {
                app.data.as_ref().unwrap().shop_tab_label(*row as usize)
            } else {
                format!("Tab {} (empty)", i + 1)
            };
            let selected = app.selected_tab == i;
            let resp = ui.selectable_label(selected, label);
            if resp.clicked() {
                app.selected_tab = i;
                app.selected_slot = None;
                app.new_tab_label_row = None;
                app.description_edit = None;
            }
        }
    });
    ui.separator();

    // Current tab details
    let current_row = npc.shop_tab_rows[app.selected_tab];
    if current_row <= 0 {
        empty_tab_ui(app, npc_idx, ui);
        return;
    }
    let current_row_usize = current_row as usize;
    let ref_count = app.data.as_ref().unwrap().ref_count(current_row_usize);

    ui.horizontal(|ui| {
        ui.label(format!("LIST_SELL row: {}", current_row_usize));
        ui.separator();
        if ref_count > 1 {
            ui.colored_label(
                Color32::YELLOW,
                format!(
                    "⚠ Shared with {} other NPC(s) — first edit will copy this tab.",
                    ref_count - 1
                ),
            );
        } else {
            ui.colored_label(Color32::LIGHT_GREEN, "Exclusive to this NPC");
        }
    });

    if app.selected_tab == SPECIAL_TAB_SLOT {
        ui.colored_label(Color32::YELLOW, SPECIAL_TAB_WARNING);
    }

    // Keep the internal description separate from the translated game label.
    {
        let label = app.data.as_ref().unwrap().shop_tab_label(current_row_usize);
        ui.label(format!("Tab name: {}", label));
    }
    if !app.data.as_ref().unwrap().has_ingame_label(current_row_usize) {
        missing_label_ui(app, npc_idx, ui);
    }
    description_ui(app, npc_idx, current_row_usize, ui);
    ui.separator();

    ui.label(RichText::new("Click a slot number to choose where to add an item.").weak());

    // Items table
    let remove_at: Option<usize>;
    {
        let data = app.data.as_ref().unwrap();
        let tab = data.shop_tabs.get(&current_row_usize);
        let items: Vec<(usize, i32)> = tab
            .map(|t| {
                t.items
                    .iter()
                    .enumerate()
                    .map(|(i, v)| (i, *v))
                    .collect()
            })
            .unwrap_or_default();

        let mut remove: Option<usize> = None;
        ScrollArea::vertical()
            .id_source("shop_items")
            .auto_shrink([false, false])
            .show(ui, |ui| {
                egui::Grid::new("items_grid")
                    .num_columns(5)
                    .striped(true)
                    .spacing([8.0, 4.0])
                    .show(ui, |ui| {
                        ui.label(RichText::new("Slot").strong());
                        ui.label(RichText::new("Icon").strong());
                        ui.label(RichText::new("Item").strong());
                        ui.label(RichText::new("Category").strong());
                        ui.label("");
                        ui.end_row();

                        for (slot, full) in &items {
                            if ui
                                .selectable_label(
                                    app.selected_slot == Some(*slot),
                                    format!("{}", slot + 1),
                                )
                                .on_hover_text(
                                    "Use this slot for the next item from the Item Browser",
                                )
                                .clicked()
                            {
                                app.selected_slot = Some(*slot);
                            }
                            if *full == 0 {
                                ui.label("—");
                                ui.label(RichText::new("(empty)").weak());
                                ui.label("");
                                ui.label("");
                                ui.end_row();
                                continue;
                            }
                            if let Some((cat, id)) = decode_item_no(*full) {
                                let item = data.item_db.lookup(cat, id);
                                let icon_no =
                                    item.map(|i| i.icon_no).unwrap_or(0);
                                draw_icon(ctx, &mut app.icons, ui, icon_no);
                                ui.label(
                                    item.map(|i| i.name.clone())
                                        .unwrap_or_else(|| format!("#{}", id)),
                                );
                                ui.label(cat.display());
                                if ui.small_button("Remove").clicked() {
                                    remove = Some(*slot);
                                }
                                ui.end_row();
                            } else {
                                ui.label("—");
                                ui.label(format!("raw {}", full));
                                ui.label("?");
                                if ui.small_button("Remove").clicked() {
                                    remove = Some(*slot);
                                }
                                ui.end_row();
                            }
                        }
                    });
            });
        remove_at = remove;
    }

    if let Some(slot) = remove_at {
        apply_tab_mutation(app, npc_idx, app.selected_tab, |items| {
            if slot < items.len() {
                items[slot] = 0;
            }
        });
    }
}

/// Every LIST_SELL row usable as a label source: it needs both a description
/// and an STL key, because the client draws the caption from the key alone.
fn label_choices(data: &DataSet) -> Vec<(usize, String)> {
    data.sell_stb
        .data
        .iter()
        .enumerate()
        .skip(1)
        .filter_map(|(row, cells)| {
            cells.get(1).filter(|s| !s.trim().is_empty())?;
            cells.get(2).filter(|s| !s.trim().is_empty())?;
            Some((row, data.shop_tab_label(row)))
        })
        .collect()
}

fn label_picker(
    app: &mut ShopEditorApp,
    npc_idx: usize,
    labels: &[(usize, String)],
    id: &str,
    ui: &mut egui::Ui,
) {
    if app.new_tab_label_row.is_none() {
        app.new_tab_label_row = app.data.as_ref().unwrap().npcs[npc_idx]
            .shop_tab_rows
            .iter()
            .find_map(|row| labels.iter().find(|(r, _)| *r as i32 == *row))
            .map(|(row, _)| *row)
            .or_else(|| labels.first().map(|(row, _)| *row));
    }
    ui.horizontal(|ui| {
        ui.label("Tab label:");
        egui::ComboBox::from_id_source(id)
            .selected_text(
                labels
                    .iter()
                    .find(|(row, _)| Some(*row) == app.new_tab_label_row)
                    .map(|(_, name)| name.as_str())
                    .unwrap_or("Select label"),
            )
            .show_ui(ui, |ui| {
                for (row, name) in labels {
                    ui.selectable_value(&mut app.new_tab_label_row, Some(*row), name);
                }
            });
    });
}

/// A shop whose LIST_SELL row has no usable STL key opens with a blank caption
/// in game -- nine of ours do. Nothing else in the editor can repair that,
/// because a label can otherwise only be chosen when a tab is created.
fn missing_label_ui(app: &mut ShopEditorApp, npc_idx: usize, ui: &mut egui::Ui) {
    ui.colored_label(
        Color32::YELLOW,
        "This tab has no in-game name: its LIST_SELL row has no STL key, so the \
         client draws a blank caption. Adopt another shop's label to fix it.",
    );
    let labels = label_choices(app.data.as_ref().unwrap());
    if labels.is_empty() {
        ui.label("No existing shop labels are available in this data.");
        return;
    }
    label_picker(app, npc_idx, &labels, "assign_tab_label", ui);
    if ui.button("Give this tab that name").clicked() {
        if let Some(label_row) = app.new_tab_label_row {
            match app
                .data
                .as_mut()
                .unwrap()
                .set_tab_label(npc_idx, app.selected_tab, label_row)
            {
                Ok(_) => app.status = "Named the tab. Save to keep changes.".to_string(),
                Err(e) => app.status = format!("Naming failed: {}", e),
            }
        }
    }
}

/// Tab 4. `CStore::ChangeStore` only reads `NPC_SELL_TAB3` when its `bSpecialTab`
/// argument is set, and that comes from the NPC's own .CON calling
/// `openStore(npc, 1)`. The server has no such gate, so a shop parked here is
/// buyable but may never be drawn.
const SPECIAL_TAB_SLOT: usize = 3;
const SPECIAL_TAB_WARNING: &str = concat!(
    "WARNING: tab 4 is the special tab. The client only draws it when this NPC's ",
    ".CON calls openStore(npc, 1); the server sells from it either way."
);

/// The internal description is roselib column 1 (game column 0). Nothing in the
/// game reads it -- the client resolves the displayed name through the STL key
/// in the next column -- but it is still shared data, so it goes through the
/// same copy-on-write path as an item edit.
fn description_ui(
    app: &mut ShopEditorApp,
    npc_idx: usize,
    current_row: usize,
    ui: &mut egui::Ui,
) {
    let tab_slot = app.selected_tab;
    let stale = !app
        .description_edit
        .as_ref()
        .is_some_and(|e| e.npc_idx == npc_idx && e.tab_slot == tab_slot);
    if stale {
        let text = app
            .data
            .as_mut()
            .unwrap()
            .get_or_load_tab(current_row)
            .map(|tab| tab.name.clone())
            .unwrap_or_default();
        app.description_edit = Some(DescriptionEdit {
            npc_idx,
            tab_slot,
            text,
        });
    }

    let mut edited = None;
    ui.collapsing("Internal description", |ui| {
        ui.label("Used by data tools; this does not change the in-game tab name.");
        if let Some(edit) = app.description_edit.as_mut() {
            if ui.text_edit_singleline(&mut edit.text).changed() {
                edited = Some(edit.text.clone());
            }
        }
    });
    if let Some(text) = edited {
        match app
            .data
            .as_mut()
            .unwrap()
            .set_tab_description(npc_idx, tab_slot, text)
        {
            Ok(_) => app.status = "Modified. Save to keep changes.".to_string(),
            Err(e) => app.status = format!("Rename failed: {}", e),
        }
    }
}

fn empty_tab_ui(app: &mut ShopEditorApp, npc_idx: usize, ui: &mut egui::Ui) {
    ui.heading(format!("Create tab {}", app.selected_tab + 1));
    ui.label("Choose a shop label. The new tab will have 48 empty item slots.");
    if app.selected_tab == SPECIAL_TAB_SLOT {
        ui.colored_label(Color32::YELLOW, SPECIAL_TAB_WARNING);
    }
    let labels = label_choices(app.data.as_ref().unwrap());
    if labels.is_empty() {
        ui.label("No existing shop labels are available in this data.");
        return;
    }
    label_picker(app, npc_idx, &labels, "new_tab_label", ui);
    if ui.button("Create empty tab").clicked() {
        if let Some(label_row) = app.new_tab_label_row {
            match app
                .data
                .as_mut()
                .unwrap()
                .create_shop_tab(npc_idx, app.selected_tab, label_row)
            {
                Ok(_) => {
                    app.selected_slot = None;
                    app.status = format!(
                        "Created tab {}. Save to keep changes.",
                        app.selected_tab + 1
                    );
                }
                Err(e) => app.status = format!("Create tab failed: {}", e),
            }
        }
    }
}

fn item_browser_ui(app: &mut ShopEditorApp, ctx: &egui::Context, ui: &mut egui::Ui) {
    ui.label(RichText::new("Item Browser").strong());
    ui.horizontal(|ui| {
        egui::ComboBox::from_id_source("cat_filter")
            .selected_text(
                app.item_filter_category
                    .map(|c| c.display())
                    .unwrap_or("All Types"),
            )
            .show_ui(ui, |ui| {
                ui.selectable_value(&mut app.item_filter_category, None, "All Types");
                for cat in ItemCategory::ALL {
                    ui.selectable_value(
                        &mut app.item_filter_category,
                        Some(*cat),
                        cat.display(),
                    );
                }
            });
    });
    ui.text_edit_singleline(&mut app.item_search);
    ui.separator();

    let Some(npc_idx) = app.selected_npc else {
        ui.label("Select an NPC first.");
        return;
    };
    let selected_tab = app.selected_tab;
    let npc_has_tab = app
        .data
        .as_ref()
        .map(|d| d.npcs[npc_idx].shop_tab_rows[selected_tab] > 0)
        .unwrap_or(false);
    if !npc_has_tab {
        ui.label("Create this empty tab in the center panel to start adding items.");
        return;
    }

    let items = {
        let data = app.data.as_mut().unwrap();
        let row = data.npcs[npc_idx].shop_tab_rows[selected_tab] as usize;
        match data.get_or_load_tab(row) {
            Some(tab) => tab.items.clone(),
            None => {
                ui.label("Selected shop tab could not be loaded.");
                return;
            }
        }
    };
    ui.label("Destination slot:");
    egui::ComboBox::from_id_source("destination_slot")
        .selected_text(
            app.selected_slot
                .map(|slot| format!("Slot {}", slot + 1))
                .unwrap_or_else(|| "First available".to_string()),
        )
        .show_ui(ui, |ui| {
            ui.selectable_value(&mut app.selected_slot, None, "First available");
            let data = app.data.as_ref().unwrap();
            for (slot, full) in items.iter().enumerate() {
                let label = format!("Slot {} — {}", slot + 1, shop_item_name(data, *full));
                ui.selectable_value(&mut app.selected_slot, Some(slot), label);
            }
        });
    let destination = app
        .selected_slot
        .or_else(|| items.iter().position(|value| *value == 0));
    let existing = destination.and_then(|slot| items.get(slot)).copied();
    let replacing = existing.map(|value| value != 0).unwrap_or(false);
    if replacing {
        ui.label(format!(
            "Replaces: {}",
            shop_item_name(app.data.as_ref().unwrap(), existing.unwrap())
        ));
    } else if let Some(slot) = destination {
        ui.label(format!("Adds to slot {}", slot + 1));
    } else {
        ui.label("Shop is full. Choose a slot to replace an item.");
    }
    ui.separator();

    let filter = app.item_search.to_lowercase();
    let cat_filter = app.item_filter_category;

    // Collect matches into a buffer so we don't borrow `data` across the add action.
    let (matches, unsellable) = {
        let data = app.data.as_ref().unwrap();
        let hits = data
            .item_db
            .all()
            .filter(|it| cat_filter.map(|c| c == it.category).unwrap_or(true))
            .filter(|it| {
                filter.is_empty()
                    || it.name.to_lowercase().contains(&filter)
                    || it.id.to_string().contains(&filter)
            });
        // An item table may grow past the 11-bit item number a shop slot can
        // address. Such a row is not a shop item at any encoding, so drop it
        // here rather than let the browser offer a code the game refuses.
        let mut v: Vec<(ItemCategory, i32, String, i32)> = Vec::new();
        let mut skipped = 0usize;
        for it in hits {
            if it.id > STORE_MAX_ITEM_NO {
                skipped += 1;
                continue;
            }
            v.push((it.category, it.id, it.name.clone(), it.icon_no));
        }
        // HashMap iteration is unordered; sort by (category, id) so the list
        // is stable across runs and easy to scan.
        v.sort_by_key(|it| (it.0 as i32, it.1));
        (v, skipped)
    };

    ui.label(
        RichText::new(format!("{} match(es)", matches.len()))
            .weak()
            .small(),
    );
    if unsellable > 0 {
        ui.colored_label(
            Color32::YELLOW,
            format!(
                "{} hidden: item id above {}, which no shop slot can address.",
                unsellable, STORE_MAX_ITEM_NO
            ),
        );
    }

    let mut add_target: Option<(ItemCategory, i32)> = None;
    ScrollArea::vertical()
        .id_source("item_browser")
        .auto_shrink([false, false])
        .show(ui, |ui| {
            for (cat, id, name, icon_no) in &matches {
                ui.horizontal(|ui| {
                    draw_icon(ctx, &mut app.icons, ui, *icon_no);
                    ui.vertical(|ui| {
                        ui.label(name);
                        ui.label(
                            RichText::new(format!("{} #{}", cat.display(), id))
                                .weak()
                                .small(),
                        );
                    });
                    if ui
                        .add_enabled(
                            existing.is_some(),
                            egui::Button::new(if replacing { "Replace" } else { "Add" }).small(),
                        )
                        .clicked()
                    {
                        add_target = Some((*cat, *id));
                    }
                });
                ui.separator();
            }
        });

    if let Some((cat, id)) = add_target {
        let full = encode_item_no(cat, id);
        match app.data.as_mut().unwrap().place_shop_item(
            npc_idx,
            selected_tab,
            app.selected_slot,
            full,
        ) {
            Ok(slot) => {
                app.status = format!(
                    "{} item in slot {}. Save to keep changes.",
                    if replacing { "Replaced" } else { "Added" },
                    slot + 1
                );
            }
            Err(e) => app.status = format!("Edit failed: {}", e),
        }
    }
}

fn shop_item_name(data: &DataSet, full: i32) -> String {
    if full == 0 {
        return "(empty)".to_string();
    }
    decode_item_no(full)
        .and_then(|(cat, id)| data.item_db.lookup(cat, id))
        .map(|item| item.name.clone())
        .unwrap_or_else(|| format!("Item #{}", full))
}

fn apply_tab_mutation(
    app: &mut ShopEditorApp,
    npc_idx: usize,
    tab_slot: usize,
    mutate: impl FnOnce(&mut Vec<i32>),
) {
    let data = app.data.as_mut().unwrap();
    let new_row = match data.begin_tab_edit(npc_idx, tab_slot) {
        Ok(r) => r,
        Err(e) => {
            app.status = format!("edit failed: {}", e);
            return;
        }
    };
    if let Some(tab) = data.get_or_load_tab(new_row) {
        mutate(&mut tab.items);
        tab.dirty = true;
    }
    app.status = "Modified.".to_string();
}

fn draw_icon(
    ctx: &egui::Context,
    icons: &mut IconStore,
    ui: &mut egui::Ui,
    icon_no: i32,
) {
    let size = Vec2::splat(32.0);
    if let Some(tex) = icons.icon_texture(ctx, icon_no) {
        ui.add(egui::Image::new(&tex).fit_to_exact_size(size));
    } else {
        let (rect, _) = ui.allocate_exact_size(size, egui::Sense::hover());
        ui.painter()
            .rect_filled(rect, 2.0, Color32::from_gray(40));
    }
}
