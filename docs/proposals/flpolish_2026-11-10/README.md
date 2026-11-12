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

## Round 5 (2026-11-10 night) - 1:1 rule, progression walk, last gaps

User rules for this round: the original's own invisible walls stay where the original has them (the canal quays too:
no falling in); wire only where the original drew a fence; a player from the drop must reach every objective and
trigger in order.

| check (v53, hzmconv 1.10.73.7) | result |
|---|---|
| fall-outs | **0** |
| progression walk (`byoaudit/progwalk.py`, 63 triggers + objectives) | **0 blocks** |
| places a player must crouch | 3, all the original's crawl passages: the R4 hole (2900 1680), the passage at (-656 -2700), the interrogation crawl space (-1232..-1712 -4464..-4752) |
| route blocks | 42 (was 46): 24 hug a wall the walk passes, 18 are the original's own walls; **0** gaps too narrow for the box (was 2) |
| unreachable pathnodes | 16 |

The two narrow gaps (an awning post at -1574 -2768, a wall end at -2032 -4601) sat between the 12u samples of a
slanted route. Sampling every route finer opened 988 fall-outs, so the finer samples apply only at reviewed spots
(`fl_levels.json` `route_widen`). The 92u lintel at (-1184 -2592) and three "crouch with no ceiling" spots were audit
artefacts: a standing way exists beside each, and the walk now crouches only where it has to.

Deviations closed: the molotov barrel at the MG nest (explodes, then burns 10 s), the music's intro segment before the
ambient loop, health boxes carry the original's 10/25/50. Still open: barks (VocBnk), the rockets' flight after their
launch keys, the ambushers' rise (no lying-to-standing animation in the stock soldier set), music segment switching,
the start loadout (deliberate, the mod's own). FIDELITY.md: 35 matched, 12 deviated, 0 missing.

In-game on v53: SP self-test 5/5 objectives, rescue, molotov burn proven, 0 Script Errors. Two-client coop to mission
end: 63/63 triggers, 5/5 objectives, FLMISSION complete; 96 actors, Germans 58/67 engaged (45 killed), Allies 22/29
engaged (8 killed), 4 idle, 0 spawned in view, 19 squad joins, 0 Script Errors, no server crash.

## Round 6 (2026-11-10 late night) - barks, rise, music order, the barrels

Converter hzmconv 1.10.73.8 (forces a reconversion), pak v56.

| deviation | what it was | now |
|---|---|---|
| German barks (E3, E6) | thought to sit in the undecoded VocBnk | the shouters' lines are in the level's script bank, which `flaudio` already decodes; the four cues (22-25) are wired to their shouters |
| music (A3) | thought to be trigger-switched | the level's music map (`1_1M.mpf`) gives a fixed play order with one loop point, no trigger switching in this level; `flaudio.music_map` reads it and `flpack` writes the order |
| ambushers' rise (E16) | popped upright | stock dead pose, then the weapon's own prone-to-crouch clip (1.1 s) into normal AI. Authored from the stock animation set, not converted from the disc |
| exploding barrels (E14) | stand-in crate model | Frontline's own barrel and wreck meshes (mesh packs `.mpk#0` / `#1`), solid, set off by a bullet or a blast; the molotov barrel burns 10 s |

Two defects found on the way, both in the shipped v1.10.70 mission:

- **The barrels were invisible and could not be shot.** The stand-in `models/custom/wooden_barrel.tik` has no
  animation file and never spawned ("Bad model name"); only blast damage at the right spot set one off.
- **Four of six "dead" ambushers stood upright.** `ai_off` stops `Actor::Think`, which is what applies the pose; only
  actors that had already thought once lay down. The pose is now held with `no_idle` and re-issued, without `ai_off`.

On camera (local stills only, they show disc content): all six ambushers lie and rise through the clip; a rifle shot
at the molotov barrel sets it off, the four drums beside it chain, the wrecks swap in, the fire burns and goes out.
The shot needs a player on the ground with a weapon in hand: a noclip camera never fires, which cost four takes.

Gates on v56: progression walk 0 blocks (68 targets), route blocks 42, narrow gaps 0. SP self-test 5/5 objectives,
rescue, molotov burn through the blast path, 0 Script Errors, no "Bad model name". Two-client coop to mission end:
63/63 triggers, 5/5 objectives, FLMISSION complete, 4 barks, 8 barrels set off, Germans 63/71 engaged (49 killed),
Allies 22/31 engaged (11 killed), 3 idle (two are ambushers nobody walked up to), 0 spawned in view, 0 Script Errors.
FIDELITY.md: 39 matched, 8 deviated, 0 missing. Open: the rockets' flight (S5), the start loadout (P3, waits
on the user), the deliberate MOHAA-body fits.

**Decided 2026-11-11 (user):** the start loadout (P3) stays the co-op loadout. Closed; do not add the original's Colt / Garand / grenades start.

## Round 7 (2026-11-11, branch flfix2) - first human playtest

Per item: FIDELITY.md "Round 7". Textures: TEXTURES.md (decision list, nothing implemented). Reference for future
missions: `docs/tools/ea/FRONTLINE_REFERENCE.md`.

- **The world was mirrored** (bug-10965). The y flip that fixed triangle winding also mirrored the level: signs read
  backwards, every left turn was a right turn. The transform is now a proper rotation; winding is fixed where it is
  wrong. Config entries measured on the mirrored build are converted on read (`flpack.spec_xy`).
- **Stale pak / stale .pth** (bug-10966, bug-10969): a pathfile cached from an older conversion of the same map name
  survives in the home folder and is used silently. The converter now stamps the build and the mission refuses a
  data script older than it; delete `maps/coop_fl_1_1.pth` in the home when re-converting.
- **Time limit** (bug-10968): a Live Operations Team Match leaves `ui_timelimit 10` archived; `ui_startdmmap` pushes
  it onto the next co-op mission, which then restarted after 10 minutes and dropped everyone to the team menu.
  `coop_mod/server.scr::coop_noLimits` clears the three limits every frame on co-op levels; `start_server.cfg`
  seeds `ui_timelimit` / `ui_fraglimit` 0. Proven on a dedicated boot with limits forced to 1 before and during.
- **Mines** (bug-10967): one blast each, then gone; no chain in the same frame; capped so a healthy player goes down
  (DBNO) instead of dying outright; drawn and signposted.
- **Mounted guns, AI facing, route order** (bug-10970), **water** (bug-10971: the canal is `textures/misc_outside/pond`),
  **no off-screen fights** (bug-10972), **tower ladder** (bug-10973).
- **Tier-1 textures** (bug-10974, user approved): 8 CC0 ground / roof / plank / stone replacements and 11 cut-out upscales, `flhd.py`; verdict per texture in `TEXTURES.md`. Never seen in a client yet.
- Mod files touched (mod repo, uncommitted): `maps/coop_fl_1_1.scr`, `coop_mod/server.scr`, `coop_mod/start_server.cfg`.

Not verified (no visible client may run while the user is playing): after-stills, the off-screen-fight walk, the
ladder climb, a human pass through the interrogation area.
