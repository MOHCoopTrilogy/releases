#!/bin/sh
# attic69_build.sh - v1.10.69: the MP (join-game) room lived in. = the v1.10.68 pak (attic68_build.sh's ship68, or a fresh run of it
# with FULL68=1) + gen_mproom69.py (notice board, field radio, card table with a staged soldier, stove, corner clutter, contact
# shadows) + gen_posters68.py re-run (the back-wall poster onto the plaster, the poster shadows as an alpha blend) -> polish_pak.py.
# patch_mproom69.py writes the urc side into the mod worktree (multiplayer.urc, every hzm_mpui_scene_*.inc, hzm_wpnview.urc).
set -e; W=/h/hzm_work/attic62; T=/c/hzm-root-attic68/docs/proposals/attic_polish_2026-11-02/tools; MOD=/c/mohaa-coop-dev/hzm-mod-attic
[ "$FULL68" = "1" ] && sh $T/attic68_build.sh                       # (the whole v1.10.68 chain; it rewrites $W/ship68)
rm -rf $W/add69; mkdir -p $W/add69
cd $T
python gen_mproom69.py "$W/ship68/zzzzzzzzzzzzzz_hzm_menus3d.pk3" "$W/add69" "$W/mproom69.json" | tail -3
python -I gen_posters68.py "$W/add69" "$W/posters68.json" | tail -1
python patch_mproom69.py "$MOD/ui" "$W/mproom69.json" | tail -8
python polish_pak.py "$W/ship68/zzzzzzzzzzzzzz_hzm_menus3d.pk3" "$W/add69" "$W/ship69/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
sha256sum "$W/ship69/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
