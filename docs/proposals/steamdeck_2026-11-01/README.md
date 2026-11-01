# Steam Deck feasibility - report, plan and guardrails (2026-11-01)

*Status: PROPOSAL. Research only: no engine or mod code was changed, nothing was built, deployed or run.*
*Evidence: [evidence/engine_portability.md](evidence/engine_portability.md), [evidence/mod_audit.md](evidence/mod_audit.md),
[evidence/web_research.md](evidence/web_research.md). Engine anchors are against the release tree
`H:/hzm_work/eng-hotfix13661` (branch `rel-1.10.38-engine`, HEAD `656a4d78`), which is newer than `openmohaa-hzm/`
(2026-10-12) and is the only tree with the shipped gamepad code. Mod anchors are against `hzm-mohaa-coop-mod/` and the
shipped manifest `manifests/latest.json` (v1.10.50, 60 files, 8.68 GB).*

## TL;DR

**It is feasible, and the engine is closer than the release pipeline.** The fork kept its Windows code behind
`_WIN32` and upstream's Linux path is intact; one function blocks a Linux compile. What is Windows-only is everything
*around* the game: the installer, the launcher, the updater, the bug-report upload and the on-screen keyboard.

**Recommended route: native Linux x86_64 build, with Proton as the documented stop-gap.**

1. The fork changed wire constants (`MAX_CONFIGSTRINGS 8192`, `GENTITYNUM_BITS 11`, ENGINE.md section 1), so upstream's
   Linux binaries cannot join our servers. We must build our own either way; with Linux that is one CI job.
2. A native SDL2 build in Game Mode gets the Steam on-screen keyboard for free when the engine calls
   `SDL_StartTextInput()` (SDL2's X11 backend opens `steam://open/keyboard` when `SteamDeck=1`). Under Proton we only
   have `osk.exe`, which does nothing useful.
3. Native avoids Wine-specific risks we found in our own code: the overlay crash guard can turn a Mesa/Wine fault
   into a hang (`sys_win32.c:836-923`), and the PowerShell launcher/updater cannot run at all.
4. A community report shows upstream's Linux build already playing on a Deck (GOG forum, source in Appendix A); the
   same report says the Windows exe under Proton showed a grey box and crashed. Treat Proton as unproven.

**Top blockers**, in order: (1) no way to install, launch or update without Windows (PowerShell/VBS/registry);
(2) ~~no Linux build exists yet~~ **fixed 2026-11-01**: the engine CI now builds Linux x86_64 green, both renderers included (not yet run on Linux); (3) typing (name, server password, connect IP,
chat, console) has no Deck path except Steam+X.

---

## 1. Ranked findings

### BLOCKERS

| # | Finding | Evidence | Fix (stage) |
|---|---|---|---|
| B1 | **Install, update and launch are Windows-only.** The web installer finds GOG via the Windows registry; the shortcut runs a VBS that starts `powershell.exe`; `updater.ps1` writes the registry and calls System32 `curl.exe` plus WinForms. None of it runs on SteamOS, and the VBS/PowerShell chain also fails under Proton. README says "Needs: Windows". | `installer/webinstall.iss:86-88`, `updater/launch_coop.vbs:7`, `updater.ps1:28,224`, `README.md:37` | Stage 0 workaround: NoInstaller zip + launch `openmohaa.exe` directly with the args from `webinstall.iss:251`. Stage 3: portable updater + Deck installer. |
| B2 | **No Linux binaries, and the fork does not compile on Linux as-is.** (a) `Sys_OpenURL` (the Discord button, 2026-09-25) uses `SDL_VERSION_ATLEAST` but `sys_main.c` never includes an SDL header: `sys_main.c:313: error: function-like macro 'SDL_VERSION_ATLEAST' is not defined` on Linux and macOS. (b) `BR_ScrubStr` is defined inside a `_WIN32` block (`cl_bugreport.cpp:1010-1579`, def at `:1040`) but called from unguarded code at `:1651`, `:1774`; the CI never reached it because (a) comes first. **The Linux CI build already runs on every push to `MOHCoopTrilogy/openmohaa` and has failed every time since**, and `fail-fast` cancels `linux-amd64` as soon as an exotic platform fails, so nobody saw a Deck-relevant result. `publish_release.ps1` stages only `.exe/.dll`. | CI run 40199712937 (`release-1.10.36`, 2026-10-25); `code/sys/sys_main.c:313`; `code/client/cl_bugreport.cpp:1040,1651,1774`; `publish_release.ps1:85-106` | **FIXED 2026-11-01 - Linux x86_64 builds green** (bug-10281, bug-10308; commits `a36f5baf..1308e16c` on `rel-1.10.38-engine`, pushed to `MOHCoopTrilogy/openmohaa`; run 41340405088). Behind (a) and (b) were five more layers, each hidden by the one before: a `static` vs `extern` OpenAL pointer, a Windows-only variable reached from `common.c`, gl2 not compiled at all by upstream's CI (no `USE_RENDERER_DLOPEN`), the shader embedder running an x86_64 helper on an ARM build machine (now a `cmake -P` script, 63/63 outputs identical), and 47 gl2 errors (C++ `or`, prototype mismatches, PIC). The artefact `out-linux-amd64` holds `openmohaa`, `omohaaded`, `cgame.so`, `game.so`, `renderer_opengl1.so`, `renderer_opengl2.so` (x86-64 ELF, needs glibc 2.34; SteamOS 3.5+ has 2.38). **Runs on Mesa (2026-11-01):** a new `linux-smoke` CI job (every push) starts the build under Xvfb at 1280x800 on Mesa llvmpipe. It found and drove two more fixes: gl2 was running gl1's code via ELF symbol interposition (the exe linked both renderer `.so` files; SIGSEGV), and the cross-built bundled SDL2 had no X11/Wayland driver (amd64 now builds natively). Run 41345831711: SDL x11, 1280x800 adopted, gl2 on GL 4.5 core, **all 137 GLSL programs compile**, OpenAL has PipeWire/Pulse. Still unverified: a map load (no game data on CI), the Deck's own GPU, Steam Input, audio playback. Windows x86/ARM64 CI still fail (x64-only crash-guard registers); not shipped. |
| B3 | **No text entry without a keyboard.** Pad Y opens `osk.exe` only under `_WIN32`; nothing calls `SDL_StartTextInput` for the Steam keyboard. Affected: server name and password (`coop_start.urc:34,62`), player name (`coop_mp_options.urc:112`), connect IP (`joininternetgame.urc:46`), bug report (`coop_report.urc:144`), chat, console. Valve's Verified rules require an on-screen keyboard for text entry. | `code/sdl/sdl_input.c:1305-1308`, `sys_win32.c:1077` | Stage 2: call `SDL_StartTextInput()` when a text field or the console takes focus (native); open `steam://open/keyboard` under Proton. |

### IMPORTANT

| # | Finding | Evidence | Fix (stage) |
|---|---|---|---|
| I1 | **Size: 8.68 GB, all 60 files mandatory.** `assets_tex` is 1.31 GB of 2,394 *uncompressed* TGAs (3.09 GB unpacked); third-party HD packs about 5.7 GB. The manifest has no "optional" flag. A 64 GB Deck, or a microSD install, makes this a real barrier. Lite install without HD is about 2.6 GB, but whether the mod depends on the HRRTM or geared-soldier models has not been checked. | `manifests/latest.json`; evidence/mod_audit.md section 2 | **Decided 2026-11-01: HD paks stay mandatory.** So: shrink rather than split. Convert the uncompressed TGAs to DDS (BC1/BC3/BC7), which also removes load-time compression work on the Deck's CPU; the Deck installer checks free space (about 9 GB plus the game) and warns about 64 GB models and slow microSD cards. |
| I2 | **gl2 renderer has never run on Mesa.** It requests a 3.2 core context (`sdl_glimp.c:745`), so every shader builds as `#version 150` on Mesa's strict compiler, and `tr_glsl.c` has 36 fatal-error exits: one rejected shader stops startup. A grep found no NVIDIA-only habits (the new `check_deck.py glsl` check is clean), and FSR's `textureGather` has a fallback (`tr_glsl.c:1872-1893`). | `code/renderergl2/tr_glsl.c:420-455`, `sdl_glimp.c:745` | Stage 1: one boot under Mesa. WSL2's Mesa (llvmpipe) is a hardware-free first check, and `glslangValidator` a second. Fallback: Zink (GL on Vulkan) ran at about 93% of radeonsi on RDNA2 (Phoronix). |
| I3 | **GCC/Clang have never compiled the fork.** `CMakeLists.txt:48-52` adds `-Werror=return-type`; GCC 14 treats implicit declarations as errors, and `tr_hzm_lens.c:33` shows the fork has had them. | as cited | Stage 1: one fix-up pass, build in Valve's Steam Runtime 3.0 "sniper" SDK so glibc matches SteamOS. |
| I4 | **Heavy features are on by default for a 4-core, 15 W, 8-CU device.** Shipped defaults target a 1080p desktop: `com_maxfps 200`, SSAO, DoF, sun shadows at 2048, generated normal maps *forced on* (`autoexec.cfg:1829`, so no player cfg can turn them off), 4000 temp models. The CPU side is single-threaded, and AI duplication by player count defaults to 50% with a cap of 80 (`aihandler.scr:229`, `variables.scr:100`). The built-in recommender scores single-core speed against a Ryzen 7 9700X, so it will rate a Deck Low or Medium. | `coop_defaults.cfg:211,223,309-311,659`; `autoexec.cfg:1829`; `client/cl_hzm_recommend.cpp:7-12` | Stage 2: Deck preset (section 3), auto-applied on first launch when `SteamDeck=1`. A Deck should join rather than host 4-player missions. |
| I5 | **Steam Input: deadzones and prompts.** Pad type comes from `SDL_GameControllerGetType` (`sdl_input.c:637-652`). Steam's virtual pad (VID 0x28DE) reads as VIRTUAL or Xbox, so it gets the 0.15 "generic" or 0.10 Xbox deadzone *on top of* Steam's own. No gyro code exists, so players will use Steam's gyro-to-mouse, but mouse motion calls `IN_PadNoteKbm` (`:1915-1920`) and flips `in_padActive`: button prompts will flicker between pad and keyboard glyphs while aiming. Lean is on the back paddles (`coop_defbinds1.cfg:33-36`), which Steam's default Xbox template does not expose. | `code/sdl/sdl_input.c:637-652,1337,1915-1920`; `coop_defbinds1.cfg:9-36` | Stage 2: a `deck` pad type (VID 0x28DE, low deadzone); treat mouse motion during recent pad input as mixed input, not a switch; publish a Steam Input community layout keyed to a fixed shortcut name. |
| I6 | **Proton-specific hazards in our own code.** The overlay guard (on by default, `common.c:1828`) parks any thread that faults outside our modules, and under Wine a Mesa or winex11 fault is "outside", so a crash becomes a freeze. `r_captureSafe` uses a layered GL window (`sdl_glimp.c:453-487`). The bug-report upload uses PowerShell (`cl_bugreport.cpp:3420-3436`). | as cited | Stage 0: document `+set com_overlayGuard 0` for Proton. Stage 2: auto-detect Wine (`wine_get_version` in ntdll) and default the guard off. |
| I7 | **Case mismatches: 511 paths (2,067 sites)** reference a mod file only when case is ignored, for example `generic_dialogue_US.tik` vs the real `Generic_dialogue_US.tik` (124 sites). The engine tolerates this today: pk3 lookups ignore case (`files.cpp:409-417,1195`) and loose files are case-corrected by a directory scan (`files.cpp:532-578`). No pak holds two entries that differ only by case. It is debt that blocks nothing, but it must not grow, and loose-file case correction costs a directory scan per miss. | `code/qcommon/files.cpp`; `check_deck_baseline.json` (511 keys) | Guardrail: ratchet in `check_deck.py case`. Pay down opportunistically. |

### NICE-TO-HAVE

| # | Finding | Evidence |
|---|---|---|
| N1 | **UI at 1280x800 is acceptable.** 116 of 182 menus use the 640x480 virtual screen, stretched 1.2:1 horizontally while text stays undistorted (`uifont.cpp:318-338`); verdana-12 renders at about 20 px. HUD text is drawn 1:1 below 1080p (`cl_ui.cpp:4225-4238`), about 12 px: passes Valve's 9 px minimum, at the recommended 12. Five fixed-pixel menus (coopAdmin, coop_objectives and others) need a look at 800p. | evidence/mod_audit.md section 4 |
| N2 | **FOV is Hor+** (`cg_view.c:7789-7793`), and `r_mode -2` (desktop resolution) is the default (`tr_init.c:1518`), so 16:10 at 1280x800 works without changes. FSR 1 render scale already exists. | as cited |
| N3 | **Pad-only menus already work**: left stick drives the cursor, D-pad moves focus, right stick scrolls (`sdl_input.c:1122-1236`). | as cited |
| N4 | **Windows-only extras that simply switch off on Linux**: the Dedicated button (stub `cl_dedicated.cpp:708`), the freeze watchdog, VRAM via DXGI (Linux falls back to `GL_ATI_meminfo`), minidumps. The fork removed the SIGSEGV handler on every platform, so Linux crashes leave no trace: add a backtrace handler. | evidence/engine_portability.md |
| N5 | **A dev cfg ships with a drive path**: `coop_mod/cfg/voprobe.cfg` names `G:\mohaa-gl2\home\maintt\qconsole.log` (in `zzzzzz_co-op_hzm_mod_code.pk3`). Harmless on a Deck, but a dev file in the release pak. | `check_deck.py shiptext` |
| N6 | **Module names need no changes**: loading never hardcodes `.dll` (`sys_main_new.c:241,309`); Linux names are `game.so`, `cgame.so`, `renderer_opengl1.so`, `renderer_opengl2.so` (`q_platform.h:264`). Home folder defaults to `~/.openmohaa` (`sys_unix.c:64-120`); HTTP is upstream libcurl, no WinHTTP. | as cited |
| N7 | **Hosting from a Deck**: UDP 12203 (game) and 12300 (query); SteamOS has no firewall active by default (community report). Internet play needs port forwarding or Tailscale/ZeroTier. 4 players + coop AI on the same 4 cores is untested. | evidence/web_research.md section 9 |

---

## 2. Staged work plan

Each stage ships something on its own.

**Decided 2026-11-01: no Deck in hand.** Testing splits three ways:

| What | Where | Catches |
|---|---|---|
| Linux compiles | GitHub Actions, on every push (exists already) | B2-type breaks, GCC/Clang errors |
| Linux runs: shaders on Mesa, map load, Linux client vs Windows server | WSL2 on this PC. `wsl --install` is a one-time step you run yourself, since it changes Windows settings. Mesa's software renderer (llvmpipe) uses the same GLSL compiler front end as the Deck's driver, and WSL can read the GOG data on `G:` in place. | I2 (gl2 on Mesa), protocol parity, `.so` loading, case lookups |
| Deck-only: frame time, Steam Input, on-screen keyboard, gamescope | A community tester with a Deck, sent a "Deck beta" build | I4, I5, B3 and the frame-time budget. Nothing else can stand in for these. |

**Decided 2026-11-01: CI host is GitHub Actions on `MOHCoopTrilogy/openmohaa`** (public, so Actions is free with no
minute cap; it already holds upstream's `shared-build-linux.yml` and runs it on every push). Only two things are missing:
the release branch has to be pushed there (today `rel-1.10.38-engine` exists only locally), and the matrix needs
`fail-fast: false` (or a trimmed matrix of `linux-amd64` + `windows-x64`) so the Deck's platform reports its own result.
`publish_release.ps1` then downloads the `linux-amd64` artefact of the **same commit** it ships (`gh run download`), so
both platforms come from one source state. The releases repo `MOHCoopTrilogy/releases` hosts the tarball beside the Windows files, as now.

### Stage 0 - Proton stop-gap guide (no code; about a day, then a community Deck tester)
- Install path: Heroic (GOG login) installs MOHAA War Chest, then unzip the **NoInstaller** release zip over it
  (`publish_release.ps1:331-433`). Add `openmohaa.exe` as a non-Steam game with `+set fs_basepath <gog dir>
  +set fs_homepath <gog dir>/home +set com_target_game 2 +set cl_renderer opengl2 +set com_overlayGuard 0`.
- On the Deck, check: does gl2 start on Wine+Mesa (I2)? Does the pad read as Xbox? Do Steam+X keyboard and
  `steam://open/keyboard` work? What frame rate does the Deck preset get on a reference map (section 4)?
- Output: `docs/STEAM_DECK.md` player guide (Proton), linked from the release README. If gl2 fails under Wine,
  document `cl_renderer opengl1` as the fallback.

### Stage 1 - Native Linux build (engine; about 1-2 weeks)
1. ~~Fix B2~~ DONE 2026-11-01.
2. ~~Push the release branch, `fail-fast: false`, fix the GCC/Clang fallout (I3) until green~~ DONE 2026-11-01. Every
   future engine branch must be pushed to `MOHCoopTrilogy/openmohaa` before release so CI can catch the next MSVC-only habit.
3. Package the artefact as `hzm-linux-x86_64.tar.gz` (`openmohaa` + `omohaaded` + the four `.so` + bundled SDL2/OpenAL/curl
   + `launch_hzm.sh`). The current Ubuntu 22.04 build needs glibc 2.34, which SteamOS has, so the Steam Runtime "sniper"
   container is optional (only needed to support older desktop distros).
4. Mesa boot test (I2): renderer half DONE in CI (`linux-smoke`, every push). Map-load half still needs WSL2 with the GOG data on `G:`.
5. Protocol parity check: a Linux client joins a Windows listen server and the reverse (wire constants, ENGINE.md section 1).
   **All five binaries per platform must come from the same commit**, the rule `publish_release.ps1` already enforces on Windows.

### Stage 2 - Deck input, UI and preset (engine + mod; about 1 week)
1. On-screen keyboard (B3): `SDL_StartTextInput()` on text-field/console focus, `SDL_StopTextInput()` on blur. Under Proton
   (detected Wine) open `steam://open/keyboard` instead of `osk.exe`.
2. `deck` pad type (I5): VID 0x28DE gets a low deadzone (Steam already applies one) and Deck glyphs.
   Mouse motion within about 500 ms of pad input counts as mixed input, so it no longer flips `in_padActive`.
3. Deck preset (I4, section 3): a fifth `Deck` preset in `gen_menu_graphics.py`, plus `coop_mod/cfg/deck_preset.cfg` for
   the rows presets deliberately skip (resolution, frame cap, VSync; `PRESET_SKIP`). The engine reads `getenv("SteamDeck")`
   into a read-only cvar and the first-run path execs the preset once. Un-force `r_hzmGenNormals` in `autoexec.cfg:1829` so the preset can turn it off.
4. UI: walk the five fixed-pixel menus at 1280x800; raise HUD text to at least 12 px at 800p.
5. Steam Input community layout (lean on the grips or the back paddles, gyro to mouse on the right pad) published under a
   fixed shortcut name, for example "HZM Coop".

### Stage 3 - Packaging and distribution (release scripts; about 1 week)
1. **Portable updater.** `manifests/latest.json` is just path/size/sha256/url, so a POSIX `hzm_update.sh`
   (curl + sha256sum, both on SteamOS) can implement it. Same manifest, a `platform` field per file (`win64`, `linux64`, `any`).
2. **Size, with every pak mandatory (decided 2026-11-01).** Convert the TGAs to DDS to shrink the install; the
   installer checks free space first. No Lite install.
3. **Deck installer.** One `install_hzm_deck.sh` run once in Desktop Mode: finds the GOG data (Heroic's `~/Games/Heroic/...`, or
   asks), unpacks the Linux tarball and paks, writes `fs_homepath`, adds the Steam shortcut with art and the layout name. After that
   everything happens in Game Mode, and the updater runs at launch. A Flatpak is a poor fit: 3+ GB of fast-changing paks plus game data outside the sandbox (OpenJKDF2 hit exactly this).
4. `publish_release.ps1`: stage and hash the Linux tarball beside the Windows set; run `check_deck.py` in preflight; add a Steam Deck
   section to the release README.

### Stage 4 - Keep it Deck-feasible (ongoing)
`docs/tools/check_deck.py` runs at every release (below), plus the manual checklist in section 4. After Stage 1, run
`--require-linux` so a release without Linux binaries fails.

---

## 3. Proposed Deck preset

The Low/Medium/High/Ultra presets live in `gen_menu_graphics.py:286-336`. "Deck" is a fifth column; the first three rows
are `PRESET_SKIP` rows, so they go in `deck_preset.cfg`. Values are proposals to tune on hardware, not measurements.

| cvar | shipped | Deck | why |
|---|---|---|---|
| `r_mode` / `r_customwidth` / `r_customheight` | -1 / 1920 / 1080 | -2 (desktop) or -1 / 1280 / 800 | native panel, 16:10 |
| `com_maxfps` | 200 | 60 (40 or 45 for battery) | 15 W budget; Deck frame limiter pairs with 40/45 |
| `r_swapInterval` | 1 | 1 | no tearing |
| `r_renderScale` / `r_fsrSharpness` | 1.0 / 0.25 | 0.75 / 0.4 | FSR 1 already exists |
| `r_msaa` / `r_ppFXAA` | -1 / 1 | 0 / 1 | MSAA is costly on 8 CUs |
| `r_ext_max_anisotropy` | 16 | 4 | bandwidth on shared LPDDR5 |
| `r_picmip` | 0 | 1 | VRAM: about 0.4-0.7 GB per map instead of 0.8-1.5 GB (estimate) |
| `r_hzmGenNormals` | 1, forced | 0 | needs un-forcing in `autoexec.cfg:1829` |
| `r_ppSSAO` / `r_ppDoF` / `r_ppHeatHaze` / `r_ppChromaticAberration` / `r_softParticles` | 1 | 0 | heaviest post-FX passes |
| `r_ppBloom` | 1 | 1 (0 for battery) | cheap, carries the look |
| `r_sunShadows` / `r_shadowMapSize` / `cg_shadows` / `r_hzmDlightShadows` | on / 2048 / 2 / 1 | 0 / 1024 / 1 / 0 | shadow passes |
| `r_hzmClouds` | -1 (auto, off only on Intel) | 0 | |
| `r_hzmWater` / `r_hzmWet` / `r_groundVariety` / `cg_footprints` | -1 / -1 / -1 / 1 | 0 | |
| `cg_effectdetail` / `cg_max_tempmodels` / `cg_marks_max` | 1 / 4000 / 487 | 0.6 / 1024 / 128 | CPU (single-threaded) |
| `r_subdivisions` / `r_lodscale` | 4 / 28 | 10 / 24 (5 on crowded maps) | the bug-3483 measurement scale |
| `coop_aiScaleChance` (when the Deck hosts) | 50 | 35 | fewer duplicated AI |
| `coop_aimAssist` | 0 | 1 | stick aiming on a 7-inch screen |
| `fov`, `cl_renderer`, `in_gamepad` | 80 / opengl2 / 1 | keep | Hor+ already gives about 90 degrees at 16:10 |

---

## 4. Per-release guardrails

### Automated: `docs/tools/check_deck.py` (new, read-only, about 50 s)

```
python -I docs/tools/check_deck.py                    # exit 1 on NEW Deck debt
python -I docs/tools/check_deck.py --update-baseline  # after paying debt off, commit the smaller baseline
python -I docs/tools/check_deck.py --require-linux    # from Stage 1 on
```

It is a ratchet: today's debt is recorded in `docs/tools/check_deck_baseline.json` and tolerated; a release fails only
on something new. Baseline at creation (v1.10.50): case 511, win32 3, shiptext 2, glsl 0.

| check | what it fails on |
|---|---|
| `case` | an asset reference whose case differs from the shipped file; two entries in one pak differing only by case |
| `win32` | a Win32 API, Windows header, MSVC keyword, drive path, `powershell`/`osk.exe`/`.vbs` or a `".dll"` literal in engine code **outside** a `_WIN32`/`_MSC_VER` guard (vendored GameSpy and `json.hpp` excluded). Self-tested: catches an unguarded call and an `#ifndef _WIN32` branch, skips guarded ones |
| `shiptext` | shipped cfg/scr/urc/tik text naming a drive path, PowerShell, cmd.exe, osk.exe, a .vbs/.bat/.ps1, `%APPDATA%` |
| `glsl` | a gl2 shader with its own `#version`, an NV-only extension, or doubles |
| `paks` | shipped total over 9.0 GB; one file growing more than 200 MB, or a new file over 300 MB, versus the previous manifest (never baselined: answer it each release); with `--require-linux`, no Linux binaries |
| `preset` | (once `deck_preset.cfg` exists) the preset sets a cvar the engine or mod does not register (`docs/generated/CVARS_*.md`) |

Not catchable by this lint, so it goes in the checklist: a Linux compile break like B2 (only a CI build catches that),
and frame time.

Proposed wiring (not done, it edits the release script): call it in the `publish_release.ps1` preflight beside the
What's New card check (`:34-62`) and abort on exit 1.

### Manual checklist (per release that touches the engine, renderer, menus or paks)
- [ ] Linux CI build green; Windows and Linux binaries built from **one** commit.
- [ ] `check_deck.py` exit 0 (with `--require-linux` after Stage 1).
- [ ] New text-entry field? It opens the on-screen keyboard on the Deck.
- [ ] New menu? It is reachable and usable by D-pad/stick only, and its smallest text is at least 9 px (target 12) at 1280x800.
- [ ] New binds? There is a pad bind, and nothing new depends on the back paddles alone.
- [ ] New post-FX, weather or AI cost? It has a cvar, and the Deck preset sets it.
- [ ] Frame-time budget, on a community tester's Deck (when the release touches render or AI cost) with the Deck preset, 1280x800, on `m2l1` and one
      crowded map (`m4l2` or `t2l1`): **at least 40 fps average, 1% lows at least 30** (Valve's floor is 30 at default settings).
- [ ] New pak over 300 MB, or total growth: is it compressed (DDS, not TGA)? Every pak is mandatory, so size is paid by every Deck player.
- [ ] The engine CI run for the shipped commit is green on `linux-amd64`.

---

## 5. Decisions

Decided by the user 2026-11-01:
1. **Hardware: no Deck.** Testing is CI, then WSL2, then a community tester (section 2).
2. **HD paks stay mandatory.** Shrink them (DDS) instead of splitting them.
3. **CI host: GitHub Actions on `MOHCoopTrilogy/openmohaa`.** The user deferred to the recommendation; it already exists and is free.

Still open: the route. Native Linux is recommended, with Proton as a guide-only stop-gap.

## Appendix A - key sources
- Valve Deck compatibility rules (9 px text, OSK, controller, 30 fps): https://partner.steamgames.com/doc/steamdeck/compat and https://partner.steamgames.com/doc/steamdeck/recommendations
- Upstream OpenMOHAA Linux releases: https://github.com/openmoh/openmohaa/releases ; compile deps: https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/04-coding/01-compiling.md ; install layout: https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/01-intro/01-installation.md ; home path: https://raw.githubusercontent.com/openmoh/openmohaa/main/docs/markdown/02-running/01-running.md
- Deck report with upstream Linux build (Proton grey-box crash): https://www.gog.com/forum/medal_of_honor_series/openmohaa_your_best_option
- SDL2 Steam keyboard on X11: https://raw.githubusercontent.com/libsdl-org/SDL/SDL2/src/video/x11/SDL_x11keyboard.c ; https://discourse.libsdl.org/t/sdl-x11-add-support-for-the-steam-deck-on-screen-keyboard/39748
- Steam virtual gamepad and ignore list: https://git.axiodl.com/encounter/SDL/commit/03250690d68bc09a9e60628a74424fb5b40a1085 ; gyro under Steam: https://discourse.libsdl.org/t/gyroscope-on-steam-deck-using-hid-driver/69064
- Steam Runtime sniper SDK (glibc): https://github.com/ValveSoftware/steam-runtime
- Zink vs radeonsi on RDNA2: https://www.phoronix.com/review/zink-radeon-august2022
- Flatpak precedents and pitfalls: https://github.com/flathub/com.etlegacy.ETLegacy ; https://github.com/shinyquagsire23/OpenJKDF2/issues/322
- Heroic: https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher
- Deck hardware: https://www.steamdeck.com/en/tech

Full claim-by-claim citations, with each tagged as checked on the page, community source or unverified, are in [evidence/web_research.md](evidence/web_research.md).
