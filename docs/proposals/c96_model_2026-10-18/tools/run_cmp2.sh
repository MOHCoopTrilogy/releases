#!/bin/sh
# Short turn: compare still (old C96, new, P38, Luger, Colt, blued) + hip fire old vs new.
T="$1"; [ -z "$T" ] && T=j
D="$(cd "$(dirname "$0")" && pwd)"
OV='C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\build\ov_c96.pk3'
cd "$D"
run() { n="$1"; shift; C96_HUD="${C96_HUD:-2}" python run_c96.py "${T}${n}" --overlay "$OV" --cgame cgame_c96 --demoyaw 160 "$@" > "../build/run_${T}${n}.out" 2>&1; tail -1 ../build/run_h.log; }
run 1 --guns c96old,c96,p38,luger,colt45,c96_blued --parts yaw --hipstill
run 2 --guns c96old,c96 --parts demoy,demohip --nostand --demoreload 190
echo ALLDONE
