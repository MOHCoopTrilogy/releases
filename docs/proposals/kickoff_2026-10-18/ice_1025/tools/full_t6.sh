#!/bin/bash
# one lock hold: build + sequential in-engine sessions. Log lines are the progress record (resumable by re-running one line).
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t6 m2l2b pbcut1,pbfin,pb0 --gif 24 || exit 1
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t6.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t6"
python ice_ingame.py m2l2a pa9,pa0 $R
python ice_ingame.py m6l2a a0,a9 $R
python ice_ingame.py m6l2b b13,b4 $R
