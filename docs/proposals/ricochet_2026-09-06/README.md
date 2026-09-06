# Bullet ricochet off metal - research and design (2026-09-06)

Research only; no project file was edited. Every `file:line` below was read this session, not
recalled. Engine paths are under `openmohaa-hzm/code/`, mod paths under `hzm-mohaa-coop-mod/`.

## TL;DR

* The server already knows the material of every world hit (`trace.surfaceFlags`), already
  stops the round at exactly one decidable point, and already has a spare-slot message channel
  to the client. A ricochet is one extra trace and one extra message per deflection.
* **A ricochet whine already exists on the client and is effectively dead** (T3 shape): it lives
  in `CG_MakeBulletHoleSound` (`cgame/cg_parsemsg.cpp:85-101`), which is reached only from the
  `iNumImpacts > 2` branch (`:843`). A single round striking metal collects exactly one impact
  and takes the other branch (`:948-961`), which plays `snd_bh_metal` and never calls the whine.
  In practice only shotgun volleys can hear it. The aliases were once unloaded too (fixed,
  `ubersound/ubersound.scr:866-871`); the reachability veto was never noticed.
* **TIKI-model hits carry no material bit.** Every `SOLID_BBOX` entity is traced against the
  temp box hull whose sides are created with `surfaceFlags = 0` (`qcommon/cm_load.c:1550`), and
  TIKI surface flags have no material at all (`tiki/tiki_shared.h:101-108`). Tank hulls and
  MG42 shields therefore reach the client as `CGM_BULLET_7` = stone (`fgame/weaputils.cpp:3043-3052`).
  Metal-ness for models must come from an entity-class allowlist, not the trace.
* Verdict: feasible, engine-side (`game.dll` + `cgame.dll` as a pair), ~250 lines. See the end.

## 1. The bullet path today

**Fire -> notetrack -> Shoot -> BulletAttack.** `Weapon::Fire` (`fgame/weapon.cpp:3564-3617`)
spends ammo and plays the fire anim; it does not trace. The TIKI notetrack `shoot` is the
`EV_Weapon_Shoot` event (`weapon.cpp:46-52`) -> `Weapon::Shoot` (`:1820`) -> `case FT_BULLET`
(`:1967`) -> `BulletAttack(...)` (`:2337-2359`) with `bulletthroughwood[mode]` /
`bulletthroughmetal[mode]` (`:2302-2303`). Player-only extras on top of the tiki values:
`g_bulletThroughWood 100`, `g_penChance 0.1`, `g_bulletThroughAny 70` (`:2305-2318`).

**Turrets use the same path.** `weapturret.cpp` overrides neither `Fire` nor `Shoot` (only
`AI_DoFiring` `:1485` and `FireDelay` `:2372`); it calls `Fire(FIRE_PRIMARY)` at `:909`, `:943`,
`:1586`, `:1669`. AI-manned turret dispersion is `m_vAIBulletSpread` (bug-1940), applied at the
muzzle, so an MG42 burst is N separate single-round `BulletAttack` calls.

**`BulletAttack`** (`fgame/weaputils.cpp:2554-3292`, signature `:2554-2576`):

| step | anchor |
|---|---|
| `MAX_TRAVEL_DIST = 16216` - `range` only shapes the aim vector (bug-2439) | `:43`, `:2776-2780`, `:2790-2793` |
| Two extra full-range traces per fire event ALREADY exist (player-suppression `:2631`, AI-suppression `:2690` + `findradius`) - the baseline cost a ricochet is compared to | `:2621-2702` |
| Caliber table replaces the tiki penetration numbers (bug-2095) | `:2746-2757` |
| Per-pellet loop, `count` clamped to 63, `vEndArray[64]` | `:2711-2713`, `:2594`, `:2773` |
| Inner trace: `G_Trace(..., newowner, MASK_SHOT_TRIG, false, "BulletAttack", true)` (traceDeep = bone hitboxes) | `:2803-2805` |
| Penetration exit trace `"BulletAttack2"` from the far side back 4u; stop if the material is not penetrable | `:2813-2837` |
| Damage lost through the thing: `newdamage -= damage * thickness * 2/(powIn+powOut)`; done when `< 1` | `:2844-2883` |
| Damage applied per hit: `ent->Damage(world, owner, newdamage, endpos, dir, plane.normal, knockback, dflags, meansofdeath, location)` - attacker = `owner`, so team / boss / XP rules key on it | `:2966-2977` |
| Impact messages, one per hit entity (world hits send NOTHING - the client draws those itself, section 3): bbox+surface-typed -> `CGM_BULLET_6`; sentient -> `CGM_BULLET_8` (flesh); bbox `CONTENTS_SOLID` -> `CGM_BULLET_7` (stone); `SOLID_BSP` -> `CGM_BULLET_6` | `:2991-3062` |
| Continue-or-stop decision: pass through foliage/glass/puddle/paper/water; wood with power; **metal/grill with power and `iContinueCount < 5`**; `bulletthroughany`; fence brushes lose `2*damage/power` and stop; **else the round stops here** | `:3065-3140`, stop at `:3136-3139` |
| Tracer bookkeeping: every `iTracerFrequency`-th round sets `iTracerCount` | `:3175-3182` |
| Final volley message: `count==1` -> `CGM_BULLET_1` (barrel+start+end, tracer) or `CGM_BULLET_2` (no tracer); `count>1` -> `CGM_BULLET_3/4` with a 6-bit count and up to 63 end points | `:3202-3279` |

So one shot can cross up to 5 metal/wood/any layers plus unlimited foliage-class surfaces, and
the client receives one *segment* message per volley plus one *impact* message per entity hit.
`actor.cpp:6300-6325` (`EventDamagePuff`) also emits `CGM_BULLET_8` for scripted blood puffs.

## 2. How the surface is known

**Bits.** `qcommon/surfaceflags.h:93-107`: `SURF_PAPER 0x2000`, `SURF_WOOD 0x4000`,
`SURF_METAL 0x8000`, `SURF_ROCK 0x10000`, `SURF_DIRT 0x20000`, `SURF_GRILL 0x40000` (grate),
`GRASS`, `MUD`, `PUDDLE`, `GLASS`, `GRAVEL`, `SAND`, `FOLIAGE`, `SNOW`, `CARPET`;
`MASK_SURF_TYPE` is the OR of those fifteen (`:119-121`). Metal-for-ricochet purposes is
`SURF_METAL | SURF_GRILL` - the same pair the penetration code treats as one class (`weaputils.cpp:3073`).

**World brushes.** The flags come from the BSP's baked shader lump in `CMod_LoadShaders`
(`cm_load.c:124-125`), not from any runtime `.shader`, which is why bug-2314 had to retype the
Omaha hedgehog clip brushes at clipmap load: `cmpatch/<map>_metal.txt` ORs `SURF_METAL` into
every side of each listed brush (`cm_load.c:1324-1400`, banner `^~^~^ CMPATCH` at `:1396`,
sides not brushes because `cm_trace.c` reads `leadside->surfaceFlags`). Only
`cmpatch/m3l1a_metal.txt` exists (106 lines); every other map's hedgehog clips are untyped.
Hedgehogs themselves are render-only static models with no collision (`cm_load.c:1330-1333`).
The trace runs on the client too (same `cm_load.c`), so both sides agree on the retyped brushes.

**Entities.** `server/sv_world.c:530-623` (`SV_ClipMoveToEntities`): a character with
`traceDeep` goes through `SV_TraceDeep` (`:582-591`, bone spheres -> `location`, no surface);
everything else uses `SV_ClipHandleForEntity` -> `CM_TempBoxModel(mins, maxs, contents)`
(`:43`) -> `CM_TransformedBoxTrace` (`:595-599`). The temp box hull is built once by
`CM_InitBoxHull` with `box_brush->contents = CONTENTS_BBOX` (`cm_load.c:1536`) and
**`s->surfaceFlags = 0` on all six sides (`:1550`)**. A `SOLID_BSP` entity (a script_model whose
model is a `*N` submodel) traces against real brushes and does get its shader's flags.

**TIKI has no material.** `tiki/tiki_shared.h:101-108` lists `TIKI_SURF_SKIN1/2/3`, `NODRAW`,
`CROSSFADE`, `NODAMAGE`, `NOMIPMAPS`, `NOPICMIP` - nothing for effects. There is no
per-tiki `surfacetype`, and nothing on either side reads the hit model's shader.

**Consequence, measured in the code, not guessed:** a round stopping on a `SOLID_BBOX` tank
hull or MG42 shield has `trace.surfaceFlags == 0`, fails the `MASK_SURF_TYPE` test at
`weaputils.cpp:2992`, is not a sentient, and falls into the `CONTENTS_SOLID` branch that sends
`CGM_BULLET_7` (`:3043-3052`). The client maps `CGM_BULLET_7` to `SFX_BHIT_STONE_LITE`
(`cg_parsemsg.cpp:1807-1815`), and when it re-traces such a hit itself `CG_MakeBulletHole`'s
`switch (iSurfType)` takes `default:` = stone (`:354-357`). So today every model hit is a stone
spark. Metal for models has to be decided by class on the server: `IsSubclassOfVehicle()`
(`fgame/simpleentity.h:84`), `IsSubclassOfTurretGun()` (used `weaputils.cpp:3196`),
`IsSubclassOfVehicleTurretGun()` (used `VehicleTank.cpp:81`).

## 3. The client side

All of it is `cgame/cg_parsemsg.cpp`.

**Decode** (`CG_ParseCGMessage_ver_15`, `:1691`): the type is 6 bits (`:1705`), so 64 slots;
the ver_15 enum (`fgame/bg_public.h:764-807`) uses 0..41 and `BG_MapCGMToProtocol` is the identity
for protocol >= 15 (`bg_misc.cpp:392-399`). `hud.cpp`, which names extra `CGM_HUDDRAW_*`
types, is not in `fgame/CMakeLists.txt`, so the enum above is the complete live list: **22 spare
type slots**. An unknown type is `cgi.Error(ERR_DROP, "CG_ParseCGMessage: Unknown CGM message
type")` (`:2143-2144`) - a stale `cgame.dll` is dropped, not desynced.

* `CGM_BULLET_1/2/5` and `3/4`: read barrel/start/end(s), 2-bit large, optional 10-bit tracer
  speed, then `CG_MakeBulletTracer(...)` (`:1708-1784`). **Every decoder passes
  `bIgnoreEntities = qtrue`** (`:1741`, `:1743`, `:1782`, `:1959`, `:1982`).
* `CGM_BULLET_6..11`: pos + 8-bit dir + large into `wall_impact_*` / `flesh_impact_*`
  (`:1785-1863`), capped at `MAX_IMPACTS 64` per frame with a **silent** drop (`:1799`);
  `CGM_BULLET_11` is the explicit metal type (`:1851-1859`) - nothing on the server sends it today.

**Queue.** `CG_MakeBulletTracer` (`:1048-1116`) copies the volley into `bullet_tracers[32]`
/ `bullet_tracer_bullets[1024]` (`:46-47`), prints on overflow (`:1090-1098`), and relocates a
volley whose start is within 48u of the local eye to the view-weapon muzzle (`:1067-1088`).
`CG_AddBulletTracers` (`:1118-1137`) drains it once per client frame.

**Draw + re-trace.** `CG_MakeBulletTracerInternal` (`:487-1046`) runs, per volley: muzzle smoke,
barrel wisp, heat haze, muzzle light, distant-fire tails (`:558-647`); UV gore (`:657-663`);
then, per bullet, a world-only `CM_BoxTrace` re-trace from start to end+32 (`:705-716`),
collecting each impact into `tImpacts[128]` (`:739-742`), drawing the tracer once
(`:744-747`, `CG_BulletTracerEffect` `:405-485` - **nothing is drawn for a segment under 150u**
`:432-434`, the beam starts 450-600u down the line `:415`, `:427`, `:446`, width x `cg_tracerGlow`
`:455`), and continuing only through HINT/NODLIGHT/SNOW/FOLIAGE/DIRT/water (`:750-752`).
Impacts are turned into holes at `:843-961`: with `> 2` impacts the four nearest get
`CG_MakeBulletHoleSound` (`:896-927`, the only callers), otherwise `CG_MakeBulletHole(...,
bMakeSound = qtrue)` (`:948-961`) whose sound comes from `CG_MakeBulletHoleType` (`:182-244`).
Server-sent impacts are consumed separately by `CG_AddBulletImpacts` (`:1139-1321`), which also
ends in `CG_MakeBulletHole(NULL, qtrue)` (`:1314-1318`). Neither reaches the whine.

**Can the existing event carry a bent tracer?** Mechanically yes - a second `CGM_BULLET_1` with
barrel = start = impact point draws a tracer from the impact - but every muzzle-side block above
would run at the impact: a muzzle puff (15%), a barrel wisp (25%), a muzzle light, and, for a
distant impact, a *gunshot report* (`coop_gun_tail_*` `:641`, `snd_gun_tail_*` `:986-992`).
The correct move is a new type decoded into the same queue with a `bRicochet` flag, so the body
skips `:558-647` and the muzzle relocation, and instead plays the whine and a spark.

**Sounds.** `ubersound/ubersound.scr:878-882`: `snd_b_ricochet1..3` -> `sound/coop_ric/ric_01..03.wav`,
`0.9 0.1 1.0 0.08 200 1700 auto loaded maps "m e t"` (prefix filter covers the whole trilogy);
`snd_b_zing1..9` (`:883-891`) are the retail `Wpn_WhizBy` set; `snd_b_impactsnap1..3` (`:875-877`).
A bare `snd_b_ricochet` resolves to a random numbered member via `Alias_ListFindRandom`
(`qcommon/alias.c:464-478`). Retail ships no ricochet audio (`:878`). The client master switch
`coop_ricochet` is seeded `1` (`coop_defaults.cfg:435`).

**Where the whine and zing live now.** Whine: `:85-101` (`coop_ricochet`, 30% roll, 260 ms
rate limit, `SURF_METAL|ROCK|GRILL`) inside `CG_MakeBulletHoleSound` - unreachable for single
rounds as shown above. Zing/suppression: closest approach of each segment to `cg.SoundOrg`
(`:804-841`), then `CG_AddSuppression((1 - d/255) * 0.75)` (`:1004-1006`, `cg_view.c:1595-1603`),
the 2D supersonic crack (`:1026-1034`) and up to three positional `snd_b_zing` (`:1036-1044`).
A deflected segment fed through the same body gets all of this for free.

## 4. Design - the smallest thing that is real on listen and dedicated

Server-authoritative: the deflection, the secondary trace and the damage happen in `game.dll`
inside `BulletAttack`; the client only draws and plays what it is told. Nothing is mod-script.

**4.1 Hook point.** At the top of the `if (trace.fraction < 1.0f)` block (`weaputils.cpp:3065`),
*before* the penetration test - a grazing round that ricochets must not also punch through, and
with the caliber table most guns have `penMetal > 0`, so a metal world hit would otherwise take
the `iContinueCount < 5` branch (`:3073-3075`) and never reach the stop at `:3136`. The hook
sees `trace`, `vDir`, `vTmpEnd`, `ent`, `newdamage`, `owner`, `bulletlarge`, `bulletbits`.

**4.2 Is it metal?**
`bMetal = (trace.surfaceFlags & (SURF_METAL | SURF_GRILL))` - world brushes, bmodel
script_models, cmpatch'd hedgehog clips - OR, when `coop_ricochetEntMetal` and the hit is a
`SOLID_BBOX` entity with `surfaceFlags == 0`: `ent->IsSubclassOfVehicle() ||
ent->IsSubclassOfTurretGun() || ent->IsSubclassOfVehicleTurretGun()`. Exclude sentients.

**4.3 Angle and roll.** With `D = vDir` (unit) and `N = trace.plane.normal` (faces the shooter,
so `D.N < 0`): `cos_i = -(D . N)`; incidence from the normal `theta_i = acos(cos_i)`. Grazing
iff `theta_i > coop_ricochetAngle` (55 deg), i.e. `cos_i < cos(55 deg) = 0.5736`. Then
`G_Random() < coop_ricochetChance` (0.25). Optional ramp: scale the chance by
`(theta_i - 55) / 35` so a 90-degree graze always spins. Box-hull normals are axis faces
(`cm_load.c:1553-1565`), so the angle against a tank's bbox face is what gets tested.

**4.4 Reflect with a small cone.** `R = D - 2 (D . N) N`; jitter
`R' = normalize(R + (P1 * crandom() + P2 * crandom()) * tan(coop_ricochetCone))` with `P1, P2`
any perpendicular pair to `R` (6 deg default).

**4.5 One secondary trace, no recursion.** `s2 = vTmpEnd + N * 1.0` (off the surface);
`e2 = s2 + R' * coop_ricochetRange` (2048); `tr2 = G_Trace(s2, vec_zero, vec_zero, e2, owner,
MASK_SHOT_TRIG, false, "CoopRicochet", true)` - same mask and traceDeep as the primary so it hits
bone hitboxes with a `location`. Discard if `tr2.ent->entity == ent && tr2.fraction < 0.01`. The
round then ends: `trace.fraction = 1; bBulletDone = qtrue;` and skip the rest of the block.

**4.6 Damage.** If `tr2.ent->entity` is `takedamage` and not `world`:
`hit->Damage(world, owner, newdamage * coop_ricochetDamage, tr2.endpos, R', tr2.plane.normal,
knockback * coop_ricochetDamage, dflags, meansofdeath, tr2.location)` - identical shape to
`:2966-2977`, attacker = original `owner`, so bug-135's directional boss protection, team rules,
the headshot hook in `Sentient::ArmorDamage` (bug-1142), hit markers (bug-2161) and XP all see a
normal bullet from the same shooter. Send the secondary's impact message with the same three
cases as `:2991-3062` (factor them into `static void CoopSendImpactCGM(...)`); the flesh case
matters because the client re-trace ignores entities and would otherwise show no blood.

**4.7 The deflected segment on the wire.** New `CGM_RICOCHET` appended after `CGM_FENCEPOST`
(`bg_public.h:806`, value 42 of 64). Server: `gi.SetBroadcastVisible(vTmpEnd, tr2.endpos)`;
`StartCGM`; impact xyz; end xyz; `WriteBits(bulletlarge, bulletbits)`; `EndCGM`.
Cost per message: coords are 19 bits (`sv_game.c:347-357`, `msg.cpp:660-668`), dir 8 bits,
type 6 + 1 continuation bit -> **123 bits ~ 15.4 bytes on the wire**, **27 bytes** in the
per-client staging buffer (`MSG_WriteCGMBits` stores 19-bit values as 4 bytes, `sv_game.c:180-213`).
For comparison an existing tracer volley is ~23 wire / 40 staging bytes and an impact ~9 / 16.
Client: `case CGM_RICOCHET:` -> `CG_MakeBulletTracer(vImpact, vImpact, &vEnd, 1, iLarge, qtrue,
qtrue, 1.0f, /*bRicochet*/ qtrue)`; add `qboolean bRicochet` to `bullet_tracer_t` (`:36-44`);
in `CG_MakeBulletTracerInternal` when set: skip `:558-647`, skip the muzzle relocation
(`:1067-1088`), play `snd_b_ricochet` at `i_vBarrel` (rate-limit ~120 ms, pitch jitter as `:99`),
`sfxManager.MakeEffect_Normal(SFX_BHIT_METAL_HARD, i_vBarrel, R')` for the spark, then let the body
draw the tracer, re-trace the segment for the far hole, and run the zing block. Gate the old
cosmetic whine at `:95` behind a new `coop_ricochetCosmetic` (default 0) so a whine now means a
deflection happened.

**4.8 Adjacent one-liner worth taking:** at `:3045` send `CGM_BULLET_11` instead of
`CGM_BULLET_7` when the class allowlist matches, so tank hulls and MG42 shields spark metal even
on the 75% of hits that do not ricochet - the half of bug-2314's user ask that `cmpatch` could not reach.

**4.9 Cvars.** Server, `game.dll`, **pre-registered in `G_InitGame` per T7** (a script `getcvar`
would otherwise create them empty): `coop_ricochetChance 0.25`, `coop_ricochetAngle 55`,
`coop_ricochetDamage 0.4`, `coop_ricochetRange 2048`, `coop_ricochetCone 6`,
`coop_ricochetEntMetal 1`, `coop_ricochetAI 1` (AI rounds may ricochet into players),
`coop_ricochetDebug 0`. Client: `coop_ricochet` (existing, FX master), `coop_ricochetCosmetic 0`.
Names deliberately do not collide across the two DLLs (T3 pair tell).

**4.10 Probe lines.** Server, gated by `coop_ricochetDebug`:
`gi.Printf("^~^~^ RICO t=%.1f own=%d surf=0x%x ent=%d cls=%s cos=%.2f -> hit=%d '%s' dmg=%.1f len=%.0f\n", ...)`
printed OUTSIDE the roll so misses are counted too (T14-1). Client:
`cgi.Printf("^~^~^ RICO-CL from=(%.0f %.0f %.0f) len=%.0f\n", ...)` in the decoder. Force the
branch (T14-3) with `coop_ricochetChance 1; coop_ricochetAngle 0`; every metal hit must then
print one `RICO` and one `RICO-CL`, on the dedicated harness and on a listen server, with
`developer 1`. `m3l1a`'s 106 retyped hedgehog brushes are the test range.

## 5. Risks

* **Per-shot cost.** Turrets share the path (section 1). Each `BulletAttack` already performs two
  extra full-range traces plus a `findradius` for suppression (`:2621-2702`); the ricochet adds
  one trace on at most `chance` x (grazing metal hits). Four MG42s at ~20 rounds/s each add at
  most ~20 traces/s. Negligible.
* **Event budget - silent on the server.** Staging buffer `CGM_DATA_SIZE 4096` bytes per client
  per frame (`sv_game.c:135`), broadcast refused at `cursize >= 3968` (`:435`, `:499`), and the
  overflow is a `Com_DPrintf` rate-limited to one per 5 s (`:165-178`) - invisible in production
  (T3). Today an MG round costs ~56 staging bytes, so ~70 rounds per server frame before drops;
  ricochets add 27 (+16 for a flesh hit) each. Client: `MAX_BULLET_TRACERS 32` volleys per
  frame with a `Com_Printf` (`:1090-1098`), `MAX_IMPACTS 64` with no print (`:1799`). Fine at
  coop scale; add a `^~^~^` line at the server overflow while in there (T3: "add the warning
  even though you raised the limit").
* **Entity pool / protocol.** Zero entities: the beam is a client refentity, the sound a
  channel. None of the 2048/4096 constants (bugs 914-934, 1186, 2283, 2291) are touched. But the
  enum lives in `bg_public.h`, compiled into both DLLs, and a stale `cgame.dll` `ERR_DROP`s on the
  first ricochet (`:2143-2144`): **ship `game.dll` + `cgame.dll` together**, the same pair rule
  as `bg_pmove.cpp` (T10, bug-2149). Remote clients need the new cgame (T8).
* **ZING and suppression.** The deflected segment runs the zing block, so a ricochet cracking past
  a listener zings and suppresses - intended. The volley-end gate (`:815`) will not exclude the
  shooter from their own ricochet coming back; a round that bounces toward you zings you. The
  server-side player-suppression block (`:2621-2663`) does not run for the secondary segment;
  acceptable for v1. Tinnitus is explosion-driven and unaffected.
* **Fairness.** AI ricochets at 0.4 damage can hit players from odd angles; `coop_ricochetAI 0`
  is the escape hatch. Friendly-fire handling is whatever `Sentient::ArmorDamage` already does
  for the attacker, unchanged.
* **Coverage is data-limited.** Only `m3l1a` has a `_metal.txt`; other maps' hedgehog clips are
  untyped stone until `docs/tools/gen_metal_brushes.py` is run for them. Static models with no
  clip brush are shot through and get nothing (`cm_load.c:1330-1333`, bug-2314).
* **Visual minimum.** `CG_BulletTracerEffect` draws nothing under 150u and starts the beam
  450-600u down the segment (`:415-446`); a ricochet into a nearby wall may be audible but
  invisible. If that reads badly, a dedicated short beam for `bRicochet` is ~15 more lines.
* **Prior record.** buglog: bug-2314 (cmpatch metal + the chain in `cm_load.c:1324-1349`),
  bug-2447 (Higgins hull impacts faked script-side from audio takes), bug-2394 (`maps` field is
  a prefix load filter - `"m e t"` here is safe), bug-2106 (suppression in `BulletAttack`),
  bug-2095 (caliber penetration overrides), bug-2439 (`bulletrange` is not a reach limit),
  bug-1940 (turret spread), bug-1142 (kill hooks belong in `ArmorDamage`, not `BulletAttack`),
  bug-2161 (`CGM_NOTIFY_HIT` precedent for a new server->client cue). `FIX_INDEX` for
  `weaputils.cpp`: 007, 617, 846, 948, 1143, 1974, 2095, 2439. `HANDOFF-2026-09-05.md:46` still
  lists "no bullet ricochets on the Higgins hull" as an open cinematic gap - this design closes
  it for real rounds if the Higgins is on the allowlist or a bmodel.

## Verdict

Feasible, and the smallest honest version is engine-side: `game.dll` (hook at
`weaputils.cpp:3065`, one helper, cvars registered in `G_InitGame`) plus `cgame.dll` (one enum
value in `bg_public.h`, one decode case, a `bRicochet` flag and two guards in
`CG_MakeBulletTracerInternal`), shipped as a pair; no mod script is needed because the sound
aliases and spark effects already exist. Roughly 150-200 server lines and 60-80 client lines,
plus the one-line gate on the dead cosmetic whine and the one-line `CGM_BULLET_11` upgrade for
tank hulls. The single biggest uncertainty is metal classification for models: a box-hull hit
carries no surface bit, so "is this a tank" rests on a class allowlist whose real membership on
the shipped maps (bbox vehicles vs `*N` bmodel script_models vs `CONTENTS_BBOX`-only props) has
not been measured - the `RICO` probe printed outside the roll is the census that settles it
before any tuning.
