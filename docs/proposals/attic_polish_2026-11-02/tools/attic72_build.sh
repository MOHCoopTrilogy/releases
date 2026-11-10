#!/bin/sh
# attic72_build.sh - v1.10.72 menus pak = the Advanced Training pak (at_attic_build.sh: ship71 b3c953cd + the TRAINING easel,
# sha 89deb29f) + the Live Operations war-map textures. make_ng3campaigns.py writes hzm_ng3c_* / hzm_ops_* into the mod's
# textures/menu (git-ignored); the menus pak sorts after the tex paks and already carries hzm_ng3c_*, so they must ride HERE
# (else the v1.10.70 overlay wins) and are then moved OUT of the mod tree (the tex pak baseline gate). The wall map
# (wallmap_ne.png) is unchanged from ship70, so no wall re-bake. Result sha 3343a976. Never deploys anything.
set -e
W=/h/hzm_work/rel172; MOD=/c/mohaa-coop-dev/hzm-mohaa-coop-mod; T=$(cd "$(dirname "$0")" && pwd)
SP=$T/../../sp3camp_2026-11-08; LO=$T/../../livemap_2026-11-09
NE='C:\mohaa-coop-dev\docs\proposals\loadscreens_2026-10-18\data\ne'
ATPAK=/h/hzm_work/advtrain-ship/ship_at/zzzzzzzzzzzzzz_hzm_menus3d.pk3
sha256sum "$ATPAK" | grep -q '^89deb29f' || { echo "AT pak is not 89deb29f"; exit 1; }
(cd $SP && python -P -E warmap.py all "$NE" "$(cygpath -w $W/warmap)" | tail -1)
(cd $LO && python -P -E gen_ops.py check --sheet "$(cygpath -w $W/warmap)" | grep '^problems')
(cd $SP && python make_ng3campaigns.py --mod "$(cygpath -w $MOD)" --sheet "$(cygpath -w $W/warmap)" | tail -2)
git -C $MOD diff --quiet --ignore-cr-at-eol -- scripts/hzm_ng3campaigns.shader && git -C $MOD checkout -- scripts/hzm_ng3campaigns.shader
rm -rf $W/add_ops; mkdir -p $W/add_ops/textures/menu
mv $MOD/textures/menu/hzm_ng3c_* $MOD/textures/menu/hzm_ops_* $W/add_ops/textures/menu/
python $T/polish_pak.py "$(cygpath -w $ATPAK)" "$(cygpath -w $W/add_ops)" "$(cygpath -w $W/ship72/zzzzzzzzzzzzzz_hzm_menus3d.pk3)"
sha256sum "$W/ship72/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
