# Database and networking

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 95-108 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=95-108 sha256=8763cfa5e0202a8e2b75bb255bb4d830fe7aef337ee4eee97dcc3ecc5b281016 -->
## Database

- PostgreSQL 12+
- Connection configured in `server.toml` (see `doc/server.toml.example`)
- Migrations in `database/migrations/` — squash with `scripts/squash-migrations.ps1`
- Passwords: SHA256 + salt (generate with `scripts/generate-password.py`)

## Networking

- Custom packet-based protocol over TCP (IOCP on server side)
- FlatBuffers for some packet types (defined in `src/common-lib/packets/*.fbs`)
- C++ packet definitions in `src/common/include/rose/network/`
- Client has separate socket connections: Login → World → Game server

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
