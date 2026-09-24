# Code conventions and dev environment

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 109-135 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=109-135 sha256=d013a136e9690c1a4820abb1395a1e01fe8ccbb9c2a4332c1002c1ee4d43f205 -->
## Code Conventions

- C++ formatting: **do not run clang-format over the tree.** `.clang-format` /
  `.clang-format-ignore` are inherited from the original team and the checked-in code no
  longer matches what current clang-format produces (VS2019's 12.0.0 rewrites ~4x more
  lines than a typical change touches, burying real diffs in churn). Match the style of
  the surrounding code by hand instead. The `scripts/format_code.py` driver was removed
  for this reason; the config files are kept only so editors have something to read.
- Rust: standard `cargo fmt`
- Prefix conventions: `C` for classes (CItem, CObjCHAR), `m_` for members, `g_` for globals
- Server packet handlers: `Recv_cli_*` / `Send_gsv_*` naming
- Client packet handlers: `Recv_gsv_*` / `Send_cli_*` naming

## Dev Environment

```powershell
just dev-setup              # Creates dev/ symlinks for assets
just client release         # Run client
just server-all release     # Run all servers
just loginserver release    # Run individual server
```

- Client looks for assets in `dev/game/`
- Servers look for data in `data/` (configurable in server.toml)
- A/B test two client builds in the real game: `scripts/ab-build.ps1 stage <name>` / `use <name>` / `toggle`. `rosenext.exe` imports `znzin.dll` by name, so the exe+dll must be swapped as a **pair** — never rename one half. See the header for the HUD-labelling and vsync caveats.
- Auto-connect: `rosenext.exe --server 127.0.0.1 --username user --password pass --auto-connect-server 1 --auto-connect-channel 1 --auto-connect-character CharName`

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
