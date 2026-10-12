"""One contact sheet + one small GIF per pistol from a run_2h session (demoy + stills).

    python evgun.py <session> <gun> <out dir> [--yaw 160] [--gifw 360] [--gifstep 4] [--colors 40]
Sheet: aim on the light backdrop, aim on the dark one, the seven stances, then the demo's raise / fire / aimed reload /
lower as rows of cropped frames (frame numbers from the capture's own ^~^~^ DEMO markers).
"""
import sys, os, re, glob, argparse
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('sess'); ap.add_argument('gun'); ap.add_argument('out'); ap.add_argument('--yaw', type=int, default=160)
ap.add_argument('--gifw', type=int, default=320); ap.add_argument('--gifstep', type=int, default=4)
ap.add_argument('--colors', type=int, default=28); ap.add_argument('--label', default='')
a = ap.parse_args()
RUN = 'G:/mohaa-adsanim/runs/%s/' % a.sess
tag = 'ab__%s__%s__yaw%d__demo__after' % (a.sess, a.gun, a.yaw)
fs = sorted(glob.glob(RUN + tag + '__*.jpg'))
assert fs, tag
log = open(RUN + 'qconsole.log', encoding='latin-1', errors='replace').read().splitlines()
marks, on = [], False
for ln in log:
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m:
        on = (m.group(1) == 'begin' and m.group(2) == tag)
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
    if on and m and 'echo' not in ln:
        marks.append((m.group(1), int(m.group(2))))
print(marks, len(fs))
raise_f = [f for n, f in marks if n == 'raise'][0]
fires = [f for n, f in marks if n == 'fire']
rel = [f for n, f in marks if n == 'reload'][0]
low = [f for n, f in marks if n == 'lower'][0]
CROP = (240, 180, 1040, 720)
TW, TH = 300, 300 * 540 // 800


def tile(i, lab=None):
    im = Image.open(fs[min(i, len(fs) - 1)]).convert('RGB').crop(CROP).resize((TW, TH), Image.LANCZOS)
    d = ImageDraw.Draw(im); t = lab or 'f%d' % i
    d.rectangle((0, 0, 8 + 6 * len(t), 12), fill=(0, 0, 0)); d.text((2, 0), t, fill=(255, 255, 0))
    return im


def row(title, idx):
    return title, [tile(i) for i in idx]


rows = [row('RAISE', [raise_f + k for k in (0, 6, 12, 16, 18, 20, 22, 26)]),
        row('FIRE (aimed)', [fires[0] + k for k in (0, 3, 4, 5, 6, 8, 11, 20)]),
        row('AIMED RELOAD', [rel + int(round(k * (low - rel - 1) / 15.0)) for k in range(16)]),
        row('LOWER', [low + k for k in (0, 2, 4, 6, 8, 12, 18, 30)])]
COLS = 8
W = TW * COLS
top_h = 360
H = top_h + 200 + sum(18 + TH * ((len(t) + COLS - 1) // COLS) for _, t in rows) + 24
S = Image.new('RGB', (W, H), (28, 28, 28))
d = ImageDraw.Draw(S)
d.text((6, 4), '%s - two-handed aim  (session %s)' % (a.label or a.gun, a.sess), fill=(255, 255, 255))
y = 22
light = Image.open(fs[raise_f + 48]).convert('RGB').resize((640, 360), Image.LANCZOS)
dark = Image.open(RUN + 'ab__%s__%s__stand__aim__after__0002.jpg' % (a.sess, a.gun)).convert('RGB').resize((640, 360), Image.LANCZOS)
zoom = Image.open(fs[raise_f + 48]).convert('RGB').crop((400, 300, 880, 720)).resize((int(480 * 360 / 420), 360), Image.LANCZOS)
S.paste(light, (0, y)); S.paste(dark, (644, y)); S.paste(zoom, (1288, y))
d.text((6, y + 2), 'aim, light backdrop', fill=(255, 255, 0)); d.text((650, y + 2), 'aim, dark backdrop', fill=(255, 255, 0))
d.text((1294, y + 2), 'zoom', fill=(255, 255, 0))
y += 364
sw = W // 7
for k, st in enumerate(('stand', 'crouch', 'prone', 'standL', 'standR', 'crouchL', 'crouchR')):
    im = Image.open(RUN + 'ab__%s__%s__%s__aim__after__0002.jpg' % (a.sess, a.gun, st)).convert('RGB').resize((sw, sw * 9 // 16), Image.LANCZOS)
    S.paste(im, (k * sw, y)); d.text((k * sw + 4, y + 2), st, fill=(255, 255, 0))
y += sw * 9 // 16 + 4
for title, tiles in rows:
    d.text((6, y + 2), title, fill=(255, 255, 255)); y += 18
    for k, im in enumerate(tiles):
        S.paste(im, ((k % COLS) * TW, y + (k // COLS) * TH))
    y += TH * ((len(tiles) + COLS - 1) // COLS)
S = S.crop((0, 0, W, y + 4))
os.makedirs(a.out, exist_ok=True)
p1 = os.path.join(a.out, '%s_twohand_sheet.jpg' % a.gun)
S.save(p1, quality=84)
print(p1, S.size, os.path.getsize(p1) // 1024, 'KB')
# small GIF: the whole demo, cropped on the hands
out, cur = [], 'hip'
labs = dict([(raise_f, 'raise'), (fires[0], 'fire'), (rel, 'aimed reload'), (low, 'lower')])
for i in range(0, len(fs), a.gifstep):
    for k in sorted(labs):
        if i >= k:
            cur = labs[k]
    im = Image.open(fs[i]).convert('RGB').crop((280, 200, 1000, 720))
    im = im.resize((a.gifw, a.gifw * 520 // 720), Image.LANCZOS)
    dd = ImageDraw.Draw(im)
    dd.rectangle((0, im.height - 14, 10 + 6 * len(cur), im.height), fill=(0, 0, 0)); dd.text((3, im.height - 13), cur, fill=(255, 255, 255))
    out.append(im.quantize(colors=a.colors, dither=0))
p2 = os.path.join(a.out, '%s_twohand.gif' % a.gun)
out[0].save(p2, save_all=True, append_images=out[1:], duration=16 * a.gifstep, loop=0)
print(p2, len(out), 'frames', os.path.getsize(p2) // 1024, 'KB')
