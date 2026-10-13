"""numbers of the first-person rig the hold is designed on (prints only):  python tools/dbs_probe.py [clip:frame ...]
VIEW frame = the camera: eye at the origin, forward +x, left +y, up +z, game units (the rig's own axes; vmcam)."""
import sys
import numpy as np
import dbs_rig as D
import dbs_hands as H

R = D.R
S = R.S
BONES = ('Bip01 R Clavicle', 'Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand', 'Bip01 L Clavicle', 'Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand')


def show(nm, f=0):
    a = D.load(nm)
    pd = R.pose_dict(a, f); W = R.evaluate(pd)
    E = W['eyes bone'][3, 0:3]
    G = W['tag_weapon_right']
    print('--- retail %s f%d: gun x axis in view %s, gun origin in view %s' % (nm, f, np.round(G[0, 0:3], 3), np.round((G[3, 0:3] - E) * S, 2)))
    for b in BONES:
        print('   %-18s view %s' % (b, np.round((W[b][3, 0:3] - E) * S, 2)))
    for s in 'RL':
        la = np.linalg.norm(W['Bip01 %s Forearm' % s][3, 0:3] - W['Bip01 %s UpperArm' % s][3, 0:3]) * S
        lb = np.linalg.norm(W['Bip01 %s Hand' % s][3, 0:3] - W['Bip01 %s Forearm' % s][3, 0:3]) * S
        print('   arm %s: upper %.2f fore %.2f reach %.2f' % (s, la, lb, la + lb))
    return W, E


def main():
    rig = H.Rig()
    for spec in (sys.argv[1:] or ['idle:0', 'charge:0']):
        nm, f = spec.split(':')
        W, E = show(nm, int(f))
    W, E = show('idle', 0)
    for nm, G in (('HOLD', rig.Gidle), ('AIM', rig.Gaim)):
        print('=== %s: gun origin in view %s  x axis %s' % (nm, np.round((G[3, 0:3] - E) * S, 2), np.round(G[0, 0:3], 3)))
        for hn, Hm in (('R wrist', rig.HRrel @ G), ('L wrist', rig.HLfor @ G)):
            p = (Hm[3, 0:3] - E) * S
            sh = (W['Bip01 %s UpperArm' % hn[0]][3, 0:3] - E) * S
            print('   %s target in view %s, from the idle shoulder %.2f u' % (hn, np.round(p, 2), np.linalg.norm(p - sh)))


if __name__ == '__main__':
    main()
