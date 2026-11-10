# flpolish - SEALED ORDERS (coop_fl_1_1) polish, 2026-11-10

User playtest: snags, the jeep scene missing, open floors, broken tree billboards, idle AI / AI that never fight,
floating props, invisible walls blocking progression, crawl holes you cannot crouch through. Everything here is
our code; converted output, stills and logs stay under `H:\hzm_work\flpolish` (never committed).

## Root causes (converter: docs/tools/frontline)

| symptom | cause | fix |
|---|---|---|
| invisible walls blocking progression | .cdb flag bit 22 + material 14 = 450u trigger volumes, converted solid | `flconvert.coll_is_volume` drops them (and from placement grid / vis occluders) |
| crawl holes need prone | FL crouch ~49u vs MOHAA 54u; doorways ~86u vs 94u | `flclear.py` headroom carving, passage + inside-wall filters, nodraw caps |
| snag on trees / posts | special-surface columns fatter than the drawn trunk, some with nothing drawn | `flfit.py` fits each column to the drawn geometry |
| see-through trees | soft-edged canopy textures drawn blended | foliage cutout rule in `tex_shader` |
| open floors / underside | floors end at cell edges with nothing beyond | `flcliff.py` clip + drawn skirt + ground under the level |
| jeep scene missing | static jeep only | `flscene.py` decodes the .mvd keys (mirrored quaternion handedness) -> `fl_jeep_run` |
| AI idle / not fighting | all 75 placements spawned at load; 4 Allied roamers made German by class name | record team byte, trigger groups (`flscene.trigger`), out-of-sight spawns, ally squad follow |
| untextured draws tinted blue | fallback texture (40,70,90) | white: vertex colour only |
| missing ammo, MG nests, dead GI | never ported | `fl_ammo`, `fl_mg_yaw/broken`, DeadGuy |

Record layout notes are in `flscene.py`; the .cdb flag word in `flcore.collision` / `flconvert.COLL_*`.

## Open

- **bug-flp-jeepdraw (engine follow-up):** a script_model whose per-frame origin stepping STARTS east of x 8192 on
  coop_fl_1_1 is never drawn for the whole run (alwaysdraw, r_novis and +broadcast do not help); started at x 8150
  it draws. Worked around with `fl_levels.json` `motion_first`. Bound children of a moving script_model were also
  never drawn (riders are stepped instead).
- Fidelity gaps: see FIDELITY.md (tank path, patrol walkers, 6 air passes, bombs, rockets, door, barks, U-boat).
- 19-34u lips (Frontline steps over them) and 20-30u gaps (Frontline's narrower body) still snag: ramp pass exists
  (`flclear.ledge_ramps`, off: it let the walker onto wall tops), width pass not written.

## Audits (docs/tools/byoaudit) - re-run with the commands in its README
