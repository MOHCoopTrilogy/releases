# v1.10.66 armoryfix: the Armory's gun previews at every resolution (2026-11-08)

Report: "the weapons view in the Loadout screen is still bad for some weapons including the actual primary 1 and 2 slots", also on SIDE
and NADE, and "the armory needs to work on my actual res" (3440x1440, `ui_menuCenter 0`).

Branches: mod `armoryfix` (off hotfix-1.10.53 61414171), engine `armoryfix-eng` (off rel-1.10.38-engine 0603a141; **client exe**
change, `cl_invrender.cpp` / `cl_uistd.cpp`). The wpnfix pak is unchanged.

## Causes

1. **Ultrawide (the user's screen):** the 640x480 menu is stretched to the screen, so at 21:9 every model box is 1.34x wider than at
   16:9. `CL_Draw3DModel` keeps 30 degrees across the box's longer side, and every Armory transform (`armory_hero_fit.tsv`,
   `armory_card_fit.tsv`) was measured at 1920x1080 - so at 3440x1440 each model grew 1.34x against the box height: the hero pistol
   and grenade lost their tops, and the SIDE / NADE / PRI tiles showed a cropped close-up (`media/uw3440_before_colt.jpg`).
2. **Stale framing tables:** measured 2026-10-18. The Lewis (81) and FG 42 irons (79) were never measured (fallback transform; the
   Lewis hero clipped at every resolution); the M3 Grease Gun's hero faced the other way from every other gun; the Mills bomb was a
   2D icon although its model renders since the v1.10.64 shader fix.
3. **Model variants** used their host's framing, though each is another mesh (1928 Tommy, Soares93 M38A, the WW1 imports...).

Not a cause: menu lighting (the same as the viewer's), the wpnfix pak's tiks (they load), and the hero drawing nothing. The empty hero
in the old Lewis still was the Lewis drawn out of the box.

## Fixes

- **engine `modelfitaspect <A>`** (widget property): a model box wider than it was at screen aspect A keeps that aspect's VERTICAL
  angle, so the model has the same size against the box height, centred, with more room left and right. A narrower box (4:3) keeps
  the old 30 degrees across the width. Default 0 = no change for any other widget.
- `gen_armory_urc.py` puts `modelfitaspect 1.7778` on every Armory model widget: the hero, the 18 card guns, the PRI 1 / PRI 2 /
  SIDE / NADE tiles and the helmet preview.
- **re-measured framing** (`tools/armory_fit.py` = the 10-18 `hero_fit.py` solver with its own state; `tools/fit_render.py` renders
  its jobs on the private client):
  - hero 76/76 and card / slot 76/76 converged, now including 66, 79 and 81; the M3 faces the same way as everything else;
  - a NEW per-variant hero table, `docs/tools/armory_variant_fit.tsv` (81/81). `wire_mv2.py` writes it into the variant chain
    pages, and the standard entry puts the host's framing back.
- the Mills bomb shows its 3D model (`gen_loadout.py` ICON2D empty).

## QA (private client on DISPLAY2, 0 Script Errors every run)

`tools/armory_audit.py` opens the Armory, inspects every gun and commits it to its slot, then frames every tab. Resolutions:
- 4:3 1440x1080
- 16:9 1920x1080
- 21:9 1920x804
- **true 3440x1440**: the background-window policy's clamp is undone, so the window overhangs DISPLAY2 and the framebuffer is
  3440x1440. No primary-display run was needed.

- `media/before_after_all_resolutions.jpg`: 11 guns (rifle, drum SMG, Lewis, MG42, bazooka, Colt, Webley, Hi-Standard, M2 frag,
  Mills, Nebelhandgranate) in hero and slot tile, before / after at all four resolutions. The 21:9 hero crops are squeezed to the
  sheet's column width.
- `media/hero_before.jpg` / `hero_after_1080.jpg`, `hero_before_uw.jpg` / `hero_after_uw.jpg`: all 76 hero renders.
- `media/slots_before*.jpg` / `slots_after*.jpg`: all 76 slot tiles.
- `media/uw3440_before_colt.jpg` / `uw3440_after_colt.jpg`: a full 3440x1440 Armory frame.

Gates: gen_loadout check EXACT, gen_lktab EXACT, gen_weapon_viewer 0 stale, check_mp_isolation 22/0.

Still flat, by art not framing: the M3 Grease Gun's grey parkerizing is close to the box's backdrop colour.
