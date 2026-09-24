# Summon info panel

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 422-431 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=422-431 sha256=8a6e12cc5d3f491cb553c57282670ff74f47514a0385d3240ef7ac22333ae0f5 -->
## Summon Info Panel

`CSummonInfoPanel` (`interface/csummoninfopanel.cpp/h`, owned by `CUIMediator` as `m_SummonPanel`) is a draggable overlay listing the player's active summons (name, ATK/DEF/LV/RES, HP bar). It is **not** a tgamectrl dialog — it draws directly with `g_DrawImpl.DrawFit` (`ID_BLACK_PANEL` background, `UI00_GUAGE_*` HP bar) + `drawFont`, like the monster-HP namebox feature, so it needs **no XML resource**. Drawn inside the HUD sprite block via `CUIMediator::Draw()`.

- Visible only when `g_pAVATAR->GetCur_SummonCNT() > 0`; one box per summon, stacked vertically. Summon object indices come from `CObjUSER::GetSummonedMobList()` (the same `m_SummonedMobList` the summon counter/CTRL-click control use); each index resolves to a live `CObjMOB` via `g_pObjMGR->Get_ClientCharOBJ`.
- **Summon gauge lifecycle** (`m_SummonedMobList` / `m_iSummonMobCapacity`, keyed by *server* object index): entries are added on the summon-spawn `gsv_MOB_CHAR` packet and removed by `SubSummonedMob()` in **four** receive paths — lethal FlatBuffer `CombatSwing` (`recv_combat_swing`) and `DamageEvent` (`recv_damage_event`) in `cnetwork.cpp`, plus legacy `GSV_DAMAGE` and `GSV_DAMAGE_OF_SKILL` with `DMG_BIT_DEAD` (`recvpacket.cpp`). All four decrement at packet receive, before any defender/visibility early-outs, so the gauge updates even when the summon object doesn't exist client-side; `SubSummonedMob` on an unknown index is a no-op, which also makes duplicate death packets safe. Do not move the decrement to `Dead()`/presentation time — a queued death presentation can be dropped, and the gauge gates re-summoning (`skill.cpp` capacity check), so a leaked entry eventually blocks the summon skill. The server mirrors lethal packets to out-of-range owners (see gameserver `CLAUDE.md`).
- **Stats are the server-scaled values, not the raw NPC table.** A summon's real combat power is scaled at creation by summon-skill level + owner level (server `CObjSUMMON::SetCallerOBJ`, `cobjnpc.cpp`). The client replicates those exact formulas once at summon time in `recvpacket.cpp` (right next to the pre-existing MaxHP scaling) and stores ATK/DEF/RES + the summon level (= owner level at summon) into `SummonMobInfo` via `SetSummonedMobStats`. **If you change the scaling formula on the server, change it here too** — the two are intentionally duplicated. HP/MaxHP are read live from the object.
- **A summon's max HP comes from the packet, for every viewer (2026-09-21).** `gsv_MOB_CHAR`'s tail is `owner idx, [summon skill idx, int max HP]` (server `CObjCHAR::Add_ADJ_STATUS`; the int is `memcpy`'d, the tail is short-aligned). `CObjMOB::Create` seeds every mob with the wild-monster `NPC_HP * NPC_LEVEL`, and the scaled override used to live inside the `pChar->IsA(OBJ_USER)` block with `g_pAVATAR->Get_LEVEL()` — so only the *owner's* client corrected it and any other player targeting the summon read e.g. `2895/141752`. It cannot be rebuilt on an observer: the formula needs the owner's level *at summon time*, and the owner may not be in the observer's object list at all. The local formula survives only as a fallback for a packet without the field (owner block, and an owner-level approximation for observers). Client and server ship together (tail grew 4 bytes); a mixed pair degrades to the old behaviour, it does not crash.
- **Drag** is handled in `CGameStateMain::ProcWndMsgInstant` (the synchronous consume path): `WM_LBUTTONDOWN` over the stack starts a drag and returns 1 so the click never reaches avatar-move / dialog hit-testing; `WM_MOUSEMOVE + MK_LBUTTON` while dragging moves the panel; `WM_LBUTTONUP` ends it. Position is in-memory only (resets each launch, default right side below the minimap) — not persisted to INI.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
