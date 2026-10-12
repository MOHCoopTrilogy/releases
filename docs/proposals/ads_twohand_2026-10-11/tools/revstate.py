"""Revolver reload states with a BREAK-OFF (user 2026-10-12: "break off the reload" - a fire press during a revolver
reload stops it and shoots what is loaded; never eat the press, never count a round that was not seated, never lose one
that was). Run AFTER webtext.py and m10text.py: edits the staged coop_mod/player_Torso.st and anims_shared.txt.

Per revolver the one-round loop becomes two torso clips and two states:
  FETCH  (hand down to the pouch; nothing attached, nothing counted)  - a fire press here closes the gun at once
  SEAT   (round in the fingers -> seated -> counted)                   - a fire press here is kept: the round finishes
                                                                         seating, then the gun closes
and after the close the owed shot is fired (straight into the pistol attack state, aimed or hip).
An empty cylinder at the press: the first round is fetched and seated, then close and fire (the press is kept).
A weapon switch closes from FETCH at once and from SEAT after the round is in (no cartridge left in the hand).

    python revstate.py <stage root>
"""
import sys, os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
root = sys.argv[1]
ROUND = 'models/ammo/nagant_pistol_shell.tik'
A = 'models/human/animation/'
FAM = {
    # fam: start state, start anim, end anim, loop torso clip, split frame, seat frame (in the loop), prop tag, clips out
    'WEBLEY': dict(end='WEBLEY_reload_end', loop='viewmodel/webley/coop_webley_tp_single_slow.skc', split=10, seat=20,
                   tag='tag_weapon_left', out='viewmodel/webley/coop_webley_tp'),
    'M10': dict(end='coop_reload_m10_end', loop='viewmodel/webley/coop_webley_tp_single_slow.skc', split=10, seat=20,
                tag='tag_weapon_left', out='viewmodel/coop_m10/coop_m10_tp'),
    'NAGANTREV': dict(end='nagantrev_reload_end', loop='viewmodel/nagantrev/coop_nagant_tp_loop_slow.skc', split=11, seat=25,
                      tag='tag_weapon_right', out='viewmodel/nagantrev/coop_nagant_tp'),
}
INT = ('\t\tRELOAD_INTERUPTED_CORRECT_ATTACHMENTS\t: IS_USING_VEHICLE\n'
       '\t\tRELOAD_INTERUPTED_CORRECT_ATTACHMENTS\t: IS_USING_TURRET\n')


def state(name, entry, action, trans):
    t = 'state %s\n{\n\tmovetype legs\n' % name
    if entry:
        t += '\tentrycommands\n\t{\n' + ''.join('\t\t%s\n' % e for e in entry) + '\t}\n'
    if action:
        t += '\taction\n\t{\n\t\t%s\t: default\n\t}\n' % action
    t += '\tstates\n\t{\n' + trans + '\t}\n}\n'
    return t


p = os.path.join(root, 'coop_mod', 'player_Torso.st')
raw = open(p, 'rb').read().decode('latin-1')
crlf = '\r\n' in raw
s = raw.replace('\r\n', '\n')
shared = os.path.join(root, 'models', 'player', 'base', 'anims_shared.txt')
u_raw = open(shared, 'rb').read().decode('latin-1')
u_crlf = '\r\n' in u_raw
u = u_raw.replace('\r\n', '\n')
aliases = ''
for fam, d in FAM.items():
    X = 'RELOAD_' + fam
    low = fam.lower()
    fetch, seat = 'coop_reload_%s_fetch' % low, 'coop_reload_%s_seat' % low
    # ---- torso clips: the loop cut in two
    src = os.path.join(root, A + d['loop']).replace('/', os.sep)
    n = int(subprocess.run([sys.executable, os.path.join(HERE, 'retime.py'), src, os.path.join(root, A + d['out'] + '_fetch.skc'), 'slice', '0', str(d['split'] - 1)],
                           capture_output=True, text=True).stdout.split('of')[-1].split()[0])
    subprocess.run([sys.executable, os.path.join(HERE, 'retime.py'), src, os.path.join(root, A + d['out'] + '_seat.skc'), 'slice', str(d['split']), str(n - 1)], check=True, capture_output=True)
    k = d['seat'] - d['split']
    aliases += ('\t%s\t%s_fetch.skc\tcrossblend 0\n\t{\n\t\tserver\n\t\t{\n\t\t\tfirst weaponcommand mainhand anim reload_single\n\t\t}\n\t}\n'
                '\t%s\t%s_seat.skc\tcrossblend 0\n\t{\n\t\tserver\n\t\t{\n\t\t\t0 attachmodel %s %s\n\t\t\t%d weaponcommand mainhand clip_add 1\n'
                '\t\t\t%d removeattachedmodel %s 0 %s\n\t\t}\n\t}\n' % (fetch, d['out'], seat, d['out'], ROUND, d['tag'], k, k, d['tag'], ROUND))
    # ---- states
    for nm in (X + '_SINGLE', X + '_CHECK_CONTINUE'):
        m = re.search(r'(?m)^state %s\n\{.*?^\}\n' % nm, s, re.S)
        assert m, nm
        s = s[:m.start()] + '@@%s@@\n' % nm + s[m.end():]
    new = (
        '// HZM coop [revolver reload 2026-10-12] one round = FETCH (hand to the pouch) + SEAT (round in, counted);\n'
        '// a fire press breaks the reload off: at once from FETCH, after the round is in from SEAT; then close and fire.\n'
        + state(X + '_SINGLE', ['viewmodelanim reload_single 1'], fetch,
                '\t\tSTAND\t: KILLED\n\t\t%s_END\t: NEW_WEAPON\n' % X + INT +
                '\t\t%s_BREAK_END\t: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand"\n' % X +
                '\t\t%s_FETCH_ARMED\t: +ATTACK_PRIMARY\n' % X +
                '\t\t%s_END\t: PUTAWAYMAIN\n\t\t%s_SEAT\t: ANIMDONE_TORSO\n' % (X, X))
        + state(X + '_FETCH_ARMED', [], None, '\t\tSTAND\t: KILLED\n' + INT + '\t\t%s_SEAT_FORCED\t: ANIMDONE_TORSO\n' % X)
        + state(X + '_FETCH_FORCED', ['viewmodelanim reload_single 1'], fetch, '\t\tSTAND\t: KILLED\n' + INT + '\t\t%s_SEAT_FORCED\t: ANIMDONE_TORSO\n' % X)
        + state(X + '_SEAT', [], seat, '\t\tSTAND\t: KILLED\n' + INT + '\t\t%s_SEAT_ARMED\t: +ATTACK_PRIMARY\n\t\t%s_CHECK_CONTINUE\t: ANIMDONE_TORSO\n' % (X, X))
        + state(X + '_SEAT_ARMED', [], None, '\t\tSTAND\t: KILLED\n' + INT + '\t\t%s_BREAK_END\t: ANIMDONE_TORSO\n' % X)
        + state(X + '_SEAT_FORCED', [], seat, '\t\tSTAND\t: KILLED\n' + INT + '\t\t%s_BREAK_END\t: ANIMDONE_TORSO\n' % X)
        + state(X + '_BREAK_END', ['viewmodelanim reload_end'], d['end'], '\t\tSTAND\t: KILLED\n\t\t%s_BREAK_FIRE\t: ANIMDONE_TORSO\n' % X)
        + state(X + '_BREAK_FIRE', [], 'none',
                '\t\tSTAND\t: KILLED\n\t\tATTACK_PISTOL_PRIMARY_AIM\t: COOP_ADS HAS_AMMO_IN_CLIP "mainhand"\n'
                '\t\tATTACK_PISTOL_PRIMARY\t: HAS_AMMO_IN_CLIP "mainhand"\n\t\tSTAND\t: default\n'))
    chk = state(X + '_CHECK_CONTINUE', ['reload // this makes the weapon want to continue reloading if it can'], 'none',
                '\t\t%s_END\t: NEW_WEAPON\n\t\t%s_END\t: PUTAWAYMAIN\n\t\t%s_SINGLE\t: RELOAD\n\t\t%s_END\t: default\n' % (X, X, X, X))
    s = s.replace('@@%s_SINGLE@@\n' % X, new, 1).replace('@@%s_CHECK_CONTINUE@@\n' % X, chk, 1)
    # ---- the start state: a press during the opening is kept
    m = re.search(r'(?m)^state %s\n\{.*?^\}\n' % X, s, re.S)
    blk = m.group(0)
    t0 = re.search(r'(?m)^(\s*)%s_SINGLE(\s*): ANIMDONE_TORSO\s*\n' % X, blk)
    assert t0, X + ' start'
    blk2 = blk[:t0.start()] + '%s%s_START_ARMED%s: +ATTACK_PRIMARY\n' % (t0.group(1), X, t0.group(2)) + blk[t0.start():]
    armed = state(X + '_START_ARMED', [], None,
                  '\t\tSTAND\t: KILLED\n' + INT + '\t\t%s_BREAK_END\t: ANIMDONE_TORSO HAS_AMMO_IN_CLIP "mainhand"\n\t\t%s_FETCH_FORCED\t: ANIMDONE_TORSO\n' % (X, X))
    s = s[:m.start()] + blk2 + armed + s[m.end():]
d_ = 0
for i, l in enumerate(s.splitlines()):
    c = l.split('//')[0]
    d_ += c.count('{') - c.count('}')
    assert d_ >= 0, i
assert d_ == 0 and '@@' not in s
open(p, 'wb').write((s.replace('\n', '\r\n') if crlf else s).encode('latin-1'))
anchor = '\tcoop_reload_m10\tviewmodel/pistol/reload_colt.skc\tcrossblend 0.3\n'
assert u.count(anchor) == 1 and 'coop_reload_webley_fetch' not in u
u = u.replace(anchor, '\t// HZM coop [revolver reload 2026-10-12] the one-round loop in two halves (player_Torso.st RELOAD_*_SINGLE / _SEAT)\n' + aliases + anchor, 1)
d_ = 0
for l in u.splitlines():
    c = l.split('//')[0]
    d_ += c.count('{') - c.count('}')
    assert d_ >= 0
assert d_ == 0
open(shared, 'wb').write((u.replace('\n', '\r\n') if u_crlf else u).encode('latin-1'))
print('states + aliases written for', list(FAM), '| new states', s.count('_BREAK_END\n{') + s.count('_BREAK_END\r'), s.count('state RELOAD_'))
