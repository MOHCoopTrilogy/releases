# Sawn-off double-barrel shotgun (`coop_dbshotgun`) - proposal, STAGED

**Status 2026-10-13 (second pass).** Own texture, own first-person hold and aim, a rebuilt reload (hip and aimed,
measured in six stances), third-person clips without the pump stroke, wiring option A as patches run in an overlay.
Everything is staged in this folder and on engine branch `dbshotgun-next` (worktree
`C:\mohaa-coop-dev\openmohaa-hzm-dbs`, cgame only). Nothing is in the mod tree, the fixes pak or the live install.

## 1. State per item

| # | Item | State | How checked |
|---|---|---|---|
| 1 | Own texture (nothing of the author's sheets) | **done** | looked at in engine: hip, ground, third person, next to the pump gun |
| 2 | Own hold (hip) and own aim | **done** | looked at (1080p stills); bead 16 px across at 1080p, its top on the screen centre |
| 3a | Reload, hip: lever by the thumb, barrels drop, selective ejectors, shell pinched and thumbed home per chamber, shut with a jolt | **done, first polish** | looked at (GIFs + sheets), both cases |
| 3b | Reload, aimed, one shell left - six stances | **done** | measured (0.01-0.59 %) AND looked at (stance sheet) |
| 3c | Reload, aimed, emptied - six stances | **done** | measured from the reload's start (0.07-1.55 %) AND looked at (stance sheet) |
| 3d | Weight (`gunphys`) | **done** | in every clip; looked at in the GIFs |
| 3e | Raise, lower, sprint, second barrel right after the first | **done** | looked at (GIFs / sheet); aimed second shot needed a statemap row (sec. 7) |
| 4 | Third person without the pump stroke | **done** (fire stand / crouch, reload end) | looked at (sheet + GIF); needs the two staged patches |
| 5 | Wiring option A + world behaviour | **patches staged and run; NOT finished**: the pick is lost at a map change (sec. 8) | select / spawn with it / switch off / death-drop log line: run and looked at; pick across a map restart: FAILS; use-to-loot: not verified |
| 6 | Engine minimal + merge note | **done** | sec. 6 |
| 7 | Sounds | aliases resolve (no alias error in `developer 1` logs), **not heard** | sec. 9 |

## 2. Source and licence

"Double Barrel Shotgun" by Jean PFP, **CC0** - `source/SOURCE.md`. Only his MESH is in the game files. The 2048 sheet
is painted by `tools/dbs_skin.py` from the mesh (position / normal / curvature per texel, the material-slot flag "this
face is wood"), ambient occlusion we bake, the RETAIL Kar98 butt wood (`main/Pak2.pk3`) and procedural steel. No pixel
of his baked sheets, nothing from the images packed in his .blend files. `bl_build.py --own` opens neither.

## 3. Pipeline (run from this folder)

```
BL="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
"%BL%" --background --factory-startup --disable-autoexec --python tools/bl_build.py -- source/Shotgun build/own --own
python tools/srclist.py --save textures/models/weapons/kar98/kar98      # build/src/kar98_retail.png (retail pak only)
python tools/dbs_skin.py bake ; python tools/dbs_skin.py paint          # build/skin_bake.npz, the 2048 sheet (seeded)
python tools/dbs_skin.py view                                           # offline look: both sides, top, bottom
python tools/dbs_build.py        # skd, parts sheet, shader, build/model.json   (mesh unchanged since the first pass)
set IRONSIGHT_EXTRA_PAKS=<abs>\build\ov.pk3
python tools/dbs_hands.py bake   # 16 first-person hand clips + build/hand_paths.json ; `report` = numbers only
python tools/dbs_hands.py sheet <clip> f,f,f out.jpg [eye|close|side|right|top]     # offline look, centre box drawn
python tools/dbs_anim.py         # the gun's own clips (uses hand_paths.json)
python tools/dbs_tik.py          # the weapon tik
python tools/dbs_tps.py          # 3 third-person torso clips (pump stroke taken out)
python tools/dbs_icon.py         # use-to-loot picture w_dbshotgun.tga
python tools/sightrow_dbs.py C:\mohaa-coop-dev\openmohaa-hzm-dbs\code\cgame\cg_adssights.h
cmake --build .cmake --config Release --target cgame -- -m:4 -v:m       (in the worktree)
python tools/mkov_dbs.py build/ov.pk3 [--wire] [--notps]                # test overlay; --wire = the armory patch
python tools/run_dbs.py  <id> --overlay <abs pk3> --cgame cgame_dbs8 --parts look,pump,action,third,misc,wire,loot,menu
python tools/run_dbsh.py <id> --overlay <abs pk3> --cgame cgame_dbs8 --guns dbs --parts yaw --stdemo stand,crouch,prone,standL,standR,braced --tail 360:4 --shots 1 --demoreload 175 --demoyaw 165
        emptied gun: --shots 2 --demoempty --demoreload 290        hip: add --sthip (one stance)
python tools/box_dbs.py <id> dbs --sway [--empty]      (emptied: set BOXENG_AFTER=66 = from the reload's start)
python tools/animruns.py <id>    # how long each row really played ; tools/strips.py, sheet.py, pair.py, mkgif.py, gifqa.py
```

Harness: private copy `G:\mohaa-hudfeed4`, owner `hudfeed4`, port 12761, `openmohaa_integ.exe` + `games/game_integ.dll`
+ `renderers/gl2_integ.dll` + `cgames/cgame_dbs8.dll` (= the branch head). `run_dbsh.py` / `box_dbs.py` are the heavy
lane's `run_h.py` / `boxeng.py` used as libraries, repointed. **Run frames are kept under `dbslib.RUNS`** (this
session: `...\scratchpad\dbs\runs\`, 8.9 GB) - G: filled up on 2026-10-13 (bug-3777); nothing was deleted.

## 4. Numbers of the weapon (unchanged from the first pass) - `tools/dbs_tik.py`

2 shells; one barrel per pull, 0.30 s between; 26 x 14 = 364 per barrel (pump: 20 x 14); spread 115 115 135 135; pellet
range 650; move speed 1.00; view kick -23 -26 / +-2 / recentre 12; start ammo 40. Name `"Shotgun (Double Barrel)"`.

## 5. First person - `tools/dbs_hands.py` (numbers at its top)

* **HOLD**: breech top at view (13.8 fwd, 6.0 right, 3.2 down), barrels 5 deg in, 2.5 deg up, 8 deg cant; forend hand
  on the rear half of the forend (wrist at 9.1 u; the forend runs 10.4-21.9 u).
* **AIM** (`charge` row + sight row): eye 11 u behind and 2.2 u above the breech top, F = the bead's TOP, delta 131 mrad.
* **WORK pose** (where the open gun is loaded): hip - chambers at view (10.8, 2.6 right, 1.1 down); aimed - chambers at
  (9.6, 0.2 right, 3.0 down), pitched 18 deg so the dropped barrels point down: all of it under the centre box.
* The reload (rows play 0.75 s / 0.66 s per shell / 1.17 s in the engine - `animruns.py`): thumb onto the lever
  (frames 2-5, the grip hand slides 2.5 u up the grip to reach it), barrels drop 5-11 with the gun turning muzzle-up
  only as far as they have dropped, fired cases out at frame 10 (back / right / up, never through the middle), left
  hand to the belt; per shell: up from below-left, shell in a ring pinch (thumb against the first two fingers), laid
  into ITS chamber (`reload_single` = right, `reload_single_l` = left; the engine picks `_l` on an empty clip), fingers
  stop at the breech face, the thumb goes behind the head and pushes it home; then the left hand takes the forend, the
  grip comes up to the barrels (latched at frame 12, lever back), the gun returns to the hold / the exact aim.
* **Weight**: `gunphys.simulate`, class PHYS (2.3 kg, 3.4 / 2.4 Hz, damping 0.62), impulses `dbs_lever / dbs_eject /
  dbs_open / dbs_shell / dbs_shut / dbs_fire`; peaks: open 3.5 deg, shell 1.3 deg, shut 3.1 deg (nods DOWN: never over
  the sight line), shot 7.1 deg and 1.3 u back.
* Raise / lower: own motions about the grip (15 u down, 38 deg muzzle down), retail frame counts 35 / 17.

### Box figures, AS PLAYED (aim sway + breath on; `boxeng.py --sway`: share of the centre box the reload covers beyond the settled aim's sway envelope; bar: under 2 % in every frame)

| | stand | crouch | prone | lean L | lean R | braced | frames over 2 % | sight line |
|---|---|---|---|---|---|---|---|---|
| one shell left (run rm1) | 0.01 | 0.02 | 0.02 | 0.59 | 0.37 | 0.12 | 0 | back to 0.00 deg |
| one shell left, final ejection (run re2) | 0.02 | 0.01 | - | 0.64 | 0.44 | 0.04 | 0 | 0.00 |
| emptied, from the reload's start (run re5, `BOXENG_AFTER=66`) | 0.58 | 0.45 | 0.22 | 0.69 | 1.55 | 0.07 | 0 | 0.00 |
| emptied, from 27-40 frames after the LAST SHOT (tool default) | 0.79 | 2.00 | 12.18 | 1.90 | 1.83 | 5.42 | prone 9, braced 6 | - |

The last row is the shot, not the reload: the tool's default window starts while the last shot's smoke is still in
the box (looked at, `build/_re5p.jpg`: prone and braced hold the smoke longest; in prone the reload starts at the shot).
The settled aim itself covers 11-17 % of the box (prone 12-14 %, braced 5-6 %).

## 6. Engine - branch `dbshotgun-next` (cgame only; no fgame, no protocol change)

1. `cg_viewmodelanim.c`: (a) per-weapon first-person rows `coopr_<weapon>_<row>` for EVERY row (first pass); (b) NEW:
   a per-weapon `reload_single` row that starts on an EMPTY clip plays `<row>_l` when the hands tiki has it. Only
   `coopr_` rows are looked at; no other gun has an `_l` row. (`_l`, not `_first`: a tiki alias holds 47 characters
   and `..._reload_single_first_ads` was 51 - never found, the hip clip played inside the aim; bug-3776.)
2. `cg_modelanim.c` (first pass): the local player's held gun plays `reload_empty` / `reload_single_first` in place
   of `reload` / `reload_single` when the row starts on an empty clip and the tik has that row.
3. `cg_adssights.h`: one row (from `sights_override.json`).
4. `cg_coopfeed.c` + `cg_coopfeed_loot.h` (`wiring/patch_cgame_loot_dbs.py`): the loot picture is looked up by the
   FULL weapon name first, then by the name cut at " (" as before; one row `"Shotgun (Double Barrel)" -> w_dbshotgun`.

**MERGE NOTE (item 2 against the SMG lane's `ads-smg-next`).** Both branches add a block to `CG_ModelAnim` right after
`CG_InterpolateAnimParms(s1, sNext, &model);` that replaces the held gun's `reload` frame infos by `reload_empty`.
Ours is table-driven: `s_dbsRows[2][2] = {{"reload","reload_empty"},{"reload_single","reload_single_first"}}`, for the
LOCAL player's weapon entity only (`s1->parent == cg.snap->ps.clientNum`, `STAT_MAXCLIPAMMO > 0`), decided once per
play of the row (`s_dbsChoice[r]` is taken when the row appears, restarts (`time < 0.05`) or was not seen for 250 ms)
from `STAT_CLIPAMMO == 0`, and only when the tik HAS the alternative row. Merge to ONE block: keep this table and
loop, delete the SMG block, and check the one thing the SMG block may do differently - WHEN it reads the clip (if it
latches the empty state at the last shot rather than at the row's start, keep its latch for row 0 and feed it into
`s_dbsChoice[0]`; row 1 must stay "clip empty when the row starts", because the first shell raises the clip to 1 and
the second shell must then play the plain row). Do not keep two blocks: each would swap the other's result back.

## 7. Third person and the shared state file (STAGED patches, not applied to the mod)

* `tools/dbs_tps.py` -> `coop_dbs_tps_fire.skc`, `_fire_crouch.skc`, `_reload_end.skc`: the pump gun's torso clips
  frame for frame (same lengths: the server's timing does not change) with the left arm re-solved to stay on the
  forend. Aliases: `rows/tps_rows_coop_dbshotgun.txt` (append inside `models/player/base/anims_shotgun.txt`).
* `wiring/patch_torso_dbs.py` (for `coop_mod/player_Torso.st`; `--check` passes on the mod tree and on the installed
  file): 5 torso rows for the exact name "Shotgun (Double Barrel)" in `ATTACK_SHOTGUN_PRIMARY`, `_AIM`,
  `RELOAD_SHOTGUN_END`; plus one exit row + routing state `COOP_DBS_REFIRE_AIM`: **the second barrel while aiming**
  was blocked for 1.2 s (the aimed fire state leaves only when the pump clip is done; bug-3775) - now at 0.30 s.
  Reload start / per-shell rows are kept (the gun's own model shows the barrels dropped for everyone).

## 8. Wiring option A - `wiring/patch_wiring_dbs.py` (exact list in its header; `--check <mod root>` passes: 85 files)

Switch on the trench gun's armory page ("DOUBLE BARREL: OFF / ON"), per player, carried by the armory's name bus
(token ` ,db1` / ` ,db0`, command 53), read at one place (`loadout_finResolve`), server gate `coop_dbShotgun` (seta 1).
Files: `variables.scr`, `player.scr`, `loadoutpick.scr` (3 places), `itemhandler.scr` (2 lists), `coop_defaults.cfg`,
`ui/coop_loadout.urc` (2 buttons; this file has NO generator and is checksum-locked in
`docs/tools/check_mp_isolation.py` - update the checksum), `ui/loadout/init.cfg`, all 74 `ui/loadout/pNN.cfg` (the
lines `docs/tools/gen_loadout.py` emits once `patch_gen_loadout()` is applied to it), 4 new cfgs under
`assets/ui/loadout/`. `coop_mod/recoil_table.txt` is generated: re-run its extractor.

Run in the overlay (`mkov_dbs.py --wire`, installed mod files patched; test profile with `coop_lockLoadout 0` - its
trench gun is locked behind the "Shadow Hunter" challenge):

| Step | Result |
|---|---|
| page shows the switch on the trench gun's page only, toggles | looked at (`dbs_loadout_switch.jpg`) |
| switch ON -> `DBSPICK 0 1`, respawn -> `cache models/weapons/coop_dbshotgun.tik`, the gun in hand | run w3 / w4, looked at |
| die with it -> `DEATHDROP e0 models/weapons/coop_dbshotgun.tik` | log line (run w3 / w4); the item on the ground not looked at |
| switch OFF, respawn -> the trench gun | looked at |
| pick kept across a map restart (`ui_startdmmap 2`) | **NOT WORKING YET.** The client keeps the pick (`coop_loDbsA` = `append name ,db1`, read back after the restart) and the same replay sent by hand AFTER the spawn lands (`DBSPICK 0 1`, runs w4 / w6 / w7). The automatic replay in `loadout_resend` is lost every time: one send (w3 / w4), four sends 4 s apart (w6), four sends behind an `isAlive` / not-spectator wait (w7 - that wait passes before the player's first spawn, so it gates nothing). After a restart the player spawns with the TRENCH GUN until he toggles the switch again (looked at). Next step: send the replay from where the spawn kit is issued (the `KITGIVE` site), not from the join thread. |
| picked up with Use | **NOT verified, and by design not for this case**: use-to-loot is for guns an AI dropped (`weapon.cpp` `m_bCoopUseLoot`), a player's drop keeps touch pickup; no AI carries this gun, so the prompt and the new picture were not seen. A script-spawned copy on the ground shows no prompt (looked at). |

## 9. Sounds (not heard - the harness is muted). No alias error line in the `developer 1` logs of runs w3-w5.

| Alias | File | Where |
|---|---|---|
| `coop_dbs_snd_fire` | `sound/weapons/fire/ShotgunFire1.wav` at pitch 0.70, volume 2.2 | each barrel |
| `coop_dbs_snd_open` | `sound/weapons/foley/wpn_Webley_reloadstart.wav` | lever / break open |
| `coop_dbs_snd_shell` | `sound/weapons/foley/ShotgunFill1.wav` | frame 12 of each shell |
| `coop_dbs_snd_close` | `sound/weapons/foley/coop_wpn_action_heavy.wav` | frame 12 of the close |
| `snd_shotgun_putaway` (shared) | `sound/characters/body_mvmt_04.wav`, `body_mvmtgear_04.wav` | raise AND lower (the shared raise alias `snd_shotgun_pullout` is the pump run forward) |
| `snd_shotgun_shell` (shared) | `sound/weapons/foley/ShotgunShellHard1.wav` | an ejected case landing |
| `shotgun_snd_pickup`, `_pickup_ammo`, `shotgun_snd_noammo` (shared) | `Pickup_01.wav`, `DryFireRifle1.wav` | pickup, dry fire |

## 10. Files for integration

* `assets/models/weapons/coop_dbshotgun.tik`, `assets/models/weapons/coop_dbshotgun/` (skd + 8 gun clips)
* `assets/models/human/animation/viewmodel/coop_dbshotgun/` : 16 hand clips `dbs_*.skc`, 3 torso clips `coop_dbs_tps_*.skc`
* `assets/textures/models/weapons/coop_dbshotgun/*.jpg`, `assets/scripts/coop_dbshotgun.shader`
* `assets/textures/hud/loot/w_dbshotgun.tga`, `assets/ui/loadout/dbs_*.cfg` (4)
* `rows/fps_rows_coop_dbshotgun.txt` -> inside `models/player/base/fps_anims_shotgun.txt` (fixes pak copy)
* `rows/tps_rows_coop_dbshotgun.txt` -> inside `models/player/base/anims_shotgun.txt`
* patches: `wiring/patch_torso_dbs.py`, `wiring/patch_wiring_dbs.py` (+ `patch_gen_loadout`), `wiring/patch_cgame_loot_dbs.py` (already on the branch)
* engine: `dbshotgun-next`; `sights_override.json` + `tools/sightrow_dbs.py`

## 11. Open points (honest list)

0. **The armory pick does not come back after a map change** (sec. 8) - the one known defect of the wiring.
1. The aimed reload plays low on the screen (chambers at about 85 % of the height): the price of staying under the
   centre box with the hand above the shell. It is readable; it is not a showcase.
2. Hip reload: the loading hand is large when it crosses to the left chamber.
3. Use-to-loot of an AI-dropped copy, touch pickup of a player's drop, the item lying after a death: not looked at.
4. The armory button sits at the bottom right corner next to the footer line; `ui/coop_loadout.urc` has no generator.
5. Third person: the hold / aim poses are the pump gun's (left hand at 16 u = the front half of this gun's forend).
6. The raise clamps the left arm in 5 frames, the lower in 8 - all below the view.
7. Sounds chosen by file, never heard. The recoil table row comes from re-running the extractor.
8. Aimed fire keeps the `charge` hands (as every gun); the kick there is the view kick only.

## 12. Handover

Knobs: `dbs_hands.py` HOLD / AIM / WORK / LOWERED / PHYS / `GP.ACTIONS` / WRIST_VIEW / BELT_VIEW / LEVER_SHIFT;
`dbs_anim.py` THETA_OPEN / THETA_CLOSE / EJECT_F / EJECT_DIR / SHUT_F; `dbs_skin.py` top block; `dbs_tps.py` JOBS.
Traps met this pass: bug-3774 .. bug-3781. Runs (in `dbslib.RUNS`): skin1, hold1-3, rl1, rm1 (one left, six stances),
re2, re3, re5 (emptied, six stances), rh5 / rh6 (hip), tp2 (third person, misc), w3-w7 (wiring; w5 also loot + menu).
Next, in order: (a) the join replay from the spawn-kit site (sec. 8), then re-run `--parts wire`; (b) an AI-dropped
copy for the use-to-loot prompt and picture; (c) listen to the sounds; (d) raise the aimed work pose if the user
prefers seeing more of the reload over the 2 % box rule. Someone's
`zzzzzzzzzzzzzzzz_memorialtest.pk3` in `G:\mohaa-hudfeed4\home\maintt` was left alone.
