"""Test overlay of the heavy lane: the harness plumbing (ovbase_1021.pk3: weather.scr hook + marker shader, built by
the pistol lane's mkbase.py) + every file under heavy/assets (game paths).

    python mkov_h.py <out.pk3> [--before]      --before: the rows files as RELEASED (no staged rows), nothing else staged
"""
import sys, os, zipfile, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv


def main():
    out = sys.argv[1]
    before = '--before' in sys.argv
    base = os.path.join(hv.SCR, 'ovbase_1021.pk3')
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(base)
        for i in b.infolist():
            z.writestr(i.filename, b.read(i.filename))
        if before:
            for cls in ('mg', 'shotgun'):
                rel = 'models/player/base/fps_anims_%s.txt' % cls
                z.write(os.path.join(hv.FIXES, rel.replace('/', os.sep)), rel); n += 1
        else:
            for d, _, fs in os.walk(hv.ASSETS):
                for f in fs:
                    p = os.path.join(d, f)
                    arc = os.path.relpath(p, hv.ASSETS).replace(os.sep, '/')
                    if arc.split('/')[0] not in ('models', 'scripts', 'sound', 'textures', 'coop_mod', 'ui', 'global'):
                        continue
                    z.write(p, arc); n += 1
    print('wrote', out, n, 'files', '(BEFORE: released rows)' if before else '')


if __name__ == '__main__':
    main()
