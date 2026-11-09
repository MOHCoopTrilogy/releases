# Frontline campaign → HZM coop: feasibility study (2026-11-08)

**Status:** this is a study only. No mod or engine file was changed, and nothing was released.
**Source:** the user's own `H:\Medal of Honor - Frontline (USA).zip` (Xbox). It was read-only
throughout. Extracted data lives only under `H:\hzm_work\frontline_study\`.
**Scope (user, binding):**
- **Route:** bring your own ISO. The converter runs on the player's PC.
- **What we port:** maps, mission scripts, objectives, dialogue, music and ambient SFX.
- **What we keep:** our own weapons, Armory, HUD, AI and coop systems.
- **Fidelity:** close enough is fine; it does not need to be 1:1.

## Verdict

**Feasible.** The hardest part is already proven to be readable.

From the Xbox disc, our own stdlib-Python code, written today, reads:
- the disc filesystem;
- every archive;
- the level render geometry, with baked vertex lighting and UVs, in world space;
- the level collision mesh;
- the prop meshes;
- the objective strings;
- the dialogue subtitles, in EN/FR/ES/IT.

Audio uses EA formats that vgmstream (ISC licence) already decodes.

Two things are not solved yet:
1. **How level meshes bind to their textures.**
2. **Where the entities are placed** (the `.bpd`).

Both are bounded reverse-engineering jobs, and they are the go/no-go items for the proof of
concept.

**The build path:** our own generator writes a MOHAA BSP (v19).
- Render geometry becomes vertex-lit triangle-soup surfaces.
- Collision becomes brushes.
- The HZM engine builds the bot navmesh from those brushes at load.
- AI pathnodes are generated from it.

Mission logic is not decompiled. Each level is rebuilt in MOHAA script, on our coop objective, feed
and voice systems, using the extracted strings and audio.

**Rough effort:** 55–80 person-weeks for the whole campaign. A pilot level is about 8–11 weeks
including the proof of concept. **Go/no-go comes after the pilot.**

> ⚠ **Found while doing this, needs a decision.** Frontline music is already in **public releases**.
> - `zzzzzzzzzzzzz_coop_music.pk3` is listed in `manifests/latest.json` and uploaded to GitHub
>   Releases (v1.10.61).
> - FEATURES.md calls it the "MOH Frontline PS3 asset extraction": 339 music cues and 175
>   ambience beds.
> - The files are gitignored, so they are not in git, but they are in the release.
>
> That contradicts the BYO rule "never in a release". Option: move it behind the same converter
> (the Xbox disc carries the score as `main.mus` + `.mpf` for each level).

---

## 1. Disc contents

| Fact | Value |
|---|---|
| Image | `Medal of Honor - Frontline (USA).iso`, 7,825,162,240 bytes, a full Redump image (video partition + game partition) |
| Hashes | SHA1 `C5F234B9…C4C6`, MD5 `04201181…A1EC`, CRC `435DD983`. All three **match Redump Xbox USA** (libretro-database mirror) |
| Game partition | XDVDFS at offset `0x18300000` (XGD1) |
| Executable | `DEFAULT.XBE`. Title ID `0x4541001A` ("Medal Of Honor Frontline"), region 1, version 1 |
| Size | 563 files on disc, 3.18 GB of data, and **10,845 files inside the VIV archives** (see `inventory.tsv` / `inventory.json`) |

None of the archive members is RefPack-compressed, so no decompressor is needed.

### Layout

- `DATA/<m>/<m_l>/`: one folder per level.
  - `level.viv`: a BIGF archive of 300–400 members.
  - `comp.viv`: a C0FB archive holding the streamed cells `*_ART_cN.cpt` and `*_C_cN.cdb`.
  - Audio: `main.mus`, `<ml>{Gun,Imp,Mov,Scr,Str,Veh,Voc,LoadN}Bnk.abk`, `<ml>StrBnk.ast`, and
    `<ml>M.mpf` (Xbox MP maps only).
- `DATA/7/7_1..7_8`: the Xbox-only split-screen deathmatch maps.
- `DATA/MOVIES/*.mpc`: 24 files, 1.09 GB. EA MPC, which is an MPEG-2 elementary stream: briefings,
  history films, extras, intro.
- `DATA/SHELL`: the menus.
  - `n_n_bLog.viv`: briefing journal pages as `.xsh` images.
  - `Shell1.asf`: the menu music.
- `DATA/LOADING/*.xsh`: the loading screens.
- `DATA/chars.bum`: the **English UI and objective string table**.

**Folder numbering is not story order.** D-Day was added late in production, so it lives in folder 6.

| Disc folder | Story mission | Levels |
|---|---|---|
| 6 | M1 D-Day | 6_1 Your Finest Hour, 6_2 Into the Breach |
| 1 | M2 A Storm in the Port (Lorient) | 1_1 Seaside Stowaway, 1_2 Special Cargo (inside U-4902), 1_3 Eye of the Storm, 1_4 A Chance Meeting |
| 2 | M3 Needle in a Haystack (Holland) | 2_1 Rough Landing, 2_2 The Golden Lion, 2_3 Operation Repunzel |
| 3 | M4 Several Bridges Too Far | 3_1 Nijmegen Bridge, 3_2 Yard by Yard, 3_3 Arnhem Knights |
| 4 | M5 Rolling Thunder (Emmerich) | 4_1 On Track, 4_2 Riding Out the Storm, 4_3 Derailed! |
| 5 | M6 The Horten's Nest (Gotha) | 5_1 Clipping Their Wings, 5_2 Enemy Mine, 5_3 Under the Radar, 5_4 Stealing the Show |

That is 19 campaign levels. The folder-to-level mapping was confirmed from each level's set-piece
names (`dday_higginsboat*` in 6_1, `Periscope_1_2`, `5_4_HOIX_Flying`, and so on). Each level is
53–128 MB on disc.

### Formats

**Status** says how far each format can be read today:
- **decoded**: our code reads it and the output was checked.
- **partly**: the structure is understood but not all of it is decoded.
- **documented**: a community document or tool covers it.
- **not needed**: out of scope for the port.
- **undocumented**: nobody has documented it yet.

| Ext | Magic | Count / bytes | What it is | Status |
|---|---|---|---|---|
| `.viv` (BIGF) | `BIGF` | 72 on disc | EA BIG archive: BE count and header size, then `{BE off, BE size, name}` | **decoded** (`tools/viv.py`) |
| `.viv` (C0FB) | `C0FB` | — | Small EA BIG: 24-bit BE offset and size | **decoded** |
| `.cpt` | ver 18 | 247 / 296 MB | **Level render art**, per streamed cell plus one base chunk. Mesh descriptor `{u32 vb, u32 ib, u16 nv, u16 ni}`. 28-byte vertex: `xyz f32`, packed normal, **BGRA baked colour**, `uv f32`. u16 triangle strips. World space, metres, Z up | **geometry decoded** (`tools/cpt2obj.py`). Material/texture binding still open; the header carries a table of `(count, offset)` sections |
| `.cdb` | ver 7 | 247 / 75 MB | **Collision mesh** per cell. `f32[3]` vertices, then 16-byte triangles `{3 vertex byte offsets, f32}`, then plane and tree sections | **triangles decoded** (`tools/cdb2obj.py`). 1_1: 31,567 tris, 0 rejected |
| `.psp` | `PBSP` | 27 | One per level. An axis-split BSP (`PBSP_HEADER`, split planes in metres). Probably the sector/visibility or AI-region tree | undocumented, optional |
| `.bpd` | ver 9 | 27 / 18.8 MB | One per level. About 100 `(count, offset)` sections, e.g. 1364 and 543 entries. **Probably entity instances and navpoints** | undocumented. **PoC target** |
| `.lfc` | — | 27 | Level class table: 290 behaviour classes (`RemoteFakeDoorTrigger`, `Navpoint`, `MObjective_1_1`…) | names readable |
| `.cbs` / `.sin` | `BSSCRIPTFILETAG` | 2102 + 2102 | Compiled behaviour scripts for an EA bytecode VM, one class each. Examples: `SoldierA_Guard`, `SoldierA_MachineGunNest`, `SoldierB_Roamer`, `Conversation`, `MObjective_1_1`, `PathFinderTrigger`, `LandMineTriggerParent` | undocumented VM. **We do not decompile it**; we read the class names as a cue sheet |
| `.mvd` | `MVD` | 186 | Motion paths for set pieces: P-47 flybys, cranes, Higgins boats, train, HO-IX | undocumented, optional |
| `.msh` | `0b000000` | 1918 / 98 MB | Static prop meshes. Same vertex and descriptor layout as `.cpt` (ResHax thread) | **decoded** with the same exporter (1_1: 226 meshes) |
| `.dmf` / `.skl` / `.mpk` | `DMF`, `1LKS` | 619 / 254 / 47 | Skinned characters (e.g. `UHM1_1.dmf`), weapon viewmodels, skeletons, swap packs | not needed for this scope (stand-in models) |
| `.emt` | `EMT\0` | 27 / 98 MB | **Level texture pack**: unnamed, indexed by ID | header readable; payload: probably Xbox DXT/swizzle like `.xsh` |
| `.tpk` | `TPAC` | 27 / 56 MB | Character texture pack, named (`BT01`, `US1`, `GM01GT01`…) | readable, not needed |
| `.xsh` | `SHPX` | 2294 + 31 | EA "shape" textures, Xbox flavour: DXT1/DXT3/8-bit palette/BGRA, some Morton-swizzled | documented (EA-Graphics-Manager GPL-3; ResHax Noesis script) |
| `.xfn` | `FNTX` | 236 | Fonts | not needed |
| `.abk` | `AB\x09\0` | 351 / 173 MB | EA AudioBank (BNKl inside). `ScrBnk` = **scripted dialogue, with the subtitle text embedded** in EN/FR/ES/IT. `VocBnk` = AI chatter. `Gun`/`Imp` = weapons/impacts. `Mov`/`Veh` = foley/vehicles. `LoadN` = random-variant banks | vgmstream `ea_schl_abk` |
| `.ast` | `SCHl` | 27 / 665 MB | Streamed sound bank that goes with `StrBnk.abk` (ambience and long cues) | vgmstream |
| `.mus` + `.mpf` | `SCHl` / `xDFP` | 27 / 186 MB | **Interactive music**: segments plus a PathFinder map. Stereo, 22,050 Hz | vgmstream `ea_schl_map_mpf_mus` |
| `.asf` | `SCHl` | 1 | Menu music | vgmstream |
| `.mpc` | `MPCh` | 24 / 1.09 GB | Movies (MPEG-2) | documented (MultimediaWiki). Optional |
| `chars.bum` | — | 1 | String table: every **objective / objective-complete / prompt** string ("Secure Submarine Fueling Roster", "Defuse Charges under Bridge"…) | **readable** |

**Community sources:**
- [StenApp, MOHF VIV archive and audio tools](https://github.com/StenApp/Medal-of-Honor-Frontline---VIV-Archiv): Python, no licence stated, so we only read it.
- [ResHax "[PS2] Medal of Honor: Frontline"](https://reshax.com/topic/18753-ps2-medal-of-honor-frontline/): `.msh` layout and `.xsh` codes. Notes that the Xbox version is easier than PS2, which needs VIF unpacking.
- [EA-Graphics-Manager](https://github.com/bartlomiejduda/EA-Graphics-Manager): GPL-3.
- [vgmstream](https://github.com/vgmstream/vgmstream): ISC.
- [MultimediaWiki, EA formats](https://wiki.multimedia.cx/index.php/Electronic_Arts_Formats).
- ZenHAX/Xentax SSH threads (Xentax is offline; use archive copies).

Nobody has documented `.cpt`/`.cdb`/`.bpd`/`.psp`. The `.cpt` and `.cdb` findings above are new.

**Evidence images (local only, never committed):**
- `H:\hzm_work\frontline_study\out\1_1_all.png`: Seaside Stowaway, all 8 cells, 116,493 tris. The
  town, the canal and its bridge, the trees and the backdrop all assemble in world space with no
  per-chunk transform.
- `H:\hzm_work\frontline_study\out\1_1_col.png`: the same level's collision footprint.

The level measures about 486 × 348 m, with Z from −12 to +16 m.

## 2. Extraction and conversion per asset type

### 2a. Level geometry → playable MOHAA map. This is the core of the job.

**Recommended route: our own BSP writer, a Python tool that emits MOHAA BSP v19.**
- It needs no third-party compiler, so it can run on the player's PC.
- It keeps Frontline's baked lighting.
- Its spec is `openmohaa-hzm/code/qcommon/qfiles.h` (lumps 0–25) plus `tr_bsp.c` / `cm_load.c`.

| Piece | How it is built |
|---|---|
| **Render** | Every `.cpt` mesh becomes an `MST_TRIANGLE_SOUP` surface with lightmap −1. The FL BGRA vertex colour becomes the vertex colour, with shaders using `rgbGen vertex`. The result looks like Frontline's own lighting and needs **no light compile**. Scale is metres × ~52 (calibrate in the pilot against MOHAA door and player height). Recentre to the origin; 1_1 becomes about 25k × 18k units |
| **Collision** | Every `.cdb` triangle, after merging coplanar neighbours (the `.cdb` plane table already groups them; 5.2k planes for 5.9k tris in cell 0), becomes a thin convex brush: the face plane, a back plane about 4 units behind, and the edge planes. That is about 25–30k brushes per level, bucketed into a kd-tree of nodes and leafs. MOHAA collides only against brushes, patches and terrain, never against render soup, so this step is required |
| **Bot navigation** | Free. `navigation_bsp.cpp` triangulates brush windings into Recast at load. A solo build that fails falls back to a tiled build automatically, and `nav_dump 1` lets us check it. A failed build is now caught, not silent (ENGINE.md, the e3l2 zero-poly lesson) |
| **AI pathnodes** | Actors still use the classic `info_pathnode` graph. Generate the nodes into the entity lump: first try FL's own `Navpoint` instances (once the `.bpd` is decoded), and fall back to sampling the engine's navmesh polys (the `docs/tools/nav_*.py` / `gen_navheat.py` family already analyse it). Cover nodes are needed for `THINK_COVER` (FEATURES: "coop maps lack cover PathNodes") |
| **Visibility** | No PVS: one cluster, everything visible. About 120k tris per level is trivial for gl2. FL's `.psp` BSP could feed portals later if fps needs it |
| **Light grid** | Sample FL vertex colours into the `LIGHTGRID*` lumps so actors and static models are lit to match. A flat ambient grid is acceptable for the pilot |
| **Doors and movers** | FL doors are entities (`DoorSwingCW` + `Door_square_1_1.msh`), not world geometry. Emit them as `script_model` / `func_rotatingdoor` with a clip brush model. Breakable walls (`M1_1_WallExplosion`, `FallingWall*_3_3`) become our usual swap recipe |
| **Sky / water** | FL backdrop meshes are in the `.cpt` and can stay as geometry. Water surfaces get a coop shader. The repo's TRAPS on sky, water and fog apply |

**Fallback route:**
1. Write a `.map` (collision brushes plus render geometry as models).
2. Compile it with EA's MOHAA `q3map` from the MOHRadiant SDK.

This was **not used**:
- It is a closed, third-party exe, so it needs the user's OK.
- It could not be redistributed to players.
- It would re-light the level, losing the FL look and taking hours per map.

I found no open-source compiler confirmed to emit MOHAA BSP v19–21.

**Quality to expect:**
- Render fidelity is high: it is FL's own mesh and lighting.
- Collision is as good as FL's, because it is FL's own collision mesh.
- Portals and vis are absent until needed.

The risks are:
- brush count and load time;
- Recast build time on big levels (6_1 Omaha);
- sloped thin-brush seams that snag players. Mitigation: merge coplanar triangles, and give
  walkable faces thicker brushes.

### 2b. Textures

**Level textures (`.emt`):**
- The payload is not decoded yet, but the `.xsh` family suggests DXT1/DXT3/P8/BGRA with Morton
  swizzle.
- Write our own decoder (documented codes, about 200 lines), or port the GPL-3 EA-Graphics-Manager
  logic. A port would make that file GPL-3, which is compatible with the GPL engine.
- **Open question:** how a `.cpt` mesh selects its `.emt` texture ID. It is probably in the
  `(count, offset)` section table at the chunk head. This is **PoC go/no-go item #1**.
- Output: DXT payloads can go straight to `.dds` (`renderergl1/tr_image.c` loads DDS); otherwise
  `.tga`.

**Props (`.msh`) → static TIKI:**
- OBJ export already works.
- The repo's `md5_2_skX` (`openmohaa-hzm*/code/tools/md5_2_skX/`, with `writeobj.c` and
  `writetiki.c`) plus `skd_add_collapse.py` gives the `.skd`/`.tik` path, so the remaining step is
  OBJ → MD5mesh.
- Only props the missions need: objective items, crates, phones, U-boat parts.

**Characters:** use stand-ins from MOHAA/SH/BT (Wehrmacht, US paratroopers, British airborne from
Spearhead's Varsity mission). Frontline `.dmf` skinned models are out of scope.

### 2c. Audio and music

**Decoding.** vgmstream (ISC) decodes every audio container on the disc. Two ways to use it:
- Vendor its C source into our converter (licence-clean).
- Write our own EA-XA / Xbox-IMA decoder (documented, about 300 lines).

Do **not** use `sx.exe`: it is EA's own closed tool.

Audio comes out as WAV.

**Music** (`main.mus` + `.mpf` for each level):
- Split it into segments.
- It plays through the **only live music path, `tmstart`/`tmstartloop`**. The mood/`.mus` system is
  stubbed in this build; see `docs/archive/legacy-root-2026-06/frontline_soundtrack_mapping.md`.
- Map the mood segments (ambient / action / victory) to objective and alarm events.

**Dialogue** (`ScrBnk.abk`):
- Each cue carries its **subtitle strings in EN/FR/ES/IT**.
- Emit `ubersound` aliases with `subtitle` text, played via `say` / `playsound` on stand-in NPCs, or
  as radio lines.
- Our `feed.scr::feed_all` / `feed_player` carries the text for coop: every player sees every line.
  This is the recipe `maps/m2l1.scr` already uses: the alias carries the subtitle, `g_subtitle`
  defaults to 0, and the transcript goes to the feed.
- The cue → line order has to be authored once per level, from the bank order plus a longplay
  reference.

**Other sounds:**
- `VocBnk` (AI barks): optional. `aivoice.scr` already does situational AI voice with MOHAA
  assets.
- `StrBnk.ast` and `MovBnk`: ambience beds and level SFX (bells, engines, sea). Convert the beds
  the levels use.
- `Gun`/`Imp`/`Veh` banks: **not needed**, because we keep our own weapons. Exception: vehicle loops
  for scripted set pieces.

### 2d. Mission scripting

The FL logic is compiled `BSSC` bytecode, one class per behaviour, on an undocumented VM. It is **not
worth decompiling**. Instead, **each level is rebuilt by hand in MOHAA script** from four inputs:
1. **Objective text**, verbatim from `chars.bum`, into our objective API (`global/objectives.scr::add_objectives` + `coop_mod/objectives.scr`, HUD = menu rule).
2. **Behaviour class names** from each level's `.lfc`/`.cbs` list, used as a cue sheet. For 1_1:
   - `SoldierA_Guard`/`Roamer`/`StayOnPath`/`MachineGunNest`/`Platform`
   - `MountedMachineGun`, `TankVehicle`
   - `M1_1_ResistanceDrop`, `M1_1_Field_Phone`, `MObjective_1_1`, `Conversation`
   - `InterrogationOfficer`/`Victim`
   - `LandMineTriggerParent`, `ExplodingBarrelSwap_1_1`, `FlyThrough_1_1`, `Soldier_SayIncoming`

   These map onto MOHAA actor types and our recipes. Per CLAUDE.md, find the working recipe first.
3. **Entity placements** from the `.bpd` (once decoded): enemy spawns, objective items, triggers,
   navpoints. Until then, place them by hand from the geometry plus a longplay.
4. **Dialogue cues** from `ScrBnk`.

**Coop layer** (shared across all levels):
- `coop_mod/main.scr::main` first;
- spawnlocations (respawn points advance with the objectives);
- `aihandler` scaling by player count;
- `missioncomplete.scr` chaining 6_1 → 6_2 → 1_1 … → 5_4;
- map tiles and briefing slides (the `bLog` journal pages can be the briefing images, via
  `menumirror.scr`);
- `maptest` coverage.

## 3. The missions

Below are the objectives from `chars.bum`, the set pieces from the `.mvd`/`.cbs` names, and the hard
coop beats.

| Level | Objectives and beats | Set pieces / hard parts | Reuse instead of converting |
|---|---|---|---|
| **6_1 Your Finest Hour** | Rescue Sgt. Kelso's men, regroup at the shingle, rescue the engineer, minefield, man the MG, MG nests on the ridge, clear the trench | Higgins-boat intro (8 boats), C-47 crash, camera cuts | **MOHAA m3l1 Omaha**: its landing intro, artillery and beach systems. The FL geometry is still worth converting (different terrain) |
| **6_2 Into the Breach** | MG bunker, radio link, smoke grenades, both gun decks | Bunker; scripted Allied/Axis air groups | m3l1/m3l2 bunker recipes |
| **1_1 Seaside Stowaway** | Resistance drop, church-tower MG over the bridge, fueling roster, find the dock, breach the dock wall, stow away in a crate | P-47 flybys and strafes, Panzer IV, jeep, interrogation scene | Ending crate becomes a trigger, then a fade, then the next map |
| **1_2 Special Cargo** | Inside U-4902: engines, aft/fore torpedo charges, radio, Enigma codebook, escape the hatch | Crate camera, engine pistons, periscope | **MOHAA mission 2 (U-529, maps m2l1–m2l3; check which holds the sub interior)** props and sounds |
| **1_3 Eye of the Storm** | Resistance cache, rooftop hatch at pen 2, supply trucks, deployment roster, wet docks | U-boat scuttle, bridge truck | MOHAA sub-pen props |
| **1_4 A Chance Meeting** | Engine research, blueprints, destroy all U-boats, fuel depot, dock gates | **Sturmgeist** camera, cranes, torpedo drop, seaplane | — |
| **2_1 Rough Landing** | Protect Cpl. **Barnes** (escort) while tanks, windmills and the Nebelwerfer are destroyed; kerosene; burn the haystack to open the gates | AA guns, P-38 | Escort recipe (`allysquad.scr`) |
| **2_2 The Golden Lion** | Sabotage the motor pool, check-point alarms, operative at the garage, truck ride, uniform, bar contact | Truck path, pub | **Disguise**: `changeGameType` papers recipe. The truck ride uses an existing vehicle-ride recipe |
| **2_3 Operation Repunzel** | Manor in disguise, keys, map behind a painting, cuckoo-clock documents, free **Gerritt**, jump into the hay truck | Cuckoo clock, desk flips | Disguise recipe |
| **3_1 Nijmegen Bridge** | Defuse 4 charges, sabotage the detonator in the fort, AA gun, escape in the medical truck | AA guns, E-boat, P-38 crash | — |
| **3_2 Yard by Yard** | Destroy the road blocks/checkpoints (gas cylinders, MGs), light tank, radio, escort the truck to town | Only 2 set pieces | **Simplest scripting on the disc** |
| **3_3 Arnhem Knights** | With British 1st Airborne: Panzer IVs, Panzerschreck squad, meet **Jigs** | 16 falling walls, tank walls, rocket | Spearhead British airborne models |
| **4_1 On Track** | Officer uniform and papers at the hotel, station controls, board the train | Sturmgeist's convertible, train | Disguise |
| **4_2 Riding Out the Storm** | Car-to-car on the train, radio, Sturmgeist's briefcase | **Moving train**: fake it with scrolling scenery, a static train and a skybox | Hardest beat for coop |
| **4_3 Derailed!** | Rail-yard charges, align the turntable, crash an engine, 2 fuel depots | — | — |
| **5_1 Clipping Their Wings** | Stash, photograph 5 blueprints, HO-IX plans, wind tunnel, foundry, test engine | Wind-tunnel plane, flying papers | — |
| **5_2 Enemy Mine** | Minecart ride to radar | **Minecart ride** (`5_2PlayerCart`) | Ride recipe; coop = all players in one cart |
| **5_3 Under the Radar** | Charges, 2 radar stations, radio position, find the hangar | — | — |
| **5_4 Stealing the Show** | Kill **Sturmgeist**, HO-IX escape while bombers destroy the facility | P-38s, roof chunks, bombers, HO-IX flight | End with a cutscene camera (`aircraft.scr` recipes) |

Characters who matter:
- **Sturmgeist**: the villain in 1_4, 4_1, 4_2 and 5_4, and a boss fight. He is worth a distinct
  model or skin.
- **Barnes**: escorted in 2_1.
- **Gerritt**: rescued in 2_3.
- **Jigs**: met in 3_3.

The rest (resistance, the Kelso squad, Manon/Delacroix on the radio) can be stand-ins or voice only.

**Not converting:**
- the 8 Xbox MP maps (`7_x`), which could become MP arenas later;
- the movies (optional; the briefings use the bLog pages).

## 4. The BYO converter

**1. Where it lives.** An optional "Frontline campaign" component in the installer and auto-updater
(`installer/hzm_coop.iss`, the engine `autoupdater`). It asks "Locate your Frontline disc image",
which can be an `.iso`, a `.zip` containing one, or a bare XISO, and remembers the path.

**2. Verifying the disc.** There are two tiers:
- *Fast check:* read `DEFAULT.XBE` through our XDVDFS reader, check title ID `0x4541001A`, then
  check the SHA1 of the XBE plus about 40 key files against a table shipped with the converter.
  Hashes are not assets.
- *Full check (optional):* the whole-image SHA1 against the Redump table. USA
  `C5F234B91005A0F342ACEB20F91C7BA682C3C4C6` is verified here. EU/DE/FR/IT/Asia values are in the
  research notes but still to be verified.

A disc that fails gets a clear message and nothing is written.

**3. Conversion.**
- Everything is local and deterministic: sorted entries, fixed mtimes, the same rule as bug-237.
- It reads the image in place, so no extraction is needed; a zip needs one streamed pass to temp.
- Output is `home/maintt/zzzz_coop_fl_<level>.pk3` (BSP, textures, sounds, aliases) plus
  `zzzz_coop_fl_music.pk3`.
- **Our** mission `.scr` files ship normally in the code pak. They are ours, and they reference
  the generated paths.

**4. Why determinism matters.**
- The server and clients must load **byte-identical BSPs** (pure/pak checksums), so the converter
  must produce identical output for every owner of the same disc.
- PAL discs must normalise to the same bytes, or be supported as a separate variant.
- **Dedicated servers need the converted paks too, so the server operator must also own a disc.**
  The `public_servers/` hosts are the user's own.

**5. Updates.**
- The manifest gets a `converter_version` and a list of generated paks with their expected sha256
  per supported disc.
- When the converter version changes, the updater re-runs the conversion from the remembered path,
  or asks again.
- A normal mod update that only touches our scripts needs no re-conversion.

**6. Packaging.**
- Players have no Python, so ship the converter as either an embedded Python runtime (PSF licence)
  plus our scripts, or a C tool built beside `md5_2_skX`.
- Either way, no third-party closed exe.

**7. Disk space.**
- Input is 7.8 GB, plus 7.8 GB of temp if it comes from a zip.
- Output is about **2–4 GB**:
  - BSPs: 19 × 15–30 MB;
  - textures: about 0.3–1 GB as DDS;
  - audio as WAV: 1 GB of ADPCM inflates about 4×, so convert only the banks used and keep
    dialogue mono at 22 kHz.

  Plan for 12 GB free at peak.

**8. Other disc variants.**
- **Xbox PAL** (EU/DE/FR/IT) probably has the same data with different languages. Diff the file
  hashes once; that is cheap to support.
- **PS2** (SLUS-20368 etc.): the same archives, but VIF-packed meshes, `.ssh` textures and PSX
  ADPCM. That means a new geometry decoder, about +6–10 weeks.
- **GameCube** (GMFE etc.): big-endian, `.gsh`, DSP audio. About +4–8 weeks.

Recommend Xbox-only for v1.

**9. Legal hygiene.**
- No Frontline bytes in git or in releases.
- Add `.gitignore` rules plus a pre-commit / CI scan for FL magics (`BIGF`, `SCHl`, `SHPX`, `MPCh`)
  and `zzzz_coop_fl_*` names.
- The inventory in this folder has names and sizes only.
- The converter code is ours (GPL with the engine).
- Never host converted output, not even for testers.

**Resolve the shipped PS3 music pak before announcing any of this** (see the verdict).

## 5. Effort and phasing

Estimates are person-weeks of focused work at this project's pace, Claude-assisted.

| Phase | Content | Estimate |
|---|---|---|
| **0. Extraction PoC** | Done today: FS, archives, inventory, `.cpt` render geometry, `.cdb` collision, `.msh`, strings. **Left:** the `.cpt` → texture binding, `.emt` decode, `.bpd` entity placements, audio decode (vgmstream build or own decoder), and splitting dialogue cues from subtitles | **2–3 wk** |
| **1. Pilot: 1_1 Seaside Stowaway end to end** | BSP writer (render + brushes + kd-tree + entity lump + light grid) 3 wk; textures/shaders 1 wk; scale, nav and pathnode validation 1 wk; mission script + dialogue + music + coop wiring 2 wk; playtest and fix 1 wk | **6–8 wk** |
| **2. Rest of the campaign (18 levels)** | Simple levels (3_2, 4_3, 5_3, 1_3, 3_1, 2_1, 6_2, 3_3, 5_1) at about 1.5–2 wk each. Heavy ones (6_1 Omaha scale, 1_2 U-boat, 2_2/2_3/4_1 disguise, 4_2 train, 5_2 minecart, 5_4 HO-IX finale, 1_4) at about 3–4 wk each | **35–50 wk** |
| **3. Coop integration framework** | Campaign chain, respawn progression, AI scaling profiles, map tiles and briefings, maptest entries, save/progression | **3–4 wk** (once; per-level coop work is inside phase 2) |
| **4. BYO converter productisation** | Installer and updater UI, disc verification tables, packaging the runtime, determinism tests, server-operator flow, PAL variants | **4–6 wk** |
| **Total** | | **≈ 50–70 wk** (about 55–80 with slack) |

### Why 1_1 for the pilot

- Its geometry and collision are **already proven** today.
- At 60 MB it is mid-size.
- It mixes urban, indoor, canal and countryside.
- It exercises every pipeline that matters to the scope: objectives (5), dialogue (interrogation,
  resistance), an MG nest, mines, a tank, and music.
- It needs **no ride or disguise** to finish: the crate stowaway becomes a trigger.

**Backup:** 3_2 Yard by Yard, which has the least scripting.

**Avoid for the pilot:** 6_1, which has the largest AI load and terrain plus the boat intro, and
overlaps m3l1.

### Main risks

1. The `.cpt` material binding resists decoding. Fallback: match by UV and texture size, or by
   hand per level. That is costly.
2. The BSP writer: a malformed lump crashes the engine (sky, fog, the light-grid layout). The engine
   source is the spec and gl1/gl2 are both ours to debug.
3. Collision from thin brushes leaves seams or snags, and big brush counts mean slow Recast. Mitigate
   with coplanar merging and the tiled navmesh fallback.
4. The `.bpd` stays opaque, so every entity is placed by hand (about +1 wk per level).
5. Ride and disguise set pieces in coop: 4_2, 5_2, 5_4, 2_2, 2_3, 4_1.
6. Deterministic output across disc variants and servers.
7. Legal: the shipped PS3 music pak today; and the "own a disc" requirement for server operators.

### Pilot go/no-go criteria

All of these must hold:
- the converter builds 1_1 from the ISO with no manual step, in under 10 minutes, deterministically
  (two runs give the same sha256);
- it boots via `ui_startdmmap 2` with zero `Script Error` lines;
- a `maptest` phase-2 patrol shows no fall-through and less than 5% stuck;
- the navmesh builds, and AI and bots reach 90% or more of the walkable area;
- 95% or more of surfaces are correctly textured, and it passes visual QA with no AI-slop issues;
- 2 players can complete all objectives with dialogue, subtitles and music;
- it runs at 60 fps or better on the user's PC (gl2);
- the CI scan finds no FL bytes in git or in a release.

**No-go:** item 1 above (texture binding) unsolved after the 3-week PoC, or the BSP writer cannot
produce collidable, navigable geometry.

## Decisions needed from the user

1. **The PS3-remaster Frontline music already in public releases** (`coop_music.pk3`): keep it,
   pull it, or move it behind the BYO converter?
2. Approve **Phase 0** (2–3 wk), then the **1_1 pilot**.
3. Choose the geometry route: **our own BSP writer** (recommended) or the EA `q3map` from the
   MOHRadiant SDK (closed exe, needs your OK, cannot run on player PCs).
4. Whether to **use vgmstream** (vendored source, ISC) or write our own EA-XA/Xbox-IMA decoder.
   Either way, no closed `sx.exe`.
5. Converter packaging: embedded Python or a C tool.
6. Xbox USA only for v1, or PAL Xbox too? PS2/GC are deferred.
7. Server policy: public servers may only run Frontline maps if the operator owns a disc.

## Files

- `tools/xdvdfs.py`: XDVDFS reader (lists and extracts, never writes to the image).
- `tools/viv.py`: BIGF/C0FB reader and unpacker.
- `tools/inventory.py`: builds `inventory.tsv` / `inventory.json`.
- `tools/cpt2obj.py`: `.cpt` / `.msh` → OBJ (render geometry, baked colour, UVs).
- `tools/cdb2obj.py`: `.cdb` → OBJ (collision).
- `tools/objview.py`: quick-look renderer (numpy and matplotlib; run without `-I`).
- `tools/probe.py`: float-run, string and word probes for undocumented chunks.
- `inventory.tsv`: 11,408 data rows, one per disc file and archive member. Columns: container, path,
  size, ext, 4-byte magic, level. Names only, no data.
- `inventory.json`: counts and bytes by extension, magics, and bytes per level.

**Run order:**
```
xdvdfs.py list <iso>
inventory.py <iso> <out>
xdvdfs.py extract <iso> <dir> "DATA/1/1_1/*"
viv.py <viv> <dir>
cpt2obj.py / cdb2obj.py
```

---

## Addendum 2026-11-08: POC result and pilot status

**POC: GO.**
- **Texture binding is solved.** Each 20-byte draw record (one table per art cell) points to a 128-byte texture record. The record's SHPX offset (word 28) is either a block inside its own chunk or zero; when it is zero, word 31 indexes the base chunk's texture table. That is 778/778 matches; the only exceptions are each chunk's null record 0. Result: 97.96% of the triangles are textured.
- **`.bpd` placement is decoded.**
  - Section 1 holds the navpoints, 24 bytes each: xyz plus the edge list.
  - Section 3 holds the entity instances: variable-size records with xyz and the behaviour chain as inline strings.
  - For 1_1 that is 1364 navpoints and 543 entities.
- **Frontline's world is mirrored** relative to MOHAA. The converter's `--mirror` flag handles it.

**Pilot (converter in `docs/tools/frontline/`, mission script in the mod's `maps/mfl_1_1.scr`):**
- Disc to pk3 takes 30 s and is byte-deterministic.
- 0 Script Errors at boot.
- The 2-bot self-test (`coop_fltest 1`) completes all 5 objectives and plays 12 dialogue cues and the music.
- **Open:** the bot navmesh is fragmented (bug-10605), and GL1 triangle-soup colours are stale (bug-10600; GL2 is fine).

**Correction to section 2a:** the engine repo already ships an open-source MOHAA map compiler, `openmohaa-hzm/code/tools/ommap`. It is a fallback to our own BSP writer, not EA's closed `q3map`.


### BYO converter productisation: user decision 2026-11-08

Frontline stays bring-your-own-disc and must be near-effortless. This adds:
- an optional installer/updater step with auto-detection of disc images (drive roots, Downloads,
  Documents, Desktop);
- hash verification (USA Xbox first);
- about 30 s of in-place conversion plus an optional local upscale;
- a local pak plus a marker cvar;
- a remembered path for silent re-conversion when the converter changes;
- a "Settings -> Frontline" entry to convert later.

Nothing EA-derived goes into git, releases, the updater payload or the public servers. Details are in
INTEGRATION.md section 8.
