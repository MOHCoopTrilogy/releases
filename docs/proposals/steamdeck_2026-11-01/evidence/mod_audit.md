# HZM MOHAA Coop: Steam Deck feasibility audit (mod side)

Date: 2026-11-01. This was read-only: nothing was built, run, or edited. Repo: `C:\mohaa-coop-dev`. I did not open the GOG folder, `G:\mohaa-gl2` or `%APPDATA%`.
Scanner: `case_scan.py` (in this folder). Raw results: `case_scan_result.json`.

> Engine-tree caveat: the `C:\mohaa-coop-dev\openmohaa-hzm` checkout is at `277bdb9d`, dated 2026-10-12, on branch
> `hzm-coop-working`. It does **not** contain the shipped gamepad code (`in_gamepad`, `in_padGame`, `joy_lookX`, menu pad
> navigation). That code is in `H:\hzm_work\eng-hotfix13661\code`, and I cite that tree wherever it applies.

---

## Ranked findings

### BLOCKERS

**B1. The only install/update/launch path runs on Windows alone.**
- Installer: `installer/webinstall.iss` is an Inno Setup `.exe`. It finds GOG through HKLM registry keys (`:86`, `:88`, `SOFTWARE\[WOW6432Node\]GOG.com\Games\1207659126`) and writes `.lnk` shortcuts (`:59-62`).
- Launcher: the shortcut runs `updater/launch_coop.vbs`. Its line 7 runs `powershell.exe -ExecutionPolicy Bypass -File updater.ps1`. Wine/Proton has `wscript` but **no powershell.exe**, so the game never starts through this path.
- Updater: `updater/updater.ps1` (477 lines) is PowerShell 5.1. It writes the WER registry key `HKCU:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps` (`:28`), calls `%SystemRoot%\System32\curl.exe` (`:224`), and re-launches itself through `wscript.exe` (`:106`). It builds the game command line at `:130`/`:141`/`:146`.
- Release README: `README.md:37` says "**Needs:** Windows, a GOG install…, about 10 GB free". `:29` and `:42` describe a `%LOCALAPPDATA%` install.
- Release staging ships only win64 binaries: `publish_release.ps1:85-106` (openmohaa.exe, cgame/game/renderer DLLs, SDL2.dll, OpenAL64.dll, libcurl.dll).
- **Deck workaround:**
  1. Install the GOG game under Proton (Heroic/Lutris).
  2. Unzip the "NoInstaller" zips, which `publish_release.ps1:331-433` builds.
  3. Add `openmohaa.exe` to Steam as a non-Steam game, with the launch arguments the installer writes (`webinstall.iss:251`): `+set fs_basepath "<gog>" +set fs_homepath "<app>\home" +set com_target_game 2 +set cl_renderer opengl2`.
- **Proper fix:** a portable updater (Python or bash) that reads `manifests/latest.json`. Every entry is just {path, size, sha256, url}, so nothing in it is Windows-specific. Alternatively, ship a Linux engine build.

**B2. The engine's HZM additions contain Windows-only code.**
These parts are wrapped in `#ifdef _WIN32`:
- The VRAM probe `renderergl2/tr_hzm_vram.c:43,297,486,1080,1130` (DXGI + registry). On Linux it falls back to `GL_ATI_meminfo`, which radeonsi does expose.
- `tr_hzm_perf.c`.
- `cgame/cg_main.c`.
- The on-screen keyboard (see B3).

Under Proton the Windows build runs on the host's OpenGL (Mesa radeonsi), and that is the realistic route. A native Linux build would need those blocks ported. Also, `coop_gfxRecommended` would rate the Deck low: the engine is single-core bound and skins on the CPU (`client/cl_hzm_recommend.cpp:7-12`), and the score is normalised to a Ryzen 7 9700X (≈4650 PassMark single-thread). The Deck's Zen2 at 3.5 GHz scores roughly half that, which lands at Low/Medium.

**B3. Text entry depends on the Windows on-screen keyboard.**
Pad Y in menus calls `Sys_OpenOnScreenKeyboard()` only under `#ifdef _WIN32` (`eng-hotfix13661/code/sdl/sdl_input.c:1305-1307`; the menu map is documented at `:1116-1128`). Under Proton it would try to start the Windows OSK, which does not exist there. The menus that need typing are:
- `ui/coop_start.urc:34` (sv_hostname), `:62` (password), `:87` (sv_maxclients), `:309` (coop_lmsLives), `:335` (coop_health)
- `ui/coop_mp_options.urc:112` and `ui/multiplayeroptions.urc:146` (ui_name, the player name)
- `ui/joininternetgame.urc:46` (ui_connectip)
- `ui/coop_report.urc:144,168` (bug report text)
- `ui/multiplayerstart_*.urc` (ui_hostname and the limits)
- chat binds `say`/`sayteam`/`messagemode` (`installer/omconfig_default.cfg:35,39,46`)
- the console, for rcon and `connect`

12 urc files contain `Field` widgets. Mitigation: Steam's keyboard (STEAM+X) works in Game Mode. A real fix would call `SDL_StartTextInput` on focus (SDL can raise the Steam keyboard) and add an in-game pad keyboard.

### IMPORTANT

**I1. Install size: 8.68 GB, and every file is mandatory.**
`manifests/latest.json` (v1.10.49) lists 60 files and has **no optional/group field**, so the updater downloads all of them. On top of that come the GOG game and the `.tmp` copies made during a download. `README.md:30` says "about 8 GB", and `:37` asks for 10 GB free.

| pak | MB | content |
|---|---:|---|
| zzzzzz_co-op_hzm_mod_assets_tex.pk3 | 1309 | **2394 uncompressed TGA (3.09 GB unpacked)** + 1920 JPG + 265 DDS |
| zzzzzzz_dds_hdmem.pk3 (HD) | 1020 | DDS siblings for HD textures (`publish_release.ps1:180-182`) |
| zzzzz-AA_HD_Project_Pak1-4 (HD) | 254+954+883+719 | third-party HD textures (in the GOG folder, not inspected) |
| zzzzzz_co-op_hzm_mod_assets_snd.pk3 | 631 | 922 mp3 + 1548 wav |
| zzzzzzz_dds_override.pk3 (HD) | 508 | DDS |
| zzzzzz_hd_world.pk3 (HD) | 378 | HD world |
| zzzzzz-HRRTM_Pak3_Textures (HD) | 369 | |
| zzzzz_hd_foliage (HD) | 194 | |
| coop_fixes / coop_fixes2 | 158 / 165 | TGA-heavy (~95 MB TGA each) |
| coop_hd_m3l1a / _skies / _a_tilefix / _shadowfix | 152 / 105 / 91 / 32 | DDS, except **skies = 61 uncompressed TGA (541 MB unpacked, 39 at 2048²)** |
| HRRTM Pak2/4/4c, hd_charskins, xw_weapons, gunsounds, hd_fx, skybox, geared | 137/41/43/92/40/32/18/17/16 | |
| coop_music 108, terrain 75 (DDS), code 30, menus3d 28, tileart 20, rest <10 | | |

- Third-party HD set (the 18 `$hdPaks` at `publish_release.ps1:171-179`, plus hdmem and fxfix): **≈5.68 GB**. The coop mod's own HD paks add ≈0.38 GB. A "Deck lite" without the HD packs would be about **2.6 GB**. I have not verified that the mod's .tik files never reference HRRTM or geared_soldiers models, so audit that before making those paks optional.
- The `coop_loadclips*.pk3` files (3 × 1.3 GB, `.hzlc`) sit in the mod dir but are **not staged** (no hits in build.ps1 or publish_release.ps1). Good: they are dev-only.

**I2. VRAM pressure.**
- `r_ext_compressed_textures 1` is seeded (`coop_defaults.cfg:74`). With it, gl2 loads `.dds` first (`renderergl2/tr_image.c:2533-2544`), and the driver compresses RGBA8 uploads to DXT1/DXT5 at load time (`tr_image.c:1761-1844`). That costs CPU and load time, which matters on a 4-core Zen2.
- All 2394 TGAs in assets_tex as RGBA8 with mips would be **4.84 GB** (sizes from the TGA headers: 189 at 2048², 288 at 1024², 406 at 882 px, which is non-power-of-two and gets resampled). The HD skies alone would be 0.96 GB.
- Only one map's subset is resident at a time. My **estimate** (not measured) is 0.8-1.5 GB at the shipped High with compression, and 0.4-0.7 GB with `r_picmip 1`. That fits the Deck's 1 GB UMA default plus GTT spill, but 4 GB UMA in the BIOS is the safer choice.
- `r_hzmGenNormals 1` is **FORCED** at `autoexec.cfg:1829`. It adds a generated normal map per texture (capped at 256 px, `:1845`). Because it is forced, a user cfg cannot turn it off.
- The in-game memory gauge `r_vramShort*` (`gen_menu_graphics.py` DEFAULT_EXCLUDE, about line 418) can verify the estimate on a real Deck.

**I3. CPU-bound engine.** Per `cl_hzm_recommend.cpp:7-12`, game, effects, drawing and skinning all run on one core. AI duplication by player count is gated by `coop_aiScale` (default on, chance 50, `coop_mod/aihandler.scr:223-230`), with `level.coop_aiScaleHardCap = 80` live actors (`coop_mod/variables.scr:100`) and `coop_aiDynamic 1` (`autoexec.cfg:673`). A Deck *hosting* a 4-player listen server will be CPU-limited on crowded maps like Omaha. The Deck should join rather than host, or host with a lower `coop_aiScaleChance`.

**I4. Shipped defaults assume a desktop GPU.**
`coop_defaults.cfg` seeds:
- `com_maxfps 200` (`:223`), `r_msaa -1` auto (`:193`)
- SSAO/DoF/bloom/FXAA/heat haze/CA all on (`:90,120,125,127,130,328`)
- `r_shadowMapSize 2048` (`:38`), `cg_shadows 2` (`:55`), `r_hzmDlightShadows 1` (`:327`)
- `cg_effectdetail 1` (`:13`), `cg_max_tempmodels 4000` (`:25`), `r_ext_max_anisotropy 16` (`:186`)
- 1920×1080 fullscreen (`:309-312`)

The 4-step presets in `gen_menu_graphics.py:286-336` exist (Low/Medium/High/Ultra; High = the coop_defaults seed). The volumetric clouds' auto mode switches off only for Intel iGPUs (`renderergl2/tr_hzm_clouds.c:393-395`), so an AMD APU gets them unless `r_hzmClouds 0`.

**I5. Gamepad works out of the box, but expects a pad that shows up as a normal SDL controller.**
- Pad support is on by default (`in_gamepad 1` per `coop_defaults.cfg:743-748`; analog `in_joystickUseAnalog 1` at `:748`, deadzones `:749-753`).
- The full default layout is in `coop_mod/cfg/coop_defbinds1.cfg:9-36`. It runs once per profile through `alias coop_defBinds1` (`coop_defaults.cfg:255-261`). Later deltas are in `coop_defbinds2.cfg:4-5`, `coop_defbinds3.cfg:4-5` (`PAD0_TOUCHPAD`/`MISC1`) and `coop_defbinds4.cfg:11` (`PAD0_Y "+coopwheelpad"`, the weapon wheel). Reset-to-defaults file: `coop_mod/cfg/coop_padbinds_default.cfg`.
- The stick-direction binds are required for analog input (`autoexec.cfg:136-138`).
- Lean is on `PAD0_PADDLE1-4` (`coop_defbinds1.cfg:33-36`). Under default Steam Input the Deck appears as an Xbox 360 pad with **no paddles**, so lean needs a Steam Input mapping of L4/R4 to a keyboard key (q/e, `coop_defbinds1.cfg:6-8`), or Steam Input turned off so SDL's native Deck driver is used.
- The sensitivity sliders come from `docs/tools/gen_menu_padaim.py:15-24` (joy_lookX 1.0, joy_lookY 0.8, joy_adsScale 0.6, deadzones 0.15/0.05, response 1.5, accel 0.6 s / 1.5x), writing `ui/coop_padaim.urc`. Layout page: `ui/coop_padlayout.urc`. Controller mode toggle: `ui/coop_controls.urc:60,86`.
- Aim assist is off by default (`coop_defaults.cfg:659-663`). For handheld coop, consider defaulting it on.
- Menus: the left stick moves a mouse cursor, D-pad moves focus, A clicks, B/Start goes back, LB/RB switch tabs (`eng-hotfix13661 sdl_input.c:1116-1128`). Menus are cursor-first but every widget can be reached with the pad. There is no gyro support; Steam Input can map gyro to the mouse.

### NICE-TO-HAVE

**N1. Case sensitivity is hygiene only, not a blocker.**
- The engine is case-insensitive on Linux for pk3 contents: `FS_HashFileName` lowercases (`qcommon/files.cpp:417`) and `FS_FilenameCompare` ignores case and treats `\` as `/` (`:1195`). Loose files go through `FS_BuildOSPath` → `FS_CorrectCase` (`:585`, `:643`), which does a readdir case-fold with `check_filecase` (`:531-575`).
- Proton/Wine is case-insensitive anyway.
- Scan result (`case_scan.py`): 24,802 indexed files (27 pk3 + loose tree), 27,213 text files, 111,918 asset references. 80,792 match exactly and 29,059 resolve to nothing in the mod (retail paks). **511 referenced paths, at 2,067 sites, match a mod file only case-insensitively.** By site, the references sit in .scr 1512, .tik 367, .shader 84, .cfg 70, .txt 34. By path, they cluster in `sound/dialogue` 267, `sound/weapons` 45, `sound/characters` 33, `models/player` 27, `models/human` 25. Examples:
  - `models/human/animation/dialogue/generic_dialogue_US.tik` vs the real `Generic_dialogue_US.tik` (124 sites)
  - `models/player/allied_airborne.tik` vs `allied_Airborne.tik`
  - `maps/m1l3a.scr` vs `maps/M1L3a.scr` (in `coop_mod/loadout.scr`)
  - `global/fakegunfire.scr` vs `global/FakeGunfire.scr`
  - `coop_mod/player_Torso.st` vs `player_torso.st` (in `coop_mod/ads_dbg.scr`)
  - `maps/e1l4/ship.scr` vs `Ship.scr` (in `coop_mod/challenges.scr`)
- Case-only duplicates: 0 inside any single pk3 and 0 inside any tree directory. 29 differ in case **across** paks or between tree and pak, for example `models/weapons/FG42.tik` vs `fg42.tik` (assets_tex/tey/fixes/fixes2/stress/scopeglass) and `textures/coop_v3/*/ThompsonSMG.tga` vs `thompsonsmg.tga`. The engine treats these as one file, so the last pak wins either way. They would only matter to an external tool that unpacks to a case-sensitive disk.
- Packed vs loose: everything ships in pk3 except `home/maintt/autoexec.cfg`, `whatsnew_pending.cfg` and `dedicated_example.cfg` (`publish_release.ps1:110,165,169`), plus the installer-seeded `omconfig` and the root binaries. All the loose names are lowercase.

**N2. UI at 1280×800: works, with a mild 4:3 stretch.**
- 115 of 182 urc files use `virtualres 1` (640×480 virtual, scaled). 5 use `virtualres 0`: coopAdmin, coopDev, coopMomMenuExample, coop_objectives, hud_compass. 66 have no `virtualres` (the hud_ammo_* files, hud_health, hud_score, morocco*).
- By default (`ui_menuCenter 0`) the virtual screen is stretched per axis: ×2.0 horizontally, ×1.667 vertically at 1280×800. That is a 1.2:1 horizontal widget stretch. `ui_menuCenter 1` gives a centred 4:3 board instead (`uilib/uiwidget.cpp:668-676`).
- Text uses the *vertical* factor on both axes (`ui_textUniform 1`, `uilib/uifont.cpp:318-338`), so glyphs are not distorted.
- Fonts: verdana-12 is used 2,389 times, facfont-20 787, courier-16 199, handle-23 5, verdana-14 2. In virtualres menus verdana-12 renders at ≈20 px at 800p. Readable (≥12 px).
- HUD text in cgame drawn with `uiHiResScale` is **1:1 pixels below 1080p** (`client/cl_ui.cpp:4225-4238`, explained in `cgame/cg_coopfeed.c:118-121`). At 800p the kill feed, bleed text and similar use the font's native height: verdana-12 is about 12 px tall, roughly 9 px cap height. That meets Valve's 9 px floor but not the preferred 12 px. Suggest a cgame HUD-text scale floor such as `max(1, vidHeight/720)`.
- `virtualres 0` menus are fixed-pixel. coopAdmin and coop_objectives would sit small or in a corner at 800p and should be checked.
- No `widescreen`/`aspect` handling in the urc files (1 incidental hit).

**N3. FOV is Hor+.** The cgame turns the 4:3 FOV into a horizontal FOV for the actual aspect (`cgame/cg_view.c:7449-7453`, fov_ratio = w/h × 3/4). The default 80 (`cg_fov`, engine `cg_main.c:252`; `fov` userinfo is unseeded) gives ≈90° horizontal at 16:10. Keep it.

**N4. No drive-letter or backslash paths in shipped content.** I scanned every .scr/.cfg/.urc/.tik/.shader/.txt/.st/.mus in the code, menus3d, late, stress, maps and fixes2 paks, plus autoexec.cfg, coop_defaults.cfg, omconfig_default.cfg, whatsnew_seed.cfg and dedicated_example.cfg. Only 3 comment hits (maps/, scripts/, ubersound/); no code hits. Hard-coded `C:\mohaa-coop-dev` / `G:\GOG…` exist only in build-side `publish_release.ps1:26-27`. Install paths are created at install time (`webinstall.iss:243-251`).

---

## Steam Deck preset (proposed)

Values come from `coop_defaults.cfg` (the "High" seed) and `autoexec.cfg`, with gen_menu_graphics Low/Medium for comparison.

| cvar | shipped default (anchor) | Low / Med preset | **Deck** | why |
|---|---|---|---|---|
| r_mode / r_customwidth / r_customheight | -1 / 1920 / 1080 (`coop_defaults:309-311`) | n/a (excluded) | **-1 / 1280 / 800** | native panel, 16:10 |
| r_fullscreen | 1 (`:312`) | n/a | 1 | gamescope |
| cl_renderer | opengl2 (`:363`, `autoexec:963`, updater `:141`) | n/a | opengl2 | needed for FSR and presets |
| r_renderScale / r_fsrSharpness | 1.0 (`:102`) / 0.25 (`:104`) | 0.85 / – | **0.75 / 0.4** | FSR1 EASU from 960×600; fill-rate/power |
| com_maxfps | 200 (`:223`) | skipped by presets | **60** (40 or 45 for battery, set the panel Hz to match) | 15 W budget; CPU-bound engine |
| r_swapInterval | 1 (`:196`) | skipped | 1 | no tearing; gamescope caps |
| r_hzmFrameGen | 0 (engine `tr_hzm_framegen.c:2793`) | skipped | 0 | adds iGPU compute and latency |
| r_msaa / r_ppFXAA | -1 / 1 (`:193`,`:125`) | 0 / 0 (Low), 0 / 1 (Med) | **0 / 1** | FXAA is cheap; MSAA is not on an APU |
| r_ext_max_anisotropy | 16 (`:186`) | 2 / 8 | **4** | |
| r_picmip | 0 (`:211`) | 1 / – | **1** | quarters TGA VRAM (2048² skins/skies) |
| r_ext_compressed_textures | 1 (`:74`) | – | 1 | keep: DDS first, DXT on upload |
| r_hzmGenNormals | 1 FORCED (`autoexec:1829`) | – | **0** (needs the autoexec gate changed) | VRAM + load time |
| r_ppSSAO / r_ppDoF | 1 / 1 (`:130`,`:120`) | 0 / 0 | **0 / 0** | heaviest post-FX |
| r_ppBloom | 1 (`:90`) | 0 / – | 1 | cheap at 0.75 scale; 0 for battery |
| r_ppHeatHaze / r_ppChromaticAberration | 1 / 1 (`:127`,`:328`) | 0 | **0 / 0** | |
| r_softParticles | 1 (`:106`) | 0 | **0** | depth reads |
| r_sunShadows / r_shadowMapSize | unseeded / 2048 (`:38`) | 0 | **0 / 1024** | |
| cg_shadows | 2 (`:55`) | – | **1** (blob) | |
| r_hzmDlightShadows | 1 (`:327`) | – | **0** | per-light shadow passes |
| r_dynamiclight / r_dlightMode | 1 (`:234`) / 1 FORCED (`autoexec:988`) | – | 1 / 1 | gameplay-relevant muzzle light |
| r_hzmClouds | -1 auto (`tr_hzm_clouds.c:129`) | – | **0** | auto excludes only Intel |
| r_hzmWater / r_hzmWet / r_groundVariety | -1 / -1 / -1 (`:276-280`) | 0/0/0 (Low) | **0 / 0 / 0** | |
| cg_footprints | 1 (`:16`) | 0 | 0 | |
| cg_effectdetail | 1 (`:13`) | 0.5 / 0.8 | **0.6** | particles cost CPU |
| cg_max_tempmodels | 4000 (`:25`) | 1024 / 2048 | **1024** | |
| cg_marks_max | 487 (`:202`) | 128 / 256 | **128** | |
| r_subdivisions | 4 (`:198`) | 20 / 10 | **10** | curve tessellation |
| r_lodscale | 28 (`:78`) | 5 / 24 | **24** (5 on crowded maps) | CPU skinning is the bottleneck (bug-3483) |
| cg_rain / coop_weatherForce | 1 (`:209`) / "" (`autoexec:1475`) | – | 1 / "" | keep weather; set "off" if fps drops in storms |
| coop_goreWoundMax / coop_goreChunks | 8 / 1 (`:575`,`:637`) | – | 4 / 1 | fewer decals |
| coop_aiScaleChance (server) | 50 (`aihandler.scr:229-230`) | – | **35 when the Deck hosts** | entity/CPU budget (cap 80, `variables.scr:100`) |
| fov | 80 (engine) | – | 80 | Hor+ ≈ 90° at 16:10 |
| ui_menuCenter | 0 | skipped | 0 (1 if the stretch bothers you) | |
| in_gamepad / in_joystickUseAnalog | 1 / 1 (`:743-748`) | – | 1 / 1 | |
| coop_aimAssist | 0 (`:659`) | – | 1 | handheld coop only (MP-gated) |

Delivery: generate a `gfx_preset_deck.cfg` beside the four generated preset cfgs (extend `PRESET_NAMES`/`PRESET_VALUES` in `gen_menu_graphics.py:295-332`). Resolution, fps and VSync are deliberately skipped by presets (`PRESET_SKIP`, `:333`), so put them in a separate one-shot "Deck" cfg or the launch arguments.

---

## Release pipeline (publish_release.ps1, 576 lines)

1. **Preflight** (`:34-62`): gh auth, SemVer check, refuses an existing tag, and checks that the What's New card title (`ui/coop_whatsnew.urc`) matches the version.
2. **Build** (`:64-77`): runs `build.ps1` and aborts on a throw or a non-zero exit.
3. **Stage** (`:79-197`): win64 engine binaries from the GOG root (`:85-106`), `dedicated_example.cfg` (`:110`), `updater.ps1`, `launch_coop.vbs`, `report_problem.ps1` (`:112-114`), the 3 core mod pk3s (`:116`), the out-of-band pk3s (`:122-164`), `autoexec.cfg` (`:165`), `whatsnew_pending.cfg` (`:169`), the 18 third-party HD paks plus dds_hdmem, hd_fxfix and xw_weapons from `G:\GOG…\maintt` (`:171-192`). It then checks every staged file exists (`:197`) and guards against a test-named or VCL-test renderer being staged (`~:255-262`).
4. **Manifest** (`:272-330`): sha256 for every file; unchanged files keep the previous release's URL.
5. **4b alternative downloads** (`:331-433`): NoInstaller and ModFilesOnly multi-part zips with INSTALL.txt, plus SHA256 lines.
6. **Publish** (`:434-503`): gh release from draft to published; the web installer is attached with `--clobber` (`:478-490`).
7. **Record manifests** in `manifests/` (`:504-515`).
8. **Discord announcement** (`:516-548`), optional.
9. **Archive PDBs** (`:549-576`).

Updater: `updater/updater.ps1`, started hidden by `launch_coop.vbs`. It diffs the remote manifest against `installed_manifest.json`, downloads `.tmp` files with `curl -C -`, verifies sha256 before swapping, and never blocks play. Windows-only, as listed under B1.
Windows-only shipped files: `MOHCoopTrilogy-WebSetup.exe`, `launch_coop.vbs`, `updater.ps1`, `report_problem.ps1`, the `.lnk` shortcuts, plus dev-only `.ps1`/`.bat` scripts at the repo root (not shipped).

## Suggested Deck work order
1. A portable updater/launcher (Python, reading `manifests/latest.json`), plus a "Steam Deck / Linux (Proton)" README section with the non-Steam-game launch arguments.
2. A `gfx_preset_deck` preset, and un-force `r_hzmGenNormals` in autoexec.
3. An OSK fallback: `SDL_StartTextInput` when a Field gains focus, which can raise the Steam keyboard in Game Mode.
4. Optional HD groups in the manifest (a "lite" install of about 2.6 GB), after auditing which mod tiks depend on HRRTM or geared models.
5. A minimum size for HUD hi-res text at ≤800p.
6. Optionally, run `case_scan.py` as a lint and fix the 511 mismatches (cosmetic for the engine, useful for external tools).
