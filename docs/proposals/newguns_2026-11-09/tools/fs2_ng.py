"""newguns: run the finishes2 bake tools against a PRIVATE staging copy (H:\\hzm_work\\newguns\\fs2_build), never the
finishes2 agent's H:\\hzm_work\\finishes2_build. The new guns' tiks / meshes come from the newguns wpnfix overlay (ng_assets.pk3).
    python fs2_ng.py build | rebake <coats> | layers | pack
"""
import os, sys
NG = r"H:\hzm_work\newguns"
STAGE = os.environ.get("HZM_FS2_BUILD") or os.path.join(NG, "fs2_build")   # [newguns2] env: a copy of the staging
os.environ.setdefault("IRONSIGHT_EXTRA_PAKS", os.path.join(NG, "fs2_tools", "ng_assets.pk3"))
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "finishes2_2026-11-09", "tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
sys.path.insert(0, TOOLS)
import fs2_build as B  # noqa: E402
B.STAGE = STAGE
import fs2_finish2 as F  # noqa: E402
F.STAGE = STAGE
STEMS = ["coop_bren", "coop_bergmann", "coop_panzerfaust"]
cmd = sys.argv[1]
if cmd == "build":
    sys.argv = ["fs2_build.py", os.path.join(NG, "fs2_tools", "roster3.tsv")] + STEMS
    B.main()
elif cmd == "rebake":
    F.rebake(sys.argv[2].split(","), set(STEMS))
elif cmd == "layers":
    F.layers()
elif cmd == "pack":
    F.pack()
