# RIFLE lane - aimed (ADS) first-person animations

Lane of `docs/proposals/ads_twohand_2026-10-11` (read the HANDOVER at the top of `../README.md` first: the standard and
the method are the pistol lane's). Rows: the `## rifle` section of `../coverage.md`. Nothing here is in the mod tree or
the fixes pak; everything is staged in this folder and on engine branch `ads-rifle-next`
(worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-rifle`, build dir `.cmake`, test build `cgames\cgame_rifle4.dll`).

# HANDOVER (2026-10-13 late morning, seventh stretch) - read this first

**Done this stretch: the G 43 Irons is closed** - server timing equal to the scoped G43, the unlock path through the
generators and tested with a real promotion, the 4 pack skins as variants on the shared G43 challenges, loot picture,
AI alias, dev lists; and a sample of the 52 variant bolt tiks run in the engine. NOT done: everything from the Kar98
reload leftovers on (order unchanged, list in the sixth stretch below).
* Engine `ads-rifle-next` **c7ce5e86** = `G:\mohaa-adsanim2\cgames\cgame_rifle8.dll` (60e00829 + the client clip
  clock). The bolt cycles being integrated are at 60e00829 (`cgame_rifle7`) and need nothing from c7ce5e86.
* Overlays: `ov_rifle_g4.pk3` (`mkov_rifle.py <pk3> --armgen` = staged assets + the generator-made armory entry),
  `ov_rifle_g3m.pk3` (the same with the measure tiks), `ov_rifle_g4y.pk3` (+ the script probes of `srvtime_ov.py`).
  `--armory` (the hand-made entry) is superseded.
* Run ids used: rb39-rb47. **rb48 is next.** Finished run folders are in `H:\hzm_archive\rifles\`.
* **FROZEN (coordinator, 2026-10-13): the between-shot bolt cycles** - the capped `rechamber_ads` clips, their rows
  and the 56 variant tiks are being taken into the release build from this folder. Do not change those clips, rows or
  tiks; a later aimed-RELOAD row goes into the same tiks as a SEPARATE row, the bolt rows byte-identical. A defect
  found in them is reported to the coordinator, not edited.

## 1a. Server timing (runs rb39-rb42; listen server; `tools/run_srvtime.py`, `srvtime_ov.py`, `srvtime_report.py`)
A server script prints level.time and the reserve ammunition every server frame, the weapon tik's own `reload` row
prints at its entry and on frame (frames - 2), `coop_fireDebug 1` prints the torso state hops. Seconds after the torso
enters the reload; hip and aimed, one round fired and emptied all read the same:

| | weapon row starts | magazine filled | weapon row's frame N-2 (row ends +0.07 s) | torso leaves the reload = can fire |
|---|---|---|---|---|
| scoped G43 (released tik) | 0.00 | 1.70 | 1.80 | 2.90 |
| G 43 Irons as staged before (88-frame `reload` clip, rb41) | 0.00 | 1.70 | **2.88** | 2.90 |
| G 43 Irons now (rb42) | 0.00 | 1.70 | 1.80 | 2.90 |

The reload itself (fire-ready 2.90 s, magazine at 1.70 s) was never longer - both come from the TORSO clip. What the
88-frame gun clip changed was the server's `WEAPON_RELOADING` window: 2.95 s instead of 1.87 s, ending after the torso
had already left the reload (read by the quick-draw logic and `Sentient::AttachToOwner`). Fixed the way the pistol
lane planned it: the 12 tiks' `reload` row is the released `g43_reload.skc` again (`tools/g43srvrow.py`; `g43tik.py`
writes the same), and the aim-only row `reload_ads_empty` (88 frames, the rack at 62-69) is kept by the cgame on its
own clock after the server's row has ended (`coop_vmGunClipClock`, default 1; the pistol lane's uncommitted change of
`ads-next` ported, without its revolver lines). `coop_g43_irons_reload.skc` is no longer referenced (left in place).
**All staged rifle tiks** (`tools/rowlen.py` -> `evidence/rowlen_staged_vs_released.tsv`): 68 tiks, 391 rows that
exist in the released tik - **0 differ in length**; 68 new rows the server has no name for (`rechamber_ads` in 56
tiks, `reload_ads_empty` in 12).
Re-run with the new cgame (rb43, six stances, sway on): the rack plays after the server's row has ended in every
stance (`GUNCLOCK start ... clip 2.90 s (server row 1.83 s)` / `end ... (clip over)`, 6 of 6).

| rb43 | hands-only box max per stance (stand crouch prone leanL leanR braced) | back to | the rifle's own body in the box |
|---|---|---|---|
| rounds left | 0.1 0.0 0.0 0.1 0.1 0.0 % | 0.01 deg | 0.6-4.2 % for 0-9 frames |
| emptied | 0.0 0.0 0.0 0.2 0.1 0.1 % | 0.02 deg | 0.1-1.0 % |

LOOKED AT: the rack frames stand, new against old (identical action); the frames around the server row's end, hip and
aimed (no pop); the six-stance sheet of the emptied reload. Only measured: the rounds-left reload in five stances.
The emptied capture still has only an end reference (bug-3742 stands).

## 1b / 1c. Unlock path, variants, names -> `wire/README.md` (the recipe; start there for the next new gun)
`wire/stage_armory_gen.py` runs patched COPIES of the generators over a scratch copy of the repo. Rank 2 stands.
Tested with a real promotion (rb46): locked at rank 0 and 1, unlocked by the `xp_award` that crosses 1200 XP, the
record keeps what it had, pick + restart spawn it, the Flecktarn variant locked until the scoped G43's own challenge
(225 kills on the shared counter) is done, then applied and spawned. The scoped G43's ACC bar is staged as 9.

## 1d. Variant bolt tiks in the engine (rb45, `cgame_rifle7` = the integrated commit)
`kar98_lite`, `kar98_camo_winter`, `mosin_nagant_rifle_gold`, `mosin_nagant_rifle_lite`, `enfield_blued`,
`enfield_lite_chrome`: each loads, fires an aimed shot and cycles, no script or load error.
`evidence/bolt_capped_variant_tiks_rb45.jpg` (looked at). `tools/boltsame.py` (model silhouette on the frames where
the base rifle's capped and uncapped captures differ most): all six are nearer the capped base capture - Kar98 0.85 /
0.74 against 0.77 / 0.65, Mosin 0.84 / 0.80 against 0.72 / 0.73, Enfield 0.82 / 0.55 against 0.78 / 0.51 (the
Enfield margin is small; chrome on a white wall reads badly). The other 46 added tiks are not run.

## 2. Kar98 reload leftovers: STARTED, NOT DONE (run rb48; nothing staged was changed)
* Emptied capture, full length (`--parts empty --shots 5 --gap 110 --rframes 360`, stand + lean left): the capture
  now runs to the settled aim (sights back to 0.00 deg). `evidence/kar98_reload_aimed_empty_rb48.gif` replaces the
  `_rb23` one (decoded every 7th frame and looked at). Hands-only box: stand 0.6 %, lean left **0.9 %** - the 2.2 %
  one-frame figure of rb23 did not come back in this run (same clips; the sway phase differs), so nothing was changed
  for it. The rifle's own body: 8.7-8.9 %, 25 frames over 2 % as it leaves / re-enters the aim. `evidence/rb48_box.json`.
* `kar98_reload_stances_rb23.jpg` JUDGED: nothing is in the centre box in any of the 18 tiles and the six stances
  show the same action. **Not acceptable by rule 3:** at "bolt opened" and "bolt closed" the right hand is a large
  OPEN, cupped hand beside the bolt knob (fingers spread, not closed round the knob), in all six stances; at "charger
  pushed" the hand is flat over the receiver and no charger is seen; the full-length GIF also shows a wide open palm
  at the right edge for about a quarter second on the way back from the pouch. To do: a closed grip on the knob, the
  pouch half second, the clip pushes as a visible jolt - the hands rows only; the Kar98 tiks' bolt rows are frozen.

New tools: `rowlen.py`, `run_srvtime.py`, `srvtime_ov.py`, `srvtime_report.py`, `g43srvrow.py`, `run_unlock.py`,
`lootpic.py`, `boltsame.py`, `append_bugs.py`; `mkov_rifle.py --armgen`. Bugs: bug-3789..3797.
Evidence: `evidence/srvtime_rb39.tsv` .. `srvtime_rb42.tsv`, `rowlen_staged_vs_released.tsv`, `rb43_box.json`,
`rb45_box.json`, `bolt_capped_variant_tiks_rb45.jpg`; `evidence/g43irons/g43irons_reload_empty_ads_rb43.gif`,
`g43irons_reload_empty_stances_rb43.jpg`, `g43irons_unlock_path_rb46.jpg`, `g43irons_variant_label_rb47.jpg`,
`loot_w_g43irons.png`.

# HANDOVER (2026-10-13 morning, sixth stretch) - current except where the seventh says otherwise

**Done this stretch: the iron-sight G43 is finished as a weapon - gripping support hand, dark-steel hood ring and sight
base, 1080p aim capture, a shot and the hip reload captured, and its AIMED RELOAD (rounds left and emptied, six
stances).** NOT done: everything after it on the list (Kar98 reload leftovers, Springfield / Mosin / Enfield reloads,
the semi-autos, Carcano / De Lisle / Arisaka / G98, the scoped sample). Engine `ads-rifle-next` is unchanged
(**60e00829** = `cgames\cgame_rifle7.dll`: the rows and the gun-row swap it needs were already there). Overlay of the
staged state: `G:\mohaa-adsanim2\ov_rifle_f3.pk3` (`mkov_rifle.py <pk3> --armory`; `ov_rifle_e5.pk3` = without the
armory entry, with the measure tiks). Neither holds the 52 finish tiks of `boltcap_variants.py` - rebuild before the
next run. Run ids used: rb28-rb38 (rb29 spent on a failed boot); **rb39 is next**.
Run folders ra1-ra7 and rb1-rb13 were MOVED off G: (disk full) to
`C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\rifles\runs\`
(set `ADS_RUNS` to it to re-read them); rb14 and later are still in `G:\mohaa-adsanim2\runs`.

## Later the same stretch (commits e0d918e and the one after): armory entry, finishes, variant coverage
* **Its own armory entry** (user: "its own rifle you unlock honestly and pretty early on"), STAGED:
  `wire/README.md` is the apply list and the recipe (written for the FG 42 Irons / double-barrel lanes too);
  `wire/stage_armory_g43irons.py` makes the patch against the mod tree and the harness copy from the released pak.
  Roster id 78, tile "GEWEHR 43 (IRON SIGHTS)" between the M1 Carbine and the Kar98k (the rifle tab is in unlock
  order), **unlock = rank 2** (1200 XP; Carbine rank 1, Kar98k rank 3, scoped G43 rank 5), finishes fid 1-7, stat bars
  DMG 5 / RPM 4 / ACC 8 / MOB 10. Run once (rb34-rb37, overlay `ov_rifle_f3.pk3`, `tools/run_armory.py`): tile, lock
  icon + requirement text, pick refused while locked, with the gate off the pick lands in PRIMARY 1, the rifle is in
  the hands after a map restart, the Winter finish applies and survives a second restart.
  Stills: `evidence/g43irons/g43irons_armory_tile_rb37.jpg` (final), `g43irons_armory_rb35.jpg` (six moments; the
  tile still at the bottom of the list there).
* **All 12 tiks in the engine** (rb38): each loads its own sheet, leaf / hood / post dark steel on every one -
  `evidence/g43irons/g43irons_finishes_rb38.jpg` (hip + aim). Selectable in the armory: STD + the 7 finishes.
  The 4 pack skins (`dhg43fleck`, `hobbsg43wood`, `hobbsg43urb`, `lv_ttg43`) exist and load but have NO armory path yet.
* **Bolt rifles, variant coverage** (`tools/boltcap_variants.py`, bug-3764): the aim-only gun row `rechamber_ads` was
  in the four base tiks only; it is now staged in every tik that shares the mesh - Kar98 19 (base, 7 finishes,
  `kar98_lite` + its 7, `hobbskarwood`, `hobbskarworn`, `lv_ttkar98`), Springfield 1 (`springfield_unscoped`; it has no
  finish tiks on that mesh), Mosin 18, Enfield 18. NOT covered: `kar98_g98` and `enfield_p14` (own meshes: the cgame's
  mesh guard keeps them on the hip clips), the Gewehrgranate family (no aim), every scoped family. **None of the 52
  added tiks has been run in the engine** - the next bolt run should carry one finish and one `_lite` per rifle.

**NOT DONE - the coordinator's open orders, in order (nothing below is started unless it says so):**
1. G 43 Irons, the user's two rules for every new gun:
   a. *"unlock paths, the way we already do it"* - generated, not hand-written: the requirement text comes from
      `docs/tools/armory_unlocks.py --emit` (-> `coop_mod/unlockreq_gen.scr`; the staging edits that generated file by
      hand - replace by a generator patch), challenges in `coop_mod/challenges.scr`, the Service Record rows and
      "Unlocks: X" names from `docs/tools/gen_service_record.py` (`REWARD_NAMES`); read `docs/FEATURES.md` about lines
      510-570 first (trap: an EMPTY `coop_mod/save/unlocks_<hash>.dat` denies every pick). Test with the mod's own
      grant path `coop_mod/coop_selftest_xp.scr` (the rank-2 grant itself was NOT tested - only the lock it feeds):
      locked -> requirement met -> unlocked -> spawn -> Service Record row; an existing unlock record keeps what it
      had. Stills wanted: the locked tile, the Service Record row. Patches to the generators go in `wire/`.
   b. *"camo / variants too"* - the 4 pack skins as model variants of roster id 78: an entry in
      `docs/tools/wire_mv2.py` (`("coop_g43_irons", [dhg43fleck, hobbsg43wood, hobbsg43urb, lv_ttg43], "<elite cid>")`
      -> fid 8-11, `ui/loadout/mvp78_*`, `reqmv78.cfg`) + base and elite `chal_def`s (else `variant_challenges.py`
      skips the gun), its own weapon id in `challenges.scr` (today its kills count as the G43's).
2. Kar98 reload leftovers (emptied capture `--rframes 360`, lean-left 2.2 %, judge `kar98_reload_stances_rb23.jpg`,
   the pouch half second and the clip pushes as a visible jolt).
3. Springfield / Mosin / Enfield aimed reloads (stripper clips, under the centre box, back to the exact aim); the
   variants P14 Enfield (`enfield_p14.tik`) and Gewehr 98 (`kar98_g98.tik`) ride with their base rifles' clips but
   each needs its own in-engine check (and its own capped `rechamber_ads` clip: `boltcap.GUNS`).
4. Semi-autos, in this order: M1 Garand (+ `garand_silenced.tik` + Pacific `m1_garand_pagarand.tik`), M1 Carbine
   (`carbine.tik`), SVT, Johnson. Then Carcano, De Lisle, Arisaka. Then ONE scoped-rifle sample with two options for
   the user; the thirteen scoped rifles and the scoped StG 44 wait for that decision.
For every aimed row made from here on: list which finish / variant tiks it reaches.

**Storage** (2026-10-13): G: filled up. Finished run folders are MOVED, never deleted: ra1-ra7 + rb1-rb13 are in
`...\scratchpad\rifles\runs\` on C: (path above); rb14-rb31 go to `H:\hzm_archive\rifles\` (`scratchpad\move_runs_h.py`,
verified copy, then the source folder is removed); rb32-rb38 are still in `G:\mohaa-adsanim2\runs`. From now on a
finished, written-up run goes to H:. Live captures stay on G:.

## G 43 Irons - what changed (supersedes the matching points of the fifth stretch below)
* **Support hand** (`tools/g43pose.py`, default now): the G43's OWN hip grip (`viewmodel/g43/g43_idle.skc`: palm under
  the fore-end, fingers wrapped up its far side, thumb up the near side) moved 0.3 u left / 2.0 u down - a hand cupped
  under the wood, thumb edge at the left, knuckles at the right of the receiver. `--aimgrip` = the old Garand-pose hand.
* **Dark steel on every finish** (`tools/g43irons.py` `MOVE`): rear sight base 70 tris + leaf 10 + slider 20, the post's
  foot 10 and the hood ring 28 (out of `g43cull`) leave their surfaces and come back, same triangles, flat shaded, in
  `coop_sight` (216 tris now; shader `cull none` for the ring). Seen on wood and Winter at 1080p.
* **Bolt**: the carrier (51 tris) and its cocking handle (32 tris, on the carrier's LEFT) are on a new bone `coop_bolt`
  (child of `G43`, identity in every retail clip).
* **Post / notch size**: stays. At 1920x1080 the post is 5 px wide and the notch about 20 px, both read
  (`evidence/g43irons/g43irons_aim_1080p_rb33.jpg`).
* **Torso state row** - a blocker found by the first hip reload (rb28, bug-3739): the state file picks the reload's
  torso clip by weapon NAME; "G 43 Irons" fell to the Garand's, which hands the gun to the left hand - the rifle left
  the right hand and dropped out of the picture. STAGED: `wire/player_torso_g43irons.patch` (one line) and the harness
  copy `assets/coop_mod/player_torso.st`, built from the RELEASED pak (`tools/g43state.py`; the mod tree's file crashed
  the test server, bug-3740).
* **Reload, the facts** (`tools/g43reload.py`, its docstring is the reference): the torso clip (88 frames, 2.93 s)
  ends the reload, not the gun's 56-frame clip. The retail hands never touch the cocking handle - the left hand takes
  the magazine out below (10-18), brings the new one (50-56), strikes its foot with the palm (64-66) and returns
  (74-82); the firing hand never leaves the grip. The staged tiks use an 88-frame gun clip
  `coop_g43_irons_reload.skc` (retail clip held) and a row `reload_ads_empty` (carrier racked 4.2 u, frames 62-69),
  which the cgame shows when an EMPTIED rifle is reloaded while aiming.
* **Aimed reloads** (`riflereload.py` machinery: holds `down` 1.9 u / `low` 2.7 u, 12 deg top-right / `reach` 3.1 u):
  rounds left = the retail technique under the centre box, back to the aim at clip frame 83; emptied = magazine out
  and in, then the left hand wraps the handle from the rifle's left (the hip grip turned 62 deg about the rifle, fingers
  closed, thumb laid down), hauls the carrier back and lets it go; back to the aim at 84. Rows
  `coopr_g_43_irons_reload` / `_reload_empty` (both the retail clip) / `_reload_ads` / `_reload_empty_ads`.

RESULTS, run rb32 (sway on, six stances: stand, crouch, prone, lean L, lean R, braced):
| | hands-only box max per stance | back to | the rifle's own body in the box |
|---|---|---|---|
| rounds left (one shot, `reload`) | 0.1 0.1 0.0 0.1 0.2 0.0 % | 0.01 deg | 0.5-4.9 % for 0-12 frames as it leaves / re-enters the aim |
| emptied (ten shots, automatic reload) | 0.0 0.0 0.0 0.1 0.1 0.1 % | 0.02 deg | 0.4-0.9 % |

The emptied figures are weaker than they look: that capture has only an end reference and the settled-aim mask still
covers 9-13 % of the box (`rbox.py`, bug-3742). Offline (`g43rpart.py`): hands 0.0 %, the gun's surfaces 0.5 %.
LOOKED AT: the 1080p aim (light, dark, Winter); the shot strip; the hip reload sheet (rb30 / rb31); the rounds-left
reload every 9th capture frame (rb31) and the emptied one every 7th + the rack enlarged (rb31); the six-stance sheet
(six moments, rb32); the emptied GIF decoded every 3rd frame. Only measured: the rounds-left GIF of rb32 itself, the
other stances' full playback.
Weak points seen, not hidden:
* the magazine change itself is under the rifle and below the picture (as on the SMGs): what shows is the hand
  leaving, the rifle sagging and jolting, the hand coming back;
* the racking hand is LARGE (the handle is 8-12 u from the eye) and for two capture frames on each side of the rack it
  is an open, pointing hand (the fingers close / open on the way);
* the left hand returns to the fore-end with spread fingers (the retail return, frames 74-82);
* an emptied G43 shows its carrier shut until the rack (the gun has no hold-open state; `fire` is the idle clip);
* the HIP reload of an emptied rifle does not rack (retail clip; a hip clip with the rack was not made);
* the rear sight base is flat mid-grey (no texture detail) beside a near-black receiver.
Evidence (`evidence/g43irons/`): `g43irons_aim_1080p_rb33.jpg`, `g43irons_shot_recoil_rb33.jpg`,
`g43irons_reload_hip_rb31.gif`, `g43irons_reload_ads_rb32.gif`, `g43irons_reload_empty_ads_rb32.gif`,
`g43irons_reload_stances_rb32.jpg`. The `_rb27` aim stills show the old open-palm hand and the finish-coloured hood.
New tools: `g43reload.py`, `g43state.py`, `g43rpart.py` (rpart for this gun); `run_rifle.py --w --h`;
`rbox.py` settled aim of an emptied capture from its last frames. Bugs: bug-3739..3745, bug-3764..3768.

# HANDOVER (2026-10-12 late night, fifth stretch) - the iron-sight G43's build; current except where the sixth says otherwise

**This stretch did ONE thing: the IRON-SIGHT G43 is built and its look test is delivered (and refined once on the
coordinator's notes). NOT done: its aimed reload, its reload stance sheets, and everything after it on the list
(Kar98 reload leftovers, Springfield / Mosin / Enfield reloads, the semi-autos, Carcano / De Lisle / Arisaka / G98,
the scoped sample).** Engine `ads-rifle-next` **60e00829** = test build `cgames\cgame_rifle7.dll`. Overlay of the
staged state: `G:\mohaa-adsanim2\ov_rifle_d4.pk3`. Run ids used: rb24-rb27; **rb28 is next**.

## Iron-sight G43 ("G 43 Irons") - what exists
Accepted by the coordinator after the look test: the notch, eye relief 17.0 u, the Garand's accuracy / movement rows.
* **Mesh** `assets/models/weapons/g43/coop_g43_irons.skd` (`tools/g43irons.py`, from the retail `g43.skd`, which is
  not touched): scope tube, two turrets, two rings, mount (300 triangles) and the whole `svt_lens` surface are out;
  the dovetail rail on the receiver's right side stays. The retail rear sight had **no notch** (a solid block 1.35 u
  wide) and the front post was 0.085 u wide (2 px): both are dropped and rebuilt as a surface of their own,
  `coop_sight` (78 triangles, shader `coop_g43_sight`, `assets/scripts/coop_g43_sight.shader` +
  `assets/textures/coop_wpn/g43_sight.tga`) - **dark steel on every finish**: a tangent-leaf plate 0.95 u wide with
  chamfered corners, a notch 0.30 u (top) / 0.20 u (foot) wide and 0.19 u deep on the post's line, a worn edge band,
  and a post 0.19 u wide inside the untouched hood ring. One mesh = first person and world / third person.
* **Tiks** `assets/models/weapons/coop_g43_irons.tik` + 11 finishes (`tools/g43tik.py`, each from the mod tree's own
  G43 tik of that finish): name **"G 43 Irons"** (a base name of its own - "G 43 (Irons)" would be stripped to
  "G 43" and get the scope, bug-3713), rank 271, no `zoom`, the M1 Garand's accuracy and movement rows, `airange long`;
  damage, fire delay, 10-round magazine, sounds, recoil kick and the reload are the G43's own.
* **Sight row** `sights_override.json` (lane-local; `tools/patch_sights_row.py <worktree>\code\cgame\cg_adssights.h`
  inserts the 12 rows): F 41.95 -1.1565 -4.388 (post tip), R 12.0845 -1.1565 -5.33 (notch shoulders), relief 17.0 u.
  The shared ironsights `sights.json` is NOT edited.
* **Aim pose** `viewmodel/g43/coop_g43_irons_aim.skc` (`tools/g43pose.py`): the Garand pose with the support hand
  1.1 u left / 1.6 u lower, so no finger shows right of the receiver. Row `coopr_g_43_irons_charge`
  (`rows_rifle.py`); the scoped G43 keeps `g43_charge`.
* **Engine** (cgame only): "G 43 Irons" -> the G43's hands and the Garand's aim tune; the 12 sight rows; the per-weapon
  row override `coopr_<weapon key>_<suffix>` now also covers `charge` (the pistol lane's rule on `ads-next`).
* **Measured** (rb27, `cg_adsSightDebug`): sights on the centre 0.00 deg in stand / crouch / prone / both leans; the
  bore sits 1.75 deg under the sight line (the rear sight is that much higher than the post on this mesh); relief
  17.00 u (19.0 u braced - the brace view, as on the Kar98).
* **Looked at** (every sheet opened): mesh from three sides before / after; hip (wood, Winter, crouch, the scoped
  gun beside it); aim on the light wall and the dark door enlarged 4x; aim in stand / crouch / prone / lean left /
  lean right / braced, light and dark, wood and Winter; third person at the hip and aiming.
  Evidence, `evidence/g43irons/`: `g43irons_mesh_side_before_after.jpg`, `g43irons_hip_rb27.jpg`,
  `g43irons_aim_rb27.jpg`, `g43irons_aim_stances_rb27.jpg`, `g43irons_third_person_rb27.jpg`; the `_rb26` files are
  the first look (flat plate with a small V nick, thin post, raw Garand pose) - superseded, kept for comparison.
* **Weak points seen**: at 1280x720 the post is 3 px wide and the notch 13 px - it reads, but small (1080p: 4.5 /
  20 px, not captured); the support hand is now an open palm on the left of the fore-end; in the mesh picture
  `g43irons_mesh_side_before_after.jpg` (current mesh) the offline renderer draws `coop_sight` as untextured light
  grey - in game it is dark steel; the held gun is small in the third-person stills; the hood ring and the rest of the
  rear sight take the finish (white on Winter); third person: the camera cvars are ignored while aiming, so there is
  no side view of the AIMED gun from outside.
* **NOT done / not verified**: the aimed reload (below); hip reload not run with the new mesh; fire / recoil not
  captured; a second client or a dedicated server (new tiks, new shader); LOD at distance (the dropped triangles'
  vertices stay in the file; `coop_sight` collapses last); `coverage.md` has no row for it.

### How a player gets it (worked out, STAGED in `wire/`, nothing applied)
The mod hands out variant tiks through two generated tables: finishes (fid 1-7, `coop_mod/loadoutskins.scr`
`level.coop_skinGive[<base tik>][fid]`) and **model variants** (fid 8+, the armory's VARIANT button cycles them, each
unlocked by a kill challenge with the host gun; generator `docs/tools/wire_mv2.py`, which also writes
`loadoutskins_base.scr`, `mvchal_gen.scr` and the `ui/loadout/mvp<id>_*.cfg` chain).
1. **Model variant of the G43 (recommended; `wire/wire_mv2_g43irons.patch`)**: one entry appended to the G43's list
   in `wire_mv2.py` -> fid 13 of roster id 04 "GEWEHR 43", label "G43 IRON SIGHTS (NO SCOPE)", unlocked like its
   other variants. Appended LAST so the saved fids 8-12 do not shift. A finish cannot be combined with a model
   variant (one fid at a time), so the 11 finish tiks would be unused on this path.
2. **Its own armory entry**: a new roster id in `coop_mod/loadoutroster.scr` (+ `coop_loRosterGive`, a UI tile) with
   `coop_skinGive["models/weapons/coop_g43_irons.tik"][1..7]` = the staged finish tiks: irons AND a finish. More
   UI work; not staged.
3. **Dropped by German riflemen**: `coop_mod/aihandler.scr` already arms a share of Kar98 soldiers with
   `models/weapons/g43.tik` (`coop_aiG43Chance`); giving them the iron-sight tik instead puts it on the ground for
   pick-up (most real G43s had no scope). Not staged.
4. Today, for testing: `give models/weapons/coop_g43_irons.tik` (what the harness does).
Needed with any of them: `wire/recoil_table_g43irons.txt` (12 rows - `coop_g43_irons` resolves to NO row of
`coop_mod/recoil_table.txt`, bug-3714; tiks named `g43_irons*.tik` would resolve by themselves and fit `wire_mv2.py`'s
default naming - a naming decision), the staged assets, the cgame, and the sight rows in the shared `sights.json`.

### Its aimed reload - NOT started; what is known
* Hip clip `viewmodel/g43/g43_reload.skc`: 88 frames x 1/30 s = 2.93 s. The gun's own `g43_reload.skc` is only
  56 frames (1.87 s) - the same mismatch the pistol lane met on the TT-33; tik: magazine surface hidden frames 16-50.
* `tools/clipinfo.py models/weapons/g43.tik reload viewmodel/g43/g43_reload.skc`: the LEFT hand keeps its place on
  the fore-end to frame 48 while the right hand leaves the grip at frame 2 and works; the hand tags change at about
  frame 50 (re-run with the off-hand span to read the second half).
* The tik has only `reload` (no `reload_empty`). Rows to use, so the scoped G43 and the G43 Sniper stay as they are:
  `coopr_g_43_irons_reload` / `coopr_g_43_irons_reload_empty` and their `_ads` (the cgame composes per-weapon row ->
  `_empty` -> `_ads`); the prefix `g43` has no mesh guard, so a plain `g43_reload_ads` would also reach the scoped guns.
* `tools/g43pose.py register()` makes the gun known to the offline tools (`V.SIGHTS['g43_irons']`, `V.GUNTIK`);
  the SMG lane's magazine reloads (`../smg/tools/smgbake.py`) are the nearest recipe (box magazine, handle worked
  when empty).

## Next (the coordinator's order, unchanged)
1. G 43 Irons: aimed reload (rounds left, emptied) + GIFs + stance sheet; hip reload and a shot looked at.
2. Kar98 reload leftovers (emptied capture `--rframes 360`, lean-left 2.2 %, judge `kar98_reload_stances_rb23.jpg`,
   pouch half second and the clip pushes as a visible jolt).
3. Springfield / Mosin / Enfield aimed reloads; 4. Garand, SVT, Johnson (the scoped G43: leave), then Carcano /
   De Lisle / Arisaka / G98, then ONE scoped rifle as a sample with two options.

## New tools this stretch
`g43parts.py` (components), `g43irons.py` (mesh + shader + texture), `g43tik.py` (12 tiks), `g43pose.py` (aim pose,
`--pic` = offline picture old / new), `g43look.py <run> <scoped run>` (the five evidence sheets),
`patch_sights_row.py`, `run_rifle.py` parts `hipstills`, `<part>D` (the same part facing `--darkyaw`), `tpc` (third
person, one screenshot per step), `relief` (settled aim at `cg_adsRigReliefBias` 0 / 1.5 / 3); `staged.py` now also
answers `vfs.winner` for a staged file that is in no pak. Bugs: bug-3711..3717.

# HANDOVER (2026-10-12 night, fourth stretch) - the bolt cycles and the Kar98 reload; still current for those

**Done: step 1 of the coordinator's list (bolt-cycle clean-up, all four rifles, six stances) and step 2 (Kar98 aimed
reload reworked, six stances). NOT started: aimed reloads of Springfield / Mosin / Enfield, the semi-autos, Carcano /
De Lisle / Arisaka / G98, the scoped sample, and the IRON-SIGHT G43 (new firm request - its section below).** Engine `ads-rifle-next` 2747ecc8 = test build `cgames\cgame_rifle4.dll`.
Overlay of the staged state: `G:\mohaa-adsanim2\ov_rifle_c6.pk3` (`mkov_rifle.py ... --measure`). Run ids used:
rb16-rb23; **rb24 is next**.

## Settled (user / coordinator) - do not reopen
* Bolt cycles between shots: **variant A** - the rifle stays LOCKED on the sights (`ease` 0); the gun's own open bolt in
  the middle of the view is accepted and exempt from the 2 % box bar; hands, stock and any drift still count.
* "Comes down under the box" is allowed for a FULL reload only.
* The recoil is NOT held in a rechamber (section below). No change to recoil recovery.

## What changed in this stretch
1. **No bolt balloons any more (`tools/boltcap.py`, new).** Locked on the sights, the retail FULL stroke brought every
   bolt's rear to 0.0-0.9 u from the eye (Springfield 0.01 u, Mosin 0.55, Kar98 0.70, Enfield 0.94 - `boltnear.py`):
   that was the Mosin's "huge flat grey mass" and the Springfield's "bar to the right edge", and it was true of all four.
   Each rifle now has an AIM-ONLY gun clip, tik row `rechamber_ads`: the same cycle with the bolt's travel scaled so its
   nearest vertex stays **>= max(2.5 u, settled distance / 1.5)** from the eye - never nearer than 2.5 u, never drawn
   more than 1.5 x its size in the settled aim. Stroke kept: Kar98 2.81 of 4.61 u, Springfield 3.00 of 5.49,
   Mosin 3.34 of 5.82, Enfield 1.86 of 3.42. Timing, sound and case are the hip row's; the hip clip keeps its full
   stroke. cgame: the held gun shows `rechamber_ads` exactly while the hands play the aimed bolt clip
   (`CG_VMAdsBoltClip`, third row of the aimed gun-row table in cg_modelanim.c).
2. **Springfield handle**: the retail clip lifts it 80.5 deg; the aimed clip lifts it the real 90 deg (`lift` in
   boltcap.GUNS). The "long bar" was the handle 0.0 u from the eye, gone with the cap. Mosin (54 deg) and Enfield
   (48 deg) lifts are the retail ones - not changed (real: 90 and about 60).
3. **The hand holds the knob (`boltphys.py`: `knob_off` keyed per frame).** The retail grip cups the knob from below
   with the little-finger side of a fist; the old fixed offset (1.2 u right) left the knob OUTSIDE the hand. Now the
   knob sits in the curled fingers while the bolt is hauled back, and the hand opens to the fingertips where the knob
   stands at the box's rim (Kar98 lift + turn-down, Springfield lift + turn-down). Mosin 0.5 / 0.25 and Enfield
   0.3 / 0.15 for the whole cycle. The hand cannot be made small: it is 7 u long and the knob 6 u from the eye.
   Tried and dropped (pictures: `gripx.py`): thumb-and-forefinger hold with the forearm turned (the back of the hand
   becomes a brown slab over the right half), hand rolled above the knob (covers the box).
4. **Hands-only ENGINE figure (`rbox.py`)**: skin-coloured box pixels beyond the settled aim (the bolt is dark / grey,
   the brass case is excluded by its yellow). `HANDS (skin) max` is printed first, the old total after it.
5. **Kar98 aimed reload reworked (`riflereload.py`)**: see its section.

## RESULTS - bolt cycles, six stances each (stand, crouch, prone, lean L, lean R, braced)
Hands-only engine box maximum per stance, in that order:
| rifle | steady (run rb17) | sway on, as played | sight line | front sight, after the recoil | back to |
|---|---|---|---|---|---|
| Kar98 | 0.6 1.0 1.0 1.8 0.7 1.4 | rb20: 1.5 1.3 0.9 1.1 1.3 1.0 | 0.58-0.64 deg (braced 0.33) | 0.26-0.61 | 0.00 |
| Springfield | 1.4 1.2 1.3 1.0 0.9 0.1 | rb18: 1.8 1.4 1.7 1.2 1.5 0.5 | 0.57-0.61 | 0.22-0.39 | 0.00 |
| Mosin | 1.0 1.2 1.1 1.0 1.0 1.0 | rb18: 1.3 2.0 1.2 1.1 1.1 1.1 | 0.60-0.65 (braced 0.36) | 0.31-0.48 | 0.00 |
| Lee-Enfield | 0.7 1.1 1.1 1.0 1.2 0.2 | rb18: 0.9 1.4 0.8 0.8 1.1 0.4 | 0.59-0.66 (braced 0.36) | 0.26-0.61 | 0.00 |

Kar98's steady figures are from rb17, before its lift offset was widened (rb18 with sway read 2.8 % lean left and
2.2 % prone at the lift; rb20 is the staged clip). The total box figure (own bolt included, exempt) is 2-15 %.
Offline (`rpart.py`): hands 0.2 / 0.7 / 0.2 / 0.0 %, front sight within 0.16 deg in the clip alone.
LOOKED AT: stand of all four every 4th capture frame (rb17) and every decoded GIF frame through the action
(Springfield, Mosin; Kar98 reload); the bolt-back frame of every rifle in every stance (stance sheet); the frames with
the highest hands figures. Only measured: the other stances' full playback.
Weak points seen, not hidden:
* the working hand is still LARGE (right third of the picture while the bolt is back); it now holds the knob;
* Springfield: the handle is a thick dark bar from the receiver to the knob at the box's right rim (the mesh);
* Enfield: the knob is hidden inside the hand while the bolt is back;
* the shortened stroke is visible to anyone who knows the rifle (the bolt does not come back far enough to feed).

## Kar98 aimed reload (`kar98_reload_ads`, runs rb19-rb23)
The whole reload is worked JUST UNDER THE CENTRE BOX: the rifle comes down first (drop 1.9 u, 7 deg to the hand), the
bolt is opened there, the rifle sags to the reaching side while the hand is at the pouch (hold `reach`: the "static
half second"), the charger is set and thumbed in at drop 3.5 u (the push holds the rifle down), the hand letting go
springs it back (`hand_off`), the bolt is closed at 1.9 u, then up to the exact aim. Why not locked for the bolt
phases (rb15): the reload's gun clip has the full stroke - bolt 1.1 u from the eye for 0.45 s at each end - and the
loading sat at the bottom edge of the frame (drop 4.3 u).
RESULTS, run rb23 (the staged clip, sway on, six stances: stand, crouch, prone, lean L, lean R, braced):
| | hands-only box max per stance | back to | the rifle's own body in the box |
|---|---|---|---|
| rounds left (one shot, then `reload`) | 0.5 0.5 0.5 0.2 1.3 0.1 % | 0.00 deg | 1.4-6.2 % for 6-12 frames |
| emptied (five shots, automatic reload) | 0.2 0.8 0.2 **2.2** 0.4 0.3 % | 0.00-0.01 deg | 0.8-6.8 % for about 24 frames |

NOT met: the rifle's OWN body reads 2-6 % beyond the settled aim for about 0.1 s as it leaves the aim and again as it
returns (capture frames 18-24 and 210-214 of the rounds-left reload) although the clip goes straight down and straight
up, aligned (offline `rpart.py`: 0.0 %). It is largest in the very first frames - the blend from the aim solve into
the clip (engine side, not looked into). Lean left, emptied: hands 2.2 % in one frame.
An EMPTIED Kar98 works its bolt once more on the sights after the fifth shot (the game's existing sequence: `rechamber`,
then the automatic `reload`) and only then comes down and reloads; the capture of that case ends 0.1 s before the rifle
is back on the aim (`--rframes 330` is too short by a few frames: use 360).
LOOKED AT: the rounds-left reload in every second GIF frame (rb20 clip) and coarse (rb19); the emptied one in every
second GIF frame (rb23); three moments in six stances (stance sheet). The rb23 rounds-left GIF itself (the last entry /
exit change) was only measured.
Weak points seen: the loading is small (the rifle is 3.5 u under the eye line, the charger about 60 px at 1280 wide);
the half second with no working hand in view now has the rifle sagging to the right and coming back, which is slow and
slight; the thumb's two pushes are visible as a dip of the whole rifle, not as a jolt.

## FIRST for the next agent: the iron-sight G43 (user, 2026-10-12: "I'd like an iron sight version of the g43 too")
**NOT built - only the mesh was looked at (this stretch ran out of context).** The coordinator's order: new tik name(s)
only (`coop_g43_irons` + the camo variants that come free from the shared mesh; `G43.tik`, its three camo tiks and
`g43sniper.tik` stay untouched), scope + mount + lens removed from a STAGED copy of `models/weapons/g43/g43.skd`,
`zoom` back to an iron-sight value, sight row through a lane-local override, world / third-person model without the
scope too, staged and switchable. LOOK TEST FIRST (hip, aiming, third person, side view of the mesh before / after)
and send it to the user before any reload work; its aimed reload comes with the semi-autos.
What `tools/g43parts.py` found (gun frame u: x forward, z NEGATIVE = up; the scope, its mount and the lens are SEPARATE
connected components, and the real sights are under them - it looks clean):
* REMOVE (second `g43` surface): scope tube 180 tris (x -1.1..6.8, z -7.1..-5.1), two turrets 22 + 16 tris
  (x 2.3..3.3), two rings 12 + 12 tris (x -0.3..1.1 and 4.5..5.9, z -6.2..-5.5), the mount 58 tris (x 1.0..4.7,
  y -0.5..0.2, z -6.2..-3.6); the whole `svt_lens` surface (8 tris at x -0.8).
* KEEP as the receiver's dovetail rail: 20 tris (x -0.8..5.0, y -0.5..0.3, z -3.6..-3.1). Check the 48-tri piece at
  x -1.5..-0.8, z -3.3..-3.1 in a picture before deciding.
* ALREADY THERE: rear tangent sight on its base ahead of the receiver (70 + 10 + 20 + 12 tris, x 11.5..16.5, top at
  z -5.3), front sight base 38 tris (x 31.5..33.6), front post 10 + 10 tris (x 40.5..42.5, top z -4.4) and its hood
  (`g43cull`, x 41.4..42.5, z -5.1..-4.0). Nothing has to be built unless the look test says the notch is too coarse.
* An skd writer exists in the pistol lane (`../tools/m10build.py`, `m10rounds.py`, `slidesplit.py`) - reuse it; the
  sight row needs the rear notch / front post points for `ironsights_2026-09-28/sights.json`-style rows.

## Next (the coordinator's order)
1. Aimed reloads for Springfield (3-part `springfield_reload` / `_single` / `_end`), Mosin, Enfield: add
   `riflereload.GUNS` entries from the Kar98's (events from `clipinfo.py <tik> reload <view clip> lo,hi`); the same
   under-the-box plan (holds `bolt` / `reach` / `push` / `close`).
2. Semi-autos: Garand (en-bloc from the top, the ping, thumb clear, op-rod really runs), G43, SVT, Johnson; then
   Carcano / De Lisle / Arisaka / G98 (kar98 prefix, own meshes: the cgame mesh guard `CoopAdsClipFitsHeldGun` keeps
   them on the hip clip - own clips under own row names, or a guard entry per mesh; each needs its own
   `rechamber_ads` gun clip: add it to `boltcap.GUNS` / `boltnear.GUNS` / `vmcam.BOLT`).
3. ONE scoped rifle (bolt cycle + reload behind the scope), report before doing the rest.
Left as is: the Gewehrgranate (no aim at all - a later decision).

## Decisions for the user
* The bolt's visible stroke while aiming is 54-61 % of the real one (the cap). Longer = bigger in the view
  (`boltcap.py --near 2.0`), shorter = smaller.
* Mosin / Enfield handle lift is the retail 54 / 48 deg (real 90 / about 60): raise it in the aimed clip as on the
  Springfield? It brings the knob nearer the centre box.
* Everything here is STAGED (assets + engine branch); nothing is in the mod tree or the fixes pak.

## The recoil: NOT held in a bolt cycle - a correction of this lane's earlier report
`tools/ftrack.py` (engine front-sight track against the clip's own offline track, per clip frame), Kar98 A, run rb14:
the shot's recoil peaks at 2.93 deg, 0.96 deg of it is left when the bolt clip starts (0.25 s after the shot) and it
keeps recovering smoothly THROUGH the clip - 0.62 deg at clip frame 5, 0.33 at 13, 0.17 at 21, 0.05 at 34 (an
exponential, tau about 0.3 s: the recoil layer `s_recoil` of cg_view.c, the same curve as after any aimed shot).
Nothing is frozen and there is no step at the clip's start or end. The "0.7 deg held through the clip" in the previous
handover was wrong: most of it was the clip's own muzzle swing (fixed by the front-sight pivot), the rest this normal
recovery. bug-3597 (the rig solve held in the kicked state) is the EMPTIED-gun auto-reload path of the other lanes;
it does not occur in a rechamber. No engine change was made for it. If the first quarter second should sit closer to
the target, the lever is the recoil layer's recovery rate while aiming (a feel change for every aimed shot - a
decision, not a fix).

## Earlier findings that stand
* **Clip-end jitter, fixed in the cgame** (`ads-rifle-next` 18dc8b36; `CG_VMAdsTagRight`, new `CG_VMAdsBoltSolo`,
  `CG_VmTagHandoff`, probe on the off-hand tag): the gun hung on the travelling hand's tag for the whole aimed bolt
  clip and wobbled about 1 deg between clip frames during the reach and the return. bug-3630.
* The hand was in the box because of the GRIP (knob deep in the palm): `knob_off`. bug-3631.
* Break-off (rb10): fire does not interrupt a Kar98 reload, switch puts the rifle away cleanly, sprint continues.
  Hip reload lens fix (bug-3451) holds in five stances (rb11). **Gewehrgranate has no aim at all** (no sight row, no
  `kar98mortar_charge` row): no aimed rows staged, left as a later decision.

## Tools (this lane's, `tools/`)
* `boltphys.py <gun>[,<gun>]` (from `assets/`): `--set ease= | back= | roll= | fskeep= | hold=a,b,c,d`, `--rc k=v`, `--scale`.
* `rpart.py <sight gun> <aim.skc> "<clip>|rechamber"`: OFFLINE box cover per frame by surface; prints **hands max / the
  gun's own surfaces max**; `--track` = signed front-sight elevation per frame; `--sheet --zoom`. Offline under-reads
  the rifle's own body against the engine - use it for the hands figure and for sweeps.
* `ftrack.py <run> <tag> <sight gun> <aim.skc> "<clip>|rechamber"`: engine front sight per clip frame, clip alone, residual.
* `run_rifle.py`: parts `bolt`, `bolt2`, `reload`, `empty`, `hipreload` (`--hipall`), `breakfire / breakswitch /
  breaksprint`, `stills`; `--steady` = breath and sway off (a figure of the clip alone); `--yaw 172` = light wall.
* `rbox.py <run> [tag] --dump --zoom=<dir> --json=`: engine box per frame, where the cover sits, sight line, front sight
  (first frames / from 0.26 s in). **The settled-aim reference is now the UNION of the eight frames before the first
  mark** (was `mean > 0.3` of six: the same pose read 3-19 % "aim covers" between captures and the rifle's own breathing
  counted as cover). Other lanes: the same weakness is in `../tools/centrebox.py`'s settled-aim mask - take the union
  of the settled window, or capture with breath / sway off.
* **New in the fourth stretch:** `staged.py` (import it first: the offline tools then read the staged tiks / gun clips
  under `assets/` as loose files - no overlay pk3 needed); `boltnear.py <gun>[,..] [--anim rechamber_ads] [--clip ..
  --offhand lo,hi]` (how near the bolt comes to the eye, its screen bounding box, per frame); `boltcap.py <guns>
  [--near 2.5]` (writes the aim-only gun clip + the staged tik with `rechamber_ads`; then re-run `nosmoke.py` for the
  measure tiks and `boltphys.py`); `gripx.py` (grip variants side by side, textured), `gripsweep.py` (hands' box
  maximum per `knob_off`); `stances.py` (stance sheet); `rpart.py --cols --frames a:b`.
  `boltphys.py` recipe keys: `knob_off` tuple or {frame: tuple}, `grip_rot` (deg about the knob), `finger_s` (curl
  scale per finger joint), `grip_pin` (absolute hand attitude in the gun frame - tried, unused).
  `rbox.py` prints `HANDS (skin) max` first; an `empty` capture is measured from 26 frames after the last shot.
  `mkov_rifle.py --measure`: a measure tik replaces the staged tik of the same path (it must carry the same rows).
  Build the cgame from Git-Bash with DASH switches: `cmake --build .cmake --config Release --target cgame -- -m:4 -v:m`.
* `riflereload.py`, `rows_rifle.py`, `mkov_rifle.py`, `rsheet.py`, `rgif.py`, `rgif2.py` (panels side by side), `clipinfo.py`.
* Engine run: `set ADS_RUNS=G:/mohaa-adsanim2/runs`; `python tools/mkov_rifle.py G:\mohaa-adsanim2\ov_x.pk3 --measure`;
  `python tools/run_rifle.py <id> --overlay G:\mohaa-adsanim2\ov_x.pk3 --cgame cgame_rifle3 --yaw 172 --guns kar98
  --parts bolt2 --stances stand,crouch,prone,standL,standR,braced --set "set vss_draw 0"`.

## Shared tool, changed with the coordinator's leave
`../tools/coverage.py`: an unknown command (`--help`) printed nothing and ran `build` - it now prints the usage and
exits (`elif cmd == 'build'`). The line-476 crash was already fixed by the owner; `--lane rifles build` works and
writes `rifles/coverage.md`. Still open there: `scan` reads a bolt capture's shot recoil as `edge` and a reload's `end`
as 2.5 where rbox reads 0.03, so this lane's `ok` flags stay false whatever the clip does.

## Files
`assets/` staged view clips + `*_phys.json`, gun clips `models/weapons/<dir>/*_ads.skc` + `*_cap.json`, staged tiks
`models/weapons/{kar98,springfield_unscoped,mosin_nagant_rifle,enfield}.tik` (released tik + the `rechamber_ads` row;
regenerate with `boltcap.py` when the released tik changes), `models/player/base/fps_anims_rifle.txt`;
`coverage_status.json`, `coverage.md`; `evidence/`. Runs `G:\mohaa-adsanim2\runs`: ra1-ra7, rb1-rb15 earlier stretches
(rb14 = locked cycles with the full stroke, rb15 = reload with locked bolt phases, both superseded); rb16 first capped
look; **rb17 = bolt cycles steady, rb18 = with sway (Springfield / Mosin / Enfield final), rb20 = Kar98 cycle final**;
rb19-rb22 Kar98 reload passes; **rb23 = Kar98 reload final, six stances**.
