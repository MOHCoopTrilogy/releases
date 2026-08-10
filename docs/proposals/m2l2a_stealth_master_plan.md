# m2l2a Coop Stealth — MASTER PLAN

Synthesized 2026-08-09 from the five research docs and three design proposals in
`docs/proposals/research_m2l2a/` (cited below as `01`..`05`, `E` = design_engine-first,
`S` = design_script-first, `V` = design_vanilla-fidelity). This plan supersedes all three
designs. It is written for a fresh implementation session with no memory of the saga.

**Ground rules for the implementer (read before touching anything):**

- Read `docs/TRAPS.md` and check `docs/generated/FIX_INDEX.md` for every file you touch.
  Read `.wolf/buglog.json` entries bug-1596..bug-1621 (this saga) before fixing anything.
- Mod tree is MOHAA script: CRLF, ASCII only, no em-dash, no bare negative in parens, no
  UTF-8 BOM. A single parse error silently kills the WHOLE file. Verify every touched
  `.scr` with `scratchpad/depthscan2.py` (raw brace counts lie; two opposite errors cancel).
- `main.scr::main` and everything before it must run in a single frame - no `wait`/`waitframe`.
  Plain `level.x = y` assignments before `waitthread coop_mod/main.scr::main` are legal.
- NIL != NULL: any negated test on a maybe-unset var must guard both. All phase gates in
  this plan therefore use POSITIVE tests only (`if (level.coop_stealthPhase == 1)`).
- Tag every change `[user 2026-08-XX]`. All existing session work is uncommitted working-tree
  state tagged `[user 2026-08-08]` / `[user 2026-08-09]`; the working tree ALSO carries
  ~5,250 lines of unrelated uncommitted work (m2l2b, coop_sr.urc, bunker, challenges...) -
  do not fold that into this change set (03 provenance caveat).
- `is_disguised` is EV_GETTER only. Script can never set the live flag; only the
  `changeGameType` window latches it. `attackplayer` = `m_bForceAttackPlayer`, a ONE-WAY
  latch cleared only in the Actor constructor (actor.cpp:9294 set / 3092 clear).
- Line numbers below are the working tree as of 2026-08-09 and WILL drift. Anchor by label
  name and the `[user 2026-08-0x]` tags, not by line.

---

## 1. How the mission actually works

### 1.1 The vanilla mechanism (retail SP)

The disguise is two flags and a timestamp on the Sentient plus two level globals:

- Every frame, **only in `g_gametype == GT_SINGLE_PLAYER`** (player.cpp:5477-5495), the
  engine recomputes `m_bIsDisguised`: true iff `m_bHasDisguise` AND alarm silent AND the
  active weapon is none-or-InventoryItem (papers) AND no actor is currently attacking this
  player. Weapon out = undisguised this frame; holster = disguised again. Retail never
  takes your weapons - "holstered (or papers in hand) = disguised" IS the stealth contract.
- `has_disguise` is set at map spawn (retail m2l2a.scr:35), before the uniform. The suit
  pickup (`likeynorway`) is cosmetics (player model swap) + objective + the papers item.
- Papers are `InventoryItem : public Weapon`. `toggleitem` raises them; primary fire plays
  `show_papers.skc` whose frame commands fire `activatepapers` ->
  `m_ShowPapersTime = level.inttime` (inventoryitem.cpp:81-84). An actor's challenge
  snapshots that timestamp at Begin and polls "was it re-stamped since" - the entire
  papers protocol is this per-player timestamp handshake, and it is already coop-correct.
- Actors gate everything on `EnemyIsDisguised()` (actor.h:2159-2174): the disguise bits
  AND NOT `m_bForceAttackPlayer` AND not already in ATTACK think. A disguised player is
  **retained as current enemy at zero threat** (actorenemy.cpp:446) - "has an enemy" is
  NOT "is fighting". Five `type_disguise` think types: `none` (never challenges, fully
  ignores), `salute` (34 of 51 actors; salutes, never checks), `sentry` (3; the ONLY real
  papers check - `level.m_iPapersLevel < m_iDisguiseLevel` at actor_disguise_common.cpp:74
  -> DENY, a non-hostile wave-off; else accept-thread + ACCEPT + permanent demote to
  salute), `officer` (2; Fake_Papers - showing ANY papers or waiting 12 s -> ENEMY ->
  ATTACK; no accept path; retail balance is "stay 256 / 64 units away"), `rover` (none here).
- Exactly ONE actor in the map needs level-2 papers: `sentry2dude`. His accept thread
  `sentry2accept` makes `$sentry2trigger` nottriggerable - one accept disarms the whole
  three-volume bust net for everyone. `goatsbutt` is the level-1 twin (`sentry1trigdisable`).
- Scripted busts are raw `attackplayer` in the map script at moments where cover is
  scripted-lost: sentry1 tripwires, sentry2 gate line/swim, the Naxos demolition (3
  scientists), killing a card player, `cower`/`scialarm`/`unholsterweapon`. `attackplayer`
  makes that actor permanently blind to the disguise (the one-way latch).
- The alarm is a **toggle**: any switch turns it on or OFF. While up, disguise is void and
  per-zone backups spawn (4 cap / 15 s). Doused, disguise resumes (in SP).
- The card game is one-shot by construction: the seated loop ejects on ANY per-frame
  thinkstate flicker, the first ejection cascades the table (`creator.broken`), the anim
  driver is deleted on stand, and there is NO re-seat path. Retail is stable only because
  a disguised solo player provably never causes a flicker (zero threat, no footstep
  notice, no misc AI events).
- Mission spine: spawn -> uniform+papers1 -> card room -> pens -> level-1 sentries ->
  `movetheflak` (crane, officer1 patrol starts) -> Naxos plant (scripted local bust,
  scientists only - outrun/kill them and stealth SURVIVES) -> papers2 pickup ->
  sentry2dude L2 accept -> `$endlevel` -> m2l2b. Note: the papers2/sentry2 gate comes
  AFTER the mandatory Naxos bust in the spine. Any design where the first bust ends
  stealth for the map breaks requirement 4.

### 1.2 The HZM layer (v1.2.x HEAD)

A three-layer sandwich (03 §1):

1. **Engine latch**: `main.scr::changeGameType` flips `g_gametype` to 0 for ~1 ms so the
   SP-only block runs once and sets `m_bIsDisguised = true`, then flips back. The flag is
   then FROZEN - in MP nothing engine-side ever clears it (not weapons, not alarm, not
   being shot). Every German's engine senses treat every player as a teammate full-time.
2. **Script mirror**: `weaponstate.scr` maintains `coop_isDisguised` per holster/unholster;
   `itemhandler.scr::setIsDisguised` is the single writer.
3. **Enforcement**: all detection re-implemented in script (`aihandler::disguiseHandler`
   1 Hz poll + cansee/hearing cascades + `[200]` inserts in `anim/disguise_*.scr`), whose
   only lever is `attackplayer` - the permanent latch.

### 1.3 Why they fight (the five frictions)

1. **The latch is one-way** but the mod used it as its everyday "react" primitive - and
   three raw call sites bypassed even the wrapper: count-scaling replicas born hostile,
   aisquad go-loud, morale berserk. One call = that actor is blind to the disguise forever.
2. **The frozen flag** means script must decide everything, at 1 Hz, with cruder senses -
   and nothing auto-clears on alarm; `takeAllDisguises` (permanent) papers over that.
3. **`actorenemy.cpp:446` retained zero-threat enemy** made aisquad/morale read "has an
   enemy" as "engaged" and go loud during stealth.
4. **`forceactivate`** in the go-loud recipes yanks posed actors out of scripted anims;
   combined with the card game's one-shot eject, the scene died permanently (plus the
   4-second cardhand attach-retry spam).
5. **SP-only hardcodes**: the challenge sight-trace targets `G_GetEntity(0)` (actor.cpp:8994)
   - players 2-4 only get challenged if the HOST's chest is visible, and empty slot 0 is a
   crash site. (`attackplayer` confirm, obstacle-bump blame, grenade fallback, AI-event
   suppression are also player-0-hardcoded; see deferred list §2.4.)

The session (2026-08-08/09) proved the core: gating the three raw sources + full
aisquad/morale stand-down held **attackers = 0 of 25 for a whole run** with the disguise
latched (10:38 measurement), all 25 actors in thinkstate idle, cardhand spam gone. What
FAILED: the card-table re-arm loop (two players still stood and never re-sat - the retail
stand path is one-way, so repair-after-eject cannot work).

---

## 2. The chosen architecture

**Script-owned three-phase state machine with one new single-owner file
(`coop_mod/stealth.scr`) + exactly ONE engine change (the challenge sight-trace retarget,
game.dll only).**

### 2.1 What each lens contributed

| Lens | Adopted | Rejected (and why) |
|---|---|---|
| **script-first (S)** | The phase machine shape (STEALTH -> BLOWN -> LOUD with the frozen latch KEPT through BLOWN); int phase var + monotonic `advance` ratchet; single-owner rule; explicit `coverBlown` shims at retail bust sites; `disguise_enemy/halt.scr` hooks for engine busts; unarmed-from-map-load (no strip needed); spawn hook above the `:711` early-exit; card protection via `enableEnemy 0`; aimaneuver stand-down | The script accept-fallback for the player-0 trace (S §5.1): an approximation - no interrogation anim, and it re-implements the accept decision from script bookkeeping instead of `m_ShowPapersTime`. A mis-timed fallback fires an accept the engine would have denied. One engine line does it right. |
| **vanilla-fidelity (V)** | E1 (the single engine change); the AC-numbered acceptance checklist + `^~^~^ST` marker grammar + TP test procedures + the 54-guard coordinate table; the director census (thinkstate==attack AND player enemy, debounced - never `.enemy != NULL`); cause-filtered card ejection (prevent, don't repair); ALARMTRIP defer-not-drop; delete dead `coop_stealthArmOnHurt` | D2 "cover-blown is terminal for the map" (BLOWN = `takeAllDisguises`). This breaks requirement 4: the Naxos bust precedes papers2/sentry2 in the spine, and vanilla explicitly supports killing the scientists and finishing the map disguised (05 §8). BLOWN must arm players WITHOUT stripping the disguise. |
| **engine-first (E)** | The three-phase insight that requirement 4 forces stealth to survive the first bust; the damage failsafe wired into blow detection; the deferred-engine-work list (§2.4) | The full engine suite (per-player MP maintenance, attackplayer retarget, bump/grenade blame, AI-event fix, `forceattackplayer 0` API). Five+ engine changes, two coexisting disguise stacks (e1l3/e1l4 vs m2l2a), live-maintenance behavior deltas nobody has ever run, and a cross-map `attackplayer` semantics change - all to buy a nicer BLOWN phase that the frozen-latch model already delivers acceptably. Wrong risk/benefit for one map. Kept on file as the v2 direction. |

### 2.2 Why this synthesis is right

1. **The verified core survives intact.** The 10:38-measured mechanism (source gates +
   stand-downs, whole-window semantics) is kept and merely re-conditioned onto one phase
   variable. Nothing that was measured working is redesigned.
2. **One engine line buys correctness that script cannot.** Without E1, requirements 3/4
   are host-position-dependent for players 2-4 (a sentry challenging player 3 silently
   never starts unless slot 0's chest is visible; empty slot 0 crashes). With E1, the
   function's every predicate consistently uses `m_Enemy`. Blast radius: the function only
   runs with a confirmed disguised enemy, so only disguise maps can observe it, and for a
   solo host `m_Enemy` IS entity 0 - SP behavior identical.
3. **The frozen latch through BLOWN is the closest fit to vanilla that script can do.**
   Holstered players stay disguised to every non-latched actor (engine flag still true);
   armed players get detected by the resumed HEAD script model (1 Hz). Deviation from
   vanilla: detection latency ~1 s, and a seeing actor latches permanently instead of
   re-calming on holster. Accepted and documented (S §7.5); the alternative (engine live
   maintenance) is the rejected E suite.
4. **Cards: prevention is the only shape that can work.** The retail stand path is one-way
   (`chairthread delete`, no re-seat anim); the 10:58 repair attempt failed in playtest as
   predicted by that structure. Preventing the eject (phase-gated cause filter +
   `enableEnemy 0`) makes "seated through stealth" deterministic without needing the still
   unidentified root cause - and the probes stay in until one clean run closes it.

### 2.3 Design decisions (binding)

- **D1**: Unarmed from FIRST SPAWN (map-load `coop_noWeapon`), not strip-at-pickup.
  Requirement 5 verbatim; kills the bug-1604/1606/1607 ordering class structurally.
  Fallback if a playtest hates the unarmed pre-pickup walk: the verified strip-at-pickup
  still works under the same machine (only the moment `coop_noWeapon` arms moves).
- **D2**: BLOWN arms everyone but KEEPS the disguise latch. LOUD (alarm) is the terminal
  strip (`takeAllDisguises`), matching the shipped mod model. Alarm doused does not
  restore stealth (documented deviation from vanilla; the phases never regress).
- **D3**: Retail scripted busts stay verbatim - not gated, not softened. They ADVANCE the
  phase (a one-line shim above each), which is what makes them "scripted" per requirement 3.
- **D4**: Whole-window gating during STEALTH, never per-target: a transiently
  undisguised-looking player must never permanently poison a guard.
- **D5**: One engine change only (E1). Everything else script.
- **D6**: `level.papers` stays global (vanilla semantics; one pickup upgrades the team -
  05 §1 "measured design, not a bug").
- **D7**: Cvar surface = exactly one public switch, `coop_stealthStart` (seeded 1).
  `coop_stealthNoAggro` and `coop_stealthFunnelGuard` are deleted with their code.

### 2.4 Deferred engine work (documented, NOT in this change)

From E §2 / 02 §3, revisit only if post-BLOWN combat fairness demands: `attackplayer`
confirm retarget to nearest living player (9293), obstacle-bump blame (3354-3406),
`Begin_Grenade` fallback blame (actor_grenade.cpp:349), `G_BroadcastAIEvent` per-originator
suppression (g_utils.cpp:1799-1803), per-player MP disguise maintenance, a
`forceattackplayer 0` clear API. All are exempt or unobservable during STEALTH (players
unarmed, player 0 disguised -> IsTeamMate exempts the poison paths).

---

## 3. The stealth state machine

### 3.1 Owner and variable

```
level.coop_stealthPhase    // NIL everywhere else; 1 = STEALTH, 2 = BLOWN, 3 = LOUD
```

- **Single owner: NEW file `coop_mod/stealth.scr`.** Exactly two labels write the var:
  the map-load assignment (phase = 1) and `advance` (monotonic ratchet:
  `if (local.target <= level.coop_stealthPhase) end`, no wait before the write). Everything
  else - aihandler, aisquad, morale, aimaneuver, alarm_system, cardgame, itemhandler - only
  READS it. This is greppable and enforceable.
- Int, positive tests only. On the four other cardgame maps (e2l2/m1l2a/m4l2/m4l3), on
  e1l3/e1l4, and on every non-stealth map the var is NIL, every `== 1` test is false, and
  all gates are provably inert (03 §10 load-bearing list untouched).
- Phase milestones that are NOT states: `level.papers` (0/1/2), papers item held. They
  change what spawners receive, not how AI is gated.

### 3.2 Phase table - what is dormant where

| System | STEALTH (1) | BLOWN (2) | LOUD (3) |
|---|---|---|---|
| Player weapons | NONE (`coop_noWeapon` from load; papers in hand via `coop_forcePapersEquip`) | armed (`coop_armPlayers`); respawners get normal loadout | armed |
| Engine disguise latch | latched true; director watchdog re-asserts | **kept latched** - holster = calm to non-latched actors | stripped (`takeAllDisguises`, permanent) |
| `aihandler::attackPlayer` wrapper | BLOCKED | live (HEAD detection resumes) | live |
| `coop_spawnReplica` clone birth-aggro | BLOCKED (clones spawn calm; `forceactivate` stays - clone anims need it) | born hostile (HEAD) | same |
| aisquad go-loud / morale berserk | FULL stand-down (not even `forceactivate`) | live | live |
| aimaneuver repositioning | stand-down (its `forceactivate` yanks posed actors) | live | live |
| `setEnemyAttackStates` restore (`attackplayer`) | BLOCKED (enableEnemy restore still runs) | live | live |
| `ai_alarm_alerted` ringer run | DEFERRED (wait <= 3 s for phase >= 2, then run or bail) | vanilla race to the switch | ringing |
| `disguiseHandler` cascades | inert by construction (nobody armed) + phase-checked | live | exits on alarm (shipped) |
| Engine challenges (salute/sentry/officer) | LIVE - vanilla (this is the point) | live (holstered players) | engine flips all to ATTACK |
| Card players | protected: `enableEnemy 0` + cause-filtered eject | vanilla wake rules (protection lifted first) | alarm buffs (`wakeupcardplayers`) |
| Retail `attackplayer` bust sites | LIVE, each advances phase first (D3) | live | live |
| director (census + watchdog + markers) | running | census only until LOUD; watchdog stopped | exits |

### 3.3 Transitions (complete list, all one-way)

**STEALTH -> BLOWN** - `stealth.scr::coverBlown local.reason` (idempotent via `advance 2`):

1. **Retail bust shims** (one line each, placed BEFORE the retail `attackplayer` so every
   downstream guard already sees phase 2): `sentry1alarm`, `sentry2thing`,
   `ohnothenaxos1`, `cardplayersdeath`, `cower`, `scialarm`, `unholsterweapon`, and the
   mod's own `waitForEnemy`. (`sciencetalk`'s attackplayer branch fires only under alarm =
   phase 3 already - no shim. `weldinginterupt` never latches and fires only post-alert -
   no shim.) Implementer MUST grep `attackplayer` in `maps/m2l2a.scr` (12 sites at HEAD)
   and classify each: shim every site reachable pre-alarm; note in-comment why the rest
   are exempt.
2. **Engine busts**: hooks at the top of `anim/disguise_enemy.scr` and
   `anim/disguise_halt.scr` - the engine plays these exactly when a challenge has failed
   (officer interrogation complete, sentry ignored 12 s, walk-off mid-check). Hook fires
   `coverBlown "engine-bust"` then falls through to the existing `[200]` insert, which now
   passes the gates because the phase already advanced.
3. **Damage failsafe**: actor-inflicted damage on any player during phase 1 ->
   `coverBlown "hurt"`. Gate on `attacker istypeof Actor` so the sentry2 swim
   `trigger_hurt` cannot arm players. (This IS the wiring of the dead
   `coop_stealthArmOnHurt` concept; the dead label itself is deleted.)
4. **Census backstop**: director sees attackers >= 1 on two consecutive ticks (2 Hz).
   Catches any missed site. Census counts `thinkstate == "attack" && .enemy is a player`
   over `level.coop_actorArray["german"]` - NEVER `.enemy != NULL` (retained zero-threat
   trap, friction 3).

**ANY -> LOUD** - `stealth.scr::alarmRaised`, called from the alarm-ON branch of
`global/alarm_system.scr` (working tree ~:701, the `[200]` `takeAllDisguises` hook)
BEFORE `takeAllDisguises`. `advance 3` runs phase-2 arming first if it never ran (alarm
rung during STEALTH by a player using a switch).

**No transition back.** Both underlying latches are one-way (`m_bForceAttackPlayer`;
`takeAllDisguises`).

### 3.4 coverBlown ordering (load-bearing)

1. `advance 2` writes the phase (every gate opens synchronously, same frame);
2. lift card protection (`enableEnemy 1` on `$suckyfatty`);
3. `waitthread itemhandler::coop_armPlayers` (extracted arming core: clear
   `coop_startUnarmed`/`coop_noWeapon`/`coop_forcePapersEquip` FIRST - or
   `giveWeaponLoadout` early-exits, bug-1607 - then re-give armory loadouts, then
   `activatePlayerWeapon` to displace the papers in hand);
4. player-facing `iprint "Cover blown - weapons free!"` (keep);
5. marker `^~^~^ST BLOWN reason=<r>`.

Players dead at that moment are armed on next spawn (noWeapon now clear -> normal
loadout pipeline).

---

## 4. Ordered implementation steps

Each step: files, precise change, risk, verifying log marker. Build with `.\build.ps1`
after every script step; watch `%APPDATA%\openmohaa\maintt\qconsole.log` (needs
`developer 1` for script println). Start every playtest via `ui_startdmmap 2`, never raw
`map`.

### Step 0 - Hygiene reverts (do first, alone)

- `global/cardgame.scr`: REVERT the ~10:58 re-arm sit loop (bug: measured not holding)
  back to the HEAD one-shot shape (`coop_cardGameSitThink` guard + holster + the plain
  `while (self.thinkstate == "idle") waitframe` eject). Do not lose the `[200]` guard.
- `coop_mod/aihandler.scr`: DELETE the opt-in funnel guard (`coop_stealthFunnelGuard`
  probe + gate inside the `attackPlayer` wrapper) - verified unnecessary (10:38 run) and
  it sits in the papers-challenge path. Delete the `coop_stealthNoAggro` cvar reads.
- `.wolf/buglog.json`: append the missing ids the code comments cite (bug-1605
  strip-by-class, bug-1607 noWeapon ordering, bug-1609 waitForEnemy) and entries for the
  10:38 funnel-guard demotion, the aisquad/morale full stand-down, and the card re-arm
  failure. The ledger has holes the comments do not.
- Risk: LOW (reverting to known states). Depthscan both files.
- Verify: grep `coop_stealthFunnelGuard` and `coop_stealthNoAggro` return nothing in the
  mod tree; cardgame.scr diff vs `git show HEAD:global/cardgame.scr` shows only the
  intended step-8 delta later.

### Step 1 - `coop_mod/stealth.scr` (NEW) + map-load route

- New file, ~150 lines: `init` (early-out unless `getcvar("coop_stealthStart") == "1"` and
  `level.coop_stealthPhase == 1`; apply card protection; containment strip sweep; start
  director), `advance` (monotonic ratchet), `coverBlown` (§3.4), `alarmRaised`,
  `onPlayerSpawn` (step 3), `director` (2 Hz: census, blown debounce, phase-1 disguise
  watchdog: per live `$player`, if engine `is_disguised` reads false -> re-assert via the
  per-player `giveDisguise` window, marker `REASSERT`; roster-free - iterate `$player`
  fresh each tick), `aggroAllowed` helper (returns 0 iff phase == 1).
- `maps/m2l2a.scr` coop branch, BEFORE `waitthread coop_mod/main.scr::main` (plain
  assignments only, cvar-gated on `coop_stealthStart`): `level.coop_stealthPhase = 1`,
  `level.coop_noWeapon = game.true`, `level.coop_startUnarmed = 1`,
  `level.coop_forcePapersEquip = game.true`. AFTER main returns:
  `thread coop_mod/stealth.scr::init`.
- `likeynorway`: REMOVE the session strip-route block (startUnarmed/forcePapersEquip/
  strip/noWeapon - all now at load); KEEP the papers hint, item adds, door, conversation,
  the SP-gated `type_disguise "salute"` flip, and one defensive
  `coop_stealthStripWeapons` sweep call.
- Risk: MEDIUM - boot order. The phase var must be set before any actor can think
  (assignment-before-main guarantees it); `init` must not wait before applying card
  protection. Also confirm `getcvar` before main.scr::main is safe (m2l2a already reads
  cvars in its coop branch - pattern-copy).
- Verify: `^~^~^ST PHASE phase=1` once at load; spawn a listen server, all players
  unarmed, papers absent pre-pickup, `^~^~^ST CENSUS attackers=0` ticking.

### Step 2 - Re-condition the verified gates onto the phase

- `coop_mod/aihandler.scr`: the `coop_stealthBlocksAggro` whole-window core
  (~:1184-1202) and the replica gate (~:274) change their condition to
  `stealth.scr::aggroAllowed` / `level.coop_stealthPhase == 1` (same semantics, one
  source of truth). **GATE the raw `attackplayer` at `setEnemyAttackStates` (~:1262)**
  identically - the last ungated site (04 §4.3); keep its `enableEnemy 1` restore
  unconditional. Add a phase check to `disguiseHandler`'s cascade calls (D4: a scavenged
  weapon must not poison during phase 1).
- `coop_mod/aisquad.scr` (~:115), `coop_mod/morale.scr` (~:71): keep the verified FULL
  stand-downs, condition -> phase == 1.
- `coop_mod/aimaneuver.scr`: ADD the same phase-1 stand-down (it cannot latch but its
  `forceactivate` yanks posed actors - 03 §5).
- Risk: LOW-MEDIUM. These are the verified mechanisms; the only new behavior is
  aimaneuver's gate and :1262. Do not touch the wrapper's bark/pain/favoriteenemy body.
- Verify: with `coop_aggroDebug 1`, existing `AGGRO BLOCKED` family logs during phase 1;
  `^~^~^ST CENSUS attackers=0` sustained with 2+ players (replicas alive and calm).

### Step 3 - Spawn/respawn/late-join hook

- `coop_mod/itemhandler.scr::managePlayerInventory`: insert
  `waitthread coop_mod/stealth.scr::onPlayerSpawn local.player` at the TOP, BEFORE the
  `if (level.coop_noWeapon) ... end` early-exit (~:711). Delete the now-dead in-place
  papers re-give at ~:745-747 (it was unreachable during stealth - 04 correction 2).
  Fix the stale line-number comment at ~:763 while there.
- `onPlayerSpawn` (in stealth.scr), when phase == 1: re-give the current papers item
  (`level.coop_itemPapers` - papers2-aware after upgrade) if `level.papers >= 1`;
  `setIsDisguised local.player true true` (forceState - class-removal/fresh-body is not a
  holster transition, bug-1606); if engine `is_disguised` reads false, run the per-player
  `giveDisguise` window; equip papers via the `coop_forcePapersEquip` machinery. When
  phase == 2: re-give papers item only. Phase 3 / NIL: end.
- CAUTION: the research docs disagree whether `giveDisguiseOnSpawn` (~:723) is reachable
  under `coop_noWeapon` (03 §2 vs 04 correction 2). READ the actual file; the hook must
  be self-sufficient either way (it is, per the above).
- Risk: MEDIUM - this is the per-spawn hot path on every map. The hook's first statement
  must be the phase test so non-stealth maps pay one comparison.
- Verify: kill+respawn and a late join during phase 1 ->
  `^~^~^ST SPAWN p=<name> armed=0 papers=<lvl> eng_is=1 late=<0|1>` per event; the
  respawner holds papers in hand, no loadout, salutes still work near him.

### Step 4 - Bust shims + engine-bust hooks

- `maps/m2l2a.scr`: one `waitthread coop_mod/stealth.scr::coverBlown "<site>"` line
  immediately above the retail `attackplayer` in: `sentry1alarm`, `sentry2thing`,
  `ohnothenaxos1`, `cardplayersdeath`, `cower`, `scialarm`, `unholsterweapon`,
  `waitForEnemy` (mod site - also give its own attackplayer an `aggroAllowed` symmetry
  gate so it cannot fire during phase 1 at all). Classify all 12 grep hits (§3.3.1).
- `anim/disguise_enemy.scr`, `anim/disguise_halt.scr`: `thread` (not waitthread - these
  run on the actor) `stealth.scr::coverBlown "engine-bust"` at the top of the `[200]`
  insert, phase-gated so non-stealth maps are untouched.
- Risk: MEDIUM - editing retail script flow. The shims are additive lines only; do NOT
  reorder or modify the retail statements. `waitthread` is safe (coverBlown has one
  waitthread inside; verify no wait-before-phase-write in `advance`).
- Verify: TP-3 style - trip sentry1 net -> `^~^~^ST BUST site=sentry1` then
  `^~^~^ST BLOWN reason=sentry1` exactly once, then `^~^~^ST ARMED p=...` x players
  within 2 s.

### Step 5 - Arming split + damage failsafe

- `coop_mod/itemhandler.scr`: extract `coop_armPlayers` from `coop_armOnBlown` (the
  clear-flags-first -> loadouts -> activate order, verbatim - it is load-bearing).
  `coop_armOnBlown` becomes: `advance 2` semantics preserved for its callers
  (`takeAllDisguises` keeps calling it; it now calls `coop_armPlayers` iff players are
  still unarmed) - net effect: BLOWN can arm without stripping, LOUD strips and arms if
  needed. DELETE the dead `coop_stealthArmOnHurt` label.
- Damage failsafe: hook the player damage path (player.scr damage handling or an
  `events.scr` subscription - follow the existing pattern in player.scr; do NOT invent a
  new bus) -> if phase == 1 and attacker `istypeof Actor` ->
  `thread stealth.scr::coverBlown "hurt"`.
- Risk: MEDIUM - `coop_armOnBlown` is referenced by alarm_system, items.scr, e1l4
  Ship/PreShip via takeAllDisguises. Keep its external signature identical; only its
  internals split. The re-arm leg has NEVER been measured (04 §3 last row) - the ARMED
  marker exists to close that.
- Verify: `^~^~^ST ARMED p=<name> kit=<weapon>` per player on first blow; a phase-1
  player shot by a latched actor arms everyone (`reason=hurt` path) even if census missed.

### Step 6 - Alarm integration

- `global/alarm_system.scr`: (a) rework the bug-1616 ALARMTRIP guard in
  `ai_alarm_alerted` from per-target drop to DEFER: while phase == 1, wait up to 3 s
  (checking the actor is still alive and attacking) for phase >= 2; if it advances,
  proceed vanilla (race to the switch); else return. Phase NIL (e1l4, m6l1c) -> vanilla
  path untouched. (b) In the alarm-ON branch, call
  `thread coop_mod/stealth.scr::alarmRaised` immediately BEFORE the existing
  `takeAllDisguises` hook (~:701).
- Risk: MEDIUM - shared by e1l4/m6l1c; the phase var is NIL there so both edits are inert.
  This file is a chrissstrahl rework (~1480 diff lines vs retail) - anchor by label, and
  depthscan.
- Verify: `^~^~^ST ALARM ev=defer` on a transient phase-1 alert (should be rare to never);
  after a genuine bust, `ev=run` and the ringer douses the switch -> `^~^~^ST PHASE
  phase=3`; alarm toggled off stops sirens/backups but phase stays 3 and nobody
  re-disguises.

### Step 7 - Card table: prevent, don't repair

- `stealth.scr::init`: `$suckyfatty enableEnemy 0` (all three); `coverBlown` restores
  `enableEnemy 1` before the retail wake rules need them (§3.4 order).
- `global/cardgame.scr` seated loop - the mod file's `sitthink` (the label that carries
  the `[200]` `coop_cardGameSitThink` guard and the
  `while (self.thinkstate == "idle") waitframe` eject; retail calls the equivalent
  `checkresponse` - locate by the loop, not the name): gated on
  `level.coop_stealthPhase == 1`, replace the bare thinkstate eject with GENUINE-CAUSE
  ejection only: `level.alarm == 1`, phase >= 2, health below the seated value (pain/
  damage), `self.creator.broken == 1`, or death. A bare thinkstate excursion with none of
  those is waited out - the actor stays seated and the anim driver is never deleted, so
  the loop resumes on its own. Phase NIL or >= 2 -> the retail one-shot eject applies
  unchanged (the other four cardgame maps are behavior-identical by construction).
- Probes: keep the SALUTE probe (`anim/disguise_salute.scr`); add ONE line at the eject
  point logging `^~^~^ST CARD ev=eject cause=<alarm|phase|pain|broken|death>
  think=<thinkstate>`; log `ev=flicker-held` (gated on `coop_aggroDebug`) when a flicker
  is waited out.
- Risk: HIGH (this is the unsolved system). The design makes the symptom impossible in
  phase 1 rather than explaining it; if TP-2 still shows a stand, the `cause` field and
  the SALUTE probe discriminate the remaining hypotheses (salute anim stall for
  non-a/c/d voicetypes -> fallback: normalize the voicetype in the map coop branch;
  anim-driver interplay -> new territory). Also verify a phase-1 card-player KILL still
  runs `cardplayersdeath` -> shim -> BLOWN -> survivors hostile (retail intent; check
  `enableEnemy 0` does not block the forced attack - `attackplayer` + the coverBlown
  restore run first).
- Verify: 10-minute card-room soak, `^~^~^ST CARD ev=eject` count 0, zero
  `cardhand01/02.tik` attach-retry lines, faces/anims cycling normally.

### Step 8 - E1: the engine trace retarget (game.dll)

- `openmohaa-hzm/code/fgame/actor.cpp` ~:8994, inside
  `PassesTransitionConditions_Disguise`: replace the sight-trace target
  `G_GetEntity(0)->centroid` with `m_Enemy->centroid` (the function already requires
  `m_Enemy` non-null at ~:8972; add a defensive NULL check anyway). Tag
  `[user 2026-08-XX]`.
- Build per CLAUDE.md engine recipe. **Deploy: game.dll is a MANUAL deploy to the GOG
  root** (build.ps1 handles cgame.dll only - project memory, lobby-build note). No exe or
  cgame change, no protocol constants -> game.dll-only ship is safe.
- Follow the turret-camera-regression rule: diff every touched engine file vs original;
  the engine repo sits on a detached HEAD.
- Risk: LOW technically (one function, only reachable with a confirmed disguised enemy),
  MEDIUM procedurally (engine build + manual deploy + PDB pairing for crash dumps).
- Verify: 2-player run, host parked out of line-of-sight behind the locker room, client
  walks to goatsbutt -> the challenge FIRES for the client (DENY/ACCEPT observed). At
  HEAD this silently never happens. Also covers the empty-slot-0 crash site.

### Step 9 - Full verification pass

Run the test plan (§6) in order: TP-1, TP-1b, TP-2, TP-3 solo first; then TP-4/5/6 with
4 players. Log every failure to `.wolf/buglog.json` before fixing it.

---

## 5. Disposition of ALL existing session work

Row numbers = the delta table in `04_session_state.md` §1. Everything is currently
uncommitted working tree.

| # | Item | Verdict | How / why |
|---|---|---|---|
| 1 | m2l2a.scr `coop_stealthStart` route in `likeynorway` | **REWORK** | Route trigger moves to map load (D1, step 1); strip demoted to defensive sweep. The verified pieces (ordering knowledge, papers equip) survive relocated. |
| 2 | `waitForEnemy` rewrite (bug-1609) | **KEEP** | + phase-symmetry gate + shim (step 4); verify (was DEPLOYED-UNVERIFIED). |
| 3 | Norway guards `type_disguise "salute"` flip SP-gated | **KEEP** | Removes the salute-vs-walkto standing trap in coop (04 §5). |
| 4 | `cardplayersdeath` -> `cc_card_sentry` challenge bump | **KEEP** | Not stealth; rides along. |
| 5 | `coop_baked_0808` blueprint placements | **KEEP** | Not stealth. The collectible.scr owner-guard defect is a separate open item - do not fold in. |
| 6 | itemhandler `managePlayerInventory` papers re-give (~:745) | **REWORK** | Delete; absorbed into `stealth::onPlayerSpawn` ABOVE the `:711` exit (step 3) - the session placement was unreachable during stealth. |
| 7 | Stealth-start comment + takeall removal (bug-1604) | **KEEP** | Verified (uniform survives). |
| 8 | `coop_armOnBlown` hooked into `takeAllDisguises` | **REWORK** | Split: `coop_armPlayers` extracted (step 5); armOnBlown remains the takeAll-side entry. Order rule preserved verbatim. |
| 9 | `coop_paperPassAll` | **KEEP** | Verify in 4P (TP-4). If the engine's own ACCEPT demote + accept-thread net disarm already reads as fair, consider deleting later for fidelity - decision deferred to the 4P run (V §3.3). |
| 10 | `coop_papersAnytime` | **KEEP** | Requirement 2 verbatim. Verify (TP-1). |
| 11 | `coop_stealthStripWeapons` | **KEEP (demoted)** | Containment only: once at init, per-player from the director when a non-InventoryItem shows up in hands (world pickup). Consider drain-until-empty loop vs fixed 4 passes while there. |
| 12 | `coop_stealthHoldDisguise` watchdog + STEALTHWATCH | **REWORK** | Absorbed into the director (step 1): roster-free, phase-1 only, read-mostly (re-assert is the exception, logged). |
| 13 | `coop_stealthArmOnHurt` | **REWORK (delete + rewire)** | Dead code at HEAD+delta. The concept ships as the damage failsafe -> `coverBlown "hurt"` (step 5); the label is deleted. |
| 14 | `enableClickablePapers` NIL/NULL guard (bug-1603) | **KEEP** | Verified. |
| 15 | weaponstate.scr:56 inventory-item rule (bug-1617) | **KEEP** | Verified; it IS the engine rule (player.cpp:5480-5484). Do not touch the bookkeeping above it. |
| 16 | `attackPlayer` funnel guard + `coop_stealthFunnelGuard` | **REVERT (delete)** | Verified unnecessary (10:38); sits in the papers-challenge path (step 0). |
| 17 | `coop_stealthBlocksAggro` whole-window block | **REWORK (keep semantics)** | The verified core. Condition changes to the phase var; behavior identical (step 2). |
| 18 | `coop_spawnReplica` clone gate | **KEEP** | Condition -> phase (step 2); `forceactivate` stays unconditional. |
| 19 | aisquad full stand-down | **KEEP** | Condition -> phase (step 2). Verified. |
| 20 | morale berserk stand-down | **KEEP** | Condition -> phase (step 2). Verified. |
| 21 | `setEnemyAttackStates` raw attackplayer (~:1262) | **REWORK (gate it)** | The last ungated latch site (step 2). |
| 22 | ALARMTRIP per-target guard (bug-1616) | **REWORK** | Defer-not-drop, phase-based (step 6) - fixes the 04 §4.4 inconsistency in the vanilla-faithful direction. |
| 23 | cardgame sitthink re-arm loop | **REVERT** | Measured FAILED. Replaced by prevention (step 7). |
| 24 | SALUTE stall probe | **KEEP (temp)** | Until one clean card-room run; then remove (§7). |
| 25 | `disguise_accept.scr` -> `coop_paperPassAll` thread | **KEEP** | Pairs with row 9. |
| 26 | autoexec TEMP `coop_aggroDebug`/`coop_bpDebug` | **REVERT at release** | Keep during implementation; §7. Also re-join the comment the insertion split. |
| 27 | `coop_defaults.cfg` `seta coop_stealthStart 1` | **KEEP** | The single public switch (D7). |
| - | NEW: aimaneuver stand-down | **ADD** | Not in the session set; closes the last `forceactivate` source (step 2). |
| - | Unrelated riders (m2l2b Enigma, collectible.scr BP guard, challenges, ambience, player.scr limp, replace.scr convOk, m3l1b...) | **OUT OF SCOPE** | Do not fold into this change set or its verdicts (03 provenance caveat). |

---

## 6. 4-player test plan

All runs on a listen server (`ui_startdmmap 2`), `developer 1`, `coop_aggroDebug 1`,
reading `%APPDATA%\openmohaa\maintt\qconsole.log`. Marker grammar:
`^~^~^ST <TAG> k=v ...` with tags PHASE, SPAWN, CENSUS, REASSERT, BUST, BLOWN, ARMED,
ALARM, CARD (defined in steps above). Single-player FIRST - it exercises everything
except E1 and the multi-player lifecycle; then the 4P deltas.

### 6.1 Single-player

**TP-1 - golden path (full stealth, no Naxos).** Spawn -> pickup -> card room walk ->
goatsbutt: show papers1 -> ACCEPT + `sentry1trigdisable` -> movetheflak -> walk past
Naxos -> papers2 pickup -> sentry2dude: deliberately show papers1 once (expect DENY
wave-off, no attack, no alarm) -> show papers2 -> ACCEPT + net disarmed -> endlevel.

PASS evidence: `PHASE phase=1` once; every `SPAWN ... armed=0 eng_is=1`;
`CENSUS attackers=0` on EVERY line; zero `BUST`/`BLOWN`; `CARD ev=eject` count 0; zero
cardhand attach-retry lines; DENY then ACCEPT observed at sentry2; mission complete.

**TP-1b - the requirement-4 keystone: post-Naxos stealth continuation.** Plant the Naxos
-> `BUST site=naxos`, `BLOWN reason=naxos`, `ARMED` x1 within 2 s, three scientists
hostile and ONLY them (census jumps by exactly the latched set) -> kill the scientists ->
holster -> walk south: salute guards salute again (frozen latch holds), papers2 pickup,
sentry2 ACCEPT with papers2, endlevel. This proves BLOWN does not end stealth (D2) and
the L2 gate works post-bust like vanilla.

**TP-2 - card-room soak.** 10 minutes in the card room, papers in hand, wave papers
repeatedly (spam safety). PASS: `CARD ev=eject` count 0; all three seated and animating;
any `ev=flicker-held` lines tallied by cause. If an eject occurs, its `cause` +
the SALUTE probe output IS the root-cause verdict - fix before proceeding.

**TP-3 - every scripted spot, deliberately.** Sub-runs: (a) trip sentry1 net pre-accept;
(b) ignore goatsbutt's challenge 12 s (ENEMY -> ATTACK); (c) walk off mid-challenge
(HALT -> ATTACK); (d) let officer1 complete an interrogation with papers shown (ENEMY
instantly, ATTACK +3 s, worst <= 15 s); (e) plant Naxos; (f) kill a card player
(survivors hostile via `cardplayersdeath`); (g) cross the sentry2 line un-accepted;
(h) sciencetrig flavor scene with alarm silent (five VO lines, NO bust). Each of a-g:
exactly one `BLOWN`, `ARMED` for every living player <= 2 s, and where the busted actor
is `$ai_alarm`: `ALARM ev=run` -> alarm rings -> `PHASE phase=3` -> disguise stripped ->
toggle a switch off -> sirens/backups stop, stealth does NOT resume.

### 6.2 4-player deltas

**TP-4 - split-pair sweep + E1 regression.** Pairs at opposite map ends walk the 54-guard
patrol route (coordinate table in `design_vanilla-fidelity.md` §7). The host parks out of
line-of-sight; a CLIENT approaches each sentry. PASS: challenges fire for the client
(ACCEPT/DENY events in log - assert events occur, NOT just silence; the pre-E1 failure
signature is a staring sentry and a quiet log); `CENSUS attackers=0` throughout; salutes
observed for whichever player is near; replicas present (2+ players) and calm.

**TP-5 - lifecycle churn during STEALTH.** One player suicides + respawns; one
disconnects + rejoins; one stays dead through the papers2 pickup then respawns (must hold
papers2 on spawn - global `level.papers` + item re-give). PASS: every `SPAWN` line
`armed=0 eng_is=1` with correct `papers=`; no `REASSERT` storm (>3/min = investigate);
census stays 0.

**TP-6 - 4-player blown path.** Trip the sentry2 net with all four alive; second run with
two players dead at the moment of the bust. PASS: single `BLOWN`; `ARMED` x(living) <= 2 s;
dead players' next `SPAWN` shows armed (normal loadout path); deferred ringer runs; zone
backups spawn; a player showing papers mid-challenge elsewhere sees his checker collapse
(vanilla disguise-lost logic) - expected, not a bug.

**Acceptance checklist (the release bar):** TP-1, TP-1b, TP-3(a,e,f,g), TP-4, TP-5, TP-6
pass; TP-2 clean OR card root-cause identified and fixed; no `Script Error` lines; no
regression in a maptest Phase 1 smoke of neighboring maps (m2l2b/m2l2c load) and one
non-stealth map (aihandler/aisquad/morale/alarm_system/cardgame are shared - e2l2 or
m1l2a for cardgame, e1l4 for alarm_system+disguises).

---

## 7. Pre-release cleanup list

1. `autoexec.cfg`: delete TEMP `set coop_aggroDebug 1` and `set coop_bpDebug 1`; re-join
   the split `developer 0` comment block.
2. Delete or gate every ungated session println (list from 04 §6): m2l2a.scr
   `STEALTH waitForEnemy fired`; itemhandler `PAPERS guard satisfied`, per-player
   `STEALTH ... isDisguised=` state line, `STEALTH weapons stripped`, `STEALTH re-asserted`,
   `STEALTH cover blown, loadouts issued` (keep the player-facing
   `iprint "Cover blown - weapons free!"`). collectible.scr BP prints are the other
   work stream - leave to it.
3. Marker review: KEEP `PHASE`/`BLOWN`/`ARMED` unconditional (rare, high-value); gate
   `CENSUS` heartbeat, `CARD ev=flicker-held`, `REASSERT` detail on `coop_aggroDebug`.
4. Remove the SALUTE stall probe once TP-2 has passed clean.
5. Cvar hygiene: `coop_stealthStart` seeded in `coop_defaults.cfg` with its justifying
   comment; `coop_stealthNoAggro`/`coop_stealthFunnelGuard` gone with their code (verify
   by grep); `coop_aggroDebug` remains as an unseeded dev cvar.
6. CRLF normalization: the 8 stealth-session files (itemhandler.scr, aisquad.scr,
   morale.scr, m2l2a.scr, m2l2b.scr, coop_defaults.cfg, player.scr, replace.scr) plus
   stealth.scr/cardgame.scr/alarm_system.scr/aimaneuver.scr if touched; the other ~21
   LF-warned files belong to other work streams.
7. Buglog: entries for every step's fixes + the step-0 backfill; final entry recording
   the architecture decision with verdict per requirement.
8. Docs (OpenWolf routing): `docs/DECISIONS.md` - the chosen architecture + the two
   rejected lenses; `docs/TRAPS.md` - merge "attackplayer is a one-way latch; whole-window
   gate during stealth" and "card-game eject is one-way; prevent, never repair" into
   existing disguise/cardgame entries if present; `docs/FEATURES.md` + one `HISTORY.md`
   line when shipped; `docs/OPEN.md` - card root cause if still open, `coop_paperPassAll`
   keep/delete decision, deferred engine list (§2.4).
9. Engine ship: game.dll (+ game.pdb next to it in the GOG root for crash-dump line
   resolution) - manual deploy; no exe/cgame pairing needed for E1.
10. Commit strategy: mod repo commit for the stealth set separate from the unrelated
    riders; engine fork is on a detached HEAD - record the E1 diff in the commit message
    per the turret-camera-regression rule.
