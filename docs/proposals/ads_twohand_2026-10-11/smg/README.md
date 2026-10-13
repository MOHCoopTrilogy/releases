# SMG lane of the aimed-animation work (started 2026-10-12)

Scope: the `## smg` rows of `..\coverage.md` (18 weapons). Method = `..\README.md` (the standard, the bake pipeline,
gunphys, the offline centre-box check, staged rows, cgame hooks). Everything here is STAGED: nothing is in the mod
tree or the fixes pak. Engine: worktree `openmohaa-hzm-ads-smg`, branch `ads-smg-next` (= ads-next 94bb3dca + ONE
generated row of `cg_adssights.h`, see the handover; `cgame_smg1.dll` = without it, `cgame_smg2.dll` = with it, both in
`G:\mohaa-adsanim3\cgames`). Test game: `G:\mohaa-adsanim3` (owner adsanim3, port 12578).

## HANDOVER (2026-10-13, runs se1 / se2) - read this first

Engine: `ads-smg-next` is at f1802d87 = 94bb3dca + ONE commit: the Silenced MP40's row of
`cg_adssights.h` (F / R z 0.45 u higher, `tools/patch_sights_row.py` from `sights_override.json`), built as
`G:\mohaa-adsanim3\cgames\cgame_smg2.dll`. It belongs TOGETHER with the staged `mp40silenced.skd` - never one
without the other (the eye would look over or under the sights). Run ids used: sa1-sd2, se1, se2, se3. Next: se4.

| gun | state |
|---|---|
| MP40 (reference) | done (section 2), unchanged |
| Silenced MP40 | **passes with aim sway ON in all eight stances** (run se1: 0.0-1.0 %, table below) after the sights of its staged mesh were raised 0.45 u. Needs the user's yes: it is a change of the gun's look (taller sights, lower gun in the aim) |
| MP40 R2 | passes (sc4; se2 stand with sway on: 0.1 % rounds left, 1.4 % empty). Per-shot handle travel looked at in the engine (se2) |
| MP18 | NOT done. A first pass was built offline and taken OUT of the staged tree again (not acceptable yet, list below). Its aim view was captured with the approved skin (se2) |
| Thompsons, Sten, PPSh, grease guns, PPS-43, Type 100, Moschetto | NOT started (section 3 has the facts) |

### Silenced MP40 with sway on - what was wrong, what was done

**Why the settled aim "moved after a clip with a relief set" (run sd1): it did not.** The probe's `relief` is 15.11 u
+-0.01 from the end of the burst to the lower in every sd1 capture; nothing re-eases. Two other things were read as it:
1. `swaybox.py` compared against the UNSHIFTED reference frame. After a 32-round burst the VIEW is still creeping
   back, so the backdrop itself counted as cover (the plain MP40 read 3.2-6.3 % the same way). Fixed: it uses
   reloadbox's shifted reference now. Re-read: sd1 0.0 / 0.3 %, MP40 sc1 0.2 %. The old figures are void.
2. Aim sway + breath are a TRANSLATION of the whole first-person rig (`cg_view.c`: sway +-0.10 u sideways, +-0.07 u
   up/down; breath +-0.105 u up/down, +-0.04 u sideways while aiming), so a part moves on screen by 572 px x shift /
   distance from the eye: the rear sight (13 u) wanders 5-8 px, anything at 5 u wanders 15-20 px.

**Why this gun and not the MP40** (`tools/topprof.py`, `tools/swayoff.py`): on `mp40silenced.skd` the rear leaf stood
0.3-0.45 u over the receiver's rear (retail MP40: 0.7 u) and the receiver is 3.2 u wide (retail 2.1). From the aiming
eye its top was INSIDE the centre box (3.5-4.9 deg under the sight line at 5-7 u from the eye; the box edge is at
7.2 deg), exactly where the sway moves it most. Offline, the settled aim ALONE, worst pair of sway states, box cover
beyond its own grown mask: silenced MP40 6.3 %, MP40 1.8 %, MP40 R2 1.6 %.

| tried | result |
|---|---|
| eye relief (the sights.json `relief` lever), offline -3 .. +4 u | 5.5 / 6.6 / 6.3 / 6.3 / 5.6 / 4.6 / 4.1 / 3.6 % - never under the bar; +4 u is the rig's clamp. Engine sd1 (+2 u) had 2.9 %. A relief cannot fix it: the receiver's top stays at the box edge at every distance |
| lowering the whole rig in the aim (offline `--drop`) | 0.2 u: 2.9 %, 0.35 u: 1.8 %, 0.5 u: 1.3 % - works, but a lowered rig takes the sights off the eye line |
| **both sights 0.45 u taller on the mesh** (`tools/sightraise.py`: rear leaf and front hood + post stretched, 112 vertices of `metal3`, nothing else touched; `sights_override.json`; the rig solve then seats the gun 0.45 u lower by itself) | offline 1.8 % worst pair (= the MP40), 0.4 % from rest. **Engine se1, sway on, cgame_smg2:** |

| stance (run se1, sway on) | rounds left | empty | settled aim alone after it | back on the aim |
|---|---|---|---|---|
| stand | 0.6 % | 0.5 % | 0.1 % | 0.06 deg |
| crouch / prone | - | 0.1 / 0.0 % | 0.1 / 0.0 % | 0.06 |
| lean left / right | - | 0.6 / 0.3 % | 0.3 / 0.2 % | 0.06 |
| crouch + lean left / right | - | 0.6 / 1.0 % | 0.6 / 0.5 % | 0.06 |
| braced | - | 0.2 % | 0.2 % | 0.06 |

Offline (every frame, magazine drawn): 0.0 % both. Looked at: every stance on the sheet, the cock at full size, both
aimed GIFs decoded. Hip GIFs remade (clips unchanged, taller sights). Weak points seen: the rear leaf is a thin tall
blade from the side (0.92 u, was 0.47 - `evidence/mp40silenced_mesh_sights_raised_side.jpg`); at the end of the pull
the index still sits under the knob's stem; third person and the world model get the taller sights too (not looked
at). The 0.06 deg at the row's end is unchanged (engine item, not this lane's).
For a release: the staged skd + this hunk in `ironsights_2026-09-28/sights.json` (`silenced_mp40` F z -6.0254, R z
-6.341) + a regenerated header, in ONE deploy. The shared sights.json is NOT edited (the lane's tools read
`sights_override.json` through smgbake; `SMG_NO_SIGHT_OVERRIDE=1` switches it off).

### Per-shot handle travel in the engine (task 2) - looked at, consecutive 16 ms frames
* Silenced MP40 (se1): knob back at rest, runs forward and back on every shot (one shot per 8 frames), stays FORWARD
  after the last round until the reload's pull (`evidence/mp40silenced_handle_per_shot_se1.jpg`).
* MP40 R2 (se2): the same (the mesh is near-black: the handle reads as a dark bar on the left;
  `evidence/mp40r2_handle_per_shot_se2.jpg`); forward when dry, 8 frames looked at.

### MP18 - where it stands (NOT staged; first-pass files are not in the repo)
* Tools are ready and stay in: `smgbake.GUNS['mp40_mp18']` (row from `EXTRA_ROWS`: its hands row lives in
  anims_shared.txt; side drum `well=(0,-1,0)`, `out_rel=12`, `in_rel=44`, right-hand cock on the MP40's sound frames
  55-61, hook fdir (0.8,-0.5,-0.3) / pdir (-0.3,-0.6,0.75) = wrist at 93 % of the arm, no IK clamp; the mirrored MP40
  hook clamps at 106 %), `smggun.OWN['mp40_mp18']` on the default pull frames, `rows_extra()` writes the shared row
  into `rows_extra.json` `shared`, `mkov_smg.py` patches the pak's own anims_shared.txt into the overlay (never a
  staged copy) and takes `--extra <dir>` (the approved skin: `..\..\mp18_skin_2026-10-12\assets`).
* Rebuild: `python ../tools/smggun.py mp40_mp18 . && python ../tools/smgbake.py mp40_mp18 . && python ../tools/stage_rows.py`.
* Seen offline in that first pass (why it was taken out): the left hand goes to the drum OPEN, fingers splayed (the
  retail approach frames); the right hand rises beside the gun flat, fingers straight up (`fing='aim'` + curl -0.8
  opens the grip too far - it needs a hooked pose of its own); the magazine actions still push the gun DOWN / up
  (`smg_mag_*` are for a magazine under the gun: a side drum needs side / roll actions and its weight in the roll).
  Offline box: rounds left 3.1 % (one frame), empty 6.6 %.
* A fact for the user's rule 1: the MP18's handle rests FORWARD when the gun is dry, on the right, 4.6 deg under and
  5.7 deg right of the sight line - inside the centre box (3.5-3.8 % offline) before any hand moves. Decision needed:
  count the dry gun as the reference for an EMPTY reload, or accept it.
* Aim view with the approved skin (`evidence/mp18_aim_new_skin_se2.jpg`): the sheets load (dark blued steel, no flat
  brown). The receiver's rear is a large flat dark face low in the centre, 31 % of the screen wide: the eye is only
  8.34 u behind the rear sight (probe `relief`; the MP40 has 13.35). First thing to try: `relief` in
  `sights_override.json` for `mp40_mp18` (the rig clamps the move at +4 u = 12.3) via `--set "set
  cg_adsRigReliefBias 4"` in a `sdemo` run, then judge the picture.
  TRIED (run se3, probe relief 12.34 u, `evidence/mp18_aim_relief_se2_se3.jpg`): the flat face becomes a readable
  receiver end with the wooden stock under it, about two thirds the size - clearly better; the receiver's top then
  reaches the bottom edge of the centre box. Not staged (it is `"mp40_mp18": {"relief": 12.3}` in
  `sights_override.json` + its header row; the user should see the picture first).
* SWAY, before any MP18 reload is judged (`swayoff.py mp40_mp18 0,2,4`, settled aim alone, worst pair of sway
  states): 7.7 % as released, 5.4 % at +2 u, **4.0 % at +4 u** (from rest 2.3 / 1.1 / 0.7 %). Its rear sight stands
  only 0.2-0.3 u over the receiver top just behind it (`topprof.py`), and the magazine housing crosses the box: with
  sway on the MP18 will NOT pass by a relief alone - it needs the silenced MP40's cure as well (taller sights,
  `sightraise.py`), offline first.

**Next, in this order.** (a) MP18: the three hand faults above, the relief, then engine + GIFs. (b) Thompson family,
Sten (support hand stays on the magazine in the aim), PPSh, grease guns (cover + bolt to build), then the three
out-of-reach guns with a lowered work pose (section 3). Before judging any other gun with sway on, run
`python ../tools/swayoff.py <gun>` (needs a `smgbake.GUNS` entry): a gun whose settled aim alone is over about 2 %
there cannot pass any reload, and the cure is in its sight height / framing, not in the clip.

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
| MP18 (`coop_mp18`) | not built | `Bone2`, right, forward x 8.3, travel 8.7; side drum; its own first-person clip cocks with the RIGHT hand f52-58, 3.7 u ahead of the handle; gun clip returns the handle forward | - | next (see the handover) |
| Silenced PPS-43 (`ppsh43silenced.skd`) | tried offline, NOT staged | `PPS43_lever` (20 vertices, right, x 9.6-10.6) hangs on the main bone -> split works; `eject` moves nothing | - | out of BOTH hands' reach from the aim (below) |
| Grease gun + silenced (`greaser.skd`) | not built | `Bone1` moves 9.4 u in the reload but NO vertex follows it; the cover is a closed surface (`Mesh_MultiAttached4`, on the top-left as modelled), no port, no bolt | - | cover on a hinge bone + a port and bolt to add |
| Thompson M1A1 / gold / 1928d (`ThompsonSMG.skd`) | not built | none (one bone) | - | add a handle (as the MP40) |
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

Evidence: `evidence/mp40silenced_reload_{aimed,hip}_{roundsleft,empty}_se1.gif` (current; the `_sc6` / `_sd2` ones show the pack's low sights), `mp40silenced_reload_aimed_empty_stances_se1.jpg`, `mp40silenced_aim_before_after_se1.jpg`;
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
`brkmarks.py` (what the rig did through a break-off), `endpose.py` (is a clip's end the aim pose), `swaybox.py` (the settled aim's own box cover with sway on, engine), `swayoff.py` (the same offline, for every sway state and eye relief), `topprof.py` (a mesh's top behind the rear sight as the eye sees it), `sightraise.py` (taller sights on a staged skd), `patch_sights_row.py` (that gun's row in the worktree's cg_adssights.h), `gifrows.py`, `eyezoom.py` (the eye's picture offline, cropped, at game size),
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
