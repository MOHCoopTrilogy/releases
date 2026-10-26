#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t24 m2l2a pa4 || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t24.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t24"
python ice_ingame.py m2l2b pb0,pbfin $R
python ice_ingame.py m5l2b rv3,rv4 $R
python ice_ingame.py m2l2b pbcut1 --gl1 --tag t24goff
python ice_ingame.py m2l2b pbcut1 --gl1 --shader --tag t24gon
python ice_ingame.py m6l2b b13 --gl1 --tag t24ioff
python ice_ingame.py m6l2b b13 --gl1 --shader --tag t24ion
