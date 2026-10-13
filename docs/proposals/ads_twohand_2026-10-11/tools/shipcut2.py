"""shipcut2.py - FOLLOW-UP CUT (ship2/): the Mauser C96 + Trench C96, nothing else (pistol lane, 2026-10-13 pm).

    python shipcut2.py <ship2 dir>            copies from ./stage, writes ROWS_fps_anims_pistol.txt and FILES.txt

The cut is ADDITIVE to ship/ (cut v2): only files of the two guns that v2 held out. No shared table is in it - the
hip rows and the torso row of the C96 are the released ones. The staged tree holds more than this (Luger toggle flick,
Welrod bolt sound, finish texture lifts, the M10): none of that was run and none of it is copied.
"""
import sys, os, re, shutil, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, 'stage')
IN_RX = [r'^models/weapons/mauser_c96[^/]*\.tik$', r'^models/weapons/coop_c96/', r'^models/weapons/coop_c96trench/',
         r'^textures/coop_c96/', r'^textures/coop_c96trench/', r'^scripts/coop_c96_clip\.shader$',
         r'^models/human/animation/viewmodel/pistol/coop_c96_[^/]*\.skc$']
PINS = ['coopr_mauser_c96_charge', 'coopr_mauser_c96_idle']


def main(out):
    assert not os.path.isdir(out) or not os.listdir(out), 'ship2 exists and is not empty: it is frozen once written'
    files = []
    for d, _, fs in os.walk(STAGE):
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), STAGE).replace(os.sep, '/')
            if any(re.search(rx, rel) for rx in IN_RX):
                dst = os.path.join(out, rel.replace('/', os.sep))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(d, f), dst)
                files.append(rel)
    rows = open(os.path.join(HERE, 'rows_p12_c96.txt'), 'rb').read().decode('latin-1').replace('\r\n', '\n')
    txt = ('// FOLLOW-UP CUT (ship2), models/player/base/fps_anims_pistol.txt - apply to the file that carries cut v2:\n'
           '//   1. REMOVE the two pin rows of the held-out C96:  %s\n'
           '//   2. ADD the rows below before the file\'s closing brace.\n'
           '// Nothing else in any player table changes: the hip row coopr_mauser_c96_reload (anims_shared.txt) and the torso row\n'
           '// coop_reload_c96 with its stripper-clip attach timeline are the RELEASED ones.\n' % ', '.join(PINS)) + rows
    open(os.path.join(out, 'ROWS_fps_anims_pistol.txt'), 'w', newline='\n').write(txt)
    files.sort()
    with open(os.path.join(out, 'FILES.txt'), 'w', newline='\n') as fh:
        for rel in files:
            b = open(os.path.join(out, rel.replace('/', os.sep)), 'rb').read()
            fh.write('%-78s %8d  %s\n' % (rel, len(b), hashlib.md5(b).hexdigest()[:8]))
    print('ship2: %d files, %d bytes' % (len(files), sum(os.path.getsize(os.path.join(out, r.replace('/', os.sep))) for r in files)))


if __name__ == '__main__':
    main(sys.argv[1])
