# Realism pass for the special AI - plan, 2026-10-15

User, verbatim: "Begin work on making the officers/reinforcements/bodyguards and paratroopers behave more
realistically, naturally, authentically, and intelligently. Everything from animations to how they behave."

**Status: PLAN ONLY. Nothing is built, nothing staged, no game was run.** Read-only pass over `officer.scr`,
`parasquad.scr`, `paradrop.scr`, `aisquad.scr`, `morale.scr`, `wounded.scr`, `aivoice.scr`, `ubersound/coop_aivoice.scr`
and `_research/npc_animation_catalog.md` / `npc_anims.csv`. "(inferred)" marks anything I did not read directly.
This extends the approved `docs/proposals/officer_reinforcements_2026-10-14/README.md` (S1..S6 + radio addition);
it does not redo it.

## The one finding that explains most of the "robotic" feel

The project already has a realism stack for ordinary Germans, and it is switched on in `autoexec.cfg`
(`coop_aiDynamic 1`, `coop_aiSquad 1`, `coop_aiSearch 1`, `coop_moraleEnable 1`, `coop_retreatEnable 1`):
squad clustering and shared alerts (`aisquad.scr`), flank/cover movers (`aimaneuver.scr`), morale break
(`morale.scr`), wounded limp/crawl away (`wounded.scr`), officer-death reaction (`officer.scr:3758`). **None of it
reaches the officer's men.** Bodyguards and the wave spawners tag every man `coop_actorStopPainHandler = 1`
(10 sites in `officer.scr`, e.g. line 733), and `aisquad.scr` (lines 126, 167, 232) and `morale.scr` (line 52) skip
exactly that flag; `aimaneuver.scr` probably does too (inferred). So these men have only `coop_wave_hunt`
(`officer.scr:1448`): run at the nearest player, stop at 350/700/900 u, then the engine's attack think. That is the
whole of their intelligence. The approved S2 section brain replaces it; this plan adds what S2 does not cover.

## 1. What players see today

| Group | What it does now | What reads as unrealistic |
|---|---|---|
| **Officer** | Stands where the engine's attack think puts him, STG44, 1 radio; canteen/heal retreats; calls waves (`randomint 8`) | No post, no cover, never behind his men; heals by running off alone; the radio alarm line (`coop_radio_german_reinf1..9`) and the feed line are the only "command" cues |
| **Reinforcements** | Appear in a fan round one point; each man runs separately at a player (`coop_wave_hunt`, 1.5 s tick) | Same entry every time; no leader, no spacing, no bounding, no cover, no reaction to losses; all start moving at the same instant; they ignore the paratroopers (waves are "player-locked", comment at `officer.scr:1453`) |
| **Bodyguards** | 1-4 men, 420 hp, STG44 (`coop_spawn_bodyguard`, `officer.scr:706`). Run to the radio, stand until the officer has contact (poll loop, lines ~750-757), then `attackplayer` | They are not an escort: no formation, no cover, no reaction to the officer being shot, nobody covers his heal retreat; they leave the officer as soon as the engine picks a target. Only link: a guard dying makes the officer call a wave |
| **Paratroopers** | By far the most developed: `parasquad.scr` (3084 lines) wedge-follows, bounds by fire team, base of fire, takes cover, stays pinned 4 s when hit, 6 s of caution on a man down, steps out of players' lines of fire, throws grenades with safety checks, clears rooms, sets up a real .30 cal | Arrival: snapped to the floor at touchdown (`paradrop.scr` ~line 385: `droptofloor`), no landing or look-around, straight into the fight (no landing animation call found - inferred). Medic (`coop_paradrop_medic`, line 906) tends players only, never a hurt trooper (per its header). Voice is one random line from `coop_para_combat` every 12 s (`coop_paradrop_voice_loop`, line 876). Known engine limits from the .30 cal write-up: hands do not follow gun pitch, gunner ignores grenades |

Cross-cutting causes: fixed timers (12 s global bark, 1.5 s hunt tick, 45 s wave cooldown), identical reaction time
for every man, voice from **two** systems at once (the German `coop_german_bark_loop` at `officer.scr:1367` plus the
situational pools in `aivoice.scr`; same for paratroopers) - double lines are likely (inferred), and bug-2324's "way too
common" complaint was exactly this. Sliding feet and snap turns are engine locomotion; script cannot fix them.

## 2. Gaps S1..S6 leave, and what to add

### Bodyguards (new step G1, after S2 because it uses the same posts)
1. **Escort formation.** Posts 120-220 u round the officer, two forward on the player side, rest at his flanks, on
   `parasquad.scr` `post` / `slotPos` / `anchor` (generic; reuse by cross-file call as the officer README does). They
   re-form when he moves, instead of dissolving at first contact.
2. **Cover.** `coverNear` / `lowCoverAt` / `cov` pick low cover; guards crouch behind it and fire over (the wall and
   crate animation families exist for MP40 / StG44, see 3). Never in a doorway, never between the officer and the
   radio path.
3. **Bounding overwatch when he relocates (S5).** One guard fires, one moves (`bound`, `overwatch`, `baseOfFire`), so
   the officer's move reads as covered, not as a jog.
4. **React to the officer being hit.** Hit hard (the S5 15 %-in-5-s rule) -> nearest guard steps onto the line
   between the shooter and the officer and lays suppressing fire; another shouts; heal retreat gets a guard escort
   that falls back with him and holds the post at the med kit.
5. **Wounded guards.** Under ~25 %: fall back to cover rather than stay in the open (reuse `wounded.scr` CRAWL/LIMP
   variants, limited to 1 at a time). **No carrying a wounded man** - no usable animation (section 3).
6. **Believable end.** Officer dead + guard alone + hurt: surrender through the existing `coop_squad_surrender`
   (`officer.scr:5277`, plays `scientist_surrender`); otherwise they fall back with the section (S5 "break").

### Reinforcements (extras on top of S2/S4)
- **Reaction jitter.** Every man waits 0.3-1.6 s (seeded) before his first move and keeps his own 1.2-2.0 s tick:
  kills the "everyone starts at once" look. Zero risk, a few lines in the S2 brain.
- **Engage the paratroopers.** Section men may take the nearest hostile of any side within ~700 u once it has shot
  them (today waves only know players). Needs the allied roster `level.coop_wave_actors` mirrored the other way
  (inferred design; the one-way link is documented in the `coop_wave_hunt` comment).
- **Hurt men break off.** Plumb the wave men into the existing wounded/morale layers through a new flag
  `coop_reinfSquad` that those scripts accept, instead of removing the StopPainHandler flag (which exists for HP
  reasons - do not touch it).

### Paratroopers (steps P1-P3, independent of the officer work)
- **P1 Arrival.** Stagger the sticks' touchdown by a random 0.3-1.2 s, a 1.5-2.5 s crouched landing pause with one
  look-around (`*_stand_alert01/02`, always loaded) before the squad brain takes over; optionally the real
  `PARAland` clip (map-gated, section 3).
- **P2 Voice from events.** `parasquad.scr::ev` (line 82) already names the moments (contact, man down, bound,
  grenade, room clear). Drive the US pools from it: `coop_av_us_attack / cover / backup / mandown / reload / grenade /
  panic / wounded` (counts 6/7/6/5/4/6/17/37 in `coop_aivoice.scr`), rank-gated so only the BAR man calls orders
  (bound = "attack", base of fire = "cover me"). Retire the 12 s random `coop_para_combat` loop behind the switch.
- **P3 Medic treats the squad.** Priority after a downed player: a hurt trooper. Trooper "down" state 20-25 s using
  `rifle_pain_standtoknees -> kneesidle -> flooridle` (always loaded; `bust.scr` / `anim/pain.scr` already use the
  chain), medic kneels with the clip `coop_paradrop_medic` already uses. If no medic lives, the downed man bleeds out.

### Voice for the Germans (step R1)
Pools that exist: `coop_av_de_attack, backup, contact, cover, fallback, grenade, kill, mandown, reload, spot, taunt`
(`ubersound/coop_aivoice.scr`, all maps "m e t"). **No German "wounded" or "panic" pool** (the US set has 37 and 17) -
a gap to fill from existing retail files, not new recordings. Radio: `coop_radio_german_reinf1..9`, `coop_radio_on/off`,
`coop_radio_chatter(_2)` (shortwave), `coop_snd_whistle` (named in the officer README; alias not re-verified). Add:
section leader barks on bound/fall-back, a guard "backup" when the officer is hit, "man down" when a mate dies, and
the radio-can't-reach-officer chatter of the approved addition. Same helper serves guards, sections and paras.

## 3. Animations

**Already loaded on every actor and unused by coop scripts** (grep of `coop_mod/` and `anim/` found no use; names
from `npc_anims.csv`):
- `<w>_stand_shock01..04` (0.7 s flinch beat) and `<w>_stand_alert01/02` (3-4 s look-around): reaction beats for
  "officer hit", "mate dropped", landing.
- `grenade_cower` + `grenade_cower_loop`: a man who cannot get away from a grenade ducks instead of standing.
- `kick_door_left/right/straight` (0.96 s): the room-clear entry in `parasquad.scr::enter`/`clearRoom` and
  Sturmtrupp doors.
- `<w>_standtocrouch_dive`, `<w>_crouchrun_*`, `<w>_injurerun_*`, `scared_run_intro01-03`: cover entry, crouched
  bounds, a hurt man running, a routed section.
- `<w>_butt` (0.6 s melee) for a man a player reaches in close quarters (engine may already do this; unverified).
- Wall and crate cover families (MP40, StG44, Sten full; BAR and Thompson lack blind-fire): **already complete, but
  they only play at authored cover nodes**, which open coop play lacks. The gap is nodes, not animations.

**Map-gated (exist in the paks, load only on certain maps; one alias-override line each makes them global - must be
tested on m, e and t families):** `throw_helmet` (2 s tantrum, officer telegraph before a call; unused by vanilla),
`88officer_coverears` (artillery wave), `den_rifle_fullbody_salute_*` (model-specific), `PARAland`, `11A907_ParaFall`,
`PARAidle`, `AA_para_pain`, `13A302_ParaDeath` (paratrooper arrival, pain, death), `prisoner_1/2/_idle`, `german_hit_*`
(captive poses for surrenders; `scientist_surrender` already works and is used), `A_11_injuredcarryA/B`,
`ALLIEDdrag`, `23A202_Drag`.

**No suitable animation - flagged, do not promise:**
- *Carrying or dragging a wounded man while both stay live AI.* The carry/drag clips are paired cutscene pieces,
  map-gated, scripted-only; the engine has no actor carry. Would need two `anim_scripted` actors origin-stepped
  together (the project's own rule: scripts cannot use `moveto`) - large, fragile. Plan: **fall back and cover
  instead.**
- *Hand signals* (halt, advance, flank): `13A301_ParaWave` is one wave; `point` appears in the shortlist but I did
  not find it in the CSV query - verify before relying on it.
- *A standing German radio operator speaking into a handset:* the radio clips found are seated or desk pieces
  (`chair_radio_*`, `A_34_Commtalk_radio_idle` e3l4, `12C102_RadioIdle` t1l2/t2l1) - verify posture; else voice only.
- *A prone gunner* for actors (already ruled out in the .30 cal write-up), *skid-stop / turn-in-place blends*
  (engine locomotion), *hands following gun pitch* (engine).

## 4. Build order (slots into the approved S1..S6)

Every step ships behind its own cvar, default on, 0 = today's behaviour; staged, run on two maps at 2 players
(`coop_aiScaleTest 1`) in the private harness `G:\mohaa-hudfeed5` using the p3 driver from the .30 cal work; 0 `Script
Error`; project parse scanners clean. One heavy job at a time (quiet-testing preference).

| # | Step | Proof (what a test run must show) | Size |
|---|---|---|---|
| 1 | **S1** entry planner (approved) | `^~^~^ RNF` lines: 5 waves from at least 3 distinct entries, none within 900 u or in line of sight of a player | S |
| 2 | **R1** event-driven German voice + retire the 12 s random loops (`coop_aiVoiceEvents`) | `AIVOICE` debug: every line tagged with an event; no two systems speak within 1 s of each other; no same alias twice in a row; fewer lines per minute than before | S |
| 3 | **S2** section brain (approved) + reaction jitter + engage-paratroopers option + `coop_reinfSquad` hook to wounded/morale | per-man first-move times differ by at least 0.3 s; bounding visible in position tracks; a leader kill produces the 8 s hesitation; with allies present a section fires on a trooper that shot it | L |
| 4 | **G1** guard escort (`coop_guardSmart`) | tracks: guards stay within 220 u of the officer in contact, at least one holds while the other moves when he relocates; hit-officer test: a guard crosses to the shooter line within 3 s | M |
| 5 | **S3** MG42 team (approved) | as in the officer README | L |
| 6 | **S4** sniper pair, dogs, Panzerschreck (approved) | as in the officer README | M |
| 7 | **S5** officer + radio addition (approved) + guard-covered heal retreat + `throw_helmet` tell if section 5 Q5 says yes | heal retreat shows an escort; calls are heard at the set; destroyed radio stops calls | M-L |
| 8 | **R2** wounded and surrender polish for sections and guards | one hurt man withdraws (log + position track); lone guard after officer death surrenders; no stranded "eliminate all" gate (kill count completes) | M |
| 9 | **S6** reserves, seed, battalion from two sides (approved) | as in the officer README | M |
| 10 | **P1** paratrooper arrival (stagger, landing pause, look-around) | touchdown times of a 5-man stick span at least 0.5 s; first squad order at least 1.5 s after the last landing | S |
| 11 | **P2** paratrooper voice from `ev` | event-tagged lines; BAR man only gives orders; no overlap with `aivoice` | S |
| 12 | **P3** medic treats troopers, trooper down state | kill a trooper to 0 hp in the harness: down pose, medic kneels, he rises; no medic: bleeds out; no new aim-at-nothing hangs | M |

P1-P3 and R1 do not depend on the officer steps, so they can fill gaps between the heavy officer steps. Suggested
first build: **S1, then R1 in the same harness session** (voice is the cheapest visible gain and touches no
movement code).

## 5. Open questions (recommended default first)

1. **Give the officer's men the existing global morale/wounded layers, or keep them only on the new section brain?**
   Default: only through the new `coop_reinfSquad` hook, never by dropping `coop_actorStopPainHandler`.
2. **Should reinforcements fight the paratroopers too?** Default: yes, within ~700 u, only after being shot at; players
   keep priority when both are visible.
3. **Cut the random 12 s barks in favour of event lines (fewer lines overall)?** Default: yes (matches the 2026-09-02
   "way too common" complaint).
4. **Medic revives hurt paratroopers, and troopers can bleed out?** Default: yes, 20-25 s bleed-out, only when no
   player is down at the same moment.
5. **Load a few map-gated clips on all maps** (`throw_helmet`, `PARAland`, German salute)? Default: yes for those three,
   tested on m / e / t before shipping; skip the rest.
6. **Guards surrender?** Default: only when the officer is dead and the guard is alone and hurt; the officer never.
7. **Wounded carry?** Default: not built (no animation); fall back and cover instead.
8. **Cap for the extra German voice lines per minute near players?** Default: 1 line per squad every 4 s, 3 per minute
   across the map.

## Candidates for TRAPS.md / OPEN.md (both at their ceilings, not added)
- *Officer men carry `coop_actorStopPainHandler`, which `aisquad.scr`, `morale.scr` and the wounded layer skip: every
  "global" AI feature must be checked for that flag before it is counted as applying to them.*
