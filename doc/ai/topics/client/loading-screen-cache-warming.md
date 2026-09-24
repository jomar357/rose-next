# Loading-screen cache warming

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 322-353 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=322-353 sha256=5e7692ae21c5b80fa9590cf9fbddfc3d80ab3d48a2699431924ebc1c741c57da -->
**Loading-screen cache warming (`[VIDEO] CACHE_WARM_MB`, 0 = off, the default)**

A zone load leaves the OS page cache cold for everything that zone has not touched yet, and a cold cache inflates `tex[read=]` roughly 10x (0.0-0.8 ms warm vs 5.4-5.8 cold). Warming reads whole groups of archive files start to finish on the prefetcher's worker thread while the loading screen is up, purely so the *first* in-game access to any of them costs no disk read.

**Measured, cold cache, same five-zone route, warming on vs off:**

| | per-texture read, in-game | per-texture read, zone transition | frames > 20 ms |
|---|---|---|---|
| on (two runs) | 0.135 / 0.142 ms | 0.475 ms | 6, 6 |
| off | 0.503 ms | 0.445 ms | 10 |

**The gain is entirely in-game, and there is none at the zone transition.** That inversion is the important part and it is structural, not a tuning failure: the warm is kicked off from `LoadZONE`, the same moment that zone's own texture burst begins, so it can never get ahead of it. What it does buy is the streaming seconds later, once you are walking around — 3.7x on the mean, 6-7x on the median. **Do not reach for warming to shorten a loading screen**; two rounds of work went into the transition case before this measurement showed it was unreachable.

The corollary for measurement: **every run before this one had warming on**, so none of them could say whether the feature did anything. A/B against *off* was the only test that mattered and it was the last one run. Default is now on at 300 MB.

**The zone's own map directory is warmed too, on a weaker rationale.** A five-zone cold-cache run showed every in-game frame at 8-20 ms, but each zone *transition* spent 45-88 ms reading 130-211 textures -- 0.2-0.65 ms each against 0.04-0.3 ms for in-game batches, i.e. reading cold. The cause was a gap in what was warmed: `3DDATA\MAPS` holds **5562 DDS files totalling 1017 MB**, more than every other tree combined, and none of it was covered. Warming a whole continent is not the answer either (Junon alone is 423 MB, most of it zones the player is not in); the zone's own directory is 18 MB at the median and 67 MB at the worst, so it is queued first and costs almost nothing. It comes from the `.ZON` path's parent, so new zones need no code change.

Five groups are queued per zone, most zone-specific first: the zone's own `3DDATA\MAPS\<continent>\<zone>`, then `3DDATA\TERRAIN\TILES\<area>`, `3DDATA\<area>`, and finally the shared `3DDATA\NPC` and `3DDATA\MOTION`. `<area>` is the continent directory taken from the zone's own map path (`ZONE_FILE()`'s third component), not a table, so a new continent needs no code change. Junon warms 5989 files / 279 MB.

Things that will bite:

- **It shares the map-cell prefetcher's worker thread but is a separate feature with a separate switch, and conflating the two silently disables it.** The warm loop originally used `ShouldProcessGeneration`, which tests `m_bEnabled` — the `MAP_PREFETCH` flag, off by default. Warming therefore aborted on its very first candidate name and logged `done (0 file(s))`, which reads as "nothing matched" rather than "never ran". Use `ShouldContinueWarm`, which tests stop + generation only.
- **Map cells always win.** `DoWarmSlice` runs only when the map-cell queue is empty, does at most 24 files, and returns to re-check the queue — so a cell queued mid-warm waits one slice, not a whole group. Getting that backwards would turn a first-visit optimisation into a permanent regression.
- **Completing a scan and being cancelled mid-scan are different, and `m_WarmedPrefixes` is never cleared.** Marking a cancelled prefix as warmed retires it for the session having read nothing. Startup crosses several zones in quick succession (`FreeZONE(0)` -> `FreeZONE(4)` -> the real one), each bumping the generation, so *every* group got retired instantly.
- **The budget is charged per zone, not per session, and that distinction is the whole feature.** As a session-lifetime cap it spent everything on the first zone: a cold-boot run warmed Junon to 279 MB of 300, then warping to Oro got its tile group and 144 of 391 object files before the cap stopped it, and a third zone would have got nothing. The counter now resets on zone change; `m_WarmedPrefixes` still suppresses re-warming `NPC`/`MOTION`, so a later zone only pays for what it actually introduces. Exhaustion logs which groups were skipped rather than truncating silently.
- **Measuring it needs a cold page cache, and rebooting is not the only way.** A second run reads everything from RAM whether or not warming is on, so an A/B without an eviction step returns "no difference" regardless of how well it works. `just purge-cache` (`scripts/purge-page-cache.ps1`) drops the standby list in about a second, which is the part of a reboot that matters here; it prints the before/after so a purge that did nothing cannot pass for one that worked.
- **`tex[read=]` is not pure disk I/O, so it has a floor warming cannot remove.** It spans `vfs_thread->open()` plus `read(..., forcing=true)`, and the forcing read does the file read *inline on the calling thread* under `cs_`, a critical section shared with the engine's VFS worker. Most of the residual is lock wait and buffer allocation. Cold-vs-warm still moves it by 3.7x, so it remains a usable signal — just do not expect it to approach zero.
- **A page-cache warm has no number of its own.** Its effect shows up as `MapIO`/`Flush` going down, never as a metric that says "warming worked". The `Warm:` HUD row reports files/MB read this session so you can tell it ran at all — cumulative, since a warmed group is deliberately never redone.
- Verify the group contents independently of the client by parsing `data.idx` directly; the per-group counts printed at startup should match a prefix count over the FAT exactly (213 / 1949 / 1784 / 2043 for Junon). That is what proved the reader was pulling the intended set rather than merely running.

- If post-warp hitches come back, check queue sizes first. If free-look hitches come back, check whether the proximity pass is still running (`Update_VisiblePatch` called from `Update_VisiblePatchManager`) and whether `m_bPatchIndexDirty` is being refreshed.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
