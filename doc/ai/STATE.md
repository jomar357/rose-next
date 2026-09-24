# Current state

_Last updated: 2026-09-24 by session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md)._

## Objective

Continuity setup (PM-002): organise inherited Markdown knowledge into `doc/ai/` and establish the
startup / checkpoint / closing protocol. **Complete, awaiting PM review.** No development work is
authorised yet.

## Approved scope

- Documentation and project instructions only (PM-003). No game code, runtime settings, assets,
  databases, personal AI settings or vendored docs.
- Commit of the documentation changes on `master` authorised and done (PM-010). **Push not authorised.**
- Next development priority: **not yet given**; ask the PM (PM-009, Q-001).

## Progress

- Done: archives with hashes; 69 verbatim topic files + mapping; compact `CLAUDE.md` ×4 and portable
  `AGENTS.md`; INDEX, SESSION_PROTOCOL, DECISIONS, OPEN_QUESTIONS, UNAVAILABLE_KNOWLEDGE, this file,
  HANDOFF, session record; `scripts/ai-docs-migrate-2026-09-24.py` and `scripts/verify-ai-docs.py`.
- Verified: `python scripts/verify-ai-docs.py` passes (all five originals rebuilt byte-for-byte,
  archives equal git blobs at `84f6206`, all relative links resolve).

## Blockers and constraints

- This checkout has no game data, binaries, `build/` backups or reference dumps
  ([UNAVAILABLE_KNOWLEDGE](UNAVAILABLE_KNOWLEDGE.md) U3-U5), so builds, data scripts and in-game
  checks cannot run here (Q-002).
- The previous maintainer's external memory is unavailable (U1).

## Next action

Ask the PM for the next development priority, and whether to push `master` to `origin`.

## Active session(s)

- [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md): open, not closed.

## Repository

- `C:\Users\Jomar\Desktop\Rose\rose-next`, branch `master`.
- This session's documentation changes are committed on `master` as one commit on top of `84f6206`,
  titled "Docs: AI continuity system; split oversized CLAUDE.md guides into doc/ai topics"
  (find it with `git log -1 --format=%H -- doc/ai/STATE.md`). **Not pushed**: local `master` is
  ahead of `origin/master` until the PM authorises a push.
- No unrelated pre-existing changes (tree was clean at start).
