#!/bin/sh
# One fair-queue turn: the proof runs in sequence on ONE private copy (C96_HUD, default 5), one client at a time.
#   sh run_final.sh <tag>        (call only while holding the harness_turn ticket "c96")
T="$1"; [ -z "$T" ] && T=f
D="$(cd "$(dirname "$0")" && pwd)"
OV='C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\build\ov_c96.pk3'
cd "$D"
run() { n="$1"; shift; C96_HUD="${C96_HUD:-5}" python run_c96.py "${T}${n}" --overlay "$OV" --cgame cgame_c96 --demoyaw 160 "$@" > "../build/run_${T}${n}.out" 2>&1; tail -1 ../build/run_h.log; }
run 1 --guns c96 --parts demoy,demohip --shots 2 --demoreload 190
run 2 --guns c96 --parts demoy --nostand --both --eshots c96=8 --demoreload 190 --demoreload_e 180
run 3 --guns c96 --parts yaw --tprel --shots 2 --demoreload 120
run 4 --guns c96_gold,c96_chrome,c96_blued,c96_bloody,c96_camo_woodland,c96_camo_winter,c96_camo_desert --parts yaw --hipstill
run 5 --guns c96 --parts yaw --tpc
echo ALLDONE
