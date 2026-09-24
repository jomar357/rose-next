# Debugging a client crash or freeze

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 655-664 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=655-664 sha256=b4839fec5ddfef4da8493cbccbd14529ddc518abc9a041aaf3d6110556898e03 -->
### Debugging a Client Crash or Freeze

The client has **no unhandled-exception filter and no minidump writer**, so a crash leaves `error.txt` ending with a clean `log: end.` and nothing else. Use `scripts/debug-client-crash.ps1` (servers up first): it hash-verifies `bin/<config>` PDBs against the deployed binaries, forces windowed mode, restores `rose-next.ini` afterwards, and writes `!analyze -v` + all thread stacks + a full `.dmp` on the access violation.

- cdb has **no working-directory switch** and the debuggee inherits the caller's, so it must launch from the game dir — otherwise the client can't find `rose.vfs` and exits early, looking exactly like "it didn't crash".
- For a **freeze, don't kill the process**: `cdb -pv -p <pid>` attaches non-invasively and works even with cdb already attached.
- The deployed `triggervfs.dll` does not match `bin/release`, so frames through it resolve to nonsense (`VGetVfsNames+0x…`) — disassemble the caller rather than trusting the symbol.
- **`client.log` survives a crash; `error.txt` does not.** The engine log is buffered, so a hard crash loses the whole session and the file still ends at the *previous* run's `log: end.` — which reads as "it never launched". The Rust-side `client.log` flushes per record, so read it first to see how far startup actually got.
- **A crash right after a class-layout change is a stale-build artifact until proven otherwise.** Adding a member to a widely-included header (`zz_node.h` is the base of every engine object) after an *interrupted* build leaves some objects compiled against the old layout. Kill stray `cl`/`link`/`mspdbsrv`, delete `build/<config>`, rebuild serially before debugging anything else.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
