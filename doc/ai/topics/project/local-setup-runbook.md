# Local setup runbook (build and run on a developer machine)

> **Provenance:** new topic, started 2026-09-24 (session [2026-09-24-continuity-setup](../../sessions/2026-09-24-continuity-setup.md))
> for PM-011 "be able to run this game locally". Written from what was observed on the PM's machine
> (`C:\Users\Jomar\Desktop\Rose\rose-next`, Windows 11 26200). Each step says whether it was
> **verified** here. The upstream instructions are the top-level [README](../../../../README.md)
> (Quickstart, Requirements, Build, Client → Assets, Server → Database).

## What the repository does and does not contain (verified 2026-09-24, `28a777f`)

- Complete **source** for client, servers, engine, tools, thirdparty libraries (Git LFS: all 263
  objects present, including `thirdparty/directx9/bin/x86/d3dx9_43.dll` and
  `thirdparty/discord-2.5.6/lib/x86/discord_game_sdk.dll`), database migrations and scripts.
- **No game data.** `data/` is gitignored by design ([data/README.md](../../../../data/README.md)); the only
  tracked files are `.gitkeep`s and the RmlUi `.rml/.rcss` + font. No STB/ZON/ZMS/`.vfs`/`data.idx`
  exists anywhere in the checkout or its history. The README names the source: the "original ROSE
  Next assets" on MEGA (link in README → Client → Assets), or your own ROSE data.
- Consequence to expect: the inherited docs describe many data changes (Karkia, Oro 667, Skaaj,
  balance passes, repairs) made by scripts against the previous maintainer's `data/` and reference
  dumps. Whether the MEGA assets already include them is **unknown**; several scripts need
  reference dumps that are not available (see [UNAVAILABLE_KNOWLEDGE](../../UNAVAILABLE_KNOWLEDGE.md) U3).

## Toolchain on the PM's machine (as of 2026-09-24, verified)

| Requirement (README) | State | Notes |
|---|---|---|
| Rust `stable-i686-pc-windows-msvc` | installed | Default toolchain is x86_64 and no override is set for `src/`: see *Traps* |
| Visual Studio 2019 toolset **v142** | MSVC **14.29.30133** + ATL/MFC added to VS 2022 Build Tools 17.14 (which also has 14.44 / v143) | Component IDs `Microsoft.VisualStudio.Component.VC.14.29.16.11.{x86.x64,ATL,MFC}`; see *Updates* for the install story |
| Windows 10 SDK | 10.0.26100 installed | Three thirdparty projects pin 10.0.18362: override on the command line |
| PostgreSQL 12+ | **18.2** via Laragon (`C:\laragon\bin\postgresql\postgresql\bin`), running, localhost:5432 | Not on PATH; local trust auth for `postgres` |
| Python 3 | 3.13 via Laragon | |
| PowerShell 7 (`pwsh`) | installed 2026-09-24 via winget | `justfile` uses `pwsh.exe`; open a new shell to get PATH |
| `just` | installed 2026-09-24 via winget | The `just build` flow was **not** used or tested; the steps below were |
| `flatc` | built by thirdparty into `bin/release/thirdparty/` | Needed by `common-lib`'s `build.rs` |
| 7-Zip | present | Extracts the MEGA `.rar` |

## Verified procedure (release, x86)

1. **Thirdparty** (must come before Rust: `common-lib` needs `flatc.exe`):
   `MSBuild.exe thirdparty.sln "-p:Configuration=release;Platform=x86;WindowsTargetPlatformVersion=10.0" -m -nodeReuse:false`
2. **Rust tools + `rose_common.lib`**, from inside `src/` (so `src/.cargo/config` sends output to `bin/`):
   `set RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc` then `cargo build --release`.
   Optional here: step 3's pre-build does it again.
3. **Rose Next C++** inside a **v142 developer environment**, so MSBuild, `rustc` and the `cc` crate
   all use MSVC 14.29:
   ```bat
   call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86 -vcvars_ver=14.29
   set RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc
   MSBuild.exe rose-next.sln "-p:Configuration=release;Platform=x86;WindowsTargetPlatformVersion=10.0" -m -nodeReuse:false
   ```
   If Rust was ever built outside that environment, first run
   `cargo clean -p libsqlite3-sys --release` in `src/` (never plain `cargo clean --release`).
4. **Game data**: the client needs `data.idx` + `rose.vfs` in its folder (`Exes/` here); the servers
   need the same content unpacked into `data/`: `bin\release\rose-vfs.exe Exes\data.idx extract-all build\vfs-extract`,
   then copy into `data/` without overwriting tracked files.
5. **Database**: `rose-next` DB with all `database/migrations/*/up.sql` applied, in order.
6. **Servers**: local `dev/server/server.toml`; start login → world → game from `bin/release` with
   `--config <that file>`.
7. **Account**: `scripts/create-account.ps1` with `-ServerToml dev\server\server.toml` and `PGBIN` set.
8. **Client**: copy `rosenext.exe`, `znzin.dll`, `triggervfs.dll`, `d3dx9_43.dll`,
   `discord_game_sdk.dll` from `bin/release` into `Exes/`; run `.\rosenext.exe --server 127.0.0.1` there.

MSVC output here is English (the inherited note about French diagnostics was the previous
maintainer's machine); still search for both `": error"` and `": erreur"`.

## Traps

- `src/common/common.vcxproj`'s pre-build is a plain `cargo build [--release]` that builds the whole
  workspace. Without a rustup override for `src/` it builds **x86_64**; set
  `RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc` for the build (IMP-012), or have the machine owner
  run `rustup override set stable-i686-pc-windows-msvc` in `src/` (the README's step).
- Mixed MSVC versions: see step 3. Leftover MSBuild nodes block the VS installer (exit 8006);
  use `-nodeReuse:false`.
- `rose-vfs` needed a fix to read offsets past 2 GB (IMP-016).

## Status

Build, tests, database and all three servers verified 2026-09-24. Login and play: reported working
by the PM the same day (see *Updates*).

## Updates

- **2026-09-24 — v142 installed; correct component IDs.** In VS 2022 the v142 toolset is
  `Microsoft.VisualStudio.Component.VC.14.29.16.11.x86.x64` (+ `.ATL`, `.MFC`). The older IDs
  `...VC.v142.x86.x64/.ATL/.MFC` do not exist there, and the command-line installer ignores unknown
  IDs and still exits 0, which is why the first four attempts "succeeded" without installing
  anything (the GUI names them in a "packages aren't available" dialog). A fifth attempt exited
  **8006** because MSBuild worker nodes left over from earlier builds were running; stop them
  (`taskkill /F /IM MSBuild.exe`, `mspdbsrv.exe`) and build with `-nodeReuse:false`. Working
  command (elevated), using the Build Tools bootstrapper:
  `vs_BuildTools.exe modify --installPath "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools" --add Microsoft.VisualStudio.Component.VC.14.29.16.11.x86.x64 --add Microsoft.VisualStudio.Component.VC.14.29.16.11.ATL --add Microsoft.VisualStudio.Component.VC.14.29.16.11.MFC --passive --norestart --wait`
  → MSVC 14.29.30133 installed (verified). With v142 available, the `PlatformToolset=v143`
  override is no longer used (IMP-015).
- **2026-09-24 — Windows SDK override still needed.** `flatc`, `fmt` and `libpqcommon` pin SDK
  10.0.18362.0 (not installed); pass `-p:WindowsTargetPlatformVersion=10.0` (IMP-014).
- **2026-09-24 — run cargo from `src/`.** `target-dir="../bin"` lives in `src/.cargo/config`, which
  cargo only reads when the working directory is inside `src/`. Running with `--manifest-path`
  from the repo root sends output to `src/target/` instead (happened once; that folder is
  gitignored and holds a stale duplicate build).
- **2026-09-24 — game data obtained (PM-016).** README's MEGA file "Rose deluxe + Plane fix.rar"
  (775 MB; SHA-256 `8a60d3b21524d8a6fc43a6574dc5a88c4c30c18edc7f6eb7fc948dc63e66503c`; one copy in
  the repo root, **untracked — never `git add` it**, one in `%USERPROFILE%\Downloads`). It is a
  client distribution, not raw `data/`. Layout now: `Exes/` = run folder (data.idx, rose.vfs,
  sound, 3ddata, Chat, clanmark, the archive's rose-next.ini); `data/` = unpacked VFS for the
  servers (36,264 files, 2.3 GB); see DECISIONS IMP-016/IMP-017. The VFS was baked 2026-09-22
  23:21, i.e. from the previous maintainer's data about two days before HEAD `84f6206`.
- **2026-09-24 — sibling folders exist.** `C:\Users\Jomar\Desktop\Rose\` also holds `RoseZA.zip`
  (2.2 GB), `Evo 434`, `Rose Revolution`, `SHO`, `Na`, `Backups`, `Tools`; RoseZA is one of the
  reference dumps the inherited docs call missing. Not inspected yet.
- **2026-09-24 — full build verified (v142).** Two more traps, both solved without repo changes:
  (1) after the switch to v142, `common`'s pre-build `cargo build --release` (it builds the whole
  Rust workspace, tools included) failed to link `rose-vfs`/`pipeline`/`npc-shop-editor`/
  `gm-item-browser`: `unresolved external __ltof3 / __dtoul3_legacy` from `libsqlite3-sys`.
  MSBuild's environment points `LIB` at the 14.29 runtime while the `cc` crate and `rustc`
  auto-detect the newest MSVC (14.44), so SQLite was compiled for 14.44 and linked against 14.29.
  (2) Fix: run the build inside a v142 developer environment so every tool agrees, and clear the
  stale SQLite build once. The working script (kept only in the session scratchpad; reproduced here):
  ```bat
  call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86 -vcvars_ver=14.29
  set RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc
  cd /d <repo>\src && cargo clean -p libsqlite3-sys --release
  cd /d <repo> && MSBuild.exe rose-next.sln "-p:Configuration=release;Platform=x86;WindowsTargetPlatformVersion=10.0" -m -nodeReuse:false
  ```
  Never run `cargo clean --release` without `-p`: `bin/release` is shared with the C++ output.
  Result: `rose-next exit=0`; `bin/release` has `rosenext.exe`, `znzin.dll`, `triggervfs.dll`,
  `sho_loginserver.exe`, `sho_worldserver.exe`, `sho_gameserver.exe`, tools and tests.
  `combat_presenter_tests`, `store_item_code_tests`, `tuning_preview_tests` pass;
  `vfs_buffer_tests <repo>\Exes` passes (917,359 checks against the real 2.36 GB VFS).
- **2026-09-24 — database.** Laragon PostgreSQL 18.2 on localhost:5432, local trust auth for user
  `postgres` (no password needed on this machine). A `rose-next` database already existed with only
  migration 0001 applied and no rows; 0002 and 0003 were applied (`psql -v ON_ERROR_STOP=1
  --single-transaction -f database/migrations/<m>/up.sql`), verified by the `skills` default and
  `exp` = bigint. There is no migration-tracking table: check columns to know what is applied.
- **2026-09-24 — servers run (verified).** Local config `dev/server/server.toml` (gitignored; made
  from `doc/server.toml.example`: this checkout's `data/` and `data/clanmark`, logs in
  `dev/server/log/`, login-server `password` = random 64 hex chars because the server copies a
  fixed 64 bytes). The tracked `Exes/server.toml` still has the previous maintainer's paths and
  credentials; do not use or copy it. Start from `bin/release`, in this order:
  ```powershell
  .\sho_loginserver.exe --config C:\Users\Jomar\Desktop\Rose\rose-next\dev\server\server.toml
  .\sho_worldserver.exe --config ...same...
  .\sho_gameserver.exe  --config ...same...
  ```
  Observed: login "Server ready"; world "Connected to login server"; game loaded 60 zones (incl.
  Oro, Skaaj #89, Karkia) and "Connected to WORLD server", 0 errors, 14 warnings, all the expected
  no-`.MOV` fallback. Zones warned (exact): 14, 57, 83, 85, 86, 87, 88, 89, 131, 133, 134, 135,
  136, 144. The other Oro zones (71, 72, 73, 78-81) have `.MOV` files.
- **2026-09-24 — client run folder.** `Exes/` now also holds this build's `rosenext.exe`,
  `znzin.dll`, `triggervfs.dll`, `d3dx9_43.dll`, `discord_game_sdk.dll` (copied from `bin/release`;
  keep exe + znzin.dll as a pair). The `rose-next.ini` is the archive's (borderless fullscreen
  1920x1080, RmlUi on). Launch: `cd Exes; .\rosenext.exe --server 127.0.0.1`.
- **2026-09-24 — account creation.** `scripts/create-account.ps1` reads `Exes/server.toml` by
  default and finds psql via `PGBIN`, so on this machine:
  `$env:PGBIN="C:\laragon\bin\postgresql\postgresql\bin"; pwsh -File scripts\create-account.ps1 -Email <name> -Password <password> -AccessLevel 2048 -ServerToml dev\server\server.toml`
  (2048 = full GM rights per the README; omit for a normal account). Left to the PM because it
  needs a password of their choosing.
- **2026-09-24 — double-click launchers and first account.** `run/` holds `start-all.bat`,
  `start-servers.bat`, `start-client.bat`, `stop-*.bat` and `create-account.bat` (see
  [run/README.md](../../../../run/README.md), DECISIONS IMP-018). Verified: `stop-servers.bat` stopped the
  three servers; `start-servers.bat` started them in their own windows (game server "Connected to
  WORLD server" at 17:16 local); `start-client.bat` launched this build's client, which reached the
  login scene (client log: cache warm, `LoginCameraMotion`). A GM account (`jomar`, access 2048)
  exists; its password was given to the PM in chat only. **Not yet verified:** logging in and
  entering the world. PowerShell 7 was installed by winget as an MSIX package: `pwsh.exe` is the
  `%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe` alias, not `C:\Program Files\PowerShell\7`.
- **2026-09-24 — archive copy removed.** The repo-root `.rar` was deleted at the PM's request
  (PM-017); the identical copy in `%USERPROFILE%\Downloads` remains as the local source of the game
  data.
- **2026-09-24 — client login limits.** The client refuses IDs under 6 and passwords under 8
  characters (IMP-019). The first account had a 5-character name and was renamed to `jomar357`;
  `scripts/create-account.ps1` now rejects names outside 6-30 and passwords outside 8-30.
  Verified: a 5-character name is rejected with "Login name must be 6-30 characters". Logging in
  and entering the world remain unverified at this checkpoint (no login yet in the server logs).
- **2026-09-24 — PM-011 met (reported by the PM).** The PM logged in as `jomar357` with the
  client from `Exes/` and reported "I am already logged in and the game is working now". Observed
  by the AI only up to the login scene; in-game behaviour beyond that is the PM's report.
