# MASTER PLAN v2.2 (VETTED x3) - m2l2a Coop Stealth: "Scuttling the U-529"

**Status:** vetted draft, amended after vetting round 2 and vetting round 3 (see section 15). Ready for Phase A implementation.
**Date:** 2026-08-09 (v2), amended 2026-08-09 (v2.1, v2.2)
**Scope:** m2l2a primary; the shared-code fixes (Phase A, Phase B) apply to e1l3 / e1l4 / m2l2b / m6l1c and every combat map, and are called out as such.
**Supersedes:** `docs/proposals/m2l2a_stealth_master_plan.md` (v1), whose premises "engine frozen" (v1 D5) and "whole-window aggro gating" (v1 D4) were invalidated by bug-1638 (per-frame disguise parity in every gametype) and bug-1639 (per-target engine-flag deference).
**Binding records:** `.wolf/buglog.json` bug-1600..bug-1640, `docs/OPEN.md`, `docs/TRAPS.md`, `docs/DECISIONS.md`.
**Incorporates:** both adversary review passes against the draft (section 12), vetting round 2 against v2 itself, and vetting round 3 against the round-2 amendment (section 15). Every confirmed finding is folded into the step, table or claim it affects, in place. Do not read section 15 as errata - the steps themselves are corrected.

---

## 1. Executive summary

The mission is to make m2l2a playable as a real cooperative stealth level for 1-4 players: everyone starts and stays unarmed, one uniform pickup dresses the whole squad, any player can present papers to any checker, and the level converts to a conventional firefight the moment a checker rejects you or an alarm rings - with every scripted scene (card game, welders, sledgehammer, the Norway pair, the Naxos scientists) playing exactly as it does in single player until then. **And, per user decision D1, silencing the alarm brings the disguise back**, exactly as retail intends.

The saga's root cause was found on 2026-08-09 and is already fixed: **bug-1638**. `Player::Think`'s disguise maintenance ran only in `GT_SINGLE_PLAYER`, so in coop `m_bIsDisguised` froze at whatever the last `changeGameType` window computed. Every stealth experiment of 08-08 and 08-09 - unarmed spawns, whole-window aggro cvars, AI stand-downs - was compensation for one frozen boolean. With `g_coopDisgParity 1`, retail stealth semantics are native in coop.

That changes the shape of this plan completely. The remaining work is **mostly subtractive**: delete the parallel script implementations of rules the engine now enforces, stop using a one-way latch (`attackplayer` / `ForceAttackPlayer`) as an everyday verb, stop using room tests to gate per-target actions, and stop letting coop's AI-enrichment systems rewrite scripted scene actors. On top of that sit two genuinely new pieces:

1. a **stealth director** that owns a single one-way QUIET -> LOUD **weapons** phase, whose LOUD action gives players their kit **holstered** rather than drawn - so a local, vanilla-survivable bust (the Naxos scientists) stays local instead of cascading into a map-wide, disguise-voiding aggro storm; and
2. a **recoverable disguise axis** (D1), driven by the `level.alarm` 1 -> 0 edge rather than by the phase machine, so dousing an alarm switch genuinely restores the uniform. The engine already implements this natively (`player.cpp:5490-5497` recomputes `m_bIsDisguised` every frame under `m_bHasDisguise && !level.m_bAlarm`); it is HZM script - `itemhandler.scr::takeAllDisguises` - that currently makes it one-way, plus one engine latch (`m_bForceAttackPlayer`) that must be cleared on the douse edge.

**Two axes, not one.** This is the single most important structural correction in v2.1:

| Axis | Variable | Direction | Owner |
|---|---|---|---|
| Weapons | `level.coop_stealthPhase` (`quiet` -> `loud`) | one-way; you never lose the kit | `stealth.scr` |
| Disguise | `level.coop_disgSuspended` (0 / 1), driven by `level.alarm` | reversible, both directions | the `level.alarm` edge, mirrored from the engine |

**Five** cvar-gated `game.dll` edits remain - E1, E2, E3, E4 and the `EquipWeapons` spawn-loadout suppression of Step 6b - plus one new one for D1 (E5). Separately, B0 is an unguarded NULL dereference that is a crash risk independent of this feature and should ship immediately as its own bug fix (it is not cvar-gated; a NULL guard has no sane "off").

**Work breakdown (six phases, eleven commits, 25 steps - the step index in section 5 is authoritative):**

| Phase | Content | Blast radius | Kill switch |
|---|---|---|---|
| **A** | Correctness fixes to shipped script: freeze arm, six anim gates, one aggro rule, scene-actor exemption (script AND personality system), papers lifecycle | shared script, every map | `coop_disgAggroParity 0` (new; takes effect at the next map load) |
| **B0** | Engine NULL guards at three `G_GetEntity(0)` sites - ship standalone | every map | none needed (pure guard) |
| **B1** | Engine E2: obstacle-bump latch judged against the actual colliding player, and no aggression at all against scripted-anim actors; engine spawn-loadout suppression | every map with moving AI | `g_coopDisgParity 0` (latched) |
| **B2** | Engine E1 + E3 + E4: per-enemy sight trace, papers-challenge timing, per-originator AI-event mute | disguise maps, multiplayer only | `g_coopDisgParity 0` (latched) |
| **B3** | Engine E5 (D1): clear `m_bForceAttackPlayer` across all actors on the `level.alarm` 1 -> 0 edge | disguise maps | `g_coopDisgParity 0` (latched) |
| **C** | `coop_mod/stealth.scr` director, lifecycle holes, holstered arming, **recoverable alarm** | m2l2a only | `coop_stealthStart 0` |

Phase A and B0 are worth landing even if the feature is later shelved.

---

## 2. Established roots and evidence

Every claim below was re-read in the working tree during synthesis and **re-verified during vetting round 2**. Line numbers are as of 2026-08-09. Where round 2 moved an anchor, the corrected anchor is given and the v2 value is noted, because several steps instruct edits by line range.

### 2.1 Script

| Claim | Anchor | Status |
|---|---|---|
| Stealth papers/disguise block sits ABOVE the `coop_noWeapon` exit | `coop_mod/itemhandler.scr:719-742`, `takeall` at `:708`, exit at `:745` | verified |
| **Uniform give sits BELOW that exit** and is unreachable during a stealth window | `itemhandler.scr:762-766` (v2 said 761-766); `:765` is the ONLY caller of `takeUniformFromPlayer` in the tree | verified - NEW DEFECT |
| The `:719` stealth block is gated on `level.coop_startUnarmed`, which **only `maps/m2l2a.scr:40`** ever sets | `itemhandler.scr:719`, `maps/m2l2a.scr:38-42` | verified - constrains Step 10 to DUPLICATE, never MOVE |
| `level.coop_enableDisguises` is set by exactly three maps | `maps/e1l4.scr:23`, `maps/m2l2a.scr:27`, `maps/m2l2b.scr:15`. **e1l3 is papers-only and never sets it** | verified - corrects a v2 claim |
| `giveDisguiseToAll` early-exits on `level.coop_enableDisguises \|\| level.alarm` | `itemhandler.scr:996` | verified - **it is INERT on m2l2a**, which pre-sets the flag at load. The live grant is per-spawn `giveDisguiseOnSpawn` (`:728` / `:759`) |
| `coop_armOnBlown` is an atomic check-then-set latch with no yield between the test and the write, and therefore **cannot fire twice** | `itemhandler.scr:1395-1396` | verified - disproves the draft's "runs twice concurrently" rationale, AND blocks any re-arm after a D1 recovery |
| `coop_armOnBlown` arms only `coop_isActive == 1 && isAlive`; a DBNO player satisfies both | `itemhandler.scr:1405`; `dbno.scr:174` `healthonly 100`, `:185` sets only `coop_dbno_active` | verified - NEW DEFECT (Step 11) |
| `giveWeaponLoadout` reads `group.player` throughout - it takes no player argument | `itemhandler.scr:1430, 1449, 1460, 1491, 1498` | verified |
| **`group` IS the ScriptClass, and BOTH halves of the rule matter.** Only an **unprefixed same-file** `thread label` / `waitthread label` shares the caller's ScriptClass (`scriptclass.cpp:192-201` -> `Director.CreateScriptThread(this, label)`). A **file-qualified** `file::label` call AND an **entity-prefixed same-file** call (`local.p waitthread someLabel`) both allocate a NEW, EMPTY ScriptClass and therefore a new empty `group` - the prefixed form routes through `listener.cpp:4192-4206` -> `scriptmaster.cpp:694-698`, which does `new ScriptClass(scr, self)` | `scriptvm.cpp:1465-1467` / `:1661-1663`; `scriptclass.cpp:192-201` vs `:211-216`; `listener.cpp:4192-4206`; `scriptmaster.cpp:694-698`; live prefixed same-file use at `itemhandler.scr:1256-1264` | verified; **round 3 added the entity-prefixed half** - this is why Step 12 needs an entry label that assigns `group.player` from `self`, not a `group.player` assignment at the call site |
| `giveWeaponLoadout`'s `has_disguise` branch holsters and prints the hint, and does NOT run `coop_backfillPrimaries` or `spawnWeaponAssert` - those live only in the else branch | `itemhandler.scr:1498-1508` vs `:1509-1547` (`use` + `activatenewweapon` at `:1535-1539`, `spawnWeaponAssert` `:1541`, `coop_backfillPrimaries` `:1546`) | verified - NEW DEFECT (Step 11) |
| `coop_papersAnytime` exits on death and is restarted only by `givePapersFlag`; its restart test `!coop_hasPapers` is permanently false because `coop_hasPapers` is never cleared anywhere | `itemhandler.scr:1207-1226` (`:1225` clears the re-entry guard), starter `:2519-2525`, spawn test `:768`; `player.scr:1444` sets `coop_isActive = -2` | verified - NEW DEFECT (Step 11) |
| `coop_papersAnytime`'s fire test is `primaryfireheld && coop_activeWeapon is NULL`, and `deactivatePlayerWeapon` (`:1095`) is exactly what nulls that flag | `itemhandler.scr:1215-1220` | verified - post-LOUD, holstering makes FIRE present papers for 2s |
| `coop_paperPassAll` fires `type_disguise "none"` immediately (the bug-1631 freeze arm); the per-guard `coop_paperPass` latch at `:1178-1179` is permanent and cleared nowhere | `itemhandler.scr:1178-1181` | verified |
| `takeAllDisguises` clears `coop_enableDisguises` + `coop_uniformOnSpawn` (`:1144-1145`) and per-player `has_disguise` / `coop_hasDisguise` / `coop_isDisguised` (`:1150-1152`), with **no inverse caller anywhere in the tree** | `itemhandler.scr:1138-1152` | verified - the D1 blocker |
| `takeAllDisguises` has exactly four callers | `global/alarm_system.scr:704`, `global/items.scr:477`, `maps/e1l4/PreShip.scr:88`, `maps/e1l4/Ship.scr:416` | verified - three of them are NOT alarms |
| The retail alarm is a genuine toggle; the OFF branch has **no coop hook at all** | `global/alarm_system.scr:700` / `:704` (ON), `:717-729` (OFF, `level.alarm = 0` at `:728`) | verified |
| `disguiseHandler` can never restart once the alarm rings: `:1007`'s `while` exits on `level.alarm`, `:1003` refuses re-entry on `coop_disguiseHandlerThread`, and `:1005` is the ONLY assignment of that flag in the tree - nothing clears it | `aihandler.scr:997-1007` | verified - NEW DEFECT (Step 21) |
| `coop_stealthArmOnHurt` has zero callers | `itemhandler.scr:1375-1387` | verified |
| `attackPlayer` funnel guard is dead by config: requires `coop_stealthNoAggro != "0"` AND `coop_stealthFunnelGuard == "1"`, and `coop_stealthNoAggro` is seeded 0 | `aihandler.scr:1076` + `autoexec.cfg:1176` + `coop_defaults.cfg:210` | verified |
| The funnel's in-code ledger records "VERIFIED 2026-08-09 10:38: with this OFF, attackers held at 0 of 25 for the whole run - the source gates alone did it" | `aihandler.scr:1063-1075` | verified - **but see the correction below: the `AGGRO BLOCKED aisquad-goloud` log line quoted as proof comes from `aisquad.scr:115`, i.e. the PER-TARGET gate at `:114`, not from the NIL branch. The measurement does not license retiring the NIL branch.** |
| `attackPlayer` ends with a bare `local.enemy attackplayer` (no target); `local.enemy favoriteenemy local.player` at `:1104` is unguarded and receives NIL on the legacy path | `aihandler.scr:1103`, `:1104`. **Round 3 corrected this from `:1102`, which is `local.enemy.flags["coop_isAttacking"] = game.true` and MUST BE PRESERVED** (readers at `aihandler.scr:1014`, `:1117`, `disguise_accept.scr:10`, `disguise_deny.scr:14`, `disguise_enemy.scr:23`). `:1101` is `enablePain = 1` | verified |
| **`coop_stealthBlocksAggro` already exists** as the bug-1639 per-target engine-flag gate | label `aihandler.scr:1184`; per-target rule `:1191-1197`; NIL branch `:1198-1222`, room walk `:1213-1222` (v2 said 1211-1222) | verified |
| **Three of its four callers pass NIL**, and the NIL branch is the only thing that makes them stand down | per-target: `aisquad.scr:114`. NIL: `aihandler.scr:274` (replica spawn), `aisquad.scr:139` (search sweeps), `morale.scr:71` (berserk) | verified - **fail-open on NIL would kill all three.** In-code rationale at `aisquad.scr:109-113` and `morale.scr:69-70` ("two card players stood up from the table") |
| The per-target rule has **no phase term**: `if( local.ed == 1 && !level.alarm && level.coop_enableDisguises ){ end (1) }` | `aihandler.scr:1191-1197` | verified - this is what makes a holstered post-LOUD player non-hostile again (by design under D1; see section 4.4) |
| `canseeUndisguisedPlayers` is a ROOM test (any player) reading the engine flag | label `aihandler.scr:1225`, body `:1227-1240` (v2 said 1233-1247) | verified |
| `anyEnemiesInAttackState` walks `level.coop_actorArray["german"]` testing `thinkstate == "attack" \|\| "pain"` **with no NULL guard on the array slot** | label `aihandler.scr:1244`, body `:1246-1252` (v2 said 1250-1258) | verified - reuse the walk SHAPE for T5, not the label |
| `setEnemyAttackStates` issues a raw `attackplayer` restore and is the SOLE restorer of `enableEnemy = 1` / `no_idle = false` | label `aihandler.scr:1277`, restore loop `:1281-1290`, `attackplayer` at `:1285` (v2 said 1285-1292) | verified |
| `resetEnemyThinkstates` sets `enableEnemy = 0` BEFORE the restore runs, and the engine turns that into `SetEnemy(NULL, false)` - so by restore time `.enemy` is NULL | `aihandler.scr:1266`; `actor.cpp:8608-8626` | verified - **a gate on `local.enemy.enemy` in `setEnemyAttackStates` can never fire** |
| **SIX** anim files carry the room-test-gated `attackPlayer self.enemy` pattern | `disguise_accept.scr:10-11`, `disguise_salute.scr:36-37`, `disguise_wait.scr:13-14`, `disguise_deny.scr:14-15`, `disguise_halt.scr:18-19`; `disguise_enemy.scr:23-28` has the same attack with **NO disguise test at all** | verified |
| **THREE** of those six have statements stranded below the attack branch's `end` - **FOUR statements in total**, because `disguise_accept.scr` has two | `disguise_accept.scr` (branch ends `:16`, `}` at `:17`, **`coop_clickablePapersEnabled` clear at `:18` AND `coop_paperPassAll` at `:22`**); `disguise_deny.scr` (ends `:20`, `coop_clickablePapersEnabled` clear at `:22`); `disguise_enemy.scr` (ends `:33`, same clear at `:35`) | verified - v2 named one statement, round 2 named three, round 3 found the fourth (`disguise_accept.scr:18`) |
| `global/wrenching.scr:80` `self attackplayer`, reachable on m2l2a via `$wrenchman1` (`m2l2a.scr:1148`), `$crateguy1` (`:1303`), `$crateguy2` (`:1310`), through `prealarmthread` (`wrenching.scr:25`) and `OnPain` (threaded at `:48`; label `:100`, `end` at `:107`) | `global/wrenching.scr:80` | verified - MISSING from v2's Step 3 site list. Round 3 corrected the thread anchor from `:47` (blank) to `:48` |
| `global/welder.scr` does **not** run on m2l2a - `$welderguy1/2 thread welding` binds to m2l2a's own local `welding:` label | `maps/m2l2a.scr:1122-1123` -> `:1231`; welder.scr's only caller is `maps/e2l2/planeGags.scr:292` | verified - corrects an assumption |
| Raw `attackplayer` sites inside `maps/m2l2a.scr` - **twelve**, not two | `:270, :307, :346, :466, :629, :638, :639, :914, :1057, :1106, :1222, :1608` | verified - v2 listed `:270` and `:914` only |
| `cardplayersdeath` issues `$suckyfatty attackplayer` as the **unbraced single statement of an `if`** | `maps/m2l2a.scr:260` (label), `:269` (`if(level.cardplayers != 3)` with no brace), `:270` | verified - an inserted "preamble" would rebind the conditional |
| **`$suckyfatty` resolves to THREE entities.** A scalar `.flags[...] = 1` assignment on it is a hard `Cannot cast 'container' to listener` Script Error | `map_entities/m2l2a_entities.txt:3558, :3583, :3608`; `global/cardgame.scr:48-56`, `:274`; `scriptvm.cpp:1794-1819`, `:1610-1623`; `scriptvariable.cpp:1108-1109` | verified - constrains Step 4's tag recipe |
| Real m2l2a targetnames for scene actors | `$suckyfatty`, `$guy1`, `$guy2`, `$guy3`, `$welderguy1`, `$welderguy2`, `$sledgehammerguy`, `$wrenchman1`, `$crateguy1`, `$crateguy2`. `jokey`, `stupid`, `goatsbutt`, `whatsthesub`, `hushyhushy`, `sentry2dude`, `officer1`, `loweralarmerguy` are **level vars only** (`m2l2a.scr:124-135`), not targetnames | verified - v2's tag list wrote "wrenchman" and prose |
| `waitForEnemy` breaks on the ROOM test then does `self attackplayer` followed by `self type_disguise "none"`; the two Norway guards are already `type_disguise "none"` and therefore **have no `self.enemy` at all** | `maps/m2l2a.scr:898-907` (loop, room test at `:901`), `:914-915`; **`:808-809`** (`:807` is the `likeynorway:` label; round 2's "corrected" `:807-808` was wrong and v2's `808-809` was right), threaded at `:839-840` | verified - Step 14 must name a predicate, because there is no target variable here |
| papers1 -> papers2 swap is `remove_item` then `add_item`, which physically strips the papers item from every spawned player and zeroes `level.papers` across a multi-frame window | `maps/m2l2a.scr:417-418` -> `global/items.scr` -> `replace.scr::take` | verified |
| Loose `playerweapon_german_mp40` exists in the locker room, **carries no targetname**, and respawns under `g_gametype 2`. It is the only `playerweapon_*` entity in the file (grep count 1) | `map_entities/m2l2a_entities.txt:30` (`"classname"`), `:28` (`"model" "weapons//mp40.tik"` - **double slash, no `models/` prefix**); `item.cpp:361` | verified - `$name remove` is unavailable; there is no find-by-classname primitive. **Round 3: the RUNTIME `.model` string has never been observed** - the map-file spelling is not it, and the shipped precedent (`main.scr:2069-2085`) had to match two case variants of one path. Step 15 must observe before it matches |
| The proven entity-sweep recipe in this codebase is a `getentbyentnum` walk after a settling wait | `coop_mod/main.scr::coop_launcherRespawnSweep` (threaded at `main.scr:136`, opens `wait 3`); `coop_mod/wounded.scr:252-262` ("getentbyentnum (NOT getentarray - that misses item entities)") | verified - Step 15's recipe |
| `spawnProtection` stamps an **8 second** default window and re-stamps on every respawn | `coop_mod/player.scr:1310-1320`, read at `:1326` | verified - far too long to key detection exemptions on |
| `managePlayerInventory` already stamps a short per-spawn timestamp | `itemhandler.scr:702` `coop_spawnEventTime = level.time` (round 3: `:700` is blank) | verified - the correct basis for Step 16 |
| `player.scr`'s armory-skin re-force runs AFTER `managePlayerInventory` in the same label and overwrites the player model with no disguise exclusion | `player.scr:1012` (call), `:1097-1159` (re-force + locked-skin heal) | verified - NEW DEFECT (Step 10) |
| `coop_officer_wait_goloud` **already returns 1 on `level.alarm == 1`**, and `alarm_system.scr:700` sets `level.alarm = 1` BEFORE threading `takeAllDisguises` at `:704` | `coop_mod/officer.scr:118-128`; m2l2a classified "deferred" at `:84` | verified - **a `reason == "alarm"` clause would be dead code.** D2 is already satisfied by shipped code |
| The same label has a hard **600 second** bound and its caller treats a 0 return as terminal | `officer.scr:118-128`, caller `:182-189` | verified - a late alarm gets no waves at all |
| `officer.scr` emits **no machine marker for a wave or a release.** The only `^~^~^` prints in the file are `:896` OFFICERHEAL, `:1736` PRONEDBG and `:3202` DEATHREACT; the release diagnostics at `:183` / `:186` / `:189` are `iprintlnbold` gated on `level.cMTE_coop_officer`, a level variable no cvar or rcon command can set | `officer.scr:183-189` | verified in round 3 - **TP-2's "no officer-wave markers" was unmeasurable; Step 14 now adds the positive markers** |
| A `^~^~^ PRONEDBG` print **already ships** inside `coop_prone_shooter`, carries no actor field, is gated on `coop_aiBehav`, and sits ABOVE the weapongroup whitelist reject | existing print `officer.scr:1736`, gate `:1735`, reject `:1740-1744` | verified in round 3 - **Step 4's A3 print must NOT reuse that marker name** |
| Replica cloning is **not** suppressed during QUIET - only the target hand-off is gated | `aihandler.scr:264-278`, in-code note `:266-272` | verified - corrects v2's "re-run cloning at the phase flip" decision |
| `coop_apply_personality` runs on **every** german actor when `coop_aiDynamic 1` (seeded on), exempts only machinegunners, and ~12% of the time forces `enableEnemy = 0` + a looped `anim_scripted` prone pose; 60% of the rest write `type_attack "cover"` | `aihandler.scr:109-111` (caller), `:26` (gate); `autoexec.cfg:580`; `officer.scr:1660+`; `replace.scr:396-399` | verified - **this, not the hurt-trooper branch, is the dominant scene-actor writer** |
| `enableEnemy = 0` forcibly removes an actor from a DISGUISE think and NULLs its enemy | `actor.cpp:8608-8626` | verified - a proned papers checker can never be shown papers |
| The hurt-trooper branch is itself gated on `coop_personality_set`, i.e. it only fires on actors `coop_apply_personality` already tagged | `aihandler.scr:424`, branch `:424-436` | verified - v2's Step 4 was treating a downstream symptom |
| Card players are set to health 2; the seated mechanic sets health 1 | `global/cardgame.scr:288-289, 378-379, 122-123` | verified |
| Additional raw `attackplayer` funnel sites outside the anim scripts | `wounded.scr:219` and `wounded.scr:336` (both have only `local.actor` in scope - no player variable exists there); `maps/e1l2/Artillery.scr:87` (passes a real player) | verified |
| `aimaneuver.scr:150` has **no `attackplayer`** - it is `enableEnemy = 0` + `runto` + `forceactivate` | `coop_mod/aimaneuver.scr:148-151` | verified - v2's site table mis-described it |
| A Script Error does **not** kill the thread. `ScriptVM::Execute`'s try/catch is inside the per-opcode loop and `HandleScriptException` returns without rethrowing | `scriptvm.cpp:1881-1883`, `:1915-1935` | verified - **so every "the thread dies" prediction in v2 and in review is wrong; the real cost is a silently skipped statement plus log noise** |
| `NIL + <number>` throws "binary '+' applied to incompatible types" - there is no VARIABLE_NONE case in `operator+=` | `scriptvariable.cpp:1496-1570` | verified - `coop_stealthArmEpoch` must be seeded |
| `local.a.alarmthread` is an EV_GETTER returning a **const array** (or NONE when unset); concatenating it into a string throws | `actor.cpp:1053-1061`, `:8160-8163`; `gamescript.cpp:1230-1242`; `scriptvariable.cpp:1496-1570` | verified - Step 4's A3 print must use a 0/1 boolean |
| `type_attack` has **no script-visible provenance** - only a current-value getter exists | `actor.cpp:753-760`; writes at `global/alarm_system.scr:336-337` | verified - "or its `type_attack` was force-assigned" is unwritable |
| Only four map scripts start the alarm system | `maps/e1l4/PreShip.scr:15`, `maps/e1l4/Ship.scr:32`, `maps/m2l2a.scr:123`, `maps/m6l1c.scr:76` | verified - constrains TP-R's map choice |
| `coop_stealthStart` is seeded in **five** places, not two | mod-root `hzm-mohaa-coop-mod/autoexec.cfg:1175` (0) and `hzm-mohaa-coop-mod/coop_defaults.cfg:207` (0) - **mod root, not repo root, and not `coop_mod/cfg/`**; plus the autotest harness homepath, which is **already 1 and therefore out of sync**: `autotest_home/maintt/coop_defaults.cfg:206`, `autotest_home/maintt/configs/omconfig.cfg:2308`, `autotest_home/maintt/stealthtest.cfg:9` | verified in round 3. Per bug-1633 a homepath cfg SHADOWS the basepath copy, so Step 17 must name all five |
| `start_server.cfg` reads `ui_dmmap`, which the caller must set FIRST | `coop_mod/start_server.cfg` (last line `ui_startdmmap 2`); pattern at `coop_mod/cfg/lobbytest.cfg:20-27`, `campaign_start.cfg:13`, `arena.cfg:19` | verified - corrects section 8.1 |
| The live launch profile's log is **not** the APPDATA one | `build.ps1:123-125`: "the live launch profile uses fs_homepath `G:\mohaa-gl2\home`, and a homepath cfg SHADOWS the basepath copy" (bug-1633) | verified - corrects section 8.1 |
| The script verifiers live in `docs/tools/`, not `scratchpad/` | `docs/tools/depthscan2.py`, `quotecheck.py`, `linecheck.py`, `scrlint.py`; `scratchpad/` holds only `rcon.py` | verified - corrects section 8.4 |

### 2.2 Engine

| Claim | Anchor | Status |
|---|---|---|
| Disguise maintenance now runs in every gametype under `g_coopDisgParity` (default 1) | `code/fgame/player.cpp:5482-5497` | verified |
| The recompute is `m_bIsDisguised = false` FIRST, then true only if `m_bHasDisguise && !level.m_bAlarm` and hands are empty or hold an `InventoryItem` | `player.cpp:5491-5497` | verified - **this is the native recoverable-alarm behaviour D1 needs** |
| `level.alarm` maps straight onto `level.m_bAlarm`, and is script-writable both ways | `level.cpp:2062-2070`, `EV_Level_SetAlarm` `:102` / dispatch `:653` | verified |
| **With `g_coopDisgParity 0` the whole block is skipped, so `m_bIsDisguised` is not reset either** - it freezes at its last value, possibly TRUE, and no alarm can clear it | `player.cpp:5490-5491`; the only other writers are `sentient.cpp:869` (ctor) and `:3338` (archive) | verified - corrects section 11's understatement |
| `g_coopDisgParity` is fetched lazily into a function-local static inside `Player::Think` and is registered nowhere else | `player.cpp:5487-5489` | verified - `CVAR_LATCH` must be applied at a real registration site, not there |
| `g_coopDisgDebug` tracer exists in four places | `actor.cpp:7934, 8033`, `actorenemy.cpp:364`, `actor_disguise_common.cpp:31-38` | verified |
| Both obstacle-bump branches are already guarded by `if (p && !IsTeamMate(p))`, and `IsTeamMate` returns true when `pOther->m_bIsDisguised` | `actor.cpp:3363-3377`, `:3391-3405`; `sentient.cpp:4008-4019` | verified - the draft's "skip when disguised" E2 is already done by parity |
| The residual is that both branches resolve the colliding player with a hardcoded `G_GetEntity(0)` | `actor.cpp:3357, 3387` | verified - matches bug-1640 "STILL OPEN" |
| **`ForceAttackPlayer` hardcodes the target too** - it is `ConfirmEnemy(this, G_GetEntity(0))` + `m_bForceAttackPlayer = true`, and both bump branches call the bare form | `actor.cpp:9336-9340`, called at `:3376` and `:3404` | verified - **resolving `p` alone does not fix TP-7** |
| The real blocker IS **usually** resolvable: `mmove_t` carries `numtouch` / `touchents[]`, and `MM_AddTouchEnt` sets `hit_temp_obstacle \|= 1` for a player blocker | `g_local.h:490` (`numtouch`) / `:491` (`touchents[MAXTOUCH]`); `g_mmove.cpp:83` (function), `:97-99` (flag set), `:105-107` (MAXTOUCH capacity return), `:117-118` (append) | verified, **but not "exact"**: the flag is set at `:99` and the capacity return at `:105-107` fires AFTER it, so `hit_temp_obstacle` can be set with **no** entnum appended (MAXTOUCH is 32, `bg_public.h:289`); and `touchents` can hold more than one player. Step 6 item 1 is worded for zero-or-many, not just for "cannot name a blocker" |
| `m_bForceAttackPlayer` is written in exactly two places - the constructor (`false`) and `ForceAttackPlayer` (`true`) - and `EnemyIsDisguised()` returns false unconditionally while it is set | `actor.cpp:3092`, `:9339`; `actor.h:2159-2174` | verified - **permanent per-actor disguise blindness; the D1 engine blocker (E5)** |
| `ConfirmEnemy` -> `AddPotentialEnemy` dereferences its argument with no NULL check | `actorenemy.cpp:279-281` | verified |
| `IsTeamMate(NULL)` returns FALSE, so a NULL entity 0 falls THROUGH into `ForceAttackPlayer` at both grenade sites | `sentient.cpp:4008-4019`; `actor_grenade.cpp:348-350`, `:440-442` | verified - two more NULL-crash sites for B0 |
| `ConfirmEnemy` opens by clearing `pSelf->m_bEnemyIsDisguised` | `actorenemy.cpp:501`, and `:528` clears it too | verified - so `attackentity` is advisory but not inert |
| **`m_bEnemyIsDisguised` is refreshed EVERY TICK the enemy is visible**, not only in `SetEnemy` | writers: `actor.cpp:2984` (ctor false), **`:4033`** (inside the per-tick `if (bCanSee)` visibility update), `:6906` (`SetEnemy`), `:10041` (false); cleared at `actorenemy.cpp:501` / `:528` | verified in round 3 - **corrects Step 3 item 4 and residual risk 5.** The stale-verdict window exists only while the actor CANNOT see the target |
| Disguise transition sight trace dereferences `G_GetEntity(0)` unguarded | **`actor.cpp:9039` assigns** (`Entity *player = G_GetEntity(0);`), **`:9045` dereferences** `player->centroid`, **`:9047` passes it as passent2**. `:9041` is the `return G_SightTrace(` | verified. **Round 3 restored v2's original anchors: round 2's "corrected" 9038/9042/9044 was wrong on all three** (`:9038` is blank), and its parenthetical "the anchors are off by ~3" is withdrawn |
| `m_bHasDisguise` is only ever written on a Player | `player.cpp:11386`; `sentient.cpp:870` init | verified - so E1's solo behaviour is provably identical (`m_Enemy` IS entity 0) |
| `G_BroadcastAIEvent`'s MISC / MISC_LOUD mute tests client 0's disguise only, and **every in-tree MISC producer passes a non-Sentient originator**, so a per-originator Sentient test would be a dead branch | `g_utils.cpp:1798-1804`; `doors.cpp:597/628/665/723`, `misc.cpp:447/536`, `weapon.cpp:4391`; zero `broadcastaievent` calls in any `.scr` | verified - corrects Step 9 |
| `m_iEnemyShowPapersTime` is snapshotted at `Begin_Disguise*` **and re-stamped by `Resume_Disguise*`**, while `Think_Disguise*` calls `UpdateEnemy(1500)` every tick with `m_bEnemySwitch` defaulting true | `actor_disguise_sentry.cpp:58`, `:72-76`, `:93`; `actor.cpp:3115` | verified - v2 said "never refreshed", which is incomplete |
| `Actor::SetEnemy` (signature `actor.cpp:6889`) has an **early return at `:6891-6893` when `pEnemy == m_Enemy`**, then assigns `m_Enemy = pEnemy` at `:6899` unconditionally and only then enters `if (m_Enemy)` at `:6903-6914`; `SetEnemy(NULL)` is routine | `actor.cpp:6889`, `:6891-6893`, `:6899`, `:6903-6914`; callers `:3270`, `:5418`, `:6821-6822`, `:8625` | verified - **an unguarded re-stamp at the top of the function is a hard crash, and the early return means it is not even the per-target refresh path** |
| `CheckEnemies` selects the current enemy by **visibility, not range**, and deliberately retains disguised enemies | `actorenemy.cpp:400-410`, **`:469`** (`:474` is the closing brace) | verified - the checker's `m_Enemy` can be a fully-visible player 300u away |
| **A disguised enemy is pinned at zero threat, and the only engine veto that can clear a holstered player's `m_bIsDisguised` requires positive threat** - a stable fixed point | `actorenemy.cpp:161-165` (early return, `m_iThreat = 0` when `m_pEnemy->m_bIsDisguised`); `player.cpp:5509-5512` (veto requires `act->m_PotentialEnemies.GetCurrentThreat() > 0`) | verified in round 3 - **this is why T5 condition 4 had to be re-derived; see section 4.2** |
| **`State_Disguise_Papers` transitions to HALT purely on >256u distance to the CURRENT enemy; `State_Disguise_Halt` then escalates to `THINKSTATE_ATTACK` after 1500ms with NO disguise test; `State_Disguise_Enemy` does the same after 3000ms** | `actor_disguise_common.cpp:96-110`, `:136-138`, `:141-148`, `:150-157` | verified - **destroys v2's claim that "the engine cannot enter ATTACK against a disguised player"; T5's premise was false** |
| `type_attack "alarm"` maps `THINKSTATE_ATTACK` to `THINK_ALARM`, so every `$ai_alarm` running its alerted thread IS in thinkstate "attack" | `actor.cpp:8049-8051`; `actor_alarm.cpp:36-71`; `global/alarm_system.scr:336-337`, measurement at `:371-372`; 13 `ai_alarm` entities in `map_entities/m2l2a_entities.txt`, set up at `maps/m2l2a.scr:123` | verified - T5 would fire on all thirteen during QUIET |
| `State_Alarm_Idle` ends with `SetThink(THINKSTATE_ATTACK, THINK_TURRET)`, permanently overwriting `THINK_ALARM`; nothing restores it | `actor_alarm.cpp` `State_Alarm_Idle`; re-issuing `type_attack "alarm"` DOES reinstall it (`actor.cpp:8241-8255`) | verified - **alarm scene reactions are one-shot unless restored (Step 22)** |
| An actor already in `THINKSTATE_ATTACK` is structurally disguise-blind, and attack thinks never call `CheckForThinkStateTransition`; the only exit requires `!m_Enemy`, which requires losing visibility | `actor.h:2159-2172`; `actor_turret.cpp:818-828`; `actorenemy.cpp:420-423` | verified - **per-actor D1 recovery is gated on breaking line of sight, not on a timer** |
| `EquipWeapons()` runs inside the engine spawn path, **before any script**, and a checker can transition to `DISGUISE_ENEMY` from that single armed frame with no path back | `player.cpp:9790-9791`, `:9931`; `actor_disguise_sentry.cpp:53-63`, `:102-104` | verified - **no script gate can pre-empt this; Step 16 needs an engine half** |
| `thinkstate` getter returns the TOP think level's state, so a pain/grenade suspension reads as "not disguise" | `actor.cpp:11929-11932`, `actor.h:1873` | verified |
| `State_Disguise_Accept` already does `SetThinkState(IDLE)` + `SetThink(DISGUISE, THINK_DISGUISE_SALUTE)` permanently | `actor_disguise_common.cpp:159-167` | verified - the `type_disguise "none"` swap is redundant |
| A latched cvar applies on the next `Cvar_Get` after a game-module reload; a normal `map <name>` DOES reload the module, `map_restart` does not | `qcommon/cvar.c:487-495`, `:685-700`; `sv_ccmds.c:269` / `:335`; `sv_init.c:633`, `:668-677` | verified |
| `thread <label>` in a VALUE context returns the label's `end (value)` when the label completes without yielding - it is NOT a bare handle | `listener.cpp:121`, `:131`, **`:4234-4243`** (`CreateReturnThread`); `scriptvm.cpp:989-994`, `:558-560` | verified - **there is no "bug-1609"; see section 15** |
| **`Level::SetAlarm` has no old-value capture** - it is a bare `m_bAlarm = ev->GetInteger(1);` - so an "on the 1 -> 0 edge" hook cannot be written there without adding one, and it fires on **every** scripted `level.alarm` write tree-wide (`coop_mod/e1l4alarm.scr:36`, `global/alarm_system.scr:728`, `maps/e1l3/FinalEscape.scr:830/833/865/956`, `maps/e1l4/Ship.scr:8`, `maps/m2l2a.scr:111`, `maps/m2l2b.scr:55`, `maps/m6l1c.scr:111`) | `level.cpp:2067-2070` | verified in round 3 - **constrains Step 23's hook choice** |
| `level.m_HeadSentient[TEAM_*]` is a **`Sentient*`** list, not an Actor list, and is populated for every Sentient of that team including players on the axis `dmteam` | `level.h:221`; `Sentient::Link` `sentient.cpp:932` / `:936`; iterated as `Sentient*` at `sentient.cpp:4025`; `m_bForceAttackPlayer` is an **Actor** member (`actor.h:728`) | verified in round 3 - **an unchecked `(Actor*)pSent` write across that list is an out-of-bounds write; Step 23 must not do it** |
| `Player::EquipWeapons` is at `player.cpp:9931`, called from the spawn path at `:9791` and again at `:11299`. **No coop stealth flag is readable from the engine today** - a grep of the whole `openmohaa-hzm/code` tree for `coop_noWeapon`, `coop_startUnarmed`, `coop_stealth`, `coopStealth` and `coopUnarmed` returns zero matches | `player.cpp:9931`, `:9791`, `:11299` | verified in round 3 - **Step 6b must NAME a new cvar; the trio is script-only** |

### 2.3 Ledger entries this plan is bound by

- **bug-1636 / bug-1637** (`global/cardgame.scr`): the entire retail card manager was dead code in coop behind a `level waittill spawn` that never fires in MP. Both sites are now shimmed and the entry is **PENDING PLAYTEST**. This activates the retail sit manager, the 1-hp seated mechanic and `chairdeath` for the first time in coop. **TP-0 must attribute card-player results to this shim, not to Step 4.**
- **bug-1638**: the saga root. `g_coopDisgParity`. PENDING PLAYTEST.
- **bug-1639**: `coop_stealthBlocksAggro` per-target engine deference. PENDING PLAYTEST. This plan **uses** that helper rather than forking a second copy.
- **bug-1640**: obstacle-bump collision latch. "PARTIALLY CLOSED by bug-1638; STILL OPEN: replace `G_GetEntity(0)` with the actual colliding player ... consider skipping `BecomeTurretGuy` for actors running a scripted anim thread." **This plan's Step 6 is that residual, extended to `ForceAttackPlayer`'s own hardcoded target.**
- **bug-1631** failed_attempt F3: "their thinkstate never leaves idle, so the sit ANIM is being replaced by something invisible to thinkstate probes" - an unexplained residual. Step 4 is a **hypothesis about that residual**, instrumented before it is fixed. Round 2 identified a much better-fitting candidate than the canteen anim: `coop_apply_personality`'s looped `anim_scripted` prone pose (section 2.1).
- **bug-1632**: entity references parked across **thread or level boundaries** misbehave. It does **not** forbid a thread-local array of entity references. Constrains Step 11 and Step 13 accordingly.
- **bug-1624**: a hook stranded below an early exit. Its sibling (the uniform) is still stranded - Step 10.
- **bug-1633 / 1634 / 1635**: the artifact tested was not the artifact edited. Constrains every deploy and every verdict.
- **Citation hygiene:** `bug-1605`, `bug-1607` and `bug-1609` **do not exist** in `.wolf/buglog.json` (the id sequence skips them). v2 cited all three. Every such citation has been removed from this document and replaced with in-code evidence. Do not re-introduce them.
- **Known log noise (confounders for any `Script Error` pass criterion):** bug-1632 is PENDING VERIFY with a documented print loop. bug-1621's MG42 include fix has landed in `models/human/new_generic_human.tik:59` (unconditional include) and should not recur. Section 8.3 therefore requires a recorded baseline allowlist (TP-BASE) rather than "no new Script Error".

---

## 3. Architecture

**Engine-Parity Stealth Director, with holstered arming and a reversible disguise axis.** Five principles, in priority order.

### P1. The engine owns disguise truth and every guard reaction

`g_coopDisgParity` recomputes `m_bIsDisguised` per frame in coop: holster or an `InventoryItem` in hand means disguised, a real weapon drawn means blown, an alarm means never, and a veto requires `GetCurrentThreat() > 0`. Script never re-implements detection. Script **reads** `is_disguised` and **writes** only `has_disguise`.

### P2. There is exactly one implementation of the disguise-deference rule, and it takes exactly one parameter

That implementation already exists: `aihandler.scr::coop_stealthBlocksAggro` (`:1184`, the bug-1639 fix). Every gate in this plan calls it, **unchanged in signature**.

**The no-target policy, settled here:** the NIL walk stays, unconditionally, for every caller. v2 specified fail-open on NIL, on the strength of an in-code measurement that in fact came from the per-target branch (`aisquad.scr:114-115`), and three of the helper's four callers pass NIL - the replica spawn (`aihandler.scr:274`), the search sweep (`aisquad.scr:139`) and the berserk path (`morale.scr:71`). Failing open on NIL silently deletes all three stand-downs on **every** disguise map (e1l4 and m2l2b as well as m2l2a) and re-creates the exact recorded failure their in-code comments describe: `forceactivate` pulling card players out of their sit animation.

**Round 3 went one step further and deleted the `failOpenOnNil` parameter v2.1 introduced.** Read the walk (`aihandler.scr:1213-1222`): it accumulates `local.anyUn` over every live player and only `end (1)`s `if( local.anyUn == 0 )`, i.e. it blocks **only while EVERY live player is engine-disguised**, and falls through to `end (0)` the moment anyone is undisguised. That is already the right semantics for `attackPlayer`. A per-caller fail-open therefore buys no additional aggro; all it does is open the bare `attackplayer` at `aihandler.scr:1103` - the permanent `m_bForceAttackPlayer` latch (`actor.h:2165`) - on the one genuinely NIL-capable route into the funnel, `aihandler.scr:1015`'s `thread sentientIsSeen local.enemy local.enemy.enemy 360`, which propagates another actor's `.enemy` and is NULL after any `enableEnemy = 0` (`actor.cpp:8608-8626`). That directly contradicts the standing rule in section 4.4.

The signature stays:

```
coop_stealthBlocksAggro <target>
```

(For completeness: the headline scenario v2.1 used to justify fail-open - a non-Player killer reaching `attackPlayer` with NIL from `aihandler.scr:150` - is refuted. `:149` guards that call with `self.fact.attacker && self.fact.attacker.classname == "Player"`.)

### P3. Script owns exactly one thing the engine does not: weapons-over-time

One new file, `coop_mod/stealth.scr`, owns `level.coop_stealthPhase` and the one-way QUIET -> LOUD transition. Nothing else writes it.

### P4. LOUD means "you have your kit", not "your cover is gone"

This is the pivot. Arming with `activatePlayerWeapon` draws a real weapon, which flips `is_disguised` false for that player on the next frame, which trips every remaining room-test gate, which raw-latches `attackplayer` map-wide, which rings the alarm, which voids disguises. A vanilla-local bust - the Naxos scientists, which the retail walkthrough tells you to shoot and carry on from - would end the mission's stealth spine, and the post-Naxos papers2 / sentry2dude gate comes **after** that bust.

Therefore: **the loud transition gives the loadout holstered while `has_disguise` still holds, and only the alarm path draws.** Players choose when to shoot.

### P5. The disguise axis is reversible; the weapons axis is not (D1)

The engine already voids `m_bIsDisguised` while `level.m_bAlarm` and restores it the frame the alarm clears, provided `m_bHasDisguise` survives. So D1 is delivered by **removing** the script that destroys `m_bHasDisguise`, not by adding a restoration mechanism on top of it.

Concretely: on a stealth-director map the alarm suspends the disguise; it does not confiscate it. Weapons, once issued, are never taken back. A recovered squad plays holstered until it chooses otherwise. Two consequences must be stated in the design rather than discovered in a playtest:

- **Per-actor recovery is gated on line of sight, not on a timer.** An actor already in `THINKSTATE_ATTACK` is structurally disguise-blind (`actor.h:2159-2172`) and attack thinks never re-evaluate the think state. The only exit requires losing the enemy, which requires visibility falling to zero (`actorenemy.cpp:420-423`). Dousing restores the squad's disguise instantly; each individual guard re-accepts it only after it has genuinely lost you.
- **Alarm scene reactions are one-shot unless restored.** `State_Alarm_Idle` overwrites `THINK_ALARM` with `THINK_TURRET` permanently. Step 22 restores it on the douse edge for every actor carrying an `alarmthread`.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Whole-window aggro gating (`coop_stealthNoAggro`) | Retired by bug-1639; measured unnecessary 2026-08-09 10:38; froze scripted NPC sequences. Deleted entirely, not left dormant. |
| **Fail-open on a NIL aggro target (v2's own choice)** | Deletes the replica, search-sweep and berserk stand-downs on every disguise map. See P2. |
| **A per-caller `failOpenOnNil` argument (v2.1's own choice)** | Round 3: the shared NIL walk already permits aggro whenever any player is undisguised, so fail-open buys nothing and only opens the permanent `attackplayer` latch on one propagation path. Parameter deleted. See P2. |
| Deferred `type_disguise "none"` retirement (a poll) | The poll's exit condition is satisfied by a pain/grenade **suspension** (`thinkstate` reports the top level), after which `Resume_Disguise*` runs `EndState + BeginState` into `THINK_DISGUISE_NONE`, whose `BeginState` is NULL - the exact bug-1631 freeze by a new route. And it is redundant: `State_Disguise_Accept` already demotes the guard permanently. **Delete the swap** instead. |
| Delivering D1 by re-running `giveDisguiseToAll` on the douse edge | It is inert on m2l2a (`itemhandler.scr:996` early-exits on `coop_enableDisguises`, which the map pre-sets), and where it is not inert it calls `resetEnemyThinkstates` + `setEnemyAttackStates`, whose raw `attackplayer` at `:1285` permanently blinds every german that was in attack or pain. Use a dedicated `restoreDisguises` that touches no thinkstate. See Step 21. |
| Script-only, no engine change | Leaves clients 2-4 structurally unchallengeable (host-centroid sight trace), leaves the obstacle-bump branch free to destroy scripted scenes in 4P, leaves the spawn-frame armed window unclosable, and leaves `m_bForceAttackPlayer` un-clearable so D1 recovery is cosmetic. |
| A second inline disguise predicate in `attackPlayer` | Forks `coop_stealthBlocksAggro`. See P2. |
| Enumerating the retail bust labels to hook | m2l2a has at least twelve raw `attackplayer` sites; the next map will have others. See T5. |

---

## 4. The state machine

### 4.1 The two axes

**Weapons axis** - `level.coop_stealthPhase`, one-way:

| State | Value | Invariants |
|---|---|---|
| **INERT** | `NIL` | Non-stealth map. Every gate in this plan uses a positive-form test, so all are no-ops. |
| **QUIET** | `"quiet"` | Trio armed (`coop_noWeapon`, `coop_startUnarmed = 1`, `coop_forcePapersEquip`). No weapon granted anywhere; the map's loose weapon entity is removed. Every body re-latches `has_disguise` + papers + **uniform**. Papers presentable at will. Scene-hostile coop systems stood down. |
| **LOUD** | `"loud"` | Trio cleared atomically **in `goLoud` itself** (not delegated to `coop_armOnBlown`'s latch). Every active player holds their kit. Every later body arms through the normal pipeline plus the epoch. Scene stand-downs lifted; **scene-actor protections are NOT lifted** (see Step 4). |

**Disguise axis** - `level.coop_disgSuspended`, reversible, mirrored from `level.alarm`:

| State | Value | Meaning |
|---|---|---|
| **INTACT** | `0` / NIL | `has_disguise` holds. The engine grants `is_disguised` to any holstered player. |
| **SUSPENDED** | `1` | An alarm is ringing. The engine denies `is_disguised` to everyone (`player.cpp:5493`). `has_disguise`, `coop_hasDisguise`, `coop_enableDisguises` and `coop_uniformOnSpawn` are **left intact** so the suspension can lift - which means `onAlarmDoused` has nothing to "restore" in those two level flags and **must not write them blindly** (see Step 21c: it snapshots them on the raise edge and re-asserts the snapshot, so an alarm rung before the locker room does not dress the squad for free). |

`level.coop_disgSuspended` has **exactly one writer**, `stealth.scr::alarmWatcher`, which **mirrors `level.alarm` on every sample** rather than latching on an edge. `takeAllDisguises` does not write it. Rationale in section 4.4.

The two axes are independent. `LOUD + INTACT` is the normal post-bust state and is fully playable stealth-with-guns. `QUIET + SUSPENDED` is unreachable (any alarm also goes LOUD). `LOUD + SUSPENDED -> LOUD + INTACT` is the D1 recovery.

Two auxiliary flags, both set-once-and-stay:

- `level.coop_stealthReason` - **why we FIRST went loud**. Never overwritten.
- `level.coop_stealthAlarmEver` - 1 once any alarm has rung, regardless of phase. Consumers that mean "an alarm happened" read this, not the reason.

### 4.2 Transitions (weapons axis)

All routed through `stealth.scr::goLoud <reason> <drawWeapon>`, idempotent.

| ID | Trigger | Source | Draws? |
|---|---|---|---|
| **T1** | A checker enters the ENEMY state (officer Fake_Papers resolution, sentry 12s timeout) | `anim/disguise_enemy.scr:22`, inside `if (level.gametype != 0){` and above the per-target `if` at `:23`. **Note the latency:** `:15` sets the alert upper anim and `:16` is `self waittill upperanimdone`, a real multi-second yield, so the preamble is NOT "at the top of the file" and T1 fires a beat after the checker turns hostile. During that beat the map is still QUIET and any lifecycle event spawns unarmed. T5 is the backstop; do not move the preamble above `:12` unless it is wrapped in its own `if (level.gametype != 0)` block | No |
| **T2** | Any alarm rings | `takeAllDisguises` tail -> `notifyLoud local.reason local.draw`, with `draw` derived inside `takeAllDisguises` as `1` for `reason == "alarm"` and `0` otherwise (Step 21a) | **Yes** |
| **T3** | Naxos caught-in-the-act during the hold-USE sabotage | `m2l2a.scr::coop_naxosCaught` | No |
| **T4** | Player damaged with an attacking German within 1600u | `m2l2a.scr::coop_blownOnDamage` (existing poll) | No |
| **T5** | **Systematic backstop:** see the corrected predicate below | `stealth.scr::quietWatchdog` | No |
| **T6** | Parity flap: a player with `has_disguise`, empty hands, no alarm, no suspension, reading `is_disguised == 0` for > 1s | `stealth.scr::quietWatchdog` | No |
| **T7** | Fault: a player holds a real `Weapon` while phase is `"quiet"` | `stealth.scr::quietWatchdog` - **reports and goes loud**, never filters | No |

#### T5 - corrected predicate (v2's was false)

v2 asserted that "the engine cannot enter ATTACK against a disguised player". **That is false in source.** `State_Disguise_Halt` sets `THINKSTATE_ATTACK` 1500ms after entry with no disguise test, and HALT is entered from PAPERS purely because the checker's current enemy is more than 256u away (`actor_disguise_common.cpp:96-110`, `:150-157`). `State_Disguise_Enemy` does the same after 3000ms. Separately, `type_attack "alarm"` maps `THINKSTATE_ATTACK` to `THINK_ALARM` (`actor.cpp:8049-8051`), so all **thirteen** `$ai_alarm` actors on m2l2a routinely sit in thinkstate `"attack"` with a player enemy during QUIET.

A bare `thinkstate == "attack" && .enemy.classname == "Player"` therefore fires constantly during a clean stealth run, and TP-2b - the declared keystone - would be structurally unreachable in 2P+.

**Round 3 refuted v2.1's condition 4 as well.** v2.1 wrote condition 4 as `.enemy.is_disguised != 1`. That is circular and unsatisfiable during QUIET, which is the only phase T5 runs in:

- `actorenemy.cpp:161-165` returns early with `m_iThreat = 0` when `m_pEnemy->m_bIsDisguised`, and `:469` deliberately RETAINS a disguised enemy at zero threat;
- `player.cpp:5509-5512` shows the only in-engine veto that can clear a holstered player's `m_bIsDisguised` requires `act->m_PotentialEnemies.GetCurrentThreat() > 0`.

Disguised implies threat 0 implies no veto implies still disguised - a stable fixed point. During QUIET every player is holstered and holds `has_disguise` (granted per spawn at `itemhandler.scr:727-728`; `maps/m2l2a.scr:27` pre-sets `coop_enableDisguises`), so `.enemy.is_disguised != 1` is essentially never true and T5 - the declared systematic backstop for expectation 4 - would have been dead code against exactly the raw-`attackplayer` busts it exists to catch (`m2l2a.scr:270` and eleven siblings, `global/wrenching.scr:80`, `wounded.scr:219`).

**The re-derived basis is the latch itself, not the target's disguise flag.** Every bust T5 must catch goes through `attackplayer` -> `Actor::ForceAttackPlayer` -> `m_bForceAttackPlayer = true` (`actor.cpp:9339`), and **nothing else in the engine sets that flag** (the only other write is the constructor's `false` at `:3092`). The disguise HALT / ENEMY escalations do not set it, and neither does `type_attack "alarm"`. So Step 23 (B3) gains a second, tiny engine deliverable: **expose `m_bForceAttackPlayer` as a read-only script getter, `forceattackplayer`**, alongside the `unforceattackplayer` event it already adds. B3 lands before Phase C in the phase order, so T5 can rely on it.

T5's predicate is, all of:

1. the actor is non-NULL, alive, and german;
2. `thinkstate == "attack"` or `"pain"`;
3. `.enemy` is non-NULL, non-NIL and `classname == "Player"`;
4. **`.forceattackplayer == 1`** - the actor has been hard-latched onto a player by a raw `attackplayer`, which is the signature of every bust site the plan enumerates and of nothing that happens during clean stealth;
5. **the actor is not alarm-driven**: `.alarmthread == NIL` and `type_attack != "alarm"`;
6. **the actor's previous sample was not a disguise state**: the watchdog keeps a per-actor last-sample and discards a transition whose previous value was `"disguise"` (which covers HALT, WAIT, PAPERS and ENEMY origins);
7. two consecutive 0.25s samples.

**The `coop_isAttacking` OR-term of v2.1 is DELETED.** v2.1 kept it on conditions 1, 3, 4, 5 only - omitting 2 and 6 - which was a second, unguarded path into a one-way `goLoud` that the section's own prohibition on re-importing HALT did not cover. The flag is also a permanent latch itself: it is written true at `aihandler.scr:1102`, `:1287` and `aisquad.scr:124` and cleared nowhere in the tree. And by v2.1's own admission it "would detect nothing after Phase A", so it buys no coverage either way.

**If B3 is rolled back, T5 degrades to nothing** and expectation 4 rests on T1, T3, T4 and T7 alone - T4 (`coop_blownOnDamage`) still catches the case once the player is actually shot, so the mission stays winnable. Record that dependency in section 11's rollback table rather than discovering it.

Rationale for keeping T5 at all: every retail bust the plan names is a **raw** `attackplayer` (`m2l2a.scr:270` and eleven siblings; the same shape at `officer.scr:537/687/1040/1048/1090/1369` and `holdout.scr:430/578`). A watchdog keyed on the flag those calls actually set is the only systematic backstop available.

**Not hooked, deliberately:** `disguise_halt.scr` (HALT is routine 4-player geometry) and `disguise_deny.scr` (vanilla DENY is a non-hostile wave-off with a re-challenge in 15-30s). Both instead get their `attackPlayer` calls per-target gated so they cannot fire on a disguised player at all. Condition 6 above is what stops T5 from re-importing HALT through the back door - this is the specific inconsistency round 2 found in v2 and it must not be re-opened.

### 4.3 LOUD entry action

```
goLoud local.reason local.draw:
    if (level.coop_stealthPhase != "quiet") { end }   // idempotent; NIL-inert
    level.coop_stealthPhase   = "loud"                // stamp FIRST, before any wait
    level.coop_stealthLoud    = 1
    if (level.coop_stealthReason == NIL) {
        level.coop_stealthReason = local.reason
    }
    if (level.coop_stealthArmEpoch == NIL) {
        level.coop_stealthArmEpoch = 0
    }
    level.coop_stealthArmEpoch = level.coop_stealthArmEpoch + 1
    // clear the trio HERE, not inside coop_armOnBlown, so the clear does not
    // depend on that label's once-only latch
    level.coop_startUnarmed     = 0
    level.coop_noWeapon         = game.false
    level.coop_forcePapersEquip = game.false
    println "^~^~^ST LOUD reason=" + local.reason + " draw=" + local.draw
    waitthread unprotectScene
    waitthread coop_mod/itemhandler.scr::coop_armAllOnBlown local.draw
end
```

**BLOCKER FIXED IN ROUND 3 - read this before writing `coop_armAllOnBlown`.** v2.1 moved the trio clear up into `goLoud` (above) *and* kept `coop_armOnBlown`'s shipped opening test as the arming loop's once-only guard. Those two statements are mutually exclusive. `itemhandler.scr:1394-1396` is:

```
coop_armOnBlown:{
    if( level.coop_startUnarmed != 1 ){ end }
    level.coop_startUnarmed = 0
```

The guard and the clear are **one atomic check-then-set pair**. Split them and, by the time `goLoud` reaches its arming call four statements later, `level.coop_startUnarmed` is already 0 - so the label ends on its first statement and **nobody is ever armed**, on the first LOUD of every run, solo included. `^~^~^ST LOUD` is printed at the line above, so the failure is silent. Every transition dies the same way (T1/T3/T4/T5/T6/T7 through `goLoud`, T2 through `notifyLoud`, and `notifyLoud`'s already-loud branch which calls `coop_armAllOnBlown` directly). Expectations 4 and 5 both fail outright; TP-2, TP-6, TP-8 and TP-8b are unreachable.

**The required shape:** `coop_armAllOnBlown` carries its **own** once-only latch, written before its first yield, and **contains no `coop_startUnarmed` test at all**:

```
coop_armAllOnBlown local.draw:
    if( level.coop_armAllDone == 1 ){ end }
    level.coop_armAllDone = 1
    ... build the thread-local player array, then give ...
end
```

`coop_armOnePlayer` (Step 12) likewise carries **no** trio test, or the epoch re-give dies the same way. Step 21e's rationale ("`coop_armOnBlown`'s `:1395-1396` is an atomic one-shot") is stale the moment `:1396` moves and has been rewritten accordingly.

Notes that are load-bearing:

- `level.coop_stealthArmEpoch` **must be seeded to 0 in `init`** and guarded here. `NIL + 1` throws "binary '+' applied to incompatible types" (`scriptvariable.cpp:1496-1570`); the statement is then skipped silently and the epoch stays NIL forever, killing Step 12 with no visible symptom outside `developer 1`.
- Stamping the phase before the arming wait closes the race with a second call.
- The trio clear moved OUT of `coop_armOnBlown`, **and the `if (level.coop_startUnarmed != 1) { end }` test at `itemhandler.scr:1395` is DELETED with it**, replaced by the independent `coop_armAllDone` latch above. The clear must not be conditional on the trio: `replace.scr:2644` and `:1349` both write `coop_noWeapon` outside this path, and if anything zeroes `coop_startUnarmed` before `goLoud`, the old shape left `coop_noWeapon` true forever and every later spawn took the `itemhandler.scr:745` exit empty-handed.
- The arming entry point is renamed `coop_armAllOnBlown` and is a **same-file** wrapper in `itemhandler.scr` around the per-player `coop_armOnePlayer` (Step 12), because `group` does not cross a file-qualified thread boundary.

`notifyLoud` is the **only** entry point wired into `takeAllDisguises`, and it is deliberately **phase-tolerant** and **draw-tolerant**:

```
notifyLoud local.reason local.draw:
    if (local.reason == "alarm") {
        level.coop_stealthAlarmEver = 1
    }
    if (level.coop_stealthPhase == "quiet") {
        waitthread goLoud local.reason local.draw
        end
    }
    // not a stealth-director map, or already loud: still guarantee the kit,
    // and still honour the draw (v2 delegated this to coop_armOnBlown, whose
    // latch had already fired, so an alarm after a non-alarm LOUD drew nobody)
    waitthread coop_mod/itemhandler.scr::coop_armAllOnBlown local.draw
    if (local.draw == 1) {
        waitthread coop_mod/itemhandler.scr::coop_drawAllWeapons
    }
end
```

`coop_drawAllWeapons` is a small new label factored out of `coop_armOnBlown`'s tail: iterate active, alive, non-DBNO players, raise their weapon, and print "Cover blown - weapons free!". It runs even when the trio is already clear.

**It must NOT be a loop of `thread activatePlayerWeapon`.** `activatePlayerWeapon` opens `if( ... || local.player.flags["coop_lastActiveWeapon"] == NULL ){ end }` (`itemhandler.scr:1121`), and that flag is NULLed by `deactivatePlayerWeapon`'s own empty-hands early return (`:1103-1107`) - so on any body that was holstered while empty-handed the draw is a no-op and `^~^~^ST LOUD reason=alarm draw=1` is followed by a holstered squad. Resolve the weapon directly instead, from `coop_loSlot1` / `coop_lastWeapon` / `level.coop_weaponUse`, and issue `use <name>` + `activatenewweapon "dual"` - exactly what the arming else-branch already does at `itemhandler.scr:1529-1539`.

(Calling `coop_armAllOnBlown` and `coop_drawAllWeapons` across the file boundary from `stealth.scr` is safe: neither READS an inherited `group`. The cross-file hazard applies only to labels that read `group`, i.e. `giveWeaponLoadout` - see Step 11.)

This matters because `takeAllDisguises` is reached from four callers. Routing its arming through a phase-gated `goLoud` alone would leave any map that sets `coop_startUnarmed` without calling `stealth.scr::init` **permanently weaponless after an alarm**.

### 4.4 Disguise-axis transitions (D1)

**The watcher MIRRORS, it does not latch.** v2.1 wrote a pure 1 -> 0 edge detector seeded `local.was = 0`, and separately had `takeAllDisguises` write `level.coop_disgSuspended = 1` itself - a second writer the edge detector never observes. `alarm_system_master` (`global/alarm_system.scr:688-732`) is a plain toggle with **no minimum on-time and no yield in either branch**, m2l2a carries **four** independent `alarm_switch_trigger` entities (`map_entities/m2l2a_entities.txt:2463, :2491, :2509, :3029`) each running its own `alarm_switch_thread`, and `ai_gofor_alarm` issues its own `douse` at `:651`. An ON-then-OFF inside one 250 ms sample is therefore constructible, and if the watcher misses it `coop_disgSuspended` latches at 1 with `level.alarm` reading 0: the hint permanently says "the alarm is up", `restoreDisguises` never runs, `disguiseHandler` is never re-threaded, E5 never fires, and **no marker is emitted**. Permanent, silent, no self-heal.

So: reconcile on VALUE every tick, and use edges only to trigger the one-shot handlers, both of which must be idempotent.

```
alarmWatcher:                          // threaded from init, 0.25s poll
    local.was = 0
    while (level.coop_stealthPhase != NIL) {
        local.now = 0
        if (level.alarm != NIL && level.alarm == 1) { local.now = 1 }
        // MIRROR: the single writer of the disguise axis, every sample
        level.coop_disgSuspended = local.now
        // EDGES: one-shot handlers, both written to be idempotent
        if (local.now == 1 && local.was != 1) { waitthread onAlarmRaised }
        if (local.now == 0 && local.was == 1) { waitthread onAlarmDoused }
        // SELF-HEAL: an edge missed inside one tick still converges
        if (local.now == 0 && local.was == 0 && level.coop_disgRestored != 1) {
            waitthread onAlarmDoused
        }
        local.was = local.now
        wait 0.25
    }
end
```

`onAlarmRaised` sets `level.coop_stealthAlarmEver = 1` and `level.coop_disgRestored = 0`, **snapshots `level.coop_enableDisguises` and `level.coop_uniformOnSpawn` into `level.coop_disgSnapEnable` / `level.coop_disgSnapUniform`**, prints `^~^~^ST SUSPEND`, and re-words the holster hint (Step 11). It does **not** write `coop_disgSuspended` (the watcher owns it) and does **not** clear `has_disguise` - `takeAllDisguises` in non-permanent mode already declined to (Step 21).

`onAlarmDoused` (Step 21 + Step 22) sets `level.coop_disgRestored = 1` first (so the self-heal leg cannot re-enter it), then does, **in this order**:

1. clear the alerted queue so a queued german cannot immediately re-ring: `level.ai_alerted_index = 0` and `level.ai_alerted_stack[1] = NULL` - **`NULL`, not `NIL`**, matching `global/alarm_system.scr:98` and the bumpstack clear at `:463`; assigning NIL removes the container element instead of nulling it. **Do NOT write `level.ai_alerted_isprocessing`**: it is a mutex owned by `alarm_system.scr`, claimed at `:425` / `:455` and released at `:436` / `:469`, and clearing it from outside releases a lock another thread believes it holds. See Step 22a for the `ai_alerted_index` floor this requires and for the re-arm cooldown's named reader;
2. `waitthread restoreDisguises` (Step 21c) - per active player set `has_disguise` + `coop_hasDisguise` + `setIsDisguised`, and re-assert the **snapshotted** `coop_enableDisguises` / `coop_uniformOnSpawn`, giving the uniform only where the snapshot was 1. **No forced holster, no thinkstate touched, no `attackplayer` ever issued** (see Rejected alternatives, and the paragraph below);
3. clear `level.coop_disguiseHandlerThread` **only after observing it NIL** and then re-`thread aihandler.scr::disguiseHandler` - see Step 21d for why the naive force-clear duplicates the loop;
4. **engine side (E5, Step 23):** clear `m_bForceAttackPlayer` across all actors, or every german latched during the loud window stays disguise-blind for the rest of the map and the recovery is cosmetic;
5. **last:** re-issue `self type_attack "alarm"` for the map-script scene alarmthreads only (Step 22b). It is last because `Actor::EventSetTypeAttack` hot-swaps an actor that is currently IN `THINKSTATE_ATTACK` straight into `THINK_ALARM` and runs its alarm thread, which for the `$ai_alarm` set is the queue **pusher** - i.e. step 5 can repopulate what step 1 just cleared. Step 22b therefore excludes that set entirely;
6. print `^~^~^ST QUIETDISG reason=doused` and an on-screen line: "Alarm silenced. Holster and break line of sight to blend back in."

**Standing rule, adopted from round 2 and binding on all future work:** on a stealth-director map, after any LOUD, **nothing may issue `attackplayer`**. `ForceAttackPlayer` sets a flag cleared only in the Actor constructor and archived into savegames. Use `attackentity` with a resolved target.

**Weapons do not un-issue on recovery, and the squad is NOT force-holstered.** v2.1 put `deactivatePlayerWeapon` inside `restoreDisguises`; round 3 deleted it. `itemhandler.scr:1110-1111` NULLs `coop_activeWeapon` and issues `deactivateweapon "dual"` server-side - the player does not choose it - which contradicts P4 ("players choose when to shoot"), contradicts the sentence below, and contradicts P5: TP-10 explicitly douses "once standing in the open" and expects the guards to keep hunting until LOS breaks, so v2.1 would have disarmed the whole squad mid-firefight. It also hands the fire button to `coop_papersAnytime` for everyone at once, whose trigger is `primaryfireheld && ( coop_activeWeapon == NULL || NIL )` at `itemhandler.scr:1215-1216`. A drawn weapon reads as blown (`player.cpp:5495`) even with the alarm clear; **holstering is the recovery action, taken by the player**, and the re-worded hint (Step 11) is the only in-game cue for it, which is why v2's plan to suppress that hint post-LOUD is reversed. If an auto-holster is ever wanted it must be restricted to players no german currently holds as `m_Enemy`, and that must be said explicitly.

---

### 4.5 SITUATION CONTAINED - the recovery trigger (user decision, 2026-08-10)

**User request, verbatim:** "if no player is spotted for 30 seconds after getting spotted everyone
reverts back to exactly how you were *Situation Contained* your weapons reholster and you get papers
back (goes back to normal). Same after an alarm is raised."

This **replaces the alarm-switch douse as the PRIMARY D1 trigger** and keeps the douse as a second
path into the same state. It adds no new subsystem: the recovery machinery is Steps 21-23 exactly as
already specified. What is new is the trigger (a heat timer) and the announcement.

#### What "reverts" means, precisely

| Thing | On contain | Why |
|---|---|---|
| Weapons | **Reholstered, NOT removed** | The user said "reholster". It is also the only safe option: `activatePlayerWeapon`/`deactivatePlayerWeapon` churn is what the P4 pivot exists to avoid, and un-issuing a kit re-opens every lifecycle hole Step 12 closes. Holstering alone restores `is_disguised` because the engine tests the ACTIVE weapon, not the inventory. |
| Papers | Re-given and re-equipped | `givePapersFlag` + `forcePapersInHand`, the Step 10 recipe. |
| Uniform / `has_disguise` | Re-latched | Step 21c `restoreDisguises`. |
| `level.alarm` | Forced 0 if still 1 | The engine gates `m_bIsDisguised` on `!m_bAlarm`; without this the disguise can never return. |
| `coop_disgSuspended` | 0 | Disguise axis back to INTACT. |
| `coop_stealthPhase` | **STAYS `"loud"`** | The weapons axis is one-way BY DESIGN. Players keep their kit; every later body still spawns armed-and-holstered. This is what makes containment a mercy rather than a punishment, and it is why expectations 4 and 5 ("every later lifecycle event spawns them LOUD") remain satisfied. |
| `m_bForceAttackPlayer` on every actor | **Cleared (engine E5)** | Mandatory - see below. |
| Alerted-AI queue | Cleared + re-arm cooldown | Step 22a; otherwise a queued ringer re-rings within seconds. |
| Alarm-spawned reinforcements already in the world | **Left alive** | Deliberate. They are men who walked here; despawning them in view is worse than leaving them. They simply stop hunting once the latch is cleared and they lose sight. |

#### The hard dependency: without E5 this feature is worse than nothing

`m_bForceAttackPlayer` is set by `ForceAttackPlayer` (`actor.cpp:9339`) and cleared **only** in the
Actor constructor (`:3092`). While set, `EnemyIsDisguised()` returns false unconditionally
(`actor.h:2159-2174`), so that actor can never re-enter a disguise think for the rest of the map.

**Measured in the 2026-08-10 playtest, during the user's intentional bust:** after the player went
DBNO, self-revived and re-disguised, the log shows `AGGRO actor=ai_alarm target=... tgtDisguised=1`
repeatedly from 00:28:08 to 00:28:21 - actors still hunting a player who already read as disguised.
That is the latch, live, on this exact map. Announce "Situation Contained" without E5 and a handful of
guards keep chasing the player forever, which reads as a broken promise rather than a missing feature.

**E5 is therefore promoted from "Phase B3, recommended" to "required before this feature ships."**

#### The genuinely hard part is the SPOTTED predicate, not the timer

A 30-second timer is trivial. Deciding what resets it is not, and it is the SAME predicate problem
that blocks T5 and bug-1652:

- the naive test ("any german in `attack` thinkstate with a player enemy") is true for all **thirteen**
  `$ai_alarm` actors during a perfectly clean QUIET run, because `type_attack "alarm"` maps ATTACK to
  THINK_ALARM. It would never let the timer start;
- `DISGUISE_HALT -> ATTACK` fires purely on the enemy being >256u away (`actor_disguise_common.cpp:96-110`,
  `:150-157`) with no disguise test, so "he escalated because you walked away" is indistinguishable from
  "he made you" by state alone;
- `is_disguised` is a stable fixed point during QUIET, so it cannot be the discriminator either.

**Settled predicate - positive evidence only.** A player is SPOTTED for the purposes of this timer when
ANY of the following happens, and at no other time:

1. a german **fires a weapon** while a player is its enemy (shots are unambiguous), OR
2. a player **takes damage** from a german (the bug-1630 signal, already built), OR
3. `level.alarm` becomes 1, OR
4. a scripted bust fires (`ohnothenaxos1`, `coop_naxosCaught`, the officer/level-2 denial path).

Each stamps `level.coop_lastSpottedTime = level.time`. Nothing else does. Absence of evidence starts
the clock; no state-machine inference is involved, which is exactly why it sidesteps all three traps
above. **This same predicate resolves bug-1652** (a checker shooting at you escalates nothing): rule 1
is precisely "a german is shooting at a player", so it becomes a LOUD trigger and a heat stamp at once.

#### Contain conditions (all must hold)

| # | Condition | Reason |
|---|---|---|
| 1 | `level.coop_stealthPhase == "loud"` | nothing to contain otherwise |
| 2 | `level.time - level.coop_lastSpottedTime >= coop_containDelay` (default 30) | the user's ask |
| 3 | no german currently has a **living player** as `.enemy` with line of sight | the engine will not forget a visible target on a timer (`actorenemy.cpp` visibility decay); containing while seen produces an instant re-spot |
| 4 | every living player is holstered | you cannot be "contained" holding a rifle; also makes the moment player-driven |
| 5 | no player is DBNO | do not hand the squad a stealth state mid-rescue |

On contain: `iprintlnbold "Situation Contained"`, marker `^~^~^ ST CONTAINED t=<heat>`, then the revert
table above, then `coop_disgSuspended = 0`.

**Re-entry is unlimited and cheap.** Getting spotted again simply re-stamps the heat and, if the alarm
rings, re-suspends the disguise axis. Contain -> spot -> contain is a legal cycle; only the weapons axis
is one-way. Cooldown `coop_containReArm` (default 10s) prevents a contain/spot flicker.

#### Deliberate divergence from vanilla, recorded

Retail has no containment mechanic: once m2l2a goes loud it stays loud. This is an addition, not a
restoration, and it is therefore **cvar-gated** (`coop_containEnable`, default 1) and recorded in
`docs/DECISIONS.md` against expectations 6 and 7 rather than shipped as a silent divergence. The
argument for it: it gives the mission a way BACK, which is what makes being spotted interesting instead
of terminal - and with the weapons axis one-way, it never rewinds player progress.

#### Why expectation 3 is load-bearing, not a convenience (established 2026-08-10)

A checker that has started asking gives exactly three outcomes
(`actor_disguise_common.cpp:59-83`):

| Player does | Engine result |
|---|---|
| Presents papers, level too low | `DISGUISE_DENY` - reject anim, back to IDLE after 3000ms, **no attack**. Free to leave, fetch level-2 papers and return. |
| Presents nothing, moves >256u away | `DISGUISE_HALT` -> `THINKSTATE_ATTACK` after 1500ms |
| Presents nothing, waits 12000ms | `DISGUISE_ENEMY` -> attack |

So **presenting papers is the only safe exit from a checkpoint you cannot yet pass**, and the retail
level design depends on it (the papers1 -> papers2 upgrade sits behind sentry2dude, who denies level-1).
Consequences for this plan: expectation 3 is a survivability mechanic, not a quality-of-life feature;
E1 (per-enemy sight trace) is what lets a NON-HOST client be challenged at all and therefore reach the
DENY outcome; and no "grace window to approach a halting checker" is needed - the escape hatch already
exists and is the papers. That closes the bug-1651 open question.

#### Open question for the first playtest

Corpses. If the squad killed guards during the loud window, "Situation Contained" while bodies lie in
the open is odd. Options: (a) accept it - MOHAA AI corpse awareness is weak; (b) require no german
death within the heat window; (c) despawn bodies on contain. **Default (a)**, because (b) makes
containment unreachable in the common case and (c) is more jarring than the bodies. Revisit after the
first run.

## 5. Implementation steps

Ordered so each step is independently verifiable. Commit boundaries are given per step group, deliberately finer than one-per-phase so Step 4 can be reverted without losing the anim-script fixes.

**Step index by phase** (round 2 found Steps 18, 19 and 20 orphaned - present in later tables with no phase and no commit id; they are placed here now):

| Phase | Steps | Commits |
|---|---|---|
| A | 0, 1, 2, 3, 4, 18, 19 | **A0 = 0 (cfg seeds only)**, A1 = 1+2, A2 = 3, A3 = 4-instrument, A4 = 4-fix, A5 = 18+19 |
| B0 | 5 | B0 |
| B1 | 6, **6b** (the engine half of Step 16) | B1 |
| B2 | 7, 8, 9 | B2 |
| B3 | 23 | B3 |
| C | 10, 11, 12, 13, 14, 15, 16-script, 17, 21, 22 | C |
| any | 20 (documentation, section 13) | with each commit |

Six phases, eleven commits, twenty-five steps (0-23 plus 6b). Round 3 corrected three bookkeeping errors here: Step 0 had no commit id, Step 6b was missing from the B1 row (it was listed only as "16-engine"), and the executive summary said 24 steps and five commits.

### Phase A - fix what is already broken

#### Step 0 - add the Phase A kill switch (commit A0, cfg seeds only)

Two new cvars, `coop_disgAggroParity` (Phase A) and `coop_stealthRecoverAlarm` (D1's kill switch, read by Step 21a), both default `1`, both seeded in **all** the places Step 17 enumerates (`hzm-mohaa-coop-mod/autoexec.cfg`, `hzm-mohaa-coop-mod/coop_defaults.cfg`, and the three autotest-homepath copies). **Step 0 owns this seed; Step 17 only back-references it.** It gates:

- **the whole `coop_stealthBlocksAggro` call in `attackPlayer`** (Step 3 item 2). Say this plainly rather than "the funnel guard": with `coop_disgAggroParity 0` the gate is skipped for **every** target, not only NIL ones, and control falls straight to `aihandler.scr:1100-1104`. That is not a regression - today's shipped funnel guard at `:1076` requires `coop_stealthNoAggro != "0"` and both cfgs seed it to `0`, so the shipped funnel is **already fully open**. Parity 0 restores exactly the pre-change behaviour, which is what a kill switch is for;
- Step 4's non-m2l2a exemption heuristics (both the hurt-trooper branch and the `coop_apply_personality` exemption).

It does **not** gate the `aihandler.scr:1021` reader swap of Step 3, which is an unconditional source edit, and there is no longer a `failOpenOnNil` argument for it to gate (deleted in round 3; see P2).

Read it once per label into a local, never per-iteration. Without it, Phase A changes shared code on every map with `git revert` as the only undo.

#### Step 1 - kill the bug-1631 freeze arm outright

`coop_mod/itemhandler.scr::coop_paperPassAll` (`:1176`): **delete** line `:1181`, `local.guard type_disguise "none"`. Keep the `coop_paperPass` one-shot latch and the squad-wide `coop_clickablePapersEnabled` clear.

Comment the rationale in place: `State_Disguise_Accept` (`actor_disguise_common.cpp:159-167`) already performs `SetThinkState(IDLE)` + `SetThink(THINKSTATE_DISGUISE, THINK_DISGUISE_SALUTE)` permanently, so the guard is a saluter after any accept. The swap buys nothing and carries 100% of the freeze risk.

Note for Step 21: the per-guard `coop_paperPass` latch at `:1178-1179` is permanent and cleared nowhere in the tree. Under D1 that is a deliberate choice, not an oversight - a guard who has already accepted the squad's papers stays satisfied across an alarm cycle. Record it as such; do not add a clear without deciding it.

**Step 1 must not ship without Step 2.** Deleting the swap means every accepted guard becomes a permanent saluter, which means `disguise_salute.scr:36`'s always-truthy room test re-evaluates on **every subsequent salute for the rest of the map**. Step 1 alone converts a one-shot freeze into a recurring aggro site. Same commit (A1).

#### Step 2 - make all SIX disguise anim gates per-target and latch-free

| File | Line | Current | Change |
|---|---|---|---|
| `anim/disguise_enemy.scr` | 23 | no disguise test at all | add `self.enemy.is_disguised != 1` |
| `anim/disguise_wait.scr` | 13 | `thread ...canseeUndisguisedPlayers` | replace with `self.enemy.is_disguised != 1` |
| `anim/disguise_deny.scr` | 14 | same | same |
| `anim/disguise_halt.scr` | 18 | same | same |
| **`anim/disguise_accept.scr`** | **10** | same | same - **this is the success path** |
| **`anim/disguise_salute.scr`** | **36** | same | same - fires on every pass after an accept |

In all six, **add the Step 3 per-target gate around the existing `coop_mod/aihandler.scr::attackPlayer` call** - do not read this as "replace `attackPlayer` with something else". All six already call that label; the change is the predicate in front of it plus the hoists below.

**THREE of the six require a structural change, not just a predicate swap - and there are FOUR stranded statements, not three.** Each sits below the attack branch's `end`, so a truthy test silently skips it:

| File | Branch `end` | Stranded statement | Fix |
|---|---|---|---|
| `anim/disguise_accept.scr` | `:16` (`}` at `:17`) | **`self.enemy.flags["coop_clickablePapersEnabled"] = game.false` at `:18`** - found in round 3, missed by v2 and round 2 | hoist above the branch |
| `anim/disguise_accept.scr` | `:16` | `thread ...coop_paperPassAll self` at `:22` | hoist above the branch; `coop_paperPassAll` must ALWAYS run |
| `anim/disguise_deny.scr` | `:20` | `self.enemy.flags["coop_clickablePapersEnabled"] = game.false` at `:22` | hoist above the branch |
| `anim/disguise_enemy.scr` | `:33` | same clear at `:35` | hoist above the branch |

**Blast radius, stated explicitly (round 3).** Step 2 is not m2l2a-scoped and is **not** behaviour-neutral off the disguise maps. The gate it removes, `aihandler.scr::canseeUndisguisedPlayers`, requires `local.actor cansee local.player local.actor.fov local.actor.sight` (`:1230-1239`); the replacement `self.enemy.is_disguised != 1` has **no visibility term**. On maps where no player ever carries `has_disguise`, a checker whose `.enemy` is a player it cannot currently see will now attack where before it did not. Affected map scripts (`type_disguise` writers): `maps/m6l1c.scr` (5 salute writes), `maps/m2l2a.scr` (4), `maps/m1l2a.scr` (1, the saluting checkpoint), `maps/m5l3.scr` (1), `maps/m6l3a.scr` (1), `maps/M3L3.scr` (1), `maps/e1l4/PreShip.scr` (1), plus `m3l1b`, `m3l2`, `t1l2`, `t2l4`, `e1l3/FinalEscape` and `e1l4/Intro`+`MapRoom`. **TP-R must therefore sample a disguise-checker map that is not otherwise covered - `m1l2a` (which is also an open crash-hunt map, so a regression there would be misattributed), and `m5l3` if time allows.**

Without Step 2, one player drawing the locker-room MP40 makes another player's checker attack **him**, three rooms away, mid-papers-check - and expectation 3 and TP-2b (the keystone) cannot pass.

**The verification gate (section 8.4) applies to all six files.** They are `.scr`, and a depth error in any one of them parse-kills the whole file silently.

#### Step 3 - one aggro rule, called from everywhere

`coop_mod/aihandler.scr::attackPlayer` (`:1038`):

1. **Delete** the two dead cvar predicates at `:1076` (`coop_stealthNoAggro`, `coop_stealthFunnelGuard`) and the inline `local.blockAggro` construction (declared at `:1062`, assigned at `:1077` and `:1084` inside the block being deleted).
2. Replace with a single call: `if (waitthread coop_stealthBlocksAggro local.player) { <debug print>; end }`, itself gated by `coop_disgAggroParity`. **Parity 0 skips the whole gate for every target** - see Step 0.
3. **`coop_stealthBlocksAggro` is called unchanged - no second parameter.** Round 3 deleted v2.1's `failOpenOnNil`: the shared NIL walk at `:1213-1222` already ends `(0)` the moment any live player is undisguised, so fail-open buys no aggro and only opens the permanent latch on one propagation path (`aihandler.scr:1015`). See P2. **Edit by label content, not by line range** - here and in item 4; the anchors drift 4-8 lines.
4. Replace the bare `local.enemy attackplayer` at **`:1103`** with `local.enemy attackentity local.player` **when a valid player target was supplied**. Keep bare `attackplayer` only for the NIL-target legacy path. NIL-guard `local.enemy favoriteenemy local.player` at `:1104`, which currently receives NIL on that path. **Preserve `:1102` (`local.enemy.flags["coop_isAttacking"] = game.true`) and `:1101` (`enablePain = 1`) untouched** - `coop_isAttacking` has live readers at `aihandler.scr:1014`, `:1117` and in all six anim gates. Round 3 corrected this anchor from `:1102`, which is the flag write, in all three places the plan cited it.
   - `attackentity` is **advisory**: it calls `ConfirmEnemy` (which clears `m_bEnemyIsDisguised`, `actorenemy.cpp:501` / `:528`) and then lets `PassesTransitionConditions_Attack` decide. `m_bEnemyIsDisguised` is **refreshed every tick the enemy is visible** (`actor.cpp:4033`, inside the `if (bCanSee)` update), so a stale "disguised" verdict can persist only for a target the actor **cannot** see. (v2.1 said "only recomputed in `Actor::SetEnemy`", which is false - and `SetEnemy` early-returns at `:6891-6893` when the enemy is unchanged, so it is not even the per-target refresh path.) That narrow window is the accepted trade against `attackplayer`'s permanent latch.

Apply the same `coop_stealthBlocksAggro` gate at every remaining site that can aggro a player:

| Site | Note |
|---|---|
| `aihandler.scr:1021` (`disguiseHandler` spotting test) | switch the last non-parity reader from the mod flag to `is_disguised`. **The loop this lives in can never restart after an alarm until Step 21 clears `coop_disguiseHandlerThread`** - without Step 21 this edit is unreachable code post-alarm. |
| `aihandler.scr:1281-1290` (`setEnemyAttackStates`) | skip **only** the `local.enemy attackplayer` line at `:1285`. `enableEnemy`, `no_idle` and `coop_actorResetThinkstate` must be restored unconditionally - `setEnemyAttackStates` is their sole restorer. The gate must be evaluated against the enemy **captured in `resetEnemyThinkstates` before it wrote `enableEnemy = 0`**, because `actor.cpp:8608-8626` has already NULLed `.enemy` by restore time; alternatively gate on "any player is engine-disguised". The live caller on m2l2a is per-spawn `giveDisguise` (`:937` -> `:959` / `:974`); `giveDisguiseToAll` is inert here (`:996`). |
| `wounded.scr:219` **and `wounded.scr:336`** | both raw `attackplayer` sites. Neither has a player variable in scope - resolve one first via `replace.scr::player_closestTargetable` (the precedent at `aisquad.scr:104`) and pass it. |
| **`global/wrenching.scr:80`** | **added in round 2.** Reachable on m2l2a through `$wrenchman1`, `$crateguy1` and `$crateguy2`, via `prealarmthread` (`:25`) and `OnPain` (`:47`, `:100-106`). Route through `attackPlayer` with a resolved target. |
| `maps/e1l2/Artillery.scr:87` | passes a real player; keep in scope so the gate is genuinely universal |
| **`coop_mod/weaponstate.scr:75`** | **added in round 3.** The fired branch (`:73-97`) is gated on `level.coop_enableDisguises && coop_hasDisguise && has_disguise` and then does `broadcastSound "explosion" 1024`, `wait 1`, `sentientIsHeard`. Today `takeAllDisguises` clears two of those three on the first alarm (`:1144`, `:1150`) so the branch dies permanently; under Step 21a's non-permanent mode all three survive and it stays live for the whole loud firefight - a divergence from both current behaviour and vanilla, and a full actor-array walk per shot per player. Add `&& level.coop_disgSuspended != 1 && !level.alarm` to the `:75` test |

**Removed from v2's site list:** `aimaneuver.scr:150`. There is no `attackplayer` there - the line is `enableEnemy = 0` + `runto` + `forceactivate`. If the reposition is still unwanted during QUIET, state it as "skip the reposition" and gate the `runto`, not an aggro call that does not exist.

**Not in scope, stated explicitly:** the twelve raw `attackplayer` sites inside `maps/m2l2a.scr` (`:270, :307, :346, :466, :629, :638, :639, :914, :1057, :1106, :1222, :1608`). Step 14 gates `:914` and re-orders `:270`; the rest remain vanilla-latching. **Consequence under D1: those actors would stay disguise-blind through a recovery - which is exactly why E5 (Step 23) is mandatory rather than optional.** Section 7's expectation-7 row is worded accordingly: the funnel is converted, the map's own sites are not.

#### Step 4 - stop the coop AI systems from rewriting scripted scene actors

Round 2 found that v2 aimed this step at the wrong writer. There are **two**, and the one v2 named is downstream of the one it did not.

**Writer 1 (dominant, missed by v2): `coop_mod/officer.scr::coop_apply_personality`.** `aihandler.scr:109-111` threads it for every german actor whenever `coop_aiDynamic == "1"`, which `autoexec.cfg:580` seeds on. It exempts only `type_idle` / `type_attack == "machinegunner"`. Roughly 12% of rolls route to `coop_prone_shooter`, which sets `local.actor.enableEnemy = 0` and then re-issues an `anim_scripted` prone pose on a loop for the actor's whole life, and spawns a `script_aimedstrafinggunfire` aimed at `replace.scr::player_closestTargetable` - which filters on health / spectator / `coop_isActive` / noclip and has **no disguise test** (`replace.scr:396-399`). About 60% of the remaining rolls write `type_attack "cover"`, overwriting the `type_attack "alarm"` that `alarm_system.scr::ai_alarm_setup` force-assigns, and the prone fallback can land up to ~2.5s after spawn, i.e. AFTER the map script's own assignment.

`enableEnemy = 0` reaches `Actor::UpdateEnableEnemy` (`actor.cpp:8608-8626`), which forces `THINKSTATE_IDLE` when the idle-level state is ATTACK, CURIOUS **or DISGUISE**, and then `SetEnemy(NULL, false)`. **A proned papers checker is removed from his disguise think and cannot hold an enemy - he can never be shown papers.** A looped `anim_scripted` is also a far better fit for bug-1631 F3 ("the sit ANIM is being replaced by something invisible to thinkstate probes") than the canteen upper anim.

**Writer 3 (found in round 3, missed by v2 and round 2): `coop_mod/wounded.scr`.** `coop_checkTacticalRetreat` gates at `:107-129` on `coop_retreatEnable`, team, `coop_limping`, `coop_actorStopPainHandler`, `coop_waveActor`, `coop_role == prone`, `coop_retreating`, the officer and turret gunners - **no scene tag, no `alarmthread` test, no `type_disguise` test** - and then commits `local.actor.enableEnemy = 0` at `:206`, `forceactivate` / `runto` at `:207-208`, and a raw `local.actor attackplayer` at `:219`. The terminal limp `coop_checkWoundedRetreat` (`:53-74`) does the same at `:300` and `:336`. Both are threaded from `handlePain` (`aihandler.scr:939` / `:942`) and both defaults are ON (`autoexec.cfg:593` `seta coop_retreatEnable 1`, `:390` `seta coop_woundedRetreat 1`). The pain-streak trigger fires at **full health** after 3 hits under 1.5 s apart (`:110-117`, `:163-166`). Per the same `actor.cpp:8608-8626` reasoning, `enableEnemy = 0` forces IDLE out of a DISGUISE think and NULLs the enemy; `actor.cpp:9339` makes the `attackplayer` latch permanent. Step 3 gates the two `attackplayer` lines but **nothing gates the `enableEnemy = 0` writes**. Apply the same exemption block at the top of both labels, covering `:206` / `:300` as well as the aggro calls. Add `coop_mod/wounded.scr` to section 8.4's touched list, and add a TP-0b / TP-R criterion that no tagged or `$ai_alarm` actor ever emits `^~^~^ RETREATDBG` (`wounded.scr:182`).

**Writer 2 (v2's original target): `coop_mod/aihandler.scr:424-436`,** the hurt-trooper branch. It fires on any actor with `flags["coop_personality_set"] == 1` and hp < 40 - i.e. only on actors Writer 1 already tagged - issuing `type_attack "cover"` and a `coop_trooper_canteen` upper anim without changing thinkstate. m2l2a's card players are hp 2 (`cardgame.scr:288-289, 378-379`) and hp 1 while seated (`:122-123`); the welders and sledgehammer man are hp 1.

**Step 4 is a hypothesis, so it is instrumented before it is fixed.**

**A3 (instrument, no behaviour change).** Two prints, no other change.

In the hurt-trooper branch:

```
local.hasAlarm = 0
if( local.a.alarmthread != NIL ){ local.hasAlarm = 1 }
println "^~^~^ HURT actor=" + local.a.targetname + " hp=" + local.hp + " oldtype=" + local.a.type_attack + " hasAlarm=" + local.hasAlarm
```

`alarmthread` is an EV_GETTER returning a **const array** when set (`actor.cpp:1053-1061` -> `gamescript.cpp:1230-1242`). Concatenating it into a string hits `operator+=`'s `default:` case and throws (`scriptvariable.cpp:1496-1570`). The statement is then skipped silently - so v2's print would have emitted lines **only for actors with no alarmthread**, i.e. never for the welders (`m2l2a.scr:1237-1238`), the cower man (`:1198-1200`), `ohnothenaxos1` (`:1333-1334`) or the two scientists (`:1526-1529`), which are exactly the actors TP-0 exists to attribute. Use the 0/1 boolean. (`type_attack` is safe to concatenate: `EventGetTypeAttack` returns a ConstString, `actor.cpp:8262-8265`.)

At the top of `coop_apply_personality` (`officer.scr:1660`), before the roll, print `^~^~^ PERS actor=... roll=... type=... hasAlarm=0|1`, and inside `coop_prone_shooter` print one **`^~^~^ PRONEPOSE actor=<targetname> wg=<group>`** per actor that actually poses.

**Three constraints on that second print, all found in round 3:**

- **Do not call it `PRONEDBG`.** A `^~^~^ PRONEDBG wg=` print **already ships** at `officer.scr:1736`. Reusing the name collides with it and makes TP-0b's grep ambiguous.
- **Place it AFTER the weapongroup whitelist reject at `:1740-1744`** (`type_attack "cover"; end`). The shipped `:1736` print sits *above* that reject, so it fires for actors that never pose - which is not what TP-0b is measuring.
- **Gate it on `coop_aggroDebug`**, the convention already used at `aihandler.scr:1053`, **not** on `coop_aiBehav`. The shipped `:1736` print is gated at `:1735` on `coop_aiBehav`, which section 8.1's preamble never sets, so it is silent under the test recipe anyway. Section 8.2 records `^~^~^ PRONEDBG wg=` as a **different, pre-existing marker**.

A3's prints are kept behind `coop_aggroDebug` through A4 and every later stage (they are read again by TP-R's baseline diff); **Step 20's cleanup commit removes them.**

Run one solo TP-0 pass.

**A4 (fix, written against what the log showed).**

*Tagging.* **BLOCKER FIXED IN ROUND 3 - the tagging cannot live in `stealth.scr::init`.** Step 14 wires `init` at `maps/m2l2a.scr:38-42`, which is inside `main` and **85 lines above** everything the tag set depends on:

- `thread global/alarm_system.scr::alarm_system_setup` is at `:123`, and its `ai_alarm_setup` is the **only** writer of `self.alarmthread` for the `$ai_alarm` set (`global/alarm_system.scr:336-337`). At `:38` **no actor has an alarmthread**, which kills both the `alarmthread != NIL` derivation and the `alarmthread` exemption.
- All ten level-var scene actors are assigned at `:124-135` via `find_guy` (`guythatlikesnorway`, `guythathatesnorway`, `whatsthesub`, `hushyhushy`, `stupid`, `jokey`, `goatsbutt`, `sentry2dude`, `officer1`, `loweralarmerguy`). At `:38` **every one of them is NIL**.

Run as written, the tag set would be roughly half its intended size, `^~^~^ST BOOT` would still print, the map would still play unarmed, every proof-of-load criterion in 8.1 would pass, and TP-0b's criterion ("zero prone markers on the tagged m2l2a scene set") would pass **vacuously** on an empty set. Same silent-failure class as round 2's B-5.

**Therefore `init` is split in two:**

| Label | Called from | Does |
|---|---|---|
| `stealth.scr::init` | `maps/m2l2a.scr:38-42`, single frame, no `wait` | trio, `coop_stealthPhase = "quiet"`, `coop_stealthArmEpoch = 0`, `^~^~^ST BOOT`, `quietWatchdog`, `alarmWatcher`, the loose-weapon sweep thread (Step 15) |
| `stealth.scr::initScene` | `maps/m2l2a.scr`, **after `:135` and before `:163`**, `waitthread` | `coop_sceneActor` tagging (targetnames + level vars + the `$ai_alarm` / `alarmthread` derivation), `protectScene`, and `^~^~^ST TAGGED n=<count>` |

Two further hardenings, because the ordering against the writers is not otherwise provable:

- The roll that must be exempted is taken **with no yield**: `aihandler.scr:109-111` threads `coop_apply_personality` for every german under `coop_aiDynamic`, and `officer.scr:1675-1677` latches and rolls immediately. **Make the exemption order-independent**: re-check the tag inside `coop_prone_shooter` (which yields at `officer.scr:1720` / `:1728`) and restore `type_attack` for any actor that turns out to have been tagged after its roll.
- **The acceptance stage must assert the tag COUNT** (`^~^~^ST TAGGED n=` against the expected set size), not merely the absence of another marker - an absent marker on an empty set is not evidence. **That stage is TP-2, not TP-0b**: `initScene` is Phase C and gated on `coop_stealthStart`, while TP-0b runs the current armed flow with no stealth start, so TP-0b can only measure the `alarmthread` and `type_disguise == "salute"` halves of the exemption. Say so in both stages rather than letting a reader assume A4 is fully validated by TP-0b.

On the tag set itself, two hard constraints round 2 established:

- **Never assign a property on a targetname that can resolve to more than one entity.** `$suckyfatty` is **three** entities (`map_entities/m2l2a_entities.txt:3558, :3583, :3608`), and a scalar `.flags[...] = 1` on a container throws `Cannot cast 'container' to listener` (`scriptvm.cpp:1794-1819`, `:1610-1623`; `scriptvariable.cpp:1108-1109`). Tag by iteration: `for( local.i = 1; local.i <= $suckyfatty.size; local.i++ ){ $suckyfatty[local.i].flags["coop_sceneActor"] = 1 }`.
- **Use the verified names.** Targetnames: `$suckyfatty`, `$guy1`, `$guy2`, `$guy3`, `$welderguy1`, `$welderguy2`, `$sledgehammerguy`, `$wrenchman1`, `$crateguy1`, `$crateguy2`. Level vars (NOT targetnames; resolved by `find_guy` at `m2l2a.scr:124-135`): `level.jokey`, `level.stupid`, `level.goatsbutt`, `level.whatsthesub`, `level.hushyhushy`, `level.sentry2dude`, `level.officer1`, `level.loweralarmerguy`, `level.guythatlikesnorway`, `level.guythathatesnorway`. v2's list wrote "wrenchman" (actual `$wrenchman1`) and prose ("the crateguys", "the welders"), which would have silently left the three hp-1 actors untagged.
- Better still, derive rather than hand-maintain: additionally tag every member of the `$ai_alarm` array and every actor whose `alarmthread != NIL`, so the list cannot drift.

*Exemptions.* Skip **both** writers when any of:

- `local.a.flags["coop_sceneActor"] == 1` - permanent, no phase clause. A `phase == "quiet"` condition would re-arm these branches on the hp-1 welders the instant T1/T3/T4/T5 fired, and the plan's own pivot is that a non-alarm LOUD leaves the map functionally stealthy.
- `local.a.alarmthread != NIL` - gated by `coop_disgAggroParity`. **v2's second condition, "or its `type_attack` was force-assigned", is deleted: there is no script-visible provenance for `type_attack`** (only a current-value getter, `actor.cpp:753-760`), so it cannot be written.
- **`local.a.type_disguise == "salute"`, and only that value.** Round 3: v2.1 wrote "carries a `type_disguise` checker role" with no predicate, and the naive reading (`!= NIL && != ""`) would exempt the **35** actors written `type_disguise "none"` across the tree (19 bare, 16 `=` form, in `itemhandler.scr`, `cardgame.scr`, `movecrate.scr`, `e1l4/MapRoom.scr`, `e1l4/PreShip.scr`, `m2l2a.scr`, `m3l1b.scr`, `m6l1c.scr`), stripping `coop_aiDynamic` - seeded on at `autoexec.cfg:580` - from large populations on maps TP-R does not sample. `"salute"` is written 13 times and is the actual checker role; `"machinegunner"` (12) is already exempt at `officer.scr:1672-1673`. **Never exempt on `"none"`.**

*Additionally, and regardless of tag:* forbid `coop_prone_shooter` outright for any actor with a set `alarmthread`, `type_disguise == "salute"`, or `type_attack == "alarm"`. `enableEnemy = 0` on a checker is unrecoverable within the disguise system. Note this covers the prone branch only - the ~60% `type_attack "cover"` overwrite is stopped by the tag/`alarmthread` exemption above, which is why the ordering hardening matters.

Do **not** attribute a TP-0 card-player result to Step 4 without first reconciling bug-1636 and bug-1637.

#### Step 18 (Phase A, commit A5) - papers across DBNO

`dbno_enter`'s `takeall` strips the papers item; restoration is `coop_key_guardian`'s 1s-delayed `itemGetAll` - a papers-less window of at least 1.5s on a body that can be standing inside a checker's PAPERS state. Restore the papers on the revive path itself rather than waiting for the guardian.

This is shared code: the guards at `coop_mod/dbno.scr:231`, `dbno.scr:728` and `coop_mod/medkit.scr:376` are `if( !level.coop_noWeapon ){` and their in-code comments name e1l3 explicitly. Any change here needs the TP-R regression pass, which is why this is Phase A and not Phase C.

#### Step 19 (Phase A, commit A5) - the papers2 swap gap

`maps/m2l2a.scr:417-418` does `waitthread global/items.scr::remove_item "papers_level1"` then `add_item "papers_level2"`. `remove_item` routes through `replace.scr::take models/items/papers.tik`, so it **physically strips the papers from every already-spawned player's hands** and sets `level.papers = 0` across a multi-frame window. The per-body block gates on `level.papers >= 1` with no retry.

Consequences: a spawn or late join landing in that window gets no papers item and no `coop_hasPapers` flag, is never retried, cannot answer a challenge, and times out into ENEMY. And a player already standing inside a checker's PAPERS state has the item removed from his hands mid-challenge.

Fix, both halves:
1. After the swap completes, re-run `givePapersFlag` and `forcePapersInHand` for **every active player** - not just future spawns.
2. Make the spawn-path give retry, or key it on `level.coop_itemPapers` alone rather than on `level.papers >= 1`.

*Phase A is shippable on its own and should be playtested (TP-BASE, TP-0, TP-0b, TP-1, TP-R) before Phase B.*

---

### Phase B - engine, split by testability

All feature edits sit behind the existing `g_coopDisgParity`; the B0 guards do not (a NULL guard has no sane "off"). Deploy per bug-1634 to **both** roots (`G:\mohaa-gl2\` and the GOG root), ship `game.pdb` beside `game.dll`, and verify per bug-1635 before any verdict.

#### Step 5 - B0 (ship immediately, independent of this feature): three NULL guards

Not one site, three. All are the bug-242 family and all are reachable on a dedicated server or with a disconnected client 0.

1. **`actor.cpp:9039`** - `PassesTransitionConditions_Disguise` does `Entity *player = G_GetEntity(0);` and dereferences `player->centroid` at **`:9045`**, passing `player` as passent2 at **`:9047`** (`:9041` is the `return G_SightTrace(`). **Round 3 restored these anchors: round 2's "correction" to 9038/9042/9044 was wrong on all three - `:9038` is blank - and that parenthetical is withdrawn.** The function early-returns unless `m_Enemy` is non-NULL and `EnemyIsDisguised()`, and `m_bHasDisguise` is only ever written on a Player (`player.cpp:11386`), so **a disguised client 1 with no client 0 reaches `:9045` with `player == NULL`**.
2. `actor_grenade.cpp:348-350` and `:440-442` - `if (!IsTeamMate(static_cast<Sentient *>(G_GetEntity(0)))) { ForceAttackPlayer(); }`. `Sentient::IsTeamMate` returns **false** for NULL (`sentient.cpp:4008-4019`), so a NULL entity 0 falls THROUGH into `ForceAttackPlayer`, which is `ConfirmEnemy(this, NULL)` -> `AddPotentialEnemy(NULL)` -> unguarded dereference at `actorenemy.cpp:279-281`.
3. `actorenemy.cpp:279` - NULL-guard `AddPotentialEnemy` itself, so no future caller can reproduce it.

Ship as its own bug-fix commit with its own buglog entry, ahead of everything else. Pair item 2 with the `ForceAttackPlayer(Sentient*)` overload of Step 6 so the grenade sites can blame the actual thrower (`m_pGrenade->edict->r.ownerNum` is in scope) rather than the host.

#### Step 6 - B1: E2, judge the obstacle bump against the actual colliding player

`actor.cpp:3354-3377` (ANIM_MODE_DEST) and `:3380-3405` (ANIM_MODE_PATH).

**The draft's proposal - "skip when the blamed player reads `m_bIsDisguised`" - is already done.** Both branches are guarded by `if (p && !IsTeamMate(p))`, and `IsTeamMate` returns true when `pOther->m_bIsDisguised` (`sentient.cpp:4018`). bug-1640 records precisely this and names the residual.

The actual edit, three items (v2 had two, and round 2 showed item 1 alone cannot pass TP-7):

1. Resolve the colliding player by scanning **`mm->touchents[0 .. mm->numtouch-1]`** for `IsSubclassOfPlayer()` rather than using `G_GetEntity(0)` at `:3357` and `:3387`. `mmove_t` carries both fields at **`g_local.h:490`** (`numtouch`) and **`:491`** (`touchents[MAXTOUCH]`). **The scan is NOT exact, and round 3 corrected the wording:** `MM_AddTouchEnt` sets `mm->hit_temp_obstacle |= 1` at `g_mmove.cpp:97-99`, the MAXTOUCH capacity return is at `:105-107` - **after** the flag set - and the append is at `:117-118`, so the flag can be set with **no** entnum recorded (MAXTOUCH is 32, `bg_public.h:289`); and `touchents` can name more than one player. So: **exactly one player found -> blame that player; zero or more than one -> skip the aggression branch entirely.** Never judge by client 0. Note this makes TP-7's "identical whether the blocker is host or client" criterion measure the one-player case, which is what TP-7 stages.
2. **Add `void Actor::ForceAttackPlayer(Sentient *pWho = NULL)`** - confirm `pWho` when non-NULL, fall back to `G_GetEntity(0)` otherwise - and pass the resolved player from both obstacle branches (`:3376`, `:3404`). Without this the judgement is correct and the aggro target is still the host: `ForceAttackPlayer` hardcodes `ConfirmEnemy(this, G_GetEntity(0))` inside the helper (`actor.cpp:9336-9340`). Guard for NULL, because `ConfirmEnemy` -> `AddPotentialEnemy` dereferences without checking.
3. **Skip the WHOLE aggression branch** - `m_bDesiredEnableEnemy` / `UpdateEnableEnemy`, `BecomeTurretGuy()` AND `ForceAttackPlayer()` - when `CurrentThink() == THINK_ANIM || CurrentThink() == THINK_ANIM_CURIOUS` (`actor.h:1441`, `:1859`, `:374-375`), gated on `g_coopDisgParity`. v2 said "skip `BecomeTurretGuy`", mirroring `CoopMannedTurretHold()` at `:3373` / `:3401`. **That is insufficient**: `BecomeTurretGuy` only rewrites the think map (`actor.cpp:13098-13109`); it is `ForceAttackPlayer` that confirms an enemy and sets the permanent `m_bForceAttackPlayer` latch, which `actor.h:2159-2173` turns into lifetime disguise blindness. Leaving `ForceAttackPlayer` running is right for a manned-turret gunner and wrong for a card player or a walking crateguy.

**B1 lands before TP-2** because it is solo-reachable: one player standing in a doorway is enough.

#### Step 6b - B1 (engine half of Step 16): suppress the spawn loadout

`Player::EquipWeapons()` is called from the engine spawn path at `player.cpp:9790-9791`, **before any script runs**. While that DM weapon is active, `player.cpp:5491-5497` computes `m_bIsDisguised = false`, and two engine reactions then need no script at all:

- `Begin_DisguiseSentry` falls to `SetThinkState(THINKSTATE_ATTACK, THINKLEVEL_IDLE)` when the enemy is not disguised (`actor_disguise_sentry.cpp:53-63`; same shape in `actor_disguise_officer.cpp:53-63`);
- `Think_DisguiseSentry` does `TransitionState(ACTOR_STATE_DISGUISE_ENEMY, 0)` (`:102-104`) - and there is **no path back** (the guard at `:102` excludes `DISGUISE_ENEMY`), with `State_Disguise_Enemy` escalating to `THINKSTATE_ATTACK` 3000ms later regardless of the player re-holstering.

So a single frame of armed respawn inside a checker's view is a guaranteed bust 3s later, and **no script gate can undo an engine thinkstate transition that has already happened.** Add an edit in `Player::EquipWeapons` (`player.cpp:9931`, called from the spawn path at `:9791` and again at `:11299`) that suppresses the spawn loadout while the director wants unarmed bodies.

**Name the key, do not leave it to the implementer (round 3).** v2.1 said "keyed on a coop cvar readable from the engine"; there is no such cvar. A grep of the whole `openmohaa-hzm/code` tree for `coop_noWeapon`, `coop_startUnarmed`, `coop_stealth`, `coopStealth` and `coopUnarmed` returns **zero** matches - the trio is three script `level` variables the engine cannot see. The mechanism is therefore:

- **`stealth.scr::init` `setcvar`s a dedicated, NON-archived cvar, `g_coopSpawnUnarmed 1`.** It must not be a `seta` cvar: `coop_stealthStart` is archived (`seta`, `autoexec.cfg:1175` / `coop_defaults.cfg:207`) and session-global, so keying on it would leak the suppression across every later map in the session.
- **`coop_mod/main.scr::main` resets `g_coopSpawnUnarmed 0` at every map load**, so a transition out of m2l2a cannot inherit it.
- **`goLoud` does NOT clear it.** `managePlayerInventory` runs `group.player takeall` unconditionally at `itemhandler.scr:708` on every spawn on every coop map, so the engine kit is discarded on every body anyway; suppressing it for the map's whole lifetime is harmless post-LOUD and needs no fourth trio member and no extension to the `^~^~^ST TRIOBREAK` assert.
- The **behaviour** edit is still gated on `g_coopDisgParity`, matching the phase table's B1 kill switch, so parity 0 restores the vanilla spawn kit.

**Add a TP-R criterion that the spawn loadout still arrives normally** on the combat map and on e1l4 - v2.1's TP-R criteria contained no such check for an engine edit whose blast radius is every map. This is solo-reachable and must land before TP-2.

#### Step 7 - B2a: E1, retarget the disguise sight trace

Same function as Step 5 item 1. Under `g_coopDisgParity`, trace `m_Enemy->centroid` with an `m_Enemy != NULL` guard; parity 0 restores the vanilla entity-0 trace **written from the B0-guarded text, keeping the NULL guard on both branches**. E1 subsumes B0 on these lines - do not let the parity-0 fallback reintroduce the unguarded dereference.

Solo-host behaviour is provably identical because `m_bHasDisguise` is only ever written on a Player (`player.cpp:11386`), so with one client `m_Enemy` **is** entity 0.

Without it, only the host can ever be challenged, therefore only the host can earn a papers ACCEPT, therefore only the host can disarm the `sentry1trigdisable` / `sentry2accept` punish nets.

#### Step 8 - B2b: E3, fix papers-challenge timing (two defects, not one)

The v2 diagnosis was half right. Both halves must be fixed or 2P+ papers remains broken.

**8a - the timestamp comparison.** `m_iEnemyShowPapersTime` is snapshotted at `Begin_Disguise*` and **also re-stamped by `Resume_Disguise*`** (`actor_disguise_sentry.cpp:72-76` -> `:58`; same at `actor_disguise_officer.cpp:72-76`), so a papers press during a pain or grenade suspension is discarded today. v2's proposed re-stamp inside `SetEnemy` does not cover the Resume path, and it introduces a new discard: if A presses while the sentry's `m_Enemy` is B, vanilla honours the press on the switch back (A's Begin-time snapshot is still 0 < `A.m_ShowPapersTime`), whereas the re-stamp sets `m_iEnemyShowPapersTime = A.m_ShowPapersTime` and silently swallows it, with the 12s clock still running.

Fix instead by replacing the snapshot semantics: in `State_Disguise_Papers` and `State_Disguise_Fake_Papers`, test **`m_Enemy->m_ShowPapersTime > m_iStateTime`** (papers presented after this challenge began) rather than comparing against `m_iEnemyShowPapersTime`. Both fields are `level.inttime`-based (`ActivatePapers`, `inventoryitem.cpp:81-84`). This fixes the enemy-churn case and the Resume case together.

**If the snapshot form is kept anyway**, the re-stamp must go **INSIDE the existing `if (m_Enemy)` block at `actor.cpp:6903-6914`, after `m_Enemy = pEnemy;`** - never at the top of `SetEnemy`. `Actor::SetEnemy` assigns `m_Enemy` unconditionally at `:6889` and `SetEnemy(NULL)` is routine (`:3270`, `:5418`, `:6821-6822`, `:8625`), so an unguarded re-stamp is a hard server crash on every disguise map. v2 specified the `m_Enemy != NULL` guard in Step 7 and omitted it in Step 8; the omission is corrected here.

**8b - the distance measurement (missed entirely by v2).** `Think_Disguise*` calls `UpdateEnemy(1500)` every tick, `m_bEnemySwitch` defaults true (`actor.cpp:3115`), and `CheckEnemies` selects the current enemy by **visibility, not range** (`actorenemy.cpp:400-410`), deliberately retaining disguised enemies (`:474`). So with 2-4 disguised players the checker's `m_Enemy` can switch to a fully visible player **further than 256u away**, at which point `State_Disguise_Papers` measures the wrong player, transitions to HALT (`actor_disguise_common.cpp:106-110`) and escalates to `THINKSTATE_ATTACK` 1500ms later - with no player having done anything wrong.

Fix: under `g_coopDisgParity`, set `m_bEnemySwitch = false` for the duration of a disguise think (`Begin_Disguise*` to `End_Disguise*`, restoring on exit; precedent at `actor.cpp:13132`/`:13142`), or re-run the `Begin_Disguise*` snapshot on every `m_Enemy` change while `m_ThinkState == THINKSTATE_DISGUISE`. v2's parenthetical rejecting the `m_bEnemySwitch` option is withdrawn - the re-stamp alone leaves 8b open. **2P+ defect; add to TP-3.**

#### Step 9 - B2c: E4, AI-event mute for any disguised player

`g_utils.cpp:1798-1804`: the `AI_EVENT_MISC` / `AI_EVENT_MISC_LOUD` global mute tests client 0's disguise only. Door noise and other misc events therefore go unmuted for clients 2-4 even when they are disguised - and m2l2a's stealth route runs through `$likeynorwaydoor`.

**The rule is the fallback, not the originator test.** Round 2 verified that every in-tree MISC producer passes a **non-Sentient** originator into `Entity::BroadcastAIEvent` (`doors.cpp:597/628/665/723`, `misc.cpp:447/536`, `weapon.cpp:4391` - a `Weapon` is an `Item`), Sentient footsteps use `AI_EVENT_FOOTSTEP` which this test does not cover, and there are **zero** `broadcastaievent` calls in any `.scr` in the mod. So an originator-Sentient branch would be dead code, and v2's claim that "the originator test collapses to the client-0 test in solo" is unfounded.

Under `g_coopDisgParity`: **mute when ANY connected player is `m_bIsDisguised`.** Optionally restrict a per-originator refinement to `originator->IsSubclassOfPlayer()`; otherwise drop the originator clause.

**TP-9 is the only evidence for E4, so E4 must emit its own observable (round 3).** v2.1 gave TP-9 a single grep, `^~^~^ AGGRO_SRC`, which has exactly three emitters - all in `coop_mod/aihandler.scr` (`:1023`, `:1166`, `:1283`) and none on the AI-event path - so an absent marker could equally mean "E4 muted the door event", "the Norway pair never had line of sight" or "Step 14's `waitForEnemy` gate blocked the funnel for an unrelated reason". Add a `g_coopDisgDebug`-gated `Com_Printf` inside the E4 branch: **`^~^~^ AIEVENT MISC muted=<0|1> anyDisguised=<n>`**. Register it in the 8.2 grammar and make it TP-9's primary grep, with `AGGRO_SRC` demoted to a secondary negative check.

**B2 lands after TP-2b passes.** E1, E3 and E4 are multiplayer-only by construction; TP-0 through TP-2b cannot exercise any of them.

#### Step 23 - B3: E5, clear the disguise-blind latch on the douse edge (D1)

`m_bForceAttackPlayer` is written in exactly two places - the constructor (`actor.cpp:3092`, false) and `ForceAttackPlayer` (`:9339`, true) - and `Actor::EnemyIsDisguised` (`actor.h:2159-2174`) returns false unconditionally while it is set. Every actor latched during a loud window is therefore **permanently unable to be fooled by any disguise, for the rest of the map**. Without E5, D1's recovery is cosmetic: the players' uniforms come back and the guards who were fighting them stay hostile forever.

**The hook is CHOSEN, not offered (round 3).** v2.1 named `Level::SetAlarm` as "natural" and an `unforceattackplayer` actor event as an alternative, without deciding. `Level::SetAlarm` is the wrong one, on three counts:

- It is the **sole** script write path for `m_bAlarm`, so it fires on **every** scripted `level.alarm = 0` in the tree: `coop_mod/e1l4alarm.scr:36` (the shipped e1l4 alarm-silence feature), `global/alarm_system.scr:728`, `maps/e1l3/FinalEscape.scr:830/833/865/956` (four mid-map writes, during an active firefight, on a map section 15.4 declares out of scope), `maps/e1l4/Ship.scr:8`, `maps/m2l2a.scr:111`, `maps/m2l2b.scr:55`, `maps/m6l1c.scr:111`.
- It is `m_bAlarm = ev->GetInteger(1);` with **no old-value capture** (`level.cpp:2067-2070`), so "on the 1 -> 0 edge" is not even implementable there without adding one.
- Walking `level.m_HeadSentient[TEAM_GERMAN]` from there is a **type error waiting to happen**: that array is `class Sentient *` (`level.h:221`), populated by `Sentient::Link` (`sentient.cpp:932` / `:936`) for every Sentient of the team including a player on the axis `dmteam` (which this mod supports - `player.scr:1097-1159`), and `m_bForceAttackPlayer` is an **Actor** member (`actor.h:728`). An unchecked `(Actor*)pSent` write is an out-of-bounds write.

**Fix, as specified:** expose a scoped `unforceattackplayer` actor event that clears `m_bForceAttackPlayer` (and `m_bEnemyIsDisguised`), and call it from `stealth.scr::onAlarmDoused` **after `restoreDisguises` and after 22b**, so it cannot fire on e1l3's escape, on e1l4's silence feature, or on any map that never runs the director. Whatever walk is used to reach the actors must carry an `IsSubclassOfActor()` guard, and note that dead-but-unremoved actors stay linked. Gate on `g_coopDisgParity` **and** `g_gametype->integer != GT_SINGLE_PLAYER`: `player.cpp:5486-5490` deliberately forces the parity block on in SP, so a cvar-only gate would change retail single-player, where `m_bForceAttackPlayer` is archived into savegames (`actor.h:1949`). (If the SP change is wanted, record it in `docs/DECISIONS.md` rather than letting it happen by omission.)

**E5 also ships the T5 getter.** Expose `m_bForceAttackPlayer` read-only as **`forceattackplayer`**, which section 4.2's re-derived T5 condition 4 depends on and which gives TP-10 a direct observable. Add a parity-gated `Com_Printf` of the cleared count on each douse - `^~^~^ E5 cleared=<n>` - because without it TP-10 cannot distinguish "E5 worked" from "line of sight never broke", and the same stage is asked to accept the latter as a non-failure.

Note this does **not** make a hostile guard instantly friendly. Per P5, an actor already in `THINKSTATE_ATTACK` is structurally disguise-blind until it loses the enemy, which requires losing line of sight (`actorenemy.cpp:420-423`). E5 removes the permanent block; LOS removes the current one. **TP-10's "re-challenge within a bounded time" is given a number: 30 seconds from `^~^~^ST QUIETDISG` for the from-cover leg.**

---

### Phase C - the stealth director

#### Step 10 - fix `managePlayerInventory`'s uniform hole (DUPLICATE, never MOVE)

`coop_mod/itemhandler.scr`: the `giveUniformToPlayer` / `takeUniformFromPlayer` pair sits at `:762-766`, **below** the `coop_noWeapon` exit at `:745`, so it is unreachable during a stealth window. Today, every mid-stealth respawn, spectate-return, DBNO corpse-revive and late join materialises in the U-boat pens as an **Allied GI**. This is bug-1624 recommitted one field over.

**v2 offered "move it, or duplicate it". The move option is deleted.** Round 2 verified that `:765` is the **only** caller of `takeUniformFromPlayer` in the entire mod, and that the label also carries the per-spawn FOV re-apply (`local.player stufftext ("vstr g_m2l1")` at `:842`) and the enemy-uniform sanity reset (`:822-835`), which run for every player on every spawn on every map. The stealth block at `:719` is gated on `level.coop_startUnarmed`, which only `maps/m2l2a.scr:40` sets - so a moved pair would be **unreachable everywhere else**, losing the uniform give on e1l4 and m2l2b and the take (with its FOV reset) on every map in the game.

The edit is therefore: **add a give-side copy inside the `:719` block, after `waitthread giveDisguiseOnSpawn` at `:728`** (so `has_disguise` is already latched), guarded on `level.coop_enableDisguises && level.coop_uniformOnSpawn && group.player.flags["coop_hasDisguise"] && group.player.has_disguise`. **Leave `:762-766` byte-identical.**

Scope note: e1l3 is a papers-only map and never sets `level.coop_enableDisguises` (only `maps/e1l4.scr:23`, `maps/m2l2a.scr:27` and `maps/m2l2b.scr:15` do), so it is unaffected either way. e1l4 and m2l2b already reach the give normally. **This fix is m2l2a-scoped.**

**Second half of Step 10 - the armory-skin stomp (found in round 2).** `giveUniformToPlayer` (`itemhandler.scr:856`) writes `local.player.model = "models/player/german_waffenss_officer.tik"` and contains no yielding call, so it completes in the frame it is threaded from `managePlayerInventory`. Later in the **same** `player.scr` label that called `managePlayerInventory` at `:1012`, the armory-skin re-force runs (`player.scr:1097-1159`): it reads `flags["coop_armorySkin"]`, falls back to the host's `coop_loSkin`, and does `local.player model ("models/player/" + local.forceSkin + "_nohat.tik")` + `helmet_apply`, and again in the locked-skin heal below. Its only exclusions are `dmteam == axis` and `spectator` - **nothing tests the disguise.** Moving the uniform give earlier makes the stomp strictly more certain.

Gate the armory-skin re-force and the locked-skin heal on `level.coop_uniformOnSpawn != 1 && local.player.flags["coop_hasEnemyUniform"] != 1`, or move the uniform give to the end of `manageAliveSpawning`. Record the ordering constraint in this step and add a worn-model check to TP-5's pass criteria.

#### Step 11 - split the arming path (the pivot)

`coop_armOnBlown` gains a `local.drawWeapon` parameter and is refactored into three same-file labels in `itemhandler.scr`:

- **`coop_armOnePlayer` (self = the player)** - `coop_armOnePlayer:{ group.player = self; ... }`, called as `local.player waitthread coop_mod/itemhandler.scr::coop_armOnePlayer`. **Round 3 settled this: `self`, never an argument.** v2.1 described it two different ways in two adjacent steps (Step 11 said "sets `group.player` from the argument", Step 12 showed the `self` form, Step 13 hedged "from `self` or from an argument"), which is the exact class of defect round 2 recorded as L1-12 and claimed fixed. Implemented per the argument form but called per the `self` form, `group.player` arrives NIL, `giveWeaponLoadout` errors on its first statement (`itemhandler.scr:1430`), and per `scriptvm.cpp:1881-1883` the Script Error does **not** kill the thread - the epoch re-give silently gives nothing. `Listener::CreateThreadInternal` passes `this` as the new thread's `self` (`listener.cpp:4192-4206`), so the `self` form is provably correct;
- `coop_armAllOnBlown <draw>` - the loop over active players, guarded by its **own** `level.coop_armAllDone` latch (see the blocker note in section 4.3), **not** by any `coop_startUnarmed` test;
- `coop_drawAllWeapons` - the draw pass, callable independently, **resolving each weapon by name rather than through `activatePlayerWeapon`** (section 4.3).

**Restate the cross-file rule correctly.** v2.1 called `coop_armOnePlayer` "the only entry point safe to call across a file boundary", which section 4.3's own pseudocode then violates three times. The rule is narrower: **a cross-file call is unsafe only to a label that READS an inherited `group`** - that is `giveWeaponLoadout` (`itemhandler.scr:1430`, `:1449`, `:1460`, `:1491`, `:1498`). `coop_armAllOnBlown` and `coop_drawAllWeapons` populate `group` themselves or do not use it, so calling them from `stealth.scr` is fine.

Behaviour:

- The trio clear has moved into `goLoud` (section 4.3), **and `coop_armOnBlown`'s `if( level.coop_startUnarmed != 1 ){ end }` at `:1395` is deleted with it**, replaced by `coop_armAllDone`. Keeping that test alongside the moved clear was the round-3 blocker: it would have read a flag its own caller cleared four statements earlier and armed nobody, silently, on the first LOUD of every run.
- `drawWeapon == 1` (alarm only): `wait game.ms` + `activatePlayerWeapon` + the "Cover blown - weapons free!" print, via `coop_drawAllWeapons`.
- `drawWeapon == 0` (T1, T3, T4, T5, T6, T7): **no** `activatePlayerWeapon`. Print "You have your weapons - draw when you're ready."
- **Exclude downed players from the arming loop.** The filter at `:1405` is `local.p != NULL && local.p.flags["coop_isActive"] == 1 && isAlive local.p`, and a DBNO player satisfies both terms (`dbno.scr:174` `healthonly 100`; `:185` sets only `coop_dbno_active`, never `coop_isActive`). Arming a downed player also runs `thread resetPlayerWeapons group.player` at `:1460`, which NILs `coop_inventoryWeapons` - the tier-1 restore source `dbno_revive` reads at `dbno.scr:729` - and with `draw == 1` stands a rifle up on a crawling body. Add `local.p.flags["coop_dbno_active"] != 1` to the filter, and **add an arm-on-revive hook** in `dbno.scr`'s revive path and `medkit.scr`'s self-revive path for when `level.coop_stealthPhase == "loud"`.

**`giveWeaponLoadout`'s tail must split on PHASE, not on `has_disguise`.** Round 2 found this is a plan-introduced regression, not shipped behaviour: today `takeAllDisguises` clears `has_disguise` at `:1150-1152` **before** calling the arm, so the else branch runs. Under P4, `has_disguise` still holds at a non-alarm LOUD, so `giveWeaponLoadout` takes the `:1498-1508` branch - which contains only `setIsDisguised`, `wait 0.25`, `deactivatePlayerWeapon`, `setIsDisguised`, the hint. It does **not** run `coop_backfillPrimaries` (`:1546`, which re-issues any 2nd+ PRIMARY the engine's team-mode pickup rule drops) or `spawnWeaponAssert` (`:1541`), both of which live only in the else branch at `:1509-1547`. Because `level.coop_enableDisguises` is never cleared on a non-alarm LOUD, `managePlayerInventory` re-grants the disguise at `:758-759` on every later respawn and the same short kit is handed out again, forever.

Therefore:

- run `coop_backfillPrimaries` and `spawnWeaponAssert` **unconditionally**;
- **the holster branch predicate must include the disguise axis.** Write it as `if( level.coop_stealthPhase == "quiet" || ( group.player.has_disguise && level.coop_disgSuspended != 1 && !level.alarm ) )`. v2.1 wrote it as `phase == "quiet"` **or** "the player still holds an intact disguise", which during a live alarm is TRUE (Step 21a deliberately keeps `has_disguise`) - so every mid-alarm respawner would take the `:1498-1508` holster branch and stand up unarmed-looking with the hint, where today `itemhandler.scr:1150` clears `has_disguise` on the alarm and the else branch runs armed and drawn. That is a direct regression against expectations 5 and 7. **Add a TP-8 criterion that a mid-alarm respawner comes back DRAWN;**
- issue `use <desired>` / `activatenewweapon "dual"` only when `draw == 1`;
- **DO NOT move the holster above the 0.25s settle.** v2.1 instructed "holster BEFORE the 0.25s settle, not after"; round 3 reversed it. The in-code note at `itemhandler.scr:1510-1517` states the `wait 0.25` at `:1500` exists precisely so the engine's MP auto-`use` fires first "so it could be deactivated again". Hoist the holster and it runs on empty hands, where `deactivatePlayerWeapon` early-returns at `:1103-1107` and sets `flags["coop_lastActiveWeapon"] = NULL` - which permanently disables `activatePlayerWeapon` for that body (`:1121`) - while the engine's auto-use raises the gun anyway, leaving the armed window open AND breaking the later draw. **The armed window is closed by Step 6b, in the engine, which is the only place it can be closed.**
- Add a TP-2 / TP-6 criterion that a two-primary armory kit survives the flip and one post-LOUD respawn.

**Keep the holster hint, re-worded per phase.** v2 suppressed "Keep your weapon holstered when in disguise." (`:1506`, one-shot via `coop_holsterHint` at `:1505`/`:1507`) whenever the phase is loud, on the grounds that it "lies to the player at the moment their cover just broke". **Under D1 the hint is the single most important instruction in the level** - holstering IS the recovery action, and `player.cpp:5491-5497` re-grants `m_bIsDisguised` the frame after a holstered player's alarm clears. Word it by state and reset `coop_holsterHint` on each edge so the new text shows once:

| State | Text |
|---|---|
| QUIET | "Keep your weapon holstered when in disguise." |
| LOUD, disguise intact | "Holster to blend back in." |
| Alarm up (`coop_disgSuspended == 1`) | "The alarm is up - your uniform is worthless until it is silenced." |

**Fix `coop_papersAnytime`'s lifecycle and its LOUD behaviour.** Two separate defects found in round 2:

1. *It never restarts after a death post-LOUD.* The loop (`:1207-1226`) ends when `coop_isActive != 1`, which `player.scr:1444` sets on every death, and clears its own re-entry guard at `:1225`. Its only starter is `givePapersFlag` (`:2519-2525`). During QUIET the stealth block calls that unconditionally at `:735`; post-LOUD the block no longer runs, and the remaining call at `:768` is gated on `!group.player.flags["coop_hasPapers"]` - a flag written true at `:2522` / `main.scr:927` / `e1l3/FinalEscape.scr:780` and **cleared nowhere**, so it is permanently false. TP-2's own criterion "papers still work at sentry2dude afterwards" fails for any player who has died since the bust. Fix: start `coop_papersAnytime` from `main.scr::itemGetAll` (which runs on every spawn via `player.scr:1013`) keyed on `level.coop_itemPapers != NIL`, and drop the `coop_forcePapersEquip` gate for the restart (`coop_armOnBlown` cleared it at `:1401`).
2. *It hijacks the fire button during a firefight.* Its test is `primaryfireheld && ( coop_activeWeapon == NULL || NIL )` (`itemhandler.scr:1215-1216`, `wait 2` at `:1219`, press-swallowing loop at `:1220`), and both `deactivatePlayerWeapon` (`:1110`) and `weaponstate.scr:68`'s holster branch null that flag - so after a `draw == 0` LOUD, every holster makes FIRE present papers for two seconds.

   **Round 3 rejected both of v2.1's offered options and settled the term.** Option (i) - "present papers only while the disguise is usable **and** the player carries no weapons at all" - is false for every active player by definition after LOUD. Option (ii) - "re-bind so the first fire press after a `draw == 0` LOUD draws the holstered weapon instead" - also removes the presentation. **Either one breaks expectation 3 at sentry2dude, which the same sentence requires and which TP-2 asserts after the Naxos bust.**

   **Keep the shipped hands-empty test exactly as it is** - it already satisfies "a holstered post-LOUD player presses FIRE, papers come up", which is expectation 3 - and scope the new term to the **alarm alone**:

   ```
   if( local.player.primaryfireheld && ( local.aw == NULL || local.aw == NIL ) && level.coop_disgSuspended != 1 && !level.alarm ) { ... }
   ```

   **Do not add any term that reads whether the player OWNS weapons.** If the fire-button friction during a firefight turns out to be real in a playtest, solve it with a separate bindable action, not by weakening the papers trigger. This term lands in the same commit as the forced-holster removal from `restoreDisguises` (Step 21c), because that removal is what stops the squad being handed the papers prompt en masse on a douse.

**Rewrite the arming loop for entity safety.** `coop_armOnBlown` currently re-assigns the shared `group.player` inside a loop that `waitthread`s `giveWeaponLoadout`, which yields at least 0.25s, while `$player.size` is re-evaluated each iteration; a disconnect mid-loop shifts the array and skips a player. Build a **thread-local array of player entity references before the first yield** and iterate that, re-validating `!= NULL && isAlive && flags["coop_isActive"] == 1 && flags["coop_dbno_active"] != 1` immediately before each give.

v2 said "snapshot entnums". Round 2 established both that a resolver exists (`getentbyentnum`, used at `wounded.scr:260-262`) **and** that bug-1632 does not apply here: its recorded failures are all entity identity crossing a **thread or level boundary** (an entnum passed as a thread param, an entity parked on a level array), not a thread-local reference array. Either recipe works; **Step 13's discipline line and this step must prescribe the same one** - they did not in v2. Thread-local references are the choice.

#### Step 12 - close the arm/spawn race with an epoch

`coop_armAllOnBlown` only arms `coop_isActive == 1 && isAlive`, but `manageAliveSpawning` waitthreads `managePlayerInventory` at `player.scr:1012` and does not set `coop_isActive = 1` until `:1047`, with multi-frame `changeGameType` windows in between. A player anywhere in that window when `goLoud` fires has already taken the `coop_noWeapon` early exit and is then **skipped** - permanently empty-handed for the rest of the map.

Fix: `goLoud` increments `level.coop_stealthArmEpoch` (seeded to 0 in `init`; see section 4.3 - `NIL + 1` throws and the statement is skipped silently). `manageAliveSpawning`, after setting `coop_isActive = 1`, compares a per-body snapshot of the epoch taken before `managePlayerInventory` and re-gives if it advanced.

**The re-give MUST go through a same-file entry label. Do not "set `group.player` first".** `group` **is** the ScriptClass (`scriptvm.cpp:1465-1467`, `:1661-1663`). A bare same-file `thread label` shares the caller's ScriptClass; a qualified `file::label` call goes through `scriptclass.cpp:211-216` -> `scriptmaster.cpp:694-698`, which does `new ScriptClass(scr, self)` - **a brand-new, empty `group`**. So writing `group.player` in `player.scr` and then calling `coop_mod/itemhandler.scr::giveWeaponLoadout` writes player.scr's group and is invisible to the fresh one the call allocates; `group.player` arrives NIL, `:1430` errors, and the epoch re-give silently hands out nothing. That is exactly why the shipped recipe works today: `managePlayerInventory` sets `group.player = self` as its own first statement (`:697`) and every downstream call inside `itemhandler.scr` is a bare same-file label.

The call is therefore:

```
local.player waitthread coop_mod/itemhandler.scr::coop_armOnePlayer
```

with `coop_armOnePlayer:{ group.player = self; ... waitthread giveWeaponLoadout <useDefault> }` living in `itemhandler.scr`.

#### Step 13 - write `coop_mod/stealth.scr`

Labels: `init`, **`initScene`**, `goLoud <reason> <draw>`, `notifyLoud <reason> <draw>`, `protectScene`, `unprotectScene`, `quietWatchdog`, **`trioWatchdog`**, `alarmWatcher`, `onAlarmRaised`, `onAlarmDoused`, `restoreDisguises`.

Discipline:
- **`group` is per-ScriptClass, and the rule has two halves.** Only an **unprefixed same-file** `thread label` / `waitthread label` shares the caller's ScriptClass (`scriptclass.cpp:192-201`). **Both** a file-qualified `file::label` call **and** an entity-prefixed same-file call (`local.p waitthread someLabel`) allocate a fresh empty one, via `listener.cpp:4192-4206` -> `scriptmaster.cpp:694-698`. Round 3 added the second half; it is not academic, because the prefixed form is in live use in the very file Step 11 refactors (`itemhandler.scr:1256-1264`). So never call a group-**reading** label (i.e. `giveWeaponLoadout`) except through a same-file entry label that populates `group` first. `coop_armOnePlayer` does that from **`self`** - settled in Step 11; the "or from an argument" alternative is deleted. Carry **both halves** into the `docs/TRAPS.md` entry in Step 20.
- strings and numbers across thread boundaries; entity references thread-LOCAL only, never parked in level containers (bug-1632);
- players resolved by iterating `$player` 1-indexed with the `coop_isActive` filter (the `replace.scr::player_closestTo` recipe) - **the same recipe Step 11 uses**;
- `waitthread`, never `thread`, where a return value is wanted **and the label may yield**. (For a non-yielding label `thread` does return its `end` value - `listener.cpp:4233-4242`, `scriptvm.cpp:989-994` - but `waitthread` is unconditionally correct, so use it.)
- every array-slot read NULL-guarded, and NIL and NULL both tested where a flag may be unset;
- no em-dash, no bare negatives in parentheses, no BOM, ASCII only.

`init` (single frame, called at `maps/m2l2a.scr:38-42`): seeds `level.coop_stealthArmEpoch = 0`; sets the trio and `coop_stealthPhase = "quiet"`; `setcvar g_coopSpawnUnarmed 1` (Step 6b); threads the loose-weapon sweep (Step 15); starts `quietWatchdog`, `trioWatchdog` and `alarmWatcher`; prints the boot assertion (Step 17). **It does NOT tag scene actors and does NOT call `protectScene`** - see the blocker note in Step 4: at `:38` no actor has an `alarmthread` and all ten scene level-vars are still NIL.

`initScene` (called with `waitthread` from `maps/m2l2a.scr` **after `:135`, before `:163`**): tags scene actors with `coop_sceneActor` (recipe in Step 4 - iterate containers, use verified names, derive from `$ai_alarm` and `alarmthread`); calls `protectScene`; prints `^~^~^ST TAGGED n=<count>`.

`quietWatchdog`: 0.25s poll; T5 (the re-derived seven-condition predicate of section 4.2, two consecutive samples), T6, T7. **Exits permanently on `"loud"`.**

`trioWatchdog`: **a separate label, and this is the round-3 correction.** v2.1 put the trio invariant inside `quietWatchdog` and then said in the same paragraph both "exits permanently on loud" and "the invariant assert keeps running after LOUD" - one label cannot do both, and Step 13's label list named no second label to carry it. `trioWatchdog` asserts the trio invariant (all three set during QUIET, all three clear after LOUD) and prints `^~^~^ST TRIOBREAK <which>`, and it **never exits**, because `replace.scr:2644` and `:1349` write `coop_noWeapon` outside this path and a half-cleared trio post-LOUD is what makes every later spawn take the `itemhandler.scr:745` exit empty-handed.

**Write the actor walk guarded; do not literally reuse `anyEnemiesInAttackState`.** That label (`aihandler.scr:1244`) reads `level.coop_actorArray["german"][local.i].thinkstate` with **no NULL guard**, and array slots hold removed actors until `removeActorFromArray` runs a frame after the death event (`aihandler.scr:115-120`). A Script Error there does not kill the thread (`scriptvm.cpp:1881-1883`) but it does emit 4 Hz of log noise into the very `Script Error` grep the test plan uses. Guard: skip NULL slots, skip `!isAlive`, resolve `local.e = local.a.enemy` and test `local.e != NULL && local.e != NIL && local.e.classname == "Player"` before touching it. Fix the guard in `anyEnemiesInAttackState` too, or leave that label alone entirely.

`protectScene` / `unprotectScene`: minimal - the card trio only. Every entity command existence-guarded, so the labels are safe when reached on e1l4 or m6l1c where `$suckyfatty` does not exist. (Note: `unprotectScene` is in practice unreachable on those maps, because `notifyLoud` only reaches `goLoud` when the phase is `"quiet"`. The guards are defensive, not load-bearing.)

`alarmWatcher` / `onAlarmRaised` / `onAlarmDoused` / `restoreDisguises`: section 4.4 and Steps 21-22.

#### Step 14 - wire the triggers

**Round 2 found the single most consequential omission in v2: no step anywhere called `stealth.scr::init`.** The wiring table had seven rows and none of them was the init call, while `maps/m2l2a.scr:38-42` still armed the trio inline. The failure would have been silent - the map still plays unarmed, so the feature looks alive, but `level.coop_stealthPhase` stays NIL, `goLoud`'s phase guard returns on every transition, `quietWatchdog` and `alarmWatcher` never start, `protectScene` never runs, no `coop_sceneActor` tag is ever set (so Step 4's A4 exemption matches nothing), the loose MP40 is never removed, and no `^~^~^ST BOOT` line exists - while section 8.1 makes that line a mandatory proof-of-load and five test stages grep for markers that cannot be emitted.

| Target | Change |
|---|---|
| **`maps/m2l2a.scr:38-42`** | **replace the inline trio block with `waitthread coop_mod/stealth.scr::init`**, inside the `level.gametype != 0` branch, after `waitthread coop_mod/main.scr::main`, with **no `wait` before it** (single-frame init rule). Keep the `getcvar "coop_stealthStart" == "1"` condition around the call. |
| **`maps/m2l2a.scr`, after `:135` and before `:163`** | **NEW ROW, round 3.** `waitthread coop_mod/stealth.scr::initScene`, under the same `coop_stealthStart` condition. This is the second half of the split forced by the Step 4 blocker: `alarm_system_setup` is threaded at `:123` and the ten `find_guy` scene level-vars are assigned at `:124-135`, so **nothing the tag set depends on exists at `:38`**. Landing the tagging in `init` would tag roughly half the intended set, silently, with every proof-of-load criterion still passing. |
| **`maps/m2l2a.scr:832-834`** | the second `coop_stealthStart` block that threads `coop_stealthStripWeapons` at the uniform pickup: **fold into `init`'s sweep (Step 15) and delete here**, or keep it explicitly as a belt-and-braces second pass. Decide in the commit; do not leave it unaddressed. |
| `anim/disguise_enemy.scr` | goLoud preamble **inside `if (level.gametype != 0){` at `:22` and OUTSIDE the per-target `if` at `:23`**. Step 2 adds `self.enemy.is_disguised != 1` to `:23`; if the preamble lands inside that `if`, T1 can never fire during QUIET, because during QUIET the enemy is always disguised. Gated on `level.coop_stealthPhase == "quiet"`. |
| `itemhandler.scr:1162` (`takeAllDisguises` tail) | replace `thread coop_armOnBlown` with `thread coop_mod/stealth.scr::notifyLoud local.reason local.draw`, where **`local.draw` is derived inside `takeAllDisguises`** (Step 21a): `local.draw = 0; if( local.reason == "alarm" ){ local.draw = 1 }`. v2.1 left `draw` unbound at this hop - the signature had two parameters, the tail wrote `<draw>` as a placeholder, and section 7 row 5 showed `takeAllDisguises "alarm" 0` feeding `notifyLoud "alarm" 1` with no stated mapping, so an implementer could plausibly wire `draw = permanent` and invert it. Written literally, `local.draw` is NIL, `if (local.draw == 1)` is false, and both TP-8's "armed and drawn" and the grep `^~^~^ST LOUD reason=alarm draw=1` fail silently. **Pass the reason from the caller** (Step 21) rather than hard-coding `"alarm"`: `takeAllDisguises` has four callers and three are not alarms (`global/items.scr:477` is a uniform confiscation; the two e1l4 sites are scripted). Hard-coding would stamp `reason = "alarm"` and force-draw on a uniform loss, and under D1 the douse handler would try to restore a disguise the map deliberately took away. |
| `m2l2a.scr` `coop_naxosCaught` (~:493) | -> `goLoud "naxos" 0`; delete its dead `setcvar coop_stealthNoAggro 0` |
| `m2l2a.scr` `coop_blownOnDamage` (~:592) | -> `goLoud "damaged" 0`; delete its dead `setcvar coop_stealthNoAggro 0` |
| `m2l2a.scr::waitForEnemy` (`:882-916`) | **Name the predicate.** These two actors are `type_disguise "none"` (**`:808-809`**; `:807` is the `likeynorway:` label - round 3 restored v2's anchor, round 2's `:807-808` was wrong - before the threads at `:839-840`), so `InitDisguiseNone` installs only an `IsState` hook - they never enter a disguise think and **never acquire a challenge target**. `self.enemy` is NULL for them, so `self.enemy.is_disguised` is not available and the loop at `:898-907` has no target variable. Resolve one explicitly: `local.tp = waitthread coop_mod/replace.scr::player_closestTo self`, test `local.tp != NULL && local.tp.is_disguised != 1` plus a `cansee`, and pass `local.tp` into both the gated funnel and `goLoud "seen_armed" 0`. **The `type_disguise "none"` write at `:915` is a no-op here and only here** because both guards are already `"none"`; comment it and do not copy the pattern. Note the spawn-frame window (Step 16) would otherwise trip this loop for both guards. |
| `m2l2a.scr::cardplayersdeath` | **Do not describe this as "a preamble before the `attackplayer` line".** `:260` is the label; `:269` is `if(level.cardplayers != 3)` **with no braces** and `:270` `$suckyfatty attackplayer` as its single statement. An inserted statement would rebind the conditional and make the attack unconditional. The edit is: add braces to the `if` at `:269`, and place `waitthread coop_mod/stealth.scr::unprotectScene` **above** it (or at the top of the label after `self waittill death`). Note the in-code comment at `:263-266` is wrong on two counts - `level.cardplayers` is never assigned anywhere in the map (so the condition is already always true), and `:163` threads this label on a three-entity targetname, so three copies run. |
| ~~`officer.scr:118`~~ | **DELETED (round 2).** v2 proposed adding `if (level.coop_stealthReason == "alarm") { end 1 }` to `coop_officer_wait_goloud`. The label's first test is already `if( level.alarm != NIL && level.alarm == 1 ){ end 1 }` (`:121`), and `global/alarm_system.scr:700` sets `level.alarm = 1` **before** threading `takeAllDisguises` at `:704` - the sole route to `reason == "alarm"`. The clause could never be the condition that trips. **D2 is already satisfied by shipped code.** Instead: (a) **add the positive markers TP-2's negative assertion needs.** Round 3: `officer.scr` emits no wave or release marker at all - its only `^~^~^` prints are `:896` OFFICERHEAL, `:1736` PRONEDBG and `:3202` DEATHREACT, and the release diagnostics at `:183` / `:186` / `:189` are `iprintlnbold` gated on `level.cMTE_coop_officer`, a level variable no cvar or rcon command can set. So "no officer-wave markers" was asserting the absence of something that never existed. Add, under `coop_aggroDebug`: **`^~^~^ OFFICER release policy=<p> alarm=<n>`** where `:189` currently `iprintlnbold`s the release, and **`^~^~^ OFFICER wave n=<n>`** at the wave spawn. TP-2 greps for both as must-be-absent; TP-8 greps for both as must-be-present. And (b) fix the real defect in that label - its hard **600 second** bound (`:118-129`) with a caller that treats a 0 return as terminal (`:182-189`), so a stealth run that rings the alarm past minute ten gets no officer waves at all. Make the wait unbounded on `deferred` maps, or re-check `level.alarm` after the timeout; if the bound stays, print `^~^~^ OFFICER goloud-timeout` so a playtest can attribute a missing officer correctly. |

#### Step 15 - contain world pickups (decided, not deferred)

**Decision: remove the loose weapon entities outright.** The loose `playerweapon_german_mp40` (`map_entities/m2l2a_entities.txt:30`) sits in the same locker room as the suit, respawns under `g_gametype 2` (`item.cpp:361`), and every killed German drops another.

**v2 gave no removal recipe, and its stated fallback names a capability that does not exist.** The pickup carries **no targetname** (only angles, origin, testanim, `model "weapons//mp40.tik"`, scale, `classname "playerweapon_german_mp40"`), so `$name remove` is unavailable; and MOHAA script has **no find-by-classname primitive**, so "re-find by classname at `goLoud`" is unimplementable. `getentarray` is also unusable here - the in-code note at `wounded.scr:252` reads "getentbyentnum (NOT getentarray - that misses item entities)", `maptest_phase2.scr:93-95` records that getentarray's classname getter returns nothing at runtime, and `maptest_waypoints.scr:36` records it does not match brush triggers.

The recipe, matching the proven pattern at `coop_mod/main.scr::coop_launcherRespawnSweep` (threaded at `main.scr:136`) and `wounded.scr:252-262`:

- `init` **threads** a sweep label (a threaded label may legally `wait`; the single-frame rule binds only in or before `main.scr::main`);
- the sweep opens `wait 3`, matching `coop_launcherRespawnSweep`'s in-code rationale "One sweep at +3s: world-PLACED pickups exist by then";
- it then walks `getentbyentnum` over `0 .. int( getcvar "maxentities" )`, matching on the model with `.owner == NULL`, and `remove`s;
- it prints **`^~^~^ST SWEEP removed=<n>`** so TP-2 can prove the removal rather than infer it from a tester not finding an MP40.

**Observe the runtime model string before writing the match (round 3).** v2.1 asserted the getter returns `models/weapons/mp40.tik`; nobody has ever looked. The map file says `"model" "weapons//mp40.tik"` (`map_entities/m2l2a_entities.txt:28` - double slash, no `models/` prefix), and the shipped precedent this recipe copies, `coop_mod/main.scr::coop_launcherRespawnSweep` (`:2069-2085`), matches **four** literals including both `models/weapons/Uk_W_Piat.tik` and `models/weapons/uk_w_piat.tik` for one model, because its author could not predict the runtime case either. That precedent also guards `local.ent.model == NIL` at `:2072` as well as `.owner` at `:2073`; v2.1's prose named only the owner guard. So: **print `local.ent.model` for every non-NULL entity once, record the exact string, then write the match** - or match defensively (`.owner == NULL` **and** `.model != NIL` **and** several spellings). If the match misses, the MP40 survives, `^~^~^ST BOOT` still prints, and expectation 1 fails only when a tester happens to walk into the locker room.

State explicitly what covers the pre-sweep window: nothing does, and nothing needs to - no player can reach the locker room inside three seconds of map load. **AI corpse drops during QUIET are deliberately NOT swept** (a repeating sweep races the pickup and treats the symptom); they are left to T7, which reports "a real Weapon in a player's hands during QUIET" as a fault and goes loud. Say so rather than leaving it implied.

Rejected: a 1 Hz strip poll; hide-and-restore (parks entity references across the QUIET window - the bug-1632 pattern, and contradicts Step 13's discipline); relaxing expectation 1 to "carried but holstered".

#### Step 16 - close the spawn-frame rifle window

Every body holds the engine's `EquipWeapons` DM rifle for one or two frames before `managePlayerInventory`'s `takeall`, during which `is_disguised` reads false - and `manageAliveRespawning` warps the body to `coop_respawnOrigin`, back among the guards, before inventory runs.

**v2's first bullet is deleted: it is a no-op.** "Add an explicit `deactivatePlayerWeapon` at the top of the stealth block" puts the call at `:719`, which is **below** `group.player takeall` at `:708`; and `deactivatePlayerWeapon` early-returns on empty hands anyway (`:1103-1107`). The window it describes runs from engine spawn through `manageAliveRespawning` (`player.scr:984`) to `waitthread managePlayerInventory` (`:1012`) - all strictly before `:708`. If a script-side holster is wanted at all it must go into `manageAliveSpawning` **before** the respawn warp at `player.scr:984`.

**The real closure is the engine half, Step 6b.** No script gate can undo an engine thinkstate transition that has already happened.

**v2's second bullet must not key on spawn protection.** `player.scr:1310-1320` defaults `coop_spawnProtect` to **8 seconds** and re-stamps `coop_spawnProtUntil` on every respawn. The readers v2 names (`disguiseHandler`, `canseeUndisguisedPlayers`, the six anim gates, T5/T6/T7, `waitForEnemy`) are shared code that also runs on e1l3, e1l4, m2l2b, m1l3c, m4l0, m6l1c and m6l3c, and on m2l2a after LOUD. Keying them on an 8-second window blinds every guard in the game for 8 seconds after any respawn - against expectation 7 and TP-R - and on m2l2a makes TP-5's "unarmed every time" check structurally unable to fail.

Use a **dedicated short window** instead: `managePlayerInventory` already stamps `group.player.flags["coop_spawnEventTime"] = level.time` at `:700`. Either test `level.time < flags["coop_spawnEventTime"] + 0.3`, or stamp and clear a purpose-made `coop_invSettleUntil` around the stealth block. Apply it **only while `level.coop_stealthPhase == "quiet"`**, and apply it to T5/T6/T7 as well, or the watchdog self-triggers on its own spawn window.

#### Step 17 - config

**Every seed site, not two (round 3).** v2.1 named two files and described them as "repo root"; there are **five** sites across two trees, the path is the **mod root**, and per bug-1633 a homepath cfg **shadows** the basepath copy - so the autotest harness is already running with `coop_stealthStart 1` while the shipped mod says 0.

| File | Line | Today |
|---|---|---|
| `hzm-mohaa-coop-mod/autoexec.cfg` | `:1175` | `seta coop_stealthStart 0` |
| `hzm-mohaa-coop-mod/coop_defaults.cfg` | `:207` | `seta coop_stealthStart 0` |
| `autotest_home/maintt/coop_defaults.cfg` | `:206` | **already 1** |
| `autotest_home/maintt/configs/omconfig.cfg` | `:2308` | **already "1"** |
| `autotest_home/maintt/stealthtest.cfg` | `:9` | **already 1** |

- `coop_stealthStart 0 -> 1` in the two mod-root files, and reconcile the three autotest-homepath copies to the same value. Editing only one reproduces the bug-1633 / 1635 false-verdict class.
- Delete `coop_stealthNoAggro` from both mod-root cfgs (`autoexec.cfg:1176`, `coop_defaults.cfg:210`) - dead wiring.
- `coop_disgAggroParity 1` **and `coop_stealthRecoverAlarm 1`** are seeded by **Step 0 / commit A0**, in the same five places. This step only back-references them; one step owns each seed. `coop_stealthRecoverAlarm` is D1's own kill switch and is read by `takeAllDisguises`'s `permanent` derivation (Step 21a) - round 3 found it named in section 11's rollback table and created by no step.
- **Seed `g_coopDisgDebug 0` and `coop_aggroDebug 0` in `hzm-mohaa-coop-mod/autoexec.cfg` as well** (see section 8.1 item 3: neither is seeded anywhere today and neither can be pushed over rcon before a map is running). Add an in-file comment that both must be 0 for a real play session.
- `g_coopSpawnUnarmed` is **not** seeded in any cfg - it is `setcvar`'d by `stealth.scr::init` and reset to 0 by `main.scr::main` at every map load (Step 6b). Seeding it archived would leak the suppression across the session.
- Boot assertion in `stealth.scr::init` printing the resolved cvars and the chosen phase.
- **8.4 gains a gate step:** grep every `coop_defaults.cfg` / `autoexec.cfg` copy under both deploy roots and the autotest homepath and assert one consistent value for `coop_stealthStart`, `coop_disgAggroParity` and `g_coopDisgParity` before any verdict.

#### Step 21 - recoverable alarm, script side (D1)

The engine already implements recoverable alarm (`player.cpp:5490-5497` recomputes `m_bIsDisguised` every frame gated on `m_bHasDisguise && !level.m_bAlarm`; `level.cpp:2062-2070` maps `level.alarm` onto `m_bAlarm`; `global/alarm_system.scr:717-729` genuinely toggles it back off). **What makes it one-way is HZM script.** Four latches must be addressed, and `takeAllDisguises` is only the first.

**21a - make the disguise strip optional.** Give `takeAllDisguises` two parameters:

```
takeAllDisguises local.reason local.permanent
```

**Omitted script arguments arrive NIL - there is no default-argument mechanism in this dialect.** So the label must open with explicit NIL defaults, and those defaults must reproduce today's behaviour for any caller that is left alone:

```
takeAllDisguises local.reason local.permanent:{
    if( local.reason == NIL ){ local.reason = "alarm" }
    if( local.permanent == NIL ){
        local.permanent = 1
        if( level.coop_stealthPhase != NIL && level.alarm == 1 && getcvar( "coop_stealthRecoverAlarm" ) != "0" ){ local.permanent = 0 }
    }
    local.draw = 0
    if( local.reason == "alarm" ){ local.draw = 1 }
    ...
```

**Round 3 resolved a three-way contradiction here.** v2.1's heading said "without changing any existing caller"; its table then required `global/alarm_system.scr:704` to pass `"alarm"` and a conditional `permanent`; and 21b declared `global/alarm_system.scr` unedited. All three cannot hold. Source: `:704` is a bare `thread coop_mod/itemhandler.scr::takeAllDisguises` with no arguments, and `itemhandler.scr:1138` is `takeAllDisguises:{` with no parameters. Honour the no-edit claim with a naive `permanent` default of 1 and `:1144-1145` / `:1150-1152` still destroy `coop_enableDisguises` / `coop_uniformOnSpawn` / `has_disguise`, `coop_stealthBlocksAggro`'s per-target rule fails open for the rest of the map (`aihandler.scr:1194` requires `level.coop_enableDisguises`), **and D1 dies silently while `^~^~^ST QUIETDISG` still prints**.

**The settled shape: the conditional is evaluated INSIDE the label, from `level.alarm` and `level.coop_stealthPhase`, exactly as above, and `global/alarm_system.scr:704` is NOT edited.** The three non-alarm callers pass their reason explicitly and are edited:

| Caller | reason | permanent | Edited? |
|---|---|---|---|
| `global/alarm_system.scr:704` | derived `"alarm"` | derived (0 on a stealth-director map with the alarm up, 1 otherwise) | **no** |
| `global/items.scr:477` | `"uniform_lost"` | 1 | yes |
| `maps/e1l4/PreShip.scr:88` | `"scripted"` | 1 | yes |
| `maps/e1l4/Ship.scr:416` | `"scripted"` | 1 | yes |

**Add a loud runtime assertion**: if the label is reached with `local.reason == NIL` on a map where `level.coop_stealthPhase != NIL`, print `^~^~^ST FAULT takealldisguises reason=nil`. A silent half-failure on the axis the whole D1 decision rests on is not acceptable.

In **non-permanent** mode the label clears only `coop_isDisguised`; it leaves `has_disguise`, `coop_hasDisguise`, `level.coop_enableDisguises` and `level.coop_uniformOnSpawn` intact, and lets the engine's own `!level.m_bAlarm` term do the voiding. **It does NOT write `level.coop_disgSuspended`** - `alarmWatcher` is that variable's single writer (section 4.4). In permanent mode it behaves exactly as today (`:1144-1145`, `:1150-1152`). e1l4's point of no return is therefore untouched.

The tail call becomes `thread coop_mod/stealth.scr::notifyLoud local.reason local.draw`, with `local.draw` derived as shown, per Step 14.

**Retaining `has_disguise` through an alarm is retail-accurate, not a coop invention.** The retail `global/alarm_system.scr` extracted from `G:\GOG\...\main\Pak0.pk3` contains **zero** references to `has_disguise` or any disguise strip - it only sets `level.alarm = 1`. The `takeAllDisguises` thread at HZM `:704` is a coop addition. So non-permanent mode restores retail state, and whatever `m_bEnemyIsDisguised` does in that state is by definition the vanilla cover-blown behaviour expectation 7 demands. **Do not add an engine term forcing `m_bEnemyIsDisguised` false under `level.m_bAlarm`** - that would make coop diverge from retail, which is the opposite of the goal.

**21b - the douse edge.** `stealth.scr::alarmWatcher` (section 4.4) mirrors `level.alarm` at 0.25s and fires `onAlarmDoused` on the 1 -> 0 edge. **The OFF branch of `global/alarm_system.scr` (`:717-730`, `level.alarm = 0` at `:728`) is not edited.** Round 3 narrowed this claim from "the file is not edited" to "the OFF branch is not edited", because Step 22a **does** require two edits elsewhere in that file (a floor in `ai_alarm_alerted_bumpstack` and the cooldown's reader in `alarm_switch_thread`). `global/alarm_system.scr` is therefore **added to section 8.4's touched-file list.**

**Known, documented race:** a 0.25 s watcher cannot beat `ai_gofor_alarm_waitforalarm`, whose `while (level.alarm == 1){ wait .1 }` at `:658-660` wakes within 100 ms of `:728`. In that window the runner can pass `:488` (alarm not 1), `:494` (index still non-zero) and `:507`, which captures `level.ai_alerted_stack[...]` into a **thread-local** that no later level-variable clear can reach, then unholster at `:519`, run the loop at `:543` and `douse` at `:651`. So **an in-flight ringer will re-ring once**, and the cooldown of 22a is what absorbs it. A synchronous hook at `:728` would win the race; that option is available and is the fallback if TP-10 shows the cooldown is not enough.

**21c - `restoreDisguises`, and what it must NOT do.** Per active player: set `has_disguise = game.true`, `flags["coop_hasDisguise"] = game.true`, and **`waitthread setIsDisguised <player> game.true game.true`** (`itemhandler.scr:2439-2445`; the third argument forces the write past the `coop_hasDisguise` test at `:2442`). The `setIsDisguised` call is round 3's addition: 21a's non-permanent mode clears `coop_isDisguised` and nothing else restores it - `weaponstate.scr:64` / `:71` fire only on a weapon **state change**, which an already-holstered player never generates, and `itemhandler.scr::coop_stealthHoldDisguise`'s loop condition at `:1308` requires `level.coop_startUnarmed == 1`, so that watchdog is permanently dead after LOUD. This is flag-divergence hygiene of the exact class bug-1638 was closed to end. (Note the only remaining **live functional** reader of the mod flag is `global/spotlight.scr:685`, which is not a disguise-map path; `aihandler.scr:1021` is converted to `is_disguised` by Step 3 unconditionally, and `:1051` is a debug print.)

**NO `deactivatePlayerWeapon` (round 3).** v2.1 put a forced squad-wide holster here. Deleted - see the closing paragraph of section 4.4 for the full argument. `player.cpp:5491-5497` re-grants `m_bIsDisguised` the frame a player holsters voluntarily, which is exactly what the re-worded hint instructs.

**Restore the SNAPSHOT, not `game.true` (round 3).** v2.1 set `level.coop_enableDisguises` and `level.coop_uniformOnSpawn` to `game.true` directly and called `giveUniformToPlayer` unconditionally. `maps/m2l2a.scr:28` sets `coop_uniformOnSpawn = game.false` at load, and the only legitimate setter is `giveUniformToAll` (`itemhandler.scr:897`, flag at `:900`) via the `add_item "uniform"` pickup at `global/items.scr:289`. So an alarm rung and doused **before the locker room** would dress the whole squad and skip the map's central pickup permanently - and m2l2a has four player-usable `alarm_switch_trigger` entities. Instead: `onAlarmRaised` snapshots both flags, `restoreDisguises` re-asserts the snapshot, and `giveUniformToPlayer` runs only where the snapshot was 1. (Under 21a neither flag is ever cleared, so in the normal case both writes are a defensive no-op - section 4.1's "left intact" and this re-assert are now consistent, which they were not in v2.1.)

**Do not route recovery through `giveDisguiseToAll`**: it is inert on m2l2a (`:996` early-exits on `coop_enableDisguises`, which the map pre-sets at load), and where it is not inert it calls `resetEnemyThinkstates` + `setEnemyAttackStates`, whose raw `attackplayer` at `aihandler.scr:1285` sets the one-way `m_bForceAttackPlayer` on every german that was in attack or pain. No `changeGameType` window is needed - `Player::SetHasDisguise` (`player.cpp:11384-11387`) is not gametype-gated.

**21c-bis - suppress the per-spawn disguise re-grant while the axis is suspended (round 3).** `itemhandler.scr:757-759` is `if (level.coop_enableDisguises && !group.player.is_disguised){ waitthread giveDisguiseOnSpawn group.player }`, unconditional on phase or alarm. During an alarm `player.cpp:5493` guarantees `is_disguised == 0`, and 21a keeps `coop_enableDisguises` TRUE - so this fires on **every respawn for the whole alarm**, and `giveDisguiseOnSpawn` -> `giveDisguise` (`:937`) runs `resetEnemyThinkstates` at `:957-960` and `setEnemyAttackStates` at `:974`, whose bare `local.enemy attackplayer` at `:1285` re-latches `m_bForceAttackPlayer` on every german in attack or pain. Post-douse it does the same for any player who respawns holding a weapon - **undoing E5 seconds after E5 ran.** This cannot happen today only because `itemhandler.scr:1144` clears `coop_enableDisguises` on the alarm; 21a introduces it. Gate `:757-759` (and `:762`) on `level.coop_disgSuspended != 1 && !level.alarm` on a stealth-director map, and let `restoreDisguises` do the grant on the douse edge.

**21d - restart `disguiseHandler`, without duplicating it.** `aihandler.scr:1007`'s `while (level.coop_enableDisguises && !level.alarm)` exits the moment the alarm rings, and restart is structurally impossible: `:1003` refuses on `level.coop_disguiseHandlerThread`, `:1005` is the **only** assignment of that flag in the entire tree, and nothing clears it. The owning loop therefore falls through to `level.coop_disguiseHandlerThread = NIL` after the `while`.

**`onAlarmDoused` must NOT force-clear that flag (round 3).** v2.1 said both things at once - Step 21d said the owner clears it on exit, section 4.4 item 4 said the douse handler clears it and re-threads. The loop's tick is `wait 1` at `:1032`, and under non-permanent mode `coop_enableDisguises` is never cleared so `level.alarm` is the **only** exit, sampled once per second. For any alarm cycle shorter than one second the owner never exits and never clears; a force-clear then lets a **second** loop claim the flag, after which every german is swept twice per second and `attackPlayer` / `sentientIsSeen` / `sentientIsHeard` fan out at double rate, growing by one loop per short cycle. So: **the owner clears it on exit only**, and `onAlarmDoused` waits for NIL (bounded, then gives up and prints `^~^~^ST FAULT disguisehandler stuck`) before re-threading. Note the 1 s `wait` at `:1002` makes the restart non-instant either way. Without the restart, a recovered-quiet has no mod-side "seen undisguised" reaction at all, and Step 3's edit at `:1021` is edited into a loop that can never run again.

**21e - re-arming is NOT part of recovery.** Per P5 that is the design: **weapons are one-way, the disguise is not.** (v2.1 justified this by `coop_armOnBlown`'s `:1395-1396` being an atomic one-shot. That rationale is **stale** - section 4.3 splits that pair and replaces the guard with an independent `coop_armAllDone` latch. The design decision stands on P5 alone.) State it in the user-facing text; do not add a re-arm label.

**21f - `coop_paperPass` is deliberately not reset.** The per-guard latch at `itemhandler.scr:1178-1179` is permanent and cleared nowhere. Under D1 a guard who already accepted the squad's papers stays satisfied across an alarm cycle. Recorded as a decision (section 14), not an oversight.

#### Step 22 - douse hygiene (D1)

Four things must happen on the same edge or the recovery is undone within seconds.

**22a - clear the alerted queue, safely, and give the cooldown a reader.** `global/alarm_system.scr`'s alerted-AI processor ends with `ai_gofor_alarm_waitforalarm: while (level.alarm == 1){ wait .1 }` (`:656-660`) then `goto ai_gofor_alarm_processnext` - the stack resumes the instant a player douses, resolves the nearest player, and fires `$alarm_switch_trigger[...] douse local.player` at `:651`, re-entering `alarm_system_master` and setting `level.alarm = 1` again at `:700`. `alarm_switch_thread`'s `wait 3` at `:679` is the only rate limit. `onAlarmDoused` sets `level.ai_alerted_index = 0` and `level.ai_alerted_stack[1] = NULL`, and sets `level.coop_alarmReArmTime = level.time + N`.

Three round-3 corrections, all mandatory:

1. **`NULL`, not `NIL`.** `global/alarm_system.scr:98` initialises that slot with `NULL` and `ai_alarm_alerted_bumpstack:463` clears it with `NULL`; the readers at `:507` and `:512` run `isalive` on it. Assigning NIL removes the container element instead of nulling it. v2.1 specified NIL - a gratuitous deviation from the file's own idiom in the one place this plan reaches into that subsystem.
2. **Do NOT write `level.ai_alerted_isprocessing`.** It is a mutex owned by `alarm_system.scr`, claimed at `:425` and `:455` and released at `:436` and `:469`. Writing it from `stealth.scr` releases a lock another thread believes it holds.
3. **Zeroing `ai_alerted_index` from outside can wedge the whole alarm system permanently, and this MUST be fixed in the same step.** `ai_alarm_alerted_bumpstack:464` is `level.ai_alerted_index --` with **no floor**, reached from `:514`, `:524`, `:607` and `:629`. If the gofor runner is mid-flight when the index is zeroed - reachable, because it wakes from the 0.1 s poll at `:658-660` up to 0.15 s before the 0.25 s watcher fires - it walks `:485` (alarm not 1), `:494` (`index == 0` is false at -1), `:500` (`1 > -1` forever), `wait 3`, a NULL slot at `:512`, bumpstack to -2, and loops. `ai_gofor_alarm_reset` - the only place the `$waittrigger_gofor_alarm` wait is re-armed - becomes unreachable and **no AI can ring the alarm again for the rest of the map**. Add the floor inside the label: `if (level.ai_alerted_index < 0){ level.ai_alerted_index = 0 }`. This is an edit to `global/alarm_system.scr`; 21b has been reworded to permit it and 8.4's touched list now includes the file.

**The cooldown's reader, named (round 3).** v2.1 wrote `level.coop_alarmReArmTime` twice, both times as a write, and never named a consumer - a variable nothing reads. The reader goes in **`alarm_switch_thread`** (`:669-682`): at `:672`, after `self waittill trigger` and before the unconditional `trigger $waittrigger_alarm_master` at `:677`, jump back to the label's loop while `level.time < level.coop_alarmReArmTime`. Print **`^~^~^ST REARM blocked`** when it does, so a suppressed re-ring is observable - none of the three possible causes of a re-ring is otherwise distinguishable in the 8.2 grammar. Note m2l2a has four `alarm_switch_trigger` entities (`map_entities/m2l2a_entities.txt:2463, :2491, :2509, :3029`), each running its own copy of this thread, so the guard must be inside the thread, not outside it.

**This is a deliberate deviation from vanilla** (the re-ring cycle is retail behaviour) taken to make D1 meaningful. Record it in `docs/DECISIONS.md` as such rather than shipping it as a silent fix, and flag it against expectations 6 and 7 in section 7.

**22a-bis - fix the backup counter, or the second alarm has no reinforcements (round 3).** `level.ai_alarm_backup_total` is incremented on spawn at `global/alarm_system.scr:850` and decremented **only** in `ai_backup_death` at `:351`, after `self waittill death` at `:349`. The despawn path `alarm_system_backup_dude_gone` (`:932-933`) is a bare `self remove` with no decrement, and a `remove` does not fire the death waittill. Despawn is the **normal** outcome after a douse (`:916-918` removes when no player can see the actor and it is beyond `backup_remove_distance`). The spawn gate is `if (level.ai_alarm_backup_total < level.ai_alarm_backup_max)` at `:799`, and `maps/m2l2a.scr:103` sets max = 4. So after one alarm cycle whose backups walk out of sight, the counter is pinned at 4 and **every later alarm spawns zero reinforcements, silently**. D1 makes repeated alarms the design. Add `level.ai_alarm_backup_total --` on the removal path at `:932` (or reset the counter in `onAlarmDoused`), and add "reinforcements still spawn on the second and third alarm" to TP-10's pass criteria.

**22b - restore `THINK_ALARM` on MAP-SCRIPT scene actors only.** `actor_alarm.cpp`'s `State_Alarm_Idle` ends with `SetThink(THINKSTATE_ATTACK, THINK_TURRET)`, permanently overwriting the alarm think, and `State_Alarm_StartThread` is the only place `m_AlarmThread.Execute(this)` runs. So on a second alarm the welders never drop their torches, the cower man never cowers, `ohnothenaxos1` never fires and the scientists never react - none of the m2l2a scene threads at `:1198-1200`, `:1237-1238`, `:1333-1334`, `:1526-1529`. Re-issue `self type_attack "alarm"`; `Actor::EventSetTypeAttack` ends in `SetThink(THINKSTATE_ATTACK, think)` (`actor.cpp:8241-8255`), so this genuinely reinstalls `THINK_ALARM`.

**Round 3 imposed four constraints on that re-issue. As v2.1 wrote it, 22a and 22b cancel on the same edge.**

1. **Exclude every actor whose `alarmthread` is `global/alarm_system.scr::ai_alarm_alerted`** - i.e. the thirteen `$ai_alarm` actors, set up at `global/alarm_system.scr:336-337`. `Actor::SetThink` sets `m_bDirtyThinkState` when the actor is already in that state (`actor.cpp:7949-7952`), consumed by `ThinkStateTransitions()` at `:7774-7777`, which runs `Begin_Alarm` (`actor_alarm.cpp:36`) -> `State_Alarm_StartThread` (`:63`) -> `m_AlarmThread.Execute(this)` (`:71`) -> `ai_alarm_alerted`, **the queue pusher** (`:425-433`). Step 22a's clear is undone in the same handler. The only brake is the HZM guard at `:396-406`, which blocks only a contact reading `is_disguised == 1` - and TP-10's own script is "ring, fight, then douse", i.e. weapons out.
2. **Run 22b LAST in `onAlarmDoused`, after the queue clear and after `restoreDisguises`** (section 4.4 ordering), and skip any actor whose `thinkstate` getter (`actor.cpp:11929-11932`) currently reads `"attack"` - otherwise the re-issue yanks surviving alarm actors out of combat and walks them to their alarm node mid-firefight.
3. **The two m2l2a scene alarmthreads are NOT idempotent, and must be made so inside this step.** `cower` (`maps/m2l2a.scr:1214-1223`, bound at `:1200`) has **no** re-entry guard, runs `self exec global/disable_ai.scr` at `:1216` then `self waittill animdone` at `:1217` on an anim chain that is long finished on a re-run, and ends in a raw `self attackplayer` at **`:1222`** - which re-latches `m_bForceAttackPlayer` the instant E5 cleared it. `weldinginterupt` (`:1254-1266`, bound at `:1238`) guards on `self.inturpupted == 1` at `:1255` but **sets `self.interupted = 1`** at `:1259` - two different spellings, so the guard is dead - then `disable_ai` at `:1258` and a `waittill animdone` on `welding_stop`. So: add `if(self.stophammering == 1){ end }` to `cower`, remove or gate its `:1222` `attackplayer`, and fix the `inturpupted`/`interupted` spelling. (`ohnothenaxos1` is already guarded by `level.naxossequencetriggered` at `:615`.) **Add an explicit re-run leg to TP-10.**
4. Reconcile with Step 4, whose hurt-trooper branch writes `type_attack "cover"` over the same field (`aihandler.scr:433`) - the scene-actor exemption must already be excluding these actors, which it does.

If 22b is judged too risky for the first landing, the fallback is to **document** that alarm scene reactions are one-shot and that expectation 7 is guaranteed only for the FIRST alarm. That is a stated residual risk (section 15), not a silent one. Given constraints 1 and 3, deferral is now the **recommended** default for the first Phase C commit.

**22c - surface the contract to the player.** Per P5, per-actor recovery is gated on breaking line of sight, not on a timer. Print `^~^~^ST QUIETDISG reason=doused` and show "Alarm silenced. Holster and break line of sight to blend back in." Add TP-10 (below), which douses from cover and measures time-to-first-re-challenge. **Do not** try to force it with `enableEnemy 0` or an `attackplayer` restore - that is exactly the latch this whole plan is removing.

---

## 6. Lifecycle hook table

The structural finding that makes expectation 1 cheap: **every body a player ever inhabits passes through one inventory choke point** - `playerSpawnEvent -> manageAliveSpawning -> managePlayerInventory` (`itemhandler.scr:695`). The trio is level-scoped, so it survives entity destruction.

| Transition | Weapons | Disguise latch | Papers | Uniform | New code? |
|---|---|---|---|---|---|
| First spawn | blocked `:745` | `giveDisguiseOnSpawn` `:728` | block `:730-741` | **Step 10** | no |
| Death -> respawn | blocked `:745` | same | same | **Step 10** | no |
| DBNO enter | blocked `dbno.scr:231` | held (no takeall of the latch) | `takeall` strips them -> **Step 18** | held | **fix** |
| DBNO revive (team / AI / medkit) | blocked `dbno.scr:728`, `medkit.scr:376` | held | `coop_key_guardian` +1s -> **Step 18** | held | **fix** |
| DBNO corpse-revive respawn | blocked `:745` | as respawn | as respawn | **Step 10** | no |
| Spectate -> return | blocked `:745` | same | same | **Step 10** | no |
| Disconnect -> reconnect | blocked `:745` (level-scoped) | same | same | **Step 10** | no |
| Late join mid-mission | blocked `:745` | same | same + **Step 19** | **Step 10** | no |
| After uniform pickup | never granted (the pickup is an InventoryItem) | **`giveUniformToAll` + per-spawn `giveDisguiseOnSpawn`** (`giveDisguiseToAll` is inert on m2l2a - `:996`) | `givePapersFlagToAll` | `giveUniformToAll` | no |
| **papers1 -> papers2 swap** | unchanged | unchanged | **Step 19** | unchanged | **fix** |
| Any of the above, post-LOUD | armed via the normal path **plus the phase-split tail** | engine-computed | **Step 11** restarts `coop_papersAnytime` | normal | **fix** |
| Any of the above, within 1s of LOUD | **Step 12** epoch, via `coop_armOnePlayer` | engine-computed | normal | normal | **fix** |
| **LOUD fires while a player is DOWNED** | **skipped** - `coop_dbno_active` filter (Step 11) | held | held | held | **fix** |
| **Revive after LOUD** | **arm on revive** (Step 11 hook in `dbno.scr` / `medkit.scr`) | held | restored (Step 18) | held | **fix** |
| **Alarm rings** | unchanged (already armed, or armed now, drawn) | `coop_disgSuspended = 1`; `has_disguise` **retained** (Step 21a) | unchanged | unchanged | **fix** |
| **Alarm doused** | unchanged - weapons are one-way, **and no forced holster** (Step 21c) | `restoreDisguises` (incl. `setIsDisguised`) + `disguiseHandler` restart + E5 (Steps 21, 23) | unchanged | re-given **only if the raise-edge snapshot said the squad already had it** (Step 21c) | **fix** |
| Spawn during `coop_disgSuspended == 1` | armed (post-LOUD) | `has_disguise` granted; engine denies `is_disguised` while the alarm holds | normal | given (uniform is cosmetic while suspended) | no |

---

## 7. Per-expectation traceability

| # | User expectation | Mechanism | Steps |
|---|---|---|---|
| **1** | Unarmed across death, DBNO, spectate, reconnect, join, and after pickups | Level-scoped trio at map load via `stealth.scr::init`; all eight grant sites already consult `coop_noWeapon`; pickups are InventoryItems; the loose MP40 removed by an entnum sweep; the engine spawn loadout suppressed at source; T7 reports any leak | 6b, 10, 14, 15, 16, 17, 18, 19 |
| **2** | One player takes the uniform, everyone gets it | `giveUniformToAll` + **per-spawn `giveDisguiseOnSpawn`** (`itemhandler.scr:728` / `:758-759`) + `givePapersFlagToAll`, level-scoped for late joiners, **plus the uniform re-give duplicated above the early exit**. **Corrected in round 2:** `giveDisguiseToAll` is a no-op on m2l2a - its first line (`:996`) early-exits on `level.coop_enableDisguises`, which `maps/m2l2a.scr:27` pre-sets at load - so do not instrument it expecting to see the squad-wide grant there | 10 |
| **3** | Any player can FIRE to show papers, to any guard, without breaking checks | Engine `activatepapers` handshake (per-owner `m_ShowPapersTime`); `coop_papersAnytime` **restarted per spawn** and phase-aware so it does not eat the fire button in a firefight; `forcePapersInHand`; **E1** so clients can be challenged at all; **E3a** so a checker never resolves on a stranger's stamp; **E3b** so a checker never measures the wrong player's distance and HALTs; the freeze arm deleted; **accept and salute no longer attack the man who just passed**; papers survive DBNO and the papers2 swap | 1, 2, 7, 8, 11, 18, 19, TP-3 |
| **4** | Wrong-papers detection -> LOUD, and every later lifecycle event spawns loud | T1 plus the **corrected** T5 backstop -> `goLoud` -> trio cleared **in `goLoud` itself** -> all later bodies arm through the pipeline, epoch-covered at the boundary via `coop_armOnePlayer`, downed bodies armed on revive. `giveWeaponLoadout`'s tail splits on phase so the post-LOUD kit is complete (backfill + assert), not the short disguise kit | 11, 12, 13, 14 |
| **5** | Any alarm -> the same | T2: `alarm_system_master` -> `takeAllDisguises` (which derives `reason = "alarm"`, `permanent = 0`, **`draw = 1`** internally - Step 21a) -> `notifyLoud "alarm" 1` -> `goLoud "alarm" 1`. Round 3 corrected this row: v2.1 wrote the chain as `"alarm" 0` feeding `"alarm" 1` with no stated derivation of the second argument, and `notifyLoud` **always** performs the draw via `coop_drawAllWeapons` even when the phase is already loud (v2 delegated that to `coop_armOnBlown`, whose one-shot latch had already fired, so an alarm after a non-alarm LOUD drew nobody). The engine voids `is_disguised` while `m_bAlarm`. **D1:** the alarm SUSPENDS the disguise rather than confiscating it, and `onAlarmDoused` restores it | 11, 13, 14, 21, 22, 23 |
| **6** | All AI play their scripts and anims exactly as vanilla | Subtractive: per-target aggro gates through one helper, **with the NIL branch left blocking** so the replica / search-sweep / berserk stand-downs survive; permanent scene-actor exemption from **both** the personality system and the hurt-trooper branch, with `coop_prone_shooter` forbidden outright on checkers and alarm actors; **E2** so a 4P body-block cannot turret-ify or permanently latch a scene actor; **E4** so door noise is muted for every disguised player; the freeze arm deleted. **Stated deviation:** Step 22a suppresses vanilla's alarm re-ring cycle for a cooldown window, deliberately, to make D1 meaningful | 1, 2, 3, 4, 6, 9, 13, 22 |
| **7** | Loud is precisely vanilla cover-blown | **Resolved reading, following from D1:** "cover-blown" means whatever the ENGINE reads as blown - a drawn weapon, or a live alarm. AI hostility is engine-native and per-target: `attackentity` replaces the latching `attackplayer` in the funnel (the map's own twelve raw sites stay vanilla-latching, which is why E5 clears the latch on a douse); scene alarmthreads are no longer overwritten by `type_attack "cover"` and are re-installed on a douse; holstered arming keeps local busts local, as retail intends. A player who goes LOUD without an alarm and then re-holsters **is** deferred to again by `aihandler.scr:1191-1197` - that is not a gap, it is D1's semantics, and the re-worded holster hint tells the player so. Officer waves are alarm-only via the **already shipped** `level.alarm` test in `coop_officer_wait_goloud` | 3, 4, 11, 14, 21, 22, 23 |
| **P** | Preserve the Naxos hold-USE sabotage and objective toasts | Untouched except swapping two dead `setcvar` lines for `goLoud` | 14 |

---

## 8. Test plan

### 8.1 Preamble - required for every stage

1. `developer 1` - already covered: `autoexec.cfg:36` is `set developer 1` and `:966` is `seta logfile 2`.
2. `g_coopDisgDebug 1`, `coop_aggroDebug 1` - **seeded in `hzm-mohaa-coop-mod/autoexec.cfg` by Step 17, NOT pushed over rcon.** Round 3: `g_coopDisgDebug` appears in no cfg in the mod, and `coop_aggroDebug` is only ever **read** (`aihandler.scr:275/1023/1053/1088`, `aisquad.scr:115`, `morale.scr:72`, `global/alarm_system.scr:389`) and never seeded - so it is `""` for the whole run and `^~^~^ AGGRO`, `AGGRO BLOCKED`, `AGGRO_SRC` and `ALARMTRIP` **never print**. Absent markers then read as PASS on TP-2b's negative keystone criterion, which is a false verdict of exactly the bug-1633/1634/1635 class. **Both must be 0 for a real play session.**
3. **Drive the console over rcon rather than handing the user cvar homework** (`docs/21-user-preferences.md:54`). Client: `scratchpad/rcon.py` -> `127.0.0.1:12203`, password in `autoexec.cfg`; the connectionless-prefix trap is recorded at `docs/TRAPS.md:569`. **rcon is available only once a map is running** - `net_ip.c:1644-1647` routes an incoming packet to `Com_RunAndTimeServerPacket` only `if(com_sv_running->integer)`, otherwise to `CL_PacketEvent`, so a connectionless rcon reaches `SVC_RemoteCommand` (`sv_main.c:676`, dispatched at `:786`) only after a map is loaded. Use rcon for **mid-run probes and the map-to-map hop, never for the first load of a session**. v2.1's "push items 1 and 2 before the map starts" and item 4's rcon-at-session-start recipe are both **not executable**; that is why items 1 and 2 are cfg seeds.
4. Start with the ordered pair, in this order:
   ```
   set ui_dmmap m2l2a
   exec coop_mod/start_server.cfg
   ```
   `start_server.cfg` ends in `ui_startdmmap 2` and reads `ui_dmmap`; v2 had the order inverted and never set `ui_dmmap` anywhere, so a tester following it literally booted whatever map was last selected. Never a bare `map` or `devmap`. `+set g_gametype 2` on the command line applies to the **dedicated / maptest** path only; on the listen path `ui_startdmmap 2` sets the gametype itself.
5. **Prove the artifact before trusting the log** (bug-1633 / 1634 / 1635):
   - **A SHA256 comparison of the deployed `game.dll` in both roots against `openmohaa-hzm\.cmake\code\server\fgame\Release\game.dll` is the PRIMARY check.** Round 3 measured v2.1's string scan and it is **already useless**: `grep -ac g_coopDisgParity` returns 1 on **both** `G:\mohaa-gl2\game.dll` and the GOG-root copy **today**, before any change, because bug-1638 shipped. It passes identically before and after every Phase B edit, and it was the only dll-side check in the list. `build.ps1` only *warns* when a running game holds the file, so a silently failed copy would let TP-1 run against the old binary and be signed off - precisely the false-verdict class this item exists to prevent. (bug-1634's `grep -qa coop_coverAuto` worked only because that string was introduced BY that change.)
   - A **per-change token** as the secondary scan: each Phase B commit introduces a unique identifier (a new cvar name, or a `Com_Printf` build stamp) and the gate greps for **that** token.
   - pk3 member timestamp compared against the `InitGame` line;
   - the `stealth.scr::init` boot assertion (`^~^~^ST BOOT`) present with the expected cvar values - **required only for the Phase C stages on m2l2a** (TP-2, TP-2b, TP-5, TP-5b, TP-6, TP-8, TP-8b, TP-10). Round 3: TP-BASE runs before any Phase A edit, TP-0 / TP-0b / TP-1 run before Phase C creates `stealth.scr`, and TP-R runs on maps Step 14 never wires - so five stages **cannot** emit it, and demanding it universally trains a tester to discount the marker where its absence genuinely IS a hard fail. The pk3-timestamp, SHA256 and log-freshness proofs stay universal;
   - **log freshness:** the log file's mtime must post-date the deploy, and the `InitGame` line for the run under test must be the **last** one in the file;
   - **cfg consistency:** grep every `coop_defaults.cfg` / `autoexec.cfg` copy under both deploy roots **and the autotest homepath** and assert one consistent value for `coop_stealthStart`, `coop_disgAggroParity` and `g_coopDisgParity` (Step 17).
6. Log: **`G:\mohaa-gl2\home\maintt\qconsole.log`**, `logfile 2`. **Not** `%APPDATA%\openmohaa\maintt\qconsole.log` - `build.ps1:123-125` records that the live launch profile uses `fs_homepath G:\mohaa-gl2\home`, and the APPDATA copy is a week stale. v2 named the stale path, which would have made every grep-based pass criterion in 8.3 read a file predating the feature.
   - **The log is TRUNCATED at every launch** - the current file contains exactly one `InitGame` line, which is what item 5's "last one in the file" requirement implies. So **after each stage, copy `qconsole.log` to `qconsole.<stage>.<timestamp>.log` before the next launch.** Without this, TP-BASE's allowlist artifact is destroyed by the very next run and every later stage's "no `Script Error` outside the recorded baseline" silently degrades to "no NEW Script Error" - the criterion the plan explicitly rejects, because Script Errors do not kill threads (`scriptvm.cpp:1881-1883`) and accumulate. **Commit the TP-BASE allowlist as a text file under `docs/proposals/m2l2a_v2_research/`**, and have the item 7 monitor do the copy automatically.
7. **Machine-parse the markers.** Run a monitor over the live log in the `maptest_monitor.ps1` / `maptest_watchdog.ps1` pattern that emits per-stage PASS / FAIL against the 8.2 grammar and leaves an artifact showing which markers actually appeared. With thirteen-plus stages at 3-6 grep criteria each, a manual-only loop is where a wrong start recipe or a missing `^~^~^ST BOOT` goes undetected.

### 8.2 Marker grammar (restated here; do not cite v1)

| Marker | Meaning |
|---|---|
| Marker | Emitted by (step) | Meaning |
|---|---|---|
| `^~^~^ST BOOT phase=<p> start=<n> aggroParity=<n> parity=<n>` | 13, 17 | director init, one per map load. **On the Phase C m2l2a stages its absence is a hard fail, not a missing print** (see 8.1 item 5 for the scoping) |
| `^~^~^ST TAGGED n=<count>` | 4, 13, 14 | `initScene` finished tagging. **TP-2 asserts the COUNT** (not TP-0b - `initScene` is Phase C and gated on `coop_stealthStart`), because an absent prone marker on an empty tag set is not evidence |
| `^~^~^ST SWEEP removed=<n>` | 15 | the loose-weapon entnum sweep, so TP-2 can prove the removal rather than infer it |
| `^~^~^ST LOUD reason=<r> draw=<0\|1>` | 13 | the one-way weapons transition, exactly once |
| `^~^~^ST SUSPEND` | 13, 21 | alarm raised; disguise axis suspended |
| `^~^~^ST QUIETDISG reason=doused` | 13, 21, 22 | alarm doused; disguise axis restored (D1) |
| `^~^~^ST REARM blocked` | 22a | the re-arm cooldown refused a re-ring. Without it, a suppressed re-ring and a re-ring that never happened are indistinguishable |
| `^~^~^ST TRIOBREAK <which>` | 13 (`trioWatchdog`) | the unarmed trio was half-cleared - always a defect. Asserted before AND after LOUD, by a label that never exits |
| `^~^~^ST FAULT weapon player=<n>` | 13 | T7: a real Weapon in hand during QUIET |
| `^~^~^ST FAULT takealldisguises reason=nil` | 21a | `takeAllDisguises` reached with NIL parameters on a stealth-director map |
| `^~^~^ST FAULT disguisehandler stuck` | 21d | the owning `disguiseHandler` loop did not clear its ownership flag within the bound |
| `^~^~^ E5 cleared=<n>` | 23 | how many actors had `m_bForceAttackPlayer` cleared on this douse. TP-10's direct observable |
| `^~^~^ AIEVENT MISC muted=<0\|1> anyDisguised=<n>` | 9 | E4's own observable. **TP-9's primary grep** |
| `^~^~^ HURT actor=... hp=... oldtype=... hasAlarm=<0\|1>` | 4 (A3) | Step 4 instrumentation. **`hasAlarm` is a 0/1 boolean, never the label name** - `alarmthread` is a const array and concatenating it throws |
| `^~^~^ PERS actor=... roll=... type=... hasAlarm=<0\|1>` | 4 (A3) | `coop_apply_personality` entry |
| `^~^~^ PRONEPOSE actor=<tn> wg=<g>` | 4 (A3) | `coop_prone_shooter` actually posed this actor. Printed **after** the weapongroup reject at `officer.scr:1740-1744` and gated on `coop_aggroDebug` |
| `^~^~^ PRONEDBG wg=<g> tries=<n>` | **pre-existing, NOT this plan** | shipped at `officer.scr:1736`, gated on `coop_aiBehav`, no actor field, printed **above** the whitelist reject so it fires for actors that never pose. **Do not grep for it as if it were `PRONEPOSE`** |
| `^~^~^ RETREATDBG ...` | **pre-existing** (`wounded.scr:182`) | Writer 3's retreat path. TP-0b / TP-R assert it never fires on a tagged or `$ai_alarm` actor |
| `^~^~^ AGGRO actor=... target=... tgtDisguised=...` | pre-existing | funnel probe. **Requires `coop_aggroDebug`, which 8.1 item 2 now seeds** |
| `^~^~^ AGGRO BLOCKED actor=... target=...` | pre-existing | the gate refused |
| `^~^~^ AGGRO_SRC <caller>` | pre-existing | which path called the funnel. Three emitters only: `aihandler.scr:1023`, `:1166`, `:1283` - **none on the AI-event path** |
| `^~^~^ ALARMTRIP actor=... enemyDisguised=... alarm=...` / `^~^~^ ALARMTRIP BLOCKED ...` | **pre-existing** (`global/alarm_system.scr:391` / `:403`, both gated on `coop_aggroDebug`) | an AI pushed, or was refused, onto the alerted queue. TP-10 asserts absent for 10 s after `^~^~^ST QUIETDISG` |
| `^~^~^ OFFICER release policy=<p> alarm=<n>` | 14 | the wave gate released. Added because `officer.scr` shipped no wave marker at all |
| `^~^~^ OFFICER wave n=<n>` | 14 | a wave spawned. TP-2 asserts absent, TP-8 asserts present |
| `^~^~^ OFFICER goloud-timeout` | 14 | the 600s wave gate expired |
| `^~^~^ PAPERS guard satisfied - whole squad waved through` | pre-existing | `coop_paperPassAll` fired |

### 8.3 Stages

Player-count requirement is explicit. Everything marked **2P+** requires a second body and is deferred until one is available; nothing in Phase A, B0 or B1 depends on those stages passing.

| Stage | Players | After | What to do | Pass criteria | Log greps |
|---|---|---|---|---|---|
| **TP-BASE** | solo | **before any Phase A edit** | One clean m2l2a run with today's code. **Then archive the log per 8.1 item 6 and commit the allowlist as a file** - the next launch truncates `qconsole.log`. | Capture the complete set of `Script Error` lines. **This set becomes the allowlist.** Every later stage's criterion is "no `Script Error` **outside the recorded baseline set**", never "no new Script Error" - Script Errors do not kill threads (`scriptvm.cpp:1881-1883`), so they accumulate silently and bug-1632 is a known live emitter | `Script Error` |
| **TP-0** | solo | A3 (instrument) | m2l2a, current armed flow, no stealth start. Watch the card room, welders, sledgehammer and scientists for a full pass. | The `^~^~^ HURT` / `^~^~^ PERS` / `^~^~^ PRONEDBG` lines identify who is writing the anim. **State up front whether this run validates bug-1637's card shim or Step 4.** Expect `PERS` on every german and `PRONEPOSE` on roughly one in eight | `^~^~^ HURT`, `^~^~^ PERS`, `^~^~^ PRONEPOSE` |
| **TP-0b** | solo | A4 (fix) | Repeat TP-0 (still **no stealth start**). | No card player stands. No canteen anim and **no prone pose** on a scene actor. **Zero `^~^~^ PRONEPOSE` and zero `^~^~^ RETREATDBG` on any of the 13 `$ai_alarm` actors.** Welder / sledgehammer alarmthreads still fire when the alarm rings. **Scope note (round 3):** with no stealth start there is no `coop_sceneActor` tag - `initScene` is Phase C - so TP-0b measures **only** the `alarmthread` and `type_disguise == "salute"` exemptions. The tag-based half is measured by TP-2 | `^~^~^ PRONEPOSE` and `^~^~^ RETREATDBG` absent for `$ai_alarm` actors |
| **TP-R** | solo | after Phase A, **again after A5**, again after Phase B | **Non-stealth regression, on THREE axes (round 3 added the third).** (a) one combat map, m1l1 or m3l1a; (b) an **alarm-heuristic** map, `m6l1c` or `e1l4` - only four maps start the alarm system (`e1l4/PreShip.scr:15`, `e1l4/Ship.scr:32`, `m2l2a.scr:123`, `m6l1c.scr:76`) and Step 4's `alarmthread` heuristic can only be exercised on those; (c) a **disguise-checker** map not otherwise covered - **`m1l2a`** (the saluting checkpoint, and an open crash-hunt map where a regression would be misattributed), `m5l3` if time allows. Axis (c) exists because Step 2 drops the `cansee` term from the gate and is therefore **not** behaviour-neutral on maps with no disguise. | Hurt troopers still cover-seek and drink on the combat map. e1l4 / m6l1c disguise and alarm flow unchanged. m1l2a's saluting checkpoint behaves as today. **The engine spawn loadout still arrives normally** on the combat map and on e1l4 (Step 6b). `^~^~^ PERS` coverage on m3l1b or m6l1c is unchanged before and after A4 (the `type_disguise` predicate of Step 4). **Three runs, not two** - Steps 18 and 19 are Phase A commit A5 and touch `dbno.scr` / `medkit.scr` / the papers spawn path, and v2 scheduled TP-R only at two points that both preceded them | baseline-diff `Script Error`, `^~^~^ AGGRO BLOCKED`, `^~^~^ PERS`, `^~^~^ RETREATDBG` |
| **TP-1** | solo | **A1 (Phase A)**; may be repeated after B1 | Approach goatsbutt holstered; show papers; approach sentry2dude with papers2. Then walk past the same guard again. | Guard challenges, accepts, **does not freeze**, and salutes on the next pass **without attacking**. Round 3 moved this from "after B0 + B1": everything it tests is delivered by Step 1 (deleting `itemhandler.scr:1181`) and Step 2 (the six anim gates), i.e. commit A1. B0 is pure NULL guards with no behavioural change and B1 touches neither the freeze nor the salute attack - so scheduling it after B1 left the most valuable and most reversible part of the plan shippable with no playtest evidence | `^~^~^ PAPERS` |
| **TP-2** | solo | Phase C | Stealth start ON. Spawn -> locker room -> uniform -> goatsbutt -> Naxos (loud walk-in) -> papers2 -> sentry2dude -> endlevel. | `^~^~^ST BOOT` present. Unarmed the whole way to the Naxos bust. `^~^~^ST LOUD reason=naxos draw=0` within about 0.5s. **`^~^~^ST TAGGED n=` present and the count matches the expected scene-actor set size** - this is the acceptance criterion for round-3 blocker R3-B2, and TP-2 is the first stage that can measure it. `^~^~^ST SWEEP removed=` present with n >= 1. Kit arrives **holstered and COMPLETE** - a two-primary armory kit survives the flip. Papers still work at sentry2dude afterwards **including after a death**. **No `^~^~^ OFFICER release` and no `^~^~^ OFFICER wave`** - measurable only because Step 14 adds those positive markers; `officer.scr` shipped none | `^~^~^ST BOOT`, `^~^~^ST TAGGED`, `^~^~^ST SWEEP`, `^~^~^ST LOUD`, `^~^~^ST TRIOBREAK`, `^~^~^ST FAULT`, `^~^~^ OFFICER` |
| **TP-2b** | solo | Phase C | Same, but take Naxos via the **quiet hold-USE sabotage**. | State stays QUIET past Naxos. sentry2dude accepts papers2. Mission completes with **not one** LOUD marker. **This is the keystone, and the corrected T5 predicate is what makes it reachable** - with v2's predicate the 13 `$ai_alarm` actors alone would have tripped it | `^~^~^ST LOUD` must be absent; `^~^~^ST BOOT` must be present |
| **TP-5** | solo (**except the reconnect leg**) | Phase C | Lifecycle sweep during QUIET: die and respawn; get downed and revived; spectate and return; ~~disconnect and reconnect~~. Inspect model, hands and papers each time. **The disconnect/reconnect leg is NOT solo-executable and is re-marked 2P+:** the harness is a listen server (`coop_mod/start_server.cfg` ends `ui_startdmmap 2`), so the solo tester IS the host and disconnecting tears down the server and every `level.*` variable including `coop_stealthPhase`. Record it in `docs/OPEN.md` with the other outstanding 2P+ stages. (The DBNO revive legs **are** solo-executable: `dbno.scr:35` grants `coop_medkits = 1` per spawn, a script flag untouched by `itemhandler.scr:708`'s `takeall`, so `dbno_selfrevive`'s `local.medkits < 1` test at `medkit.scr:235-241` passes.) | Unarmed every time. **German uniform every time - check the WORN MODEL, not just the flag** (the armory-skin re-force at `player.scr:1097-1159` is the stomp risk, Step 10). Papers in hand every time. No TRIOBREAK, no FAULT | `^~^~^ST TRIOBREAK`, `^~^~^ST FAULT` |
| **TP-5b** | solo | Phase C | Cross the papers1 -> papers2 swap while standing in a checker's PAPERS state, and respawn inside the swap window. Also **respawn deliberately inside a checker's disguise-think range**. | Papers survive the swap in hand; a body spawned inside the window still ends up holding papers. **The checker does not transition to `DISGUISE_ENEMY` from the spawn frame** (Step 6b) | baseline-diff `Script Error` |
| **TP-6** | solo | Phase C | Trigger LOUD, then repeat TP-5. Also respawn **within one second** of the LOUD moment. Also get **downed before** the LOUD and revived after it. | Armed every time, including the one-second respawner (epoch) and the revived-after-LOUD body (Step 11 revive hook). Kit is complete, not the short disguise kit | `^~^~^ST LOUD` once only |
| **TP-8** | solo | Phase C | Ring the alarm deliberately. **Then respawn mid-alarm.** | Everyone armed **and drawn** - which requires `coop_drawAllWeapons` to resolve weapons by name rather than through `activatePlayerWeapon` (Step 11) and `draw` to be derived as 1 inside `takeAllDisguises` (Step 21a). **A mid-alarm respawner comes back DRAWN, not holstered with the hint** (Step 11's tail predicate). `^~^~^ST SUSPEND`. Backups spawn. Welder / sledgehammer / scientist alarmthreads all fire. Officer waves **do** wake (`^~^~^ OFFICER wave` present). Combat feels vanilla. Also record the german actor count before and after, to confirm replica scaling was never suppressed | `^~^~^ST LOUD reason=alarm draw=1`, `^~^~^ST SUSPEND`, `^~^~^ OFFICER` |
| **TP-8b** | solo | Phase C | Ring the alarm **after** a non-alarm LOUD has already happened. | Weapons are **drawn** (the `coop_drawAllWeapons` path), `^~^~^ST SUSPEND` fires, officer waves wake. `coop_stealthReason` still reads the first reason - that is correct - but `coop_stealthAlarmEver` is 1 | `^~^~^ST SUSPEND` |
| **TP-10** | solo | Phase C (D1) | **Recoverable alarm.** Ring the alarm, fight, then douse a switch: once standing in the open, once from cover with no guard in line of sight. Then **ring and douse a second and a third time**. | `^~^~^ST QUIETDISG reason=doused` within 0.5s, and `^~^~^ E5 cleared=<n>` with n > 0 on the same edge - without that count, "E5 worked" and "LOS never broke" are indistinguishable, and the stage is asked to accept the latter as a non-failure. Uniform restored, on-screen line shown. **The tester is NOT force-holstered** (Step 21c). **From cover: guards stop hunting and re-challenge within 30 seconds. In the open: they do not, until LOS breaks** - that is the documented contract (P5), not a failure. The alarm does **not** immediately re-ring; if it is refused, `^~^~^ST REARM blocked` says so (Step 22a). **Reinforcements still spawn on the second and third alarm** (Step 22a-bis's backup-counter fix). If Step 22b ships, a second alarm still produces welder / cower / scientist reactions **and re-running `cower` / `weldinginterupt` does not strand or re-aggro them** (Step 22b constraint 3); no `^~^~^ ALARMTRIP` in the 10 s after `^~^~^ST QUIETDISG` | `^~^~^ST QUIETDISG`, `^~^~^ST SUSPEND`, `^~^~^ST REARM`, `^~^~^ E5`, `^~^~^ ALARMTRIP` |
| **TP-3** | **2P+** | B2 | A shows papers to goatsbutt while B stands in the same room; then B shows papers to the same guard; then A draws a weapon while B is mid-check with a different guard. **Also: B stands visible 300u behind the checker while A is being challenged at 100u.** | A's check resolves on A's action only (E3a). B's check is not aborted or redirected by A's weapon (Step 2). **The checker does not HALT-then-ATTACK because it measured B's distance (E3b).** No guard permanently ignores a re-holstered player | `^~^~^ AGGRO`, `^~^~^ PAPERS` |
| **TP-4** | **2P+** | B2 | Host deliberately hidden behind a wall, or dead, while the client walks up to a sentry. | The client **is** challenged and can pass (E1). | `^~^~^ PAPERS` |
| **TP-7** | **2P+** | B1 | Stand in officer1's office doorway and in the crateguy path; block them deliberately, with the host disguised and with the host dead. | Actors path around or wait. No scene actor converts to a turret-attacker. No map-wide aggro. **Result identical whether the blocker is the host or a client** - this criterion is only reachable because Step 6 item 2 gives `ForceAttackPlayer` a target parameter | `^~^~^ AGGRO` |
| **TP-9** | **2P+** | B2 | One player opens `$likeynorwaydoor` while disguised, host elsewhere and undisguised. | The door noise does not alert the Norway pair (E4), **evidenced by `^~^~^ AIEVENT MISC muted=1` on the door event** (Step 9's new print). **TP-9 is the only evidence for E4** - the originator branch is dead code in this tree - so it must not rest on `AGGRO_SRC` alone, whose three emitters are all in `aihandler.scr` and none on the AI-event path; an absent `AGGRO_SRC` is equally consistent with "the pair never had line of sight" | `^~^~^ AIEVENT MISC` (primary), `^~^~^ AGGRO_SRC` (secondary, must be absent) |

**Solo-verifiable proxy for TP-3 / TP-4 / TP-7 / TP-9:** none can be faked with one body. Where a second body is unavailable, run TP-2 / TP-2b / TP-10, then land B2 with the multiplayer stages marked outstanding in `docs/OPEN.md` rather than claiming them passed.

Log every failure to `.wolf/buglog.json` **before** fixing it.

### 8.4 Verification gate between phases (ordered, not optional)

Run all of these before **each** deploy point, and before treating any playtest as evidence, **in this order**. **The tool paths in v2 were wrong** - `scratchpad/` holds only `rcon.py`; the verifiers live in `docs/tools/`. `docs/TRAPS.md:567` already records "check tools exist before citing them - `scratchpad/` is wiped periodically".

0. **BACK UP FIRST (round 3 reordered this).** Copy the **current** `game.dll`, `game.pdb` and `cgame.dll` in **both** `G:\mohaa-gl2\` and the GOG root to `*_pre_stealth_bak`, **before running `build.ps1`**. v2.1 ordered the backup as item 8, after item 7's `.\build.ps1` - and `build.ps1:157-167` unconditionally `Copy-Item -Force`s the `$binaries` array into both roots, so the pair section 11's rollback row depends on would already have been destroyed. (`G:\mohaa-gl2` currently shows many `*_pre_*_bak` siblings but no `*_pre_stealth_bak`.)
1. `python docs/tools/depthscan2.py <each touched .scr>` - running depth must never go negative and must be 0 at every column-0 label. Note `scrlint.py` (item 4, and already a hard gate inside `build.ps1:8-9` over the whole mod tree) covers BOM, non-ASCII, negative depth, non-zero depth at EOF and unterminated strings/comments; **the rule depthscan2 adds that scrlint does not is the column-0-label-at-depth-other-than-0-or-1 rule**, i.e. the bug-239 cancelling-error case. That is the reason to run it per file.
2. `python docs/tools/linecheck.py <each touched .scr and .cfg>` - line endings, BOM, non-ASCII.
3. `python docs/tools/quotecheck.py <each touched .scr>` - quote balance.
4. `python docs/tools/scrlint.py <each touched .scr>`.
5. **Derive the "touched" list from `git diff --name-only`, do not maintain it by hand.** The reference list, corrected in round 3 (v2.1's "explicit" list omitted six edit targets): the six `anim/disguise_*.scr` files - `disguise_accept.scr`, `disguise_salute.scr`, `disguise_wait.scr`, `disguise_deny.scr`, `disguise_halt.scr`, `disguise_enemy.scr`; `coop_mod/{stealth,itemhandler,aihandler,player,dbno,medkit,officer,wounded,weaponstate,main,replace}.scr`; **`global/alarm_system.scr`** (Step 22a's index floor and cooldown reader), **`global/items.scr:477`**, **`maps/e1l4/PreShip.scr:88`**, **`maps/e1l4/Ship.scr:416`** (the three non-alarm `takeAllDisguises` callers Step 21a edits), **`maps/e1l2/Artillery.scr`** (Step 3), `global/wrenching.scr`, `maps/m2l2a.scr`, and the cfgs of Step 17.
6. `python docs/tools/docgen.py check` (exit 1 means stale; fix with `build`, never by editing generated output).
7. `.\build.ps1` from `C:\mohaa-coop-dev`. **Script-only deploy points (every Phase A and Phase C point) must NOT ship binaries.** `build.ps1:151-167` copies `cgame.dll`, `game.dll`, `game.pdb` and `renderer_opengl1.dll` into every root with **no** condition beyond `Test-Path` on the source, so any locally-built B0/B1/B2 output sitting in `.cmake` rides along with a Phase A script commit - and item 9's string scan cannot detect an unintended *newer* engine, only a missing one. Add a **`-ScriptOnly`** switch to `build.ps1` that skips the `$binaries` loop and require it at every script-only deploy point; failing that, require `git status --short openmohaa-hzm` clean **and** a recorded hash of the `.cmake` outputs in the stage log before any script-only playtest. TP-R's whole purpose is attribution.
8. Engine only: rebuild, then let item 7's `build.ps1` deploy `game.dll` **and** `game.pdb` to both roots (the manual copy v2.1 described here is redundant - `build.ps1` already does it). The backup is item 0.
9. Proof of load, per 8.1 item 5: **SHA256** of the deployed `game.dll` in both roots against the `.cmake` output (primary), the per-change token scan (secondary), pk3 member timestamp against the `InitGame` line, log mtime post-dating the deploy, and the cfg-consistency grep of Step 17.

---

## 9. What gets retired

| Item | Location | Why |
|---|---|---|
| `coop_stealthNoAggro` cvar | `autoexec.cfg:1176`, `coop_defaults.cfg:210`, `aihandler.scr:1076` | Whole-window gating retired by bug-1639; measured unnecessary; its blanket refusal sat in the papers-challenge path |
| `coop_stealthFunnelGuard` cvar and its predicate | `aihandler.scr:1076` | Dead by construction. The funnel guard becomes unconditional, per-target, and routed through the one helper |
| Two `setcvar coop_stealthNoAggro 0` "lifts" | `m2l2a.scr` ~:493, ~:592 | Dead wiring |
| `coop_stealthArmOnHurt` (entire label) - **deletion assigned to Step 11 / commit C in round 3**, having previously had no step, no phase row and no rollback entry | `itemhandler.scr:1375-1387`; its body at `:1381` is `thread coop_armOnBlown`, i.e. **the second live caller the Step 11 rename must not strand** (the others are `itemhandler.scr:1162`, converted by Step 14, and `maps/m2l2a.scr:494` / `:593`, also converted by Step 14) | Zero external callers; superseded by `coop_blownOnDamage` |
| `local.guard type_disguise "none"` | `itemhandler.scr:1181` | The bug-1631 freeze arm, and redundant - `State_Disguise_Accept` already demotes an accepting sentry to salute permanently |
| `thread ...canseeUndisguisedPlayers` as a gate | `disguise_wait.scr:13`, `disguise_deny.scr:14`, `disguise_halt.scr:18`, `disguise_accept.scr:10`, `disguise_salute.scr:36` | **A room test cannot gate a per-target attack.** That reason alone is sufficient and is the only one this document now gives. v2 additionally cited "a thread handle in a condition is always truthy (bug-1609)" - **both halves of that are wrong**: `thread <label>` in a value context returns the label's `end` value when the label does not yield (`listener.cpp:4233-4242`, `scriptvm.cpp:989-994`, `:558-560`), and there is no `bug-1609` in the ledger. Do not re-introduce either claim, and do not add `itemhandler.scr:956/1002/1028` to the Step 2 sweep on its strength |
| ~~`coop_stealthBlocksAggro`'s NIL-target room walk~~ | ~~`aihandler.scr:1213-1222`~~ | **NOT RETIRED, and NOT parameterised.** v2 retired it; round 2 established that three of the helper's four callers pass NIL and the walk is the only thing standing them down, on every disguise map, so v2.1 made fail-open a per-caller argument. **Round 3 deleted that argument too:** the walk already ends `(0)` whenever any live player is undisguised, so fail-open buys no aggro and only opens the permanent latch. The helper's signature is unchanged. See P2 and Step 3 item 3 |
| Bare `attackplayer` **in the aggro funnel** | **`aihandler.scr:1103`** (round 3 corrected this from `:1102`, which is the `coop_isAttacking` flag write and must be preserved) | Sets the one-way `m_bForceAttackPlayer` latch and confirms entity 0 (hunts the host, not the offender). Replaced by `attackentity` when a target is supplied. **Scope: the funnel only.** The twelve raw sites inside `maps/m2l2a.scr` are NOT converted; E5 (Step 23) is what makes that survivable under D1 |
| Direct `thread coop_armOnBlown` in `takeAllDisguises` | `itemhandler.scr:1162` | Routed through the phase-tolerant `notifyLoud` so exactly one place decides `drawWeapon` - **not** because of a concurrency hazard, which `itemhandler.scr:1395-1396` disproves |
| Draft E2 ("skip the bump when the blamed player is disguised") | `actor.cpp:3363, 3391` | Already done by `IsTeamMate` + parity. Replaced by bug-1640's recorded residual, **plus the `ForceAttackPlayer` target parameter v2 missed** |
| ~~The `officer.scr:118` reason clause~~ | ~~`officer.scr:118`~~ | **Never added.** Dead code by construction - `level.alarm` is already 1 whenever the clause could be true. D2 is satisfied by shipped code |
| ~~"Re-run replica cloning at the phase flip"~~ | v2 sections 12 and 14 | **Deleted.** Its premise is false: cloning is never suppressed during QUIET. `coop_tryDuplicateActor`'s gates contain no stealth test, and the in-code note at `aihandler.scr:266-272` says so in terms - only the target hand-off at `:277` is gated. There is nothing to reverse and no step to write |
| v1 master plan sections D4 and D5 | `docs/proposals/m2l2a_stealth_master_plan.md` | Superseded by bug-1638 / bug-1639. Mark the file superseded |

---

## 10. Lessons learned

1. **Adopt engine rules; never invent parallel ones.** The engine's rules are: disguised means no weapon or an InventoryItem in hand; `enemy != NULL` is not "engaged"; an accepting sentry is already permanently demoted; a disguised player is already a teammate for collision purposes; **and an alarm suspends a disguise rather than destroying it.** Read the rule, defer to it, delete the parallel implementation. D1 is delivered by deleting a strip, not by adding a restore.
2. **A one-way latch is not an everyday primitive.** `attackplayer` -> `ForceAttackPlayer` sets a flag cleared only in the Actor constructor, archived into savegames, and it confirms entity 0 rather than the actual offender. The moment a feature becomes recoverable, every such latch becomes a permanent bug.
3. **Room tests cannot gate per-target actions.** The failure is invisible in solo testing - which is why it survived in six files.
4. **When you find one instance of a bad pattern, grep for the pattern, not the line - and then grep again.** v2 found four gates; there were six. v2 found one stranded statement below an `end`; round 2 found three; **round 3 found four, across the same three files** (`disguise_accept.scr` has two, at `:18` and `:22`). v2 found two raw `attackplayer` sites in `m2l2a.scr`; there are twelve. v2 named one scene-actor writer; round 2 found the dominant second; **round 3 found a third** (`coop_mod/wounded.scr`). v2 named two cfg seed sites for `coop_stealthStart`; **there are five.** Each round's "complete" inventory was incomplete.
5. **"Blocks future grants" is not "unarmed"** on a map with a world weapon entity that respawns under `g_gametype 2`.
6. **Watch for hooks below early exits.** bug-1624 was "the papers re-give sat below the `coop_noWeapon` exit". The uniform give still is.
7. **Thinkstate is a lying oracle.** The script getter reports the *top* think level. Worse than v2 knew: `THINKSTATE_ATTACK` is also where `type_attack "alarm"` actors live and where a disguise HALT lands 1.5s after a routine 256u walk-away, so "attack with a player enemy" is not evidence of a bust.
8. **When a repair loop keeps failing, the cause is a writer you have not found.** v2 blamed the hurt-trooper branch. That branch only fires on actors `coop_apply_personality` already tagged - the real writer was one level up, running on **every** german, with a 12% chance of pinning any actor prone with `enableEnemy = 0`.
9. **Prefer deletion to deferral.** The most reliable code is the code you removed.
10. **A systematic backstop only works if its predicate is one the sites actually set - and one that quiet operation does not.** v2 fixed the first half and broke the second: its T5 predicate fires on thirteen `$ai_alarm` actors during a perfectly clean stealth run.
11. **A behavioural transition must be as reversible as the thing it models.** Vanilla's Naxos bust is local and survivable; vanilla's alarm is a toggle. Match the granularity of the fiction - and note that "reversible" has a **per-actor** cost the fiction does not mention: an actor already in ATTACK is disguise-blind until it loses line of sight.
12. **A config seed in two files is a config seed you will edit once**, and a log path in two places is a log you will read the stale copy of.
13. **`failed_attempts` is the most valuable field in the log** - but only if the entries exist. v2 cited `bug-1605`, `bug-1607` and `bug-1609`, none of which are in the ledger, and built two design decisions on the third. **Cite the code, or cite an id you have just grepped for.**
14. **A "no-op" fix costs more than no fix.** v2's officer clause, v2's `aimaneuver.scr` gate, v2's `setEnemyAttackStates` gate on a field the previous label already NULLed, and v2's Step 16 bullet 1 are four separate no-ops, each of which would have consumed a review, a deploy and a playtest stage.
15. **Wire the entry point.** The single most consequential defect found in round 2 was that no step called `stealth.scr::init`. Every marker, tag, sweep and watchdog in Phase C depended on it, the test plan greps for its boot line, and the map would still have *looked* like it was working.
16. **`group` is the ScriptClass.** A file-qualified `thread` call allocates a fresh one. Any label that reads `group` needs a same-file entry point that populates it.

---

## 11. Rollback

Layered, each layer independently revertible without touching the others.

| Layer | Kill switch | Effect |
|---|---|---|
| Phase C (the director, incl. D1 recovery) | `coop_stealthStart 0` in **both** cfgs | `stealth.scr::init` never runs; phase stays NIL; every Phase C gate inert; `takeAllDisguises` sees `coop_stealthPhase == NIL` and passes `permanent = 1`, i.e. today's one-way behaviour; map reverts to today's armed flow |
| D1 alone (keep the director, drop recoverable alarm) | **`coop_stealthRecoverAlarm 0`**, seeded alongside the other cvars in Step 0 / Step 17 and read by `takeAllDisguises`'s `permanent` derivation (Step 21a) | Alarm becomes permanent again; everything else in Phase C stands. **Round 3 note:** v2.1 named this cvar exactly once, here, and no step created it - a documented kill switch that did not exist. It is now real. Its alternative in v2.1 ("force `permanent = 1` at `alarm_system.scr:704`'s call") is no longer applicable, because 21a evaluates `permanent` inside the label and does not edit that call |
| Phase A (shared script) | `coop_disgAggroParity 0` in all cfg copies | Disables the **whole** `coop_stealthBlocksAggro` gate in `attackPlayer` - for every target, not merely NIL ones - and Step 4's non-tag heuristics, restoring today's behaviour at runtime (today's funnel guard at `aihandler.scr:1076` requires `coop_stealthNoAggro != "0"`, seeded 0, so the shipped funnel is already fully open). Steps 1, 2, the `coop_sceneActor` tag, the `aihandler.scr:1021` reader swap, and Steps 18/19 remain (correctness fixes with no sane "off"). **There is no `failOpenOnNil` argument to gate - deleted in round 3.** |
| T5 (the systematic bust backstop) | roll back B3 | T5 depends on the `forceattackplayer` getter E5 ships (section 4.2). Without B3 it is inert and expectation 4 rests on T1, T3, T4 and T7; T4 still catches a bust once the player is shot, so the mission stays winnable |
| Engine parity + E1..E5 | `g_coopDisgParity` - **latched; takes effect at the NEXT MAP LOAD** | Reverts to vanilla / SP-only paths |
| Officer waves on loud | nothing to delete - waves are alarm-only via the shipped `level.alarm` test in `coop_officer_wait_goloud` | v2's rollback row named a clause that does nothing; corrected |
| Scene protections | call `unprotectScene` at init, or delete the `protectScene` call | Card trio behaves as today |
| Engine binaries | `*_pre_stealth_bak` copies of `game.dll` + `game.pdb` in **both** roots | Restore both roots together |
| Script layer | git revert per commit: **A0 (Step 0, cfg seeds only)**, A1 (1+2), A2 (3), A3/A4 (4), **A5 (18+19)**, B0, B1, B2, **B3**, C | Phase A commits are independently useful; prefer reverting C first. Round 3 added A0, which v2.1 omitted from both the phase index and this list |

### The parity switch is not a live toggle, and parity 0 is not a safe resting state

`g_coopDisgParity 0` was advertised in v1 as a live, no-restart kill switch. It is not safe as one, and round 2 sharpened why.

`player.cpp:5490` is `if (g_gametype->integer == GT_SINGLE_PLAYER || s_coopDisgParity->integer) {` and the **first statement inside that block is `m_bIsDisguised = false;`**. With parity 0 in coop the whole block is skipped, so the flag is not merely stale - **it is never reset, and can be frozen TRUE**. A grep of every writer confirms there is no other one (`sentient.cpp:869` ctor, `:3338` archive, `player.cpp:5491/5497/5512`). A frozen-TRUE flag then reaches `IsTeamMate` (`sentient.cpp:4018` - every player is a teammate of every actor), `actorenemy.cpp:164` (zero threat), `:469`, and both obstacle branches. And because the recompute is what an alarm uses to clear the flag, **the alarm cannot fix it either**. Script reads `is_disguised` as truth in shipped code (`aihandler.scr:1193` in `coop_stealthBlocksAggro`, and `:1234` inside `canseeUndisguisedPlayers` - round 3 corrected the second anchor from `:1227`, which is the cMTE trace line) and this plan adds more readers.

Do both:

1. **Register `g_coopDisgParity` with `CVAR_LATCH` at a real registration site** - once in `G_InitGame`, or re-`Cvar_Get` at the top of every level, with a single cached pointer that E1..E5 all read. **Do not bolt `CVAR_LATCH` onto the lazy function-local static inside `Player::Think` (`player.cpp:5487-5489`)**, which is where the cvar is currently created and nowhere else; a latched value is only applied on the next `Cvar_Get` after a game-module reload, and that static caches the pointer for the process. Note also that a normal `map <name>` **does** reload the game module (`sv_ccmds.c:269`, `sv_init.c:633`, `:668-677`) so the latch applies; only `map_restart` (`sv_ccmds.c:335`) does not.
2. **Make parity 0 safe by construction:** move `m_bIsDisguised = false` for MP clients OUTSIDE the parity gate, so the worst case is frozen-FALSE (vanilla-equivalent) rather than frozen-TRUE.

**v2.1's third item - a `coop_disgTruth` accessor - is DELETED (round 3).** It appeared exactly once in the whole document, had no step, no phase, no commit and no step-index entry, and it flatly contradicted the steps: Step 2 adds six raw `self.enemy.is_disguised` readers, Step 3 adds a seventh at `aihandler.scr:1021`, and section 4.2's T5 used to add an eighth - none of which called it. It is also unnecessary once item 2 lands: with `m_bIsDisguised = false` outside the gate, parity 0 is vanilla-equivalent for a raw reader, which removes the poison the accessor existed to neutralise.

---

## 12. Change log against the draft (v1 -> v2)

Retained for provenance. **Round-2 corrections to these same items are in section 15**; where the two disagree, section 15 wins and the step text has already been rewritten accordingly.

| Draft item | v2 change | v2 driver | Round-2 status |
|---|---|---|---|
| Step 2: four anim files | -> six; accept restructured | `disguise_accept.scr:10,16,22` | **extended**: three files need structural edits, not one |
| Step 3: new inline predicate in `attackPlayer` | -> call the existing `coop_stealthBlocksAggro`; NIL fails open; scope extended | `aihandler.scr:1184` | **partly reversed**: NIL must stay blocking; fail-open becomes a per-caller argument. `wrenching.scr:80` added; `aimaneuver.scr:150` removed |
| T5 predicate `flags["coop_isAttacking"]` | -> `thinkstate == "attack"\|"pain"` with a player enemy | the flag is written in three places | **premise refuted**: the engine DOES enter ATTACK against disguised players. Predicate re-derived with seven conditions |
| Step 6 (E2): "skip when disguised" | -> resolve the actual colliding player; skip `BecomeTurretGuy` | `sentient.cpp:4018`; bug-1640 | **extended**: `ForceAttackPlayer` hardcodes the target too, and the whole aggression branch must be skipped for `THINK_ANIM` actors |
| Step 4 exemption gated on `phase == "quiet"` | -> permanent for the tag; instrument-first | bug-1631 F3 | **extended**: the dominant writer is `coop_apply_personality`, not the hurt-trooper branch; tag recipe corrected for containers and real names; the `alarmthread` print would have thrown |
| takeAllDisguises rewiring justified by "runs twice concurrently" | -> rationale deleted; `notifyLoud` phase-tolerant | `itemhandler.scr:1395-1396` | **extended**: also draw-tolerant, and the reason must be passed by the caller |
| Step 12 epoch "calls `giveWeaponLoadout`" | -> set `group.player` first | `giveWeaponLoadout` takes no argument | **refuted**: `group` does not cross a file boundary. Needs a same-file entry label |
| Step 15: hide and restore the loose MP40 | -> remove it, or re-find by classname | bug-1632 | **partly refuted**: there is no find-by-classname primitive. Removal needs the `getentbyentnum` sweep recipe |
| Officer waves gated on LOUD | -> gated on `reason == "alarm"` | T5 on a local bust would spawn boss waves | **refuted as an edit**: already satisfied by the shipped `level.alarm` test. Clause dropped |
| Phase B as one block | -> B0 / B1 / B2 | solo cannot exercise E1/E3/E4 | **extended**: B0 covers three sites; B1 gains the `EquipWeapons` half; B3 added for D1 |
| E4 absent | -> added per-originator mute | research constraints | **corrected**: the originator branch is dead code; the "any disguised player" fallback is the rule |
| Rollback: `coop_stealthStart` covers everything | -> corrected; `coop_disgAggroParity` added | Phase A is unconditional shared-code change | **extended**: parity 0 is frozen-TRUE, not merely stale |
| Open decision 2 (replica cloning) | -> "decided: re-run cloning at the phase flip" | claimed enemy-count scaling was disabled | **DELETED**: the premise is false; cloning is never suppressed |
| Open decision 1 (world weapons) | -> decided: remove at init | - | kept, recipe supplied |
| Documentation / ledger work | -> Step 20 | - | kept; Step 20 given a home in the phase index |

---

## 13. Step 20 - documentation and ledger (mandatory, part of the work)

Not optional and not "session end tidying" - these are deliverables of the change. Step 20 runs **with each commit**, not once at the end.

**`.wolf/buglog.json`** - new entries for defects this plan discovered, logged **before** they are fixed:
1. The uniform give stranded below the `coop_noWeapon` early exit (`itemhandler.scr:762-766`) - the bug-1624 sibling.
2. The accept, salute, deny and enemy `attackPlayer` sites - attacks the player who just passed his papers, and strands `coop_paperPassAll` / the papers-prompt clear below the branch `end`.
3. The unguarded `G_GetEntity(0)` dereferences at **`actor.cpp:9039-9047`** (assign `:9039`, dereference `:9045`, passent2 `:9047`), `actor_grenade.cpp:348`, `:440`, and the unguarded `AddPotentialEnemy` at `actorenemy.cpp:279`.
4. The papers2 swap stripping papers from live hands (`m2l2a.scr:417-418`).
5. `coop_apply_personality` pinning arbitrary germans prone with `enableEnemy = 0`, removing disguise checkers from their think (`officer.scr:1660+` -> `actor.cpp:8608-8626`).
6. `disguiseHandler` unable to restart after any alarm (`aihandler.scr:1003-1007`; the flag is assigned once and cleared nowhere).
7. `coop_papersAnytime` never restarting after a post-LOUD death (`itemhandler.scr:768` gates on a flag that is never cleared).
8. `coop_armOnBlown` arming downed players and wiping their DBNO restore source (`itemhandler.scr:1405`, `:1460` -> `dbno.scr:729`).
9. The armory-skin re-force overwriting the disguise uniform (`player.scr:1097-1159`).
10. `coop_officer_wait_goloud`'s 600s bound silently cancelling all officer waves on a long run.
11. **`level.ai_alarm_backup_total` is never decremented on the despawn path** (`global/alarm_system.scr:932-933` is a bare `self remove`; the only decrement is `:351`, behind `self waittill death` at `:349`), so after one alarm cycle whose backups walk out of sight the counter is pinned at `ai_alarm_backup_max` and every later alarm spawns zero reinforcements, silently. Shared code; affects every alarm map.
12. **`ai_alarm_alerted_bumpstack` decrements `level.ai_alerted_index` with no floor** (`global/alarm_system.scr:464`), so any external zeroing while a runner is in flight wedges `ai_gofor_alarm` in a permanent `wait 3` loop and no AI can ring the alarm again for the rest of the map.
13. **`maps/m2l2a.scr::weldinginterupt`'s re-entry guard is dead** - it tests `self.inturpupted` at `:1255` and sets `self.interupted` at `:1259`, two different spellings. `cower` (`:1214-1223`) has no guard at all and ends in a raw `self attackplayer` at `:1222`.
14. **`coop_mod/wounded.scr`'s retreat paths rewrite scene actors**: `coop_checkTacticalRetreat` sets `enableEnemy = 0` at `:206` and `attackplayer` at `:219`, `coop_checkWoundedRetreat` the same at `:300` / `:336`, with no scene / `alarmthread` / `type_disguise` exclusion, on a pain streak that fires at full health.
15. **`coop_prone_shooter`'s shipped `^~^~^ PRONEDBG` print** (`officer.scr:1736`) sits above the weapongroup whitelist reject at `:1740-1744`, so it fires for actors that never pose, and carries no actor identifier.
16. Whatever TP-0's instrumentation actually reveals.

Update bug-1640 with a `superseded_by` / progress field when B1 lands. Extend the schema with **fields**, never prose.

**Authored docs**, routed per the OpenWolf table and merged into existing entries rather than appended:

| Content | Destination |
|---|---|
| Room tests cannot gate per-target actions; one-way latches (`attackplayer`) are not everyday verbs; hooks stranded below early exits; a config seed in two files is really a seed in five, and a homepath copy shadows the basepath one; **`group` is per-ScriptClass and is NOT shared by a file-qualified call NOR by an entity-prefixed same-file call - only by an unprefixed same-file `thread label`**; **`thinkstate == "attack"` is not evidence of hostility**; **a property assignment on a multi-entity targetname throws**; **Script Errors do not kill threads**; **omitted script arguments arrive NIL - there is no default-argument mechanism**; **an engine flag a disguise pins to a fixed point cannot be used to detect that the disguise failed** (the `is_disguised` / threat / veto circularity); **a debug marker name is an API - grep before you mint one**; **cite ledger ids you have grepped for** | `docs/TRAPS.md` (merge into the existing disguise and parse-killer entries) |
| The holstered-arming pivot; the two-axis state machine; delete-vs-defer for the freeze arm; one aggro helper with a per-caller NIL policy; remove-vs-hide for world pickups; **suppressing vanilla's alarm re-ring cycle to make D1 meaningful**; **weapons one-way / disguise reversible** | `docs/DECISIONS.md` |
| D1 / D2 / D3 as confirmed user decisions, and any correction arising from the playtests | `docs/21-user-preferences.md` |
| The shipped stealth director and its status flips | `docs/FEATURES.md` + one line in `docs/HISTORY.md` |
| Outstanding 2P+ stages (TP-3, TP-4, TP-7, TP-9) and anything awaiting playtest | `docs/OPEN.md` |
| Mark v1 superseded | `docs/proposals/m2l2a_stealth_master_plan.md` header |

Respect the size ceilings printed by `python docs/tools/docgen.py check`. Prune before adding.

---

## 14. User decisions - CONFIRMED

All three of v2's open decisions have been answered. None is open.

### D1 - Recoverable alarm: **CONFIRMED RECOVERABLE**

Silencing an alarm restores the disguise. Implemented per P5 and section 4.4, as a **separate reversible axis** from the one-way weapons phase:

- `takeAllDisguises` gains `reason` + `permanent` parameters, **both NIL-defaulted inside the label**, and derives `draw` there too; on a stealth-director map with the alarm up it resolves `permanent = 0`, which suspends rather than confiscates (Step 21a). `global/alarm_system.scr:704` is **not** edited; the three non-alarm callers are, and e1l4's point of no return is byte-identical in behaviour.
- `stealth.scr::alarmWatcher` **mirrors** `level.alarm` every 0.25 s (it is the sole writer of `level.coop_disgSuspended`) and fires `onAlarmDoused` on the 1 -> 0 edge, with a value-based self-heal for an edge that completes inside one tick: alerted-queue clear (`NULL`, no mutex write, with an index floor added in `alarm_system.scr`) + re-arm cooldown **with a named reader in `alarm_switch_thread`**, `restoreDisguises`, `disguiseHandler` restart **without force-clearing the ownership flag**, E5, then the `THINK_ALARM` restore last, player-facing message (Steps 21, 22).
- Engine E5 clears `m_bForceAttackPlayer` across all actors on the same edge (Step 23) via a **scoped `unforceattackplayer` actor event called from `onAlarmDoused`** - not from `Level::SetAlarm`, which fires on ten unrelated scripted writes - with an `IsSubclassOfActor` guard and an SP exclusion. Without it every guard latched during the loud window stays disguise-blind and the recovery is cosmetic. E5 also exposes the `forceattackplayer` getter that T5 depends on.
- **Weapons are not un-issued, and the squad is not force-holstered.** Once you have your kit you keep it; **holstering is the recovery action the player takes.** Round 3 removed `deactivatePlayerWeapon` from `restoreDisguises`: it contradicted P4, P5 and TP-10's own staging, and disarmed the squad mid-firefight.
- **Recovery is per-actor and gated on line of sight**, not on a timer (P5). This is surfaced in-game and tested by TP-10.
- **Accepted deviations from vanilla, both deliberate and both recorded in `docs/DECISIONS.md`:** the alerted-queue clear and cooldown (Step 22a) suppress vanilla's immediate re-ring; and the per-guard `coop_paperPass` latch is deliberately **not** reset, so a guard who already waved the squad through stays satisfied across an alarm cycle (Step 21f).

### D2 - Officer waves only on `reason == "alarm"`: **CONFIRMED - and already shipped**

No code change is required. `coop_mod/officer.scr::coop_officer_wait_goloud` already returns 1 on `level.alarm == 1` (`:121`) and on nothing else that a non-alarm LOUD sets, and `global/alarm_system.scr:700` sets `level.alarm = 1` before the `takeAllDisguises` thread at `:704`. v2's proposed clause was unreachable. What IS required is (a) a negative assertion in TP-2 that no officer-wave markers appear on a non-alarm LOUD, and (b) the 600-second-bound fix in Step 14, which is a real defect on long stealth runs.

### D3 - DBNO during QUIET stays empty-handed: **CONFIRMED**

No downed pistol during the stealth window. Accepted consequence: higher bleedout odds while unarmed. Two related fixes are still required and are in Step 11 and Step 18: a downed player must not be armed by `coop_armOnBlown` (it wipes his DBNO restore source), and he must be armed **on revive** if the LOUD happened while he was down; and his papers must survive the DBNO `takeall`.

### Still genuinely open (non-blocking, decide during Phase C)

- Whether Step 22b (restoring `THINK_ALARM` on the douse edge, so a **second** alarm still produces the welder / cower / scientist reactions) lands in the first Phase C commit or is deferred with the one-shot limitation documented. Both are acceptable; the fallback is stated, not silent.
- Whether `maps/m2l2a.scr:832-834`'s second `coop_stealthStripWeapons` call is folded into `init`'s sweep or kept as a belt-and-braces second pass (Step 14).

---

## 15. Vetting round 2

### 15.1 What was attacked, and how

v2 was re-vetted in full against the working tree - mod (`hzm-mohaa-coop-mod`), engine (`openmohaa-hzm`), the ledger (`.wolf/buglog.json`, bug-1600..1640 plus the `failed_attempts` on bug-1631 / bug-1632), the six research JSONs and three designs under `docs/proposals/m2l2a_v2_research/`, `docs/TRAPS.md`, and the retail data in `G:\GOG\...\main\Pak*.pk3`. **No line number, quoted snippet or assertion in v2 was trusted; every one was treated as a hypothesis and opened.** Seven independent review lenses plus a dedicated engine lens were run, and every finding was then adjudicated against source a second time before being accepted.

The brief was: what would make this plan fail to compile, fail to run, break axis AI, break a scripted scene, violate one of the seven binding expectations, regress another map or a shipped feature, be unimplementable as written, or be internally inconsistent.

**93 findings were raised. 90 survived adjudication (16 blocker entries covering 6 distinct blocking defects, 38 major, 36 minor). 3 were refuted outright and are recorded in 15.4 so they are not re-raised.** Many of the 90 are duplicates across lenses; the distinct-defect count is roughly 55.

### 15.2 Confirmed findings by severity

**Counts: 16 blocker entries / 6 distinct blocking defects; 38 major; 36 minor.**

#### Blockers (all resolved in this document)

| # | Defect | Evidence | Where fixed |
|---|---|---|---|
| **B-1** | **Fail-open on a NIL aggro target deletes three shipped stand-downs on every disguise map.** Three of `coop_stealthBlocksAggro`'s four callers pass NIL - replica spawn (`aihandler.scr:274`), search sweep (`aisquad.scr:139`), berserk (`morale.scr:71`); only `aisquad.scr:114` passes a target. The NIL walk at `:1213-1222` is the only thing standing them down. The in-code measurement v2 cited as licence (`AGGRO BLOCKED aisquad-goloud`) comes from `aisquad.scr:115`, i.e. the surviving per-target gate. Blast radius is e1l4 and m2l2b too. Step 0's kill switch did not cover it. Recreates the recorded "two card players stood up from the table" failure (`aisquad.scr:109-113`, `morale.scr:69-70`). Raised by four lenses independently (L1-01, L3-01, L5-01, L6-03). | `aihandler.scr:1184`, `:1213-1222`, `:274`; `aisquad.scr:114/139`; `morale.scr:71`; `actor.cpp:9336-9339`; `actor.h:2159-2167` | P2, Step 0, Step 3 item 3, section 9 |
| **B-2** | **D1 (recoverable alarm) is not implementable as v2 is written**, in four places at once, and four separate latches block it: `takeAllDisguises` destroys `has_disguise` / `coop_enableDisguises` / `coop_uniformOnSpawn` with no inverse anywhere (`itemhandler.scr:1141-1152`); `coop_armOnBlown` is a one-shot (`:1395-1396`); `disguiseHandler` can never restart (`aihandler.scr:1003-1007`, flag assigned once, cleared nowhere); and the engine's `m_bForceAttackPlayer` is cleared only in the Actor constructor (`actor.cpp:3092`, `:9339`). The alarm-off branch (`alarm_system.scr:717-729`) has no coop hook. Seven finding entries (L1-04, L3-07, L7-01, L6-01, L5-02, L4-02, E-04). | as cited | Section 1 (two axes), P5, section 4.1 / 4.4, Steps 21, 22, 23, section 14 D1 |
| **B-3** | **T5's stated premise is false in source.** v2: "the engine cannot enter ATTACK against a disguised player". `State_Disguise_Halt` sets `THINKSTATE_ATTACK` 1500ms after entry with **no disguise test**, and HALT is entered from PAPERS purely on >256u to the current enemy; `State_Disguise_Enemy` does the same at 3000ms. Separately, `type_attack "alarm"` maps ATTACK to `THINK_ALARM`, so all **13** `$ai_alarm` actors on m2l2a sit in thinkstate "attack" with a player enemy during QUIET. T5 as specified fires on all of them, making TP-2b - the declared keystone - structurally unreachable. v2 is also self-contradictory: section 4.2 calls HALT "routine 4-player geometry" and declines to hook it, then routes it into a one-way LOUD via T5. (L3-02, L7-02.) | `actor_disguise_common.cpp:96-110`, `:136-157`; `actor.cpp:8049-8051`; `actor_alarm.cpp:36-71`; `alarm_system.scr:336-337`, `:371-372`; `map_entities/m2l2a_entities.txt` | Section 4.2 (seven-condition predicate), Step 13 |
| **B-4** | **`group` does not cross a file-qualified thread call.** `group` IS the ScriptClass; a bare same-file `thread label` shares it, a `file::label` call allocates a new empty one. Step 12's "set `group.player` then call `giveWeaponLoadout` cross-file from `manageAliveSpawning`" writes `player.scr`'s group and is invisible to the fresh ScriptClass; `group.player` arrives NIL and the epoch re-give hands out nothing. (L4-01, L1-03.) | `scriptvm.cpp:1465-1467`, `:1661-1663`; `scriptclass.cpp:197-201` vs `:211-216`; `scriptmaster.cpp:694-698`; `itemhandler.scr:697`, `:1430` | Step 12 (`coop_armOnePlayer`), Step 13 discipline, section 2.1 |
| **B-5** | **No step called `stealth.scr::init`.** Step 14's wiring table had seven rows, none of them the init call; `maps/m2l2a.scr:38-42` still armed the trio inline; Step 17 only flipped cvar seeds. Silent failure: the map still plays unarmed, but the phase stays NIL, `goLoud` returns on every transition, no watchdog, no scene tags, no MP40 sweep, and no `^~^~^ST BOOT` - which section 8.1 makes a mandatory proof-of-load and five stages grep for. (L7-03, L1-09.) | plan Steps 13/14/17 vs `maps/m2l2a.scr:36-42`, `:832-834` | Step 14 (first two rows), lesson 15 |
| **B-6** | **`coop_apply_personality` is the dominant scene-actor writer, and v2 never mentions it.** It runs on every german under `coop_aiDynamic 1` (seeded on), exempts only machinegunners, and ~12% of the time sets `enableEnemy = 0` plus a looped `anim_scripted` prone pose - which `actor.cpp:8608-8626` turns into a forced IDLE and `SetEnemy(NULL)` **even from a DISGUISE think**, so a proned papers checker can never be shown papers. ~60% of other rolls overwrite `type_attack "alarm"`. v2's Step 4 target (the hurt-trooper branch) is gated on `coop_personality_set`, i.e. only fires on actors this same system already tagged. The looped `anim_scripted` is also a far better fit for bug-1631 F3 than the canteen anim. (L3-03.) | `aihandler.scr:109-111`, `:26`, `:424`; `autoexec.cfg:580`; `officer.scr:1660+`; `replace.scr:396-399`; `actor.cpp:8608-8626` | Step 4 (Writer 1), lesson 8 |

#### Major (38 entries) - grouped by where they landed

- **Engine correctness (7):** unguarded re-stamp at the top of `SetEnemy` would be a hard crash - must go inside `if (m_Enemy)` (E-01, Step 8). `ForceAttackPlayer` hardcodes `G_GetEntity(0)` so Step 6 item 1 alone cannot pass TP-7 (E-02, L7-08, Step 6 item 2). Skipping `BecomeTurretGuy` alone is insufficient - the latch is in `ForceAttackPlayer` (E-03, Step 6 item 3). `EquipWeapons` runs before any script and can bust a checker with no path back (E-06, Step 6b). Parity 0 leaves `m_bIsDisguised` frozen **TRUE**, not merely stale (E-09, section 11). Two more NULL-crash sites at `actor_grenade.cpp:348/440` plus `AddPotentialEnemy` (E-10, Step 5). E3's re-stamp fixes the wrong half and introduces a new discard; and the distance measurement bug is untouched (E-05, L1-11, Step 8a/8b).
- **D1 mechanics (6):** `disguiseHandler` cannot restart (L6-07, Step 21d). The alerted queue re-rings a doused alarm within seconds (L6-05, Step 22a). `State_Alarm_Idle` makes scene alarmthreads one-shot (L6-06, Step 22b). Per-actor recovery is gated on line of sight, not a 10s timer (L6-04, P5 / TP-10). Recovery must not route through `giveDisguiseToAll`, whose `setEnemyAttackStates` issues a raw `attackplayer` (L6-02, Step 21c). Reason and draw latch to the first LOUD, so an alarm after a non-alarm LOUD draws nobody (L1-05, section 4.3 `notifyLoud`).
- **Arming and lifecycle (8):** `giveWeaponLoadout`'s `has_disguise` branch omits `coop_backfillPrimaries` and `spawnWeaponAssert`, so every post-LOUD kit is short a primary (L4-03). `coop_armOnBlown` arms downed players and wipes their DBNO restore source (L4-07). `coop_papersAnytime` never restarts after a post-LOUD death (L4-04) and eats the fire button when holstered (L7-09). The uniform pair must be duplicated, never moved (L4-06, L5-04). The armory-skin re-force stomps the disguise model (L4-05). m2l2a pre-sets `coop_enableDisguises` at load, so players are engine-disguised before the uniform exists (L4-08).
- **Aggro-site inventory (5):** `global/wrenching.scr:80` is a live m2l2a aggro path v2 missed, while `global/welder.scr` is not on this map at all (L1-02). Twelve raw `attackplayer` sites in `m2l2a.scr`, not two (L3-04). `wounded.scr:219/336` have no player in scope; `aimaneuver.scr:150` has no `attackplayer`; the `setEnemyAttackStates` gate reads a field already NULLed (L5-03). The per-target rule has no phase term, so a holstered post-LOUD player is deferred to again - resolved as intended behaviour under D1 rather than a bug (L3-05, L5-05, section 7 row 7).
- **Scene protection (3):** `$suckyfatty` is three entities and a scalar assignment throws; the tag list uses names that do not exist (L3-08, L5-09). The Step 4 `alarmthread` print would throw and emit nothing for exactly the actors it exists to identify (L1-07).
- **Test-harness validity (4):** the named log path is a week stale and is not the one the live profile writes (L7-05). The start recipe is inverted and never sets `ui_dmmap` (L7-07). Spawn-protection is an 8-second window and must not gate detection (L1-08, L5-06). `NIL + 1` throws, so the arm epoch is never written (L1-06).
- **Officer waves (1):** the 600-second bound silently cancels all waves on a long stealth run (L6-10).
- **Structure (4):** Steps 18/19/20 were orphaned with no phase or commit id, and TP-R cited them while running only before they existed (L7-10); the officer clause is dead code (L1-13 and three duplicates, counted under minor); the arming recipe was prescribed two different ways in two steps (L1-12); `giveDisguiseToAll` is inert on m2l2a so section 7's expectation-2 row named dead code (L7-14).

#### Minor (36 entries)

Dead officer clause (4 duplicate entries), verifier tool paths in `scratchpad/` instead of `docs/tools/` (3 duplicates), non-existent ledger ids `bug-1605/1607/1609` (1), aihandler anchor drift of 4-8 lines on three rows (1), the stranded statements in `disguise_deny.scr` / `disguise_enemy.scr` (1), the unbraced `if` at `m2l2a.scr:269` (1), the Norway guards having no `self.enemy` to test (1), the `type_attack` provenance test being unwritable (1), TP-R's second map unable to exercise the alarm heuristic (1), the trio clear depending on `coop_armOnBlown`'s latch (1), the holster hint being the D1 recovery cue rather than a lie (1), `takeAllDisguises`'s reason hard-coded for three non-alarm callers (1), the unguarded actor-array walk in `anyEnemiesInAttackState` (1), the orphaned replica-cloning "decision" whose premise is false (2), the missing rcon / marker-parsing loop against a recorded user preference (1), the missing `Script Error` baseline allowlist (1), Step 16 bullet 1 being a no-op below `takeall` (1), the giveWeaponLoadout 0.25s armed window (1), `attackentity`'s advisory semantics and the unguarded `favoriteenemy` (1), reason-vs-alarm flag separation (1), `CVAR_LATCH` registration site (1), E1 subsuming B0 on the same lines (1), `Resume_Disguise*` also re-stamping the papers time (1), the E4 originator branch being dead code (1), Step 15's non-existent classname fallback and missing recipe (counted major under L7-04; the recipe note is minor), bug-1621 cited as a live confounder when its fix has landed (1), and Step 14's T1 preamble placement relative to Step 2's new predicate (1).

Every one is folded into the step it affects. None was deferred.

### 15.3 What round 2 confirmed as sound

Recorded so the next pass does not re-litigate it:

- The bug-1638 parity diagnosis and its consequences. `player.cpp:5482-5497` is exactly as v2 describes.
- P4 (holstered arming) as the correct shape for a local bust, and the reasoning behind it.
- The B0 NULL-guard finding (extended to three sites, not reduced).
- The six-anim-gate inventory, the `disguise_accept.scr` structural problem, and the "room tests cannot gate per-target actions" principle.
- `IsTeamMate` + parity already implementing draft E2, and bug-1640's residual being the real work.
- `coop_armOnBlown`'s latch being atomic (v2's correction of the draft was right).
- The uniform-below-the-early-exit defect, the papers2 swap defect, and the DBNO papers gap.
- `State_Disguise_Accept` already demoting an accepting sentry, making the `type_disguise "none"` swap redundant - Step 1 is correct as written.
- The "prove the artifact before trusting the log" discipline (only the log path itself was wrong).

### 15.4 Refuted - do not re-raise

| Claim | Why it is wrong |
|---|---|
| **"`if ($suckyfatty != NULL)` throws when the targetname does not exist, so existence guards are unsafe."** | `OP_UN_TARGETNAME` only throws when `*m_PrevCodePos` is in the equality/boolean opcode ranges (`scriptvm.cpp:1794-1812`). `m_PrevCodePos` is assigned at the TOP of the execution loop (`:1080`) before the dispatch fetch (`:1104`), so during `OP_UN_TARGETNAME` it IS `OP_UN_TARGETNAME` - and the enum (`scriptopcodes.h:158-181`) places that opcode strictly between the two ranges. The ScriptError is unreachable. **The existence-guard idiom in Step 13 is safe.** (Resolve scene actors into level vars anyway - but for the container reason of B-4/L3-08, not this one.) |
| **"A thread handle used as a condition is unconditionally truthy (bug-1609), so `thread <label>` in a value context never returns the label's result."** | Listener registers both an EV_NORMAL and an EV_RETURN `thread` event (`listener.cpp:121`, `:131`); `CreateReturnThread` (`:4233-4242`) allocates a return pointer, runs the thread synchronously, and `ScriptVM::End` writes through it (`scriptvm.cpp:989-994`, `:558-560`). A label that completes without yielding returns its `end (value)` correctly - which is why the e1l3 / e1l4 disguise flow works today. **And `bug-1609` does not exist in the ledger** (the id sequence runs 1604, 1606, 1608, 1610...; 1605 and 1607 are also absent). v2 built the section 9 retirement rationale and part of Step 2's scope on it. Removed. Do not add `itemhandler.scr:956/1002/1028` to any sweep on this basis. |
| **"There is no entnum-to-entity resolver in this dialect, so Step 11's entnum snapshot is unimplementable."** | `getentbyentnum` exists and is used in shipped mod code for exactly this: `coop_mod/wounded.scr:260-262` sweeps `int( getcvar "maxentities" )`. Thread-local entity references are preferred (Step 11) for other reasons, but the entnum recipe is available and Step 15 relies on it. |

Three further sub-claims were refuted **inside** otherwise-confirmed findings and are recorded here because they would otherwise mislead:

- **"A Script Error aborts the event and the thread."** It does not. The try/catch is inside the per-opcode loop and `HandleScriptException` returns without rethrowing (`scriptvm.cpp:1881-1883`, `:1915-1935`). The real cost is a silently skipped statement plus log noise - which is worse for attribution, and is why TP-BASE exists.
- **"e1l3 would lose its uniform give if the pair were moved."** e1l3 never sets `level.coop_enableDisguises` and is papers-only; the maps at risk are e1l4 and m2l2b.
- **"Replica cloning is suppressed during QUIET, disabling enemy-count scaling for the map's main force."** It is not. `aihandler.scr:264-278` spawns, equips, leashes and `forceactivate`s the clone unconditionally; only `local.r attackplayer` at `:277` is gated, and the in-code comment says so.

### 15.5 Residual risk accepted

1. **Second-alarm scene reactions.** If Step 22b is deferred, welder / cower / scientist alarm reactions are one-shot per map, because `State_Alarm_Idle` overwrites `THINK_ALARM` permanently. Expectation 7 is then guaranteed only for the FIRST alarm. Documented, not silent.
2. **Per-actor D1 recovery latency.** A guard who currently sees you keeps hunting until he loses line of sight, even after a douse and even with E5. This is engine structure (`actor.h:2159-2172`, `actorenemy.cpp:420-423`), not a script bug. Surfaced in-game and measured by TP-10.
3. **The twelve raw `attackplayer` sites inside `maps/m2l2a.scr` stay vanilla-latching.** Converting them is out of scope; E5 is what makes them survivable across a D1 recovery. If E5 is ever rolled back, those actors become permanently disguise-blind after any loud window.
4. **Deliberate deviation from vanilla in Step 22a.** Suppressing the alerted-queue re-ring for a cooldown window is not retail behaviour. It is required for D1 to be meaningful and is recorded in `docs/DECISIONS.md`.
5. **`attackentity`'s stale-verdict residual.** `m_bEnemyIsDisguised` is **refreshed every tick the enemy is visible** (`actor.cpp:4033`) and cleared by `ConfirmEnemy` (`actorenemy.cpp:501` / `:528`), so the stale window exists **only while the actor cannot see the target** - narrower than v2.1 claimed ("only recomputed in `Actor::SetEnemy`", which is false). Strictly better than `attackplayer`'s permanent latch.
6. **Pre-uniform disguise on m2l2a.** `maps/m2l2a.scr:27` sets `coop_enableDisguises` at load, so an empty-handed player is engine-disguised before he owns a uniform. Sentries still challenge him (he is a valid challenge candidate); they simply will not attack an undressed GI. This leg is deliberately non-vanilla; the alternative - moving the seed to the uniform pickup - is available and is noted in Step 10's scope note if a playtest finds it jarring.
7. **All 2P+ evidence is outstanding.** TP-3, TP-4, TP-7, TP-9 and the multiplayer half of TP-10 cannot be run solo. B2 and B3 land with those stages marked outstanding in `docs/OPEN.md`, never claimed as passed.
8. **bug-1636 / 1637 (the card-manager shim) is itself PENDING PLAYTEST** and lands in the same window as Step 4. TP-0 must state which of the two it is attributing.

---

## 15A. Vetting round 3

### 15A.1 What was attacked, and how

Round 3 targeted **the round-2 amendment itself**, on the reasoning that it grew the document from 654 to 1164 lines and had never been adversarially reviewed. The declared high-risk surface was: Steps 21, 22 and 23 (the recoverable-alarm machinery - `takeAllDisguises`'s new parameters, `alarmWatcher`'s edge detector, `restoreDisguises`, the `disguiseHandler` re-thread, the alerted-queue clear and cooldown, the `type_attack "alarm"` re-issue, and engine E5); the two-axis model; the re-derived seven-condition T5; the restructured Step 4 with its two writers; the new Step 6b; the Step 12 rewrite; Step 14's init wiring rows; and the per-caller `failOpenOnNil` argument.

Method was the same as round 2 and deliberately harsher: **no line number, quoted snippet or assertion in v2.1 was trusted**, including the ones round 2 had itself "corrected". Six review lenses were run over the plan, the mod tree, the engine tree, `.wolf/buglog.json` (bug-1600..1640), the research JSONs, `docs/TRAPS.md`, `build.ps1`, the deployed artifacts in `G:\mohaa-gl2\` and the GOG root, the live `qconsole.log`, and the retail scripts in `G:\GOG\...\main\Pak*.pk3`. Every finding was then adjudicated a second time against source before acceptance.

**Round 3 raised 87 findings. 84 survived adjudication (4 blocker entries covering 2 distinct blocking defects, 32 major, 48 minor); 14 of the survivors were PARTIAL, i.e. the mechanism was real but the stated failure scenario was wrong and has been corrected here rather than propagated; 3 were refuted outright.** 15A.4 records the refuted findings **and** the refuted sub-claims that sat inside otherwise-confirmed ones, because the latter would mislead just as effectively.

Note the shape of the result: round 2's 6 distinct blockers came down to 2 in round 3, and **both round-3 blockers were introduced BY the round-2 amendment.** That is the expected signature of a rewrite that has not itself been reviewed, and it is the reason this round was worth running.

### 15A.2 The two blockers, and how they are resolved

| # | Defect | Evidence | Resolution in this document |
|---|---|---|---|
| **R3-B1** | **`coop_armAllOnBlown`'s retained guard reads a flag `goLoud` cleared four statements earlier, so NOBODY is ever armed - on the first LOUD of every run, solo included, silently.** `itemhandler.scr:1394-1396` is `coop_armOnBlown:{ / if( level.coop_startUnarmed != 1 ){ end } / level.coop_startUnarmed = 0` - one atomic check-then-set pair. Section 4.3 moved the clear up into `goLoud` (line 299) and then called the arm at line 304, while Step 11 and section 4.3's own notes said the `:1395` test "remains as the once-only guard for the giving loop". `^~^~^ST LOUD` is printed **before** the dead call, so the failure emits a success marker. Kills T1/T3/T4/T5/T6/T7 through `goLoud`, T2 through `notifyLoud`, and `notifyLoud`'s already-loud branch. Expectations 4 and 5 fail outright; TP-2, TP-6, TP-8 and TP-8b become unreachable. Raised independently by two lenses (L3-01, L5-01). | `itemhandler.scr:1394-1396`; plan section 4.3, Step 11, Step 21e | **Section 4.3** now specifies an independent `level.coop_armAllDone` latch written before the first yield, and **deletes the `coop_startUnarmed` test from the arming label entirely**. Step 11 restates it, and Step 21e's stale "atomic one-shot" rationale is rewritten to stand on P5 alone. `coop_armOnePlayer` carries no trio test either, or the epoch re-give would die the same way |
| **R3-B2** | **`stealth.scr::init` cannot tag scene actors, because at its wiring point nothing it needs exists yet.** Step 14 wires `init` at `maps/m2l2a.scr:38-42`; `thread global/alarm_system.scr::alarm_system_setup` is at `:123` and is the only path to the sole writer of `self.alarmthread` (`global/alarm_system.scr:336-337`), and the ten `find_guy` scene level-vars are assigned at `:124-135`. So at `:38` **no actor has an alarmthread and all ten level vars are NIL** - the drift-proof `alarmthread` derivation tags nothing and every named scene actor resolves to NIL. Silent AND unfalsifiable: `^~^~^ST BOOT` still prints, the map still plays unarmed, every 8.1 proof-of-load criterion passes, and TP-0b's criterion ("zero prone markers on the tagged set") passes **vacuously** on an empty set. The exemption then matches roughly half its intended set, including the `$ai_alarm` actors whose `type_attack "alarm"` is overwritten by `coop_apply_personality`'s ~60% cover roll - against expectation 6. Same class as round 2's B-5. Raised independently by two lenses (L1-A02, L4-B5-01). | `maps/m2l2a.scr:38-42`, `:73`, `:123`, `:124-135`; `global/alarm_system.scr:336-337`; `aihandler.scr:109-111`; `officer.scr:1675-1677` | **`init` is split.** `init` keeps the single-frame work at `:38-42`; a new **`initScene`** carries the tagging and `protectScene` and is called after `:135` and before `:163` (new row in Step 14's table). Two hardenings because the ordering against `coop_apply_personality` is not otherwise provable: the exemption is re-checked inside `coop_prone_shooter` (which yields) and `type_attack` restored for a late tag, and **TP-0b now asserts the tag COUNT** via a new `^~^~^ST TAGGED n=` marker, not merely the absence of another marker |

### 15A.3 Confirmed findings by severity

**Counts: 4 blocker entries / 2 distinct blocking defects; 32 major; 48 minor. 14 of the 84 were PARTIAL.**

#### Major (32) - grouped by where they landed

- **The recoverable-alarm machinery, i.e. the round-2 amendment's core (10).** `takeAllDisguises`'s contract was self-contradictory in three places at once - 21a's heading said no caller changes, its table required an edited conditional at `alarm_system.scr:704`, and 21b said the file is not edited; honouring the last one silently kills D1 (L1-A04, L2-M4, L3-03 -> Step 21a rewritten, conditional moved inside the label, NIL defaults made explicit, `^~^~^ST FAULT` assertion added). `draw` was never bound at the `takeAllDisguises` -> `notifyLoud` hop (L3-02, L2-M5 -> derived in 21a, section 7 row 5 corrected). `restoreDisguises`'s forced `deactivatePlayerWeapon` contradicted P4, P5 and TP-10's own staging and disarmed the squad mid-firefight (L5-06, L6-07, L2-m1 -> deleted). `disguiseHandler`'s ownership flag was described two contradictory ways and the force-clear duplicates the loop on any sub-1s alarm cycle (L2-M1 -> 21d rewritten). `itemhandler.scr:757-759`'s per-spawn disguise re-grant fires all through an alarm and re-latches every german via `setEnemyAttackStates`, undoing E5 (L5-04 -> new 21c-bis). The alarm-suspended respawn takes the holster branch and comes back unarmed-looking (L5-02 -> Step 11 tail predicate). `weaponstate.scr:75`'s fired-while-disguised branch stays live for the whole loud firefight (L5-11 -> added to Step 3). `alarmWatcher`'s edge-only detector can permanently latch the axis (L5-07, L2-M3 -> mirror + self-heal).
- **The alarm subsystem it reaches into (5).** `ai_alarm_alerted_bumpstack` has no index floor, so zeroing the index from outside can wedge `ai_gofor_alarm` permanently and no AI can ring the alarm again for the rest of the map (L2-B2 -> Step 22a item 3). The re-arm cooldown had **no reader** anywhere (L1-A05, L2-B3, L6-09, L4-B2-01, L5-08 -> reader named in `alarm_switch_thread`, `^~^~^ST REARM blocked` added, 21b's no-edit claim narrowed to the OFF branch, `global/alarm_system.scr` added to 8.4). 22b's `type_attack "alarm"` re-issue re-fires the queue **pusher** on the douse edge and yanks surviving actors out of combat (L2-B1, L6-08 -> `$ai_alarm` excluded, ordering fixed, deferral made the recommended default). The two m2l2a scene alarmthreads are non-idempotent and one's re-entry guard is dead on a spelling (L2-M2 -> constraint 3). `ai_alarm_backup_total` is never decremented on despawn, so the second alarm has no reinforcements (L2-M8 -> new 22a-bis).
- **Engine (3).** E5's hook was offered, not chosen, and the "natural" option fires on ten unrelated scripted `level.alarm` writes, has no old-value capture, and walks a `Sentient*` list as `Actor*` (L6-15, L2-M7, L2-M6 -> scoped `unforceattackplayer` event, subclass guard, SP exclusion). Step 6b named a gating cvar that does not exist anywhere in the engine tree (L6-03, L5-10, L3-07 -> `g_coopSpawnUnarmed` named, non-archived, reset at map load). T5's condition 4 was circular and unsatisfiable during QUIET (L4-B3-01 -> re-derived on a new `forceattackplayer` getter shipped by E5).
- **Scene-actor writers (2).** A **third** writer exists and Step 4 never mentioned it - `coop_mod/wounded.scr`'s two retreat paths, both defaults ON, triggering at full health on a 3-hit pain streak, writing `enableEnemy = 0` and raw `attackplayer` with no scene exclusion (L4-B6-01 -> Writer 3). Step 2's blast radius is wider than TP-R samples and is **not** behaviour-neutral off the disguise maps, because the replacement predicate drops the `cansee` term (L6-13 -> TP-R third axis).
- **Test-harness validity (5).** The `grep -qa g_coopDisgParity` proof-of-load already passes on **both current pre-change binaries** and was the only dll-side check (L6-01 -> SHA256 primary, per-change token secondary). `build.ps1` ships engine binaries on every run with no gate, so Phase A script commits can carry unintended B-phase dlls (L6-06 -> `-ScriptOnly`). rcon is unavailable before a map loads, and `coop_aggroDebug` / `g_coopDisgDebug` are seeded nowhere, so four markers never print and absent markers read as PASS (L6-04 -> cfg seeds, 8.1 item 3 restated). The A3 prone print collided with a shipped marker of the same name, in the wrong place, behind a cvar the preamble never sets - on the acceptance gate for round 2's blocker B-6 (L1-A07, L6-12 -> renamed `^~^~^ PRONEPOSE`, moved, re-gated). `officer.scr` emits no wave marker at all, so TP-2's D2 assertion was unmeasurable (L3-14, L6-11 -> positive markers added in Step 14).
- **Contract clarity (1).** The `coop_armOnePlayer` signature was specified two different ways in adjacent steps with nothing adjudicating - the exact class round 2 recorded as L1-12 and claimed fixed (L1-A08, L3-09 -> `self` form settled in Step 11, Step 13's hedge deleted, the cross-file rule restated correctly).

#### Minor (48)

Anchor corrections applied in place: `aihandler.scr:1102` -> `:1103` in three locations, with `:1102` explicitly preserved (L1-A01, L3-04); `actor.cpp` 9038/9042/9044 -> **9039/9045/9047**, restoring v2's original and withdrawing round 2's "correction" (L1-A03); `maps/m2l2a.scr:807-808` -> **`:808-809`**, likewise (L4-B5-02, L1-A13); `itemhandler.scr:700` -> `:702`, `:697` -> `:698`; `wrenching.scr:47` -> `:48`; `actorenemy.cpp:474` -> `:469`; `SetEnemy`'s assignment `:6903` -> `:6899` plus the unmentioned early return at `:6891-6893`; `officer.scr:118-129` -> `:118-128`; `listener.cpp:4233-4242` -> `:4234-4243`; `inventoryitem.cpp:80-83` -> `:81-84`; `g_local.h:489-491` -> `:490-491`; `g_mmove.cpp:97-98` -> `:97-99` plus `:105-107` and `:117-118`; `aihandler.scr:1227` -> `:1234` in section 11. Also: the fourth stranded statement at `disguise_accept.scr:18` (L1-A09, L3-11); Step 2's "replace `attackPlayer`" being self-referential; five `coop_stealthStart` seed sites, not two, three of them already out of sync in the autotest homepath (L4-B5-02); `coop_isDisguised` never restored by `restoreDisguises` (L4-B2-02, L5-12); `coop_uniformOnSpawn` blanket-set to true, dressing the squad for free on a pre-locker-room alarm (L5-05); `NIL` where the file's idiom is `NULL` (L6-17); `ai_alerted_isprocessing` being another thread's mutex (L2-m2); the `coop_disgTruth` accessor orphaned from every step (L3-05); `coop_stealthRecoverAlarm` named only in the rollback table and created by no step (L3-08); Step 0 having no commit id (L3-06); Step 6b missing from the phase index (L3-07); TP-1 scheduled after B0+B1 when its content lands in A1 (L3-13); `^~^~^ST BOOT` demanded as a hard fail on five stages that cannot emit it (L3-10); the `quietWatchdog` trio assert both exiting and not exiting at LOUD (L3-18); TP-9's grep unable to distinguish three outcomes (L3-15); TP-5's reconnect leg not solo-executable on a listen host (L6-10, DBNO half refuted); `qconsole.log` truncated at every launch, destroying the TP-BASE allowlist (L6-16); `coop_stealthArmOnHurt`'s retirement having no step or commit, and `itemhandler.scr:1381` being a second live caller of the renamed label (L3-19); the `type_disguise` exemption predicate unwritten, where the naive reading exempts 35 `"none"` actors (L6-14); the loose-MP40 model string never observed (L1-A11); the engine-binary backup ordered after the build that overwrites it (L6-05); the touched-file list omitting six edit targets (L1-A06, L6-02); `coop_isAttacking` kept as an OR-term on a subset of T5's conditions (L3-12); T1's preamble sitting below a multi-second yield (L3-20); the phase/commit/step counts in the executive summary (L3-17); the `group` rule missing its entity-prefixed half (L4-B4-01); `coop_disgAggroParity 0` described as gating only the NIL argument when it disables the whole gate (L4-B1-02).

Every one is folded into the step it affects. None was deferred.

### 15A.4 Refuted in round 3 - do not re-raise

| Claim | Why it is wrong |
|---|---|
| **"Retaining `m_bHasDisguise` through an alarm lets `m_bEnemyIsDisguised` mis-read a blown player as disguised, so an engine term must force it false under `level.m_bAlarm`."** | The mechanism is real (`actor.cpp:6906`, `actor.h:2159-2172`, `actor.cpp:8974-8986`) but the conclusion inverts expectation 7. The **retail** `global/alarm_system.scr` extracted from `G:\GOG\...\main\Pak0.pk3` contains **zero** references to `has_disguise` or any disguise strip - it only sets `level.alarm = 1`. The `takeAllDisguises` thread at HZM `:704` is a coop addition. So 21a's non-permanent mode **restores retail state exactly**, and whatever the flag does in it is by definition vanilla cover-blown behaviour. The proposed engine term would make coop **diverge** from retail. Do not add it. |
| **"`takeAllDisguises`'s `:1141` early exit on `!level.coop_enableDisguises` means a second alarm skips `notifyLoud`, so QUIET + SUSPENDED becomes reachable."** | Unreachable. Every writer of `level.coop_enableDisguises` was grepped: `itemhandler.scr:997` / `:1026` (true), `:1032` / `:1054` (false, both inside `giveDisguiseToAll`, which early-exits at `:996` whenever the flag is already true - so on m2l2a neither is reachable), `:1144` (false, permanent mode only), and `maps/e1l4.scr:23` / `m2l2a.scr:27` / `m2l2b.scr:15` (true). The only route to a false flag on m2l2a is a **permanent** `takeAllDisguises`, whose sole non-alarm trigger is `global/items.scr:471-478` on `remove_item "uniform"` - and m2l2a never removes the uniform. Under D1 the alarm passes `permanent = 0`. Section 4.1's "QUIET + SUSPENDED is unreachable" stands. |
| **"`restoreDisguises` not restoring `coop_isDisguised` lets `disguiseHandler` re-blow cover through the stale flag."** | The **fact** is right and the fix was applied anyway (21c now calls `setIsDisguised`), but this **failure path** is not the reason. Step 3 converts the `disguiseHandler` spotting test at `aihandler.scr:1021` from the mod flag to the engine flag **unconditionally**, in Phase A, which lands before Phase C - and `coop_disgAggroParity` does not gate that swap. Every other reader is a debug print (`:1051`), a dead watchdog (`itemhandler.scr:1315`, gated on `coop_startUnarmed == 1`) or a non-disguise-map path (`global/spotlight.scr:685`). Do not justify the `setIsDisguised` call with this scenario. |
| **"A non-Player killer can reach `attackPlayer` with a NIL target from `aihandler.scr:150`, so the funnel needs fail-open."** | `aihandler.scr:149` guards that call with `self.fact.attacker && self.fact.attacker.classname == "Player"`. Every other caller was enumerated: the six anim gates test `classname == "Player"` first, `:1024` passes a resolved player, `Artillery.scr:87` passes a real player. **Exactly one** NIL-capable route survives (`:1015`'s propagation of another actor's `.enemy`), and the shared NIL walk already handles it correctly. This was the stated justification for `failOpenOnNil`, which is now deleted. |

Two further sub-claims were refuted **inside** otherwise-confirmed findings:

- **"The papers swap is at `maps/m2l2a.scr:416-417`, not `:417-418`."** No - `:416` is `$papers2 remove`, `:417` is the `remove_item`, `:418` is the `add_item`. The plan was already right; the correction was itself off by one.
- **"The `getentbyentnum (NOT getentarray...)` in-code note is not at `wounded.scr:252`."** It is, exactly as cited.
- **"TP-5's DBNO revive legs are not solo-executable."** They are. `dbno.scr:35` grants `coop_medkits = 1` inside the per-spawn DBNO init, and that is a script flag untouched by `itemhandler.scr:708`'s `takeall`, so `dbno_selfrevive`'s `local.medkits < 1` test passes. Only the **reconnect** leg is blocked, and only because the solo tester is the listen host.

### 15A.5 Residual risk newly accepted in round 3

1. **The 0.25 s watcher loses a race it cannot win.** `ai_gofor_alarm_waitforalarm` polls at 0.1 s (`global/alarm_system.scr:658-660`) and captures the alerted stack into a **thread-local** at `:507`, beyond the reach of any later level-variable clear. So an in-flight ringer will re-ring once after a douse, absorbed by the 22a cooldown rather than prevented. The synchronous alternative - hooking `:728` directly - is available and is the documented fallback if TP-10 shows the cooldown is insufficient.
2. **Step 22b is now recommended for deferral in the first Phase C commit.** Constraints 1 and 3 (the `$ai_alarm` exclusion and the non-idempotent `cower` / `weldinginterupt` threads) make it the highest-risk item remaining in Phase C, and its fallback - one-shot alarm scene reactions, expectation 7 guaranteed for the first alarm only - is already documented.
3. **T5 depends on B3.** The re-derived predicate keys on a `forceattackplayer` getter that E5 ships. If B3 is rolled back, T5 is inert and expectation 4 rests on T1, T3, T4 and T7. T4 still catches a bust once the player is actually shot, so the mission stays winnable; the loss is the systematic backstop, not the mission.
4. **Step 2 changes behaviour on maps with no disguise.** Dropping the `cansee` term is not a no-op on `m1l2a`, `m5l3`, `m6l3a` and `M3L3`. TP-R's third axis exists to catch it, but it is a single solo pass on one or two of those maps, not a sweep.
5. **`^~^~^ E5 cleared=<n>` and the 30-second TP-10 bound are new and unvalidated.** They make the D1 contract measurable for the first time; the number itself is a starting estimate, not a measured one.
