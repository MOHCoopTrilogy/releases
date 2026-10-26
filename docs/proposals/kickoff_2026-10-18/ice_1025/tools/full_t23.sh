#!/bin/bash
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t21.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t23"
python ice_ingame.py m2l2a pa4 $R
python ice_ingame.py m2l2b pb0,pbfin $R
