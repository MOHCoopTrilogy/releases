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
