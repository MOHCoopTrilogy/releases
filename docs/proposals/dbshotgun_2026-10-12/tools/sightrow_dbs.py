r"""Lane-local sight row: add or rewrite the row of code/cgame/cg_adssights.h for every key in ../sights_override.json
(the way heavy/tools/sightrow_h.py and the SMG lane's patch_sights_row.py do for their guns; this gun is NEW, so the
row is inserted - after the last `// shotgun` row - when it is not there yet). The shared ironsights sights.json is
NOT touched. "F" / "R" given as the string "model.json sight.F" are read from build/model.json.

    python tools/sightrow_dbs.py C:\mohaa-coop-dev\openmohaa-hzm-dbs\code\cgame\cg_adssights.h [--check]
"""
import sys, os, re, json
import dbslib as L


def main():
    h = sys.argv[1]
    ov = json.load(open(os.path.join(L.PROP, 'sights_override.json')))
    model = json.load(open(os.path.join(L.BUILD, 'model.json')))
    txt = open(h, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)
    n = 0
    for key, o in ov.items():
        F = model['sight']['F'] if isinstance(o['F'], str) else o['F']
        R = model['sight']['R'] if isinstance(o['R'], str) else o['R']
        row = '    {"%s", "%s", {%.4ff, %.4ff, %.4ff}, {%.4ff, %.4ff, %.4ff}, %.6ff, {%.3ff, %.3ff, %.3ff}, %.3ff}, // %s' % (
            o['tik'], o['name'], *F, *R, o['delta_mrad'] / 1000.0, *o['U'], o['relief'], key)
        idx = [i for i, l in enumerate(lines) if l.rstrip().endswith('// ' + key)]
        if idx:
            assert len(idx) == 1
            if lines[idx[0]] != row:
                lines[idx[0]] = row; n += 1
        else:
            last = max(i for i, l in enumerate(lines) if l.rstrip().endswith('// shotgun'))
            lines.insert(last + 1, row); n += 1
        print(row.strip())
    if '--check' not in sys.argv and n:
        open(h, 'w', encoding='utf-8', newline='').write(nl.join(lines))
    print('%d row(s) %s' % (n, 'would change' if '--check' in sys.argv else 'changed'))


if __name__ == '__main__':
    main()
