# SMG lane of the aimed-animation work (started 2026-10-12)

Scope: the `## smg` rows of `..\coverage.md` (18 weapons). Method = `..\README.md` (the standard, the bake pipeline,
gunphys, the offline centre-box check, staged rows, cgame hooks). Everything here is STAGED: nothing is in the mod
tree or the fixes pak. Engine: worktree `openmohaa-hzm-ads-smg`, branch `ads-smg-next` (= ads-next 94bb3dca, NO change
so far; built as `G:\mohaa-adsanim3\cgames\cgame_smg1.dll`). Test game: `G:\mohaa-adsanim3` (owner adsanim3, port 12578).

## State (2026-10-12 evening)

| step | state |
|---|---|
| 1. support hand in the aim where the hip has it | **done**, engine-run in every stance + braced (section 1) |
| 2. MP40 reference reload: aimed + hip, rounds left + empty | **done and engine-run in every stance** (section 2); AI firing not yet seen |
| 3. Thompson family, Sten, PPSh, grease gun, Moschetto, Type 100, MP18 | not started; mechanism / mesh survey in section 3 |

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
  released files. Not a missing texture or shader; needs real textures (weapon-HD). Open.
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
| `reload_empty` (hip, empty) | follows the retail cocking hand's index fingertip: forward to frame 60, back by 63 |

Seen in the engine (run sb4, hip): handle back while ready, away from its place during each shot, gone forward once dry.

**Hands, aimed** (firing hand never leaves its grip; no gun key set by hand - `gunphys` class `smg`, new `smg_*` actions):
1. thumb on the catch, hand slides down onto the magazine (frames 3-8); magazine dragged down the well and out
   low-left (10-16): the gun follows it down, then lifts; while the hand is at the pouch the muzzle hangs 1.3 deg low
   (shoulder + firing hand carry it - support weight 0.3, not 0);
2. the new magazine comes up BESIDE the gun on the left, in view under the box (36), drops under the housing, is
   driven up (44-48): the gun is pushed up 0.46 u;
3. rounds left: the hand goes straight back to the housing (58). EMPTY: it goes up the receiver's left side, hooks
   the handle with the index finger from below-left (55) and pulls it back (55-61): the gun comes 1.0 u back into
   the shoulder and cants 0.8 deg; the sear holds the bolt, the hand lets go (63) and is back on the housing (71).

**Hands, hip** (the same story): `mp40_reload` = the retail clip to the seat frame, then its own end pose - the mimed
cock is gone (a gun with rounds left is cocked already); `mp40_reload_empty` = the retail clip with its cocking hand
turned about its own wrist so the index fingertip is ON the handle (the retail mime is 3 u out to the left).

**Engine, run sb4** (`tools/reloadbox.py`; reload found from the probe's anim field; an emptied gun's first 8 frames =
its last shot's flash are left out of the box figure; reference shifted to each frame's background):

| stance, case | centre box beyond the aim (bar 2 %) | sight line max | back on the aim after the row | pose |
|---|---|---|---|---|
| stand, rounds left | 0.6 % | 1.38 deg | 0.06 deg, 0.00 within 0.8 s | 1.00 |
| stand, empty | 1.2 % | 1.38 | 0.06 | 1.00 |
| crouch / prone, empty | 0.1 / 0.7 % | 1.38 | 0.06 | 1.00 |
| lean left / right, empty | 1.3 / 0.5 % | 1.38 | 0.06 / 0.05 | 1.00 |
| braced, empty | 0.2 % | 1.38 | 0.06 | 1.00 |

Offline (every frame, magazine prop drawn): 0.0 % rounds left, 0.5 % empty. GIFs (20 fps, centre box drawn), all
decoded and looked at frame by frame: `evidence/mp40_reload_aimed_roundsleft_sb4.gif`, `..._aimed_empty_sb4.gif`,
`..._aimed_empty_{crouch,prone,leanleft,leanright,braced}_sb4.gif`, `..._hip_roundsleft_sb4.gif`, `..._hip_empty_sb4.gif`.

Known weak points (seen in playback):
* The first 4 frames of every "empty" GIF: the VIEW is still coming back from the 32-round burst (the wall moves).
* The seat lifts the gun in about two frames - a visible hop.
* Aimed, rounds left: almost nothing shows but the magazine top (frames 14-16 and 36-40) and the gun's own sag; the
  hand is on screen for 0.2 s. On target, but quiet. The last 0.6 s is the settled aim (the server's reload is longer).
* The cocking hand reads as a fist beside the receiver; the hooked index is hidden by the hand's own back from the eye.
* Hip, empty: the handle goes back in ONE clip frame (the retail hand's own speed, 6 u in 33 ms); the release keeps
  the retail's splayed open hand. Hip, rounds left: the last 0.5 s is a still hip pose.
* 0.06 deg is left when the row ends and eases to 0.00 in 0.8 s - the engine's re-solve after the held clip, not the
  clip (its fade 6 -> 14 frames changed nothing). Bar 0.05.
* Other guns on the `mp40` rows (silenced MP40, PPS-43, grease guns, MP18, MP40 R2) now play these clips too: the
  hand goes to where the MP40's handle is. Their own meshes come in step 3 (per-weapon rows: `coopr_<weapon>_reload`).
* **AI:** a spawned NCO carries his MP40 as before, but the map's friendly NPC killed him within a second in both
  tries - an AI MP40 FIRING was not seen. Third person: fires and reloads with nothing detached; the handle is too
  small to judge there. The handle's travel per clip is checked offline (table above).

## 3. The other SMGs - mechanism and mesh (survey, nothing built)

All of them fire from an open bolt: handle back when ready, forward when dry, cocked after an EMPTY reload only.

| gun (mesh) | handle, real | movable part on the mesh today (reload / fire clips) |
|---|---|---|
| MP40 (`mp40.skd`, 11 tiks) | left, reciprocates | none -> added (section 2) |
| MP40 R2 (`coop_mp40r2`) | left | `Bone1` moves in fire and reload |
| Silenced MP40 (`mp40silenced.skd`) | left | `eject` bone moves (what it is: to check) |
| MP18 (`coop_mp18`) | right | `Bone2` moves in fire and reload; side magazine, own hip reload |
| Thompson M1A1 (`ThompsonSMG.skd`; gold; 1928d copy) | right side | none (the whole gun is one bone) -> add |
| Thompson 50rd, M1928 (`Thompson50.skd`, `coop_tommy28`) | top | `Bolt` moves in fire and reload |
| Thompson M1A1 remodel (`coop_m1a1dk`) | right side | `chamber` moves in fire only |
| Sten (`sten_smg.skd`) | right | `Sten_Bolt` moves in fire and reload |
| PPSh (`ppsh_smg.skd`) | right, reciprocates | welded into the mesh, no bone -> split |
| Silenced PPS-43 (`ppsh43silenced.skd`) | right | `eject` bone moves (to check) |
| Grease gun + silenced (`greaser.skd`) | M3: crank; M3A1: finger hole under the cover | `Bone1` moves in reload only (cover or bolt: to check) |
| Moschetto / Beretta M38 | right, does NOT reciprocate (returns forward) | `Rechamber` + `Eject_Cover` move |
| Type 100 (`type100.skd`) | right | `bolt` moves in fire only; falls to the Thompson's torso reload |

## Tools (`tools/`)

`takeover.py` regenerates `run_smg.py` (+ `smg_block.py`: `sdemo` / `shipdemo` / `tp` / `ai` captures) and the measure
tools from `..\tools`, repointed at G:\mohaa-adsanim3. `smgpose.py` (aim poses + `handsurvey.json`), `smggun.py`
(handle + open-bolt clips + tik rows for every tik on a mesh), `smgbake.py` (aimed + hip hands; `--box` offline box
check with the magazine drawn, `--cu` close-up of the hand on the handle, `--look`), `stage_rows.py` (fps_anims_smg.txt
= released fixes-pak copy + this lane's rows, `rows_extra.json` from the bake), `mkov_smg.py` (overlay; `--base` =
released rows; adds the AI spawn poll to the plumbing), `reloadbox.py` (engine measure of one capture), `aimpair.py`,
`sideview.py` / `eyepair.py` / `gunside.py` (offline looks), `status_merge.py` / `status_reload.py`, `buglog_add.py`.

    cd smg/assets
    python ../tools/smggun.py mp40 .  &&  python ../tools/smgbake.py mp40 .  &&  python ../tools/stage_rows.py
    python ../tools/mkov_smg.py <SCRATCH>\adssmg\ov_x.pk3
    IRONSIGHT_EXTRA_PAKS=<that pk3> python ../tools/smgbake.py mp40 . --nobake --box --which ads_empty,ads_loaded
    cd ../tools; python run_smg.py <id> --overlay <abs pk3> --cgame cgame_smg1 --guns mp40 --parts sdemo,shipdemo,tp \
        --sstances stand,crouch,prone,standL,standR,braced --yaw 160 --hold 235 --rel 215
    python reloadbox.py <id> mp40__adsE --skip 8 --dump
    python dgif.py <id> mp40__adsE out.gif --frames 283:469:3 --w 400 --crop 240,120,1040,720 --box; python gifsheet.py out.gif sheet.jpg 0:64:1

Reusable by the MG / heavy lane: `smggun.py` (`patch_tik`, `same_mesh_tiks`, the open-bolt clip set - BAR aside, the
belt-feds and the DP-28 are open bolt too), `smgbake.py`'s `hook_rel` (a hand hooked on a handle built from the hand's
own geometry) and the `smg_*` gunphys actions, `reloadbox.py` (background-aligned reference), `smgpose.py`, `gunside.py`.

Harness facts added here: the coop game fires on the tik's `sp firedelay`; `set cheats 1` does not survive the mod's
server start (no `spawn`, no `notarget`; the harness's `dog 1` has been a no-op); aim sway is ON in the shared runner
(`cg_adsSway 0.1`, `cg_weaponBreath 1`) - take still pairs with it off.
