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
| Tower ladder down (bug-11017) | OPEN. Six runs, no clean top mount | - |
| Window from the street | no void | `vw72_pond\v_win1..3.jpg` |
| Canal water (bug-11019) | emitted as `textures/choppywater/tehao_indoorwater`, up normals, world UVs | `vw_hq\hq_quay_02.png`, `hq_eye_01.png`, `hq_low_01.png`, `canal_clip_5s.mp4` |
| Unseen deaths walk | NOT zero. coop_fltest 9, 1 client: 63/63 triggers, objectives 1-5, 0 script errors, 0 spawned in view. German deaths beyond 1500u of the walker 4 of 42 (was 22 unseen before the gating): the tank set piece and fights the walker teleported away from. American 5 of 9, all the jeep crew, because the walk harness misses trigger 17 (bug-11020). The walk teleports; a human walk is the real test | `aa_t9\aiaudit.json`, `aa_t9\server_qconsole.log` |

## Deviations from the original (for the user; choices are not settled here)

| what | original | conversion | forced or choice |
|---|---|---|---|
| Player loadout | Frontline's weapons | co-op Armory loadout | choice (user decision) |
| Air strike on the Panzer | as on the disc | rockets hit the Panzer | choice (user decision) |
| Canal water look | flat disc water | mod water under a stock shader name, up normals, world-space UVs (tile 512) | choice (user decision) |
| MG42 yaw | record yaw = gunner's side | muzzle = record + 180 | forced (engine convention) |
| MG42 height | 22u over the support | 19u (stock MOHAA mount) | choice, 3u |
| MG42 rest pose, unmanned | unknown | muzzle up about 45 degrees (MOHAA turret idle) | forced (engine) |
| MG42 gun 3 ("Broken") | broken prop | not spawned | choice |
| Panzer height while driving | path heights | seated on the ground each step (path is up to 9u off) | choice |
| Jeep | disc animation | origin-stepped along the 77 path keys from key 1; stops upright, undamaged model, at the record's wreck spot | forced (script_model movement); wreck model is a choice |
| Jeep crew, "dead" men | disc actors | MOHAA actors; play-dead men are scenery until they rise | forced |
| Fly-throughs (Stuka, P-47) | disc triggers | paired to the nearest set-piece trigger | forced (trigger data is partial) |
| AI behaviour, accuracy, health | Frontline AI | MOHAA AI with the mod's scaling | forced |
| AI kept asleep until the player is near; spawns deferred out of view | unknown | fl_offscreen gating, deferred spawns | choice (user: no fights off-screen) |
| Allied squad follows the player | unknown | follows | choice |
| One ally moved | (799,479) | (760,479), out of a wall | forced, 39u |
| Intro crates | BreakingWoodBoxSwap x20 | MOHAA crate model, crate-sized collision | forced (model), collision a choice |
| Models | Frontline models | MOHAA stand-ins where no conversion exists | forced |
| Textures | disc textures | 5 CC0 swaps (mud x3, roof slates, planks) | choice |
| Sky and far plane | disc sky | MOHAA sky box and fog distance | forced |
| Collision | disc collision | built from drawn geometry plus: riverbed, edge-of-world clip, lip ramps, 10 widened spots, 114 kept clip sheets, 5 patches | forced (no usable disc collision); each widened spot is a choice |
| Tower ladder | disc ladder | built from the drawn ladder with a scripted top exit | forced |
| Time and frag limits | none | switched off for the mission | forced (co-op) |
| World mirroring | - | none (un-mirrored since bug-10965) | - |
