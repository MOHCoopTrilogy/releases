"""Server reload timeline of a run_srvtime.py session, from the game log. All times are the SERVER's level.time (the
script probe's tick, 50 ms steps); a line without its own time takes the last tick's.

    python srvtime_report.py <session> [--raw]
Per gun and part: when the torso state machine enters / leaves its reload states, when the weapon tik's own `reload`
row starts / reaches its last frame / is left (WEAPON_RELOADING is held from the start of that row to its end), and in
which tick the reserve ammunition drops (= the magazine is filled). Seconds after the torso enters the reload.
Writes ../evidence/srvtime_<session>.tsv
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim2/runs')


def main():
    sess = sys.argv[1]
    raw = '--raw' in sys.argv
    p = os.path.join(RUNS, sess, 'qconsole.log')
    if not os.path.isfile(p):
        p = 'G:/mohaa-adsanim2/home/maintt/qconsole.log'
    seg = None
    out = []
    t = None
    for ln in open(p, encoding='latin-1'):
        m = re.search(r'\^~\^~\^ (RT|FIREDBG) (.*)', ln)
        if not m:
            continue
        kind, s = m.group(1), m.group(2).strip()
        if kind == 'RT':
            mm = re.match(r'begin (\S+) (\S+)', s)
            if mm:
                seg = {'gun': mm.group(1), 'part': mm.group(2), 'ev': [], 'reserve': None}
                continue
            if seg is None:
                continue
            mm = re.match(r'tick t=([\d.]+) reserve=(-?\d+)', s)
            if mm:
                t = float(mm.group(1)); r = int(mm.group(2))
                if seg['reserve'] is not None and r != seg['reserve']:
                    seg['ev'].append((t, 'reserve %d -> %d' % (seg['reserve'], r)))
                seg['reserve'] = r
                continue
            mm = re.match(r'weapon reload row (\w+) t=([\d.]+)', s)
            if mm:
                seg['ev'].append((float(mm.group(2)), 'weapon row ' + mm.group(1)))
                continue
            if s.startswith('cmd '):
                seg['ev'].append((t, s))
                continue
            if s.startswith('end '):
                out.append(seg); seg = None
        elif seg is not None:
            mm = re.match(r'TORSO (\S+) -> (\S+)', s)
            if mm and mm.group(2) != '(none)':
                seg['ev'].append((t, 'torso %s -> %s' % mm.groups()))
            elif s.startswith('SHOOT'):
                seg['ev'].append((t, 'shot'))
    rows = ['gun\tpart\ttorso reload in (level.time)\tweapon row starts\tmagazine filled\tweapon row last frame\tweapon row left (WEAPON_RELOADING ends)\ttorso leaves the reload\tfirst state after\tshots before']
    for sg in out:
        ev = sg['ev']
        if raw:
            print('==', sg['gun'], sg['part'])
            for e in ev:
                print('   %8s  %s' % ('%.2f' % e[0] if e[0] is not None else '-', e[1]))
        rin = [e for e in ev if e[1].startswith('torso') and 'RELOAD' in e[1].split('-> ')[1].upper() and 'RELOAD' not in e[1].split(' ')[1].upper()]
        if not rin:
            rows.append('%s\t%s\tNO RELOAD SEEN' % (sg['gun'], sg['part'])); continue
        t0 = rin[-1][0]
        after = [e for e in ev if e[0] is not None and e[0] >= t0 - 0.001]
        rel = lambda pred: next(('%.2f' % (e[0] - t0) for e in after if pred(e[1])), '-')
        leave = next((e for e in after if e[1].startswith('torso') and 'RELOAD' in e[1].split(' ')[1].upper() and 'RELOAD' not in e[1].split('-> ')[1].upper()), None)
        rows.append('\t'.join([sg['gun'], sg['part'], '%.2f' % t0, rel(lambda s: s == 'weapon row ENTRY'), rel(lambda s: s.startswith('reserve')),
                               rel(lambda s: s == 'weapon row LAST'), rel(lambda s: s == 'weapon row EXIT'),
                               ('%.2f' % (leave[0] - t0)) if leave else '-', leave[1].split('-> ')[1] if leave else '-',
                               str(sum(1 for e in ev if e[1] == 'shot' and e[0] is not None and e[0] <= t0))]))
    dst = os.path.normpath(os.path.join(HERE, '..', 'evidence', 'srvtime_%s.tsv' % sess))
    open(dst, 'w', newline='\n').write('\n'.join(rows) + '\n')
    print('\n'.join(rows))
    print('->', dst)


if __name__ == '__main__':
    main()
