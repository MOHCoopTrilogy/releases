# Gore expansion - limbs, disfigurement, artery spurts (research + design, 2026-10-05)

User asks: *"can we research how to make the gore more realistic? Any potential for limbs, or
disfiguring? I know we had tried that in the past to not much luck (besides the head)."* and *"we do
have a system in place, I just want it expanded upon."* Also queued: *artery hits spurt realistically*
(pulsing jets from neck / thigh / upper-arm hits, synced to a heartbeat, weakening over seconds, blood
decals where the arcs land).

Status: **design only.** No mod or engine file was changed. One offline prototype was run (below). The
in-engine proof run was **not** done - see section 6.

Everything here is framed as an **extension of the shipped gore stack**: the same `Sentient::CoopGore*`
hooks in `ArmorDamage`, the same `com_blood` / `coop_gore*` / `coop_decap*` cvars and budgets, the same
`models/fx/coop_*.tik` + `scripts/coop_blood.shader` asset line, the same replication channels
(attachments via `parent/tag_num`, `entityState.surfaces`, cgame -> renderer bridge).

---

## 1. What exists today (the system we are extending)

All in `openmohaa-hzm/code/fgame/sentient.cpp` unless noted. AI only in coop (bug-785/792 "no gore on
players"); opened for player victims in MP arenas only via `CoopMpGoreSession()` (bug-2799).

| Layer | Mechanism | Anchor |
|---|---|---|
| T1 blood skins | accumulated damage (not health - AI HP is faked at 5000) picks skin index 1/2 on every flesh/uniform surface; 178 composited `_blood1/2/3` textures, 63+51 generated override tiks | `CoopGoreUpdateSkinTier`; `docs/tools/gen_gore_skins.py`, `gen_gore_tiks.py`, `audit_gore_skins.py` |
| Gib skins | explosion deaths jump straight to the heaviest tier (`_blood3`) | `CoopGoreTryGibSkins`, `coop_goreGibSkins` |
| Disfigured face | confirmed headshot kill writes skin 3 (`<face>_blood3`, 28 textures) to the `head` surface only, latched | `CoopGoreDisfigureHead` (bug-1874) |
| T2 drip + pool | looping `coop_blooddrip*.tik` attached to the torso tag; particles carry `collision + bouncedecal coop_bloodsplat`, so drips leave ground marks client-side; corpse pool grows in steps | `CoopGoreTryDripAttach`, `EventCoopGorePoolGrow` |
| T3 wound props | `coop_wound1.tik` crossed quad attached at the LBD hit bone (`gi.CM_GetHitLocationInfo`), 8 per body, oldest recycled | `CoopGoreTryWoundProp` (bug-1876, bug-2191 pivot fix) |
| T4 UV wounds | renderer ray-tests every bullet segment against the CPU-skinned triangles and paints a hole + `#150200` halo into a per-entity copy of the diffuse; client-side, both gl1 and gl2 | `renderergl2/tr_gore.c` (bug-905 skin snap) |
| Headshot kill FX | guaranteed burst + wall splat on the alive->dead edge, brain matter, eyeball prop | `CoopHeadshotKillFx`, `CoopGoreHeadshotExtras` (bug-1142) |
| Death kinetics | corpse shove along the shot; explosions throw `coop_gorechunk.tik` meat (budgeted, 6 s) and roll decap | `CoopGoreDeathKinetics`, `CoopGoreThrowChunks` |
| **Decapitation** | `head` surface -> `MDL_SURFACE_NODRAW`; `HeadGibObject` built from the corpse's own composite with every non-head surface hidden; `coop_stump_neck.tik` cap in a tracked wound-prop slot; 30 % of explosion/shotgun deaths, 3 per server frame, 32 alive | `CoopGoreTryDecapitate` (bug-1875), `object.cpp HeadGibObject`; `gore_decap` script mark |
| Corpse gore | bodies are shootable (flat `CONTENTS_WEAPONCLIP` slab) and every gore layer keeps running on a corpse | bug-1321, bug-1975, `CoopGoreCorpseDamage` |
| Arterial-ish hit spray | cgame chance-layers a second, upward blood burst on hits | `cgame/cg_parsemsg.cpp`, `coop_bloodSpurtUp 75` |
| Blood trails | wounded moving AI drop ground decals; the **only gore host rule in the UI** | `coop_bloodTrail*`, `ui/coop_hostrules.urc` |
| HRRTM blood addon | third-party `zzzzzzz-HRRTM_Blood_effects_Addon.pk3` (installed in maintt): overrides `bh_human_uniform_hard/lite.tik`, `bloodspurt.tik`, `blood_long.tik`, `bloodeffects.shader` - i.e. the stock bullet-hit puffs. Not ours, never repack it | install-side |
| Ragdoll | client Verlet sim; cgame pushes per-channel matrices into the renderer bone cache ("Hook A") | `cgame/cg_ragdoll.c`, `renderergl2/tr_ragdoll.cpp` |

Docs that are **stale** on this (not edited here - flag for whoever next touches them):
`docs/FEATURES.md` still says decapitation `REVERTED` and limb dismemberment `PLANNED`;
`docs/DECISIONS.md` "Reversed twice - decapitation" still says *zero `CoopGoreTryDecapitate` symbols
exist*. The code has had decap live since bug-1875 (re-add) with five follow-up fixes.

## 2. History of past attempts

**Limbs were never built - they were ruled out on paper.** `_research/limb_dismemberment_plan.md`
(July) found the human body mesh is three fused surfaces (`Wehrmact_pants` = hips + both legs,
`Wehrmact_tunic` = torso + both arms, collar), so the surface-nodraw trick that removes a helmet or a
head can only remove half a body. No severed-limb model exists in any of the 40 retail paks; the
engine's own gib path references FAKK-era models MOHAA never shipped (`fx_rgib1..5.tik`,
`fx_bspurt.tik`, `gib1.def`). The fallback that shipped is meat chunks: `coop_gorechunk.tik` on
explosion deaths, and 20 static chunk clusters on the Omaha beach (bug-2231).

**The head is the part that worked - after a long road:**

| Round | What happened | Lesson |
|---|---|---|
| bug-856/861 (07-18) | decap shipped, "AI went all glitchy", pulled | real cause later traced to the entity-pool stomp (bugs 914-927), not decap; but unbudgeted per-death spawns into an 80-man horde are a real load spike |
| bug-866 / 892 | re-done on the engine's gib discipline (dead-gated, **per-frame budget**, tracked slot, precache), then reverted from source as a precaution | the budget pattern is the template |
| bug-1875 (08-1x) | re-added; head = the victim's own composite with all other surfaces hidden (no new art) | reuse the victim's model instead of authoring one |
| bug-1880 | four stacked causes: floating hands, nothing, invisible head | match surfaces **by name**, every surface called `head` |
| bug-1903 / 1906 / 1910 / 1915 | heads floating, five reports: `SOLID_NOT` (no world collision), a settle think parking on the corpse, `MASK_VIEWSOLID` clipmask stopping on trigger brushes, allsolid freeze because the origin sat at the feet | **copy `gibs.cpp`'s recipe exactly** (`SOLID_BBOX + MOVETYPE_GIB + MASK_SOLID`) and handle the allsolid freeze |
| bug-2017 | the fix was inert for 3 days: engine default moved, cfg seed did not | engine default + cfg seed are one decision |
| bug-2191 | wound props swam around the body: one-sided xbeam art + world-axis attach | attach with `use_angles` and centre the art on the tag |

Other relevant reverts: gore round 4 "way too much" (bug-795/796/817) - **intensity needs a user
checkpoint per round**. Decals on skeletal models via `R_MarkFragments` are impossible (world nodes
only) - the T4 UV painter is the substitute and already works.

## 3. Per-feature feasibility

### 3a. Limb removal - HIGH, by a mechanism not tried before: bone-chain collapse in the renderer

Neither per-surface hiding (surfaces are fused) nor per-bone scale (the skeletor has no bone scale; no
`entityState` field carries one) works. But this renderer **CPU-skins every character every frame**
(`RB_SkelMesh`: `p = sum w * (offset * BoneMatrix + BoneOrigin)`), and the ragdoll already proves we can
overwrite the per-entity bone cache after `R_GetFrame` (Hook A in `R_AddSkelSurfaces`,
`renderergl2/tr_model.cpp:1236-1268`, mirrored in gl1). So:

- **Collapse**: for a severed limb, write `matrix = 0, origin = cut-joint origin` into every bone of the
  limb chain (`Bip01 R UpperArm`, `Forearm`, `Hand`, fingers, the matching `helper` bones). Every vertex
  owned by the chain lands on the joint; triangles become degenerate and vanish; seam vertices that
  blend with the parent are pinched into a **closed cone** - the hole closes itself. A stump cap prop at
  the joint (same idea as `coop_stump_neck.tik`) covers the pinch.
- **Keep (the severed limb itself)**: the inverse. Spawn a gib entity using the victim's own composite
  (exactly how the severed head is built today) and collapse *every bone except the chain* to the cut
  joint. Result: only the arm or leg draws - real sleeve, real hand, real boot, every uniform, **no
  per-model art**. Physics = the `HeadGibObject` recipe that bug-1903..1915 finally got right.
- Works on every rig with the Bip01 skeleton, which is every human the ragdoll already runs on.
  Collapsed triangles are degenerate, so the T4 UV painter cannot hit them (no wounds on a missing arm).

**Offline proof (done):** `evidence/limb_collapse_offline.png`, made by `tools/limb_proto.py` from the
real `german_wehrmact_soldier.tik` composite (`heerprivate.skd` + `head1.skd` + `hand.skd`), posed with
the engine-exact skeletor port the ragdoll work already validated
(`ragdoll_2026-09-27/lookdev/tools/skel_extract.py`). Panels: intact; right arm at the shoulder + left
leg at the knee; left arm at the elbow + right leg at the hip; the severed arm in KEEP mode; a
`death_back1` corpse with the same cuts. Every cut closes cleanly. Flat shaded, untextured, the
`HOSEROT/AVROT` helper bones approximated - it proves the **geometry**, not the final look.

**Seam census** (`tools/census.py`, `evidence/seam_census.txt`), vertices per cut:

| model | upper-arm cut | elbow cut | hip cut | knee cut |
|---|---|---|---|---|
| `heerprivate` (950 verts) | 68 gone, 28 seam (clavicle) | 14 / 54 (elbow helper) | 185-190 / **0** | 158 / 9 |
| `airborne` (1222) | 42 / 67 (**Spine2**) | 42 / 39 (Spine2 + elbow helper) | 170 / 38 (hip helper) | 156 / 14 |
| `hand.skd` (604) | 53-60 / 44 (finger bones - must be in the chain) | same | - | - |

Two findings that shape the build: (1) the chain cannot be "descendants of the cut bone" -
`helper Relbow` hangs under the **clavicle** on the right side, and the finger bones live only in
`hand.skd` - so chains are a per-limb **name table**, checked by a census over the whole roster;
(2) the airborne sleeve has vertices blended to `Spine2`, which will make a stretched sliver on an
elbow cut. The census flags any seam partner far from the cut joint, so these models get the
upper-arm cut only, or a per-model exception.

**Networking - no protocol change, no exe change:**
- The **stump cap entity is the carrier.** game.dll attaches `coop_stump_arm.tik` / `coop_stump_leg.tik`
  to the victim at the cut bone (tracked wound-prop slot, as the neck stump is). Attachments already
  replicate `parent` + `tag_num` to every client and to late joiners. cgame, while adding that entity,
  sees "stump model, parent P, tag T" and tells the renderer "collapse T's chain on entity P".
- The KEEP gib carries an invisible `coop_limbkeep.tik` marker attached at its chain root - same rule,
  inverse mode.
- cgame -> renderer: the exe forwards `cgi->R_SetRagdollPose = re.SetRagdollPose` untouched
  (`client/cl_cgame.cpp:904`), so a sentinel call (e.g. `count < 0` = limb record) reaches the
  renderer with **no exe or refexport change**. The cleaner alternative, a new `SetLimbCollapse`
  export, means exe + cgame + renderer ship together (the T4 pairing cost). Recommend the sentinel,
  documented loudly in both files.
- Server side: a per-body `m_iCoopLimbMask` so `CoopGoreTryWoundProp`, drips and new spurts skip hits
  on a missing limb (the server's hit spheres do not know it is gone - otherwise a wound would float
  where the arm was, the bug-2191 look again).

**Triggers** (one new call beside `CoopGoreTryDecapitate`, same gates): explosion / grenade / rocket /
artillery deaths with the limb near the blast; shotgun or MG burst at close range on a limb hit
location; heavy fire into a corpse limb (`CoopGoreCorpseDamage`). Budget per server frame, shared
with decap. Death and corpses only - a live AI never loses a limb (no legless crawler; the anims and
AI do not exist for it).

Ships: game.dll (trigger, mask, gib entity), cgame.dll (carrier scan), renderer gl1 + gl2 (collapse
hook), pk3 (2 stump tiks, 1 marker tik).

### 3b. Disfigurement and wounds - HIGH for extensions of T4; LOW for region skins

- **Region skin swaps (torso/arm/leg overlays): LOW.** The same fused surfaces defeat it: a "left arm
  wound" skin on the tunic would also mark the torso and the right arm. Not worth new art.
- **Wound soak over time: HIGH, renderer-only.** T4 already owns a per-entity diffuse copy and the UV
  of every wound; re-stamp a larger, fainter `#150200` halo at the same UV a few times over ~15 s so
  each hole visibly soaks the cloth around it. Client-side, no art, no network.
- **Exit wounds: HIGH.** The T4 ray test already intersects the far side of the body; for rifles and
  MGs also stamp the exit triangle, larger. Pair with an exit-side spray in `cg_parsemsg.cpp` beside the
  existing `coop_bloodSpurtUp` burst.
- **Face:** already done (`_blood3` face on headshot kills). A second face rung for close shotgun kills
  would need new face art (28 faces) - medium, only if asked.

### 3c. Artery spurts - HIGH, game.dll + pk3 only

- **Detection:** `ArmorDamage` already has `location` (`HITLOC_NECK`, `HITLOC_R/L_ARM_UPPER`,
  `HITLOC_R/L_LEG_UPPER`) and the MOD. Bullet MODs, chance-gated, alive or killing blow.
- **Emitter:** a new `models/fx/coop_artery.tik`, a re-skin of `coop_blooddrip.tik`, attached at the
  LBD bone for that location (same `gi.CM_GetHitLocationInfo` lookup T3 uses, tracked slot, auto-removed
  with the body). Its streak particles keep `collision + dietouch + bouncedecal coop_bloodsplat`, so
  **every arc leaves a decal where it lands**, client-side, already proven by the drip.
- **Heartbeat:** a pulse is a burst on a frame, not a constant rate. Give the tik three looping anims on
  a small dummy `.skc` (authorable with the existing `ironsights_2026-09-28/blender/skc_io.py`):
  `pulse_strong` / `pulse_mid` / `pulse_weak`, ~0.8 s cycles, each with a frame-0 `tagspawn` burst
  (frame-keyed client commands on anims are proven - `new_generic_human.tik` spawns the cigarette on
  frame 21). game.dll steps strong -> mid -> weak -> remove (~3 + 4 + 4 beats); on death it jumps to
  weak and dies fast, because pressure drops when the heart stops. Zero network traffic after the
  attach.
- **Clutching:** retail has `death_choke` / `death_choke2` (neck), `*_stand_hit_leg`, `*_stand_hit_rarm`,
  `a_11_headwound*`, `a_11_jogshoulderwound_cycle`. Forcing `death_choke` on neck kills is cheap if the
  death-anim pick can be steered (to verify); living clutch-while-fighting is not worth it.
- Players excluded in coop (bug-792), on in MP arenas through `CoopMpGoreSession()`.

### 3d. Explosions, mist, gibs - HIGH (all extensions)

- Blast deaths: replace part of today's chunk spray with **real limbs** from 3a (1-2 limbs + head on a
  close blast; all four on a direct hit = torso + flying limbs). Chunks stay as filler.
- Blood mist: a short `coop_bloodcloud`-style puff at the hit on rifle/MG hits (exists for underwater).
- Note: `Gib::Splat` is SP-gated (`gibs.cpp:141`); do not revive the retail Gib class - keep to the
  `HeadGibObject` recipe.

## 4. Performance, isolation, settings, rating

- **Cost:** the collapse is a write of a few bone matrices per affected entity per frame - nothing. A KEEP
  gib skins the full composite (~2-3k verts) to draw an arm, the same price the severed head pays today;
  bound by the shared per-frame budget and a ring cap (like `coop_decapMax`). Artery emitters: cap ~4
  concurrent (drips already cap ~8); decals ride the client's recycled mark pool.
- **MP isolation:** new code lives inside the existing gore functions, behind the existing
  `IsSubclassOfPlayer() && !CoopMpGoreSession()` gates; `check_mp_isolation` must stay 22/22.
- **Settings:** today only Blood Trails is in the host rules. Add one **Gore** host rule
  `coop_goreLevel 0/1/2` = Off / Standard (today's set) / Realistic (+ limbs, artery, soak, exit). It
  maps onto the existing master cvars rather than replacing them, and `com_blood 0` still kills
  everything. Seed it in `coop_defaults.cfg` **and** as the engine default (bug-2017).
- **Rating / distribution:** retail MOHAA is a Teen title; dismemberment is Mature-tier content. It is a
  free mod, but the release notes and the ModDB page should say so, the default should stay
  **Standard**, and Realistic should be an explicit opt-in. Germany: the game already ships with blood
  toggles; nothing here is new in kind, only in degree.

## 5. Phased build plan with gates

| Phase | Scope | Ships | Gate |
|---|---|---|---|
| **A. Artery spurts** | trigger + `coop_artery.tik` + 3-anim dummy skc + staged heartbeat; neck kill -> `death_choke` if steerable | game.dll + pk3 | one in-engine GIF of a neck and a thigh hit (arc, decals, fade); user intensity checkpoint |
| **B. Wound soak + exit wounds** | T4 re-stamp over time; exit stamp; exit-side spray | renderer gl1+gl2 + cgame | before/after stills at 10 m; user checkpoint |
| **C0. Limb collapse proof** | renderer hook behind a dev cvar (`r_coopLimbTest <chain>` on every skeletal entity) - no game code | renderer gl2 only, sandbox | in-engine still matches the offline image on 3 models (heer, airborne, SS) |
| **C1. Limbs on corpses** | carrier scan, sentinel bridge, stump tiks, `m_iCoopLimbMask`, triggers on blasts + corpse damage, roster census tool | game.dll + cgame + renderer + pk3 | 20 blast kills, zero floating parts, zero stuck heads/limbs; entity count flat under an 80-AI grenade test |
| **C2. Flying limbs** | KEEP-mode gib entity on the `HeadGibObject` recipe | game.dll + cgame | lands on ground on 3 maps incl. a trigger-carpeted one (bug-1910) |
| **D. Settings** | `coop_goreLevel` host rule + seeds + release-note line | pk3 + game.dll | menu round trip; `com_blood 0` kills all |

Order is cheapest-first: A and B need no new mechanism; C carries the risk and is staged so C0 can kill
it in one sandbox run before any gameplay code exists.

## 6. Cost estimate (honest)

| Phase | Code | Art | Agent sessions | Risk |
|---|---|---|---|---|
| A | ~200 lines game.dll | 1 tik + 1 tiny skc, reuse drip sprites | 1 + a playtest | low |
| B | ~120 lines renderer x2 + ~40 cgame | none | 1 | low |
| C0 | ~60 lines renderer | none | 0.5 (+ an engine build and a slot) | low - it is Hook A's pattern |
| C1 | ~350 lines across 4 binaries | 2 stump caps (crossed quads like the neck stump first; a modelled cap later) | 2-3 + 2 playtests | **medium** - ragdoll interplay, seam slivers on some models, the pairing |
| C2 | ~150 lines | none | 1 + a playtest | medium - the five-round history of the heads |
| D | ~60 lines + urc | none | 0.5 | low |

Total ~6-7 sessions and ~5 playtests. Per-model art: **none** - the collapse/keep pair is what makes
limbs affordable. The decap history says to budget one extra round for physics surprises in C2.

**Not done in this session:** the in-engine proof. It needs a renderer build in an isolated engine copy,
a private harness install and a test slot (the queue held four topics). The offline image proves the
deformation with the real mesh, weights and skeleton; C0 is the one-run in-engine gate.

## 7. Questions for the user

1. Limbs on **corpses and blast deaths only**, or do you also want limbs shot off a living soldier as
   the killing blow from a heavy weapon (still death-only, just from bullets)?
2. Which weapons may sever: explosives only, or also shotguns and MGs at close range?
3. Should flying limbs persist like heads (`coop_decapLife 0`) or fade?
4. Artery spurts: should a hit artery also **bleed the AI out** (gameplay: a neck hit kills in a few
   seconds), or stay purely visual?
5. Do you want the three-level **Gore** setting (Off / Standard / Realistic) in the host rules, and
   should Realistic be the default or opt-in?
6. Players: keep the coop rule "no gore on players" for the new effects too (MP arenas excepted)?

## Files

- `tools/skd_collapse.py` - SKMD surface/weight parser
- `tools/census.py` - seam census per limb cut (stdin: skd paths)
- `tools/limb_proto.py` - the offline collapse / keep render (reads retail paks read-only)
- `evidence/limb_collapse_offline.png` - md5 `7a526323a18f93c819a022e32f897068`
- `evidence/seam_census.txt`
