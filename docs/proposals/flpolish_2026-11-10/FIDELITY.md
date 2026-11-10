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
| R7 | Player-clip boundaries (special surface, 2131 tris) along the route edges | kept as clip | M |
| R8 | Trees/posts wrapped in tall clip columns | columns shrunk to the drawn trunk/post; 6 with nothing drawn dropped | D (snag fix) |
| R9 | Level edges: no floor past them | clip wall + drawn skirt + ground under the level (no void) | D |
| R10 | 19-34u lips walked over (Frontline step height ~0.7 m) | MOHAA STEPSIZE 18: lips stay steps (ramp pass built, off: it opened wall tops) | X |
| R11 | Gaps narrower than the MOHAA box (30u) but wider than Frontline's (~20u) on the AI routes: 28 | not widened | X |
| R12 | Door (DoorSwingCW, -1891 -2748) opened by its group | drawn closed geometry, no door entity | X |

## Encounters (group -> trigger -> members)

All 41 trigger-driven groups now spawn when a living player reaches the original trigger (radius from the record),
out of every player's sight (`fl_spawn_hidden`, 0 of 65 spawned in view in the audit run). Counts and teams are the
record's own (team byte, word 13); the class-name rule had made 4 Allied roamers German.

| # | where (MOHAA) | trigger | original | port | status |
|---|---|---|---|---|---|
| E1 | north lane allies (7774 3688) | proximity 3024u | 3 GIs + 1 German, alert | same, GIs join the squad when a player passes | M (+ squad follow, D) |
| E2 | jeep wreck (6352 3965 ..) | road 7536 3360 | 3 GIs, 3 Germans, crates, barrels | same | M |
| E3 | road shouters (5092 3358) | 384u | 3 Germans (planes / incoming / get out of the open) | spawned; their bark lines (VocBnk) not played | D |
| E4 | town gate (2825 1599) | 307u | 4 GIs, 2 Germans | same | M |
| E5 | tank square (2172 1539) | 528u | Panzer IV + 3 GIs | tank static, GIs spawn | D (tank does not drive path 66) |
| E6 | square south (1357 1224) | 374u | 5 Germans incl. "they're after the tanks" | same, bark not played | D |
| E7 | west street (823 542 / 740 -735) | proximity | 2 Germans | same | M |
| E8 | phone post (1335 -401) | 461u | dead GI + field phone | both placed at load | M |
| E9 | hangout (1717 -2010) / (771 -1977) | 355u / 230u | 3 + 2 talkers | same | M |
| E10 | upper floor (1126 -2156) / proximity 1133u | 283u | 8 Germans incl. 2 path walkers, 2 GIs | same; path walkers stand | D (no patrol paths) |
| E11 | MG post (1123 -2271) | 154u | mounted MG | MG42 turret, manned by nearest nest gunner | M |
| E12 | door house (-15 -2897) | 230u | 2 Germans + door | Germans spawn; door X | D |
| E13 | interrogation (-2114 -4427) | 461u | officer + Castro + clipboard | interrogation scene (ours, optional rescue) | D (rescue is ours, user request) |
| E14 | MG nest (-2549 -4759) | 461u | 3 nest crew, MG, molotov barrel, wall charge | crew + MG42 + barrels; molotov barrel X | D |
| E15 | docks (-5144 -3783), (-6705 -6205) | 461u / 2918u | 5 + 2 Germans | same | M |
| E16 | 4 ambushers on a death event | death of a group member | spawned at load (no death trigger) | D |

## Scripted moments

| # | moment | original | port | status |
|---|---|---|---|---|
| S1 | Jeep run | trigger 77 (7665 4380): jeep (driver, passenger, gunner) down the road west, hits the mine at the bend (6782 3356), flips, stops wrecked in the arch | Frontline's own 229 motion keys from key 20 (keys 1-19 run behind the gate where no one can see; started there the entity was never drawn), crew seated, mine blast, 2 killed, survivor joins | M |
| S2 | Jeep wheels flying off (4 tyre motion files) | 4 wheels | no MOHAA wheel model | X |
| S3 | Air: 7 fly-throughs (P47 fly-by, dogfight, strafe, rocket the tank, bomb the building, circling, Stuka) | 7 triggers | one P-47 run over the tank (coop aircraft recipe) | D |
| S4 | Bombs hitting the ground (2) and falling building parts (2) | triggers 423, 86 | not played | X |
| S5 | Rockets fired from the square (2) | trigger 255 | not played | X |
| S6 | U-boat bobbing at the dock (AnimMoveMechLoop, its own mesh) | trigger 11 | mesh not converted | X |
| S7 | Wall breach to the dock (M1_1_WallExplosion) | objective | use + explosion | M |
| S8 | Land mines (4) | step on | radius damage | M |

## Objectives, pickups, audio

| # | item | original | port | status |
|---|---|---|---|---|
| O1-O5 | 5 objectives, text from the disc | same order and text | | M |
| P1 | health 10/25/50 (18/7/5) | stock 25/50 health boxes | D (no 10 box) |
| P2 | ammo: grenade 11, pistol 9, rifle 8 | stock ammo boxes at the same 28 points | M |
| P3 | Colt / Garand / grenades at the start | coop loadout instead | D |
| A1 | ScrBnk dialogue: interrogation, dock, tower, nest, panzer | played at the matching spots | M |
| A2 | "mg_hurt" line (wounded gunner) | decoded, never played | X |
| A3 | Music: ambient, action after the roster, end sting; PathFinder triggers switch segments | ambient/action/end only | D |

## Score (1 player)

Matched 22 - Deviated 19 - Missing 9 (of 50). The deviations at R4/R5/R8/R9 are deliberate MOHAA-body fits; S1 is
the original scene. Next for 1:1: tank path 66 and the patrol walkers (paths 2, 151 are in the reference), the six
missing air passes and bombs, the door, the shouters' barks, wheels, U-boat mesh.
