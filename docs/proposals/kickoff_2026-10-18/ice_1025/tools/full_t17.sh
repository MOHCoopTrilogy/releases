#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t17 obj/obj_team3 oh1,oh3 || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t17.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t17"
python ice_ingame.py lib/mp_bizerteharbor_lib hb1 $R
python ice_ingame.py m5l2b rv1,rv2 $R
python ice_ingame.py m4l0 po0 $R
