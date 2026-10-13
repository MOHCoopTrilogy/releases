r"""MOVE finished run folders off G: (the drive ran full, 2026-10-13; coordinator: move, never delete).

    python moveruns.py <prefix,prefix,...|id,id,...> [--max-gb 25] [--keep-c 45]
Each folder G:\mohaa-adsanim4\runs\<id> is copied to DEST\<id>, the copy is verified (same file names and sizes) and only
then is the source removed. Stops when --max-gb is reached or C: would drop under --keep-c GB free. Appends to
DEST\moved.txt (id, files, GB). Tools find a moved run through hv.run_dir(<id>) / ADS_RUNS=<DEST>.
"""
import os, sys, shutil
SRC = 'G:/mohaa-adsanim4/runs'
DEST = r"H:\hzm_archive\heavy"          # the archive disk (slow; finished, written-up runs only - live captures stay on G:)


def arg(k, d):
    if k in sys.argv:
        i = sys.argv.index(k); v = float(sys.argv[i + 1]); del sys.argv[i:i + 2]; return v
    return d


maxgb = arg('--max-gb', 25.0); keepc = arg('--keep-c', 45.0)
pats = sys.argv[1].split(',')
os.makedirs(DEST, exist_ok=True)
moved = 0.0
for d in sorted(os.listdir(SRC)):
    if not any(d == p or (d.startswith(p) and len(p) == 2) for p in pats):
        continue
    s = os.path.join(SRC, d); t = os.path.join(DEST, d)
    if not os.path.isdir(s):
        continue
    files = {e.name: e.stat().st_size for e in os.scandir(s) if e.is_file()}
    sub = [e.name for e in os.scandir(s) if e.is_dir()]
    gb = sum(files.values()) / 2 ** 30
    free = shutil.disk_usage('C:/').free / 2 ** 30
    if moved + gb > maxgb or free - gb < keepc:
        print('stop before %s: moved %.1f GB, C: free %.1f GB' % (d, moved, free)); break
    if sub or os.path.exists(t):
        print('skip', d, '(subfolders)' if sub else '(already at the destination)'); continue
    shutil.copytree(s, t)
    got = {e.name: e.stat().st_size for e in os.scandir(t) if e.is_file()}
    assert got == files, d
    shutil.rmtree(s)
    moved += gb
    open(os.path.join(DEST, 'moved.txt'), 'a').write('%s\t%d files\t%.2f GB\n' % (d, len(files), gb))
    print('moved %s %d files %.2f GB' % (d, len(files), gb), flush=True)
print('done: %.1f GB moved; G: free %.1f GB, C: free %.1f GB' % (moved, shutil.disk_usage('G:/').free / 2 ** 30, shutil.disk_usage('C:/').free / 2 ** 30))
