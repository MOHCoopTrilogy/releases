# Bren Mk I - held from v1.10.68; the sight redo plan

The MP 28 and the Panzerfaust 60 ship in v1.10.68. The Bren is switched off (not deleted) until its iron sights are rebuilt.

## How it is switched off (and back on)
`tools/bren_off.py` (run with `on` to reverse; nothing else is needed for the switch itself):
- `docs/tools/loadout_weapons.tsv` row 82 is prefixed `#OFF ` - the Armory tile and pages, loadouts, lktabs, stats, the weapon
  viewer and the generated unlock roster all drop it.
- `coop_mod/challenges.scr`: the unlock challenge `wpn_bren_v` and the kill-stat token `coop_bren -> wid "bren"` are commented
  out AND their tokens renamed `chal_def_HELD` / `containsText_HELD` (the generators' regexes do not skip `//` comments: a
  plain comment left the row in the Service Record count, 450 baked vs 449 live).
- `coop_mod/loadoutroster.scr`: the hand-written `case "82"` is commented (armory_unlocks / unlock_audit read it).
- finishes2: the private staging (`H:\hzm_work\newguns\fs2_build`) has the Bren's sheet and 13 variant tiks moved to
  `held_bren\` (`fs2_tools/fs2_drop_bren.py`); to restore, move them back, merge `held_bren\state.json` into `state.json`,
  `fs2_ng.py pack`.
- Kept as they are (inert while the gun cannot be obtained): the wpnfix assets (mesh, clips, hands rows, tiks, finishes 1-7),
  the engine rows (cg_adssights.h, viewmodel prefix, loot icon, heat), anims_vickers.txt rows, giveall / itemhandler / class
  lists, credits, weapon_history.tsv.
- After switching back on: the five-step generator sequence, then gen_service_record (+1 row: re-check the SELFTEST stamp).

## Why it is held
QA rounds ng11-ng27 (media/final*, buglog 10720-10738). The hip and reload work is done (reload re-posed low and right, the reach
starts under the gun, aimed reload rows, magazine prop in the hand, exit cleanup). The sight picture is not:
1. **The model's sights are not a Bren's.** The front blade sits 1.24 u left of the magazine centre line, but the rear sight is
   a source "aperture leaf" (1 u x 1.8 u plate) on the same line, plus a separate drum ring at the magazine base on the RIGHT.
   A real Bren's rear drum and aperture leaf and its front blade are all offset LEFT of the magazine (about 1.4 in), and you aim
   along that offset line with the magazine to the right.
2. **The eye cannot be put at a real eye relief.** In game the rig leaves the eye ~1 u behind the rear sight point whatever the
   row's relief says (the along-axis move is clamped to +-4 u, and the VB aim pose `vickers_charge` = `bar_stand00.skc` holds the
   cheek far forward). So any real rear sight fills the view (the leaf: ~75 % of the screen, "a pipe"), and a ring AT the rear
   point swings 10+ deg with the rig's residual (ADSSIGHT R px +-300-400 while F stays centred).
3. The v1.10.68 stopgap (no leaf, a thin ring 3 u ahead on the sight line) reads acceptably but is not a Bren sight.

## The redo
### A. Sights rebuilt on the model (build_bren.py + a new `bren_sights.py`)
- Measure the real geometry from references: line-of-sight offset left of the bore/magazine (~1.4 in = ~1.4 u at the mod's
  scale), rear drum + aperture leaf at the rear of the body on the LEFT, front blade on its bracket on the LEFT of the barrel.
- Rebuild, in the gun frame, as proper parts on the `vickers` bone: (1) a rear aperture leaf - thin plate (<= 0.08 u), outer
  ~0.45 u, hole ~0.12 u, standing on the drum; (2) the drum; (3) the front blade and its bracket, both at the same left offset.
  Remove the source's aperture leaf (part 34 rear end), the misplaced drum ring at the magazine base, the stopgap ring, and the
  `SIGHT_DY` hack (the parts are modelled where they belong instead of shifted).
- One texture region of the existing sheet (receiver steel) for the new parts; both faces where seen edge-on.
- Regenerate the sight rows from the model (F = blade tip, R = aperture centre, `sight_r*.json`), no hand numbers.

### B. The eye behind the real aperture at a proper distance
- The Bren needs its OWN aim pose instead of the BAR's: `coopr_bren_charge` (per-weapon row, `CoopPerWeaponReloadAnim`
  already resolves it), keyed like `mp28_ads.py` / `key_bolt.py`: the gun pulled back so the aperture sits 2.5-3.5 u in front
  of the eyes bone (a real aperture is used close: ~3 in), cheek on the butt, the left hand on the butt grip / the right on the
  pistol grip as on the real gun. Then the row's relief is reached without the +-4 u clamp, and the leaf reads as a soft ring:
  outer 0.45 u at 3 u = ~8.5 deg radius, ~1/3 of the 21:9 screen height; the hole is the target window.
- Target: ADSSIGHT R px within +-20 px of F (not +-300) - the aperture stays put; verify the rig residual for the new pose with
  `cg_adsSightDebug 1` before any stills.
- Aimed reload: keep `coopr_bren_reload_ads` (same clips) - it starts from the new aim pose, check the first 0.5 s for sweep.

### C. Verification (no stills until each passes)
1. Offline: the engine-calibrated render (vmcam.scene2 + the corr for the new charge pose) - post at the crosshair inside the
   hole, the ring 25-35 % of the screen height, the magazine wholly right of the sight line.
2. `clipcheck.py`: no vertices nearer than the weapon near plane in the charge pose and the aimed reload.
3. One in-game run (`run_cfg.py --only 82`, guard on, in_mouse 0, in_nograb 1, never activated): zoomed ADS before / after the
   first shots, a sway series (5 frames, 0.3 s apart) to show the ring stays put, aimed reload frames, hip reload sheet.
4. Gates: gen_loadout / gen_weapon_viewer / gen_skins check, unlock_audit, check_tik_surfaces, check_anim_aliases,
   check_mp_isolation, SELFTEST stamp after gen_service_record.

## Status 2026-11-09 ~21:50: DONE on newguns2 (root / mod `newguns2`, engine `newguns2-eng`) - the Bren is back ON
- **A. Sights on the model** (`tools/bren_sights.py`, called by `build_bren.py`): one line of sight y -1.94 / z -5.85 (gun frame:
  1.94 u = ~1.37 in left of the bore, over the source drum's centre, which was already there), level with the bore. Rear: the
  source drum (32/33) kept + its bracket onto the body, a sight ARM back to an APERTURE LEAF at x -9.60 (plate 0.06 thick, disc
  r 0.45, hole r 0.21, stem down to the arm). Front: a blade 0.10 wide between two ears on a base + strut into the barrel's left
  side. Dropped: source arm + leaf (34), aperture disc (49), blade / ears (55 / 16), the ring on the magazine catch (35), the
  `SIGHT_DY` shear and the floating ring. The carrying handle (2/3/8) is turned down to the right (it stood in the aperture's
  view, right of the post). New parts are planar-mapped into a 40-texel receiver-steel window of the sheet (one flat texel read
  as a black cut-out; a wrapped mapping drew a seam - both seen in game, nb2 / nb3).
- **Rows from the model**: `bren_ads.py row <engine>` rewrites the 8 `coop_bren*` rows of cg_adssights.h from `bren_sights.row()`
  (F = blade top, R = hole centre, relief 3); `gen_sight_alias` adds the 13 finishes2 variants.
- **B. Own aim pose** `coopr_bren_charge` = `coop_bren_ads.skc` (`bren_ads.py bake`): the rig's whole correction for the new row
  baked into bar_stand00 (the VB's pose had the aperture 3.42 u BEHIND the eye: rot 0.71 deg, move, relief +6.42 u); hands ride,
  arms by IK, no clamp. The engine's target on it is now 0 / 0 / 0 (aperture 3.00 u ahead of the eye, nothing clamped).
- **Peep lock** (engine, cg_view.c `CG_AdsPeepLock`, rows with 0 < relief <= 4.5 = the Bren only; `cg_adsPeepLock 0` = off):
  the feel layers after the rig all TRANSLATE the gun (cg_adsSway 0.4 u, breath, kick, lag), which swung a 3 u ring +-60 px
  round a steady post (nb2). After them the gun is turned about its front sight so the aperture is back on the eye -> post
  line. nb3 / nb4: R - F <= 6.4 px on all 48 aimed samples (ADS, 5-frame sway, strafe sway, burst, after the shots, after the
  aimed reload); before 60-90 px.
- **Aimed reloads** `coopr_bren_reload_ads` / `cv_bren_reload_{s,m}_ads` -> `coop_bren_reload_fps{,_s,_m}_ads.skc`
  (`bren_ads.py reload`): the hip clips with the gun LOCKED in the aim pose, rolled 70 deg about the VIEW axis (ring and post
  stay on target, the magazine and the hand work out to the right) and a 6 deg dip round the insert. Arms in the centre box
  <= 3.1 % (35 deg roll: 13.9 %), no IK clamp on the main clip. (ADSSIGHT R-F during a reload is not meaningful: the gun is on
  tag_weapon_left.) Hip reloads untouched (hand low).
- **Clip check**: aim pose + 3 aimed reloads 0 vertices nearer than 1 u (nearest 2.80 u); hip reloads 0 / 0 even at r_znear 4.
- **Re-enabled**: `bren_off.py on` (paths now env / newguns2 defaults), `HZM_FS2_BUILD=H:\hzm_work\newguns2\fs2_build`
  (a COPY of newguns' staging) `fs2_drop_bren.py restore` + `fs2_ng.py pack` -> sha256 2b76b445 (byte-identical to the
  pre-hold pak), gen_skins fs2 write, the five steps, gen_service_record (450 rows, stamp 554288dc, ng-run SELFTEST OK).
- Stills: media/final4 (run nb4, m5l1a, 3440x1438, GL2; red cross = screen centre).
