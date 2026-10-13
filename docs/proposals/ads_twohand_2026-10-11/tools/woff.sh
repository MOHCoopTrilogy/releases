#!/bin/sh
# woff.sh <what: cycle|reload|cycle,reload> <sheet prefix> [every]   Welrod: bake, wip overlay, offline centre-box check + sheet
D="$(cd "$(dirname "$0")" && pwd)"; W="$(cygpath -w "$D")"
cd "$D/stage" || exit 1
IRONSIGHT_EXTRA_PAKS="$W\\_ov_wip.pk3;$W\\_bases.pk3" python ../welrod.py . gun,$1 2>&1 | grep "class pistol"
sh ../build_ov.sh _ov_wip.pk3 | tail -1
A=models/human/animation/viewmodel/pistol
P=""
case "$1" in *cycle*) P="$P $A/coop_welrod_cycle_ads.skc|fire_ads";; esac
case "$1" in *reload*) P="$P $A/coop_welrod_reload_empty_ads.skc|reload_ads_empty";; esac
IRONSIGHT_EXTRA_PAKS="$W\\_ov_wip.pk3" python ../offbox.py welrod $A/coop_welrod_ads2h.skc $P --w ${WW:-400} --sheet "$D/$2" --every ${3:-2} --cols ${COLS:-7} 2>&1 | grep -v "^$"
