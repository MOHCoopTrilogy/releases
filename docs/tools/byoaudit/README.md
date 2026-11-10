# byoaudit - audits for converted own-disc maps

Re-runnable checks for a map the bring-your-own-disc converters build on the player's PC (Frontline `coop_fl_*`,
European Assault `coop_ea_*`). Everything here is our code. Everything it **reads** (the local pak) and **writes**
(logs, stills, top-down PNGs) contains converted disc content: keep it under `H:\hzm_work\...`, never in git, a
release, the updater or the public servers.

| tool | what it checks | how |
|---|---|---|
| `geoaudit.py` | walkability, invisible walls, crawl/crouch openings, floor holes, falls out of the world, grounding of placements, route blocks | offline, on the pak's BSP with the engine's own box-trace rules (`mapgeo.py`, numba) |
| `aiaudit.py` | AI that stand idle, never engage, cannot move, spawn in view; kills and engagements per side | private dedicated server + background clients, the map's `coop_aiaudit 1` log (`coop_mod/aiaudit.scr`) |
| `walkshots.py` | the mission walk: stills along the route for visual QA | one SP background client, noclip/tele/screenshot |
| `byoclient.py` | the launcher the two in-engine tools share | `harness_window.launch_background` only (test display by resolution, never focused, guard enforced, muted, no pad) |

## Running them

```
python geoaudit.py <local pk3> coop_fl_1_1 <outdir> --png
python aiaudit.py coop_fl_1_1 <outdir> faceoff                      # Allies vs Germans, no player
python aiaudit.py coop_fl_1_1 <outdir> mission --test 9 --minutes 30 # every trigger in mission order, then the objectives
python walkshots.py <local pk3> coop_fl_1_1 <outdir>
```

The in-engine tools need the private client folder (`BYO_CLIENT`, default `G:\mohaa-flpolish`: byte copies of an
engine build, `home\maintt`, `home2\maintt`, `srvhome\maintt` each holding the local converted pak plus the test pak
of changed mod scripts). While the user's own game runs they use the 1080p second screen (`BYO_TEST_RES`).

## Pointing them at European Assault (`coop_ea_1_11`)

- `geoaudit.py` is map-agnostic: it reads `maps/<map>.bsp` and `maps/<map>_data.scr` from the pak. The EA converter
  writes the same BSP layout (`docs/tools/ea/flbsp.py`). Pass `--data` if the data script has another name.
- `aiaudit.py --game ea` sets `coop_eatest` instead of `coop_fltest`. The EA map script needs the same three hooks
  as `maps/coop_fl_1_1.scr`: `coop_aiaudit 1` -> `thread coop_mod/aiaudit.scr::run`, `coop_mod/aiaudit.scr::add`
  on every actor it spawns, and test modes 8 (face-off) / 9 (route walk) if those measurements are wanted.
- `walkshots.py --points '^ea_(trig|pos|start)$' --order <expr>` with the EA data script's point names and the
  direction its route runs.

## What the numbers mean

- **walkable_cells**: 16u cells a crouching player reaches from the spawns. **pathnodes_unreachable**: the level's own
  AI path points (from the original's navpoints) the player cannot reach: progression blockers.
- **blocked_moves**: `visible` (a drawn wall), `invisible` (nothing drawn within 8u of the contact),
  `edge_of_world` (a clip at the end of the floor), `opening_blocked` (a drawn low opening that collision fills).
- **route_blocks**: two AI path points with an open drawn line between them that a crouching player cannot sweep.
- **void_falls**: steps that fall out of the world. **undrawn_floor_cells**: floor you stand on with nothing drawn.
- **must_crouch_cells**: reachable only crouched (crawl passages, low doorways).
