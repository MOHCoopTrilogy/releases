"""Prone pistol reloads run the full length (2026-10-12, coordinator's decision).

Before: player_Torso.st RELOAD_PISTOL played `coop_prone_reload_pistol` (pistol_prone_reload.skc, 15 f x 0.1 s = 1.50 s)
for EVERY pistol in prone and left on ANIMDONE_TORSO, while the first-person reload clips (hip AND aimed) are 73 frames
= 2.43 s (Beretta 63 = 2.10 s): in prone the server ended the reload 0.93 s early, the view clip was cut (the
Hi-Standard lost its rack), and every pistol showed a Colt magazine in the body's hand.

After: one prone alias per standing alias, on the prone body clip retimed to the standing length
(coop_pistol_prone_reload_73.skc / _63.skc, hand events lined up with the standing clip), carrying the STANDING alias's
own server commands (its magazine model, clip_fill at the same frame). Prone = standing in time and in ammo timing.

    python patch_prone_reload.py <staged tree>      (patches <tree>/models/player/base/anims_shared.txt and
                                                     <tree>/coop_mod/player_Torso.st in place; idempotent)
"""
import sys, os, re, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
vfs = gunskc.R.vfs
tree = sys.argv[1]
MARK = 'HZM coop [prone pistol reload 2026-10-12]'
# prone alias, standing alias it mirrors, the file the standing alias lives in, prone clip, state-file condition
SET = [
    ('coop_prone_reload_beretta', 'beretta_reload', 'anims_beretta.txt', 63, 'IS_WEAPON_ACTIVE "mainhand" "Beretta"'),
    ('coop_prone_reload_p38', 'p38_reload', 'anims_pistol.txt', 73, 'IS_WEAPON_ACTIVE "mainhand" "Walther P38"'),
    ('coop_prone_reload_histandard', 'histandard_reload', 'anims_pistol.txt', 73, 'IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"'),
    ('coop_prone_reload_c96', 'coop_reload_c96', 'anims_shared.txt', 73, 'IS_WEAPON_ACTIVE "mainhand" "Mauser C96"'),
    ('coop_prone_reload_pistol', 'pistol_reload', 'anims_pistol.txt', 73, ''),
]


def text_of(fn):
    f = os.path.join(tree, 'models', 'player', 'base', fn)
    if os.path.isfile(f):
        return io.open(f, encoding='latin-1', newline='').read()
    return vfs.read('models/player/base/' + fn).decode('latin-1')


def block_of(txt, alias):
    """the { server { ... } } block that follows the alias row (commands only, comments stripped)"""
    m = re.search(r'(?m)^[ \t]*%s[ \t]+\S+\.skc[^\r\n]*\r?\n[ \t]*\{' % re.escape(alias), txt)
    assert m, alias
    i = m.end() - 1
    depth, j = 0, i
    while True:
        if txt[j] == '{':
            depth += 1
        elif txt[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    body = txt[i:j + 1].replace('\r', '')
    cmds = []
    for ln in body.split('\n'):
        t = ln.split('//')[0].strip()
        if re.match(r'(first|last|entry|exit|\d+)\s', t):
            cmds.append(re.sub(r'\s+', ' ', t))
    assert cmds and cmds[0].startswith('first reloadweapon'), (alias, cmds)
    return cmds


# ---------------------------------------------------------------- anims_shared.txt
p = os.path.join(tree, 'models', 'player', 'base', 'anims_shared.txt')
s = io.open(p, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
if MARK in s:                                   # idempotent: drop our earlier block, restore the anchor row
    a = s.index('\t// ' + MARK)
    b = s.index('\t// end ' + MARK)
    b = s.index(nl, b) + len(nl)
    s = s[:a] + s[b:]
else:                                           # first run: remove the 1.50 s alias (row + its block)
    m = re.search(r'(?m)^[ \t]*coop_prone_reload_pistol[ \t]+weapon_pistol/prone/pistol_prone_reload\.skc[^\r\n]*\r?\n[ \t]*\{', s)
    assert m, 'coop_prone_reload_pistol row not found'
    j = m.end() - 1
    depth = 0
    while True:
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    j = s.index(nl, j) + len(nl)
    s = s[:m.start()] + '@@PRONE@@' + s[j:]
if '@@PRONE@@' not in s:
    m = re.search(r'(?m)^[ \t]*coop_prone_aim_pistol[ \t]+\S+[^\r\n]*\r?\n', s)
    assert m
    s = s[:m.end()] + '@@PRONE@@' + s[m.end():]
L = ['\t// ' + MARK + ' the prone body clip retimed to the STANDING reload\'s length (73 f = 2.43 s, Beretta 63 f =',
     '\t// 2.10 s; hand off the gun / back on it at the standing clip\'s frames) with the standing alias\'s own commands: the',
     '\t// reload lasts as long lying down as standing, so the first-person clip (hip and aimed) is no longer cut 0.93 s',
     '\t// short (the Hi-Standard lost its rack), and each pistol shows its own magazine. Was: one 1.50 s alias for all.']
for alias, stand, fn, n, cond in SET:
    cmds = block_of(text_of(fn) if fn != 'anims_shared.txt' else s, stand)
    L += ['\t%s\tweapon_pistol/prone/coop_pistol_prone_reload_%d.skc' % (alias, n), '\t{', '\t\tserver', '\t\t{']
    L += ['\t\t\t' + c for c in cmds]
    L += ['\t\t}', '\t}']
L += ['\t// end ' + MARK]
s = s.replace('@@PRONE@@', nl.join(L) + nl)
io.open(p, 'w', encoding='latin-1', newline='').write(s)
print('anims_shared.txt:', len(SET), 'prone aliases')

# ---------------------------------------------------------------- player_Torso.st
p = os.path.join(tree, 'coop_mod', 'player_Torso.st')
s = io.open(p, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
a = s.index('state RELOAD_PISTOL')
b = s.index('states', a)
blk = s[a:b]
lines = blk.split(nl)
keep = [ln for ln in lines if 'coop_prone_reload_' not in ln and MARK not in ln]
k = next(i for i, ln in enumerate(keep) if ln.strip() == 'action')
assert keep[k + 1].strip() == '{'
new = ['\t\t// ' + MARK + ' per pistol, each as long as its standing reload (anims_shared.txt); first match wins']
for alias, stand, fn, n, cond in SET:
    new.append('\t\t%s\t: POSITION_TYPE "prone"%s' % (alias, (' ' + cond) if cond else ''))
keep[k + 2:k + 2] = new
s = s[:a] + nl.join(keep) + s[b:]
io.open(p, 'w', encoding='latin-1', newline='').write(s)
print('player_Torso.st: RELOAD_PISTOL prone lines', len(new) - 1)
