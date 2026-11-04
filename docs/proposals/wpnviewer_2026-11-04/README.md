# Attic weapon viewer on the rifle rack (v1.10.63, built 2026-11-04)

User: *"For the rifle rack make it a weapon viewer the camera goes to when clicked on ... fully rotatable with mouse ... weapon
name, brief history, credit if it's a skin someone made and how to unlock it ... evaluate all of our weapon models and variants".*

| piece | where |
|---|---|
| engine | branch `wpnviewer-eng` (worktree `H:\hzm_work\wpnviewer-eng`, off `rel-1.10.38-engine`): 62a4611b orbit viewer, a8aca56e drop the light rig. openmohaa.exe only |
| mod | branch `wpnviewer` (worktree `H:\hzm_work\wpnviewer-mod`, off `hotfix-1.10.53`): 03e6f7bd |
| generator | `docs/tools/gen_weapon_viewer.py build|check|list` (`HZM_MOD=<mod tree>`), authored prose in `docs/tools/weapon_history.tsv` |
| harness | `tools/wpnview_run.py setup|sheet|views|shots|ingame` on `G:\mohaa-wpnview` (DISPLAY2), `tools/contact.py` |
| menus3d pak | unchanged - the viewer needs no new 3D assets (urc + cfgs ship in the code pak) |

## What it does
* Rack hotspot (`scenehot "rack"`, index 17, caption WEAPONS RACK): `sceneleave 1`, camera flies 0.6 s to the rack, `pushmenu hzm_wpnview`.
  The viewer menu holds the attic at that same camera (its own Scene3D `wvscene`), so there is no cut; ESC / B / BACK pops it and the
  attic flies home. Works from the in-game ESC -> Main Menu too (`media/viewer_ingame_720.jpg`, the cgame refdef branch).
* Paper-kit sheet (the mpui palette): tabs RIFLES / SNIPERS / SMGS / HEAVY / PISTOLS / GRENADES (named `tab<k>`: LB / RB step them),
  the gun list of the tab, `< variant n/N >`, PREV GUN / NEXT GUN / ZOOM (1x, 1.5x, 2.2x) / RESET VIEW, MADE BY, HOW TO UNLOCK,
  YOUR STATUS, FIELD NOTES (history).
* 452 entries = 77 roster guns + 294 finishes + 81 model variants. Every fact is read from the code (see the generator docstring).
* Status reads the profile the client already archives: `coop_loLkA<id>` (the Armory padlock), `coop_uiD<i>` / `coop_uiN<i>`
  (challenge done / progress, Service Record index). Finish progress is not archived client-side, so finishes say where it shows.
* Engine (`cl_uistd.cpp` UIFakkLabel): `modelorbit 1` turns the model about its bounds centre and frames its bounding SPHERE to the
  narrower field of view - no rotation can push it out of the box at any screen shape; `modeltiltcvar` (vertical drag),
  `modelzoomcvar` (wheel over the widget, 0.6-3.5; `WantsHoverWheel` so no click is needed), the menu right stick turns it
  (`CL_UIOrbitStick`, sdl_input hands the stick over instead of wheel ticks while a viewer is on screen).
  **Older exe:** the three commands are unknown and silently ignored; the widget is the Armory hero preview with yaw drag
  (`media/viewer_oldexe_720.jpg`, no log errors).

## Merge with the attic session's rack
The attic session (`attic_polish_2026-11-02/tools/make_attic_polish.py`, branch attic-63) builds the rack and already appends
`scenehot "rack"` LAST with `RACK_C_BU (2.90, 2.55, 1.56)` / `RACK_POSE` and a placeholder fly-there-and-back command, plus its
`hot_rack` proxy and `atticsign_rack` caption. `gen_weapon_viewer.py` uses the same constants and is idempotent:
* run it **after** `make_attic_polish.py` (last step of the main.urc rebuild order): when the rack hotspot exists it only rewrites
  the `scenehot "rack"` command and the `hot_rack` stuffcommand (`rewired`); on a tree without it (this branch's base) it adds
  hotspot + box + caption + proxy itself (`added`), marked `// ---- [wpnviewer]`.
* when merging the branches, take attic-63's `main.urc` and re-run `HZM_MOD=<tree> python docs/tools/gen_weapon_viewer.py build`;
  `check` must then report 0 stale files. If the rack moves, change `RACK_C_BU` / `RACK_DIST` in both scripts.
* The viewer's backdrop copies every non-actor `scenemodel` / `scenelight` of `atticscene`, so after the rebuild it shows their rack.
* Open (attic side): the rack is on the x 3.00 wall, outside the 16:9 and 4:3 home frame - only 21:9 can click it; the hot_rack
  proxy gives pad / keyboard access. A 4:3 / 16:9 way in (a twin plate like WHAT'S NEW 4:3) is the attic session's call.

## QA (720 / 4:3 1440x1080 / 21:9 1920x804, GL2, private client)
`media/contact_720_01..08.jpg` (every entry), `viewer_{720,43,219}[_tilt].jpg`, `attic_rack_hover_720.jpg`, run folders under
`H:\hzm_work\wpnviewer\runs\`. Mouse drag (spin 108 / tilt 48 after a 180x80 px drag) and the right stick both measured via cvars.
Defects found: bug-10526 (two invisible WW1 variants, fixed), 10527 (generator), 10528 (light rig, dropped), 10529 (East's
lightingSpherical imports render dark in any world-less preview, OPEN), 10530 (TT-33 SILENCED finishes tint only the suppressor,
OPEN). Mills bomb: black 3D model, shown as the Armory's 2D icon (gen_loadout.ICON2D).
Not in the viewer: items with finishes that are not Armory guns (mine detectors, binoculars, the DBNO pistol, the `_lite` AI
copies, the Kar98 rifle grenade).
