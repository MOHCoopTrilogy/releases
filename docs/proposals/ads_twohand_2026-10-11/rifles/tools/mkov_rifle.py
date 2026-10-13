"""Test overlay for the rifle lane: harness plumbing (ovbase_1021.pk3, a copy of the pistol lane's) + every game file
staged under rifles/assets (clips, tiks, models/player/base/fps_anims_rifle.txt). *_phys.json / *.md are left out.

    python mkov_rifle.py <out.pk3> [--measure]
--measure also packs tools/measure_ov (nosmoke.py's measure-only tiks, never shipped) over the staged files.
"""
import sys, os, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', 'assets'))


def main():
    out = sys.argv[1]
    only = None
    measure = '--measure' in sys.argv
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(os.path.join(HERE, 'ovbase_1021.pk3'))
        for i in b.infolist():
            z.writestr(i.filename, b.read(i.filename))
        mr = os.path.join(HERE, 'measure_ov')
        # a measure-only tik REPLACES the staged one of the same path (nosmoke.py derives it from the staged tik - run
        # it again after boltcap.py changes a staged tik; checked below by the row both must carry)
        marcs = {os.path.relpath(os.path.join(d, f), mr).replace(os.sep, '/').lower() for d, _, fs in os.walk(mr) for f in fs} if measure else set()
        for d, _, fs in os.walk(ROOT):
            for f in sorted(fs):
                if f.endswith(('.json', '.md', '.bak')):
                    continue
                p = os.path.join(d, f)
                arc = os.path.relpath(p, ROOT).replace(os.sep, '/')
                if arc.lower() in marcs:
                    st, me = open(p, 'rb').read(), open(os.path.join(mr, arc.replace('/', os.sep)), 'rb').read()
                    assert (b'rechamber_ads' in st) == (b'rechamber_ads' in me), arc + ': the measure tik is older than the staged one - re-run nosmoke.py'
                    continue
                if only and not any(s in arc for s in only):
                    continue
                z.write(p, arc); n += 1
                print('file:', arc, os.path.getsize(p))
        if measure:
            mr = os.path.join(HERE, 'measure_ov')
            for d, _, fs in os.walk(mr):
                for f in sorted(fs):
                    p = os.path.join(d, f)
                    arc = os.path.relpath(p, mr).replace(os.sep, '/')
                    assert arc not in z.namelist(), arc + ': staged AND measure-only - derive the measure tik from the staged one (nosmoke.py does)'
                    z.write(p, arc)
                    print('MEASURE-ONLY file:', arc)
    print('wrote', out, n, 'staged files')


if __name__ == '__main__':
    main()
