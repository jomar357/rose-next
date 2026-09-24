# Cart / castle gear combat and visuals

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 117-134 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=117-134 sha256=265b6a9075c6fde47cf8c9f7a0da79aecaa913f8b862dcd2ca3fa6c224603e76 -->
### Cart / Castle Gear Combat

When `GetPetMode() >= 0`, combat state is split between the rider avatar and the `CObjCART`:

- `CObjCHAR::SetCMD_ATTACK` must route mounted attacks to `m_pObjCART->SetCMD_ATTACK` before the rider-side `CanApplyCommand()` gate. If the rider queues the first post-mount attack on itself, the server can already be processing `CLI_ATTACK` while the client still looks idle.
- Server still attributes some legacy damage packets to the rider (user index). `Recv_gsv_DAMAGE` re-keys the damage event to the cart's client index when `pAtkOBJ->GetPetMode() >= 0 && pAtkOBJ->IsUSER()`. Damage must only be queued once under that canonical cart/castle-gear attacker index.
- Legacy damage timeout and missed-hit recovery are retired for live combat. If a hit frame has no matching server event, no presentation occurs.
- `ActionInFighting` case 21 and the rider-side `ActionBow` / `ActionGun` attack frames must skip `Hitted()` / projectile spawning when `GetPetMode() >= 0 && !IsPET()`. The rider's attack motion is visual only; the cart/castle gear is the source of truth for hit timing.
- The first mounted attack after `Drive Cart` can fail if the player attacks before moving even once. Root cause: cart runtime movement state was only being fully primed by mounted move flow. `CreateCart` and `SetCMD_PET_ATTACK` now copy the rider's move speed / move mode into the cart up front so the first attack can immediately path toward the target.
- `CObjCART::Get_fAttackSPEED()` falls back to the rider's `stats.attack_speed` (then a hard 100 default) because the cart's own `stats.attack_speed` is never synced from the server. A 0 attack speed produces motion speed 0 → NaN bone transforms → `zz_octree` min <= max assertion crash.

### Cart / Castle Gear Visual Loading

Cart visual creation (`CreateCart` / `CreateCartFromMyData` → `CObjCART::Create`) has several silent early-returns. Key gotchas:

- The union at `cobjchar.h` around line 1348 has **inverted** field names vs `RIDE_PART_*` indices: `m_sEngineIDX` is actually slot 0 (BODY) and `m_sBodyIDX` is slot 1 (ENGINE). Rest of the client follows the same inversion, so data round-trips — but it reads wrong.
- When `list_pat_skeleton.stb` has no skeleton entry for a cart body, `io_basic.cpp` synthesizes one from the body-item part data. Without this fallback, cart creation returns false while the server-side drive-mode speed is already applied (`recvpacket.cpp` unconditionally writes `move_speed` from the `TOGGLE_TYPE_DRIVE` packet before `RideCartToggle(true)` runs) — the player ends up moving at cart speed with no cart model.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
