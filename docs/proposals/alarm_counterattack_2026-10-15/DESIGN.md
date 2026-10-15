# Alarm state + final counter-attack - design (no code yet), 2026-10-15

Both features ride on the AI realism build (`proposals/ai_realism_2026-10-15/BUILD.md`): `reinf.scr::rnf_entry` (planned wave entry), the radio call-ins, the idle watchdog, and the officer waves in `officer.scr::coop_call_reinforcements` (45 s cooldown). Nothing here adds a new spawn system.

## What exists today (grep results)
- **Two vanilla alarm systems.** `global/alarmer.scr` (m4l3, m6l2a, m6l3a): any `enemy` AI runs to an `animate_equipment_alarmswitch` (targetname `alarm`), `alarmspawner` AI appear, the bell rings, `alarm_always_on` re-arms it after 14-20 s. `global/alarm_system.scr` (disguise maps e1l4 PreShip/Ship, m2l2a, m6l1c): zone triggers + `$alarm_switch_trigger` + `$ai_alarm` pullers + reinforcements; it already refuses to ring while a contact is still disguised.
- **Other alarm maps** (scripted, not generic): m1l2a (coop go-loud klaxon, `coop_alarm_emitter`, `level.alarm`), m2l3 (`level.alarm`, `$alarm_sound`, `alarmnode`), e1l4/PreShip (`$clerkalarmswitch anim turnon`). Alarm text also appears in e1l1, e1l3, e2l2, e3l3, m1l1 (commented out), m1l3a/b/c, m3l1b, m3l2, m5l3, t2l1/t2l2. Most of the 54 maps have no working alarm.
- **Assets.** Switch models: `models/animate/alarmswitch.tik` (animated: `anim turnon`), `models/miscobj/alarmswitch.tik`, `models/static/alarmswitch.tik` (static), also `electrical_switch_pulse/nopulse`. Bells: `models/static/alarmbell.tik`, `static_alarmbell.tik`, `static_subalarmbell.tik`. All are already in the build-mode catalog (`buildmode_catalog.scr` rows 14, 28, 29).
- **Sounds.** `alarm_switch` (Mec_Switch_05), `alarmbell` (Mec_Alarm_07; ubersound lists only m6l2a/m4 - needs widening), `coop_alarm_siren` (Mec_Alarm_10, our own alias, ubersound.scr:1536, works on `m e t` maps), German shout lines `den_alarm_*` (sighted set), `coop_radio_german_reinf1..9`.
- **Tooling.** `coop_build` places any catalog model live and saves `coop_mod/save/build_<map>.dat` in paste-ready script form; the proven bake path is `coop_mod/coop_placements.scr::<map>` (m1l1 is the template). `docs/tools/gen_push_maps.py` + `push_spawns.json` is the model for a data-file-to-generated-script flow.

## Feature A - ALARM state

**Authoring (fast, data-driven).** One new file `docs/tools/alarm_points.json`: per map, a list of `{pos, angles, kind: switch|bell, area}`. A generator `gen_alarm_points.py` writes `coop_mod/alarmpoints.scr::<map>` (spawn script_model + `alarmswitch` + a bell within ~600 u). Points are captured in-game: stand at the wall, `coop_build` the switch, then the generator reads `build_<map>.dat` entries whose model matches alarmswitch/alarmbell and appends them to the JSON. A map is "alarm-ready" with 2-4 points. Target: **first 12 maps** with open enemy compounds and no scripted rides: m1l1, m1l3a, m3l1a, m3l2, m4l1, m5l2, e2l1, e3l1, e3l2, t1l1, t2l1, t3l1 (user adjusts). Placement rule: one in each enemy HQ/barracks, one at each main gate/bunker door, one near the officer start; never within 700 u of a player spawn.

**Vanilla maps keep their own system.** m4l3, m6l2a, m6l3a stay on `alarmer.scr` (they only get the coop hooks below); m1l2a and m2l3 keep their scripts.

**Trigger** (new `coop_mod/alarm.scr`, runs only if the map has alarm points):
1. A guard that has had a player enemy for >=2 s and is within 1500 u of a switch is ordered to run to it (vanilla `type_attack alarm` + `alarmnode` mechanic, or a `runto` goal if that does not take). The run is visible; **killing or stunning him before he arrives cancels the pull** (the stealth-skill moment).
2. Sustained unsilenced gunfire (>=3 shots within 1200 u of a living guard with no enemy yet) sends the nearest guard to a switch.
3. A guard who saw a player and survives 12 s (fled) also pulls.
Disguised players never trigger (copy the `is_disguised` gate in `alarmer.scr::doalarm`).

**Effect while live.** Switch `anim turnon` + `alarm_switch`; bell/siren loops (`coop_alarm_siren`, widen the `alarmbell` map list); `rnf_entry` waves at radio cadence (first after 10 s, then ~40 s) until a cap; idle patrols (via `aisquad`/`aimaneuver`) get one go-to-player-area order; `level.alarm = 1` for existing script checks. **Off:** shoot or knife the bell/switch (shootable pattern of `rnf_radio_shootable`), or 90 s with no AI seeing a player (timeout, waves stop). Max 2 pulls per mission; a second switch may re-arm while one is still alive.

**Fairness caps.** Alarm waves share the existing call budget; max 8 alarm-wave AI alive; size by players (1-2: 3, 3-4: 4, 5+: 5); no dogs/air; no alarm in the first 60 s of a map.

**Stealth-map exclusion.** The module starts only when `level.coop_alarmMap == 1` (from the alarm-ready list) and is hard-blocked when any of: `level.coop_stealthMap == 1` (m2l2a, e1l4; m6l1c sets it late at line 1253), `level.coop_enableDisguises` (e1l4, m2l2a, m2l2b, m6l1c), or the map already owns an alarm (m1l2a, m2l3, m4l3, m6l2a, m6l3a, m6l1c, e1l4). `bust.scr` contain is untouched. With the cvar 0 everything is as released.

**Switches:** `coop_alarm` (default 0 until proven, then 1), `coop_alarmMaxPulls` 2, `coop_alarmWaveGap` 40, `coop_alarmCap` 8, `coop_alarmDebug` (`^~^~^ ALARM` lines).

## Feature B - COUNTER-ATTACK

**Trigger.** Main objectives complete, hooked at the top of `coop_mod/missioncomplete.scr::main` (before `coop_missionCompleteRan` is set, lines 29-30), once per map via `level.coop_counterDone`.
**Flow.** Objective line "Hold the position - counter-attack incoming", German radio line + `coop_radio_on` squelch; 15 s grace; waves through `rnf_entry` (planned entry, never from a sight line) every 25-35 s for **150 s**; HUD countdown; at the end leftover AI stay alive and `missioncomplete` continues exactly as today. **End condition is time**, not kills (kills can strand a squad); early finish if >=80% of wave AI are dead after wave 4.
**Wave sizes.** 1-2 players: 4 per wave; 3-4: 6; 5-8: 8; rifle/MG mix, one officer-type from wave 3 (officer wave types 0/1/3/6 only; skip 2 sniper, 4/5 air, 7 dogs). Cap 14 alive.
**Which maps.** On by default where the final area is open. Exclude via `level.coop_noCounter = 1`: maps ending in a ride or cutscene (e1l3 FinalEscape, e1l4 ship end, vehicle/train/plane endings in the m5, t3, e2l2, e3l4 sets - confirm each by reading the map's last label), the stealth/disguise maps above, and any case with no living player.
**Switches:** `coop_counter` (0 until proven), `coop_counterSecs` 150, `coop_counterWaveGap` 30, `coop_counterCap` 14, `coop_counterDebug`.

## Build order (each step a dedicated-server boot, no feature on by default)
1. **Counter skeleton** (`coop_counter.scr`, forced by `coop_counterForce 1`): HUD + timer. Test: m1l1, message shows, 150 s elapse, map advances; `coop_counter 0` identical to today.
2. **Waves via `rnf_entry`.** Test: counts correct for 1/2/4 players, entries out of sight, cap 14 holds.
3. **Exclusions + real objective-complete trigger.** Test: fires on 3 maps; does NOT fire on a ride-ending map, m2l2a or e1l4.
4. **Alarm module on m4l3** (existing `alarmer.scr`, new hooks): guard runs and can be killed; siren heard map-wide; waves arrive; shooting the bell stops it.
5. **Generator + capture flow** on m1l1: points via `coop_build`, `alarmpoints.scr` generated; none near spawns.
6. **Rollout** to the other 11 maps in batches; each boot proves the alarm fires and can be silenced.
7. **Stealth regression:** m2l2a and e1l4 with both cvars 1 show no `^~^~^ ALARM` line and no counter-attack.
8. Playtest, then flip defaults.

## Open questions (recommended defaults)
- Wake idle patrols map-wide? Only within 2500 u of the switch.
- Alarm waves outlast the officer? Yes, cap-limited (user: "reinforcements would continue").
- Counter-attack for a lone player? On, size 4.
- First alarm maps? The 12 above, user veto.
- Who places switches? User places with `coop_build` (~5 min a map), agent batch-checks the .dat files.
