"""Every finish / variant tik of a gun IN THE AIM on one sheet (user rule: a change has to reach every finish tik) - from a
`stills` run in which each tik was given as a --guns key (run_smg.py: a key that is not in its table = models/weapons/<key>.tik):

    python run_smg.py <id> --overlay <pk3> --cgame cgame_smg4 --guns sten,sten_bloody,... --parts stills --stances stand --yaw 160
    python finishsheet.py <id> <out.jpg> [--guns a,b,c] [--crop 240,120,1040,720] [--cols 4] [--scale 0.6] [--stance stand]
The last still of each tik's settled aim, cropped; the centre box is drawn.
"""
import sys, os, re, glob, argparse
from PIL import Image, ImageDraw
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim3/runs') + '/'

ap = argparse.ArgumentParser()
ap.add_argument('sess'); ap.add_argument('out'); ap.add_argument('--guns', default=None); ap.add_argument('--crop', default='240,120,1040,720')
ap.add_argument('--cols', type=int, default=4); ap.add_argument('--scale', type=float, default=0.6); ap.add_argument('--stance', default='stand')
a = ap.parse_args()
x0, y0, x1, y1 = [int(v) for v in a.crop.split(',')]
found = {}
for p in sorted(glob.glob(RUNS + a.sess + '/ab__%s__*__%s__aim__after__*.jpg' % (a.sess, a.stance))):
    m = re.search(r'ab__%s__(.+?)__%s__aim__after__(\d+)\.jpg$' % (re.escape(a.sess), a.stance), p.replace('\\', '/'))
    if m:
        found[m.group(1)] = p                      # the last one of each gun
guns = a.guns.split(',') if a.guns else sorted(found)
ims = []
for g in guns:
    if g not in found:
        print('NOT in the run:', g); continue
    im = Image.open(found[g]).convert('RGB')
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0))
    im = im.crop((x0 * W // 1280, y0 * H // 720, x1 * W // 1280, y1 * H // 720))
    im = im.resize((int(im.width * a.scale), int(im.height * a.scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 9 + 7 * len(g), 14), fill=(0, 0, 0)); d.text((4, 1), g, fill=(255, 255, 0))
    ims.append(im)
cols = min(a.cols, len(ims))
w, h = ims[0].size
S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), 'white')
for k, im in enumerate(ims):
    S.paste(im, ((k % cols) * w, (k // cols) * h))
S.save(a.out, quality=88)
print(a.out, S.size, len(ims), 'tiks')
