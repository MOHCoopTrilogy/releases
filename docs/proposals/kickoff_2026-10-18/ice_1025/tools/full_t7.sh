#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t7 m2l2c pc10,pc6 --gpu || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t7.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t7"
python ice_ingame.py m2l2a pa4,pa8 $R
python ice_ingame.py m6l2a a0,a9 $R --variants "r_hzmWaterIce 0.5|r_hzmWaterIce 0.7|r_hzmWaterIce 1.1" --gpu
python ice_ingame.py m6l2b b13,b4 $R
python ice_ingame.py dm/mohdm5 md0 $R
