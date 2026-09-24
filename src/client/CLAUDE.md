# CLAUDE.md — Rose Next Client (component guide)

Auto-loaded when working under `src/client/`. The root [CLAUDE.md](../../CLAUDE.md) and
[doc/ai/](../../doc/ai/INDEX.md) rules apply first. This compact guide replaced a 745-line
(176 KB) version on 2026-09-24; every line of that version is preserved verbatim in the
`doc/ai/topics/client/` files listed below (original bytes:
[archive](../../doc/ai/archive/2026-09-24/MANIFEST.md), line map:
[mapping](../../doc/ai/migration/2026-09-24-mapping.md)). The rules here are summaries of
inherited, unverified notes: read the topic before changing the code it describes.

Direct3D 9Ex (plain D3D9 fallback) Win32 client, single-threaded game loop, C++ (VS2019, x86),
built as part of `rose-next.sln`. Packet handlers: `Recv_gsv_*` in `network/recvpacket.cpp`,
`Send_cli_*` in `network/sendpacket.cpp`. Engine changes make `rosenext.exe` + `znzin.dll` a
deploy **pair**.

## Combat presentation (read the combat topics before touching `CObjCHAR` combat code)

- The server decides **how much**; the client only decides **when** to show it. No live call to
  `CCal::Get_DAMAGE()` / `Get_SkillDAMAGE()`.
- Every `CObjCHAR` owns `m_CombatDamageQueue`. `Hitted()` consumes exactly one matching event; a
  frame with no event shows nothing. Do not resurrect timeout / missed-hit recovery.
- `ProjectileImpact` events wait for the projectile's impact; immediate presentation must push
  them back.
- `Reconcile_HP()` is the only thing that raises authoritative HP; lower HP is folded into the next
  real presentation, never a silent bar jump. `StatusTick` is the one raise-allowed exception.
  Digits are `damage_value`; drift correction must not alter them.
- A queued event that can never be presented must be removed (orphan sweeps), or
  `has_pending_damage()` disables HP reconciliation for that character for good.
- Client-synthesised event ids come from `Rose::Combat::kClientSyntheticEventIdBase`.
- Retail hit reactions (flinch) were removed on both client and server; do not restore them.
- One attack animation per confirmed swing (`CanStartConfirmedSwing`, repeat count 1). Several
  "obvious" fixes for phantom swings and position drift were tried and **reverted**: read the
  phantom-swing topic before trying one.

Topics: [core and queue](../../doc/ai/topics/client/combat-core-and-queue.md) ·
[pre-empted swings and remote casts](../../doc/ai/topics/client/combat-preempted-and-remote-casts.md) ·
[orphan swing sweep](../../doc/ai/topics/client/combat-orphan-swing-sweep.md) ·
[projectile classification](../../doc/ai/topics/client/combat-projectile-classification.md) ·
[HP authority and healing](../../doc/ai/topics/client/combat-hp-authority-and-healing.md) ·
[death](../../doc/ai/topics/client/combat-death.md) ·
[phantom swings](../../doc/ai/topics/client/combat-phantom-swings.md) ·
[drain-on-death and stranding](../../doc/ai/topics/client/combat-drain-and-stranding.md) ·
[AI chase and attack speed](../../doc/ai/topics/client/ai-chase-and-attack-speed.md) ·
[cart / castle gear](../../doc/ai/topics/client/cart-castle-gear.md) ·
cross-cutting: [project/combat-damage-presentation](../../doc/ai/topics/project/combat-damage-presentation.md)

## Terrain streaming and performance

- Hitches were resource creation at first render, not file I/O. Measure **lead time**, not queue
  depth: terrain meshes (1 frame) → `[VIDEO] TERRAIN_INSERTS_PER_FRAME`; textures (200-300
  frames) → `[VIDEO] LOAD_BUDGET_US`. Each fix does nothing for the other problem.
- Hunt unexplained hitches with `[VIDEO] FRAME_SPIKE_LOG_MS` and `VSYNC=0`; `STREAM_SPIKE_LOG_MS`
  is silent for non-streaming causes. Diagnostics use `LOG_INFO`, not `LogString`.
- Deferred map unloads, patch keep-alive and patch-index staleness have specific invariants
  (a freed neighbour tile once crashed the client). `vfgetdata()` is a trap.
- If you touch `CFileSystemTriggerVFS::Read()`, re-run `bin\release\vfs_buffer_tests.exe <game dir>`.

Topics: [queues and patches](../../doc/ai/topics/client/terrain-streaming-queues-and-patches.md) ·
[cull bounds and patch index](../../doc/ai/topics/client/terrain-cull-bounds-and-patch-index.md) ·
[prefetch and VFS reads](../../doc/ai/topics/client/terrain-prefetch-and-vfs-reads.md) ·
[hitch campaign 2026-08-28](../../doc/ai/topics/client/frame-hitch-campaign-2026-08-28.md) ·
[chunk hitch and budgets](../../doc/ai/topics/client/chunk-hitch-and-load-budgets.md) ·
[diagnostics and spike log](../../doc/ai/topics/client/streaming-diagnostics-and-spike-log.md) ·
[spawn and texture create](../../doc/ai/topics/client/character-spawn-and-texture-create.md) ·
[cache warming](../../doc/ai/topics/client/loading-screen-cache-warming.md)

## Device, window and timing

- 9Ex: no `D3DPOOL_MANAGED`; stage lockable data in `SYSTEMMEM`. Occlusion throttles, never resets.
- `IsFullScreenMode()` (exclusive only), `IsWindowedFrame()` (windowed only), `IsBorderless()`:
  pick the right predicate; a borderless backbuffer is always the monitor size.
- `resetScreen()` creates a **new** device, so a cached `IDirect3DDevice9*` goes stale.
- Whether vsync is the only frame cap is **disputed** in the inherited notes (C-001 in
  [OPEN_QUESTIONS](../../doc/ai/OPEN_QUESTIONS.md)).

Topic: [frame timing, device, screen modes](../../doc/ai/topics/client/frame-timing-device-screen-modes.md)

## Objects, models and effects

- `m_hNodeMODEL` can be NULL on a live object: test `HasModelNODE()` before per-frame model access.
  Engine `getPosition()/getVisibility() failed` lines have no subject; count objects, not lines.
- Data-driven dummy indices go through `ResolveDummyIDX`; check `INVALID_DUMMY_POINT_NUM` (999).
- Bone effect budgeting/batching applies only to `CreateBoneEFFECT` passive effects.

Topics: [model node and dummy indices](../../doc/ai/topics/client/model-node-and-dummy-indices.md) ·
[bone particles](../../doc/ai/topics/client/bone-particles.md) ·
[overhead names](../../doc/ai/topics/client/overhead-names-cnamebox.md)

## UI and client-only features

- Input: `ProcWndMsgInstant` (synchronous consume) runs before the queued `MsgProc` path; panels
  that consume clicks are ordered there. `CUserInputState::IsEnemy` is the single PVP verdict.
- RmlUi: device lifetime is checked every frame; input consumption is decided by panel geometry,
  not the hover element; `.rml/.rcss` and `UI_strID.ID` load loose, never from the VFS.
- Client-only features send no new packets unless their topic says so (Monster Inspector, chat item
  links, item preview, damage meter, quest icons).

Topics: [input, PVP, summon control](../../doc/ai/topics/client/input-pvp-summon-control.md) ·
[summon info panel](../../doc/ai/topics/client/summon-info-panel.md) ·
[Monster Inspector](../../doc/ai/topics/client/monster-inspector.md) ·
[NPC quest icons](../../doc/ai/topics/client/npc-quest-icons.md) ·
[chat links and item preview](../../doc/ai/topics/client/chat-links-and-item-preview.md) ·
[damage meter](../../doc/ai/topics/client/damage-meter.md) ·
[RmlUi layer](../../doc/ai/topics/client/rmlui-layer.md)

## Build, launch, logging

- Launch: `rosenext.exe --server 127.0.0.1 --username … --password … --auto-connect-server 1 …`
  from `dev/game/`. Never write real credentials into docs.
- `client.log` level: `[LOG] LEVEL=debug` in `rose-next.ini` or `ROSE_LOG_LEVEL`; all diagnostics
  (incl. `CombatTrace`) are Debug. `client.log` flushes per record and survives a crash;
  `error.txt` is buffered and does not.

Topics: [overview](../../doc/ai/topics/client/overview.md) ·
[build, launch, logging](../../doc/ai/topics/client/build-launch-logging.md)
