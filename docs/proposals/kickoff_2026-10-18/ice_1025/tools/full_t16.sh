#!/bin/bash
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t15.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t16"
python ice_ingame.py obj/obj_team3 oh1,oh3 $R
python ice_ingame.py m5l2b rv1,rv2 $R
