#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t11 m5l2b rv0 || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t11.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t11"
python ice_ingame.py obj/obj_team3 od $R
python ice_ingame.py lib/mp_bizerteharbor_lib hb1 $R
python ice_ingame.py m4l0 po0 $R
