"""Test overlay pk3 for the new C96:  ship2 (the pistol lane's C96 hands / rows / Trench) + this cut (mesh, sheet, tiks, gun clips)
+ models/player/base/fps_anims_pistol.txt = the RELEASED fixes-pak copy with ship2's row change (pins out, four rows in).
    python mkov_c96.py <out.pk3>
Nothing is written anywhere but <out.pk3>.
"""
import os, sys, re, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c96lib as L

SHIP2 = os.path.join(L.ROOT, '..', 'ads_twohand_2026-10-11', 'ship2')
GOGFIX = r"G:/GOG/Medal of Honor - Allied Assault War Chest/maintt/zzzzzzzzzz_coop_fixes.pk3"
LIVEFIX = os.path.join(L.ROOT, '..', '..', 'tools', 'assets', 'fixes')
ROWS = 'models/player/base/fps_anims_pistol.txt'


def pistol_rows():
    with zipfile.ZipFile(GOGFIX) as zf:
        txt = zf.read(ROWS).decode('latin-1')
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)
    n0 = len(lines)
    lines = [l for l in lines if l.split('//')[0].split()[:1] not in (['coopr_mauser_c96_charge'], ['coopr_mauser_c96_idle'])]
    assert n0 - len(lines) == 2, n0 - len(lines)
    add = [l for l in open(os.path.join(SHIP2, 'ROWS_fps_anims_pistol.txt'), 'rb').read().decode('latin-1').replace('\r\n', '\n').split('\n')
           if l.startswith('\t') or l.startswith('//=')]
    add = [l for l in add if l.strip()]
    k = max(i for i, l in enumerate(lines) if l.strip() == '}')
    lines = lines[:k] + add + lines[k:]
    return nl.join(lines).encode('latin-1')


def main():
    out = sys.argv[1]
    files = {}
    for root in ((SHIP2,) if os.environ.get('C96_OLD') else (SHIP2, L.STAGE)):
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root).replace(os.sep, '/')
                if rel.upper().endswith('.TXT') and '/' not in rel:
                    continue                      # FILES.txt / ROWS_*.txt of ship2
                files[rel] = p
    base = zipfile.ZipFile(os.path.join(L.BUILD, 'ovbase_c96.pk3'))
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as z:
        for n in base.namelist():
            z.writestr(n, base.read(n))
        for rel in sorted(files):
            z.write(files[rel], rel)
        z.writestr(ROWS, pistol_rows())
    print('overlay', out, len(files) + 1, 'files')


if __name__ == '__main__':
    main()
