#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::sync::{mpsc, Arc};

use egui::{Color32, RichText};
use egui_extras::{Column, TableBuilder};
use npc_shop_editor::assets::Assets;
use npc_shop_editor::catalog::{Catalog, CatalogItem, Filter, RangeFilter};
use npc_shop_editor::data::ItemCategory;
use npc_shop_editor::icons::IconStore;

fn main() -> eframe::Result<()> {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("warn")).init();
    let root = std::env::args_os().nth(1).map(PathBuf::from).or_else(|| {
        let beside_exe = std::env::current_exe().ok()?.parent()?.to_path_buf();
        [Some(beside_exe), std::env::current_dir().ok()]
            .into_iter()
            .flatten()
            .flat_map(|root| [root.join("data"), root])
            .find(|path| {
                path.join("data.idx").is_file() || path.join("3DDATA/STB/LIST_WEAPON.STB").is_file()
            })
    });
    eframe::run_native(
        "ROSE GM Item Browser",
        eframe::NativeOptions {
            viewport: egui::ViewportBuilder::default()
                .with_inner_size([1320.0, 820.0])
                .with_min_inner_size([1100.0, 650.0]),
            ..Default::default()
        },
        Box::new(move |cc| Box::new(Browser::new(cc, root))),
    )
}

type Loaded = Result<(Catalog, Arc<Assets>), String>;

#[derive(Clone, Copy, PartialEq)]
enum Sort {
    Type,
    Id,
    Name,
    Level,
    Attack,
    Defense,
    Resistance,
    Quality,
}

impl Sort {
    const ALL: [(Self, &'static str); 8] = [
        (Self::Type, "Type"),
        (Self::Id, "ID"),
        (Self::Name, "Name"),
        (Self::Level, "Level"),
        (Self::Attack, "Attack"),
        (Self::Defense, "Defense"),
        (Self::Resistance, "Resistance"),
        (Self::Quality, "Quality"),
    ];
    fn label(self) -> &'static str {
        Self::ALL.iter().find(|(key, _)| *key == self).unwrap().1
    }
}

struct Browser {
    catalog: Option<Catalog>,
    icons: IconStore,
    loading: Option<mpsc::Receiver<Loaded>>,
    root: Option<PathBuf>,
    error: Option<String>,
    filter: Filter,
    sort: Sort,
    descending: bool,
    results: Vec<usize>,
    selected: Option<usize>,
    quantity: i32,
    copied: Option<(String, std::time::Instant)>,
}

impl Browser {
    fn new(cc: &eframe::CreationContext<'_>, root: Option<PathBuf>) -> Self {
        cc.egui_ctx.set_visuals(egui::Visuals::dark());
        let mut app = Self {
            catalog: None,
            icons: IconStore::empty(Path::new(".")),
            loading: None,
            root: None,
            error: None,
            filter: Filter::default(),
            sort: Sort::Type,
            descending: false,
            results: Vec::new(),
            selected: None,
            quantity: 1,
            copied: None,
        };
        if let Some(root) = root {
            app.load(root, &cc.egui_ctx);
        }
        app
    }

    fn load(&mut self, root: PathBuf, ctx: &egui::Context) {
        self.root = Some(root.clone());
        self.catalog = None;
        self.results.clear();
        self.selected = None;
        self.error = None;
        self.icons = IconStore::empty(Path::new("."));
        let (tx, rx) = mpsc::channel();
        let ctx = ctx.clone();
        self.loading = Some(rx);
        std::thread::spawn(move || {
            let result = (|| -> anyhow::Result<_> {
                let assets = Arc::new(Assets::open(&root)?);
                let catalog = Catalog::load(&assets)?;
                Ok((catalog, assets))
            })()
            .map_err(|e| format!("{e:#}"));
            let _ = tx.send(result);
            ctx.request_repaint();
        });
    }

    fn poll_load(&mut self) {
        let Some(receiver) = &self.loading else {
            return;
        };
        let result = match receiver.try_recv() {
            Ok(result) => result,
            Err(mpsc::TryRecvError::Empty) => return,
            Err(mpsc::TryRecvError::Disconnected) => {
                Err("Loading stopped unexpectedly. Please reopen the data folder.".into())
            }
        };
        self.loading = None;
        match result {
            Ok((mut catalog, assets)) => {
                match IconStore::from_assets(assets) {
                    Ok(icons) => self.icons = icons,
                    Err(e) => catalog.warnings.push(format!("Icons unavailable: {e:#}")),
                }
                self.catalog = Some(catalog);
                self.refresh();
            }
            Err(e) => self.error = Some(e),
        }
    }

    fn refresh(&mut self) {
        let Some(catalog) = &self.catalog else {
            return;
        };
        self.results = catalog
            .items
            .iter()
            .enumerate()
            .filter(|(_, item)| self.filter.matches(item))
            .map(|(i, _)| i)
            .collect();
        self.results.sort_by(|&a, &b| {
            let (a, b) = (&catalog.items[a], &catalog.items[b]);
            let cmp = match self.sort {
                Sort::Type => (a.item.category as u8).cmp(&(b.item.category as u8)),
                Sort::Id => a.item.id.cmp(&b.item.id),
                Sort::Name => a.item.name.to_lowercase().cmp(&b.item.name.to_lowercase()),
                Sort::Level => a.level.cmp(&b.level),
                Sort::Attack => a.attack.cmp(&b.attack),
                Sort::Defense => a.defense.cmp(&b.defense),
                Sort::Resistance => a.resistance.cmp(&b.resistance),
                Sort::Quality => a.quality.cmp(&b.quality),
            };
            (if self.descending { cmp.reverse() } else { cmp }).then_with(|| {
                (a.item.category as u8, a.item.id).cmp(&(b.item.category as u8, b.item.id))
            })
        });
        if self
            .selected
            .is_some_and(|selected| !self.results.contains(&selected))
        {
            self.selected = None;
        }
    }

    fn copy(&mut self, command: String, ctx: &egui::Context) {
        ctx.copy_text(command.clone());
        self.copied = Some((command, std::time::Instant::now()));
        ctx.request_repaint_after(std::time::Duration::from_secs(4));
    }

    fn filters(&mut self, ui: &mut egui::Ui) {
        ui.heading("Find an item");
        ui.add_space(8.0);
        ui.add(
            egui::TextEdit::singleline(&mut self.filter.search)
                .hint_text("Name, ID, type:ID...")
                .desired_width(f32::INFINITY),
        );
        ui.add_space(8.0);
        let previous_category = self.filter.category;
        egui::ComboBox::from_label("Item type")
            .width(160.0)
            .selected_text(self.filter.category.map_or("All types".into(), |c| {
                format!("{} - {}", c as u8, c.display())
            }))
            .show_ui(ui, |ui| {
                ui.selectable_value(&mut self.filter.category, None, "All types");
                for &cat in ItemCategory::ALL {
                    ui.selectable_value(
                        &mut self.filter.category,
                        Some(cat),
                        format!("{} - {}", cat as u8, cat.display()),
                    );
                }
            });
        if previous_category != self.filter.category {
            self.filter.class = None;
        }
        let mut classes: Vec<i32> = self
            .catalog
            .iter()
            .flat_map(|c| &c.items)
            .filter(|item| {
                self.filter
                    .category
                    .map_or(true, |cat| cat == item.item.category)
            })
            .map(|item| item.class)
            .filter(|&class| class > 0)
            .collect();
        classes.sort_unstable();
        classes.dedup();
        egui::ComboBox::from_label("Subtype")
            .width(160.0)
            .selected_text(
                self.filter
                    .class
                    .map_or("All subtypes".into(), |c| c.to_string()),
            )
            .show_ui(ui, |ui| {
                ui.selectable_value(&mut self.filter.class, None, "All subtypes");
                for class in classes {
                    ui.selectable_value(&mut self.filter.class, Some(class), class.to_string());
                }
            });
        ui.add_space(12.0);
        ui.label(RichText::new("Stat ranges").strong());
        ui.small("Leave a bound blank for no limit.");
        range_ui(ui, "Required level", &mut self.filter.level);
        range_ui(ui, "Attack power", &mut self.filter.attack);
        range_ui(ui, "Defense", &mut self.filter.defense);
        range_ui(ui, "Resistance", &mut self.filter.resistance);
        range_ui(ui, "Quality", &mut self.filter.quality);
        ui.add_space(8.0);
        ui.checkbox(&mut self.filter.spawnable_only, "Spawnable items only")
            .on_hover_text("Hide rows without an icon or outside the game's item ID range.");
        if ui.button("Clear filters").clicked() {
            self.filter = Filter::default();
        }
        ui.add_space(12.0);
        ui.small(
            "Stats are base item values, before bonuses, gems, refinement or character stats.",
        );
        ui.small("Level 0 = no level requirement. A dash means the stat does not apply.");
        ui.separator();
        ui.label("Select an item to inspect it.");
        ui.label("Copy its command, then paste it into game chat.");
    }

    fn details(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        let Some(item) = self
            .selected
            .and_then(|i| self.catalog.as_ref()?.items.get(i))
        else {
            ui.label("Select an item for details and its GM command.");
            return;
        };
        let mut command_to_copy = None;
        ui.horizontal(|ui| {
            draw_icon(ui, ctx, &mut self.icons, item, 48.0);
            ui.vertical(|ui| {
                ui.strong(&item.item.name);
                ui.label(format!(
                    "Type {} ({})  |  ID {}  |  Subtype {}",
                    item.item.category as u8,
                    item.item.category.display(),
                    item.item.id,
                    item.class
                ));
                ui.label(format!(
                    "Level {}   Attack {}   Defense {}   Resistance {}   Quality {}",
                    stat(item.level),
                    stat(item.attack),
                    stat(item.defense),
                    stat(item.resistance),
                    item.quality
                ));
            });
            ui.separator();
            ui.vertical(|ui| {
                if item.stackable() {
                    ui.horizontal(|ui| {
                        ui.label("Quantity");
                        ui.add(egui::DragValue::new(&mut self.quantity).clamp_range(1..=100));
                    });
                }
                if let Some(command) = item.command(self.quantity) {
                    ui.horizontal(|ui| {
                        ui.monospace(&command);
                        if ui.button("Copy command").clicked() {
                            command_to_copy = Some(command);
                        }
                    });
                } else {
                    ui.colored_label(Color32::LIGHT_RED, "This row cannot be spawned.");
                }
            });
        });
        if !item.description.is_empty() {
            ui.label(&item.description);
        }
        if let Some(command) = command_to_copy {
            self.copy(command, ctx);
        }
    }

    fn table(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        let Some(catalog) = &self.catalog else {
            return;
        };
        ui.horizontal(|ui| {
            ui.strong(format!(
                "{} matching / {} items",
                self.results.len(),
                catalog.items.len()
            ));
            ui.separator();
            egui::ComboBox::from_label("Sort")
                .selected_text(self.sort.label())
                .show_ui(ui, |ui| {
                    for (sort, label) in Sort::ALL {
                        ui.selectable_value(&mut self.sort, sort, label);
                    }
                });
            ui.checkbox(&mut self.descending, "Descending");
        });
        ui.add_space(6.0);
        if self.results.is_empty() {
            ui.label("No matching items. Adjust or clear the filters.");
            return;
        }
        let mut copy = None;
        TableBuilder::new(ui)
            .striped(true)
            .resizable(true)
            .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
            .column(Column::exact(42.0))
            .column(Column::remainder().at_least(150.0))
            .column(Column::initial(115.0))
            .column(Column::initial(50.0))
            .columns(Column::initial(55.0), 4)
            .column(Column::exact(62.0))
            .header(24.0, |mut header| {
                for label in [
                    "Icon", "Name", "Type", "ID", "Level", "Attack", "Defense", "Resist.",
                    "Command",
                ] {
                    header.col(|ui| {
                        ui.strong(label);
                    });
                }
            })
            .body(|body| {
                body.rows(44.0, self.results.len(), |mut row| {
                    let index = self.results[row.index()];
                    let item = &catalog.items[index];
                    row.set_selected(self.selected == Some(index));
                    row.col(|ui| {
                        draw_icon(ui, ctx, &mut self.icons, item, 40.0);
                    });
                    row.col(|ui| {
                        if ui
                            .selectable_label(self.selected == Some(index), &item.item.name)
                            .on_hover_text(&item.description)
                            .clicked()
                        {
                            self.selected = Some(index);
                        }
                    });
                    row.col(|ui| {
                        ui.label(format!(
                            "{} - {}",
                            item.item.category as u8,
                            item.item.category.display()
                        ));
                    });
                    row.col(|ui| {
                        ui.monospace(item.item.id.to_string());
                    });
                    for value in [item.level, item.attack, item.defense, item.resistance] {
                        row.col(|ui| {
                            ui.label(stat(value));
                        });
                    }
                    row.col(|ui| {
                        if ui
                            .add_enabled(item.spawnable(), egui::Button::new("Copy"))
                            .on_hover_text("Copy /item command for one item")
                            .clicked()
                        {
                            copy = item.command(1);
                            self.selected = Some(index);
                        }
                    });
                });
            });
        if let Some(command) = copy {
            self.copy(command, ctx);
        }
    }
}

impl eframe::App for Browser {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_load();
        egui::TopBottomPanel::top("top").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("ROSE GM Item Browser");
                ui.separator();
                if ui
                    .add_enabled(
                        self.loading.is_none(),
                        egui::Button::new("Open data folder..."),
                    )
                    .clicked()
                {
                    if let Some(root) = rfd::FileDialog::new()
                        .set_title("Loose data folder (or game folder containing data.idx)")
                        .pick_folder()
                    {
                        self.load(root, ctx);
                    }
                }
                if ui
                    .add_enabled(self.loading.is_none(), egui::Button::new("Open VFS..."))
                    .clicked()
                {
                    if let Some(index) = rfd::FileDialog::new()
                        .set_title("Open a packed game data index")
                        .add_filter("ROSE VFS index", &["idx"])
                        .pick_file()
                    {
                        self.load(index, ctx);
                    }
                }
                if ui
                    .add_enabled(
                        self.loading.is_none() && self.root.is_some(),
                        egui::Button::new("Reload"),
                    )
                    .clicked()
                {
                    self.load(self.root.clone().unwrap(), ctx);
                }
                if let Some((command, when)) = &self.copied {
                    if when.elapsed().as_secs() < 4 {
                        ui.colored_label(Color32::LIGHT_GREEN, format!("Copied {command}"));
                    }
                }
            });
            if let Some(root) = &self.root {
                ui.small(root.display().to_string());
            }
            if let Some(catalog) = &self.catalog {
                if !catalog.warnings.is_empty() {
                    egui::CollapsingHeader::new(format!(
                        "Data warnings ({})",
                        catalog.warnings.len()
                    ))
                    .show(ui, |ui| {
                        egui::ScrollArea::vertical()
                            .max_height(110.0)
                            .show(ui, |ui| {
                                for warning in &catalog.warnings {
                                    ui.colored_label(Color32::LIGHT_YELLOW, warning);
                                }
                            });
                    });
                }
            }
        });
        if self.catalog.is_none() {
            egui::CentralPanel::default().show(ctx, |ui| {
                ui.add_space(55.0);
                if self.loading.is_some() {
                    ui.spinner();
                    ui.heading("Loading items...");
                } else {
                    ui.heading("Find items. Copy commands. Get testing.");
                    ui.label(
                        "Keep the supplied data folder beside this tool for automatic loading.",
                    );
                    ui.label("You can also open another data folder or a VFS index.");
                    ui.label(
                        "The tool reads game data. GM access is required to use /item in the game.",
                    );
                    if let Some(error) = &self.error {
                        ui.colored_label(Color32::LIGHT_RED, error);
                    }
                }
            });
            return;
        }
        let old_filter = self.filter.clone();
        let old_sort = (self.sort, self.descending);
        egui::SidePanel::left("filters")
            .exact_width(255.0)
            .show(ctx, |ui| {
                egui::ScrollArea::vertical().show(ui, |ui| self.filters(ui));
            });
        if old_filter != self.filter {
            self.refresh();
        }
        egui::TopBottomPanel::bottom("details")
            .min_height(112.0)
            .show(ctx, |ui| {
                egui::ScrollArea::vertical()
                    .max_height(190.0)
                    .show(ui, |ui| self.details(ui, ctx));
            });
        egui::CentralPanel::default().show(ctx, |ui| self.table(ui, ctx));
        if old_sort != (self.sort, self.descending) {
            self.refresh();
            ctx.request_repaint();
        }
    }
}

fn range_ui(ui: &mut egui::Ui, label: &str, range: &mut RangeFilter) {
    ui.label(label);
    ui.horizontal(|ui| {
        ui.add(
            egui::TextEdit::singleline(&mut range.min)
                .hint_text("Min")
                .desired_width(95.0),
        );
        ui.label("to");
        ui.add(
            egui::TextEdit::singleline(&mut range.max)
                .hint_text("Max")
                .desired_width(95.0),
        );
    });
    if let Err(error) = range.bounds() {
        ui.colored_label(Color32::LIGHT_RED, error.to_string());
    }
}

fn stat(value: Option<i32>) -> String {
    value.map_or("-".into(), |v| v.to_string())
}

fn draw_icon(
    ui: &mut egui::Ui,
    ctx: &egui::Context,
    icons: &mut IconStore,
    item: &CatalogItem,
    size: f32,
) {
    if let Some(texture) = icons.icon_texture(ctx, item.item.icon_no) {
        ui.image((texture.id(), egui::vec2(size, size)));
    } else {
        let (rect, response) = ui.allocate_exact_size(egui::vec2(size, size), egui::Sense::hover());
        ui.painter().rect_filled(rect, 4.0, Color32::from_gray(45));
        ui.painter().text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            "?",
            egui::FontId::proportional(18.0),
            Color32::GRAY,
        );
        response.on_hover_text("Icon unavailable");
    }
}
