# Live Operations: CRIME.NET-style bot matches popping up on the NEW GAME war map

**Status: PLAN + MOCKUP ONLY (2026-11-09).** Nothing in the mod or engine has been changed.

| File | What it is |
|---|---|
| `mock_newgame.png` | The existing NEW GAME wall map with five live contracts on it, the Stalingrad edge tab, one hover slip and the open dispatch card. |
| `mock_card.png` | The dispatch card at 2x, for checking the type. |
| `ops_locations.json` | The location table: all 35 installed MP maps, each with its pin, confidence and evidence. Section 4 is this table. |
| `make_mock.py` | Draws both mocks from `../sp3camp_2026-11-08/warmap.py`. It also runs a layout check over **all 35** locations. |
| `layout_report.json` | The verdict from that check for each location. |

## What the user asked for, in order

1. "Can we do like Payday does the crime.net map? Occasionally have TDM or Objective game modes pop up on
   their respective TDM and obj maps and locations on the map. It'll put you into maps against bots."
2. "You can jump into these without unlocking them obviously. And they are random."
   - So nothing is locked, and no campaign progress is needed to play a contract.
   - Everything is rolled at random: the map (from the TDM/OBJ-capable pool), the mode (when the map has
     both), the bot count, the bot skill, the modifier, when the contract appears and how long it stays up.
3. "Instead of it on a board have the locations pop up on the existing map where you pick a mission for
   single player."
   - So there is no new board and no new attic prop.
   - Contracts appear on the **NEW GAME war map** (`ui/hzm_newgame3d.urc`, the 3D wall), and on the flat
     chooser `ui/hzm_ngflat.urc` as well (feasible: see section 6).
   - They sit alongside the campaign tags and look clearly different from them.
   - The VANILLA / CHRONOLOGICAL toggle and the campaign locks are left exactly as they are. Contracts
     ignore locks.
4. "Make sure we get their locations correct as much as possible."
   - Every pin comes from the evidence table in section 4.
   - Fictional or ambiguous maps are marked *approx* and placed for a stated reason.

---

## 1. The experience (`mock_newgame.png`)

You open NEW GAME as usual. The war map, the twelve campaign pins and tags, the dashed leaders, the legend
and the toggle are all unchanged. On top of that, **4 to 6 live contracts** are inked onto the map.

### What a contract looks like

Each contract is deliberately unlike a campaign tag. Campaign tags are paper slips in campaign colours;
contracts are **red grease pencil and rubber stamps**:

- **A red grease-pencil loop** around the location. It pulses slowly: the shader's alpha breathes.
- **A timer ring** inside the loop. It drains clockwise and turns red in its last quarter.
- **A small rubber stamp, TDM or OBJ**, placed beside the loop by a layout pass. The pass tries 8
  directions at two distances, and refuses any spot over a campaign pin, a campaign tag, a printed
  name, the toggle, the legend or another contract. For all 35 locations it reports **0 problems**.
- **A censored location** ("Somewhere in Germany" and similar) gets a **dashed** loop around an area and
  a small black tack. It never gets an invented town. This is the real wartime censor's formula, and it
  keeps the rule that real places must be real.
- **A contract at a place you fought in the campaign wraps that campaign pin.** For example, the Omaha
  OBJ contract circles the aa3 pin, Brest circles aa5, Berlin sh3, Monte Cassino bt3 and Kasserine bt1.
  In CRIME.NET terms, the place is hot again.
- **Stalingrad** lies east of the wall's window (lon -16.4 to 40.4). It appears as an **edge tab**
  reading "STALINGRAD >>" at its latitude, circled in grease pencil.

### Hovering and clicking

- **Hover** a contract and a typed slip appears. It gives the place, the mode, the bots, the modifier
  and the time left, for example "VALLETTA, MALTA / TEAM MATCH 7 BOTS / HARDCORE / EXPIRES 1:48".
- **Click** a contract and its **dispatch card** opens (`mock_card.png`). The card carries:
  - the operation codename, rolled from a word list
  - location, map, mode
  - forces: "You + 5 riflemen vs 6 Axis (11 bots)"
  - bot skill, modifier, limit, reward, expiry
  - **DEPLOY** and **FILE AWAY** stamps

### Draw order

From the bottom up: map, contract loops and rings, campaign tags, contract stamps, hover slip, card. A
loop that runs under a tag therefore never hides the tag's lettering.

### Three campaign tags need a small nudge

This is part of the proposal and needs a yes from the user. Three Breakthrough tags sit right on top of
contract locations:
- **bt3** (Monte Cassino) covers Bologna, Monte Battaglia and the Castello area: it sits on the Gothic
  Line.
- **bt2** (Sicily) covers Malta.
- **bt1** (Kasserine) covers the Tunisian desert.

A search that keeps `warmap.qa()` clean, and keeps every contract loop clear, moved them:

| Tag | Was | Becomes |
|---|---|---|
| bt3 | (43.65, 12.6) | (45.9, 12.6), above the Adriatic head |
| bt2 | (36.0, 17.9) | (36.0, 18.9) |
| bt1 | (34.2, 9.4) | (38.7, 8.9), into the sea north of Tunisia |

Pins and leaders do not move. The change is three numbers in `missions.json` plus a rerun of
`make_ng3campaigns.py`. The mock already shows the nudged layout.

**The other option is to leave the tags alone**, but then the tag hides the contract. Malta and Bologna
would be invisible. Two *approximate* France pins were also moved, to a clear spot in the Massif Central;
section 4 gives the reason.

### Cadence

- The generator ticks in **60 s slots**. In each slot, if fewer than 6 contracts are live, there is about
  a 60% chance a new one arrives.
- Each contract lives for **3 to 6 minutes**, so the map settles at 4 to 6 live contracts, with something
  new every 1 to 2 minutes.
- Only **one live contract per location slot** at a time:
  - The three Bizerte maps share one slot.
  - Crossroads and The Bridge share the "Somewhere in France" slot.
  - Generic locations in the same theatre never stack.
- A contract whose card is open **does not vanish under your cursor**. Its ring keeps draining, and
  DEPLOY works until you close the card.

---

## 2. Mechanics

### Start path

This reuses the existing HZM MP launch path exactly. Today a mode button execs
`ui/coop_mpmenu/start_<mode>.cfg` (`coop_mpMode`, `ui_mpIs*`), then `launch_gt<n>.cfg` (`ui_dedicated 0`,
`ui_maxclients`, `ui_hostname`), then `ui_startdmmap <gt>`. `UI_StartDMMap_f` (`cl_ui.cpp`) reads
`ui_dmmap`, `ui_timelimit`, `ui_fraglimit` and `ui_gamespy`, and runs `map`. On the stock MP map,
`mp.scr` runs (`level.coop_mpRun`), and `mp_bots.scr` drives `sv_numbots` from `coop_mpBotFill`.

DEPLOY runs:

```
hzm_ops deploy <slot>                        (client command, new; C++)
  set ui_dmmap dm/mohdm3 ; set ui_timelimit 10 ; set ui_fraglimit 40
  set ui_maxclients 4 ; set ui_gamespy 0 ; set ui_hostname "HZM Op IRON KETTLE"
  exec ui/coop_mpmenu/ops/arm.cfg            coop_mpMode none, ui_mpIs* = 0, coop_mpOps 1, sv_maxbots 16
  exec ui/coop_mpmenu/ops/bots_11.cfg        coop_mpBotFill 11            (generated family)
  exec ui/coop_mpmenu/ops/skill_veteran.cfg  bot_aim* tier                (generated)
  exec ui/coop_mpmenu/ops/mod_storm.cfg      coop_mpWeather / coop_mpHardcore / coop_mpPreset (generated)
  exec ui/coop_mpmenu/ops/side_allies.cfg    coop_mpOpsSide allies
  exec ui/coop_mpmenu/launch_gt2.cfg         -> ui_startdmmap 2   (4 for OBJ)
```

**Why per-value cfgs instead of variables:**
- A cfg cannot `$`-substitute a dynamically set cvar.
- `vstr` is banned by isolation clause 18.
- C++ outside a declared `HZM-MP` hook may not name a `coop_mp*` token (clause 14).

The `bots_8.cfg` family already solves this problem the same way, and the `ops/*.cfg` files are generated.

`sv_maxbots` is `CVAR_LATCH`, so it is set before `ui_startdmmap`. If it is not, the log says "No bots,
skipping navigation" and no bots spawn.

### In the match: `coop_mod/mp_ops.scr` (new, MP-owned, in `MP_MANIFEST`)

- Gated on `level.coop_mpRun == 1` **and** `coop_mpOps == 1`. The flag is consumed one-shot at map init
  (TRAPS T7).
- Puts the host on `coop_mpOpsSide`. `G_RemoveBots` already sheds the fuller team, so the bots split
  around the human: "You + 5 vs 6".
- Prints `^~^~^ OPS start|end`.
- Writes `ui_opsResult "win 23 9 IRON KETTLE"` at the end. A listen server shares its cvar table with its
  own client, so the menu can read this.

### Return

The client already reads `PMF_INTERMISSION` (`cl_ui.cpp:2211`).
- When `ui_opsLive 1` is set and intermission has lasted 10 s or more, the ops module sends `disconnect`
  (for the listen host, that also kills the server).
- It then execs `ops/restore.cfg` to put the `bot_aim*` tier back to defaults.
- It reopens **NEW GAME**, with the finished card stamped **MISSION ACCOMPLISHED** or **OPERATION FAILED**.
- `sv_maplist` holds only the contract map, so the worst case is a replay of that map, never a coop load.

### Rewards

- **Recommendation:** pay XP into the **Service Record** through the one sanctioned bridge,
  `xp.scr::xp_award_mp`. Isolation clause 8 permits it, and it is capped at 2000 per match by
  `coop_xp_mpMatchCap`.
- That bridge already credits a human killing a bot. Only a *bot* attacker is filtered, by
  `coop_mpProgCreditBots`.
- On top of that, a contract bonus (+100 for a win, +50 for a loss, scaled by bot skill), paid once by
  `mp_ops.scr`.
- No contract is gated behind anything.

### Friends

It is a listen server. `mp_bots` sheds one bot per human who joins, and LAN browsers see the server.
A "Radio it in" stamp on the card sets `ui_gamespy 1` and a findable hostname.

**Shared world (recommended):** seed the roll from the **UTC slot**,
`seed = hash(floor(utc/60), "hzm-ops-v1")`. Everyone on the same mod version then sees the same
contracts at the same moment, so friends can say "take the Remagen one" and join. No server is needed for
this.

### SP and coop safety

- Contract widgets live in a coop file (`hzm_newgame3d.urc`), so they name only `ui_ops*` cvars and the
  legal `ui/coop_mpmenu/` path token (clause 7).
- They do not touch the `coop_spdone*` locks or `ui_ngMode`.
- DEPLOY always goes through `ui_startdmmap`, never `map` or `devmap`, so the SP path cannot trigger.
- The coop `start_server.cfg` already zeroes the bot cvars and restores speed (bugs 2629 and 2630).
- Coop runs no playerbots, so a leftover `bot_aim*` tier could never touch coop. `ops/restore.cfg`
  keeps it out of ordinary MP hosting too.

---

## 3. Bots: what exists and its limits

| Fact | Source |
|---|---|
| Native OpenMOHAA playerbots, with Recast navigation **baked at map load** for any MP map. No pathnodes are needed. | `mp_bots.scr` header |
| `sv_maxbots` is latched and acts as the slot ceiling and the nav gate. `sv_numbots` is the live count. HZM backfills against human count, capped at 12 by `coop_mpBotMax`. | `mp_bots.scr` |
| Tuned combat AI: cover, flanks, breaching, grenades, bandaging, aim convergence (80+ `bot_*` cvars). | `CVARS_ENGINE.md` |
| Objective *movement*: `hzm_attractnode` ATTACK/DEFEND bands, used in KOTH, Domination, Push, CTF, Demolition and Base Assault. | `mp_botobj.scr`, `mp_botdirector.scr` |
| **Bots never press USE, so they cannot plant or defuse.** USE is pressed only to bandage. | `playerbot.cpp:962`; `mp_demolition.scr:26` "Bots never press [USE]" |
| **No single skill cvar.** Difficulty is a preset of `bot_aimSpread`, `bot_aimConvMs`, `bot_aimAngErr`, `bot_aimTurnMax` and `bot_fov_acquire*`. | `CVARS_ENGINE.md` |
| **On stock MP maps, bots have only been seen on `dm/mohdm1` and `dm/mohdm6`** (the damage test). The large soaks were Push on campaign arenas. | SOURCE_OF_TRUTH; `bot_soak.ps1` |

**Plan:**
1. **TDM first.**
2. Then **OBJ with the "you are the sapper" rule.** The human is always on the planting side. Enemy bots
   hold DEFEND nodes seeded on the stock bomb sites, and friendly bots escort through the ATTACK band.
   You win by planting or by elimination. Stock gt4 has no respawns.
3. Phase 3 (engine): bots hold USE at a node flagged `plant`. That allows bot attackers, contracts where
   the human defends, and TOW and LIB.

**Skill tiers** (values tuned in Phase 0):

| Tier | Settings |
|---|---|
| RECRUIT | spread 1.6, conv 2600 ms, angErr 1.8 |
| REGULAR | defaults: 1.0 / 1800 / 1.1 |
| VETERAN | 0.8 / 1300 / 0.8 |
| ELITE | 0.6 / 1000 / 0.6, and never also Hardcore |

**Bots:** 5 to 15, odd numbers, sized by map. **MVP modifiers** use existing host knobs only:
- Hardcore (`coop_mpHardcore`)
- Rifles / Snipers presets (`coop_mpPreset`)
- Storm (`coop_mpWeather`)

Low Ammo comes later. Night needs per-map lighting, so it is out of the MVP.

---

## 4. Locations: every installed MP map, with evidence

### Method

**1. Primary: the game's own data**, extracted from the installed pk3s (`main`, `mainta`, `maintt`;
stock paks only, the mod's overrides excluded):
- **ws** = the BSP worldspawn `message`
- **ld** = `ui/loading_<map>.urc` title
- **loc** = `global/localization.txt`
- **scr** = `maps/<map>.scr` header comment and scoreboard text
- **obj** = `g_obj_*` objective text
- **tex** = BSP texture and sky names
- **mdl** = static models in the BSP
- **rm** = `Readme_patch_2.40.txt`

**2. Secondary references.**
- There are no AA/SH/BT PC manuals under `D:\LaunchBox\Manuals` (only console MOH titles), and none in
  the GOG folder apart from the readmes, which were grepped.
- Web lookups: the MOH Fandom wiki returned HTTP 402 and StrategyWiki returned 403. The Pingperfect
  and gamehostbros map lists name the files but give no settings. So the secondary evidence used here is
  limited to Wikipedia's coordinates for Monte Battaglia.
- **Nothing below rests on a web claim alone.**

**3. Coordinates** are the named town or landmark itself: the bridge, the abbey, the Casbah, the beach
sector. They are not the country.

**4. Confidence.**
- **high**: the game names a real place.
- **medium**: the game names a country or region, or the town is inferred from strong in-map evidence.
- **approx**: the map is fictional or unnamed. These are drawn as a dashed area, labelled "Somewhere in
  ...", and the reason for the pin is stated.

### The table

The pins in `ops_locations.json` are the coordinates below.

| Map | Modes | In-game name | Real place | lat, lon | Evidence | Conf |
|---|---|---|---|---|---|---|
| dm/mohdm1 | TDM | Southern France | Provence coast, Dragoon landing area | 43.27, 6.64 | ws "South France"; ld/loc/scr "SOUTHERN FRANCE". Region only; Dragoon was the only Allied fighting there. | approx |
| dm/mohdm2 | TDM | Destroyed Village | Somewhere in Normandy | 49.10, -0.55 | ws/ld/scr give no place; tex `brest/nrmndywlset_1a` (stock Normandy wall set) | approx |
| dm/mohdm3 | TDM | Remagen | Ludendorff Bridge, Remagen, Germany | 50.5794, 7.2440 | ld + loc "Remagen - dm/mohdm3"; scr "REMAGEN"; tex `remagenchurchrail` | high |
| dm/mohdm4 | TDM | The Crossroads | Somewhere in France | 45.3, 2.6 | ld/loc/scoreboard "The Crossroads"; scr header "THE BRIDGE" (built from obj_team4); tex `french/sign_back`. Pinned in the Massif Central, the nearest clear spot (the Bastogne tag covers north-central France) | approx |
| dm/mohdm5 | TDM | Snowy Park | Somewhere in Germany, winter | 50.3, 9.6 | ld/loc/scr give no place; tex `central_europe_winter/*`, `frozenriver`. No national cue. **User to confirm the theatre.** | approx |
| dm/mohdm6 | TDM | Stalingrad | Stalingrad (Volgograd), USSR | 48.7080, 44.5133 | ws/ld/loc/scr "STALINGRAD". Off the wall's east edge, so shown as an edge tab | high |
| dm/mohdm7 | TDM | Algiers | Casbah of Algiers, Algeria | 36.7850, 3.0600 | ld + loc "Algiers - dm/mohdm7"; scr header "NORTH AFRIKA", scoreboard "Algiers"; tex `afrika_map1`, casbah set | high |
| obj/obj_team1 | OBJ, TDM | The Hunt | Somewhere in Normandy | 48.95, -0.95 | ld/scr "THE HUNT"; obj "Find and destroy the Flak 88"; tex `nrmndywlset_2a` | approx |
| obj/obj_team2 | OBJ, TDM | V2 Rocket Facility | Somewhere in Germany | 51.6, 11.2 | ld "V2 Rocket Facility"; scr "V2 FACILITY"; obj "Destroy the Control Room / V2 Rocket"; mdl nazi banner. Peenemunde rejected: it is not named, and real V-2 field sites were in France and the Netherlands | approx |
| obj/obj_team3 | OBJ, TDM | Omaha Beach | Omaha Beach, Colleville sector, Normandy | 49.369, -0.871 | ws + ld "Omaha Beach"; scr "OMAHA BEACH OBJECTIVE DM"; obj "Breach the shingle / Destroy two 15cm cannons". Wraps campaign pin aa3 | high |
| obj/obj_team4 | OBJ, TDM | The Bridge | Somewhere in France | 45.3, 2.6 | ld/scr "THE BRIDGE"; obj "Place an explosive under the bridge"; tex French set (shared with mohdm4). Shares the France slot. **User to confirm.** | approx |
| dm/mp_bahnhof_dm | TDM | Bahnhof | Somewhere in Normandy (a station) | 49.25, -0.25 | ld/scoreboard "Bahnhof"; **mdl `signpost_stlo`**, whose boards read Rouen / Paris / Londres / Le Mans / Rosel (texture inspected), i.e. a Normandy crossroads near Caen. It is a reused stock asset, hence approx | approx |
| dm/mp_bazaar_dm | TDM | Bazaar | Somewhere in North Africa | 35.4, 5.6 | ld/scr "Bazaar"; tex stock `algiers/*` casbah and mosaic set; no city named | approx |
| dm/mp_brest_dm | TDM | Brest | Brest, Brittany, France | 48.390, -4.486 | ld + scr header + scoreboard "Brest"; tex `brest/*`. ws says "The Bridge", most likely left over from its source map; the game's own name wins. Wraps campaign pin aa5 | high |
| dm/mp_gewitter_dm | TDM | Gewitter | Somewhere in Germany | 49.6, 8.6 | ld/scoreboard "Gewitter" (thunderstorm), "Contest Winner by Rungsi"; runs `global/weather.scr` | approx |
| dm/mp_holland_dm | TDM | Holland | the Netherlands, pinned at Arnhem | 51.98, 5.90 | ld + scr + scoreboard "Holland"; tex `taholland/hollandroof`. The country is certain. Arnhem is the Spearhead-era (Market Garden) choice, drawn as an area | medium |
| dm/mp_malta_dm | TDM | Malta | Valletta, Malta | 35.8989, 14.5146 | ld/scoreboard "Malta"; sky `malta`; **mdl `maltasign`/`maltasign2`**, British pub signs "Three Crowns" and "Wild Goose" | medium |
| dm/mp_stadt_dm | TDM | Stadt | Somewhere in Germany | 51.3, 7.9 | ld/scoreboard "Stadt" (town), "Contest Winner by Surgeon" | approx |
| dm/mp_unterseite_dm | TDM | Unterseite | Somewhere in Germany | 52.3, 10.5 | ld/scr/scoreboard "Unterseite", "Contest Winner by EraserX" | approx |
| dm/mp_verschneit_dm | TDM | Verschneit | Somewhere in Germany, winter | 50.5, 12.4 | ld/scoreboard "Verschneit" (snowed-in); tex winter `tavernsign` | approx |
| obj/mp_ardennes_tow | TOW, TDM | Ardennes | the Ardennes, Belgium | 50.25, 5.95 | ld "Ardennes"; sky `ardennes`, `taardennes/ardennes_crater`; obj "Control the Flak88". Region, drawn as an area NE of the Bastogne pin (sh2) | medium |
| obj/mp_berlin_tow | TOW, TDM | Berlin | Berlin, Germany | 52.520, 13.405 | ld + scr "MP_Berlin_TOW"; tex `ta_berlin/*`; obj "Control Radar Dish". Wraps campaign pin sh3 | high |
| obj/mp_druckkammern_tow | TOW, TDM | Druckkammern | a German U-boat pen, pinned at Hamburg-Finkenwerder | 53.54, 9.87 | ld "Druckkammern"; obj "Disengage U-Boat Clamps / Open Pen Doors / Steal U-Boat"; **tex `misc_outside/subpen_water2`**. The pen is not named; the German name puts it on the German coast (Fink II). Trondheim is the AA campaign's pen | approx |
| obj/mp_flughafen_tow | TOW, TDM | Flughafen | a German airfield | 50.9, 6.9 | ws + ld "Flughafen"; sky `flughafen`; obj "Open Hangar Doors / Runway Lights / Axis Motorpool". Not named; Rhineland, the 1945 front | approx |
| obj/mp_bologna_obj | OBJ, TDM | Bologna | Bologna, Italy | 44.4938, 11.3426 | ws + ld "Bologna"; scr "MP_Bologna_OBJ"; sky `bologna` | high |
| obj/mp_castello_obj | OBJ, TDM | Castello | Somewhere in Italy, winter mountains | 43.6, 11.9 | ws + ld "Castello" (castle); scr comment "snow"; tex `german_sign_halt_rust`. A snowbound Italian castle fits the Apennines in winter 1944-45 | approx |
| obj/mp_palermo_obj | OBJ, TDM | Palermo | Palermo, Sicily | 38.1157, 13.3615 | ld + scr "MP_Palermo_OBJ", scoreboard "Palermo"; sky `palermo`; rm "Palermo's Objective mode..." | high |
| obj/mp_bizertefort_obj | OBJ, TDM | Bizerte Festung | old fortress by the canal, Bizerte, Tunisia | 37.2760, 9.8680 | ws "Bizerte"; ld "Bizerte Festung"; rm "Bizerte Fortress ... the gem of Tunisia ... the streets near the canal ... the ancient fortress" | high |
| obj/mp_kasserine_tow | TOW, TDM | Kasserine | Kasserine Pass, Tunisia | 35.25, 8.73 | ld + scr "MP_Kasserine_TOW"; sky `kasserinetow`; `afka_terrain` cliffs. Beside campaign pin bt1 | high |
| obj/mp_montebattaglia_tow | TOW, TDM | Monte Battaglia | summit of Monte Battaglia, Casola Valsenio | 44.2181, 11.5797 | ld + scr + scoreboard "Monte Battaglia"; tex `it_terrain/battaglia*`. Summit 44 13 05 N 11 34 47 E (Wikipedia, Battle of Monte Battaglia) | high |
| obj/mp_montecassino_tow | TOW, TDM | Monte Cassino | Monte Cassino abbey, Italy | 41.4903, 13.8139 | ld + scr + scoreboard "Monte Cassino"; sky `cassino`. Wraps campaign pin bt3 | high |
| lib/mp_anzio_lib | LIB, TDM | Anzio | Anzio beachhead, Italy | 41.4475, 12.6286 | ld + scr "ANZIO"; `water_anzio`, `anziobeachsky`; rm "Anzio Beach" | high |
| lib/mp_bizerteharbor_lib | LIB, TDM | Bizerte | Bizerte harbour, Tunisia | 37.2680, 9.8820 | ld "Bizerte"; scr "BIZERTE HARBOR"; sky `bizerte`. Shares the Bizerte slot | high |
| lib/mp_ship_lib | LIB, TDM | Stuckguter | a German cargo ship in Bizerte harbour | 37.2680, 9.8820 | **ws "Tunisia - Bizerte Harbor"**; ld "Stuckguter"; rm "a German cargo ship, is being raided"; the ship itself is fictional | high |
| lib/mp_tunisia_lib | LIB, TDM | Tunisia | the Tunisian desert, central steppe | 34.4, 9.3 | ws "Tunisian Desert"; ld + scr "TUNISIA". The country is certain; drawn as an area | medium |

**Totals:** 15 high, 4 medium, 16 approx.

**What a playtest could firm up.** Two maps were not inspected inside their BSP for signage text beyond
static-model and texture names: Snowy Park and The Bridge. A look in game at any visible signs in the
"approx" maps would upgrade them. That is a user check, per the rule "the user checks maps in game".

**Side findings (not fixed, plan-only session):**
- `ui/coop_mpmenu.urc:445` labels `dm/mohdm3` as "Algiers". The game calls it **Remagen**.
- `:448` labels `dm/mohdm7` as "The Hunt". The game calls it **Algiers**; The Hunt is `obj/obj_team1`.
- `:450` lists `dm/mp_castello_dm`, which has no BSP installed.
- Loading screens and scripts exist for `mp_streetsofmessina_tow`, `mp_thunder_dm` and `dm/mp_palermo_dm`,
  but none of their BSPs is installed, so they are excluded.

**MVP pool (TDM, 8 maps, all high or medium, and spread across the map):** Remagen, Stalingrad (edge
tab), Algiers, Brest, Malta, Berlin, Monte Cassino, Bologna.

**Phase 2 OBJ pool:** Omaha Beach, Bologna, Palermo, Bizerte Festung, The Hunt, V2 Rocket Facility,
The Bridge and Castello, each after it passes the Phase 0 sweep.

---

## 5. Mockups and their QA

- **`mock_newgame.png`** is the real `warmap.wall_view()` render. It has the campaign pins, the
  `overlay()` leaders and legend, and the three proposed tag nudges.
  - Campaign tags are drawn as plain slips in campaign colours; the in-game ones are the
    `make_ng3campaigns.py` textures.
  - The example roll: Remagen TDM (storm), Bologna OBJ (0:43 left, red ring), Omaha OBJ (wraps aa3),
    Malta TDM (hovered), "Somewhere in Germany" TDM (Verschneit, dashed area), and Stalingrad (edge tab).
  - The Remagen card is open, with a grease-pencil leader to its pin.
- **`mock_card.png`** is the card at 2x.
- **QA was checked by eye on both images:**
  - The type is clean: Prestige Elite and Courier Bold, no missing glyphs. The degree sign is avoided.
  - No stamp sits on a tag, pin or printed name.
  - The hover slip clears the tags.
  - The layout check reports 35 locations, 1 off-wall (Stalingrad), and 0 problems.

---

## 6. Technical approach

### Almost all of it is UI and generated

The NEW GAME tags are already `scenelabel` Labels and Buttons gated by `enabledcvar`, with
`hovercommand "set ui_scene_hot N"`. Contracts copy that pattern exactly. Every location is a fixed point
on the wall, so **no new scene/render code is needed**.

**`gen_ops.py`** (new) reads `ops_locations.json` and emits:
1. The NEW GAME **contract widgets**, appended to `hzm_newgame3d.urc` by `make_ng3campaigns.py`. Per
   location slot:
   - a loop Label (solid or dashed shader, pulsing `alphaGen wave`)
   - 8 ring-state Labels, gated `ui_opsR<slot>==k`
   - TDM and OBJ stamp Labels at the slot's layout-pass spot
   - a hover-slip Label with three `linkcvar` lines
   - a click Button that stuffs `hzm_ops card <slot>`

   All of them are gated on `ui_ops<slot>==1`, never on locks. Count: about 34 slots x 13 widgets, which
   is generated output of the same kind as today's 3,136-line file.
2. The same set for **`hzm_ngflat.urc`**, projected into its flat map rect. Feasible: it is a plain 2D
   map with Buttons.
3. The `ui/coop_mpmenu/ops/*.cfg` families.
4. `cl_hzm_ops_table.h`.
5. The layout QA, which fails the build if any slot loses its stamp spot or sits under a tag.

**`code/client/cl_hzm_ops.cpp`** (new, roughly 300 lines, and the only engine code):
- the time-slot generator
- writes the `ui_ops*` cvars once a second while NEW GAME is open
- `hzm_ops card|deploy|close`
- the intermission return watcher

**`ui/hzm_ops_card.urc`:** the card, with `linkcvar` labels and the DEPLOY and FILE AWAY stamp buttons.

**`coop_mod/mp_ops.scr`** plus one seam line in `mp.scr`, and an entry in `MP_MANIFEST`. Then run
`check_mp_isolation.py` and its selftest.

**`missions.json`:** the three tag nudges (decision 1).

### Phases

| Phase | Scope | Effort |
|---|---|---|
| **0. Sweep** | Dedicated harness, **one map at a time** (quiet testing): 35 maps under gt2 with 10 bots for 3 min each, recording nav built, bots spawned, kills both ways and stuck share. Then the 8 gt4 maps, boot and round only. Fix the three menu label bugs. | 0.5-1 day, mostly unattended |
| **1. MVP** | `gen_ops.py`, `cl_hzm_ops.cpp`, the card, `mp_ops.scr`, the tag nudges. **TDM vs bots on the 8 MVP maps, on both NEW GAME screens.** | 3 days |
| **2. OBJ + flavour** | gt4 sapper contracts; modifiers; MP challenge ribbon; Radio-it-in. | 2-3 days |
| **3. Optional** | Bots plant and defuse (engine); TOW and LIB; HZM bot-aware modes (KOTH, Domination, CTF) as "objective" contracts; Push campaign-arena contracts. | 3-5 days |

### Risks

- **Bots on stock maps:** only 2 of 35 have been seen with bots. Phase 0 checks the rest, and failing
  maps never roll.
- **Cvar leaks:** handled by one-shot consumption plus `restore.cfg`. Check with a coop boot right after
  an ops match.
- **Stock gt4 with bots:** unverified.
- **Tag nudges:** they change a screen the user signed off. That is why it is decision 1.
- **NEW GAME widget count:** a large but generated urc. Check the menu's load time.
- **Approx theatres:** need user confirmation, especially Snowy Park and The Bridge.

---

## 7. Decisions for the user

1. **Tag nudges.** Move the three Breakthrough tags (bt3 north to the Adriatic head, bt2 one degree east,
   bt1 into the sea north of Tunisia) so contracts at Bologna, Monte Battaglia, Castello, Malta and
   Tunisia are visible. This is recommended. The alternative is to keep the tags and accept that those
   contracts hide under them.
2. **Objective with bots.** MVP = TDM, then OBJ with the "you are the sapper" rule (recommended).
   Alternatives:
   - about 2 days of engine work first, so bots plant and defuse
   - use HZM's bot-aware modes (KOTH, Domination, CTF) as the "objective" contracts
3. **Shared world plus XP.** Seed contracts from UTC, so everyone sees the same map and friends can
   coordinate (recommended), or roll per player. Also: should completed contracts pay a bonus into the
   Service Record through the capped `xp_award_mp` bridge?

Smaller questions:
- Confirm the approx theatres, especially Snowy Park and The Bridge.
- Are the 8 MVP maps the right pool?
- Should the Radio-it-in public toggle be in v1?
