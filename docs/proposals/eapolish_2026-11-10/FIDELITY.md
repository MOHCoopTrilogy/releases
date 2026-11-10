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
| R5 | Gate to the graveyard opened by its dispatcher | gate mesh is a smart object (not converted): no gate | X |
| R6 | Collision blocker at the partisan leader (removed after his speech) | not placed (an invisible wall would break the zero-invisible-walls rule) | D |
| R7 | Bridge destroyed by the Germans (timer + effects package) | bridge mesh is a smart object (not converted) | X |

## Encounters

| # | item (original) | port | status |
|---|---|---|---|
| E1 | 90 spawn points; team from the character definition (73 German incl. officers and an SS commander, 17 Russian partisans incl. the leader and two women) | 86 placed (4 have no standing spot on the collision); team, weapon (MP40 / Gewehr 43 / PPSh) from the record | M (models: stock winter Wehrmacht / Soviet stand-ins, no female partisan model: D) |
| E2 | Spawn when the original's group is activated; count and alive-at-once from the record | same; never in a player's view (`ea_seen`, waits up to 60 s) | M |
| E3 | 20 groups present at load (start squad, garrisons) | same | M |
| E4 | Squads move to their SquadObjective points; later points ordered by triggers (e.g. the graveyard retreat) | first point on spawn, later points when their group fires (`ea_sq_move`) | M (cover/ambient behaviour inside a point: D, MOHAA AI) |
| E5 | Deaths feed counters (counter-attack waves, reinforcements) | death lists sent as in the record | M |
| E6 | 9 mounted MG points (2 in the church tower, 2 on the railgun towers ...) | MG42 turrets at the points, manned by the nearest German | M |
| E7 | 3 Panzer IVs, each death reported to the Panzer objective's counter | live winter Panzer IV VehicleTanks (t3l1 recipe) at the original's placements, wake when a player is within 3000u | M (they do not drive the original's paths: D) |
| E8 | Russian squad follows / fights | Barney follow when a player passes (Frontline polish recipe) | D |

## Scripted moments

| # | moment | port | status |
|---|---|---|---|
| S1 | Level start fade-in, then the primary objective | objective in the original order; fade not played | D |
| S2 | The railgun fires on the squad (camera shake, impacts, loops until the railgun area is reached) | gag loop with shake + distant impacts near the players, stopped by the original's dispatcher | M (impact fx are stock) |
| S3 | Railgun: 3 charges, counter, 8 s timer, destruction scene | same chain; stock 15 cm cannon stand-in turns into its wreck | D (railgun mesh not converted) |
| S4 | Comm tower, ammo dump: charge -> objective -> destruction | same chain; stock stand-ins removed in the blast | D (meshes) |
| S5 | Church: secure, German counter-attack with PA announcements, waves counted, end camera, end of level | same chain to the original's EndTheLevel | M (static end camera: D) |
| S6 | Nebelwerfer plunger | use point at the plunger fires its groups | M (rocket fx: X) |
| S7 | Ambient fires, smoke, birds, fog (effects packages) | not placed | X |

## Objectives, pickups, audio

| # | item | port | status |
|---|---|---|---|
| O1 | 6 objectives, disc text, shown in the order the original activates them (railgun first, then partisans, Panzers, ammo dump, tower, church) | same | M |
| P1 | 40 pickups: medkits, revive kits, stick grenades, bazookas, PPSh, Gewehr | at the original's points, appear when their group fires | M (revive kit -> health box: D) |
| A1 | Scripted lines (27 cues) | the disc's own subtitle at the right moment | D (voice: the cue -> speech-file link is not decoded) |
| A2 | Music: interactive score switched by 10 music triggers | 4 segments by our choice (ambient / action / church / end) | D |

## Geometry (byoaudit geoaudit, local pak)

Unchanged by this pass (collision identical before/after): 139,470 walkable cells, 1,966 blocked moves with nothing
drawn near (429 brushes, 661 clusters), 117 edge-of-world, 71 blocked openings, 462 floor cells with nothing drawn,
0 falls out of the world. Only 151 of the 1,966 sit within 200u of a smart-object placement, so most are not the
missing meshes; they need a look on screen before a converter rule is written (see README, open).

## Score (1 player)

Counted from the tables above: **Matched 17 - Deviated 13 - Missing 5** (of 35).
