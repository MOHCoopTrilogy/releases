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
| R1 | Player start in the north-west field (-5438 3191), squad around him | same. 2026-11-12: the three Russians added at the co-op start are off by default (`coop_eaStartSquad 1` brings them back); the original has none there. Start kit from the Player record (see follow-up). | D |
| R2 | Kit: PPSh, Gewehr 43, stick grenades; bazookas are pickups on the map | same kit, 6 bazooka pickups at the original's points | M |
| R3 | Route: start -> checkpoint -> partisan leader (west, -3500 -375) -> trenches / bridge / nebelwerfer (south-west) -> railgun (-941 -2463) -> village -> graveyard -> comm tower (4042 -2998) -> church (5140 -1935) | the same order emerges from the original's triggers in the self-test walk | M |
| R4 | 137 logic objects (volume triggers, gag triggers, dialogue triggers, dispatchers, counters, timers, 5 demolition charges, a plunger) | all interpreted; trigger volumes from the record (sphere radius / box half-extents, rotated) | M (box extents' unit inferred: D until checked on screen) |
| R5 | Gate to the graveyard opened by its dispatcher | the original's gate leaves (easob), each built around its hinge (the placement's origin) as a script_object: they swing open 100 deg in 2.5 s when the original's dispatcher fires | M (swing seen in the log; on camera pending) |
| R6 | Collision blocker at the partisan leader (removed after his speech) | the original's invisible blocker (InvisibleCollision3x3x0) at its placement, solid while its group is on, gone when the original's go-back timer deactivates it (seen in the co-op run) | M |
| R7 | Bridge destroyed by the Germans (timer + effects package) | the original's bridge mesh with collision; when its group fires: the effects package's blast, then the original's destroyed bridge mesh (SMA_WoodBridge6_D) | M (not reached in the walks: the original stops it if the player is quick) |

## Encounters

| # | item (original) | port | status |
|---|---|---|---|
| E1 | 90 spawn points; team from the character definition (73 German incl. officers and an SS commander, 17 Russian partisans incl. the leader and two women) | 86 placed (4 have no standing spot on the collision); team and weapon from the record (MP40 / PPSh; the German rifle is the Kar98k: MOHAA's AI has no G43 reload) 2026-11-11 (0.7.9): unchanged count; the dropped four are three off-map stubs and one MMG gunner (TAKE_IT_MMG_01, no standing spot). Headless walk: 124 of the original's 185 men spawned, 37 of 50 groups in full; the rest are wave refills and three groups whose trigger the stand-in never reached. | M (models: stock winter Wehrmacht / Soviet stand-ins, no female partisan model: D) |
| E2 | Spawn when the original's group is activated; count and alive-at-once from the record | same; never in a player's view (`ea_seen`, waits up to 60 s) | M |
| E3 | 20 groups present at load (start squad, garrisons) | same | M |
| E4 | Squads move to their SquadObjective points; later points ordered by triggers (e.g. the graveyard retreat) | first point on spawn, later points when their group fires (`ea_sq_move`), on 788 path nodes laid on the original's AI places (the map had none: no AI could move) 2026-11-11 (0.7.6-0.7.9): 2,771 nodes - every floor level (cellars, stairs, upper floors), a 40u pass near the AI places, and isolated node groups bridged or dropped; worldspawn `map_time` now changes with the map so the engine's cached .pth graph is rebuilt. Headless walk: 0 'couldn't find start node' (was ~220), 3 'end node' (was 324). | M (cover/ambient behaviour inside a point: D, MOHAA AI) |
| E5 | Deaths feed counters (counter-attack waves, reinforcements) | death lists sent as in the record | M |
| E6 | 9 mounted MG points (2 in the church tower, 2 on the railgun towers ...) | MG42 turrets at the points, manned by the nearest German | M |
| E7 | 3 Panzer IVs; each squad drives its SquadObjective legs; each death reported to the Panzer objective's counter | live winter Panzer IV VehicleTanks at the original's placements; their squad's legs as info_vehiclepoint paths (converter), driven when the original orders them (Panzer 1 and 2 hold; Panzer 3 drives 4 legs, 8,500u); our own wreck swap (destroyed base + turret) | M |
| E8 | Russian squad follows / fights | Barney follow when a player passes (Frontline polish recipe) 2026-11-11: the scattered squad goal is used only where a man fits, else the squad point. | D |

## Scripted moments

| # | moment | port | status |
|---|---|---|---|
| S1 | Level start fade-in, then the primary objective | the original's Start_Level gag: its fades (out, in) then the primary objective | M |
| S2 | The railgun fires on the squad (camera shake, impacts, loops until the railgun area is reached) | gag loop with shake + distant impacts near the players, stopped by the original's dispatcher 2026-11-11: officer.scr's artillery recipe - numbered lead-in sound at the railgun, whistle and hit sound at the impact, radius damage 200 / 300u (never within 420u of a Russian), no shell where there is no ground. | M (impact fx are stock) |
| S3 | Railgun: 3 charges, counter, 8 s timer, destruction scene | same chain on the original's railgun mesh; its explosion package plays and the original's destroyed railgun mesh replaces it 2026-11-11: each charge point has the stock pulsating explosive marker at the record's own height and a hold-USE hint (objx2.scr recipe); the use boxes are no longer solid. The railgun mesh is anchored on its own origin (0.7.6: parts were displaced) and has its own collision. Not yet seen on screen. | M (wreck shown in the camera walk) |
| S4 | Comm tower, ammo dump: charge -> objective -> destruction | same chain; the tower's own destroyed mesh replaces it, the ammo dump goes in its package's blast (it has no destroyed mesh in the original either) 2026-11-11: same marker / hold-USE at both charges; the tower mesh is anchored on its own origin (it floated). Not yet seen on screen. | M |
| S5 | Church: secure, German counter-attack with PA announcements, waves counted, end camera, end of level | same chain to the original's EndTheLevel | M (static end camera: D) |
| S6 | Nebelwerfer plunger | use point at the plunger fires its groups; the launch and impact packages play as the original's own particle systems, converted on the player's PC (see S7); one system of the launch (the muzzle glow) is not in the level's effect stream and is left out 2026-11-11: the plunger has the marker and hold-USE hint. | M (one glow system absent) |
| S7 | Ambient fires, smoke, fog, birds (45 effects packages) | every package at its placement and with its placement's own turn (roof fires lie along their roof slope). Converter 0.7.x (`eafx.py`) reads the level's particle systems and writes each one as an emitter: emission rate and burst size, life, size and growth, start and end colour and alpha with their per-particle ranges, spawn box, velocity, acceleration, spin, blend mode, view-distance clip and fade. What the stock emitter cannot say goes through the engine's `convfx` emitter command (converted maps only). 30 packages become 39 emitter files and 46 sprite shaders. Units, re-checked against public footage of the level (0.7.2): the stored particle sizes are half extents, so every quad is twice as wide as 0.7.0 drew it - that was why smoke read as separate dots and flames as specks. Lifetimes are seconds, speeds metres per second and the emission tick 30 Hz; those agree with the footage and are unchanged. Width and height end scales are kept apart as a sprite aspect plus an area-preserving growth (approximation). Engine: converted systems are no longer thinned by the effect-detail setting or hidden by the leaf visibility test (about a third of the particles were being dropped). Checked against the footage: straw and roof fires are solid orange flame masses under continuous dark smoke; the burning tank and the smoke column are continuous; a medium fire is a soft flame mass of about a metre and a half; a small fire is either a flame of about a metre in a crater or, for the package with no flame layer, a smoking crater. Not carried: depth bias, the fog multiplier, noise (only six blast layers use it) and trails (only five spark and rocket layers use them) - no ambient fire, smoke or fog system uses either; acceleration stays in world space; four systems are not in the level's effect stream (a house fire, the nebelwerfer muzzle glow, a tombstone dust puff, one tank-explosion layer); birds not placed. The two ground-fog packages are drawn but are nearly the colour of the distance fog and hard to tell apart from it; the far-off fires beyond the village draw as lit plumes but their wide horizon glow is weaker than in the footage | M (listed parameters not carried) |
| S8 | Night sky and distance fog | SUPERSEDED 2026-11-12 (see follow-up): fog is linear from 0 to opaque at 95 m and the sky is the level's own. Before: the level's own global fog record: its colour, its near and far distances and its ceiling (the fog stops at 44 % and never hides the far scenery). Converter 0.7.3 writes `farplane_bias`, `farplane`, `farplane_color` and the engine extension `farplane_maxfog` (GL2 renderer only; not written into savegames), with far-plane culling off; a stock night sky stands in for the original's. The level's five weather areas are not ported; the snow itself is lit brighter than in the footage 2026-11-11: the mod's own snow / blizzard weather is opted in (`level.coop_weatherTheme = "snow"`, the stock winter-map recipe); the level's five weather areas are still not ported, so nothing doubles. Off: `coop_weatherForce off` (this map), `coop_dynWeather 0` (all maps), `coop_wxExtreme 0` (no blizzards). | M (fog) / D (weather is a deliberate addition) |

## Objectives, pickups, audio

| # | item | port | status |
|---|---|---|---|
| O1 | 6 objectives, disc text, shown in the order the original activates them (railgun first, then partisans, Panzers, ammo dump, tower, church) | same | M |
| P1 | 40 pickups: medkits, revive kits, stick grenades, bazookas, PPSh, Gewehr | at the original's points, appear when their group fires 2026-11-11 headless: all 40 appear, incl. the 6 bazookas. | M (revive kit -> health box: D) |
| A1 | Scripted lines (27 cues in the level's scenes; 61 voiced lines on the disc) | the original's own voice (UBER event -> str.ast stream, decoded on the player's PC) with its subtitle, at the original's moment; the scene waits for the line | M |
| A2 | Music: interactive score switched by 10 music triggers | the 10 triggers with their own volumes / groups and their own music EVENT (15-20, 35-37, 50); each event plays the section the score's own event table names (eamusic.py, read from the .mpf on the player's PC): intro samples in order, then the looping tail where the section loops (events 16 and 19), once and silent where it does not. Per the control file a cue event switches at once; here the old cue is faded over 1 s before the new one starts. The three stingers (35-37) play over, a cue that arrives while one plays is held until it ends (as the control file defers it), then the held or looping cue comes back | M (the score's state events 0-12 - fade-outs of 5 / 3 / 1 s, the held-cue return with a 2 s fade-in, the idle bed - are raised by the game program by rules that are not in the control file, so they are not driven; the control file has no cross-fade between cues - an earlier note here said 2-3 s) |
| A3 | Ambience: the level's AmbienceTrigger zones with their loops | the zones' loops decoded on the player's PC (eapack.ambience) and played while a player is inside the zone (2 zones entered in the headless walk); loudness not heard yet | M |

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

Converter 0.7.9 (2026-11-11, playtest fixes), same audit: invisible contacts 1,055 (1,010 on the edge of the
playable area as in the original, 40 one-way in 21 places, 5 two-way), 2 of them on the railgun's own collision
(ours); walkable cells 138,322; must-crouch cells 2,036; falls out of the world 0; floor cells with nothing drawn
under them 456. Changes: smart-object meshes anchored on their own origin (walls, railgun, tower), headroom relief
(459 collision triangles that hang 78u+ over a floor lifted to 98u: the original's soldier is shorter than
MOHAA's 94u hull, which made door headers and stair soffits one-sided walls), no solid use boxes at the six
charge sites, the cellar blocker solid only while its group is on.

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

**Matched 24 - Deviated 3 - Missing 0** (of 27 rows).
Deviations: E8 the Russian squad's follow logic; S8 the mod's snow weather (deliberate, 2026-11-11; the original authors no weather on the played area); R1 start squad now off by default. S6/S7 now play the original's particle systems (converter 0.7.0 + engine `convfx`), with the uncarried parameters listed in the rows.

Verified 2026-11-10 on converter 0.7.0 with the convfx engine build (private install only):
- SP self-test walk (1 client): all 6 objectives, the mission end, 0 Script Errors, ~60 fps at 960x540; every music event in order (15-20, 36, 35, 50, 37, end) with the 1 s fade logged at each cue change.
- Co-op self-test on a private dedicated server with 1 client (the 2-client run was not repeated for this round - the changes are client-side drawing and music): all 6 objectives, the mission end, 0 Script Errors, all 109 Germans killed, 0 of 109 deferred spawns in view, 7 idle AI.
- Stills at 26 fixed views before and after (local, H:\hzm_work\eapolish\shots\fx_before, fx_after, fx_pairs_1.jpg, fx_pairs_2.jpg).
- Partisan barn: 12 stills from the barn floor and the cellar (local, shots\barn2). The cellar was crouch-only for MOHAA's taller hull (standing since the 0.7.7 headroom relief); from crouch height and from the barn floor nothing outside shows. The earlier still that showed the outside under the walls came from the self-test standing a player in the cellar, eye level with the floor planks. Nothing capped, nothing blocked.


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

## 2026-11-11 playtest follow-up (converter 0.7.10 to 0.7.17, checked 2026-11-12)

Basis: headless dedicated walks with a stand-in player (dev only), offline audits, and the original-game traces kept
locally. No visible client run is recorded here; what is unseen on screen is said so.

- Spawns: actors are force-activated when made (the engine leaves an actor far from every player unthinking for 60 s,
  which starved the groups). MaxAlive is record word 50. Census on the walk: 160 of 189 men made, 0 left waiting.
- ICS points (0.7.16): a point with an actor group relays its slot-1 Activate list when its actor is in place. The
  opening now shows "Locate Partisan Fighters" and spawns the second leader and three idle partisans together, as the
  original does. The exact moment is inferred; slots 2 and later are not decoded.
- Start kit from the Player record: PPSh 142 rounds (stock clip 70, original 71), rifle 30 (original 20; the stock
  weapon cannot start lower), 4 grenades.
- MG teams: gun squads from the records' own links, gun raised to its floor, gunner spot tested, yaw corrected,
  gunner seated on arrival (bunker.scr recipe). Stock MG42 stands in for the original's gun.
- Artillery: only the disc's gag timing, effect and sound; landing shells with damage are an extra, off by default
  (`coop_eaShells 1`).
- Fog and sky (0.7.17), from the original's GPU state at the opening: fog colour 50,56,63, linear from 0 to opaque at
  95 m (record words 26 and 28; words 27 and 29 are not decoded; `EA_FOG_CEIL=1` at conversion restores the old
  reading). The sky box is built from the level's own five sky textures and moon (`easky.py`) at 0.75 brightness; the
  skirt below the horizon is a flat fill and the two alpha cloud layers are not reproduced. Seen on screen
  2026-11-12 (0.7.19): the sky shader carries a no-op stage with `nofog` so the engine's sky fog leaves it alone
  (0.7.18; without it the whole sky was fog colour), and the -x / +y images are written under the names the
  engine's side order expects (0.7.19; before, hard seams). Moon on +x; its uv orientation is assumed.
- World light: vertex colours are divided by 2.83, the engine's map-load gain at the mod's pinned settings
  (2^(2-0) x 0.71). By formula, not measured against a reference still.
- Headroom relief (0.7.10/0.7.11): only where the taller MOHAA player cannot pass the original's opening.
- Path nodes (0.7.15): bridge rounds join the church and other groups to the main graph (2326 of 3011 nodes).
- Test code (stand-in walk, probes, watch lines) runs only with `coop_dev 1`.
- Still open (see the next section for the scenes): squad-objective completion sends are not implemented
  (Ruins_SQ01 spawns at load), 6 of 8 objectives are tracked. Full list: the local content audit.

## 2026-11-12 tanks, spawn groups, guns, loudspeakers, leader scenes (converter 0.7.18 to 0.7.21)

Basis: headless dedicated walks (a stand-in player, dev only; one walk with a dev drain that kills the Germans so
refill waves can be counted), one visible bazooka run on a muted client, offline reads of the disc records. Sound is
proven by log lines only; loudness and range are unheard. The emulator trace of the original could not be run this
round, so nothing below is compared against an original frame.

Tanks
- A script-spawned tank is moved 75u forward by the engine in its second frame. The script sets the record point
  again 0.2 s later and the tank then stays on it. Height and roll are the engine's ground fit: tank 1 straddles a
  trench lip, tank 2 stands in the ruined house and cuts its low wall. The disc holds no other placement data for
  them (position and a flat rotation only: no rest node, path or ground offset). Unverified against the original.
- Health is 700 for each tank, the figure in the disc's tank sheet (it was a random 400, 800 or 1200). The original's
  rocket damage is not decoded; at the stock 200 a hit a tank takes 4 hits. Unverified.
- The bazooka route works: the level's own bazooka pickup, rockets take 200 a hit, all three tanks destroyed in the
  visible run. The third kill now shows "Tank 3 of 3 Destroyed" like the first two (the count check skipped it).

Spawn groups (the 160 of 189 census)
- Six groups came up short: g291102 (village squads, 12 of 13), g291108 (graveyard squads, 9 of 24), g2e14eb
  (GermanWave2_1, 3 of 9), g2e14ec (GermanWave2_2, 0 of 3), g2e1536 (GermanWave3_1_02, 1 of 4), g2a11c7
  (Take_Right_SideHill, 2 of 3).
- Five of them are refill waves: the record caps how many are alive at once, and the next man comes only when one
  dies. Nobody died in the unattended walk, and the level's own turn-off triggers then switched the points off. With
  the Germans killed as they come (dev drain) every one fills: 189 of 189, no group short. No change to the build.
- g2e14ec was a real fault: the level sends Activate to a point it had switched off earlier, and the script did not
  switch it back on. Fixed; the group now spawns in every walk.
- Spawns still happen only out of the players' sight.

Machine guns
- The squad that mans a gun is now read from the records: a squad objective with the StayOnMMG tactic at the gun
  (guns 1, 2, 4, 5, 6, 7, 8; gun 4 is an allied squad, the partisan woman, from her second objective on). Guns 3 and
  9 have no such objective and take the squad whose first objective is nearest (73u and 146u): an inference.
- A called man who stalls within 320u of his gun, unseen by every player, is placed at it (stock pathing stops
  short of the nest). Seen or farther away he goes back to his squad and is called again after 20 s.
- Walks: guns 1, 2, 3, 5, 6, 7, 8 and 9 were manned. Gun 4 called its partisan; she was not seen to arrive.

Loudspeakers
- The PA announcement plays from the loudspeaker point the level has switched on, not on every player: the point by
  the comm tower from the start, the church point once the gate sequence switches it on (the tower point is switched
  off when the tower is destroyed).
- The church point's own sound (a 4.0 s speech stream in the level's sound bank) is decoded and plays from the point
  when it is switched on. Whether it repeats is not decoded: it plays once. The tower point's own sound is a bank
  sample with two variants and is not decoded.

Scripted character scenes
- Decoded: each scene's cue events (frame at 30 a second plus the cue name's CRC, stored ahead of the rig's animation
  name) and the scene record's listen group, actor group and target lists. Not decoded: the skeleton animation, the
  non-voice events, whether the done-sends fire at the start or the end, and what the original does with a Play that
  arrives while the actor is in another scene.
- Stand-in for four scenes: the scene's own actor goes to the scene point, faces the nearest player and speaks the
  cue lines at their own times, heard from him, in a stock pose. Partisan leader: "American, over here" and "waiting
  downstairs" (0.00 and 1.90 s), the plan speech (four lines at 0.17, 12.00, 15.73 and 19.43 s), "back to the front
  lines" (0.03 s, each time the go-back trigger fires; a Play during another of his scenes waits 6 s, then is
  dropped). The partisan woman: "come with me" at 0.83 s.
- Two leader lines (10258 and 10259a) are in the audio bank but no record, sequence or scene event in the level
  refers to them. They are not played. Whether the original ever plays them is unverified.
- The other 27 scenes do not play.

### User decisions 2026-11-12 (Their Dying Breath)

- Invented "Charge set - get clear!" line: removed (the disc has no line there).
- Co-op start kit: kept, approved deviation.
- Tank health: the original's figure. The disc has both halves: the Panzer IV sheet (hitPointThreshold 700) and
  the M1 Bazooka's rocket sheet next to it (Damage 550, blast radius 6), so the original destroys a Panzer with 2
  rockets. The stock rocket lands 200 a direct hit, so the tanks carry 700 in that scale (255): the same 2 rockets.
  Headless dev kill test (coop_eatest 14, overlay v37): each tank destroyed by its 2nd hit, all three counter
  lines, 0 Script Errors. Splash hits and misses on a client are the stock rocket's (not compared).
- Snowfall: stays on, approved deviation. Open: it did not show on the client last round.
- Display: converted disc missions get a neutral display chain; the per-map switch is being defined in the Sealed
  Orders work and will be reused here, not rebuilt.
- Order of work from here: scripted scenes and voiced lines first; sky, fog, light and tank seating last.
