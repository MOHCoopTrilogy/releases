"""build_set.py - the FULL tile set, from tools/tileset.py (authored picks) and tools/titles.json (authored titles).

    python tools/build_set.py [bsp ...]     # build all (or the named) tiles
    python tools/build_set.py sheet <name> [bsp ...]   # a progress/QA sheet of the built tiles, at real on-screen size

Per tile (id = bsp with '/' -> '_'):
  set/master/<id>_card_{c,s}_1024.jpg    master cards (c = ui_menuCenter 1 square; s = default 16:9 stretch, squeezed)
  set/game/<id>_{c,s}.jpg                512x512 shipped tile textures
  set/game/print_<id>_{c,s}.jpg          512x384 shipped war-room prints (4:3 texture; s authored at 16:9 and squeezed)
  set/sources/<id>.jpg                   the source frame (q95), with set/SOURCES.json provenance
Crops come from the spec's `focus` box (what must be in shot) by tile_treat.fit_box at each exact aspect, never crossing
the spec's `allow` region (e.g. below a console line, above a vehicle wheel). Explicit boxes (crop_c/crop_s/pcrop_c/
pcrop_s) override.
"""
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tile_treat as T  # noqa: E402
import tileset  # noqa: E402

OUT = os.path.join(PROP, "set")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"


def tid(bsp):
    return bsp.replace("/", "_")


def read_raw(raw):
    if isinstance(raw, (tuple, list)):
        return Image.open(io.BytesIO(zipfile.ZipFile(os.path.join(GOG, raw[0])).read(raw[1]))).convert("RGB")
    return Image.open(raw).convert("RGB")


def boxes(s, size):
    allow = s.get("allow")
    f = s.get("focus", (0, 0) + size)
    pw_c = T.PHOTO_W
    pw_s = int(round(T.S * T.LAYOUT_ASPECT["s"])) - 2 * T.MARGIN
    ma = s.get("max_aspect", 99)
    return {
        "crop_c": s.get("crop_c") or T.fit_box(min(pw_c / T.PHOTO_H, ma), f, size, allow),
        "crop_s": s.get("crop_s") or T.fit_box(min(pw_s / T.PHOTO_H, ma), f, size, allow),
        "pcrop_c": s.get("pcrop_c") or T.fit_box(min(T.PRINT_ASPECT["c"], ma), f, size, allow),
        "pcrop_s": s.get("pcrop_s") or T.fit_box(min(T.PRINT_ASPECT["s"], ma), f, size, allow),
    }


def build(bsp, titles, prov):
    s = dict(tileset.SPECS[bsp])
    i = tid(bsp)
    for d in ("master", "game", "sources"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    src = os.path.join(OUT, "sources", i + ".jpg")
    im = read_raw(s["raw"])
    im.save(src, quality=95, subsampling=0)
    b = boxes(s, im.size)
    spec = dict(s, src=src, title=titles[bsp]["title"], crop=b["crop_c"], crop_s=b["crop_s"],
                pcrop_c=b["pcrop_c"], pcrop_s=b["pcrop_s"])
    for lay in ("c", "s"):
        c = T.card(spec, lay)
        c.save(os.path.join(OUT, "master", "%s_card_%s_1024.jpg" % (i, lay)), quality=95, subsampling=0)
        T.game_texture(c, lay).save(os.path.join(OUT, "game", "%s_%s.jpg" % (i, lay)), quality=92, subsampling=0)
        p = T.print_photo(spec, lay)
        p.resize((512, 384), Image.LANCZOS).save(os.path.join(OUT, "game", "print_%s_%s.jpg" % (i, lay)), quality=92,
                                                 subsampling=0)
    frm = ("retail pak " + "/".join(s["raw"])) if isinstance(s["raw"], (tuple, list)) else s["raw"]
    prov[bsp] = {"from": frm, "how": s.get("how", ""), "size": im.size,
                 "boxes": {k: [round(v) for v in bx] for k, bx in b.items()}}
    print("built", bsp, "-", titles[bsp]["title"])


def sheet(name, ids):
    """Progress/QA sheet: each tile as the engine shows it at 1080p - card_c 225x225, card_s 300x225, print_s 492x277."""
    rows = []
    for bsp in ids:
        i = tid(bsp)
        p = os.path.join(OUT, "game", "%s_c.jpg" % i)
        if os.path.exists(p):
            rows.append(i)
    cols = 3
    cw = 225 + 300 + 369 + 40
    rh = 277 + 26
    S = Image.new("RGB", (cols * cw + 10, ((len(rows) + cols - 1) // cols) * rh + 10), (18, 34, 18))
    d = ImageDraw.Draw(S)
    for k, i in enumerate(rows):
        x, y = 10 + (k % cols) * cw, 8 + (k // cols) * rh
        d.text((x, y), i, fill=(250, 199, 71))
        a = Image.open(os.path.join(OUT, "game", "%s_c.jpg" % i)).resize((225, 225), Image.LANCZOS)
        b = Image.open(os.path.join(OUT, "game", "%s_s.jpg" % i)).resize((300, 225), Image.LANCZOS)
        c = Image.open(os.path.join(OUT, "game", "print_%s_c.jpg" % i)).resize((369, 277), Image.LANCZOS)
        S.paste(a, (x, y + 18))
        S.paste(b, (x + 235, y + 18))
        S.paste(c, (x + 545, y + 18))
    os.makedirs(os.path.join(OUT, "sheets"), exist_ok=True)
    out = os.path.join(OUT, "sheets", name + ".jpg")
    S.save(out, quality=88)
    print("sheet", out, len(rows))


def main(a):
    titles = json.load(open(os.path.join(HERE, "titles.json"), encoding="utf-8"))["tiles"]
    if a and a[0] == "sheet":
        sheet(a[1], a[2:] or list(tileset.SPECS))
        return
    pf = os.path.join(OUT, "SOURCES.json")
    prov = json.load(open(pf)) if os.path.exists(pf) else {}
    for bsp in (a or list(tileset.SPECS)):
        build(bsp, titles, prov)
    os.makedirs(OUT, exist_ok=True)
    json.dump(prov, open(pf, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1:])
