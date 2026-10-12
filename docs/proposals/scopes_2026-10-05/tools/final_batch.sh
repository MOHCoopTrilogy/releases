#!/bin/sh
# batch5.sh - build + the FINAL set: cgame_scopes_g (ADS gate for scope-owned rifles) + gl2_scopes_b (ff369620)
S="C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/7ee3b4ee-deea-4563-b7bc-c7746a82f4e9/scratchpad"
sh "$S/scopes/build_scopes2.sh" cgame omohrenderergl2 > "$S/scopes/build_g.out" 2>&1 || { echo "BUILD FAILED"; exit 1; }
B=/c/mohaa-coop-dev/openmohaa-hzm-scopes2/.cmake/code
cp "$B/client/cgame/Release/cgame.dll" /g/mohaa-hudfeed/cgames/cgame_scopes_g.dll
cp "$B/renderercommon/renderergl2/Release/renderer_opengl2.dll" /g/mohaa-hudfeed/renderers/gl2_scopes_g.dll
md5sum /g/mohaa-hudfeed/cgames/cgame_scopes_g.dll /g/mohaa-hudfeed/renderers/gl2_scopes_g.dll /g/mohaa-hudfeed/renderers/gl2_scopes_b.dll
run() { n="$1"; shift; sh "$S/scopes/job.sh" python "$S/scopes/run_scopes2.py" "$@" > "$S/scopes/out_$n.txt" 2>&1; echo "done $n $(date +%T)"; }
export CG=cgame_scopes_g
export GL2NAME=gl2_scopes_g
run h_ease ease
run h_res720 res 1280x720
run h_variants variants
run h_mp mp
run h_res1080 res 1920x1080
run h_res43 res 1024x768
run h_resuw res 1920x804
run h_gl1 gl1 1280x720
run h_nopost nopost
run h_nopak nopak opengl2
run h_msaa8 msaa8
export SPIKE_MS=25
export EXTRA="set r_ignoreGLErrors 0"
GL2=G:/mohaa-hudfeed/renderers/gl2_scopes_g.dll sh "$S/scopes/job.sh" python "$S/bunker/spike_test.py" m3l1b 240 scopes_hb > "$S/scopes/out_h_spike_b.txt" 2>&1; echo "done h_spike_b $(date +%T)"
GL2=G:/mohaa-hudfeed/renderers/gl2_scopes_g.dll sh "$S/scopes/job.sh" python "$S/bunker/spike_test.py" m3l1a 150 scopes_ha > "$S/scopes/out_h_spike_a.txt" 2>&1; echo "done h_spike_a $(date +%T)"
CG=cgame_ship GL1NAME=gl1_ship run c_gl1strict_ship gl1strict
