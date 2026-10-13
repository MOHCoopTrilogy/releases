"""decode GIFs and lay frames out for looking at:  python tools/gifqa.py out.jpg n_per_gif gif1 gif2 ...
prints frame count, size, duration, bytes of each"""
import sys, os
from PIL import Image, ImageDraw, ImageSequence

out, n = sys.argv[1], int(sys.argv[2])
rows = []
for g in sys.argv[3:]:
    im = Image.open(g)
    fr = [f.convert('RGB') for f in ImageSequence.Iterator(im)]
    print('%-44s %3d frames %s %d ms %.2f MB' % (os.path.basename(g), len(fr), fr[0].size, im.info.get('duration', 0), os.path.getsize(g) / 1048576.0))
    idx = [round(i * (len(fr) - 1) / float(n - 1)) for i in range(n)]
    row = []
    for i in idx:
        f = fr[i].resize((320, round(fr[i].height * 320 / fr[i].width)), Image.LANCZOS)
        ImageDraw.Draw(f).text((4, 2), '%s f%d' % (os.path.basename(g)[4:-4], i), fill=(255, 255, 0))
        row.append(f)
    rows.append(row)
W = n * 320; H = sum(r[0].height for r in rows)
sh = Image.new('RGB', (W, H)); y = 0
for r in rows:
    for k, f in enumerate(r):
        sh.paste(f, (k * 320, y))
    y += r[0].height
sh.save(out, quality=86)
print('wrote', out, sh.size)
