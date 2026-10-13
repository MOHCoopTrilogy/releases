"""SMG lane test overlay: the harness plumbing (ovbase_1021.pk3, built by ..\\..\\tools\\mkbase.py - marker shader +
coop_mod/weather.scr with the test thread) + every file under ../assets (the staged tree, game paths).

    python mkov_smg.py <out.pk3> [--base] [--extra <other assets dir>]        --base = plumbing only (the RELEASED rows and clips: a "before" run)
Asserts that every clip a staged fps_anims row names and that lives under viewmodel/coop_* or is staged is in the pak.
"""
import sys, os, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\adssmg"
BASE = os.path.join(SCR, 'ovbase_1021.pk3')


def ai_poll(src):
    """TEST OVERLAY ONLY: the harness thread also spawns one AI in front of the player when the cvar coop_isAi changes
    (the dev `spawn` command needs cheats, which the mod's server start switches off) - to look at a gun in an AI's
    hands. Spliced into the test thread's loop; brace depth is checked (a script that fails to compile says nothing)."""
    import re
    nl = '\r\n' if '\r\n' in src else '\n'
    k = src.rfind('coop_is_test:')
    assert k > 0
    head, body = src[:k], src[k:]
    nl = '\r\n' if '\r\n' in body else '\n'          # the spliced test thread has its own line ends
    a1 = '\tlocal.lastF = ""' + nl
    assert body.count(a1) == 1
    body = body.replace(a1, a1 + '\tlocal.lastA = ""' + nl)
    a2 = '\t\twaitframe' + nl + '\t}' + nl + '}end'
    assert body.count(a2) == 1, body[-200:]
    blk = nl.join(['\t\tlocal.a = getcvar( "coop_isAi" )',
                   '\t\tif( local.a != "" && local.a != local.lastA && $player != NULL && $player.size >= 1 ){',
                   '\t\t\tlocal.lastA = local.a',
                   '\t\t\tlocal.p = $player[1]',
                   '\t\t\tlocal.fw = angles_toforward local.p.viewangles',
                   '\t\t\tlocal.org = local.p.origin + local.fw * 230',
                   '\t\t\tlocal.ai = spawn local.a "origin" local.org',
                   '\t\t\tlocal.p notarget 0',
                   '\t\t\tprintln( "^~^~^ ISTEST ai " + local.a + " at " + local.org )',
                   '\t\t}', ''])
    body = body.replace(a2, blk + a2)
    new = head + body
    d = 0
    for i, l in enumerate(new.splitlines()):
        c = l.split('//')[0]
        if re.match(r'^[A-Za-z_][A-Za-z0-9_ ]*:', c):
            assert d == 0, ('depth at label', i + 1, l[:50])
        d += c.count('{') - c.count('}')
        assert d >= 0, (i + 1, l)
    assert d == 0
    return new


ROWS = 'models/player/base/fps_anims_smg.txt'
# --integ: files of the lane tree that the integration did NOT ship under these names (it shipped the MP40's aimed clip
# as coop_mp40_reload_ads.skc; this one would replace the RELEASED clip the generic mp40_reload_ads row still names)
INTEG_SKIP = {'models/human/animation/viewmodel/mp40/mp40_reload_ads.skc'}


def integ_rows():
    """fps_anims_smg.txt for a run ON TOP OF THE INTEGRATED GAME (2026-10-13: MP40 / Silenced MP40 / MP40 R2 are live with
    per-weapon rows coopr_mp40_*; the generic mp40_* rows are the RELEASED ones again and the Grease Guns, the Silenced
    PPS-43 and the MP18 read them): the live file, every generic mp40_* row left as it is, every other row of the lane
    file put on top (changed clip in place, new row before the closing brace)."""
    import re
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'ironsights_2026-09-28', 'tools')))
    import vfs
    live = vfs.read(ROWS).decode('latin-1')
    nl = '\r\n' if '\r\n' in live else '\n'
    lane = open(os.path.join(ASSETS, ROWS.replace('/', os.sep)), encoding='latin-1').read()
    rx = r'(?m)^[ \t]+(\S+)[ \t]+(\S+\.skc)[^\r\n]*'
    have = dict(re.findall(rx.replace('[^\\r\\n]*', ''), live))
    new, chg, kept = [], 0, 0
    for m in re.finditer(rx, lane):
        row, clip = m.group(1), m.group(2)
        if row.startswith('mp40_'):
            kept += int(have.get(row) != clip)
            continue
        if row not in have:
            new.append(m.group(0))
        elif have[row] != clip:
            live, k = re.subn(r'(?m)^([ \t]+%s[ \t]+)\S+\.skc' % re.escape(row), lambda q: q.group(1) + clip, live)
            assert k == 1, (row, k)
            chg += 1
    k = live.rstrip().rfind('}')
    live = live[:k] + '\t// ads-smg lane rows on the integrated file (mkov_smg --integ)' + nl + nl.join(new) + nl + live[k:]
    print('--integ: live rows %d, lane rows added %d, repointed %d, generic mp40_* rows left as live %d' % (len(have), len(new), chg, kept))
    return live


def main():
    out = sys.argv[1]
    base_only = '--base' in sys.argv
    integ = '--integ' in sys.argv
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(BASE)
        for i in b.infolist():
            data = b.read(i.filename)
            if i.filename == 'coop_mod/weather.scr':
                data = ai_poll(data.decode('latin-1')).encode('latin-1')
            z.writestr(i.filename, data)
        if not base_only:
            for d, _, fs in os.walk(ASSETS):
                for f in fs:
                    p = os.path.join(d, f)
                    arc = os.path.relpath(p, ASSETS).replace(os.sep, '/')
                    if integ and (arc.lower() == ROWS or arc.lower() in INTEG_SKIP):
                        continue
                    z.write(p, arc); n += 1
            if integ:
                z.writestr(ROWS, integ_rows().encode('latin-1')); n += 1
            # rows that live in anims_shared.txt (rows_extra.json 'shared'): the live pak's own copy with those rows
            # repointed goes into the overlay; NOT staged under assets (a staged copy of a shared file goes stale)
            import json, re
            ex = json.load(open(os.path.join(HERE, 'rows_extra.json')))
            if ex.get('shared'):
                sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'ironsights_2026-09-28', 'tools')))
                import vfs
                txt = vfs.read('models/player/base/anims_shared.txt').decode('latin-1')
                for row, clip in ex['shared']:
                    txt, k = re.subn(r'(?m)^(\s*%s\s+)\S+' % re.escape(row), lambda m: m.group(1) + clip, txt)
                    assert k == 1, (row, k)
                    print('anims_shared.txt: %s -> %s' % (row, clip))
                z.writestr('models/player/base/anims_shared.txt', txt.encode('latin-1')); n += 1
            for xd in [sys.argv[i + 1] for i, v in enumerate(sys.argv) if v == '--extra']:
                for d, _, fs in os.walk(xd):          # another proposal's staged tree (e.g. the approved MP18 skin)
                    for f in fs:
                        p = os.path.join(d, f)
                        z.write(p, os.path.relpath(p, xd).replace(os.sep, '/')); n += 1
    names = set(x.lower() for x in zipfile.ZipFile(out).namelist())
    if not base_only:
        rows = zipfile.ZipFile(out).read(ROWS).decode('latin-1').splitlines()
        staged = 0
        for l in rows:
            t = l.split('//')[0].split()
            if len(t) >= 2 and '/coop_' in t[1].lower() or (len(t) >= 2 and 'ads-smg' in l):
                if integ and ('models/human/animation/' + t[1]).lower() not in names:
                    import vfs                  # a row the integration shipped: its clip is in the live pak
                    assert vfs.read('models/human/animation/' + t[1]) is not None, ('row names a clip that is neither staged nor live', t)
                    continue
                assert ('models/human/animation/' + t[1]).lower() in names or 'coop_dp28' in t[1].lower() or 'coop_johnson' in t[1].lower(), ('row names a clip that is not staged', t)
                staged += 1
        print('rows naming staged clips:', staged)
    print('wrote', out, n, 'staged files', os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
