# Medal of Honor: Frontline (Xbox) - how the game stores a mission, and how we convert it

Reference for future bring-your-own-disc missions. Written 2026-11-11 after the SEALED ORDERS (level 1_1,
`coop_fl_1_1`) fix pass. It describes formats and behaviour; it contains no disc content. The per-mission record
(what matches the original, what does not, and why) is `docs/proposals/flpolish_2026-11-10/FIDELITY.md`.

Code: `docs/tools/frontline/` (converter), `docs/tools/byoaudit/` (test harness), mission script
`hzm-mohaa-coop-mod/maps/coop_fl_1_1.scr`. The European Assault converter in this folder (`docs/tools/ea/`) is a
sibling with a different engine generation; only the audit harness is shared.

Status words used below: **proven** = checked against the disc and seen working in a converted run;
**inferred** = fits every record seen on 1_1 but not tested against another level; **unknown** = not decoded.

## 1. Containers and file layout

| file | what it holds | reader | status |
|---|---|---|---|
| disc image (.iso, XDVDFS) | the file tree; never written to | `flcore.Disc` | proven |
| `level.viv` style archive per level | the level's files, incl. object meshes (.msh) | `flcore.Level` | proven |
| `<l>_ART.cpt` + per-cell `.cpt` (version 18) | textures and drawn geometry, streamed in cells | `flcore` | proven |
| `.cdb` (version 7) | collision triangles with a material word | `flcore.collision` | proven |
| `.bpd` (version 9) | placement: paths, navpoints, entity instances with behaviour chains | `flcore`, `flscene` | records proven, most behaviour words unknown |
| `.mvd` (version 2) | recorded motion of set pieces (vehicles, aircraft) | `flscene` | proven |
| `chars.bum` | objective, hint and subtitle text | `flpack` | proven |
| ScrBnk sound banks, music streams | dialogue cues, music | `flpack` (decoded by a locally built vgmstream) | proven |

The level is streamed in cells: there is no single world mesh, no BSP, no visibility data and no floor past the
edge of the playable area.

## 2. Drawn geometry

- `.cpt` header (u32 words): texture record tables (128-byte records: width, height, pixel offset, index into the
  base chunk's shared table) and a draw table of 20-byte records (node, texture record, geometry pointer).
- Geometry: 28-byte vertices (position, packed normal, BGRA colour, uv) and u16 triangle strips.
- All lighting is baked into the vertex colour. There are no lightmaps and no light entities.
- Windings are not consistent inside one mesh (terrain skirts, facades).
- Object meshes (.msh) for movable things (doors, vehicles, props) sit in the level archive and are placed by .bpd
  object records.

Conversion (`flconvert.py`, `flbsp.py`): 48 MOHAA units per metre; every draw becomes a vertex-lit
`MST_TRIANGLE_SOUP` surface in a version-19 BSP (one cluster, no vis lump, far plane and fog from
`fl_levels.json`). Shaders are written per texture: two-sided, `rgbGen vertex`, no lightmap. Output is
byte-deterministic (sorted iteration, fixed zip times).

Traps:
- **Handedness (bug-10965).** Frontline's world is right-handed with the same up axis the converter uses; an earlier
  build mirrored y to make a first route line up and shipped the whole town mirrored - lettering on signs read
  backwards and every recorded yaw was wrong. Decide handedness from data, not from a screenshot: `signhand.py`
  (work dir) measures the uv winding of lettered quads against their world winding. Current converter: no mirror.
- **Hairline gaps between cells** show the sky in MOHAA (`flseam.py` bridges them, only over walkable floor with
  nothing drawn below).
- **Nothing is drawn under or behind much of the town.** Looking through windows or holes shows the void. The
  converter adds a dark under-ground plane; interiors that the original never drew stay empty (see FIDELITY.md).
- **No floor past the edge** (`flcliff.py` adds out-of-reach clip walls where a walkable edge has nothing below).

Verification: `byoaudit/geoaudit.py` (walk flood from the spawn: walkable cells, void falls, undrawn floor cells,
blocked openings, floating/buried placements), `byoaudit/visaudit.py`, stills by `byoclient.py`.

## 3. Collision

- `.cdb` triangles carry a material word. Low 11 bits = material; high bits = flags (a "special surface" bit and a
  "volume" bit). Material 14 = trigger volumes, 15 = the river's water volume (**proven** on 1_1), material 3 with
  the special bit = a smooth player-only wrap around facades, props and trees (**proven**), other materials =
  footstep/impact classes (**inferred**, not mapped to MOHAA surface types yet).
- The Frontline player is smaller than MOHAA's: crouch about 49u, stand about 86u, body about 20u wide at our
  scale, against MOHAA 54u / 94u / 30u, and MOHAA steps only 18u.

Conversion: every collision triangle becomes a thin convex brush (6 axial bevels first - `CM_BoundBrush` needs
them). Then, all inside the converter:

| pass | what it does | why |
|---|---|---|
| `flsheets.py` | drops the invisible material-3 wrap, gives the drawn thing behind it its own collision; keeps a reviewed list (`clip_keep`) | "only blocked by what you can see" |
| `flfit.py` | shrinks tree/post blocker columns to what is drawn | invisible walls |
| `flclear.py` | carves crawl holes to 54u+ and doorways to 94u+, caps them | Frontline's smaller player |
| `flroutes.py` | keeps every original AI route open and wide enough for a 30u box | routes blocked by our own collision |
| `flcliff.py` | edge-of-world walls, parapets | no floor past the edge |
| riverbed + water volume | a bed 160u under the water surface and a `CONTENTS_WATER` volume above it | a player in the canal lands, is in water, then the script drowns him as the original's river kills |

Traps: two opposite windings in one floor (use centred prisms); a brush side duplicated on an axial plane deletes
the walk face (bug-10605); the audit numbers move in both directions when one pass changes, so always compare a
whole `geoaudit.json` before and after, not one counter.

## 4. Materials, alpha, glass, water

- Textures are small (32 to 256 px; 441 on 1_1) and stretched far: the main ground runs at about 8 world units per
  texel. `H:\hzm_work\flpolish\fix2\texinv.py` measures every texture (area, texel density, closest approach).
- Alpha has three uses, told apart from the pixels and the mesh: fully keyed cutouts (foliage, fences, ruined
  facades) -> `alphaFunc GE128` with depth write; soft alpha (shadow blobs, debris decals, grass fringes; more than
  10% partial pixels) -> `blendFunc blend`; **vertex alpha** (203 on 1_1) on flat meshes = water.
- Window glass: 1_1 has no separate glass material; windows are part of the facade texture or open holes.
  (**proven** for 1_1, **unknown** for other levels.)
- Water: mapped by shader name to `textures/misc_outside/pond`. On the gl2 renderer the mod's water pass
  (`r_hzmWater`, engine `hzm_waterwet.h`, POND preset: calm, dark green) takes it over; on gl1 the stock shader
  script is the look. Nothing disc-derived is used for water. `FL_WATER_SHADER` overrides the name.

Traps: foliage with antialiased edges must be cut out, not blended (blended leaves do not depth-sort); a soft decal
drawn as a cutout turns its pale fringe opaque.

## 5. Placement records (.bpd)

- Section 0: named paths. Section 1: navpoints (24 bytes: position, packed edge count, edge list) - the AI's walk
  graph. Section 3: entity instances, variable-length records with an inline behaviour chain.
- Section-3 record words (u32): [3] kind (1 trigger volume, 2 object, 3 actor, 10 projectile generator),
  [4..6] position, [7..10] rotation quaternion (w x y z), actor word [13] byte 1 = team (1 Allied, 2 Axis).
  Trigger size = high half of word [11], in decimetres.
- Actor class comes from the record's type hash; the converter keeps a short class name per placement
  (`level.fl_axis_cls`, `fl_ally_cls`) for logs only.

Status: kinds, positions, rotations, teams, trigger sizes **proven**. Health, weapon, accuracy, patrol/idle
animation, alert state fields: **unknown** - the converter gives every soldier MOHAA defaults scaled by the co-op
difficulty code.

## 6. Triggers, messages and sequences

Frontline has no text script per level. Behaviour is data: records send and answer numbered **messages**.

- Message ids are words in 65536..69999. An object or actor record lists the ids it ANSWERS to. A trigger record
  holds a count N, the N ids it SENDS, then an action pair whose code says when: 4 = player enters the volume,
  51/52 = proximity / line of sight, 42 = clean-up.
- An actor that answers to a message is **not in the world until that message is sent** (**proven**: on 1_1 every
  later area's soldiers answer to the id sent by the trigger at that area's entrance). Actors with no message are
  present from the level start. Placed corpses were not found on 1_1.
- Set pieces (jeep, aircraft passes, the tank) are objects answering to a message plus a `.mvd` motion: 32-byte
  frames at 30 per second (position, tag, quaternion); model forward is local -y.
- Projectile generators (kind 10) are the scripted shell/rocket sources.

Conversion: `flscene.py` writes only level variables into the generated data script (`maps/coop_fl_1_1_data.scr`):
per placement its group (the message id that wakes it), position, yaw, team; per trigger its position, radius and
the ids it sends; per set piece its motion frames. The committed mission script does the rest:

- a group is spawned when a live player enters its trigger (the `FLGRP start` block of the mission script), out of sight, grounded, with a path;
  nothing in a later area exists before that. Marker: `^~^~^ FLSET area <id> active count=<k> trigger=<n>`.
- every AI death is logged with cause, nearest player distance and whether a player could see it
  (`^~^~^ FLSET death ...`) - the audit that proves nothing dies off-screen.
- set pieces play their recorded motion by origin-stepping (`moveto` is a no-op on a `script_model`), with markers
  `^~^~^ FLSET seq <name> start|end at <time>`.

Unknown: the conditions inside behaviour chains beyond the action code (timers, counters, "all dead" tests), the
order two messages fire in when one trigger sends several, per-actor idle scripts and conversation groups.
Sequence timing in our script therefore follows the recorded motions and dialogue cue lengths, not a decoded
timeline.

## 7. Objectives, text, dialogue, music

- Objective and hint strings live in `chars.bum`; which message completes which objective is **inferred** from the
  trigger that sits at the objective's location (table in FIDELITY.md).
- `flpack.py` writes the strings, dialogue cue aliases with lengths, and music paths into the generated pak only.
  The mission script adds/completes objectives through the co-op objective API and prints
  `^~^~^ FLSET obj <n> state <status> at <time>`. HUD text and the objectives menu use the same string.

## 8. Ladders, mounted guns, doors, mines

- **Ladders: no ladder record or collision material was found on 1_1** (unknown how the original marks one).
  A ladder is only a drawn strip (1_1: material c4_feb00, 22 triangles, inside the bridge tower). Find them with
  a search for narrow, tall, vertical strips of one material, list each in `fl_levels.json` "ladders" (base at
  the climbing face, yaw the climber faces, height, exit point at the top) and the mission builds it with
  `coop_mod/ladder.scr`. That recipe dismounts forwards; where forwards is a wall (a hatch ladder) the mission
  sets the climber down at the exit point.
- **Mounted guns** are object records; the gunner is an actor placed beside it. The converter grounds the gun on
  the drawn surface under its record (a floating or buried gun means the mesh under it was not found; geoaudit
  lists them as placements_floating / buried).
- **Doors** are object meshes with their own motion; ours are script objects moved by the mission script.
- **Mines** are records in the hedge fields; ours fire once, cannot chain in the same frame, and leave a player
  downed rather than dead (bug-10967).

## 9. How a mission opens and ends

Original: a briefing film, then the level starts with scripted set pieces around the player; the level ends when
the last objective's message is sent, followed by the next level's load.

Ours: the co-op lobby/briefing, a title card on join (no team menu, no spectator camera), the Armory loadout
(decided deviation), then the same objective chain; the last objective calls the co-op mission-complete path
(`coop_mod/missioncomplete.scr`), never `bsptransition`.

Traps:
- An archived `timelimit` / `fraglimit` from an earlier deathmatch session ends a co-op campaign map on a timer
  (bug-10968; `coop_mod/server.scr::coop_noLimits` clears both on every coop_* map).
- A converted pak is identified by the worldspawn `map_time` key and `level.fl_conv`; the script refuses a pak
  from an older converter build with a visible message (bug-10966). A stale `.pth` next to the map in the home
  folder is rebuilt only when `map_time` changes (bug-10969).

## 10. Test method

`docs/tools/byoaudit/` against a private client folder (default `G:\mohaa-flpolish`), never the live install:

| tool | proves |
|---|---|
| `geoaudit.py` | geometry and collision counts (section 2 and 3) |
| `progwalk.py` | every trigger and objective spot is reachable on foot from the spawn |
| `aiaudit.py ... mission --clients 2 --test 9` | a full route walk on a dedicated server: every trigger, objective and sequence marker, the death audit, mission complete. Always two clients: the first joiner of the harness never spawns |
| `walkshots.py`, `byoclient.py` | stills at chosen spots |

A run is judged from the `^~^~^` marker order (expected order in FIDELITY.md), not from watching it.

## 11. Open unknowns (carry to the next mission)

1. Behaviour-chain words past the action code: timers, counters, group-dead conditions.
2. Actor attributes: health, weapon, accuracy, idle animation, alert state, patrol path binding.
3. How ladders and usable objects are marked.
4. Footstep/impact meaning of the collision materials other than 3, 14, 15.
5. Whether other levels carry lightmaps, glass materials, moving water or placed corpses - none on 1_1.
6. Which message completes which objective when no trigger sits at the objective's location.
7. The first-joiner spawn fault of the test harness (seen only with harness clients; a human join is checked
   separately).
