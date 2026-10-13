"""finger / lever numbers for the reload design (prints only):  python tools/dbs_probe2.py"""
import json, os, math
import numpy as np
import dbslib as L
import dbs_rig as D
import dbs_hands as H
import dbs_anim as GA

R = D.R
S = R.S


def main():
    rig = H.Rig()
    G = rig.Gidle
    pd = rig.solve(rig.pd0, G, rig.HLfor)
    W = R.evaluate(pd)
    print('R hand joints in the gun frame (hold):')
    for b in ('Bip01 R Hand', 'Bip01 R Finger0', 'Bip01 R Finger01', 'Bip01 R Finger02', 'Bip01 R Finger1', 'Bip01 R Finger11', 'Bip01 R Finger12',
              'Bip01 R Finger2', 'Bip01 R Finger22', 'Bip01 R Finger4', 'Bip01 R Finger42'):
        print('   %-18s %s' % (b, np.round(D.in_gun(G, W[b][3, 0:3]), 2)))
    P = json.load(open(os.path.join(L.BUILD, 'own', 'high_parts.json')))['parts']
    for part in ('lever', 'trig_f', 'trig_r'):
        v = np.array(P[part], float).reshape(-1, 8)[:, :3]
        g = (v * np.array([13.25, -13.25, -13.25])) * 0.52 + np.array([9.3, -1.05, -2.44])
        print('%s game box min %s max %s' % (part, np.round(g.min(0), 2), np.round(g.max(0), 2)))
        if part == 'lever':
            # the thumb piece = the rear end's top
            rear = g[g[:, 0] < g[:, 0].min() + 0.8]
            print('   lever rear end centre %s' % np.round(rear.mean(0), 2), 'pivot', np.round(GA.W0['dbs_lever'] * 0.52, 2))
    b = np.array(P['body'], float).reshape(-1, 8)[:, :3]
    g = (b * np.array([13.25, -13.25, -13.25])) * 0.52 + np.array([9.3, -1.05, -2.44])
    for x0 in (-8, -6, -4, -2, 0, 2):
        m = (g[:, 0] > x0 - 0.5) & (g[:, 0] < x0 + 0.5)
        if m.any():
            print('   body slice x %+d: y %.2f..%.2f  z %.2f..%.2f' % (x0, g[m, 1].min(), g[m, 1].max(), g[m, 2].min(), g[m, 2].max()))
    # fingers: idle curl vs the retail shell-feeding hand, per joint angle between the two
    fill = D.load('reload_single')
    pf = R.pose_dict(fill, 10)
    print('L finger joints: angle idle -> retail fill f10 (deg)')
    for k in sorted(rig.fing8):
        qa, qb = np.asarray(rig.fing8[k], float), np.asarray(pf[k], float)
        d = abs(float(qa @ qb)); ang = 2 * math.degrees(math.acos(min(1.0, d)))
        print('   %-24s %5.1f   idle %s  fill %s' % (k, ang, np.round(qa, 3), np.round(qb, 3)))
    Wf = R.evaluate(pf)
    Hl = Wf['Bip01 L Hand']
    print('retail fill f10: L hand local finger joints (hand frame, game u)')
    for b in ('Bip01 L Finger0', 'Bip01 L Finger02', 'Bip01 L Finger1', 'Bip01 L Finger12', 'Bip01 L Finger2', 'Bip01 L Finger22', 'Bip01 L Finger4', 'Bip01 L Finger42'):
        print('   %-18s fill %s   idle %s' % (b, np.round((Wf[b][3, 0:3] - Hl[3, 0:3]) @ Hl[0:3, 0:3].T * S, 2),
                                            np.round((rig.W0[b][3, 0:3] - rig.W0['Bip01 L Hand'][3, 0:3]) @ rig.W0['Bip01 L Hand'][0:3, 0:3].T * S, 2)))


if __name__ == '__main__':
    main()
