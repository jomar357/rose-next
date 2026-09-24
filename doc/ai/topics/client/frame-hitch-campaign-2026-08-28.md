# Frame-hitch campaign 2026-08-28

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 190-221 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=190-221 sha256=808605b701a3424da12263af6d3a1b8f036dda7dfbf7847377fba34dbffacb6b -->
**Frame-hitch campaign, 2026-08-28 — where it ended up**

Worst frame on a fixed Muris walking route, measured with `[VIDEO] FRAME_SPIKE_LOG_MS`:

| | worst frame | spikes >20 ms |
|---|---|---|
| start | 139.6 ms | 17 |
| + motion parser bulk-read | 120.5 ms | ~13 |
| + DDS mip chains shipped | 30.7 ms | 5 |
| + mesh read buffering, mips corrected | 21.9 ms | 2 |
| final (warm cache) | none over 20 ms | 0 |
| **validated at 60 Hz, vsync on** | **21.4 ms, no interval missed** | **3** |

At 60 Hz the same route reports `avg` of exactly **16.7 ms** on every spike, and the worst frame is 21.4 ms with nothing approaching 33.3. A single genuinely missed interval in a 30-frame window would move the average to 17.3, so the 20.6–21.4 ms readings are profiler/present-queue jitter rather than dropped frames. `flush` is **0.0–1.5 ms** because `manager_update` gets `frame_ms²` as its allowance and at 16.7 ms frames that is enough to pre-load almost everything — 4–5 ms of useful loading per frame in the idle time, and essentially nothing force-flushed at render. The streaming design works as intended once the frame has room.

Three separate causes, none of them the streaming dials everyone reaches for first, and each found only by narrowing the measurement one level at a time. Both remaining spikes sit ~4x the 5 ms average and neither has a dominant phase; the largest single identifiable cost left is `g_pTerrain->SetCenterPosition()` at **9.3 ms** (`logic[terr=9.3]` with `flush=2.6`), which is pure streaming bookkeeping and loads nothing.

**`SetCenterPosition` turned out to be the map-cell read, not patch bookkeeping.** Two samples of `logic[terr=9.3]` / `[terr=9.5]` sent me to split `Update_VisiblePatchManager` into five passes; that found nothing, because the expensive work is on the boundary-crossing path (`AddOneMap`, `AddMAP`, `ReOrginazationPatch`) which only runs when the player enters a new map cell. Instrumenting *that* showed the cost is `AddOneMap` — the map cell disk read, at 1.3-7.5 ms, which the `MapIO:` row had been reporting as `last map load` all along. It is already throttled to one per 150 ms (`kMinMapLoadIntervalMs`) and no longer pushes a frame over 20 ms now that everything around it is cheap. Nothing to fix; it is inherent I/O, already paced.

Two measurement traps this campaign hit, both worth remembering:

- **An intermittent cost needs the intermittent path instrumented.** Wrapping the every-frame function found `terr=0.1` with all five sub-passes at 0.0 and looked like the problem had vanished.
- **A cold OS page cache inflates `tex[read=]` roughly tenfold** (0.0-0.8 ms warm, 5.4-5.8 ms cold) and with it every frame total. The first run after a re-bake is not comparable with anything. `MAP_PREFETCH` warms map chunks but not textures.

**A total-frame-time threshold cannot compare streaming across framerates.** `FRAME_SPIKE_LOG_MS` fires on the frame total, so the population it samples changes with the framerate: at 60 Hz vsync a frame carrying 4 ms of flush totals ~17 ms and never crosses a threshold of 20, while the same frame uncapped totals ~17 ms against a 3 ms average and looks enormous. That produced a confident, wrong conclusion here — that high framerates starve the resource amortiser — from a 60 Hz run logged at 20 ms against uncapped runs logged at 15. Compared like-for-like at the same chunk arrival, warm cache, same threshold, `flush` is 3.8-5.0 ms uncapped at ~300 fps and 4.0 ms capped at 144: no difference. Use `STREAM_SPIKE_LOG_MS`, which triggers on flush time, when the question is about streaming.

**Measure at the framerate players will actually see.** The whole campaign was run with `VSYNC=0` at 200-330 fps, which is right for *diagnosis* — it exposes CPU cost that a vsync wait would otherwise hide inside `present`. It is wrong for *judging severity*: at 60 Hz the budget is 16.67 ms, so a 17.7 ms frame drops one interval and a 40.8 ms frame drops three, while the same frames look minor against a 3.3 ms average. Validate with `VSYNC=1`.

With vsync on, read the spike log differently: every in-budget frame measures ~16.7 ms because the wait sits inside `present`, so totals cluster at 16.7 / 33.3 / 50 and a `FRAME_SPIKE_LOG_MS` of **20** catches exactly the frames that missed an interval. A large `present` there is the vsync wait and is expected — check `present[mgr= slp=]` before reading anything into it. The amortiser also gets a *bigger* per-frame allowance at 60 fps (`manager_update` is handed `frame_ms²`), so streaming is better amortised than the uncapped numbers suggest; the uncapped measurements are pessimistic for streaming and accurate for CPU spikes.

Method note worth keeping: every round of this overturned the previous round's conclusion. The streaming log blamed terrain; the frame log said `netin`; the packet timer said spawn; the spawn timer said motion loading; the motion split said the file parse, not I/O. **Do not act on the first phase that looks large** — split it until the thing you are looking at has one cause.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
