# e3l4 cold-load crash — diagnostic breadcrumbs (2026-06-24)

Instrumentation-only pass. **No logic changed, no guards added.** Added cheap
`Com_Printf` / `cgi.Printf` breadcrumbs with the unique greppable prefix
`^E3DBG` along the client gamestate-parse + cgame-init + alias/cache replay path
that the prior investigation (`fix_e3l4_crash2.md`) localized the 0xc0000409
(`__report_gsfailure` /GS stack-overrun) to. The LAST `^E3DBG` line in the
qconsole tail after the crash names the exact configstring / alias / resource
being processed at the fault, pinning the function + the offending buffer.

All breadcrumbs only fire during map load, so they are effectively free.

---

## Files + lines instrumented

### 1. EXE (client) — `code/client/cl_parse.cpp` (`CL_ParseGamestate`)
- **~L544** — entry marker: `^E3DBG CL_ParseGamestate: ENTER`
- **~L575** — per-configstring, inside the parse loop, logged AFTER the string is
  read and its length computed (so an oversized/over-count configstring is the
  last line before a crash):
  `^E3DBG cs idx=<i> (norm=<csNum>) len=<len> dataCount=<n>`
- **~L597** — after the configstring loop:
  `^E3DBG CL_ParseGamestate: configstrings done, dataCount=<n>`

### 2. EXE (client) — `code/client/cl_cgame.cpp` (`CL_InitCGame`)
- **~L924** — entry: `^E3DBG CL_InitCGame: ENTER`
- **~L929** — `^E3DBG CL_InitCGame: mapname='<mapname>'`
- **~L937/939** — around the cgame DLL load:
  `^E3DBG CL_InitCGame: loading cgame DLL` then `... cgame DLL loaded`
- **~L950** — just before the VM entry that replays the cache/alias commands:
  `^E3DBG CL_InitCGame: calling CG_Init (snap.valid=<n>)`
- **~L961** — `^E3DBG CL_InitCGame: CG_Init returned`
- **~L963/965** — around TIKI finalize:
  `^E3DBG CL_InitCGame: calling TIKI_FinishLoad` then `... TIKI_FinishLoad returned`

  (If the last line seen is `calling CG_Init` with no `CG_Init returned`, the
  crash is INSIDE the cgame DLL — i.e. the AliasCache/Alias/CacheResource replay
  below. If `CG_Init returned` prints but `TIKI_FinishLoad returned` does not, the
  fault is in TIKI finalize instead.)

### 3. cgame DLL — `code/cgame/cg_commands.cpp`
- **`CacheResource` (~L4192)** — logs every cached resource path + its length:
  `^E3DBG CacheResource '<path>' (len=<n>)`. The LAST one before the dump is the
  trigger resource.
- **`ClientGameCommandManager::AliasCache` (~L4288)** — entry:
  `^E3DBG AliasCache name='<alias>' real='<realname>' nargs=<n>`; and per
  parameter, logged BEFORE each `strcat` into `parmbuffer[2048]`:
  `^E3DBG AliasCache parm slen=<this_arg_len> parmlen=<used>/2048`
  (so a parm that pushes `parmlen` toward/over 2048 is visible as the last line).
- **`ClientGameCommandManager::Alias` (~L4341)** — entry:
  `^E3DBG Alias name='<alias>' real='<realname>' nargs=<n>`; and per parameter,
  before the `strcat` into `parmbuffer[2048]`:
  `^E3DBG Alias parm slen=<this_arg_len> parmlen=<used>/2048`.

These two `parmbuffer[2048]` strcat loops are the prime overrun suspects flagged
(but not cleared) by the prior pass; the `slen`/`parmlen` numbers make an
oversize directly visible without a debugger.

`parmbuffer[2048]` is now RULED OUT (parmlen stayed ~41 across power_generator2).
The remaining suspect is the operation IMMEDIATELY AFTER power_generator2's
AliasCache returns. The 2026-06-24 pass adds the three breadcrumb layers below to
name it.

---

## NEW (2026-06-24): pin the operation after power_generator2

### 4. cgame DLL — cache-script COMMAND DISPATCH loop
`code/cgame/cg_commands.cpp` — `CG_Command_ProcessFile` (~L5549). This is the
loop that reads each line of the `ubersound/*.scr` cache scripts (where
`aliascache power_generator2 ...` lives) and dispatches it via
`commandManager.SelectProcessEvent(ev)`. Instrumented immediately around the
dispatch call:
- BEFORE dispatch:
  `^E3DBG ProcessFile dispatch cmd='<eventname>' arg1='<first arg>' nargs=<n>`
- AFTER dispatch:
  `^E3DBG ProcessFile dispatch DONE`

So the command line **immediately after** the power_generator2 aliascache is
named by its `cmd='...'`. If that `dispatch cmd=...` line prints with **no**
following `dispatch DONE`, that command is the crasher (case a). The driver of
this loop during CG_Init is `CG_RegisterSounds` -> `CG_RegisterSoundsForFile`
-> `CG_Command_ProcessFile` (see `cg_main.c` ~L247/285).

### 5. cgame DLL — `CacheResource` registration dispatch (case b)
`code/cgame/cg_commands.cpp` — `CacheResource` (~L4189). The entry-path log
(`^E3DBG CacheResource '<path>' (len=)`) was already present. Added BEFORE/AFTER
breadcrumbs bracketing the *actual* underlying registration call, split per
extension so the dispatch target is explicit:
- `.wav`/`.mp3`: `^E3DBG CacheResource BEFORE/AFTER S_RegisterSound(wav|mp3) '<path>'`
- `.tik`: `^E3DBG CacheResource BEFORE/AFTER R_RegisterServerModel '<path>'`
- `.spr`: `^E3DBG CacheResource BEFORE/AFTER R_RegisterShader '<path>'`

A `BEFORE` with no matching `AFTER` = the registration of that resource faults.
`SubPen_Generator_Run.wav` takes the `.wav` -> `S_RegisterSound` branch.

### 6. EXE (client) — WAV/sound load function
`code/client/snd_mem_new.cpp` — `S_LoadSound` (~L432, the new OpenAL-system
loader; `cgi.S_RegisterSound` -> `S_RegisterSound` (snd_dma_new.cpp ~L347) ->
`S_LoadSound`). Breadcrumbs:
- entry: `^E3DBG S_LoadSound ENTER file='<path>' streamed=<n> force=<n>`
- after FS_FOpenFileRead: `^E3DBG S_LoadSound '<path>' fileSize=<n>`
- around the RIFF header parse:
  `^E3DBG S_LoadSound BEFORE GetWavinfo '<path>' size=<n>` then
  `^E3DBG S_LoadSound AFTER GetWavinfo '<path>' rate= width= ch= samples= dataofs= datasize=`

If `BEFORE GetWavinfo` prints with no `AFTER`, the RIFF-header parse in
`GetWavinfo` (same file, ~L217) is the fault. `GetWavinfo` was reviewed and does
NOT write parsed header fields into a fixed stack buffer (DumpChunks' `str[5]` is
the only fixed buffer and is unreachable here), so the BEFORE/AFTER bracket is the
needed instrumentation rather than an inner-buffer length log. NOTE for the
*fix* pass (not touched now): `S_RegisterSound` (snd_dma_new.cpp ~L362-365)
lower-cases `name` into `szCacheName[MAX_QPATH]` and writes the NUL terminator at
`szCacheName[i]` where `i` can reach `MAX_QPATH` (one past the array) before the
`i >= MAX_QPATH` check at L367 — a candidate /GS off-by-one if a cached sound
name is exactly MAX_QPATH long. Left as-is per breadcrumbs-only scope.

---

## Rebuild targets

Two separate build artifacts are on the crash path, so REBUILD BOTH:

1. **EXE** — CMake target **`openmohaa`** (output `openmohaa.exe`). Covers the
   `cl_parse.cpp` + `cl_cgame.cpp` breadcrumbs AND the new `snd_mem_new.cpp`
   `S_LoadSound`/`GetWavinfo` breadcrumbs (the sound loader is compiled into the
   exe, not the cgame DLL).
2. **cgame DLL** — CMake target **`cgame`** (output `cgame.dll`, see
   `code/cgame/CMakeLists.txt`: `add_library(cgame SHARED ...)` /
   `OUTPUT_NAME "cgame${TARGET_BIN_SUFFIX}"`). Covers the `cg_commands.cpp`
   breadcrumbs (`CG_Command_ProcessFile` dispatch loop + `CacheResource`).
   NOTE the target is named **`cgame`** but its Release artifact lands at
   `.cmake\code\client\cgame\Release\cgame.dll` (the `code/cgame` source dir is
   pulled in under the client build tree). That is exactly the path `build.ps1`
   (line 16) deploys from — confirmed.

Build both, e.g. from the existing `.cmake` build dir:
```
cmake --build C:\mohaa-coop-dev\openmohaa-hzm\.cmake --config Release --target openmohaa cgame
```

### Deploy
- `openmohaa.exe` deploys to the GOG root
  `G:\GOG\Medal of Honor - Allied Assault War Chest\` (the running exe the dumps
  reference). `build.ps1` does NOT copy the exe — copy the freshly built
  `openmohaa.exe` there manually.
- `cgame.dll` is loaded from the **GOG root** (NOT `maintt`). `build.ps1` already
  handles this (line 16): it copies
  `C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll` ->
  `G:\GOG\Medal of Honor - Allied Assault War Chest\cgame.dll`. So after building
  the `cgame` target, running `build.ps1` deploys the DLL (and the pk3/cfg).
  Make sure the game is closed or the copy is skipped with a WARNING.

(Optional, for the next pass: building RelWithDebInfo would also yield a matching
PDB, but breadcrumbs alone are enough to pin the buffer here.)

---

## Grep to run after reproducing the crash

Reproduce the e3l4 cold-load crash, then tail the qconsole log for the last
`^E3DBG` lines. Logs live under `%APPDATA%\openmohaa\<fs_game>\qconsole.log`
(this mod runs in `maintt`):

PowerShell (last 40 breadcrumb lines):
```powershell
Select-String -Path "$env:APPDATA\openmohaa\maintt\qconsole.log" -Pattern '\^E3DBG' |
  Select-Object -Last 40 | ForEach-Object { $_.Line }
```

Bash (Git Bash):
```bash
grep -a '\^E3DBG' "$APPDATA/openmohaa/maintt/qconsole.log" | tail -40
```

If the game also writes to the basepath, also check
`G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\qconsole.log`.

### How to read the result
- **Last line is `^E3DBG cs idx=... len=...`** → the crash is in
  `CL_ParseGamestate`; that configstring's index/len is the offender (oversized
  or over-count configstring overrunning the gamestate buffer).
- **Last line is `^E3DBG CL_InitCGame: calling CG_Init ...`** (no `CG_Init
  returned`) → crash is inside the cgame DLL replay; the LAST `^E3DBG
  CacheResource / AliasCache / Alias` line before it names the resource/alias.
- **Last line is `^E3DBG AliasCache parm ...` / `Alias parm ...` with
  `parmlen` near/over 2048** → confirms the `parmbuffer[2048]` strcat overrun;
  the alias `name=` from the immediately preceding entry line is the trigger.
- **Last line is `^E3DBG CacheResource '<path>'`** → that resource registration
  (sound/model/shader) is faulting.

### New cases (2026-06-24) — narrowing the post-power_generator2 op
- **Last line is `^E3DBG ProcessFile dispatch cmd='X' ...`** (no following
  `^E3DBG ProcessFile dispatch DONE`) → **case (a)**: the cache-script command
  `X` (the line right after power_generator2) is the crasher. `X` names the
  exact event handler to look at next.
- **Last `dispatch cmd=` is the power_generator2 aliascache, FOLLOWED BY
  `dispatch DONE`, then the NEXT `dispatch cmd='Y'` with no `DONE`** → command
  `Y` is the crasher (cleaner confirmation of case a).
- **Last line is `^E3DBG CacheResource BEFORE S_RegisterSound(wav) 'sound/mechanics/SubPen_Generator_Run.wav'`**
  (no `AFTER`) → **case (b)**: the sound registration itself faults; follow the
  `S_LoadSound` breadcrumbs.
- **Last line is `^E3DBG S_LoadSound BEFORE GetWavinfo '...'`** (no `AFTER`) →
  the RIFF/WAV header parse in `GetWavinfo` is the fault.
- **`S_LoadSound ENTER` prints but `... fileSize=` does not** → fault is in
  `FS_FOpenFileRead` for that path.

That last `^E3DBG` line pins the exact function + buffer for the next pass to add
the correct bounds guard (named-constant + guard pattern, no silent truncation).
