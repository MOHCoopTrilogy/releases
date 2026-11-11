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
