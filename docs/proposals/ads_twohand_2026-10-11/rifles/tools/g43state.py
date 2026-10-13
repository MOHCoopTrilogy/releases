"""Iron-sight G43: the torso state file picks the reload's torso animation BY WEAPON NAME (coop_mod/player_torso.st,
state RELOAD_RIFLE... `g43_reload : IS_WEAPON_ACTIVE "mainhand" "G 43"`). "G 43 Irons" is a base name of its own (so
the scope table does not catch it), so it fell through to the generic `rifle_reload`: the Garand's torso clip, which
hands the gun to the LEFT hand tag - and the G43's first-person clip takes that hand down to the pouch. Run rb28: the
rifle swings up, leaves the right hand and drops out of the picture for a second (bug-3718).

Fix = ONE line under the G 43's. Staged copy for the harness overlay (apply-on-top: re-run when the mod's file changes)
and a patch for the wiring step:
    python g43state.py   -> ../assets/coop_mod/player_torso.st, ../wire/player_torso_g43irons.patch
"""
import os, re, difflib
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\player_torso.st"
OUT = os.path.join(HERE, '..', 'assets', 'coop_mod', 'player_torso.st')
PATCH = os.path.join(HERE, '..', 'wire', 'player_torso_g43irons.patch')
RELEASED = 'G:/GOG/Medal of Honor - Allied Assault War Chest/maintt/zzzzzz_co-op_hzm_mod_code.pk3'     # read only: what the test install mounts


def build(raw, src_name):
    nl = '\r\n' if '\r\n' in raw else '\n'
    m = re.findall(r'(?m)^([ \t]*)g43_reload([ \t]*): IS_WEAPON_ACTIVE "mainhand" "G 43"[ \t]*\r?$', raw)
    assert len(m) == 1, len(m)
    assert '"G 43 Irons"' not in raw, 'already in the mod tree'
    rx = re.compile(r'(?m)^([ \t]*)g43_reload([ \t]*): IS_WEAPON_ACTIVE "mainhand" "G 43"[ \t]*(\r?\n)')
    mm = rx.search(raw)
    line = '%s//[g43 irons 2026-10-12] the iron-sight G43: the G43\'s own torso reload (no hand-over of the gun)%s' % (mm.group(1), nl)
    line += '%sg43_reload%s: IS_WEAPON_ACTIVE "mainhand" "G 43 Irons"%s' % (mm.group(1), mm.group(2), nl)
    new = raw[:mm.end()] + line + raw[mm.end():]
    d = 0
    for ln in new.splitlines():
        c = ln.split('//')[0]
        d += c.count('{') - c.count('}')
    assert d == 0, d
    return new


def main():
    # the PATCH is against the mod tree; the harness copy is built from the RELEASED file the test install mounts (run
    # rb29: the mod tree's file already uses a condition, COOP_TURRET_LOW, that the test install's game dll does not
    # know - 'Server crashed: Unknown condition', the map never came up; bug-3719)
    import zipfile
    raw = open(SRC, 'rb').read().decode('latin-1')
    new = build(raw, SRC)
    diff = difflib.unified_diff(raw.splitlines(True), new.splitlines(True), 'a/hzm-mohaa-coop-mod/coop_mod/player_torso.st',
                                'b/hzm-mohaa-coop-mod/coop_mod/player_torso.st', n=2)
    os.makedirs(os.path.dirname(PATCH), exist_ok=True)
    open(PATCH, 'w', newline='').write(''.join(diff))
    z = zipfile.ZipFile(RELEASED)
    nm = [n for n in z.namelist() if n.lower() == 'coop_mod/player_torso.st']
    assert len(nm) == 1, nm
    rel = build(z.read(nm[0]).decode('latin-1'), RELEASED)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(rel.encode('latin-1'))
    print('wrote', os.path.normpath(OUT), '(from the released pak, as', nm[0] + ')', 'and', os.path.normpath(PATCH))


if __name__ == '__main__':
    main()
