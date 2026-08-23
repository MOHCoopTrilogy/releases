# Debris Pile + Overhead Marker Asset Hunt

Paks scanned: `G:/GOG/.../{main,mainta,maintt}/*.pk3`. Mod runs `fs_game=maintt`, so on AA maps only `main/*.pk3` + `maintt/*.pk3` load. Prefer **main** (always present) assets; `mainta` (SH) assets need re-aliasing and are flagged.

TGA header decode key: byte[2]=image type (2=uncompressed RGB(A)), bytes[12-13]=width LE, bytes[14-15]=height LE, byte[16]=bpp (24=no alpha, 32=alpha). Alpha presence further verified by sampling the alpha channel.

---

## HUNT 1 — destroyed radio/table replacement (debris/rubble pile)

Want a persistent solid mesh (classname static/object, NOT a one-shot FX emitter), roughly table-sized or bigger (~40-100 units across).

| Path | Theater | Class / type | bbox (QUAKED) @ scale | What it is |
|------|---------|--------------|------------------------|------------|
| **models/static/rubble_bigpile.tik** | **main** (always loads) | static_obstacle, skelmodel `rubble_bigpile.skb` + idle anim, scale 0.52 | `(-32 -32 0)(32 32 128)` = **64 x 64 footprint, 128 tall** | Collapsed pile of broken concrete/rubble + scattered boards. Solid persistent obstacle. **BEST FIT.** |
| models/static/rubble_smallpile.tik | main | static_obstacle, skelmodel `rubble_smallpile.skb`, scale 0.52 | `(-32 -32 0)(32 32 128)` (bbox same; mesh smaller) | Smaller rubble pile (bricks + concrete). Good if bigpile reads too tall; visually lower mass. |
| models/static/librarytabledestroyed.tik | main | static_furniture, skelmodel `librarytable.skd`, scale 0.52 | `(-8 -8 0)(8 8 16)` = 16 x 16 footprint | A *destroyed table* mesh. Thematically perfect (it WAS on a table) but small — better as a companion piece than the main pile. |
| models/static/loveseatdestroyed.tik | main | static_furniture, skelmodel `loveseat.skd`, scale 0.52 | `(-8 -8 0)(8 8 16)` | Wrecked furniture (sofa). Small; furniture-debris flavor only. |
| models/static/sandbag_large_semicircle.tik | main | static_obstacle, scale 0.52 | `(-56 -96 0)(64 104 56)` ~120 x 200 | Large but clearly a sandbag wall, not generic debris. Only if you want sandbag look. |

Rejected (too small / one-shot FX, per brief):
- `models/fx/chunkcrete.tik`, `models/fx/crates/crate-jib-*.tik` — small generic gibs (as noted).
- `models/fx/crates/debris_*.tik`, `models/fx/windows/debris_*.tik` — **one-shot sprite EMITTERS** (verified: `debris_3` spawns `cardboard-gib.spr` particles via `originspawn`, dummy skelmodel). Not persistent meshes.
- `models/fx/bp_debris1-3.tik` — small FX debris chunks, skelmodel exists but bbox `(-16 -16 0)(8 16 56)` and authored as `fx_misc_debris`, gravity/ScriptModel flavor. Too small/generic.
- `models/vehicles/*_destroyed*.tik`, `Panzer_destroyed*`, `tigertank_destroyed*`, `C47_Destroyed_*` — vehicle wreckage; way too big and theater = maintt/mainta. Wrong scale for a tabletop radio.

### TOP PICK (Hunt 1): `models/static/rubble_bigpile.tik`
main theater (always available), persistent static_obstacle skelmodel, 64x64x128 — reads as a collapsed blown-up debris pile, right size for replacing a radio+table. If it sits too tall, fall back to `rubble_smallpile.tik` (same family) and optionally drop `librarytabledestroyed.tik` beside/under it for the "the table got blown apart" read.

---

## HUNT 2 — overhead faction marker art

Current (looks "massive and ugly"):
- AXIS `textures/interior/ironcross.tga` — **128x128**, 32bpp. It's a large interior *detail* texture; far bigger than needed and reads as a plaque.
- ALLIED `textures/sprites/ampstar_white.tga` — **16x16, 24bpp = NO ALPHA**. This is the root cause of the "solid square": no transparency, and it isn't wrapped by any shader (verified: no `.shader` entry references it), so the engine draws the full opaque 16x16 quad. `ampstar.tga` / `ampstargreen` / `ampstaryellow` are also 16x16 24bpp (no alpha) — same problem.

### (a) Alpha cut-out texture options

| Path | Theater | Size / bpp | Alpha? (sampled) | What it is |
|------|---------|-----------|------------------|------------|
| **textures/hud/axis_headicon.tga** | **maintt** (the mod's own pk3) | 64x64, 32bpp | **YES** — transparent border + AA edges (sampled: ~368 fully transparent, 857 partial, 296 opaque per 4k px) | Clean cut-out AXIS head icon. Purpose-built for this. **BEST AXIS.** |
| **textures/hud/allies_headicon.tga** | **maintt** (mod pk3) | 64x64, 32bpp | **YES** — (368 transparent, 1153 partial, 373 opaque) | Clean cut-out ALLIED head icon. **BEST ALLIED.** |
| textures/interior/ironcross.tga | main | 128x128, 32bpp | YES (has alpha: 260 transparent / 192 partial sampled) — but it's a wall detail tex | Iron cross detail texture. Has alpha, but oversized; shrink-on-quad needed. Fallback only. |
| textures/flags/nazi1.tga | main | 128x256, 32bpp | yes | Nazi flag texture — too busy/rectangular for a small icon. |
| textures/decals/eagleglobe.tga | main | 128x256, 24bpp | NO | USMC eagle-globe decal, no alpha, rectangular. Not suitable. |

### (b) 3D insignia model options (attach above head instead of billboard)
- `models/static/static_nazibanner*.tik`, `static_naziflag*.tik`, `static_kriegsflag.tik`, `cranebanner.tik` (main) — full banners/flags, much too large and not camera-facing; not viable as a small head marker.
- No small standalone 3D iron-cross / star / eagle insignia model exists in any pak (searched `eagle|cross|flag|banner|pennant|star|insignia|emblem`). `models/static/nazieagle/` is only a texture, not a TIK. So the **billboard-quad approach with a proper alpha texture is the right path** — no good 3D substitute.

### TOP PICKS (Hunt 2)
The mod already ships the right assets; the bug is the *current texture choices*, not the billboard technique.
- **AXIS:** `textures/hud/axis_headicon.tga` — 64x64, 32bpp, real alpha cut-out (theater maintt, already loaded). Replace `textures/interior/ironcross.tga` with this.
- **ALLIED:** `textures/hud/allies_headicon.tga` — 64x64, 32bpp, real alpha cut-out (maintt). Replace `textures/sprites/ampstar_white.tga` (which has no alpha) with this.

Both are square 64x64 with transparent margins, so they will render as clean floating symbols at a small (~8-12 unit) quad size instead of opaque plaques. If the billboard still looks too big, that's a quad-size/scale issue in the spritegen shader, not the texture.
