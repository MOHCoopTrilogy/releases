# New guns from free CC models: Bren, MP 28, Panzerfaust (2026-11-09) - IN PROGRESS

Branches: root `newguns` (worktree `C:\hzm-newguns\root`, off main 2e4c862a), mod `newguns` (worktree `C:\hzm-newguns\mod`,
off hotfix-1.10.53 4811fcef). An engine branch `newguns-eng` off rel-1.10.38-engine c3020fe0 will be needed for the cgame tables
(sight rows, feed/loot icons, viewmodel prefix, modelanim tune). Nothing has been pushed, merged or deployed.
Template: `../fg42hd_2026-11-08` (the mesh fitted onto the shipped bones, a texture bake, sight rows, gen_skins, the Armory fit, viewer credits).

The Boys was **dropped** at the user's call ("If it's not there we don't need it"). The only CC models are two untextured low-poly
ones, which the user rejected, and the EA disc has no Boys model to convert.

## Sources (downloaded by the user; untrusted data, read with `python -I`, never committed)
| gun | model | licence | where |
|---|---|---|---|
| Bren | "Bren Mk1 LMG" - maximiliaanmaene, https://sketchfab.com/3d-models/df74f7e3720d469e8bf425407e7ddc34 | CC BY 4.0 | `H:\hzm_work\newguns\src\bren` (1 mesh 27.9k tris, 1 PBR set) |
| MP 28 | "MP-28" - BrendanStakenburg, https://sketchfab.com/3d-models/a8838ccaf87243cfa71a321092065d6a | CC BY 4.0 | `...\src\mp28` (530k tris; Dark Steel / Steel / Wood PBR) |
| Panzerfaust | "Panzerfaust 60" - marcusww, https://sketchfab.com/3d-models/bb5ac613b7b84c5384900bc64ee83ead | CC BY 4.0 | `...\src\panzerfaust` (two copies; use circle,d1-d4,patrone,pin,spring,tube1,в5) |

Previews: `tools/bl_preview.py` -> `H:\hzm_work\newguns\prev\preview_3guns.jpg`.

QA notes on the sources, to be fixed in the bake:
- The Bren's source mesh is pitched about 21 degrees (its object is called "Tilted"). Its barrel and flash hider are bare bright
  steel, which would read as chrome; tone them to the receiver's finish.
- The Panzerfaust's decals are **misspelt**: "Starker Feuerstahl" should be "Feuerstrahl". They must be painted out, or
  re-lettered correctly in the bake. Never ship the misspelling.
- The MP 28's magazine sits on the LEFT, like the Sten's.

## Names and ids (for the roster, gen_skins, and the engrave bench)
| id | tik (finishes: `<stem>_{gold,chrome,blued,bloody,camo_woodland,camo_winter,camo_desert}.tik`) | in-game name | Armory | class | donor skeleton / anims |
|---|---|---|---|---|---|
| 82 | `models/weapons/coop_bren.tik` | `Bren` | BREN MK I - .303 / LIGHT MG / 30 RD | heavy (bipod brace, overheat) | `uk_w_vickers` (Vickers-Berthier: also a .303 top-magazine LMG) |
| 83 | `models/weapons/coop_bergmann.tik` | `MP28` | MP 28 - 9MM / FULL-AUTO / 32 RD | smg | `sten` (left side magazine) |
| 84 | `models/weapons/coop_panzerfaust.tik` | `Panzerfaust` | PANZERFAUST 60 - ROCKET / SINGLE-SHOT | heavy, rocket | `panzerschreck` |
The MP 28's stem is `coop_bergmann`, NOT `coop_mp28`: check_mp_isolation treats every `coop_mp*` token as MP-only and
failed 72 engine/mod lines on the first name (2026-11-09).
Id 73 is a permanent hole: the 2026-08 Panzerfaust (bug-1907). Do not reuse it.

## Panzerfaust: what the code needs (research 2026-11-09)
- Clone `panzerschreck.tik` (`ammotype heavy`, `clipsize 1`, `firetype projectile`, the `initialiseItem` exec). Set `startammo 1` in
  every mode, `autoputaway 1`, `usenoammo 0`, and no reachable reload.
- **The likely cause of bug-1907 "doesn't shoot at all":** `coop_mod/player_torso.st` (~889-892) enters `ATTACK_BAZOOKA_PRIMARY`
  only for "Bazooka", "PIAT" and "Panzerschreck". Add "Panzerfaust" there, and to the AIM exclusions (~105) and `player_legs.st`
  (30, 113, 171, 227, 283).
- **Discard:** the engine never removes an empty weapon; `autoputaway` only holsters it, the way grenades work. So the discard is done
  by script. The `weaponstate.scr "ATTACK_BAZOOKA_PRIMARY"` hook waits for the fire to finish, then calls
  `itemhandler.scr::takePlayerWeapon`. It sets a used-up flag the way `officer.scr::coop_smoke_consume` does (bug-4005), so
  keyitems and respawn re-gives don't restore the tube.
- The engine's `cg_viewmodelanim.c:455-461` already maps "Panzerfaust" to the Panzerschreck viewmodel prefix.

## Roster checklist per gun (from the Lewis / DP-28 / double-barrel / FG42 HD passes)
`docs/tools/loadout_weapons.tsv` row -> `gen_loadout.py build/check`; `weapon_history.tsv` (id text plus a `credit:<id>` line)
-> `gen_weapon_viewer.py`; `gen_skins.py add <stem>` (7 finishes); the unlock and challenge (`challenges.scr`, `unlock_audit.py`);
`keyitems.scr` `coop_key_heavyModels` (Bren, Panzerfaust); `giveall.scr`; `buildmode_catalog`; Armory hero fit
(`armoryfix_2026-11-08/tools/armory_fit.py`); `docs/SKIN_CREDITS.md` "Weapon models (CC)", `hzm_credits.txt` and the
`credits/coop_cc_models.txt` in the wpnfix pak. Engine: `cg_adssights.h` rows, `cg_coopfeed_loot.h` (icon w_*),
`cg_modelanim.c` tune/alias, `cg_viewmodelanim.c` prefix, and optionally an `s_coopCalibers` row ("bren" was removed as dead
in 2026-08 and can come back).

## Status 2026-11-09 ~11:50 (first in-game pass, run ng3, private client G:\mohaa-newguns, m2l1 coop, Armory route)
Built and staged (wpnfix sources + mod worktree + engine worktree), gates: gen_loadout check EXACT (79 guns), gen_weapon_viewer 0 stale,
unlock_audit covers 79/79, check_mp_isolation = baseline (21 pass / 1 pre-existing fail), scrlint 938 clean. Offline renders good.
In game, first look, NOT ready:
- Bren: renders near-black in daylight (the fg42hd tone target, mean 33/255, is too dark for this mesh: re-tone); ADS view blocked by
  a dark mass (the ghost ring / eye placement: check the sight row in the engine log `ADSRIG`); reload holds the VB's magazine prop.
- MP 28: hip pose reads twisted / the gun points off-axis in the reload frames: check the Sten_SMG bone frame fit (vmview offline
  looked right, so compare against the engine's draw), and its tone.
- Panzerfaust: the tube's rear end sits at the camera at the hip (the Panzerschreck rig's eye is near the tube); the discard works
  (the weapon is gone after the shot). Needs its own hip placement / the leaf sight in view.
- The newguns-eng base (c3020fe0) logs `unknown anim command 'coop_loadout_idle'` for every player tik: the deployed mod expects a
  newer engine than this base - test exes should come from the current engine branch, or the base should be rebased.

## Reserved ranges (proposed to finishes2 via the coordinator, 2026-11-09)
| what | newguns uses | finishes2 should use |
|---|---|---|
| finish tik ranks (gen_skins) | 1210-1239 (in use: 1210-1230) | 1240 and up |
| coop_skinN rows (loadoutskins.scr) | up to 599 (in use: 574-588) | 600 and up |
| Armory roster ids | 82-84 (73 stays a hole) | 85 and up |
| finish slots (fids) | 1-7 only (the seven standard finishes; checked in loadoutskins.scr 2026-11-09) | 8-18 model variants, 40 and up = finishes2's new finishes |
| challenge ids | wpn_bren_v, wpn_mp28_v, wpn_panzerfaust_v, fin_bren_*, fin_mp28_*, fin_panzerfaust_* | - |
gen_skins asserts rank uniqueness only against what is on disk, so whichever branch merges second must re-run `gen_skins.py add`.

## Status 2026-11-09 ~12:25 (runs ng4-ng7 in game, nv1 viewer)
Corrections to the 11:50 notes: the MP 28 is fine (the twisted look was the Sten's own hold and reload tilt); the near-black guns are
m2l1's backlit spawn (the shipped StG 44 reads as black there too), not the sheets. The Bren and MP 28 sheets were still lifted
(steel x1.75 / x1.45: the VB's own sheet averages ~58/255).
- Bren: carried-MG heat works (HANDHEATHUD lines; table row "Bren" 2.8 on newguns-eng), firedelay 0.12 (500 rpm); ADS solves
  (ADSRIG) with the ghost ring around the blade, magazine to the right as on the real gun; relief 6 clamps at 4, set to 3. Reload
  carries its OWN magazine now (coop_bren_clip.tik on the VB clip prop's bones, torso aliases bren_reload* in the adopted
  anims_vickers.txt); the hand still lands on the VB's well (4.7 u ahead): retargeted hands are next.
- Panzerfaust: fires, warhead hides, the spent tube is taken (PZF_DISCARD). The rocket-class AIM exclusion now includes it (an aimed
  Panzerfaust showed no weapon at all, like the Panzerschreck would): its hip view is the aim view, warhead under the crosshair.
- Viewer (media/viewer_nv1.jpg): all three on the rack with history, credits, unlock line, 8 entries each.
Open: the viewer's locked "Progress" reads 0/450, 0/550, 0/350 although unlockprog_gen says 60 / 60 / 10 kills - the runtime
export (coop_loLkA<id>) is pointing at the wrong data; Armory hero framing (armory_fit) not run; MP Armory rows (blocked on mpid 34,
bug-10673); retargeted Bren reload hands; in-game stills need a lit map (m1l1 starts in the night truck ride).
Test runner: run_gun.py (Armory route, overlay = every mod file changed since hotfix-1.10.53), run_viewer.py.

## Status 2026-11-09 ~17:45 (finishing pass: reload hands, rack numbers, finishes2 coverage, stills)
- **Merged in**: root `main` + `finishes2-tools`; mod `hotfix-1.10.53` + `finishes2`; engine `rel-1.10.38-engine` (the v1.10.67
  view-weapon projection / near-plane fix). Generated files regenerated, not hand-merged.
- **Bren reload hands** (tools/bren_hands.py): the VB's three view reload clips with the RIGHT hand moved (-5.65, 0.3, 1.2) gun
  units onto the Bren's magazine (eased in off the grip f3-12, out to the cocking handle after the insert), right arm re-solved
  by the ADS lanes' two-bone IK, tags untouched. Rows `coopr_bren_reload`, `cv_bren_reload_s`, `cv_bren_reload_m` in an ADOPTED
  `fps_anims_mg.txt` (wpnfix, stress-pak base pinned). build_bren_clip.py re-places the prop against the new _s clip (reproduces
  byte-identically). Offline clip check (tools/clipcheck.py): 0 vertices nearer than the weapon near plane on all 3 clips; the
  right hand's nearest approach 6.8 u (VB 8.1 u; hand_survey NEAR is 6). In game the hand is large at the start of the pull.
- **Rack unlock numbers**: the viewer's "0/450" was a STALE archived coop_uiN<i>: the 3 unlock challenges were added as Service
  Record rows without regenerating the SR (boot SELFTEST FAIL 450 vs 447), and every later row moved up by 3. gen_service_record.py
  re-run (450 rows, stamp 554288dc, reward names added); ng8 boots SELFTEST OK. The numbers are right after the first export
  (chal_flush, <= 30 s after joining) - the same rule as every other gun.
- **finishes2 coverage**: tools/fs2_ng.py runs fs2_build / fs2_finish2 against a PRIVATE copy `H:\hzm_work\newgunss2_build`
  (finishes2's own staging untouched): 910 existing rows byte-identical, +39 (fids 40-52, ranks 2910-2948), pak 199.3 MB sha256
  2b76b445. Generators run with `HZM_BASE_MOD=<base mod> HZM_FS2_PAK=<that pak> HZM_FS2_BUILD=<that dir> HZM_MOD=<mod worktree>`.
- **Stills** (m5l1a, overcast daylight, 3440x1440, GL2): media/ng8/ (+ sheet_bren.jpg, sheet_mp28_pzf.jpg). Bren / MP 28 /
  Panzerfaust ADS sights aligned (ADSSIGHT res < 0.3 mrad); Panzerfaust fires and the tube is discarded (PZF_DISCARD).
- **Merge order**: finishes2 first, then newguns. Then in the base checkout: replace finishes2's pak with
  `H:\hzm_work\newgunss2_build\zzzzzzzzzz_coop_finishes_hd.pk3` (or re-run fs2_ng.py-equivalent in finishes2's staging),
  `gen_wpnfix_pak.py build`, and the 5-step generator sequence (gen_skins check, finish_challenges --emit, gen_loadout build,
  gen_weapon_viewer build, gen_skinbase). Engine: merge newguns-eng (cgame/game unchanged since 8f10e4a2).
- Open: MP Armory rows (mpid 34, bug-10673); Armory hero framing (armory_fit) not run; the MP 28's ADS shows the Sten's support
  sleeve over the left third of the view (Sten parity).

## Status 2026-11-09 ~18:50 (coordinator QA pass: Bren reload / Bren ADS / MP 28 aim + reload / third person)
- **Bren reload** (tools/bren_reload2.py, keys bren_reload2_keys.json): on top of the magazine retarget, the GUN is re-posed for the
  whole reload (rigid transform about the left hand: pitch 15 down, roll 35 about the bore, 2 back, 1 right; eased in over the first
  ~12 frames and out at the end) and BOTH hands ride with it, arms re-solved by IK. The work (pull, pouch, insert) now happens low
  and right; the VB's arm that swept at the eye is gone. Offline coverage (engine rig, 21:9, hip fov): right hand <= 3.2 %, right
  sleeve <= 9.1 % of the screen on every frame (gate 15 %). Clip check: 0 vertices nearer than the weapon near plane on all three
  clips, nearest gun vertex 1.08 u (r_weaponznear 0.6).
- **Bren ADS**: the ADS picture was a dark block over the lower half whenever the gun had not just fired (ng11-ng16). Cause: the
  sight row put the eye on the ghost-ring line, 4 u behind the ring, which is INSIDE the source mesh's rear-sight housing.
  Fix (engine row, the Sten "virtual rear" precedent): rear point 0.6 u above the ring centre. Plus the sights moved 0.7 u
  further left of the magazine (build_bren.py SIGHT_DY, rows y -1.942 / -1.939): the magazine edge now starts ~110 px right of
  the blade at 3440 (was ~40). media/final/bren_ads_zoom_ng18.jpg.
- **Bren torso reloads**: `exit` commands remove the magazine prop and give the gun back to the main hand when a reload is cut
  short (anims_vickers.txt; a cut reload skipped `last`).
- **MP 28** (tools/mp28_ads.py, mp28_reload.py): its own aim pose `coopr_mp28_charge` (left hand under the magazine housing,
  elbow down: left sleeve 13.3 % -> 1.1 % of the screen) and its own hip reloads `coopr_mp28_reload[_empty]`,
  `cv_mp28_reload[_empty]_s/_m` (the gun held 70 % toward a steady reference pose and 18 deg lower instead of swinging up at the
  eye); aimed reloads keep the Sten's clips under `coopr_mp28_reload*_ads` / `cv_mp28_*_ads`. Adopted fps_anims_smg.txt (wpnfix).
- **Third person**: stills with cg_cameradist 22 / cg_camerasideoffset 58 / cg_cameraheight 2, aimed (the gun shows).
- **Test runner** tools/run_cfg.py: NO pad script (user playing): console steps exec'd over loopback rcon (net_ip 127.0.0.1,
  IPv4 only), waits in ms (cmd.c), in_gamepad 0 / in_joystick 0, harness_window no-activate policy, muted, 3440x1440 ultrawide.
- Stills: media/final/ (ng18 = all but the Bren reload; ng19 = the Bren reload with the shipped clips; ng19's weather is darker).
