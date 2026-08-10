# Objective challenges — script-derived, trilogy-wide

**Rewritten 2026-08-08, replacing the first version rather than sitting beside it.** That version was
written from objective *text* plus general knowledge and spot-checked afterwards. Wrong method: it
produced four proposals assuming mechanics the maps do not have (three needed a shots-fired stat that
exists nowhere in the mod; one needed an alarm on m1l2b, which has none). This version is derived the
other way round — **read what each map script already tracks, then write the challenge against it.**

Every entry names the **variable and line** it reads. If a challenge is not here, it is because the
map exposes no hook for it, not because nobody thought of it.

## Why this is the feasible method

Every campaign challenge in `coop_mod/challenges.scr` keys on a bespoke stat (`cc_*`, `obj_*`,
`evt_*`) that a map script bumps at a chosen moment. There is **no** generic tracking of "was seen",
"shots fired" or "alarm raised". A challenge is therefore feasible exactly when the map already
maintains a variable that answers it — a flag it sets, a counter it increments, or a timer it stamps.
Those are what the hook scan extracted, and they are the only things quoted here.

**Wiring cost per entry:** one `chal_bump` at the site named in the Hook column, plus a `chal_def`.
No engine work.

---

## Allied Assault

### m1l1 — the checkpoint village
Eleven `level.flags[...]` gates initialised at `m1l1.scr:102-111`, set by the scripted scenes.

| Title | Feat | Hook |
|---|---|---|
| No Time to Explain | Get out of the checkpoint within 20s of the door opening | `flags[door]` :293 vs `flags[checkdoor]` :107 |
| Lights Out in the Village | Finish with the lantern out | `flags[lantern]` :109, set :904 |
| All the Way In | Complete the truck ride uninterrupted (existing "Rode It In" is a different feat) | `flags[ride]` :103, `flags[ridecomplete]` :108 |
| Bazooka Improvisation | ⚠️ Take the intro bazooka before the truck is destroyed — the target only becomes `triggerable` at :985 and `killtruck` threads at :987, so the window is ~1s inside a cutscene. Verify before building. | `flags[introbazooka]` :106 |
| Not a Friend Lost | Finish with zero dead friendlies | `level.deadfriends` |

### m1l2a — the fortress
Seventeen flags at `:83-93` — the richest single map in the trilogy for this.

| Title | Feat | Hook |
|---|---|---|
| Unmarked Prisoner | Reach the POW without the prisoner taking damage | `flags[POW_damage]` :83 |
| The Right Choice | Complete the branch without changing your mind | `flags[choice]` :86 + `flags[choicechange]` :93 |
| Their Own Guns | Destroy the Flak by the friendly-flak route | `flags[friendlyflak]` :90 vs `flags[flak]` :89 |
| Every Charge Counts | Finish using no more than the explosives issued | `level.explosivecount`, `level.bombnum` |
| Ticket to Ride | Complete the truck ride sequence intact | `flags[truckride]` :84 |

### m1l3b / M1L3a — the coast
| Title | Feat | Hook |
|---|---|---|
| Coastal Clean Sweep | Kill every counted defender on the approach | `level.totalbaddies` m1l3b :67, M1L3a :77 |
| Charges to Spare | Destroy the target using fewer charges than issued | `level.bombnum` m1l3b :52 |

### m2l1 — the research facility
| Title | Feat | Hook |
|---|---|---|
| The Whole Filing Cabinet | Finish with zero documents left behind | `level.remaining_documents` :41 |
| Seven Minutes | Clear the scene-7 sequence inside its own timer | `level.s7_time` :34 |

### m2l2a / m2l2b — the U-boat pens
| Title | Feat | Hook |
|---|---|---|
| Let Them Finish the Hand | Reach the objective with the card players still alive | `level.deadcardplayers` :233 |
| Cut the Hand Short | The inverse — eliminate every card player | `level.deadcardplayers` :233 |
| Wall to Wall | Complete every wall-science step | `level.wallscifinishcount` :1366 |
| Charges and Gates | Plant every bomb without leaving a gate open | `level.bombcount` :53 + `level.gatecount` :80 |

### m2l3 — the escape
| Title | Feat | Hook |
|---|---|---|
| Through the Vents | Take a set number of kills from the vents | `level.ventkills` :121 |
| Nothing Left Behind | Finish with every counted enemy dead | `level.deadoenemies` :77, `level.deadspawnguys` :112 |

### m3l1a / m3l1b — Omaha and the bunkers
| Title | Feat | Hook |
|---|---|---|
| Crater to Crater | Cross the beach by the crater route | `flags[craters]` :244 |
| Beach Party Timing | Reach the shingle inside the beach timer | `level.beachPartyTime` :5132 |
| Backline Cleared | Kill every counted rear defender | `level.coop_rear_total` :2341 |
| Fifteen Second Fuse | Plant and clear before the bomb timer expires | `level.bomb_tick_time` :2134, `bomb_set_time` :2139 |
| Not One Ally Lost | Finish with the full ally count intact | `level.coop_ally_total` :2901 |

### m3l2 — Battle in the Bocage
| Title | Feat | Hook |
|---|---|---|
| Clip Their Wings | Destroy the Flak 20 | `level.flak20dead` :38 |
| Scene Four, Clean | Complete the scene-4 defence without failing it | `level.scene4_complete` :40 |

### m4l1 / m4l2 / m4l3 — Maquis and the tank park
| Title | Feat | Hook |
|---|---|---|
| Everyone Walks Out | Finish the escort with the full alive count | `level.alive_count` m4l1 :80 |
| First Objective, First Try | Complete objective 1 without a retry | `level.obj1_complete` m4l2 :75 |
| Clean Ending | Reach the ending with every counted enemy down | `flags[ending]` m4l3 :89 + `level.totalbaddies` :88 |

### m5l1a / m5l1b — Sniper Town
| Title | Feat | Hook |
|---|---|---|
| Bazooka First | Recover the bazooka before the reunion | `flags[gotbazooka]` :68 vs `flags[reunion]` :71 |
| Every Sniper Accounted | Kill every counted sniper | `level.deadsnipers` m5l1a :154 / m5l1b :105 |
| Every Position Searched | Search every crew position on the map — the bazooka only appears when `searchedcrews == totalcrews` (:1351), so this is what the level is really asking | `level.searchedcrews` :1347 vs `level.totalcrews` :1332 |
| Crew Intact to City Hall | Reach city hall with the tank crew alive | `flags[tankcrew]` :124, `flags[cityhall]` :125, `flags[tankcrewdead]` :121 |
| Full Card | Complete every counted objective on the level | `level.completeobjs` :127 |

### m5l3 — the bridge
Twelve flags at `:102-112` — the cleanest narrative state machine in the trilogy.

| Title | Feat | Hook |
|---|---|---|
| Plunger Denied | ⚠️ Stop the demolition before the plunger is destroyed — but m5l3:1124 comments "Tank has destroyed the plunger" inside the tank firing sequence. Only feasible if killing the tank first prevents it. Verify. | `flags[plungergone]` :103 / :1124 |
| The Bridge Stands | Finish with the bridge intact | `flags[Bridge_Is_Gone]` :106 never set |
| In Position First | Be ready to snipe before the tank reaches the bridge | `flags[readytosnipe]` :104 vs `flags[tankatbridge]` :102 |
| Guns Before Armour | Kill the Flak 88 before the final tank approaches | `flags[Flak88_dead]` :109 vs `flags[Final_Tank_Approaches]` :105 |
| No King Tiger Lost | Finish without losing the King Tiger | `flags[King_Tiger_Lost]` :108 |
| Before the Guns | Win without calling artillery | `flags[Artillary_Ready]` :110, `flags[The_Day_is_won]` :112 |

### m6l1c / m6l2a / m6l3a / m6l3b / m6l3d — Fort Schmerzen
| Title | Feat | Hook |
|---|---|---|
| Second Objective, Untouched | Complete objective 2 without being wounded | `level.obj2complete` m6l1c :943 |
| Charges as Issued | Complete the radio post using the counted charges | `level.objective1_bombcount` m6l2a :161 |
| Waypoint Discipline | Complete the allied advance without losing the waypoint | `level.scene2_ai_waypointnumber` m6l3a :1073 |
| Every Objective in Scene Six | Complete all scene-6 objectives | `level.scene6_objectives_complete` m6l3a :2485 |
| Valve by Valve | Open every counted valve | `level.valvecount` m6l3d :65 |
| Objective One, First Pass | Complete objective 1 without dying | `level.objective1complete` m6l3b :138 |

## Spearhead

| Title | Feat | Hook |
|---|---|---|
| Charges Laid | Plant every bridge charge the script counts | `level.chargecount` t1l3 :137 |
| Parade Ground | Clear the parade without exceeding the death counter | `level.parade_death_counter` t2l1 :93 |
| All Four Objectives | Finish t2l1 with all four objective flags set | `obj1-4Complete` t2l1 :83-86 |
| Latrine Duty | The map counts this. Find out why. | `level.toiletcounter` t2l1 :94 |
| Convoy Seats Filled | Complete the ride with every seat occupied | `level.coop_seatCount` t2l2 :1123 |
| Reinforcements Unneeded | Finish without the reinforcement count rising | `level.coop_reinfCount` t2l2 :1170 |
| First Wave Unbroken | Kill the full wave-1 infantry count | `level.totalinfantrykilledinwave1` t2l3 :1391 |
| Three Waves, Full Count | Clear all three waves' counted infantry | `...wave1/2/3` t2l3 :1391 / :1487 / :1622 |
| Found Him Fast | Reach the captain inside the find timer | `level.findcaptaintime` t2l3 :107 |
| Kept Him Breathing | Captain survives his full live-timer | `level.captainlivetime` t2l3 :101 |

## Breakthrough

⚠️ **The e-series exposes almost no hooks.** e1l2, e3l1, e3l4 and e1l4 set no challenge-usable flags
or counters at all; e3l3 has three triggers and nothing else. Proposing challenges there would mean
inventing the tracking first, so **none are proposed** — that is a finding, not an omission. If the
e-series should have objective challenges, instrumenting those maps is the prerequisite.

---

## Maps with no usable hook

`e1l2`, `e3l1`, `e3l4`, `m4l0`, `m6l1a`, `m6l1b`, `m6l3c`, `m6l3e`, `t1l1`, `t1l2`, `t2l4`, `t3l1`,
`training` — no flags, counters or timers a challenge could read. Anything here needs new
instrumentation in the map script first.

## Third filter: can the player influence it?

A hook existing is not enough. **m1l1's checkpoint always goes loud** — `thread gotshot` sits at
`m1l1.scr:983` in a straight-line cutscene (papers animation completes, flag is set, truck is
destroyed), and the published walkthroughs agree: *"A German will check the papers... he'll say
they're no good... the ambush occurs regardless of player action."* A challenge to keep that scene
quiet is impossible, and it has been removed rather than left in looking plausible.

An automated screen classified all 95 hook sites as player-influenced or unconditional. **Treat it as
a screen, not a verdict** — it has false positives: `t1l3` `chargecount++` looked unconditional but
sits inside `placeexplosive1:`, which only runs when a player plants a charge. The condition is the
label being reached, not an `if`. Conversely it correctly caught `m5l3` `plungergone`, written inside
the enemy tank's firing sequence.

**So the remaining verification is per-entry and manual:** open the write site named in the Hook
column and answer one question — *can a player change whether this line runs?* That is minutes per
challenge against a named line, and it cannot be skipped.

## What external walkthroughs were worth

Two outcomes, both useful, neither of them "more objectives":

- **A claim rejected.** The Medal of Honor wiki describes a hidden minigame on Sniper's Last Stand —
  finish on Hard with the tank crew alive and a bazooka-armed medic hunts you for 60 seconds. There is
  **no such logic in the shipped scripts** (no `bazookamed`, no seeker, nothing). Fan wikis carry
  myths; a walkthrough claim needs the same verification as a guess.
- **A real error in this document found.** Chasing that lead through m5l1a showed `level.totalcrews`
  is not "vehicle crews to kill" — it counts **crew search positions**, and `flags[bazooka]` only
  fires once `searchedcrews == totalcrews`. The entry above was rewritten. That is precisely the
  "semantics unverified" risk this document warns about, caught in the wild.

The general lesson: guides are good for **finding leads and confirming what is scripted** — GameRevolution
settling the m1l1 checkpoint was worth more than any amount of staring at the script. They are not
evidence on their own.

## Method

Hooks extracted mechanically across all 49 objective-bearing map scripts — `level.flags[x]`
assignments, `level.*` counters and timers, labels, `waittill death` / `waittill trigger` sites — then
challenges written only against what the scan returned. The scan is reproducible
(`scratchpad/hooks.py`). Titles checked against all 303 existing challenges; no collisions.

**What is still unverified:** that each named variable holds the value the feat assumes at the moment
it is read. The scan proves a variable exists and where it is written; it does not prove the semantics.
Each entry needs its site read once before implementation — that is a five-minute check per challenge,
against a named line, rather than a design question.
