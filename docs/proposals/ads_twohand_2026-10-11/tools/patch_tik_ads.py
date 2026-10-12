"""Add the aimed gun-side rows to a staged revolver tik (idempotent): reload_ads_loaded / reload_ads_empty (cgame
shows them instead of `reload` in an aimed reload) and reload_end_ads (instead of `reload_end`; cgame ads-next).

    python patch_tik_ads.py <tik> <open clip> <open sound frame> <open sound> <close clip> <close sound frame> <close sound>
"""
import sys, re
tik, oc, of, os_, cc, cf, cs = sys.argv[1:8]
s = open(tik, 'rb').read().decode('latin-1')
nl = '\r\n' if '\r\n' in s else '\n'
s = re.sub(r'(?s)\t// HZM coop \[aimed revolver rows\].*?// HZM coop \[aimed revolver rows end\]' + nl, '', s)
blk = ['\t// HZM coop [aimed revolver rows] the gun worked LOW under the centre box: its own open / close eased and earlier',
       '\treload_ads_loaded\t%s' % oc, '\t{', '\t\tclient', '\t\t{', '\t\t\t%s sound %s' % (of, os_), '\t\t}', '\t}',
       '\treload_ads_empty\t%s' % oc, '\t{', '\t\tclient', '\t\t{', '\t\t\t%s sound %s' % (of, os_), '\t\t}', '\t}',
       '\treload_end_ads\t%s' % cc, '\t{', '\t\tclient', '\t\t{', '\t\t\t%s sound %s' % (cf, cs), '\t\t}', '\t}',
       '\t// HZM coop [aimed revolver rows end]', '']
if oc == '-':                      # no aimed open clip: only the close
    blk = blk[:1] + blk[15:]
m = re.search(r'(?m)^\treload_end\s', s)
assert m, 'no reload_end row'
s = s[:m.start()] + nl.join(blk) + s[m.start():]
open(tik, 'wb').write(s.encode('latin-1'))
print('patched', tik)
