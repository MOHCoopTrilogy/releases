# HEAVY lane (MGs / shotgun) - HANDOVER, 2026-10-13 (sixth agent). Read this first.

Lane of the aimed-animation work: the `## mg` and `## heavy` rows of `../coverage.md`. The method is the pistol
lane's (`../README.md` top section); this file says what is different here, what is done and what is next.
**Everything is STAGED** in this folder and on engine branch `ads-heavy-next` (worktree
`C:\mohaa-coop-dev\openmohaa-hzm-ads-heavy`, build dir `.cmake` - NOT `build`). Nothing is in the mod tree, the fixes
pak or a live install. Run ids used: ha hb hc hd he hf hn hs (earlier), hg1-hg3, hh1-hh9, hi1, hi2, hj1, hj2 (third agent), **hj3-hj14 (fourth agent)** -
hj15-hj25 (fifth agent), **hj26-hj44 (sixth agent)** - never reuse one; next free: `hj45`.

**FROZEN (coordinator, 2026-10-13): BAR family, StG 44 family, DP-28 and the pump shotgun are being integrated from this
folder at engine 4b73e8c5. Do NOT change their staged files, rows, tool output or README sections; a defect in one
goes to the coordinator by message.** `fps_anims_mg.txt` gained one ADDED row since (the irons aim pose), nothing else.

## FG 42 pair - hip reload, aimed reload, charging handle, armory entry (sixth agent, runs hj26-hj44)
Engine `ads-heavy-next` **aa84c42d** (= 24f21200 + `tools/apply_reloadfinish.py`) = test DLL **`cgame_heavy9`** (every figure below); bugs 3824-3832.
Overlay `SCRATCH/adsheavy/ov_f10.pk3` = `mkov_h.py` + `wire/patch_fg42irons_state.py --pk3`. Supersedes "What plays
today" and "How the player gets it" of the fifth agent's section below. BOTH guns (scoped FG 42, FG 42 Irons), all
8 finishes each = 16 tiks.
* **Server timing** (`tools/run_srvtime_h.py`, `evidence/srvtime_hj26.tsv` = released rows, `srvtime_hj39.tsv` = the
  staged tiks; `tools/rowlen_h.py` -> `evidence/rowlen_staged_vs_released.tsv`): identical before and after, both
  guns, hip / aimed, rounds left / emptied: magazine filled 1.35 s, the torso leaves the reload at 2.32-2.33 s, the
  weapon's own `reload` row (fg42.skc, 91 frames - WEAPON_RELOADING) reaches its last frame at 2.95 s. A trigger tap
  2.5 s into a reload fired nothing (hj28). Of the lane's 62 staged tiks: 249 server-read rows equal, 0 differ; the
  138 new rows (`reload_empty`, `reload_ads_empty`, `reload_ads_loaded`, `reload_end_loaded`) exist only for the cgame.
* **Charging handle** (`tools/fg42handle.py`, `fg42handle.json`): surface `coop_handle` (28 tris: a stem out of the
  painted slot's front end + an upright grip bar, shader `coop_fg42_sight`, worn faces at the texture's dark | edge
  seam - the full edge column was a WHITE bar in the engine) on a new bone `coop_chg` (child of `FG42`, 5.0 u back).
  `coop_fg42_irons.skd` = the irons mesh + the handle; **`coop_fg42.skd` = the RETAIL mesh + the handle** - the 8
  staged scoped tiks (`FG42.tik`, `fg42_<finish>.tik`; `tools/fg42rows.py`) point to it, nothing else of them differs
  from the mod tree except the rows below. Gun clip `models/weapons/fg42/coop_reload_empty.skc` (91 frames, handle
  back f66-70, let go, home f73).
* **Tik rows, all 16** (`fg42rows.py`): `reload` keeps its clip, its server commands and its length; its client block
  loses `30 sound fg42_snd_bolt` (rounds left = no handle work). New, cgame-only: `reload_empty` / `reload_ads_empty`
  (`coop_reload_empty.skc`, the bolt sound at frame 66) and `reload_ads_loaded` (`fg42.skc`). Sounds not listened to.
* **Technique** (`tools/fg42bake.py`, look tool `tools/fgview.py`): the LEFT hand leaves the handguard, cups the side
  magazine from below (the StG 44 magazine grip of the retail art turned 90 deg about the gun's long axis: palm
  under, thumb round the outer end, fingers hooked over the front edge + extra curl), draws it out to the left AT
  frame 20, pouch, back, home AT frame 40 (the server hides the gun's own magazine 0.66-1.32 s and shows the prop on
  the off-hand tag 0.67-1.34 s; the prop rides the wrist turned like the gun, a Kabsch fit puts it exactly in the
  gun's magazine while the hand holds the seated one). Rounds left: back to the handguard, 71 frames (2.34 s). EMPTY:
  the left hand is back on the handguard, the RIGHT hand leaves the pistol grip (the handle is on the firing side),
  hooks the bar with its own grip pose + the index closed, hauls it back, lets go - the spring runs it home - and
  drops away closed; 91 frames (3.0 s). Weight: gunphys class `fg42` (5.3 kg, the magazine's weight on the left;
  actions `fg_*`). AIMED: straight DOWN first, turned only under the box, an emptied gun stays down between the
  magazine and the handle (rolled 16 deg top-to-left for it), back the same way.
* **cgame** (`tools/apply_reloadfinish.py`, `coop_vmReloadFinish`, default 1): the torso leaves the reload at 2.33 s
  and the server sends idle / charge - a 91-frame hands row was CUT there (trace: 2.34 s). Now a RELOAD row named
  `coopr_*` or `fg42_reload*` that has more than 0.05 s left is played to its end before that idle / charge is taken
  (2.93 s measured, hj28 / hj37); fire, put-away, another weapon replace it at once; a row no longer than its torso
  reload is untouched. Display only. **A DECISION FOR THE COORDINATOR / USER** - without it the emptied reload must
  be cut to 2.33 s (handle work in 0.9 s).
* **Rows** (`stage_rows.py`, now built on the released rows file AS COMMITTED at 993f706 - the coordinator's
  integration rewrites the working copy while it runs, `--live` takes that): `fg42_reload` repointed,
  `fg42_reload_empty` (both guns, hip); `coopr_fg_42_irons_reload`, `_reload_empty`, `_reload_ads`,
  `_reload_empty_ads`, `_reload_adsb`, `_reload_empty_adsb` (irons only: the scoped gun's scope picture is not ours).
* **Centre box AS PLAYED, beyond the sway envelope** (`centrebox.json`; emptied: `BOXENG_CLIPLEN=190`, new - the anim
  id is the aim's again at 2.33 s while the row runs on): stand / crouch / prone / lean L / lean R / braced -
  rounds left (hj32) **0.23 / 0.21 / 0.31 / 0.04 / 0.12 / 0.05 %**; emptied (hj33) **1.64 / 1.76 / 1.75 / 0.99 /
  1.73 / 0.25 %** (peak at the release, clip frame 73); 0 frames over 2 %; every run back within 0.00 deg. The first
  bake read 3.8 % standing (canted while still high) and 5.9 % (the hand opening at the release): both fixed.
* **Reload while SCOPED** (scoped FG 42, hj36 / hj37, trace): NOTHING staged for it. The cgame starts the HIP row
  (`fg42_reload` 2.32 s / `fg42_reload_empty` 2.93 s, `ads=0`) and returns to `fg42_charge`; all 240 frames show the
  scope picture, swaying as the aim does - no hands, no gun. It follows the rifle lane's scoped sample.
* **Armory / unlock** - `wire/README.md` (`wire/stage_armory_fg42irons.py`: generator-based, the rifle lane's
  scratch-repo recipe): roster id 79, tile "FG 42 (IRON SIGHTS)" above the scoped FG 42 on the heavy tab, **rank 18**.
  Run hj34 / hj38 with the lock gate armed and the mod's own `xp_award`: rank 0 locked (padlock, "UNLOCK: Rank:
  Major General", click refused) -> one award under rank 18: locked -> the award: "Promoted: Major General", unlocked,
  the scoped FG 42 (rank 19) still locked -> picked -> the map again: spawns with it -> Winter after its challenge
  (150 snow-map kills by `chal_bump`): applied -> the map again: spawns with the Winter gun.
* **Looked at** (`evidence/fg42/`): the six-stance sheets `fg42irons_reload_aimed_roundsleft_stances_hj32.jpg`,
  `..._empty_stances_hj33.jpg`; crops `fg42irons_handle_and_magazine_crops_hj33.jpg` (white handle),
  `fg42irons_handle_crops_hj42.jpg` (toned); GIFs decoded and played back: `fg42irons_reload_aimed_roundsleft.gif`
  (hj41), `_aimed_empty.gif` (hj42), `fg42irons_reload_hip_roundsleft.gif` / `_hip_empty.gif`,
  `fg42_scoped_reload_hip_roundsleft.gif` / `_hip_empty.gif` (hj43); `fg42_both_guns_all_finishes_hip_hj44.jpg` (16
  tiks in the engine); `fg42irons_armory_tile_hj38.jpg`, `fg42irons_unlock_path_hj34_hj38.jpg`.
* **Weak points / not done**: while it is gripped the handle is hidden under the back of the firing hand (seen
  before and after; the BAR's weak point again); the left hand on the magazine shows its palm side and thumb, the
  four fingers are behind the magazine; emptied margins are thin (1.6-1.8 %); BRACED the work is at the frame's
  bottom edge, the handle hand is out of view; the hip reload plays in the lowest third of the screen; crouch + lean
  and break-offs (fire / sprint / switch during the reload) NOT run; third person not looked at (the torso row is
  unchanged: the left hand swaps the magazine, nobody cocks); sounds not listened to; that a LOCKED finish click is
  refused was not shown (the client cvar kept 6, the server's refusal is not logged); the armory's finish name line
  "FG 42 (IRON SIGHTS) (WOODLAND)" is 30 characters (the line clips near 27 - not looked at for the long names).

## Fifth agent, 2026-10-13: shotgun polish (supersedes the matching lines of "Shotgun reload" below)
Engine `ads-heavy-next` **4b73e8c5** = `cgame_heavy6` (the shotgun's; what the integration takes). Overlay of the shotgun runs: `SCRATCH/adsheavy/ov_k8.pk3`.
* **Break-off, round chambered: 0.38-0.40 s from the press to the shot** (was 1.18-1.23 s; runs hj15, hj19, hj20,
  `tools/brktime.py <run>` reads it from the log). `patch_sgbreak.py` STAGE 2 (still a PATCH; it upgrades a stage-1
  file): the state machine has no memory, so a reload that leaves the start state with a round in the gun runs
  copies of the loop pair (`RELOAD_SHOTGUN_SINGLE_CH` / `_CHECK_CONTINUE_CH`, same rows, same timing) whose break-off
  goes to `RELOAD_SHOTGUN_BREAK_QUICK`: torso row `shotgun_reload_break` (11 frames, `coop_tps_reload_break.skc`,
  added to `anims_shotgun.txt` by `stage_sgreload.py`; weapon anim `idle`, so no pump sound for others) and
  `viewmodelanim reload_end` sent TWICE. cgame (`apply_sgbreak.py`) sees the change counter step by two and plays
  `<row>_break` (+ `_ads`): rows `shotgun_reload_end_break` (hip, cut from the retail end) and
  `shotgun_reload_end_break_ads` (`sgbake.py` part `brk`), crossblend 0.12. No new anim id, fgame untouched. A reload
  that began EMPTY keeps the 1.2 s end with the pump. The uninterrupted reload is not retimed.
* **Hand and shell** (`sgbake.py`): the loop is RE-PHASED - it starts and ends at the pouch with the shell in the hand
  (`first attachmodel`; counted at frame 14 as before, removed at 15); show beat f5-8, gate f11, home f13. The start
  clip's hand is seen leaving the forend (f3-19). Pouch point `5,9,-10`. Carrying hand = closed pinch (`PIN`,
  `pinch()` finger_add; prop pinch point `8.6,2.4,-2.6`). Engine: hand out of view about 0.35 s before the first
  shell (was 0.6 s), shell in view 15 capture frames = 0.24 s per round (was about 0.1 s).
  Never pair `first removeattachedmodel` with `first attachmodel` of the same model: the prop is gone (bug-3756).
* **Centre box AS PLAYED, beyond the sway envelope** (`centrebox.json`): rounds left hj16 stand / crouch / prone /
  lean L / lean R / braced **0.45 / 0.12 / 0.36 / 0.40 / 0.29 / 0.51 %**; crouch + lean L / R (hj20) 0.37 / 0.28 %;
  emptied hj19 from the reload's start (`BOXENG_AFTER=64`) **0.17 / 0.04 / 0.10 / 0.40 / 0.41 / 0.53 %**; 0 frames
  over 2 %, every run back within 0.00 deg.
* **Looked at**: `evidence/shotgun_reload_aimed_roundsleft_stances_hj16.jpg`, `..._empty_stances_hj19.jpg` (incl. the
  first 51 frames in every stance: the last shot's kick, the hull, smoke - the gun is at its aim),
  `..._crouch_leans_hj20.jpg`, `shotgun_shell_pinch_crops_hj17.jpg`; GIFs rebuilt and decoded:
  `shotgun_reload_aimed_partial.gif` (hj16), `_full.gif` (hj19), `_breakoff_fire.gif` (hj20, 0.40 s),
  `shotgun_reload_hip_roundsleft.gif` (hj21: the retail hip loop now has the shell in the hand from its start).
  `shotgun_reload_hip_empty.gif` is still the fourth agent's (hj14).
* **Not done / weak**: third person only partly seen (`shotgun_reload_third_person_hj20.jpg`: `--tprel` camera cuts
  the body - try dist 40, height 8, side -12); the gun as a ground pickup NOT captured (`weapdrop` does nothing in the
  harness, bug-3759); at a break-off the shell in the hand vanishes at once and the hand sinks away in 3 frames;
  a killed player may keep a shell on the hand tag (no row removes it); the hip break row was not captured; sounds
  not listened to; the hip reload still swings the muzzle through the centre (left, coordinator's call).
* Coverage rows: `cov_h.py scan hj16 hj19 hj20`, `lowered` set, rule yes / yes / yes.
* New tools: `brktime.py`, `apply_sgbreak.py`, `moveruns.py`, `run_h.py --tprel / --ground`.
* **Disk**: G: ran full (bug-3758). Nobody deletes. Finished, written-up runs are MOVED to the archive disk:
  `python tools/moveruns.py <id,id,...>` -> `H:\hzm_archive\heavy\<id>` (verified copy, then the source removed;
  run it in the background, H: is slow). Live captures stay on `G:\mohaa-adsanim4\runs`. The coordinator moved
  ha1..hj14 to H: as well. A six-stance run with a tail is 1.3-2 GB; a stills run of 8 guns 0.2 GB.

## FG 42 Irons - a NEW weapon (fifth agent, runs hj22-hj25; user 2026-10-13) - look test delivered and accepted
Engine `ads-heavy-next` **24f21200** = `cgame_heavy8` (`cgame_heavy7` = the same without the trace). Overlay:
`SCRATCH/adsheavy/ov_f5.pk3` = `mkov_h.py` + `wire/patch_fg42irons_state.py --pk3` (the state row, see below).
The rifle lane's G 43 Irons recipe (`..\rifles\README.md`), its helpers imported as a library.
* **Mesh** `assets/models/weapons/fg42/coop_fg42_irons.skd` (`tools/fg42irons.py`; `tools/fg42parts.py` lists the
  retail components): the retail `fg42.skd` (SKMD v5, 4 stray bytes after ofsEnd - dropped, bug-3770) had NO rear sight
  under the scope and a front slab with a stud facing the eye. Out (triangles only): scope tube 76, turret / ring /
  mount 96, its foot 26, the lens surface, the front slab 46. In, surface `coop_sight` (218 tris, shader
  `coop_fg42_sight`, `scripts/coop_fg42_sight.shader`, `textures/coop_wpn/fg42_sight.tga` = the G43 sheet at 0.52 /
  0.66 - it read mid-grey on this gun): REAR aperture ring outer r 0.46 / hole r 0.21 u, 0.22 u thick, a worn band
  round the rim, on a stalk with a range drum and a foot at x -6.2 on the receiver's rear tube; FRONT post 0.38 u wide
  at the tip with a worn-bright band across its top (coordinator's note: the 0.26 u post was lost on dark foliage)
  on a hinge block on the retail foot. Sight line 0.10 deg to the bore axis, sight radius 33 u.
* **Tiks** (`tools/fg42tik.py`): `coop_fg42_irons.tik` + gold, chrome, blued, bloody, camo_woodland, camo_winter,
  camo_desert = EVERY finish the scoped FG 42 has; name "FG 42 Irons" (+ " (Gold)" ...), rank 231, no zoom, the
  BAR's accuracy and movement rows read from the mod tree's bar.tik (coordinator: the BAR's - settled); damage, fire
  delay, 20 rounds, sounds, reload the FG 42's own. The sights are dark steel on every finish (sheet below).
* **Sight row** `sights_override.json` key `fg42_irons` (`"new": true`): F 26.77 -0.855 -5.50, R -6.2 -0.855 -5.44,
  relief 12. `tools/apply_fg42irons.py <worktree>` writes the 8 rows and the three cgame edits (name -> the fg42
  hands prefix; aim tune donor StG 44; the per-weapon row override also covers `charge`). `hv.lib()` registers a
  `new` key for the offline tools (gun entry `fg42irons` in `hv.GUNS`).
* **Aim pose** `viewmodel/fg42/coop_fg42_irons_aim.skc` (`tools/fg42pose.py`, row `coopr_fg_42_irons_charge` in
  `stage_rows.py`): the StG 44 aim pose (the gun's seat in the firing hand is identical to the FG 42 hip idle's),
  both arms 5 u further out, the support hand = the hip idle's grip turned 40 deg about the gun through the
  handguard and 0.4 u lower: palm on the handguard's left flank, fingers under (the plain hip grip put four fingers
  large right of the rear sight, bug-3771). The scoped FG 42 has no aim pose and is untouched.
* **Looked at** (`evidence/fg42irons/`): `fg42irons_mesh_side_before_after.jpg`; `fg42irons_hip_aim_hj23.jpg` (hip,
  aim light / dark, crouch, prone, lean left); `fg42irons_aim_enlarged_hj25.jpg` (the thicker post: light wall, dark,
  Winter; `_hj23` = the thin post, superseded); `fg42irons_finishes_hip_aim_hj23.jpg` (base + 7 finishes, hip + aim);
  `fg42irons_third_person_hj23.jpg`; `fg42_reloads_today_hj24.jpg`.
* **Weak points seen**: the side magazine is a long dark slab left of the sight just under the centre box; the stock
  fills the bottom centre; a little of the firing hand shows right of the receiver under the box (coordinator: tuck
  it if cheap - it is not: `fixed_right` keeps the firing arm, it needs its own finger pose); the third-person
  stills show the gun small; the hip stills of hj23 were not re-taken with the thicker post.
* **What plays today** (run hj24, `--set "set coop_vmTrace 1"`, `apply_vmtrace.py`, bug-3773): SCOPED FG 42, reload
  with the scope up: the cgame starts the HIP row `fg42_reload` for 2.32 s and goes back to `fg42_charge`; all 200
  frames show the unchanged scope picture - no hands, no gun, the picture does not move. The gun's `reload` row has
  `entry sound fg42_snd_reload`; not listened to. FG 42 IRONS aimed: the same hip row (no `_ads` row yet) - the gun
  drops to the hip clip, an OPEN left hand comes up mid-screen, back at the aim after 2.3 s. HIP reload (both guns,
  DaRKaNGeL's clip): the left hand paws at the magazine with open fingers - it has to be rebuilt to the rule.
* **State row** (bug-3772): `coop_mod/player_Torso.st` picks the reload's torso row by the exact name "FG 42";
  `wire/patch_fg42irons_state.py <tree>` adds the row for "FG 42 Irons" (a PATCH; `--pk3 in out` patches a test
  overlay - the lane's staged state file is the shotgun's and is frozen). Run hj24 with it: the hip reload plays.
* **How the player gets it** - `wire/README.md`: own armory entry (roster id 79 proposed, tab heavy), **unlock at rank
  18** (the scoped FG 42 is rank 19; rank 18 unlocks nothing today), the 7 finishes under the new base tik, recoil
  rows staged (`wire/recoil_table_fg42irons.txt`). The generator patch script is NOT written: the coordinator said to
  wait for the rifle lane's generator-based recipe in `..\rifles\wire\README.md`, then follow it. How the scoped FG
  42's finishes unlock was not found (`challenges.scr` has no "fg42" text).

## NEXT, in the coordinator's order (items 1-4 of the fifth agent's list are DONE - the FG 42 section above)
A deploy of the integrated build replaced the game paks the harness reads (2026-10-13 about 11:00): REBUILD the
overlay before the next run (`stage_rows.py`, `mkov_h.py`, `wire/patch_fg42irons_state.py --pk3`); the frozen guns'
released baseline is the integrated version from then on (`stage_rows.py` PIN may have to move to the new commit).
1. FG 42 leftovers: break-offs, crouch + leans, third person, the scoped reload once the rifle lane's sample exists.
2. Belt-feds, in this order: M1919 .30 cal portable (the aim shows a black receiver wall and the reload swings the
   barrel through the box, bug-3622; sight row via `sights_override.json` first), MG42 portable, Breda,
   Vickers-Berthier (top magazine as the DP-28 - reuse that recipe), Lewis Gun (`bar_bar1918.tik`, pan): top cover
   opened, belt laid in, cover closed, charging handle worked - visibly on the model; the gun down under the box and
   back to the exact aim; the same server-timing check per gun (`run_srvtime_h.py ov ... --ammo mg`). The M1919,
   the MG42 and the Lewis play the BAR's hands prefix: their own rows are `coopr_<weapon key>_reload...`.
   A new mechanism part = `fg42handle.py`'s recipe (a surface on a new bone, `add_bead.add_surface` then
   `split_bone.split`); a hands row longer than the torso reload needs its name in `apply_reloadfinish.py`'s opt-in.
   **M1919 - what is there today (read from the files 2026-10-13, NOTHING staged, nothing run):**
   * `30calportable.tik` (name "M1919 30cal", weapontype mg, clipsize 120): surfaces `weapon`, `weapon1`, `belt`; the
     reload audit of 2026-10-05 already gave it a gun clip `coop_30cal_reload.skc` (98 frames, 3.27 s) with a `cover`
     bone (open f16-69, 74 deg) and a `chandle` bone (pulled f75-86), `belt` hidden f34-56; hands row
     `coopr_m1919_30cal_reload` -> `viewmodel/coop_reload/m1919_reload.skc` (97 frames, 3.2 s; MG42 and Lewis have
     the same kind of row - they are in the mod tree's `anims_shared.txt`, not in `fps_anims_mg.txt`); torso row
     `coop_reload_m1919` (`tps_reload_bar.skc`, 98 frames 3.27 s: belt prop `coop_belt_30cal.tik` on the off-hand tag
     frames 32-58, `clip_fill` at 72). So the HIP reload already opens the cover, lays the belt, closes it and works
     the handle (offline sheet `fgview.py ... --hip --sight m1919 --pose viewmodel/mg/barpose.skc --tik
     models/weapons/30calportable.tik --prop models/ammo/coop_belt_30cal.tik:32:58 --hide belt:34:56`): the open
     cover stands straight up through the middle of the screen.
   * AIM: the cgame's `cg_adssights.h` has NO row for it (the shared `sights.json` key `m1919` is a synthetic line at
     z +1.49, UNDER the receiver, `verified` false) - that is the black receiver wall of bug-3622. The mesh HAS a rear
     leaf: a frame of two uprights (x -0.55, y -0.51..-0.24 and 0.23..0.50, z -8.7..-6.4) with a 0.48 u window, on a
     base block (x -1.0..2.6, z -6.9..-1.5); it has NO front sight; receiver top z -4.9, front block x 15.95..17.52
     top z -5.02. Proposed (the FG 42 Irons recipe: `fg42irons.py` for the surface, `apply_fg42irons.py` for the new
     cgame rows, `sights_override.json` `"new": true`): a notch slider across the leaf's window (top z -7.9) and a
     front blade on the front block (x 16.6..17.3, tip z -7.9, 0.24 u wide) as surface `coop_sight` on the weapon
     bone of a new `coop_30cal_sights.skd`; row F (16.95, 0, -7.9) R (-0.55, 0, -7.9), relief about 10; its own aim
     pose row `coopr_m1919_30cal_charge` (the gun has a pistol grip and no stock).
   * AIMED RELOAD: the open cover is 12 u tall - under the box it only fits with the gun far down or rolled on its
     side. The cheap, honest recipe is hold_bake's `gun_abs` = the HIP clip's own gun place (one choreography serves
     hip and aim: down to the hip work pose, the audit clip's hands, back to the exact aim), row
     `coopr_m1919_30cal_reload_ads`; the hands of the audit clip must be LOOKED AT first (open hands?). The row is
     3.2 s against a 3.27 s torso reload: no `apply_reloadfinish.py` needed. Ammo type for the timing probe: check
     the tik (`--ammo mg`).
3. Leftovers: BAR A1 / A2 tiks run; BAR and DP-28 return to aim with more weight inside the server's reload time; BAR
   hip reload; the BAR skin lift for its other finish sheets (new files only) - those guns are FROZEN: new files only.
4. Shotgun leftovers that need a way round the harness: the hip break row capture, the ground pickup look, a
   third-person camera that shows the reload (bug-3759).

## State (third agent, runs hg / hh / hi / hj1-hj2; engine: cgame_heavy2 for every reload figure, cgame_heavy3 = + the shotgun row)
| item | state |
|---|---|
| 1 measurement AS PLAYED (sway + breath on) | **done** - `boxeng.py --sway` (the SMG lane's reloadbox code as a library) + `run_h.py --tail 360:4`; bug-3620 answered: a measuring artefact (bug-3667) |
| BAR, aimed, rounds left + emptied, six stances | **done**, re-read with sway on (table below) |
| BAR other meshes (M1918 Classic / A1 / A2, Pacific): emptied row (bug-3623) | **done** - they carry the same `bolt` bone; rows staged, run hh4 (bug-3670) |
| BAR / StG 44 break-offs (fire, sprint, switch, aim dropped) | **run and looked at** (hh3, hh5) |
| StG 44, aimed, six stances | **done**, re-read with sway on; the "left lean on the bar" was the tool's skip rule (bug-3668) |
| StG 44 hip reload: no cocking with rounds left | **done** (hh5, bug-3672) |
| StG 44 finishes | gold run and looked at (hh6); **there is no scoped StG 44 tik in the mod** (bug-3674) |
| hand on the handle (BAR, StG 44) | re-posed: wrist from below, fingers and knuckles readable (bug-3671); the knob is still hidden while gripped |
| FG 42 | **scoped weapon, no iron-sight aim** (bug-3673; coordinator confirmed). Reload while scoped today: the scope picture stays, no viewmodel (hh9). Its HIP reload on the model is **not started** |
| DP-28, aimed, rounds left + emptied, six stances + braced rows | **done to the three rules** (hi1 / hi2), weak points listed below |
| shotgun sight | **DONE (fourth agent, runs hj3-hj5, bug-3696 / 3697)**: brass bead r 0.27 u (surface `coop_bead`) + the receiver's matted sighting groove (surface `coop_groove`), row delta 30 mrad + relief 14.11 u on `ads-heavy-next` 5e351620 (`cgame_heavy4`). `evidence/shotgun_aim_before_after_hj5.jpg`; see "Shotgun sight" below |
| shotgun reload, aimed (rounds left + emptied, six stances) | **done to the three rules (fourth agent, runs hj9-hj12)** - see "Shotgun reload"; weak points listed there |
| shotgun: the pump only when the gun was empty | **done** - cgame `ads-heavy-next` 0cef28a7 (`cgame_heavy5`, `tools/apply_sgpump.py`), aimed and hip (bug-3729) |
| shotgun: firing breaks off the reload | **done** - `tools/patch_sgbreak.py` (state file PATCH, stage 1 + 2): round chambered 0.40 s to the shot, gun was empty 1.2 s with the pump (bug-3728, bug-3755) |
| shotgun hip reload | checked: shells one by one (retail), no pump with rounds left (hj13), pump when emptied (hj14); NOT rebuilt - the retail hip clip swings the muzzle up through the centre of the screen, as before |
| belt-feds (M1919 portable, Breda, Vickers, MG42), FG 42 hip reload, BAR A1 / A2 run, BAR / DP-28 heavier return, BAR hip reload | **not started** |

### Centre box AS PLAYED (cg_adsSway 0.1, cg_weaponBreath 1 = the runner's defaults), `centrebox.json`
`xmax` = share of the box covered beyond the settled aim's SWAY ENVELOPE (everything the settled aim covers during one
whole sway period after the reload, grown 6 px); `mask6` = against the six-frame aim mask (the SMG lane's figure);
`alone` = the settled aim ALONE against that mask (what the aim does by itself). Emptied guns: the first 20-35 capture
frames are the last shot's kick and smoke; `after 40` = the maximum after 0.64 s.

| gun, run | stand / crouch / prone / lean L / lean R / braced, % beyond the envelope | emptied: after 40 frames | settled aim alone vs its own six-frame mask |
|---|---|---|---|
| BAR rounds left, hg1 | 0.04 / 0.00 / 0.00 / 0.05 / 0.04 / 0.03 | - | 6.8 / 7.6 / 5.6 / 10.1 / 6.1 / 0.1 |
| BAR emptied, hh1 (new grip) | 0.11 / 0.18 / 0.15 / 0.05 / 1.10 / 1.87 | 0.00 / 0.01 / 0.03 / 0.05 / 0.06 / 0.43 | 6.2 / 6.9 / 7.2 / 4.5 / 6.8 / 0.1 |
| StG 44 rounds left, hg1 | 0.09 / 0.20 / 0.13 / 0.17 / 0.09 / 0.08 | - | 0.8 / 1.1 / 0.3 / 0.5 / 0.4 / 0.0 |
| StG 44 emptied, hh2 (new grip) | 0.35 / 0.56 / 1.23 / 0.42 / 0.08 / 1.95 | 0.04 / 0.06 / 0.05 / 0.11 / 0.08 / 0.28 | 0.3 / 0.1 / 0.9 / 0.5 / 0.6 / 0.0 |
| DP-28 rounds left, hi1 | 0.00 / 0.00 / 0.00 / 0.07 / 0.04 / 0.01 | - | 5.7 / 4.2 / 3.2 / 7.3 / 5.0 / 0.6 |
| DP-28 emptied, hi2 | 1.17 / 0.31 / 0.27 / 0.19 / 0.03 / 0.30 | 0.01 / 0.04 / 0.04 / 0.05 / 0.03 / 0.04 | 3.1 / 2.7 / 5.5 / 1.6 / 5.3 / 0.0 |

0 frames over 2 % in every row; every clip ends within 0.00 deg of the aim. **Read with care:** the figures of 1-2 % on
emptied guns are the last shot (kick at capture f24-26, smoke of 20-30 rounds over the dark door) - looked at with
`tools/swayshow.py` (run hg3), the model is out of the box by capture frame 18. Against the six-frame mask the BAR
and the DP-28 read 2-6 % in the free stances for the same reason their settled aim does: **the aim of a gun whose rear
is 6-8 u from the eye wanders 15-25 px with the sway** (bug-3669: BAR 4-10 %, DP-28 3-7 % by itself; StG 44 under
1.2 %). That is the aim, not the reload - a decision for the user (relief / taller sights / less sway near the eye).
bug-3620 (the BAR's "2-3 % for 16 frames at the return", run hd2) was exactly this (bug-3667).

### What was done to the two finished guns
* Hand on the handle: `hk_off (0.2, 1.0, -3.8)` - the wrist comes up from below, the eye looks down on knuckles and
  fingers closed round the knob (`evidence/bar_handle_engine_crops_hh3.jpg`, `mp44_handle_engine_crops_hh5.jpg`).
  About a fifth of the screen wide on the StG 44, still about a quarter on the BAR at full pull. The loaded clips are
  byte-identical to the previous agent's (0e1d9d7d, 72239c8c, 33486b6d, 80d8c375); empty: BAR 260f44d6 / 1095f963
  (braced), StG 44 cdc28061 / 2c4ec8e8.
* BAR other meshes: `patch_tik_h.py bar` `more_paths` = `models/weapons/BAR` (retail mesh: 36 vertices of `bar3` on
  the `bolt` bone, the knob 0.7 u higher than the S93's) + `models/weapons/coop_pabar`; 12 tiks. Not confirmed by eye:
  the retail knob's travel (the hand covers it). `bar_bar1918.tik` is the Lewis gun - untouched.
* StG 44 hip: `heavybake.py mp44 --hip` -> `coop_mp44_reload_hip.skc` (row `mp44_reload`), tik `reload` = handle-still
  clip + cut sound, `reload_empty` = retail clip + retail sound (`patch_tik_h` `hip=True`). Other players hear the cut
  sound for every reload. Not listened to.
* Break-offs, both guns alike (`run_h.py --brk`, the SMG lane's `sbreak`; `evidence/*_breakoffs_*.jpg`): trigger and
  sprint do nothing, the reload runs to its end in the aim; next weapon: the gun goes down at once, nothing left
  behind; aim let go: the framing goes to the hip in 0.7 s while the row hands over to the hip clip, ends as the hip
  clip does. Rounds left only, 0.8 s and 1.7 s into the reload; looked at on sheets, not as GIFs.
* Still open on these two: the BAR's return from the work pose takes 0.2 s (brisk for 9 kg); hip reload of the BAR
  untouched; Lewis / MG42 keep their hip clips while aiming.

## DP-28 - `tools/heavybake.py dp28` (+ `--braced`), `tools/patch_tik_h.py dp28`
Facts (`heavylib.py dp28`, `clipinfo.py`, `gunmove.py`): at the aim the pan (8.4 u across) lies 8-17 u from the eye,
1-3 deg under the sight line - it is the lower half of the aim's own picture (the aim covers 36 % of the box). The
pack's hip clip: the LEFT hand does everything - on the pan f24-28, away f32-40, seated f44-48, pressed f52-60, then
the same hand hauls the knob, which on THIS mesh is on the LEFT (surface `Cylinder2`, bone `rechamb`, 2.7 u) and sits
UNDER the pan, 2.6 u inboard of its rim. **In this mod the DP-28 holds 20 rounds** (`clipsize 20`).
* `feed='top'` in the gun entry: the magazine keys of `spec()` with the well's axis turned round (lift, press), pan
  physics `lg_pan_*`, class `dp` (11.5 kg, a quarter of it the pan).
* The server shows the pan prop on the off-hand tag f29-45 and hides the gun's own for exactly those frames: the lift
  starts AT f29, the new pan is down AT f45 - the swap is 0.5 s, the server's window (torso state, mod tree).
* Work pose 2.6 u down, 14 deg cant (3.6 u put the pan on the frame's bottom edge in the engine, run hh7 - the
  engine's gun rides lower than `eyeview.py` shows). EMPTY: a second pose `hcant` (1.5 u down) for the pull, the hand
  goes in under the pan's left rim FROM THE SIDE (`hk_off (0.0, 3.6, -1.0)`; from below the fingers came up through
  the pan) and hauls the knob, released; keyed to the BAR sound the gun plays (handle f66-73 - the pack's own pull was
  0.25 s late against it). Rounds left = open bolt held by the sear: no handle work, gun clip
  `coop_reload_ads_loaded.skc` + the cut BAR sound (tik rows `reload_ads_loaded` / `reload_ads_empty`, 8 tiks).
* Rows: `dp28_reload_ads` (same path as the SHIPPED clip - replaced), `dp28_reload_empty` (pack hip clip),
  `dp28_reload_empty_ads`, `dp28_reload_adsb`, `dp28_reload_empty_adsb`. Clips: loaded 11b8861d, empty 8d91082a,
  braced a45e0877 / 36f01ecc; gun clips 1012388b / 95da2b8e. Offline box 0.0 % (the prop is not in that figure).
Evidence: `evidence/dp28_reload_aimed_loaded.gif` (hi1), `dp28_reload_aimed_empty.gif` (hi2) - decoded and
looked at every fourth frame at small size (no pop seen), NOT stepped frame by frame;
`dp28_reload_aimed_empty_stances_hi2.jpg` (six stances: pan away, new pan in, pan on for the pull - looked at);
`dp28_pan_and_handle_engine_crops_hi2.jpg` (looked at). **Weak points:** the knob and most of the hand are hidden under the pan during the pull
(a pale shape under the left rim); the pan is out of the gun for 0.5 s; the return takes 0.3-0.4 s; the brief says
"charging handle on the right" - the real gun's is, this mesh has it on the left and the pack's hip clip works it with
the left hand, which is what was reproduced. Break-offs and the hip reload not run.

## Shotgun sight - `tools/stage_sgsight.py` (supersedes stage_bead.py), `sights_override.json`, `tools/sgaim.py`, `tools/sgsheet.py`
What was wrong (bug-3697): the aim pose has the eye 10.1 u behind the virtual rear point = OVER the receiver's rear end
(a 1.8 u wide receiver 2-3 u from the eye is a wall); the retail roof is a peaked ridge with a mirrored soft texture;
the bead was 6 px and UNLIT - `rgbGen lightingDiffuse` draws black on a model in this engine, every model shader of
the mod uses `lightingSpherical` (bug-3696).
* Row (`sights_override.json` -> `sightrow_h.py`): relief 14.11 u = the rig's +4 u clamp (more needs a new aim clip:
  offline +6 looked a little better still, +10 brings the firing hand and forearm large into the bottom of the frame),
  delta 30 mrad (the whole barrel top shows between receiver and bead; bullets go to the bead's foot = screen centre).
* Mesh (ONE skd, 14 tiks): bead r 0.27 u, 68 % proud, 14 x 8 sphere = 10-12 px at 1280 wide (16-18 px at 1080p).
  Groove: the ridge vertices of the receiver roof exist once per roof side in the retail mesh, so they SLIDE down their
  own roof edge to two rails (+-0.20 u; position and UV stay on the edge, the roof keeps its shape) and a new surface
  closes the gap: chamfers, floor (+-0.11 u, 0.10 u deep), front end plate; zero width at the rear station. No old
  triangle is re-indexed; the new surfaces collapse away at low detail. Own textures (written by the tool): brass with
  the glint painted in, groove with bright worn rails and a cross-matted floor.
* `python ../tools/stage_sgsight.py` from `assets/` WITHOUT `IRONSIGHT_EXTRA_PAKS` (it reads the retail skd); it
  rewrites the two `surface ...` lines in an already staged tik and keeps that tik's other edits.
* Offline design tool: `IRONSIGHT_EXTRA_PAKS=<pk3> python ../tools/sgaim.py out.jpg --v delta:relief_move ...`
  (matches the engine picture). Engine: `run_h.py ... --parts stills --wallstill stand,crouch,prone --tpc`
  (`--wallstill` = stills on the light wall, tag `<st>W`; `--tpc` = third person close; guns `sggold sgcamo sgchrome`).
* Looked at (hj4 / hj5): light wall stand / crouch / prone, dark foliage in seven stances, third person aimed (the bead
  shows, same skd as the view model - there is no other shotgun mesh), gold / winter camo / chrome finishes.
  NOT done: the gun lying on the ground as a pickup (same skd, not captured); the groove from close up in third person.
* Weak points, say them: the receiver is still about a fifth of the screen wide at its near end (it is 4 u from the
  eye); the stock wrist under it shows the retail texture's mirror seam; on the gold finish the brass bead is gold on
  gold (reads against the backdrop, not against the gun); the groove stays blued steel on every finish.

## Shotgun reload - `tools/sgbake.py`, `tools/stage_sgreload.py`, `tools/patch_sgbreak.py`, `tools/apply_sgpump.py`
What the shipped aimed clips did (run hj6): the gun stayed on the sights, the hand went under it and NOTHING was seen -
the M1897's gate is under the receiver, and no shell prop existed. Staged now (all in `assets/`, engine on the branch):
* **Clips** (`sgbake.py`; hold_bake through the pistol lane's `revbake.py` as a library; the three aimed rows keep their
  SHIPPED paths, the staged files replace them): start 23 frames, one shell 20 frames (seamless loop), end 32 frames in
  two versions. The gun PITCHES DOWN ABOUT THE BUTT 4.6 deg (the muzzle goes under the centre box, the receiver stays
  in the frame), cants 20 deg, 3 u out along the view. The support hand goes down to the pouch and brings every shell
  up beside the receiver's left flank IN VIEW (the "show" beat), rolls it under to the gate (the retail hand-to-gun
  relation, `rel`) and thumbs it forward; the gun takes each shell (gunphys class `shotgun` 3.6 kg, actions
  `sg_shell_gate` / `sg_shell_home`, 0.6 deg). End, gun WAS EMPTY (`shotgun_reload_end_ads`): hand to the forend, the
  pump under the box with the gun's own slide (retail timing: back f10-11, forward f20-21; `sg_pump_back` / `_fwd`),
  then up into the aim. End, rounds were left (`shotgun_reload_end_loaded_ads`): hand to the forend, up, no pump.
  Clips: start 627e9043, single (SG_SEAT 3) see `sgbake.py` output, end 73ecf09b, loaded end c9b6f74f.
* **Why not turn the gate to the eye**: a straight drop that clears the box takes the receiver out of the bottom of the
  frame; a roll of 95 deg (the real "inverted" load), and already 30-40 deg, throws the firing arm's elbow up through
  the view (the firing hand keeps the grip). Tried offline (`sgtry.py`), bug-3732.
* **Shell prop + count** (`stage_sgreload.py` -> `models/player/base/anims_shotgun.txt` = retail pak3 + edits):
  `models/ammo/shotgunshell.tik` on the support hand's tag, loop frames 7-15; the shell is COUNTED AT FRAME 14 (retail:
  frame 5, hand still at the pouch) - a loop broken off before that no longer keeps its shell (GAMEPLAY, bug-3730);
  the end row removes a shell left in the hand. Tik row `reload_end_loaded coop_shotgun_still32.skc` in the 14 tiks.
* **Pump only when empty** (`apply_sgpump.py`, cgame): the clip count is remembered when the `reload` row is chosen;
  rounds were left -> hands `<row>_loaded` (+ `_ads`), gun `reload_end_loaded` (still clip, no pump sound). Display
  only. Other players still see / hear the server's `reload_end` (the pump) - not changed. Hip: the retail end with the
  pump frames cut (`sgbake.py --hipend`, row `shotgun_reload_end_loaded`).
* **Fire breaks the reload off** (`patch_sgbreak.py <tree>`): the retail early-out waited for the weapon's reload latch
  and lost early presses; now start / loop -> `RELOAD_SHOTGUN_BREAK_END` (end row, `donereloading`) ->
  `RELOAD_SHOTGUN_BREAK_FIRE` -> the owed shot. `assets/coop_mod/player_Torso.st` is the PISTOL lane's staged file +
  this patch, for the test overlay only: the state file is shared - **apply the patch to the final tree, do not copy
  the file**. From press to shot: 1.18 s (the end row; with the pump when the gun was empty).
* Stage order: `stage_sgsight.py`, `sgbake.py --hipend` (needs `IRONSIGHT_EXTRA_PAKS=<pk3 with the staged mesh>`, e.g.
  `SCRATCH/adsheavy/sg_p2.pk3` from `sgpak.py`), `stage_sgreload.py` and `stage_rows.py` (both WITHOUT the overlay
  variable), `patch_sgbreak.py assets` on a fresh copy of the state file, `mkov_h.py`.

### Centre box AS PLAYED (sway + breath on), beyond the settled aim's sway envelope, `centrebox.json`
| run | stand / crouch / prone / lean L / lean R / braced, % | frames over 2 % | back to |
|---|---|---|---|
| rounds left (2 shells), hj12 | 0.46 / 0.18 / 0.32 / 0.72 / 0.53 / 0.93 | 0 | 0.00 deg |
| emptied (5 shells + pump), hj11, from the reload's start (`BOXENG_AFTER=64`) | 0.19 / 0.07 / 0.01 / 0.46 / 0.62 / 0.16 | 0 | 0.00 deg |
The emptied capture's first 51 frames read 20-30 %: the last shot's kick, a second of smoke and the pellet marks; the
reload starts 74 frames after the shot (prone: 13 - its fire state is shorter). Offline (`offbox.py` through
`hv.lib()`): 0.0 / 0.0 / 0.0 / 0.9 %. The sight line leaves 7.6 deg and is back within 0.00 deg.
Harness: a pump gun needs `--shotgap 85` (presses under 1.4 s apart are lost) and fires once on a held trigger -
`--sthip` = the stdemo capture from the hip, press by press (bug-3731).

Evidence: `evidence/shotgun_reload_aimed_partial.gif` (hj12), `shotgun_reload_aimed_full.gif` (hj11),
`shotgun_reload_aimed_breakoff_fire.gif` (hj14), `shotgun_reload_hip_roundsleft.gif` (hj13),
`shotgun_reload_hip_empty.gif` (hj14), `shotgun_reload_aimed_empty_stances_hj11.jpg`. Decoded and looked at: the
break-off GIF, the full GIF round the first shell and the pump, both hip ends (small); the partial GIF and the stance
sheet as sheets. NOT stepped frame by frame.
**Weak points, say them:** the shell is in view for about 0.1-0.15 s per round (two GIF frames) - the loop is 0.67 s
and the hand goes to the pouch each time; the gate itself is never seen (the shell goes in under the receiver); the
shown hand has its forefinger out along the shell (the forend grip's fingers), the shell sits beside it rather than
in a closed pinch; nothing happens in view for 0.6 s between the gun coming down and the first shell; the pump under
the box is small in the picture; braced uses the same clips (no `_adsb` row); prone reload starts 1 s sooner after the
last shot than the other stances (state timing, not looked into); a break-off costs 1.18 s before the owed shot; the
sounds were not listened to; second-client / third-person view of the shell prop not captured; coverage rows not
updated (`cov_h.py scan` reads "not ok" because the sight line leaves by design - needs the `lowered` flag).

## FG 42 - what the still shows
`evidence/mp44_gold_and_fg42_aim_hh6_hh9.jpg`: top row the gold StG 44's emptied aimed reload (same mesh, plays the
new clips); bottom row the FG 42 with the aim key held, sway on - **the scope picture** (`zoom 20`, lens surface; the
scopes system draws it), through 20 rounds and the whole reload: the scope stays up, no viewmodel is drawn, the reload
passes unseen. Nothing was staged for an iron-sight aim. To do: its HIP reload on the model (the mesh is one static
surface set on one bone - a charging handle needs its own bone first, as the SMG lane added one to the MP40); the
reload-while-scoped design follows the rifle lane's sample. Fourth agent: the hh9 LOG cannot say whether a reload
played - the ADSFRAME probe (clip / anim) prints nothing while the FG 42's scope is up (56 lines, all before the gun
was given); the 245 frames show the unchanged scope picture from the first to the last. Needs a run with a clip trace.

## Engine branch `ads-heavy-next` (this lane's cgame)
* ef1e7934: a braced aimed reload / bolt picks the hands row `<row>_adsb` when fps_anims has it (`CG_CoopBrace() > 0.5`,
  the recipe of `../../ads_bolt_2026-10-04/engine/apply_adsbrace.py`); no row = `<row>_ads` as before.
* 01e2460b: merge of ads-next 191f1879 (ADSSETTLE diagnostic, `cg_adsRigSettle`, default off - no behaviour change).
* 89c08278 / 5e351620: the 14 shotgun sight rows (`sightrow_h.py`): delta 30 mrad, relief 14.11 u. Ships only with the
  staged shotgun mesh.
* 0cef28a7: the pump only when the gun was empty (`apply_sgpump.py`): `CG_CoopReloadFromEmpty()`, hands `<row>_loaded`
  for the end row, gun `reload_end_loaded`. No row = as before, so every other gun is untouched.
* Test DLLs in `G:\mohaa-adsanim4\cgames`: `cgame_heavy1` (ef1e7934), `cgame_heavy2` (01e2460b: every BAR / StG 44 /
  DP-28 figure), `cgame_heavy3` (89c08278), `cgame_heavy4` (5e351620: shotgun sight), **`cgame_heavy5` (0cef28a7,
  current: shotgun reload)**. Build: `cmake --build .cmake --config Release --target cgame` in the worktree.

## How this lane runs (all tools in `tools/`, run from `assets/` unless said)
* `hv.py` paths + guns; `hv.lib()` = hold_bake / rig / vmcam. Shared tools that need the runs folder: `ADS_RUNS=G:/mohaa-adsanim4/runs`
  (or `python tools/sh.py <tool> ...`).
* Engine runs: `python tools/run_h.py <id> --overlay <abs pk3> --cgame cgame_heavy2 --guns bar --parts ...` (the shared
  run_2h.py repointed to `G:\mohaa-adsanim4`, owner `adsanim4`, port 12598). Lane extras: `--map`, `--spot`, `--pitch 8.5`
  (20 rounds of automatic fire walk the view up 8.5 deg), and **`--stdemo stand,crouch,prone,standL,standR,braced`** =
  the aimed reload in each stance as a DENSE capture on the light wall (`--demoyaw 165`) that `boxeng.py` can measure
  (`--parts none --stdemo ...`; with `--demoempty --shots 20 --shotgap 8 --demoreload 240` the gun is emptied first,
  without it `--shots 1 --demoreload 240` and 200 frames pass before the reload so the recoil is out).
  A session is 2-4 min; log `SCRATCH/adsheavy/run.log`, frames `G:/mohaa-adsanim4/runs/<id>/`.
* **Box numbers AS PLAYED: `run_h.py ... --tail 360:4` (sway on, the runner's default) and `boxeng.py <id> <gun> --sway [--empty] [--cbx]`.**
  The earlier sway-off measure (`--set "set cg_adsSway 0" --set "set cg_weaponBreath 0"`, `boxeng.py --align 6`, bug-3619) stays for old runs: with sway / breath on the AIM itself wanders 15-45 px during a 4 s reload and reads 3-7 % by itself;
  braced / prone views sit up to 6 px off the reference (over 20 bullet holes that read 4-6 % with no model in the box).
  `--cbx [--empty] [--add]` writes `centrebox.json` in the shared coverage.py schema (an emptied gun: the first 20
  capture frames are the last shot's kick). Measure on the DARK skin (`mkov_h.py out.pk3 --skip textures`): the lifted
  BAR on the brown door is under-detected. LOOK at the lifted-skin runs.
* Overlay: `python ../tools/stage_rows.py` then `python ../tools/mkov_h.py <out.pk3> [--skip textures] [--before]`.
* Offline first: `../../tools/offbox.py` (box over every clip frame, `IRONSIGHT_EXTRA_PAKS=<overlay>`);
  `tools/eyeview.py` (frames large / zoomed / with outside views), `tools/hktry.py` (bake `--set` variants into scratch
  and draw them in one sheet - nothing staged is touched), `tools/trypose.py`, `heavylib.py`.
* Sheets / GIFs: `tools/fsheet.py`, `tools/stsheet.py <out> sess:tag:+N:label ...` (chosen engine frames, `+N` from the
  reload mark), `../tools/dgif.py` + `../tools/gifsheet.py` and LOOK.
* Status: `tools/cov_h.py scan <id>` (stance from the stdemo tag), `python ../tools/coverage.py --lane heavy rule bar yes yes yes "<runs>"`
  (writes the lane's own status; `--lane heavy show` writes `heavy/coverage.md`, a lane-local preview - `../coverage.md`
  is the pistol lane's to build).
* Bugs: `python tools/buglog_add.py entries.json` (bug-3588..3591, 3597 predecessor; 3619-3623 this session).
* Patch scripts: write them as FILES. A Git-Bash heredoc turned a backslash-n into a line break again (bug-3621).

## BAR (second agent's notes; the sway-off table below is superseded by the one above) - `tools/heavybake.py bar` (+ `--braced`), `tools/patch_tik_h.py bar`
At the cheek weld nothing of the BAR's mechanism can be seen (handle 14 deg below / 9 deg left behind the comb, well
18-36 deg below the sight line), so for the work the gun SAGS 4.1 deg about the butt when the support hand leaves
(gunphys class `bar`, 9 kg) and the firing hand holds it canted 32 deg, 3 u forward, 0.7 u down (the WORK pose,
`gun_abs`); magazine stripped down the well and shown bottom-left out and in, seated, slapped; an EMPTY gun then gets
the left hand on the operating handle, hauled back and run forward with the gun's `bolt` bone keyed in the same
frames (gun clip `coop_reload_ads_empty.skc`, tik rows `reload_ads_empty` / `reload_ads_loaded` on bar.tik + 7 finishes,
cut loaded sound). Rows: `bar_reload_ads`, `bar_reload_empty` (retail hip clip), `bar_reload_empty_ads`, and the braced
`bar_reload_adsb` / `bar_reload_empty_adsb` (`braced=` in the gun entry: support 0.3, strength 0.8 -> 2.4 deg sag, butt
end 0.7 u lower instead; a shallower sag put the front sight ears into the box, run hc2).

Final clips: loaded 0e1d9d7d, empty 703e4870, braced 33486b6d / cad69914, gun clip 4a5edd0c; cgame_heavy2.
| what | runs | engine box extra vs the settled aim (aligned, sway off) | offline | sight line |
|---|---|---|---|---|
| loaded: stand, crouch, prone, lean L, lean R, braced | hc6, hc7 | 0.1 / 0.1 / 0.2 / 0.1 / 0.1 / **1.3 %**, 0 frames over 2 % (not aligned: max 1.8 %, prone) | 0.0 % | leaves 6.2 deg (braced 4.3), back to 0.01 deg |
| EMPTY: the same six | hd1, hd3 | first 6-15 capture frames = the last shot's kick (6-20 %); after them **max 0.8 %**, 0 frames over | 0.0 % | back to 0.00 deg |
| EMPTY, standing, sway + breath ON, lifted skin (what the player sees) | hd2 | work 0 %; **2-3 % for 16 capture frames at the return** | - | clip end within 0.02 deg |

bug-3597 as it stands (bug-3620): the rig-solve target does not freeze (ADSSETTLE 0.0000 rad / 0.000 u on the emptied
BAR, hd1 / hd2); the clip's tail was tight and is now closed (support hand back f77-82, the last four frames are the
aim pose). The 2-3 % at the return appears ONLY with `cg_adsSway` / `cg_weaponBreath` on - the aim's own sway / breath
offset while the clip plays against where it is afterwards. A cgame question for the ads-next owner; re-measure when it lands.

Evidence: `evidence/bar_reload_aimed_loaded.gif` (hc4), `bar_reload_aimed_empty.gif` (hd2) - both lifted skin, played
back frame by frame, no pop; `bar_handle_engine_crops_hc1.jpg` (the ribbed knob forward, fingers round it, GONE from
the front at full pull); `bar_reload_aimed_loaded_stances_hc4.jpg`, `bar_reload_aimed_empty_stances_hd1_hd3.jpg` (dark skin).

Weak points, seen in playback - say them:
* The handle hand is the back of a pale fist / forearm about a quarter of the screen wide, 7 u from the eye at the end
  of the pull. The knob is seen in the reach frames (0.1 s) and not while it is gripped. Eight other grips / work
  poses were tried offline (`hktry.py`: from below, edge-on, gun pushed forward, gun yawed): every one was larger or
  brought the firing arm into view. It reads by the hand's travel, the gun's roll into the shoulder and the sound.
* The return from the work pose to the aim takes 0.2 s (brisk for 9 kg). The magazine is in view 0.2 s each way.
* Stock-mesh BARs (`bar_bar1918a*`, `bar_pabar`) share the rows: rounds left is fine (hc10), an EMPTY one would grip
  the S93 handle point with no gun-side row - **not run, open** (bug-3623). Lewis / MG42 keep their own `coopr_*` hip
  clips while aiming (box clear in the sampled frames, not rebuilt). Break-offs not run. Hip reload untouched.
* M1919 portable: aiming shows a black receiver wall over the lower half of the screen into the box, and its reload
  swings the barrel up through the box (hc9 / hc10, bug-3622) - item 4, sight row first.

## StG 44 (second agent's notes; figures superseded above) - `tools/heavybake.py mp44` (+ `--braced`), `tools/patch_tik_h.py mp44`
The second `heavybake` gun entry; `spec()` is shared with the BAR. Facts (`heavylib.py mp44`, `clipinfo.py`,
`gunmove.py`): at the cheek the magazine hangs 33-50 deg below the sight line (frame edge 26) and the left-side cocking
handle, 15 deg below at rest, ends its 6.2 u pull 37 deg below, 4 u from the eye - the same answer as the BAR (sag
2.9 deg by gunphys class `stg`, 5.4 kg, + the canted work pose 1.2 u down). Differences that are in the entry:
* **Order**: sag first (support off f2-6), cant after (f7-15); the return mirrors it (cant off f52-60, then the rise).
  Canted while still high the gun left the aim's silhouette through the box (5.6 % offline, bug-3646).
* **Magazine prop**: the server attaches `mp44_clip` to the off-hand tag from frame 0 (gun's own hidden f13-42):
  `handover=True` + `prop_hold={'tag_weapon_left': 12}` keep it inside the gun's magazine until the hand has it
  (`tagrel.py` prints the tag against the retail relation).
* **Handle**: `release=True` - no hold-open, the hand pulls it back (f63-67) and LETS GO, the spring runs it home
  (f69-71) without the hand. `bolt=dict(chan='Box02 pos', ...)`: the generic bolt channel of `gun_clip()`.
* **Rounds left = closed bolt, one in the chamber: no cocking.** The RETAIL gun clip cocks in every reload, so the tik
  gets `reload_ads_loaded` -> `coop_reload_ads_loaded.skc` (handle still, sound cut at f56-62) and `reload_ads_empty`
  -> `coop_reload_ads_empty.skc` (our pull). 11 tiks on `models/weapons/mp44` + the strapped twin on
  `models/weapons/coop_mp44strap` (`more_paths`: same handle geometry, byte-identical retail clip; clips staged on its path).
* `slap_action='lg_mag_slap_light'`: the BAR's palm slap threw the lighter gun's front sight to the box (bug-3647).
* Rows: `mp44_reload_ads` (same path as the SHIPPED clip - the staged file replaces it), `mp44_reload_empty` (retail hip),
  `mp44_reload_empty_ads`, `mp44_reload_adsb`, `mp44_reload_empty_adsb`.

Final clips: loaded 72239c8c, empty 38e83d9b, braced 80d8c375 / ed50e65d; cgame_heavy2; overlay `SCRATCH/adsheavy/ov_m6.pk3`.
| what | run | engine box extra (aligned, sway off), stand / crouch / prone / lean L / lean R / braced | offline | sight line |
|---|---|---|---|---|
| loaded | he7 | 0.2 / 0.8 / 0.7 / 0.4 / 0.2 / 0.3 %, 0 frames over | 0.3 % (braced 0.9) | leaves 5.2 deg (braced 3.9), back to 0.01 deg |
| EMPTY | he6 | after the last shot's kick and smoke (6-29 capture frames): 0.9 / 1.0 / 1.6 / **1.96** / 1.7 / 1.6 %, 0 frames over | 0.3 % | back to 0.00 deg |
| strapped variant, EMPTY, standing | hf2 | 4 kick frames, then 0 over; looked at (plays the new clip, handle worked) | - | back to 0.00 deg |
| aim pose (shipped, unchanged) in 8 stances incl. braced | hf1 | - | - | 0.00 deg |

An emptied gun reads higher than a settled one in the same clip (0.4 % loaded against 2.0-2.5 % emptied before the
work pose went 0.5 u lower, run he5): after a long burst the gun rides a little higher through the reload. Leave margin.
Evidence: `evidence/mp44_reload_aimed_loaded.gif` (he7), `mp44_reload_aimed_empty.gif` (he6) - played back, no pop;
`mp44_handle_engine_crops_he6.jpg`; `mp44_reload_aimed_{loaded_stances_he7,empty_stances_he6}.jpg`.
Weak points: the hand on the handle is the back of a pale hand about a third of the screen wide for 0.7 s (the handle
shows before the hand closes and after it is home, not while gripped); empty lean-left is ON the bar (1.96 %); the hip
reload is untouched (retail cocks even with rounds left); break-offs and the scoped / finish tiks not run (same mesh).

## Skins
* `tools/barskin.py`: S93_bar / S93_bar-bipod lifted (mean 19 -> 45), `.dds` + `.tga` both staged.
* `tools/clipskin.py`: the magazine prop `textures/models/weapons/bar/barclip` toned down from light grey (84) onto the
  lifted gun (47, its warm cast), `.dds` + `.tga`. It is the retail prop's texture: the hip reload shows it too.
* Finishes against the lifted base (run hc9, aimed, same wall): desert / winter / woodland camo are all LIGHTER than
  the base; bloody is a dark red and darker than the base (its own art, as intended); the stock-mesh `bar_bar1918a` is
  near black and `bar_pabar` pale grey - their own skins, not part of the lift.
* **Shipping: the texture the engine shows is `S93_bar.dds` inside `zzzzzzzzzz_coop_hd_m3l1a.pk3`, which is off limits.
  The lifted `.dds` files (and `barclip.dds` if that pak carries it - check `vfs.winner`) must ship in a pak that sorts
  ABOVE it.** This lane ships nothing.

## Next
1. Shotgun sight: done, see "Shotgun sight".
2. FG 42 hip reload on the model (above); a run that proves whether a scoped reload plays at all (clip trace).
3. Belt-feds: M1919 portable first (sight row; bug-3622), Breda, Vickers, MG42.
4. Shotgun leftovers: a `shotgun_cycle_ads` look at the pump between aimed shots (it stayed at the aim in hj11, not
   measured apart from the smoke); a longer "show" of the shell; a short end row for a break-off with a round
   chambered; the hip reload rebuilt off the centre of the screen if the user wants it.
5. A new gun = a `heavybake` entry (copy DP28 for a top feed, MP44 for a well): `clipinfo.py <row> <gun clip>` and
   `gunmove.py <tik> reload` give the retail timeline, the bolt channel and the handle point; `heavylib.py <prefix>
   <points>` where they sit at the aim; then `hktry.py` / `eyeview.py` (set `IRONSIGHT_EXTRA_PAKS=<overlay>` or the
   staged gun rows are not found), THEN the engine. Read `clipsize` from the tik before an emptied run.
Carry-forward for the coordinator: the lifted BAR `.dds` must ship in a pak sorting above
`zzzzzzzzzz_coop_hd_m3l1a.pk3` (see "Skins"); never touch that pak.

Runs: ha1 / ha2 (aim poses), hb1-hb9 (predecessor's BAR iterations), hs / hn (skin), hc1-hc10 (2b: stances, braced,
variants, finishes), hd1-hd3 (final BAR clips, settle diagnostics), he1-he7 (StG 44; he6 / he7 final), hf1 (StG 44 aim
stills), hf2 (strapped variant). `centrebox.json` keys are GUN names (`bar`, `bar_empty`, ...) as coverage.py reads
them; `python ../tools/coverage.py --lane heavy build` writes the lane preview `heavy/coverage.md` (BAR and StG 44: DONE).
Bugs: 3619-3623, 3646-3649 (second agent); 3667-3676, 3681 (third agent); 3696-3698, 3727-3732 (fourth agent); 3755-3759, 3769-3773 (fifth agent); 3824-3832 (sixth agent).
Tools added by the third agent: `boxeng.py --sway`, `swayshow.py`, `run_h.py --tail / --brk / --hipdemo / --hold / --rel`,
`heavybake.py --hip` + `feed='top'`, `patch_tik_h.py` `more_paths` for the BAR, `hip=True`, the `dp28` set.
