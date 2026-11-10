#!/bin/sh
# attic62_build.sh - the v1.10.62 attic re-bake and rebuild, in order.  Step 2 is a ~40 min GPU job (Cycles, -t 4).  Each step is the project's own generator; nothing here edits by hand.
set -e
T=/c/mohaa-coop-dev/docs/proposals/attic_polish_2026-11-02/tools
M3=/c/mohaa-coop-dev/docs/proposals/kickoff_2026-10-18/menus3d
NG=/c/mohaa-coop-dev/docs/proposals/mphub3d_2026-11-02/newgame
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
W=H:/hzm_work/attic62
MOD=C:/mohaa-coop-dev/hzm-mod-attic           # branch attic-62

# 1. scene edits (CPU, seconds): door moved, doorway filled, jamb liners, props cut + stock imported, FIELD REPORT board, lamps,
#    phones -> bakelite, key-lamp rig prop removed.  Re-run any time; it always starts from the archived attic_room.blend.
python $T/export_stock.py "$W/stock" models/static/typewriter.tik models/static/smallfilecabinet.tik models/static/projector.tik \
    models/static/toolbox_closed.tik models/items/documents1a.tik models/items/documents2a.tik models/static/simplerectable.tik
python $T/gen_fieldreport_art.py "$W/art/fieldreport_board.png"
"$B" -b 'H:\hzm_archive\menuattic\export\attic_room.blend' -t 2 --python $T/attic62_edit.py -- "$W/stock" "$W/art" "$W/attic_room_62.blend"

# 2. THE BAKE (GPU, ~40 min; one heavy job; run at BelowNormal priority): only the groups the scene edits touch.  radio / nook / chalk
#    are unchanged and come from the shipped bake (bake_s5); the wall map from the New Game bake (bake_wm)
"$B" -b "$W/attic_room_62.blend" -t 4 --python $M3/attic_bake3.py -- --out "$W/bake" --nook     --groups floor,fan,chrome,bg,projector,props --bg 4096 --bg-spp 24
# the fan blades alone, visible to rays again (the room above baked without them: no frozen blade shadow)
"$B" -b "$W/attic_room_62.blend" -t 4 --python $T/rotor_visible.py --python $M3/attic_bake3.py -- --out "$W/bake_rotor" --groups rotor
cp "$W"/bake_rotor/rotor.* "$W/bake/"
S5=G:/mohaa-hudfeed3/menus3d/bake_s5
for f in radio.npz radio.png nook.npz nook.png chalk.npz chalk.png radios.json; do cp $S5/$f "$W/bake/"; done
cp H:/hzm_work/ng/bake_wm/wallmap.npz H:/hzm_work/ng/bake_wm/wallmap.png "$W/bake/"

# 3. models: every group (one shader file holds them all) -> stage62; the New Game step re-cuts bg / chrome (PINS) into the pak
python $M3/build_models2.py "$W/bake" "$W/stage62" --scale 52.5
cp H:/hzm_work/mpui/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3 "$W/ship_base.pk3"       # the MP-menu session's pak is the base
python $NG/make_newgame3d.py --mod-ui $MOD/ui --attic-bake "$W/bake" --stage "$W/ng_stage" --pk3 "$W/ship_base.pk3"
# 4. attic polish: main.urc (gramophone, hover box, FIELD REPORT + toolbox hotspots, idle chalk, button gating, WHAT'S NEW 4:3 twin,
#    v62 model lists from the build, moved briefing hotspot) + its pak files
ATTIC62_BUILD="$W/stage62/build.json" python $T/make_attic_polish.py $MOD/ui
rm -rf "$W/pkadd"; mkdir -p "$W/pkadd/models/menu" "$W/pkadd/textures/menu" "$W/pkadd/scripts"
for g in floor fan projector props; do cp "$W"/stage62/models/menu/atc_$g[0-9]* "$W/pkadd/models/menu/"; done
cp "$W"/stage62/textures/menu/* "$W/pkadd/textures/menu/"; cp "$W/stage62/scripts/hzm_atcscene.shader" "$W/pkadd/scripts/"
python $T/gen_fan_rotor.py "$W/bake" "$W/pkadd" "$W/rotor_axis.json" && python $T/gen_gram_model.py "$W/pkadd" && python $T/gen_gram_art.py "$W/pkadd" && python $T/gen_ng_tags.py "$W/pkadd" && python $T/gen_glow.py "$W/pkadd"
RETOUCH_OPS=floor_lm,floor_alb,wall,phones FLOOR_ALB_PAK="$W/ship_base.pk3" python $T/retouch.py "$W/bake" "$W/pkadd"
python $T/polish_pak.py "$W/ship_base.pk3" "$W/pkadd" "$W/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
# 5. harness (one client, non-primary monitor): survey 720 / 1080 / 219 / 43 / 43c + video, then make_contacts / make_crops / audit_sheet
