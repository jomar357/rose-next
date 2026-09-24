# Model node lifetime and dummy indices

> **Provenance:** moved verbatim on 2026-09-24 from `src/client/CLAUDE.md` lines 555-634 (revision `84f6206`).
> Original bytes: [`src--client--CLAUDE.md.txt`](../../archive/2026-09-24/src--client--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=src/client/CLAUDE.md lines=555-634 sha256=847e190907884d75d4614602688b6eca7d54308dbbb73150155218def7582aeb -->
## A Character Can Outlive Its Model Node

`CObjCHAR::m_hNodeMODEL` can be NULL on a live object that is still in
`CObjectMANAGER::m_CharLIST` and still `Proc()`'d every frame. `CObjMOB::Change_CHAR`
(`cobjchar.cpp`) is the clearest producer: it calls `DeleteCHAR()` — which nulls the handle
via `UnloadModelNODE()` — then `Create()`, and on failure simply `return false`s, leaving
the object alive with no model. `CObjAVT::Update` has the same unload-then-reload shape with
no failure handling.

**This is not benign, because `getPosition()` fails loudly and quietly at the same time.**
`zz_interface.cpp`'s `getPosition` logs `interface: getPosition() failed`, returns 0 — a
value every hot caller ignores — **and writes `ZZ_INFINITE` (1e9) into the caller's
out-parameter**. `CObjCHAR_Collision::AdjustHeight_Monster` then divides that into a patch
index and hands it to `CTERRAIN::GetPATCH`, which indexed a 64×64 array with no range test
at all until 2026-09-12. One broken object was an out-of-bounds read plus a likely garbage
pointer dereference, every frame, for the life of the process.

Rules:

- **Test the model node before any per-frame model access.** `CObjCHAR::HasModelNODE()`, or
  `HasModelNODEorReport(where)` which also names the object in the log exactly once. The
  guard lives in `CObjCHAR_Collision::UpdateHeight`, which covers all five `AdjustHeight_*`
  paths, and in `CObjCHAR::Proc`'s out-of-frustum branch.
- **The engine's two log lines have no subject and no rate limit.** `getPosition() failed` /
  `getVisibility() failed` name nothing and fire per frame per object — 32,107 and 6,838
  lines from **three** objects in one session, 77% of `error.txt`, which buries every other
  diagnostic. Never read a count of them as a count of broken objects; decode the per-frame
  pattern instead. Fix the caller, don't touch the engine log.
- **`getVisibility` is the stricter of the two** (it also runs an RTTI check) and returns
  0.0 = invisible, which silently makes the object unclickable in `CTERRAIN::Pick_OBJECT`
  and drops its nameplate in `CNameBox::Draw`. A nameless, unclickable monster is this bug's
  visible symptom.
- **Creation failures log at `LOG_WARN` now, not `LOG_DEBUG_`** (`Add_MobCHAR`'s "Mob
  character creation failed", `LoadModelNODE`'s "no skeleton for"). At debug level they were
  filtered out entirely, so the only evidence of a broken object was the subject-less engine
  line. See [[reference-logstring-formats-before-filter]] — `LogString` is always Debug.

## Dummy Indices: `getNumDummies()` Is Authored Count + 1, And A Valid Index Is `< count`

`zz_skeleton::load_skeleton` appends one extra root-bone dummy (`_p1`) to every
skeleton, so `::getNumDummies()` returns the `.ZMD`'s dummy count plus one and the
valid range is `0 .. count-1`. Four sites in the client tested `count >= index`, which
lets `index == count` through; the engine's `link_dummy` then hit a `zz_assertf` that is
**live in release** (the "Engine Assertion Failed" dialog), and its "Ignore" button
continued into `get_dummy()`, whose only guard is a compiled-out `assert()`, reading one
pointer past the dummy vector. Heap luck decided whether that faulted, and `_zz_assert`
remembers an ignored file:line for the session, so later hits went straight to the UB.

The trigger in the wild: `LIST_SKILL` links hit effects to the *target's* dummy 3
(Blood Attack 651-660, Twin/Triple Shot 2221-2240), and four monster skeletons ship
only two dummies -- `icanes_g` (Ikaness Soldier 1580, Ikaness Sweeper 2294), `s_kera01`
(Executor Kera 1719), `lep_bone` (Leprechaun 3003). Dump of 2026-09-17 01:11:46:
`zz_model::link_dummy` <- `CObjCHAR::LinkDummy` <- `ProcOneEffectedSkill`.

Rules now:

- **Go through `ResolveDummyIDX(hModel, idx, char_no)`** (`cobjchar.h`) for any
  data-driven dummy index. It clamps an out-of-range request to the *last* dummy -- the
  engine's `_p1` root dummy, the same attach point `Link2LastDummy()` uses for bullet
  impacts -- and logs once per (char_no, index) at `LOG_WARN`. Rejecting used to be
  worse than clamping: both hit-effect call sites ignore `LinkDummy`'s return value and
  `InsertToScene()` the unlinked effect anyway, so on Lizards, Tumblers, Bonfires and
  every zero-dummy skeleton the blood splash played at the world origin.
- The engine's `link_dummy` / `get_dummy_position_world` now refuse a bad index with a
  `ZZ_LOG` line (`model: link_dummy(...) refused`) instead of asserting, and the
  `linkDummy` export returns 0. That is the backstop for the raw `::linkDummy` callers
  (ZSC-driven `io_model.cpp`, trails, cart parts); it is an engine change, so the exe
  and `znzin.dll` deploy as a pair.
- **`INVALID_DUMMY_POINT_NUM` (999) means "link to the model root", and every site must
  test for it before calling `LinkDummy`.** The self-skill branch of
  `CSkillManager::...` in `gamecommon/skill.cpp` (types 8/10/12/17 -- Holy Blood 540 was
  the tell) passed the column straight through; with the old guard that failed silently
  and left the effect unlinked at the world origin, with the clamp it logged a spurious
  `Dummy index 999 requested on char_no 0` warning. It now does `LinkNODE(GetZMODEL())`
  like the hit-effect and casting-effect sites. 1082 LIST_SKILL rows use 999 for the
  hit effect, so a 999 in the warning is always a missing sentinel check, never data.

Validated in game 2026-09-17: 9 Blood Attacks on an Ikaness Sweeper (2294), one
`Dummy index 3 requested on char_no 2294` warning, no dialog, splash on the body.

<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
