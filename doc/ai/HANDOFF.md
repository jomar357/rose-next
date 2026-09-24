# Latest handoff

_From session [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md), written 2026-09-24 at an
interim checkpoint. The session is **not closed**: the PM has not used the closing phrase. Replace
this file at closing, after preserving its substance in the session record._

## Completed

- The four oversized `CLAUDE.md` guides (≈318 KB) now live verbatim in 69 indexed topic files under
  `doc/ai/topics/`; the guides themselves are compact (root 118 lines). Originals archived with
  SHA-256 in `doc/ai/archive/2026-09-24/`.
- `AGENTS.md` is a portable entry point; the unreachable external memory it used to name is
  recorded as a gap.
- Continuity records and the session protocol exist, including the closing rule for the phrase
  "Our work here is done".
- `python scripts/verify-ai-docs.py` rebuilds every original byte-for-byte and checks links.

## Remaining / waiting on the PM

- The next development priority (Q-001).
- Whether to push `master` (the documentation commit is local only; PM-010 authorised the commit, not a push).
- Where game data, reference dumps and a deployable game folder come from on this machine (Q-002).
- Optional: a copy of the previous maintainer's memory directory (Q-003).

## Watch out for

- Topic text is inherited and unverified; three conflicts are already logged (C-001..C-003 in
  [OPEN_QUESTIONS](OPEN_QUESTIONS.md)).
- Never edit inside `verbatim` markers; add dated *Updates* instead.
- jCodeMunch has not indexed this repo yet; index before code exploration.

## Next-session prompt (copy as is)

```text
You are continuing work on Rose Next (C:\Users\Jomar\Desktop\Rose\rose-next) under the direction
of the Project Manager. Read, in order: CLAUDE.md, doc/ai/INDEX.md, doc/ai/STATE.md,
doc/ai/HANDOFF.md. Then reconcile them with the checkout (git status -sb, git rev-parse HEAD,
git status --porcelain=v1 -uall) and report any mismatch. If STATE.md lists an open session that
was never closed, treat its work as interrupted and recover from its session record plus the diff.
Run `python scripts/verify-ai-docs.py --quiet` and report the result. Do not start development
work: no task is authorised yet. Ask the PM for the next development priority and whether the
local documentation commit on master should be pushed. Open a new session record under
doc/ai/sessions/ and follow doc/ai/SESSION_PROTOCOL.md.
```
