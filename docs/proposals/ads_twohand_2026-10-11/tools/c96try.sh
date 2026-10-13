#!/bin/sh
# c96try.sh <out.jpg> [f0 f1 step] - env C96_* ; bake hands + gun, wip overlay, cropped key frames (emptied reload)
D="$(cd "$(dirname "$0")" && pwd)"; W="$(cygpath -w "$D")"
export IRONSIGHT_EXTRA_PAKS="$W\_ov_wip.pk3;$W\_bases.pk3"
cd "$D/stage" || exit 1
python ../c96.py . reload,gun 2>&1 | grep -i "error\|Traceback\|assert" | cut -c1-300
sh ../build_ov.sh _ov_wip.pk3 | tail -1
cd ..; python c96look.py "$1" ${2:-27} ${3:-51} ${4:-3} ${5:-empty} ${6:-0.15,0.30,0.85,1.0}
