"""Test overlay for the two-handed pistol aim: harness plumbing (ovbase_1021.pk3) + every file under stage/models +
fps_anims_pistol.txt = the RELEASED fixes-pak copy with the given `<gun>_charge` rows repointed.

    python mkov.py <out.pk3> colt45=viewmodel/pistol/colt45_ads2h.skc [gun=clip ...] [--blend 0.3]
A row that does not exist yet (guns whose charge row is missing) is added to the ADS block. Every repoint is
asserted (a silently missing row would test the old pose).
"""
import sys, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
FX = r"C:\mohaa-coop-dev\docs\tools\assets\fixes\models\player\base\fps_anims_pistol.txt"


def main():
    out = sys.argv[1]
    blend = '0.3'
    pairs = []
    args = sys.argv[2:]
    while args:
        a = args.pop(0)
        if a == '--blend':
            blend = args.pop(0)
        else:
            pairs.append(a.split('='))
    txt = open(FX, 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in txt else '\n'
    for gun, clip in pairs:
        rx = re.compile(r'(?m)^(\s*%s_charge\s+)(\S+)([^\r\n]*)' % re.escape(gun))
        m = rx.search(txt)
        if m:
            txt = txt[:m.start()] + m.group(1) + clip + m.group(3) + txt[m.end():]
        else:
            anchor = '//===================== HZM coop ADS aim poses (additive) ====================='
            assert anchor in txt
            txt = txt.replace(anchor, anchor + nl + '\t%s_charge\t\t\t%s\t\tcrossblend %s' % (gun, clip, blend), 1)
        rows = [l for l in txt.splitlines() if l.split('//')[0].split()[:1] == ['%s_charge' % gun]]
        assert len(rows) == 1 and clip in rows[0], (gun, rows)
        print('row:', rows[0].strip())
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(os.path.join(HERE, 'ovbase_1021.pk3'))
        for i in b.infolist():
            z.writestr(i.filename, b.read(i.filename))
        z.writestr('models/player/base/fps_anims_pistol.txt', txt.encode('latin-1'))
        root = os.path.join(HERE, 'stage')
        for d, _, fs in os.walk(os.path.join(root, 'models')):
            for f in fs:
                p = os.path.join(d, f)
                arc = os.path.relpath(p, root).replace(os.sep, '/')
                z.write(p, arc); n += 1
                print('file:', arc, os.path.getsize(p))
    for gun, clip in pairs:
        assert 'models/human/animation/' + clip in zipfile.ZipFile(out).namelist(), clip
    print('wrote', out, n, 'staged files')


if __name__ == '__main__':
    main()
