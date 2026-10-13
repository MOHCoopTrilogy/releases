"""one-off source patch of srvrows.py: declared server-side changes + stale-base (3-way merge) handling. Idempotent."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, 'srvrows.py')
s = open(p, encoding='utf-8').read()
if 'DECLARED = [' in s:
    print('already patched')
    raise SystemExit
a = "CLIENT_OK = re.compile("
b = '''# Server-side changes that were DECIDED (not side effects): reported as `decl`, never as FAIL. (file tail, row regex, why)
DECLARED = [
    ('m10_revolver.tik', r'reload|reload_end|reload_single',
     'S&W M10 loads round by round (revolver list A-C, 2026-10-12; listen-server runs tn2 / pa5 / pa12) - a per-round reload cannot be client-only'),
    ('webley_revolver.tik', r'reload|reload_end|reload_single',
     'Webley: open / close 0.53 -> 0.8 s, one round 0.53 -> 0.8 s (coordinator 2026-10-12, list item C "give them time and weight"; webslow.py; runs tl9 tn1 ts1)'),
    ('nagant_revolver.tik', r'reload_single', 'Nagant: one round 0.53 -> 0.9 s (same decision; runs tn3 tu1)'),
    ('anims_pistol.txt', r'nagantrev_reload_loop|webley_reload_end|webley_reload_loop', 'the torso rows of the two revolver decisions above'),
    ('anims_shared.txt', r'coop_reload_webley_start', 'the torso row of the Webley decision above'),
    ('anims_shared.txt', r'coop_prone_reload_pistol',
     'prone pistol reload as long as the standing one, 1.50 -> 2.43 s (coordinator 2026-10-12; patch_prone_reload.py; run tl8)'),
]
# staged text files that are SNAPSHOTS of a mod-tree file: (staged path, mod path, mod commit the snapshot was taken from).
# The mod file may have moved on since; shipping = a 3-way merge, and the merged text is what gets checked.
BASES = {
    'models/player/base/anims_shared.txt': ('models/player/base/anims_shared.txt', '6cf61e58'),
    'coop_mod/player_Torso.st': ('coop_mod/player_torso.st', '12e9faf6'),
}


def declared(rel, nm):
    for tail, rx, why in DECLARED:
        if rel.lower().endswith(tail) and re.fullmatch(rx, nm):
            return why
    return None


def merged(root, rel, res, emit=None):
    """the staged file 3-way merged with the mod tree's current file (base = the commit it was snapshot from)"""
    import subprocess, tempfile
    st = staged(root, rel)
    if rel not in BASES:
        return st
    modp, rev = BASES[rel]
    cur = os.path.join(MOD, rel.replace('/', os.sep))
    base = subprocess.run(['git', '-C', MOD, 'show', '%s:%s' % (rev, modp)], capture_output=True).stdout
    theirs = open(cur, 'rb').read()
    if base == theirs:
        return st
    d = tempfile.mkdtemp()
    fs = []
    for nm, b in (('ours', st), ('base', base), ('theirs', theirs)):
        f = os.path.join(d, nm); open(f, 'wb').write(b); fs.append(f)
    r = subprocess.run(['git', 'merge-file', '-p'] + fs, capture_output=True)
    if r.returncode != 0:
        res['fail'].append('%s: the mod file changed since %s and the 3-way merge has %d conflict(s)' % (rel, rev, r.returncode))
        return st
    res['info'].append('%s: snapshot of mod %s, the mod file has changed since - 3-way merge clean (%+d bytes); the MERGED text is checked and is what ships'
                       % (rel, rev, len(r.stdout) - len(st)))
    if emit:
        f = os.path.join(emit, rel.replace('/', os.sep)); os.makedirs(os.path.dirname(f), exist_ok=True); open(f, 'wb').write(r.stdout)
    return r.stdout


CLIENT_OK = re.compile('''
assert a in s
s = s.replace(a, b, 1)

# declared rows: route FAIL lines of a declared row to `decl`
a = '''def check_tik(root, rel, res, verbose):'''
b = '''class _Res(dict):
    """res['fail'].append(line) lands in res['decl'] when the line names a declared (file, row)"""


class _Fail(list):
    def __init__(self, res):
        self.res = res

    def append(self, line):
        m = re.match(r'(\\S+): (?:NEW )?row `([^`]+)`', line)
        why = declared(m.group(1), m.group(2)) if m else None
        if why:
            self.res['decl'].append((line, why))
        else:
            list.append(self, line)


def check_tik(root, rel, res, verbose):'''
assert a in s
s = s.replace(a, b, 1)
a = "    res = dict(fail=[], info=[], same=[], client={}, tiks=0)"
b = "    res = dict(info=[], same=[], client={}, tiks=0, decl=[])\n    res['fail'] = _Fail(res)\n    emit = sys.argv[sys.argv.index('--emit-merged') + 1] if '--emit-merged' in sys.argv else None"
assert a in s
s = s.replace(a, b, 1)
a = "def check_table(root, rel, res, client):\n    st = staged(root, rel).decode('latin-1')"
b = "def check_table(root, rel, res, client, emit=None):\n    st = merged(root, rel, res, emit).decode('latin-1')"
assert a in s
s = s.replace(a, b, 1)
a = "check_table(root, 'models/player/base/' + fn, res, fn.lower().startswith('fps_'))"
b = "check_table(root, 'models/player/base/' + fn, res, fn.lower().startswith('fps_'), emit)"
assert a in s
s = s.replace(a, b, 1)
a = "        a = strip(open(stf, 'rb').read().decode('latin-1')).split('\\n')"
b = "        a = strip(merged(root, 'coop_mod/player_Torso.st', res, emit).decode('latin-1')).split('\\n')"
assert a in s, 'torso'
s = s.replace(a, b, 1)
a = "    for l in res['fail']:\n        print('FAIL  ' + l)"
b = ("    seen = set()\n    for l, why in res['decl']:\n        print('decl  ' + l)\n        if why not in seen:\n            seen.add(why); print('      = ' + why)\n"
     "    for l in res['fail']:\n        print('FAIL  ' + l)")
assert a in s
s = s.replace(a, b, 1)
a = "    print('%d weapon tiks checked, %d FAIL' % (res['tiks'], len(res['fail'])))"
b = "    print('%d weapon tiks checked, %d declared server-side changes, %d FAIL' % (res['tiks'], len(res['decl']), len(res['fail'])))"
assert a in s
s = s.replace(a, b, 1)
s = s.replace("        json.dump(res, open(", "        json.dump(dict(res, fail=list(res['fail'])), open(")
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
