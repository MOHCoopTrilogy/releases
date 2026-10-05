"""ab_gif.py - side-by-side BEFORE | AFTER gif from two run frame sequences (engine screenshots).
    python ab_gif.py <out.gif> <before glob> <before step> <after glob> <after step> [label_before] [label_after]
step = take every Nth frame so both play at real time (frames are 16 ms of game time; gif 48 ms per frame)."""
import sys, glob
from PIL import Image, ImageDraw
out, bg, bs, ag, as_ = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5])
lb = sys.argv[6] if len(sys.argv) > 6 else 'BEFORE'; la = sys.argv[7] if len(sys.argv) > 7 else 'AFTER'
B = sorted(glob.glob(bg))[::bs]; A = sorted(glob.glob(ag))[::as_]
n = max(len(A), len(B)); fr = []
for i in range(n):
    S = Image.new('RGB', (960, 300), (0, 0, 0)); d = ImageDraw.Draw(S)
    for k, (L, t) in enumerate(((B, lb), (A, la))):
        im = Image.open(L[min(i, len(L) - 1)]).convert('RGB').crop((240, 135, 1280, 720)).resize((480, 270))
        S.paste(im, (k * 480, 30)); d.text((k * 480 + 6, 8), t, fill=(255, 255, 0))
    fr.append(S.quantize(colors=128))
fr[0].save(out, save_all=True, append_images=fr[1:], duration=48, loop=0, optimize=True)
import os; print(out, len(fr), 'frames', round(os.path.getsize(out) / 1e6, 1), 'MB')
