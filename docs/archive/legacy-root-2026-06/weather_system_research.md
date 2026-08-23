# Dynamic Random Weather System — Research Report (OpenMOHAA-HZM + HZM Coop Mod)

Research only. No code was modified. All file:line citations are against the trees under
`C:\mohaa-coop-dev\openmohaa-hzm\code` (engine) and `C:\mohaa-coop-dev\hzm-mohaa-coop-mod`
(mod scripts). Mod runs under `fs_game=maintt`; on AA m-series maps only `main` + `maintt`
paks load.

---

## TL;DR feasibility

- **Fog: fully feasible, pure script, coop-consistent.** `$world farplane` / `farplane_color`
  / `farplane_bias` write a replicated configstring (`CS_FOGINFO`) — every client sees the
  same fog with no cgame change. Gradual animation = step the value in a `for`/`wait` loop
  (the campaign already does this). `$world.farplane` read-back works.
- **Rain: feasible and coop-consistent, BUT needs a `func_rain` brush volume that already
  exists in the BSP.** Rain intensity is driven by `level.rain_density` / `level.rain_slant`
  / `level.rain_shader` etc., which are **server-side configstrings (`CS_RAIN_*`) that
  replicate to all clients** — no cgame change for density control. The catch: the actual
  rain *volume* is an `ET_RAIN` entity created only from a map's `func_rain` brush
  (`nature.cpp:71`). Script cannot spawn an `ET_RAIN` volume. So rain only renders on maps
  that ship a `func_rain` brush. On maps without one you get rain *sound* but no visible
  rain unless cgame is modified.
- **Lightning flash: partial.** The campaign technique (`global/weather.scr`) flashes via
  `setcvar "r_fastsky" "1"` + brightening `$world farplane_color`. The `farplane_color`
  half replicates; the `r_fastsky` half is a **client cvar set server-side via
  `gi.cvar_set` — it does NOT reach remote clients** (`scriptthread.cpp:3074`). So in coop
  only the host sees the fastsky flash. A coop-correct sky flash needs either a fog-color
  pulse (replicated) or a cgame change.
- **Thunder sound: feasible but alias-gated.** `thunder1/2/3` aliases exist in the maintt
  ubersound but are restricted to `maps "m5l1"` (`ubersound/ubersound.scr:1105`). To use
  on arbitrary m-series maps you must add map-agnostic aliases (mod ubersound edit, not a
  dll change).
- **Snow: not natively supported.** No snow particle system in the engine. Only option is
  an emitter `.tik` (e.g. `models/emitters/snowdrift.tik`, Spearhead/UBER asset) attached
  per-player — same coop attach problem as the e1l1 storm cube. Recommend deferring snow.

**Recommended approach:** Build a pure-script `level`-thread state machine that drives
**fog (farplane/farplane_color)** + **`level.rain_density` configstring** + **replicated
thunder via fog-color pulse and a per-player `playsound`**. This is 100% coop-consistent
and needs zero dll changes. Treat visible rain streaks as "best-effort" (present only where
the BSP has a `func_rain`); the fog + darkening + thunder sell the storm everywhere.

---

## 1. FOG — `$world` farplane family

### Engine (server-side, replicated)
Defined in `fgame/worldspawn.cpp`:

| Command | Type | Line | Notes |
|---|---|---|---|
| `$world farplane <dist>` | SETTER | `worldspawn.cpp:172` (setter), `:199` (normal) | Distance of far clip plane. **Doubles as fog distance** — large value = fog pushed far away / effectively no fog; small value = thick near fog. |
| `$world.farplane` | GETTER | `worldspawn.cpp:163` | Read current distance. **Confirmed works** — `weather.scr:13` does `level.farplane = $world.farplane`. Implemented as `ev->AddFloat(farplane_distance)` (`worldspawn.cpp:716`). |
| `$world farplane_color (r g b)` | SETTER/normal | `:126`, `:135` | Fog color, 0–1 floats. |
| `$world.farplane_color` | GETTER | `:117` | Read-back; `weather.scr:14` uses it. |
| `$world farplane_bias <f>` | SETTER/normal | `:226`, `:235` | Fog falloff bias. |
| `$world farplane_cull <0\|1\|2>` | normal | `:153` | 0 = no cull, 1 = normal, 2 = cull w/o BSP cull. |
| `$world skybox_farplane <f>` | SETTER/normal | `:271`, `:280` | Separate farplane for the skybox portal. |
| `$world animated_farplane <start end Zstart Zend>` | normal | `:208` | Engine-side height-interpolated farplane (varies with player Z). Per-player via `player->origin.z` (`worldspawn.cpp:861`). NOT a time animation. |
| `$world animated_farplane_color <cStart cEnd Zstart Zend>` | normal | `:144` | Height-interpolated color. |

### Replication / why it is coop-safe
`World::UpdateFog()` (`worldspawn.cpp:651`) packs cull/distance/bias/skybox/color into one
string and calls `gi.setConfigstring(CS_FOGINFO, …)` (`:682`). Every `farplane*` setter calls
`UpdateFog()`, so the value is pushed to **all connected clients** automatically. No cgame
change required for fog.

### Smoothly animating fog over time (existing patterns)
The campaign steps farplane in a `for` loop with small `wait`:

- `maps\m4l3.scr:890` `intro_truck_pushfog` — `for (local.i=1500; local.i<=2700; local.i+=50){ $world farplane local.i; wait .2 }`
- `maps\m4l3.scr:893` and `:1299` — additional stepped farplane loops.
- `global\RoomTransform.scr:192` `RampDownFog` — sets `farplane_color` then `for (i=3500; i>1000; i-=100){ $world farplane i; wait .2 }`.
- `m3l1a.scr`, `M3L3.scr`, `m6l2a.scr` use the same step idiom (per task brief).

**Pattern to reuse:** to roll fog in, lerp `farplane` *down* (e.g. 8000 → 1200) and shift
`farplane_color` toward a desaturated grey; to clear, lerp back up. Step every 0.1–0.2 s.
Raising farplane removes fog; lowering it thickens fog.

---

## 2. RAIN / SNOW

### Rain rendering (cgame)
- `cgame/cg_nature.cpp:80 CG_Rain()` draws rain as CG beams every frame for the `ET_RAIN`
  entity. Spawn box is clamped to `cg.rain.min_dist` around `cg.refdef.vieworg`
  (`cg_nature.cpp:109`), i.e. rain follows each player's camera automatically.
- Splash on impact: `RainTouch()` swaps the beam to `splash_z.spr` (`cg_nature.cpp:36`).
- Render dispatch: `cg_ents.c:576 case ET_RAIN: CG_Rain(cent);`.
- Master toggle cvar: `cg_rain` (default "1") — `cg_nature.cpp:61`. Client-side; `cg_rain 0`
  disables rain locally.

### Rain parameters — server-driven, REPLICATED
Client reads them from configstrings in `cg_main.c:391-436` (`CS_RAIN_DENSITY` … `CS_RAIN_NUMSHADERS`).
The server sets those configstrings through **`level` properties** (`fgame/level.cpp`):

| Script (set on `level`) | Event | level.cpp | Configstring |
|---|---|---|---|
| `level.rain_density = <f>` | SETTER `rain_density` | `:410` def, `:2278` impl | `CS_RAIN_DENSITY` |
| `level.rain_speed = <f>` | `rain_speed` | `:430`, `:2288` | `CS_RAIN_SPEED` |
| `level.rain_speed_vary = <i>` | `rain_speed_vary` | `:450`, `:2298` | `CS_RAIN_SPEEDVARY` |
| `level.rain_slant = <i>` | `rain_slant` | `:470`, `:2308` | `CS_RAIN_SLANT` |
| `level.rain_length = <f>` | `rain_length` | `:490`, `:2318` | `CS_RAIN_LENGTH` |
| `level.rain_min_dist = <f>` | `rain_min_dist` | `:510`, `:2328` | `CS_RAIN_MINDIST` |
| `level.rain_width = <f>` | `rain_width` | `:530`, `:2338` | `CS_RAIN_WIDTH` |
| `level.rain_shader = <str>` | `rain_shader` | `:550`, `:2348` | `CS_RAIN_SHADER` |
| `level.rain_numshaders = <i>` | `rain_numshaders` | `:570`, `:2358` | `CS_RAIN_NUMSHADERS` (broken on protocol ≤ MOH, `:2360`) |

All of these are `gi.setConfigstring(...)` (e.g. `level.cpp:2280`). **Configstrings replicate
to every client**, so raising/lowering `level.rain_density` makes rain intensity change
identically for all coop players with no cgame change. Defaults are set in `level.cpp:965-973`
(`CS_RAIN_DENSITY "0"`, shader `"textures/rain"`).

`global\weather.scr` already drives these: `weather.scr:378 level.rain_density = level.raindensity`
and `weather.scr:385 level.rain_slant = local.raindensity`. So the existing mod weather system
*already* writes the replicated rain configstrings — that part is coop-safe today.

### The rain VOLUME — the one real limitation
The visible rain only exists where an `ET_RAIN` entity exists. `ET_RAIN` is created **only**
by the `func_rain` brush class (`fgame/nature.cpp:71 CLASS_DECLARATION(Entity, Rain, "func_rain")`,
`nature.cpp:82 edict->s.eType = ET_RAIN`). There is **no script command to spawn a `func_rain`
volume** and `spawn`-ing a `script_model` will not become `ET_RAIN`. Consequences:

- On maps that ship a `func_rain` brush (storm maps), `level.rain_density` controls visible
  rain for everyone — perfect.
- On maps without one, `level.rain_density` changes nothing visible (no `ET_RAIN` to iterate),
  though you still get rain *sound* (section 3) and fog/darkening.

> If visible rain everywhere is a hard requirement, that needs a cgame change (e.g. a
> camera-anchored rain box, or letting script flag an entity as `ET_RAIN`). Pure-script can
> only guarantee rain where the level geometry already provides the volume.

### Rain assets under maintt
- Shader: default `textures/rain` (`level.cpp:972`); `splash_z.spr` for splashes
  (`cg_nature.cpp:36`). These ship in base `pak`s, so available under maintt.
- Rain *sounds* — see section 3 (alias-gated).

### Snow
No snow particle path exists in the engine (grep of cgame/fgame for "snow" returns only
footstep sounds `fs_snow_*`). The only snow visual asset found is
`UBER-MODS-v8.00-MOHAA\models\emitters\snowdrift.tik` (UBER/Spearhead-side asset — **flag as
NOT guaranteed under maintt**). Implementing snow would require attaching an emitter `.tik`
to each player's view (same per-player attach problem as the e1l1 storm, section 5/6).
**Recommendation: defer snow; not natively supported.**

---

## 3. LIGHTNING + THUNDER

### Existing flash technique (`global\weather.scr`)
- `weather.scr:346 flash:` → `setcvar "r_fastsky" "1"` + `$world farplane_color (0.9 0.9 0.9)`
  + `show` any `level.weatherF[]` flash entities.
- `weather.scr:355 unflash:` → `setcvar "r_fastsky" "0"` + restore `farplane_color` + `hide`.
- `weather.scr:268 singlethunder:` strobes flash/unflash (1–3 flicker patterns) then plays
  thunder: `weather.scr:321 if ($player){ $player playsound thunder }`.
- `weather.scr:335 thunder:` loop waits `level.thundertime + randomint(level.thundertime*1.5)`
  then `waitthread singlethunder`, gated by `level.thunder` (`:338`).

### Coop correctness of the flash
- `farplane_color (0.9 0.9 0.9)` → replicated via `CS_FOGINFO` ⇒ all clients see the brief
  fog-color brightening. **Coop-safe.**
- `setcvar "r_fastsky" …` → `ScriptThread::SetCvarEvent` = `gi.cvar_set` (`scriptthread.cpp:3074`),
  a **server cvar set**. `r_fastsky` is a *renderer client* cvar; setting it on the server
  does not push to remote clients. ⇒ **Only the listen-server host sees the fastsky white
  flash; remote players do not.** This is the main coop defect in the inherited flash.
- **Coop-correct sky flash via pure script:** pulse `$world farplane_color` toward white for
  ~0.1 s and back (replicated to all). Optionally combine with a brief raise of ambient via
  the worldspawn `ambient`/`suncolor` events (section 4) — but those are NORMAL events that
  also funnel through configstrings/`UpdateFog`-style updates, so they replicate. Avoid
  relying on any `r_*`/`cg_*` cvar for the visible flash.

### Thunder sound — replicated, but alias-gated
- `$player playsound thunder` plays per-player; in coop iterate all players (`$player` is the
  player array). `playsound` on a player entity is server-driven and each client hears it.
- Aliases in **maintt** ubersound: `ubersound\ubersound.scr:1105-1107`
  `thunder1/2/3 → sound/amb/Amb_Thunder_0{1,2,3}.wav`, **but gated `maps "m5l1"`**. The
  generic alias `thunder` (used by `weather.scr:322`) is not guaranteed on arbitrary maps.
- The `.wav` files (`sound/amb/Amb_Thunder_*.wav`, `Amb_Rain*.wav`) live in base paks, so the
  audio data is present; only the alias *map filter* blocks them.
- **Fix (script/asset, not dll):** add map-agnostic aliases in the mod's ubersound (remove
  the `maps "…"` restriction or list the m-series maps), e.g.
  `alias thunder sound/amb/Amb_Thunder_01.wav … local streamed`. `local` channel is the
  recommended spatialization for omni sounds like thunder (`ubersound.scr:45` comment).

### Delayed thunderclap after lightning (realistic timing)
Lightning is visual (instant), thunder is delayed by distance. Pattern:
`thread flash; wait flashDur; thread unflash; wait (1 + randomfloat(2)); <play thunder on all players>`
— mirror `weather.scr:268-326` but replace the single-player `playsound` with an all-players
loop and a fog-color pulse instead of `r_fastsky`.

---

## 4. SKY / CLOUDS / DARKENING

Worldspawn light/sun events (`fgame/worldspawn.cpp`), all replicate through worldspawn
config updates:

| Command | Line | Effect |
|---|---|---|
| `$world ambient <intensity>` | `:343` | Ambient light intensity. |
| `$world ambientlight <bool>` | `:334` | Enable/disable ambient light. |
| `$world suncolor (r g b)` | `:352` | Sun color. |
| `$world sunlight <bool>` | `:361` | Sun on/off. |
| `$world sundirection (p y r)` | `:370` | Sun direction. |
| `$world skyalpha <f>` | `:406` | Sky portal alpha. |
| `$world skyportal <bool>` | `:415` | Toggle sky portal. |
| `$world skybox_farplane`, `skybox_speed` | `:271`, `:298` | Skybox clip / scroll speed (move clouds). |

**Darkening for a storm (pure script, coop-safe):** the most reliable, fully-replicated lever
is **`$world farplane_color` shifted toward dark grey + `farplane` pulled in** (fog does the
visual darkening because distant geometry fades to fog color). Optionally lower
`$world ambient` / change `suncolor` for added gloom. To gradually darken then restore, lerp
`farplane_color` over N steps exactly like the `RampDownFog` loop (`RoomTransform.scr:192`).

Note `global\ambient.scr` historically animated gamma/haze via `setcvar r_gammabias`
(`ambient.scr:289`) and `setcvar r_farplane_color` (`ambient.scr:309`), but **those code paths
are explicitly disabled in coop** — `lightlevel`/`lighten`/`darken` all early-out via
`if(waitthread coop_mod/main.scr::inCoopMode){ end }` (`ambient.scr:249, 301, 323`). They are
also client cvars and would not replicate anyway. Do not build on `r_gammabias`/`r_farplane_color`
for coop; use `$world` events.

---

## 5. EXISTING SYSTEMS — `global\weather.scr` and `global\ambient.scr`

### `global\weather.scr` (the existing weather state machine — build on this)
A full rain/thunder/wind system keyed off four numeric "weather patterns" 0–3:

- **Init** (`weather.scr:1-129`): caches `level.farplane`/`farplane_color` from `$world`,
  builds entity arrays from map targetnames `$weatherF` (flash entities), `$weatherR`
  (roof/rain-sound emitters), `$weatherI` (interior), `$weatherW` (window), `$wind`. These
  are **map-authored entities**; on maps without them the arrays are size 0 and those parts
  no-op.
- **State driver** (`weather.scr:223 weatherchanger` / `:246 medicchanger`): a hardcoded
  timed sequence that walks `level.weatherpattern` 0→1→2→3→2→1→… with `wait`s. This IS an
  existing weather state machine — but it's a fixed loop, not random, and not gradual at the
  state boundaries (it relies on `weatherpattern:` smoothing).
- **Smoothing** (`weather.scr:169 weatherpattern`): low-pass filters wind/shutter/rain
  density/volume/thunder-time toward the target pattern's values with `local.trans = 0.07`
  per second (`:208-213`). **This is the gradual-transition engine you want** — targets are
  per-pattern constants (`:163-198`); the actual `level.*` values ease toward them. Already
  produces natural ramps.
- **Apply** (`weather.scr:365 weatherloop`): converts `level.raindensity`/`rainvolume` into
  `level.rain_density` (replicated configstring, `:378`) and `level.rain_slant` (`:385`), and
  loops rain ambience sounds (`rain_ext`/`rain_int`/`rain_roof`/`rain_window`/`rain_puddle`).
  **Most loopsound blocks are gated `if (level.gametype == 0)`** (`:398, 422, 433`) — i.e.
  single-player only; the `$playersound*` emitters are only spawned in SP (`:76-92`). So in
  coop the rain *sound* via these `$playersound` entities does not play; only the
  `level.weatherR[]`/`weatherW[]` map-entity loops (`:441-459`) run regardless.
- **Thunder** (`:268-344`): flash/unflash + per-player thunder (SP-only `playsound`, `:319`).
- **Wind/trees** (`:477 treemovement`): `setcvar r_static_shadermultiplier1` (client cvar,
  won't replicate) for foliage sway.

**Verdict:** `weather.scr` is a genuine, reusable state machine with a working easing layer
and already writes the replicated `level.rain_density`/`rain_slant`. Its weaknesses for coop:
(a) the sequence is deterministic, not random; (b) thunder/rain *sound* and the `r_fastsky`
flash are SP-gated or client-cvar based so they don't replicate; (c) it depends on
map-authored `$weatherF/$weatherR/...` entities that most m-series maps lack. A random coop
system can **reuse the `weatherpattern` easing math and the `level.rain_density` writes**, and
**replace** the deterministic `weatherchanger` and the SP/cvar-bound flash & sound paths.

### `global\ambient.scr`
Music/ambience + interior/exterior trigger bookkeeping. The fog/haze/gamma animators
(`lightlevel`, `lighten`, `darken`) are **all disabled in coop** (`:249, :301, :323`). It is
not a usable weather hook for coop beyond confirming we should drive fog via `$world`, not
cvars. `level.farplanerate = 0.015` (`:48`) is the legacy haze step rate.

---

## 6. COOP / MULTIPLAYER replication summary

| Effect | Mechanism | Replicates to all clients? | Coop verdict |
|---|---|---|---|
| Fog distance/color/bias/cull | `$world farplane*` → `CS_FOGINFO` (`worldspawn.cpp:682`) | **Yes** (configstring) | Pure script, safe |
| Rain intensity (density/slant/speed/shader…) | `level.rain_*` → `CS_RAIN_*` (`level.cpp:2278+`) | **Yes** (configstring) | Pure script, safe |
| Rain *volume* existence (`ET_RAIN`) | `func_rain` BSP brush only (`nature.cpp:71`) | N/A — must pre-exist in map | Script cannot create; rain visible only where map provides it |
| Sky flash via `r_fastsky` | `setcvar` = `gi.cvar_set` (`scriptthread.cpp:3074`) | **No** (client renderer cvar) | Host-only; avoid for coop |
| Sky flash via `farplane_color` pulse | `$world farplane_color` → `CS_FOGINFO` | **Yes** | Use this instead |
| Ambient/sun darkening | `$world ambient/suncolor/sunlight` (`worldspawn.cpp:334+`) | **Yes** (worldspawn config) | Pure script, safe |
| Thunder sound | per-player `playsound` (iterate `$player`) | **Yes** (server sound event) | Safe; needs un-gated alias |
| Rain ambience loops | `$playersound* loopsound` | SP-gated in weather.scr (`:398` etc.) | Re-implement as per-player loop for coop |
| Foliage sway | `setcvar r_static_shadermultiplier1` | **No** (client cvar) | Host-only; cosmetic, skip or accept |
| Emitter cube / snowdrift attached to view | `attach`/`glue` to one `$player` | No — single entity, one player | e1l1 storm explicitly SP-gated (`storm.scr:88,131,...`); needs cgame for coop |

**Rule of thumb:** anything routed through `$world` events or `level.rain_*` (i.e. configstrings)
is automatically coop-consistent. Anything routed through `setcvar` of a `r_*`/`cg_*` client
cvar is host-only and must be avoided or replaced. Per-player effects (thunder sound, rain
ambience) must loop over the player array.

---

## 7. Proposed random weather state machine (pure script, coop-safe)

A single `level` thread. All visuals via `$world farplane`/`farplane_color`(+`ambient`),
intensity via `level.rain_density`/`rain_slant`, thunder via fog-color pulse + all-player
`playsound`. Everything below is replicated; **no dll change required.**

### State table

| State | farplane (fog dist) | farplane_color (target) | rain_density | thunder | typical dwell |
|---|---|---|---|---|---|
| CLEAR | high (map default, cache at init) | map default | 0 | off | 90–240 s |
| FOG_ROLLING_IN | lerp high→~1400 | shift toward grey-blue | 0 | off | 20–40 s transition |
| FOG | ~1200–1600 | grey | 0 | off | 60–150 s |
| RAIN_BUILDING | lerp toward ~1600 | darken grey | 0 → ~3 | off | 15–30 s |
| RAIN | ~1500 | dark grey | ~3–5 | off | 60–180 s |
| THUNDERSTORM | ~1100 | darkest grey | ~6–10 | on | 45–120 s |
| CLEARING | lerp back to defaults | lerp to default | →0 | off | 25–45 s |

### Transition mechanics (gradual — never snap)
- Keep current values `level.wx_fog`, `level.wx_fogcolor`, `level.wx_density` and per-state
  *targets*. Every 0.1 s ease current toward target:
  `cur = cur*(1-k) + target*k` with `k≈0.05–0.1` (exactly the `weatherpattern` low-pass at
  `weather.scr:208`). Then push `$world farplane cur_fog`, `$world farplane_color cur_color`,
  `level.rain_density = cur_density`, `level.rain_slant = derived`.
- Color is a vector — ease each component (reuse the vector add idiom in
  `ambient.scr:307` / `RoomTransform.scr` color sets).
- A state's job is only to set the *targets* + pick a randomized dwell time; the easing loop
  produces the smooth ramp automatically. This guarantees "rolls in / builds / passes."

### Logical ordering (makes physical sense)
- Rain is always preceded by FOG/RAIN_BUILDING (clouds = fog darkening first), never snaps
  from CLEAR to heavy rain.
- THUNDERSTORM only reachable from RAIN (storm intensifies).
- Thunder enabled only in THUNDERSTORM (and optionally tail end of RAIN).
- CLEARING always follows storm/rain before returning to CLEAR.
- Random next-state chosen with weighted transitions (e.g. from RAIN: 40% stay, 35%
  THUNDERSTORM, 25% CLEARING), and randomized dwell via `randomint`/`randomfloat`.

### Lightning + thunder timing (realistic)
In THUNDERSTORM, a sub-thread:
1. `wait randomfloat(thunderGap)` (gap shrinks with intensity; reuse `level.thundertime` idea).
2. Lightning: pulse `$world farplane_color` toward near-white for ~0.08–0.15 s (optionally a
   1–3 flicker like `weather.scr:268`), then ease back. (Replicated; replaces `r_fastsky`.)
3. `wait (0.5 + randomfloat(2.5))` — distance delay.
4. Thunder: `for each player { player playsound thunder }` using an un-gated alias.
5. Loop.

### Coop-consistency guarantees
- All state is on `level` (shared server object) and applied via configstrings ⇒ identical
  for every client.
- No `r_fastsky`, no `cg_rain` toggling, no `r_static_shadermultiplier1`, no per-`$player`
  attached emitter for the core system.
- Rain *sound* loops, if wanted, iterate the player array (or use map `level.weatherR[]`
  entities) — never the SP-only `$playersound` entities.

### What stays "best effort" (document, don't block on)
- **Visible rain streaks** appear only on maps with a `func_rain` brush. Elsewhere the storm
  is sold by fog darkening + thunder + (optional) rain ambience. Acceptable for a first
  version.
- **Snow** omitted (no engine support).

---

## 8. If a cgame.dll change is ever desired (scope, optional)

Only two things genuinely need cgame to be "perfect":
1. **Rain anywhere without a map brush** — add a code path that anchors a rain box to
   `cg.refdef.vieworg` driven purely by the `CS_RAIN_*` configstrings (logic already exists
   in `CG_Rain`; it just needs an `ET_RAIN`-less invocation when density>0). ~30–50 lines in
   `cg_nature.cpp` + a trigger configstring.
2. **A true client-side lightning sky flash** (full-screen brighten) instead of the
   fog-color proxy — minor `cg_view`/draw change keyed off a configstring or temp event.

Neither is required for a solid, coop-consistent weather system; both are enhancements.

---

## Appendix — key file:line citations

- Fog setters/getters/replication: `fgame/worldspawn.cpp:117-315, 651-683, 716-763`
- Fog animation loops (script): `maps/m4l3.scr:890-895, 1299`; `global/RoomTransform.scr:192-202`
- Rain render (cgame): `cgame/cg_nature.cpp:36, 61, 80, 109, 159`; dispatch `cgame/cg_ents.c:576`
- Rain configstring parse (client): `cgame/cg_main.c:391-436`
- Rain `level` setters (server, replicated): `fgame/level.cpp:410-588, 965-973, 2278-2371`
- Rain configstring IDs: `fgame/bg_public.h:71-79`
- `func_rain` / `ET_RAIN` (volume creation): `fgame/nature.cpp:71-90`; `bg_public.h:506`
- `func_emitter`: `fgame/nature.cpp:42-61`
- Existing weather state machine: `global/weather.scr` (init `1-135`, smoothing `163-221`,
  changer `217-266`, thunder/flash `268-362`, apply `365-475`)
- Coop-disabled ambient animators: `global/ambient.scr:249, 301, 323`
- `setcvar` = server cvar set: `fgame/scriptthread.cpp:375, 3074`
- Thunder/rain aliases (maintt, map-gated): `ubersound/ubersound.scr:1105-1112`
- e1l1 storm (per-player emitter, SP-gated in coop): `maps/e1l1/storm.scr:28-46, 88-117`
- Snow asset (Spearhead/UBER, not maintt-guaranteed): `UBER-MODS-v8.00-MOHAA/models/emitters/snowdrift.tik`
