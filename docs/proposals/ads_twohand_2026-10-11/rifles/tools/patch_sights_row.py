r"""Rows of code/cgame/cg_adssights.h for the keys of ../sights_override.json, in the generator's own row format (the hunk
gen_sights_header.py would emit once the ironsights lane's sights.json carries them). The rifle lane's entries are
NEW guns (`"new": true`, one row per tik of `tiks`): rows are inserted in tik order, existing rows of the same tik are
rewritten. Used on the lane's engine worktree only; the shared sights.json is NOT touched.

    python patch_sights_row.py <worktree>\code\cgame\cg_adssights.h [--check]
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROW = re.compile(r'^\s*\{"([^"]+)", ')


def row(tik, name, o, key):
    return ('    {"%s", "%s", {%.4ff, %.4ff, %.4ff}, {%.4ff, %.4ff, %.4ff}, %.6ff, {%.3ff, %.3ff, %.3ff}, %.3ff}, // %s'
            % ((tik, name) + tuple(o['F']) + tuple(o['R']) + (o.get('delta', 0.0),) + tuple(o.get('up', [0.0, 0.0, -1.0])) + (o.get('relief', 0.0), key)))


def main():
    h = sys.argv[1]
    ov = json.load(open(os.path.join(HERE, '..', 'sights_override.json')))
    txt = open(h, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)
    n = 0
    for key, o in ov.items():
        assert o.get('new'), key + ': only new-gun entries are handled here'
        for tik, name in sorted(o['tiks'].items()):
            new = row(tik, name, o, key)
            at = [i for i, ln in enumerate(lines) if ROW.match(ln) and ROW.match(ln).group(1).lower() == tik.lower()]
            if at:
                if lines[at[0]] != new:
                    print('-', lines[at[0]].strip()); print('+', new.strip()); n += 1
                    lines[at[0]] = new
                continue
            rows = [i for i, ln in enumerate(lines) if ROW.match(ln)]
            pos = next((i for i in rows if ROW.match(lines[i]).group(1).lower() > tik.lower()), rows[-1] + 1)
            lines.insert(pos, new)
            print('+', new.strip()); n += 1
    if '--check' not in sys.argv and n:
        open(h, 'w', encoding='utf-8', newline='').write(nl.join(lines))
    print('%d row(s) %s' % (n, 'would change' if '--check' in sys.argv else 'changed'))


if __name__ == '__main__':
    main()
