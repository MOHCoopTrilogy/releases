"""print the animation blocks whose alias matches the given keys, from the installed paks' player / human anim files"""
import sys, re, glob, os
sys.path.insert(0, glob.glob(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\batches\heavy\tools')[0])
import vfs
keys = sys.argv[1:]
n = int(os.environ.get('N', '520'))
for path in vfs.glob_paths('models/player/base/', '.txt') + vfs.glob_paths('models/human/', '.tik') + vfs.glob_paths('models/player/', '.tik'):
    d = vfs.read(path)
    if not d:
        continue
    s = d.decode('latin-1').replace('\r', '')
    for key in keys:
        m = re.search(r'(?mi)^\s*' + re.escape(key) + r'\b', s)
        if m:
            print('==', path, '<-', os.path.basename(vfs.winner(path)[0]))
            print(s[m.start():m.start() + n].rstrip())
