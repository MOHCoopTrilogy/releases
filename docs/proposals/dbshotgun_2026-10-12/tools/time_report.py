"""Server timing table from a run's time.json (tools/run_world.py part `time`): per segment the torso states with the
server time they were entered (relative to the segment's first event), each shell counted (the pool dropping by 1),
each shot (coop_fireDebug's SHOOT line, the server frame it fell in).

    python tools/time_report.py <run> [<baseline run>]     second run: compares the segments both have, state by state
"""
import os, sys, json
import dbslib as L


def load(run):
    return json.load(open(os.path.join(L.RUNS, run, 'time.json')))


def events(seg):
    """-> [(t, what)] : state changes, shells counted, shots"""
    ev, last_st, last_am = [], None, None
    for e in seg:
        if e[0] == 'st':
            _, t, st, am = e
            if st != last_st:
                ev.append((t, 'state ' + st)); last_st = st
            if last_am is not None and am != last_am:
                ev.append((t, 'pool %+d' % (am - last_am)))
            last_am = am
        elif e[0] == 'shoot' and e[1] is not None:
            ev.append((e[1], 'SHOT'))
        elif e[0] == 'cmd':
            ev.append((None, 'key ' + e[1]))
    return ev


def rel(ev):
    """times relative to the first SHOT (or the first timed event)"""
    t0 = next((t for t, w in ev if w == 'SHOT'), None)
    if t0 is None:
        t0 = next((t for t, w in ev if t is not None), 0.0)
    return [((round(t - t0, 3) if t is not None else None), w) for t, w in ev]


def main():
    a = load(sys.argv[1])
    b = load(sys.argv[2]) if len(sys.argv) > 2 else None
    out = []
    for name in a:
        ea = rel(events(a[name]))
        out.append(name)
        out.append('   ' + '  '.join('%s%s' % (('%.3f ' % t) if t is not None else '', w) for t, w in ea if not w.startswith('state STAND') or True))
        if b is not None and name in b:
            eb = rel(events(b[name]))
            ka = [(w, t) for t, w in ea if t is not None]
            kb = [(w, t) for t, w in eb if t is not None]
            same = [x[0] for x in ka] == [x[0] for x in kb]
            worst = max([abs(x[1] - y[1]) for x, y in zip(ka, kb)] or [0.0]) if same else None
            out.append('   vs %s: %s' % (sys.argv[2], ('same sequence of %d events, largest time difference %.3f s' % (len(ka), worst)) if same else
                                         'DIFFERENT SEQUENCE: ' + '  '.join('%.3f %s' % (t, w) for w, t in kb)))
    txt = '\n'.join(out)
    print(txt)
    open(os.path.join(L.BUILD, 'time_%s%s.txt' % (sys.argv[1], ('_vs_' + sys.argv[2]) if b else '')), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
