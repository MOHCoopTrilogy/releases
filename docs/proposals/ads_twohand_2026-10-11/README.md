# HANDOVER (2026-10-12 late evening, PISTOL lane) - read this first, the rest of the file is the history

**State: A, B and C of the list are done and committed (engine `ads-next` 191f1879 = test cgame `cgame_adsnext9`).
D and E are NOT started.** Nothing is in the mod tree or the fixes pak; all of it is staged here.
RUN IDS: use the prefix `pa` (pa1, pa2 used). `boot_session` deletes an existing run folder - ids tm1-tm3 and tn1 of
earlier sessions were lost that way on 2026-10-12; `run_2h.py` / `run_break2.py` now refuse an existing id.
The work is split into four lanes since 2026-10-12: this folder's root is the PISTOL lane (pistols + revolvers) and it
OWNS `tools/` and `coverage.md`; `rifles/`, `smg/`, `heavy/` are the other lanes (own harness copies, own
`coverage_status.json`, merged by `tools/coverage.py build`; they read `tools/` as a library - keep changes there
backward compatible; the runs folder of every shared tool comes from `ADS_RUNS`).

## B, done (runs tl1-tl8)
| what | result | evidence |
|---|---|---|
| Prone pistol reloads | full length now: `tools/patch_prone_reload.py` - one prone torso alias per standing alias (Colt + sharers, P38, Hi-Standard, Beretta, C96) on the prone body clip retimed to the standing length (`coop_pistol_prone_reload_73.skc` / `_63.skc`) with the standing alias's own commands. View reload in prone: 150 frames for Colt / P38 / Hi-Standard (was 88), Beretta 129; hip AND aimed (the hip reload had the same cut). Revolvers have no prone line, unchanged. GAMEPLAY: prone pistol reload 1.50 s -> 2.43 s (Beretta 2.10 s). | `evidence/histandard_prone_reload_aimed.gif`, `histandard_reload_stances_tl8.jpg` |
| Hi-Standard rack | the releasing hand is a relaxed curl coming off to the left (was a splayed hand lifting straight up); the PER-SHOT rack is now inside the bar - it had never been measured: 7.9 % / 13.5 % of frames in run ti2, 25 % offline. Now engine tl8: per-shot max 0.5 %, reload max 0.3 %, back to 0.01 deg; offline 0.0 % / 0.2 %. | `evidence/histandard_aimed_cycle_reload.gif` |
| Pass bar | `coverage.py`: a weapon flagged `lowered` (declared rack / open-cylinder phase) passes a stance when the capture ends within 0.05 deg, pose >= 0.9 and the centre box (loaded, empty, per-shot cycle) is <= 2 %; no box figure = not passed. `centrebox.py --cycle` measures the per-shot segment. | `coverage.md` |
| Revolver break-off, second client | `tools/run_break2.py` (host serves, a joiner of the same install is driven by posted keys in real time and captured; overlay on `ovbase_1021_p2.pk3` = `MKOV_BASE`), `tools/breakmarks.py` (animation + `clip=` trace). FOUND AND FIXED: a press in FETCH closed, fired - and the gun opened again by itself 0.1-0.2 s later (the `reload` latch of CHECK_CONTINUE; `tools/patch_breakfire.py`: `donereloading` in `RELOAD_*_BREAK_FIRE`). Run tl7, Webley / M10 / Nagant, press in FETCH and in SEAT with 4 rounds in: close, owed shot, no restart, every round accounted for. Loopback only (no real latency). A second press DURING the close is absorbed into the one owed shot. | `evidence/breakoff_2nd_client_*.gif` |

Harness facts learned in B: a cfg `wait N` is only N ms under fixedtime (the host with `coop_isFixed 16`); on a free
running client time the capture from Python and post keys (run_break2.py). ADSFRAME carries `clip=` / `ammo=` from
cgame_adsnext8 on. `run_2h.py --parts reloads --rstances prone --rhip --revery 3` = aimed + hip reload in a stance.

## C, done (runs tl9, tl10, tn1-tn3, pa1, pa2; overlay recipe unchanged: `sh build_ov.sh ov_x.pk3`)
| gun | change | engine (emptied gun, aimed) | evidence |
|---|---|---|---|
| Webley | open and close states 0.53 s -> 0.8 s, HIP AND AIM (`tools/webslow.py`, then `revbake.py webley_hip / webley_ads`): the barrel tips over 12 frames (was 4), shuts over 10; hands re-keyed, sounds / cases moved with it. A Webley reload is 0.27 s longer at each end. | box max 0.3 %, 0.00 deg, 5 stances (tn1) | `evidence/webley_reload_aimed_c.gif` |
| S&W M10 | dump pose raised 1.4 u and flattened (cylinder face fully in frame), cases thrown up and left | box max 0.4 %, 0.00 deg, 5 stances (tn2, pa2) | `evidence/m10_reload_aimed_c.gif` |
| Nagant | worked 1.8 u higher (gate 5.6 u under the eye line - the limit of the 2 % bar), feeding hand comes from below, lower support elbow; in prone the gun and both hands are in frame now | box max 0.3 %, 0.00 deg, 5 stances (tn3) | `evidence/nagant_reload_aimed_c.gif`, `revolver_stances_tn.jpg` |

M10 cases "vanishing near the top of their arc": they do not - the evidence GIF's crop (x from 240) cut them off on
the left. Full frames of run pa2: out at f276, top of the arc f282, out of the bottom-left of the frame f286 = 0.17 to
0.2 s, which is what brass does at that distance under the game's gravity (800 u/s2); left as it is, the GIF is
re-cut (crop from x 140) so the arc is in it. Capture frames are 16 ms; a GIF frame of dgif `:3` is 48 ms.
Still weak, seen in playback: the Nagant's left forearm is still large for
about 0.1 s at the hand-over; the Webley hip open / close were looked at only at coarse scale.
NOT DONE - M10 chambers filling one by one. Design (about half a day): (1) `m10face.py` appends six surfaces
`coop_round1..6` instead of the one `coop_m10_heads` (round k on the chamber k steps behind the feed chamber; round 6 on
the feed chamber); (2) cgame, in the held-gun block of `cg_modelanim.c` (where `reload_end_ads` is chosen): a surface
named `coop_round<N>` is drawn iff N <= STAT_CLIPAMMO - but latched, so a new round shows when the loop clip restarts;
(3) `m10build.py`: the loop clip spins `coop_cyl` one chamber over its last 4 frames (the pattern is then continuous
across the restart); (4) the tik's `surface coop_m10_heads +/-nodraw` lines go. The Webley / Nagant could use the same
rule. Gun frame axes for particle rows: x forward, y right, z DOWN.

bug-3597 (does the rig-solve target freeze mid-recoil on an emptied gun?): measured, NOT confirmed - see the buglog
entry and `cg_view.c` CG_AdsRigSolve; `cg_adsSightDebug 2` prints `ADSSETTLE`, `tools/sightend.py <run>` prints the
sight line at and after the clip's end. The Colt's 0.08 deg at the end of its empty reload is the baked physics tail.

## The standard (every aimed reload / cycle, all three)
1. ON TARGET - centre box (middle 20 % of the screen) covered beyond the settled aim under 2 % in every frame; where
   the mechanism cannot be worked on the sights the gun comes DOWN under the box and returns to within 0.05 deg.
2. THE WEAPON REACTS with weight - every motion from a cause, through `tools/gunphys.py`, never decorative keys.
3. THE ACTION REALLY WORKS on the model, by the hand that suits the real control; reproduce the hip technique.

## What passes now (revolvers, aimed, runs tk11-tk13 on cgame_adsnext7 + `G:\mohaa-adsanim\ov_revolvers_default.pk3`)
| gun | engine box max | offline box max (every frame) | back to | per round | GIF (20 fps, centre box drawn) |
|---|---|---|---|---|---|
| Webley | 0.2 % (empty tk13, 3 rounds tk4) | 0.2 % | 0.00 deg | 2.5 deg swing | `evidence/webley_reload_aimed_low_small.gif` |
| S&W M10 | 1.6 % (tk11), 0.3 % (3 rounds tk4) | 0.2 % | 0.00 deg | 2.5 deg swing | `evidence/m10_reload_aimed_low_small.gif` |
| Nagant | 0.4 % (tk12) | 0.0 % | 0.00 deg | 0.8 u shove + 1.1 deg (from the clip) | `evidence/nagant_reload_aimed_low_small.gif` |

M10 run tk13 read 4.5 % in its first five measured frames: that is the last shot's smoke over the brown door (the
model is outside the box there - offline 0.2 %, partial reload 0.3 %). The hip reloads were not touched.

Known weak points, seen in playback (tell the user, do not hide them):
* Webley close: the gun turns upright in about 0.1 s (two GIF frames) - brisk; the support hand lands on the grip in
  the last two frames of the rise. Open: the barrel still tips in about 0.1 s (eased, was 3 frames linear).
* M10: cases are in view for about 0.16 s, low left, in front of the sleeve; the dump's cylinder sits at the bottom edge.
* Nagant: the whole work is at the bottom edge of the frame (gate just in view); during the hand-over the left
  forearm comes in large from the left edge for about 0.2 s.
* Break-off states: re-run from a second client with the new clips in B (below) - one defect found and fixed.

## How A was done (reuse this for every other gun)
* `tools/revbake.py`: aimed sets now use a list of `gun_abs` poses - `Tlo` (the aim dropped straight down, aligned)
  then the work pose. Leaving: Tlo weight 0->1 first, work pose after; returning: work pose off first, then Tlo->aim.
  A gun that rises / falls aligned stays inside the aim's own silhouette, so the box cover is zero by construction.
  `curl()` = finger_add for a hand on a thin part. Physics event frames per family in the set's `phys` dict;
  `REV_SEAT` (default 2.0) scales the per-round reaction; `gate_seat` / `cyl_turn` are the Nagant's actions.
* Gun-side clips: `tools/retime.py ... warp new:old,...` moves / eases a part of a gun clip; the staged tiks carry
  `reload_ads_loaded` / `reload_ads_empty` (aimed open), `reload_end_ads`, `reload_single_ads`
  (`tools/patch_tik_ads.py`, `patch_tik_nagant_single.py`); cgame ads-next shows them in an aimed reload.
* Check OFFLINE first: `sh tools/rev.sh <webley|m10|nagant> [sheet.jpg]` bakes, builds `_ov_wip.pk3` and runs
  `tools/offbox.py` (box cover over EVERY clip frame; needs `IRONSIGHT_EXTRA_PAKS=<overlay>` for staged gun clips).
  The engine measure (`centrebox.py`) skips the first 20 capture frames of an emptied gun and still counts smoke.
* Engine run (the working copies live in `SCRATCH\ads2h`, synced into `tools/` at each commit; no lock / slot needed):
  `sh build_ov.sh ov_x.pk3` then
  `python run_2h.py <id> --overlay <abs path>\ov_x.pk3 --cgame cgame_adsnext7 --guns webley,m10_revolver --parts demoy --demoempty --demoreload 450 --shots 6`
  (Nagant: `--guns nagantrev --shots 7 --demoreload 500`; partial reload: drop `--demoempty`, `--shots 3 --demoreload 260`).
  Never give 7 shots to a 6-round gun: the 7th press is a break-off. Then `python centrebox.py <id> --dump`,
  `python loopreact.py <id>`, `python animmarks.py <id>` (ADSFRAME `anim` / `sight` do not describe a gun on the
  off-hand tag: the Nagant reads 6 -> 8 and 0.00 deg while its loop plays).
* GIF: `python dgif.py <id> <gun> out.gif --frames a:b:3 --w 400 --crop 240,120,1040,720 --box` (delta frames, about
  2 MB for 130 frames), then `python gifsheet.py out.gif sheet.jpg a:b:1` and LOOK at every frame of the transitions.
* Python patch scripts are written with the file tool - a heredoc mangled `\t` / `\s` again today (bug-3581).

## The list from here (PISTOL lane; order given by the coordinator; report at each letter)
D. Welrod (bolt action after EVERY shot and after the reload; knob at the rear on the sight line: lower / roll the
   gun as for the Hi-Standard). Then Mauser C96 (stripper clip from the top), Luger, PPK, TT-33, Nambu, the silenced
   variants: each needs its own in-engine run (the 15 pistols sharing the Colt / P38 clips were only checked
   offline; add harness keys). Silencers must not meet the support hand or the box.
E. Trim the Colt and P38 empty reloads and the Beretta loaded one (each a few frames over 2 %); the Beretta reads
   near-black (seen again in run tl3, prone); the P38 open slide shows a dark gap from behind; braced and
   vehicle-seat stances for every pistol; every stance LOOKED AT.
A pistol row is DONE only with: aim pose, aimed reload (loaded + empty), per-shot cycle where the gun has one, all
stances run and looked at, the three yes columns, a run id. Hi-Standard: all of that except braced / vehicle seats.

---

# Two-handed pistol aim (2026-10-11)

User: *"We were supposed to also have two hands holding handguns in ads btw"* - part of the "everything under aimed
reloads" order. Continues `docs/proposals/ads_bolt_2026-10-04` (same harness, same baker).

**Status: Colt .45 done end to end and tested in the engine; STAGED ONLY, waiting for the user to approve the pose
before the other five handguns are built.** Nothing is in `docs/tools/assets/fixes`, nothing is in the mod tree,
nothing deployed, no engine change.

## 1. How the pistol aim pose works today (from the code)

* Aiming plays the gun's `<prefix>_charge` row of `models/player/base/fps_anims_pistol.txt`: a ONE-frame pose clip
  (`viewmodel/coltpose00.skc` for the Colt, Beretta, Webley, Nagant and M10; `p38pose00.skc`; `hs_pistol00.skc`).
  Hip idle to aim is the row's 0.3 s crossblend. The three clips are the same pose within 0.6 u.
* In those clips the left arm hangs at the hip (left hand 30 u below and 20 u left of the eye) - the pistol is
  held one-handed. The rifles get their left hand from their own aim clip in exactly the same way.
* Aimed fire plays no clip (`player_Torso.st` `ATTACK_PISTOL_PRIMARY_AIM` -> `viewmodelanim charge`); the kick is the
  procedural muzzle flip of `cg_view.c` (`cg_adsPistolKick`), which turns the WHOLE first-person rig about the wrist.
  So a support hand keyed into the aim pose rides the recoil with the gun by construction.
* The off hand is drawn while aiming for every gun that has a sight row (`CG_AdsRigSolveOwns`); a pistol without one
  keeps today's hidden off hand (`cg_adsHideOffHand`) and simply stays one-handed.
* Every pistol that has no prefix of its own (Luger, TT-33, PPK, Nambu, Welrod, C96 via `p38`, the silenced ones, the
  Colt variants) uses `colt45_*` or `p38_*`, so it inherits the pose of that row.

So the two-handed hold is DATA only: a new one-frame aim clip per row, and the aimed reload re-baked to start and end
on it. No cgame change.

## 2. The pose (`tools/mk2h.py`, recipe `assets/colt45_recipe.json`)

A wrap-around support grip: the left palm on the left grip panel over the firing hand's fingertips, left fingers
around the front of the firing hand's fingers with the index pressed up under the trigger guard, left thumb forward
along the frame under the slide, outboard of the right thumb. Nothing on the slide, nothing near the sights.

Built, not hand-keyed, so it can be repeated per gun:
1. **Mirror** the firing hand's grip through the gun's vertical centre plane. The plane and the axes are the SIGHT
   LINE's (rear sight -> front sight, the sight row's up), not the weapon tag's, because the Breakthrough pistols are
   root-frame meshes with other axes. The rig's left/right bones are mirror frames with local z flipped
   (`F = diag(1,1,-1)`, measured from the hand meshes by `tools/mirconv.py`; finger flexion is +z on both sides).
2. **Move it into a support grip**: 0.7 u forward, 0.5 u out, 1.4 u down (index under the guard), then 25 deg of yaw
   about the front strap so the wrist swings out to the left and the fingers reach further round.
3. **Fingers**: the index takes the middle finger's curl (the mirrored trigger finger would lie in the guard), all
   four opened 12 / 25 / 15 deg at knuckle / middle / tip to go around the firing hand; the thumb's three bones are
   aimed at points on the frame.
4. **Left arm** by two-bone IK. The retail pose's left shoulder sits 2 u in FRONT of the eye (it was posed for a
   hanging arm), which forces a 65-90 deg wrist; the shoulder is turned back (clavicle 121 deg, to about where the
   right one is) and the elbow put out to the left. Wrist bend 8 deg (the firing hand's is 33).
5. Everything else - trunk, eye, the whole right arm and its fingers, `tag_weapon_right` - is bit-identical to the
   source pose (`right_same 0.0`), so the rig solve and the sight picture cannot change. `tag_weapon_left` is keyed
   onto the gun, as the `_ads` clips do.

Offline previews (`--view`, the calibrated ADS camera of `ads_bolt` + close-ups) agreed with the engine stills to
within what can be seen; `evidence/colt45_grip_closeups_offline.jpg` is the fit check from the side, front and top.

## 3. The aimed reload on that pose (`hold_bake.py` `left_grip`, `tools/bake_p.py`)

The shipped Colt aimed reload (`fixed_right`, bug-3467) is reproduced byte for byte by `bake_p.py colt45_reload`
(md5 ebe2bb7b) and is still reproduced after the change below.

With a hand on the gun the old bake threw it out of view in two frames: it blends toward the retail left hand, which
starts and ends hanging at the hip. New recipe option `left_grip {fa, fb, way, hold}`: the support hand travels from
the aim grip straight to where the retail art has it at frame `fa` (12) and from frame `fb` (61, the palm under the
magazine floor) back onto the grip, on a smootherstep with a sideways bulge so the fingers come off the firing hand
before the hand drops; its fingers open on the same track, twice as fast. Between `fa` and `fb` the retail relation
is untouched. First and last frame are the aim pose exactly.

## 4. Engine runs (private install `G:\mohaa-adsanim`, slot word `adsbolt`, m3l2 harness spot, 1280x720)

The install was refreshed first: exe / game / gl1 / gl2 and `cgames/cgame_1022d.dll` from `SCRATCH\built_1022d` (the
released v1.10.21 set: exe affd0767, game 689d0db1, gl2 4bc77ba0, cgame 6d6799b2), and its `pristine` autoexec /
coop_defaults from the released copies. The old files are in `G:\mohaa-adsanim\bak_pre1022d\`. The harness plumbing
(`coop_mod/weather.scr` + marker shader) was rebuilt on the RELEASED weather.scr (`tools/mkbase.py`); the overlays up
to ab60 carried a copy from before 2026-09-28.

Overlay = plumbing + the released fixes-pak `fps_anims_pistol.txt` with `colt45_charge` repointed + the two clips
(`tools/mkov.py`; `G:\mohaa-adsanim\ov_2h_c.pk3` md5 58e2771f). Released cgame, no test build.

| run | what | result |
|---|---|---|
| th1 | first pose (mirror, hand under the guard, shoulder untouched) | plays, but reads as one lump of flesh from the eye |
| th2 | hand yawed out, thumb forward, shoulder back | reads as two hands; a detached sliver of left cuff at the bottom edge |
| th3 | elbow further out (final) | below |

th3 (2026-10-12 01:10, 4.1 min, 1488 shots, 0 script errors, window clean), `logcheck.py th3` and
`tools/democheck.py th3`:

| scenario | ADS pose factor | sight line |
|---|---|---|
| settled aim: stand, crouch, prone, lean L, lean R, crouch-lean L, crouch-lean R | 1.00 | 0.0 deg |
| demo, raise (50 frames) | 0.23 -> 1.00 | settles to 0.01 deg |
| demo, two aimed shots | 1.00 | kick 3.93 / 3.98 deg, back to 0.01 deg |
| demo, aimed reload (170 frames) | 1.00 | max 1.30 deg (logcheck gate 6), 0.35 deg in its last sixth |
| aimed reload: crouch, prone, lean L, lean R | 1.00 | max 1.3 deg, edges 0.6 - STAYS IN ADS |

Looked at, frame by frame (sheets in `G:\mohaa-adsanim\gifs\twohand\`):
* raise - the support hand comes up from the lower left at about 2/3 of the raise and closes on the gun; it never
  crosses the lens. Two fingers show open for one or two frames just before it lands (f26).
* fire - both hands ride the flip as one piece; the slide cycles between the thumbs; nothing separates.
* aimed reload - starts and ends on the pose; the hand leaves down-left, comes back open from the left and wraps.
* lower - the hand is off the gun and out of view within eight frames, the gun is at the hip by frame 20.

## 5. Not verified / known weak points

* **Only the Colt .45 mesh was looked at.** `colt45_charge` is also the pose of every pistol that falls back to the
  Colt prefix (Luger, TT-33, PPK, Nambu, Welrod, silenced Colt / TT / Luger / Beretta, the Colt variants) - not one of
  them was run. The support hand wraps the firing HAND, which is the same on all of them, so first-order it fits; a
  longer grip or a fatter frame can still poke through.
* P38, Hi-Standard, Beretta, Webley, Nagant: not built yet.
* The magazine exchange itself happens below the frame, as in the shipped clip: for about 1.5 s only the firing hand
  and the gun are on screen. That is the next step's work (retune the aimed pistol reloads), not changed here.
* Braced and vehicle seats: not run for the pistol.
* Hip to aim while moving, sprint-out and weapon switch from the aim: not captured.
* A wandering NPC walks into two of the stance stills; it is the map's, not an artefact.

## 6. Shipping it (after approval)

Per gun: the pose clip -> `docs/tools/assets/fixes/models/human/animation/viewmodel/pistol/<gun>_ads2h.skc`, the
`<gun>_charge` row of the fixes-pak `fps_anims_pistol.txt` repointed (the mod-tree copy stays the released one, as the
`gen_fixes_pak.py restore` recipe needs), the re-baked `<gun>_reload_ads.skc` over the shipped one, manifest entries.
`coop_vmAdsAnims` does not gate the pose (it is the aim row itself); a one-key A/B would need a cvar-selected row.

## Files

`tools/` (working copies in `SCRATCH\ads2h`): mk2h.py (pose builder), var.py (variant sheets), mirconv.py /
insp.py / gungeo_q.py / lpath.py (measurements), bake_p.py (pistol reload bake), clipview.py / blendsim.py (offline
frames), mkbase.py / mkov.py (overlay), run_2h.py + go.sh (harness run under the heavy lock + slot), democheck.py
(per-segment numbers), sheet.py (sheets, GIFs). `assets/`: the recipe and the two Colt clips (pose a97b8330, reload
ca75453b). `evidence/`: stills. Sheets, GIF and MP4: `G:\mohaa-adsanim\gifs\twohand\`.
