r"""M1919 .30 cal portable: the HIP reload row lives in a SHARED file - a PATCH, not a staged copy.

`coopr_m1919_30cal_reload` (the hip hands row, rounds left) is a row of models/player/base/anims_shared.txt (reload
audit 2026-10-05), a file every lane's guns share: the lane does not stage a copy of it. This repoints that ONE row to
the rebuilt hip clip (tools/beltbake.py: closed hands, 97 frames as before):

    coopr_m1919_30cal_reload   viewmodel/coop_reload/m1919_reload.skc  ->  viewmodel/coop_m1919/coop_m1919_reload_hip.skc

Every other M1919 row is an ADDED row of the lane's own fps_anims_mg.txt (tools/stage_rows.py).

    python patch_m1919_rows.py <tree>              a mod / fixes tree (edits <tree>/models/player/base/anims_shared.txt)
    python patch_m1919_rows.py --pk3 <in> <out>    a test overlay: <in> + the patched file (read from the fixes tree)
Idempotent; refuses when the row is not exactly one line.
"""
import sys, os, re, zipfile
REL = 'models/player/base/anims_shared.txt'
ROW = 'coopr_m1919_30cal_reload'
OLD = 'viewmodel/coop_reload/m1919_reload.skc'
NEW = 'viewmodel/coop_m1919/coop_m1919_reload_hip.skc'
FIXES = r"C:\mohaa-coop-dev\docs\tools\assets\fixes"


def patch(txt):
    rx = re.compile(r'(?m)^(\s*%s\s+)(\S+)' % re.escape(ROW))
    ms = rx.findall(txt)
    assert len(ms) == 1, ('rows named %s' % ROW, len(ms))
    if ms[0][1] == NEW:
        return txt, False
    assert ms[0][1] == OLD, ms[0][1]
    return rx.sub(lambda m: m.group(1) + NEW, txt), True


if __name__ == '__main__':
    if sys.argv[1] == '--pk3':
        src, dst = sys.argv[2], sys.argv[3]
        txt, ch = patch(open(os.path.join(FIXES, REL.replace('/', os.sep)), 'rb').read().decode('latin-1'))
        with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
            b = zipfile.ZipFile(src)
            for i in b.infolist():
                if i.filename != REL:
                    z.writestr(i.filename, b.read(i.filename))
            z.writestr(REL, txt.encode('latin-1'))
        print('wrote', dst, '(row repointed)' if ch else '(row was already repointed)')
    else:
        p = os.path.join(sys.argv[1], REL.replace('/', os.sep))
        txt, ch = patch(open(p, 'rb').read().decode('latin-1'))
        if ch:
            open(p, 'wb').write(txt.encode('latin-1'))
        print(p, 'patched' if ch else 'already patched')
