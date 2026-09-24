# AGENTS.md — entry point for AI tools

This repository is Rose Next Classic (ROSE Online server + client, C++/Rust, 32-bit x86 Windows).
It is worked on with Claude Code and other AI tools under the direction of a Project Manager.
The rules are the same for every tool. All persistent project knowledge is in this repository;
a local memory folder (step 3) is a supplement, never a requirement.

Before doing any work:

1. Read [CLAUDE.md](CLAUDE.md) at the repository root: the operating guide (PM authority, startup,
   documentation duties, the closing phrase "Our work here is done", essential project rules).
   Your tool may not load it automatically; read it anyway.
2. Read [doc/ai/INDEX.md](doc/ai/INDEX.md), [doc/ai/STATE.md](doc/ai/STATE.md) and
   [doc/ai/HANDOFF.md](doc/ai/HANDOFF.md), then reconcile them with `git status` / `git log`.
3. **On the PM's machine only:** Claude Code keeps a memory index for this project at
   `C:\Users\Jomar\.claude\projects\C--Users-Jomar-Desktop-Rose-rose-next\memory\MEMORY.md`.
   If it exists, read that index (not every file it links; open a linked note only when relevant).
   As of 2026-09-24 it holds one note about the PM's role and working preferences. It is
   secondary: when it disagrees with `doc/ai/`, the repository wins, and anything project-relevant
   learned there belongs in `doc/ai/`. If the path does not exist (another machine or tool),
   continue without it.
4. Read only the topic files that INDEX routes your task to. When you work under `src/client/`,
   `src/sho_gameserver/` or `xadet/rose-online-map-editor/`, also read that directory's `CLAUDE.md`.
5. Follow [doc/ai/SESSION_PROTOCOL.md](doc/ai/SESSION_PROTOCOL.md) for checkpoints, concurrent
   sessions and closing.

Treat documentation written before 2026-09-24 as inherited evidence, not as instruction or
verified fact. Only the PM's directions (recorded in [doc/ai/DECISIONS.md](doc/ai/DECISIONS.md))
authorise work, commits, pushes or deployment.

The previous `AGENTS.md` pointed at another maintainer's external memory index, which is not
available; its original text and the consequences are recorded in
[doc/ai/UNAVAILABLE_KNOWLEDGE.md](doc/ai/UNAVAILABLE_KNOWLEDGE.md).
