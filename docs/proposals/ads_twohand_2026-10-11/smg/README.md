# SMG lane of the aimed-animation work (started 2026-10-12)

Scope: the `## smg` rows of `..\coverage.md` (18 weapons). Method = `..\README.md` (the standard, the bake pipeline,
gunphys, the offline centre-box check, staged rows, cgame hooks). Everything here is STAGED: nothing is in the mod
tree or the fixes pak. Engine: worktree `openmohaa-hzm-ads-smg`, branch `ads-smg-next` (= ads-next 94bb3dca, NO change
so far; built as `G:\mohaa-adsanim3\cgames\cgame_smg1.dll`). Test game: `G:\mohaa-adsanim3` (owner adsanim3, port 12578).

## HANDOVER (2026-10-12 night) - read this first

| step | state |
|---|---|
| 1. support hand in the aim where the hip has it | **done** (section 1) |
| 2. MP40 reference reload + 2b leftovers | **done**, runs sc1-sc3, every stance incl. crouch-leans; break-offs run; open: the 0.06 deg at the row's end (bug-3597, waits for the pistol lane's fix on ads-next - NOT merged, ads-next only carries a diagnostic so far) (section 2) |
| 3. own reload on its own mesh: Silenced MP40, MP40 R2 | **built and run** (section 3) - see the table there for what is still open on each |
| 3. MP18, PPS-43, grease guns, Thompsons, Sten, PPSh, Moschetto, Type 100 | NOT done. Tools and facts are ready (section 3: which bone, which hand, reach); nothing of these guns is staged |
| 4. MP18 flat brown | was its imported textures; a new skin is approved (docs dc7a8d1), nothing changed here |

ads-next has moved on since this branch was cut (d2a6d31b: the held gun draws surfaces named `coop_round<N>` only while
N <= rounds in the gun, cvar `coop_vmRoundSurfaces` - no SMG has such surfaces; 191f1879: a diagnostic for bug-3597).

**Next, in this order.** (a) When the coordinator says bug-3597 landed: merge ads-next into ads-smg-next, build
`cgame_smg2`, re-run `sdemo` for the MP40 and read `back on the aim after it`. (b) MP18 - the only right-side handle
the FIRING hand can reach (94 % of the arm); its own first-person clip already cocks with the right hand, so use
`cock='R'` (ready in smgbake) on a `GUNS['mp40_mp18']` entry built from `viewmodel/coop_reload/mp18_reload.skc` (side
magazine: out f16-20, in f36-44, gun's drum hidden f12-44, prop f10-46; the clip's right hand mimes 3.7 u ahead of the
handle - move it on). Its hip row lives in the SHARED `anims_shared.txt` (`coopr_mp40_mp18_reload`): a patch script with
its hunk, not a staged copy. COORDINATOR, 2026-10-12: the MP18's new skin is approved and in the fixes-pak sources (docs
dc7a8d1, `textures/coop_mp18/{body,clip,drum,front,stuff}`; NOT in the harness paks until the next deploy - staged
copies in `docs/proposals/mp18_skin_2026-10-12/assets`, put them in the overlay to judge); its AIM VIEW shows the butt
plate / rear of the stock badly (flat, close to the eye) - that belongs to the MP18's aim pose work: an own
`coopr`-style aim pose is not possible (the aim row is per prefix), so look at the sight relief / the rig solve for
this weapon first (`aimpair.py`, sights.json `relief`) and judge it against the new sheets. (c) The handles out of reach (PPS-43, Type 100, Moschetto; table in section 3): a lowered
work pose - decide with the coordinator. (d) Thompsons (M1A1 / gold / 1928d: add a handle as on the MP40;
50-round / M1928: the `Bolt` already rests BACK), Sten, PPSh (split), grease guns (nothing moves on the mesh: cover
+ bolt have to be built).

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
handle, fingers half closed into a hook (was a flat open hand), eased to the hip grip after the pull (no splay).

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
`..._hip_empty_sc3.gif`; every stance on one sheet: `evidence/mp40_reload_aimed_empty_stances_sc1.jpg`.

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
| Silenced MP40 (`mp40silenced.skd`) | built, run sc2 + sc6 | a real knob on bone `eject`, left; the retail clips slam it back and forward at the END of every reload | sc6 (aim sway off): rounds left 0.0 %, empty 0.3-0.8 % in stand / crouch / prone / leans / crouch-leans / braced; back on the aim 0.06 deg | with aim sway ON the same clips read 2.4-4.0 % in three stances (sc2): the gun is drawn close to the eye and the sway alone carries it out of the aim's own mask - the measure, not the reload. Hip, empty: the hand is open until it closes on the knob; at the end of the aimed pull the index sits under the knob's stem. Per-shot knob travel not looked at in the engine |
| MP40 R2 (`coop_mp40r2`) | built, run sc4 | `Bone1`, left; the pack's clips already rest it back (its reload = the EMPTY story) | sc4: rounds left 0.1 %, empty 0.0-0.7 % in all eight; back on the aim 0.06 deg (braced 0.02) | hip, empty: the same open hand on the reach. Per-shot travel not looked at in the engine. The mesh is near-black in the offline renders (its texture), fine in the engine |
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

Evidence: `evidence/mp40silenced_reload_{aimed,hip}_{roundsleft,empty}_sc6.gif`, `mp40silenced_reload_aimed_empty_stances_sc6.jpg`;
`evidence/mp40r2_reload_{aimed,hip}_{roundsleft,empty}_sc4.gif`, `mp40r2_reload_aimed_empty_stances_sc4.jpg`,
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
`brkmarks.py` (what the rig did through a break-off), `eyezoom.py` (the eye's picture offline, cropped, at game size),
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
