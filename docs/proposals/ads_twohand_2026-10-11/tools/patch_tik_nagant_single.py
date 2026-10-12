"""Staged Nagant tik: reload_single_ads (cgame ads-next shows it instead of reload_single in an aimed reload) - the same
clip and sound, the fired case only nudged out of the gate (the hip row throws it 85-195 u/s up so it is seen from the
hip; with the gun worked low under the sights that case crossed the centre of the screen). Idempotent."""
import re, sys
tik = sys.argv[1]
vel = sys.argv[2] if len(sys.argv) > 2 else 'crandom 10 crandom 10 range 30 16'
s = open(tik, 'rb').read().decode('latin-1')
nl = '\r\n' if '\r\n' in s else '\n'
s = re.sub(r'(?s)\t// HZM coop \[aimed loop row\].*?// HZM coop \[aimed loop row end\]' + nl, '', s)
m = re.search(r'(?ms)^\treload_single[ \t]+(\S+)[^\n]*\n\t\{.*?\n\t\}[^\n]*\n', s)
assert m, 'no reload_single block'
blk = m.group(0)
new = re.sub(r'^\treload_single', '\treload_single_ads', blk, count=1)
new, n = re.subn(r'randvel [^\r\n]*', 'randvel ' + vel, new, count=1)
assert n == 1
new = '\t// HZM coop [aimed loop row] aimed: the case is only nudged out (see patch_tik_nagant_single.py)' + nl + new + '\t// HZM coop [aimed loop row end]' + nl
s = s[:m.end()] + new + s[m.end():]
open(tik, 'wb').write(s.encode('latin-1'))
print('patched', tik, 'randvel', vel)
