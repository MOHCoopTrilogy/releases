# m3l2 ground: courtyard, barnyard and road (2026-09-29)

Status: **APPLIED 2026-10-04 (v7 texture), not deployed.** `zzzzzzzzzz_coop_m3l2ground.pk3` (sha256 28eebd04..., md5 aaf0e6ca) is in `hzm-mohaa-coop-mod\` (gitignored like every root pak; reproducible with `tools/gen_m3l2ground_pak.py build`), and build.ps1 / publish_release.ps1 copy/stage it. `python apply_m3l2ground.py --check` rebuilds the pak and runs every gate. v8 (work/build_v8) was an env-var experiment (HZM_MID_KEEP / HZM_PEBBLE, values unrecorded) and is NOT shipped: not reproducible. In-engine before/after: `evidence/ingame/` (`*_pair.jpg` = gl2 BEFORE over AFTER, `*_gl1_after.jpg` = gl1 fallback, `m3l3_road_control.jpg` = a map sharing the old road texture, identical with and without the pak, mean |diff| 0.01). Rig: `tools/m3l2g_ingame.py` (+ `M3L2G_VIEWS=a,b` to shoot a subset), pairs by `tools/ingame_pairs.py RUNDIR evidence/ingame`.

## What the user sees today, and why

| Place | Shader in the BSP | Image that actually loads | Problem |
|---|---|---|---|
| Road (66 curve patches) and courtyard / lanes (40 planar faces) | `textures/wilderness/m3l3grass_bocroad`. BT `tanatural.shader` (maintt pak1) remaps it | `m3l3grass_bocroad_new.dds` from **`zzzzzzzzzz_coop_hd_shadowfix.pk3`**: a 1024 sharpened upscale of the 512 BT art | Crunchy "worm" oversharpening (luma std 47 vs 39 retail). The art is a **road strip** with grass shoulders and dark rut bands |
| Courtyard between the house and the two outbuildings | the same road strip, laid as **4 separate side-by-side faces**. Each one restarts `t` (0.36→0.88, then 0.32, 0.23, 0.15 …) | same | Four copies of a road strip sit side by side. Rut and shoulder bands form parallel stripes, with hard jumps at x = -3840, -3728 and -3536. This is the user's "plopped side by side" |
| Barnyard at the late barn (-6700..-6150, -6880..-5820) | `textures/misc_outside/bocage_stevereq` (road gravel) | `zzzzzzzzzz_coop_hd_a_tilefix.pk3` | Repeats every **128 u**, so a readable grid of blotches across the yard |

Earlier fixes: bug-m3l2-ground-seams (self-tiling set2 / set2rad jpgs, in the assets_tex pak). bug-1129 rebuilt bocroad_new in `zzzzzzzz_hd_groundfix.pk3`, which is **dev-only and never shipped**. The shadowfix pak (09-08) later shipped the upscale again. The terrain pak's own bocroad_new (512) and bocroad (2048) are shadowed or never drawn. None of these fixes touched the layout, and the layout is the real cause.

## The fix

1. **A new farmyard surface** (`textures/hzm_m3l2/farmyard`, 2048², **world-projected** with `tcGen vector`, **512 u per repeat**, 4 px/u). The courtyard is about two repeats across and the per-face UV jumps no longer matter, so the four side-by-side strips are gone. The art is **periodic image quilting** of the packed-dirt parts of eight retail ground photographs (pinned by sha256). Every quilt pixel is a real photo pixel; no upscaler. Patches with strong blobs and re-used source spots are penalised. v7 adds a cleaning pass (single-pixel JPEG specks replaced by a 3x3 median, chroma smoothed, the 1-2 u oversharpened "worm" band halved) and a texel-level grain, because the raw quilt carried the retail JPEG's specks. Mean colour is matched to the shipped set2/set2rad dirt it meets.
2. **A new road** (`textures/hzm_m3l2/road`, 1024², the curves' own UVs), same soil, grass shoulders cut from the terrain grass it meets, faint wheel tracks.
3. **m3l2 only**: `maps/m3l2.bsp` gets a patched **shader lump** (tools/bsp_patch.py). Entries 58 and 286 (`m3l3grass_bocroad`) are renamed to the road name. TWO entries are appended: `farmyard` (courtyard faces) and `farmyard_b` (the 8 late-barn barnyard faces, formerly `bocage_stevereq`). They use the same image but their own `tcGen vector` pair, taken from each group's own BSP uv axes (the barnyard's uv is rotated about -19 degrees from the courtyard's), so gl2's generated relief, whose tangent frame comes from the BSP uv, is lit from the correct side on both. The shaderNum of 15 faces is re-pointed. Every other byte is identical: lightmap lump (`maps/m3l2.hzmlm` still applies), brushes, entities (`map_time`, so `m3l2.pth` still loads), static models. Other maps and every Omaha asset are untouched (see `evidence/map_usage.md`).

## Packaging

`zzzzzzzzzz_coop_m3l2ground.pk3` (6.65 MB) contains maps/m3l2.bsp, scripts/hzm_m3l2_ground.shader, textures/hzm_m3l2/{farmyard,road}.{dds,jpg}, CREDITS. DDS = DXT1 with a full mip chain from our own encoder; the jpg siblings are the gl2 relief source and the compression-off fallback. It ships outside `assets_tex` (no 1.3 GB re-download, bug-3251). The only other `maps/m3l2.bsp` is retail `main/Pak5.pk3`; every maintt pak mounts above main; all other names are new.

**Client/server alignment (corrected 2026-09-29):** the map CHECKSUM does NOT change. `CM_Checksum` (`cm_load.c:759`) returns the header's stored checksum field (bytes 8-11) and the patch never writes it. An old client joining a new server therefore still loads (and shows the old ground); the earlier "checksum mismatch" warning in this README was wrong. What still matters is pak alignment under sv_pure, which the auto-updater keeps aligned.

## Verification (see evidence/ingame/ for the images)
- `python apply_m3l2ground.py --check` rebuilds the pak in memory, byte-compares, and runs every gate: pinned retail BSP, only shader lump + 15 shaderNum words changed, lightmap lump identical, no other BSP references the new names, no Omaha member, DXT1/mips/encoder-lean, wrap seams, no clone (48 u patches, 8 orientations, best match > 0.9: 0%), mean colours vs the neighbours.
- Determinism: two builds are byte-identical.

## Files
- `tools/gen_m3l2ground_pak.py build|check`, `tools/gen_m3l2_ground.py`, `quilt.py`, `bsp_patch.py`, `clones.py`
- `tools/groundview.py`, `views.py`, `preview_pair.py`, `top_pair.py` - headless previewer (ground only)
- `tools/m3l2g_ingame.py` - in-engine before/after, private client `G:\mohaa-m3l2ground`
- `evidence/map_usage.md`, `evidence/headless/`, `evidence/ingame/`
- `staged/` - the pak, `gates.json`, full-size previews
