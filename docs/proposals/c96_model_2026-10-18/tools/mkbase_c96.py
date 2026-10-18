"""Harness plumbing rebuilt on the weather.scr that is DEPLOYED now (the ADS lanes' ovbase_1021.pk3 carries the
1.10.21 file; the harness's game paks changed on 2026-10-13). Reads only; writes build/ovbase_c96.pk3.

    python tools/mkbase_dbs.py
"""
import zipfile, glob, os, re, sys
L = type('L', (), {'BUILD': r'C:/mohaa-coop-dev/docs/proposals/c96_model_2026-10-18/build'})

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
OLD = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\ads2h\ovbase_1021.pk3"
OUT = os.path.join(L.BUILD, 'ovbase_c96.pk3')


def main():
    old = zipfile.ZipFile(OLD)
    shader = old.read('scripts/zz_ironsight_test.shader')
    ow = old.read('coop_mod/weather.scr').decode('latin-1')
    cur = None
    for p in sorted(glob.glob(os.path.join(GOG, '*.pk3'))):
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower() == 'coop_mod/weather.scr':
                cur = (p, z.read(n).decode('latin-1'))
    cw = cur[1]
    hook = [l for l in ow.splitlines(True) if 'coop_isPoll' in l]
    assert len(hook) == 1, hook
    lines = ow.splitlines(True)
    anchor = lines[lines.index(hook[0]) - 1]
    assert cw.count(anchor) == 1, ('anchor', anchor, cw.count(anchor))
    m = re.search(r'(?m)^coop_is_test:', ow)
    start = ow.rfind('//TEST OVERLAY ONLY', 0, m.start())
    assert start > 0 and 'coop_is_test:' not in cw
    new = cw.replace(anchor, anchor + hook[0], 1)
    if not new.endswith('\n'):
        new += '\r\n'
    new += '\r\n' + ow[start:]
    d = 0
    for i, l in enumerate(new.splitlines()):
        c = l.split('//')[0]
        if re.match(r'^[A-Za-z_][A-Za-z0-9_ ]*:', c):
            assert d == 0, (i + 1, l)
        d += c.count('{') - c.count('}')
        assert d >= 0, (i + 1, l)
    assert d == 0 and '\u2014' not in new
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('scripts/zz_ironsight_test.shader', shader)
        z.writestr('coop_mod/weather.scr', new.encode('latin-1'))
    print('wrote', OUT, 'from', os.path.basename(cur[0]), len(cw), '->', len(new))


if __name__ == '__main__':
    main()
