#!/bin/sh
# attic66_build.sh - v1.10.66: the General's blueprint (attic62_edit section 11 -> attic_room_66.blend; bake66 = props + blueprint,
# over bake63b + bake_reels_b), on top of the shipped pak cd492bc3, the weapon viewer re-wired after make_attic_polish.
#
set -e; W=/h/hzm_work/attic62; T=/c/mohaa-coop-dev/docs/proposals/attic_polish_2026-11-02/tools; MOD=/c/mohaa-coop-dev/hzm-mod-attic
cp $W/bake63b/props.* $W/bake63b/bg.* $W/bake63b/projector.* $W/bake63b/medallid.* $W/bake/; cp $W/bake_reels_b/reels.* $W/bake/
WM=${WM_BAKE:-H:/hzm_work/ng/bake_wm_ne}; [ -f "$WM/wallmap.png" ] || WM=H:/hzm_work/ng/bake_wm     # v1.10.66: the shared Natural Earth wall map (spfix2) once it is baked
cp "$WM"/wallmap.npz "$WM"/wallmap.png $W/bake/
cp $W/bake66/props.* $W/bake66/blueprint.* $W/bake66/desk.* $W/bake66/bg.* $W/bake66/projector.* $W/bake/; cp $W/bake66d/desk.* $W/bake66d/desk2.* $W/bake/; cp $W/bake66_reels/reels.* $W/bake/
cp $W/ship_v65_cd492bc.pk3 $W/ship_base.pk3     # v1.10.66: on top of the shipped pak (sha cd492bc3)
cd /c/mohaa-coop-dev/docs/proposals/mphub3d_2026-11-02/newgame; python make_newgame3d.py --mod-ui 'C:\mohaa-coop-dev\hzm-mod-attic\ui' --attic-bake 'H:\hzm_work\attic62\bake' --stage 'H:\hzm_work\attic62\ng_stage' --pk3 'H:\hzm_work\attic62\ship_base.pk3' --wm-bake "$WM" 2>&1 | grep '^{"bg"'
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/menus3d; python build_models2.py 'H:\hzm_work\attic62\bake' 'H:\hzm_work\attic62\stage62' --scale 52.5 | tail -1
cd $T; ATTIC62_BUILD='H:\hzm_work\attic62\stage62\build.json' python make_attic_polish.py 'C:\mohaa-coop-dev\hzm-mod-attic\ui' | tail -2
(cd /c/mohaa-coop-dev && HZM_MOD=C:/mohaa-coop-dev/hzm-mod-attic python docs/tools/gen_weapon_viewer.py build | tail -1)     # the viewer re-points the rack command (make_attic_polish writes a placeholder)
rm -rf $W/pkadd; mkdir -p $W/pkadd/models/menu $W/pkadd/textures/menu $W/pkadd/scripts
for g in floor fan projector props blueprint desk desk2; do cp $W/stage62/models/menu/atc_$g[0-9]* $W/pkadd/models/menu/; done
cp $W/stage62/textures/menu/* $W/pkadd/textures/menu/; rm $W/pkadd/textures/menu/hzm_atc_wallmap.jpg; cp $W/stage62/scripts/hzm_atcscene.shader $W/pkadd/scripts/
python gen_fan_rotor.py "$W/bake" "$W/pkadd" "$W/rotor_axis.json" | tail -1; python gen_door_pane.py "$W/pkadd" | tail -1; python gen_clock.py "$W/pkadd" | tail -1; CLOCK_PREFIX=hzm_hubclock CLOCK_CBU="0.95 5.325 2.55" CLOCK_R=0.16 CLOCK_BEZEL=0.205 python gen_clock.py "$W/pkadd" | tail -1
python gen_gram_model.py "$W/pkadd" >/dev/null; python gen_gram_art.py "$W/pkadd" >/dev/null; python gen_ng_tags.py "$W/pkadd" >/dev/null; python gen_glow.py "$W/pkadd" >/dev/null
python gen_dials.py "$W/bake" "$W/dials.json" "$W/pkadd" | tail -1
python gen_projector_fx.py "$W/bake" "$W/stage62" "$W/pkadd" "$W/projector_reels.json" | tail -3
python gen_records3d.py "$W/bake" "$W/art" "$W/medalbox.json" "$W/pkadd" 'C:\mohaa-coop-dev\hzm-mod-attic\ui' | tail -1
RETOUCH_OPS=floor_lm,floor_alb,wall,phones,dials DIALS_JSON=H:/hzm_work/attic62/dials.json FLOOR_ALB_PAK=/h/hzm_work/mpui/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3 python retouch.py "$W/bake" "$W/pkadd" | tail -1
# the shared Natural Earth wall (spfix2): its own encoded wall texture (WALL_JPG, swappable for a label fix) over make_newgame3d's,
# and the flat main-menu room re-render (ROOM_DIR, textures/mohmenu/hzm_room/*: this pak loads after zzzzzzzzzzzz_coop_fixes2.pk3)
WALL_JPG=${WALL_JPG:-H:/hzm_work/ng3c_wallonly/variants/hzm_atc_wallmap_q95_420.jpg}
[ -f "$WALL_JPG" ] && cp "$WALL_JPG" $W/pkadd/textures/menu/hzm_atc_wallmap.jpg
ROOM_DIR=${ROOM_DIR:-H:/hzm_work/room_ne/stage/pk3/textures/mohmenu/hzm_room}
[ -d "$ROOM_DIR" ] && mkdir -p $W/pkadd/textures/mohmenu/hzm_room && cp "$ROOM_DIR"/* $W/pkadd/textures/mohmenu/hzm_room/
python polish_pak.py "$W/ship_base.pk3" "$W/pkadd" "$W/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
