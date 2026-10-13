"""Read the SRVPROBE lines of run_ded.py's client logs and compare the arms (bug-3736).

    python dedcmp.py <dir with client_<arm>.log> [--ref rel] [--md out.md] [--json out.json]

Per arm / gun / mode (hip, ads), from what the SERVER reported in the snapshots (server time, ms):
  shot gap      time between two shots of one string (clip going down by one), min and median
  double        snapshots in which the clip went down by more than one
  reload        per reload, loaded (rounds left) and emptied (clip 0):
     hands      how long the hands id stayed VM_ANIM_RELOAD (the torso state's reload)
     row        how long the weapon entity showed its `reload` row (= WEAPON_RELOADING; 0 = shorter than a snapshot)
     refill     hands id RELOAD -> the clip is full again
     next shot  hands id RELOAD -> the first shot after it
     clip / reserve  rounds in the clip after the refill, rounds taken from the reserve
  fire row      how long the weapon entity showed `fire` after a shot (ForceIdle at its end), median
A figure differs when it is more than two server frames (50 ms) from the reference arm; figures that hang on the
trigger pulse (shot gap, next shot) when more than one pulse (100 ms).
"""
import sys, os, re, json, statistics
VM_RELOAD = 6
PS = re.compile(r'SRVPROBE st (-?\d+) ps clip (-?\d+) ammo (-?\d+) vma (-?\d+) chg (-?\d+)')
WE = re.compile(r'SRVPROBE st (-?\d+) went (\d+) wanim (\S+) t ([-\d.]+)')
B = re.compile(r'\^~\^~\^ DED (begin|end) (\S+) (\S+) (\S+)')


def sections(path):
    """per (gun, mode): a list of states in server-time order - the ps values and the set of weapon entities showing
    `reload` / `fire` as their newest animation"""
    out = {}
    cur = None
    ps = dict(clip=0, ammo=0, vma=0, chg=0)
    wan = {}
    for ln in open(path, 'rb').read().decode('latin-1').split(chr(10)):
        m = B.search(ln)
        if m:
            cur = (m.group(3), m.group(4)) if m.group(1) == 'begin' else None
            if cur:
                out[cur] = []
            continue
        st = None
        m = PS.search(ln)
        if m:
            st = int(m.group(1)); ps = dict(clip=int(m.group(2)), ammo=int(m.group(3)), vma=int(m.group(4)), chg=int(m.group(5)))
        m = WE.search(ln)
        if m:
            st = int(m.group(1)); wan[m.group(2)] = m.group(3)
        if cur is None:
            continue
        if st is not None:
            w = 'reload' if 'reload' in wan.values() else ('fire' if 'fire' in wan.values() else 'idle')
            e = dict(ps, st=st, wanim=w, t=0.0)
            if out[cur] and out[cur][-1].get('st') == st:
                out[cur][-1] = e
            else:
                out[cur].append(e)
        elif 'GUNCLOCK start' in ln:
            out[cur].append(dict(clock=ln.strip()[-70:]))
    return out


def med(v):
    return int(statistics.median(v)) if v else None


def analyse(ev):
    clocks = [e for e in ev if 'clock' in e]
    ev = [e for e in ev if 'st' in e]
    r = dict(shots=0, gaps=[], double=0, reloads=[], fire_row=[], clocks=len(clocks))
    last_shot = None
    i = 0
    cur_rel = None
    for i in range(1, len(ev)):
        a, b = ev[i - 1], ev[i]
        if b['vma'] == VM_RELOAD and a['vma'] != VM_RELOAD:
            cur_rel = dict(start=b['st'], clip0=a['clip'], ammo0=a['ammo'], hands=None, row0=None, row=0, refill=None, next=None, clip1=None, took=None)
            r['reloads'].append(cur_rel)
            last_shot = None
        if cur_rel and cur_rel['hands'] is None and a['vma'] == VM_RELOAD and b['vma'] != VM_RELOAD:
            cur_rel['hands'] = b['st'] - cur_rel['start']
        if b['wanim'] == 'reload' and (a['wanim'] != 'reload'):
            if cur_rel and cur_rel['row0'] is None:
                cur_rel['row0'] = b['st']
        if a['wanim'] == 'reload' and b['wanim'] != 'reload' and cur_rel and cur_rel['row0'] is not None and cur_rel['row'] == 0:
            cur_rel['row'] = b['st'] - cur_rel['row0']
        d = b['clip'] - a['clip']
        if d > 0 and cur_rel and cur_rel['refill'] is None:
            cur_rel['refill'] = b['st'] - cur_rel['start']
            cur_rel['clip1'] = b['clip']
            cur_rel['took'] = cur_rel['ammo0'] - b['ammo']
        if d < 0:
            r['shots'] += 1
            if d < -1:
                r['double'] += 1
            if last_shot is not None:
                r['gaps'].append(b['st'] - last_shot)
            last_shot = b['st']
            if cur_rel and cur_rel['refill'] is not None and cur_rel['next'] is None:
                cur_rel['next'] = b['st'] - cur_rel['start']
            # the fire row's length: until the weapon entity's newest animation is no longer `fire`
            for j in range(i, min(i + 60, len(ev))):
                if ev[j]['wanim'] != 'fire' and ev[j]['st'] > b['st']:
                    r['fire_row'].append(ev[j]['st'] - b['st'])
                    break
                if j > i and ev[j]['clip'] < ev[j - 1]['clip']:
                    break
    out = dict(shots=r['shots'], gap_min=min(r['gaps']) if r['gaps'] else None, gap_med=med(r['gaps']), double=r['double'],
               fire_row=med(r['fire_row']), clocks=r['clocks'])
    for kind, sel in (('loaded', lambda x: x['clip0'] > 0), ('emptied', lambda x: x['clip0'] == 0)):
        rs = [x for x in r['reloads'] if sel(x) and x['refill'] is not None]
        out['n_' + kind] = len(rs)
        for k in ('hands', 'row', 'refill', 'next', 'clip1', 'took'):
            v = [x[k] for x in rs if x[k] is not None]
            out['%s_%s' % (kind, k)] = med(v)
    return out


KEYS = [('shots', 'shots fired in the window', None), ('gap_min', 'shot gap min', 100), ('gap_med', 'shot gap median', 100), ('double', 'double', 0), ('fire_row', 'fire row', 50),
        ('n_loaded', 'loaded reloads', None), ('loaded_hands', 'loaded: hands', 50), ('loaded_row', 'loaded: row', 50), ('loaded_refill', 'loaded: refill', 50),
        ('loaded_next', 'loaded: next shot', 100), ('loaded_clip1', 'loaded: clip', 0), ('loaded_took', 'loaded: from reserve', None),
        ('n_emptied', 'emptied reloads', None), ('emptied_hands', 'emptied: hands', 50), ('emptied_row', 'emptied: row', 50),
        ('emptied_refill', 'emptied: refill', 50), ('emptied_next', 'emptied: next shot', 100), ('emptied_clip1', 'emptied: clip', 0),
        ('emptied_took', 'emptied: from reserve', 0), ('clocks', 'client clip clock starts', None)]


def main():
    d = sys.argv[1]
    ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else 'rel'
    arms = {}
    for fn in sorted(os.listdir(d)):
        m = re.match(r'client_(\w+)\.log$', fn)
        if m:
            arms[m.group(1)] = {k: analyse(v) for k, v in sections(os.path.join(d, fn)).items()}
    names = [ref] + [a for a in arms if a != ref]
    lines = []
    bad = {a: 0 for a in names}
    for key in sorted(arms.get(ref, {})):
        lines.append('\n### %s, %s\n' % key)
        lines.append('| measure | ' + ' | '.join(names) + ' |')
        lines.append('|---|' + '---|' * len(names))
        for k, label, tol in KEYS:
            vals = [arms[a].get(key, {}).get(k) for a in names]
            cells = []
            for a, v in zip(names, vals):
                c = '-' if v is None else str(v)
                if a != ref and tol is not None and (v is None) != (vals[0] is None):
                    c += ' **DIFF**'; bad[a] += 1
                elif a != ref and tol is not None and v is not None and vals[0] is not None and abs(v - vals[0]) > tol:
                    c += ' **DIFF**'; bad[a] += 1
                cells.append(c)
            lines.append('| %s | %s |' % (label, ' | '.join(cells)))
    lines.append('\nfigures that differ from `%s` by more than the tolerance: ' % ref + ', '.join('%s %d' % (a, bad[a]) for a in names if a != ref))
    txt = '\n'.join(lines)
    print(txt)
    if '--md' in sys.argv:
        open(sys.argv[sys.argv.index('--md') + 1], 'w', newline='\n').write(txt + '\n')
    if '--json' in sys.argv:
        json.dump({a: {'%s %s' % k: v for k, v in arms[a].items()} for a in arms}, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)


if __name__ == '__main__':
    main()
