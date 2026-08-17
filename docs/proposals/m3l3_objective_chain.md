# m3l3 — seven-objective mission rebuild

Design agreed with the user 2026-08-16. Retail m3l3 ships **one** objective ("Locate and destroy the
Nebelwerfers", pushed active at map init). This replaces that with a seven-stage chain, reusing the
map's own scene triggers and the coop systems that already exist.

## Coordinates (user-captured, `viewpos` over rcon)

`viewpos` reports EYE height. Ground origins below already have `DEFAULT_VIEWHEIGHT` (82) subtracted.

### Church defend zone (objective #6)

| | eye | ground | note |
|---|---|---|---|
| centre | `2463 -2312 -149` | `2463 -2312 -231` | |
| boundary | `641 -2444 -197` | `641 -2444 -279` | 48u lower than centre — the churchyard slopes |

**Radius 1827u** (horizontal, ~114 ft / 46 m). Use a CYLINDER, not a sphere: a sphere pops the
player "outside" for standing on a step, and the ground already falls 48u across the zone
(TRAPS T19 — a radius is a sphere unless you make it otherwise).

### Attack wave spawns (objective #6)

All verified against the nav mesh: each sits within 148u of a pathnode, with pathnodes present at
the route midpoint to the church, so none is stranded.

| # | ground origin | yaw | dist from centre | nearest node | opens |
|---|---|---|---|---|---|
| 2 | `5445 -1100 -421` | 263 (W) | 3219 | 129u | start |
| 3 | `5592 -2620 -431` | 103 (E) | 3144 | 69u | start — **faced at the church unless told otherwise** |
| 4 | `3465 -206 -335` | 250 (W) | 2332 | 148u | **only after objective #4 (barbed wire) completes** |
| 5 | `-1220 -851 -240` | 25 (NE) | 3962 | 79u | start |

A fifth reading at `1581 -2440 -279` (891u — INSIDE the radius) was **rejected by the user**: it
would have spawned attackers behind the defenders' line and tripped the "germans inside the church"
fail condition the instant it fired.

**Consequence of the wire gate:** until objective #4 is done the assault comes only from east and
west. #4 is the north approach, so destroying the wire visibly opens a new axis — the objective has
a tactical result, not just a checkbox.

**Cadence:** drive waves on "N alive inside the perimeter", NOT a fixed timer. The approaches run
2,332–3,962u, i.e. 20–40s of travel each, so a fixed timer would let waves stack and arrive as one
mob after a lull, and the far western lane (#5) would go dead.

## The chain

| # | objective | mechanism | status |
|---|---|---|---|
| 1 | Advance into the town | existing BSP `setthread scene3` trigger — no new coords needed | ready |
| 2 | Clear the town | scene3 spawners exhausted AND no live germans within a radius. Needs a straggler sweep so one stuck enemy cannot strand it | ready |
| 3 | Eliminate the King Tiger | hook `scene4_tank_death`. Also intercept the BSP `scene4` trigger so the tank cannot start before #2 completes | ready |
| 4 | Bridge the barbed wire (fetch a plank, ramp over it) | see the detail section below — the wire is NOT destroyed | needs 2 coords |
| 5 | Signal the airborne drop | `objective_drop.scr` + an `objective_positions.scr` entry for m3l3. Red flash = `pulse_explosive.tik` + the proven glow recipe (`models/fx/dummy.tik` + `light` / `lightRadius` / `lightOn`) | needs smoke coords |
| 6 | Defend the church until reinforcements | wave director + cylinder watcher + scripted fence (designed, not yet implemented) + fail condition, then the C-47 drop | needs fail threshold |
| 7 | Locate and destroy the Nebelwerfers | retail, already written — must move from map-init to last | ready |

## Systems being reused (do not rebuild)

- **Objectives + compass waypoint:** retail `global/objectives.scr::add_objectives <n> <status> <text> <origin>`
- **Airborne drop:** `coop_mod/paradrop.scr` — C-47 flies in, 5 paratroopers descend and fight
  alongside players. Fires on `smokeDropZone <origin>` when a signal smoke lands.
- **Signal smoke placement:** `coop_mod/objective_drop.scr`, per-map config in `objective_positions.scr`
- **Red pulsing objective marker:** `models/items/pulse_explosive.tik` (as used by `coop_radio_bomb_enable`)
- **Countdown timer:** the NATIVE `stopwatch <seconds>` player command, fanned to every player by
  `coop_mod/replace.scr::stopwatch`.

**NOT reusable, corrected 2026-08-16:** `cmpatch/<map>.txt` is *not* a way to add walls. `cm_killbrush`
only ZEROES a brush's contents — the e1l2 recipe DELETES unwanted collision and cannot create any.
A solid brush would also block the AI. See the scripted fence below.

## Known risks

- **`holdout.scr` (759 lines) is NOT being used** for objective #6. It has wave machinery that looks
  ideal, but it has never been tested in play; debugging an unproven system inside a campaign
  mission is a worse trade than writing bespoke waves off the map's own spawner pattern.
- **Objective restructuring is the fiddly part.** Retail pushes obj 1 active at map init and
  `scene7_objective_assignment` retargets the compass to the nearest intact nebelwerfer. That logic
  must only run once stage 7 opens, or the compass points at the finale from the first second.
- **Paradrop pathing is currently broken** (landed troopers fall into a patrol think with no nodes —
  557 `Path not found` in one session, entnums confirmed as `c47fly.tik` / `allied_usa_c47-paratrooper1.tik`).
  Objectives #5 and #6 both end in a drop, so this wants fixing before the drop becomes a mission beat.

## Objective #4 detail — BRIDGE the wire, do not destroy it

**Why this design and not demolition.** The barbed wire on m3l3 is not an entity and not removable:
a search of the whole BSP entity list found no wire model and no wire targetname, and `markwall` at
16 units returns only `textures/common/clip` (brush **3962**, one brush spanning the whole run). The
visible wire is drawn geometry. `killwall` refuses visible geometry by design and can only kill the
clip — so "destroying" the wire would leave an intact-looking fence that players walk straight
through. The user's objection is correct and decisive: that reads as a bug, not an objective.

Going OVER the wire removes the problem entirely. The fence stays visible and intact, nobody clips
through anything, and it is closer to how obstacles were actually crossed. It also makes the
question of whether the wire is baked geometry irrelevant, because we stop trying to delete it.

### The mechanic (as specified by the user)

1. **Plank pickup.** A plank prop at a user-placed spot, **flashing red**. Walk up, interact, it
   **disappears** and the player is carrying the plank.
2. **Plank placement.** A **flashing red ghost plank** lying over the wire at a second user-placed
   spot. Interact while carrying, the ghost is replaced by a **solid plank** and the ramp is live.
3. Objective completes; **spawn #4 (north) opens**, so bridging has the same tactical consequence
   the demolition version would have had.

The three `bangalore_pulsating` props placed earlier are **withdrawn** — that idiom belonged to the
demolition version.

### Prerequisites, in this order

Order matters: `CreatePaths` traces real geometry to decide links, so the world must already be in
its final shape before nodes are walked.

1. Place the plank props (pickup spot + bridge spot).
2. `killwall` the clip — brush **3962**. Without this the ramp is blocked by invisible collision
   even with a plank visibly lying across it. Persists to `cmpatch/m3l3_local.txt`.
3. `coopnavrec` ON, walk up the plank and down the far side, OFF. This drops a node per step and
   rebuilds the graph (`Player::CoopNavRebuild` -> `CoopPrepareRuntimeRebuild` + `CreatePaths`).
4. Bake the printed nodes into the map script via `coop_navnode` — **runtime nodes do not survive a
   map change**, so an unbaked run is lost on the next load.

### Why the AI can follow it

MOHAA's path graph is BAKED: node connectivity comes from a precomputed `.pth` archive, so a prop
spawned at runtime creates no links and AI would ignore a ramp entirely. That was the original
objection to this design. It is answered by the runtime rebuild this project already has
(`PathSearch::CoopPrepareRuntimeRebuild` keeps the node objects, drops the connectivity, and lets
`CreatePaths` relink from scratch), plus the `coopnavrec` walk-the-ground tool. Nodes over the plank
therefore give the waves a real route.

### Props available

| what | category | index |
|---|---|---|
| plank | **33 "GEOMETRY (SCALABLE)"** | 9 — `box_wood_plank` (scalable, best for a ramp of an exact length) |
| plank alt | 22 "DEBRIS + RUBBLE" | 10 / 12 — `crate-jib-plank`, `crate-jib-smallplank` |
| ramp alt | 11 "DEFENSES + BARRIERS" | 24 / 25 — `ramp_quadleg`, `ramp_tripleleg` (pre-made ramps with legs) |

`box_wood_plank` is scalable, so it can be sized to span the wire exactly rather than approximated.

### Still needed

- Coord for the **plank pickup** spot
- Coord for the **plank bridge** spot (where the ghost lies over the wire)

## Objective #6 detail (as designed with the user)

### Progress fence — DESIGNED, NOT IMPLEMENTED (bug-1820, reverted by bug-1822)

Five walked points, four segments, 291u total, essentially straight (bearings 61-75 deg) and flat
(z -307/-308). Sits ~3,000u from the church.

| v | ground origin |
|---|---|
| 1 | `-110 -795 -307` |
| 2 | `-69 -717 -307` |
| 3 | `-39 -662 -307` |
| 4 | `-2 -592 -308` |
| 5 | `14 -533 -308` |

**STATUS: reverted.** A first implementation was written and PARSE-KILLED maps/M3L3.scr — the whole
file, so m3l3 loaded with no script at all and players got the raw team menu (T1). It was removed to
restore the map. The design below stands; the code must be rebuilt under the morlang expression
rules and compile-tested per piece (see bug-1822).

To be implemented in script, NOT geometry, for two reasons that are both hard requirements:
`cm_killbrush` can only ZERO a brush's contents (the e1l2 cmpatch recipe deletes collision, it
cannot create any), and a real solid brush would block the german waves as well as the players.

**The blocked side is learned, not hardcoded.** The church and the nebelwerfers lie at nearly
perpendicular bearings from this fence, so "forward" cannot be inferred from geometry, and guessing
wrong would fence players OUT of their own defensive position. `coop_fence_arm` samples a live
player's side when it arms (players are at the church at that point) and takes that as the allowed
side. Correct by construction here and on any map it is reused for.

Side test uses the overall v1->v5 line rather than per-segment normals: the segments deviate by
<14 degrees, so per-segment normals would flip sign inside the kinks and jitter a player back and
forth. Nearest-distance still walks all four segments. Lowered by `coop_fence_down` when the
nebelwerfer objective opens.

### Nebelwerfer suppressive fire (18 impact points)

The guns you are about to go destroy shell you while you hold. Points are ground origins.

`946 -2667 -207` · `709 -3141 -432` · `1189 -4168 -443` · `2807 -2640 -451` · `1010 -2132 -241` ·
`1009 -1844 -312` · `3694 -2113 -495` · `1933 -3008 -333` · `1455 -2765 -278` · `2699 -4165 -479` ·
`3736 -3080 -456` · `1061 -2399 -253` · `711 -2193 -279` · `208 -2558 -343` · `1729 -3140 -321` ·
`2691 -1901 -378` · `1985 -1800 -309` · `787 -1712 -311`

14 fall inside the defend radius, 4 outside (1868-2268u) — **keep the outliers**, they sell it as
area fire rather than a scripted ring around the player. Spread 3528 x 2456u, distance from centre
470-2268u, so damage can be weighted by proximity instead of a bare random roll.

Open decisions: escalate cadence with wave count (recommended - gives the phase a shape); reuse the
existing stuka/artillery warning so shells whistle before landing (recommended - otherwise damage
comes from nowhere); **exempt germans from shell damage**, or the barrage fights FOR the player by
clearing the church and improving the overrun bar.

### HUD

- **Overrun bar** = how full the church is (germans inside vs fail threshold). 3 slots: label,
  track, fill. Precedent is the DBNO team-revive channel (text 135 + bar 136-137). Must be >=100 so
  the calm-player fade cannot hide it (T18). Everything 100-155 is allocated and 156-249 is the
  computed challenge/objectives block, so borrow from a range that can never be co-displayed with a
  mission-time firefight: lobby-only (117-126) or mission-end debrief (127-134).
- **Countdown to the airborne** = the NATIVE `stopwatch <seconds>` player command, fanned to all
  players by `coop_mod/replace.scr::stopwatch`. No new HUD work.

## Objective #6 — settled design (2026-08-16)

### Access: a ladder, not a bridge

The road approach was ABANDONED after three independent routes hit the same wall (see the wire
section). Players now reach the church by **placing a ladder over a wall**:

- Ladder marker sits pre-placed, **flashing red**; interact and it becomes a real climbable ladder.
  No fetch step - a fetch means one player wanders while three wait.
- **Placement comes from the build-mode capture, verbatim** (bug-1828). `buildmode.scr:641` passes
  `coop_build_lastpos` / `coop_build_yaw` / `lh` to `ladder.scr::main`, and writes those SAME three
  values into the save as `local.m.origin`, the `local.m.angles` yaw and the `(LADDER h N)` comment -
  so the save already holds the exact arguments. First build invented yaw 192 / height 160 against
  the captured 358 / 128; a 166-degree yaw error builds the climb volume on the wrong face of the
  wall, so the ladder is visible and unclimbable. A ladder is placed FACING INTO the wall - yaw is
  not cosmetic.
- **The base needs a manual 22u standoff** (bug-1831). The capture is the point the player aimed at,
  so the origin sits ON/IN the wall face; `ladder.scr`'s own 20u clearance trace then starts in solid
  and returns its start point unmoved (log: `LADDER spawned at ( 4016.000 -967.000 -328.000 )`), and
  the climber - placed a further 14u along `-forward` - is still against a wall it is ~15u wide
  against, so it grinds partway up. `coop_churchLadderMarker` now steps the base 22u along `-forward`
  before building. Direction is fixed by ladder.scr's own convention: the angle is the yaw the player
  faces while climbing, i.e. **INTO** the wall, so `-forward` is out of it.
- `coop_mod/ladder.scr` spawns a genuine `func_ladder` plus beam rails (bugs 1412/1415). This is the
  ONLY crossing the engine supports, because **ladder climbing is player-only**: `PathNode::LadderTo`
  is declared in navigate.h:201 and NEVER IMPLEMENTED, there is no `AI_LADDER` spawnflag (the QUAKED
  comment advertises one; the constants stop at AI_LOW_WALL_ARC), and every MASK_LADDER trace lives
  in player_conditionals.cpp. Actors cannot climb, ever.
- That is fine here BY DESIGN: the ladder is for players. The waves never use it.
- Build-mode marker placed at `4016 -967 -328`.

### Enemy arrival

- **Barbed-wire spawn `2137 -1342 -343`, facing 192 deg** (south, toward the church), 1023u out.
  Nearest pathnode 94u, 35 nodes within 600u, route midpoint covered - **reachable, verified**.
- ~50 `bush_full_heavyweather` props placed to screen the spawn so pop-in is hidden.
- When the defend objective triggers, a **cosmetic board** spawns over the barbed wire. It carries
  nobody - it exists purely to explain how the waves got across. This is what makes the whole design
  work: the fiction is sold visually while the AI path from where nodes already exist.

### Keeping players in the church

NOT an instant fail (agreed with the user) - in a firefight players get pushed out or chase
stragglers, and a hard boundary would lose runs on a technicality.

- **Overrun bar accelerates by the FRACTION of the squad outside the radius**, not merely when it is
  empty. One of four peeling off to flank is tactics; four of four is abandonment.
- **Per-player message on crossing out**, not a team banner - the three doing their job must not be
  nagged. Stops the moment they return.
- **Waves converge on the CHURCH, not the nearest player.** Leaving then means watching the church
  fall from a distance: self-punishing, no artificial rule needed.
- Compass objective stays pinned to the church so the way back is always legible.

### MG42s

Three of the map's own `scene6_*` guns are in play: `scene6_mg2` (146u), `scene6_mg1` (186u),
`scene6_mg3` (506u). **Ammo-gated at 500 rounds each**, resupplied by the existing deployable ammo
box system - the boxes sit inside the church, so resupply is a reason to STAY.

Note on the number: an MG42 fires ~20 rounds/sec, so 500 rounds is ~25 seconds of continuous fire.
Expect to tune. Remaining count must be VISIBLE or an empty gun reads as broken.

Open: `turretweapon_german_mg42` is not the `vehicleturret.cpp` class that carries `m_iAmmo`, so the
script-facing ammo lever must be confirmed before promising the cap; fallback is a script shot
counter that makes the gun un-mountable at zero.

### RESOLVED: the church geometry

The two readings were the building's opposite ENDS, not centre-and-edge - confirmed by the user
("the mg42s are opposite side than the entrance").

| | ground |
|---|---|
| entrance end | `639 -2427 -279` |
| far end (MG side) | `2463 -2312 -231` |
| **CENTRE** | **`1551 -2370 -255`** |

- **Zone: `level.coop_chZone` = 1100u** (one constant, read by the german count, the defender
  count and the nag). Shipped as 950 first and that was wrong: the MG42s sit at 905 / 947 / **995**u,
  so scene6_mg2 fell OUTSIDE the church it stands in and manning it did not count as defending,
  while scene6_mg3 sat 3u inside the boundary. 1100 clears all three plus the door (914u) with
  margin. bug-1829.
- **The outer 1827u "leave penalty" ring is GONE.** It only ever fed a multiplier on a bar that
  could not be pushed back, and it nagged from so far out that leaving the zone that decides the
  fight went unmentioned. The nag now fires at the zone edge, where it means something.

Cross-checks that confirm the anchor: the barbed-wire spawn is 1183u out (outside the building,
inside the grounds - attackers arrive beyond the walls, correct), and two of the map's OWN scene6
rally points fall inside at 212u and 575u, i.e. retail already expects Germans to reach the nave.
That is the breach the fail condition measures.

### Fail threshold - AGREED

`2 + (2 x players)` -> **4 / 6 / 8 / 10** for 1-4 players. Four germans loose inside a church is
already losing for one player; +2 per player keeps a full squad honest without making it
unloseable, since more players also means more doors covered.

### (superseded) the readings once looked contradictory

`2463 -2312` (taken as centre) and `613 -2434` (taken as doorway) are **1854u apart** - further than
the 1827u radius derived from them, so the two zones would be identical and the fail condition would
trip on the first wave. The scene6 rally points cluster at x 256-448 (near the doorway reading) while
the three church MG42s sit at x 2388-2544 (near the centre reading), so the fight spans ~2200u and
one of the two anchors is mislabelled. **Need a clean pair from the same building: centre of the
floor, then its doorway.** Every zone check depends on this.

## BUILT 2026-08-16 (bug-1824) - objective #6, testable in isolation

Nine pieces, each compile-tested by dedicated boot before the next was written. Start it with
`set coop_chStart 1` in console; it is NOT on the objective chain yet.

| label | role |
|---|---|
| `coop_churchDist` | cylinder distance from centre `1551 -2370` |
| `coop_churchGermans` / `PlayersOut` / `PlayersAlive` | zone counters |
| `coop_churchThreshold` / `coop_churchRate` | 2+2*players; fill rate x1.0-3.0 by squad outside |
| `coop_churchBarSetup` / `BarSet` / `BarClear` | overrun bar, slots 128-130 |
| `coop_churchDefense` / `coop_churchNag` | the tick, fail check, per-player return message |
| `coop_churchWaveLane` / `coop_churchWaves` | 5-lane pressure-driven director |
| `coop_churchImpact` / `Barrage` / `ShellHurt` | 18-point barrage, germans exempt |
| `coop_churchLadderMarker` | flashing marker -> real func_ladder |
| `coop_churchWireBoard` / `coop_churchDrop` | cosmetic board; C-47 at the LZ |
| `coop_churchPhase` / `coop_churchWatch` | orchestration + dev entry |

**Tunables:** `coop_chDur` 300, `coop_chCapF` 6000, `coop_chDrain` 250, `coop_chZone` 1100,
`coop_chShellMin/Max/Cap` 4/9/260. Set `coop_chDebug 1` to print germans / defenders / rate / progress
per tick.

### The bar is a CONTESTED capture point - not a countdown (bug-1829)

The first build shipped a one-way ratchet: the tick was `if(rate>0){prog+=rate}else{prog-=drain}`,
and the rate only hit 0 with ZERO germans in a zone spanning the whole scene6 street - so during the
battle it never drained, and a defender standing inside subtracted **nothing**, merely dropping a
3x-to-1x multiplier. Playtest: *"Church got overrun really fast and i dont think anyone was in it"*,
*"me going in didnthelp"*. The constants were unmeasured too - cap 24000 solo against a rate reaching
1800/tick at 2 ticks/s is a 5-10 second loss, against a 300 second phase.

Now `coop_churchRate` returns a **signed** delta and each defender inside cancels one german:

| state | delta / tick |
|---|---|
| no germans inside | `-coop_chDrain` |
| germans > defenders | `net * 60`, **doubled when nobody is inside at all** |
| defenders >= germans | `-((defenders - germans) * 125 + coop_chDrain)` |

Measured solo: 4 germans undefended = 25 s to overrun, the same 4 with one defender = 67 s, defenders
matching germans = the bar clears. Leaving it alone is what loses it, which is the point of the phase.

**Still to build:** MG42 ammo gating (the script-facing ammo lever for `turretweapon_german_mg42`
is unconfirmed - it is NOT the `vehicleturret.cpp` class that carries `m_iAmmo`), and the trigger
that commits the phase to the objective chain.

## Still needed from the user

1. C-47 landing zone coords (where the paratroopers touch down)
2. Signal smoke placement coords (objective #5)
3. Which exits to seal for the church phase (invisible walls)
4. Barbed wire: entity names, and shoot-vs-plant
5. Fail threshold: how many germans inside the church loses the mission


## AGREED OBJECTIVE PANEL LAYOUT (user-approved 2026-08-16, NOT yet wired)

Ten narrative steps, eight panel slots (`coop_so1`-`so8`). Two merges, agreed with the user:

* **town advance + clear the town = one objective.** Same fight, and the retail script has no clean
  boundary between them.
* **acquire the explosives folds into destroy the flak**, as a toast rather than its own slot - it
  is a ~20s fetch between two real objectives and the toast already announces it.

| slot | objective | fires on | status |
|---:|---|---|---|
| 1 | Take the town | map start / town entry | trigger TO FIND |
| 2 | Destroy the King Tiger | `scene4` tank destroyed | trigger TO FIND |
| 3 | Get over the wall | `coop_churchApproach` (2500u, threads `scene6`) | **working** |
| 4 | Clear the church | `coop_churchAnyGermans` 0 + player inside | **working** |
| 5 | Destroy the flak gun | plant marker -> 15s stopwatch -> `p_aagun_d` swap | **working** |
| 6 | Signal the drop zone | m18 marker used | **working** |
| 7 | Hold the church | `coop_chDone` with `coop_chOver` 0 | **working** |
| 8 | Destroy the Nebelwerfers | retail 4-gun counter | retail, needs a slot |

Five of eight already fire at the right moment; wiring them is adding `coop_obj_push <slot> <status>
<text>` and `coop_obj_toast_all <index> <text>` at hooks that exist. Slots 1-2 need their triggers
located in the retail script first.

**Process, agreed: ONE objective per dedicated-server boot.** This file has been parse-killed twice
(bug-1822, bug-1826) and a whole chain written blind cost a session both times. The three scanners
cannot prove morlang compiles - only a boot can.
