# Menu load: in game -> Main Menu, and room pop-in (2026-11-10)

User (v1.10.72): going to the Main Menu from a live game takes a very long time, frozen frame. Coordinator add-on:
moving between menu rooms, characters and props pop in after the camera arrives.

## Measured (private client G:\mohaa-menuload, the user's own settings, gl2, 1920x1080 test window)

| path | before (v1.10.72/73) | after (engine `menuload-eng`) |
|---|---|---|
| in game -> Main Menu (dm_main's button = `pushmenu main`) | **10.8 s, one frozen frame** | **1.0-1.4 s** behind the veil + progress bar (the screen stays live) |
| disconnect -> menu | **17.3 s** (R_Init 2.1 s + 14.2 s in one frozen frame) | **~2 s**: 0.9-1.1 s re-registration (frozen) + 0.8-0.9 s behind the veil |
| m4l0 load with the player's real preload list | preload 11.0 / 13.4 s (CL_EndRegistration 11.2 / 13.5 s) | preload 1.0-1.4 s (CL_EndRegistration 1.3-2.5 s); 219 menu shaders dropped from the list |
| cold start -> menu | attic only 19-27 s (first ever boot incl. 7 s driver shader compile), 9 s frozen frame; other rooms loaded on first entry | 20-34 s for ALL 32 rooms (1933 model registrations) behind the veil + bar; no load on any room entry |
| kept menu textures | - | **183-184 MB VRAM** (kept only with >= 4 GB detected VRAM) |

Logs: `H:\hzm_work\menuload\runs\` (base / base173 = before; new173c = after; rooms_cold3 / rooms_game = transitions).

## Causes

1. **gl2 re-runs R_Init on every map load and every disconnect** (RE_BeginRegistration): every texture deleted.
   The 3D menu's ~250 Mpix of art (eight 4096^2) then reloaded: ~6 s driver DXT/RGTC compression
   (`r_ext_compressed_textures 1`), ~2 s generated normal maps, the rest decode/upload.
2. **Every Scene3D registered its models in its own first Draw**: whole attic in one frame; actors 45 frames later
   ("load lazily"); stage props on first use; other rooms only when entered -> the pop-in.
3. **The shader-preload learner (`r_hzmPreload`, bug-3493) recorded the menu's shaders as the MAP's**: every map the
   player ever opened the Main Menu on preloaded the attic in its loading screen (+10-12 s per load). Every player.

## Fix (engine branch `menuload-eng`, off rel-1.10.38-engine)

- renderer: menu textures (`r_hzmKeepImagePrefixes` = textures/menu/ textures/mohmenu/) survive the re-registration
  (`r_hzmKeepMenuImages`, only with >= 4 GB `r_gpuVramMB`); KEEPIMG line with real VRAM.
- renderer: menu shaders (menu paths, the menus pak's shader-name prefixes, or a script body naming a menu path) are
  never learned and are dropped (file rewritten) the first time a polluted list is read.
- exe: a room with anything unregistered draws the loading veil + progress bar and registers ~50 ms a frame;
  boot loads all 32 rooms behind the first veil; after a game the visible room gates its reveal and the other rooms
  load in the background (~4 ms a frame, done in ~0.2 s). Actors no longer load late. `r_hzmPreload` paused while
  menu models register. `^~^~^ MENULOAD ready|disconnect|background done|late` lines.
- exe: the weapon bench registers the six guns one step away in the background.

**REVERTED, do not retry blindly:** keeping the renderer registration on disconnect (ioq3 style, the old map left
loaded). On gl2 the 3D menu then drew nothing after a game - a flat dark fill under the 2D widgets (runs/new173b,
mean diff 54/45/41 vs the cold menu) - while the in-game Main Menu (cgame alive) was fine. Cause not found.

## Verification

- `ml_run.py`: timings above. `ml_rooms.py`: 18 legs at 20 fps, cold start (rooms_cold3) and from the in-game Main
  Menu (rooms_game), sheets by `ml_sheet.py`. **0 `MENULOAD late` lines** in every run; no room load on entry after boot.
- Cold vs post-game menu stills: mean diff 1.2 (after disconnect) / 2.8 (in game) - the same as the unmodified build
  (1.2 / 2.9); the residue is the animated cast, clock and weather.
- `check_mp_isolation --mod <menuload-mod> --engine <menuload-eng>`: 22 passed, 0 failed.

## Harness traps (learned here)

- A cfg cannot drive the 3D menu: hotspot commands use `uiafter`/Cbuf_AddText, which run after the WHOLE cfg.
  Chain one cfg per step with `uiafter <s> exec next.cfg` (ml_rooms.py).
- `ui_startdmmap` appends its `map` at the END of the buffer (after your cfg's quit): issue its set-line + `map` yourself.
- `popmenu` needs its argument (`popmenu 0|1`); use the menu's own `escapecommand`.
- A latched `+set` (r_ext_compressed_textures) is archived by the run: restore the config before every launch.
