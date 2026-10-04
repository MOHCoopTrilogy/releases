# New art and real names for the coop mission tiles - APPLIED 2026-10-04 (committed, not deployed)

**Status 2026-10-04.** All 67 tiles (55 levels + 12 briefings) are built in both layouts, as cards and prints, from
`tools/tileset.py` (picks + provenance) and `tools/titles.json` (titles) by `tools/build_set.py`. Applied with
`apply/apply.py`: mod wiring (ui/coop_maps.inc, ui/coop_start.urc, ui/coop_start/*.cfg), art in
`docs/tools/assets/tileart/`, pak `zzzzzzzzzz_coop_tileart.pk3` from `docs/tools/gen_tileart_pak.py` (gated in
build.ps1, staged in publish_release.ps1). Fixes bug-3274 (logged as bug-3300).
- Batch C (BT + SH + AA retakes) was captured 2026-09-29. Retake C2 (ride release, `staging/retake2.json`) ran
  2026-10-04 and freed e1l4 and t2l2. **e3l4 and t3l2 are still provisional**: the player stays on the jeep MG / in
  the T-34, so those tiles are crops clear of the ride (bug-3301).
- In-engine proof of the wiring: `G:/mohaa-tileart/runs/r2_ui/ui_<cfg>_c{0,1}.tga`, every mission cfg in both
  `ui_menuCenter` layouts.
- Sheets: `set/sheets/progress_C.jpg` (batch C + re-picks), `set/sheets/final_{1,2,3}.jpg` (all 67).
- Independent review: PASS WITH NITS. Fixed: m2l3 (figures of unclear side), e1l1 (near-plane GI), Italy briefing
  exposure. Open nits: m3l1b shows the gun emplacement, not a bunker interior (the requested coastal-gun retake);
  m1l3b truck interior; m4l2 Tiger texture.

---


**Status 2026-09-29, round 2.** Round 1's samples failed an independent review (a floating Sherman, a German newsreel
frame labelled as GIs, an empty Berlin frame, a Tiger I under a King Tiger title, an unreadable kicker, and a 33%
horizontal stretch under the default menu layout). Round 1 is kept for the record in `superseded_round1/`.

Round 2: **7 samples are finished.**
- **Re-staged in the queued run:** 4, via `staging/tileart_run.py`, slot "tileart", 12:20-12:27. It took 6.2 min, the
  window report was clean, and the slot was written "free". The log is `staging/run.log`.
- **Offline:** 3.
- **Still failing QA:** t3l2 (see Samples).

Nothing in the mod tree, the engine, any live install or any repo was changed. Nothing was deployed.
There is one shared-tool edit: `docs/tools/harness_guard.py` registers the private install `G:\mohaa-tileart`,
the same way every other staging install is registered.

## What is wrong today (swept by `tools/inventory.py` -> `INVENTORY.md`)

- **67 tiles** in 13 dropdown missions: **55 levels + 12 briefings**.
- The art is old in-game screenshots from mixed eras: `textures/mohmenu/dmloading/*.jpg` (1024) and
  `ui/coop_tiles/*.jpg` (512).
- **bug-3274:** all six BT/SH briefing tiles show AA Mission 1's Operation Torch map.
- AA tiles carry no names. SH/BT tiles carry dev labels drawn across the middle of the picture, and several are
  wrong:
  - "t1l2 Verviers" and "t1l3 Malmedy" are Belgian towns, but t1 is Normandy;
  - "t3l2 Sub Pens" is wrong: t3l2 is Berlin.
- **Mission headers** ("A Storm in the Port", "The Bridge", "The Great Escape", "Operation Torch", "Operation
  Avalanche") are invented or historically wrong (bug-3280, bug-3284).
- **`coop_mapDescription`** swaps m6l3c/m6l3d (bug-3285).

## Method, and why

- **Pictures:** real game frames only, never generated.
  - Levels: an in-engine `screenshot` of the level's own place, and its own placed vehicles where it has them.
  - SH briefings: Spearhead's own retail slideshow stills (`mainta/pak1.pk3 textures/mohmenu/Slideshow/
    {Normandy,Bastogne,Berlin}/*.jpg`, 56 photographs at 500x375).
  - BT briefings: BT has no retail stills, and its 512x256 briefing films fail at tile size, so they are staged
    in-engine.
  - AA briefings: AA's own briefing slide art.
- **Finish:** `tools/tile_treat.py`, one parameter set for the whole series: a silver-gelatin print on war-room paper.
- **Title:** the level's real name in the card's lower margin, in Bahnschrift SemiBold Condensed (the face the
  facfont-20 HD atlas was rendered from).
- **Why not Blender or painting:**
  - Blender: there is no BSP importer, so it would show the right props on an invented set.
  - Painting: it can't stay consistent across 67 tiles and reads as filtered.
- **Why staged frames plus one finish:** it guarantees the real place, uniforms and vehicles. The loadart set proved
  this route.

**Correct in the default menu layout.** The user plays 1920x1080 with `ui_menuCenter 0`, the default stretch. It
scales x by W/640 and y by H/480, so at 16:9 the 100x100-unit tile shows at **4:3**, and the remaster's 164x123-unit
print shows at **16:9** (`uiwidget.cpp` SetVirtualScale). So every card and print exists twice:
- `_c`: authored square/4:3 for `ui_menuCenter 1`;
- `_s`: authored at its 16:9-stretched on-screen shape, then squeezed into the texture, so the engine's own stretch
  restores it.

`samples/qa/onscreen_1080p.jpg` shows each variant at its real on-screen size. `scalecvar` (the loadart route to a
uniform scale) was checked and rejected for tiles: it also rescales the tile's position, pulling the grid off the
rest of the stretched menu.
- **Wiring (corrected in round 3).** A twin widget set does not work. `globalwidgetcommand` reaches a widget through
  `UIWidget::PassEventToWidget`, which returns early for a disabled widget (`uiwidget.cpp:2574`). So a cfg can only
  update the set that is currently enabled, and a live Stretched/Centred switch would show stale tiles. The fix is
  mod-only and uses the mechanism loadart already proved in-engine (`linkcvartoshader`, bug-3251's pak):
  - The 11 `coop_startMapN` Buttons stay exactly as they are (same names, rects and click commands), with a
    transparent shader. They remain the click target and the hover.
  - Under each Button sit two Labels. One has `linkcvar "coop_tileArtN_c"` and `linkcvartoshader`, gated
    `enabledcvar "ui_menuCenter"`. The other has `linkcvar "coop_tileArtN_s"`, gated `enabledcvar "!ui_menuCenter"`.
  - Each mission cfg sets the cvars (`set coop_tileArt2_s textures/mohmenu/hzmtile/m1l1_s`) instead of widget
    shaders. Cvars are set whether or not a widget is enabled, and a linked Label re-reads its cvar every draw, so a
    live layout switch is correct at once.
  - An empty cvar means no shader (`cl_main.cpp:4311`), so unused slots stay blank. No engine change.
- **Sources narrower than the window** (the 4:3 retail stills in the 16:9 variants) print at their own shape, centred
  on the paper, instead of being cropped or stretched.

**Baked title, and the localization route.**
- The reviewer found that button titles are drawn through `Sys_LV_CL_ConvertString`, and that localization files
  (`global/localization*.txt`, all loaded at client start by `sys/win_localization.cpp`) are read by the TikiScript
  reader, which turns `\n` into a newline. So an engine-drawn two-line title looks possible.
- Today's measurement still stands: only 35 of 67 proposed names fit one facfont-20 line on a 100-unit tile
  (INVENTORY.md header, swept). A
  two-line facfont title would cover about 35% of the tile, and the tile keeps one font size.
- **Decision:**
  - today's grid: the title is **baked** into the card margin, generated from `tools/titles.json`;
  - war room: the print ships **caption-free** and its caption stays **engine-drawn**.
- **Tested in-engine in the staging run** (`samples/qa/ui_loctest_ingame.jpg`, from
  `G:\mohaa-tileart\runs\ui\ui_loctest.tga`; `G:\mohaa-tileart\home\maintt\qconsole.log` lines 642-645 show
  `global/localization_zz_tiletest.txt` loaded):
  - a key mapped to `"Secret Documents\nof the Kriegsmarine"` **draws as two crisp engine lines**;
  - a literal `\n` sent from a cfg draws as the characters `\n` and overflows the tile.
- **So the route is real**, at a cost:
  - it needs one localization entry per two-line title;
  - facfont-20 is fixed size, so two lines cover about a third of the tile;
  - white engine text straight on bright art (snow) needs a backing band.
- **It stays the alternative, not the default:** baked in today's grid (one texture, exact layout), engine-drawn in the
  war room.
- **Kicker line dropped.** It was about 4 px at 720p. Titles are one size across the grid: 104 px on the 1024 card
  (96 only where one line needs it; two lines at 92 or less). That is about 18 px tall at 1080p and 12 px at 720p.
  `samples/qa/titles_all_{s,c}_*` shows all 67.
- **Round-3 finish (one parameter change for the whole set).** The round-2 review found speckled foliage, edge halos,
  a glowing tent and a green cast. So:
  - clarity and sharpening are eased (0.30/0.35 to 0.20/0.20);
  - a highlight shoulder rolls whites off instead of clipping;
  - halation is lighter;
  - the kept scene colour is capped at 3.5%, so no card carries a cast;
  - the texture post-sharpen is halved.

## Samples (`samples/`)

| id | tile | picture | title | status |
|---|---|---|---|---|
| aa1_m1l2a | AA1 m1l2a (Lighting the Torch) | in-engine: the Arzew courtyard at night | The Rescue Mission | done |
| bt2_e1l3 | BT1 e1l3 | in-engine: the Moorish horseshoe gate | Bizerte Canal | done |
| brief_t2 | SH2 briefing (bug-3274) | retail SH Bastogne slideshow still E: the BASTOGNE town sign | Briefing | done |
| aa2_m5l2a | AA5 m5l2a | in-engine: the level's OWN King Tiger (`vehicles//kingtank.tik`, `playertank`, where the retail BSP places it), side-on | Destroyed Village | done |
| sh1_t2l1 | SH2 t2l1 | in-engine: the Bastogne road, no smoke-sprite emitters; GIs firing on German infantry advancing beside the Panzer IV | Panzer Attack | done |
| bt1_e1l1 | BT1 e1l1 | in-engine: the level's own disabled Sherman (thrown track on the sand) in the dust-hazed camp; no spawned props | Battle of Kasserine Pass I | done |
| brief_e2 | BT2 briefing (replaces the remaster's blank SICILY card) | in-engine: e2l1's own opening, glider troops braced beside a jeep inside the CG-4A | Briefing | done |
| sh2_t3l2 | SH3 t3l2 | both bridge cameras re-staged | The Last Stand | **failed QA again** |

**t3l2 failed again, and I am not presenting it.** The two spawned Soviet riflemen (loadart nodes 1127/1130) stand
fused into one shape and idle in every frame of both cameras, and the dust-sprite columns are back. Next pass: film
the level's OWN scripted bridge defence (objective 3), not spawned actors. Spearhead is still sampled twice (t2l1 and
the Bastogne briefing).

**Round-2 staging QA:**
- The m5l2a King Tiger has its Henschel turret, its "332" tactical number and its track links. The log's
  `Couldn't load vehicles/kingcannon.tik` is pre-existing (loadart logged `tigercannon.tik` too) and does not strip
  the model.
- The picture shows the level's King Tiger (the objective: escape with it) on the road at the village's edge; the
  village itself is not in frame. The title stays the level's retail name.
- **m5l2a, round 3:** re-cropped to y 1080, so the tracks, their contact with the road and the tank's shadow are in
  frame (round 2 cut through the wheels). The canopy's dither is the engine's own alpha-tested foliage (it looks the
  same in play); the eased finish no longer amplifies it.
- The e1l1 Sherman sits on the sand. The thin line above the tent is the level's own smoke wisp. The camouflage net
  is the level's alpha-tested net texture.
- e1l1 in coop opens on a truck ride, so every box stays above the truck's wheel.
- **t2l1, round 3:** re-picked to bs_y+0_02. Frame +12_07 lined a standing GI up with a corpse, which read as one
  merged shape. bs_y-12_07 (a nose-up Panzer that reads as lifted) and bs_y+0_05 (a screen blood splash) are also
  rejected. In +0_02 every figure stands clear of the others.
- brief_e2: the pilot frame was rejected, because his shoulder patch renders as an unreadable blob. The jeep's
  bumper serial is cropped out.
- The engine still printed "UnnamedSoldier#8240 has joined the Allies" at y ~58 despite `ui_gmbox 0`. Every box
  starts below it.

Files per sample:
- `full/<id>_card_{c,s}_1024.jpg`;
- `game/<id>_{c,s}.jpg`: 512, the shipped texture;
- `full/<id>_print_{c,s}_1024x768.jpg`.

Mocks (`mock/`), drawn by the remaster's offline `.urc` renderer, used read-only:
- `grid_{s,c}_before_after_{1920x1080,1280x720}.png`;
- `tiles_{s,c}_1to1_*`: the tile rows at real screen pixels;
- `warroom_mixed_{stretched,centred}.png`: the remaster's station-04 board, cropped below its mission slate, with
  sample prints and captions from `titles.json`. Slot 4 is left as the remaster's own print for comparison.
- `warroom_sicily_{stretched,centred}.png`: the remaster's own Sicily board with only its blank "SICILY /
  Breakthrough 2" card replaced by `brief_e2`.

QA (`qa/`): `crops.jpg` (all four boxes on each source), `onscreen_1080p.jpg`, `titles_all_*`, `sampling_*`.

**Round-2 QA on the finished three:**
- **bt2:** every box keeps x >= 650 and y <= 720. That keeps the eagle-marked retail crates and the vehicle hood out
  of all four variants; round 3 lowered it from 736, which let a sliver of the hood into the `_s` pair.
- **brief_e2:** its `_s` boxes start at x 520, so the wall's stain decal (which could read as handwriting) is out.
- **aa1:** the stretched print stops above the player's rifle (y <= 836). The balcony figure is a level model behind
  a see-through balustrade texture; it stays, as a nit.
- **brief_t2:** a sharp 500x375 retail photograph (three soldiers holding the "BASTOGNE" sign), cropped inside its
  burned-in vignette. Spearhead's own Bastogne slideshow, so American by its source.

## Titles

`INVENTORY.md` (generated) has all 67 tiles with today's image, today's label, the proposed title and its source,
plus the retail evidence per tile.
- **Rules:**
  - the retail worldspawn name wins;
  - a retail "Chapter - Part" name uses the part (the chapter is the mission header);
  - m6l1c keeps the mod's "Das Sturmgewehr" (retail has the article wrong);
  - m4l0 is "The Farmhouse", from its own script header ("FARM HOUSE") and objectives.
- **SH rule:** SH worldspawn is only the region, so the title is a retail checkpoint name from `global/savenames.scr`.
  The rule is a stated judgement, not a mechanical one: **the checkpoint that names the level's central fight or goal
  as its RETAIL objectives describe it (read from the retail `maps/<bsp>.scr` in the paks, never the mod's objective
  strings); if no checkpoint names it, the opening checkpoint.** Round 3 corrected three justification errors the
  review found: t1l3's final objective is 6; t1l2's only retail objective is "Locate and Destroy Artillery
  Emplacements"; t2l4 sets objective 1 by number only. No title changed. The per-level justification, quoting the
  retail objectives, is in `titles.json` and INVENTORY.md:
  - t1l1 The Rendezvous
  - t1l2 Lock and Load
  - t1l3 The Hunt Begins
  - t2l1 Panzer Attack
  - t2l2 Top of the Mountain
  - t2l3 Defend the Front
  - t2l4 A Quiet Little Town
  - t3l1 Welcome to Berlin
  - t3l2 The Last Stand
- **Mission names** match the menu remaster's chalk list exactly (bug-3280), as bare names:
  - AA: Lighting the Torch, Scuttling the U-529, Operation Overlord, Behind Enemy Lines, The Day of the Tiger,
    Return to Schmerzen;
  - BT: Tunisia, Sicily, Italy;
  - SH: Normandy, Bastogne, Berlin.
- AA 5 and AA 6 follow the retail chalk signs in `main/Pak6EnUk.pk3`, the English pak (other language editions may
  differ). Their briefing BSPs say "Day of the Tiger" and "The Return to Schmerzen".
- **Source tags:**
  - `retail-ws` only where the BSP has a message (asserted by the sweep);
  - the six SH/BT briefing BSPs have none, so they are tagged `retail-region`.

## Packaging and wiring (the full set, after approval)

- **Pak:** a separate small `zzzzzzzzzz_coop_tileart.pk3`, like loadart (bug-3251), from `docs/tools/gen_tileart_pak.py`.
  - Sources come from `docs/tools/assets/tileart/`.
  - Deterministic: sorted, ZIP_STORED, fixed stamp, with a `check` mode.
- **Members** (new names under `textures/mohmenu/hzmtile/`, so no `.dds`/`.tga` shadowing, TRAPS T6):
  - `<bsp>_c.jpg` and `<bsp>_s.jpg`: 512x512 cards;
  - `print_<bsp>_c.jpg` and `print_<bsp>_s.jpg`: 512x384 prints;
  - briefings named `briefing_<x>`;
  - about 67 x 4 x ~70 KB, roughly 19 MB.
- **Lint:** every cfg shader resolves to a member; 512x512 / 512x384 baseline JPEG; lowercase ASCII; no shader
  script defines an `hzmtile/*` name; every tile has a title.
- **cfgs:** 13 `ui/coop_start/*.cfg` files, generated from `inventory.json` + `titles.json`. Each sets both tile sets
  (bare image paths: `RE_RegisterShaderNoMip`, so no picmip). The engine title is set to `" "`. The same generator
  rewrites the dropdown labels and `coop_missionName`.
- **bug-3274:** slot 1 of e1-e3 and t1-t3 points at the campaign's own briefing card.
- **War room (coordinate with the remaster):**
  - the room uses `print_<bsp>_{c,s}` behind its own layout gate (`ui_menuCenter`), as its backdrops already do;
  - captions take their text from `titles.json`;
  - its blank "SICILY" card and the old loading-shot prints are replaced;
  - in its square-tile theme, its white mount doubles the card's paper, so that theme should drop the mount.
- **Separately:** `coop_mod/variables.scr` `coop_mapDescription` should be regenerated from the same table
  (bug-3285).

## Full-set estimate

1. **Staging:** the same rig, 48 levels, about 3 h of slot time in 3-4 quiet runs of 45-60 min each. The subjects
   are each level's placed vehicles and signature places, found from its BSP entity lump.
2. **Briefings:** 6 SH/AA from retail stills and slides, no slot needed; 3 BT staged within the runs above.
3. **Finish and QA:** offline, plus an independent review, about 1 day.
4. **Pak, generator and lint, plus a boot check in the private install:** about half a day.

## Files

- `tools/`:
  - `titles.json` (authored: titles, rules, per-level justifications);
  - `inventory.py`;
  - `fontfit.py`;
  - `tile_treat.py`;
  - `samples.py`;
  - `mock_grid.py`;
  - `qa_onscreen.py`, `qa_titles.py`, `qa_sampling.py`.
- `staging/tileart_run.py`: the queued capture run (`check` / `wait` / `run`). It reuses the loadart rig by import
  and writes `run.log` here.
- `sources/`: the raw frames plus `SOURCES.json` (provenance; retail stills are read straight from the paks).
- `superseded_round1/`: round 1's samples, mocks, QA and sources.
