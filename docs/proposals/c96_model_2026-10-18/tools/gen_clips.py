"""Gun clips for the new C96 skeleton (all 8 bones, all channels in every clip).

    python gen_clips.py            -> ship/models/weapons/coop_c96n/*.skc

Bones moved: coop_slide (bolt, -x = rearward, BOLT raw units), coop_tog (hammer, deg about the lateral axis through its
pin: +deg = top rearward = cocked), coop_trig (trigger, -deg = pulled).  Timelines of the reload clips are the ones of
ads_twohand_2026-10-11/tools/c96.py (the server's torso row coop_reload_c96 is 73 frames at 30 per second; the hands
clips were keyed to it): bolt_state() is copied from there, nothing else of that file is used.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c96lib as L
import skx as X
import build_mesh as BM

BOLT = float(os.environ.get('C96N_BOLT', '3.8'))      # raw units the bolt travels rearward (0.25 BU)
HAM_COCK = 64.1                                       # the source's own cocked angle
HAM_OVER = 78.0                                       # the bolt carries the hammer further while it passes over
TRIG_PULL = -9.4
N = 73
K = dict(out=(49, 52))
HIP = dict(draw=(12, 18), close=48)
OUT = os.path.join(L.STAGE, 'models', 'weapons', 'coop_c96n')
QID = [0.0, 0.0, 0.0, 1.0]


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def bolt_state(f, empty, hip=False, draw=None):
    if hip:
        c = HIP['close']
        close = 1.0 if f <= c else max(0.0, 1.0 - ((f - c) / 2.0) ** 2)
        if empty:
            return close
        d0, d1 = HIP['draw']
        return min(smooth((f - d0) / float(d1 - d0)), close)
    o0, o1 = K['out']
    close = 1.0 if f <= o1 - 2 else max(0.0, 1.0 - ((f - (o1 - 2)) / 2.0) ** 2)
    if empty:
        return close
    d0, d1 = (16, 20)
    return min(smooth((f - d0) / float(d1 - d0)), close)


M = json.load(open(os.path.join(L.BUILD, 'mesh.json')))
HP = np.array(M['ham_piv']); TP = np.array(M['trig_piv'])


def pivot_chan(piv, deg):
    """pos / rot channel (identity bind at the gun origin) that turns the bone `deg` about +y through raw point piv"""
    Rl = L.rot_rows((0, 1, 0), deg)
    c = np.asarray(piv, float)
    p = c - c @ Rl
    return [float(p[0]), float(p[1]), float(p[2]), 0.0], L.mat_quat(Rl)


# the P38 skeleton's own constant values (tags the rows and the cgame use)
OLD = {'Box01 pos': [4.8783, -1.0914, 0.4278, 0.0], 'Box01 rot': [0.0218, -0.0087, -0.0002, 0.9997],
       'p38clip pos': [0.0, 0.0, 0.0, 0.0], 'p38clip rot': [0.0, 0.0872, 0.0, 0.9962],
       'tag_eject rot': [-0.2988, -0.6409, -0.2988, 0.6409]}
CHANNELS = []
for n, _p in BM.BONES:
    CHANNELS += [n + ' pos', n + ' rot']


def frame(u, ham, trig):
    v = {}
    v['origin pos'] = [0.0, 0.0, 0.0, 0.0]; v['origin rot'] = QID
    v['tag_barrel pos'] = list(M['tag_barrel']) + [0.0]; v['tag_barrel rot'] = QID
    v['tag_eject pos'] = list(M['tag_eject']) + [0.0]; v['tag_eject rot'] = OLD['tag_eject rot']
    v['Box01 pos'] = OLD['Box01 pos']; v['Box01 rot'] = OLD['Box01 rot']
    v['p38clip pos'] = OLD['p38clip pos']; v['p38clip rot'] = OLD['p38clip rot']
    v['coop_slide pos'] = [-BOLT * u, 0.0, 0.0, 0.0]; v['coop_slide rot'] = QID
    v['coop_tog pos'], v['coop_tog rot'] = pivot_chan(HP, ham)
    v['coop_trig pos'], v['coop_trig rot'] = pivot_chan(TP, trig)
    return [v[c] for c in CHANNELS]


def write(name, frames, ft):
    bmin, bmax, rad = np.array(M['bmin']), np.array(M['bmax']), M['radius']
    data = X.build_skc(CHANNELS, frames, ft, bmin, bmax, rad)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, name), 'wb').write(data)
    return len(frames)


def ham_for(u):
    return HAM_COCK + (HAM_OVER - HAM_COCK) * min(1.0, u * 1.6)


def main():
    out = {}
    # idle: bolt closed, hammer cocked
    out['c96n_idle.skc'] = write('c96n_idle.skc', [frame(0.0, HAM_COCK, 0.0)], 0.25)
    # idle_empty: bolt held open
    out['c96n_idle_empty.skc'] = write('c96n_idle_empty.skc', [frame(1.0, HAM_OVER, 0.0)], 0.25)
    # fire: hammer falls, bolt recoils and returns and re-cocks (8 frames x 0.02 s)
    fire = [(0.0, HAM_COCK, TRIG_PULL * 0.6), (0.0, HAM_COCK * 0.45, TRIG_PULL), (0.0, 0.0, TRIG_PULL),
            (0.45, 8.0, TRIG_PULL * 0.8), (1.0, HAM_OVER, TRIG_PULL * 0.4), (0.7, HAM_COCK + 6, 0.0),
            (0.25, HAM_COCK, 0.0), (0.0, HAM_COCK, 0.0)]
    out['c96n_fire.skc'] = write('c96n_fire.skc', [frame(*r) for r in fire], 0.02)

    def reload_clip(name, empty, hip):
        fr = []
        for f in range(N):
            u = bolt_state(f, empty, hip)
            fr.append(frame(u, ham_for(u) if u > 0 else HAM_COCK, 0.0))
        out[name] = write(name, fr, 1 / 30.0)
    reload_clip('c96n_reload_ads_loaded.skc', False, False)
    reload_clip('c96n_reload_ads_empty.skc', True, False)
    reload_clip('c96n_reload_empty.skc', True, True)
    reload_clip('c96n_reload_hip.skc', False, True)
    print(out)


if __name__ == '__main__':
    main()
