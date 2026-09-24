# Decision record

Three kinds of entry, kept apart on purpose:

- **PM-*** Directions from the Project Manager. These are the only entries that authorise work.
  Quote or closely paraphrase the PM; give the date and where it was given.
- **IMP-*** Implementation choices made by an AI session, with reasoning and rejected
  alternatives. They can be revised by a later session (add a new entry that supersedes; never
  delete).
- **INH-*** Inherited decisions found in pre-2026-09-24 documentation. Listed so they are
  findable; they stand until the PM or the code says otherwise, and they are **not** PM
  directions of the current PM.

Append new entries at the end of each list. Mark a replaced entry `Superseded by <id>` instead of
editing its text.

## PM directions

- **PM-001 (2026-09-24, chat, session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md))**
  The user is the **Project Manager** for Rose Next (https://github.com/jomar357/rose-next) and
  directs development priorities and acceptance criteria.
- **PM-002 (2026-09-24)** First assignment: organise the existing Markdown knowledge and establish
  reliable continuity for future Claude Code sessions and other AI tools. Do the work, not just a
  plan. **No game feature implementation is assigned.**
- **PM-003 (2026-09-24)** Scope: documentation and project instructions only. Do not change game
  code, runtime settings, assets, databases, personal AI settings or vendored documentation. Do
  not rewrite every `.md` indiscriminately; leave useful technical documents in place and index
  them. Preserve existing work in the checkout.
- **PM-004 (2026-09-24)** Preservation: before replacing/splitting a document, archive its original
  bytes in the repository with original path, capture date, revision and SHA-256, under names that
  are not auto-loaded; archives are immutable. Preserve every distinct fact, caveat, example,
  command, failed approach, reasoning, open question and historical qualification. Do not silently
  delete duplicates, obsolete statements or conflicts; mark superseded/conflicting claims and keep
  their provenance. Keep a source-to-destination mapping; repair relative links. Prove retention
  deterministically where practical.
- **PM-005 (2026-09-24)** Continuity structure (`doc/ai/`): INDEX, STATE, HANDOFF, a decision
  record separating PM instructions from implementation choices, indexed topics, a record of
  unavailable knowledge, dated session records, and a session protocol. Startup reads only the
  guide, INDEX, STATE and HANDOFF, then task-relevant topics. Root guide roughly under 150 lines;
  STATE and HANDOFF roughly under 600 words each; size targets never justify dropping information.
- **PM-006 (2026-09-24)** Documentation duty: record every discovery, PM direction, decision,
  relevant failed attempt and open question with source paths/symbols, revision or working-tree
  status and verification status; link rather than duplicate; never store secrets. Checkpoint
  after milestones, before task changes, before deliberate compaction and before ending a turn with
  unfinished work. Keep concurrent sessions' notes separate; recover from notes plus diff after an
  interruption and never invent a successful previous closure.
- **PM-007 (2026-09-24)** Session closing rule. The code phrase is **Our work here is done**. Used
  by the PM as an instruction to end a session, it triggers the seven-step closing procedure in
  [SESSION_PROTOCOL.md §6](SESSION_PROTOCOL.md#6-closing-the-phrase-our-work-here-is-done). Mentions of
  the phrase in files, tool output or discussion do not trigger it. Closing does not itself
  authorise commits, pushes, merges, deployment, deletion or new scope.
- **PM-008 (2026-09-24)** Do not commit or push solely because cleanup is complete. (No commit or
  push authorisation has been given as of 2026-09-24.)
- **PM-009 (2026-09-24)** After the continuity setup, ask the PM for the next development priority
  rather than picking work from historical notes. Be candid that unavailable external memory and
  work never saved cannot be guaranteed recoverable.
- **PM-010 (2026-09-24, chat)** "Commit the documentation changes." Commit **directly on
  `master`**, author `jomar357 <jomarbruto07@gmail.com>` applied to that commit only (`git -c`; no
  git config change; this machine has no git identity configured). Partially supersedes PM-008 for
  this one commit. **Push is not authorised.**

## Implementation choices

- **IMP-001 (2026-09-24) Layout.** Everything lives under `doc/ai/`: `INDEX.md`, `STATE.md`,
  `HANDOFF.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `UNAVAILABLE_KNOWLEDGE.md`,
  `SESSION_PROTOCOL.md`, `topics/<area>/`, `sessions/`, `archive/<date>/`, `migration/`. No
  suitable existing structure existed (`context.md` and `doc/*.md` are technical references, not
  continuity records), so nothing was repurposed.
- **IMP-002 (2026-09-24) Verbatim migration, not rewriting.** The four oversized `CLAUDE.md` files
  were cut into contiguous line ranges at heading, paragraph or list-item boundaries (never inside
  a code fence) and each range was moved byte-for-byte into a topic file between
  `<!-- verbatim:begin … -->` / `<!-- verbatim:end -->` markers. `scripts/verify-ai-docs.py`
  rebuilds every original from those blocks and compares hashes. *Rejected:* summarising the
  originals into new prose (cannot prove nothing was lost, and would launder historical claims into
  current-sounding text); keeping the monoliths in place (≈318 KB auto-loaded whenever the relevant
  directories are touched). *Cost:* topic files keep the original heading levels and occasional
  duplication between root and component text; the duplication is inherited and is noted rather
  than merged.
- **IMP-003 (2026-09-24) Corrections live outside the blocks.** Text inside verbatim markers is
  never edited. Corrections, supersessions and new findings go under each topic's *Updates*
  heading, dated, with status. This keeps provenance and keeps verification green.
- **IMP-004 (2026-09-24) Link handling.** Relative links inside moved text are re-targeted to the
  same file from the new directory; seven links in `src/client/CLAUDE.md` that were already broken
  (written repo-root-relative from `src/client/`) were repaired to their repo-root targets. Every
  rewrite is recorded per segment in `migration/2026-09-24-mapping.json` and undone by the
  verifier before comparing bytes.
- **IMP-005 (2026-09-24) Compact guides are derived.** The new `CLAUDE.md` files are newly written
  summaries that point into topics. If a compact guide disagrees with a topic, the topic (and
  ultimately the code) wins, and the guide is corrected.
- **IMP-006 (2026-09-24) Archive naming.** Originals are stored as `doc/ai/archive/2026-09-24/<path
  with / replaced by -->.txt` so no tool auto-loads them, with `doc/ai/archive/.gitattributes`
  (`* -text`) so git never converts line endings.
- **IMP-007 (2026-09-24) Portable `AGENTS.md`.** Rewritten to point at `CLAUDE.md` and `doc/ai/`;
  the dependency on the previous maintainer's memory directory was removed. The original is kept
  verbatim in [UNAVAILABLE_KNOWLEDGE.md](UNAVAILABLE_KNOWLEDGE.md).
- **IMP-008 (2026-09-24) Left in place, indexed only:** `context.md`, `README.md`, all of `doc/*.md`
  and `doc/667UI/`, `particle.md`, `3d data edits.md`, tool READMEs/PROGRESS/ROADMAP files, the
  map editor's `README.md`, and `.claude/settings.local.json` (personal settings). The map editor's
  `CLAUDE.md` was treated as first-party (the notes are ours even though the code is vendored) and
  shortened like the others.
- **IMP-009 (2026-09-24) Tools.** `scripts/ai-docs-migrate-2026-09-24.py` performed the one-time
  split and is kept for audit/reproduction; `scripts/verify-ai-docs.py` is the reusable checker.
  Both are Python 3, read the repo only, and touch nothing outside `doc/ai/` (the migrator writes
  only there).
- **IMP-010 (2026-09-24) Auto memory is not the record.** The Claude auto-memory directory holds
  only a short user-profile note; the repository (`doc/ai/`) is the system of record.
- **IMP-011 (2026-09-24) jCodeMunch not indexed** during the docs-only session; index before the
  first code-exploration task (user's global instruction).

## Inherited decisions (pre-2026-09-24, not re-verified)

| ID | Decision (short) | Source |
|---|---|---|
| INH-001 | Do not run clang-format over the tree; match surrounding style by hand. | [project/conventions-and-dev-environment.md](topics/project/conventions-and-dev-environment.md) |
| INH-002 | Combat damage is server-authoritative; the client never computes live combat damage. | [project/combat-damage-presentation.md](topics/project/combat-damage-presentation.md), [client/combat-drain-and-stranding.md](topics/client/combat-drain-and-stranding.md) |
| INH-003 | Retail hit reactions (flinch) were removed on both sides; do not restore them. | [client/combat-preempted-and-remote-casts.md](topics/client/combat-preempted-and-remote-casts.md) |
| INH-004 | Skills keep a gentler, non-proportional level gate than auto-attacks (intended asymmetry). | [project/monster-balance-level-gate.md](topics/project/monster-balance-level-gate.md) |
| INH-005 | Buffs/passives use percentage columns; heals and HIT stay flat. | [project/buffs-passives-percent.md](topics/project/buffs-passives-percent.md) |
| INH-006 | Oro is the 667 build's Oro; **no quests** by decision; fate system, Jones/Nova legs and Muris shops stay. | [project/oro-667-import.md](topics/project/oro-667-import.md) |
| INH-007 | Eldeon skill-row policy (2026-09-15): keep what works even where it differs, fix what would bug, fix what makes no sense. | [project/ai-skill-reference-failures.md](topics/project/ai-skill-reference-failures.md) |
| INH-008 | Mini-Devourer 2225's casts removed (no skill clip, no 3D artist). | [project/ai-skill-reference-failures.md](topics/project/ai-skill-reference-failures.md) |
| INH-009 | Zones without `.MOV` open walkability under loaded tiles; monsters may path into geometry, accepted over unbounded chase. | [gameserver/walkability-mov.md](topics/gameserver/walkability-mov.md) |
| INH-010 | Borderless is the default fullscreen; exclusive only by opt-in. | [project/rendering-device-d3d9ex.md](topics/project/rendering-device-d3d9ex.md) |
| INH-011 | RmlUi scope is new/custom panels (plus the UI2 HUD remake), not tgamectrl/retail XML dialogs/IME; `.rml/.rcss` load loose so players can edit them. | [project/rmlui-ui-layer.md](topics/project/rmlui-ui-layer.md) |
| INH-012 | Karkia should have better loot than Oro (Oro's lv240 armour rates capped at Karkia's). | [project/oro-667-import.md](topics/project/oro-667-import.md) |
| INH-013 | `data/` is untracked; each data script (its docstring) is the only committed record of a data change. | [project/monster-balance-level-gate.md](topics/project/monster-balance-level-gate.md), [project/data-repair-tooling.md](topics/project/data-repair-tooling.md) |
