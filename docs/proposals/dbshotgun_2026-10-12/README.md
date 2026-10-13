# Sawn-off double-barrel shotgun (`coop_dbshotgun`) - proposal, STAGED

**Status 2026-10-13 (third pass: the armory side).** The weapon itself (own texture, hold, aim, reloads, third person)
is as the second pass left it. New: the mod's full FINISH SET (7 finishes, sec. 13), its OWN ARMORY ENTRY with an
unlock path through the generators (id 80, sec. 8 - wiring option A is superseded), the pick and the finish proven
over a map restart and a map change. World behaviour (sec. 14) is only partly verified.
Everything is staged in this folder and on engine branch `dbshotgun-next` (worktree
`C:\mohaa-coop-dev\openmohaa-hzm-dbs`, cgame only, unchanged this pass: 96c32bd9 = harness `cgame_dbs8`). Nothing is
in the mod tree, the fixes pak, `docs/tools` or the live install.

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
| 5a | Finish set: gold, chrome, blued, bloody, woodland, winter, desert | **done** | looked at in engine: every finish at the hip, in the aim, in third person, open (runs f1-f3, a2) |
| 5b | Own armory entry + unlock path (challenge "Both Barrels", 60 shotgun kills) | **done, staged** | run a1 / a2: every step of sec. 8 looked at + log |
| 5c | The pick lost at a map change (the second pass's open defect) | **fixed** by 5b | run a1: slot + finish after a map restart AND a map change, looked at |
| 5d | World behaviour | **NOT finished** (sec. 14) | a double barrel lying on the ground: looked at; death-drop log line; touch pickup, use-to-loot, shell sharing: NOT verified |
| 6 | Engine minimal + merge note | **done** (unchanged this pass) | sec. 6 |
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
python tools/dbs_finish.py       # the 7 finishes: 4 baked sheets + bore mask, coop_dbshotgun_finish.shader, 7 tiks ; `view` = offline
python tools/dbs_clip.py         # textures/hud/clip/clip_2.tga (the armory's 2-round picture)
python wiring/stage_armory_dbs.py --sr                                  # the armory entry through the generators -> wiring/gen, armory_ov
python tools/mkov_dbs.py build/ov.pk3 [--armory] [--notps]              # test overlay; --armory = armory_ov + the test hooks
python tools/run_dbs.py  <id> --overlay <abs pk3> --cgame cgame_dbs8 --parts look,pump,action,third,misc,fin
python tools/run_arm.py  <id> --overlay <abs pk3> --cgame cgame_dbs8 --parts arm[,armq,world] --set "set coop_lockLoadout 1"
python tools/fin_sheet.py <run> <out prefix>                            # finish contact sheets
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
Rank **645** (was 640 = the pump gun's: a shared rank hides a gun on the weapon wheel; bug-3810).

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
  2026-10-13: the mod TREE's state file gained `RELOAD_SHOTGUN_BREAK_END` (a reload broken off to fire), which also plays
  `shotgun_reload_end`: the patch now puts the row in front of each (1 state in the released file, 2 in the tree);
  `--check` passes on both. The tree's new shotgun states were NOT run with this gun (the test install is the release).

## 8. Armory: own entry, own unlock path - `wiring/stage_armory_dbs.py` (details: `wiring/WIRING.md`)

Roster id **80**, tile **DOUBLE BARREL** on the HEAVY tab under the TRENCH GUN, DMG 10 / RPM 3 / ACC 6 / MOB 10, 2 rounds.
**Unlock rule: challenge "Both Barrels" - Get 60 kills with the Shotgun** (`wpn_shotgun_v`, on the pump gun's existing
kill statistic; the mod's own pattern for a gun's sibling - drum Thompson, silenced MP40, scoped StG - sits between the
base and the elite kill challenge, here 30 and 90). **Finishes** unlock as the pump gun's do (the finish by its own
account-wide challenge; the gun takes finishes once `wpn_shotgun`, 30 shotgun kills, is done) - shared with the pump
gun, no statistic of its own. **Master switch** `coop_dbShotgun` (0 = tile hidden, pick refused).
Made the mod's way: sources edited in a scratch copy of the repo, then `gen_loadout.py build`, `gen_skinbase.py`,
`armory_unlocks.py --emit`, `gen_loadout.py check` (EXACT REPRODUCTION) and, for the test install, the patched
`gen_service_record.py` - as patched COPIES; `docs/tools` and the mod tree are untouched.

Run a1 (private test install, released mod + overlay `mkov_dbs.py --armory`, `coop_lockLoadout 1`, cgame_dbs8, 0 script
errors) and a2; progress was made with the mod's own `chal_bump` (the function a kill calls), not by editing a record:

| Step | Result | Checked by |
|---|---|---|
| fresh record: tile with padlock, hover text "UNLOCK: 60 kills w/ Shotgun (Both Barrels)" | yes | looked at (`dbs_armory_unlock_path.jpg` 1) |
| click while locked | inspect page only, `coop_lo1` stays empty | looked at (2) + cvar |
| an existing record (the pump gun unlocked through ITS challenge) + 59 shotgun kills | still locked (`v=59`) | log |
| the 60th kill | `models/weapons/coop_dbshotgun.tik` added to the record; the record kept everything it had (compared before / after) | log; tile without padlock looked at (3) |
| click | PRIMARY 1 = DOUBLE BARREL, `coop_lo1` = 80, server slot = the tik | looked at (4) + log |
| respawn in the map | in the kit (4 items); in the hand after `useweaponclass heavy` - the game brought up PRIMARY 2 first | looked at (5) |
| finish WINTER (its challenge + `,f16`) | "WINTER finish applied", `coop_loS1F` = 6 | log |
| map RESTART (m3l2) | spawns with the winter double barrel in the hand, slot + finish intact | looked at (6) + log |
| map CHANGE (m3l2 -> m2l1) | the same | looked at (7) + log |
| Service Record | SUPPORT WEAPONS 12/12: "Both Barrels 60/60"; baked hover "Unlocks: Double Barrel Shotgun" | page looked at in game (8); the hover picture looked at as a file - the hover itself not exercised (no mouse in the harness) |
| `coop_dbShotgun 0` | tile gone from the heavy tab (its row stays empty); after a restart "DOUBLE BARREL is switched off on this server", slot empty, spawns without it | looked at (9, 10) + log |

NOT tested: a second client / a dedicated server; the disconnected (main menu) armory; the mod TREE's newer files
(the test install runs the released mod - `player_Torso.st` in the tree has new shotgun reload states since 08:54
today, the torso patch's check passes on it but nothing was run against it); the MP armory (not wired, on purpose).

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

* `assets/models/weapons/coop_dbshotgun.tik` + 7 finish tiks `coop_dbshotgun_{gold,chrome,blued,bloody,camo_woodland,camo_winter,camo_desert}.tik`
* `assets/models/weapons/coop_dbshotgun/` (skd + 8 gun clips)
* `assets/models/human/animation/viewmodel/coop_dbshotgun/` : 16 hand clips `dbs_*.skc`, 3 torso clips `coop_dbs_tps_*.skc`
* `assets/textures/models/weapons/coop_dbshotgun/` : `coop_dbshotgun.jpg`, `_parts.jpg`, `_bloody.jpg`, `_camo_woodland.jpg`, `_camo_winter.jpg`, `_camo_desert.jpg`, `_fmask.jpg`
* `assets/scripts/coop_dbshotgun.shader`, `assets/scripts/coop_dbshotgun_finish.shader` (uses the mod's `textures/coop_skins/env_sheen.tga`)
* `assets/textures/hud/loot/w_dbshotgun.tga`, `assets/textures/hud/clip/clip_2.tga`
* `rows/fps_rows_coop_dbshotgun.txt` -> inside `models/player/base/fps_anims_shotgun.txt` (fixes pak copy)
* `rows/tps_rows_coop_dbshotgun.txt` -> inside `models/player/base/anims_shotgun.txt`
* patches: `wiring/patch_torso_dbs.py`; `wiring/gen/armory_dbs.patch` (18 mod files) + `wiring/gen/new/` (12 cfgs) +
  `wiring/gen/generators.patch` (TSV row, `armory_unlocks.py` HZM_MOD, `gen_service_record.py` HZM_MOD + REWARD_NAMES);
  then the generators and the `ui/coop_loadout.urc` checksum (`wiring/WIRING.md` steps 6-7);
  `wiring/patch_cgame_loot_dbs.py` (already on the branch)
* engine: `dbshotgun-next` 96c32bd9; `sights_override.json` + `tools/sightrow_dbs.py`
* NOT for integration: `armory_ov/` (test install), `wiring/superseded/` (option A), `build/`

## 11. Open points (honest list)

1. World behaviour, sec. 14: touch pickup, use-to-loot, shell sharing are not verified; one unexplained log line.
2. The aimed reload plays low on the screen (chambers at about 85 % of the height). NOT raised this pass.
3. Hip reload: the loading hand is large when it crosses to the left chamber. NOT changed this pass.
4. Stage finishes (gold / chrome / blued) read flat on this dark sheet - the same look as the pump gun's (side by side:
   `build/_f2_refs.jpg`), the wood is tinted too, as on every gun. The winter "open" still has the loading hand in it.
5. With the master switch off the tile's row is an empty gap and the PRIMARY card keeps the archived name.
6. A respawn in the map brings up PRIMARY 2 first when the double barrel is PRIMARY 1 (after a map load it is in the
   hand); not looked into - may be the same for any pair of guns.
7. Third person: the hold / aim poses are the pump gun's; the raise clamps the left arm in 5 frames, the lower in 8.
8. Sounds chosen by file, never heard.
9. Recoil table: 8 rows written from the tik's own viewkick line by the staging script (the extractor named in the
   table's header was not found under docs/tools).
10. Not wired (as for the other new guns): `global/weapon.scr` AI alias, `developer.scr` / `buildmode_catalog.scr`
    lists, the MP armory, model variants (pack skins).

## 12. Handover

Knobs: `dbs_hands.py` HOLD / AIM / WORK / LOWERED / PHYS / `GP.ACTIONS` / WRIST_VIEW / BELT_VIEW / LEVER_SHIFT;
`dbs_anim.py` THETA_OPEN / THETA_CLOSE / EJECT_F / EJECT_DIR / SHUT_F; `dbs_skin.py` top block; `dbs_tps.py` JOBS;
`dbs_finish.py` FINISHES / BLOTCH_CM / BORE_MASK; `stage_armory_dbs.py` ID / BARS / CHAL / XFM (env DBS_XFM).
Traps: bug-3774 .. bug-3781 (second pass), bug-3808 .. bug-3813 (this pass).
Runs: finished ones are in `H:\hzm_archive\dbs\<run>\` (f1-f3 finishes, a1 armory, a2 armq + world v1, a3 world v2;
second pass: re2-re5, rh1-rh6, rl1, rm1-rm4). **Loss, bug-3808:** this pass's first archive move put the second pass's
28 run folders into one folder; the 15,117 `ab__<run>__` frames were sorted back, 511 files without a run id in their
names (per-run qconsole.log / notes.json / wire stills / tp, act, ms frames) collided - one copy of each survives in
`H:\hzm_archive\dbs\_merged_no_run_id\`. The media made from them is intact in `media/` and `build/`.
The harness home keeps the test player's unlock record and armory picks between runs (a2 started with 7 unlocks).
Next, in order: (a) world behaviour: kill the test AI another way (shoot it), use-to-loot prompt + picture, touch
pickup by a player who carries no shotgun, shells with readable counts, and the `cannot be picked up` line (bug-3813);
(b) raise the aimed work pose (`WORK['ads']`, six-stance box runs); (c) the hip loading hand; (d) listen to the sounds.
Someone's `zzzzzzzzzzzzzzzz_memorialtest.pk3` in `G:\mohaa-hudfeed4\home\maintt` and the old `runs` folders there were left alone.

## 13. The finish set - `tools/dbs_finish.py`

The seven the pump gun has, by the mod's recipe (`gen_skins.py` / `bake_skins.py` / `gen_weapon_skins.py`, read, not
run): gold / chrome / blued = shader stages over OUR sheet with the mod's tint and sheen numbers; bloody / woodland /
winter / desert = sheets baked from OUR sheet with the mod's colour maths and palettes. Different from the mod, on
purpose: the pattern is laid out in gun space (this atlas has many islands - a UV-space pattern breaks at every seam);
the bores, breech faces, standing breech and muzzle faces keep the base sheet on the baked finishes, and a mask stage
keeps the bores dark under the stage finishes; the bead and the shells are the untouched second surface.
**All eight tiks carry the name "Shotgun (Double Barrel)"** - a second " (Finish)" suffix would resolve to the pump
gun's hands, torso rows and sight row (bug-3809); the armory tells them apart by tik path. Ranks 3000-3006.
`gen_skins.py` skips this gun by itself (a name with " (" is "already a variant"), so it will not overwrite them.

## 14. World behaviour (NOT finished) - runs a2, a3

| Item | State |
|---|---|
| death drop | log `DEATHDROP e0 models/weapons/coop_dbshotgun.tik` at every death with it; a double barrel lying on the ground looked at (`dbs_world_unfinished.jpg`, right) |
| touch pickup of a player's drop | NOT verified: the test player's kit already held the gun (the armory pick persists in the harness home), so "in the hand afterwards" proves nothing |
| `cannot be picked up` | 3 x in run a3: `(itemhandler.scr::handleWeaponPickup) *ERROR*: Weapon with model models/weapons/coop_dbshotgun.tik cannot be picked up by <player>`, each right after a respawn at the place of the own death drop. Cause not established (bug-3813) |
| AI with the gun | armed through `aihandler.scr::coop_actorArm` (log `DBSAI armed`; the AI stands with a long gun at its side, looked at, not close enough to name it) |
| use-to-loot prompt + picture | NOT verified: the script-spawned AI could not be killed by script (`damage 5000`, then `takedamage` + `kill`: it stayed up), so there was no AI drop |
| shells shared with the pump gun | NOT verified by a run. By the tiks: both declare `ammotype "shotgun"` (one pool in the engine); `itemhandler.scr::getAmmoType` answers "shotgun" for the tik (staged) |
