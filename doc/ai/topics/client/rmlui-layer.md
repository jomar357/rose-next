# RmlUi layer (client implementation)

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 502-554 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=502-554 sha256=990ea685d18f9099eb24e8911453e4e40905be4964c47ab5d9c6d82aa12329a2 -->
## RmlUi UI Layer (`rmlui/`)

CSS-authored panels, off by default (`[VIDEO] RMLUI=1` or `ROSE_RMLUI=1`). `/dps` then opens the
RmlUi damage meter instead of `CDamageMeterPanel`; both consume the same `CDamageMeter` snapshot, so
the data core is untouched and the two views A/B in place. Design notes and phase history:
[doc/rmlui-evaluation.md](../../../rmlui-evaluation.md).

| File | Role |
|---|---|
| `RoseRmlRenderer.*` | `Rml::RenderInterface` on D3D9(Ex) — synchronous, no batching |
| `RoseRmlSystem.*` | clock, logging, clipboard, `JoinPath` |
| `RoseRmlUi.*` | context ownership, device lifetime, input bridge |
| `RoseRmlDamageMeter.*` | the meter view + data-model bindings |

Hooks: `CGame::GameLoop` (init/shutdown), `CGameState::render_dev_ui` (the shared in-scene overlay
point every state already calls — must be **outside** `beginSprite()/endSprite()`, the state guard
assumes it owns the device), `CGameState::ProcWndMsgInstant` (input, first refusal),
`CApplication::ApplyWindowedClientResize` + `ResizeWindowByClientSize` (device rebuild), and an
`RmlUi: draws=` debug HUD line.

**Device lifetime — the trap.** `resetScreen()` does **not** `Reset()` the device: `cleanup()` calls
`SAFE_RELEASE(d3d_device)` and `initialize()` creates a *new* one, so a cached `IDirect3DDevice9*`
goes stale. There are six `resetScreen()` call sites (four in `CApplication`, two in
`coptiondlg.cpp`) and hooking them individually was got wrong twice. Correctness therefore rests on
`Update()` comparing the engine's current device against ours each frame and rebuilding on change;
the explicit hooks are only an optimisation. Both paths log. Note RmlUi does **not** re-request
compiled geometry or shaders after a reset, so the renderer keeps CPU-side copies of vertex/index
data and gradient ramps and refills them itself; `Rml::ReleaseTextures()` covers only textures.

**Input arbitration — the other trap.** Consumption is decided by **panel geometry**, never by
`Context::GetHoverElement()`. Each document's `<body>` must span the viewport (or `ElementHandle`
cannot drag a panel — it clamps to the move target's containing block), which makes the hover element
a screen-wide hit target. Every top-level child of every visible document counts as solid UI;
everything else is transparent to the game. A left-press on a panel latches a dragging flag until
release so a drag keeps tracking off-panel, and `WM_MOUSEWHEEL` carries **screen** coordinates unlike
the other mouse messages, so it needs `ScreenToClient` before hit-testing.

**Rendering notes.** RmlUi 6 vertices are **premultiplied alpha** (blend is `ONE`/`INVSRCALPHA`) and
RGBA-ordered where D3D9 wants BGRA. `D3DPOOL_DEFAULT` textures cannot be locked, so both texture
paths go via a `SYSTEMMEM` staging texture + `UpdateTexture`. Linear gradients are implemented
without a shader: the gradient decorator sets each vertex's `tex_coord` to its element-local pixel
position, so a `D3DTTFF_COUNT2` texture-coordinate transform onto a baked 256×1 ramp reproduces one
exactly. Radial/conic gradients, blurred `box-shadow`, `filter` and `transform` are unimplemented and
warn or no-op; `border-radius` needs no renderer support (RmlUi tessellates it).

**Assets.** `.rml`/`.rcss` load loose via `fopen` relative to the launch dir — the VFS bake never
covers them, same as `UI_strID.ID`. That is deliberate: players edit them. Texture loading resolves
**disk first, VFS second** so a player's file beats shipped art; `RoseRmlSystem::JoinPath` passes
game-root paths (`3DDATA/...`) through untouched instead of resolving them against the document
folder. Keep the RmlUi debugger visible while authoring — RCSS errors are otherwise completely
silent, and a discarded declaration (e.g. `transition: … linear`, which is invalid; RmlUi has only
`linear-in`/`-out`/`-in-out`) looks exactly like one that works.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
