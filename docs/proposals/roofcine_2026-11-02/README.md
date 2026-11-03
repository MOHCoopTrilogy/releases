# Norway ending: roof blasts, roof holes, no "tables" (2026-11-02, branch `roof-cine`)

User 2026-11-02: *"When the building blows up at the end, it looks like three giant tables appear on top of the structure? What is that?
The explosion effects are supposed to be also happening at the top of the concrete building, giant fireballs from the explosions blowing
holes in the roof."*

## What the "tables" were
The **interiors of the five top-tier wall breaches** (sites 6, 18, 19, 20, 21) of map v7/v7b. The breach builder sizes an interior's
box from the panel: for a wall whose u axis is world z, `ucr = centre + (panel height + 240) / 2`, which for the top tier (z 1000..1190)
is z 1310 - **95 u above the concrete building's 1216 roofline**. When `cin_breach` showed `breach_N_interior`, its ceiling and the top of
its back wall stood up behind the parapet as a flat, warm-tinted (fire-lit vertex colour) slab, one per site: brown boxes on the skyline
that never go away. Measured from the shipped BSP (`maps/m2l3.bsp` ff151fa1): interior max z 1311 for exactly those five, every other
interior <= 1061.

Contributing (transient, not the slabs): `barracks_explosion` / `aircraft_explosion` throw `metal_section` / `ibeam_piece` tempmodels
that scale with the emitter; at the roof blasts' 7-22x they are house-sized plates for 1-2 s.

## Fixes
* **Map v9** - top-tier interiors capped: `int_ceil 1206` (closed ceiling under the roof) + `int_zmax 1210` (clip pass). Max z now 1210.
* **Script** (`coop_mod/finale_m2l3_cine.scr`):
  * `cin_fx`: above scale 2.2 the two debris-throwing emitters are swapped for `explosion_bridge` (sprites only).
  * `cin_breach`: an interior whose top rises past z 1214 is not shown (an un-updated v7 map gets holes with no slabs).
  * `cin_debris`: a piece that never lands within 6 s is removed (no hanging debris); one that lands on the concrete building
    (z > 880) is removed after 0.6 s.
  * `cin_notch` (new): the roof eruption at a notch site - swap under the flash, a giant fireball column fed for 6-7 s,
    fire + smoke in the bite, concrete/metal chips only (`cin_roofchips`).
  * `cin_oneshot`: the tank-room blast also blows notch 25; each of the four following roof blasts blows notch 24, 26, 23, 27.

## Roof holes - how they are made (real geometry, same pipeline as the facade breaches)
The roof plane is never in view from the one-shot camera (it sits on the train roof, ~15 deg below the roofline), so a hole in the roof
has to read as a **bite out of the skyline**. New breach kind `notch` in the builder (`tools/v7/make_chunks5.py`, generated from the v7
builder by `tools/patch_v9.py`):
* the panel is the whole top tier (brush 1993, y 3080..3176, z 960..1216) between two x bounds; it is doubled upward (virtual
  z 960..1472), the ragged hole (`make_hole2`: lobes, cracks, chips, spalled edges, rebar, scorch ring, soot streaks) is centred on the
  real top edge, then **every surface of `breach_N_damaged` is clipped at z 1216** - a jagged U bitten out of the roofline, the wall
  thickness showing in its flanks, front faces on the stock texture + lightmap. Surface-only (no collision; nobody stands up there).
* `breach_N_interior` = the gutted room behind it (the builder's interior), clipped at z 1202: no ceiling - the roof is gone.
* `breach_N_intact` = the carved stock piece (looks and collides as stock until the swap).

| site | x range | chunk | notes |
|---|---|---|---|
| 23 | -2640..-2010 | crumble_facade_4 | between top-tier sites 18 and 6 |
| 24 | -1440..-860 | crumble_facade_5 | between 6 and 19 |
| 25 | -250..370 | crumble_facade_6 | in front of the tank room; the first, biggest blast |
| 26 | 940..1290 | crumble_facade_7 | east end |
| 27 | -3660..-3205 | crumble_facade_3 | between 21 and 18 |

No box crosses a chunk cut (-3200, -2000, -800, 400) or another breach box.

## Reproduce (byte-exact)
```
python tools/mk_v9spec.py H:\hzm_work\maprebuild\v7_s3.json H:\hzm_work\maprebuild\v7_s4.json <out>
python tools/v7/make_chunks5.py <out>/v9_s3.json      # base: H:\hzm_work\maprebuild\v4\c2.bsp (md5 da3e482b...)
python tools/v7/make_pclip.py   <out>/v9_s4.json
python tools/v7b_ents.py <out>/c4.bsp <out>/m2l3.bsp   # the v7 -> v7b "+broadcast" entity step (list: tools/v7b_broadcast.txt)
```
`tools/v7/` is a frozen copy of the v7 builder set (`make_chunks4_v7.py`, `breachgeo.py` = `breachgeo_v7.py`, ...). Proof it is the
real thing: the v7 spec through it, then `make_pclip` and `v7b_ents`, gives the shipped map byte for byte (md5 ff151fa1); and
`make_chunks5.py` with the v7 spec gives the v7 `c3.bsp` byte for byte (8d373a1a) - the new keys change nothing unless used.
(The working copies `maprebuild_1025/tools/make_chunks4.py` / `breachgeo.py` were edited after v7 and no longer reproduce it.)

## Map file and how it ships
| file | bytes | md5 |
|---|---|---|
| v9 `maps/m2l3.bsp` | 14,895,440 | `30c4a952803bc981f49f2c7332e2df62` |
| `maps/m2l3.pth` (unchanged from v7b) | 99,012 | `ae0f4e18710f8b4e1060878d0123cd30` |
| v7b `maps/m2l3.bsp` (shipped today, kept) | 14,548,184 | `ff151fa112131f3b0b6cd323528910f3` |

The map ships in `hzm-mohaa-coop-mod\zzzzzzzzzz_coop_maps.pk3` (git-ignored, copied by build.ps1 and staged by publish_release.ps1).
Candidate pak with only `maps/m2l3.bsp` replaced: `H:\hzm_work\roofcine\zzzzzzzzzz_coop_maps.pk3`. To ship: copy it over the mod
checkout's pak in the release that carries the script (the original stays at `H:\hzm_work\maprebuild\v7b\maps\m2l3.bsp`).
Script and map are independent in both directions: new script + v7b map = no notches (cin_notch no-ops), top-tier interiors stay
hidden; old script + v9 map = the v7 ending without the slabs (notch sites stay intact).
Model numbers moved (append order: the new sites sit in their chunks' sequence); nothing in the mod references m2l3 `*N` numbers and
there is no `cmpatch/m2l3*.txt`.

---

# Part 2 - the payoff (2026-11-02, same branch): fires in every hole, the rolling chain, the climax, the victims, sound

Users asks (via the coordinator): fires burning inside every blast hole to the end; explosion sound effects; a rolling "doppler"
chain of detonations from the roof eruptions through the facility to the fuel-tank room; "make it an epic payoff, do all of it";
enemies thrown / set on fire.

## Sound audit (the big finding)
The ending was **silent**. Its recipe came from `maps/m2l2b.scr` and kept that map's aliases: `explode_tank`, `explode_bridge`,
`m2l2_alarm2` are scoped to maps `"m2l2b"`, `explode_kfive1` to `e2l*`, `explode_hallway1` to `m6l3*`, `E3L4_Tunnel_Explo1` is
`null.wav` on e3l4 only. On m2l3 every one logged "needs an alias" (~230 lines a run) and played nothing; only `stonecrash01/02`
(maps `"m t"`) was heard. Fixed (bug-10412): blasts use the coop_ex_* pool (maps `"m e t ..."`), and
`ubersound/coop_finale_m2l3.scr` adds m2l3-scoped `explode_bridge` / `explode_tank` (fired by the emitter tiks). The alarm bed (`m2l2_alarm2`, also silent) is replaced by `coop_fin_siren` in the v1.10.61 working copy - keep that line of `cin_beds` when merging.
After: 0 "needs an alias" lines.

## New sounds: nothing downloaded
Everything is DERIVED from the mod's own shipped explosion pool (`sound/coop_explosions/coop_ex_*.wav`, already licensed and
shipped in `zzzzzz_co-op_hzm_mod_assets_snd.pk3`) plus a procedurally synthesised whoosh (numpy). No third-party file was
fetched, so there is no new licence to record. Generator: `tools/gen_fin_sounds.py <coop_explosions dir> <out sound/coop_fin>`.

| file / alias | built from | treatment |
|---|---|---|
| `fin_chain01..08` / `coop_fin_chain01..08` | large_08, bomb_02, large_06, bomb_04, large_09, bomb_05, large_05, bomb_03 | 0.45 s pre-roar (noise, cutoff sweeping 3400 -> 260 Hz: the doppler "rushing past and away") into the hit; per step deeper: low-pass 5200 -> 650 Hz, pitch 1.00 -> 0.84, bass +2..+7 dB, echo tail 90/210 -> 230/570 ms, -0.6 dB/step; loudness -16.5 LUFS at step 1 (= coop_ex_large_08); every file CUT so all end together 0.65 s after the last trigger (the silence beat) |
| `fin_tankboom` / `coop_fin_tankboom` | bomb_01 + large_08 (+0.12 s) + sub_01 x2 | low-pass 3.8 kHz, double echo 260/620 ms, 9 s, 2.5 s fade |
| reused | `coop_ex_sub_01` (sub-bass layer), `coop_tinnitus_ring` (ear ring), `coop_snd_fire_large` (= retail Amb_FireLoop_02, the fire roar bed), `fire_med` (each hole) | as shipped |

Ship note: `*.wav` are git-ignored in the mod. The nine files must be generated into the release checkout's
`hzm-mohaa-coop-mod\sound\coop_fin\` (build.ps1 packs `sound/` into the assets_snd pak) - run the generator there.

## What plays when (capture av4, game time; t0 = the one-shot cut, START + 1.6 s)
| t (s) | event | emitter position | sound |
|---|---|---|---|
| 1.5 | roof eruption, notch 24 | roofline x -1150 | coop_ex large+bomb+sub+debris (cin_snd 3) |
| 2.3 / 3.05 / 3.75 | notches 26 / 23 / 27 | x 1115 / -2325 / -3432 | same pool, random picks; fire roar bed starts (0.45) |
| 4.25 | chain 1 | (-2325 3400 800) | coop_fin_chain01 |
| 4.95 | chain 2 | (-1700 3600 620) | coop_fin_chain02 |
| 5.55 | chain 3 | (-1150 3800 450) | coop_fin_chain03 |
| 6.05 | chain 4 | (-600 3700 300) | coop_fin_chain04 |
| 6.47 | chain 5 | (-150 3950 150) | coop_fin_chain05 |
| 6.83 | chain 6 | (150 4200 0) | coop_fin_chain06 |
| 7.13 | chain 7 | (300 4350 -200) | coop_fin_chain07 |
| 7.39 | chain 8 (deepest) | (420 4150 -400) | coop_fin_chain08 |
| 8.04 | SILENCE: everything ducks (s_sfxduck 0.03, tmvolume 0.15, fire bed 0.04, fireballs stop feeding) | - | - |
| 8.54 | FLASH (warm white), sky/fog orange | - | duck released |
| 8.94 | BOOM: tank room + notch 25 + mushroom + shockwave + debris rain + victims | players / tank (436 4092) | coop_fin_tankboom + coop_ex_sub_01 + coop_ex_bomb_06 |
| 9.3 | ear ring, music swells 0.3 -> 1.6 over 3 s, fire bed to 1.0 | players | coop_tinnitus_ring |
| 10.5 ->| facade volleys, small buildings, secondaries | facade | cin_snd per blast |
| ~19 | fade on the burning building; tmvolume 1, s_sfxduck 1 restored | | |

## The payoff items
| # | item | how | status |
|---|---|---|---|
| - | fire in every hole to the end | `cin_holefire`: two uneven tongues off the bottom of the opening, smoky fire inside, lip smoke/flame, 1/3 a smoke column; random size/start/mix; a flickering orange dynamic light per hole (`light`/`lightRadius`, one flicker thread). OWN fire pool (life >= 200, cap 360) - debris/bursts can never starve it | landed |
| - | roof plumes not identical | per-notch fireball height/length/size + column count, staggered gaps | landed |
| - | rolling chain | `cin_chain` + baked variants, emitters pan left -> right toward the tank room; dust + a dull pop behind the parapet + a jolt per hit | landed |
| 1 | silence beat | chain files all cut at the same instant; rumble bed off from the first chain hit; the four roof eruptions use short-tailed layers and their hidden deep blasts stay quiet; fire bed 0.04, tmvolume 0.15 and s_sfxduck 0.03 for the 0.5 s. Measured in the render (av5): ~-10 dBFS RMS before, -22..-31 in the beat, boom right after | landed |
| 2 | flash then boom | flash, boom 0.4 s later | landed |
| 3 | mushroom | `cin_mushroom`: 24 rising fireballs z 1250 -> 2450, then a dark cap (norbigstacksmoke + tehao_thicksmoke) that hangs to the end | landed |
| 4 | slow-mo + push-in | **timescale not used**: it is server-global, would slow every client's music/sound and the cutscene's own waits, and the fade/music timing would drift. Faked: an fov zoom 52 -> 41 over 1.5 s, hold 1 s, ease back (a camera dolly drove the lens through the yard's crate stacks in capture av2, so it is a zoom) | fallback |
| 5 | light | flash; fog colour (1.0 .58 .30) with the fog plane at 9000, both stepped back to (.6 .6 .7) / 26000 over 10 s; hole dlights. The sky shader itself cannot be tinted from script | landed (fog/sky haze) |
| 6 | shockwave | existing ground ring (cin_shock) + snow blown off the hut roofs (mortar_snow_cloud + snowdrift at the roofs, found by camera-ray traces) | landed |
| 7 | camera shake per blast | notch quakes scale with blast size; chain jolts grow per hit; tank 0.45 s x 3.2 then 2 s x 1.0 (kept moderate: user 2026-10-27 "way too much shaking") | landed |
| 8 | burning debris rain | 12 pieces from above the tank room over the facade into the yard, each carrying a fire+smoke that rides it and burns where it lands; removed after 22 s; never left hanging (no landing in 6 s = removed; landing on the concrete building = removed) | landed |
| 9 | collateral | sparks off the power lines (generic_spark_big_pulse along the wires) + snow off roofs. **Hut windows / yard lights: not possible** - the lit windows are lightmapped texture on world brushes and the yard lamps are static models without targetnames, so script cannot break or switch them | partial |
| 10 | audio | sub layer, ear ring, music swell (tmvolume), fire roar bed | landed |
| 11 | final shot | the camera holds on the burning building under the orange haze as it cools; the train pulls out of frame | landed |
| - | victims | `cin_victims_take` hands live hostiles in the yard to the cutscene before `def_clear`; `cin_victims_stage` stages extras in the black (camera-ray + ground trace, out of view until the fade-in). They run when the roof goes; at the climax 2 burn (coop_fire_s on `Bip01 Spine1`, run, fall, smoulder) and the rest are killed by MOD_EXPLOSION damage away from the tank room (the engine death impulse, capped 420 * g_corpseImpulse, + 260 u/s lift) into the client ragdoll | landed |

## Evidence (capture av5: client G:\mohaa-roofcine-av = the rel59 binaries + this branch's scripts/map/sounds in an overlay pak)
Recorded as a demo during the run, then rendered by the engine's own demo render (`set activeAction video; demo roofend`, 60 fps,
game sound in the file; the plain `video` command does not exist in this build's console path).
* **Video:** `G:\mohaa-roofcine\runs\av5\media\norway_ending_payoff_1080p60.mp4` - 25 s, 1920x1080 60 fps, H.264 CRF 19 + AAC 192k, 37.8 MB, from the fade-in to the fade-out.
* GIF of the climax: `G:\mohaa-roofcine\runs\av5\media\climax.gif`; stills `G:\mohaa-roofcine\runs\av5\media\still_*.jpg` (seconds into the raw render: 6.5 roof eruptions, 9.0 chain, 11.6 flash, 12.6 / 13.6 zoom, orange haze, burning men, bodies thrown, 14.6 the volleys, 16.5 / 22.0 every hole burning).
* qconsole: 0 "needs an alias" for the ending's own sounds (the one left, `m2l2_alarm2`, is replaced by `coop_fin_siren` in v1.10.61), 0 script errors.

Known / not changed: the hole flames are the stock `cfx_flame` sprite, which reads as a bright white-cored tongue at 4000-5000 u
(engine sprite, cannot be tinted from script); the music swell uses `tmvolume` on whatever track the client plays; s_sfxduck and
tmvolume are stufftext, so they act in live play - the demo render showed the beat because the sounds themselves stop.

---

# Part 3 - map v10: the collapse, the door climax, breakable windows, new flames, no idle actors (2026-11-02)

## Map v10 (`tools/mk_v10spec.py` + `tools/v7/make_chunks5.py` + `make_pclip` + `v7b_ents` + `tools/make_windows.py`)
| what | how | names |
|---|---|---|
| THE door hole (the climax) | breach 28 at the foot of the wall around the door, x -880..-60, z -512..300 (the facade's lower cuts moved to -890 so it stays in one chunk), ~5 m ragged hole, no fake room: the burning hangar is behind it | `breach_28_*` |
| the long pieces | the protruding ledge band (brush 4563) and the tiers above it (3393 cornice + 1993 top tier) are separate structures, each cut in six spans at x -3175 -1980 -780 -275 410 - the only x values where no breach box sits, so every hole stays whole in its piece | `crumble_ledge_1..6`, `crumble_upper_1..6` |
| grey hut (the yard's south wall) | four ragged holes 29-32 below the windows (brush 1088 added to `yardwall_s`), burning rooms behind | `breach_29..32_*` |
| breakable windows | all 8 lit panes (`jh_rustwin1lit`) become stock `func_window` (250 hp, MOD_EXPLOSION x10, engine glass-shatter debris + sound); the broken state is a smashed dark pane (`textures/hzm/window_broken.tga`, generated) | `fin_win_1..8` (+`_broken`) |
| lamps | **none is in the one-shot frame**: every lamp in the map (`static/lightbulb_caged.tik`, 40+) is a static model inside the facility, behind the facade, and their light is baked into the lightmaps (no light entity survives compile). A static model cannot take damage and baked light cannot go dark; doing it would mean converting them to entities with switchable dlights - not done (no visible payoff from the cine camera). The "lights" the camera sees are the lit windows, and they go dark when they break | - |
v10 `maps/m2l3.bsp` 15,510,044 B md5 `736349801168d05f51352e9cc55f0011`; `.pth` unchanged (v7b, loads with no "Pathnodes have changed"); 0 BSP / CM errors in the capture log.
Map pak (only `maps/m2l3.bsp` replaced + `scripts/hzm_window.shader` + `textures/hzm/window_broken.tga` added):
`H:\hzm_work\roofcine\v10\zzzzzzzzzz_coop_maps.pk3` md5 `492468868d338e785834b300c43e6788`.

## Script (v10)
* **Climax at the door** (`cin_doorblast`): breach 28 swap, the largest fireball of the ending (9 s, scale 9), five explosion emitters, the
  longest flash (held 0.32 s, 1.7 s fall-off), the biggest shake, the boom; the men staged around the door take the biggest throws.
* **Collapse** (`cin_collapse`, `cin_topple`): from the door outward - span 4, then 5 and 3, 6 and 2, then 1. Each ledge piece breaks off and
  drops forward, the tiers above tip over (roll 80-84 deg) and fall; every piece comes to rest on the 4th-highest of 15 traces under where
  it lies (a thin wall top does not hold a 1000 u slab up; a hut roof or a crate stack does), so nothing hangs. The breach panels, their
  fires and every long-lived effect sitting on a piece ride it down (rotated with it); room interiors behind are hidden as it goes.
  The left hut's roof pieces are hidden as the span-2 pieces come down through them (`cin_crash`: dust, debris, fire inside).
* **Grey hut** (`cin_greyhut`): every window is hit by a small radius damage 40 u in front of the pane when the blast front reaches it
  (from the pane plane itself the engine's sight trace starts in the wall and the pane took nothing), then holes 29-32 open.
* **Lean-to** (`cin_leanto`): three eruptions along its roof, its front wall (`collapse_shed_front`) blown out, fire inside, and the
  span-6 pieces land on it. Its roof is one sloped world surface, so it is not holed - the builder only cuts axial panels.
* **Flames** (`scripts/coop_fin_fire.shader`, `models/emitters/coop_fin_fire_{big,m,s}.tik`): nothing downloaded - the in-house flame
  flipbook (coop_fx pak) re-used vertex-tinted orange-red with alpha-weighted additive blending (overlaps build orange instead of white),
  a second phase of red tongues, dark smoke, embers, the fork's `firelight`. Big fires in the big holes / roof bites, smaller in small.
* **Idle actors** (`cin_actors_sweep`, `cin_census`): in the black before the fade-in every living actor is accounted for - an axis
  soldier in the camera's frame joins the payoff (reacts, runs, is thrown/burns), any other axis soldier is removed, allies in frame away
  from the train are removed. The standing "guard" was one of the map's own scripted German actors (the run lists `oenemy`, `irunaway1`,
  `irunaway2` among others) the cine never knew about. `CENSUS` lines (entnum, model, targetname, team, thinkstate, victim) at the
  fade-in, the chain, boom +2 s and the fade: the last census reads `total=0`.
* Not done: crates / lamp poles / fences are world brushes - they cannot be smashed (pieces that land on crates rest on them).

## Evidence (capture av7, map v10)
* Video 1080p60: `G:/mohaa-roofcine/runs/av7/media/norway_ending_v10_1080p60.mp4` (25 s, 28.1 MB, H.264 + AAC); phone copy 720p30 `G:/mohaa-roofcine/runs/av7/media/norway_ending_v10_phone_720p.mp4` (15.9 MB).
* Before/after per item: `G:/mohaa-roofcine/runs/av7/media/before_after_{1_grey_hut,2_leanto,3_door,4_facade,5_left_hut}.jpg`; full frames `full_*.jpg` (seconds into the raw render).
* Silence beat measured in the render: about -10 dBFS RMS before, -42 to -51 in the beat. 0 script errors, 0 BSP/CM errors; CENSUS fade total=0.

## Map v10b: the hidden east halftrack start (east gate)
Built after `make_windows.py`: `python tools/make_eastgate.py c6.bsp m2l3.bsp <assets>` (the `eastwall` structure is in `mk_v10spec.py`).
* `coop_fin_eastgate2` - the east wall section x 1472..1488, y 350..530, z -512..-296 (216 x 180 u opening; halftrack ~260 x 130 x 130),
  a script_object that looks and collides like the wall. Open/close: `coop_mod/finale_m2l3_eastgate.scr::eg_open` / `::eg_close`
  (origin stepping: 24 u east, then 190 u north behind the wall; 1.3 s each; gate_iron_open1 / gate_iron_close). No-ops without the gate.
* `coop_fin_eastgate2_clip` - permanent PLAYERCLIP|MONSTERCLIP brush in the opening: players and AI can never leave through it even
  while the gate is open; vehicles pass (MASK_VEHICLE has neither bit). Proven: the test halftrack drove through it.
* `coop_fin_eastramp` - a snow bank outside (the collision floor drops 64 u at x 1664, too high a step for the halftrack): 1:4 slope
  x 1664..1920, solid, vertex-lit snow top (`scripts/hzm_eastgate.shader`).
* Route (DrivableVehicle sdkfz + info_waypoint chain + `drive ... 160 100 40 128`, the alarmveh recipe), tested in capture eg2:
  hidden start `( 2250 440 -528 )` -> `( 2000 440 -528 )` -> `( 1800 440 -498 )` -> `( 1650 440 -464 )` -> gate `( 1480 440 -464 )` ->
  `( 1350 440 -464 )` -> joins fd_ht2_p at `( 1150 440 -464 )`. It arrived at x 1125 in 7.5 s; gate opened when the hull passed x 1950,
  closed when it passed x 1250. Ground probes: -576 outside, the ramp, -512 inside.
* Stills: `G:\mohaa-roofcine\runs\eg2\media\eastgate_A_defence_line_start_hidden.jpg` (zone centre, eye height, looking at the
  start: nothing of it), `_B_gate_open_halftrack_coming.jpg`, `_C_through.jpg`, `_D_closed_behind.jpg`. 0 script errors, no
  "Pathnodes have changed".
* Known: seen through the open gate the outside reads as white snow under the fog (no void, but no detail at that range either).
