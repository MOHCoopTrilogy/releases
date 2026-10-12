"""SMG lane test overlay: the harness plumbing (ovbase_1021.pk3, built by ..\\..\\tools\\mkbase.py - marker shader +
coop_mod/weather.scr with the test thread) + every file under ../assets (the staged tree, game paths).

    python mkov_smg.py <out.pk3> [--base]        --base = plumbing only (the RELEASED rows and clips: a "before" run)
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


def main():
    out = sys.argv[1]
    base_only = '--base' in sys.argv
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
                    z.write(p, arc); n += 1
    names = set(x.lower() for x in zipfile.ZipFile(out).namelist())
    if not base_only:
        rows = open(os.path.join(ASSETS, 'models', 'player', 'base', 'fps_anims_smg.txt'), encoding='latin-1').read().splitlines()
        staged = 0
        for l in rows:
            t = l.split('//')[0].split()
            if len(t) >= 2 and '/coop_' in t[1].lower() or (len(t) >= 2 and 'ads-smg' in l):
                assert ('models/human/animation/' + t[1]).lower() in names or 'coop_dp28' in t[1].lower() or 'coop_johnson' in t[1].lower(), ('row names a clip that is not staged', t)
                staged += 1
        print('rows naming staged clips:', staged)
    print('wrote', out, n, 'staged files', os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
