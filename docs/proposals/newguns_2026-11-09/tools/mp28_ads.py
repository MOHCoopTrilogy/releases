"""MP 28 aim pose of its own (coordinator QA 2026-11-09: on the Sten's aim row coop_sten_ads_mag.skc the left sleeve covers the left
third of the screen). The Sten's aim clip with the LEFT hand moved along the gun (gun frame offset, eased per frame = one pose for
the whole clip) and the left elbow dropped (IK pole bias down), so the forearm comes up from below instead of across from the left.
Right arm, eye, body, both tags untouched -> the sight picture is the Sten row's (rig solve on the MP 28's sight row).

Coverage: engine-calibrated rig + the held ADS correction for the MP 28 sight row, 21:9, ADS weapon fov (wfov 95.8 measured in
game at 3440x1440); share of the screen covered by the left hand + the sleeve pixels in the left 45 %.
    python mp28_ads.py sweep '[[dx,dy,dz,pole_down], ...]'
    python mp28_ads.py bake dx dy dz pole_down <src clip> <out.skc>
    python mp28_ads.py sheet <clip> <out.jpg>
"""
import sys, os, math, json
T_ = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T_); _c = os.getcwd(); os.chdir(T_)
import vmcam as V  # noqa: E402
import key_bolt as KB  # noqa: E402
os.chdir(_c)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
R = V.R; S = R.S
CTL = json.load(open(os.path.join(T_, '..', 'assets', 'ctl_stand.json')))
TIK = 'models/weapons/coop_bergmann.tik'
V.SIGHTS['mp28'] = dict(V.SIGHTS['sten_mark_ii'], tik=TIK, name='MP28', F=[23.2418, -0.7099, -4.5307], R=[3.2229, -0.7099, -4.7487], relief=0.0)
SRC = 'models/human/animation/viewmodel/sten/coop_sten_ads_mag.skc'
W, H, FOV = 430, 180, 95.8


def corr_of(clip):
    return V.rig_target(V.evaluate_ctl(R.pose_dict(clip, clip.numFrames - 1), CTL), V.SIGHTS['mp28'])


def render(clip, f, w=W, h=H, tex=False):
    corr = corr_of(clip)
    surfs, E, Wb = V.scene2(R.pose_dict(clip, f), 'mp28', TIK, 'idle', 0.0, CTL, corr, None, None)
    surfs = [s for s in surfs if np.abs(s['P']).max() < 1e3]
    rgb, ids, dep = V.shade_render(surfs, E, FOV, w, h, tex=tex)
    return rgb, ids, surfs


def coverage(clip, f):
    rgb, ids, surfs = render(clip, f)
    sid = ids // 1000000; m = ids >= 0
    hand = np.zeros(ids.shape, bool); slv = np.zeros(ids.shape, bool)
    for i, s in enumerate(surfs):
        if s['name'] == 'lefthand':
            hand |= m & (sid == i)
        if s['name'] == 'viewsleeves':
            slv |= m & (sid == i)
    slv[:, int(W * 0.45):] = False
    return hand.mean(), slv.mean()


def bake(dx, dy, dz, pole, src=SRC):
    hip = R.load(src); out = R.load(src); cm = R.chanmap(out)
    for f in range(hip.numFrames):
        pd = R.pose_dict(hip, f)
        Wc = R.evaluate(pd)
        G = Wc['tag_weapon_right']
        HL = Wc['Bip01 L Hand'].copy()
        HR = Wc['Bip01 R Hand'].copy()
        HL[3, 0:3] = HL[3, 0:3] + np.array([dx, dy, dz]) @ G[0:3, 0:3] / S
        KB.solve_arms(pd, Wc, HR, HL, G, pole_bias={'L': [0, 0, -pole]} if pole else None)
        KB.write_frame(out, hip, cm, f, pd)
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(out.numFrames)]
    return out


def main():
    cmd = sys.argv[1]
    if cmd == 'sweep':
        for p in json.loads(sys.argv[2]):
            out = bake(*p)
            tmp = r'H:\hzm_work\newguns\brenhands\sw\mp28.skc'
            open(tmp, 'wb').write(R.skc_io.write(out))
            c = R.load(tmp)
            a, b = coverage(c, c.numFrames - 1)
            print(p, 'left hand %.1f%% left sleeve %.1f%%' % (100 * a, 100 * b), flush=True)
    elif cmd == 'bake':
        dx, dy, dz, pole = [float(x) for x in sys.argv[2:6]]
        out = bake(dx, dy, dz, pole, sys.argv[6])
        open(sys.argv[7], 'wb').write(R.skc_io.write(out))
        c = R.load(sys.argv[7])
        print('wrote', sys.argv[7], 'cover %.1f%% / %.1f%%' % tuple(100 * x for x in coverage(c, c.numFrames - 1)))
    elif cmd == 'sheet':
        c = R.load(sys.argv[2])
        rgb, ids, _ = render(c, c.numFrames - 1, 1032, 432, tex=True)
        im = Image.fromarray(rgb)
        a, b = coverage(c, c.numFrames - 1)
        ImageDraw.Draw(im).text((6, 6), 'hand %.1f%% lsleeve %.1f%%' % (100 * a, 100 * b), fill=(255, 255, 0))
        im.save(sys.argv[3], quality=85)


if __name__ == '__main__':
    main()
