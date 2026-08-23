# MOHAA Sound Asset Catalog — Radio / Explosions / Planes

Read-only research catalog for the coop mod. Covers all three theaters in the GOG War Chest install:

- **AA** = Allied Assault — `G:/GOG/Medal of Honor - Allied Assault War Chest/main/` (Pak0..pak7)
- **SH** = Spearhead — `.../mainta/` (pak1..pak5)
- **BT** = Breakthrough — `.../maintt/` (pak1..pak4)

Sound files live **inside** the `.pk3` (ZIP) archives under `sound/`. The `ubersound/ubersound.scr` (SFX) and `ubersound/uberdialog.scr` (voice) files inside each pak map an **alias name** → a WAV/MP3 path (+ optional subtitle). **Use the alias name in scripts** (e.g. `$player playsound bazooka_exp1` / `level.snd_explosion = "grenade_explode1"`), not the raw path. Aliases are the engine's intended handle; the raw path may be missing or theater-specific.

> **Theater note:** SH and BT ubersound/uberdialog largely *re-alias the same AA WAVs* (AA Pak3 holds the master explosion/leadin set in `sound/weapons/explo/`). Where a SH/BT alias points at an AA-only WAV, it works because pk3s stack at load time. SH/BT add their own NEW wavs for Stuka/C47/glider, stickybomb, mortar, minesweeper, etc.

## Summary / counts

| Category | Raw WAV/MP3 files | Aliases (usable handles) | Richest source |
|---|---|---|---|
| **Radio / comms** | ~10 explicit radio SFX files + the entire `sound/dialogue/` tree for VO | AA: ~25 radio-SFX aliases + dedicated `dfr_m3l3_radio1-6` & comms VO; SH/BT: scripted air-strike radio scenes | AA `ubersound.scr` (radio loops/static) + `uberdialog.scr` (M3L2/M3L3 air-support, M5L3 Alpha-Zulu, M2L1 sniper); SH `t1l2` Foxhound; **BT `E3L4` Angels/King-3 airstrike** |
| **Explosions** | 49 in AA `sound/weapons/explo/` (master set) + SH/BT extras | AA ~139, SH ~117, BT ~116 explosion aliases | **AA Pak3** `sound/weapons/explo/` (all `Explo_*`, `Exp_*`, `Exp_LeadIn_*`) |
| **Planes / aircraft** | AA: plane1-3, m5_plane_sequence, M1_StukaIdle; SH/BT: Stuka_*, c47_*, glider_* | AA ~12, SH ~19, **BT ~36** | **BT pak1** `sound/vehicle/` (Stuka_by, c47_loop/tow, glider_loop) + SH stuka set |

**Caveat — broken/dangling aliases:** Several AA plane aliases point at WAVs that are **NOT present** in any pak (`sound/vehicle/M1_PlaneBy.wav`, `M1_StukaTakeOff.wav`, `plane4.wav`). SH/BT `plane1-4` also re-point to the missing `M1_PlaneBy.wav`. These will fail silently. Prefer the verified-present files flagged below.

---

# 1. RADIO / COMMS

## 1A. Explicitly radio-named SFX (loops, static, beeps) — BEST for ambience/props

These are pure radio sound effects (set static, tuning, looping radio chatter bed). Verified present unless noted.

| Alias (ubersound) | WAV path | Theater | Pak | Notes |
|---|---|---|---|---|
| `radio_loop` | sound/mechanics/Mec_RadioMusic_01.wav | AA | Pak0/Pak3 | Generic looping radio (music/chatter bed) |
| `m6l2a_radio_loop` | sound/mechanics/Mec_RadioMusic_01.wav | AA | Pak3 | Radio loop (m6l2a) |
| `m6l2b_radio_loop` | sound/mechanics/Mec_RadioLoop_05.wav | AA | Pak3 | Radio loop (m6l2b) |
| `m2l3_radio1` | sound/mechanics/Mec_RadioLoop_04.wav | AA | Pak3 | Looping radio |
| `m2l3_radio2` / `m2l2b_radio1/2` / `m3l1b_radio1` | sound/mechanics/Mec_RadioLoop_03.wav | AA | Pak3 | Looping radio |
| `m4l2_radio` / `m4l3_radio` / `m3l1b_radio2` | sound/mechanics/Mec_RadioLoop_04.wav | AA | Pak3 | Looping radio |
| `m2l1_radio3` | sound/mechanics/Mec_RadioLoop_05.wav | AA | Pak3 | Looping radio |
| `m2l1_radio4` | sound/mechanics/Mec_RadioMusic_01.wav | AA | Pak3 | Radio music |
| `m1l2b_radio1` / `m2l2a_radio2` | sound/mechanics/shortwave2.wav | AA | Pak0 | Shortwave tuning |
| `bombtick2` | sound/mechanics/shortwave1.wav | AA | Pak0 | Shortwave (reused as bomb tick) |
| `m1l2b_radio2` / `m2l1_radio1` / `m2l2_radio1` | sound/mechanics/static1.wav | AA | Pak0 | Radio static |
| `m4l3_radiosend` | sound/mechanics/M4_SendTransmission.wav | AA | Pak3 | "Send transmission" SFX |
| `fail_artillery` / `snd_binoculars` | sound/mechanics/Mec_RadioNoise_11.wav | AA | Pak3 | Radio noise burst |
| (no alias) | sound/mechanics/Radio_On.wav | SH | pak1 | Radio power-on |
| (no alias) | sound/mechanics/Radio_Off.wav | SH | pak1 | Radio power-off |
| (raw) | sound/mechanics/shortwave3.wav, shortwave4.wav | AA | Pak0 | Extra shortwave variants |
| (raw) | sound/mechanics/Mec_RadioLoop_03/04/05.wav, Mec_RadioNoise_11.wav | AA | Pak3 | Master radio-loop WAVs |

## 1B. Dedicated radio-transmission VOICE clips (radio-EQ'd dialogue) — BEST for comms playback

`dfr_m3l3_radio1..6` are the actual filtered/EQ'd radio-voice lines from the M3L2/M3L3 air-support call-in (no subtitle in alias, but they ARE the radio-chatter clips):

| Alias | WAV | Theater | Pak |
|---|---|---|---|
| `dfr_m3l3_radio1` | sound/dialogue/M3L2/A/dfr_m3l3_337k.wav | AA | Pak0 |
| `dfr_m3l3_radio2` | sound/dialogue/M3L2/A/dfr_m3l3_338k.wav | AA | Pak0 |
| `dfr_m3l3_radio3` | sound/dialogue/M3L2/A/dfr_m3l3_339k.wav | AA | Pak0 |
| `dfr_m3l3_radio4` | sound/dialogue/M3L2/A/dfr_m3l3_340k.wav | AA | Pak0 |
| `dfr_m3l3_radio5` | sound/dialogue/M3L2/A/dfr_m3l3_341k.wav | AA | Pak0 |
| `dfr_m3l3_radio6` | sound/dialogue/M3L2/A/dfr_m3l3_343k.wav | AA | Pak0 |

## 1C. Radio-style mission DIALOGUE (inferred from subtitle content) — usable comms lines with text

Filename doesn't say "radio" but the content is clearly a radio transmission (call signs, "over", "this is", "do you copy"). All have alias names usable directly. `dfr_` = friendly VO, `den_` = enemy/German VO.

### AA — air-support / artillery call-in (M3L2 & M3L3, Echo Charlie)
| Alias | Subtitle | WAV |
|---|---|---|
| `airstrike_valid_target1` / `dfr_m3l3_346k1` | "Roger. Target acquired." | sound/dialogue/M3L2/A/dfr_m3l3_346k.wav |
| `airstrike_valid_target2` / `dfr_m3l3_347k2` | "Roger. Consider it done." | sound/dialogue/M3L3/A/dfr_m3l3_347o.wav |
| `airstrike_invalid_target1` / `dfr_m3l3_344k1` | "That's not a target. Over." | sound/dialogue/M3L2/A/dfr_m3l3_344k.wav |
| `airstrike_invalid_target2` / `dfr_m3l3_345k1` | "Give me a target. Over." | sound/dialogue/M3L2/A/dfr_m3l3_345k.wav |
| `airstrike_already_enroute1` / `dfr_m3l3_348k1` | "Target already acquired / Already enroute to a target. Over." | sound/dialogue/M3L2/A/dfr_m3l3_348k.wav |
| `airstrike_already_enroute2` / `dfr_m3l3_349k1` | "Already enroute to a target. Over." | sound/dialogue/M3L2/A/dfr_m3l3_349k.wav |
| `dfr_M3L3_add10` | "Echo Charlie out of ammo and returning to base. You're on your own now. Good luck, over and out." | sound/dialogue/M3L3/A/dfr_m3l3_add10o.wav |
| `streamed_dfr_scripted_M3L1_036h` | "Shore party. Gap teams and assault infantry are pinned down at beach obstacles! Request additional supporting fire, over!" | sound/dialogue/m3l1/A/dfr_scripted_M3L1_036h.wav |

### AA — M5L3 artillery coordinates exchange (Alpha-Zulu)
| Alias | Subtitle | WAV |
|---|---|---|
| `dfr_m5l2_504` | "This is Alpha-Zulu. Awaiting coordinates, over." | sound/dialogue/m5l3/A/dfr_m5l2_504k.wav |
| `dfr_m5l2_505` / `dfr_m5l2_508` | "Alpha-Zulu standing by." | sound/dialogue/m5l3/A/dfr_m5l2_505k.wav |
| `dfr_m5l2_506` | "This is Alpha-Zulu, standing by." | sound/dialogue/m5l3/A/dfr_m5l2_506k.wav |
| `dfr_m5l2_507` | "This is Alpha-Zulu. Waiting for a response." | sound/dialogue/m5l3/A/dfr_m5l2_507k.wav |
| `dfr_m5l2_511` | "We got it, over." | sound/dialogue/m5l3/A/dfr_m5l2_511k.wav |
| `dfr_m5l2_512` | "Transmission received." | sound/dialogue/m5l3/A/dfr_m5l2_512k.wav |
| `dfr_m5l2_513` | "Roger, coordinates received." | sound/dialogue/m5l3/A/dfr_m5l2_513k.wav |
| `dfr_m5l2_514` | "Roger, we have the coordinates." | sound/dialogue/m5l3/A/dfr_m5l2_514k.wav |
| `dfr_m5l2_515` | "Got it, coordinates have been received." | sound/dialogue/m5l3/A/dfr_m5l2_515k.wav |
| `dfr_m5l2_516` | "Affirmative, coordinates received." | sound/dialogue/m5l3/A/dfr_m5l2_516k.wav |
| `dfr_scripted_M5L3_12c` | "This is Lieutenant Powell." | sound/dialogue/m5l1/A/dfr_scripted_M5L3_12c.wav |

### AA — M2L1 sniper/spotter radio exchange (Blue Fox / White Rook)
| Alias | Subtitle | WAV |
|---|---|---|
| `dfr_M2L1_200m` | "Blue fox this is white rook." | sound/dialogue/M2L1/A/dfr_M2L1_200z.wav |
| `dfr_M2L1_201m` | "I'm in the guard house near the gate." | .../dfr_M2L1_201z.wav |
| `dfr_M2L1_204m` | "I'm going to take out the guards at the gate." | .../dfr_M2L1_204z.wav |
| `dfr_M2L1_205m` | "When I open fire, give me sniper cover." | .../dfr_M2L1_205z.wav |

### AA — radio-as-objective dialogue (M3L2/M3L3)
| Alias | Subtitle |
|---|---|
| `dfr_M3L3_331j` | "We could call in some air support if we had a radio. We have to find another way around." |
| `dfr_M3L3_333j` | "Private Cobb do you have a radio?" |
| `dfr_M3L3_334i` | "Our squad's radioman was killed in the clearing... there's a sniper in the silo." |
| `dfr_M3L2_add07` | "Powell, grab that radio." |
| `dfr_m3l3_325j_1` | "Powell, get us some air support." |
| `dfr_m3l3_326j_1` | "Powell, hit that 88 with air support." |

### SH — Foxhound radio briefing (t1l2) & Captain Monroe (t3l2)
| Alias | Subtitle | WAV |
|---|---|---|
| `dfr_T1L2_BR6801` | "Base to Foxhound, come in foxhound." | sound/dialogue/Mission_1/Allies/dfr_T1L2_BR6801ALTtb2.mp3 |
| `dfr_T1L2_BC6903` | "Foxhound receiving, go ahead." | .../dfr_T1L2_BC6903ALTta1.mp3 |
| `dfr_T1L2_BR6805` | "Reports indicate the span is heavily defended... succeed at all costs. Over." | .../dfr_T1L2_BR6805tb1.mp3 |
| `dfr_T1L2_BC6904` | "Roger that, over and out." | .../dfr_T1L2_BC6904ALTta4.mp3 |
| `dfr_T3L2_AC4501` | "Sergeant Barnes, do you read me? This is Captain Monroe... destroy the far bridge. Repeat." | sound/dialogue/Mission_3/Allies/dfr_T3L2_AC4501tg8.mp3 |
| `dfr_T3L2_AC4507` | "Get back here ASAP. Godspeed, Sergeant. Over and Out." | .../dfr_T3L2_AC4507tg21.mp3 |

### BT — air-strike radio scene (E3L4, Angels / King 3) — strongest comms set
| Alias | Subtitle | WAV |
|---|---|---|
| `DFRUS_E3L4_CO1606` | "Requesting an immediate air strike on our position, zero-two. Two-seven, zero-zero-one. Over." | sound/dialogue/Mission_3/Allies/DFRUS_E3L4_CO1606xs02.mp3 |
| `DFRUS_E3L4_CO1607` | "Roger, Angels, confirm the target is the castle, over." | .../DFRUS_E3L4_CO1607xs02.mp3 |
| `DFRUS_E3L4_CO1608` | "Roger that, Angels... do you copy?" | .../DFRUS_E3L4_CO1608xs07.mp3 |
| `DFRUS_E3L4_CO1609` | "Do you copy, Angels?" | .../DFRUS_E3L4_CO1609xs02.mp3 |
| `DFRUS_E3L4_NC1517` | "Repeat. We need confirmation to target that location! Over." | .../DFRUS_E3L4_NC1517xd01.mp3 |
| `DFRUS_E3L4_NC1518` | "We need confirmation to run it that close to friendlies. Over." | .../DFRUS_E3L4_NC1518xd03.mp3 |
| `DFRUS_E3L4_NC1519_02` | "King 3, respond. Repeat. Confirm the castle is the target. Over." | .../DFRUS_E3L4_NC1519xd05.mp3 |
| `DFRUS_E3L4_NC1521_02` | "King 3, roger that. Castle is confirmed. Angels inbound. Get clear - now! Over." | .../DFRUS_E3L4_NC1521xd06.mp3 |
| `dfr_E2L1_C472` | "Roger that sir, Airborne all the way." | sound/dialogue/Mission_2/Allies/DFRUS_E2L1_CP1203xy01.mp3 |
| `dfr_E2L1_GLIDER2` | "Roger that, detachment ready." | .../DFRUS_E2L1_GP1302xd03.mp3 |

### Misc radio-style (German, train comms)
| Alias | Subtitle | Theater |
|---|---|---|
| `den_m6l2_630p` | "This is the Schmerzen train, we can give Colonel Sanders a lift into the base..." | AA |

> Mission **briefing** narration `mb_101..mb_604` (`sound/dialogue/Briefings/mb_*.mp3`, AA Pak0) is HQ/OSS briefing voice — radio-adjacent if you want a "command transmission" feel. ~29 clips, one set per mission (mb_1xx..mb_6xx).

---

# 2. EXPLOSIONS

The master explosion WAV set is **AA Pak3 `sound/weapons/explo/`** (49 files). SH/BT mostly re-alias these and add a few extras (tree_explode, KasserineBridgeExplo, Explo_veh_bike, Stuka_impact).

## 2A. By rough size / type (alias → WAV, AA `ubersound.scr` unless noted)

### Small / grenade / mine
| Alias | WAV |
|---|---|
| `grenade_explode1`..`4` | sound/weapons/explo/Explo_Grenade1..4.wav |
| `grenade_exp_water1`/`2` | sound/weapons/explo/Exp_Grenade_Water1/2.wav |
| `explode_mine1`..`4` | sound/weapons/explo/Explo_Grenade1..4.wav (reused) |
| `big_explosion1`..`3` | sound/weapons/explo/Explo_Grenade1..3.wav |

### Medium / bazooka / rocket
| Alias | WAV |
|---|---|
| `bazooka_exp1`..`3` (AA) / `bazooka_exp01`..`03` (SH/BT) | sound/weapons/explo/Explo_Bazooka1..3.wav |
| `bazooka_fly` (SH/BT) | sound/weapons/explo/Exp_LeadIn_08.wav |

### Metal / vehicle / tank / truck / plane / flak / AA-gun (all use Explo_MetalMed1-5)
| Alias | WAV |
|---|---|
| `explode_tank1`..`4`, `explode_truck1`..`5`, `explode_plane1`..`5`, `explode_metal1`..`5` | sound/weapons/explo/Explo_MetalMed1..5.wav |
| `explode_flak881`..`4`, `explode_aagun1`..`4`, `explode_bike1`, `explode_jeep1` (SH), `explode_glider1`/`2` (BT) | Explo_MetalMed*.wav |
| `truck2_explode`, `explode_plane_flying` | Explo_MetalMed1.wav |

### Large / building / stone / wood
| Alias | WAV |
|---|---|
| `explode_building_large1`/`2`, `explode_building_large_large1`/`2` | sound/weapons/explo/Explo_StoneLarge1/2.wav |
| `explode_building_small1`/`2`, `stonecrash01`..`03` | sound/weapons/explo/Explo_StoneMed1/2.wav |
| `explode_gate` | sound/weapons/explo/Explo_WoodLarge1.wav |
| (raw) Explo_WoodLarge1/2.wav (AA), sound/mechanics/Explo_WoodLarge1.wav (BT) | — |

### Gas tank / electrical / searchlight
| Alias | WAV |
|---|---|
| `gas_explode1`/`2`, `explode_gastank1`/`2` (SH) | sound/weapons/explo/Explo_GasTank1/2.wav |
| `short_circuit1`/`2`, `explode_electrical1`/`2`, `explode_prototype` | sound/weapons/explo/Explo_Elec1/2.wav |
| `explode_searchlight1`/`2` | sound/weapons/explo/Explo_Searchlight1/2.wav |

### Artillery / shell — incoming leadin + impact
| Alias | WAV |
|---|---|
| `arty_leadin2`..`7` (AA) / `arty_leadin01`..`12`, `distant_leadin01`..`14`, `drop_bomb` (SH/BT) | sound/weapons/explo/Exp_LeadIn_06..13.wav |
| `arty_exp_sand1`..`4` (AA) / `arty_exp_sand08`..`10` (SH) | sound/weapons/explo/exp_dirt_01..04.wav |
| `arty_exp_water1`..`3`, `explode_water1`..`3` | sound/weapons/explo/exp_water_01..04.wav |
| `arty_exp_interior1`..`3` | sound/weapons/explo/Exp_Interior_01..04.wav |

### Cannon / mortar (fire SFX that read as explosions)
| Alias | WAV | Theater |
|---|---|---|
| `tank_snd_fire1`, `king_snd_fire2`, `flak_snd_fire1`, `flak88_fire1` | sound/weapons/fire/TankCannonFire1.wav | AA |
| (raw) sound/weapons/Fire/4_2_wep_cannon_fire.wav | — | SH |
| (raw) sound/weapons/Fire/MortarFire.wav, knee_mortar_fire.wav | — | BT/SH |
| (raw) sound/weapons/Fire/grenadelaunchFire1.wav | — | SH/BT |

### Naval / scenario one-offs
| Alias | WAV | Theater |
|---|---|---|
| `exp_higgins`, `higgins_explosion`, `explode_sub` | sound/weapons/explo/Exp_Higgins_01.WAV | AA |
| `exp_shingle` | sound/weapons/explo/Exp_Shingle_01.WAV | AA |
| (raw) sound/items/KasserineBridgeExplo1.wav | — | BT |
| (raw) sound/vehicle/Explo_veh_bike.wav | — | BT |
| (raw) sound/mechanics/tree_explode1/2/3.wav | — | SH/BT |
| (raw) sound/weapons/impact/Stuka_impact01..04.wav | — | SH (bomb impact from dive bomber) |

### Bomb priming / timers (BT/SH have dedicated)
| Alias | WAV | Theater |
|---|---|---|
| `bomb_prime1`..`6` | sound/items/Bomb_Priming01..04.wav | SH/BT |
| `bombtick1` | sound/items/Item_Timer_01.wav | AA/SH/BT |
| `radiobomb` | sound/items/RadioBomb.wav | AA |
| (raw) sound/items/stickybomb_fuse/plant/pickup.wav | — | SH/BT |

---

# 3. PLANES / AIRCRAFT

The verified-present aircraft WAVs are concentrated in **AA Pak3** (`sound/vehicle/`) and **BT/SH pak1** (`sound/vehicle/`). Several AA/SH/BT aliases point at the missing `M1_PlaneBy.wav` family — flagged below.

## 3A. Verified-present aircraft WAVs

| WAV path | Theater | Pak | Used by alias |
|---|---|---|---|
| sound/vehicle/M1_StukaIdle.wav | AA | Pak3 | `m1l3b_stuka_idle` |
| sound/vehicle/plane1.wav | AA | Pak3 | `plane_by6` (BT) |
| sound/vehicle/plane2.wav | AA | Pak3 | `plane_by5/7/8` (BT) |
| sound/vehicle/plane3.wav | AA | Pak3 | (raw; airplane bys) |
| sound/vehicle/m5_plane_sequence.wav | AA | Pak3 | `m5l1a_plane` |
| sound/vehicle/Stuka_loop.wav | SH, BT | pak1 | `stuka_loop`, `stuka_loop1/2` |
| sound/vehicle/Stuka_by04.wav | BT | pak1 | `e2l3_c47_flyby` |
| sound/vehicle/stuka_by01.wav, stuka_by02.wav/.mp3, stuka_by03.mp3 | SH/BT | pak1 | `stuka_by1/2`, `e2l2_stuka_flyby`, `stuka_by_close` |
| sound/vehicle/stuka_damage01/02.wav | SH | pak1 | `stuka_by3/4` |
| sound/vehicle/stuka_crash_school.wav, stuka_crash_street.wav | SH | pak1 | `stuka_crash_school/street` |
| sound/vehicle/c47_loop.wav | BT | pak1 | `e2l1_c47_snd_idle` |
| sound/vehicle/c47_tow_line.wav | BT | pak1 | `e2l1_c47_snd_teather` |
| sound/vehicle/glider_loop.mp3, glider_loop2.wav | BT | pak1 | `e2l1_glider_snd_idle` |
| sound/vehicle/plane_cargo.wav | SH | pak1 (alias `cargoplane`) | `cargoplane` |
| sound/vehicle/t1l1_PlaneCrash.wav | SH | pak1 | `t1_planecrash` |
| sound/amb_stereo/t1l1_Opening_Front/Back.wav | SH | pak1 | `t1_planefront`/`t1_planeback` (stereo plane opening) |
| sound/weapons/impact/Stuka_impact01..04.wav | SH | pak1 | dive-bomber bomb impacts |

## 3B. Aircraft aliases — quick reference (alias → WAV)

### AA
| Alias | WAV | Status |
|---|---|---|
| `m1l3b_stuka_idle` | sound/vehicle/M1_StukaIdle.wav | OK |
| `m5l1a_plane` | sound/vehicle/m5_plane_sequence.wav | OK |
| `m1l3b_first_stuka_takeoff` | sound/vehicle/M1_StukaTakeOff.wav | **MISSING WAV** |
| `m1l3b_stuka_strafing_run`, `airplane3`..`6` | sound/vehicle/M1_PlaneBy.wav | **MISSING WAV** |
| `m3l2_first_airstrike`, `m3l2_second_airstrike`, `m3l3_airstrike_first_plane`, `m3l3_airstrike_second_plane` | sound/vehicle/plane4.wav | **MISSING WAV** |
| `credits2` | sound/music/mus_aircraftfacility.mp3 | OK (music) |

### SH
| Alias | WAV | Status |
|---|---|---|
| `stuka_loop` | sound/vehicle/Stuka_loop.wav | OK |
| `stuka_by1` | sound/vehicle/stuka_by01.wav | OK |
| `stuka_by2` | sound/vehicle/stuka_by02.wav | OK |
| `stuka_by3`/`4` | sound/vehicle/stuka_damage01/02.wav | OK |
| `stuka_crash_school`/`street` | sound/vehicle/stuka_crash_*.wav | OK |
| `cargoplane` | sound/vehicle/plane_cargo.wav | OK |
| `t1_planecrash` | sound/vehicle/t1l1_PlaneCrash.wav | OK |
| `t1_planefront`/`t1_planeback` | sound/amb_stereo/t1l1_Opening_*.wav | OK |
| `plane1`..`4` | sound/vehicle/M1_PlaneBy.wav | **MISSING WAV** |

### BT (richest aircraft set)
| Alias | WAV | Status |
|---|---|---|
| `stuka_loop1`/`2` | sound/vehicle/Stuka_loop.wav | OK |
| `stuka_by2`, `stuka_by_close` | sound/vehicle/stuka_by02.mp3 | OK |
| `e2l2_stuka_flyby` | sound/vehicle/stuka_by03.mp3 | OK |
| `e2l3_c47_flyby` | sound/vehicle/Stuka_by04.wav | OK |
| `e2l1_c47_snd_idle` | sound/vehicle/c47_loop.wav | OK |
| `e2l1_c47_snd_teather` | sound/vehicle/c47_tow_line.wav | OK |
| `e2l1_glider_snd_idle` | sound/vehicle/glider_loop2.wav | OK |
| `glider_fire` | sound/amb/Amb_FireLoop_02.wav | OK |
| `plane_by5`/`6`/`7`/`8` | sound/vehicle/plane2.wav / plane1.wav | OK (AA wavs) |
| `explode_glider1`/`2` | sound/weapons/explo/Explo_MetalMed3/4.wav | OK |
| `explode_plane1`..`3`, `explode_plane_flying` | sound/weapons/explo/Explo_MetalMed*.wav | OK |
| `plane1`..`4`, `airplane5`/`6`, `m1l3b_stuka_strafing_run` | sound/vehicle/M1_PlaneBy.wav | **MISSING WAV** |
| `m1l3b_first_stuka_takeoff` | sound/vehicle/M1_StukaTakeOff.wav | **MISSING WAV** |
| `m3l2_first_airstrike`/`second` | sound/vehicle/plane4.wav | **MISSING WAV** |
| `disable_plane1`..`4` | sound/mechanics/m1l2b_disabletruck01..04.wav | OK (engine die-out) |

---

## Appendix — how to find/extract more

- List a pak: `unzip -l "G:/GOG/Medal of Honor - Allied Assault War Chest/main/Pak3.pk3"`
- Read an alias script: `unzip -p ".../main/Pak0.pk3" "ubersound/ubersound.scr"`
- Alias scripts present:
  - AA: `ubersound/ubersound.scr` & `ubersound/uberdialog.scr` in **Pak0**
  - SH: `ubersound.scr`+`uberdialog.scr` in **pak4** (also pak1/pak2/pak3 older copies)
  - BT: `ubersound.scr` in **pak3** (newest) / **pak1**; `uberdialog.scr` in **pak1**
- Alias line format: `alias <NAME> <wavpath> soundparms <basevol> <volmod> <pitch> <pitchmod> <minDist> <maxDist> <channel> <streamed|loaded> [subtitle "..."] maps "<maplist>"`
- `dfr_` = Dialog Friend (Allied VO), `den_` = Dialog Enemy (German VO).
