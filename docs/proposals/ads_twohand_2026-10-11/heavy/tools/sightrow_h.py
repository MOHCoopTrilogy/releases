r"""Lane-local sight rows: rewrite the rows of code/cgame/cg_adssights.h whose key (the trailing `// key`) is in
heavy/sights_override.json - F / R / relief as the SMG lane's patch_sights_row.py does, and `delta_mrad` (that tool
leaves the delta alone). The shared ironsights sights.json is NOT touched. Engine worktree of this lane only.

    python sightrow_h.py <worktree>\code\cgame\cg_adssights.h [--check]

Also stages what the override's `mesh` block names (see sights_override.json): nothing here - the mesh tools do that.
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    h = sys.argv[1]
    ov = json.load(open(os.path.join(HERE, '..', 'sights_override.json')))
    txt = open(h, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in txt else '\n'
    out, n = [], 0
    rx = re.compile(r'^(\s*\{"[^"]+", "[^"]+", )\{([^}]*)\}, \{([^}]*)\}, ([-\d.]+f), \{([^}]*)\}, ([-\d.]+f)\}, // (\S+)\s*$')
    for ln in txt.split(nl):
        m = rx.match(ln)
        if m and m.group(7) in ov:
            o = ov[m.group(7)]
            f = '%.4ff, %.4ff, %.4ff' % tuple(o['F']) if o.get('F') else m.group(2)
            r = '%.4ff, %.4ff, %.4ff' % tuple(o['R']) if o.get('R') else m.group(3)
            dl = ('%.6ff' % (o['delta_mrad'] / 1000.0)) if 'delta_mrad' in o else m.group(4)
            rel = ('%.3ff' % o['relief']) if 'relief' in o else m.group(6)
            new = '%s{%s}, {%s}, %s, {%s}, %s}, // %s' % (m.group(1), f, r, dl, m.group(5), rel, m.group(7))
            if new != ln:
                n += 1
            ln = new
        out.append(ln)
    if '--check' not in sys.argv and n:
        open(h, 'w', encoding='utf-8', newline='').write(nl.join(out))
    print('%d row(s) %s' % (n, 'would change' if '--check' in sys.argv else 'changed'))


if __name__ == '__main__':
    main()
