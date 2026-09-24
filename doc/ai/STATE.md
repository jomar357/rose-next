# Current state

_Last updated: 2026-09-24 by session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md)._

## Objective

**PM-011: be able to run the game locally** on the PM's machine: **achieved** 2026-09-24 (the PM
logged in as `jomar357` and reported the game working). Continuity setup (PM-002) is done
and committed (`28a777f`).

## Approved scope

- PM-011 (run locally) and PM-014 (install everything needed). PM-015: do **not** use jCodeMunch here.
- Game data from the README's MEGA archive (PM-016); no program from the archive is run.
- Commits/pushes need explicit authorisation per action. PM-017/PM-018: commit this work and open
  a PR into `master` from branch `local-run-setup` (no direct push to `master`).

## Progress (details: [local-setup-runbook](topics/project/local-setup-runbook.md))

- Installed: PowerShell 7, `just`, MSVC v142 (14.29.30133 + ATL/MFC) in VS 2022 Build Tools.
- Built (verified): thirdparty, Rust i686 tools and `rose-next.sln` in release x86 with v142 inside
  a 14.29 developer environment; 4 test programs pass. Servers running (login, world, game).
- `rose-vfs` fixed for offsets past 2 GB (IMP-016, uncommitted code change).
- Game data: `Exes/` = client run folder (data.idx, rose.vfs, sound, …); `data/` = unpacked VFS
  for the servers (36,264 files).
- Database: Laragon PostgreSQL 18.2, existing empty `rose-next` DB; migrations 0002 and 0003 applied
  on top of 0001 (verified). GM account `jomar357` (access 2048) exists; password given in chat
  only.
- Local server config: `dev/server/server.toml` (gitignored; generated login-server password, not
  recorded anywhere).

## Blockers and constraints

- None for PM-011.

## Next action

Get the PR from `local-run-setup` reviewed and merged; then ask the PM for the next development
priority. Double-click launchers for testing: `run/`.

## Active session(s)

- [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md): open, not closed.

## Repository

- `C:\Users\Jomar\Desktop\Rose\rose-next`. Work committed on branch `local-run-setup` (from `master`
  `28a777f`, itself 1 ahead of `origin/master` `84f6206`), pushed, PR open into `master`.
  Local `master` still points at `28a777f` and is not pushed.
- Never commit: the game data (`data/`, `Exes/` game files) and `dev/server/` are gitignored. The
  MEGA `.rar` was deleted from the repo root (a copy remains in `%USERPROFILE%\Downloads`).
- Gitignored local state this work depends on: `data/` (2.3 GB), `Exes/` game files + client
  binaries, `bin/`, `build/vfs-extract/`, `build/vfs-list.txt`, `dev/server/`, `src/target/` (stale).
- Running at this checkpoint: login, world and game servers (own windows) and a client.
