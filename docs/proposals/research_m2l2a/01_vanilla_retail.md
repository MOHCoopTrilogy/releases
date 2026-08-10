# m2l2a — The Vanilla Retail Mission, Inside and Out

Research doc, 2026-08-09. READ-ONLY research: every claim below carries a pak/file:line citation.

## CORRECTIONS (verification pass)

Adversarial re-verification 2026-08-09 against Pak0/Pak5/maintt paks, the entity lump, and
`openmohaa-hzm/code/fgame`. All eight load-bearing claims survived; six precision fixes were applied:

1. **Welders do NOT `attackplayer`** (§2.7 item 6). `weldinginterupt` (m2l2a.scr:980–992) breaks the
   animation, gives the welder a Walther P38 and re-enables AI — but contains no `attackplayer`. Only
   the sledgehammer guy's `cower` (948) and the scientists' `scialarm` (1334) carry the latch in that
   group. Consequence: an alerted welder fights by ordinary AI hostility and is NOT permanently blinded
   to the disguise — the only worker/scientist latches are cower and scialarm. (The 7-site grouping
   stands; the welder detail inside item 6 was wrong.)
2. **Officer worst case is ≤ 15 s, not ≤ 12 s** (§2.7 tail). Not-showing path: PAPERS → ENEMY at 12 s
   (common.cpp:91), then ENEMY → ATTACK 3 s later (common.cpp:107–109). Showing papers: ENEMY instantly,
   ATTACK 3 s later. The 12 s figure was only the PAPERS→ENEMY leg.
3. **Officers/rovers skip the WAIT state** (§1.3). `Begin_DisguiseOfficer`/`Begin_DisguiseRover`
   transition straight to ACTOR_STATE_DISGUISE_PAPERS; only sentry begins in WAIT (approach phase).
   "Same approach" overstated the similarity.
4. **The card-table loop is anim-driven, not "3 s per step"** (§2.3). The step gate is
   `local.time = level.time + 3000` (cardgame.scr:325) — script `level.time` is in SECONDS, so the
   timeout is a 3000 s dead-man (a retail ms-vs-s slip); in practice each step advances when a
   `cardgame3anim` thread finishes the step's anim and sets `level.carddone` (e.g. 484/497/758/765).
5. **papers.tik vs papers2.tik** (§1.2): besides shader and rank, papers.tik also carries a `visa`
   anim (papers_visa.skc) that papers2.tik lacks. Cosmetic; the level still lives in `level.m_iPapersLevel`.
6. **Line ref**: `cometolife` label is at m2l2a.scr:817; 809–815 is `moveaflak` (which waits on
   `$movetheflak`, threads cometolife, and does the alarm-silent autosave). §2.8 cited 809–855 for
   cometolife.

Everything else — the GT_SINGLE_PLAYER-only player block (player.cpp:5477–5495), the G_GetEntity(0)
sight-trace (actor.cpp:8994), the toggleitem→fire→`activatepapers` (frames 30–70)→`m_ShowPapersTime`
chain (inventoryitem.cpp:81–84), the think-type behaviors, the one-way `m_bForceAttackPlayer` latch
(actor.cpp:3092/9294), the single level-2 actor (sentry2dude, confirmed sole `disguise_level 2` in the
entity lump), the alarm toggle master (alarm_system.scr:769–812), the 4-cap/15 s zone backups, the
census (34 salute / 10 none / 3 sentry / 2 officer / 2 unset of 51 `ai_*`; 13 `$ai_alarm`; 13
`$alarm_sound`), and the one-shot card game (checkresponse 791–837, broken 785–788, `chairthread
delete` at 805, no re-seat path) — was independently re-verified and left unchanged.

**Sources** (extracted with python zipfile from `G:\GOG\Medal of Honor - Allied Assault War Chest\`):

| File | Pak | Size | Notes |
|---|---|---|---|
| `maps/m2l2a.scr` | `main/Pak5.pk3` | 35,882 B | the retail map script (line numbers below refer to this copy) |
| `global/alarm_system.scr` | `main/Pak0.pk3` | 39,526 B | Benson 'elmagoo' Russell's alarm/zone/backup system |
| `global/items.scr` | `main/Pak0.pk3` | 11,880 B | papers/uniform inventory + HUD |
| `global/cardgame.scr` | `main/Pak0.pk3` | 19,275 B | Mackey McCandlish's card players |
| `anim/disguise_{halt,wait,papers,accept,deny,enemy,salute}.scr` | `main/Pak0.pk3` | 371–1,806 B | the challenge animations the ENGINE plays |
| `models/items/papers.tik`, `papers2.tik` | `main/Pak0.pk3` | 976/963 B | the InventoryItem definitions |
| `models/human/animation/scripted/table.tik` | `main/Pak0.pk3` | — | card-game anims incl. cardhand attach |
| entity lump | `map_entities/m2l2a_entities.txt` | 1,206 ents | keyvalue prefixes `$`/`#` stripped |

Engine citations are `openmohaa-hzm/code/fgame/...` (OpenMOHAA reimplementation of retail fgame; disguise
code is unmodified by our fork except where noted).

Runtime override note: under the War Chest BT launch (`com_target_game 2`) `maintt/pak1.pk3` overrides
`global/items.scr` (rewritten, but papers/uniform cases behave identically — maintt items.scr:200–277,446–459),
`global/alarm_system.scr` (one change: the gofor-alarm sighttrace becomes `canseenoents` at line 607) and
`global/cardgame.scr` (cosmetic reformat only). `main/pak7.pk3` patches `global/alarmer.scr` (a hint-print
guard only; alarmer.scr is not used by m2l2a anyway — m2l2a uses alarm_system.scr).

---

## 1. Engine substrate: how the disguise actually works

### 1.1 The player side — two flags and a timestamp

- `Sentient::m_bHasDisguise` / `m_bIsDisguised` / `m_ShowPapersTime` (sentient.h:205–208).
- Script bridge: player property `has_disguise` (player.cpp:1161/1171, setter at 11360); `is_disguised`
  is **EV_GETTER only** (player.cpp:11350) — script can never force it.
- Every frame, **only in `g_gametype == GT_SINGLE_PLAYER`** (player.cpp:5478–5495):
  `m_bIsDisguised = false`, then it becomes true iff **all** of:
  1. `m_bHasDisguise` set (script gave you the disguise),
  2. `!level.m_bAlarm` (alarm silent),
  3. active main weapon is **null or an InventoryItem** (player.cpp:5484) — i.e. holstered, or papers in hand,
  4. **no actor currently attacking has the player as enemy** (player.cpp:5487–5493). One blown actor
     un-disguises you for *everyone* until it dies or disengages.
- `level.m_bAlarm` and `level.m_iPapersLevel` are script-bridged as `level.alarm` and `level.papers`
  (level.cpp:93–104, 165–175; storage 769–770; get/set 2064–2099). items.scr writes `level.papers`,
  alarm_system.scr writes `level.alarm`; the engine reads both.

### 1.2 Showing papers — the exact mechanical chain

1. Papers are a weapon-inventory item: `classname InventoryItem`, `weapon_class ITEM`
   (papers.tik init; inventoryitem.cpp:61 `WEAPON_CLASS_ITEM`).
2. The **`toggleitem`** console command (bound key; hint printed by m2l2a.scr:584–585) is
   `EV_Sentient_ToggleItemUse` (sentient.cpp:462, handler sentient_combat.cpp:953): if an InventoryItem
   is in hand → switch back to last weapon; otherwise → `useweaponclass item1`, which raises the papers
   as the active "weapon" (client side: cg_consolecmds.c:639).
3. With papers raised, **primary fire** plays the papers' `fire` anim (`show_papers.skc`), whose server
   frame commands `30/40/50/60/70 activatepapers` (papers.tik animations block) fire
   `EV_InventoryItem_Activate_Papers` → `GetOwner()->m_ShowPapersTime = level.inttime`
   (inventoryitem.cpp:81–84). That timestamp is the whole "I showed my papers" signal.
4. Holding papers keeps you disguised (rule 3 above), so raising them never breaks cover.
5. papers.tik vs papers2.tik differ in shader (`wehrpass` vs `wehrpass_l2`), rank, and papers.tik's
   extra `visa` anim (papers_visa.skc, absent from papers2.tik); the LEVEL lives in
   `level.m_iPapersLevel`, not in the item.

### 1.3 The actor side — think types and the challenge state machine

Actors gate everything on `EnemyIsDisguised()` (actor.h:2159–2174): true iff
(`m_bEnemyIsDisguised` or enemy's live `m_bIsDisguised`) **and** `!m_bForceAttackPlayer` **and**
`m_ThinkState != THINKSTATE_ATTACK`. Consequences already verified this session and re-confirmed here:

- `attackplayer` (script) → `m_bForceAttackPlayer` **one-way latch**, cleared only in the Actor
  constructor (actor.cpp:3092 area) — one call permanently blinds that actor to the disguise.
- An actor already in ATTACK think never re-respects the disguise.
- Threat: `ActorEnemy::UpdateThreat` returns 0 for a disguised enemy (actorenemy.cpp:164–166) but the
  disguised player is **retained** as current enemy at zero threat (actorenemy.cpp:446) — so the actor
  keeps "watching" you.
- The attack transition itself is blocked while disguised: `PassesTransitionConditions_Attack` returns
  false if `EnemyIsDisguised()` (actor.cpp:8941).
- `m_bEnemyIsDisguised` snapshots: on SetEnemy (actor.cpp:6906 — note `m_bHasDisguise && (m_bIsDisguised
  || !CanSeeEnemy)`), refreshed every sight check (actor.cpp:4033).

**The challenge transition** — `PassesTransitionConditions_Disguise` (actor.cpp:8955–9007):
throttled to 5 Hz (`m_iNextDisguiseTime`, 8964–8968); requires a confirmed enemy who is disguised;
`|Δz| ≤ 48`; 2-D distance strictly between 32 and `disguise_range`; and a sight trace from the actor's
eye to **`G_GetEntity(0)`'s centroid** (actor.cpp:8994) — the hardcoded SP player-0 assumption.
`CheckForTransition` (actor.cpp:8861–8879) skips any think whose `PassesTransitionConditions` is NULL.

**Per-actor tunables** (engine defaults actor.cpp:3024–3027: period 30 s, range 256, level 1;
`m_iNextDisguiseTime = 1` so first challenge is immediate):

| keyvalue | event | notes |
|---|---|---|
| `type_disguise` `salute\|sentry\|officer\|rover\|none` | actor.cpp:8228–8235 | invalid → ScriptError + fallback salute. **Default think map is SALUTE** (actor.cpp:8440) |
| `disguise_level` 1 or 2 | actor.cpp:8281–8289 | anything else → reset to 1 + ScriptError |
| `disguise_range` | actor.cpp:9216–9217 | stored squared |
| `disguise_period` | actor.cpp:9237 | seconds → ms; re-challenge cooldown |
| `disguise_accept_thread` | actor.cpp:8244–8252 | fired at the moment of acceptance (actor_disguise_common.cpp:77–79) |

**The five think types** (registered actor.cpp:6708–6712):

- **`none`** (`InitDisguiseNone`, actor_disguise_common.cpp:27–30) — only `IsState` is set;
  `PassesTransitionConditions` stays NULL, so the actor **never challenges**. Combined with the
  zero-threat rule it simply ignores a disguised player. This is what card players, scientists
  and workers use.
- **`salute`** (actor_disguise_salute.cpp) — challenge = play `anim/disguise_salute.scr`
  (fullbody salute, weapongroup-dependent) then back to IDLE on animation end. Never asks for
  papers, cannot deny. Re-challenge after `disguise_period` (End_DisguiseSalute).
  Mid-salute, if the disguise drops or the alarm rings → ATTACK (Think_DisguiseSalute).
- **`sentry`** (actor_disguise_sentry.cpp) — the only genuine papers check. States (bodies in
  actor_disguise_common.cpp): WAIT (`disguise_wait.scr`; approach to half-range or 3 s inside 256 →
  PAPERS; walk away → IDLE) → PAPERS (`disguise_papers.scr`; **12 s** to show papers, else ENEMY;
  move > 256 away → HALT). On papers shown (`m_iEnemyShowPapersTime < m_Enemy->m_ShowPapersTime`,
  snapshot taken at Begin): `level.m_iPapersLevel < m_iDisguiseLevel` → **DENY** (`disguise_deny.scr`
  prints "You don't have the proper papers!" / "Come back when you have them." — **non-hostile**, back
  to IDLE after 3 s, re-challenge after period) else → fire `disguise_accept_thread`, **ACCEPT** →
  after 3 s `SetThink(THINKSTATE_DISGUISE, THINK_DISGUISE_SALUTE)` (common.cpp:121–129) — an accepting
  sentry becomes a mere saluter **permanently**.
- **`officer`** (actor_disguise_officer.cpp) — no WAIT/approach phase: Begin transitions straight to
  the PAPERS state, which here is `State_Disguise_Fake_Papers` (common.cpp:85–101): **showing papers →
  instant ENEMY**; not showing → ENEMY after 12 s; walking away > 256 → HALT. HALT → ATTACK after
  1.5 s; ENEMY → ATTACK after 3 s (common.cpp:103–119) — worst case ATTACK ≤ 15 s from challenge. Its
  state switch has no ACCEPT/DENY at all. **An officer's challenge always ends hostile** — the retail
  "officers see through your disguise" rule is this code.
- **`rover`** (actor_disguise_rover.cpp) — identical to officer (Begin also goes straight to
  `State_Disguise_Fake_Papers`; its ACCEPT case is unreachable). m2l2a ships zero rovers.

All four active types bail to ATTACK the moment `level.m_bAlarm` is true or `EnemyIsDisguised()`
turns false (each Think_*), and `FL_NOTARGET` on the enemy suppresses the hostile ends everywhere.
The anims themselves are data: engine plays `anim/disguise_*.scr` via the string table
(scriptmaster.cpp:332–338).

---

## 2. The retail m2l2a mission, step by step

Map spans x −4816…−1518, y −976 (north, flak/crane end) … −6949 (south, officer quarters);
player start `info_player_start` at **−4816 −3880 −36** (entity lump; parsed summary line 4).

### 2.1 Spawn

- `main:` (m2l2a.scr:5) preps crates, `exec global/loadout.scr` (line 14) — loadout gives
  **silenced pistol, Springfield, MP40, stielhandgranate, pistol drawn** (Pak0 global/loadout.scr,
  m2l2a block: `useweaponclass pistol`), and `exec global/cardgame.scr` (line 15).
- After `level waittill spawn` (line 22): `level.ai_alarm_backup_time = 15`, `_max = 4` (33–34),
  **`$player.has_disguise = 1` (line 35)** — the disguise flag is live from the first frame, *before*
  any pickup: holstering in your US uniform already disguises you mechanically. The uniform pickup
  only swaps the player model and satisfies the objective.
- `level.alarm = 0` (36), objectives 1–3 registered (38–41), `level.alarm_sound = m2l2_alarm` (43),
  `alarm_system_setup` launched (45), the 10 named `$ai_alarm` actors bound via
  `find_guy` (46–57), `add_item "explosives"` silently (62 — you carry the demo charge from the start).
- Hints (197–205): "Press ( Holster-key ) to holster your weapon." / "If your weapon is not holstered
  **your cover will be blown**." Retail **never takes your weapons** — the entire stealth contract is
  "holstered (or papers in hand) = disguised".

### 2.2 Uniform + papers pickup — what `likeynorway` does in RETAIL (m2l2a.scr:578–610)

Trigger: `trigger_useonce` at −4427 −3995 −11 with `setthread likeynorway` (entity lump line ~206),
sitting on `$suit` (items//officer_uniform.tik prop, −4437 −3992) and `$papers1`
(animate/pulse_papers1.tik glowing prop, −4416 −3994) — one **use** press takes both:

1. Sets the two locker-room guards (`find_name` guythatlikesnorway/-hates-, both `targetname ai_alarm`,
   no `type_disguise` key → engine default salute) to `type_disguise "none"` for the scene (579–580).
2. `$suit remove`, `$papers1 remove` (581–582).
3. Prints "Be prepared to show your papers when asked." + the **`toggleitem`** key hint (583–585);
   plays both pickup sounds (586–587).
4. Objective 1 complete → current objective 2 (588, via `objective1` at 336–340).
5. `add_item "papers_level1"` → HUD icon, `$player item models/items/papers.tik`, **`level.papers = 1`**
   (items.scr:186–198). `add_item "uniform"` → **`$player.has_disguise = 1`** (redundant with line 35)
   and **`setcvar g_playermodel "german_waffenss_officer"`** (items.scr:249–261) — the engine swaps the
   player model next frame (player.cpp:5467–5473). (`remove_item "uniform"` would revert model and
   clear has_disguise — items.scr:390–394 — never called in m2l2a.)
6. Unlocks/open `$likeynorwaydoor`, walks the two guards in, runs their six-line Norway conversation
   (593–603), then sets both to `type_disguise "salute"` and sends them on patrol (604–608).
7. **`$suckyfatty hearing 1024`** (609) — the card players' hearing is raised after the scene
   (map start set it to 200, line 163).

### 2.3 The card game as retail wrote it (global/cardgame.scr, main/Pak0)

Setup in m2l2a: one `animate_furniture_cardtable` `targetname "cardgame"` targeting `suckyfatty`
(entity lump lines 40–48); **three** `ai_german_wehrmact_soldier` share `targetname suckyfatty`
(origins −4188 −4088 −36, −4132 −4096 −36, −3941 −3960 −32 — the room after the locker room).
No `$sit` entities exist in m2l2a (sitman/sitthink path unused; that path is m1l2a/m4l3 furniture).

Three targets → `cardgame3` (cardgame.scr:50–51, 264–332). Per player (272–317):

- `type_disguise "none"` (275) — card players never challenge.
- teleported onto table tags `tag_actor01..03`, `.mumble = 0`, **`holster`**, `.no_idle = 1`,
  `.originalhealth` saved then **`health = 2`**, **`noticescale = 1`** (279–290) — near-blind,
  one-shot-kill while seated.
- `thread checkresponse` (295), random chair-death anim registered as deathanim (297–302),
  `thread cardgame3anim <n>` (304) — the seated card-play animation driver,
  a spawned notsolid `furniture/cardchair.tik` under each (307–312), `thread chairdeath` (315).
- The table itself loops `self.current = 1..14` forever (319–329); each step waits until a
  `cardgame3anim` thread finishes the step's anim and sets `level.carddone` (the nominal timeout
  `level.time + 3000` at 325 is a retail ms-vs-s slip — a 3000-second dead-man, so the cadence is
  anim-length-driven); `cardgame3anim` (459–770) maps each step to
  `Chair_actor{1,2}_{idleloop,fish,queen,king,drawcard}` anims.

**Card hands**: the attach is anim data, not script — `models/human/animation/scripted/table.tik`:
`chair_actor1_idleloop` / `chair_actor2_idleloop` have `first attachmodel models/miscobj/cardhand01/02.tik
tag_weapon_left` (table.tik lines 43–55); the hands are removed at frame 3 of `chair_alert_stand` /
`chair_curious_stand` (lines 21–32). (This is the exact source of the coop attach-retry spam: every
idleloop restart re-runs `first attachmodel`.)

**When a retail card player may legitimately stand — `checkresponse` (791–837):**

```
while ((self.thinkstate == "idle") && (self.creator.broken == 0))
    waitframe
```

1. **Own thinkstate leaves "idle"** — any transition (curious from noise/sight, attack, pain, grenade)
   sampled *every frame*; a single-frame flicker ejects.
2. **Table cascade**: the first player to pop runs `thread broken` (799) which sets
   `self.creator.broken = 1` after 0–1.5 s (785–788) — the other two stand even if still idle.
3. **Death** — `chairdeath` (66–94) swaps in an animated falling chair.

On standing: `lookat $player`, AI disabled, **`self.chairthread delete`** (805 — the anim driver is
destroyed), `chair_alert_stand` anim, unholster, restore `originalhealth`, clear deathanim, 6 s of
re-unholster loops, chair plays `chair_alert_stand_end` (804–834). **There is no code path that ever
re-seats a card player** — standing is designed one-way; `level.carddone`/table loop keep running
pointlessly. Retail stays stable only because a disguised ent-0 player produces zero threat and no
footstep notice, so `thinkstate` simply never leaves "idle" pre-alarm.

Map-side extras: `wakeupcardplayers` (m2l2a.scr:231–249) polls `level.alarm` and on alarm raises
`$suckyfatty hearing 512` (+easy-skill accuracy nerfs); `cardplayersdeath` (189–195) — on a card
player's death, `$suckyfatty attackplayer` unless `level.cardplayers == 3` (that level var is never
set in the file: intent "survivors fight back on a table kill"; one of our known raw `attackplayer`
sites). All three card players also carry vestigial `find_name "guythathatesnorway"` keys but are NOT
`targetname ai_alarm`, so `find_guy` never returns them (it scans only `$ai_alarm` —
alarm_system.scr:1034–1049).

### 2.4 Actor census — disguise keyvalues (entity lump, all 51 `ai_*` entities)

| `type_disguise` | count | who |
|---|---|---|
| `salute` | 34 | kriegsmarine/wehrmacht rank & file, incl. all 3 card players |
| `none` | 10 | scientists (guy1–3 + lab), misc workers (welders, hammerer, wrench, crate) |
| `sentry` | 3 | elite sentries: **goatsbutt** (−3912 −3480 −286, level 1, accept→`sentry1trigdisable`), **sentry2dude** (−2736 −6256 −494, **level 2**, accept→`sentry2accept`, `leash 64`, `fixedleash 1`, `noticescale 1`), unnamed (−3692 −3892 −490, level 1) |
| `officer` | 2 | **officer1** (−4048 −6048 −488, range 256; script sets `.maxdist = 4000` m2l2a.scr:151) and an unnamed Wehrmacht officer (−4016 −2820 −516, **range 64** — brush-past only) |
| (unset → default salute) | 2 | the two Norway locker-room guards (script-managed, §2.2) |

Every actor that has the keys uses `disguise_range 256` (except the range-64 officer),
`disguise_period 15`, `disguise_level 1` — **exactly one actor in the whole map requires level-2
papers: sentry2dude**. 13 actors are `targetname ai_alarm` (alarm ringers, §2.6).

### 2.5 The papers LEVEL system in m2l2a

- Level 1 papers: with the uniform (§2.2) → `level.papers = 1`. Satisfies every level-1 sentry
  (goatsbutt, the unnamed elite): State_Disguise_Papers accepts, runs accept-thread, actor demotes
  itself to saluter.
- **The upgrade**: `$papers2` (animate/pulse_papers2.tik at −3606 −6930 −268, far-south officers'
  quarters past officer1's area) + `trigger_useonce` `setthread papers2pickup` (−3611 −6949 −244).
  `papers2pickup` (m2l2a.scr:329–334): suppress the hint, remove prop,
  `remove_item "papers_level1"` + `add_item "papers_level2"` → `level.papers = 2`
  (items.scr:200–212; remove path 380–389 briefly zeroes it).
- **Who sees through level 1**: only sentry2dude (`disguise_level 2`). His DENY is non-hostile
  (3 s → idle, re-challenge in 15 s) — you are *told* to go find papers2, not attacked.
- Player guidance: `$papers2hint` trigger (−2896 −6336) prints "You need a new set of papers to
  procede past this point." once (m2l2a.scr:181–188), suppressed after pickup (330).

### 2.6 The alarm system (global/alarm_system.scr + m2l2a wiring)

Setup `alarm_system_setup` (14–386) requires `$zone_trigger`, `$alarm_switch_trigger`, `$ai_alarm`,
and 4 `$waittrigger_*` relays (m2l2a has all: entity lump). m2l2a wiring:

- **20 `zone_trigger`** brushes (`trigger_multipleall`) partition the map into zones
  `zone1,2,25,3,4,5,6,7,8`, each with an `alarm_switch` number (1,2,3,5) and a `target` pointing at a
  zone-center chain (t1511, t1516, t1523, t1554, t1524, t1535, t1549, t1550, t1563). Whoever touches
  one gets `.zone/.zone_number/.zone_index` stamped (zone_trigger_thread, 401–416) — `$player.zone_index`
  drives backup spawning.
- The AI chained off each zone center are **converted to spawners at setup**
  (spawner_create_targetname, line 279) — they don't exist until the alarm rings.
- **4 alarm switches** (`trigger_use` `alarm_switch_trigger` → animate/alarmswitch.tik models t1538/
  t1547/t1545/t1543 at −3846 −3817, −3971 −3718, −4427 −2627, −3828 −6146). A switch trigger fires the
  master (750–763); the master **toggles**: alarm off→on (anim turnon, start backup+sound threads) or
  on→**off** (769–812) — the switches are `trigger_use`, so the player can walk up and shut the alarm
  off; disguise then resumes for non-attacking actors.
- **`$ai_alarm` actors** (13 here): setup forces `type_attack "alarm"` + `alarmthread = ai_alarm_alerted`
  (422–442). When one is alerted it pushes itself on a stack (471–505); `ai_gofor_alarm` (546–744) picks
  a living, still-attacking, player-visible ringer (visibility: sighttrace line 607; maintt variant:
  `canseenoents`), races him to the zone's switch **only while he's closer to it than the player is**
  (646–657), and on arrival **`douse $player`** on the switch trigger (730) → alarm on.
- Alarm ON effects: `level.alarm = 1` + `level.alarmlights = 1` (781–782) → engine `m_bAlarm` → player
  can't be disguised (§1.1) and every disguise-think actor goes ATTACK (§1.3); loopsounds on all 13
  `$alarm_sound` dummies (818–850, alias `m2l2_alarm` via m2l2a.scr:43); **backup spawning** (856–971):
  every 15 s, per the player's current zone, respawn missing chain guys up to 4 alive
  (`ai_alarm_backup_total`), each running `alarm_system_backup_dude` (977–1020): runto player,
  then self-remove once dead-or-unseen and > 2048 away (997).
- Map add-ons: `playalarmsound` PA announcements every 85 s while ringing (473–490);
  `alarmall` helper — force-ring switch 1 (272–277, unused in the file); intercom chatter only while
  the alarm is off (`intercomsoundcycle`, 502–550).

### 2.7 Every SCRIPTED forced-detection moment (cover blown regardless of disguise)

Each of these carries at least one `attackplayer` — the **permanent** per-actor blind-to-disguise
latch (§1.3) — except where item 6 notes otherwise (welders arm but never latch):

1. **Sentry checkpoint 1 tripwires** — `$sentry1trig` relay (−4024 −3240 −232) fed by two
   `trigger_multiple` at −4072 −3104 −216 and −4352 −3232 −216 (past goatsbutt's stair post).
   `sentry1alarm` (m2l2a.scr:799–807): goatsbutt shouts `den_alarm_01c` then **`attackplayer`**.
   Disarmed by showing papers to goatsbutt: his `disguise_accept_thread` `sentry1trigdisable`
   (795–797) makes the relay nottriggerable.
2. **Sentry checkpoint 2 gate** — `$sentry2trigger` relay (−2688 −6360 −456) fed by two
   `trigger_multiple` (−2676 −6212, −2616 −6356) and a `trigger_hurt` (−2676 −6480).
   `sentry2thing` (223–228): sentry2dude leash 2048 + **`attackplayer`**. Disarmed only by a
   **level-2** papers acceptance (`sentry2accept`, 791–793).
3. **Blowing the Naxos** — `$naxos` trigger (−4414 −1898 −124, on the prototype; you carry explosives
   from spawn) → `objective2` (342–351) → `ohnothenaxos1` (390–430): scientists guy1–3 detach
   clipboards, unholster, and **`attackplayer`** (forced, scripted, disguise irrelevant), plus
   `blowupthenaxos` swaps smashed models + fire (380–388). The same `ohnothenaxos1` is the scientists'
   `alarmthread` (`type_attack "alarm"`, sciwalkto 1055–1065 / startwallscience 1252–1255), so alerting
   any lab scientist triggers the full trio.
4. **Lab small talk trap** — `sciencetrig` (−4002 −2070 −154) → `sciencetalk` (754–789): if the alarm
   is already up, `self attackplayer` immediately (756–758); otherwise guy3 walks over and delivers
   five VO lines — pure flavor, no detection.
5. **Card-table kill** — `cardplayersdeath` (189–195): any card player dying → `$suckyfatty
   attackplayer` (§2.3).
6. **Worker self-defense** — welders and the sledgehammer guy are `type_attack "alarm"` with
   alarmthreads `weldinginterupt` / `cower` (957–1004, 916–949): once *alerted* (player no longer
   disguised near them), they break animation and draw a Walther P38. **Only the sledgehammer guy's
   `cower` ends in `attackplayer` (948)** — `weldinginterupt` (980–992) arms the welder and re-enables
   AI but never latches, so an alerted welder fights by ordinary AI hostility and would re-respect a
   regained disguise. `scialarm` (1331–1335) is the scientists' version and DOES latch (1334). These
   fire only after cover is already lost; cower and scialarm are the raw `attackplayer` latches here.
7. **Card wake helper** — `unholsterweapon` (267–270) generic `unholster + attackplayer` helper (wired
   from entity `thread` keys).

Not forced-detection but often mistaken for it: **officer challenges** (§1.3) — engine-driven; any
officer engagement (officer1 patrolling after `movetheflak`, or the range-64 officer mid-map) ends in
ATTACK within ≤ 15 s no matter what you show (papers shown: ENEMY instantly, ATTACK +3 s; not shown:
ENEMY at 12 s, ATTACK +3 s); retail's design is "stay ≥ 256 units from officers".

### 2.8 Mission spine / endgame

1. Spawn → uniform+papers1 (one use press) → walk past the card room, downstairs into the pens.
2. Show papers to level-1 sentries when challenged (or just never enter their 256-unit bubble);
   salute-types only salute; workers/scientists ignore you.
3. `movetheflak` trigger (−3875 −976 −438, north end) → `moveaflak` (809–815) threads `cometolife`
   (817+) and autosaves if the alarm is silent: music, crane run, welders/hammerer/crate/wrench loops
   start, **officer1 begins his patrol** (officer1go, 880–900).
4. Plant explosives on the Naxos (`$naxos`) → prototype destroyed, scientist trio hostile, objective 2
   complete → objective 3 (342–351).
5. South wing: grab `$papers2` (level 2), pass sentry2dude's checkpoint east.
6. `$endlevel` trigger (−2309 −4007 −408, the second U-boat) → `endmission` (559–563):
   objective 3 complete + `exec global/missioncomplete.scr m2l2b 1` → next map.
7. Deaths of the sledgehammer/wrench/welder workers carry into m2l2b via `game.m2l2*dead`
   (1341–1357).

---

## 3. Retail facts most load-bearing for any coop redesign

1. Disguise is **ent-0, single-player-only physics**: the whole player block is inside
   `g_gametype == GT_SINGLE_PLAYER` (player.cpp:5478) and the actor challenge sight-traces
   `G_GetEntity(0)` (actor.cpp:8994). Nothing about papers/challenges was ever written for >1 player.
2. Retail **keeps all weapons**; stealth = holstered-or-papers-in-hand, enforced per frame. There is no
   weapon confiscation anywhere in m2l2a.
3. `$player.has_disguise = 1` is set at map spawn (m2l2a.scr:35), *before* the uniform: the pickup is
   cosmetic (model swap) + objective; mechanically you are disguise-capable from frame 1.
4. Showing papers is `toggleitem` → papers InventoryItem in hand → primary fire → `activatepapers`
   frame commands → `m_ShowPapersTime` timestamp. That timestamp vs. the actor's Begin-snapshot is the
   entire protocol.
5. `attackplayer` = permanent disguise blindness for that actor (constructor-only reset); m2l2a retail
   itself uses it liberally (7 sites, §2.7) but **only at moments where cover is already scripted-lost**.
6. Exactly one level-2 gate exists (sentry2dude); DENY is non-hostile by design — the papers-level
   system is a courteous door-lock, not a detection mechanic.
7. Officers/rovers can never accept papers (`State_Disguise_Fake_Papers`); their challenge is a timed
   death sentence — retail balance is spacing (range 256/64), not papers.
8. Alarm is a level-global bool that is **toggleable at any switch by the player**, voids the disguise
   while up, and drives per-zone 4-cap/15 s reinforcement respawning off `$player.zone_index`.
9. The card game is one-shot by construction: per-frame `thinkstate == "idle"` sampling + a 0–1.5 s
   `broken` table cascade + `chairthread delete` on stand, with **no re-seat path**. Any transient
   thinkstate flicker (exactly what coop's extra un-disguised players cause) permanently ends the scene
   — retail never needed a re-arm because a disguised solo player generates zero threat and no
   footstep notice.
