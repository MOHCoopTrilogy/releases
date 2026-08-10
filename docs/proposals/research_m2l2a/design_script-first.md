# m2l2a Definitive Coop Stealth — SCRIPT-FIRST Design (engine frozen)

Design proposal, 2026-08-09. Lens: **script-only, minimal diff**. Engine (`openmohaa-hzm`) is
treated as read-only; every mechanism below is `.scr`/`.cfg`. Evidence base: research docs
`01_vanilla_retail.md` (retail mission + engine substrate), `02_engine.md` (disguise machinery),
`03_hzm_baseline.md` (HEAD coop layer), `04_session_state.md` (session delta + verification
ledger), `05_papers2_scripted.md` (papers level 2 + scripted detection). Cited as 01..05 §n.

---

## 0. Executive summary

One new file, `coop_mod/stealth.scr`, becomes the **single owner** of a monotonic three-phase
state machine `STEALTH(1) → BLOWN(2) → LOUD(3)` stored in `level.coop_stealthPhase`. Everything
else is gates that read the phase:

- **Phase 1 (STEALTH)**: players are unarmed with papers in hand from frame one; every
  mod-originated `attackplayer` source is blocked (the verified whole-window block, 04 §1 #17);
  aisquad/morale/aimaneuver are fully stood down; card players and other scripted-idle actors are
  protected by `enableEnemy 0` plus a phase-gated eject in `cardgame.scr`. The **engine's own
  disguise machinery runs untouched** — salutes, sentry papers checks, the level-2 gate, DENY
  wave-offs, and officer busts all behave as vanilla (requirement 3/4).
- **Phase 2 (BLOWN)**: entered by any *scripted* detection (retail bust sites, engine
  ENEMY/HALT bust via the `disguise_enemy/halt.scr` hooks, actor-inflicted damage). Everyone is
  armed (existing `coop_armOnBlown` machinery), the HEAD detection/aggro model resumes, but the
  engine disguise latch is **kept** — holstering still calms non-latched actors, matching
  vanilla's recoverable local busts (01 §3.9, 05 §8).
- **Phase 3 (LOUD)**: the alarm. Existing choke point (`alarm_system` → `takeAllDisguises`)
  unchanged: permanent disguise strip + arming, per the shipped mod model (03 §8).

The verified session core (source-gated aggro block, 0/25 attackers sustained — 04 §3) is kept
and rewired to read the phase. The failed card re-arm loop is reverted and replaced with a
prevention design (don't eject during STEALTH) instead of a repair design (re-seat after eject).

---

## 1. Requirements → mechanism map

| # | Requirement (verbatim intent) | Mechanism |
|---|---|---|
| 1 | 4 players spawn/respawn/late-join during stealth | `stealth.scr::onPlayerSpawn` hook placed ABOVE the `coop_noWeapon` early-exit in `managePlayerInventory` (fixes the 04 §4.2 hole); roster-free watchdog |
| 2 | All players hold papers, can SHOW anytime | items.scr fan-out (unchanged, 05 §10) + per-spawn re-give + `coop_papersAnytime` (04 §1 #10) + `coop_forcePapersEquip` |
| 3 | Nobody spotted unless SCRIPTED | Whole-window aggro block covers only **mod-originated** `attackplayer`; retail bust sites and the engine challenge state machine are deliberately left live |
| 4 | Level-2 papers upgrade like vanilla | `papers2pickup`/`sentry2accept` untouched (05 §4-5); global `level.papers` accepted by design; script accept-fallback for the player-0 trace hazard |
| 5 | No weapons until blown/alarm | `level.coop_noWeapon` armed at **map load** (not at pickup); every blow path funnels into `coverBlown` which arms everyone |
| 6 | Ambient NPCs behave as vanilla | `enableEnemy 0` during STEALTH + phase-gated `checkresponse` eject in cardgame.scr + kept aisquad/morale stand-down (no `forceactivate` yanks) |

---

## 2. The state machine

### 2.1 State variable and owner

```
level.coop_stealthPhase   // NIL on non-stealth maps; 1 = STEALTH, 2 = BLOWN, 3 = LOUD
```

- **Int, not string** — every consumer tests `if (level.coop_stealthPhase == 1)`. On the four
  other cardgame maps (e2l2/m1l2a/m4l2/m4l3, 03 §8) and every non-stealth map the var is NIL and
  the comparison is false, so all gates are inert. Per the project NIL/NULL gotcha
  (mohaa_script_notes), any *negated* test must guard both: use positive `== 1` tests only.
- **Single owner: `coop_mod/stealth.scr`** (new file). Only two labels ever write the var:
  `init` (sets 1) and `advance` (monotonic ratchet). Nothing else in the tree assigns it —
  that is the enforceable "one owner" rule, and it is greppable.
- Transitions are **monotonic**: `advance` does `if (local.target <= level.coop_stealthPhase) end`
  — double calls, racing calls, and out-of-order alarm-vs-bust all collapse safely. No
  serialization thread needed beyond that guard (script is single-threaded per frame; `advance`
  runs no `wait` before writing the var).

### 2.2 Phases and what each one asserts

| | STEALTH (1) | BLOWN (2) | LOUD (3) |
|---|---|---|---|
| Player weapons | none; papers in hand (`coop_noWeapon` set) | full armory loadout (`coop_armOnBlown` path) | same |
| Engine disguise latch (`m_bIsDisguised`) | latched TRUE, watchdog re-asserts | **kept latched** — holster = calm (vanilla-like recovery, 01 §3.9) | stripped (`takeAllDisguises`, permanent per mod model, 03 §8) |
| Mod `attackplayer` sources | ALL blocked (whole-window, 04 #17) | unblocked — HEAD detection model resumes (03 §4) | unblocked |
| Engine challenges (salute/sentry/officer) | live, vanilla | live | engine flips all to ATTACK on alarm (02 §7.2d) |
| aisquad / morale / aimaneuver | full stand-down (04 #19/#20 + new aimaneuver gate) | active | active |
| Count-scaling replicas | spawn, but born calm (04 #18) | born hostile as at HEAD | same |
| Card players / scripted idlers | protected: `enableEnemy 0`, eject gated off | vanilla wake-up rules resume | alarm buffs (`wakeupcardplayers`) |
| Alarm ringers (`ai_alarm_alerted`) | blocked (aligned to whole-window, fixes 04 §4.4) | vanilla — a latched actor may run for the switch (01 §2.6) | ringing |

### 2.3 Transition triggers (the complete list)

`STEALTH → BLOWN` — call `stealth.scr::coverBlown local.reason`:

1. **Retail scripted bust sites** in `maps/m2l2a.scr` (01 §2.7, 05 §7.2): `sentry1alarm`
   (tripwire past goatsbutt), `sentry2thing` (gate line / swim `trigger_hurt`),
   `ohnothenaxos1` (Naxos demolition — mandatory story blow), `cardplayersdeath` (card-player
   kill), `unholsterweapon`, `cower`, `scialarm`. One added line per site, placed **before** the
   retail `attackplayer` so downstream guards see phase 2.
2. **Engine-driven busts** — hooks in `anim/disguise_enemy.scr` and `anim/disguise_halt.scr`
   (the engine plays these exactly when a challenge has failed: officer interrogation complete,
   sentry ignored 12 s, walk-off mid-check — 02 §2). The hook fires `coverBlown` *then* falls
   through to the existing `[200]` attackPlayer insert, which now passes the gate because the
   phase already advanced.
3. **Actor-inflicted damage on any player while phase 1** — the reworked
   `coop_stealthArmOnHurt` (currently dead code, 04 §4.1), wired into the player damage path and
   gated to `attacker istypeof Actor` so environmental damage (the sentry2 swim `trigger_hurt`,
   05 §5) does not blow cover by itself.
4. **A player acquires a real weapon mid-stealth** (world pickup) — detected by the watchdog;
   it first tries to strip (`coop_stealthStripWeapons` per-player); stripping, not blowing, is
   the response — this is a containment trigger, not a blow trigger.

`ANY → LOUD` — `stealth.scr::alarmRaised`, called from the existing `[200]` alarm-ON hook next
to `takeAllDisguises` (mod alarm_system:701, 05 §7.3). `advance 3` implies passing through
BLOWN's arming if it never ran (the monotonic ratchet runs phase-2 actions iff skipped).

There is **no transition back**. The alarm may be doused (retail toggle, 01 §2.6) — `level.alarm`
still governs the alarm system's own behavior, but the stealth phases never regress, because both
underlying latches are one-way: `m_bForceAttackPlayer` (02 §4) and `takeAllDisguises` (03 §8).

---

## 3. Architecture by layer

### 3.1 Substrate (unchanged): the engine latch

The shipped three-layer sandwich (03 §1) stays: `changeGameType` windows latch `m_bIsDisguised`
true per player; `weaponstate.scr` mirrors holster state into `coop_isDisguised`; script owns
detection. The session's `weaponstate.scr:56` inventory-item rule (papers in hand keep the
disguise — engine rule player.cpp:5480, bug-1617, VERIFIED 04 §1 #15) is kept verbatim.

### 3.2 Unarmed route: `coop_noWeapon` from frame one

The session route stripped weapons at uniform pickup because the loadout had already been given
(04 §2). The definitive route moves the lockout to **map load**:

- `maps/m2l2a.scr` coop branch sets `level.coop_noWeapon = game.true` +
  `level.coop_startUnarmed = 1` + `level.coop_forcePapersEquip = game.true` at load (gated on
  `coop_stealthStart`). `managePlayerInventory:711` then early-outs for every spawn — **no
  loadout is ever granted, so there is nothing to strip** and the bug-1607 ordering hazard
  (noWeapon-before-strip starves the strip) disappears structurally.
- `coop_stealthStripWeapons` (VERIFIED, 04 #11) is demoted from route-critical to **containment
  sweep**: called once after `stealth::init` (belt-and-braces against anything another system
  granted) and per-player from the watchdog when a non-InventoryItem shows up in someone's hands
  (world weapon pickup). Its `setIsDisguised force` tail is kept (bug-1606: class-removal is not
  a holster transition).
- Pre-pickup players are **empty-handed**, which satisfies the engine disguise criterion (no
  weapon → disguised, 01 §1.1) — the pre-papers segment needs no special casing.
- Unwind is unchanged: `coop_armOnBlown` clears `coop_startUnarmed` / `coop_noWeapon` /
  `coop_forcePapersEquip` FIRST, then loadouts, then `activatePlayerWeapon` (04 §2).

### 3.3 Aggro containment: one predicate, five gates

Replace the session's `coop_stealthBlocksAggro` window flag with the phase test. A tiny helper
in stealth.scr keeps every gate identical:

```
// stealth.scr::aggroAllowed  — returns 0 during the stealth window, 1 otherwise
```

Gated sites (the complete mod-originated `attackplayer` inventory, from 03 §4-5 / 04 §1):

| Site | File | Session status | Design |
|---|---|---|---|
| `attackPlayer` wrapper | aihandler.scr:1027 | funnel guard demoted to opt-in | gate on phase (replaces funnel guard, which is **deleted** — verified unnecessary 10:38 run, 04 §3) |
| replica birth | aihandler.scr (`coop_spawnReplica`) | gated, VERIFIED | keep; `forceactivate` stays unconditional (clone anims) |
| aisquad go-loud | aisquad.scr:~110 | full stand-down, VERIFIED | keep, read phase |
| morale berserk | morale.scr:~67 | full stand-down, VERIFIED | keep, read phase |
| `setEnemyAttackStates` restore | aihandler.scr:1262 | **UNGATED** (04 §4.3) | gate — the last raw site |
| `ai_alarm_alerted` | global/alarm_system.scr:393-403 | per-target guard (bug-1616) | **align to whole-window** (fixes 04 §4.4: an innocent undisguised player must not ring the alarm during phase 1) |
| `waitForEnemy` | maps/m2l2a.scr:727-766 | rewritten (bug-1609) | keep rewrite; add phase gate before its `attackplayer` for symmetry |

Deliberately **NOT** gated: every retail `attackplayer` in `maps/m2l2a.scr` (the 11 retail
sites, 03 §7) and the engine state machine. These are the "scripted" spots of requirement 3;
each one now also *advances the phase* (§2.3), so by the time the latch fires the gates are
already open and downstream behavior (alarm ringers, detection cascades) is vanilla.

`aimaneuver.scr` gets the same stand-down gate as aisquad/morale: it cannot latch anyone (no
`attackplayer`) but its `forceactivate` yanks scripted-anim actors (03 §5) — the session cured
the card-hand spam by stopping exactly this class of disturbance.

### 3.4 Ambient scripted actors (requirement 6) — prevent, don't repair

The 10:58 re-arm loop FAILED in playtest (04 §5) and is **reverted**. The replacement attacks
the eject itself, not the recovery:

1. **`enableEnemy 0` on `$suckyfatty` (×3) during phase 1**, applied by `stealth::init` and
   restored (`enableEnemy 1`) by `coverBlown`. With no enemy acquisition there is no retained
   zero-threat enemy, no disguise-transition capture, and no curious-from-sight — the three
   candidate flicker sources of 04 §5 all require an enemy or an AI event. Pain and death still
   perturb (correct: shooting a card player must end the scene — `cardplayersdeath` is retail
   detection, 01 §2.7.5).
2. **Phase-gated eject in `global/cardgame.scr::checkresponse`**: during phase 1, a thinkstate
   flicker does not eject — the loop re-enters the sit instead (skip the stand branch and the
   `creator.broken` cascade unless `self.health` dropped or phase ≥ 2). This is defense-in-depth
   for whatever residual mechanism stood the two players up on 08-09; it makes "seated through
   the stealth window" *deterministic* rather than dependent on identifying that mechanism.
   Behaviour-neutral on the other four cardgame maps (phase var NIL → gate false → retail path).
   On BLOWN the retail one-shot eject applies unchanged — cover is blown, they *should* stand.
3. **Norway pair**: keep the session's SP-gating of the `type_disguise "salute"` flip (04 #3 —
   a salute-type with a live disguised enemy wins over the walkto and traps them standing,
   04 §5) and the `waitForEnemy` rewrite (04 #2). During phase 1 its exit condition
   (`canseeUndisguisedPlayers`) can never fire because nobody has a weapon.
4. **Card protection ordering**: `enableEnemy 0` must land before the actors can flicker.
   `level.coop_stealthPhase = 1` is assigned in m2l2a.scr **before** `waitthread main.scr::main`
   (plain assignment, no wait — legal per the single-frame init rule), so every gate is armed
   from the first AI frame; `stealth::init` applies the per-actor protections right after main
   returns, same frame.
5. The SALUTE stall probe (04 #24) stays until one clean 4-player run confirms the card room,
   then is removed.

### 3.5 Papers UX and the level-2 gate (requirements 2 & 4)

- Grant/fan-out unchanged: `likeynorway` → `items.scr` → all players + `level.papers = 1`;
  `papers2pickup` → `level.papers = 2` (05 §3-4). Global level is accepted by design (05 §1) —
  one player's upgrade upgrades the team, which is the correct coop reading of a level-global.
- **Show anytime**: keep `coop_papersAnytime` (04 #10) — primary fire while holding papers (or
  empty-handed) fires the papers item, which plays `show_papers.skc` and stamps
  `m_ShowPapersTime` per player (01 §1.2). This is per-player-correct engine machinery (02 §2).
- Keep `coop_paperPassAll` (04 #9) + the `disguise_accept.scr` hook (04 #25): one accepted
  check clears the whole squad and retires the checker — the right coop reading of ACCEPT's
  permanent downgrade-to-salute (02 §2: players 2-4 would otherwise never be re-checked anyway).
- Keep the `enableClickablePapers` NIL guard (bug-1603, VERIFIED).
- **DENY stays a wave-off**: with everyone unarmed, the `[200]` inserts in
  `disguise_deny/accept/wait/salute.scr` can never fire their attackPlayer branch
  (`canseeUndisguisedPlayers` false), so sentry2dude's level-1 DENY is exactly vanilla:
  3 s anim, back to idle, re-ask in 15 s (05 §2.3).

### 3.6 Spawn / respawn / late join (requirement 1)

Single hook: `stealth.scr::onPlayerSpawn self`, called from
`itemhandler.scr::managePlayerInventory` **immediately before** the `:711 coop_noWeapon`
early-exit (this placement is the fix for 04 §4.2 — the session's papers re-give at :745 was
unreachable during stealth). For phase 1 spawns it:

1. re-gives the current papers item (`level.coop_itemPapers` — papers2-aware after the upgrade,
   05 §10);
2. runs `setIsDisguised self true true` (forceState) on the fresh body;
3. relies on the normal `giveDisguiseOnSpawn` (already above :711) for the engine latch;
4. equips the papers via the `coop_forcePapersEquip` machinery.

The watchdog (`coop_stealthHoldDisguise`, reworked per 04 #12) becomes **roster-free**: each
0.5 s tick iterates the live `$player` array (1-indexed, `.size`), so respawners and late
joiners are covered with no registration step. Per tick, per player: if the engine getter
`is_disguised` reads false → re-latch via the per-player `giveDisguise` window and log
(`STEALTH re-asserted`, gated print); if a non-InventoryItem is in hand → strip (§3.2). The
watchdog exits when phase ≥ 2.

### 3.7 Arming on blow (requirement 5)

`coverBlown` (phase 2 actions, run once):

1. `level.coop_stealthPhase = 2` (first — every gate opens synchronously);
2. restore card players (`enableEnemy 1`) and any other phase-1 actor protections;
3. `waitthread itemhandler.scr::coop_armPlayers` — the arming core **extracted** from
   `coop_armOnBlown` (clear flags → loadouts → activate weapon, order per 04 §2) so that BLOWN
   can arm without stripping disguises;
4. player-facing print ("Cover blown — weapons free!", kept per 04 §6).

`takeAllDisguises` keeps calling `coop_armOnBlown`, which now = `advance 2` (idempotent) +
disguise strip bookkeeping; the alarm hook additionally calls `alarmRaised` (= `advance 3`).
Post-BLOWN respawners need no special path: `coop_noWeapon` is cleared, so the normal loadout
pipeline arms them.

---

## 4. Per-file change list

| File | Change | Why |
|---|---|---|
| **`coop_mod/stealth.scr`** (NEW, ~150 lines) | `init` (phase 1, card protection, containment sweep, start watchdog), `onPlayerSpawn`, `coverBlown`, `alarmRaised`, `advance` (monotonic), `aggroAllowed`, roster-free watchdog, sentry accept-fallback watcher (§5.1) | single owner; everything else becomes a reader |
| `maps/m2l2a.scr` | `level.coop_stealthPhase = 1` + `coop_noWeapon`/`coop_startUnarmed`/`coop_forcePapersEquip` at load (cvar-gated, before `waitthread main`); remove the likeynorway strip block (route moved to load); add one `coverBlown` line before each retail bust site (§2.3.1); keep waitForEnemy rewrite + SP-gated salute flip + `cc_card_sentry` | route start moves to frame 1; scripted spots become transitions |
| `coop_mod/itemhandler.scr` | call `stealth::onPlayerSpawn` above the `:711` exit; extract `coop_armPlayers` from `coop_armOnBlown`; delete `coop_stealthArmOnHurt` (logic moves to stealth.scr, actually wired); demote `coop_stealthStripWeapons` to containment; move watchdog to stealth.scr; keep paperPassAll / papersAnytime / clickable-papers guard / takeall-removal (bug-1604) | fixes the respawn hole (04 §4.2), wires the dead failsafe (04 §4.1) |
| `coop_mod/aihandler.scr` | wrapper + replica + `:1262` restore site gate on `aggroAllowed`; **delete** the opt-in funnel guard (`coop_stealthFunnelGuard`) and its probe | closes the last raw site (04 §4.3); funnel guard proven unnecessary (04 §3) |
| `coop_mod/aisquad.scr`, `coop_mod/morale.scr` | keep verified stand-down; gate reads phase | one source of truth |
| `coop_mod/aimaneuver.scr` | add the same phase-1 stand-down | its `forceactivate` yanks scripted anims (03 §5) |
| `global/alarm_system.scr` | `ai_alarm_alerted` guard → whole-window (phase 1); alarm-ON hook additionally calls `alarmRaised` | fixes 04 §4.4; phase 3 entry |
| `global/cardgame.scr` | **revert** the 10:58 re-arm loop; add phase-gated eject in `checkresponse` (+ broken-cascade gate); keep the one-shot `coop_cardGameSitThink` guard and holster call | replaces the FAILED repair with prevention (§3.4); NIL-safe on the other 4 maps |
| `anim/disguise_enemy.scr`, `anim/disguise_halt.scr` | `thread stealth::coverBlown "engine-bust"` before the existing `[200]` insert | engine busts (officers, ignored/abandoned challenges) arm the players |
| `anim/disguise_accept.scr` | keep `coop_paperPassAll` thread | 04 #25 |
| `anim/disguise_salute.scr` | keep SALUTE probe until card room verified, then remove | 04 #24 |
| `autoexec.cfg` | remove TEMP `coop_aggroDebug`/`coop_bpDebug`, re-join the split comment | 04 §6 |
| `coop_defaults.cfg` | keep `seta coop_stealthStart 1`; **delete** `coop_stealthNoAggro`/`coop_stealthFunnelGuard` (subsumed by phase / deleted) | cvar surface: exactly one switch |
| release pass | gate/remove the ungated printlns listed in 04 §6; normalize the 8 stealth-session CRLF files (of 29 total) | 04 §4.7 |

## 4b. Session-work disposition (delta rows from 04 §1)

- **KEEP as-is**: #2 waitForEnemy rewrite, #3 SP-gated salute flip, #4 cc_card_sentry, #7
  takeall removal, #9 paperPassAll, #10 papersAnytime, #14 clickable-papers guard, #15
  weaponstate inventory-item rule, #18 replica gate, #19/#20 stand-downs, #22 ALARMTRIP guard
  (semantics aligned), #24/#25 anim hooks, #27 stealthStart seed.
- **REWORK**: #1 route trigger moves likeynorway→load; #6 papers re-give moves above :711 (into
  onPlayerSpawn); #8 armOnBlown split (armPlayers extracted); #11 strip demoted to containment;
  #12 watchdog roster-free + moved; #13 armOnHurt actually wired (in stealth.scr); #17 window
  flag → phase test; #21 :1262 gated.
- **REVERT/DELETE**: #16 funnel guard (+cvar), #23 cardgame re-arm loop, #26 TEMP debug seeds.
- Unrelated riders (m2l2b, collectible.scr BP guard, challenges, …) are out of scope — do not
  fold into this change set (03 provenance caveat).

---

## 5. 4-player specifics

1. **The player-0 sight trace** (`PassesTransitionConditions_Disguise` →
   `G_GetEntity(0)->centroid`, 02 §3.2): a challenge for player N only *starts* if the actor can
   see the host's chest. Script cannot fix the trace. Mitigations:
   - `coop_paperPassAll`: one successful check (by whoever the engine will check — usually the
     host) clears everyone and retires the checker.
   - **Script accept-fallback** (new, in stealth.scr, scoped to the two accept-thread sentries
     only): a watcher per gate sentry (goatsbutt, sentry2dude). If a player stands inside
     disguise_range with `level.papers >= <that sentry's level>` and *shows papers* (tracked by
     the script's own papers-use bookkeeping in `enableClickablePapers`/papersAnytime — script
     cannot read `m_ShowPapersTime`) for ≥ 5 s while the sentry has NOT entered a challenge, the
     watcher fires the retail accept thread itself (`sentry1trigdisable` / `sentry2accept`),
     retires the sentry (`type_disguise "none"`), and prints the accept feedback. This exactly
     reproduces the accept thread's world-effects (relay disarm, 05 §5) without the engine anim.
     Risk: no interrogation animation plays in the fallback path — cosmetic only.
   - Host-dead/disconnected during stealth: 02 §3.2 flags the missing-entity-0 crash hazard in
     the trace; on a listen server slot 0 exists while the server does. No script action.
2. **`attackplayer` confirms entity 0** (02 §3.3): post-BLOWN this is HEAD behavior and out of
   scope. (Noted option, not in this diff: migrate the wrapper to the HZM `attackentity`, which
   confirms the real target and does not set the poison flag.)
3. **Obstacle-bump / grenade-fallback engine poisons** target player 0 (02 §3.4/3.9): both are
   exempt while player 0 is disguised (`IsTeamMate`), which the watchdog guarantees during
   phase 1 by re-asserting the latch. Post-BLOWN they are HEAD behavior.
4. **Global `level.papers` / global BLOWN**: both are deliberate. One player tripping a bust
   arms and exposes everyone — requirement 5 reads cover as team-global. Players split across a
   scripted-spot boundary (A trips `sentry2trigger` while B is mid-interrogation elsewhere)
   resolve cleanly: phase 2 opens the gates, B's checker flips hostile via the engine's own
   disguise-lost/alarm logic — vanilla semantics, just simultaneous.
5. **Misc-AI-event suppression keys off player 0** (02 §3.5): irrelevant in phase 1 (no guns);
   HEAD behavior afterward.

---

## 6. Failure modes explicitly defended

| Failure mode | Defense |
|---|---|
| **One-way `m_bForceAttackPlayer` latch** fired by a mod system during stealth | complete gate inventory (§3.3) incl. the previously ungated `:1262`; only retail/scripted sites can latch, and each advances the phase first |
| **Thinkstate flicker ejecting card players** | `enableEnemy 0` (removes the flicker sources) + phase-gated eject (tolerates any residual flicker) + stand-downs (no `forceactivate`) |
| **Respawn during stealth** | `onPlayerSpawn` above the `:711` exit; roster-free watchdog; forceState re-assert on the fresh body |
| **Late join during stealth** | same path — managePlayerInventory runs on connect; watchdog picks the player up on the next tick |
| **Players split across scripted-spot boundaries** | monotonic global phase; transitions are idempotent and ordered before the retail `attackplayer` lines |
| **Alarm during stealth (switch, or ringer race)** | `advance 3` implies phase-2 arming if skipped; ringers blocked in phase 1, vanilla in phase 2+ |
| **World weapon pickup mid-stealth** | watchdog detects non-InventoryItem in hand → per-player strip; never silently leaves an armed "disguised" player (which the engine latch would otherwise tolerate, 02 §3.1) |
| **Boot-order race (gates read phase before init)** | phase var assigned before `waitthread main.scr::main` in the map script's first statements |
| **Player hurt by an actor while unarmed** | wired armOnHurt → `coverBlown` (actor-inflicted only; trigger_hurt exempt) |
| **Papers item lost on death** | per-spawn re-give of `level.coop_itemPapers` (papers2-aware) |

---

## 7. Open risks

1. **Card-stand root cause is still unidentified** (04 §5). The design makes the symptom
   impossible during phase 1 rather than explaining it; the SALUTE probe stays in until a clean
   4-player card-room run. If the pair still stands with `enableEnemy 0` + gated eject, the
   remaining suspects are anim-driven (`cardgame3anim` interplay), not thinkstate — new territory.
2. **Accept-fallback is an approximation**: no interrogation anim, and its "papers shown"
   signal is the script's own bookkeeping, not `m_ShowPapersTime`. Mis-timing risks a fallback
   accept the engine would have denied — mitigated by re-checking `level.papers` against the
   sentry's level at fire time (the only condition the engine itself checks, 05 §1).
3. **`enableEnemy 0` on card players** is untested against `chairdeath`/pain handling; verify a
   card-player kill during phase 1 still runs `cardplayersdeath` + survivors hostile (retail
   intent, requirement 3).
4. **DEPLOYED-UNVERIFIED session pieces retained** (paperPassAll, papersAnytime, waitForEnemy
   rewrite, per-spawn re-give) need their first measured runs; the 04 §3 ledger lists exactly
   what has never been observed (cover-blown re-arm mid-fight above all).
5. **Phase-2 "holster to calm" recovery** is better than the shipped model but subtly stronger
   than vanilla (in SP an active attacker also strips the flag for everyone; in coop the latch
   holds, so only latched actors stay hostile). Accepted as the closest script-only fit — the
   alternative (takeAllDisguises on every bust) contradicts vanilla's recoverable-bust design
   (05 §8, "completable fully disguised past the Naxos bust").
6. **Shared-file gating**: cardgame.scr and alarm_system.scr changes ride on `coop_stealthPhase`
   being NIL elsewhere; e1l3/e1l4 keep their own `coop_noWeapon`/disguise flows untouched
   (03 §10) — but e1l4 also runs alarm_system, so the whole-window `ai_alarm_alerted` guard must
   read the phase var (NIL there → vanilla), NOT `coop_enableDisguises`.
7. **Officer walking into the spawn/papers room during phase 1** ends in an engine bust the
   players cannot fight until `coverBlown` arms them (~1 frame later) — the 3 s ENEMY grace
   (02 §2.3) covers the arming latency, but a 4-player pile-up in a doorway with officer1 is the
   stress case to playtest.
8. Buglog hygiene: log the missing bug-1605/1607/1609 ids and the 10:38/10:58 events when
   implementation starts (04 §4.5/4.6).

## 8. Suggested verification plan (first playtest script)

1. Solo: full run — pickup → card room 5 min idle (seated?) → goatsbutt accept → Naxos blow
   (arms? scientists only hostile?) → papers2 → sentry2 accept → end.
2. Solo: alarm route — ring switch during phase 1 → phase 3, armed, disguise stripped, backups.
3. 2P: host hidden, client at sentry2 → does the fallback accept fire? client papers-show UX.
4. 2P: client death + respawn mid-stealth → papers/disguise/unarmed state on the fresh body.
5. 2P: one player trips `sentry1trig` while the other sits in the card room → both armed, card
   players stand (phase 2), goatsbutt runs for the switch.
6. 4P: officer1 corridor stress case (risk 7); STEALTHWATCH census attackers=0 for the whole
   phase-1 window.
