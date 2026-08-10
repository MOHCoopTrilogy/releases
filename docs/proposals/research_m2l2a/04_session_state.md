# 04 — Session State: Exact Local Delta and Verification Status (m2l2a stealth route)

## CORRECTIONS (verification pass, 2026-08-09)

Independently re-verified against the working tree, `.wolf/buglog.json`, git, and the engine
sources. The load-bearing findings all held: the whole-window `coop_stealthBlocksAggro` core
(aihandler:1184-1202) and its three source gates (aihandler:274 replica / aisquad:115 / morale:71),
the opt-in funnel guard (aihandler:1076, requires `coop_stealthFunnelGuard == "1"`, unseeded),
dead `coop_stealthArmOnHurt` (itemhandler:1330 is the only occurrence in the tree), the ungated
raw `attackplayer` at aihandler:1262, the ALARMTRIP per-target guard (alarm_system:393-403), the
weaponstate.scr:56 inventory-item rule (engine rule confirmed at player.cpp:5480-5484), the
one-way latch (set actor.cpp:9294, cleared only at actor.cpp:3092), the missing bug-1605/1607/1609
ids, the cardgame re-arm loop as described, and the complete §6 print inventory. Four things were
wrong or stale and are fixed in the body below:

1. **§4.6 "Nothing after bug-1619 is logged" was false.** The buglog now runs to **bug-1621**:
   bug-1620 (m2l2b bomb-site bricked before manifest, 11:05 playtest) and bug-1621 (MG42_crouch_*
   anims missing on grenadier TIK) were appended after the snapshot. What remains true — and the
   section now says only this — is that the 10:38 funnel-guard verification, the full stand-down
   escalation, and the card re-arm failure are still unlogged.
2. **§1 row 6 misattributed the papers-ITEM re-give to `itemGetAll`.** `itemGetAll` lives in
   `coop_mod/main.scr:906` and is **unchanged** this session. The re-give was added to
   `itemhandler.scr::managePlayerInventory` (:745-747). Worse: it sits BELOW the
   `if (level.coop_noWeapon){ end }` early-exit at :711, and the stealth route sets that flag
   (m2l2a.scr:680) — so on the one map it was written for, the re-give is unreachable for a
   mid-stealth respawner. §4.2 updated accordingly (the respawn hole is deeper than stated).
3. **Stale line numbers.** `alarm_system:666` → **:701** in the working tree (the session's 35
   added lines shifted it); itemhandler's coop_noWeapon checks are at
   **:711/:1549/:1584/:1710**, not :711/:1379/:1414/:1540 (the doc had copied the pre-diff
   numbers out of the code comment at itemhandler:763 — that comment is itself stale and worth
   fixing when the file is next touched).
4. **§4.7 undercounted the line-ending warnings.** `git diff` warns `LF will be replaced by CRLF`
   for **29 files** in the working tree, not 8. The eight named are the stealth-session subset;
   the rest ride in from other uncommitted work (ambience, ammobox, challenges, xp, m1l*, ui/*,
   ubersound, …). A release normalization pass has the full 29 to consider.

Everything else in the document was left untouched.

---

Snapshot date: 2026-08-09. Baseline: `hzm-mohaa-coop-mod` nested repo, HEAD `f694b31` (public
v1.2.3 line). **Every stealth change below is uncommitted working-tree state**, marked in-source
with `[user 2026-08-08]` / `[user 2026-08-09]`. Sources: `git diff` per file, `.wolf/buglog.json`
bug-1596..bug-1619, `docs/SESSION_HANDOFF.md` (written ~02:00, i.e. BEFORE the 10:38/10:58
late-morning work — the diffs and the debrief context are the authority for that last stretch).

Verification vocabulary used below:
- **VERIFIED** — a cited log measurement exists.
- **DEPLOYED-UNVERIFIED** — in the working tree and deployed, no measurement cited anywhere.
- **FAILED** — measured and did not hold.
- **DEAD** — code exists but is never invoked.

---

## 1. Delta at a glance

| # | File | Change | Status | Master-design verdict |
|---|------|--------|--------|----------------------|
| 1 | `maps/m2l2a.scr` | `coop_stealthStart` route in `likeynorway` (startUnarmed + forcePapersEquip + strip + noWeapon, in that order) | VERIFIED (disguise holds; route playable) | **KEEP** |
| 2 | `maps/m2l2a.scr` | `waitForEnemy` rewrite (bug-1609): exit on `canseeUndisguisedPlayers`, waitthread-not-thread | DEPLOYED-UNVERIFIED | **KEEP** (verify) |
| 3 | `maps/m2l2a.scr` | likeynorway `type_disguise "salute"` gated to `level.gametype == 0` | DEPLOYED-UNVERIFIED (card system still failing after) | **KEEP** (part of card rework) |
| 4 | `maps/m2l2a.scr` | `cardplayersdeath` → `cc_card_sentry` challenge bump (bug-1599 salvage) | DEPLOYED-UNVERIFIED | **KEEP** (not stealth) |
| 5 | `maps/m2l2a.scr` | `coop_baked_0808` blueprint placements (3 props) | BROKEN downstream (BP owner-guard, handoff §3) | **KEEP** map-side; fix is in collectible.scr |
| 6 | `coop_mod/itemhandler.scr` | `managePlayerInventory` (:745-747): re-give the papers ITEM on spawn (flag alone was set before). NOT `itemGetAll` — that is main.scr:906, unchanged. Sits BELOW the :711 `coop_noWeapon` early-exit, so it never runs mid-stealth (§4.2) | DEPLOYED-UNVERIFIED | **REWORK**: move above the :711 exit (or re-give in itemGetAll) so it covers the stealth window it was written for |
| 7 | `coop_mod/itemhandler.scr` | stealth-start comment + removal of the old `takeall` (bug-1604) | VERIFIED (uniform survives) | **KEEP** |
| 8 | `coop_mod/itemhandler.scr` | `coop_armOnBlown` hooked into `takeAllDisguises` (single cover-blown choke point) | PARTIALLY VERIFIED (see §3) | **KEEP** |
| 9 | `coop_mod/itemhandler.scr` | `coop_paperPassAll` (guard accepts papers → whole squad cleared, guard retired via `type_disguise "none"`) | DEPLOYED-UNVERIFIED | **KEEP** (verify 2+ players) |
| 10 | `coop_mod/itemhandler.scr` | `coop_papersAnytime` (primaryfire-while-unarmed shows papers outside interrogation) | DEPLOYED-UNVERIFIED | **KEEP** (user design rule) |
| 11 | `coop_mod/itemhandler.scr` | `coop_stealthStripWeapons` (class-based 4-pass drain + `setIsDisguised force` + per-player state print) | VERIFIED (bug-1606/1607 chain; disguise then holds) | **KEEP**; consider drain-until-empty loop instead of fixed 4 passes |
| 12 | `coop_mod/itemhandler.scr` | `coop_stealthHoldDisguise` 2 Hz watchdog + STEALTHWATCH census | VERIFIED as instrument; the 08-09 inventory-item fix un-broke it | **REWORK** (see §4 gaps) |
| 13 | `coop_mod/itemhandler.scr` | `coop_stealthArmOnHurt` | **DEAD — never threaded from anywhere** | **REWORK**: wire it or delete it |
| 14 | `coop_mod/itemhandler.scr` | `enableClickablePapers` NULL-or-NIL guard (bug-1603) | VERIFIED (papers usable) | **KEEP** |
| 15 | `coop_mod/weaponstate.scr:56` | inventory-item-in-hand keeps disguise (engine rule player.cpp:5480) (bug-1617) | VERIFIED (00:58 measurement; `eng_is=1 mod_is=1` holds) | **KEEP** |
| 16 | `coop_mod/aihandler.scr` | `attackPlayer` AGGRO probe + funnel guard, now **opt-in** via `coop_stealthFunnelGuard` (default OFF) | VERIFIED 10:38 that it is NOT needed (source gates alone → attackers 0/25) | **KEEP dormant** or delete in master; do not default ON (sits in papers-challenge path) |
| 17 | `coop_mod/aihandler.scr` | `coop_stealthBlocksAggro` — whole-pre-alarm-window block (engine `m_bForceAttackPlayer` one-way latch is the rationale) | VERIFIED (attackers 0 of 25 sustained, 10:38 run) | **KEEP** — this is the core fix |
| 18 | `coop_mod/aihandler.scr` | `coop_spawnReplica`: clone gated on `coop_stealthBlocksAggro`, `forceactivate` unconditional | VERIFIED (part of the 0/25 run; clone anims no longer blocked) | **KEEP** |
| 19 | `coop_mod/aisquad.scr` | go-loud **full stand-down** during stealth window (not even `forceactivate`) | VERIFIED (log full of `AGGRO BLOCKED aisquad-goloud`; all 25 idle) | **KEEP** |
| 20 | `coop_mod/morale.scr` | berserk full stand-down during stealth window | VERIFIED (same run) | **KEEP** |
| 21 | `coop_mod/aihandler.scr:1262` | `setEnemyAttackStates` restore site: **raw `attackplayer` still UNGATED** (probe only) | Gap — did not fire in verified runs, but nothing prevents it | **REWORK**: gate it like the other three sites |
| 22 | `global/alarm_system.scr` | `ai_alarm_alerted` ALARMTRIP probe + disguised-enemy guard (bug-1616) | VERIFIED (`ALARMTRIP BLOCKED` in log) | **KEEP**; align semantics with #17 (it still per-target tests instead of whole-window) |
| 23 | `global/cardgame.scr` | `sitthink` re-arming sit loop (added ~10:58) | **FAILED** — next playtest still had two card players stand, faces shifting | **REWORK/REVERT** — card system unsolved |
| 24 | `anim/disguise_salute.scr` | SALUTE stall probe (voicetype/weapongroup print, gated) | Instrument only | **KEEP** until card system solved, then remove |
| 25 | `anim/disguise_accept.scr` | thread `coop_paperPassAll` on accept | DEPLOYED-UNVERIFIED | **KEEP** (pairs with #9) |
| 26 | `autoexec.cfg` | TEMP `set coop_aggroDebug 1` + `set coop_bpDebug 1` | Working as intended | **REVERT before release** (also re-join the comment the insertion split — it landed mid-sentence of the `developer 0` block) |
| 27 | `coop_defaults.cfg` | `seta coop_stealthStart 1` seed (route ON by default) | Design decision | **KEEP** (mission requires the disguise anyway; cvar justifies itself in-line) |

Related-but-not-stealth changes riding in the same working tree (do not fold into the stealth
verdicts): `maps/m2l2b.scr` (~293 lines: Enigma decrypt/visibility bug-1610/1611, manifest gate
bug-1608, sub-escape finale, `waitTillSpawn` shim bug-1613), `global/ambience.scr`+`maps/m1l2b.scr`
(bug-1612 rename), `coop_mod/collectible.scr` (blueprint think staged checkpoints — **open defect**:
`local.owner` param never binds, handoff §3), `coop_mod/player.scr` (limp warning 08-07, skin
fail-open bug-1595), `coop_mod/replace.scr::convOk`, `coop_mod/challenges.scr` (bug-1596..1601
batch), plus m3l1b/build-mode cvar seeds in `coop_defaults.cfg`.

---

## 2. The stealth-start route in detail (m2l2a.scr `likeynorway` + itemhandler)

Gated on `getcvar "coop_stealthStart" == "1"` (seeded ON in coop_defaults.cfg). Order is
load-bearing and was bought with three bugs:

1. `level.coop_startUnarmed = 1` — marks the map as running the stealth route.
2. `level.coop_forcePapersEquip = game.true` — `main.scr::forcePapersInHand` (already committed,
   07-19 e1l3 work — NOT part of this delta) draws papers in-hand on every spawn.
3. `waitthread coop_mod/itemhandler.scr::coop_stealthStripWeapons` — strips what is ALREADY
   carried, by weapon class (armory can hand out any of 69 guns, so e1l3's model-name list was
   unusable). Then `setIsDisguised <p> true true` (forceState) because removal-by-class is not a
   holster transition and nothing else would set the flag (bug-1606). Then starts the
   hold-disguise watchdog.
4. `level.coop_noWeapon = game.true` — set AFTER the strip (bug-1607): it is the lockout for
   FUTURE grants (checked at itemhandler :711/:1549/:1584/:1710 in the working tree — the code
   comment at itemhandler:763 still cites the pre-diff numbers :1379/:1414/:1540; all
   pre-existing e1l3 plumbing).

Unwind: `itemhandler.scr::takeAllDisguises` → `thread coop_armOnBlown` — clears
`coop_startUnarmed` + `coop_noWeapon` + `coop_forcePapersEquip` FIRST (or `giveWeaponLoadout`
early-exits and the kit never arrives), re-gives every active player their armory loadout, then
`activatePlayerWeapon` to displace the papers still rendered in-hand. `takeAllDisguises` is the
single choke point — alarm_system:701, items.scr:477, e1l4 Ship.scr:416 + PreShip.scr:88 all
route through it.

**Verified live**: the route is playable end-to-start — papers usable (bug-1603 fix measured),
uniform survives (takeall removed, bug-1604), disguise holds (`eng_is=1 eng_has=1 mod_is=1`,
handoff §1 row 3), attackers 0 of 25 sustained (10:38 run).
**Not yet measured**: the cover-blown re-arm arriving mid-fight (§3), papers re-give on respawn
(#6), squad-wide paper pass (#9/#25), papers-anytime presentation (#10).

---

## 3. Verification ledger (what was actually measured, and when)

| Measurement | Where cited | What it proves |
|---|---|---|
| `AGGRO actor=ai_alarm target=<player> tgtDisguised=1 alarm=0` (00:37) | bug-1615 | 3 of 4 `attackPlayer` callers never checked disguise |
| every `AGGRO` followed by `AGGRO BLOCKED` | bug-1615, handoff §1 | funnel guard worked when ON |
| `ALARMTRIP actor=ai_alarm enemy=player enemyDisguised=1 alarm=0` → `ALARMTRIP BLOCKED` | bug-1616 | second, independent alarm aggro path found and closed |
| disguise silently cleared ~18 s in (00:58), held after weaponstate fix | bug-1617 | papers-in-hand were clearing the disguise; engine inventory-item rule is correct |
| `STEALTHWATCH … attackers=0 -> 7 -> 9 -> 15 alarm=0` (01:16) | bug-1618, handoff §1 | flags correct yet aggro climbing → raw `attackplayer` sites (replica/aisquad/morale) |
| **attackers held 0 of 25 whole run, funnel guard OFF, log full of `AGGRO BLOCKED aisquad-goloud`** (10:38) | aihandler.scr in-source VERIFIED note + debrief | the three SOURCE gates alone are sufficient; funnel guard demoted to opt-in |
| all 25 actors reach `thinkstate idle`; cardhand attach-failure spam ($suckyfatty entnum 170, 4 s retry loop) stops | debrief context | full stand-down (aisquad/morale) also cured the scripted-anim yanking |
| next playtest after the ~10:58 cardgame re-arm: **two card players still stand and never sit**, facial anims shifting | debrief context | the re-arm loop as written DOES NOT HOLD — card system unsolved |
| cover-blown re-arm | — | **never explicitly measured**. bug-1604's "spotted with no weapons" symptom has not recurred, but no log line shows loadouts arriving after a genuine blow. Treat as open verification |

---

## 4. Gaps, dead code, discrepancies (things the master design must resolve)

1. **`coop_stealthArmOnHurt` is dead code.** Grep of the whole mod tree finds only its definition
   (itemhandler.scr:1330) and its internal `thread coop_armOnBlown`. No spawn path threads it. So
   the "hit while unarmed → arm everyone" failsafe described in its header DOES NOT RUN. Wire it
   (player spawn path under `level.coop_startUnarmed`) or delete it.
2. **Respawn/late-join hole in the watchdog + strip.** `coop_stealthStripWeapons` runs ONCE at
   uniform pickup, over players active at that moment. A player who respawns (or joins) mid-stealth
   does NOT even get the #6 papers-ITEM re-give: that block (managePlayerInventory:745) sits below
   the `if (level.coop_noWeapon){ end }` exit at :711, which the stealth route arms (m2l2a:680) —
   so during the stealth window managePlayerInventory ends before reaching it. The respawner's
   papers come only from the committed e1l3 plumbing (main.scr::itemGetAll re-giving
   `level.coop_playerItemN` + the coop_forcePapersEquip hook's `use`), IF the papers give routed
   through replace.scr::item on this map — unverified. And nobody restarts
   `coop_stealthHoldDisguise` for them and no `setIsDisguised force` runs on their fresh body.
   Their disguise state depends entirely on weaponstate transitions again — the exact machinery
   bug-1606 proved unreliable.
3. **`setEnemyAttackStates` restore site (aihandler.scr:1262) still issues raw `attackplayer`
   ungated** — it only got an `AGGRO_SRC` probe. It restores actors flagged
   `coop_actorResetThinkstate`; if that ever fires during a stealth window it will latch
   `m_bForceAttackPlayer` (one-way, cleared only in the Actor constructor) exactly like the three
   sites that were gated.
4. **Guard semantics are inconsistent.** `coop_stealthBlocksAggro` blocks for the WHOLE pre-alarm
   window (correct — the latch is one-way and a legitimately-undisguised player en route to the
   papers must not permanently blind guards). The alarm guard (`ai_alarm_alerted`) still uses the
   older per-target test (`enemyDisguised == 1`, or nobody-undisguised when enemy is nameless). An
   undisguised-but-innocent player walking to the pickup can therefore still ring the alarm. Align.
5. **Buglog ids cited in code that do not exist in the buglog.** Comments reference bug-1605
   (strip-by-class), bug-1607 (waitthread race / noWeapon ordering), bug-1609 (waitForEnemy) —
   none of these ids are in `.wolf/buglog.json` (verified by id scan; the file runs …1603, 1604,
   1606, 1608…). Either they were drafted and never appended, or the numbering in comments drifted.
   The knowledge is in the comments; the ledger has holes. Log them properly.
6. **The late-morning stealth events are not in the buglog.** The ledger does continue past
   bug-1619 — bug-1620 (m2l2b bomb-site bricked when touched before the manifest) and bug-1621
   (MG42_crouch_* anims missing on the grenadier TIK) were appended 2026-08-09 — but the 10:38
   funnel-guard verification/demotion, the aisquad/morale full-stand-down escalation, and the
   cardgame re-arm attempt and its failure are still only in code comments and the debrief.
7. **Line endings.** git warns `LF will be replaced by CRLF` for **29 working-tree files**. The
   stealth-session subset is itemhandler.scr, aisquad.scr, morale.scr, m2l2a.scr, m2l2b.scr,
   coop_defaults.cfg, player.scr, replace.scr; the other 21 (ambience, ammobox, challenges, xp,
   objectives, cover, blueprint, several maps/m1l*, gags, global/*, ubersound, ui/*) ride in from
   other uncommitted work. Not a known parse killer, but the project convention (and TRAPS T2
   history) says normalize before commit — and the release pass has the full 29 to consider, not
   just this session's 8.
8. **Card system is unsolved** (see §5). Do not present the re-arm loop as a fix.
9. **Blueprint bake on m2l2a is inert** — `coop_bp_think` exits at the owner-guard (param 2, the
   player entity, never binds; handoff §3 has the fix suggestion: pass entnum, resolve from
   `$player` per tick). The three `coop_baked_0808` placements therefore do nothing visible yet.

---

## 5. The card-table system — status: FAILED / unsolved

What is known, in order:
- Retail `sitthink` was one-shot: sit only while `thinkstate == "idle"`; any transient flicker
  (which the coop AI layer produces routinely) ejects the actor permanently; the only "return"
  animation (`chair_alert_stand_end`) animates the CHAIR, not the man.
- `forceactivate` from aisquad/morale was yanking card players out of the scripted sit — fixed by
  the full stand-down (#19/#20), which also stopped the cardhand attach-failure spam.
- The likeynorway saluters trap: in coop the two Norway-talkers hold the player as (zero-threat)
  enemy, so `type_disguise "salute"` makes `PassesTransitionConditions_Disguise` win over the
  scripted walkto — they stand at the table saluting forever ("Saluting guy...." logged twice).
  Gated to SP (#3).
- The `sitthink` re-arm loop (settle 1 s → re-holster → re-seat unless alarm/attack/pain) was added
  ~10:58 — and the very next playtest still had two card players stand and never sit, facial anims
  visibly shifting. So either the loop's re-seat branch never runs (they may be stuck in
  `curious`, which the loop deliberately treats as a real breakout), or the stand is driven by a
  path the loop cannot see (the salute-stall hypothesis in `disguise_salute.scr`: retail TIKs only
  define `den_(unarmed|rifle)_fullbody_salute_` for voicetypes a01-a03/c01-c03/d01-d03; any other
  voicetype → anim missing → `flaggedanimdone` never arrives → pose held forever). The SALUTE
  probe exists to answer this but its output from the failing pair has not been captured/read.

Master design should treat "card players stay seated through the stealth window" as an open
problem with three candidate mechanisms (thinkstate flicker, salute stall, disguise-transition
capture) and a probe already in place to discriminate them.

---

## 6. Release gating — every diagnostic that must be gated or removed

**Delete outright (TEMP, marked as such):**
- `autoexec.cfg`: `set coop_aggroDebug 1`, `set coop_bpDebug 1` (+ re-join the split comment).

**Ungated `println`s added this session (compile them out or gate before release):**
- `maps/m2l2a.scr:760` — `STEALTH waitForEnemy fired`
- `coop_mod/itemhandler.scr:1162` — `PAPERS guard satisfied - whole squad waved through`
- `coop_mod/itemhandler.scr:1252` — per-player `STEALTH <name> isDisguised=… engine_is=…` state line
- `coop_mod/itemhandler.scr:1256` — `STEALTH weapons stripped (items kept)`
- `coop_mod/itemhandler.scr:1288` — `STEALTH re-asserted a cleared disguise`
- `coop_mod/itemhandler.scr:1335` — `STEALTH player hurt while unarmed` (dead code today)
- `coop_mod/itemhandler.scr:1376` — `STEALTH cover blown, loadouts issued`
- `coop_mod/collectible.scr:143-156` — `BP think started`, `BP g0`..`BP g3`, `BP END at *-guard`
  (unconditional; handoff §5 already flags them)

**Already gated on `coop_aggroDebug` (fine once the autoexec TEMP lines go):** the AGGRO /
AGGRO_SRC / AGGRO BLOCKED family (aihandler:275,1023,1054,1089,1166,1260; aisquad:116; morale:72),
ALARMTRIP + ALARMTRIP BLOCKED (alarm_system:391,400), SALUTE probe (disguise_salute.scr), and the
STEALTHWATCH census (itemhandler, inside the watchdog). The BP per-tick print is gated on
`coop_bpDebug`.

**Player-facing, keep:** `iprint "Cover blown - weapons free!"` (itemhandler:1373).

**Pre-existing loud prints NOT from this session** (noted so they are not blamed on the stealth
work): `main.scr::coop_reissueMissionItems` REISSUE lines are unconditional by design since the
07-19 bug-898 hunt — separate cleanup decision.

**Cvars introduced by this work:** `coop_stealthStart` (seeded 1 in coop_defaults.cfg),
`coop_stealthNoAggro` (unseeded; empty ≠ "0" so default-ON by construction),
`coop_stealthFunnelGuard` (unseeded; opt-in, must equal "1"), `coop_aggroDebug` / `coop_bpDebug`
(TEMP). Master design should decide which of the first three get a `seta` seed + docs row.
