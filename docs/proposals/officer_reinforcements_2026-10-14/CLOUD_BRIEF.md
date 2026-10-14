# CLOUD BRIEF - HZM MOHAA Coop Mod, script drafts (written 2026-10-14)

You are working in a cloud copy of the repository `MOHCoopTrilogy/hzm-mohaa-coop-mod`, branch
`coop-wip` (tip `4f8a1019` = public release v1.10.22). This is a co-op mod for Medal of Honor:
Allied Assault running on the OpenMOHAA engine. The files are Morpheus game scripts (`*.scr`),
configs (`*.cfg`), UI (`ui/*.urc`) and assets.

**You cannot run the game here.** There is no engine, no game data, no test harness. Your job is to
write careful FIRST DRAFTS that a local session on the developer's PC will fetch, test and finish.
Write for that reader: small commits, one concern each, and a clear list of what is unproven.

The user is not a programmer. Report in plain language.

## Where your work goes

- Commit to a NEW branch (use the branch the cloud environment gives you, or `cloud/reinf-draft`).
  Never commit to `coop-wip`, never force-push, never open or merge a pull request into `coop-wip`.
- One commit per step (S1, S2 ... and one each for items B and C). The local session will take
  them one at a time, so each commit must leave the mod loadable on its own.
- Put your notes in `_cloud_notes/NOTES.md` on your branch (the local session will not merge that
  folder). For every step: what you wrote, which existing code you copied the recipe from
  (file + label), what you could not verify, and the exact in-game check that would prove it.

## Hard rules

1. Add NO file under `textures/` or `models/`, and change none there. A build gate refuses it
   (it would force every player to re-download 1.3 GB).
2. Do not touch the Omaha maps or anything of theirs: `maps/m3l1a*`, `maps/m3l1b*`, `maps/e3l1*`,
   `maps/e3l2*`, `maps/obj/obj_team3*`.
3. Do not edit `ui/`, `*.tik`, sound aliases' existing rows, or any `.pk3`. Script and cfg only.
   (Adding a new alias row is fine if the design needs it and the sound file already exists.)
4. Everything new sits behind its switch (`coop_reinfSmart`, default off for now). With the switch
   off the mod must behave exactly as v1.10.22 does. No change to existing behaviour by default.
5. **Copy, do not invent.** Before writing any mechanism (spawning AI, turrets, AI orders, sounds,
   weather, hints, triggers), grep `maps/`, `global/`, `coop_mod/` for a place that already does it
   and copy that exact recipe. Name the source in your notes. Only invent when the search is empty,
   and say so.
6. Do not guess engine commands. If a script command or entity field is not used anywhere in this
   repository, treat it as non-existent unless you can show it in the engine source
   (`MOHCoopTrilogy/openmohaa` on GitHub may be stale; say if you relied on it).

## Script language traps (each of these has cost a full debugging session)

- **Parse killers** - any one silently stops the WHOLE file from compiling, and the map then runs
  with no script at all: an em-dash or any non-ASCII character; a bare negative in parentheses such
  as `(-1)` (write `(0 - 1)` or use a variable); a UTF-8 BOM; a label/brace mismatch.
- Brace counts can balance while the file is broken (two opposite errors cancel). Verify with a
  **running-depth scan**: depth never goes negative and is 0 at every column-0 label (internal goto
  labels may sit at depth 1). Write a small Python checker for this as your first act, run it on
  every `.scr` you touch, and paste its output into your notes.
- Files are ASCII with the line endings they already have. Do not reformat or re-indent existing
  code; keep diffs minimal.
- No `waittill pain` - use `waittill damage` or an `events.scr` subscription.
- `wait` / `waitframe` are forbidden in or before `coop_mod/main.scr::main` (the whole init runs in
  one frame). New init hooks called from there must return in the same frame and `thread` anything
  that waits.
- `moveto` / `move` silently do nothing on a `script_model` - step the origin each tick.
- `spawn <class> key "value" ...` with inline key/values is fine (190+ working uses).
- Per-player state lives in `self.flags["coop_*"]`. `$player` is 1-indexed; `$player.size` is the
  connected count. Players can leave mid-loop: check `!= NULL` after every wait.
- The mod runs with `g_gametype 2`. Coop code is gated by `level.gametype != 0`. On a few player-vs-
  player arenas `inCoopMode` is true too - reinforcements must not run there (find how existing
  coop features exclude MP arenas and copy it).
- Cvars read in scripts must be seeded in `coop_mod/cfg/coop_defaults.cfg` (find the file and follow
  its conventions); do not rely on unset cvars.
- Every script file that waits on the coop framework calls
  `waitthread coop_mod/main.scr::waitForMainScript` first.
- Debug prints follow the existing pattern (`level.cMTE_coop_<file>`); add one for the new file.

## The work, in priority order

### A. Officer and reinforcements rework (the main job)

The full audit, the approved design, the build order S1..S6 and the user's answers are in the
second half of this document ("Officer and reinforcements: audit and design"). The coordinator note
at its top records what the user approved, including the radio addition: a destroyable radio, and
after the officer dies ordinary troops keep calling backup (with German radio chatter if an alias
for it already exists in the mod) until the radio is destroyed.

That document refers to local files and tools you do not have (`docs/TRAPS.md`, `.wolf/buglog.json`,
harness copies, G: paths). Ignore those references; everything you need about the existing code is
in this repository, chiefly `coop_mod/officer.scr`, `coop_mod/aihandler.scr`, `coop_mod/events.scr`
and the map scripts.

Build S1, then S2, then S3 and so on, in order. Depth beats breadth: a careful S1-S3 is worth more
than six thin steps. Stop and write up rather than rush the later steps.

### B. Forced sandstorm on the SAS rescue mission

The user's request, verbatim: "in the SAS rescue mission, when you pick up the explosives and the
first coop smoke grenade and the alarm triggers, can we force an extreme sandstorm every time, it
adds to the atmosphere a lot, should continue through end of the mission. After you place the
explosives on the gate door you should get a hint "Tutorial: Sandstorms, Blizzards and
Thunderstorms make visibility more difficult, tread carefully.""

- First identify the map. It is one of the North Africa mission-1 maps (`m1l*`). Find the script
  that has the explosives pickup, the coop smoke-grenade pickup, the alarm and the gate door, and
  say in your notes which map it is and the lines that prove it. If two maps fit, say so and do
  not guess.
- Read `coop_mod/weather.scr` to learn how weather is chosen and how a map or event can force a
  type and intensity. Use the existing forcing mechanism if there is one; if there is none, add the
  smallest possible hook and describe it.
- The storm starts at that moment, every run, and holds until the mission ends (it must survive
  the weather system's own timers and must not carry over to the next map).
- The hint shows once per player, after the explosives are placed on the gate. Copy how existing
  one-time tutorial hints are shown and remembered.
- This item is NOT behind `coop_reinfSmart`; give it its own switch `coop_m1StormForce`, default 1.

### C. "Give all weapons" key does nothing (diagnosis by reading)

In v1.10.22 the developer's key `bind K "append name ,gax"` does nothing on their own listen
server. The path is: the player's name change carries a comma command -> `coop_mod/player.scr`
(the name-command dispatch; `gax` is index 17) -> `coop_mod/developer.scr::give_all_weapons` ->
`global/giveall.scr`. Read that whole path and list every gate that could make it silently do
nothing for the host (dev cvar, host check, admin check, alive/spawned check, a rate limit, a name
length limit, anything recently changed around the name bus). Rank the candidates and say what one
console check would tell them apart. Fix it only if the cause is certain from the code alone.

## Final report

End with: the branch name; the list of commits with one line each; the depth-scan output; what is
unproven; and any question the user must answer. No claims of "works" - nothing here was run.

---

> **COORDINATOR NOTE 2026-10-14 - USER APPROVED THE DESIGN ("I love your design summary. I'd like to roll it out.") - BUILD IT.**
> Open questions: take the recommended answers (MG42 team inside the rifle section; killing the officer breaks the CURRENT attack; Panzerschreck only with a target;
> sniper pair; truck / motorcycle arrivals later, map by map; build order S1 entry first, then S2, S3 MG42 team ...; the officer is not capturable).
> **ADDITION from the user (verbatim):** "I also think that unless the radio does get destroyed, random troops will call in (If we have German radio chatter that plays that would be great)
> after the officer dies (as though they are trying to call back in and can't reach the officer so they are sending in backup)."
> Meaning: the officer's RADIO is a real, destroyable object. While it stands and the officer is dead, a surviving soldier goes to the radio after a delay, tries to raise the officer,
> and calls in backup (a smaller wave through the same entry planner); German radio chatter plays at the set if an existing alias exists (verify each alias on m / e / t maps; no new sound files).
> This can repeat with growing delays until the radio is destroyed (shot / grenade / explosives; give it health and a visible destroyed state using existing models) or no soldier can reach it.
> Destroying the radio ends all further calls - tell the players so through the feed once. With the officer alive the radio is how HE calls waves, so destroying it early cuts him off too.
> Add it to step S5 (officer) / S6 (reserves), behind `coop_reinfSmart` and its own cvar; scale and caps as the other waves; never blocks mission progress.

# Officer and reinforcements: audit and design - 2026-10-14

User, verbatim: "Go ahead and start working on refining all of the reinforcements that the officer calls in, including
the mg squad we never rolled out. I want the officer and all reinforcement types to be smarter, more realistic, more
dynamic, unique, etc." Then, same day: **"Design summary in an artifact first, don't implement anything yet"**.

## HANDOVER (keep current)

- **State: Phase 1 only (audit + design). NOTHING IS BUILT. Nothing is staged. The mod tree and the engine are
  untouched.** `assets/`, `tools/` and `media/` in this folder are empty. No game session was run; every statement
  below comes from reading `coop_mod/officer.scr` (5529 lines, coop-wip `4f8a1019`), `officer_positions.scr`,
  `parasquad.scr`, `parasquad_gun.scr`, `paradrop.scr`, `bunker.scr` notes in the bug log, and the paratrooper write-up
  `docs/proposals/para_30cal_2026-10-12/README.md`.
- **Not read** (so not claimed): `coop_officer_init` body beyond its waits, `coop_officer_medkit_retreat`,
  `coop_apply_personality` past its first screen, `coop_prone_shooter`, `coop_squad_surrender` past its cohort scan,
  `surrender.scr`, `morale.scr`, `wounded.scr`, `director.scr` past its header, `coop_selftest_officer.scr`.
  Read these before building steps S2, S5 and S6.
- **Waiting on the user:** the open questions at the end (also in `design_summary.html`, the page made for the user).
- **Next step when the user says go:** S1 (entry planner), in a staged copy under `assets/coop_mod/`, tested through an
  overlay pk3 in the private harness `G:\mohaa-hudfeed5` (port 12781; runner / driver to copy:
  `docs/proposals/para_30cal_2026-10-12/tools/pass4/p3lib.py`, `p3_sess.py`, `p3_drv.scr`, `scan.py`, `mkgif.py`).
- **How to test (planned, not yet run):** boot a map with an officer anchor (two of m3l2, m4l3, m5l1a, m1l1 - never an
  Omaha map) with `+set developer 1`, `coop_dev 1`, `level.cMTE_coop_officer = 1`; the driver forces first contact and
  the wave type; count `Script Error` (must be 0); read the `^~^~^ RNF` lines the new file prints; one engine
  `screenshot` per step; `coop_aiScaleTest 1` for the 2-player sizes, `coop_officerBasePc` for 3 and 4.
- The mod repo has an uncommitted `coop_defaults.cfg` change that is not from this work. Do not commit it.

---

## 1. What the officer does today

**When he appears.** `officer.scr::coop_officer_policy` sorts every map into `none` (10 maps: rides, cinematics,
Omaha, the sniper duel), `deferred` (6 stealth maps: he waits up to 600 s for `level.alarm`) or `combat` (the rest).
After the settle waits of `coop_officer_init` he is spawned at the map's authored anchor
(`officer_positions.scr`, 53 maps carry `coop_officer_anchor` + `coop_officer_reinf_zone`) with a radio set and 1-4
bodyguards (STG44, 420 hp, leash 2048).

**The man.** STG44, accuracy 70, sight 2400, leash 2048, health scaled to the live players. He is an ordinary
engine actor with `attackplayer`: he stands where the engine's attack think puts him and shoots. He has no post, no
cover order, no position behind his men. Three scripted behaviours sit on top:
- `coop_officer_brain`: under 40 % health and unseen for 8 s he runs to a health post and heals to full (at most
  `coop_officerMaxHeals`, default 2); under 50 % and unseen for 6 s he sips a canteen (at most 3).
- `coop_officer_retreat_monitor`: under 8 % health he runs to the radio.
- `coop_officer_reinforcements`: the wave calls, below.

**When he calls a wave.** First sighting of a player (or first damage); at 75 % and 50 % health; at 30 % the
BATTALION (plus the heal retreat); each time a bodyguard dies; and, 70 % of the time and at most twice, when a squad
is wiped out. Every call passes `coop_call_reinforcements`: a cooldown (`coop_officerWaveCooldown`, default 45 s; the
director scales it), then **`randomint 8`** picks the type, rerolled against the map's `coop_wave_mask`; Stuka and
artillery need a player he can see under open sky, else they become type 1. The radio plays one of nine German alarm
lines, the players get a feed line naming the wave.

**Where waves appear.** One point per map: `coop_officer_reinf_zone` (else 500 u behind him, else 300 u). Men are
fanned 80-360 u round it (`coop_spread_pos`: ground trace, 180 u height limit, line of sight to the anchor). Nothing
tests whether a player can see the point, how near the players are, or whether a path leads from it to them. Only
the sniper and the dogs look for a far `$enemyspawner` / `$alarmspawner`.

**How they move and fight.** Every foot soldier runs `coop_wave_hunt`: every 1.5 s, run toward a point 220 u to one
side of the nearest player until 350 u away (900 for the "cover" personality, 700 for "flank"), then hand over to the
engine's attack think. `coop_apply_personality` rolls aggressive / cover / flanker per man. There is no squad: no
leader, no fire and movement, no shared target, no reaction to losses.

**What ends it.** His death: the "success" sting, his drops, the radio becomes bombable, a replacement-officer
watch starts, some maps spawn "death battalions". Survivors react only if `coop_deathReact` is 1 (default off): 70 %
charge, 30 % fall back. Destroying the radio stops all further waves.

**Scaling.** `coop_reinf_count` (men: authored base is the 2-player size, +/- `coop_officerSquadPer` a player, cap 6,
yields at the AI hard cap), `coop_reinf_scale` (health +/-35 %, accuracy 15 % of the gap a player step), re-matched
live. Cvars: `coop_officerScale`, `coop_officerBasePc`, `coop_officerSquadPer`, `coop_officerBattalionPer`,
`coop_officerHealthPct`, `coop_officerAccPct`, `coop_officerWaveCooldown`, `coop_officerMaxHeals`, `coop_deathReact`;
per map `coop_wave_mask`, `coop_feature_waves / boss / battalion / voice`, `coop_officer_no_airstrikes`,
`coop_officer_waves_at_zone`, `coop_officer_sniper_at_zone`.

### The eight wave types

| # | name in the feed | what it is (2-player size) | weaknesses seen in the code |
|---|---|---|---|
| 0 | Elite Squad | 3 men (cap 6), 100 hp, shotgun x2 / Kar98k / STG44 by dice, 3 grenades, two smoke puffs 10-18 s later **on their own spawn point** | smoke lands where they were, not where they go; same rush as type 1; weapons by dice, so no role |
| 1 | Wehrmacht Squad | 3 men (cap 6), 120 hp, MP40 / Kar98k / STG44 | the baseline rush: straight at the nearest player, stop at 350 u; no leader; nothing distinguishes it from type 0 but the guns |
| 2 | Elite Sniper | 1 man, scoped Kar98k, accuracy 100, sniper model | alone, no spotter; "perch" = farthest spawner or 1200 u behind the officer, height never considered; walks to 1100 u of the nearest player and stays; never displaces; uses `waittill movedone` (hangs when he is hit on the way) |
| 3 | Grenadier Squad | 2 men (cap 6), MP40, 5 grenades + a scripted lob loop | they hunt to 350 u like riflemen, so the grenade men end up in the front rank |
| 4 | Stuka | scripted dive, bombs scattered round a seen outdoor player | fine as an effect; called by dice, not because the players are bunched in the open |
| 5 | Artillery | scripted barrage, same aim rule | same |
| 6 | Anti-Tank Team | Panzerschreck gunner + MP40 loader, 150 hp | called against men on foot, on maps with no vehicle at all; the gunner has no hunt thread; the loader spawns a fixed 50 u east of him |
| 7 | Attack Dogs | 2 dogs (cap 5) + handler (MP40) | dogs spawn before and apart from the handler (fixed +/-128 u offsets); dogs use `waittill movedone`; handler is just another rifleman |
| - | Battalion (30 % health) | a large group at the zone that marches in | not audited beyond its anchor choice |

Common to all: one entry point per map; can appear in view; no path test; no squad behaviour; no retreat; type by
dice; a wave's only link to the officer is the eagle marker.

## 2. The MG squad that was never rolled out

- **Where:** `officer.scr::coop_spawn_mg_team` (line 2860). The file's first lines still list "1 = MG team".
  Nothing calls it. Its header says: *"DEPRECATED (scrapped) - floated the gunner and never fired"*. Type 1 was
  replaced by the Wehrmacht Squad.
- **What it does:** spawns `models/statweapons/mg42_gun.tik` at the wave point, turns it toward the nearest player,
  spawns a gunner with the engine's `machinegunner` think and `turret <gun>`, plus one MP40 "spotter" who hunts.
- **Why it failed (from the code and the bug log):**
  1. *Never fired* - same cause as bug-1572 (the build-mode nest): a mounted gunner holds the gun but nothing drives
     it. Every working nest in the game threads `global/mg42_active.scr::mg42` on the gun, with the
     `<gun>` / `<gun>_gunner` targetname pair. This spawner never did.
  2. *Floated* - the gun is a bare tripod-less model dropped onto a spread point: no rest under it, no test of the
     ground, no seat for the gunner. The engine snaps the gunner to the gun wherever it is.
  3. It appeared, complete, at the reinforcement point: no carry, no set-up, no choice of ground, no line to the
     players, no pack-up. A static nest that pops in is not a team.
- **What is missing, and now exists elsewhere:** all of it was built for the friendly paratroopers' .30 cal
  (`parasquad.scr`, 1900 lines of it; `para_30cal_2026-10-12/README.md` passes 2-4): site planner on real cover or a
  sandbag rest (`mgPlan`, `mgTry`, `mgSite`), path-tested walk-up (`mgReach`, `mgWalk`), set-down (`mgSetup`), a
  gunner who fires bursts and stops before the barrel cooks (`mgHold`, engine keys `coopammo`, `coopaibelt`,
  `coopheatrates`, getters `.coopammo` / `.coopheat` through `parasquad_gun.scr`), belt change, grenade flight and
  return (`nadeWatch`, `mgFlee`), pack-up and re-site (`mgPackup`), the gun left behind for the players with its belt
  (`mgLeft`, `mgRest`). What it lacks is a **side switch**: its enemy is "the Germans", its friends are the players.

## 3. Design

Guiding picture: a German platoon leader with a radio, a small escort, and sections he commits one at a time. Each
section is built for one job, arrives from a direction the players cannot see, moves as a group, and stops being a
threat when its job is taken away. Kill the leader and the attack comes apart.

### 3.0 Shape of the code

- One new file, **`coop_mod/reinf.scr`**. `officer.scr` keeps every spawner and gets a few gated hooks. A new file
  cannot break the 5529-line one, and with **`coop_reinfSmart 0`** every hook is skipped: today's behaviour, exactly.
- Count and stats stay with `coop_reinf_count` / `coop_reinf_scale` (the one authority for officer content); XP class,
  wave roster, feed keys, `coop_wave_mask` and the "Full Deck" challenge (8 types) are unchanged. **No ninth type.**
- Reused as they are, by cross-file call: `parasquad.scr::cov`, `lowCoverAt`, `tight`, `coverNear`, `flatDist`,
  `lineTo` (generic, no squad table), `officer.scr::coop_find_ground`, `coop_spread_pos`, the scout path probe of
  `paradrop.scr::coop_para_lz`, the tether post of `parasquad.scr::post`.
- Germans hold at their leash when the enemy is beyond `maxdist` (the engine's own branch; the write-up notes it is
  German-only), so a tethered post holds a German better than it holds a paratrooper.

### 3.1 Entry: where a wave comes from (S1)

`reinf.scr::entry` returns the point a wave forms up on. Candidates: the authored zone, every `$enemyspawner` /
`$alarmspawner` origin, and a ring of 12 points at 1000-1800 u round the players' centre. A candidate passes when:
ground under it (`coop_find_ground`); room for a man; **no living player has a line to it** (solid-world trace from
each player's eye to head height, as `coop_para_lzSeen`) and none is within 900 u; **a path leads from it to the
players** (hidden scout actor: `runto` + `pathdist` after 0.3 s, accepted under 3x the straight distance + 600);
not within 300 u of an objective item or trigger the map lists (`level.coop_reinf_keepout`, optional per map).
Among the passing candidates one is drawn with a seeded roll, weighted away from the direction of the last wave.
None passes = the authored zone, as today. Cost: one hidden actor for about 4 s, at most 14 probes a call.
Maps with `coop_officer_waves_at_zone 1` keep their zone (they set it because free search went off-map).

### 3.2 The section brain (S2)

`reinf.scr::section` - one thread per wave, 0.5 s tick, replacing `coop_wave_hunt` for its men.
- **Posts.** Every man is tethered to a post the brain moves (leash 170-240 u). No more per-man rush.
- **Leader.** Slot 0 (the MP40) is the Unteroffizier. Alive: the section bounds. Dead: 8 s of hesitation (everyone
  to cover, nobody moves up), then the next man leads and bounds get shorter.
- **Approach.** Out of contact: two teams, alternate bounds of up to 400 u along the path toward the players.
- **Contact** (a man has an enemy, or one was hit): one team is the base of fire (`suppresschance 100`), the other
  bounds at most 300 u to cover found by `coverNear` (low cover first, a corner second, never a doorway).
- **Stand-off by type** - the section stops where its job is done (table below), not at 350 u for everyone.
- **Losses.** At half strength the section stops advancing and holds cover. At one man left, or when the officer
  dies, he falls back to the entry point or surrenders through the existing `coop_squad_surrender`.
- **Never** `waittill movedone` (poll + re-issue, as the file's own note demands); no man is left with a dead brain:
  if the section thread ends, each man gets `coop_wave_hunt` back.

### 3.3 The types

| # | becomes | who | arrives | fights | beaten by |
|---|---|---|---|---|---|
| 1 | **Schuetzengruppe** (rifle section) | NCO MP40, riflemen Kar98k, one STG44; on open ground one man in three carries the **MG42** (3.4) | on foot from the entry point | bounds cover to cover to 600-800 u and holds; the patient one | flanking the base-of-fire team; killing the NCO |
| 0 | **Sturmtrupp** (assault group) | MP40 / STG44 / one shotgun, 3 grenades each | from a second entry point 60-120 degrees off the last wave | smoke **between** itself and the players, then a path-tested flank route (a waypoint 500 u to the side, scout-probed) to 200 u; grenades first indoors | holding the corner the smoke hides; it has no long guns |
| 3 | **Grenadiere** | 2-6, MP40 + grenades | with or behind another section if one is alive | stop at 500-700 u **behind cover**, lob over it (existing lob loop), move 150 u after three lobs | closing the distance: weak inside 300 u |
| 2 | **Scharfschuetzen** (sniper pair) | sniper + spotter (MP40) | far entry; perch = the candidate with a line to the players at 1400-2600 u, highest first | one shot cycle, then both move to another perch after 25-40 s of contact or any hit; the spotter guards the approach | the glint of the perch change; rushing the spotter |
| 6 | **Panzerschreck-Trupp** | gunner + loader | on foot | **only called against a vehicle, a manned gun or players in a building**: one rocket at the wall / gun, relocate; else the type is not offered | the reload: the loader must be next to him |
| 7 | **Hundefuehrer** | handler + 2-5 dogs | all together at the entry point, the handler leading | dogs heel on the handler until 900 u or first sight, then he lets them go; he follows as a rifleman; dogs go for the most isolated player | killing the handler early: the dogs lose direction for a few seconds |
| 4 | **Stuka** | - | - | unchanged effect; **offered only when two or more players (or the one solo player) have stood within 400 u of each other under open sky for 10 s** | spreading out, going indoors |
| 5 | **Artillerie** | - | - | same rule; preferred over the Stuka when the players have not moved for 20 s (a held position) | moving |
| - | **Battalion** | as today | from two entry points instead of one | each half runs the section brain | - |

### 3.4 The MG42 team (S3 - the piece that was never rolled out)

Part of the rifle section (historically the German section is built round its MG), not a type of its own.
- **Who:** gunner (carries the gun, pistol-armed while moving if the model allows, else Kar98k), assistant (ammo,
  MP40, takes the gun over when the gunner dies), the section's riflemen as its guard.
- **Carry:** the gun on the gunner's back / at the trail (`models/weapons/mg42portable*` models are already in the
  paks; which reads best is a harness look - no new model).
- **Site:** `parasquad.scr`'s planner with a side switch: real cover it can rest the bipod on (a wall top or sill
  25-66 u high) overlooking the players at 600-1400 u, else flat open ground on the bipod; never in a doorway, never
  where a squad mate stands in front of it. Path-tested before he walks.
- **Fire:** bursts, stops before the barrel cooks, belt of 250 and one spare (`coopammo`, `coopaibelt`,
  `coopheatrates`); it suppresses the players' cover so the other team can bound. Sound and tracer are the MG42's own.
- **Relocate:** when a player gets within 60 degrees of its flank inside 500 u, when a grenade lands within 300 u
  (the team runs, waits, comes back), or when it has had no target for 20 s - pack up, new site.
- **Capture:** gunner and assistant dead = the gun stays where it is with what is left on its belt, tips back on its
  butt, and any player can use it (the left-behind-gun rules of the .30 cal: `mgLeft`, `mgRest`).
- **Not on:** indoor entry points, maps with `coop_feature_mg 0` (per map), `coop_reinfMg 0`.
- **The work:** a side switch through about 1900 lines of `parasquad.scr` (who is the enemy, who must not be in front
  of the muzzle, which gun / bipod / prop models, German instead of American voice). The largest single step.
  Alternative considered and rejected: the build-mode recipe (`bunker.scr::mg_nest_manned` + `mg42_active.scr`) - it
  fires, but it is a nest that appears, which is what was scrapped.

### 3.5 The officer (S5)

- **Command post.** He takes cover (`coverNear`) 150-300 u behind where his escort stands, out of the players'
  line; his escort is tethered round him (two forward, the rest at his side). He fights from there.
- **Orders.** On each call: the whistle (`coop_snd_whistle`, exists) once, then the radio line (exists, nine
  variants). To build: verify each alias plays on m / e / t maps; no new sound.
- **Choosing the wave** (`reinf.scr::pick`, replaces `randomint 8`, still inside the map's mask):
  players bunched in the open -> Stuka / artillery / MG section; in a building -> Sturmtrupp, grenadiers,
  Panzerschreck; spread out -> dogs or Sturmtrupp at the most isolated player; holding at long range -> snipers;
  nothing fits -> rifle section. No type twice in a row; the roll is seeded per session and logged.
- **Relocate.** A player within 600 u with a line to him, or 15 % health lost in 5 s: he moves to the next cover
  toward the radio, escort covering. This replaces the 8 % dash.
- **Escort gone.** He stops fighting, withdraws to the radio (the existing, currently unused
  `coop_reinf_retreat_and_wave`) and calls from there. Catch him on the way and the call does not happen.
- **His death breaks the attack.** `coop_deathReact` behaviour becomes the rule under `coop_reinfSmart`: every
  section loses its leader bonus; sections at half strength or less surrender (existing system); the others fall
  back to their entry points and hold there. Death battalions stay as the maps set them.
- Unchanged: health scaling, heals and their cap, the radio objective, the replacement officer, music, XP.

### 3.6 Variation and reserves (S6)

Seed = map name + session start time. It decides: entry points, which variant a type takes (MG or not, sniper perch),
the flank side. **Reserves:** the officer holds one call back; it is spent on what the players do - a player alone
400 u from the others for 15 s (dogs / Sturmtrupp at him), the squad dug into sandbags (grenadiers, artillery), a
captured MG42 turned on his men (snipers, Panzerschreck). Truck or motorcycle arrivals need a per-map road path and
are **not** in this round (see the questions).

### 3.7 Cvars (all seeded in `coop_defaults.cfg`)

| cvar | default | meaning |
|---|---|---|
| `coop_reinfSmart` | 1 | master switch; 0 = everything as released today |
| `coop_reinfEntry` | 1 | entry planner (0 = authored zone only) |
| `coop_reinfMg` | 1 | MG42 team in the rifle section |
| `coop_reinfMgChance` | 50 | percent of eligible rifle sections that bring it |
| `coop_reinfBreak` | 1 | the attack breaks when the officer dies |
| `coop_reinfDebug` | 0 | `^~^~^ RNF` lines |

### 3.8 Cost

Actor counts per wave do not change (`coop_reinf_count` stays the authority; the MG team and the spotter come out of
the section's count, the sniper pair is 2 instead of 1). New: one thread per section at 2 Hz; a cover search is up
to about 150 traces spread over waits; one hidden scout actor for about 4 s per call; one squad-table scan for
grenades per MG team. To be measured in the harness with the server frame time the project already logs.

### 3.9 What it will not do

Spawn in a player's view or within 900 u; spawn off the path network; stand on or block an objective item, a door
the map scripts, or a ladder; touch Omaha maps (no officer there today, none added); add a file under `textures/`
or `models/` (no new download); change the eight wave types, their feed keys, the mask or the challenges; change
anything when `coop_reinfSmart` is 0.

## 4. Build order

Each step is staged, tested on two maps at 1-player and scaled sizes, then committed alone.

| step | what the player sees | size |
|---|---|---|
| S1 | waves come from different, unseen, reachable directions | small (about 250 lines, 1 hook) |
| S2 | rifle section, Sturmtrupp, grenadiers move and fight as groups, each with its own distance | large |
| S3 | the MG42 team: carry, site, fire, relocate, capture | largest (side switch in `parasquad.scr`) |
| S4 | sniper pair with perches; dogs with their handler; Panzerschreck only where it has a target | medium |
| S5 | the officer: post behind his men, whistle, choice of wave, relocation, withdrawal, the break on his death | medium-large |
| S6 | reserves and the per-session seed; battalion from two sides | medium |

## 5. Open questions for the user (recommendation first)

1. **MG42 team inside the rifle section, or a ninth wave type of its own?** Recommended: inside the section (no
   change to the mask, the feed, the "Full Deck" challenge).
2. **His death breaks the attack - on by default?** Recommended: yes (today survivors carry on as if nothing
   happened unless `coop_deathReact 1`).
3. **Panzerschreck only when there is something to shoot at** (vehicle, manned gun, players in a building)?
   Recommended: yes; on most maps it will then be rare.
4. **Sniper becomes a pair** (2 actors instead of 1)? Recommended: yes.
5. **Truck / motorcycle arrivals:** recommended later, map by map (each needs a road path placed and looked at in
   game); say which maps matter most.
6. **Order:** S1, S2, S3 as listed, or the MG42 team first? Recommended: S1 first (small, and every later step
   stands on it), then S3 if the MG is what the user wants to see soonest.
7. **Captured officer?** The surrender system refuses him on purpose (2026-08-20: "the officer never surrenders").
   Recommended: keep that.

## Candidates for TRAPS.md / OPEN.md (both at their ceilings - not added)

- *A turret gunner needs `global/mg42_active.scr::mg42` threaded on the gun (targetnames `<gun>` / `<gun>_gunner`)
  or he holds it and never fires (bug-1572) - the cause of the scrapped officer MG team as well.*
- *`officer.scr` picks the wave type with `randomint 8`; `coop_wave_hunt` is the only movement logic of every wave.*
