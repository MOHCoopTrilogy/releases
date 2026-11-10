# Frontline missions in the campaigns: integration plan (Phase 2)

**Status:** plan only. Nothing here is implemented yet. It is to be sequenced on top of `spfix2` once
that merges, because the New Game map, chrono, loading screens and the attic overlap with it.

**Scope of the first mission:** `coop_fl_1_1`, Frontline level 1_1, "Seaside Stowaway". The
same mechanism scales to every converted level.

## 0. The rule that drives everything: bring your own disc

- A Frontline map exists **only** on a PC that converted its own disc.
- The shipped mod contains no Frontline data, no tile art and no loading art. It must behave exactly
  as today when nothing is converted:
  - no Frontline tiles;
  - campaigns skip the mission silently;
  - one "Requires your own Medal of Honor: Frontline disc - see Convert Frontline" note where a
    player would otherwise look for it.

## 1. Detection marker (converter output, local only)

The converter adds two files to the **local** pak `zzzz_coop_fl_<level>.pk3`.

**`fl/have_<level>.cfg`.** This sets the per-level flag and recomputes the global one:
```
set coop_flHave_1_1 1
set coop_flHave 1
```

**`fl/meta_<level>.scr`.** This is the metadata (section 2).

The shipped mod adds one silent line to `autoexec.cfg` and to `coop_defaults.cfg` (both live in the
code pak):
```
exec fl/have_1_1.cfg
```
- If the file is missing, the engine prints "couldn't exec" and nothing else happens.
- One line per known level. The list of known levels is ours, not Frontline data.

**Scripts:** `if( getcvar "coop_flHave_1_1" == "1" )` before offering, chaining or cycling the map.

**Menus:** the existing `cvarvisible` / `enabledcvar` widget gates in `.urc` files, keyed on
`coop_flHave_1_1`.

## 2. Metadata: one source of truth

There are two layers.

**Our layer, `docs/tools/frontline/fl_levels.json`.** Committed, with no Frontline text. It holds
the bsp name, the chrono date and the war-map coordinates. These are historical facts that we
research and cite.

**Disc layer, `fl/meta_<level>.scr`.** Generated locally. It holds:
- the display name, read from the disc;
- the objective list (already in `maps/coop_fl_<l>_data.scr`).

The disc's mission and level names live in `DATA/chars.bum` and the `bLog` journal pages. I still
have to locate the level-name string ordinals; until then the converter falls back to the shell
string table.

Fields every consumer reads:

| field | source | used by |
|---|---|---|
| `bsp` | ours | everything (`coop_fl_1_1`) |
| `title` | disc | join card, loading screen, coop tile caption, briefing |
| `mission` | disc | tile header, war-map tag |
| `place`, `lat`, `lon` | ours, researched | war-map pin, join card place line |
| `date`, `time` | ours, researched | chrono order, join card date |
| `unit` | ours | join card unit line (OSS, Lt. Jimmy Patterson's operation) |
| `card_title`, `card_place`, `card_when`, `card_unit` | ours | join card for 1_1: **SEALED ORDERS** (user's choice, 2026-11-09; replaced RETURN TO SENDER, which is daily challenge #57) / St. Mathieu, France / August 17, 1944 - 0900 hrs / Office of Strategic Services. The row is set in `maps/coop_fl_1_1.scr`, because `joincard_titles.tsv` validates against the retail paks |
| `objectives[]` | disc | briefing, objective HUD (already wired) |

**Date and place, resolved from the disc (2026-11-08):** the briefing journal for this level
(`DATA/SHELL/1_1_bLog.viv`, page 1) gives three facts:
- the level is Seaside Stowaway;
- the place is **St. Mathieu, France**;
- the time is **17 August 1944, 0900 hours**.

The date matches the user's. The place is **Pointe Saint-Mathieu**, near Brest in Finistère, Brittany:
lat 48.330, lon -4.771. It is a real headland with a lighthouse, which fits the dock dialogue about a
captain docking near the lighthouse. The level's goal in the story is to reach the Lorient U-boat
pens, which is why "Lorient" is associated with it. The "Périers 7 km" road sign is set dressing
painted for this level only, not evidence of a Normandy setting. The disc never mentions St. Nazaire
or St. Malo. The location table (`chars.bum` @0x2bd0, repeated in `shell.viv` @0x10a36d0) gives
the levels in order:

| level | location |
|---|---|
| 1_1 | St. Mathieu, France |
| 1_2 | Aboard U-4902 |
| 1_3 | Shipyards of Lorient, France |
| 1_4 | Shipyards of Lorient, France |
| 2_1 | Holland Countryside |

**Final (confirmed by the user, 2026-11-08):** coop_fl_1_1 is pinned to St. Mathieu, France (Pointe
Saint-Mathieu, 48.330, -4.771), 17 August 1944, 0900 hours. When 1_3 and 1_4 are ported they take
"Shipyards of Lorient, France". These values are in `fl_levels.json` with their source. Chrono order is unchanged: 17 Aug 1944 sits
before AA M5 (20 Aug 1944, Brest), which is geographically right next door.

**Map name (2026-11-08): `coop_fl_<chapter>_<level>`, not `mfl_*`.** The engine loads scripted animations
per map by name prefix (`includes` blocks in `models/human/new_generic_human.tik`, matched in
`TIKI_ParseIncludes`). `mfl_*` matched no block, so the AI on the map had none of the 69 scripted sets
(weapons, unarmed, interrogation, table...). `coop_*` matches the same block real coop maps use, and both
coop-map tests already accept it (`main.scr::isCoopEnabledMap`, `fgame/sentient.cpp`). The sound-alias
bridge uses the token `coop_fl`, which no other map starts with.

Enumeration audit for players **without** Frontline: nothing in the mod's scripts, configs or menus lists
`coop_*` maps by prefix. The MP map pickers and the rotation setup scan only `maps/dm`, `maps/obj` and
`maps/lib`. The only root-level scan is the dev `maplist` button (`UI_MapList_f`), which can list only
BSPs present on that PC, and `coop_fl_*.bsp` exists only in a disc owner's locally generated pak. Every
hard-coded list added in section 3 (campaign chain, server menu tile, maptest, loadart, join card) is
gated on `coop_flHave_<l>`.

## 3. Touchpoints

The exact files are below.

**Campaign order and next-map chaining**
- **File:** `coop_mod/maplist.scr` (array `local.maps`, next/previous map).
- **Hook:** insert `coop_fl_1_1` after the Frontline-inclusive predecessor. Wrap the lookup so a missing
  map is stepped over: `waitthread fl_skipIfMissing`, which checks `coop_flHave_*`.
- **Missing map:** skipped silently.

**Begin Full Campaign**
- **Files:** `coop_mod/cfg/campaign_start.cfg`, plus the order in `coop_mod/maplist.scr`.
- **Hook:** the order proposal is in section 4.
- **Missing map:** skipped silently.

**Chronological campaign**
- **Files:** `coop_mod/chrono.scr` (on `spfix2`) and `ui/coop_chronoresume.urc`.
- **Hook:** per `docs/proposals/chrono_campaign_2026-11-08/ORDER.md`, place `coop_fl_1_1` (17 Aug 1944,
  Lorient) between AA M4 "Behind Enemy Lines" (22 Jun 1944) and AA M5 "The Day of the Tiger"
  (20 Aug 1944, Brittany/Brest), i.e. immediately **before AA M5**. The resume/next logic already
  skips by list.
- **Missing map:** skipped silently.

**Coop mission select (flat)**
- **Files:**
  - `ui/coop_maps.inc`, GENERATED by `docs/proposals/mpui_2026-11-02/make_mpui.py`;
  - `ui/coop_start/*.cfg`, GENERATED by `docs/proposals/mission_tile_art_2026-09-29/tools/gen_wiring.py`.
- **Hook:** a "Frontline" campaign group in the generator. The tile art cvar points at a texture the
  converter writes into the local pak (section 5).
- **Missing map:** the tile is hidden (`cvarvisible coop_flHave_1_1`), and one note tile is shown
  instead.

**3D mission select / attic**
- **Files:** `ui/hzm_newgame3d.urc` and the attic menus (attic build).
- **Hook:** the same `cvarvisible` gate.
- **Missing map:** hidden.

**Coop server/start map list**
- **File:** `ui/coop_start.urc`, the map dropdown, generated by the same `make_mpui.py`.
- **Hook:** an entry gated on `coop_flHave_1_1`.
- **Missing map:** hidden.

**SP New Game war map**
- **Files:** `ui/hzm_newgame3d.urc`, `ui/hzm_ng3d_mission*difficulty.urc` (`spfix2`).
- **Hook:** the pin, tag and lock read the metadata. The pin is gated on `coop_flHave_1_1`; locks
  follow campaign progress.
- **Missing map:** no pin.

**Join card**
- **File:** `coop_mod/joincard_table.scr`, GENERATED by `docs/tools/gen_joincard.py` from
  `docs/tools/joincard_titles.tsv`.
- **Hook:** a row for `coop_fl_1_1` whose title/place/date come from the metadata at run time. Frontline
  text can't be stored in the TSV, so the row says "read `level.fl_title`". The map script sets that
  from `maps/coop_fl_1_1_data.scr`.
- **Missing map:** not applicable.

**Loading screen and loading clip**
- **Files:** `ui/loadart.txt`, `scripts/coop_loadart.shader`, the engine `LOADART` / `LOADCINE` rules
  (`openmohaa-hzm-loadart`).
- **Hook:** loadart pool entry `coop_fl_1_1 -> textures/fl/1_1/loadart` (rendered locally, section 5).
  LOADCINE keeps "skip, no rule".
- **Missing map:** not applicable.

**Spawn locations**
- **File:** `coop_mod/spawnlocations.scr` (already on branch `frontline`: label `coop_fl_1_1`).
- **Missing map:** not applicable.

**Briefing**
- **Files:** `ui/missionbriefingback.inc`, `coop_mod/menumirror.scr`.
- **Hook:** briefing slides come from the disc's `bLog` journal pages, which the converter turns into
  local TGAs.
- **Missing map:** not applicable.

**SP path**
- **File:** `maps/coop_fl_1_1.scr`.
- **Hook:** with `g_gametype 0` the coop framework stays off. Objectives, set pieces and the mission
  end go through `global/missioncomplete.scr` as on the stock SP maps. This must be verified in SP
  (Phase 1 item).
- **Missing map:** not applicable.

**Challenge: "Saving Private Castro"** (user request 2026-11-09; built in Phase 2 because it touches mainline
challenge files)
- **What:** the optional rescue on `coop_fl_1_1`. Kill the interrogating officer before the execution shot,
  and Castro gets up, takes a rifle and fights with the squad. Completed when Castro is **rescued and alive at
  mission end**, in coop or SP. The map already tracks this: `level.fl_interrogState == "rescued"` plus
  `isalive level.fl_castro` at `FLMISSION complete` (prints `FLSET prisoner survived to mission end`).
- **Files:**
  - `coop_mod/challenges.scr`: one `chal_def`, APPENDED, ASCII only (the file's own rule):
    `"evt_saving_castro" "campaign" "Saving Private Castro" "Rescue Private Castro from the interrogation
    and bring him through Seaside Stowaway alive" "evt_saving_castro" 1 <reward>`.
  - The writer is `chal_team_bump "evt_saving_castro" 1` at that point in `maps/coop_fl_1_1.scr`, the
    same call m1l2a makes for "Cut Him Down".
  - Read `docs/generated/FIX_INDEX.md` for `challenges.scr` and `mvchal_gen.scr` first.
- **Reward (proposal):** the existing XP bonus (`xp_team_award 30 "objective" "Prisoner Rescued"`, already
  in the map) plus the challenge's cosmetic. Challenges here reward a player skin, so the proposal is an
  unused US enlisted skin that suits a rescued GI. Pick it from the reward pool with
  `docs/tools/unlock_audit.py`, which must pass: a writer, a reachable target and a real reward.
- **Visibility:** shown only when `coop_flHave_1_1` is set. Players without the disc never see a challenge
  they cannot complete. The Service Record / medals list filters on it, the same gate as the server tile.
- **MP isolation:** the bump only runs on `coop_fl_1_1` in coop or SP. `chal_team_bump` already skips MP
  runs, and nothing writes the stat from an MP mode.

**Cutscenes** (user request 2026-11-09: "We will need cutscenes too to work")

What the disc has (scan of every level and `DATA/MOVIES`):
- **Films:** `DATA/MOVIES/*.mpc`, 24 files, 1.04 GB. Each is EA `MPCh` chunks around MPEG-2 640x448 at
  29.97 fps, plus EA ADPCM R1 stereo 48 kHz audio; ffmpeg's electronicarts demuxer reads them.
  - campaign: `brief11`, `brief21`, `brief31`, `brief41`, `brief51` (one briefing per mission), `intro`,
    `title`, `ealogo`, `credits`;
  - extras, not campaign: `history1-6`, `making1-6`, `extras1-2`, `demo`.
- **In-engine camera scenes** (placed `.bpd` objects and `.cbs` scripts):
  - 1_2: `CrateCam_1_2` / `PlayerInCrateCam1_2`, inside the stowaway crate;
  - 1_4, 4_1, 4_2, 5_4: the `Sturmgeist*Cam*` villain scenes;
  - 2_1: `Buddy_Intro1`;
  - 3_1: `Captain_Tarver_Intro`;
  - 5_1: `M5_1_SpyCamera`, `TrunkLidSpyCamera5_2`, the flying papers;
  - 6_1: the D-Day landing camera (`DDayMovingCameraScript` / `DDayPlayerCameraScript` plus intro lines).
- **1_1:** no camera scene. It has the aircraft flypast (`FlyThrough_1_1`, 7 placements; Stuka/P-47 `.mvd`
  motion) and the P-47 set piece, already rebuilt. Its cinematic is the mission briefing film `brief11`.

Plan:
1. **Films = briefing maps**, copying the stock SH/BT recipe (`maps/briefing/briefinge1.scr`):
   - the film goes out in SERVERINFO (`sets coop_briefvideo`), so every client plays it together and a late
     joiner joins mid-film, with a per-player `cinematic` for old exes;
   - skip uses the coop READY gate (the whole squad), and SP uses the vanilla skip;
   - a 210 s safety cap.
   The pilot is `briefing/briefingfl1` -> `coop_fl_1_1`:
   - `docs/tools/frontline/flmovies.py` (player's PC) encodes `brief11` to `video/flbrief11.roq`;
   - the briefing room BSP is a copy of the player's own `maps/briefing/briefinge1.bsp`;
   - both go into the local `zzzz_coop_fl_m1_brief.pk3`; the script `maps/briefing/briefingfl1.scr` and an
     empty `spawnlocations` label are mod side.
   - The RoQ follows the stock layout exactly: 512x256 with no audio chunks, plus `video/flbrief11.wav` beside it.
     The engine streams `<movie>.mp3`, then `.wav`, as the film's sound (`S_SetupMovieAudio`).
   - The first take (512x352 with roq_dpcm audio inside the RoQ) was published to the player and played, but the
     engine closed it in the same second: `trFMV::stop` came straight after `play`.
   - The stock-layout take still needs one in-game check.
   - Frontline's films have no subtitle track, so none are added.
2. **Camera scenes:** rebuild with MOHAA's cinematic recipe, copied from the stock scripts:
   - camera entities on a path, `cuecamera` / `follow`, `freezeplayer` and `drawhud 0`, letterbox;
   - the mod's cutscene lock: every player frozen and protected, skippable by the host or a vote, late
     joiners are put into the scene;
   - subtitles from the cue banks where the disc has them.
   Pilot candidate: 1_2's crate camera (the next level after 1_1).
3. **Order:** briefings first (one tool, five films), then the camera scenes level by level as each
   level is ported.

## 4. Where Frontline sits in the Full Campaign (proposal)

Story order, not disc order:
1. Frontline M1 D-Day (6_1, 6_2) is the same day as MOHAA's Omaha (m3l1).
2. Frontline's Lorient chapter (1_1–1_4) follows D-Day.

Proposal: **after `m3l3`**, the end of MOHAA's Normandy chapter, and **before `m4l0`**. The Full
Campaign then runs Torch, Norway, D-Day (MOHAA), then Frontline "A Storm in the Port", then Sniper's
Last Stand.

If a player lacks the conversion, `maplist.scr` skips straight from `m3l3` to `m4l0`, exactly as
today. Chrono uses the researched date instead (section 2).

## 5. Art rendered on the player's PC (never shipped)

All of these are produced by the converter after conversion, into the local pak:
- **Coop tile art:** an engine screenshot from a fixed eye-height viewpoint listed in our
  `fl_levels.json`, taken with the same background-window harness rules. It is cropped to the tile
  size and named `textures/fl/1_1/tile.tga`.
- **Loading art:** the same mechanism, 16:9, `textures/fl/1_1/loadart.tga`.
- **War-map pin:** our own art (a shipped generic pin) plus the text from the metadata.
- **Fallback:** if the client can't render (headless/server), use a neutral "Frontline" tile with the
  converted title. The server doesn't need art.

## 6. Multiplayer join without the map

**Today:** a client without `maps/coop_fl_1_1.bsp` gets the engine's missing-map path. Downloads are off
for this content, which is correct: it must never be served.

**Hook:** `client/cl_parse` / `CL_InitCGame` map-missing check (engine). On a map name starting
`coop_fl_`, replace the generic error with: "This server runs a Frontline mission. You need your own
Medal of Honor: Frontline disc - see Convert Frontline in the HZM installer." Then return to the menu.
No hang.

The server also needs `sv_allowDownload` refusal for `zzzz_coop_fl_*.pk3` and `zzzz_fl_hdtex_*.pk3`.
This is a hard filter in `sv_client.c`, so a misconfigured server can't leak converted data.

**Public servers:** untouched. They can host `coop_fl_*` only if converted there. That is the operator's
own disc.

## 7. Order of work after `spfix2` merges

1. Marker + metadata in the converter (`flpack.py`), plus the `autoexec.cfg` / `coop_defaults.cfg`
   exec lines.
2. `maplist.scr` skip-if-missing, plus Full Campaign insertion.
3. `make_mpui.py` / `gen_wiring.py` groups and gates: flat tiles and server list.
4. Chrono entry, once the date is verified.
5. War-map pin (`spfix2` files).
6. Join card: run-time title.
7. Local tile and loading art render.
8. Engine: friendly missing-map message and download refusal (`frontline-eng`).
9. Full test matrix:
   - with and without a conversion;
   - SP and coop;
   - Full and chrono campaigns;
   - a join without the map.


## 8. Bring-your-own-disc, made near-effortless (installer and updater)

User decision, 2026-11-08: Frontline stays bring-your-own-disc. Converted data is **never** shipped.
That covers git, releases, the auto-updater payload and the public servers.

**Optional installer/updater step: "Have Medal of Honor: Frontline? Point us at your disc image."**
- **Auto-detect** candidates in: the root of each drive, Downloads, Documents and Desktop. Look for
  `*.iso`, `*.xiso`, and `*.zip` that holds an Xbox image (zip members are listed without extracting).
- **Verify** against the shipped hash table:
  - USA Xbox first: full-image SHA1 `C5F234B9...C4C6`. A fast pre-check uses the XBE title ID
    `0x4541001A` plus key-file hashes.
  - PAL rows come later.
  - On a mismatch, the message is "This isn't a supported Frontline disc image" and nothing is
    written.
- **Convert in place.** It reads the image directly; a zip needs one streamed temp copy. That takes
  about 30 s per level, plus the optional local upscale (GPU, one job, with a fallback if
  Vulkan/GPU is missing).
- **Write locally:**
  - the map/audio pak `zzzz_coop_fl_<level>.pk3`;
  - the optional `zzzz_fl_hdtex_<level>.pk3`;
  - the marker `fl/have_<level>.cfg`.
- **UI:** a progress bar, then a clear success message ("Frontline: Seaside Stowaway added") or a
  failure message with the reason.

**Remember the path** in the installer's own settings (`installed_manifest.json`, a `frontline` block:
image path, image SHA1, converter version, the generated paks and their sha256).
- When the converter version changes, the updater re-converts silently from the remembered image.
- If the image is gone, it skips quietly and keeps the old local paks.

**In game:**
- **Without the disc:** Frontline is hidden everywhere (section 0). There is optionally one line in
  the coop menu: "Own Frontline? Add it in Settings -> Frontline."
- **Settings -> Frontline** runs the same conversion later: pick or detect, verify, convert, then
  restart the menu to pick up the new paks.

**Hard guarantees:**
- The updater payload carries only our code and the hash table.
- `sv_allowDownload` refuses `zzzz_coop_fl_*` and `zzzz_fl_hdtex_*` (section 6).
- A CI/pre-commit scan rejects FL magics (`BIGF`, `SCHl`, `SHPX`, `MPCh`) and those pak names.

**Onboarding, approved by the user 2026-11-09** (built in Phase 2; refines the bullets above):
- **Installer page:** optional, after the main install: "Own Medal of Honor: Frontline? Add its campaign".
  **Skip is the default**, so pressing Next through the installer never touches Frontline. **Add**
  auto-detects the image in the drive roots, Downloads, Desktop and Documents, or lets the player browse.
  Then verify, convert, done, with the progress and result UI above.
- **Existing players:** a one-time What's New line plus an "Add Frontline" button. It never prompts again
  (one seen-flag in the installer settings).
- **Attic prop** (the in-world home for the feature, per the attic rule): a Frontline object on the attic
  shelf. Options are a Frontline game case, or the St. Mathieu / Lorient map rolled on the shelf. It lights
  up on hover like the other attic props.
  - **Without Frontline:** it opens the Add Frontline step (file picker or auto-detect, convert, progress,
    result).
  - **With Frontline:** it shows the converted missions and a **Re-convert** option.
  - The model, placement and bake are coordinated with the attic agent, which owns the attic scene. Test
    with `ui_atticMain 1`.
- **Classic menu:** a Settings -> Frontline entry with the same actions, for players without the attic.
- **Updater:** remembers the image path and re-converts silently whenever the converter version changes.
  Failures go to a log plus a dismissible note, and **never block launch**.

## 9. Hard requirement: Frontline never gets in the way of the rest of the mod

**Installer/updater**
- The Frontline step is **off by default** and skippable with one click.
- It runs only **after** the main install or update has completed, with a timeout (10 min per level,
  2 min for detection).
- Failure, cancel or timeout:
  - is logged to `frontline_convert.log`, plus a dismissible note in the What's New card;
  - **never** shows a blocking modal;
  - never fails or rolls back the install, update or launch.
- The converter writes only to a temp file, then renames it to its own `zzzz_coop_fl_*` / `zzzz_fl_*`
  paks and `fl/` marker. It never touches any other file. A half-written pak is deleted, and the
  previous good one is kept.

**Campaigns**
- **Without Frontline:** `maplist.scr` / `chrono.scr` behave byte-identically to today. The Frontline
  entries are filtered out before the list is built, so there is no gap, no extra step and no lock
  that waits on them.
- **With Frontline:** the mission is inserted. The successor's unlock is computed as if Frontline
  were absent. "Unlock m5l1 after m4l3" stays the rule, so skipping or never playing Frontline can't
  strand progress. Frontline's own unlock depends on its predecessor, never the other way round.

**Multiplayer: proposal**
- A server only rotates or chains into an `coop_fl_*` map when **every connected player** advertises it.
  The client userinfo carries `fl_have` with a bitmask of converted levels, set from the marker cfg.
- Otherwise the server skips to the next non-Frontline map. A player who joins mid-Frontline-map
  without it gets the clear message (section 6) and is returned to the menu. Nobody else is affected.
- The alternative (keep the map and spectate those players) was rejected, because it strands them.
- Public servers stay off Frontline. Their map lists don't include `coop_fl_*`.

**Performance and size without Frontline**
- No Frontline pak is present, so there is no mount.
- The only cost is the one `exec fl/have_*.cfg` line, which fails silently.
- `maps/coop_fl_*.scr` is never loaded (no map).
- The `anim/pain.scr` fallback is a two-line guard with no measurable cost.
- Measure it: boot time, memory, and the pak list.

### No-Frontline regression test (required before any release that carries Frontline code)

Run on a fresh install **without** the disc, and compare against the current release build:
1. The installer completes with the Frontline step skipped. The updater runs clean; there's no new
   modal or note beyond "Frontline: not added".
2. **Full Campaign:** Begin starts `co_lobby1`, then `briefing1`, then `m1l1`. The chain across
   `m3l3` to `m4l0` is unchanged (scripted run through `maplist.scr` next-map logic).
3. **Chronological:** starts, and the order lists no Frontline entry. The step from AA M4 to AA M5 is
   direct.
4. **SP New Game:** the war map shows no Frontline pin, and the locks and unlocks are identical
   (scripted unlock-state dump vs the current build).
5. **Coop join:**
   - a host and a client both without Frontline: join, play and mission-complete as today;
   - a mixed lobby (one client has Frontline): the server never enters `coop_fl_*`.
6. **Cost:** the same pak list; boot time within noise; the same Script Error count (0).

## 10. Release plan: Frontline + European Assault pilots playable in coop by v1.10.70

User target (2026-11-09): "I want Frontline/European Assault map pilots playable in coop by .70". v1.10.66 is
live. The Frontline side owns the shared bring-your-own-disc delivery; the EA agent plugs its converter into it.
Campaign and chrono slots (section 4) come in a later version unless they turn out cheap.

**One shared tool, our code only: `hzmconv.exe`.**
- **What it is:** a standalone build (PyInstaller one-folder) of the Frontline converter, the EA converter and
  the optional upscale step. Players need no Python. It contains only our code plus the runtimes listed below,
  with **no EA bytes**.
- **Shipping:** in the mod's updater payload, sha256-listed in the manifest. If code-signing is available at
  release time, the exe is signed too.
- **Interface both games share (the EA agent implements its half):**
  - `hzmconv detect` lists candidate images (drive roots, Downloads, Desktop, Documents).
  - `hzmconv verify --game frontline|ea --image P` checks the hash table.
  - `hzmconv add --game frontline|ea --image P --home <maintt>` converts, then writes the local paks and
    the marker `fl/have_<l>.cfg` or `ea/have_<l>.cfg`.
  - Progress goes to stdout as JSON lines, read by the installer UI.
  - Per game, a Python module provides `verify(image)`, `levels()`, `convert(image, level, out_dir, progress)`.
- **Bundled runtimes and licences (checked before shipping):**
  - Python (PSF);
  - numpy, Pillow (BSD/HPND);
  - vgmstream-cli (ISC-style permissive), one build shared by both games:
    - the EA agent's MPEG-enabled build (EA's EALayer3 music needs mpg123);
    - it goes in as `tools/vgmstream/vgmstream-cli.exe`;
    - `hzmconv_ea.py` expects that path and drops music if it is missing;
    - Frontline uses the same build only if the converted 1_1 pak is byte-identical (sha256) to the one from
      the plain build; otherwise Frontline keeps the plain build in its own folder.
  - libmpg123 (LGPL-2.1):
    - a dynamic DLL, `libmpg123-0.dll`, placed next to vgmstream-cli.exe;
    - built with MSVC x64 from mpg123-1.32.12 (sha256 9ed33460…2e55, GPG-verified against Thomas Orgis' key);
    - shipped with COPYING (LGPL-2.1) and a link to the source tarball. Being a DLL, a user can swap it out.
  - realesrgan-ncnn-vulkan (MIT) and its x4plus weights (BSD-3), optional;
  - films (MPEG-2 decode, RoQ encode): our own **minimal LGPL-2.1 ffmpeg 8.1**:
    - built with MSYS2/MinGW from the signed source tarball (sha256 b072aed6…756a);
    - a static `ffmpeg.exe` of 2.2 MB with no external libraries, `License: LGPL version 2.1 or later`;
    - only these parts are enabled: the EA and RoQ demuxers, the mpeg2video, adpcm_ea_r1 and RoQ decoders, the
      RoQ encoders and muxer, the pcm_s16le encoder and wav muxer (film sound), scale/crop/format/aresample/fps,
      and file I/O;
    - its RoQ output is byte-identical to the BtbN LGPL build's (brief11, same sha256);
    - it ships in `tools/ffmpeg/` with COPYING.LGPLv2.1, `CONFIGURE_LINE.txt` and the source link
      https://ffmpeg.org/releases/ffmpeg-8.1.tar.xz. The build script `build.sh` is kept beside it.
    - Fallback (Option C): fetch the pinned BtbN LGPL build on demand. Briefing films are optional at runtime.
  - No GPL component is bundled.

**What lands when:**

| version | lands | player-visible without a disc? |
|---|---|---|
| **.67** | Hidden plumbing, MP safety and this plan: `coop_flHave_*` / `coop_eaHave_*` cvars and markers; the userinfo advertise and the server's all-clients rule; the MP missing-map message (section 6); the never-hinder regression test (section 9) in the release checklist | no |
| **.68** | `hzmconv.exe` in the updater payload; **Settings -> Frontline / European Assault** (add, re-convert, status); a one-time What's New line; converted maps listed in the coop map select and the server start menu **only when present**, with title-card text | no (only a Settings entry and one line) |
| **.69** | Installer page (skip by default) and updater silent re-convert; **attic prop** (with the attic agent); EA converter plugged in by the EA agent; real 2-client coop playtests of both pilots, with fixes | no |
| **.70** | Both pilots playable start to finish in coop: 2 real clients, 0 Script Errors, every gate passing (deterministic conversion, patrol < 5%, objectives via the real use key, SP end, fps). Frontline extras: the Castro rescue/execution, the briefing film, the model swaps. The "Saving Private Castro" challenge if the mainline challenge work fits; else .71 with the campaign slots | no |

**Never-hinder test** (section 9) runs at every one of these versions, unchanged. Without a disc: the
campaigns are byte-identical, menus show nothing new beyond the Settings entry and the one-time line, and MP
joins and rotations behave as before.
