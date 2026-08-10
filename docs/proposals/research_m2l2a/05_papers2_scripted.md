# 05 — Papers Level 2 + Scripted Detection (m2l2a / m2l2b / m2l2c)

Research pass, 2026-08-09. Read-only survey of: retail Pak0/Pak5 scripts (extracted via zipfile),
the current mod tree (`hzm-mohaa-coop-mod/`), the engine fork (`openmohaa-hzm/code/fgame/`), and
the entity dump (`map_entities/m2l2a_entities.txt`). Line numbers for retail scripts are the
retail files' own line numbers; mod line numbers are the current working-tree files.

---

## CORRECTIONS (verification pass, 2026-08-09)

Independently re-verified against Pak0/Pak5 (zipfile), the engine fork, the mod working tree and
the entity dumps. The core mechanics all held up (papers level is a script-only level-global;
`actor_disguise_common.cpp:74` is the single comparison; the accept thread is sentry-only;
DENY is a wave-off; officers are unconditional busts; the `attackplayer` latch and the
entity-0 sight trace are as stated). Seven points were wrong or imprecise and are fixed in the
body below:

1. **§1 TIK table**: retail `papers.tik` uses surface shader `wehrpass`, NOT `wehrpass_l1`, and
   is `rank 2 2` (papers2.tik is `rank 3 3`); papers.tik also has an extra `visa papers_visa.skc`
   animation papers2 lacks. "Byte-for-byte the same" was wrong — behaviorally identical is right.
2. **§7.3 was wrong that the mod's `global/alarm_system.scr` is "identical — no diff"**. It is a
   chrissstrahl coop rework (~1480 diff lines, labels shifted), and its alarm-ON branch adds
   `thread coop_mod/itemhandler.scr::takeAllDisguises` (mod :701) — in the mod, raising the alarm
   permanently strips every player's disguise; dousing it does NOT restore it (unlike vanilla).
   Retail line numbers cited in §7.3 remain valid for the retail file.
3. **§7.3 "eleven" find_guy resolutions** — there are TEN (retail m2l2a.scr:46-57), matching the
   ten names listed.
4. **§7.2 workers row**: the welders' alarmthread `weldinginterupt` (retail :980-992) arms the
   P38 but NEVER calls `attackplayer`; only sledgehammerguy's `cower` (:940-949) ends in the
   latch. The blanket "arm + attackplayer" description was wrong for the welders.
5. **§9 m2l2b mod cover-blow**: the mod SP-gates `$player.has_disguise = 0`
   (`if(level.gametype == 0)`); in coop the strip flows through `remove_item "uniform"` →
   `items.scr:477` → `takeAllDisguises`.
6. **§9 m2l2c**: "zero papers/disguise references" is true of the SCRIPT only — the m2l2c BSP
   entity lump carries 15 `type_disguise "salute"` actors (inert, since nothing there grants
   `has_disguise`).
7. **§5 precision**: `sentry2accept` silences the RELAY (`$sentry2trigger nottriggerable`), which
   kills the bust function of all three volumes in one stroke — but the `trigger_hurt`'s DAMAGE
   is not routed through the relay and keeps hurting swimmers after accept.

---

## 1. How the papers "level" actually works at engine level

**There is no per-item level field.** The two papers are two entirely separate `InventoryItem`
weapons, and the *level* is a single level-scoped integer that only script writes:

| Piece | Where | Fact |
|---|---|---|
| `models/items/papers.tik` | Pak0 | `classname InventoryItem`, `name "Papers"`, surface shader `wehrpass`, `rank 2 2`, plus a `visa papers_visa.skc` anim papers2 lacks |
| `models/items/papers2.tik` | Pak0 | `classname InventoryItem`, `name "Papers"`, surface shader `wehrpass_l2`, `rank 3 3`, no `visa` anim — behaviorally identical otherwise (`firedelay 0.5`, fire anim `show_papers.skc` with the same five `activatepapers` frames; rank only affects inventory ordering) |
| `level.m_iPapersLevel` | `level.h:157`, init 0 at `level.cpp:770` | THE papers level. Script property name `papers`: `EV_Level_SetPapersLevel`/`GetPapersLevel` (`level.cpp:163-179`, handlers `level.cpp:2092-2100`). **The engine itself never sets it from a pickup** — only `level.papers = N` in script does. |
| `m_ShowPapersTime` (Sentient) | `sentient.h:208` | Timestamp of the last time the player *showed* papers. Set by `InventoryItem::ActivatePapers` (`inventoryitem.cpp:81-84`) — the `activatepapers` event fired from the papers TIK's `fire` animation at server frames 30/40/50/60/70 ("so that the player has a good chance of showing them to the AI even if they're waving them around all silly like"). Both papers.tik and papers2.tik fire it identically. |
| `m_iEnemyShowPapersTime` (Actor) | `actor.h:797-799` | The actor's snapshot of the enemy's show-time taken when a challenge starts. "Papers were shown to me" == `snapshot < enemy->m_ShowPapersTime`. |
| Persistence | `sentient.cpp:3362-3375` (`IsItemName`) + `ArchivePersistantData` (`sentient.cpp:3387-3399`) | camera / binoculars / **papers.tik / papers2.tik are deleted from the inventory before map-transition persistence**. Papers never carry across a level change; every map re-grants what it wants (see §9). |
| Savegame | `level.cpp:2636` | `m_iPapersLevel` is archived inside a map's save, so mid-map save/load keeps the level. |

So: **papers1 vs papers2 differ only in HUD icon, hand-model skin, and the `level.papers` value
the granting script writes.** An actor's `disguise_level` (1 or 2; setter clamps and errors on
anything else, `actor.cpp:8284-8299`, default 1 at `actor.cpp:3027`) is compared against
`level.m_iPapersLevel` in exactly ONE place in the whole engine:
`actor_disguise_common.cpp:74` — `else if (level.m_iPapersLevel < m_iDisguiseLevel)
TransitionState(ACTOR_STATE_DISGUISE_DENY)`.

### Coop consequence (measured design, not a bug)
`level.papers` is **global, not per-player**. One player using the papers2 pickup upgrades the
whole team's level instantly. The per-player part in coop is only *holding the item to show*
(`level.coop_itemPapers` + `coop_hasPapers` flag, §10).

---

## 2. The engine challenge state machines (who can bust a level-1 disguise, and how)

### 2.1 When a challenge starts — `Actor::PassesTransitionConditions_Disguise` (`actor.cpp:8955-9006`)
All disguise think-types share this gate:
- rate-limited by `m_iNextDisguiseTime` (re-armed to `now + disguise_period` when a challenge
  ends — `End_DisguiseSentry` `actor_disguise_sentry.cpp:61-64`, same for officer/rover;
  `disguise_period` is 15 s on every actor in this map);
- requires a current `m_Enemy` that **is disguised** (`EnemyIsDisguised()`, `actor.h:2159-2167` —
  false unconditionally once `m_bForceAttackPlayer` is latched by `attackplayer`);
- `|Δz| <= 48`, `32 < dist2D < disguise_range` (256 on everything here except one officer at 64);
- **sight-trace from the actor's eye to `G_GetEntity(0)->centroid`** — a hardcoded player-0
  assumption (`actor.cpp:8993-9005`). In 4-player coop the enemy being challenged can be player N
  while the trace runs against player 0. (Known SP assumption; relevant to the stealth work.)

### 2.2 What each `type_disguise` does once the challenge runs

| type_disguise | Think file | Papers behavior |
|---|---|---|
| `none` | `actor_disguise_common.cpp:27-30` (`InitDisguiseNone` registers only `IsState`) | Never challenges, never salutes. Can only turn hostile via script (`attackplayer`), the alarm, or the player losing the disguise. |
| `salute` | `actor_disguise_salute.cpp` | Salutes; never asks for papers; `level.m_bAlarm` or an undisguised enemy flips it to attack. 34 of the 49 disguise-configured actors in m2l2a are this. |
| `sentry` | `actor_disguise_sentry.cpp` | **The only type that does the real level check.** WAIT (approach) → PAPERS. `State_Disguise_Papers` (`actor_disguise_common.cpp:58-83`): papers not shown within 12 s → ENEMY; walk >256 away mid-check → HALT; papers shown → `level.m_iPapersLevel < m_iDisguiseLevel` ? DENY : (run `disguise_accept_thread` if set, then ACCEPT). **`disguise_accept_thread` can only ever fire from a sentry-type actor.** |
| `officer` | `actor_disguise_officer.cpp` | Goes straight to PAPERS (`Begin`, :52-55) but dispatches `State_Disguise_Fake_Papers` (`actor_disguise_common.cpp:85-101`): **showing papers — any papers — or letting 12 s pass → ENEMY.** There is no accept path. Officers *always* see through the disguise once an interrogation runs to completion; this matches retail walkthrough advice ("stay away from officers"). |
| `rover` | `actor_disguise_rover.cpp` | Same `Fake_Papers` dead-end as officer. (None placed in m2l2a/m2l2b.) |

### 2.3 The outcome states (`actor_disguise_common.cpp`)

| State | Behavior | Then |
|---|---|---|
| ACCEPT (:121-129) | plays `anim/disguise_accept.scr` 3 s | back to THINKSTATE_IDLE, disguise think becomes SALUTE |
| DENY (:131-138) | plays `anim/disguise_deny.scr` 3 s | **back to THINKSTATE_IDLE — a failed level check is NOT an attack and NOT an alarm.** Re-challenge only after `disguise_period` (15 s). |
| ENEMY (:103-110) | `anim/disguise_enemy.scr`, 3 s grace | THINKSTATE_ATTACK |
| HALT (:112-119) | `anim/disguise_halt.scr`, 1.5 s grace | THINKSTATE_ATTACK |

The interrogation animation itself is `anim/disguise_papers.scr` (registered at
`scriptmaster.cpp:334`): ask (`den_actor_ask_*`) → suspicion → interrogate → aim, escalating over
~12 s — the visual countdown that matches the engine's 12 s window.

### 2.4 The two global kill-switches
- **Alarm**: script `level.alarm = 1` writes engine `Level::m_bAlarm` (`level.cpp:2062-2070`).
  Every disguise thinker checks it every frame and goes straight to attack
  (e.g. `actor_disguise_sentry.cpp:97-100`), and `Begin_*` refuses to challenge while it is up.
  While the alarm is up the player cannot re-acquire `m_bIsDisguised` (`player.cpp:5480`).
- **The player's own disguise flag**: SP-only per-frame decider `player.cpp:5477-5495` —
  `m_bIsDisguised = m_bHasDisguise && !alarm && (no weapon || weapon is InventoryItem)` **and no
  living actor with `m_Enemy == this` currently in `IsAttacking()`**. That last clause is the
  cascade: ONE actor entering attack (scripted `attackplayer`, officer bust, ENEMY/HALT timeout)
  strips `m_bIsDisguised`, and every other actor then sees an undisguised enemy. The mod
  reproduces the flag via `changeGameType` flips (see CLAUDE.md / itemhandler notes).

---

## 3. Papers level 1 — where the level-1 kit comes from

Entity chain (all coordinates from `map_entities/m2l2a_entities.txt`):
- `$suit` `script_model` `items//officer_uniform.tik` @ `-4437.98 -3992.78 -20` (lump :207-212)
- `$papers1` `script_model` `animate/pulse_papers1.tik` @ `-4416.43 -3994.44 -20` (lump :195-201)
- `trigger_useonce` model `*8` @ `-4427 -3995 -11`, `setthread likeynorway` (lump :202-206)

`likeynorway` (retail `maps/m2l2a.scr:578-610`; mod `maps/m2l2a.scr:645+`):
removes the props, prints "Be prepared to show your papers when asked.",
`add_item "papers_level1"` + `add_item "uniform"`, unlocks `$likeynorwaydoor`, then runs the
two-guard locker-room conversation. It also sets the two conversation guards
`type_disguise "none"` for the scene (retail :578-579), flipping them to `"salute"` after
(:604-605; in the mod this flip is SP-only — `[user 2026-08-09]` block at mod :699-711 keeps
them "none" in coop because a salute-type with a live disguised enemy wins over the walkto and
traps them standing).

Note: retail also sets `$player.has_disguise = 1` at map spawn (retail :35), *before* the suit
exists — `m_bHasDisguise` is up from the start of the map in vanilla; the suit pickup is what
grants the papers item + the German player model.

`global/items.scr` (retail :186-198 / mod :199-216) `add_item "papers_level1"`:
HUD icon `textures/hud/item_papers1`, gives `models/items/papers.tik`
(mod: via `coop_mod/replace.scr::item` to every player + `itemhandler.scr::givePapersFlagToAll`),
then **`level.papers = 1`**.

---

## 4. Papers level 2 — where it is obtained, retail and mod (identical logic)

Entity chain — a small office at the south end of the pens, before the second checkpoint:
- `$papers2` `script_model` `animate/pulse_papers2.tik` @ `-3606.01 -6930.81 -268`
  (lump :7440-7453) — pulsating desk prop (`wehrpass_l2_pulsating` shader).
- `trigger_useonce` model `*150` @ `-3611 -6949 -244`, `setthread papers2pickup` (lump :4396-4401).
- `papers2hint` `trigger_multiple` model `*1` @ `-2896 -6336 -304` (lump :12-17) — a walk-through
  volume on the approach to the checkpoint.

`papers2pickup` (retail `maps/m2l2a.scr:329-334`; mod `maps/m2l2a.scr:392-397` — **unchanged in
the mod**):
```
papers2pickup:
    level.sentry2hintmessaged = 1
    $papers2 remove
    waitthread global/items.scr::remove_item "papers_level1"
    waitthread global/items.scr::add_item "papers_level2"
end
```
`items.scr` `papers_level2` (retail :200-212 / mod :218-235): icon `textures/hud/item_papers2`,
takes papers.tik, gives `models/items/papers2.tik` (mod: to all players +
`givePapersFlagToAll "models/items/papers2.tik"` which also updates `level.coop_itemPapers`),
then **`level.papers = 2`**. `remove_item "papers_level1"` first sets `level.papers = 0`
(retail :380-384) before the add restores it to 2 — a one-frame window, irrelevant in practice.

`sentry2hintmessage` (retail :181-188; mod :230-237): first touch of `$papers2hint` prints
**"You need a new set of papers to procede past this point."** once
(`level.sentry2hintmessaged` latch; the pickup pre-latches it so the hint never fires after you
already hold papers2).

---

## 5. The level-2 gate — sentry2, the ONLY disguise_level 2 check in the game files surveyed

`grep '"disguise_level" "2"'` across the m2l2a/m2l2b dumps hits exactly once: lump :7416.

**`sentry2dude`** (lump :7396-7424): `ai_german_elite_sentry` @ `-2736 -6256 -494`,
`type_disguise "sentry"`, **`disguise_level 2`**, `disguise_range 256`, `disguise_period 15`,
**`disguise_accept_thread "sentry2accept"`**, `noticescale 1` (near-blind to normal notice — he
is a checkpoint fixture, not a hunter), `fixedleash 1`, `leash 64`, targetname `ai_alarm`,
`$find_name sentry2dude` (script handle `level.sentry2dude`, retail :55).

**The bust net** — `sentry2trigger` `trigger_relay` @ `-2688 -6360 -456` (lump :4344-4347) is
fired by THREE volumes bracketing the gate line:
- `trigger_multiple` `*149` @ `-2676 -6212 -388` (lump :4353-4358)
- `trigger_multiple` `*248` @ `-2616 -6356 -388` (lump :8325-8330)
- **`trigger_hurt` `*148` @ `-2676 -6480 -388`** (lump :4348-4352) — the water route around the
  gate both hurts you and busts you. (This is the trigger_hurt the mod header comment at mod
  :1-5 flags "remove trigger hurt at -2676 -6480 -388" as a chrissstrahl fixme.)

`sentry2thing` (retail :223-228; mod :281-286 — unchanged):
```
$sentry2trigger waittill trigger
level.sentry2dude leash 2048
level.sentry2dude resetleash
level.sentry2dude attackplayer
```
`attackplayer` is the one-way `m_bForceAttackPlayer` latch (`Actor::ForceAttackPlayer`,
cleared only in the Actor constructor) — after a bust this sentry is permanently blind to the
disguise and now has the leash to chase.

**The intended pass** — `sentry2accept` (retail :791-793; mod :939-941 — unchanged):
```
sentry2accept:
    $sentry2trigger nottriggerable
end
```
Executed by the ENGINE from `State_Disguise_Papers`'s accept branch, which requires
`level.m_iPapersLevel >= 2`. Note the disarm acts on the RELAY: `nottriggerable` on
`$sentry2trigger` kills the bust function of all three volumes in one stroke, but the
`trigger_hurt`'s DAMAGE is applied by the volume itself, not routed through the relay — the
swim-around keeps hurting after accept; only the bust stops. Showing level-1 papers gets the
DENY wave-off (no attack, no alarm, 15 s until he asks again) — but the bust volumes stay
armed, so the *area* stays closed.
Sequence as designed: pick up papers2 → walk up to the sentry → he challenges → show papers
(toggleitem in SP; primary fire in coop) → accept thread disarms all three bust triggers →
the south gate area (`$gate3` corridor toward `$endlevel`) is open, still disguised.

**Fail states at this gate, vanilla:**
| What you do | Result |
|---|---|
| Show papers1 | DENY anim → he returns to idle. No shooting, no alarm. Gate volumes still armed. |
| Ignore the challenge 12 s | ENEMY → 3 s → attack (and he is `$ai_alarm`, so once in attack the alarm pipeline can start, §7.3) |
| Walk off mid-challenge (>256) | HALT → 1.5 s → attack |
| Cross the gate line / swim around | `sentry2thing`: leash 2048 + permanent `attackplayer` |
| Show papers2 | accept thread → checkpoint permanently disarmed |

---

## 6. The level-1 checkpoint — same wiring one level down (for contrast)

**`goatsbutt`** (lump :160-180): `ai_german_elite_sentry` @ `-3912 -3480 -286`,
`type_disguise "sentry"`, `disguise_level 1`, **`disguise_accept_thread "sentry1trigdisable"`**,
`type_attack "alarm"`, targetname `ai_alarm`.
- Bust relay `sentry1trig` (`trigger_relay` @ `-4024 -3240 -232`, lump :50-53) fired by
  `trigger_multiple` `*5` @ `-4072 -3104 -216` (lump :103-108) and `*80` @ `-4352 -3232 -216`
  (lump :3428-3433).
- `sentry1alarm` (retail :799-807): trigger → goatsbutt says `den_alarm_01c` then `attackplayer`.
- `sentry1trigdisable` (retail :795-797): accept (any papers ≥1) → `$sentry1trig nottriggerable`.
- His AI is toggled by area triggers `sen1on`/`sen1off` + `enablesentrytrigger`
  (retail :288-316) so he only actively challenges near his post.

A third sentry-type actor exists: a patrolling elite sentry on `subsentrypath` @
`-3692 -3892 -490` (lump :7695-7722), `disguise_level 1`, no accept thread, `type_attack alarm` —
a roaming level-1 papers check on the pens floor.

---

## 7. Everything in m2l2a that is MEANT to spot or challenge a level-1-disguised player

### 7.1 Census from the entity lump (49 actors carry disguise keys)
- `type_disguise "salute"` × 34 — decorative compliance, no papers check.
- `type_disguise "none"` × 10 — never interact with the disguise; hostile only via script/alarm.
- `type_disguise "sentry"` × 3 — goatsbutt (L1), roaming subsentrypath sentry (L1), sentry2dude (**L2**).
- `type_disguise "officer"` × 2 — both are walking cover-blowers (Fake_Papers, §2.2):
  - **`officer1`** (lump :120-155): wehrmact officer @ `-4048 -6048 -488`, `disguise_range 256`,
    `sight 3072`, `hearing 2000`, `maxdist 4000`, `$find_name officer1`. `officer1go`
    (retail :880-900) `forceactivate`s him and walks him on a long route through `$officerdoor1`
    across the south pens — a mobile "do not let him corner you" hazard.
  - Patrolling officer @ `-4016 -2820 -516` (lump :2274-2300), `patrolpath soldierpath101`,
    **`disguise_range 64`** — busts only at point-blank; the designed lesson is "give officers room".

### 7.2 Scripted detection sequences (map script, fire regardless of a valid level-1 disguise)
| Sequence | Wiring | Effect |
|---|---|---|
| **Card players** | `$suckyfatty` ×3 (wehrmact soldiers @ card room upstairs, lump :3557-3625; `cardtable` targets them, lump :40-48). Retail :88 `$suckyfatty thread cardplayersdeath` (:189-195): on a card player's death, `if (level.cardplayers != 3) $suckyfatty attackplayer`. `level.cardplayers` is assigned NOWHERE (verified: only reads exist in either tree), so the condition is always true — **killing any card player turns the survivors hostile, disguise irrelevant.** | attackplayer latch |
| **Scientists guy1/guy2/guy3** | `ai_german_misc_scientist` @ `-4260/-4376/-4304, -1992..-2028` (lump :1500-1580), `type_disguise "none"` in the BSP AND re-set at retail :135-137 / mod :188-190. `sciencetrig` `trigger_multiple` `*9` @ `-4002 -2070 -154` → `suspiciousscientists` → `sciencetalk` (retail :754-789): guy3 walks at you asking questions; **if `level.alarm == 1` he skips talk and goes straight `attackplayer`** (:755-759). | dialogue escort; attack under alarm |
| **Naxos bust** | `$naxos` `trigger_multiple` (spawnflags 128 = use-button) @ `-4414 -1898 -124` (lump :156ff) → `objective2` (retail :342-351) → `ohnothenaxos1` (:390-430): all three scientists `attackplayer` — **destroying the prototype is a scripted, unavoidable local cover-blow.** The scientists' `alarmthread` is also `ohnothenaxos1` (`sciwalkto` :1055-1060, `startwallscience` :1252-1255), so alerting them any other way runs the same bust. | attackplayer ×3 |
| **Sentry gates** | §5, §6 | attackplayer |
| **Workers with alarm duty** | `sledgehammerguy` (retail :916-949; alarmthread `cower` at :940-949), `welderguy1/2` (:957-992; alarmthread `weldinginterupt` at :980-992) — `type_attack "alarm"` + `alarmthread`: when alerted they stop working and arm a Walther P38. **Only `cower` ends in `attackplayer`; `weldinginterupt` does NOT** — the welders re-engage through the normal alarm-attack that alerted them, with no forced latch. `scialarm` (:1331-1335) and `unholsterweapon` (:267-270) are arm+`attackplayer` helpers. | attackplayer (sledgehammer, scialarm) / plain attack (welders) |
| **Mod-only: `waitForEnemy`** | mod :727-766, threaded onto both locker-room guards at mod :686-687. `[200]` Smithy addition, patched `[user 2026-08-08]` (bug-1609): waits while all players are disguised (`aihandler.scr::canseeUndisguisedPlayers`), then `attackplayer` + `type_disguise "none"`. | attackplayer (coop guard) |

### 7.3 The generic alarm pipeline (`global/alarm_system.scr` — retail; the mod ships a coop REWORK of this file, see last bullet)
- Setup (retail m2l2a.scr:43-57): `level.alarm_sound = m2l2_alarm`, `alarm_system_setup`, and
  ten named `$ai_alarm` guys resolved via `find_guy` (`alarm_system.scr:1034-1049`, matches
  `.find_name` within the `$ai_alarm` targetname group): guythatlikesnorway, guythathatesnorway,
  whatsthesub, hushyhushy, stupid, jokey, goatsbutt, sentry2dude, officer1, loweralarmerguy.
- Every `$ai_alarm` actor gets `type_attack "alarm"` + `alarmthread ai_alarm_alerted`
  (`alarm_system.scr:422-442`): on entering attack they push themselves on the alerted stack, and
  `ai_gofor_alarm` (:546-744) picks a living, sighted one to RUN to the zone's alarm switch and
  douse it (`:730`).
- Three wall switches (`trigger_use` + `animate//alarmswitch.tik`) @ `-3846 -3817 30`,
  `-3971 -3718 -227`, `-4427 -2627 -438` (lump :2459-2520), zone volumes `$zone_trigger` tag the
  player's current zone.
- `alarm_system_master` (:769-812) **toggles**: first trigger → `level.alarm = 1` (engine
  `m_bAlarm`, §2.4) + lights + siren + backup spawns; a second use of a switch turns it OFF
  (`level.alarm = 0`) — the alarm is recoverable in vanilla, and the switches are trigger_use,
  so the player can shut it down.
- Backup waves while alarm is up: `alarm_system_backup_spawn` (:856-971), map-tuned
  `level.ai_alarm_backup_max = 4`, cycle `15 s` (retail m2l2a.scr:33-34); backups self-remove
  when the player is far and unseen (:997-999).
- `playalarmsound`/`wakeupcardplayers` (retail :473-490, :231-249) add per-map alarm flavor:
  intercom barks and card players getting `hearing 512` under alarm.
- **Mod tree divergence (correction — the file is NOT retail-identical):** the shipped
  `global/alarm_system.scr` is a chrissstrahl coop rework (~1480 unified-diff lines;
  `$player.zone_index` → `level.playerZone_index`; labels shift: `ai_alarm_alerted` 471→370,
  `ai_gofor_alarm` 546→473, `alarm_system_master` 769→685, `alarm_system_backup_spawn` 856→768).
  The logic is retail-shaped and the master toggle (a second switch use douses the alarm) is
  retained — but the alarm-ON branch adds `thread coop_mod/itemhandler.scr::takeAllDisguises`
  (mod :701, `[200]` Smithy): in the mod, raising the alarm PERMANENTLY strips every player's
  disguise (`has_disguise = false` for all inside a `changeGameType` window, §10) — unlike
  vanilla, dousing the alarm does not let the disguise re-form. All `alarm_system.scr` line
  numbers above are the RETAIL file's.

---

## 8. Vanilla fail-state summary (what the designers intended, mechanism by mechanism)

1. **Wrong papers level at a sentry** → DENY animation, actor returns to idle, re-asks in 15 s.
   *No attack, no alarm.* Area denial is enforced separately by the bust trigger nets.
2. **Refusing/ignoring a sentry challenge** → 12 s → ENEMY → 3 s → attack.
3. **Walking away mid-challenge** → HALT → 1.5 s → attack.
4. **Any officer completing an interrogation** (papers shown or 12 s) → attack. No accept path.
5. **Crossing a checkpoint line un-accepted** → relay → scripted `attackplayer` (permanent latch).
6. **Weapon out** (SP: any non-InventoryItem in hands) → `m_bIsDisguised` false that frame → every
   salute/sentry thinker flips to ENEMY on its next think.
7. **One actor attacking you** → `player.cpp:5489-5493` strips `m_bIsDisguised` → global cascade.
8. **Alarm up** → all disguise thinkers attack; disguise cannot re-form until the alarm is doused
   (vanilla — in the mod the alarm-on `takeAllDisguises` hook makes the loss permanent, §7.3);
   reinforcement waves every 15 s (cap 4 alive).
9. **Scripted story busts** regardless of papers: Naxos destruction (local, three scientists),
   killing a card player, alerting the alarm-duty workers.

The mission is completable fully disguised up to the Naxos bust, and — because the scientists are
the only latched attackers and can be outrun/killed before reaching an alarm switch — the
disguise can survive to the end of m2l2a. m2l2b then re-issues level-1 papers and scripts the
final, mandatory cover-blow.

---

## 9. Carry-over: m2l2b and m2l2c

- Engine strips papers/camera/binoculars items at every transition (§1), and `m_iPapersLevel`
  is re-initialized per map (`level.cpp:770`).
- **m2l2b re-grants LEVEL 1, not level 2** (retail `maps/m2l2b.scr:68-69`; mod :121-122):
  `add_item "papers_level1" 1` + `add_item "uniform" 1`. The level-2 papers are strictly a
  m2l2a-scoped key for the sentry2 gate.
- m2l2b's scripted cover-blow: first bomb planted → `bombcount == 1` branch (retail :224-231;
  mod :318-330): `$player.has_disguise = 0` (in the MOD this line is SP-gated
  `if(level.gametype == 0)` — in coop the strip flows through `remove_item "uniform"` →
  `items.scr:477` → `takeAllDisguises`), `remove_item "papers_level1"`,
  `remove_item "uniform"`, "Your cover has been blown.", 55 s stopwatch. m2l2b's 14
  disguise-typed actors are all salute/none — there is no papers checkpoint in m2l2b.
- **m2l2c's SCRIPT has zero papers/disguise references** (grep of retail m2l2c.scr: none). The
  m2l2c BSP entity lump still carries 15 `type_disguise "salute"` actors — inert in practice,
  since nothing in m2l2c grants `has_disguise` and the m2l2b cover-blow removed it — so the map
  plays as pure escape, but "zero disguise content" is only true of the script, not the lump.

---

## 10. Current mod tree: what changed around papers, and coop implications

Verified against the working tree (papers2pickup / sentry2accept / sentry2thing /
sentry1trigdisable / sentry1alarm are UNCHANGED from retail; the `items.scr` papers cases are
logic-identical with coop plumbing. `global/alarm_system.scr` is NOT retail — it is a
chrissstrahl coop rework whose alarm-on branch adds the `takeAllDisguises` hook, §7.3).

| Mechanism | Where | What it does |
|---|---|---|
| Item fan-out | `global/items.scr:203,222` → `coop_mod/replace.scr::item` | papers item granted to every connected player, not `$player[1]`. |
| Papers bookkeeping | `items.scr:207,226` → `itemhandler.scr::givePapersFlagToAll` (:2485-2492) | sets `level.coop_itemPapers = <tik path>` (single global — the CURRENT papers model) + per-player `coop_hasPapers` flags. |
| Respawn re-give | `itemhandler.scr::managePlayerInventory:733-747` (`[user 2026-08-08]`) | every spawn re-gives `level.coop_itemPapers` unconditionally — so after `papers2pickup`, respawning/late-joining players hold papers2.tik and (because `level.papers` is global) pass the level-2 check. |
| Showing papers in coop | `anim/disguise_papers.scr:13-16` (`[200]` hook) → `itemhandler.scr::enableClickablePapers` (:2501-2534) | while a guard interrogates, PRIMARY FIRE uses the papers item (with the NIL/NULL unarmed guard, `[user 2026-08-08]`). `coop_mod/main.scr::forcePapersInHand` (:1015+) + `level.coop_forcePapersEquip` keep them equipped outside interrogations on the stealth start. |
| Disguise flag in MP | `items.scr` uniform case (:285-291) → `itemhandler.scr::giveDisguiseToAll` (:962+) | sets `has_disguise` on all players inside a `changeGameType 0` window (the `player.cpp:5477` block is SP-gated), retry loop if any player failed to disguise. |
| Uniform loss | `itemhandler.scr::takeAllDisguises` (:1109+) → `coop_armOnBlown` (:1349+) | the single "cover is gone" choke point; re-arms stealth-start players and clears `coop_forcePapersEquip`. |
| Stealth start | mod m2l2a.scr:645-684 (`[user 2026-08-08]`, bug-1604/1607) | `coop_stealthStart` cvar → unarmed spawn (`coop_noWeapon` recipe from e1l3) + papers-in-hand. |

### Open risks for the stealth route at the sentry2 gate specifically
1. **Entity-0 sight trace** (`actor.cpp:8993`): sentry2dude challenging player N still sight-traces
   player 0; if the host is elsewhere behind occluders, the challenge may never start for the
   player standing at the gate — leaving the bust net armed with no legitimate way to disarm it.
2. **The accept thread is the only disarm** for the three bust volumes, and it only runs from a
   completed sentry challenge (§2.2). Anything that keeps sentry2dude out of THINKSTATE_DISGUISE
   (e.g. an `attackplayer` latched earlier — one call blinds him to the disguise forever, incl.
   the mod's own go-loud paths) permanently closes the legit route; only the shoot-through
   remains.
3. **`trigger_useonce` pickup**: `*150` fires once for the whole server. Fine as designed —
   `level.papers` is global and `givePapersFlagToAll` fans the item out — but a player who is
   dead/spectating during pickup relies entirely on the `managePlayerInventory` re-give.
4. **Officers cannot be passed** by any papers level (Fake_Papers, §2.2). officer1's scripted
   walk (`officer1go`) crosses the south pens between the papers2 office and the gate; on the
   stealth route he is a timing hazard, not a papers problem.
5. **Card system** remains unsolved per the 2026-08-09 playtest (re-arm patch in
   `global/cardgame.scr:133-166` did not hold — two card players still stood and never re-sat);
   `cardplayersdeath`'s `attackplayer` is retail-intended detection and must stay.

---

## Citation index (primary anchors)

- Engine: `actor_disguise_common.cpp:58-138`, `actor_disguise_sentry.cpp:38-141`,
  `actor_disguise_officer.cpp:38-135`, `actor.cpp:3025-3027, 8284-8299, 8955-9006`,
  `actor.h:794-802, 2159-2167`, `player.cpp:5477-5495`, `inventoryitem.cpp:38-84`,
  `sentient.cpp:3362-3399`, `sentient.h:208`, `level.h:154-157`,
  `level.cpp:163-179, 659-660, 770, 2062-2070, 2092-2100, 2636`, `scriptmaster.cpp:334`.
- Retail (Pak0/Pak5): `maps/m2l2a.scr:33-57, 88, 122-166, 181-195, 223-228, 267-334, 342-351,
  390-430, 461-463, 578-610, 743-807, 880-900, 916-992, 1049-1065, 1331-1335`,
  `global/items.scr:186-212, 249-261, 380-394`, `global/alarm_system.scr:422-442, 546-744,
  750-812, 856-971, 1034-1049`, `anim/disguise_papers.scr` (whole), `maps/m2l2b.scr:68-69,
  224-231`, `models/items/papers.tik`, `models/items/papers2.tik`,
  `models/animate/pulse_papers2.tik`.
- Mod tree: `maps/m2l2a.scr:139, 188-190, 230-247, 281-286, 392-397, 645-766, 939-945`,
  `global/items.scr:199-235, 285-291, 461-479`, `coop_mod/itemhandler.scr:695-767, 962-1010,
  1109-1136, 1211+, 1349+, 2485-2534`, `coop_mod/main.scr:926-928, 1015+`,
  `anim/disguise_papers.scr:13-16`, `global/cardgame.scr:133-166`, `maps/m2l2b.scr:121-122,
  318-330`.
- Entity lump `map_entities/m2l2a_entities.txt`: papers2hint :12-17, sentry1trig net :50-53,
  :103-108, :3428-3433, officer1 :120-155, goatsbutt :160-180, papers1/suit/likeynorway trigger
  :195-212, patrol officer :2274-2300, alarm switches/zones :2459-2520+, card players
  :3557-3625, sentry2trigger net :4344-4358, :8325-8330, papers2pickup trigger :4396-4401,
  sentry2dude :7396-7424, papers2 prop :7440-7453, roaming sentry :7695-7722.
