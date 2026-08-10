# m2l2a Definitive Coop Stealth — Design (lens: VANILLA-FIDELITY + VERIFICATION)

Date: 2026-08-09. Author basis: research docs 01–05 in this directory (cited as `01 §x` etc.),
`.wolf/buglog.json` bug-1604..1621, and the 54-guard entity dump
(`map_entities/m2l2a_parsed.txt`). This is a DESIGN — no code was changed to produce it.

The lens: every observable vanilla behavior of the mission becomes a numbered acceptance
check (AC). The design is the minimal mechanism set that makes every AC pass in coop, and
every AC gets a machine-parseable `^~^~^` log marker so a playtest is a pass/fail table, not
an anecdote.

---

## 0. Design principles and the four ruling engine facts

1. **`m_bForceAttackPlayer` is a one-way latch** (set actor.cpp:9294, cleared only in the
   Actor ctor at 3092; archived into saves — 02 §4). Therefore: *no emergent path may ever
   call `attackplayer` during the stealth window*. Only retail-scripted busts may. This is
   the single most important invariant; the 10:38 measurement (attackers 0/25 sustained with
   the three source gates on, funnel guard OFF — 04 §3) proves the gate set is sufficient.
2. **The coop disguise is a frozen engine latch** (player.cpp:5477–5495 is
   GT_SINGLE_PLAYER-only; the mod flips gametype for 1 ms to set `m_bIsDisguised`, then
   nothing engine-side ever clears it — 02 §3.1, 03 §1). Therefore: cover-blown is a
   *script-owned event*, and it needs exactly one owner.
3. **Every actor-side protection keys off the live flag** via the OR at actor.h:2161
   (threat 0, retained-at-zero-threat enemy, IsTeamMate, NoticeFootstep, curious suppression
   — 02 §1). Therefore: while the latch holds and no actor is poisoned, ambience is stable
   *by engine physics*, not by script effort. Script's only jobs are (a) don't poison
   anyone, (b) don't `forceactivate` posed actors, (c) decide when cover is blown.
4. **The papers handshake is per-player-correct already** (`m_ShowPapersTime` on the
   Sentient vs the actor's Begin snapshot — 02 §2); the two SP-hardcoded pieces are the
   challenge sight-trace to `G_GetEntity(0)` (actor.cpp:8994) and `level.m_iPapersLevel`
   being global (02 §3.2/3.6). The trace gets a one-line engine fix; the global papers level
   is *kept* as the coop semantic (one pickup upgrades the team — 05 §1 "measured design").

### Explicit design decisions (D#)

- **D1 — Weapons: unarmed from first spawn until BLOWN.** Requirement 5 verbatim ("NOBODY
  gets weapons until cover is confirmed blown or the alarm is raised"). Mechanism: arm
  `level.coop_noWeapon` at map load (the e1l3 papers-only recipe, 03 §10) so no loadout is
  ever granted, instead of the session's strip-at-pickup. `coop_stealthStripWeapons` is
  retained as a belt-and-braces sweep at pickup (armory carry-over, dropped-weapon pickups).
  This is a deliberate vanilla deviation (retail keeps all weapons and uses holstering — 01
  §3.2); the user requirement overrides, and the cvar `coop_stealthStart` keeps it optional.
  *Fallback if playtest dislikes it*: the session's verified strip-at-pickup order
  (bug-1607) still works under the same state machine — only the moment `coop_noWeapon`
  arms moves.
- **D2 — Cover-blown is terminal for the map.** Vanilla lets the disguise re-form after
  killing an isolated attacker or dousing the alarm; the shipped mod's model is "blown once
  = stealth over" (`takeAllDisguises` permanent — 03 §8). Keep the mod model: requirement 5
  makes weapons-return terminal anyway, and un-blowing is impossible per-actor (fact 1).
  Documented deviation: dousing the alarm still stops backups/sirens (AC-25) but does not
  restore stealth.
- **D3 — Scripted busts stay verbatim retail.** The seven retail `attackplayer` groups (01
  §2.7) are not touched, not gated, not softened. They are the "SCRIPTED" in requirement 3.
- **D4 — Whole-window aggro block, not per-target.** An undisguised-looking player (weapon
  scavenged, mid-give hiccup) must never permanently poison a guard (04 §4.4 rationale).
  During STEALTH, *all* mod-layer aggro paths are blocked regardless of target state; the
  alarm-runner path is deferred, not dropped (see §3.4).
- **D5 — One engine change** (E1, §5.11): retarget the challenge sight-trace from
  `G_GetEntity(0)` to `m_Enemy` with a NULL guard. Without it, requirement 3/4 are
  host-position-dependent for players 2–4 and a crash risk exists on empty slot 0 (02 §3.2).
  Everything else stays script-side.
- **D6 — Card players: prevent the ejection instead of repairing it.** The 10:58 re-arm
  loop FAILED in playtest (04 §5). Replace with a cause-filtered ejection condition inside
  `sitthink`, gated to the stealth phase so the other four cardgame maps are byte-identical
  in behavior (§3.5). Root cause still gets discriminated by the SALUTE/thinkstate probe
  before the fix is trusted (open risk R1).

---

## 1. Acceptance criteria — every observable vanilla behavior, numbered

Legend: **[V]** = vanilla-identical target; **[V±]** = vanilla-shaped with a documented coop
deviation; **[C]** = coop-only requirement (no vanilla analogue). Source citations point at
the research docs. Markers are defined in §6.

### Lifecycle / spawning

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-01 | Map loads; coop init single-frame; all connected players spawn at `info_player_start` (−4816 −3880 −36); every player engine-disguised (`eng_has=1`, `eng_is=1`) within 2 s of spawn | 01 §2.1, 03 §7 | [C] |
| AC-02 | Players spawn with NO weapons; papers not yet held; holstered hands | D1 | [C] |
| AC-03 | Respawn during STEALTH: fresh body unarmed, papers item re-given (post-pickup), papers equipped, disguise re-asserted within 2 s | 04 §4.2 hole | [C] |
| AC-04 | Late join during STEALTH: identical to AC-03; joiner never receives a loadout | 04 §4.2 | [C] |
| AC-05 | Player dead/spectating at the moment of a papers pickup still holds the correct papers item on next spawn | 05 §10 risk 3 | [C] |

### The pickup and papers UX

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-06 | One use-press on the locker trigger (−4427 −3995 −11) removes `$suit`+`$papers1`, completes objective 1, prints the papers hint, opens `$likeynorwaydoor` | 01 §2.2 | [V] |
| AC-07 | After pickup: ALL players hold `papers.tik`, `level.papers == 1`, all player models swap to `german_waffenss_officer` | 01 §2.2, 05 §3 | [V±] (fan-out to all players) |
| AC-08 | Any player can SHOW papers at will: primary fire with papers in hand plays the wave anim and stamps that player's `m_ShowPapersTime`; doing so never causes aggro (papers are an InventoryItem → disguise holds, weaponstate:56 rule) | 02 §2, 04 #10/#15 | [V] (requirement 2) |
| AC-09 | Norway locker-room conversation: both guards walk in, six lines play to completion, guards end non-hostile (coop: remain `type_disguise "none"`; SP: flip to salute) | 01 §2.2, 05 §3 | [V±] |

### Ambient stability (the heart of requirement 3/6)

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-10 | Attackers == 0 for the entire STEALTH window while no scripted bust has fired — sustained across the full 54-guard census, 1P and 4P | 04 §3 (10:38 run) | [C] |
| AC-11 | All three card players remain seated and playing for the entire STEALTH window; zero `cardhand01/02.tik` attach-retry lines in the log | 01 §2.3, 04 §5 | [V] |
| AC-12 | Salute-type guards (34) salute a player who walks within `disguise_range 256`, then resume; re-salute only after `disguise_period 15 s`; no escalation | 01 §1.3, §2.4 | [V] |
| AC-13 | `type_disguise "none"` actors (10: scientists, workers) fully ignore disguised players | 02 §6 | [V] |
| AC-14 | After `movetheflak` (−3875 −976 −438): crane run, welder/hammerer/wrench/crate work loops run uninterrupted; alarm-silent autosave analogue skipped in coop | 01 §2.8 | [V] |
| AC-15 | `sciencetrig` flavor scene: alarm silent → guy3 walks over, five VO lines, no detection; alarm up → immediate `attackplayer` | 01 §2.7 item 4 | [V] |

### Papers checks and the level-2 gate (requirement 4)

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-16 | Goatsbutt (−3912 −3480 −286, L1) challenges the *challenged* player: WAIT→PAPERS; papers shown → ACCEPT, `sentry1trigdisable` makes `$sentry1trig` nottriggerable, goatsbutt permanently demotes to salute | 01 §1.3, 05 §6 | [V] (needs E1 in 4P) |
| AC-17 | Ignoring a sentry challenge 12 s → ENEMY → 3 s → ATTACK (deliberate spot) | 02 §2 | [V] |
| AC-18 | Walking >256 away mid-challenge → HALT → 1.5 s → ATTACK (deliberate spot) | 02 §2 | [V] |
| AC-19 | sentry2dude (−2736 −6256 −494, **L2**) shown papers1 → DENY: wave-off anim, "You don't have the proper papers!", back to idle, re-challenge in 15 s, NO attack, NO alarm | 05 §5 | [V] |
| AC-20 | `$papers2` pickup (−3606 −6930 −268): papers1 item swapped for papers2 on ALL players, `level.papers == 2`, `$papers2hint` suppressed | 05 §4 | [V±] (global level is the coop semantic) |
| AC-21 | sentry2dude shown papers2 (by ANY player) → accept → `sentry2accept` → `$sentry2trigger` nottriggerable → gate open for everyone; sentry demotes to salute | 05 §5 | [V±] |
| AC-22 | Crossing the sentry2 line / swimming around, un-accepted → `sentry2thing`: leash 2048 + `attackplayer` (deliberate spot); the water `trigger_hurt` keeps hurting even post-accept | 05 §5 + correction 7 | [V] |
| AC-23 | Tripping the sentry1 net (−4072 −3104 / −4352 −3232) pre-accept → `sentry1alarm`: `den_alarm_01c` bark + `attackplayer` (deliberate spot) | 01 §2.7 item 1 | [V] |

### Officers (deliberate always-spot instances)

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-24 | Any officer interrogation that runs to completion ends hostile: papers shown → ENEMY instantly, ATTACK +3 s; not shown → ENEMY at 12 s, ATTACK +3 s (worst ≤15 s). No accept path exists. Staying ≥ range (256 / 64 for the mid-map officer) avoids the challenge entirely | 01 §1.3, corrections 2–3 | [V] |
| AC-25a | officer1 begins his south-pens patrol at `officer1go` after `movetheflak`; route verifiable against the coordinate table (§7) | 01 §2.8, 05 §7.1 | [V] |

### Scripted story busts

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-26 | Planting on `$naxos` (−4414 −1898 −124) → prototype destroyed, objective 2 complete, scientists guy1–3 `attackplayer` (unavoidable local bust) | 01 §2.7 item 3 | [V] |
| AC-27 | Killing any card player → surviving `$suckyfatty` `attackplayer` | 01 §2.7 item 5 | [V] |
| AC-28 | Alerted sledgehammer guy runs `cower` → arms P38 + `attackplayer`; alerted welders run `weldinginterupt` → arm P38, NO latch (fight by ordinary hostility) | 01 correction 1 | [V] |

### Alarm system

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-29 | A busted `$ai_alarm` actor races the player to the zone's switch and douses it → alarm ON. In coop this run is *deferred* until the director declares BLOWN (≤ ~1 s), never dropped | 01 §2.6, §3.4 below | [V±] |
| AC-30 | Alarm ON: `level.alarm = 1`, lights, sirens on all 13 `$alarm_sound` dummies, PA every 85 s, every disguise-thinker goes ATTACK, per-zone backups every 15 s capped 4 alive | 01 §2.6 | [V] |
| AC-31 | Any player can toggle a switch OFF: backups/sirens stop; (deviation D2) stealth does NOT resume | 01 §2.6, 03 §8 | [V±] |

### Cover-blown and endgame (requirement 5)

| AC | Behavior | Source | Class |
|---|---|---|---|
| AC-32 | The FIRST genuine attacker (any scripted bust, officer timeout, or alarm) → director declares BLOWN exactly once → `takeAllDisguises` → every active player receives their armory loadout within 2 s; players dead at that moment are armed on next spawn | 04 §2 unwind | [C] |
| AC-33 | Before BLOWN, no player ever holds a firearm (including respawners, late joiners, dropped-weapon pickups) | D1 | [C] |
| AC-34 | `$endlevel` (−2309 −4007 −408) → objective 3 complete → `missioncomplete.scr m2l2b` — reachable fully-stealth (papers2 route) AND post-blown (fight through) | 01 §2.8 | [V] |
| AC-35 | Worker deaths carry into m2l2b via `game.m2l2*dead` | 01 §2.8 | [V] |

---

## 2. Architecture: the stealth-phase state machine and its single owner

### 2.1 Owner

**NEW file `coop_mod/stealth.scr`** — the *only* writer of `level.coop_stealthPhase`.
Everything else (aihandler gates, aisquad/morale stand-downs, alarm defer, cardgame
ejection filter, itemhandler spawn hook) **reads** the phase; nothing else writes it.
Rationale: the session scattered the window condition across five files with three
different predicates (04 §4.4 "guard semantics are inconsistent"); one variable, one
writer, one place to instrument.

### 2.2 States

```
            map load, coop_stealthStart==1
  OFF ────────────────────────────────────────► STEALTH
   ▲                                              │
   │  (any other map / cvar 0:                    │  declareBlown(reason), exactly once:
   │   phase stays OFF, all gates inert,          │   - attacker census confirmed (2 ticks)
   │   zero behavior delta elsewhere)             │   - level.alarm == 1
                                                  ▼
                                               BLOWN   (terminal for the map, D2)
```

- `level.coop_stealthPhase` ∈ `"off" | "stealth" | "blown"`. Milestones *within* STEALTH
  are plain level flags, not states: `level.coop_stealthPapers` (1 after AC-07, 2 after
  AC-20) — they change what spawners are given, not how AI is gated.
- **OFF** is the default everywhere; every gate is written as
  `if (level.coop_stealthPhase == "stealth") …` so non-stealth maps and
  `coop_stealthStart 0` are provably unaffected (03 §10 load-bearing list).
- **STEALTH** starts at map load (D1), not at uniform pickup. The pickup is an event
  (AC-06/07), not a transition.
- **BLOWN** is entered exactly once via `stealth.scr::declareBlown <reason>`; it is the
  ONLY caller of `itemhandler::takeAllDisguises` on this map besides the alarm hook (which
  itself routes through declareBlown, §3.4). It re-arms players via the existing
  `coop_armOnBlown` chain (04 §2, unwind order verified).

### 2.3 The director thread (`stealth.scr::director`)

2 Hz loop, absorbing and replacing `coop_stealthHoldDisguise` + STEALTHWATCH (04 #12):

1. **Census**: over `level.coop_actorArray["german"]`: count actors whose thinkstate is
   `attack` AND whose `.enemy` is a player. (NOT `.enemy != NULL` — a disguised player is
   *retained* as a zero-threat enemy by actorenemy.cpp:446; that retained state must never
   read as engaged. This is the exact bug that made aisquad go loud, 03 §5.)
2. **Blown detection**: census ≥ 1 on two consecutive ticks (debounce = "confirmed" in
   requirement 5), OR `level.alarm == 1` → `declareBlown`.
3. **Disguise watchdog**: per player, if engine `is_disguised` reads false while phase is
   STEALTH → re-assert via the give window (the verified bug-1617/1618 machinery), marker
   `REASSERT`.
4. **Marker heartbeat**: `^~^~^ST CENSUS …` every tick while `coop_aggroDebug 1`, else
   every 10 s (§6).

The director exits after declaring BLOWN (nothing left to own; `coop_armOnBlown` handles
the unwind).

### 2.4 Spawn hook (`stealth.scr::onPlayerSpawn <player>`)

Called for every spawn/respawn/late-join while phase != OFF (wiring in §5.3). Closes the
04 §4.2 hole completely:

- phase STEALTH: assert no loadout arrived (noWeapon already blocks grants); if
  `level.coop_stealthPapers >= 1` re-give the current `level.coop_itemPapers` item and
  equip it (`coop_forcePapersEquip` path); run `setIsDisguised <p> true true`; if engine
  `is_disguised` false, run the per-player give window; emit `^~^~^ST SPAWN`.
- phase BLOWN: nothing (normal loadout pipeline owns it).

This also *replaces* the dead `coop_stealthArmOnHurt` (04 #13): being hurt while unarmed
no longer needs its own failsafe because BLOWN (the only source of legitimate damage-
dealing hostiles, given the gates) already re-arms everyone; environmental damage
(trigger_hurt water at sentry2) must NOT arm players. Delete the dead label.

---

## 3. Mechanisms per requirement (what makes each AC pass)

### 3.1 Aggro gating — requirement 3's "nobody unless scripted" (AC-10, 12, 13)

Keep the four VERIFIED source gates, re-conditioned onto the phase var (D4):

| Site | Session state (04 §1) | Design |
|---|---|---|
| `aihandler::attackPlayer` wrapper funnel guard | opt-in, verified unnecessary | **delete** (or keep dormant one release) — the source gates are sufficient and it sits in the papers-challenge path |
| `coop_spawnReplica` (#18) | gated, verified | keep; condition → `phase == "stealth"` |
| `aisquad` go-loud full stand-down (#19) | verified | keep; condition → phase |
| `morale` berserk stand-down (#20) | verified | keep; condition → phase |
| `setEnemyAttackStates` restore site aihandler:1262 | **ungated raw attackplayer** (04 §4.3) | **gate it identically** — it re-latches `coop_actorResetThinkstate` actors after give windows; during STEALTH, skip the `attackplayer`, keep the `enableEnemy` restore |
| `disguiseHandler` weapon-out detection (03 §4) | active | during STEALTH phase, its `attackPlayer` branch is inert by construction (players are unarmed, D1); leave the handler running for the post-pickup papers UX and the BLOWN transition — but its cascade calls must also check phase so a scavenged weapon cannot poison (D4) |

Retail scripted busts (D3) are raw `attackplayer` sites in `maps/m2l2a.scr` /
`global/cardgame.scr` / alarm plumbing and do **not** route through any of the gated
sites — they keep working untouched. That is exactly the requirement-3 split: mod-layer
emergent aggro gated, retail-scripted aggro live.

`forceactivate` discipline: the full stand-downs (not-even-forceactivate) are what got all
25 actors to idle and stopped the cardhand spam (04 §3). Any future AI-layer feature must
respect the same rule during STEALTH.

### 3.2 Unarmed window — requirement 5 (AC-02, 32, 33)

- Map load (coop branch): `level.coop_noWeapon = true` BEFORE any player can spawn
  (m2l2a.scr, right after `main.scr::main` returns). All four itemhandler grant sites
  already honor it (:711/:1549/:1584/:1710 — 04 correction 3).
- `likeynorway`: keep `coop_stealthStripWeapons` sweep (safety; also covers a host who
  changed the cvar mid-map) + `coop_forcePapersEquip` (papers-in-hand carry).
- BLOWN unwind (existing, keep): `coop_armOnBlown` clears `coop_startUnarmed` /
  `coop_noWeapon` / `coop_forcePapersEquip` FIRST, then re-gives armory loadouts, then
  `activatePlayerWeapon` (04 §2 order is load-bearing). Add markers (§6) because this leg
  was never measured (04 §3 last row).

### 3.3 Papers flow — requirements 2 and 4 (AC-06..08, 16, 19..21)

All shipped/verified machinery, kept:

- Item fan-out to all players + `givePapersFlagToAll` (05 §10).
- `weaponstate.scr:56` inventory-item rule (bug-1617, VERIFIED) — papers in hand never
  clears the disguise.
- `enableClickablePapers` + NIL/NULL guard (bug-1603, VERIFIED) — primary fire presents
  during interrogation.
- `coop_papersAnytime` (04 #10) — presentation outside interrogations; requirement 2
  verbatim. Verify in test plan (currently DEPLOYED-UNVERIFIED).
- `coop_paperPassAll` (04 #9/#25): on a sentry accept, wave the whole squad through and
  retire the guard via `type_disguise "none"`. **Rework note**: the engine already retires
  an accepting sentry (ACCEPT → think becomes SALUTE permanently, common.cpp:121–129), and
  the accept threads disarm the bust nets for everyone. Keep paperPassAll only if the
  4-player test shows players 2–4 being re-challenged in a way that reads as unfair;
  otherwise delete for fidelity (vanilla's demote-to-salute already means "the group is
  cleared").
- Level-2 gate: `papers2pickup` / `sentry2accept` / `sentry2thing` stay retail-verbatim
  (05 §4–5 confirms mod == retail here). `level.papers` stays global (D-accepted, 05 §1).

### 3.4 Alarm integration (AC-29..31)

- Keep the alarm-ON `takeAllDisguises` hook (alarm_system:701) but route it through
  `stealth.scr::declareBlown "alarm"` so BLOWN and the alarm can never disagree about
  ordering (declareBlown is idempotent).
- **Rework the ALARMTRIP guard** (bug-1616, 04 #22) from drop to **defer**: in
  `ai_alarm_alerted`, while `phase == "stealth"` and the census has not yet confirmed,
  wait (with a 3 s ceiling and liveness checks) instead of returning. The vanilla race to
  the switch (01 §2.6) then proceeds ~≤1 s after any genuine bust, preserving AC-29;
  a transient false alert (the case bug-1616 actually caught) evaporates because the actor
  leaves attack and the deferred run bails. This resolves the 04 §4.4 semantic
  inconsistency in the vanilla-faithful direction.

### 3.5 Card players + ambient NPCs — requirement 6 (AC-11, 09, 14)

Status: FAILED as of the last playtest (04 §5); treat as unsolved, design accordingly.

**Step 1 — discriminate the cause before trusting any fix (open risk R1).** The SALUTE
probe (04 #24) plus one added probe line inside `sitthink`'s exit path (log the exiting
`thinkstate` and `.enemy`) distinguishes the three candidate mechanisms (thinkstate
flicker / salute stall / disguise-transition capture). One 10-minute observation run
(TP-2 below) answers it.

**Step 2 — the fix (D6): filter the ejection, don't repair it.** Retail `sitthink`/
`checkresponse` eject on *any* per-frame thinkstate flicker because in SP a disguised
player provably never causes one (01 §2.3, §3.9). Coop does cause spurious flickers. So,
gated on `phase == "stealth"` (and ONLY then — cardgame.scr is shared by e2l2, m1l2a,
m4l2, m4l3; 03 §10):

- Replace the eject condition `self.thinkstate != "idle"` with *genuine-cause* ejection:
  `level.alarm`, self damaged (health < seated value / pain), table `broken`, death, or an
  undisguised player visible (`canseeUndisguisedPlayers`). A bare thinkstate excursion
  with none of those causes is waited out (actor stays seated; the anim driver was never
  deleted, so the loop resumes).
- Because the eject is prevented rather than reversed, the one-way parts of the retail
  stand path (`chairthread delete`, no re-seat anim) are never triggered — which is
  precisely why the 10:58 re-arm loop could not work: it ran *after* the one-way steps.
- Revert the 10:58 re-arm loop (04 #23) once this lands.
- The likeynorway coop branch keeping the two Norway guards `type_disguise "none"`
  (04 #3) is kept — it removes the salute-vs-walkto capture trap (04 §5) and satisfies
  AC-09.

**Fallback if Step 1 shows an anim stall** (missing salute anim for a voicetype —
04 §5 hypothesis): the guards in question get their voicetype normalized in the map's coop
branch (data fix, no engine work).

### 3.6 4-player specifics

1. **Challenge sight-trace** — E1 engine fix (§5.11). Without it: a sentry challenging
   player 3 silently never starts unless player 1 (slot 0) is also visible; with slot 0
   empty it can crash (02 §3.2). With it, AC-16/19/21 hold for whichever player is
   actually challenged.
2. **Census and gates are player-agnostic** — they iterate `$player` / actor arrays, no
   slot-0 assumptions.
3. **Players split across scripted-spot boundaries**: the bust nets are relays fired by
   volumes; ANY player crossing fires them for the team (vanilla semantic, kept). A player
   mid-papers-challenge while another trips the sentry2 line: the bust latches sentry2dude,
   his challenge collapses to ENEMY (02 §2 think exits), census → BLOWN. Correct and
   intended (AC-22).
4. **`level.papers` global**: one pickup upgrades all (AC-20). Dead/spectating players
   covered by the spawn hook re-give (AC-05).
5. **AI_EVENT player-0 suppression** (g_utils.cpp:1799): while phase is STEALTH all
   players are disguised, so the asymmetry is unobservable; post-BLOWN it is moot. No
   change.
6. **Obstacle-bump / grenade-fallback poison** (02 §3.4/3.9): both are exempt while
   player 0 is disguised (IsTeamMate), which holds for the whole STEALTH window; players
   are unarmed so no player grenades exist pre-BLOWN. No change needed; noted as R6.
7. **Zone/backup system**: the mod's alarm rework already tracks `level.playerZone_index`
   (05 §7.3); backups key off whichever player last touched a zone trigger. Acceptable
   vanilla-shaped behavior; verify in TP-4.

---

## 4. Disposition of existing session work (maps to 04 §1 rows)

**KEEP as-is** (verified or benign): rows 1 (stealth route — reworked only in *when*
noWeapon arms, D1), 2 (waitForEnemy rewrite), 3 (Norway guards none-in-coop), 4
(cc_card_sentry), 7 (takeall removal), 8 (armOnBlown hook), 10 (papersAnytime), 11
(strip), 14 (clickable-papers guard), 15 (weaponstate inventory-item rule), 17
(stealthBlocksAggro core — becomes phase-conditioned), 18 (replica gate), 19/20
(aisquad/morale stand-downs), 22 (ALARMTRIP → reworked to defer, §3.4), 24 (SALUTE probe,
until R1 closed), 25 (accept → paperPassAll, pending the §3.3 keep/delete decision), 27
(coop_stealthStart seed).

**REWORK**: row 6 (papers re-give → move into `stealth.scr::onPlayerSpawn`, above the
:711 early-exit problem entirely), row 12 (watchdog → absorbed into director), row 16
(funnel guard → delete/dormant), row 21 (gate aihandler:1262), row 22 (defer semantics).

**REVERT**: row 23 (cardgame re-arm loop — replaced by D6), row 26 (autoexec TEMP debug
seeds + re-join the split comment), row 13 (`coop_stealthArmOnHurt` — delete dead code,
superseded by §2.4).

**Not stealth, do not fold in** (04 §1 tail list): m2l2b Enigma work, collectible.scr
blueprint owner-guard defect, challenges batch, etc.

---

## 5. Per-file change list (implementer's map)

| # | File | Change | Why / AC |
|---|---|---|---|
| 5.1 | **NEW `coop_mod/stealth.scr`** | director thread (census, blown detection, watchdog, markers), `declareBlown`, `onPlayerSpawn`, phase var init from `coop_stealthStart` | §2; AC-01..05, 10, 32, 33 |
| 5.2 | `maps/m2l2a.scr` | coop branch: set phase + `coop_noWeapon` at load (D1); `likeynorway` keeps strip+forcePapersEquip but drops its own noWeapon arming; thread director; keep waitForEnemy rewrite, Norway-none gating, cc_card_sentry; add marker calls at likeynorway / papers2pickup / naxos / endmission | AC-02, 06, 07, 20, 26, 34 |
| 5.3 | `coop_mod/player.scr` (or `main.scr::startMapCallback` route) | invoke `stealth.scr::onPlayerSpawn` from the per-player spawn path when `level.coop_stealthPhase != "off"` — use the existing `level.coop_hasCallback["coop_playerJustSpawned"]` opt-in so non-stealth maps pay nothing | AC-03..05 |
| 5.4 | `coop_mod/itemhandler.scr` | delete the :745 in-place papers re-give (moved to 5.1); delete `coop_stealthArmOnHurt`; keep strip / armOnBlown / paperPassAll / papersAnytime / clickable guard; add BLOWN markers in `takeAllDisguises`+`coop_armOnBlown`; fix the stale :763 comment (04 correction 3) | AC-32, 33 |
| 5.5 | `coop_mod/aihandler.scr` | re-condition replica gate + wrapper onto phase var; **gate the :1262 raw attackplayer**; funnel guard deleted or dormant; disguiseHandler cascade calls check phase | AC-10; fact 1 |
| 5.6 | `coop_mod/aisquad.scr`, `coop_mod/morale.scr` | keep full stand-downs, condition → phase var | AC-10, 11 |
| 5.7 | `global/alarm_system.scr` | ALARMTRIP guard → defer-until-BLOWN (3 s ceiling); alarm-ON hook routes through `declareBlown "alarm"` | AC-29, 30, 32 |
| 5.8 | `global/cardgame.scr` | revert 10:58 re-arm loop; cause-filtered ejection in `sitthink`, gated `phase == "stealth"`; keep the one-shot lifetime guard; add exit-cause probe line | AC-11; D6; behavior-neutral for the other 4 maps |
| 5.9 | `anim/disguise_*.scr` | no change (keep [200] inserts + SALUTE probe until R1 closed) | AC-12, 16 |
| 5.10 | `autoexec.cfg` / `coop_defaults.cfg` | remove TEMP `coop_aggroDebug`/`coop_bpDebug` seeds (re-join split comment); keep `seta coop_stealthStart 1`; add `seta` + docs rows for any surviving stealth cvar; `coop_stealthNoAggro`/`coop_stealthFunnelGuard` disappear with their code | 04 §6 |
| 5.11 | **ENGINE** `openmohaa-hzm/code/fgame/actor.cpp` (~8994) | **E1**: sight-trace target `G_GetEntity(0)` → `m_Enemy` (with NULL fall-back to entity 0 for exact SP parity, and a NULL guard either way). fgame → ships in `game.dll`; follow the project's exe/cgame/game pairing rules for deploy | AC-16, 19, 21 in 4P; crash risk (02 §3.2) |

Optional/deferred engine items (NOT required for the ACs): grenade-fallback guard
(actor_grenade.cpp:349) and obstacle-bump blame — both exempt during STEALTH via
IsTeamMate; revisit only if post-BLOWN latching proves disruptive.

Everything script-side is CRLF, ASCII-only, no bare negatives in parens, run
`scratchpad/depthscan2.py` before deploy (TRAPS; 04 §4.7 notes 29 files pending LF→CRLF
normalization at release).

---

## 6. TEST PLAN — markers and the pass matrix

### 6.1 Marker grammar

All markers use the established machine-parseable prefix. Grammar:

```
^~^~^ST <TAG> k=v k=v ...
```

Emitted unconditionally (they are few and phase-scoped); the high-rate CENSUS line is
gated on `coop_aggroDebug`. Tags:

| TAG | Emitted by | Fields | Proves |
|---|---|---|---|
| `PHASE` | stealth.scr | `phase=stealth\|blown reason=<r> t=<level.time>` | state machine transitions, exactly-once |
| `SPAWN` | onPlayerSpawn | `p=<name> armed=0 papers=<0\|1\|2> eng_is=<0\|1> late=<0\|1>` | AC-01..05 |
| `CENSUS` | director | `attackers=<n> germans=<n> alarm=<0\|1> tick=<n>` | AC-10 (must read `attackers=0` every line pre-BLOWN) |
| `REASSERT` | director | `p=<name>` | watchdog fired (should be rare; >3/min = investigate) |
| `PICKUP` | m2l2a.scr | `what=papers1\|papers2 by=<name> papers=<lvl>` | AC-06/07/20 |
| `SHOW` | (existing engine chain, verified via) itemhandler | `p=<name>` on each activatepapers use | AC-08 |
| `ACCEPT` / `DENY` | accept threads + disguise_deny insert | `actor=<targetname> lvl=<n> papers=<lvl>` | AC-16, 19, 21 |
| `BUST` | wrappers at the retail bust threads (marker-only shims — one `println` line above each retail site, D3 code untouched) | `site=sentry1\|sentry2\|naxos\|cardkill\|cower\|officer-timeout` | AC-17, 18, 22, 23, 26, 27, 28 |
| `ALARM` | alarm_system | `state=on\|off by=<player\|ai> zone=<n>` + `DEFER`/`RUN` for the alarm-runner | AC-29..31 |
| `BLOWN` | declareBlown | `reason=<census\|alarm\|site> attackers=<n>` | AC-32 (must appear exactly once) |
| `ARMED` | coop_armOnBlown | `p=<name> kit=<weapon>` per player | AC-32/33 (closes the never-measured re-arm leg) |
| `CARD` | cardgame sitthink | `ev=seated\|flicker-held\|eject cause=<alarm\|pain\|broken\|seen\|death> p=<actor>` | AC-11 + R1 discrimination |
| `NPC` | movetheflak / sciencetalk / likeynorway conv | `scene=<name> ev=start\|done` | AC-09, 14, 15 |

### 6.2 Test procedures (each is one live run reading `%APPDATA%\openmohaa\maintt\qconsole.log`)

**TP-1 — 1-player golden path (full-stealth completion).** Spawn → pickup → goatsbutt
accept → movetheflak → naxos SKIPPED (walk past) → papers2 → sentry2 accept → endlevel.
PASS =
`PHASE stealth` once; every `SPAWN … armed=0 eng_is=1`; `CENSUS attackers=0` on every
line until end; `PICKUP papers1` then `papers2`; `ACCEPT actor=goatsbutt`,
`DENY actor=sentry2dude papers=1` (deliberately show papers1 once first),
`ACCEPT actor=sentry2dude papers=2`; zero `BUST`, zero `BLOWN`; `CARD ev=eject` count 0;
zero `cardhand` attach-retry lines; mission-complete banner. Covers AC-01, 02, 06-08,
10-14, 16, 19, 20, 21, 34.

**TP-2 — card-table soak + probe read (1P).** Stand in the card room 10 min, wander with
papers in hand, present papers repeatedly (AC-08 spam-safety). PASS = `CARD ev=eject`
count 0; every `CARD ev=flicker-held` line's `cause` field read and tallied (this run
CLOSES R1 — if ejects still occur, their `cause` field is the root-cause verdict).

**TP-3 — every scripted spot, deliberately (1P, six sub-runs or console-teleport).**
(a) trip sentry1 net pre-accept → `BUST site=sentry1` + `BLOWN reason=census` + every
player `ARMED`; (b) ignore goatsbutt 12 s → officer-style timeout → `BUST`/`BLOWN`;
(c) walk off mid-challenge → HALT → same; (d) engage officer1, show papers →
`BUST site=officer-timeout` ≤15 s; (e) plant naxos → `BUST site=naxos` ×3 scientists +
`BLOWN`; (f) kill a card player → `BUST site=cardkill` + survivors attack. Each sub-run
also PASSES only if `ALARM DEFER` → `ALARM RUN` appears when the busted actor is
`$ai_alarm` and the alarm actually rings (AC-29/30) — then toggle a switch OFF and
verify backups stop (AC-31). Covers AC-15 too (walk sciencetrig with alarm silent
beforehand: `NPC scene=sciencetalk ev=done`, no `BUST`).

**TP-4 — the 54-guard patrol sweep (1P, then 4P).** Using the §7 coordinate table:
teleport-patrol to within ~200 u of every guard cluster (the maptest phase-2 pattern,
CLAUDE.md), papers in hand, dwelling 10 s each. PASS = `CENSUS attackers=0` throughout;
`salute` markers/behavior observed at salute guards (visual); `DENY`/`ACCEPT` only at
the three sentries; officers avoided by the route (>256/>64) produce nothing. In 4P the
same sweep is run with players deliberately split into pairs at opposite map ends —
this is the E1 regression test: challenges must fire for the *nearby* pair with the host
parked out of line-of-sight behind the locker room. FAIL signature without E1: sentry
stares, no challenge, `CENSUS` still 0 (silent) — which is why the 4P sweep explicitly
asserts `ACCEPT/DENY` events occur, not just quiet.

**TP-5 — 4-player lifecycle churn.** During STEALTH: one player suicides and respawns
(AC-03), one disconnects and rejoins (AC-04), one stays dead through the papers2 pickup
then respawns (AC-05). PASS = every `SPAWN` line shows `armed=0`, correct `papers=`,
`eng_is=1`; no `REASSERT` storm; `CENSUS attackers=0` held throughout.

**TP-6 — 4-player blown-path.** Trip sentry2 net with all four alive, two players dead
variant second run. PASS = single `BLOWN`; `ARMED` ×(alive players) within 2 s; dead
players' next `SPAWN` shows `armed=1` (post-BLOWN spawns take the normal loadout path);
alarm rings via the deferred runner; backups spawn per zone.

### 6.3 1P vs 4P differences cheat-sheet

| Check | 1P expectation | 4P delta |
|---|---|---|
| Challenge initiation | fires for the solo player (slot 0 — works even without E1) | fires for whichever player is challenged — REQUIRES E1; assert ACCEPT/DENY events, not silence |
| CENSUS | attackers=0 | identical (gates are player-agnostic) |
| Replica clones | none (needs 2+ players) | clones spawn non-hostile during STEALTH (04 #18); post-BLOWN born hostile as shipped |
| papers level | global | global — one pickup upgrades all; assert via a second player's ACCEPT at sentry2 |
| Bust nets | tripping player = the only player | ANY player trips for the team; mid-challenge player sees the collapse (AC-22 note) |
| Spawn hook | trivial | carries AC-03/04/05 load |

---

## 7. The 54-guard coordinate table (from `map_entities/m2l2a_parsed.txt`)

Ground truth for TP-4 patrol waypoints and for verifying scripted patrols (officer1 route,
subsentrypath rover). Z range −632…−4; player start −4816 −3880 −36. Annotations from the
01/05 census (three entries are non-actor pickups/props that ride in the dump's AI grep).

| # | Class | X Y Z | Note |
|---|---|---|---|
| 1 | playerweapon_german_mp40 | −4626 −4227 −31 | (pickup, not an actor — must NOT be obtainable pre-BLOWN, AC-33) |
| 2 | ai_german_wehrmact_officer | −4048 −6048 −488 | **officer1** — always-spot, patrols after movetheflak (AC-24/25a) |
| 3 | ai_german_elite_sentry | −3912 −3480 −286 | **goatsbutt**, L1 sentry, accept=sentry1trigdisable (AC-16) |
| 4 | ai_german_kreigsmarine | −4016 −4884 −496 | salute |
| 5 | ai_german_wehrmact_soldier | −4200 −4196 −44 | salute (locker area) |
| 6 | ai_german_misc_worker | −4368 −1416 −500 | none-type (welder group) |
| 7 | interactobject_magazine… | −3926 −3922 −4 | (prop) |
| 8 | interactobject_magazine… | −3930 −4019 −4 | (prop) |
| 9 | ai_german_misc_worker | −4392 −1300 −496 | none-type |
| 10 | ai_german_wehrmact_soldier | −4156 −4176 −44 | salute |
| 11 | ai_german_kreigsmarine | −4120 −4940 −496 | salute |
| 12 | ai_german_misc_scientist | −4260 −2016 −168 | none; naxos bust trio (AC-26) |
| 13 | ai_german_misc_scientist | −4376 −2028 −164 | none; trio |
| 14 | ai_german_misc_scientist | −4304 −1992 −160 | none; trio |
| 15 | ai_german_wehrmact_soldier | −4096 −1004 −492 | salute (north/flak end) |
| 16 | ai_german_wehrmact_officer | −4016 −2820 −516 | **range-64 officer** — brush-past hazard (AC-24) |
| 17 | ai_german_kreigsmarine | −4460 −3488 −216 | salute |
| 18 | ai_german_kreigsmarine | −4316 −3640 −64 | salute |
| 19 | ai_german_kreigsmarine | −4632 −3508 −176 | salute |
| 20 | ai_german_kreigsmarine | −4172 −3260 −288 | salute (sentry1 net area — TP-3a) |
| 21 | ai_german_kreigsmarine | −4696 −3080 −288 | salute |
| 22 | ai_german_kreigsmarine | −4228 −2708 −492 | salute |
| 23 | ai_german_kreigsmarine | −4300 −1752 −492 | salute |
| 24 | ai_german_kreigsmarine | −4536 −1932 −492 | salute |
| 25 | ai_german_kreigsmarine | −4320 −1632 −492 | salute |
| 26 | ai_german_kreigsmarine | −3996 −956 −492 | salute |
| 27 | ai_german_kreigsmarine | −4072 −944 −492 | salute |
| 28 | ai_german_kreigsmarine | −4220 −980 −492 | salute |
| 29 | ai_german_kreigsmarine | −3928 −3668 −492 | salute (pens floor) |
| 30 | ai_german_kreigsmarine | −3928 −3960 −492 | salute |
| 31 | ai_german_kreigsmarine | −4044 −4036 −464 | salute |
| 32 | ai_german_wehrmact_soldier | −3892 −6116 −492 | salute (south wing) |
| 33 | ai_german_kreigsmarine | −4432 −2120 −492 | salute |
| 34 | ai_german_kreigsmarine | −4536 −2012 −492 | salute |
| 35 | ai_german_kreigsmarine | −3820 −1374 −494 | salute |
| 36 | ai_german_kreigsmarine | −3838 −1292 −494 | salute |
| 37 | ai_german_kreigsmarine | −3956 −5116 −488 | salute |
| 38 | ai_german_kreigsmarine | −3956 −4980 −488 | salute |
| 39 | ai_german_wehrmact_soldier | −4188 −4088 −36 | **card player** ($suckyfatty) — AC-11/27 |
| 40 | ai_german_wehrmact_soldier | −4132 −4096 −36 | **card player** |
| 41 | ai_german_wehrmact_soldier | −3941 −3960 −32 | **card player** |
| 42 | ai_german_misc_worker | −3261 −6063 −349 | none-type worker |
| 43 | ai_german_misc_worker | −3038 −4705 −598 | none-type worker |
| 44 | ai_german_misc_worker | −3200 −3368 −540 | none-type worker |
| 45 | ai_german_misc_worker | −2909 −5896 −494 | none-type worker |
| 46 | ai_german_misc_worker | −2345 −3624 −522 | none-type worker |
| 47 | ai_german_elite_sentry | −2736 −6256 −494 | **sentry2dude — the L2 gate** (AC-19/21/22) |
| 48 | ai_german_elite_sentry | −3692 −3892 −490 | roaming L1 sentry, subsentrypath |
| 49 | ai_german_kreigsmarine | −2276 −6708 −488 | salute (SE corner) |
| 50 | ai_german_kreigsmarine | −2324 −6764 −488 | salute |
| 51 | ai_german_kreigsmarine | −3788 −1340 −488 | salute |
| 52 | ai_german_kreigsmarine | −3788 −1268 −488 | salute |
| 53 | ai_german_kreigsmarine | −2548 −6652 −488 | salute |
| 54 | ai_german_misc_worker | −2184 −4156 −632 | none-type worker (lowest point) |

Suggested TP-4 patrol order (south-to-north sweep minimizing officer proximity):
start (−4816 −3880) → locker/card cluster (5,10,39–41) → sentry1 approach (3,20) →
mid-pens (29–31, 48) → science wing edge (12–14, keep >256 from #16) → north flak end
(15, 26–28, 6/9 welders) → back south corridor (33–34, 22–25) → south wing (32, 2 area —
observe officer1 from range) → papers2 office (−3606 −6930) → sentry2 (47) → SE corner
(49–50, 53) → endlevel (−2309 −4007).

---

## 8. Failure modes explicitly defended

| # | Failure mode | Defense |
|---|---|---|
| F1 | **One-way latch poisoning** (any `attackplayer` during stealth) | All five mod-layer sites gated on the phase var (incl. the previously-ungated aihandler:1262); retail sites are, by definition, the sanctioned spots; census confirms 0 attackers continuously (AC-10) |
| F2 | **Thinkstate flicker ejecting card players** | D6 cause-filtered ejection: a flicker with no genuine cause is held, never ejected; the one-way stand path is never entered |
| F3 | **Respawn during stealth** (armed body / no papers / cleared disguise) | `onPlayerSpawn` hook (§2.4); `coop_noWeapon` armed from load blocks any grant; watchdog re-asserts a dropped engine flag |
| F4 | **Late join during stealth** | same hook; joiner path identical to respawn (AC-04) |
| F5 | **Players split across scripted-spot boundaries** | busts are team-wide by relay design (vanilla); census → single idempotent BLOWN; mid-challenge player's collapse is the intended outcome |
| F6 | **Retained zero-threat enemy misread as "engaged"** | census counts thinkstate==attack only; aisquad/morale stand-downs stay for the whole window |
| F7 | **Alarm run dropped by the guard** (vanilla race lost) | defer-not-drop rework (§3.4) with a bail on de-escalation |
| F8 | **Host (slot 0) dead/absent breaking challenges or crashing** | E1 NULL-guarded m_Enemy trace |
| F9 | **BLOWN double-fire / ordering races** (alarm hook vs census) | `declareBlown` idempotent, single writer; alarm hook routes through it |
| F10 | **Scavenged weapon pre-BLOWN** (dropped MP40 pickup at #1, post-blown corpses N/A) | `coop_noWeapon` blocks grant paths; strip sweep at pickup; disguiseHandler weapon-out branch phase-gated so it can't poison — and AC-33 asserts the invariant in test |
| F11 | **Give-window races** (disguise re-assert while an actor mid-challenge) | existing serialization (`coop_disguisingInProgress` / `coop_changeGameTypeThread`) kept; REASSERT marker makes frequency visible |

---

## 9. Open risks

- **R1 — Card-player root cause is still unproven.** D6 removes the ejection trigger
  class, but if TP-2 shows ejects with cause `seen` or `pain` during a compliant run,
  something upstream is still perturbing them and the design needs another pass. The
  probe fields are in place to answer it in one run.
- **R2 — The BLOWN re-arm leg has never been measured** (04 §3 last row). TP-3/TP-6's
  `ARMED` markers are the closing evidence; until then treat `coop_armOnBlown` as
  DEPLOYED-UNVERIFIED.
- **R3 — E1 is an engine change** → game.dll build + deploy pairing; follow the
  turret-camera regression rule (diff every touched engine file vs original) and note the
  fork is on a detached HEAD. Scope is one function; still, ship it with a before/after
  TP-4 4P run.
- **R4 — `coop_paperPassAll` keep/delete decision** deferred to the 4P TP-4 result (§3.3).
- **R5 — D1 (unarmed from spawn) diverges from the verified 10:38 run** (which stripped
  at pickup). The state machine supports both; if the pre-pickup unarmed walk plays badly,
  fall back to strip-at-pickup without touching the rest of the design.
- **R6 — Post-BLOWN latch noise** (obstacle-bump / grenade-fallback poisoning against
  player 0) is out of scope here but documented in 02 §3; harmless to stealth, relevant to
  general combat fairness.
- **R7 — Ledger hygiene**: bug-1605/1607/1609 cited in comments but absent from
  buglog.json; the 10:38/10:58 events unlogged (04 §4.5/4.6). Implementation session must
  log them, plus this design's decisions to `docs/DECISIONS.md`.
- **R8 — Release pass**: 29 files pending CRLF normalization; TEMP debug seeds in
  autoexec.cfg; the §6 marker set must itself be reviewed for release gating (keep PHASE/
  BLOWN/ARMED, gate the rest on `coop_aggroDebug`).
