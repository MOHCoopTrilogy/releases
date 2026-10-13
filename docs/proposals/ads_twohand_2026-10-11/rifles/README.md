# RIFLE lane - aimed (ADS) first-person animations

Lane of `docs/proposals/ads_twohand_2026-10-11` (read the HANDOVER at the top of `../README.md` first: the standard and
the method are the pistol lane's). Rows: the `## rifle` section of `../coverage.md`. Nothing here is in the mod tree or
the fixes pak; everything is staged in this folder and on engine branch `ads-rifle-next`
(worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-rifle`, build dir `.cmake`).

# HANDOVER (2026-10-12 night) - state after the second session

**Step 1 (Kar98) is rebuilt to the user's correction and run in every stance; it is NOT a pass by the strict 2 %
bar and waits for the user's choice between two variants (GIF below). Step 2 is baked and running; 3-5 untouched.**

## The user's correction (2026-10-12, verbatim) - it overrides the first session's bolt cycle
> "Just a reminder, bolt actions should ideally not move much from locking onto target when the bolt is pulled back"
> "Like you can have weight etc but ideally it stays primarily on target"

The first session's cycle took the whole rifle 3.4 deg under the target for a second per shot. Rule now, for the
per-shot BOLT CYCLE: the rifle stays on the target, only the firing hand leaves; the reaction (tug, shove, cant, settle)
stays but small. "Comes down under the box" is allowed ONLY for the full reload's loading phase.

## What was found (three facts, all measured)
1. **What crossed the box at the clip ends was the rifle itself, jittering - an engine fault, fixed.** `CG_VMAdsTagRight`
   kept the gun on `tag_weapon_right` for the whole aimed bolt clip. That tag hangs off the hand that travels to the
   bolt; the clip's tag keys cancel the hand only AT the clip's frames, and between them lerp(arm) x lerp(tag) is not the
   gun's pose. Result: the rifle wobbled about 1 deg (single rendered frames 3 deg) for the 0.2 s of the reach and again
   on the hand's way back - in the shipped hand-keyed clips too (VMH probe, run rb3). Fix, branch `ads-rifle-next`
   **18dc8b36**: right tag only while the aimed clip blends in, then the server's tag (the still off hand), no fade
   (`CG_VMAdsTagRight`, new `CG_VMAdsBoltSolo`, `CG_VmTagHandoff`; `cg_adsSightDebug` trace also on the off-hand tag).
   Test build `cgames\cgame_rifle3.dll`. Runs rb4-rb13: gun steady, no pops in frame-by-frame playback. bug-3630 (the correction itself: bug-3631).
   The remaining 2-3 % in the first 3-5 frames of a cycle is the SHOT's own recoil still decaying (23 % at its peak).
2. **On the Kar98 the open bolt handle stands in the centre box when the rifle is fully on the sights** (run rb8,
   variant A: 15.5 % of the box, 64 frames per two cycles; offline 8 % at the lift, 17-20 % with the bolt back). No cant
   clears it (30 deg either way: 11-15 %): the handle's root is on the bolt body, on the centre line. Only lowering the
   RECEIVER does (0.75 u reads 1.4 % offline, 1.1 u 0.1 %).
3. **The hand was in the box because of the grip**, not the technique: the retail grip has the knob deep in the palm, so
   palm and fingers lay over the receiver left of the knob (25 % of the box alone at a cheek weld). `knob_off` moves the
   grip to the fingers; the hand's bulk is then right of / under the knob, outside the box (0 %).

## What is staged now (the default, "variant C") and the alternative
* **C - front sight on the target, receiver eased down** (`tools/boltphys.py`, per-gun `ease`): the butt eases down
  while the muzzle comes up about it, so the FRONT sight stays on the target and only the receiver / rear sight / bolt
  sink under the box (Kar98 1.25 u; Springfield and Mosin 0.5 u; Lee-Enfield 0 = fully locked, its handle stays under
  the sight line). Head 2 u back off the comb, 2 deg cant to the working hand, eased in over 11 clip frames (receiver
  down first, forward as the bolt opens). Stroke weight in roll and fore-aft tug, not muzzle swing; scale 2.5.
* **A - rifle locked on the sights** (`--set drop=0 --set pitch=0 --set back=-3`): sight line within 0.6 deg, but the
  Kar98's bolt handle and the bolt body fill the right half and the bottom of the box while the bolt is open.
* GIF, both side by side, two shots / two cycles, light wall, box drawn: `evidence/kar98_bolt_aimed_A_vs_C_rb8_rb7.gif`.

## RESULTS (engine, cgame_rifle3, yaw 172 light wall; `evidence/rb7_box.json` ... )
Front sight = how far the front sight is from the target, deg, whole cycle after the anim change. About 0.7 deg of it
is NOT the clip: the shot's recoil pose is held while an aimed clip that starts mid-recoil plays (bug-3597, the pistol
lane's fix on ads-next - merge it when the coordinator says it landed; the clip then plays about 0.7 deg lower).
"Sight line" = `sight dev` of the probe (the rear-to-front line against the view).

| clip (run) | stance | front sight off target | sight line | back to | centre box beyond the aim |
|---|---|---|---|---|---|
| Kar98 cycle C (rb7) | stand | 0.75-0.85 deg | 2.65 deg | 0.01 | 5.7-10.4 % (26-145 frames) |
| | crouch / prone | 0.88-1.24 / 0.78-1.09 | 2.65 | 0.01 | 6.0 / 4.8-7.5 % |
| | lean L / lean R | 0.86-0.91 / 0.77-0.98 | 2.65 | 0.01-0.02 | 4.0-4.6 / 5.5-6.8 % |
| | braced | 0.71-0.80 | 2.57 | 0.01 | 2.3-4.7 % |
| Kar98 cycle A (rb8) | stand | 0.78 deg | 0.59 deg | 0.00 | 15.5 % (64 frames): bolt handle + bolt body |
| Kar98 aimed reload (rb9) | stand / crouch | - | 3.7 deg (low phase) | 0.04 / 0.03 | 5.7 / 6.3 % in the two bolt phases, under 2 % while low |
| | prone | - | 3.7 | 0.03 | 1.5 % (pass) |
| | lean L / lean R / braced | - | 3.7 | 0.03 | 3.9 / 4.7 / 2.6 % |

**The 2 % bar is NOT met.** In C every over-the-bar frame is the same thing (zoom crops, `rbox.py --zoom`): the rifle's
own barrel and hand-guard top directly UNDER the front sight, with the support fingers beside it - visible because the
rear sight that hides them at the aim has sunk. No hand, no bolt handle, no knob; the target above the front sight is
clear in every frame. In A it is the bolt handle. The first session's "pass by going 3.4 deg under" is what the user
rejected. A decision is needed: C as it is, A, or a relaxed reading of the bar for the rifle's own barrel.

Playback, frame by frame (every GIF decoded with `rsheet.py --gif`):
* Kar98 cycle C: no pops. The receiver sinks in about 0.1 s as the recoil ends (reads as part of the recovery, brisk);
  knob lifted, drawn, shoved, turned down by the fingers, hand lower right; the case leaves at the right of the box;
  the receiver comes back up over about 0.4 s after the hand is on the grip. The knob and the hand are large at the
  right edge while the bolt is back (2 u from the eye).
* Kar98 cycle A: no pops; with the bolt back the bolt body is a large dark mass at the bottom centre and the handle
  crosses the right half of the box.
* Kar98 aimed reload (`evidence/kar98_reload_aimed_rb9.gif`): bolt opened with the front sight on the target, rifle
  lowered, about 0.5 s with no right hand in view (the left hand holds; the body-reach reaction added there is slight
  and hardly reads), charger thumbed in under the box, flicked off at the right, bolt closed on the target, back to
  the aim. No pops.
* Break-off (run rb10, standing, 70 frames into the reload = rifle low): FIRE does not interrupt (retail: the reload
  finishes, then the gun fires only on a new press); SWITCH puts the rifle away from the low pose and raises the next
  weapon, no pop seen at sheet scale; SPRINT (run forward): the reload continues while moving and ends in the aim.
  Looked at as sheets only, not measured.
* Hip reload lens fix (bug-3451, run rb11): stand, crouch, prone, lean L, lean R - the right hand stays lower right
  through the charger flick in all five, never across the centre.
* **Gewehrgranate (`kar98_mortar.tik`, prefix kar98mortar): has no aim at all** - no ironsight row
  (`ADSSIGHT norow wpn='Gewehrgranate'`) and no `kar98mortar_charge` row (run rb12: the gun never comes up, "Couldn't
  find view model animation kar98mortar_charge"). No aimed rows are staged for it; whether a grenade rifle gets an aim
  is a decision, not a missing row.

## RESULTS-2: Springfield, Mosin, Lee-Enfield bolt cycles (run rb13, overlay `ov_rifle_b4.pk3`, two shots each)
| rifle (hold) | front sight off target, six stances | sight line | back to | centre box beyond the aim (frames over, of 170) |
|---|---|---|---|---|
| Springfield (receiver eased 0.5 u) | 0.57-0.81 deg | 1.13 deg | 0.00 | stand 11.8 % (100), crouch 3.0 (42), prone 4.6 (1), lean L 4.6 (4), lean R 3.9 (4), braced 6.5 (2) |
| Mosin (0.5 u) | 0.61-0.80 deg | 1.15 deg | 0.00 | 6.6 (5), 4.7 (40), 4.6 (2), 3.0 (10), 4.2 (2), 5.4 (2) |
| Lee-Enfield (LOCKED, 0) | 0.57-0.82 deg | 0.36-0.64 deg | 0.00 | 6.4 (94), 10.9 (41), 6.3 (24), 11.9 (50), 7.4 (27), 2.6 (1) |

All three stay on the target and none meets the 2 % bar in the engine (offline said 0.6 / 1.3 / 1.1 %: not to be
trusted here either). Playback of each GIF (`evidence/<gun>_bolt_aimed_rb13.gif`, frames 8-37 decoded): no pops on any.
* Springfield: sight picture nearly unchanged; the open handle lies along the bottom of the box and passes its lower
  right corner, knob just outside; with the bolt back handle and hand are below the box.
* Mosin: the straight handle rises through the lower right corner of the box while open; the bolt body comes back as
  a long silver tube from the lower left; hand far lower right.
* Lee-Enfield: aperture locked on the target for the whole cycle; the working hand is in view at the right during the
  lift and the turn-down (it was below the frame), off the right edge of the GIF crop while the bolt is back; the
  rifle goes 3.3 u forward and back (the aperture visibly shrinks and grows - reads as a pump; try 2 u).
The box numbers swing with the capture ("aim covers" 3-19 % for the same pose): the settled-aim mask comes from six
frames of a breathing aim. A steadier reference (more frames, or `cg_weaponBreath 0` for the measure) is the next
thing to do before tuning any of these against the bar.

## How it is built (reuse for every bolt rifle)
* **Bolt cycle** - `cd assets; python ../tools/boltphys.py <gun>[,<gun>]`: hands = `ads_bolt_2026-10-04/tools/key_bolt.py`
  (right hand rides the gun's bolt bone) + `knob_off` (grip on the fingers); gun = `gunphys.simulate`, class `RIFLE`
  (m 4.1, 2.6 / 2.0 Hz, damping 0.62, almost no muzzle sag when the firing hand leaves), following ONE hold and
  answering `rb_up`, `rb_back` + `rb_stop`, `rb_fwd`, `rb_down`, `rb_grip` at the frames of the gun's own clip.
  Per gun in `GUNS`: stroke frames, `hold` (ease in / out frames), `ease`, `rc` (recipe overrides).
  `--set ease=x | drop= | pitch= | roll= | back= | hold=a,b,c,d`, `--rc knob_off=(x,y,z)`, `--scale`, `--suffix`.
* **Which part is in the box, offline** - `python ../tools/rpart.py <sight gun> models/human/animation/viewmodel/<aim>.skc
  "<clip>|rechamber" [--sheet out.jpg --zoom]`: per frame the box cover by SURFACE name, front / rear sight movement.
  Offline UNDER-reads the rifle's own barrel (its settled aim covers 20 % of the box, the engine's 8-13 %): use it for
  hand / bolt questions and for sweeps, never for the final figure.
* **Full reload** - `python ../tools/riflereload.py kar98` (hold_bake; holds `bolt` / `close` = the cycle's on-target
  hold, `low` = under the box; knob grip offset `bolt.off`; `body_reach` / `body_back` for the pouch trip).
* **Rows** - `python ../tools/rows_rifle.py` (released fixes copy + this lane's rows; hunks printed).
* **Engine run** (`G:\mohaa-adsanim2`, owner `adsanim2`, port 12558; set `ADS_RUNS=G:/mohaa-adsanim2/runs`):
  `python tools/mkov_rifle.py G:\mohaa-adsanim2\ov_x.pk3 --measure` then
  `python tools/run_rifle.py <id> --overlay G:\mohaa-adsanim2\ov_x.pk3 --cgame cgame_rifle3 --yaw 172 --guns kar98 --parts bolt2,reload --stances stand,crouch,prone,standL,standR,braced --set "set vss_draw 0"`.
  Parts: `bolt` (one shot + cycle), `bolt2` (two shots, two cycles), `reload`, `empty`, `hipreload` (`--hipall` = every
  stance), `breakfire` / `breakswitch` / `breaksprint` (`--breakat`, `--bframes`), `stills`.
  `--set "set cg_vmHandDebug 1"` adds the VMH probe (gun and hands per rendered frame: the tool that found fact 1).
* **Measure** - `python tools/rbox.py <id> [tag] --dump --zoom=<dir> --json=evidence/<id>_box.json`: box per frame
  (view-kick compensated), where the cover sits, zoom crops with the cover tinted red, sight line, front-sight offset
  (all frames / from 0.26 s into each cycle). `RBOX_FROM_FIRE=1` = include the shot's recoil frames.
* **Look** - `tools/rsheet.py <id> <tag> out.jpg a:b:step [--crop]`, `tools/rgif.py`, `tools/rgif2.py out.gif --panel
  "<id>|<tag>|<label>" --panel ...` (variants side by side), `rsheet.py --gif` to play a GIF back.

## Next (the coordinator's order)
1. Kar98: the user's choice A / C; then merge ads-next when told (bug-3597) and re-measure the front sight; the
   reload's no-hand half second still looks static; the receiver's 0.1 s drop at the start is brisk.
2. Springfield, Mosin, Enfield: cycles run in all stances (RESULTS-2 above) - on target, bar not met; raise the
   Springfield / Mosin ease until the handle clears the box corner (or accept, by the user's choice for the Kar98);
   shorten the Enfield's slide. Their aimed reloads: add `riflereload.GUNS` entries (events from
   `tools/clipinfo.py <tik> reload <view clip> lo,hi`). Arisaka + G98: kar98 prefix, own meshes - the cgame mesh guard
   (`CoopAdsClipFitsHeldGun`) keeps them on the hip clip; they need own clips (own knob positions) under own row
   names, or a guard table entry per mesh - not decided.
3. Garand / carbine / silenced Garand, 4. G43 / SVT / Johnson / Carcano / De Lisle, 5. one scoped rifle: untouched.

## Notes for the shared tools' owner (pistol lane)
* `coverage.py --lane rifles build` STILL crashes at line 476 (`rl.get` on a str) - 2026-10-12 19:00; it also runs
  `build` for an unknown argument such as `--help`. `scan` / `rule` / `action` / `note` work.
* `coverage.py scan` on this lane's captures: a `bolt` capture contains the shot, so `edge` reads the recoil (2.48);
  a reload's `end` reads 2.5 where `rbox.py` reads 0.03 - the lane's `ok` flags stay false whatever the clip does.
* `offbox.py` has no per-surface split (this lane's `rpart.py` has); `centrebox.py` has no cycle-after-shot mode.

## Files
`tools/` boltphys.py, riflereload.py, rows_rifle.py, mkov_rifle.py (+ ovbase_1021.pk3), run_rifle.py, rbox.py, rpart.py,
rsheet.py, rgif.py, rgif2.py, clipinfo.py, nosmoke.py (+ measure_ov/, measure only). `assets/` staged clips +
`*_phys.json` + `models/player/base/fps_anims_rifle.txt`. `coverage_status.json` this lane's rows.
Runs: `G:\mohaa-adsanim2\runs\ra1..ra7` (first session), `rb1..rb13` (this one; rb1-rb3 = before the engine fix;
rb7 Kar98 cycle, rb8 variant A, rb9 reload, rb10 break-off, rb11 hip reload, rb12 Gewehrgranate, rb13 the other three).
