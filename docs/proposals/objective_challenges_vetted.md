# Vetting Report - Objective & Scripted-Event Challenges (47 proposals)

**Audit date:** 2026-08-04 · **Scope:** READ-ONLY. No game files were modified.

**Sources compared:**
- `docs/proposals/objective_challenges.md` (47 proposals, ids `obj_*` / `evt_*`)
- `hzm-mohaa-coop-mod/coop_mod/challenges.scr` - 235 shipped `chal_def` lines (lines 59-336),
  including the 23 `fac_*` faction challenges and `cc_static_line`
- `challenges.scr::cc_objFeat` (:1098-1133) - the 31 claimed `map:index` feat keys
- `challenges.scr::chal_mission_complete` (:1323-1393) - the map-completion / playstyle feats
- The 12 in-map `chal_team_bump` / `cc_award_clean` call sites (e1l1, e1l4, e2l1 x2, e3l3, m4l3,
  m6l3c, t2l1 x2)
- Map scripts spot-checked to settle contested calls: `m3l2.scr`, `m5l1b.scr`, `m1l2a.scr`,
  `m3l1a.scr`, `e1l4.scr` + `e1l4/Ship.scr`, `e1l1/scene3.scr`, `t2l1.scr`, `t2l4.scr`

**Headline:** 46 of 47 survive. 1 is a true duplicate. 11 need text or target changes before
they go in. **No stat-name collisions** - but 4 descriptions carry em-dashes that would
parse-kill `challenges.scr` if pasted verbatim.

---

## 1. Summary table

| # | proposal id | verdict | collides with | note |
|---|---|---|---|---|
| 1 | `obj_whole_section` | KEEP | - | m1l1 shares map with `cc_torch` (m1l1:4, player no-down) and `m_first` (map completion). Different axis: named-NPC survival. |
| 2 | `evt_cut_him_down` | KEEP | - | POW is Pvt. Jury (`m1l2a.scr:3741`, `self delete` on damage), NOT the SAS Agent/Grillo of `cc_the_rescue` (m1l2a:6). **Wiring fix:** award off `level.flags[hostage] = 1` (`:3796`), not `m1l2a:1` - objective 1 is "Find and rescue the SAS Agent", the wrong beat. |
| 3 | `evt_monkey_business` | KEEP | - | m1l3b's only other feat is `cc_pointe_du_hoc` (m1l3b:3). **Em-dash in description - must be stripped.** |
| 4 | `evt_turd_kind` | KEEP | - | m1l3c holds `cc_lights_out` (:1) and `cc_signal_fleet` (:3). Unrelated. |
| 5 | `obj_the_manifest` | KEEP | - | m2l2b genuinely unclaimed. `cc_naxos` / `cc_das_boot_stealth` are m2l2a. |
| 6 | `obj_ghost_ductwork` | KEEP | - | Same index as `cc_end_of_line` (m2l3:2) but that is a `cc_award_clean` no-down test; this reads an alert-escalation latch. Both co-fire legitimately. |
| 7 | `obj_dog_green_present` | **OVERLAP** | `cc_finest_hour` | Both m3l1a, both `cc_award_clean`, both read `coop_wentDownMap`. m3l1a:7 ("Infiltrate the bunker", completes `:3389`) is strictly later than m3l1a:3 (bangalores) and the latch never resets mid-map, so **earning this always earns cc_finest_hour**. Legitimate tier, but the name also clashes with `cc_end_of_line` ("All Present and Accounted For"). **REWORD.** |
| 8 | `obj_both_doors` | **OVERLAP** | `cc_rangers_house` | **Verified same building.** `m3l2.scr:186` obj1 = "Search the house.", `:624` obj2 = "Defend the back of the house.", `:997` obj3 = "Defend the front of the house." `cc_rangers_house` is m3l2:1 + `cc_award_clean`; this is m3l2:2+3 + `cc_award_clean` - same house, same latch, strictly later. **REWORD** as an explicit tier. |
| 9 | `evt_five_shells` | KEEP | - | Not covered by `kt_rocket` (counter, stat `rocket`), `wpn_panzerschreck` (counter) or `cc_tiger_country` (t2l1 sticky bomb). **REWORD**: tracking is a means-of-death test, it cannot count five shells; and the description carries an em-dash. |
| 10 | `obj_not_a_scratch` | **OVERLAP** | `cc_rough_landing` | Same map, **same objective index (m4l1:2)**, same NPC (`level.pilot`). Existing = "alive"; proposal = "never hit". Distinguishable (damage latch vs `isAlive`) so a valid tier. **REWORD** so the pair reads as a tier. |
| 11 | `obj_rode_it_in` | KEEP | - | m4l2 holds `cc_kings_push` (sub-5-minute, per-player at mission complete). Different condition. `cc_resistance` is m4l3, not m4l2. |
| 12 | `obj_two_more_tigers` | KEEP | - | m4l3's only feat is `cc_resistance` (no-alarm). Adjacent line, different branch. |
| 13 | `obj_crew_intact` | **DUPLICATE** | `cc_king_tiger` | Existing description is verbatim the same achievement: *"Steal the King Tiger with the tank crew still alive"*. **DROP** - see section 4. |
| 14 | `obj_medic_over` | KEEP | - | m5l1b's only feat is `cc_king_tiger`. Hidden `game.skill == "hard"` branch, unclaimed. Ship-blocker risk (`missioncomplete void`) stands. |
| 15 | `evt_pole_position` | KEEP | - | m5l2a has no feat. `cc_day_of_tiger` is `map_m5l2b`. |
| 16 | `obj_bridge_stands` | KEEP | - | m5l3 holds `cc_tiger_defense` (tank >=85% HP), `cc_earn_this` (no heal/no death), `cc_the_bridge` (m5l3:4). None reads `Bridge_Is_Gone`. **Em-dash in description.** |
| 17 | `obj_no_bells_nordwind` | KEEP | - | No m6l1c alarm feat exists (`cc_welded_steel` = :2, `cc_first_of_kind` = :3). `cc_nordwind` is m6l1a. Co-fires with proposal #47 by design. |
| 18 | `obj_not_one_ranger` | KEEP | - | m6l3a completely unclaimed. |
| 19 | `evt_look_the_gas` | KEEP | - | m6l3d holds `cc_gas_gas_gas` (m6l3d:2, plant the charges). Gag vs objective. |
| 20 | `obj_unburned` | **OVERLAP** | `cc_schmerzen_escape` | Same map, **same label** - the proposal targets `m6l3c.scr:191-193`, which is exactly where `cc_schmerzen_escape` is already bumped (`:193`). Conditions differ (fire damage vs `coop_wentDownMap`) and are not supersets of each other, so both can stand. **REWORD** so it does not read as a re-skin of "Out Through the Fire". |
| 21 | `obj_both_boys_home` | KEEP | - | t1l2 holds `cc_nijmegen` (t1l2:1) and `m_market`. NPC-survival axis unclaimed. |
| 22 | `obj_four_charges` | KEEP | - | t1l3 unclaimed. **Design caution:** as specified it fires on plain objective-6 completion, i.e. it may be a completion freebie. Consider gating on the `bridge_kills_player:` fail path never having fired. |
| 23 | `evt_shabbadoo` | KEEP | - | - |
| 24 | `evt_kalimba_says` | KEEP | - | - |
| 25 | `evt_six_flushes` | KEEP | - | **REWORD**: description says "Stavelot", but `cc_quiet_town` already owns "Stavelot" for **t2l4**, and this is t2l1. |
| 26 | `obj_three_came_back` | KEEP | - | t2l1 holds `cc_purple_heart` and `cc_tiger_country` (both destruction) and `m_bulge`. Squad-survival unclaimed. **REWORD**: same "Stavelot" text clash with `cc_quiet_town` (t2l4). |
| 27 | `obj_turnabout` | KEEP | - | Distinct from `cc_purple_heart` (destroy the Nebelwerfers) and `cc_tiger_country` (sticky-bomb the Tiger). **REWORD**: the proposed hook is plain objective-2 completion and cannot verify "with a captured Nebelwerfer". |
| 28 | `obj_running_on_fumes` | KEEP | - | `cc_return` is `map_t3l2` - a completion freebie. Completion-freebie + condition-feat on one map is the catalogue's established pattern (`cc_shingle` + everything on e3l4), not a collision. |
| 29 | `obj_both_guns_turned` | KEEP | - | e1l1 holds `cc_desert_fox` (tank duel, `scene3.scr:564`) and `m_kasserine`. Verified `$scene3Cannon1`/`$scene3Cannon2` + `level.seize_enemy_artillery_objNum` are unclaimed. **REWORD**: "Destroy both Flak 88s" would be the **third** near-identical description after `cc_rangers_flak` (m3l2) and `cc_nijmegen` (t1l2). |
| 30 | `obj_save_the_crab` | KEEP | - | e1l2 unclaimed. `cc_convoy` (t2l2 truck) and `cc_tiger_defense` (m5l3) are other maps. |
| 31 | `obj_sneakers` | KEEP | - | e1l3 unclaimed. Reads `level.sneakersDetected`, **not** the alarm system - so it will not double-fire with proposal #47. |
| 32 | `obj_every_man_out` | KEEP | - | e1l3 unclaimed. Near-identical *wording* to proposal #40 (`obj_all_seven_home`) but different map and different NPC set - see section 6. |
| 33 | `obj_not_a_single_bell` | **OVERLAP** | `cc_stowaway` | Same map, same "stay undetected" family. **Verified they can diverge:** `cc_stowaway` reads `level.coop_coverBlown`, set by a *music transition trigger* (`e1l4.scr:401`, `$musicTransitionCoverBlown`); this reads `level.alarmSounded` (`Ship.scr:406`, 5 call sites). Genuinely different flags. **REWORD** so the two do not both read as "don't get caught". |
| 34 | `evt_they_never_saw_us` | KEEP | - | e2l1 holds `cc_enemy_mine` (AB-41 + Flak) and `cc_static_line` (McMartin pole). Unrelated scene. |
| 35 | `obj_all_six_home` | **OVERLAP** | `cc_static_line` | McMartin is one of the six. `cc_static_line` is a mid-map *rescue action* (`paraBattle.scr:261`); this is an *end-state count of six*. Earning all-six implies McMartin lived, so it is a one-of-six / all-six tier. **Keep unchanged** - the tracking distinguishes them cleanly. |
| 36 | `obj_let_them_sleep` | KEEP | - | e2l2's only feat is `cc_flugplatz` (`map_e2l2` freebie). |
| 37 | `evt_back_of_the_class` | KEEP | - | - |
| 38 | `obj_nine_tanks` | KEEP | - | e2l3 unclaimed. `cc_nuts` (t2l3:6 Bastogne waves) is a different map. |
| 39 | `evt_crunchy_goodness` | KEEP | - | e3l1 unclaimed. Same *design* as #9 but different map/weapon. **Em-dash in description.** |
| 40 | `obj_all_seven_home` | KEEP | - | e3l2 unclaimed. |
| 41 | `obj_nothing_gets_through` | KEEP | - | e3l3 holds `cc_rolling_thunder` (K5 finale, `e3l3.scr:133`). `cc_convoy` is the *Allied* truck on t2l2 - opposite side, other map. |
| 42 | `obj_able_baker_charlie` | KEEP | - | e3l4's only feat is `cc_shingle` (`map_e3l4` freebie). |
| 43 | `evt_seconds_to_spare` | KEEP | - | Timed feats exist (`cc_longest_day` m3l1a, `cc_kings_push` m4l2) but on other maps. |
| 44 | `evt_full_deck` | KEEP | - | Distinct from `kt_reinf` ("Kill 30 enemy reinforcements", stat `reinf`) - variety, not count. **Hard requirement:** the stat must be `evt_full_deck`; the `owave_<r>` markers are per-player dedupe flags and must live outside the stat namespace (see section 5). |
| 45 | `evt_not_today_fritz` | KEEP | - | `cc_hell_let_loose` is the other officer-wave no-down feat but keys on the officer/bodyguard/battalion wipe, not on wave types 4+5. |
| 46 | `obj_clean_sweep` | **OVERLAP** | `cc_end_of_line` (and every `cc_award_clean` feat) | At target 1 this is a generic superset of all seven existing no-down feats. `cc_end_of_line` (m2l3:2), `cc_nuts` (t2l3:6) and `cc_schmerzen_escape` (m6l3c) all sit on the *last* beat of their map, so the first time any of them pays, `obj_clean_sweep` pays too. **REWORD** - raise the target so it is a career goal. |
| 47 | `obj_the_quiet_type` | KEEP | - | Per-map no-alarm feats exist (`cc_silent_night`, `cc_under_radar`, `cc_resistance`, `cc_das_boot_stealth`) but this is a 5-mission career counter - a different axis, the same relationship `ms_*` has to `map_*`. |

**Totals: 35 KEEP as-is · 11 KEEP after reword · 1 DROP.**

---

## 2. DROP

### `obj_crew_intact` - duplicate of `cc_king_tiger`

`challenges.scr:281`:

```
waitthread chal_def "cc_king_tiger" "vehicles" "Beutepanzer" "Steal the King Tiger with the tank crew still alive" "cc_king_tiger" 1 "models/coop_helmets/coop_helmet_ger_tankhat.tik"
```

That *is* the proposal, word for word. What the proposal actually found is that `cc_king_tiger`
is **mis-wired**, not that a new challenge is needed. Verified at `maps/m5l1b.scr:1094-1103`:

```
if (level.engineers > 2){ setcvar g_medal1 "1" }          // all three crew
if (level.engineers > 1){                                  // two of three
    waitthread global/objectives.scr::add_objectives 4 3 "Steal the King Tiger with the tank crew." ...
```

`cc_objFeat` pays `cc_king_tiger` on `m5l1b:4`, which fires at **`engineers > 1`** - two of the
three crew. The shipped description promises three.

**Recommendation:** drop `obj_crew_intact` entirely and instead move the existing bump from the
`m5l1b:4` branch in `cc_objFeat` (`challenges.scr:1120`) onto the `level.engineers > 2` branch at
`m5l1b.scr:1094`. That makes the shipped description true and costs one line instead of a new
catalogue entry. This is a **bugfix to an existing challenge**, and is the only change in this
report that touches shipped behaviour - flag it for the user before acting.

Death messages for the disqualify latch, if a stricter version is ever wanted:
`m5l1b.scr:263 / :270 / :277`.

---

## 3. REWORD - exact replacement text

All 11 below are cleared for implementation **with the substituted text**. Every line here is
plain ASCII (no em-dash, no bare negative in parentheses) and is `chal_def`-ready.

### 3.1 `obj_dog_green_present` - tier over `cc_finest_hour`, and a name clash with `cc_end_of_line`

| | original | replacement |
|---|---|---|
| Name | Dog Green, All Present | **The Whole Beach** |
| Desc | Take the bunker at the top of Omaha without one man dying on the beach | **Take the bunker at the top of Omaha with nobody going down from the ramp to the door** |

```
waitthread chal_def "obj_dog_green_present" "campaign" "The Whole Beach" "Take the bunker at the top of Omaha with nobody going down from the ramp to the door" "obj_dog_green_present" 1 ""
```

### 3.2 `obj_both_doors` - tier over `cc_rangers_house`, same house

| | original | replacement |
|---|---|---|
| Name | Both Doors Held | **Held Both Doors** |
| Desc | Hold the back and the front of the farmhouse with nobody going down | **Clear the house and hold both the back and the front without anyone going down** |

```
waitthread chal_def "obj_both_doors" "campaign" "Held Both Doors" "Clear the house and hold both the back and the front without anyone going down" "obj_both_doors" 1 ""
```

### 3.3 `evt_five_shells` - em-dash + unenforceable claim

The proposed hook is a means-of-death test on `scene4_tank_death:`; it cannot count rockets.

| | original | replacement |
|---|---|---|
| Desc | Kill the Panzer with the Panzerschreck (em-dash) it takes exactly five | **Finish the Panzer at the crossroads with a Panzerschreck rocket** |

```
waitthread chal_def "evt_five_shells" "vehicles" "Five Shells" "Finish the Panzer at the crossroads with a Panzerschreck rocket" "evt_five_shells" 1 ""
```

### 3.4 `obj_not_a_scratch` - tier over `cc_rough_landing` on the same objective index

Keep the name (distinct from "Get the Flyboy Home"). Tighten the description so the pair reads as
alive / untouched, and **confirm at implementation time that the hook is a `waittill damage`
latch, not `isAlive`** - otherwise the two become identical.

```
waitthread chal_def "obj_not_a_scratch" "campaign" "Not a Scratch on Him" "Deliver the downed pilot to the Maquis hideout without him taking a single hit" "obj_not_a_scratch" 1 ""
```

### 3.5 `obj_unburned` - shares the exact label with `cc_schmerzen_escape`

| | original | replacement |
|---|---|---|
| Name | Unburned | **Not a Blister** |
| Desc | Escape the collapsing fort without a single player taking fire damage | **Escape the collapsing fort without any player taking a single point of fire damage** |

```
waitthread chal_def "obj_unburned" "campaign" "Not a Blister" "Escape the collapsing fort without any player taking a single point of fire damage" "obj_unburned" 1 ""
```

### 3.6 `evt_six_flushes` - "Stavelot" belongs to `cc_quiet_town` (t2l4), this is t2l1

```
waitthread chal_def "evt_six_flushes" "discovery" "Six Flushes" "Flush the outhouse six times and see what comes out" "evt_six_flushes" 1 ""
```

### 3.7 `obj_three_came_back` - same "Stavelot" clash

| | original | replacement |
|---|---|---|
| Desc | Finish Stavelot with your whole squad alive | **Get all three of your squad out of the Ardennes alive** |

```
waitthread chal_def "obj_three_came_back" "fireteam" "Three Came Back" "Get all three of your squad out of the Ardennes alive" "obj_three_came_back" 1 ""
```

### 3.8 `obj_turnabout` - description promises a weapon the hook cannot see

`halftrack_dead:` (`t2l1.scr:1647`) fires on objective 2 completing regardless of what killed it.
Two options; **A** is the safe one.

**A (no new tracking):**
```
waitthread chal_def "obj_turnabout" "vehicles" "Turnabout" "Destroy the halftrack blocking the Ardennes road" "obj_turnabout" 1 ""
```

**B (keep the flavour):** add a means-of-death / inflictor check inside `halftrack_dead:` before
the bump, and keep the original description. Costs a real map-script edit rather than a one-liner,
and must dodge the `coop_tank1DeathWatch:` failsafe noted at proposal wiring-note 6.

### 3.9 `obj_both_guns_turned` - third "both Flak 88s" description in the catalogue

Existing: `cc_rangers_flak` "Destroy both Flak 88s in the D-Day breakout" (m3l2) and `cc_nijmegen`
"Destroy both Flak 88s guarding the bridge town" (t1l2). Lean on *seize* and on Kasserine.

```
waitthread chal_def "obj_both_guns_turned" "campaign" "Both Guns Turned" "Seize both Flak 88 batteries above Kasserine Pass" "obj_both_guns_turned" 1 ""
```

### 3.10 `obj_not_a_single_bell` - split cleanly from `cc_stowaway`

`cc_stowaway` = the disguise/approach half (`level.coop_coverBlown`). This one = the ship's alarm,
right through the scuttling (`level.alarmSounded`).

```
waitthread chal_def "obj_not_a_single_bell" "discovery" "Not a Single Bell" "Scuttle the freighter and get clear without the ship alarm ever sounding" "obj_not_a_single_bell" 1 ""
```

### 3.11 `obj_clean_sweep` - raise the target or it is redundant

At target 1 it is auto-paid by `cc_end_of_line` / `cc_nuts` / `cc_schmerzen_escape`. Make it a
career goal so it sits alongside `ms_*` rather than duplicating the per-map no-down feats.

| | original | replacement |
|---|---|---|
| Name | Clean Sweep | **Spotless Record** |
| Desc / target | Complete every primary objective on a mission without one player going down / 1 | **Complete 5 missions with every primary objective done and nobody going down / 5** |

```
waitthread chal_def "obj_clean_sweep" "campaign" "Spotless Record" "Complete 5 missions with every primary objective done and nobody going down" "obj_clean_sweep" 5 ""
```

If the per-map expected-objective count proves unreliable (the proposal's own Risk note - e3l4
objective 8 is registered but its completion block is commented out at `e3l4.scr:101-107`), **drop
this one rather than shipping a challenge that cannot be earned.**

---

## 4. Stat-name collisions (hard bugs)

**None found.** All 47 proposal ids begin `obj_` or `evt_`. The shipped stat namespace is:

- `wpn_*` (69), `fac_*` (13 distinct), `cc_*` (43), `map_*` (12)
- bare counters: `kill`, `headshot`, `melee`, `scripted_havoc`, `wallbang`, `longshot`,
  `blindfire`, `savior`, `reinf`, `grenade`, `rocket`, `downedkill`, `vehicle`, `revive`,
  `airstrike`, `reinforce`, `officer`, `objective`, `sideobj`, `missions`

Zero intersection. Following the file's `stat == id` convention (comment at `challenges.scr:212`)
is safe for all 46 survivors.

**Two near-misses to guard at implementation time:**

1. **`evt_full_deck` must not bump `reinf`.** `kt_reinf` ("Welcoming Committee", 30 reinforcement
   kills) already owns that stat. The proposal's `owave_<r>` markers are per-player dedupe flags -
   store them as `self.coop_owave_<r>` or an entry in `self.flags[]`, never as a `chal_def` stat.
2. **`obj_clean_sweep` must not bump `objective`.** `t_obj` / `t_obj_e` own that stat (15 / 50
   primary objectives). Use stat `obj_clean_sweep`.

**Separate hard bug, higher priority than any of the above - 4 parse killers.** These proposal
descriptions contain **em-dashes (U+2014)**. Per `docs/TRAPS.md`, one non-ASCII character silently
compile-kills the *entire* `challenges.scr`, taking the whole challenge system down with it:

| proposal | offending text |
|---|---|
| `evt_monkey_business` | `Destroy Stuka number seven (em-dash) the one the developers hand-wired` |
| `evt_five_shells` | `Kill the Panzer with the Panzerschreck (em-dash) it takes exactly five` |
| `obj_bridge_stands` | `Finish The Bridge without the bridge going down (em-dash) theirs or yours` |
| `evt_crunchy_goodness` | `Kill the tank with the PIAT (em-dash) the objective they cut but never removed` |

ASCII-clean replacements are in the CLEARED list below. Run `docs/tools/depthscan2.py` on
`challenges.scr` after the append regardless.

---

## 5. Proposal-vs-proposal findings

No two proposals duplicate each other. Four things to be aware of:

1. **`obj_no_bells_nordwind` (#17) and `obj_not_a_single_bell` (#33) both feed `obj_the_quiet_type`
   (#47).** By design - one run pays the per-map feat and one of the five career ticks, exactly the
   way `map_*` and `missions` already coexist. Not a duplicate; just do not double-count within
   `obj_the_quiet_type` if a map raises the alarm flag more than once.
2. **`obj_sneakers` (#31) does NOT feed `obj_the_quiet_type`** - it reads `level.sneakersDetected`,
   not `global/alarm_system.scr`. If you *want* e1l3 to count toward the career feat, that is a
   second hook, not a freebie.
3. **`obj_every_man_out` (#32, e1l3 British prisoners) and `obj_all_seven_home` (#40, e3l2 POWs)**
   read almost identically in a list. Different maps, different NPCs - keep both, but consider
   making #32 read *"Break the British prisoners out of the Bizerte jail without losing one"* so
   the Service Record pages do not look like a copy-paste error.
4. **The "named allies survive" family is now 5 entries** (#1 m1l1, #21 t1l2, #26 t2l1, #35 e2l1,
   #18 m6l3a) after `obj_crew_intact` is dropped. That is fine - one per map - but they should not
   all get the same verb. Currently: "still on their feet" / "neither lost" / "alive" / "all alive"
   / "without losing a single man". Good enough as-is.

**Bonus finding, outside scope:** the shipped catalogue already contains a near-duplicate pair.
`cc_under_radar` ("Wire It Quiet" - wire the radio command post undetected) and `cc_silent_night`
("Silent Night, Deadly Night" - infiltrate the town and destroy the command post without raising
any alarms) are **both on m6l2a and both gated on `level.alarmactive != 1`**
(`challenges.scr:1124` and `:1381`). One run pays both, always. Worth a separate decision; not
touched here.

---

## 6. CLEARED FOR IMPLEMENTATION (46)

Append-only, at the end of `chal_init` - inserting mid-list shifts every later catalogue index and
silently mis-binds `ui/coop_sr.urc` (proposal wiring-note 1). Every line below is plain ASCII and
uses the file's `stat == id` convention with a deferred reward.

Categories use the proposal's own assignments. If the `setpiece` category from wiring-note 3 is
adopted, move the 14 `evt_*` lines to it; nothing else changes.

### Allied Assault (19)

```
waitthread chal_def "obj_whole_section" "campaign" "The Whole Section" "Finish Lighting the Torch with Richards, Wilson, Thomas and Allen all still on their feet" "obj_whole_section" 1 ""
waitthread chal_def "evt_cut_him_down" "campaign" "Cut Him Down" "Free the interrogation-chair prisoner without him taking a single hit" "evt_cut_him_down" 1 ""
waitthread chal_def "evt_monkey_business" "discovery" "Monkey Business" "Destroy Stuka number seven, the one the developers hand-wired" "evt_monkey_business" 1 ""
waitthread chal_def "evt_turd_kind" "discovery" "Close Encounters of the Turd Kind" "Catch the one German who never made it off the latrine" "evt_turd_kind" 1 ""
waitthread chal_def "obj_the_manifest" "discovery" "The Manifest" "Find the Enigma manifest hidden aboard the U-boat" "obj_the_manifest" 1 ""
waitthread chal_def "obj_ghost_ductwork" "discovery" "Ghost in the Ductwork" "Reach the train station without the base ever escalating past its first alert" "obj_ghost_ductwork" 1 ""
waitthread chal_def "obj_dog_green_present" "campaign" "The Whole Beach" "Take the bunker at the top of Omaha with nobody going down from the ramp to the door" "obj_dog_green_present" 1 ""
waitthread chal_def "obj_both_doors" "campaign" "Held Both Doors" "Clear the house and hold both the back and the front without anyone going down" "obj_both_doors" 1 ""
waitthread chal_def "evt_five_shells" "vehicles" "Five Shells" "Finish the Panzer at the crossroads with a Panzerschreck rocket" "evt_five_shells" 1 ""
waitthread chal_def "obj_not_a_scratch" "campaign" "Not a Scratch on Him" "Deliver the downed pilot to the Maquis hideout without him taking a single hit" "obj_not_a_scratch" 1 ""
waitthread chal_def "obj_rode_it_in" "discovery" "Rode It In" "Reach the tank park aboard the German truck without ever being spotted" "obj_rode_it_in" 1 ""
waitthread chal_def "obj_two_more_tigers" "vehicles" "Two More for the Scrapheap" "Find and bomb both hidden King Tigers in the Gestapo motor pool" "obj_two_more_tigers" 1 ""
waitthread chal_def "obj_medic_over" "discovery" "Medic Over" "Trigger the hidden fifth objective and bring the reinforcements all the way through Sniper Town" "obj_medic_over" 1 ""
waitthread chal_def "evt_pole_position" "vehicles" "Pole Position" "Flatten all three telephone poles with the King Tiger" "evt_pole_position" 3 ""
waitthread chal_def "obj_bridge_stands" "campaign" "The Bridge Still Stands" "Finish The Bridge without the bridge going down, theirs or yours" "obj_bridge_stands" 1 ""
waitthread chal_def "obj_no_bells_nordwind" "discovery" "No Bells at Nordwind" "Take the blueprints, the rifle and the stockpile without ever tripping the alarm" "obj_no_bells_nordwind" 1 ""
waitthread chal_def "obj_not_one_ranger" "campaign" "Not One Ranger" "Clear the boxcar sniper duel at Fort Schmerzen without losing a single man" "obj_not_one_ranger" 1 ""
waitthread chal_def "evt_look_the_gas" "discovery" "You Fools, Look the Gas!" "Be there when the scientist's warning stops being a warning" "evt_look_the_gas" 1 ""
waitthread chal_def "obj_unburned" "campaign" "Not a Blister" "Escape the collapsing fort without any player taking a single point of fire damage" "obj_unburned" 1 ""
```

### Spearhead (8)

```
waitthread chal_def "obj_both_boys_home" "fireteam" "Both Boys Home" "Take the Flak 88 town with neither of your riflemen lost" "obj_both_boys_home" 1 ""
waitthread chal_def "obj_four_charges" "campaign" "Four Charges, One Bridge" "Set every charge on the bridge and be back with the Captain before they blow" "obj_four_charges" 1 ""
waitthread chal_def "evt_shabbadoo" "discovery" "Shabbadoo" "Nobody knows what it means. Trip it anyway" "evt_shabbadoo" 1 ""
waitthread chal_def "evt_kalimba_says" "discovery" "Kalimba Says" "Click the thing you were never meant to find" "evt_kalimba_says" 1 ""
waitthread chal_def "evt_six_flushes" "discovery" "Six Flushes" "Flush the outhouse six times and see what comes out" "evt_six_flushes" 1 ""
waitthread chal_def "obj_three_came_back" "fireteam" "Three Came Back" "Get all three of your squad out of the Ardennes alive" "obj_three_came_back" 1 ""
waitthread chal_def "obj_turnabout" "vehicles" "Turnabout" "Destroy the halftrack blocking the Ardennes road" "obj_turnabout" 1 ""
waitthread chal_def "obj_running_on_fumes" "vehicles" "Running on Fumes" "Hold the last bridge without the T-34 ever touching a repair barrel" "obj_running_on_fumes" 1 ""
```

### Breakthrough (15)

```
waitthread chal_def "obj_both_guns_turned" "campaign" "Both Guns Turned" "Seize both Flak 88 batteries above Kasserine Pass" "obj_both_guns_turned" 1 ""
waitthread chal_def "obj_save_the_crab" "vehicles" "Save the Crab" "Bring the minesweeper tank through Bizerte alive" "obj_save_the_crab" 1 ""
waitthread chal_def "obj_sneakers" "discovery" "Sneakers" "Cross the Bizerte patrol ground without ever being seen" "obj_sneakers" 1 ""
waitthread chal_def "obj_every_man_out" "campaign" "Every Man Out" "Break the British prisoners out of the Bizerte jail without losing one" "obj_every_man_out" 1 ""
waitthread chal_def "obj_not_a_single_bell" "discovery" "Not a Single Bell" "Scuttle the freighter and get clear without the ship alarm ever sounding" "obj_not_a_single_bell" 1 ""
waitthread chal_def "evt_they_never_saw_us" "discovery" "They Never Saw Us" "Let the Italian search party finish all four lines at the wrecked glider before you fire" "evt_they_never_saw_us" 1 ""
waitthread chal_def "obj_all_six_home" "fireteam" "All Six Home" "Finish Crete with Hudson, McMartin, Phillips, Johnson, Gobs and Michaels all alive" "obj_all_six_home" 1 ""
waitthread chal_def "obj_let_them_sleep" "discovery" "Let Them Sleep" "Sabotage all four fighters without waking a single sleeping guard" "obj_let_them_sleep" 1 ""
waitthread chal_def "evt_back_of_the_class" "discovery" "Back of the Class" "Find the lesson nobody was supposed to interrupt" "evt_back_of_the_class" 1 ""
waitthread chal_def "obj_nine_tanks" "vehicles" "Nine Tanks, No Ground" "Repel the whole tank assault without one of them crossing the line" "obj_nine_tanks" 1 ""
waitthread chal_def "evt_crunchy_goodness" "vehicles" "Crunchy Goodness" "Kill the tank with the PIAT, the objective they cut but never removed" "evt_crunchy_goodness" 1 ""
waitthread chal_def "obj_all_seven_home" "campaign" "All Seven Home" "Cover the prisoners' escape from Monte Battaglia without losing one" "obj_all_seven_home" 1 ""
waitthread chal_def "obj_nothing_gets_through" "campaign" "Nothing Gets Through" "Destroy the munitions convoy with not one truck escaping" "obj_nothing_gets_through" 1 ""
waitthread chal_def "obj_able_baker_charlie" "campaign" "Able, Baker, Charlie" "Hold all three bunkers below the castle without abandoning one" "obj_able_baker_charlie" 1 ""
waitthread chal_def "evt_seconds_to_spare" "discovery" "Seconds to Spare" "Get clear of the castle with under thirty seconds on the airstrike clock" "evt_seconds_to_spare" 1 ""
```

### Cross-game (4)

```
waitthread chal_def "evt_full_deck" "combat" "The Full Deck" "Face down all eight kinds of reinforcement the Officer can call" "evt_full_deck" 8 ""
waitthread chal_def "evt_not_today_fritz" "combat" "Not Today, Fritz" "Survive a Stuka dive and an artillery barrage on the same map without going down" "evt_not_today_fritz" 1 ""
waitthread chal_def "obj_clean_sweep" "campaign" "Spotless Record" "Complete 5 missions with every primary objective done and nobody going down" "obj_clean_sweep" 5 ""
waitthread chal_def "obj_the_quiet_type" "discovery" "The Quiet Type" "Complete five different missions without ever raising the alarm" "obj_the_quiet_type" 5 ""
```

---

## 7. Pre-flight checklist before any of this is wired

1. **Append only.** `chal_ui_export` publishes by catalogue index; `ui/coop_sr.urc` hard-binds
   `coop_uiB0`..`coop_uiB234`. Inserting mid-list mis-binds the whole disconnected Service Record.
2. **`gen_sr4.py` is not in the repo.** Copy it into `docs/tools/` before adding entries, or the
   disconnected Service Record cannot be regenerated. (Per the user's memory index it is the only
   generator for the 17 page `.tga`s with titles baked in.)
3. **ASCII only.** Four proposal descriptions carry em-dashes - use the cleared text above.
4. **Verify with `docs/tools/depthscan2.py`** after editing `challenges.scr` and every map script.
5. **`obj_crew_intact` is a bugfix, not an addition** - the `cc_king_tiger` re-point in section 2
   changes shipped behaviour and should be confirmed with the user first.
6. **`obj_medic_over` (#14) is still ship-blocked** by the `missioncomplete.scr void` routing on
   the m5l1b hard-skill branch. Unchanged by this audit.
