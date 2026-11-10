# Chronological Campaign - the order (v1.10.64 candidate)

User ask (2026-11-08): *"I want a new Begin Chronological Campaign button added to the coop menu under Begin Full Campaign.
This should do exactly what it sounds like, play the campaign chronological based on order of events."*

The chain itself lives in `hzm-mohaa-coop-mod/coop_mod/chrono.scr` (`nextMission`). This file is the reasoning behind it.

## Which game is which

In the War Chest paks, **Spearhead is the t-series** (`mainta/pak1.pk3`: `t1l1`-`t3l2`, briefings `briefingt1-3`) and
**Breakthrough is the e-series** (`maintt/pak1.pk3`: `e1l1`-`e3l4`, briefings `briefinge1-3`). The worldspawn messages agree:
`e1l1` = "Tunisia - Battle of Kasserine Pass I", `t1l1` = "Normandy". (Some older comments in `coop_mod/maplist.scr` have the
two names the other way round.)

## The order

Missions are ordered by the date each one **opens**; a mission's own levels always stay together and in their own order.

| # | Mission | Game | Date | Maps (briefing, then levels) |
|---|---|---|---|---|
| 1 | Lighting the Torch | Allied Assault M1 | 7-8 Nov 1942 (Operation Torch, Arzew, Algeria) | briefing1, m1l1, m1l2a, m1l2b, m1l3a, m1l3b, m1l3c |
| 2 | Scuttling the U-529 | Allied Assault M2 | 12 Feb 1943 (Trondheim, Norway) | briefing2, m2l1, m2l2a, m2l2b, m2l2c, m2l3 |
| 3 | Tunisia | Breakthrough E1 | 20 Feb 1943 (Kasserine) to Apr-May 1943 (Bizerte) | briefinge1, e1l1, e1l2, e1l3, e1l4 |
| 4 | Sicily | Breakthrough E2 | 9-10 Jul 1943 (Operation Husky: glider landing, Caltagirone, Gela) | briefinge2, e2l1, e2l2, e2l3 |
| 5 | Italy | Breakthrough E3 | 12 Jan 1944 (Monte Cassino) to 28 Sep 1944 (Monte Battaglia) | briefinge3, e3l1, e3l2, e3l3, e3l4 |
| 6 | Normandy | Spearhead T1 | night of 5-6 Jun 1944 (airborne drop ahead of the landings) | briefingt1, t1l1, t1l2, t1l3 |
| 7 | Operation Overlord | Allied Assault M3 | 6 Jun 1944 (Omaha Beach) | briefing3, m3l1a, m3l1b, m3l2, m3l3 |
| 8 | Behind Enemy Lines | Allied Assault M4 | 22 Jun 1944 (Normandy) | briefing4, m4l1, m4l2, m4l3 |
| 9 | The Day of the Tiger | Allied Assault M5 | 20 Aug 1944 (Brittany, the Brest area) | briefing5, m5l1a, m5l1b, m5l2a, m5l2b, m5l3 |
| 10 | Bastogne | Spearhead T2 | 24-25 Dec 1944 (Battle of the Bulge) | briefingt2, t2l1, t2l2, t2l3, t2l4 |
| 11 | Return to Schmerzen | Allied Assault M6 | 18 Jan 1945 (Siegfried Line, Germany) | briefing6, m6l1a, m6l1b, m6l1c, m6l2a, m6l2b, m6l3a, m6l3b, m6l3d, m6l3c, m6l3e |
| 12 | Berlin | Spearhead T3 | 30 Apr 1945 (Battle of Berlin) | briefingt3, t3l1, t3l2 |

`m4l0` is not part of either campaign chain (it is not reached from any briefing or level), so it is not in this one either.
The AA M6 level order m6l3b -> m6l3d -> m6l3c is the game's own (the files are named out of order).

## Sources, and the calls that needed judgement

**The games' own text comes first.** It dates very little: `maps/m3l1a.scr` carries "June 6, 1944" and `maps/t2l1.scr`
"Dec 24, 1944" (both also used for the mod's title cards, `coop_mod/menumirror.scr`). The worldspawn messages name the places
(Kasserine, Bizerte, Glider Landing, Caltagirone, Gela, Monte Cassino, Anzio, Monte Battaglia, Normandy, Bastogne, Berlin),
and the AA briefing art names the rest (`arzewaerial`, `naxos`, `brestmap`, `schmerzen`). The remaining dates are the in-game
mission dates as catalogued by the Medal of Honor wiki (List of Missions; Allied Assault, Breakthrough and Spearhead mission
pages), checked against the historical operations they depict.

- **AA M2 (12 Feb 1943) before BT E1 (20 Feb 1943).** Eight days apart; the U-529 raid comes first. (The real U-529 was lost
  in February 1943, which fits.)
- **BT E1 spans February to spring 1943.** The wiki dates Kasserine 20 Feb and Bizerte 20 Apr 1943; historically Bizerte fell on
  7 May 1943. Either way it sits wholly between AA M2 and BT E2.
- **BT E3 (Italy) is the one genuinely ambiguous mission.** Monte Cassino (Jan 1944) and Anzio (22 Jan 1944) come long before
  Normandy, but its last level, Monte Battaglia, is 28 Sep 1944 - after AA M4 and M5. A mission's levels cannot be split, so it is
  placed by its opening date (Jan 1944), before Normandy. The alternative - after AA M5 - would put Cassino and Anzio five to eight
  months out of order to fix one level.
- **SH T1 before AA M3.** Spearhead's drop is the night of 5-6 June; the Omaha landings were at 06:30 on 6 June.
- **AA M4 / M5.** 22 Jun 1944 (Normandy, behind the lines) and 20 Aug 1944 (Brittany, consistent with the siege of Brest,
  Aug-Sep 1944).
- **SH T2 (Dec 1944) before AA M6 (18 Jan 1945).** The Bulge first; Schmerzen follows a month later.
- **SH T3 Berlin (30 Apr 1945) is last.**

## What happens at the ends

- The two finales that roll credits instead of handing over - **e3l4** (Breakthrough) and **m6l3e** (Allied Assault) - are not
  last here, so in this campaign they go to the next mission's briefing instead of the credits (hooks in `maps/e3l4/Outro.scr`
  and `maps/m6l3e.scr::roll_credits`).
- After **t3l2** (Berlin) the saved progress is cleared and the server returns to the lobby, which starts the order again - the
  same loop t3l2 already did (`missioncomplete t1l1`). The finale has no credits roll of its own; that is an open item.
