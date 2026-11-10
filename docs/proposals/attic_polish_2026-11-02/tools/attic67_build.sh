#!/bin/sh
# attic67_build.sh - v1.10.67: the gable window bigger (1.5 x 0.9 m) + the skylight in the left roof slope (attic67_edit.py ->
# attic_room_67.blend; bake67 = the room 'bg' re-baked with the real openings) + the window's outside (gen_wx_sky.py, wx_town.py's
# bake, gen_window_view.py) + its ambience. The v1.10.66 chain (attic66_build.sh) re-run from the v1.10.65 pak with bake67's bg.
set -e; W=/h/hzm_work/attic62; T=/c/mohaa-coop-dev/docs/proposals/attic_polish_2026-11-02/tools; MOD=/c/mohaa-coop-dev/hzm-mod-attic
cp $W/bake63b/props.* $W/bake63b/bg.* $W/bake63b/projector.* $W/bake63b/medallid.* $W/bake/; cp $W/bake_reels_b/reels.* $W/bake/
WM=${WM_BAKE:-H:/hzm_work/ng/bake_wm_ne}; [ -f "$WM/wallmap.png" ] || WM=H:/hzm_work/ng/bake_wm
cp "$WM"/wallmap.npz "$WM"/wallmap.png $W/bake/
cp $W/bake66/props.* $W/bake66/blueprint.* $W/bake66/desk.* $W/bake66/bg.* $W/bake66/projector.* $W/bake/; cp $W/bake66d/desk.* $W/bake66d/desk2.* $W/bake/; cp $W/bake66_reels/reels.* $W/bake/
cp $W/bake67/bg.* $W/bake/                       # v1.10.67: the room with the bigger gable window and the skylight
cp $W/ship_v65_cd492bc.pk3 $W/ship_base.pk3
python $T/crlf.py "$MOD/ui/main.urc"          # make_newgame3d wants CRLF (gen_weapon_viewer writes LF) - a failing pipe hid it
cd /c/mohaa-coop-dev/docs/proposals/mphub3d_2026-11-02/newgame; python make_newgame3d.py --mod-ui 'C:\mohaa-coop-dev\hzm-mod-attic\ui' --attic-bake 'H:\hzm_work\attic62\bake' --stage 'H:\hzm_work\attic62\ng_stage' --pk3 'H:\hzm_work\attic62\ship_base.pk3' --wm-bake "$WM" > $W/ng67.log 2>&1 || { tail -5 $W/ng67.log; exit 1; }
grep '^newgame3d' $W/ng67.log | cut -c1-160
# make_newgame3d's UI output is OLDER than the branch's (sp3camp's make_ng3campaigns.py regenerated hzm_newgame3d.urc after it):
# keep only its pak models, put the branch's UI files back (make_attic_polish adds the window lines to them below)
git -C $MOD checkout -- ui/hzm_newgame3d.urc ui/hzm_ng3d_aa1diff.urc ui/hzm_ng3d_aa2diff.urc ui/hzm_ng3d_aa3diff.urc ui/hzm_ng3d_aa4diff.urc ui/hzm_ng3d_aa5diff.urc ui/hzm_ng3d_aa6diff.urc ui/hzm_ng3d_bt1diff.urc ui/hzm_ng3d_bt2diff.urc ui/hzm_ng3d_bt3diff.urc ui/hzm_ng3d_sh1diff.urc ui/hzm_ng3d_sh2diff.urc ui/hzm_ng3d_sh3diff.urc
rm -f $MOD/ui/hzm_ng3d_mission1difficulty.urc $MOD/ui/hzm_ng3d_mission2difficulty.urc $MOD/ui/hzm_ng3d_mission3difficulty.urc
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/menus3d; python build_models2.py 'H:\hzm_work\attic62\bake' 'H:\hzm_work\attic62\stage62' --scale 52.5 | tail -1
cd $T; python gen_wx_sky.py H:/hzm_work/wx/sky | tail -1
rm -rf $W/wxadd; python gen_window_view.py ${WX_TOWN:-H:/hzm_work/wx/town} H:/hzm_work/wx/sky $W/ship_base.pk3 $W/wxadd | tail -3
[ -d $W/wxadd/models/menu ] || { echo "gen_window_view.py FAILED (its | tail hid the error)"; exit 1; }
ATTIC62_BUILD='H:\hzm_work\attic62\stage62\build.json' WX_JSON=H:/hzm_work/attic62/wxadd/wx_scene.json python make_attic_polish.py 'C:\mohaa-coop-dev\hzm-mod-attic\ui' | tail -2
(cd /c/mohaa-coop-dev && HZM_MOD=C:/mohaa-coop-dev/hzm-mod-attic python docs/tools/gen_weapon_viewer.py build | tail -1)
# the weapon viewer and the records / medals scenes copy every attic model but not the scenewx roles: the outside would draw untinted
# there (the strike's room wash at full white) - strip it from them
for f in hzm_wpnview.urc hzm_records3d.urc hzm_medals3d.urc; do sed -i '/models\/menu\/hzm_wx_/d; /^scenemodelcvar "hzm_wx_/d; /^scenewx "/d' $MOD/ui/$f; done
rm -rf $W/pkadd; mkdir -p $W/pkadd/models/menu $W/pkadd/textures/menu $W/pkadd/scripts
for g in floor fan projector props blueprint desk desk2; do cp $W/stage62/models/menu/atc_$g[0-9]* $W/pkadd/models/menu/; done
cp $W/stage62/textures/menu/* $W/pkadd/textures/menu/; rm $W/pkadd/textures/menu/hzm_atc_wallmap.jpg; cp $W/stage62/scripts/hzm_atcscene.shader $W/pkadd/scripts/
python gen_fan_rotor.py "$W/bake" "$W/pkadd" "$W/rotor_axis.json" | tail -1; python gen_door_pane.py "$W/pkadd" | tail -1; python gen_clock.py "$W/pkadd" | tail -1; CLOCK_PREFIX=hzm_hubclock CLOCK_CBU="0.95 5.325 2.55" CLOCK_R=0.16 CLOCK_BEZEL=0.205 python gen_clock.py "$W/pkadd" | tail -1
python gen_gram_model.py "$W/pkadd" >/dev/null; python gen_gram_art.py "$W/pkadd" >/dev/null; python gen_ng_tags.py "$W/pkadd" >/dev/null; python gen_glow.py "$W/pkadd" >/dev/null
python gen_dials.py "$W/bake" "$W/dials.json" "$W/pkadd" | tail -1
python gen_projector_fx.py "$W/bake" "$W/stage62" "$W/pkadd" "$W/projector_reels.json" | tail -3
python gen_records3d.py "$W/bake" "$W/art" "$W/medalbox.json" "$W/pkadd" 'C:\mohaa-coop-dev\hzm-mod-attic\ui' | tail -1
for f in hzm_wpnview.urc hzm_records3d.urc hzm_medals3d.urc; do sed -i '/models\/menu\/hzm_wx_/d; /^scenemodelcvar "hzm_wx_/d; /^scenewx "/d' $MOD/ui/$f; done      # (again: gen_records3d re-copies the models into records / medals)
RETOUCH_OPS=floor_lm,floor_alb,wall,phones,dials DIALS_JSON=H:/hzm_work/attic62/dials.json FLOOR_ALB_PAK=/h/hzm_work/mpui/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3 python retouch.py "$W/bake" "$W/pkadd" | tail -1
WALL_JPG=${WALL_JPG:-H:/hzm_work/ng3c_wallonly/variants/hzm_atc_wallmap_q95_420.jpg}
[ -f "$WALL_JPG" ] && cp "$WALL_JPG" $W/pkadd/textures/menu/hzm_atc_wallmap.jpg
ROOM_DIR=${ROOM_DIR:-H:/hzm_work/room_ne/stage/pk3/textures/mohmenu/hzm_room}
[ -d "$ROOM_DIR" ] && mkdir -p $W/pkadd/textures/mohmenu/hzm_room && cp "$ROOM_DIR"/* $W/pkadd/textures/mohmenu/hzm_room/
cp -r $W/wxadd/models $W/wxadd/textures $W/wxadd/scripts $W/wxadd/sound $W/pkadd/
python gen_ng_cut.py "$W/stage62" "$W/pkadd" "$MOD/ui" | tail -3      # the New Game view: no desk props in front of the war map
python polish_pak.py "$W/ship_base.pk3" "$W/pkadd" "$W/ship67/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
