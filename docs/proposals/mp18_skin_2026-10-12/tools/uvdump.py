"""MP18 survey: per surface of mp18.skd - triangle / vertex counts, bones, bone-space bounds, UV bounds,
texel coverage, UV overlap, and a UV wireframe drawn over the surface's current texture.
usage: python uvdump.py   (writes evidence/uv_<surface>.png + evidence/uvdump.json)"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import skd
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
EVI = os.path.join(HERE, "..", "evidence")
SURF_TEX = {"Tube1": "body.jpg", "Cube1": "stuff.jpg", "Plane1": "clip.jpg", "Cube3": "drum.jpg", "Cylinde0": "front.JPG"}


def main():
    os.makedirs(EVI, exist_ok=True)
    m = skd.read(open(os.path.join(MOD, "models/weapons/coop_mp18/mp18.skd"), "rb").read())
    out = {}
    for s in m["surfaces"]:
        name = s["name"]
        uv = np.array([v["uv"] for v in s["verts"]], float)
        pos = np.array([v["pos"] for v in s["verts"]], float)
        bones = sorted(set(v["bone"] for v in s["verts"]))
        tex = SURF_TEX.get(name)
        info = dict(tris=len(s["tris"]), verts=len(s["verts"]), bones=bones,
                    pos_min=pos.min(0).round(2).tolist(), pos_max=pos.max(0).round(2).tolist(),
                    uv_min=uv.min(0).round(3).tolist(), uv_max=uv.max(0).round(3).tolist(), tex=tex)
        if tex:
            p = os.path.join(MOD, "textures/coop_mp18", tex)
            im = Image.open(p).convert("RGB")
            a = np.asarray(im, float)
            info["tex_size"] = im.size
            info["tex_mean"] = a.mean((0, 1)).round(1).tolist()
            info["tex_sd"] = a.std((0, 1)).round(1).tolist()
            W = 1024
            big = im.resize((W, W), Image.LANCZOS)
            d = ImageDraw.Draw(big)
            cov = Image.new("I", (W, W), 0)
            cova = np.zeros((W, W), np.int32)
            area3 = 0.0; areauv = 0.0
            for t in s["tris"]:
                pts = [((uv[i][0] % 1.0) * W, (uv[i][1] % 1.0) * W) for i in t]
                d.line(pts + [pts[0]], fill=(0, 255, 0), width=1)
                one = Image.new("1", (W, W), 0)
                ImageDraw.Draw(one).polygon(pts, fill=1)
                cova += np.asarray(one, np.int32)
                a3 = np.linalg.norm(np.cross(pos[t[1]] - pos[t[0]], pos[t[2]] - pos[t[0]])) / 2
                e1 = uv[t[1]] - uv[t[0]]; e2 = uv[t[2]] - uv[t[0]]
                area3 += a3; areauv += abs(e1[0] * e2[1] - e1[1] * e2[0]) / 2
            big.save(os.path.join(EVI, "uv_%s.png" % name))
            info["uv_cover"] = round(float((cova > 0).mean()), 3)
            info["uv_overlap2"] = round(float((cova > 1).sum() / max(1, (cova > 0).sum())), 3)
            info["area3d"] = round(area3, 1); info["areauv"] = round(areauv, 4)
            info["uv_wraps"] = bool((uv.min() < -0.01) or (uv.max() > 1.01))
        out[name] = info
        print(name, json.dumps(info))
    json.dump(out, open(os.path.join(EVI, "uvdump.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
