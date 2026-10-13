"""The SHIP CUT's frozen file list: every file the integration takes from this folder, with size and sha256.

    python tools/ship_manifest.py            writes DBS_SHIP.manifest.tsv
    python tools/ship_manifest.py --check    exit 1 when a frozen file changed / is missing / a new one appeared
"""
import os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
OUT = os.path.join(PROP, 'DBS_SHIP.manifest.tsv')
DIRS = ['assets', 'rows', os.path.join('wiring', 'gen', 'new')]
TEXT = ('tik', 'txt', 'cfg', 'py', 'patch', 'shader', 'json', 'scr', 'tsv', 'md', 'urc')
FILES = [os.path.join('wiring', 'patch_torso_dbs.py'), os.path.join('wiring', 'patch_cgame_loot_dbs.py'), os.path.join('wiring', 'stage_armory_dbs.py'),
         os.path.join('wiring', 'gen', 'armory_dbs.patch'), os.path.join('wiring', 'gen', 'generators.patch'), 'sights_override.json',
         os.path.join('tools', 'sightrow_dbs.py')]


def listing():
    rows = []
    for d in DIRS:
        for r, _, fs in os.walk(os.path.join(PROP, d)):
            for f in fs:
                rows.append(os.path.relpath(os.path.join(r, f), PROP).replace(os.sep, '/'))
    rows += [f.replace(os.sep, '/') for f in FILES]
    out = []
    for rel in sorted(rows):
        data = open(os.path.join(PROP, rel.replace('/', os.sep)), 'rb').read()
        if rel.rsplit('.', 1)[-1].lower() in TEXT:          # git's autocrlf may rewrite line ends on a checkout: not a change
            data = data.replace(b'\r\n', b'\n')
        out.append('%s\t%d\t%s' % (rel, len(data), hashlib.sha256(data).hexdigest()))
    return out


def main():
    now = listing()
    if '--check' in sys.argv:
        old = open(OUT).read().split('\n')
        old = [l for l in old if l and not l.startswith('#')]
        a, b = set(old), set(now)
        for l in sorted(a - b):
            print('CHANGED OR GONE:', l.split('\t')[0])
        for l in sorted(b - a):
            print('NEW OR CHANGED :', l.split('\t')[0])
        print('%d frozen files, %s' % (len(old), 'all as frozen' if a == b else 'NOT as frozen'))
        sys.exit(0 if a == b else 1)
    open(OUT, 'w', newline='\n').write('# path (under docs/proposals/dbshotgun_2026-10-12)\tbytes\tsha256\n' + '\n'.join(now) + '\n')
    print('wrote', OUT, len(now), 'files', sum(int(l.split('\t')[1]) for l in now), 'bytes')


if __name__ == '__main__':
    main()
