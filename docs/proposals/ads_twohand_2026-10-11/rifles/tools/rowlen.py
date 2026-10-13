"""SERVER-READ ROW LENGTHS: every animation row of every staged weapon tik against the RELEASED tik's row of the same
name (frames, seconds). The server plays a weapon tik's rows by NAME (`reload` holds WEAPON_RELOADING until the clip
ends, `fire` -> ForceIdle at its end, `rechamber`), so a row whose clip got longer / shorter changes server state; a
row the released tik does not have (`rechamber_ads`, `reload_ads_empty`) is only ever shown by the cgame.

    python rowlen.py [--all]        (--all prints equal rows too)
A NEW tik (coop_g43_irons*) is compared with the tik it was derived from: REF below.
Writes ../evidence/rowlen_staged_vs_released.tsv
"""
import os, sys, re, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged                       # noqa: E402
vfs = staged.vfs
WDIR = os.path.join(staged.ASSETS, 'models', 'weapons')
REF = lambda tk: re.sub(r'^coop_g43_irons', 'g43', tk)     # the scoped G43 family


def clip_len(data):
    if data is None:
        return None
    import skdlib                       # v13 and (through skc14.py) the processed v14 clips
    a = skdlib.read_skc(data)
    return a.numFrames, a.frameTime


def rows(text):
    """animation rows of a tik: name -> (clip path, has a server block with commands)"""
    t = re.sub(r'//[^\n]*', '', text)
    m = re.search(r'(?mi)^\s*animations\b', t)
    if not m:
        return {}
    head, body = t[:m.start()], t[m.end():]
    path = ''
    for pm in re.finditer(r'(?mi)^\s*path\s+(\S+)', head):
        path = pm.group(1)
    out = {}
    d = 0
    for ln in body.split('\n'):
        s = ln.strip()
        if d == 1:
            pm = re.match(r'(?i)path\s+(\S+)', s)
            if pm:
                path = pm.group(1)
            rm = re.match(r'(\S+)\s+(\S+\.skc)\b', s, re.I)
            if rm:
                out[rm.group(1).lower()] = (path.rstrip('/') + '/' + rm.group(2)).lower()
        d += s.count('{') - s.count('}')
    return out


def measure(tik_text, on):
    (staged.on if on else staged.off)()
    try:
        r = {}
        for nm, clip in rows(tik_text).items():
            r[nm] = (clip, clip_len(vfs.read(clip)))
        return r
    finally:
        staged.on()


def main():
    allrows = '--all' in sys.argv
    lines = ['tik\trow\tstaged clip\tstaged frames\tstaged s\treleased clip\treleased frames\treleased s\tverdict']
    ndiff = nnew = neq = 0
    tiks = sorted(f for f in os.listdir(WDIR) if f.lower().endswith('.tik'))
    for tk in tiks:
        st_text = open(os.path.join(WDIR, tk), 'rb').read().decode('latin-1')
        staged.off()
        rel_raw = vfs.read('models/weapons/' + tk)
        ref = tk
        if rel_raw is None:
            ref = REF(tk)
            rel_raw = vfs.read('models/weapons/' + ref)
        staged.on()
        assert rel_raw is not None, tk + ': no released tik to compare with'
        S = measure(st_text, True)
        Rr = measure(rel_raw.decode('latin-1'), False)
        for nm in sorted(set(S) | set(Rr)):
            sc, sl = S.get(nm, (None, None))
            rc, rl = Rr.get(nm, (None, None))
            f = lambda l: ('%d\t%.3f' % (l[0], l[0] * l[1])) if l else '-\t-'
            if nm not in Rr:
                v = 'NEW ROW (not in the released tik: the server has no name for it)'; nnew += 1
            elif nm not in S:
                v = 'ROW REMOVED'; ndiff += 1
            elif sl is None or rl is None:
                v = 'CLIP NOT FOUND'; ndiff += 1
            elif sl[0] != rl[0] or abs(sl[1] - rl[1]) > 1e-6:
                v = 'LENGTH DIFFERS'; ndiff += 1
            else:
                v = 'equal'; neq += 1
            if v != 'equal' or allrows:
                lines.append('\t'.join([tk + ('' if ref == tk else ' (vs ' + ref + ')'), nm, str(sc), f(sl), str(rc), f(rl), v]))
    out = os.path.normpath(os.path.join(HERE, '..', 'evidence', 'rowlen_staged_vs_released.tsv'))
    open(out, 'w', newline='\n').write('\n'.join(lines) + '\n')
    print('\n'.join(l for l in lines if 'NEW ROW' not in l))
    print('tiks %d, rows equal %d, rows that DIFFER %d, new rows %d -> %s' % (len(tiks), neq, ndiff, nnew, out))
    # the new rows, by name
    names = {}
    for l in lines[1:]:
        c = l.split('\t')
        if 'NEW ROW' in c[-1]:
            names.setdefault(c[1], []).append(c[0])
    for k, v in sorted(names.items()):
        print('new row %-22s in %d tiks' % (k, len(v)))


if __name__ == '__main__':
    main()
