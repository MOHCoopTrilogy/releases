# First-person gun-clipping audit - plan (prep, 2026-11-09)

Status: **offline prep only** - no code changed, no client runs. Starts after v1.10.66 ships.
Engine source read: `H:\hzm_work\wpnfix-eng` (branch `fg42hd-eng`, off rel-1.10.38-engine); paths below are `code/...` in it.

## What "clipping" can mean here (three different defects, three different fixes)

| class | looks like | owner |
|---|---|---|
| **A. near-plane slice** | the rear of the gun / hands / a scope's eyecup cut off in a hard straight line close to the eye | renderer projection (`r_znear`, `r_weaponznear`, the weapon projection) |
| **B. gun through the world** | the barrel goes into a wall or prop, or the world draws over the gun | depth hack + `coop_weaponCollision*` pull-back |
| **C. gun vs body** | hands/sleeves through the stock, a magazine through the forearm, the gun through the player's own chest at extremes | animation / rig poses, per gun (the ADS rig solve, the sprint / lean / prone poses) |

Each finding in the matrix gets tagged A, B or C first; the fix is completely different per class.

## Likely global causes (read from the code)

1. **The weapon projection exists only while it differs from the world's (class A, all guns, hip).**
   `renderergl2/tr_main.c` (~2105-2140) builds `weaponProjectionMatrix` - with the closer near plane `r_weaponznear` (default 1,
   `autoexec.cfg` seta 1) - only when `|r_weaponfovx - fovX| > 0.05` or the frame is the scope's viewmodel-only pass (`onlyVm`).
   At the hip `cg_view.c` (~9070) sets `r_weaponfovx` = the world fov, so `weaponFovActive` is false and the gun is drawn with the
   **world** near plane `r_znear` 4 (cheat-protected). Anything of the gun closer than 4 units to the eye is sliced at the hip but
   not in ADS. Candidates: scope eyecups (Kar98k, Springfield, FG 42), long receivers held close in sprint / lean, pistols in the
   aimed-pistol pose, the bolt hand on a rechamber. **Suspect #1** - check by forcing the weapon projection always on (one-line test).
2. **Hor+ FOV at ultrawide (class A + C).** `cg_view.c` ~8941-8949 widens `fov_x` with the aspect (`atan(tan(fov/2)*ratio)`), and
   the weapon fov follows it. At 3440x1440 the horizontal fov is ~106 deg (at cg_fov 80): the viewmodel's left/right extremes (the
   support hand, a side magazine (FG 42, Sten, Lanchester), the bipod) come into view, where they were off screen at 4:3 / 16:9.
   Those parts were never authored to be seen; arm meshes end, sleeves open, hands intersect. Expect findings at uw only.
3. **The depth hack range (class B).** View weapons draw with `qglDepthRange(0, 0.3)` (`tr_backend.c` ~1100), so the world can
   never draw over them - but that also means a gun pushed into a wall shows "through" it. `coop_weaponCollision` (Reach 30,
   Back 9, Dip 4; `cg_view.c` ~6478) pulls the gun back / down from walls: check its trace length against long guns (Lewis, MG42,
   PIAT, bazooka are longer than 30) and that it runs in ADS, lean and prone too.
4. **Motion layers stacking (class A + C).** `CG_OffsetFirstPersonView` (`cg_view.c` 3913-7213) adds, per frame: weapon lag
   (`cg_weaponLag*`, `coop_weaponMass*`, `coop_weaponLagMove`), bob (`coop_bobLock`, `cg_weaponFootfall`), breath / sway
   (`cg_weaponBreath`, `cg_scopeSway`), sprint lower (`cg_sprintLower*`), recoil (`coop_kickHeft`, `coop_fovPunch`, brace kick),
   landing (`CG_GetLandingSeverity`), injury shake, limp, hit flinch, the crouch weight. Each is tuned alone; their **sum** at an
   extreme (sprint + land + lean, or full-auto + crouch + turn) can carry the gun's rear past the near plane (A) or the hands into
   the stock (C). Look for clamps on the summed offset - there may be none.
5. **Lean / prone eye offsets (class A + C).** `CG_EyeOffset` (`cg_view.c` 10167) moves the eye; the viewmodel is anchored to it.
   Lean rolls the view: a rolled near plane cuts a long gun diagonally. Prone lowers the eye onto the gun's line.
6. **The ADS rig solve (class C).** `CG_AdsRigSolve` / `cg_adssights*.h` place the sight on the eye with a relief clamp of +-4
   units from the cheek weld (found in fg42hd). Guns whose rows push the rear toward the eye past `r_weaponznear` 1 slice in ADS.

## Test matrix

Guns: **every row of `docs/tools/loadout_weapons.tsv`** (76 in the roster today) plus their model variants
(`loadoutskins.scr` fids >= 8). Do not hand-list them - the harness reads the tsv.

Actions per gun (x 2 resolutions: 1920x1080 and 3440x1440; 4:3 1440x1080 as a spot check):

| # | action | why |
|---|---|---|
| 1 | idle (hip) | baseline; the near-plane suspect #1 |
| 2 | walk | bob |
| 3 | sprint (incl. sprint-to-fire) | the sprint lower pose + bob: the biggest swings |
| 4 | jump + land (hard landing) | landing severity |
| 5 | crouch, crouch-walk | crouch weight, eye drop |
| 6 | prone (where allowed) | eye on the gun line |
| 7 | lean left / right (standing and crouched) | rolled near plane, support hand |
| 8 | fire (single + full-auto burst) | recoil / kick stacking |
| 9 | ADS idle + ADS fire | rig solve, relief clamp |
| 10 | reload (hip + ADS; empty + loaded) | hands and magazines |
| 11 | weapon switch in / out | raise / lower |
| 12 | face a wall at 8, 16, 32 units | class B, the collision pull-back |
| 13 | turn fast (mouse flick) | lag spring overshoot |

Per cell: one still at the motion's extreme (the harness triggers the action and captures at its peak), plus a short frame
burst for 3, 4, 8 and 10. Tag each defect A / B / C.

## How to run it (sized for one client at a time, quiet)

- One pad-script run per gun covers rows 1-11 and 13 in one boot (~2.5 min at 85 s boot); row 12 needs a wall-facing spawn (one map,
  one spot, reused). 76 guns x 2 resolutions = ~152 runs, ~6.5 h of client time - run in batches between other sessions' queues.
- Harness: `run_fg42.py` generalised (it already takes gid / gun / WV_RES / WV_DISPLAY_RES=3440x1440 / muted / pad-script).
  **Rules (2026-11-08):** pad-script runs need an exe with de222de5 (`fg42hd-eng` 368e33b8); test windows on the 3440x1440 display
  picked by resolution; wait for every other `openmohaa.exe` to exit before each launch; close the client when the capture ends.
- Cheap, no-client triage first: an offline pass over every view tik's idle / sprint / reload clips (skc + skd, the tools in
  `docs/proposals/fg42hd_2026-11-08/tools` read both) computing each frame's nearest-vertex distance to the eye. Anything closer
  than `r_znear` 4 at the hip or `r_weaponznear` 1 in ADS is a class-A finding before a single client run.
- Automatic in-game flag (proposed, needs a small cgame probe): log `^~^~^ VMCLIP` when the view weapon's bounds come within
  `r_znear` of the eye in a frame where `weaponFovActive` is false - a machine-readable class-A detector for the batch.

## Carried over from fg42hd

- **Scope-in flash**: for ~3 frames on scope-in the RETAIL full-screen overlay (black side bars, green lens) shows before the lens
  view takes over (FG 42, run `fg_q6fg1080` r_08..r_14). Check the Kar98k and every other scoped rifle in the same matrix (row 9).
- ADS stills in snow / fog read the eyepiece ring grey for the Kar98k as well - the lens pass's blur, not geometry; do not log it as clipping.

## First fixes to try (after the data, not before)

1. Suspect #1: give the view weapon its own projection (near plane `r_weaponznear`) at the hip too - drop the `> 0.05` gate for
   the view-weapon pass. One condition in `tr_main.c`; affects every gun at once; needs a z-fighting check of hands vs gun.
2. A clamp on the summed first-person offset (cause 4), if the data shows stacking.
3. Per-gun fixes (class C) only where 1 and 2 do not cover it, through the existing generators (sight rows, hold tables).

## Findings (2026-11-09, steps 1-2 done, step 3 first fix in)

- **Offline pass** (`tools/clip_survey.py` -> `assets/clip_survey.tsv`, 781 rows, 723 mapped): **40 hip clips** bring gun or hands
  inside the world near plane (r_znear 4) - reloads, bolt work, pullout / putaway of the Johnson, Mosin, Enfield, L42A1, Kar98k,
  Gewehrgranate, Springfield, SVT, Carcano, Vickers-Berthier, shotgun, double barrel, Hi-Standard, FG 42 - and **all 40 clear at
  the weapon near plane**. 3 aimed rows go under 1 u (Mosin rechamber 0.71, Enfield reload 0.79, Springfield reload_end 0.87).
  106 coop `cv_*` / `coopr_*` aim rows have no aim pose to measure (no `_charge` row of their own).
- **Suspect #1 confirmed**: engine `viewclip-eng` 40ddb4e2 (`r_weaponProjAlways`, default 1) gives the view weapon its own
  projection at the hip too; mod `viewclip` 9bb365cf sets `r_weaponznear 0.6`. A/B in one boot (`tools/run_ab.py`): the Johnson
  reload's hand is sliced open before, solid after (`media/johnson_reload_before_after.*`).
- **Second class, not a near-plane cut (class C)**: some reload / bolt clips bring a HAND so close to the eye that it fills the view
  as a big low-poly, crumpled shape - identical before and after the fix: Kar98k aimed reload (the bolt hand), the double barrel's
  single-shell reload (hand 3.7 u from the eye). Needs the clips re-posed (hold_bake's clear_hand), per gun.
- **Scope-in flash**: the Kar98k sniper scopes in cleanly (run `fg_k98raise`, no retail overlay frame); the ~3-frame retail
  overlay is FG 42-only so far.
- Movement rows (sprint, jump, crouch, lean, fire, ADS) on Mosin / Enfield / double barrel / Kar98k / FG 42: no near-plane cut
  seen before or after; the gun stays > 4 u from the eye in those poses.

## Result (2026-11-09, pass complete)
- All 70 holdable guns run at 3440x1440 after the fix (hip fire, reload, switch, sprint, jump, crouch, lean, ADS, ADS
  reload, wall): review sheets media/uw_after_*.jpg. The only TRUE clipping found anywhere was the hip near-plane cut
  (40 clips) - fixed globally (r_weaponProjAlways 1 + r_weaponznear 0.6; before/after media/johnson_reload_3440_before_after.gif)
  - plus the double-barrel shell reload worked further out (4 clips). Bolt-rifle / Sten aimed reloads left as they are
  (user decision).
- Harness traps found on the way (not game bugs): sidearms load from w<gid>_s3.cfg (run_ab now picks the slot); the test
  overlay's older anims_shared.txt lacks the revolver reload anims -> the Webley / Nagant runs crashed the TEST server
  until the current file was laid over it for those runs (tools/vc_with_pak.py). The FG 42 Irons' tall rear diopter
  reads large at the hip but is attached and correct.
