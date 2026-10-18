#!/bin/sh
# Side-by-side proof turn (coordinator QA 2026-10-18): the new C96 next to the old one, the P38, the Luger, the Colt.
T="$1"; [ -z "$T" ] && T=h
D="$(cd "$(dirname "$0")" && pwd)"
OV='C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\build\ov_c96.pk3'
OVO='C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\build\ov_old.pk3'
cd "$D"
run() { n="$1"; ov="$2"; shift; shift; C96_HUD="${C96_HUD:-5}" python run_c96.py "${T}${n}" --overlay "$ov" --cgame cgame_c96 --demoyaw 160 "$@" > "../build/run_${T}${n}.out" 2>&1; tail -1 ../build/run_h.log; }
run 1 "$OV" --guns c96old,c96,p38,luger,colt45 --parts yaw --hipstill
run 2 "$OV" --guns c96old,c96 --parts demoy,demohip --nostand --demoreload 190
run 3 "$OV" --guns c96 --parts demoy --shots 2 --demoreload 190
run 4 "$OVO" --guns c96 --parts demoy --shots 2 --demoreload 190
run 5 "$OV" --guns c96_gold,c96_chrome,c96_blued,c96_bloody,c96_camo_woodland,c96_camo_winter,c96_camo_desert --parts yaw --hipstill
echo ALLDONE
