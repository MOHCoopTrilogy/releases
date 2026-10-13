# SMG lane of the aimed-animation work (started 2026-10-12)

Scope: the `## smg` rows of `..\coverage.md` (18 weapons). Method = `..\README.md` (the standard, the bake pipeline,
gunphys, the offline centre-box check, staged rows, cgame hooks). Everything here is STAGED: nothing is in the mod
tree or the fixes pak. Engine: worktree `openmohaa-hzm-ads-smg`, branch `ads-smg-next` (= ads-next 94bb3dca + two
generated rows of `cg_adssights.h`, see the handover; `cgame_smg3.dll` in `G:\mohaa-adsanim3\cgames` has both).
Test game: `G:\mohaa-adsanim3` (owner adsanim3, port 12578).

## HANDOVER (2026-10-13, runs se4 - se9) - read this first

Engine: `ads-smg-next` is at 7b4bc029 = 94bb3dca + TWO commits, each ONE generated row of `cg_adssights.h`
(`tools/patch_sights_row.py` from `sights_override.json`): f1802d87 the Silenced MP40's (F / R z 0.45 u higher), 7b4bc029
the MP18's (F_root / R_root z 0.3 u higher, eye relief 12.34 u). Built as `G:\mohaa-adsanim3\cgames\cgame_smg3.dll`
(`cgame_smg2` = without the MP18 row, `cgame_smg1` = without either). Each row belongs TOGETHER with its staged mesh
(`mp40silenced.skd`, `coop_mp18/mp18.skd`) - never one without the other (the eye would look over or under the sights).
Run ids used: sa1-sd2, se1-se9. Next: se10. Build: `cmake --build .cmake --config Release --target cgame` in the worktree.

| gun | state |
|---|---|
| MP40 (reference) | done (section 2), unchanged |
| Silenced MP40 | **done** (run se4, sway on, cgame_smg2, eight stances): rounds left 0.1-1.5 %, empty 0.1-0.7 %, settled aim alone 0.0-0.9 %, back on the aim 0.05-0.07 deg. Rear leaf shaped into a notch block (below). Looked at: stance sheets, the four GIFs decoded, third person |
| MP40 R2 | passes (sc4; se2 stand with sway on: 0.1 % rounds left, 1.4 % empty). Per-shot handle travel looked at in the engine (se2) |
| MP18 | **done** (run se6, sway on, cgame_smg3, eight stances): rounds left 0.2-1.0 %, empty 0.2-1.2 % (against the dry gun's own pose), settled aim alone 0.0-0.4 %, back on the aim 0.04-0.06 deg. Eye relief +4 u, sights 0.3 u taller, side-drum physics, left hand closed on the drum, firing hand hooked on the handle bar's end. Table and weak points below |
| Thompson (retail mesh `ThompsonSMG.skd`: Thompson + its eleven finish tiks) | **built; passes with aim sway OFF** in all eight stances (run se9: rounds left 0.3-1.0 %, empty 0.2-1.5 %). **With sway ON it does not pass reliably and cannot: its settled aim ALONE is at 0.1-6.3 % (se8) - a decision for the user, below.** The other four Thompson meshes are NOT built and show these prefix rows meanwhile |
| Thompson remodel / M1928 / 1928 Tommy / 50rd, Sten, PPSh, grease guns, PPS-43, Type 100, Moschetto | NOT started (section 3 has the facts; the Thompson survey is below) |

### Sight raises made (coordinator's blanket rule: the minimum that passes, believable, checked in third person)

| gun | raise | how | before / after | third person |
|---|---|---|---|---|
| Silenced MP40 | both sights 0.45 u (run se1) | `sightraise.py`, then `sightshape.py --surf metal3 --box 6.64,6.85,-1.6,-0.25,-6.35,-5.37 --half 0.55,0.24`: the raised leaf was a plate 0.1 u thick and 0.96 u tall (a spike from the side) - now a notch block 1.1 u long at the foot, 0.48 u at the tip; x only, the eye's picture is the same | `evidence/mp40silenced_aim_before_after_se1.jpg`, side: `mp40silenced_mesh_sights_raised_side.jpg` (spike) -> `mp40silenced_mesh_sights_shaped_side.jpg` | `evidence/mp40silenced_third_person_se4.jpg`: a small block on the receiver, hooded front post; no spike |
| MP18 | both sights 0.3 u + eye relief 8.34 -> 12.34 u | `sightraise.py models/weapons/mp40_mp18.tik ... 0.3 --box Cube1:1.8,2.25,-5.42 --box Cube1:25.3,26.1,-4.2`, then `sightshape.py --surf Cube1 --box 1.86,2.20,-2.8,-2.0,-5.98,-5.32 --scale 3.2,1.5` (run with `IRONSIGHT_EXTRA_PAKS` = an overlay holding the skd being shaped). Search: `sighttry.py` - settled aim alone, worst pair of sway states 3.4 % at relief +4 alone, 2.4 / 2.2 / 2.4 / 2.2 % at 0.2 / 0.3 / 0.45 / 0.6 u (from rest 1.1 -> 0.4 %): 0.3 u is where it stops improving | `evidence/mp18_aim_before_after_se6.jpg`, side: `mp18_mesh_sights_raised_side.jpg` | `evidence/mp18_third_person_se5.jpg`: small rear block and front post, reads as the gun's own sights |

For a release each needs, in ONE deploy: the staged skd + its hunk in `ironsights_2026-09-28/sights.json` (the values in
`sights_override.json`; the MP18 is a root-frame gun: F_root / R_root as well as F / R, and `relief`) + a regenerated
header. The shared sights.json is NOT edited (the lane's tools read `sights_override.json` through smgbake;
`SMG_NO_SIGHT_OVERRIDE=1` switches it off, `SMG_SIGHT_OVERRIDE_FILE` points at a trial file).

### MP18 (run se6) - what it does

Aimed, EMPTY (`coopr_mp40_mp18_reload_empty_ads`, 76 frames):
1. f2-8 the left hand leaves the aim grip LOW and to the left (waypoint `via`, fingers closed), comes up to the drum from
   below-left and closes on it (`magmix` 0.55: the pack clip's spread fingers closed half way to the aim grip);
2. f13-17 the drum is dragged out along the raked housing (`well` (-0.6, -0.8, 0)): the gun is pulled LEFT (side 0.2 u)
   and cants toward the pull (roll 1.2 deg), swings back as the drum comes free; f40-44 the new drum is driven home: the
   gun is pushed RIGHT and forward and cants the other way (`smg_side_*`, class smg; next to no drop: 0.19 u, the muzzle
   sag while the hand is away is 0.9 deg with `shoulder` 0.5);
3. the left hand KEEPS HOLD of the seated drum (f44-63) while the firing hand turns into a hook right beside the grip
   (f43-48), goes up to the END of the handle bar (f55: index over the bar, second phalanx down its front face - hook
   `grab`, the hand = the rigid fit to three index joints), pulls it back to the sear (f55-61, gentle start), lets go
   (f63), goes home and turns back last (f70-74); the left hand returns to its grip (f63-71).
Aimed, rounds left (`..._reload_ads`): 1 and 2, a tug outward on the seated drum, home. No pull.
Hip: rounds left = the pack clip to the seat, then its end pose (no mimed cock); empty = that + the same firing hand
(hook pose + `grab`) on the gun clip's own curve.

| stance (run se6, sway on) | rounds left | empty (dry-gun reference) | settled aim alone | back on the aim |
|---|---|---|---|---|
| stand | 0.5 % | 1.2 % | 0.2 % | 0.04-0.06 deg |
| crouch / prone | 0.2 / 0.3 % | 0.4 / 0.4 % | 0.2 / 0.0 % | 0.06 |
| lean left / right | 1.0 / 0.8 % | 0.4 / 0.5 % | 0.2 / 0.4 % | 0.06 |
| crouch + lean left / right | 0.7 / 0.5 % | 0.3 / 0.7 % | 0.3 / 0.2 % | 0.06 |
| braced | 0.2 % | 0.2 % | 0.1 % | 0.05 |

Offline (every clip frame, drum drawn): 0.2 % both. Looked at: all eight stances on the sheets, twelve full-size engine
frames of the empty reload (`evidence/mp18_reload_aimed_empty_frames_se6.jpg`), the four GIFs decoded.
Weak points seen: the firing hand holds the handle at its very END (thumb and index around the bar's tip - further in,
the fingers over the bar stand in the centre box while the handle is forward); the left hand's index lies along the
drum's rear face as in the pack clip; in the full-frame GIFs (440 px) the hands are small - the frame sheet shows them;
the hip clips were looked at only on the decode sheet and one offline sheet; 0.04-0.06 deg at the row's end (engine item).
Not listened to. Not run: break-off mid-reload for this gun, an AI with it.

### Three things the next gun needs to know (all cost a run or more here)

1. **A firing hand that leaves the grip moves the GUN between the clip's keys** (bug-3659). The weapon tag hangs on that
   hand; the bake counter-keys it on the 30 Hz keys only. Run se5: the gun jumped on every other 16 ms frame (0.64 u /
   1.4 deg at the half-way points; 2-10 % of the box) and the offline tools - integer frames - saw nothing.
   `python ../tools/midframe.py <clip.skc>` prints it; under about 0.1 u / 0.1 deg it is not seen. Cure in the bake: turn
   the hand beside the grip, travel without turning, start the pull gently (`pull_soft` in smggun OWN, shared with
   smgbake's `pull_u`), give the turn frames. Applies to every `cock='R'` gun (Sten, M1A1 remodel) and to bake_hip_right.
2. **gunphys runs with hand=-1 in this lane: roll and side of every event are reversed** (bug-3660). Write a new action
   as it is seen and reverse it under the table, as `smg_side_*` does; check with the SB_TRACE print or the baked tag.
3. **Root-frame guns** (sights.json `frame_used: root` - the Breakthrough / pack meshes): the rig reads F_root / R_root
   (bug-3662), and a prop that is a copy of such a gun's skeleton has to be added to `gungeo.root_skds()` or the offline
   looks draw it 2-3 u off (bug-3661). `topprof.py` reads F / R against root-frame geometry for such a gun: its angles
   are off by the frame offset.

Also new: an EMPTY reload is measured against the DRY gun's own pose as well as the cocked aim (coordinator's decision 3,
bug-3665): `smgbake --box` does it for `*_empty`, `measure_run.py` for every E capture (`--nodry` = off; it prints how
much the dry mask adds - after a long burst that includes lingering smoke, so read it next to the offline figure).
`run_smg.py --parts sdemol` (lower-case L) = rounds left in EVERY stance of `--sstances`; `tpc` = close third-person
stills (the camera cvars do not frame the gun well, bug-3666: crop and enlarge). `evid.py <run> <gun key> <name> <sheet>
--stances` = the four full-frame GIFs + stance sheets + one decode sheet. `smgbake --cu out.jpg --cuhand L|R --cam f,l,u`
= a close look at one hand.

### Thompson, retail mesh (runs se7 / se8 / se9) - built, one decision open

**Gun.** `ThompsonSMG.skd` has one bone and no handle: the cocking slot is painted on the RIGHT of the receiver (x -2.2 ..
3.2, z -3.9) with a knob ring painted at its front end. A knob is ADDED (`smggun.GUNS['thompson']`: box 0.42 x 0.7 x
0.42 u on its own bone `coop_bolt`, standing out of the right wall; back x -1.6 = cocked, forward x 3.4 = inside the
painted ring; existing vertices untouched), open bolt as the MP40 (`coop_thompson_fire` / `_fire_empty` / `_idle_empty` /
`_reload_empty` / `_reload_ads_empty`; the key is in the names). All 12 tiks on this mesh are patched by script. The
reload sound (ThompsonReload1a.wav: magazine out f9-13, in f39 / f45-49, handle f57-65) is cut before the handle for
`reload` (`coop_thompson_snd_reload_loaded`). `evidence/thompson_mesh_handle_added_side.jpg` (back / forward).

**Hands** (`smgbake.GUNS['thompson']`, the PREFIX rows `thompson_reload[_empty][_ads]`):
* aimed: the left hand leaves the fore-grip, magazine out and in as the MP40's (under the gun; in this close aim almost
  all of it is under the frame - the new magazine shows beside the gun on the left for 0.2 s), back to the fore-grip;
  EMPTY: the FIRING hand turns into a hook beside the grip (f47-52), goes up to the knob (f59), pulls it back to the
  sear on the sound's clacks (f59-65), lets go (f67), home by f75. The server ends this reload at f78 of the row's 84
  frames (`end=77`, bug-3683);
* hip: rounds left = the retail clip to the seat, then its end pose (the mimed cock is gone); empty = the RETAIL
  technique - the left hand over the top of the gun, turned about its wrist onto the knob (`hip_cock='L'`), the knob
  follows it (f63.5-66.5).

| stance | rounds left, sway OFF (se9) | empty, sway OFF (se9) | back on the aim |
|---|---|---|---|
| stand | 0.6 % | 1.1 % | 0.07 / 0.14 deg |
| crouch / prone | 0.7 / 0.8 % | 0.2 / 1.0 % | 0.07 |
| lean left / right | 1.0 / 0.3 % | 0.3 / 0.6 % | 0.08 |
| crouch + lean left / right | 0.9 / 0.3 % | 0.4 / 0.6 % | 0.07 |
| braced | 0.3 % | 1.5 % (smoke: nothing of the gun or the hands is in the box in the braced view; se7 read 5.5 % the same way) | 0.07 |

Offline (every frame): 1.1 % rounds left, 1.7 % empty; gun between the keys 0.07 u / 0.06 deg (`midframe.py`).
**With aim sway ON (run se8, cgame_smg3, the same clips but for the last frames):** stand rounds left 2.2 % (5 frames
over), stand empty 0.8 %, crouch empty 0.3 % - and the SETTLED AIM ALONE, nothing happening: 0.8 %, 6.3 % (23 of 52
frames over) and 0.1 % after those three. Offline, settled aim alone: 6.9 % from rest, 20 % between two sway states;
with eye relief +2 / +4 u: 4.2 / 2.3 % from rest, 12.9 / 8.3 % worst pair. The rear aperture with its two guard ears
and the receiver top cover 50 % of the box a few units from the eye, and the sway moves them 15-20 px. This is not a
low-sight case, so no sight was raised. **Decision for the user (bug-3682):** change the Thompson's aim framing (eye
relief +4 u and more - a visible change to the most used gun), or judge its reloads with sway off / against a
reference that follows the sway.

Looked at: all eight stances on the sheets (se9), ten full-size engine frames of the empty reload + third person
(`evidence/thompson_reload_aimed_empty_frames_and_third_person_se7.jpg`), the four GIFs decoded.
Weak points seen: the eye sees next to nothing of the magazine swap (it is under the frame; only the gun's dip and
lift show it); at the pull the gun comes 0.9 u back and cants - in this close aim the whole sight picture swells for
0.15 s (the MP40's figure; `smg_bolt_pull_r` could be made lighter for this gun); the firing hand is a large shape
right of the receiver and hides the knob it holds; the painted knob ring stays at the front of the slot while the real
knob rests back (a 0.42 u square in a 0.9 u ring when forward) - a bigger knob or a repainted slot is a look decision;
the first frames of the "empty" GIF show the view still coming back from the burst. Not run: break-off, AI, the
per-shot knob travel in the engine (same clip set as the MP40's), the finish tiks one by one (same mesh and rows).
Not listened to.

### Thompson family - the other four meshes, NOT started

| tik(s) | mesh | handle | gun clip, magazine hidden | note |
|---|---|---|---|---|
| thompsonsmg, thompsonsmg_gold | `ThompsonSMG/ThompsonSMG.skd` | none (one bone) | 71 fr, f9-47 | add a handle on the RIGHT (the M1A1's place), firing hand, `grab` |
| thompsonsmg_tommy1928d | `coop_tommy1928d/ThompsonSMG.skd` | none | 71 fr, f24-58 (its own prop window f22-60) | its own mesh and timing |
| thompson50 | `Thompson/Thompson50.skd` | `Bolt`, TOP knob, rests back, +5.05 forward | 84 fr, f26-58 | drum; group xw_thompson50; the knob is ON the sight line |
| thompsonsmg_tommy28 | `coop_tommy28/ThompsonSMG.skd` | `Bolt`, top knob | 84 fr x 0.032, f9-47 | as the 50rd |
| thompsonsmg_m1a1dk | `coop_m1a1dk/thompson.skd` | `chamber`, right, forward x 3.2, travel 6.1 | 71 fr, f9-47 | firing hand reaches (75 %) |

Hands row `thompson_reload` = `viewmodel/smg/reload_tommy_stand.skc`, 84 frames; the left hand is away f1-77 (pouch at
f28), the right never leaves the grip; server prop `models/ammo/thompson_clip.tik` on tag_weapon_left f8-46; aim pose
`thompson_charge` = `viewmodel/idle_tommy_stand.skc` (support hand on the fore-grip, 0.3 u from the hip place: nothing to
re-pose). `prop_qa.attach_windows(row, frames, frametime)` gives the prop window of any row (sten 12-43, ppsh 44-60).
A TOP knob on the sight line cannot be worked on the sights: lowered work pose (the standard's second route).

**Next, in this order.** (a) the rest of the Thompson family: the remodel as a `_variant('thompson', ...)` with its own
`chamber` handle (`smggun.OWN`, `cock='R'` + `grab`), the 1928 Tommy (its own mesh, no handle, prop window f22-60), then
the top-knob pair (M1928, 50rd) with a lowered work pose - until then those four show the retail mesh's prefix rows
(a hand on a knob that is not there): **do not ship the Thompson rows before all five are built.** Then Sten (support hand stays on the magazine in the aim), PPSh, grease guns (cover + bolt to build), then the three
out-of-reach guns with a lowered work pose (section 3). Before judging any gun with sway on, run
`python ../tools/swayoff.py <gun>` (needs a `smgbake.GUNS` entry): a gun whose settled aim alone is over about 2 %
there cannot pass any reload - `sighttry.py` finds the raise. Run `midframe.py` on every clip with a moving firing hand.

### Silenced MP40 with sway on - what was wrong, what was done (run se1; unchanged facts)

Aim sway + breath are a TRANSLATION of the whole first-person rig (`cg_view.c`: sway +-0.10 u sideways, +-0.07 u up /
down; breath +-0.105 u up / down, +-0.04 u sideways while aiming), so a part moves on screen by 572 px x shift /
distance from the eye. On `mp40silenced.skd` the rear leaf stood 0.3-0.45 u over the receiver's rear (retail MP40:
0.7 u) and the receiver is 3.2 u wide (retail 2.1): its top was INSIDE the centre box, 5-7 u from the eye. Settled aim
alone, offline, worst pair of sway states: 6.3 % (MP40 1.8 %). Eye relief -3 .. +4 u: 5.5-3.6 %, never under the bar;
lowering the rig works but takes the sights off the eye line; both sights 0.45 u taller: 1.8 % (= the MP40).
`swaybox.py` compares against the reference shifted to each frame's background (the unshifted figures of sd1 are void).
Per-shot handle travel looked at in the engine: Silenced MP40 (se1), MP40 R2 (se2) - back at rest, forward and back on
every shot, forward after the last round (`evidence/mp40silenced_handle_per_shot_se1.jpg`, `mp40r2_handle_per_shot_se2.jpg`).

## 1. Aim poses (`tools/smgpose.py`, rows by `tools/stage_rows.py`)

The released `<prefix>_charge` pose with the support hand put in the hip idle's hand-to-gun relation, left arm
re-solved. Trunk, eye, firing arm, its fingers and the weapon tag are the released pose's (asserted per bake), so the
sight picture cannot change.

| prefix (guns) | hip place | released aim | new aim | centre box, settled aim: released -> new (engine) |
|---|---|---|---|---|
| mp40 (MP40, silenced, PPS-43, grease guns, MP18, MP40 R2) | on the magazine housing | 2.4 u off | **0.0 u** | 11.3 -> 11.4 % |
| ppsh | behind the drum | 4.7 u off | **1.8 u** (same place along the gun; 1.2 u left, 1.4 u lower) | 18.7 -> 18.6 % |
| moschetto (both tiks) | on the fore-end | 2.6 u off | **0.0 u** | 11.4 -> 7.6 % |
| type100 | on the side magazine | 7.4 u off | **1.4 u** (was 2.0 in the pistol lane's pose) | 26.1 -> 21.2 % |
| sten | on the side magazine | - | 0.0 u (pistol lane's clip, taken over unchanged) | 18.2 -> 18.3 % (sway off) |

* PPSh: the hip hand wraps a stock narrower than the hand - at the exact place its thumb and fingertips flank the rear
  sight (9.8 % of the box), 1.2 u lower its fingertips showed on the RIGHT of the receiver (run sa2). Final: 1.2 u to
  the left and 1.4 u lower - nothing right of the gun, 0.1 % of the box. Type 100: exact place = 11.8 % hand in the box.
* Runs: `sa1` released poses; `sa2` new poses, 8 stances, 5 guns (pose 1.00, sight line unchanged in all 40); `sa3`
  the seven guns sharing the rows, standing; `sa5` RELEASED poses braced; `sa6` / `sa7` sway off (Sten, PPSh pairs,
  PPSh in 8 stances). Stills: `evidence/aim_<gun>_before_after.jpg`, `aim_<gun>_stances_*.jpg`,
  `aim_variants_stand_sa3.jpg`, `braced_released_vs_new_sa5_sa2.jpg`.
* **Sten (bug-3585) - settled:** not a pose effect. The stills of sa1 / sa2 were taken with aim sway on; the Sten's
  rear sight is 4.27 u from the eye, so the sway moves its receiver cap 6-7 times further than the front sight. Sway
  off: sight points and the gun's tag point identical to 0.1 px for both poses. The released picture is kept.
* **Braced:** the sights sit at the bottom edge of the box with the RELEASED poses too (front sight 25-33 px below the
  centre for every gun, the same with the new poses) - the braced view's own framing.
* **MP18 flat brown:** the pack's own textures are near-uniform colour fields (body.jpg sd 6 on 8 bits); same with the
  released files. Not a missing texture or shader. A new skin was approved on 2026-10-12 (docs dc7a8d1,
  `docs/proposals/mp18_skin_2026-10-12`); nothing of it is changed or staged in this lane.
* Open: PPSh / Moschetto aim poses borrow the MP40's pistol-grip firing hand (holds air under a rifle stock, bug-3586).

## 2. MP40 reference (`tools/smggun.py`, `tools/smgbake.py`)

**Gun.** The mesh has no cocking handle (the slot is painted: x 4.3 .. 12.0, z -4.25 on the left of the tube). A handle
is ADDED (box 0.36 x 0.8 x 0.36 u on its own bone `coop_bolt`; existing vertices, UVs and weights untouched; it samples
uv 0.547, 0.4185 - the point the weapon-HD lane already holds for an MP40 knob). OPEN BOLT, as it works:

| gun clip (11 tiks on this mesh, patched by script) | handle |
|---|---|
| bind pose / `idle` / `reload` (unchanged retail clips) | back, x 5.0 |
| `fire` -> `coop_fire.skc` (6 frames at 1/60 s) | 5.0 -> 8.6 -> 11.5 -> 8.9 -> 6.3 -> 5.0 on every shot |
| `fire_empty` (server picks it for the last round) / `idle_empty` | runs forward and stays: 11.5 |
| `reload_ads_empty` (aimed, empty) | forward until frame 55, pulled back over 55-61 |
| `reload_empty` (hip, empty) | forward until frame 58, eased back over 58-63.5 (2b: was the retail hand's one frame) |

**Sound (2b).** The reload sound is ONE file (MP40Reload1a.wav: magazine out 0.37 s, in 1.15-1.25 s, handle 1.97 s and
2.15 s). A rounds-left reload must not sound cocked: `reload` now plays `coop_mp40_snd_reload_loaded` (the file faded
out over f51-56, tik-local aliascache, `sound/weapons/foley/` staged); the EMPTY rows keep the retail sound. Not
listened to (no audio in the harness); no load error in the logs. Other players hear the cut one for every reload.

**Hands, aimed** (firing hand never leaves its grip; no gun key set by hand - `gunphys` class `smg`, `smg_*` actions):
1. thumb on the catch, hand slides down onto the magazine (f3-8); magazine dragged down the well (10-14), swung out to
   the LEFT of the gun and seen leaving low-left (15-22): the gun follows it down, then lifts; while the hand is at the
   pouch (25-28) the muzzle hangs 1.3 deg low (shoulder + firing hand carry it - support weight 0.3, not 0);
2. the new magazine comes up BESIDE the gun on the left, in view under the box (31-39), drops under the housing, is
   driven up (44-48). 2b: the weight comes back onto the hand from 4 frames before the seat to 3 after it and the push
   is 0.8 of sb4's over 5.5 frames - the fastest sight-line step at the seat fell from 0.175 to under 0.11 deg per
   capture frame (`reloadbox.py --dump` lists the six fastest steps; the fastest now is the drag at f11, 0.14);
3. rounds left: a tug on the seated magazine (f51, the gun dips), the hand back on the housing (62). EMPTY: the hand
   goes up the receiver's left side, palm DOWN and toward the gun, hooks the handle with the index (55) and pulls it
   back (55-61): the gun comes 1.0 u back into the shoulder and cants 0.8 deg; the sear holds the bolt, the hand
   lets go (63) and is back on the housing (71). The eye sees the knuckles lead up to the handle and the index on
   its front face (`evidence/mp40_cock_closeup_sc1.jpg`; sb4's hand had its palm on the wall = "a fist").

**Hands, hip** (the same story): `mp40_reload` = the retail clip to the seat frame, the palm stays under the magazine
3 frames, then the gun comes back to the hip by f70 (the mimed cock is gone; 0.2 s of settled pose is left, was 0.5);
`mp40_reload_empty` = the retail clip with its cocking hand turned about its own wrist so the index fingertip is ON the
handle; the fingers close as the hand leaves the magazine (three quarters to the hip grip by the reach, run sd2 - it
was a flat open hand in sb4 and still open on the reach in sc3) and ease to the hip grip after the pull (no splay).

**Engine** (`tools/measure_run.py` = `reloadbox.py` per capture; an emptied gun's first 8 frames = its last shot's
flash are left out; reference shifted to each frame's background). Final clips: run sc3 (stand) - sc1 / sc2 ran every
stance with the same hands (sc2's MP40 HANDLE was dead, bug in the tools, fixed: its box figures stand, its pictures
are not used).

| stance, case | centre box beyond the aim (bar 2 %) | sight line max | back on the aim after the row | pose |
|---|---|---|---|---|
| stand, rounds left (sc3) | 0.4 % | 1.39 deg | 0.06 deg | 1.00 |
| stand, empty (sc3) | 1.0 % | 1.39 | 0.06 | 1.00 |
| crouch / prone, empty (sc1; sc2) | 0.4 / 0.4 %; 0.1 / 0.4 % | 1.38 | 0.06 | 1.00 |
| lean left / right, empty | 0.9 / 0.7 %; 0.8 / 1.0 % | 1.38 | 0.06 | 1.00 |
| crouch + lean left / right, empty (new) | 1.2 / 0.8 %; 0.9 / 0.8 % | 1.38 | 0.06 | 1.00 |
| braced, empty | 0.2 %; 0.2 % | 1.38 | 0.06 | 1.00 |

Offline (every frame, magazine prop drawn): 0.0 % rounds left, 0.3 % empty. GIFs (20 fps, centre box drawn), decoded
and looked at: `evidence/mp40_reload_aimed_roundsleft_sc3.gif`, `..._aimed_empty_sc3.gif`, `..._hip_roundsleft_sc3.gif`,
`..._hip_empty_sd2.gif`; every stance on one sheet: `evidence/mp40_reload_aimed_empty_stances_sc1.jpg`.

**Break-off mid-reload** (run sc1 rounds left, sc3 empty; `sbreak`, 0.8 s and 1.7 s into the reload; `brkmarks.py`):

| what | result |
|---|---|
| trigger | nothing: the reload runs to its end in the aim (a magazine reload is not interruptible by fire in this game) |
| sprint (`+speed +forward`) | nothing: the reload runs to its end, aim framing held (pose 1.00) |
| next weapon | the gun goes down at once, the next weapon comes up; no hand, magazine or handle left behind (`evidence/mp40_breakoff_switch_sc1.jpg`) |
| aim let go | the framing goes to the hip in 0.7 s while the row hands over to the hip clip at the same frame; magazine and hand arrive together, ends as the hip clip does (`evidence/mp40_breakoff_aim_dropped_sc1.jpg`) |

Known weak points (seen in playback):
* The first 4 frames of every "empty" GIF: the VIEW is still coming back from the 32-round burst (the wall moves).
* The magazine is on screen 0.25 s going out and 0.3 s coming in - more than sb4's 0.2 s in all, still brisk: the
  server's prop window (f10-48) is fixed and the well itself is under the frame.
* The tug and the hand's return to the housing are under the frame: only the gun's dip shows them.
* 0.06 deg is left when the row ends and eases to 0.00 in 0.8 s (bug-3597, the engine's held rig solve). Bar 0.05.
* In the GIFs the hand's skin is pale (96-colour palette); the full-size crop shows the game's own.

## 3. Each gun's own reload on its own mesh

All of them fire from an open bolt: handle back when ready, forward when dry, cocked after an EMPTY reload only.

**How a gun is built** (`smggun.py <key> .` then `smgbake.py <key> .` then `stage_rows.py`):
* The gun side. Mesh with NO handle: add one (`GUNS`, the MP40). Mesh WITH a moving bone (`OWN`): nothing on the mesh
  changes - every gun clip the tik names is re-issued under `coop_<key>_...` with that bone's channel rewritten to the
  open-bolt story (`fire` = back-forward-back, `fire_empty` / `idle_empty` = forward, `reload` = held back,
  `reload_empty` / `reload_ads_empty` = forward until the pull; every other clip = held back) and the tik rows are
  pointed at them. `rest='back'` for a pack whose clips already rest the bolt back (MP40 R2). Handle modelled but on
  the main bone: `split=(surface,)` gives it its own bone first (PPS-43, tried, not staged). The key is in the clip
  names because several meshes share one model directory (bug: the silenced MP40 once overwrote the MP40's clips).
* The hands. `smgbake.GUNS[key] = _variant('mp40', key, ...)`: the MP40 choreography on that gun's sight line and
  handle (`smggun_<key>.json`), staged as the per-weapon rows `coopr_<key>_reload[_empty][_ads]` (cgame
  `CoopPerWeaponReloadAnim`, already in ads-next: they win over the prefix rows for exactly that weapon).
* `reachcheck.py <key> [L|R]` BEFORE choosing the hand: shoulder, hooked wrist, per cent of the arm.

| gun | state | handle on the mesh | engine: box beyond the aim, stances | open |
|---|---|---|---|---|
| Silenced MP40 (`mp40silenced.skd`; since se1 with both sights 0.45 u taller, see the handover) | built, run sc2 + sc6, **se1** | a real knob on bone `eject`, left; the retail clips slam it back and forward at the END of every reload | sc6 (aim sway off): rounds left 0.0 %, empty 0.3-0.8 % in stand / crouch / prone / leans / crouch-leans / braced; back on the aim 0.06 deg | **se1, sway ON: 0.0-1.0 % in all eight stances** (it was 2.4-4.0 % in three stances of sc2 with the pack's low sights). Hip, empty: the hand closes before the reach since sd2; at the end of the aimed pull the index sits under the knob's stem. Per-shot knob travel looked at (se1) |
| MP40 R2 (`coop_mp40r2`) | built, run sc4 | `Bone1`, left; the pack's clips already rest it back (its reload = the EMPTY story) | sc4: rounds left 0.1 %, empty 0.0-0.7 % in all eight; back on the aim 0.06 deg (braced 0.02) | hip, empty: the hand closes before the reach since sd2. Per-shot travel looked at (se2). The mesh is near-black in the offline renders (its texture), fine in the engine |
| MP18 (`coop_mp18`; staged mesh: sights 0.3 u taller, eye relief 12.34 u) | built, run **se6** | `Bone2`, a bar on the right, forward x 8.3, travel 8.7 (ends about 1.3 u right of the bolt's centre); side drum; the pack's own first-person clip cocks with the RIGHT hand f52-58, 3.7 u ahead of the handle | se6, sway ON: rounds left 0.2-1.0 %, empty 0.2-1.2 % (dry-gun reference) in all eight stances; back on the aim 0.04-0.06 deg | the firing hand holds the bar at its end; break-off and AI not run (see the handover) |
| Silenced PPS-43 (`ppsh43silenced.skd`) | tried offline, NOT staged | `PPS43_lever` (20 vertices, right, x 9.6-10.6) hangs on the main bone -> split works; `eject` moves nothing | - | out of BOTH hands' reach from the aim (below) |
| Grease gun + silenced (`greaser.skd`) | not built | `Bone1` moves 9.4 u in the reload but NO vertex follows it; the cover is a closed surface (`Mesh_MultiAttached4`, on the top-left as modelled), no port, no bolt | - | cover on a hinge bone + a port and bolt to add |
| Thompson M1A1 + finishes (`ThompsonSMG.skd`, 12 tiks) | built, runs se7-se9 | ADDED: a knob on the right, back x -1.6, travel 5.0 | se9, sway OFF: rounds left 0.3-1.0 %, empty 0.2-1.5 % in all eight | with sway ON the settled aim alone is over the bar (bug-3682, decision); see the handover |
| Thompson 1928 Tommy (`coop_tommy1928d`) | not built | none (its own mesh) | - | add a handle; prop window f22-60 |
| Thompson 50rd / M1928 | not built | `Bolt`, top knob at x -0.9, rests BACK already, +5.1 forward in the retail reload | - | `rest='back'`; a knob on the sight line |
| Thompson M1A1 remodel (`coop_m1a1dk`) | not built | `chamber`, right, forward x 3.2, travel 6.1 | - | firing hand reaches (75 %) |
| Sten | not built | `Sten_Bolt`, right, forward x 7.8, travel 8.8 | - | firing hand reaches (92 %) |
| PPSh | not built | welded into the mesh | - | split by box (`split_bone.py --box`) |
| Moschetto / Beretta M38 | not built | `Rechamber`, right, forward x 12.3, travel 4.1 (+ `Eject_Cover`); the real handle does not reciprocate | - | out of the firing hand's reach (107 %) |
| Type 100 | not built | `bolt`, right, forward x 10.3, travel 5.6 | - | out of reach (101 %) |

(`python smggun.py survey <tik>:<bone>:<L|R|T> ...` prints these lines; `gunsurvey.py <tik>` the bones, clips, server
frames and sound of a gun; `handtrace.py <row>` which hand leaves its grip when in a first-person clip.)

**Which hand.** In EVERY retail SMG hip reload (Thompson, drums, Sten, PPSh, Moschetto, Type 100) the right hand never
leaves the grip: the left hand does magazine and handle, reaching over the gun for a right-side handle (Type 100:
index tip at y +2.7 in f51-71). Only the pack-made MP18 clip uses the right hand. In the AIM a hand over the top
crosses the sights, so a right-side handle is the firing hand's - where it can reach:

* the right shoulder is 20 u behind the weapon tag in the aim pose and the arm is 26.8 u long: a hooked wrist reaches a
  handle up to about x 8 (MP18 94 %, Sten 92 %, M1A1 remodel 75 %); PPS-43 (x 10.4) is at 117 % (102 % with the
  fingers forward), Type 100 101 %, Moschetto 107 %;
* a clamped firing arm DRAGS THE GUN: hold_bake's `right_path` keys the weapon tag from the planned hand (PPS-43,
  offline: the gun swung through the view, 24 % of the box). Never accept `IK clamp R` in a bake;
* the left hand UNDER the receiver (`_UNDER` in smgbake, the under-reach) gets to the PPS-43's handle at 92-100 % of
  the arm and only with the forearm through the pistol grip - not usable as tried;
* so for the handles out of reach the route is the standard's second one: the gun comes DOWN under the box into a
  work pose (revbake's `gun_abs` list / the BAR's work pose in `..\heavy`) and is worked there with the retail
  left-hand technique, back to the aim within 0.05 deg. Not built; a decision for the coordinator.

Ready in the tools, exercised only offline: `cock='R'` (aimed: the left hand returns to its grip first, the firing
hand hooks, pulls, returns - mirrored hook and mirrored `smg_*_r` physics; hip: `bake_hip_right`, built on the
rounds-left clip), `handle='R'` + `_UNDER`, `hip_built` (a built left-hand hook over the top at the hip).

Evidence: `evidence/mp40silenced_reload_{aimed,hip}_{roundsleft,empty}_se4.gif` (current, full frame; the `_sc6` / `_sd2` ones show the pack's low sights), `mp40silenced_reload_aimed_{empty,roundsleft}_stances_se4.jpg`, `mp40silenced_aim_before_after_se1.jpg`, `mp40silenced_third_person_se4.jpg`;
`evidence/mp18_reload_{aimed,hip}_{roundsleft,empty}_se6.gif`, `mp18_reload_aimed_{empty,roundsleft}_stances_se6.jpg`, `mp18_reload_aimed_empty_frames_se6.jpg`, `mp18_aim_before_after_se6.jpg`, `mp18_third_person_se5.jpg`;
`evidence/thompson_reload_{aimed,hip}_{roundsleft,empty}_se9.gif` (sway off), `thompson_reload_aimed_{empty,roundsleft}_stances_se9.jpg`, `thompson_reload_aimed_empty_frames_and_third_person_se7.jpg`, `thompson_mesh_handle_added_side.jpg`;
`evidence/mp40r2_reload_{aimed,hip}_{roundsleft,empty}_sc4.gif` (hip empty: `_sd2`), `mp40r2_reload_aimed_empty_stances_sc4.jpg`,
`mp40r2_cock_closeup_sc4.jpg`. All GIFs decoded (gifsheet.py) and looked at; every stance looked at on its sheet.

**AI** (run sc5, `--map m6l1a --spot 6152,-6528,5440,135`: no friendly actor on that map, nearest enemy 1779 u away;
`mapents.py`): a spawned Wehrmacht NCO raises his MP40, fires bursts at the player, reloads (the gun held up, a
magazine on the ground), fires again - 12 s, nothing detached, no animation error in the log
(`evidence/mp40_ai_firing_sc5.jpg`). The handle is under a pixel at that distance: its per-shot travel is checked on
the first-person gun and offline only.

## Tools (`tools/`)

`takeover.py` regenerates `run_smg.py` (+ `smg_block.py`: `sdemo` / `shipdemo` / `tp` / `ai` / `sbreak` captures; `--map`
/ `--spot`) and the measure tools from `..\tools`, repointed at G:\mohaa-adsanim3. `smgpose.py` (aim poses +
`handsurvey.json`), `smggun.py` (added handle, or `OWN` / `split` for a mesh that has one; open-bolt clips; tik rows for
every tik on a mesh; the cut rounds-left sound; `survey`), `smgbake.py` (aimed + hip hands, `_variant` per weapon;
`--box` offline box check with the magazine drawn, `--cu` close-up of the hand on the handle, `--look`; `SV_RIGHT=1`
looks from the right), `stage_rows.py` (fps_anims_smg.txt = released fixes-pak copy + this lane's rows,
`rows_extra.json` from the bake), `mkov_smg.py` (overlay; `--base` = released rows; adds the AI spawn poll),
`measure_run.py` (every aimed capture of a gun in a run -> `reload_<run>_<gun>.json`, `--status` into
`coverage_status.json`), `reloadbox.py` (one capture; `--dump` = frames over the bar + the fastest sight-line steps),
`stancesheet.py` (every stance of a gun on one sheet), `capcrop.py` (full-size crops of capture frames),
`brkmarks.py` (what the rig did through a break-off), `endpose.py` (is a clip's end the aim pose), `swaybox.py` (the settled aim's own box cover with sway on, engine), `swayoff.py` (the same offline, for every sway state and eye relief), `topprof.py` (a mesh's top behind the rear sight as the eye sees it), `sightraise.py` (taller sights on a staged skd), `sightshape.py` (a thin raised leaf into a block, x only), `sighttry.py` (offline search for the smallest raise that passes with sway on), `midframe.py` (does the gun stay put BETWEEN a clip's keys), `evid.py` (a gun's GIFs + sheets from one run), `patch_sights_row.py` (that gun's row in the worktree's cg_adssights.h), `gifrows.py`, `eyezoom.py` (the eye's picture offline, cropped, at game size),
`reachcheck.py`, `gunsurvey.py`, `handtrace.py`, `mapents.py` (player start + actors of a map: where an AI can be
looked at), `aimpair.py`, `sideview.py` / `eyepair.py` / `gunside.py` (offline looks), `status_merge.py` /
`status_reload.py`, `buglog_add.py`.

    cd smg/assets                       (IRONSIGHT_EXTRA_PAKS must be UNSET for smggun / the bake)
    python ../tools/smggun.py mp40 .  &&  python ../tools/smggun.py silenced_mp40,mp40_reactivated .
    for g in mp40 silenced_mp40 mp40_reactivated; do python ../tools/smgbake.py $g .; done;  python ../tools/stage_rows.py
    python ../tools/mkov_smg.py <SCRATCH>\adssmg\ov_x.pk3
    IRONSIGHT_EXTRA_PAKS=<that pk3> python ../tools/smgbake.py mp40 . --nobake --box --which ads_empty,ads_loaded
    IRONSIGHT_EXTRA_PAKS=<that pk3> python ../tools/eyezoom.py mp40 . ads_empty out.jpg --frames 50:66:2
    cd ../tools; python run_smg.py <id> --overlay <abs pk3> --cgame cgame_smg1 --guns mp40 --parts sdemo,shipdemo,sbreak \
        --sstances stand,crouch,prone,standL,standR,crouchL,crouchR,braced --yaw 160 --hold 235 --rel 215
            (harness gun keys: mp40s, mp40r, mp18, pps43, greasegun ...; --hold = clipsize x sp firedelay / 0.016 + 40:
             300 for the silenced MP40; near-eye guns: add --set "set cg_adsSway 0" --set "set cg_weaponBreath 0")
    python measure_run.py <id> mp40 --dump [--status models/weapons/mp40.tik mp40];  python brkmarks.py <id>
    python dgif.py <id> mp40__adsE__ out.gif --frames 284:470:3 --w 400 --crop 240,120,1040,720 --box
    python gifsheet.py out.gif sheet.jpg 0:64:1;  python stancesheet.py <id> mp40 sheet.jpg
    python run_smg.py <id> --overlay <pk3> --cgame cgame_smg1 --guns mp40 --parts ai --map m6l1a --spot 6152,-6528,5440,135

Reusable by the MG / heavy lane: `smggun.py` (`patch_tik`, `same_mesh_tiks`, the open-bolt clip set, `OWN` for a mesh
with a bolt bone, `cut_wav`), `smgbake.py`'s `hook_rel` (a hand hooked on a handle built from the hand's own geometry,
either hand) and the `smg_*` gunphys actions, `reloadbox.py`, `reachcheck.py`, `smgpose.py`, `gunside.py`.

Harness facts: the coop game fires on the tik's `sp firedelay`; `set cheats 1` does not survive the mod's server start
(no `spawn`, no `notarget`; the harness's `dog 1` has been a no-op); aim sway is ON in the shared runner
(`cg_adsSway 0.1`, `cg_weaponBreath 1`) - it moves a gun that is drawn close to the eye by several pixels and reads as
box cover (silenced MP40); a gun that is not emptied within `--hold` does not reload (and the next capture starts one
round from dry); mp40.skd, mp40silenced.skd and ppsh43silenced.skd share `models/weapons/mp40`.
