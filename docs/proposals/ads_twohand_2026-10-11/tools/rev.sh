#!/bin/sh
# rev.sh <webley|m10|nagant> <sheet.jpg> [w]   bake the aimed clips, build the overlay _ov_wip.pk3, offline centre-box check + sheet
D="$(cd "$(dirname "$0")" && pwd)"; G=$1; OUT=$2; W=${3:-320}
cd "$D/stage" || exit 1
A=models/human/animation/viewmodel
case $G in
 webley) for s in webley_ads webley_ads_slow; do python ../revbake.py $s . 2>&1 | grep -v "^work pose" ; done
   GUN=webley_revolver; AIM=$A/webley/webley_ads2h.skc
   PARTS="$A/webley/webley_reload_ads.skc|reload_ads_empty $A/webley/webley_reload_single_ads_slow.skc|reload_single $A/webley/webley_reload_end_ads.skc|reload_end_ads";;
 m10) for s in m10_ads m10_ads_empty m10_ads_slow; do python ../revbake.py $s . 2>&1 | grep -v "^work pose"; done
   GUN=s_w_m10_38; AIM=$A/coop_m10/m10_ads2h.skc
   PARTS="$A/coop_m10/m10_reload_empty_ads.skc|reload $A/coop_m10/m10_reload_ads.skc|reload $A/coop_m10/m10_reload_single_slow_ads.skc|reload_single $A/coop_m10/m10_reload_end_ads.skc|reload_end_ads";;
 nagant) for s in nagant_ads nagant_ads_slow; do python ../revbake.py $s . 2>&1 | grep -v "^work pose"; done
   GUN=nagant_revolver; AIM=$A/nagantrev/nagantrev_ads2h.skc
   PARTS="$A/nagantrev/nagantrev_reload_ads.skc|reload|11,31 $A/nagantrev/nagantrev_reload_single_slow_ads.skc|reload_single|0,27 $A/nagantrev/nagantrev_reload_end_ads.skc|reload_end|0,9";;
esac
sh ../build_ov.sh _ov_wip.pk3 | tail -1
IRONSIGHT_EXTRA_PAKS="$D/_ov_wip.pk3" python ../offbox.py $GUN $AIM $PARTS --w $W ${OUT:+--sheet "$D/$OUT"} --every ${EVERY:-2} --cols ${COLS:-8} 2>&1 | grep -v "^$"
