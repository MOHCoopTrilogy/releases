"""SMG lane test overlay: the harness plumbing (ovbase_1021.pk3, built by ..\\..\\tools\\mkbase.py - marker shader +
coop_mod/weather.scr with the test thread) + every file under ../assets (the staged tree, game paths).

    python mkov_smg.py <out.pk3> [--base]        --base = plumbing only (the RELEASED rows and clips: a "before" run)
Asserts that every clip a staged fps_anims row names and that lives under viewmodel/coop_* or is staged is in the pak.
"""
import sys, os, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\adssmg"
BASE = os.path.join(SCR, 'ovbase_1021.pk3')


def main():
    out = sys.argv[1]
    base_only = '--base' in sys.argv
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(BASE)
        for i in b.infolist():
            z.writestr(i.filename, b.read(i.filename))
        if not base_only:
            for d, _, fs in os.walk(ASSETS):
                for f in fs:
                    p = os.path.join(d, f)
                    arc = os.path.relpath(p, ASSETS).replace(os.sep, '/')
                    z.write(p, arc); n += 1
    names = set(x.lower() for x in zipfile.ZipFile(out).namelist())
    if not base_only:
        rows = open(os.path.join(ASSETS, 'models', 'player', 'base', 'fps_anims_smg.txt'), encoding='latin-1').read().splitlines()
        staged = 0
        for l in rows:
            t = l.split('//')[0].split()
            if len(t) >= 2 and '/coop_' in t[1].lower() or (len(t) >= 2 and 'ads-smg' in l):
                assert ('models/human/animation/' + t[1]).lower() in names or 'coop_dp28' in t[1].lower() or 'coop_johnson' in t[1].lower(), ('row names a clip that is not staged', t)
                staged += 1
        print('rows naming staged clips:', staged)
    print('wrote', out, n, 'staged files', os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
