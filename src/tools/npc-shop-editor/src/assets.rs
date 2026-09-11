//! Read-only access to extracted assets or a shipped data.idx and its archives.
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use roselib::files::IDX;
use roselib::io::RoseFile;

pub struct Assets {
    root: PathBuf,
    packed: Option<HashMap<String, Entry>>,
}

struct Entry {
    archive: PathBuf,
    offset: u64,
    size: i32,
    encoded: bool,
}

impl Assets {
    pub fn open(path: &Path) -> Result<Self> {
        let idx = if path.is_file() {
            Some(path.to_path_buf())
        } else {
            find_ci(path, "data.idx").ok()
        };
        if let Some(idx) = idx {
            let root = idx
                .parent()
                .context("index has no parent directory")?
                .to_path_buf();
            let index =
                IDX::from_path(&idx).map_err(|e| anyhow::anyhow!("{}: {}", idx.display(), e))?;
            let mut entries = HashMap::new();
            for vfs in index.file_systems {
                for file in vfs.files.into_iter().filter(|f| !f.is_deleted) {
                    entries
                        .entry(normalize(&file.filepath.to_string_lossy()))
                        .or_insert(Entry {
                            archive: vfs.filename.clone(),
                            // roselib exposes the old signed field; the game now uses all 32 bits.
                            offset: file.offset as u32 as u64,
                            size: file.size,
                            encoded: file.is_compressed || file.is_encrypted,
                        });
                }
            }
            return Ok(Self {
                root,
                packed: Some(entries),
            });
        }
        for root in [
            Some(path),
            path.parent(),
            path.parent().and_then(Path::parent),
        ]
        .into_iter()
        .flatten()
        {
            if find_ci(root, "3DDATA/STB/LIST_WEAPON.STB").is_ok() {
                return Ok(Self {
                    root: root.to_path_buf(),
                    packed: None,
                });
            }
        }
        bail!("Choose a game folder containing data.idx, or extracted data containing 3DDATA/STB/LIST_WEAPON.STB")
    }

    pub fn read(&self, path: &str) -> Result<Vec<u8>> {
        let Some(entries) = &self.packed else {
            return fs::read(find_ci(&self.root, path)?).with_context(|| format!("reading {path}"));
        };
        let entry = entries
            .get(&normalize(path))
            .with_context(|| format!("{path} is missing from data.idx"))?;
        if entry.encoded || entry.size < 0 {
            bail!("{path}: unsupported compressed/encrypted entry or invalid length");
        }
        let mut file = File::open(find_ci(&self.root, &entry.archive.to_string_lossy())?)?;
        if entry.offset + entry.size as u64 > file.metadata()?.len() {
            bail!("{path}: archive is truncated");
        }
        file.seek(SeekFrom::Start(entry.offset))?;
        let mut bytes = vec![0; entry.size as usize];
        file.read_exact(&mut bytes)
            .with_context(|| format!("reading {path}"))?;
        Ok(bytes)
    }
}

fn normalize(path: &str) -> String {
    path.replace('\\', "/")
        .trim_matches('/')
        .to_ascii_uppercase()
}

fn find_ci(root: &Path, path: &str) -> Result<PathBuf> {
    let mut current = root.to_path_buf();
    for part in path.split(['/', '\\']).filter(|p| !p.is_empty()) {
        if part == "." || part == ".." || part.contains(':') {
            bail!("invalid asset path: {path}");
        }
        let direct = current.join(part);
        current = if direct.exists() {
            direct
        } else {
            fs::read_dir(&current)?
                .filter_map(Result::ok)
                .find(|entry| {
                    entry
                        .file_name()
                        .to_string_lossy()
                        .eq_ignore_ascii_case(part)
                })
                .with_context(|| format!("missing {path}"))?
                .path()
        };
    }
    Ok(current)
}

#[cfg(test)]
mod tests {
    use super::*;
    use roselib::files::idx::{VfsFileMetadata, VfsMetadata};
    use std::io::Write;

    #[test]
    fn reads_split_archives_unsigned_offsets_and_ignores_deleted_entries() {
        let temp = tempfile::tempdir().unwrap();
        fs::write(temp.path().join("rose.vfs"), b"first").unwrap();
        let mut large = File::create(temp.path().join("rose_2.vfs")).unwrap();
        // Sparse fixture exercises the historical signed-2GB failure without
        // allocating or reading gigabytes. FSCTL_SET_SPARSE keeps disk use tiny.
        #[cfg(windows)]
        {
            use std::os::windows::io::AsRawHandle;
            #[link(name = "kernel32")]
            extern "system" {
                fn DeviceIoControl(
                    handle: *mut std::ffi::c_void,
                    code: u32,
                    input: *const u8,
                    input_len: u32,
                    output: *mut u8,
                    output_len: u32,
                    returned: *mut u32,
                    overlapped: *mut u8,
                ) -> i32;
            }
            let mut returned = 0;
            assert_ne!(
                unsafe {
                    DeviceIoControl(
                        large.as_raw_handle(),
                        0x900c4,
                        std::ptr::null(),
                        0,
                        std::ptr::null_mut(),
                        0,
                        &mut returned,
                        std::ptr::null_mut(),
                    )
                },
                0
            );
        }
        let offset = 0x8000_0100u32;
        large.seek(SeekFrom::Start(offset as u64)).unwrap();
        large.write_all(b"second").unwrap();
        drop(large);
        let mut index = IDX::new();
        let mut first = VfsMetadata::new();
        first.filename = "rose.vfs".into();
        let mut deleted = VfsFileMetadata::new();
        deleted.filepath = "3DDATA/STB/TEST.STB".into();
        deleted.is_deleted = true;
        first.files.push(deleted);
        let mut second = VfsMetadata::new();
        second.filename = "rose_2.vfs".into();
        let mut entry = VfsFileMetadata::new();
        entry.filepath = "3DDATA/STB/TEST.STB".into();
        entry.offset = offset as i32;
        entry.size = 6;
        second.files.push(entry);
        index.file_systems = vec![first, second];
        index
            .write(&mut File::create(temp.path().join("data.idx")).unwrap())
            .unwrap();
        let assets = Assets::open(temp.path()).unwrap();
        assert_eq!(assets.read("3ddata\\stb\\test.stb").unwrap(), b"second");
        assert!(assets.read("missing").is_err());
        // A partial download must fail rather than return a partial file.
        File::options()
            .write(true)
            .open(temp.path().join("rose_2.vfs"))
            .unwrap()
            .set_len(offset as u64 + 2)
            .unwrap();
        assert!(assets.read("3ddata/stb/test.stb").is_err());
    }

    #[test]
    fn extracted_item_data_needs_no_npc_or_shop_tables() {
        let temp = tempfile::tempdir().unwrap();
        let stb = temp.path().join("3ddata/stb");
        fs::create_dir_all(&stb).unwrap();
        fs::write(stb.join("list_weapon.stb"), b"weapon").unwrap();
        for root in [temp.path(), stb.parent().unwrap(), &stb] {
            let assets = Assets::open(root).unwrap();
            assert_eq!(
                assets.read("3DDATA/STB/LIST_WEAPON.STB").unwrap(),
                b"weapon"
            );
        }
    }
}
