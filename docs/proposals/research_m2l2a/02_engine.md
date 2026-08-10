# Engine Disguise Machinery — Authoritative Reference

## CORRECTIONS (verification pass)

Adversarial re-verification 2026-08-09 (independent read of every cited line, grep sweeps,
Pak0 papers.tik extraction, m2l2a entity-dump recount). Claims 0-3 data model, EnemyIsDisguised
logic, the MP latch, the papers timestamp handshake, the player-0 breakage list, the
`type_disguise none` semantics and the HALT/ENEMY no-success-exit machinery all verified
exactly as written. Three defects were found and fixed in the body below:

1. **`ForceAttackPlayer()` has FIVE call sites, not three** (section 4, section 3 item 9,
   section 7 item 3). The doc claimed script `attackplayer` + the two obstacle-bump branches
   were "exactly three places". Grep shows two more in `Begin_Grenade`:
   **actor_grenade.cpp:349 is a LIVE fourth site** — a TEAM_GERMAN actor entering the grenade
   thinkstate whose `m_pGrenade` has meanwhile become NULL runs
   `if (!IsTeamMate(G_GetEntity(0))) ForceAttackPlayer();` (336-354). A disguised player 0 is
   exempt (IsTeamMate returns true for disguised sentients), but if player 0 is *not*
   disguised the actor poisons itself with no script call and no obstacle bump involved.
   actor_grenade.cpp:441 is a fifth, unreachable site (dead `else` of the always-true
   `if (m_pGrenade)` at 362 after the early return at 342-354). Section 3 item 9 had
   mislabeled both as mere "IsTeamMate tests" in flee/martyr decisions.
2. **m2l2a census was inverted** (sections 5 and 6). Actual counts from
   map_entities/m2l2a_entities.txt: **34 salute, 10 none, 3 sentry, 2 officer** — salute, not
   "none", is the rank-and-file majority. And the doc missed that the second sentry
   (entities.txt:7405) is **`disguise_level 2`** with its own accept thread
   `"sentry2accept"` (7416, 7419) — so "m2l2a sets disguise_level 1 on its checkers" was
   wrong, and `level.papers` must reach 2 for that checkpoint. Third sentry (7706) is level 1
   with no accept thread.
3. **Section 7 item 2 said "only three ways a disguised player gets shot", omitting the alarm
   path** that section 1 itself documents: with `level.m_bAlarm` set (script-settable in coop
   while the latch holds), every `Begin_Disguise*` re-validation and every `Think_Disguise*`
   does a direct `SetThinkState(ATTACK)` even while `EnemyIsDisguised()` is still true
   (salute.cpp:94, sentry.cpp:97, officer.cpp:98, rover.cpp:98). Added as way (d).

Everything else was left untouched. Line-number spot checks that all passed: actor.h:2159-2174,
player.cpp:5477-5499, actorenemy.cpp:164/446/478/505, actor.cpp:2984/3092/4033/6906/9996/
8868-8871/8941/8955-9007/9034/9294/9302-9309/9351, inventoryitem.cpp:81-84, common.cpp all
states, g_utils.cpp:1798-1803, level.h:154/157, level.cpp:769-770, sentient.cpp:869-871/4018,
Pak0 models/items/papers.tik activatepapers frames 30/40/50/60/70.

---

Research artifact for the m2l2a stealth-route work (2026-08-09). All citations are
`openmohaa-hzm/code/fgame/<file>:<line>` in the current working tree (HEAD = v1.2.3 baseline
plus uncommitted `[user 2026-08-0x]` changes; line numbers verified by direct read this session).
Read-only reference — no code was modified.

---

## 0. Data model: who holds which field

| Field | Holder | Init / default | Cite |
|---|---|---|---|
| `m_bIsDisguised` | `Sentient` (so Player and Actor both have it) | `false` | sentient.h:205, sentient.cpp:869 |
| `m_bHasDisguise` | `Sentient` | `false` | sentient.h:206, sentient.cpp:870 |
| `m_ShowPapersTime` | `Sentient` (per-player, inttime of last papers wave) | `0` | sentient.h:208, sentient.cpp:871 |
| `m_fPlayerSightLevel` | `Sentient` (adds into actor visibility) | — | actorenemy.cpp:120 |
| `m_bEnemyIsDisguised` | `Actor` (cached per-actor view of its enemy) | `false` | actor.h:722, actor.cpp:2984 |
| `m_bForceAttackPlayer` | `Actor` | `false` (ctor ONLY) | actor.h:728, actor.cpp:3092 |
| `m_iNextDisguiseTime` | `Actor` (cooldown gate for the disguise thinkstate) | `1` | actor.h:792, actor.cpp:3024 |
| `m_iDisguisePeriod` | `Actor` (ms) | `30000` | actor.h:794, actor.cpp:3025 |
| `m_fMaxDisguiseDistSquared` | `Actor` (stored squared) | `Square(256)` | actor.h:796, actor.cpp:3026 |
| `m_iEnemyShowPapersTime` | `Actor` (snapshot of enemy's ShowPapersTime at challenge start) | `0` | actor.h:798, actor.cpp:2896 |
| `m_DisguiseAcceptThread` | `Actor` (ScriptThreadLabel) | unset | actor.h:800 |
| `m_iDisguiseLevel` | `Actor` (1 or 2 only) | `1` | actor.h:802, actor.cpp:3027 |
| `m_iPapersLevel` | **`Level` (GLOBAL, not per-player)** | `0` | level.h:157, level.cpp:770 |
| `m_bAlarm` | `Level` (global) | `false` | level.h:154, level.cpp:769 |

Script bindings:

- Player: `is_disguised` is **EV_GETTER only** (player.cpp:1149-1158 -> `GetIsDisguised`
  player.cpp:11348); `has_disguise` has both getter and setter (player.cpp:1159-1178 ->
  player.cpp:11353-11361). Script can grant the disguise but can never set the live flag.
- Actor: `type_disguise` (actor.cpp:762-788 -> `EventSetTypeDisguise` actor.cpp:8227),
  `disguise_level` (789-815 -> 8282), `disguise_range` (stored squared, 9214-9218),
  `disguise_period` (seconds -> ms, 9235-9238), `disguise_accept_thread` (1062-1088 -> 8248).
- Level: `level.papers` (level.cpp:163-181 -> get 2092 / set 2097), `level.alarm`
  (level.cpp:91-108 -> set 2069).
- Papers are `InventoryItem : public Weapon` (inventoryitem.cpp:47, item name map item.cpp:45).

`m_bForceAttackPlayer` is archived into savegames (actor.h:1949) — it even survives SP
save/load.

---

## 1. Full input set: when does an actor NOT attack a disguised player

The single decider is the inline `Actor::EnemyIsDisguised()` (actor.h:2159-2174):

```
returns TRUE (protected) iff:
    (m_bEnemyIsDisguised  OR  m_Enemy->m_bIsDisguised)      // actor.h:2161
AND !m_bForceAttackPlayer                                    // actor.h:2165
AND m_ThinkState != THINKSTATE_ATTACK                        // actor.h:2169
```

Three independent inputs, all required:

**(a) One of the two disguise bits.** Either the live per-player `m_bIsDisguised`, or the
actor's own cached `m_bEnemyIsDisguised`. The cache is written at:
- `SetEnemy` (actor.cpp:6906): `m_Enemy->m_bHasDisguise && (m_Enemy->m_bIsDisguised || !CanSeeEnemy(0))`
  — an unseen enemy who merely *has* a disguise is treated as disguised.
- Every successful sight check on the current enemy (`Actor::CanSee` actor.cpp:4033) syncs
  cache := live flag.
- Cleared to false by: ctor (2984), `NoticeShot` when the shooter is a **teammate** of the
  actor (actor.cpp:9996 — any German firing near him clears the cache), and both squad-confirm
  paths `ConfirmEnemy` / `ConfirmEnemyIfCanSeeSharerOrEnemy` (actorenemy.cpp:478, 505).
  Because of the OR at actor.h:2161, clearing the cache alone does NOT expose the player while
  the live `m_bIsDisguised` stays true — this is why the coop latched flag holds.

**(b) `m_bForceAttackPlayer` false.** See section 4.

**(c) The actor is not already in the attack thinkstate.** actor.h:2169: once an actor is in
`THINKSTATE_ATTACK`, `EnemyIsDisguised()` reports false *to that actor* — an attacking actor
never re-respects a disguise until it leaves the attack state. (SP relies on this plus the
player-side maintenance loop, section 3.)

Where the protection is enforced:

| Gate | Effect when disguised | Cite |
|---|---|---|
| `ActorEnemy::UpdateThreat` | threat forced 0 (checks the **live** `m_pEnemy->m_bIsDisguised` only — force flag does NOT bypass this) | actorenemy.cpp:164-166 |
| `ActorEnemySet::CheckEnemies` | disguised current enemy **retained** at zero threat instead of dropped | actorenemy.cpp:446-450 |
| `PassesTransitionConditions_Attack` | no transition to attack | actor.cpp:8941 |
| `PassesTransitionConditions_Curious` | sight-based curious suppressed | actor.cpp:9034 |
| `PassesTransitionConditions_Disguise` | disguise challenge only fires if protected | actor.cpp:8976 |
| `EventShareEnemy` | enemy NOT shared with squad | actor.cpp:9351 |
| Machinegunner think | stays on gun instead of `BecomeTurretGuy` | actor_machinegunner.cpp:333-342 |
| `Sentient::IsTeamMate` | a disguised sentient counts as teammate of EVERYONE | sentient.cpp:4018 |
| `Actor::HandlePain` | pain from a "teammate" (= any disguised attacker) is ignored entirely | actor.cpp:5264 |
| `Actor::NoticeFootstep` | disguised footsteps never noticed | actor.cpp:10018 |
| `G_BroadcastAIEvent` | `AI_EVENT_MISC(_LOUD)` suppressed — but only checks **player 0** | g_utils.cpp:1799-1803 |
| `SetPathToNotBlockSentient` | actors politely step out of a disguised player's way | actor.cpp:12593 |

For the attack transition to fire at all, the enemy must also be **confirmed**:
`IsEnemyConfirmed()` = `m_fCurrentVisibility > 0.999` (actorenemy.h:141-144). Visibility
accumulation (`UpdateLMRF`/`UpdateVisibility`, actorenemy.cpp:30-126) is disguise-blind — a
disguised player still becomes a fully "confirmed" zero-threat enemy, which is exactly the
actorenemy.cpp:446 retained state we measured (attackers=0, enemy held).

Things that break the protection regardless of the flags: `level.m_bAlarm` (kills the
player-side flag in SP at player.cpp:5480, and every disguise think transitions to attack on
alarm: salute.cpp:94, sentry.cpp:97, officer.cpp:98, rover.cpp:98); the HALT/timeout paths of
the papers state machine (section 2) which call `SetThinkState(THINKSTATE_ATTACK, ...)`
directly, bypassing `PassesTransitionConditions_Attack`.

`FL_NOTARGET` on the enemy is a separate parallel protection checked in the same places
(actor.cpp:8937, disguise thinks, common states).

---

## 2. Papers check: the full state machine

### Entry — `PassesTransitionConditions_Disguise` (actor.cpp:8955-9007)

All must hold, evaluated at most every 200 ms (8964-8968):

1. `!m_bLockThinkState` (8960); `level.inttime >= m_iNextDisguiseTime` (8964).
2. `m_Enemy` set (8972) — the disguised player IS the retained zero-threat enemy.
3. `EnemyIsDisguised()` (8976) and `IsEnemyConfirmed()` (8980).
4. Height difference <= 48 units (8984).
5. 2D distance in the open interval (32, disguise_range) — `fDistSquared <= Square(32)` or
   `>= m_fMaxDisguiseDistSquared` both fail (8988-8992).
6. Sight trace from actor eye **to `G_GetEntity(0)`'s centroid** — hardcoded player 0, not
   `m_Enemy` (8994-9006). SP assumption; see section 3.

Priority: checked from `CheckForThinkStateTransition` AFTER attack, BEFORE curious
(actor.cpp:8840-8848). The dispatch table for `THINKSTATE_DISGUISE` is `m_ThinkMap`, default
`THINK_DISGUISE_SALUTE` (actor.cpp:8440), overridden per-actor by `type_disguise`
(`EventSetTypeDisguise` actor.cpp:8227-8241; think name strings "salute", "sentry", "officer",
"rover", "none" — scriptmaster.cpp:347-351). GlobalFuncs registered at actor.cpp:6708-6712.

### Begin (per type)

Every Begin re-validates `(EnemyIsDisguised() || FL_NOTARGET) && !level.m_bAlarm`, else goes
straight to `THINKSTATE_ATTACK`:

- **salute** (actor_disguise_salute.cpp:39-59): plays `anim/disguise_salute.scr`, no papers
  interaction at all; on animation end -> IDLE (105-108). `End_DisguiseSalute` always sets
  `m_iNextDisguiseTime = now + m_iDisguisePeriod` (61-64).
- **sentry** (actor_disguise_sentry.cpp:38-59): snapshots
  `m_iEnemyShowPapersTime = m_Enemy->m_ShowPapersTime` (line 53), enters sub-state `WAIT`.
- **officer** (actor_disguise_officer.cpp:38-59): snapshot (53), enters `PAPERS` directly.
- **rover** (actor_disguise_rover.cpp:38-59): snapshot (53), enters `PAPERS` directly.

`End_Disguise{Sentry,Officer,Rover}` set `m_iNextDisguiseTime = now + (m_State ? period : 500)`
— i.e. if the encounter never left sub-state 0 (`WAIT` == `ACTOR_STATE_DISGUISE_START` == 0,
actor.h:432-440), re-challenge in 500 ms; otherwise full disguise_period (sentry.cpp:61-64,
officer.cpp:61-64, rover.cpp:61-64).

### Sub-states (`eActorState_Disguise`, actor.h:432-440; shared bodies in actor_disguise_common.cpp)

```
WAIT  --(dist^2*4 < range^2, i.e. inside half range)--------> PAPERS      common.cpp:42-44
      --(>3 s AND dist > 256)-------------------------------> IDLE        common.cpp:47-52
      --(>3 s AND dist <= 256)------------------------------> PAPERS      common.cpp:54

PAPERS (real check - SENTRY ONLY, sentry.cpp:112):            common.cpp:58-83
      player has NOT re-shown papers since snapshot
        (m_iEnemyShowPapersTime >= m_Enemy->m_ShowPapersTime):
          --(12 s timeout)----------------------------------> ENEMY       common.cpp:65-66
          --(player walks 2D dist > 256)--------------------> HALT        common.cpp:68-72
      player HAS shown papers:
          --(level.m_iPapersLevel <  m_iDisguiseLevel)------> DENY        common.cpp:74-75
          --(level.m_iPapersLevel >= m_iDisguiseLevel)------> run m_DisguiseAcceptThread,
                                                              then ACCEPT common.cpp:77-81

PAPERS (fake check - OFFICER and ROVER, officer.cpp:117, rover.cpp:121):  common.cpp:85-101
      --(player shows papers OR 12 s timeout)---------------> ENEMY       common.cpp:91-93
      --(player walks 2D dist > 256)------------------------> HALT        common.cpp:96-99
      (there is NO accept path: showing papers to an officer/rover type BLOWS the cover;
       rover's ACCEPT switch case at rover.cpp:107-109 is unreachable dead code)

ENEMY --(3 s, unless FL_NOTARGET)--> SetThinkState(ATTACK)    common.cpp:103-110
HALT  --(1.5 s, unless FL_NOTARGET)-> SetThinkState(ATTACK)   common.cpp:112-119
       (HALT has NO success exit: returning to the actor does not resume the papers check;
        the only non-attack exits are losing m_Enemy or FL_NOTARGET)
ACCEPT --(3 s)--> IDLE  +  SetThink(THINKSTATE_DISGUISE, THINK_DISGUISE_SALUTE)
                                                              common.cpp:121-129
       (a successful papers check PERMANENTLY downgrades that actor to salute-type;
        he never re-checks papers, and End_* pushes the next challenge out by
        disguise_period)
DENY  --(3 s)--> IDLE (type unchanged; re-challenge after disguise_period)
                                                              common.cpp:131-138
```

Every Think_Disguise* also hard-exits: `!m_Enemy` -> IDLE; alarm -> ATTACK; disguise lost
(`!EnemyIsDisguised()` and not NOTARGET) -> ENEMY sub-state (sentry.cpp:93-100,
officer.cpp:94-101, rover.cpp:94-101, salute.cpp:89-97).

### How pressing fire with papers reaches the actor

There is no event to the actor at all — it is a **timestamp handshake**:

1. Player selects papers (an `InventoryItem`; papers.tik `init/server` sets
   `classname InventoryItem`) and presses fire; the weapon plays its `fire` animation.
2. Retail `models/items/papers.tik` (Pak0) runs server frame commands during `fire`
   (`show_papers.skc`): `activatepapers` at frames 30, 40, 50, 60, 70 — "every 10 frames so
   the player has a good chance of showing them" (comment in the TIK).
3. `EV_InventoryItem_Activate_Papers` ("activatepapers", inventoryitem.cpp:38-45) ->
   `InventoryItem::ActivatePapers` -> `GetOwner()->m_ShowPapersTime = level.inttime`
   (inventoryitem.cpp:81-84). Per-player, on the Sentient.
4. The actor in sub-state PAPERS polls `m_iEnemyShowPapersTime >= m_Enemy->m_ShowPapersTime`
   each think (common.cpp:64 / 91). The snapshot taken at Begin means only a wave that happens
   *during* the challenge counts.

Since `m_ShowPapersTime` sits on the Sentient and is compared against `m_Enemy`'s copy, this
half of the handshake is per-player-correct in coop.

### Animations invoked

`DesiredAnimation(ANIM_MODE_NORMAL, STRING_ANIM_DISGUISE_*_SCR)` — const-string table maps to
`anim/disguise_{salute,wait,papers,enemy,halt,accept,deny}.scr` (scriptmaster.cpp:332-338;
files in retail Pak0). Notable content: `disguise_papers.scr` escalates upper-body anims
`den_actor_ask_` -> `den_actor_suspicion_` -> `den_fullbody_interrogate_` -> aim;
`disguise_deny.scr` does a raw `centerprint "You don't have the proper papers!"` (a retail
centerprint that goes to everyone in coop); salute picks `den_unarmed_fullbody_salute_` vs
`den_rifle_fullbody_salute_` by `self.weapongroup`.

---

## 3. SP-only assumptions that break under 4-player coop

1. **Player flag maintenance is gametype-gated** — `Player::Think`, player.cpp:5477-5499.
   Only when `g_gametype == GT_SINGLE_PLAYER`: recompute `m_bIsDisguised` every frame:
   `m_bHasDisguise && !level.m_bAlarm` (5480) AND active WEAPON_MAIN is none or an
   InventoryItem (5481-5483) AND no German-list actor (`m_HeadSentient[0]`, TEAM_GERMAN=0,
   sentient.h:78) currently has `m_Enemy == this && IsAttacking()` (5486-5493). In MP this
   whole block never runs, so `m_bIsDisguised` keeps its last value forever — this is both the
   mod's latch trick (flip gametype for one Think so 5484 sets it, flip back before anything
   else) and the reason nothing ever auto-clears it in coop: **weapon in hand, alarm, and
   being shot at do NOT drop the disguise in MP**. Only another gametype-flip recompute (or a
   savegame archive) can change it.
2. **Challenge sight-trace targets player 0** — `PassesTransitionConditions_Disguise`,
   actor.cpp:8994-9006 traces to `G_GetEntity(0)->centroid` while every other predicate in the
   function uses `m_Enemy`. With 4 players: an actor whose retained enemy is player 3 will
   only enter the papers challenge if it ALSO has line of sight to player 1's (slot 0) chest;
   if slot 0 is dead/spectating/elsewhere the challenge silently never fires. No NULL guard:
   if entity slot 0 is empty (dedicated, host disconnected) this is a crash site.
3. **`attackplayer` confirms player 0 only** — `ForceAttackPlayer` actor.cpp:9293
   (`ConfirmEnemy(G_GetEntity(0))`), `EventAttackPlayer` throws ScriptError without entity 0
   (9304-9306). The HZM `EventAttackEntity` (9320-9334) is the coop-safe replacement: confirms
   an arbitrary sentient and — critically — does NOT set `m_bForceAttackPlayer`.
4. **Obstacle-bump aggression blames player 0** — `GetMoveInfo` ANIM_MODE_DEST and
   ANIM_MODE_PATH branches, actor.cpp:3354-3377 and 3382-3406: ANY player body-blocking a
   moving actor makes it `BecomeTurretGuy()` + `ForceAttackPlayer()` against entity 0 (HZM
   already NULL-guards and spares manned MG42 gunners; `IsTeamMate(p)` does exempt a
   *disguised* player 0 from triggering it — but a non-disguised player 0 is blamed for
   player 3's bump). NOTE: this is a stock engine path that sets the poison flag with no
   script call involved — bumping a patroller while others are visible can start the cascade.
5. **`AI_EVENT_MISC` suppression checks player 0's disguise for everyone's events**
   (g_utils.cpp:1799-1803): if player 0 is disguised, misc AI events from ALL players are
   suppressed; if player 0 is not, a disguised player 2's misc events broadcast normally.
6. **`level.m_iPapersLevel` is global** (level.h:157): "the level of papers the player
   currently has" — one value for all four players. Whoever's challenge resolves uses the
   shared level; per-player papers pickups cannot be represented.
7. **Player stealth meter / enemies** — `Player::UpdateEnemies` (player.cpp:5064-5114) is
   `GT_SINGLE_PLAYER`-only (5071) and maintains `m_fPlayerSightLevel` which feeds actor
   visibility (actorenemy.cpp:120). In MP it stays 0 — actors are actually *slower* to confirm
   players in coop; not a break, but a behavior delta to remember.
8. **`RequireThink`** (actor.cpp:6794-6800): SP requires entity 0 to exist; MP path uses
   `lastNetTime` — fine, but another entity-0 dependency to be aware of.
9. **Grenade-think fallback poisons against player 0** — `Begin_Grenade`,
   actor_grenade.cpp:336-354: a TEAM_GERMAN actor that enters the grenade thinkstate with
   `m_pGrenade` NULL (grenade exploded/removed between the transition check and BeginState)
   runs `if (!IsTeamMate(G_GetEntity(0))) ForceAttackPlayer();` (348-349). A *disguised*
   player 0 is exempt via IsTeamMate, but a non-disguised player 0 gets blamed and the actor
   takes the permanent poison flag — no script call, no obstacle bump. (A twin at 440-441 is
   unreachable dead code: the `else` of the always-true `if (m_pGrenade)` at 362.) The
   machinegunner player-0 assumption was already reworked to nearest-living-player under
   `[user 08-02]` (actor_machinegunner.cpp:243-300).

---

## 4. What `m_bForceAttackPlayer` poisons — and that nothing clears it

Set: `Actor::ForceAttackPlayer` (actor.cpp:9294), reached from **four live call sites**:
script `attackplayer` (EventAttackPlayer 9302-9309, event def 1314-1322), the two
obstacle-bump branches (3376, 3404), and the `Begin_Grenade` no-grenade fallback
(actor_grenade.cpp:349 — German actor, `m_pGrenade` NULL, player 0 not a teammate/disguised;
see section 3 item 9; its twin at 441 is unreachable dead code). Cleared: **only** the Actor
constructor (actor.cpp:3092). Grep of the whole tree shows no other assignment of
`m_bForceAttackPlayer` (only 3092 false / 9294 true) — there is no event, no think reset
(`BecomeTurretGuy` rewrites the think map at 13053-13064 but not the flag), no state that
restores it. It is even archived into savegames (actor.h:1949). **One-way latch for the
actor's lifetime: confirmed.**

What it poisons — everything routed through `EnemyIsDisguised()` (actor.h:2165):

- `PassesTransitionConditions_Attack` (8941): the disguised player becomes attackable the
  moment they are confirmed — and `ForceAttackPlayer` itself force-confirms player 0
  (9293), so the attack transition fires on the next `CheckForThinkStateTransition`.
- `PassesTransitionConditions_Disguise` (8976): that actor never challenges again — no more
  halt/papers, straight to gunfire.
- `PassesTransitionConditions_Curious` (9034) now treats the player as a normal unconfirmed
  enemy source.
- All four `Begin_Disguise*` re-validations and `Think_Disguise*` "disguise lost" checks: if
  the actor happens to be mid-challenge, it flips to the ENEMY sub-state / attack.
- `EventShareEnemy` (9351): the gate opens, so the poisoned actor **shares its enemy with its
  whole squad ring** every 0.75 s (EV_Actor_ShareEnemy posted on SetEnemy, 6904). Nuance: the
  squad-mates receive `ConfirmEnemyIfCanSeeSharerOrEnemy` (actorenemy.cpp:501-536) which
  clears *their* cached `m_bEnemyIsDisguised` (505) — but the live `m_Enemy->m_bIsDisguised`
  is still true in the coop latch, so per actor.h:2161 the squadmates remain non-hostile.
  The flag does not spread; only the flagged actor shoots.
- What it does NOT bypass: `ActorEnemy::UpdateThreat`'s zero-threat rule (actorenemy.cpp:164
  checks the live flag only) — the poisoned actor attacks a zero-threat enemy, which works
  because attack transitions key off confirmation (visibility), not threat.

Once the poisoned actor is in `THINKSTATE_ATTACK`, condition (c) of section 1 keeps ANY
attacking actor blind to disguise anyway (actor.h:2169) — and in SP the maintenance loop
(player.cpp:5486-5493) would then clear the player's own flag ("an attacker exists"),
cascading hostility to everyone. In coop the cascade does not happen automatically because
the maintenance never runs; the measured result (session 2026-08-08: attackers=0 of 25 with
all raw `attackplayer` sites blocked) matches this model exactly.

---

## 5. `disguise_level` vs papers level: who holds what, where compared

- The **actor** holds `m_iDisguiseLevel` — how demanding this checker is. Valid values 1 or 2
  only; anything else resets to 1 with a ScriptError (actor.cpp:8282-8290). m2l2a sets
  `"disguise_level" "1"` on nearly all actors (map_entities/m2l2a_entities.txt:147, 169, ...)
  — **except the second sentry checkpoint (entities.txt:7405), which is
  `"disguise_level" "2"` (7416)**: `level.papers` must be raised to 2 before that check can
  pass.
- The **Level object** holds `m_iPapersLevel` — how good the papers currently held are.
  Script-set via `level.papers = N` (level.cpp:2097-2100); starts at 0 every map load
  (level.cpp:770), so until a map script raises it, even a level-1 sentry denies.
- The single comparison in the entire engine: `State_Disguise_Papers`,
  actor_disguise_common.cpp:74: `level.m_iPapersLevel < m_iDisguiseLevel` -> DENY, else
  accept-thread + ACCEPT. Only sentry-type actors ever execute it (section 2).
- `m_DisguiseAcceptThread.Execute(this)` runs at the moment of acceptance, before the ACCEPT
  anim (common.cpp:77-79); m2l2a wires **two** accept threads:
  `"disguise_accept_thread" "sentry1trigdisable"` on the first sentry (m2l2a_entities.txt:165)
  and `"disguise_accept_thread" "sentry2accept"` on the level-2 sentry (7419). The third
  sentry (7706, level 1) has no accept thread.

Deny is non-violent: 3 s reject anim, back to IDLE, actor keeps its type and re-challenges
after `disguise_period` (m2l2a uses 15 s). The player loses nothing by failing a sentry check
— only officers/rovers punish the attempt.

---

## 6. `type_disguise none`: full ignore, not challenge-then-attack

`THINK_DISGUISE_NONE` registers **only** `IsState` (`InitDisguiseNone`,
actor_disguise_common.cpp:27-30) — no `PassesTransitionConditions`, no ThinkState, no
Begin/End. `CheckForTransition` returns false when the func table has no
PassesTransitionConditions (actor.cpp:8868-8871). Consequences:

- The actor can **never enter** `THINKSTATE_DISGUISE`: no halt, no papers, no salute.
- Attack is *independently* blocked by `EnemyIsDisguised()` at actor.cpp:8941, and sight-based
  curious by 9034. So versus a disguised player, a `type_disguise none` actor **fully ignores
  them**: it idles, retaining the player as a zero-threat confirmed enemy
  (actorenemy.cpp:446), doing nothing at all.
- The instant the disguise drops (or the actor is force-flagged), normal attack rules resume —
  "none" only removes the challenge behavior, not hostility.
- Balcony actors' disguise slot is identical (`InitBalconyDisguise` registers only IsState,
  actor_balcony.cpp:63-66): balcony guys never challenge either.
- m2l2a census (grep of m2l2a_entities.txt): **34 "salute", 10 "none", 3 "sentry",
  2 "officer"** — salute is the rank-and-file majority; "none" is the exception (entities.txt
  279, 1300, 1523, 1547, 1572, 4446, 4479, 7082, 7264, 8310). Sentries: 180 (accept thread
  `sentry1trigdisable`), 7405 (level 2, accept thread `sentry2accept`), 7706 (level 1, no
  accept thread). Officers: 134 and 2284 (the 2284 one with `disguise_range 64`).

(Do not confuse with `STRING_DISGUISE_NONE` reuse as the generic string "none" in
TurretGun target-type and teamwin parsing — weapturret.cpp:2241, scriptthread.cpp:4363.)

---

## 7. Coop-relevant summary (m2l2a implications)

1. The latched `m_bIsDisguised` (gametype-flip trick) is honored by every actor-side gate via
   the OR at actor.h:2161, and in MP nothing engine-side ever un-sets it: not weapons, not
   alarm, not being attacked. It is strictly script-owned in coop.
2. The only four ways a disguised player gets shot: (a) an actor carrying
   `m_bForceAttackPlayer` (one-way latch, four live call sites incl. the Begin_Grenade
   fallback, ctor-only reset), (b) an actor already in `THINKSTATE_ATTACK` (actor.h:2169),
   (c) the disguise state machine timing out / halting (officer & rover types always end in
   ENEMY->attack if the player lingers 12 s or shows papers; HALT->attack in 1.5 s after
   walking off mid-check), (d) `level.m_bAlarm` set while an actor is in — or entering — a
   disguise thinkstate: every Begin_Disguise* re-validation and every Think_Disguise* does a
   direct SetThinkState(ATTACK) on alarm even though `EnemyIsDisguised()` still holds
   (salute.cpp:94, sentry.cpp:97, officer.cpp:98, rover.cpp:98). In coop the alarm does NOT
   clear the latched flag (section 3.1), but it does flip every mid-challenge checker hostile.
3. Per-player-correct pieces: `m_ShowPapersTime` handshake, `m_bIsDisguised` /
   `m_bHasDisguise` storage, `IsTeamMate`. Player-0-hardcoded pieces: the challenge
   sight-trace (actor.cpp:8994), `attackplayer` (9293), obstacle-bump blame (3357/3387),
   grenade-fallback blame (actor_grenade.cpp:348-349), misc-AI-event suppression
   (g_utils.cpp:1801). Global pieces: `level.m_iPapersLevel`, `level.m_bAlarm`.
4. A full 4-player papers flow would need: per-player papers level (engine holds it on
   `Level`), the 8994 trace retargeted at `m_Enemy`, and the accept-thread contract reviewed
   (accept permanently downgrades the checker to salute — common.cpp:127 — which is fine for
   one player but means players 2-4 never get checked, only saluted; for m2l2a's gate-opening
   accept thread that is arguably desirable).
