# Shared data types and item encoding

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 674-683 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=674-683 sha256=92609274b4792003536f7aa763fbef8f99e74d551e87230cca1d608a829025b3 -->
### Shared Data Types
`src/common/shared/` contains game data structures (items, quests, inventory, economy) used by both client and server. Changes here affect both sides.

### Item Encoding And Package Items
Item headers are shared wire data between client and server. `tagBaseITEM` uses a 5-bit item type plus an 11-bit item number so item IDs above 1023 (for example use-item boxes `10:1060`-`10:1062`) round-trip correctly. The created flag is server-only state on `tagITEM`; do not put it back into the packed 16-bit header or the client will decode high IDs as wrapped lower IDs (for example `10:1060` becoming `10:36`).

When creating items from explicit type/id pairs, use the type/id initializer instead of the legacy `type * 1000 + id` packed integer format. The latter cannot represent item numbers above 999. This matters for `/item`, package rewards, and any code path that spawns or grants modern high-numbered use items.

Use-item class `322` is a package box: the value in `LIST_USEITEM.STB` `ADD_DATA_VALUE` selects a server-side reward package. Unknown package IDs should fail without consuming the box so missing package mappings are visible and recoverable.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
