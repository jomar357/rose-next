# Latest handoff

_From session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md), interim checkpoint
2026-09-24. The session is **not closed**. Previous interim handoff (continuity setup complete,
waiting on priority/commit/data questions) is superseded; its substance is in the session record
and in DECISIONS PM-010..PM-016._

## Completed

- Continuity system committed (`28a777f`, local only, not pushed).
- PM-011 "run the game locally": toolchain installed (pwsh, just, MSVC v142); everything builds in
  release x86; the project's 4 test programs pass; game data from the README's MEGA archive is in
  `Exes/` (client) and `data/` (servers); database migrated; login, world and game servers run
  against `dev/server/server.toml`.

## Remaining

- PM-011 achieved: the PM logged in as `jomar357` and reported the game working.
- Review and merge the PR from `local-run-setup` into `master`; then fast-forward local `master`.
- Launchers for testing without commands: [run/README.md](../../run/README.md).

## Watch out for

- Build inside `vcvarsall x86 -vcvars_ver=14.29` with `RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc`;
  mixing MSVC 14.44 and 14.29 breaks the Rust link.
- Do not use jCodeMunch in this repo (PM-015). Do not use the tracked `Exes/server.toml`.
- The servers were started by a Claude session and may not survive it; restart per the runbook.

## Next-session prompt (copy as is)

```text
You are continuing work on Rose Next (C:\Users\Jomar\Desktop\Rose\rose-next) under the direction
of the Project Manager. Read, in order: CLAUDE.md, doc/ai/INDEX.md, doc/ai/STATE.md,
doc/ai/HANDOFF.md, then doc/ai/topics/project/local-setup-runbook.md. Reconcile them with the
checkout (git status -sb, git rev-parse HEAD, git status --porcelain=v1 -uall) and report any
mismatch; if STATE.md lists an open session that was never closed, treat its work as interrupted
and recover from its session record plus the diff. Run `python scripts/verify-ai-docs.py --quiet`.
The current objective is PM-011 (run the game locally). Check whether the three servers are running
and restart them per the runbook (or run/start-servers.bat) if not, then ask the PM for the next
development priority (PM-011 is achieved). Do not use jCodeMunch in this repo. Do not commit or push without the PM's explicit say-so.
Open a new session record under doc/ai/sessions/ and follow doc/ai/SESSION_PROTOCOL.md.
```
