# tools/ — gl2 A/B sweep + upgrade preview

Dev-only helpers for evaluating the OpenGL2 (rend2) renderer across the trilogy. **Nothing here
ships** — no pk3, no manifest, no change to player defaults (`omconfig_default.cfg` / `autoexec.cfg`
are untouched). These exist so you can A/B the gl2 wins and pick what to promote later.

## Files

| File | What it is |
|------|-----------|
| `gl2_ab_sweep.ps1` | Hardened screenshot sweep: launches each map under several renderer configs and captures a shot per config. |
| `gl2_upgrades.cfg` | Opt-in preview of the confirmed gl2 wins (`exec` it in-game, or it's the `gl2-upgraded` leg of the sweep). |
| `gl2_ab_maps.txt` | Editable map list the sweep reads. |

## Why the sweep was rewritten

The earlier sweep spiralled into a runaway that piled up ~24 `openmohaa` processes and, combined
with the machine load, is the likely reason the remote-control link dropped. The session diagnosed
three root causes; this version designs all three out, plus adds a hang watchdog:

1. **Two sweeps running at once** cross-killed each other's boots → cascade of respawns.
   → **Single global mutex.** A second sweep refuses to start.
2. **Killing `openmohaa` by name** nuked the *other* sweep's (and any play session's) instances.
   → **Only ever kills the exact PID it launched**, and that PID's child tree.
3. **`taskkill` left hung instances alive.**
   → **`Stop-Process -Force`** with empty-pipeline guards (what actually cleared them).
4. **A modal-hung map wedged the whole run** into an endless completion-waiter.
   → **Per-boot watchdog** (`-BootTimeoutSec`): a boot that never captures is force-killed and
   recorded as a miss; the sweep moves on.

## Usage

```powershell
# always dry-run first — prints the map × config matrix, launches nothing
.\tools\gl2_ab_sweep.ps1 -DryRun

# real run (writes shots to C:\mohaa-coop-dev\gl2_ab by default)
.\tools\gl2_ab_sweep.ps1
```

Output files are named `<map>__<config>.jpg` so gl1 / gl2-default / gl2-upgraded line up per map.

## ⚠️ Before you trust it

Built off-machine and **untested** — the process-management skeleton is the hardened part, but the
in-engine **capture step** (how the boot cfg loads a map, dwells, screenshots, quits) is a
template. Confirm it matches how your original sweep drove the engine (the mod's `coop_maptest`
mode is an alternative auto-driver), then run once with `-DryRun`, then a single map, before a full
trilogy pass. Cvar names in `gl2_upgrades.cfg` marked "confirm in your build" (`r_forceSun`,
`r_forceToneMap`, `r_cameraExposure`) come from the session's analysis — the rest are straight from
`installer/omconfig_default.cfg`.
