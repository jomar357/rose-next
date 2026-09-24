# CLAUDE.md — ROSE Online Map Editor (xadet) (component guide)

Auto-loaded when working under `xadet/rose-online-map-editor/`. The root
[CLAUDE.md](../../CLAUDE.md) and [doc/ai/](../../doc/ai/INDEX.md) rules apply first. This compact
guide replaced a 305-line version on 2026-09-24; every line of it is preserved verbatim in the
`doc/ai/topics/map-editor/` files below ([archive](../../doc/ai/archive/2026-09-24/MANIFEST.md),
[mapping](../../doc/ai/migration/2026-09-24-mapping.md)). Summaries here are of inherited,
unverified notes.

Legacy C# map editor (~2007): WPF on .NET Framework 3.5, XNA 3.1 rendering in a WinForms panel,
irrKlang audio, **x86 only**. Vendored from jackwakefield/rose-online-map-editor at `7f0462e`
(Apache 2.0) and modified in place; there is no upstream remote. It shares no build tooling with
the C++/Rust workspace; its only coupling is the game data in `../../data`.

## Build, deploy, run

- VS2019 MSBuild, `Release|x86`, `Map Editor.sln`. The `irrKlang.NET2.0.dll` reference is stale:
  pass `/p:ReferencePath=<this checkout>\data` (the inherited command names another machine's
  path; see U7 in [UNAVAILABLE_KNOWLEDGE](../../doc/ai/UNAVAILABLE_KNOWLEDGE.md)).
- Editing source is not enough: copy `Map Editor.exe` and `.pdb` from `Map Editor\bin\x86\Release\`
  into `../../data`, which is also the editor's working directory.
- Log: `../../data/Map Editor.log` (every line and full exceptions). Debug from the log's stage and
  stack trace first; clear it before asking for a retest.

## Rules

- Keep changes narrow; no broad refactors or formatting churn. Update the matching undo command
  when you change edit behaviour.
- Tolerate missing optional assets (log and continue); abort only for required files; never swallow
  new exceptions silently. WPF control updates from background threads go through the dispatcher.
- Do not edit game data to fix editor code unless the PM asks.
- **Saving rewrites the whole map with no undo and no backup**, and `data/` is untracked: back up the
  zone folder first. Servers see a save after restart; the client only after a VFS re-bake.
- **Never delete a placed decoration/construction object**: LIT entries are keyed by ordinal, so
  deletion misassigns every later lightmap (known, not fixed). Move or sink it instead.
- Keep both tileset helper lookups (`3Ddata\ESTB` and root `ESTB`) working.

Topics: [overview, build, architecture, data formats](../../doc/ai/topics/map-editor/overview-build-architecture.md) ·
[debugging and editing guidelines](../../doc/ai/topics/map-editor/debugging-and-editing-guidelines.md) ·
[compatibility fixes already made](../../doc/ai/topics/map-editor/compatibility-fixes.md) (Karkia/Skaaj IFO saves, blank sky column,
MOV painting and its tests, precision, morph flags, lightmap sharing, startup tolerance) ·
[verification checklist](../../doc/ai/topics/map-editor/verification-checklist.md)
