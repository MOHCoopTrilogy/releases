"""The row `reload_ads_empty` (= `reload_empty` under the name the integrated cgame looks for when an EMPTIED gun is
reloaded while aiming) in the 7 FINISH tiks, without re-running dbs_finish.py (which re-bakes the sheets and re-ranks).
The base tik gets the row from dbs_tik.py; this copies the base tik's block into each finish tik after its
`reload_empty` block and checks that nothing else differs from the base but what differed before.

    python tools/dbs_tikrow.py [--check]
"""
import os, sys, re, io
import dbslib as L

W = os.path.join(L.ASSETS, 'models', 'weapons')
FIN = ('gold', 'chrome', 'blued', 'bloody', 'camo_woodland', 'camo_winter', 'camo_desert')


def block(text, name):
    m = re.search(r'(?m)^\t%s\t[^\n]*\n\t\{\n.*?\n\t\}\n' % re.escape(name), text, re.S)
    assert m, name
    return m


def main():
    base = io.open(os.path.join(W, 'coop_dbshotgun.tik'), encoding='latin-1', newline='').read()
    nl = '\r\n' if '\r\n' in base else '\n'
    b = base.replace('\r\n', '\n')
    new = block(b, 'reload_ads_empty').group(0)
    assert block(b, 'reload_empty').group(0).replace('\treload_empty\t', '\treload_ads_empty\t', 1) == new
    n = 0
    for k in FIN:
        p = os.path.join(W, 'coop_dbshotgun_%s.tik' % k)
        raw = io.open(p, encoding='latin-1', newline='').read()
        t = raw.replace('\r\n', '\n')
        if '\treload_ads_empty\t' in t:
            print(k, 'has the row')
            continue
        m = block(t, 'reload_empty')
        assert m.group(0) == block(b, 'reload_empty').group(0), k
        t = t[:m.end()] + new + t[m.end():]
        d = 0
        for l in t.split('\n'):
            c = l.split('//')[0]
            d += c.count('{') - c.count('}')
            assert d >= 0
        assert d == 0
        n += 1
        if '--check' not in sys.argv:
            io.open(p, 'w', encoding='latin-1', newline='').write(t.replace('\n', '\r\n') if '\r\n' in raw else t)
        print(k, 'row added' if '--check' not in sys.argv else 'would add the row')
    print(n, 'finish tiks changed')


if __name__ == '__main__':
    main()
