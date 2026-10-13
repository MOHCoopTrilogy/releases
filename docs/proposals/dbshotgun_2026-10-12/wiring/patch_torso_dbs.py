"""PATCH for the shared third-person state file coop_mod/player_Torso.st: the double barrel's own torso rows
(no pump stroke after a shot, none at the end of the reload). STAGED - not applied to the mod tree by this lane.

    python wiring/patch_torso_dbs.py <path to player_Torso.st> [--check]        (idempotent; --check writes nothing)
    as a library:  patch(text) -> text

Five rows, all conditioned on the EXACT weapon name "Shotgun (Double Barrel)" (Player::CondWeaponActive tries the exact
name first), placed after the two running rows (those already use rifle clips with no pump) and before the pump gun's
standing rows, so the first match wins and no other gun reaches them:
    ATTACK_SHOTGUN_PRIMARY      + coop_dbs_crouch_fire, coop_dbs_stand_fire
    ATTACK_SHOTGUN_PRIMARY_AIM  + coop_dbs_crouch_fire, coop_dbs_stand_fire
    RELOAD_SHOTGUN_END          + coop_dbs_reload_end
Plus the SECOND BARREL WHILE AIMING (run re2): the aimed fire state ATTACK_SHOTGUN_PRIMARY_AIM leaves only when its
torso clip is done (1.2 s - the pump gun's pump), so a second pull inside that time did nothing; the hip state
already lets a ready semi-auto fire again through CHECK_PRIMARY_ATTACK_SEMIAUTO. For this gun only: one exit row
to a new routing state COOP_DBS_REFIRE_AIM (stops the torso clip, goes straight back), so the aimed second shot
comes as soon as the weapon's own fire delay (0.30 s) allows.
The aliases are rows/tps_rows_coop_dbshotgun.txt (-> models/player/base/anims_shotgun.txt); the clips have the retail
clips' frame counts, so the timing of the shared states is unchanged.
"""
import re, sys

NAME = 'IS_WEAPON_ACTIVE "mainhand" "Shotgun (Double Barrel)"'
MARK = '[dbshotgun]'
FIRE = ('\t\t// HZM coop %s a double barrel has no pump: its own torso clips, the left hand stays on the forend\n'
        '\t\tcoop_dbs_crouch_fire\t\t: POSITION_TYPE "crouching" %s\n'
        '\t\tcoop_dbs_stand_fire\t\t: %s\n') % (MARK, NAME, NAME)
END = ('\t\t// HZM coop %s no pump stroke after the last shell\n'
       '\t\tcoop_dbs_reload_end\t\t: %s\n') % (MARK, NAME)
REFIRE_ROW = ('\t\t// HZM coop %s the second barrel while aiming: do not wait for the torso clip\n'
              '\t\tCOOP_DBS_REFIRE_AIM\t\t: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand" %s\n') % (MARK, NAME)
REFIRE_STATE = ('\n// HZM coop %s routing state: the second shot of the double barrel while aiming (see ATTACK_SHOTGUN_PRIMARY_AIM)\n'
                'state COOP_DBS_REFIRE_AIM\n{\n\tmovetype legs\n\n\taction\n\t{\n\t\tnone\t\t\t\t: default // stop the torso clip, so the next one fires\n\t}\n\n'
                '\tstates\n\t{\n\t\tSTAND\t\t\t\t: KILLED\n\t\tATTACK_SHOTGUN_PRIMARY_AIM\t: default\n\t}\n}\n') % MARK


def patch(text):
    nl = '\r\n' if '\r\n' in text else '\n'
    s = text.replace('\r\n', '\n')
    if MARK in s:
        return text
    rx_fire = re.compile(r'^[ \t]*shotgun_crouch_fire[ \t]+: POSITION_TYPE "crouching"[ \t]*\n', re.M)
    assert len(rx_fire.findall(s)) == 2, 'expected the pump gun\'s crouch-fire row in two states, found %d' % len(rx_fire.findall(s))
    s = rx_fire.sub(lambda m: FIRE + m.group(0), s)
    rx_end = re.compile(r'^[ \t]*shotgun_reload_end[ \t]+: default[ \t]*\n', re.M)
    # the released file plays shotgun_reload_end in ONE state (RELOAD_SHOTGUN_END); the mod tree of 2026-10-13 has a second
    # (RELOAD_SHOTGUN_BREAK_END, a reload broken off to fire): our row goes in front of each
    assert len(rx_end.findall(s)) in (1, 2), len(rx_end.findall(s))
    s = rx_end.sub(lambda m: END + m.group(0), s)
    rx_aim = re.compile(r'(^state ATTACK_SHOTGUN_PRIMARY_AIM[ \t]*\n\{.*?^\tstates[ \t]*\n\t\{[ \t]*\n[ \t]*STAND[ \t]+: KILLED[ \t]*\n)', re.M | re.S)
    assert len(rx_aim.findall(s)) == 1
    s = rx_aim.sub(lambda m: m.group(1) + REFIRE_ROW, s)
    s = s.rstrip('\n') + '\n' + REFIRE_STATE
    # the parse-killer checks of docs/TRAPS.md on what was added, and a running brace depth scan of the whole file
    assert '—' not in FIRE + END and '(-' not in FIRE + END
    d = 0
    for i, l in enumerate(s.split('\n')):
        c = l.split('//')[0]
        d += c.count('{') - c.count('}')
        assert d >= 0, ('brace depth below zero', i + 1)
    assert d == 0, 'braces do not balance'
    return s.replace('\n', nl)


def main():
    p = sys.argv[1]
    raw = open(p, 'rb').read().decode('latin-1')
    out = patch(raw)
    print('%s: %s' % (p, 'already patched' if out == raw else '5 torso rows in 3 states, 1 exit row + the routing state COOP_DBS_REFIRE_AIM'))
    if out != raw and '--check' not in sys.argv:
        open(p, 'wb').write(out.encode('latin-1'))


if __name__ == '__main__':
    main()
