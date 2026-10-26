#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t8 obj/obj_team3 oa,ob || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t8.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t8"
python ice_ingame.py e1l4 hb0 $R
python ice_ingame.py m5l2b rv0 $R
python ice_ingame.py m4l0 po0 $R
python ice_ingame.py m2l2a pa4 $R --gpu
python ice_ingame.py m6l2a a0,a9 $R --gpu
