"""Stage a copy of one of the mod's fps_anims_<class>.txt with rows repointed (the mod tree itself is not touched).

    python stagerows.py <stage root> <class: smg|rifle|mg|shotgun> row=clip [row=clip ...]
"""
import sys, os, re
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
root, cls = sys.argv[1], sys.argv[2]
rel = os.path.join('models', 'player', 'base', 'fps_anims_%s.txt' % cls)
raw = open(os.path.join(MOD, rel), 'rb').read().decode('latin-1')
for a in sys.argv[3:]:
    row, clip = a.split('=')
    rx = re.compile(r'(?m)^(\s*%s\s+)(\S+)' % re.escape(row))
    assert len(rx.findall(raw)) == 1, row
    raw = rx.sub(lambda m: m.group(1) + clip, raw, count=1)
    print('row', row, '->', clip)
dst = os.path.join(root, rel)
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, 'wb').write(raw.encode('latin-1'))
