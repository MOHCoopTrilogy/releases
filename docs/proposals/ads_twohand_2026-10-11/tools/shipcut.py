"""SHIP CUT of the pistol lane (2026-10-13): the staged tree without the guns that are held out.

    python shipcut.py <ship dir> <test overlay.pk3>

Held out, and how each is kept exactly as released:
  Mauser C96 + Trench C96   (stripper clip unfinished)  their staged tiks, mesh, gun clips, hands clips, textures, shader and
                            the rows_p12_c96.txt rows are left out; the two share the P38 prefix, whose aim row now is the
                            two-handed pose, so ONE pin row keeps their released aim: coopr_mauser_c96_charge -> p38pose00.skc
                            (the cgame's per-weapon row, ads-next 2627cb94). Their hip idle is the P38's new idle2h clip -
                            only the left hand's finger channels differ, and that hand is out of view at the hip.
  S&W M10 + its 7 finishes  (another player always sees six chamber heads) tiks, mesh, textures, shader, rows_m10.txt and
                            the m10 row repoints are left out, and the ONE line of player_Torso.st that sends the M10 to
                            the round-by-round states is removed - it reloads on the released line (coop_reload_m10). The
                            M10 torso / hands clips that the shared tables still name stay in (unreachable, harmless).
Everything else ships as staged and as tested. The cut is rebuilt from ./stage every time (idempotent).
"""
import sys, os, re, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p12
vfs = p12.vfs
OUT_RX = [r'^models/weapons/mauser_c96[^/]*\.tik$', r'^models/weapons/coop_c96/', r'^textures/coop_c96/', r'^scripts/coop_c96_clip\.shader$',
          r'^models/human/animation/viewmodel/pistol/coop_c96_', r'^models/weapons/m10_revolver[^/]*\.tik$', r'^models/weapons/coop_m10/',
          r'^textures/coop_m10/', r'^scripts/coop_m10_face\.shader$',
          # the SMG lane's Sten aim pose sits in this tree from run tg1: not a pistol, not in this cut
          r'^models/player/base/fps_anims_smg\.txt$', r'^models/human/animation/viewmodel/sten/']
M10_ROUTE = re.compile(r'(?m)^[ \t]*RELOAD_M10[ \t]*:[ \t]*IS_WEAPON_ACTIVE "mainhand" "S&W M10 \.38"[ \t]*\r?\n')
EXTRA = ['rows_webley_empty.txt', 'rows_nagant.txt', 'rows_pistol_empty.txt', 'rows_cycle.txt', 'rows_p12_luger.txt', 'rows_p12_ppk.txt',
         'rows_p12_welrod.txt', 'rows_cut_pins.txt']
PINS = ('\t//===================== HZM coop SHIP CUT 2026-10-13: guns held out keep their released aim pose (their prefix row now is the two-handed pose) =====================\n'
        '\tcoopr_mauser_c96_charge\t\t\tviewmodel/p38pose00.skc\t\t\tcrossblend 0.3\n')


def main():
    ship, pk3 = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    stage = os.path.join(HERE, 'stage')
    cut = os.path.join(HERE, 'stage_cut')
    if os.path.isdir(cut):
        shutil.rmtree(cut)
    left, kept = [], 0
    tables = ''
    for dp, dn, fns in os.walk(stage):
        for fn in fns:
            src = os.path.join(dp, fn)
            arc = os.path.relpath(src, stage).replace(os.sep, '/')
            if any(re.search(rx, arc, re.I) for rx in OUT_RX):
                left.append(arc)
                continue
            dst = os.path.join(cut, arc.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            kept += 1
            if arc.lower().startswith('models/player/base/') and arc.lower().endswith('.txt'):
                tables += open(src, 'rb').read().decode('latin-1').lower()
    # M10 hands / torso clips: keep only what the shared tables still name, and never a file the released game has
    md = os.path.join(cut, 'models', 'human', 'animation', 'viewmodel', 'coop_m10')
    for fn in sorted(os.listdir(md)) if os.path.isdir(md) else []:
        arc = 'models/human/animation/viewmodel/coop_m10/' + fn
        named = ('viewmodel/coop_m10/' + fn).lower() in tables
        rel = p12.rd(arc) is not None
        if not named or rel:
            os.remove(os.path.join(md, fn)); left.append(arc + ('   (not named by a shipped table)' if not named else '   (the released file stays)'))
            kept -= 1
    # the state file: the M10 goes back to the released reload line
    tp = os.path.join(cut, 'coop_mod', 'player_Torso.st')
    s = open(tp, 'rb').read().decode('latin-1')
    s2, n = M10_ROUTE.subn('', s)
    assert n == 1, n
    open(tp, 'wb').write(s2.encode('latin-1'))
    open(os.path.join(HERE, 'rows_cut_pins.txt'), 'w', newline='\n').write(PINS)
    args = (open(os.path.join(HERE, 'ovargs_default.txt')).read().split() + open(os.path.join(HERE, 'ovargs_idle.txt')).read().split())
    args = [a for a in args if not (a.startswith('m10=') or a.startswith('row:m10_'))]
    env = dict(os.environ, MKOV_EXTRA=';'.join(EXTRA), MKOV_STAGE=cut, MKOV_EMIT=ship)
    env.pop('MKOV_BLOCK', None)
    if os.path.isdir(ship):
        shutil.rmtree(ship)
    r = subprocess.run([sys.executable, os.path.join(HERE, 'mkov.py'), pk3] + args, cwd=HERE, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-1500:]
    # texture lifts (gamma-lifted retail sheets) await the user's approval and are separable: beside the cut, not in it
    opt = os.path.join(os.path.dirname(ship), 'ship_awaiting_approval')
    if os.path.isdir(opt):
        shutil.rmtree(opt)
    if os.path.isdir(os.path.join(ship, 'textures')):
        os.makedirs(opt)
        shutil.move(os.path.join(ship, 'textures'), os.path.join(opt, 'textures'))
        left.append('textures/models/weapons/**   (texture lifts: in ../ship_awaiting_approval, not in the cut)')
    open(os.path.join(ship, 'LEFT_OUT.txt'), 'w', newline='\n').write('\n'.join(sorted(left)) + '\n')
    n = sum(len(f) for _, _, f in os.walk(ship))
    print('ship cut: %d staged files kept, %d left out (LEFT_OUT.txt), %d files in %s, overlay %s' % (kept, len(left), n, ship, pk3))


if __name__ == '__main__':
    main()
