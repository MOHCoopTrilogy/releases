# Known Working State — HZM MOHAA Coop Extension
# Update this file at the START of every session before touching any code.
# Last updated: 2026-06-21 — Wave types 6+7 (AT team + dogs), officer skin pool, Wehrmacht path fix, radio chatter variety

## Process Rules
**BUILD RULE: Every source edit requires build.ps1 to deploy before testing. The game reads only the pk3, not source files. An expected new print not appearing in-game = pre-edit code is still running. Run: powershell -ExecutionPolicy Bypass -File C:\mohaa-coop-dev\build.ps1 after EVERY edit.**

**PARSE SAFETY: After every batch of .scr changes, run all three checks before building:**
1. BOM check: `$b=[IO.File]::ReadAllBytes("file.scr"); $b[0..3]` — first byte must NOT be 239 (0xEF). If it is, rewrite with -Encoding ASCII.
2. Bare negative check: `grep \(-[0-9] file.scr` — zero matches required. Pattern `(-N` is a parse killer; must be `( -N` with space.
3. Invalid command check: every new script command not in the prior working version must be confirmed in vanilla or HZM scripts before building.
**Build only after all three pass. A silent parse error kills the entire .scr file — no functions in it will execute.**

**SPAWN SYNTAX RULE: In MOHAA script, `spawn ClassName` takes NO inline keyvalue arguments. Do NOT write `spawn ClassName "key" "value"` or `spawn ClassName key "value"`. Set all properties afterward via assignment or commands:**
```
local.ent = spawn ClassName
local.ent.property = value
local.ent command arg
```
Violation caused two parse-killing sessions. Unquoted token after classname (e.g. `spawn SplinePath targetname "x"`) is also a kill.

1. Read this file and any transcript summary BEFORE touching any code.
2. Check Player-Confirmed Good Feels before every repack.
3. Check Known Limitations before attempting any fix — if it is listed there, do NOT attempt it again without a new confirmed solution.
4. Read current file state before editing — never rely on memory alone.
5. Confirm root cause with evidence before making any change.
6. One change at a time when debugging.
7. If a working feature breaks, identify exactly what changed since it last worked before touching anything.
8. Run Pre-Change Checklist before every edit.
9. Run Repack Verification Checklist before every pk3 repack.
10. A feature is only marked WORKING after the player explicitly confirms it in testing — not from code review alone.
11. After EVERY failed approach add an entry to Known Limitations IMMEDIATELY before trying the next approach. Do not wait until end of session.
12. After EVERY code change that is tested and confirmed broken add to Change Log with RESULT: FAILED and document why it failed.
13. After EVERY successful player confirmation update the feature status to WORKING immediately.
14. When a bug is fixed document the LESSON LEARNED in the Lessons Learned section immediately.
    Future features must check this section before implementation.
15. When a repack is ready always ask the player this exact question before repacking:
    "Ready to build and deploy? I can run build.ps1 to pack and copy everything automatically,
    or you can do it manually. Which do you prefer?"
    Wait for the answer before proceeding.
    If player says yes: run powershell -ExecutionPolicy Bypass -File C:\mohaa-coop-dev\build.ps1
    If player says no: provide manual instructions.

---

---

## Feature: Cover / Sandbag Placement System
Status: PLAYER CONFIRMED WORKING — COMPLETE
Last confirmed working: 2026-06-20
Key implementation:
  - coop_mod/cover.scr             — cover_place, cover_hud_monitor, cover_proximity_monitor, cover_remove
  - coop_mod/player.scr            — arrayIndex 9 dispatches to cover_place; manageAliveSpawning starts
                                     cover_hud_monitor and cover_proximity_monitor; spectator cleanup
                                     clears slots 40-44
  - coop_mod/dbno.scr              — dbno_start sets coop_cover_placements = 2 on every spawn
  - textures/hud/coop_cover_icon.tga — custom 32x32 RGBA TGA (sandy tan sandbag silhouette)
  - models/static/coop_sandbag.tik   — custom TIK referencing sandbag_link_main.skd at scale 0.52
  - ubersound/ubersound.scr          — coop_sandbag_place alias (body_falldirt_04.wav, item channel)
HUD slots used: 40 (icon shader), 41 (placement count), 42 (proximity hint "[RMB] Remove cover"),
                43 (removal progress bar bg), 44 (removal progress bar fill)
Model: models/static/coop_sandbag.tik (sandbag_link_main.skd, scale 0.52, path models/static/sandbags)
  SKD source: main/Pak0.pk3 — base AA game assets accessible from maintt context
Angles: bagangles[1] = player yaw only. No pitch correction. No yaw offset.
  Model stands upright at default orientation (0 0 0) — long axis perpendicular to player view.
Collision: single script_object box from authoritative .map clip brush data:
  col1.origin = hitpos (same as visual model, no offset)
  setsize ( -13 -52 0) (10 52 47) — matches original game clip brush exactly
  safesolid (not solid — delays if player is inside bounds on spawn)
  NOTE: SOLID_BBOX setsize does NOT rotate with entity angles (see Known Limitations).
  Full .map bounds covers correct footprint for all placement directions.
Sound: local.player playsound coop_sandbag_place fires on placement (thud feedback).
Owner stored as direct entity ref (level.coop_cover_owner_ent[slot] = local.player)
  — avoids entnum comparison and $player[] loop entirely
Confirmed behaviours:
  - Place sandbag: aim at floor within 200 units, press bind. WORKING.
  - Model appears upright, correct orientation. PLAYER CONFIRMED.
  - Collision blocks movement through wall. PLAYER CONFIRMED.
  - Placement thud sound fires on drop. WORKING.
  - HUD count decrements on place, increments on refund. WORKING.
  - Proximity hint "[RMB] Remove cover" shows within 80 units. WORKING.
  - Hold RMB 100 frames to remove: progress bar fills, sandbag deleted. WORKING.
  - Refund: "Sandbag refunded!" fires to owner on removal. WORKING.
  - DBNO blocks placement (coop_dbno_active guard). WORKING.
  - Floor-only placement guard (hitpos Z vs player origin Z + 32). WORKING.
Known limitations:
  - Placement count cap is 2 per player (hardcoded in dbno.scr and refund guard < 2).
  - SOLID_BBOX collision does not rotate — box is always world-axis-aligned regardless of
    entity angles. .map clip bounds work correctly at all angles for this model shape.

---

## Feature: Medkit System (Standing Heal + Self-Revive + HUD + Refill)
Status: PLAYER CONFIRMED WORKING — ALL PARTS
Last confirmed working: 2026-06-20
Key implementation:
  - coop_mod/medkit.scr             — medkit_use, medkit_hud_monitor, dbno_selfrevive, coop_scan_health_entities
  - coop_mod/dbno.scr               — dbno_start resets medkit flags; dbno_enter threads dbno_selfrevive;
                                       dbno_bleedout_timer pauses elapsed when coop_dbno_healing==1
  - coop_mod/player.scr             — arrayIndex 8 dispatches to medkit_use; manageAliveSpawning starts
                                       medkit_hud_monitor; spectator cleanup clears slots 33-39
  - coop_mod/main.scr               — threads coop_scan_health_entities on level start
  - ubersound.scr                   — coop_medkit_cloth, coop_exhale1/2, coop_dbno_call_01 through 06
  - coop_mod/variables.scr          — level.coop_healthDropFreq = 10
HUD slots used: 33 (text/revival msg), 34 (progress bg), 35 (progress fill), 36 (medkit icon shader),
                37 (medkit count), 38 (movement cancel msg — DBNO only), 39 (self-revive hint — DBNO only)
textures/hud/coop_medkit_icon.tga   — custom 32x32 RGBA TGA, position 5 -62 16 16 (above health bar)
Confirmed behaviours (2026-06-20):
  - Standing heal: full health restore (health level.coop_health). CONFIRMED PERFECT.
  - Self-revive: full health restore (health level.coop_health). CONFIRMED PERFECT.
  - HUD icon: position 5 -62 above health bar, count at 23 -60. CONFIRMED PERFECT.
  - Health pack refill: works both injured (delta path) and full health (timer scan, 5s). CONFIRMED WORKING.
  - Movement cancel: fires correctly on both standing heal and self-revive. CONFIRMED WORKING.
  - Cloth wrap sound + exhale on completion: CONFIRMED WORKING.
  - DBNO dialogue: randomized from 6-file pool (AMdfr_m_04/05). CONFIRMED WORKING.
  - Enemy drop frequency: reduced to every 10 kills (was 5). CONFIRMED WORKING.
  - Press medkit key while injured → progress bar fills over 5 seconds. CONFIRMED WORKING.
  - Moving during heal cancels silently. CONFIRMED WORKING.
  - Getting shot cancels with "Heal interrupted!" CONFIRMED WORKING.
  - "Already at full health" guard fires correctly. CONFIRMED WORKING.
  - "No medkits remaining" guard fires correctly. CONFIRMED WORKING.
  - Medkit count decrements and holds. CONFIRMED WORKING.
Known issues (cosmetic only):
  - M key bind: M is default MOHAA screenshot key, players must rebind (see Known Limitations)
  - RMB melee fires once on first right-click in DBNO (see Known Limitations)
  - managePlayerInventory + disguise missions: untested (see Known Limitations)

---

## Feature: Name-Append Keybind System
Status: WORKING
Last confirmed working: 2026-06-19
Key implementation:
  - variables.scr:125-140 — getNameAppendCommands, token prefix array (indices 0-14)
  - player.scr:492-521    — playerNameCommand dispatch (arrayIndex 0-14)
  - ui/BIND.SCR:37-51     — binditem entries (append name ,<token><data>)
Known conflicts:
  - Token in variables.scr MUST be a prefix of the bind string with at least 1 trailing character as data payload.
    playerExtract returns NIL if nothing follows the token — entire dispatch aborts silently.
  - MAX_NAME_LENGTH = 32 in OpenMoHAA. Total name + bind string must stay under 32 chars.
  - Token design rule: bind string = token + data. e.g. token=" ,7t" bind="append name ,7tp" → data="p".

---

## Feature: Third Person Camera
Status: PLAYER CONFIRMED WORKING — 2026-06-20
Last confirmed working: 2026-06-20
Key implementation:
  - thirdperson.scr:1-35    — coop_thirdperson_monitor (toggle loop, delegates to set3rdPerson)
  - thirdperson.scr:37-43   — coop_tp_toggle (sets coop_tp_toggleRequest flag + debug print)
  - player.scr:1080-1091    — set3rdPerson (HZM proven function: developer=1, changeGameType 0,
                               stufftext "set cg_3rd_person <0|1>", changeGameType 2, restore dev)
  - player.scr:514          — arrayIndex==7 dispatches to thirdperson.scr::coop_tp_toggle
  - ui/BIND.SCR:43          — binditem "Coop Third Person" "append name ,7tp"
  - variables.scr:134       — local.command["7"]=" ,7t"
Known conflicts:
  - set3rdPerson uses waitthread internally — monitor loop BLOCKS during each gametype switch.
    This is acceptable; the monitor is a dedicated per-player background thread.
  - set3rdPerson only sets cg_3rd_person, NOT cg_cameraverticaldisplacement.
    All displacement logic has been removed from thirdperson.scr.
  - changeGameType is serialized (concurrent calls queue and wait). If another system calls
    changeGameType simultaneously the toggle will be delayed until the other call finishes.
  - Direct stufftext "cg_3rd_person 1" (no "set" keyword) is BLOCKED by cg_servercmds_filter.
    set3rdPerson uses "set cg_3rd_person" form internally — correct.
  - sv_cheats approach abandoned: setcvar in scripts does not broadcast serverinfo updates
    to already-connected clients. setcvar "sv_cheats" "1" removed from variables.scr.
  - set3rdPerson gametype-switch trick confirmed NOT working in OpenMoHAA. The engine
    enforces CVAR_CHEAT independently of gametype. Requires an engine-level fix (fork).
  - console confirmed: "set3rdPerson: 1" fires correctly, immediately followed by
    "cg_3rd_person is cheat protected". The call chain is correct; the engine blocks the set.
  - set3rdPerson 0 console noise on death: FIXED (2026-06-19). thirdperson.scr cleanup block
    now guards with "if( local.tp_active == 1 )" before calling set3rdPerson 0.

---

## Feature: DBNO System (core)
Status: WORKING
Last confirmed working: 2026-06-19
Key implementation:
  - dbno.scr:1-28     — dbno_start (resets HUD, checks coop_dbno cvar, starts monitor)
  - dbno.scr:30-112   — dbno_monitor (health watch loop, triggers dbno_enter)
  - dbno.scr:115-163  — dbno_enter (sets DBNO state, starts all sub-threads)
  - dbno.scr:166-177  — dbno_bleedout_timer
  - dbno.scr:180-230  — dbno_fade_manager (screen darkens over time)
  - dbno.scr:290-309  — dbno_die (kills player on bleedout)
  - dbno.scr:437-494  — dbno_marker_manager (spinning medkit + red glow + HUD label for other players)
Player-confirmed behaviours (2026-06-19):
  - Movement penalty message fires once per episode (not per frame). WORKING.
Known conflicts:
  - Any runtime error in dbno_enter aborts the thread, preventing all sub-threads from starting.
    Previously: setspeed with invalid index 0 caused this. Fixed to index 1.
  - animation override files (anims_injured.txt, include.txt) caused crashes near explosions.
    Both renamed to .bak and EXCLUDED from pk3. Do not restore without crash testing.

---

## Feature: DBNO Speed Control
Status: WORKING — confirmed perfect by player
Last confirmed working: 2026-06-19
Key implementation:
  - models/weapons/dbno_pistol.tik — movementspeed 0.55 on all three modes (sp/dm/realism)
  - NO setspeed calls anywhere in dbno.scr — weapon movementspeed is the sole speed control
Known conflicts:
  - DO NOT add setspeed calls — they multiply with movementspeed and cause excessive slowness.
    History: setspeed 0.8 * movementspeed 0.3 = 24% effective speed (extremely slow).
  - DO NOT change movementspeed from 0.55 without explicit player approval (see Player-Confirmed Good Feels).
  - The weapon's movementspeed only applies while that weapon is equipped. DBNO pistol is
    force-equipped in dbno_enter, so this reliably applies throughout the DBNO state.

---

## Feature: DBNO E Key / USE Detection
Status: WORKING — player confirmed 2026-06-19
  - Tap E: medic callout WORKING
  - Hold E: let go (letgo_monitor) WORKING
Last confirmed working: 2026-06-19
Key implementation:
  - dbno.scr:370-398  — dbno_letgo_monitor polls self.useheld each frame
  - autoexec.cfg:4    — bind e "+use" (overrides omconfig.cfg's unbindall after it runs)
Known conflicts:
  - omconfig.cfg (%APPDATA%\openmohaa\maintt\configs\omconfig.cfg) starts with unbindall.
    This wipes ALL binds including +use. autoexec.cfg runs AFTER omconfig.cfg in Q3 startup
    sequence, so bind e "+use" in autoexec.cfg correctly re-establishes the bind each launch.
  - If omconfig.cfg is regenerated by the game (e.g., opening Options), it will write unbindall
    again but NOT write bind e "+use" (since that's from autoexec, not the in-game UI).
    The autoexec bind will still fire on next launch and restore it.
  - self.useheld is tied to the +use GAME ACTION, not a specific key. Any key bound to +use works.

---

## Feature: Test DBNO Keybind
Status: WORKING (dispatch confirmed, DBNO trigger unverified end-to-end)
Last confirmed working: 2026-06-19
Key implementation:
  - ui/BIND.SCR:50         — binditem "Coop Test DBNO" "append name ,tdx"
  - variables.scr:140      — local.command["14"]=" ,td"
  - player.scr:520         — arrayIndex==14 dispatches to dbno.scr::dbno_enter local.player "chest"
Known conflicts:
  - Calls dbno_enter directly, bypassing dbno_monitor's health check.
    Will not work if player is already in DBNO state (coop_dbno_active flag set).

---

## Feature: Debug Instrumentation
Status: ACTIVE (to be removed once features confirmed working)
Last confirmed working: 2026-06-19
Key implementation:
  - player.scr:514     — local.player iprintlnbold "DISPATCH 7" on third person keybind
  - thirdperson.scr:54 — local.player iprintlnbold "TP TOGGLE FIRED" in coop_tp_toggle
Known conflicts: none

---

## Feature: Build Script (build.ps1)
Status: WORKING
Last confirmed working: 2026-06-19
Key implementation:
  - C:\mohaa-coop-dev\build.ps1 — packs hzm-mohaa-coop-mod\ into pk3 using .NET ZipArchive,
    deploys to BOTH G:\GOG\...\maintt\ (basepath) AND %APPDATA%\openmohaa\maintt\ (homepath).
  - Dual deploy is REQUIRED: OpenMoHAA homepath (AppData) takes priority over basepath (GOG).
    A stale pk3 in AppData will shadow the GOG pk3 entirely — old code will run.
  - Packs 668 files, ~39 MB. Run time: ~5 seconds.
Run command: powershell -ExecutionPolicy Bypass -File C:\mohaa-coop-dev\build.ps1
Known conflicts: none

---

## Feature: Officer Boss + Radio Station
Status: IMPLEMENTED — deployed 2026-06-21, awaiting player confirmation
Last deployed: 2026-06-21

Key confirmed commands:
  - spawn "model.tik" "health" "400" "targetname" "name" — actor spawn with inline health
  - actor.health = 400                  — health property setter (entity.cpp EV_SetHealth2)
  - actor health 400                    — command form (seen in Boating.scr)
  - actor.accuracy = 85                 — aim quality 0-100
  - actor.mindist = 128                 — min distance from target
  - actor.maxdist = 768                 — max combat distance
  - actor.leash = 4096                  — max wander from spawn point
  - actor.fixedleash = 0                — allow leash to extend
  - actor.sight = 1024                  — sight range
  - actor.hearing = 1024                — hearing range
  - actor.noticescale = 25              — noticing speed
  - actor.interval = 256                — distance to keep from squadmates
  - actor.nosurprise = 1                — no surprise reaction
  - actor.ammo_grenade = 2              — grenade count
  - actor.enemysharerange = 100         — range within which allies share enemy info
  - actor.sound_awareness = 100         — sound detection probability
  - actor.enableEnemy = 1               — enable enemy detection
  - actor gun "Walther P38"             — force weapon
  - actor dontdropweapons               — no weapon drop on death
  - actor waittill death                — fires when actor dies (confirmed in HZM map scripts)
  - actor moveto "run_forward" (X Y Z)  — navigate to position (sets THINK_RUNNER)
  - actor moveto "run_forward" $entity  — navigate to waypoint entity
  - actor attackplayer                  — force attack nearest player (actor.cpp line 1226)
  - actor setaimtarget entity 0/1       — aim at entity; 1 = also make current enemy
  - script_model takedamage             — make prop damageable
  - script_model.health = 80            — prop health setter
  - prop waittill damage                — fires when prop takes any damage hit
  - prop remove                         — remove entity completely
  - prop immune bash/bullet/shotgun     — immunity by damage type

Destructible prop pattern (from e2l3/building1.scr):
  self waittill damage
  if (self.health > 0) { goto loop_label }
  // destroy sequence here
  self remove

Health-triggered retreat pattern:
  while( isAlive local.officer ){
      local.officer waittill damage
      if( local.officer.health < 100 ){
          local.officer moveto "run_forward" local.retreat_pos
          break
      }
  }

Models confirmed available (base game pak, no custom TIK needed):
  - models/human/german_waffenss_officer.tik    — SS officer (most menacing)
  - models/human/german_africa_officer.tik       — Afrika Korps officer
  - models/human/german_wehrmact_officer.tik     — Wehrmacht officer
  - models/miscobj/radio_military.tik            — tabletop military radio
      bounds: (-16 -16 0)(8 16 24), scale 0.52, shader radio_military
  - models/static/static_radiostation1.tik ... static_radiostation4.tik  — full room-size setups
  - models/miscobj/radio_civilian.tik            — civilian radio
  - models/static/static_radio2.tik              — smaller radio unit

Sounds confirmed available (base game pak, need ubersound aliases before use):
  - sound/mechanics/Mec_RadioLoop_03.wav         — in main/Pak3.pk3
  - sound/mechanics/Mec_RadioLoop_04.wav         — in main/Pak3.pk3
  - sound/mechanics/Mec_RadioLoop_05.wav         — in main/Pak3.pk3
  - sound/mechanics/Mec_RadioNoise_11.wav        — in main/Pak3.pk3
  - sound/mechanics/Radio_On.wav                 — in mainta/pak1.pk3
  - sound/mechanics/Radio_Off.wav                — in mainta/pak1.pk3

Implementation plan:
  - Spawn officer near random living enemy (model: german_waffenss_officer.tik, 400 HP, accuracy 85)
  - Spawn radio station near officer (models/miscobj/radio_military.tik, 80 HP, takedamage)
  - Spawn 2 bodyguards at officer position
  - Officer calls reinforcements every 60-90 seconds while alive AND radio intact
  - Random reinforcement type each call
  - Retreat (moveto) when health < 100
  - waittill death → stop all reinforcement threads
  - Radio destructible: 80 HP, waittill damage loop, remove on death, play Radio_Off.wav
  - Destroying radio blocks all future reinforcement calls

---

## Critical Config Values — DO NOT CHANGE WITHOUT UPDATING THIS FILE

### autoexec.cfg (inside pk3 — client-side, fires after omconfig.cfg)
  set sv_dmspeedmult 0.75    — server DM speed multiplier, required by HZM
  bind e "+use"              — restores +use on E after omconfig's unbindall wipes it

### %APPDATA%\openmohaa\maintt\server.cfg (AppData — dedicated server only, NOT loaded by listen server)
  set sv_dmspeedmult 0.75   — kept in sync with autoexec
  set sv_sprinton 0         — HZM original
  set sv_cheats 1           — harmless fallback; not the active fix for listen server

### coop_mod/dbno.scr
  NO setspeed calls — all four removed. Speed controlled solely by dbno_pistol.tik movementspeed.
  DO NOT re-add setspeed calls without checking Player-Confirmed Good Feels first.

### models/weapons/dbno_pistol.tik
  sp/dm/realism movementspeed 0.55 — confirmed perfect feel (see Player-Confirmed Good Feels)
  DO NOT change without explicit player approval.

### models/player/base/anims_injured.txt.bak + include.txt.bak
  EXCLUDED from pk3 (renamed to .bak). Caused crashes near explosions.
  DO NOT restore to .txt until crash-isolated testing confirms they are safe.

### variables.scr getNameAppendCommands token table (DO NOT SHORTEN TOKENS)
  ["7"]=" ,7t"   bind="append name ,7tp"   data="p"   → third person
  ["8"]=" ,8m"   bind="append name ,8mk"   data="k"   → medkit (stub)
  ["9"]=" ,9c"   bind="append name ,9cv"   data="v"   → cover (stub)
  ["10"]=" ,pg"  bind="append name ,pgx"   data="x"   → ping (stub)
  ["11"]=" ,bn"  bind="append name ,bnx"   data="x"   → binoculars (stub)
  ["12"]=" ,rd"  bind="append name ,rdx"   data="x"   → radio (stub)
  ["13"]=" ,rv"  bind="append name ,rvx"   data="x"   → revive (stub)
  ["14"]=" ,td"  bind="append name ,tdx"   data="x"   → test DBNO

---

## Player-Confirmed Good Feels
RULE: Check this section before every repack. Never change a confirmed value without explicit player instruction.

### DBNO Movement Speed
Value: movementspeed 0.55 in models/weapons/dbno_pistol.tik — NO setspeed calls anywhere.
Player quote: "the last time we actually changed this it was perfect. It was the exact speed I wanted it at."
DO NOT change this value without explicit player approval.

### Health Restoration — Standing Heal and Self-Revive
Value: full health via health level.coop_health (750 by default) in BOTH medkit.scr::medkit_use
and medkit.scr::dbno_selfrevive.
Status: PLAYER CONFIRMED — both standing heal and self-revive restore to full health.
Reasoning: healthonly 50 with max_health 750 displayed as 6% on health bar (50/750). Using
health level.coop_health restores both current and max health, giving a full bar. Standing
heal previously used +50 HP partial restore — player confirmed full restore is correct behavior.
DO NOT change either to partial heal without explicit player approval.

### DBNO Crouch/Limp Movement
Player confirmed the crouch/limp movement during DBNO feels like limping. This is the intended feel.
Do not replace with prone or any other animation state.

### DBNO Bleedout Timer
Normal hit body locations: 60 seconds feels right.
Headshot: 45 seconds feels right.
Do not adjust timers without explicit player approval.

### Third Person Camera Toggle
Third person toggle works correctly. Camera pulls back behind player. Works during normal gameplay and DBNO. Toggle via Controls menu keybind.
Status: PLAYER CONFIRMED — 2026-06-20

### Cover Sandbag Placement — Model, Angles, Collision, Sound, Removal
Model: coop_sandbag.tik (sandbag_link_main.skd, scale 0.52). PLAYER CONFIRMED — 2026-06-20.
Angles: bagangles[1] = player yaw only. No pitch correction. No yaw offset. DO NOT add pitch or
  yaw offset — model stands upright and faces correctly at default orientation.
Collision: setsize ( -13 -52 0) (10 52 47) from .map clip brush data. DO NOT change these values.
Sound: coop_sandbag_place (body_falldirt_04.wav, item channel) fires on placement. CONFIRMED.
Removal: hold RMB 100 frames within 80 units, sandbag deleted and placement refunded. CONFIRMED.
Refund: owner receives placement back on removal; "Sandbag refunded!" message fires. CONFIRMED.

---

## Known Limitations and Dead Ends
These have been researched and confirmed not possible with the current approach.
Do NOT attempt these again without a new confirmed solution first.

### Cover System — Sandbag Collision Shape
Status: RESOLVED — full QUAKED bounds with safesolid is the correct approach.
  col1.origin = hitpos (no offset)
  setsize (-32 -80 0)(56 88 56)        — full QUAKED bounds
  safesolid                            — delays solid if player is inside bounds on spawn
safesolid confirmed in e1l1/thinkTank.scr and e3l2/thinkTank.scr for script_object collision.
Do NOT add the isalive check back to the proximity scan — script_model health is always 0,
isalive always returns false, and the classname fallback was unreliable. NULL check is sufficient.
Do NOT use partial-bounds approaches (e.g. curved-wall-only box) — SOLID_BBOX does not rotate
  with entity angles so partial boxes only align with the visual model at one specific world angle.
  See: ### SOLID_BBOX setsize does not rotate.
Do NOT call solid on the script_model (vis) directly — uses full QUAKED hull which blocks
  the entire footprint. Separate script_object required for collision.

### SOLID_BBOX setsize does not rotate
LESSON: script_object uses SOLID_BBOX. gi.linkentity() computes world-space AABB as:
  absmin = origin + mins   (no rotation applied)
  absmax = origin + maxs   (no rotation applied)
Entity angles are completely ignored for the collision shape. Setting local.col1.angles on a
script_object has zero effect on collision — the box is always the same world-space AABB
regardless of which direction the entity faces.
Consequence: any partial-bounds collision box on a rotatable placeable object will only align
with the visual model at one specific world angle. At all other angles, the collision will be
misaligned. Full QUAKED bounds (covering the entire model footprint) is the only correct
approach for script_objects that can be placed at arbitrary angles.
APPLIES TO: any script_object collision box on a rotatable entity.

### Prone Animation on Players
Status: BLOCKED
Reason: No PRONE state in player_legs.st. forcelegsstate PRONE is invalid.
setmotionanim/setactionanim are Actor class only — not available on players.
walk_injured_forward animation exists but only in AI TIK, not player TIK chain.
Custom include.txt override caused crashes near explosions — files renamed to .bak.
Resolution path: Add walk_injured_forward to player TIK chain carefully and test in isolation
away from explosion scenarios.

### Per-Player FOV Tunnel Vision
Status: BLOCKED
Reason: fov command is SP-only in MOHAA. stufftext cg_fov blocked by OpenMoHAA filter.
Resolution path: Engine fork.

### Red Tint Overlay
Status: BLOCKED
Reason: ihuddraw slots 21-26 claimed by HZM items system which continuously overwrites our values.
Slot 30 attempted but also not rendering correctly.
Resolution path: Unknown — may require a different overlay approach.

### Custom Keybinds via stufftext bind
Status: BLOCKED
Reason: OpenMoHAA blocks bind command via stufftext for security reasons.
Resolution path: Use name-append system via ui/BIND.SCR (confirmed working).

### M Key Default MOHAA Bind
Status: NOTE ONLY
The M key is bound to the screenshot/print action in default MOHAA. Players must open the Coop Bind
menu and rebind the "Coop Medkit" action to a different key (e.g. X, Z, F). No code fix needed.

### DBNO RMB Melee on First Click
Status: NOTE ONLY — cosmetic, do not fix
The engine processes one melee attack frame on the first right-click while in DBNO, even though
secondary fire was removed from dbno_pistol.tik. No gameplay impact.

### Self-Revive via managePlayerInventory — Disguise Mission Risk
Status: NOTE — not tested in disguise missions
On self-revive, dbno_selfrevive threads managePlayerInventory to restore the player's weapon loadout.
This function also handles disguise state (coop_hasDisguise, coop_alliedUniform etc.). In
non-disguise missions this is a no-op. In disguise missions it re-evaluates disguise on revival —
probably correct behavior but untested. Flag for testing if disguise missions are added.

### cg_3rd_person via autoexec.cfg toggle bind
Status: BLOCKED
Reason: cg_3rd_person is CVAR_CHEAT. toggle cg_3rd_person in autoexec.cfg has no effect
without sv_cheats, and sv_cheats cannot be set for listen server via scripts or cfg files.
Resolution path: Engine fork.

### sv_maxclients via getcvar
Status: CONFIRMED BROKEN in listen server
Reason: returns empty string not a number. int("") = 0. Do not use for player loops.
Use $player.size instead.

### Canteen vs Medkit pickup — cannot distinguish in script
Status: CONFIRMED IMPOSSIBLE in vanilla MOHAA script
Reason: item_25_healthbox.tik (canteen), item_50_healthbox.tik (medkit), item_100_healthbox.tik
(surgeon pack) all share classname Health. No targetname, no pickup event, no script callback
fires on collection. The pickupsound directive (med_canteen vs med_kit) is engine-side and
cannot be intercepted in script. Delta discrimination is unreliable due to max-health clamping.
Resolution path: None without an engine hook or entity-monitoring approach (see below).

### Full-health player medkit refill — entity scan implemented (single-player safe)
Status: IMPLEMENTED (2026-06-20) — pending player test
Implementation: coop_scan_health_entities in medkit.scr; threaded from main.scr.
Scans 0..maxentities once at map start, stores entnums + origins in level.coop_health_ents[].
Per-tick in medkit_hud_monitor: when curr_hp >= level.coop_health, iterate stored list and check
if any entry is NULL and player was within 100 units → award medkit, nil out the stored entry.
Known limitations:
  - Multiplayer: first player within 100 units who reaches max health gets the refill, not necessarily
    the one who picked up the box. Acceptable for coop play.
  - Respawning packs: nil'd entry won't re-trigger; if the same pack respawns it won't give another refill.
    Fine for coop maps (MOHAA coop packs don't respawn).
  - Scan cost: one-time only at map start (waitframe then scan). Per-tick only iterates pre-built list.

---

## Lessons Learned
Insights from debugging sessions. Check this section BEFORE implementing any new feature.

### $player[] array iteration
LESSON: Never iterate $player[] up to 64. Accessing indices beyond connected player count causes
"array index out of range" and "Cannot cast 'none' to listener" errors every frame.
SUPERSEDED — the sv_maxclients getcvar approach (fallback 16) is also broken (see lesson below).
ALWAYS USE $player.size. See: ### $player.size vs sv_maxclients
APPLIES TO: any loop that iterates all connected players.

### DBNO flag ordering in revival sequences
LESSON: coop_dbno_letgo MUST be set to 1 before coop_dbno_active is cleared on self-revive.
If not, dbno_fade_manager exits its while loop and takes the death-screen path: sets HUD slot
20 to full black alpha, waits 1.5 seconds, then clears. This blacks the player screen for
1.5s and corrupts player entity state, causing commands like iprintlnbold to fail with
"Failed execution of command for class Player Targetname player".
CORRECT ORDER in any revival sequence:
  coop_dbno_letgo   = 1    (skip death-screen path in fade_manager)
  coop_dbno_dead    = 1    (block dbno_monitor re-trigger)
  coop_dbno_healing = NIL  (allow bleedout timer to process)
  coop_dbno_active  = NIL  (signal all DBNO threads to exit)
APPLIES TO: any revival sequence that clears DBNO state.

### healthonly 9999 buffer
LESSON: dbno_start sets healthonly 9999 as a damage buffer so small amounts of incoming fire
do not immediately trigger the DBNO cumulative threshold. Any health value read during DBNO
will be ~9749+ not a real 0-100 value. coop_dbno_prev_health captures this buffer value, NOT
the player's real health before going down.
NEVER use coop_dbno_prev_health for health restoration after self-revive — it will always
resolve to ~9749, which gets clamped to 100 by any max-health check.
ALWAYS use health X (not healthonly X) for restoration; currently health level.coop_health (full health on self-revive).
APPLIES TO: any health restoration after DBNO.

### Per-player threads vs global $player[] loops
LESSON: Global loops iterating $player[] are fragile: they spam errors when array indices
exceed connected player count, and run every frame on the server regardless of need.
Prefer per-player threads started from manageAliveSpawning where possible.
The medkit_pickup_monitor global loop was replaced with per-player health-delta detection
inside medkit_hud_monitor for exactly this reason — zero $player[] iteration required.
APPLIES TO: any feature that needs to monitor all players.

### Entity validity after DBNO state changes
LESSON: When clearing DBNO state, multiple threads wake simultaneously and try to act on the
player entity. Commands sent to a player whose screen is being taken over by another thread
(e.g. dbno_fade_manager's death screen) will fail with "Failed execution" errors.
Always resolve parallel-thread interference first before debugging the failing command itself.
Always check local.player != NULL before any command in a revival sequence.
APPLIES TO: any multi-thread system where state changes affect multiple threads simultaneously.

### Weapon inventory after DBNO revival
LESSON: coop_inventoryWeapons is only populated when a player physically picks up a weapon
entity in the world. Default spawn loadout (given via giveInventory/spawnInventory at map
start) does NOT go through addToInventory and does NOT populate this flag. After
resetPlayerWeapons the array exists as [NIL] (not truly NIL), so NIL checks pass incorrectly.
Always use 3-tier restore: (1) coop_inventoryWeapons loop, (2) level.coop_weaponLoadout loop,
(3) hardcoded fallback loadout. local.gave flag MUST be set to 1 in BOTH tier 1 AND tier 2
loops — otherwise tier 3 fires on top of a successful tier 2 restore, doubling weapons.
APPLIES TO: any weapon restoration after DBNO revival.

### Thread timing after state changes
LESSON: Commands like item, takeall, and stoploopsound may internally yield execution in
OpenMoHAA. After clearing coop_dbno_active, always add wait 0.1 before healthonly to let all
DBNO threads exit cleanly before setting health. Without this, a thread waking in the gap
between active=NIL and healthonly can overwrite the health value.
APPLIES TO: any health restoration immediately after DBNO state is cleared.

### $player.size vs sv_maxclients
LESSON: getcvar "sv_maxclients" returns empty string in listen server context.
int("") = 0, fallback of 16 still accesses indices beyond real player count.
ALWAYS use $player.size which returns the exact count of connected players.
HZM already uses this in mg42_hack.scr, developer.scr, strings.scr, main.scr.
Zero risk of out of range errors.
APPLIES TO: every $player[] loop.

### health vs healthonly
LESSON: healthonly sets current health only. health sets both current AND max health.
The health bar displays current/max as a percentage. playerHealth (called at spawn) sets
max health via: local.player health level.coop_health (default 750). Subsequent healthonly
calls do not touch max_health, so healthonly 50 with max 750 displays as 6% on the bar.
dbno_start's healthonly 9999 also does not raise max_health — it only sets the damage buffer.
Always use health X (not healthonly X) when you want the bar to reflect the value correctly.
APPLIES TO: any health restoration after DBNO.

### coop_lastWeapon contamination
LESSON: coop_lastWeapon is updated continuously by weaponstate.scr based on currently active
weapon. During DBNO the active weapon is dbno_pistol.tik so coop_lastWeapon =
"weapons/dbno_pistol.tik" when revival fires. Using this to re-equip after revival fails
silently since dbno_pistol was removed by takeall. ALWAYS use useweaponclass rifle after
revival, not use coop_lastWeapon.
APPLIES TO: any revival sequence after takeall.

### AppData pk3 shadowing (homepath priority)
LESSON: OpenMoHAA searches homepath (%APPDATA%\openmohaa\) BEFORE basepath (GOG installation).
A same-named pk3 in AppData shadows the GOG pk3 entirely — the AppData version wins for every
file inside it, even if the GOG pk3 is newer or larger. If files are missing from the AppData
pk3, the engine falls through to the original HZM pak1-pak4 files, not the GOG pk3.
ALWAYS deploy to BOTH locations. build.ps1 already does this. Never test after deploying to
GOG only — the AppData copy will silently serve old code.
APPLIES TO: every build and deploy cycle.

### iprint vs iprintlnbold_noloc
LESSON: iprint "message" 1 is the correct command for player-facing in-game messages.
Type 1 = large center-screen display. Type 0 = smaller notification (used for team messages).
iprintlnbold_noloc fails to display in-game in some thread contexts (shows in server console only).
Confirmed working: dbno.scr "You are DOWN!" uses local.player iprint local.down_msg 1.
APPLIES TO: any player-facing message.

### Flag timing around wait statements
LESSON: Never clear a guard flag before a wait if the flag protects against a monitor that
runs during that wait. coop_medkit_in_use was cleared before wait 0.1, allowing
medkit_hud_monitor to detect the +50 HP delta and re-add the medkit during the wait window.
Always clear guard flags AFTER any wait statements that background monitors could run through.
APPLIES TO: any flag-guarded system with background monitors.

### Health delta pickup detection conflict
LESSON: medkit_hud_monitor detects world health pickups by watching for health increases of
10-200 HP (world packs give ~150 HP — see ### MOHAA health pack delta value). Any in-script
health restoration in this range triggers the same detector and adds a medkit back to the
player's count, cancelling the decrement. Always guard the pickup detector with
coop_medkit_in_use check when a heal is in progress.
APPLIES TO: any script that restores 10-200 HP to a player.

### useweaponclass rifle needs settle time
LESSON: useweaponclass triggers internal weapon-state processing in OpenMoHAA. Commands sent
immediately after (playsound, iprintlnbold_noloc) fail with "Failed execution of command for
class Player" because the entity is in a transitional state during equip processing.
ALWAYS add wait 0.1 after useweaponclass before any entity command.
The same applies to takeall — wait 0.1 before health/item calls.
APPLIES TO: any revival or weapon-swap sequence.

### MOHAA health pack delta value
LESSON: MOHAA world health packs restore approximately 150 HP per pickup, not 10-50 HP as assumed.
Any health pickup detector must use an upper threshold of at least 150 to catch world health pack pickups.
The medkit_hud_monitor detector was originally set to delta <= 50, which silently rejected all world
health pack pickups. Confirmed via debug iprint: actual delta = 150. Threshold corrected to <= 200.
APPLIES TO: any health delta detection system.

### getentbyentnum entity scan pattern
LESSON: getentbyentnum N is a confirmed working script command. butler.scr:106-128 iterates
0..int(getcvar("maxentities")) to find and remove specific item models. developer.scr:785 does
the same for proximity/touch detection. Entity .model and .classname are readable at runtime.
This is the only viable approach for finding world entities by type from a script (no
findentity/getentbyclassname command exists in MOHAA script).
Performance note: maxentities is typically 1024; full scans are expensive and should only be
done once at map-start, not per-tick. Per-tick checks should only iterate a pre-built list.
APPLIES TO: any feature that needs to find world entities by classname or model at runtime.

### MOHAA ihuddraw shader element size
LESSON: ihuddraw_shader elements use the rect width/height to control display size.
A 32x32 TGA at rect 32 32 shows at native size; smaller rect values downscale it in screen-space.
The HUD icon was reduced from rect 10 -66 32 32 to rect 10 -36 16 16 to match the health bar
star icon size. Position y value must move proportionally when size changes (height halved,
y adjusted from -66 to -36 to keep bottom edge in the same screen region).
APPLIES TO: any ihuddraw_shader placement that needs to match existing HUD element sizes.

### iprint type 1 goes to top-left in OpenMoHAA (not center screen)
LESSON: In OpenMoHAA, iprint "msg" 1 routes to the notify area (top-left rotating list), NOT
center screen as vanilla MOHAA documentation suggests. Type 0 also appears in notify area.
For center-screen messages, use ihuddraw_string with align center center on a free slot.
The BLEEDING OUT text (slot 27, center center) is the confirmed working pattern for this.
APPLIES TO: any message that must appear center-screen (confirmations, status messages, etc.).

### ihuddraw slot persistence means no flag needed for "show once" text
LESSON: ihuddraw_string on a slot persists visually until explicitly cleared with alpha 0 or
string "". There is no need for a "msg_shown" flag pattern — setting the string once is enough;
it stays visible through all subsequent while-loop iterations. The msg_shown flag pattern only
becomes necessary if you use iprint (which fires and vanishes immediately). Always prefer
ihuddraw_string for persistent status/hint messages over iprint + flag tracking.
APPLIES TO: any repeating loop that needs to show a message without spamming it.

### MOHAA script randomint syntax
NOTE (unconfirmed): User-proposed randomint N returns a random integer from 0 to N-1.
Pending test confirmation before documenting as confirmed working.
If randomint is unavailable, alternative: use (level.time * 100) % N or similar.
APPLIES TO: any random selection in script (sound shuffle, spawn variance, etc.).

### Custom TIK for script-spawned placeable objects
LESSON: To use an existing MOHAA model as a script-spawned placeable object:
1. Create a custom .tik file in the mod pak (e.g. models/static/coop_sandbag.tik).
   Reference the original SKD/SKC from the base game pak — no need to copy asset files.
   Use scale 0.52 (standard cm→units conversion) unless the original TIK uses a different value.
2. For collision bounds, extract the .map file for the model from the base game pak.
   The clip brush coordinates in the .map file are authoritative in-game unit bounds.
   These are more accurate than OBJ geometry estimates or QUAKED comment bounds.
3. Use a separate script_object (not the script_model) for collision, with setsize from step 2.
   Call safesolid (not solid) so spawning inside the bounds delays activation safely.
4. Remember SOLID_BBOX does not rotate — setsize bounds are always world-axis-aligned.
   Verify the bounds work at all placement angles before confirming as working.
APPLIES TO: any script-spawned placeable cover, decoration, or interactive object.

### MOHAA script lexer: negative vector components require space after opening parenthesis
LESSON: The MOHAA script lexer tokenizes `(-N` as TOKEN_MINUS followed by a number, which
breaks vector literal parsing. Any vector with a negative first component MUST have a space
between the opening parenthesis and the minus sign.
WRONG (causes parse/syntax error, silently breaks entire script file):
  setsize (-13 -52 0)(10 52 47)
  setsize (-32 -80 0)(56 88 56)
CORRECT:
  setsize ( -13 -52 0) (10 52 47)
  setsize ( -32 -80 0) (56 88 56)
This applies to ALL vector literals with negative first components in MOHAA script:
setsize, origin assignments, any (X Y Z) literal where X is negative.
APPLIES TO: every vector literal with a negative first component in .scr files.

### SOLID_BBOX collision does not rotate with entity angles
LESSON: script_object (and script_model) use SOLID_BBOX. gi.linkentity() computes the
world-space AABB by adding origin + mins and origin + maxs directly — no rotation applied.
Setting entity.angles on a script_object has zero effect on the collision shape.
This means any partial-bounds box (e.g. covering only the curved wall of a semicircle) will
only align with the visual model at one specific world angle. At all other placement angles
the collision box will be in the wrong position relative to the visual.
CORRECT APPROACH: For any placeable object that can face arbitrary directions, use full
model-footprint bounds (full QUAKED bounds) so the box covers the model at all angles.
If partial collision is needed at arbitrary angles, compute the world-space offset explicitly
using angles_toforward and right-vector arithmetic, and spawn the collision entity at an
offset position — not by relying on entity.angles to rotate the box.
APPLIES TO: any script_object or script_model collision box on a rotatable entity.

### UTF-8 BOM kills the entire .scr file silently
LESSON: PowerShell `Set-Content -Encoding utf8` in PS 5.1 adds a UTF-8 BOM (bytes EF BB BF) to
the start of the file. MOHAA's script parser treats these as illegal leading characters and fails
to parse the ENTIRE file — all functions stop loading without any in-game error. Symptoms: features
that previously worked suddenly never spawn; no crash, no error message. This is the third
encoding-related parse killer confirmed this session:
  1. Em-dash / non-ASCII bytes anywhere in file (even comments) — bytes > 0x7F fail parser
  2. Bare negative as first token after `(` — `(-13` → parser error; must write `( -13`
  3. UTF-8 BOM at start of file — entire file silently dead to the parser
NEVER use `Set-Content -Encoding utf8` on any .scr file. Use `-Encoding ASCII` (PS 5.1 safe).
Prefer the Edit tool which never adds BOM. Strip an existing BOM with byte-level read/write:
  $b=[System.IO.File]::ReadAllBytes($p); [System.IO.File]::WriteAllBytes($p,$b[3..($b.Length-1)])
Verify clean: first 4 bytes should start with ASCII (e.g. 47=`/` for `//` comment, not 239=0xEF).
APPLIES TO: every PowerShell write to any .scr file.

### $player is 1-indexed — $player[0] is the world entity
LESSON: MOHAA's `$player` entity array is 1-indexed. `$player[0]` refers to the world entity,
NOT the first connected player. Attempting player operations on `$player[0]` (playsound, health,
iprint, etc.) silently operates on the world entity instead of a player.
CORRECT player loop pattern:
  local.pi = 1
  while( local.pi <= $player.size ){
      $player[local.pi] playsound coop_radio_chatter
      local.pi++
  }
WRONG (treats world entity as player):
  local.pi = 0
  while( local.pi < $player.size ){
      $player[local.pi] playsound ...   // $player[0] = world, wrong
      local.pi++
  }
APPLIES TO: every loop that iterates all connected players by index.

### Full health medkit refill approach
LESSON: When player is at full health walking over a health pack produces zero delta so the
delta detector never fires. The pre-scanned entity list approach also fails if the scan found
0 packs (map variant mismatch, wrong model paths, or scan ran before health entities spawned).
Most reliable approach is a timer-based classname scan every 5 seconds that only runs when
player is at full health and has 0 medkits. Uses getentbyentnum with classname == "Health"
check and 100 unit proximity. Fires refill and exits scan loop immediately on first match
(local.si = local.maxent to break). Timer threshold >= 50 at wait 0.1 per tick = 5 seconds.
maxentities should be read once before the while loop, not per-tick. Guard with
if( local.maxent <= 0 ){ local.maxent = 1024 } in case getcvar returns empty string.
APPLIES TO: any health pickup detection at full health.

### ihuddraw position relative to health bar bottom-left area
LESSON: The MOHAA engine renders the health bar, health number, and allied star at hardcoded
engine coordinates in the bottom left. These cannot be read from scripts.

Through iterative testing the confirmed working position for a 16x16 HUD icon placed just
above the health bar top-left area is:
  ihuddraw_rect local.player SLOT 5 -62 16 16

And for a text label immediately to the right of that icon:
  ihuddraw_rect local.player SLOT 23 -60 0 0

Both use left bottom alignment. The y value of -62 places the element just above the health
bar and allied star icon which sit at approximately y=-34 to y=-50 in engine space.
APPLIES TO: any custom HUD element that needs to sit above the default MOHAA health bar
in the bottom left.

---

## Pre-Change Checklist
Before making ANY change, explicitly state:
1. FILES AFFECTED: [list every file being touched]
2. FEATURES AT RISK: [list every working feature that touches these files]
3. ROOT CAUSE CONFIRMED: [yes/no — with evidence]
4. GOOD FEELS AT RISK: [check against Player-Confirmed Good Feels section]
5. DEAD ENDS CHECKED: [confirm this is not a known blocked approach]
If any of these cannot be answered confidently — STOP and research more before proceeding.

---

## Repack Verification Checklist
Before every pk3 repack confirm:
1. ASCII clean on ALL modified files (no Unicode, no smart quotes)
2. No duplicate lines from edits
3. No multi-line conditions in script
4. Good feels values unchanged
5. All modified functions shown in context and verified

---

## Session Start Protocol
At the start of every new session:
1. Read KNOWN_WORKING_STATE.md
2. Read transcript summary if available
3. List what was working at end of last session
4. List what was broken/pending at end of last session
5. Confirm the plan before touching any files

---

## Rollback Awareness
Before any significant change, identify the rollback plan:
- What files would need to revert?
- What values would they revert to?
- Is there a known good state to return to?

---

## Single Responsibility Rule
Each session should have ONE primary goal. Secondary fixes can be included only if they are:
- Directly related to the primary goal
- Confirmed not to affect other features
- Small and low risk
If a secondary issue is found during a session, note it in this file and address it next session.

---

## Change Log
[2026-06-19] dbno.scr — removed all 4 setspeed calls (were index 0 → invalid, then 1 at various values). Speed control moved to tik file exclusively. WHY: setspeed was aborting dbno_enter thread (index 0 invalid), then stacking with movementspeed causing 24% effective speed. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] models/weapons/dbno_pistol.tik — restored sp/dm/realism movementspeed 0.55 (was removed in prior session, then 0.3, then removed again). WHY: confirmed perfect feel at 0.55 with no setspeed. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] dbno.scr dbno_crawl_manager — added penalty_shown flag to fire "Moving is accelerating your bleed-out!" once per movement episode instead of every 10 frames. WHY: message was spamming. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] KNOWN_WORKING_STATE.md — added Known Limitations, Player-Confirmed Good Feels, Process Rules, Change Log, Pre-Change Checklist, Repack Verification Checklist, Session Start Protocol, Rollback Awareness, Single Responsibility Rule. WHY: establish session discipline. RESULT: APPLIED
[2026-06-19] DBNO STABILIZATION COMPLETE — Full DBNO pass player-confirmed. Speed (movementspeed 0.55), E key tap (medic callout), E key hold (letgo), movement penalty message (once per episode) all WORKING. DBNO marked stable.
[2026-06-19] medkit.scr — fixed HUD position (slot 36 left bottom 10 -30), weapon restoration via managePlayerInventory thread on self-revive, health restoration hardcoded to 50hp. WHY: coop_dbno_prev_health was capturing the pre-DBNO 9999 buffer health. RESULT: FAILED — health still unchanged after revive; dbno_monitor re-triggers DBNO immediately after coop_dbno_active cleared, overwriting healthonly 50 with healthonly 100. managePlayerInventory may also have had side effects.
[2026-06-19] medkit.scr — replaced medkit_pickup_monitor global loop with sv_maxclients cap instead of 64. RESULT: FAILED — sv_maxclients getcvar returning invalid/zero value in this server context, loop still accessed out-of-range $player indices and spammed errors.
[2026-06-19] medkit.scr — CRITICAL FIXES: (1) medkit_pickup_monitor deleted; health pickup detection moved into per-player medkit_hud_monitor (no $player array loop). (2) dbno_selfrevive: coop_dbno_dead=1 set BEFORE coop_dbno_active=NIL — blocks dbno_monitor re-trigger on revived player. (3) forcelegsstate STAND added after modheight stand. (4) weapon restore: coop_inventoryWeapons loop + level.coop_weaponLoadout fallback (default loadout not stored in inventory flags for fresh-spawn players). (5) HUD rect moved to -50. WHY: dbno_monitor was re-triggering DBNO on revival because cumulative damage tracked during DBNO fired the moment coop_dbno_active cleared; $player loop approach fundamentally broken for variable server sizes. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] medkit.scr dbno_selfrevive — completion block flag order fixed: coop_dbno_letgo=1 added first, then dead=1, then healing=NIL, then active=NIL. WHY: coop_dbno_letgo not set was causing dbno_fade_manager to take death-screen path (1.5s full black) after every self-revive, corrupting player state and causing "Failed execution of command iprintlnbold for class Player" errors. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] dbno.scr — all 4 $player[] loops (dbno_enter, dbno_medic_callout, dbno_marker_manager x2) changed to $player.size. WHY: getcvar sv_maxclients returns empty string in listen server; hardcoded 64 and fallback 16 both exceeded real player count causing index-out-of-range spam. $player.size returns exact connected count. RESULT: PLAYER CONFIRMED (no array errors)
[2026-06-19] medkit.scr dbno_selfrevive — useweaponclass rifle replaces use coop_lastWeapon in revival sequence. WHY: coop_lastWeapon is set to weapons/dbno_pistol.tik by weaponstate.scr during DBNO; using it after takeall fails silently, leaving player unarmed. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] medkit.scr dbno_selfrevive — playsound changed from snd_pickup to med_kit (Health_MedKit_01.wav, confirmed ubersound.scr:1086); iprintlnbold changed to diagnostic "Revived! HP=X". RESULT: PLAYER CONFIRMED (print showed HP=750)
[2026-06-19] medkit.scr dbno_selfrevive — healthonly local.restore_health changed to health level.coop_health in revival completion block. WHY: healthonly only sets current health; max health remains 750 from spawn, so healthonly 50 displayed as 50/750=6% on health bar. health level.coop_health sets both current and max to the configured value, restoring a full health bar. RESULT: PLAYER CONFIRMED WORKING
[2026-06-19] dbno.scr dbno_enter — healthonly 100 changed to health 100. WHY: health 100 correctly sets max health to 100 during DBNO state, giving a clean health chain: spawn health 750 → DBNO health 100 → revival health level.coop_health. RESULT: WORKING (part of confirmed system)
[2026-06-19] build.ps1 created at C:\mohaa-coop-dev\build.ps1. WHY: manual pk3 packing was producing flat structure (all files at root). .NET ZipArchive with explicit entryName preserves directory paths. Deploys to both GOG basepath and AppData homepath. RESULT: WORKING (667 files, 39.16 MB, dual-deploy confirmed)
[2026-06-19] AppData shadow pk3 discovered and fixed. WHY: %APPDATA%\openmohaa\maintt\zzzzzz_co-op_hzm_mod_mohaa.pk3 (90.5 MB, old build) was shadowing GOG pk3 — engine loaded old code from pak1-pak4 because the AppData pk3 lacked medkit.scr. Build.ps1 now deploys to both locations. RESULT: FIXED (canary confirmed new code running)
[2026-06-19] medkit.scr dbno_selfrevive — added wait 0.1 after useweaponclass rifle and before playsound med_kit. WHY: useweaponclass triggers internal weapon-state processing; entity in transitional state caused "Failed execution of command iprintlnbold_noloc for class Player" at revival print line. RESULT: DEPLOYED (not yet player-confirmed)
[2026-06-19] medkit.scr medkit_hud_monitor — removed MEDKIT V2 LOADED canary line. WHY: canary served its purpose (confirmed new code running after AppData shadow fix). No longer needed. RESULT: APPLIED
[2026-06-19] medkit.scr medkit_use — fixed health threshold from >= 75 to >= level.coop_health and health cap from 100 to level.coop_health; changed all 4 iprintlnbold calls to iprintlnbold_noloc. WHY: with 750 max health the old values blocked healing above 75/100 (10-13% of max) — essentially never usable. All iprintlnbold calls need _noloc to avoid localization errors. RESULT: PENDING TEST
[2026-06-19] medkit.scr medkit_use — healthonly → health for correct bar display; 60 frames → 200 frames (~10s); setspeed 0 1 on start / setspeed 1.0 1 on all exit paths to freeze movement during heal. WHY: health bar showing ~6% due to healthonly not resetting max_health; double-use caused by invisible health feedback; player requested movement freeze during heal. RESULT: PENDING TEST
[2026-06-19] player.scr dispatch — changed arrayIndex==8 from thread to local.player thread for medkit_use. medkit_hud_monitor — added coop_medkit_in_use guard to pickup detector. medkit_use — removed setspeed freeze; added origin tracking cancel (> 15 units); 200 frames → 100 frames (~5s); fill_width = heal_frames * 2; wait 0.1 before playsound/print. WHY: pickup detector was re-adding medkit after each use (cancelling decrement); text not showing due to missing settle time after health command; player requested movement-cancel instead of freeze; 10s too long. RESULT: PENDING TEST
[2026-06-19] STANDING HEAL COMPLETE — Player confirmed all behaviours working. Key fixes applied: iprint type 1 for all player-facing messages (iprintlnbold_noloc fails in some contexts); coop_medkit_in_use = NIL moved to after wait 0.1 (was before, allowing monitor to re-add medkit during wait); health level.coop_health before healthonly to reset max health to 750 before setting current. RESULT: PLAYER CONFIRMED WORKING
[2026-06-20] textures/hud/coop_medkit_icon.tga — new 32x32 RGBA TGA added to mod (green box, white halo cross, red cross, transparent bg). Generated via Python/Pillow. WHY: replace "Medkit: N" text HUD with icon + number. RESULT: DEPLOYED
[2026-06-20] medkit.scr medkit_hud_monitor — slot 36 changed from ihuddraw_string to ihuddraw_shader (icon); slot 37 added for count number (verdana-14). Icon rect 10 -36 16 16; count rect 28 -34. player.scr spectator cleanup extended to also hide slot 37. WHY: icon HUD replaces text label. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr dbno_selfrevive — added local.msg_shown flag; cancel message "You cannot apply health kits when moving" now fires only once per hold attempt; msg_shown reset in both cancelled and else cleanup blocks. WHY: previous message spammed every frame player was moving. RESULT: DEPLOYED — pending player test
[2026-06-20] ubersound.scr — coop_medkit_cloth volume 2.0→4.0; coop_exhale1/2 pitch 1.5→3.0. WHY: sounds still too quiet in-game. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr medkit_use — cloth sound moved from pre-loop single play to loop-internal frames 1 and 50. dbno_selfrevive — cloth plays at hold_frames 1, 67, 134. WHY: single play at start was inaudible by the time any heal was felt; repeating gives tactile feedback across the full duration. RESULT: DEPLOYED — pending player test
[2026-06-20] textures/hud/coop_medkit_icon.tga — icon position adjusted to rect 95 -10 16 16 (was 10 -36 16 16). Count number slot 37 moved to rect 113 -8. WHY: original position was overlapping the health bar region. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr dbno_selfrevive — replaced iprint + msg_shown flag with ihuddraw slot 38 for movement cancel message. msg_shown variable removed entirely. WHY: msg_shown was reset every time the secondaryfireheld==1 block re-entered (every outer-while frame while RMB held + moving), causing spam regardless of the flag. ihuddraw persistent text shows once and stays until cleared. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr dbno_selfrevive — added ihuddraw slot 39 self-revive hint "Hold [MOUSE2] to self-revive" (center center, verdana-14, yellow-white, rect 0 -30). Shown on function entry, hidden on revival/exit. WHY: player had no visual indication of how to trigger self-revive. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr dbno_selfrevive — replaced iprint revival message with ihuddraw slot 33 (center center, handle-23, green, rect 0 0) for 3 seconds then cleared. Uses int(local.player.health) to avoid .000 suffix. WHY: iprint type 1 goes to top-left notify area in OpenMoHAA, not center screen. RESULT: DEPLOYED — pending player test
[2026-06-20] ubersound.scr — coop_exhale1/2 pitch 3.0→5.0. WHY: exhale sound still too low-pitched after prior 1.5→3.0 boost. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr — added coop_scan_health_entities function. main.scr — threads it at map start. medkit_hud_monitor — full-health entity proximity check added. WHY: when player is at full health, picking up a health box produces zero delta and the refill detector misses it. Entity scan detects pack disappearance near player. RESULT: DEPLOYED — pending player test
[2026-06-20] player.scr spectator cleanup + dbno_start — added ihuddraw_alpha 0 for slots 38 and 39. WHY: new HUD slots need cleanup on all exit paths. RESULT: DEPLOYED
[2026-06-20] coop_mod/variables.scr — level.coop_healthDropFreq changed from 5 to 10. WHY: halves enemy health drop frequency, making world packs and medkit system more meaningful. RESULT: DEPLOYED
[2026-06-20] medkit.scr medkit_hud_monitor — slot 36 rect shifted left from 62 -34 to 48 -34; slot 37 rect shifted from 80 -32 to 66 -32. WHY: player-confirmed icon position was right of intended alignment with allied star. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr medkit_hud_monitor — added timer-based classname scan (>= 50 ticks = 5s interval). Scans all entities by classname "Health" within 100 units when player is at full health with 0 medkits. WHY: entity pre-scan approach unreliable (zero results on some maps); delta detector blind at full health. Timer scan is parallel fallback. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr medkit_hud_monitor — icon slot 36 rect moved to 5 -52 16 16; count slot 37 moved to 23 -50. WHY: bracketing position above health bar row. RESULT: DEPLOYED — pending player test
[2026-06-20] medkit.scr medkit_use — standing heal changed from +50 HP partial restore to full health (health level.coop_health). Removed local.new_health calculation and healthonly call. WHY: player confirmed full restore is correct behavior, matching self-revive. RESULT: PLAYER CONFIRMED
[2026-06-20] medkit.scr medkit_hud_monitor — icon slot 36 final position 5 -62 16 16; count slot 37 final position 23 -60. WHY: iterative bracketing from player in-game feedback. RESULT: PLAYER CONFIRMED PERFECT
[2026-06-20] MEDKIT SYSTEM COMPLETE — Player confirmed all features working: full health restore on standing heal and self-revive, HUD icon position perfect, health pack refill working at both injured and full health, movement cancel working on both heal types, cloth wrap and exhale sounds confirmed, DBNO dialogue randomization confirmed, enemy drop frequency at 10 confirmed. RESULT: PLAYER CONFIRMED ALL WORKING
[2026-06-20] cgame.dll v1 — built from HEAD (0.83.0). RESULT: FAILED — game crashed on map load. Root cause: ABI break in commit f8854080 (Aug 23 2025) added 3 fn pointers to cgameImport_t without bumping CGAME_IMPORT_API_VERSION. Integer version check (3==3) passed; struct layout mismatch caused crash.
[2026-06-20] cgame.dll v2 — rebuilt at commit a72bc153 (Aug 3 2025, matching installed v0.82.1-beta). Root CMakeLists.txt patched to add cgame directly after qcommon and guard server block. cg_main.c:147 CVAR_CHEAT→0. Output: 556 KB Release build. RESULT: DEPLOYED — pending player test
[2026-06-20] THIRD PERSON COMPLETE — Player confirmed working via engine fork. cgame.dll rebuilt at commit a72bc153 with CVAR_CHEAT removed from cg_3rd_person. set3rdPerson debug print removed.
[2026-06-20] cover.scr — collision setsize changed from partial-wall (-32 -80 0)(56 -20 56) to full QUAKED bounds (-32 -80 0)(56 88 56). WHY: SOLID_BBOX setsize does not rotate with entity angles — partial box only aligned with visual model at one specific world angle. Full bounds works correctly at all placement angles. See: SOLID_BBOX setsize does not rotate (Known Limitations). RESULT: DEPLOYED — pending player test
[2026-06-20] COVER SYSTEM COMPLETE — Custom coop_sandbag.tik created using sandbag_link_main.skd at scale 0.52. Collision from authoritative .map clip brush data: ( -13 -52 0)(10 52 47). Placement sound coop_sandbag_place (body_falldirt_04.wav) added to ubersound.scr. Model angle = player yaw only, no offset. RESULT: PLAYER CONFIRMED ALL WORKING

[2026-06-21] coop_mod/officer.scr — full officer boss feature implemented: officer spawn (german_waffenss_officer.tik, 2000 HP), radio station (radio_military.tik, 80 HP, destructible), 2 bodyguards, 7 reinforcement wave types (elite squad, MG nest, sniper team, grenadier, artillery strike, support squad, patrol team), HP-threshold retreats at 75/50/25% (waves) and 15% (medkit retreat to nearest health entity), radio broadcast to all players. WHY: core officer boss mechanic. RESULT: DEPLOYED — awaiting player test
[2026-06-21] coop_mod/officer.scr — coop_officer_marker simplified: lightswarmers removed (cgame overhead icon handles identification), glow-only marker (script_model dummy.tik + light red 300). WHY: lightswarmers were redundant once cgame icon was added; cleaner visual. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr + cgame cg_modelanim.c — cgame overhead icon restricted to actors with RF_EXTRALIGHT ("betterlighting") rendereffect. Set on: officer, 2 bodyguards, elite squad, MG gunner + spotter, sniper, grenadier. NOT set on regular map enemies. cgame gate: ET_MODELANIM + EF_AXIS + RF_EXTRALIGHT + !EF_DEAD. WHY: icon was gated on EF_AXIS alone which would show on all German enemies; betterlighting restricts to boss-encounter actors. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr coop_radio_broadcast — radio chatter now played per-player (playsound on each $player[N]). WHY: radio entity playsound is 3D-positional; players far from the cardtable couldn't hear it. Per-player loop guarantees full-volume regardless of distance. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr coop_officer_medkit_retreat — corrected to scan for nearest "Health" classname entity (getentbyentnum loop) instead of running to radio position. Officer runs there, heals to 1500 HP over 10 ticks, resets HP thresholds. WHY: background agent had implemented retreat to radio position instead of health entity. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr — CRITICAL BOM FIX: PowerShell Set-Content -Encoding utf8 added UTF-8 BOM (EF BB BF) which silently killed entire file. Stripped with byte-level WriteAllBytes. File verified clean: 0 BOM, 0 high bytes, 28278 bytes. WHY: officer and all reinforcements stopped spawning after mass-replace edit. RESULT: FIXED — deployed
[2026-06-21] coop_mod/officer.scr coop_radio_broadcast — player loop fixed from 0-indexed to 1-indexed ($player[1] through $player[$player.size]). WHY: $player[0] is world entity; 0-indexed loop was operating on world entity for first iteration. RESULT: FIXED — deployed
[2026-06-21] coop_mod/precache.scr — removed lightswarmers_small.tik cache line. WHY: lightswarmers no longer used in officer encounter (replaced by cgame overhead icon). RESULT: DEPLOYED
[2026-06-21] cgame cg_modelanim.c + scripts/coop_hud_sprites.shader + textures/hud/axis_headicon.tga — ICON FIX: overhead icon never rendered because R_RegisterModel("axis_headicon.spr") called SPR_RegisterSprite which looks up shader "textures/hud/axis_headicon" — that shader did not exist in any pak. Created shader (spritegen parallel, nofog, references axis_headicon.tga) + 32x32 BGRA TGA (red target circle). Added 3-strike warning print on RegisterModel failure. cgame rebuilt + deployed. RESULT: DEPLOYED — awaiting player confirmation
[2026-06-21] coop_mod/officer.scr — AT team wave type 6 added: coop_spawn_at_team (panzerschreck gunner + mp40 loader), coop_at_fire_loop (scripted fire, max 5 shots, 5s reload, 1-indexed player loop). randomint 6→7. precache: added panzerschreck.tik + panzerschreckshell.tik. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr coop_spawn_sniper — spawn pushed 700 units further back (behind officer direction); accuracy 95→100; mindist 512→800; maxdist 2048→3500; leash 4096→6000; noticescale 100 added; coop_wave_hunt removed (replaced with inline nosurprise+forceactivate — no runtoClosest loop so sniper holds distance). RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr — dog pack wave type 7 added: coop_spawn_dogs (2x german_shepherd.tik + german_hund_hundpatrol.tik handler with mp40), coop_dog_hunt (attackplayer loop every 5s). randomint updated to 8 (types 0-7). precache: german_shepherd.tik + german_hund_hundpatrol.tik. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr coop_officer_spawn — officer random skin pool added: randomint 4 picks between german_waffenss_officer.tik (default), german_Wehrmacht_colonel.tik, german_Wehrmacht_officer.tik, german_elite_gestapo.tik. precache: all 4 models added. RESULT: DEPLOYED
[2026-06-21] coop_mod/officer.scr + precache.scr — Wehrmacht path typo fix: agent wrote "german_Wehrmacht_colonel/officer.tik" (9-char correct German) but pak stores "german_Wehrmacht_colonel/officer.tik" (8-char game typo — missing h before t). Fixed via byte-level replacement (PowerShell). Verified with ASCII bytes: should be w,e,h,r,m,a,c,t = 8 chars. RESULT: DEPLOYED
[2026-06-21] ubersound.scr + coop_mod/officer.scr coop_radio_broadcast — added coop_radio_chatter_2 alias (shortwave4.wav, same soundparms). coop_radio_broadcast now randomizes between chatter and chatter_2 (randomint 2). WHY: variety in radio sound on each reinforcement call. RESULT: DEPLOYED

---

## Sprite Shader System (cgame overhead icon fix)
Status: DEPLOYED 2026-06-21 — awaiting player confirmation

Root cause documented: R_RegisterModel("file.spr") calls SPR_RegisterSprite() which strips .spr
and looks up a shader named "file" via R_FindShader. No shader = hModel 0 = function returns
before drawing. Fix: create scripts/*.shader with the sprite definition + provide the TGA.

Shader format for MOHAA sprites (scripts/ directory, not shaders/):
  name_of_sprite_without_extension  <- must match what SPR_RegisterSprite looks up
  {
      nofog
      nopicmip
      nomipmaps
      spritegen parallel    <- or parallel_oriented / parallel_upright / oriented
      spritescale 1.0
      {
          map textures/hud/myicon.tga
          blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
          alphaGen vertex
          rgbGen vertex
      }
  }

Files added: scripts/coop_hud_sprites.shader, textures/hud/axis_headicon.tga (32x32 red circle)

---

## Next Session
Target: Player test the officer boss encounter. Confirm: overhead icon shows (red circle on boss actors only), AT team fires panzerschreck, dogs attack, skin pool shows varied officer models, radio chatter alternates between shortwave3/4.
Pending work:
  - P4 pre-ship cleanup: remove all debug iprintlnbold prints, restore wait 75 in reinforcements (currently wait 15), remove god mode (developer.scr + player.scr:517 + BIND.SCR:46)
  - Boss healthbar: ihuddraw slots 45-47
  - addobjective calls: mission tracker integration
  - Afrika Korps bodyguard model: german_Afrika_officer.tik on e1-series maps (confirmed path: models/human/german_Afrika_officer.tik)
  - Proper fgame rebuild: requires admin terminal choco install winflexbison3 -y, then cmake with BUILD_NO_SERVER=OFF
Remaining deferred features: per-player FOV, prone animation, red tint overlay (all engine-blocked or in Known Limitations).
