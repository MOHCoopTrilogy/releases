# MOHAA Sound Catalog — German (Axis) Radio / Comms & Combat VO

Companion to `sound_catalog_radio_explosions_planes.md` (US/Allied pass). This pass covers the
**German / Axis** side: radio-style command call-outs, scripted mission command chatter, and general
combat voice-over.

Extracted read-only from the GOG *Allied Assault War Chest* install at
`G:/GOG/Medal of Honor - Allied Assault War Chest/`. Originals were not modified — every file in the
library is a fresh copy (`cp` for loose files; all German VO ships **loose on disk** as `.wav` (AA) or
`.mp3` (SH/BT), so no `unzip -p` was needed). Alias resolution and subtitles come from the
`ubersound/uberdialog.scr` inside the paks (AA `main/Pak0.pk3`, SH `mainta/pak4.pk3`, BT `maintt/pak1.pk3`).

**Theater tags:** `__aa` = Allied Assault (`main/`), `__sh` = Spearhead (`mainta/`), `__bt` = Breakthrough (`maintt/`).
Library filenames are `<alias>__<originalname>__<theater>.<ext>`.

**Counts copied**
| Set | Files |
|---|---|
| `radio/german_comms/` (radio / command call-outs) | **375** |
| `german_voice/` (general combat VO) | **938** |
| **Total** | **1313** |

Comms theater split: 42 `__aa`, 175 `__sh`, 158 `__bt`.

### Key naming convention (how to read aliases)
- `DEN` prefix = **D**ialog **EN**emy (German); `DFR` = Dialog Friend (US). The engine uses the DEN/DFR
  prefix to pick German-vs-US subtitle handling.
- `DENGM_` = German (Breakthrough naming), `DENIT_` = Italian, `den_` = German (AA/SH naming).
- `axis_axis*` (AA) and `axis_german_*` (SH/BT) are the **multiplayer voice-command menu** sets —
  short, clean, radio-suitable command lines with subtitles.
- All German dialogue aliases carry the `streamed` flag (loose-file streaming), confirming the US-pass lesson.

### AA-usable vs theater-gated (IMPORTANT for the coop mod)
The coop mod runs on AA **m-series** maps. Alias availability is gated by the `maps "..."` field:
- **AA `axis_axis1_*`** — `maps "dm obj"` (MP gametypes). Files are the loose `GRden_*c.wav` set and
  exist in AA `main/`. **Usable on AA** (the alias is registered by AA's own Pak0 uberdialog). These are
  the best AA-native German command call-outs.
- **AA `den_*` generic combat VO** (`generic/g/*`) — `maps "m dm obj"`. **Fully AA-usable**; this is the
  enemy bark set the m-series maps already use.
- **SH `axis_german_*` / `den_call_*` / `den_T*`** — registered only by SH `pak4` uberdialog
  (`maps "dm obj"` / `"t*"`). **Spearhead-gated**: the alias won't resolve on a stock AA server unless the
  mod pk3 re-declares the alias (or you reference the loose file path directly). Flag = **SH-only**.
- **BT `DENGM_*` / `DENIT_*` / `axis_german_global*` / `axis_german_lib*`** — registered by BT `pak1`
  uberdialog (`maps "e*"` / `"dm obj"`). **Breakthrough-gated** = **BT-only** on stock AA.
- To use SH/BT lines on AA maps: re-alias them in the mod's `coop_mod` ubersound (point a new AA-scoped
  alias at the copied loose file), or play the loose `.mp3` path directly. The audio files themselves are
  theater-agnostic once copied into the mod pk3.

---

## 1. RADIO / COMMS — German command call-outs  (`radio/german_comms/`)

These are the priority set: short command lines that read as radio / HQ chatter and mirror the US
airstrike/paradrop radio. Best candidates near the top.

### 1a. AA multiplayer command set — `axis_axis1_*`  (AA-native, loose `GRden_*c.wav`)
The cleanest AA-usable German command lines. (AA ships 5 identical instance copies `axis_axis1..5`; only
the unique `axis_axis1_*` files were kept — same audio.) `maps "dm obj"`, all loose under
`main/sound/dialogue/multiplayer/g/`.

| Alias | File (loose) | Theater | Subtitle |
|---|---|---|---|
| `axis_axis1_aa` | multiplayer/g/GRden_g_01c.wav | AA | Squad, move in! |
| `axis_axis1_ab` | multiplayer/g/GRden_g_02c.wav | AA | Squad, fall back! |
| `axis_axis1_ac` | multiplayer/g/GRden_g_03c.wav | AA | Squad, attack right flank! |
| `axis_axis1_ad` | multiplayer/g/GRden_g_04c.wav | AA | Squad, attack left flank! |
| `axis_axis1_ae` | multiplayer/g/GRden_g_05c.wav | AA | Squad, hold this position! |
| `axis_axis1_af` | multiplayer/g/GRden_g_06c.wav | AA | Squad, covering fire! |
| `axis_axis1_ag` | multiplayer/g/GRden_g_07c.wav | AA | Squad, regroup! |
| `axis_axis1_bg` | multiplayer/g/GRden_c_08c.wav | AA | Charge! |
| `axis_axis1_bh` | multiplayer/g/GRden_c_09c.wav | AA | Attack! |
| `axis_axis1_bi` | multiplayer/g/GRden_c_10c.wav | AA | Open fire! |
| `axis_axis1_cc` | multiplayer/g/GRden_r_03c.wav | AA | Enemy Spotted. |
| `axis_axis1_cd` | multiplayer/g/GRden_r_04c.wav | AA | Sniper! |
| `axis_axis1_ce` | multiplayer/g/GRden_r_05c.wav | AA | Grenade! Take Cover! |
| `axis_axis1_cf` | multiplayer/g/GRden_r_06c.wav | AA | Area Clear. |
| `axis_axis1_ba` | multiplayer/g/GRden_c_01c.wav | AA | Cover me! |
| `axis_axis1_bb` | multiplayer/g/GRden_c_02c.wav | AA | I'll cover you! |
| `axis_axis1_bc` | multiplayer/g/GRden_c_03c.wav | AA | Follow me! |
| `axis_axis1_bf` | multiplayer/g/GRden_c_06c.wav | AA | Taking Fire! Need some help! |
| `axis_axis1_ca` | multiplayer/g/GRden_r_01c.wav | AA | Yes sir! |
| `axis_axis1_cb` | multiplayer/g/GRden_r_02c.wav | AA | No sir! |

(Also present: `_da`..`_eh` taunt/banter lines — "Is that all you've got?", "They're a bunch of cowards!", etc.)

### 1b. SH multiplayer command set — `axis_german_*`  (SH-only; loose `Multiplayer/German/*.mp3`)
Mirror of 1a but German-voiced for Spearhead, plus objective win/lose lines.

| Alias | File (loose) | Theater | Subtitle |
|---|---|---|---|
| `axis_german_ba` | Multiplayer/German/den_mpsc_GS5926tk1.mp3 | SH | Squad, move in! |
| `axis_german_bb` | Multiplayer/German/den_mpsc_GS5927tk1.mp3 | SH | Squad, fall back! |
| `axis_german_bc` | Multiplayer/German/den_mpsc_GS5928tk4.mp3 | SH | Squad, attack right flank! |
| `axis_german_bd` | Multiplayer/German/den_mpsc_GS5929tk2.mp3 | SH | Squad, attack left flank! |
| `axis_german_be` | Multiplayer/German/den_mpsc_GS5930tk2.mp3 | SH | Squad, hold this position! |
| `axis_german_bf` | Multiplayer/German/den_mpsc_GS5931tk3.mp3 | SH | Squad, covering fire! |
| `axis_german_bg` | Multiplayer/German/den_mpsc_GS5932tk3.mp3 | SH | Squad, regroup! |
| `axis_german_cg` | Multiplayer/German/...GS5942.mp3 | SH | Attack! |
| `axis_german_ch` | Multiplayer/German/...GS5943.mp3 | SH | Open fire! |
| `axis_german_dc` | Multiplayer/German/...GS5946.mp3 | SH | Enemy Spotted. |
| `axis_german_dd` | Multiplayer/German/...GS5947.mp3 | SH | Sniper! |
| `axis_german_de` | Multiplayer/German/...GS5948.mp3 | SH | Grenade! Take Cover! |
| `axis_german_df` | Multiplayer/German/...GS5949.mp3 | SH | Area Clear. |
| `axis_german_cf` | Multiplayer/German/...GS5941.mp3 | SH | Get ready to move in on my signal. |
| `axis_german_ah` | Multiplayer/German/den_mpgm_GS5925tk6.mp3 | SH | The enemy has overrun our objective! |
| `axis_german_ag` | Multiplayer/German/den_mpgm_GS5924tk2.mp3 | SH | We've lost an objective! |
| `axis_german_ae` | Multiplayer/German/den_mpgm_GS5922tk5.mp3 | SH | Objective achieved. |

(Plus `_ea`..`_eh` taunts, `_success01/02` `_failure01/02` objective stingers.)

### 1c. SH scripted mission Axis chatter — `den_T*`, `den_call_*`  (SH-only; loose `Mission_*/Axis/*.mp3`)
Scripted in-mission command/reinforcement chatter. `den_call_GS*` is the **reinforcement call-out family**
(120 files copied; 3 distinct lines, many voice variants — ideal for "rally on the contact" radio).

| Alias | File (loose) | Theater | Subtitle |
|---|---|---|---|
| `den_T1L1_GS5901` | Mission_1/Axis/den_T1L1_GS5901tk2.mp3 | SH | Over here, over here! |
| `den_T1L1_GS5801` | Mission_1/Axis/den_T1L1_GS5801tp1.mp3 | SH | Hurry, find him! |
| `den_T1L3_GG5701` | Mission_1/Axis/den_T1L3_GG5701tu1.mp3 | SH | Americans! |
| `den_T1L3_GC5601` | Mission_1/Axis/den_T1L3_GC5601tf11.mp3 | SH | Come get me coward! |
| `den_T1L1_GermanWalla` | Mission_1/Axis/den_T1L1_GermanWalla.mp3 | SH | (German crowd/radio walla loop — ambient chatter bed) |
| `den_call_GS5912xx` (×9) | Mission_2/Axis/den_call_G*5712/5812/5912*.mp3 | SH | That's our truck, attack! |
| `den_call_GS5913xx` (×9) | Mission_2/Axis/den_call_G*5713/5813/5913*.mp3 | SH | They've got our supplies! |
| `den_call_GS5914xx` (×N) | Mission_2/Axis/den_call_G*5714*.mp3 | SH | Stop them! |

### 1d. BT scripted mission Axis chatter — `DENGM_E*`, `DENIT_E*`  (BT-only; loose `Mission_*/Axis/*.mp3`)
The richest **alarm / intruder / pursue** radio content in the game. Top picks:

| Alias | File (loose) | Theater | Subtitle |
|---|---|---|---|
| `DENGM_E1L4_GS8607` | Mission_1/Axis/DENGM_E1L4_GS8607xc01.mp3 | BT | Alarm! Alarm! |
| `DENGM_E1L4_GO8307` | Mission_1/Axis/DENGM_E1L4_GO8307xk02.mp3 | BT | Intruder! Alarm! |
| `DENGM_E1L4_GS8804` | Mission_1/Axis/DENGM_E1L4_GS8804xo06.mp3 | BT | Halt, Intruder! |
| `DENGM_E1L3_GS8911` | Mission_1/Axis/DENGM_E1L3_GS8911xk03.mp3 | BT | Intruders! |
| `DENGM_E1L3_GS8910` | Mission_1/Axis/...GS8910*.mp3 | BT | After them! |
| `DENGM_E3L3_G95301` | Mission_3/Axis/...G95301*.mp3 | BT | Stop the American! |
| `DENGM_E3L3_G75103` | Mission_3/Axis/...G75103*.mp3 | BT | Stop him! |
| `DENGM_E3L3_G45801` | Mission_3/Axis/...G45801*.mp3 | BT | Ambush!!! |
| `DENGM_E3L3_G45802` | Mission_3/Axis/...G45802*.mp3 | BT | Covering Fire!! |
| `DENGM_E3L3_G45805` | Mission_3/Axis/...G45805*.mp3 | BT | Hold them off! |
| `DENGM_E3L3_G65004` | Mission_3/Axis/...G65004*.mp3 | BT | Reload! Reload! |
| `DENGM_E1L4_GS8807` | Mission_1/Axis/...GS8807*.mp3 | BT | Do not let him escape! |
| `DENGM_E1L4_GS8806` | Mission_1/Axis/DENGM_E1L4_GS8806xo02.mp3 | BT | Over here! |
| `DENGM_E1L3_GS8003` | Mission_1/Axis/...GS8003*.mp3 | BT | It is a trick! Get them! |
| `DENGM_E3L3_G55901` | Mission_3/Axis/...G55901*.mp3 | BT | Don't let the American get to the artillery! |
| `den_E2L1_ITALIAN2` | Mission_2/Axis/DENIT_E2L1_IS7602xu03.mp3 | BT | An airplane crashed over here. |
| `DENIT_E2L2_IS7501` | Mission_2/Axis/...IS7501*.mp3 | BT | Defend the airfield! |
| `DENIT_E1L4_IS7102` | Mission_1/Axis/...IS7102*.mp3 | BT | Find the American! |

(Also: checkpoint/papers dialogue — "Let me see your papers.", "I must see your clearance!" — and a
ship-sinking set — "Abandon ship!", "We are sinking!".)

### 1e. BT global Axis combat commands — `axis_german_global*`  (BT-only; loose `global/GM/*.mp3`)
Map-agnostic ("global") German combat shouts used across BT `e` maps. Subtitles live in `//` comments
above each alias in the uberdialog.

| Alias | File (loose) | Theater | Subtitle |
|---|---|---|---|
| `axis_german_global001a/b` | global/GM/DENGM_global_GS8001xl0*.mp3 | BT | Over here! |
| `axis_german_global002a/b/c` | global/GM/DENGM_global_GS8002*.mp3 | BT | Return fire! |
| `axis_german_global003a/b/c` | global/GM/DENGM_global_GS8003*.mp3 | BT | Ambush! |
| `axis_german_global004a/b` | global/GM/DENGM_global_GS8004*.mp3 | BT | Incoming! |
| `axis_german_global006a/b` | global/GM/DENGM_global_GS8006*.mp3 | BT | There he is! |
| `axis_german_global007a/b` | global/GM/DENGM_global_GS8007*.mp3 | BT | Up ahead! |
| `axis_german_global008a/b/c` | global/GM/DENGM_global_GS8008*.mp3 | BT | Behind us! |
| `axis_german_global009a/b/c` | global/GM/DENGM_global_GS8009*.mp3 | BT | They're everywhere! |
| `axis_german_global010..014` | global/GM/DENGM_global_GS801*.mp3 | BT | Help! / Fight soldier! / I'm here! / What was that? / Who's there! |

### 1f. BT MP jail/Liberty objective commands — `axis_german_lib*`  (BT-only)
| Alias | File | Theater | Subtitle |
|---|---|---|---|
| `axis_german_liba` | Multiplayer/German/DENGM_mplb_GS8833*.mp3 | BT | Guard our jail! |
| `axis_german_libb` | Multiplayer/German/DENGM_mplb_GS8834xo02.mp3 | BT | Capture the enemy jail! |
| `axis_german_libc` | Multiplayer/German/DENGM_mplb_GS8835*.mp3 | BT | I'm defending our jail! |
| `axis_german_libd` | Multiplayer/German/DENGM_mplb_GS8836xo06.mp3 | BT | I'm attacking the enemy jail! |
| `axis_german_libe` | Multiplayer/German/DENGM_mplb_GS8837*.mp3 | BT | Rescue the prisoners! |
| `axis_german_libf` | Multiplayer/German/DENGM_mplb_GS8838xo04.mp3 | BT | The enemy is attacking our jail! |

---

## 2. GENERAL COMBAT VO — German enemy barks  (`german_voice/`)

The full AA `generic/g/*` enemy bark set (loose `.wav`, `maps "m dm obj"`, **fully AA-usable**) plus BT
German generic death/pain. These are non-radio in-world shouts. Most carry **no subtitle** (generic barks);
the engine plays them positionally on actors. Folders mirror the source categories.

| Category (folder) | Files | Theater | Source | Notes |
|---|---|---|---|---|
| `german_voice/attack/`  | 171 | AA | generic/g/attack | "den_attack_*" — charge/aggression shouts |
| `german_voice/sighted/` | 42  | AA | generic/g/sighted | spotting the player (incl. Alt_G_/Alt_O_ alarm variants) |
| `german_voice/curious/` | 92  | AA | generic/g/curious | "did you hear that?" investigate barks |
| `german_voice/fear/`    | 163 | AA | generic/g/fear | panic / suppressed |
| `german_voice/death/`   | 99 AA + 11 BT | AA/BT | generic/g/death, BT generic/GM/death | death screams |
| `german_voice/pain/`    | 99 AA + 16 BT | AA/BT | generic/g/pain, BT generic/GM/pain | hit reactions |
| `german_voice/idle/`    | 26  | AA | generic/g/idle | ambient idle mutters |
| `german_voice/disguise/`| 219 | AA | generic/g/disguise | checkpoint/guard challenge lines (m2l2 "papers/intruder" set lives here; some DO carry subtitles, e.g. "Who is your commanding officer?") |

### Generic-bark alias families (for scripting)
These are exposed via aliases like `snd_den_<state>_generic<N>` (death/pain/fear) and
`den_alarm_*` / `den_attack_*` / `den_curious_*` (registered in all three uberdialogs). Examples:
- `snd_den_death_generic1..N` -> `generic/g/death/den_death_*.wav`
- `snd_den_pain_generic1..N` -> `generic/g/pain/*.wav`
- `den_alarm_09a01..N` -> `generic/g/sighted/Alt_G_*.wav` (the "alarm raised on sighting" set — closest
  generic equivalent to a radio alert; **no subtitle**, pure shout)
- `den_attack_NNNx` -> `generic/g/attack/den_attack_*.wav`

---

## 3. Notes / decisions
- **Why loose, not pak:** every German dialogue file ships loose under `<theater>/sound/dialogue/...`
  (`.wav` for AA, `.mp3` for SH/BT) and is flagged `streamed`. The paks contain only the alias scripts,
  not the audio. (AA `Pak4.pk3` also bundles a copy of `GRden_*`, but the loose copies were used.)
- **Dedup:** AA registers `axis_axis1..5` as five identical instances pointing at the same `GRden_*`
  files; only the unique `axis_axis1_*` set was copied (~42 files) instead of 210 redundant copies.
- **BT `DENGM_call_*` aliases** reference renumbered files (`den_call_GC57xx`) that do not exist loose in
  the BT install (stale SH-era references) — skipped, 0 copied. The 120 `den_call_*` copies are the SH set.
- **No dedicated "radio EQ" German loop** was found beyond the shared `Mec_RadioLoop_*` static beds already
  catalogued in the US pass (`radio/static_loops/`); those beds are language-neutral and reusable under any
  German radio call-out. `den_T1L1_GermanWalla.mp3` is the one German-specific ambient radio/crowd bed.
- **Italian (`DENIT_`)** lines were included where they are command/comms content (BT Mission Axis), since
  BT Axis forces are mixed German/Italian; flagged in the tables.
