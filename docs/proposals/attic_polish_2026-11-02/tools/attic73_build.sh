#!/bin/sh
# attic73_build.sh - v1.10.73 menus pak = the shipped v1.10.72 pak (rel172/ship72, sha 3343a976) +
#   (1) gen_shadows73.py: the rack's (MP room) and the projector screen's (attic) wall shadows, multiply -> alpha blend (bug-10768
#       follow-up): hzm_attic68.shader (only those two bodies) + hzm_hub_rackshade.tga + hzm_proj_screenshade.tga
#   (2) gen_mproom69.py re-run on ship72 for the 4th NOTICES sheet (PERSONAL BESTS): ONLY the files that differ from / are new to
#       ship72 are taken, and they must all be the notices' (asserted) - every other output of the generator is byte-identical
#   (3) gen_bests.py --add: the PERSONAL BESTS screen's three page backgrounds + hzm_pb.shader
#   (4) gen_rain73.py: the near rain sheet clipped out of the wing (rain indoors), tileable skylight drops + rivulets, seamless
#       cloud deck + a scud layer for LOOK UP (urc side: patch_wx73.py)
#   (5) close_hub73.py: hzm_hub_close - the MP room continued 120 u past its open front and capped (voidraster.py / voidprobe.py)
#   (6) close_ring73.py hzm_atc_close (the attic's open back end), crack_backer73.py hzm_atc_cracks (the wing's corner crack:
#       the user's 'white sliver'), gen_hatch73.py (the ladder hatch = QUIT GAME; the floor model gets its opening)
# The mod side (ui/multiplayer.urc + the room copies via patch_mproom69.py, ui/coop_pb.urc + coop_mod/bests_table.scr via
# gen_bests.py --mod) is committed on the mod branch; MOD= checks it is current. Result sha 58825b73. Never deploys anything.
set -e
W=/h/hzm_work/attic62; T=$(cd "$(dirname "$0")" && pwd); LB=$T/../../leaderboard_2026-11-10
MOD=${MOD:-/h/hzm_work/polish73-mod}
BASE=/h/hzm_work/rel172/ship72/zzzzzzzzzzzzzz_hzm_menus3d.pk3
sha256sum "$BASE" | grep -q '^3343a976' || { echo "base pak is not 3343a976"; exit 1; }
rm -rf $W/add73 $W/gen73 $W/pbchk $W/ship73/*.tmp; mkdir -p $W/add73 $W/pbchk/coop_mod $W/pbchk/ui
cd $T
python gen_shadows73.py "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)"
python gen_rain73.py "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)"      # rain out of the wing, skylight drops, sky scud
python close_hub73.py "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)"    # the MP room closed (urc side: patch_close73.py)
python close_ring73.py "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)" hzm_atc_close -52.5 60 21 100 atc_bg1,atc_bg2,atc_floor1   # the attic's open back end
python -P crack_backer73.py --from "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)" "$(cygpath -w $T/crack_backer73.json)" hzm_atc_cracks   # the wing's corner crack
python gen_hatch73.py "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)"     # the ladder hatch (QUIT GAME; urc side: patch_hatch73.py)
python gen_mproom69.py "$(cygpath -w $BASE)" "$(cygpath -w $W/gen73)" "$(cygpath -w $W/mproom73.json)" | tail -1
python - "$(cygpath -w $BASE)" "$(cygpath -w $W/gen73)" "$(cygpath -w $W/add73)" <<'EOF'
import os, re, shutil, sys, zipfile
z = zipfile.ZipFile(sys.argv[1]); names = set(z.namelist()); gen, add = sys.argv[2], sys.argv[3]; took = []
for r, _, fs in os.walk(gen):
    for f in fs:
        p = os.path.join(r, f); k = os.path.relpath(p, gen).replace(os.sep, "/"); b = open(p, "rb").read()
        if k in names and z.read(k) == b:
            continue
        assert re.fullmatch(r"models/menu/hzm_hub69_n_\w+\.(skd|skc|tik)|textures/menu/hzm_hub69_n_bests(_lit)?\.jpg|scripts/hzm_hub69\.shader", k), k
        os.makedirs(os.path.dirname(os.path.join(add, k)), exist_ok=True); shutil.copyfile(p, os.path.join(add, k)); took.append(k)
print("mproom73: took %d files (the notices)" % len(took))
EOF
python $LB/gen_bests.py --add "$(cygpath -w $W/add73)" --mod "$(cygpath -w $W/pbchk)"
cmp $W/pbchk/ui/coop_pb.urc $MOD/ui/coop_pb.urc && cmp $W/pbchk/coop_mod/bests_table.scr $MOD/coop_mod/bests_table.scr || { echo "mod coop_pb.urc / bests_table.scr stale: run gen_bests.py --mod"; exit 1; }
python polish_pak.py "$(cygpath -w $BASE)" "$(cygpath -w $W/add73)" "$(cygpath -w $W/ship73/zzzzzzzzzzzzzz_hzm_menus3d.pk3)"
sha256sum "$W/ship73/zzzzzzzzzzzzzz_hzm_menus3d.pk3"
