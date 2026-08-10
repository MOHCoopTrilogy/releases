# The unwired challenges — feasibility triage

**2026-08-08.** Companion to bug-1596. These are `chal_def` rows that ship in the Service Record
with no producer for their stat, so no player can complete them. This document is the
wire-these / cut-these split, run with the same three filters used on the 2026-08-08 picked batch:

1. does the entity or variable **exist**,
2. is it **player-influenced** or decided by a cutscene,
3. does it **hold the value the feat assumes** at the moment it would be read.

Filters 1 and 2 are done below and cite a file and line. **Filter 3 is per-entry and is NOT done
here** — it is the one that killed `Coastal Clean Sweep` (a live respawn gauge read as a total) and
`Cut the Hand Short` (a counter that resets inside its own thread), and it has to be run against the
specific line at wiring time.

> **Read this before trusting the first pass.** An earlier probe searched only each map's main
> `.scr` and reported "NONE" for eight entries. The BT/SH maps keep most of their logic in
> `maps/<map>/` sub-scripts, so those were false negatives — and separately, I had assigned the
> **wrong map** to eight challenges. Search `maps/`, `maps/<map>/` and `gags/` together, and never
> assume the map from the description alone.


> **Counts corrected 2026-08-08 (bug-1601).** The original figure of 49/47 was inflated: the
> checker globbed `maps/*.scr`, which does not match `maps/<map>/*.scr`, so three already-wired
> challenges (`cc_static_line`, `cc_desert_fox`, `cc_enemy_mine`) were counted as dead. True
> starting point was **46**. 21 were wired on 2026-08-08, leaving **25**. Any cross-reference
> scan of this repo must walk the tree, never glob one level.

---

## A — Verified: the hook exists, wire it (26)

The named entity or variable is present and player-influenced. Each needs one hook in its own map
script, most of them one line in the existing mission-complete block.

| Challenge | Map | Anchor |
|---|---|---|
| Shabbadoo | t1l3 | `shabbadoo:` label `t1l3.scr:488`, `level.shabbadoo`, `$enemyspawnertrigger[].shabbadoo` |
| Kalimba Says | t1l3 | `t1l3.scr:510` -> `gags/t1l3_misc.scr::kalimbasays` |
| Close Encounters of the Turd Kind | t2l1 | `$outhouse_dude` spawned at `t2l1.scr:898` ("Now, spawn the OUTHOUSE DUDE!") |
| Monkey Business | m1l3b | `$stuka7 thread monkey_stuka_setup` `m1l3b.scr:100` — hand-wired, exactly as described |
| Autoblinda Down | **e2l1** | `$AB41`, `maps/e2l1/ab41_scene.scr`, `level.ab41ready` |
| Save the Crab | **e1l2** | `maps/e1l2/Crab.scr::InitCrab` / `ObjectiveGuardCrab`, `level.crabdead` |
| They Never Saw Us | e2l1 | `$searchparty` + **our own** `coop_searchPartyShotWatch` (bug-1344) already detects the first shot |
| Nine Tanks, No Ground | **e2l1** | `maps/e2l1/FinalBattle.scr::StartTankBattle` |
| Sneakers | **e1l3** | `maps/e1l3/Sneakers.scr::ShadowThread` |
| Let Them Sleep | **e1l3** | `self.asleep` in `maps/e1l3/Briefing.scr:822` |
| Crunchy Goodness | **e3l1** | `level.objPIAT`; `e3l1.scr:159` literally reads *"no longer an objective, but still full of crunchy goodness"* |
| Seconds to Spare | **e3l2** | `Air_Strike_Explode_Start` `e3l2.scr:432` |
| The Manifest | m2l2b | `m2l2b.scr:596` `"Manifest stolen"`, `enigmamedal` |
| The Bridge Still Stands | m5l3 | `level.flags[Bridge_Is_Gone]` `m5l3.scr:106` |
| Pole Position | m5l2a | `pole1:` label `m5l2a.scr:450` |
| Two More for the Scrapheap | m4l3 | `level.tank1_bomb_planted` `m4l3.scr:476` |
| Not a Scratch on Him | m4l1 | `level.pilot.health` `m4l1.scr:135` |
| Running on Fumes | t3l2 | four T-34 repair-barrel triggers, `t3l2.scr:1640+` |
| Both Boys Home | t1l2 | `level.friendly1` / `friendly2` `t1l2.scr:41-44` |
| All Six Home | e2l1 | all six named: `$leroy.targetname="hudson"`, McMartin, Phillips, Johnson, Gobs, `$michaels` |
| Static Line Savior | e2l1 | McMartin, the paratrooper on the pole `e2l1.scr:189` |
| Both Guns Turned | e1l1 | `maps/e1l1/scene3.scr::InitFlak88s` |
| The Whole Section | m1l1 | Richards / Wilson / Thomas / Allen all have KIA messages `m1l1.scr:463-472` |
| Not One Ranger | m6l3a | boxcar + ranger assault scene, `m6l3a.scr:206/228` |
| Not a Single Bell | e1l4 | freighter + `"Scuttled"` autosave `e1l4.scr:166`, `maps/e1l4/PreShip.scr` |
| All Seven Home | **e3l4** | Monte Battaglia. **Caveat:** e3l4 has the open bug-1471 spawner defect — verify the map runs correctly first |

## B — Mod-native, feasible by construction (3)

We own the code, so the only question is where to put the bump.

| Challenge | Where |
|---|---|
| Spotless Record | cross-map: `coop_wentDownMap` + objective completion, both already tracked |
| Not Today, Fritz | `coop_stuka_attack` `officer.scr:1504` + the artillery warning; both ours |
| The Full Deck | officer wave types 0-7 exist; the variable name still needs locating in `officer.scr` |

## C — Needs real investigation before wiring (14)

The map exists and the feat is plausible, but the specific state it reads was **not found** by the
probe. Each needs someone to open the map and decide whether to wire it, restate it, or cut it.
Do **not** wire these from the description.

Ghost in the Ductwork (m2l3 — no alert-level variable found) · The Whole Beach (m3l1a — no door
flag) · Held Both Doors (m3l2 — no front/back door state) · Five Shells (m4l1 — no crossroads or
Panzerschreck-kill tracking) · Rode It In (m4l2 — no "spotted" state) · Not a Blister (m6l3d — no
fire-damage tracking; would need a means-of-death check, engine-side) · Three Came Back (t2l2 — no
friendly/squad entities at all) · Turnabout (t2l2 — halftracks exist, the blocking one does not
resolve) · Every Man Out (e1l4 — no prisoner entities found) · Able, Baker, Charlie (e3l3 — "Baker,
this is King 6" is radio dialogue, not a three-bunker hold) · Nothing Gets Through (e1l2 — the map
has a munitions **depot** and a **friendly** tank convoy; the description looks wrong) · Chasing the
Fox (e1l1 — a panzer exists, the "duel" framing does not) · Cut Him Down (m1l2a — chair and prisoner
exist in quantity, the "without a single hit" state does not) · Medic Over (m5l1a — see below, likely a cut)

## D — Cut: the thing the challenge describes does not exist (4)

| Challenge | Why |
|---|---|
| Back of the Class | Zero hits for classroom / blackboard / lesson / lecture across all 608 script files |
| No Bells at Nordwind | No alarm or bell on any Nordwind map (m6l1a is 164 lines and has neither) |
| The Quiet Type | "Five missions without raising the alarm" needs a cross-map alarm concept. `level.alarmactive` exists on **exactly one map**, m6l2a |
| Medic Over | No hidden fifth objective anywhere in the trilogy; no reinforcement or medic state on m5l1a |

---

## What this says about the batch

**It is mostly real.** 26 verified plus 3 mod-native is 29 of 47 wireable, against 4 outright dead.
Whoever wrote these knew the scripts, not just the campaign: *Shabbadoo* and *Kalimba Says* are
internal label names, *Monkey Business* is `monkey_stuka_setup`, and *Crunchy Goodness* is quoting a
developer comment. The failure was never the ideas — it was that 50 definitions landed and none of
the hooks did.

**The 14 in group C are where the remaining risk is**, and they are the ones most likely to have
been written from a walkthrough rather than from the map. Treat each as a fresh feasibility
question, not as work already scoped.
