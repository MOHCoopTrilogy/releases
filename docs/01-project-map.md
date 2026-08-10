# 01 — Project Map, Build, Deploy, Test

Verified against the working tree 2026-07-29. Supersedes the stale parts of `CLAUDE.md`.

---

## 1. What lives where

| Path | What it is | Git |
|---|---|---|
| `C:\mohaa-coop-dev\` | Release/publish repo (manifests, `build.ps1`, `publish_release.ps1`) | `origin main`, HEAD `216f7ca manifest 1.1.55` |
| `hzm-mohaa-coop-mod/` | The mod: 479 `.scr` total (118 top-level `maps/*.scr`, 268 under `maps/` recursively, 96 in `coop_mod/`), plus ui, sounds, textures, tiks | nested repo → `git push org coop-wip`, HEAD `f10ac19 v1.1.54` |
| `openmohaa-hzm/` | HZM fork of the OpenMOHAA engine (C/C++, CMake) | → `git push org hzm-coop-working`, HEAD `819a6e93` (2026-07-23) |
| `moh-modelviewer/` | Node model preview tool | rarely touched |
| `.wolf/` | OpenWolf memory. `buglog.json` = still useful; `memory.md`/`cerebrum.md` = mined into `docs/` |
| `G:\GOG\Medal of Honor - Allied Assault War Chest\` | The **play install** (basepath + engine binaries in root) |
| `%APPDATA%\openmohaa\maintt\` | Homepath — **wins over basepath** for pk3 load order |
| `G:\mohaa-gl2\` | Isolated gl2 sandbox. `maintt` is a **junction to the real GOG maintt** |

> ⚠️ **Uncommitted work is the single largest risk in this project right now.**
> Engine repo: 139 modified files on top of a 2026-07-23 commit. Mod repo: 146 modified files
> on top of v1.1.54. Everything after those dates — the gore chain, the entity-1023 fix, all gl2
> work, the font swap, `MAX_SOUNDS 1600`, the 13-bit `frameInfo` widening — exists **only in the
> working tree**. There is no restore point for any of it.

---

## 2. Build & deploy

### Mod content (scripts, cfg, ui, textures, sounds — the common case)

```powershell
# from C:\mohaa-coop-dev
.\build.ps1
```

`build.ps1` packs `hzm-mohaa-coop-mod/` into the coop pk3 set and deploys to **both** `maintt`
folders, plus `autoexec.cfg` and `coop_defaults.cfg`.

**It also unconditionally deploys two engine binaries to the GOG root** (`build.ps1:132-150`):
`cgame.dll` and `renderer_opengl1.dll`, from `.cmake/`. This is intended for shipping, but it is
also a live footgun — see [03-record-vs-code.md](03-record-vs-code.md) §gl2-sandbox and bug-1172.
**Before any mod-only `build.ps1` run, check whether the current `.cmake` output for those two
DLLs contains engine changes not approved for the real install.**

`build.ps1` does **not** deploy `game.dll` or `openmohaa.exe` — those are manual copies.

### Engine

```sh
cd openmohaa-hzm/.cmake
cmake --build . --config Release --target cgame          # cgame.dll  → GOG root (build.ps1 does this)
cmake --build . --config Release --target fgame          # game.dll   → GOG root (MANUAL, back up first)
cmake --build . --config Release --target openmohaa      # openmohaa.exe → GOG root (MANUAL)
cmake --build . --config Release --target omohrenderergl1  # renderer_opengl1.dll (build.ps1 does this)
cmake --build . --config Release --target omohrenderergl2  # renderer_opengl2.dll
```

Rules, all evidenced:

- **One `--target` per `cmake --build` invocation.** Multiple targets → MSB1008 through this
  project's MSBuild wrapper (cerebrum 2026-07-28).
- **Target names ≠ output names.** `omohrenderergl2` produces `renderer_opengl2.dll`. Check the
  `.vcxproj` list rather than guessing (cerebrum 2026-07-28).
- **Renderers are separate DLLs** (`USE_RENDERER_DLOPEN=ON` in `.cmake/CMakeCache.txt` — note the
  `CMakeLists.txt:17` *default* is `OFF`; the cache is what this build actually uses). A `tr_*.c`
  fix ships as a renderer DLL, never as an exe rebuild.
- **Header constant changes can be missed by incremental builds.** Touch the `.cpp` that *defines*
  the array (e.g. `actor.cpp` for `MAX_BODYQUEUE`) or the old value stays in the DLL
  (cerebrum 2026-06-28).
- **Never chain build → deploy → boot in one background command.** Build in the foreground, verify
  the `.dll ->` line, *then* launch. Two 4-minute boots ran against a stale DLL after a silent
  `LNK2019` (cerebrum 2026-07-28).
- **Never `Select-Object -Last N` a cmake build and call it verified** — it has hidden a failed
  build and shipped a stale DLL. Grep for `error`, or check the output timestamp (cerebrum 2026-07-28).
- After many rapid incremental fgame/cgame builds, `--clean-first` before the deploy build, then
  headless-boot and grep for `Event 'damageable' does not exist` — the event-registry corruption
  canary (bug-961).

### Deploy gap trap

pk3s and DLLs are **file-locked while the game runs**, so deploys silently fail mid-session. If a
whole batch of fixes is reported "still broken", suspect the game never closed. Conversely, a
clean error-free `cp` over `openmohaa.exe` / `renderer_*.dll` is itself proof the process was not
running (cerebrum 2026-07-28, bug-1163).

---

## 3. Which binaries must ship together

Any change to a **cross-binary protocol constant** requires `openmohaa.exe` + `cgame.dll` +
`game.dll` rebuilt and deployed as one set. `gameState_t` is `memcpy`'d whole across the
exe↔cgame boundary with **no API version guard**, so a stale DLL corrupts memory silently
(`q_shared.h` comments; bug-1180).

Constants in that class: `MAX_CONFIGSTRINGS`, `MAX_SOUNDS`, `MAX_MODELS`, `MAX_WEAPONS`,
`GENTITYNUM_BITS`, and any `msg.cpp` netfield width.

**Not** in that class: renderer-local constants (`MAX_ENTITIES` in gl1, `MAX_SHADERS`) and
per-process caches (`MAX_TIKI_ALIASES`) — those have no network implication (bug-1172).

---

## 4. Running and testing

### Normal play (listen server)

1. Launch OpenMOHAA on the Breakthrough profile (`com_target_game 2`).
2. Multiplayer → Start Game → **HaZardModding Coop Mod**.
3. Pick a map tile → Apply. That execs `coop_mod/start_server.cfg`, ending in `ui_startdmmap 2`.

**Always `ui_startdmmap 2`.** Raw `map <name>` / `devmap` takes the SP loading path even with
`g_gametype 2` latched → "Continue" button, coop init skipped.

`com_target_game 2` (BT) mounts **all three** pak sets (`main` + `mainta` + `maintt`), so
Spearhead t-series maps run fine under the normal launch. The old "t-series needs target 1" note is
**obsolete and inverted** — under target 1 the coop pk3s never mount at all.

### Headless / scripted boots

- **`omohaaded.exe` does not work on this fork** — it never executes buffered commands
  (`+map`, cfg, console all queue forever). Do not re-diagnose (bug-999).
- **Use `openmohaa.exe` as a listen server instead** (cerebrum 2026-07-22):
  ```
  openmohaa.exe +set fs_homepath <isolated> +set g_gametype 2 +set net_port 12203
                +set r_fullscreen 0 +set com_abnormalExit 0 +exec boot_<map>.cfg
  ```
  with `boot_<map>.cfg` = `seta developer 1; set ui_dmmap <map>; exec coop_mod/start_server.cfg`.
  Load/init crashes (the P0 class) reproduce solo; player-count-gated bugs do not.
- **`+set com_abnormalExit 0` is mandatory** in harnesses, or the exe can relaunch itself after a
  taskkill and the phantom holds `qconsole.log` (bug-1143 family).
- **Never force-kill the game.** A killed process leaves a stale `OpenMoHAA.pid`, and the next boot
  blocks on a modal "Abnormal Exit" dialog (`sys_main.c:255`) — the harness then mis-reports
  "SERVER NEVER READY" (bug-1064). Clean quit = `PostMessage WM_CLOSE` to the window titled exactly
  `OpenMoHAA`.

### Driving the game yourself (rcon)

The user is the sole tester and has explicitly asked **not** to be handed debug homework. Drive
the console yourself:

- `set rconpassword "hzmdev"` lives in the untracked autoexec; send via `python scratchpad/rcon.py "<cmd>"` → `127.0.0.1:12203`.
- **The rcon packet needs the connectionless DIRECTION byte**: `\xff\xff\xff\xff\x02` + `"rcon pw cmd"`.
  Without `\x02` the server tokenizes `"con"`, logs `bad connectionless packet`, and executes
  **nothing** — while still echoing the packet, which reads as success. Port this into any older
  `rcon.py` before trusting it (bug-1143).
- On a **listen server**, rcon commands run as **the host player** (`g_entities[0]`), so `tele x y z`,
  `face p y r`, `weapnext`, `kill` all act on the host. `EV_CHEAT` commands need boot-time
  `+set thereisnomonkey 1` (cerebrum 2026-07-27).
- Open menus with `rcon pushmenu <name>` (`dm_main` **is** the ESC board). **Do not** use
  `keybd_event` — SDL ignores synthetic key events (cerebrum 2026-07-28).
- `CVAR_CHEAT` diagnostics are **dead on a listen server** (`sv_cheats 0` clamps them back to 0).
  Register investigation-time diagnostics as `CVAR_TEMP` (cerebrum 2026-07-28).
- **Never `seta` a `CVAR_ARCHIVE` cvar over rcon during a probe** — it is written into the sandbox
  `omconfig` on exit and poisons every later run. Force experiment cvars in both the boot cfg and
  the command line (cerebrum 2026-07-28).

### Dev visibility — the gate that hides everything

**`developer 1` is required for dev sessions** (bug-911). Both script `println` output *and*
script compile/runtime errors are developer-gated (`ScriptThread::Println` early-returns at
`scriptthread.cpp:2869`). The engine's own `^~^~^` lines are C-side `Com_Printf` and always print —
**a log full of `^~^~^` does not mean script prints are working.**

Print routing, which is not intuitive:

| Call | Reaches the player | Reaches `qconsole.log` |
|---|---|---|
| `println` | no | **only with `developer 1`** |
| `iprintln` / `iprintlnbold` | yes (HUD) | yes (text is echoed) |

So: HUD-visible bisect prints use `iprintlnbold`; greppable machine lines use `println` prefixed
`^~^~^` **plus** `developer 1`. Gate every diagnostic print behind the project's
`level.cMTE_coop_*` flag — dev prints must never reach players.

### Automated map-rotation tester

```
exec coop_mod/cfg/maptest_start.cfg     # Phase 2 patrol (54 maps)
exec coop_mod/cfg/maptest_start_sh.cfg  # Spearhead t-series
exec coop_mod/cfg/maptest_stop.cfg
```
`coop_maptest 1` = load smoke test, `2` = player-teleporting patrol. Watched by
`maptest_monitor.ps1` / `maptest_watchdog.ps1` via the `^~^~^` prefix.

### The standing console-watch rule

**After every deploy + boot, sweep the whole log — not just the feature under test.** Standard grep:

```
Script Error|Couldn't compile|Couldn't parse|not properly loaded|ERROR|WARNING|failed|Registration failed|exceeded|overflow
```

Report anything new even if unrelated. Treat `Couldn't load X` as a **real defect** until both the
file's existence *and* its format are verified — the Frontline stingers were silent for a week
behind a warning dismissed as cosmetic (bug-933b).

Log file: `%APPDATA%\openmohaa\maintt\qconsole.log`. `logfile 2` in autoexec keeps it flushed
per-line for live tailing.

---

## 5. Mod architecture (unchanged and still accurate)

Every coop-integrated map script calls, **first, with no delay before it**:

```
waitthread coop_mod/main.scr::main
```

which initialises the whole framework **synchronously in one frame** (`wait`/`waitframe` are
forbidden in or before it):

```
variables.scr::main      → global constants
server.scr::main         → server cvars, dedicated/listen detection
spawnlocations.scr::main → spawn points
player.scr::manage       → per-frame player lifecycle (thread)
events.scr::init         → event subscriptions
officer.scr::init        → boss AI wave system
```

`level.coop_mainScriptLoaded` gates everything; late callers use
`coop_mod/main.scr::waitForMainScript`.

**63 of 118 `maps/*.scr` are coop-converted** (they call `coop_mod/main.scr::main`). The rest are
sub-scripts, gags, and unconverted retail. The mod ships only a **partial** override set of
`maps/` and `global/` — retail scripts it does not ship still run from the pak and were **never
coop-converted**. Always check `original-scripts/<game>/` before assuming a per-site patch can
cover a global (bug-1212).

Per-player state lives in `self.flags["coop_*"]`. `$player` is a **1-indexed array**; `$player.size`
is the connected count. Gametype must be `g_gametype 2` (Team Match); coop features gate on
`level.gametype != 0`.

### Map transition

- **Clean restart / advance**: `stuffsrv "map <name>"` → `SV_Map_f`. No archive, no gametype flip.
- **Never** `bsptransition`, `loadMap`, or `leveltransition` on a live coop server — they run the
  persistant archive and crash.
- `game.*` script vars **do not survive** a coop map transition: `SV_SpawnServer` tears down and
  re-inits the game DLL, and the persistant-archive restore is gated to `GT_SINGLE_PLAYER`
  (`sv_ccmds.c:301`). Cross-map persistence = cvars or files (cerebrum 2026-07-06).
