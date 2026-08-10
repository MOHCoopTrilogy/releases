# 03 - The HZM coop layer as shipped (v1.2.x baseline, before the 2026-08-08/09 stealth session)

Research doc for the m2l2a stealth-route redesign. Read-only survey of the disguise/stealth
machinery **as it exists at the mod repo's HEAD**, i.e. before any of our uncommitted
`[user 2026-08-08]` / `[user 2026-08-09]` working-tree changes.

## CORRECTIONS (verification pass, 2026-08-09)

Independently re-verified against the nested git repo (`git show HEAD:`), the retail Pak5
`maps/m2l2a.scr`, and the engine sources. Every label/line citation checked in sections 2-10
was confirmed exact (itemhandler/weaponstate/aihandler/aisquad/morale/aimaneuver/main.scr/
m2l2a.scr/cardgame/alarm_system/autoexec/items.scr, plus player.cpp:5477-5495,
actor.cpp:3092/9291-9295, actorenemy.cpp:164/446, actor.h EnemyIsDisguised,
PassesTransitionConditions_Disguise's `G_GetEntity(0)` at actor.cpp:8994; `is_disguised` is
EV_GETTER-only at player.cpp:1149-1158 while `has_disguise` has a setter). The "~562 inserted
lines across 10 files" figure was reproduced exactly (562 insertions across the 10 stealth
`.scr` files, `--ignore-cr-at-eol`; `coop_defaults.cfg` adds 37 more). Four fixes were made:

1. **Section 7 — `:700` is not a retail attackplayer site.** Retail Pak5 `m2l2a.scr` has 11
   `attackplayer` sites; HEAD has 12, and the one addition is exactly `:700` inside
   `waitForEnemy` — the `[200]` coop func described in the preceding bullet. It was
   double-listed under "retail" sites; removed from that list.
2. **Provenance — "shipped public baseline" was imprecise.** `f694b31` (committed 08-07
   15:58) is what **manifest-1.2.201** (committed 08-07 15:59) points at. The *current*
   public release is **v1.2.3**, whose manifest was created 08-08 14:54 with **no
   corresponding mod commit** — it was packaged from the 08-08 working tree, so it may
   include early-08-08 uncommitted fixes. HEAD is still the right analysis baseline; the
   claim about what the newest manifest ships was tightened.
3. **Provenance — the working tree is NOT "HEAD + stealth layer only".** The full
   uncommitted diff is ~5,850 insertions across 67 files (ignoring CRLF churn); the stealth
   layer is only ~600 of it. Substantial unrelated uncommitted work rides along
   (`ui/coop_sr.urc` ~1,787, `maps/m3l1b.scr` ~594, `coop_mod/bunker.scr` ~502,
   `coop_mod/challenges.scr` ~436, the m2l2b Enigma/bomb work ~292, ...). The `git show
   HEAD:` method is unaffected, but "working tree minus HEAD" must not be read as "the
   stealth layer". A caveat was added to the provenance section.
4. Trivial cite fix: the salute-tail engine-cooldown wait+comment is at `disguise_salute.scr:61`,
   not `:62`.

## Provenance / method

- The mod tree is its **own nested git repo** at `C:\mohaa-coop-dev\hzm-mohaa-coop-mod`
  (the outer `C:\mohaa-coop-dev` repo tracks only the release pipeline - allowlist
  `.gitignore`). Mod HEAD = `f694b31` "v1.2.201: m3l1b coop pass..." (committed 08-07
  15:58) - the last committed mod state, and what **manifest-1.2.201** points at. The
  *current* public release is **v1.2.3** (manifest created 08-08 14:54, **no matching mod
  commit** - packaged from the 08-08 working tree, so it may carry early-08-08 uncommitted
  fixes). HEAD remains the correct committed baseline for this analysis.
- Every file below was read via `git -C hzm-mohaa-coop-mod show HEAD:<path>` (exported to
  scratchpad, so all line numbers are HEAD line numbers). No working-tree contamination.
- HEAD already contains committed `[user 2026-07-*]` / `[user 2026-08-0x]` (x<=7) work from
  earlier sessions (e.g. bug-1458 waittill shims in m2l2a.scr, bug-1477 den_alarm_12a in
  aihandler.scr). Those ARE baseline. Only `[user 2026-08-08]`/`[user 2026-08-09]` marks the
  current stealth saga, and none of it is committed (verified: `git grep "user 2026-08-08"
  HEAD` and `-09` both return nothing).
- **Caveat:** the working tree carries much more uncommitted work than the stealth layer -
  ~5,850 inserted lines across 67 files in total (`--ignore-cr-at-eol`), of which the
  stealth layer is only ~600. Unrelated riders include `ui/coop_sr.urc` (~1,787),
  `maps/m3l1b.scr` (~594), `coop_mod/bunker.scr` (~502), `coop_mod/challenges.scr` (~436)
  and the m2l2b Enigma/bomb work (~292). "Working tree minus HEAD" is therefore NOT a
  synonym for "the stealth layer"; use the `[user 2026-08-08/09]` tags to scope it.
- **`coop_stealthStart` does not exist at HEAD.** `git grep coop_stealthStart HEAD` returns
  nothing; it appears only in the uncommitted working tree (`coop_defaults.cfg`,
  `maps/m2l2a.scr`). See the last section.

## 1. Upstream's disguise model in one paragraph

The engine only computes disguise in single-player: `player.cpp` ~5480 sets
`m_bIsDisguised = true` iff the active weapon is absent or an `InventoryItem` (papers),
inside a `g_gametype == GT_SINGLE_PLAYER` block, and `is_disguised` is an EV_GETTER (script
can read, never write). Upstream's answer is a **three-layer sandwich**:

1. **Engine latch via gametype windows.** `main.scr::changeGameType` (main.scr:1647) flips
   the `g_gametype` cvar to 0 for ~1ms so the SP-only block runs once, then flips back to 2.
   During the window the mod deactivates player weapons and forces attacking actors idle so
   the engine's two criteria pass, and sets `player.has_disguise = true`. Result: the
   engine-side `m_bIsDisguised` is **latched true and then frozen** (the SP block never runs
   again in gametype 2). From that point every German's engine senses (`ActorEnemy::
   UpdateThreat` threat 0, `Sentient::IsTeamMate`, `Actor::NoticeFootstep`) treat every
   player as a teammate, full-time, weapon in hand or not.
2. **Script-side mirror of the "real" disguise state.** Because the engine is frozen, the
   mod tracks what `m_bIsDisguised` *would* be in the per-player flag
   `coop_isDisguised`, updated by `weaponstate.scr` on every holster/unholster
   (raise weapon -> false, put away -> true). `itemhandler.scr::setIsDisguised` (:2126) is
   the single writer. This flag is script-only - the engine never sees it.
3. **Forced-attack layer as the enforcement arm.** All *detection* of a blown cover is
   re-implemented in script (`aihandler.scr::disguiseHandler` 1 Hz poll + `sentientIsSeen`/
   `sentientIsHeard` cascades + coop inserts in the `anim/disguise_*.scr` behaviors), and the
   only lever it has to make an engine-blinded actor shoot a disguised player is the script
   command `attackplayer` -> `Actor::ForceAttackPlayer()` -> `m_bForceAttackPlayer`, a
   **one-way latch** cleared only in the Actor constructor (actor.cpp:3092). One call makes
   that actor ignore disguise forever.

So: *engine says "teammate", script decides "made you", attackplayer makes it stick
permanently.* There is no per-actor un-blow.

## 2. itemhandler.scr - the give/take machinery (HEAD)

All in `coop_mod/itemhandler.scr`:

| label | line | what it does |
|---|---|---|
| `managePlayerInventory` | :695 | per-spawn entry. `level.coop_noWeapon` early-out (:711 - papers-only maps get NO loadout at all). If `coop_enableDisguises && !is_disguised` -> `giveDisguiseOnSpawn` (:723-726). Re-give uniform model if `coop_uniformOnSpawn` (:728-732). `givePapersFlag` if `level.coop_itemPapers` (:734-736). |
| `giveDisguise` | :891 | per-player window. Serialized on `level.coop_disguisingInProgress` (:898-908). Criterion 1: if `anyEnemiesInAttackState` -> `resetEnemyThinkstates` (:911-914). Criterion 2: `deactivatePlayerWeapon` (:917). Window: `changeGameType 0 0` -> `has_disguise = true` + `coop_hasDisguise = true` -> `changeGameType 2 game.ms` (:919-922). Then re-activate weapon + `setEnemyAttackStates` (:924-929). |
| `giveDisguiseToAll` | :945 | same dance for all players at once. **Early-outs if `level.coop_enableDisguises` is already true or `level.alarm`** (:950). Verifies with `anyPlayerNotDisguised` (reads the engine getter, :982); on failure clears flags and recursively retries (:983-990); on success prints "You are now disguised!", seeds each player's `coop_isDisguised` from their held item (:996-1001) and **starts `aihandler::disguiseHandler`** (:1004). If alarm raised mid-give: gives up permanently (:1006-1009). |
| `giveDisguiseOnSpawn` / `OnConnect` | :875 / :864 | wrappers; OnSpawn tallies time spent in the window into `coop_spawnTimeOffset` (loadout timing bookkeeping). |
| `deactivatePlayerWeapon` | :1049 | stores `coop_lastActiveWeapon`, `deactivateweapon "dual"` - the "weapon out of hand" half of the engine criteria. Comment (:1043-1047) states the model explicitly: "we only enable SP engine disguise checks for 1 ms (gametype hack)". |
| `takeAllDisguises` | :1092 | **permanent, global off-switch.** Early-out if disguises already off (:1095). Sets `coop_enableDisguises = false`, `coop_uniformOnSpawn = false`, then one window in which every player gets `has_disguise = false`, `coop_hasDisguise/coop_isDisguised = false` (:1102-1108). Nothing ever re-enables on the same map (a fresh `giveDisguiseToAll` could, but no shipped map calls it twice). |
| `takeDisguise` | :2136 | per-player version, same window pattern. |
| `setIsDisguised` | :2126 | writes `coop_isDisguised` only when `coop_hasDisguise` (or forced). Comment: "isDisguised will turn on and off depending on whether they have a weapon in their hand or not". |
| `giveUniformToAll` / `giveUniformToPlayer` | :851 / :810 | cosmetic layer - swaps player model to `level.coop_disguiseUniform` (default `german_waffenss_officer`), sets `coop_uniformOnSpawn` so respawns keep it. Backed out by `takeUniformFromPlayer`. |
| `givePapersFlag` / `enableClickablePapers` | :2206 / :2231 | papers UX: while a guard runs `disguise_papers`, a poll lets an empty-handed player press primary fire to `use` the papers item (:2243-2246). |
| disguise tail of `giveWeaponLoadout` | :1184-1195 | on disguise maps, after the kit is given: force `coop_isDisguised = true` twice around a 0.25s wait, deactivate the weapon, print the "Keep your weapon holstered" hint. |

The `changeGameType` windows themselves (main.scr:1647): refuse to run when
`level.gametype == 0`, are serialized via `level.coop_changeGameTypeThread`, and are globally
disabled during map load via `level.coop_preventGameTypeChanges`. **The same window mechanism
is load-bearing far outside stealth**: the entire weapon-give pipeline (`giveInventory`) and
`coop_reissueMissionItems` (main.scr:947-973 - e1l2 mine detector on every revive/respawn)
run gives under a gametype-0 window so MP weapon handling does not fight them.

## 3. weaponstate.scr - the RAISE/PUTAWAY mirror (HEAD, 93 lines)

Called by the engine statefile (`global/mike_torso`) on every holster/unholster of every
player, on **every map** - it is the project's weapon-state bookkeeper first and a disguise
component second:

- `RAISE_WEAPON` (:21-57): resolves the held item via `returnActiveWeapon` (items that are
  not `classname "Weapon"` - papers - do NOT count), maintains `coop_activeWeapon`,
  `coop_lastWeapon`, `coop_previousWeapon` etc. (respawn carry-over, exact-ammo, weapon
  cycling on all maps depend on these). Only the tail is disguise: if
  `level.coop_enableDisguises` -> `setIsDisguised player (activeWeapon == NULL)` (:55-57).
- `PUTAWAY_MAIN` (:58-64): clears the flags, `setIsDisguised player true`.
- fired states (`state[0]=='A' && state[1]=='T'`, :65-89): if disguised and the gun is not
  the silenced pistol / carcano (:71-77), simulate the shot being heard:
  `broadcastSound player "explosion" 1024` + after 1s `sentientIsHeard player player`
  (:79-85). This is the "loud gun while disguised" model - there is no engine path for it
  because the engine thinks the player is a teammate.

## 4. aihandler.scr - detection, enforcement, and the actor pipeline (HEAD)

- `main` (:18): per-actor entry (every coop-tracked actor on every map runs it). Auto-starts
  `disguiseHandler` once per map (:40-42) - the handler itself waits 1s and exits unless
  `level.coop_enableDisguises` is set, so on non-disguise maps it is a no-op.
- `disguiseHandler` (:987): THE cover-blown poll. 1 Hz loop while
  `coop_enableDisguises && !level.alarm`. For every live german:
  - if he is already `coop_isAttacking`: `sentientIsSeen enemy enemy.enemy 360` each tick -
    aggro spreads from any attacker to anyone who can see him (:1004-1007).
  - else for every player with `has_disguise && coop_hasDisguise && !coop_isDisguised`
    (i.e. disguised player holding a weapon) that he `cansee` within his fov/sight:
    `attackPlayer` + `sentientIsSeen` + `sentientIsHeard` cascades (:1009-1018).
  - Exits permanently when the alarm fires (loop condition) - and is only ever restarted by
    a successful `giveDisguiseToAll`.
- `attackPlayer` (:1027): the wrapper around the engine latch: sighted-VO bark
  (`den_alarm_12a`, bug-1477), `enablePain = 1`, `coop_isAttacking = true`, **`attackplayer`**,
  `favoriteenemy player`. At HEAD there is NO gate inside it - every caller latches the actor
  permanently.
- `sentientIsHeard` (:1049): hearing sim over `level.coop_actorArray["german"]` - engine-like
  rule (half `hearing` range always heard, full range at `sound_awareness`% chance), with an
  arbitrary 512u range when not in the same PVS. Hits -> `attackPlayer`.
- `sentientIsSeen` (:1089): `cansee` check over the german array (PVS-gated), hits ->
  `attackPlayer`. Together these two make one detection cascade into squad-wide aggro.
- `canseeUndisguisedPlayers` (:1113): used by the `anim/disguise_*` inserts - true if the
  actor can see ANY player whose `coop_isDisguised` is false.
- `anyEnemiesInAttackState` / `resetEnemyThinkstates` / `setEnemyAttackStates`
  (:1130/:1146/:1163): the criterion-1 dance around every give window. Reset: attacking/pain
  actors get `enableEnemy = 0`, `no_idle = true`, flag `coop_actorResetThinkstate`. Restore:
  `enableEnemy = 1` + **raw `attackplayer`** (:1170) + `coop_isAttacking = true`. Upstream
  semantics: actors already fighting when the disguise is handed out stay hostile forever -
  deliberate, but it means a single stray aggro before the give bakes in permanent attackers.
- `actorHandler` (:54): the everything-pipeline (accuracy store, pain handler, chatter/voice
  registration, difficulty, array registration, count-scaling hook, death hooks: kills/XP,
  weapon enable, health drops, corpse despawn). Disguise-relevant tail: on death by a player
  while disguises are enabled -> `sentientIsSeen corpse killer 360` (:148-152) - witnesses of
  the kill go loud.
- **Count-scaling** `coop_tryDuplicateActor` (:169) + `coop_spawnReplica` (:243): with 2+
  players each non-special german rolls replica clones. Each replica is born with
  `forceactivate` + **raw `attackplayer`** (:267-268) - i.e. at baseline, on a disguise map
  with 2+ players, every clone is *born permanently disguise-blind and hunting*. (This was
  measured in the session as one of the three wrapper-bypassing sites.)

## 5. The AI-dynamics layer (aisquad / morale / aimaneuver) - stealth-hostile and ON by default

Shipped HEAD `autoexec.cfg` seeds: `coop_aiDynamic 1` (:580), `coop_aiSquad 1` (:583),
`coop_moraleEnable 1` (:591). Launched from `main.scr::main` (:283-293) on every map, plus
`coop_reinf_brain` unconditionally (:129).

- `aisquad.scr` (SB1/SB2, 1.7s loop): clusters germans within 900u; if ANY member of a
  cluster has a live `.enemy`, every un-engaged member is sent loud: `enablePain = 1`,
  `coop_isAttacking = true`, **raw `attackplayer`**, `favoriteenemy`, **`forceactivate`**
  (:108-113), capped 12/tick. Two stealth collisions: (a) it bypasses the `attackPlayer`
  wrapper entirely, and (b) the engine **deliberately retains a disguised player as the
  current enemy at zero threat** (actorenemy.cpp:446) - so `.enemy != NULL` is NOT proof of
  a real fight, and a pre-disguise acquisition can make a "silent" cluster read as engaged
  and go loud during stealth. `forceactivate` additionally yanks scripted-anim actors (card
  players) out of their loops. The optional search pass (`coop_aiSearch`, :121-163) issues
  `runto` + `forceactivate` toward last-known positions.
- `morale.scr` (3s loop): when live germans < half of peak, up to 4 engaged survivors react;
  ~30% go BERSERK: `coop_role = "aggr"`, leash 4096, **raw `attackplayer`** + `forceactivate`
  (:64-69). Same two collisions (wrapper bypass + `.enemy` retained-at-zero-threat gate).
- `aimaneuver.scr` (2s loop): repositions only actors with a live `.enemy` (flank/cover/aggr
  roles) via `enableEnemy 0` -> `runto` -> `forceactivate` re-engage. No `attackplayer` - it
  cannot blind anyone to the disguise, but its `forceactivate` also breaks scripted anims if
  a retained zero-threat enemy makes an idle actor look engaged.

At baseline none of these systems knows disguise maps exist. This is the second half of the
"attackers=0 of 25" session finding: blocking the wrapper was not enough because
`coop_spawnReplica`, aisquad SB2 and morale-berserk all issue raw `attackplayer`.

## 6. anim/disguise_*.scr - the engine behavior scripts, coop-patched (HEAD)

The engine's disguise state machine (`PassesTransitionConditions_Disguise`) still runs in
coop - but it **sight-traces to `G_GetEntity(0)`**, a hardcoded SP player-0 assumption, so
which behavior fires keys off player 0 only. Upstream's coop inserts live at the top of each
behavior script and re-check the *real* multiplayer state:

- `disguise_accept/deny/halt/wait/salute.scr`: identical `[200]` insert - if the actor's
  enemy is a Player, he is not already `coop_isAttacking`, and `canseeUndisguisedPlayers`
  (someone has a gun out) -> `attackPlayer self.enemy` + `sentientIsSeen` + `sentientIsHeard`,
  then bail out of the polite anim (accept :8-18, deny :12-22, halt :16-21, wait :11-16,
  salute :33-44 - salute also `aimat`s).
- `disguise_enemy.scr` (:21-35): the same insert **without** the `canseeUndisguisedPlayers`
  check - a `type_disguise "enemy"` actor always goes loud on a disguised player, matching
  vanilla semantics.
- `disguise_papers.scr` (:13-17): starts `enableClickablePapers` so an empty-handed player
  can present papers with primary fire; map-specific branches for e1l3/e1l4 retained.
- Long `wait`s at the tails "stop the engine calling the script on this actor again during
  this time" (salute :61, `wait 5`).

## 7. maps/m2l2a.scr - the map's own coop branch (HEAD)

- Load: `level.coop_aaMap = 1`, `main.scr::main`, then **`level.coop_enableDisguises = true`
  and `coop_uniformOnSpawn = false` at :21-22** - the map is disguise-enabled from frame one.
  Consequence chain worth internalizing:
  - Every player is engine-disguised **from their first spawn** (managePlayerInventory ->
    giveDisguiseOnSpawn), long before touching the suit. The suit pickup is a door-gate and
    cosmetics, not the mechanical grant.
  - When the suit IS taken (`likeynorway` :634 -> `global/items.scr::add_item "uniform"` ->
    items.scr:289-290 `giveUniformToAll` + `giveDisguiseToAll`), `giveDisguiseToAll`
    **early-outs at :950** because `coop_enableDisguises` is already true. Its retry/verify/
    handler-start logic is dead code on this map; `disguiseHandler` instead comes from the
    `aihandler::main` autostart.
- SP-only branches: `$player.has_disguise = 1` only when `level.gametype == 0` (:77-79);
  SP objective adds (:85-90). Coop objective 1 ("Find a disguise") is added in the coop
  branch at :27.
- `likeynorway` (:634-677): removes `$suit`/`$papers1`, prints the coop papers hint ("press
  PRIMARY FIRE", :645), adds items `papers_level1` + `uniform`, unlocks/opens
  `$likeynorwaydoor`, then walks the two norway guards through their conversation. Each guard
  gets `thread waitForEnemy` (:658-659).
- `waitForEnemy` (:689-704, a `[200]` addition): polls until the guard's thinkstate leaves
  idle/disguise, then `turnto NULL`, `walkto NULL`, **raw `attackplayer`**,
  `type_disguise "none"` - i.e. the moment anything perturbs these two, they latch hostile.
- Other raw **retail** `attackplayer` sites in the map script (all latch permanently):
  `cardplayersdeath` :237 (`$suckyfatty` when a card player dies), `sentry2thing` :274,
  `unholsterweapon` :313, plus :428/:456/:465-466 (norway-guard and guy1-3 outcomes),
  :843/:892/:1008/:1394. (Verified against retail Pak5 `maps/m2l2a.scr`: it has exactly
  these 11 sites; HEAD's 12th is the `[200]` `waitForEnemy` site at :700 described above -
  it is a coop addition, not retail.)
- `wakeupcardplayers` (:278-294): on alarm, buffs `$suckyfatty` hearing/notice.
- Alarm wiring: `alarm_system_setup` + `find_guy` extraction (:95-107), `alarmall` douses the
  switch via `player_closestTo` (:316-328).

## 8. global/cardgame.scr and global/alarm_system.scr coop hooks (HEAD)

- `cardgame.scr::sitthink` (:108-160): `[200]` double-call guard `coop_cardGameSitThink`
  (:111-114) - **one-shot for the actor's lifetime**. Holsters via `replace.scr::holster`
  (:118), parks health at 1 with a chair death anim, then
  `while (self.thinkstate == "idle") waitframe` (:133-134). ANY transient thinkstate flicker
  (curious/alerted for a single frame - e.g. a `forceactivate` from aisquad, or a retained
  zero-threat enemy) permanently ejects him: stand anim, `unholster` (:143), health restored,
  `runtoClosest` (:152). There is **no path back to the chair** at HEAD - this is the
  measured card-player failure mode (standing players + endless cardhand attach-retry spam),
  and our 08-09 re-arm patch (working tree) still does not hold. Treat as unsolved.
  cardgame.scr is shared by **e2l2, m1l2a, m2l2a, m4l2, m4l3** at HEAD.
- `alarm_system.scr::alarm_system_master` (:648+): first time the alarm turns ON ->
  `level.alarm = 1` and `[200]` hook `thread itemhandler::takeAllDisguises` (:665-666).
  Note the asymmetry: the master thread can later toggle `level.alarm = 0` (switches are
  toggles), but the disguise take is permanent - upstream's model is "alarm once = stealth
  over for the map". alarm_system is shared by **e1l4 (PreShip/Ship), m2l2a, m6l1c**.

## 9. Where the shipped model fights the engine (the friction list)

1. **`is_disguised` is read-only** -> every state change needs a serialized 1ms
   `g_gametype 0` window, with weapons force-deactivated and attacking actors force-idled so
   the SP block's criteria pass. Visible holster blip; global cvar flip; races guarded by
   three separate flags (`coop_disguisingInProgress`, `coop_changeGameTypeThread`,
   `coop_preventGameTypeChanges`).
2. **Engine disguise state is frozen between windows** -> engine senses treat players as
   teammates full-time; ALL detection is script (1 Hz poll + cansee/hearing sims), so
   reaction latency is up to ~1s and uses cruder senses than the engine's.
3. **`attackplayer` is a one-way latch** (m_bForceAttackPlayer, cleared only in the Actor
   constructor) -> the only enforcement primitive is permanent. `setEnemyAttackStates`
   re-latches pre-give attackers; there is no per-actor "calm down and honor the disguise
   again" anywhere in the shipped mod.
4. **`actorenemy.cpp:446` retains a disguised player as current enemy at zero threat** ->
   `.enemy != NULL` is used as "engaged" by aisquad/morale/aimaneuver, so stealth states leak
   into the combat-AI layer and trigger raw go-loud paths that bypass the wrapper entirely
   (`coop_spawnReplica` :268, aisquad :110, morale :67 - the three measured bypasses).
5. **`PassesTransitionConditions_Disguise` traces to `G_GetEntity(0)`** -> engine-initiated
   salute/papers behaviors key off player 0 only; players 2-4 are invisible to the
   initiation logic and only covered by the script-side cascades.
6. **`forceactivate` vs scripted-anim actors** - the go-loud recipes wake card players and
   other posed actors; combined with cardgame's one-shot sitthink this is unrecoverable.
7. **Alarm asymmetry** - the alarm can be switched off, the disguise loss cannot. And
   `disguiseHandler` self-terminates on alarm and never restarts.

## 10. What is load-bearing for non-stealth maps (a redesign must NOT break)

- **`changeGameType` windows** - used by the weapon-give pipeline (`giveInventory`) and
  `coop_reissueMissionItems` on every map / every respawn (e1l2 mine detector). Do not
  change window semantics; only the disguise-specific callers are fair game.
- **`weaponstate.scr::main`** - the coop_activeWeapon/lastWeapon/previousWeapon bookkeeping
  feeds respawn carry-over, exact-ammo, loadout logic on every map. The disguise tail is
  cleanly gated on `level.coop_enableDisguises`; the bookkeeping above it is untouchable.
- **`aihandler.scr::main`/`actorHandler`** - per-actor spine for every map (difficulty,
  pain, XP/kills, chatter, count-scaling, corpse handling). `disguiseHandler` autostart is
  harmless elsewhere (self-exits), but `resetEnemyThinkstates`/`setEnemyAttackStates` also
  service the give windows used by e1l3/e1l4.
- **Disguise consumers at HEAD** (grep `coop_enableDisguises` / `has_disguise`):
  - `e1l4` + `maps/e1l4/*` - full-disguise map: enabled at load (e1l4.scr:23), Intro.scr
    applies the window pattern directly (:416-421, has its own comment on the
    spawn-ordering gotcha), PreShip/Ship call `takeAllDisguises`.
  - `e1l3` (`maps/e1l3/FinalEscape.scr`, `courtyard.scr`) - papers-only stealth:
    `level.coop_noWeapon = true` lockout (FinalEscape:732), `has_disguise = 1` sprinkled per
    section, courtyard re-arms (`coop_noWeapon = false`, `has_disguise = 0`). Uses the SAME
    `coop_noWeapon` flag our stealth work reuses - a redesign must keep its semantics
    ("blocks future grants only").
  - `m2l2b` - disguises enabled at load (:14), carried across the transition.
  - `anim/disguise_*.scr` inserts + `canseeUndisguisedPlayers` serve e1l3/e1l4 as much as
    m2l2a.
- **`takeAllDisguises` alarm hook** runs on every alarm_system map (e1l4, m2l2a, m6l1c) -
  it early-outs unless disguises are on, keep it that way.
- **aisquad/morale/aimaneuver/coop_reinf_brain** - shipped ON (autoexec at HEAD) and carry
  the combat feel of every map. A stealth redesign must *gate* their go-loud paths during
  stealth windows, not remove or default-off them.
- **cardgame.scr** - shared by 5 maps; the sitthink guard and holster calls predate the
  stealth work. Any card-player fix must stay behaviour-neutral for e2l2/m1l2a/m4l2/m4l3.

## 11. coop_stealthStart - NOT baseline

At HEAD it does not exist anywhere. In the uncommitted working tree
(`[user 2026-08-08/09]` session work, ~562 inserted lines across 10 files):

- `coop_defaults.cfg` seeds `seta coop_stealthStart 1` ("papers-in-hand stealth route. ON -
  the mission already REQUIRES the disguise ... this only changes how you carry it").
- `maps/m2l2a.scr` `likeynorway` branch, gated on the cvar: sets `level.coop_startUnarmed`,
  `level.coop_forcePapersEquip`, strips current weapons via a NEW
  `itemhandler.scr::coop_stealthStripWeapons`, and only THEN sets
  `level.coop_noWeapon = true` (bug-1607 ordering note); `coop_armOnBlown` re-arms later.
- Companion uncommitted work: attackplayer guards in aihandler, aisquad/morale stealth
  stand-down, alarm hooks, cardgame sitthink re-arm attempt (measured NOT holding as of the
  08-09 playtest - card system still unsolved).

Everything in this doc's sections 1-10 describes HEAD without any of that; evaluate the
session layer against it, not as part of it.

## Appendix: quick call-graph of the shipped disguise path (m2l2a)

```
map load: m2l2a.scr:21  level.coop_enableDisguises = true
player spawn: player.scr -> itemhandler::managePlayerInventory:695
    -> giveDisguiseOnSpawn:875 -> giveDisguise:891
         -> aihandler::resetEnemyThinkstates (criterion 1)
         -> deactivatePlayerWeapon (criterion 2)
         -> main::changeGameType 0 -> has_disguise=true -> changeGameType 2   [engine latch]
         -> aihandler::setEnemyAttackStates (re-latch prior attackers)
    -> giveWeaponLoadout:1114 disguise tail :1184 (setIsDisguised true, holster hint)
any actor init: aihandler::main:18 -> disguiseHandler:987 (1 Hz)
    weapon out + seen  -> attackPlayer:1027 (raw engine latch) + sentientIsSeen/Heard cascades
weapon raise/putaway: statefile -> weaponstate::main -> setIsDisguised (script mirror only)
unsilenced shot: weaponstate:79 -> broadcastSound + sentientIsHeard
suit pickup: likeynorway:634 -> items.scr:289 giveUniformToAll + giveDisguiseToAll(early-out :950)
alarm: alarm_system_master:665 -> takeAllDisguises:1092 (permanent) ; disguiseHandler exits
parallel, unaware of stealth: coop_spawnReplica:268 / aisquad:110 / morale:67  raw attackplayer
```
