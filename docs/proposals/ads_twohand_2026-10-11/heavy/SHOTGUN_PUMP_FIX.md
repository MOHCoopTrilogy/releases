# Pump shotgun: no pump stroke in the aim - FIX CUT (heavy lane, 2026-10-13, runs hj47-hj53) - bug-3844..3848

User, on the deployed integrated build: **"noticed the shotgun doesnt have the pumping action when in ads"**.
A follow-up to the frozen shotgun files: **new files and added rows only**, nothing of the integrated shotgun set is
changed. Everything is STAGED in this lane folder + one commit on the engine lane branch.

## What was wrong (reproduced on the deployed build, WITHOUT the lane overlay)
Runs hj47 (aim) / hj48 (hip): the user's cgame (`G:\GOG\...\cgame.dll` a7c8c1e6, copied into the harness as
`cgame_userinteg8`), the GOG paks as deployed, the harness plumbing overlay only. Three single shots each.
* HIP: the support hand racks the forend back and forward after every shot (retail clip `fire_shotgun_stand.skc`).
* AIM: the hull ejects, the pump sound plays, the support hand DOES NOT MOVE in any of the 244 frames
  (`evidence/shotgun_pump/shotgun_deployed_aim_vs_hip_hj47_hj48.jpg`).
* Cause, from the code and the view-animation trace (run hj49): **while the aim is held the server keeps the hands at
  `charge` (the aim pose) through every shot** - the hands row `shotgun_fire`, which carries the pump stroke, is never
  started. The gun's own `fire` row (`shotgun_fire.skc`, 32 frames) still runs the forend back (frames 10-11, 5.38 u)
  and forward (frames 20-21) - under a hand that stays where it is.
* **It was already so before the lane's work and before the integration (case a)**: the released rows file (fixes pak
  at 993f706) has no cycle row for the shotgun, its `shotgun_adsfire` row is referenced by no engine code, and neither
  the lane's "pump only when the gun was empty" change (it only picks the reload's END row), the break-off patch nor
  the integration's per-weapon rows touch the fire path. Not a regression of the rollout - a gap it left.

## The fix
The cgame already has a client-only "aimed per-shot cycle" (pistol lane 2026-10-12, Hi-Standard / Welrod): when the
clip ammo drops while the aim pose is up it plays a `..._cycle_ads` hands row and goes back to the aim pose at its end.
The pump gun gets its own row for it.

| what | file | note |
|---|---|---|
| NEW clip | `assets/models/human/animation/viewmodel/shotgun/coop_shotgun_cycle_ads.skc` (32 frames at 30 / s, 30 960 bytes, md5 **8b09ccff** - RE-TIMED, see "Hull and pull-back" below; the first cut was 4f95c41b) | `tools/sgpump.py`. The firing hand and the gun stay where the aim has them; the support hand keeps its aim grip and RIDES THE FOREND - its place is the aim grip moved by the forend's own travel in the gun's `fire` row, frame for frame (measured on the mesh), so hand and forend cannot part. Weight: gunphys class `shotgun`, the lane's `sg_pump_back` (frame 10) / `sg_pump_fwd` (frame 20) at 0.6: the gun leaves its aim by 0.27 deg / 0.28 u at most |
| 4 ADDED rows | `assets/models/player/base/fps_anims_shotgun.txt` (`tools/stage_rows.py`, the last four rows; the file's other rows are byte-identical to the integrated ones) | `coopr_shotgun_cycle` -> `viewmodel/shotgun/fire_shotgun_stand.skc` (retail hip clip: what an aim let go in mid-pump hands over to, and the base name the cgame needs), `coopr_shotgun_cycle_ads` -> the new clip, `coopr_shotgun_cyclelast` / `coopr_shotgun_cyclelast_ads` -> the same two clips (after the LAST shell) |
| engine | `ads-heavy-next` **54514e44** (cgame only; `tools/apply_cyclewpn.py <worktree>`, idempotent) = test DLL `cgame_heavy11` (a9655dd7; it also carries the M1919 sight row of the lane's next commit, inert for the shotgun) | see below |

**Per-weapon rows** (`coopr_shotgun_*`, keyed by the weapon NAME "Shotgun"; its finishes resolve through the
"(Finish)" strip). Nothing shared is repointed. No tik, no state file, no server-read row is touched.

### What the engine commit does, and what the integration needs of it
`apply_cyclewpn.py` handles both source shapes (tested on scratch copies of both files; **built and run only on
ads-heavy-next**):
* ads-heavy-next / the DEPLOYED integ-ads bb5dc05f: the cycle trigger knows only `<prefix>_cycle_ads`. The patch makes it
  look for `coopr_<weapon key>_cycle_ads` first.
* integ-ads from 2627cb94 on (HEAD 47acac77 today): the pistol lane's Welrod change already looks up
  `coopr_<weapon key>_cycle` - **there the two rows `coopr_shotgun_cycle` + `coopr_shotgun_cycle_ads` and the clip
  already give the pump after every shot with rounds left, with no engine change at all.** The patch adds two things:
  1. **same-mesh guard**: the per-weapon lookup falls back on the "(Finish)"-stripped name. "Shotgun (Double Barrel)"
     strips to "Shotgun" - without the guard the double-barrel gun (not shipped yet) would play the pump stroke after
     its first barrel. With it a stripped name only counts when the held gun is the same mesh as the base gun
     (`CG_AdsSightSameMesh`); an exact-name row always counts (the Welrod's rows are exact).
  2. **last round**: `coopr_<weapon key>_cyclelast_ads` plays when the shot that started it emptied the gun (the
     prefix rows stay "rounds left only"). At the hip the retail clip pumps after EVERY shot, the last one too - so the
     aim does the same. Without the patch (or without the two `cyclelast` rows) the aim shows no pump after the last
     shell; the reload from empty still ends with its own pump.
* No `coopr_<key>_cycle*` row = unchanged for every gun (the Hi-Standard's prefix row and the Welrod's rows resolve
  exactly as before). cvar `coop_vmAimedCycle 0` switches every aimed cycle off, as before.

## Checked
| check | result |
|---|---|
| trace, run hj49 / hj51 (`coop_vmTrace 1`) | after every aimed shot `id=16 row=coopr_shotgun_cycle_ads`, back to `shotgun_charge` 0.99 s later; 5th (last) shell `coopr_shotgun_cyclelast_ads`; the automatic reload starts 1.17 s after the last shot (`shotgun_reload_ads`), i.e. after the stroke has ended |
| six stances, sway on, run hj49 (3 shots each, every frame captured, `--tail 360:4`) | LOOKED AT in every stance: `evidence/shotgun_pump/shotgun_aimed_pump_stances_hj49.jpg` - the hand comes back along the barrel (frames 28-36 after the shot) and goes forward again (by frame 54), bead and barrel stay on the aim point |
| centre box | **the clip by itself adds 0.0 % of the box beyond the settled aim** (offline `offbox.py`, every frame: the hand slides inside the aim's own silhouette). The engine figure of an aimed SHOT cannot be told apart from the shot: the kick, the smoke and the hull read 3-13 % for a second after every shot with OR without the pump - see the table below |
| server timing | no server-read file is changed. Measured with a trigger press every 80 ms, clip ammo read per captured frame (16 ms): **shot to shot 1.200 s in all four intervals with the fix (run hj52) and 1.200 s in all four on the deployed build (run hj53)** - equal; at an 80 ms press cadence that is a fire delay between 1.12 and 1.20 s, the released 1.15-1.175 s |
| 0 `Script Error` in the session logs | hj47-hj52 |

Centre box AS PLAYED, % of the box beyond the aim's sway envelope, worst frame over three aimed shots (`boxeng.py --sway`,
`BOXENG_CLIPLEN=237`; hj49 = with the fix, hj50 = the deployed build, the same shots without a pump):

| stance | whole 3 shots: fix / deployed | pump windows only (frames 18-52 after each shot): fix / deployed |
|---|---|---|
| stand | 3.85 / 3.60 | 3.42 / 3.19 |
| crouch | 5.60 / 11.89 | 4.89 / 9.47 |
| prone | 5.25 / 7.03 | 3.26 / 5.25 |
| lean left | 3.30 / 1.93 | 3.30 / 1.93 |
| lean right | 11.42 / 12.99 | 11.42 / 12.38 |
| braced | 0.82 / 0.31 | 0.82 / 0.27 |

The spread between the two builds is the shot-to-shot spread of the kick (the deployed build reads HIGHER in three
stances). Only braced, where the kick is small, is a clean reading: 0.82 %. The 2 % bar is met by the clip itself
(0.0 % offline) and in the braced engine run; it is NOT shown by an engine figure in the five free stances, because
the released aimed shot alone does not meet it there.

## Evidence (`evidence/shotgun_pump/`)
* `shotgun_aimed_three_shots_pump_hj49.gif` - three aimed shots with the pump, standing, centre box drawn (2.3 MB,
  decoded and looked at). Finished.
* `shotgun_hip_three_shots_pump_hj48.gif` - three shots at the hip (deployed build = unchanged by the fix), for
  comparison (2.2 MB). Finished.
* `shotgun_aimed_pump_stances_hj49.jpg` - six stances x four moments of one shot. Finished.
* `shotgun_aimed_fix_vs_deployed_hj49_hj50.jpg` - fix against deployed, lean left and standing, the same frames.
* `shotgun_deployed_aim_vs_hip_hj47_hj48.jpg` - the report reproduced.

## Not done / weak points
* Built and run on `ads-heavy-next` only; on integ-ads the patch script was applied to a scratch copy of the file
  (it applies), not compiled, not run.
* An aim let go in mid-pump (hands over to `coopr_shotgun_cycle` = the hip clip at the same clip time), sprint /
  weapon switch in mid-pump, crouch + lean: NOT run.
* Third person not looked at (the server rows are unchanged: other players see what they saw before).
* Sounds not listened to (the gun's `fire` row plays `shotgun_snd_rechamber` at every shot, as before).
* The finishes (13 tiks) were not run one by one: they share the mesh, the hands rows and the weapon-name rule; the
  base gun was run.
* From the eye the stroke is a hand sliding toward the eye along the barrel - the forend itself is hidden under the
  hand and the receiver at this aim (relief 14 u): it reads as a pump by the hand's travel, not by the forend.
* `tools/run_h.py --pump` (new lane part: N single presses, every frame captured, boxeng-readable) and
  `boxeng.py` `BOXENG_SERIES=<json>` (per-frame series) are the tools used.

## Hull and pull-back (user: "do you see the shell eject when you pump?") - clip RE-TIMED, run hj56
* **Measured, first cut (run hj49, every 16 ms frame):** the hull is first in the picture 0.13-0.14 s after the client
  sees the shot and has left it by 0.19-0.24 s (the gun's `fire` row: `entry commanddelay 0.2 tagspawn tag_eject`).
  The forend - and with it the first cut's hand - went back only at clip frames 10-11 = 0.33-0.37 s. **The hull was
  out 0.13-0.2 s BEFORE the hand had even started back.**
* **The hip reference has the same mismatch**: the retail hip clip's hand is at the rear at its frame 11 (0.37 s), the
  hull leaves at 0.2 s. It is the retail gun row's own timing (eject at 0.2 s, forend at 0.33 s), hip and aim alike.
* **Fix (the HAND clip only, `tools/sgpump.py --pull 3,5`, the default now):** the hand leaves the front after clip
  frame 3, is half way at 4 and AT THE REAR FROM FRAME 5 (0.167 s), stays there, and goes forward WITH the forend at
  the gun's own frames 20-21. New clip md5 **8b09ccff** (32 frames, same rows, same length; `sg_pump_back` at frame 4).
  Offline the clip adds 0.2 % of the centre box.
* **Run hj56** (stand, crouch, lean left; 3 shots each; trace: `coopr_shotgun_cycle_ads` after every shot, 0 Script
  Error): hull first seen 0.144 / 0.144 / 0.128 s after the shot, the hand at the rear at 0.167 s - within one clip
  frame. The hull is in the aim view for 5-7 captured frames (about 0.1 s), right of the receiver, going up and to
  the right; it is not behind the hand. LOOKED AT: `evidence/shotgun_pump/shotgun_aimed_pullback_and_hull_hj56.jpg`
  (six crops: shot, hand starting back, further back, at the rear with the hull out, hull rising, hull leaving).
* **What this does NOT fix, plainly:**
  * the forend ON THE MESH and the pump SOUND still follow the frozen gun row (forend back at 0.33 s): for 0.17-0.2 s
    the hand is at the rear while the forend under it has not moved yet. From the eye the forend is hidden in this
    aim (under the hand and the barrel), so it is not seen; the sound was not listened to.
  * the hand now waits at the rear for 0.5 s (frames 5-19) before the forward stroke.
  * the HIP is unchanged: there the hull still leaves 0.17 s before the hand reaches the rear (retail).
* **The cleaner fix, a decision for the coordinator / user:** one CLIENT command in the gun's `fire` row -
  `entry commanddelay 0.2 tagspawn tag_eject` -> `0.35` in the 14 shotgun tiks - would put the hull on the real
  pull-back for hip AND aim (hand, forend, sound and hull together), and the first cut's clip (4f95c41b, hand on the
  forend frame for frame) would then be the right one. It is a client block: no server-read row changes length. The
  tiks are frozen, so it was NOT done here.
* The six-stance figures and GIFs above are of the first cut (hj49); only stand / crouch / lean left were re-run
  with the re-timed clip (hj56), and the GIF was not rebuilt.
