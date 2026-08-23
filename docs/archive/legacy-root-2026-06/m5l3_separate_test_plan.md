# m5l3 (+ m5l2b) Separate/Thorough Test Plan
Source: subagent aa6045a999361da2c (2026-06-23). Plan only; no files modified. "We will do it later" per user.

## m5l3 reality
NOT multi-BSP-scene. Single sniper-overwatch map. ALL waitForPlayer calls (main:123, bomberdetect:222, objgen:413, enemyspawnerthink:1911, flak88:1976) are the SAME spawn gate (replace.scr::waitForPlayer - first blocks, rest spin on level.coop_waitforPlayer). The REAL progression gate is ONE thing: a player standing in $binoleft/$binoright/$binomid. objgen (threaded from main as `$obj5 thread objgen 5`) BLOCKS at m5l3.scr:417:
  while(!(istouching $binoleft) && !(istouching $binoright) && !(istouching $binomid)){ wait 0.5 }
Standard Phase 2 spawns a player (clears waitForPlayer) but never parks them in a bino volume -> only Phase A (intro) runs; everything below is UNTESTED.

Phases (post-bino-gate, self-advancing on flags/time):
- A Intro (TESTED): flak88 loop, towers, objectives 1-4.
- B Bridge recon: touch bino -> readytosnipe, $playertank thread dodrive (auto-drives, destroys flak88+plunger, lines 1085-1191), thread enemytankstart (spawn vehicles/tigertank, line 306), first bridgeblower (spawnthreadguy 832).
- C Blower defense: objgen 507-543 repeated spawnthreadguy waves; ends on plungergone/Bridge_Is_Gone.
- D Artillery: objgen 548 thread artilleryattack -> Artillary_Ready=1; bino click handlers fire arty/bomber; enemyref reinforcements.
- E King Tiger: wintime elapsed + player in bino + curvehicles<2 (objgen 559-574) -> enemytankstart escalates to spawn vehicles/kingtank (line 330, 7000hp) + showhealth HUD.
- F Win: King_Tiger_Lost==0 & curvehicles drained (objgen 587) -> obj4 complete, setcvar g_m6l1 1, missioncomplete briefing/briefing6.
Heavy/special content the smoke test misses: vehicles/tigertank + vehicles/kingtank spawns (configstring-heavy, same family as m5l2b), kingtank_d.tik death model, exploder ids 101-104/301-308, ai.scr spawn 201-216, German bridge-blowers, King Tiger health HUD (huddraw 100), stg44/mp44 weapon points.

## Test approach (recommended): m5l3-specific "scene-walk" thread, new cvar, NO edit to m5l3.scr
- New cvar coop_maptest_m5l3 (default 0). Reuse Phase 2 clicker/watchdog/transition/banners.
- New cfg coop_mod/cfg/maptest_m5l3_start.cfg: seta coop_maptest 2; seta coop_maptest_m5l3 1; seta coop_maptest_dwell 600; seta g_scriptcheck 0; set ui_dmmap m5l3; exec coop_mod/start_server.cfg
- New coop_mod/maptest_m5l3.scr thread coop_maptest_m5l3_walk, hooked in coop_mod/main.scr::main beside the Phase 2 hook. It reads/writes level.flags[]/level.wintime/$bino* from OUTSIDE (so m5l3.scr is untouched):
  1. waitForMainScript; bail if cvar!=1 or level.coop_mapname!=m5l3. Wait $player.size>=1, emit ^~^~^ MAPTEST_LOADED m5l3 (clicker fires), set high health.
  2. Verify entities, banner each: ^~^~^ MAPTEST3_ENT m5l3 <name> <origin|MISSING> for $binoleft/right/mid,$obj5,$playertank,$flak88,$plunger.
  3. PHASE B: teleport $player[1].origin=$binomid.origin (fallback left/right); RE-ASSERT origin+health every tick ~20s (Phase 2 idiom) so AI can't knock player off the volume; banner MAPTEST3_SCENE m5l3 B_recon. Unblocks objgen:417.
  4. Poll plungergone -> MAPTEST3_PLUNGER_GONE; first tiger alive -> MAPTEST3_TIGER_SPAWNED; 90s timeout -> MAPTEST3_TIGER_TIMEOUT.
  5. PHASE D: Artillary_Ready==1 -> MAPTEST3_ARTY_READY.
  6. PHASE E: FORCE gate -> set level.wintime=level.time, keep player on bino so objgen 559-574 -> Final_Tank_Approaches -> King Tiger branch (enemytankstart 320-346). Poll -> MAPTEST3_KINGTIGER_SPAWNED / _TIMEOUT.
  7. STOP before PHASE F win (the win path execs global/missioncomplete.scr briefing/briefing6 = transition). Emit MAPTEST3_ALL_SCENES_OBSERVED, hand back to coop_maptest_transition to advance. Forcing the real win is a separate riskier sub-test.
- Value: forces the two vehicle spawns + exploders + AI waves + HUD to actually run under coop (paths the smoke test never hits); any TIKI overrun/configstring overflow/null-deref/parse error surfaces with a greppable per-phase banner.
- Shared (no change): clicker, watchdog, coop_maptest_transition, MAPTEST_LOADED convention, teleport+reheal-each-tick idiom. New: maptest_m5l3.scr, the cvar, the cfg, one hook line in main.scr.
- Parse: ASCII, no BOM/em-dash, keep compound && / || on one line, negatives only in vectors.

## m5l2b re-inclusion (skipped sibling)
Skipped at maptest.scr:193-194 for "vehicle BSP exceeds MAX_MSGLEN 49152". MAX_MSGLEN since raised to 131072 (Issue #14; m6l1c already re-added on that basis). m5l2b.scr coop tank path is in place + noted working (players_tank replication 53-122, level.coop_playerTank, coop_autoDriveTank line 558 auto-drives King Tiger along $playertank_trigger to level_end -> missioncomplete m5l3 line 447). m5l2b is a SINGLE linear auto-drive scene (no bino-gate forcing needed). VERIFY: load manually (set ui_dmmap m5l2b; seta coop_maptest 0), watch gamestate-send for MAX_MSGLEN/gamestate-overflow/configstring errors (should be gone at 131072); confirm "coop_autoDriveTank ... King Tiger" start + reached-end + missioncomplete m5l3. If clean, re-add m5l2b at idx23 in coop_maptest_list (between m5l2a and m5l3), delete skip comment, and re-verify downstream PHASE_END index comments (30/35/40 shift by one).
