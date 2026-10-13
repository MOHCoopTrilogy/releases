#!/bin/sh
# loff.sh <sheet> [every]   Luger: bake the reload hands, wip overlay, offline centre-box check + sheet of the EMPTY reload
D="$(cd "$(dirname "$0")" && pwd)"; W="$(cygpath -w "$D")"
cd "$D/stage" || exit 1
export IRONSIGHT_EXTRA_PAKS="$W\\_ov_wip.pk3;$W\\_bases.pk3"
python ../luger.py . gun,reload 2>&1 | grep "class pistol\|Error"
sh ../build_ov.sh _ov_wip.pk3 | tail -1
A=models/human/animation/viewmodel/pistol
python ../offbox.py luger_p08 $A/coop_luger_ads2h.skc "$A/coop_luger_reload_empty_ads.skc|reload_ads_empty" --w ${WW:-400} --sheet "$D/$1" --every ${2:-2} --cols ${COLS:-7} 2>&1 | grep -v "^$"
