"""How far the FRONT SIGHT is from the target through an aimed bolt cycle, and whose doing it is: the engine's probe
(ADSFRAME F, 12.85 px per deg) against the clip's own offline track (rpart.py --track), per clip frame.
residual = engine - clip = what is NOT the clip (the shot's recoil still recovering, the view lag, the rig solve).

    cd rifles/assets
    python ../tools/ftrack.py <session> <tag substring> <sight gun> <aim.skc> "<clip.skc>|rechamber" [--cycle 1] [--step 3]
"""
import sys, os, re, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim2/runs').rstrip('/') + '/'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sess'); ap.add_argument('sub'); ap.add_argument('gun'); ap.add_argument('aim'); ap.add_argument('part')
    ap.add_argument('--cycle', type=int, default=1); ap.add_argument('--step', type=int, default=3)
    a = ap.parse_args()
    import rpart
    trk = rpart.measure(a.gun, a.aim, a.part, 160, quiet=True)
    ft = rpart.R.load(a.part.split('|')[0]).frameTime * 1000.0
    on = False; rows = []
    for ln in open(RUNS + a.sess + '/qconsole.log', encoding='latin-1', errors='replace'):
        if 'echo' in ln:
            continue
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m:
            on = m.group(1) == 'begin' and a.sub in m.group(2)
            continue
        if on and 'ADSFRAME' in ln:
            f = re.search(r' t=(\d+).* anim=(\d+).* F=\(([-\d.]+) ([-\d.]+)\)', ln)
            rows.append((int(f.group(1)), f.group(2), float(f.group(4))))
    f0 = rows[0][2]; idle = rows[0][1]
    # the n-th run of a NEW anim id that is not the idle / fire row = the n-th cycle clip
    starts = [i for i in range(1, len(rows)) if rows[i][1] != rows[i - 1][1] and rows[i][1] not in (idle,)]
    cyc = [i for i in starts if sum(1 for r in rows[i:i + 20] if r[1] == rows[i][1]) >= 15]
    i0 = cyc[a.cycle - 1]; t0 = rows[i0][0]; aid = rows[i0][1]
    pk = max((-(r[2] - f0) / 12.85 for r in rows[max(0, i0 - 40):i0]), default=0.0)
    print('shot recoil peak before the clip: front sight %.2f deg up; at the clip start %.2f deg' % (pk, -(rows[i0][2] - f0) / 12.85))
    print(' clip f | engine | clip alone | residual   (deg, + = front sight ABOVE the target)')
    worst = wr = 0.0
    for k, (t, an, fy) in enumerate(rows[i0:]):
        if an != aid:
            break
        cf = (t - t0) / ft
        c = trk[min(len(trk) - 1, int(round(cf)))]['f_up']
        e = -(fy - f0) / 12.85
        worst = max(worst, abs(e)); wr = max(wr, abs(e - c)) if cf >= 12 else wr
        if k % a.step == 0:
            print('  %5.1f | %6.2f | %6.2f | %6.2f' % (cf, e, c, e - c))
    print('front sight off the target through the clip: max %.2f deg; not the clip (residual) from clip frame 12 on: max %.2f deg' % (worst, wr))


if __name__ == '__main__':
    main()
