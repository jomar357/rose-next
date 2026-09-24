# Game server summon control

> **Provenance:** moved verbatim on 2026-09-24 from `src/sho_gameserver/CLAUDE.md` lines 126-141 (revision `84f6206`).
> Original bytes: [`src--sho_gameserver--CLAUDE.md.txt`](../../archive/2026-09-24/src--sho_gameserver--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/sho_gameserver/CLAUDE.md lines=126-141 sha256=5c6c5a90a4883047334c93a14896121934443336b0cfe8d5093bca9e60ad86be -->
## Summon Control (CTRL+Click)

Players can directly command their summons (phantom swords, companions) with CTRL+click. The client sends `CLI_SUMMON_CONTROL` (`net_prototype.h`, id `0x0776` — distinct from the legacy unused `CLI_SUMMON_CMD` stance packet) carrying a command byte (`SUMMON_CTRL_MOVE` / `SUMMON_CTRL_ATTACK`), a target object index, and a destination.

- `classUSER::Recv_cli_SUMMON_CONTROL` validates (has summons, not stunned, attack target is a live hostile mob in-zone, move within 150 m) and calls `CZoneTHREAD::CommandSummons_MoveTo` / `CommandSummons_Attack`.
- Those helpers iterate `m_ObjLIST` and match summons via `GetControllableSummon` (object is `OBJ_MOB`, alive, `GetCallerUsrIDX() == owner index`, **and** `GetCallerHASH()` matches — caller index alone is reused). There is no owner→summon list; iteration is the source of truth.
- The order applies to **all** of the player's summons at once. Stationary summons (Bonfire, walk+run speed 0) are excluded from move orders.

### CObjSUMMON manual-order window

`CObjSUMMON` has a manual-order window (`m_dwManualOrderUntil`, `MANUAL_ORDER_MS` = 5000, `SetManualOrder()` / `IsManualOrderActive()`). While active it suppresses **both** the continuous follow-the-owner re-plan in `CObjSUMMON::Proc()` **and** AIP auto-aggro (via the `Do_StopAI` override) so the player's explicit order is honored, then the summon resumes normal follow behavior. `SetManualOrder()` is called unconditionally on every order (not gated on the move succeeding) so the window is always set; a re-order refreshes it. The follow loop itself (toward the always-walkable owner) still uses `SetCMD_MOVE2D`.

### PlayerOrderMoveTo (do NOT use SetCMD_MOVE2D for player clicks)

Move orders go through `CObjSUMMON::PlayerOrderMoveTo`, **not** `SetCMD_MOVE2D`. `CObjCHAR::SetCMD_MOVE2D` rejects destinations where `GetZONE()->IsMovablePOS()` is false (non-walkable cells) and silently keeps the old command — which made CTRL+click move orders "randomly" ignored depending on the exact terrain cell clicked. The avatar's own click-to-move has no such gate (it relies on client CANTMOVE collision feedback). `PlayerOrderMoveTo` replicates SetCMD_MOVE2D minus the IsMovablePOS check (calls `CObjAI::SetCMD_MOVE2D` + the now-`protected` `Send_gsv_MOVE`), so player orders are tolerant of non-walkable clicks like the avatar. Attack orders use the AI's `SetCMD_RUNnATTACK` (chase + attack). Keep the strict IsMovablePOS gate only for internal AI pathing.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
