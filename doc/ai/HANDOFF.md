# Latest handoff

_From session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md), closed 2026-09-24
by the PM ("Our work here is done"). The previous handoff is preserved verbatim in that session
record._

## Completed

- AI continuity system: compact `CLAUDE.md` guides, verbatim topic files, archive, records,
  session protocol, `scripts/verify-ai-docs.py`.
- The game runs locally on the PM's machine: v142 build, game data, database, servers, client,
  double-click launchers in `run/`. The PM logged in as `jomar357` and reported it working.
- PR #1 merged into `master` (`5f5d006`).

## Remaining

- No development task is authorised: ask the PM for the next priority.
- `AGENTS.md` now points agents to this machine's Claude memory index as an optional, secondary
  source (PM-020); committed and pushed with the closing records (PM-021).
- Suggestions awaiting a PM decision: rotate the credentials in the tracked `Exes/server.toml` and
  untrack it; delete the merged branch `local-run-setup`.

## Watch out for

- Build inside `vcvarsall x86 -vcvars_ver=14.29` with `RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc`
  (see the runbook). Never `cargo clean --release` without `-p`.
- Do not use jCodeMunch in this repo (PM-015). Do not use the tracked `Exes/server.toml`.
- Game data and build output are local only (gitignored).

## Next-session prompt (copy as is)

```text
You are continuing work on Rose Next (C:\Users\Jomar\Desktop\Rose\rose-next) under the direction
of the Project Manager. Read, in order: CLAUDE.md, doc/ai/INDEX.md, doc/ai/STATE.md,
doc/ai/HANDOFF.md. Reconcile them with the checkout (git status -sb, git rev-parse HEAD,
git status --porcelain=v1 -uall) and report any mismatch; everything from the last session is
committed and pushed to master. On the PM's machine, also read the Claude
memory index named in AGENTS.md step 3 if it exists (secondary to doc/ai/). Run `python scripts/verify-ai-docs.py --quiet`.
No development task is authorised: ask the PM for the next priority. For running the game, read doc/ai/topics/project/local-setup-runbook.md and
use the launchers in run/. Do not use jCodeMunch in this repo. Do not commit, push, merge or delete
anything without the PM's explicit say-so. Open a new session record under doc/ai/sessions/ and
follow doc/ai/SESSION_PROTOCOL.md.
```
