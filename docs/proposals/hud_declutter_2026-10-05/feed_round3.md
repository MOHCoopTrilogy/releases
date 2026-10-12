# Event feed, round 3: the map scripts

User, 2026-10-12: "there are still many messages that appear on the left side Like the ones you created for
completing certain omaha objectives IE: move up the beach under the smoke... we need to move more of those into
our new message bar at the bottom left. But honestly, for those let the scenes tell the story."

Scope: every non-commented `iprintln` / `iprintlnbold` / `iprint` / `centerprint` / `locprint` in `maps/*.scr` and
`maps/*/*.scr` (283 lines on 2026-10-12). Rule per line, first that fits:
1. **removed** - co-op narration of what the scene, the voice-over or the objective already says;
2. **feed** - information the player cannot get otherwise, short and uniform, per player where it concerns one;
3. **kept** - must-act-now lines, mission failure and killed-in-action, countdowns, "press USE" prompts, the retail
   exit refusal ("You have not completed all your objectives") and every "cover blown" line (see Questions);
4. **console** - debug leftovers that could reach a screen.

Not touched: `maps/training.scr` (39 lines; the prints are the lesson), `maps/obj/*` and `maps/dm/*` (26 lines;
multiplayer maps), `maps/m3l1a*` / `maps/m3l1b.scr` story lines (done as the pattern in mod 91f9668a).

Line numbers are as they were before the edit.

## Allied Assault, missions 4-6

| Line | Original | Decision | Why / new feed line |
|---|---|---|---|
| M5L2A.scr:541 | `local.player iprint local.message 1` | removed | a duplicate: line 537 already sends the same message through the helper at 652 |
| M5L2A.scr:652 | `self iprint local.message 1` (why the player was just moved) | feed | personal, `m5l2a_moved`: "The tank has to reach this point to complete the objective" / "Return to the battle, your brethren need you" |
| m5l2b.scr:445 | "The tank needs to reach here to win!" | feed | personal, `m5l2b_tankend`: "The tank has to reach this point to finish the mission" |
| m5l2b.scr:598 | `self iprint local.message 1` | feed | personal, `m5l2b_moved`: "Return to the battle, your brethren need you" |
| m6l1c.scr:1207 / 1209 | "Papers taken. The uniform is here too." / "Uniform taken. The papers are here too." | feed | team, `m6l1c_cache`; nothing else says half the cache is still there |
| m6l1c.scr:1238 | "The alarm is up. Shut it off before you can pass as one of them." | feed | team, `m6l1c_alarm`; the only explanation of a refused disguise |
| m6l1c.scr:1276 | "You are in uniform. Show your papers, and stay quiet." | feed | team, `m6l1c_uniform` |
| m6l1c.scr:1516 | "Nobody is left to come and investigate." | feed | personal, `m6l1c_radio` |
| m6l2a.scr:1318 / 1320 / 1337 / 1416 / 1418 / 1730 | the same six lines as m6l1c | feed | keys `m6l2a_cache`, `m6l2a_alarm`, `m6l2a_uniform`, `m6l2a_radio` |
| m6l2a.scr:2266 | "Train schedule acquired." | removed | objective 1 is ticked two lines later and objective 2 added |
| m6l2a.scr:2325 | "Not yet - you still need ..." | feed | team, `m6l2a_bombgate`; the fallback instruction at a refused bomb site |
| m6l2a.scr:2350 | "The radio command post can now be rigged." | removed | objective 4 is added and made current just above |
| m6l2a.scr:2451 | "Level 2 papers acquired." | feed | team, `m6l2a_papers2`; the pickup icon is suppressed there, so this is the only signal |
| m6l2a.scr:2688 / 2693 | "This should slow down existing reinforcements." / "This should buy you some time should things Go Loud." | removed | objective 2 is ticked and the radio reply is subtitled at that moment |
| m6l2a.scr:2761 | "Out of time - the charges are going." | removed | the stopwatch has run out and the blast scene starts on the next line |
| m6l2a.scr:2779 | "Clear. Blow it." | removed | one second before the ending scene |
| m6l2a.scr:3401 | "Too exposed - rig the mast, the generator and the power box instead." | feed | team, `m6l2a_sabrefuse` |
| m6l2a.scr:3668 | the 174-character "Intel reports an Officer with Level 2 Access ..." | feed | personal, `m6l2a_l2hint`: "Intel: an officer in town holds level 2 papers - he collects the helmets of the men he has killed" |

Kept (retail or must-act-now): "You have not completed (all of) your objectives" on m4l0, m4l1, m4l3, m6l1a, M6L1b,
m6l1c, m6l2a, m6l3b, m6l3d; the killed-in-action and mission-failed lines of m4l1, m5l1b, m5l3, m6l3a; the m5l1a
gate hints and its "Stay back, there's a sniper up there!"; the M5L2A tank tutorial (single player only); the
countdowns ("5 seconds to clear the room", "30 seconds to escape to elevator", "Charges set. n seconds ...");
"You must first open the valves."; the two m6l3a HINT lines; the Ranger casualties counter; and
**"Your cover is blown!"** on m6l1c / m6l2a (a stealth-state line the player must act on, as on m2l2a).
Debug lines found are all unreachable (m4l0: behind `if( 0 && ...)` and after a bare `end`; M5L2A / m5l2b
`local.messagePrintout` is never assigned).

## Spearhead and Breakthrough

| Line | Original | Decision | Why / new feed line |
|---|---|---|---|
| t2l1.scr:1322, t2l4.scr:1014 | "You picked up a sniper rifle" | feed | team, `t2l1_sniper` / `t2l4_sniper`, same words |
| t2l1.scr:2021 | "<name> is down - n left. Lose them all and the mission fails." | removed | objective 6 republishes "[n remaining]" on the next line and the retail killed-in-action line fires on the same death |
| t2l3.scr:3457 | "THEY ARE THROUGH ON <side> - hunt him down! n more breaches and the line falls." | feed (amber) | `t2l3_breach`: "They are through on <side> - n more breaches and the line falls"; the objective has the count but not the side |
| t3l2.scr:1242 / 1814 | "You are riding the T-34. Seats are locked for this mission." / "You are riding the T-34." | feed | personal, `t3l2_seat` |
| e1l4/Intro.scr:175 | "Cover blown!" | removed | a co-op duplicate of the retail line three seconds earlier ("You've blown your cover without getting on the ship!"), sirens already on |
| e3l3/scene1.scr:174 | "Stealth phase: hold your fire until the ambush!" | removed | fired once at map setup; the line at 986 says it when a living player exists |
| e3l3/scene1.scr:986 | "Stealth phase: weapons are secured until the ambush is sprung!" | kept | the only explanation for empty hands, and it fires during the mission title and briefing, when the HUD (and the feed with it) is hidden - as a feed line it aged out unseen (mod 384a3697) |
| e3l3/scene1.scr:1008 | "Weapons free!" | feed | team, `e3l3_free` |

Kept: every mission-failed and killed-in-action line (t2l1, t2l2, e1l2, e1l3, e1l4, e2l1, e2l3, e3l2, e3l3, e3l4);
"THE LINE IS BROKEN - fall back!" (t2l3: the only text for that loss); "Your cover was blown." (e1l3); the
Hold-USE / press-use prompts (e2l1 glider, e2l2 jeep); "You have not completed all your objectives yet." (t2l1,
retail refusal); single-player branches. Debug lines are all behind gates that are off (`level.showTriggerMessages`,
`level.hackIntro`, `level.freeCam`, `level.skip_scene*`), dead (`e1l4.scr::ArmPlayer`, `e1l1 tankHealthHud`) or
inside `/* */`.

## Allied Assault, missions 1-3

| Line | Original | Decision | Why / new feed line |
|---|---|---|---|
| m1l2a.scr:498 | "The SAS Agent moves up to the interrogation." | removed | he walks there in view and the objective follows him |
| m1l2a.scr:728 | "Follow the SAS Agent." | feed | team, `m1l2a_follow`; fires only when the team has left him behind |
| m1l2a.scr:2943 / 3126 (+ six callers) | the per-player refusals: "You need to be accompanied by the SAS Agent to blow up the gate / the flak", "Grillo needs to be outside of combat ...", "Grillo is on his way to you", "The player leading Grillo needs to come here ...", "You have no explosives" | feed | personal, `m1l2a_hint` (one key: a newer reason replaces the older one); co-op lines, each the only explanation of a refused USE |
| m1l2a.scr:3331 | "The town has been put on full alert, expect reinforcement waves!" | feed (amber) | `m1l2a_alert`: "The town is on full alert - expect reinforcement waves" |
| m2l2a.scr:294 | "You need a new set of papers to procede past this point." | feed | team, `m2l2a_papers` (spelling corrected) |
| m2l2a.scr:707 | "Naxos sabotaged." | removed | the objective is ticked on the same line |
| m2l2b.scr:282 / 312 | "Recover the Enigma manifest first." | feed | team, `m2l2b_manifest` |
| m2l2b.scr:1121 | "Decrypting Enigma traffic..." | feed | team, `m2l2b_enigma` |
| m2l2c.scr:149 / 160 | `iprintlnbold_noloc("farplane[n]:" + level.fogplane)` | console | a fog debug dump that could reach the screen |
| m3l1a.scr (six sites) | "You have received health from a medic." | feed | `medic`: "A medic patched you up". Sent to every player, because the scene's `$player heal` heals every player |
| m3l2.scr:1949 / 2076 / 2234 | "Once you find a radio / destroy the anti-aircraft gun you will be able to call in air support." | feed | team, `m3l2_air` |
| m3l2.scr:2896 | "You where moved because you where to far away from the Battle" | feed | personal, `m3l2_moved` (spelling corrected) |
| M3L3.scr:409 | "Hint: the bazooka will respawn after a few seconds." | feed | team, `m3l3_bazooka` |
| M3L3.scr:2650 / 2660 | "TIGER TANK: n percent" / "Tiger Tank destroyed." | feed | team, `m3l3_tiger`: one line that updates in place instead of a bold line per hit |
| M3L3.scr:6805 | "Get back inside the church - nobody is holding it." | feed (amber) | personal, `m3l3_church`; the hold fails if nobody returns |
| M3L3.scr:7300, 7484, 8080, 8150, 8202, 8231 | "Ladder placed ...", "The airborne are on their way ...", "Flak gun destroyed ...", "Smoke out ...", "Hold the church ...", "The church holds - C-47 inbound!" | removed | co-op narration; each fires where the objective changes or the scene (smoke, aircraft, voice) plays |
| M3L3.scr:7947 / 7975 | "Church clear. Grab the explosives." / "Explosives set. Destroy the flak gun ..." | feed | team, `m3l3_explosives`: "Grab the explosives for the flak gun" / "Explosives picked up - plant them on the flak gun" |
| M3L3.scr:8031 | "Charge set - clear the area!" | feed | team, `m3l3_charge`: "Charge set on the flak gun"; the 15 s stopwatch and its ticking start on the same line |

Kept: killed-in-action and mission-failed lines (m1l1, m1l2a:3757, m3l2, M3L3); the exit refusals (m1l2b:668,
m2l2b:429, m3l2:2882); "You have been seen!" / "Your cover is blown!" (m2l2a) and "Your cover has been blown."
(m2l2b); the retail act-now hints (m1l1:2667, m3l2:1608, M3L3:695 / 2740); the retail one-liners at a ticked
objective (M1L3c:295 "Equipment Destroyed", m2l2b:1144 "Manifest stolen"). m3l1a / m3l1b: only the medic line.

## Questions (lines where the right answer is the user's)

1. **"Cover blown" lines** (m2l2a x2, m2l2b, m6l1c, m6l2a, e1l3): kept bold on the left. They could be an amber feed
   line instead (amber is also drawn in Hardcore).
2. **"You have not completed all your objectives"** (retail, about fourteen maps): kept on the left. Could be a feed line.
3. **Killed-in-action lines** ("Cpt. Ramsey killed in action" and the like, retail): kept. Could be a feed line where
   the mission goes on after the death.
4. **Hardcore**: only amber feed lines are drawn there. The refusal explanations now in the feed (m1l2a SAS / Grillo
   reasons, m6l1c / m6l2a "The alarm is up ...", "Not yet - you still need ...", "Too exposed ...", "You are in uniform")
   are therefore not shown to a Hardcore player, who did see the old left-side line.
5. **Removed, but the scene carries less than a sentence did**: t2l1:2021 (the name of the squadmate who went down is
   no longer printed, only the count in the objective); m6l2a:2761 "Out of time - the charges are going" (the stopwatch
   runs out and the blast follows); e3l3/scene1:174; e1l4/Intro:175 "Cover blown!" (a duplicate of the retail line).
6. **e3l1/BritHQ.scr:209 "Approach the jeep"**: left as it was (an Omaha-campaign map, and it is not clear the scene
   alone tells a player to walk to the jeep).
7. **Retail one-liners at a ticked objective** (M1L3c "Equipment Destroyed", m2l2b "Manifest stolen"): kept as retail
   strings although the objective says the same.
8. **A feed line sent while the HUD is hidden is never seen.** `drawhud 0` (mission title cards, briefings,
   cinematics) hides the feed, and a line goes on ageing while hidden. Found on e3l3 (question row above). The feed
   could instead hold a line until the HUD is back; that is a change to the feed itself, not made here. M3L3's
   bazooka hint (4 s after map start) is the other round 3 line near a map start; M3L3 does not hide the HUD.

## Proof

- Compile: every touched script, working-tree copy, loaded on a test server and asked for a label that does not
  exist - "label 'zz_compile_probe' does not exist in '<file>'" for 18 of 18, no compile-failure line in the log
  (scratch `round3_verify.py`); e3l3/scene1.scr again after its revert. depthscan2 / linecheck / quotecheck /
  prosecheck clean, check_mp_isolation 22 of 22.
- Stills (1280x720, left message box ON, HUD not faded, the real script label run by a driver):
  `media/round3_m3l2_air_support.jpg`, `media/round3_m6l2a_uniform_refusal.jpg`, `media/round3_t2l3_breach.jpg` -
  the line is in the feed at the bottom left and the left side is empty.
- Not run in play: every other line of the tables (their triggers need the mission played to that point).
- Commits (mod coop-wip): 3704ab07 (AA 1-3), a464b62e (AA 4-6), 8dc7a200 (Spearhead / Breakthrough), 384a3697 (e3l3).
