#!/bin/sh
# attic64_build.sh - v1.10.64 leftovers: attic63_build.sh with the brighter rack guns (attic_room_64b.blend, RACK_GUN_GAIN; bake64b = props
# alone, over the v1.10.63 bake63b), on top of the shipped v1.10.63 pak, and the weapon viewer re-wired after make_attic_polish.
# (The cancelled rack move, attic-64, used this file with bake64 props + bg; that bake was stopped.)
set -e; W=/h/hzm_work/attic62; T=/c/mohaa-coop-dev/docs/proposals/attic_polish_2026-11-02/tools; MOD=/c/mohaa-coop-dev/hzm-mod-attic
cp $W/bake63b/props.* $W/bake63b/bg.* $W/bake63b/projector.* $W/bake63b/medallid.* $W/bake/; cp $W/bake_reels_b/reels.* $W/bake/
cp $W/bake64b/props.* $W/bake/
cp $W/ship_v63_247d592e.pk3 $W/ship_base.pk3     # v1.10.64: on top of the shipped v1.10.63 pak (sha 247d592e)
cd /c/mohaa-coop-dev/docs/proposals/mphub3d_2026-11-02/newgame; python make_newgame3d.py --mod-ui 'C:\mohaa-coop-dev\hzm-mod-attic\ui' --attic-bake 'H:\hzm_work\attic62\bake' --stage 'H:\hzm_work\attic62\ng_stage' --pk3 'H:\hzm_work\attic62\ship_base.pk3' 2>&1 | grep '^{"bg"'
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/menus3d; python build_models2.py 'H:\hzm_work\attic62\bake' 'H:\hzm_work\attic62\stage62' --scale 52.5 | tail -1
cd $T; ATTIC62_BUILD='H:\hzm_work\attic62\stage62\build.json' python make_attic_polish.py 'C:\mohaa-coop-dev\hzm-mod-attic\ui' | tail -2
(cd /c/mohaa-coop-dev && HZM_MOD=C:/mohaa-coop-dev/hzm-mod-attic python docs/tools/gen_weapon_viewer.py build | tail -1)     # the viewer re-points the rack command (make_attic_polish writes a placeholder)
rm -rf $W/pkadd; mkdir -p $W/pkadd/models/menu $W/pkadd/textures/menu $W/pkadd/scripts
for g in floor fan projector props; do cp $W/stage62/models/menu/atc_$g[0-9]* $W/pkadd/models/menu/; done
cp $W/stage62/textures/menu/* $W/pkadd/textures/menu/; rm $W/pkadd/textures/menu/hzm_atc_wallmap.jpg; cp $W/stage62/scripts/hzm_atcscene.shader $W/pkadd/scripts/
python gen_fan_rotor.py "$W/bake" "$W/pkadd" "$W/rotor_axis.json" | tail -1; python gen_door_pane.py "$W/pkadd" | tail -1; python gen_clock.py "$W/pkadd" | tail -1
python gen_gram_model.py "$W/pkadd" >/dev/null; python gen_gram_art.py "$W/pkadd" >/dev/null; python gen_ng_tags.py "$W/pkadd" >/dev/null; python gen_glow.py "$W/pkadd" >/dev/null
python gen_projector_fx.py "$W/bake" "$W/stage62" "$W/pkadd" "$W/projector_reels.json" | tail -3
python gen_records3d.py "$W/bake" "$W/art" "$W/medalbox.json" "$W/pkadd" 'C:\mohaa-coop-dev\hzm-mod-attic\ui' | tail -1
RETOUCH_OPS=floor_lm,floor_alb,wall,phones FLOOR_ALB_PAK=/h/hzm_work/mpui/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3 python retouch.py "$W/bake" "$W/pkadd" | tail -1
python polish_pak.py "$W/ship_base.pk3" "$W/pkadd" "$W/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
