# flpolish - SEALED ORDERS (coop_fl_1_1) polish, 2026-11-10

User playtest: snags, the jeep scene missing, open floors, broken tree billboards, idle AI / AI that never fight,
floating props, invisible walls blocking progression, crawl holes you cannot crouch through. Everything here is
our code; converted output, stills and logs stay under `H:\hzm_work\flpolish` (never committed).

## Root causes (converter: docs/tools/frontline)

| symptom | cause | fix |
|---|---|---|
| invisible walls blocking progression | .cdb flag bit 22 + material 14 = 450u trigger volumes, converted solid | `flconvert.coll_is_volume` drops them (and from placement grid / vis occluders) |
| crawl holes need prone | FL crouch ~49u vs MOHAA 54u; doorways ~86u vs 94u | `flclear.py` headroom carving, passage + inside-wall filters, nodraw caps |
| snag on trees / posts | special-surface columns fatter than the drawn trunk, some with nothing drawn | `flfit.py` fits each column to the drawn geometry |
| see-through trees | soft-edged canopy textures drawn blended | foliage cutout rule in `tex_shader` |
| open floors / underside | floors end at cell edges with nothing beyond | `flcliff.py` clip + drawn skirt + ground under the level |
| jeep scene missing | static jeep only | `flscene.py` decodes the .mvd keys (mirrored quaternion handedness) -> `fl_jeep_run` |
| AI idle / not fighting | all 75 placements spawned at load; 4 Allied roamers made German by class name | record team byte, trigger groups (`flscene.trigger`), out-of-sight spawns, ally squad follow |
| untextured draws tinted blue | fallback texture (40,70,90) | white: vertex colour only |
| missing ammo, MG nests, dead GI | never ported | `fl_ammo`, `fl_mg_yaw/broken`, DeadGuy |

Record layout notes are in `flscene.py`; the .cdb flag word in `flcore.collision` / `flconvert.COLL_*`.

## Open

- **bug-flp-jeepdraw (engine follow-up):** a script_model whose per-frame origin stepping STARTS east of x 8192 on
  coop_fl_1_1 is never drawn for the whole run (alwaysdraw, r_novis and +broadcast do not help); started at x 8150
  it draws. Worked around with `fl_levels.json` `motion_first`. Bound children of a moving script_model were also
  never drawn (riders are stepped instead).
- Fidelity gaps: see FIDELITY.md (tank path, patrol walkers, 6 air passes, bombs, rockets, door, barks, U-boat).
- 19-34u lips (Frontline steps over them) and 20-30u gaps (Frontline's narrower body) still snag: ramp pass exists
  (`flclear.ledge_ramps`, off: it let the walker onto wall tops), width pass not written.

## Round 2 (2026-11-10 evening) - engine extensions, collision classes, set pieces

**Engine (branch flpolish-eng off rel-1.10.38-engine; gated by worldspawn keys only converted maps carry):**
- `6b9b3575` wide entity coordinates (`hzm_widecoords` -> serverinfo `sv_wideCoords`): the root cause of
  bug-flp-jeepdraw is the +-8192 wrap of the 16-bit entity-origin wire field; MP/coop isolation check 22/22.
- `362b483d` per-map step height (`hzm_stepsize` -> `sv_stepSize`; game Pmove, cgame prediction, actor Mmove).

**Collision sources.** Every converted collision brush now names its source in its nodraw shader, so the walk audit
splits invisible contacts by origin. On the routes the remainder is mostly Frontline's own smooth player-clip layer
(material 3 + special bit): sheets 16-128u in front of facades and rubble that are the ONLY collision of what stands
behind them, and boundaries closing side streets. The original player stopped at them too. Sheets with a wall that
already collides behind them are dropped (`flskin.skins`, 180). Re-seating the rest onto the drawn surface was tried
and removed (it opened escapes through one-sided facade cards or closed passages; bug log).

| geoaudit (crouch flood) | v19 (shipped polish) | v23 |
|---|---:|---:|
| route blocks (original nav edges a crouching player cannot follow) | 146 | 85 |
| path points unreachable | 17 | 17 |
| void falls | 7 | 25 (7 clusters, new step-34 reach) |
| invisible contacts on routes | 982 | 1190 (more reachable area at step 34) |
| - of which Frontline player-clip sheets (m3s) | 419 | 664 |
| - our edge-of-world clip | 132 | 8 |
| visaudit steep see-through | 0 | 0 |

**Set pieces / fidelity (script + converter, not yet seen in game):** the Panzer is placed again (it had been
spawned as a rifleman since the team-byte rule) and drives Frontline's path 66 when its group wakes; the seven
fighter passes, two bombs, two rockets and the U-boat play Frontline's own motion keys with stock models
(`fl_levels.json set_pieces`); StayOnPath soldiers walk their named paths; death ambushers lie in a dead pose and rise
when a player comes within 420u; the wounded MG gunner's line plays; the jeep starts at key 1 and its crew is bound.

## Round 3 (2026-11-10 night) - blocked only by what you can see; Frontline's own meshes; in-game runs

**Visible collision (flsheets, converter 0.5.0).** Every non-walkable Frontline player-clip sheet is dropped and the
drawn geometry it stood in front of gets thin collision of its own. The sheets that bound the level where nothing is
drawn stay (fl_levels.json `clip_keep`, 114 of 1462, curated with `sheetiter.py`: drop all, keep the sheets on the walk
audit's escape frontier) and get a barbed-wire edge. Tree/post columns fit the drawn points inside them. The canal is a
water volume: its quays keep their edge, a bed under the water catches anyone who gets in and the mission script drowns
him (fl_water). geoaudit now ends a walk where the map kills the player and samples visibility from 12u up.

| geoaudit (crouch flood, map step 34) | v19 | v23 | v32 |
|---|---:|---:|---:|
| invisible contacts on routes | 982 | 1190 | 179 |
| - Frontline player clip (m3s) | 419 | 664 | 65 (boundaries with a drawn edge, slopes) |
| - our edge-of-world / quay clip | 132 | 8 | 39 (canal quays) |
| route blocks | 146 | 85 | 95 |
| path points unreachable | 17 | 17 | 16 |
| void falls | 7 | 25 | 11 |
| visaudit steep see-through | 0 | 0 | 0 |

**Frontline's own object meshes** (`flcore.mesh`, inline models `$fl_om_*`): the door (swings open when its group
wakes - checked on camera), the two falling house chunks, the four jeep wheels on the jeep's clock, the P-47 and Stuka
for all seven passes, both bombs, the rockets and the U-boat (checked on camera, bobbing at the lighthouse dock). Their
rotations are the stored ones conjugated by the mirror (`flscene.raw_angles`), vertex colour doubled (PS2 range).

**In-game runs (flpolish-eng build, v1.10.73 base merged):** SP camera run - jeep from key 1 drawn past x 8192, crew
seated, mine, wreck; tank drives path 66 and burns out at the end of the rocketing P-47 pass; bombs, house chunks,
rockets, door, U-boat; 0 Script Errors. Two-client coop route walk (61/63 triggers in the 14 min cap): 103 actors,
Germans 63/74 engaged, 54 killed; Allies 22/29 engaged, 10 killed; 7 idle (5 of them death ambushers no player came
within 420u of); 0 spawned in view; 17 squad joins; 42 groups; 0 Script Errors.

## Round 4 (2026-11-10 late) - ship gates

geoaudit v39: fall-outs **0**, route blocks 49 (the original's routes cut open to MOHAA's box by flroutes), unreachable
16, invisible contacts on routes 105 (37 of them canal quays, 17 kept boundary sheets now with their barbed wire).
SP camera run on the v1.10.74 base: all 17 set pieces that fired played Frontline's own mesh (log `FLSP start ... frontline mesh`),
jeep drawn at the gate, 0 Script Errors. Two-client coop (30 min cap): all 63 triggers, 5/5 objectives,
FLMISSION complete; 106 actors, Germans 67/76 engaged (49 killed), Allies 22/30 engaged (12 killed), 6 idle, 0 spawned
in view, 0 Script Errors.

## Audits (docs/tools/byoaudit) - re-run with the commands in its README
