"""ovbase_1021_p2.pk3 = ovbase_1021.pk3 with the harness poll (coop_mod/weather.scr coop_is_test) able to place / give
ANOTHER player: cvar coop_isPlayer (1-based index into $player; unset / out of range = 1, as before). TEST OVERLAY ONLY.
Used by run_break2.py (the second client is the one measured). mkov.py picks the base with MKOV_BASE."""
import zipfile, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = zipfile.ZipFile(os.path.join(HERE, 'ovbase_1021.pk3'))
out = os.path.join(HERE, 'ovbase_1021_p2.pk3')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for i in src.infolist():
        d = src.read(i.filename)
        if i.filename == 'coop_mod/weather.scr':
            t = d.decode('latin-1')
            a = '\t\t\tlocal.p = $player[1]\n'
            nl = '\n'
            if a not in t:
                a = a.replace('\n', '\r\n'); nl = '\r\n'
            assert t.count(a) == 1, t.count(a)
            b = ('\t\t\tlocal.pn = int( getcvar( "coop_isPlayer" ) )' + nl +
                 '\t\t\tif( local.pn < 1 || local.pn > $player.size ){ local.pn = 1 }' + nl +
                 '\t\t\tlocal.p = $player[local.pn]' + nl +
                 '\t\t\tprintln( "^~^~^ ISTEST player " + local.pn + " of " + $player.size )' + nl)
            t = t.replace(a, b)
            dp = 0
            for ln in t.replace('\r', '').split('\n'):
                c = ln.split('//')[0]
                dp += c.count('{') - c.count('}')
                assert dp >= 0
            assert dp == 0
            d = t.encode('latin-1')
        z.writestr(i.filename, d)
print('wrote', out)
