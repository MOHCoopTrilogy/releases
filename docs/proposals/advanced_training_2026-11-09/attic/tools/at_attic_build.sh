#!/bin/sh
# at_attic_build.sh - the TRAINING prop for the 3D attic (advtrain 2026-11-10): menus pak = the shipped v1.10.71 pak
# (H:\hzm_work\attic62\ship71, sha256 b3c953cd...) + the practice-target easel, and the urc side in the mod worktree.
#   1. gen_target_at.py  -> models/menu/hzm_at_target(.tik/.skd/.skc) + _lit, textures/menu/hzm_at_*, scripts/hzm_at_target.shader
#                           (placed by raycast against the baked room: feet on the floor, no part inside any room triangle)
#   2. patch_attic_at.py -> $MOD/ui/main.urc hotspot 20 "training" (appended LAST), caption, proxy, fill light, lit-copy swap;
#                           the plain easel in hzm_records3d.urc / hzm_medals3d.urc
#   3. gen_training_urc.py -> $MOD/ui/coop_training.urc (the two-card sheet: Basic Training / Advanced Training)
#   4. polish_pak.py ship71 + add -> $S/zzzzzzzzzzzzzz_hzm_menus3d.pk3 (deterministic: sorted entries, fixed timestamps)
# PREVIEW=1 also renders offline QA stills (atticview.py: home view with hit boxes, the lit copy, the fly-in close-up, the sheet).
# Never deploys anything; never writes under H:\hzm_work\attic62. Run from Git-Bash.
set -e
T=$(cd "$(dirname "$0")" && pwd)
BASEPAK=/h/hzm_work/attic62/ship71/zzzzzzzzzzzzzz_hzm_menus3d.pk3
W=/h/hzm_work/advtrain-ship; S=$W/ship_at; MOD=${AT_MOD:-/h/hzm_work/advtrain-mod}
POL=$T/../../../attic_polish_2026-11-02/tools/polish_pak.py
w() { cygpath -w "$1"; }
sha256sum "$BASEPAK" | grep -q '^b3c953cd' || { echo "base pak is not the shipped v1.10.71 one"; exit 1; }
mkdir -p $S; rm -rf $S/add_at
cd $T
python gen_target_at.py "$(w $S/add_at)" "$(w $S/target_at.json)" "$(w $BASEPAK)" "$(w $MOD/ui/main.urc)" 2>/dev/null | tail -3
python patch_attic_at.py "$(w $MOD/ui)" "$(w $S/target_at.json)"
python gen_training_urc.py "$(w $MOD/ui)"
python "$(w $POL)" "$(w $BASEPAK)" "$(w $S/add_at)" "$(w $S/zzzzzzzzzzzzzz_hzm_menus3d.pk3)"
sha256sum "$S/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
if [ "${PREVIEW:-0}" = "1" ]; then
  P=$S/prev; mkdir -p $P; PK="$(w $S/zzzzzzzzzzzzzz_hzm_menus3d.pk3)"; U="$(w $MOD/ui/main.urc)"
  FLY=$(python -c "import json;print(json.load(open(r'$(w $S/target_at_urc.json)'))['fly'])")
  nice -n 15 python atticview.py "$PK" "$U" "$(w $P/home_hot.png)" --hot --hl training | tail -1
  nice -n 15 python atticview.py "$PK" "$U" "$(w $P/home_lit.png)" --show hzm_at_target_lit --hide hzm_at_target --crop 0,380,640,860 | tail -1
  nice -n 15 python atticview.py "$PK" "$U" "$(w $P/fly.png)" --cam "$FLY" --size 1280x720 | tail -1
  python urc_preview.py "$(w $MOD/ui/coop_training.urc)" "$(w $P/fly.png)" "$(w $P/sheet.png)" cardAdv
fi
