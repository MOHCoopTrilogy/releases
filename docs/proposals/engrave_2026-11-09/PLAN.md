# Gun engraving -> Customize bench (2026-11-09)

User: a personal engraving on any gun, knife-scratched, visible on every gun you hold. Expanded (user: "Yes whatever
makes the most sense to you"): a CUSTOMIZE bench in the Armory - engraving text plus insignia, plates, Medal of Honor
series emblems and US decorations, placed on predefined spots per gun, nudged, saved per gun.

## Where it stands (branch `engrave`: engine H:/hzm_work/eng-engrave, mod C:/mohaa-coop-dev/hzm-mod-engrave)
- **Image**: the client carves the text into a 1024x128 RGBA image (client/cl_engrave.cpp): 2-4 diverging knife-point
  passes per stroke, frayed edges, skips, slips, hand letterforms seeded from the text. RGB = 2x-modulate over the
  gun's own lit surface (pale raw wood), alpha = bright bare metal (steel shader). Re-carved only on change.
- **Renderer**: `re.SetDynamicImage(name, w, h, rgba)` (gl1 + gl2, tr_hzm_dynimage.c) - a named image from client
  pixels, kept across levels, rebuilt after the per-map image reset (gl2), re-sent after vid_restart.
- **Placement**: a flat quad model (models/hzm/engrave_quad.tik) drawn with the gun's render flags each frame
  (cgame/cg_engrave.c), so it is behind the hands, in the gun's depth range, and follows reload / recoil.
- **Anchors**: docs/tools/engrave/gen_engrave_anchors.py from the weapon mesh posed by the ENGINE's own bone frames
  and the measured first-person camera (cg_engraveDebug 1 -> collect_cams.py). Finding: at the hip the camera looks
  ALONG the gun, so big sides are seen at a glancing angle; the solver picks text directions by their on-screen
  baseline (<= 62 deg tilt), scores by letter height on screen, ray-casts against the gun, keeps the quad on screen.
- First in-game result: H:/hzm_work/engrave/eg_v2_zoom.jpg (Garand receiver side, MG42 top cover, shotgun receiver).

## Bench v1 - built 2026-11-09 (second session)
- **One placement table, two readers**: `qcommon/hzm_engrave_table.h` (header-only C) parses anchors + spots + uses, the decal
  list and the finish decals, and builds every quad for a gun (engraving, player emblems, finish emblems; max 6). The cgame
  (gun in hand) and the client (every Armory / bench model widget, via `CL_Engrave_AddToEntity` from `CL_Draw3DModel`) both use it.
- **Spots**: the solver names every hip-visible candidate patch (`stock_l/_r`, `receiver_l/_r`, `grip`, `top`, `butt`) and writes
  `spot <key> <name> o u v width mat lines sq du0 du1 dv0 dv1` (sq = largest square at the centre, the emblem size cap; du/dv =
  how far the centre may slide on the patch). The hand-checked anchor stays the `engrave` spot. A spot is "taken" when a placed
  quad has its name or sits on the same place under another name (`HZE_Taken`), so automatic picks never stack.
- **Emblems**: `docs/tools/engrave/gen_engrave_decals.py` -> `textures/hzm/decal/*.tga` (the finishes art, padded to one of the
  quad aspects 0.5 .. 8, never stretched), `scripts/hzm_decal.shader`, `scripts/hzm_decals.txt`. MOH series art (AA logo, BT
  logo, OSS seal, Croix de Guerre, Capture of Berlin) is NOT shipped: shaders point at the retail images, letterboxed with
  `tcMod transform` on a clampmap; the engine hides one whose image is missing (`need`).
- **Finish decals**: `scripts/hzm_finish_decals.txt` lines with the same finish + decal in a row are ALTERNATIVES - the first
  spot the gun has that is free wins, else the fallback order; one decal per group.
- **Bench UI**: Armory hero "CUSTOMIZE" -> `ui/coop_custom.urc` (generated, `gen_custom_urc.py`): the words field
  (`cl_engraveText`), tabs ENGRAVING / EMBLEM 1 / EMBLEM 2, emblem + spot steppers, move / tilt / size / mirror / centre,
  finish-emblem toggle, TURN OVER, RESET, SAVE, BACK. All controls are the client command `hzmcust`; unsaved edits live in
  `cl_custEdit` (+ `cl_custEditKey`) and show on the preview and on the gun in hand; SAVE writes archived `cl_cust_<key>`.
- **Legibility (22 px goal)**: 19/72 for long words; **33/72 for words of <= 10 letters** - those use the gun's
  `engrave_short` spot (two lines on a 2:1 quad, image engrave_dyn3 512x256, layout code 3) where it gives >10% bigger
  letters (34 guns, all hand-checked). A 3-line 8:3 layout and looser patches gained nothing.
- **Bench framing / ZOOM** (cl_engrave.cpp `CL_Engrave_ZoomEntity`): the bench ignores the hero transform's framing and
  centres the posed-mesh bounds (`bounds` lines from the solver) at any box shape; ZOOM turns the edited piece face-on and
  fills the box with it. Checked on 9 guns at 1920x1080 and 3440x1440 (H:/hzm_work/engrave/bench_stills2).
- **Hand check of spots**: cfg-only runs (docs/tools/engrave/qa/bench_run.py check_spots / check_short; cmd_wait is in MS,
  SP loads continue with `finishloadingscreen`); 17/188 emblem spots + 9 short spots failed and are dropped
  (merge_engrave_spots.py EG_SPOTFAIL). Emblems at the hip are small (top / butt slivers): the bench ZOOM is where they read.
- **Tool fixes**: gunmesh.read_skc_frame0 validated the SKAN header (10 min -> 3 s a gun, bug-10714); the solver keeps the
  40 largest patches; `merge_engrave_spots.py <checked report> <new reports> <out> <mod>` adds spots without moving a
  hand-checked anchor (never re-run --avoid against the current report, bug-10710).
- Per-gun string: `t <spot> du dv rot scale mirror ; d <decal> <spot> du dv rot scale mirror ; notext ; nofinish`.

## Bench design (decisions)
1. **Two decal paths, one source of truth (the anchor table)**:
   - v1 keeps the **quad decal** for everything (text and emblems): exact placement, no UV dependence, works on every
     gun now.
   - The **UV composite** (decal painted into a per-player copy of the gun's texture, picks up wear/finish) is the v2
     path. It needs (a) per-entity surface shader override (new refEntity fields, exe+cgame+renderers ship together),
     (b) the anchor's texels: every texel of the patch's triangles is mapped back to 3D and into the anchor's (u,v),
     (c) a **mirrored/shared-UV check**: many stocks map left and right onto the same texels; a shared spot would show
     the decal twice (once mirrored), so the tool marks such spots `quad-only`.
2. **Spots per gun**: the tool emits up to 6 named spots (stock L/R, receiver L/R, grip, buttplate) from the hip-visible
   patches, plus the region each may move within (the patch rectangle).
3. **Nudge**: move (along u/v), rotate (+-30 deg), scale (0.5-1.5), mirror; clamped so the quad stays inside its patch
   rectangle; re-checked against the hip occlusion data.
4. **Saved per gun**: `ui/coop_custom.cfg`-style archived cvars `cl_cust_<gunkey>` = "spot type id dx dy rot scale
   mirror on", plus `cl_engraveText`. Off switch per gun (`on`) and global (`cl_engrave`).
5. **Emblems**: art lives in the mod pak (finishes agent, docs/proposals/finishes2_2026-11-09/decals/) as RGBA with the
   same modulate/alpha convention. MOH series logos are read at RUNTIME from the player's own main/mainta/maintt paks
   (never shipped); Frontline only from the local converted pak and only when `coop_flHave` is set; a missing texture
   hides the emblem. US decorations (MoH Army, Purple Heart, Silver/Bronze Star, CIB, jump wings) as clean vector art.
6. **Preview**: Armory + weapon viewer draw the same quad on their model widget (uilib scene path, exe side) from the
   same anchor table.
7. **Others' guns (not v1)**: send `cl_engraveText` (and spot choice) in userinfo, an `cg_engraveOthers 0/1` option, a
   small blocklist filter applied by the RECEIVER, each client carves others' images only for guns in view (LRU of 4).

## QA gates
- `gen_engrave_anchors.py --check`: every holdable gun has >= 1 anchor or the build fails.
- In-game hand-occlusion check: the harness renders each gun with the quad in a flat debug colour and counts visible
  pixels against the projected area; < 85% visible = fail (hands are not in the offline mesh).
- Stills per class at 1080p and 3440x1440, a reload GIF, Armory entry.

## Decal API for finishes (coordinator 2026-11-09: asymmetric insignia go through the bench, not the texture)
34 guns share mirrored UVs left/right, so an asymmetric insignia painted into the texture would show reversed on one
side. Finishes' default decals are therefore drawn by the bench's quad system (geometry on the gun's bone, exactly like
the engraving), as preset placements per finish.

**Art** (finishes agent): `docs/proposals/finishes2_2026-11-09/decals/manifest.json` + PNGs, as now. The bench's pak
build converts each decal to `textures/hzm/decal/<name>.tga` (the largest file, RGBA, straight alpha) and one shader per
decal `textures/hzm/decal/<name>` (`blendFunc blend`, `rgbGen lightingSpherical`, `polygonOffset`, `cull none`, mipmapped),
so the decal takes the gun's lighting like the engraving. Orientation follows the manifest's `upright` field
("+s towards the muzzle, +t down" = the quad's +u is the gun's forward direction projected on the surface).

**Placements** (finishes agent writes, the bench reads): `scripts/hzm_finish_decals.txt`, one line per decal:
```
decal <finish> <decal name> <spot> <size> [<du> <dv> <rot> <mirror>]
```
- `<finish>`: the finish id the player has equipped (the tik suffix: `airborne`, `ffi`, `dak`, ... ; `*` = every finish).
- `<decal name>`: `name` in manifest.json.
- `<spot>`: a named anchor spot the bench generates per gun from the hip-visible surfaces: `stock_l`, `stock_r`,
  `receiver_l`, `receiver_r`, `grip`, `butt`, or `engrave` (the engraving's own spot). A gun without that spot falls
  back to the next in that order; with none, the decal is not drawn (never off the part).
- `<size>`: the decal's long side in game units (manifest `recommended_long_side_units` is the default when `-`).
- optional nudge in the spot's own frame: `du dv` in units along / up the surface, `rot` degrees, `mirror` 0/1;
  clamped so the quad stays inside the spot's patch rectangle.
Several lines per finish draw several decals. The player's own bench choices for that gun come after (and can switch a
finish decal off per gun: `cl_cust_<gun>` holds `nofinish`).

**Engine side** (bench): cg_engrave.c generalises to a small list of quads per gun (engraving + finish decals + player
decals, at most 6), each `{shader, spot, width, aspect, du, dv, rot, mirror}`, all placed from the same anchor table
(`scripts/hzm_engrave_anchors.txt` gains `spot <gun> <name> o u v width maxw maxh material` lines). Same render flags as
the gun, so every decal is behind the hands and follows reloads.
