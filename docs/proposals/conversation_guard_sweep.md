# Conversation guard sweep - scripted dialogue that outlives its speakers

Read-only audit. Nothing was edited. Companion machine-readable file:
`docs/proposals/conversation_guard_sites.json` (196 objects, `{file, line, actors, problem, recommended, risk, note}`).

Reference fix this mirrors: `hzm-mohaa-coop-mod/maps/m3l1b.scr:1061` (`coop_bunkerConvOk`) and its
three call sites at `m3l1b.scr:1078`, `:1091`, `:1106`.

## Scan provenance

| | count |
|---|---:|
| map scripts swept (`maps/*.scr`, all of them) | **121** |
| global scripts swept (`global/*.scr`, all of them) | **68** |
| `say` / `playsound` / `waittill saydone` / `waittill sounddone` call sites examined in `maps/` | **461** |
| ...same in `global/` | **74** |
| of those, actor-dialogue sites (`say`, `say_wait`, `waittill saydone/sounddone` attached to a speaker) | **262** in maps, **3** in global |
| map files that contain any actor dialogue at all | **14** |
| findings recorded | **196** (148 safe to guard, 48 DO-NOT-GUARD) |

The other ~270 sites are prop and SFX `playsound` with no speaker at all: doors, vehicles
(`global/vehicles_thinkers.scr`, `autotruck.scr`, `autotank.scr`, `autoplane.scr`), exploders,
searchlights, shutters, weather, ambience. They cannot "keep talking after the speaker is dead"
because they have no speaker. They are out of scope and are not listed.

`m3l1b.scr` was excluded as instructed.

Maps with **zero** actor-dialogue sites (their hits were all prop/SFX playsound), confirmed by
opening each: `t1l1`, `t2l3`, `t2l4`, `e1l1`, `e2l1`, `e2l2`, `e3l2`, `e3l3`, `m2l2b`, `m2l2c`,
`m5l3`, `m6l1a`, `M6L1b`, `m6l3b`, `M5L2A`.

## The shared-helper question, answered first

**There is no mod-wide conversation helper today.** I looked before enumerating, as instructed.

- `global/say_to.scr` is the only shared dialogue routine, and it is called by exactly **one**
  map (`m3l2.scr`, 8 call sites). It checks `self == NULL` at `say_to.scr:6` but never checks
  `isalive` or `thinkstate`, and its `waittill saydone` at `say_to.scr:63` is unprotected. Worth
  fixing, but it is not the lever.
- `coop_mod/replace.scr::say_wait` (`:1100`) and `::playsound_wait` (`:1042`) are the coop
  compatibility shims that make `saydone`/`sounddone` fire at all in MP. They are plumbing, not
  policy - they deliberately do not decide whether a line should play.

So the highest-value action is to **create** the shared helper, then point the per-map sites at
it. One new label in `coop_mod/replace.scr` covers every finding below:

```
//=========================================================================
//Returns 1 only when every actor passed in is present, alive and unalerted.
//Second actor is optional. NIL and NULL are different values in this dialect,
//so both legs are tested. Mirrors coop_bunkerConvOk in maps/m3l1b.scr:1061.
//=========================================================================
convOk local.a local.b:{
	if( local.a == NIL || local.a == NULL ){ end 0 }
	if( !isalive local.a ){ end 0 }
	if( local.a.thinkstate != idle ){ end 0 }
	if( local.b != NIL && local.b != NULL ){
		if( !isalive local.b ){ end 0 }
		if( local.b.thinkstate != idle ){ end 0 }
	}
	end 1
}end
```

Call it inline, which this dialect allows (`!waitthread` is used in 8 files, e.g.
`coop_mod/aihandler.scr:23`):

```
if( !waitthread coop_mod/replace.scr::convOk $speakerA $speakerB ){ end }
```

ASCII only, no em-dash, no bare negative in a vector literal, braces and labels balanced.

### The three problems, and which fix each one takes

1. **Unguarded `say` / `playsound`.** Fix: `convOk` above the line.
2. **`thinkstate == idle` does not cover dead, and reading `.thinkstate` off a removed actor is
   reading off NULL.** Fix: the NULL leg and the `isalive` leg must both come *before* the
   thinkstate leg, in that order, as in `m3l1b.scr:1062-1065`.
3. **`waittill saydone` / `waittill sounddone` strands the thread.** This is the one that does
   real damage, and it needs a *different* fix from problems 1 and 2. Skipping the say is often
   wrong; skipping the *wait* almost never is. For any scene that gates progression, guard the
   wait and leave the say alone. `coop_mod/replace.scr::playsound_wait_helper_temp` (`:1082`) is
   the project's existing mechanism for force-resuming a suspended thread and is the right tool
   when a hard timeout is needed instead of a skip.

---

# Tier 1 - guard is clearly right, and a coop squad will hit these

Ranked by how likely four players actually walk in and start shooting mid-scene.

## 1. `maps/M1L3c.scr` - `germantalkers`, lines 379-477 - WORST SITE IN THE MOD

Sixteen dialogue lines and sixteen `waittill saydone` calls, **zero guards of any kind**.
Two German actors, `$talker1` and `$talker2`, chatting in the radio room.

Sites: say at `M1L3c.scr:384, 390, 396, 402, 408, 414, 420, 426, 432, 438, 444, 450, 456, 462,
468, 474`; matching `waittill saydone` at `:385, 391, 397, 403, 409, 415, 421, 427, 433, 439,
445, 451, 457, 463, 469, 475`.

Why it matters: this is a room players enter and clear. The label is fired by a BSP trigger
(`setthread germantalkers`, confirmed at `_research/cov_manifests.json:3894`), it is a dead-end
label, and **nothing in the file waits on it** - I grepped the whole mod, the only source
reference is the definition at `M1L3c.scr:379`. So it is live, it is interruptible, and
guarding it cannot break anything downstream. Best value-to-risk ratio in the sweep.

Fix: one `convOk` call at the top of the label plus one before each say, exactly as
`m3l1b.scr:1078` does it.

```
germantalkers:
	if( !waitthread coop_mod/replace.scr::convOk $talker1 $talker2 ){ end }
	$talker1 thread coop_mod/replace.scr::say_wait "den_m6l1_614r" "idle"
	$talker1 waittill saydone
	wait .1
	if( !waitthread coop_mod/replace.scr::convOk $talker1 $talker2 ){ end }
	...
```

Aside, not a coop bug: lines `:438, 450, 462, 474` use `$talker1` for aliases ending in `b`,
which are `$talker2`'s voice. Retail shipped it that way (the commented-out originals above each
line say the same). Out of scope, noted so nobody "fixes" it by accident.

## 2. `maps/m6l1c.scr` - two per-map helpers covering 27 lines

`sciencesayto` (`:520-530`) and `soldiersayto` (`:566-576`) are already the right shape - fixing
those two labels fixes every line they serve. This is the second-best leverage in the sweep.

- **`m6l1c.scr:529` is a guaranteed strander.** `local.talker waittill animdone` sits *outside*
  the guard at `:522`. If the talker is dead or attacking, no anim was ever started, so this
  waits forever and the whole `sciencechatsequence` (`:483-511`, 11 lines) dies with it -
  including the `type_disguise "salute"` restore at `:515-516`.
- `m6l1c.scr:522, 526` - `isalive` plus `thinkstate != "attack"` only. No NULL leg, and any
  alerted-but-not-yet-attacking state still talks.
- `m6l1c.scr:493, 498, 502` - `.thinkstate` read off `level.soldier4` / `level.scientist1` with
  no NULL check.
- `m6l1c.scr:568` - same partial guard for `soldiersayto`, which serves 16 lines at `:542-557`.
- `m6l1c.scr:573` - `if(local.listener)` is a truthiness test, not `isalive`.

Safe to guard: `soldierchatsequence` grants its objective at `m6l1c.scr:536-537` *before* the
chat starts, and sets `type_disguise "salute"` at `:560-561` *after*. Guarding per line lets each
`waitthread` return immediately, so the sequence still runs to the end and the disguise state is
still restored. Nothing is skipped.

Do **not** guard `m6l1c.scr:783` and `:806` (`den_alarm_01c`) - that is the alarm being raised.

## 3. `maps/m2l2a.scr` - partial guards everywhere, one typo

The best-hardened map in the set (Smithy did a pass), which is exactly why the gaps stand out.

- **`m2l2a.scr:493-498`** - `guytalk`. `$guy3`'s own lines at `:483-492` are wrapped in
  `if(isalive self)`; `$guy2` and `$guy1`'s lines at `:493-498` are not. These two are told to
  `attackplayer` at `m2l2a.scr:465-466`, so players are shooting at them at that exact moment.
  Textbook partial guard.
- **`m2l2a.scr:738-757`** - `norgirls`. Ten say lines and ten `waittill saydone`, with the
  `isalive` checks done **once** at `:730` and `:732` before the volley begins. Corridor scene
  the squad walks straight into. Highest interruption probability in this map.
- **`m2l2a.scr:819-822`** - `whatsuptalk`. `isalive` on both parties, no `thinkstate`. Alerted
  guards keep discussing the submarine. Helper covers 6 lines at `:793-798`.
- **`m2l2a.scr:853-870`** - `sciencetalk`. No `isalive self` at all; only an alarm test at `:841`
  and a `level.scienceinterupt == 2` bail between lines.
- **`m2l2a.scr:680`** - `likeynorwaytalk`. Already `isalive` plus `thinkstate == "idle"`. Only
  the NULL leg is missing. This is the closest thing in the mod to a correct guard already.
- **`m2l2a.scr:813` - latent bug, unrelated to guards but found in the same block.**
  `if(isalive level.whatsthesube)` has a trailing `e`. That variable is never assigned anywhere,
  so `level.whatsthesub type_disguise "salute"` at `:814` never fires. Compare `:815`, which
  spells it correctly.

Do **not** guard `m2l2a.scr:531, 535, 549` - those are the base PA/intercom, prop emitters with
no thinkstate, and a public-address system broadcasting to a room full of corpses is correct
behaviour. Do **not** guard `m2l2a.scr:890` (`sentry1alarm`) - it is already `isalive`-guarded and
is immediately followed by `attackplayer`; a `thinkstate == idle` test there would break alarm
raising.

## 4. `maps/m2l3.scr` - German search party, plus a real spawn-gate stall

**`sequence1`, `m2l3.scr:406-430`** - "there is an intruder". Five German actors
(`$germansoldier1-4`, `$germanofficer1`), nine lines, all unguarded. A strand on any of the
`waittill saydone` calls at `:407, 410, 413, 416, 419, 422, 425, 428` leaves `level.talking`
stuck at 1 and skips `level.guyshavespoke = 1` at `:438`. Safe to guard.

**`sequence2`, `m2l3.scr:497-505`** - partial guard. `$germansoldier2`'s line at `:493-495` is
wrapped in `if (isAlive $germansoldier2)`; `$germansoldier3` and `$germansoldier1` at `:498-505`
are not. A strand skips `level.talking = 0` at `:507`.

**`$trainguy1`, `m2l3.scr:667, 679, 686, 960, 972, 1006, 1018` - GUARD THE WAIT, NOT THE SAY.**
These lines sit inside `level.getoverheresounding` / `level.holdupsounding` mutex flags that are
set to 1 before the say and reset to 0 only after `waittill saydone`. If `$trainguy1` dies
mid-line the flag is stuck at 1 and that bark is muted for the rest of the map. Worse: in
`procedecheck` (`m2l3.scr:1005-1018`) the strand also skips `thread playerthreatenstuff` and
`level.procede = 0` at `:1020-1021`, stalling the chain-spawn gate. With four players and
friendly fire, killing the train guy is realistic. Keep the say; put a NULL/isalive test in front
of the wait only.

## 5. `maps/m4l2.scr` - visa checkpoint, lines 748-763

`$camptruck_driver` is checked with `isalive` at `:745`, `:752` and `:759`. `$guard01` standing
next to him is checked nowhere - `:748/749`, `:755/756`, `:762/763` are bare. Partial guard, and
three consecutive `waittill saydone` calls on an unguarded speaker. A strand skips
`$guard01 turnto NULL` at `:764` and the driver's `anim_scripted opel_driver` at `:767`.

Mitigating: a parallel `camptruck_waitfordone` (`m4l2.scr:770-774`) runs `wait 19` then sets
`level.WaitingForCampTruckDone = 1`, so there is a timeout fallback. Real but not urgent.

---

# Tier 2 - guard is right, lower interruption probability

Full per-line detail is in the JSON. Summary:

| file | sites | shape |
|---|---:|---|
| `maps/M3L3.scr:897, 898, 913, 914` | 4 | `level.ramsey` guarded on `isAlive $halftrack` but never on himself. **`:914` is the highest-consequence strand outside tier 1**: it hangs the `while (isAlive $halftrack)` loop, so `thread scene1_captain_leavecover` at `:920` never runs and the captain stays tethered behind the wreck for the rest of the map. |
| `maps/M3L3.scr:520, 522` | 2 | ambient follow chatter, unguarded |
| `maps/m1l2a.scr` (17 sites) | 17 | SAS-agent escort ambient barks: `:884/885`, `:898/899`, the `dfr_m1l2_add04` spotlight barks at `:1376, 1388, 1400, 1437, 1453, 1478, 1529` (note `:1512` IS guarded - partial guard), `:2157`, `:2236`, `:932`, `:2501/2504/2507`, `:2704/2707/2710`, `:1591`, `:1596`, `:3032`, `:3193`, `:3818/3819` |
| `maps/t1l2.scr:994, 998, 1015, 1024` | 4 | `level.cappy` / `level.friendly2` unguarded while `:992` IS guarded |
| `maps/t1l3.scr:436, 635` | 2 | `level.captain` unguarded while `:429` IS guarded |
| `maps/m5l1b.scr:208, 209, 421, 423, 425, 457, 459` | 7 | follow barks, unguarded |
| `maps/m5l1a.scr:837, 838` | 2 | `local.friend` unguarded while siblings at `:855, 913, 939` are guarded |
| `global/say_to.scr:62, 63` | 2 | NULL checked at `:6`, `isalive`/`thinkstate` never; shared helper but only `m3l2.scr` calls it |

---

# DO-NOT-GUARD - silencing these can soft-lock the mission

48 sites. These are cutscene or objective dialogue where later code depends on the scene running.
Where a strand is still a real risk, the safe move is to guard **only** the `waittill saydone`
with a NULL/isalive test, never to skip the `say`.

### `maps/m3l1a.scr:5248, 5276, 5367, 5381, 5399, 5406, 5430, 5440, 5446, 5498, 5518, 5528, 5543` - `$shingle_ranger1`

The D-Day beach captain. His lines are interleaved with the sequence machinery itself: at
`m3l1a.scr:5248` he says "go go, get moving", then `:5256-5257` calls
`global/objectives.scr::add_objectives 5` and `current_objectives 5`, `:5258` starts
`thread follow_captain`, and `:5260` queues `ai_add_todo ... "sequence_12_bunker_base"`.
Silencing him removes the only cue the squad has for the bunker push, on a map where the
objective is literally "Follow the Captain to the bunker."

### `maps/m1l2a.scr:1760, 1766, 2318, 2325, 2338` and `:3898, 3909, 3920` - SAS agent

Objective dialogue with the objective grants sitting *between* the lines. At `:1760/1766` the
next statements are `thread newobjective` and
`add_objectives 2 3 "Follow the SAS Agent."` (`:1774-1776`). At `:2318-2338` the grants for
objectives 2 and 3 plus `current_objectives 2` sit at `:2333-2337`, *between* `:2325` and
`:2338`. At `:3898-3920` the exfil objective 6 is granted at `:3925`.

### `maps/m1l2a.scr:1414, 1566, 1817, 1824, 1869, 1877, 1956`

Scripted SAS-agent sequence beats. Lower confidence than the above - read the surrounding block
before touching any of them.

### `maps/m3l2.scr:377, 393, 404, 414` - `level.ramsey`

`dfr_directive_001j_2`, `dfr_directive_150j_1`, `dfr_cover_01j_1`, `dfr_cover_01j_Find`. These
are the captain's HOLD directives to the five battalions - the mission's instructions to the
squad, not chatter.

### `maps/m5l1a.scr:1005, 1017, 1051, 1056, 1063, 1076, 1116, 1127, 1152, 1165`

`dfr_scripted_M5L3_*` scripted mission sequence. Several already carry partial guards; do not
extend those into skips.

### Alarm and PA lines

- `maps/m2l2a.scr:531, 535, 549` - base PA/intercom. Prop emitters, no thinkstate. Broadcasting
  to an empty room is what a PA system does.
- `maps/m2l2a.scr:890` - `sentry1alarm`. Already `isalive`-guarded, immediately followed by
  `attackplayer`. A `thinkstate == idle` guard would break alarm raising.
- `maps/m6l1c.scr:783, 806` - `den_alarm_01c`. Same reasoning.

---

# Suggested order of work

1. Add `convOk` to `coop_mod/replace.scr`. One label, no behaviour change on its own.
2. `maps/M1L3c.scr:379-477` - 32 sites, zero downstream risk, biggest audible win.
3. `maps/m6l1c.scr:520-530, 566-576` - two helper labels, 27 lines covered, and fixes the
   guaranteed strander at `:529`.
4. `maps/m2l2a.scr` - `guytalk` `:493-498`, `norgirls` `:738-757`, `whatsuptalk` `:819`,
   `sciencetalk` `:853-870`, plus the `whatsthesube` typo at `:813`.
5. `maps/m2l3.scr:406-430` and `:497-505` (guard), then `$trainguy1` `:667-1018` (wait-only).
6. `maps/M3L3.scr:914` - small, but it is a map-lasting captain lockup.
7. `maps/m4l2.scr:748-763`, then tier 2.

Every fix in steps 2-7 is a pure addition of a guard clause. None of them removes a line, so a
per-map bisect is cheap if something does go wrong.
