#!/bin/bash
cd /c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/ice_1025/tools
R="--renderer H:/hzm_work/ice1025_assets/renderer_opengl2_t8.dll --extglsl H:/hzm_work/ice1025_eng/code/renderergl2/glsl/hzmwater_fp.glsl --tag t9"
python ice_ingame.py obj/obj_team3 oc,ob $R
python ice_ingame.py lib/mp_bizerteharbor_lib hb1 $R
python ice_ingame.py m5l2b rv0 $R
python ice_ingame.py m4l0 po0 $R
python ice_ingame.py m2l2a pa4 $R
