# Frame timing, device, swap chain and screen modes

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 635-692 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=635-692 sha256=407cb3af87661aa03db85c678fc32b16bf6b2f942355ad7a8b1c555597184a21 -->
## Frame Timing & Timer Precision

`g_GameDATA.GetElapsedFrameTime()` ([game.cpp:172,180](../../../../src/client/game.cpp#L172)) is built on `timeGetTime()`. By default Windows quantizes `timeGetTime()` to the system tick (~15.6 ms), which dominates anything driven by per-frame dt above 60 fps:
- 50 Hz (20 ms real frame): measured dt = 15.6 or 31.2 → ±25% variance around mean.
- 75 Hz (13.3 ms real frame): measured dt = 0 or 15.6 → ±100%+ variance, even when frames are perfectly smooth.

`WinMain` instantiates `HighResTimerScope` ([winmain.cpp:19-30](../../../../src/client/winmain.cpp#L19-L30)) which calls `timeBeginPeriod(1)` for the lifetime of the process and `timeEndPeriod(1)` on exit. Do not add a second `timeBeginPeriod(1)` somewhere else; the WinMain RAII covers everything. Do not remove it — the symptoms it cures (jittery RMB camera, jerky dialog-drag, "stutter that only goes away at 50 Hz") look like a frame-pacing or driver bug but are pure timer-quantization downstream of `GetElapsedFrameTime()`.

**Diagnostic**: if a stutter seems to span unrelated subsystems (camera + UI + animation) and gets worse as monitor refresh rate climbs above the 64 Hz timer rate, suspect timer precision before swap-chain queue depth or driver state. Confirm with `QueryPerformanceCounter` traces of actual frame durations alongside `timeGetTime()` deltas — they should agree.

## Device, Swap Chain & Screen Modes

The client runs on a **Direct3D 9Ex** device when the platform provides one, falling back to plain D3D9 otherwise. Full design notes, rationale and the outstanding gaps live in [doc/d3d9ex-migration.md](../../../d3d9ex-migration.md) — read that before touching device creation, present, or reset. Highlights that bite from the client side:

- `D3DPOOL_MANAGED` is **illegal** on a 9Ex device and is gone from everything we compile. New device resources go in `D3DPOOL_DEFAULT` and must survive the invalidate/restore cycle. `D3DPOOL_SYSTEMMEM` is still legal and is the escape hatch for anything that genuinely needs `LockRect`.
- **`d3dx9_43.dll` is a hard runtime dependency.** D3DX9 is no longer statically linked; the client will not start without the DLL next to it. The old 2005-era static D3DX allocated `ID3DXFont`'s glyph cache in `D3DPOOL_MANAGED`, so on a 9Ex device font creation succeeded but `DrawText` silently drew nothing — no chat, no item names, no player names, while sprites (and therefore the rest of the UI) rendered fine. If text vanishes wholesale, suspect the D3DX runtime before the font code.
- **A/B switch:** `rose-next.ini` → `[VIDEO] D3D9EX=0`, or `ROSE_NO_D3D9EX=1` in the environment, forces the legacy path. Always confirm via the log which path is live — a toggle that silently does nothing produces a false negative (this cost a debugging round).
- **Occlusion skips the frame.** When the window is minimised (or another app owns the monitor fullscreen), `throttle_if_occluded()` makes `::beginScene()` return false, so the render is skipped rather than drawn and discarded — the same contract a lost device already used, which is why no state code changed. Note `background_render` is unaffected: a visible-but-unfocused window is *not* occluded. **If you touch this:** skipping the frame stops `swap_buffers()` running, and that is the only thing that *sets* the occluded flag, so the poll of `CheckDeviceState()` inside `throttle_if_occluded()` is what un-latches it. Drop the poll and the client goes black on the first minimise and never comes back. Skipping waits for 2 consecutive occluded presents — the compositor reports one-frame blips during normal play and dropping a frame for those is a visible hitch buying nothing.
- **An occlusion log line is not a black screen.** A skipped present leaves the previous front buffer on screen, so the throttle costs a dropped frame, never a blank one. If occlusion lines correlate with something visibly black, the display itself is being handed back and forth — look at mode ownership, not at the render loop. Read the `iconic=`/`foreground=`/`elapsed=` fields before theorising: a genuine minimise and a compositor blip produced identical logs before those existed, and the first "reproduction" chased under the new logging turned out to be a real 23-second minimise. Write-up in [doc/d3d9ex-migration.md](../../../d3d9ex-migration.md).

Present parameters ([zz_renderer_d3d.cpp:734-800](../../../../src/engine/src/zz_renderer_d3d.cpp#L734-L800)) intentionally use:
- `BackBufferCount = 1` — minimum flip-queue depth, makes it harder for a missed-vsync frame to lock the pipeline into a half-rate beat.
- `SwapEffect = D3DSWAPEFFECT_DISCARD` (regardless of FSAA) — runtime-managed back buffers instead of `D3DSWAPEFFECT_FLIP`'s driver-managed flip queue, which on AMD could pin the present cadence after a single overrun. **`D3DSWAPEFFECT_FLIPEX` was evaluated and rejected** — it conflicts with MSAA (a live user setting) and with the `Present(..., hwnd, ...)` destination-window override; see the migration doc for why the motivating symptom turned out to be something else entirely.

These were tightened while diagnosing the sticky-stutter bug. Neither change alone fixed the perceived stutter — the timer-precision fix above did — but both narrow the surface for residual driver-side queue pathologies and are kept defensively. Do not raise `BackBufferCount` back to 2 or restore `D3DSWAPEFFECT_FLIP` without a measured reason.

**Vsync is the only frame cap in the engine** — there is no software frame limiter anywhere. The presentation interval is therefore decided **once, after** the fullscreen/windowed split ([zz_renderer_d3d.cpp:798](../../../../src/engine/src/zz_renderer_d3d.cpp#L798)); keep it that way. The windowed branch used to hardcode `D3DPRESENT_INTERVAL_IMMEDIATE` and ignore `state.use_vsync` (which defaults to true), so windowed mode ran unbounded while fullscreen was capped — which also accounted for the long-standing "windowed feels worse than fullscreen" impression. `[VIDEO] VSYNC=0` in `rose-next.ini` uncaps deliberately; the exported `useVSync()` script hook is never called by anything, so the INI is the only knob.

### Three screen modes, and which predicate to use

`e_ScreenMode` (`capplication.h`) is `SCREEN_MODE_WINDOWED` / `_BORDERLESS` / `_EXCLUSIVE`. **Borderless is the default fullscreen** — `[VIDEO] EXCLUSIVE_FULLSCREEN=1` in `rose-next.ini` (or `ROSE_EXCLUSIVE_FULLSCREEN=1`) opts back into the legacy exclusive device, which is also the A/B switch for the black-flash bug it was introduced to fix. `[VIDEO] FULLSCREEN` keeps its old 0/1 meaning and is still what the options dialog persists; `PreferredFullscreenMode()` decides which flavour a "1" means, and `SetFullscreenMode(bool)` survives as a shim over `SetScreenMode()` so the existing call sites (WinMain, Alt+Enter, the options radio) are unchanged.

Picking the wrong predicate is the easy mistake here, because borderless is *fullscreen to the player* and *windowed to D3D*:

| Predicate | True for | Use it for |
|---|---|---|
| `IsFullScreenMode()` | exclusive only | anything feeding `setScreen(..., use_fullscreen)` → `D3DPRESENT_PARAMETERS::Windowed` |
| `IsWindowedFrame()` | windowed only | "can the user drag this frame / does it have a caption" — `WM_SIZE` handling, the FPS title text, the options radio, Alt+Enter |
| `IsBorderless()` | borderless only | the monitor-sized special cases |

`ChangeScreenMode()` and the options dialog must test `IsWindowedFrame()`, not `!IsFullScreenMode()` — the latter is true in borderless, so Alt+Enter would ask for a mode it is already in and rebuild the device for nothing.

**A borderless backbuffer is always the monitor size.** `ResizeWindowByClientSize` overwrites the requested resolution with `GetMonitorRect()` in that branch, so the resolution list is a deliberate no-op there. A `WS_POPUP` window gets exactly the client area it asks for, so a mismatched backbuffer would be stretched by D3D and drift every hit-test — the failure the next section exists to prevent. Borderless is also **not** `WS_EX_TOPMOST`: the exclusive path uses it because an exclusive device owns the display anyway, but on a plain window it only makes the game fight for the top of the z-order.

`ApplyWindowedClientResize` early-outs unless `IsWindowedFrame()`. Borderless has nothing to react to (`WM_SIZE` there would mean a monitor reflow, and each one costs a full device teardown).

### Window sizing must match the backbuffer

In windowed mode the backbuffer is created at the requested client size and D3D **stretches it to whatever the client area actually is**. Mouse input is raw client pixels, so any mismatch silently desyncs hit-testing from what is drawn — the error grows with distance from the origin, which reads as "the checkbox is a bit off" rather than an obvious break.

`CApplication::ResizeWindowByClientSize` therefore clamps against the room actually left for the *client* area (`SM_C*MAXTRACK` minus the decoration size), not against the raw screen size, and re-syncs the renderer if the granted client rect still differs from the request. Windows refuses to size a `WS_THICKFRAME` window past `SM_C*MAXTRACK` unless the app handles `WM_GETMINMAXINFO`, which this client does not — so on a 1920×1080 desktop a requested 1080-tall client area came back as 1061 and everything below the top of the screen drifted.

Frame drags are handled by `CApplication::ApplyWindowedClientResize`, driven from `WM_ENTERSIZEMOVE` / `WM_EXITSIZEMOVE` / `WM_SIZE`. It **accepts** the client area Windows gave us and rebuilds the device to match — deliberately *not* calling `ResizeWindowByClientSize`, which would `MoveWindow` the window the user is dragging. Three guards matter, and each closes a real failure rather than a theoretical one:

- **Deferral.** `WM_SIZE` fires continuously during a drag and every resize is a full device teardown, so the work waits for `WM_EXITSIZEMOVE`. Maximise/restore/programmatic sizes arrive outside a drag and apply immediately; `SIZE_MINIMIZED` is skipped (zero client area, and a reset with a zero-sized backbuffer fails).
- **Re-entrancy** (`m_bResizingEngine`). Our own `MoveWindow` posts `WM_SIZE` synchronously, so the handler would otherwise recurse into the resize. `ResizeWindowByClientSize` and `SetScreenMode` both hold this for their duration — the latter because `SWP_FRAMECHANGED` posts `WM_SIZE` while `m_ScreenMode` still holds the *old* value, which would rebuild the device for a size `ChangeScreenMode` is about to replace.
- **Engine lifetime** (`m_bEngineReady`, set after `Init_DEVICE`, cleared before teardown). The window is created *before* `initZnzin()`, so `znzin`/`state` are null in between. Note `CHECK_INTERFACE` in `zz_interface.cpp` is only a **profiler hook** — it does not null-check anything, so `setScreen()` would happily dereference null.

<!-- verbatim:end -->

## Updates

- **2026-09-24 (migration, status: conflict, unverified).** The claim above that "Vsync is the only frame cap in the engine" (original client line 661) conflicts with root `CLAUDE.md` line 162, now in [project/rendering-device-d3d9ex.md](../project/rendering-device-d3d9ex.md), which says `zz_system::sleep()` also enforces `max_framerate` and calls itself a correction of an earlier line. Treat this claim as **probably superseded**. Tracked as C-001 in [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md).
