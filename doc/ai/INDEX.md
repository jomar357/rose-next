# doc/ai index: where project knowledge lives

Entry point for every session after the operating guide. Read [STATE.md](STATE.md) and
[HANDOFF.md](HANDOFF.md) next, then only the topics your task needs. Procedure:
[SESSION_PROTOCOL.md](SESSION_PROTOCOL.md).

## Core records

| File | Purpose |
|---|---|
| [STATE.md](STATE.md) | Current objective, approved scope, progress, blockers, next action, active session, branch/commit, unfinished changes |
| [HANDOFF.md](HANDOFF.md) | Latest handoff and copyable next-session prompt |
| [DECISIONS.md](DECISIONS.md) | PM directions (`PM-*`), AI implementation choices (`IMP-*`), inherited decisions (`INH-*`) |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | Questions for the PM, conflicts between inherited claims, unfinished/unvalidated inherited work |
| [UNAVAILABLE_KNOWLEDGE.md](UNAVAILABLE_KNOWLEDGE.md) | What history refers to but this checkout cannot see (external memory, data, dumps, binaries) |
| [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) | Startup, checkpoint, concurrency, status vocabulary, closing procedure ("Our work here is done") |
| [sessions/](sessions/) | Dated session records (detail, commands, results, previous handoffs) |
| [archive/2026-09-24/MANIFEST.md](archive/2026-09-24/MANIFEST.md) | Byte-exact originals of the guides replaced on 2026-09-24, with hashes |
| [migration/2026-09-24-mapping.md](migration/2026-09-24-mapping.md) | Every original line range → its topic file (the "where did section X go" table) |

Check integrity at any time: `python scripts/verify-ai-docs.py` (read-only).

## Sessions

| Date | Record | Summary |
|---|---|---|
| 2026-09-24 | [2026-09-24-continuity-setup](sessions/2026-09-24-continuity-setup.md) | Continuity system created; guides migrated to topics |

## Finding a topic by task

| If you are working on… | Start with |
|---|---|
| Setting up / running the game on a machine | **project/local-setup-runbook** (start here), then the README |
| Building anything, or a build that fails oddly | project/build-system-and-pitfalls, project/conventions-and-dev-environment |
| Combat display, HP bars, death, damage digits | project/combat-damage-presentation, then the client/combat-* topics, gameserver/combat-flow-and-packet-rules |
| Monster skills, AI files, imports that bring AI | project/missing-npc-row-degrade, project/ai-skill-reference-failures, gameserver/ai-guard-npc-rows-skills-status |
| Frame hitches, streaming, loading | project/terrain-streaming-performance, client/streaming-diagnostics-and-spike-log, client/chunk-hitch-and-load-budgets |
| Rendering artefacts (flicker, vanishing walls, z-fighting) | project/cull-bounds-zsc, project/depth-buffer-precision, project/coplanar-placements, project/object-lightmaps-atlas |
| Device, window modes, alt-tab | project/rendering-device-d3d9ex, client/frame-timing-device-screen-modes |
| A crash or freeze | project/debugging-client-crash, project/missing-assets-degrade, client/model-node-and-dummy-indices |
| Game data edits, balance, imports | project/data-repair-tooling, project/monster-balance-level-gate, project/buffs-passives-percent, project/oro-667-import, project/skaaj-import, project/item-import-tooling |
| Baking / VFS | project/vfs-offset-limit, project/data-repair-tooling |
| UI panels, RmlUi, UI2 | project/rmlui-ui-layer, client/rmlui-layer, project/client-only-features |
| Monster spawns, leashing | project/monster-spawning-regen, gameserver/walkability-mov |
| Map editor (xadet) | map-editor/* |

## Topics

Every topic file starts with a provenance header and ends with an *Updates* section. Text between
`verbatim` markers is inherited and unverified; see the header of each file.

### project (from the root guide)

| Topic | Covers |
|---|---|
| [Project overview and architecture](topics/project/overview-and-architecture.md) | What Rose Next is, the four-process architecture, per-zone server threads. |
| [Build system, key build facts, common build pitfalls](topics/project/build-system-and-pitfalls.md) | Three-phase x86 build, /Od history, D3D9 headers, d3dx9_43.dll, RmlUi/FreeType projects, French MSVC diagnostics, build-via-sln rule. |
| [Project structure](topics/project/project-structure.md) | Directory map of src/, data/, database/, thirdparty/, scripts/, tools. |
| [Database and networking](topics/project/database-and-networking.md) | PostgreSQL, server.toml, migrations, password hashing; packet protocol and FlatBuffers. |
| [Code conventions and dev environment](topics/project/conventions-and-dev-environment.md) | No clang-format over the tree; naming prefixes; just recipes; A/B builds; auto-connect. |
| [Combat damage presentation (cross-cutting)](topics/project/combat-damage-presentation.md) | Server-authoritative DamageEvent/CombatSwing model; mob-death drop broadcast and duplicate ground items; orphaned events and HP convergence; pending death. |
| [Rendering device (Direct3D 9Ex)](topics/project/rendering-device-d3d9ex.md) | 9Ex pools, dynamic buffers, occlusion codes, borderless fullscreen, display-mode mirroring, VSYNC and the INIT.LUA framerate cap. |
| [Bone particle budget (summary)](topics/project/bone-particle-budget.md) | CBoneEffectBudget tiers, budgets and additive batching for passive bone effects. |
| [Monster spawning: regen point caps](topics/project/monster-spawning-regen.md) | CRegenPOINT tactical escalation, tacticPoint vs limitCNT, Karkia 4x overpopulation, per-slot counts, import-karkia stage 3. |
| [Client-only features (summaries)](topics/project/client-only-features.md) | Summon control, summon info panel, Monster Inspector, NPC quest icons, damage meter, chat item links, item preview. |
| [RmlUi UI layer and UI2 (summary)](topics/project/rmlui-ui-layer.md) | RmlUi/FreeType integration, rose-theme.rcss, UI2 conversion switch, drag/click and drag-and-drop traps. |
| [Cull bounds come from geometry, not the ZSC](topics/project/cull-bounds-zsc.md) | Broken ZSC AABBs, MakeAABBFromObject engine query, ZMS version units, 4-plane frustum, audit-zsc-bounds.py. |
| [Depth buffer precision](topics/project/depth-buffer-precision.md) | D16 -> D24 negotiation, near-plane math, log format codes, no depth bias, set-camera-near-plane.py. |
| [Coplanar map-object placements flicker](topics/project/coplanar-placements.md) | Zero-separation duplicate placements, fix-coplanar-object-overlaps.py, never delete records, back-to-back faces. |
| [Object lightmaps are a gutterless atlas](topics/project/object-lightmaps-atlas.md) | Why mip bleeding cannot occur (INIT.LUA setMipmapLevel(3)) and when it could. |
| [Missing assets must degrade, not kill](topics/project/missing-assets-degrade.md) | Four VFS/engine defects on the missing-file path; ZZ_LOG varargs trap; failed-load recording; manager re-queue. |
| [A missing NPC row must degrade, not kill](topics/project/missing-npc-row-degrade.md) | Change_CHAR on blank LIST_NPC rows, DeleteBoneEFFECT by-value bug, heap-corruption dumps, audit-ai-monster-refs.py. |
| [AI skill references: five failure classes](topics/project/ai-skill-reference-failures.md) | Blank/colliding skill ids, release-clip events, slot layouts, column 88/90 status, impossible level windows; import-monster-skills.py and audit-ai-skill-refs.py. |
| [Debugging a client crash or freeze](topics/project/debugging-client-crash.md) | debug-client-crash.ps1, cdb working dir, non-invasive attach, client.log vs error.txt, stale-build artifacts. |
| [Terrain streaming performance (summary)](topics/project/terrain-streaming-performance.md) | Lead time vs queue depth, insert cap vs load budget, null-neighbour map tile crash, spike logs. |
| [Shared data types and item encoding](topics/project/shared-data-and-item-encoding.md) | src/common/shared; 5+11-bit item header; type/id initializer; package boxes (class 322). |
| [Buffs and passives are percentage-based](topics/project/buffs-passives-percent.md) | Rate vs flat columns, pre-buff base stat, heals stay flat, HIT stays flat, vtable change warning. |
| [Monster balance and the level gate](topics/project/monster-balance-level-gate.md) | Level-proportional hit gate (1.05), skill gate, (ATK-DEF+250), drop cutoff, balance-pass ordering. |
| [Oro is the 667 build's Oro](topics/project/oro-667-import.md) | remove-oro/import-oro-667, missing 667 AI/CON/MOV, CXE dialogs, attack-speed units, NPC_TYPE, summon closure, drops. |
| [Skaaj (Jrose cat-folk island)](topics/project/skaaj-import.md) | import-skaaj.py, blank sky column, quest switch 90, global trigger names, QEX1 overrides, I_NUM STL. |
| [Data repair tooling](topics/project/data-repair-tooling.md) | Catalogue of idempotent data-fix scripts and the failure each addresses; STL key grep trap; .bak in bakes. |
| [The .vfs offset limit (2 GB -> 4 GB)](topics/project/vfs-offset-limit.md) | Unsigned offsets, vfread/vfseek fixes, pack.ps1 + verify-vfs.py, rose_N.vfs rollover. |
| [Item import tooling](topics/project/item-import-tooling.md) | import-item.py, --art-only safety, icon tools, skill-tree art, ZSC/field model indices. |
| [NPC dialog quest options (.CON QEX1 appendix)](topics/project/npc-dialog-qex1.md) | Lua 4 bytecode dialogs and the QEX1 appendix mechanism. |
| [Local setup runbook](topics/project/local-setup-runbook.md) | **New 2026-09-24.** What this checkout contains, toolchain state, working build order, Rust and toolset traps, remaining steps to run locally. |

### client (from `src/client/CLAUDE.md`)

| Topic | Covers |
|---|---|
| [Client overview](topics/client/overview.md) | Subsystem directories, important classes, client networking. |
| [Client combat: core model and damage queue](topics/client/combat-core-and-queue.md) | DamageEvent fields, per-defender queue, Hitted timing, crowd catch-up, projectile timing, hard-control interrupts. |
| [Client combat: pre-empted swings and remote casts](topics/client/combat-preempted-and-remote-casts.md) | Self-pre-empted swings, remote cast held behind swing, cast watchdog, GSV_SKILL_START validation, hit reactions removed. |
| [Client combat: orphan swing sweep](topics/client/combat-orphan-swing-sweep.md) | Resolving unpresentable confirmed swings; grace period measurement; misses that are not this bug. |
| [Client combat: projectile classification](topics/client/combat-projectile-classification.md) | Ranged skill classification, target-bound skills, fireless motions, bow/gun frames with nothing to fire, presentation_kind agreement. |
| [Client combat: HP authority and healing](topics/client/combat-hp-authority-and-healing.md) | Reconcile_HP, announced heals, StatusTick exception, checkpoint supersession and staleness, digits vs HP. |
| [Client combat: death presentation](topics/client/combat-death.md) | Explicit death, lethal legacy payloads, pending-death backstop, spectator stale-death fallback. |
| [Client combat: phantom swings and position drift](topics/client/combat-phantom-swings.md) | Self-looping attack motions, MISS presentation, one animation per confirmed swing, reverted fixes. |
| [Client combat: drain-on-death and stranded events](topics/client/combat-drain-and-stranding.md) | Attacker dies mid-swing, no client damage math, orphan sweep as self-healing, synthetic event ids, key methods. |
| [Client AI chase movement and attack speed](topics/client/ai-chase-and-attack-speed.md) | CMD_MOVE with target paths; server-owned swing cadence and speed sync. |
| [Cart / castle gear combat and visuals](topics/client/cart-castle-gear.md) | Rider vs cart routing, damage re-keying, first mounted attack, inverted union fields, skeleton fallback. |
| [Terrain streaming: queues, hysteresis, patch keep-alive](topics/client/terrain-streaming-queues-and-patches.md) | Load/unload queues, deferred unloads, proximity ring, insert caps. |
| [Terrain: object cull bounds and patch index staleness](topics/client/terrain-cull-bounds-and-patch-index.md) | MakeAABBFromObject details, far-insert test, patch pointer staleness. |
| [Terrain: chunk prefetch and buffered VFS reads](topics/client/terrain-prefetch-and-vfs-reads.md) | CMapFilePrefetcher through the VFS, six files per cell, 32 KB read-ahead, vfs_buffer_tests. |
| [Frame-hitch campaign 2026-08-28](topics/client/frame-hitch-campaign-2026-08-28.md) | Measured route results, causes, measurement traps, vsync interpretation. |
| [Chunk-display hitch and load budgets](topics/client/chunk-hitch-and-load-budgets.md) | Lead-time table, TERRAIN_INSERTS_PER_FRAME, LOAD_BUDGET_US, rejected per-item weight fix. |
| [Streaming diagnostics and the whole-frame spike log](topics/client/streaming-diagnostics-and-spike-log.md) | MapIO/Flush rows, instrumentation traps, FRAME_SPIKE_LOG_MS format and phase semantics. |
| [Character spawn (motion parser) and texture create costs](topics/client/character-spawn-and-texture-create.md) | Bulk motion reads, spawn breakdown, missing DDS mip chains, add-dds-mipmaps.py, vfgetdata trap, lightmap exclusion. |
| [Loading-screen cache warming](topics/client/loading-screen-cache-warming.md) | CACHE_WARM_MB measurements, per-zone budget, cold-cache measurement, traps. |
| [Overhead name drawing (CNameBox)](topics/client/overhead-names-cnamebox.md) | Sprite batch, boxed drawFont rect above origin, clan row, the not-understood rule. |
| [Bone particle budgeting, batching and emit accumulator](topics/client/bone-particles.md) | Tiers, batching conditions, spawn-debt accumulator rules. |
| [Input dispatch, PVP enemy verdict, summon control](topics/client/input-pvp-summon-control.md) | ProcWndMsgInstant vs queued path, right-drag camera, IsEnemy, CTRL+click summon orders. |
| [Summon info panel](topics/client/summon-info-panel.md) | Visibility, gauge lifecycle, server-scaled stats, max HP from packet, drag. |
| [Monster Inspector](topics/client/monster-inspector.md) | Client-only window skill, drop list walk, live HP, 3D preview pipeline, input, background art. |
| [NPC overhead quest icons](topics/client/npc-quest-icons.md) | QSD trigger harvesting, dialog probe, timed quests, refresh, draw, sprites, deploy gotcha, status. |
| [Chat item links and item preview panel](topics/client/chat-links-and-item-preview.md) | Wire token, send/display paths, tooltips; Alt+click preview, puppet, camera mirror. |
| [Damage meter (/dps)](topics/client/damage-meter.md) | Data core tap, attribution fields, classification, dedup, segments, UI, credit, limits. |
| [RmlUi layer (client implementation)](topics/client/rmlui-layer.md) | Files, hooks, device lifetime trap, input arbitration, rendering notes, asset loading. |
| [Model node lifetime and dummy indices](topics/client/model-node-and-dummy-indices.md) | NULL m_hNodeMODEL on live objects, getPosition/getVisibility traps, ResolveDummyIDX, INVALID_DUMMY_POINT_NUM. |
| [Frame timing, device, swap chain and screen modes](topics/client/frame-timing-device-screen-modes.md) | timeBeginPeriod, 9Ex rules, present parameters, three screen modes and predicates, window sizing. |
| [Client build, conventions, launch and diagnostic logging](topics/client/build-launch-logging.md) | Dependencies, launch flags, LOG LEVEL switch, client.log behaviour. |

### gameserver (from `src/sho_gameserver/CLAUDE.md`)

| Topic | Covers |
|---|---|
| [Game server overview, configuration, dependencies](topics/gameserver/overview.md) | Architecture, source layout, networking, zones, server.toml, dependencies, conventions. |
| [Game server combat flow and presentation packet rules](topics/gameserver/combat-flow-and-packet-rules.md) | Apply_DAMAGE flow, repeat attack no-op, PVP ally rule, DamageEvent/CombatSwing rules, speed fields. |
| [Game server AI guard, junk NPC rows, skill damage, status effects](topics/gameserver/ai-guard-npc-rows-skills-status.md) | AIACT24 guard, junk NPC row degrade, projectile skill tagging, status success bits. |
| [Game server summon control](topics/gameserver/summon-control.md) | Recv_cli_SUMMON_CONTROL, manual-order window, PlayerOrderMoveTo. |
| [Walkability and missing .MOV files](topics/gameserver/walkability-mov.md) | Blocked-by-default grid, leash/wander gating, per-tile open fallback, affected zones. |

### map-editor (from `xadet/rose-online-map-editor/CLAUDE.md`)

| Topic | Covers |
|---|---|
| [Map editor overview, build/deploy, architecture, data formats](topics/map-editor/overview-build-architecture.md) | Vendored xadet editor, VS2019 build, deploy to data/, manager layout, file types. |
| [Map editor debugging workflow and editing guidelines](topics/map-editor/debugging-and-editing-guidelines.md) | Log-first debugging, narrow changes, optional assets, save semantics and no undo. |
| [Map editor compatibility fixes already made](topics/map-editor/compatibility-fixes.md) | Karkia/Skaaj IFO save fix, LIT ordinals, sky column, MOV painting, precision, morph flags, lightmap sharing. |
| [Map editor verification checklist](topics/map-editor/verification-checklist.md) | Manual checks for map load, spawn UI and object/terrain changes. |

## Other first-party documents (left in place, not migrated)

Inherited and unverified like the topics. Sizes as of 2026-09-24.

| Document | About |
|---|---|
| [context.md](../../context.md) (18 KB) | Deep technical reference: packet wire formats, command ID ranges, connection flow, entity hierarchy, sectors, server tick loop, combat pipeline |
| [README.md](../../README.md) (28 KB) | Public project readme |
| [doc/rose-next-build.md](../rose-next-build.md) | Build notes |
| [doc/d3d9ex-migration.md](../d3d9ex-migration.md) | D3D9 → 9Ex migration roadmap and design notes |
| [doc/znzin-optimizations.md](../znzin-optimizations.md) | Engine performance investigation |
| [doc/zsc-bounding-boxes.md](../zsc-bounding-boxes.md) | ZSC bounding boxes and the vanishing Muris walls |
| [doc/rmlui-evaluation.md](../rmlui-evaluation.md) | RmlUi evaluation, phases, authoring palette, traps |
| [doc/combat-display-fix.md](../combat-display-fix.md), [doc/combat-crowd-drain.md](../combat-crowd-drain.md) | Combat display history; crowd damage presentation |
| [doc/balance-analysis.md](../balance-analysis.md) | Endgame balance analysis (re-derived by `scripts/balance-sim.py`) |
| [doc/project-drops.md](../project-drops.md) | Endgame loot tier |
| [doc/karkia-roadmap.md](../karkia-roadmap.md) (81 KB), [doc/karkia-survey.md](../karkia-survey.md), [doc/karkia-catacombs-implementation-brief.md](../karkia-catacombs-implementation-brief.md) | Karkia import |
| [doc/jrose-survey.md](../jrose-survey.md), [doc/jrose-back-import.md](../jrose-back-import.md), [doc/jrose-catacombs-investigation.md](../jrose-catacombs-investigation.md), [doc/jrose-catacombs-collision-investigation.md](../jrose-catacombs-collision-investigation.md), [doc/jrose-tower-of-sorrow-investigation.md](../jrose-tower-of-sorrow-investigation.md) | Jrose data surveys and investigations |
| [doc/mors-survey.md](../mors-survey.md) | Mors survey (Jrose) |
| [doc/skill-import-investigation.md](../skill-import-investigation.md), [doc/skill-tree-art.md](../skill-tree-art.md) | Skill import; adding a skill to the skill tree art |
| [doc/custom-equipment-asset-feasibility.md](../custom-equipment-asset-feasibility.md), [doc/npc-weapon-models.md](../npc-weapon-models.md) | Equipment assets; NPC weapon models |
| [doc/monster-inspector-ui-spec.md](../monster-inspector-ui-spec.md) | Monster Inspector art spec |
| [doc/tuning-preview.md](../tuning-preview.md) | Mounted-stat preview tuning |
| [doc/667UI/](../667UI/) (3 files) | 667 build HUD/UI reverse-engineering |
| [particle.md](../../particle.md), [3d data edits.md](<../../3d data edits.md>) | Particle performance notes; 3D data edit notes |
| [src/tools/quest-editor/PROGRESS.md](../../src/tools/quest-editor/PROGRESS.md) (70 KB), [ROADMAP.md](../../src/tools/quest-editor/ROADMAP.md), [multi step chain quest.md](<../../src/tools/quest-editor/multi step chain quest.md>) | Quest editor design log, roadmap, chain-quest note |
| [src/tools/npc-shop-editor/README.md](../../src/tools/npc-shop-editor/README.md) | Shop editor / GM browser |
| [data/README.md](../../data/README.md) | Where to place game data |

Vendored docs (`thirdparty/`, `website/.../vendor/`, the map editor's upstream `README.md`) are not indexed.
