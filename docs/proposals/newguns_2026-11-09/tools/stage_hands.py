"""Stage the Bren's reload hands into the wpnfix sources: the three retargeted view clips (new) and the re-placed magazine prop."""
import json, os, shutil
SRC = r'C:\hzm-newguns\root\docs\tools\assets\wpnfix'
OUT = r'H:\hzm_work\newguns\brenhands\out'
MAN = os.path.join(SRC, 'wpnfix_manifest.json')
raw = open(MAN, 'rb').read()
man = json.loads(raw)
files = {'models/human/animation/viewmodel/coop_bren/coop_bren_reload_fps.skc': 'coop_bren_reload_fps.skc',
         'models/human/animation/viewmodel/coop_bren/coop_bren_reload_fps_s.skc': 'coop_bren_reload_fps_s.skc',
         'models/human/animation/viewmodel/coop_bren/coop_bren_reload_fps_m.skc': 'coop_bren_reload_fps_m.skc',
         'models/weapons/coop_bren/coop_bren_clip.skd': 'coop_bren_clip.skd'}
for rel, f in files.items():
    dst = os.path.join(SRC, *rel.split('/'))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(OUT, f), dst)
    man.setdefault(rel, {'new': True})
    print(rel, man[rel])
# keep the file's own formatting (indent / key order / newline style)
indent = 1 if b'\n "' in raw else 2
s = json.dumps(dict(sorted(man.items())) if list(man) == sorted(man) else man, indent=indent)
if b'\r\n' in raw:
    s = s.replace('\n', '\r\n')
if raw.endswith(b'\n') and not s.endswith('\n'):
    s += '\r\n' if b'\r\n' in raw else '\n'
open(MAN, 'wb').write(s.encode('utf-8'))
