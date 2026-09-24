# Bone particle budgeting, batching and emit accumulator

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 364-397 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=364-397 sha256=eb39d4172154e07aeb8e3cebb04d260816bfafb40af39b9aaf63f6cb78a6e87f -->
## Bone-Attached Particle Budgeting

Character model bone effects created by `CCharMODEL::CreateBoneEFFECT` are passive cosmetic effects and are registered with `CBoneEffectBudget` (`BoneEffectBudget.cpp/h`) using owner, NPC id, bone index, and effect hash. Registration is intentionally narrow: do not add skill particles, hit effects, bullets, terrain/weather effects, weapon effects, or general `g_pEffectLIST` effects to `BoneFx`.

The budget manager runs once per main-frame update after scene update. It prioritizes player/current target, visible + in-frustum owners, nearest distance to avatar, then duplicate groups. The budget is cost-based (`configured particle capacity`, `configured emit rate`, emitter count, active particles) rather than raw effect-count based. Duplicate full-tier groups are capped per NPC/effect signature, so several copies of the same monster can still show an aura while later duplicates degrade gracefully. After additive particle texture batching proved stable in-game, the current relaxed budget is 480 runtime particles, 360 emit/sec, and 3 full duplicate groups per same NPC/effect signature.

Particle tiers are stored on `CEffect` and applied particle-only:
- `Full`: normal emit/update.
- `Reduced`: emit scale 0.35, runtime cap 40% with a minimum of 8 particles per emitter.
- `Minimal`: emit scale 0.08, runtime cap 12% clamped to 2-6 particles per emitter, update every 150 ms.
- `Off`: stop emitter and clear live particles.

`CEffect::StartEffect()` must preserve the stored particle tier, especially `Off`, so relink/start paths do not restart disabled particles. Mesh and sound parts inside the same effect stay unchanged. Engine-side runtime caps live in `zz_particle_emitter` / `zz_particle_event_sequence`; when caps are lowered, particles above the cap are deleted so old full-tier particles do not keep updating.

The debug HUD line starts with `BoneFx:` and reports groups, effects, emitters, active particles, runtime cap, configured emit rate, tier counts, and top NPC id. Use it to validate cases like Frozen Thorn (`NPC 1528`) without relying on the generic `Fx` line.

## Bone Particle Texture Batching

`CCharMODEL::CreateBoneEFFECT` also marks its `CEffect` particles with `SetParticleBatchRenderHint(true)`. This is the only client opt-in path for particle batching; gameplay particles and normal world effects must not be hinted unless they are separately audited.

The engine batches only hinted particle emitters that are additive-safe (`D3DBLENDOP_ADD` with destination blend `D3DBLEND_ONE`) and whose sequences can share the same texture/render-state key. Mixed or incompatible emitters fall back to the original render path. This was validated with Frozen Thorn (`NPC 1528`) aura particles, which use additive `_shine_03.dds` sequences and previously paid roughly one draw call per particle.

Batching lives in `zz_particle_emitter::RenderParticleListWithBatching` and sequence vertex append helpers in `zz_particle_event_sequence`. It writes world-space particle vertices into shared dynamic buffers, then draws one or more chunks per texture/render-state group. The debug HUD line starts with `PartBatch:` and reports batch groups, particles, draw calls, fallback count, and estimated saved draw calls.

## Particle Emit-Accumulator (death-then-spawn timing)

`zz_particle_event_sequence::update` accumulates fractional emit budget in `m_fNumNewPartsExcess` and spawns when it crosses 1.0. The accumulator is **only consumed when a spawn actually succeeds** — i.e., inside the `while (m_fNumNewPartsExcess >= 1.0f && free_elements > 0 && ...)` loop, the `m_fNumNewPartsExcess -= 1.0f` happens immediately after a successful `CreateNewParticle`. This matches the Rust port's pattern at `rose-offline-client/src/systems/particle_sequence_system.rs:336-394`.

Do not restore the older pattern that decremented the accumulator unconditionally when it crossed 1.0 regardless of whether `free_elements` allowed the spawn. That bug produced a visible synchronised flash on every cosmetic emitter capped at `num_particles=1` (smoke-on-buildings in town hubs), because the emit accumulator's "ready to spawn" moment drifted out of phase with the death frame — sometimes the spawn fired the same frame the slot freed (no gap), but more often the next spawn-trigger was 1-5 frames away, leaving the slot empty for ~16-83 ms per cycle. SMOKE_04 on JZ01 chimneys was the canonical repro.

For finite emitters (`m_Loops > 0`), `remaining_for_loops` enforces the `m_Loops * m_iNumParticles` cap and the accumulator is clamped to that remaining budget so it cannot overshoot after the loop completes.

`m_fNumNewPartsExcess` is allowed to grow beyond 1.0 while the slot is full, and that is correct — it preserves the "spawn debt" so the replacement particle fires on the death frame instead of waiting for the accumulator to refill from zero. Don't add a cap unless you have a measured runaway case; for an infinite emitter at `emit_rate * life` the steady-state ceiling is bounded.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
