#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t18 obj/obj_team3 oh3,oh1,oe --gpu || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t18.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t18"
python ice_ingame.py m2l2b pb0,pbfin $R
python ice_ingame.py m2l2a pa4 $R
