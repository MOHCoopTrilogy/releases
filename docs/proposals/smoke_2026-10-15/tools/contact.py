import sys
from PIL import Image
d, tag, ids, out = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")], sys.argv[4]
W = Image.new("RGB", (1280, 360 * ((len(ids) + 1) // 2)))
for k, i in enumerate(ids):
    W.paste(Image.open("%s/%s_f_%04d.jpg" % (d, tag, i)).resize((640, 360)), ((k % 2) * 640, (k // 2) * 360))
W.save(out, quality=80)
