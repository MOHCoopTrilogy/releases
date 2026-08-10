# m2l2a Definitive Coop Stealth — ENGINE-FIRST Design

Design proposal, 2026-08-09. Lens: we may modify `openmohaa-hzm/code/fgame` (game.dll ships with
the mod). Evidence base: research docs 01–05 in this directory — cited as [01]…[05] with their
section numbers; the facts are theirs, not re-derived here.

---

## 0. Thesis

The shipped mod fights the engine because `m_bIsDisguised` is frozen in MP and the whole
detection stack was re-implemented in script on top of a one-way latch ([03] §1, §9). The
engine-first move is the opposite: **make the engine's own per-frame disguise maintenance run
per-player in coop, behind an opt-in level flag**, and delete the compensating machinery. Five
bounded fgame changes restore the retail stealth contract natively:

1. Per-player MP disguise maintenance (kills the `changeGameType` latch hack for disguise).
2. Retarget the challenge sight-trace from `G_GetEntity(0)` to `m_Enemy` (fixes the SP player-0
   assumption AND a live crash site) ([02] §3.2).
3. Retarget `attackplayer`'s confirm + the obstacle-bump / grenade-fallback blame from player 0
   to the actual player involved ([02] §3.3, §3.4, §3.9).
4. Fix `G_BroadcastAIEvent` suppression to check the event originator's disguise, not player 0's
   ([02] §3.5).
5. A script-facing latch reset (`forceattackplayer 0`) as a recovery tool — NOT used to bypass
   scripted spots.

Everything protocol-visible is untouched: these are all fgame (game.dll) server-side fields and
logic. **No exe or cgame change, no net-field change → game.dll-only ship** (the exe+cgame+game
triple-ship rule is not triggered).

The payoff is a three-phase stealth state machine whose middle phase — armed but re-stealthable
by holstering — is exactly retail's contract ([01] §3.2) and is only possible because the engine
recomputes `m_bIsDisguised` live. Requirement 4 (papers-2 like vanilla) is unreachable without
it: the Naxos bust is a scripted local cover-blow ([01] §2.7 item 3) that must arm the players
(req 5) yet must NOT end stealth, because the papers2/sentry2 gate comes after it in the mission
spine ([01] §2.8, [05] §8).

---

## 1. Architecture overview

```
                 ┌────────────────────────────────────────────────────────┐
                 │ ENGINE (fgame, gated on new Level flag m_bCoopDisguise) │
                 │  per-player m_bIsDisguised maintenance each Think       │
                 │  challenge trace → m_Enemy   attackplayer → real player │
                 │  AI-event suppression per-originator                    │
                 └───────────────▲────────────────────────┬───────────────┘
            level.coop_disguise=1│                        │ native senses: threat 0,
            has_disguise per plr │                        │ footsteps, curious/attack
                 ┌───────────────┴────────────────────────▼───────────────┐
                 │ SCRIPT: coop_mod/stealth.scr — SINGLE OWNER            │
                 │  phase: UNARMED → WEAPONS_LIVE → LOUD                  │
                 │  owns: level.coop_stealthPhase, arm/strip, blow watch  │
                 └───────────────┬────────────────────────────────────────┘
                                 │ gates (kept from session, verified 10:38 run [04] §3)
                 ┌───────────────▼────────────────────────────────────────┐
                 │ aihandler/aisquad/morale source gates + stand-downs    │
                 │ active while alarm off; retail attackplayer sites      │
                 │ NEVER gated (scripted spots, req 3)                    │
                 └────────────────────────────────────────────────────────┘
```

Division of labor after the change:

| Concern | Owner | What changes |
|---|---|---|
| Is player P disguised right now | **engine** (per-player maintenance) | was: frozen latch + script mirror `coop_isDisguised` |
| Detection of an undisguised player | **engine** (native transitions, footsteps, AI events) | was: `disguiseHandler` 1 Hz poll + cansee/hearing sims ([03] §4) |
| Papers show handshake | engine (already per-player-correct, [02] §2) | unchanged |
| Papers level | `level.papers` global (vanilla semantics, [05] §1) | unchanged — see §6.3 |
| Phase (when weapons exist) | **script**: `stealth.scr` | new single owner |
| Spurious mod go-loud sources | script gates (session work) | kept, one gap closed |
| Scripted spots | retail map script, untouched | req 3 |

---

## 2. Engine change list (file → change → why)

All paths `openmohaa-hzm/code/fgame/`. Every change carries `[user 2026-08-09]` comment tags.

### 2.1 `level.h` / `level.cpp` — the opt-in flag

- Add `qboolean m_bCoopDisguiseMaintain;` next to `m_bAlarm`/`m_iPapersLevel` (level.h:154–157
  area), init `false` at level.cpp:770 area.
- Script property `coop_disguise` (getter+setter, pattern-copy of `alarm` at level.cpp:91–108,
  2062–2070). Only disguise maps set it; every other map is bit-for-bit unaffected.
- Do NOT archive it (MP has no savegames; SP never sets it).

Why a Level flag and not a cvar: it must reset on map change automatically (m2l2b transition,
[05] §9) and be settable from the map script that owns the route.

### 2.2 `player.cpp` — per-player maintenance in MP

At the existing SP-only block (player.cpp:5477–5495, [02] §3.1), change the gate from
`g_gametype == GT_SINGLE_PLAYER` to
`g_gametype == GT_SINGLE_PLAYER || level.m_bCoopDisguiseMaintain`, keeping the body identical
**except** the attacker scan: it already iterates the TEAM_GERMAN sentient list checking
`m_Enemy == this` — that test is per-player-correct as written (each Player's Think checks
attackers *on himself*). Verify no other `this`-vs-entity-0 assumption inside the block; [02]
§3.1 records none.

Semantics gained, per player, every frame (exactly retail [01] §1.1):
- `has_disguise` && alarm silent && (no weapon || InventoryItem in hand) && no actor currently
  attacking *me* → disguised; otherwise not.
- Weapon drawn → undisguised for that player only. Holster → disguised again. This is the
  vanilla holster contract, live in coop, and it is what makes Phase 2 (§4) work.

Interaction with the old latch: on maps that do NOT set the flag, nothing changes — the
`changeGameType` trick still works for e1l3/e1l4 until they opt in ([03] §10).

Also extend `Player::UpdateEnemies` (player.cpp:5064–5114, [02] §3.7) gate the same way so
`m_fPlayerSightLevel` feeds actor visibility as in SP. Optional but keeps detection latency
vanilla-equal; if it misbehaves in testing it can be dropped without touching the design.

### 2.3 `actor.cpp` — `PassesTransitionConditions_Disguise` trace (the load-bearing fix)

actor.cpp:8994–9006 ([02] §2, [05] §2.1): replace `G_GetEntity(0)->centroid` with
`m_Enemy->centroid` (every other predicate in the function already uses `m_Enemy`), plus a NULL
guard. Effects:

- A sentry/officer/salute challenge now fires against the player it is actually retaining as
  enemy — players 2–4 get challenged (req 2, req 3).
- Removes the crash site when entity slot 0 is empty (dedicated / host-disconnected, [02] §3.2).
- Blast radius: the function only ever runs with a confirmed disguised enemy, so only disguise
  maps (m2l2a/m2l2b/e1l3/e1l4) can observe the change — and for a solo host, `m_Enemy` and
  entity 0 are the same body, so SP/solo behavior is identical.

### 2.4 `actor.cpp` — `attackplayer` retarget (latch SEMANTICS UNCHANGED)

`ForceAttackPlayer`/`EventAttackPlayer` (actor.cpp:9293–9309, [02] §3.3): keep the one-way
latch — scripted spots depend on it being permanent (req 3) — but confirm the **nearest living
player** (fallback: any living player; ScriptError only if none) instead of `G_GetEntity(0)`.
Precedent: the machinegunner nearest-living-player rework `[user 08-02]`
(actor_machinegunner.cpp:243–300, [02] §3.9). This is a global behavior change on every map
that calls `attackplayer` — the risk is confined to *which* player gets pre-confirmed, and
"nearest living" strictly dominates "slot 0 or throw" in coop. Do NOT add auto-clearing.

New script API on Actor, for recovery/design use only:
- `forceattackplayer 0|1` setter + getter (event pair next to EventAttackPlayer). Clearing does
  NOT un-confirm the enemy or leave ATTACK thinkstate; it only re-opens `EnemyIsDisguised()`
  (actor.h:2165). Document loudly: the mod must never call this inside a retail scripted-spot
  flow. Intended uses: post-alarm-douse experiments, card-player rescue (§7), dev tooling.

### 2.5 `actor.cpp` — obstacle-bump blame (actor.cpp:3354–3406)

The two branches blame entity 0 for any player's body-block ([02] §3.4). Change: blame the
actual blocking sentient — the branch already has the blocking entity in hand; pass it through
so the `IsTeamMate(p)` disguise exemption tests the *blocker*, and the ForceAttackPlayer confirm
(after 2.4) lands on the blocker if it latches. During the pre-alarm window our script gates
make this nearly unreachable anyway (players are unarmed and disguised → IsTeamMate true → no
latch), but a non-disguised player 0 must not be blamed for player 3's bump.

### 2.6 `actor_grenade.cpp:349` — grenade-fallback blame

`Begin_Grenade` no-grenade fallback ([02] §1 correction 1, §3.9): replace the
`IsTeamMate(G_GetEntity(0))` test with the actor's own `m_Enemy` if set, else skip the
ForceAttackPlayer entirely. The unreachable twin at :441 is left as-is (dead code).

### 2.7 `g_utils.cpp:1799–1803` — AI event suppression per-originator

`G_BroadcastAIEvent` suppresses misc events iff *player 0* is disguised ([02] §3.5). Change:
if the event's originating entity is a Player, test THAT player's `m_bIsDisguised`. With 2.2
live this makes gunshot/footstep-adjacent AI events per-player-correct natively, which retires
weaponstate.scr's `broadcastSound` gunshot simulation on maintained maps ([03] §3).

### 2.8 Explicitly NOT changed

- `State_Disguise_Papers` / `Fake_Papers` state machines, DENY/ACCEPT/ENEMY/HALT timing,
  officer no-accept rule — vanilla behavior is a requirement (req 3, [05] §2).
- ACCEPT's permanent downgrade-to-salute (common.cpp:127): kept. For m2l2a's gate-opening
  accept threads this is desirable — one player passes the check, the gate disarms for the
  team, the sentry salutes everyone after ([02] §7.4).
- `level.m_iPapersLevel` stays a level global — that IS vanilla (req 4; [05] §1 "coop
  consequence: measured design, not a bug"). A per-player papers level was considered and
  rejected: it changes vanilla semantics, adds an archive/protocol question, and the only
  level-2 consumer is one sentry whose accept disarms a *shared* trigger net anyway ([05] §5).
- `actorenemy.cpp:446` retained-zero-threat enemy: kept (retail behavior; the script layer
  already knows `.enemy != NULL` ≠ engaged, [03] §9.4).

---

## 3. Script-side architecture: `coop_mod/stealth.scr`, the single owner

New file. Nothing else writes `level.coop_stealthPhase`. All other systems *read* the phase or
subscribe via the event bus (`game.event doEvent "coop_stealthPhase"` on every transition,
eventsystem.scr pub/sub).

```
main:            called from maps/m2l2a.scr after main.scr::main (single frame, no waits)
                 sets level.coop_disguise = 1 (engine flag, §2.1)
                 phase = STEALTH_UNARMED; starts watch thread
watch:           2 Hz. Detects genuine blows (§4 transitions). Sole caller of armAll.
armAll:          -> coop_armOnBlown (itemhandler, reworked §5): clear noWeapon/forcePapersEquip/
                 startUnarmed, re-give armory loadouts, activate weapon
onAlarm:         event from alarm_system hook: phase = LOUD (terminal)
```

### The phase machine

| Phase | Entered by | Player weapons | Disguise | Mod aggro gates |
|---|---|---|---|---|
| `STEALTH_UNARMED` | map load | none (papers only) | engine-maintained, effectively always on (no weapon to draw) | ALL gated (replica/aisquad/morale stand-down + wrapper block) |
| `WEAPONS_LIVE` | first genuine blow: scripted latched attacker engages a player, or a player takes actor damage, or any german reaches ATTACK with a player enemy for >1 s | armed (armAll) | engine-maintained: weapon out = seen, holstered = disguised — **retail contract** | still gated (whole pre-alarm window — the verified semantics of `coop_stealthBlocksAggro` [04] §1 #17) |
| `LOUD` | `level.alarm == 1` (alarm_system hook → takeAllDisguises stays wired [03] §8) | armed | permanently stripped (`takeAllDisguises`) | lifted; combat AI fully live |

Why three phases and not two: req 5 forces unarmed until a blow; req 4 forces stealth to
survive the Naxos blow (papers2 + sentry2 come after it, [01] §2.8). Only the engine
maintenance makes the middle phase implementable without re-inventing the SP rules in script.

Transitions are one-way. `WEAPONS_LIVE` does not revert to `UNARMED` (weapons once given are
kept — req 5's "until" is a floor, not an oscillation), and re-stealthing inside
`WEAPONS_LIVE` is not a phase change: it is just the engine rule doing its job per player.

### Blow detection (the `watch` thread)

Sources, any of which fires `WEAPONS_LIVE`:
1. **Scripted-spot hook**: the `aihandler::attackPlayer` wrapper and the retail raw sites both
   result in an actor with `thinkstate == "attack"` and a player enemy; watch polls the german
   array for that (2 Hz, sustained one tick to skip transients).
2. **Damage failsafe**: wire the currently-dead `coop_stealthArmOnHurt` ([04] §4.1) into the
   player spawn path under `STEALTH_UNARMED` — a player taking actor damage while unarmed arms
   everyone even if the poll missed it.
3. **Alarm** (skips straight to `LOUD` via onAlarm).

This deliberately does NOT hook individual scripted busts by name — the engine-visible attack
state is the common denominator of all of them ([01] §2.7), so new/missed sites cannot strand
unarmed players.

---

## 4. Per-file mod change list

Baseline for verdicts: the session-delta table [04] §1. R = rework, K = keep, X = revert.

### `maps/m2l2a.scr`
- **R**: stealth route init moves from `likeynorway` to map load: after `main.scr::main`,
  `waitthread coop_mod/stealth.scr::main` (sets `level.coop_disguise`, `coop_noWeapon`,
  `coop_forcePapersEquip`, `coop_startUnarmed`, phase). Players are unarmed from first spawn
  (req 5 verbatim) — this supersedes the strip-at-pickup ordering that cost bugs 1604/1606/1607
  ([04] §2). `coop_stealthStripWeapons` is kept and called once defensively at init (armory
  edge: a weapon granted before the flag lands).
- **K**: `likeynorway` keeps: papers item + uniform adds (vanilla), coop papers hint, the
  SP-gating of the guards' `type_disguise "salute"` flip (#3), `waitForEnemy` rewrite (#2 —
  now verify; with engine maintenance its `canseeUndisguisedPlayers` exit condition becomes
  meaningful pre-blow only if someone is mid-`WEAPONS_LIVE` with a drawn gun — correct).
- **K untouched**: `papers2pickup`, `sentry2accept`, `sentry2thing`, `sentry1alarm`,
  `cardplayersdeath`, Naxos chain — all retail scripted spots (req 3, [05] §4–7).
- **K**: `cc_card_sentry` bump (#4), `coop_baked_0808` placements (#5) — not stealth.

### `coop_mod/itemhandler.scr`
- **R**: `managePlayerInventory` papers-ITEM re-give (#6) moves ABOVE the `:711`
  `coop_noWeapon` early-exit — [04] §1 #6 / §4.2 showed it is unreachable exactly when needed.
  Respawn/late-join sequence under stealth becomes: (no loadout) → re-give
  `level.coop_itemPapers` → `has_disguise = true` (plain setter — **no changeGameType window
  needed anymore**, the engine recomputes from it next Think) → `coop_forcePapersEquip` hook
  draws papers.
- **R**: `giveDisguise`/`giveDisguiseToAll`/`takeDisguise` grow a fast path: when
  `level.coop_disguise` is set, just set/clear `has_disguise` per player and end — no window,
  no weapon deactivation, no thinkstate dance. The window path remains for non-opted-in maps
  (e1l3/e1l4) — `changeGameType` itself is untouched (load-bearing for `giveInventory` and
  `coop_reissueMissionItems`, [03] §10).
- **R**: `coop_armOnBlown` decouples from `takeAllDisguises`: it becomes the `WEAPONS_LIVE`
  action (called by stealth.scr), while `takeAllDisguises` stays the alarm/LOUD choke point
  and *also* calls armAll if weapons were not yet issued (alarm during `STEALTH_UNARMED`).
- **R**: `coop_stealthArmOnHurt` wired (dead → §3 source 2). `coop_stealthHoldDisguise`
  watchdog demoted to a `coop_aggroDebug`-gated census instrument (#12) — with engine
  maintenance a script re-assert would fight the engine; it must observe, not write.
- **K**: `coop_paperPassAll` (#9), `coop_papersAnytime` (#10), `enableClickablePapers` NIL
  guard (#14), stealth-start comment / takeall removal (#7).
- **X**: `coop_stealthFunnelGuard` (#16) deleted — verified unnecessary (10:38 run) and it
  sits in the papers-challenge path.

### `coop_mod/weaponstate.scr`
- **K** bookkeeping (untouchable, [03] §10). Disguise tail (`setIsDisguised`) and the
  gunshot-heard simulation (:65–89) get a `level.coop_disguise` bypass: on maintained maps the
  engine does both natively (§2.2, §2.7). Keep for non-opted-in disguise maps.

### `coop_mod/aihandler.scr`
- **K**: `coop_stealthBlocksAggro` whole-pre-alarm-window block (#17), replica gate (#18) —
  the verified core ([04] §3). Semantics restated under the new design: it gates the MOD's
  spurious sources; retail scripted sites never route through it (req 3 preserved).
- **R**: gate the `setEnemyAttackStates` raw `attackplayer` at :1262 like the other three
  sites ([04] §4.3) — with the window path retired on this map it should be unreachable, but
  the latch is one-way; belt and braces.
- **R**: `disguiseHandler` gains an early-exit when `level.coop_disguise` is set — its 1 Hz
  cansee/hearing cascades are the script reimplementation the engine now provides. (Keep it
  live for e1l3/e1l4.)

### `coop_mod/aisquad.scr`, `coop_mod/morale.scr`
- **K**: full stand-downs during the pre-alarm window (#19, #20 — verified; they also cured
  the `forceactivate` scripted-anim yanking and the cardhand spam [04] §3).

### `global/alarm_system.scr`
- **K**: `takeAllDisguises` hook (mod :701) and the ALARMTRIP guard (#22), **R**: align
  ALARMTRIP to whole-window semantics ([04] §4.4) — an undisguised-but-innocent player (drawn
  weapon mid-`WEAPONS_LIVE` is legitimate) must trip it, but during `STEALTH_UNARMED` nobody
  can be legitimately undisguised, so gate on phase, not per-target.

### `global/cardgame.scr`
- **X**: revert the failed sitthink re-arm loop (#23 — measured not holding) back to the
  HEAD one-shot + guard shape. Then re-test under the new engine flags (§7). Keep the SALUTE
  probe (#24) until the standing-pair mechanism is identified. Any change must stay
  behavior-neutral for e2l2/m1l2a/m4l2/m4l3 ([03] §10).

### `anim/disguise_*.scr`
- **K** as-is. The `[200]` coop inserts key off `canseeUndisguisedPlayers`, which is
  phase-correct under the new model (nobody undisguised in `STEALTH_UNARMED`; genuinely
  undisguised players in `WEAPONS_LIVE` should be reacted to). `disguise_accept.scr` →
  `coop_paperPassAll` thread kept (#25).

### `autoexec.cfg` / `coop_defaults.cfg`
- **X**: TEMP `coop_aggroDebug`/`coop_bpDebug` lines + re-join the split comment (#26).
- **K**: `seta coop_stealthStart 1` (#27). Decide seeds for `coop_stealthNoAggro` (rename to
  match `coop_stealthBlocksAggro` or drop the alias) per [04] §6; document all in the cvar
  table so docgen picks them up.

---

## 5. 4-player specifics

1. **Spawns/respawns/late joins (req 1)**: identical path — spawn under `STEALTH_UNARMED` is
   loadout-less (`:711` early-out), papers-ITEM re-give (now above the exit), plain
   `has_disguise = true`, `forcePapersEquip`. No window, no serialization, no watchdog
   dependence — the engine recomputes the player's disguise on his first Think. During
   `WEAPONS_LIVE`/`LOUD`, `coop_noWeapon` is cleared so spawns get normal armory loadouts.
2. **Challenges target the right player**: §2.3 makes every actor challenge its own retained
   enemy. Four players can be in four simultaneous challenges; `m_ShowPapersTime` is already
   per-player ([02] §2) and `enableClickablePapers` is per-player script.
3. **Split across scripted-spot boundaries**: player A showing papers at sentry2 while player
   B crosses the trip line: vanilla-legal outcomes preserved — B's crossing fires
   `sentry2thing` (bust latch) unless A's accept has already run `sentry2accept`
   (`nottriggerable` on the relay disarms all three volumes for everyone, [05] §5). The bust
   is a scripted spot → watch fires `WEAPONS_LIVE`. The trigger_hurt keeps hurting swimmers
   after accept (retail behavior, [05] correction 7) — leave it.
4. **Per-player blow, team-level arming**: a scientist latched onto player A un-disguises A
   only (engine per-player rule) but arms the whole team (req 5's "nobody gets weapons until
   blown" flips to "everyone armed on first blow" — one shared phase, no per-player arming
   asymmetry to reason about). B/C/D remain disguised while holstered.
5. **AI-event fairness**: §2.7 makes player 2's gunshot audible even while player 1 is
   disguised (was suppressed team-wide by the player-0 check).
6. **Officer hazards**: unchanged vanilla — officers bust whoever they retain, spacing is the
   counterplay ([01] §2.7 tail). With 4 players spread out, officer1's patrol will genuinely
   challenge whoever is nearest; that ends in a scripted-spot-equivalent blow (ENEMY→ATTACK)
   → `WEAPONS_LIVE`. This matches "deliberate always-spot instances still work" (req 3).

---

## 6. Requirements traceability

| Req | Where satisfied |
|---|---|
| 1. 4 players spawn/respawn/late-join | §5.1; engine maintenance removes the window/race machinery that made spawns fragile ([04] §4.2) |
| 2. Everyone holds + shows papers at will | papers fan-out + re-give ([05] §10), `coop_papersAnytime` kept, `m_ShowPapersTime` per-player, challenges reach players 2–4 via §2.3 |
| 3. No unscripted spotting; scripted spots exact | pre-alarm gates on mod sources only; retail `attackplayer` sites untouched; latch semantics unchanged (§2.4); officer/sentry state machines untouched (§2.8) |
| 4. Papers-2 like vanilla | `level.papers` global kept (§2.8); `papers2pickup`/`sentry2accept`/`sentry2thing` untouched; stealth survives Naxos via `WEAPONS_LIVE` holster contract (§3) |
| 5. No weapons until blown/alarm | `STEALTH_UNARMED` from map load; armAll on first genuine blow or alarm; damage failsafe wired (§3) |
| 6. Ambient NPCs behave | stand-downs kept (verified: 25/25 idle, cardhand spam gone [04] §3); per-player engine senses remove the flicker sources ([03] §9.2); card table = open risk (§7) |

---

## 7. Failure modes explicitly defended

1. **The one-way latch** (`m_bForceAttackPlayer`): all four mod-side spurious sources gated
   (three verified + `setEnemyAttackStates` closed, §4); engine bump/grenade blame retargeted
   (§2.5–2.6) so an innocent disguised player can't latch a patroller; scripted latches are
   *intended* and arm the team via the watch. Recovery exists (`forceattackplayer 0`) but is
   policy-restricted to non-retail flows.
2. **Thinkstate flicker vs scripted anims**: stand-downs remove `forceactivate` yanking; per-
   player live disguise removes the "undisguised player 0 view" that drove curious flickers;
   AI-event suppression now per-originator. Card players are `type_disguise none` → never
   challenge ([02] §6); with zero threat + no footstep notice + no misc events, their
   thinkstate has no remaining legitimate exit pre-blow. If the standing-pair bug persists
   after the revert (§4 cardgame), the SALUTE probe discriminates the three candidate
   mechanisms ([04] §5); an engine-side `forceattackplayer 0`-style rescue or a scripted
   re-seat is the fallback — **treat as open until a playtest passes**.
3. **Respawn during stealth / late join**: §5.1; no per-spawn window; watchdog is read-only.
4. **Players split across scripted-spot boundaries**: §5.3 — outcomes are the vanilla ones,
   and any bust resolves to a phase everyone shares.
5. **Host slot-0 death/disconnect**: §2.3 removes both the silent-never-challenges failure and
   the NULL-deref crash ([02] §3.2, [05] §10 risk 1).
6. **Alarm mid-challenge**: engine already forces mid-challenge actors to ATTACK on alarm
   ([02] §7.2d); phase machine reaches `LOUD` via the hook, players are armed by then or
   armAll runs inside `takeAllDisguises` (§4 itemhandler).
7. **Map transition**: papers items are engine-stripped at transition and `m_iPapersLevel`
   re-inits ([05] §9); `level.coop_disguise` is a Level field → auto-resets; m2l2b opts in
   with its own `stealth.scr::main` call when we port the route (out of scope here).
8. **Blowing other maps up**: every engine change is either gated on the new flag (§2.2) or
   only reachable with a disguised enemy (§2.3) or strictly-better targeting of an existing
   coop-broken path (§2.4–2.7). Non-disguise maps cannot observe §2.2/§2.3; §2.4–2.7 change
   only *which* player is blamed/confirmed — smoke-test the maptest Phase 2 rotation anyway.

---

## 8. What ships, build order, verification plan

- **Engine**: game.dll only (all fgame). No protocol constants, no new net fields → no
  exe/cgame pairing required. Note: game.dll deploys to the GOG root manually (memory:
  lobby build note), not via build.ps1's cgame path — follow the usual game.dll deploy step.
- **Mod**: `build.ps1` as usual after script changes.
- **Order**: (1) engine flag + player.cpp maintenance + trace fix, behind the flag, verify on
  a solo listen server that m2l2a still plays; (2) stealth.scr + itemhandler rework, single
  player run of the full spine (papers1 → sentries → Naxos → papers2 → sentry2 → endlevel);
  (3) 4-player session: late join + respawn during `STEALTH_UNARMED`, split-boundary tests at
  both checkpoints, officer challenge on a non-host player; (4) card-table observation run
  with the SALUTE probe captured; (5) maptest rotation smoke for regression.
- **Measurements to demand** (extend the [04] §3 ledger): attackers=0 sustained pre-blow with
  engine maintenance ON; a non-host player receiving a sentry challenge (log the trace fix);
  `WEAPONS_LIVE` arming < 1 s after the Naxos bust; holster-re-stealth working post-Naxos
  (`eng_is` flips 0→1 on holster); alarm→LOUD strip; respawn mid-stealth holding papers.

---

## 9. Open risks

1. **Card table remains unsolved** — the design removes the known perturbation sources but the
   08-09 standing pair is unexplained; do not claim the fix until the probe run passes ([04] §5).
2. **Behavior deltas from live maintenance**: on the opted-in map, actors now *natively* react
   to a drawn weapon (pre-alarm, `WEAPONS_LIVE`) faster than the old 1 Hz script poll — tuning
   surprises possible; the stand-downs mask squad spread until alarm, which may read as
   "guards shoot but friends don't react" in `WEAPONS_LIVE`. Acceptable v1; revisit gates then.
3. **`UpdateEnemies` in MP** (§2.2 optional part) has never run in coop; sight-level feedback
   could make actors confirm faster everywhere on the map. Ship it OFF (separate flag or skip)
   if any doubt.
4. **e1l3/e1l4 divergence**: two disguise stacks coexist until those maps opt in — the gates
   in shared files (`weaponstate`, `aihandler`, `disguise_*.scr`) must stay correct for both;
   every bypass in §4 is conditioned on `level.coop_disguise` for exactly this reason.
5. **`attackplayer` retarget** (§2.4) is the one unconditional cross-map engine change; the
   maptest sweep is the mitigation. If it scares us at release time, gate it on
   `g_gametype != GT_SINGLE_PLAYER` (SP keeps entity-0 semantics identically).
6. **Papers UX under simultaneous challenges** (4 players, one `enableClickablePapers` design
   written for one interrogation at a time) — verify concurrency; worst case is a missed
   primary-fire → DENY/ENEMY path, which is survivable and vanilla-shaped.
