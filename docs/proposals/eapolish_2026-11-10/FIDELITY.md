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
| R6 | Collision blocker at the partisan leader (removed after his speech) | the original's invisible blocker (InvisibleCollision3x3x0) at its placement, solid while its group is on, gone when the original's go-back timer deactivates it (seen in the co-op run) | M |
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
| A1 | Scripted lines (27 cues in the level's scenes; 61 voiced lines on the disc) | the original's own voice (UBER event -> str.ast stream, decoded on the player's PC) with its subtitle, at the original's moment; the scene waits for the line | M |
| A2 | Music: interactive score switched by 10 music triggers | the 10 triggers with their own volumes / groups and their own music EVENT (15-20, 35-37, 50); each event plays the score's segment of that number, converted on the player's PC | D (the .mpf event -> segment chain is not decoded) |

## Geometry and progression (local pak; basis since 2026-11-10: the ORIGINAL's collision)

User rule: invisible walls are fine where the original European Assault has them (1:1 is the bar); the concern is
invisible walls that block progression, and blockers our conversion created. So the converter keeps the level's .cdb
collision exactly as it is (the clip-sheet rebuild and its barbed wire are opt-in, EA_SHEETS=1, and off), and the audit
splits invisible contacts by the collision that makes them (each brush names its source):

| measure | converter 0.6.0 (sheet rebuild) | 0.6.0, original collision, own-collision smart objects |
|---|---:|---:|
| invisible contacts on the ORIGINAL's own collision (as in EA - fine) | 422 incl. ours | 1,057 (575 on routes) |
| invisible contacts EXTRA vs the original (ours: target 0) | n/a | 0 (was 5: the railgun's collision doubled) |
| falls out of the world | 0 | 0 |
| floor cells with nothing drawn under them | 481 | 459 |
| walkable cells | 143,292 | 139,532 |

**Progression walk** (docs/tools/ea/ea_progwalk.py): from the original's player start, stand hull then crouch, every
trigger and use point the co-op mission run fired, in that order: 90 points, from the start road and the checkpoint,
the partisan cellar, the railgun ridge and its charges, the village, the graveyard and its gate, the crypts and the
comm tower, the church square (the Nemesis squad), back across the bridge to the Nebelwerfer hill. 86 reached
standing, 4 only crouched (the partisan cellar's two triggers, one at the church square, one by the haystacks), 0
blocked. SoundDialogueTrigger02 (6555 -2003) is not on the walk: it is centred 500u past the end of the level's
floor (no floor east of x 6050) with a 537u sphere, so in the original's identical geometry no player reaches it
either; the church defence it would start comes from the original's other path (the counter on the Nemesis squad's
deaths). The co-op run proved that: the trigger was skipped and the church defence still started. **Progression
blocks: 0.**

## Score (1 player)

**Matched 22 - Deviated 4 - Missing 0** (of 26 rows).
Deviations: E8 the Russian squad's follow logic, S6/S7 EA particle systems as stock emitters, A2 music events mapped to
segments by number.

Verified 2026-11-10 on converter 0.6.0 (the original's collision):
- 2-player co-op self-test (private dedicated server + 2 clients): all 6 objectives, the mission end, 0 Script
  Errors, 26 voice lines played, 5 idle AI, 0 of 109 deferred spawns in view; all 109 Germans killed (80 engaged,
  60 moved); 4 of 15 Russians killed, 12 joined the squad. The partisan leader's blocker went on at the start and
  off when the original's timer released it.
- SP camera walks (stills local, H:\hzm_work\eapolish\shots\tour3, tour4): fires and smoke, tower and railgun wrecks,
  ammo dump blast, gates opening, subtitles in order, the church defence.
Not verified on screen: trigger box sizes against the original, a Panzer driving its whole path.
