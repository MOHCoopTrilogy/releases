"""Break-off of a revolver reload: the reload no longer restarts by itself after the owed shot (bug found by the
second-client run tl6, 2026-10-12).

RELOAD_<X>_CHECK_CONTINUE's `reload` latches Weapon::m_bShouldReload for the next round; only clip_add (a round
seated) or donereloading clears it. A fire press in FETCH (or during the opening) closes the gun with the latch still
set, so right after the owed shot the idle state saw RELOAD true and opened the gun again (0.1 - 0.2 s after the shot,
3 or 4 rounds in). A press in SEAT went through clip_add and did not. Now every break-off clears the latch in
RELOAD_<X>_BREAK_FIRE (`weaponcommand mainhand donereloading`) before the shot.

    python patch_breakfire.py <staged tree>       (idempotent; also in revstate.py for a fresh generation)
"""
import io, os, re, sys
p = os.path.join(sys.argv[1], 'coop_mod', 'player_Torso.st')
s = io.open(p, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
n = 0
for m in list(re.finditer(r'(?m)^state (RELOAD_\w+_BREAK_FIRE)\r?\n\{\r?\n(\tmovetype legs\r?\n)?', s))[::-1]:
    blk_end = s.index(nl + '}' + nl, m.end())
    if 'donereloading' in s[m.end():blk_end]:
        continue
    ins = ('\tentrycommands' + nl + '\t{' + nl +
           '\t\t// HZM coop [revolver reload 2026-10-12] the reload was broken off: drop the "wants to go on reloading" latch' + nl +
           '\t\t// (set by CHECK_CONTINUE, cleared only by a seated round) or the gun opens again right after the owed shot' + nl +
           '\t\tweaponcommand mainhand donereloading' + nl + '\t}' + nl)
    s = s[:m.end()] + ins + s[m.end():]
    n += 1
dp = 0
for ln in s.replace('\r', '').split('\n'):
    c = ln.split('//')[0]
    dp += c.count('{') - c.count('}')
    assert dp >= 0
assert dp == 0
io.open(p, 'w', encoding='latin-1', newline='').write(s)
print('BREAK_FIRE states patched:', n, '| total with donereloading:', len(re.findall(r'weaponcommand mainhand donereloading', s)))
