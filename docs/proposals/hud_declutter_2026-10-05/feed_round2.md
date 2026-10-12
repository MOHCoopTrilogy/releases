# Event feed, round 2: more of the informative text in the small feed

User, 2026-10-06: the small feed text format is liked; route MORE of the informative text into it.
Round 1 (PLAN.md section 6) moved about 230 script print sites. This round is what was still printed the old
way on 2026-10-12: everything in `coop_mod/*.scr` and the mod's `global/*.scr` that is not a comment, a `cMTE`
/ `coop_dev` / tester-gated debug line, a builder or editor tool, or a multiplayer-mode (`mp_*`) script, plus
the lines `game.dll` prints itself (they never went through a script, so round 1 could not see them).

Rule used: **information goes to the feed; anything the player has to act on now stays where it is.** Feed
lines are sentence case, no exclamation marks, no full stop, one clause where possible.

## 1. What changed

### 1a. Lines the engine prints (`game.dll`, co-op missions only)

Co-op only = the level variable `coop_mainScriptLoaded` (never set in a multiplayer mode). A client whose cgame
does not advertise the feed (an old cgame, a bot) gets the retail line exactly as before.

| Old text (where it showed) | New feed line | Notes |
|---|---|---|
| `Picked Up <weapon>` (message box, 5 s, queued) | same words, personal line (steel tick) | one line, key `wpn` |
| `Got <n> <type> Rounds` / `Got <n> Grenades` / `Got <n> Rifle Grenades` (message box): ammo boxes, a picked-up gun's ammo, use-to-loot ammo | same words, personal line | one line **per ammo type** (`am_<type>`): the newest amount replaces the older one for that type, and a gun's two ammo lines never replace each other |
| `<name> is preparing for deployment` (chat box) | same words, team line (brass tick) | keyed by the player (`join<n>`) |
| `<name> has entered the battle` (chat box, **every player on every map load**) | same words, team line, **new players only** | a player carried over from the previous map is not announced - the rule the "has joined the Allies" line already follows (user answer 5, 2026-10-05) |
| `<name> has joined the Allies` (feed since round 1) | unchanged words | key was one shared `join`; two players joining together replaced each other. Now `join<n>`, so the three join lines of ONE player replace each other and two players keep a line each |
| `<name> has left the battle` (chat box) | same words, team line | key `join<n>` |
| `<name> called a vote.` (message box, **bold, 10 s, beep**) | `<name> called a vote`, team line | the vote prompt itself is untouched |
| `Vote Passed: <what>` / `Vote Failed: <what>` (bold, beep) | same words, team line | key `vote` |

**Hardcore:** the feed draws only amber alerts there (user answer 6). Pickup and vote lines therefore keep
their retail print under Hardcore (the rule `coop_mod/loot.scr` already follows for "Found ..."); the join /
leave lines follow the existing "has joined" line and are console-only in Hardcore.

### 1b. Script lines

| Old text | File | New feed line (category, key) |
|---|---|---|
| `Pinned: <challenge id>` / `Unpinned: <challenge id>` (message box) | `coop_mod/challenges.scr` | `Pinned: <challenge TITLE>` / `Unpinned: <title>` (self, `pin`) - the id was internal |
| `Already complete - can't pin: <id>` (bold, beep) | `challenges.scr` (2 sites) | `Already complete - cannot pin: <title>` (self, `pin`) |
| `5 challenges pinned already - unpin one first.` (bold) | `challenges.scr` | `Five challenges are pinned - unpin one first` (self, `pin`) |
| `Challenges are disabled (coop_challenges 0).` (bold) | `challenges.scr` (2 sites) | `Challenges are disabled on this server` (self, `chal_off`) |
| `Pin: unknown challenge <n>` | `challenges.scr` | console only (a developer line) |
| `Ready` / `Not ready` (bold, 10 s, beep, one more line per press) | `coop_mod/readygate.scr` | `Ready` / `Not ready` (self, `ready`): one line that flips. The gate's rule is untouched |
| `Admin: no player in slot <n>`, `Admin: <name> has no GUID yet - IP ban only` (bold) | `coop_mod/admin.scr` | same words (self, `admin`) |
| `Admin: godmode ON` / `OFF` (bold, to the target) | `admin.scr` | `Admin: godmode on` / `off` (self, `admin`) |
| `adminCommand unsupported command: <raw>` / `... action: <raw>` (bold) | `admin.scr` | `Admin: unsupported command` (self, `admin`); the raw text goes to the console |
| `<Thing> is not allowed, cvar coop_dev needs to be 1` (bold) | `coop_mod/main.scr` | `<Thing> needs coop_dev 1 on this server` (self, `dev`) |
| `No valid player found. Try with different parameter.` (bold) | `coop_mod/player.scr` | `No valid player found - try a different parameter` (self, `cmd`) |
| `WAVE CLEARED` (bold) | `coop_mod/holdout.scr` | `Wave cleared` (team, `ho`) |
| `OFFICER ELIMINATED` (bold) | `holdout.scr` | `The Officer has been eliminated` (team, `off_dead` - the officer system's own line) |
| `HQ ACKNOWLEDGES - REINFORCEMENTS INBOUND` (bold) | `holdout.scr` | `HQ acknowledges - reinforcements inbound` (team, `ho`) |
| `BUILD MODE OFF - GOING LIVE` (bold) | `holdout.scr` | `Build mode off - going live` (team, `ho`) |
| `landmine defused!` / `landmine vanished!` (message box) | `global/landmine_sp.scr` | `Landmine defused` / `The landmine is gone` (self, `mine`); single player keeps the retail line |
| `Approach alarms and press the USE key to toggle them off or on.` (**bold, every 30 s** while an alarm sounds) | `global/alarmer.scr` | **user 2026-10-12: a one-time hint.** `Alarms: walk up to one and press USE to switch it off or on` (hint, `alarm_use`): shown once per player profile by the feed's own hint memory. Single player and the MP modes keep the retail line |
| `Blueprint n / m Found` (centre of the screen, 3 s) | `coop_mod/collectible.scr` | **user 2026-10-12: "the pickup confirm can be in the feed".** `Blueprint n / m found` (self, `bp_found`) |
| `Press USE to take the blueprint` (feed line when within reach) | `collectible.scr` | **user 2026-10-12: "the hint that a blueprint is nearby needs to go completely".** Removed. There was no sound or marker tied to it; the model's own pulse is part of the placed art and stays. USE within reach still takes it |
| `Blueprint set complete - see the debrief` on EVERY pickup | `collectible.scr` | a bug (integer division, bug-3527): now every fifth, as written |
| `BACKUP SPAWNING: there are no spawners for zone: ...` (**bold, to every player** - a tester's line) | `global/alarm_system.scr` | console only |
| `Loadout called more then once`, `level.script is undefined, doing giveall` (to every player) | `global/loadout.scr` | console only |

## 2. Left as it is, and why

| Text | Where | Why |
|---|---|---|
| `Plant explosives on the radio...`, `The radio is exposed! Approach it and press Use...`, `A surviving officer spotted you...`, `Negative - no clear sky...` | `officer.scr` | the next thing to do / a refusal the caller must react to (KEEP in round 1) |
| `You are now disguised!`, `The alarm was raised...`, `Cover blown - weapons free!`, `Keep your weapon holstered...`, `...press (PRIMARY FIRE) to show them.` | `itemhandler.scr` | stealth state the player acts on (KEEP in round 1) |
| `Alarm sounding!` | `e1l4alarm.scr` | act now |
| `You've stepped on a landmine!` | `global/landmine_sp.scr` | act now (stand still) |
| `You have no explosives.`, the tank-lost failure lines, the tank `Health:` subtitle | `global/turret.scr`, `global/vehicles_thinkers.scr` | contextual prompt / mission failure / retail readout |
| `LMS failed all players are dead or inactive.` | `main.scr` | mission failure |
| `Coop Map Check is active, loading next map in: n`, `BAD SERVER SETTINGS, reloading map`, `LOADING MAP NOW` | `server.scr` | countdown / the map is about to reload |
| `Your Name is to long (n) for commands to work...` | `player.scr` | the player has to change his name |
| Holdout banners `HOLDOUT BEGINS`, `CHECKPOINT n OF m - DIG IN`, `WAVE n / m`, `NEXT WAVE IN n SECONDS`, `WAVE IN n`, `AN OFFICER LEADS THE FINAL WAVE`, `THE POINT IS LOST - MISSION FAILED`, `HOLDOUT COMPLETE`, `HOLDOUT ABORTED`, `You fell - you rejoin when the wave is cleared`, `HOLD USE - RADIO HQ...` | `holdout.scr` | countdowns, calls to act, start and end of the mode |
| Holdout editor lines (`CHECKPOINT n SET...`, `ENEMY APPROACH n SET...`, `SAVED n checkpoint(s)...`) | `holdout.scr` | an editor the player switched on (out of scope since round 1) |
| Lobby lines: `Ready!` / `Not ready`, `Launch aborted - not everyone is ready`, `Launching campaign...`, `Change your uniform in the ARMORY`, `Skin: <name>`, `No other skins unlocked yet.` | `lobby.scr` | the lobby runs with the HUD off (`drawhud 0`), and the feed is not drawn while the HUD is off; a line sent there would be invisible |
| Helmet TUNE / FIT readouts | `helmet.scr` | fitting tool |
| `MISSIONITEM ...`, `You are being auto spawned for testing!!!`, the `OFFICER:` / `REINF:` lines, `= NEW Spawnlocations =`, `AI alive: ...`, developer-login lines | `main.scr`, `officer.scr`, `spawnlocations.scr`, `aibehav.scr`, `mom_*.scr` | already gated behind a debug switch (`coop_missionItemDebug`, `cMTE`, `coop_aiBehav 2`, developer login) |
| Five blank prints after a disguise change | `itemhandler.scr:2549` | not a message: it scrolls the retail box clear |
| `You have bandaged yourself up.` (centre, after a self-revive), `Healing Player`, `You are being revived`, `Applying medkit...`, `Patching up squadmate...`, `Giving up...` | `medkit.scr`, `dbno.scr` | part of the revive / heal progress display the action is watched on |
| Prompts: `[USE] Resupply ammo`, `Ammo box depleted (no resupplies left for you)`, `Hold [USE] to remove cover`, `Hold [USE] to convert enemy`, `Hold [USE] to heal player`, `You are out of medkits.`, `Press [USE] to Contain The Situation`, `Avoid the Officer...`, `Body Being Investigated. Leave the Area Immediately`, `Situation Escalated - Weapons Free`, `Press [key] to track your objectives` | `ammobox.scr`, `cover.scr`, `surrender.scr`, `dbno.scr`, `itemhandler.scr`, `bust.scr`, `objectives.scr` | "press F" prompts and act-now warnings |
| Ready gate panel (`Press F ( [Use] ) to Ready Up`, the tally line, the roster), the `LAUNCHING IN n` countdown | `readygate.scr`, `lobby.scr` | the gate's own display / a countdown |
| `NEW OBJECTIVE` toast and the objectives list | `objectives.scr` | retail objective text |
| XP popups, the debrief card, the pinned-challenge progress bar, the wave banner | `xp.scr`, `challenges.scr`, `holdout.scr` | decided in round 1 (user answers 1 and 2) |
| Engine: `You killed yourself`, `You killed <name>`, team-kill removal, `Can not change teams again...`, `That team has enough players`, `Reinforcements in n`, `Next respawn in n seconds`, `This door is jammed`, weapon-ban lines | `game.dll` | PvP lines, countdowns, and refusals at the thing the player is touching |
| Respawn-point / checkpoint moves | - | the mod prints nothing for these today (the two "stuck" lines went to the feed in round 1), so there was nothing to route. `Coop Mission Progress has been saved` (e1l3) went to the feed in round 1 |

## 3. The queue: no line is lost when several arrive at once

Checked before adding volume. **It was losing lines:** the feed kept three live lines by giving the oldest a
200 ms forced fade the moment a fourth arrived, with no minimum time on screen. Four lines in one frame meant
the first was on screen for a fifth of a second; of eight, the first five were.

Now (`cg_coopfeed.c`): a line that finds all three rows taken by lines younger than **1.5 s** waits (up to 24
waiting lines; alerts wait ahead of everything else; the same key while waiting is one counted line) and goes
up as soon as the oldest row has had its 1.5 s. A burst pages through three rows every 1.5 s.

Measured in the private harness (m1l1, 1280x720, `coop_feedDebug 1`, scratchpad `small/feed_test.py r2`):

| Sent in ONE frame | Result |
|---|---|
| 8 different lines (5 personal/team, 1 alert in sixth place) | 8 shown: 3 at once; the alert + 2 after 1500 ms; the last 2 after 3000 ms. No row given up before 1500 ms |
| 3 lines, then the same key 3 times | 3 shown at once; one line `Bodyguard down ... x3` after 1500 ms |
| Hardcore on (the harness profile's default, run r1) | 24 lines accepted, only the 3 alerts drawn; the ammo pickup kept its retail print |

Not changed: three rows, the hold times per category, the look.

## 4. Stills

All from the engine's own `screenshot` in the harness (cgame d6f70347, game 9f3ad806, the released exe and
renderer). The loot prompt and the enemies-remaining line were raised from the client console for the layout
(`coop_lootT`, `coop_ecLine`); the feed lines and the item readout are real.

| File (in `media/`) | Shows |
|---|---|
| `round2_feed_1920x1080.jpg` | three feed lines (alert, team, personal) above the item readout; loot prompt under the crosshair; enemies-remaining top right |
| `round2_feed_1920x1080_worst.jpg` | the worst case: three lines that each wrap to two rows |
| `round2_feed_640x480.jpg`, `round2_feed_640x480_worst.jpg` | the same two at 640x480. Worst case: the feed's right edge is 13 px left of the loot prompt's key cap |
| `round2_queue_and_routes_1280x720_crops.jpg` | bottom-left crops: page 2 of the 8-line burst; the `x3` line; `Pinned: <title>` + a real `Got 1 Heavy Rounds`; the three tick colours; wrapped lines; the ready gate's `Ready` |

Seen on the way and **fixed the same day** (engine 8e8f9edd):
- bug-3521, `round2_itemrow_vs_health_1280x720.jpg` (before): the retail health / stamina cluster, when visible,
  covered part of the medkit / sandbag / ammo-box row. After, with the cluster forced visible (`coop_hudFade 0`):
  `round2_hudfix_640x480_hud_visible.jpg`, `..._1280x720_...`, `..._1920x1080_...`, crops in
  `round2_hudfix_itemrow_crops.jpg`. The row and the feed are lifted at heights under about 1070 px; 1080p and
  above are unchanged. 3440x1440 could not be captured (the test display is 1920x1080).
- bug-3522: the enemies-remaining line ran into the top-right item icons. It now ends left of them, or goes
  under them when the compass bar leaves no room (640x480): `round2_hudfix_enemyline_crops.jpg`.

## 5. Not verified in play

`Picked Up <weapon>` (the test's spawned shotgun was not taken), the vote lines and `has left the battle` were
not exercised. Exercised later the same day: the landmine line, the alarm hint (shown once, the repeat dropped
by the client), `Blueprint 1 / 1 found`, and with two clients `is preparing for deployment` / `has entered the
battle` / `has joined the Allies` (keyed per player) and the gate's `Ready` on both screens.
