"""The EYE's picture of a staged reload clip, rendered at the game's size and CROPPED to the part that matters (a hand on
the handle is 60 px wide at 1280: the plain sheets are too small to judge whether a pull reads).

    cd smg/assets; IRONSIGHT_EXTRA_PAKS=<overlay> python ../tools/eyezoom.py <gun> . <which> <out.jpg> --frames 50:66:2
                   [--crop x0,y0,x1,y1 of 1280x720, default 300,250,860,720] [--cols 4] [--w 1280]
"""
import sys, os, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smgbake as SB
import sideview as SV


def main():
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('root'); ap.add_argument('which'); ap.add_argument('out')
    ap.add_argument('--frames', default='50:66:2'); ap.add_argument('--crop', default='300,250,860,720')
    ap.add_argument('--cols', type=int, default=4); ap.add_argument('--w', type=int, default=1280)
    a = ap.parse_args()
    g = SB.GUNS[a.gun]
    path, anim = SB.clip_of(a.gun, a.root, a.which)
    c = SB.R.load(path)
    aimp = os.path.join(a.root, 'models', 'human', 'animation', g['aim'].replace('/', os.sep))
    corr = SV.corr_of(aimp if os.path.isfile(aimp) else SB.R.ANIM + g['aim'], g['sight'])
    SV.V.PROP.clear()
    SV.V.PROP.update(tik=g['prop'], t0=g['propwin'][0] * c.frameTime, t1=g['propwin'][1] * c.frameTime, tag='tag_weapon_left')
    p = [int(x) for x in a.frames.split(':')] if ':' in a.frames else None
    fr = list(range(*p)) if p else [int(x) for x in a.frames.split(',')]
    k = a.w / 1280.0
    box = tuple(int(float(x) * k) for x in a.crop.split(','))
    ims = []
    for f in fr:
        if f >= c.numFrames:
            continue
        eye = SV.panels(c, f, g['sight'], corr, anim, a.w, only_eye=True)[0].crop(box)
        ImageDraw.Draw(eye).text((4, 4), '%s %s f%d' % (a.gun, a.which, f), fill=(0, 0, 0))
        ims.append(eye)
    SV.V.PROP.clear()
    W, H = ims[0].size
    cols = min(a.cols, len(ims))
    S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * W, (i // cols) * H))
    S.save(a.out, quality=88)
    print(a.out, S.size)


if __name__ == '__main__':
    main()
