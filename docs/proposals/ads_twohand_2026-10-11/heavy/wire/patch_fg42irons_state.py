r"""FG 42 Irons: the torso state row of its reload - a PATCH for coop_mod/player_Torso.st (the file is shared by every
lane: apply this to the final tree, never copy a lane's staged file).

The reload's torso row is picked by the exact weapon NAME:
    coop_reload_fg42    : IS_WEAPON_ACTIVE "mainhand" "FG 42"
"FG 42 Irons" (a new base name, so the cgame's scope table does not match it) falls through to the class default - the
G 43 Irons did the same and its rifle left the hand (bug-3739). This adds the same row for the new name right after it.

    python patch_fg42irons_state.py <tree>             (<tree>/coop_mod/player_Torso.st; idempotent)
    python patch_fg42irons_state.py --pk3 <in> <out>   the same on the state file inside a test overlay pk3
"""
import io, os, re, sys, zipfile
REL = 'coop_mod/player_Torso.st'


def patch(s):
    if '"FG 42 Irons"' in s:
        return s, False
    nl = '\r\n' if '\r\n' in s else '\n'
    m = list(re.finditer(r'(?m)^([ \t]*)coop_reload_fg42([ \t]*):([ \t]*)IS_WEAPON_ACTIVE "mainhand" "FG 42"[^\r\n]*\r?\n', s))
    assert len(m) == 1, len(m)
    m = m[0]
    row = '%scoop_reload_fg42%s:%sIS_WEAPON_ACTIVE "mainhand" "FG 42 Irons"\t// HZM coop [heavy lane 2026-10-13, patch_fg42irons_state.py] the iron-sight FG 42: the same reload' % (m.group(1), m.group(2), m.group(3)) + nl
    return s[:m.end()] + row + s[m.end():], True


if sys.argv[1] == '--pk3':
    src, dst = sys.argv[2], sys.argv[3]
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zo:
        done = False
        for i in zi.infolist():
            b = zi.read(i.filename)
            if i.filename.lower() == REL.lower():
                t, ch = patch(b.decode('latin-1')); b = t.encode('latin-1'); done = True
                print('state file in the overlay:', 'patched' if ch else 'already patched')
            zo.writestr(i.filename, b)
        assert done, 'no %s in %s' % (REL, src)
else:
    p = os.path.join(sys.argv[1], 'coop_mod', 'player_Torso.st')
    s = io.open(p, encoding='latin-1', newline='').read()
    t, ch = patch(s)
    if ch:
        io.open(p, 'w', encoding='latin-1', newline='').write(t)
    print('patched' if ch else 'already patched', p)
