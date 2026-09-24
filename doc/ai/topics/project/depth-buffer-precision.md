# Depth buffer precision

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 332-398 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=332-398 sha256=fd0f91c3f762640b942e45d42259e6f30f71134cddc06e5b9a1b6c4b10421a2e -->
### Depth Buffer Precision (Engine)

The device used a **16-bit depth buffer** (`D3DFMT_D16`, hardcoded), and the avatar
camera's near plane is **1 m** against a far plane of 800 m (`LIST_CAMERA` columns 5
and 6, multiplied by 100 into cm by `ApplyCameraOption`, then by `ZZ_SCALE_IN` into
engine metres). Resolvable depth separation is `z^2*(f-n)/(n*f*2^bits)`, which at 16
bits is 3.8 cm at 50 m, 15 cm at 100 m and **61 cm at 200 m** — so any two surfaces
mounted closer than that collapsed into one depth bucket and z-fought. On screen it
read as black bands crawling across a distant object and resolving cleanly as you
walked in, because the loser of the fight is usually an unlit interior or backside.
It did not reproduce in the xadet map editor, which is XNA and defaults to Depth24.

`initialize()` now probes `D24S8 -> D24X8 -> D16` with `CheckDeviceFormat` +
`CheckDepthStencilMatch` and stores the winner in `depthstencil_format`. 24 bits is
256x finer, which pushes the onset past the far plane for any realistic mounting gap.

Things that will bite:

- **The near plane is the whole story; the far plane is nearly irrelevant.** With
  `f >> n` the expression collapses to `z^2/(n*2^bits)`. Pulling the far plane from
  800 m in to 250 m changes precision by 0.4%; raising the near plane from 1 m to 5 m
  improves it 5x. Reach for `n` or for bit depth, never for `f`.
- **Only the log tells you which format you got.** `r_d3d: depth-stencil format = N`
  — 75 is D24S8, 77 is D24X8, 80 is the old D16. A probe that silently falls back
  looks exactly like a fix that did not work. Same trap as the D3D9Ex toggle.
- `DEPTH_STENCIL_FORMAT` is now only the fallback seed. Every consumer reads the
  member `depthstencil_format`, including the offscreen z-surface in
  `restore_device_objects()` — that site used the macro directly and would otherwise
  have silently disagreed with the device.
- The FSAA check validates the sample type against the **backbuffer and the depth
  format**. Checking only the backbuffer was harmless while the depth format was a
  constant and is not once it varies: a mismatch fails device creation outright
  rather than degrading to no FSAA.
- Nothing in the engine touches the stencil buffer (no stencil render states, `Clear`
  never passes `D3DCLEAR_STENCIL`), so D24X8 is as good as D24S8. Both are probed
  because driver support for the two is not identical.
- Force the old buffer for A/B testing with `[VIDEO] DEPTH24=0` in `rose-next.ini` or
  `ROSE_NO_DEPTH24=1` in the environment — and confirm via the log.
- There is **no depth bias anywhere**. `zz_renderer_d3d::set_depthbias` is declared
  and defined but never called, and would not work if it were: D3D9's
  `D3DRS_DEPTHBIAS` takes a float bit-pattern, so its `int` parameter turns any small
  value into a denormal ~= 0. Do not reach for it to paper over a z-fight.

Which assets were affected: the failure needs two mesh parts of one object stacked
closer than the depth resolution. The recognisable family is shop signs, statues, and
the `road01`/`road01top` overlay pairs — that naming convention is the real tell, and
Junon Polis has the most of them.

A one-off scan for part pairs whose world AABBs overlap widely on two axes and by
under 25 cm on the third flagged 70 of the 14618 map objects. **Treat that as
corroboration for why only a few assets showed the artefact, not as a predictor**, and
do not rebuild it as a tool: an AABB overlap is not a surface separation (the boxes of
a concave part overlap where the surfaces do not), the thresholds were chosen to fit
the reported case rather than derived, and at 24 bits the separation that still fights
is under ~0.3 cm at any distance we draw — two orders of magnitude below what that
scan measured. If a similar artefact ever survives the format check in the log,
measure real mesh-surface separation; the AABB proxy will mislead you.

To confirm a suspected z-fight from data alone, with no rebuild:
`scripts/set-camera-near-plane.py` raises the near plane across all six `LIST_CAMERA`
rows (`--dry-run` / `--verify` / `--restore`). Precision scales with `n` but onset
*distance* only with `sqrt(n)`, so 1 -> 5 moves the artefact out ~2.2x rather than
removing it — a partial retreat is the confirming signal, not a weak result. The
follow camera's minimum distance is 1.0 m, so a 5 m near plane clips the avatar at
full zoom-in; that is expected, not a second bug. It writes no sidecar next to the
STB on purpose, since `pack.rs` would bake one into the `.vfs`.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
