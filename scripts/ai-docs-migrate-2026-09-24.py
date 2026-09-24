#!/usr/bin/env python3
"""One-time migration of the oversized AI instruction files into doc/ai/ topics.

Run on 2026-09-24 against HEAD 84f6206. It is kept so the migration is
reproducible and auditable; `scripts/verify-ai-docs.py` is the tool to run
afterwards (and in any later session).

What it does, in order:

1. Archives the original bytes of every instruction file it replaces into
   `doc/ai/archive/2026-09-24/` under a `.txt` name (so no AI tool ever
   auto-loads an archive as instructions), and writes `manifest.json` with
   original path, capture date, git revision, git blob id and SHA-256.
   An archive that already exists is never rewritten: if its hash differs
   from the current source the script stops.
2. Splits each archived file into contiguous line ranges (the PLAN below).
   Every line of every source lands in exactly one segment. Each segment is
   written *verbatim* into a topic file between
   `<!-- verbatim:begin ... -->` / `<!-- verbatim:end -->` markers. Several
   segments may go to one topic file.
3. Relative Markdown links inside a segment are re-targeted so they still
   point at the same file from the topic's new directory. Links that were
   already broken in the original (for example `src/client/CLAUDE.md`
   linking `doc/rmlui-evaluation.md`, which resolves under `src/client/`)
   are repaired to the repo-root path when that exists. Every rewrite is
   recorded per segment (`links`) in `doc/ai/migration/2026-09-24-mapping.json`
   so the verifier can undo them and prove byte identity.
4. Writes the mapping JSON and a human-readable `2026-09-24-mapping.md`.

It does NOT write the new compact CLAUDE.md / AGENTS.md files; those are
authored by hand. It refuses to overwrite an existing topic file unless
`--force` is given, because topic files gain dated "Updates" over time.
"""
import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE = "2026-09-24"
ARCHIVE_DIR = f"doc/ai/archive/{DATE}"
MAPPING_JSON = f"doc/ai/migration/{DATE}-mapping.json"
MAPPING_MD = f"doc/ai/migration/{DATE}-mapping.md"
TOPICS = "doc/ai/topics"

# source path -> archive file name
SOURCES = {
    "CLAUDE.md": "root--CLAUDE.md.txt",
    "src/client/CLAUDE.md": "src--client--CLAUDE.md.txt",
    "src/sho_gameserver/CLAUDE.md": "src--sho_gameserver--CLAUDE.md.txt",
    "xadet/rose-online-map-editor/CLAUDE.md": "xadet--rose-online-map-editor--CLAUDE.md.txt",
    "AGENTS.md": "root--AGENTS.md.txt",
}

# dest topic -> (title, one-line summary for the index)
TOPIC_META = {
    # ---- root CLAUDE.md --------------------------------------------------
    "project/overview-and-architecture.md": ("Project overview and architecture", "What Rose Next is, the four-process architecture, per-zone server threads."),
    "project/build-system-and-pitfalls.md": ("Build system, key build facts, common build pitfalls", "Three-phase x86 build, /Od history, D3D9 headers, d3dx9_43.dll, RmlUi/FreeType projects, French MSVC diagnostics, build-via-sln rule."),
    "project/project-structure.md": ("Project structure", "Directory map of src/, data/, database/, thirdparty/, scripts/, tools."),
    "project/database-and-networking.md": ("Database and networking", "PostgreSQL, server.toml, migrations, password hashing; packet protocol and FlatBuffers."),
    "project/conventions-and-dev-environment.md": ("Code conventions and dev environment", "No clang-format over the tree; naming prefixes; just recipes; A/B builds; auto-connect."),
    "project/combat-damage-presentation.md": ("Combat damage presentation (cross-cutting)", "Server-authoritative DamageEvent/CombatSwing model; mob-death drop broadcast and duplicate ground items; orphaned events and HP convergence; pending death."),
    "project/rendering-device-d3d9ex.md": ("Rendering device (Direct3D 9Ex)", "9Ex pools, dynamic buffers, occlusion codes, borderless fullscreen, display-mode mirroring, VSYNC and the INIT.LUA framerate cap."),
    "project/bone-particle-budget.md": ("Bone particle budget (summary)", "CBoneEffectBudget tiers, budgets and additive batching for passive bone effects."),
    "project/monster-spawning-regen.md": ("Monster spawning: regen point caps", "CRegenPOINT tactical escalation, tacticPoint vs limitCNT, Karkia 4x overpopulation, per-slot counts, import-karkia stage 3."),
    "project/client-only-features.md": ("Client-only features (summaries)", "Summon control, summon info panel, Monster Inspector, NPC quest icons, damage meter, chat item links, item preview."),
    "project/rmlui-ui-layer.md": ("RmlUi UI layer and UI2 (summary)", "RmlUi/FreeType integration, rose-theme.rcss, UI2 conversion switch, drag/click and drag-and-drop traps."),
    "project/cull-bounds-zsc.md": ("Cull bounds come from geometry, not the ZSC", "Broken ZSC AABBs, MakeAABBFromObject engine query, ZMS version units, 4-plane frustum, audit-zsc-bounds.py."),
    "project/depth-buffer-precision.md": ("Depth buffer precision", "D16 -> D24 negotiation, near-plane math, log format codes, no depth bias, set-camera-near-plane.py."),
    "project/coplanar-placements.md": ("Coplanar map-object placements flicker", "Zero-separation duplicate placements, fix-coplanar-object-overlaps.py, never delete records, back-to-back faces."),
    "project/object-lightmaps-atlas.md": ("Object lightmaps are a gutterless atlas", "Why mip bleeding cannot occur (INIT.LUA setMipmapLevel(3)) and when it could."),
    "project/missing-assets-degrade.md": ("Missing assets must degrade, not kill", "Four VFS/engine defects on the missing-file path; ZZ_LOG varargs trap; failed-load recording; manager re-queue."),
    "project/missing-npc-row-degrade.md": ("A missing NPC row must degrade, not kill", "Change_CHAR on blank LIST_NPC rows, DeleteBoneEFFECT by-value bug, heap-corruption dumps, audit-ai-monster-refs.py."),
    "project/ai-skill-reference-failures.md": ("AI skill references: five failure classes", "Blank/colliding skill ids, release-clip events, slot layouts, column 88/90 status, impossible level windows; import-monster-skills.py and audit-ai-skill-refs.py."),
    "project/debugging-client-crash.md": ("Debugging a client crash or freeze", "debug-client-crash.ps1, cdb working dir, non-invasive attach, client.log vs error.txt, stale-build artifacts."),
    "project/terrain-streaming-performance.md": ("Terrain streaming performance (summary)", "Lead time vs queue depth, insert cap vs load budget, null-neighbour map tile crash, spike logs."),
    "project/shared-data-and-item-encoding.md": ("Shared data types and item encoding", "src/common/shared; 5+11-bit item header; type/id initializer; package boxes (class 322)."),
    "project/buffs-passives-percent.md": ("Buffs and passives are percentage-based", "Rate vs flat columns, pre-buff base stat, heals stay flat, HIT stays flat, vtable change warning."),
    "project/monster-balance-level-gate.md": ("Monster balance and the level gate", "Level-proportional hit gate (1.05), skill gate, (ATK-DEF+250), drop cutoff, balance-pass ordering."),
    "project/oro-667-import.md": ("Oro is the 667 build's Oro", "remove-oro/import-oro-667, missing 667 AI/CON/MOV, CXE dialogs, attack-speed units, NPC_TYPE, summon closure, drops."),
    "project/skaaj-import.md": ("Skaaj (Jrose cat-folk island)", "import-skaaj.py, blank sky column, quest switch 90, global trigger names, QEX1 overrides, I_NUM STL."),
    "project/data-repair-tooling.md": ("Data repair tooling", "Catalogue of idempotent data-fix scripts and the failure each addresses; STL key grep trap; .bak in bakes."),
    "project/vfs-offset-limit.md": ("The .vfs offset limit (2 GB -> 4 GB)", "Unsigned offsets, vfread/vfseek fixes, pack.ps1 + verify-vfs.py, rose_N.vfs rollover."),
    "project/item-import-tooling.md": ("Item import tooling", "import-item.py, --art-only safety, icon tools, skill-tree art, ZSC/field model indices."),
    "project/npc-dialog-qex1.md": ("NPC dialog quest options (.CON QEX1 appendix)", "Lua 4 bytecode dialogs and the QEX1 appendix mechanism."),
    # ---- src/client/CLAUDE.md --------------------------------------------
    "client/overview.md": ("Client overview", "Subsystem directories, important classes, client networking."),
    "client/combat-core-and-queue.md": ("Client combat: core model and damage queue", "DamageEvent fields, per-defender queue, Hitted timing, crowd catch-up, projectile timing, hard-control interrupts."),
    "client/combat-preempted-and-remote-casts.md": ("Client combat: pre-empted swings and remote casts", "Self-pre-empted swings, remote cast held behind swing, cast watchdog, GSV_SKILL_START validation, hit reactions removed."),
    "client/combat-orphan-swing-sweep.md": ("Client combat: orphan swing sweep", "Resolving unpresentable confirmed swings; grace period measurement; misses that are not this bug."),
    "client/combat-projectile-classification.md": ("Client combat: projectile classification", "Ranged skill classification, target-bound skills, fireless motions, bow/gun frames with nothing to fire, presentation_kind agreement."),
    "client/combat-hp-authority-and-healing.md": ("Client combat: HP authority and healing", "Reconcile_HP, announced heals, StatusTick exception, checkpoint supersession and staleness, digits vs HP."),
    "client/combat-death.md": ("Client combat: death presentation", "Explicit death, lethal legacy payloads, pending-death backstop, spectator stale-death fallback."),
    "client/combat-phantom-swings.md": ("Client combat: phantom swings and position drift", "Self-looping attack motions, MISS presentation, one animation per confirmed swing, reverted fixes."),
    "client/combat-drain-and-stranding.md": ("Client combat: drain-on-death and stranded events", "Attacker dies mid-swing, no client damage math, orphan sweep as self-healing, synthetic event ids, key methods."),
    "client/ai-chase-and-attack-speed.md": ("Client AI chase movement and attack speed", "CMD_MOVE with target paths; server-owned swing cadence and speed sync."),
    "client/cart-castle-gear.md": ("Cart / castle gear combat and visuals", "Rider vs cart routing, damage re-keying, first mounted attack, inverted union fields, skeleton fallback."),
    "client/terrain-streaming-queues-and-patches.md": ("Terrain streaming: queues, hysteresis, patch keep-alive", "Load/unload queues, deferred unloads, proximity ring, insert caps."),
    "client/terrain-cull-bounds-and-patch-index.md": ("Terrain: object cull bounds and patch index staleness", "MakeAABBFromObject details, far-insert test, patch pointer staleness."),
    "client/terrain-prefetch-and-vfs-reads.md": ("Terrain: chunk prefetch and buffered VFS reads", "CMapFilePrefetcher through the VFS, six files per cell, 32 KB read-ahead, vfs_buffer_tests."),
    "client/frame-hitch-campaign-2026-08-28.md": ("Frame-hitch campaign 2026-08-28", "Measured route results, causes, measurement traps, vsync interpretation."),
    "client/chunk-hitch-and-load-budgets.md": ("Chunk-display hitch and load budgets", "Lead-time table, TERRAIN_INSERTS_PER_FRAME, LOAD_BUDGET_US, rejected per-item weight fix."),
    "client/streaming-diagnostics-and-spike-log.md": ("Streaming diagnostics and the whole-frame spike log", "MapIO/Flush rows, instrumentation traps, FRAME_SPIKE_LOG_MS format and phase semantics."),
    "client/character-spawn-and-texture-create.md": ("Character spawn (motion parser) and texture create costs", "Bulk motion reads, spawn breakdown, missing DDS mip chains, add-dds-mipmaps.py, vfgetdata trap, lightmap exclusion."),
    "client/loading-screen-cache-warming.md": ("Loading-screen cache warming", "CACHE_WARM_MB measurements, per-zone budget, cold-cache measurement, traps."),
    "client/overhead-names-cnamebox.md": ("Overhead name drawing (CNameBox)", "Sprite batch, boxed drawFont rect above origin, clan row, the not-understood rule."),
    "client/bone-particles.md": ("Bone particle budgeting, batching and emit accumulator", "Tiers, batching conditions, spawn-debt accumulator rules."),
    "client/input-pvp-summon-control.md": ("Input dispatch, PVP enemy verdict, summon control", "ProcWndMsgInstant vs queued path, right-drag camera, IsEnemy, CTRL+click summon orders."),
    "client/summon-info-panel.md": ("Summon info panel", "Visibility, gauge lifecycle, server-scaled stats, max HP from packet, drag."),
    "client/monster-inspector.md": ("Monster Inspector", "Client-only window skill, drop list walk, live HP, 3D preview pipeline, input, background art."),
    "client/npc-quest-icons.md": ("NPC overhead quest icons", "QSD trigger harvesting, dialog probe, timed quests, refresh, draw, sprites, deploy gotcha, status."),
    "client/chat-links-and-item-preview.md": ("Chat item links and item preview panel", "Wire token, send/display paths, tooltips; Alt+click preview, puppet, camera mirror."),
    "client/damage-meter.md": ("Damage meter (/dps)", "Data core tap, attribution fields, classification, dedup, segments, UI, credit, limits."),
    "client/rmlui-layer.md": ("RmlUi layer (client implementation)", "Files, hooks, device lifetime trap, input arbitration, rendering notes, asset loading."),
    "client/model-node-and-dummy-indices.md": ("Model node lifetime and dummy indices", "NULL m_hNodeMODEL on live objects, getPosition/getVisibility traps, ResolveDummyIDX, INVALID_DUMMY_POINT_NUM."),
    "client/frame-timing-device-screen-modes.md": ("Frame timing, device, swap chain and screen modes", "timeBeginPeriod, 9Ex rules, present parameters, three screen modes and predicates, window sizing."),
    "client/build-launch-logging.md": ("Client build, conventions, launch and diagnostic logging", "Dependencies, launch flags, LOG LEVEL switch, client.log behaviour."),
    # ---- src/sho_gameserver/CLAUDE.md ------------------------------------
    "gameserver/overview.md": ("Game server overview, configuration, dependencies", "Architecture, source layout, networking, zones, server.toml, dependencies, conventions."),
    "gameserver/combat-flow-and-packet-rules.md": ("Game server combat flow and presentation packet rules", "Apply_DAMAGE flow, repeat attack no-op, PVP ally rule, DamageEvent/CombatSwing rules, speed fields."),
    "gameserver/ai-guard-npc-rows-skills-status.md": ("Game server AI guard, junk NPC rows, skill damage, status effects", "AIACT24 guard, junk NPC row degrade, projectile skill tagging, status success bits."),
    "gameserver/summon-control.md": ("Game server summon control", "Recv_cli_SUMMON_CONTROL, manual-order window, PlayerOrderMoveTo."),
    "gameserver/walkability-mov.md": ("Walkability and missing .MOV files", "Blocked-by-default grid, leash/wander gating, per-tile open fallback, affected zones."),
    # ---- xadet/rose-online-map-editor/CLAUDE.md --------------------------
    "map-editor/overview-build-architecture.md": ("Map editor overview, build/deploy, architecture, data formats", "Vendored xadet editor, VS2019 build, deploy to data/, manager layout, file types."),
    "map-editor/debugging-and-editing-guidelines.md": ("Map editor debugging workflow and editing guidelines", "Log-first debugging, narrow changes, optional assets, save semantics and no undo."),
    "map-editor/compatibility-fixes.md": ("Map editor compatibility fixes already made", "Karkia/Skaaj IFO save fix, LIT ordinals, sky column, MOV painting, precision, morph flags, lightmap sharing."),
    "map-editor/verification-checklist.md": ("Map editor verification checklist", "Manual checks for map load, spawn UI and object/terrain changes."),
}

END = None  # "to the last line"
PLAN = {
    "CLAUDE.md": [
        (1, 22, "project/overview-and-architecture.md"),
        (23, 54, "project/build-system-and-pitfalls.md"),
        (55, 94, "project/project-structure.md"),
        (95, 108, "project/database-and-networking.md"),
        (109, 135, "project/conventions-and-dev-environment.md"),
        (136, 148, "project/combat-damage-presentation.md"),
        (149, 163, "project/rendering-device-d3d9ex.md"),
        (164, 170, "project/bone-particle-budget.md"),
        (171, 209, "project/monster-spawning-regen.md"),
        (210, 212, "project/overview-and-architecture.md"),
        (213, 233, "project/client-only-features.md"),
        (234, 284, "project/rmlui-ui-layer.md"),
        (285, 331, "project/cull-bounds-zsc.md"),
        (332, 398, "project/depth-buffer-precision.md"),
        (399, 446, "project/coplanar-placements.md"),
        (447, 469, "project/object-lightmaps-atlas.md"),
        (470, 479, "project/missing-assets-degrade.md"),
        (480, 527, "project/missing-npc-row-degrade.md"),
        (528, 654, "project/ai-skill-reference-failures.md"),
        (655, 664, "project/debugging-client-crash.md"),
        (665, 673, "project/terrain-streaming-performance.md"),
        (674, 683, "project/shared-data-and-item-encoding.md"),
        (684, 728, "project/buffs-passives-percent.md"),
        (729, 748, "project/monster-balance-level-gate.md"),
        (749, 763, "project/oro-667-import.md"),
        (764, 797, "project/skaaj-import.md"),
        (798, 815, "project/data-repair-tooling.md"),
        (816, 835, "project/vfs-offset-limit.md"),
        (836, 844, "project/item-import-tooling.md"),
        (845, 847, "project/npc-dialog-qex1.md"),
        (848, END, "project/build-system-and-pitfalls.md"),
    ],
    "src/client/CLAUDE.md": [
        (1, 39, "client/overview.md"),
        (40, 49, "client/combat-core-and-queue.md"),
        (50, 55, "client/combat-preempted-and-remote-casts.md"),
        (56, 59, "client/combat-orphan-swing-sweep.md"),
        (60, 64, "client/combat-projectile-classification.md"),
        (65, 73, "client/combat-hp-authority-and-healing.md"),
        (74, 78, "client/combat-death.md"),
        (79, 86, "client/combat-phantom-swings.md"),
        (87, 94, "client/combat-drain-and-stranding.md"),
        (95, 116, "client/ai-chase-and-attack-speed.md"),
        (117, 134, "client/cart-castle-gear.md"),
        (135, 157, "client/terrain-streaming-queues-and-patches.md"),
        (158, 173, "client/terrain-cull-bounds-and-patch-index.md"),
        (174, 189, "client/terrain-prefetch-and-vfs-reads.md"),
        (190, 221, "client/frame-hitch-campaign-2026-08-28.md"),
        (222, 249, "client/chunk-hitch-and-load-budgets.md"),
        (250, 272, "client/streaming-diagnostics-and-spike-log.md"),
        (273, 312, "client/character-spawn-and-texture-create.md"),
        (313, 321, "client/streaming-diagnostics-and-spike-log.md"),
        (322, 353, "client/loading-screen-cache-warming.md"),
        (354, 363, "client/overhead-names-cnamebox.md"),
        (364, 397, "client/bone-particles.md"),
        (398, 421, "client/input-pvp-summon-control.md"),
        (422, 431, "client/summon-info-panel.md"),
        (432, 443, "client/monster-inspector.md"),
        (444, 461, "client/npc-quest-icons.md"),
        (462, 487, "client/chat-links-and-item-preview.md"),
        (488, 501, "client/damage-meter.md"),
        (502, 554, "client/rmlui-layer.md"),
        (555, 634, "client/model-node-and-dummy-indices.md"),
        (635, 692, "client/frame-timing-device-screen-modes.md"),
        (693, END, "client/build-launch-logging.md"),
    ],
    "src/sho_gameserver/CLAUDE.md": [
        (1, 57, "gameserver/overview.md"),
        (58, 92, "gameserver/combat-flow-and-packet-rules.md"),
        (93, 108, "gameserver/ai-guard-npc-rows-skills-status.md"),
        (109, 125, "gameserver/overview.md"),
        (126, 141, "gameserver/summon-control.md"),
        (142, 194, "gameserver/walkability-mov.md"),
        (195, END, "gameserver/overview.md"),
    ],
    "xadet/rose-online-map-editor/CLAUDE.md": [
        (1, 127, "map-editor/overview-build-architecture.md"),
        (128, 162, "map-editor/debugging-and-editing-guidelines.md"),
        (163, 294, "map-editor/compatibility-fixes.md"),
        (295, END, "map-editor/verification-checklist.md"),
    ],
    # The inherited AGENTS.md is preserved verbatim inside the unavailable-
    # knowledge record, because its only substantive content is the pointer
    # to an external memory index that no longer exists on this machine.
    "AGENTS.md": [
        (1, END, "@doc/ai/UNAVAILABLE_KNOWLEDGE.md"),
    ],
}

LINK_RE = re.compile(rb"\]\(([^)\s]+)\)")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def split_lines(b):
    parts = b.split(b"\n")
    lines = [p + b"\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])  # no trailing newline on the last line
    return lines


def is_external(target):
    t = target.decode("utf8", "replace")
    return t.startswith(("http://", "https://", "mailto:", "#")) or ":" in t.split("/")[0] and not t.startswith(".")


def split_anchor(t):
    for sep in ("#",):
        if sep in t:
            i = t.index(sep)
            return t[:i], t[i:]
    return t, ""


def exists(repo_path):
    return os.path.exists(os.path.join(ROOT, repo_path))


def relocate_links(text, src_dir, dest_dir):
    """Return (new_text, [ {orig, new, repaired} ... ]) in order of appearance."""
    records = []

    def sub(m):
        target = m.group(1)
        if is_external(target):
            return m.group(0)
        t = target.decode("utf8")
        path, anchor = split_anchor(t)
        if not path:
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(src_dir, path))
        repaired = False
        if not exists(resolved) and exists(posixpath.normpath(path)):
            resolved = posixpath.normpath(path)
            repaired = True
        new = posixpath.relpath(resolved, dest_dir) + anchor
        records.append({"orig": t, "new": new, "repaired": repaired,
                        "target": resolved, "target_exists": exists(resolved)})
        return b"](" + new.encode("utf8") + b")"

    return LINK_RE.sub(sub, text), records


def fence_balanced(seg_bytes):
    n = sum(1 for l in split_lines(seg_bytes) if l.lstrip().startswith(b"```"))
    return n % 2 == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing topic files")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rev = git("rev-parse", "HEAD").decode().strip()
    os.makedirs(os.path.join(ROOT, ARCHIVE_DIR), exist_ok=True)

    manifest = {"captured": DATE, "revision": rev, "files": []}
    mapping = {"date": DATE, "revision": rev, "archive_dir": ARCHIVE_DIR, "sources": []}
    topics = {}  # dest -> list of (src, a, b, bytes, link records)

    for src, arch_name in SOURCES.items():
        arch = f"{ARCHIVE_DIR}/{arch_name}"
        cur = open(os.path.join(ROOT, src), "rb").read()
        arch_abs = os.path.join(ROOT, arch)
        if os.path.exists(arch_abs):
            data = open(arch_abs, "rb").read()
            if sha256(data) != sha256(cur) and not args.force:
                # The live file was already replaced by the compact guide:
                # the archive is the source of truth from here on.
                pass
        else:
            data = cur
            if not args.dry_run:
                with open(arch_abs, "wb") as f:
                    f.write(data)
        blob = git("rev-parse", f"HEAD:{src}").decode().strip()
        head_bytes = git("show", f"HEAD:{src}")
        manifest["files"].append({
            "original_path": src, "archive": arch, "bytes": len(data),
            "sha256": sha256(data), "git_blob": blob,
            "matches_HEAD": head_bytes == data,
        })

        lines = split_lines(data)
        n = len(lines)
        plan = [(a, n if b is None else b, d) for a, b, d in PLAN[src]]
        covered = sorted((a, b) for a, b, _ in plan)
        expect = 1
        for a, b in covered:
            assert a == expect, f"{src}: gap/overlap at line {expect} (next segment starts {a})"
            assert b >= a
            expect = b + 1
        assert expect == n + 1, f"{src}: plan ends at {expect-1}, file has {n} lines"

        src_dir = posixpath.dirname(src)
        segs = []
        for a, b, d in plan:
            seg = b"".join(lines[a - 1:b])
            if not fence_balanced(seg):
                sys.exit(f"{src}:{a}-{b}: segment splits a code fence")
            if d.startswith("@"):
                dest = d[1:]
            else:
                dest = f"{TOPICS}/{d}"
            dest_dir = posixpath.dirname(dest)
            new, links = relocate_links(seg, src_dir, dest_dir)
            heads = [l.decode("utf8").strip() for l in lines[a - 1:b]
                     if re.match(rb"^#{1,6} ", l)]
            segs.append({"lines": [a, b], "dest": dest, "sha256": sha256(seg),
                         "bytes": len(seg), "headings": heads, "links": links})
            topics.setdefault(dest, []).append((src, a, b, new, sha256(seg)))
        mapping["sources"].append({"path": src, "archive": arch,
                                   "sha256": sha256(data), "lines": n, "segments": segs})

    # ---- write topic files -------------------------------------------------
    written = []
    for dest, parts in topics.items():
        if dest.startswith(TOPICS + "/"):
            key = dest[len(TOPICS) + 1:]
            title, _summary = TOPIC_META[key]
            depth = key.count("/") + 1  # doc/ai/topics/<area>/ -> doc/ai
            up = "../" * depth
            prov = "; ".join(f"`{s}` lines {a}-{b}" for s, a, b, _, _ in parts)
            archs = sorted({SOURCES[s] for s, *_ in parts})
            out = [f"# {title}\n", "\n",
                   f"> **Provenance:** moved verbatim on {DATE} from {prov} (revision `{rev[:7]}`).\n",
                   "> Original bytes: " + ", ".join(f"[`{x}`]({up}archive/{DATE}/{x})" for x in archs) + ".\n",
                   f"> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the {DATE}\n",
                   "> migration; confirm against the code before relying on a claim. Mentions of \"root/client/server\n",
                   f"> `CLAUDE.md`\" inside the text mean the pre-{DATE} guides; find sections via [INDEX]({up}INDEX.md).\n",
                   "> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by\n",
                   "> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.\n",
                   "\n"]
            for s, a, b, new, h in parts:
                out.append(f"<!-- verbatim:begin src={s} lines={a}-{b} sha256={h} -->\n")
                out.append(new.decode("utf8"))
                if not new.endswith(b"\n"):
                    out.append("\n")
                out.append("<!-- verbatim:end -->\n\n")
            out.append("## Updates\n\n_None yet. Add dated entries (newest last) with source paths, revision and verification status._\n")
            path = os.path.join(ROOT, dest)
            if os.path.exists(path) and not args.force:
                sys.exit(f"refusing to overwrite {dest} (use --force)")
            if not args.dry_run:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf8", newline="\n") as f:
                    f.write("".join(out))
            written.append(dest)
        else:
            # Embedded into a hand-written record: emit the block to stdout-ready file.
            blk = []
            for s, a, b, new, h in parts:
                blk.append(f"<!-- verbatim:begin src={s} lines={a}-{b} sha256={h} -->\n")
                blk.append(new.decode("utf8"))
                blk.append("<!-- verbatim:end -->\n")
            frag = os.path.join(ROOT, ARCHIVE_DIR, "..", "..", "migration", f"{DATE}-embedded-{os.path.basename(dest)}.frag")
            if not args.dry_run:
                os.makedirs(os.path.dirname(frag), exist_ok=True)
                with open(frag, "w", encoding="utf8", newline="\n") as f:
                    f.write("".join(blk))
            print(f"embedded block for {dest} written to {os.path.relpath(frag, ROOT)} -- paste it in by hand")

    # ---- mapping + manifest -----------------------------------------------
    if not args.dry_run:
        os.makedirs(os.path.join(ROOT, os.path.dirname(MAPPING_JSON)), exist_ok=True)
        with open(os.path.join(ROOT, MAPPING_JSON), "w", encoding="utf8", newline="\n") as f:
            json.dump(mapping, f, indent=1, ensure_ascii=False)
            f.write("\n")
        with open(os.path.join(ROOT, ARCHIVE_DIR, "manifest.json"), "w", encoding="utf8", newline="\n") as f:
            json.dump(manifest, f, indent=1)
            f.write("\n")
        md = [f"# Source-to-destination mapping ({DATE})\n", "\n",
              f"Generated by `scripts/ai-docs-migrate-{DATE}.py` at revision `{rev[:7]}`. Every line of every\n",
              "listed source is in exactly one row. Line ranges refer to the archived copy (identical to the\n",
              f"file at `{rev[:7]}`). Machine-readable form, with per-link rewrite records: [{os.path.basename(MAPPING_JSON)}]({os.path.basename(MAPPING_JSON)}).\n",
              "Verify with `python scripts/verify-ai-docs.py`.\n", "\n"]
        for s in mapping["sources"]:
            md.append(f"## `{s['path']}` ({s['lines']} lines, sha256 `{s['sha256'][:16]}...`)\n\n")
            md.append("| Lines | Bytes | Headings in range | Destination | Link rewrites |\n|---|---|---|---|---|\n")
            for g in s["segments"]:
                hd = "<br>".join(h.replace("|", "\\|") for h in g["headings"]) or "_(continuation, no heading)_"
                rel = posixpath.relpath(g["dest"], posixpath.dirname(MAPPING_MD))
                nl = len(g["links"])
                rep = sum(1 for x in g["links"] if x["repaired"])
                lk = f"{nl}" + (f" ({rep} repaired)" if rep else "")
                md.append(f"| {g['lines'][0]}-{g['lines'][1]} | {g['bytes']} | {hd} | [{g['dest'][len('doc/ai/'):]}]({rel}) | {lk} |\n")
            md.append("\n")
        with open(os.path.join(ROOT, MAPPING_MD), "w", encoding="utf8", newline="\n") as f:
            f.write("".join(md))
    print(f"{len(written)} topic files; mapping -> {MAPPING_JSON}")


if __name__ == "__main__":
    main()
