"""Stack QA cards into review contact sheets: python contact.py <qa dir> <out prefix> [per_sheet]"""
import sys, os, glob
from PIL import Image
d, pre = sys.argv[1], sys.argv[2]
per = int(sys.argv[3]) if len(sys.argv) > 3 else 4
cards = sorted(glob.glob(os.path.join(d, "*.jpg")))
for i in range(0, len(cards), per):
    ims = [Image.open(c) for c in cards[i:i + per]]
    W = 2000
    ims = [im.resize((W, int(im.size[1] * W / im.size[0]))) for im in ims]
    s = Image.new("RGB", (W, sum(im.size[1] for im in ims) + 6 * len(ims)), "white")
    y = 0
    for im in ims:
        s.paste(im, (0, y)); y += im.size[1] + 6
    s.save("%s_%02d.jpg" % (pre, i // per), quality=85)
print((len(cards) + per - 1) // per, "sheets from", len(cards), "cards")
