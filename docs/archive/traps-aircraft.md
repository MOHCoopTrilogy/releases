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
