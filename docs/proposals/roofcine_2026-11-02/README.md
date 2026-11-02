# Norway ending: roof blasts, roof holes, no "tables" (2026-11-02, branch `roof-cine`)

User 2026-11-02: *"When the building blows up at the end, it looks like three giant tables appear on top of the structure? What is that?
The explosion effects are supposed to be also happening at the top of the concrete building, giant fireballs from the explosions blowing
holes in the roof."*

## What the "tables" were
The **interiors of the five top-tier wall breaches** (sites 6, 18, 19, 20, 21) of map v7/v7b. The breach builder sizes an interior's
box from the panel: for a wall whose u axis is world z, `ucr = centre + (panel height + 240) / 2`, which for the top tier (z 1000..1190)
is z 1310 - **95 u above the concrete building's 1216 roofline**. When `cin_breach` showed `breach_N_interior`, its ceiling and the top of
its back wall stood up behind the parapet as a flat, warm-tinted (fire-lit vertex colour) slab, one per site: brown boxes on the skyline
that never go away. Measured from the shipped BSP (`maps/m2l3.bsp` ff151fa1): interior max z 1311 for exactly those five, every other
interior <= 1061.

Contributing (transient, not the slabs): `barracks_explosion` / `aircraft_explosion` throw `metal_section` / `ibeam_piece` tempmodels
that scale with the emitter; at the roof blasts' 7-22x they are house-sized plates for 1-2 s.

## Fixes
* **Map v9** - top-tier interiors capped: `int_ceil 1206` (closed ceiling under the roof) + `int_zmax 1210` (clip pass). Max z now 1210.
* **Script** (`coop_mod/finale_m2l3_cine.scr`):
  * `cin_fx`: above scale 2.2 the two debris-throwing emitters are swapped for `explosion_bridge` (sprites only).
  * `cin_breach`: an interior whose top rises past z 1214 is not shown (an un-updated v7 map gets holes with no slabs).
  * `cin_debris`: a piece that never lands within 6 s is removed (no hanging debris); one that lands on the concrete building
    (z > 880) is removed after 0.6 s.
  * `cin_notch` (new): the roof eruption at a notch site - swap under the flash, a giant fireball column fed for 6-7 s,
    fire + smoke in the bite, concrete/metal chips only (`cin_roofchips`).
  * `cin_oneshot`: the tank-room blast also blows notch 25; each of the four following roof blasts blows notch 24, 26, 23, 27.

## Roof holes - how they are made (real geometry, same pipeline as the facade breaches)
The roof plane is never in view from the one-shot camera (it sits on the train roof, ~15 deg below the roofline), so a hole in the roof
has to read as a **bite out of the skyline**. New breach kind `notch` in the builder (`tools/v7/make_chunks5.py`, generated from the v7
builder by `tools/patch_v9.py`):
* the panel is the whole top tier (brush 1993, y 3080..3176, z 960..1216) between two x bounds; it is doubled upward (virtual
  z 960..1472), the ragged hole (`make_hole2`: lobes, cracks, chips, spalled edges, rebar, scorch ring, soot streaks) is centred on the
  real top edge, then **every surface of `breach_N_damaged` is clipped at z 1216** - a jagged U bitten out of the roofline, the wall
  thickness showing in its flanks, front faces on the stock texture + lightmap. Surface-only (no collision; nobody stands up there).
* `breach_N_interior` = the gutted room behind it (the builder's interior), clipped at z 1202: no ceiling - the roof is gone.
* `breach_N_intact` = the carved stock piece (looks and collides as stock until the swap).

| site | x range | chunk | notes |
|---|---|---|---|
| 23 | -2640..-2010 | crumble_facade_4 | between top-tier sites 18 and 6 |
| 24 | -1440..-860 | crumble_facade_5 | between 6 and 19 |
| 25 | -250..370 | crumble_facade_6 | in front of the tank room; the first, biggest blast |
| 26 | 940..1290 | crumble_facade_7 | east end |
| 27 | -3660..-3205 | crumble_facade_3 | between 21 and 18 |

No box crosses a chunk cut (-3200, -2000, -800, 400) or another breach box.

## Reproduce (byte-exact)
```
python tools/mk_v9spec.py H:\hzm_work\maprebuild\v7_s3.json H:\hzm_work\maprebuild\v7_s4.json <out>
python tools/v7/make_chunks5.py <out>/v9_s3.json      # base: H:\hzm_work\maprebuild\v4\c2.bsp (md5 da3e482b...)
python tools/v7/make_pclip.py   <out>/v9_s4.json
python tools/v7b_ents.py <out>/c4.bsp <out>/m2l3.bsp   # the v7 -> v7b "+broadcast" entity step (list: tools/v7b_broadcast.txt)
```
`tools/v7/` is a frozen copy of the v7 builder set (`make_chunks4_v7.py`, `breachgeo.py` = `breachgeo_v7.py`, ...). Proof it is the
real thing: the v7 spec through it, then `make_pclip` and `v7b_ents`, gives the shipped map byte for byte (md5 ff151fa1); and
`make_chunks5.py` with the v7 spec gives the v7 `c3.bsp` byte for byte (8d373a1a) - the new keys change nothing unless used.
(The working copies `maprebuild_1025/tools/make_chunks4.py` / `breachgeo.py` were edited after v7 and no longer reproduce it.)

## Map file and how it ships
| file | bytes | md5 |
|---|---|---|
| v9 `maps/m2l3.bsp` | 14,895,440 | `30c4a952803bc981f49f2c7332e2df62` |
| `maps/m2l3.pth` (unchanged from v7b) | 99,012 | `ae0f4e18710f8b4e1060878d0123cd30` |
| v7b `maps/m2l3.bsp` (shipped today, kept) | 14,548,184 | `ff151fa112131f3b0b6cd323528910f3` |

The map ships in `hzm-mohaa-coop-mod\zzzzzzzzzz_coop_maps.pk3` (git-ignored, copied by build.ps1 and staged by publish_release.ps1).
Candidate pak with only `maps/m2l3.bsp` replaced: `H:\hzm_work\roofcine\zzzzzzzzzz_coop_maps.pk3`. To ship: copy it over the mod
checkout's pak in the release that carries the script (the original stays at `H:\hzm_work\maprebuild\v7b\maps\m2l3.bsp`).
Script and map are independent in both directions: new script + v7b map = no notches (cin_notch no-ops), top-tier interiors stay
hidden; old script + v9 map = the v7 ending without the slabs (notch sites stay intact).
Model numbers moved (append order: the new sites sit in their chunks' sequence); nothing in the mod references m2l3 `*N` numbers and
there is no `cmpatch/m2l3*.txt`.
