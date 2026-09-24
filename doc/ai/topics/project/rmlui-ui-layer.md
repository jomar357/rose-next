# RmlUi UI layer and UI2 (summary)

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 234-284 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=234-284 sha256=8e3c972b7d4bea15690d49a90d78cbc296bb468d323bfe4107a555c22ed2f239 -->
### RmlUi UI Layer (Client)
New/custom client panels can be authored in **HTML/CSS-like files** (`.rml` / `.rcss`) instead of
hard-coded C++ draw calls, via **RmlUi 6.2 + FreeType 2.13.3** (`thirdparty/RmlUi-6.2`,
`thirdparty/freetype-2.13.3`, built as x86 `/MT` static libs with `RMLUI_CUSTOM_RTTI`). The client
side is `src/client/rmlui/`; assets live loose in `3ddata/rmlui/`.

Off by default — enable with `[VIDEO] RMLUI=1` in `rose-next.ini` or `ROSE_RMLUI=1`. When enabled,
`/dps` opens the RmlUi damage meter instead of the legacy `CDamageMeterPanel`; both read the same
`CDamageMeter` core, so they A/B in place.

**Scope is new/custom panels only.** `tgamectrl`, the 56 retail XML dialogs, chat input and **IME**
are out — RmlUi has no IME composition handling, and the input boundary is the fiddliest part of the
integration. The purpose is quick, player-editable interfaces, **not** reproducing the original
TSI/atlas workflow: `.rml`/`.rcss` are loaded loose (never via the VFS) so players can edit them, and
texture loading resolves **disk first, VFS second** so a player's file overrides shipped art.

**The shared look lives in `3ddata/rmlui/rose-theme.rcss`** (2026-09-23): the 667 build's "glass"
UI re-expressed as gradients — palette sampled from `GLASSUI_*.DDS`, a colour-neutral `ui-gloss`
`@decorator` laid over `background-color` so one definition makes a glass bar of any colour, and
`ui-window` / `ui-titlebar` / `ui-well` / `ui-btn` / `ui-gauge` component classes. A panel links the
theme first and keeps its own `.rcss` to layout only; the damage meter is the reference. RCSS has no
`var()`, so the palette is a comment block, not tokens. `/uireload` re-reads every stylesheet in
game (styles only — markup still needs a restart). Each gradient is one draw call and the backend
does not batch; fine for a few panels, revisit before moving the whole HUD over.

**UI2 is the RmlUi remake of the retail HUD, converted one piece at a time** (2026-09-23). The
player picks classic or UI2 with `[VIDEO] UI2=1` (implies RmlUi) or the `/ui2` chat command, which
switches live and saves the choice. `src/client/rmlui/RoseUi2.cpp` holds the whole "converted"
switch: `kReplacedDialogs` (legacy `DLG_TYPE_*` hidden from the outside every frame in
`IT_MGR::Update`, because game code re-shows dialogs freely — no legacy class is edited) and
`kReplacedPieces` (HUD draws that are not dialogs, e.g. `CEndurancePack::Draw`, gated at their
call site). Converted so far: the status panel (`DLG_TYPE_INFO` → `RoseRmlStatusPanel`, 667
compact layout) and the buff strip (`PIECE_BUFF_BAR` → `RoseRmlBuffBar`: buffs, summon/fuel
gauges, worn gear). Shared helpers: `RoseRmlLayout` (drag position saved in `[UI_LAYOUT]`,
clamped on screen) and `RoseRmlIcons` (a legacy TSI sprite → `<img src rect>`, loaded through the
VFS — no atlas re-cutting). Things that will bite:

- **RmlUi fires `click` after a drag and has no drag threshold**, so a panel that is both a
  handle and a button must compare press/release positions (the status panel uses 4 px).
- A converted panel must reproduce **every** job of the legacy piece or be deliberately
  documented as dropped: `CEndurancePack::Draw` also drew the summon/fuel gauges and the worn
  gear, not just buffs. The status panel dropped the weapon/ammo slot and two dead buttons.
- The drag-and-drop panels (quickbar, inventory) need a bridge first: `CDragNDropMgr` resolves
  drop targets by legacy dialog type, so an RmlUi panel is invisible to it.

Linear gradients are implemented in the D3D9 backend without a shader, and `border-radius` needs no
renderer support, so skins need no image files at all. Radial/conic gradients, blurred `box-shadow`,
`filter` and `transform` are **not** implemented and will warn or do nothing. Full design notes,
phase history, the authoring palette and the traps are in
[doc/rmlui-evaluation.md](../../../rmlui-evaluation.md); client specifics are in the client `CLAUDE.md`.

<!-- verbatim:end -->

## Updates

- **2026-09-24 (migration, status: open).** The "Scope is new/custom panels only" sentence predates or sits uneasily with UI2 (the RmlUi remake of the retail HUD, 2026-09-23) described below it. Scope question C-003 in [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md).
