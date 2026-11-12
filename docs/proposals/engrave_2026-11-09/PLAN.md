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

## benchfix (v1.10.72, 2026-11-10) - user report on v1.10.71
- **Tilt**: the bench preview drag tilts too (modeltiltcvar cl_custTilt, +-60 deg, clamped in the drag and re-based at the
  limit; applied about the screen's horizontal axis before the bench's own framing, so TURN OVER and every screen shape
  stay framed; ZOOM keeps its face-on pose). `hzmcust tilt <deg>` / `spin <deg>` drive it in scripted QA.
- **MOVE over the whole face**: the solver writes, per spot, `face <key> <spot> u0 v0 cellu cellv nu nv <hex>` - the flat face
  the spot lies on as a <= 48 x 16 grid (on the patch, on screen at the hip, not hidden by the gun). The in-game tile check
  (`cg_engraveFaceCheck <spot>` -> ENGRAVETILE corners -> `check_faces.py`) clears the cells a hand covers
  (merge_engrave_spots.py EG_TILEFAIL). HZE_Place keeps the whole quad (size, tilt, mirror) on set cells; the bench stores
  where the piece really lands. Steps: < > 0.25, << >> 1.5, ^ v 0.1 units.
- HZE_MAX_USES 1024 -> 4096: a table with a use line per finish variant (1569) silently lost every gun past 1024.
- **Newer guns (benchfix 2)**: the 21 armory meshes added since the first solve (Bren, MP28, Panzerfaust, BAR/Lewis, the
  Pacific / Trench / G98 / P14 / Tommy variants) measured in game (cams_new), solved, merged with EG_ADDNEW and hand-checked
  (text 1 fail -> re-solved with --avoid, spots 4 dropped, face tiles 103 cleared). 93 anchors cover 1672 tiks; only the
  grenades have none. Inputs now live in data/ (cams.json, anchors_report.json) instead of a scratch folder.
- **Wood carvings**: the wood shaders take the stain away under the cut (alpha) and put lit raw wood back - pale on dark walnut.
- **"Dark preview" was a test-build artefact**: a fresh cmake configure defaults USE_RENDERER_DLOPEN OFF, which links the GL1
  renderer into the exe; GL1 lights menu models darker. Release builds load renderer_opengl2.dll and are as bright as v1.10.68.
- Legibility (22 px at 1080p): 23/93 long words, 44/93 words of <= 10 letters.

## Optics fix + free placement (2026-11-11) - user: "on some guns the engraving ends up on the scope", "I want to choose precisely where"
- **What a triangle is** (`docs/tools/engrave/gunclass.py`): metal / wood / optic / hand for every triangle, in skd order. An
  optic is found by surface or shader name, by a shader rule learned over all guns (two passes: the silenced Nagant's scope
  is the surface "Weas"), and by geometry (the piece that rings a lens, pieces inside the scope's capsule or hugging it, a
  tube welded into the rifle walked from the glass: the L42A1). Maps: H:/hzm_work/engrave/click/classes.
- **Solver**: optic triangles never join a candidate patch. `--classes <bad.json>` lists the anchors / spots of a report
  that sit on an optic, clears face cells over one and writes `tris <key> <count> <runs>` (run-length classes) into the
  table. `merge_engrave_spots.py` with `EG_ONLY=<bad.json>` replaces exactly the listed ones.
- **Result**: 27 anchors / spots were on an optic (14 guns; the default engraving on 8: arisakasniper, carcanosniper,
  g43sniper, mp44scoped, nagant_sniper, nagant_snipersilenced, springfield, svt_rifle). 20 re-solved, 7 dropped, the other
  303 byte-identical (data/optic_fix_2026-11-11.json). The new default spots on scoped guns are small (9-18 px letters at
  1080p): with the scope excluded little of the gun is in view at the hip. **The in-game hand check (check_visible /
  check_faces) of the 20 re-solved ones is still to do.**
- **Free placement**: a click on the bench's gun (`modelclickcommand "hzmcust click"` on the model widget, cl_uistd.cpp;
  `hzmcust clickf <fx> <fy>` for scripts) casts a ray through the preview's own projection against the mesh posed as the
  renderer poses it (cl_engrave.cpp CL_Bench_BuildMesh), in the gun's entity space. The quad is laid on the tangent plane at
  the hit (the smooth normal or the triangle's own, whichever carries the bigger piece), reading along the screen's right
  (snapped to the gun's long axis within 20 degrees), sized to the largest that has gun under 9 x 5 points of it (flush
  within +0.09 / -0.03 units, same facing, no optic / hand / magazine). Refused with a 4 s note: scope, hand, magazine or
  belt (it leaves the gun on a reload), the inside of the mesh, edge-on, no room.
- **String**: `tf o(3) u(3) n(3) width kind metal rot scale mirror` / `df <decal> o(3) u(3) n(3) width metal rot scale mirror`.
  `HZE_PlaceFree` builds the quad for every reader (bench, gun in hand); old strings build byte-identical quads (tested
  over 160 guns x 7 strings against the old header). MOVE walks the piece over the surface, TILT / SIZE / CENTRE are
  checked against the mesh, the SPOT stepper takes it back to a named spot, TURN OVER and ZOOM work as before.
- **Checked in a client** (private G:/mohaa-engrave, 1920x1080; stills H:/hzm_work/engrave/click): clicks6 = receiver,
  stock, magazine well, barrel shroud on the scoped StG44, M1 Garand, Thompson, Colt .45, MG42 (21 placements, scope and
  magazine clicks refused); hand1 = the same strings on the gun in hand (flat check quads); ops1 = move / tilt / size /
  mirror / centre / turn over / stepper / emblem. Not checked: a real mouse click (the scripted path enters at the
  command the widget sends), 3440x1440, other players' view.
- QA: `docs/tools/engrave/qa/click_run.py <tag> look|clicks|hand|ops <WxH> <display WxH>` (own home, binaries from the build
  tree, never under the user's game: harness_guard.user_game_running_raw()).
