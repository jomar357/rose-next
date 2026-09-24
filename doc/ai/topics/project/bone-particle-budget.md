# Bone particle budget (summary)

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 164-170 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=164-170 sha256=fffcd33646abcd3ff0b3e02c56eeb739e8cd7cbe87ce411e896dc802787e8772 -->
### Bone Particle Budget (Client/Engine)
Cosmetic character bone effects created by `CCharMODEL::CreateBoneEFFECT` are tracked separately by `CBoneEffectBudget` (`src/client/BoneEffectBudget.*`). This budget exists for passive bone-attached aura/loop effects only; skill, hit, projectile, terrain, weather, weapon, and normal world effects must not be registered there.

The manager budgets visible bone-effect groups by estimated particle capacity and emit rate, then applies particle-only tiers through `CEffect::SetParticleTier`: Full, Reduced, Minimal, Off. Mesh and sound components remain unchanged. Runtime caps and emit scaling are enforced in the engine particle emitter/sequence code, so degraded/off tiers are actually cheaper instead of only hidden. Current relaxed budgets are 480 runtime particles, 360 emit/sec, and 3 full duplicate groups per same NPC/effect signature. The debug HUD exposes this as the `BoneFx:` line.

Additive-compatible bone particles also opt into safe texture batching through `CEffect::SetParticleBatchRenderHint`, forwarded to `zz_particle_emitter`. Only `CreateBoneEFFECT` enables this hint. The engine batches hinted additive sequences by texture/render state in `zz_particle_emitter::RenderParticleListWithBatching`; incompatible particles and all non-bone effects use the old render path. The debug HUD exposes batching as the `PartBatch:` line.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
