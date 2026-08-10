# HOLDOUT — a checkpoint wave-defence gametype

**Proposal · 2026-08-04 · READ-ONLY research. No game file was modified.**

> **The vision (user's words):** *"full single player maps where you move from checkpoint to
> checkpoint and defend waves of enemies — think how Sniper Elite 5 does this. We will need a lobby
> system and menu build out like HZM Coop to setup the game server and then host."*

Every claim below carries a `file:line` anchor. Where an anchor disagrees with this text, the code
wins ([SOURCE_OF_TRUTH.md](../SOURCE_OF_TRUTH.md)). Three load-bearing premises taken from research
agents were re-verified directly against source before being written down, per
[TRAPS.md § T11](../TRAPS.md#t11); they are marked ✅ **verified** at the point of use.

---

## 0. Verdict in one page

**HOLDOUT should be assembled, not invented.** Between the officer wave system, the *retail* map
scripts, and the lobby/ready/XP/challenge layers, roughly 80% of this gametype already exists in the
tree. The genuinely new code is a director loop and a per-map arena table.

**The single most important finding:** *the original MOHAA developers already shipped this gametype.*
`maps/m3l2.scr` and `maps/M3L3.scr` implement checkpoint wave-defence as a repeated four-label
pattern — `sceneN_spawnerM_initialize` → `_spawndetectorM_control` → `_spawnM_detect_death` →
`_spawnM_cleared` → next scene. m3l2 has 84 occurrences of that machinery, M3L3 has 166 across ten
spawner systems. It is already coop-hardened: `maps/m3l2.scr:650-653` doubles the caps under
`if( level.gametype != 0 )`. Per CLAUDE.md's fix methodology (*"find how a confirmed-working map
already handles it, and copy that exact recipe"*), **that pattern — not `coop_call_reinforcements` —
is the architectural template.**

| | |
|---|---|
| **Reuse wholesale** | `playersWarpto` (checkpoint move + respawn re-pin), `readygate.scr` (squad-ready between arenas), `officer.scr`'s standalone spawn helpers, `coop_reinf_count`/`coop_reinf_scale` (player-count scaling), `xp_team_award` / `chal_def` / `chal_team_bump`, `lobby.scr` (setup lobby), `ui/coop_start.urc` + `campaign_start.cfg` (menu + mode-flag start), `maptest_waypoints.scr` (nav-valid arena candidate coordinates) |
| **Extract / generalise** | ~10 `while( level.coop_officer_alive == 1 )` conditions that currently freeze four of the eight wave types when no officer exists |
| **Build new** | `coop_mod/holdout.scr` (the director, ~600-800 lines), `coop_mod/holdout_positions.scr` (per-map arena data), `ui/coop_holdout.urc`, `coop_mod/cfg/holdout_start.cfg`, a Holdout challenge block |
| **Do NOT reuse** | `coop_officer_reinforcements` / `coop_officer_brain` / the HP-threshold state machine — that is boss-fight pacing, not wave pacing |
| **Biggest risk** | Entity-pool exhaustion. Indefinite wave spawning is precisely the failure shape of bugs 914-927. See §5.1 |
| **Phase 1** | m3l2, `coop_holdout 1`, one authored arena, three files touched, no map-script edits |

---

## 1. Existing systems: what plugs in, and what does not

### 1.1 `coop_mod/officer.scr` — the wave system, assessed honestly

**Verdict: the spawners are ~90% reusable. The dispatcher and the lifecycle loops are not.**

`coop_officer_init` is threaded unconditionally from `main.scr:141`; all gating is internal
(`officer.scr:9-11`). The eight wave types dispatch from `coop_call_reinforcements`
(`officer.scr:1455-1486`) — note the file header at `officer.scr:4` lists a **different, stale**
table; the dispatch is the truth:

| Type | Content | Function | Base / cap |
|---|---|---|---|
| 0 | Elite Squad | `coop_spawn_elite_squad` `officer.scr:1890` | 3 / 6 |
| 1 | Wehrmacht Squad (the always-safe fallback) | `coop_spawn_infantry_squad` `:2006` | 3 / 6 |
| 2 | Elite Sniper | `coop_spawn_sniper` `:2138` | 1, no scaling |
| 3 | Grenadier Squad | `coop_spawn_grenadiers` `:2316` | 2 / 6 |
| 4 | Stuka dive bomber | `coop_stuka_attack` `:2571` | no actors |
| 5 | Artillery barrage | `coop_artillery_barrage` `:2733` | no actors |
| 6 | Anti-Tank Team | `coop_spawn_at_team` `:2778` | fixed 2 |
| 7 | Attack dogs | `coop_spawn_dogs` `:2948` | 2 / 5 + handler |

Selection is a masked random roll (`officer.scr:1425-1433`) against `level.coop_wave_mask`, tested by
integer division because MOHAA has no bitwise AND (`coop_wave_allowed`, `officer.scr:1358-1373`).
**That mask is a per-arena difficulty knob for free** — e.g. an interior arena sets the mask to
exclude 4/5, exactly as `officer_positions.scr` already does per map via
`level.coop_officer_no_airstrikes`.

**Spawn positioning already generalises.** `coop_call_reinforcements` prefers
`level.coop_officer_reinf_zone` and falls back to `officer.origin - fwd*500`
(`officer.scr:1392-1397`), then applies a Z-tolerance rejection (`:1399-1420`) and fans individuals
out through `coop_spread_pos` (`:1589-1620`) — a capped spiral, 80..360u, hardened after battalions
were once flung ~1240u into walls.

**Hard blockers if you call it standalone.** `coop_call_reinforcements` opens with
`if( level.coop_officer == NULL ){ end }` (`officer.scr:1377`), and roughly ten behaviour loops spin
on `while( ... level.coop_officer_alive == 1 )`. With no officer: grenadiers never throw
(`officer.scr:2888`), the AT gunner never fires (`:2841`), the sniper never repositions (`:2211`),
only dog #1 spawns (`:3004`, `:3039`), and `coop_squad_monitor` exits on its first tick (`:1952`).
`coop_nearest_player_pos` (`:2646-2664`) measures distance *from the officer*, so with a NULL officer
every distance reads 0 and it silently returns the **last** player rather than the nearest — a
wrong-answer bug, not a crash.

**Already standalone, drop-in, zero changes:** `coop_find_ground` (`:1217`), `coop_spread_pos`
(`:1589`), `coop_reinf_pc`/`coop_reinf_count`/`coop_reinf_scale` (`:1494-1582`), `coop_model_for`
(`:446`), `coop_wave_allowed` (`:1358`), `coop_apply_personality` (`:1629`), `coop_wave_hunt`
(`:1311`), `coop_push_toward` (`:1275`), `coop_prone_shooter` (`:1675`), `coop_idle_patrol` (`:3402`),
`coop_hasOpenSky` (`:2699`), the whole `coop_air_bombing_run` chain. Three of these are *already*
reused outside officer.scr — `aihandler.scr:247` calls `coop_spread_pos`, `aihandler.scr:270` calls
`coop_apply_personality`.

**⭐ The best existing template is `coop_spawn_death_battalion` (`officer.scr:3327-3392`)** ✅
**verified by direct read.** Its own comment at `:3325-3326` says it is *"NOT gated on
coop_officer_alive"*. Signature `(local.pos, local.ang, local.msg, local.hold, local.seed)`:

- player-count scaled through `coop_reinf_count 10 "coop_officerBattalionPer" 3 22` (`:3336`)
- `local.seed` widens the scatter ring so a second wave at the same point does not stack (`:3339`)
- **`local.hold == 1` = dig in and guard, engaging on sight; `hold != 1` = march at the players**
  (`:3351`, `:3371-3389`). That single flag is "defenders hold the arena" vs "attackers push the
  arena", already written and already tuned
- per-trooper: mixed loadout, `coop_reinf_scale` for health/accuracy, `coop_wave_glow`,
  `coop_personality_set` so `coop_reinf_brain`'s hurt manager still covers them

**Recommendation:** write a fresh `holdout.scr` director. Reuse the standalone helpers. Model the
wave spawner on `coop_spawn_death_battalion`, **not** on `coop_call_reinforcements`. Optionally
extract the officer-liveness gate later (§6, Phase 4) — replacing ~10 `level.coop_officer_alive`
tests with a generic `level.coop_waveSystemActive` is the one change that would unlock wave types
2/3/6/7 for any caller, and it is mechanical.

### 1.2 The retail precedent — checkpoint wave-defence, already shipped ⭐

✅ **verified by direct read of `maps/m3l2.scr`.** `scene3_spawner1_initialize:` (`m3l2.scr:644-659`):

```
	level.scene3_spawn1_teamvalue = 0        // total spawned so far
	level.scene3_spawn1_teamlimitmax = 16    // total the arena will ever field
	level.scene3_spawn1_currentalive = 0     // live right now from this spawner
	level.scene3_spawn1_currentalivemax = 4  // CONCURRENCY CAP
	if( level.gametype != 0 ){               // HZM coop - bigger attack for more players
		level.scene3_spawn1_teamlimitmax = 32
		level.scene3_spawn1_currentalivemax = 8
	}
	level.scene3_spawn1_loopwaittime = 1
	level.scene3_spawn1_deactivator = 0
```

The controller (`m3l2.scr:663-782`) loops while `istouching $scene3_spawndetector1` — **a trigger
volume literally defines the arena** — spawns from `$scene3_spawndetector1_spawnerN.origin`
script_origins with inline keyvalues (`spawn models/human/german_waffenss_shutze "targetname" X
"type_attack" "cover"`, `:696`), threads `_detect_death` per actor (which decrements `currentalive`,
`:786-791`), threads `_ai_navigate` to route them in along authored paths (`:795-826`), then
`goto`s itself. `_cleared` (`:968-980`) blocks until `teamvalue >= teamlimitmax && currentalive == 0`
and then `thread scene4` — **the next arena**.

This gives HOLDOUT four things it would otherwise have to invent, and gives them in the shape the
engine was designed around:

1. **`currentalivemax` is the entity-budget answer.** A concurrency cap, not just a total budget.
2. **`teamlimitmax` is the wave-length answer.**
3. **`_detect_death` decrementing a live counter is the wave-cleared answer** — and it never reads
   engine health, which matters enormously (§5.3).
4. **`_cleared` → next scene is the checkpoint-progression answer.**

`M3L3.scr` runs the same architecture across ten spawner systems (`scene3_spawner1..5`,
`scene4_spawner1..4`, `scene6_spawner1`), and `officer_positions.scr:311-320` describes m3l3's own
content as *"scene6 church wave-defense, scene7 nebelwerfers."*

### 1.3 `coop_mod/aihandler.scr` — scaling and the live enemy registry

- **`level.coop_actorArray["german"]`** is the live registry every custom AI layer iterates
  (`aihandler.scr:5-7`, `:601-621`). Membership is the correct "is this wave cleared" oracle.
  ⚠️ Registering into `["american"]` is a **write-only graveyard** — bug-1260 found paratroopers got
  no personality, no maneuver, no squad, no morale, no knockdown because nothing reads that key.
- **Count scaling** — `coop_tryDuplicateActor` (`aihandler.scr:169-236`) clones *actors*, not
  spawners, for every actor entering the world. Excluded: `coop_waveActor` (`:188`), so officer waves
  never double-dip; a HOLDOUT wave must set the same flag. Cvars `coop_aiScale`,
  `coop_aiScaleChance` (def 50), `coop_squadDensity`, `coop_aiScaleTest`. **All three are seeded in
  no shipped cfg** ([OPEN.md § Never ran](../OPEN.md#never-ran)).
- **The hard cap is 80 live Germans** — `level.coop_aiScaleHardCap = 80`, `variables.scr:100`,
  commented *"entity-budget safety"*. Enforced with a `break` mid-batch at `aihandler.scr:228`.
  ⚠️ At `officer.scr:1528-1530` the same cap is only a **soft** clamp: it reduces *extras* back to
  base but never refuses a wave, so repeated waves can exceed 80 indefinitely. **HOLDOUT must enforce
  it hard.**
- **Accuracy scales with player count**; health does not (`calculateAccuracy`, `aihandler.scr:687-716`).
- **`coop_reinf_brain`** (`aihandler.scr:278-462`, threaded from `main.scr:115`) is **not a spawner**
  despite the name. It is one shared 1.5 s manager loop doing bullet-sponge reconciliation, a
  hurt-trooper cover+canteen manager, and idle chatter. HOLDOUT troopers get its hurt manager free
  simply by carrying `flags["coop_personality_set"]`.

### 1.4 `coop_mod/spawnlocations.scr` + `playersWarpto` — the checkpoint primitive

Dispatch is dynamic on the map name (`spawnlocations.scr:13-21`): the label name **is** the map name,
with `/` replaced by `_`. A coop map with no label throws `label X does not exist` every load, which
is why empty stubs exist for co_lobby4-8 (`:209-236`, with the reason stated in-line at `:211`).

An entry is just eight slots of `level.flags["coop_spawnNorigin"]` / `["coop_spawnNangles"]`.
Consumption in `main.scr::playerPlaceAtSpawn` (`:632-709`) maps player index → slot N directly, with
`droptofloor 512` (`:692`, bug-940: authored Z is eye height from the viewpos workflow).

**`<map>_updateN` labels already ARE a checkpoint mechanism** — each advances the coop respawn point
forward through the map, threaded by the map scripts at story beats (~60 call sites, e.g.
`maps/e1l2.scr:302,318,339,349,366`). Maps with the longest chains: **e1l1 (12), e1l4 (11), m2l1 (6),
m3l3 (6), m4l2 (6)**.

**⭐ The whole checkpoint move is one existing call** — `main.scr:590-629`:

```
waitthread coop_mod/main.scr::playersWarpto <origin> <angle> 1
```

With `setSpawn == 1` it overwrites **all eight** spawn slots to that origin/angle (`main.scr:599-607`)
and warps every player there. That is "advance the squad to the next checkpoint and re-pin their
respawn" in a single line.

### 1.5 Lobby, ready gate, clickable UI

- **`lobby.scr::lobbyMapMain`** (`:12-162`) gives camera, auto-deploy, mannequins, roster, ready
  system, countdown and launch. Per-lobby variance is a handful of `level.coop_lobbySlotOrg[1..4]` /
  `coop_lobbyCamOrg` / `coop_lobbyNextMap` vars set *before* the thread (`maps/co_lobby2.scr:18-29`).
  Launch is `stuffsrv ( "map " + local.next )` (`lobby.scr:699`) — deliberately **not**
  `bsptransition`/`loadMap`, which archive on a live coop server and crash (`lobby.scr:639-641`).
- **`readygate.scr::coop_readyGateStart`** (`:15-124`) is the *reusable* squad-ready gate for
  non-lobby maps. Set it going, watch `level.coop_readyGateDone`. **This is the between-arena
  "everyone press F to start the next wave" control, already written.**
- **No client key binds are needed anywhere.** The engine publishes `self.coop_lobbyInput` from the
  usercmd (`fgame/player.cpp:13479-13504`): 31 = D, 32 = A, **33 = F/+Use**. A mouse cursor bridge
  exists too (`player.cpp:13517-13564`, virtual 640×480 + click edge), driving `lobbyui.scr`'s 8-slot
  clickable button framework (`lobbyui.scr:69-80`, AABB hit test at `:111-114`).
- **The lobby maps are copied stock BSPs.** `maps/co_lobby1.scr:2` — *"a copy of training.bsp"*, and
  *"The vanilla training range / radio-instruction scripts are intentionally NOT run here. This map
  only keeps the world + ambience."* Eight such BSPs already ship (4.6-22.8 MB each). **This is the
  proven escape hatch if suppressing a campaign map's vanilla mission proves leaky** (§2.5, §6 Phase 5).

### 1.6 `xp.scr` and `challenges.scr` — scoring is a one-line integration

**XP.** One entry point, `xp.scr:380`:

```
xp_award local.player local.amount local.reason local.label
xp_team_award local.amount local.reason local.label          // xp.scr:745
```

`reason` must be one of the fixed buckets `kills valor objective support revive mission`
(`xp.scr:359`) or the debrief card will not render it. `label` is the free-text crosshair popup.
Persistence is dual-channel per player: write-through cvar `coop_xp_<id>` plus file
`coop_mod/save/xp_<id>.dat` (`xp.scr:281-341`), with an explicit warning never to park XP in `game.*`
because the coop transition wipes it. The end-of-map debrief `xp_summary` (`xp.scr:950-1063`) is
already called from `missioncomplete.scr` and pays Mission Complete 100 / Deathless 50 / Made It 75.

**Challenges.** One `chal_def` line adds a challenge (`challenges.scr:3`, `:451-471`) ✅ **verified**:

```
chal_def <id> <cat> <title> <desc> <stat> <target> <reward>
```

Progress is `chal_bump <player> <stat> <n>` (`:712`), `chal_team_bump <stat> <n>` (`:859`), or
`cc_award_clean <stat>` (`:879`) — the last of which **already excludes anyone who went DBNO this
map**, via `player.coop_wentDownMap` stamped at `dbno.scr:190`. Persistence mirrors XP:
`coop_chal_<id>` cvar + `chal_<id>.dat`, with unlocks on a separate `coop_unlocks_<id>` channel.

### 1.7 `main.scr::main` boot order and gametype gating

`main.scr:35-291` runs ~53 dispatches **synchronously in one frame**; `wait`/`waitframe` are
forbidden in or before it (`main.scr:11-20`). The established hook shape for a new opt-in subsystem
is the cvar-guarded thread used by maptest and build mode:

```
	if( getcvar( "coop_maptest" ) == "1" ){ thread coop_mod/maptest.scr::coop_maptest_tick }   // main.scr:159
	if( getcvar( "coop_build_boot" ) == "1" ){ thread coop_mod/buildmode.scr::coop_build_monitor }  // main.scr:131
```

Coop requires `g_gametype 2`; features gate on `level.gametype != 0` (`main.scr:93-96`). **HOLDOUT is
not a new engine gametype and must not try to be** — it is a mode flag layered on Team Match, exactly
like `coop_campaign`.

### 1.8 Build mode + blueprint as the arena authoring tool

Build mode is a live in-game placement tool (`buildmode.scr`, activated by
`exec coop_mod/cfg/buildmode.cfg`). Its architecture is what matters here:

- **A one-cvar command bus** — every numpad key does `set coop_build_cmd <action>`; the session loop
  polls, executes, clears (`buildmode.scr:22-25`, dispatch at `:239-423`).
- **`modeswap` (`\`) already cycles object → sound → fog → object** (`buildmode.scr:248-282`). *A whole
  parallel mode with its own catalog, own state and own capture file, reusing the same 16 binds, is an
  established pattern.* Adding a **holdout** mode is a near-copy of that seam.
- **Invisible logical markers are already precedented.** SOUND mode places `fx/dummy.tik` —
  *"an invisible script_model"* (`buildmode_sounds.scr:6-9`) — carrying script-var payload, with a
  *visible stand-in ghost* that is never placed (`:154`), and writes its own capture file
  `coop_mod/save/snd_<map>.dat` (`:263`). Radius authoring exists too: sound mode tunes
  `coop_build_sndmin` on the same keys — identical knob shape to an arena radius.
- **Capture format** is paste-ready script text appended to `coop_mod/save/build_<map>.dat`
  (`buildmode.scr:140`, `:727-737`), written to the **homepath**.
- **Blueprint** (`blueprint.scr`) is a template layer on top: anchor-relative offsets in a
  `bpv1,<name>,<count>|<tik>,<fx>,<ry>,<dz>,<ryaw>,<pitch>,<scale>,<solid>|...` line
  (`blueprint.scr:25-30`). `bp_place <origin> <yaw> <name> <mult>` is already a one-call
  *"drop a fortification here"* API, and `bs_remove` (`:495`) deletes a whole composed structure as
  one unit. **An arena's cover set can be authored once and stamped at every checkpoint.**

⚠️ `blueprint.scr` has an open defect — bug-1001, *"all of the items in the blueprints are small
squares"*, with zero `BUILD_BP_PLACE` lines in the session log, i.e. a wiring failure
([OPEN.md:193](../OPEN.md)). Do not put blueprint cover on the Phase 1 critical path.

**The two-path load pattern to copy for arena data** — `fogmode.scr:273-302`: read the homepath
author copy first, fall back to the shipped pak copy, version-tag the header, and **`float()`/`int()`
every parsed field** (bug-1352: the splitters return strings, and a later `>` comparison aborts the
thread at that line while the caller happily prints success).

---

## 2. Gametype plumbing: how HOLDOUT is selected and started

### 2.1 `coop_campaign` is the exact template ✅ verified

The mod already ships a second mode selected from the same menu. `coop_mod/cfg/campaign_start.cfg`:

```
set sv_maxclients 4
set ui_maxclients 4
set ui_dmmap co_lobby1
exec coop_mod/start_server.cfg
set coop_campaign 1        // AFTER the exec - start_server.cfg clears it to 0 at :36
```

`start_server.cfg:36` resets `set coop_campaign 0` so plain single-map play can never inherit a stuck
flag. The flag is then read at `global/missioncomplete.scr:29` to detour the map chain. **HOLDOUT
copies this contract exactly.** Ordering works because `exec` inserts ahead in the command buffer
while `ui_startdmmap`'s payload is appended to the tail behind an explicit `wait;`
(`cl_ui.cpp:3451`, `:3465`), so the trailing `set` lands before the `map`.

### 2.2 The `ui_startdmmap` trap (bug-1326)

`UI_StartDMMap_f` (`client/cl_ui.cpp:3331-3481`) appends one `Cbuf_AddText` block at `:3451-3480`
that **re-pushes server cvars from archived `ui_*` twins, AFTER any cfg that ran before it**:

| Pushed | Sourced from | Write site |
|---|---|---|
| `dedicated`, `sv_maxclients`, `sv_gamespy` | `ui_dedicated`, `ui_maxclients`, `ui_gamespy` | `:3452-3454` |
| `g_gametype`, `g_gametypestring` | `Cmd_Argv(1)` = literal `2`; `Argv(2)`, default `"Free-For-All"` | `:3455-3456` |
| `fraglimit`, `timelimit`, `g_teamdamage` | `ui_fraglimit`, `ui_timelimit`, `ui_teamdamage` | `:3457-3459` |
| `g_inactivespectate`, `g_inactivekick` | `ui_inactivespectate`, `ui_inactivekick` | `:3460-3461` |
| `sv_hostname` | **`ui_hostname`** | `:3463` |
| `cheats` | hardcoded 0 | `:3464` |

Consequences for HOLDOUT:

- ✅ **`coop_*` cvars are untouched by this list** — which is exactly why `coop_campaign` works as a
  mode flag and `coop_holdout` will too.
- Any `g_<X>` HOLDOUT wants to set must have its `ui_<X>` twin seeded alongside. `start_server.cfg`
  already patches `ui_inactivespectate` / `ui_inactivekick` at `:20-21` for this reason.
- **`ui_dmmap` empty ⇒ total silent no-op.** `cl_ui.cpp:3362-3364` returns before doing anything.
- Live latent defect worth fixing in passing: `start_server.cfg:3`'s `set sv_hostname "Coop TEST"`
  **never survives** — nothing mirrors it into `ui_hostname`.

### 2.3 The map-name constraint ✅ verified by direct read

`main.scr::isCoopEnabledMap` (`:1877-1896`) decides whether the coop mod runs at all. For a
`c`-initial map name it accepts only `containsText(map,"co_lobby")`, or
`map.size > 5 && map[4] == "_" && containsText(map,"coop_")` (`:1893-1894`).

- `co_holdout1` → `map[4]` is `'o'` → **fails both → coop silently does not run.**
- `coop_holdout1` / `coop_hold_m3l2` → `map[4]` is `'_'` and contains `coop_` → **passes, zero edits.**

Existing campaign map names (`m3l2`, `m3l3`, `m2l1`, `e1l1`) pass via the `m`/`e`/`t` branch at
`:1889`, so running HOLDOUT on an existing map name needs no change here either.

### 2.4 File-by-file edit list

| # | File | Action |
|---|---|---|
| 1 | `coop_mod/start_server.cfg` | **EDIT** — add `set coop_holdout 0` at line 36 beside `set coop_campaign 0`. Non-optional: this is what stops a stuck flag leaking into normal play |
| 2 | `coop_mod/cfg/holdout_start.cfg` | **NEW** — clone of `campaign_start.cfg`: maxclients, `ui_dmmap`, `exec coop_mod/start_server.cfg`, then `set coop_holdout 1` + any `coop_hold*` tuning cvars **after** the exec |
| 3 | `ui/coop_holdout.urc` | **NEW** — `menu "coop_holdout" 640 480 NONE 0` … `end.`. Auto-registered by `cl_ui.cpp:5634-5640` (`FS_ListFiles("ui/","urc")`), so no registry edit — but it needs a **client restart** to appear. Apply button: `stuffcommand "wait 250;exec coop_mod/cfg/holdout_start.cfg"` |
| 4 | `ui/coop_start.urc` | **EDIT** — one Button before `end.` at `:421`, copied from the "BEGIN FULL CAMPAIGN" button at `:405-420`, with `stuffcommand "set ui_dmmap nomap;pushmenu coop_holdout"`. Free space around `rect 190 356 260 28` |
| 5 | `coop_mod/main.scr` | **EDIT** — one guarded thread beside the maptest hooks (~`:159`): `if( getcvar( "coop_holdout" ) == "1" ){ thread coop_mod/holdout.scr::hold_main }` |
| 6 | `coop_mod/holdout.scr` | **NEW** — the director |
| 7 | `coop_mod/holdout_positions.scr` | **NEW** — per-map arena table |
| 8 | `coop_mod/challenges.scr` | **EDIT** — a `chal_def` block in `chal_init` + one `coop_chal_catOrder` / `coop_chal_catLabel` entry |
| 9 | `coop_mod/spawnlocations.scr` | **EDIT, only if a new map name is introduced** — an (even empty) label of that name, or every load throws |
| 10 | `coop_mod/server.scr` | **EDIT, optional** — `if( getcvar("coop_holdout") == "" ){ setcvar "coop_holdout" "0" }` at `:33`, matching the `coop_lockLoadout` idiom at `:28` |

⚠️ **Do not `include "ui/coop_maps.inc"` in the new menu.** `globalwidgetcommand` resolves widget
names *globally across every loaded menu*, so both boards' tiles would retarget together. Copy it to
`ui/coop_holdout_maps.inc` with distinct names, or declare tiles inline with the shader and
stuffcommand baked in (simplest, since the HOLDOUT map list is short and static).

### 2.5 Which map does HOLDOUT actually run on? Three options

| | Approach | Cost | Risk |
|---|---|---|---|
| **A** | Run on the **existing campaign map name**, vanilla mission left running | Zero new content; 3 files | Vanilla objectives/cinematics/exit triggers still live. Fine for a prototype, not shippable |
| **B** | Run on the **existing map name**, vanilla mission body **gated off** by an early branch after the map's setup section | One map-script edit per map | The setup section must still run — skipping it is exactly bug-1294 (e2l1 lost every light style and fire effect). Requires care about *where* the branch goes |
| **C** | **Copied BSP** under a `coop_hold_<map>` name with a fresh minimal script, per the co_lobby recipe | ~5-20 MB pak growth per map | Cleanest isolation. BSP entities still spawn from the entity lump, so an entity audit is needed |

**Recommendation: A for Phase 1, B for Phases 2-4, C only if B proves leaky.** The co_lobby precedent
proves C works (`maps/co_lobby1.scr:2-4`), so it is a known-good fallback rather than a gamble.

---

## 3. Core mechanics design

### 3.1 Arena definition and data format

An **arena** is the atomic unit: a defended position, its approach lanes, and its wave schedule.

Follow `officer_positions.scr`'s structure — a single label containing a flat `if/else-if` chain on
`level.coop_mapname`. The reason is documented at `officer_positions.scr:27-29`: **`exec` runs in the
caller's context, so per-map thread dispatch does not work.** Do not invent a different dispatch.

```
holdout_positions.scr::getArenas
	} else if( local.m == "m3l2" ){
		level.coop_hold_count = 3

		level.coop_hold_org[1]     = ( -3198 -2651 123 )   // arena centre (nav-valid)
		level.coop_hold_yaw[1]     = 0
		level.coop_hold_radius[1]  = 900                   // "inside the arena" test
		level.coop_hold_ztol[1]    = 128                   // reject spawn zones off this floor
		level.coop_hold_waves[1]   = 3                     // waves to survive here
		level.coop_hold_mask[1]    = 255                   // coop_wave_mask, per arena
		level.coop_hold_zoneN[1]   = 2
		level.coop_hold_zone[1][1] = ( -4706 -4008 -12 )   // attacker spawn lane A
		level.coop_hold_zone[1][2] = ( -3315 -6718 -273 )  // attacker spawn lane B
		level.coop_hold_spawn[1]   = ( -3600 -3856 78 )    // player checkpoint / respawn
	}
```

Per-arena fields intentionally mirror names the officer system already understands
(`coop_wave_mask`, the z-tolerance idea from `level.coop_officer_reinf_ztol`), so the extracted
spawners need no translation layer.

**Authoring workflow (three tiers, cheapest first):**

1. **Tier 0 — free, today.** `maptest_waypoints.scr` already holds two pre-extracted per-map vector
   tables: `getWaypoints` (`info_pathnode` origins, cap 32/map) and `getTriggerWaypoints`
   (trigger-volume centres, cap 60/map). **`info_pathnode` origins are on the AI navigation graph by
   construction**, which directly de-risks the single worst authoring failure (§5.2). Start every
   arena from a pathnode coordinate.
2. **Tier 1 — `developer.scr` viewpos capture.** `developer.scr:408-409` already prints paste-ready
   `level.flags[coop_spawnNorigin] = ( ... )` from live player positions; `printmarkers` (`:1468-1506`)
   does the same from eight placed markers. This is how every officer anchor in the tree was scouted.
3. **Tier 2 — a HOLDOUT build mode.** Add `"holdout"` to `modeswap`'s cycle
   (`buildmode.scr:248-282`), place `fx/dummy.tik` markers with script-var payload exactly as
   `buildmode_sounds.scr:257-313` does, tune radius on the keys sound mode uses for `coop_build_sndmin`,
   and write `coop_mod/save/hold_<map>.dat`. Load with the fogmode two-path + `float()` recipe
   (`fogmode.scr:273-302`). **This is Phase 4 work, not Phase 1** — Tiers 0/1 unblock everything
   earlier at a fraction of the cost.

### 3.2 Checkpoint progression

```
for each arena A in 1..coop_hold_count:
    playersWarpto( hold_spawn[A], hold_yaw[A], 1 )     // main.scr:590 - warp + re-pin all 8 respawn slots
    announce + HUD "SECTOR A / N"
    readygate.scr::coop_readyGateStart                 // squad presses F when ready
    wait for level.coop_readyGateDone
    for each wave W in 1..hold_waves[A]:
        spawn wave (concurrency-capped, see 3.3)
        wait until arena cleared
        between-wave breather (3.5)
    arena complete: XP + challenge bump, resupply window
end -> mission complete via coop_mod/missioncomplete.scr
```

Two decisions worth stating explicitly:

- **Respawn always re-pins to the current arena.** `playersWarpto ... 1` overwrites all eight slots
  (`main.scr:599-607`), so a player who dies mid-wave returns to the arena they are defending, not to
  the map start. This is the entire reason the mode does not need custom respawn code.
- **Advance is squad-gated, not trigger-gated.** `readygate.scr` means no player is teleported away
  mid-loot, and it works for remote clients with no binds (`readygate.scr:1-11`).

### 3.3 Wave composition, pacing and scaling

Copy the retail arithmetic from `m3l2.scr:646-654` verbatim, because it is the discipline that keeps
the entity pool safe:

| Knob | Meaning | Suggested default (2-player baseline) |
|---|---|---|
| `holdAliveMax` | **concurrency cap** — live wave actors from this arena | `6 + 2*(pc-2)`, hard ceiling 16 |
| `holdTotal` | total actors this wave will ever field | `8 + 4*(waveIndex-1)` |
| `holdInterval` | seconds between spawn batches | `2.0`, easing to `1.2` at higher waves |
| `holdMask` | `coop_wave_mask` for this arena | 255 outdoors, exclude types 4/5 indoors |

**Player-count scaling reuses the officer arithmetic unchanged** (`officer.scr:1512-1531`):

```
n = base + (clamp($player.size, 1..4) - coop_officerBasePc) * per
```

with `coop_officerBasePc` defaulting to 2, floored at 1, capped, and clamped back to `base` when live
Germans reach 80. Because `(pc - bp)` can be negative, **solo play scales *down*** — authored numbers
are a two-player baseline, which is the documented convention (FEATURES.md, officer wave scaling).
Per-actor health/accuracy scaling comes free from `coop_reinf_scale` (`officer.scr:1548-1582`,
health +35%/extra player capped 690, accuracy +15% of remaining range).

**Escalation across waves** should move three dials, in this order of felt impact:
1. `holdAliveMax` (pressure) — the one players actually feel
2. wave type mask (variety) — introduce dogs/grenadiers/AT at wave 3+, sniper as a wave-4 spice
3. `holdTotal` (length) — last, because long waves read as tedium rather than difficulty

**Attacker behaviour:** use `coop_spawn_death_battalion`'s `hold` flag inverted — HOLDOUT attackers
are `hold != 1` (march at the players, `officer.scr:3378-3389`, `coop_death_battalion_march`), while
an optional "flank squad" can use `hold == 1` to dig in on a side lane and force players off one
firing angle.

**Do not enable AI prone/crouch.** `anim/attack.scr:48-62` forces both to 0 because
`AttackLongRangeCrouch` → `AttackCrouchDodge` spins into *"Command overflow. Possible infinite loop"*
= server crash (`fgame/actor.cpp:8274-8350`). Cosmetic `anim_scripted` prone via
`coop_prone_shooter` (`officer.scr:1675`) is the safe version and is already used by officer waves.

### 3.4 Fail and success conditions; DBNO interaction

**DBNO already exists and needs no changes.** `coop_dbno` is forced to 1 in `autoexec.cfg:24`;
threshold 250 cumulative damage (`dbno.scr:101-102`, reset after 2 damage-free seconds at `:96-99`);
90 s bleedout (`:176-177`, 45 s on a headshot down). Four revive routes: team revive
(`dbno.scr:586-654`), self-revive with a medkit (`medkit.scr:235+`), AI medic (`dbno.scr:661-799`),
corpse revive within `coop_dbnoCorpseRevive` seconds at the spot they fell (`dbno.scr:332-364`).

**⭐ The "everyone is down" predicate already exists** ✅ **verified.** `director.scr:83-98` counts
`local.upN` over players that are `isAlive` and not `flags["coop_dbno_active"]`, and
`director.scr:116` latches an S5 near-wipe branch on `upN == 0`. Today it *eases the game*
(snaps AI skill to floor, forces a 40 s relax valley). **HOLDOUT wants the same predicate to end the
round.** Reuse the counting loop; do not re-derive it.

The only existing wipe/fail path in the mod is LMS: `main.scr::lmsForceSpectatorHandle:1542-1556`
counts non-spectator players and calls `replace.scr::missionfailed` at zero. ⚠️ That loop has a
variable-shadowing defect (the inner `local.player = $player[local.i]` clobbers the parameter) —
**do not copy it verbatim.**

**Proposed conditions:**

| Outcome | Condition | Cvar |
|---|---|---|
| **Wave cleared** | live wave actors == 0 **and** total spawned == `holdTotal` | — |
| **Arena cleared** | all `hold_waves[A]` cleared | — |
| **Run complete** | last arena cleared → `coop_mod/missioncomplete.scr` (which already runs `xp_summary` and the debrief) | — |
| **Wipe** | `upN == 0` sustained for `coop_holdWipeGrace` seconds (default 5, so a simultaneous double-down that gets revived does not end the run) | `coop_holdWipeGrace` |
| **On wipe** | default: restart the **current arena** from wave 1 (`coop_holdRetry 1`); alternative: whole run (`coop_holdRetry 0`) | `coop_holdRetry` |
| **Hard restart** | `main.scr::restartMap:1773-1821` — `stuffsrv "map <clean name>"`. **Never** `bsptransition`/`loadMap` on a live coop server | — |

A wipe **must not** silently rely on LMS. Leave `coop_lmsLives` at its default 0 (off,
`variables.scr:63`); HOLDOUT owns its own fail condition.

### 3.5 Between-wave economy

Everything needed already ships:

- **Ammo box** (`ammobox.scr`) — one per player *per match* (`:16-67`, keyed on entnum), 96-unit
  proximity, `[USE]` to resupply, `coop_ammobox_refills` uses per player per box (default 2,
  `:180-181`), owner earns +10 support XP per teammate resupply capped at 7/map (`:209-224`).
  **For HOLDOUT, change one thing: reset `level.coop_ammobox_dropped[entnum]` per arena**, so the
  once-per-match box becomes once-per-checkpoint. That single line converts an existing feature into
  the mode's economy.
- **Medkits** — `flags["coop_medkits"]` resets to 1 and `coop_cover_placements` to 2 on every spawn
  (`dbno.scr:36-37`), cap 2. A between-wave top-up to 2 is one assignment.
- **Cover** — `cover.scr::cover_place` sandbags (2 per life) is already bound; `blueprint.scr::bp_place`
  can stamp a pre-authored fortification set at each arena once bug-1001 is resolved.
- **Optional reward: allied paradrop.** `paradrop.scr::smokeDropZone` (`:10`) already drops five
  fighting paratroopers and a medic. Arming it as a "survive wave 5" reward is a one-line
  `level.coop_paradrop_armed = 1`. ⚠️ Register any allied actor into
  `level.coop_actorArray["german"]`-driven layers correctly — bug-1260's fix was to thread
  `coop_apply_personality` on each paradropper because the `["american"]` array is read by nothing.

**Recommended breather:** 20 s default (`coop_holdBreather`), during which the ammo box resets, HUD
shows the next wave preview, and a shortened ready gate can skip the remainder.

### 3.6 Scoring, XP and a Holdout challenge set

```
xp_team_award  25  "objective" "Wave <n> Cleared"
xp_team_award  75  "objective" "Sector <A> Held"
xp_award  <p>  40  "valor"     "Last Man Standing"      // sole survivor when a wave clears
```

Reuse the existing `reason` buckets — a new string works mechanically (it just creates a new
`coop_xp_b_*` bucket) but `xp_card_categories` will not render it.

A starter challenge block for `chal_init`, using the verified `chal_def` signature. New category
`"holdout"` needs one entry in `coop_chal_catOrder` (`challenges.scr:393-404`) and
`coop_chal_catLabel` (`:405-415`):

| id | stat | target | title / condition |
|---|---|---|---|
| `hold_waves_1/2/3` | `hold_waves` | 25 / 100 / 500 | tiered "waves survived" counter |
| `hold_sector_flawless` | `hold_flawless` | 1 | clear a sector with nobody downed — `cc_award_clean "hold_flawless"` does the DBNO exclusion for you (`challenges.scr:879`, reading `coop_wentDownMap` from `dbno.scr:190`) |
| `hold_solo` | `hold_solo` | 1 | complete a full run solo |
| `hold_noresupply` | `hold_noresupply` | 1 | clear a sector without touching an ammo box |
| `hold_m3l2` … | `hold_<map>` | 1 | per-map completion, mirroring the existing `map_<mapname>` convention (`challenges.scr:1377-1447`) |

⚠️ **Challenge descriptions must be pure ASCII.** The vetting pass on the last challenge batch found
four em-dashes that would have parse-killed `challenges.scr` outright
([TRAPS.md § T1](../TRAPS.md#t1)).

### 3.7 HUD

⚠️ **The reserved block in `_research/hud_slot_map.md` is stale.** It nominates 88-99 as "reserved for
the next feature", but ✅ **verified**: `fogmode.scr` now occupies **88-94** and `buildmode.scr`
occupies 54-59 + 61.

**Claim 135-149 for HOLDOUT** (15 slots, currently free, and **fade-exempt because ≥100** — which the
mode needs, since a wave counter must survive the 5-second HUD idle fade). Suggested layout: 135
sector title, 136 wave counter, 137 enemies-remaining, 138 breather countdown, 139 objective line,
140-144 spare. Update `_research/hud_slot_map.md` when claimed — that file's own rule #4 requires it.

---

## 4. Map selection

Metrics below combine `map_entities/*_entities.txt` (raw entity dumps), `officer_positions.scr`,
`spawnlocations.scr`, and `maptest_waypoints.scr`. **Read the waypoint counts carefully:** both
tables are capped (60/map triggers, 32/map pathnodes), so "60+32" means "hit both caps", and raw
`info_pathnode` count is the honest nav-coverage proxy. Coop-integration is *not* a discriminator —
`docs/generated/SUBSYSTEMS.md:179-240` lists essentially every campaign map as integrated.

### Top 3 recommendations

**1. `m3l2` — "Village Warzone" / Battle in the Bocage (AA) — prototype here.**
The retail wave-defence architecture is already in this file: 84 occurrences of the spawner/detector
machinery, three sequential arenas (`scene3` back of house → `scene4` front of house → `scene5`),
already coop-scaled at `m3l2.scr:650-653`. `officer_positions.scr:284-310` carries seven
human-scouted, viewpos-verified coordinates including **four `hold = 1` death-battalion positions** —
i.e. four defended-arena spawn points already placed by a person. 1733 pathnodes, 42 ground-level AI
positions (*"Excellent coverage"*, `map_entities/SUMMARY.md:191`), 58+32 waypoints, 3665-line script.
Normandy village: enclosed house interiors, a walled yard, street approaches — textbook arena shape.
Two open defects, both harmless here: bug-1218 (`$level_end_trigger` label missing at `m3l2.scr:2854`
— irrelevant once HOLDOUT owns level end) and bug-1219 (an `SV_FindIndex` overflow that
[OPEN.md:143](../OPEN.md) says *"will resolve when the current exe is deployed. Do not fix it in
source."*). Weakness: only 2 player spawn zones, so the checkpoint chain is authored by hand.

**2. `m4l3` — Sicilian Village (AA) — best raw infrastructure.**
The only AA map combining **6 `$alarmspawner` + 10 `$enemyspawner`** with **2612 pathnodes** (3rd
highest of 54 maps). `map_entities/SUMMARY.md:11` classifies alarmspawners as *"guaranteed nav-valid"*
— authored spawn nodes the retail designer already proved AI can path from, which is exactly the
property §5.2 says HOLDOUT most needs. TIER 1 / HIGH-confidence officer anchor (the only tier with no
`verify_ingame` flag), the **only** map with a real shipping coordinate in `objective_positions.scr:33-37`,
4 spawnlocations zones, and it is roster index 1 in the maptest harness (`maptest.scr:173`) so it is
the most-exercised map in the tree. Walled farm compound: truck yard, shacks, command post,
courtyards, gated lanes. Opens on a short truck ride, but coop already handles that
(`faketruck_playerexit`) and spawn zone 1 sits at the offload point.

**3. `m2l1` — Highway 1 (AA) — the pre-authored arena chain.**
`officer_positions.scr:188-207` is the richest entry in the whole file: **four viewpos-verified
`death_battalion` positions with `hold = 1`**, documented in that file as *"they dig in and guard
their own area, engaging on sight (no rush)"*. Four spatially distinct defended points, already
scouted, plus `waves_at_zone = 1`. Six spawnlocations zones = a ready-made six-checkpoint route.
1133 pathnodes, 17 `$enemyspawner`, 54-65 authored AI. [TRAPS.md:619](../TRAPS.md) notes it is
*"a concentrated map"* (~41 simultaneous enemies) — good wave density. Final arena drops ~500 units in
Z, which exercises the per-arena `ztol` field early.

### Also strong

- **`m3l3`** (Comrade in Arms) — **2728 pathnodes, the highest of any non-crashy map**, 6 spawn zones,
  viewpos-verified officer anchor, and **166 occurrences of the wave machinery across ten spawner
  systems** (`M3L3.scr:1531,1705,1832,1969,2123,2924,3046,3165,3287,3454`) ✅ verified. Bocage → town
  square → walled churchyard → nebelwerfer field is four natural arenas. Held back only by the
  unresolved cosmetic ground seam ([OPEN.md:221](../OPEN.md)).
- **`e1l1`** (BT Tunisia) — **36 `$enemyspawner`** and **12 spawnlocations zones, the longest
  checkpoint chain in the mod**. Desert bunker complex with gated approaches and minefield-channelled
  lanes. ⚠️ Two cautions: `maps/e1l1.scr` carries a `monitorEntityCount` label and `global/*.scr` has
  *"enable print for debugging overflow issue on e1l1"* hotfix guards — a wave spawner on a map
  already instrumented for entity overflow is a poor first test. Also its `spawnlocations.scr` base
  origin looks copy-pasted from m6l3d and needs a viewpos check.
- **`m6l2b`** (Crossroads) — the clean-room fallback. **1814 pathnodes and 52 ground AI positions**
  (best ground-AI ratio in the game) against a **339-line** script and only 27 trigger volumes, i.e.
  enormous nav coverage with almost no vanilla scripting to fight. If m3l2 keeps tripping over retail
  set-pieces, go here.

### Avoid

| Map | Why |
|---|---|
| **`e3l4`** | **Fatal for this gametype specifically.** `maptest_waypoints.scr:4121-4127`: teleporting onto e3l4 terrain triggers an engine terrain-collision-trace stack overrun (`0xc0000409`, `cm_terrain.c`), so its tour is disabled outright. A checkpoint-teleport mode hits that exact path. Plus bug-1027 (`outro.scr` fails to load, 251× cascade) |
| **`t1l1`-`t3l2`** (all 9 SH maps) | Launch-profile split: their BSPs live in `mainta/pak1.pk3` and mount under `com_target_game=1` (`maptest.scr:222-228`), so they cannot be iterated alongside the m/e rotation. All t-series officer anchors are untested `verify_ingame` estimates. **`t2l1` is the best map in the trilogy on paper** (52 `$enemyspawner`, 2450 pathnodes, labels literally named `kitchen_fight` / `office_fight` / `window_ambush_1/2`) — revisit it for Phase 5, not the prototype |
| **`t2l2`, `t3l2`, `m5l2b`, `m4l0`, `m1l3b`** | Vehicle-ride or cinematic-driven. `coop_feature_boss = 0` on several; t2l2 additionally throws 265 script errors on coop boot (bug-1026) and has an unguarded second vehicle-crew spawn path ([OPEN.md:172](../OPEN.md)) |
| **`m3l1a`** | The trap of the set: 8424-line script (largest in AA) and 182 triggers, but **80 pathnodes — the worst nav coverage of all 54 maps.** Scripting volume is not playable space |
| **`m1l1`** | The existing wave system already had to be **de-scoped** here — `coop_wave_mask` cut to 57 and `coop_feature_battalion = 0` because the map is *"too big for this map"*. Strapped-in truck intro with no respawn |
| **`m2l2a/b/c`, `m6l3c/d/e`, `m3l1b`, `m6l1a/b`, `m5l1a`, `e2l3`** | Corridors, ship/cave interiors, or too little AI and space (101-636 pathnodes). e2l3 has **5 `ai_` entities and no authored German enemies at all** |

---

## 5. Risks and unknowns

### 5.1 ⚠️ Entity-pool exhaustion — the biggest risk by a wide margin

`GENTITYNUM_BITS 11` → `MAX_GENTITIES 2048` (`qcommon/q_shared.h:1667-1668`), with 2046/2047 reserved
as `ENTITYNUM_WORLD`/`ENTITYNUM_NONE`. `Level::AllocEdict` (`fgame/level.cpp:1700-1747`) now clamps at
`i >= ENTITYNUM_WORLD` and `gi.Error(ERR_DROP, "Level::AllocEdict: no free edicts")` on true
exhaustion — a clean drop rather than the world-slot stomp that produced the entire bugs-914-927
crash family. The in-code comment at `level.cpp:1727-1732` is the best account of it.

**Indefinite wave spawning is exactly the pressure profile that broke it before.** Bug-926's own root
cause reads: *"count-scaled battalions + corpses kept forever + EVERY dead AI leaving 2-3
dropped-weapon entities forever."*

**Four gaps HOLDOUT must close, each with a concrete fix:**

1. **No `spawn` NULL guard anywhere in the officer wave path.** ✅ verified at
   `officer.scr:3343-3345` — `local.b = spawn local.bmodel` then `local.b.origin = ...` immediately.
   The same shape recurs at `:512`, `:1812`, `:1906`, `:2022`, `:2183`, `:2332`, `:2787`, `:2986`,
   `:3005`, `:3041`. The bomb-FX code *was* hardened (guards at `:3868, 3890, 3921, 3934, 3953`, with
   the budget documented at `:3863-3867`) and `aihandler.scr:250` guards replicas — so the pattern
   exists, it just was never applied to actors. **Every HOLDOUT spawn gets `if( local.x == NULL ){ break }`.**
2. **The 80-actor cap is soft on the officer path.** `officer.scr:1528-1530` only clamps *extras* back
   to base; a base wave still spawns at 81 live Germans. HOLDOUT must check
   `level.coop_actorArray["german"].size` **before every batch and refuse**, matching
   `aihandler.scr:228`'s hard `break`.
3. **`level.coop_wave_actors[]` grows without bound.** `officer.scr:1317-1319` and `:3068-3070`
   increment `level.coop_wave_count` forever with no compaction on death. Over a long HOLDOUT run that
   leaks array slots and makes any iteration O(total spawns ever). **Keep a compacted per-arena roster
   and clear it at each arena boundary.**
4. **Corpses persist by default.** `coop_corpseLife` defaults to 0 = off (`aihandler.scr:126`, and
   OFF is a deliberate user preference). `MAX_BODYQUEUE` is **128** (`fgame/actor.h:306`, raised from
   5 for coop) — and note its own comment still says *"MAX_GENTITIES 1024"*, which is wrong, it is
   2048. Dropped weapons are already relieved: engine default 30 (`fgame/gamecvars.cpp:455`), raised
   to 60 by `autoexec.cfg:363` as bug-926's pressure relief.
   **HOLDOUT should set a non-zero `coop_corpseLife` for its own
   duration only, and restore it afterwards** — do not change the global default.

**Also do not copy** `coop_officer_medkit_retreat` (`officer.scr:918-974`), which walks the entire
entity pool with `getentbyentnum` — a 2048-iteration synchronous scan.

### 5.2 ⚠️ AI pathing: arena anchors in dead nav space

Bug-1319 is the canonical failure: the e2l1 officer anchor *"had no reachable path node, so the
officer + guards could never path after arriving"*, producing endless
`^~^~^ Path not found in Actor::MoveToPatrolCurrentNode` spam. It was fixed only by the user
re-scouting coordinates with `viewpos`.

**The log line is machine-parseable** (`fgame/simpleactor.cpp:212`, `:281`), so this is testable
rather than hoped-for. Mitigations, in order:

1. **Author arena centres and spawn zones from `info_pathnode` origins** (`maptest_waypoints.scr::getWaypoints`)
   — nav-valid by construction.
2. Prefer maps with `$alarmspawner` entities, which `map_entities/SUMMARY.md:11` calls *"guaranteed
   nav-valid"* — m4l3 is the only AA map with six of them.
3. `coop_find_ground` (`officer.scr:1217-1221`) + `droptofloor` on every spawn, and the Z-tolerance
   rejection from `officer.scr:1399-1420`.
4. A validation pass modelled on `tracescan.scr` (a cvar-gated dev grid scanner): spawn a probe actor
   at each authored zone, issue a `runto` toward the arena centre, and grep for `Path not found`.

### 5.3 ⚠️ Enemy health is buffered — never read engine health to detect a clear

`aihandler.scr::initialisePainVars` (`:720-819`) moves each German's real HP into
`flags["coop_actorActualHealth"]` and sets engine `self health` to `coop_aiBuffer` (default **1000**).
The only code converting "real HP reached 0" into a death is `handlePain`, reached solely through
`global/pain.scr` (bug-1212, and bug-1275 found `coop_painThread` was a latch nothing cleared, making
every enemy a permanent sponge until fixed).

⚠️ There is a live inconsistency: `actorPainHandler:870` still hardcodes
`if(self.health != (5000 - self.fact.damage))` while the buffer default is 1000, so that comparison
never matches and every buffered actor takes the "health changed elsewhere" branch on first hit. Worth
a separate look; **for HOLDOUT the lesson is simply: detect wave clear by `waittill death` +
counter decrement (the retail `_detect_death` pattern) or by `level.coop_actorArray["german"]`
membership. Never by engine health.**

### 5.4 Precache, sounds and anims

`officer.scr:135-147` caches 11 models at init specifically because *"e/t-series maps don't call
coop_mod/precache.scr"*. HOLDOUT must do the same for every model any wave type can field, or the
first spawn of each is a synchronous disk hit mid-combat (the bug-1141 lag-spike shape that
`sndcache.scr` exists to fix).

`MAX_SOUNDS` is a four-constraint family documented at `qcommon/q_shared.h:1690-1755` — read it in
full before adding sound content. ⚠️ **Live deploy gap:** the header says 1600 but bug-1219 reports
`SV_FindIndex overflow (max=1280)` from a live m3l2 log, because the deployed `openmohaa.exe`
(2026-07-21) predates the header edit ([TRAPS.md § T10](../TRAPS.md#t10)). HOLDOUT adds sound
registrations on the map with the *existing* overflow — deploy the current exe before measuring.

### 5.5 The "spawns during setup then dies unheard" class

Two distinct shapes, both live:

- **`waittill` that already fired does not abort — it simply does not wait** (bug-1294). A HOLDOUT
  director threaded from `main.scr` runs *before* `level waittill prespawn`, so any arena setup that
  touches map entities must go through `replace.scr::waitTillSpawn` / `::waitTillPrespawn`, never a
  bare `level waittill`. The log line `invalid waittill spawn for 'Level'` looks like a warning and is
  the oracle.
- **Same-frame spawn → model → solid race** ([TRAPS.md § T9](../TRAPS.md#t9)): `setmodel` is deferred,
  so `getmins`/`getmaxs` read zero in the spawn frame. Any solid cover placed by HOLDOUT must use the
  three-phase framedefer pattern from `coop_placements.scr` (spawn → frame boundary → measure and
  solidify), and `getmins` must use **property** syntax or the whole file fails to compile (bug-910).

### 5.6 Dedicated server

- Build mode is **host-only** (`buildmode.scr:85-97` requires entnum 0 with `coop_isHost`; a client
  `set` cannot reach the server cvar table). Arena *authoring* is therefore listen-server only; arena
  *playback* has no such constraint.
- The lobby input and cursor bridges are engine-side per-player (`player.cpp:13479`, `:13517`), so
  ready gates and clickable UI work for remote clients on a dedicated server.
- ⚠️ bug-330: `game.dll` segfaults loading bare DM maps under a dedicated server, *"likely a coop hook
  assuming coop init ran"*. Coop maps load fine. The working recipe is the **client exe with
  `+set dedicated 1`**, not `omohaaded.exe`.
- `level.coop_dedicated` is computed once at `variables.scr:51-53`.

### 5.7 Persistence

XP and challenges persist per player via cvar + homepath file and survive both map transitions and
restarts (`xp.scr:281-341`, `challenges.scr:491-584`). **Run state does not and should not** — a
`stuffsrv "map <name>"` reload re-runs `main.scr::main` from scratch, so a wipe restarts the run.
⚠️ Never park run state in `game.*`: `xp.scr:3-8` warns explicitly that the coop transition wipes it,
and `g_scriptcheck` + non-empty coop `game.*` vars produces a `Com_Error` that *looks exactly like a
crash* ([TRAPS.md § T15](../TRAPS.md#t15)).

### 5.8 Parse killers in the new data table

`holdout_positions.scr` will be a large hand-written table of vector literals — the highest-risk file
shape in the project. [TRAPS.md § T1](../TRAPS.md#t1) lists 15+ bug ids. Specifically:
no em-dash, no BOM, no non-ASCII; **a space after every `(` in a vector literal** so a leading
negative can never form the paren-minus killer (the build-mode capture writer already does this
deliberately); no string literal spanning lines; no nested `waitthread` as an argument to another
`waitthread` (`buildmode.scr:271-275`); quote any argument beginning with `+`/`-`.
✅ **The three scanners DO exist and should be run on every edit** — verified present at
`docs/tools/depthscan2.py`, `docs/tools/linecheck.py`, `docs/tools/quotecheck.py`. (TRAPS.md § T1
note 3 and [OPEN.md § Tooling lost](../OPEN.md#tooling-lost) both say the depth scanner is gone;
that refers to the vanished `scratchpad/` copy. **The `docs/tools/` set is live — those two records
are stale and should be corrected.**) They catch disjoint classes, so run all three. And
`developer 1` is mandatory regardless: compile errors are developer-gated at three call sites
(`fgame/scriptthread.cpp:2858/2869/2883`), so without it a parse kill is completely silent.

---

## 6. Phased implementation plan

### Phase 1 — prove the wave loop (smallest thing that works)

**Goal:** on m3l2, with `coop_holdout 1`, one authored arena runs N waves that spawn, scale by player
count, get cleared, and report. No menu, no lobby, no checkpoints, no map-script edits. The vanilla
mission is left running and ignored.

| File | Action |
|---|---|
| `coop_mod/holdout.scr` | **NEW** ~250 lines: `hold_main` (wait for main script + a player), `hold_run_arena`, `hold_spawn_batch` (modelled on `coop_spawn_death_battalion`, with a NULL guard and a hard 80 check), `hold_wave_cleared`, `^~^~^ HOLDOUT_*` log banners |
| `coop_mod/holdout_positions.scr` | **NEW** ~60 lines: `getArenas`, m3l2 only, one arena, coordinates lifted from `officer_positions.scr:284-310` (already viewpos-verified) |
| `coop_mod/main.scr` | **EDIT** one line beside the maptest hooks |

Start it from the console: `set coop_holdout 1; set ui_dmmap m3l2; exec coop_mod/start_server.cfg`.

**Complexity: low.** Every hard part is a call into existing code. The real work is the concurrency
bookkeeping, and m3l2's own `scene3` is the reference implementation.

**Done when:** `^~^~^ HOLDOUT_WAVE_CLEARED` fires three times in a row with live-German count never
exceeding the cap, and no `Path not found` or `no free edicts` in the log.

### Phase 2 — checkpoints and the arena chain

**Goal:** three arenas on m3l2, `playersWarpto` between them, `readygate` gating each advance, wave
HUD on slots 135-149, run-complete → `missioncomplete`, wipe → arena retry.

| File | Action |
|---|---|
| `coop_mod/holdout.scr` | **EXTEND** — arena loop, `playersWarpto ... 1`, `readygate.scr::coop_readyGateStart`, HUD, the `upN == 0` wipe predicate lifted from `director.scr:83-98`, breather + ammo-box reset |
| `coop_mod/holdout_positions.scr` | **EXTEND** — 3 arenas, coordinates from `officer_positions.scr` hold-battalion points + `maptest_waypoints.scr` pathnodes |
| `maps/m3l2.scr` | **EDIT** — a `coop_holdout` early-branch that suppresses the vanilla mission threads while keeping the setup block (option B, §2.5) |

**Complexity: medium.** The map-script gate is the delicate part — bug-1294 is the cautionary tale for
cutting too much. Budget a full pass reading m3l2's `main` to find the exact boundary between setup
and mission.

### Phase 3 — menu, mode start and lobby

**Goal:** hostable from the Start Game menu with map, wave count and difficulty options.

| File | Action |
|---|---|
| `coop_mod/start_server.cfg` | **EDIT** — `set coop_holdout 0` at line 36 |
| `coop_mod/cfg/holdout_start.cfg` | **NEW** — clone of `campaign_start.cfg` |
| `ui/coop_holdout.urc` | **NEW** — tiles (own `.inc`, distinct widget names), `linkcvar` fields for `coop_holdWaves` / `coop_holdDifficulty`, Apply, Back |
| `ui/coop_start.urc` | **EDIT** — one button before `end.` at `:421` |
| `coop_mod/server.scr` | **EDIT** — default the flag at `:33` |
| (optional) a `coop_holdout1` lobby map + `spawnlocations.scr` label | **NEW** — only if a pre-run staging lobby is wanted; `lobby.scr::lobbyMapMain` supplies everything else |

**Complexity: low-medium.** Entirely template work. The traps are known and enumerated in §2.2-2.4.
Remember the client restart for a new `.urc`.

### Phase 4 — authoring tooling and generalisation

**Goal:** author arenas in-game instead of by hand; unlock all eight wave types.

- Add `"holdout"` to `buildmode.scr::modeswap`'s cycle; place `fx/dummy.tik` markers per
  `buildmode_sounds.scr:257-313`; write `coop_mod/save/hold_<map>.dat`; load via the fogmode two-path
  + `float()` recipe.
- **Extract the officer-liveness gate**: replace ~10 `while( ... level.coop_officer_alive == 1 )`
  conditions with a generic `level.coop_waveSystemActive` (`officer.scr:1952, 2211, 2841, 2888, 3004,
  3039, 1861, 1874`), and parameterise `coop_nearest_player_pos` (`:2653-2655`) and
  `coop_far_enemy_anchor` (`:2239`). This unlocks wave types 2/3/6/7.
- Add a `coop_selftest_holdout.scr` following the `coop_st_officer` mode-dispatcher pattern
  (`coop_selftest_officer.scr:31-45`) so the regression harness at `_research/regression/` can exercise
  it unattended — the project's only working automated verification
  ([TRAPS.md § T14](../TRAPS.md#t14)).

**Complexity: medium.** The extraction is mechanical but touches the largest coop script (4374 lines),
so read `docs/generated/FIX_INDEX.md` for officer.scr's ordered bug history first.

### Phase 5 — more maps, isolation, polish

- m4l3 and m2l1 arena tables (both already have human-scouted coordinates).
- Holdout challenge block + category in `challenges.scr`.
- If the option-B vanilla suppression proves leaky: copied BSPs under `coop_hold_<map>` names, per the
  co_lobby recipe. **Verify the name passes `isCoopEnabledMap` (`map[4] == "_"`) and add the
  `spawnlocations.scr` label.**
- Revisit `t2l1` once the SH launch-profile split is handled.

---

## 7. Open questions for the user

1. **Fail semantics** — on a squad wipe, retry the current sector (proposed default) or restart the
   whole run?
2. **Vanilla mission** — should HOLDOUT suppress the map's objectives and cinematics entirely
   (recommended), or leave them running as optional side content?
3. **Run length** — how many sectors per map, and how many waves per sector? The proposal assumes 3
   sectors × 3-5 waves ≈ 25-40 minutes.
4. **Between-run persistence** — should sector progress carry across a server restart, or is a run
   always a single session?
5. **Prototype map** — m3l2 is recommended for the retail wave architecture; m4l3 has better raw nav
   and spawner infrastructure. Which map do you want to prove it on?

---

## Appendix — anchor index

| Subsystem | Primary anchors |
|---|---|
| Officer waves | `coop_mod/officer.scr:1377-1486` (dispatch), `:1494-1582` (scaling), `:1589-1620` (spread), `:3327-3392` (death battalion ⭐), `:1217-1221` (ground snap) |
| Retail wave-defence ⭐ | `maps/m3l2.scr:644-659, 663-782, 786-791, 968-980`; `maps/M3L3.scr:1531+` (ten spawner systems) |
| AI scaling / registry | `coop_mod/aihandler.scr:169-236, 228, 278-462, 687-716`; `coop_mod/variables.scr:97-101` |
| Checkpoints | `coop_mod/main.scr:590-629` (`playersWarpto`), `:632-709`; `coop_mod/spawnlocations.scr:13-21` |
| Lobby / ready | `coop_mod/lobby.scr:12-162, 643-700`; `coop_mod/readygate.scr:15-124`; `coop_mod/lobbyui.scr:69-80, 111-114`; `fgame/player.cpp:13479-13564` |
| Scoring | `coop_mod/xp.scr:380, 745, 950-1063`; `coop_mod/challenges.scr:451-471, 712, 859, 879` |
| DBNO / wipe | `coop_mod/dbno.scr:81-253, 586-654`; `coop_mod/director.scr:83-98, 116`; `coop_mod/main.scr:1542-1556` |
| Menu / start | `ui/coop_start.urc:348-362, 405-420`; `coop_mod/start_server.cfg`; `coop_mod/cfg/campaign_start.cfg`; `client/cl_ui.cpp:3331-3481, 5634-5640`; `coop_mod/main.scr:1877-1896` |
| Authoring | `coop_mod/buildmode.scr:22-25, 140, 248-282, 491-527, 727-737`; `coop_mod/buildmode_sounds.scr:6-9, 257-313`; `coop_mod/blueprint.scr:25-30, 366-457`; `coop_mod/fogmode.scr:256-302`; `coop_mod/maptest_waypoints.scr` |
| Entity budget | `qcommon/q_shared.h:1667-1668`; `fgame/level.cpp:1700-1747`; `fgame/gamecvars.cpp:323, 455`; `fgame/actor.h:306` |
| Nav failure | `fgame/simpleactor.cpp:212, 281`; bug-1319 |
