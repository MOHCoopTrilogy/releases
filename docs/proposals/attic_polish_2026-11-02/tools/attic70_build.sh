#!/bin/sh
# attic70_build.sh - v1.10.70: = the v1.10.69 pak (attic69_build.sh's ship69, sha 78c03994) +
#   1. OWN DISCS: gen_byodisc70.py (two piles of film cans on the projector's desk, FRONTLINE / EUROPEAN ASSAULT lid labels, + their lit copy) / patch_attic70.py (main.urc hotspot 19,
#      caption, proxy, fill light; the plain cans in the records / medals views)
#   3. gen_wallpins70.py: the attic's decorative push-pins cut out of atc_chrome1 (they sat over the U.S.S.R.)
#   2. the war map widened east to Stalingrad (sp3camp warmap.py WALL_WIN 31.5..67.5N, lon_c 15.85; missions.json tags re-placed):
#      warmap.py all -> ng_bake.py (the attic wall group re-baked through the attic bake, GPU: a CPU run lights it wrong, bug-10785) -> hzm_atc_wallmap.jpg (q95, as
#      build_models2 writes it) + make_ng3campaigns.py (hzm_newgame3d.urc pins / tags / toggle, the overlay, tags and the flat
#      briefing room's map; its textures are git-ignored in the mod, so they ride in this pak too)
# BLENDER=0 skips the bake (re-use $S/bake_wm). Run from Git-Bash. Never deploys anything.
set -e
W=/h/hzm_work/attic62; S=$W/ship70; MOD=/c/mohaa-coop-dev/hzm-mod-attic
T=${ATTIC_TOOLS:-/c/hzm-root-attic70/docs/proposals/attic_polish_2026-11-02/tools}; SP=$T/../../sp3camp_2026-11-08; NG=$T/../../mphub3d_2026-11-02/newgame
NE='C:\mohaa-coop-dev\docs\proposals\loadscreens_2026-10-18\data\ne'
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
mkdir -p $S
(cd $SP && python -P -E warmap.py all "$NE" "$(cygpath -w $S/warmap)" | tail -1)
if [ "${BLENDER:-1}" = "1" ]; then
  (cd $NG && nice -n 15 "$B" -b H:/hzm_archive/menuattic/export/attic_room.blend -t 4 --python ng_bake.py -- --map "$(cygpath -w $S/warmap/wallmap_ne.png)" \
     --out "$(cygpath -w $S/bake_wm)" --occ 'H:\hzm_work\ng\occ.json' > $S/bake_wm.log 2>&1) || { tail -5 $S/bake_wm.log; exit 1; }
fi
grep -q "all done" $S/bake_wm.log || { echo "the wall bake did not finish"; exit 1; }
cmp -s $S/bake_wm/wallmap.npz H:/hzm_work/ng/bake_wm_ne/wallmap.npz || echo "NOTE: the wall atlas layout differs from v1.10.69's - rebuild atc_wallmap1 with build_models2"
rm -rf $S/add70
cd $T
python gen_byodisc70.py $S/add70 $S/byo70.json | tail -1
python gen_wallpins70.py "$W/ship69/zzzzzzzzzzzzzz_hzm_menus3d.pk3" $S/add70 | tail -8      # the decorative push-pins off the map
python -c "from PIL import Image; Image.open(r'$(cygpath -w $S/bake_wm/wallmap.png)').convert('RGB').save(r'$(cygpath -w $S/add70/textures/menu/hzm_atc_wallmap.jpg)', quality=95)"
(cd $SP && python make_ng3campaigns.py --mod "$(cygpath -w $MOD)" --sheet "$(cygpath -w $S/warmap)" | tail -2)
git -C $MOD diff --quiet --ignore-cr-at-eol -- scripts/hzm_ng3campaigns.shader && git -C $MOD checkout -- scripts/hzm_ng3campaigns.shader
cp $MOD/textures/menu/hzm_ng3c_* $S/add70/textures/menu/
python patch_attic70.py "$MOD/ui" $S/byo70.json | tail -4
python polish_pak.py "$W/ship69/zzzzzzzzzzzzzz_hzm_menus3d.pk3" "$S/add70" "$S/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
sha256sum "$S/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
