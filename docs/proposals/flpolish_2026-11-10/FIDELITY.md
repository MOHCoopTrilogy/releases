# SEALED ORDERS (coop_fl_1_1) - fidelity checklist against Frontline 1_1

Authority: the original level's own data on the player's disc, read by `docs/tools/frontline/flfidelity.py` into a
LOCAL reference (`H:\hzm_work\flpolish\fidelity\fidelity_1_1.{json,md}`, never committed). This file holds only our
paraphrase, our MOHAA coordinates and the status of each item. 1 player = the original; coop scaling sits on top.

Status: **M** matched, **D** deviation (closest MOHAA equivalent, reason given), **X** missing (still to do).

## Route and gating

| # | item (original) | port | status |
|---|---|---|---|
| R1 | Drop zone in the north lane (player start 7729 5610) | same spawn region | M |
| R2 | Lane south to the jeep road, road west to the arch (6700 3350) | walkable; audited | M |
| R3 | Town: arch -> square -> street south past the tank (1330 600 .. 1320 -540) | walkable | M |
| R4 | Crawl hole through the wall into the town (2897 1690, 46u high in Frontline units) | carved to MOHAA crouch (60u) - FL's crouch fits 49u, MOHAA's needs 54 | D |
| R5 | Interrogation house reached through a low crawl space (-1232 -4656) | carved to crouch | D |
| R6 | 4 tall trigger VOLUMES (crawl hole, interrogation house, two in the town) never block a character | dropped from collision (were solid: the "invisible walls blocking progression") | M |
| R7 | Player-clip boundaries (special surface) along the route edges | where they close the level with nothing drawn (124 sheets, curated with the walk audit) kept as the original has them, invisible (user: the original's own invisible walls are fine; no wire the original did not draw); the converter-made blockers are gone and the drawn geometry collides instead. Canal quay walls kept (user decision: no falling in) | M |
| R8 | Trees/posts wrapped in tall clip columns | columns shrunk to the drawn trunk/post; 6 with nothing drawn dropped | D (snag fix) |
| R9 | Level edges: no floor past them | clip wall + drawn skirt + ground under the level (no void) | D |
| R10 | 19-34u lips walked over (Frontline step height ~0.7 m) | HZM engine step height per map (worldspawn hzm_stepsize 34: players, prediction, actors) | M |
| R11 | Gaps narrower than the MOHAA box (30u) but wider than Frontline's (~20u) on the AI routes | collision cut to the MOHAA box along every open route of the original's navigation (flroutes; collision only, nothing drawn changes); route blocks 146 -> 42, none of them a gap too narrow for the box (two slanted gaps past a post and a wall end are sampled finer, fl_levels.json route_widen) | D |
| R12 | Door (DoorSwingCW) opened by its group | Frontline's own door mesh (inline model), solid while shut, swings when group 65552 wakes (log: FLSET door open; still to confirm on camera which drawn panel it replaces) | M |

## Encounters (group -> trigger -> members)

All 41 trigger-driven groups now spawn when a living player reaches the original trigger (radius from the record),
out of every player's sight (`fl_spawn_hidden`, 0 of 65 spawned in view in the audit run). Counts and teams are the
record's own (team byte, word 13); the class-name rule had made 4 Allied roamers German.

| # | where (MOHAA) | trigger | original | port | status |
|---|---|---|---|---|---|
| E1 | north lane allies (7774 3688) | proximity 3024u | 3 GIs + 1 German, alert | same, GIs join the squad when a player passes | M (+ squad follow, D) |
| E2 | jeep wreck (6352 3965 ..) | road 7536 3360 | 3 GIs, 3 Germans, crates, barrels | same | M |
| E3 | road shouters (5092 3358) | 384u | 3 Germans (planes / incoming / get out of the open) | spawned; each shouts his own German line a moment after he appears (unsubtitled samples 22, 23, 25 of the level's script bank, converted as `bark_*` cues) | M |
| E4 | town gate (2825 1599) | 307u | 4 GIs, 2 Germans | same | M |
| E5 | tank square (2172 1539) | 528u | Panzer IV + 3 GIs | tank placed again (it had been spawned as a rifleman), drives Frontline's path 66 when its group wakes, burns out when the rocketing P-47 pass ends on it | M |
| E6 | square south (1357 1224) | 374u | 5 Germans incl. "they're after the tanks" | same; the shouter's line (script bank sample 24) plays as he appears | M |
| E7 | west street (823 542 / 740 -735) | proximity | 2 Germans | same | M |
| E8 | phone post (1335 -401) | 461u | dead GI + field phone | both placed at load | M |
| E9 | hangout (1717 -2010) / (771 -1977) | 355u / 230u | 3 + 2 talkers | same | M |
| E10 | upper floor (1126 -2156) / proximity 1133u | 283u | 8 Germans incl. 2 path walkers, 2 GIs | same; the StayOnPath pair walk Frontline's named paths 2 and 151 until they have an enemy | M |
| E11 | MG post (1123 -2271) | 154u | mounted MG | MG42 turret, manned by nearest nest gunner | M |
| E12 | door house (-15 -2897) | 230u | 2 Germans + door | Germans spawn, the door swings open | M |
| E13 | interrogation (-2114 -4427) | 461u | officer + Castro + clipboard | interrogation scene (ours, optional rescue) | D (rescue is ours, user request) |
| E14 | MG nest (-2549 -4759) | 461u | 3 nest crew, MG, molotov barrel, wall charge | crew + MG42 + barrels. The barrels are Frontline's own meshes (mesh packs `Barrel_Metal_Flammable_Red.mpk`, `BarrelMolotovSwapping.mpk`: intact, and the wreck the original swaps in), solid, set off by a bullet or a blast; the molotov barrel burns 10 s where it stood. Until this round the stand-in model failed to load and every barrel was invisible and could not be shot | M |
| E15 | docks (-5144 -3783), (-6705 -6205) | 461u / 2918u | 5 + 2 Germans | same | M |
| E16 | death ambushers (StartByIdDeathAmbush) | lie among the dead, rise when the player comes close | lie in a stock dead pose and get up through the stock prone-to-crouch clip of their weapon (1.1 s, seen on camera: lying, gathering, kneeling, aiming) when a player is within 420u or they are hit. Frontline's own clip is in its undecoded motion format; before this round four of the six stood upright while "playing dead" | M |

## Scripted moments

| # | moment | original | port | status |
|---|---|---|---|---|
| S1 | Jeep run | trigger 77 (7665 4380): jeep (driver, passenger, gunner) down the road west, hits the mine at the bend (6782 3356), flips, stops wrecked in the arch | Frontline's own 229 motion keys from key 1 behind the gate (HZM engine wide coordinates: a start past x 8192 was never drawn), crew bound to the jeep, mine blast, 2 killed, survivor joins | M |
| S2 | Jeep wheels flying off (4 tyre motion files) | 4 wheels | Frontline's own wheel mesh on its own four motions, on the jeep's clock from the mine hit | M |
| S3 | Air: 7 fly-throughs (P47 fly-by, dogfight, strafe, rocket the tank, bomb the building, circling, Stuka) | 7 triggers | all seven passes on Frontline's own motion keys with its own P-47 and Stuka meshes; the plane-to-trigger table is ours (closest pass, unique) | M |
| S4 | Bombs hitting the ground (2) and falling building parts (2) | triggers 423, 86 | both bombs on their own keys and meshes, burst on landing; the two house chunks (own meshes) fall on their own keys as the second bomb lands | M |
| S5 | Rockets fired from the square (2) | trigger 255 | their own launch keys and mesh; the flight after the launch keys is ours (at the Panzer while it stands) | D |
| S6 | U-boat bobbing at the dock (AnimMoveMechLoop, its own mesh) | trigger 11 | its own mesh bobbing on its own keys all mission | M |
| S7 | Wall breach to the dock (M1_1_WallExplosion) | objective | use + explosion | M |
| S8 | Land mines (4) | step on | radius damage | M |

## Objectives, pickups, audio

| # | item | original | port | status |
|---|---|---|---|---|
| O1-O5 | 5 objectives, text from the disc | same order and text | | M |
| P1 | health 10/25/50 (18/7/5) | stock health boxes carrying the original's amounts (10/25/50) | M |
| P2 | ammo: grenade 11, pistol 9, rifle 8 | stock ammo boxes at the same 28 points | M |
| P3 | Colt / Garand / grenades at the start | coop loadout instead (deliberate: the mod's Armory loadout on every map) | D |
| A1 | ScrBnk dialogue: interrogation, dock, tower, nest, panzer | played at the matching spots | M |
| A2 | "mg_hurt" line (wounded gunner) | played the first time a manned MG42's gunner is hit | M |
| A3 | Music: the level's music map (`1_1M.mpf`) plays intro, sting, then ambient and action alternating; the end piece is its second section. It is a fixed order, not trigger-switched (the earlier note was wrong) | the same order, read from the map at conversion (`flaudio.music_map`); the end piece at the mission's end | M |

## Score (1 player)

Matched 39 - Deviated 8 - Missing 0 (of 47 items; the earlier "of 50" over-counted the table, which holds 47).
Round 1 was 22 / 19 / 9 on the same table. The deviations at R4/R5/R8/R9 are deliberate MOHAA-body fits, R7 now
matches (the original's own sheets, nothing added). R11 is a deviation: the gaps are cut to MOHAA's box along the original's routes (42 route blocks remain: 24 hug a wall the walk passes, the rest are the original's own walls).
Progression walk (progwalk.py): 0 blocks; a player has to crouch in three places only, all the original's crawl passages (R4 hole, the passage at -656 -2700, the interrogation crawl space R5).
Open deviations: the rockets' flight after their launch keys (S5; the disc holds only the launch keys), the start
loadout (P3, deliberate, awaiting the user's answer), and the deliberate MOHAA-body fits above. Closed in round 6:
the shouters' barks (E3, E6), the ambushers' rise (E16), the music order (A3).
Set pieces were checked in one SP camera run (2026-11-10, stills local only); the door's swing and the fly-by over
the docks were logged but not yet seen on camera.

## Round 7 (flfix2, 2026-11-11) - after the first human playtest

How Frontline itself works (file formats, triggers, groups, set pieces, what is still unknown) is written down once
in [`docs/tools/ea/FRONTLINE_REFERENCE.md`](../../tools/ea/FRONTLINE_REFERENCE.md); this file only scores the port.

**Coordinates.** Every coordinate in the tables ABOVE was measured on the first conversion, which was mirrored in y
(bug-10602). The world is no longer mirrored (bug-10965: lettering on signs read backwards, the map was the mirror
image of the original). From here on coordinates are the un-mirrored ones: negate y of anything above.
P3 (loadout) is no longer an open deviation: the co-op Armory kit is the decided behaviour.

### Objectives (original vs port)

| # | key (chars.bum) | original trigger | port | marker | status |
|---|---|---|---|---|---|
| O1 | obj_drop 104 / done 122 | active from level start; done at the interrogation | state 2 at t=1.3, done when the interrogation is released | `FLSET obj 1` | M |
| O2 | obj_roster 106 / done 125 | listed at start, activates when O1 is done | same | `FLSET obj 2` | M |
| O3 | obj_dock 111 / done 127 | after O2 | same | `FLSET obj 3` | M |
| O4 | obj_crate 114 / done 129 | after O3 | same | `FLSET obj 4` | M |
| O5 | obj_wall 118 / done 134 | after O4; the wall breach ends the level | same | `FLSET obj 5` | M |

Text is the disc's own. The ORDER is the list order of the disc's string table; whether the original lets two be done
out of order is **unknown** (no objective-script record decoded). In the automated walk the five complete in order
(964.3 / 967.3 / 970.3 / 973.3 / 976.3 s; the walk's test mode completes them, a human has not).

### Scripted sequences: expected order vs the order seen (walk `ai58b`, 2 clients, server log)

Expected = the order of the original's triggers along the route (R1-R12). Actual = `FLSET` markers, in log order.

| # | sequence | original trigger | seen at (s) | in expected place |
|---|---|---|---|---|
| 1 | U-boat bobbing | level start (11) | 0.3 | yes |
| 2 | music intro, sting, ambient | level start | 1-40 | yes |
| 3 | Stuka dogfight | 77 with the jeep | 68.3 - flies its keys and is removed | yes (was: hung above the Panzer, item 11) |
| 4 | Jeep run, mine, 4 wheels | 77 | 68.5 start, wheels 73.7, end 76.1 | yes (was: not seen, item 2 - started behind a wall of the mirrored map) |
| 5 | P-47 dogfight | 77 | 70.8 | yes |
| 6 | P-47 bombs the building | 423 | 110.3-122.3 | yes |
| 7 | bomb 1, bomb 2, house parts 1+2 | 423 / 86 | 138.3, 166.3, 169.7-170.7 | yes |
| 8 | Panzer drives its path (66) | group wake | after trig 38 | yes |
| 9 | P-47 circle, rockets the tank; tank destroyed | 255 | after trig 52 | yes (flight to the Panzer is ours, decided) |
| 10 | rockets fired from the square | 255 | after trig 30 | yes |
| 11 | P-47 strafes the MG | its own trigger | ends 343.65 | yes |
| 12 | patrols on paths 2 and 151 | group wake (42) | after trig 42 | yes |
| 13 | door opens | group 65552 (trig 3) | after trig 3 | yes |
| 14 | P-47 fly-by | its own trigger | 586.3-596.3 | yes |
| 15 | interrogation (posed at start, released at O1) | objective | posed 1.3, released 964.3 | yes; **not confirmed by a human** (item 15) |

No sequence fired out of order and none failed to fire in the walk; 0 script errors. What the walk cannot tell: whether
each one is IN VIEW of a player at the moment it plays (the walk's clients do not look).

### Areas wake on the player (item 14)

Nothing German exists before its trigger: 64 deferred spawns, 0 spawned in a player's view. `^~^~^ FLSET area <group>
active count=<k> trigger=<n>` is printed when a group wakes. The populated groups in the walk:

| group | trigger | count | | group | trigger | count |
|---|---|---|---|---|---|---|
| 0 (start squad) | level start | 11 | | 65545 | 42 | 10 |
| 65555 | 20 | 4 | | 65544 | 35 | 2 |
| 65540 | 16 | 6 | | 65552 (door) | 3 | 2 |
| 65557 | 22 | 3 | | 65550 | 23 | 1 |
| 65542 | 26 | 6 | | 65611 | 8 | 6 |
| 65632 | 38 | 3 | | 65553 | 62 | 3 |
| 65546 | 34 | 5 | | 65591 | 10 | 1 |
| 65547 | 63 | 2 | | 65562 | 44 | 5 |
| 65541 | 36 | 3 | | 65594 | 46 | 2 |

The other 25 activations have count 0: they are set-piece groups (planes, bombs, the door) with no soldiers.

**Death audit, before the fix (walk `ai58b`):** 93 actors, 42 Germans and 9 Americans killed; **22 German deaths with no
player in sight, 8 of them more than 1200 units from any player** - the squad ran ahead and fought groups that had
woken on a trigger the players crossed long before they could see them. That is the "already dead when we got there".
**Fix (map script, `fl_offscreen`):** a soldier of either side is ignored by all other AI until a living player is
within 1500 units or has a clear line to him inside 4000; set pieces never damage AI that is not engaged.
**Status: written, boots clean, NOT verified by a walk** (no client may run while the user plays). The disc places
no corpses on this level (no dead-body class in the placement records), so any pre-dead German is a defect.

### Mounted guns (item 7) - every `MountedMachineGun` record

| # | first conversion (origin, yaw) | now (origin, yaw) | stands on | note |
|---|---|---|---|---|
| 1 | (-2581 -4808 -125), 0 | (-2581 4808 -128), 304 | sandbag nest by the square | the "floating MG42 on the cobbles" |
| 2 | (-5727 -3960 -129), 0 | (-5727 3960 -132), 274 | nest | |
| 3 | (6573 3385 -123), 0 | (6573 -3385 -123), 179, broken | the wrecked jeep | Frontline flags it Broken: not spawned |
| 4 | (1120 -2209 463), 0 | (1128 2209 460), 90 | bridge tower platform | reached only by the tower ladder |
| 5 | (-5734 -5891 -176), 0 | (-5734 5891 -178), 90 | nest | |
| 6 | (1641 -742 -122), 0 | (1630 742 -122), 48 | window sill across the bridge | the "misplaced MG42 across the bridge" |

Before: every gun faced yaw 0 and sat at the record's origin (its pivot, below the barrel). Now: Frontline's own
facing, dropped onto what is under it and lifted by the tripod height; the nearest German machine-gunner of the group
mans it when the group wakes (`FLSET mg <n> manned`). Seen manned in the walk: gun 1. After-stills not yet taken.

Correction (v62): the lift was 34u and the guns hung about 15u over their rests. Stock mounts sit 18-19u over the support (m4l1 `turret3`, `turret4`, measured), and Frontline's own record is 22u over it; the lift is now 19u, which puts every gun within 3u of the record's height. The "black patch on the cobbles" under gun 1 is Frontline's own blob shadow for the nest (`1eeb00`, a black 32x32 disc, alpha up to 65%, on a 295u quad at (-2545 4752 -167)); 14 such quads and the square ones (`1ee600`) lie 0.5-3u over the ground with no depth offset, so they could z-fight into hard black shapes. The 10 soft ground-decal shaders now carry `polygonOffset`. Not seen in a client yet.

### Ladders (item 13)

| # | where | drawn as | collision / record | now |
|---|---|---|---|---|
| 1 | bridge tower, inside of the west wall (plane x=1065, y 2258..2282, z -209..431) | material c4_feb00, 22 triangles | none - Frontline has no ladder record we can read | climbable: `fl_levels.json` "ladders" -> `level.fl_ladder*` -> coop ladder recipe; the climber is set down beside the hatch at the top (bug-10973). Boots clean (`FLSET ladder 1`); **the climb itself is unverified** |

Down (v62): a player who steps into the hatch at the top is put on the ladder facing the wall (`fl_ladder_top`, log `FLSET ladder 1 down client=N`) instead of dropping 600u; the helper's own top mount needed him to touch a 1u trigger while looking 40 degrees down. Boots clean; not climbed in a client yet.

`H:/hzm_work/flpolish/fix2/findladder.py` (narrow, tall, vertical strips of one material) finds no second ladder.
An upper floor at (-1919 4799 16) holds 9 pathnodes no walk reaches and has no drawn ladder or stair: unknown whether
the original lets the player up there.

### Collision audit, first conversion -> now (`docs/tools/byoaudit/geoaudit.py`)

| measure | first | now |
|---|---|---|
| walkable cells | 14557 | 74615 |
| pathnodes unreachable | 1058 | 16 |
| route blocks (clusters) | 147 (97) | 35 (30) in v62; every one has a walk-around of at most about 90u and drawn geometry within 32u (wall ends and posts beside the straight node-to-node line; `H:/hzm_work/flpolish/fix2/triage61.json`) |
| placements unreachable | 118 | 19 (fly-through markers off the map, the tower gun and its ammo, 2 rockets) |
| falls into the void | 0 | 0 |
| low openings a crouched player passes | 0 | 30 clusters |
| low openings still too low | 15 | 53 (the flood now covers 5x the area; none is on a route: the progression walk meets 0 blocks and crouches at the original's 3 crawl passages only) |

### Unknown, said plainly

AI attributes per class (accuracy, health, reaction) are not decoded - ours are MOHAA's. Whether the original's
squad waits for the player or advances on its own is not decoded; ours follows the player. Trigger-to-plane pairing
for the seven fly-throughs is ours (closest pass). The cause of the "black patch on the cobbles" is likely one of the
original's square shadow blobs with nothing standing on it (see TEXTURES.md), not confirmed on camera.

## Round 8 (flfix2, 2026-11-11) - seen in a client

Build v65hb. Stills and logs under `H:\hzm_work\flpolish\fix2\`.

| check | result | proof |
|---|---|---|
| Panzer hovering | not floating at rest; the pale patch is Frontline's own ground art. Driving phase now ground-follows (bug-11016), not filmed | `vw63\crop1.jpg` |
| MG42 facing (bug-11015) | fixed and seen, all five spawned guns | `vw65\` (side-on + muzzle-end; gun 4 side-on blocked by a wall) |
| MG42 gunner seat | gun 1: gunner crouched behind the stock, co-op client. Guns 2, 4, 5, 6 never logged as manned in any run | `vc4\c_mg1_00.tga` |
| Jeep scene | fires from trigger 17 for a co-op player, drives in through the arch, mine, stops at the wreck spot in 7.625 s; Stuka dogfight starts with it and the Stuka is removed at its end | `vc3\sheet_jeep.jpg`, `vc3\qconsole.log` |
| Crawl passage to the interrogation | passes in SP physics only; not walked by a co-op player | `vw64\` |
| Tower ladder up | passes in a co-op client | `vw71\` |
| Tower ladder down (bug-11017) | was OPEN here; fixed in round 9 (bug-11027) | `r9\sheet_lad2.jpg` |
| Window from the street | no void | `vw72_pond\v_win1..3.jpg` |
| Canal water (bug-11019) | emitted as `textures/choppywater/tehao_indoorwater`, up normals, world UVs | `vw_hq\hq_quay_02.png`, `hq_eye_01.png`, `hq_low_01.png`, `canal_clip_5s.mp4` |
| Unseen deaths walk | NOT zero. coop_fltest 9, 1 client: 63/63 triggers, objectives 1-5, 0 script errors, 0 spawned in view. German deaths beyond 1500u of the walker 4 of 42 (was 22 unseen before the gating): the tank set piece and fights the walker teleported away from. American 5 of 9, all the jeep crew, because the walk harness misses trigger 17 (bug-11020). The walk teleports; a human walk is the real test | `aa_t9\aiaudit.json`, `aa_t9\server_qconsole.log` |

## Round 9 (flfix2, 2026-11-11/12) - disc bytecode and emulator reference

Sources: the decoded behaviour bytecode (`H:\hzm_work\flpolish\cbs_decode\SCENES.md`, D = read from the disc, I = inferred),
the emulator capture of the original (`H:\hzm_work\ref_xemu\NOTES_sealed_orders.md`, no audio) and the user's watch of the
original. Stills and logs under `H:\hzm_work\flpolish\fix2\r9\`. Build v71 (converter changes: `flpack.py` MMGPoint runners, `fl_sp_by`,
`fl_mark`; `fl_levels.json` set pieces 19 -> 17, marks, hint_gun; HZMCONV_VERSION not bumped here).

### Set pieces: what the disc specifies and what the build does

| set piece | disc (D decoded / I inferred / R reference frame) | build | exact? |
|---|---|---|---|
| Jeep: start | D player enters trigger 77 (6.4 m): body + 4 tyres + Stuka 287 start together | same trigger, same instant (`jeep7`: jeep start and plane start in the same frame) | yes |
| Jeep: crew | D driver, passenger, gunner attached to body nodes, ride loops 6500/6502/6504; R at least two visible, one at the rear gun | three riders: seated driver and passenger (stock e2l2 jeep poses), gunner standing at the pedestal gun | forced: disc animations and node offsets have no asset mapping; stock poses |
| Jeep: dust | D one puff 0.33 s after start | one puff at 0.33 s | yes (stock puff effect) |
| Jeep: fire on the drive-in | D generators 471/472 (NoFlash, MG42 sound) fire at the jeep while it is in trigger 470; no firing code in the gunner. R tracers cross the lane mouth just before the jeep. User: the .30 cal is fired | two hidden MG42 guns at records 471/472 fire at the jeep while inside 470 (t 1.6-3.2 s). `coop_fljeepcrew 1` makes the gunner fire instead | open: decode vs user account; default = decode. Tracer look is MOHAA's |
| Jeep: bumps | D mine 82 (explosion + bump anims 6509-6511), trigger 403 (second bump) | mine 82 explosion at t 2.15, trigger 403 logged at 2.68; no bump animation | forced: animations unmapped |
| Jeep: hit | D mines 81/95: explosions, driver and passenger play 6501/6503, fade 6 s, removed; gunner 6505 then wounded loop 6506 on the jeep. User: about two survive. R a soldier slumped in the wreck | default: driver and passenger fade 6 s and are removed at 6.7 s; gunner slumped on the wreck. `coop_fljeepcrew 1`: driver and passenger stay in cover | open: decode vs user account; default = decode. Poses are stock stand-ins |
| Jeep: tumble, wheels | D body and tyres on pre-authored tracks. R tumbles beyond the arch, a wheel rolls back down the road to the gate, wreck upright inside the village, wheels around it | the disc's own body and wheel meshes on the disc's own motion keys: tumble at the arch, wreck upright at (6561 -3310), three wheels beside it, the fourth ends back at the gate (8419 -3327) | yes for path and timing (7.6 s); origin-stepped at 20 Hz |
| Jeep: gun on the wreck | D message 103 at track end spawns rec 302 (I link); player within 6.2 m: hint text, gunner plays sound 82 and anim 6507, fades 6 s, removed. R "Press ACTION to Use Machine Gun", gun mountable, muzzle flash and casings | disc MG30_cal mesh at rec 302, usable (stock turret), hint text 190 from the disc text table, gunner line (stream 17 "mg_hurt") at 298u, fade and removal at 6.7 s | forced: sound 82 -> stream 17 is inferred, no reference audio; final animation unmapped; turret arc 180 each way is ours |
| Stuka 287 | D trigger 77, sound 66. R low along the road about 1.2 s behind the jeep | disc mesh on disc keys; crosses the lane mouth right behind the jeep (`sheet7_lane.jpg` frame 5) | yes for path; engine sound is a stand-in |
| Fly-through 288 (dogfight), 290 (strafe) | D no start link / no sender: never flown | removed (were flown before this round) | yes |
| Bomber 289, bombs 299/300, house parts | D trigger 41 starts the plane; a plane crossing sky triggers 423 / 86 drops each bomb; bomb impact (76 -> 74) drops parts 294/295 | plane on trigger 41; bombs released when a flying set piece is inside the trigger sphere (39.8 s and 41.9 s in `bomb2`); house parts 3.4 s after the 86 crossing | I: parts are timed, not chained to the impact message. NOTE: Stuka 287 also crosses trigger 423 and drops bomb 1 during the jeep scene (`jeep7` log); literal reading of the data, unconfirmed |
| Fly-through 291, rockets 385/386 | D trigger 220; rockets launch when an object (I: the tank) enters trigger 255 | plane on 220; rockets when a player enters 255; they hit the Panzer | I trigger object; rockets-to-Panzer is the user's decision |
| Fly-by 292 | D trigger 84 | same | yes (not re-shot) |
| Circling 301 + line | D trigger 226, also sends 415 = "They're after the tanks" | plane on 226 (`sheet_pz1.jpg`); line from the bark table | line timing not re-checked |
| "Planes above" | D sky trigger 107 sends 415 when a plane crosses | bark on the soldier's own wake | I, not matched to the plane crossing |
| Panzer | D trigger 251, path start, turret re-aim 3-6 s, fire 0.25-1 s after, generator 473 on trigger 256, death: explosion, destroyed model, sound 61 | trigger 251, disc path, MOHAA tank turret AI | forced: turret timing is the engine's |
| Wall breach | D trigger 430 spawns wall and barrels; use (86) -> chain -> wall frames 1-20 in four steps, sound 61, objective 4 | use + explosion + objective 4 | wall's four-step animation not reproduced |
| Interrogation, play-dead men | not in the decoded scenes | as rounds 7/8 | unverified against the disc |
| Allied squad | D no scripted moves: spawn triggers, order triggers, 110 cover points | follows the player | choice (existing row) |

### Round 9 items

| item | result | proof |
|---|---|---|
| Tower ladder down | fixed with the scripted top mount. Stock top mount (FuncLadder::CanUseLadder) needs floor behind the ladder plane at the lip; the tower has its outer wall there | `lad2.out` (start 374, end -160.2), `sheet_lad2.jpg` |
| MG42 guns 2, 4, 5, 6 | 2 and 5 manned by their MMGPoint runners; 4 and 6 have no MMGPoint on the disc: unmanned in the original | `sheet_mg2.jpg` |
| Gun 3 "Broken" | it is the jeep's .30 cal (rec 302, StartBrokenById = started by message, not a broken prop); now the disc mesh, usable | `sheet6_gun.jpg` |
| Canal wall streaks | the disc's own texture and UVs | `tex_6180.png` |
| Crates, first objective | disc meshes and textures; objective 1 is the Resistance drop ("Press ACTION to Search Drop" -> "Resistance Drop Found") | `sheet_crate2.jpg` |
| Canal depth (two interim options, default unchanged) | opt1 subpen_opaque: dark opaque surface, bed and wall bases hidden; opt2 canal_water: green opaque surface, bed hidden; current: bed visible. Default not changed | `quay\` |

## Round 10 (flfix2, 2026-11-12) - the jeep scene on the emulator trace

Sources: `H:\hzm_work\ref_xemu\TRACE_jeep.md` and its body / tyre / plane tracks, the reference frames in
`H:\hzm_work\ref_xemu\captures\sealed_orders\`, the disc records. Build v73 in `G:\mohaa-flpolish` only. Converter
changes (HZMCONV_VERSION not bumped): `flconvert.py` shader names (bug-11034), `flscene.py` rotation (bug-11035, changes
object-mesh rotations of every mission on its next conversion). Pair sheets, ours beside the reference: `H:\hzm_work\flpolish\fix2\r10\final\`.

| item | finding | result | proof |
|---|---|---|---|
| Jeep texture (user: "the texture is all wrong") | bug-11034: the engine cuts a shader name at its last dot; `Mesh.msh_<n>` names made every texture of a mesh one shader | each texture has its own shader; olive body with star, grille, seats, spare wheel, jerrycan; tyres and .30 cal checked | `pair_6_wreck.jpg`, `H:\hzm_work\flpolish\fix2\r10\jc2\sheet.jpg` |
| Jeep, tyre and plane rotation | bug-11035: the stored quaternion is the inverse of the rotation | body heads along its track, wreck faces as in the reference, all four loose tyres end flat, planes fly nose first | `pair_6_wreck.jpg`, `tyrerot.py`, `bodyrot.py`, `planerot.py` |
| Timing | trace ticks (60 per second, 0 = player on trigger 77) | generators on tick 71 to 123, bump mine 105, double blast and crew thrown 279, gun created 285, fourth mine 291, fades 1.1 s / 1.9 s after the blast (bug-11036) | log markers `FLJEEP` |
| Stuka and bomb 1 | the bombs are children of the bomber pass (FlyThrough_1_1 118), +153 and +219 ticks after its start; the jeep-scene plane drops nothing | Stuka no longer releases bomb 1; both bombs still fall with the bomber | `H:\hzm_work\flpolish\fix2\r10\bomb.out` |
| Generators 471 / 472 | disc: two fixed points 6.3 m above the road either side of the road line, behind the jeep; no direction stored; emulator: tracers cross the lane mouth first, then the jeep, then a German fighter very low about 1.2 s behind | tracer fire from those two points at the jeep = the strafe; the jeep's gun is silent | `pair_1_lane_pass.jpg`, `pair_2_plane.jpg` |
| Allies in the lane mouth | recs 104-106 (group 65555) first act at +134 ticks | group held until 2.83 s; nobody in the lane mouth as the jeep passes | `pair_1_lane_pass.jpg` |
| Thrown crew | they stood back up and faded standing (bug-11037) | they stay down (stock anim, animdone, bedead recipe) | `H:\hzm_work\flpolish\fix2\r10\s_arch3\sheet.jpg` |
| Objective wording vs the published pause screen | five of six identical; objective 2 "Man Machine Gun in Church Tower" and "Machine Gun Manned" missing; hint is "Shoot Barrels to Destroy Wall" (published: "Destroy Fuel Drums to Breach Wall"); no crouch prompt, no HQ hint lines; ours adds "Optional: Rescue the prisoner" | NOT changed yet | - |

Not exact, open: the 6 s fade of the thrown men and the gunner is not visible (stock soldier skins have no entity-alpha stage);
they disappear when the fade time ends. The throw arc and the thrown poses are invented around stock animations.

## Round 11 (flfix2, 2026-11-12) - light, fog, sky, hedge foot, blast, crew fade

Sources: `H:\hzm_work\ref_xemu\TRACE_sky_fog.md`, the sky faces in `H:\hzm_work\ref_xemu\sky\`, `TRACE_jeep.md`, the
reference frames, the disc records. Build v85 in `G:\mohaa-flpolish` only. Converter changes (HZMCONV_VERSION not bumped):
`flconvert.py` (light gain, fog and sky keys, sky shader and hull, hedge skirt), `flbsp.py` (light_gain, planar surfaces),
`fl_levels.json` (1_1: farplane 4800, farplane_bias 240, farplane_cull 0, farplane_color, sky_faces). No engine cvar changed.
Pairs, reference left and ours right: `H:\hzm_work\flpolish\fix2\r11\final\`.

| item | finding | result | proof |
|---|---|---|---|
| Light (bug-11057) | the disc lights by vertex colour only, a 1x modulate; nothing was dropped. The mod's renderer multiplies map vertex light by 4 x 0.71 | converted maps only: vertex colours x 0.352 (= 1 / (4 x 0.71)); entities: ambientlight 40 40 40 (chosen). Soldiers and the jeep read consistent with the world | `pair_1_lane.jpg`, `H:\hzm_work\flpolish\fix2\r11\fade1_f5.jpg` |
| Fog (bug-11058) | trace: linear, start 240, end 4800 disc units, colour 104,106,109, far clip at the fog end, on every scene draw | converted exactly; fog as view depth is inferred; clear colour 48,48,48 has no equivalent and is not represented | `pair_1_lane.jpg` |
| Sky (bug-11058) | trace: 6-face box on the eye, drawn first, not fogged | the six captured faces as a sky box with a no-fog stage; clouds visible. The faces go into the player's private pak only (FL_SKY_DIR at conversion); without them the stock sky stays | `pair_2_sky.jpg` |
| Rain (bug-11060) | the port had a rain theme; the original has no weather | removed: no rain, no rain sound. This is a visible change from the build the user played | `pair_1_lane.jpg` |
| Hedge-foot wedge (bug-11059) | the disc HAS geometry there: three leaning hedge skirt faces (draws 153, 491, 1231) that the hedge reskin dropped as "not vertical" | restored (RESKIN_NZ 0.7); nothing added; the two lids tried first are removed again | `H:\hzm_work\flpolish\fix2\r11\lane8.jpg` |
| Blast (bug-11061) | the disc's mine effect is a low dirt burst, not a fireball | emitter built from the disc particle records: grey dirt cloud, small puff, dark pieces; nothing reaches the arch top | `pair_3_blast.jpg`, `H:\hzm_work\flpolish\fix2\r11\arch4_sheet.jpg` |
| Crew fade (bug-11062) | stock skins cannot fade; the men also came to rest inside the wreck | fade-capable skin clones; rest spots 110u either side of the wreck; fade 1.1 s / 1.9 s after the blast, 6 s, removed 6.7 s after the fade starts (trace, log markers) | `strip_5_crew_fade.jpg`, `pair_4_wreck.jpg` |
| Objective wording | user, 2026-11-12: "Keep ours it's fine" | unchanged, including the two prisoner lines; HUD text matches the objective menu | - |

Not matched, open:
- Brightness: ours is still clearly brighter than the reference (mid-grey road, yellow-green leaves against a very dark dusk).
  The client's gamma (r_gamma 1.3) and the mod's tonemap sit on top of the corrected vertex light; they are engine settings
  and were not touched.
- Blast: a thin dust cloud veils the arch for about 1 s where the reference frame shows the jeep clearly. The particle record
  fields are only partly decoded ("read as").
- Tumble: one thrown man passes through the jeep body, and the gunner stands upright on the jeep while it tumbles
  (stock animations on an invented arc; no decoder for the disc's skeletal animations).
- The driver's rest spot is on the far side of the wreck from the square; only the passenger's fade was seen on screen.

## Deviations from the original (for the user; choices are not settled here)

| what | original | conversion | forced or choice |
|---|---|---|---|
| Player loadout | Frontline's weapons | co-op Armory loadout | choice (user decision) |
| Air strike on the Panzer | as on the disc | rockets hit the Panzer | choice (user decision) |
| Canal water look | flat disc water | mod water under a stock shader name, up normals, world-space UVs (tile 512) | choice (user decision) |
| MG42 yaw | record yaw = gunner's side | muzzle = record + 180 | forced (engine convention) |
| MG42 height | 22u over the support | 19u (stock MOHAA mount) | choice, 3u |
| MG42 rest pose, unmanned | unknown | muzzle up about 45 degrees (MOHAA turret idle) | forced (engine) |
| MG42 gun 3 (rec 302) | the jeep's .30 cal, spawned by message when the jeep's track ends, mountable | disc MG30_cal mesh on a stock turret; arc 180 each way | forced (engine turret); arc a choice |
| Panzer height while driving | path heights | seated on the ground each step (path is up to 9u off) | choice |
| Jeep | body and four tyres on pre-authored tracks | disc meshes origin-stepped on the disc's keys (20 Hz); wreck = the disc body where its track ends | forced (script_model movement) |
| Jeep crew poses and animations | disc animations 6500-6511 on body nodes | stock MOHAA poses: seated driver and passenger, gunner at the gun, thrown = death_mortar_high / death_mortar_twist on an invented 0.7 s arc, wounded gunner = A_22_driver_cover; no bump animation (6509-6511) | forced (no decoder for the disc's skeletal animations) |
| Crew fades | 6 s fade-out of driver, passenger and gunner | 6 s fade on fade-capable clones of the stock skins (same textures) | forced (stock skins have no entity-alpha stage) |
| Thrown crew rest spots | not traced | 110u either side of the wreck | choice |
| Mine blast effect | disc particle records | emitter built from the records; several fields "read as"; alpha 0.25 | inferred; alpha a choice |
| Jeep crew fate | trace: driver and passenger thrown out at the blast and fade; gunner wounded, speaks when the player reaches the gun, then fades | default = trace; `coop_fljeepcrew 1` (off) = two stay in cover | settled by the trace |
| Fire at the jeep | trace: no crew member fires; generators 471 / 472, 10 volleys from +70 to +122 ticks, from two points above and behind the jeep (the strafe) | generators at the disc points, aimed at the jeep (no direction is stored); tracer and gun sound are stock stand-ins | aim = inferred; `coop_fljeepcrew 1` (off) = gunner fires |
| Jeep .30 cal position | created at +284 ticks | the mesh rides the body; the usable gun is created at +284 on the record's rest spot | choice |
| Gunner's line | sound 82 | stream 17 "mg_hurt" from the player's converted audio | inferred mapping, no reference audio |
| Play-dead men | disc actors | MOHAA actors; scenery until they rise | forced |
| Fly-throughs | 287, 289, 291, 292, 301 started by triggers; 288 and 290 never started | the five; 288 and 290 removed | - |
| Bomb 1 and the Stuka | trace: the jeep-scene plane drops nothing; both bombs are children of the bomber pass | bomber only | exact |
| House parts | fall on the bomb's impact message | fall 3.4 s after the plane crosses trigger 86 | choice (timing stand-in) |
| Rockets | launch when an object (inferred: the tank) enters trigger 255 | launch when a player enters it | inferred |
| AI behaviour, accuracy, health | Frontline AI | MOHAA AI with the mod's scaling | forced |
| AI kept asleep until the player is near; spawns deferred out of view | unknown | fl_offscreen gating, deferred spawns | choice (user: no fights off-screen) |
| Allied squad follows the player | unknown | follows | choice |
| One ally moved | (799,479) | (760,479), out of a wall | forced, 39u |
| Intro crates | BreakingWoodBoxSwap x20 | the disc's crate mesh and texture, collision sized to it; break sound is a stock stand-in; nothing dropped | forced (sound) |
| Resistance drop | small package between the crates, hold ACTION about 1 s | the disc's mesh; taken on a single USE press | choice (hold time) |
| Models | Frontline models | MOHAA stand-ins where no conversion exists | forced |
| Textures | disc textures | 5 CC0 swaps (mud x3, roof slates, planks) | choice |
| Sky | 6-face box on the eye, unfogged | the six faces captured from the emulator, in the player's private pak only; stock sky when they are absent; drawn on a hull around the map | exact textures; hull forced (engine) |
| Fog and far plane | linear 240 to 4800, colour 104,106,109, far clip 4800, clear colour 48,48,48 | same start, end and colour; far plane does not cull (the sky hull lies beyond it); clear colour not represented | exact values; fog as view depth inferred; no cull forced |
| World light | vertex colours, 1x | vertex colours x 0.352 to cancel the renderer's 4 x 0.71 map light; still brighter than the original (client gamma and tonemap untouched) | forced (engine); residual open |
| Light on soldiers and objects | vertex colours | ambientlight 40 40 40 plus the engine's light grid | choice (value) |
| Weather | none | none (rain theme removed in round 11) | exact |
| Objective wording | disc / published pause screen wording | ours, including two prisoner lines; HUD text = objective menu text | choice (user decision 2026-11-12: "Keep ours it's fine") |
| Collision | disc collision | built from drawn geometry plus: riverbed, edge-of-world clip, lip ramps, 10 widened spots, 114 kept clip sheets, 5 patches | forced (no usable disc collision); each widened spot is a choice |
| Tower ladder | disc ladder | built from the drawn ladder; scripted mount and exit at the top | forced (engine top mount needs floor behind the ladder plane; the tower has a wall there) |
| Canal depth | (user request, not a disc fact) bed should not show through | unchanged default (tehao_indoorwater, bed visible); two converter-only options shot: FL_WATER_SHADER=textures/water/subpen_opaque (dark, opaque) or textures/water/canal_water (green, opaque) | OPEN, user to pick |
| Time and frag limits | none | switched off for the mission | forced (co-op) |
| World mirroring | - | none (un-mirrored since bug-10965) | - |
