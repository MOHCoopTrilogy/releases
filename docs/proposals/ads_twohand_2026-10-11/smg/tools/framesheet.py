"""Contact-frame sheet of one aimed / hip capture of a run_smg session: the engine frames at the given CLIP frames
(1/30 s; a capture frame is 16 ms), full frame or a crop at full size, centre box drawn - to LOOK at every hand contact.

    python framesheet.py <session> <harness gun> <E|L> <out.jpg> --clip 9,12,14,... [--stance stand] [--hip]
                         [--crop x0,y0,x1,y1 of 1280x720] [--cols 4] [--w 640]
The reload's first capture frame comes from reload_<session>_<gun>.json (measure_run.py) for an aimed capture, from the
`DEMO reload` mark for a hip one (an emptied gun at the hip starts by itself: --start <capture frame> overrides).
"""
import sys, os, re, json, argparse, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim3/runs').rstrip('/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sess'); ap.add_argument('gun'); ap.add_argument('case'); ap.add_argument('out')
    ap.add_argument('--clip', required=True); ap.add_argument('--stance', default='stand'); ap.add_argument('--hip', action='store_true')
    ap.add_argument('--crop'); ap.add_argument('--cols', type=int, default=4); ap.add_argument('--w', type=int, default=640)
    ap.add_argument('--start', type=int)
    a = ap.parse_args()
    st = '' if a.stance == 'stand' else a.stance
    tag = 'ab__%s__%s__%s%s%s__%s__after' % (a.sess, a.gun, st, 'hip' if a.hip else 'ads', a.case, 'demohip' if a.hip else 'demo')
    run = '%s/%s/' % (RUNS, a.sess)
    if a.start is not None:
        i0 = a.start
    elif not a.hip:
        d = json.load(open(os.path.join(HERE, 'reload_%s_%s.json' % (a.sess, a.gun))))
        i0 = d['%s_%s' % (a.stance, 'empty' if a.case == 'E' else 'loaded')]['reload'][0]
    else:
        i0, cur = None, False
        for ln in open(run + 'qconsole.log', encoding='latin-1', errors='replace'):
            if 'echo' in ln:
                continue
            if 'ABSCEN begin ' + tag in ln:
                cur = True
            m = re.search(r'DEMO (fire|reload) (\d+)', ln)
            if cur and m and (m.group(1) == ('fire' if a.case == 'E' else 'reload')) and i0 is None:
                i0 = int(m.group(2))
            if 'ABSCEN end ' + tag in ln:
                break
        assert i0 is not None, tag
        if a.case == 'E':
            print('hip E: the reload starts by itself when the gun runs dry - give --start <capture frame>; using the fire mark + hold as a guess')
    cl = [float(x) for x in a.clip.split(',')]
    crop = [int(x) for x in a.crop.split(',')] if a.crop else [0, 0, 1280, 720]
    cw, ch = crop[2] - crop[0], crop[3] - crop[1]
    w = a.w; h = int(round(w * ch / float(cw)))
    rows = (len(cl) + a.cols - 1) // a.cols
    S = Image.new('RGB', (w * a.cols, h * rows), 'black')
    for k, c in enumerate(cl):
        f = i0 + int(round(c * (1000.0 / 30.0) / 16.0))
        p = run + tag + '__%04d.jpg' % f
        if not os.path.isfile(p):
            continue
        im = Image.open(p).convert('RGB')
        d = ImageDraw.Draw(im)
        d.rectangle((512, 288, 768, 432), outline=(255, 255, 0))
        im = im.crop(crop).resize((w, h), Image.LANCZOS)
        ImageDraw.Draw(im).text((5, 4), 'clip f%g (capture %d)' % (c, f), fill=(255, 255, 0))
        S.paste(im, ((k % a.cols) * w, (k // a.cols) * h))
    S.save(a.out, quality=87)
    print(a.out, S.size, tag, 'reload starts at capture frame', i0)


if __name__ == '__main__':
    main()
