"""Reload-authenticity contact sheets (reload_authenticity_2026-10-05). Read-only over the live install's pk3s.
Per gun: the first-person hip reload clip(s) the CLIENT picks (cg_viewmodelanim.c prefix -> fps_anims row), timed
against the torso reload the SERVER picks (player_Torso.st RELOAD_* action rows): its attachtohand windows decide
which hand tag holds the gun, its attachmodel/removeattachedmodel frames put the ammo prop in a hand. The gun is
posed by its own world 'reload' anim; its server surface +nodraw/-nodraw toggles are applied.
8 frames over the whole reload (split reloads: 3 start / 2 single / 3 end); two views per frame: EYE (calibrated
shooter's eye, hip framing) and ORB (3/4 view from above on the feed side L/R).

    python sheet.py <out dir> key[,key...]
"""
import os, sys, json, math, re, subprocess
import numpy as np
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
CWD0 = os.getcwd()
sys.path.insert(0, T)
sys.path.insert(0, CWD0)
os.chdir(T)
import vmcam as V
import prep_frames as PF
R = V.R
import vfs, gungeo
import torso as TO
from PIL import Image, ImageDraw

SPR = ['rifle/springfield_reload_start.skc', 'rifle/springfield_reload_fill.skc', 'rifle/springfield_reload_end.skc']
SPT = ['springfield_reload_start', 'springfield_reload_loop', 'springfield_reload_end']
# key: (tik, [fps clips], left-hand surface, [torso anims], orbit side)
G = {
 'garand': ('models/weapons/m1_garand.tik', ['rifle/vm_riflereload.skc'], 'garandhand', ['rifle_reload'], 'L'),
 'carbine': ('models/weapons/carbine.tik', ['rifle/vm_riflereload.skc'], 'garandhand', ['rifle_reload'], 'L'),
 'kar98': ('models/weapons/kar98.tik', ['rifle/kar98_reload.skc'], 'garandhand', ['kar98_reload'], 'R'),
 'arisaka': ('models/weapons/arisaka.tik', ['rifle/kar98_reload.skc'], 'garandhand', ['rifle_reload'], 'R'),
 'kar98_g98': ('models/weapons/kar98_g98.tik', ['rifle/kar98_reload.skc'], 'garandhand', ['kar98_reload'], 'R'),
 'kar98sniper': ('models/weapons/kar98sniper.tik', SPR, 'garandhand', SPT, 'R'),
 'kar98snsil': ('models/weapons/kar98snipersilenced.tik', SPR, 'garandhand', ['rifle_reload'], 'R'),
 'springfield': ('models/weapons/springfield.tik', SPR, 'garandhand', SPT, 'R'),
 'springfield_unscoped': ('models/weapons/springfield_unscoped.tik', SPR[:1], 'lefthand', ['rifle_reload'], 'R'),
 'springfield_smlescope': ('models/weapons/springfield_smlescope.tik', SPR, 'garandhand', SPT, 'R'),
 'enfield': ('models/weapons/enfield.tik', ['enfield/enfield_reload.skc'], 'lefthand', ['enfield_reload'], 'R'),
 'enfield_p14': ('models/weapons/enfield_p14.tik', ['enfield/enfield_reload.skc'], 'lefthand', ['enfield_reload'], 'R'),
 'enfieldsniper': ('models/weapons/enfieldsniper.tik', ['enfield/enfield_reload.skc'], 'lefthand', ['rifle_reload'], 'R'),
 'mosin': ('models/weapons/mosin_nagant_rifle.tik', ['mosin_nagant/mosin_nagant_reload.skc'], 'lefthand', ['mosin_reload'], 'R'),
 'nagant_sniper': ('models/weapons/nagant_sniper.tik', ['mosin_nagant/mosin_nagant_reload.skc'], 'lefthand', ['rifle_reload'], 'R'),
 'svt': ('models/weapons/svt_rifle.tik', ['svt40/svt_reload.skc'], 'lefthand', ['svt_reload'], 'L'),
 'g43': ('models/weapons/g43.tik', ['g43/g43_reload.skc'], 'lefthand', ['g43_reload'], 'L'),
 'g43sniper': ('models/weapons/g43sniper.tik', ['g43/g43_reload.skc'], 'lefthand', ['rifle_reload'], 'L'),
 'carcano': ('models/weapons/it_w_carcano.tik', ['carcano/a_w_carcano_reload_fps.skc'], 'lefthand', ['carcano_reload'], 'R'),
 'delisle': ('models/weapons/delisle.tik', ['delisle/a_w_delisle_reload_fps.skc'], 'lefthand', ['delisle_reload'], 'L'),
 'l42a1': ('models/weapons/uk_w_l42a1.tik', ['enfieldsniper/A_W_enfieldsniper_reload_fps.skc'], 'lefthand', ['enfieldl42a1_reload'], 'L'),
 'johnson': ('models/weapons/johnson_m1941.tik', ['coop_johnson/johnson_reload.skc'], 'lefthand', ['rifle_reload'], 'R'),
 'thompson': ('models/weapons/thompsonsmg.tik', ['smg/reload_tommy_stand.skc'], 'lefthand', ['smg_reload'], 'L'),
 'thompson50': ('models/weapons/thompson50.tik', ['smg/reload_tommy_stand.skc'], 'lefthand', ['smg_reload'], 'L'),
 'tommy1928d': ('models/weapons/thompsonsmg_tommy1928d.tik', ['smg/reload_tommy_stand.skc'], 'lefthand', ['smg_reload'], 'L'),
 'tommy28': ('models/weapons/thompsonsmg_tommy28.tik', ['smg/reload_tommy_stand.skc'], 'lefthand', ['smg_reload'], 'L'),
 'mp40': ('models/weapons/mp40.tik', ['MP40/reload_mp40_stand.skc'], 'lefthand', ['mp40_reload'], 'L'),
 'mp18': ('models/weapons/mp40_mp18.tik', ['MP40/reload_mp40_stand.skc'], 'lefthand', ['mp40_reload'], 'L'),
 'mp40silenced': ('models/weapons/mp40silenced.tik', ['MP40/reload_mp40_stand.skc'], 'lefthand', ['smg_reload'], 'L'),
 'pps43s': ('models/weapons/ppsh43silenced.tik', ['MP40/reload_mp40_stand.skc'], 'lefthand', ['smg_reload'], 'L'),
 'greasegun': ('models/weapons/greasegun.tik', ['MP40/reload_mp40_stand.skc'], 'lefthand', ['smg_reload'], 'R'),
 'sten': ('models/weapons/sten.tik', ['sten/sten_reload.skc'], 'lefthand', ['sten_reload'], 'L'),
 'ppsh': ('models/weapons/ppsh_smg.tik', ['ppsh/ppsh_reload.skc'], 'lefthand', ['ppsh_reload'], 'L'),
 'moschetto': ('models/weapons/it_w_moschetto.tik', ['moschetto/A_W_MOD38ASMG_reload_fps.skc'], 'lefthand', ['moschetto_reload'], 'L'),
 'beretta_m38': ('models/weapons/moschetto.tik', ['moschetto/A_W_MOD38ASMG_reload_fps.skc'], 'lefthand', ['smg_reload'], 'L'),
 'type100': ('models/weapons/type100smg.tik', ['type100/type100-reload.skc'], 'lefthand', ['smg_reload'], 'L'),
 'bar': ('models/weapons/bar.tik', ['mg/reload_bar.skc'], 'lefthand', ['mg_reload'], 'L'),
 'bar1918': ('models/weapons/bar_bar1918.tik', ['mg/reload_bar.skc'], 'lefthand', ['mg_reload'], 'L'),
 'mp44': ('models/weapons/mp44.tik', ['mp44/mp44_reload.skc'], 'lefthand', ['mp44_reload'], 'L'),
 'mp44scoped': ('models/weapons/mp44scoped.tik', ['mp44/mp44_reload.skc'], 'lefthand', ['rifle_reload'], 'L'),
 'fg42': ('models/weapons/fg42.tik', ['fg42/fg42_stand_reload.skc'], 'lefthand', ['fg42_reload'], 'L'),
 'vickers': ('models/weapons/uk_w_vickers.tik', ['Vickers/A_W_Vickers_reload_fps.skc'], 'lefthand', ['vickers_reload'], 'L'),
 'breda': ('models/weapons/it_w_breda.tik', ['breda/A_W_Breda_reload_fps.skc'], 'lefthand', ['mg_reload'], 'R'),
 'dp28': ('models/weapons/dp28.tik', ['coop_dp28/dp28_reload.skc'], 'lefthand', ['mg_reload'], 'L'),
 'm1919': ('models/weapons/30calportable.tik', ['mg/reload_bar.skc'], 'lefthand', ['mg_reload'], 'L'),
 'mg42': ('models/weapons/mg42portable.tik', ['mg/reload_bar.skc'], 'lefthand', ['mg_reload'], 'L'),
 'colt45': ('models/weapons/colt45.tik', ['pistol/reload_colt.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'colt1911w': ('models/weapons/colt45_colt1911w.tik', ['pistol/reload_colt.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'p38': ('models/weapons/p38.tik', ['pistol/reload_p38.skc'], 'lefthand', ['p38_reload'], 'L'),
 'c96': ('models/weapons/mauser_c96.tik', ['pistol/reload_p38.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'c96trench': ('models/weapons/mauser_c96_c96trench.tik', ['pistol/reload_p38.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'luger': ('models/weapons/lugerp08.tik', ['pistol/reload_colt.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'webley': ('models/weapons/webley_revolver.tik', ['webley/webley_reload_start.skc', 'webley/webley_reload_single.skc', 'webley/webley_reload_end.skc'], 'lefthand', ['webley_reload_start', 'webley_reload_loop', 'webley_reload_end'], 'L'),
 'nagantrev': ('models/weapons/nagant_revolver.tik', ['nagantrev/reload_start.skc', 'nagantrev/reload_loop.skc', 'nagantrev/reload_end.skc'], 'lefthand', ['nagantrev_reload_start', 'nagantrev_reload_loop', 'nagantrev_reload_end'], 'R'),
 'm10': ('models/weapons/m10_revolver.tik', ['coop_m10/m10_reload.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'beretta': ('models/weapons/it_w_beretta.tik', ['beretta/A_W_MOD34Pistol_reload_fps.skc'], 'lefthand', ['beretta_reload'], 'L'),
 'welrod': ('models/weapons/welrod.tik', ['pistol/reload_colt.skc'], 'lefthand', ['pistol_reload'], 'L'),
 'shotgun': ('models/weapons/shotgun.tik', ['shotgun/reload_start.skc', 'shotgun/reload_fill.skc', 'shotgun/reload_end.skc'], 'lefthand', ['shotgun_reload_start', 'shotgun_reload_loop', 'shotgun_reload_end'], 'L'),
}
NFR = 8
W, H = 320, 180
TORSO = TO.parse()


def resolve(p):
    p = 'viewmodel/' + p
    for cand in (p, p.replace('viewmodel/smg/', 'viewmodel/'), p.replace('viewmodel/mg/', 'viewmodel/'),
                 p.replace('viewmodel/pistol/', 'viewmodel/'), p.replace('viewmodel/shotgun/', 'viewmodel/')):
        if vfs.read(R.ANIM + cand):
            return R.ANIM + cand
    base = os.path.basename(p).lower()
    hits = [k for k in vfs.index() if k.startswith(R.ANIM + 'viewmodel/') and k.endswith('/' + base)]
    if hits:
        return hits[0]
    raise FileNotFoundError(p)


def look(campos, target):
    f = target - campos; f /= np.linalg.norm(f)
    l = np.cross([0, 0, 1.0], f); l /= np.linalg.norm(l)
    u = np.cross(f, l)
    return lambda P: np.stack([(P - campos) @ f, (P - campos) @ l, (P - campos) @ u], 1)


def tok_time(tok, nf, ft):
    if tok in ('entry', 'first', 'enter'):
        return 0.0
    if tok in ('last', 'end', 'exit'):
        return (nf - 1) * ft
    return int(tok) * ft


def torso_events(names):
    """per part: list of (time, kind, args) + torso length"""
    parts = []
    for n in names:
        a = TORSO.get(n.lower())
        if not a:
            parts.append(([], None)); continue
        try:
            c = R.load(a['skc']); nf, ft = c.numFrames, c.frameTime
        except Exception:
            nf, ft = 100, 0.03333
        ev = []
        for tok, cmd, args in a['ev']:
            try:
                tt = tok_time(tok, nf, ft)
            except ValueError:
                continue
            if cmd == 'weaponcommand' and len(args) >= 3 and args[1].lower() == 'attachtohand':
                ev.append((tt, 'hand', args[2].lower()))
            elif cmd == 'attachmodel':
                ev.append((tt, 'add', (args[0], args[1].strip('"') if len(args) > 1 else 'tag_weapon_left')))
            elif cmd == 'removeattachedmodel':
                ev.append((tt, 'rem', args[-1]))
        parts.append((sorted(ev, key=lambda e: e[0]), nf * ft))
    return parts


def surf_toggles(tik):
    """the gun's reload anim server block: [(frame or 'last', surface glob, hidden bool)]"""
    d = re.sub(r'//[^\n]*', '', vfs.read(tik).decode('latin1'))
    m = re.search(r'^\s*reload\s+\S+[^\n]*\n\s*\{(.*?)\n\s*\}\s*\n\s*client', d, re.M | re.S)
    if not m:
        m = re.search(r'^\s*reload\s+\S+[^\n]*\n\s*\{(.*?)\n\s*\}', d, re.M | re.S)
    out = []
    if m:
        for tok, s, sg in re.findall(r'(\w+)\s+surface\s+(\S+)\s+([+-])nodraw', m.group(1)):
            out.append((tok, s.lower(), sg == '+'))
    return out


def W_tag(Wf, tag):
    for k in Wf:
        if k.lower() == tag.lower():
            return Wf[k]
    return Wf['tag_weapon_left']


_pc = {}


def prop_surfs(Wf, tik, tag):
    if tik not in _pc:
        try:
            _pc[tik] = gungeo.load_gun(tik, anim='idle', frame=0)
        except Exception as e:
            print('prop fail', tik, e); _pc[tik] = None
    g = _pc[tik]
    if g is None:
        return []
    Tm = W_tag(Wf, tag)
    return [dict(s, name='prop:' + os.path.basename(tik) + ':' + s['name'], P=s['P'] @ Tm[0:3, 0:3] + Tm[3, 0:3] * R.S, gun=True) for s in g['surfs']]


def run(key, out, ctl):
    tik, clips, lsurf, tnames, side = G[key]
    V.LEFT_SURF[key] = lsurf
    cl = [R.load(resolve(c)) for c in clips]
    tparts = torso_events(tnames)
    tog = surf_toggles(tik)
    gt_ = gungeo.parse_tik(tik)
    gskc = R.load(gungeo._res(gt_, gt_['anims']['reload'])) if 'reload' in gt_['anims'] else None
    plan = []
    if len(cl) == 1:
        n = cl[0].numFrames
        plan = [(0, int(round(i * (n - 1) / (NFR - 1)))) for i in range(NFR)]
    else:
        for ci, k in ((0, 3), (1, 2), (2, 3)):
            if ci < len(cl):
                n = cl[ci].numFrames
                plan += [(ci, int(round(i * (n - 1) / (k - 1)))) for i in range(k)]
    starts = np.cumsum([0] + [c.numFrames * c.frameTime for c in cl])
    frames = []
    for ci, f in plan:
        c = cl[ci]; t = f * c.frameTime; gt = starts[ci] + t
        # hand tag + props from torso events of parts <= ci (props only within the part)
        hand = 'mainhand'; props = {}
        for pi in range(min(ci + 1, len(tparts))):
            for tt, kind, arg in tparts[pi][0]:
                if pi == ci and tt > t:
                    break
                if kind == 'hand':
                    hand = arg
                elif kind == 'add' and pi == ci:
                    props[arg[0].lower()] = arg[1]
                elif kind == 'rem' and pi == ci:
                    props.pop(arg.lower(), None)
        tag = 'tag_weapon_left' if hand == 'offhand' else 'tag_weapon_right'
        Wf = V.evaluate_ctl(R.pose_dict(c, f), ctl)
        arms = V.arm_surfs(Wf, key)
        gs, gfr = V.PR.gun_surfs(Wf, tik, 'reload', gt, lambda fr: True, tag)
        gnf = gskc.numFrames if gskc else 1
        hid = {}
        for tok, s, h in tog:
            ff = gnf - 1 if tok == 'last' else (0 if tok in ('entry', 'first') else int(tok) if tok.isdigit() else 0)
            if ff <= gfr:
                hid[s] = h
        def hidden(nm):
            nm = nm.lower()
            for s, h in hid.items():
                if h and (s == nm or s == 'all' or (s.endswith('*') and nm.startswith(s[:-1]))):
                    return True
            return False
        gs = [dict(s, gun=True) if not hidden(s['name']) else dict(s, gun=True, P=s['P'] * 0 + 1e5) for s in gs]
        ps = []
        for ptik, ptag in props.items():
            ps += prop_surfs(Wf, ptik, ptag)
        lab = '%s f%d %.2fs gun@%s%s' % (os.path.basename(clips[ci]).replace('.skc', '')[-18:], f, gt,
                                         'L' if tag.endswith('left') else 'R', (' +' + ','.join(os.path.basename(p)[:-4] for p in props)) if props else '')
        frames.append((Wf, arms, gs, ps, lab))
    # union surface list (props vary): fixed slots = arms + gun + every prop surface ever used (parked far away)
    proto = {}
    for Wf, arms, gs, ps, lab in frames:
        for s in arms + gs + ps:
            proto.setdefault(s['name'] + ('#g' if s.get('gun') else ''), s)
    keys = list(proto)
    Wf0 = frames[0][0]
    gT = Wf0['tag_weapon_right']
    pivot = gT[3, 0:3] * R.S + np.array([8.0, 0, 0]) @ gT[0:3, 0:3]
    cpos = pivot + np.array([-4.0, 0.0, 34.0])          # TOP view: above the gun, muzzle up the screen, gun-left = screen-left
    fT, uT = np.array([0, 0, -1.0]), np.array([1.0, 0, 0]); lT = np.cross(uT, fT)
    L = lambda P: np.stack([(P - cpos) @ fT, (P - cpos) @ lT, (P - cpos) @ uT], 1)
    rows = []
    for view in (0, 1):
        for Wf, arms, gs, ps, lab in frames:
            cur = {s['name'] + ('#g' if s.get('gun') else ''): s for s in arms + gs + ps}
            E = Wf['eyes bone'][3, 0:3] * R.S
            row = []
            for k in keys:
                P = cur[k]['P'] if k in cur else proto[k]['P'] * 0 + 1e5
                far = np.abs(P).max() > 5e4
                row.append(P * 0 + 1e5 if far else ((P - E) if view == 0 else L(P)))
            rows.append(row)
    fov = V.weapon_fov(1280, 720, gun_zoom=0.0)
    meta = {'W': W, 'H': H, 'fov': fov, 'znear': 1.0, 'frames': list(range(len(rows))),
            'surfs': [{'name': k, 'png': PF.tex_png(proto[k]['shader']), 'gun': bool(proto[k].get('gun'))} for k in keys]}
    arrs = {'meta': np.array(meta, dtype=object)}
    for i, k in enumerate(keys):
        arrs['tri%d' % i] = proto[k]['tri']; arrs['uv%d' % i] = proto[k]['UV']
        arrs['P%d' % i] = np.array([r[i] for r in rows], dtype=np.float32)
    d = os.path.join(out, key)
    os.makedirs(d, exist_ok=True)
    np.savez_compressed(os.path.join(d, 'pack.npz'), **arrs)
    subprocess.run([PF.BLENDER, '-b', '--factory-startup', '--python', os.path.join(T, 'bl_preview.py'), '--',
                    os.path.join(d, 'pack.npz'), d], capture_output=True)
    n = len(frames)
    S = Image.new('RGB', (W * 4, H * 4), (40, 40, 40))
    dr = ImageDraw.Draw(S)
    for i in range(n):
        for v in (0, 1):
            fn = os.path.join(d, 'v%03d.png' % (i + v * n))
            if not os.path.isfile(fn):
                continue
            x = (i % 4) * W; y = ((i // 4) * 2 + v) * H
            S.paste(Image.open(fn).convert('RGB'), (x, y))
            dr.rectangle([x, y, x + W - 1, y + 13], fill=(0, 0, 0))
            dr.text((x + 3, y + 1), ('EYE ' if v == 0 else 'TOP ') + key + ' ' + frames[i][4], fill=(255, 255, 0))
    fn = os.path.join(out, key + '_reload_sheet.jpg')
    S.save(fn, quality=78)
    print('wrote', fn, 'torso', tnames, 'tog', tog, flush=True)


if __name__ == '__main__':
    out = sys.argv[1] if os.path.isabs(sys.argv[1]) else os.path.join(CWD0, sys.argv[1])
    ctl = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
    keys = list(G) if sys.argv[2] == 'all' else sys.argv[2].split(',')
    for k in keys:
        try:
            run(k, out, ctl)
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAIL', k, repr(e), flush=True)
