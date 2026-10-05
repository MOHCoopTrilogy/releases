# HUD declutter: inventory, classification, design (PHASE 1, proposal only)

User, 2026-10-05: *"we get a lot of text that pops up on the left about items being equipped, items being
locked, current rank, etc. That all seems so obnoxious. Is it really necessary?"*

Status: **inventory + proposal, nothing changed, nothing built, no slot runs.** Line numbers are from the
working tree on 2026-10-05 (mod branch `coop-wip`, engine `hzm-coop-working`). Frequencies are estimates
from reading the triggers, not measured: a typical officer mission with 2-4 players.

---

## 1. Why it feels obnoxious: how the left-hand text actually works

The text on the left is the engine's **game-message box** (`gmbox`, client exe `client/cl_uigmbox.cpp`).
Every script `iprintln` / `iprintlnbold` / `<player> iprint` arrives there as a reliable `print` server
command (`fgame/scriptthread.cpp:3141`, `fgame/player.cpp:13669`) and is routed by
`UI_PrintConsole` (`client/cl_ui.cpp:1356`):

| fact | where | effect |
|---|---|---|
| holds **5** lines, a 6th pushes the oldest out | `cl_uigmbox.cpp:291`, `m_items[5]` | a burst fills the whole box |
| **only the top line decays**; the others wait their turn | `PostDecayEvent` `:137-169` | lines are on screen *sequentially*, not in parallel |
| hold time **5 s per line, 10 s for bold** | `:158-162` | 5 bold lines = **~50 s** of text after a burst |
| **every bold line plays the `objective_text` sound** | `cl_ui.cpp:1432-1434` | an officer fight beeps like an objective update every few seconds |
| `iprint <text> 1` and `iprintlnbold` are bold | `player.cpp:13669` | **~232 of the 289** coop-script sites are bold |

So the problem is less any single message than: almost everything is bold, bold holds 10 s and beeps, and
lines queue instead of fading together. A five-message officer sequence parks text on screen for most of a
minute.

Two other channels get mentioned below:
- **DM box** (chat/obituaries) - engine `G_PrintToAllClients(..., 2)`; the "has joined" line goes here.
- **`ihuddraw_*` toasts** (XP, promotion, challenge-complete, objectives) - separate widgets. They ride one
  unreliable snapshot each (TRAPS T8, `hudresend.scr`), and the fade-exempt slot band is **full**
  (`_research/hud_slot_map.md`, "Genuinely free: Nothing"). That decides the design in section 4.

**Existing gates you can reuse:** `menumirror.scr::coop_quietNotices` (quiets armory/unlock toasts over a
briefing, bug-3234, 11 call sites), `main.scr::printInfo` (a rate-limited per-player print, 8 callers),
`coop_xpKillPopup` (XP popup toggle), `g_coopHardcore` serverinfo (cgame already hides HUD pieces in
Hardcore), `cg_drawsvlag` (slow-server icon).

---

## 2. Inventory (gameplay-time text)

Scope: the 289 `iprint*`/`centerprint`/`locprint` sites in `coop_mod/*.scr` (excluding `mp_*`,
`developer`, `maptest*`, `*selftest*`, `helmtest`, and lines gated by `cMTE`/`dbg`/`coop_dev`), the 405 in
`maps/` and `global/`, the `ihuddraw_string` toasts that show mid-mission, and the engine paths. Grouped
into message families. **Style:** B = bold gmbox (10 s + beep), N = normal gmbox (5 s), DM = chat box,
T = `ihuddraw` toast, I = icon. **Who:** All = broadcast, Self = the one player, Act = the actor's name
shown to all.

### 2a. The examples from the screenshots

| # | Message | file:line | Trigger | Freq / mission | Who | Style | Class |
|---|---|---|---|---|---|---|---|
| 1 | "You have acquired the binoculars! / explosives! / papers / radio..." (20 items) | `global/items.scr:39-314` | `add_item` (map pickup) | 1-6 | **All** (ScriptThread broadcast, even players who picked nothing up) | N | **ICON** |
| 2 | "Helmet locked: Wool Cap - Challenge: ..." | `coop_mod/helmet.scr:495` (`helmet_lockNotice`) | automated re-validation on join / spawn / revive / armory close while the preview is parked on a locked helmet | 1 per map per player (de-duped per index, bug-1578), more if you browse | Self | B | **MOVE** (armory) |
| 3 | "Gloves locked: ..." / "Skin locked: ..." / "Armory: that skin is still locked - wearing ..." | `gloves.scr:163`, `helmet.scr:1379`, `player.scr:1383` | same automation as #2 | 0-2 per map | Self | B / N | **MOVE** |
| 4 | "UnnamedSoldier has joined the Allies" | engine `fgame/player.cpp:11717-11722` | **every** team join, and in coop every player re-joins on **every** map load | players x maps | All | DM | **MERGE** (genuine joins) / **CUT** (map-change re-joins) |
| 5 | "Intel reports a High-Ranking Officer is visiting this area." + "Be cautious of his reinforcements he brought with him." + per-map tutorial lines | `officer.scr:609-616` | officer spawn | 2 + 0-3 lines at once | All | B | **MERGE** (one line) |
| 6 | "You eliminated one of the Officer's bodyguards! He calls for reinforcements!" | `officer.scr:892` | **each** bodyguard death | = bodyguard count (2-4) | All | B | **MERGE** (stacks "x3") |
| 7 | "Allied paratroopers have landed!" | `paradrop.scr:384` | paradrop lands | 0-3 | All | B | **MERGE** |
| 8 | "C-47 inbound! Allied paratroopers dropping in!" (+ "Signal smoke! Allied paradrop inbound!" in the same breath) | `paradrop.scr:33,39`; `maps/M3L3.scr:8214` | paradrop called | 0-3 (x2 lines) | All | B | **MERGE** (one line) |
| 9 | "Recon reports the Officer has deployed an Elite Squad / Wehrmacht Squad / Elite Sniper / Grenadier Squad / Anti-Tank Team / attack dogs..." | `officer.scr:1620-1648` | each reinforcement wave | 2-6 | All | B | **MERGE** (alert tint) |
| 10 | "Recon reports the Officer has called in a Stuka / Artillery barrage onto your position." | `officer.scr:1636,1640` | air/arty wave | 0-2 | All | B | **KEEP** (react now; shorten) |
| 11 | Rank / XP: "Service record: Sgt - 12,340 XP (Prestige 1)" | `xp.scr:426` (`xp_identify`) | every map join | 1 per map | Self | B | **CUT** (scoreboard + service record have it) |
| 12 | "PROMOTED" ceremony (insignia + ping + music duck) | `xp.scr:2268-2322` (`xp_promo_ceremony`, slots 72-73) | rank-up mid-mission | 0-1 | Self | T + sound | **MOVE** (debrief; already shown on the card at `xp.scr:2120`) |
| 13 | "PRESTIGE STAR n!" | `xp.scr:638` | prestige | rare | Self | B | **MOVE** (debrief) |
| 14 | "+N Headshot / Long Shot..." XP micro-popups | `xp.scr:880-924` (`xp_micro_popup`, slots 73-75, `coop_xpKillPopup`) | each kill/award | dozens | Self | T (crosshair, small) | **MOVE** (default off, tally on debrief) - *ask* |
| 15 | "+N XP" rank-bar fill popup | `xp.scr:1631-1796` (`xp_hud_popup`) | XP gains | many | Self | T | **MOVE** (debrief) |
| 16 | "CHALLENGE COMPLETE / <title> / Recorded in your Service Record" + typewriter SFX + duck | `challenges.scr:2458-2571` (`chal_notify`, slots 76-78) | challenge completed; also "MEDAL EARNED" (`medals.scr:181`) and "Variant unlocked" (`challenges.scr:1178`) | 0-5 | Self | T + 2.5 s SFX | **MOVE** (debrief) + 1 silent feed line - *ask* |
| 17 | Pinned-challenge 25/50/75 % progress bar | `challenges.scr:1985-2032` (`chal_progress_popup`, slots 86-87) | milestone on a **pinned** challenge only | 0-6 | Self | T | **KEEP** (opt-in by pinning) |
| 18 | "Armory: <weapon> equipped" / "Armory: your loadout has been applied" / "cleared PRIMARY" / "picks cleared" / "kits are scripted on this mission" | `loadoutpick.scr:138,167,194,265,319,668` | armory pick / close / regive | 1-4 per armory visit | Self | N | **MOVE** (armory status line) |
| 19 | Finish / variant feedback: "<finish> finish applied", "is locked - see CHALLENGES", "Master this weapon first", "Standard model" | `loadoutpick.scr:1130-1264` | armory finish/variant buttons | per click | Self | N | **MOVE** (armory status line) |
| 20 | "Walk when you want to sneak up on enemies." / "Press ( key ) to walk..." | `maps/m1l2b.scr:172,215`; `maps/m4l2.scr:209,212` | vanilla tutorial trigger | 1-2, every playthrough | All | B | **MERGE** (hint, once per profile) |
| 21 | "SLOW SERVER" blinking icon | engine `cgame/cg_drawtools.cpp:350-374`, lit by `svlag` (`server/sv_main.c:1162`) | sustained server overrun (bug-1663 gate) | rare | All | I | **CUT** - already off by default (bug-3209 one-shot, `cg_drawsvlag 0`; the live profile `omconfig.cfg` reads `"0"`). If it was seen, it came from a profile/harness that never ran `coop_hudFix1` |

### 2b. Officer system (`coop_mod/officer.scr`, all broadcast, all bold)

| Message | line(s) | Freq | Class |
|---|---|---|---|
| "The Officer's bodyguards have been eliminated!" | 899 | 1 | MERGE |
| "Recon reports the Officer has slipped away / is falling back / retreating / slipping away to a health post" (5 variants) | 826, 1072-1081 | 0-3 | MERGE (one de-dup key) |
| "The Officer is drinking from his canteen to recover!" | 848 | 0-2 | MERGE |
| "The Officer has been fully healed! Thresholds reset!" | 1152 | 0-2 | MERGE |
| "The Officer barks into his radio - but his reinforcements are not ready yet!" | 1521 | 0-3 | CUT (flavour, no action) |
| "Recon reports the Officer has summoned a BATTALION!" | 2584 | 0-1 | MERGE (alert tint) |
| "The Battalion has been wiped out!" / "<squad> eliminated." | 2668, 2748 | 1 per wave | MERGE (stacks) |
| "Recon reports the Officer is calling another wave to replace his losses!" | 2753 | 0-2 | MERGE |
| "The officer has been eliminated!" + "Plant explosives on the radio to stop reinforcements permanently!" | 3806-3807 | 1 | KEEP 3807 (it is the next objective) / MERGE 3806 |
| custom officer message hook | 3984 | map-defined | MERGE |
| "The officer dropped a Signal Smoke Grenade / Binoculars / both!" | 4230-4234 | 1 | MERGE |
| "<name> picked up the Signal Smoke! / Binoculars!" / "recovered the Binoculars! (n strikes left)" / "recovered the Signal Smoke!" | 4323, 4357, 4369, 4882 | 1-3 | MERGE |
| "Signal Smoke ready! Equip grenades and throw..." / "Equip binoculars from pistol slot..." / binoc tutorial array | 4324, 4362, 4366 | 1-2 | MERGE (hint, once per profile, **to the carrier only**) |
| "Negative - no clear sky above target coordinates. Strike request denied." | 4434 | per failed call | KEEP, but **to the caller only** (now broadcast) |
| "Fire mission requested... (n remaining)" / "Final fire mission requested..." | 4452, 4455 | 0-3 | MERGE |
| "The Binoculars / Signal Smoke were dropped - a teammate can recover them." | 4802, 4851 | per carrier death | MERGE |
| "The radio is exposed! Approach it and press Use to plant explosives." | 4910 | 1 | KEEP |
| "<name> planted explosives on the radio!" / "Radio destroyed! Reinforcements cannot be called!" | 4936, 4999 | 1 each | MERGE |
| "A surviving officer spotted you and is radioing for backup!" | 5046 | 0-1 | KEEP |
| `objective_drop.scr`: "Intel recovered: a Signal Smoke / Binoculars is stashed at the objective!", "<name> picked up ...", tutorial lines, "Binoculars recovered - n strikes left" | 78, 122, 165-166, 203-209 | 0-2 | MERGE (tutorials -> hint) |

### 2c. Paradrop, squad, revive, medkit

| Message | file:line | Freq | Who | Style | Class |
|---|---|---|---|---|---|
| "Flak got one of the C-47s - fewer troopers inbound!" | `paradrop.scr:188` | 0-2 | All | B | MERGE |
| "An Allied Medic revived a teammate!" / "Allied Medic patched you up! HP: n" | `paradrop.scr:591,646` | 0-4 | All / **All** (646 says "you" to everyone) | B | MERGE (646 -> self) |
| "Allied paratroopers eliminated." | `paradrop.scr:755` | 0-3 | All | B | MERGE |
| "You are DOWN! arm wound. Bleeding out in 30s" | `dbno.scr:238` | per down | Self | B | KEEP |
| "A squadmate is DOWN - look for the medkit marker..." / "A squadmate bled out." | `allysquad.scr:216,279` | per down | All | B | KEEP |
| "<name> got a squadmate back on their feet - that was his last one." | `allysquad.scr:306` | per AI revive | All | B | MERGE |
| "A medkit brought you back to your feet!" | `dbno.scr:420` | per self-revive | Self | B | MERGE |
| Medkit: "Medkit refilled!", "Medkit stowed (n/cap)", "Already at full health", "No medkits remaining", "Heal interrupted!", "You have bandaged yourself up.", healer/target lines, "No medkits - cannot self-revive" | `medkit.scr:51,78,150,179,185,258,313,502,506,521,528` | many | Self | B | MERGE |
| "Pack detected nearby!" | `medkit.scr:75` | per pack | Self | B | CUT |
| "Hardcore: no self-revive while a teammate is up..." | `medkit.scr:588` | per attempt | Self | B | KEEP |
| LMS: "You have [ n ] lives left - LastManStanding is active!", "You have 0 lives left", "You are allowed back in the game!" | `player.scr:1733`, `main.scr:1768,1790` | per death | Self | N/B | KEEP (rule the player must know) |
| LMS: "COOP: LMS active/inactive - ..." / "LMS failed all players are dead" | `player.scr:239,253`, `main.scr:1779-1832` | per change | All | B | MERGE (failure line KEEP) |
| "Spawn protection: n seconds" | `player.scr:1603` | per spawn | Self | N | CUT (the existing spawn-protect visual says it) |
| "If you are stuck, press use..." / "Moved you to a different spawnlocation" | `player.scr:1470,1480` | rare | Self | B | MERGE |
| Holdout: "You fell - you rejoin when the wave is cleared", "HOLD USE - RADIO HQ TO RESPAWN YOUR SQUAD" / "You are back in the fight!" | `holdout.scr:641,751` / `697` | per event | Self | B / N | KEEP / MERGE |

### 2d. Deployables, cosmetics, views, vehicles (all Self)

| Message | file:line | Class |
|---|---|---|
| Ammo box: "already deployed", "Not while in disguise", "deployed - each squadmate can resupply twice", resupply result | `ammobox.scr:22,32,72,220,237` | MERGE |
| Sandbags: "No sandbag placements remaining", "Not while in disguise", "Cannot place here - no ground / too high", "Sandbag refunded" | `cover.scr:6,16,44,49,349` | MERGE |
| Take-cover: "No cover here - face a low wall..." | `takecover.scr:40` | MERGE |
| Take-cover: "Cover released", "In cover - hold FIRE to blind-fire..." | `takecover.scr:29,52,55` | CUT (the camera/pose already shows it) |
| "View: First Person / Free Cam / Third Person" | `thirdperson.scr:20-31` | CUT (visible) |
| Emotes "You salute", "At ease", "Stretching" | `player.scr:752-754` | CUT |
| Helmet/skin hotkey: "Helmet: X", "Skin: X", "No other ... unlocked yet", "Can't change ... while down/dead" | `helmet.scr:781,799,816,1334,1352,1434`; `lobby.scr:532,551` | MERGE |
| "Recruited - he fights for you now" | `surrender.scr:173` | MERGE |
| "Back on the .30cal!", "Riding along - you unload when the jeep stops", "Back aboard the AB41!", "Back on the convoy .30cal!" | `maps/e3l1.scr:360,375`; `maps/e3l3.scr:838`; `maps/e3l4.scr:365` | MERGE |
| Vehicle/gun cooldowns via `printInfo` ("You need to wait before you can leave the tank again!" etc.), "You are not allowed to move right now" | `global/vehicles_thinkers.scr:71,116,120,231`; `replace.scr:2524` | MERGE |
| "Allied fire brought down X!" / "<name> shot down X!" | `aircraft.scr:1196-1204` | MERGE |
| "<name> dropped a heavy weapon..." / "recovered a heavy weapon!" | `keyitems.scr:47,160` | MERGE |
| Blueprint collectibles: "Press USE to take the blueprint" / "Blueprint set complete" / coin-flip results / "HEADS! Unlocked: X" | `collectible.scr:284,372,398,438,445` | MERGE (prompt) / MOVE (unlock -> debrief "UNLOCKED THIS MISSION") |

### 2e. Stealth / disguise and vanilla map lines

| Message | file:line | Class |
|---|---|---|
| "You are now disguised!", "The alarm was raised. You can no longer disguise!", "Cover blown - weapons free!", "Keep your weapon holstered when in disguise.", "press (PRIMARY FIRE) to show papers" | `itemhandler.scr:1154,1168,1868,1978,3193` | KEEP (state the player must act on) |
| "Alarm sounding!" / "Alarm silenced." | `e1l4alarm.scr:64,50` | KEEP / MERGE |
| Mission-fail and casualty lines: "Mission Failed", "You failed to protect Klaus / the Minesweeper / Baker Bunker", "Your cover was blown", "<NPC> has been killed in action", "A POW was killed", e3l4 airstrike countdown | `maps/e1l2/Intro.scr`, `e1l3/*`, `e1l4/Intro.scr`, `e2l1.scr:225,228`, `e3l2/*`, `e3l3/scene1.scr:684`, `e3l4/*`, `m1l1.scr:526-535`, `m1l2a.scr:680-681,3757`, `m2l2a.scr:536,825` | KEEP |
| e3l3 "Stealth phase: hold your fire...", "Weapons free!" | `maps/e3l3/scene1.scr:174,986,1008` | KEEP |
| Contextual prompts: "Hold USE to eject from the glider / cut your chute", "Press USE to get in jeep", "Approach the jeep", "Press use to set the explosive / use the cannon", "You have no explosives." | `maps/e2l1/gliderride.scr:963,1528`; `e2l2/guardPost.scr:87`; `e3l1/BritHQ.scr:209`; `e1l2/Artillery.scr:798,801`; `m1l2a.scr:2943,3126` | KEEP |
| Vanilla tutorial hints: "Press the USE key...", "Use your compass...", "Press OBJECTIVE key...", "Follow the arrow on your compass", "You can only climb one side of a ladder", "Press (Secondary Attack) to use the scope", "Press the ( key ) to holster... If your weapon is not holstered your cover will be blown", "Sometimes an objective may be located directly above or below..." | `m1l1.scr:702-799,2540,2667`; `m1l2a.scr:345,728,4022`; `m1l2b.scr:168-215`; `m2l1.scr:321-326,598-607`; `m2l2a.scr:294,313-316` | MERGE (hint, once per profile) |
| Coop tutorial: "TUTORIAL: Paratroopers can be deployed..." (**4 bold lines = 40 s**) | `m1l2a.scr:3418-3421` | MERGE (one hint line) |
| Map pickups: "You have acquired the KAR98 Sniper Rifle / a mine detector", "You picked up a Bazooka / an STG-44 / a Shotgun", "Document taken." | `e1l2/Artillery.scr:356`; `e1l2/Intro.scr:1341`; `e3l4/Bunker4.scr:48`; `e3l4/Tunnel.scr:206,228`; `m2l1.scr:132-171` | ICON |
| "Coop Mission Progress has been saved!" | `e1l3/Sneakers.scr:132` | MERGE |
| "Naxos sabotaged." / "Equipment Destroyed" / "The town has been put on full alert..." | `m2l2a.scr:707`; `M1L3c.scr:295`; `m1l2a.scr:3331` | KEEP |

### 2f. Live debug / dev prints that reach players (CUT - these are defects)

| Message | file:line |
|---|---|
| "Fadein", "Briefing", "COOP SKIPPED: SetPlayerHealthScale" (every e3l1 load) | `maps/e3l1.scr:190,219,275` |
| "jeepUseLoop - use" / "- exit" | `maps/e3l1/JeepRidePart3.scr:368,402` |
| "ExitStageRight", "RollOutTank2 -> playertank?" | `maps/e3l1/AfterSnipers.scr:392,427` |
| "DoCappyAirFieldSpeech - moved players / skipped dialog", "golyndon - skipped ..." | `maps/e2l2/guardPost.scr:382,398`; `maps/e2l2/briefing.scr:94,147` |
| "$playerChangingClothes waittill trigger", "... triggered", "clausEscapeRoute waitForPlayer finished", "$playerFullyDisguised triggered", "playerFullyDisguised done" | `maps/e1l3/FinalEscape.scr:361,365,419,435,753` |
| "briefing water mortar over" | `maps/e1l3/Briefing.scr:576` |
| "$pow1_door should open now", "$MCJailDoor is closing...", "$MCJailDoor unlocked" | `maps/e3l2/MiniCourtyard_Section.scr:131,189,204` |
| "^~^~^ AB41 stall-recover: re-issuing drive" (machine-log line printed to the HUD) | `maps/e3l3/e3l3_AB41.scr:148` |
| "KILLING WALL" | `maps/e3l1/BritHQ.scr:192` |
| "e1l1/scene2.scr::doMiddleDeath is triggering.... fixme", "e2l1/gliderride.scr::UnrestrictView - needs fixing", "error doMineField is not working", "AICLEANUP >>>> local. trigger is NULL", "this was disabled by chrissstrahl" | `maps/e1l1/scene2.scr:1542`; `maps/e2l1/gliderride.scr:1315`; `maps/e1l1.scr:412`; `maps/e1l1/aicleanup.scr:37`; `maps/m1l2a.scr:1219` |
| `$player[1].viewangles` | `maps/e3l4/Outro.scr:718` |
| "COOP e1l2 placements: THREAD START" / "DONE spawned n objects" (every e1l2 load) | `coop_mod/coop_placements.scr:654,1019` |
| "Coop: WARNING: spawnclip - NULL entity given", "Coop Error: teleportToOnTouch ...", generic error relay | `coop_mod/replace.scr:2135,2151,2411` (-> `println`) |
| "COOPDEBUG: incomplete command...", "manageNamechange - could not retrive...", "playerNameCommand: ... not on valid List", "Coming soon" x3 | `coop_mod/player.scr:499,653,679-681,828` |
| "pressed 1..12" | `coop_mod/mom_actions.scr:34-131` |
| "Are you hacking dude ?", "GO SLEEP! YOU ARE SLIPPING." | `coop_mod/mom_login.scr:50`; `coop_mod/admin.scr:22` |
| "AI alive: ... moving: ..." | `coop_mod/aibehav.scr:172` (check its gate) |
| "coop_scan: Found n health packs" | `coop_mod/medkit.scr:928` |
| "You are being auto spawned for testing!!!" | `coop_mod/main.scr:407` |

Already gated, leave alone: `level.showTriggerMessages` (e1l1 scene2/3), `coop_missionItemDebug` (main.scr:1156),
`level.coop_debugSpawn` (spawnlocations.scr:34), the `username == Chrissstrahl` line (spawnlocations.scr:3165),
`maps/dm/*` "TOUR:" (bot tour harness), `e2l2/cinematic.scr` "Hacks enabled".

### 2g. Not gameplay-time, unchanged

Lobby / ready gate (`lobby.scr`, `readygate.scr`, `lobbyui.scr`), builder and editor tools the player
switches on (`buildmode*`, `blueprint`, `wallgun`, `fogmode`, holdout F5-F8 editor, helmet TUNE/FIT),
admin self-feedback (`admin.scr` "Admin: ..."; the broadcast "Admin kicked / banned / slayed" lines are
MERGE), debrief card (`xp.scr::xp_summary_card`). MP modes (`mp_*.scr`) are out of scope (MP isolation);
the feed can get an MP twin later if wanted.

---

## 3. Classification summary

Counted by message family = the 98 rows of section 2, by each row's first class (2f rows are all CUT):

| Class | Families | What happens |
|---|---:|---|
| **KEEP** | 17 | stays a bold gmbox line (objectives, fail states, downs, stealth state, "on your position" strikes, contextual USE prompts, LMS lives, pinned progress) |
| **MERGE** | 43 | goes to the new event feed (section 4); includes the vanilla tutorial hints as a once-per-profile *hint* category |
| **ICON** | 2 | pickups: the item icon flashes by the inventory with a 1-word label, no sentence |
| **MOVE** | 9 | rank, XP, promotion, prestige, challenge-complete, medals, unlocks -> debrief card / service record; locks, equipped, applied, finishes -> an armory status line |
| **CUT** | 27 | live debug prints (2f, 17 rows across 25 files), "Spawn protection", "Service record" join line, "Pack detected", emotes, view mode, cover confirmations, radio-not-ready flavour, slow-server icon (already off) |

**Can the vanilla "You have acquired..." text be suppressed?** Yes, cheaply and safely. It is not engine
text: it is `global/items.scr` (vanilla global script; our pk3 already ships an override), one `iprintln`
per item, and the label already takes a `local.nomessage` parameter (`items.scr:15`). Gate it on
`level.gametype != 0` (coop) and route the item's HUD graphic (already chosen in the same switch,
`local.item_graphic`) to the feed as an ICON entry. Vanilla single player (`gametype 0`) keeps its line
unchanged; MP modes never run `items.scr`. The engine itself prints nothing for weapon/ammo pickups
(`fgame/item.cpp` `ItemPickup` has no print). The map-local copies (e1l2, e3l4, m2l1) are edited per map.
Side benefit: today the line is a broadcast, so a player across the map is told "You have acquired
explosives!" when somebody else picked them up.

**"has joined the Allies"** is game.dll (`fgame/player.cpp:11717`). Proposal: in coop only (gate on the
same coop detection as `CoopMpPlayerHit`, i.e. `coop_mpRun`-aware, not the map-name test - see bug-2713 /
bug-2968), skip the broadcast when the client was already connected before this map (a map-change
re-join), and send genuine joins to the feed. MP keeps the vanilla line.

---

## 4. Design

### 4.1 Event feed: cgame-drawn, fed by tagged prints (no ihuddraw slots)

**Why not ihuddraw or a new menu:** the fade-exempt slot band is full, and every `ihuddraw` write rides
one unreliable snapshot (T8; it would need `hudresend` claim/resend for every line). Prints are already
**reliable** server commands that reach cgame (`cg_servercmds.c:455` "print"/"hudprint"). So:

- **Wire format:** script sends an ordinary per-player `iprint` (not bold) whose text starts with a tag:
  `~f<cat>[:<key>[:<icon>]]~<text>`. No quotes, no `;` (T8 rules hold because it is plain print text,
  not stufftext - nothing for `cg_servercmds_filter.cpp` to learn).
- **cgame intercept** (`CG_ServerCommand` "print" branch): if the payload after the colour byte starts
  with `~f`, call `CG_FeedPush(cat, key, icon, text)` and echo the **untagged** text to the console *without*
  a colour byte (so `UI_PrintConsole` keeps it in console/qconsole.log but never puts it in the gmbox, and
  no `objective_text` beep). Untagged prints behave exactly as today.
- **Script API**, new `coop_mod/feed.scr` (coop-only; MP scripts may not call it, add it to the
  `check_mp_isolation` clause list like `hudresend.scr`):
  - `feed_player local.player local.cat local.key local.text` and `feed_all local.cat local.key local.text`
    (loops `$player`).
  - Capability check: only tag for clients that report the new cgame (a `CVAR_USERINFO` cvar, read via
    `info_valueforkey` like kit/cosmetics, TRAPS T8). Older clients get a plain **non-bold** line.
  - `local.key` is the de-dup key so variants collapse (the five "retreating to a health post" lines are
    one key; "bodyguard down" stacks to "x3").
- **Categories:** `0 alert` (amber tick, 6 s, for MERGE lines that still warrant attention: enemy wave
  deployed, battalion), `1 team` (4 s: paradrop, kills of squads, item pass-arounds), `2 self` (3 s:
  medkit, ammo box, sandbags, vehicle cooldowns), `3 pickup` (2.5 s, icon + one word), `4 hint`
  (once per profile: the client keeps seen keys in an archived cvar `coop_hintSeen`; the server-side
  hint text is skipped when the key is already seen).
- **Rendering**, procedural like `CG_DrawStaminaArc` (`cg_drawtools.cpp:1835`): bottom-left, above the
  health/stamina area; verdana-12 (the XP micro-popup size); **max 3 lines**, newest at the bottom; each
  line has its **own** timer (parallel fade, not the gmbox queue): 150 ms fade-in, hold, 600 ms fade-out;
  a repeat of the same key within 8 s bumps a counter ("Bodyguard down x3") and restarts the hold instead
  of adding a line; a 4th line pushes the oldest out with a fast fade. Colours from the debrief brass/steel
  palette (`xpbar_*`), a 2 px category tick at the left edge rather than coloured text. Not subject to
  `s_hudFadeAlpha` (it is not a slot), so it shows to a stationary player.
- **Pickup icons:** cat 3 with `<icon>` = the shader `items.scr` already picked (`textures/hud/item_*`):
  the icon pops at 1.3x and settles beside the feed with one word ("Binoculars"). Players other than the
  picker get the cat-1 line "<name> picked up explosives" only for mission items (papers, explosives).
- **Toggles** (Coop Settings, archived, client-side): `coop_feed 0/1/2` - 0 = KEEP lines only, 1 = feed
  (default), 2 = feed + mirror to the old gmbox (for anyone who liked it). `coop_hints 0/1` (default 1).
- **Hardcore:** cgame already reads `g_coopHardcore`; in Hardcore the feed draws only cat 0 and hints are
  off. KEEP lines still go to the gmbox (they are rule-critical). No icons.
- **KEEP lines** stay vanilla bold gmbox lines - they are rare once everything else leaves the box, which
  is the point: a bold line and its beep mean something again.

### 4.2 End-of-mission summary: extend the existing debrief card, plus a menu page

- In-game: `xp.scr::xp_summary_card` already plays at mission end (insignia, animated bar, category
  totals, "PROMOTED TO", "UNLOCKED THIS MISSION:" list, slots 63-69 / 127-134 / 160-167). Add two short
  sections in the same style: **Challenges completed this mission** (titles, one typewriter cue for the
  whole list instead of one per toast) and **Medals / prestige**. The mid-mission promotion ceremony and
  the challenge-complete toast stop playing mid-combat; their moment moves here.
- Menu: a **"Last mission"** page built from the What's New / field-report card layout
  (`ui/coop_whatsnew.urc`), filled from archived `coop_lastMission_*` cvars the server writes at debrief.
  It also lists locked items you tried to wear ("Wool Cap - Challenge: ...") so the lock reason has a home.
- Armory: one **status line** in the loadout menu bound to a cvar (`coop_armoryStatus`), replacing the
  "Armory: ... equipped / applied / locked / finish applied" prints. The armory is already SHOW-ALL-WITH-
  LOCK, so the lock reason belongs beside the item there, not on the battlefield.

### 4.3 What it needs

| piece | where | notes |
|---|---|---|
| `CG_FeedPush` + draw + intercept | `cgame/cg_servercmds.c`, `cgame/cg_drawtools.cpp` | cgame.dll only; client exe untouched |
| `coop_mod/feed.scr` | new | coop-only, isolation clause, capability check |
| call-site edits | ~110 sites in ~35 files | mechanical: `iprintlnbold "X"` -> `thread coop_mod/feed.scr::feed_all 1 "key" "X"`; brace/parse scanners + `check_map_compiles` + `check_mp_isolation` 22/22 |
| debug-print removals | 2f list | to `println` (log keeps them) |
| `global/items.scr` gate | 20 lines, one switch | coop-only |
| join-message gate | `fgame/player.cpp:11717` | game.dll, coop-only |
| debrief additions + Last-mission page + armory status line | `xp.scr`, `challenges.scr`, `ui/*.urc` | reuse whatsnew layout |

Order: (1) CUT the debug prints and the redundant lines (script-only, no cgame needed, immediate relief);
(2) cgame feed + `feed.scr` + routing; (3) MOVE to debrief/armory; (4) join gate in game.dll.

---

## 5. Questions for the user

1. Mid-mission **promotion** and **challenge complete**: move them entirely to the debrief, or keep one
   small silent feed line ("Promoted: Sergeant", "Challenge complete: The Tell-Tale Ping") in the moment?
2. The **XP kill popups** near the crosshair (+10 Headshot): keep as they are, or default them off with
   the tally on the debrief? (They are already small and have a toggle.)
3. Where should the feed sit: **bottom-left above health/stamina** (proposed), or stay top-left where the
   old text was, just smaller and capped at 3 lines?
4. **Tutorial hints** ("Walk when you want to sneak..."): show once per profile (proposed), or off entirely
   by default?
5. **Join messages:** hide the map-change re-joins only (proposed), or hide joins in coop completely?
6. In **Hardcore**, should the feed show the amber "enemy wave deployed" alerts, or nothing at all?

---

## 6. Answers (user, 2026-10-05) and PHASE 2 - what was built

Answers: (1) promotion + challenge-complete = debrief card PLUS one quiet feed line; (2) crosshair XP popups unchanged;
(3) feed bottom-left above health/stamina; (4) hints once per profile; (5) hide only map-change re-joins, new players to
the feed; (6) Hardcore shows only the amber threat alerts. Added later: ALL DBNO text - "You are DOWN!" is cut (the
bleed-out ring/vignette/heartbeat carry it), teammates get one feed line; only mission failure / everyone down stays bold.

Built (all edits are anchored ops: `tools/ops_engine.py`, `tools/ops_mod.py`, applied/staged by `tools/hudops.py`):

| piece | where |
|---|---|
| event feed (3 lines, per-line fade, `xN` stacking, no sound, hints, Hardcore filter, armory/last-mission cvars) | `openmohaa-hzm/code/cgame/cg_coopfeed.c` (new) + 2 hook hunks (`cg_servercmds.c`, `cg_drawtools.cpp`) |
| capability + old-client fallback | cgame registers `cg_hzmFeed 1` (USERINFO, ROM); `feed.scr::feed_capable` reads it; others get plain non-bold text |
| script API | `hzm-mohaa-coop-mod/coop_mod/feed.scr` (new): `feed_player/feed_all/feed_others/feed_hint*/feed_icon/feed_itemPickup/feed_mapList/feed_chalDone/feed_lastMission` |
| routing | ~230 print sites in 55 scripts (officer, paradrop, objective_drop, DBNO, medkit, armory, cosmetics, LMS, admin, maps) |
| developer prints | to `println` (console/log only) |
| "You have acquired" | `global/items.scr`: coop only, icon + one word for the picker (`parm.other`), everyone for a scripted give |
| armory | confirmations -> `coop_armoryStatus` (not drawn); denials -> one self line. `ui/coop_loadout.urc` is checksum-LOCKED (check_mp_isolation clause 6), so no new label there; the lock reasons already show in its REQ rows |
| promotion / challenge / medal / prestige | one quiet feed line; the debrief list is now "EARNED THIS MISSION" (+ challenges, medals, prestige); the mid-mission rank bar is off (`coop_xpRankBar 1` restores it) |
| LAST MISSION page | `ui/coop_lastmission.urc` (new, What's New plate) + main-menu button; lines `coop_lm0..9` written by the feed at the debrief |
| re-join hiding | game.dll `g_client.cpp` (carried-over flag) + `player.cpp` (`HZM_CoopJoinSession` = level var coop_mainScriptLoaded) |

Client cvars (archived, cgame-registered, no menu yet): `coop_feed 0/1/2`, `coop_hints 0/1`, `coop_feedX/Y`, `coop_hintSeen*`.
