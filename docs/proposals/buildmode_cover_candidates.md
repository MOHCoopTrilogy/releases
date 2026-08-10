# Build-Mode Cover Candidates — MOHAARU custom map pack audit

**Date:** 2026-08-07
**Scope:** READ-ONLY audit of `G:\mohaa_custom_maps` for static prop models usable as **cover**
in build mode, not already in `coop_mod/buildmode_catalog.scr`.
**Nothing was copied, extracted or modified.** This file is the only artifact written.

---

## 1. Summary — what was actually measured

Every number below came from a scripted sweep; the method is stated next to each.

| Measurement | Value | How measured |
|---|---:|---|
| `.pk3` archives found under `G:\mohaa_custom_maps` | **7** | `os.walk` + `.pk3` suffix |
| Archives successfully **opened** by `zipfile` | **7** | counted after `ZipFile()` succeeded; asserted `> 0` |
| Total zip entries across all 7 | **22,106** | sum of `len(z.namelist())` |
| Unique `models/**/*.tik` paths | **658** | set union, lowercased, `/`-normalised |
| — already present in `buildmode_catalog.scr` | **97** | set intersection with catalog paths |
| — already present under `hzm-mohaa-coop-mod/models/` | **2** | set intersection with on-disk tree (723 `.tik` on disk) |
| — **remaining / uncovered** | **559** | difference |
| Rejected wholesale by directory class (see §5) | **309** | prefix match on `skylimit/ fx/ emitters/ sound/ player/ human/ projectiles/ statweapons/` |
| Shortlist after directory rejection | **250** | 559 − 309 |
| Candidates opened and read in full (.tik text) | **85** | hand-picked from the 250 by name/path heuristic |
| Of those, parsed without error | **83** | 2 paths (`models/school/organ*.tik`) were listed but the entry name did not round-trip; treated as not-found |
| Candidates whose geometry was **measured** (SKD bbox) | **53** | binary parse of the `.skd`, see §2 |

Catalog itself: **44 categories**, **1,859 item lines**, **1,844 unique tik paths**
(15 paths appear in two categories).

### The 7 archives

| pk3 | entries |
|---|---:|
| `x-MOHAARU_Map_Pack.pk3` | 2,900 |
| `xyz-MOHAARU_Map_Pack.pk3` | 2,470 |
| `z-MOHAARU_Map_Pack.pk3` | 3,708 |
| `zz-MOHAARU_Map_Pack.pk3` | 1,200 |
| `zzz-MOHAARU_Map_Pack.pk3` | 2,890 |
| `zzzz-MOHAARU_Map_Pack.pk3` | 5,829 |
| `zzzzz-MOHAARU_Map_Pack.pk3` | 3,109 |

> **A prior pass already mined these packs.** Categories 37 `MOHAARU COVER` (5 items) and
> 38 `MOHAARU SCENE` (14 items) exist. That pass took only `models/milkshape/*` content.
> It never touched `models/custom/`, `models/renan_models/` (the root-level `models/*.tik`),
> `models/storm/` or the `cod_*` railcars — which is where essentially all the value below is.

---

## 2. How size was determined (so the numbers can be trusted or discarded)

MOHAA `.skd` is `SKMD`. Struct layout taken from this repo's own
`openmohaa-hzm/code/tools/md5_2_skX/skx_format.h` (`skdHeader_t` / `skdBone_t` /
`skdSurface_t`, with compile-time size asserts 148/84/100). The parser walks surfaces →
vertices → weights, resolves each weight's bone-relative offset against a bone world position
accumulated down the parent chain, and takes the min/max. Dimensions are then multiplied by
the `scale` in the `.tik` `setup` block.

- **53 of 53 measured models resolved to a single root bone** except `cubus_coke_truck` (6
  bones). Single-bone means the bbox is exact, not estimated.
- `.skb` files are `SKL ` **version 3**, a different container the parser does not read.
  Those three models (`pool`, `car`, `fordpolice`) are marked **size unknown**.
- Reference scale: MOHAA ≈ 1 unit per inch. Player standing ≈ 72u, crouched ≈ 40u.
  **Good cover = 40–70u tall.** Dimensions below are `X × Y × Z`, Z = height, post-scale.

---

## 3. How "self-contained" was determined

First attempt was wrong and is recorded here so it is not repeated: matching a surface's
shader name against pk3 filenames by basename gave false positives, because
`models/custom/cementery/crypt010.skd` "matches" shader `crypt010`. **That result was
discarded.**

The correct check, used for the table below, is three-stage:

1. Parse every `scripts/*.shader` in the pk3 with a brace walker (4,193 shader defs in
   `zzzzz` alone; 8,571 in the 44 retail paks) and look the surface's shader name up there.
2. For each `map` / `clampmap` / `animmap` stage in that shader, confirm the image exists —
   in the same pk3, or in retail (`main`/`mainta`/`maintt`, 39,403 entries).
3. If the name is not a pk3 shader, fall back to a literal image file, then to a retail shader.

Result: **every candidate's textures resolve** — zero missing images across the whole
shortlist. The single exception is `models/items/item_88shell.tik`, whose shader
`static_88shell_MOD` resolves nowhere.

**Additionally**, each shader name was tested for **collision** — is that same name also
defined in another MOHAARU pack, or in retail? This is the project's documented
shader-isolation hazard (`docs/TRAPS.md`, bug-922: contested shader names lose
unpredictably). The result splits the shortlist cleanly in two, and it is the single most
useful finding of this audit:

- Everything under `models/custom/`, `models/renan_models/`, `models/storm/`,
  `models/milkshape/` — **zero collisions**. Clean to pull.
- Every `*w.tik` winter/alt **reskin of a retail vehicle** — 1 to 13 colliding shader names
  each. See §6.

---

## 4. Ranked cover candidates

All rows: source pk3 is `zzzzz-MOHAARU_Map_Pack.pk3` unless noted; all are **absent from the
44 retail paks** (verified by path lookup) so they are genuinely new content that would have
to ship. "Self-contained" = shaders defined in-pack, all texture stages resolve, **and** no
shader-name collision with retail or another pack.

### Tier 1 — new concepts, correct cover height

| # | Model | What it is | Size X×Y×Z (u) | pk3 | Self-contained |
|--:|---|---|---|---|---|
| 1 | `models/custom/crypt020.tik` | Stone crypt / sarcophagus with lid. Hard cover, near standing height | 71 × 134 × 61 | zzzzz | **yes** |
| 2 | `models/custom/crypt010.tik` | Plain stone crypt, flat top | 71 × 134 × 57 | zzzzz | **yes** |
| 3 | `models/cod_flatcar.tik` | Railway flatcar. Long low barricade / rail-yard cover | 96 × 463 × 68 | zzzzz | **yes** |
| 4 | `models/custom/tombstone30.tik` | Tall headstone / cross, standing cover | 11 × 29 × 75 | zzzzz | **yes** |
| 5 | `models/custom/tombstone10.tik` | Slab headstone, crouch cover | 4 × 24 × 48 | zzzzz | **yes** |
| 6 | `models/custom/tombstone40.tik` | Headstone variant | 4 × 30 × 51 | zzzzz | **yes** |
| 7 | `models/custom/tombstone50.tik` | Headstone variant, wider | 5 × 32 × 48 | zzzzz | **yes** |
| 8 | `models/custom/tombstone20.tik` | Thick headstone | 10 × 25 × 45 | zzzzz | **yes** |
| 9 | `models/custom/tombstone60.tik` | Headstone variant | 4 × 25 × 48 | zzzzz | **yes** |
| 10 | `models/custom/tombstone70.tik` | Headstone variant | 4 × 24 × 48 | zzzzz | **yes** |
| 11 | `models/custom/tombstone80.tik` | Headstone — same bbox as 70, distinct file (different bytes) | 4 × 24 × 48 | zzzzz | **yes** |
| 12 | `models/custom/woodstack.tik` | Stacked log pile. Ideal crouch cover | 118 × 29 × 48 | zzzzz | **yes** |
| 13 | `models/custom/bench.tik` | Wooden bench with back | 90 × 27 × 55 | zzzzz | **yes** |
| 14 | `models/w_barrel_5.tik` | Wooden barrel cluster / group | 73 × 36 × 51 | zzzzz | **yes** |
| 15 | `models/custom/stone_bench.tik` | Long stone bench, low/prone cover | 149 × 48 × 39 | zzzzz | **yes** |
| 16 | `models/w_barrel.tik` | Single wooden barrel, upright | 33 × 33 × 48 | zzzzz | **yes** |
| 17 | `models/custom/wooden_barrel.tik` | Barrel, distinct mesh from #16 | 28 × 29 × 41 | zzzzz | **yes** |
| 18 | `models/custom/dragon_tooth.tik` | Concrete dragon's tooth. Different mesh from retail `static/dragontooth.tik` | 64 × 64 × 67 | zzzzz | **yes** |
| 19 | `models/cod_boxcar_o.tik` | Open-door railway boxcar — wall-scale barrier, not crouch cover | 404 × 107 × 161 | zzzzz | **yes** |
| 20 | `models/cod_boxcar_c.tik` | Closed railway boxcar | 107 × 404 × 161 | zzzzz | **yes** |

> `models/custom/wooden_barrel_2.tik` is **byte-identical geometry** to `models/w_barrel.tik`
> (same md5 on the `.skd`). Take one, not both.
> `models/custom/wood_champagne_crate.tik` is likewise byte-identical to
> `models/custom/wood_crate.tik` — same mesh at a different `scale` (.55 vs .7).

### Tier 2 — machinery, hard cover

| # | Model | What it is | Size X×Y×Z (u) | pk3 | Self-contained |
|--:|---|---|---|---|---|
| 21 | `models/storm/storm_buldozer.tik` | Bulldozer. Big solid hard cover | 204 × 127 × 125 | xyz | **yes** |
| 22 | `models/storm/storm_generator.tik` | Industrial generator set | 208 × 151 × 113 | xyz | **yes** |
| 23 | `models/milkshape/cubus_ford_truck.tik` | Period Ford flatbed truck | 268 × 102 × 93 | xyz | **yes** |
| 24 | `models/milkshape/cubus_pkmchevy.tik` | Chevy pickup | 284 × 107 × 76 | xyz | **yes** |

Caveat on 23/24: the era of these two was **not** verified — only their geometry and shaders
were. Both declare `classname drivablevehicle` / `animate` in the tik, which build mode
overrides anyway (§7). Eyeball them before shipping.

### Tier 3 — interior / urban cover (furniture)

All `zzzzz`, all self-contained, all zero-collision.

| # | Model | What it is | Size X×Y×Z (u) |
|--:|---|---|---|
| 25 | `models/metal_shelve.tik` | Metal warehouse shelving unit | 127 × 43 × 109 |
| 26 | `models/custom/armoire_d.tik` | Wardrobe / armoire, damaged | 36 × 99 × 148 |
| 27 | `models/refrigerator.tik` | Period refrigerator | 57 × 52 × 138 |
| 28 | `models/bookshelf_wide.tik` | Wide bookshelf | 27 × 119 × 121 |
| 29 | `models/bookshelf_shortdoor.tik` | Short bookshelf with door | 33 × 68 × 117 |
| 30 | `models/dining_table_sq.tik` | Large dining table (flippable cover) | 222 × 93 × 66 |
| 31 | `models/common_table.tik` | Plain table | 129 × 61 × 65 |
| 32 | `models/bathtub5.tik` | Cast-iron bathtub | 127 × 59 × 54 |
| 33 | `models/sink_kitchen.tik` | Kitchen sink counter run | 81 × 238 × 127 |
| 34 | `models/waw_stove.tik` | Cast-iron stove with flue (199u incl. flue) | 130 × 80 × 199 |
| 35 | `models/waw_bed.tik` | Iron bed frame | 124 × 161 × 96 |
| 36 | `models/custom/cod_bed_d.tik` | Bed, damaged | 98 × 131 × 77 |
| 37 | `models/custom/mattress_b.tik` | Bare mattress (soft cover / dressing) | 63 × 134 × 84 |

### Tier 4 — marginal, low priority

`models/ammobox4.tik` (129×43×27), `models/ammobox3.tik` (46×38×23),
`models/custom/crate010.tik` (26×50×26), `crate020.tik` (26×51×26),
`wood_crate.tik` (25×46×27), `wood_crate_e.tik` (25×46×27),
`wood_champagne_crate.tik` (20×36×21), `wood_champagne_crate_2.tik` (20×36×21).

All self-contained and clean, but **21–27u tall** — prone cover at best, and the catalog
already carries 60 crate entries and a full `CRATES + SUPPLY` category. Pull only if
stackability or visual variety is wanted.

---

## 5. Which existing category each candidate slots into

Build mode auto-forces `solid` on entry for categories flagged
`level.coop_build_catIsCover[c] = 1` — currently **34, 35, 37, 39** only.

| Candidates | Category | Note |
|---|---|---|
| crypts, tombstones, dragon_tooth, woodstack, barrels (`w_barrel`, `w_barrel_5`, `wooden_barrel`), benches | **37 `MOHAARU COVER`** | already `catIsCover=1`, so they inherit solid-on-entry. This is the natural home and needs no new category. |
| `cod_flatcar`, `cod_boxcar_c`, `cod_boxcar_o` | **11 `DEFENSES + BARRIERS`** or **20 `STRUCTURES + HULLS`** | boxcars at 161u are barriers, not cover. Catalog currently has **no static railcar** (`models/vehicles/bp44train.tik` is a vehicle, `models/static/wagon.tik` is a horse cart). |
| `storm_buldozer`, `storm_generator`, `cubus_ford_truck`, `cubus_pkmchevy` | **37 `MOHAARU COVER`** (buldozer/generator) / **5 `TRUCKS + HALFTRACKS`** or **6 `JEEPS + CARS`** (the two trucks) | |
| shelving, armoire, refrigerator, bookshelves, tables, bathtub, sink, stove, beds, mattress | **12 `FURNITURE`** / **27 `FURNITURE + FIXTURES 2`** | 12 already holds `metalbench`, `bunkerbench`, `w_parkbench`, `peetrough` |
| ammo boxes | **25 `AMMO + CLIPS`** or **10 `CRATES + SUPPLY`** | |
| crates | **10 `CRATES + SUPPLY`** | |

If the cemetery set is taken as a group, a new `catIsCover=1` category (e.g. `CEMETERY
COVER`) is cleaner than diluting 37 — the catalog has **zero** hits for `tombstone`,
`gravestone`, `crypt` or `fountain` today.

---

## 6. Rejected — with reasons, so this is not re-audited

### 6a. Rejected wholesale by directory (309 paths, not individually opened)

| Prefix | count | reason |
|---|---:|---|
| `models/skylimit/` | 207 | skybox definitions, not props |
| `models/fx/` | 25 | effect emitters |
| `models/player/` | 20 | player models |
| `models/emitters/` | 18 | effect emitters |
| `models/human/` | 15 | character models |
| `models/sound/` | 13 | sound entities |
| `models/statweapons/` | 7 | weapons |
| `models/projectiles/` | 4 | projectiles |

Plus, from the remaining 250, roughly 60 root-level character tiks (`german_*`, `dday_*`,
`*-ranger_*`, `allied_*`, `new_generic_human.tik`) and ~40 `models/static/hitpmodels/*`
foliage (bushes, ferns, palms, grass). Characters are not cover; several of them also
**override retail path names**, which is an actively dangerous thing to ship.

### 6b. Individually examined and rejected

| Model(s) | Reason |
|---|---|
| `models/vc/vcfountain.tik`, `vcbridge1/2`, `vccanal`, `vcsewer` (+ `vcfire`, `vclighthum`, `vcchurchbell`, `vcphone`, `vcwindtrees1`) | **Not geometry.** All use `models/fx/dummy/dummy3.skd`, declare `rendereffects +dontdraw` + `notsolid`, and have **zero surfaces**. These are invisible ambient-sound emitters. The name "vcfountain" is misleading — it is the fountain's *sound*, not the fountain. |
| `models/frag-n-rock.tik` | Same: `dummy3.skd`, dontdraw, notsolid, 0 surfaces — an ambient sound emitter (`Amb_fragnrock.wav`). |
| `models/static/hedgehogw.tik` | Winter Czech hedgehog. Catalog already has `static/hedgehog_snowy.tik` (cat 11 #29) plus 5 other hedgehog entries. Also 1 colliding shader (`static_hedgehog_w`). |
| `models/custom/haybale.tik` | 34×53×26. Catalog already has `haystack`, `haystack1`, `haystack_dry01`, `haystack_dry02` in cat 11. |
| `models/ammo/mg_box.tik` | **Exists in retail paks already.** Also 19×17×14 — far under the 24u floor. |
| `models/items/item_88shell.tik` | Shader `static_88shell_MOD` resolves in **no** pk3 and **no** retail pak. Would render untextured. |
| `models/furniture/bunkerchrnw.tik`, `luxurychrnw.tik` | Chairs. Retail `.skd` + winter reskin; too small for cover. |
| `models/custom/street_lamp.tik`, `models/street_lamp5.tik` | 18×16×159 — a pole. No cover value. |
| `models/storm/storm_h2.tik` (245×128×100), `storm_monte.tik` (306×124×86) | Hummer H2 and Monte Carlo — modern civilian cars, anachronistic. |
| `models/milkshape/cubus_coke_truck.tik` | Coca-Cola truck. Anachronistic; also 1,240u long, 6 bones, and 1 shader resolves only from retail. |
| `models/milkshape/ufo/`, `bong/`, `popcan/`, `s76-camo/rudolph-s5`, `models/caskami/deadalien/`, `models/static/quake3_flag.tik`, `models/caskami/fork/` | Joke / non-WW2 content. |
| `models/caskami/fordpolice/fordpolice.tik` | Modern police car. (Also `.skb` — unmeasurable.) |
| `models/milkshape/pool/pool.tik`, `models/milkshape/car/car.tik` | `.skb` = `SKL ` version 3; the SKD parser cannot size them, so cover suitability is unverified. Pool table is plausible cover — re-open only if someone wants to eyeball it in-game. |
| `models/hedgerow.tik` | Bocage hedgerow, but measures **690 × 394 × 395** post-scale — implausibly tall for a hedge and likely a whole multi-piece strip, or a mesh authored in a different axis convention. Self-contained and collision-free, so **not dead** — but do not add it blind; load it in build mode and look at it first. |
| `models/static/rock_large_omaha.tik` | Retail `rock_winter_large.skd` + one colliding shader. Cat 16 already has 16 rock entries. |
| `models/static/v2w.tik`, `models/static/mg42ammoboxbltnw.tik`, `models/static/opeltruck_hoodopen_movable.tik` | Retail geometry + colliding custom shader; marginal gain. |
| **All winter/alt vehicle reskins:** `vehicle_shermantankw`, `vehicle_shermantank_deadw`, `vehicle_panzer_iv_europew`, `vehicle_opeltruck_greenw`, `vehicle_european_delivery_truck_green_caskami`, `vehicles/opeltruckgreen_dw`, `vehicles/panzer_iv_eudw`, `vehicles/panzer_iv_omaha`, `vehicles/snow_jeep`, `vehicles/m3a1`, `vehicles/allied_kingtank(_d)`, `vehicles/axis_kingtank_d` | **The shader-isolation trap, in bulk.** Their `.skd`/`.skb` is *not in the pk3* — it is the retail mesh. Only the shaders are new, and each carries **2–13 shader names that are also defined in other MOHAARU packs and/or retail** (e.g. `vehicle_panzer_iv_europew`: 12 of 12 collide; `panzer_iv_eudw`: 13 of 13). Per `docs/TRAPS.md` / bug-922 a contested shader name loses unpredictably. The only gain is a winter palette on vehicles cats 1 and 5 already carry. If ever wanted, apply the shader-isolation recipe: fresh shader name + private texture path, both coop-pk3-only, plus a retargeted tik. |

---

## 7. Two implementation notes worth keeping

1. **The tik's own `classname` / `notsolid` does not matter.** `buildmode.scr:657` spawns
   `script_model` and then applies solidity itself (`:664` `local.m solid` /
   `local.m notsolid`). So `storm_buldozer`'s `classname animate` + `notsolid`, and the
   `drivablevehicle` classnames, are irrelevant to build-mode use. Only geometry, shaders
   and size matter.

2. **Solid hulls are resized from the ghost.** `buildmode.scr:690` does
   `setsize ghost.getmins*scale ghost.getmaxs*scale` — so the measured bboxes above are what
   the player will actually clip against, times the build scale. A 48u tombstone at scale 1
   is genuine crouch cover; it does not need scaling up.

3. **Provenance caveat.** The `models/renan_models/` set (all the root-level `models/*.tik`:
   `cod_boxcar_*`, `cod_flatcar`, `w_barrel*`, `ammobox*`, `hedgerow`, `refrigerator`,
   `waw_*`, `bathtub5`, `bookshelf_*`, `metal_shelve`, `sink_kitchen`, `common_table`,
   `dining_table_sq`) carries QUAKED comments reading `static_COD5_...` /
   "Call of Duty World at War". These are third-party ports of another commercial game's
   assets. That is a redistribution question, not a technical one, and it is the user's call —
   flagging it rather than deciding it.

---

## 8. Reproducing this audit

Scripts are in the session scratchpad (not committed):
`scan1.py` (enumerate + exclude), `scan2.py` (tik deps), `bbox.py` (SKD geometry),
`retail.py` (retail availability), `shaders.py` (shader/texture resolution),
`collide.py` (shader-name collisions), `dedupe.py` (md5 on `.skd`).
Every one asserts `archives_opened > 0` before trusting a result.
