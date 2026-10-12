"""Hi-Standard GIF: the rack zoomed on the gun first, then the normal view (shot - cock, reload ending in the rack)."""
import sys, glob
from PIL import Image, ImageDraw
sess, out = sys.argv[1], sys.argv[2]
fs = sorted(glob.glob('G:/mohaa-adsanim/runs/%s/ab__%s__histandard__yaw160__demo__after__[0-9][0-9][0-9][0-9].jpg' % (sess, sess)))
S = 320
segs = [('ZOOM: gun down, left hand over the slide, pull, release', list(range(66, 112, 3)), (440, 400, 840, 720), 130),
        ('shot - overhand cock', list(range(52, 130, 5)), (380, 200, 900, 720), 80),
        ('reload - magazine in - overhand rack - on target', list(range(246, 400, 6)), (380, 200, 900, 720), 96)]
frames, durs = [], []
for lab, idx, crop, ms in segs:
    for i in idx:
        im = Image.open(fs[i]).convert('RGB').crop(crop)
        w = S; h = int(im.height * S / im.width)
        im = im.resize((w, h), Image.LANCZOS)
        c = Image.new('RGB', (S, S), (20, 20, 20)); c.paste(im, (0, (S - h) // 2))
        d = ImageDraw.Draw(c); d.rectangle((0, 0, S, 13), fill=(0, 0, 0)); d.text((3, 1), '%s  f%d' % (lab, i), fill=(255, 255, 120))
        frames.append(c.quantize(colors=32, dither=0)); durs.append(ms)
frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=False)
import os
print(out, len(frames), 'frames', os.path.getsize(out) // 1024, 'KB')
