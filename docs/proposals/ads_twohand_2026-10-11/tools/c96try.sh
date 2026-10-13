#!/bin/sh
# c96try.sh <out.jpg> [frames a-b:step] [empty|loaded] [crop]  - env C96_* ; bake hands (+ gun with GUN=1), wip overlay, tiles WITH the server's props
D="$(cd "$(dirname "$0")" && pwd)"; W="$(cygpath -w "$D")"
export IRONSIGHT_EXTRA_PAKS="$W\\_ov_wip.pk3;$W\\_bases.pk3"
cd "$D/stage" || exit 1
python ../c96.py . reload${GUN:+,gun} 2>&1 | grep -i "error\|Traceback\|assert\|clip tag" | cut -c1-300 | sort -u
sh ../build_ov.sh _ov_wip.pk3 | tail -1
A=models/human/animation/viewmodel/pistol
if [ "${3:-empty}" = empty ]; then C=$A/coop_c96_reload_empty_ads.skc; G=reload_ads_empty; else C=$A/coop_c96_reload_ads.skc; G=reload_ads_loaded; fi
python ../c96view.py $C $G "$D/c96w/$1" --frames ${2:-36-52:4} --w ${WW:-640} --cols ${COLS:-5} --crop ${4:-0.1,0.3,0.9,1.0} --box --aim $A/coop_c96_ads2h.skc 2>&1 | tail -1
