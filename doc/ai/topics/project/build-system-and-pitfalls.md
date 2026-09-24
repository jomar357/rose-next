# Build system, key build facts, common build pitfalls

> **Provenance:** moved verbatim on 2026-09-24 from `CLAUDE.md` lines 23-54; `CLAUDE.md` lines 848-856 (revision `84f6206`).
> Original bytes: [`root--CLAUDE.md.txt`](../../archive/2026-09-24/root--CLAUDE.md.txt).
> **Status:** inherited knowledge written by earlier sessions. It was **not re-verified** during the 2026-09-24
> migration; confirm against the code before relying on a claim. Mentions of "root/client/server
> `CLAUDE.md`" inside the text mean the pre-2026-09-24 guides; find sections via [INDEX](../../INDEX.md).
> **Editing rule:** never edit between `verbatim` markers (they are checked byte-for-byte by
> `scripts/verify-ai-docs.py`). Record corrections, supersessions and new findings under *Updates*.

<!-- verbatim:begin src=CLAUDE.md lines=23-54 sha256=2aedab0f5295cfb263d7e164bf54c896f6ad3c7e3f8a215afb5603315a6111e3 -->
## Build System

Mixed Rust (i686-pc-windows-msvc) + C++ (VS2019, x86). Three-phase build:

```powershell
# Full build (recommended)
just build release    # or: scripts/build.ps1 -config release

# Manual steps:
# 1. Build thirdparty C++ deps
MSBuild.exe thirdparty.sln -p:Configuration=release;Platform=x86
# 2. Build Rust crates (MUST be i686)
cd src/ && cargo +stable-i686-pc-windows-msvc build --release
# 3. Build Rose Next C++ projects
MSBuild.exe rose-next.sln -p:Configuration=release;Platform=x86
```

### Key build facts
- Rust toolchain override: `stable-i686-pc-windows-msvc` in `src/`
- Cargo target dir: `bin/` (set in `src/.cargo/config`)
- Output binaries: `bin/release/` — rosenext.exe, sho_gameserver.exe, sho_loginserver.exe, sho_worldserver.exe, pipeline.exe
- Thirdparty output: `bin/release/thirdparty/`
- `ntdll.lib` is a required linker dependency for client and all servers
- Build assets: `just build-assets release` or `scripts/build-assets.ps1`
- **`common` and `lib_util` used to compile with `/Od` in the *release* configuration** — an explicit `<Optimization>Disabled</Optimization>` in their release `ItemDefinitionGroup`, not an inherited default. Both are now `MaxSpeed`. **Check what a project actually compiles before estimating the blast radius.** `common.vcxproj` builds only 8 of the 21 `.cpp` files under `src/common/` — `io/stb.cpp`, `io/reader.cpp`, `log.cpp`, `network/network_util.cpp`, `util.cpp`, `uuid.cpp`, `sha256.cpp`, `goddess_effect.cpp`. `lib_util` adds `CStr`, `CRandom`, the socket layer, `PacketHEADER`, threads and hashing. `calculation.cpp` and the shared item/quest code are **not** in either — they are listed directly in `client.vcxproj` and `sho_gameserver.vcxproj`, so combat math was always optimized. The fix is real but it is the STB/string/socket layer, not the game logic. Measured on `item_drop.stb` (438 KB, 188,751 cells): parse **34 ms → 2 ms, 17x**, which took the character-select stall's table loading with it.
  - **A missing `<Optimization>` element does *not* mean `/Od`.** `triggervfs`, `tgamectrl` and `common-server` have no such element and inherit `/O2` from the MSBuild release defaults — they are fine. Only an *explicit* `Disabled` is a bug, so grepping for absent properties produces false positives. Confirm with `MSBuild ... -t:<project> -v:detailed` and read the actual `CL.exe` command line.
  - `sho_gameserver` is deliberately `MinSpace` (`/O1`), which is optimized, just for size rather than speed.
  - **MSVC's diagnostics here are localised (French).** Filtering build output for `": error"` silently matches nothing — the string is `": erreur"`. A build that failed can look like a build that passed.
- **D3D9 core headers come from the Windows 10 SDK**, not the vendored DX SDK — `d3d9.h`/`d3d9types.h`/`d3d9caps.h` were deleted from `thirdparty/directx9/include/` so the SDK copies (which have the 9Ex interfaces) win. MSVC searches every `/I` path before the system include dirs, so the vendored copies could not be beaten by ordering. The rest of the vendored SDK stays, because D3DX9 is not in the Windows SDK.
- **`d3dx9_43.dll` must ship with the client** — D3DX9 is linked against the June 2010 redistributable rather than the old static lib. `scripts/post-build.ps1` copies it into `bin/<config>` and `scripts/dist.ps1` bundles it; a hand-rolled deploy that forgets it produces a client that will not start.
- **RmlUi and FreeType are hand-written `.vcxproj` files in `thirdparty.sln`** (like every other dep here — the upstream projects are CMake-based and we do not use CMake). Both need `RMLUI_CUSTOM_RTTI` (client RTTI is off) and `RMLUI_FONT_ENGINE_FREETYPE` — without the latter RmlUi compiles its "no font engine" branch and `Rml::Initialise` fails at runtime. RmlUi also needs per-directory object output (`<ObjectFileName>$(IntDir)%(RelativeDir)</ObjectFileName>`): `Source/Core/Geometry.cpp` and `Source/Debugger/Geometry.cpp` share a basename and otherwise overwrite each other, failing the link with unresolved externals that look like missing sources.

<!-- verbatim:end -->

<!-- verbatim:begin src=CLAUDE.md lines=848-856 sha256=86e2897e507f6beb7b08395bad69a0243de80725c79d699cd7a1fcf7bb887734 -->
## Common Pitfalls

- **Always build via the .sln, not individual .vcxproj files.** Projects depend on `$(SolutionDir)` and `$(GeneratedDirCommon)` (→ `build/gen/common/`) from `rose-next.props`. These don't resolve when building a vcxproj standalone. Use: `MSBuild.exe rose-next.sln -p:Configuration=release;Platform=x86 -t:sho_gameserver`
- The `common.vcxproj` pre-build step runs `cargo build`, so building via the solution handles Rust automatically
- Always build Rust with i686 toolchain — the entire project is 32-bit x86
- FlatBuffers schemas in `src/common-lib/packets/` must be compiled with `flatc` (handled by build.rs)
- `src/common-lib/build.rs` uses `PROFILE` env var (not `DEBUG`) to find flatc path
- Server projects link against Rust staticlib output — build Rust before C++
- Thirdparty must be built before rose-next.sln
<!-- verbatim:end -->

## Updates

_None yet. Add dated entries (newest last) with source paths, revision and verification status._
