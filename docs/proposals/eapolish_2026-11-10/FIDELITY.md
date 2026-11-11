# THEIR DYING BREATH (coop_ea_1_11) - fidelity checklist against European Assault 1_11

Authority: the original level's own object database on the player's disc, decoded by `docs/tools/ea/eadb.py` and
written out by `docs/tools/ea/eafidelity.py` into a LOCAL reference (`H:\hzm_work\eapolish\fidelity\fidelity_1_11.{json,md}`,
never committed). This file holds only our paraphrase, our MOHAA coordinates and the status of each item; it quotes no
EA text and carries no EA audio. 1 player = the original; coop scaling sits on top.

Status: **M** matched, **D** deviation (closest MOHAA equivalent, reason given), **X** missing (still to do).

## How the port follows the original

The original level is a message graph: 1,087 records; triggers, timers, counters and dispatchers send
activate / deactivate / objective-succeeded / play messages to activation groups, and squads, spawn points, pickups,
props, tanks, objectives and other logic objects that belong to a group react; scripted scenes are ordered action
lists ("gags"). Converter 0.3.0 (`eavm.py`) writes that graph into the local data script; `maps/coop_ea_1_11.scr`
interprets it. Route, encounters, their order, objectives and the end come from the disc, not from hand placement.
Before this, the names were read wrongly (bug-eap-dbnames): the player started in the church (the original's LAST
area) and the props stood at the wrong places.

## Route and gating

| # | item (original) | port | status |
|---|---|---|---|
| R1 | Player start in the north-west field (-5438 3191), squad around him | same | M |
| R2 | Kit: PPSh, Gewehr 43, stick grenades; bazookas are pickups on the map | same kit, 6 bazooka pickups at the original's points | M |
| R3 | Route: start -> checkpoint -> partisan leader (west, -3500 -375) -> trenches / bridge / nebelwerfer (south-west) -> railgun (-941 -2463) -> village -> graveyard -> comm tower (4042 -2998) -> church (5140 -1935) | the same order emerges from the original's triggers in the self-test walk | M |
| R4 | 137 logic objects (volume triggers, gag triggers, dialogue triggers, dispatchers, counters, timers, 5 demolition charges, a plunger) | all interpreted; trigger volumes from the record (sphere radius / box half-extents, rotated) | M (box extents' unit inferred: D until checked on screen) |
| R5 | Gate to the graveyard opened by its dispatcher | the original's gate leaves (easob), each built around its hinge (the placement's origin) as a script_object: they swing open 100 deg in 2.5 s when the original's dispatcher fires | M (swing seen in the log; on camera pending) |
| R6 | Collision blocker at the partisan leader (removed after his speech) | not placed (an invisible wall would break the zero-invisible-walls rule) | D |
| R7 | Bridge destroyed by the Germans (timer + effects package) | the original's bridge mesh with collision; when its group fires: the effects package's blast, then the original's destroyed bridge mesh (SMA_WoodBridge6_D) | M (not reached in the walks: the original stops it if the player is quick) |

## Encounters

| # | item (original) | port | status |
|---|---|---|---|
| E1 | 90 spawn points; team from the character definition (73 German incl. officers and an SS commander, 17 Russian partisans incl. the leader and two women) | 86 placed (4 have no standing spot on the collision); team and weapon from the record (MP40 / PPSh; the German rifle is the Kar98k: MOHAA's AI has no G43 reload) | M (models: stock winter Wehrmacht / Soviet stand-ins, no female partisan model: D) |
| E2 | Spawn when the original's group is activated; count and alive-at-once from the record | same; never in a player's view (`ea_seen`, waits up to 60 s) | M |
| E3 | 20 groups present at load (start squad, garrisons) | same | M |
| E4 | Squads move to their SquadObjective points; later points ordered by triggers (e.g. the graveyard retreat) | first point on spawn, later points when their group fires (`ea_sq_move`), on 788 path nodes laid on the original's AI places (the map had none: no AI could move) | M (cover/ambient behaviour inside a point: D, MOHAA AI) |
| E5 | Deaths feed counters (counter-attack waves, reinforcements) | death lists sent as in the record | M |
| E6 | 9 mounted MG points (2 in the church tower, 2 on the railgun towers ...) | MG42 turrets at the points, manned by the nearest German | M |
| E7 | 3 Panzer IVs; each squad drives its SquadObjective legs; each death reported to the Panzer objective's counter | live winter Panzer IV VehicleTanks at the original's placements; their squad's legs as info_vehiclepoint paths (converter), driven when the original orders them (Panzer 1 and 2 hold; Panzer 3 drives 4 legs, 8,500u); our own wreck swap (destroyed base + turret) | M |
| E8 | Russian squad follows / fights | Barney follow when a player passes (Frontline polish recipe) | D |

## Scripted moments

| # | moment | port | status |
|---|---|---|---|
| S1 | Level start fade-in, then the primary objective | the original's Start_Level gag: its fades (out, in) then the primary objective | M |
| S2 | The railgun fires on the squad (camera shake, impacts, loops until the railgun area is reached) | gag loop with shake + distant impacts near the players, stopped by the original's dispatcher | M (impact fx are stock) |
| S3 | Railgun: 3 charges, counter, 8 s timer, destruction scene | same chain on the original's railgun mesh; its explosion package plays and the original's destroyed railgun mesh replaces it | M (wreck shown in the camera walk) |
| S4 | Comm tower, ammo dump: charge -> objective -> destruction | same chain; the tower's own destroyed mesh replaces it, the ammo dump goes in its package's blast (it has no destroyed mesh in the original either) | M |
| S5 | Church: secure, German counter-attack with PA announcements, waves counted, end camera, end of level | same chain to the original's EndTheLevel | M (static end camera: D) |
| S6 | Nebelwerfer plunger | use point at the plunger fires its groups; the original's nebelwerfer packages play as stock snow-blast emitters | D (stock rocket effects) |
| S7 | Ambient fires, smoke, fog, birds (45 effects packages) | every package at its placement: fires (19) burn from the start as stock fire emitters with fire sounds, smoke and fog linger, blasts play when their group fires; birds not placed | D (EA particle systems mapped to the closest stock emitters; engine particle import not written) |

## Objectives, pickups, audio

| # | item | port | status |
|---|---|---|---|
| O1 | 6 objectives, disc text, shown in the order the original activates them (railgun first, then partisans, Panzers, ammo dump, tower, church) | same | M |
| P1 | 40 pickups: medkits, revive kits, stick grenades, bazookas, PPSh, Gewehr | at the original's points, appear when their group fires | M (revive kit -> health box: D) |
| A1 | Scripted lines (27 cues) | the disc's own subtitle at the right moment | D (voice: the cue -> speech-file link is not decoded) |
| A2 | Music: interactive score switched by 10 music triggers | the 10 triggers with their own volumes / groups and their own music EVENT (15-20, 35-37, 50); each event plays the score's segment of that number, converted on the player's PC | D (the .mpf event -> segment chain is not decoded) |

## Geometry (byoaudit geoaudit, local pak)

| measure | 0.3.0 (names fixed) | 0.4.0 + smart objects | 0.4.0 + clip sheets | 0.5.0 (clip_keep 38) |
|---|---:|---:|---:|---:|
| blocked moves with nothing drawn within 8u | 1,966 | 1,059 | 602 | 579 |
| - of which thin drawn obstacles (ea_geothin: rays to 40u at 28-60u height) | - | - | - | 460 |
| - truly invisible | - | - | - | 119 (41 clusters) |
| invisible brushes | 429 | 258 | 198 | 184 |
| falls out of the world | 0 | 0 | 2 | 0 |
| edge of world | 117 | 56 | 99 | 99 |
| floor cells with nothing drawn under them | 462 | 421 | 670 | 562 |
| walkable cells | 139,470 | 136,362 | 140,778 | 139,747 |

The 35 smart-object placements (railgun, tower, ammo dump, bridge, 2 gates, 18 tombstones/crosses, crates, building
corners) are the original's meshes now, with collision on what is drawn. Floating clip sheets standing in front of
drawn geometry are dropped (403) and that geometry collides instead (flsheets, the Frontline polish rule); level-edge
sheets stay (155) and are drawn as a barbed-wire edge, as are the flcliff edge walls. A look at the 8 biggest remaining
invisible clusters on screen: barbed-wire runs, Czech hedgehogs, dragon's teeth, rails and house debris - thin drawn
obstacles the 8u test does not see; the 2 remaining void falls are one spot on the west edge (open).

## Score (1 player)

**Matched 20 - Deviated 6 - Missing 0** (of 26 rows; several M rows carry a minor note in the row).
Deviations: R6 the partisan leader's invisible blocker (left out: it is an invisible wall), E8 the Russian squad's
follow logic, S6/S7 EA particle systems as stock emitters, A1 voices (subtitles only: the dialogue -> speech-file hash
is still unknown), A2 music events mapped to segments by number.

Verified headless 2026-11-10 (converter 0.4.0 run, before round 3): the whole mission in the original's order to its
own end, 0 Script Errors. Round 3 (converter 0.5.0) on camera (SP walk, stills local in H:\hzm_work\eapolish\shots\tour2):
partisans, burning village (stock fires + smoke columns at the original's 19 fire placements), tower destroyed and its
wreck shown, ammo dump blast, railgun destroyed and its wreck shown, gates opened, subtitles in sequence. Not yet on
camera: the church defence (the walk stood on a z-0 music trigger off the map - fixed, not re-run), trigger box
sizes, a Panzer driving (the walk knocked Panzer 3 out as it started).
