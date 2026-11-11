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
| S6 | Nebelwerfer plunger | use point at the plunger fires its groups; the launch and impact packages play as the original's own particle systems, converted on the player's PC (see S7); one system of the launch (the muzzle glow) is not in the level's effect stream and is left out | M (one glow system absent) |
| S7 | Ambient fires, smoke, fog, birds (45 effects packages) | every package at its placement and with its placement's own turn (roof fires lie along their roof slope). Converter 0.7.x (`eafx.py`) reads the level's particle systems and writes each one as an emitter: emission rate and burst size, life, size and growth, start and end colour and alpha with their per-particle ranges, spawn box, velocity, acceleration, spin, blend mode, view-distance clip and fade. What the stock emitter cannot say goes through the engine's `convfx` emitter command (converted maps only). 30 packages become 39 emitter files and 46 sprite shaders. Units, re-checked against public footage of the level (0.7.2): the stored particle sizes are half extents, so every quad is twice as wide as 0.7.0 drew it - that was why smoke read as separate dots and flames as specks. Lifetimes are seconds, speeds metres per second and the emission tick 30 Hz; those agree with the footage and are unchanged. Width and height end scales are kept apart as a sprite aspect plus an area-preserving growth (approximation). Engine: converted systems are no longer thinned by the effect-detail setting or hidden by the leaf visibility test (about a third of the particles were being dropped). Checked against the footage: straw and roof fires are solid orange flame masses under continuous dark smoke; the burning tank and the smoke column are continuous; a medium fire is a soft flame mass of about a metre and a half; a small fire is either a flame of about a metre in a crater or, for the package with no flame layer, a smoking crater. Not carried: depth bias, the fog multiplier, noise (only six blast layers use it) and trails (only five spark and rocket layers use them) - no ambient fire, smoke or fog system uses either; acceleration stays in world space; four systems are not in the level's effect stream (a house fire, the nebelwerfer muzzle glow, a tombstone dust puff, one tank-explosion layer); birds not placed. The two ground-fog packages are drawn but are nearly the colour of the distance fog and hard to tell apart from it; the far-off fires beyond the village draw as lit plumes but their wide horizon glow is weaker than in the footage | M (listed parameters not carried) |
| S8 | Night sky and distance fog | the level's own global fog record: its colour, its near and far distances and its ceiling (the fog stops at 44 % and never hides the far scenery). Converter 0.7.3 writes `farplane_bias`, `farplane`, `farplane_color` and the engine extension `farplane_maxfog` (GL2 renderer only; not written into savegames), with far-plane culling off; a stock night sky stands in for the original's. The level's five weather areas are not ported; the snow itself is lit brighter than in the footage | P (weather areas, sky art, snow brightness) |

## Objectives, pickups, audio

| # | item | port | status |
|---|---|---|---|
| O1 | 6 objectives, disc text, shown in the order the original activates them (railgun first, then partisans, Panzers, ammo dump, tower, church) | same | M |
| P1 | 40 pickups: medkits, revive kits, stick grenades, bazookas, PPSh, Gewehr | at the original's points, appear when their group fires | M (revive kit -> health box: D) |
| A1 | Scripted lines (27 cues in the level's scenes; 61 voiced lines on the disc) | the original's own voice (UBER event -> str.ast stream, decoded on the player's PC) with its subtitle, at the original's moment; the scene waits for the line | M |
| A2 | Music: interactive score switched by 10 music triggers | the 10 triggers with their own volumes / groups and their own music EVENT (15-20, 35-37, 50); each event plays the section the score's own event table names (eamusic.py, read from the .mpf on the player's PC): intro samples in order, then the looping tail where the section loops (events 16 and 19), once and silent where it does not. Per the control file a cue event switches at once; here the old cue is faded over 1 s before the new one starts. The three stingers (35-37) play over, a cue that arrives while one plays is held until it ends (as the control file defers it), then the held or looping cue comes back | M (the score's state events 0-12 - fade-outs of 5 / 3 / 1 s, the held-cue return with a 2 s fade-in, the idle bed - are raised by the game program by rules that are not in the control file, so they are not driven; the control file has no cross-fade between cues - an earlier note here said 2-3 s) |

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

**Matched 25 - Deviated 1 - Missing 0** (of 26 rows).
Deviation: E8 the Russian squad's follow logic. S6/S7 now play the original's particle systems (converter 0.7.0 + engine `convfx`), with the uncarried parameters listed in the rows.

Verified 2026-11-10 on converter 0.7.0 with the convfx engine build (private install only):
- SP self-test walk (1 client): all 6 objectives, the mission end, 0 Script Errors, ~60 fps at 960x540; every music event in order (15-20, 36, 35, 50, 37, end) with the 1 s fade logged at each cue change.
- Co-op self-test on a private dedicated server with 1 client (the 2-client run was not repeated for this round - the changes are client-side drawing and music): all 6 objectives, the mission end, 0 Script Errors, all 109 Germans killed, 0 of 109 deferred spawns in view, 7 idle AI.
- Stills at 26 fixed views before and after (local, H:\hzm_work\eapolish\shots\fx_before, fx_after, fx_pairs_1.jpg, fx_pairs_2.jpg).
- Partisan barn: 12 stills from the barn floor and the cellar (local, shots\barn2). The cellar is crouch-only in the original's collision; from crouch height and from the barn floor nothing outside shows. The earlier still that showed the outside under the walls came from the self-test standing a player in the cellar, eye level with the floor planks. Nothing capped, nothing blocked.


Verified 2026-11-10 on converter 0.6.0 (the original's collision):
- 2-player co-op self-test (private dedicated server + 2 clients): all 6 objectives, the mission end, 0 Script
  Errors, 26 voice lines played, 5 idle AI, 0 of 109 deferred spawns in view; all 109 Germans killed (80 engaged,
  60 moved); 4 of 15 Russians killed, 12 joined the squad. The partisan leader's blocker went on at the start and
  off when the original's timer released it.
- SP camera walks (stills local, H:\hzm_work\eapolish\shots\tour3, tour4): fires and smoke, tower and railgun wrecks,
  ammo dump blast, gates opening, subtitles in order, the church defence.
On screen 2026-11-10 (stills local, H:\hzm_work\eapolish\shots\trig6, tank12): every one of the 87 volume triggers
marked at its corners from above (sizes and placements match the roads, doorways and yards they guard); Panzer 3
(invulnerable for that test only) drove all 4 of its legs to their ends on the roads - after two fixes: legs routed over
open ground (a straight leg ran it into a house) and a pivot to face each leg before driving it (MOHAA's autopilot
cannot start a leg facing back along it).
Not compared side by side with the original: trigger sizes are the original's numbers, not measured against EA play.
