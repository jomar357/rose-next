# Streaming diagnostics and the whole-frame spike log

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 250-272; `src/client/CLAUDE.md` lines 313-321 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=250-272 sha256=50f14ce5abe35aed9f8f13536b8c8b05f80238db64b4422c2cc28330f62c4213 -->
**Debugging**
- The `MapIO:` HUD row gives last/worst wall-clock ms for a single `CMAP::Load` and a single unload, plus a phase breakdown (`him`/`til`/`ifo`/`lit`/`quad`). Use it instead of the `Logic:` line's `terr=` — that is a 30-frame average, and with loads gated to one per 150 ms most frames contain none, so a 30 ms spike averages away to nothing.
- The `Flush:` row measures `zz_manager::flush_entrance` — resource loads forced to happen synchronously at first-render time rather than being amortised by the lazy entrance line. This is the cost of **displaying** new terrain as opposed to reading its files, it runs inside `beginScene()`, and it therefore lands in the `Time:` line's `shadow=` slot rather than `logic=`.
- **Three instrumentation traps, all hit in practice — respect them when adding counters here:**
  - A "worst since zone entry" peak **saturates during the zone-in burst** (35–50 ms is normal there) and is then useless for anything you do afterwards. Hence `/perfreset`, which re-zeroes `Flush: peak` and `MapIO: worst`.
  - A per-frame value is **unreadable**: the event lasts one frame at 130 fps. Hence `recent`, a ~4 s sliding hold (bigger spike replaces at once, otherwise it expires and re-baselines) with an age so you know whether you are looking at something that just happened.
  - Neither of the above helps if you are busy playing. Hence the **spike log**: with `[VIDEO] STREAM_SPIKE_LOG_MS=4` (the threshold doubles as the switch; **0 = off, the default**), any frame spending ≥ that many ms in `flush_entrance` writes a `Flush spike:` line to `client.log`, rate-limited to 4/s and independent of the debug HUD. Collect by playing, read afterwards. Too chatty to leave on.
  - **`lazyq`/`lazyterr` in that line are sampled after the render phase has already drained the queue**, so they read ~0 during the very spikes they appear to explain. Read `leadavg`/`leadmax` instead — measured at the flush itself. This misreading cost a whole debugging round.
  - **A diagnostic scoped to one subsystem is silent for every other cause, and silence reads as health.** `STREAM_SPIKE_LOG_MS` fires only when `flush_entrance` was expensive, so a hitch from the packet drain, object Proc, the shadow pass or a GPU stall produced no line at all and looked exactly like a smooth frame. That is what `FRAME_SPIKE_LOG_MS` below is for.

**Whole-frame spike log (`[VIDEO] FRAME_SPIKE_LOG_MS`, 0 = off, the default)**

Triggers on **total frame time** rather than on any one subsystem, and prints that frame's own phase split. Start here when hunting an unexplained hitch; `STREAM_SPIKE_LOG_MS` then narrows down whatever it points at.

```
Frame spike: 47.3 ms (avg 8.1) | netin=0.3 logic=2.1 scnupd=1.2 shadow=31.9 render=8.4
ui=1.1 present=1.9 oth=0.4 | logic[obj=1.4 terr=0.2 fx=0.3 uiupd=0.1]
| flush=30.2ms/258n [terrain=255 mesh=0 tex=3 mat=0 other=0] | suppressed=0
```

- Lives in `FrameProfiler.cpp` (`EmitSpike`/`NoteSpike`), threshold pushed in from `winmain.cpp` at startup and logged there so an inactive diagnostic cannot be mistaken for a quiet session.
- **The 250 ms rate limiter keeps the *worst* frame of each window, not the first, and emission is deferred to the end of the window to make that possible.** Keeping the first is the obvious implementation and it is actively misleading: in the very first capture it reported a 24 ms frame and discarded a >=104 ms one that landed 250 ms later, so the headline number was the least interesting frame of the burst. `others=N` counts the rest of the window. A hitch log that drops the biggest hitch is worse than no log, because it looks like evidence.
- **`pkt[n= worst= ]` breaks the drain down further**: how many packets the frame handled, and the single most expensive one's type and cost. `n` high with a small `worst` is packet volume; `n` low with a large `worst` is one handler doing something enormous — measured, that is the case here. Types print in hex so they grep straight against `src/common/net_prototype.h`; `scripts/decode-packet-type.py --log <client.log>` annotates a whole capture. Note client→server and server→client share the id space (`0x0796` is both `CLI_STOP` and `GSV_STOP`), and the log only ever reports received packets, so the inbound name is the right reading.
<!-- verbatim:end -->

<!-- verbatim:begin src=src/client/CLAUDE.md lines=313-321 sha256=5e55bcc8cf85d2ee92a7492515eaf01c0ab9eaf83bcedc7c1efd0ed077038ada -->
- **`netin` is four unrelated jobs** — the Win32 pump, `g_GameDATA.Update()`, `g_pNet->Proc()` and `ProcInput()` — and it turned out to be one of the largest spike phases in practice (48-201 ms in-game, `flush=0`). The `netin[msg/gdat/pkt/inp]` group splits it. Packet handlers run synchronously inside `g_pNet->Proc()`, so anything a packet triggers — a zone change, a large inventory update — is charged to `pkt` rather than to the phase that does the work.
- **The phase values are that frame alone**, not the HUD's 30-frame mean. `FrameProfiler::End` accumulates into a per-frame bucket which `EndFrame` folds into the window total — the whole reason the log exists is that a hitch is one frame and the averaged HUD row cannot hold it.
- **`flush=` is sampled from `CGameStateMain::Update`, not from `EndFrame`, and that ordering is load-bearing.** The engine rolls its per-frame flush counters over in `zz_system::sleep()`, which `swapBuffers()` calls — i.e. *before* `FrameProfiler::EndFrame()` runs. Sampling them in the profiler would read a clean zero on every spike frame and quietly exonerate streaming for hitches it caused. Hence `FrameProfiler::CaptureFlushStats()`, called after the render and before `endScene()`.
- **`flush=` is a whole-frame total and does not belong to any one phase.** Force-loads happen in at least three places: the octree's within-50 m distance pass (`zz_scene_octree::update_distance`, reached from `updateSceneEx()` — so it lands in **scnupd**), `zz_terrain_block::before_render()` under `beginScene()` (**shadow**), and the render pass. A large `flush=` therefore says streaming was involved but not which phase paid for it — read it *against* the phase values, not instead of them. Sampling after the render is what makes it a complete total.
- Frames that never reach that call (lost focus with `BACKGROUND_RENDER=0`, or `beginScene()` returning false) report `flush=unsampled`, deliberately not `flush=0.0` — "no data" and "no flush work" are different findings.
- **Run with `VSYNC=0` while hunting.** With vsync on, the frame cap is paid inside `present`, which inflates it on every frame and masks the real cost of everything else.
- `oth` = total minus the bracketed phases. A large `oth` is a real finding — work inside the frame that no bracket covers — not measurement noise.
- Streaming diagnostics use `LOG_INFO`, **not `LogString`**. `LogString` reports every line as `Debug` regardless of its `LOG_NORMAL`/`LOG_DEBUG_` argument (`log.h`'s `OutputString` hardcodes it), and the client initialises the logger at `Info` — so a `LogString` diagnostic never reaches `client.log`. Anything you add that needs to be readable must use the `LOG_*` macros.
- Logs around `LoadZONE` / `FreeZONE` report queued-load and dirty-map counts; they must return to 0 after zone teardown.
<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
