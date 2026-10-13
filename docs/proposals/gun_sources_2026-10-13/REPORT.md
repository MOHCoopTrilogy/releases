# Better gun skins from outside the MOHAA scene - research report (2026-10-13)

Research only. Nothing was downloaded, nothing in the mod or the game was changed. Weighted towards
**Route B (repaint our own meshes)** after the user's steer "b would be ideal"; Route A (replacement
models) is a short appendix. The web part was cut short on purpose (usage budget) - section 6 lists what
that left unverified.

## 1. Summary

- **Repainting is realistic and the material is there.** Two big libraries - **ambientCG** and
  **Poly Haven** - publish everything under CC0 and say in plain words that redistribution is allowed and
  no credit is needed. Between them they have what a gun needs: about a dozen walnut veneers, fine-grained
  woods, plywood (for laminated stocks), scratched and painted steel, sheet metal, rust, leather, hessian
  and plain fabrics, dark plastics. **3dtextures.me** is also CC0.
- **Two libraries named in the brief are not as clean as assumed.** **ShareTextures** now uses a
  "custom CC0" with a ban on redistribution in collections without written permission - treat as *ask
  first*. **cgbookcase** says "100% free, no restrictions" on its front page but I found no licence page
  (the old one is a 404) - treat as *unverified*.
- **Nobody publishes "parkerized" or "blued gun steel" as a ready material.** Those finishes are almost
  uniform; what makes them read is edge wear, handling polish and fine scratches. That is what our own
  script already did for the double barrel. The libraries add the micro-detail (scratch and pitting
  layers); the look still comes from our painter. **Wood is where a photo source matters most.**
- **The weakest guns are a clear group**: the retail-era rifles and SMGs that no HD community pack ever
  covered (Lee-Enfield, G43, Mosin, SVT-40, Sten, FG 42, grease gun, M1 Carbine, unscoped Springfield)
  and a handful of tiny shared sheets (one 320x240 silencer texture is used by six guns).
- **A repaint does not fix a blocky outline or a missing part.** The Sten (591 triangles), Mosin (667)
  and M1919 (848, no sights) stay as coarse as they are. A repaint fixes blur, flat colour and missing
  surface detail - which is most of what reads in the aimed view.
- **Reference photos**: Wikimedia Commons has a category for nearly every weak gun (17-266 files each).
  Looking at a photo while painting carries no obligation. Copying pixels out of one does - see 3.4.
- **Route A exists but is thin**: Sketchfab has CC-BY (credit required) models for most of our guns,
  **none CC0** in the results I listed, and the licence there is a dropdown the uploader picks.

## 2. Triage - which gun families look weak

Method: `tools/triage.py` (read-only). Triangles are read from each mesh's header; the texture size is
the sheet the engine actually loads for the largest surface, taken from the 2026-10-05 weapon audit
(`docs/proposals/weapon_hd_2026-10-05/tools/inventory.json`). Full table: `triage.tsv` (87 weapons).
**Numbers only - I did not look at the textures in this task.** "Weak" means small sheet and/or coarse
mesh, plus what we already know from our own work. The inventory is eight days old: the MP18 repaint,
the BAR lift and the new double barrel are not in it.

"Upscaled 1024" = a 512 px original run through an upscaler: sharper edges, no new detail.

### Weak (repaint candidates)

| family | triangles | sheet(s) loaded today | note |
|---|---:|---|---|
| Shared silencer sheet `colt/colt45s2.tga` | - | **320x240** | used by 6 guns: silenced Colt, Beretta, Garand, grease gun, Kar98 sniper, Mosin sniper |
| Silenced Beretta | 1,204 | **256x256** jpg + the silencer sheet | smallest gun sheet in the set |
| M3 Grease Gun (+ silenced) | 2,567 / 2,903 | 512x512 jpg, one sheet, one surface | mesh is decent, texture is not; no moving parts on the mesh |
| Sten Mk II | 591 | 512x512, one sheet | coarsest SMG mesh |
| FG 42 | 920 | 512x512 jpg, one sheet | rear sight was added by us |
| Lee-Enfield | 782 | 512x512 retail, one sheet | 14 finishes hang off it |
| G43 (+ sniper) | 925 / 916 | 512x512 retail (sniper: its own 512 jpg) | |
| Mosin-Nagant (+ snipers) | 667 / 1,372 | 512x512 retail | |
| SVT-40 | 802 | 512x512 retail | |
| Springfield M1903 (unscoped) | 763 | 2 x 512x512 + a 100 px sights sheet | |
| M1 Carbine | 1,738 | 6 sheets, 480-612 px | |
| Beretta M38 (`moschetto.tik`) | 1,100 | 512x512 jpg | the same mesh as the Moschetto, which loads an upscaled 1024 |
| Silenced MP40, Silenced PPS-43 | 1,242 / 1,094 | 400-512 px / 500-800 px | |
| Nambu Type 14 | 3,180 | 512x512 | good mesh, small sheet |
| Welrod | 2,452 | 5 sheets, 620x540 | |
| Mauser C96 | 4,788 | 12 sheets, 640x480 | dense mesh, photo-patch sheets |
| S&W M10 | 3,288 | 12 sheets, 640x480 | same |
| Johnson M1941 | 12,506 | 16 sheets, 640x480 | densest mesh we have, smallest patches |
| Scoped variants: Enfield, Carcano, Garand (scope part), StG 44 scoped | 2,159-5,763 | 256-600 px | scope sheets `m1d.tga` 320x240 and `m1d2.tga` 256x512 are shared |
| Silenced Colt .45 | 3,452 | 512x512 + the silencer sheet | |
| Gewehrgranate | 1,712 | 256-512 px retail | |
| Pump shotgun - **receiver top only** | 762 | 2048 HD sheet | the sheet is fine, the receiver top is a soft blur (known) |

### Middling (upscaled or native 1024; coarse retail meshes)

Webley, Nagant revolver, Beretta, Hi-Standard, Carcano, De Lisle, L42A1, PPSh, Moschetto,
Vickers-Berthier, Breda, PIAT, Bazooka, **M1919** (1024 upscaled, 848 triangles, no sights on the mesh),
TT-33 (750 px), Luger (native 1024), PPK (1000 px, 4,926 triangles), Arisaka, Type 100, DP-28.

### Fine (leave)

Colt 45, P38, Kar98k and its sniper, M1 Garand, Thompson, MP40, StG 44, Springfield sniper,
Panzerschreck (all HD community sheets at 2048), BAR and MG42 (2048, upscaled), and the imported
remodels with ~1000-1200 px sheets on 2,000-5,500 triangle meshes (Thompson 1928 variants, MP18,
MP40 Reactivated, Gewehr 98, P14, Lewis, Webley Mk VI, Pacific Colt and Garand, StG 44 strapped).

One lesson from the 2026-10-05 pilot applies here: making an already-HD sheet bigger showed "almost no
visible difference" at the hip and only helped in the aimed view. So the gain is in the weak group
above, not in polishing the fine group.

## 3. Route B - sources for repainting our own meshes

### 3.1 Material libraries and what their licences actually say

| library | licence as stated on its own page | redistribution of our painted result | credit | verdict |
|---|---|---|---|---|
| **ambientCG** (ambientcg.com) | CC0 1.0; the licence page says you may "copy, modify, distribute" even commercially, and names putting the raw files in a video game | yes | not required | **use** |
| **Poly Haven** (polyhaven.com) | "all licensed as CC0"; "You can redistribute them" | yes | not required | **use** |
| **3dtextures.me** | CC0; any purpose; only asks that you do not claim to be the author | yes | not required | **use** |
| **ShareTextures** | a *custom* CC0 with added restrictions: no redistribution in collections / other sites / plugins without written permission; says nothing about games or mods | unclear | not required | **ask first or skip** |
| **cgbookcase** | front page: "100% free, no restrictions"; no licence page found today | probably, unverified | - | **verify before use** |
| Textures.com (for the record) | not CC0 - this is why we repainted the double barrel instead of shipping the author's bake | no | - | **do not use** |

A texture we paint from CC0 inputs is ours to ship with no strings. That is the reason to stay with the
three "use" rows.

### 3.2 Materials per surface type

Names come from the two libraries' public catalogue listings (868 Poly Haven textures, ambientCG
searches). **I matched them by name and category, I did not open or view each one** - whoever does the
repaint should eyeball the candidates first.

| surface on a gun | Poly Haven (CC0) | ambientCG (CC0) | note |
|---|---|---|---|
| **Walnut stock** (Garand, Carbine, Springfield, Thompson, BAR, Lee-Enfield, shotgun) | `american_walnut_veneer`, `black_walnut_veneer_01/02/03`, `european_walnut_veneer_04/05`, `natural_walnut_veneer`, `smoked_walnut_veneer`, `walnut_veneer`, `walnut_veneer_02`, `fine_grained_wood`, `dark_wood` | fine wood set `Wood013`-`Wood032`, `Wood053`-`Wood058`, `Wood090A/B`-`Wood092` (no asset is tagged "walnut") | veneers are flat, straight grain - right for a stock; darken and add oil sheen and dents in the painter |
| **Beech / birch stock** (Kar98k early, Mosin, SVT-40, PPSh) | `ash_veneer`, `white_maple_veneer`, `cherry_veneer` as stand-ins | paler entries of the same wood set | neither library has a beech by name; Soviet birch is a pale wood under orange-red shellac, so the tint is ours anyway |
| **Laminated stock** (late Kar98k, G43, FG 42 late type) | `plywood` (edge-on layer lines), any veneer cut across the grain | - | the glue lines are the look; easy to generate as stripes over a veneer |
| **Blued steel** (barrels, receivers, pistols) | `blue_metal_plate`, `metal_plate`, `metal_plate_02` | scratched set `Metal015`-`Metal018`, `Metal037`-`Metal039`, `Metal050B/C`, `Metal054A-C`, `Metal056A-C` | no "gun bluing" material anywhere: keep our procedural blue-black with edge wear, use these only as scratch / pitting layers |
| **Parkerized / phosphate grey** (US guns, late German guns) | `metal_plate` desaturated | `Metal0xx` scratch layers, `Rust007`-`Rust010` very faint for speckle | a matte grey-green with fine speckle; the pilot found the speckle is what sells it |
| **Stamped / painted sheet steel** (grease gun, Sten, MP40, PPS-43, magazines) | `painted_metal_shutter`, `rusty_painted_metal`, `green_metal_rust`, `rusty_metal_sheet` | `SheetMetal001`-`004`, `PaintedMetal001`-`018` | weld seams and press lines must be painted along our UVs - no library has those |
| **Worn bakelite** (MP40 grip and fore-end, StG 44 grips, P38 grips, FG 42 early grip) | - | dark entries of `Plastic001`-`Plastic018` | no bakelite asset in either library; it is brown-black plastic with a fibre mottle, simple to generate |
| **Canvas / webbing sling** | `hessian_230`, `hessian_380`, `denim_fabric` | plain weaves in the `Fabric0xx` set (105 results; no asset is tagged "canvas") | tint khaki / olive |
| **Leather sling, holster, cheek pad** | `brown_leather`, `fabric_leather_01/02`, `leather_red_02/03` | `Leather001`-`Leather039` | |
| **Rust and grime accents** | `rust_coarse_01`, `rusty_metal`-`rusty_metal_05` | `Rust007`-`Rust010`, `Metal020`-`Metal026` | use sparingly: service weapons were oiled |

### 3.3 Reference photos for the weak guns

Wikimedia Commons category pages, with the number of files each held when checked today.

| gun | Commons category | files |
|---|---|---:|
| M3 Grease Gun | `Category:M3 Grease gun` | 85 |
| Sten | `Category:Sten` | 50 (+6 subcategories) |
| FG 42 | `Category:FG42` | 30 |
| Lee-Enfield | `Category:Lee-Enfield Rifle No. 4` | 266 |
| G43 | `Category:Gewehr 43` | 17 |
| Mosin-Nagant | `Category:Mosin-Nagant rifle`, `Category:Mosin carbine` | 97 / 43 |
| SVT-40 | `Category:SVT-40` | 53 |
| Springfield M1903 | `Category:Springfield M1903` | 117 |
| M1919 | `Category:Browning M1919` | 120 |
| Beretta M38 | `Category:Beretta MAB 38` | 62 |
| PPS-43 | `Category:PPS-43` | 65 |
| Mauser C96 | `Category:Mauser C96` | 129 |
| MP18 | `Category:MP18` | 38 |
| Nambu | `Category:Nambu Type 14` | 24 |
| Welrod | `Category:Welrod` | 21 |
| Johnson M1941 | `Category:M1941 Johnson` | 14 |
| Type 100 | `Category:Type 100 submachine gun` | 8 |
| Pump shotgun | `Category:Winchester Model 1897` / `Category:Winchester Model 1912` | 16 / 3 |
| M1 Carbine, BAR, Carcano, De Lisle | not confirmed (the lookup was rate-limited or returned nothing) | - |

The URL is `https://commons.wikimedia.org/wiki/` + the category name with underscores.

### 3.4 The share-alike point, in plain terms

Every Commons file has its own licence. Three cases matter:

- **Looking at a photo and painting from it**: no obligation, whatever the photo's licence. This is how
  the references above should normally be used.
- **Copying pixels from a public-domain or CC0 photo** (US government and army photos are public
  domain; some museums release CC0): free to use, no strings.
- **Copying pixels from a CC-BY-SA photo**: the texture sheet we make becomes a derived work. It then
  needs credit **and must itself be offered under CC-BY-SA**. It does not spread to the rest of the mod,
  but that one sheet could no longer be mixed with pixels we cannot relicense - for example the walnut
  we took from a retail stock texture. Simplest rule: **CC-BY-SA photos are for looking, not for
  pasting.** CC-BY (no SA) pixels are usable with a credit line.

### 3.5 Which weak guns Route B fixes by itself

- **Fully fixed by a repaint** (the mesh is adequate, the sheet is the problem): grease guns, the shared
  silencer sheet, silenced Beretta and Colt, Nambu, Welrod, C96, M10, Johnson, Beretta M38, M1 Carbine,
  the pump shotgun's receiver top, the scope sheets.
- **Clearly better, outline stays coarse** (under ~1,000 triangles): Lee-Enfield, G43, Mosin, SVT-40,
  FG 42, unscoped Springfield, Sten.
- **Not fixed by paint**: the M1919's missing sights and the grease gun's missing moving parts. Those
  are mesh additions - the kind we already do in the ADS lanes (added handles, sights, breech blocks).

## 4. What each route costs us

**Repaint (Route B).** The mesh, its bones, the hand poses and every hip and aimed animation stay
exactly as they are. Work per gun:

1. Paint the sheet on the existing layout (script: wood, steel, wear, markings).
2. Ship it as `.dds` - in this engine a `.dds` in any pak beats a `.jpg` or `.tga` of the same name, so
   a repaint shipped in another format can be silently outranked.
3. Regenerate the four **baked** finishes (bloody and the three camos). Blued, chrome and gold are
   shader effects over the base sheet and follow by themselves.
4. One in-engine look per gun, hip and aimed.

Guns with many small sheets (Johnson 16, C96 12, M10 12, Carbine 6) cost more than one-sheet guns.

**Replacement model (Route A).** Everything is redone for that gun: conversion to the engine's mesh
format, new bones for the moving parts, new first-person hand poses, hip and aimed reloads and bolt
work re-baked for every stance, a world model, all seven finishes and every variant, the armory
entries - and the animation work already finished for that gun is thrown away. Only worth it where the
mesh itself is the complaint and a repaint cannot help.

## 5. Recommended shortlist - most visible improvement for least rework

| # | what | why it is cheap | materials | references |
|---|---|---|---|---|
| 1 | **Shared silencer sheet** (`colt45s2.tga`, 320x240) | one tiny sheet, six guns improve at once | blued / parkerized steel with scratch layer (ambientCG `Metal0xx`), knurling bands painted on the UVs | photos of the Welrod and De Lisle suppressors for wear patterns |
| 2 | **M3 Grease Gun** + silenced | one 512 sheet on one surface; the mesh is already decent | phosphate grey over stamped sheet steel (`SheetMetal001`-`004`, `PaintedMetal0xx`), painted weld seam along the receiver halves, dark plastic or steel grip | `Category:M3 Grease gun` (85) |
| 3 | **Pump shotgun receiver top** | a spot repaint of one UV island on an otherwise good HD sheet | our blued steel recipe from the double barrel, matting lines on the rib | `Category:Winchester Model 1912` / `1897` |
| 4 | **FG 42** | one 512 sheet, four surfaces | blued steel, laminated wood stock (`plywood` + veneer), bakelite-brown handguard | `Category:FG42` (30) |
| 5 | **Lee-Enfield** | one retail 512 sheet; a main British rifle | walnut or beech (`european_walnut_veneer`, `ash_veneer`), blued steel, brass butt plate, webbing sling (`hessian`) | `Category:Lee-Enfield Rifle No. 4` (266) |
| 6 | **G43** (+ sniper sheet) | one retail 512 sheet (the sniper has its own, likely the same layout - not checked) | laminated beech stock, phosphate steel, bakelite-style top handguard | `Category:Gewehr 43` (17) |
| 7 | **Mosin-Nagant and SVT-40** | two retail 512 sheets, same material recipe for both | pale wood under orange-red shellac (`white_maple_veneer` tinted), blued steel, canvas sling | `Category:Mosin-Nagant rifle` (97), `Category:SVT-40` (53) |
| 8 | **Sten Mk II** | one 512 sheet | black-painted and blued tube steel, weld beads, sheet-steel magazine | `Category:Sten` (50) |

Next tier, same recipe: M1 Carbine and unscoped Springfield (walnut + parkerized; more sheets), Beretta
M38, Nambu, then the many-sheet guns (Welrod, C96, M10, Johnson).

Per family, in one line each:

- **Repaint**: everything in the "Weak" table.
- **Leave**: everything in the "Fine" list; the "Middling" list until the weak group is done.
- **Mesh addition, not a new model**: M1919 sights (already in hand in the heavy lane), grease gun
  bolt cover.
- **Replace**: nothing recommended now. If one gun is ever replaced, the Sten or the Mosin (coarsest
  meshes) would gain most - see the appendix.

## 6. What I could not verify

- **I did not look at any texture or preview image** - neither ours nor the libraries'. The triage is
  by size and triangle count; the material names are by catalogue name and category.
- The triage uses the 2026-10-05 inventory; guns changed since then are not reflected.
- cgbookcase's licence (no licence page found); ShareTextures' position on bundling in a mod.
- Individual Commons files' licences - they vary file by file and must be read at the moment a photo
  is used as a pixel source. The categories for the M1 Carbine, BAR, Carcano and De Lisle were not
  confirmed.
- Whether each weak gun's UV layout is roomy enough for a higher-resolution repaint (overlapping or
  mirrored islands limit what paint can do) - needs a look per gun.
- Route A: OpenGameArt, itch.io, BlenderKit, Poly Haven models, museum scans, GitHub open-source WW2
  games and ModDB were **not** searched beyond a few general queries; the Sketchfab listing below is
  metadata only, previews not viewed, authorship not checked.
- Not legal advice: the licence readings are a plain reading of each site's own page on 2026-10-13.

## Appendix A - Route A stand-outs (short, as found)

From `tools/sketchfab_scan.py`: public listing queries per gun, models marked downloadable, sorted by
likes; full list in `sketchfab_scan.tsv`. **Every licence here is the dropdown the uploader chose, not a
verified statement of authorship. No CC0 model appeared for any of our guns; all rows are CC Attribution
(credit required).** Quality is read from the listing figures only.

| gun | model / author | triangles | textures | URL |
|---|---|---:|---|---|
| Trench shotgun | "Winchester Model 1897", buh-late | 18.3k | 4096 px | https://sketchfab.com/3d-models/6194ecd23344442fb23f5820f895a0d8 |
| M1 Carbine | "M1 Carbine", roelandvermeulen (a course piece) | 6.9k | 4096 px | https://sketchfab.com/3d-models/d9edbccc56fe4b6db765ebc494dc2ceb |
| Sten | "STEN Mk5", alexanderkirby (a Mk V, we have a Mk II) | 15.0k | 4096 px | https://sketchfab.com/3d-models/746a00d1a1bd4278927839fdc903dff6 |
| Welrod | "Welrod MKii", alexanderkirby | 3.2k | 4096 px | https://sketchfab.com/3d-models/892e4f1defa843268d459ba5f3475f1c |
| Springfield | "M1903 A3 Springfield", Gintoki1234 (says it has a simple rig) | 22.7k | 4096 px | https://sketchfab.com/3d-models/fa6f760cd28b4d3db2011ab2cab0f719 |
| Lee-Enfield | "Lee Enfield SMLE MKIII", skaveria | 12.5k | 4096 px | https://sketchfab.com/3d-models/7c35777ac96f4c6693b21a145a6dd7d5 |
| Mosin | "Mosin Nagant M91", Doinkoloink | 9.1k | 4096 px | https://sketchfab.com/3d-models/55c00242c4024307a761a89167e39a7c |
| Beretta M38 | "Beretta MAB 38", twilightfox | 15.7k | 4096 px | https://sketchfab.com/3d-models/4607b3ab335f4c28a065276a5e7e1d77 |
| FG 42 | "FG42", Shorty_Digitan | 16.9k | 4096 px, 30 files | https://sketchfab.com/3d-models/d699ac259bd74f70a51125a7e4320f4b |
| many guns | TastyTony's "Low-Poly ..." series (grease gun, Sten, G43, SVT-40, PPS-43, Carcano, Nambu, BAR, 1897...) | 2-9k | **untextured** | e.g. https://sketchfab.com/3d-models/9fe93b78f0c147d3970d7fadd1df776e |

Red flags seen:

- Uploads titled "(Enlisted)" by one account (M1919A4, De Lisle, Beretta M38): taken from the commercial
  game Enlisted - **not usable**, whatever the licence field says.
- An MP40 titled after the game Free Fire; one MP18 and one FG 42 whose text mentions Battlefield - treat
  as game-derived until shown otherwise.
- One MP18 whose uploader states he did not model it.
- Off Sketchfab: a "free Unity low-poly WW2 weapons" pack whose terms forbid redistribution; RenderHub
  WW2 listings marked editorial-use-only.
- OpenGameArt: a "Various Small Arms" set (author Tabasco, listed as CC-BY 3.0 / CC0, said to include an
  M1911 and a Mosin 91/30) came up in search and was **not opened**.

## Sources

- https://docs.ambientcg.com/license/
- https://ambientcg.com/ (catalogue listing via its public API)
- https://polyhaven.com/license
- https://polyhaven.com/textures (catalogue listing via https://api.polyhaven.com/assets?t=textures)
- https://3dtextures.me/about/
- https://www.sharetextures.com/p/license
- https://www.cgbookcase.com/
- https://commons.wikimedia.org/wiki/Category:M3_Grease_gun
- https://commons.wikimedia.org/wiki/Category:Sten
- https://commons.wikimedia.org/wiki/Category:FG42
- https://commons.wikimedia.org/wiki/Category:Lee-Enfield_Rifle_No._4
- https://commons.wikimedia.org/wiki/Category:Gewehr_43
- https://commons.wikimedia.org/wiki/Category:Mosin-Nagant_rifle
- https://commons.wikimedia.org/wiki/Category:SVT-40
- https://commons.wikimedia.org/wiki/Category:Springfield_M1903
- https://commons.wikimedia.org/wiki/Category:Browning_M1919
- https://commons.wikimedia.org/wiki/Category:Beretta_MAB_38
- https://commons.wikimedia.org/wiki/Category:PPS-43
- https://commons.wikimedia.org/wiki/Category:Mauser_C96
- https://commons.wikimedia.org/wiki/Category:MP18
- https://commons.wikimedia.org/wiki/Category:Nambu_Type_14
- https://commons.wikimedia.org/wiki/Category:Welrod
- https://commons.wikimedia.org/wiki/Category:M1941_Johnson
- https://commons.wikimedia.org/wiki/Category:Type_100_submachine_gun
- https://commons.wikimedia.org/wiki/Category:Winchester_Model_1897
- https://commons.wikimedia.org/wiki/Category:Winchester_Model_1912
- https://api.sketchfab.com/v3/search (public listing; the model URLs are in Appendix A and `sketchfab_scan.tsv`)
- https://opengameart.org/content/low-poly-guns-pack (search result, not opened)
- https://opengameart.org/content/cethiels-weapons-3d (search result, not opened)
- https://shakiroslann.digitalpress.blog/free-unity-package-low-poly-weapon/ (search result: no redistribution)
- https://www.renderhub.com/loss/ww2-mp40-rigged-submachine-gun (search result: editorial use only)
- https://www.cgchannel.com/2020/03/get-2000-free-3d-models-from-the-smithsonian-collection/ (search result; no firearm scans confirmed)
- Local: `docs/proposals/weapon_hd_2026-10-05/` (audit, inventory, pilot result), `docs/proposals/ads_twohand_2026-10-11/coverage.md`
