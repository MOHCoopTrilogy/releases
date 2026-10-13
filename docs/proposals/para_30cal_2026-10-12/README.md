# The paratrooper's .30 cal (bug-3562) - 2026-10-12

User: "When the paratrooper sets up his 30 cal he kinda just stands with it over his shoulder mounted on nothing
(without a bipod at that). How can we make it so he sets it up on an object or something realistic like that? Im
also not sure it has the right 30 cal sound when he shoots." And: "I am open to him dropping a small sandbag as
support as a worst case scenario as long as its never in the path of progress".

**Status: SECOND PASS committed to the mod (`coop-wip` `8a35ddcd`, on top of `e40bfab8`), NOT deployed. Mod only -
no engine change. The second pass REPLACES the site search described below (sections "What it does now" to "Not
verified" are the first pass, kept as the record): read "SECOND PASS" at the end of this file first.**
Files: `coop_mod/parasquad.scr` (gunner, findMgSpot, mgSetup, mgPackup + new mgSurf, mgFree, mgOpen, mgWalk,
mgLower, mgAbort), `anim/mg42_idle.scr`, new `models/statweapons/coop_30cal_para.tik`.

## What was wrong

- The gun was placed **14 u short of the cover it was meant to rest on and 12 u above its top**, and nothing was
  ever traced under it. On open ground it was simply put 40 u up. The model (`models/statweapons/30cal.tik`) is the
  bare gun - retail maps build the mount into the map.
- Sound: that tiki plays `jeep_snd_fire` = `sound/weapons/fire/50CalFire2.wav`, **a .50 cal recording** (the
  shipped HRRTM pack even replaces it with a longer .50 sample), at `firedelay 0.06` - the MG42's 1000 rpm. The
  .30 cal the players carry (`models/weapons/30calportable.tik`) plays `WaW30cal` at `firedelay 0.09`.

## What it does now

`findMgSpot` plans one of three emplacements, best first. Every one stands on something that was traced.

| | support | where | gun height over the gunner's feet |
|---|---|---|---|
| A | the retail MG42 bipod (`models/statweapons/mg42_bipod.tik`) on an **object already in the map** | a solid WORLD surface 22-56 u up, level within 3 u over the bipod's feet and 12 u deep, with nothing standing on it (a fence on a wall is refused); a pushable crate, a vehicle or a door is not a support | 40-75 u |
| B | Breakthrough's tripod (`models/weapons/mg42portable_placed_base.tik`, 49 u) on the **ground** | all three feet on world ground within 6 u of level, nothing ahead for 72 u | 50.5 u |
| C | a small **sandbag rest** he puts down (31 u, non-solid) with the bipod on it | only where the ground will not take the tripod (6-12 u out of level), only after four empty searches, never on m3l1a / m3l1b / e3l1 / e3l2 / obj_team3 | 49.5 u |

The pose is the engine's own: `Actor::ThinkHoldGun_TurretGun` blends the crouched and standing gun animations from
the gun's height above his feet (38.7 u = crouched, 71.8 u = standing) and seats him ~61 u behind it. So every mode
keeps the gun in that band over the ground he will be on, and his seat is swept with his hull the way the engine
does it (monster clip included). There is no prone gunner animation in the game for an actor, so "prone behind it"
is not offered.

For every mode: a field of fire (2 of 3 rays, centre and 25 degrees either side, against solid / fence / weapon
clip), room over the gun, no player in front of the muzzle (unchanged), not crowded (unchanged), and **mgOpen** -
he must have 150 u of free width across him with 40 u each side and 64 u behind, on one level (no stair, no edge
beside him). For the sandbags it is 220 u and 96 u. That is what keeps him out of a doorway, corridor, trench,
stair or bridge. The mount, the bags and the ammo can are **not solid**, so nothing put down can block a player,
an actor or a vehicle even if a placement is wrong.

Set-down: sandbags, then the mount, then the ammo can, then the gun, each lowered into place (0.25-0.35 s);
pack-up is the reverse. The surface is traced again when he arrives, and **a gunner the engine did not seat at the
gun packs up at once** (no more hands on nothing). The existing aborts stay (player in front, spot not reached).
The walk-up tries the path graph, then walks straight over an `info_waypoint` when the line is clear.

Sound: new `coop_30cal_para.tik` = Breakthrough's file with `WaW30cal` and `firedelay 0.09` - the same sample,
alias and cadence as the players' .30 cal. For the shooter's squad and for players at distance it is the ordinary
weapon alias (800 / 4000 u falloff). The distant-gunfire tail (`coop_distantFire`, beyond 2500 u) and the bullet
crack (`coop_bulletCrack`) are driven by the bullet message, not by the alias (`cgame/cg_parsemsg.cpp`), so they
apply to this gun as to any other - by code reading, not heard.

`anim/mg42_idle.scr`: a gunner the engine has crouched traverses with `mg42_crouch_left/right`; the standing clips
stood him up for every turn of the gun. This file serves every machine gunner in the game.

## Tested (harness G:/mohaa-hudfeed5, game.dll 9b8ac78f, a real C-47 stick called by the test driver)

| place | map | result |
|---|---|---|
| ground, tripod (B) | m3l2 | set up and fired in 3 sessions, packed up in the one that ran to the end. Stills and the GIF. Not re-run with the last two guards (seat sweep, seated check) - those were re-run on the sandbag site only |
| sandbag rest (C, mode forced on level ground) | m3l2 | set up, fired, packed up - 5 sessions, the last with the final script |
| object (A) | m4l1, an earth bank 33 u high | **refused by the final script.** Earlier builds set the gun on the bank on its bipod, but the engine would not seat the gunner there (a clip hull at the seat) and he knelt 25 u short with his hands on nothing - that is what the seat sweep and the seated check were added for. No site where A completes was found |
| before (released script) | m3l2 open ground | gun 40 u in the air, no mount: `media/ground_tripod_before_after.jpg` |

0 script errors in every session; `depthscan2`, `linecheck`, `prosecheck`, `quotecheck`, `check_empty_rhs` clean;
`check_mp_isolation` 22/22.

## Media

- `media/ground_tripod_before_after.jpg` (and `_wide`) - before / after on open ground. In the close after-crop a
  squadmate stands in the left foreground; `after_ground_0..4.jpg` are the full frames.
- `media/sandbag_rest_after.jpg`, `after_bag_1.jpg` - the sandbag rest.
- `media/tripod_setup_fire_packup.gif` (2.6 MB) - tripod: set-up, firing, pack-up. The firing part is cluttered:
  a test enemy ran into the emplacement and squadmates crowd round.
- `media/superseded_*` - the m4l1 bank at night (brightened x2.2), from the build that still accepted that site.
  They show the bipod on the bank AND the unseated gunner. Kept as the record of why the check exists.

## Not verified / known limits

- **Mode A has no successful run.** The surface tests are exercised (grid probe of m4l1: 10 hits before the seat
  test), the full emplacement is not. A daylight map with a low solid wall would be the place to see it.
- **Mode C was only seen forced** (`level.coop_psqMgForce = "C"`, a test hook) on level ground. Its natural
  trigger - ground 6-12 u out of level after four empty searches - was not reached in a session.
- **Pathnodes are not readable from script**, so "not in a path" is the clearance geometry above plus non-solid
  props, not a pathnode test. A mission vehicle's spline is not known to the script either: the gunner himself
  (a solid actor) can still be in a vehicle's way on open ground, exactly as any trooper can.
- **Omaha maps were not booted.** The sandbag ban is a map-name test in `findMgSpot`.
- **Sound was not heard by anyone** - alias, sample and cadence are from the files. `WaW30cal.wav` is a quieter
  recording (loudest 80 ms RMS 0.26 against 0.83 for the .50 sample) played at volume 3.0, as for the players' gun.
- **The walk-up fails on some landings**: in 3 of the last 4 m3l2 tripod sessions he came down 350-600 u away with
  no path and no clear line, and never got to the spot (he retries every 15 s). The released script has the same
  limit; the straight-line fallback only helps when the line is clear.
- The gunner swings on a 61 u arc as the gun traverses +-60 degrees; the seat is swept at 0 and +-45 degrees only.
- The bipod sits under the gun's pivot, which on this model is about a third of the way back from the muzzle.
- Second client, dedicated server, gl1: not run.

---

# SECOND PASS (2026-10-12, `coop-wip` `8a35ddcd`) - and the HANDOVER

User, on the first pass: "I think it makes more sense for him to go to the nearest existing cover he could prop it to
with a bipod and suppress enemies or place the sandbag with 30 cal where he can suppress enemies". Then: "Make sure
the sandbag isn't invisible on the sides too", "not the BAR paratrooper and it's a riflemen instead" / "Don't
completely remove the BAR paratrooper", "if he dies on it, it should stay there and players should be able to mount it
with a finite amount of ammo and overheat mechanic".

## What is in the commit

`coop_mod/parasquad.scr` (the whole `.30 CAL` block is new; `findMgSpot` is gone), new `models/static/coop_mg_bags.tik`
+ `scripts/coop_mgbags.shader`, generator `docs/tools/gen_coop_mgbags.py` (the `.skd` / `.skc` are gitignored like every
generated mesh; they are on disk in the mod tree and `--check` passes).

| | |
|---|---|
| **Order** | A = existing COVER under the bipod, C = the sandbag rest, only when no cover passes. The ground tripod (B) is behind `coop_paraMgTripod 1`, default off |
| **Cover (A)** | `mgTry`: something solid within 120 u at shin height; its top traced 9 u (5 u for a thin wall) in from the face, both bipod feet and 3 u before / behind them on it and level within 3 u, nothing standing on it (a player clip over it is ignored), 21-53 u over the ground he will be on. A window sill passes |
| **Sandbags (C)** | near-level open ground (8 u across the footprint), within 300 u of him, never where a player has walked (`trail` / `mgLane`: the last 48 marks, 110 u), never straight ahead of the squad (100 u either side for 420 u), never in a gap (`mgOpen` strict), never on m3l1a / m3l1b / e3l1 / e3l2 / obj_team3 |
| **Field of fire** | `mgFire`, traced from the gun: to the known enemy (clear to within 96 u of him, pitch within 20 degrees), to where one was last known (15 s), or 800 u down the line of advance; plus one flank. No field = no site |
| **Seat** | `mgSeat` is the engine's own arithmetic (`Actor::ThinkHoldGun_TurretGun`); his hull is swept at the seat for 0, 15, 30, 45 degrees either side and `maxYawOffset` is set to what is free (under 30 = refused). He is put on the traced seat before `turret` |
| **Getting there** | `mgReach`: `runto` + `self.pathdist` after 0.3 s = a real path test from script; else a straight walk over ground traced every 32 u (`mgLine`); else the graph to a via point and straight from there. Unreachable sites are printed and skipped; no reachable site = he stays a rifleman |
| **On the gun** | the turret's own track / suppress cycle (5 s on the last seen position, 3 s watching); `mgHold` holds fire with a player or squad mate in front and adds script bursts at an enemy only the squad knows; `mgTend` packs up when the squad moves on, the support is gone, or the enemy is out of arc / masked for 15 s (the next search re-sites him) |
| **Who** | member 3 (M1 Garand) carries it; member 1 keeps the BAR. Member 3 is also the man who bails out of a C-47 lost to flak. A squad that lands without him has no .30 cal |
| **If he dies at it** | `mgLeft`: gun, mount, bags and can stay; belt = what was left of 250 (his fire is reckoned at 11 rounds a second of bursts, never under 25); players mount with Use (engine `TurretGun`), overheat and the belt read-out are the engine's |
| **Stray men** | `walkOut` (brain, FOLLOW): a man two orders could not move walks straight over traced ground |

**Why the walk-up failed** (first pass: "lands 350-600 u away with no path"): `PathSearch::NearestStartNode` and
`NearestEndNode` (`fgame/navigate.cpp`) look for a pathnode only in the **256 u map cell** the man / the goal stands
in (and within 94 u of his height). A cell with no node = no path, to anywhere, for ever; `runto <vector>` then does
nothing and nothing tells the script. `g_patherror 1` prints it ("couldn't find start node" / "end node").

## Shown in engine (harness G:/mohaa-hudfeed5, integration binaries built_integ7, real C-47 sticks)

| kind | map | what happened | debug line |
|---|---|---|---|
| cover: a **window sill**, 48 u | m3l3, upstairs room at (3080, 3959) | planned, 34 u straight walk, set up standing (hp 66.5), packed up when the squad moved on - twice (a6, a7) | `mg site how=2 mode=A ... top=48.000 fire=advance:1.259 arc=45` |
| sandbags, open yard | m3l2, three sessions (g1, g2, h1) | real landing, **path walks of 345 u (path 812), 135 u, 80 u**, set up crouched (hp 40), packed up | `mg site how=1 mode=C ... walk=345.034 path=812.049` |
| sandbags, natural | m3l3 lower ground (a1, a2) | 6-14 refused searches, then a site; the map's own snipers killed him in a2 | `mg plan aim=enemy ... passed=12 tried=1` |
| killed at the gun | m3l2 (h1) | `mg left for the players belt=241 fired=9.600`; the player pressed Use: mounted (`turret=` the gun), fired, emptied a 40-round TEST belt ("BELT EMPTY"), Use again: off it, walked on 100 u | `logs/run_h1.txt` |
| Omaha | m3l1a (om1) | four searches, every one `bags=0 ... passed=0`: nothing placed, he stays a rifleman | `mg nosite aim=advance ground=45 passed=0 tried=0 bags=0` |
| unreachable site | m3l3 (a4) | the same sill from 230 u away with no path and no walkable line: refused every time | `mg refuse why=unreachable mode=A ... walk=230.204 path=0.000` |

0 script errors from this code in every session (the m3l2 errors in g1 are the map script calling Germans the test
driver removed). Scanners clean, `check_mp_isolation` 22/22.

**Test set-up that is NOT the game**, said plainly: on m3l3 the gunner was stood 70 u from the hold point until a site
was planned (`bring`; that room has no pathnodes and the squad wedge sends him 300 u off); his health was 5000 there;
`purge` removed the map's own Germans in the a4-a7, g and h sessions; the 40-round belt in h1 was set by the driver.

## Media (`media/`, second pass = `p2_*` and `sandbag_walkround_*`)

- `sandbag_walkround_after.jpg` - the new rest from 8 directions standing, 8 crouched, and above: closed all round.
  `sandbag_walkround_before_firstpass.jpg` - the first pass's wall end cap the same way: an open shell, black patches.
- `p2_cover_window_m3l3_a/b/c.jpg` - the gun on its bipod on the sill, his rifle slung, ammo can on the floor.
- `p2_sandbag_m3l2_a/b/c.jpg` - the sandbag rest in the yard.
- `p2_left_gun_m3l2_*.jpg` - after his death (left_0/1), a player on it (mount_0, mount_fire, mount_empty), off it.
- **No GIF.** The frames of g2 (`G:/mohaa-hudfeed5/runs/p2_g2`) have squad mates standing between the camera and
  the gun the whole time and show no firing: not a clean GIF, so none was made.

## NOT verified / not done - the handover

1. **A clean GIF, and the gun actually seen firing from a cover site.** `mgHold`'s script bursts never ran in a
   session (0 `mg suppress` lines); the turret's own fire was seen on the first-pass tripod and by a player in h1.
   Recipe for the GIF: after `mg setup k=1` move the hold point 480 u aside (under the 560 u pack-up distance) so the
   wedge leaves, then the driver's `enemy` command, camera `cam` 130 : 110.
2. **Only one cover site was run** (the m3l3 sill, standing). The planner finds cover on m4l3 (12 sites), m2l1 (11),
   m5l1a (7) - `tools/pass2/logs/sweep_*.txt` - but there a teleported player is sent back (m4l3, m2l1) or the stick
   lands on roofs (m5l1a), so no session got a gunner to one. A crouched cover site (top 21-35 u) was never run.
3. **Second client: not run.** Everything put down is an ordinary server entity (script_model / TurretGun).
4. **A player on a LOW gun, seen by others.** The left gun is a `TurretGun`: the player stands. On the sandbag rest
   the gun is 40 u up; what a standing player's body looks like on it in third person was not looked at. Probably
   wrong, and it needs the player turret legs state (engine / `player_legs.st`), not script.
5. **Engine follow-ups for the left gun** (none made; `game1-next` untouched): the empty text is the engine's "BELT
   EMPTY - resupply from an ammo box" although no ammo box refills this gun; no dry click; the AI gunner's shots are
   not counted (reckoned in script); no getter for belt / heat, so the debug has only `mg left ... belt=`; the gun
   idles with its barrel 45 degrees up once nobody is on it. The body lies at the seat (not solid, a player mounts
   over it).
6. **Grease gun: not done.** Findings: `models/weapons/greasegun.tik` is in `zzzzz_xw_weapons.pk3`, name "M3 Grease
   Gun", `weapongroup xw_greasegun` - a PLAYER weapon; an actor given it has no animation set and falls to the default
   in `anim/reload.scr`. It needs an AI tik (the Thompson's `weapongroup thompson`, name "Thompson (M3 Grease Gun)" so
   every consumer strips to "thompson" - TRAPS, weapon variant suffixes - with the greaser mesh and sound), given with
   `coop_mod/aihandler.scr::coop_actorArm` after `gun "thompson"` (bug-3306: never `gun <tik>`). Roll it in
   `paradrop.scr` at `local.wtype == 2` (the Thompson man: never the BAR man or the gunner, three rifles remain).
7. **Tactical squad brain** ("they do sometimes brainlessly rush") and **landing without teleports**: not started.
   What this pass learned for them: a man in a nodeless 256 u cell cannot path (above) - that is the landed-and-stuck
   trooper; `walkOut` was seen to get such a man moving at least five times across the sessions (`walkout k=2 goal=1 left=13..45`) and found no
   walkable line in the m3l3 room (`goal=0`). On m5l1a a stick called at (3007, -3601, 188) came down on roofs at
   z = 404 and 584 and one level below; on m4l3 three of five landed 4000 u from the smoke and died. `paradrop.scr`
   picks no landing points before the jump. The reach test built here (`mgReach`) needs a living actor, so it cannot
   vet a landing point before the man exists - that would be the engine query.
8. Not seen in a session: the 15 s out-of-arc / masked re-site (the 8 s version fired once, a1), `coop_paraMgTripod
   1`, `coop_paraDebug 2`, a thin wall (5 u inset), cover that is not world geometry (refused by design: a vehicle
   bonnet or a pushable crate is not used).

Tools: `tools/pass2/` - `p2_run.py` (the sessions above; options in its header), `p2_drv.scr` (the driver), `p2_sweep.py`
/ `p2_grid.py` / `p2_flood.py` (where does a map have cover), `p2_strip.py` (walk-round of a prop), `build_scr.py` +
`frag_mg.scr` + `edit_*.py` (how the script was assembled; the mod file is the truth now).
