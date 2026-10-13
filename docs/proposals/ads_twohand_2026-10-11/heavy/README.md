# HEAVY lane (MGs / shotgun) - HANDOVER, 2026-10-12 late night (third agent). Read this first.

Lane of the aimed-animation work: the `## mg` and `## heavy` rows of `../coverage.md`. The method is the pistol
lane's (`../README.md` top section); this file says what is different here, what is done and what is next.
**Everything is STAGED** in this folder and on engine branch `ads-heavy-next` (worktree
`C:\mohaa-coop-dev\openmohaa-hzm-ads-heavy`, build dir `.cmake` - NOT `build`). Nothing is in the mod tree, the fixes
pak or a live install. Run ids used: ha hb hc hd he hf hn hs (earlier), hg1-hg3, hh1-hh9, hi1, hi2, hj1, hj2 (third agent), **hj3-hj5 (fourth agent)** -
never reuse one; next free: `hj6`.

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
| belt-feds (M1919 portable, Breda, Vickers, MG42), shotgun reload, FG 42 hip reload | **not started** |

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

## FG 42 - what the still shows
`evidence/mp44_gold_and_fg42_aim_hh6_hh9.jpg`: top row the gold StG 44's emptied aimed reload (same mesh, plays the
new clips); bottom row the FG 42 with the aim key held, sway on - **the scope picture** (`zoom 20`, lens surface; the
scopes system draws it), through 20 rounds and the whole reload: the scope stays up, no viewmodel is drawn, the reload
passes unseen. Nothing was staged for an iron-sight aim. To do: its HIP reload on the model (the mesh is one static
surface set on one bone - a charging handle needs its own bone first, as the SMG lane added one to the MP40); the
reload-while-scoped design follows the rifle lane's sample.

## Engine branch `ads-heavy-next` (this lane's cgame)
* ef1e7934: a braced aimed reload / bolt picks the hands row `<row>_adsb` when fps_anims has it (`CG_CoopBrace() > 0.5`,
  the recipe of `../../ads_bolt_2026-10-04/engine/apply_adsbrace.py`); no row = `<row>_ads` as before.
* 01e2460b: merge of ads-next 191f1879 (ADSSETTLE diagnostic, `cg_adsRigSettle`, default off - no behaviour change).
* Test DLLs in `G:\mohaa-adsanim4\cgames`: `cgame_heavy1` (ef1e7934), **`cgame_heavy2` (01e2460b, current)**.

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
2. FG 42 hip reload on the model (above).
3. Belt-feds: M1919 portable first (sight row; bug-3622), Breda, Vickers, MG42.
4. Shotgun reload: shells one at a time on target or just under the box, break off on fire, pump only when the chamber
   was empty; aimed fire plays `viewmodelanim charge`, so a `shotgun_cycle_ads` row is needed for the pump between
   aimed shots (cgame per-shot cycle hook of ads-next 4b6be659).
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
Bugs: 3619-3623, 3646-3649 (second agent); 3667-3676, 3681 (third agent).
Tools added by the third agent: `boxeng.py --sway`, `swayshow.py`, `run_h.py --tail / --brk / --hipdemo / --hold / --rel`,
`heavybake.py --hip` + `feed='top'`, `patch_tik_h.py` `more_paths` for the BAR, `hip=True`, the `dp28` set.
