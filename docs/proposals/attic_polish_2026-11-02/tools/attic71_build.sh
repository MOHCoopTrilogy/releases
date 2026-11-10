#!/bin/sh
# attic71_build.sh - v1.10.71 hotfix pak = the shipped v1.10.70 pak (ship70, sha 322799a5) + the card player's new loop
# (models/human/hzm_menu/hub_gi_menu.tik from gen_mproom69.py; nothing else of its output is taken - the rest of the MP room ships
# unchanged in ship70). The rack fix is urc-only (patch_mproom69.py -> the mod's ui/multiplayer.urc). Never deploys anything.
set -e; W=/h/hzm_work/attic62; T=$(cd "$(dirname "$0")" && pwd)
rm -rf $W/gen71 $W/add71; mkdir -p $W/add71/models/human/hzm_menu
cd $T
python gen_mproom69.py "$W/ship70/zzzzzzzzzzzzzz_hzm_menus3d.pk3" "$W/gen71" "$W/mproom71.json" | tail -1
cp $W/gen71/models/human/hzm_menu/hub_gi_menu.tik $W/add71/models/human/hzm_menu/
python polish_pak.py "$W/ship70/zzzzzzzzzzzzzz_hzm_menus3d.pk3" "$W/add71" "$W/ship71/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
sha256sum "$W/ship71/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
