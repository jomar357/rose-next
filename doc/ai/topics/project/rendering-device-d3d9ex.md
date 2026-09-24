# Rendering device (Direct3D 9Ex)

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 149-163 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=149-163 sha256=209f0f71451f2e4c619180eec39ad3426910f5e5a9be5d8ffe30ae53eafd1d29 -->
### Rendering Device (Direct3D 9Ex)
The client runs on a **Direct3D 9Ex** device when available, falling back to plain D3D9. The payoff is that alt-tab, lock, UAC and RDP no longer lose the device — previously each cost a full invalidate → reset → reload-every-texture-from-VFS cycle that also threw on failure.

Consequences worth knowing before touching rendering:
- **`D3DPOOL_MANAGED` is illegal on a 9Ex device** and has been removed from everything we compile. New resources go in `D3DPOOL_DEFAULT` and must survive `invalidate_device_objects()` / `restore_device_objects()`. `D3DPOOL_SYSTEMMEM` is still legal — use it for anything that genuinely needs `LockRect`, since DEFAULT textures cannot be locked.
- A DEFAULT-pool buffer that is locked every frame needs `D3DUSAGE_DYNAMIC` + `D3DLOCK_DISCARD`; a plain DEFAULT buffer locked per-frame stalls the pipeline. Conversely `D3DLOCK_DISCARD` is illegal on a non-dynamic buffer.
- `S_PRESENT_OCCLUDED` and `S_PRESENT_MODE_CHANGED` are **success** codes — a plain `FAILED()` test misses them. Occlusion must throttle, never reset. An occlusion log line is *not* a black screen: a skipped present leaves the previous front buffer on screen, so the throttle costs a dropped frame, never a blank one.
- Under 9Ex `TestCooperativeLevel()` is deprecated and always returns `S_OK`; use `CheckDeviceState()`, and only after a present returns something unusual.
- **Fullscreen is borderless by default** — a windowed device covering the monitor, so nothing ever hands display-mode ownership back and forth. The legacy exclusive device is `[VIDEO] EXCLUSIVE_FULLSCREEN=1` (or `ROSE_EXCLUSIVE_FULLSCREEN=1`); it produced brief full-screen black flashes mid-game that borderless removes by construction. In borderless the backbuffer is **always** the monitor size — anything else is stretched by D3D and drifts UI hit-testing.
- **`_fill_fullscreen_mode_ex()`'s `D3DDISPLAYMODEEX` must mirror the present parameters exactly** (`Format` = `BackBufferFormat` even though that is `A8R8G8B8`, `RefreshRate` = `FullScreen_RefreshRateInHz` even when that is 0). The runtime cross-checks them and returns `D3DERR_INVALIDCALL` — and the fallback ladder then hands back a working Ex device via plain `CreateDevice`, so **only the log tells you**. Read `error.txt` after any device-creation change.
- Force the legacy path for A/B testing with `[VIDEO] D3D9EX=0` in `rose-next.ini` or `ROSE_NO_D3D9EX=1` in the environment — and confirm via the log, since a toggle that silently does nothing gives a false negative.
- The **depth-stencil format is negotiated at device creation**, not fixed — see "Depth Buffer Precision" below before touching format selection in `initialize()`.

`[VIDEO] VSYNC=0` uncaps the framerate — but vsync is **not** the only limiter, contrary to what this line used to say. `zz_system::sleep()`, reached from `swapBuffers()`, enforces `max_framerate` with `::Sleep()`. It does not bind in practice only because `data/SCRIPTS/INIT.LUA:39` calls `setFramerateRange(15, 1000)`; the `src/` default is **60**, so grepping `src/` alone gives the wrong answer — the same trap as `setMipmapLevel` and `setLazyBufferSize`. Note `sleep()` also runs `manager_update()`, the resource amortiser, so the client's `present` phase has never been GPU wait alone: measured, real Present is 0.2–0.4 ms and the rest was the amortiser plus a per-frame yield. Full design notes, the D3DX9 upgrade rationale, the rejected `FLIPEX` work and the remaining gaps are in [doc/d3d9ex-migration.md](../../../d3d9ex-migration.md).

<!-- verbatim:end -->

## Updates

- **2026-09-24 (migration, status: conflict, unverified).** The VSYNC paragraph above contradicts the client text now in [client/frame-timing-device-screen-modes.md](../client/frame-timing-device-screen-modes.md) ("Vsync is the only frame cap"). This paragraph is the later, self-described correction. C-001 in [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md).
