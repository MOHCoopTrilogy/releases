import sys, io, numpy as np, scene as SC
from PIL import Image, ImageDraw
st = SC.stack()
import re
rp = re.compile(r'^(main|mainta|maintt).pak\d', re.I)
def retail(base):
    for ext in ('.jpg', '.tga', '.dds'):
        for i, m in reversed(st.copies.get(base + ext, [])):
            if rp.search(st.name(i)):
                return SC.decode(st.read(i, m), ext), st.name(i) + ext
    return None, None
names = sys.argv[2:]
T = 300; cols = 5
rows = (len(names) + cols - 1) // cols
sheet = Image.new('RGB', (T * cols, (T + 16) * rows), (25, 25, 25)); d = ImageDraw.Draw(sheet)
for k, n in enumerate(names):
    a, src = retail(n)
    if a is None: continue
    im = Image.fromarray(np.asarray(a, np.uint8)).resize((T, T), Image.LANCZOS)
    x, y = (k % cols) * T, (k // cols) * (T + 16)
    sheet.paste(im, (x, y + 16))
    d.text((x + 3, y + 2), "%s %dx%d" % (n.split('/', 1)[1][:34], a.shape[1], a.shape[0]), fill=(255, 255, 0))
sheet.save(sys.argv[1], quality=88)
