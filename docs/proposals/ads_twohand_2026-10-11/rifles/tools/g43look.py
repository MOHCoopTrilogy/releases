"""Iron-sight G43 look test: the evidence sheets from a stills run (run_rifle.py parts hipstills,stills,stillsD,tpc) and
the offline side views (smg/tools/gunside.py through staged).

    python g43look.py <run> [<run of the scoped G43's stills, default rb24>]
writes ../evidence/g43irons/g43irons_{mesh_side_before_after,hip,aim,aim_stances,third_person}_<run>.jpg
"""
import sys, os, runpy, tempfile
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim2/runs')
EV = os.path.normpath(os.path.join(HERE, '..', 'evidence', 'g43irons'))
IR, WI, SC = 'coop_g43_irons', 'coop_g43_irons_camo_winter', 'g43'


def shot(run, gun, st, part, k):
    return Image.open(os.path.join(RUNS, run, 'ab__%s__%s__%s__%s__after__%04d.jpg' % (run, gun, st, part, k))).convert('RGB')


def label(im, txt):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 7 * len(txt), 18), fill=(0, 0, 0))
    d.text((4, 3), txt, fill=(255, 255, 255))
    return im


def grid(cells, cols, out):
    w, h = cells[0].size
    rows = (len(cells) + cols - 1) // cols
    S = Image.new('RGB', (cols * w, rows * h), (30, 30, 30))
    for i, c in enumerate(cells):
        S.paste(c, ((i % cols) * w, (i // cols) * h))
    S.save(out, quality=90)
    print('wrote', out, S.size)


def side():
    import staged  # noqa: F401
    cells = []
    for tik, name in (('g43', 'G 43 (scoped, as shipped)'), ('coop_g43_irons', 'G 43 Irons (staged mesh)')):
        tmp = os.path.join(tempfile.gettempdir(), 'g43side_%s.jpg' % tik)
        argv = sys.argv
        sys.argv = ['gunside.py', 'models/weapons/%s.tik' % tik, tmp, '--x', '-16,44']
        try:
            runpy.run_path(os.path.join(HERE, '..', '..', 'smg', 'tools', 'gunside.py'), run_name='__main__')
        finally:
            sys.argv = argv
        im = Image.open(tmp).convert('RGB')
        w = im.width
        third = im.height // 3
        for k, v in enumerate(('left side', 'right side', 'from above')):
            c = im.crop((0, k * third + 90, w, k * third + 90 + 300))
            cells.append(label(c, '%s - %s' % (name, v)))
    # order: scoped L, irons L, scoped R, irons R, scoped top, irons top
    cells = [cells[0], cells[3], cells[1], cells[4], cells[2], cells[5]]
    grid(cells, 2, os.path.join(EV, 'g43irons_mesh_side_before_after.jpg'))


def main():
    run = sys.argv[1]
    scr = sys.argv[2] if len(sys.argv) > 2 else 'rb24'
    os.makedirs(EV, exist_ok=True)
    side()
    half = lambda im: im.resize((960, 540), Image.LANCZOS)
    grid([label(half(shot(run, IR, 'stand', 'hipstills', 2)), 'G 43 Irons - hip (%s)' % run),
          label(half(shot(run, WI, 'stand', 'hipstills', 2)), 'G 43 Irons (Winter) - hip'),
          label(half(shot(scr, SC, 'stand', 'hipstills', 2)), 'G 43, scoped, as shipped - hip (%s)' % scr),
          label(half(shot(run, IR, 'crouch', 'hipstills', 2)), 'G 43 Irons - hip, crouch')], 2,
         os.path.join(EV, 'g43irons_hip_%s.jpg' % run))
    cells = []
    for st, nm in (('stand', 'light wall'), ('standD', 'dark door')):
        im = shot(run, IR, st, 'stills', 2)
        cells.append(label(im.copy(), 'G 43 Irons - aiming, %s (%s), full frame 1280x720' % (nm, run)))
        z = im.crop((480, 250, 800, 430)).resize((1280, 720), Image.LANCZOS)
        cells.append(label(z, 'the same, the middle 320x180 px enlarged 4x'))
    grid(cells, 2, os.path.join(EV, 'g43irons_aim_%s.jpg' % run))
    cells = []
    for g in (IR, WI):
        for st in ('stand', 'crouch', 'prone', 'standL', 'standR', 'braced', 'standD', 'crouchD', 'proneD', 'standLD', 'standRD', 'bracedD'):
            try:
                cells.append(label(shot(run, g, st, 'stills', 2).crop((320, 180, 960, 540)), '%s %s' % ('Irons' if g == IR else 'Irons (Winter)', st)))
            except FileNotFoundError:
                pass
    grid(cells, 3, os.path.join(EV, 'g43irons_aim_stances_%s.jpg' % run))
    cells = []
    for g, r, nm in ((IR, run, 'G 43 Irons'), (SC, scr, 'G 43 scoped, as shipped')):
        a = shot(r, g, 'stand', 'tpc', 1).crop((0, 60, 800, 660)).resize((640, 480), Image.LANCZOS)
        b = shot(r, g, 'stand', 'tpc', 4).crop((160, 240, 800, 720))
        cells += [label(a, '%s - third person, hip, from the right' % nm),
                  label(b, ('%s - third person, aiming (shoulder camera, crop)' if g == IR else '%s - aiming = its scope picture (crop)') % nm)]
    grid(cells, 2, os.path.join(EV, 'g43irons_third_person_%s.jpg' % run))


if __name__ == '__main__':
    main()
