# HEAVY lane (MGs / shotgun) - HANDOVER, 2026-10-12 evening. Read this first.

Lane of the aimed-animation work: the `## mg` and `## heavy` rows of `../coverage.md`. The method is the pistol
lane's (`../README.md` top section); this file only says what is different here, what is done and what is next.
**Everything is STAGED** in this folder and on engine branch `ads-heavy-next` (no cgame change yet: the lane cgame
`cgame_heavy0` is ads-next 94bb3dca rebuilt). Nothing is in the mod tree, the fixes pak or a live install.

## State by numbered point of the brief
| point | state |
|---|---|
| (1) aim poses with the support hand as at the hip: BAR, DP-28, Vickers-Berthier, Breda | **done**, runs ha1 (before) / ha2 (after), 8 stances incl. braced, sight line 0.00 deg. `evidence/<gun>_aimhand_before_after.jpg`, `<gun>_aimhand_stances_ha2.jpg` |
| (2) BAR aimed reload to the three rules, loaded + empty | **built and run standing; see "BAR" below for the numbers and the honest weak points**. Stances run = see the table there |
| BAR skin "slightly brighter" (user 2026-10-12) | **staged**, `tools/barskin.py`, sheet `evidence/bar_skin_lift_before_after.jpg` |
| (3) MP44, FG42 (sight row first), DP-28 | **not started** |
| (4) Breda, Vickers, portable .30 cal / MG42 | **not started** (aim poses of Breda / Vickers done under (1)) |
| (5) shotgun: bead sight, shells, pump | **not started** |
| launchers (bazooka, Panzerschreck, PIAT) | not re-checked by a run; `player_Torso.st` AIM excludes them per the matrix - leave N/A |

## How this lane runs (all tools in `tools/`, run from `assets/` unless said)
* `hv.py` paths + guns; `hv.lib()` = hold_bake / rig / vmcam with the bolt tools importable. The pistol lane's tools
  are used as a LIBRARY; those that hard-code `G:/mohaa-adsanim/runs` go through `python ../tools/sh.py <tool> args`
  (swaps the literal for `G:/mohaa-adsanim4/runs` at load, no copy).
* Engine runs: `python tools/run_h.py <id> --overlay <abs pk3> --cgame cgame_heavy0 --guns bar --parts ...` = the
  shared run_2h.py repointed to `G:\mohaa-adsanim4`, owner `adsanim4`, net_port 12598. Lane extras: `--map m4l1
  --spot x,y,z,yaw` (night map at its player start: -3904,-6120,-456,45), `--pitch 8.5` (start the view lower: 20
  rounds of automatic fire walk it up 8.5 deg and the box ends on the dark beam, where a dark gun cannot be measured).
  One game at a time in the copy; a session is 2-6 min. Log `SCRATCH/adsheavy/run.log`, frames `G:/mohaa-adsanim4/runs/<id>/`.
* Overlay: `python ../tools/stage_rows.py` (fps_anims_mg / _shotgun = the RELEASED fixes-pak copy + the declarative
  EDITS in that file - both files are this lane's), then `python ../tools/mkov_h.py <out.pk3> [--skip textures] [--before]`
  (plumbing `SCRATCH/adsheavy/ovbase_1021.pk3` + everything under `assets/`).
* Offline first: `python ../../tools/offbox.py bar <aim.skc> "<clip.skc>|<gun anim>" --w 320 [--sheet x.jpg]` with
  `IRONSIGHT_EXTRA_PAKS=<overlay>` for staged gun rows; `python ../tools/trypose.py bar out.jpg roll=32,pitch=4.6,mv=3/0.4/0`
  tries gun work poses (eye view, box cover); `heavylib.py bar <gun pt> ...` prints where points of the gun sit in the
  aim camera frame (deg below / left of the sight line).
* Engine measure: `python tools/boxeng.py <id> --dump`. NOT the shared centrebox.py for automatic guns: its baseline
  is the aim just before the reload, which after a burst has not recovered from the recoil (the BAR then reads
  4-5 % "extra" for every frame after it is back). boxeng compares with the settled aim at the END of the reload
  capture, as offbox does. The first ~13 capture frames of an EMPTIED gun are the last shot's kick and smoke.
* Sheets / GIFs: `tools/fsheet.py <id> demo a:b:step out.jpg --crop 240,120,1040,720`; `python tools/sh.py dgif <id> demo out.gif
  --frames a:b:3 --w 400 --crop 240,120,1040,720 --box`, then `python ../tools/gifsheet.py out.gif sheet.jpg a:b:1` and LOOK.
* Status: `tools/cov_h.py scan <id>` -> `coverage_status.json` (same schema as the pistol lane's). **`../tools/coverage.py`
  does not know this lane yet** (LANES has 'rifles' and 'smg' only and gives mg + heavy to 'smg') - reported, bug-3591.
* Bugs: `python tools/buglog_add.py entries.json` appends to `.wolf/buglog.json` without rewriting it (bug-3588..3591 are this lane's).

## (1) Aim poses - `tools/handpose.py`
All four `<prefix>_charge` rows borrowed the BAR aim clip `viewmodel/bar_stand00.skc`: the support hand hung open
1.5-5 u under the gun (on the Vickers visible from the eye as an empty palm). New one-frame clips
`viewmodel/<dir>/coop_<prefix>_ads_hand.skc` = the same aim (trunk, eye, firing arm, weapon tag untouched) with the
left hand in the hip idle's hand-to-gun relation. Open: `bar_charge` is also the aim row of the M1919 / MG42 / Lewis
(prefix `bar`): they now get the BAR-forearm hand on other meshes - not looked at. `tools/posecmp.py` / `pair_h.py` =
the side views that prove what the hand holds (from the eye the change is mostly hidden behind the gun).

## (2) BAR aimed reload - `tools/heavybake.py bar` (approach approved by the user via the coordinator, 2026-10-12)
Facts that shape it (`heavylib.py bar ...`): at the cheek weld the stock hides the left-side operating handle
(14 deg below, 9 deg left of the sight line, behind the comb) and the magazine well is 18-36 deg below the sight
line - the frame edge is 26 deg. Nothing of the work can be seen on the sights, and a hand BEHIND the knob ends the
5.75 u pull 4 u from the eye. A strong cant (55-90 deg) swings the firing hand into the lens. So:
* **Gun**: the support hand leaving lets the muzzle SAG 4.6 deg about the butt (gunphys class `bar`: 9 kg, 1.25 Hz
  one-handed, damping 0.62 - physics, `dip_pivot` = the butt 10.8 u behind the eye); the firing hand holds it in a
  WORK pose on top of that (`gun_abs`: canted 32 deg top-right about the butt, yawed 3 deg, let 3 u forward out of
  the cheek weld), `dip_after` puts the spring motion on top. Actions `lg_*` (magazine tug / free / in / slap,
  handle grab / back / stop / forward, hand on) are defined in heavybake.py for a shouldered long gun. One-sided
  clamp: the gun never rides ABOVE its aim (the return overshoot put 5 % of gun into the box).
* **Hands**: firing hand fixed on the grip. Left hand keyed (`left_path`): forearm -> the seated magazine (retail
  hand-to-gun relation of frame 15) -> stripped 5.8 u down the well's axis -> swung out LEFT through the bottom-left
  of the view (the magazine is SEEN there, out f24-27 and in f36-39; the well itself is below the frame) -> pouch ->
  back, seated f46, palm slap f53 -> (EMPTY only) across from the left onto the knob (`gunpt` key, wrist straight
  left of the knob, fingers closed round it), hauled back f66-69, run forward f71-73 -> forearm.
* **Gun side**: `models/weapons/bar_lmg/coop_reload_ads_empty.skc` = the retail gun reload with `bolt pos` y keyed
  0 -> 11.06 -> 0 by the same `bolt_u()` the hand follows. `tools/patch_tik_h.py bar` stages bar.tik + its 7 finishes
  with `reload_ads_empty` (that clip, retail sound) and `reload_ads_loaded` (retail gun clip, sound
  `bar_snd_reload_loaded` = BARReload1.wav faded out before the handle, tik-local aliascache). Hands rows:
  `bar_reload_ads` (rounds left: magazine only - an open-bolt gun still cocked), `bar_reload_empty` (hip: retail
  clip, so cgame finds the next one), `bar_reload_empty_ads`. Frames follow the retail sound (out f12-16, in f40-44,
  click f52, handle f67-73) and the server's prop window (bar_clip on tag_weapon_left f15-50, gun Clip hidden f18-46).

Numbers and evidence: see the table at the end of this file (filled from the last runs).

Known weak points (seen in playback - say them, do not hide them):
* The magazine exchange at the WELL is below the frame; what is seen is the magazine in the hand going out and
  coming in bottom-left. The retail prop `models/ammo/bar_clip.tik` is light grey against the dark S93 gun.
* The handle hand is a closed fist against the left of the receiver, about a quarter of the screen wide at the end
  of the pull (it is 7 u from the eye); the knob itself cannot be made out on the dark gun, so "fingers round the
  knob" was judged on offline renders only. The bolt bone moves (gun clip) but was not verified in a zoomed engine crop.
* The firing hand / wrist shows under the gun in the work pose (pink at the bottom edge) - it is the hand on the grip.
* Only the S93-mesh BAR (bar.tik + finishes). `bar_bar1918a*` / `bar_pabar` (stock mesh, other handle point), the
  Lewis, M1919 and MG42 play their own `coopr_*` hip clips in an aimed reload - untouched.
* Break-off states (fire / switch / sprint during the reload) not run. Hip reload untouched (retail mime pull).

## BAR skin - `tools/barskin.py`
Cause of "very dark": the TEXTURE (S93_bar mean 19 / 255; on screen the gun read 9 where DP-28 / Breda read 44-47),
one plain lightingSpherical stage. Lift = a monotone luminance curve (19 -> 44), chroma grown only with gain ** 0.25
(a plain multiply turned the crushed yellow darks mustard / camo - first try, rejected on the sheet). Both files per
sheet are staged: `.dds` (the weapon-HD pak `zzzzzzzzzz_coop_hd_m3l1a.pk3` member, what the engine shows) and `.tga`
(`zzzzz_xw_weapons.pk3`, shown without the HD pak). Read by bar.tik only (one tik for first person, world, pickup,
Armory) and multiplied by the blued / chrome / gold finishes; bloody / camo finishes have their own JPGs (untouched,
so they may now read DARKER than the base gun - not checked). **Shipping: the lifted .dds must replace the HD pak's
member or sort above it, or that pak hides it.**

## Next, in the brief's order
1. BAR: re-read the weak points above with the lifted skin on (the knob shows then); stock-mesh BAR variants
   (`heavybake` needs a second gun entry: handle point from `gunview.py models/weapons/bar_bar1918a.tik`); break-offs.
2. MP44 (shipped clip: 4.5 deg drift, cocking hand out of view), FG42 (no sight row: add it to the cgame sight table
   first - that is this lane's cgame change), DP-28 (pan off / on, charge) - the same reasoning (sag + work pose)
   applies wherever the control sits out of view at the cheek weld; say which in the report.
3. Breda, Vickers, portable .30 cal / MG42 (belt: cover up, belt in, cover down, charge).
4. Shotgun: sight delta 18-20 mrad + brass bead (`../../ads_bolt_2026-10-04/README.md` 8.5), shells one at a time,
   pump after the last; aimed fire plays `viewmodelanim charge` (player_Torso.st ATTACK_SHOTGUN_PRIMARY_AIM), so the
   pump between aimed shots shows NO hand motion today - it needs a `shotgun_cycle_ads` row (cgame per-shot cycle hook).

## BAR numbers (final clips: loaded a8221414, empty f668a1ff, gun clip 4a5edd0c; cgame_heavy0; yaw 165 light wall)
| what | run | engine box extra vs the settled aim (`boxeng.py`) | offline box (`offbox.py`, every frame) | sight line | evidence |
|---|---|---|---|---|---|
| loaded, standing | hb7 | max 1.4 %, 0 of 240 frames over 2 % | 0.5 % | leaves 6.2 deg (declared sag + cant), back to 0.01 deg | `evidence/bar_reload_aimed_loaded.gif` (70 frames, 1.2 MB) |
| loaded: crouch, prone, lean L, lean R, braced | hb8 | not measured (sparse capture, dark backdrop) | - | 6.1-6.2 deg, back to 0.02 deg, pose factor 1.00 | `evidence/bar_reload_aimed_loaded_stances_hb8.jpg` |
| EMPTY, standing | hb9 | f287-296: the last shot's kick (21 % -> 2 %); work phase 0 %; **2-3 % for 16 capture frames (0.26 s) at the return** | 0.5 % | back to 0.00 deg | `evidence/bar_reload_aimed_empty.gif` (68 frames, 1.2 MB) |

The 2-3 % of the EMPTY return is not the clip (the loaded clip has the same return and reads 1.4 %): an emptied gun
starts its reload by itself in the middle of the last shot's recoil; the ADS rig solve is HELD while the client-only
aimed clip plays (ads-next 940420bf), so it is held in the kicked state, the whole reload plays about 0.6 deg high and
the gun sinks 15 px to the true aim after the clip ends (crops: capture f462 / f470 against f520). A general cgame
point for every emptied-gun aimed reload (pistols too) - reported, bug-3597; NOT changed on `ads-heavy-next`.
Not done for the BAR: EMPTY in the other stances; a braced variant (the braced gun sags the full 4.6 deg although the
rest carries it - wants the `_adsb` reduction of `../../ads_bolt_2026-10-04/tools/bake_class.py`); break-offs.
Runs of the day: ha1 / ha2 (aim poses), hb1-hb9 (BAR reload iterations; hb7 / hb8 / hb9 are the final clips),
hs1 / hs3 and hn1 / hn3 (skin before / after, day m3l2 and night m4l1; hs2 / hn2 = the rejected first lift).
