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
| E3 | road shouters (5092 3358) | 240u | 3 Germans (planes / incoming / get out of the open) | spawned; only SayPlanesAbove speaks (its line when the bomber crosses sky trigger 107, with the disc's shout clip 14228 on him), Incoming / GetOutOfTheOpen are silent: no message 415 ever reaches them (codedecode item 6, round 23; was: all three shouted) | M |
| E4 | town gate (2825 1599) | 307u | 4 GIs, 2 Germans | same | M |
| E5 | tank square (2172 1539) | 528u | Panzer IV + 3 GIs | tank placed again (it had been spawned as a rifleman), drives Frontline's path 66 when its group wakes, burns out when the rocketing P-47 pass ends on it | M |
| E6 | square south (1357 1224) | 374u | 5 Germans incl. "they're after the tanks" | same; the shouter's line (script bank sample 24) plays as he appears | M |
| E7 | west street (823 542 / 740 -735) | proximity | 2 Germans | same | M |
| E8 | phone post (1335 -401) | 461u | dead GI + field phone | both placed at load | M |
| E9 | hangout (1717 -2010) / (771 -1977) | 355u / 230u | 3 + 2 talkers | same | M |
| E10 | upper floor (1126 -2156) / proximity 1133u | 283u | 8 Germans incl. 2 path walkers, 2 GIs | same; the StayOnPath pair both walk path 2 (rec 247 forward, 248 in reverse: actor attrs 42 / 43, round 23; "2 and 151" was wrong, 2:151 is a squad link) until they have an enemy | M |
| E11 | MG post (1123 -2271) | 154u | mounted MG | MG42 turret, manned by nearest nest gunner | M |
| E12 | door house (-15 -2897) | 230u | 2 Germans + door | Germans spawn, the door swings open | M |
| E13 | interrogation (-2114 -4427) | 461u | officer + Castro + clipboard | interrogation scene (ours, optional rescue) | D (rescue is ours, user request) |
| E14 | MG nest (-2549 -4759) | 461u | 3 nest crew, MG, molotov barrel, wall charge | crew + MG42 + barrels. The barrels are Frontline's own meshes (mesh packs `Barrel_Metal_Flammable_Red.mpk`, `BarrelMolotovSwapping.mpk`: intact, and the wreck the original swaps in), solid, set off by a bullet or a blast; the molotov barrel burns 10 s where it stood. Until this round the stand-in model failed to load and every barrel was invisible and could not be shot | M |
| E15 | docks (-5144 -3783), (-6705 -6205) | 461u / 2918u | 5 + 2 Germans | same | M |
| E16 | death ambushers (StartByIdDeathAmbush) | an ALERT man made the moment someone of the spawner's area dies (codedecode item 3; all six records StartAlert): nobody lies among the dead | spawned alert, out of view, on the same rule (decode audit 2026-11-22; was: lying in a stock dead pose and rising at 420u, an assumption) - coop_flPlayDead 1 brings the old men back; the user chose the disc's way (2026-11-22) | M |

## Scripted moments

| # | moment | original | port | status |
|---|---|---|---|---|
| S1 | Jeep run | trigger 77 (7665 4380): jeep (driver, passenger, gunner) down the road west, hits the mine at the bend (6782 3356), flips, stops wrecked in the arch | Frontline's own 229 motion keys from key 1 behind the gate (HZM engine wide coordinates: a start past x 8192 was never drawn), crew bound to the jeep, mine blast, 2 killed, survivor joins | M |
| S2 | Jeep wheels flying off (4 tyre motion files) | 4 wheels | Frontline's own wheel mesh on its own four motions, on the jeep's clock from the mine hit | M |
| S3 | Air: 7 fly-throughs (P47 fly-by, dogfight, strafe, rocket the tank, bomb the building, circling, Stuka) | 7 triggers | five passes (287, 289, 291, 292, 301) on their own triggers and motion keys with the disc's P-47 and Stuka meshes; 288 (dogfight) and 290 (strafe) have no sender and never fly, so they are not built (round 9 decode; the old "plane-to-trigger table is ours" was superseded) | M |
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
| 12 | patrols on path 2 (recs 247 / 248, 248 in reverse; 2:151 is a squad link, not a path - code decode 2026-11-15) | group wake (42) | after trig 42 | yes |
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

## Round 12 (flfix2, 2026-11-12) - wall breach, road line, light and fog measured, wreck pose

Sources: `H:\hzm_work\ref_xemu\TRACE_breach.md`, `TRACE_jeep.md` and tracks, the reference frames, the disc records.
Build v88 in `G:\mohaa-flpolish` only. Converter changes (HZMCONV_VERSION not bumped): `flconvert.py` (clip `boxes` per object
mesh; half-texel UV inset on non-tiling axes; `ambientlight` read from the level table; test overrides FL_AMBIENT,
FL_LIGHT_GAIN, FL_FARPLANE), `fl_levels.json` (21 `walbrk` meshes wb0..wb20; 1_1 farplane 16000, farplane_bias 600).
Stills: `H:\hzm_work\flpolish\fix2\r12\`.

| item | finding | result | proof |
|---|---|---|---|
| Wall breach (bug-11063) | trace: use at the molotov barrel, fuse +1 s, blast +6 s, all five barrels on one tick, 20 break frames in 0.8 s in four steps, second boom +0.6 s, objective +0.1 s | built to the trace with the disc's own 21 wall meshes; standing wall ends block, rubble does not | `FLBREACH` log markers; breach stills in `H:\hzm_work\flpolish\fix2\r12\` |
| Pale line down the road (bug-11064) | texture edge bleed on non-tiling surfaces | half-texel UV inset on non-tiling axes | `ln87.jpg` |
| White streak in the sky | it is the muzzle flash and tracer of the fire at the jeep, not a surface | unchanged; the original fires 10 volleys there too | `ln4\lane_01.tga` |
| Wreck pose | trace end pose and the four tyre rest spots equal ours once the converter's recentre offset (-42, +220) is applied; the wreck is upright, two wheels flat on the cobbles, spare on the back, fourth wheel far up the lane as in the trace | unchanged; the earlier pair looked tipped because of its camera | `pair_4_wreck_r12b.jpg`, `wk1_crop.jpg` |
| Light, measured (bug-11066) | zero vertex light gives a black world: no added light term. ambientlight 0 changes nothing on screen. Offline, texture x disc vertex colour equals our screen value with the display chain off (lane road 29 x 200/255 = 23, screen 21) | the 0.352 factor is right; no data change. The client display chain (r_gamma 1.3 and the post chain) multiplies by 1.3 to 1.45 | tables below |
| Fog, measured (bug-11065) | with zero light the far lane read 50 of 107 from fog alone, more than the reference's total (28). The original's world fog is about a quarter of the linear 5..100 m reading at 50 m; that reading was marked not proven in the trace (world draws use a vertex program, its fog output was not dumped) | fog refitted to the reference frame: start 600, end 16000, same colour. Two sample points, one frame: a fit, not a trace value | `pair_4_wreck_r12b.jpg` |

Wreck view, camera 6260,-3290,-150 yaw -3 pitch 15, mean RGB; v88 (reference | ours normal | ours display chain off | ratios of luminance):

| surface | reference | normal | chain off | normal/ref | off/ref |
|---|---|---|---|---|---|
| cobble mid | 26,27,25 | 41,41,39 | 31,31,30 | 1.54 | 1.17 |
| cobble near | 28,29,27 | 64,65,60 | 45,45,43 | 2.25 | 1.57 |
| stone wall by arch | 17,17,16 | 40,40,37 | 30,29,28 | 2.35 | 1.73 |
| jeep hood | 30,34,31 | 67,72,66 | 48,52,48 | 2.15 | 1.55 |
| jeep side panel | 15,18,17 | 29,35,30 | 24,28,25 | 1.92 | 1.56 |
| hedge bank past arch | 13,14,13 | 16,17,13 | 14,14,11 | 1.20 | 1.01 |
| far end of lane | 28,29,27 | 38,37,32 | 28,27,25 | 1.29 | 0.95 |
| sky (lane view) | 103,104,107 | 135,136,139 | 110,110,115 | 1.31 | 1.06 |

Far end of lane by build, chain off: fog 240..4800 = 59; no fog = 18; fog 600..16000 = 28 (reference 28).

Not matched, open:
- Walls and the jeep near the camera stay 1.5 to 1.7 times brighter than the reference with the display chain off. The
  patches are not on identical spots (the reference camera is closer and steeper), so no factor is derived from them.
- The lane pair is not on a matched camera (the reference stands under a tree further into the lane); its road and hedge
  rows are not comparable and are left out.
- Fog: the true function needs the world vertex program's fog output from the emulator. The original also clips at
  100 m; ours does not cull.
- Wreck: our wounded gunner sits in plain view (stock seated cover pose); the reference frame shows no gunner in the
  jeep and a rifleman standing behind it, which we do not have (soldier tracks unverified).
- Breach not verified: the real use-key path, trigger arming and hint in a full run, collision of the wall ends, sounds.

## Round 13 (flfix2, 2026-11-12) - wreck crew, breach in a full run, the bomber pass on the trace

Sources: `H:\hzm_work\ref_xemu\TRACE_bombers.md`, `TRACE_jeep.md`, `TRACE_breach.md`, the disc records. Build v89 in
`G:\mohaa-flpolish` only. Converter changes (HZMCONV_VERSION not bumped): `flscene.py` (.mvd key rate from the header),
`flpack.py` (set-piece keys parent / after / hold / stop), `fl_levels.json` (bombs and house parts on the bomber's clock).
Mod script `maps/coop_fl_1_1.scr` (uncommitted). Stills and logs: `H:\hzm_work\flpolish\fix2\r13\`.

| item | result | evidence |
|---|---|---|
| Wreck crew (bug-11077) | gunner lies wounded beside the wreck (stock injured loop), nobody seated in the jeep; thrown men start clear of the body | `cw1_tumble.jpg`, `cw1_rest.jpg` |
| Breach, full run with the real use key | objectives 1 and 2 by use, trigger 62, armed, use at the molotov, fuse +1.0, blast +6.0, break steps +0 / 0.2 / 0.4 / 0.6, open +0.775, five barrels on one tick, objective 3 | `br4.out`, `br5.out`, `br5_sheet.jpg`, `br5_obj.jpg` |
| Collision at the wall afterwards | the gap (y 5053) is walked through; the north wall end holds (stops at x -3240.5); the south end could not be reached to test | `br5.out` |
| Shot barrel path removed (bug-11078) | disc records: wall barrels and molotov are AnimateOnMsg (no damage path); 1.5 s of fire does nothing now | `br5.out` |
| Barrel meshes on their records (bug-11079) | log only | `bm4.out` |
| .mvd key rate (bug-11080) | header word = 60 Hz ticks per key: 1 = P-47s, bombs, rockets; 2 = jeep, wheels, Stuka, house parts, U-boat | emulator tracks |

Bomber pass, seconds from the plane's start (ours, runs bm2 / bm4 | trace):

| event | ours | trace |
|---|---|---|
| "planes above" line | 1.525 | 1.517 |
| bomb A made | 2.55 | 2.55 |
| bomb B made | 3.65 | 3.65 |
| bomb A lands, dock wall (4207,-2696,-106) | 4.35 | 4.35 |
| house parts start (recs 294 / 295) | 5.05 | 5.05 |
| bomb B lands, the house (4246,-1962,97) | 5.15 | 5.15 |
| plane gone | 6.025 | 6.1 |

What the bombs destroy: bomb A hits the dock wall point (blast, shake; no mesh change found in the disc records), bomb B
the house, whose two parts fall (1.0 s of keys). Still: `bm4_burst.jpg`.

Not matched or not verified:
- gunner pose and spot are stand-ins (animation 6506 has no decoder; the trace gives no gunner position);
- the standing rifleman of the reference frame is a square roamer (one of three AlliedSoldier_A records), not confirmed on our frame;
- the break frames are hidden by the fireball on our stills (log markers only); the hint text was not legible on a still;
- disc hint text says "Shoot Barrels to Destroy Wall" while the records give the barrels no damage path: shooting was never traced in the original;
- blast look is the stock emitter + sound + radius damage (original: 3 particles, CREATEEXPLOSION 20 and 30, not decoded); no reference frame of the blasts, so no matched pair;
- the two death-ambush soldiers (recs 69, 70) exist from level load instead of being created at +267 ticks;
- the other P-47 passes and the rockets now run at the header rate too (matches the plane lives in the trace), not re-shot; rocket delay 0.6 s remains a stand-in.

Content audit rows (`H:\hzm_work\flpolish\content_audit\AUDIT.md`): S05 bomber PARTIAL -> timing MATCH, blast look listed;
S06 shouters PARTIAL -> MATCH for the three at trigger 411 (one line with sound, two silent), the fourth (rec 229) untouched;
S23 breach PARTIAL -> MATCH on trigger, timing and frames, hint conflict listed; S02 / A08 / I05 jeep, crew, gun: built and
shown, poses listed as stand-ins.

Look round (2026-11-12, after the v1.10.79 playtest): the decoded fog IS applied (`fl_levels.json` 1_1 farplane 4800,
farplane_bias 240; commit 002f71d7). Same views, v94 vs the new conversion (local): `H:\hzm_work\flpolish\look\fog_pairs_a.jpg`,
`fog_pairs_b.jpg`; the far town now hazes like the reference frame `sq_across`. The object light formula of the same staged
patch (`H:\hzm_work\flpolish\fix2\r13\fog_conv.py`, OBJLIT part) is still NOT applied.

Look work parked on the user's priority (2026-11-12): the decoded fog (linear 240..4800, planar) and the object light
formula are NOT applied; the build still carries the fitted fog 600..16000. A patch is staged, untested:
`H:\hzm_work\flpolish\fix2\r13\fog_conv.py`.

## Round 14 (flfix2, 2026-11-12) - text ids, hints, the ambush pair, wreck gunner stills

Build v90 in `G:\mohaa-flpolish` only. Converter changes (HZMCONV_VERSION not bumped): `flpack.py` (disc record number
per axis soldier, `level.fl_axis_rec`), `fl_levels.json` (hint_wall 187 -> 1750, hint_gun 190 -> 968). Mod script
`maps/coop_fl_1_1.scr` (uncommitted): records 69 / 70 held and released at bomber clock +4.45 s, out of view.
Stills and logs: `H:\hzm_work\flpolish\fix2\r14\`.

Text ids: a Frontline script text id is the index among the non-empty strings of `chars.bum`; `fl_levels.json` keeps raw
ordinals (empties included). The 1_1 objective names are ids 28-32, done texts 33-37 (trace texts 35 and 37 agree).

| item | result | evidence |
|---|---|---|
| Barrels at the dock wall | stand on the ground before the blast (bug-11079 seat edit), 0 script errors | `..\r13\br6_sheet.jpg` |
| Dark shape in the fireball | the disc's own molotov wreck mesh (`BarrelMolotovSwapping.mpk`), swapped in at blast B as the trace shows; textured, not a missing mesh | `..\r13\br6_wreck.jpg` |
| Molotov hint (bug-11083) | now "Press ACTION to Ignite Rag" = trace hint 501; the "Shoot Barrels" string is never shown in the trace | v90 data script |
| Objective T06 "Machine Gun Manned" | not in the original 1_1: the raw ordinal belongs to another mission's texts; nothing built | `chars.bum` id table |
| Ambush pair recs 69 / 70 (bug-11084) | created at +267 ticks through the out-of-view spawn | data `fl_axis_rec`; timing not yet run on a client |
| Body in the camera at the 30cal | harness artefact: with `cg_drawviewmodel 0` nothing is in view; with 2 it is the player's own rifle viewmodel, as in normal play | `atgun_vm0_00`, `atgun_vm2_00` (`j3a.jpg`) |
| Wounded gunner | slumped in the rear of the wreck by the gun mount (log 6591,-3344,-152), not beside it | `j3a.jpg` |
| 30cal fire | muzzle flash on frames 2-9 of 10 | `j3b.jpg` |

Not matched or not verified: the HUD did not draw on the gunner stills, so the gun hint is still not shown legibly on a
still; the ambush timing and the re-shoot of the other P-47 passes and rockets wait for the client hold to lift; "Press
START button to View Objectives" (text id 273, console wording, when shown not traced) is not ported.

## Round 14b (flfix2, 2026-11-12) - shot breach, jeep wreck to the new traces, bomber pair, P-47 re-shoot

Sources: `H:\hzm_work\ref_xemu\TRACE_breach_shoot.md`, `TRACE_jeep_wreck.md`. Mod script only (base checkout,
commits f9158a0b and 07abce8c); no converter change. Stills and logs: `H:\hzm_work\flpolish\fix2\r14\`.

| item | result | evidence |
|---|---|---|
| Shot breach (bug-11087, reverses bug-11078) | 3 player hits on any one of the five barrels (per barrel; a bullet that goes through counts once, on the first barrel) blow all five and the wall on the next frame, no fuse; a shot molotov does not burn | `brs.out`, `brs_sheet.jpg` |
| Use breach | unchanged: fuse +1.0 s, blast +6.0 s, steps +0/0.2/0.4/0.6, second boom +0.6, open +0.775, OBJ 3 | `bru.out` |
| Wounded gunner (bug-11088) | face-down over the rear deck by the spare tyre at the trace spot; at 6.2 m his line, he pushes up and stands at the front, worn helmet hidden, a netted helmet left on the rear deck; fade 3.8 s after the line | `j4e.jpg`, `j4a.jpg`, `j4f.jpg` |
| Gun hint | "Press ACTION to Use Machine Gun" legible with the HUD on (the coop cgame shows each hint key once per profile: test clients clear `coop_hintSeen`) | `jeep3_hint.jpg` |
| 30cal fire | muzzle flash frames | `j3b.jpg` |
| Body in view at the gun | harness only (`cg_drawviewmodel 2` = the player's own rifle); nothing with 0 | `j3a.jpg` |
| Gun wave | 2.0 s after a player mounts the .30 cal: Allies 104-106, Germans 21, 98, 469, out of view; triggers 20 / 59 (recs 87 / 420) hold for the gun | `jeep4.out` |
| Jeep's own group 65540 | recs 64, 65, 103, 60-62 start with the jeep; rec 103 (StartIdle) holds his spot | `jeep4.out` |
| Ambush pair recs 69 / 70 | created at bomber clock +4.45 s (0.10 s after bomb A), out of view | `bomb.out` |
| P-47 rocket pass and circling P-47 at the header rate | plane, two rockets, tank destroyed, circle pass; nothing broken | `pz_sheet.jpg` |

Not matched or not verified: gunner poses are stock stand-ins (6506 / 6507 have no decoder); the worn helmet on our
model is the plain web one while the dropped one is netted; the rifleman's stay was set (leash) but his 40 s position
was not logged; whether the wave also comes without the gun (triggers 87 / 420, code 51) is not traced - here it
waits for the gun; the hint shows once per player profile in co-op (the original shows it each time a player is near).

## Round 14c (flfix2, 2026-11-13) - gunner (user decision), officer off, scene 5 to the traces

Mod script only (base checkout, commit a09a3d4a). Sources: `TRACE_panzer.md`, `TRACE_mg_ambush_end.md`,
`TRACE_germans.md`, `TRACE_panzer_kill.md`. Stills and logs: `H:\hzm_work\flpolish\fix2\r14\`.

| item | result | evidence |
|---|---|---|
| Wounded gunner (user decision, bug-11093) | thrown off at the blast, coop DBNO pose on the ground behind the wreck (not solid, clear of the gun's mount side); line at 6.2 m; dies 1 s after it; gun mountable, wave +2.0 s | `j5a.jpg`, `jeep5.out` |
| Officer / enemy waves (user: "Keep officer off for now") | `level.coop_noOfficerWaves = 1` (existing per-map opt-out); log "OFFICER waves disabled"; no wave or assist feed lines | `jeep5/qconsole.log` |
| Panzer (bug-11094) | created by its trigger (ours 38 = disc 251) out of view at disc (1372,466); 192u arc, halts +4.0 s; turret tracks +2.9; cannon +3.6 / +4.2 / +6.8 (stock VehicleTank, autotank recipe); hull MG from +7.6 within 45 m | `pz2a.jpg`, `pz2.out` |
| MG nest | only the gunner (rec 33) walks to the waypoint (4 s cap, ends ~40u short), feeder and lead hold; runners to guns 2 / 5 dropped | `pz2b.jpg` |
| Talkers (trigger 266 = ours 50) | AI off with their own idle (no talking clip on the German model), notice a player 2.6 s after they appear, or when shot | `pz2b.jpg` |

Not matched or not verified: the tank's hull MG is a hidden stock MG42 (the disc builtin 0x6c is a guess at the hull MG);
the cannon aims at the nearest player; tank destruction stays the user-approved rocket kill (TRACE_panzer_kill.md:
the original's rockets do not kill it); the listener waits while a player watches his spot (spawn rule).

## Round 15 (flfix2, 2026-11-12) - window into a floorless house (bug-11115)

| item | finding | result | proof |
|---|---|---|---|
| "Through these windows I can still see under the map" (user) | the ground-floor window of the house south of the jeep road (window about (6480,-3590), house (6330..6620, -3910..-3590)); the house is a shell with no ground floor on the disc too (nothing dropped). The original shows its sky box there: one flat dark colour below the horizon (TRACE_sky_fog.md). Ours showed the edge fill (cobble skirt + cobble ground under the level) | converter `flpit.py`: every floorless pocket closed off by drawn walls gets a render-only lid in that colour (83 81 76), 4u under the ground around it; level edges keep skirt and ground. 1_1: 623 pockets, collision unchanged | offline ray view `rv7b.png` (fill pixels at the window 20743 -> 0); in-game `H:\hzm_work\flpolish\fix2\r15\s1\` |

## Round 17 (flfix2, 2026-11-13) - ambience ("it sounds quiet", bug-11149)

| item | original (TRACE_ambience.md) | conversion | status |
|---|---|---|---|
| Ambience beds | three streamed loops in 11STRBNK.AST (57 s, 192 s, 62 s, 22 kHz stereo) | the same three streams decoded from the player's disc (loop body of each, sizes equal to the reference decodes), aliases fl11_amb1..3, one levelwide loop at a time | exact audio; which bed a zone starts is now read from the .abk's streamed-ref table, not assumed |
| Ambience zones | recs 44-48, spheres, enter starts bed (44, 45 -> 0; 46, 47 -> 1; 48 -> 2), no stop | same records, positions and radii through the converter's transform (level.fl_ambz*); switch on entry by any living player; bed keeps playing | exact rule; zone test 2D (spheres sit at z 0) - a choice |
| Fire crackle | PLAYSOUND 57 of sound set 446 -> 11SCRBNK sample (resolved via 1_1propSnd.som), volume 20000/32767, positional at recs 99 / 100 / 101 | the same disc sample (stream 31, 14 s loop), alias fl11_fire at 0.61; loops at the three spots, 99 and 101 stop on leave, 100 never stops | sample resolved from the disc tables (not heard); falloff 256-2400u a stand-in (EA's falloff not decoded) |
| Burning rag on the molotov | same sound 57 (set 716 -> the same row) | still coop_snd_fire_small until the map swaps in level.fl_fire_alias | stand-in until wired |
| Mod ambience on top | none | coop ambience bed (coop_amb_country, bridged for coop_fl) and its artillery sweeteners also play unless the map sets level.coop_ambienceBed = "none" | user choice |
| In a client | - | not heard yet: needs the map script's fl_ambience thread (handed to the map owner) and a listen | not verified |

## Round 18 (flfix2, 2026-11-13) - after the second human playtest: allies, jeep gun and gunner, interrogation, voices

Mod script only (`maps/coop_fl_1_1.scr`, new `coop_mod/discallies.scr`, an opt-in line in `coop_mod/aihandler.scr`). Runs
in `H:\hzm_work\flpolish\fix2\r17\` (one muted 1080 client each, v107 pak): `base0` / `tune1` (player stands at the
TRACE_allies spot A, never fires; old kit / new kit), `eng0` / `eng1` (player fights: auto-aim at the nearest visible German
plus bursts; old / new), `fin` (use icon, house). Deaths are attributed from the pain handler (`FLSET death ... by=`).

| Item (user) | Cause | Now | Proof |
|---|---|---|---|
| ".30 cal ... two inside of each other" | mounted, the engine draws the turret's own first-person gun (`30cal_viewmodel.tik` on the eyes, world turret hidden from the gunner) while our disc gun mesh followed the aim in the same place | the disc mesh is hidden from the mounted player only (`svflags +notsingleclient`); everyone else still sees the disc gun | `r17/ongun_l_00_c.jpg` (one gun), log `30cal mounted by 0: disc mesh hidden from him` |
| Wounded gunner "kinda flips" | `death_prone` starts face-down; the downed cycle (23A825) lies on his back | settles from the cycle into the stock on-back dead pose (`dead_pose3`) over 1.2 s, stub death handler, pose kept on the body. (Webber's own 23A826_DeadPose was tried first: half-sitting with a raised fist, `base0` stills) | `r17/eng1_dead_b_crop.jpg`, `r17/eng1_death_seq.jpg` |
| Allies "decimating" / "crush the Germans" | paratrooper kit: accuracy 60, health 300, noticescale 50 (spots twice as fast), BAR; AI damage on AI unscaled | `coop_mod/discallies.scr` kit: accuracy 18, health 150, noticescale 100, Garand instead of BAR; `level.coop_aiVsAiDmg 0.5` (AI-vs-AI damage of the other team halved; opt-in, a stock map is unchanged: `r17/stock17_m2l1.log`) | square group (3 Germans) dead after spawn: old +5..+8 s (standing) / +8..+11 s (fighting); new +14..+17 s (standing, kit only) / +17..+32 s (fighting). Whole route with a fighting player: old = allies 6 kills, player 2; new = allies 3, player 4 (all 3 ally kills in the square while the test player was on the .30 cal) |
| Allies "stuck, not moving forward" | trail goals were points on a straight line 820u behind the player, off the path graph (user log: 56 `couldn't find end node`), so they never moved | goals are spots the players actually walked (a trail of positions every 128u), on the ally's side of the player; an unreachable goal (no motion in 2.5 s) is dropped for the next; an ally stranded twice and unseen is put on an unseen spot of the trail; a German of the area alive far off no longer holds an ally the player has walked past; the push never takes an ally further than the player | `r17/eng1` ally positions at every stop: 600-1100u behind the player from the wreck to trigger 66 |
| Same German line "constantly" | one disc line per situation on every German, no line limit | shared cooldown `level.coop_avLineCd = 25` (aivoice.scr 8ec71705), each play logged (`AIVOICE`) | `r17/tune1` log: 7 lines in about 4 min, none repeated within 25 s |
| Interrogation starts "before you get near it" | started at 1100u, through walls | starts within 350u of the officer, or 750u with a clear line from the player's eyes to him | headless `r17/int17_7.log`, `r17/int17_5.log` |
| "heard him killing Castro but he was still alive" | `interrog_5` OPENS with the shot (0.5 s clipped bang and room tail, then his words); we played it while he only aimed and shot after it | the execution is atomic: he aims 5 s (rescue window), then the bang (`interrog_5`), the prisoner's death and the state change in one frame; killed first, the line never plays; the alarm path the same | headless: mode 7 executed, `FLSHOOT 2` and `interrog_5` on the same tick; mode 5 rescued, no `interrog_5` |
| Dialogue after its speakers were dead | the dock lines (and the nest shout) played from a fixed spot on distance only | German lines need a living speaker near the spot and come from him; the dock talk needs calm (no enemy) speakers within 700u, re-checked before each line, and stops for good otherwise | code; not yet seen in a client |
| Panzer "didn't notice it firing" | trigger 38 fired 2400u from the tank: its three shots went off unseen, the rocket pass killed it a minute later | the shots keep the trace spacing but start once a player sees the tank or is within 1500u (60 s cap); the rocket pass waits for the second shot (45 s cap) | code; not yet seen in a client |
| "two houses sections" not seen | ours had only the bomb's fireball | a stock dust cloud at the house as its parts start, then a long smoke column (stand-ins) | `r17/fin` stills |
| Barrel use "not obvious" | no use prompt | the mod's crosshair USE icon (`coop_mod/actprompt.scr`, `hand`) while a player faces one of our use spots within 110u (drop, molotov barrel) | `r17/fin/use_on_*.tga` |
| Ambience | (Round 17) | `fl_ambience` wired; the mod's country bed off on this mission (`level.coop_ambienceBed none`) | boot log `FLAMB start beds=3 zones=5 fires=3` |

Round 18b (client run `r17/dp2`): the Panzer is created out of sight and fires its three shots (trace spacing) once a
player is within 2200u or sees it; seen down the street with the muzzle flash (`r17/dp2_tank5.jpg`), the rocket pass
after the shots. `grenade_nest` is never spoken by the interrogation officer or a man playing dead; the dock talk is
skipped when every German there is already in the fight. MG-nest men with no room behind them die forward or crumple
in place instead of the stock fall-back; the user's legs-up corpse did not reproduce (`r17/dp2_nest_crop.jpg`).
Not done: the tower MG "glitchy" (waiting for the user's detail), the use icon seen on the barrel itself (same code as
the drop).

## Round 16 (flfix2, 2026-11-12) - collision: doorways and arches

User playtest (2026-11-12): "invisible walls" in doorways, arches, lanes and wall holes along the route (screens
10-22). Stills, logs and walk results under `H:/hzm_work/flpolish/fix2/r16/`; offline sweeps
(`walksweep.py`, `routesweep.py`, `cross.py`) in the round's scratch folder. Build v106 (`H:/hzm_work/flpolish/v106_fl_1_1.pk3`).

| check | v95 (as played) | v106 | proof |
|---|---|---|---|
| Octagonal arch from the dark stone room to the lane before the crawl hole (screen 10), off its centre line (x 2990) | standing player stopped under the arch's right chamfer (90-105u up), passes crouched | passes standing both ways (2975, 2985, 2990) | `r16/c_v106/archx2990_ab_stand_pre.jpg` / `_stand.jpg`, `c_v106.out` (origin 2990,-2260 -> 2990,-1974) |
| Arch into the breach yard (screen 22) | passes standing in the test engine | passes standing both ways | `r16/c_v106/yard5180_ab_stand*.jpg` (origin -2700 -> -3082) |
| Engine walk, 50 AI-route crossings both ways + the two arches (1 client) | 82 of 89 standing, 2 crouch only, 5 blocked | 100 of 108 standing, 1 crouch only, 7 blocked (2 starts inside a fitted post, the same 5 as v95) | `main_v95.out`, `c_v106.out` |
| Offline route-pair sweep (MOHAA box 30 x 94 / 54, step 38) | 154 pairs blocked standing | 111 | |
| geoaudit | walkable 74615, void falls 0, must-crouch cells 1277 | 74725, 0, 965 | |
| Screens 11, 12, 15-20 | not located on the map (no positions in the playtest log) - NOT verified | | |

Cause found: Frontline's doors and arches are about 2.0 m (96u) high and their collision is a vertical sheet ending at
the door top (no ceiling face, so the headroom pass never saw them); with the 2u floor slab that left 94u - exactly
MOHAA's stand box - and the engine lifts the box a full step (38u) over any seam or stub before sliding on. Arches'
chamfers start at 90-105u. Converter: `flclear.lift_lintels` (commits 8af40870, 31725dc3).

### Round 16b - the live engine, per screen, step lips

The test install's engine (Nov 10) is not the live one (game/cgame/exe hashes differ). The same walks were run with
byte copies of the live binaries (`G:/mohaa-flpolish/_live1112`, `r16/L_v95.out`, `r16/L_v106.out`): 40 runs, v95 31
standing / v106 32. The live engine honours the map's 38u step, and the octagonal arch passes standing there on v95 too.

| screen | found at | v95 live | v106 live | cause / note |
|---|---|---|---|---|
| 10 octagonal arch | (2945-3002, -2109) | pass | pass | test engine: blocked off centre on v95 (chamfer 90-105u); fixed by lift_lintels |
| 11 lane to the crawl hole | (2975, -2000 -> -1820); hole (2840-2960, -1680) | pass; hole passes | pass | the straight line from the arch to the hole meets a drawn wall, not a defect |
| 16 opening over the VINS LIQUEURS street | upper floor (1600-1680, 1460-1480, z -6), 155u over the street | blocked | blocked | the original blocks it too (sill + material 10/13 sheets 35-115u); the street in front of the shop has no collision floor on the disc either - the original's boundary, kept |
| 19 breach hole into the interrogation room (presumed) | (-1712, 4752) -> (-1750, 4680) | standing blocked both ways, crouch one way | standing one way, crouch the other | partly improved; not confirmed as the screen's hole |
| 20 door from the dotted-wallpaper room | (-1748, 4772) -> (-1862, 4798) | pass | pass | - |
| 22 breach-yard arch | (-2840, 5150-5240) | pass | pass | - |
| 12, 15, 17, 18 | not found | | | - |
| capped lane before the interrogation | (-1232, 4464) -> (-1712, 4752) | blocked standing and crouched | same | the original's crawl tunnel (player-clip sheets 52u over the lane, kept as 61u caps); its floor has a hole at (-1329, 4607): a player who climbs onto the sheet falls through it. Pre-existing, not changed |

Step lips (18-38u rises from the walkable area): 913 edges in 290 places on v106, half of them with no drawn
surface within 6u. Not smoothed: the live engine climbs 38u on this map, so they are not walls; clip half-steps
would be a deviation without a cause.

## Round 16c (collision, 2026-11-13) - screens 12-18 and the capped lane, live engine

Located from the user's own log: the screens' file times (12 at 17:13:49, 15 at 17:17:21, 17 at 17:22:32, 18 at
17:23:04) against his FLTRIG positions, then stills taken there (`H:/hzm_work/flpolish/fix2/r16/Le_v106/*_pre.jpg`).
Walks with byte copies of the live binaries (`r16/Le_v95.out`, `r16/Le_v106.out`).

| screen | found at | v95 (live engine) | v106 (live engine) | cause / note |
|---|---|---|---|---|
| 12 diamond-wallpaper room, door onto the street | room x 2232-2420, y -1700..-1600; door x 2231, y -1676..-1627 (lintel 129u) | the walker stops in the doorway (x 2248) | through to the street (x 2017) | lintel; fixed by lift_lintels. The still shows the CORDIN-GIRARDOT street, not the red barn doors: probable, not certain |
| 15 rusty pointed arches past the bridge | not found: at that time the user was on the Panzer street (1400-1550, 470-900) | - | - | - |
| 17 breach gap with slats and the canteen | (-656, 2620-2700) - matches the screen | passes standing (x -656) | passes standing (x -656) | 16u off its centre: v95 passed once, v106 crouched once; v106 only removed collision there (lintel pieces), so not a regression |
| 18 diamond-wallpaper room onto a barrel yard | room with rubble near (-840, 2700) found; its door to the yard not found | - | - | - |
| capped lane (-1232, 4464) -> (-1712, 4752) | | blocked standing and crouched | same | Not a passage in the original: the line crosses floorless house shells (no disc floor, nothing drawn, only our pit lids) under the original's player-clip sheets at 52u and 94u, with rubble drawn at 57-89u, and only one AI node at its start. The original keeps the player out; kept blocked. The holes are under 61-65u caps, so they can't be reached at the 38u step. An emulator frame would settle it |

## Round 19 (flfix2, 2026-11-13) - visuals after the second playtest

Converter only. Paks `H:\hzm_work\flpolish\v108_fl_1_1.pk3` (f123d82d..e5cc91d2) and `v109_fl_1_1.pk3` (+90c3f927, 92a1a1a3),
commit lists beside them. Stills: `H:\hzm_work\flpolish\fix2\r19\a108\` (v108, LIVE engine binaries on the test home).
v109 seen in a client: `H:\hzm_work\flpolish\fix2\r19\b109\` (hedges, window, pit, crates). Water: `r19\d109\`, `r19\d111\` (v111 = v109 + 8ebfc56e).

| item (user) | cause | now | proof |
|---|---|---|---|
| Pit floor "light grey" (bug-11161) | the lid wore the sky band's 83 81 76; our display chain lifts it to ~112 on screen, the rooms around read 35-90 | 24 23 22 (~40 on screen, like the shaded wall foot); the band colour is kept as `rgb_original` | `r19/a108/pit.tga` |
| See-through hedges, "into nothingness" (bug-11162) | the reskin stretches hedgerow.tga over 1.25x the box: its gappy crown band (image rows 15-45%) covered the top third of the original's opaque hedge box; Frontline's hedges have nothing inside | an opaque core in every original hedge face (the image's leaf body, unraised, 0.85 darker, foot 96u lower where the ground falls away); the card is drawn in front (polygonOffset); above the old top the crown stays open | `r19/a108/hedge*.tga` (v108: crown gaps closed; the void under hedges at `hedgeFar` led to the 96u foot in v109, not yet seen) |
| See-through trees and shrubs | the tree cards near the start are the disc's own sparse branch cards (alpha-tested, two-sided); nothing dropped, no blended foliage in view | unchanged | `r19/a108/treeA/treeB/treeFar.tga` |
| Window smear (bug-11163, user shot0377, by the wall objective) | the disc's out-of-bounds ground draws there (c6 240, 358, 535, 741, 1242, texture 54200) have UVs shared by pairs of vertices: zero UV area, the texture smeared along a line; nothing dropped (offline render of every disc draw: no street there on the disc either) | such ground triangles (n.z >= 0.4, >= 10000 u^2, tiling texture) get planar world UVs at the texture's own floor density | `r19/a108/win.tga`, `win2.tga` (v108: the yard fixed, the embankment still streaked -> v109) |
| "Shooting the water does nothing" (bug-11164) | the BSP had the water (32 CONTENTS_WATER brushes; offline point-contents: water under the surface, nothing above). In v109 (`r19/d109/waterC_*`) a round into the canal threw the STONE impact (flash and chips): the canal bed under the water had no surface type, so the cgame chose stone | v111 (8ebfc56e): the water volume as stock water (CONTENTS_WATER + TRANSLUCENT, puddle surface) and a puddle canal bed: the stone chips are gone (`r19/d111/waterC_strip.jpg`). A white puff still rises at the hit; whether it is the stock water splash cannot be told apart from the gun smoke in these stills, and no stock-map comparison was run. Known, not closed | `r19/d109/waterC_strip.jpg` vs `r19/d111/waterC_strip.jpg` |
| Bridge crates "dropped" (bug-11165) | they are the disc's own records 432/435/436, tilted 10/15/10 degrees about x to sit on the arched deck; our roll had the wrong sign for the engine, so they leaned against the arch (corners 6-11u sunk or floating) | roll fixed in flscene (raw_angles and mohaa_angles): the crates follow the deck (corners within 0-3u). Same fix turns the jeep tumble and the planes' bank the right way (not yet seen) | `r19/a108/crates2.tga`; offline corner check |
| Hedges read as boxes, orange line (coordinator QA of v109, bug-11199) | the MOHAA hedgerow card was lighter, sharper art among the disc's own darker hedge and shrub art (12de80, 129d80, 170980); the original's lane is all disc art | user decision 2026-11-13 (option 1): back to the disc's OWN opaque hedge boxes (16c480), the card and its core dropped (7e21243e); a 96u foot skirt of the same texture keeps the void out from under them; 16c480 now passes the learned upscale (dd970a90: opaque dense foliage gets the cards' wider worm limit; leaf grain kept, colour-matched). v113 + its upscale pak: one dark leaf mass with the disc shrubs, no see-through, no seam line; light level 1:1 with the disc (vertex colour); the lane still reads lighter than the reference overall (display chain, row 'Display chain on disc maps') and the branch cards in front of the lane hedges are yellower. Left: a thin pale sliver under one far hedge (hedgeFar, centre right) and the skirt shows as a dark band where the ground falls away. The grey area in hedgeB2 is outside the playable side (disc draws nothing) | `H:\hzm_work\flpolish\fix2\r19\f113\s_hedge.jpg`, `f113\lane_pair.jpg` (reference left) |
| Lane brightness: neutral display chain (user decision 2026-11-12) | never built: no script, cgame or renderer code reads a disc-map flag (EA notes: 'being defined in the Sealed Orders work'). The test client runs the full mod chain: r_gamma 1.3, r_postProcess 1, r_ppTonemap 1, r_ppExposure 0.7, r_ppSaturation 1.083, r_ppContrast 0.9986, r_ppBloom 1, r_ppSharpen 1, r_mapOverBrightBits 2 / scale 0.71, r_overBrightBits 0. r_gamma is client-archived and a server cannot set it (CG_IsSetVariableAllowed) | measured at the original's lane camera (4:3 crop, mean luminance hedge / road): reference 9.4 / 12.9; ours 24.6 / 26.6; true neutral (r_gamma 1, r_postProcess 0, test client only) 19.5 / 20.6; the existing per-map grade layer (coop_mapGrade expo 0.50, sat 0.92) 11.1 / 11.8. NOT applied: the row goes in the mod repo (docs/tools/grade_profiles.tsv -> coop_mod/cfg/mapgrade.cfg, `coop_fl_1_1 0.50 1.00 0.92 0.00`) - handed to the coordinator; a forced neutral chain would need cgame work | `H:\hzm_work\flpolish\fix2\r19\g114\lane_variants.jpg`, `i116\lane_pair.jpg` (reference, ours, ours at grade 0.50) |
| Lane branch cards yellower (bug-11202) | the stock tree cards that replace 1dd980 etc. (fl_texmap) were graded on Pak2's 256 px tga, while the engine draws the HD DDS override (tree1_5: mean blue 2 against the tga's 24): the vertex grade left them yellow | the drawn image is written into the private pak with its luminance and the disc card's hue (95ec3ec3, luminance recolour 0ef203eb); the disc card itself is olive-yellow (mean 36 34 18), so most of the remaining difference is brightness | `i116\s_i.jpg` |
| Pale sliver under a far hedge (hedgeFar) | the skirt covered only edges at each hedge plane's lowest height; this hedge's foot is bumpy | skirt on every boundary foot edge, texture continued downward (no stretched band) | `i116\s_i.jpg` (hedgeFar) |
| Culling vs the fog | vis_radius is 7000 (cells 1024): nothing within ~7090u can be culled, the fog is solid at 4800 | unchanged: no popping possible inside the fog. Frame time (live engine, 60 fps cap): start overlook 16.6 ms (rf 1.7, bk 1.0), church tower west 15.9 (1.5 / 1.4), tower east 16.2 (0.7 / 7.9) | `r19/a108.out` |

## Round 20 (flfix2, 2026-11-13) - particles, house wall, one-shots

Converter only (commits 0bf6e1bd, 94765973, ffbf73a3; CONV_BUILD 9). Pak `H:\hzm_work\flpolish\v110_fl_1_1.pk3`, commit list
beside it; headless dedicated boot `fix2\r20\boot20.log`: `^~^~^ FLDATA conv 9 pfx 15 oneshot areas 7`, ubersound/fl_1_1.scr
parsed (SERVER) with no error lines. The map script is not changed here: its blocks are with the map owner. Nothing seen
or heard in a client yet. Sweep: `H:\hzm_work\sweep_2026-11-13\SWEEP_fl_1_1.md`; work files `sweep_2026-11-13\sopfx\` (local).

**Particle systems (bug-11184).** The 15 kind-9 records are a 72-byte header plus the same 168-byte block the
CREATEPARTICLESYSTEMBYTYPE templates use (type hash in its first word; 236 such blocks in 1_P.bpd). emt_1_1.emt is not
particle data (no seed word 12345, no type hash: int16 tuples). Read as (flscene.particle): colour range, spawn box,
velocity range, acceleration, start size, emit duration (0 = continuous), rate per second, particle life, spin, sprite key;
start = word 32 high half (1 runs from load, 2 waits for an event). The sprite itself is not on the level (same key = same
sprite). Stock emitter by decoded type; positions through the converter's transform (level.fl_pfx_*).

| rec | our pos | decoded | type -> stock | start |
|---|---|---|---|---|
| 4, 5, 6 | (3564 -3423 -215), (533 -773 -90), (995 1190 198) | grey 0.3, 0.5-1 m, up 1 m/s, 6/s, life 12 / 12 / 14 s | smoke -> tehao_firesmoke_long | load |
| 7 | (1356 -2493 -153) | black, 2 m, 7 x 5 m box, sinks and rises, 6/s, 12 s | pall -> tehao_thicksmoke | load |
| 8 | (4238 -1894 -14) house | black to grey, 1-1.5 m, 6/s, 12 s | smoke -> tehao_firesmoke_long | house (field = event; the original's frames: no smoke before, a black column after, `ref_xemu/trace/b41h_prepost.png`) |
| 9 / 10 | (-2054 4431 -57 / -92) roster fire | smoke 0.18 grey, 6/s, 12 s / flame orange, 0.2-0.5 m, up 0.6-1.1 m/s, 5/s, 1 s | smoke / flame -> tehao_fire | 9 load; **10 event, starter not decoded: not spawned** |
| 11 / 12 | (4614 -2604 37 / 63) dock street | flame 0.6-1 m, 2.8/s, 1 s / black smoke | flame / smoke | load (small flame on the street at trigger 41's moment, `trace/b41_sheet.png`) |
| 13 | (4228 -1916 -13) house | flame as 11 | flame | load (field) - not checked against a frame |
| 208, 209 / 421, 422 | (4190 / 4108 -2836 -112 / -147) the burning car | smoke 5 / 4.2 per s, 12 / 9.7 s / flame bed 0.1-0.8 m, life 1.3 / 0.9 s, rate field 0 | smoke / flame | load (car burning with its column at trigger 41's moment, before any bomb: `trace/b41_sheet.png` frame 1) |
| 51 | (4302 -2932 -104) | StartBeachExplosionBig: its own burst (150 bits at 15 m/s, 0.1 s) + four by-type systems (grey dirt 1.4-2 m up to 20 m/s; cloud up to 28 m/s, 3.7 s; geyser 2-8 m up to 41 m/s; debris) + a 7 s smoke 20 ticks later, CREATEEXPLOSION, vibration 1.5 s | blast -> explosion_bombdirt, removed after 8 s | bombA (AUDIT row 4; its starter on link 6:240 is not identified) |

Scale (`fl_pfx_scale`) is the system's size against its type's median on this level; the engine does not apply entity
scale to originemitter sprites (cg_commands.cpp UpdateEmitter: only dlight intensity), so it is information only.

**House wall (bug-11185).** house_remove_1_1.msh belongs to ObjectivePickUp rec 293: 49 of its 81 vertices coincide with
the baked world at that record's origin, no rotation (the world art carries the hole). The original removes it on
message 74 from trigger 83, the moment the house parts start. Now script_object `fl_om_house_remove` (inline model,
visible from load, clip boxes on its two wall faces, 0.18 m thick). The original also plays sound 54 then (id not resolved).

**One-shot banks (bug-11186).** LoadOneShotSound 53-59 load 11LOAD1-7 (record word 14 = the bank). 431 distinct clips
(541 with repeats between banks). Every bank: entry 1 silence, ~20 pain grunts, then German lines, then American lines
- the area's barks for BOTH sides. Transcribed locally (faster-whisper small, German and English) and placed by our phrase
table: 145 pain, German contact 23 / attack 15 / taunt 12 / backup 10 / grenade 7 / cover 7 / kill 7 / banter (lost him)
6 / mandown 5 / fallback 3 / reload 1, American attack 60 / cover 37 / suppress 14 / grenade 12 / contact 7 / fallback 6 /
taunt 1; 46 unplaced (unclear words), LOAD8/9 not loaded by any 1_1 trigger. Numbered alias sets (the engine plays one at
random from the base name) so the AI voice gets variety without an aivoice.scr change.

| item | original | conversion | status |
|---|---|---|---|
| Particle systems | 15 kind-9 records | 14 placed as stock emitters; rec 10 (the roster fire) runs from level load like every script-less kind-9 record (code decode item 4, round 23; was: "waits for its undecoded start") | data built |
| House wall | swapped out at the house blast | disc mesh, hidden at the blast by the map script | data built; not seen |
| One-shot banks | one bank per area, clips chosen by the AI through AEMSEVENT (computed id, not decoded) | per area, per side, per situation sets on the situational AI voice | data built; situation per clip is ours |
| Visual check wanted | - | emulator stills: roster fire (-2012 4211 disc) before and after the MG-nest street is reached; the house front (4271 -2136 disc) before trigger 41 from the street, for rec 13's flame; the four untriggered spots (3606 -3643), (575 -993), (1038 970), (1398 -2713) | queued |

Round 20b (map script, mod 3c8e943d, sweep items): wired - the 12 load-rule particle systems start with the level
(`r17/r20*`: the burning car and its black column at the bomb site from load, smoke at the roster), rec 8 and the
`fl_om_house_remove` wall go at trigger 41 (`FLSP house wall removed`), rec 51 with bomb A; the one-shot banks feed the
situational voice (Germans de_*, allies us_*; bank = the last area a player entered). `level.coop_noReplicas` (new
opt-out in aihandler.scr, b90c9272) and `level.coop_noCounter`: no ADDED clones or end waves. The door (rec 401) opens and
closes with the use key from both sides; the ScriptSlave move had thrown the leaf to (-39 57 -1) on its first swing,
now stepped by hand in place (`r17/doorc3_sheet.jpg`: open and closed from the face and the side), USE icon drawn (`r17/doorc_icon.jpg`).
Round 20c (emulator stills `ref_xemu/so_fx`, mod f546ed7c): the bomb site matches (wrecked car and dark column, 10 s and 18 s
after bomb A); the house front has no flame before trigger 41, so rec 13 now starts with the house blast (was: load);
the roster fire (rec 10) burns before the player reaches the MG-nest street, so it now runs from load (was: not spawned).
Walked stills (`so_fx/walked_sheet.png`, mod 2451dc60): rec 4 = a burning car with a dark column (matches the
stock fire smoke); rec 5 = a low brownish haze at street level, no column, now the stock lingering smoke; rec 6 = no
smoke seen on the VINS LIQUEURS facade from street level (the system sits at z 198, above the frame; kept as decoded,
open); rec 7 = a burnt wreck with no smoke in two frames, so not spawned (choice: the frames over the decode); rec 10
still burns, a thick black column over the roof, after the MG-nest street. The door was not in view; open.

## Round 21 (flfix2, 2026-11-15) - cover and routes

Decoded from the 1_1 .bpd and the VM traces (`docs/tools/frontline/flcover.py` holds the layout). The 113 kind-5
records are 109 cover points (type hash 0x9101C906, 116 bytes), 3 mounted-gun points (0x5B607813, "MGPoint", word 28 = 8)
and record 0 (0x2070A66D, not a point; undecoded). A cover point carries: position; the quaternion = its facing, toward
the threat; word 13 byte 1 = the side that may use it (0 any 83, 1 Allied 18, 2 Axis 12 - the actor's own team byte);
word 14 = a link tag shared with the BreakingWoodBoxSwap crate it leans on (19 points, one per side of a crate, facing
each other across it); word 28 = type: 1 (28) corner with the wall on the right, 2 (21) wall on the left (measured on
the converted collision: 23/28 and 20/21; a corner spot often holds a 1 and a 2 at one position, 90 degrees apart),
4 (59) behind low cover or a crate, 80 (1, rec 112) not decoded. No message id or group link is stored.
Evidence: 84 of the 85 traced AISETCOVERPOINT calls (and all 259 GETWAYPOINTINFO calls) take a section-3 record
number of a 0x9101C906 record, the 85th is -1 (clear); allies took only team 0/1 points, Germans only 0/2; in run sr_D
ally rec 64 took point 121 and stopped 18u from it, the shouters took 119 and 123 where they stood.

Routes: no actor record holds a path id, and no soldier calls a path builtin in 60+ traces (only the tank's
MECHFOLLOWPATH, argument 3 - path 3 is the stub beside it, but its traced 3.9 m arc follows neither path 3 nor 66: open).
The gun wave's allies (recs 104-106, `sq_wave4`) run the jeep road, within 64u of path 67 for 37/47 and 54/84 of their
samples and near path 99, not paths 43/44. So the actor-to-path link stays undecoded; the paths are data
(`level.fl_npath[id][i]`, now with `fl_npath_id[j]` / `fl_npath_cnt`).

Built (converter commits 804872a2, 4cf8f6b5; test pak v118): `level.fl_cov[k]` (MOHAA position, placed where a MOHAA
body stands clear of the BSP's brushes and the crate boxes, mean 16u from the disc point), `fl_cov_yaw` (facing, toward
the threat), `fl_cov_type` (1 / 2 / 4 / 8 MG / 80), `fl_cov_team`, `fl_cov_tag`, `fl_cov_om` (the crate's inline
model, `$fl_om_<name>`), `fl_cov_grp` (INFERRED: the waking message of the nearest actor record within 15 m that may use
it), `fl_cov_node`, `fl_cov_rec`, `fl_cov_n` = 112. 101 become MOHAA cover nodes (info_pathnode spawnflags + angle): disc
1 -> corner_right (32), 2 -> corner_left (16), both turned 180 degrees (a stock corner node points away from the threat:
measured on m1l1/m2l1/m2l3/m3l2/m4l0, 123 corner nodes), 4 -> crate (128), 80 -> cover (4). Left out: the 3 MG points,
5 second records of a shared corner spot (one node per spot), 3 with no walkable link to a navpoint node.
Proof: 1421 nodes (1320 + 101), 0 in solid, 0 floating, 0 in a crate box, 101/101 walk-linked to a navpoint node
(approximate CheckMove; 100 in a part of >= 10 navpoint nodes, the navpoint parts are unchanged); headless boot: the
engine rebuilt the .pth once (3.1 s) and reused it on the next boot, no Duplicate node / not linked / paths-per-node /
Script Error, the data script compiles (`compilescript`).
Not yet in the map: the script layer (each soldier tethered to the nearest free point of his side in combat, one man
per point, re-pick when the crate breaks or he is flanked; the trail's move-up ends on a cover point; a disc path is
followed where one runs past both the ally and his goal) is handed to the map owner.

| item | original | conversion | status |
|---|---|---|---|
| Cover points | 109 records, AISETCOVERPOINT | 112 data points, 101 MOHAA cover nodes; script layer `fl_cov_think` (mod ba237365, on by default 22fb8b9f) | proven in a client: `r17/dp3` 44 FLCOV lines, Germans and allies take and hold points in the Panzer street, the nest yard and the dock and re-pick when the crate breaks, they are flanked or the enemy is on the point; stills `r17/cover_panzer_street.jpg`, `r17/cover_ally_dock.jpg` |
| Named paths for soldiers | per record: attr 42 = path id, attr 43 = direction (code decode, CODE_FINDINGS_fl_1_1.md) | `fl_axis_path` / `fl_ally_path` + `pathdir` from the record (flfix2 92c17e39); Germans patrol it (fl_pathbeat, reverse when attr 43 = 1), allies run it once (fl_ally_pathrun: the gun wave on path 67); the distance fit is dev-only | decoded |

Layer choices (round 21b): one man per point; allies never take a point closer to the enemy than the nearest player;
MG crews on their marks or guns and men playing dead keep their own behaviour; the scaling extras get cover through
`fl_mk_axis`; a point not reached in 12 s is dropped (some "cannot reach it" re-picks in dp3); `coop_flCover 0` /
`coop_flPaths 0` switch the two parts off.

## Characters (flchar, 2026-11-15) - the disc's own soldiers

Decode: `docs/tools/frontline/flchar.py` (formats in its header). Each actor record's word 18 names a character
definition in `levelfile.lfc`: skeleton, body .dmf, body texture, head .dmf, head texture, two ints, hat .msh and its
offset. 1_1 places 20 definitions on 9 bodies. Sheets: `H:\hzm_work\flchar\` (offline bind and posed, in-game).

| definition | body / texture / head / hat | who (count) | status |
|---|---|---|---|
| 645ffd2b | BM37 / BT01 / HT01 / German helmet | Roamers, StayOnPath (11) | built, ON (all 20 approved and on) |
| 9a138cf4, ed14bc62, 031add4e | BM01 / BT01 / HT01, HT02, HT03 / helmet | Roamers, shouters, MG lead, talkers (7, 6, 4) | built, ON (all 20 approved and on) |
| 2e091524, 590e25b2, c76ab011, b06d8087 | BM03 / BT01 / various / helmet | Roamers, MG feeder (4, 4, 4, 1) | built, ON (all 20 approved and on); GR4 chest piece not drawn (no texture on the disc); emulator rec 67 (so_chars bm03_rec67_*): the original shows a plain field-grey tunic there, no separate layer - leaving it out matches |
| c18e036f, 588752d5 | BM33 / BT01c / HT03, HT02 / helmet | Roamers, MG gunner (5, 1) | built, ON (all 20 approved and on) |
| 3f817f27 | BM02 / BT01 / HT02 / helmet | Roamer, talkers (3) | built, ON (all 20 approved and on) |
| 7f9a5a86 | BM11 / BT02 / HT02b / officer cap | capped Roamers (3) - the emulator's capped Roamer (so_chars ger_cap_face_crop) | built, ON (all 20 approved and on); cap, tabs, tunic match; face shape and visor height differ (head morphs) |
| e6930b3c | BM11 / BT02 / HT02b / officer cap | interrogation officer (1) | built, ON (all 20 approved and on) |
| 9719a637 | BM12 / BT02 / HT03 / side cap | talker (1) | built, ON (all 20 approved and on) |
| dca82ce9, 45a17d53, 42ccb94a, abaf1c7f, 35cb89dc | BM22 / BT21 / HT01b, HT02a, HT03a / M1 helmet with net | GIs, dead GI, jeep crew (6, 6, 2, 7, 2) | built, ON (all 20 approved and on) |
| 07d5b007 | BM22 / BT21 / HT02a / none | interrogation victim (1) | built, ON (all 20 approved and on) |
| adba9dd8 | BM37_20L / BT01 / UHM02 + HT01_128 | not placed on 1_1 (low-detail set) | not built |

## Round 22 - final sweep (flfix2, 2026-11-15)

Converter f695ba5f, 143fd1ca, 760ebc18 (CONV_BUILD 10); test pak `H:\hzm_work\flpolish\v119_fl_1_1.pk3` (built from the
committed tree), commit list beside it. Headless dedicated boots `fix2\r22\boot_a.log` (installed pak: `FLDATA conv 10`,
the 10 generated emitter tiks cached and started, 0 Script Error) and `boot_b.log` (a test copy of the map script with the
round-22 blocks, private home: FLPG / FLAMB / journal vars read, 0 Script Error). Map-script blocks: with the map owner
(`fix2\r22\round22_blocks.scr`). Nothing seen or heard in a client yet. Buglog bug-11223..11230.

| item | original (decoded) | conversion | status |
|---|---|---|---|
| Projectile generator 473 (Panzer street) | kind 10, ProjectileGenerator.lst + `trace/trig256`: on trigger 256 (player enters, msg 357) ONE round of the enemy Panzerschreck definition (weapbul 0x4f79c15b), silent, from its own spot (the end of the tank's path 66, 3.7 m up) at the middle of named path 17 (the road toward the player); one burst of one per switch-on, a second switch-on is ignored | `level.fl_pg*` (pos, kind, rate, burst, cycles, pause, path, aim points, switch trigger); block `fl_pg_all` fires a stock panzerschreckshell along the decoded line (probe: `FLPG rec 473 shot 1 of 1`) | data built; block with the owner |
| Kind-10 layout | word 28 high = the named path the burst is spread along, shot s of N at (s + 0.5) / N of it (jeep pair: paths 43 / 44, the two lines of the jeep road, 10 rounds each at 15/s, one burst); 29 rate, 30 fire argument, 31 / 32 burst, 33 bursts per switch-on, 34 / 35 pause, 37 round | fl_jeep_gens still aims at the jeep (choice of round 10); fl_pg_aim[2..3] hold the original's road lines if wanted | decoded |
| Distant battle fire 212 | no behaviour class, no links: never created | fl_pg_on 0, not built | MATCH (dead in the original) |
| House sound 54 | PLAYSOUND(54) of ObjectivePickUp 293 is called (bq tick 4055) but the record has no sound-set link (11 / 12); the six sets with a 54 row are pickups. Same for 61 on BuildingExplosionParent 96. The blast's sound is the bombs' own sets | nothing to play | MATCH (silent in the original; decode, not heard) |
| Trigger 91 / area 373 | enter = hold (51), leave = release (52); 405 / 425 hold only; release acts only while the spawner has no man up; a man is made when any area-373 member dies (talkers 71 / 72, ally 408, an ambusher); count / delay words not located; the walk's 3 creations of #11 each followed an event 46 (child aborted), not the child's death | `level.fl_area*` (also area 370: trigger 87, r 63 m, hold only, ambush 52); block `fl_amb91_data` reads 91 from data (= the numbers in the map) | data built; respawn 12 s / cap 3 stays a choice |
| Path-finder triggers 49 / 227 | PATHFINDERSETLEVEL(word 14): music level 0 at the start, 60 at the Panzer street; every branch of 1_1M.mpf takes 0..127, so the level changes nothing here | `level.fl_pf*` | MATCH (no audible effect) |
| 46 unplaced barks | 7 entry-1 digital silences, 2 cries (1:22 = 5:21), 37 voiced lines | 39 placed (re-transcribed with a combat-phrase prompt, checked against the placed sets' duration / envelope statistics); low-confidence ones: 1:43, 2:33, 2:35, 4:32, 5:31, 5:33, 5:34, 6:29 | ours (situation per clip) |
| Particle size | [51, 52] start size, [53, 54] end size (metres) | own emitter per system `models/emitters/fl_1_1_pfx<rec>.tik` (stock syntax) with the decoded size, rate, life, colour, box, velocity, acceleration, spin; mod sprites stand in (cfx_puff / cfx_flame); recs 421 / 422 rate 0 -> 4.2 (ours); fl_pfx_stock keeps the old model | built, not seen: the decoded puffs (0.5-1 m) and flames (0.2-1 m) are far smaller than the stand-ins (3.5 m puffs) |
| Entity scale and sprites | - | round 20's note was wrong: cg_tempmodels.cpp SpawnTempModel multiplies sprite scale, velocity and spawn offsets by the entity's scale; not used (it would scale speed too) | corrected |
| Journal, 3 pages | DATA/SHELL/1_1_BLOG.VIV, three images with the text baked in (title "Seaside Stowaway", place, date, orders), Xbox prompts at the bottom | cut above the prompts, `textures/fl/1_1/journal1-3.tga`, `level.fl_journal*`; block `fl_journal_watch` shows them once per player on first spawn (Use next, Fire close) | data built; block with the owner |
| 62 code-509 volumes | WRONG, see the decode audit below: upright cylinders in front of the locked doors; ACTION inside sends 509 to RemoteFakeDoorTrigger rec 478 | built (decode audit) | superseded |

Round 22b (map script, mod 23c52ebe): wired - generator 473 (`r17/dp7`: switched on by trigger 256, one round fired),
trigger 91 from the data (`FLAMB trigger 91 at ( -1804 2722 -118 ) r 1949`), the journal (`r17/dp7_journal.jpg`: pages
shown, Use next, Fire close), and the record start states on MOHAA's actor mood (StartAlert = alert, StartCurious =
curious, StartIdle = the default bored; the idle talkers keep their scene). Cover proof stills: Germans at the dock
crate cover point (`r17/cover_dock_germans.jpg`), a German at a corner point (`r17/cover_corner_german.jpg`), allies
in cover in the Panzer street (`r17/cover_panzer_street.jpg`); no still yet of an ally standing ON a point (the dev
camera found none within 80u of his point at the shot times). Approved additions (user, 2026-11-15) marked in the
deviation table: floorless-house lid, hedge skirt, ground UV repair, crown clamp, execution timing, area-373 cap,
110u crew spots, MG42 3u lower, single-press drop, .30 cal rest spot.
Round 22c (mod a4702840): the journal's key line sits above the page (it overlapped the pickup feed); a cover point
with a living enemy within 160u is not free; clean still of a German holding the dock crate point against the
camera player, no hit blur (`r17/cover_dock_german_clean.jpg`, run dp8).

## Animations (flanim, 2026-11-15) - the disc's own character clips

Decoder `docs/tools/frontline/flanim.py` (format in its docstring; read from the XBE's eMotion code): `emt_1_1.emt`
holds 967 animation ids over 1,446 clips; a clip is a stream of poses at 15 per second (4 ticks of 60 Hz) on the 55
joints of Soldier.skl, plus game events (sounds, footsteps). Clip lengths match the emulator traces' re-issue times
(901: 132 ticks against 126-128; 6506: 80 against 78). Retarget `flanimconv.py` (the EA route) writes them onto the
stock Bip01 skeleton as `fl_a<id>` aliases in the disc character's own tik, gated by `flanimconv.OWN_ANIM` (empty).
Offline sheets: `H:\hzm_work\flanim\out\OFFLINE_fl_scenes_{a,b,c}_v2.jpg` (disc-native), `CONV_fl_jeep_v1.jpg`
(native vs converted). Nothing in game yet; nothing wired into the mission script (the map owner integrates).

| clip(s) | what the disc does | conversion | status |
|---|---|---|---|
| 6500 / 6502 / 6504 | driver, passenger, gunner ride loops (gunner stands at the gun, one foot up) | fl_a6500 / 6502 / 6504 | converted, gated |
| 6501 / 6503 / 6505 | thrown out at the mine (6505: the gunner lands draped face-down) | the root travel kept in the clip (6501 flies 1.3 m) | converted, gated |
| 6506 | gunner's wounded loop, face-down over the rear deck, legs hanging | fl_a6506 (loop) | converted, gated |
| 6507 | gunner pushes up off the deck; the last pose is half-raised (torso up, legs trailing), not standing | fl_a6507 | converted, gated; the decode matches the emulator (`ref_xemu\so_chars\gunner_rise`, 2026-11-16: he pushes up at +146, moves forward low along the jeep, ends half-raised at the front at windscreen height, not upright) |
| 6509-6511 | bumps | fl_a6509-6511 | converted, gated |
| 903 / 900 / 2201 / 2209 / 2221 / 8301 | interrogation officer: talk, idles, hit, death (8301 has 65 alternatives, 41 distinct) | fl_a<id>, alternatives fl_a<id>_<n> | converted, gated |
| 901 | the victim, seated and tied (the disc's chair is not part of the clip) | fl_a901 (loop) | converted, gated |
| 14397 / 14419 / 14423 / 14140 / 14051 | talker, listener, notice, combat | fl_a<id> | converted, gated |
| 784 / 826, 769-779, 764-767 | MG nest gunner (aim loops, 5 alternatives each), feeder, lead (points) | fl_a<id> | converted, gated |
| play-dead men | not identified (no trace names their ids) | stock | open |
| locomotion, deaths, hits, cover, reload | ids not identified yet | stock | next |
| class 1010 (412 ids) | no skeleton: probably lip-sync for the head morph targets | not converted | queued after locomotion |

## Round 23 - code decode applied (2026-11-15)

Source: `H:\hzm_work\codedecode\CODE_FINDINGS_fl_1_1.md` (XBE + 1_1 scripts, static). Converter flfix2 92c17e39, test pak
v120; map script mod (this round). Headless boot: 0 errors, `FLSET patrol on path 71 / 82` with directions.

| item | decoded | now |
|---|---|---|
| Soldier paths | attr 42 path id, attr 43 direction; builtin 0x24 looks the path up by exact id | per record (26 Germans, 6 allies: the gun wave on path 67); the nearest-path fit and the "paths 2 and 151" note are gone |
| Rec 51 landing-zone blast | its only starter shares link 6:240, which occurs once (in rec 51) | never started (was: with bomb A) |
| Trigger 91 / area 373 | respawn 0, count 1; man made on any area death while not held; held deaths lost | no refill (was: 12 s, cap 3) |
| Particle start | load loop makes every kind-9 record without a start script | start = load when word 16 = 0; rec 8 from load; rec 13 kept with the blast (frame) |
| Moods | Idle / Curious 20 s / Alert 40 s re-armed by stimuli (allies 5 s), per-mood sight and fov | MOHAA mood + a decay thread; sight = record metres x 48 (at least 512u), fov = record degrees, set per mood |
| Barks | only triggers 107 / 226 send 'say your line' | SayIncoming and SayGetOutOfTheOpen silent; SayPlanesAbove and AfterTheTanks as before |
| One-shot banks | only the last entered area's bank is in memory | as built in round 20 (fl_os_watch) |


## Decode audit (2026-11-22) - Frontline half of the "everything" pass

Report: `H:\hzm_work\decodeaudit\REPORT.md`; progress and evidence: `H:\hzm_work\decodeaudit\FL_PROGRESS.md`.
Converter: flfix2 (flscene.volume, flpack._fakedoors and fl_vol_*, the tank's record path, flanim OPS, flanimconv
OWN_ANIM = all); mod: `maps/coop_fl_1_1.scr` (fl_in_vol, fl_fakedoors, fl_oa).

| # | item | original (decoded) | conversion | status |
|---|---|---|---|---|
| 21 | Trigger volume unit and shape | native containment test 0x32d90 (XBE): word 11 low = shape, word 11 high / word 12 = lengths x 1/16 m (0x12e2ac = 0.0625); shape 0 sphere (0x32be0), 1 upright cylinder with a height band (0x32c30; 189 records), 2 box turned by the record quaternion (0x32ca0 with 0x54ce0's matrix; 12 records, e.g. trigger 91 = 25 x 7 m at 18 degrees, not a 41 m circle). The old decimetre reading made every volume 1.6x too wide | every radius /16 (flscene.radius_m); every kind-1 record's own volume as `level.fl_vol_*[rec]`; the mission's trigger watch (fl_in_trig -> fl_in_vol) tests the radius, the height band and the box. Ours: the 192u minimum radius kept (a 0.5 s poll steps over a thinner volume) and each box half extent at least 96u; ASSUMPTION the tested point is the player's middle (origin + 40u: a capsule's centre); a box is tested on its two horizontal extents only (its z compare was not followed to the end: on a +-2.5 m reading trigger 61, a 3 x 1.6 m box 3.4 m over the street, never fired in run fl_god_d4b) | decoded; built |
| 8 | Tank route | the tank record's attr 42 = path 3, attr 43 = 2 (HierobjVehicle L0122: the direction flips at each end); Navpoint 225 could hand it a new path (msg 189 over a category-6 link, GETOBJINFO(64) = its word 14 low = 1) but its only link 6:253 is shared by no record: never sent | `level.fl_tank_path 3`, `fl_tank_pathdir 2` from the record (was the nearest-path fit, 66); the drive itself stays the traced 3.9 m arc (fl_tank_trace), which is what MECHFOLLOWPATH on path 3 drew in the trace | decoded; drive = the trace |
| 7 | Locked doors | 62 cylinders (r 1.5 m, -5 .. +2 m) in front of the doors that never open: slot 4 (ACTION inside) sends 509; RemoteFakeDoorTrigger rec 478 (watcher p2 0x010001fd, any sender): HUD text 5 "This Door Will Not Open", PLAYSOUND 96 of the volume's sound set 11:685 at the volume (SOMI row -> 11ScrBnk group 3 entry 38, a 0.31 s rattle), bi_b0 = an AI noise there (0x29ae0, event 51), then REGISTERTIMEREVENT(3, 77): listening again 3 ticks later | built: `level.fl_fdoor*` + the disc's sample; fl_fakedoors: ACTION inside a volume -> the text (to the player who pressed, coop), the sound, `ai_event misc` (stock radius: ASSUMPTION for strength 1.0), one answer at a time, 0.05 s re-arm. `coop_flFakeDoors 0` = off | built |
| 1 | Scene clips | the disc's own clips (flanim) | OWN_ANIM = every placed definition; the mission plays fl_a<id> on men in their disc tik (fl_oa): jeep ride loops 6500 / 6502 / 6504 and thrown 6501 / 6503, talker / listener 14397 / 14419 + notice 14140, the shout 14228 with SayPlanesAbove's and TheyreAfterTheTanks' lines. Kept stock (user-approved designs): the gunner's DBNO drop and lying pose, the interrogation's m1l2a chair staging; MG crews keep the turret's own poses. `coop_flOwnAnim 0` = all stock | built. QA: offline disc-native vs converted sheets `H:\hzm_work\decodeaudit\fl\qa\jeep_crew.jpg` (match; the thrown clips keep their 1.3 m flight) and `talk_shout.jpg` (match; the shout 14228 raises the arm a little lower than the disc, the listener's forearm sits a little forward: retarget, small); run `fl_god_d3`: FLOA jeep driver / passenger thrown and both talkers on their disc clips, 0 errors but the shout (14228 missing from flanimconv.SCENES, added since). Not yet seen on camera: the riders' seat height in the jeep |
| 17 | In-clip game opcodes | the stream reader hands 0xc800-0xcfff to the game's callback (0x37300; tables 0x376a0 / 0x376e8), which reads its own argument words (0x38860): c803 / c806 / c80d / c80e / c80f / c811 / c812 and the 20 ca opcodes take one, c80b two; c803-c811 post anim-marker events to the character's script; c806 / c80f are sounds (c80f n = sound n of 1_1animSnd.som, through the PLAYSOUND player 0x80860); c900 = the last-pose marker; ca00-ca5d = movement sounds (0x80150 -> 0x80226: action = opcode - 0xca01 on the ground's surface, the player's step graph) | flanim.events reads the arguments; flanimconv writes the ca steps / landings as the clip's own frame commands (`footstep` / `landing` / `bodyfall`: the stock cgame picks the sample by the surface - the footsteps' choice). Not converted: c806 / c80f (the animSnd bank was not resolved; one use in the scene clips: the gunner's rise 6507, sound 2), the anim-marker events (no MOHAA listener), the ca argument word (ASSUMPTION 10 = right foot) | partly built |
| 4 | Actor tuning | (code decode, CODE_FINDINGS_fl_1_1_audit.md part 1) hit points = attr 22 (6-60; most Germans 8, MG crews and allies 12, recs 88 / 89 24); weapon slots = attrs 27-29 (weapbul hashes; 0 = Kar98); death drop = attr 23 x attr 24; aim skill attr 30 (cone 3 / 2 / 1 degrees) and aim period attr 32 (0.5 / 1 / 2 s); soldier*.cls = 21 boxes per bone, no damage multipliers; weapbul: difficulty changes only spread and damage (Kar98 3 / 5 / 12) | Germans carry their record's own weapon (`level.fl_axis_gun`, mesh name -> the stock MOHAA gun: P38, MP40, Kar98, Panzerschreck) and its hit points x 5.25 (user 2026-11-22: "based on disc"): the scale keeps the disc's shots to kill - the player's rifle bullet does 10-12 and his SMG 4-6, so an 8-HP German takes 1 rifle hit or 2 SMG hits (12 HP: 2 / 3); 8 -> 42 gives the same counts against MOHAA's multiplayer bullet damage (Garand 50, Kar98 110: 1; Thompson / MP40 25: 2). [PROV] MOHAA's hit-location multipliers, the Armory guns' own numbers and the mod's player-count scaling sit on top, not checked in a fight; the disc's region scaling is not decoded. `coop_flHpScale` overrides; `coop_flRecAI 0` = the old alternating MP40 / Kar98 at stock health. Not applied: the allies (user-approved kit, `discallies.scr`: the disc gives them 12 HP and Garand / Thompson), aim skill / period (MOHAA's accuracy and the mod's scaling stay), hit boxes and region damage (not decoded), death drops | built (Germans) |
| 3 | Particles and blasts | 240-byte particle records (15 placed kind-9, 244 by-type templates in .bpd section 4, named by CRC32 in section 8); sprite = a byte offset of one of the 78 SHPX images in .bpd section 2; CREATEEXPLOSION has no look of its own: each blast is its script's CREATEPARTICLESYSTEMBYTYPE calls (codedecode part 2) | flpfx.py: the 78 sprites -> textures/fl/1_1/pfx, one emitter tik per template / placed record; systems that emit for <= 0.4 s are one burst (anim enter originspawn, count = rate x duration), longer ones an emitter the map stops after the record's duration (0 = never). Map: fl_fx_or / fl_fx_one / fl_fx_mk at the mines (3 sites), bombs, rockets, tank kill (TankVehicle), grey and molotov barrels, the molotov's fuse (BarrelMolotovFuse rag fire), wall breach (one M1_1_WallExplosion system per step, script order), house (BuildingExplosionParent + Falling_BuldingPart dust where each part lands), crates (BreakingWoodBoxSwap), jeep body puff (JeepBody_1_1), generator muzzle flashes (ProjectileGenerator, every 0.096 s while firing); the placed records on their own sprites. coop_flDiscFx 1 (default) / 0 = the stock stand-ins | readings settled by eye (below); MATCH for the bomb-site column, roster column, bomb dust, mine veil |
| 3a | Particle readings (camera pass 2026-11-23, `H:\hzm_work\decodeaudit\fl\pfx2\{dock2,rest2,size3}_sheet.jpg`) | colour bytes, alpha bytes, size fields, rate | colour 0xff = 1.0 (0x80 drew white dust and grey columns against the original's near-black ones: dock2_sheet); alpha = transparency (as opacity the mine / bomb smoke, alpha 0-1, vanishes; the original's shows); size = radius (x2 width: only then do the bomb-site and roster columns and the bomb dust fill the frame as in clips/d_1.4 / so_fx/roster_fire_after2: size3_sheet); rate = per emission x0.7 (>1) / x0.4 (>10) x 60 / period, from the native code (the raw count looked the same at frame level: not settled by eye) | settled (rate: code reading) |
| 11 | Sound banks: graph reader | AEMS module banks; each .ABK holds 1-3 modules (descriptor table at header word 0x10: sub id, object count, EventSystem module index, object offset); 11Load1-9 carry BOTH the bark module (15, fe3) and the script one-shot module (14, fe7) in either order; objects with id 0 exist (VehBnk 0x350 / 0x35c) | codedecode tools/fl_aemsobj.py walks every module in full (it stopped at VehBnk node 38 on the id-0 objects, skipped ScrBnk's first 23 objects on a 0x400 link floor, and read only the first module); the same reader in flaudio (aems_graph) | DONE (bug-11481) |
| 11a | Tank engine | TankVehicle = vehicle type 1 (behaviour 1 state 5); HierobjVehicle behaviour 1 starts AEMSEVENT {module 16, GETSOUNDINFO(3,5), (1,5), (0,5), 32000, 0, type} when the path is taken (event 209 state 1) and stops it only at death (state 14). 11VehBnk module 16: type 1 -> idle loop slot 0 (14.1 s, on while the running level is 0..11) and drive loop slot 14 (16.1 s, on from 4), plus two gear-change one-shots (slots 8 / 21, level bands 9..18 / 11..22) and a pitch table on the level | converter vehicle_engines -> fl11_veh_tank_drive while it rolls, _idle once it holds, off at its death (was: the stock tank move loop, silence once it held) | built (d9); deviations: the running level (GETSOUNDINFO(3,5)) is not decoded, so no pitch change and no gear-change one-shots; drive / idle switch on our move / halt |
| 11b | Jeep engine | types 2 / 3 have EMPTY slots in 11VehBnk on 1_1, and JeepBody_1_1 (an AnimatedMovingMech) never reaches its module-16 code; it plays PLAYSOUND(66) once as it starts (state 6): set 452 -> script-bank entry 29, a 10.1 s run | prop_sounds "jeep": played once at the start (was: the stock jeep loop for the whole ride) | built (d9) |
| 11c | Plane passes | every plane is a FlyThrough_1_1 record (287-292, 301): PLAYSOUND(66) once as its pass starts (state 9), set 450 sub 746 -> entry 21, a 7.5 s flyby (sub 747 = the same entry) | prop_sounds "plane" (sub_link): one flyby at each set piece's start (was: the stock Stuka / P-47 loops for the whole flight) | built (d9); distances (600 / 8000) ours |
| 11d | ImpBnk / GunBnk / VocBnk | ImpBnk = modules 5 (sub 81e) and 3 (sub 637); GunBnk = modules 1, 10, 6; VocBnk = module 8 (the bark module's fallback when a soldier's voice flag is set: L0040 sends module 8 if local2) | not converted: their senders (impact material, the disc's own guns) are stood in by the engine's own impacts and the Armory guns | open (no evidence-backed use yet) |
| 5 | Bark clip choice | DECODED: the soldiers' voice behaviour 2 (SoldierA_Roamer L0040) sends AEMSEVENT {module 15, event, speaker type (m14.f42), GETSOUNDINFO(0,2), (1,2), 0}; module 15 = the resident LOAD bank's fe3 module; param 0x968 = event 1-10 picks a random index range per voice family (09.0b / 09.04 selectors on 08.01 ranges), param 0x969 = speaker type (13 -> 5 families: German, American, 3 silent). Senders: 1 hit, 2 death, 3 attack start (b0 state 41), 4 move to a cover point (b0 58), 5 cover point re-picked (b0 49-53), 7 Alert entry + squad-signal anims; 6 Curious, 8 alarm run, 9, 10 have no live clip on 1_1. The earlier emulator "bark candidate" 0x5dc90 is the PLAYER's footstep code (module 4) | converter: oneshots "events" builds each area set from the bank's own groups (flaudio.bark_slots, flpack.bark_sets): de_ / us_ contact (7, German only), attack (3), cover (4), fallback (5); suppress, backup, banter, kill, mandown, taunt, reload get no disc line (the original has no such event) | built (d9, bug-11478); deviations: when a line plays follows our aivoice situations, not the original's state changes; 1 / 2 (pain / death) stay the engine's own sounds (as before) |
| rec 4 | Burning truck smoke (dock street) | a dark column and flames over the truck (`ref_xemu/so_fx/rec4_walked.png`); the record's origin is 0.84 m UNDER the cobbles (z -4.49 m, street -3.65 m) | the engine never sent the emitter (an origin inside the world has no cluster); converter _pfx_lifts: a placed system under walkable ground with no floor beneath is lifted to the ground + 0.1 m (only rec 4 on 1_1) | built (d9, bug-11480); not yet seen on camera |
| 3b | Tank hits | GunVehicle heavy hit: systems ddbf2761 / 44b676db / 22e95db3 at the turret + PLAYSOUND(61) of set 519 (entries 17-18) (TRACE_panzer_kill) | fl_tank_life: every health drop above 0 plays flpfx GunVehicle_hit at the tank and prop_sounds "tank_hit" (entry 17; the random pick of 18 not taken) | built (d9); not yet seen on camera |

## Deviations from the original (for the user; choices are not settled here)

| what | original | conversion | forced or choice |
|---|---|---|---|
| Player loadout | Frontline's weapons | co-op Armory loadout | choice (user decision) |
| Particle colour over life | each particle drifts from its start colour (between A and B) to its end colour | one colour per system = the mean of start and end (MOHAA's emitter has no colour drift; `colorvelocity` is wired to angular velocity in the engine) | forced (engine) |
| Particle fade | alpha drifts linearly from start to end | MOHAA fades to 0 from a delay: delay = life x end/start opacity (same mean opacity); a system whose end is as opaque as its start pops out at the end of its life | forced (engine) |
| Short particle systems | emitted over their duration (<= 0.4 s, e.g. the mine dirt 0.13 s) | all particles at once (one burst) | forced (a script_model carrier draws one-shots only from animation commands) |
| Particle orientation | each system's acceleration rotates with the placed object | placed records: acceleration in world axes; by-type offsets rotate with the object (tank, wall, crate, jeep) | choice (no placed record is rotated far enough to show) |
| Placed smoke rec 4 (the burnt car down the dock street) | a dark column (so_fx rec4_walked) | its system spawns at z -215 and showed nothing in two framed passes | open |
| Tank hits / GunVehicle | each heavy hit: ddbf2761 / 44b676db / 22e95db3 + sound 61 | not wired (the stock tank's damage has no per-hit hook here); GunVehicle state 15 is overridden by TankVehicle's, so its set never plays on 1_1 | open (hits) |
| Air strike on the Panzer | the P-47's rockets do not kill the tank (TRACE_panzer_kill.md: hull 180, tracks 80 each) | rockets hit and destroy the Panzer | user decision (rockets-to-Panzer) |
| Canal water look | flat disc water | mod water under a stock shader name, up normals, world-space UVs (tile 512) | choice (user decision) |
| MG42 yaw | record yaw = gunner's side | muzzle = record + 180 | forced (engine convention) |
| MG42 height | 22u over the support | 19u (stock MOHAA mount) | choice, 3u - user-approved 2026-11-15 |
| MG42 rest pose, unmanned | unknown | muzzle up about 45 degrees (MOHAA turret idle) | forced (engine) |
| MG42 gun 3 (rec 302) | the jeep's .30 cal, spawned by message when the jeep's track ends, mountable | disc MG30_cal mesh on a stock turret; arc 180 each way | forced (engine turret); arc a choice |
| Panzer drive | created at its trigger, 192u arc in 3.9 s, cannon +216 / +251 / +407 ticks, hull MG from +449 | same timings; stock VehicleTank, cannon at the nearest player, hidden MG42 on the hull (bug-11094) | MG a stand-in |
| Jeep | body and four tyres on pre-authored tracks | disc meshes origin-stepped on the disc's keys (20 Hz); wreck = the disc body where its track ends | forced (script_model movement) |
| Jeep crew poses and animations | disc animations 6500-6511 on body nodes | stock MOHAA poses: seated driver and passenger, gunner at the gun, thrown = death_mortar_high / death_mortar_twist on an invented 0.7 s arc, wounded gunner = A_22_driver_cover; no bump animation (6509-6511) | driver / passenger: now the disc's own ride and thrown clips (decode audit); the gunner keeps the user-approved DBNO drop |
| Crew fades | 6 s fade-out of driver, passenger and gunner | 6 s fade on fade-capable clones of the stock skins (same textures) | forced (stock skins have no entity-alpha stage) |
| Thrown crew rest spots | not traced | 110u either side of the wreck | choice - user-approved 2026-11-15 |
| Death-ambush pair at the bomber (recs 69, 70) | created 267 ticks after the bomber starts | same, through the out-of-view spawn (may wait while a player watches the spot) (bug-11084) | timing exact unless watched |
| German shouters at the bomber | one line with sound (planes above, +91 ticks), two animation only | same; the line plays from the shouter's record place even while his spawn is held out of view | exact (sound); animation not carried |
| P-47 passes and rockets, speed | .mvd header rate (1 tick per key) | same since bug-11080 (twice the earlier speed) | exact by the header; not re-shot |
| Mine blast effect | disc particle records | emitter built from the records; several fields "read as"; alpha 0.25 | inferred; alpha a choice |
| Jeep crew fate | trace: driver and passenger thrown out at the blast and fade; gunner wounded, speaks when the player reaches the gun, then fades | default = trace; `coop_fljeepcrew 1` (off) = two stay in cover | settled by the trace |
| Fire at the jeep | trace: no crew member fires; generators 471 / 472, 10 volleys from +70 to +122 ticks, from two points above and behind the jeep (the strafe) | generators at the disc points, aimed at the jeep (no direction is stored); tracer and gun sound are stock stand-ins | aim = inferred; `coop_fljeepcrew 1` (off) = gunner fires |
| Jeep .30 cal position | created at +284 ticks | the mesh rides the body; the usable gun is created at +284 on the record's rest spot | choice - user-approved 2026-11-15 |
| Inside floorless houses (seen through windows) | nothing drawn: the sky box's flat dark lower band shows | a flat lid in that colour 4u under the street (bug-11115); same look from a window, but it is geometry: it hides the foot of a cut-out ruin card or wall where that runs below street level, and fog tints it with distance where the sky was unfogged | choice (stands in for the sky band) - user-approved 2026-11-15 |
| Hedges (round 19c) | opaque hedge boxes (16c480) | the same disc boxes and texture (upscaled on the player's PC like the other textures), plus a 96u skirt of that texture under each face (bug-11199) | exact art; skirt a choice - user-approved 2026-11-15 |
| Smeared out-of-bounds ground (round 19) | the disc's zero-UV-area triangles (c6 240, 358, 535, 741, 1242): a smeared line of texture | planar world UVs at the texture's own density (bug-11163) | choice (repairs disc data) - user-approved 2026-11-15 |
| Gunner's line | sound 82 | stream 17 "mg_hurt" from the player's converted audio | inferred mapping, no reference audio |
| Play-dead men | none: StartByIdDeathAmbush makes an ALERT man the moment someone of its area dies (all six records StartAlert, codedecode item 3) | nobody plays dead by default (decode audit); coop_flPlayDead 1 = the old lying / rising men (ours) | exact (default) |
| Fly-throughs | 287, 289, 291, 292, 301 started by triggers; 288 and 290 never started | the five; 288 and 290 removed | - |
| Bombs | both are children of the bomber pass: made at +153 / +219 ticks, land at +261 / +309 | same times and points (bug-11080); blast = stock emitter, sound, radius damage, shake | timing exact; blast look a stand-in |
| House parts | start 303 ticks after the bomber starts | same (5.05 s on the bomber's clock, bug-11080) | exact (timing) |
| Rockets | launch when an object (inferred: the tank) enters trigger 255 | launch when a player enters it | inferred |
| AI behaviour, accuracy, health | Frontline AI | MOHAA AI with the mod's scaling | forced |
| AI kept asleep until the player is near; spawns deferred out of view | unknown | fl_offscreen gating, deferred spawns | choice (user: no fights off-screen) |
| Allied squad behaviour | generic soldier AI (TRACE_allies): fight from the spawn, push when the area's Germans are down, trail 16-19 m behind the player, never lead, cover via AISETCOVERPOINT | the traced rule for every ally (fl_ally_trail), trail spots from the players' walked positions, the disc's cover points (fl_cov_think) | traced rule; balance user-approved 2026-11-13 |
| One ally moved | (799,479) | (760,479), out of a wall | forced, 39u |
| Intro crates | BreakingWoodBoxSwap x20 | the disc's crate mesh and texture, collision sized to it; break sound is a stock stand-in; nothing dropped | forced (sound) |
| Resistance drop | small package between the crates, hold ACTION about 1 s | the disc's mesh; taken on a single USE press | choice (hold time) - user-approved 2026-11-15 |
| Models | Frontline models | MOHAA stand-ins where no conversion exists | forced |
| Characters (flchar, 2026-11-15) | 20 disc character definitions on 1_1: 9 bodies (BM01/02/03/11/12/22/33/37), one head with 37 morph targets, 10 head textures, 4 hats; each actor record names its definition | the disc's own meshes and textures (player's PC only), re-posed from the disc A-pose onto the stock Bip01 standing pose and driven by the stock animations; one level of body-only smoothing; every character texture 4x on the player's PC - bodies, heads, gear, hats and the fade twins (30 of 30 passed the upscale QA; insignia, lettering and the 32 px helmet decal kept as a plain resample); OFF in game (stock models) until each sheet is approved (level.fl_chr_own) | forced (no disc animation decoder yet); gate = user QA |
| Faces | the head's 37 morph targets: 1-10 mouth shapes (lip-sync), 12-15 eyes/brows, 16-27 expressions, 28-37 head SHAPES; a definition's first int (0-9) picks shape 28+int (capped Roamer: shape 34 = the emulator's long face, heavy brow); the second int (0-11) is not a resting expression | each character's own head shape (user approved 2026-11-15); expressions and lip-sync not used. Under a helmet or cap the crown keeps the smaller of its neutral and shaped form (blended 4 cm below the rim), so no shaped head pokes through; hats keep the disc's size and offset (checked on all 19 hatted characters, HATS_clamp_check_v4) | exact shapes; crown clamp a choice (hidden under the hat) - user-approved 2026-11-15 |
| Fingers | flat disc bind hands, disc finger animation | curled into the stock grip (30/45/30 degrees, thumb 10/15/15) so stock weapons sit in the hand | forced (stock animations never move fingers) |
| Jeep riders | disc crew models faded out | their own disc models on fade-capable twin shaders (blend + entity alpha), the script's 6 s fade unchanged; stock fade paratrooper only as fallback | exact (models); fade look by the script |
| Castro (interrogation challenge) | not on the disc (ours) | stock model | - |
| Interrogation victim | BM22 US body, HT02a, no helmet | same (definition 07d5b007) | exact (when approved) |
| Textures | disc textures (64-256 px, up to 8 units per texel on the ground) | 9 CC0 swaps, Poly Haven, tinted to the disc texture's mean colour with its own stains laid over (hd/CREDITS.txt): mud x3, roof slates, planks (round 7); look round 2026-11-12, user 'replace the smudged walls and ground': ground 54200 + b3600 -> stony_dirt_path, mossy whitewash 6180 + ccf80 -> worn_mossy_plasterwall (the plank wall 41180 swap was withdrawn after QA: too new; it is upscaled instead). Every other texture: the player's own image, 4x learned upscale on the player's PC by default (lettered sheets, blended sprites and fine leaf sprays keep the original) | user decisions 2026-11-11 and 2026-11-12 |
| Textures, round 3 (2026-11-15) | disc textures; the learned upscale rejected 143 of 549 (smoothed grain, invented 'worms', text) | 4 more CC0 swaps (user standing permission for online CC0): weathered board walls d080 + 67180 -> weathered_planks, corrugated sheet 38280 -> worn_corrugated_iron, dark earth 123b80 -> brown_mud_dry; and (user 'Online') brick wall 4aa80 -> dark_brick_wall, two repeats, its mortar toned down to the disc's dark joints. All tinted to the disc mean with its stains laid over (hd/CREDITS.txt). The upscale's rejects get a soft retry (grain re-laid or invented detail damped, held inside the texture's own colour range): 64 of 85 kept on a side-by-side sheet; the 14 it made worse (fl_texmap nosoft) and every lettered sheet (signs, the cigar box, the Renault sign, the Balkenkreuz) take a careful 4x (clean enlargement + 20 % ESRGAN detail held to the source's colours; user 'as long as you are careful' / 'double check the text': every letter checked side by side and in game); the coin c2_138800 a plain enlargement | user decisions 2026-11-15 ('everything', 'Online') |
| Smoke (generated emitters, 2026-11-16) | the disc's placed smoke / pall systems: near-black puffs whose size is relative to the disc's own smoke sprite | every generated smoke / pall emitter (recs 4-9, 12, 208, 209) reads that size relative to our stand-in puff (smoke x4, pall x3), grows over its life (1.8x / 1.6x), alpha 0.5 / 0.55 and a dark-grey colour (x3 / x8): read as metres they drew small opaque black blobs drifting off; the original's house and car smoke are soft dark-grey plumes several metres wide (ref_xemu/trace/b41h_prepost.png). Rate, drift and life stay the disc's; flames untouched | look fix (coordinator QA r17 fin3) |
| Shop fronts: sliding along them (2026-11-16) | the disc keeps a player-clip sheet smooth across a whole facade, so a player walking into the Bazar de Varzy front slides ~230u along it to the alcove (ref_xemu/so_fx/bazar bz_01/02) | the converter keeps collision only where something is drawn (the facade sheets are dropped; the one over the window recess, c1 324/325, is kept), so ours stops dead at the window's side frame; nobody can get in either way | forced by the 'blocked only by what you see' rule (flfix2) |
| Tree and leaf cards 1dd980, 12c380, 15b680, 15f800, 1d5680, 1d9800 (look round 2026-11-13) | the disc's 128-512 px leafy tree and branch cards | the mod's own HD stock MOHAA tree cards (models/natural tree1_3/1_4/1_5, tree4_3/4_4; drawn at 1024 px), hard cut-out kept, graded to each disc card's mean colour on its solid texels; the 2:1 tree card 124280 keeps the disc's image (no stock card of that shape) | user-approved "Yes upgrade" |
| Sky | 6-face box on the eye, unfogged | the six faces captured from the emulator, in the player's private pak only; stock sky when they are absent; drawn on a hull around the map | exact textures; hull forced (engine) |
| Fog and far plane | fog colour 104,106,109, linear 5..100 m of view depth (re-render proven, TRACE_fog_colour.md), far clip 100 m, clear colour 48,48,48 | linear 240..4800 units, same colour; no far cull (the sky box shows past the fog end); clear colour not represented | exact fog; no cull forced (bug-11058) |
| World light | vertex colours, 1x | vertex colours x 0.352 to cancel the renderer's 4 x 0.71 map light; measured equal to texture x vertex colour with the display chain off | forced (engine); exact by measurement |
| Display chain on disc maps | none (emulator output as is) | the client's r_gamma 1.3 and post chain: ours is 2.0-2.6x the reference at the lane; the user's neutral chain (2026-11-12) was never built; proposed: per-map grade expo 0.50 / sat 0.92 (measured 1.0-1.2x) | BUG, not a choice (user decision); fix handed over (mod repo grade row) |
| Wall breach | trace timings and break frames; use at the molotov (6 s fuse) or 3 hits on one barrel (no fuse); hint "Press ACTION to Ignite Rag" | same, both ways (bug-11087, bug-11083) | blast look a stand-in (stock emitter) |
| Texture edges | clamp on non-tiling surfaces | half-texel UV inset on non-tiling axes | forced (engine has no per-axis clamp here) |
| Fire at the jeep, look | disc tracers | stock muzzle flash and tracer (a white streak in stills) | stand-in |
| Wounded gunner | 6506 face-down over the rear deck, 6507 rises to the front, fades | thrown off at the blast, coop DBNO pose on the ground, his line when a player comes up, then dies (bug-11093) | user-approved 2026-11-12 |
| Light on soldiers and objects | vertex colours | the engine's light grid; the ambientlight 40 40 40 key has no visible effect in this renderer | forced (engine) |
| Weather | none | none (rain theme removed in round 11) | exact |
| Objective wording | disc / published pause screen wording | ours, including two prisoner lines; HUD text = objective menu text | choice (user decision 2026-11-12: "Keep ours it's fine") |
| Collision | disc collision | built from drawn geometry plus: riverbed, edge-of-world clip, lip ramps, 10 widened spots, 114 kept clip sheets, 5 patches | forced (no usable disc collision); each widened spot is a choice |
| Tower ladder | disc ladder | built from the drawn ladder; scripted mount and exit at the top | forced (engine top mount needs floor behind the ladder plane; the tower has a wall there) |
| Canal depth | (user request, not a disc fact) bed should not show through | unchanged default (tehao_indoorwater, bed visible); two converter-only options shot: FL_WATER_SHADER=textures/water/subpen_opaque (dark, opaque) or textures/water/canal_water (green, opaque) | OPEN, user to pick |
| Time and frag limits | none | switched off for the mission | forced (co-op) |
| World mirroring | - | none (un-mirrored since bug-10965) | - |
| Hint memory in co-op | hint shown each time a player is near | the coop cgame shows each hint key once per player profile (`coop_hintSeen`) | mod-wide rule, not changed here |
| Officer / enemy-wave system | none | off on this map (`level.coop_noOfficerWaves = 1`) | user decision 2026-11-12 |
| MG runners to guns 2 and 5 | not seen in the trace (24 s with the player in the trigger) | dropped (bug-11094) | trace; the route itself not traced |
| Jeep .30 cal facing | mounted, it looks west over the windscreen into the square (frames w6 / w7 / wn) | same since bug-11095 (the record yaw read 180 off); 360 traverse | exact (facing) |
| Gun wave rule | only a player using the gun starts it; walking away unused or trigger 420 switch it off | mounting starts it 2 s later; walking away unused or trigger 420 start it at once, out of view (bug-11100) | user-approved 2026-11-13 |
| Wounded gunner's death | (no death: he fades) | prone death (death_prone) from the downed pose, corpse stays (bug-11095) | user-approved 2026-11-12 |
| Interrogation | three lines (4, 5, 6; the third loops), the officer idles until he notices the player; no execution, the prisoner never reacts (TRACE_interrogation.md) | ours kept: nine bank lines, execution unless the officer is killed first, optional rescue, Castro challenge | user-approved 2026-11-13 ("I want to keep ours") |
| Interrogation start | trigger 37 (3.2 m from the officer) | 1100u of the clipboard: trigger 37 lies inside our 200u rescue release (bug-11100) | forced by the kept rescue |
| Clipboard pickup | walk within 2.3 m (rec 282) | same (bug-11100) | exact |
| Trigger messages | start / clean-up / disable / enable per trigger | same since bug-11097 (every trigger used to start its groups) | exact |
| Jeep squad (recs 64, 65, 103) | hold while their Germans live, push to the last one, trail 16-19 m behind the player, removed at trigger 66 | same (bug-11098); trail distance 820u behind a player 920u past them | exact by the trace |
| Death-ambush pair (recs 69, 70) | created on the death of shouter rec 215, killed by bomb A | same; bomb A kills him within 600u (our blast radius would not) (bug-11099) | blast reach forced |
| Panzer projectile generator (rec 473, trigger 256) | switched on by trigger 256 | not built (parameters not decoded); trigger 256 starts the tank (bug-11098) | missing |
| Trigger 91 (death-ambush area 373 off / on) | disables rec 407's ambush while the player is inside | not emitted | not built (untraced effect) |
| Bomber timing | real speed: bomb A and the house down within 0.4-0.8 s of trigger 41 (dock_early / house_early sheets); traced motion times are slowed | the bomber is inbound at the trigger (keys start 3.95 s in): bomb A +0.40 s, house with it, bomb B +1.20 s, ambush pair with bomb A (bug-11110) | lead derived from the frames |
| Dock and exit | dock = trigger rec 1 (r 25 m); end = exit trigger rec 2 (r 2.6 m) walked into with 1-5 done, text 36, ENDLEVEL | same spots and radii; our crate objective completes at the exit, crate prop there (bug-11103) | exact (positions) |
| Hints on entering | drop lid rec 383 (text 52), MG volumes 283 / 384 / 539 / 302 (text 274), molotov (501) | same texts on entering, once per player (and the coop cgame's once-per-profile rule) | exact text |
| Area-373 ambush respawn | respawn on death, gaps 600-1050 ticks, held while inside trigger 91; limit not decoded | none: respawn 0, count 1 on recs 90 / 92 / 407; a man is made the instant an area member dies while not held, a death while held is lost | exact (code decode): no refill - one man per spawner, finished once killed; the 12 s / cap-3 fill-in is gone |
| Rec 539 MG | using it starts the MG-nest crew early | same (bug-11103) | exact |
| Field phone | its volume (rec 387) plays sound 40 once | plays our bank's sound-40 cue once on entering (bug-11103) | cue mapping by id |
| Allied soldiers (all groups) | generic soldier AI: fight from spawn, push when the area's Germans are down, trail 16-19 m behind the player | same rule for every allied soldier; they no longer follow closely (bug-11103) | trace rule applied to all groups |
| Starting weapons (message 43 at the drop) | given on touch | our co-op Armory loadout | user-approved |
| Message 509 | WRONG (was "dead, no listener"): RemoteFakeDoorTrigger rec 478 answers 509 from any sender (filter 0) - the locked doors (decode audit) | built | superseded |
| Bump-through toggles (46/47) and halt marker 246 | AI bump-through and a halt marker for soldiers | not built: stock AI navigation | forced |
| Panzer and bullets | bullets do nothing; the player may leave it alive | immune to bullets; destroyed only by the rocket pass (user decision) | exact (bullets) |
| Objectives | six: drop, Man Machine Gun in Church Tower (rec 384), roster, wall, dock, the exit | same six in the original order, objective 2 with the disc's own texts; optional rescue moved to slot 7 (bug-11111); proven on foot: ladder from the base, use, objectives 1-6, mission end | user-approved 2026-11-13 ("Add the og objective") |
| Stock AI barks | only the original's lines | level.coop_discBarksOnly = 1: no stock voice, chatter or taunts (bug-11110); the disc's two German combat lines (script bank 20 'Lass ihn nicht abhauen!', 21 'Das warst du, alliiertes Schwein!') on the AI voice's attack and man-down situations (bug-11113) | user-approved 2026-11-12; situation mapping a choice (the original's AI states are not decoded) |
| Church-tower MG mount | a tripod MG on the tower floor (the walk frames do not show its height) | the stock turret on sandbags at floor + 44, disc x/y and facing kept: MOHAA's use trace cannot reach a turret at floor height (bug-11112) | forced (engine use height) |
| Other mounted guns (1, 2, 5, 6) | usable | reached and mounted on foot with use (run guns); facing from the records, not checked against frames | facing unverified |
| Allied soldiers' strength | Frontline AI (not decoded); in the trace allies support and can die | kit accuracy 18, health 150, noticescale 100, no BAR, AI-vs-AI damage x0.5 (`coop_mod/discallies.scr`, `level.coop_aiVsAiDmg`) | user-approved 2026-11-13 ("balance the allies on the frontline missions") |
| Trail goals | AISETCOVERPOINT on the player's route | a spot the player walked, 500-900u behind him on the ally's side; unseen placement of a stranded ally; round 21 layer: the free disc cover point within 300u of that spot | cover-point layer ON (mod 22fb8b9f, proven r17/dp3-dp6): the move-up ends on a disc cover point near the trail spot; forced (no decoded route link) |
| Cover points (round 21) | 109 records: facing, side, crate tag, type; the AI picks one per man | same points; placed up to ~44u off (mean 16u) where a MOHAA body fits; MOHAA cover nodes: corner types flipped 180 degrees and one node per spot (5 second records of a corner pair have none), 3 unreachable spots have none; the stock cover state fights from them (corner lean / over-the-crate), not Frontline's own | forced (engine body size, node conventions); group link inferred |
| Mounted-gun points (round 21) | 3 MGPoint records | data only (`fl_cov_type` 8), no node | not used |
| Soldiers on named paths | per record: actor attr 42 = path id, attr 43 = direction (round 23) | Germans patrol their own path, allies run theirs once (the gun wave on 67); the round-21 "link not found" reading is gone | exact (decoded) |
| Jeep .30 cal, mounted | the disc gun seen from behind | the stock first-person 30cal for the gunner, the disc gun for everyone else | forced (engine turret view model) |
| Wounded gunner's death pose | (no death: he fades) | settles into the stock on-back dead pose, body stays | user-approved 2026-11-12 (pose changed 2026-11-13) |
| Interrogation execution | never happens (line 3 stalls) | after interrog_4 he aims 5 s, then the bang that opens interrog_5 = the shot | choice (kept from the user's rescue design) - user-approved 2026-11-15 |
| Interrogation start | trigger 37, 54u from the officer | 350u, or 750u in line of sight of the officer | forced (our 200u rescue radius) |
| Panzer first shot | +216 ticks from its trigger | same spacing, from when a player sees it or is within 2200u; rocket pass after the second shot | choice (user: it must be seen firing) |
| House collapse dust and smoke | disc particle records | stock dust cloud and smoke column; round 20: the smoke column at the disc's own record 8 spot (tehao_firesmoke_long), once the map script takes the block | stand-in (forced: no disc sprite carried) |
| Placed particle systems (round 20) | 15 kind-9 systems with their own sprites | stock emitters chosen by decoded type (smoke, pall, flame, blast) at the disc spots; size not carried (engine ignores entity scale on emitter sprites) | forced (sprites not on the level); type mapping a choice |
| Particle start rules (round 20) | record start field + messages | every kind-9 record with no start script (word 16 = 0) is made at level load (code decode); word 32 high = particles per emission; rec 51 never starts (its link 6:240 has no partner); rec 8 from load; rec 13's flame kept with the house blast (emulator still house_front_pre41 shows none before trigger 41) | decoded; rec 13 against the frames |
| House wall section (round 20) | house_remove swapped out on message 74 | disc mesh on rec 293, clip on its two wall faces (0.18 m slabs, windows included), hidden by the map script with the house parts; sound 54 not played | clip shape a choice; timing exact once wired |
| One-shot barks (round 20, decoded 2026-11-23) | 11LOAD bank of the area entered; the clip group per AI event is decoded (decode audit row 5) | same banks per area; each situation plays the original's group for one event (contact 7, attack 3, cover 4, fallback 5); the transcription table is no longer used | which event a situation stands for, and when it fires, are ours (our AI is the engine's) |
| Use prompt | hint text on approach | hint text plus the mod's USE icon when facing the spot | user-approved 2026-11-13 |
| Collision over doors, arches and wall gaps (round 16) | the wall's collision ends where it is drawn (about 96u over the floor, arch chamfers from about 90u) | collision only: whatever hangs 56-136u over a floor that runs on level through the wall is cut away up to 136u over that floor; the AI-route carve cuts walls to 136u (ceilings still 106u); doorway soffit caps at 136u. Shots pass through that band of drawn wall over an opening | forced (MOHAA's 94u stand box + its 38u step-up) |
| Low openings the original crouched through, 56-82u high | crouch | can be walked through standing where the opening runs on level both sides | side effect of the row above |
| Enemy count at 2+ players (coop_mod/discscale.scr) | one player | 1 player: exactly the disc. 2+ players: a wave (the level start, or a group's start trigger) gets extra men shared over its plain Roamer records, each at his record's place after that record's own man, only when no player sees the spot (fl_seen; after 90 s the nearest unseen German record within 1500u; never spawned in view), built by fl_mk_axis (same off-screen wake, voice, area); factor on the wave 1 / 1.5 / 2 / 2.5 for 1 / 2 / 3 / 4+ players (nearest man), at most 8 extras a wave, 24 live Germans level-wide, the live-German hardcap and a free-entity floor; the area clean-up removes them and the allies' area-clear test counts them; the area-373 respawn cap (3) scales the same way. Never scaled: ambush / play-dead men, talkers, shouters, the MG nest, the gun wave, path patrols, the interrogation officer. Extras send nothing. Accuracy scaling as on every map, no health scaling; generic cloner and end waves off | user-approved 2026-11-13 |
| Door use prompt | 'Press ACTION to Open / Close Door' | the mod's USE icon (hand) facing it within 140u; use toggles | user-approved (use icon) |
| Character animations (flanim, 2026-11-15) | the disc's own clips (emt_1_1.emt) | the scripted-scene clips retargeted onto the stock skeleton (fl_a<id>); stock bone lengths, fingers ride the hand (the disc animates them); everything else stock until decoded | gated off (flanimconv.OWN_ANIM) until the in-game sheets pass and the user approves |
| Scene clip timing | 15 poses per second, interpolated by the engine | the same poses at the same rate (frametime 1/15 s) | exact |
| Panzer IV model (flprops, 2026-11-16) | the disc's own Panzer IV: hull, turret, short 75 mm gun, hull MG, both tracks; its own destroyed set | the disc's meshes and textures (player's PC only) on the stock panzer_tank_europe (live tank), vehicle_panzer_iv_europe (parked copy) and Panzer_destroyed_lowpoly_base (wreck, the disc's destroyed hull, turret, gun and treads; its turret ring on the wreck's turret0, where the stock smoke rises); steel textures 4x with a fine CC0 painted-steel grain (ambientCG PaintedMetal005 + Metal016, colourless, the Balkenkreuze resampled only), road wheels and tracks 4x ESRGAN | user-approved 2026-11-16 ("Yes to sealed"; sheet SHEET_fl_panzer_ingame_v3) |
| Panzer scale | the disc's own size against its soldiers | 52u per disc metre, the converted soldiers' scale (the world converts at 48u per metre): tank and crew keep the disc's proportions, the tank stands about 8% larger against the buildings | choice (user-approved with the sheet) |
| Panzer tracks | animated (Tank_PIV_Tread01/02.mpk frames run while it drives) | the first frame, still: the stock tank's skeleton has no track-frame swap, so the treads do not crawl | forced (stock vehicle entity) |
| Panzer driving, aiming, firing | the original tank's own handling | the stock tank's, unchanged: drive and lean animations, turret turn and gun pitch speeds, collision box, sounds, muzzle effects; the gun's recoil is ours (9u back along the barrel, home in 0.25 s) since the stock recoil was built for the stock barrel | forced (stock gameplay entities kept) |
| Nest MG42 model (flprops, 2026-11-16) | the disc's tripod-mount MG42 (MG42GunTripod: no bipod, pivot in the receiver) | the disc's mesh and texture (player's PC only, texture 4x ESRGAN) on the stock statweapons/mg42_gun turret: its pistol grip sits in the stock gunner's hands, so the stock seat, clips and cone fit unchanged and the gun turns about a point ~31u ahead of the disc's own pivot; muzzle and ejection port from the disc. The hidden hull MG and the jeep's projectile-generator guns keep the stock tik (never seen) | OFF - user chose stock HD MG42, 2026-11-16: after the tower playtest (the disc texture is 128 px; its 4x upscale reads the same from the gunner's seat, SHEET_fl_tower_mg42_compare_v2) every nest gun is the stock turret with the mod's 2048 px texture |
| Health10 / Health50 pickups (flprops, 2026-11-16) | the disc's canteen (Health10) and medkit case (Health50) | the disc's meshes and textures on the stock item_25 / item_50_healthbox entities (pickup, amount, sound unchanged), larger than the stock boxes as on the disc (soldier scale 52u per metre: canteen ~19u tall, the medkit case ~22u standing on its edge); their soft drop-shadow cards kept, blended; textures 4x (ESRGAN, the red crosses resampled only) | user-approved 2026-11-16 |
| Health25 pickup model (flprops, 2026-11-17) | the disc's medkit case (seen in the original: rec 333, ref_xemu so_fx/health/h25_sheet.png) | the same disc medkit as Health50 on the stock item_25_healthbox entity (pickup, amount, sound unchanged), standing on its edge as on the disc | settled from the reference; under the approved health pickups (2026-11-16) |
| Field phone model (flprops, 2026-11-16) | the disc's field-phone case with its handset on the cord | the disc's mesh and textures (about 41 x 104u with the cord laid out) on the stock phone_squarebase entity, in place of the stock desk phone; leather with a fine CC0 grain (ambientCG Leather030), the dial and lettering resampled only | user-approved 2026-11-16 |
| Bridge Panzer wreck collision (2026-11-16, user playtest) | the burnt hull blocks as drawn | the wreck script_model carries the live tank's hull box (panzer_tank_europe setsize -134..134 x -74..74 x 0..78) instead of the destroyed model's own bounds (-171..212 x -107..104 x 0..102, blown parts included), which stopped bullets around and above it | fix (user: "an invisible wall above and around it you cant shoot thru") |
| Bush and hedge cards (2026-11-16, user playtest) | see-through foliage, walked through (ref_xemu walk s7) | the drawn-geometry slabs flsheets gave the bush (c6_150000) and hedge (174a80) cards next to dropped wrap sheets are taken out after the edge pass (fl_levels seethru_nocoll) | fix (user: "invisible walls or issues walking") |
| .30 cal gun wave pushes (2026-11-16) | recs 21 / 98 / 469 start as recorded (21 alert, 98 / 469 idle on patrol path 12, sight 40 m); 98 and 469 stand in a walled yard west of the square (its 7 path nodes an island) | each wave German, once in, presses on the gun with the mod's wave-push recipe (coop_push_toward to 450u of the gun, then attacks); 98 and 469 come in just outside the yard on connected ground out of the gun's view (5808,-2759 / 5329,-3178). Traced (ref_xemu TRACE_gun_wave.md): the original HOLDS - rec 469 shuffles ~180u closer and holds ~20 m off, rec 98 drifts away and holds ~25 m off, rec 21 walks in along the far street; by ~20 s the nearest German is ~980u from the gun; coop_flGunPush 0 = the disc behaviour | user request ("the enemies didn't push up when you get on the 30 cal") |
| Church-tower MG42 gunner (2026-11-16) | the tower gun (rec 384) is unmanned, the player's (objective 2) | from the bridge push (the Panzer's area starting) a German mans it (the mod's nest recipe, global/mg42_active.scr, reach 3000u so the bridge deck is covered); he appears unseen; once he is dead or off the gun a player mans it and objective 2 completes as before; coop_flTowerGunner 0 = none | user request ("put an enemy on the church tower mg42") |
| Bridge snipers (2026-11-16) | none | three German snipers from the bridge push: an upper-floor window west of the bridge (844,986) and two flat roofs (1596,1034 / 1052,-1270), each with a clear line to 5-6 of 6 bridge-deck points (offline, walls/sniperspots.py); the mod's alarm-sniper recipe (accuracy 55 + player-count scaling, crouched on roofs, arrival glint + shout, a repeating scope glint); unseen spawn; coop_flSnipers 0 = none | user request ("snipers overlooking the bridge" / "in buildings and roofs with sightlines to the bridge") |
| Coop officer at map load, in cover, ignored by the allies (2026-11-16) | none (2026-11-12: off) | the mod's officer spawns at map load (officer_positions.scr coop_officer_instant_spawn; the players start 3700u away) at the street's north-west corner by the road, behind his radio table and the building corner (4880,-3072; was 5607,-3378 mid-street): hidden from the jeep gun, seen from 31 of 785 east-street and 233 of 636 courtyard points (old spot 750 / 517). The allied AI ignore him (THREATBIAS_IGNOREME, fl_officer_ignore, the coop_ea_1_11 recipe) and only a PLAYER makes his first contact (officer.scr coop_officer_contactPlayers: an allied AI he fights is not contact, a sighting must hold 1 s) - so he lives until a player engages him and the waves come for the players; his bodyguards and waves are fair game; coop_flOfficer 0 = no officer | user request ("have the officer instantly spawn at map start", "the bots eliminated the officer almost immediately") |
| Jeep .30 cal belt (2026-11-16) | not limited in the decode or the traces (the 20 s mounted run shows no ammo count) | 150 rounds in total, one pool on the gun for every player, the engine's finite belt (coopammo): the HUD shows BELT n, at 0 it clicks dry; coop_flJeepAmmo n overrides (-1 unlimited) | user request ("Make that jeep 30 cal only have 150 rounds") |
| .30 cal road group, option C (2026-11-16) | the gun wave is the three recorded men (recs 21 / 98 / 469) | on the first player mounting the .30 cal (also when the wave came earlier), 4 more Germans (disc scaling: 4 x factor, at most 6) come in up the road north-west of the street (4308..4465, -2040..-2351), out of the gun's sight and every player's view, about a second apart, and push down the road onto the gun (coop_push_toward, fanned on the gun's west side, leash 4096) - in view along the street within ~10 s, 700u from the gun by 12 s; the recorded three are unchanged; coop_flGunRoad 0 = off | user request ("C is good have them come down the road") |
| .30 cal gun wave pushes - leash (2026-11-16) | (as the row above) | the push men get the wave recipe's leash (4096 + resetleash): at the default 512 the engine's attack think held rec 21 on the road for the whole wave (ofw1, ofw3, r2: never moved); with it he closes to ~380u | fix of the 2026-11-16 push |
| Bridge: the Panzer is the players' (2026-11-16) | the Stukas bomb the Panzer on the bridge (sequence sp_bomb / P47 rocket) | no Stuka strike on the tank: a respawning bazooka by the sandbags on our side (1360,-420; restocks 25 s after it is taken) and the players must kill the Panzer; 4 far-side defenders and 2-wave reinforcements (all spawned unseen), five sniper perches with shot-checked lines on the deck; the tower MG42 gunner respawns every few seconds until a player reaches the tank area | user request ("place a bazooka on our side of the bridge... we will have to destroy the tank ourselves... Needs to be tough to cross the bridge", "mg gunner should respawn every few seconds... as long as you havent made it to the tank") |
| Objective list: Secure the Bridge (2026-11-16) | the disc's objective 2 is the tower MG | a new objective 2 "Secure the Bridge" (marker 1250,1300) completes when a player reaches the tower radio trigger (conway_tower); the tower MG becomes objective 3; the list is 8 (drop, bridge, tower MG, defend, roster, wall, dock, crate) | user request |
| Defend the Bridge (2026-11-16) | none (the disc moves on after the tower MG) | after the tower MG: hold a 520u ring at the bridge (1300,-150) for 105 s while waves of 2 + players (at most 6) come from both far roads every 20 s; the clock pauses with "Return to the bridge!" while nobody is inside; allies are squishy (capped at 60 HP) for the hold; every wave man spawns out of every player's view (any of the four road entries, else skipped) | user request |
| Castro rescue as a secondary (2026-11-16) | the disc's optional rescue has no objective line | "Rescue Pvt Castro" on the Additional Objectives line 3 (coop_so3) when he is found, ticked on rescue, "- failed" if he dies; re-sent to players who join later | user-approved option (a) |
| Sealed Orders allies toned down (2026-11-16) | as the allied-strength row above (accuracy 18, AI-vs-AI x0.5) | on this map only: AI-vs-AI damage x0.3, ally accuracy 12 (level.coop_aiVsAiDmg / level.coop_discAllyAcc) | user request ("allies too OP") |
| Footsteps by surface (2026-11-16) | the disc's surface classes (code decode) | the converter writes the disc's surface class into the BSP surface flags (cliff-tagged faces included); its crunch class plays the dirt steps (these maps have no gravel alias; the stock gravel steps are the same sounds) | fix (from the code decode) |
| Edge skirts over drawn ground (2026-11-16, converter fix, bug-11345) | the dark-brick ground floors show their own green doors and windows | (was: the converter's drawn edge skirt also hung from upper-storey slab edges inside the house shells, 2u behind the facade, and filled those openings with a stretched plaster picture) a skirt is skipped where a drawn floor lies 40..500u under the edge: 114 of 392 skipped on 1_1; collision brushes, brushsides and every referenced plane byte-identical, geoaudit equal to v144 (75235 walkable, 0 void falls) | fix (user: "this looks funky") |
| Window glass (2026-11-17, converter flglass.py) | intact panes kept only as material-13 collision (one pane per flag word) and drawn by the game; broken panes drawn by the level's 1c0900 cards, one cell of that 2x3 texture each (emulator: a grid of panes with grey bars, the room faintly behind; ref_xemu so_fx/glass) | each intact pane drawn as one cell of the level's intact window texture 1be880 (frame bars + 69%-alpha glass), blended, lit by vertex colour: 197 panes on 1_1, 2 left to the 1c0900 cards; the 1c0900 cards (8 surfaces / 86 tris) byte-identical; collision unchanged (brushes and brushsides equal by shader name, the glass shader is non-solid); geoaudit equal to v145. Window-area mean 32/33/30 against the emulator's 36/36/34 (was 31 with no glass) | fix (was: every window showed straight through to the room) |
| Window glass is static (2026-11-17) | the panes do not break: three aimed pistol shots leave the Bazar window intact (glass_10..12) | no breakable glass added (no func_window, no break effect) | as the original |
| MG gunners off their gun (2026-11-17) | not in our traces (what a Frontline gunner carries once off his gun is not decoded) | a nest or tower gunner who comes off his gun - unarmed and over 100u from it, or the gun gone, for two checks - gets an MP40 (aihandler.scr coop_actorArm) and the ordinary cover think, so he fights on instead of standing unarmed (`gun "MG42"` leaves a mounted gunner no hand weapon; bug-11353's crate errors) | user request ("Give them an mp40") |
| Capsule step (2026-11-17, engine per-map rule) | Frontline's player is a capsule with no step-up routine (code decode: fl_player_move_notes.md): it rides over a sill under any ceiling its body fits and keeps a step onto a steep face; walkable slope 50 deg | worldspawn hzm_capsulestep 1 (HZM engine bg_slidemove PM_StepSlideMove): the highest step that fits under a low ceiling, and a step onto a steep face is kept; our 38u step stays (the conversion made the original's 20-34u bevels vertical lips). Jeep road / street / Castro: 11 steep-landing + 1 headroom refusals at the user's viewpos -> 0; original-track refusals 93 -> 45 (the rest are collision, not the step) | fix (user: low invisible walls you can jump) |
| Tunnel to the interrogation room (2026-11-17, converter flclear + fl_levels 1_1) | a crawl passage under 46-50u ceilings with rubble lips; Frontline's 38u crouch goes through (code decode) | crawl caps at floor+86 (were +60; still crouch-only under the 94u stand box), the rubble mound's edge that juts into the lane carved out of collision (x -1722..-1640, y 4687..4708, drawn rubble kept), and the tunnel's north end at the bend sealed (a prone player slid under a slab into the void). With the engine's capsule step (hzm_capsulestep) a crouched player now crawls through: replica of the user's install, stuck at (-1688,4716) -> through to (-2035,4709); either half alone still sticks | fix (user: stuck crouched in the tunnel of destroyed buildings, can't get into the hostage room) |
| Far-bank wave waits for the tower MG42 (2026-11-17) | trigger 31 (the tower's foot) starts group 65545 on the far bank | the group comes when the first player mounts the church-tower MG42 (coop_flFarGate 0 = the original's trigger); the far-bank defenders, reinforcements and snipers keep the crossing hard before it | user request ("wait until you get on the mg42 to spawn in the wave on their side of the bridge") |
| Tank area = at the tank (2026-11-17) | (our rule: the tower gunner respawns until the tank is reached) | 220u of the Panzer's halt point (was 450u: walking onto the bridge deck counted) | fix (user: the gunner stopped coming back) |
| Bridge sniper perches (2026-11-17) | none (2026-11-16: five perches incl. a chimney top) | five crouched far-side perches behind a roof ridge or sill (offline: cover 3-41u toward the bridge, 4-6 of 6 deck points seen from the crouched eye), accuracy 75 (was 55), glint kept | user request ("this sniper is barely doing anything" / "needs to be tough to cross the bridge") |
| Officer: no stolen fight (2026-11-17) | none (2026-11-16: officer ignored by the allies) | until a player makes contact the officer and his bodyguards take no damage and the allies ignore the guards too; a reinforcement call refused by the 45 s cooldown is made again when it is over (guards down or his HP falling, at most 3 more) | user request ("this officer battle was a bit too easy ... they had the drop on him") |
| Jeep squad hurt (2026-11-17) | the jeep's squad (group 65540) at full strength | they climb out of the wreck at 35 HP and hold near it (leash 300) until a player is past them | user request ("make the first jeep guys have really low HP since they wrecked the jeep") |
| Defend the Bridge: paradrop + enemies remaining (2026-11-17) | none (2026-11-16: a 105 s hold) | the hold shows on the HUD as PARATROOPERS INBOUND <s> (pauses outside the ring); at zero a friendly paradrop lands on our side (paradrop.scr), and the hold is done when they land; the attackers still up are left to them and the players (no counter) | user request ("until a paradrop comes in and drops more friendlies?", "I like holding ... until reinforcements arrive instead") |
