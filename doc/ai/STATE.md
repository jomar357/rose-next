# Current state

_Last updated: 2026-09-24 at the closing of session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md)._

## Objective

None active. The last objective, **PM-011 (run the game locally)**, was achieved on 2026-09-24:
the PM logged in as `jomar357` and reported the game working. Before that, the continuity setup
(PM-002) was completed.

## Approved scope

- No development task is authorised. Ask the PM for the next priority (do not pick one from
  historical notes).
- Standing rules: do not use jCodeMunch in this repo (PM-015); commits, pushes, merges and
  deletions need explicit authorisation per action.

## Progress

- PR #1 merged into `master` as `5f5d006` (continuity system + local-run setup); one more commit
  on top with `AGENTS.md` and the closing records (PM-021).
- Local setup on the PM's machine works: see [local-setup-runbook](topics/project/local-setup-runbook.md)
  and the launchers in [run/](../../run/README.md).

## Blockers and constraints

- None known. Game data, build output and server config exist only on the PM's machine (gitignored).

## Next action

Ask the PM for the next development priority.

## Active session(s)

- None. [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md) closed 2026-09-24.

## Repository

- `C:\Users\Jomar\Desktop\Rose\rose-next`, `master` even with `origin/master` (see below).
- The `AGENTS.md` change (PM-020) and the closing record edits are committed on `master` and
  pushed (PM-021), in the commit after `5f5d006` titled "AGENTS.md: point to this machine's
  Claude memory; session closing records". Working tree clean after that.
- Branch `local-run-setup` (`4a349a3`) remains locally and on `origin`; it is merged.
- Gitignored local state: `data/`, `Exes/` game files and client binaries, `bin/`, `build/`,
  `dev/server/`, `src/target/`. Game-data archive: `%USERPROFILE%\Downloads\Rose deluxe + Plane fix.rar`.
- At closing the three servers and a client were left running for the PM (stop: `run/stop-all.bat`).
