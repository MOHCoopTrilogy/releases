"""SERVER-READ ROW LENGTHS of the double barrel (a new gun: there is no released tik to compare with, so the rows are
stated, and the 8 tiks are checked to be equal row for row) + the third-person torso rows it plays against the pump
gun's rows of the same states.

    python tools/dbs_rowlen.py            -> prints; writes build/dbs_rowlen.tsv
"""
import os, re, sys, io
import dbslib as L

W = os.path.join(L.ASSETS, 'models', 'weapons')
FIN = ('', '_gold', '_chrome', '_blued', '_bloody', '_camo_woodland', '_camo_winter', '_camo_desert')
FIXES = os.path.join(L.DOCS, 'tools', 'assets', 'fixes')


def clip(data):
    a = L.skdlib.read_skc(data)
    return a.numFrames, a.frameTime


def rows(text):
    t = re.sub(r'//[^\n]*', '', text)
    m = re.search(r'(?mi)^\s*animations\b', t)
    head, body = t[:m.start()], t[m.end():]
    path = ''
    for pm in re.finditer(r'(?mi)^\s*path\s+(\S+)', head):
        path = pm.group(1)
    out, d = {}, 0
    for ln in body.split('\n'):
        s = ln.strip()
        if d == 1:
            pm = re.match(r'(?i)\$?path\s+(\S+)', s)
            if pm:
                path = pm.group(1)
            rm = re.match(r'(\S+)\s+(\S+\.skc)\b', s, re.I)
            if rm:
                out[rm.group(1).lower()] = (path.rstrip('/') + '/' + rm.group(2)).lower()
        d += s.count('{') - s.count('}')
    return out


def read(vpath):
    p = os.path.join(L.ASSETS, vpath.replace('/', os.sep))
    if os.path.isfile(p):
        return open(p, 'rb').read()
    p = os.path.join(FIXES, vpath.replace('/', os.sep))
    if os.path.isfile(p):
        return open(p, 'rb').read()
    return L.vfs.read(vpath)


def main():
    out = []
    ref = None
    for f in FIN:
        t = io.open(os.path.join(W, 'coop_dbshotgun%s.tik' % f), encoding='latin-1').read()
        r = {n: (c,) + clip(read(c)) for n, c in rows(t).items()}
        if ref is None:
            ref = r
            for n, (c, nf, ft) in r.items():
                out.append('weapon tik row\t%s\t%s\t%d frames\t%.3f s' % (n, os.path.basename(c), nf, nf * ft))
        assert r == ref, ('finish tik differs', f)
    out.append('8 tiks: every row equal to the base tik\'s (%d rows)' % len(ref))
    al = open(os.path.join(FIXES, 'models', 'player', 'base', 'anims_shotgun.txt'), encoding='latin-1').read()
    ours = open(os.path.join(L.PROP, 'rows', 'tps_rows_coop_dbshotgun.txt'), encoding='latin-1').read()

    def alias(text, name):
        m = re.search(r'(?m)^\s*%s\s+(\S+\.skc)' % re.escape(name), text)
        assert m, name
        return 'models/human/animation/' + m.group(1).lower()
    for mine, pump in (('coop_dbs_stand_fire', 'shotgun_stand_fire'), ('coop_dbs_crouch_fire', 'shotgun_crouch_fire'), ('coop_dbs_reload_end', 'shotgun_reload_end')):
        a = clip(read(alias(ours, mine))); b = clip(L.vfs.read(alias(al, pump)))
        out.append('torso row\t%s\t%d frames %.3f s\tpump gun %s\t%d frames %.3f s\t%s' % (mine, a[0], a[0] * a[1], pump, b[0], b[0] * b[1], 'EQUAL' if a == b else 'DIFFERENT'))
        assert a == b
    for shared in ('shotgun_reload_start', 'shotgun_reload_loop', 'shotgun_reload_break'):
        try:
            b = clip(read(alias(al, shared)))
            out.append('torso row (shared, not changed)\t%s\t%d frames\t%.3f s' % (shared, b[0], b[0] * b[1]))
        except AssertionError:
            out.append('torso row (shared)\t%s\tnot in this anims_shotgun.txt' % shared)
    print('\n'.join(out))
    open(os.path.join(L.BUILD, 'dbs_rowlen.tsv'), 'w').write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()
