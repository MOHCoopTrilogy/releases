
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
| m3l2 yard | before (s1, s2, b2) | s1: one on a roof (+349), two in a sunken lane with no pathnodes | 5, 2, 3 | 0 | 3117 / 3104 | 749 u (1014) | 17.3 / 6.8 s |
| m3l2 yard | after (s5-s8, g1, a2, q1, k1, k2) | none: all 45 landings within 2 u of their points, 119 u from the smoke | 0 in every run (k1: 2 medic rescues caused by the test's player jumping 8000 u; that rule is fixed) | 0 | 3200 | 206 u (565) | 10.5 / 5.0 s |
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
