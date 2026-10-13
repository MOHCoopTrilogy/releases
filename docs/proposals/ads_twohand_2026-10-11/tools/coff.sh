#!/bin/sh
# coff.sh <sheet> [every]   C96: gun clips + reload hands, wip overlay, offline centre-box check + sheet (empty, then loaded)
D="$(cd "$(dirname "$0")" && pwd)"; W="$(cygpath -w "$D")"
cd "$D/stage" || exit 1
export IRONSIGHT_EXTRA_PAKS="$W\\_ov_wip.pk3;$W\\_bases.pk3"
python ../c96.py . gun,reload 2>&1 | grep "class pistol\|Error\|c96 clips\|SPLIT\|assert\|Traceback"
sh ../build_ov.sh _ov_wip.pk3 | tail -1
A=models/human/animation/viewmodel/pistol
python ../offbox.py mauser_c96 $A/p38_ads2h.skc "$A/coop_c96_reload_empty_ads.skc|reload_ads_empty" "$A/coop_c96_reload_ads.skc|reload_ads_loaded" --w ${WW:-400} --sheet "$D/$1" --every ${2:-2} --cols ${COLS:-7} 2>&1 | grep -v "^$"
