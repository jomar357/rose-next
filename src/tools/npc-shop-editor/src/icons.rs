use std::collections::HashMap;
use std::fs;
use std::io::{Cursor, Read};
use std::path::{Path, PathBuf};

use anyhow::{anyhow, Context, Result};
use byteorder::{LittleEndian, ReadBytesExt};
use egui::{ColorImage, TextureHandle, TextureOptions};

use crate::data::resolve_icon_dir;
use crate::dds;

/// A sprite rect within a named texture sheet.
#[derive(Debug, Clone)]
struct SpriteRef {
    sheet_idx: usize,
    x: u32,
    y: u32,
    w: u32,
    h: u32,
}

pub struct IconStore {
    atlas: IconAtlas,
    res_dir: PathBuf,
    /// Decoded sheets, keyed by sheet index in the TSI.
    sheets: HashMap<usize, dds::DecodedImage>,
    /// Egui textures keyed by global sprite index.
    textures: HashMap<u64, Option<TextureHandle>>,
}

impl IconStore {
    pub fn load(root: &Path) -> Result<Self> {
        let res_dir = resolve_icon_dir(root)?;
        let tsi_path = find_file_ci(&res_dir, "ITEM1.TSI")
            .context("locating ITEM1.TSI inside 3DDATA/CONTROL/RES/")?;
        let atlas = IconAtlas::read(&fs::read(&tsi_path)?)
            .with_context(|| format!("reading {}", tsi_path.display()))?;
        Ok(Self {
            atlas,
            res_dir,
            sheets: HashMap::new(),
            textures: HashMap::new(),
        })
    }

    /// Used when the icons couldn't be loaded — the editor still works,
    /// just without visible icons.
    pub fn empty(root: &Path) -> Self {
        Self {
            atlas: IconAtlas::default(),
            res_dir: root.to_path_buf(),
            sheets: HashMap::new(),
            textures: HashMap::new(),
        }
    }

    /// Look up a sprite by its linear index (icon_no in the item tables).
    /// Sprite order determines the global index; each sprite independently
    /// names its texture sheet (which can differ from its containing block).
    fn locate(&self, icon_no: u32) -> Option<SpriteRef> {
        self.atlas.sprites.get(icon_no as usize).cloned()
    }

    fn ensure_sheet(&mut self, sheet_idx: usize) -> Result<&dds::DecodedImage> {
        if !self.sheets.contains_key(&sheet_idx) {
            let sheet_name = self
                .atlas
                .sheets
                .get(sheet_idx)
                .ok_or_else(|| anyhow!("sheet index out of range"))?;
            let sheet_path = find_file_ci(&self.res_dir, sheet_name)
                .with_context(|| format!("locating sheet texture {}", sheet_name))?;
            let bytes = fs::read(&sheet_path)
                .with_context(|| format!("reading {}", sheet_path.display()))?;
            let decoded = dds::decode(&bytes)
                .with_context(|| format!("decoding DDS {}", sheet_path.display()))?;
            self.sheets.insert(sheet_idx, decoded);
        }
        Ok(self.sheets.get(&sheet_idx).unwrap())
    }

    /// Get (or create) an egui texture handle for an item's icon.
    pub fn icon_texture(&mut self, ctx: &egui::Context, icon_no: i32) -> Option<TextureHandle> {
        if icon_no <= 0 {
            return None;
        }
        let key = icon_no as u64;
        if let Some(slot) = self.textures.get(&key) {
            return slot.clone();
        }
        let handle = self.try_build_texture(ctx, icon_no as u32);
        self.textures.insert(key, handle.clone());
        handle
    }

    fn try_build_texture(&mut self, ctx: &egui::Context, icon_no: u32) -> Option<TextureHandle> {
        let sprite = self.locate(icon_no)?;
        if sprite.w == 0 || sprite.h == 0 {
            return None;
        }
        let sheet = match self.ensure_sheet(sprite.sheet_idx) {
            Ok(s) => s,
            Err(e) => {
                log::warn!("ensure_sheet({}) failed: {}", sprite.sheet_idx, e);
                return None;
            }
        };
        let cropped = sheet.crop(sprite.x, sprite.y, sprite.w, sprite.h)?;
        let size = [cropped.width as usize, cropped.height as usize];
        let image = ColorImage::from_rgba_unmultiplied(size, &cropped.rgba);
        Some(ctx.load_texture(format!("icon_{}", icon_no), image, TextureOptions::LINEAR))
    }
}

/// The roselib TSI reader discards each sprite's texture ID and assumes it is
/// the containing block's index. Relocated item icons retain their global
/// index but point at another sheet, so retain those IDs in this read-only reader.
#[derive(Default)]
struct IconAtlas {
    sheets: Vec<String>,
    sprites: Vec<SpriteRef>,
}

impl IconAtlas {
    fn read(bytes: &[u8]) -> Result<Self> {
        let mut reader = Cursor::new(bytes);
        let sheet_count = reader.read_u16::<LittleEndian>()? as usize;
        let mut sheets = Vec::with_capacity(sheet_count);
        for _ in 0..sheet_count {
            let len = reader.read_u16::<LittleEndian>()? as usize;
            let mut name = vec![0; len];
            reader.read_exact(&mut name)?;
            let end = name.iter().position(|&b| b == 0).unwrap_or(name.len());
            sheets.push(String::from_utf8_lossy(&name[..end]).into_owned());
            let _color_key = reader.read_u32::<LittleEndian>()?;
        }
        let total = reader.read_u16::<LittleEndian>()? as usize;
        let mut sprites = Vec::with_capacity(total);
        for _ in 0..sheet_count {
            let count = reader.read_u16::<LittleEndian>()?;
            for _ in 0..count {
                let sheet_idx = reader.read_u16::<LittleEndian>()? as usize;
                if sheet_idx >= sheet_count {
                    return Err(anyhow!(
                        "sprite {} references missing sheet {}",
                        sprites.len(),
                        sheet_idx
                    ));
                }
                let x1 = reader.read_u32::<LittleEndian>()?;
                let y1 = reader.read_u32::<LittleEndian>()?;
                let x2 = reader.read_u32::<LittleEndian>()?;
                let y2 = reader.read_u32::<LittleEndian>()?;
                let mut metadata = [0; 36]; // color and 32-byte name
                reader.read_exact(&mut metadata)?;
                sprites.push(SpriteRef {
                    sheet_idx,
                    x: x1.min(x2),
                    y: y1.min(y2),
                    w: x1.abs_diff(x2),
                    h: y1.abs_diff(y2),
                });
            }
        }
        if sprites.len() != total {
            return Err(anyhow!(
                "TSI sprite count mismatch: expected {}, got {}",
                total,
                sprites.len()
            ));
        }
        Ok(Self { sheets, sprites })
    }
}

fn find_file_ci(dir: &Path, name: &str) -> Result<PathBuf> {
    let direct = dir.join(name);
    if direct.exists() {
        return Ok(direct);
    }
    // Normalize: strip any directory component.
    let basename = Path::new(name)
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| name.to_string());
    let direct = dir.join(&basename);
    if direct.exists() {
        return Ok(direct);
    }
    for entry in fs::read_dir(dir).with_context(|| format!("reading {}", dir.display()))? {
        let entry = entry?;
        if entry
            .file_name()
            .to_string_lossy()
            .eq_ignore_ascii_case(&basename)
        {
            return Ok(entry.path());
        }
    }
    Err(anyhow!("file not found: {}/{}", dir.display(), name))
}

#[cfg(test)]
mod tests {
    use super::*;
    use byteorder::WriteBytesExt;

    fn fixture_tsi() -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.write_u16::<LittleEndian>(2).unwrap();
        for name in [b"icon01.dds\0", b"icon02.dds\0"] {
            bytes.write_u16::<LittleEndian>(name.len() as u16).unwrap();
            bytes.extend_from_slice(name);
            bytes.write_u32::<LittleEndian>(0).unwrap();
        }
        bytes.write_u16::<LittleEndian>(3).unwrap();
        // Global icon 1 remains in block 0 but was moved to texture 1.
        for block in [&[0u16, 1][..], &[1u16][..]] {
            bytes.write_u16::<LittleEndian>(block.len() as u16).unwrap();
            for &sheet in block {
                bytes.write_u16::<LittleEndian>(sheet).unwrap();
                for coord in [0, 0, 40, 40] {
                    bytes.write_u32::<LittleEndian>(coord).unwrap();
                }
                bytes.extend_from_slice(&[0; 36]);
            }
        }
        bytes
    }

    fn fixture_dds(bgra: [u8; 4]) -> Vec<u8> {
        let mut bytes = vec![0; 128];
        bytes[..4].copy_from_slice(b"DDS ");
        for (offset, value) in [
            (4, 124u32),
            (8, 0x100f),
            (12, 40),
            (16, 40),
            (20, 160),
            (76, 32),
            (80, 0x41),
            (88, 32),
            (92, 0xff0000),
            (96, 0xff00),
            (100, 0xff),
            (104, 0xff000000),
            (108, 0x1000),
        ] {
            bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
        }
        for _ in 0..40 * 40 {
            bytes.extend_from_slice(&bgra);
        }
        bytes
    }

    #[test]
    fn loads_icons_from_every_supported_root_and_uses_sprite_texture_id() {
        let temp = tempfile::tempdir().unwrap();
        let data = temp.path();
        let stb = data.join("3DDATA/STB");
        let res = data.join("3DDATA/CONTROL/RES");
        fs::create_dir_all(&stb).unwrap();
        fs::create_dir_all(&res).unwrap();
        fs::write(stb.join("LIST_NPC.STB"), []).unwrap();
        fs::write(res.join("ITEM1.TSI"), fixture_tsi()).unwrap();
        fs::write(res.join("icon01.dds"), fixture_dds([0, 0, 255, 255])).unwrap();
        fs::write(res.join("icon02.dds"), fixture_dds([0, 255, 0, 255])).unwrap();

        for root in [data.to_path_buf(), data.join("3DDATA"), stb] {
            let mut store = IconStore::load(&root).unwrap();
            let sprite = store.locate(1).unwrap();
            assert_eq!(sprite.sheet_idx, 1);
            let crop = store
                .ensure_sheet(sprite.sheet_idx)
                .unwrap()
                .crop(sprite.x, sprite.y, sprite.w, sprite.h)
                .unwrap();
            assert_eq!((crop.width, crop.height), (40, 40));
            assert!(crop
                .rgba
                .chunks_exact(4)
                .all(|pixel| pixel == [0, 255, 0, 255]));
            assert_eq!(store.locate(0).unwrap().sheet_idx, 0);
            assert_eq!(store.locate(2).unwrap().sheet_idx, 1);
            assert!(store.locate(3).is_none());
            assert!(store.icon_texture(&egui::Context::default(), 1).is_some());
        }
    }

    #[test]
    fn rejects_truncated_tsi() {
        let bytes = fixture_tsi();
        assert!(IconAtlas::read(&bytes[..bytes.len() - 1]).is_err());
    }

    #[test]
    fn rejects_invalid_texture_reference() {
        let mut bytes = fixture_tsi();
        // Header: 2 sheets, two (length + 11-byte name + color key), total, block count.
        let first_sprite = 2 + 2 * (2 + 11 + 4) + 2 + 2;
        bytes[first_sprite..first_sprite + 2].copy_from_slice(&2u16.to_le_bytes());
        assert!(IconAtlas::read(&bytes).is_err());
    }

    #[test]
    #[ignore = "requires the workspace's extracted data assets"]
    fn workspace_item_icons() {
        use crate::data::{DataSet, ItemCategory};

        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../data");
        let data = DataSet::load(&root).unwrap();
        let mut store = IconStore::load(&root.join("3DDATA/STB")).unwrap();
        let ctx = egui::Context::default();
        // Face #1 (Flu Mask) is visible in the reported screenshot.
        let face = data.item_db.lookup(ItemCategory::Face, 1).unwrap();
        assert!(store.icon_texture(&ctx, face.icon_no).is_some());
        let mut checked = std::collections::HashSet::new();
        let mut failed = Vec::new();
        for item in data.item_db.all().filter(|item| item.icon_no > 0) {
            if checked.insert(item.icon_no) && store.icon_texture(&ctx, item.icon_no).is_none() {
                failed.push(format!("{} (icon {})", item.name, item.icon_no));
            }
        }
        println!(
            "Checked {} distinct item icons across {} sheets",
            checked.len(),
            store.sheets.len()
        );
        assert!(
            failed.is_empty(),
            "Icons that failed to load: {:#?}",
            failed
        );
    }
}
