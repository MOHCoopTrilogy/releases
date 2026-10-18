"""Tiks of the new C96 (base + 7 finishes) from the pistol lane's ship2 tiks (their text is kept: name, rank, sounds, rows,
tuning), with the mesh, surfaces, finish shaders and gun clips swapped.   python gen_ship.py

  models/weapons/mauser_c96.tik            path models/weapons/coop_c96n, skelmodel c96n.skd, 14 surfaces -> shader coop_c96n
  models/weapons/mauser_c96_<finish>.tik   the same with coop_c96n_<finish>
The Trench C96 (mauser_c96_c96trench.tik, own mesh) is not touched.
"""
import os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c96lib as L

SHIP2 = os.path.join(L.ROOT, '..', 'ads_twohand_2026-10-11', 'ship2', 'models', 'weapons')
OUT = os.path.join(L.STAGE, 'models', 'weapons')
FIN = ['', '_bloody', '_blued', '_camo_desert', '_camo_winter', '_camo_woodland', '_chrome', '_gold']
M = json.load(open(os.path.join(L.BUILD, 'mesh.json')))
CLIPMAP = {'c96.skc': 'c96n_idle.skc', 'coop_c96_reload_ads_loaded.skc': 'c96n_reload_ads_loaded.skc',
           'coop_c96_reload_ads_empty.skc': 'c96n_reload_ads_empty.skc', 'coop_c96_reload_empty.skc': 'c96n_reload_empty.skc',
           'coop_c96_idle_empty.skc': 'c96n_idle_empty.skc', 'coop_c96_reload_hip.skc': 'c96n_reload_hip.skc'}


def convert(text, fin):
    nl = '\r\n' if '\r\n' in text else '\n'
    t = text.replace('\r\n', '\n')
    shader = 'coop_c96n' + fin
    lines = ['\tscale 0.52', '\t// HZM coop [C96 model swap 2026-10-18]: "Mauser C96" by no12u (Sketchfab), CC BY 4.0 - mesh, sheet and gun clips are new;',
             '\t// hands, torso rows, sounds, numbers are the pistol lane\'s. Rows / bones: coop_slide = bolt, coop_tog = hammer, coop_trig = trigger.',
             '\tpath models/weapons/coop_c96n', '\tskelmodel c96n.skd']
    lines += ['\tsurface %s shader %s' % (s, shader) for s in M['surfaces']]
    t, n = re.subn(r'(?m)^\tscale 0\.52\n.*?(?=^\}\n)', '\n'.join(lines) + '\n', t, count=1, flags=re.S)
    assert n == 1
    # clips: only the lines of the animations block that name a file we replace
    def clip(m):
        f = m.group(3)
        assert f in CLIPMAP, f
        return m.group(1) + m.group(2) + CLIPMAP[f]
    t = re.sub(r'(?m)^(\t(?:idle|secondaryfire|reload_ads_loaded|reload_ads_empty|reload_empty|idle_empty|reload)\s+)()(\S+\.skc)', clip, t)
    t, nf = re.subn(r'(?m)^(\tfire\s+)c96\.skc', r'\1c96n_fire.skc', t)
    assert nf == 1
    t = t.replace('reload\t\tc96n_reload_hip.skc', 'reload\t\tc96n_reload_hip.skc')
    return t.replace('\n', nl)


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in FIN:
        src = os.path.join(SHIP2, 'mauser_c96%s.tik' % f)
        text = open(src, 'rb').read().decode('latin-1')
        res = convert(text, f)
        open(os.path.join(OUT, 'mauser_c96%s.tik' % f), 'wb').write(res.encode('latin-1'))
    print('tiks:', len(FIN))
    # shows the animation lines once
    t = open(os.path.join(OUT, 'mauser_c96.tik'), encoding='latin-1').read()
    for l in t.splitlines():
        if re.match(r'\t(idle|fire|secondaryfire|reload\w*|surface c96f1|path|skelmodel)\b', l):
            print(l.rstrip())


if __name__ == '__main__':
    main()
