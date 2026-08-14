# Cut and unused retail content — research findings

**Status: RESEARCH ONLY. No code, script or asset changes were made from any of this.**
Nothing here is wired up, restored or scheduled. It is a survey of what still ships inside the
retail data, recorded so it is not lost in agent transcripts.

Produced 2026-08-11 by four independent research agents plus direct verification. Everything is
labelled by how strongly it is evidenced — read the label before acting on the claim.

| label | means |
|---|---|
| **VERIFIED HERE** | checked directly against the retail pk3s during this session, in this repo |
| **VERIFIED (agent)** | an agent checked it against retail data and showed its working; not re-checked here |
| **PARTIAL** | evidence is suggestive but incomplete, or the sweep that found it has known blind spots |
| **DOCUMENTED** | a public source states it; not confirmed in data |

Retail paths below are relative to `G:\GOG\Medal of Honor - Allied Assault War Chest\`.

---

## ⚠️ Security: tcrf.net serves a prompt-injection payload to automated fetchers

**Three separate agents independently hit this.** Fetching `tcrf.net/Medal_of_Honor:_Allied_Assault`
(both the article and `?action=raw`) returned, instead of article text, a block of instructions
addressed to AI agents: demands to write files (one variant asked for an EICAR antivirus test
string), a fake financial-transfer instruction, fake system/shutdown codes, and text directing the
assistant to insult the operator and tell the user to press Alt+F4.

**No agent acted on any of it, and no TCRF page content was used in this document.** The handful of
TCRF facts referenced below arrived via search-engine snippets only.

Ordinary search snippets of the same URL return real article text, so this looks like an
anti-scraper honeypot served on user-agent. **Treat automated fetches of tcrf.net as untrusted
input.** If TCRF is needed, read it in a browser by hand.

Two lesser access notes: `medalofhonor.fandom.com` returns HTTP 402 to plain fetchers (readable via
its MediaWiki API or a real browser), and `web.archive.org` and `strategywiki.org` were blocked.

---

## Corrections — read these first

These matter more than the finds, because each one is a belief this project currently holds that is
wrong, or a trap the next researcher would fall into.

### e2l1 is Sicily, not Crete
`hzm-mohaa-coop-mod/ui/coop_start/e2.cfg` reads `"2 Sicily, Operation Husky"`, and the Breakthrough
mission list is Kasserine/Torch (e1), Sicily/Husky (e2), Cassino-Anzio-Battaglia (e3). There is **no
Crete level in Breakthrough**. A memory file is named `e2l1_crete_overhaul.md`; whatever it
describes, the "Crete" label is wrong and will mislead. **VERIFIED HERE** (cfg text).

### The Spearhead t2l3 gag scripts are already restored in this mod
An agent reported `gags/t2l3_medic.scr`, `t2l3_blitzkrieg.scr`, `t2l3_soldiers_run_and_die.scr`,
`t2l3_friendly.scr`, `t2l3_soldiers_trench_dash.scr` and `T3L2_BattleTanks.scr` as ~1,962 lines of
inert cut content. That is true **of retail** and false of this mod: `maps/t2l3.scr` execs
`t2l3_soldiers_run_and_die`, `t2l3_blitzkrieg::BarrageInit`, `t2l3_medic::t2l3_sarg_think`,
`t2l3_medic::medic_start` and `t2l3_soldiers_trench_dash::cue_trench_dash`. Our `t2l3_medic.scr` is
19,926 bytes against retail's 17,032 — already extended. Only the `trench_dash` *init* is still
commented (t2l3.scr:74), though its cue fires at :358. **VERIFIED HERE.**

Same applies to `m4l0` (Farm House) and `training.scr` — both already coop-integrated here.

### `GT_CTF` / `GT_OBELISK` / `GT_HARVESTER` are NOT a cut MOHAA mode
They appear in `openmohaa-hzm/code/botlib/be_ai_goal.c` — inherited **Quake III Arena bot code**
from the id Tech 3 base. The real gametype enum (`bg_public.h`) is contiguous
`GT_SINGLE_PLAYER..GT_LIBERATION` with no gaps, and the shipped `callvote.cfg` files agree.
**There is no hidden gametype.** **VERIFIED (agent), both sides.**

### openmohaa is a reimplementation — check retail DLLs before calling anything "cut"
Several classes and script commands exist in `openmohaa-hzm/code/` but **not** in the retail
`gamex86.dll`, so they are additions, not cut retail content. Confirmed openmohaa-only:
`info_grav_pathnode`, `script_drivablevehicle`, `gravpath_create`, `deletespawn`, `keepspawn`,
`blastshield`, `viewmodelprefix`, `ignorewalls`, and everything named `coop_*` / `nav_*` / `fs_*`.
The `script_aimedstrafinggunfire` / `projectilegenerator` / `throbbingbox_explodenebelwerfer` family
is Spearhead-and-later only, absent from `main\gamex86.dll`.

### Two sweep false-positive classes worth knowing
- `models/player/*_fps.tik` are derived at runtime (the `_fps` suffix is in all six retail DLLs), so
  they look unreferenced and are not.
- `*_sml.bsp` low-detail variants look unused; the engine appends `_sml` at runtime.
- `localization.txt` stores key-hint strings as fragments split around `&&&` substitution, so
  exact-match testing wrongly reports them missing. This produced three retracted "cut mechanic"
  claims (a tutorial, a compass ball-bearing mechanic, a stealth takedown) — all are in
  `training.scr`.

---

## Verified here, during this session

Six claims were re-checked directly against the retail pk3s.

### 1. m1l2a's Flak 88 objective chain is still placed in the shipped map
The most restorable item found. `m1l2a.bsp` still contains:

| entity | class | origin |
|---|---|---|
| `flak88b` | `turretweapon_german_88mmflakturret` | `-891 -3431 -264` |
| `explosives100` | `script_model` | `723.75 -675.78 -54` |
| (unnamed) | `trigger_useonce` | `1993 3044 -481` |

Live script **hides** them — `m1l2a.scr:101-102` is `$explosives100 hide` / `notsolid` — and the
objectives sit commented at `:438-439` (*"Use explosives to escape."*, *"Use explosives to destroy a
Flak88."*). Line 530 still references `$explosives100.origin` in live code, and
`global/savenames.scr:83` still defines the autosave as **"Destroying Flak 88s"**.
**VERIFIED HERE** (entity dump + script).

### 2. `obj_capture.scr` — a complete cut multiplayer mode
`mainta\pak1.pk3 :: global/obj_capture.scr`, 3,451 bytes / 140 lines, header
`// LOGIC FOR King of The Hill/Capture and Hold ENTITIES // by Z`. Contains neutral/allies/axis flag
swapping, `controlling_team`, per-team accrual (`allies_time` / `axis_time`), `win_time`, `teamwin`,
and a `locprint` HUD readout. **Referenced by nothing** in retail or in this mod. Breakthrough
dropped the file entirely. **VERIFIED HERE** (size, content markers, zero references).

### 3. A multi-seat vehicle scripting API that no shipped level calls
`openmohaa-hzm/code/fgame/vehicle.cpp` registers `QueryFreeDriverSlot`, `QueryFreePassengerSlot`,
`QueryFreeTurretSlot` and their `...SlotPosition` / `...SlotAngles` / `...SlotStatus` siblings, plus
`steerinplace`, `undrivable`, `seatanglesoffset`, `setweapon`, `showweapon`. An agent confirmed the
strings are in the **retail** DLLs. Nothing in retail or this mod calls them.

**Directly relevant to the tank-MG-gunner prototype and the `DetachTurretSlot` semantics work** —
this appears to be the API those features were meant to use. **VERIFIED HERE** (present in
vehicle.cpp, zero callers here).

### 4. Three unused drivable-vehicle physics classes
`VehicleHalfTrack`, `VehicleWheelsX2` (motorcycle), `VehicleWheelsX4` (car/jeep) — registered in
retail `main`+`mainta`+`maintt` DLLs, and bound by **zero** shipped `.tik`. Plus
`DrivableVehicleTandem` (two-seat crewed), Breakthrough-only, also unbound. Every shipped vehicle
falls back to generic `DrivableVehicle` or `VehicleTank`. Sources exist in
`openmohaa-hzm/code/fgame/`. **VERIFIED HERE** (sources) **+ (agent)** (retail DLL strings, tik binding counts).

Related and **DOCUMENTED**: drivable vehicles were cut from Breakthrough multiplayer for time — TKO's
Jody Hicks, GameSpot Q&A: *"the drivable vehicle code, while functional, wasn't up to the standards
of Medal of Honor."* The machinery is live: `panzer_tank_drivable.tik` and
`panzer_cannon_drivable.tik` are precached by e1l1, e3l1 and e3l4.

### 5. Cut first-person viewmodels for emplaced guns
`mainta\pak1.pk3` ships `models/statweapons/p_flak88_viewmodel.tik` (1,666 b) and
`p_aa_viewmodel.tik` (1,662 b); Breakthrough adds `it_w_breda_gun_viewmodel.tik`. Their basenames
appear nowhere else in the shipped game. Evidence of a cut first-person view for player-operated
emplacements — this project already restored a *mannable* FLAK-88, which never had one.
**VERIFIED HERE** (present, sized).

### 6. FG42 — a fully tuned cut weapon
`mainta\pak1.pk3 :: models/weapons/FG42.tik`, 8,860 bytes, containing `bulletdamage`,
`bulletspread`, `firedelay`, `zoomspreadmult` and `rank` — i.e. play-balanced, not a stub. Mesh
(`fg42.skd`), animations, LOD and texture all ship. **DOCUMENTED** on the wiki as console-spawnable
with an invisible model and borrowed sounds/animations, so the gap is shader/skin wiring.
**VERIFIED HERE** (size, tuning keys present).

Also spot-confirmed present: `models/vehicles/p47.tik` (a **drivable** P-47, only `p47fly.tik` is
used), `models/miscobj/move_hedgehog.tik` (a pushable beach hedgehog — a cut D-Day
obstacle-clearing mechanic), and `models/vehicles/uboat.tik`.

---

## Verified by agents, not re-checked here

### Maps that ship but are unreachable
- **`MP_Malta_DM`** — a *finished* MP map: 11.9 MB BSP, script, precache, loading screen, its own
  texture tree, models, skybox, ambience hook and localisation entry. Present in **no**
  `maplist_*.cfg` and no `MENU.CFG` in any of the three games; appears only in `callvote.cfg`. One
  maplist line from being selectable. Found independently by two agents.
- **`maps/DM/MP_Palermo_DM.scr`** — a complete 1,586-byte DM map script credited to Jeff Zaring /
  Jason Abbott, with **no matching BSP**. Palermo shipped only as an OBJ map.
- **"Streets of Messina"** (Breakthrough) — precache script, a live `global/ambience.scr` hook, a
  loading shader and a complete loading screen titled *"Streets of Messina"*, but no BSP.
  **PARTIAL inference:** its precache script is byte-identical (3,652 b) to
  `MP_Palermo_OBJ_precache.scr`, which suggests Messina *became* Palermo — but byte-identity does
  not establish direction.
- **`obj_team5`** — `ui/loading_objdm5.urc` declares `menu "obj/obj_team5"` with loading art
  shipped; only `obj_team1..4` have BSPs.
- **`maps/briefing/briefingc1.bsp`** — an orphan briefing room, zero references anywhere.

### Cut objectives whose entities still exist
- **m3l1b (Omaha)** — four original objectives sit in a `/* */` block: destroy 2× 20mm AA, the FLAK
  88, the 15cm artillery, then rendezvous. Surviving in the BSP: `88mm_weapon1` / `88mm_weapon2`
  (`turretweapon_german_88mmflakturret` using the `15cmcannon.tik` model) each with an
  `88mm_explosive1/2` charge marker and `88mm_trigger1/2`, referenced by no script. Deleted from the
  BSP: the 20mm guns, the rendezvous point, and the FLAK 88 gunnery crew — whose firing animations
  are still in the script. ~200 further commented lines carry an unfinished ending with placeholder
  VO text.
- **e3l4 "Escape the Castle"** — objective id, text, fail message, a dedicated `Escape.scr`, a
  dynamic waypoint loop and live calls all ship. Third-party *War Chest Restored v1.1* already
  restored it, which proves it works.
- **e1l1 "limpers"** — three wounded soldiers with dedicated animations, commented out with
  `// dhs 7/2/3 limpers disabled for the moment`, but **line 814 still live** referencing
  `$scene1_limper_2.origin`, so the entities remain in the BSP.
- **e2l3 C-47 paradrop** — `maps/e2l3/AirDrop.scr` complete, with all its entities (`c47`,
  `c47_path`, `c47_dropper_1/2/3`, `c47_dude1/2/3`) confirmed present in `e2l3.bsp`.
- **m1l1 MG42 last stand** — `$mg42` is a real turret in the BSP, spawners exist, and the
  `rearguys:` handler is live code; only the objectives and 3 of 4 `alarmspawn` calls are commented.
- **m2l2a torpedo-cart set-piece** — ~70 commented lines staging three crewmen pushing a torpedo
  cart through the pens. **The entities were stripped from the shipped BSP**; only `gate3` survives.
  Restoring this needs new entities, unlike the items above.

### Cut items — seven fully-coded, never granted
`global/items.scr` defines 20 items; seven are granted by no level: `camera` (spy camera),
`battery`, `radar_blueprints`, `radar_notes`, `uboat_blueprints`, `uboat_notes`, `stg44_blueprints`.
The four document items have HUD shaders pointing at TGAs that **do not ship** (cut early); `camera`
and `battery` have complete art.

**The spy camera was more than a model:** `textures/hud/cameraoverlay.tga` (262 KB) is a full-screen
viewfinder with a working shader, referenced by nothing, and `sound/items/camerapic.wav` is
precached by **m3l2** — a level outside Norway. `m2l1.scr:48` has `//$player item items/camera.tik`
commented out. Ties to m2l1's cut *"Steal all Research Documents"* objective, whose four
`naxosplans1-4.tik` models ship with unique textures and whose live code still sets
`level.remaining_documents = 4`.

Two more sit in `global/inventory.txt` with models but no handler: **Bratwurst** (joke item) and a
**Flare Gun**.

### Unused entity classes and mechanics
An exhaustive sweep (160 BSPs, 2,827 tiks, 1,646 text files, cross-checked against retail DLL string
tables) found **55 classnames registered by the retail engine that no shipped level uses**. The
coherent groups:

- **The entire `useanim` interaction family** — `func_useanim`, `func_useanimdest`, `func_touchanim`,
  `func_useobject`, with events `finishuseanim`, `startuseobject`, `attachtoladder`, `tweakladderpos`.
- **The entire runtime-spawner family** — `func_spawn`, `func_respawn`, `func_randomspawn`,
  `func_spawnchain`, `func_spawnoutofsight`, `func_remove`. Every shipped AI is pre-placed instead.
- **FAKK2 traversal leftovers** — `func_monkeybars`, `func_horizontalpipe`, `func_fulcrum`,
  `func_runthrough`, `func_sinkobject`, `func_fallingrock`, `plant_puffdaddy`.
- **Teleporters / jump pads / powerups / secrets** — `trigger_teleport`, `func_teleportdest`,
  `trigger_push`, `trigger_pushany`, `trigger_givepowerup`, `trigger_secret`.
- Misc: `func_beam`, `func_emitter`, `func_explodingwall`, `func_multi_exploder`, `trigger_music`,
  `portal_camera`, `portal_surface`, `health_020`, `sound_randomspeaker`, `play_sound_triggered`.

Corroborating artifact: `main\Pak0.pk3 :: scripts/tempfakk.shader` still ships.

**Two genuinely broken classnames shipped in retail maps:** `info_array` (m1l2a, m5l3 — no `model`
key, so it fails `G_CallSpawn` at load) and `"classname" "crap"` in m3l2, a literal placeholder.

### Unused assets
- **Characters:** `german_misc_frogman` (a German combat diver — finished mesh, animation, dedicated
  shader, 1 MB body texture; fits the U-boat mission), `german_misc_kradshutzen` +
  `-afrika` (motorcycle troops, *with* MP player models — they were set up as a playable skin),
  `1st-ranger_lieutenant`, `1st-ranger_sergeant`, `2nd-ranger_sergeant`.
- **Vehicles:** `uboat.tik`, `higgins.tik` + `higginslite.tik`, `p47.tik`, `sdkfz_afrika.tik`,
  three European civilian cars, a grey delivery truck, `stuka_dsrt_fly.tik`, `panzer_tank2.tik`.
- **Emplacements:** `howitzer.tik` (and Omaha's cut objective called for a *"15cm Artillery
  emplacement"*), `20mmflak_w` + destroyed variant, `nebelwerfer_w`.
- **Weapons:** `mills_grenade_sp` (British Mills bomb, SP build), `russian_f1_grenade_sp` (Soviet
  F-1, SP build), `static_kar98`, `item_bar_weapon.tik` (a BAR pickup entity).
- **Skyboxes:** four complete unused 6-face sets in `main\Pak2.pk3 env/` — `afrikadusk2`, `bocdusk`,
  **`dday2a`** and **`ddaystormy`**. The last two are a *stormy Omaha* sky and are documented nowhere.
- **Documents:** eight `models/items/documents1a-1d, 2a-2d.tik` plus `papers_open` / `papers_open2`,
  referenced by no script and none of 88 SP entity dumps. m4l0's document objective instead uses a
  magazine model.
- **Dev leftovers:** `models/tests/` (22 prototype models), `scripts/mohtest.shader`,
  `global/spotlight_old.scr`, `music/mohpc_prototype.mus`, a raw `.map` source file, and a `dump/`
  directory in `maintt\pak1.pk3` containing `testemitter.txt`.

### A retail bug worth knowing
`main\Pak0.pk3 :: scripts/hud.shader` has the two papers HUD icons **swapped** —
`textures/hud/item_papers1` loads `item_papers2.tga` and vice versa. Level-1 papers display the
level-2 icon in every retail copy. Directly relevant to this project's papers work.
**VERIFIED (agent).**

### Cut medals
`ui/medals.urc` displays 9. Two medal textures ship referenced only by a shader definition and never
by any menu: `purpleheart_med.tga` and `europeanmedal.tga` (+ `_sign`). Base-game only — all six
expansion medals ship and are awarded.

---

## Documented but not confirmed in data

- **Remagen Bridge** — a cut SP mission (Powell captures the Ludendorff Bridge), seen in the trailer
  and E3 2001 footage. Surviving artifacts confirmed by an agent: `textures/german/jh_remagen2km.tga`
  (a road sign) and `textures/misc_outside/remagen_clifface1.jpg`.
- **A cut Tunisia mission** — leftovers confirmed: the `afrikadusk2` sky, `sdkfz_afrika.tik`, the cut
  EAME medal, and briefing photos `rommel.tga`, `afrika88s.tga`, `torch.tga`.
- **A cut European (bocage) mission** — only the `bocdusk` sky survives.
- **e1l2 Cpl. Vic** — listed on the wiki explicitly as cut; the player was to mark mines with flags
  and Vic would clear them. `US_V_MineClearing.tik` is real and referenced by e1l1/e1l2, and
  `trigger_landmine` is placed 33× across the expansions.
- **e2l2 Caltagirone** — two entirely different scenarios evidenced by shipped audio, including a
  control room from which Baker radios aircraft back.
- **e1l3** — a Tiger tank was to breach the fort, destroyed with a mortar; the wiki says the evidence
  is *"in game scripts"*, which makes `maps/e1l3/` worth a targeted read.
- **Spearhead has no disguise/infiltration at all** — an existing engine mechanic that no Spearhead
  level uses.
- **Beta**: an M1 Garand start on Omaha and a sprint mechanic absent from the final game (TCRF via
  snippet, unverified). A Nov 27 2001 demo build is archived at Hidden Palace — the obvious next
  step for beta comparison.

---

## Clean negatives — worth recording so nobody re-searches them

- **No cut gametype.** The enum is contiguous and the configs agree.
- **No cut SP levels survive as BSPs** in either expansion — `mainta` holds exactly t1l1–t3l2,
  `maintt` exactly e1l1–e3l4.
- **No unused Italian units or weapons.**
- **No unused AI think type.** All 38 appear in shipped entity data.
- **Fandom has essentially no cut-content coverage of any Spearhead level** — nine stub pages of
  bugs and historical nitpicks. The script and asset sweeps were far more productive there.
- **e3l3 Anzio, m1l3b, m1l3c, m2l2c, m2l3, m4l1, m4l2, and all of missions 5 and 6**: nothing found.
  One agent initially flagged a long list of commented objectives across m5l1a/m5l3/m6l2a/m6l2b/m6l3a
  and then **retracted it** — those objectives are live in retail; the commented copies are earlier
  drafts sitting beside the shipped versions.

---

## Known limits of this survey

- **Unused-asset sweeps are name-based.** Something referenced indirectly (through an emitter or
  shader chain resolved without a file extension) can evade them. The `static/`, `fx/`, `emitters/`
  and `animate/` categories are explicitly **PARTIAL** for this reason.
- **BSP entity dumps in this repo cover the 54 SP campaign maps only, not MP maps.** An asset placed
  only in an MP map can look unused. Two candidates were caught this way and removed
  (`2nd-ranger_sergeant.tik`, `stuka_dsrt_fly.tik` initially looked unused; the latter is placed in
  m1l3b, which also contradicts a wiki claim that the desert Stuka never appears).
- **Commented-out `add_objectives` calls are ambiguous** — the second argument is a *status*, so some
  commented lines are disabled status-updates rather than whole cut objectives. Only entries whose
  index assignment or first registration is also commented were promoted above.
- `docs/generated/filemap.tsv` indexes the workspace, not the retail data, so it is of no use for
  this kind of question.
