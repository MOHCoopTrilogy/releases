r"""Shotgun sight evidence sheets from engine stills (run folders under hv.RUNS):

    python sgsheet.py pair <before run> <after run> <out.jpg>      light wall + dark backdrop, before | after | after centre 2x
    python sgsheet.py stances <run> <out.jpg> [gun,gun,...]        wall stand/crouch/prone + dark stand/crouch/prone/leans per gun
    python sgsheet.py tp <run> <out.jpg> [gun]                     third person: aimed frame + crop of the muzzle
"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw


def fr(run, gun, tag, k=2):
    p = os.path.join(hv.RUNS, run, 'ab__%s__%s__%s__aim__after__%04d.jpg' % (run, gun, tag, k))
    if not os.path.isfile(p):
        c = sorted(glob.glob(os.path.join(hv.RUNS, run, 'ab__%s__%s__%s__aim__after__*.jpg' % (run, gun, tag))))
        p = c[-1]
    return Image.open(p).convert('RGB')


def lab(im, t, col=(255, 240, 60)):
    d = ImageDraw.Draw(im); d.rectangle((0, 0, 8 + 7 * len(t), 18), fill=(0, 0, 0)); d.text((5, 4), t, fill=col)
    return im


def pair(b, a, out):
    rows = []
    for (tb, ta, name) in (('yaw165', 'standW', 'light wall'), ('stand', 'stand', 'dark backdrop')):
        B = fr(b, 'shotgun', tb, 1); A = fr(a, 'shotgun', ta)
        W, H = A.size
        z = A.crop((W // 2 - 180, H // 2 - 180, W // 2 + 180, H // 2 + 180)).resize((H, H), Image.LANCZOS)
        row = Image.new('RGB', (W * 2 + H, H))
        row.paste(lab(B, 'BEFORE (released) - %s' % name), (0, 0)); row.paste(lab(A, 'AFTER (staged: bead, groove, eye 4 u back) - %s' % name), (W, 0))
        row.paste(lab(z, 'after, centre 2x'), (W * 2, 0))
        rows.append(row)
    S = Image.new('RGB', (rows[0].size[0], rows[0].size[1] * len(rows)))
    for i, r in enumerate(rows):
        S.paste(r, (0, i * r.size[1]))
    S = S.resize((2400, S.size[1] * 2400 // S.size[0]), Image.LANCZOS)
    S.save(out, quality=90); print(out, S.size)


def stances(run, out, guns):
    tags = ['standW', 'crouchW', 'proneW', 'stand', 'crouch', 'prone', 'standL', 'standR']
    cw, ch = 480, 300
    S = Image.new('RGB', (cw * len(tags), ch * len(guns)))
    for j, g in enumerate(guns):
        for i, t in enumerate(tags):
            im = fr(run, g, t); W, H = im.size
            c = im.crop((W // 2 - 320, H // 2 - 150, W // 2 + 320, H // 2 + 250)).resize((cw, ch), Image.LANCZOS)
            S.paste(lab(c, '%s %s' % (g, t)), (i * cw, j * ch))
    S.save(out, quality=88); print(out, S.size)


def tp(run, out, gun):
    fs = sorted(glob.glob(os.path.join(hv.RUNS, run, 'ab__%s__%s__stand__tpc__after__*.jpg' % (run, gun))))
    a = Image.open(fs[8]).convert('RGB')
    z = a.crop((260, 340, 560, 490)).resize((1280, 640), Image.LANCZOS)
    S = Image.new('RGB', (1280, 720 + 640)); S.paste(lab(a, 'third person, aim held (%s)' % run), (0, 0)); S.paste(lab(z, 'the gun, 4.3x'), (0, 720))
    S.save(out, quality=88); print(out)


if __name__ == '__main__':
    m = sys.argv[1]
    if m == 'pair':
        pair(sys.argv[2], sys.argv[3], sys.argv[4])
    elif m == 'stances':
        stances(sys.argv[2], sys.argv[3], (sys.argv[4] if len(sys.argv) > 4 else 'shotgun').split(','))
    else:
        tp(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else 'shotgun')
