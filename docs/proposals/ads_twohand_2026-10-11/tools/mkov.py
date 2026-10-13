"""Test overlay for the two-handed pistol aim: harness plumbing (ovbase_1021.pk3) + every file under stage/models +
fps_anims_pistol.txt = the RELEASED fixes-pak copy with the given `<gun>_charge` rows repointed.

    python mkov.py <out.pk3> colt45=viewmodel/pistol/colt45_ads2h.skc [gun=clip ...] [--blend 0.3]
A row that does not exist yet (guns whose charge row is missing) is added to the ADS block. Every repoint is
asserted (a silently missing row would test the old pose).
"""
import sys, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.environ.get('MKOV_STAGE') or os.path.join(HERE, 'stage')      # shipcut.py points this at its filtered copy
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
        rowname = gun[4:] if gun.startswith('row:') else gun + '_charge'      # row:<name>=clip repoints any row
        xb = None
        if '@' in clip:                                   # clip@0.1 also sets the row's crossblend
            clip, xb = clip.split('@')
        rx = re.compile(r'(?m)^(\s*%s\s+)(\S+)([^\r\n]*)' % re.escape(rowname))
        m = rx.search(txt)
        if m:
            rest = m.group(3)
            if xb is not None:
                rest2 = re.sub(r'crossblend\s+[\d.]+', 'crossblend ' + xb, rest)
                rest = rest2 if rest2 != rest or ('crossblend ' + xb) in rest else rest + '\tcrossblend ' + xb
            txt = txt[:m.start()] + m.group(1) + clip + rest + txt[m.end():]
        else:
            anchor = '//===================== HZM coop ADS aim poses (additive) ====================='
            assert anchor in txt
            txt = txt.replace(anchor, anchor + nl + '\t%s\t\t\t%s\t\tcrossblend %s' % (rowname, clip, blend), 1)
        rows = [l for l in txt.splitlines() if l.split('//')[0].split()[:1] == [rowname]]
        assert len(rows) == 1 and clip in rows[0], (gun, rows)
        print('row:', rows[0].strip())
    extra = os.environ.get('MKOV_EXTRA')         # ;-separated files of whole rows (with their { } blocks) to append
    for ef in ([x for x in extra.split(';') if x] if extra else []):
        et = open(ef, 'rb').read().decode('latin-1').replace('\r\n', '\n').rstrip('\n')
        k = txt.rstrip().rfind('}')              # before the file's closing brace
        txt = txt[:k] + et.replace('\n', nl) + nl + txt[k:]
        print('extra rows from', os.path.basename(ef))
    blocks = os.environ.get('MKOV_BLOCK')        # row=file;row=file : a { } block inserted right after that row's line
    for item in ([x for x in blocks.split(';') if x] if blocks else []):
        rn, bf = item.split('=')
        bt = open(bf, 'rb').read().decode('latin-1').replace('\r\n', '\n').rstrip('\n')
        m = re.search(r'(?m)^\s*%s\s+\S+[^\r\n]*(\r?\n)' % re.escape(rn), txt)
        assert m, rn
        txt = txt[:m.end()] + bt.replace('\n', nl) + nl + txt[m.end():]
        print('block after row', rn)
    emit = os.environ.get('MKOV_EMIT')            # also write the staged tree (rows file + clips) for the proposal
    if emit:
        import shutil
        d = os.path.join(emit, 'models', 'player', 'base'); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'fps_anims_pistol.txt'), 'wb').write(txt.encode('latin-1'))
        for dd, _, fs in os.walk(STAGE):
            for f in fs:
                src = os.path.join(dd, f)
                dst = os.path.join(emit, os.path.relpath(src, STAGE))
                os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst)
        print('emitted staged tree to', emit)
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(os.path.join(HERE, os.environ.get('MKOV_BASE', 'ovbase_1021.pk3')))
        for i in b.infolist():
            z.writestr(i.filename, b.read(i.filename))
        z.writestr('models/player/base/fps_anims_pistol.txt', txt.encode('latin-1'))
        root = STAGE
        for d, _, fs in os.walk(root):
            for f in fs:
                p = os.path.join(d, f)
                arc = os.path.relpath(p, root).replace(os.sep, '/')
                z.write(p, arc); n += 1
                print('file:', arc, os.path.getsize(p))
    for gun, clip in pairs:
        assert 'models/human/animation/' + clip.split('@')[0] in zipfile.ZipFile(out).namelist(), clip
    print('wrote', out, n, 'staged files')


if __name__ == '__main__':
    main()
