# HZM OpenMOHAA fork: Steam Deck / Linux portability audit (read-only)

Audited tree: **`H:/hzm_work/eng-hotfix13661`**, branch `rel-1.10.38-engine`, HEAD `656a4d78` (2026-11-01). It has one dirty file, `code/cgame/cg_parsemsg.cpp`.
It is newer than `C:\mohaa-coop-dev\openmohaa-hzm` (`hzm-coop-working`, `277bdb9d`, 2026-10-12), and it is the release line, so all line numbers below are from the H: tree.
Fork vs merge-base `a72bc153`: 429 files, +147k/-5k lines. Nothing was built, edited or run.

In short, native Linux is realistic. The fork kept almost all of its Windows code behind `#ifdef _WIN32` and left upstream's Linux path alone. I found **one definite compile blocker**. The rest is Windows-only *features* that are stubbed out on Linux, plus Deck-specific polish. Proton looks feasible too, but the updater, the bug reporter and the overlay guard are at risk there.

---

## BLOCKERS (native Linux)

### B1. `cl_bugreport.cpp` does not compile on non-Windows
- `code/client/cl_bugreport.cpp:1010` opens `#ifdef _WIN32`, which closes at `:1579`. `BR_ScrubStr` is defined inside that block (`:1040`).
- It is called from code that is **not** guarded: `BR_CleanScrub` at `:1648-1652` (call at `:1651`) and `:1774`. In C++ an undeclared identifier is a hard error, and the file is globbed into every client build (`code/client/CMakeLists.txt:7`).
- Fix: move `BR_ScrubStr`, which is pure string code, out of the `_WIN32` block, or guard its callers. The feature's own entry points already stub cleanly on Linux ("only implemented on Windows", `:2963-2966`, `:3348-3351`), so only this one leak needs fixing.
- My guard-scan only caught `BR_*` statics. Expect a few more of these once the first GCC/Clang build runs. Nobody has compiled this fork for Linux; upstream CI does that (`.github/workflows/shared-build-linux.yml:54,73`, which uses clang).

### B2. Linux client binaries must be built from this fork (wire constants)
- This is a known fact, not a code defect. There is no Linux build pipeline: `build.ps1` and `publish_release.ps1` are Windows-only, and the manifest stages only `.dll` and `.exe` files (`publish_release.ps1:86-106`).
- Upstream's `shared-build-linux.yml` is a ready template: clang, flex, bison, and SDL2, OpenAL-soft and wolfssl built from source.

## IMPORTANT

### I1. Compiler strictness (GCC 14+/Clang 16+)
- The top-level CMake adds `-Werror=return-type` for GCC and Clang (`CMakeLists.txt:48-52`). Any fork function that falls off the end without a return will now fail to build. MSVC only warns about this (C4715/C4716).
- The existing MSVC log (`H:/hzm_work/eng-hotfix13661/.cmake/build.log`, a partial rebuild) shows no C4715. Its C4013 (implicit declaration) and C4047 hits (`tr_bsp.c:3145,4091`, `tr_scene.c:591`, `tr_sprite.c:97`) are all upstream lines that upstream CI already builds.
- One fork comment admits implicit declarations used to exist and were patched: `renderergl2/tr_hzm_lens.c:33-34`, "undeclared, so C would have truncated the pointer". GCC 14 makes those errors.
- Budget one fix-up pass. `cl_bugreport.cpp:44-45` maps `_stricmp` only under `BUGREPORT_SELFTEST`. `q_shared.h:258-259` maps `stricmp` to `strcasecmp` on non-WIN32, so `cl_keys.cpp:731` is fine.

### I2. Mesa rejecting a GLSL shader can hard-fail the renderer
- Shader header: `#version 150` on desktop GL ≥3.2. It adds `#define texture2D texture`, `varying`→`in`/`out`, and `out vec4 out_Color` (`renderergl2/tr_glsl.c:420-455`).
- The context asks for **3.2 core** first, then 2.0 compat, then ES 2.0 (`sdl/sdl_glimp.c:745-753`). Mesa radeonsi gives a core 4.6 context, so every shader runs under `#version 150` core.
- `tr_glsl.c` has **36 `ERR_FATAL`** sites (e.g. the sharpen shader near `:1862`). One Mesa-strict compile error in a fork post-FX shader kills gl2 startup. NVIDIA, which this fork was developed on, is lenient.
- My greps found no HLSL-isms (`saturate`/`lerp`/`float3`), no `gl_FragData`, no non-constant `const` initialisers and no uniform-initialised globals. That is a good sign, but it is not proof.
- Handled well already: FSR EASU uses `textureGather` with `#extension GL_ARB_gpu_shader5` and falls back to bilinear (`tr_glsl.c:1872-1893`). Mesa exposes gpu_shader5. `sampler2DMS` (`glsl/msaa_depthresolve_fp.glsl:14`) is core in 1.50. The MSAA resolve has a non-fatal fallback (`tr_glsl.c:2380-2394`).
- Action: run each `glsl/*.glsl` through `glslangValidator` with the `#version 150` header prepended, or boot once on Mesa (llvmpipe works) before Deck hardware.
- NVIDIA-only paths are optional and gated: `GL_NV_alpha_to_coverage_dither_control` (`tr_extensions.c:~225-231`, NULL when missing) and `GL_NVX_gpu_memory_info` (`tr_gfxprobe.c:~414`). The VRAM readout falls back to `GL_ATI_meminfo`, which Mesa has (`tr_hzm_vram.c:405-420`).

### I3. Steam Input: pad type, deadzone and glyphs
- SDL2 game controller API, `SDL_GameControllerGetType` (`sdl/sdl_input.c:637-652`): PS3/4/5→`ps`, Switch Pro→`nintendo`, and **UNKNOWN / VIRTUAL / Stadia / Luna / Shield→`generic`**. Everything else is `xbox`. The result is published as `in_padType` and logged as `^~^~^ PADTYPE <fam> (sdl type N)` (`:651`).
- The Deck under Steam Input appears as "Steam Virtual Gamepad" (VID 28de). With SDL ≥2.30's Steam virtual-gamepad info it reports the underlying type. The Deck's built-in pad most likely comes out `generic` or `xbox`. **One boot's PADTYPE line will settle it.**
- Auto-deadzone (`IN_PadDeadzone`, `:1337-1350`): ps 0.06, xbox 0.10, nintendo 0.09, any other type 0.15. Steam Input already applies its own deadzone, so `generic` stacks to roughly 0.15 + Steam's. Suggestion: treat VID 28de as its own family with a small deadzone, or recommend `joy_autoDeadzone 0`.
- **Gyro:** the fork has no SDL sensor code at all. Gyro on Deck means Steam Input "gyro to mouse".
  - Mouse motion of ≥3 px calls `IN_PadNoteKbm()` (`:1915-1920`), which flips `in_padActive` to 0. Key prompts and glyphs (`cgame/cg_coopfeed.c:1001-1015`) will then flicker between pad and KBM while you aim with gyro or the trackpads. The same happens with mouse-button binds (`:1927-1930`).
  - Aim friction is applied to the stick only (`client/cl_input.cpp:645-652`), so gyro aim gets no assist. That is acceptable.
- SDL version: SDL2 2.32.8 is bundled for Windows (`code/thirdparty/SDL2-2.32.8`). Linux uses the system SDL2 (`sdl/CMakeLists.txt:76`). The pad-test virtual device needs ≥2.24 (`SDL_JoystickAttachVirtualEx`, `sdl_input.c:~900`) and `SDL_OpenURL` needs ≥2.0.14 (it is version-guarded).

### I4. On-screen keyboard is Windows-only
- Pad **Y** in a menu calls `Sys_OpenOnScreenKeyboard()` only under `#ifdef _WIN32` (`sdl/sdl_input.c:1305-1308`). That runs `ShellExecuteA("osk.exe")` (`sys/sys_win32.c:1075-1077`).
- On Linux or Proton nothing opens. `SDL_StartTextInput()` is called once at init (`sdl_input.c:2151`), and `SDL_HINT_ENABLE_SCREEN_KEYBOARD` is never set. Deck players must press **Steam+X** for console, chat and name fields.
- Native fix: open `steam://open/keyboard` via `SDL_OpenURL` when `SteamDeck=1` or `SteamAppId` is set. That works in Game Mode.

### I5. Proton: the updater, launcher and bug reporter are PowerShell-based
- `updater/launch_coop.vbs:7` runs `wscript` → `powershell.exe -File updater.ps1`.
  - `updater.ps1` needs `$env:SystemRoot\System32\curl.exe` (`:224`), WinForms dialogs (`:67-96`, `:334`) and an HKCU WER `LocalDumps` key (`:25-30`).
  - It then launches the game with `+set fs_basepath <GOG> +set fs_homepath <app>\home +set com_target_game 2` (`:118-146`).
- A Proton prefix has no PowerShell, and probably no `curl.exe` in System32. The updater fails, so players must run `openmohaa.exe` directly with those three args as Steam launch options. Users also lose auto-update and the "update available" text, which reads `coop_latest_seen.txt` from the updater (`client/cl_ui.cpp:1966-2019`).
- The in-game bug report upload writes `upload.ps1` and runs System32 PowerShell (`client/cl_bugreport.cpp:3420-3436`), so it fails under Proton. WER CrashDumps (`:1557`) do not exist under Wine.
- Native Linux has the same gap: the engine has no updater (`code/autoupdater/` is an unbuilt ioq3 relic), so a Linux updater would have to be a shell or Python script.

### I6. Proton: the overlay guard VEH can turn crashes into hangs
- `sys/sys_win32.c:818-924` registers a **first** vectored exception handler (`AddVectoredExceptionHandler(1, …)` at `:923`, installed from `:940`). It is on by default (`com_overlayGuard 1`, `qcommon/common.c:1828`).
- It parks forever any thread whose access violation is not inside openmohaa.exe, game, cgame or the renderer DLL (`:836-900`).
- Under Wine, faults in Mesa, winex11 or DXVK code have no Windows module for `GetModuleHandleExA` to find, so they are treated as foreign and the thread is parked. If that thread is the main or render thread, the game **freezes instead of crashing**.
- Wine-internal handled exceptions also reach this handler first.
- Recommend `+set com_overlayGuard 0` under Proton, or auto-disable it when `ntdll!wine_get_version` exists.

## NICE-TO-HAVE / informational

- **Module names on Linux.** No fork code hardcodes `.dll` for loading.
  - Game: `"game" DLL_SUFFIX DLL_EXT` (`sys/new/sys_main_new.c:241`). Cgame: `"cgame" …` (`:309`). Renderer: `"renderer_%s" DLL_SUFFIX DLL_EXT` (`client/cl_main.cpp:3453-3466`).
  - `DLL_EXT ".so"` (`qcommon/q_platform.h:264`). `DLL_SUFFIX` is empty in release (`:84-86`; `-dbg` only in debug). `TARGET_BIN_SUFFIX ""` (`CMakeLists.txt:79`), `PREFIX ""` (`code/cgame/CMakeLists.txt:31-32`, `fgame/CMakeLists.txt:79-80`, `renderergl2/CMakeLists.txt:37-38`).
  - Result: **`game.so`, `cgame.so`, `renderer_opengl1.so`, `renderer_opengl2.so`**, with no arch tag.
  - `.dll` literals in fork code appear only in Windows-guarded code (`sys_win32.c:843-844`, `tr_hzm_vram.c:303,569,626`) or in report text (`cl_bugreport.cpp:2246`).
- **MSVC-only CMake flags are all inside `if(MSVC)`**: `/Zi /DEBUG /MAP` (`CMakeLists.txt:29-44`), cgame (`code/cgame/CMakeLists.txt`), fgame `/MAP`.
  - `#pragma comment(lib, …)` in `cl_bugreport.cpp:64-66` and `cl_dedicated.cpp:~39-40` sits inside `_WIN32` blocks. It is ignored by MinGW, which is irrelevant for Linux.
  - `renderergl2/CMakeLists.txt` gained a UTF-8 BOM, which CMake accepts.
  - The fork's `code/sdl/CMakeLists.txt:16` change actually fixes an upstream variable name.
- **Fork Win32 code is all guarded, with stubs on Linux.**
  - `cl_dedicated.cpp:55-721` (CreateProcess `omohaaded.exe` at `:517`, Job object at `:529`, BCrypt at `:443`) has a stub `#else` at `:708`, so the coop "Dedicated" button does nothing on Linux.
  - `hzm_diag.c` watchdog (`:721` `#if _WIN32 && _M_X64` … `#else` stubs) uses SEH, Toolhelp and SuspendThread (`:783,838`). On Linux `HzmDiag_Micros` falls back to ms×1000 (`:127-139`), which affects diagnostics only.
  - `tr_hzm_perf.c:17-40` (QPC, else fallback). `tr_hzm_vram.c` (DXGI/PDH on a worker thread, `:275-326`, `:444-743`, `CreateThread` at `:730`). `tr_hzm_lens.c:38-87` (crash VEH, inert by default). `sdl_glimp.c:453-487` (`r_captureSafe` WS_EX_LAYERED).
  - `scriptvm.cpp:50-77` (GetThreadTimes / `clock_gettime`).
  - SSE2 intrinsics in `renderergl2/tr_model.cpp:28,3750-3752` are fine on x86_64.
  - No hardcoded drive letters were found in fork code. The only hit is a comment-adjacent `"\\."` drive-root case in `cl_dedicated.cpp:157`, which is Windows-guarded.
- **Filesystem and case sensitivity.** These are upstream and work on Linux.
  - Inside pk3s, lookup is case-insensitive: `FS_HashFileName` lowercases (`qcommon/files.cpp:409-417`) and `FS_FilenameCompare` (`:1195`) is used in `FS_FOpenFileReadDir` (`:1292…`).
  - Loose files are case-corrected: `FS_BuildOSPath` → `FS_CorrectCase` (`:628-643`, `:585`), which uses `check_filecase`'s `opendir` + `Q_stricmp` scan per path component on non-Windows (`:532-578`). It costs a directory scan on a miss, which is acceptable.
  - Defaults: `fs_homepath` is `$XDG_DATA_HOME`/`~/.openmohaa` (`sys/sys_unix.c:64-120`, `q_shared.h:80`), and Flatpak is handled. Pass `+set fs_homepath` explicitly, as the Windows updater does.
  - Fork-added raw `fopen`s are cwd-relative log files (`cl_main.cpp:3819` `hzm_fatal.log`, `tr_hzm_lens.c:62`) or Windows-only. The cwd must be writable.
  - HTTP: there is no WinHTTP or WinINet anywhere. The engine uses upstream libcurl (`code/thirdparty/curl-8.15.0`, `qcommon/CMakeLists.txt:89`; `libcurl.dll` ships per `publish_release.ps1:106`). Pak sha256 checking is done by `updater.ps1:282-299`, not the engine.
- **Resolution and FOV on the Deck.** `r_mode` defaults to **-2** (desktop resolution, `renderergl2/tr_init.c:1518`), so 1280×800 is native even though it is not in the mode table (`:581-592`).
  - FOV is hor+ against 4:3: `fov_ratio = w/h*0.75`, `fov_x = 2·atan(tan(fov/2)·ratio)` (`cgame/cg_view.c:7789-7793`). 16:10 is correct.
  - The UI is a 640×480 virtual canvas (`uilib/uiwinman.cpp:730`). Check menus visually at 16:10.
  - Performance: there is lots of gl2 post-FX, volumetric clouds and water on an 8-CU RDNA2 iGPU. FSR 1 render scale already exists (`tr_glsl.c:1872-1893`). Plan a "Deck" preset.
- **UI with a pad alone works.** The left stick drives a cursor, D-pad focus-walks widgets (`UIWindowManager::PadNavigate`), the right stick scrolls, and stick-over-slider switches to focus mode (`sdl/sdl_input.c:1122-1236`). The console disables the pad (`:1360-1362`). Pad init runs on an SDL thread after the first 60 frames (`:1014-1016`); `SDL_HINT_JOYSTICK_THREAD` is a Windows-only hint and harmless.
- **Crash handling.** The fork removed the SIGSEGV/SIGILL/SIGFPE handlers on all platforms (`sys/sys_main.c` diff; comment at the removed `signal(SIGSEGV…)`). On Linux a crash now dies without the ioq3 "Received signal" cleanup message. It is still core-dumpable.
- **Registry and CD key.** The only registry use is the bug report's `RegGetValueA` for the CPU name (`cl_bugreport.cpp` Windows block). There is no Discord or Steam SDK. The Discord button is `Sys_OpenURL` via `SDL_OpenURL` (`sys_main.c` diff), which works through xdg-open, though maybe not inside gamescope Game Mode.

## Proton quick list (Windows exe under Wine)

| item | risk | anchor |
|---|---|---|
| Updater/launcher (vbs→PowerShell, System32 curl.exe, WinForms) | **breaks**: launch openmohaa.exe directly with the 3 args | `updater/launch_coop.vbs:7`, `updater.ps1:67,224,130` |
| Bug report upload (PowerShell) | breaks, reports "3" | `cl_bugreport.cpp:3420-3436` |
| Overlay guard VEH parks non-PE faulting threads | possible hang instead of crash | `sys_win32.c:836-923`, `common.c:1828` (`com_overlayGuard 0`) |
| `r_captureSafe` WS_EX_LAYERED on the GL window | Wine layered+GL can go slow or black; `r_captureSafe 0` | `sdl_glimp.c:453-487`, call `:1037` |
| osk.exe for pad Y | no-op; use Steam+X | `sys_win32.c:1077` |
| DXGI/PDH VRAM probe | DXVK dxgi/Wine PDH; menu-only worker thread, low risk | `tr_hzm_vram.c:303,569,626,730` |
| VC++ runtime not shipped | Proton's builtin msvcp140 is usually fine; add `vcrun2022` if STL imports fail | `publish_release.ps1:101-103` |
| SDL2.dll / OpenAL64.dll / libcurl.dll shipped beside exe | fine | `publish_release.ps1:104-106`; AL default `OpenAL64.dll` `snd_openal_new.cpp:235` |
| Dedicated child (CreateProcess + Job object + BCrypt) | Wine supports these; likely OK | `cl_dedicated.cpp:443,517,529` |
| Steam Input under Proton | XInput Xbox 360 → `xbox`, 0.10 deadzone, Xbox glyphs (good) | `sdl_input.c:639-650` |
| GOG path from updater ini; absolute Windows paths | GOG data must sit in the prefix or a Z:\ path | `updater.ps1:118-130` |
