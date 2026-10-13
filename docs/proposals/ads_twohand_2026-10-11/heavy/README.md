# HEAVY lane (MGs / shotgun) - HANDOVER, 2026-10-12 night (second agent). Read this first.

Lane of the aimed-animation work: the `## mg` and `## heavy` rows of `../coverage.md`. The method is the pistol
lane's (`../README.md` top section); this file says what is different here, what is done and what is next.
**Everything is STAGED** in this folder and on engine branch `ads-heavy-next` (worktree
`C:\mohaa-coop-dev\openmohaa-hzm-ads-heavy`, build dir `.cmake` - NOT `build`). Nothing is in the mod tree, the fixes
pak or a live install.

## State by numbered point of the brief
| point | state |
|---|---|
| (1) aim poses, support hand as at the hip: BAR, DP-28, Vickers-Berthier, Breda | **done** (ha1 / ha2), `evidence/<gun>_aimhand_*.jpg` |
| (2) + (2b) BAR aimed reload, loaded + empty, all six stances incl. a braced variant | **done to the three rules - see "BAR" for the numbers and the honest weak points** |
| BAR skin lift + magazine prop tone | **staged** (`tools/barskin.py`, `tools/clipskin.py`) - see "Skins" for the shipping note |
| (3) MP44 | **done to the three rules, six stances, loaded + empty** - see "StG 44" |
| (3) FG42 (sight row first), DP-28 | **not started** (FG42: no `fg42` entry in `sights.json`, no `fg42_charge` row) |
| (4) Breda, Vickers, portable .30 cal / MG42 | **not started**; two findings from run hc9 / hc10 below |
| (5) shotgun: bead sight, shells, pump | **not started** |
| launchers | not re-checked by a run; Torso AIM excludes them per the matrix - N/A |

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
* **Box numbers are taken with `--set "set cg_adsSway 0" --set "set cg_weaponBreath 0"` and `boxeng.py <id> bar --align 6`**
  (bug-3619): with sway / breath on the AIM itself wanders 15-45 px during a 4 s reload and reads 3-7 % by itself;
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

## BAR - `tools/heavybake.py bar` (+ `--braced`), `tools/patch_tik_h.py bar`
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

## StG 44 - `tools/heavybake.py mp44` (+ `--braced`), `tools/patch_tik_h.py mp44`
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

## Next, in the brief's order
3. FG42: sight row first - `sights.json` has no `fg42` entry (F = front post tip, R = rear aperture, picked from the
   mesh as the other 70 were: `../../ironsights_2026-09-28`, then `engine/gen_sights_header.py` -> `cg_adssights.h` on
   `ads-heavy-next`, rebuild) and there is no `fg42_charge` aim row either (`handpose.py` from `fg42_idle`); its
   reload is 71 frames, prop `fg42clip` on the off-hand tag f28-56, side magazine (check from the eye whether it shows
   without a cant). DP-28: the pan is in the sight picture, the gun comes down for it; prop `coop_dp28_clip` f29-45,
   97 frames. A new gun = a `heavybake` entry (copy MP44's): `clipinfo.py <row> <gun clip>` and `gunmove.py <tik> reload`
   give the retail timeline, the bolt channel and the handle point; `heavylib.py <prefix> <points>` where they sit at
   the aim; then `hktry.py <gun> loaded none x.jpg --box "<k=v;...>"` until the box passes offline, THEN the engine.
4. Breda, Vickers, portable .30 cal / MG42 (belt: cover up, belt, cover down, charge). M1919 needs its sight row.
5. Shotgun: sight delta 18-20 mrad + brass bead (`../../ads_bolt_2026-10-04/README.md` 8.5), shells one at a time,
   pump after the last; aimed fire plays `viewmodelanim charge`, so the pump between aimed shots shows no hand motion
   today - a `shotgun_cycle_ads` row (cgame per-shot cycle hook of ads-next 4b6be659).
Also open for the BAR: stock-mesh empty reload, break-offs, a slower return.

Runs: ha1 / ha2 (aim poses), hb1-hb9 (predecessor's BAR iterations), hs / hn (skin), hc1-hc10 (2b: stances, braced,
variants, finishes), hd1-hd3 (final BAR clips, settle diagnostics), he1-he7 (StG 44; he6 / he7 final), hf1 (StG 44 aim
stills), hf2 (strapped variant). `centrebox.json` keys are GUN names (`bar`, `bar_empty`, ...) as coverage.py reads
them; `python ../tools/coverage.py --lane heavy build` writes the lane preview `heavy/coverage.md` (BAR and StG 44: DONE).
Bugs this session: 3619-3623, 3646-3649.
