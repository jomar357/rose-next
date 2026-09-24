# Unavailable and unrecoverable knowledge

What this project's history refers to but this checkout **cannot** see. Recorded so that no
session treats an absence as proof, and none claims a memory it does not have. Update this file
when something is recovered (move the entry to *Recovered*, with how and when) or when a new gap
is found.

Last reviewed: 2026-09-24, checkout `C:\Users\Jomar\Desktop\Rose\rose-next`, `master` at `84f6206`.

## Gaps

| # | What | Where it is referenced | Status on 2026-09-24 | Consequence |
|---|---|---|---|---|
| U1 | Previous maintainer's Claude Code memory index `C:\Users\Thomas\.claude\projects\c--Users-Thomas-Desktop-Rose-rose-next-classic\memory\MEMORY.md` and every file it linked | Inherited `AGENTS.md` (preserved verbatim below) | **Permanently unavailable** (PM-013, 2026-09-24: "we don't have it anymore"). `C:\Users\Thomas` does not exist on this machine. Contents never seen by this project's current sessions. | Any knowledge that lived only there is lost to us. Do not assume what it said. If the PM can obtain a copy, archive it under `doc/ai/archive/<date>/` before using it. |
| U2 | Memory entry `[[reference-logstring-formats-before-filter]]` | [client/model-node-and-dummy-indices.md](topics/client/model-node-and-dummy-indices.md) (verbatim text) | **Unavailable** (it is a U1 memory slug). | The surrounding text states the gist: `LogString` always reports at Debug level; see also [client/build-launch-logging.md](topics/client/build-launch-logging.md). |
| U3 | (2026-09-24: `C:\Users\Jomar\Desktop\Rose\RoseZA.zip` and other dumps exist beside the repo; not inspected) Reference data dumps `C:\Users\Thomas\Desktop\Testclients\` (QQ-iROSE, RoseZA, titanRose; other text also names Jrose, ruff, tsuki, 667, Evo dumps) | [project/data-repair-tooling.md](topics/project/data-repair-tooling.md), import topics | **Not on this machine.** | Data-repair and import scripts that read those dumps cannot be re-run here until the PM supplies the dumps and their location. |
| U4 | (Partly recovered 2026-09-24: `data/` now holds the unpacked 2026-09-22 VFS; see local-setup-runbook) Game data under `data/` (STB/STL/ZSC/IFO/…); `build/` backups and manifests (e.g. `build/oro-667/`, `build/ai-skill-refs/`, `build/coplanar-overlaps/`); STB sidecars written by balance passes | Many topics; `data/` is gitignored by design | **Absent locally.** `data/` holds only 16 tracked files (`.gitkeep`s, `data/README.md`, the RmlUi `.rml/.rcss` and a font). No `build/` directory exists. | Nothing that depends on game data (audits, `--verify` of data scripts, bakes, running servers or the client) can be done or checked here. Every "validated in game" statement in the topics is historical. |
| U5 | Built binaries and the deployed game folder (`bin/`, `Exes/` except `server.toml`, `dev/`) | Build/debug topics | **Absent locally.** No build has been run in this checkout. | No historical build or test result can be assumed to hold for this checkout. |
| U6 | Chat transcripts and reasoning of earlier sessions (all commits are by `ThomasL`, 461 of them) | Implicit | **Not available**, except what was written into the repository. | Commit messages and the archived guides are the only record. |
| U7 | Map editor build path `C:\Users\Thomas\Desktop\Rose\rose-next-classic\data` used as `/p:ReferencePath` | [map-editor/overview-build-architecture.md](topics/map-editor/overview-build-architecture.md) | **Path does not exist here.** | Substitute this checkout's `data` folder; `irrKlang.NET2.0.dll` must be present there, and it is not tracked in git (not verified). |
| U8 | `.claude/settings.local.json` (tracked) holds permission rules for `C:\Users\Thomas\...` paths | Personal AI settings | Left untouched on purpose (personal settings are out of scope). | Harmless; the rules match nothing on this machine. |
| U9 | jCodeMunch index of this checkout | User's global instructions | Not used for this project (PM-015, 2026-09-24). An `index_folder` call was interrupted; whether a partial index exists is unknown and irrelevant. | Use Grep/Glob/Read. |

## The inherited `AGENTS.md`

Replaced on 2026-09-24 by a portable entry point that does not depend on any one user's
memory directory. Its original text, byte-exact (checked by `scripts/verify-ai-docs.py`):

<!-- verbatim:begin src=AGENTS.md lines=1-13 sha256=1d1358bfc48da8a2a9d06d89665516a2bb2466c8bc8f3b87daa3c3381d074fc0 -->
# Project instructions
This project is primarily maintained with Claude Code.
Before doing any work in this repository:

1. Read `CLAUDE.md` at the repository root and follow its project guidance.

2. Read the Claude Code project memory index located at:

   `C:\Users\Thomas\.claude\projects\c--Users-Thomas-Desktop-Rose-rose-next-classic\memory\MEMORY.md`

3. Treat MEMORY.md as an index to additional persistent project knowledge. When searching for relevant project knowledge, consult MEMORY.md before doing broad repository exploration.

4. Do **not** read every memory file by default, and do not treat anything in claude.md or memory.md as absolute truth.
<!-- verbatim:end -->

## Recovered

_Nothing yet._
