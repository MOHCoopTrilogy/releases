"""Re-bake the BAKED weapon finishes (bloody + 3 camos) from the new HD base sheets.

    python docs/tools/weapon_hd/build_finishes.py            all baked finish textures -> stage/fin + QA cards
    python docs/tools/weapon_hd/build_finishes.py --only colt45

Today they are 128-620 px (bake_skins.py baked them from the stock 256-512 sheets in 2026-08), next to a gun that is
now 2048-4096: a camo gun would look far softer than its plain twin. Gold / chrome / blued are shader stages over the
base diffuse and inherit the HD sheet with no work. The bake functions are bake_skins.py's own (tuned with the user,
bug-1901/1913): the base is split into a low-frequency shading term and a high-frequency detail term and only the hue
is replaced. Output 1024 on the long side (the approved ~175 MB scope), DXT1 + full mips, named <same stem>.dds so it
wins over today's .jpg (R_LoadImage probes .dds first). Base = the HD sheet WITH its seeded wear (row 0), so a bloody
or camo gun keeps the same chips and scratches as the plain one.
"""
import os, sys, io, re, json, argparse, hashlib
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import vfs
import build_sheets as B

_bs = io.open(os.path.join(os.path.dirname(HERE), "bake_skins.py"), encoding="utf-8").read()
_ns = {"__file__": os.path.join(os.path.dirname(HERE), "bake_skins.py")}
exec(_bs.split("def make_envmap(")[0], _ns)           # BAKED + the tuned image functions, no driver
BAKED = _ns["BAKED"]
CAMO = {   # palettes + seeds exactly as bake_skins.BAKED (the user-tuned values)
    "camo_woodland": ([(58, 66, 40), (86, 92, 56), (44, 40, 30), (104, 98, 66)], 3),
    "camo_winter": ([(178, 182, 186), (140, 146, 152), (96, 102, 108), (206, 210, 213)], 11),
    "camo_desert": ([(176, 150, 104), (146, 120, 78), (198, 178, 138), (118, 98, 66)], 5),
}
OUT = os.path.join(B.BUILD, "stage", "fin")
QA = os.path.join(B.BUILD, "qa", "fin")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); a = ap.parse_args()
    jobs = json.load(open(os.path.join(HERE, "jobs.json")))
    by_base = {}
    for j in jobs:
        by_base.setdefault(os.path.basename(j["stem"]), []).append(j)
    idx = vfs.index()
    targets = sorted({re.sub(r"\.(jpg|tga|png|dds)$", "", k) for k in idx
                      if k.startswith("textures/coop_skins/") and re.search(r"_(bloody|camo_woodland|camo_winter|camo_desert)\.(jpg|tga)$", k)})
    rep = {}
    cards = {}
    for t in targets:
        gun = t.split("/")[2]
        if a.only not in t:
            continue
        stub, key = re.match(r".*/(.+?)_(bloody|camo_woodland|camo_winter|camo_desert)$", t).groups()
        cand = by_base.get(stub.lower(), [])
        # prefer the job a TIK of this gun uses, else any job with that sheet name
        cand.sort(key=lambda j: (not any(gun in u["tik"] for u in j["users"]), j["stem"]))
        src = None
        if cand:
            png = os.path.join(B.BUILD, "png", B.safe(cand[0]["stem"]) + ".png")
            if os.path.exists(png):
                src = Image.open(png).convert("RGB"); how = "HD " + cand[0]["stem"]
        if src is None:
            vp = None
            if cand:
                vp, w = vfs.resolve_image(cand[0]["stem"])
            else:                       # magazine sheets with no gun job (mauserammo, barclip): find by name
                hits = sorted(k for k in idx if k.startswith("textures/models/weapons/")
                              and re.search(r"/" + re.escape(stub.lower()) + r"\.(tga|jpg|dds)$", k))
                if hits:
                    vp, w = vfs.resolve_image(os.path.splitext(hits[0])[0])
            if not vp:
                rep[t] = "no base found - left as today"; continue
            src = Image.open(io.BytesIO(vfs.read(vp))).convert("RGB"); how = "today " + vp
        W, H = src.size
        s = 1024.0 / max(W, H)
        if s < 1:
            src = src.resize((max(4, int(round(W * s / 4)) * 4), max(4, int(round(H * s / 4)) * 4)), Image.LANCZOS)
        # KEEP THE APPROVED CAMO SCALE: camo() lays width/(scale*6) pattern cells across the sheet, so baking at 1024
        # what was baked at 512 doubled the blob count (QA, mosin). Scale the cell size by new/old width instead.
        tvp, _w = vfs.resolve_image(t)
        oldw = Image.open(io.BytesIO(vfs.read(tvp))).size[0] if tvp else src.size[0]
        if key == "bloody":
            arr = BAKED[key](src)
        else:
            pal, seed = CAMO[key]
            arr = _ns["camo"](src, pal, scale=max(1, int(round(4.0 * src.size[0] / max(1, oldw)))), seed=seed)
        arr = np.clip(arr, 0, 255).astype(np.float64)
        dds = B.encode_mipped(arr)
        p = os.path.join(OUT, *(t + ".dds").split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(dds)
        rep[t] = "%s -> %dx%d %s" % (how, arr.shape[1], arr.shape[0], hashlib.md5(dds).hexdigest()[:8])
        cards.setdefault(gun, []).append((t, Image.fromarray(arr.astype(np.uint8))))
        print(t, rep[t], flush=True)
    os.makedirs(QA, exist_ok=True)
    for gun, ims in cards.items():          # one card per gun: today's 4 bakes over the new 4
        tiles = []
        for t, im in ims:
            vp, w = vfs.resolve_image(t)
            old = Image.open(io.BytesIO(vfs.read(vp))).convert("RGB") if vp else im
            tiles.append((old.resize((320, 320)), im.resize((320, 320))))
        card = Image.new("RGB", (330 * len(tiles), 650), "white")
        for i, (o, n) in enumerate(tiles):
            card.paste(o, (i * 330, 0)); card.paste(n, (i * 330, 330))
        card.save(os.path.join(QA, gun + "_" + str(len(tiles)) + ".jpg"), quality=85)
    json.dump(rep, open(os.path.join(B.BUILD, "report_fin.json"), "w"), indent=1)
    print(len(rep), "finish textures")


if __name__ == "__main__":
    main()
