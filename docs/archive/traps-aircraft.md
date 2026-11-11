# Traps found by the aircraft work (2026-10-05)

Moved here because `docs/TRAPS.md` is at its size ceiling. Design and evidence: `docs/proposals/aircraft_2026-10-05/`.

- **An entity above the sky brush is never sent.** `SV_LinkEntity` finds no leaf for a box outside the world, so
  `areanum` is -1 and `numClusters` 0, and `SV_AddEntitiesVisibleFromPoint` skips it before any distance test - its
  loop sound too, unless `levelwide`. `c47fly.tik`/`p47fly.tik` have `setsize -32..32`, so only the origin counts.
  `svflags +broadcast` (or `alwaysdraw`) bypasses it; the renderer then draws it over the sky. bug-3380.
- **Entity origins wrap past +-8192.** `MSG_PackCoord` sends 16-bit quarter units. Keep movers inside +-7900.
  bug-3382.
- **Script `sqrt` is `sqrtf(DEG2RAD(x))`.** For a real root write `sqrt( x * 57.2957795 )`; do not fix the engine,
  scripts depend on the quirk. `cos`/`sin`/`atan` take and return degrees. bug-3383.
- **`wait 0.05` is every second server frame at sv_fps 40.** A script mover stepped that way judders against 40 Hz
  snapshots (half the client frames show no motion). Use `waitframe` and integrate `level.time` deltas. bug-3381.
- **A harness client is capped by `com_maxfpsUnfocused`** (harness_window adds 60), not only `com_maxfps`. bug-3384.
- **Above the sky, a down trace hits the sky brush's top face** (1856/1920 on m2l3) and a probe from just under the sky
  starts solid inside the boundary walls: both read as "obstacles" and refused every track. Clearance for a plane above
  the lowest sky = what a droptofloor probe from just under the sky finds; a solid start there is the boundary. bug-10425 (finair).
- **The default `traced` mask has no CONTENTS_FENCE**: chain-link fences are invisible to it. Placement traces use
  34155265 (SOLID|FENCE|PLAYERCLIP|VEHICLECLIP|BODY|...). bug-10422.
- **Script view angles never turn a manned turret**: `VehicleTurretGun::RemoteControl` integrates the raw usercmd angles
  and `SetViewAngles` only moves delta_angles; a usercmd angle back to exactly 0 is ignored too. Harness gunners use
  pad `@mouse` events (finair `mktrack.py`). bug-10421.
- **ProjectileGenerator_Gun rounds never registered a hit on a coop player** (point blank, coop_dmgProbe silent):
  use them for tracers/impacts only and deal damage in script. bug-10420.
