# Session 2026-09-24: continuity setup

- **Status:** **closed** 2026-09-24 by the PM's closing phrase (PM-019); see *Closing* below
- **Tool / model:** Claude Code desktop app, `claude-opus-5-5`
- **Checkout:** `C:\Users\Jomar\Desktop\Rose\rose-next`, remote `origin` = https://github.com/jomar357/rose-next.git
- **Branch / base:** `master` at `84f6206723fb4a8abf27df8a71eeb458fd734553`, even with `origin/master` at start
- **Working tree at start:** clean (no staged, unstaged or untracked files)
- **Authorised scope:** PM-002 / PM-003 in [DECISIONS.md](../DECISIONS.md): documentation and project instructions only. No commit or push authorised.

## Starting situation (verified 2026-09-24 in this checkout)

- Auto-loaded instruction files: root `CLAUDE.md` (99,586 B, 856 lines), `src/client/CLAUDE.md`
  (176,345 B, 745 lines), `src/sho_gameserver/CLAUDE.md` (23,060 B, 207 lines),
  `xadet/rose-online-map-editor/CLAUDE.md` (19,140 B, 305 lines); `AGENTS.md` (663 B). About
  318 KB of guides, loaded whenever a session touched those directories.
- `AGENTS.md` pointed at `C:\Users\Thomas\.claude\projects\...\memory\MEMORY.md`. `C:\Users\Thomas`
  does not exist here. This session's own auto-memory directory was empty.
- No `CLAUDE.local.md`, `GEMINI.md`, `.cursorrules` or Copilot instructions. `.claude/settings.local.json`
  is tracked and holds permission rules for Thomas's paths (left alone).
- `data/` has 16 tracked files only; `bin/`, `build/`, `dev/` absent; `Exes/` holds `server.toml`
  only; reference dumps absent. All 461 commits are by `ThomasL`.
- jCodeMunch: repo resolvable but not indexed; not indexed this session (docs-only).
- 43 first-party Markdown files inventoried (paths/sizes/headings); vendored docs under
  `thirdparty/` and `website/.../vendor/` excluded.

## What was done

1. Archived the five originals byte-for-byte to `doc/ai/archive/2026-09-24/*.txt` with
   `manifest.json` (path, date, revision, git blob, SHA-256) and `MANIFEST.md`; added
   `doc/ai/archive/.gitattributes` (`* -text`).
2. Wrote `scripts/ai-docs-migrate-2026-09-24.py`: splits each archived guide into contiguous line
   ranges (31 + 32 + 7 + 4 segments + AGENTS 1) and writes them verbatim into 69 topic files under
   `doc/ai/topics/{project,client,gameserver,map-editor}/` with provenance headers and an *Updates*
   section; re-targets relative links (7 originally broken links in the client guide repaired);
   writes `doc/ai/migration/2026-09-24-mapping.{json,md}`. Checks full line coverage and that no
   segment splits a code fence.
3. Wrote `scripts/verify-ai-docs.py` (read-only): archive hashes, archive vs git blob, coverage,
   per-block byte identity after undoing recorded link rewrites, whole-file reconstruction,
   relative-link existence, size budgets.
4. Wrote the continuity records: `INDEX.md`, `SESSION_PROTOCOL.md`, `DECISIONS.md` (PM-001..009,
   IMP-001..011, INH-001..013), `OPEN_QUESTIONS.md` (3 PM questions, 3 conflicts, 19 inherited
   unfinished items), `UNAVAILABLE_KNOWLEDGE.md` (U1-U9, embeds the old `AGENTS.md` verbatim),
   `STATE.md`, `HANDOFF.md`, this record.
5. Replaced the four `CLAUDE.md` files with compact guides and `AGENTS.md` with a portable entry
   point. Sizes after: root 118 lines / 8,322 B; client 115 / 7,663 B; gameserver 54 / 3,770 B;
   map editor 42 / 2,917 B.
6. Recorded inherited conflicts in the affected topics' *Updates* (vsync frame cap; historical VFS
   threshold; RmlUi scope).
7. Saved a short user-profile note to Claude auto-memory pointing at `doc/ai/` (not the record).

## Failed attempts / corrections during the session

- First topic generation wrote headers with one `../` too many (links to the archive and INDEX
  resolved to `doc/` instead of `doc/ai/`). Caught by inspection and by the verifier's link check;
  fixed in the migrator (`depth = key.count("/") + 1`) and regenerated with `--force`. Archives were
  not touched by the regeneration (hash-checked).
- Heading scan initially counted `#` lines inside code fences as headings (root guide's build
  block). The migrator therefore checks fence balance per segment rather than trusting headings.

## Verification

Command (run from the repo root, working tree = this session's uncommitted changes on `84f6206`):

```bash
python scripts/verify-ai-docs.py
```

Result of the final run: see *Final verification* below (filled in at the checkpoint).

Not verified: any technical claim inside the topics (all inherited); rendering of the Markdown in
GitHub (only link targets were checked, not anchors); whether other AI tools auto-load `AGENTS.md`.
Byte counts are not token counts; no token measurement was made.

## Checkpoint verification (2026-09-24, working tree = this session's uncommitted changes on `84f6206`)

- `python scripts/verify-ai-docs.py` → `0 failure(s), 0 warning(s)`: five archives match their
  SHA-256 and the git blobs at `84f6206`; `CLAUDE.md` (31 segments), `src/client/CLAUDE.md` (32),
  `src/sho_gameserver/CLAUDE.md` (7), `xadet/rose-online-map-editor/CLAUDE.md` (4) and `AGENTS.md`
  (1) rebuilt byte-for-byte; 493+ relative links resolve; root guide 118 lines.
- Negative test on a scratch copy (outside the repo): changing one word inside a verbatim block →
  2 failures naming `CLAUDE.md:729-748`; appending a byte to an archive → hash failure. Without git
  the verifier warns (5) instead of failing on the git comparison.
- Independent naive check (concatenate blocks, plain `diff` against archives, no link undo): the
  only differing lines are the 15 recorded link re-targetings (root 6, client 9); gameserver, map
  editor and AGENTS identical.
- Not run: builds, tests, data scripts (nothing to build or run them against here).

## Commit (PM-010)

- PM said "Commit the documentation changes"; answered a question choosing author
  `jomar357` with the PM's account email, applied with `git -c` for this commit only (no git identity
  is configured on this machine), and committing directly on `master`. Push not authorised.
- Staged by explicit paths (the five guides, `doc/ai/`, the two scripts); verifier re-run before
  committing. The hash cannot be written inside its own commit:
  `git log -1 --format=%H -- doc/ai/STATE.md`.

## Run the game locally (PM-011 .. PM-016)

After the commit, the PM set the priority "be able to run this game locally", said "install
everything that is needed", stopped jCodeMunch use for this project, and approved the MEGA game-data
download. Full verified procedure and every trap: [local-setup-runbook](../topics/project/local-setup-runbook.md);
decisions IMP-012..IMP-017 in [DECISIONS](../DECISIONS.md).

Chronology (all 2026-09-24):
1. Inventory: no game data in the repo (by design); VS 2022 Build Tools with only v143; Rust i686
   present; `just`, `pwsh`, PostgreSQL-on-PATH missing; Laragon PostgreSQL 18.2 running.
2. Installed `pwsh` and `just` (winget). v142: four installer attempts "succeeded" without
   installing (wrong component IDs, silently ignored); a fifth hit exit 8006 (leftover MSBuild
   nodes); the sixth with IDs `...VC.14.29.16.11.*` installed MSVC 14.29.30133.
3. First builds with a v143 override: thirdparty needed `WindowsTargetPlatformVersion=10.0`;
   Rust needed thirdparty's `flatc` first and must run from `src/`; `rose-next.sln` failed on v143
   (C7664 in `ioDataPOOL.h`, `std::unary_function` in three engine files). Switched to v142 rather
   than edit game code (IMP-015).
4. v142 build failed at `common`'s cargo pre-build: SQLite object compiled by MSVC 14.44, linked
   against 14.29 libs. Fixed by building inside `vcvarsall x86 -vcvars_ver=14.29` after
   `cargo clean -p libsqlite3-sys --release`. Build succeeded; 4 test programs pass.
5. Game data: browser-pane download of "Rose deluxe + Plane fix.rar" (PM also saved a copy in the
   repo root). It is a client distribution. Extraction slip: `-x!*.exe` did not match files in the
   archive's subfolder, so its prebuilt binaries were extracted into `Exes/`; none was run; they
   were deleted from `Exes/` (and the VFS's baked `Map Editor.exe/.pdb` + irrKlang DLL from `data/`).
6. `rose-vfs extract-all` died past 2 GB → fixed sign extension in
   `src/tools/vfs-browser/src/vfs.rs` (IMP-016) → all 36,264 files extracted and copied into `data/`
   without overwriting tracked files.
7. Database: existing empty `rose-next` DB had only migration 0001; applied 0002 and 0003.
8. Local `dev/server/server.toml`; login, world and game servers started from `bin/release` and
   connected (60 zones, 0 errors, 14 expected no-`.MOV` warnings).

Still to do: PM creates an account; launch the client and log in (not yet verified).

Processes left running at this checkpoint: `sho_loginserver.exe`, `sho_worldserver.exe`,
`sho_gameserver.exe` (started as background tasks of this Claude session; they may stop when the
session ends).

## Launchers, account, PR (PM-017, PM-018)

- `run/` launchers written and tested: `stop-servers.bat` and `start-servers.bat` (servers in
  their own windows), `start-client.bat` (client reached the login scene). First versions broke
  under a PATH containing Git's GNU `find`/`timeout`; tools are now called by full path.
- Account: created `jomar` (GM 2048) with a generated password given in chat only; the client
  rejected it ("Email too short", minimum 6); renamed to `jomar357` in the database; the account
  script now enforces the client's limits (IMP-019).
- The repo-root `.rar` was deleted at the PM's request.
- Privacy check before publishing (public repo): removed the PM's email address from document
  text (it remains in commit author metadata, as chosen); no passwords in any file.
- PM asked for a PR: the work goes on branch `local-run-setup` and a PR into `master` (PM-018).
- The Claude Code process restarted mid-task; recovered from the checkout and logs (servers and
  a client were still running; no login yet recorded in the server logs).
- The PM then reported: "I am already logged in and the game is working now" (PM-011 met, as
  reported by the PM).

## Closing (2026-09-24, PM-019)

**Completed this session**
- Continuity system (PM-002): compact guides, 69 verbatim topics, archive, mapping, records, protocol,
  verifier. Commit `28a777f`.
- Run the game locally (PM-011): toolchain installed, v142 build, game data, database, servers,
  launchers, account; the PM logged in and reported the game working. Commit `4a349a3`.
- PR #1 (https://github.com/jomar357/rose-next/pull/1) merged into `master` as `5f5d006`.

**Repository state at closing** (recorded after the merge, before these record edits)
- Repo `C:\Users\Jomar\Desktop\Rose\rose-next`, remote `origin` https://github.com/jomar357/rose-next.git.
- Branch `master` at `5f5d006`, even with `origin/master`. Branch `local-run-setup` at `4a349a3`
  exists locally and on `origin` (not deleted).
- Working tree was clean after the merge. The only changes after that are these closing record
  edits (`doc/ai/DECISIONS.md`, `STATE.md`, `HANDOFF.md`, this file): **uncommitted, unpushed**.
- No unrelated pre-existing changes.
- Local state needed to continue, all gitignored and only on this machine: `data/` (unpacked VFS,
  2.3 GB), `Exes/` (client run folder: data.idx, rose.vfs, sound, the built client binaries),
  `bin/release/` (build output), `dev/server/server.toml` + `dev/server/log/`, `build/vfs-extract/`
  and `build/vfs-list.txt`, stale `src/target/`. Game-data source archive:
  `%USERPROFILE%\Downloads\Rose deluxe + Plane fix.rar`. Database: Laragon PostgreSQL 18.2,
  database `rose-next`, account `jomar357` (password given to the PM in chat only).
- Processes left running at closing, deliberately (the PM is playing): `sho_loginserver.exe`,
  `sho_worldserver.exe`, `sho_gameserver.exe`, `rosenext.exe`. Stop with `run/stop-all.bat`.
- A background `grep` started by the AI for a secret scan may still be running over `data/`; it is
  read-only and harmless.

**Verification at closing**
- `python scripts/verify-ai-docs.py` on the working tree with these closing edits: result recorded
  in the closing reply (run after writing this file).
- `gh pr view 1`: state MERGED, merge commit `5f5d006`, merged 2026-09-24T11:07:25Z.
- `git status -sb` after `git pull --ff-only`: `master...origin/master`, clean.
- Build and tests: last run earlier this session on the tree now committed as `4a349a3` (release x86,
  v142); **not re-run** after the merge. The merge commit's tree equals `4a349a3`'s (merged with no
  other changes on `master`).
- Not verified by the AI: gameplay beyond the login scene (PM-reported working).

**Open at closing**
- Next development priority: not given.
- Commit of these closing record edits: needs PM authorisation.
- Suggested, not authorised: rotate the credentials in the tracked `Exes/server.toml` and untrack it;
  delete the merged branch `local-run-setup`.
- Inherited open questions and conflicts: [OPEN_QUESTIONS](../OPEN_QUESTIONS.md).

## Addendum after closing (2026-09-24, PM-020)

The PM asked to add this device's Claude memory to `AGENTS.md`, then closed again.
- Memory folder inspected: `MEMORY.md` + `user-pm-role.md` (one user-profile note written this
  session; no project facts that are not also in `doc/ai/`).
- `AGENTS.md`: new step 3 (optional, this machine only, yields to `doc/ai/`); intro sentence
  adjusted. Unlike the inherited pointer (U1), the path exists and is marked optional.
- Repository at this second closing: `master` = `origin/master` = `5f5d006`; **uncommitted**:
  `AGENTS.md`, `doc/ai/DECISIONS.md`, `HANDOFF.md`, `INDEX.md`, `STATE.md`, this file. Nothing else
  changed; processes as recorded above.
- Verification: `python scripts/verify-ai-docs.py` (result in the closing reply); `git status`.
- Then the PM said "commit and push" (PM-021): these edits were committed on `master` and pushed
  to `origin/master`.

## Final verification

See *Closing* above.

## Previous handoff

The handoff that was current when this session closed (replaced at closing), verbatim except that its two relative links were re-targeted for this folder:

> # Latest handoff
>
> _From session [2026-09-24-continuity-setup](2026-09-24-continuity-setup.md), interim checkpoint
> 2026-09-24. The session is **not closed**. Previous interim handoff (continuity setup complete,
> waiting on priority/commit/data questions) is superseded; its substance is in the session record
> and in DECISIONS PM-010..PM-016._
>
> ## Completed
>
> - Continuity system committed (`28a777f`, local only, not pushed).
> - PM-011 "run the game locally": toolchain installed (pwsh, just, MSVC v142); everything builds in
>   release x86; the project's 4 test programs pass; game data from the README's MEGA archive is in
>   `Exes/` (client) and `data/` (servers); database migrated; login, world and game servers run
>   against `dev/server/server.toml`.
>
> ## Remaining
>
> - PM-011 achieved: the PM logged in as `jomar357` and reported the game working.
> - Review and merge the PR from `local-run-setup` into `master`; then fast-forward local `master`.
> - Launchers for testing without commands: [run/README.md](../../../run/README.md).
>
> ## Watch out for
>
> - Build inside `vcvarsall x86 -vcvars_ver=14.29` with `RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc`;
>   mixing MSVC 14.44 and 14.29 breaks the Rust link.
> - Do not use jCodeMunch in this repo (PM-015). Do not use the tracked `Exes/server.toml`.
> - The servers were started by a Claude session and may not survive it; restart per the runbook.
>
> ## Next-session prompt (copy as is)
>
> ```text
> You are continuing work on Rose Next (C:\Users\Jomar\Desktop\Rose\rose-next) under the direction
> of the Project Manager. Read, in order: CLAUDE.md, doc/ai/INDEX.md, doc/ai/STATE.md,
> doc/ai/HANDOFF.md, then doc/ai/topics/project/local-setup-runbook.md. Reconcile them with the
> checkout (git status -sb, git rev-parse HEAD, git status --porcelain=v1 -uall) and report any
> mismatch; if STATE.md lists an open session that was never closed, treat its work as interrupted
> and recover from its session record plus the diff. Run `python scripts/verify-ai-docs.py --quiet`.
> The current objective is PM-011 (run the game locally). Check whether the three servers are running
> and restart them per the runbook (or run/start-servers.bat) if not, then ask the PM for the next
> development priority (PM-011 is achieved). Do not use jCodeMunch in this repo. Do not commit or push without the PM's explicit say-so.
> Open a new session record under doc/ai/sessions/ and follow doc/ai/SESSION_PROTOCOL.md.
> ```

Before that: none (this was the first session with a HANDOFF.md).

### Handoff replaced at the second closing (verbatim, links re-targeted for this folder)

> # Latest handoff
>
> _From session [2026-09-24-continuity-setup](2026-09-24-continuity-setup.md), closed 2026-09-24
> by the PM ("Our work here is done"). The previous handoff is preserved verbatim in that session
> record._
>
> ## Completed
>
> - AI continuity system: compact `CLAUDE.md` guides, verbatim topic files, archive, records,
>   session protocol, `scripts/verify-ai-docs.py`.
> - The game runs locally on the PM's machine: v142 build, game data, database, servers, client,
>   double-click launchers in `run/`. The PM logged in as `jomar357` and reported it working.
> - PR #1 merged into `master` (`5f5d006`).
>
> ## Remaining
>
> - No development task is authorised: ask the PM for the next priority.
> - The closing record edits (DECISIONS, STATE, HANDOFF, session record) are uncommitted; ask before
>   committing.
> - Suggestions awaiting a PM decision: rotate the credentials in the tracked `Exes/server.toml` and
>   untrack it; delete the merged branch `local-run-setup`.
>
> ## Watch out for
>
> - Build inside `vcvarsall x86 -vcvars_ver=14.29` with `RUSTUP_TOOLCHAIN=stable-i686-pc-windows-msvc`
>   (see the runbook). Never `cargo clean --release` without `-p`.
> - Do not use jCodeMunch in this repo (PM-015). Do not use the tracked `Exes/server.toml`.
> - Game data and build output are local only (gitignored).
>
> ## Next-session prompt (copy as is)
>
> ```text
> You are continuing work on Rose Next (C:\Users\Jomar\Desktop\Rose\rose-next) under the direction
> of the Project Manager. Read, in order: CLAUDE.md, doc/ai/INDEX.md, doc/ai/STATE.md,
> doc/ai/HANDOFF.md. Reconcile them with the checkout (git status -sb, git rev-parse HEAD,
> git status --porcelain=v1 -uall) and report any mismatch; the last session closed with its
> closing record edits uncommitted on master. Run `python scripts/verify-ai-docs.py --quiet`.
> No development task is authorised: ask the PM for the next priority and whether to commit the
> pending record edits. For running the game, read doc/ai/topics/project/local-setup-runbook.md and
> use the launchers in run/. Do not use jCodeMunch in this repo. Do not commit, push, merge or delete
> anything without the PM's explicit say-so. Open a new session record under doc/ai/sessions/ and
> follow doc/ai/SESSION_PROTOCOL.md.
> ```
