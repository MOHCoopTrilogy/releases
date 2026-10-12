#!/bin/sh
# batch8.sh - (1) MSAA off at render scale 1 on the final pair; (2) is the +0.5 ms of Omaha "cl" on the final gl2 a
# property of the scope code or of the binary's layout? two gl2 builds of the FINAL source whose only change is extra
# comment text in the scope shader (it is embedded as a string), run on Omaha next to the final and first-build gl2.
S="C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/7ee3b4ee-deea-4563-b7bc-c7746a82f4e9/scratchpad"
W=/c/mohaa-coop-dev/openmohaa-hzm-scopes2
G=$W/code/renderergl2/glsl/hzmscope_fp.glsl
B=$W/.cmake/code/renderercommon/renderergl2/Release/renderer_opengl2.dll
R=/g/mohaa-hudfeed/renderers
pad() { python -c "
import io,sys
p=sys.argv[1]; n=int(sys.argv[2])
s=io.open(p,encoding='utf-8',newline='').read()
nl='\r\n' if '\r\n' in s else '\n'
s=s.rstrip('\r\n')+nl+nl.join('// layout probe padding line %03d - comment only, no code' % k for k in range(n))+nl
io.open(p,'w',encoding='utf-8',newline='').write(s)
" "$G" "$1"; }
pad 12; sh "$S/scopes/build_scopes2.sh" omohrenderergl2 > "$S/scopes/build_p1.out" 2>&1; cp "$B" $R/gl2_scopes_p1.dll
(cd $W && git checkout -- code/renderergl2/glsl/hzmscope_fp.glsl)
pad 40; sh "$S/scopes/build_scopes2.sh" omohrenderergl2 > "$S/scopes/build_p2.out" 2>&1; cp "$B" $R/gl2_scopes_p2.dll
(cd $W && git checkout -- code/renderergl2/glsl/hzmscope_fp.glsl)
sh "$S/scopes/build_scopes2.sh" omohrenderergl2 > "$S/scopes/build_final_again.out" 2>&1; cp "$B" $R/gl2_scopes_rebuilt.dll
md5sum $R/gl2_scopes_p1.dll $R/gl2_scopes_p2.dll $R/gl2_scopes_rebuilt.dll $R/gl2_scopes_g.dll
(cd $W && git status --short | head -3)
CG=cgame_scopes_g GL2NAME=gl2_scopes_g sh "$S/scopes/job.sh" python "$S/scopes/run_scopes2.py" msaa0 > "$S/scopes/out_k_msaa0.txt" 2>&1; echo "done msaa0 $(date +%T)"
export SPIKE_MS=25
export EXTRA="set r_ignoreGLErrors 0"
one() { CG=cgame_scopes_g GL2=G:/mohaa-hudfeed/renderers/$2.dll sh "$S/scopes/job.sh" python "$S/bunker/spike_test.py" m3l1a 150 $1 > "$S/scopes/out_k_$1.txt" 2>&1; echo "done $1 $(date +%T)"; }
one lay_p1 gl2_scopes_p1
one lay_A gl2_scopes
one lay_p2 gl2_scopes_p2
one lay_F gl2_scopes_g
