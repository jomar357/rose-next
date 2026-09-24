# Archive 2026-09-24: original AI instruction files

These files hold the **original bytes** of the instruction files that were replaced by compact
guides on 2026-09-24. They are named `*.txt` so that no AI tool loads them as instructions.

**Immutable.** Never edit, rename, re-encode or delete these files. `.gitattributes` in this
folder turns off line-ending conversion. `scripts/verify-ai-docs.py` checks each one against the
SHA-256 below and against the git blob at the capture revision.

- Capture date: 2026-09-24
- Revision: `84f6206723fb4a8abf27df8a71eeb458fd734553` (`master`, clean working tree, even with `origin/master` at capture)
- Machine-readable: [manifest.json](manifest.json)
- Where each line went: [../../migration/2026-09-24-mapping.md](../../migration/2026-09-24-mapping.md)

| Archive file | Original path | Bytes | Lines | Git blob | SHA-256 |
|---|---|---|---|---|---|
| [root--CLAUDE.md.txt](root--CLAUDE.md.txt) | `CLAUDE.md` | 99,586 | 856 | `8ca0d3f9` | `dc9da16dd98cef7e83473efe84ea10752c341200d0e0aee048bfd3c3bc8a257e` |
| [src--client--CLAUDE.md.txt](src--client--CLAUDE.md.txt) | `src/client/CLAUDE.md` | 176,345 | 745 | `3c00f745` | `432d7127a2bcbe41ba9ce7259313bfc378acac1107bc2d3bdff13a8b58d16bad` |
| [src--sho_gameserver--CLAUDE.md.txt](src--sho_gameserver--CLAUDE.md.txt) | `src/sho_gameserver/CLAUDE.md` | 23,060 | 207 | `e270a31b` | `c3ae3915b4a467941f7c74e866e48a9ad43b99d9c748a136c75392a739c07ec4` |
| [xadet--rose-online-map-editor--CLAUDE.md.txt](xadet--rose-online-map-editor--CLAUDE.md.txt) | `xadet/rose-online-map-editor/CLAUDE.md` | 19,140 | 305 | `e531c00e` | `001390974c19f9f163b5b5db02c55492815e1d540e42f40e071fd4010f62aeb1` |
| [root--AGENTS.md.txt](root--AGENTS.md.txt) | `AGENTS.md` | 663 | 13 | `7cf06a6c` | `1d1358bfc48da8a2a9d06d89665516a2bb2466c8bc8f3b87daa3c3381d074fc0` |

Not archived because they were not changed: `context.md`, `README.md`, everything under `doc/`
other than `doc/ai/`, tool READMEs and progress logs. They remain the live copies.
