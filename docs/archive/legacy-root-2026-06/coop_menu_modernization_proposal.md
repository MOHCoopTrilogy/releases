# Coop Main-Menu Rebuild + Modernization Proposal (HZM Coop / OpenMOHAA, Breakthrough profile)

Date: 2026-06-24
Scope: RESEARCH + PROPOSAL ONLY. No mod files edited, no pk3 rebuilt, no game launched
(a live map-rotation test is running). All paths below are absolute.

Engine source read: `C:\mohaa-coop-dev\openmohaa-hzm` (the NO_MODERN_DMA / old-SDL-sound build).
Mod read: `C:\mohaa-coop-dev\hzm-mohaa-coop-mod` and the deployed pak
`C:\mohaa-coop-dev\zzzzzz_co-op_hzm_mod_mohaa.pk3`.

---

## TL;DR (read this first)

- **The single most important conclusion: the user should provide an MP3, not a WAV.**
  Recommended format: **MP3, 44.1 kHz (or 22.05 kHz), stereo, CBR 128-192 kbps, full length,
  named `mus_MainTheme.mp3`.** MOHAA's menu theme is *already* an MP3 and this build streams
  MP3 via libmad on the active sound path. WAV is NOT required and is actively worse (PCM WAV
  is loaded whole; long tracks are huge and have crashed this build's load path before).
- **Easiest music wire-in (zero engine change, zero menu change):** drop the file at
  `sound/music/mus_MainTheme.mp3` inside the coop pak. The engine's
  `S_TriggeredMusic_PlayIntroMusic()` hardcodes that exact path; the coop pak sorts last and
  wins, so it overrides the stock theme automatically.
- **Menu art:** must be **TGA or JPG** (PCX/BMP also accepted; **PNG is NOT** in the active
  renderer's image dispatch). DDS only when S3TC is on.
- **The coop start plumbing (`ui_dmmap` -> Apply -> `coop_mod/start_server.cfg` -> `g_gametype 2`
  -> `ui_startdmmap 2`) and the maptest harness can be left 100% intact.** A reskin touches art,
  fonts, layout, and music only. **Verdict: SAFE**, if you follow the rules in section (d).

---

## (a) Current menu architecture (files + coop start flow)

### a.1 The UI system in this engine

MOHAA menus are `.urc` resource files parsed by the in-engine UI library. Relevant source:

- UI lib: `C:\mohaa-coop-dev\openmohaa-hzm\code\uilib\` -- one C++ class per widget type:
  `uiwidget.cpp` (base), `uilabel.cpp`, `uibutton.cpp`, `uicheckbox.cpp`, `uifield.cpp`,
  `uipulldownmenucontainer.cpp`, `uipulldownmenu.cpp`, `uimenu.cpp` (the menu/screen container),
  `uifont.cpp` (font handling), `uiwinman.cpp` (window manager).
- Client glue: `C:\mohaa-coop-dev\openmohaa-hzm\code\client\cl_ui.cpp` (binds engine callbacks
  into the UI lib, e.g. `cl_ui.cpp:3759  uii.Rend_LoadFont = re.LoadFont`).

Widget keys are registered as events; the `.urc` parser maps each key line to a widget event.
Confirmed widget keys / capabilities usable purely from `.urc` (no engine change):

- `menu "<name>" <w> <h> <flags> <n>` header; `bgcolor`, `bgfill`, `fullscreen 1`,
  `virtualres 1` (auto-scale 640x480 design space to real resolution -- see a.4),
  `borderstyle NONE|RAISED`.
- Per-widget: `rect x y w h`, `fgcolor`, `bgcolor`, `borderstyle`, `font <name>`,
  `textalign left|center|right`, `title "..."`.
- Images: `shader "<name-or-path>"`, `hovershader`, `tileshader 0|1`,
  `linkcvar "<cvar>"` + `linkcvartoshader` (drive the displayed image from a cvar),
  `enabledcvar "<cvar>"` (show widget only if cvar set).
- Buttons: `clicksound "<wav>"`, `stuffcommand "<console cmds>"`, `hovercommand`,
  `mouseawaycommand`, `ordernumber`.
- `PulldownMenuContainer` with `addpopup "MENU" "<label>" command "<console cmd>"`.
- **Sound on a Label**: `oneshotsound "<file>"` and `loopingsound "<file>" [vol] [...]`
  (`uilabel.cpp:48-60`, handlers at `uilabel.cpp:188,192`). At runtime a looping-sound Label
  issues `tmstartloop <file>` (`uilabel.cpp:374`) -- this is the in-`.urc` music hook (see c.2).
- `globalwidgetcommand <widgetName> <key> <value>` -- used at runtime from `.cfg` files to
  repaint existing widgets (this is how the coop map slots get re-themed per mission).

What is **restylable purely via `.urc`/`.cfg` + new assets** (no recompile):
layout/rects, colors, fonts (any installed font name), all background/button art (as shaders),
hover art, click sounds, looping menu music, button command wiring, pulldown entries.

What would need **engine/cgame work** (out of scope for a reskin): new widget *types*, animated
video backgrounds beyond the existing shader-animation system, PNG support, changing the hardcoded
intro-music filename, true per-aspect art swaps.

### a.2 Vanilla / current main menu `.urc`

The coop mod ships its own main menu at
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\main.urc` (also inside the pak as `ui/main.urc`).
Structure (read in full):

- `menu "main" 640 480 NONE 0`, `fullscreen 1`, `virtualres 1` (main.urc:5,9,10).
- A grid of `Label` widgets drawing the "war room" background via shaders `main_a`/`main_b` and a
  `ui_voodoo`-gated hi-res tile set `textures/mohmenu/voodoo/main_*` (main.urc:12-104).
- A "sign" label driven by cvar `ui_signshader` (main.urc:106-118) -- the hover caption system.
- Interactive `Button` widgets, each `stuffcommand` a `pushmenu`/`spmap`/`quit`, with
  `hovercommand`/`mouseawaycommand` setting `ui_*` shader cvars: New Game -> `pushmenu briefingroom`,
  Records -> `pushmenu war_records`, Briefing, Multiplayer -> `pushmenu multiplayer`,
  Options -> `pushmenu options_main`, Credits -> `spmap credits`, Quit, Back-to-game
  (main.urc:160-401).
- **There is NO music line in `main.urc`.** Menu music is started entirely by the engine
  (see a.3 / c).

The coop *start/host* + map-select screen (the functional flow we must preserve) is a separate set:

- `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start.urc` -- host options (server name,
  password, max players, friendly fire, dedicated, LMS, health) plus the mission dropdown and the
  Apply/Back buttons.
- `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_maps.inc` -- 10 reusable thumbnail buttons
  `coop_startMap1..coop_startMap10` (5x2 grid), included at `coop_start.urc:331`.
- `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start\*.cfg` -- per-mission repaint cfgs
  (`m0,m1..m6,e1,e2,e3,t1,t2,t3`).
- Other coop UI: `coop_mom.urc`, `coop_login.urc`, `coop_objectives.urc`, `coopAdmin.urc`,
  `coopDev.urc`, `hud_compass.urc`, `multiplayerstart.urc` (all under `ui/`).

### a.3 The coop start flow (THE CONTRACT THAT MUST NOT BREAK)

End to end (verified against files and `C:\mohaa-coop-dev\coop_menu_additions.md`):

1. Mission dropdown (`coop_start.urc:150-177`, `PulldownMenuContainer coop_missionNameSel`):
   each entry is `addpopup "MENU" "<label>" command "exec ui/coop_start/<id>.cfg"`.
2. The per-mission cfg (e.g. `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_start\m1.cfg`) uses
   `globalwidgetcommand coop_startMapN shader textures/mohmenu/dmloading/<map>` and
   `globalwidgetcommand coop_startMapN stuffcommand "set ui_dmmap <map>"` to repaint the 10 slots.
3. Clicking a thumbnail runs its `stuffcommand` -> `set ui_dmmap <map>`. (A `Field` linked to
   `ui_dmmap` mirrors the choice, `coop_start.urc:181-193`.)
4. Apply button (`coop_start.urc:348-362`): `stuffcommand "wait 250;exec coop_mod/start_server.cfg"`.
5. `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\start_server.cfg` sets the coop server cvars
   -- `g_gametype 2` (start_server.cfg:25), `maxentities 2048`, `g_healrate 100000`,
   floodprotect, etc. -- and ends with `ui_startdmmap 2` (start_server.cfg:43), which boots
   `ui_dmmap` in COOP gametype (not single-player).

**The map-rotation TEST HARNESS reuses the exact same contract:**
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\cfg\maptest_start.cfg` does `set ui_dmmap <map>`
then `exec coop_mod/start_server.cfg` (maptest_start.cfg:28-29). So the harness depends on
`ui_dmmap` + `start_server.cfg` + the `g_gametype 2` / `ui_startdmmap 2` behavior -- NOT on any
menu art. The contract is: *something* must set `ui_dmmap` and then run `start_server.cfg`.

### a.4 Widescreen / hi-res scaling (already available)

`uiwidget.cpp:289 "virtualres"`, `:292 "usevirtualres"`; scaling math at `uiwidget.cpp:1048-1057`
(`scaleFrameVirtualRes(... uid.scaleRes)`). With `virtualres 1` (which `main.urc` and
`coop_start.urc` already set), the engine treats the menu as a 640x480 virtual canvas and scales it
to the real screen resolution. So **hi-res/widescreen menus need no engine work** -- just author art
at higher native resolution and keep the 640x480 rects; the engine upscales the canvas. (Art drawn
as a full-screen background shader can be a large TGA/JPG; it is sampled to fit.)

---

## (b) Modernization plan (art / layout / fonts -- exact files)

Design principle: **reskin, don't re-plumb.** Keep all widget *names*, all `stuffcommand`s, all
cvar links; change only art (`shader`), fonts, rects, colors, and add music. This keeps both the
coop launch flow and the maptest harness byte-for-byte compatible.

### b.1 Image format rules (renderer-confirmed)

Active image dispatch: `C:\mohaa-coop-dev\openmohaa-hzm\code\renderergl1\tr_image.c:2399-2469`
(`R_LoadImage`). Accepted: **`.tga`, `.jpg`** (tries jpg then tga for either extension),
**`.pcx`, `.bmp`, `.gst`**; **`.dds`** only when `glConfig.textureCompression == TC_S3TC*`.
**PNG is NOT dispatched here** (an `R_LoadPNG` exists in `renderercommon/tr_image_png.c` but is not
wired into this menu/texture path). TGA constraints (`tr_image_tga.c:106-116`): type 2/3/10 only,
24- or 32-bit, no colormaps. So:

- New backgrounds / large art with no alpha -> **JPG** (small files, fine for opaque art).
- Buttons / signs / anything needing transparency -> **32-bit TGA** (alpha channel).
- Author at hi-res (e.g. 1024 or 2048 wide for the full background); `virtualres` scales it.

### b.2 Fonts

Fonts are loaded by NAME from `fonts/<name>.RitualFont` (`tr_font.cpp:330 "fonts/%s.RitualFont"`);
default is `verdana-14` (`uifont.cpp:268`). The coop menus already use `facfont-20` and
`verdana-12`. To restyle text you either (1) reuse existing shipped font names, or (2) add a new
`.RitualFont` + its glyph page image (TGA) under `fonts/` in the coop pak and reference it via the
`font <name>` widget key. **No engine change**; this is a pure asset add. Keep using a font that
exists in the base paks if you want zero new font assets -- just change `font` lines and colors.

### b.3 Concrete edit list for a modernized look

Ship all of these INSIDE the coop pak so they win (section d). Edit the source copies under
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\` and rebuild the pak at the next coordinated build.

1. **New main-menu background** -- replace the art behind `main.urc`:
   - Option A (least intrusive): keep the existing `main_a`/`main_b`/`voodoo/main_*` shader names
     but override the underlying TGA/JPG assets in the pak (new art, same shader names) -- zero
     `.urc` edits, the new art simply replaces the old.
   - Option B: in `ui/main.urc`, repoint the background `Label` shaders to a new
     `textures/mohmenu/coop/menu_bg` TGA/JPG and simplify/remove the war-room hotspot buttons you
     don't want.
2. **Restyle buttons**: in `ui/main.urc` and `ui/coop_start.urc`, swap `shader`/`hovershader` to
   new TGA art and/or adjust `fgcolor`/`bgcolor`, `font`, `rect`. Do NOT touch `stuffcommand`,
   `linkcvar`, or widget `name`s.
3. **Coop start screen polish** (`ui/coop_start.urc` + `ui/coop_maps.inc`): update the field/label
   colors, the HZM logo shader (`coop_maps.inc:10 textures/mohmenu/coop/hzm_coop_mod_logo`), the
   footer version string (`coop_start.urc:376-385`), and the map-thumbnail button frames. The 10
   slot names and their per-mission repaint cfgs are untouched.
4. **Optional layout cleanup**: the `coop_start.urc` host fields can be re-laid-out freely (rects)
   as long as each `Field`/`CheckBox` keeps its `linkcvar` and the Apply button keeps its
   `stuffcommand "wait 250;exec coop_mod/start_server.cfg"`.
5. **Loading screens** (optional theme cohesion): `ui/loading_coop_morocco.urc` and the
   `textures/mohmenu/dmloading/*` thumbnails can be re-arted (TGA/JPG) to match.

Achievable via `.urc` + assets only: everything in 1-5. Needs engine/cgame work (skip): animated
video background, new widget types, PNG, runtime aspect-ratio art swaps.

---

## (c) Music integration recipe (Operation Market Garden theme)

### c.1 How menu music actually plays in THIS build (NO_MODERN_DMA)

Build flags (`C:\mohaa-coop-dev\openmohaa-hzm\code\client\CMakeLists.txt`):
- `USE_CODEC_MP3` is defined **unconditionally** (CMakeLists.txt:24) and **libmad is always linked**
  (CMakeLists.txt:65-80).
- Under NO_MODERN_DMA the build EXCLUDES `snd_*.cpp` but COMPILES all `snd_*.c` plus `new/*.c*`
  (CMakeLists.txt:49-59). Verified compiled set includes `snd_dma.c`, `snd_main.c`,
  `snd_codec.c`, `snd_codec_mp3.c`, `snd_codec_wav.c`, and `new/snd_main_new.cpp`.

So the active music path is the Q3-style background-stream path, and **MP3 is a registered,
streaming codec on it**:
- `snd_codec.c:135-140`: registers `mp3_codec` (under `USE_CODEC_MP3`) and always `wav_codec`.
- `snd_codec_mp3.c:46-54`: `mp3_codec` provides streaming open/read/close
  (`S_MP3_CodecOpenStream` / `ReadStream` / `CloseStream`) -- it **streams**, decoding in 128 KB
  chunks (`MP3_DATA_BUFSIZ`, snd_codec_mp3.c:40), so the whole file is never loaded into memory.
- `new/snd_main_new.cpp` (compiled under NO_MODERN_DMA) bridges the MOHAA triggered-music API to
  this path: `S_TriggeredMusic_StartLoop` -> `S_StartBackgroundTrack(file,file)`
  (snd_main_new.cpp:478-486), and crucially:
  **`S_TriggeredMusic_PlayIntroMusic()` calls
  `S_StartBackgroundTrack("sound/music/mus_MainTheme.mp3", "")`** (snd_main_new.cpp:503-505).
- The main menu intro music is triggered by the engine on returning to the menu:
  `cl_main.cpp:1281` and `cl_main.cpp:2698` both call `S_TriggeredMusic_PlayIntroMusic()` when the
  client disconnects / the menu comes up.
- `S_StartBackgroundTrack` -> `S_OpenBackgroundStream` -> `S_CodecOpenStream` picks the codec by
  extension (snd_dma.c:1415-1432, snd_codec.c:37-116). The engine *prefers* 22050 Hz stereo and
  only **warns** (does not fail) otherwise: `snd_dma.c:1405-1407` "music file %s is not 22k stereo".

**Therefore MP3 is fully supported for the menu theme in this exact build, and MOHAA's own theme is
already an MP3.** The "old SDL sound = WAV only" assumption in the brief is too pessimistic for
*music*: WAV-only applies to short sampled SFX, but the background-music stream uses the codec
table, which includes the MP3 codec here.

### c.2 Exact format the USER should provide

**Provide: `mus_MainTheme.mp3` -- MP3, stereo, 44.1 kHz (22.05 kHz also fine), CBR 128-192 kbps,
MPEG-1 Layer III, full length of the Operation Market Garden track. No special trimming/looping
needed.** Notes:
- libmad here decodes Layer III (`snd_codec_mp3.c:171 MAD_LAYER_III` check). Use standard MP3
  (avoid exotic VBR headers / MP3pro). CBR is safest.
- 22.05 kHz stereo exactly matches the engine's preferred rate and silences the warning, but
  44.1 kHz plays fine (warning only). Pick 44.1 kHz for fidelity or 22.05 kHz for an exact match.
- A 2-4 minute MP3 at 128-192 kbps is ~2-6 MB -- trivial. Streaming means length is not a memory
  concern.

**Do NOT provide a PCM WAV for this.** A full-length 16-bit 44.1 kHz stereo WAV is ~10 MB/min and
the brief notes large PCM WAVs have crashed this build's load path; MP3 sidesteps that entirely by
streaming.

### c.3 Where to place it / how it gets wired (two options)

**Option 1 -- RECOMMENDED (zero engine change, zero menu change):**
Put the file at **`sound/music/mus_MainTheme.mp3`** inside the coop pak
(source: `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\sound\music\mus_MainTheme.mp3`, then rebuild
`zzzzzz_co-op_hzm_mod_mohaa.pk3`). Because that pak sorts last and wins
(see d), it overrides the stock `mus_MainTheme.mp3`, and the engine's hardcoded
`S_TriggeredMusic_PlayIntroMusic()` plays it automatically on the main menu. Nothing in any `.urc`
or `.cfg` needs to reference it. This is exactly how the community replaces MOHAA menu music
(confirmed: menu music lives in `main/sound/music` and is overwritable).
- The mod already ships `.mp3` files (e.g.
  `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\sound\coop\german\reinf_alarm1.mp3`), proving MP3 playback
  works in the deployed build.

**Option 2 -- explicit in-menu trigger (if you want the music tied to the menu, not the engine
intro hook, or want a different filename):**
Add a hidden `Label` to `ui/main.urc` with a `loopingsound`:

```
resource
Label
{
    name "coop_menuMusic"
    rect 0 0 1 1
    bgcolor 0 0 0 0
    borderstyle "NONE"
    loopingsound "sound/music/coop_market_garden.mp3"
}
```

At its first draw the Label stuffs `tmstartloop sound/music/coop_market_garden.mp3`
(`uilabel.cpp:373-374`), which loops the track via the same codec path. This lets you use a custom
filename and keep the stock `mus_MainTheme.mp3` untouched. (You may also want a matching `tmstop`
on entering a map; the mod already wraps `tmstart`/`tmstop` coop-safely in
`global/music.scr` -> `coop_mod/replace.scr`.)

**Recommendation:** use **Option 1** for the main menu theme (simplest, robust). Reserve Option 2
if you later want different music on different menu screens.

---

## (d) BREAK-THE-MOD assessment + phased plan

### d.1 Mount + load order

- Pak `zzzzzz_co-op_hzm_mod_mohaa.pk3` sorts last alphabetically and therefore **wins all file
  conflicts** -- any `ui/*.urc`, `textures/...` art, `fonts/...`, or `sound/music/...` shipped in
  it overrides the base game. So **all modernized menu assets should ship inside the coop pak.**
- fs-unify means `main\` paks reach all three games (AA/SH/BT); the running profile is Breakthrough
  (`com_target_game=2`). The coop pak is mounted in that profile, so its menu wins there.
- **Vanilla single-player menu impact:** the coop pak already overrides `ui/main.urc`, so the
  "vanilla" main menu is *already* the coop one whenever the coop pak is mounted. Reskinning it
  does not regress anything that isn't already coop-overridden. If you ever need the untouched
  stock menu, that only happens with the coop pak unmounted -- out of scope here.

### d.2 Does it keep coop + the test harness working?

**Verdict: SAFE**, provided the reskin obeys these invariants (all art/font/music changes do):
1. `coop_mod/start_server.cfg` is **not** modified (keep `g_gametype 2`, `ui_startdmmap 2`).
2. The Apply button keeps `stuffcommand "wait 250;exec coop_mod/start_server.cfg"`.
3. The map slots keep names `coop_startMap1..10` and their `set ui_dmmap <map>` stuffcommands;
   `coop_maps.inc` keeps those widget names so the per-mission `.cfg` repaints still bind.
4. The mission dropdown keeps its `addpopup ... exec ui/coop_start/<id>.cfg` entries (or an
   equivalent that still execs those cfgs).
5. `ui_dmmap` stays the map-selection cvar and remains writable by menu + by
   `maptest_start.cfg`.

Because the maptest harness talks to `ui_dmmap` + `start_server.cfg` directly and never touches
menu art, a pure reskin **cannot** disturb it. It would become **CONDITIONAL/BREAKS** only if a
"rebuild" rewrote `start_server.cfg`, renamed the slot widgets, or changed the `ui_dmmap` /
`ui_startdmmap 2` contract -- so don't.

Music via Option 1 is independent of all UI plumbing (engine-side), so it is SAFE by construction.

### d.3 Phased implementation recommendation

- **Phase 0 (now, no build):** finalize art mockups + collect the user's
  `mus_MainTheme.mp3` (format per c.2). Nothing deployed; live maptest undisturbed.
- **Phase 1 (music only, lowest risk):** add `sound/music/mus_MainTheme.mp3` to the coop pak
  (Option 1). No `.urc`/`.cfg` edits. Verify the new theme plays on the main menu. This alone
  satisfies the "theme it around Operation Market Garden" goal.
- **Phase 2 (art reskin):** override background/button/sign TGA-JPG art under the existing shader
  names (Option A in b.3.1) -- still no `.urc` logic edits, minimal risk. Smoke-test that the menu
  renders and the coop start flow still launches a map in gametype 2.
- **Phase 3 (layout/font polish):** edit `ui/main.urc` + `ui/coop_start.urc` rects/fonts/colors
  and the coop start screen, preserving all invariants in d.2. Re-run a short maptest to confirm
  the `ui_dmmap` -> `start_server.cfg` path is intact.
- **Phase 4 (optional):** new `.RitualFont` + matching loading-screen art for full visual cohesion.

Do each phase as its own pak rebuild, and only when the live maptest run is paused/finished.

---

## File:line reference index (codebase findings)

- Active image formats: `code/renderergl1/tr_image.c:2399-2469` (TGA/JPG/PCX/BMP/GST/DDS; no PNG).
  TGA constraints: `code/renderercommon/tr_image_tga.c:106-116`.
- MP3 codec registered + streaming: `code/client/snd_codec.c:135-140`,
  `code/client/snd_codec_mp3.c:40,46-54,171`.
- Build keeps MP3 + libmad under NO_MODERN_DMA: `code/client/CMakeLists.txt:24,49-59,65-80`.
- Background-track stream + 22k-stereo warning (not fatal): `code/client/snd_dma.c:1389-1432`.
- Triggered-music bridge + hardcoded `mus_MainTheme.mp3`:
  `code/client/new/snd_main_new.cpp:478-486,503-505`.
- Engine triggers menu intro music: `code/client/cl_main.cpp:1281,2698`.
- `.urc` Label looping-sound key -> `tmstartloop`: `code/uilib/uilabel.cpp:48-60,188,192,373-374`.
- `virtualres` widescreen scaling: `code/uilib/uiwidget.cpp:289,292,1048-1057`.
- Font load by name from `fonts/<name>.RitualFont`: `code/renderergl1/tr_font.cpp:300-330`;
  default `verdana-14`: `code/uilib/uifont.cpp:268`.

## File:line reference index (mod / coop flow)

- Main menu (coop-overridden): `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\main.urc` (no music line).
- Coop start screen + Apply: `ui\coop_start.urc:150-177` (dropdown), `:181-193` (ui_dmmap field),
  `:331` (include maps.inc), `:348-362` (Apply -> start_server.cfg).
- Map slots: `ui\coop_maps.inc` (coop_startMap1..10).
- Per-mission repaint example: `ui\coop_start\m1.cfg`.
- Start contract: `coop_mod\start_server.cfg:25` (g_gametype 2), `:43` (ui_startdmmap 2).
- Maptest reuse of contract: `coop_mod\cfg\maptest_start.cfg:28-29`.
- Coop music wrappers (tmstart/tmstop): pak `global/music.scr` -> `coop_mod\replace.scr`.

## Web sources

- OpenMoHAA docs/home: https://docs.openmohaa.org/ , https://www.openmohaa.org/
- Menu music lives in `main/sound/music` and is overwritable; community replaces the main-theme
  file: https://forums.nexusmods.com/topic/5933218-trying-to-replace-main-menu-music/
- MOHAA menu-music mods (confirm theme-swap convention):
  http://www.mohaaaa.co.uk/AAAAMOHAA/content/where-you-menu-music ,
  https://www.lonebullet.com/mods/download-mohaa-menu-music-medal-of-honor-allied-assault-mod-free-24575.htm
- MOHAA modding / UI community hubs:
  https://gamebanana.com/games/720 , https://www.moddb.com/games/medal-of-honor-allied-assault/mods
