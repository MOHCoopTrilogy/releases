r"""Sort the merged archive folder back into per-run folders (2026-10-13, bug: the move loop's "\\$d" reached bash as
"\$d", so every run folder was moved INTO ONE folder `H:\\hzm_archive\\dbs$d`).

    python tools/archive_sort.py            # renames only, on H: (same volume); deletes nothing

Frames named ab__<run>__... go to H:\\hzm_archive\\dbs\\<run>\\ ; files whose name carries no run id (they collided
between runs - one copy survived) go to H:\\hzm_archive\\dbs\\_merged_no_run_id\\ with a note.
"""
import os, re, sys
SRC = 'H:\\hzm_archive\\dbs$d'
DST = 'H:\\hzm_archive\\dbs'
rx = re.compile(r'^ab__([a-z]+[0-9]+)__')
n = {}
for d, _, fs in os.walk(SRC):
    for f in fs:
        m = rx.match(f)
        run = m.group(1) if m else '_merged_no_run_id'
        rel = os.path.relpath(d, SRC)
        out = os.path.join(DST, run, '' if rel == '.' else rel)
        os.makedirs(out, exist_ok=True)
        t = os.path.join(out, f)
        assert not os.path.exists(t), t
        os.rename(os.path.join(d, f), t)
        n[run] = n.get(run, 0) + 1
open(os.path.join(DST, '_merged_no_run_id', 'README.txt'), 'w').write(
    'These files had no run id in their names. On 2026-10-13 the run folders hold1..w7 were moved with a broken\n'
    'destination path and landed in ONE folder; files with the same name in several runs (qconsole.log, notes.json,\n'
    'wire_*.jpg, tp_*/act_*/ms_* frames ...) overwrote each other - ONE copy of each survived (which run it is from is\n'
    'not known by name; check the file time). The ab__<run>__ frames were not affected and are in the run folders.\n')
for k in sorted(n):
    print(k, n[k])
left = sum(len(fs) for _, _, fs in os.walk(SRC))
print('left in source:', left)
