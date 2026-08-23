# HD Texture Pack Research — MOHAA Trilogy on OpenMOHAA (HZM Coop)

Read-only research. Nothing was downloaded, installed, or modified. The user installs.
Date: 2026-06-24. Scope: add a high-definition texture pack across AA + Spearhead + Breakthrough running on the HZM coop build, without breaking the coop mod.

---

## TL;DR

- **Top recommendation:** "Medal of Honor Allied Assault HD" (ModDB, `ZzZzZz - MOHAAHD_FINAL.pk3`). It is the only mature, single-file pak that the author explicitly states works for **AA, SH, and BT** — exactly our unified main+mainta+maintt mount. It is texture-only (no scripts/.tik/.bsp), so it cannot collide with the coop mod's script logic.
- **Integration in one paragraph:** Drop the HD pak into each game base folder it should cover, renamed so it sorts **after** the stock `pakN.pk3` but **before** our coop mod pak — e.g. `zz_hd_textures.pk3` (the coop pak is `zzzzzz_co-op_hzm_mod_mohaa.pk3`, which still sorts last and therefore wins every conflict). Because the engine mounts main + mainta + maintt under the one Breakthrough profile, a single placement in `main` (plus the pak's own SH/BT coverage) reaches all three games; keep it **texture-only** (no `.scr/.tik/.shader/.bsp`) so it only overrides image files and never touches mod behavior, then launch and watch the qconsole pak-mount list + run the existing 52-map maptest rotation to confirm no new load errors.
- **Single biggest risk:** Engine **texture-format support is narrow** — the renderer (`renderergl1`) loads only **TGA / JPG** (+ PCX/BMP) for normal textures, and **DDS only when the GPU reports S3TC compression**; **PNG is not wired in this backend at all.** A pack delivered as PNG (or as DDS on a non-S3TC context) silently fails to load and you get the default/placeholder texture. Verify the candidate pack ships TGA/JPG before recommending install.

---

## PART 1 — Candidate packs

ModDB blocks automated fetches (HTTP 403), so coverage/format/license below is from search snippets and the cited pages; treat the per-field values as "confirm on the download page before installing." The memory ref `reference_mohaa_moddb.md` (the 35-repo `mohaa-moddb` GitHub org) is a *scripting* resource — it contains no texture packs, so this went broader (ModDB, Nexus, OpenMOHAA GitHub org).

| Pack | Source | Covers | 3-game coverage | Format / res | Packaging | License / redistrib | Active / updated | Targets |
|---|---|---|---|---|---|---|---|---|
| **MOHAA HD ("MOHAAHD_FINAL")** ⭐ | moddb.com/mods/medal-of-honor-allied-assault-hd | World textures, ~3,500 textures modified | **AA + SH + BT (author-stated)** | AI-upscaled; mixed res; ships as pk3 (confirm TGA/JPG inside) | Single `ZzZzZz - MOHAAHD_FINAL.pk3` | Mixed/derivative — "some textures extracted from CoD" (redistribution gray area, personal use) | Final ~May 2010 (stable, inactive) | Retail engine; format-compatible w/ OpenMOHAA |
| **MoHAA Complete 2x Remaster** | moddb.com/mods/mohaa-complete-2x-remaster | Stock-map world textures **+ player skins** | AA-centric (stock maps + MP skins) | 1920x1080-class upscales | pk3 | Per ModDB page | Newer than the 2010 HD pack | Retail; format-compatible |
| **MoHAA Texture remaster (ESRGAN 2K)** | nexusmods.com/medalofhonoralliedassault/mods/2 | Environment textures, some items/posters | AA only; "replace Pak2.pk3" in `main` | **2K, TGA in pk3** (format confirmed) | pk3 (replaces a stock pak) | Author/free modder resources; **no re-upload / no porting** | Slow WIP | Retail; **noted MP visual glitches + D-Day MP map broken** |
| **MoHAA Redux HD Textures** | nexusmods.com/medalofhonoralliedassault/mods/9 | World textures (redux set) | AA | Upscaled (confirm format) | pk3 | Nexus per-mod perms | — | Retail |
| **Enhanced Textures** | moddb.com/mods/enhanced-textures | Higher-quality world textures, "original look intact" | AA | 256–2K | pk3 | Per page | — | Retail |
| **Hi-Res Realism Texture mod** | moddb.com/mods/hi-res-realism-texture-mod | World textures | AA | Hi-res | pk3 | Per page | Older | Retail |
| **FAH Infantry HD Remaster** | moddb.com/mods/fah-infantry-hd-remaster | **Character/infantry skins only** (x2/x4/x6) | AA infantry | Upscaled skins | pk3 | Per page | — | Retail; pairs well w/ a world pack |
| **MP Texture Pack HD-1080p** | moddb.com/mods/moh-allied-assault-mp-textures-hd-1080p | **MP** stock maps + player skins | AA MP | 1920x1080 | pk3 addon | Per page | — | Retail |
| **ESRGAN_MoHAA_auto** (toolkit) | github.com/gabriellichacz/ESRGAN_MoHAA_auto | *Tooling* to upscale your own | any (you generate) | You choose (TGA) | scripts | Open source tool | Active-ish | Build-your-own option |
| **openmoh/MOHAA-HD-Assets** | github.com/openmoh/MOHAA-HD-Assets | (Intended HD asset home) | — | — | git | OpenMOHAA org | **Effectively empty — 1 commit, a "nonconverted" folder, no README/content** | OpenMOHAA-native, but **not usable today** |

**OpenMOHAA's own HD effort:** There is an org repo `openmoh/MOHAA-HD-Assets`, but it is a placeholder (1 commit, empty `nonconverted` folder, no description). OpenMOHAA itself has **no shipped/official HD texture pack** as of this research — the community ModDB/Nexus packs above are the realistic options.

---

## PART 2 — Engine / format feasibility (verified in source)

All citations are from the live HZM tree under `C:\mohaa-coop-dev\openmohaa-hzm`.

**Texture loaders actually wired (renderergl1 — the active backend).** `code/renderergl1/tr_image.c`, `R_LoadImage()` (line ~2399) dispatches by extension:
- `.tga` / `.jpg` -> tries JPG then TGA (lines 2429–2445). **These are the safe, universal formats.**
- `.pcx` -> `LoadPCX32` (2446); `.bmp` -> `LoadBMP` (2450); `.gst` -> ghost (2458).
- **`.png` is NOT handled here.** `tr_image_png.c` exists in `renderercommon` but `R_LoadImage` in gl1 never calls `LoadPNG` (grep: no match). **Do not assume PNG textures load.**
- **DDS:** `LoadDDS` exists (line 1477) but is only attempted when `glConfig.textureCompression == TC_S3TC || TC_S3TC_ARB` (lines 2418–2425). DDS is opportunistic, not guaranteed — on a context without S3TC it is skipped. A DDS-only pack is therefore a gamble; TGA/JPG always works.

**TGA constraints (`LoadTGA`, ~1628):** only type 2 (RGB), 3 (grayscale), 10 (RLE-RGB); 24- or 32-bit only; **no colormaps/8-bit palettized** (errors with `ERR_DROP`). So a pack of paletted/16-bit TGAs would hard-error. Standard 24/32-bit upscale TGAs are fine.

**Max texture size / downscale (`tr_image.c` 511–520, `tr_init.c` 313–314):** `glConfig.maxTextureSize` is read from the GPU's `GL_MAX_TEXTURE_SIZE`. Any image larger than that is **halved repeatedly until it fits** ("clamp to the current upper OpenGL limit"). On any modern GPU this is >=16384, so 2K/4K textures load at full res; the engine will not reject large textures, it just downsamples if the GPU can't hold them. `r_picmip` further reduces detail if set.

**Perf / VRAM implications.** These packs replace many BASE textures with 2K–4K uncompressed TGA. VRAM and load-time scale roughly with the square of resolution: a 2x linear upscale is ~4x the texel memory; the "complete remaster" sets unpack to ~20 GB on disk and can push hundreds of MB–GB of VRAM. Because gl1 uploads largely uncompressed (DDS/S3TC only when the driver advertises it), expect higher VRAM use and longer map loads than retail. Mitigations available to the user: prefer JPG world textures (smaller), keep skins TGA (alpha), or set `r_picmip 1`.

---

## PART 3 — Integration without breaking the coop mod (verified in source)

**Pak load order (decisive).** `code/qcommon/files.cpp`:
- Within one game dir, `Sys_ListFiles(...".pk3")` is sorted by `paksort` -> `FS_PathCmp` (ASCII/alpha), then each pak is **prepended** to `fs_searchpaths` in iteration order (3111, 3129–3140). Net effect: **later alphabetically = higher search priority.** This matches the project's understanding ("pk3s load alphabetically, later = higher priority").
- The coop mod pak is `zzzzzz_co-op_hzm_mod_mohaa.pk3` — six z's. **Any HD pak named with fewer/lower z's (e.g. `zz_hd_textures.pk3`) sorts BEFORE it, so the coop pak wins every filename conflict.** This is the core no-break guarantee.

**Unified mount (per-game coverage).** `FS_Startup` (3506–3516): when `fs_basegame == "maintt"` (our Breakthrough profile), the engine also `FS_AddGameDirectory("mainta")`, added before maintt so priority is **maintt+mod > mainta > main**. So a placement in `main` is visible to all three games; the HD pack's own SH/BT-specific textures (if any) can additionally go in `mainta`/`maintt`. Recommended placement:
- `main\zz_hd_textures.pk3` — covers AA world textures shared across the trilogy (most of the win).
- Optionally `mainta\zz_hd_textures.pk3` and/or `maintt\zz_hd_textures.pk3` if the pack has expansion-specific art. In every dir it sorts after stock `pakN.pk3` and before `zzzzzz_...` (maintt only has the coop pak).

**Texture-only = the safe choice.** The coop mod is *scripts + a cgame.dll + cfgs* (see `build.ps1`: packs `hzm-mohaa-coop-mod` recursively). It does not own world `.tga`/`.jpg` art. A pack that contains **only image files (no `.scr/.tik/.shader/.bsp/.snd`)** can therefore override BASE textures without ever shadowing a coop-mod file — there is literally no overlapping path. This is the single most important constraint to enforce when picking/repacking a candidate.

**Shader (.shader) risk.** `.shader` files in `scripts/` define surface passes; two paks defining the same shader name can conflict, and shader changes *can* alter gameplay-visible surfaces (e.g. transparency, glow). Many HD packs are pure image swaps and ship no `.shader`. **If a candidate pack includes `.shader` files, inspect/strip them** unless they're needed — image-only override avoids all shader-merge risk. The coop pak's shaders (if any) still win by load order, but stripping avoids surprises.

**sv_pure / pure-pak rejection — NOT a problem in this engine (verified).**
- Server default is `sv_pure 0` (`code/server/sv_init.c:1070–1072`).
- The client **ignores the server's sv_pure**: `code/client/cl_parse.cpp:505–506` — `// wombat: we ignore server's sv_pure for now` (the `cl_connectedToPureServer` assignment is commented out). So clients are never kicked for carrying an extra HD pak the server lacks, and vice-versa.
- Practical note: for a clean coop session, have **all players install the same HD pak** anyway (purely cosmetic consistency / autodownload off). A mismatched pak only changes what each client *sees* locally; it does not desync or reject — the server's missing-files path only prints a non-fatal warning (`cl_main.cpp:1974–1986`).

**build.ps1 implications.** `build.ps1` only packs/deploys the coop pak (`zzzzzz_...pk3`), `autoexec.cfg`, and `cgame.dll`. It **does not touch HD paks** — they are dropped in by hand once and persist. No build.ps1 change is required. The only caution: do **not** put HD source art inside `hzm-mohaa-coop-mod\` (it would get swept into the coop pak by the recursive `Get-ChildItem`); keep the HD pak a standalone file in the game dirs.

**How to test for conflicts (no new tooling needed).**
1. Install the HD pak to `main\` (and optionally `mainta\`/`maintt\`).
2. Launch the existing Breakthrough profile; in `qconsole.log` confirm the pak-mount list shows `zz_hd_textures.pk3` mounting **before** `zzzzzz_co-op_hzm_mod_mohaa.pk3` (and that `mainta` is mounted — proves fs-unify).
3. Run the existing 52-map maptest rotation (`maptest_start.cfg`). Success = same `MAPTEST_LOADED`/tour banners as the clean baseline, no new `LoadTGA: ... not supported` / `could not load` image errors, no new crashes. Any image-format error in the log identifies a non-TGA/JPG asset to drop.
4. Spot-check 2–3 maps per game (AA m-series, SH t-series, BT e-series) visually; confirm coop HUD/objectives unchanged (proves the script layer is untouched).

---

## Recommendation + why

1. **Primary: "MOHAA HD" (`ZzZzZz - MOHAAHD_FINAL.pk3`)** — only mature pack explicitly covering AA+SH+BT, single-file, world-texture-only, and the author already documents the "add Z's to control load order" trick we rely on. Rename to `zz_hd_textures.pk3` so our coop pak still outranks it. Caveat: AI-upscale artifacts on some textures, and "some textures from CoD" makes redistribution gray — fine for personal/closed coop, not for bundling into a public release.
2. **Optional pairing: FAH Infantry HD Remaster** for higher-res character skins (the HD pack is weaker on infantry), if it ships TGA.
3. **Cleaner-license alternative: the Nexus ESRGAN 2K pack** — TGA-confirmed and clearer permissions, but **AA-only** and has known MP glitches (D-Day MP map breaks); acceptable for the SP/coop campaign but won't cover SH/BT.
4. **Avoid relying on** `openmoh/MOHAA-HD-Assets` (empty) and any **DDS-/PNG-only** pack (format support is conditional/absent in gl1).

**Before install, verify on the pack's download page:** (a) contents are TGA/JPG (not PNG; not DDS-only), (b) no `.scr/.tik/.bsp` and ideally no `.shader`, (c) license permits personal use.

## Risks
- **R1 (biggest): format mismatch** — PNG won't load in gl1; DDS only loads with S3TC; paletted/16-bit TGA hard-errors. Mitigation: TGA/JPG packs only; check log for image errors.
- **R2: VRAM / load time** — 2K–4K uncompressed uploads (S3TC not guaranteed); 20GB-class packs are heavy. Mitigation: JPG world art, `r_picmip 1`, or skip the largest packs.
- **R3: shader collisions / gameplay-visible surface changes** — only if a pack ships `.shader`; strip or inspect. Image-only packs are immune.
- **R4: redistribution/licensing** — MOHAA HD contains CoD-derived art; keep it personal-use, don't bundle into a public coop release.
- **R5: client cosmetic mismatch** (not a desync/kick — sv_pure ignored) — for visual consistency, all coop players should install the same pak.

## Sources
- https://www.moddb.com/mods/medal-of-honor-allied-assault-hd
- https://www.moddb.com/mods/medal-of-honor-allied-assault-hd/downloads/mohaa-hd-final
- https://www.gamepressure.com/download.asp?ID=58443
- https://www.moddb.com/mods/mohaa-complete-2x-remaster
- https://www.nexusmods.com/medalofhonoralliedassault/mods/2
- https://www.nexusmods.com/medalofhonoralliedassault/mods/9
- https://www.moddb.com/mods/enhanced-textures
- https://www.moddb.com/mods/hi-res-realism-texture-mod
- https://www.moddb.com/mods/fah-infantry-hd-remaster
- https://www.moddb.com/mods/moh-allied-assault-mp-textures-hd-1080p
- https://github.com/gabriellichacz/ESRGAN_MoHAA_auto
- https://github.com/openmoh/MOHAA-HD-Assets
- https://github.com/openmoh/openmohaa
- https://www.dsogaming.com/mods/call-of-juarez-medal-of-honor-allied-assault-get-ai-enhanced-hd-texture-packs/
