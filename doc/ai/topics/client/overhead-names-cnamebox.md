# Overhead name drawing (CNameBox)

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 354-363 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=354-363 sha256=5f32a8acaf0cc81f36f8426242f022a6dc37a222916af94b6f09171b658f5543 -->
## Overhead Name Drawing (`CNameBox`)

Names are drawn inside the sprite batch that `CGameStateMain::Render_GameMENU` opens around `g_pViewMSG->Draw()`, so `drawFont`'s `bUseSprite` argument must be **true** there. The `false` overload takes a branch that calls `begin_sprite` itself and asserts no batch is active (`zz_font_d3d.cpp:165`); calling it inside the batch corrupts the sprite state and the damage shows up later as an unrelated `sprite_began()` assert at `zz_font_d3d.cpp:312`. Debug probes using the screen-coordinate overload are therefore not safe here.

**A boxed `drawFont` rect must sit *above* the transform origin.** `DrawMyName` drew the player's name into `{0, 0, 115, 14}` -- below the origin, over the gauge -- and produced no glyphs at all, despite a reached call site, a non-empty name, white colour, a valid font handle, a correct transform and a measured text extent (14px) that fits the rect. Every one of those was verified by tracing before the cause was found. The non-sprite overload rendered the same string fine, so neither the font nor the string was at fault. `DrawMobName` and `DrawAvatarName`'s no-gauge branch both use a rect *above* the origin (`{..., -18, ..., 0}`) with an explicit `setTransformSprite`, and both work; `DrawMyName` now matches them, which is why the player's name sits above the bar rather than inside it.

**Moving the name above the bar means the clan row has to move too.** `GetClanMarkDrawPos` places the clan mark/name at `y - NAMEBOX_HEIGHT/2 - 20`, which assumes the name sits at the gauge's height -- true for other players, false for `DrawMyName` since the fix above. With `SHOWMYNAME=1` a clanned player saw their clan drawn over their own name while everyone else saw it correctly. `DrawMyName` now passes `y - iHeightNameRow` (18, the same value as the name rect), giving clan / name / gauge. Not checked: `CChatBox::Draw` anchors the speech bubble at `y - 50/70 - NAMEBOX_HEIGHT`, so your own bubble may touch the lifted clan row.

**The underlying rule is not understood** -- the fix matches a working call site rather than explaining why a below-origin rect yields nothing in that batch. `DrawAvatarName`'s gauge branch still draws into `{0, 0, ...}` and is presumably affected the same way; it is hard to notice because it only shows for other players. If this bites again, that is the thread to pull.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
