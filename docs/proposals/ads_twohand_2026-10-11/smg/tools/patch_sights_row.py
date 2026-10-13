r"""Rewrite the rows of code/cgame/cg_adssights.h that belong to the keys of ../sights_override.json (F / R / relief),
in the generator's own row format - the same hunk gen_sights_header.py would emit once the ironsights lane's
sights.json carries the change. Used on the lane's engine worktree only; the shared sights.json is NOT touched here.

    python patch_sights_row.py <worktree>\code\cgame\cg_adssights.h [--check]
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    h = sys.argv[1]
    ov = json.load(open(os.path.join(HERE, '..', 'sights_override.json')))
    txt = open(h, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in txt else '\n'
    out, n = [], 0
    for ln in txt.split(nl):
        m = re.match(r'^(\s*\{"[^"]+", "[^"]+", )\{([^}]*)\}, \{([^}]*)\}, ([-\d.]+f), \{([^}]*)\}, ([-\d.]+f)\}, // (\S+)\s*$', ln)
        if m and m.group(7) in ov:
            o = ov[m.group(7)]
            F = o.get('F'); R = o.get('R')
            f = '%.4ff, %.4ff, %.4ff' % tuple(F) if F else m.group(2)
            r = '%.4ff, %.4ff, %.4ff' % tuple(R) if R else m.group(3)
            rel = ('%.3ff' % o['relief']) if 'relief' in o else m.group(6)
            new = '%s{%s}, {%s}, %s, {%s}, %s}, // %s' % (m.group(1), f, r, m.group(4), m.group(5), rel, m.group(7))
            if new != ln:
                n += 1
                print('-', ln.strip()); print('+', new.strip())
            ln = new
        out.append(ln)
    if '--check' not in sys.argv and n:
        open(h, 'w', encoding='utf-8', newline='').write(nl.join(out))
    print('%d row(s) %s' % (n, 'would change' if '--check' in sys.argv else 'changed'))


if __name__ == '__main__':
    main()
