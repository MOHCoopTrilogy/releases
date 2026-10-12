# RIFLE lane - aimed (ADS) first-person animations

Lane of `docs/proposals/ads_twohand_2026-10-11` (read the HANDOVER at the top of `../README.md` first: the standard and
the method are the pistol lane's). Rows: the `## rifle` section of `../coverage.md`. Nothing here is in the mod tree or
the fixes pak; everything is staged in this folder and on engine branch `ads-rifle-next`
(worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-rifle`, build dir `.cmake`).

# HANDOVER (2026-10-12 evening) - state after the first session

**Step 1 of the order (Kar98 as the reference rifle) is staged and run; steps 2-5 are not done** (three more bolt
cycles are baked and pass the offline check, not yet run in the engine - see "Next").

## What exists
| gun | row | clip | status |
|---|---|---|---|
| Kar98 | `kar98_rechamber_ads` (existing row, clip replaced) | `assets/.../viewmodel/rifle/kar98_rechamber_ads.skc` | see RESULTS |
| Kar98 | `kar98_reload_ads` (NEW row) | `assets/.../viewmodel/rifle/kar98_reload_ads.skc` | see RESULTS |
| Springfield / Mosin / Enfield | existing `*_rechamber_ads` rows, clips replaced | `assets/.../{rifle,mosin_nagant,enfield}/*_rechamber_ads.skc` | baked, offline box 0.0 %, NOT run in the engine |

## How it is built (reuse for every bolt rifle)
* **Bolt cycle** - `tools/boltphys.py <gun>`: the HANDS are `ads_bolt_2026-10-04/tools/key_bolt.py`'s (right hand rides
  the gun's own bolt bone from the retail knob grip, rolled under / swung right of the knob); the GUN no longer takes
  hand-set keys. `key_bolt`'s `keys` are generated for every frame from `gunphys.simulate` with a rifle class
  (`RIFLE`: m 4.1, 2.6 Hz with the firing hand on / 2.0 Hz off, damping 0.62) following ONE hold (`HOLD`: off the cheek
  3 u along the sight line, 1.2 u down, muzzle 2.3 deg down, canted 3 deg to the working hand) and answering the four
  strokes (`rb_up`, `rb_back` + `rb_stop`, `rb_fwd`, `rb_down`) and the hand landing on the grip (`rb_grip`) at the
  frames the gun's own rechamber clip makes them. Stroke impulses are scaled x4 (`--scale`): at x1 the strokes moved
  the rifle 0.2 deg / 0.1 u, which does not read on screen.
* **Full reload** - `tools/riflereload.py <gun>`: `hold_bake` (both hands keep the retail hip clip's hand-to-gun
  relation frame by frame, so the technique is the gun's own), the gun pose = `gunphys` following a short list of
  HOLDS (`bolt` on the sights, `low` = butt dropped toward the armpit so the open action sits under the centre box,
  `close`), rotation about the butt (`dip_pivot` -22). Bolt strokes inside the reload use key_bolt's knob grip
  (`right_path` with `relT` keys riding the bolt bone). `prop_until`: the hand tag that carries the server's ammo prop
  keeps the hip art's value while the prop exists, afterwards both tags are on the gun.
* **Check offline first**: from `assets/`:
  `python ../../tools/offbox.py kar98 models/human/animation/viewmodel/kar_stand00.skc "<clip>|rechamber"` and
  `"<clip>|reload|1,100"` (the `|lo,hi` = frames the gun is on the off-hand tag; without it a reload renders the gun on
  the prop tag and reads 20 %).
* **Rows**: `python tools/rows_rifle.py` writes the staged `fps_anims_rifle.txt` = the released fixes copy + this
  lane's rows (apply-on-top; hunks are printed).
* **Engine run** (`G:\mohaa-adsanim2`, owner `adsanim2`, port 12558):
  `python tools/mkov_rifle.py G:\mohaa-adsanim2\ov_x.pk3 [--measure]` then
  `python tools/run_rifle.py <id> --overlay G:\mohaa-adsanim2\ov_x.pk3 --cgame cgame_rifle2 --guns kar98 --parts bolt,reload --stances stand,crouch,prone,standL,standR,braced --set "set vss_draw 0"`
  then `python tools/rbox.py <id> --dump` (centre box per frame, view-kick compensated, sight deviation),
  `python tools/rsheet.py <id> <tag part> out.jpg a:b:step`, `python tools/rgif.py <id> <tag part> out.gif --frames a:b:3 --w 400 --crop 240,120,1040,720 --box`,
  and `python tools/rsheet.py --gif out.gif sheet.jpg 0:999:1` to play a GIF back frame by frame.
* **Measure-only overlay** (`--measure`, `tools/nosmoke.py`): the shot's lingering muzzle smoke hangs in the centre box
  while the bolt is cycled and the engine measure counts it on the dark door; the measure run carries the gun's tik
  with that one emitter removed. Never staged for shipping (`tools/measure_ov/`).

## Engine (branch `ads-rifle-next`, from ads-next 94bb3dca)
One change, `code/cgame/cg_modelanim.c` **`CG_VmTagHandoff`**: a switch back to `tag_weapon_right` while aiming
(`CG_AdsPoseFactor() > 0.5`) does not fade. The reload's hand-over back to the main hand arrives while the view blends
into the aim pose, whose `tag_weapon_left` sits 16 u up the fore-end; fading from that tag swung the rifle out to the
right for 0.2 s after every aimed Kar98 reload (run ra2). Test builds: `G:\mohaa-adsanim2\cgames\cgame_rifle1.dll`
(branch point), `cgame_rifle2.dll` (with the change).

## RESULTS (runs ra5-ra7, cgame_rifle2 = engine 705832a8, overlay `ov_rifle_a7m.pk3` = staged files + measure tiks)
Engine centre box = `rbox.py` (per frame, view-kick compensated, smoke emitter off); offline = `offbox.py` every frame.
The ra5 rows are one clip revision older than ra7 (before the softer bolt-down roll, the reach waypoint and `prop_from`).

| clip | stance | engine box max (frames over 2 %) | offline | back to |
|---|---|---|---|---|
| Kar98 bolt cycle | stand | 3.4 % (5: two after the recoil, three at the return) | 0.5 % | 0.00 deg |
| | crouch / lean L / lean R (ra5) | 8.1 / 4.7 / 5.6 % (5-9 frames, same two places) | | 0.00-0.01 |
| | prone / braced (ra5) | 4.7 % (2 frames out of the recoil) / 1.2 % | | 0.00-0.01 |
| Kar98 aimed reload | stand | 5.5 % (5: view frames 3-5 and the last two) | 0.0 % | 0.02 deg |
| | crouch / lean L / lean R (ra5) | 3.4 / 4.7 / 3.3 % (3 frames each) | | 0.01-0.02 |
| | prone / braced (ra5) | 1.5 % / 1.5 % | | 0.01 |
| Springfield / Mosin / Enfield bolt | stand only | 3.5 % (6) / 5.7 % (10) / 7.3 % (3) | 0.0 % each | 0.00 (Springfield capture ended early) |

**The 2 % bar is NOT met in the engine** for 2-10 frames per clip, all at the two ends (leaving the recoil pose /
re-entering the aim); every frame in between is under it. The offline check does not see it (no recoil pose, no blend,
no sway), so it cannot be trusted alone for the ends. Not found yet which part crosses the rim - suspects: the fire
row's recoil pose still blending out when the cycle row starts (0.06 s), and the support hand's fingers beside the
fore-end as the rifle comes back up.

Playback, frame by frame (GIFs in `evidence/`, sheets `kar98_*_playback_ra6.jpg`, `kar98_reload_start_ra7.jpg`):
* Kar98 bolt: knob lifted, drawn, shoved, turned down by the right hand, visible lower right; case leaves as the bolt
  comes back. The rifle sits 3.4 deg under the target for about 1 s (target clear above it). After the bolt is down
  the rifle stays low about 0.3 s while the right hand goes back to the grip below the frame - reads slow.
  The palm is the same large flat slab as the shipped clip.
* Kar98 reload: bolt opened at the hold, rifle lowered, **0.9 s with the rifle low and no right hand in view** (the
  pouch trip is off screen), charger thumbed in below the box, the empty charger flicked off at the right edge at box
  height (outside the box), bolt closed on the way up, back to the aim. No jump at the start (ra7), no swing at the end.
  The measure's "sight dev" for a reload is not meaningful (gun on the off-hand tag).
* Springfield / Mosin: hand and bolt shown. **Enfield: the working hand is almost entirely below the frame** - defect.
* Kar98 HIP reload (bug-3451, shipped `coop_kar98_reload.skc`, run ra1): the right hand stays lower right through the
  charger flick, never through the lens (`kar98_hipreload_flick_ra1.jpg`, every 2nd frame 106-136). Standing only.

## Next (in the coordinator's order)
1. Kar98: find and remove the 3-6 % at the clip ends (zoom the box at capture frames 27-32 / 89-92 of a bolt run;
   try a longer `coop_vmAdsInBlend`, or start the hold 2 frames later); shorten the low wait after the bolt; the
   `kar98mortar_*` rows (rifle grenade Kar98) have no `_ads` rows yet; break-off states (fire / switch / sprint during
   the reload) NOT run; crouch-lean and vehicle stances NOT run.
2. Springfield (3-part reload: `springfield_reload` / `_single` / `_end`), Enfield (raise the hand into view), Mosin,
   Arisaka + G98 (kar98 prefix, own meshes: the cgame's mesh guard keeps them on the hip clip - needs their own clips
   or a guard change): all stances, then the aimed reloads with `riflereload.py` (add a `GUNS` entry per gun: holds,
   pose timeline, events from `tools/clipinfo.py <tik> reload <view clip> lo,hi`).
3. Garand / carbine / silenced Garand, 4. G43 / SVT / Johnson / Carcano / De Lisle, 5. one scoped rifle: untouched.

## Shared-tool notes for the pistol lane
* `coverage.py --lane rifles build` fails at line 476 (`rl.get` on a str: some lane's status has `rule` as a string;
  this lane's are dicts). `scan` / `rule` / `action` / `note` / `lowered` work.
* `offbox.py --prop` only applies to `_single` parts: a reload's hand-held ammo prop is not drawn offline.
* `centrebox.py` has no view-kick compensation and no cycle-after-shot mode (this lane's `rbox.py` has both).

## Files
`tools/` boltphys.py, riflereload.py, rows_rifle.py, mkov_rifle.py (+ ovbase_1021.pk3), run_rifle.py, rbox.py,
rsheet.py, rgif.py, clipinfo.py, nosmoke.py (+ measure_ov/, measure only). `assets/` staged clips + `*_phys.json`
(the holds, events and class each clip was baked from) + `models/player/base/fps_anims_rifle.txt`.
`coverage_status.json` this lane's rows. Runs: `G:\mohaa-adsanim2\runs\ra1..ra7`.
