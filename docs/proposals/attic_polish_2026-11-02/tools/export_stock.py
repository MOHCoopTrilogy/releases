"""export_stock.py <out dir> <tik> [<tik> ...] - stock MOHAA / SH / BT models -> OBJ + MTL + PNG for the attic Blender scene (v1.10.62).

Each model is posed and scaled exactly as the game shows it (gen_gram_model.load: frame-0 bone pose + tik scale, game units),
written in game units with Z up; attic62_edit.py imports it, scales by 1/52.5 to Blender metres and places it.  The textures are
each surface's first shader stage (stock_preview.texture), saved as PNG beside the OBJ.  CPU only."""
import os, sys
import numpy as np
from PIL import Image

H_ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H_)
_argv = sys.argv
sys.argv = [sys.argv[0], "x"]
import stock_preview as SPV  # noqa: E402
sys.argv = _argv

out = sys.argv[1]
for tik in sys.argv[2:]:
    name = os.path.splitext(os.path.basename(tik))[0]
    d = os.path.join(out, name)
    os.makedirs(d, exist_ok=True)
    surfs = SPV.load(tik)
    # EXPORT_SKIP_SHADERS: comma list of shaders left out (the weapons' loose ammo clip surfaces, m1clip, sit off the gun)
    _skip = [x.strip().lower() for x in os.environ.get("EXPORT_SKIP_SHADERS", "").split(",") if x.strip()]
    surfs = [x for x in surfs if (x["shader"] or "").lower() not in _skip]
    obj = ["mtllib %s.mtl" % name]
    mtl = []
    vo = 1
    for k, s in enumerate(surfs):
        mat = "%s_%d" % (name, k)
        tex = SPV.texture(s["shader"]) if s["shader"] else None
        mtl += ["newmtl %s" % mat, "Kd 1 1 1"]
        if tex is not None:
            fn = "%s.png" % mat
            Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8)).save(os.path.join(d, fn))
            mtl.append("map_Kd %s" % fn)
        mtl.append("")
        obj.append("o %s" % mat)
        for p in s["P"]:
            obj.append("v %.5f %.5f %.5f" % tuple(p))
        for uv in s["U"]:
            obj.append("vt %.5f %.5f" % (uv[0], 1.0 - uv[1]))      # skd t runs down the image, OBJ v runs up
        for n in s["N"]:
            obj.append("vn %.5f %.5f %.5f" % tuple(n))
        obj.append("usemtl %s" % mat)
        for t in s["tris"]:
            a, b, c = (int(i) + vo for i in t)
            obj.append("f %d/%d/%d %d/%d/%d %d/%d/%d" % (a, a, a, c, c, c, b, b, b))     # retail winding is clockwise
        vo += len(s["P"])
    open(os.path.join(d, name + ".obj"), "w").write("\n".join(obj) + "\n")
    open(os.path.join(d, name + ".mtl"), "w").write("\n".join(mtl) + "\n")
    P = np.vstack([s["P"] for s in surfs])
    print("%-22s %4d tris  size %.1f x %.1f x %.1f u  min %s" % (name, sum(len(s["tris"]) for s in surfs), *(P.max(0) - P.min(0)), np.round(P.min(0), 1)))
