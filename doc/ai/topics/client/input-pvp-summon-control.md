# Input dispatch, PVP enemy verdict, summon control

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 398-421 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=398-421 sha256=49ac63d85a9aa1a787839caf158b9b5632cc0316b5c3c75ae1a4273829616e26 -->
## Input Dispatch

Windows messages arrive in `CGame::AddWndMsgQ` (called from `WndProc`). For each message the active state's `ProcWndMsgInstant` runs **synchronously on the Win32 thread**; if it returns non-zero the message is consumed, otherwise it is queued in `m_WndMsgQ` and drained next frame by `CGame::ProcInput` → `ProcMouseInput` / `ProcKeyboardInput`.

The queued path for mouse messages calls `g_itMGR.MsgProc` → `CITStateNormal::Process`, which iterates **every open dialog** (`m_Dlgs`) and **every icon** (`m_Icons`) in reverse, calling `pDlg->Process(uiMsg, wParam, lParam)` on each for hit-testing. Cost is O(n_dialogs × n_controls) per drained message.

**Right-click camera drag**: `CGameStateMain::ProcWndMsgInstant` handles `WM_MOUSEMOVE` with `MK_RBUTTON` by calling `Add_YAW` / `Add_PITCH` (cheap, dirty-flag only) and **returning 1 to consume the message**. Windows delivers mousemove at 100–500 Hz during active drag; without the early return, each one would queue and pay the full dialog hit-test walk on the next frame, producing micro-stutters. No UI reacts to mousemove while RMB is held for camera control, so the consumption is safe. `m_ptCurrMouse` is updated in `AddWndMsgQ` **before** `ProcWndMsgInstant`, so global cursor tracking isn't affected.

Left-click, hover, and non-drag cursor motion all still flow through the queued path (UI must see them). Only `WM_MOUSEMOVE + MK_RBUTTON` is consumed early.

## PVP: You Are Never Your Own Enemy

`CUserInputState::IsEnemy` (`jcommandstate.cpp`) is the client's single hostile/friendly verdict for players (attack click, cursor, `CheckCastingTargetFilter`). It switches on the target's `pvp_state`: in an `AllExceptParty` zone (Junon Cartel, Crusader Training Camp, Lion's Plains, Union War, Desert of the Dead) it answers "enemy" for anyone not in the party list, and in an `All` zone for everyone — including the avatar itself, which the party list never contains. So Cure (type 11, target filter 3 `FRIEND_ALL`) on yourself printed "Invalid target" in those zones while Healing (type 10, a self-type skill that skips the filter) worked (alpha test #2, 2026-09-22). `IsEnemy` now returns false for `g_pAVATAR` before the switch. The server's `CObjAVT::Is_ALLIED` already had the `pDestCHAR == this` case.

## Summon Control (CTRL+Click)

CTRL+click lets a player command their summons (move / attack) instead of moving the avatar. The logic is in `CUserInputState::TrySummonControlClick` (`jcommandstate.cpp`), called at the top of **both** `ClickObject` and `DBClickObject` for the active `CSevenHeartUserInput` (and `CDefaultUserInput`):

- It is consumed (returns true, avatar does **not** move) only when the player owns a summon (`GetCur_SummonCNT() > 0`), is not riding, and CTRL is held (`wParam & MK_CONTROL`). Otherwise it returns false and legacy CTRL+click behavior (HP peek, drop-item info, item pickup, NPC/player clicks) is unchanged.
- CTRL+click on terrain (`OBJ_GROUND`/`OBJ_CNST`) → `Send_cli_SUMMON_CONTROL_MOVE`. CTRL+click on a hostile `OBJ_MOB` → `Send_cli_SUMMON_CONTROL_ATTACK`. Other object types are **not** consumed (return false) so their existing CTRL+click behavior is preserved.
- **Both** click paths must be hooked: rapid repositioning (RTS-style) is delivered by Windows as `WM_LBUTTONDBLCLK` → `DBClickObject`. Hooking only `ClickObject` makes every other rapid click move the avatar instead of the summon.

Sends go through `CSendPACKET::Send_cli_SUMMON_CONTROL_MOVE` / `_ATTACK` (`network/sendpacket.cpp`) using the shared `CLI_SUMMON_CONTROL` packet. The server is authoritative for which summons obey and how; see the gameserver `CLAUDE.md` "Summon Control" section (including the `IsMovablePOS` gotcha that made move orders look random).

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
