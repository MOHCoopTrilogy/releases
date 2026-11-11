# shootfix - "anim/shoot.scr took over 10 seconds" (bug-10935)

The server dropped every player with `anim/shoot.scr took over 10 seconds, entnum = N`.
Seen on Sealed Orders co-op (ent 227), m3l3 (ent 482, ent 818) and m2l3 (ent 120, the Norway entry).

## What the error is

Not a script watchdog. It is one line at the end of `Actor::State_Cover_Shoot`
(`fgame/actor_cover.cpp`): if the actor has been in `ACTOR_STATE_COVER_SHOOT` for more than
10 s (`level.inttime > m_iStateTime + 10000`) the engine calls `Com_Error(ERR_DROP)`. The original
source marks it `FIXME: debug build only?`. Two different things get an actor there.

## Cause B - a real script hang (reproduced on demand)

`anim/shoot.scr` sent any actor closer than `reallyshortrange` to `attack.scr::AttackDoMelee`, which
plays `<weapongroup>_butt` and then does `self waittill upperanimdone`. A weapon group with no butt
animation (bazooka on every rig; sten, moschetto, shotgun, vickers on the base-game rigs) logs
`unknown animation 'bazooka_butt'`, nothing ever ends, and the engine drops the server 10 s later.
In play: a Panzerschreck man in cover with a player inside arm's reach.

Fix (mod, `shootfix-mod` 47aff171): `attack.scr::AttackMeleeKind` says whether the weapon can club.
`shoot.scr` only takes the melee branch when it can; `AttackDoMelee` never waits on an animation that
may not exist (fixed 0.45 s follow-through for the groups that only some rigs have).

## Cause A - asleep is not shooting (log evidence, not reproduced on demand)

`Actor::RequireThink` stops an actor that no client has been sent for 60 s. One that falls asleep in
COVER_SHOOT keeps the state time of that burst; the first think after a player respawns or warps back
into his PVS finds it older than 10 s. The Sealed Orders and first m3l3 crashes sit right after a teleport / respawn with no `_butt` error
for that entity; the Norway record describes the same moment (finale warp). Two attempts to stage it (`--repro A`)
did not put a sleeping actor in COVER_SHOOT, so this one is fixed by construction only.

Fix (engine, `shootfix-eng` 902fa240): `Think_Cover` restarts the burst timer after a think gap over
1 s, and the `Com_Error` is gone - a shoot script that really is stuck now logs
`^~^~^ COVERSHOOT stuck ent=…` and sends that one actor back to FIND_COVER.

## Runs (m3l3 unless noted, harness, 1080p screen, muted)

| run | game.dll | anim scripts | scenario | result |
|---|---|---|---|---|
| ctl1 | release | release | 4-min patrol | CRASH at 161 s, ent 818 (`bazooka_butt`) |
| fix1-fix4 | fix | release | 4-min patrol x4 | no crash, 30-32 waypoints each |
| rB_ctl | release | release | repro B | CRASH 11 s after the first bazooka man |
| rB_eng | fix | release | repro B | no crash, `COVERSHOOT stuck ent=808 ms=10025` once, recovered |
| rB_mod | release | fix | repro B | no crash, no `_butt` error |
| rB_both | fix | fix | repro B | no crash, no `_butt` error, no stuck line |
| rA_ctl | release | release | repro A | no crash (scenario does not trigger cause A) |
| rA_eng | fix | release | repro A | no crash |
| both1 | fix | fix | 4-min patrol | no crash, 30 waypoints |
| both2 (m5l1a) | fix | fix | 4-min patrol | no crash, 3 waypoints (player died twice; short patrol) |

Logs: `H:\hzm_work\shootfix\runs\<tag>\qconsole.log` (local only).

## Runner

`tools/run_shootfix.py <tag> <map> [--control] [--min N] [--repro A|B] [--modfix]` - private install
`G:\mohaa-shootfix`, launches through `docs/tools/harness_window.py`, keeps to
`H:\hzm_work\display_queue.txt`. `--control` uses the release game.dll; `--repro` adds a test thread to
m3l3 through an overlay pk3 in the private home; `--modfix` puts the two fixed anim scripts in that overlay.

## Merge

1. Mod: merge `shootfix-mod` (47aff171) into `hotfix-1.10.53`. Script only; this alone removes cause B.
2. Engine: merge `shootfix-eng` (902fa240) into the engine release branch and rebuild `game.dll`. Removes
   cause A and makes any future stuck shoot script a log line instead of a server drop.
3. Root: merge `shootfix` (this folder).

## Open

- Cause A has no on-demand repro. If `COVERSHOOT wake` (developer print) shows up in a soak log, that is it firing.
- The 0.45 s follow-through for sten / moschetto / shotgun / vickers is a fixed time, not the animation length.
