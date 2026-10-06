"""Side-by-side crops: shipped today (HRRTM DDS, upsampled to the new size) vs the new sheet, plus overview."""
import sys, os
from PIL import Image, ImageDraw
W = os.path.expandvars(r"%TEMP%\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\weaponhd")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previews")
def run(name, today, boxes):
    new = Image.open(os.path.join(W, name + "_final.png")).convert("RGB")
    old = Image.open(os.path.join(W, "src", today)).convert("RGB").resize(new.size, Image.BICUBIC)
    tiles = []
    for (u0, v0, u1, v1) in boxes:
        b = (int(u0 * new.size[0]), int(v0 * new.size[1]), int(u1 * new.size[0]), int(v1 * new.size[1]))
        tiles.append((old.crop(b), new.crop(b)))
    Wt = sum(t[0].size[0] for t in tiles) + 12 * len(tiles); Ht = max(t[0].size[1] for t in tiles) * 2 + 12
    s = Image.new("RGB", (Wt, Ht), "white"); x = 0
    for o, n in tiles:
        s.paste(o, (x, 0)); s.paste(n, (x, o.size[1] + 12)); x += o.size[0] + 12
    s.save(os.path.join(OUT, name + "_crops.jpg"), quality=90)
    ov = Image.new("RGB", (2048 + 12, 1024 * new.size[1] // new.size[0]), "white")
    ov.paste(old.resize((1024, 1024 * new.size[1] // new.size[0])), (0, 0)); ov.paste(new.resize((1024, 1024 * new.size[1] // new.size[0])), (1036, 0))
    ov.save(os.path.join(OUT, name + "_overview.jpg"), quality=88)
    print(name, s.size)
if __name__ == "__main__":
    import json
    run(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]))
