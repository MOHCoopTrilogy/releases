# e1l4 Respawn-Loop / Team-Select Root Cause

Investigation date: 2026-06-23. All file:line refs are from
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`. Live log:
`C:\Users\curry\AppData\Roaming\openmohaa\maintt\qconsole.log`.

---

## TL;DR

The repeated server re-spawn on **e1l4** is **NOT** a generic coop team/spawn-routing
bug. It is the e1l4 **stealth "show-your-papers" gate auto-failing the mission**, which
calls `coop_mod/replace.scr::missionfailed` -> `coop_mod/main.scr::restartMap`, reloading
the map (`e1l4$`). This is exposed by the **Phase 2 maptest harness** (`coop_maptest 2`),
whose patrol-tour teleports the lone test "player" away from the intro truck while the
papers gate is live and never presents papers, so the gate's `KillPlayerIfFailPapers`
watchdog fails the mission on a timer. The map then restarts forever because every fresh
load re-arms the same papers gate and the bot never satisfies it.

The "MP team-select screen" the user saw is the **downstream symptom**: each
`restartMap` -> `SV_SpawnServer` bumps `sv.serverId`; the client's `serverId !=
sv.serverId` so the engine (`sv_client.c:2103-2114`) drops + resends gamestate
("dropped gamestate, resending" / `SV_SendClientGameState()`), and because the restart
fires before the client settles into a team, the client lands back on the team menu.

This is **e1l4-specific** (it is the only remaining stealth/papers mission in the rotation),
but the *class* of bug — a scripted `missionfailed`/auto-kill path that triggers under the
unattended maptest — can recur on any map with a mid-level fail condition.

---

## 1. The normal (WORKING) coop team-assign + spawn flow

A map's `main` calls `waitthread coop_mod/main.scr::main` (e1l4.scr:15), which threads the
per-frame player manager `player.scr::manage` (main.scr:105) and wires the engine
`playerspawn` bridge via `events.scr::initialiseEvents` (main.scr:118).

Team auto-join (no team-select menu) works like this:

1. **`player.scr::manage`** loops every server frame (player.scr:42). For a player on the
   `spectator` team it calls `manageSpectator` (player.scr:54-55).
2. **`manageSpectator`** (player.scr ~745-751): when the spectator holds primary fire
   (`local.player.primaryfireheld`), it calls
   `coop_mod/main.scr::skipTeamAndWeaponSelect`.
3. **`skipTeamAndWeaponSelect`** (main.scr:296-334) is the auto-join: it sets
   `primarydmweapon "rifle"` (fills `dm_primary` so the engine stops re-pushing the weapon
   picker — main.scr:310-316), then `join_team "allies"` with `g_teamswitchdelay 0`
   (main.scr:319-322), and dismisses the menu with staggered `popmenu 0` stufftexts
   (main.scr:324-325).
4. On the resulting engine `playerspawn`, `events.scr` -> `main.scr::playerSpawnEvent` ->
   **`player.scr::manageAliveSpawning`** (player.scr:790). It first-time-inits via
   `manageSetup` (sets `coop_isActive=-3`, player.scr:189), then **forces a valid team**:
   `if( local.player.dmteam == "spectator" || thread coop_mod/main.scr::forceValidTeam )`
   (player.scr:802). `forceValidTeam` (main.scr:284-292) threads `forceTeam` if the player
   is on `axis` and returns 1 to abort+`resetSpawn` for that frame.
5. Once on allies, `manageAliveSpawning` runs the spawn placement
   (`playerPlaceAtSpawn`, player.scr:821, or `manageAliveRespawning`, player.scr:818),
   gives inventory/health/glue/FOV, sets `coop_isActive=1` / `coop_isAlive=game.true`, and
   fires `coop_playerJustSpawned` / `coop_playerJustRespawned` (player.scr:819/822).

`replace.scr::waitForPlayer` (replace.scr:99) is the map-side gate that blocks the level
script until `level.coop_playerReady == 1`; in SP it degrades to `level waittill spawn`.
e1l4 calls it at e1l4.scr:60.

**Maps 1-36 toured fine** because none of them auto-fails the mission, so this flow runs to
`coop_isActive=1` and the map never restarts the server.

---

## 2. Why e1l4 deviates: the smoking-gun chain

### 2a. The repeated re-spawn is `restartMap`, not a maptest advance

The maptest advances to the NEXT map with a clean `map <next>` via
`coop_maptest_transition` -> `stuffsrv("map " + local.next)` (maptest.scr:160 /
maptest_phase2.scr:252). That would log `Server: e2l1` (the next map). Instead the log
shows the SAME map reloading with a trailing **`$`**:

```
1896  23:40:19  Server: e1l4          <- maptest advance e1l3 -> e1l4 (clean)
3299  23:41:03  Server: e1l4$         <- RESTART  (~44s later)
4726  23:41:58  Server: e1l4$
5046  23:43:37  Server: e1l4$
5328  23:45:52  Server: e1l4$         <- never advances to e2l1
```

The `$` savepoint suffix is appended by **`restartMap`** (main.scr:1488-1494):
```
local.mapname = getcvar "mapname"
...
else{ local.mapname = (local.mapname+"$") }       // main.scr:1491
thread loadMap local.mapname game.true            // main.scr:1494
```
So the loop is `restartMap` firing over and over, NOT the rotation tester. The maptest
e1l4 tick never completes: in each cycle it only reaches patrol waypoint 3/20 before the
restart wipes it (log lines 1862-1903 show WAYPOINT 0..3 then `Server: e1l4$`).

### 2b. What calls `restartMap`

Only three callers exist (grep `restartMap`):
- `main.scr:363` — `playerCountChanged` when `local.playerCount == 0`.
- `replace.scr:2390` — `missionfailed`.
- `server.scr:263` — `checkForVote` (`coop_callvote == "restartmap"`; not active here).

### 2c. The e1l4 stealth papers gate auto-fails -> missionfailed -> restartMap

e1l4 is the BT stealth mission. During the truck intro the player is glued/notsolid/hidden
in the truck and a German guard demands papers. The gate watchdog
**`maps/e1l4/Intro.scr::KillPlayerIfFailPapers`** (Intro.scr:266-290):
```
while ( (isalive $1stgateguard) && ($1stgateguard.thinkstate != "attack")) { wait 1 }
...
if (level.GatePapersAccepted != 1){
    waitthread global/throbtext.scr::throbtext_off
    exec coop_mod/replace.scr::killplayer                 // Intro.scr:283
    if(level.gametype != 0){
        exec coop_mod/replace.scr::missionfailed          // Intro.scr:287  (coop)
    }
}
```
`replace.scr::missionfailed` (replace.scr:2377-2391) fades to red then:
```
thread coop_mod/main.scr::restartMap                       // replace.scr:2390
```

The live log confirms the gate is active during the patrol tour: the throbtext
`"Show your papers."` (`GateGuardDialogue`, Intro.scr:210-211) appears at 23:40:48
("LOCALIZATION ERROR: 'Show your papers.'"), in the same window as the patrol waypoints,
and the restart lands ~15s after waypoint 3 — consistent with the guard reaching
`attack` thinkstate (papers never shown by the bot) and `KillPlayerIfFailPapers` firing.

### 2d. Why the maptest exposes it (and a human normally wouldn't)

The Phase 2 tester (maptest_phase2.scr:147-185) **teleports the single test player through
BSP waypoints across the whole map** while the e1l4 intro is mid-sequence:
- The intro glues the player to the truck and force-manages spectator/camera state
  (`Intro.scr::handlePlayer` 422-454, `coop_startTruckSpawnManager` 460-494). The maptest
  teleport (`$player[1].origin = local.pos`, maptest_phase2.scr:172) yanks the player away
  from the gate area, so papers can never be shown and the guard escalates to `attack`.
- The bot has no human to press the papers key, so `level.GatePapersAccepted` stays != 1
  and the fail path is guaranteed.

A human player riding the intro normally shows papers in time, so the fail path never runs
and the map proceeds — which is why this never reproduced in maps 1-36 and won't in normal
play of e1l4 either.

### 2e. Secondary feedback: count==0 restart can also contribute

Independently, while the player is killed (`killplayer`, replace.scr:1432) and dropped to a
respawn/spectator state during the glued intro with `coop_disableSpawnWarper = game.true`
(e1l4.scr:14), `$player.size` can momentarily read 0, and `playerCountChanged` ->
`if(local.playerCount == 0){ waitthread restartMap }` (main.scr:361-364) provides a second
route to the exact same `e1l4$` restart. Either way the trigger is the auto-fail/auto-kill
during the unattended intro.

### 2f. Things ruled OUT
- `level.coop_debugSpawn = 1` (e1l4.scr:12) only makes spawn markers visible
  (spawnlocations.scr:7); harmless re: restarts.
- `level.coop_devTimescaleOn = 0` (e1l4.scr:13) makes the `developer.scr::timescale` calls
  in Intro.scr no-ops (developer.scr:488); not a factor.
- `waitTillPrespawn`/`waitForPlayer` are used correctly (e1l4.scr:28,60); init is fine —
  the map loads and reaches gameplay every cycle (689 entities / 1993 simple entities
  spawned each load).
- The disguise/uniform system (`coop_enableDisguises`, `coop_uniformOnSpawn`, e1l4.scr:19-21)
  changes player model, not team; it does not call `restartMap`/`changeGameType` in a way
  that restarts the server.
- No round-based gametype / `map_restart` / `spawnserver` in e1l4 scripts; the restart is
  purely the script `restartMap` path.

---

## 3. Proposed fix

Two layers. The first is the real fix; the second hardens the harness.

### Fix A (primary, e1l4 conversion gap): make the papers-fail coop-safe

In coop the intro should not silently kill + restart the server when the gate is not
satisfied — least of all for a maptest bot that can't show papers. Guard the auto-fail so
it cannot fire during the maptest, and prefer a soft re-prompt over `missionfailed` in coop.

In `maps\e1l4\Intro.scr::KillPlayerIfFailPapers` (around Intro.scr:278-289), gate the
coop fail path behind a maptest check and (optionally) avoid the hard server restart:

```
if (level.GatePapersAccepted != 1){
    waitthread global/throbtext.scr::throbtext_off
    waitframe

    // [fix] never auto-fail/restart under the unattended map tester (no human to show papers)
    if( getcvar("coop_maptest") == "1" || getcvar("coop_maptest") == "2" ){
        level.GatePapersAccepted = 1     // let the tour proceed instead of restarting
        end
    }

    exec coop_mod/replace.scr::killplayer

    if(level.gametype != 0){
        exec coop_mod/replace.scr::missionfailed
    }
}
```

(ASCII only, no em-dash, no bare negative-in-parens, no BOM — matches HZM parse hygiene.
`getcvar` returns a string, hence the `"1"`/`"2"` string compares, same idiom as
maptest.scr:36.)

Optionally also short-circuit `FAILEDMISSION` (Intro.scr:152-169) the same way so the
"blown your cover" path can't restart the server under maptest.

### Fix B (harness hardening, prevents the whole class): suppress restartMap under maptest

Make `restartMap` a no-op (or a clean advance) while the map tester is running, so ANY
map's mid-level fail/auto-kill can't turn into an infinite `<map>$` reload during an
unattended run. In `coop_mod\main.scr::restartMap` (main.scr:1482):

```
restartMap:{
    // [fix] do not self-restart during the map-rotation tester; it would loop forever
    if( getcvar("coop_maptest") == "1" || getcvar("coop_maptest") == "2" ){
        println "^~^~^ MAPTEST_RESTART_SUPPRESSED"
        end
    }
    local.mapname = getcvar "mapname"
    ...
}
```

Fix A is the correct conversion fix; Fix B is cheap insurance for future stealth/fail-capable
maps in the rotation.

---

## 4. Is it e1l4-specific or systemic?

**Specific in trigger, systemic in shape.**
- The exact auto-fail papers gate is unique to e1l4 (the only stealth/papers mission left in
  the rotation per level_scripts_sh_bt.md notes), so **Fix A is an e1l4 conversion gap**.
- BUT any map that can call `coop_mod/replace.scr::missionfailed` (or
  `playerCountChanged` count==0) mid-level can produce the identical infinite
  `<map>$` restart under the unattended Phase 2 tester, because the tester teleports/kills a
  lone bot that cannot satisfy scripted objectives. That makes **Fix B** worthwhile as a
  framework-level guard.

### Does it "get fixed with conversion"? (user's hypothesis)
Partly. Normal human coop play of e1l4 likely already avoids the loop (a human shows papers
in time). But the *conversion* is still incomplete: a coop stealth mission that responds to a
failed papers check by restarting the whole server (kicking everyone back through gamestate
resend + team menu) is poor coop behavior even with humans — e.g. one straggler who misses
the papers prompt would restart the map for the whole party. So Fix A (don't hard-restart the
server on a coop papers fail; re-prompt or fail soft) is a genuine conversion improvement,
not just a maptest accommodation.

---

## Appendix — key citations

- Engine drop/resend trigger: `code/server/sv_client.c:2103-2114` (serverId != sv.serverId
  while client not CS_ACTIVE) — engine source not in this tree; behavior confirmed in log
  ("dropped gamestate, resending" / `SV_SendClientGameState()` / repeated CS_CONNECTED ->
  CS_PRIMED -> CS_ACTIVE per reload).
- `restartMap` appends `$`: main.scr:1488-1494.
- `restartMap` callers: main.scr:363 (count==0), replace.scr:2390 (missionfailed),
  server.scr:263 (vote).
- e1l4 papers-fail: maps/e1l4/Intro.scr:266-290 (`KillPlayerIfFailPapers`), 152-169
  (`FAILEDMISSION`); both reachable from the gate sequence `GateGuardDialogue`
  (Intro.scr:196-263).
- `replace.scr::missionfailed` -> restartMap: replace.scr:2377-2391.
- Maptest teleport tour: maptest_phase2.scr:147-185 (`$player[1].origin = local.pos`),
  death test 197-204.
- Working team auto-join: player.scr:745-751 (manageSpectator fire-to-join),
  main.scr:296-334 (skipTeamAndWeaponSelect), player.scr:790-823 (manageAliveSpawning),
  main.scr:284-292 (forceValidTeam).
- Log evidence: qconsole.log lines 1896 (Server: e1l4), 3299/4726/5046/5328 (Server: e1l4$),
  1862-1903 (patrol stops at WAYPOINT 3/20 then restart), 23:40:48 "Show your papers."
