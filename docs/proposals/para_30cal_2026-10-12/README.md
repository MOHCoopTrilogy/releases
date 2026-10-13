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

---

# ENGINE SIDE OF THE LEFT GUN (2026-10-12, engine `game1-next` `92944d37` + `277bdb9d`, on `integ-1.10.22` `a9a00da9`)

Handover item 5 above (`92944d37`, `fgame/weapturret.cpp` / `.h`), then round 2 (`277bdb9d` + mod `coop-wip`
`7ca17790`): bug-3639 fixed, and the player crouches behind a low gun - both at the end of this section.
**Not deployed, and `parasquad.scr` does not use the keys yet** - the lines below are for whoever edits that file. Nothing here changes a gun that does not ask: every key is off
(or at the MG42's numbers) by default, there is no cgame change and no new network field - the HUD reads the same
packed `STAT_MGHEAT` ("BELT n" + the heat bar). bug-3636..3639.

## The keys (ordinary TurretGun events: script, or the server block of a tik)

| key | what it does | default |
|---|---|---|
| `coopnoresupply 1` | the empty-belt line is **"Belt empty"** in the event feed (bottom left; cat 2 "self", key `mgbelt`), once per trigger pull. A cgame without the feed, or a Hardcore host, gets it as the centre print | 0 = "BELT EMPTY - resupply from an ammo box", centre print |
| `coopdrysound <alias>` | played from the gun once per trigger pull on an empty belt | none |
| `coopheatrates <heat> <bleed> <cool> <lock> [hot]` | heat per second of fire, bleed per second between bursts, cooling per second while cooked, seconds dead after a cook-off, heat per second firing while cooked (default 2.5 x heat). The bar is still 0-100 | `50 8 25 2 125` (the MG42) |
| `coopaibelt 1` | an AI gunner fires at the gun's own `firedelay`, each round comes off the belt, and at 0 the gun does not fire (whatever the tracker or a `startFiring` asks) | 0 |
| `cooprestpitch <deg>` | unmanned, the gun eases to this pitch (0 level, positive muzzle down) instead of dropping its butt | unset = retail butt drop |
| `.coopammo` `.coopheat` `.coopoverheated` | getters: rounds left (-1 unlimited), heat 0-100, 1 while cooked | |

No belted gun heats while the trigger is held on an empty belt (bug-3639, `277bdb9d`; in `92944d37` only a gun with
`coopnoresupply` or `coopdrysound`).

## Lines for `parasquad.scr`

In `mgSetup`, after `local.gun suppressHeight 40`:

```
	local.gun coopammo 250
	local.gun coopaibelt 1
	local.gun coopnoresupply 1
	local.gun coopdrysound "bar_snd_noammo"
	local.gun coopheatrates 40 8 25 2
	local.gun cooprestpitch 3
```

In `mgLeft`, instead of the reckoning from `local.fired` (the three lines that compute `local.n` / `local.left`):

```
	local.left = local.gun.coopammo
	if( local.left < 25 ){ local.left = 25 }
```

(`local.gun coopammo local.left` stays; drop the floor if an empty gun should be left empty.) `coop_psqMgFired` and the
11-rounds-a-second sum in `mgHold` are then dead. For the debug line: `local.gun.coopheat`, `local.gun.coopoverheated`.
While he is on it, `local.gun.coopammo == 0` is "he is out": the engine only stops the gun, what he does next (pack up,
or a new belt after a pause: `local.gun coopammo 250`) is the script's.

**Two things this changes for the gunner himself, both wanted but not yet tuned in script:**

- **His rate of fire drops from 40 to 10 rounds a second.** `TurretGun::AI_DoFiring` calls `Fire()` every server
  frame of a burst, and `Fire()` has no fire-delay test - an AI gunner's cyclic rate is `sv_fps` (40 live), whatever
  the tik says. That is what the second pass saw and what the script took for "11 rounds a second". True of every
  AI-manned turret, the maps' MG42 nests included; those keep it (they were tuned at it). `aibulletspread 300 300`
  was chosen at four times the rounds.
- **Heat.** An AI gunner cooks at a ceiling rolled 55-95 per burst; at 40 / s that is 1.4-2.4 s of fire. With
  `burstFireSettings 1.2 3.0 0.8 2.2` he cooked 5 times in 24 s (steam hiss, 2 s dead, then cooling to a rolled
  0-35). Shorter bursts cook less.

## Numbers chosen for the M1919, and what was measured

`coopheatrates 40 8 25 2` on the tik's `firedelay 0.09`: against the MG42's `50 8 25 2` on `0.06`. Same lock-out (2 s
dead, then it can be fired hot at 100 / s of heat against 25 of cooling, or left 4 s to go cold).

Harness `G:/mohaa-hudfeed3`, m3l2, the gun spawned by an overlay driver with `mgSetup`'s own lines on a sandbag-rest
site (gun 40 u up), left with `mgLeft`'s lines; values are the turret's getters every 0.1 s. Run a3 = everything below
with the committed code (`tools/engine_left/logs/result_a3.json`); "control" = the same gun with none of the keys.

| | with the keys | control |
|---|---|---|
| trigger held from cold | cooked after **2.5 s, 24 rounds** (9.6 / s) | 1.9 s, 19 rounds (10.0 / s) |
| after the cook-off | no round for **2.0 s** (heat 100 -> 50), then firing again while hot (heat pegged at 100, 10 / s); released: cold 3.9 s later | no round for 2.0 s |
| last round of a 10-round belt, trigger still held | heat 37 falling at 8 / s; one "Belt empty" feed line; three pulls = three lines | 3-round belt, held 3 s: heat **98.75** with the belt at 0 (bug-3639 - fixed in `277bdb9d`, below) |
| dry click | three pulls with `bar_snd_noammo`: no error. Three pulls with a made-up alias: three `Entity::Sound: ... needs an alias` errors - the sound call runs once per pull and `bar_snd_noammo` resolves (it is aliased for every map: `maps "m e t dm obj train lib moh"`). **Not listened to** | none |
| Hardcore host (run a2) | the centre print "Belt empty" (the feed draws only alerts there) | |
| unmanned | pitch **3.0** from spawn | **-45.56** (barrel up) |
| off the gun, looking 32.6 up | -20.9 -11.0 -5.2 -1.8 0.2 1.4 2.6 3.0 at 0.1 s steps (0.8 s) | |
| off the gun, looking 35.1 down | 31.1 19.5 12.7 8.7 6.3 4.9 3.7 3.0 (0.8 s) | |
| AI gunner, 24 s of the turret's own track cycle at three riflemen | belt 241 -> 158 = **83**, and **83** `FIREDBG SHOOT .30 Cal` lines; 10.0 / s inside a burst (before the firedelay gate, run a2: 158 = 158 at 40 / s) | not counted |
| AI gunner, belt set to 15 (script `startFiring`) | 15 shots, then none in 10 s; belt 0, heat 0 | |
| he is killed at it | pitch 3.0 within 0.5 s; `.coopammo` read 103; Use mounted the player, who fired 102 -> 88 | |

Stills (`media/`): `eng_rest_before.jpg` / `eng_rest_after.jpg` (unmanned, control and with the key),
`eng_after_death.jpg`, `eng_hot_hud.jpg` (BELT 225, the bar full), `eng_belt_empty_feed.jpg` ("Belt empty" in the feed,
BELT 0), `eng_belt_empty_hardcore.jpg` (the centre print), `eng_third_person.jpg` (item below).

## Not verified

- The click was never heard (the harness is muted); only that the call runs once per pull and the alias resolves.
- Nothing was run with `parasquad.scr` itself (it does not set the keys yet), on a second client, or on a dedicated
  server. Only m3l2, only the sandbag-rest height.
- An older `game.dll` with a script that sets the keys: not tried (each line would be an unknown command).
- In the rest stills the gun stands a little clear of the bipod's head; that is where `mgSetup` puts the two (gun
  +40, bipod +38.6), not something this pass moved.

## Round 2 (engine `277bdb9d`, mod `coop-wip` `7ca17790`)

### bug-3639: the trigger held on an empty belt heats no belted gun

The empty test is one branch in front of the heat branches now, for every belted gun. Measured on a retail
`models/statweapons/mg42_gun.tik` with `coopammo 300`, player on it, this build (runs c1, c2) against the previous one
(`92944d37`, run c0):

| | this build | previous build |
|---|---|---|
| trigger held from cold, rounds in the belt | cooked after 2.0 s, 31 rounds (15.5 / s) | 1.9 s, 30 rounds (15.8 / s) |
| after the cook-off | no round for 2.0 s; cold 9.0 s after it | 2.0 s; 9.0 s |
| belt 3, trigger held 3 s | heat peaked **7-8** (the three rounds) and fell to 0, no cook-off | heat **98.75**, cooked off |
| text | "BELT EMPTY - resupply from an ammo box", centre print | the same |

(1.9 / 2.0 s and 30 / 31 rounds are the 0.1 s sampling: run b1 of this build read 1.9 s and 30.) One difference in
when the text shows, by the code and not measured: it is now also sent while the gun is in its 2 s dead time after a
cook-off.

### bug-3658: a player on a LOW gun crouches behind it

**What decides "low":** the AI gunner's own test (`Actor::ThinkHoldGun_TurretGun`): crouch weight
w = (71.8 - h) / 33.1 for a gun h over the ground the man is held on, crouched at w >= 0.5 - a gun **under 55.25 u**.
Decided once per mount (`Player::EnterTurret` -> `TurretGun::CoopUserLow`). Coop missions only; never a vehicle or a
portable turret; `coop_turretCrouch 0` switches it off; `developer 1` prints `TURRETSEAT enter / exit`.

**What a low gun changes:** hull 54, view height 48 (put back exactly in `ExitTurret`), the AI's crouched seat
(62.4 - 3.0 w back and 10.3 - 1.6 w to the left of the gun, where the standing player is 64 back and 0 left), and
the condition `COOP_TURRET_LOW` for the state files.

**Where the pose really comes from - not the legs states.** The first report above was wrong, and so were bug-304 and
bug-309 before it: on a ground turret the legs states `COOP_TURRET_MAN` / `TURRET_USING` are never evaluated. The
torso state `TURRET_IDLE` is `movetype anim`, `Player::EvaluateState` runs the legs machine only under
`MOVECONTROL_LEGS`, and the debug line the engine already prints says so (`TURRETSTATE legs='STAND'`, once, and never
another). The whole body is the TORSO state's action row (`turret_idle` = the retail `mg42_stand_idle`), chosen once
on entering the state. So the mod commit has: the two aliases (`anims_shared.txt`), the crouched idle row in
`player_Torso.st` `TURRET_IDLE`, a new torso state `TURRET_FIRE_LOW` for the firing clip, and the crouch rows in the
two legs states as asked (dead on a ground turret, commented as such).

**Ship the mod commit and the engine together**: the state file names a condition an older `game.dll` does not have.
The other way round (new `game.dll`, old state file) was not run; by construction it gives the crouched hull and
seat with the standing clip.

Seen in engine (m3l2, run c2 = this build + the mod files, run c0 = the previous build + the deployed state files):

| | low gun (.30 cal, 40.1 u) | standing height (retail MG42 at 60.1 u; the map's own `scene7_mg1` at 61.9 u) |
|---|---|---|
| `TURRETSEAT enter` | `low=1 crouch=0.96 maxsz=54 view=48 psview=48` | `low=0 crouch=0.00 maxsz=94 view=82 psview=82` |
| seat | (-3651.642 2246.965) = the AI gunner's seat on the same gun in run a3, to the unit | the same origin as the previous build, to the unit (both guns) |
| third person | kneeling behind the gun, hands on it, front foot behind the bags; the firing clip with the trigger (before: upright, hands in the air over the gun) | the same frame as the previous build: mean absolute difference 0.0-0.1 of 255 (`scene7_mg1`, both sides) |
| first person | the same frame as the previous build (difference 0.5 of 255) | `scene7_mg1`: difference 1.0 of 255 |
| off it with Use | `TURRETSEAT exit maxsz=94 view=82 psview=82`, hull read back 94, walked away | hull 94 |
| the gun removed under him | exit 94 / 82 / 82, `turret=none`, hull 94 | |
| killed on it | exit 94 / 82 / 82, then the ordinary dead hull (32) | |

**First person needed nothing.** With `g_turretcameras 1` (the mod's setting) the view on a turret is the turret's own
camera, at the gun's origin + its `viewOffset` (-42 0 10): 50 u over the ground on this gun, looking along it, whatever
the body does. The crouched view height (48) is what the third-person camera and anything aiming at his eyes use.

**The 64 u hold distance:** on the crouched seat (59.5 u back for this gun) his front foot is clear of the bags in
the side stills (they reach 16.5 u back from the gun). Nothing sits inside them.

Stills (`media/`, all QA'd at full size): `eng_low_side_before.jpg` / `eng_low_side_after.jpg` (from his left, the
whole man), `eng_low_side_fire.jpg` (from his right, firing; the dark patch on the ground is in this frame only -
probably the muzzle flash's own shadow, not checked), `eng_low_first_person.jpg`, `eng_nest_side_before.jpg` /
`eng_nest_side_after.jpg` (the map's `scene7_mg1`). The side view is a test camera: a script `Camera` whose angles
point across the gun - in third person on a turret the client chases the player along the camera's angles.

**Not verified / to know:**

- **Map guns under 55.25 u now crouch the player too** - that is the rule as asked. m3l2 has two: `scene4_mg42`
  (38.9 u over the ground behind it) and `scene11_mg2` (54.9 u). Neither was mounted. The AI blends between the two
  poses by height; a player gets one or the other, so on a gun between about 45 and 55 u the full crouch puts the
  hands up to half a blend (some 15 u) under the gun.
- A second client watching him, a dedicated server, the pose after a map restart: not run. The pose is an ordinary
  player animation and an ordinary hull, nothing new goes over the wire.
- Leaving a low gun under a ceiling too low to stand under: not tried (he gets the standing hull back regardless).
- Test set-up in these runs: every actor on the map removed (friendly ones walk into the frame), the player made
  undamageable for the stills (something on m3l2 kills a man standing at `scene7_mg1` within seconds), the gun's
  traverse locked to 0 for the side views (the gun follows the test camera's angles otherwise).

Tools: `tools/engine_left/` - `lg_run.py` (round 1), `lg_run2.py` (round 2: `c2 new`, `c0 old mg42,nest,low`),
`lg_drv.scr`, `lg_lib.py`, `patch_lowgun_mod.py` + `patch_lowgun_torso.py` (how the mod files were edited),
`logs/result_c2_new.json`, `logs/result_c0_previous_build.json`.

---

# THIRD PASS (2026-10-12, mod `coop-wip` `cd54b05a` + `8ade3c9c` + `fd54ab32`) - and the HANDOVER

Not deployed. Mod only (three commits); the engine side is the section above (game.dll `4fbcc3b9`, `game1-next`).
Scripts: `coop_mod/parasquad.scr`, `coop_mod/paradrop.scr`, new `coop_mod/parasquad_gun.scr`, new
`models/weapons/coop_greasegun_ai.tik`, one line in `coop_defaults.cfg`. bug-3686..3695.

User, all still binding: "go to the nearest existing cover he could prop it to with a bipod and suppress enemies or
place the sandbag", "make the paratroopers be more sentient and aware, they do sometimes brainlessly rush. Make them
tactical and extremely realistic", "we had to make it so they teleport if they get stuck or fall off map.... how can we
refine that without them teleporting at all or as much", "sometimes the paratroopers should spawn in with grease guns
too", "no jank".

## What changed, in plain words

**1. Why they rushed, and what holds them now.** Every trooper had a 640 u leash that was reset to wherever he stood -
by the script on every order, and by the engine itself on every new enemy (`Begin_Cover` -> `SetLeashHome`). It never
held anyone: on m3l2 the squad ended 1000 u past the hold point. Now every man has a POST: his leash is tethered (the
engine's own `tether` - `Actor::Think` puts his leash home on the tether entity every frame) to a point the squad brain
moves, with a 170-240 u leash. The engine's cover and turret thinks only path, hunt and take cover nodes inside the
leash (`SetPathWithLeash`), so the post is where he fights. `maxdist` is 3000 (an American whose enemy is beyond
`maxdist` always charges; the "hold at your leash" branch is German-only). `resetleash` is gone (it clears the tether).

**2. Fire and movement** (`brain`, CONTACT): the wedge turns to face the enemy and stays beside / behind the players;
a man past them toward the enemy comes back. A BASE OF FIRE is the .30 cal with the enemy in its arc, else the BAR man
with a line to him, else two riflemen with one - with no base of fire nobody moves up. With one, the men who are behind
their place bound one fire team at a time, 300 u at most, to cover (`coverNear`: low cover he can fire over first, a
corner second; never a doorway, a mate's spot or a player's muzzle), while the gun fires bursts for the move and the
others suppress. A man in plain view goes to cover (crouched) and his post goes with him; with none in reach he gets
small. PINNED (hit in the last 4 s): he stays down, no orders. MAN DOWN: 6 s nobody bounds, everybody in view takes
cover. On first contact everybody in view looks for cover at once. LANES: a man in front of a player's muzzle steps
out of it (in a fight, or while the player fires), and out of the .30 cal's. Room clearing only with a base of fire;
the Thompson and the BAR go in, the man with the gun on his back last. Grenades: `gren_awareness 90` (the engine's own
grenade think gets a man away; default was 20 %). The medic's leash is tethered behind the players.

**3. Landings.** `paradrop.scr::coop_para_lz` picks five landing points while the C-47s are inbound, nearest the smoke
first: ground at the squad's level, open sky over it and 44 u round it, level, room for a man, dry, 110 u apart, out of
the enemy's sight where that can be had - and connected: a scout (an actor nobody sees, not solid, ignored by the enemy,
physics off) is stood on each point and ordered to the smoke; his `pathdist` is the engine's own answer. Each canopy is
steered onto its point (over it by 450 u up, then straight down). The stuck / off-map teleport is a last resort: only
for a man who fell out of the world, or whom the brain reports LOST - two orders, then two straight walks (`walkOut`,
which now also walks him back onto the network: his landing point, else a mate) went nowhere AND he has no path to
his landing point, a mate or the anchor (`onNet`). The place he is put is looked at and path-tested with the man
himself (`coop_paradrop_rescue`). The old failsafe moved any man who was 700 u from a player, idle and not closing
for 8 s, onto ground nobody had looked at.

**4. Grease gun.** In `coop_paraGreaseChance` percent of the drops (seeded 50 in `coop_defaults.cfg`, 0 = never) the
squad's SMG man (member 2 - never the BAR man or the gunner) carries an M3. `models/weapons/coop_greasegun_ai.tik` is
the players' `greasegun.tik` with the name "Thompson (M3 Grease Gun)" and `weapongroup thompson`, so an actor has
animations for it. Generator: `tools/pass3/make_grease_tik.py` (`--check` passes).

**5. The .30 cal.** Level when nobody aims it (it tipped 13 degrees barrel-up during the set-down and stayed there -
that is why the crouched gunner's hands were "at his face": the grips had sunk 10 u under them); pitch held to 12
degrees either way and sites planned for that; a WATCH (level, down his arc) instead of the engine's default position,
whose pitch follows the first player; the engine keys through `parasquad_gun.scr` (a file of its own, so an older
game.dll loses only that file): 10 rounds a second, bursts of 5-9, cone 150, he stops at 45 heat and lets it bleed
(70 while the squad bounds on his fire), a second belt after 4 s, belt out = pack up and stay a rifleman, a gun he
dies at keeps what was on the belt. The gun sits LOW on its rest: bipod prop drawn at 0.75 (12.8 u, a real M1919A6
bipod is 12 in), bag stack at 1.2 (25.8 u), gun 13.5 u over the top bag (was 17.8) and still 39.3 u over his ground,
which is what his crouched pose is made for. The planner owns its man from the start of a search (a bound order that
began during it pulled him off the walk-up); with no site that sees the enemy himself it takes one that covers the
ground toward him; a man a floor below the muzzle is not "in front of it"; the gun does not pack up for "enemy
masked" while it has fired in the last 20 s; a site he did not reach is not planned again for 60 s.

## Shown in the harness (G:/mohaa-hudfeed5, game.dll 4fbcc3b9, real C-47 sticks, 0 script errors in every session)

Said plainly, the test set-up that is NOT the game: the "player" the squad anchors on is a fixed hold point at the
call spot (`pin`) and the real player is the camera, parked near by, notarget, no damage; where it says `bring`, the
gunner was stood in a room that has no pathnodes; where it says `purge`, the map's Germans were removed; where it says
"test burst", the driver made the gun fire for the picture.

| item | map, set-up | what happened |
|---|---|---|
| sandbag site, unassisted, the map's own Germans | m3l2 yard, nothing placed, normal health (runs s5, s6, g1) | landed on tested points, gunner planned a bag site, path walks of 287 / 215 / 203 u, set up crouched, tracked and fired bursts at the Germans in the upstairs windows 650-1000 u off (`mg track`, 2-5 `mg suppress` a run), held his fire for a mate in front, packed up when the squad moved on. GIF `p3_sandbag_m3l2_setup_fire_packup.gif` |
| cover site, unassisted, the map's own Germans | m4l3 (runs a5, a6) | a6: cover 46 u high, set up standing at t=72 s, stayed. a5: four bag set-ups, then cover 48 u high and a burst from it (`mg setup k=1 mode=A ... top=48.001`, `mg suppress` 5 s later). **Log only - no picture of a cover site firing at real enemies** |
| cover site: a window sill, 48 u | m3l3, `bring` + `purge` (g3, g4, k3) | set up, hands on the gun, packed up. No enemy in his view in three tries, so no fire of his own there; side stills with a test burst. GIF `p3_cover_sill_m3l3_setup_packup_nofire.gif` |
| crouched cover site | m3l3, unassisted (c1, before the gun was lowered) | cover 22.7 u high, set up crouched. With the lower gun cover under 24.7 u is refused now; a crouched cover site (24.7-35 u) was **not run again** |
| hands / stock / bipod | m3l2 bags, m3l3 sill | level gun: crouched hands at the rear of the receiver (were 10 u above it), bipod feet on the top bag / the sill, gun in the yoke, nothing floating. A gun pitched 12 degrees at a high target still has the grips ~8 u from his hands (engine: his pose does not follow the pitch) |
| a player on the left gun, and on low map guns | m3l2 (k1, k2), m3l3 (k3) | kneels behind the bag gun, hands on it; stands at the sill gun. m3l2's `scene4_mg42` (38.9 u) and `scene11_mg2` (54.9 u): mounted, kneeling, stills. The "rod" of `eng_low_side_after.jpg` is not in any of these (it was the engine test's own stray MG42) |
| grease gun | m3l2, chance 100 (q1) | the M3 in member 2's hands, carried, aimed |
| landings and teleports, raw counts, one run each | | see the table below |

### Numbers (one run each - these are single runs, not statistics)

"far" = how far the farthest of men 1-4 is from the hold point, averaged over the run. "in view" = man-seconds a
standing trooper was in clear line of an attacking German within 1600 u. Before = mod `8a35ddcd`; after = this pass.

| map | | landings off the ground level | teleports / rescues | men lost | squad health left of 3200 | far avg (max) | in view |
|---|---|---|---|---|---|---|---|
| m3l2 yard | before (s1, s2, b2) | s1: one on a roof (+349), two in a sunken lane with no pathnodes | 5, 2, 3 | 0 | 3101 / 3117 / 3104 | 749 u (1014; b2) | 3.0 / 17.3 / 6.8 s |
| m3l2 yard | after (s5-s8, g1, a2, q1, k1, k2) | none: all 45 landings within 3.1 u of their points, 119 u from the smoke | 0 in every run (k1: 2 medic rescues caused by the test's player jumping 8000 u; that rule is fixed) | 0 | 3200 | 206 u (565) | 10.5 / 5.0 s |
| m5l1a | before (b3) | two on roofs (+407, +284) | 1 | 1 | 2562 | 416 u (1124) | 16.3 s |
| m5l1a | after (a3, then a4 with landing points out of sight) | none | a3: 0; a4: 1 rescue (a man one map cell from his landing point in a cell with no pathnode; `walkOut` now walks him back) | a3: 1; a4: 0 | 2550 / 3200 | (hold point is on a ledge above the street) | 34.5 / 18.0 s |
| m4l3 | before (b5) | one on a roof (+692) | 7: the whole squad was teleported 5700 u to the test's player | 0 | - (left the fight) | - | - |
| m4l3 | after (a5, a6) | none | a5: 1 medic rescue (test's player 5700 u away; rule fixed after); a6: 0 | 0 | 2547 / 3200 | 244 / 312 u | 47.5 / 10.5 s |
| m3l3 | before (b6) | one on a roof (+442) | 1 | 0 | 3200 | - | - |
| m3l3 | after (a7, a8) | none | 0 | 0 | 3200 | - | - |

The "in view" number did not improve everywhere (m5l1a a3 was worse than before: all five landed in the fight, where
before two sat on roofs): that is what the out-of-sight landing points and cover-at-once were added for; a4 is after.

## Media of this pass (`media/p3_*`)

- `p3_sandbag_m3l2_setup_fire_packup.gif` - finished. Walk-up, bags, bipod, gun, bursts (muzzle flash), pack-up; m3l2, the map's Germans, unassisted.
- `p3_cover_sill_m3l3_setup_packup_nofire.gif` - set-up and pack-up at the window sill; NO firing in it (see above).
- `p3_clean_sandbag_ai_side_idle / _side_fire / _rear_fire / _side_tele.jpg`, `p3_clean_sandbag_player_side_idle / _side_fire / _side_left / _front.jpg` - the final bag set-up from the side: AI gunner and a player, idle and firing (AI: test burst). `purge`, nothing else spawned.
- `p3_clean_cover_sill_ai_side_idle / _side_fire / _rear_fire.jpg`, `p3_clean_cover_sill_player_side_idle / _side_fire / _side_left.jpg`, `p3_cover_sill_m3l3_tele.jpg` - the same at the sill (`bring`, `purge`).
- `p3_left_gun_rest.jpg` - the gun he died at: muzzle 3 degrees down, bags, can.
- `p3_sandbag_m3l2_firing_real_enemies.jpg` - a burst at the map's own Germans (frame of run g1).
- `p3_m3l2_scene4_mg42_player_side.jpg`, `p3_m3l2_scene11_mg2_player_rear.jpg` - a player on m3l2's two low map guns (the second from behind: its sandbag nest hides him from the side).
- `p3_greasegun_m3l2_front / _side / _aim.jpg` - the M3.
- `p3_tactics_m3l2_before_after_tracks.gif`, `p3_tactics_m5l1a_before_after_tracks.gif` (+ `_still.jpg`) - before | after, **plotted from the positions the driver logged, not game captures**. An overhead game capture of "before" is not possible: the old failsafe teleports the squad to a camera hanging in the air (run b1: 127 teleports).

## NOT done / not verified - the handover

1. **No picture of the gun firing from a COVER site at real enemies** (log only, m4l3 a5). A crouched cover site was
   not run with the lowered gun. Recipe: `p3_sess.py <label> m4l3 699 -1128 -70 90 gun=1 firewait=60` and wait for a
   `mode=A` set-up (a6 got one at t=72 s).
2. **Second client: not run.** Everything is server-side script on ordinary entities.
3. **The tactical GIF is a plot.** No in-game before / after GIF (see media). The numbers are single runs.
4. **Gunner and grenades.** A mounted gunner does not react to a grenade (`type_grenade "machinegunner"`, the retail
   recipe); leaving the gun for one and coming back needs either an engine getter for "a live grenade near me" or a
   re-man path in script. Not started. The others use the engine's own grenade think (`gren_awareness 90`); not seen
   in a session (no German threw one).
5. **Not seen in a session:** `tac mandown` beyond its debug line (one death, a3), a room clear under the new rules
   end to end, the second belt / `belt_out`, the `barrel_hot` hold (he never reached 45 heat in these fights), a
   rescue for "fell", the medic's new stuck rule, `coop_paraGreaseChance 0`.
6. **Hands at a pitched gun.** At 12 degrees of pitch the grips are ~8 u from the gunner's hands; his pose does not
   follow the gun's pitch (engine, `Actor::ThinkHoldGun_TurretGun`). A real fix is engine-side.
7. **A hold point the squad cannot reach** (a ledge, a room with no pathnodes: m5l1a, m3l3): the squad fights from
   the nearest ground it can reach; the wedge slots are refused when they are a floor away. The medic's leash point
   is then unreachable too.
8. **Stances.** `coop_paraCrouch` / `coop_paraProne` are read by `anim/attack.scr` when it starts a leg; a man told to
   "get small" does so at his next attack leg, not at once. "in view" above counts him as standing until then.
9. **Docs:** `docs/TRAPS.md` is at its ceiling (70 / 70 KB) and `docs/OPEN.md` over it (51 / 50); nothing was added.
   Two lines that belong in TRAPS when someone prunes: *an actor's leash never holds unless it is tethered or fixed -
   the engine re-homes him on every new enemy, and `resetleash` clears a tether*; *a "no progress" test on the
   straight distance to the goal stalls falsely on any path that leads round something - test that he is moving*.
10. **Engine asks:** none blocking. Useful: a script getter for the current TurretGun AI state / "is firing", and a
    path-exists query that needs no actor (the scout does it today).

Tools: `tools/pass3/` - `p3_sess.py` (one metered session; options in its header), `p3_mount.py` (side stills, a
player on the guns), `p3_grease.py`, `p3_drv.scr` (the overlay driver: cameras, meter, positions), `p3lib.py`
(harness glue; the binaries are read from the session scratchpad: `built_integ7`, `built_leftgun`), `tracks.py`
(the plots), `scan.py` (the project's parse scanners on single files), `edits/ed1..ed16.py` + `edlib.py` (how the
scripts were changed; the mod files are the truth), `logs/run_*.txt` (every session quoted above).

---

# FOURTH PASS (2026-10-12 / 13, mod `coop-wip` `b8c330ff` + `e277c9bb` + `60bc2ca7` + `237adcc2`) - and the HANDOVER

Not deployed. **Mod only, no engine change**: `coop_mod/parasquad.scr`, `coop_mod/parasquad_gun.scr`,
`coop_mod/paradrop.scr`. Game DLL used: `built_integ7/game.dll` md5 `6b515fbf` (harness name `game_p4`), unchanged.
bug-3746..3754. User, new and binding: **"when no one is using that 30 cal it should be facing upward"**.

## What changed, in plain words

**1. Hands on the grips under pitch (`mgPivot`).** The third pass had this wrong: the engine's pose DOES follow the
pitch - it holds the hands 39 u behind the pivot on the gun's pitched line and blends stand / crouch to reach them.
But the crouched pose is the floor (hands 38.7 u over his feet), and a gun 39.3 u high pitched up takes its grips under
it: 8 u at 12 degrees, 13 u at 20. Now, every frame while somebody is on the gun, the gun is lifted by what is missing
(7.2 u at 12, 12.2 u at 20, 15.3 u at 25): he raises the muzzle with the grips where they are, and the bipod, fast to
the barrel, comes off its rest with it. Pitched down, or on a gun high enough for the blend (a sill), nothing moves -
the engine's pose follows by itself. Script only: it works on an older game.dll too. `pitchCaps -25 / 12` (was 12 / 12);
the planner takes targets up to 22 degrees up; a mate up to 27 degrees above the muzzle counts as "in front of it".
A PLAYER has one crouched clip and no blend: on the lowest guns (the bags) the gun follows him both ways (up to 9 u
down: the bipod's feet press into the bags).

**2. The unmanned gun lies back on its butt (`mgRest`, `mgRestSet`, `mgMount`).** The pitch at which the underside of
the gun (pivot to the stock's lowest corner: 63.4 u back, 8.2 u under the bore, `tools/pass4/gun_profile.py`) meets the
world: **30 degrees on the sandbags, 44 on a 48 u sill** (there the receiver meets the sill's near edge; the butt
hangs ~12 u over the floor), 60 at most. The engine's own drop is not used: it tests a point 56 u back on the bore
line and buries this model's stock 11 u in the ground. `cooprestpitch` (eased, ~0.6 s) through
`parasquad_gun.scr::rest`; `maxIdlePitch` on an older game.dll. The bipod stays planted. **The tip only exists while
nobody holds it**: the gun is level for the whole set-down (its butt would come down where he stands) and before a
trooper takes it; a player's Use snaps it to his view in one frame, as on every MG42 in the game (`P_SetTargetAngles`;
read 0.4 s after Use: pitch 0.0). It goes back to its rest when he dies, packs up, or a player gets off.

**3. Grenades (`nadeWatch`, `mgFlee`, `nadeRun`, `mgGiveUp`).** One thread a squad looks through the entity table (64
slots a frame) for a projectile at rest within 300 u of a man. The mounted gunner lets go, gets 300 u away over
looked-at ground, waits for it, walks back - the gun is levelled before his last steps, its stock lies where he
kneels - and takes it again; a gun he cannot get back to, or that a player took, is the players' and he stays a
rifleman. A man on foot runs. The squad's own grenade, for 6 s, only moves a man it came back to within 150 u.
(In the harness the engine's own grenade think, `gren_awareness 90`, did not move a man on foot.)

**4. Landings where there is no path network (`coop_para_lz`).** A man without a path-connected point gets one that
passed everything else. m2l1's first road: before, `lz plan n=0`, four of five on the cliff tops (154-662 u up), one
rescue teleport; after, five landings within 8 u of the call height.

**5. Two rules found by accident.** A spectator is not the squad's "nearest player" (a man 1200 u under a flying
player read as "fell out of the world": 18 teleports in 45 s with the test's player 3000 u up). The seat of an
unmanned gun is kept free (`mgSeatClear`): a mate standing on it made a player stand upright behind the sandbag gun.

## Shown in the harness (G:/mohaa-hudfeed5, game.dll 6b515fbf, real C-47 sticks)

Test set-up that is NOT the game, as before: the squad's anchor is a fixed hold point (`pin`), the player is the
camera (notarget, no damage). `purge` = the map's Germans removed; `bring` = the gunner stood in the pathnode-less
room; `aimp` / `pcap` = the test aims the AI gun / pins the pitch of the gun a player is on; `fireon`, `mbelt`,
`nade` = the test makes it fire, cuts the belt, lays a stick grenade; `others` = the rest of the squad hidden.

| item | map, set-up | what happened |
|---|---|---|
| pitch, AI, bags | m3l2, `purge`, `aimp` (t7) | 0 / +12 / +20 (+ firing) / +25 / -10: hands on in every side still; gun lifted 7.2 / 12.2 / 15.3 u |
| pitch, player, bags | m3l2, `pcap` (t7) | kneeling, hands on at 0 / +12 / +20 (+ firing) / +25 / -10 (gun 6.8 u down); grips up to 2.4 u ahead of his hands at 20 (his seat is flat behind the gun) |
| pitch, AI, sill 48 u | m3l3, `bring` `purge` (u2) | hands on at 0 / +12 / +20 / +25, he goes lower by himself (engine blend); no lift |
| pitch, player, sill | m3l3 (u2) | **hands ~10 u over the grips at 0, more pitched up - as before this pass** (item 1 below) |
| rest | m3l2 (t7), m3l3 (u2) | -30 on the bags, butt on the ground, bipod on the top bag; -44 on the sill; after the gunner's death and after a player got off |
| the take | m3l2 (t7) | gun level through the set-down, he kneels onto it; GIF |
| barrel hot | m3l2 `fireon` (e1); m4l3 unassisted (c2) | e1: stopped at 45.4 heat, bled to 12 in 4.5 s, fired again. c2, a real fight: two `barrel_hot` holds |
| belt | m3l2 `mbelt` (e3, e4) | 12 rounds: `mg newbelt`, silent 4 s, 250 again. 10 rounds, no belt more: `leave why=belt_out`, pack-up, no new site in 15 s |
| grenade, mounted gunner | m3l2 `nade` 110 u (e3, e5); m4l3 unassisted (c2) | e3 / e5: he and the men within 300 u ran, it went off, he came back, `back=1`. c2: a grenade came to rest 90 u from him in the fight - left, back on the gun 8.4 s later |
| room clear | m3l2 unassisted (r1) | two: `clear stack` -> `enter` -> `done` (one `timeout`, one `cleared`). **Not looked at on camera**; who went through the door first was not measured |
| player far away | m3l2 (e5) | 8000 u away at the squad's height, 45 s: 0 teleports, 0 rescues |
| walkOut | m4l3 r2 (1), m5l1a r3 (8), f3 (6), m3l2 f1 (1) | every one `goal=1 lost=0`, no rescue. On m5l1a one man walked out 8 times in 30 s - the slot he is sent to has no path |
| cover under 24.7 u | all maps | `refused: height=` 4 (m3l2), 20 (m4l3), 26 (m5l1a) in the plan lines. **No crouched cover site (24.7-35 u) came up in any run** |
| cover site firing | m4l3, only cover sites planned (`force A`), else unassisted (c2, c4) | wall 46-48 u, standing; c4: walk-up at t=112, track and bursts, pack-up; GIF. Unforced (c1) he took the bags there |
| older game.dll | m3l2, `game_ship` 689d0db1 (o1) | `parasquad_gun.scr` does not compile (1 compile error + 4 "not properly loaded" lines, by design), `parasquad.scr` has none; set-up, `mg suppress`, gun lifted 5.1 u at 8.4 degrees up, pack-up, 0 teleports, 5 alive 3200 hp. Its rest (maxIdlePitch) was not looked at |

### Regression, final commit `237adcc2`, one drop a map, the map's own Germans, 165 s

| map | script errors | teleports / rescues | alive, health of 3200 | from the hold point at the end | landings |
|---|---|---|---|---|---|
| m3l2 (f1) | 0 | 0 / 0 | 5, 3080 | 95-173 u | all at ground level |
| m4l3 (f2) | 0 | 0 / 0 | 5, 3200 | 110-232 u | within 18 u of the call height |
| m5l1a (f3) | 0 | 0 / 0 | **0 - all five killed by t=165** (the first man as the fight began, script time 86 s; then 129, 152, 155 s and the last before the end; 18 Germans) | - | on the street below the ledge |
| m2l1 (f4), at the players' spawn, no enemy near | 0 | 0 / 0 | 5, 3200 | 118-427 u (no path network: they stay where they land) | within 8 u |

One commit earlier (`e277c9bb`: r1 m3l2, r2 m4l3, r3 m5l1a): 0 errors, 0 teleports, 0 rescues; alive 5 / 5 / 4, health
3200 / 3137 / 1830. Single runs; on m5l1a the squad fights 17-18 Germans alone (the test's player does not fight).

## Media of this pass (`media/p4_*`)

- `p4_pitch_sandbag_ai_side.jpg` - finished. AI gunner at 0 / +12 / +20 / +20 firing / +25 / -10, from his left (t7).
- `p4_pitch_sandbag_player_side.jpg` - finished. A player on the left gun, same angles, from his right (t7).
- `p4_pitch_sill_ai_side.jpg` - finished. AI at the 48 u sill, 0 / +12 / +20 firing / +25 (u2).
- `p4_pitch_sill_player_side_OPEN.jpg` - evidence of the open item: a player at the sill, hands over the gun (u2).
- `p4_rest_unmanned.jpg` - finished. The gun at rest: bags from the side and from behind, the sill. The dark patch on the ground in the bag stills is the blood of the gunner the test killed.
- `p4_take_ai_sandbag_setdown_level_take.gif` - evidence, not a showcase: bags, bipod, can, gun (level), he kneels onto it; squad mates in the background (t7).
- `p4_rest_after_player_gets_off.gif` - short: the player gets off, the gun lies back (t7).
- `p4_cover_wall_m4l3_walkup_fire_packup.gif` - finished, with two things to know: m4l3 is a night map (dark), and a squad mate fires from beyond the wall left of the gun's line. Walk-up, bipod on the wall, bursts at the map's Germans, pack-up (c4).
- `p4_grenade_m3l2_frames.jpg` - evidence sheet, not finished media: the squad scatters, the blast, the gunner walks back and takes the gun (e3). A man runs past the camera in the first frames.

## NOT done / not verified - the handover

1. **A player on a mid-height gun (45-66 u: every cover site above ~31 u of cover).** One clip, no blend: crouched
   under 55.25 u, standing over it; at the 48 u sill his hands are ~10 u over the grips, and pitching up takes the
   grips further away. Not changed here. Script cannot fix it without lifting the gun 10 u off the sill at level.
   Engine: a player pose that follows the gun height. **Choice for the user** (below).
2. `mgSeatClear` never fired in a session (no mate stood on the seat in t7): not shown by a positive case.
3. A crouched cover site (24.7-35 u); a second client; a dedicated server; a real spectator; the click by ear.
4. Room clear: counted in the log (r1, f2), not filmed, and "no man through a door ahead of the players" not measured.
5. m5l1a: the squad alone was wiped out in f3. Not looked into (attrition from the first second; no single event).
6. Old game.dll: the unmanned rest by `maxIdlePitch` was not looked at.
7. The grenade test lays a grenade and calls `ai_event grenade`; a thrown one was only seen once, by chance (c2).
8. The in-game before / after tactics GIF of the third pass: still a plot.
9. `docs/TRAPS.md` / `docs/OPEN.md`: at their ceilings, nothing added. Candidates: *a TurretGun's unmanned butt drop
   tests the bore line 56 u back, not the model - a stock that hangs lower is buried*; *the engine's gunner pose
   follows pitch (hands on the pitched line), its floor is the crouch pose at 38.7 u*; *with a script camera cued the
   client's command angles follow the camera: a test cannot pitch a player's turret, pin its pitch caps instead*.

**Disk:** G: ran full twice. Nothing was deleted. The run folders of `G:/mohaa-hudfeed5/runs` and of this pass (107 folders, pass 2 / 3 / 4, about 3.9 GB of frames, logs and json) were moved to the session scratchpad `...\scratchpad\_delete_me\para\` (the coordinator moves that on to `H:\hzm_archive\para\`); `p3_c1` is in `H:\hzm_archive\para\` already. `G:/mohaa-hudfeed5/runs` is empty. `tools/pass4/p3lib.py` writes new runs to `<its folder>/runs`.

Tools: `tools/pass4/` - `p4_pitch.py` (pitch / rest / take stills, AI and player), `p4_ev.py` (hot, belt, beltout,
nade, nadefoot, far), `p3_sess.py` (+ `here`, `force=A`), `p3_drv.scr` (+ aimp gst mbelt nade others nocorpse pcap
paim hurt), `p3lib.py` (game DLL by `GAMEDLL=`: `game_p4` default, `game_ship` = the older one), `regsum.py`,
`gun_profile.py`, `mkgif.py`, `edits/` (ed17-ed20 = the script edits, fix_* = the test tools), `logs/run_*.txt`.
